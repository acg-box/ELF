"""Verify frozen inputs, native tool evidence, review lineage, and bounded costs."""
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
from benchmark_agent.tools import project_note,schemas
from benchmark_agent.runner import parse_answer


def read(name):
    return json.loads((ROOT/name).read_text())


def lines(name):
    return [json.loads(line) for line in gzip.decompress((ROOT/name).read_bytes()).splitlines()]


manifest=read('manifest.json')
assert set(manifest)=={p.name for p in ROOT.iterdir() if p.is_file() and p.name!='manifest.json'}
for name,digest in manifest.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
cases=lines('cases.jsonl.gz');finals=lines('finalizations.jsonl.gz');paged=lines('paged-cases.jsonl.gz')
assert len(cases)==100
assert len({(c['condition'],c['query']['case_id']) for c in cases})==100
assert all(c['status'] in ('completed','tool_budget_exhausted','round_budget_exhausted') or (c['condition']=='initial' and c['status']=='invalid_answer') for c in cases)
initial={r['case_id']:r['value'] for r in lines('initial.jsonl.gz')}
ingest={r['evidence_id']:r['value'] for r in lines('ingest.jsonl.gz')}
workload=read('workload.json');sources={s['evidence_id']:s['text'] for s in workload['items']}
receipts=lines('provider-receipts.jsonl.gz');by_response={}
for receipt in receipts:
    request,response=receipt['request'],receipt['response']
    if 'input' in request:
        assert request['model']=='qwen/qwen3-embedding-8b' and request['dimensions']==4096
        assert all(len(v['embedding'])==4096 for v in response['data'])
    else:
        assert request['model']=='deepseek/deepseek-v4.1-flash'
        assert request['max_tokens']==393216 and request['reasoning']['effort']=='max'
        assert request['provider']['only']==['deepseek']
        by_response[response['id']]=receipt
assert {c['query']['case_id'] for c in paged}=={'memory-0-1','memory-2-1','memory-3-1','memory-4-0'}
for case in cases+paged:
    key=case['query']['case_id'];condition=case['condition']
    assert case['expected']==workload['oracle'][key]
    if case['trace']:
        first=by_response[case['trace'][0]['response']['id']]['request']
        expected={'question':case['query']['question'],'initial_memories':[project_note(n,'notes') for n in initial[key]['notes']]}
        if condition=='paged':expected['initial_search_id']=initial[key]['search']['search_id']
        assert json.loads(first['messages'][1]['content'])==expected
    allowed={t['function']['name'] for t in schemas(condition)}
    for step in case['trace']:
        assert step['response']==by_response[step['response']['id']]['response']
        for tool in step['tools']:
            assert tool['name'] in allowed
            result=tool['result']
            if tool['name']=='get_note' and condition not in ('source','both'):assert 'source_ref' not in result
            if tool['name']=='read_document' and 'error' not in result:
                excerpt=result['excerpt'];metadata=result['metadata'];eid=metadata['source_ref']['evidence_id']
                assert excerpt['verification']['verified']
                assert sources[eid].encode()[excerpt['start_offset']:excerpt['end_offset']].decode()==excerpt['excerpt']
                assert metadata['content_hash']==ingest[eid]['document']['content_hash']
    if case['status']=='completed':
        parsed=parse_answer(case['trace'][-1]['response']['choices'][0]['message']['content'])
        assert all(case.get(k,True if k=='format_compliant' else None)==v for k,v in parsed.items())
    if case['status']=='invalid_answer':
        assert case['text']==case['trace'][-1]['response']['choices'][0]['message']['content']
        assert not case['format_compliant']
    if condition=='initial':assert len(case['trace'])==1 and case['tool_calls']==0
