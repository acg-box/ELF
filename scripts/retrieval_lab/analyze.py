"""Use DuckDB to query retained measurements; never replace raw observations."""
import duckdb
from .common import read, save


def analyze(root):
    db=duckdb.connect(str(root/'analysis.duckdb'))
    observations=[]
    throughput=[]
    quality=[]
    for backend in ['qdrant','infinity','postgres']:
        folder=root/'backends'/backend
        if (folder/'quality.json').exists():
            quality += [{**r,'backend':backend} for r in read(folder/'quality.json')['rows']]
        for n in [10000,50000]:
            if not (folder/f'scale-{n}.json').exists():continue
            value=read(folder/f'scale-{n}.json')
            observations += [{**r,'backend':backend,'n':n} for r in value['rows']]
            throughput.append({'backend':backend,'n':n,'build_seconds':value['build_seconds'],**value['concurrency_8'],'delete_ms':value['delete_visibility']['delete_and_query_ms']})
    save(root/'latency-rows.json',observations)
    save(root/'throughput-rows.json',throughput)
    save(root/'quality-rows.json',quality)
    sql="""SELECT backend,n,filtered,ef,count(*) AS samples,
      round(avg(recall_at_10),4) AS recall_at_10,
      round(quantile_cont(ms,0.5),3) AS median_ms,
      round(quantile_cont(ms,0.95),3) AS p95_ms,
      min(returned) AS minimum_returned
      FROM measurements GROUP BY ALL ORDER BY n,filtered,ef,backend"""
    if observations:
        db.execute('CREATE OR REPLACE TABLE measurements AS SELECT * FROM read_json_auto(?)',[str(root/'latency-rows.json')])
        cursor=db.execute(sql);columns=[x[0] for x in cursor.description]
        summary=[dict(zip(columns,row)) for row in cursor.fetchall()]
    else:summary=[]
    save(root/'backend-summary.json',{'latency':summary,'throughput':throughput})
    (root/'analysis.sql').write_text(sql+';\n')
    if quality:
        db.execute('CREATE OR REPLACE TABLE quality AS SELECT * FROM read_json_auto(?)',[str(root/'quality-rows.json')])
        cursor=db.execute("SELECT backend,mode,scope,count(*) AS questions,avg(reference_source_coverage) AS source_coverage,avg(expected_fact_coverage::INTEGER) AS fact_coverage FROM quality WHERE split != 'dev' GROUP BY ALL ORDER BY scope,mode,backend")
        columns=[x[0] for x in cursor.description]
        save(root/'quality-summary.json',[dict(zip(columns,row)) for row in cursor.fetchall()])
    db.close()
    print({'latency_rows':len(observations),'quality_rows':len(quality),'duckdb':duckdb.__version__},flush=True)
