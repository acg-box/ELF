"""Capture immutable Git records; keep the answer oracle on the host."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import subprocess


def digest(value):
    return hashlib.sha256(value).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def capture(repo, out, plan):
    if (out / 'freeze.json').exists():
        raise ValueError('A frozen workload is immutable; select a new output directory')
    stages = []
    for name, revision in plan['checkpoints']:
        commit = git(repo, 'rev-parse', revision).decode().strip()
        timestamp = git(repo, 'show', '-s', '--format=%cI', commit).decode().strip()
        stages.append({'id': name, 'commit': commit, 'timestamp': timestamp})
    for before, after in zip(stages, stages[1:]):
        subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor',
                        before['commit'], after['commit']], check=True)
    sources = []
    for stage, path in plan['records']:
        revision = stages[stage]['commit']
        raw = git(repo, 'show', revision + ':' + path)
        sources.append({'stage': stage, 'path': path, 'commit': revision,
                        'timestamp': stages[stage]['timestamp'], 'kind': 'blob',
                        'blob': git(repo, 'rev-parse', revision + ':' + path).decode().strip(),
                        'text': raw.decode(), 'sha256': digest(raw)})
    for stage in range(len(stages)):
        revision = stages[stage]['commit']
        raw = git(repo, 'show', '-s', '--format=%B', revision)
        sources.append({'stage': stage, 'path': 'COMMIT_MESSAGE', 'commit': revision,
                        'timestamp': stages[stage]['timestamp'], 'kind': 'commit_message',
                        'text': raw.decode(), 'sha256': digest(raw)})
    for change in plan.get('diffs', []):
        revision = git(repo, 'rev-parse', change['revision']).decode().strip()
        raw = git(repo, 'show', '--format=', revision, '--', *change['paths'])
        sources.append({'stage': change['stage'], 'path': change['name'], 'commit': revision,
                        'timestamp': git(repo, 'show', '-s', '--format=%cI', revision).decode().strip(),
                        'kind': 'diff', 'paths': change['paths'], 'text': raw.decode(), 'sha256': digest(raw)})
    sources.sort(key=lambda s: (s['stage'], s['path']))
    for i, source in enumerate(sources):
        source['id'] = f's{i + 1:02d}'
        source['title'] = source['path'] + '@' + source['commit'][:9]
    out.mkdir(parents=True, exist_ok=True)
    archive = b''.join((json.dumps(s, ensure_ascii=False) + '\n').encode() for s in sources)
    (out / 'sources.jsonl.gz').write_bytes(gzip.compress(archive, mtime=0))
    save(out / 'checkpoints.json', stages)
    save(out / 'freeze.json', {'schema': 'elf.real_project_freeze/v1',
         'repository': plan['repository'],
         'files': {p.name: digest(p.read_bytes()) for p in sorted(out.iterdir()) if p.is_file()},
         'records': len(sources), 'original_bytes': sum(len(s['text'].encode()) for s in sources),
         'boundary': 'Full selected Git blobs and unedited commit/diff records. Retrospective tasks; no natural-session or live-deployment claim.'})
    return sources


def load(root):
    freeze = json.loads((root / 'freeze.json').read_text())
    for name, expected in freeze['files'].items():
        if digest((root / name).read_bytes()) != expected:
            raise ValueError('Frozen input changed: ' + name)
    sources = [json.loads(line) for line in gzip.decompress((root / 'sources.jsonl.gz').read_bytes()).splitlines()]
    for source in sources:
        if digest(source['text'].encode()) != source['sha256']:
            raise ValueError('Original source hash mismatch')
    return sources, json.loads((root / 'checkpoints.json').read_text())


def spans(text, maximum=6000):
    """Deterministic, contiguous line windows; no task or oracle influences extraction."""
    start = 0
    pending = b''
    for line in text.encode().splitlines(keepends=True):
        if pending and len(pending) + len(line) > maximum:
            yield start, start + len(pending), pending.decode()
            start += len(pending)
            pending = b''
        pending += line
    if pending:
        yield start, start + len(pending), pending.decode()