original={(c['condition'],c['query']['case_id']):c for c in cases+paged}
final_raw={(r['condition'],r['case_id']):r['value'] for r in lines('finalization-responses.jsonl.gz')}
for final in finals:
    response=final_raw[final['condition'],final['query']['case_id']]['response']
    assert response==by_response[response['id']]['response']
    assert 'tools' not in by_response[response['id']]['request']
    assert all(final[k]==v for k,v in parse_answer(response['choices'][0]['message']['content']).items())
    prior=original[final['condition'],final['query']['case_id']]
    assert prior['status'] in ('tool_budget_exhausted','round_budget_exhausted')
reviews=read('answer-reviews.json')
assert len(reviews)==len(cases)+len(finals)+len(paged)
for phase,rows in [('primary',cases),('finalization',finals),('paged',paged)]:
    for case in rows:
        review=next(r for r in reviews if (r.get('phase','primary'),r['condition'],r['case_id'])==(phase,case['condition'],case['query']['case_id']))
        assert review['answer_sha256']==hashlib.sha256(case.get('text','').encode()).hexdigest()
        assert review['reason']
assert all(s['exact_original_bytes'] and s['receipt_hash_matches'] for s in read('source-integrity.json'))
assert len(read('source-integrity.json'))==20
assert len(read('final-source-integrity.json'))==20
assert all(all(row[k] for k in ['exact_original_bytes','receipt_hash_matches','chunk_offsets_match','first_insert_only']) for row in read('final-source-integrity.json'))
prior_notes=json.loads((ROOT.parent/'2026-10-11-memory-consistency-4096/baseline-extraction-diagnostics.json').read_text())['notes']
assert sorted(n['text'] for n in read('notes.json'))==sorted(n['text'] for n in prior_notes)
assert all(s['dimensions']==[4096] for s in read('embedding-state.json').values())
assert read('embedding-state.json')==read('final-embedding-state.json')
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    for name in ['notes.json','graph_fact_evidence.json','workload.json','answer-reviews.json']:(root/name).write_bytes((ROOT/name).read_bytes())
    def save(path,value):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))
    for key,value in ingest.items():save(root/'ingest'/(key+'.json'),value)
    for key,value in initial.items():save(root/'initial'/(key+'.json'),value)
    for c in cases:save(root/'cases'/c['condition']/(c['query']['case_id']+'.json'),c)
    for c in finals:save(root/'finalizations'/c['condition']/(c['query']['case_id']+'.json'),c)
    for c in paged:save(root/'paged-cases'/c['condition']/(c['query']['case_id']+'.json'),c)
    for r in lines('finalization-responses.jsonl.gz'):save(root/'finalization-responses'/r['condition']/(r['case_id']+'.json'),r['value'])
    measured=analyze(root)
    assert measured==read('analysis.json')
    for row in measured['cases']:
        if row.get('reviewed_correct'):assert not row['expected_identifiers_unseen'],(row['phase'],row['condition'],row['case_id'])
attempts={r['path']:r['value'] for r in lines('attempts.jsonl.gz')}
resumed=original['source','memory-2-1']
assert resumed['resumed_recorded_turns']==5
assert any(isinstance(v,list) and v==resumed['trace'][:5] for v in attempts.values())
usage=lines('usage.jsonl.gz');accounting=read('accounting.json')
assert [r['ordinal'] for r in usage]==list(range(1577,1577+len(usage)))
assert not any(r['status']=='in_flight' for r in usage)
assert {r['ordinal'] for r in receipts}=={r['ordinal'] for r in usage if r['status']=='completed'}
paid=sum((r.get('usage') or {}).get('cost',0) or 0 for r in usage)
assert math.isclose(paid,accounting['new_paid_usd'])
assert math.isclose(accounting['prior_paid_usd']+paid,accounting['cumulative_paid_usd'])
assert accounting['cumulative_paid_usd']<=accounting['conservative_exposure_usd']<=10
print(json.dumps({'primary_and_initial_control_cases':len(cases),'cached_expansion_diagnostics':len(paged),'evidence_only_finalizations':len(finals),'cumulative_paid_usd':accounting['cumulative_paid_usd']}))
