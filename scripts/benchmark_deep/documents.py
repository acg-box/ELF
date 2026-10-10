"""Small source-precision workload; exact identifiers make omissions visible."""
from __future__ import annotations

import hashlib


def workload():
    items, oracle, queries = [], {}, []
    def add(name, text):
        key = 'e_' + hashlib.sha256(('documents-v1:' + name).encode()).hexdigest()[:24]
        items.append({'evidence_id': key, 'text': text})
        return key
    def ask(lane, question, facts, evidence=(), forbidden=()):
        key = f'doc-{len(oracle):03d}'
        queries.append({'action':'query','scope':'documents','case_id':key,'lane':lane,'question':question})
        oracle[key] = {'lane':lane,'facts':list(facts),'evidence':list(evidence),
                       'forbidden':list(forbidden),'supported':bool(facts)}
    for i in range(4):
        name = f'Kestrel-{i}'
        policy = add(name + '-policy',
            f'{name} signed return policy. Ordinary goods have a 7-day return window. '
            f'The complete exception list consists of two clauses: custom-made goods use exception CUSTOM-{i}-7c2; '
            f'quality defects use exception DEFECT-{i}-9b4 and are exempt from the 7-day limit. '
            'Both exception identifiers must be retained when listing all exceptions. '
            f'The old informal draft listed only DRAFT-{i}-2d1 and has no authority.')
        table = add(name + '-table',
            f'{name} approved regional routing table. Columns are region, response window, queue.\n'
            f'North | 4 hours | NORTH-{i}-6a8\nSouth | 12 hours | SOUTH-{i}-3e5\n'
            'Rows are independent; do not mix a region with another row.')
        ask('document_exceptions', f'List both exception identifiers in the signed {name} return policy.',
            [f'CUSTOM-{i}-7c2',f'DEFECT-{i}-9b4'], [policy], [f'DRAFT-{i}-2d1'])
        ask('document_table', f'What is the approved queue for the South region of {name}?',
            [f'SOUTH-{i}-3e5'], [table], [f'NORTH-{i}-6a8'])
        ask('document_absent', f'What is the signed replacement product warranty code for {name}?', [])
    return {'schema':'elf.deep_workload/v2', 'actions':[
        {'action':'ingest','scope':'documents','items':items}, *queries]}, oracle
