"""Docker lifecycle for the matched ELF API benchmark; secrets stay in private files."""
import json
import hashlib
import os
from pathlib import Path
import re
import secrets
import subprocess
import time
import urllib.request

PREFIX = 'elf-matched'
IMAGE = None  # Selected explicitly by the matched runner.
LABEL = 'elf.benchmark=elf-matched'


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True).strip()


def owned(name):
    p = subprocess.run(['docker', 'inspect', name], capture_output=True, text=True)
    if p.returncode:
        return False
    if json.loads(p.stdout)[0]['Config']['Labels'].get('elf.benchmark') != 'elf-matched':
        raise ValueError('Resource ownership mismatch: ' + name)
    return True



def prepare_tokenizer(root):
    receipt = {'url':'https://huggingface.co/openai-community/gpt2/resolve/607a30d783dfa663caf39e06633721c8d4cfcd7e/tokenizer.json',
               'sha256':'8414cab924d8b9b33013f0d221c5862f365ee9be39c5c2bfae8a5a9e970478a6'}
    target = root / 'tokenizer.json'
    if not target.exists():
        with urllib.request.urlopen(receipt['url'],timeout=60) as response:
            target.write_bytes(response.read())
    if hashlib.sha256(target.read_bytes()).hexdigest() != receipt['sha256']:
        raise ValueError('Pinned tokenizer digest mismatch')
    (root / 'tokenizer-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


def start(root, repo, common):
    auth_path = root / 'private-auth.json'
    if auth_path.exists():
        auth = json.loads(auth_path.read_text())
    else:
        auth = {scope: secrets.token_hex(24) for scope in ('documents', 'memory')}
        auth_path.write_text(json.dumps(auth)); auth_path.chmod(0o600)
    if subprocess.run(['docker', 'network', 'inspect', PREFIX], capture_output=True).returncode:
        docker('network', 'create', '--label', LABEL, PREFIX)
    network = json.loads(docker('network','inspect',PREFIX))[0]
    if network['Labels'].get('elf.benchmark') != 'elf-matched':
        raise ValueError('Network ownership mismatch')
    def run(name, image, args=(), command=()):
        if not owned(name):
            docker('run', '-d', '--name', name, '--label', LABEL, '--network', PREFIX,
                   *args, image, *command)
    run(PREFIX + '-db', 'pgvector/pgvector:pg18',
        ('-e', 'POSTGRES_PASSWORD=benchmark-local', '-e', 'POSTGRES_DB=elf'))
    run(PREFIX + '-qdrant', 'qdrant/qdrant:v1.18.0')
    run(PREFIX + '-sidecar', common.HS_IMAGE,
        ('-p', '127.0.0.1:19889:8899', '-v', str(root) + ':/experiment',
         '-v', str(repo / 'scripts/benchmark_deep/native_sidecar.py') + ':/native-sidecar.py:ro',
         '-e', 'HINDSIGHT_API_RERANKER_LOCAL_FORCE_CPU=true', '--entrypoint', 'python'),
        ('/native-sidecar.py',))
    config = (repo / 'elf.example.toml').read_text()
    config = config.replace('127.0.0.1:51892', '0.0.0.0:51892')
    config = config.replace('postgres://postgres:postgres@127.0.0.1:5432/elf',
                            'postgres://postgres:benchmark-local@elf-matched-db:5432/elf')
    config = config.replace('http://127.0.0.1:6334', 'http://elf-matched-qdrant:6334')
    config = config.replace('4_096', '1536').replace('tokenizer_repo = "REPLACE_ME"',
                                                  'tokenizer_repo = "/experiment/tokenizer.json"')
    config = config.replace('auth_keys                = []', '')
    config = config.replace('auth_mode                = "off"', 'auth_mode                = "static_keys"')
    config = config.replace('bind_localhost_only      = true', 'bind_localhost_only      = false')
    base = os.environ['LITELLM_BASE_URL'].replace('127.0.0.1', 'host.docker.internal')
    for name, model, endpoint in (('embedding', common.EMB, '/embeddings'),
            ('llm_extractor', common.CHAT, '/chat/completions'),
            ('rerank', 'cross-encoder/ms-marco-MiniLM-L-6-v2', '/rerank')):
        values = {'api_base': 'http://elf-matched-sidecar:8899/v1' if name == 'rerank' else base,
                  'api_key': 'local-only' if name == 'rerank' else os.environ['LITELLM_API_KEY'],
                  'model': model, 'provider_id': 'openai', 'path': endpoint, 'timeout_ms': 3600000}
        if name == 'embedding': values['dimensions'] = 1536
        if name == 'llm_extractor': values['temperature'] = 0.1
        section = f'[providers.{name}]\ndefault_headers = {{}}\n' + ''.join(
            k + ' = ' + json.dumps(v) + '\n' for k, v in values.items()) + '\n'
        config = re.sub(r'\[providers\.' + name + r'\][\s\S]*?(?=\n\[)', section, config, count=1)
    for scope, token in auth.items():
        config += '\n[[security.auth_keys]]\n' + ''.join(k+' = '+json.dumps(v)+'\n' for k,v in {
            'token_id':scope,'token':token,'tenant_id':'matched','project_id':scope,
            'agent_id':'benchmark','read_profile':'private_only','role':'user'}.items())
    path = root / 'private-elf.toml'; path.write_text(config); path.chmod(0o600)
    for _ in range(60):
        if subprocess.run(['docker','exec',PREFIX+'-db','pg_isready','-U','postgres'],capture_output=True).returncode == 0:
            break
        time.sleep(1)
    for role in ('api', 'worker'):
        name = PREFIX + '-' + role
        if owned(name):
            docker('stop',name); docker('rm',name)
        run(name, IMAGE, ('--add-host','host.docker.internal:host-gateway',
            '-v',str(root)+':/experiment', *(['-p','127.0.0.1:19892:51892'] if role=='api' else [])),
            ('elf-'+role,'--config','/experiment/private-elf.toml'))
    for _ in range(300):
        try:
            urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:19892/health',
                headers={'Authorization':'Bearer '+auth['documents']}),timeout=2).close()
            common.api(common.SIDE,'/tokens',{'text':'ready'})
            return auth
        except Exception:
            time.sleep(2)
    raise TimeoutError('ELF or reranker readiness failed; inspect owned container logs')


def drain():
    sql = "SELECT (SELECT count(*) FROM indexing_outbox WHERE status <> 'DONE') + (SELECT count(*) FROM doc_indexing_outbox WHERE status <> 'DONE') + (SELECT count(*) FROM search_trace_outbox WHERE status <> 'DONE');"
    for _ in range(600):
        if int(docker('exec',PREFIX+'-db','psql','-U','postgres','-d','elf','-At','-c',sql)) == 0:
            return
        time.sleep(2)
    raise TimeoutError('Native indexing did not drain')
