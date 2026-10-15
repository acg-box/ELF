"""Chronological native ingestion and independent, bounded agent conversations."""
from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

from benchmark_budget import totals
from .corpus import digest, load, save, spans
from .runtime import Runtime
from .tools import SourceTools, opening_tool, schemas
from .evidence import compact_check


def read(path):
    return json.loads(path.read_text())


def usage(root):
    ledger = read(root / 'budget-ledger.json')
    paid, exposure = totals(ledger)
    return {'paid_usd': paid, 'exposure_usd': exposure, 'requests': len(ledger['requests'])}


def request(messages, condition, closing, protocol, required_tool=None, tool_schemas=None):
    payload = {'model': protocol['model'], 'messages': messages,
               'max_tokens': protocol['max_output_tokens'], 'reasoning': {'effort': protocol['reasoning']}}
    if protocol.get('client_v3'):
        available = schemas(condition, True) if tool_schemas is None else tool_schemas
        if closing:
            available = [tool for tool in available if tool['function']['name'] == 'submit_answer']
            required_tool = 'submit_answer'
        payload.update(tools=available, tool_choice={'type': 'function', 'function': {'name': required_tool}} if required_tool else 'required')
    elif not closing:
        payload.update(tools=schemas(condition), tool_choice={'type': 'function', 'function': {'name': required_tool}} if required_tool else 'auto')
    req = urllib.request.Request(os.environ['LITELLM_BASE_URL'] + '/chat/completions',
        data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + os.environ['LITELLM_API_KEY']})
    with urllib.request.urlopen(req, timeout=3600) as response:
        return payload, json.load(response)


