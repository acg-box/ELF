"""Offline verification: hashes, embedding reuse, paired judgments and accounting."""
import gzip
import hashlib
import json
import math
from pathlib import Path

root=Path(__file__).resolve().parent

def read(name):
    p=root/name
    raw=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
    return json.loads(raw)

def lines(name):return [json.loads(x) for x in gzip.decompress((root/name).read_bytes()).splitlines()]

manifest=read('manifest.json')
assert set(manifest)=={p.name for p in root.iterdir() if p.is_file() and p.name!='manifest.json'}
for name,sha in manifest.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
prior=root.parent/'2026-10-10-elf-language-provenance'
witness={}
for line in gzip.decompress((prior/'provider-receipts.jsonl.gz').read_bytes()).splitlines():
    r=json.loads(line);req,res=r['request'],r['response']
    if 'input' not in req or 'data' not in res:continue
    inputs=req['input'] if isinstance(req['input'],list) else [req['input']]
    receipt_sha=hashlib.sha256((json.dumps({'request':req,'response':res},indent=2)+'\n').encode()).hexdigest()
    for v in res['data']:witness[receipt_sha,inputs[v['index']]]=v['embedding']
data=read('dataset.json.gz')
assert len(data['corpus'])==71 and len(data['queries'])==70
for row in data['corpus']+data['queries']:
    text=row.get('text',row.get('question'))
    assert row['vector']==witness[row['receipt_sha256'],text]
    assert row['embedding_input_sha256']==hashlib.sha256(text.encode()).hexdigest()
assert read('embedding-reuse.json')['missing']==[]
assert read('context-controls.json')['prior_combined_contexts_reproduced']==20
cases=lines('ablation-cases.jsonl.gz');reviews={(r['condition'],r['case_id']):r for r in read('ablation-review.json')}
assert len(cases)==len(reviews)==60
for c in cases:
    r=reviews[c['condition'],c['query']['case_id']]
    assert c['status']=='completed'
    assert r['answer_sha256']==hashlib.sha256(c['text'].encode()).hexdigest()
    assert r['strict_correct']==c['strict_correct']
    if r['reviewed_correct']!=r['strict_correct']:
        assert c['query']['lane']=='abstention'
        assert c['text'].lower().startswith('no budget owner has been appointed')
        assert 'no budget owner has been appointed' in c['context']['text'].lower()
for condition,summary in read('ablation-summary.json').items():
    selected=[c for c in cases if c['condition']==condition and c['query']['split']!='dev']
    assert len(selected)==summary['scored']==16
    assert sum(reviews[condition,c['query']['case_id']]['reviewed_correct'] for c in selected)==summary['reviewed_correct']
    assert sum(c['strict_correct'] for c in selected)==summary['strict_correct']
usage=lines('usage.jsonl.gz');cost=read('accounting.json')
assert len(usage)==60 and all(x['status']=='completed' and x['kind']=='chat' for x in usage)
assert [x['ordinal'] for x in usage]==list(range(893,953))
assert math.isclose(sum(x['usage']['cost'] for x in usage),cost['new_paid_usd'])
assert math.isclose(sum(c['reader']['usage']['cost'] for c in cases),cost['new_paid_usd'])
assert math.isclose(cost['prior_paid_usd']+cost['new_paid_usd'],cost['cumulative_paid_usd'])
assert cost['cumulative_paid_usd']<=10 and cost['new_embedding_calls']==cost['unsettled']==0
for receipt in lines('provider-receipts.jsonl.gz'):
    r=receipt['request'];assert r['model']=='deepseek/deepseek-v4.1-flash'
    assert r['max_tokens']==943718 and r['reasoning']['effort']=='max'
for n in [10000,50000]:
    vector_hashes=set();query_hashes=set()
    for backend in ['infinity','qdrant','postgres']:
        v=read(f'{backend}-scale-{n}.json.gz');vector_hashes.add(v['vector_sha256']);query_hashes.add(v['query_sha256'])
        assert len(v['rows'])==840 and v['delete_visibility']['absent']
        for r in v['rows']:
            assert len(r['ids'])==len(set(r['ids']))==r['returned']==10
            assert not r['filtered'] or all(i%10==r['query']%10 for i in r['ids'])
            assert math.isclose(r['recall_at_10'],len(set(r['ids'])&set(r['exact_ids']))/10)
    assert len(vector_hashes)==len(query_hashes)==1
assert len(read('latency-rows.json.gz'))==5040
for backend in ['infinity','qdrant','postgres']:
    v=read(backend+'-sustained.json.gz');assert len(v['rounds'])==3
    for r in v['rounds']:
        assert r['seconds']>=9.99 and len(r['workers'])==8
        assert not any(w.get('failure') for w in r['workers'])
        assert sum(w['queries'] for w in r['workers'])==r['queries']
        assert math.isclose(r['qps'],r['queries']/r['seconds'])
print(json.dumps({'answers':60,'cached_vectors_reused':141,'dense_measurements':5040,'cumulative_paid_usd':cost['cumulative_paid_usd']}))
