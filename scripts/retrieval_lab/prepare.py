"""Recover vectors and candidate pools from immutable prior run receipts."""
import gzip
import json
import hashlib
from pathlib import Path
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


def prepare(root, receipts):
    vectors = {}
    for value, receipt_sha in receipt_rows(receipts):
        request, response = value['request'], value['response']
        if 'input' not in request or 'data' not in response:
            continue
        assert request['model'] == 'qwen/qwen3-embedding-8b'
        assert request['dimensions'] == 1536
        inputs = request['input']
        if isinstance(inputs, str):
            inputs = [inputs]
        for row in response['data']:
            vector = row['embedding']
            assert len(vector) == 1536
            text = inputs[row['index']]
            vectors.setdefault(text, {'vector': vector, 'receipt_sha256': receipt_sha})
    suite = read(EVIDENCE / 'frozen-workloads.json')
    notes = read(EVIDENCE / 'extraction-diagnostics.json')['notes']
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
    for row in corpus + queries:
        text = row.get('text', row.get('question'))
        if text not in vectors:
            missing.append({'identity': row.get('case_id', row.get('evidence_id')), 'text_sha256': digest(text)})
        else:
            row.update(vectors[text])
            row['embedding_input_sha256'] = digest(text)
    save(root / 'embedding-reuse.json', {'model': 'qwen/qwen3-embedding-8b', 'dimensions': 1536, 'unique_saved_inputs': len(vectors), 'corpus_count': len(corpus), 'query_count': len(queries), 'missing': missing, 'new_embedding_calls': 0})
    if missing:
        raise ValueError(f'{len(missing)} exact embedding inputs absent; do not approximate or silently re-embed')
    save(root / 'dataset.json', {'corpus': corpus, 'queries': queries})
    save(root / 'frozen-workloads.json', suite)
    selected = [x for x in cases() if x['condition'] == 'elf-memory-retrieval-reader']
    inverse = {x['doc_id']: x['evidence_id'] for x in read(EVIDENCE / 'source-integrity.json')['records']}
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
    print({'prepared': len(corpus), 'queries': len(queries), 'pools': len(pools), 'new_embedding_calls': 0}, flush=True)
