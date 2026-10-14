"""Export only de-identified measurements from a private project trial."""
from __future__ import annotations

import json
from pathlib import Path
import tomllib

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
                         'incorrect_time', 'unsupported_claim', 'unsupported_current_state',
                         'unbound_citation', 'invalid_format', 'incomplete'}
        if set(review['flags']) - allowed_flags:
            raise ValueError('Public reviews require generic flags, not private prose')
        result['review'] = {'accepted': review['accepted'], 'passed_criteria': review['passed_criteria'], 'flags': review['flags']}
        private_result = json.loads((root / 'cases' / row['cell'] / 'result.json').read_text())
        result['stage'] = private_result['stage']
        result['reader_pid'] = private_result['pid']
        result['request_interval'] = [private_result['usage_before']['requests'], private_result['usage_after']['requests']]
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
        collect(private_result.get('provided_originals', {}))
        result['inspected_source_ids'] = sorted(source_aliases[s] for s in inspected)
        public['cells'].append(result)
    save(destination / 'measurements.json', public)
    save(destination / 'sources.json', {'fixture_sha256': digest((fixture / 'freeze.json').read_bytes()),
        'records': [{'id': source_aliases[s['id']], 'stage': s['stage'], 'bytes': len(s['text'].encode()), 'sha256': s['sha256']} for s in sources]})
    amendment = root / 'preformal-input-amendment.json'
    if amendment.exists():
        previous = json.loads(amendment.read_text())
        calibration = root / 'calibration-fixture/freeze.json'
        save(destination / 'input-amendment.json', {
            'previous_freeze_sha256': previous['previous_freeze_sha256'],
            'formal_freeze_sha256': digest((fixture / 'freeze.json').read_bytes()),
            'calibration_freeze_sha256': digest((calibration if calibration.exists() else fixture / 'freeze.json').read_bytes()),
            'boundary': 'A calibration-only diagnostic input gained an omitted paragraph before formal execution. Formal selections and original bytes did not change; the recorded calibration answer was not repeated.'})
    controls = {'schema', 'conditions', 'formal_repetitions', 'calibration_repetitions', 'max_rounds',
                'max_tool_calls', 'max_evidence_bytes', 'max_tool_result_bytes', 'model', 'provider',
                'reasoning', 'max_output_tokens', 'embedding_model', 'embedding_dimensions',
                'embedding_provider', 'reranker', 'extraction_window_bytes', 'memory_notes_per_event',
                'budget_usd', 'calibration_tranche_usd', 'paid_retries', 'ranking_or_prompt_tuning_after_formal_start',
                'host_opening', 'hydrate_sources', 'client_v3', 'note_character_limit', 'mmr_enabled', 'frozen_extraction', 'agent_contract', 'omit_chat_temperature', 'chat_prompt_price', 'chat_completion_price', 'extractor_parse_attempts'}
    save(destination / 'protocol.json', {k: v for k, v in json.loads((fixture / 'protocol.json').read_text()).items() if k in controls})
    native = []
    for path in sorted(root.glob('native-stage-*.json')):
        state = json.loads(path.read_text())
        native.append({'stage': state['stage'], 'sources_verified': state['sources_verified'],
                       'vectors': state['vectors'], 'notes': len(state['notes'])})
    save(destination / 'native.json', native)
    reuse = root / 'provider-reuse.jsonl'
    if reuse.exists():
        rows = [json.loads(line) for line in reuse.read_text().splitlines()]
        save(destination / 'provider-reuse.json', {'reused': {kind: sum(row['kind'] == kind and row['reused'] for row in rows)
             for kind in ('embedding', 'extraction')}, 'forwarded_embeddings': sum(not row['reused'] for row in rows),
             'log_sha256': digest(reuse.read_bytes()),
             'boundary': 'Reused responses were settled in the earlier ledger. These are not new provider invocations.'})
    ledger = json.loads((root / 'budget-ledger.json').read_text())
    save(destination / 'request-ledger.json', [{
        **{key: row[key] for key in ('ordinal', 'kind', 'status', 'reserved_usd', 'model', 'provider',
              'seconds', 'requested_provider', 'requested_max_tokens', 'reasoning_effort') if key in row},
        'usage': {key: value for key, value in row.get('usage', {}).items()
                  if key in ('prompt_tokens', 'completion_tokens', 'total_tokens', 'cost')},
    } for row in ledger['requests']])
    builds = {}
    for phase in ('calibration', 'formal-first', 'formal', 'diagnostic'):
        path = root / ('runtime-build-' + phase + '.json')
        if phase == 'formal' and not path.exists():
            path = root / 'runtime-build.json'
        if path.exists():
            builds[phase] = {key: value for key, value in json.loads(path.read_text()).items()
                             if key in ('source_commit', 'binaries', 'tokenizer_sha256', 'database_image', 'qdrant_image')}
    snapshot = root / 'harness-snapshot.json'
    if snapshot.exists():
        builds['reader_files'] = {key: value for key, value in json.loads(snapshot.read_text())['files'].items()
                                 if key not in ('scripts/benchmark_pilot/report.py', 'scripts/benchmark_pilot/export.py',
                                                'scripts/benchmark_pilot/verify_export.py')}
    native_config = root / 'private-elf.toml'
    if native_config.exists():
        config = tomllib.loads(native_config.read_text())
        builds['native_limits'] = {key: config[section][key] for section, keys in (
            ('memory', ('max_note_chars', 'max_notes_per_add_event')),
            ('security', ('evidence_min_quotes', 'evidence_max_quotes', 'evidence_max_quote_bytes')))
            for key in keys if key in config[section]}
        diversity = config.get('ranking', {}).get('diversity', {})
        if 'enabled' in diversity:
            builds['native_limits']['mmr_enabled'] = diversity['enabled']
    save(destination / 'runtime-provenance.json', builds)
    rejection_audit = root / 'write-rejection-audit.json'
    if rejection_audit.exists():
        audit = json.loads(rejection_audit.read_text())
        save(destination / 'write-rejection-audit.json', {key: audit[key] for key in (
            'candidates', 'first_gate_outcomes', 'quote_identity', 'note_character_limit', 'quote_byte_limit',
            'same_frozen_proposals', 'proposal_sha256') if key in audit})
    restoration = root / 'backup' / 'restore-receipt.json'
    if restoration.exists():
        receipt = json.loads(restoration.read_text())
        save(destination / 'restoration.json', {key: receipt[key] for key in (
            'source_count', 'postgres_state_equal', 'qdrant', 'image_manifests')} | {
            'private_receipt_sha256': digest(restoration.read_bytes())})
    read_audit = root / 'read-audit.json'
    if read_audit.exists():
        audit = json.loads(read_audit.read_text())
        metrics = ('verified_bodies', 'original_bytes', 'repeated_bodies_suppressed',
                   'native_bounded_reads', 'native_rereads')
        save(destination / 'read-audit.json', {
            'summary': audit['summary'],
            'all_delivered_original_bytes_match': audit['all_delivered_original_bytes_match'],
            'all_native_caps_respected': audit['all_native_caps_respected'],
            'formal': {condition: {key: sum(row.get(key, 0) for row in audit['cells']
                if row['phase'] == 'formal' and row['condition'] == condition) for key in metrics}
                for condition in raw['summary']},
            'private_receipt_sha256': digest(read_audit.read_bytes())})
    save(destination / 'private-evidence-hashes.json', {
        'boundary': 'These hashes identify private evidence. Original business records, task text, answer text and provider receipts are not published.',
        'files': [{'path_sha256': digest(str(p.relative_to(root)).encode()), 'content_sha256': digest(p.read_bytes())} for p in sorted(root.rglob('*.json'))
                  if 'private-' not in p.name and p.name not in ('runtime.json',)
                  and not p.name.endswith('.attempt.json') and p.is_file()]})
    (destination / 'verify.py').write_bytes(Path(__file__).with_name('verify_export.py').read_bytes())
    save(destination / 'manifest.json', {'files': {p.name: digest(p.read_bytes()) for p in sorted(destination.iterdir()) if p.is_file()}})
    print(json.dumps({'exported_cells': len(public['cells']), 'destination': str(destination)}))
