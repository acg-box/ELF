"""Verify exported hashes, saved scores, and review-to-answer bindings offline."""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
sys.path.insert(0, str(REPO / 'scripts'))
from benchmark_deep.parser_stress import identifiers_exact, score

for name, digest in json.loads((ROOT / 'manifest.json').read_text()).items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name

for cohort in (ROOT, ROOT / 'best-profile'):
    with gzip.open(cohort / 'cases.jsonl.gz', 'rt') as stream:
        rows = [json.loads(line) for line in stream]
    review = {(r['condition'], r['case_id']): r for r in json.loads((cohort / 'semantic-review.json').read_text())}
    assert len(rows) == len(review) == 180
    assert len({(r['condition'], r['case_id']) for r in rows}) == 180
    counts = collections.defaultdict(collections.Counter)
    for row in rows:
        identity = (row['condition'], row['case_id'])
        checked = review[identity]
        text = row.get('text', '')
        assert hashlib.sha256(text.encode()).hexdigest() == checked['answer_sha256'], identity
        normalized = score(row['expected'], text) if row['status'] == 'completed' else None
        assert normalized == row['correct'] == checked['strict_correct'], identity
        if checked['semantic_correct'] != (normalized is True):
            assert (not row['expected']['supported'] or not identifiers_exact(row['expected'], text)), identity
        count = counts[row['condition']]
        count['questions'] += 1
        count['completed'] += row['status'] == 'completed'
        count['normalized_correct'] += normalized is True
        count['reviewed_correct'] += checked['semantic_correct']
        count[row['lane'].split('_')[0] + '_reviewed_correct'] += checked['semantic_correct']
    print(json.dumps({'cohort': cohort.name, 'scores': dict(counts)}, ensure_ascii=False))
print('All manifest hashes and answer/review bindings match. Semantic judgments require source review.')
