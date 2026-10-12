"""Inspect stored representations separately from agent answer quality."""
import json
from pathlib import Path
from collections import defaultdict,deque
r=Path(__file__).resolve().parent
def read(name):return json.loads((r/name).read_text())
work=read('workload.json');entities={e['entity_id']:e for e in read('graph_entities.json')};facts=read('graph_facts.json');edges=read('graph_fact_evidence.json')
groups={s['evidence_id']:i//4 for i,s in enumerate(work['items'])};notes={n['note_id']:n for n in read('notes.json')}
origins={key:{groups[e['source']['message_id']] for e in n['source_ref'].get('evidence',[])} for key,n in notes.items()}
by_fact=defaultdict(set)
for e in edges:by_fact[e['fact_id']].update(origins[e['note_id']])
entity_groups=defaultdict(set);adj=defaultdict(list)
for f in facts:
 for identity in (f['subject_entity_id'],f.get('object_entity_id')):
  if identity:entity_groups[identity].update(by_fact[f['fact_id']])
 if f.get('object_entity_id'):adj[f['subject_entity_id']].append((f['object_entity_id'],f['fact_id']))
aliases=read('graph_entity_aliases.json')
paths=[]
for group,name in enumerate(['Larch','Cobalt','Reed','Sable','Cedar','ACCT-N','ACCT-S','EGRET-CN','DELTA-8']):
 canonical_starts=[i for i,e in entities.items() if e['canonical']==name]
 starts=sorted(set(canonical_starts)|{a['entity_id'] for a in aliases if a['alias_norm']==name.casefold()});target=f'REPLAY-{group}-632';found=[]
 for start in starts:
  queue=deque([(start,[])]);seen={start}
  while queue:
   identity,path=queue.popleft()
   if entities[identity]['canonical']==target:found.append(path);break
   if len(path)>=3:continue
   for other,fact in adj[identity]:
    if other not in seen:seen.add(other);queue.append((other,path+[fact]))
 paths.append({'group':group,'canonical_start':name,'canonical_start_ids':canonical_starts,'start_ids':starts,'target':target,'paths':found})
reachability=[]
for group,name in enumerate(['Larch','Cobalt','Reed','Sable','Cedar','ACCT-N','ACCT-S','EGRET-CN','DELTA-8']):
 labels=[name]+(['白鹭项目'] if group==7 else [])
 starts=sorted({i for i,e in entities.items() if any(label.casefold() in e['canonical'].casefold() for label in labels)}|{a['entity_id'] for a in aliases if a['alias_norm']==name.casefold()})
 target=f'REPLAY-{group}-632';entity_paths=[];scalar_paths=[];quote_paths=[]
 for start in starts:
  queue=deque([(start,[])]);seen={start}
  while queue:
   identity,path=queue.popleft()
   if len(path)>=3:continue
   for f in facts:
    if f['subject_entity_id']!=identity:continue
    extended=path+[f['fact_id']]
    if f.get('object_value') and target in f['object_value']:scalar_paths.append({'start':start,'facts':extended})
    if any(e['fact_id']==f['fact_id'] and target in (e.get('quote') or '') for e in edges):quote_paths.append({'start':start,'facts':extended})
    other=f.get('object_entity_id')
    if other:
     if target in entities[other]['canonical']:entity_paths.append({'start':start,'facts':extended})
     if other not in seen:seen.add(other);queue.append((other,extended))
 reachability.append({'group':group,'start_candidates':[{'id':i,'canonical':entities[i]['canonical']} for i in starts],'target':target,'entity_terminal_paths':entity_paths,'scalar_terminal_paths':scalar_paths,'paths_with_target_in_evidence_quote':quote_paths})
result={'notes':len(notes),'graph_entities':len(entities),'facts':len(facts),'evidence_links':len(edges),'links_with_quotes':sum(bool(e.get('quote')) for e in edges),'facts_with_unknown_valid_from':sum(f['valid_from'] is None for f in facts),'entities_used_by_multiple_source_groups':[{'entity_id':i,'canonical':entities[i]['canonical'],'source_groups':sorted(g)} for i,g in entity_groups.items() if len(g)>1],'canonical_fragments':{key:[{'entity_id':i,'canonical':e['canonical']} for i,e in entities.items() if key in e['canonical']] for key in ['ACCT-N','ACCT-S','EGRET-CN','DELTA-8']},'stored_three_edge_recovery_paths':paths,'source_name_variant_reachability':reachability,'limits':['Graph paths start separately from each exact canonical or exact-alias candidate and use only stored directed entity edges. No fragments are merged. This does not simulate native canonical-priority resolution, validity filters, query budgets, or semantic entailment.','Shared names can denote one real actor or different actors; multiple source groups alone do not prove a wrong merge.','Canonical name variants remain separate unless the caller provides identity authority. The wider diagnostic starts from each name or identifier variant separately, never joins nodes, and reports scalar terminals and quote-only evidence separately. No diagnostic joins or oracle answers are supplied to the agent.']}
assert result == read('representation-diagnostics.json')
print(json.dumps({k:result[k] for k in ['notes','graph_entities','facts','evidence_links','links_with_quotes','facts_with_unknown_valid_from']}));print(json.dumps([{'group':v['group'],'entity_paths':len(v['entity_terminal_paths']),'scalar_paths':len(v['scalar_terminal_paths']),'quote_paths':len(v['paths_with_target_in_evidence_quote'])} for v in reachability]))
