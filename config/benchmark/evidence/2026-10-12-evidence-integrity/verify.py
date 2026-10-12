"""Verify the matched evidence-integrity trial without model or database access."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[3]/'scripts'))
from benchmark_agent.analysis import analyze
from benchmark_agent.runner import parse_answer
from benchmark_agent.tools import project_note,schemas
from grounding import audit_absence,summarize_quality


def read(name):return json.loads((ROOT/name).read_text())
def lines(name):return [json.loads(line) for line in gzip.decompress((ROOT/name).read_bytes()).splitlines()]
def digest(data):return hashlib.sha256(data).hexdigest()


manifest=read('manifest.json')
assert set(manifest)=={p.name for p in ROOT.iterdir() if p.is_file() and p.name!='manifest.json'}
for name,value in manifest.items():assert digest((ROOT/name).read_bytes())==value,name
work=read('workload.json');protocol=read('protocol.json')
assert work==json.loads((ROOT.parent/'2026-10-11-agent-evidence/workload.json').read_text())
assert protocol['dimensions']==4096 and protocol['agent_policy']=='bounded-v2'
assert protocol['max_rounds']==12 and protocol['max_tool_calls']==24
cases=lines('cases.jsonl.gz');receipts=lines('provider-receipts.jsonl.gz')
assert len(cases)==100
assert {(c['condition'],c['query']['case_id']) for c in cases}=={(condition,q['case_id']) for condition in ['notes','source','graph','both','initial'] for q in work['queries']}
initial={r['case_id']:r['value'] for r in lines('initial.jsonl.gz')}
ingest={r['evidence_id']:r['value'] for r in lines('ingest.jsonl.gz')}
sources={s['evidence_id']:s for s in work['items']};by_response={};extractions={}
for row in receipts:
    request,response=row['request'],row['response']
    if 'input' in request:
        assert request['model']=='qwen/qwen3-embedding-8b' and request['dimensions']==4096
        assert all(len(v['embedding'])==4096 for v in response['data'])
    else:
        assert request['model']=='deepseek/deepseek-v4.1-flash'
        assert request['max_tokens']==393216 and request['reasoning']['effort']=='max'
        assert request['provider']['only']==['deepseek']
        by_response[response['id']]=row
        if request['messages'][0]['content'].startswith('You are a memory extraction engine'):
            messages=json.loads(request['messages'][-1]['content'].split('Here are the messages as JSON:\n',1)[1])
            assert len(messages)==1 and 'source_document' not in messages[0]
            m=messages[0];assert m['content']==sources[m['msg_id']]['text']
            assert m['msg_id'] not in extractions,'No favorable extraction resampling'
            extractions[m['msg_id']]=json.loads(response['choices'][0]['message']['content'])
assert set(extractions)==set(sources)
for eid,event in ingest.items():
    assert [n['text'] for n in event['event']['extracted']['notes']]==[n['text'] for n in extractions[eid]['notes']][:3]
for case in cases:
    key=case['query']['case_id'];condition=case['condition'];trace=case['trace']
    assert case['expected']==work['oracle'][key]
    assert case['status'] in ('completed','invalid_answer','round_budget_exhausted')
    assert len(trace)<=12 and case['tool_calls']<=24
    assert case['tool_calls']==sum(len(step['tools']) for step in trace)
    first=by_response[trace[0]['response']['id']]['request']
    context={'question':case['query']['question'],'initial_memories':[project_note(n,'notes') for n in initial[key]['notes']]}
    if condition!='initial':context['initial_search_id']=initial[key]['search']['search_id']
    assert json.loads(first['messages'][1]['content'])==context
    allowed={t['function']['name'] for t in schemas(condition)}
    executed=0
    for step in trace:
        receipt=by_response[step['response']['id']]
        closing=step['turn']==11 or executed>=24 or condition=='initial'
        assert ('tools' not in receipt['request'])==closing
        if closing:assert not step['tools']
        executed+=len(step['tools'])
        assert step['response']==receipt['response']
        calls=step['response']['choices'][0]['message'].get('tool_calls') or []
        assert len(calls)==len(step['tools'])+len(step.get('unexecuted_tool_calls',[]))
        for tool in step['tools']:
            assert tool['name'] in allowed
            result=tool['result']
            if tool['name']=='get_note' and condition not in ('source','both'):assert 'source_ref' not in result
            if tool['name']=='read_document' and 'error' not in result:
                excerpt=result['excerpt'];metadata=result['metadata'];eid=metadata['source_ref']['evidence_id']
                assert excerpt['verification']['verified']
                assert sources[eid]['text'].encode()[excerpt['start_offset']:excerpt['end_offset']].decode()==excerpt['excerpt']
                assert metadata['content_hash']==ingest[eid]['document']['content_hash']
    if case['status']=='completed':
        parsed=parse_answer(trace[-1]['response']['choices'][0]['message']['content'])
        assert all(case[k]==v for k,v in parsed.items())
    if condition=='initial':assert len(trace)==1 and case['tool_calls']==0
reviews=read('answer-reviews.json');assert len(reviews)==100
for case in cases:
    review=next(r for r in reviews if (r['condition'],r['case_id'])==(case['condition'],case['query']['case_id']))
    assert review['answer_sha256']==digest(case.get('text','').encode()) and review['reason']
case_by_key={(c['condition'],c['query']['case_id']):c for c in cases}
metrics_by_key={(m['condition'],m['case_id']):m for m in read('analysis.json')['cases']}
for issue in read('citation-issues.json'):
    key=(issue['condition'],issue['case_id']);assert issue['citation'] in case_by_key[key]['citations']
    observed=metrics_by_key[key]['citation_sources'].get(issue['citation'],[])
    for source in issue.get('source_evidence_ids', [issue['source']] if 'source' in issue else []):assert source in observed
for issue in read('factual-issues.json'):
    assert (issue['condition'],issue['case_id']) in case_by_key
    assert issue['counterevidence'] in sources[issue['counterevidence_id']]['text']
notes_by_id={n['note_id']:n for n in read('notes.json')}
for group in read('source-occurrence-groups.json'):
    assert len(group['notes'])>1
    assert len({n['note_id'] for n in group['notes']})==len(group['notes'])
    assert len({tuple(n['sources']) for n in group['notes']})==len(group['notes'])
    for note in group['notes']:
        actual=notes_by_id[note['note_id']]
        assert actual['text']==group['text']
        assert sorted({e['source']['message_id'] for e in actual['source_ref']['evidence']})==note['sources']
for prefix in ['', 'final-']:

    docs={d['doc_id']:d for d in read(prefix+'source-documents.json')}
    assert len(docs)==20
    assert {d['source_ref']['evidence_id'] for d in docs.values()}==set(sources)
    for doc in docs.values():
        eid=doc['source_ref']['evidence_id']
        assert doc['content'].encode()==sources[eid]['text'].encode()
        assert doc['content_hash']==ingest[eid]['document']['content_hash']
        assert doc['created_at']==doc['updated_at'] and doc['status']=='active'
    for chunk in read(prefix+'source-chunks.json'):
        assert docs[chunk['doc_id']]['content'].encode()[chunk['start_offset']:chunk['end_offset']].decode()==chunk['chunk_text']
    for note in read('notes.json'):
        for evidence in note['source_ref']['evidence']:
            source=evidence['source'];pointer=source['document'];doc=docs[pointer['ref']['doc_id']]
            position=pointer['locator']['position'];eid=source['message_id']
            assert doc['source_ref']['evidence_id']==eid
            assert pointer['state']['content_hash']==doc['content_hash']
            assert doc['content'].encode()[position['start']:position['end']].decode()==sources[eid]['text']
for name in ['source-integrity.json','final-source-integrity.json']:
    rows=read(name);assert len(rows)==20
    assert all(all(row[k] for k in ['exact_original_bytes','receipt_hash_matches','chunk_offsets_match','first_insert_only','active']) for row in rows)
for name in ['source-pointers.json','final-source-pointers.json']:
    rows=read(name);assert rows
    assert {r['note_id'] for r in rows}=={n['note_id'] for n in read('notes.json')}
    assert all(r['hash_matches'] and r['message_span_matches'] and r['source_matches'] for r in rows)
assert read('native-notes.json')==read('final-native-notes.json')
assert all(note['hit_count']==0 for note in read('final-native-notes.json'))
assert read('embedding-state.json')==read('final-embedding-state.json')
assert all(s['dimensions']==[4096] for s in read('embedding-state.json').values())
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    for name in ['notes.json','graph_fact_evidence.json','workload.json','answer-reviews.json']:(root/name).write_bytes((ROOT/name).read_bytes())
    def save(path,value):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))
    for key,value in ingest.items():save(root/'ingest'/(key+'.json'),value)
    for key,value in initial.items():save(root/'initial'/(key+'.json'),value)
    for case in cases:save(root/'cases'/case['condition']/(case['query']['case_id']+'.json'),case)
    assert analyze(root)==read('analysis.json')
    assert audit_absence(root)==read('absence-grounding.json')
assert summarize_quality(read('analysis.json'),reviews,read('citation-issues.json'),read('absence-grounding.json'))==read('quality-summary.json')
attempts={row['path']:row['value'] for row in lines('attempts.jsonl.gz')}
interrupted=attempts['attempts/provider-connection-loss/progress.json']
resumed=case_by_key['notes','memory-4-2']
assert resumed['trace'][:2]==interrupted[:2] and resumed['resumed_recorded_turns']==2
assert interrupted[2]['response']['choices'][0]['finish_reason']=='error' and not interrupted[2]['tools']
assert resumed['seconds'] is None
usage=lines('usage.jsonl.gz');accounting=read('accounting.json')
assert [r['ordinal'] for r in usage]==list(range(2600,2600+len(usage)))
assert not any(r['status']=='in_flight' for r in usage)
assert {r['ordinal'] for r in receipts}=={r['ordinal'] for r in usage if r['status']=='completed'}
paid=sum((r.get('usage') or {}).get('cost',0) or 0 for r in usage)
assert math.isclose(paid,accounting['new_paid_usd'])
assert math.isclose(accounting['prior_paid_usd']+paid,accounting['cumulative_paid_usd'])
assert accounting['cumulative_paid_usd']<=accounting['conservative_exposure_usd']<=10
print(json.dumps({'cases':len(cases),'original_sources':len(sources),'extraction_samples':len(extractions),'cumulative_paid_usd':accounting['cumulative_paid_usd']}))
