"""Matched dense recall/latency and native lexical quality probes."""
import concurrent.futures
import hashlib
import json
import random
import threading
import time
import numpy as np
from .backends import BACKENDS, rrf
from .common import read, save


def normalize(values):
    values=np.asarray(values,dtype=np.float32)
    return values/np.linalg.norm(values,axis=1,keepdims=True)


def exact(vectors,query,tenants,tenant,k=10):
    ids=np.arange(len(vectors)) if tenant is None else np.flatnonzero(tenants==tenant)
    scores=vectors[ids]@query
    # stable ties by row identity; the float32 reference is independent of all engines.
    return ids[np.lexsort((ids,-scores))[:k]].tolist()


def measured(call):
    start=time.perf_counter_ns();value=call()
    return value,(time.perf_counter_ns()-start)/1e6


def scale_data(base,n):
    rng=np.random.default_rng(20261010+n)
    left=rng.integers(len(base),size=n);right=rng.integers(len(base),size=n)
    weight=rng.uniform(.3,.8,size=(n,1)).astype(np.float32)
    values=weight*base[left]+(1-weight)*base[right]
    values+=rng.normal(0,.015,size=values.shape).astype(np.float32)
    return normalize(values)


def benchmark(root,backend):
    folder=root/'backends'/backend
    folder.mkdir(parents=True,exist_ok=True)
    data=read(root/'dataset.json')
    corpus=data['corpus'];queries=data['queries']
    base=normalize([r['vector'] for r in corpus]);qvectors=normalize([q['vector'] for q in queries])
    results=[]
    small_path=folder/'quality.json'
    if not small_path.exists():
        db=BACKENDS[backend]('elf_lab_real')
        rows=[{**r,'tenant':int(r['scope']=='memory')} for r in corpus]
        start=time.monotonic();state=db.create(rows,base,hybrid=True);build=time.monotonic()-start
        for q,vec in zip(queries,qvectors):
            tenant=int(q['scope']=='memory')
            dense,dense_ms=measured(lambda:db.search(vec,tenant,128,k=10))
            def hybrid():
                return rrf([db.search(vec,tenant,128,k=60),db.text(q['question'],tenant,k=60)])
            combined,hybrid_ms=measured(hybrid)
            for mode,hits,latency in [('dense',dense,dense_ms),('hybrid',combined,hybrid_ms)]:
                texts='\n'.join(corpus[i]['text'] for i in hits)
                ids=[corpus[i]['evidence_id'] for i in hits]
                relevant=set(q['expected']['evidence'])
                results.append({'case_id':q['case_id'],'scope':q['scope'],'split':q.get('split','diagnostic'),'mode':mode,'ids':ids,'ms':latency,
                    'reference_source_coverage':len(set(ids)&relevant)/len(relevant) if relevant else None,
                    'expected_fact_coverage':all(f.casefold() in texts.casefold() for f in q['expected']['facts']) if q['expected']['supported'] else None})
        save(small_path,{'build_seconds':build,'state':state,'rows':results})
        print(json.dumps({'backend':backend,'phase':'quality','queries':len(results),'build_seconds':build}),flush=True)
    for n in [10000,50000]:
        path=folder/f'scale-{n}.json'
        if path.exists():continue
        vectors=scale_data(base,n);tenants=np.arange(n,dtype=np.int32)%10
        rows=[{'id':i,'tenant':int(tenants[i])} for i in range(n)]
        name='elf_lab_'+str(n);db=BACKENDS[backend](name)
        start=time.monotonic();state=db.create(rows,vectors);build=time.monotonic()-start
        print(json.dumps({'backend':backend,'phase':'indexed','n':n,'build_seconds':build,'state':state}),flush=True)
        reference={(i,filtered):exact(vectors,q,tenants,i%10 if filtered else None) for i,q in enumerate(qvectors) for filtered in [False,True]}
        results=[]
        # Warm every query/filter, then fixed shuffled query order for repeated measurements.
        for i,q in enumerate(qvectors):
            for filtered in [False,True]:db.search(q,i%10 if filtered else None,128)
        for ef in [64,128]:
            jobs=[(i,filtered,repeat) for repeat in range(3) for i in range(len(queries)) for filtered in [False,True]]
            random.Random(20261010).shuffle(jobs)
            for i,filtered,repeat in jobs:
                tenant=i%10 if filtered else None
                hits,ms=measured(lambda:db.search(qvectors[i],tenant,ef))
                truth=reference[i,filtered]
                assert len(set(hits))==len(hits)
                assert tenant is None or all(tenants[x]==tenant for x in hits), 'Scope filter leak'
                results.append({'query':i,'filtered':filtered,'repeat':repeat,'ef':ef,'ids':hits,'exact_ids':truth,'recall_at_10':len(set(hits)&set(truth))/len(truth),'returned':len(hits),'ms':ms})
        local=threading.local()
        def parallel(i):
            if not hasattr(local,'db'):local.db=BACKENDS[backend](name)
            return local.db.search(qvectors[i%len(queries)],None,128)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(parallel,range(16)))
            start=time.monotonic();outputs=list(pool.map(parallel,range(280)));seconds=time.monotonic()-start
        # A deleted nearest neighbor must disappear from a subsequent accepted query.
        victim=reference[0,False][0];start=time.monotonic();db.delete(victim)
        after=db.search(qvectors[0],None,128)
        delete_ms=(time.monotonic()-start)*1000
        assert victim not in after,'Deleted row remains visible after synchronous delete'
        save(path,{'n':n,'dimension':1536,'synthetic':True,'generator':'seeded mixture of cached real vectors plus Gaussian noise; not a real large corpus',
            'vector_sha256':hashlib.sha256(vectors.tobytes()).hexdigest(),'query_sha256':hashlib.sha256(qvectors.tobytes()).hexdigest(),
            'build_seconds':build,'state':state,'plans':db.plans(qvectors[0]) if hasattr(db,'plans') else None,'rows':results,'concurrency_8':{'queries':280,'seconds':seconds,'qps':280/seconds,'all_returned_10':all(len(x)==10 for x in outputs)},
            'delete_visibility':{'victim':victim,'absent':True,'delete_and_query_ms':delete_ms}})
        print(json.dumps({'backend':backend,'phase':'complete','n':n,'qps8':280/seconds}),flush=True)
