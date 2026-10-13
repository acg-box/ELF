"""Identical source access with explicit, enforced memory ablations."""
from __future__ import annotations

import json
import re
import urllib.error


def schemas(condition):
    definitions = [
        ('list_sources', 'List immutable Git records available at this checkpoint.', {}, []),
        ('read_source', 'Read exact original lines. Line numbers are one-based. Returns a native citation reference.',
         {'source_id': {'type': 'string'}, 'start_line': {'type': 'integer', 'minimum': 1},
          'line_count': {'type': 'integer', 'minimum': 1, 'maximum': 100}}, ['source_id']),
        ('search_files', 'Search original lines with a case-insensitive regular expression, like grep. Returns up to 20 matches with nearby lines and citation references.',
         {'pattern': {'type': 'string'}}, ['pattern']),
    ]
    if condition != 'no_elf':
        definitions.append(('search_sources', 'Search original documents through native ELF vector and lexical retrieval. Read returned source IDs for context.',
                            {'query': {'type': 'string'}}, ['query']))
    if condition == 'full_elf':
        definitions += [
            ('search_memories', 'Search native extracted memories. These are discovery candidates; inspect their originals before a final claim.', {'query': {'type': 'string'}}, ['query']),
            ('evidence_pack', 'Read selected native memories and their verified original windows. Maximum six note IDs.',
             {'note_ids': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1, 'maxItems': 6}}, ['note_ids']),
            ('recall_evidence', 'Recall missing evidence using up to four literal subjects. Optionally specify historical as_of in RFC3339.',
             {'subjects': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1, 'maxItems': 4}, 'as_of': {'type': 'string'}}, ['subjects']),
            ('query_graph', 'Traverse native entity relationships by surface. Returned evidence note IDs can be read with evidence_pack.',
             {'surface': {'type': 'string'}, 'as_of': {'type': 'string'}}, ['surface']),
        ]
    return [{'type': 'function', 'function': {'name': n, 'description': d, 'parameters': {
        'type': 'object', 'properties': p, 'required': r, 'additionalProperties': False}}} for n, d, p, r in definitions]


