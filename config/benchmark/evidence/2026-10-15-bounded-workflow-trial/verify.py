"""Check closed trial integrity and arithmetic, not independent task correctness."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
read = lambda name: json.loads((root / name).read_text())
for name, expected in read('manifest.json')['files'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
measurements = read('measurements.json')
ledger = read('provider-requests.json')
budget = measurements['budget']
assert [r['ordinal'] for r in ledger] == list(range(budget['first_new_ordinal'], budget['last_ordinal'] + 1))
assert all(r['status'] == 'completed' for r in ledger)
assert all(r['requested_max_tokens'] == 128000 and r['reasoning_effort'] == 'medium' for r in ledger if r['kind'] == 'chat')
paid = sum(r['usage']['cost'] for r in ledger)
assert abs(paid - budget['added_usd']) < 1e-8
assert abs(budget['opening_paid_usd'] + paid - budget['paid_usd']) < 1e-8
assert abs(budget['opening_exposure_usd'] + paid - budget['exposure_usd']) < 1e-8
assert budget['paid_usd'] <= budget['exposure_usd'] <= 10
cells = measurements['cells']
assert len(cells) == 15 and sum(len(c['sessions']) for c in cells) == 30
ordinals = [n for c in cells for n in c['provider_ordinals']]
assert sorted(ordinals) == [r['ordinal'] for r in ledger]
costs = {r['ordinal']: r['usage']['cost'] for r in ledger}
for cell in cells:
    assert abs(cell['paid_usd'] - sum(costs[n] for n in cell['provider_ordinals'])) < 1e-8
    assert cell['observed_human_corrections'] is None
    assert len(cell['sessions']) == 2
    for session in cell['sessions']:
        assert session['budget_contract_passed'] == (session['evidence_bytes'] <= 65536)
    if cell['native']:
        native = cell['native']
        assert native['postgres_state_equal'] and native['lossless_archive_verified'] and native['resources_removed']
        assert all(v['dimension'] == 4096 and (v['stored_vector_query_passed'] if v['points'] else v['stored_vector_query_passed'] is None) for v in native['qdrant'])
for batch, arms in measurements['summary'].items():
    for arm, summary in arms.items():
        group = [c for c in cells if c['batch'] == batch and c['condition'] == arm]
        assert summary['planned_trajectories'] == summary['recorded_trajectories'] == len(group) == 2
        assert summary['functional_passes'] == sum(c['functional_checks_passed'] is True for c in group)
        assert summary['functional_failures'] == sum(c['functional_checks_passed'] is False for c in group)
        assert summary['unassessed_after_stop'] == sum(c['functional_checks_passed'] is None for c in group)
        assert summary['handoffs_before_resume'] == sum(c['handoff_before_resume'] for c in group)
        assert summary['handoffs_at_close'] == sum(c['handoff_at_close'] for c in group)
        assert summary['budget_contract_failures'] == sum(any(not s['budget_contract_passed'] for s in c['sessions']) for c in group)
        assert abs(summary['paid_usd'] - sum(c['paid_usd'] for c in group)) < 1e-8
        assert abs(summary['session_seconds'] - sum(c['session_seconds'] for c in group)) < 1e-6
        assert summary['native_tool_calls'] == sum(sum(n for name, n in c['tool_counts'].items() if name.startswith('elf_')) for c in group) == 0
assert sum(c['status'] == 'local_request_size_limit' for c in cells) == 1
assert not measurements['decision']['memory_benefit_established']
assert not measurements['decision']['product_ranking_supported']
print(json.dumps({'verified_trajectories': len(cells), 'recorded_sessions': 30,
                  'new_paid_requests': len(ledger), 'added_usd': paid,
                  'formal_native_tool_calls': 0,
                  'boundary': 'Integrity and arithmetic only. No memory-benefit or customer-readiness claim.'}, indent=2))