def cell(args, repo, sources, checkpoints, protocol, task):
    """The reader receives only this question, its visible sources, and allowed tools."""
    target = args.root / 'cases' / args.cell / 'result.json'
    trace_path = target.parent / 'trace.json'
    if target.exists() or trace_path.exists():
        raise ValueError('Never repeat a recorded cell or partial conversation')
    rt = Runtime(args.root, repo)
    documents = read(args.root / 'documents.json')
    visible = [s for s in sources if s['stage'] <= task['stage']]
    host = SourceTools(args.condition, visible, documents, rt.api, protocol)
    messages = [{'role': 'system', 'content': (repo / 'config/agent/evidence-reader.md').read_text()},
                {'role': 'user', 'content': json.dumps({'task': task['question'],
                 'checkpoint': checkpoints[task['stage']],
                 'instructions': 'Use the declared retrieval and read tools to inspect immutable original evidence before answering. File and native reads return the same original evidence references. The host will check your final claims through ELF. Do not infer current external service state from repository history. Return only the shared-contract JSON.',
                 'sources': [{k: s[k] for k in ('id', 'title', 'timestamp')} for s in visible]}, ensure_ascii=False)}]
    if protocol.get('client_v3'):
        messages.append({'role': 'user', 'content': 'This host assigns conversation-local E-number handles to original references. Use those handles unchanged in citations. Submit through submit_answer; the host resolves handles and checks the complete final chain before rendering. Native references remain private host metadata.'})
    provided = None
    if args.condition == 'exact_source':
        provided = host.provide(read(args.root / 'fixture/exact-source.json')[task['id']])
        messages.append({'role': 'user', 'content': json.dumps(provided, ensure_ascii=False)})
    started = time.monotonic()
    trace, calls = [], 0
    before = usage(args.root)
    result = {'cell': args.cell, 'task_id': task['id'], 'condition': args.condition,
              'repetition': args.repetition, 'phase': task['phase'], 'pid': os.getpid(),
              'stage': task['stage'], 'status': 'round_budget_exhausted'}
    if provided is not None:
        result['provided_originals'] = provided
    try:
        for turn in range(protocol['max_rounds']):
            closing = turn == protocol['max_rounds'] - 1 or calls >= protocol['max_tool_calls'] - int(bool(protocol.get('client_v3')))
            if closing:
                messages.append({'role': 'user', 'content': 'This is the final turn in the fixed workflow budget. Return your JSON answer from the evidence already inspected. Mark unestablished facts unknown.'})
            required_tool = opening_tool(args.condition, trace, protocol.get('hydrate_sources', False)) if protocol.get('host_opening') and args.condition != 'exact_source' else None
            if protocol.get('client_v3'):
                messages.append({'role': 'user', 'content': f'Host budget: {host.remaining} evidence bytes and {protocol["max_tool_calls"] - calls} tool calls remain. Read only to close a named gap. Before submit_answer, cover each requested part and keep the subject, applicable time, conditions, and exclusions from its cited original. submit_answer performs the final binding check.'})
            payload, response = request(messages, args.condition, closing, protocol, required_tool)
            step = {'turn': turn, 'request': payload, 'response': response, 'tools': []}
            trace.append(step)
            save(trace_path, trace)
            choice = response['choices'][0]
            if choice.get('finish_reason') in ('length', 'error'):
                result['status'] = 'provider_completion_failed'
                break
            message = choice['message']
            messages.append({k: v for k, v in message.items() if k in ('role', 'content', 'tool_calls', 'reasoning_content', 'reasoning_details')})
            tool_calls = message.get('tool_calls') or []
            if not tool_calls:
                content = message.get('content') or ''
                result['raw_answer'] = content
                if protocol.get('client_v3'):
                    result.update(status='invalid_answer', error='The client contract requires submit_answer')
                    break
                try:
                    answer = json.loads(content)
                    if not isinstance(answer.get('text'), str) or not isinstance(answer.get('supported'), bool) or not isinstance(answer.get('claims'), list):
                        raise ValueError('Expected text, supported and claims')
                    result['answer'] = answer
                    claimed = [c['reference'] for claim in answer['claims'] for c in claim.get('citations', []) if c.get('kind') == 'reference']
                    result['all_references_seen'] = bool(claimed) and all(ref in host.references for ref in claimed)
                    result['claim_bindings'] = rt.api('/v2/evidence/check', {'claims': answer['claims']})
                    result['status'] = 'completed'
                except (ValueError, KeyError, TypeError) as error:
                    result.update(status='invalid_answer', error=str(error))
                break
            for call in tool_calls:
                fn = call['function']
                if fn['name'] == 'submit_answer' and protocol.get('client_v3') and calls < protocol['max_tool_calls']:
                    calls += 1
                    arguments = json.loads(fn['arguments'])
                    try:
                        final = host.finalize(arguments)
                        value = compact_check(final['claim_bindings'])
                        if not all(c['binding_verified'] for c in value['claims']) and not closing:
                            value['error'] = 'The complete answer has invalid bindings. Repair before resubmitting.'
                        else:
                            result.update(final, raw_answer=json.dumps(arguments, ensure_ascii=False), status='completed')
                    except (ValueError, KeyError, TypeError) as error:
                        value = {'error': str(error)}
                        if closing:
                            result.update(status='invalid_answer', error=str(error), raw_answer=json.dumps(arguments, ensure_ascii=False))
                    step['tools'].append({'name': fn['name'], 'arguments': arguments, 'result': value})
                    save(trace_path, trace)
                    messages.append({'role': 'tool', 'tool_call_id': call['id'], 'content': json.dumps(value)})
                    if result['status'] in ('completed', 'invalid_answer'):
                        break
                    continue
                if closing or calls >= protocol['max_tool_calls']:
                    value = {'error': 'Tool-call budget exhausted.'}
                else:
                    try:
                        arguments = json.loads(fn['arguments'])
                        value = host.call(fn['name'], arguments)
                    except (ValueError, TypeError) as error:
                        arguments, value = {}, {'error': str(error)}
                    calls += 1
                    step['tools'].append({'name': fn['name'], 'arguments': arguments, 'result': value})
                    save(trace_path, trace)
                messages.append({'role': 'tool', 'tool_call_id': call['id'], 'content': json.dumps(value, ensure_ascii=False)})
            if result['status'] in ('completed', 'invalid_answer'):
                break
    except urllib.error.HTTPError as error:
        detail = error.read().decode()
        result.update(status='transport_failed', error={'http_status': error.code, 'detail': detail})
    except (OSError, ValueError, KeyError, TypeError) as error:
        result.update(status='harness_failed', error=str(error))
    finally:
        result.update(seconds=time.monotonic() - started, tool_calls=calls,
                      evidence_bytes=protocol['max_evidence_bytes'] - host.remaining,
                      usage_before=before, usage_after=usage(args.root))
        save(target, result)
        if host.handles:
            save(target.parent / 'evidence-handles.json', {'native': host.handles.native, 'visible': sorted(host.handles.visible)})
            save(target.parent / 'original-read-receipts.json', host.original_reads)
        print(json.dumps({k: result[k] for k in ('cell', 'status', 'seconds', 'tool_calls', 'usage_after')}), flush=True)
    return 2 if result['status'] in ('transport_failed', 'harness_failed') else 0


