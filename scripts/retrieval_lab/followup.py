"""Sustained throughput and explicit PostgreSQL planner diagnosis after the base run."""
import concurrent.futures
import json
import logging
import threading
import time
import numpy as np
from .backends import BACKENDS
from .benchmark import measured, normalize
from .common import read, save


def followup(root, backend, round_count=3):
    if (root/'backends'/backend/'sustained.json').exists():
        raise ValueError('Sustained evidence already exists; archive the attempt or use a fresh artifact root')
    logging.disable(logging.NOTSET)
    logging.basicConfig(level=logging.ERROR)
    queries=normalize([q['vector'] for q in read(root/'dataset.json')['queries']])
    name='elf_lab_50000'
    rounds=[]
    for round_index in range(round_count):
        barrier=threading.Barrier(8)
        shared={}
        def worker(worker_id):
            db=BACKENDS[backend](name)
            for i in range(10):db.search(queries[(worker_id+i)%len(queries)],None,128)
            barrier.wait()
            if worker_id==0:shared['end']=time.perf_counter()+10
            barrier.wait()
            latencies=[];i=worker_id;underfilled=0
            start=time.perf_counter()
            failure=None
            try:
                while time.perf_counter()<shared['end']:
                    hits,ms=measured(lambda:db.search(queries[i%len(queries)],None,128))
                    underfilled+=len(hits)!=10
                    latencies.append(ms);i+=8
            except Exception as error:
                failure={'query':i%len(queries),'type':type(error).__name__,'message':str(error)}
            finally:
                db.close()
            return {'queries':len(latencies),'latencies_ms':latencies,'seconds':time.perf_counter()-start,'underfilled':underfilled,'failure':failure}
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            rows=list(pool.map(worker,range(8)))
        seconds=max(r['seconds'] for r in rows);count=sum(r['queries'] for r in rows)
        rounds.append({'round':round_index,'seconds':seconds,'queries':count,'qps':count/seconds,'workers':rows})
        save(root/'backends'/backend/'sustained.json',{'seconds_per_round':10,'rounds':rounds,'concurrency':8,'ef':128,'filtered':False,'rows_in_table':49999,'complete':False})
        print(json.dumps({'backend':backend,'round':round_index,'qps':count/seconds,'failures':sum(r['failure'] is not None for r in rows)}),flush=True)
        if any(r['failure'] for r in rows):raise RuntimeError('Sustained trial failed; partial measurements retained')
    save(root/'backends'/backend/'sustained.json',{'seconds_per_round':10,'rounds':rounds,'concurrency':8,'ef':128,'filtered':False,'rows_in_table':49999,'complete':True,'boundary':'Runs after the matched deletion probe removed the same exact nearest-neighbor row from each backend.'})
    if backend=='postgres':
        db=BACKENDS[backend](name)
        base=read(root/'backends'/backend/'scale-50000.json')
        victim=base['delete_visibility']['victim']
        # Restore the deleted vector identically so original exact qrels apply.
        from .benchmark import scale_data
        data=read(root/'dataset.json');vectors=scale_data(normalize([r['vector'] for r in data['corpus']]),50000)
        db.client.execute(f'INSERT INTO {name}(id,tenant,vec,body) VALUES (%s,%s,%s,%s)',(victim,victim%10,vectors[victim],''))
        db.client.execute('SET enable_bitmapscan = off')
        db.client.execute('SET enable_seqscan = off')
        db.client.execute('SET enable_sort = off')
        # Discourage exact B-tree + sort, leaving ordered HNSW with iterative filtering.
        rows=[]
        ref={(x['query'],x['filtered']):x['exact_ids'] for x in base['rows']}
        for i,q in enumerate(queries):db.search(q,i%10,128)
        for repeat in range(3):
            for i,q in enumerate(queries):
                ids,ms=measured(lambda:db.search(q,i%10,128))
                assert all(x%10==i%10 for x in ids)
                rows.append({'query':i,'repeat':repeat,'ids':ids,'ms':ms,'recall_at_10':len(set(ids)&set(ref[i,True]))/10})
        save(root/'backends'/backend/'forced-hnsw-filtered.json',{'settings':{'enable_bitmapscan':'off','enable_seqscan':'off','enable_sort':'off','hnsw.iterative_scan':'strict_order','ef':128},'plans':db.plans(queries[0]),'rows':rows,'boundary':'Diagnostic local-session settings only; not a production recommendation or a replacement for the default-planner measurements.'})
