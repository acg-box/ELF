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
    if (root/'ablation-review.json').exists():
        reviewed={(r['condition'],r['case_id']):r for r in read(root/'ablation-review.json')}
        answers=[]
        for path in sorted((root/'ablation').glob('*/*.json')):
            v=read(path);usage=v['reader']['usage'];review=reviewed[v['condition'],v['query']['case_id']]
            answers.append({'condition':v['condition'],'case_id':v['query']['case_id'],'split':v['query']['split'],
                'strict_correct':v['strict_correct'],'reviewed_correct':review['reviewed_correct'],
                'context_tokens':v['context']['tokens'],'seconds':v['seconds'],'paid_usd':usage['cost'],
                'prompt_tokens':usage['prompt_tokens'],'completion_tokens':usage['completion_tokens'],
                'cached_tokens':(usage.get('prompt_tokens_details') or {}).get('cached_tokens',0)})
        save(root/'answer-rows.json',answers)
        db.execute('CREATE OR REPLACE TABLE answers AS SELECT * FROM read_json_auto(?)',[str(root/'answer-rows.json')])
        answer_sql="""SELECT condition,count(*) AS completed,
          count(*) FILTER (WHERE split != 'dev') AS scored,
          sum(strict_correct::INTEGER) FILTER (WHERE split != 'dev') AS strict_correct,
          sum(reviewed_correct::INTEGER) FILTER (WHERE split != 'dev') AS reviewed_correct,
          sum(reviewed_correct::INTEGER) AS all_reviewed_correct,
          avg(context_tokens) AS mean_context_tokens,quantile_cont(seconds,0.5) AS median_seconds,
          sum(paid_usd) AS paid_usd,sum(prompt_tokens) AS prompt_tokens,
          sum(completion_tokens) AS completion_tokens,sum(cached_tokens) AS cached_tokens
          FROM answers GROUP BY condition ORDER BY condition"""
        cursor=db.execute(answer_sql);columns=[x[0] for x in cursor.description]
        aggregate=[dict(zip(columns,row)) for row in cursor.fetchall()]
        save(root/'ablation-summary.json',{r.pop('condition'):r for r in aggregate})
        (root/'ablation-analysis.sql').write_text(answer_sql+';\n')
    db.close()
    print({'latency_rows':len(observations),'quality_rows':len(quality),'duckdb':duckdb.__version__},flush=True)
