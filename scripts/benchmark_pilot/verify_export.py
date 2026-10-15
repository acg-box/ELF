"""Verify public measurements without access to private project source text."""
import hashlib
import json
import math
from pathlib import Path
import sys


def explicit_cost(row):
    """Match the gateway's settled-cost semantics without a repository import."""
    value = (row.get('usage') or {}).get('cost')
    return value if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0 else None


def verify(root):
    manifest = json.loads((root / 'manifest.json').read_text())
    for name, expected in manifest['files'].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
    data = json.loads((root / 'measurements.json').read_text())
    protocol = json.loads((root / 'protocol.json').read_text())
    sources = {s['id']: s for s in json.loads((root / 'sources.json').read_text())['records']}
    cells = data['cells']
    ledger = json.loads((root / 'request-ledger.json').read_text())
    assert [r['ordinal'] for r in ledger] == list(range(1, len(ledger) + 1))
    assert all(r['status'] in ('completed', 'uncertain', 'provider_failed', 'completed_cost_unknown') for r in ledger)
    opening_paid = data['new_budget'].get('prior_paid_usd', 0)
    paid = opening_paid + sum(explicit_cost(r) or 0 for r in ledger)
    exposure = opening_paid + sum(explicit_cost(r) if r['status'] == 'completed' and explicit_cost(r) is not None
        else max(r['reserved_usd'], explicit_cost(r) or 0) for r in ledger)
    assert abs(paid - data['new_budget']['paid_usd']) < 1e-8
    assert abs(exposure - data['new_budget']['exposure_usd']) < 1e-8
    prior = data['exploration']['requests']
    assert abs(opening_paid + sum(explicit_cost(r) or 0 for r in ledger[:prior]) - data['exploration']['paid_usd']) < 1e-8
    for row in ledger[prior:]:
        if row['kind'] == 'chat':
            if row['status'] == 'completed':
                assert row['model'] == protocol['model']
            assert row['requested_max_tokens'] == protocol['max_output_tokens']
            assert row['reasoning_effort'] == protocol['reasoning']
    assert len({c['cell'] for c in cells}) == len(cells)
    assert len({c['reader_pid'] for c in cells}) == len(cells)
    for cell in cells:
        assert cell['tool_calls'] <= protocol['max_tool_calls']
        assert cell['evidence_bytes'] <= protocol['max_evidence_bytes']
        assert all(sources[s]['stage'] <= cell['stage'] for s in cell['inspected_source_ids'])
        assert 0 <= cell['review']['passed_criteria'] <= cell['required_criteria']
        assert cell['review']['accepted'] == (cell['review']['passed_criteria'] == cell['required_criteria'] and not cell['review']['flags'])
        first, last = cell['request_interval']
        assert prior <= first < last <= len(ledger)
        assert abs(sum(explicit_cost(r) or 0 for r in ledger[first:last]) - cell['paid_usd']) < 1e-8
    for condition, summary in data['summary'].items():
        group = [c for c in cells if c['condition'] == condition and c['phase'] == 'formal']
        assert summary['measured'] == len(group) <= summary['planned']
        if 'formal_task_count' in protocol:
            assert summary['planned'] == protocol['formal_task_count'] * protocol['formal_repetitions']
        assert summary['completed'] == sum(c['status'] == 'completed' for c in group)
        assert summary['semantic_acceptance'] == sum(c['review']['accepted'] for c in group)
        assert summary['reviewed'] == len(group)
        assert summary['reviewed_criteria'] == sum(c['required_criteria'] for c in group)
        assert summary['passed_criteria'] == sum(c['review']['passed_criteria'] for c in group)
        assert abs(summary['paid_usd'] - sum(c['paid_usd'] for c in group)) < 1e-9
        matched = []
        for cell in group:
            pair = [other for other in cells if other['phase'] == 'formal'
                    and (other['task_id'], other['repetition']) == (cell['task_id'], cell['repetition'])]
            if (len(pair) == len(protocol['conditions'])
                    and {other['condition'] for other in pair} == set(protocol['conditions'])
                    and not any(other['status'] in ('transport_failed', 'harness_failed') for other in pair)):
                matched.append(cell)
        assert summary['matched_content_cells'] == len(matched)
        assert summary['matched_criteria'] == sum(c['required_criteria'] for c in matched)
        assert summary['matched_passed_criteria'] == sum(c['review']['passed_criteria'] for c in matched)
        assert summary['matched_accepted'] == sum(c['review']['accepted'] for c in matched)
    native = json.loads((root / 'native.json').read_text())
    for stage in native:
        assert stage['sources_verified'] == sum(s['stage'] <= stage['stage'] for s in sources.values())
        for rows in stage['vectors'].values():
            assert all(r['embedding_dim'] == 4096 for r in rows)
    expected_formal = sum(v['planned'] for v in data['summary'].values())
    recorded_formal = sum(c['phase'] == 'formal' for c in cells)
    assert recorded_formal == sum(s['measured'] for s in data['summary'].values()) <= expected_formal
    assert sum(c['phase'] == 'calibration' for c in cells) <= protocol.get('calibration_task_count', 2) * protocol['calibration_repetitions'] * len(protocol['conditions'])
    accounted = data['exploration']['paid_usd'] + sum(v['paid_usd'] for v in data['preparation'].values()) + sum(c['paid_usd'] for c in cells)
    if data.get('native_recall_diagnostic'):
        accounted += data['native_recall_diagnostic']['paid_usd']
    assert abs(accounted - data['new_budget']['paid_usd']) < 1e-8
    assert 0 <= data['new_budget']['paid_usd'] <= data['new_budget']['exposure_usd'] <= 10
    assert protocol['embedding_dimensions'] == 4096
    assert protocol['model'] == 'openai/gpt-6-luna'
    assert protocol['reasoning'] == 'medium'
    assert protocol['max_output_tokens'] == 128000
    audit = json.loads((root / 'write-rejection-audit.json').read_text())
    assert audit['candidates'] == data['native_writes']['candidates'] == sum(audit['first_gate_outcomes'].values())
    if protocol.get('frozen_extraction'):
        limits = json.loads((root / 'runtime-provenance.json').read_text())['native_limits']
        reuse = json.loads((root / 'provider-reuse.json').read_text())
        assert limits['max_note_chars'] == protocol['note_character_limit'] == audit['note_character_limit']
        assert limits['mmr_enabled'] == protocol['mmr_enabled']
        assert audit['same_frozen_proposals'] and len(audit['proposal_sha256']) == 64
        assert reuse['reused']['extraction'] == data['native_writes']['windows']
        assert all(s['amortized_usd_per_task'] is None for s in data['summary'].values())
    restore = json.loads((root / 'restoration.json').read_text())
    assert restore['source_count'] == len(sources) and restore['postgres_state_equal']
    assert all(row['dimension'] == 4096 and (row['stored_vector_query_passed'] if row['points'] else row['stored_vector_query_passed'] is None) for row in restore['qdrant'])
    return {'verified_cells': len(cells), 'original_records': len(sources),
            'formal_cells': {'planned': expected_formal, 'recorded': recorded_formal},
            'paid_usd': data['new_budget']['paid_usd'],
            'boundary': 'Artifact integrity and metric consistency only; private semantic review is not independently reproduced.'}


if __name__ == '__main__':
    print(json.dumps(verify(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent), indent=2))
