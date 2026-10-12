"""Measure actual tool use and evidence reachability without judging answer semantics."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics

from .tools import project_note


def initial_coverage(root,workload):
    rows=[]
    for query in workload['queries']:
        notes=json.loads((root/'initial'/(query['case_id']+'.json')).read_text())['notes']
        body='\n'.join(n['text'] for n in notes)
        structured=json.dumps([note_evidence(project_note(n,'notes')) for n in notes])
        facts=workload['oracle'][query['case_id']]['facts']
        rows.append({'case_id':query['case_id'],'split':query['split'],'expected':facts,
                     'body_missing':[f for f in facts if f not in body],
                     'structured_missing':[f for f in facts if f not in structured]})
    (root/'initial-fact-coverage.json').write_text(json.dumps(rows,indent=2)+'\n')
    return rows


def citation_sources(root):
    """Build an offline provenance index. Never supply this index to the agent."""
    sources={}
    for note in json.loads((root/'notes.json').read_text()):
        sources[note['note_id']]={e['source']['message_id'] for e in note.get('source_ref',{}).get('evidence',[]) if e.get('source',{}).get('message_id')}
    for path in (root/'ingest').glob('*.json'):
        sources[json.loads(path.read_text())['document']['doc_id']]={path.stem}
    for edge in json.loads((root/'graph_fact_evidence.json').read_text()):
        sources.setdefault(edge['fact_id'],set()).update(sources.get(edge['note_id'],set()))
    def chunks(value,doc=None):
        if isinstance(value,dict):
            doc=value.get('doc_id',doc)
            if doc in sources:
                for key in ('chunk_id','span_id','source_span_id','source_record_id'):
                    if isinstance(value.get(key),str):sources.setdefault(value[key],set()).update(sources[doc])
            for item in value.values():chunks(item,doc)
        elif isinstance(value,list):
            for item in value:chunks(item,doc)
    for path in (root/'cases').glob('*/*.json'):
        for step in json.loads(path.read_text()).get('trace',[]):
            for tool in step['tools']:chunks(tool['result'])
    return sources


def identifiers(value):
    """Collect returned evidence identifiers, not arbitrary UUIDs in diagnostics."""
    found=set()
    if isinstance(value,dict):
        for key,item in value.items():
            if key in ('note_id','doc_id','chunk_id','fact_id','span_id','source_span_id','source_record_id') and isinstance(item,str):found.add(item)
            elif key=='evidence_note_ids':found.update(item)
            found.update(identifiers(item))
    elif isinstance(value,list):
        for item in value:found.update(identifiers(item))
    return found


def note_evidence(note):
    result={'text':note.get('text'),'structured':note.get('structured'),
            'quotes':[e['quote'] for e in note.get('source_ref',{}).get('evidence',[]) if 'quote' in e]}
    if 'source_evidence' in note:result['originals']=[s['excerpt']['excerpt'] for s in note['source_evidence']]
    return result


def evidence_payload(name,result):
    """Exclude query echoes and diagnostic strings from fact-availability checks."""
    if name in ('search_notes','get_search'):
        return [{'summary':i.get('summary'),'text':i.get('text')} for i in result['items']]
    if name=='get_note':return note_evidence(result)
    if name=='search_documents':return [i.get('snippet') for i in result['items']]
    if name=='read_document':return result['excerpt']['excerpt']
    if name=='query_graph':return [{'subject':result.get('subject'),'predicate':f.get('predicate'),'object':f.get('object'),**({'evidence_quotes':f['evidence_quotes']} if 'evidence_quotes' in f else {})} for f in result.get('facts',[])]
    raise ValueError('Unknown evidence tool: '+name)


def case_metrics(case,initial):
    initial=[project_note(n,'notes') for n in initial]
    visible=identifiers(initial);graph_objects=set();graph_evidence=set();provenance={}
    counts=Counter();requests=Counter();errors=[];hops=[];source_links=[];evidence_follows=[]
    payloads=[json.dumps([note_evidence(n) for n in initial],ensure_ascii=False)]
    for step in case.get('trace',[]):
        for tool in step['tools']:
            name=tool['name'];args=tool['arguments'];result=tool['result'];counts[name]+=1
            requests[(name,json.dumps(args,sort_keys=True))]+=1
            if 'error' in result:
                errors.append({'tool':name,'arguments':args,'error':result['error']});continue
            if name=='query_graph':
                subject=result.get('subject',{}).get('entity_id')
                if subject in graph_objects:
                    hops.append({'entity_id':subject,'requested_by':'id' if args.get('entity_id') else 'surface','facts':len(result.get('facts',[]))})
                for fact in result.get('facts',[]):
                    entity=fact.get('object',{}).get('entity')
                    if entity:graph_objects.add(entity['entity_id'])
                    graph_evidence.update(fact.get('evidence_note_ids',[]))
            if name=='get_note':
                if args['note_id'] in graph_evidence:evidence_follows.append(args['note_id'])
                for evidence in result.get('source_ref',{}).get('evidence',[]):
                    source=evidence.get('source',{});mid=source.get('message_id')
                    if mid:provenance.setdefault(mid,[]).append({'note_id':args['note_id'],'source_hash':source.get('content_hash'),'quote':evidence.get('quote','')})
            originals=([result] if name=='read_document' else result.get('source_evidence',[]) if name=='get_note' else [])
            for original in originals:
                metadata=original['metadata'];excerpt=original['excerpt'];mid=metadata.get('source_ref',{}).get('evidence_id')
                for source in provenance.get(mid,[]):
                    source_links.append({**source,'message_id':mid,'doc_id':metadata['doc_id'],
                                         'hash_matches':source['source_hash']==metadata['content_hash'],
                                         'quote_in_excerpt':source['quote'] in excerpt['excerpt'],
                                         'verified':excerpt['verification']['verified']})
            visible.update(identifiers(result));payloads.append(json.dumps(evidence_payload(name,result),ensure_ascii=False))
    expected=case['expected']['facts'];available='\n'.join(payloads)
    return {'condition':case['condition'],'case_id':case['query']['case_id'],'split':case['query']['split'],'lane':case['query']['lane'],
            'status':case['status'],'strict_correct':case.get('strict_correct',False),
            'answer_sha256':hashlib.sha256(case.get('text','').encode()).hexdigest(),
            'tool_counts':dict(counts),'tool_errors':errors,'graph_object_follows':hops,
            'repeated_identical_tool_calls':sum(n-1 for n in requests.values()),
            'graph_evidence_note_follows':evidence_follows,'source_links':source_links,
            'unseen_citations':[c for c in case.get('citations',[]) if c not in visible],
            'expected_identifiers_seen':[f for f in expected if f in available],
            'expected_identifiers_unseen':[f for f in expected if f not in available],
            'seconds':case.get('seconds'),'model_rounds':len(case.get('trace',[])),
            'chat_cost_usd':sum((s['response'].get('usage') or {}).get('cost',0) or 0 for s in case.get('trace',[])),
            'format_compliant':case.get('format_compliant',True)}


def analyze(root):
    root=Path(root);rows=[]
    sources=citation_sources(root);workload=json.loads((root/'workload.json').read_text())
    initial_coverage(root,workload)
    reviews=json.loads((root/'answer-reviews.json').read_text()) if (root/'answer-reviews.json').exists() else []
    review_by={(r.get('phase','primary'),r['condition'],r['case_id']):r for r in reviews}
    for folder,phase in [('cases','primary'),('finalizations','finalization'),('paged-cases','paged')]:
        for path in sorted((root/folder).glob('*/*.json')):
            case=json.loads(path.read_text())
            if phase=='finalization':
                original=json.loads((root/('paged-cases' if case['condition']=='paged' else 'cases')/case['condition']/path.name).read_text())
                response=json.loads((root/'finalization-responses'/case['condition']/path.name).read_text())
                case['trace']=original['trace']+[{'response':response['response'],'tools':[]}]
                case['seconds']=case['seconds']+original['seconds'] if original.get('seconds') is not None else None
            initial=json.loads((root/'initial'/(case['query']['case_id']+'.json')).read_text())['notes']
            row=case_metrics(case,initial);row['phase']=phase;review=review_by.get((phase,row['condition'],row['case_id']))
            project_index=int(row['case_id'].split('-')[1])
            expected_sources={x['evidence_id'] for x in workload['items'][project_index*4:project_index*4+4]}
            row['citation_sources']={c:sorted(sources.get(c,set())) for c in case.get('citations',[])}
            row['citations_with_target_project_source']=[c for c in case.get('citations',[]) if sources.get(c,set()) & expected_sources]
            row['citations_only_from_other_projects']=[c for c in case.get('citations',[]) if sources.get(c,set()) and not sources[c] & expected_sources]
            if review:
                if review['answer_sha256']!=row['answer_sha256']:raise ValueError('Review does not match answer')
                row['reviewed_correct']=review['correct'];row['review_reason']=review['reason']
            rows.append(row)
    finalized={(r['condition'],r['case_id']):r for r in rows if r['phase']=='finalization'}
    summary=[]
    for stage in ['primary','with_finalization']:
      for condition in ['initial','notes','source','graph','both']:
        for split in ['test','dev']:
            group=[r for r in rows if r['condition']==condition and r['split']==split and r['phase']=='primary']
            if stage=='with_finalization':group=[finalized.get((r['condition'],r['case_id']),r) for r in group]
            times=[r['seconds'] for r in group if r['seconds'] is not None]
            summary.append({'stage':stage,'condition':condition,'split':split,'answers':len(group),
                            'completed':sum(r['status']=='completed' for r in group),
                            'strict_correct':sum(r['strict_correct'] for r in group),
                            'reviewed':sum('reviewed_correct' in r for r in group),
                            'reviewed_correct':sum(r.get('reviewed_correct',False) for r in group),
                            'tool_calls':sum(sum(r['tool_counts'].values()) for r in group),
                            'tool_errors':sum(len(r['tool_errors']) for r in group),
                            'repeated_identical_tool_calls':sum(r['repeated_identical_tool_calls'] for r in group),
                            'cases_with_document_reads':sum(r['tool_counts'].get('read_document',0)>0 or bool(r['source_links']) for r in group),
                            'cases_with_verified_provenance_follow':sum(any(l['hash_matches'] and l['verified'] and l['quote_in_excerpt'] for l in r['source_links']) for r in group),
                            'cases_with_graph_queries':sum(r['tool_counts'].get('query_graph',0)>0 for r in group),
                            'cases_with_object_entity_follows':sum(bool(r['graph_object_follows']) for r in group),
                            'cases_with_graph_evidence_follows':sum(bool(r['graph_evidence_note_follows']) for r in group),
                            'cases_with_unseen_citations':sum(bool(r['unseen_citations']) for r in group),
                            'chat_cost_usd':sum(r['chat_cost_usd'] for r in group),
                            'latency_samples':len(times),'median_seconds':statistics.median(times) if times else None})
    output={'summary':summary,'cases':rows,'limitations':['Identifier presence is diagnostic, not proof of an entailment or a correct subject binding.','A provenance follow requires a prior get_note, matching source identity/hash, and verified excerpt containing its quote.','An object follow can return zero facts; this measures actual traversal attempts, not useful multi-hop inference.','Manual semantic reviews are bound to the exact answer hash; raw strict scores are unchanged.','A citation from another project can support an explicit comparison or decoy exclusion; inspect the claim before classifying it as an attribution error.']}
    (root/'analysis.json').write_text(json.dumps(output,indent=2)+'\n')
    return output
