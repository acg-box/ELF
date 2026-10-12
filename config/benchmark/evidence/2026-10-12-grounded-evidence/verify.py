"""Verify the retained grounded-evidence trial without model or database access."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[3] / 'scripts'))
from benchmark_agent.runner import GROUNDED_PROMPT, parse_answer
from benchmark_agent.tools import project_note, schemas
from binding_audit import audit


def read(name):
    return json.loads((ROOT / name).read_text())


def lines(name):
    return [json.loads(line) for line in gzip.decompress((ROOT / name).read_bytes()).splitlines()]


def digest(value):
    return hashlib.sha256(value).hexdigest()


manifest = read('manifest.json')
assert set(manifest) == {p.name for p in ROOT.iterdir() if p.is_file() and p.name != 'manifest.json'}
for name, value in manifest.items():
    assert digest((ROOT / name).read_bytes()) == value, name
work, protocol = read('workload.json'), read('protocol.json')
assert work == json.loads((ROOT.parents[1] / 'grounded-evidence/workload.json').read_text())
prior = json.loads((ROOT.parent / '2026-10-12-evidence-integrity/workload.json').read_text())
assert work['items'][:20] == prior['items'] and work['queries'][:20] == prior['queries']
for key, value in prior['oracle'].items():
    assert work['oracle'][key] == value
assert protocol['dimensions'] == 4096 and protocol['agent_policy'] == 'grounded-v3'
assert protocol['agent_prompt'] == GROUNDED_PROMPT
assert protocol['max_rounds'] == 12 and protocol['max_tool_calls'] == 24
assert protocol['max_output_tokens'] == 393216
assert read('run-execution-policy.json')['workers'] == 2
assert read('run-invocation-completed.json')['remaining'] == 0
cases, receipts = lines('cases.jsonl.gz'), lines('provider-receipts.jsonl.gz')
conditions = ['notes', 'source', 'graph', 'both', 'initial']
assert len(cases) == 132
assert {(c['condition'], c['query']['case_id']) for c in cases} == {
    (row['condition'], row['case_id']) for row in read('execution-plan.json')['selected']}
initial = {row['case_id']: row['value'] for row in lines('initial.jsonl.gz')}
assert len(initial) == 36
by_response = {}
extractions = {}
source_items = {item["evidence_id"]: item for item in work["items"]}
for row in receipts:
    request, response = row['request'], row['response']
    if 'input' in request:
        assert request['model'] == 'qwen/qwen3-embedding-8b' and request['dimensions'] == 4096
        assert all(len(item['embedding']) == 4096 for item in response['data'])
    else:
        assert request['model'] == 'deepseek/deepseek-v4.1-flash'
        assert request['max_tokens'] == 393216 and request['reasoning']['effort'] == 'max'
        assert request['provider']['only'] == ['deepseek']
        by_response[response['id']] = row
        if request['messages'][0]['content'].startswith('You are a memory extraction engine'):
            messages = json.loads(request['messages'][-1]['content'].split('Here are the messages as JSON:\n', 1)[1])
            assert len(messages) == 1 and 'source_document' not in messages[0]
            message = messages[0]
            assert message['content'] == source_items[message['msg_id']]['text']
            assert message['msg_id'] not in extractions
            extractions[message['msg_id']] = json.loads(response['choices'][0]['message']['content'])
assert set(extractions) == set(source_items)
for row in lines('ingest.jsonl.gz'):
    event = row['value']['event']
    assert event['ingestion_profile'] == {'id': 'default', 'version': 5}
    assert [note['text'] for note in event['extracted']['notes']] == [note['text'] for note in extractions[row['evidence_id']]['notes']][:3]
notes = {row['note_id']: row for row in read('native-notes.json')}
documents = {row['doc_id']: row for row in read('source-documents.json')}
for document in documents.values():
    original = source_items[document['source_ref']['evidence_id']]['text']
    assert document['content'].encode() == original.encode()
    assert document['created_at'] == document['updated_at'] and document['status'] == 'active'
for chunk in read('source-chunks.json'):
    original = documents[chunk['doc_id']]['content'].encode()
    assert original[chunk['start_offset']:chunk['end_offset']].decode() == chunk['chunk_text']
for note in notes.values():
    for evidence in note['source_ref'].get('evidence', []):
        pointer = evidence['source']['document']
        original = documents[pointer['ref']['doc_id']]
        span = pointer['locator']['position']
        assert original['content_hash'] == pointer['state']['content_hash']
        assert original['content'].encode()[span['start']:span['end']].decode() == source_items[evidence['source']['message_id']]['text']
reviews = {(row['condition'], row['case_id']): row for row in read('answer-reviews.json')}
assert len(reviews) == len(cases)
audits = []
for case in cases:
    key, condition, trace = case['query']['case_id'], case['condition'], case['trace']
    assert case['expected'] == work['oracle'][key]
    assert len(trace) <= 12 and case['tool_calls'] <= 24
    assert case['tool_calls'] == sum(len(step['tools']) for step in trace)
    first = by_response[trace[0]['response']['id']]['request']
    context = {'question': case['query']['question'],
               'initial_memories': [project_note(note, 'notes') for note in initial[key]['notes']]}
    if condition != 'initial':
        context['initial_search_id'] = initial[key]['search']['search_id']
    assert first['messages'][0]['content'] == GROUNDED_PROMPT
    assert json.loads(first['messages'][1]['content']) == context
    allowed = {tool['function']['name'] for tool in schemas(condition, True)}
    for step in trace:
        assert step['response'] == by_response[step['response']['id']]['response']
        assert all(tool['name'] in allowed for tool in step['tools'])
    if case['status'] == 'completed':
        final = parse_answer(trace[-1]['response']['choices'][0]['message']['content'])
        for field in ('text', 'supported', 'citations', 'claims'):
            assert case[field] == final.get(field, [] if field == 'claims' else None)
    native = case.get('claim_bindings')
    if native:
        assert native['semantic_support'] == 'not_evaluated'
        assert len(native['claims']) == len(case['claims'])
        for claim, binding in zip(case['claims'], native['claims']):
            assert len(binding['citation_verified']) == len(claim['citations'])
            for citation, verified in zip(claim['citations'], binding['citation_verified']):
                if not verified:
                    continue
                quote = citation['quote']
                assert quote.strip() and len(quote.encode()) <= 8192
                if citation['kind'] == 'note':
                    assert quote in notes[citation['note_id']]['text']
                else:
                    document = documents[citation['doc_id']]
                    assert document['content_hash'] == citation['content_hash']
                    assert quote in document['content']
            enough = claim['state'] == 'unknown' or len(claim['citations']) >= (2 if claim['state'] == 'conflict' else 1)
            assert binding['binding_verified'] == (enough and all(binding['citation_verified']))
    review = reviews[(condition, key)]
    assert review['answer_sha256'] == digest(case.get('text', '').encode())
    assert review['claims_sha256'] == digest(json.dumps(case.get('claims'), sort_keys=True, ensure_ascii=False).encode())
    audits.append(audit(case, initial[key]['notes']))
attempts = {row['path']: row['value'] for row in lines('attempts.jsonl.gz')}
resumed = next(case for case in cases if case['condition'] == 'both' and case['query']['case_id'] == 'memory-3-1')
assert resumed['resumed_recorded_turns'] == 4
assert resumed['trace'][:4] == attempts['attempts/both/memory-3-1-http520/progress.json']
resumed = next(case for case in cases if case['condition'] == 'notes' and case['query']['case_id'] == 'memory-4-1')
failed_trace = attempts['attempts/notes/memory-4-1-provider-error/progress.json']
assert failed_trace[-1]['response']['choices'][0]['finish_reason'] == 'error'
assert failed_trace[-1]['response']['choices'][0]['message']['content'] is None
assert failed_trace[-1]['response']['usage']['cost'] == 0
assert resumed['resumed_recorded_turns'] == 2 and resumed['trace'][:2] == failed_trace[:2]
failed_control = attempts['attempts/initial/contrast-7-1-provider-error/progress.json']
assert len(failed_control) == 1
assert failed_control[0]['response']['choices'][0]['finish_reason'] == 'error'
assert not failed_control[0]['response']['choices'][0]['message'].get('content')
assert failed_control[0]['response']['usage']['cost'] == 0
assert sorted(audits, key=lambda row: (row['condition'], row['case_id'])) == read('binding-audits.json')
assert read('embedding-state.json') == read('final-embedding-state.json')
for name in ('source-integrity.json', 'final-source-integrity.json'):
    rows = read(name)
    assert len(rows) == 36
    assert all(all(row[key] for key in ('exact_original_bytes', 'receipt_hash_matches',
                                      'chunk_offsets_match', 'first_insert_only', 'active')) for row in rows)
assert read('source-documents.json') == read('final-source-documents.json')
assert read('backup-receipt.json')['restore_contents_match']
compatibility = read('source-window-compatibility.json')
assert len(compatibility['notes']) == 84 and compatibility['all_equal']
assert compatibility['paid_requests'] == 0
assert all(row['equal'] and row['before_sha256'] == row['after_sha256'] for row in compatibility['notes'])
by_audit = {(row['condition'], row['case_id']): row for row in audits}
quality = read('quality-summary.json')
assert quality['completed'] == quality['planned'] == len(cases)
for row in quality['rows']:
    selected = [case for case in cases if case['condition'] == row['condition'] and
                ('contrast' if case['query']['case_id'].startswith('contrast-') else 'original') +
                '_' + case['query']['split'] == row['cohort']]
    keys = [(case['condition'], case['query']['case_id']) for case in selected]
    def mechanical(key):
        binding = by_audit[key]
        return binding['exposure_pass'] and binding['native_binding_pass']
    assert row['completed'] == row['planned'] == row['reviewed'] == len(selected)
    assert row['factually_correct'] == sum(reviews[key]['correct'] for key in keys)
    assert row['semantic_support_pass'] == sum(reviews[key]['semantic_grounding'] for key in keys)
    assert row['mechanical_binding_pass'] == sum(mechanical(key) for key in keys)
    assert row['joint_pass'] == sum(reviews[key]['correct'] and reviews[key]['semantic_grounding'] and mechanical(key) for key in keys)

logs = {row['path']: row['text'] for row in lines('validation-logs.jsonl.gz')}
for check in read('validation.json')['checks']:
    assert check['result'] == 'passed'
    assert digest(logs[check['log']].encode()) == check['sha256']
accounting = read('accounting.json')
assert accounting['conservative_exposure_usd'] <= 10
usage = lines('usage.jsonl.gz')
assert not any(row['status'] == 'in_flight' for row in usage)
paid = sum((row.get('usage') or {}).get('cost', 0) or 0 for row in usage)
assert abs(paid - accounting['new_paid_usd']) < 1e-9
assert abs(accounting['prior_paid_usd'] + paid - accounting['cumulative_paid_usd']) < 1e-9
print(json.dumps({'cases': len(cases), 'sources': 36,
                  'cumulative_paid_usd': accounting['cumulative_paid_usd'],
                  'boundary': 'Reproduces retained evidence checks; semantic reviews remain human-readable judgments.'}))
