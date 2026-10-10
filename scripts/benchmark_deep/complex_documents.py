"""Raw PDF and fixed free-parser text inputs with the same held-out questions."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'config/benchmark/fixtures/complex-documents-v1'


def workload():
    items, queries, oracle = [], [], {}
    for doc in json.loads((ROOT / 'oracle-source.json').read_text()):
        raw = (ROOT / doc['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != doc['sha256']:
            raise ValueError('Complex document fixture changed: ' + doc['file'])
        items.append({'evidence_id': doc['evidence_id'],
                      'text': (ROOT / (doc['evidence_id'] + '.txt')).read_text(),
                      'file_base64': base64.b64encode(raw).decode(),
                      'file_extension': '.pdf', 'content_type': 'application/pdf'})
        for q in doc['questions']:
            key = f'complex-{len(oracle):03d}'
            queries.append({'action': 'query', 'scope': 'complex-documents',
                            'case_id': key, 'lane': q['lane'], 'question': q['question']})
            oracle[key] = {**{k: q[k] for k in ('lane', 'facts', 'forbidden')},
                           'evidence': [doc['evidence_id']] if q['facts'] else [],
                           'supported': bool(q['facts'])}
    return {'schema': 'elf.deep_workload/v2', 'actions': [
        {'action': 'ingest', 'scope': 'complex-documents', 'items': items}, *queries]}, oracle
