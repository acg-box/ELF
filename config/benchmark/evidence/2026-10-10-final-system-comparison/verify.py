"""Verify frozen system-comparison evidence without services or paid calls."""
import gzip
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parent

def read(name):
    return json.loads((root / name).read_text())

def rows(name):
    return [json.loads(line) for line in gzip.decompress((root / name).read_bytes()).splitlines()]

manifest = read('manifest.json')
for name, expected in manifest.items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
cases = rows('cases.jsonl.gz')
reviews = {(x['condition'], x['case_id']): x for x in read('review.json')}
assert len(cases) == len(reviews) == 280
assert len({(x['condition'], x['case_id']) for x in cases}) == 280
assert all(x['status'] == 'completed' for x in cases)
assert Counter(x['condition'] for x in cases) == dict.fromkeys(
    ['hindsight-native', 'ragflow-native', 'hindsight-retrieval', 'ragflow-retrieval'], 70)
for case in cases:
    review = reviews[(case['condition'], case['case_id'])]
    assert review['answer_sha256'] == hashlib.sha256(case['text'].encode()).hexdigest()
    assert review['strict_correct'] == case['correct']
    assert case['case_id'] not in read('protocol.json')['excluded_cases']
result = {}
for condition, summary in read('evaluation.json')['conditions'].items():
    selected = [x for x in cases if x['condition'] == condition]
    documents = [x for x in selected if not x['case_id'].startswith('memory-')]
    memory = [x for x in selected if x['case_id'].startswith('memory-') and x['split'] != 'dev']
    assert len(documents) == 50 and len(memory) == 16
    assert sum(x['split'] == 'dev' for x in selected) == 4
    correct = lambda subset: sum(reviews[(condition, x['case_id'])]['correct'] for x in subset)
    score = correct(documents) + 50 * correct(memory) / 16
    assert math.isclose(score, summary['weighted_score'])
    result[condition] = {'documents': correct(documents), 'memory': correct(memory), 'score': score}
usage = rows('usage.jsonl.gz')
accounting = read('accounting.json')
assert [x['ordinal'] for x in usage] == list(range(accounting['first_ordinal'], accounting['last_ordinal'] + 1))
assert math.isclose(sum((x.get('usage') or {}).get('cost', 0) for x in usage), accounting['new_paid_usd'])
assert accounting['cumulative_paid_usd'] <= accounting['cumulative_exposure_usd'] <= 20
assert not any(x['status'] in ('inflight', 'in_flight') for x in usage)
assert read('controller-completion.json')['exit_code'] == 0
assert read('cleanup.json')['credentials_removed']
print(json.dumps({'completed': len(cases), 'scores': result, 'cumulative_paid_usd': accounting['cumulative_paid_usd']}, indent=2))
