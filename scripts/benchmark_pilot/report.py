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
        tools = [tool for step in trace for tool in step['tools']]
        tool_counts = Counter(tool['name'] for tool in tools)
        budget_errors = sum('evidence-byte budget' in str(tool['result'].get('error', '')) for tool in tools)
        empty_truncations = sum(tool['result'].get('truncated') is True and tool['result'].get('items') == [] for tool in tools)
        memory_completions = sum(tool['name'] in ('search_memories', 'evidence_pack', 'recall_evidence', 'query_graph', 'elf_searches_create', 'elf_searches_get', 'elf_evidence_pack', 'elf_evidence_recall', 'elf_graph_query') and 'error' not in tool['result'] for tool in tools)
        results.append({k: row[k] for k in ('cell', 'task_id', 'phase', 'condition', 'repetition', 'status', 'seconds', 'tool_calls', 'evidence_bytes')} | {
            'cohort': next(t.get('cohort', 'original') for t in tasks if t['id'] == row['task_id']),
            'criteria': criteria, 'text_pattern_coverage': sum(c['text_patterns_present'] for c in criteria) / len(criteria),
            'native_binding': bool(binding) and all(c['binding_verified'] for c in binding),
            'all_references_seen': row.get('all_references_seen', False), 'usage': usage,
            'tool_counts': dict(tool_counts),
            'evidence_budget_errors': budget_errors, 'empty_truncated_results': empty_truncations,
            'memory_tool_completions': memory_completions,
            'memory_evidence_reads': sum(tool['name'] in ('evidence_pack', 'elf_evidence_pack', 'recall_evidence', 'elf_evidence_recall')
                and bool(tool['result'].get('pack', tool['result']).get('notes'))
                and bool(tool['result'].get('pack', tool['result']).get('sources')) for tool in tools),
            'citation_checks': tool_counts.get('elf_evidence_check', 0),
            'failed_citation_checks': sum(tool['name'] == 'elf_evidence_check' and
                any(not c['binding_verified'] for c in tool['result'].get('claims', [])) for tool in tools),
            'provider_requests': len(requests), 'cost_exposure_usd': totals({'requests': requests})[1],
            'paid_usd': row['usage_after']['paid_usd'] - row['usage_before']['paid_usd']})
    review_path = root / 'review.json'
    reviews = json.loads(review_path.read_text()) if review_path.exists() else {}
    paired = {}
    for row in results:
        if row['phase'] == 'formal':
            paired.setdefault((row['task_id'], row['repetition']), []).append(row)
    comparable = {key for key, group in paired.items()
                  if len(group) == len(protocol['conditions'])
                  and not any(row['status'] in ('transport_failed', 'harness_failed') for row in group)}
    summary = {}
    for condition in protocol['conditions']:
        rows = [r for r in results if r['phase'] == 'formal' and r['condition'] == condition]
        times = sorted(r['seconds'] for r in rows)
        reviewed = [reviews[r['cell']] for r in rows if r['cell'] in reviews]
        matched = [row for row in rows if (row['task_id'], row['repetition']) in comparable and row['cell'] in reviews]
        summary[condition] = {
            'planned': sum(t['phase'] == 'formal' for t in tasks) * protocol['formal_repetitions'],
            'measured': len(rows), 'completed': sum(r['status'] == 'completed' for r in rows),
            'text_pattern_coverage': statistics.mean(r['text_pattern_coverage'] for r in rows) if rows else None,
            'native_binding_pass': sum(r['native_binding'] and r['all_references_seen'] for r in rows),
            'reviewed': len(reviewed), 'semantic_acceptance': sum(r['accepted'] for r in reviewed),
            'reviewed_criteria': sum(len(r['criteria']) for r in rows if r['cell'] in reviews),
            'passed_criteria': sum(r['passed_criteria'] for r in reviewed),
            'answered_criteria': sum(len(r['criteria']) for r in rows if r['status'] == 'completed' and r['cell'] in reviews),
            'answered_passed_criteria': sum(reviews[r['cell']]['passed_criteria'] for r in rows if r['status'] == 'completed' and r['cell'] in reviews),
            'matched_content_cells': len(matched),
            'matched_criteria': sum(len(row['criteria']) for row in matched),
            'matched_passed_criteria': sum(reviews[row['cell']]['passed_criteria'] for row in matched),
            'matched_accepted': sum(reviews[row['cell']]['accepted'] for row in matched),
            'matched_native_binding_pass': sum(row['native_binding'] and row['all_references_seen'] for row in matched),
            'matched_paid_usd': sum(row['paid_usd'] for row in matched),
            'matched_median_seconds': statistics.median(row['seconds'] for row in matched) if matched else None,
            'median_seconds': statistics.median(times) if rows else None,
            'p95_seconds': times[math.ceil(len(times) * .95) - 1] if rows else None,
            'tool_calls': sum(r['tool_calls'] for r in rows),
            'tool_counts': dict(sum((Counter(r['tool_counts']) for r in rows), Counter())),
            'cells_with_budget_loss': sum(bool(r['evidence_budget_errors'] or r['empty_truncated_results']) for r in rows),
            'memory_tool_cells': sum(any(r['tool_counts'].get(name) for name in ('search_memories', 'evidence_pack', 'recall_evidence', 'query_graph', 'elf_searches_create', 'elf_searches_get', 'elf_evidence_pack', 'elf_evidence_recall', 'elf_graph_query')) for r in rows),
            'memory_tool_completed_cells': sum(bool(r['memory_tool_completions']) for r in rows),
            'memory_evidence_cells': sum(bool(r['memory_evidence_reads']) for r in rows),
            'citation_check_cells': sum(bool(r['citation_checks']) for r in rows),
            'citation_repair_cells': sum(bool(r['failed_citation_checks']) and r['native_binding'] and r['all_references_seen'] for r in rows),
            'source_search_cells': sum(bool(r['tool_counts'].get('search_sources') or r['tool_counts'].get('elf_docs_search_l0')) for r in rows),
            'paid_usd': sum(r['paid_usd'] for r in rows),
            'cost_exposure_usd': sum(r['cost_exposure_usd'] for r in rows),
            'prompt_tokens': sum(r['usage']['prompt_tokens'] for r in rows),
            'cached_prompt_tokens': sum(r['usage']['cached_prompt_tokens'] for r in rows),
            'cache_write_prompt_tokens': sum(r['usage']['cache_write_prompt_tokens'] for r in rows),
            'reasoning_tokens': sum(r['usage']['reasoning_tokens'] for r in rows),
            'completion_tokens': sum(r['usage']['completion_tokens'] for r in rows)}
    for condition, value in summary.items():
        value['cohorts'] = {}
        for cohort in sorted({r['cohort'] for r in results if r['phase'] == 'formal'}):
            matched = [r for r in results if r['phase'] == 'formal' and r['condition'] == condition
                       and r['cohort'] == cohort and (r['task_id'], r['repetition']) in comparable and r['cell'] in reviews]
            value['cohorts'][cohort] = {
                'matched_cells': len(matched), 'criteria': sum(len(r['criteria']) for r in matched),
                'passed_criteria': sum(reviews[r['cell']]['passed_criteria'] for r in matched),
                'accepted': sum(reviews[r['cell']]['accepted'] for r in matched),
                'mean_paid_usd': statistics.mean(r['paid_usd'] for r in matched) if matched else None,
                'median_seconds': statistics.median(r['seconds'] for r in matched) if matched else None}
    setup = {'source_index': {'seconds': 0, 'paid_usd': 0}, 'memory': {'seconds': 0, 'paid_usd': 0}}
    writes = {'windows': 0, 'candidates': 0, 'operations': Counter(), 'rejections': Counter()}
    for path in (root / 'ingest').glob('*.json'):
        if path.name.endswith('.attempt.json'):
            continue
        row = json.loads(path.read_text())
        kind = 'source_index' if path.name.endswith('-document.json') else 'memory'
        setup[kind]['seconds'] += row['seconds']
        setup[kind]['paid_usd'] += row['after']['paid_usd'] - row['before']['paid_usd']
        if kind == 'memory':
            response = row['response']
            writes['windows'] += 1
            writes['candidates'] += len(response.get('extracted', {}).get('notes', []))
            for result in response.get('results', []):
                writes['operations'][result['op']] += 1
                if result.get('reason_code'):
                    writes['rejections'][result['reason_code']] += 1
    for condition, value in summary.items():
        prep = 0 if condition == 'no_elf' else setup['source_index']['paid_usd']
        prep += setup['memory']['paid_usd'] if condition == 'full_elf' else 0
        mean = value['matched_paid_usd'] / value['matched_content_cells'] if value['matched_content_cells'] else None
        value['amortized_usd_per_task'] = None if protocol.get('frozen_extraction') else {
            str(n): prep / n + mean if mean is not None else None for n in (1, 5, 20)}
    paid, exposure = totals(ledger)
    exploration_path = root / 'exploration.json'
    exploration_count = json.loads(exploration_path.read_text())['prior_request_count'] if exploration_path.exists() else 0
    exploration_paid, exploration_exposure = totals({'requests': ledger['requests'][:exploration_count]})
    diagnostic_path = root / 'retrieval-diagnostic.json'
    diagnostic = json.loads(diagnostic_path.read_text()) if diagnostic_path.exists() else None
    diagnostic_summary = None if diagnostic is None else {
        'status': diagnostic.get('status', 'incomplete'), 'queries': len(diagnostic['queries']),
        'paid_usd': diagnostic['after']['paid_usd'] - diagnostic['before']['paid_usd'],
        'graph_counts': diagnostic.get('graph_counts', {}),
        'query_results': [{'candidates': len(row.get('search', {}).get('items', [])),
                           'sources': len(row.get('pack', {}).get('sources', [])),
                           'complete_notes': sum(note['complete'] for note in row.get('pack', {}).get('notes', [])),
                           'pack_complete': row.get('pack', {}).get('complete', False),
                           'source_bytes': row.get('pack', {}).get('source_bytes', 0),
                           'seconds': row.get('seconds')} for row in diagnostic['queries']]}
    return {'schema': 'elf.real_project_measurements/v1', 'summary': summary, 'cells': results,
            'preparation': setup,
            'preparation_cost_basis': 'Incremental replay cost; cold-start amortization is not estimated.' if protocol.get('frozen_extraction') else 'Recorded provider preparation cost.',
            'new_budget': {'paid_usd': paid, 'exposure_usd': exposure, 'ceiling_usd': 10},
            'exploration': {'requests': exploration_count, 'paid_usd': exploration_paid, 'exposure_usd': exploration_exposure},
            'native_writes': writes,
            'native_recall_diagnostic': diagnostic_summary,
            'review_boundary': 'Text-pattern coverage is diagnostic only. Semantic reviews are explicit, source-based assistant assessments, not independent judges. Native binding does not prove entailment.'}


def write_report(root, fixture):
    value = measurements(root, fixture)
    save(root / 'measurements.json', value)
    print(json.dumps({'summary': value['summary'], 'preparation': value['preparation'], 'budget': value['new_budget']}, indent=2))
