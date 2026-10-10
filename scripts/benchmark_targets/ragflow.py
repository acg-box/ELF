"""RAGFlow 1.0 native document ingestion, retrieval, and source lifecycle."""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


def request(method, path, value=None, *, data=None, content_type='application/json'):
    if value is not None:
        data = json.dumps(value).encode()
    req = urllib.request.Request(os.environ['RAGFLOW_URL'] + '/api/v1' + path,
        data=data, method=method, headers={'Authorization': 'Bearer ' + os.environ['RAGFLOW_API_KEY'],
                                         'Content-Type': content_type})
    with urllib.request.urlopen(req, timeout=180) as response:
        result = json.load(response)
    if result.get('code', 0) != 0:
        raise RuntimeError(f"RAGFlow API {method} {path}: {result.get('code')}: {result.get('message')}")
    return result.get('data')


def upload(dataset, item):
    boundary = 'elf-' + uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            f'filename="{item["evidence_id"]}.txt"\r\nContent-Type: text/plain\r\n\r\n'
            + item['text'] + f'\r\n--{boundary}--\r\n').encode()
    docs = request('POST', f'/datasets/{dataset}/documents', data=body,
                   content_type='multipart/form-data; boundary=' + boundary)
    return docs[0]['id']


def wait_parsed(dataset, ids):
    deadline = time.monotonic() + float(os.environ.get('BENCHMARK_DEEP_INGEST_TIMEOUT_SECONDS', '1200'))
    while True:
        data = request('GET', f'/datasets/{dataset}/documents?page_size=1000')
        docs = [d for d in data['docs'] if d['id'] in ids]
        if any(str(d.get('ingestion_status', d.get('run'))).upper() in ('FAIL', 'FAILED', 'CANCELED', '4') for d in docs):
            raise RuntimeError('RAGFlow native parsing failed: ' + json.dumps(docs))
        if len(docs) == len(ids) and all(str(d.get('ingestion_status', d.get('run'))).upper() in ('DONE', 'SUCCEEDED', 'SUCCESS', '3') for d in docs):
            return docs
        if time.monotonic() >= deadline:
            raise TimeoutError('RAGFlow document parsing did not finish')
        time.sleep(2)


def contexts_from_chunks(chunks, mapping):
    inverse = {native_id: evidence_id for evidence_id, native_id in mapping.items()}
    return [{'evidence_id': inverse.get(chunk.get('document_id')),
             'text': chunk.get('content', ''), 'native_document_id': chunk.get('document_id'),
             'native_chunk_id': chunk.get('id')} for chunk in chunks]


def run_action(action, root: Path):
    path = root / ('ragflow-' + action['scope'] + '.json')
    kind = action['action']
    if kind == 'ingest':
        dataset = request('POST', '/datasets', {
            'name': 'elf-' + action['scope'] + '-' + uuid.uuid4().hex[:10],
            'embedding_model': os.environ['RAGFLOW_EMBEDDING_MODEL'],
            'parser_id': 'general', 'permission': 'me'})
        state = {'dataset_id': dataset['id'], 'documents': {}}
        path.write_text(json.dumps(state))
        for item in action['items']:
            state['documents'][item['evidence_id']] = upload(dataset['id'], item)
            path.write_text(json.dumps(state))
        ids = list(state['documents'].values())
        parsed = request('POST', f'/datasets/{dataset["id"]}/chunks', {'document_ids': ids})
        return {'native': {'dataset': dataset, 'parse': parsed,
                          'documents': wait_parsed(dataset['id'], ids)}}
    state = json.loads(path.read_text())
    dataset = state['dataset_id']
    if kind == 'query':
        result = request('POST', '/retrieval', {'question': action['question'],
            'dataset_ids': [dataset], 'page': 1, 'page_size': 5,
            'similarity_threshold': 0.2, 'vector_similarity_weight': 0.3,
            'top_k': 1024, 'keyword': False})
        return {'contexts': contexts_from_chunks(result['chunks'], state['documents']),
                'native': result,
                'boundary': 'Dataset-scoped hybrid retrieval. No ACL revocation or native synthesis claim.'}
    old_id = state['documents'][action['evidence_id']]
    deleted = request('DELETE', f'/datasets/{dataset}/documents', {'ids': [old_id]})
    readback = request('GET', f'/datasets/{dataset}/documents?id={old_id}')
    if readback['docs']:
        raise RuntimeError('Deleted RAGFlow document is still listed')
    del state['documents'][action['evidence_id']]
    native = {'deleted_id': old_id, 'delete': deleted, 'deleted_document_readback': readback}
    if kind == 'update':
        new_id = upload(dataset, action)
        state['documents'][action['evidence_id']] = new_id
        request('POST', f'/datasets/{dataset}/chunks', {'document_ids': [new_id]})
        native.update(replacement_id=new_id, documents=wait_parsed(dataset, [new_id]),
                      boundary='Native document delete and upload; not an atomic in-place source update.')
    path.write_text(json.dumps(state))
    return {'native': native}
