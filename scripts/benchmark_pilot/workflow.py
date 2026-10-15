"""Run two frozen maintenance batches with fresh conversations and file handoffs."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.error

from .corpus import digest, save
from .runner import ingest, request, usage
from .runtime import Runtime
from .tools import SourceTools, schemas
from .workspace import Workspace, frozen_files


def read(path):
    return json.loads(path.read_text())


def workflow_schemas(condition):
    tools = [t for t in schemas(condition, True)
             if condition != 'no_elf' and t['function']['name'].startswith('elf_')]
    for tool in tools:
        if tool['function']['name'] == 'elf_searches_create':
            tool['function']['description'] = 'Find stored project memories. Read their original evidence before applying them.'
    for name, description, properties in [
        ('shell', 'Run a shell command in this isolated current checkout. Inspect, edit, test, and keep HANDOFF.md for the next session. Python and Git are available; network and package installation are unavailable.', {'command': {'type': 'string'}}),
        ('finish_work', 'Finish this session. Files are the deliverable. State remaining gaps honestly and leave a useful HANDOFF.md.', {'summary': {'type': 'string'}}),
    ]:
        tools.append({'type': 'function', 'function': {'name': name, 'description': description,
            'parameters': {'type': 'object', 'properties': properties,
                           'required': list(properties), 'additionalProperties': False}}})
    return tools


def conversation(root, repo, workspace, runtime, sources, documents, protocol, instruction, stage):
    directory = root / f'session-{stage}'
    directory.mkdir(exist_ok=False)
    condition = protocol['condition']
    host = SourceTools(condition, sources, documents, runtime.api if runtime else None, protocol)
    messages = [{'role': 'system', 'content': (
        'Complete the requested ELF maintenance work in the current checkout. Use the provided tools. '
        'This is a fresh session: prior work is available only through files and declared retrieval. '
        'Choose tools that help; native memory is optional. Treat retrieved notes and your own prior '
        'handoff as fallible derived context. Current user requirements control this task. Inspect '
        'original evidence when needed; preserve originals and historical evidence bundles. '
        'You can use Git, ordinary file tools, and Python tests. Cargo is unavailable in the isolated '
        'Python image, so use the equivalent Python test command. Do not install tools. '
        'Leave HANDOFF.md with decisions, changed files, commands, results, and remaining work. '
        'Do not claim unperformed tests or completed work. Use finish_work to end the session.')},
        {'role': 'user', 'content': instruction}]
    trace, calls = [], 0
    started, before = time.monotonic(), usage(root)
    result = {'stage': stage, 'condition': condition, 'status': 'round_budget_exhausted',
              'pid': os.getpid(), 'scripted_requirement_updates': int(stage > 0),
              'observed_human_corrections': None}
    try:
        available = workflow_schemas(condition)
        for turn in range(protocol['max_rounds']):
            closing = turn == protocol['max_rounds'] - 1 or calls >= protocol['max_tool_calls'] - 1
            if closing:
                messages.append({'role': 'user', 'content': 'The fixed session budget is ending. Finish from the current files and state any gaps.'})
            payload, response = request(messages, condition, False, protocol,
                'finish_work' if closing else None, available)
            step = {'request': payload, 'response': response, 'tools': []}
            trace.append(step)
            save(directory / 'trace.json', trace)
            choice = response['choices'][0]
            if choice.get('finish_reason') in ('length', 'error'):
                result['status'] = 'provider_completion_failed'
                break
            message = choice['message']
            messages.append({k: v for k, v in message.items() if k in
                ('role', 'content', 'tool_calls', 'reasoning_content', 'reasoning_details')})
            tool_calls = message.get('tool_calls') or []
            if not tool_calls:
                result.update(status='invalid_finish', summary=message.get('content'))
                break
            for call in tool_calls:
                fn = call['function']
                arguments = json.loads(fn['arguments'])
                calls += 1
                if calls > protocol['max_tool_calls'] or (closing and fn['name'] != 'finish_work'):
                    value = {'error': 'Session tool-call budget exhausted'}
                elif fn['name'] == 'finish_work':
                    result.update(status='completed', summary=arguments['summary'])
                    value = {'completed': True}
                elif fn['name'] == 'shell':
                    cap = min(host.remaining, protocol['max_tool_result_bytes'])
                    if cap <= 0:
                        value = {'error': 'Session evidence budget exhausted'}
                    else:
                        value = workspace.shell(arguments['command'], directory, max(0, cap - 256))
                        host.remaining -= len(json.dumps(value, ensure_ascii=False).encode())
                else:
                    value = host.call(fn['name'], arguments)
                step['tools'].append({'name': fn['name'], 'arguments': arguments, 'result': value})
                save(directory / 'trace.json', trace)
                messages.append({'role': 'tool', 'tool_call_id': call['id'],
                                 'content': json.dumps(value, ensure_ascii=False)})
                if result['status'] == 'completed':
                    break
            if result['status'] == 'completed':
                break
    except urllib.error.HTTPError as error:
        result.update(status='provider_failed', http_status=error.code)
        # Preserve the error for diagnosis without repeating the conversation.
        (directory / 'provider-error.txt').write_bytes(error.read())
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        result.update(status='execution_failed', error=str(error))
    finally:
        result.update(seconds=time.monotonic() - started, tool_calls=calls,
            evidence_bytes=protocol['max_evidence_bytes'] - host.remaining,
            usage_before=before, usage_after=usage(root))
        result['changed_files'] = workspace.snapshot(directory)
        save(directory / 'result.json', result)
        save(directory / 'original-read-receipts.json', host.original_reads)
    return result


def source_record(name, text, stage, revision, timestamp, memory=False):
    return {'id': digest((str(stage) + ':' + name).encode())[:16], 'title': name,
        'path': name, 'text': text, 'sha256': digest(text.encode()), 'stage': stage,
        'timestamp': timestamp, 'commit': revision, 'kind': 'work_record' if memory else 'blob',
        'origin': 'https://github.com/acg-box/ELF', 'extract_memory': memory}


def save_sources(root, sources):
    archive = b''.join((json.dumps(s, ensure_ascii=False) + '\n').encode() for s in sources)
    (root / 'fixture/sources.jsonl.gz').write_bytes(gzip.compress(archive, mtime=0))


def trajectory(experiment, repo, spec, condition, repetition):
    cell = f"{spec['id']}--{condition}--{repetition}"
    root = experiment / 'runs' / cell
    if root.exists():
        if (root / 'completed.json').exists():
            return
        raise RuntimeError('Partial trajectory exists; do not silently rerun: ' + cell)
    root.mkdir(parents=True)
    (root / 'budget-ledger.json').symlink_to(experiment / 'budget-ledger.json')
    protocol = {**read(experiment / 'fixture/protocol.json'), 'condition': condition,
                'conditions': [condition]}
    save(root / 'fixture/protocol.json', protocol)
    workspace = Workspace(root, protocol['workspace_image'], 'elf-workflow-' + cell.replace('_', '-'))
    native = Runtime(root, repo, owner=workspace.name + '-native') if condition != 'no_elf' else None
    if native:
        shutil.copyfile(experiment / 'tokenizer.json', root / 'tokenizer.json')
    started, before = time.monotonic(), usage(root)
    sources, results = [], []
    try:
        workspace.start(protocol['source_repository'], protocol['source_revision'])
        if native:
            native.start()
        for stage, session in enumerate(spec['sessions']):
            instruction = (experiment / 'fixture' / session).read_text()
            inbox = workspace.checkout / 'pilot-requests' / f'{stage}.md'
            inbox.parent.mkdir(exist_ok=True)
            inbox.write_text(instruction)
            paths = spec['source_paths'] if stage == 0 else ['HANDOFF.md']
            for name in paths:
                path = workspace.checkout / name
                if path.is_file():
                    sources.append(source_record(name, path.read_text(), stage,
                        protocol['source_revision'], protocol['source_timestamp'], name == 'HANDOFF.md'))
            sources.append(source_record(f'pilot-requests/{stage}.md', instruction, stage,
                protocol['source_revision'], protocol['source_timestamp'], True))
            for source in sources:
                if source['kind'] == 'work_record':
                    source['canonical_uri'] = f"elf-workflow://{cell}/{source['stage']}/{source['path']}?sha256={source['sha256']}"
            save_sources(root, sources)
            if native:
                ingest(native, root, sources, stage, protocol)
            context = {'root': str(root), 'stage': stage, 'cell': cell,
                       'instruction': instruction, 'sources': sources}
            save(root / 'session-input.json', context)
            command = [os.sys.executable, '-m', 'benchmark_pilot.workflow', str(root), str(repo)]
            env = {**os.environ, 'PYTHONPATH': str(repo / 'scripts')}
            subprocess.run(command, cwd=repo, env=env, check=True)
            result = read(root / f'session-{stage}/result.json')
            results.append(result)
            print(json.dumps({'cell': cell, 'stage': stage, 'status': result['status'],
                              'usage': usage(root)}), flush=True)
            if result['status'] in ('provider_failed', 'execution_failed'):
                raise RuntimeError('Stop after a failed trajectory; preserve all records')
        # Only the evaluator sees these checks; they were absent from the Agent mount.
        evaluator = root / 'evaluate.py'
        shutil.copyfile(experiment / 'fixture' / spec['acceptance'], evaluator)
        with evaluator.open('rb') as script, (root / 'acceptance.log').open('wb') as output:
            assessed = subprocess.run(['docker', 'exec', '-i', workspace.name, 'python3', '-'],
                                     stdin=script, stdout=output, stderr=subprocess.STDOUT, timeout=90)
        changed = results[-1]['changed_files']
        allowed = set(spec['allowed_files']) | {'HANDOFF.md', 'pilot-requests/0.md', 'pilot-requests/1.md'}
        unexpected = [p for p in changed if p not in allowed]
        save(root / 'completed.json', {'cell': cell, 'batch': spec['id'], 'condition': condition,
            'repetition': repetition, 'acceptance_passed': assessed.returncode == 0,
            'scope_passed': not unexpected, 'unexpected_files': unexpected,
            'sessions_completed': sum(r['status'] == 'completed' for r in results),
            'seconds_including_preparation': time.monotonic() - started,
            'usage_before': before, 'usage_after': usage(root)})
    finally:
        workspace.close()
        if native:
            native.close()


def run_workflow(args, repo):
    frozen_files(args.root / 'fixture')
    spec = read(args.root / 'fixture/batches.json')
    selected = [b for b in spec if b['id'] == args.batch]
    if len(selected) != 1:
        raise ValueError('Choose one frozen --batch')
    protocol = read(args.root / 'fixture/protocol.json')
    if args.batch != 'calibration':
        for condition in protocol['conditions']:
            path = args.root / 'runs' / f'calibration--{condition}--1' / 'completed.json'
            result = read(path)
            if not result['acceptance_passed'] or not result['scope_passed']:
                raise ValueError('Inspect calibration before a formal batch')
    for repetition in range(1, selected[0].get('repetitions', protocol['repetitions']) + 1):
        arms = protocol['conditions']
        offset = (repetition - 1) % len(arms)
        for condition in arms[offset:] + arms[:offset]:
            if (args.root / 'STOP').exists():
                raise RuntimeError('Operator STOP marker present')
            trajectory(args.root, repo, selected[0], condition, repetition)
    return 0


if __name__ == '__main__':
    import sys
    root, repo = map(Path, sys.argv[1:])
    context, protocol = read(root / 'session-input.json'), read(root / 'fixture/protocol.json')
    workspace = Workspace(root, protocol['workspace_image'], 'elf-workflow-' + context['cell'].replace('_', '-'))
    native = Runtime(root, repo) if protocol['condition'] != 'no_elf' else None
    documents = read(root / 'documents.json') if native else {}
    conversation(root, repo, workspace, native, context['sources'], documents,
                 protocol, context['instruction'], context['stage'])
