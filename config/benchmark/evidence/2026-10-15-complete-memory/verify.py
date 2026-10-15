"""Verify public arithmetic and native receipts; private semantic review is not reproduced."""
import hashlib,json,statistics
from pathlib import Path
root=Path(__file__).parent
read=lambda name:json.loads((root/name).read_text())
for name,sha in read('manifest.json')['files'].items():
 assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
m=read('measurements.json');b=m['budget'];i=read('integrity.json');rows=read('requests.json')
paid=sum(r.get('usage',{}).get('cost',0) for r in rows)
reserve=sum(r['reserved_usd'] for r in rows if 'cost' not in r.get('usage',{}))
assert len(rows)==b['new_requests']
assert abs(paid-b['added_settled_usd'])<1e-9
assert abs(reserve-b['new_unresolved_reserve_usd'])<1e-9
assert abs(b['opening_settled_usd']+paid-b['settled_usd'])<1e-9
assert abs(b['opening_exposure_usd']+paid+reserve-b['exposure_usd'])<1e-9
assert 0<=b['settled_usd']<=b['exposure_usd']<=b['ceiling_usd']==10
assert paid+reserve<=0.5
covered=[]
for row in m['cells']+m['preparation']:
 a,z=row['requests'];assert 0<=a<=z<=len(rows);covered.extend(range(a,z))
 assert abs(sum(r.get('usage',{}).get('cost',0) for r in rows[a:z])-row['paid_usd'])<1e-9
for row in m['native_probes']:
 covered.extend(row['request_indices'])
 assert abs(sum(rows[j].get('usage',{}).get('cost',0) for j in row['request_indices'])-row['paid_usd'])<1e-9
assert sorted(covered)==list(range(len(rows)))
formal=[c for c in m['cells'] if c['phase']=='formal'];calibration=[c for c in m['cells'] if c['phase']=='calibration']
assert len(formal)==6 and len(calibration)==3
for mode,expected in [('replay',4),('boundary',1),('fresh',1)]:
 cells=[c for c in formal if c['mode']==mode];s=m['summary'][mode]
 assert len(cells)==s['cells']==expected
 assert sum(c['criteria'] for c in cells)==s['criteria']
 assert sum(c['passed_criteria'] for c in cells)==s['passed_criteria']
 assert sum(c['accepted'] for c in cells)==s['accepted']
 assert abs(statistics.mean(c['seconds'] for c in cells)-s['mean_seconds'])<1e-9
 assert abs(sum(c['paid_usd'] for c in cells)-s['reader_paid_usd'])<1e-9
 assert sum(c['memory_use']['notes_read']>0 for c in cells)==s['memory_read_cells']
 assert sum(c['memory_use']['originals_cited']>0 for c in cells)==s['exact_memory_original_cited_cells']
assert all(c['passed_criteria']==sum(c['criterion_pass']) and c['criteria']==len(c['criterion_pass']) for c in m['cells'])
assert all(c['native_binding'] and c['all_references_seen'] for c in m['cells'])
assert all(c['memory_use']['notes_read'] and c['memory_use']['originals_cited'] for c in calibration)
assert i['replay_oracle_matches_previous'] and i['replay_questions_match_previous']
assert i['replay']['proposals_unchanged'] and i['replay']['originals_unchanged'] and i['replay']['indexed_text_unchanged']
assert len(i['candidate_replay'])==26 and i['replay']['restored']==7
assert all(c['new_op']=='ADD' for c in i['candidate_replay'] if c['old_reason']=='REJECT_TOO_LONG')
assert i['prior_520']['characters']==520 and i['prior_520']['new_ops']==['ADD']*3
assert i['prior_520']['complete_text_stored_and_read'] and i['prior_520']['proposals_unchanged']
assert i['prior_520_tiny_budget']=={'complete':False,'notes':0,'omitted':1}
assert all(i[k]['index_audit']['exact_parent_substrings'] and i[k]['index_audit']['all_nonwhitespace_parent_bytes_covered'] for k in ('replay','prior_520'))
assert all(v['embedding_dim']==4096 for state in i['native'] for values in state['vectors'].values() for v in values)
assert all(r['postgres_state_equal'] for r in i['restore'])
assert all(v['dimension']==4096 and v['stored_vector_query_passed'] for r in i['restore'] for v in r['qdrant'])
p=read('protocol.json');assert p['model']=='openai/gpt-6-luna' and p['reasoning']=='medium' and p['max_output_tokens']==128000
assert p['note_character_limit'] is None and p['ingest_max_bytes']==32768 and p['preview_max_chars']==512 and p['mmr_enabled']
print(json.dumps({'formal':{k:[v['passed_criteria'],v['criteria']] for k,v in m['summary'].items()},'added_usd':paid,'exposure_usd':b['exposure_usd']}))