def ingest(rt, root, sources, stage, protocol):
    documents_path = root / 'documents.json'
    documents = read(documents_path) if documents_path.exists() else {}
    selected = [s for s in sources if s['stage'] == stage]
    for source in selected:
        if source['id'] in documents:
            continue
        before = usage(root)
        started = time.monotonic()
        body = {'scope': 'agent_private', 'title': source['title'], 'source_ref': {
            'schema': 'doc_source_ref/v1', 'doc_type': 'dev', 'ts': source['timestamp'],
            'repo': source['origin'], 'commit_sha': source['commit'],
            'source_kind': 'repo_file',
            'canonical_uri': source['origin'] + ('/blob/' + source['commit'] + '/' + source['path']
                if source['kind'] == 'blob' else '/commit/' + source['commit']),
            'captured_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_created_at': source['timestamp'], 'trust_label': 'user_captured',
            'pilot_source_id': source['id']}, 'content': source['text']}
        if source['kind'] == 'work_record':
            body['source_ref'].update(doc_type='chat', source_kind='chat_excerpt',
                thread_id=source['canonical_uri'].split('/')[2],
                role='assistant' if source['path'] == 'HANDOFF.md' else 'user',
                canonical_uri=source['canonical_uri'], source_content_hash=source['sha256'],
                trust_label='unverified' if source['path'] == 'HANDOFF.md' else 'user_captured')
            body['source_ref'].pop('commit_sha')
            body['source_ref'].pop('repo')
        try:
            doc = rt.api('/v2/docs', body)
        except urllib.error.HTTPError as error:
            if not protocol.get('record_source_policy_rejections'):
                raise
            detail = error.read().decode(errors='replace')
            if error.code != 400 or json.loads(detail).get('message') != 'content contains secrets.':
                raise RuntimeError('Unexpected native document rejection: ' + detail) from error
            save(root / 'ingest' / (source['id'] + '-source-rejected.json'), {
                'source_id': source['id'], 'path': source['path'], 'sha256': source['sha256'],
                'http_status': error.code, 'error': json.loads(detail),
                'before': before, 'after': usage(root), 'seconds': time.monotonic() - started})
            continue
        documents[source['id']] = doc
        save(documents_path, documents)
        rt.drain()
        save(root / 'ingest' / (source['id'] + '-document.json'), {'document': doc,
            'seconds': time.monotonic() - started, 'before': before, 'after': usage(root)})
    admitted = [s for s in sources if s['id'] in documents] if protocol.get('record_source_policy_rejections') else sources
    if 'full_elf' not in protocol['conditions']:
        verify_state(rt, root, admitted, documents, stage)
        return
    for source in (s for s in selected if s.get('extract_memory', True) and s['id'] in documents):
        doc = documents[source['id']]
        for i, (start, end, text) in enumerate(spans(source['text'], protocol['extraction_window_bytes'])):
            path = root / 'ingest' / (source['id'] + f'-memory-{i}.json')
            if path.exists():
                continue
            attempt = path.with_suffix('.attempt.json')
            if attempt.exists():
                raise RuntimeError('Unresolved extraction attempt; do not resend: ' + str(attempt))
            body = {'scope': 'agent_private', 'dry_run': False, 'messages': [{
                'role': 'user', 'content': text, 'ts': source['timestamp'],
                'msg_id': source['id'] + f'-{i}', 'source_document': {
                    'doc_id': doc['doc_id'], 'content_hash': doc['content_hash'],
                    'position': {'start': start, 'end': end}}}]}
            before, started = usage(root), time.monotonic()
            save(attempt, {'source_id': source['id'], 'start': start, 'end': end, 'before': before})
            try:
                response = rt.api('/v2/events/ingest', body)
                status = 'completed'
            except urllib.error.HTTPError as error:
                if error.code >= 500 or error.code == 402:
                    raise
                response, status = {'http_status': error.code, 'detail': error.read().decode()}, 'rejected'
            rt.drain()
            save(path, {'source_id': source['id'], 'start': start, 'end': end, 'status': status,
                'response': response, 'seconds': time.monotonic() - started,
                'before': before, 'after': usage(root)})
            print(json.dumps({'event': 'memory_ingest', 'source_id': source['id'], 'window': i,
                              'status': status, 'usage': usage(root)}), flush=True)
    verify_state(rt, root, admitted, documents, stage)


