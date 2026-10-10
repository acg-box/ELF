#!/usr/bin/env python3
"""Provision an isolated RAGFlow API user and run the Docker deep benchmark.

Run inside benchmark-budget. The native Docker server must already be ready.
Only the budget gateway token is passed to RAGFlow; never the provider secret.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import subprocess
import urllib.request

from benchmark_runner.providers import container_url
from benchmark_runner.runtime import REPO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact-root', required=True, type=Path)
    parser.add_argument('--manifest', type=Path, default=Path('config/benchmark/ragflow-v1.json'))
    parser.add_argument('--public-key', required=True, type=Path,
                        help='conf/public.pem from the pinned native server image')
    parser.add_argument('--url', default='http://127.0.0.1:19380')
    parser.add_argument('--workload-group', choices=('behavior','mutations','documents','complex-documents','scale-100'), default='behavior')
    parser.add_argument("--ingest-seconds", type=int, default=600)
    parser.add_argument("--source-labels", action="store_true")
    args = parser.parse_args()
    auth = None
    def api(method, path, value=None):
        req = urllib.request.Request(args.url + '/api/v1' + path, method=method,
            data=None if value is None else json.dumps(value).encode(),
            headers={'Content-Type':'application/json', **({'Authorization':auth} if auth else {})})
        with urllib.request.urlopen(req, timeout=180) as response:
            row = json.load(response)
            if row.get('code', 0) != 0:
                # Provider configuration errors can echo the submitted gateway token.
                msg = str(row.get('message', 'RAGFlow API failure'))
                raise RuntimeError(msg.replace(os.environ['EMBEDDING_API_KEY'], '[redacted]'))
            return row.get('data'), response.headers.get('Authorization')
    password = secrets.token_hex(20)
    encrypted = subprocess.check_output(['openssl','pkeyutl','-encrypt','-pubin',
        '-inkey',str(args.public_key),'-pkeyopt','rsa_padding_mode:pkcs1'],
        input=base64.b64encode(password.encode()))
    _, auth = api('POST','/users',{'nickname':'ELF Benchmark',
        'email':'elf-' + secrets.token_hex(8) + '@example.test',
        'password':base64.b64encode(encrypted).decode()})
    if not auth:
        raise RuntimeError('RAGFlow registration did not return a session token')
    token, _ = api('POST','/system/tokens',{})
    api('PUT','/providers',{'provider_name':'OpenAI-API-Compatible'})
    api('POST','/providers/OpenAI-API-Compatible/instances',{
        'instance_name':'elf_benchmark', 'api_key':os.environ['EMBEDDING_API_KEY'],
        'base_url':container_url(os.environ['EMBEDDING_API_BASE']),
        'model_info':[{'model_name':'qwen/qwen3-embedding-8b', 'model_type':['embedding'],
                       'max_tokens':8192,'extra':{'max_dimension':1536,'dimensions':[1536]}}]})
    env = {**os.environ, 'RAGFLOW_API_KEY':token['token'],
           'RAGFLOW_EMBEDDING_MODEL':'qwen/qwen3-embedding-8b@elf_benchmark@OpenAI-API-Compatible'}
    result = subprocess.run(['cargo','make','benchmark-deep','--target','ragflow',
        '--manifest',str(args.manifest),'--artifact-root',str(args.artifact_root),
        '--workload-group',args.workload_group,'--max-seconds','2400','--ingest-seconds',str(args.ingest_seconds), *(['--source-labels'] if args.source_labels else [])],cwd=REPO,env=env)
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
