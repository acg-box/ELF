"""Check citation exposure and native binding results; do not infer entailment."""
import hashlib
import json

from benchmark_agent.tools import project_note


def audit(case, initial):
    notes = {}
    sources = {}

    def collect(value):
        if isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, dict):
            identity = value.get('note_id')
            if isinstance(identity, str):
                for key in ('text', 'summary', 'quote'):
                    if isinstance(value.get(key), str):
                        notes.setdefault(identity, []).append(value[key])
            metadata, excerpt = value.get('metadata'), value.get('excerpt')
            if isinstance(metadata, dict) and isinstance(excerpt, dict):
                sources.setdefault(metadata['doc_id'], []).append({
                    'hash': metadata['content_hash'], 'text': excerpt['excerpt'],
                    'verified': excerpt['verification']['verified'],
                })
            for item in value.values():
                collect(item)

    collect([project_note(note, 'notes') for note in initial])
    for step in case.get('trace', []):
        for tool in step['tools']:
            if 'error' not in tool['result']:
                collect(tool['result'])
    claims = case.get('claims')
    rows, ids = [], []
    if isinstance(claims, list):
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                rows.append({'claim_index': index, 'valid_shape': False, 'exposed': False})
                continue
            citations = claim.get('citations')
            valid = (isinstance(claim.get('text'), str) and bool(claim['text'].strip())
                     and claim.get('state') in ('supported', 'absent', 'unknown', 'conflict')
                     and isinstance(citations, list))
            checks = []
            for citation in citations if isinstance(citations, list) else []:
                exposed = False
                if isinstance(citation, dict):
                    kind, quote = citation.get('kind'), citation.get('quote')
                    identity = citation.get('note_id' if kind == 'note' else 'doc_id')
                    if isinstance(identity, str):
                        ids.append(identity)
                    if isinstance(quote, str) and quote.strip():
                        if kind == 'note':
                            exposed = any(quote in text for text in notes.get(identity, []))
                        elif kind == 'source':
                            exposed = any(row['verified'] and row['hash'] == citation.get('content_hash')
                                          and quote in row['text'] for row in sources.get(identity, []))
                checks.append(exposed)
            enough = (claim.get('state') == 'unknown' or len(checks) >=
                      (2 if claim.get('state') == 'conflict' else 1))
            rows.append({'claim_index': index, 'valid_shape': valid,
                         'citation_exposure': checks, 'exposed': valid and enough and all(checks)})
    native = case.get('claim_bindings')
    native_pass = (isinstance(native, dict) and native.get('semantic_support') == 'not_evaluated'
                   and len(native.get('claims', [])) == len(rows)
                   and bool(rows) and all(row['binding_verified'] for row in native['claims']))
    top = case.get('citations', [])
    top_matches = len(top) == len(set(top)) and set(top) == set(ids)
    return {'condition': case['condition'], 'case_id': case['query']['case_id'],
            'answer_sha256': hashlib.sha256(case.get('text', '').encode()).hexdigest(),
            'claims_sha256': hashlib.sha256(json.dumps(claims, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            'claim_count': len(rows), 'claims': rows, 'top_level_matches_claims': top_matches,
            'exposure_pass': bool(rows) and all(row['exposed'] for row in rows) and top_matches,
            'native_binding_pass': native_pass,
            'semantic_support': 'requires_separate_review'}
