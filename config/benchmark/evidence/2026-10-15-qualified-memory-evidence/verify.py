"""Verify bundle integrity and comparison arithmetic, not private semantic truth."""
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics

root = Path(__file__).resolve().parent
read = lambda path: json.loads(path.read_text())
for name, expected in read(root/'manifest.json')['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest() == expected, name
for name in ('baseline-new', 'extraction-candidate', 'pack-only'):
    spec = importlib.util.spec_from_file_location(name, root/name/'verify.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.verify(root/name)

data = read(root/'comparison.json')
old = read(root.parent/'2026-10-14-bounded-source-evidence/measurements.json')
controls = read(root/'extraction-candidate/measurements.json')
new_base = read(root/'baseline-new/measurements.json')
final = read(root/'pack-only/measurements.json')
for arm, groups in data['conditions'].items():
    for name, result in groups.items():
        fresh = name.endswith('_new')
        source = new_base if name=='prior_new' else old if name=='prior_original' else final if arm=='full_elf' else controls
        rows = [r for r in source['cells'] if r['phase']=='formal' and r['condition']==arm
                and (r.get('cohort')=='frozen-2026-10-15')==fresh]
        assert result['cells'] == len(rows)
        assert result['frozen_coverage'] == sum(r['review']['passed_criteria'] for r in rows)
        assert result['frozen_accepted'] == sum(r['review']['accepted'] for r in rows)
        assert result['frozen_required'] == 4*len(rows)
        assert result['excluded_obligations'] == (0 if fresh else 2)
        assert 0 <= result['excluded_passes'] <= result['excluded_obligations']
        assert result['unambiguous_coverage'] == result['frozen_coverage']-result['excluded_passes']
        assert result['unambiguous_required'] == result['frozen_required']-result['excluded_obligations']
        assert abs(result['median_seconds']-statistics.median(r['seconds'] for r in rows)) < 1e-8
        assert abs(result['mean_answer_usd']-sum(r['paid_usd'] for r in rows)/len(rows)) < 1e-8
assert data['budget']['paid_usd'] == final['new_budget']['paid_usd']
assert abs(data['budget']['added_usd']-(data['budget']['paid_usd']-data['budget']['before_task_paid_usd'])) < 1e-8
assert data['budget']['paid_usd'] <= data['budget']['exposure_usd'] <= 10
quotes = read(root/'pack-only/qualifier-audit.json')['delivery']
assert quotes['evidence_quote_presentations'] == quotes['evidence_quotes_bound_to_returned_windows'] > 0
print(json.dumps({'verified_run_cells': sum(len(read(root/name/'measurements.json')['cells']) for name in
    ('baseline-new','extraction-candidate','pack-only')), 'paid_usd': data['budget']['paid_usd'],
    'boundary': 'Integrity and arithmetic only; source-based judgments are not independently reproduced.'}, indent=2))
