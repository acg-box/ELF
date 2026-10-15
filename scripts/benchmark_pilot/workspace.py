"""Disposable Docker execution for the finite project-maintenance trial."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

from .corpus import save


def frozen_files(root):
    manifest = json.loads((root / 'freeze.json').read_text())
    for name, expected in manifest['files'].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen workflow input changed: ' + name)
    return manifest


class Workspace:
    def __init__(self, root, image, name):
        if not re.fullmatch(r'elf-workflow-[a-z0-9-]+', name):
            raise ValueError('Invalid workflow container owner')
        self.root, self.image, self.name = root, image, name
        self.checkout = root / 'checkout'
        self.calls = 0

    def start(self, repository, revision):
        if not self.checkout.exists():
            subprocess.run(['git', 'clone', '--quiet', '--single-branch', '--branch', 'main',
                            '--no-local', repository, str(self.checkout)], check=True)
            subprocess.run(['git', '-C', str(self.checkout), 'checkout', '--quiet', '--detach', revision], check=True)
            subprocess.run(['git', '-C', str(self.checkout), 'remote', 'remove', 'origin'], check=True)
        subprocess.run(['docker', 'run', '-d', '--name', self.name,
            '--label', 'elf.benchmark=' + self.name, '--network', 'none', '--read-only',
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--pids-limit', '128',
            '--memory', '1g', '--cpus', '1', '--tmpfs', '/tmp:rw,size=128m',
            '--mount', 'type=bind,src=' + str(self.checkout) + ',dst=/work',
            '--workdir', '/work', '--entrypoint', 'sleep', self.image, 'infinity'],
            check=True, stdout=subprocess.DEVNULL)

    def shell(self, command, directory, cap):
        self.calls += 1
        path = directory / f'shell-{self.calls:03}.log'
        path.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        with path.open('wb') as output:
            try:
                process = subprocess.run(['docker', 'exec', self.name, 'sh', '-lc', command],
                    stdout=output, stderr=subprocess.STDOUT, timeout=90)
                code = process.returncode
            except subprocess.TimeoutExpired:
                # End the isolated workload rather than leave a command running in it.
                subprocess.run(['docker', 'stop', '--time', '1', self.name],
                               check=True, stdout=subprocess.DEVNULL)
                raise RuntimeError('Workspace command timed out; preserve the cell and stop')
        with path.open('rb') as output:
            raw = output.read(max(0, cap))
        return {'exit_code': code, 'output': raw.decode('utf-8', errors='replace'),
                'truncated': path.stat().st_size > len(raw), 'seconds': time.monotonic() - started}

    def snapshot(self, directory):
        subprocess.run(['git', '-C', str(self.checkout), 'add', '-A'], check=True)
        patch = subprocess.check_output(['git', '-C', str(self.checkout), 'diff', '--cached', '--binary', 'HEAD'])
        (directory / 'work.patch').write_bytes(patch)
        files = subprocess.check_output(['git', '-C', str(self.checkout), 'diff', '--cached',
                                         '--name-only', 'HEAD'], text=True).splitlines()
        save(directory / 'work.json', {'patch_sha256': hashlib.sha256(patch).hexdigest(),
                                      'changed_files': files})
        return files

    def close(self):
        inspected = subprocess.run(['docker', 'inspect', self.name], capture_output=True, text=True)
        if inspected.returncode:
            return
        item = json.loads(inspected.stdout)[0]
        if item['Config']['Labels'].get('elf.benchmark') != self.name:
            raise RuntimeError('Workspace owner changed')
        if item['State']['Running']:
            subprocess.run(['docker', 'stop', '--time', '1', self.name], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['docker', 'rm', self.name], check=True, stdout=subprocess.DEVNULL)
