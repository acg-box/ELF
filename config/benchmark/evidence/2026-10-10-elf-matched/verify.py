"""Verify the ELF matched-run evidence without paid calls or Docker."""
import gzip
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parent
read = lambda name: json.loads((root / name).read_text())
rows = lambda name: [json.loads(line) for line in gzip.decompress((root / name).read_bytes()).splitlines()]
for name, digest in read('manifest.json').items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
cases = rows('cases.jsonl.gz')
reviews = {(x['condition'], x['case_id']): x for x in read('review.json')}
assert len(cases) == len(reviews) == 140
assert Counter(x['condition'] for x in cases) == {
    'elf-documents-pack-reader': 50, 'elf-documents-retrieval-reader': 50,
    'elf-memory-pack-reader': 20, 'elf-memory-retrieval-reader': 20}
assert sum(x['split'] == 'dev' for x in cases) == 8
for case in cases:
    review = reviews[(case['condition'], case['case_id'])]
    assert review['answer_sha256'] == hashlib.sha256(case.get('text', '').encode()).hexdigest()
    assert review['strict_correct'] == bool(case.get('correct'))
    assert not review['correct'] or case['status'] == 'completed'
evaluation = read('evaluation.json')
for condition, summary in evaluation['conditions'].items():
    selected = [x for x in cases if x['condition'] == condition and x['split'] != 'dev']
    correct = sum(reviews[(condition, x['case_id'])]['correct'] for x in selected)
    assert correct == summary['reviewed_correct']
    assert math.isclose(correct / len(selected), summary['accuracy'])
for mode, score in evaluation['weighted_scores'].items():
    expected = 50 * (evaluation['conditions']['elf-documents-' + mode]['accuracy'] +
                     evaluation['conditions']['elf-memory-' + mode]['accuracy'])
    assert math.isclose(score, expected)
usage = rows('usage.jsonl.gz'); accounting = read('accounting.json')
assert [x['ordinal'] for x in usage] == list(range(1, len(usage) + 1))
assert math.isclose(sum((x.get('usage') or {}).get('cost', 0) for x in usage), accounting['paid_usd'])
assert accounting['paid_usd'] <= accounting['conservative_exposure_usd'] <= 10
assert not any(x['status'] == 'in_flight' for x in usage)
previous = root.parent / '2026-10-10-final-system-comparison/frozen-workloads.json'
assert read('frozen-workloads.json') == json.loads(previous.read_text())
assert read('cleanup.json')['owned_containers_removed']
print(json.dumps({'cases': len(cases), 'scores': evaluation['weighted_scores'], 'paid_usd': accounting['paid_usd']}))
