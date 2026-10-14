"""Reuse settled provider fixtures for controlled admission and embedding comparisons."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import urllib.error
import urllib.request


def key_for(body, kind):
    if kind == 'embedding':
        value = {'model': body['model'], 'input': body['input'], 'dimensions': body.get('dimensions')}
    else:
        # Freeze the original proposed notes; the new admission limit is the independent variable.
        prompt = body['messages'][-1]['content']
        if not prompt.startswith('Return an instance matching this JSON Schema:'):
            return None
        value = json.loads(prompt.splitlines()[-1])
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class RecordedProvider:
    def __init__(self, root, directories, upstream, token):
        self.root, self.upstream, self.token = root, upstream, token
        self.records = {}
        self.lock = threading.Lock()
        for directory in directories:
            for path in sorted(Path(directory).glob('*.json'), key=lambda p: int(p.stem)):
                row = json.loads(path.read_text())
                body, response = row['request'], row['response']
                kind = 'embedding' if 'input' in body else 'extraction'
                key = key_for(body, kind)
                if key is None:
                    continue
                if kind == 'embedding':
                    if not response.get('data') or any(len(v['embedding']) != 4096 for v in response['data']):
                        continue
                else:
                    try:
                        assert isinstance(json.loads(response['choices'][0]['message']['content'])['notes'], list)
                    except (ValueError, KeyError, TypeError, AssertionError):
                        continue
                self.records[(kind, key)] = response
        provider = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                kind = 'embedding' if self.path.endswith('/embeddings') else 'extraction'
                key = key_for(body, kind)
                response = provider.records.get((kind, key))
                if response is None and kind == 'extraction':
                    self.send_error(409, 'No frozen extraction for this exact input; do not make a new model call.')
                    return
                reused = response is not None
                if not reused:
                    request = urllib.request.Request(provider.upstream + '/embeddings',
                        data=json.dumps(body).encode(), headers={'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + provider.token})
                    try:
                        with urllib.request.urlopen(request, timeout=3600) as result:
                            response = json.load(result)
                    except urllib.error.HTTPError as error:
                        self.send_response(error.code); self.end_headers(); self.wfile.write(error.read())
                        return
                with provider.lock:
                    with (provider.root / 'provider-reuse.jsonl').open('a') as log:
                        log.write(json.dumps({'kind': kind, 'input_sha256': key, 'reused': reused}) + '\n')
                data = json.dumps(response).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers(); self.wfile.write(data)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}/v1'

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
