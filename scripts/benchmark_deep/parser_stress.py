"""Frozen parser stress workload and value-aware diagnostic scoring."""
import base64
import hashlib
import html
import json
import re
import unicodedata


def normalized(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    text = re.sub(r'(?<=\d),(?=\d{3}(?:\D|$))', '', text)
    return re.sub(r'\s+', '', text)


def contains(text, fact):
    text, fact = normalized(text), normalized(fact)
    if fact.isdigit():
        return re.search(r'(?<!\d)' + re.escape(fact) + r'(?!\d)', text) is not None
    return fact in text


def score(expected, text):
    # Remove citation indices before checking small numeric answers.
    clean = re.sub(r'\[.*?\]|##\d+\$\$', '', text).strip()
    if not expected['supported']:
        return bool(re.fullmatch(r'unknown[.!]?', clean, re.I))
    return (all(contains(clean, f) for f in expected['facts'])
            and not any(contains(clean, f) for f in expected['forbidden']))


def span_present(text, fact):
    """Match retained source values without joining adjacent numeric table cells."""
    text = html.unescape(re.sub(r'<[^>]*>', ' ', text))
    text = unicodedata.normalize('NFKC', text)
    if fact.isdigit():
        text = re.sub(r'(?<=\d),(?=\d{3}(?:\D|$))', '', text)
        return re.search(r'(?<!\d)' + re.escape(fact) + r'(?!\d)', text) is not None
    return contains(text, fact)


def workload(fixture_root, free_root):
    items, queries, oracle = [], [], {}
    for doc in json.loads((fixture_root / 'oracle-source.json').read_text()):
        raw = (fixture_root / doc['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != doc['sha256']:
            raise ValueError('Parser fixture changed: ' + doc['file'])
        parsed = json.loads((free_root / (doc['evidence_id'] + '.json')).read_text())
        if parsed['source_sha256'] != doc['sha256'] or len(parsed['pages']) != doc['pages']:
            raise ValueError('Free extraction does not match the frozen PDF')
        items.append({'evidence_id': doc['evidence_id'], 'text': parsed['text'],
                      'file_base64': base64.b64encode(raw).decode(),
                      'file_extension': '.pdf', 'content_type': 'application/pdf'})
        for question in doc['questions']:
            key = f'stress-{len(oracle):03d}'
            queries.append({'action': 'query', 'scope': 'parser-stress', 'case_id': key,
                            'lane': question['lane'], 'question': question['question']})
            oracle[key] = {**{k: question[k] for k in ('lane', 'facts', 'forbidden')},
                           'supported': bool(question['facts']),
                           'evidence': [doc['evidence_id']] if question['facts'] else []}
    return {'actions': [{'action': 'ingest', 'items': items}, *queries]}, oracle
