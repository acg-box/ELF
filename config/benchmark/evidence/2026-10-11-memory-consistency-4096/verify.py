"""Verify retained answers, full vectors, matched measurements, and task costs."""
import gzip
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(name):
    path = ROOT / name
    raw = gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes()
    return json.loads(raw)


def lines(name):
    return [json.loads(row) for row in gzip.decompress((ROOT / name).read_bytes()).splitlines()]


manifest = read('manifest.json')
assert set(manifest) == {p.name for p in ROOT.iterdir() if p.is_file() and p.name != 'manifest.json'}
for name, sha in manifest.items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha, name

receipts = lines('provider-receipts.jsonl.gz')
witness = {}
for receipt in receipts:
    request, response = receipt['request'], receipt['response']
    if 'input' in request:
        assert request['model'] == 'qwen/qwen3-embedding-8b'
        assert request['dimensions'] == 4096
        inputs = request['input'] if isinstance(request['input'], list) else [request['input']]
        raw = (json.dumps({'request': request, 'response': response}, indent=2) + '\n').encode()
        sha = hashlib.sha256(raw).hexdigest()
        for row in response.get('data', []):
            assert len(row['embedding']) == 4096
            # Preparation retains the first occurrence of repeated batch inputs.
            witness.setdefault((sha, inputs[row['index']]), row['embedding'])
    else:
        assert request['model'] == 'deepseek/deepseek-v4.1-flash'
        assert request['max_tokens'] == 943718
        assert request['reasoning']['effort'] == 'max'

dataset = read('dataset.json.gz')
assert len(dataset['corpus']) == 88 and len(dataset['queries']) == 70
for row in dataset['corpus'] + dataset['queries']:
    text = row.get('text', row.get('question'))
    assert len(row['vector']) == 4096
    assert row['vector'] == witness[row['receipt_sha256'], text]
    assert row['embedding_input_sha256'] == hashlib.sha256(text.encode()).hexdigest()
assert read('embedding-reuse.json')['missing'] == []
assert read('embedding-reuse.json')['new_embedding_calls'] == 0

for prefix in ['baseline', 'selection']:
    cases = lines(prefix + '-cases.jsonl.gz')
    reviews = {(r['condition'], r['case_id']): r for r in read(prefix + '-review.json')}
    assert len(cases) == len(reviews) == 140
    assert all(c['status'] == 'completed' for c in cases)
    for case in cases:
        review = reviews[case['condition'], case['case_id']]
        assert review['answer_sha256'] == hashlib.sha256(case['text'].encode()).hexdigest()
        assert review['strict_correct'] == case['correct']
        if review['strict_correct'] != review['reviewed_correct']:
            text = case['text'].strip()
            numeric = case['case_id'] in ['stress-020', 'stress-022'] and text in ['420', '930'] and case['expected']['facts'] == [text]
            absent = case['case_id'].startswith('memory-') and case['case_id'].endswith('-3') and text.lower().startswith('no budget owner has been appointed') and 'no budget owner has been appointed' in case['context']['text'].lower()
            routing = case['case_id'] == 'stress-024' and text == 'No bank-routing number is published.' and text in case['context']['text']
            assert numeric or absent or routing
    for condition, summary in read(prefix + '-summary.json').items():
        rows = [c for c in cases if c['condition'] == condition and c['split'] != 'dev']
        assert len(rows) == summary['scored']
        assert sum(reviews[c['condition'], c['case_id']]['reviewed_correct'] for c in rows) == summary['reviewed_correct']
    if prefix == 'selection':
        assert sum('reused_from' in c for c in cases) == 100
        assert all('reused_from' not in c for c in cases if c['condition'].startswith('elf-memory'))

assert read('selection-embedding-state.json') == read('baseline-embedding-state.json')
for state in read('selection-embedding-state.json').values():
    assert state['dimensions'] == [4096]
assert read('selection-source-integrity.json')['all_original_bytes_equal']
assert read('selection-source-integrity.json')['all_citation_offsets_equal']
integrity = read('baseline-memory-integrity.json')
assert integrity['notes'] == 54 and integrity['verbatim_quotes_verified'] == 74
assert integrity['identifier_mismatches'] == integrity['rejected'] == []
assert integrity['all_extracted_keys_non_authoritative']
assert read('context-controls.json')['prior_combined_contexts_reproduced'] == 20
cases = lines('ablation-cases.jsonl.gz')
reviews = {(r['condition'], r['case_id']): r for r in read('ablation-review.json')}
assert len(cases) == len(reviews) == 60
for case in cases:
    assert case['status'] == 'completed'
    review = reviews[case['condition'], case['query']['case_id']]
    assert review['answer_sha256'] == hashlib.sha256(case['text'].encode()).hexdigest()
    assert review['strict_correct'] == case['strict_correct']
    if review['strict_correct'] != review['reviewed_correct']:
        assert case['query']['lane'] == 'abstention'
        assert case['text'].lower().startswith('no budget owner has been appointed')
        assert 'no budget owner has been appointed' in case['context']['text'].lower()
for condition, summary in read('ablation-summary.json').items():
    rows = [c for c in cases if c['condition'] == condition and c['query']['split'] != 'dev']
    assert len(rows) == summary['scored'] == 16
    assert sum(reviews[condition, c['query']['case_id']]['reviewed_correct'] for c in rows) == summary['reviewed_correct']

for n in [10000, 50000]:
    vectors, queries = set(), set()
    for backend in ['qdrant', 'infinity']:
        value = read(f'{backend}-scale-{n}.json.gz')
        assert value['dimension'] == 4096 and len(value['rows']) == 840
        assert value['delete_visibility']['absent']
        vectors.add(value['vector_sha256']); queries.add(value['query_sha256'])
        for row in value['rows']:
            assert len(row['ids']) == len(set(row['ids'])) == row['returned'] == 10
            assert not row['filtered'] or all(i % 10 == row['query'] % 10 for i in row['ids'])
            assert math.isclose(row['recall_at_10'], len(set(row['ids']) & set(row['exact_ids'])) / 10)
    assert len(vectors) == len(queries) == 1
assert len(read('latency-rows.json.gz')) == 3360
for backend in ['qdrant', 'infinity']:
    value = read(backend + '-sustained.json.gz')
    assert value['complete'] and len(value['rounds']) == 3
    for row in value['rounds']:
        assert row['seconds'] >= 9.99 and len(row['workers']) == 8
        assert not any(w['failure'] or w['underfilled'] for w in row['workers'])
        assert sum(w['queries'] for w in row['workers']) == row['queries']
        assert math.isclose(row['qps'], row['queries'] / row['seconds'])

usage = lines('usage.jsonl.gz'); accounting = read('accounting.json')
prior = json.loads((ROOT.parent / '2026-10-10-retrieval-laboratory/accounting.json').read_text())
assert math.isclose(accounting['prior_paid_usd'], prior['cumulative_paid_usd'])
assert [r['ordinal'] for r in usage] == list(range(953, 953 + len(usage)))
assert all(r['status'] == 'completed' for r in usage)
assert math.isclose(sum(r['usage']['cost'] for r in usage), accounting['new_paid_usd'])
assert math.isclose(accounting['prior_paid_usd'] + accounting['new_paid_usd'], accounting['cumulative_paid_usd'])
assert accounting['cumulative_paid_usd'] <= 10 and accounting['unsettled'] == 0
print(json.dumps({'native_cases': 140, 'new_memory_answers': 40, 'ablation_answers': 60,
                  'full_vectors': 158, 'dense_measurements': 3360,
                  'cumulative_paid_usd': accounting['cumulative_paid_usd']}))
