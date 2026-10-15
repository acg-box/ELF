"""Check public arithmetic and integrity; private semantic review is not reproduced."""
import hashlib,json,statistics
from pathlib import Path
root=Path(__file__).parent
read=lambda name:json.loads((root/name).read_text())
for name,sha in read('manifest.json')['files'].items():
 assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
d=read('measurements.json');b=d['budget'];requests=read('requests.json');i=read('integrity.json')
paid=sum(r.get('usage',{}).get('cost',0) for r in requests)
reserve=sum(r['reserved_usd'] for r in requests if 'cost' not in r.get('usage',{}))
assert len(requests)==b['new_requests']
assert abs(paid-b['added_settled_usd'])<1e-9 and abs(reserve-b['new_unresolved_reserve_usd'])<1e-9
assert abs(b['opening_settled_usd']+paid-b['settled_usd'])<1e-9
assert abs(b['opening_exposure_usd']+paid+reserve-b['exposure_usd'])<1e-9
assert 0<=b['settled_usd']<=b['exposure_usd']<=b['ceiling_usd']==10
assert paid+reserve<=0.5
covered=[]
for row in d['cells']+d['preparation']+[d['native_probe']]:
 a,z=row['requests'];assert 0<=a<=z<=len(requests);covered.extend(range(a,z))
 assert abs(sum(r.get('usage',{}).get('cost',0) for r in requests[a:z])-row['paid_usd'])<1e-9
assert sorted(covered)==list(range(len(requests)))
formal=[c for c in d['cells'] if c['phase']=='formal'];s=d['summary']
assert len(formal)==s['formal_cells']==4
assert sum(c['passed_criteria'] for c in formal)==s['passed_criteria']==21
assert sum(c['criteria'] for c in formal)==s['criteria']==24
assert sum(c['accepted'] for c in formal)==s['accepted']==1
assert all(c['native_binding'] and c['all_references_seen'] for c in formal)
assert all(c['current_repair_state_correct'] and c['literal_rejection_retained'] and c['pending_native_acceptance_preserved'] for c in formal)
assert all(c['passed_criteria']==sum(c['criterion_pass']) for c in d['cells'])
assert abs(statistics.mean(c['seconds'] for c in formal)-s['mean_seconds'])<1e-9
assert abs(sum(c['paid_usd'] for c in formal)-s['reader_paid_usd'])<1e-9
assert i['restored_candidates']==7 and i['critical_recall_ranks']==[1,1]
assert i['proposals_unchanged'] and i['originals_unchanged'] and i['indexed_text_unchanged']
assert i['replay_oracle_matches_previous'] and i['replay_questions_match_previous']
assert len(i['candidate_replay'])==26
assert all(c['new_op']=='ADD' for c in i['candidate_replay'] if c['old_reason']=='REJECT_TOO_LONG')
assert i['fresh_ingestion_profile']['version']==7
assert sorted((n['characters'],n['op']) for n in i['fresh_candidates'])==[(417,'ADD'),(489,'ADD'),(520,'REJECTED')]
assert all(n['characters']<=512 for n in i['fresh_candidates'] if n['op']=='ADD')
assert next(n for n in i['fresh_candidates'] if n['op']=='REJECTED')['reason']=='REJECT_TOO_LONG'
assert all(r['postgres_state_equal'] for r in i['restore'])
assert all(v['dimension']==4096 and v['stored_vector_query_passed'] for r in i['restore'] for v in r['qdrant'])
assert all(v['embedding_dim']==4096 for state in i['native'] for rows in state['vectors'].values() for v in rows)
print(json.dumps({'formal_obligations':[s['passed_criteria'],s['criteria']],'restored_candidates':7,'added_usd':paid,'exposure_usd':b['exposure_usd']}))
