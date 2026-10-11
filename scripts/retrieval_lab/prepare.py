"""Recover vectors and candidate pools from immutable prior run receipts."""
import gzip
import json
import hashlib
import os
import urllib.request
from pathlib import Path
from itertools import chain
from .common import EVIDENCE, cases, digest, read, save


def receipt_rows(path):
    path=Path(path)
    if path.is_file():
        for line in gzip.decompress(path.read_bytes()).splitlines():
            row=json.loads(line)
            value={'request':row['request'],'response':row['response']}
            original=(json.dumps(value,indent=2)+'\n').encode()
            yield value,hashlib.sha256(original).hexdigest()
    else:
        for item in sorted(path.glob('*.json')):
            yield read(item),hashlib.sha256(item.read_bytes()).hexdigest()


def prepare(root, receipts, native_run=None, fill_missing=False):
    evidence = Path(native_run) if native_run else EVIDENCE
    dimension = read(evidence / "protocol.json")["dimensions"] if native_run else 1536
    if native_run and dimension != 4096:
        raise ValueError("New native runs require full 4096-dimensional Qwen embeddings")
    vectors = {}
    for value, receipt_sha in chain(receipt_rows(receipts), receipt_rows(root / "filled-embeddings")):
        request, response = value['request'], value['response']
        if 'input' not in request or 'data' not in response:
            continue
        assert request['model'] == 'qwen/qwen3-embedding-8b'
        assert request['dimensions'] == dimension
        inputs = request['input']
        if isinstance(inputs, str):
            inputs = [inputs]
        for row in response['data']:
            vector = row['embedding']
            assert len(vector) == dimension
            text = inputs[row['index']]
            vectors.setdefault(text, {'vector': vector, 'receipt_sha256': receipt_sha})
    suite = read(evidence / 'frozen-workloads.json')
    notes = read(evidence / 'extraction-diagnostics.json')['notes']
    corpus = []
    missing = []
    for scope, workload in suite.items():
        for item in workload['items']:
            corpus.append({'id': len(corpus), 'evidence_id': item['evidence_id'], 'kind': 'source', 'scope': scope, 'text': item['text']})
    for note in notes:
        if note['status'] != 'active':
            continue
        corpus.append({'id': len(corpus), 'evidence_id': 'elf-note:' + note['note_id'], 'kind': 'memory', 'scope': 'memory', 'text': note['text']})
    queries = [{**q, 'scope': scope, 'expected': workload['oracle'][q['case_id']]} for scope, workload in suite.items() for q in workload['queries']]
    generated = 0
    if fill_missing:
        needed = sorted({row.get('text', row.get('question')) for row in corpus + queries} - vectors.keys())
        for offset in range(0, len(needed), 16):
            inputs = needed[offset:offset + 16]
            request = {'model':'qwen/qwen3-embedding-8b','dimensions':dimension,'input':inputs}
            base = os.environ['LITELLM_BASE_URL'].replace('127.0.0.1','host.docker.internal')
            req = urllib.request.Request(base.rstrip('/') + '/embeddings', data=json.dumps(request).encode(), headers={'Authorization':'Bearer ' + os.environ['LITELLM_API_KEY'],'Content-Type':'application/json'})
            with urllib.request.urlopen(req, timeout=3600) as response:
                value = json.load(response)
            receipt = {'request':request,'response':value}
            receipt_path = root / 'filled-embeddings' / (digest(json.dumps(inputs)) + '.json')
            save(receipt_path, receipt)
            receipt_sha = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
            if sorted(row['index'] for row in value['data']) != list(range(len(inputs))):
                raise ValueError('Incomplete embedding response')
            for row in value['data']:
                if len(row['embedding']) != dimension:
                    raise ValueError('Embedding dimension mismatch')
                vectors[inputs[row['index']]] = {'vector':row['embedding'],'receipt_sha256':receipt_sha}
            generated += 1
    for row in corpus + queries:
        text = row.get('text', row.get('question'))
        if text not in vectors:
            missing.append({'identity': row.get('case_id', row.get('evidence_id')), 'text_sha256': digest(text)})
        else:
            row.update(vectors[text])
            row['embedding_input_sha256'] = digest(text)
    save(root / 'embedding-reuse.json', {'model': 'qwen/qwen3-embedding-8b', 'dimensions': dimension, 'unique_saved_inputs': len(vectors), 'corpus_count': len(corpus), 'query_count': len(queries), 'missing': missing, 'new_embedding_calls': generated})
    if missing:
        raise ValueError(f'{len(missing)} exact embedding inputs absent; do not approximate or silently re-embed')
    save(root / 'dataset.json', {'corpus': corpus, 'queries': queries})
    save(root / 'frozen-workloads.json', suite)
    save(root / 'input-protocol.json', read(evidence / 'protocol.json') if native_run else {'source_commit':'6cf7bc03a23579cb9415541b04906f2e87485c79','dimensions':1536})
    native_cases = [read(p) for p in (evidence / 'cases').rglob('*.json')] if native_run else cases()
    selected = [x for x in native_cases if x['condition'] == 'elf-memory-retrieval-reader']
    inverse = {x['doc_id']: x['evidence_id'] for x in read(evidence / 'source-integrity.json')['records']}
    pools = []
    for case in selected:
        rows = []
        for item in case['native']['hydrated']:
            if 'note_id' in item:
                rows.append({'kind': 'memory', 'evidence_id': 'elf-note:' + item['note_id'], 'text': item['text']})
            else:
                rows.append({'kind': 'source', 'evidence_id': inverse[item['doc_id']], 'text': item['excerpt']})
        pools.append({'case_id': case['case_id'], 'rows': rows, 'prior_context': case['context']})
    save(root / 'ablation-pools.json', pools)
    print({'prepared': len(corpus), 'queries': len(queries), 'pools': len(pools), 'new_embedding_calls': generated}, flush=True)
