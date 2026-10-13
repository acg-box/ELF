"""Export only de-identified measurements from a private project trial."""
from __future__ import annotations

import json
from pathlib import Path

from .corpus import digest, load, save
from .report import measurements


def export(root, destination):
    if destination.exists():
        raise ValueError('Evidence exports are immutable; select a new destination')
    fixture = root / 'fixture'
    sources, _ = load(fixture)
    source_aliases = {s['id']: f'source-{i + 1:03}' for i, s in enumerate(sources)}
    tasks = json.loads((fixture / 'tasks.json').read_text())
    aliases = {task['id']: f'task-{i + 1:02}' for i, task in enumerate(tasks)}
    raw = measurements(root, fixture)
    reviews = json.loads((root / 'review.json').read_text())
    public = {k: v for k, v in raw.items() if k != 'cells'}
    public['cells'] = []
    for row in raw['cells']:
        result = {k: v for k, v in row.items() if k not in ('task_id', 'cell', 'criteria')}
        result.update(task_id=aliases[row['task_id']], cell=f"{aliases[row['task_id']]}--{row['condition']}--{row['repetition']}",
                      required_criteria=len(row['criteria']),
                      matching_text_patterns=sum(c['text_patterns_present'] for c in row['criteria']))
        review = reviews[row['cell']]
        allowed_flags = {'missing_detail', 'stale_decision', 'incorrect_scope',
                         'unsupported_current_state', 'unbound_citation', 'invalid_format', 'incomplete'}
        if set(review['flags']) - allowed_flags:
            raise ValueError('Public reviews require generic flags, not private prose')
        result['review'] = {'accepted': review['accepted'], 'passed_criteria': review['passed_criteria'], 'flags': review['flags']}
        private_result = json.loads((root / 'cases' / row['cell'] / 'result.json').read_text())
        result['stage'] = private_result['stage']
        result['reader_pid'] = private_result['pid']
        trace = json.loads((root / 'cases' / row['cell'] / 'trace.json').read_text())
        inspected = set()
        def collect(value):
            if isinstance(value, dict):
                if value.get('source_id'):
                    inspected.add(value['source_id'])
                for v in value.values():
                    collect(v)
            elif isinstance(value, list):
                for v in value:
                    collect(v)
        for step in trace:
            for tool in step['tools']:
                collect(tool['result'])
        result['inspected_source_ids'] = sorted(source_aliases[s] for s in inspected)
        public['cells'].append(result)
    save(destination / 'measurements.json', public)
    save(destination / 'sources.json', {'fixture_sha256': digest((fixture / 'freeze.json').read_bytes()),
        'records': [{'id': source_aliases[s['id']], 'stage': s['stage'], 'bytes': len(s['text'].encode()), 'sha256': s['sha256']} for s in sources]})
    controls = {'schema', 'conditions', 'formal_repetitions', 'calibration_repetitions', 'max_rounds',
                'max_tool_calls', 'max_evidence_bytes', 'max_tool_result_bytes', 'model', 'provider',
                'reasoning', 'max_output_tokens', 'embedding_model', 'embedding_dimensions',
                'embedding_provider', 'reranker', 'extraction_window_bytes', 'memory_notes_per_event',
                'budget_usd', 'calibration_tranche_usd', 'paid_retries', 'ranking_or_prompt_tuning_after_formal_start',
                'omit_chat_temperature', 'chat_prompt_price', 'chat_completion_price', 'extractor_parse_attempts'}
    save(destination / 'protocol.json', {k: v for k, v in json.loads((fixture / 'protocol.json').read_text()).items() if k in controls})
    native = []
    for path in sorted(root.glob('native-stage-*.json')):
        state = json.loads(path.read_text())
        native.append({'stage': state['stage'], 'sources_verified': state['sources_verified'],
                       'vectors': state['vectors'], 'notes': len(state['notes'])})
    save(destination / 'native.json', native)
    save(destination / 'private-evidence-hashes.json', {
        'boundary': 'These hashes identify private evidence. Original business records, task text, answer text and provider receipts are not published.',
        'files': [{'path_sha256': digest(str(p.relative_to(root)).encode()), 'content_sha256': digest(p.read_bytes())} for p in sorted(root.rglob('*.json'))
                  if 'private-' not in p.name and p.name not in ('runtime.json',)
                  and not p.name.endswith('.attempt.json') and p.is_file()]})
    (destination / 'verify.py').write_bytes(Path(__file__).with_name('verify_export.py').read_bytes())
    save(destination / 'manifest.json', {'files': {p.name: digest(p.read_bytes()) for p in sorted(destination.iterdir()) if p.is_file()}})
    print(json.dumps({'exported_cells': len(public['cells']), 'destination': str(destination)}))
