"""Run the shipped ELF API and worker against task-owned Docker stores."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import time
import tomllib
import urllib.request
import urllib.error

from .corpus import save

OWNER = 'elf-project-pilot'


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True).strip()


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class Runtime:
    def __init__(self, root, repo):
        self.root, self.repo = root, repo
        self.processes = []
        self.logs = []
        path = root / 'runtime.json'
        if path.exists():
            self.state = json.loads(path.read_text())
        else:
            self.state = {'owner': OWNER, 'pg_port': port(), 'qdrant_port': port(),
                          'http_port': port(), 'admin_port': port(), 'mcp_port': port()}
            save(path, self.state)
        self.owner = self.state['owner']
        if not re.fullmatch(r'elf-[a-z0-9-]+', self.owner):
            raise ValueError('Invalid runtime owner')
        auth = root / 'private-auth.json'
        if not auth.exists():
            save(auth, {'token': secrets.token_hex(24)})
            auth.chmod(0o600)
        self.token = json.loads(auth.read_text())['token']
        self.base = 'http://127.0.0.1:' + str(self.state['http_port'])

    def api(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(self.base + path, data=data,
            headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=3600) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            error.add_note(error.read().decode())
            raise

    def sql(self, query):
        return docker('exec', self.owner + '-db', 'psql', '-U', 'postgres', '-d', 'elf', '-At', '-c', query)

    def stores(self):
        for suffix, image, ports, env in [
            ('db', 'pgvector/pgvector:pg18', [f"127.0.0.1:{self.state['pg_port']}:5432"],
             ['POSTGRES_PASSWORD=pilot-local', 'POSTGRES_DB=elf']),
            ('qdrant', 'qdrant/qdrant:v1.18.0', [f"127.0.0.1:{self.state['qdrant_port']}:6334"], [])]:
            name = self.owner + '-' + suffix
            existing = subprocess.run(['docker', 'inspect', name], capture_output=True, text=True)
            if existing.returncode == 0:
                row = json.loads(existing.stdout)[0]
                if row['Config']['Labels'].get('elf.benchmark') != self.owner:
                    raise ValueError('Container owner mismatch')
                if not row['State']['Running']:
                    docker('start', name)
                continue
            volume = name + '-data'
            check = subprocess.run(['docker', 'volume', 'inspect', volume], capture_output=True, text=True)
            if check.returncode == 0:
                if json.loads(check.stdout)[0]['Labels'].get('elf.benchmark') != self.owner:
                    raise ValueError('Volume owner mismatch')
            else:
                docker('volume', 'create', '--label', 'elf.benchmark=' + self.owner, volume)
            args = ['run', '-d', '--name', name, '--label', 'elf.benchmark=' + self.owner]
            for value in ports:
                args += ['-p', value]
            for value in env:
                args += ['-e', value]
            target = '/var/lib/postgresql' if suffix == 'db' else '/qdrant/storage'
            docker(*args, '-v', volume + ':' + target, image)
        for _ in range(60):
            check = subprocess.run(['docker', 'exec', self.owner + '-db', 'pg_isready', '-h', '127.0.0.1', '-U', 'postgres'], capture_output=True)
            if check.returncode == 0:
                return
            time.sleep(1)
        raise TimeoutError('Pilot PostgreSQL readiness failed')

    def start(self):
        self.stores()
        protocol = json.loads((self.root / 'fixture' / 'protocol.json').read_text())
        tokenizer = self.root / 'tokenizer.json'
        if not tokenizer.exists():
            raise ValueError('Supply the verified GPT-2 tokenizer.json in the run directory')
        if hashlib.sha256(tokenizer.read_bytes()).hexdigest() != '8414cab924d8b9b33013f0d221c5862f365ee9be39c5c2bfae8a5a9e970478a6':
            raise ValueError('Tokenizer hash mismatch')
        config = (self.repo / 'elf.example.toml').read_text()
        for key, number in [('http', self.state['http_port']), ('admin', self.state['admin_port']), ('mcp', self.state['mcp_port'])]:
            config = re.sub(key + r'_bind\s*=\s*"[^"]+"', key + '_bind = "127.0.0.1:' + str(number) + '"', config)
        config = config.replace('postgres://postgres:postgres@127.0.0.1:5432/elf',
                                f"postgres://postgres:pilot-local@127.0.0.1:{self.state['pg_port']}/elf")
        config = config.replace('http://127.0.0.1:6334', f"http://127.0.0.1:{self.state['qdrant_port']}")
        config = config.replace('tokenizer_repo = "REPLACE_ME"', 'tokenizer_repo = ' + json.dumps(str(tokenizer)))
        for name, model, endpoint in [('embedding', 'qwen/qwen3-embedding-8b', '/embeddings'),
                                      ('llm_extractor', protocol['model'], '/chat/completions'),
                                      ('rerank', 'local-token-overlap', '/rerank')]:
            values = {'api_base': os.environ['LITELLM_BASE_URL'], 'api_key': os.environ['LITELLM_API_KEY'],
                      'model': model, 'provider_id': 'local' if name == 'rerank' else 'openai',
                      'path': endpoint, 'timeout_ms': 3600000}
            if name == 'embedding':
                values['dimensions'] = 4096
            if name == 'llm_extractor':
                values['temperature'] = 0.1
            section = f'[providers.{name}]\ndefault_headers = {{}}\n' + ''.join(k + ' = ' + json.dumps(v) + '\n' for k, v in values.items()) + '\n'
            config = re.sub(r'\[providers\.' + name + r'\][\s\S]*?(?=\n\[)', lambda _: section, config, count=1)
        config = config.replace('auth_mode                = "off"', 'auth_mode                = "static_keys"')
        config = config.replace('auth_keys                = []', '')
        config += '\n[[security.auth_keys]]\n' + ''.join(k + ' = ' + json.dumps(v) + '\n' for k, v in {
            'token_id': self.owner, 'token': self.token, 'tenant_id': self.owner, 'project_id': 'project',
            'agent_id': 'pilot', 'read_profile': 'private_only', 'role': 'user'}.items())
        tomllib.loads(config)
        path = self.root / 'private-elf.toml'
        path.write_text(config)
        path.chmod(0o600)
        for role in ['api', 'worker']:
            log = (self.root / (role + '.log')).open('ab')
            self.logs.append(log)
            self.processes.append(subprocess.Popen([str(self.repo / 'target/debug' / ('elf-' + role)),
                '--config', str(path)], cwd=self.repo, stdout=log, stderr=subprocess.STDOUT))
        for _ in range(90):
            if any(p.poll() is not None for p in self.processes):
                raise RuntimeError('Pilot API or worker exited; inspect private run logs')
            try:
                request = urllib.request.Request(self.base + '/health',
                    headers={'Authorization': 'Bearer ' + self.token})
                with urllib.request.urlopen(request, timeout=2):
                    pass
                save(self.root / 'runtime-build.json', {'source_commit': subprocess.check_output(
                    ['git', 'rev-parse', 'HEAD'], cwd=self.repo, text=True).strip(),
                    'binaries': {r: hashlib.sha256((self.repo / 'target/debug' / ('elf-' + r)).read_bytes()).hexdigest() for r in ['api', 'worker']},
                    'tokenizer_sha256': hashlib.sha256(tokenizer.read_bytes()).hexdigest(),
                    'database_image': json.loads(docker('inspect', self.owner + '-db'))[0]['Image'],
                    'qdrant_image': json.loads(docker('inspect', self.owner + '-qdrant'))[0]['Image']})
                return
            except (OSError, ValueError):
                time.sleep(1)
        raise TimeoutError('Pilot API readiness failed')

    def drain(self):
        query = "SELECT (SELECT count(*) FROM indexing_outbox WHERE status <> 'DONE') + (SELECT count(*) FROM doc_indexing_outbox WHERE status <> 'DONE') + (SELECT count(*) FROM search_trace_outbox WHERE status <> 'DONE');"
        for _ in range(180):
            if int(self.sql(query)) == 0:
                return
            time.sleep(1)
        raise TimeoutError('Native indexing did not reach DONE')

    def close(self):
        for process in reversed(self.processes):
            process.terminate()
        for process in self.processes:
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for log in self.logs:
            log.close()
