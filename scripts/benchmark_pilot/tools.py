"""Identical source access with explicit, enforced memory ablations."""
from __future__ import annotations

import json
import re
import urllib.error


def schemas(condition):
    position = {'type': 'object', 'properties': {'start': {'type': 'integer', 'minimum': 0},
                'end': {'type': 'integer', 'minimum': 1}}, 'required': ['start', 'end'], 'additionalProperties': False}
    citation = {'type': 'object', 'additionalProperties': False, 'required': ['kind', 'reference'],
                'properties': {'kind': {'const': 'reference'}, 'reference': {'type': 'string'}}}
    claim = {'type': 'object', 'additionalProperties': False, 'required': ['text', 'state', 'citations'],
             'properties': {'text': {'type': 'string'},
                 'state': {'type': 'string', 'enum': ['supported', 'absent', 'unknown', 'conflict']},
                 'depends_on': {'type': 'array', 'items': {'type': 'integer', 'minimum': 0, 'maximum': 11}},
                 'citations': {'type': 'array', 'maxItems': 8, 'items': citation}}}
    definitions = [
        ('list_sources', 'List immutable Git records available at this checkpoint.', {}, []),
        ('read_source', 'Read exact original lines. Line numbers are one-based. Use small ranges. Returns a native citation reference.',
         {'source_id': {'type': 'string'}, 'start_line': {'type': 'integer', 'minimum': 1},
          'line_count': {'type': 'integer', 'minimum': 1, 'maximum': 100}}, ['source_id']),
        ('search_files', 'Search original lines with a case-insensitive regular expression. Returns at most 20 narrow matches and citation references.',
         {'pattern': {'type': 'string'}}, ['pattern']),
        ('elf_evidence_check', 'Check complete claim dependencies and original citation bindings before the final answer. Repair failed references from inspected evidence; this does not verify entailment.',
         {'claims': {'type': 'array', 'minItems': 1, 'maxItems': 12, 'items': claim}}, ['claims']),
    ]
    if condition != 'no_elf':
        definitions += [
            ('elf_docs_search_l0', 'Search original documents. Pass a selected doc_id and pointer.locator.position to elf_docs_excerpts_get.',
             {'query': {'type': 'string'}, 'top_k': {'type': 'integer', 'minimum': 1, 'maximum': 8}}, ['query']),
            ('elf_docs_excerpts_get', 'Read an original at a search result byte position, with a copyable native reference. L1 is a focused window; L2 is for a missing premise.',
             {'doc_id': {'type': 'string'}, 'position': position, 'level': {'enum': ['L0', 'L1', 'L2']}}, ['doc_id', 'position', 'level']),
        ]
    if condition == 'full_elf':
        definitions += [
            ('elf_searches_create', 'Start handoffs with planned_search and top_k=4. Resolve relevant note IDs with elf_evidence_pack before broad original reads.',
             {'query': {'type': 'string'}, 'mode': {'enum': ['quick_find', 'planned_search']},
              'top_k': {'type': 'integer', 'minimum': 1, 'maximum': 12}}, ['query', 'mode']),
            ('elf_searches_get', 'Expand cached candidates before issuing another query.',
             {'search_id': {'type': 'string'}, 'top_k': {'type': 'integer', 'minimum': 1, 'maximum': 12}}, ['search_id']),
            ('elf_evidence_pack', 'Resolve selected memory notes to verified original windows. Start with a small source budget.',
             {'note_ids': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1, 'maxItems': 12},
              'max_source_bytes': {'type': 'integer', 'minimum': 1, 'maximum': 32768}}, ['note_ids']),
            ('elf_evidence_recall', 'Recall missing evidence using up to four literal subjects. Optionally specify historical as_of in RFC3339.',
             {'subjects': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1, 'maxItems': 4}, 'as_of': {'type': ['string', 'null']}}, ['subjects']),
            ('elf_graph_query', 'Traverse native entity relationships. Read evidence_note_ids with elf_evidence_pack.',
             {'subject': {'type': 'object', 'properties': {'surface': {'type': 'string'}}, 'required': ['surface']},
              'as_of': {'type': ['string', 'null']}}, ['subject']),
        ]
    return [{'type': 'function', 'function': {'name': n, 'description': d, 'parameters': {
        'type': 'object', 'properties': p, 'required': r, 'additionalProperties': False}}} for n, d, p, r in definitions]


def opening_tool(condition, trace, hydrate_sources=False):
    """A bounded host opening; subsequent retrieval remains the agent's choice."""
    if not trace:
        return {'no_elf': 'search_files', 'source_only': 'elf_docs_search_l0',
                'full_elf': 'elf_searches_create'}[condition]
    if hydrate_sources and condition == 'source_only' and len(trace) == 1 and any(
            tool['name'] == 'elf_docs_search_l0' and tool['result'].get('items')
            for tool in trace[0]['tools']):
        return 'elf_docs_excerpts_get'
    if condition == 'full_elf' and len(trace) == 1 and any(
            tool['name'] == 'elf_searches_create' and tool['result'].get('items')
            for tool in trace[0]['tools']):
        return 'elf_evidence_pack'
    return None


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
        raw = self.sources[source_id]['text'].encode()
        lines = raw.splitlines(keepends=True)
        first = int(args.get('start_line', 1)) - 1
        count = int(args.get('line_count', 24))
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
        if name == 'elf_evidence_check':
            return self.api('/v2/evidence/check', args)
        if name == 'elf_docs_search_l0':
            data = self.api('/v2/docs/search/l0', {'candidate_k': 60, 'top_k': 4, **args})
            return {'items': [{**row, 'source_id': self.inverse[row['doc_id']]}
                             for row in data['items'] if row['doc_id'] in self.inverse]}
        if name == 'elf_docs_excerpts_get':
            if args['doc_id'] not in self.inverse:
                raise ValueError('Future or foreign source crossed the checkpoint')
            return {**self.api('/v2/docs/excerpts', args), 'source_id': self.inverse[args['doc_id']]}
        if name in ('elf_searches_create', 'elf_searches_get'):
            if name == 'elf_searches_create':
                data = self.api('/v2/searches', {'top_k': 4, 'candidate_k': 60, **args})
            else:
                from urllib.parse import urlencode
                data = self.api('/v2/searches/' + args['search_id'] + '?' + urlencode({'top_k': args.get('top_k', 8), 'touch': 'false'}))
            return {k: data[k] for k in ('search_id', 'items', 'total', 'has_more') if k in data}
        if name == 'elf_evidence_pack':
            return self.project_pack(self.api('/v2/evidence/pack', {'max_source_bytes': 6000, **args}))
        if name == 'elf_evidence_recall':
            data = self.api('/v2/evidence/recall', args)
            return {**data, 'pack': self.project_pack(data['pack'])}
        return self.api('/v2/graph/query', {'limit': 12, **args})

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
        # A truncated pack cannot keep a successful completeness claim or dangling links.
        if value.get('truncated'):
            pack = value.get('pack', value)
            if 'sources' in pack and 'notes' in pack:
                available = {source.get('reference') for source in pack['sources']}
                pack['complete'] = False
                for note in pack['notes']:
                    refs = note.get('source_references', [])
                    if any(ref not in available for ref in refs):
                        note['complete'] = False
                        note['source_references'] = [ref for ref in refs if ref in available]
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
