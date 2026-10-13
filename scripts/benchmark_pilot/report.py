"""Produce reproducible measurements; text matches are not semantic acceptance."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
import statistics
from collections import Counter

from benchmark_budget import totals
from .corpus import save


def measurements(root, fixture):
    oracle = {r['id']: r for r in json.loads((fixture / 'oracle.json').read_text())}
    tasks = json.loads((fixture / 'tasks.json').read_text())
    protocol = json.loads((fixture / 'protocol.json').read_text())
    ledger = json.loads((root / 'budget-ledger.json').read_text())
    results = []
    for path in sorted((root / 'cases').glob('*/result.json')):
        row = json.loads(path.read_text())
        answer = row.get('answer', {})
        text = '\n'.join([answer.get('text', ''), *[c.get('text', '') for c in answer.get('claims', [])]])
        criteria = [{**c, 'text_patterns_present': all(re.search(p, text, re.I | re.S) for p in c['patterns'])}
                    for c in oracle[row['task_id']]['criteria']]
        lower = row['usage_before']['requests']
        upper = row['usage_after']['requests']
        requests = ledger['requests'][lower:upper]
        usage = {k: sum(r.get('usage', {}).get(k, 0) or 0 for r in requests)
                 for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
        usage['cached_prompt_tokens'] = sum((r.get('usage', {}).get('prompt_tokens_details') or {}).get('cached_tokens', 0) or 0 for r in requests)
        usage['cache_write_prompt_tokens'] = sum((r.get('usage', {}).get('prompt_tokens_details') or {}).get('cache_write_tokens', 0) or 0 for r in requests)
        usage['reasoning_tokens'] = sum((r.get('usage', {}).get('completion_tokens_details') or {}).get('reasoning_tokens', 0) or 0 for r in requests)
        binding = row.get('claim_bindings', {}).get('claims', [])
        trace = json.loads((path.parent / 'trace.json').read_text())
        tool_counts = Counter(tool['name'] for step in trace for tool in step['tools'])
        results.append({k: row[k] for k in ('cell', 'task_id', 'phase', 'condition', 'repetition', 'status', 'seconds', 'tool_calls', 'evidence_bytes')} | {
            'criteria': criteria, 'text_pattern_coverage': sum(c['text_patterns_present'] for c in criteria) / len(criteria),
            'native_binding': bool(binding) and all(c['binding_verified'] for c in binding),
            'all_references_seen': row.get('all_references_seen', False), 'usage': usage,
            'tool_counts': dict(tool_counts),
            'provider_requests': len(requests), 'paid_usd': row['usage_after']['paid_usd'] - row['usage_before']['paid_usd']})
    review_path = root / 'review.json'
    reviews = json.loads(review_path.read_text()) if review_path.exists() else {}
    summary = {}
    for condition in protocol['conditions']:
        rows = [r for r in results if r['phase'] == 'formal' and r['condition'] == condition]
        times = sorted(r['seconds'] for r in rows)
        reviewed = [reviews[r['cell']] for r in rows if r['cell'] in reviews]
        summary[condition] = {
            'planned': sum(t['phase'] == 'formal' for t in tasks) * protocol['formal_repetitions'],
            'measured': len(rows), 'completed': sum(r['status'] == 'completed' for r in rows),
            'text_pattern_coverage': statistics.mean(r['text_pattern_coverage'] for r in rows) if rows else None,
            'native_binding_pass': sum(r['native_binding'] and r['all_references_seen'] for r in rows),
            'reviewed': len(reviewed), 'semantic_acceptance': sum(r['accepted'] for r in reviewed),
            'reviewed_criteria': sum(len(r['criteria']) for r in rows if r['cell'] in reviews),
            'passed_criteria': sum(r['passed_criteria'] for r in reviewed),
            'median_seconds': statistics.median(times) if rows else None,
            'p95_seconds': times[math.ceil(len(times) * .95) - 1] if rows else None,
            'tool_calls': sum(r['tool_calls'] for r in rows),
            'tool_counts': dict(sum((Counter(r['tool_counts']) for r in rows), Counter())),
            'paid_usd': sum(r['paid_usd'] for r in rows),
            'prompt_tokens': sum(r['usage']['prompt_tokens'] for r in rows),
            'cached_prompt_tokens': sum(r['usage']['cached_prompt_tokens'] for r in rows),
            'cache_write_prompt_tokens': sum(r['usage']['cache_write_prompt_tokens'] for r in rows),
            'reasoning_tokens': sum(r['usage']['reasoning_tokens'] for r in rows),
            'completion_tokens': sum(r['usage']['completion_tokens'] for r in rows)}
    setup = {'source_index': {'seconds': 0, 'paid_usd': 0}, 'memory': {'seconds': 0, 'paid_usd': 0}}
    for path in (root / 'ingest').glob('*.json'):
        if path.name.endswith('.attempt.json'):
            continue
        row = json.loads(path.read_text())
        kind = 'source_index' if path.name.endswith('-document.json') else 'memory'
        setup[kind]['seconds'] += row['seconds']
        setup[kind]['paid_usd'] += row['after']['paid_usd'] - row['before']['paid_usd']
    for condition, value in summary.items():
        prep = 0 if condition == 'no_elf' else setup['source_index']['paid_usd']
        prep += setup['memory']['paid_usd'] if condition == 'full_elf' else 0
        mean = value['paid_usd'] / value['measured'] if value['measured'] else None
        value['amortized_usd_per_task'] = {str(n): prep / n + mean if mean is not None else None for n in (1, 5, 20)}
    paid, exposure = totals(ledger)
    exploration_path = root / 'exploration.json'
    exploration_count = json.loads(exploration_path.read_text())['prior_request_count'] if exploration_path.exists() else 0
    exploration_paid, exploration_exposure = totals({'requests': ledger['requests'][:exploration_count]})
    return {'schema': 'elf.real_project_measurements/v1', 'summary': summary, 'cells': results,
            'preparation': setup, 'new_budget': {'paid_usd': paid, 'exposure_usd': exposure, 'ceiling_usd': 10},
            'exploration': {'requests': exploration_count, 'paid_usd': exploration_paid, 'exposure_usd': exploration_exposure},
            'review_boundary': 'Text-pattern coverage is diagnostic only. Semantic reviews are explicit, source-based assistant assessments, not independent judges. Native binding does not prove entailment.'}


def write_report(root, fixture):
    value = measurements(root, fixture)
    save(root / 'measurements.json', value)
    print(json.dumps({'summary': value['summary'], 'preparation': value['preparation'], 'budget': value['new_budget']}, indent=2))
