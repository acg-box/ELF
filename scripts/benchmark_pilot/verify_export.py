"""Verify public measurements without access to private project source text."""
import hashlib
import json
from pathlib import Path
import sys


def verify(root):
    manifest = json.loads((root / 'manifest.json').read_text())
    for name, expected in manifest['files'].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
    data = json.loads((root / 'measurements.json').read_text())
    protocol = json.loads((root / 'protocol.json').read_text())
    sources = {s['id']: s for s in json.loads((root / 'sources.json').read_text())['records']}
    cells = data['cells']
    assert len({c['cell'] for c in cells}) == len(cells)
    assert len({c['reader_pid'] for c in cells}) == len(cells)
    for cell in cells:
        assert cell['tool_calls'] <= protocol['max_tool_calls']
        assert cell['evidence_bytes'] <= protocol['max_evidence_bytes']
        assert all(sources[s]['stage'] <= cell['stage'] for s in cell['inspected_source_ids'])
        assert 0 <= cell['review']['passed_criteria'] <= cell['required_criteria']
        assert cell['review']['accepted'] == (cell['review']['passed_criteria'] == cell['required_criteria'] and not cell['review']['flags'])
    for condition, summary in data['summary'].items():
        group = [c for c in cells if c['condition'] == condition and c['phase'] == 'formal']
        assert summary['planned'] == summary['measured'] == len(group)
        assert summary['completed'] == sum(c['status'] == 'completed' for c in group)
        assert summary['semantic_acceptance'] == sum(c['review']['accepted'] for c in group)
        assert summary['reviewed'] == len(group)
        assert summary['reviewed_criteria'] == sum(c['required_criteria'] for c in group)
        assert summary['passed_criteria'] == sum(c['review']['passed_criteria'] for c in group)
        assert abs(summary['paid_usd'] - sum(c['paid_usd'] for c in group)) < 1e-9
    native = json.loads((root / 'native.json').read_text())
    for stage in native:
        assert stage['sources_verified'] == sum(s['stage'] <= stage['stage'] for s in sources.values())
        for rows in stage['vectors'].values():
            assert all(r['embedding_dim'] == 4096 for r in rows)
    expected_formal = sum(v['planned'] for v in data['summary'].values())
    assert sum(c['phase'] == 'formal' for c in cells) == expected_formal
    assert sum(c['phase'] == 'calibration' for c in cells) == 6
    accounted = data['exploration']['paid_usd'] + sum(v['paid_usd'] for v in data['preparation'].values()) + sum(c['paid_usd'] for c in cells)
    assert abs(accounted - data['new_budget']['paid_usd']) < 1e-8
    assert 0 <= data['new_budget']['paid_usd'] <= data['new_budget']['exposure_usd'] <= 10
    assert protocol['embedding_dimensions'] == 4096
    assert protocol['model'] == 'openai/gpt-6-luna'
    assert protocol['reasoning'] == 'medium'
    assert protocol['max_output_tokens'] == 128000
    return {'verified_cells': len(cells), 'original_records': len(sources),
            'paid_usd': data['new_budget']['paid_usd'],
            'boundary': 'Artifact integrity and metric consistency only; private semantic review is not independently reproduced.'}


if __name__ == '__main__':
    print(json.dumps(verify(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent), indent=2))
