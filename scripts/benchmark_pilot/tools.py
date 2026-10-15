"""Identical source access with explicit, enforced memory ablations."""
from __future__ import annotations

import json
import re
import urllib.error

from .evidence import EvidenceHandles, compact_check


def schemas(condition, client_v3=False):
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
    if client_v3:
        definitions.append(('submit_answer', 'Submit the final answer and its complete claim chain. The host resolves citation handles and checks current access before rendering; do not write the answer again after this call.',
            {'text': {'type': 'string'}, 'supported': {'type': 'boolean'},
             'claims': {'type': 'array', 'minItems': 1, 'maxItems': 12, 'items': claim}}, ['text', 'supported', 'claims']))
    if condition == 'exact_source':
        definitions = [d for d in definitions if d[0] in ('elf_evidence_check', 'submit_answer')]
    if condition in ('source_only', 'full_elf'):
        definitions += [
            ('elf_docs_search_l0', 'Search original documents. Pass a selected doc_id and pointer.locator.position to elf_docs_excerpts_get.',
             {'query': {'type': 'string'}, 'top_k': {'type': 'integer', 'minimum': 1, 'maximum': 8}}, ['query']),
            ('elf_docs_excerpts_get', 'Read an original at a search result byte position. max_bytes bounds the original window (default 3000); the host also limits it to remaining budget. A smaller position alone does not shrink L1. Returned offsets identify the inspected bytes.',
             {'doc_id': {'type': 'string'}, 'position': position, 'level': {'enum': ['L0', 'L1', 'L2']},
              'max_bytes': {'type': 'integer', 'minimum': 1, 'maximum': 32768}}, ['doc_id', 'position', 'level']),
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
        self.handles = EvidenceHandles() if protocol.get('client_v3') else None
        self.seen_candidates = {}
        self.original_reads = []

    def result_cap(self, name):
        reserve = 2048 if self.handles and name != 'elf_evidence_check' else 0
        return min(self.remaining - reserve, self.protocol['max_tool_result_bytes'])

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
            if self.handles:
                candidate = {**self.original(source_id, start, start + len(selected) + len(line)),
                    'start_line': first + 1, 'next_line': first + 1 + len((selected + line).splitlines()),
                    'total_lines': len(lines)}
                if len(json.dumps(candidate, ensure_ascii=False).encode()) > self.result_cap('read_source'):
                    break
            selected += line
        if not selected:
            raise ValueError('One original line does not fit the common evidence-byte budget.')
        return {**self.original(source_id, start, start + len(selected)),
                'start_line': first + 1, 'next_line': first + 1 + len(selected.splitlines()), 'total_lines': len(lines)}

    def excerpt(self, args):
        source_id = self.inverse[args['doc_id']]
        if not self.handles:
            return {**self.api('/v2/docs/excerpts', args), 'source_id': source_id}
        cap = self.result_cap('elf_docs_excerpts_get')
        limit = int(args.get('max_bytes', 3000))
        if limit < 1:
            raise ValueError('max_bytes must be positive')
        # Bound at the native owner. Do not slice text while retaining a wider reference.
        def read(limit):
            body = {**args, 'max_bytes': limit}
            native = self.api('/v2/docs/excerpts', body)
            self.original_reads.append({'request': body, 'response': native})
            value = {k: native[k] for k in ('doc_id', 'excerpt', 'start_offset', 'end_offset', 'reference') if k in native}
            value.update(source_id=source_id, source_timestamp=self.sources[source_id]['timestamp'],
                         verified=native['verification']['verified'])
            if not value['verified']:
                value['verification_errors'] = native['verification']['verification_errors']
            return value
        value = read(min(limit, max(1, cap - 512)))
        if len(json.dumps(value, ensure_ascii=False).encode()) > cap:
            # JSON control-character escaping can use six bytes per original byte.
            # One conservative local read fits that case without another model turn.
            overhead = len(json.dumps({**value, 'excerpt': '', 'native_reads': 2}, ensure_ascii=False).encode()) + 32
            if cap < overhead + 6:
                raise ValueError('Original metadata does not fit the common evidence-byte budget.')
            value = read(min(limit, (cap - overhead) // 6))
            value['native_reads'] = 2
        return value

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
        allowed = {row['function']['name'] for row in schemas(self.condition, bool(self.handles))}
        if name not in allowed or name == 'submit_answer':
            raise ValueError('Tool is unavailable in this condition')
        if name == 'list_sources':
            return {'items': [{k: v for k, v in source.items() if k in ('id', 'title', 'timestamp', 'stage')}
                             for source in self.sources.values()]}
        if name == 'read_source':
            return self.read(args)
        if name == 'search_files':
            return self.grep(args['pattern'])
        if name == 'elf_evidence_check':
            if self.handles:
                checked = self.api('/v2/evidence/check', {'claims': self.handles.resolve(args['claims'])})
                return compact_check(checked)
            return self.api('/v2/evidence/check', args)
        if name == 'elf_docs_search_l0':
            data = self.api('/v2/docs/search/l0', {'candidate_k': 60, 'top_k': 4, **args})
            rows = [{**row, 'source_id': self.inverse[row['doc_id']]}
                    for row in data['items'] if row['doc_id'] in self.inverse]
            if self.handles:
                rows = [{k: v for k, v in row.items() if k in ('doc_id', 'source_id', 'title', 'snippet', 'pointer', 'score')}
                        for row in rows]
                for row in rows:
                    row['pointer'] = {'locator': {'position': row['pointer']['locator']['position']}}
                    row['source_timestamp'] = self.sources[row['source_id']]['timestamp']
            return {'items': rows}
        if name == 'elf_docs_excerpts_get':
            if args['doc_id'] not in self.inverse:
                raise ValueError('Future or foreign source crossed the checkpoint')
            return self.excerpt(args)
        if name in ('elf_searches_create', 'elf_searches_get'):
            if name == 'elf_searches_create':
                data = self.api('/v2/searches', {'top_k': 4, 'candidate_k': 60, **args})
            else:
                from urllib.parse import urlencode
                data = self.api('/v2/searches/' + args['search_id'] + '?' + urlencode({'top_k': args.get('top_k', 8), 'touch': 'false'}))
            value = {k: data[k] for k in ('search_id', 'items', 'total', 'has_more') if k in data}
            if self.handles:
                seen = self.seen_candidates.get(data['search_id'], set())
                value['already_returned_note_ids'] = [r['note_id'] for r in value['items'] if r['note_id'] in seen]
                value['items'] = [r for r in value['items'] if r['note_id'] not in seen]
            return value
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
        reserve = 2048 if self.handles and name != 'elf_evidence_check' else 0
        if self.remaining <= reserve + 100:
            return {'error': 'Common evidence-byte budget exhausted.'}
        try:
            value = self.execute(name, args)
        except urllib.error.HTTPError as error:
            if error.code >= 500 or error.code == 402:
                raise
            value = {'error': {'status': error.code, 'detail': error.read().decode()}}
        except (KeyError, ValueError, re.error) as error:
            value = {'error': str(error)}
        if self.handles:
            value = self.handles.project(value)
        cap = min(self.remaining - reserve, self.protocol['max_tool_result_bytes'])
        if name == 'elf_evidence_check' and self.handles:
            if len(json.dumps(value, ensure_ascii=False).encode()) > cap:
                value = {'error': 'Complete citation verdict does not fit. No partial success is returned.'}
            self.remaining -= len(json.dumps(value, ensure_ascii=False).encode())
            return value
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
                value = {'error': 'Result does not fit common evidence-byte budget. Request a smaller max_bytes or fewer file lines.'}
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
                    if 'evidence_quotes' in note:
                        note['evidence_quotes'] = [quote for quote in note['evidence_quotes'] if any(
                            source.get('reference') in note.get('source_references', [])
                            and quote in source.get('text', '') for source in pack['sources'])]
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
        if self.handles:
            self.handles.expose(value)
            self.references.update(self.handles.native[ref] for ref in self.handles.visible)
            if 'search_id' in value:
                self.seen_candidates.setdefault(value['search_id'], set()).update(r['note_id'] for r in value.get('items', []))
        self.remaining -= len(json.dumps(value, ensure_ascii=False).encode())
        return value

    def provide(self, selections):
        originals = []
        for selection in selections:
            value = self.original(selection['source_id'], selection['start'], selection['end'])
            originals.append(value)
        value = self.handles.project({'originals': originals})
        size = len(json.dumps(value, ensure_ascii=False).encode())
        if size > self.remaining - 2048:
            raise ValueError('Frozen exact-source evidence exceeds the common budget')
        self.remaining -= size
        self.handles.expose(value)
        self.references.update(self.handles.native[ref] for ref in self.handles.visible)
        return value

    def finalize(self, answer):
        if not isinstance(answer.get('text'), str) or not isinstance(answer.get('supported'), bool):
            raise ValueError('Expected text, supported, and claims')
        claims = self.handles.resolve(answer['claims']) if self.handles else answer['claims']
        try:
            binding = self.api('/v2/evidence/check', {'claims': claims})
        except urllib.error.HTTPError as error:
            if error.code >= 500 or error.code == 402:
                raise
            raise ValueError(error.read().decode()) from error
        refs = [c['reference'] for claim in claims for c in claim.get('citations', []) if c.get('kind') == 'reference']
        return {'answer': {**answer, 'claims': claims}, 'claim_bindings': binding,
                'all_references_seen': bool(refs) and all(ref in self.references for ref in refs)}
