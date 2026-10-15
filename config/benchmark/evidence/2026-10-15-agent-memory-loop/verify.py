"""Verify arithmetic and integrity, not the private semantic judgments."""
import hashlib, json, statistics
from pathlib import Path

root=Path(__file__).parent
load=lambda name:json.loads((root/name).read_text())
for name,expected in load('manifest.json')['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
d=load('measurements.json');requests=load('requests.json');b=d['budget']
assert len(requests)==b['new_requests']==128
assert all(r['status']=='completed' for r in requests)
added=sum(r['usage']['cost'] for r in requests)
assert abs(added-b['added_settled_usd'])<1e-9
assert abs(b['opening_settled_usd']+added-b['settled_usd'])<1e-9
assert abs(b['opening_exposure_usd']+added-b['exposure_usd'])<1e-9
assert 0<=b['settled_usd']<=b['exposure_usd']<=b['ceiling_usd']==10
covered=[]
for row in d['cells']+d['preparation']:
    start,end=row['requests'];assert 0<=start<=end<=len(requests)
    covered.extend(range(start,end))
    assert abs(sum(r['usage']['cost'] for r in requests[start:end])-row['paid_usd'])<1e-9
assert sorted(covered)==list(range(len(requests)))
assert len(d['cells'])==15 and sum(c['phase']=='formal' for c in d['cells'])==12
assert len({c['pid'] for c in d['cells']})==15
formal=[c for c in d['cells'] if c['phase']=='formal']
keys={(c['task_id'],c['repetition']) for c in formal};assert len(keys)==4
for key in keys:
    assert sorted(c['condition'] for c in formal if (c['task_id'],c['repetition'])==key)==['full_elf','no_elf','source_only']
for arm,s in d['summary'].items():
    rows=[c for c in d['cells'] if c['phase']=='formal' and c['condition']==arm]
    assert len(rows)==s['cells']==4
    assert sum(c['accepted'] for c in rows)==s['accepted']
    assert sum(c['passed_criteria'] for c in rows)==s['passed_criteria']
    assert sum(c['criteria'] for c in rows)==s['criteria']==24
    assert abs(statistics.mean(c['seconds'] for c in rows)-s['mean_seconds'])<1e-9
    assert abs(sum(c['paid_usd'] for c in rows)-s['paid_usd'])<1e-9
    assert all(c['native_binding'] and c['all_references_seen'] for c in rows)
i=load('integrity.json');assert i['restore']['source_count']==6 and i['restore']['postgres_state_equal']
assert all(v['dimension']==4096 and v['stored_vector_query_passed'] for v in i['restore']['qdrant'])
assert i['native'][-1]['sources_verified']==6 and i['native'][-1]['notes']==17
print(json.dumps({'verified_cells':15,'formal_cells':12,'added_usd':added,'settled_usd':b['settled_usd'],'exposure_usd':b['exposure_usd']}))