def verify_state(rt, root, sources, documents, stage):
    native = json.loads(rt.sql("SELECT COALESCE(json_agg(d),'[]'::json) FROM (SELECT doc_id,content FROM doc_documents) d"))
    actual = {d['doc_id']: d['content'] for d in native}
    expected = [s for s in sources if s['stage'] <= stage]
    for source in expected:
        if digest(actual[documents[source['id']]['doc_id']].encode()) != source['sha256']:
            raise ValueError('Native original bytes changed: ' + source['id'])
    if len(actual) != len(expected):
        raise ValueError('Future or unrelated documents in the native store')
    vectors = {}
    for table in ['doc_chunk_embeddings', 'note_embeddings', 'note_chunk_embeddings', 'note_field_embeddings']:
        vectors[table] = json.loads(rt.sql(f"SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT embedding_dim, count(*) FROM {table} GROUP BY embedding_dim) t"))
        if any(row['embedding_dim'] != 4096 for row in vectors[table]):
            raise ValueError('Full 4096-dimensional embedding requirement failed')
    notes = json.loads(rt.sql("SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT note_id,type,key,text,status,source_ref FROM memory_notes ORDER BY note_id) t"))
    save(root / f'native-stage-{stage}.json', {'stage': stage, 'sources_verified': len(expected),
         'source_sha256': {s['id']: s['sha256'] for s in expected}, 'vectors': vectors, 'notes': notes})


def run(args, repo, sources, checkpoints, protocol, tasks):
    selected = [t for t in tasks if t['phase'] == args.phase]
    rt = Runtime(args.root, repo)
    try:
        rt.start()
        for stage in sorted({t['stage'] for t in selected}):
            marker = args.root / f'{args.phase}-stage-{stage}-completed.json'
            if marker.exists():
                continue
            ingest(rt, args.root, sources, stage, protocol)
            for task_index, task in enumerate(t for t in selected if t['stage'] == stage):
                for repetition in range(protocol[args.phase + '_repetitions']):
                    order = protocol['conditions']
                    offset = (task_index + repetition + stage) % len(order)
                    for condition in order[offset:] + order[:offset]:
                        cell_id = f"{task['id']}--{condition}--{repetition + 1}"
                        target = args.root / 'cases' / cell_id / 'result.json'
                        if target.exists():
                            continue
                        if (args.root / 'STOP').exists():
                            raise RuntimeError('Operator STOP marker present')
                        command = [sys.executable, str(repo / 'scripts/benchmark-project-pilot.py'),
                                   '--root', str(args.root), '--phase', args.phase, '--cell', cell_id,
                                   '--condition', condition, '--task', task['id'], '--repetition', str(repetition + 1)]
                        result = subprocess.run(command, cwd=repo)
                        if result.returncode:
                            raise RuntimeError('Cell stopped; preserve result and diagnose before continuing: ' + cell_id)
            rt.drain()
            save(marker, {'stage': stage, 'usage': usage(args.root)})
        save(args.root / (args.phase + '-completed.json'), {'phase': args.phase, 'usage': usage(args.root)})
    finally:
        rt.close()


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--phase', choices=['calibration', 'formal', 'report', 'export', 'workflow'], required=True)
    parser.add_argument('--batch')
    parser.add_argument('--export-dir', type=Path)
    parser.add_argument('--cell')
    parser.add_argument('--task')
    parser.add_argument('--condition', choices=['no_elf', 'source_only', 'full_elf', 'exact_source'])
    parser.add_argument('--repetition', type=int, default=1)
    args = parser.parse_args()
    args.root = args.root.resolve()
    args.root.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parents[2]
    if args.phase == 'workflow':
        from .workflow import run_workflow
        return run_workflow(args, repo)
    frozen = args.root / 'fixture'
    sources, checkpoints = load(frozen)
    origin = read(frozen / 'freeze.json')['repository']
    for source in sources:
        source['origin'] = origin
    protocol, tasks = read(frozen / 'protocol.json'), read(frozen / 'tasks.json')
    if args.phase == 'report':
        from .report import write_report
        write_report(args.root, frozen)
        return 0
    if args.phase == 'export':
        from .export import export
        if args.export_dir is None:
            raise ValueError('Specify a new --export-dir for de-identified evidence')
        export(args.root, args.export_dir)
        return 0
    if args.cell:
        task = next(t for t in tasks if t['id'] == args.task)
        return cell(args, repo, sources, checkpoints, protocol, task)
    if args.phase == 'formal' and not (args.root / 'calibration-completed.json').exists():
        raise ValueError('Complete and inspect calibration before the formal tranche')
    run(args, repo, sources, checkpoints, protocol, tasks)
    return 0