class SourceTools:
    def __init__(self, condition, sources, documents, api, protocol):
        self.condition, self.api, self.protocol = condition, api, protocol
        self.sources = {s['id']: s for s in sources}
        self.documents = documents
        self.inverse = {v['doc_id']: k for k, v in documents.items() if k in self.sources}
        self.remaining = protocol['max_evidence_bytes']
        self.references = set()

    def original(self, source_id, start, end):
        source = self.sources[source_id]
        raw = source['text'].encode()
        text = raw[start:end].decode()
        doc = self.documents[source_id]
        return {'source_id': source_id, 'title': source['title'], 'source_timestamp': source['timestamp'],
                'start': start, 'end': end, 'text': text,
                'reference': f"elf-source-v1/{doc['doc_id']}/{doc['content_hash']}/{start}/{end}"}

    def read(self, args):
        source_id = args['source_id']
        lines = self.sources[source_id]['text'].encode().splitlines(keepends=True)
        first = int(args.get('start_line', 1)) - 1
        count = int(args.get('line_count', 60))
        if first < 0 or not 1 <= count <= 100 or first >= len(lines):
            raise ValueError('Invalid line range')
        start = sum(map(len, lines[:first]))
        selected = b''
        for line in lines[first:first + count]:
            if selected and len(selected) + len(line) > 6000:
                break
            selected += line
        return {**self.original(source_id, start, start + len(selected)),
                'start_line': first + 1, 'next_line': first + 1 + len(selected.splitlines()), 'total_lines': len(lines)}

    def grep(self, pattern):
        if not isinstance(pattern, str) or len(pattern) > 200:
            raise ValueError('Pattern must contain at most 200 characters')
        regex = re.compile(pattern, re.IGNORECASE)
        result = []
        for source in self.sources.values():
            lines = source['text'].splitlines(keepends=True)
            offset = 0
            for line_no, line in enumerate(lines, 1):
                if regex.search(line):
                    start = max(0, line_no - 2)
                    before = ''.join(lines[:start]).encode()
                    window = ''.join(lines[start:line_no + 2]).encode()
                    if len(window) <= 2000:
                        result.append({**self.original(source['id'], len(before), len(before) + len(window)), 'match_line': line_no})
                    else:
                        result.append(self.original(source['id'], offset, offset + len(line.encode())))
                    if len(result) >= 20:
                        return {'items': result, 'has_more': True}
                offset += len(line.encode())
        return {'items': result, 'has_more': False}

    def execute(self, name, args):
        allowed = {row['function']['name'] for row in schemas(self.condition)}
        if name not in allowed:
            raise ValueError('Tool is unavailable in this condition')
        if name == 'list_sources':
            return {'items': [{k: v for k, v in source.items() if k in ('id', 'title', 'timestamp', 'stage')}
                             for source in self.sources.values()]}
        if name == 'read_source':
            return self.read(args)
        if name == 'search_files':
            return self.grep(args['pattern'])
        if name == 'search_sources':
            data = self.api('/v2/docs/search/l0', {'query': args['query'], 'top_k': 8, 'candidate_k': 60})
            return {'items': [{'source_id': self.inverse[row['doc_id']], 'snippet': row['snippet'],
                              'title': self.sources[self.inverse[row['doc_id']]]['title'],
                              'source_timestamp': self.sources[self.inverse[row['doc_id']]]['timestamp'],
                              'position': row['pointer']['locator']['position']}
                             for row in data['items'] if row['doc_id'] in self.inverse]}
        if name == 'search_memories':
            data = self.api('/v2/searches', {'mode': 'planned_search', 'query': args['query'], 'top_k': 12, 'candidate_k': 60})
            return {k: data[k] for k in ('search_id', 'items', 'total', 'has_more') if k in data}
        if name == 'evidence_pack':
            return self.project_pack(self.api('/v2/evidence/pack', {'note_ids': args['note_ids'], 'max_source_bytes': 8000}))
        if name == 'recall_evidence':
            data = self.api('/v2/evidence/recall', args)
            return {**data, 'pack': self.project_pack(data['pack'])}
        return self.api('/v2/graph/query', {'subject': {'surface': args['surface']}, 'as_of': args.get('as_of'), 'limit': 12})

    def project_pack(self, pack):
        # Native order is retained. The common output budget may trim the tail.
        value = dict(pack)
        value['sources'] = [{**s, 'source_id': self.inverse.get(s['doc_id'])} for s in pack['sources'] if s['doc_id'] in self.inverse]
        if len(value['sources']) != len(pack['sources']):
            raise ValueError('Future or foreign source crossed the checkpoint')
        return value

    def call(self, name, args):
        if self.remaining <= 100:
            return {'error': 'Common evidence-byte budget exhausted.'}
        try:
            value = self.execute(name, args)
        except urllib.error.HTTPError as error:
            if error.code >= 500 or error.code == 402:
                raise
            value = {'error': {'status': error.code, 'detail': error.read().decode()}}
        except (KeyError, ValueError, re.error) as error:
            value = {'error': str(error)}
        cap = min(self.remaining, self.protocol['max_tool_result_bytes'])
        # Drop complete tail records, never slice serialized JSON or native references.
        lists = []
        def find_lists(node):
            if isinstance(node, dict):
                for v in node.values():
                    find_lists(v)
            elif isinstance(node, list):
                lists.append(node)
        find_lists(value)
        while len(json.dumps(value, ensure_ascii=False).encode()) > cap:
            candidates = [v for v in lists if v]
            if not candidates:
                value = {'error': 'Result does not fit common evidence-byte budget. Read fewer lines.'}
                break
            max(candidates, key=lambda v: len(json.dumps(v))).pop()
            value['truncated'] = True
        def references(node):
            if isinstance(node, dict):
                ref = node.get('reference')
                if isinstance(ref, str) and ref.startswith('elf-source-v1/'):
                    self.references.add(ref)
                for v in node.values():
                    references(v)
            elif isinstance(node, list):
                for v in node:
                    references(v)
        references(value)
        self.remaining -= len(json.dumps(value, ensure_ascii=False).encode())
        return value
