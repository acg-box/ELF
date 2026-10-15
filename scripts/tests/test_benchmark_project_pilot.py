"""Prove chronology, evidence budgets, and condition boundaries before paid work."""
import json
import gzip
import hashlib
from pathlib import Path
import sys
import unittest
import tempfile
import io
import urllib.error
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark_pilot.corpus import load, spans
from benchmark_pilot.corpus import save
from benchmark_pilot.export import export
from benchmark_pilot.runtime import Runtime
from benchmark_pilot.runner import document_request, require_calibration
from benchmark_pilot.evidence import memory_use
from benchmark_pilot.tools import SourceTools, opening_tool, schemas


class ProjectPilotTests(unittest.TestCase):
    def setUp(self):
        self.source = {'id': 's01', 'title': 'record', 'timestamp': '2026-10-04T00:00:00Z',
                       'text': 'Old plan\n中文原文\nNew decision\n', 'stage': 0}
        self.documents = {'s01': {'doc_id': 'native-a', 'content_hash': 'abc'}}
        self.protocol = {'max_evidence_bytes': 1500, 'max_tool_result_bytes': 600}

    def host(self, condition, api=lambda *args: None):
        return SourceTools(condition, [self.source], self.documents, api, self.protocol)

    def test_all_arms_read_identical_exact_utf8_bytes(self):
        results = [self.host(c).call('read_source', {'source_id': 's01', 'start_line': 2, 'line_count': 1})
                   for c in ('no_elf', 'source_only', 'full_elf')]
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1], results[2])
        self.assertEqual(results[0]['text'], '中文原文\n')
        self.assertEqual(results[0]['end'] - results[0]['start'], len('中文原文\n'.encode()))

    def test_host_opening_uses_available_tools_and_does_not_repeat_empty_memory(self):
        for arm in ('no_elf', 'source_only', 'full_elf'):
            self.assertIn(opening_tool(arm, []), {t['function']['name'] for t in schemas(arm)})
        trace = [{'tools': [{'name': 'elf_searches_create', 'result': {'items': []}}]}]
        self.assertIsNone(opening_tool('full_elf', trace))
        trace[0]['tools'][0]['result']['items'] = [{'note_id': 'a'}]
        self.assertEqual(opening_tool('full_elf', trace), 'elf_evidence_pack')
        self.assertIsNone(opening_tool('full_elf', trace * 2))

    def test_chat_capture_preserves_original_role_and_origin(self):
        origin = {'schema': 'doc_source_ref/v1', 'doc_type': 'chat',
                  'thread_id': 'session-1', 'role': 'assistant', 'ts': self.source['timestamp'],
                  'source_kind': 'chat_excerpt', 'canonical_uri': 'local://session-1/message-1'}
        source = {**self.source, 'role': 'assistant', 'source_ref': origin}
        request = document_request(source)
        self.assertEqual(request['content'].encode(), self.source['text'].encode())
        self.assertEqual(request['source_ref']['role'], 'assistant')
        self.assertEqual(request['source_ref']['canonical_uri'], origin['canonical_uri'])
        self.assertNotIn('commit_sha', request['source_ref'])
        self.assertNotIn('captured_at', origin)

    def test_formal_admission_requires_memory_originals_in_checked_calibration(self):
        trace = [{'tools': [{'name': 'elf_searches_create', 'result': {'items': [{'note_id': 'n1'}]}}]}]
        answer = {'claims': [{'citations': [{'kind': 'reference', 'reference': 'native-ref'}]}]}
        handles = {'E1': 'native-ref'}
        self.assertEqual(memory_use(trace, answer, handles)['originals_cited'], 0)
        trace.append({'tools': [{'name': 'elf_evidence_pack', 'result': {
            'notes': [{'note_id': 'n1', 'source_references': ['E1']}],
            'sources': [{'reference': 'E1', 'text': 'Exact original'}]}}]})
        used = memory_use(trace, answer, handles)
        self.assertEqual(used, {'notes_read': 1, 'originals_read': 1, 'originals_cited': 1})
        self.assertEqual(memory_use(trace, {'claims': []}, handles)['originals_cited'], 0)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol = {'conditions': ['full_elf'], 'calibration_repetitions': 1}
            tasks = [{'id': 'cal', 'phase': 'calibration'}]
            save(root / 'calibration-completed.json', {})
            with self.assertRaises(ValueError):
                require_calibration(root, protocol, tasks)
            row = {'task_id': 'cal', 'phase': 'calibration', 'condition': 'full_elf',
                   'repetition': 1, 'status': 'completed', 'memory_use': used,
                   'all_references_seen': True, 'claim_bindings': {'claims': [{'binding_verified': True}]}}
            path = root / 'cases/cal--full_elf--1/result.json'
            save(path, row)
            require_calibration(root, protocol, tasks)
            for changes in ({'memory_use': {}}, {'status': 'invalid_answer'},
                            {'all_references_seen': False}, {'claim_bindings': {'claims': [{'binding_verified': False}]}}):
                save(path, {**row, **changes})
                with self.assertRaises(ValueError):
                    require_calibration(root, protocol, tasks)

    def test_source_control_hydrates_before_more_discovery(self):
        trace = [{'tools': [{'name': 'elf_docs_search_l0', 'result': {'items': [{'doc_id': 'a'}]}}]}]
        self.assertEqual(opening_tool('source_only', trace, True), 'elf_docs_excerpts_get')
        self.assertIsNone(opening_tool('source_only', trace, False))
        self.assertIsNone(opening_tool('source_only', trace * 2, True))

    def test_native_api_error_body_remains_available_to_the_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            rt = Runtime(Path(directory), Path.cwd())
            failure = urllib.error.HTTPError(rt.base, 400, 'Bad Request', {}, io.BytesIO(b'expected a reference string'))
            with patch('urllib.request.urlopen', side_effect=failure):
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    rt.api('/v2/evidence/check', {'claims': []})
                self.assertEqual(caught.exception.read(), b'expected a reference string')

    def test_native_excerpt_and_check_use_declared_routes(self):
        calls = []
        def api(path, args):
            calls.append((path, args))
            if path.endswith('/excerpts'):
                return {'reference': 'elf-source-v1/native-a/abc/0/3', 'excerpt': 'Old'}
            return {'claims': [{'binding_verified': False}], 'semantic_support': 'not_evaluated'}
        host = self.host('source_only', api)
        result = host.call('elf_docs_excerpts_get', {'doc_id': 'native-a', 'level': 'L1', 'position': {'start': 0, 'end': 3}})
        self.assertIn(result['reference'], host.references)
        check = host.call('elf_evidence_check', {'claims': []})
        self.assertFalse(check['claims'][0]['binding_verified'])
        self.assertEqual(calls[0][0], '/v2/docs/excerpts')
        self.assertEqual(calls[1][0], '/v2/evidence/check')

    def test_future_source_is_not_readable_or_resolvable(self):
        host = self.host('full_elf')
        self.assertIn('error', host.call('read_source', {'source_id': 'future'}))
        with self.assertRaises(ValueError):
            host.project_pack({'sources': [{'doc_id': 'future'}], 'notes': []})

    def test_no_memory_calls_in_baselines(self):
        def forbidden(*args):
            self.fail('Ablated native API must not be called')
        for condition in ('no_elf', 'source_only'):
            self.assertIn('error', self.host(condition, forbidden).call('elf_searches_create', {'query': 'decision'}))
        self.assertIn('error', self.host('no_elf', forbidden).call('elf_docs_search_l0', {'query': 'decision'}))

    def test_truncation_preserves_parseable_complete_records_and_read_citations(self):
        host = self.host('no_elf')
        result = host.call('search_files', {'pattern': '.'})
        self.assertLessEqual(len(json.dumps(result, ensure_ascii=False).encode()), 600)
        json.loads(json.dumps(result))
        for row in result.get('items', []):
            self.assertIn(row['reference'], host.references)
        self.assertNotIn('elf-source-v1/future/abc/0/1', host.references)

    def test_extraction_windows_cover_every_original_byte(self):
        text = ('中文\n' * 900) + 'tail'
        rows = list(spans(text, 600))
        self.assertEqual(''.join(r[2] for r in rows), text)
        for left, right in zip(rows, rows[1:]):
            self.assertEqual(left[1], right[0])
        self.assertEqual(rows[-1][1], len(text.encode()))

    def test_changed_original_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = {**self.source, 'sha256': hashlib.sha256(self.source['text'].encode()).hexdigest()}
            original = gzip.compress((json.dumps(source) + '\n').encode(), mtime=0)
            (root / 'sources.jsonl.gz').write_bytes(original)
            (root / 'checkpoints.json').write_text('[]')
            (root / 'freeze.json').write_text(json.dumps({'files': {'sources.jsonl.gz': hashlib.sha256(original).hexdigest()}}))
            self.assertEqual(load(root)[0][0]['text'], self.source['text'])
            (root / 'sources.jsonl.gz').write_bytes(original + b'changed')
            with self.assertRaises(ValueError):
                load(root)

    def test_public_export_excludes_private_source_questions_answers_and_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'private'
            fixture = root / 'fixture'
            canary = 'PRIVATE_PROJECT_CANARY'
            source = {**self.source, 'id': canary, 'title': canary, 'path': canary, 'text': canary,
                      'sha256': hashlib.sha256(canary.encode()).hexdigest()}
            fixture.mkdir(parents=True)
            (fixture / 'sources.jsonl.gz').write_bytes(gzip.compress((json.dumps(source) + '\n').encode(), mtime=0))
            save(fixture / 'checkpoints.json', [])
            save(fixture / 'tasks.json', [{'id': canary, 'phase': 'formal', 'question': canary}])
            save(fixture / 'oracle.json', [{'id': canary, 'criteria': [{'obligation': canary, 'patterns': [canary]}]}])
            save(fixture / 'protocol.json', {'conditions': ['no_elf'], 'formal_repetitions': 1,
                'frozen_extraction': False, 'reuse_receipts': [canary], 'private_annotation': canary})
            save(fixture / 'freeze.json', {'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.iterdir()}})
            save(root / 'budget-ledger.json', {'prior_paid_usd': 0, 'requests': [{
                'ordinal': 1, 'kind': 'chat', 'status': 'completed', 'reserved_usd': 0,
                'model': 'test-model', 'usage': {'cost': 0, 'private_annotation': canary},
                'provider_error': canary}]})
            (root / 'private-elf.toml').write_text(f'''[providers]
api_key = "{canary}"
[memory]
max_note_chars = 240
max_notes_per_add_event = 3
[security]
evidence_min_quotes = 1
evidence_max_quotes = 2
evidence_max_quote_bytes = 320
''')
            cell_id = canary + '--no_elf--1'
            save(root / 'cases' / cell_id / 'result.json', {'cell': cell_id, 'task_id': canary, 'phase': 'formal',
                'condition': 'no_elf', 'repetition': 1, 'status': 'completed', 'seconds': 1, 'tool_calls': 1,
                'evidence_bytes': 10, 'answer': {'text': canary, 'claims': []},
                'usage_before': {'requests': 0, 'paid_usd': 0}, 'usage_after': {'requests': 0, 'paid_usd': 0},
                'stage': 0, 'pid': 100})
            save(root / 'cases' / cell_id / 'trace.json', [{'tools': [{'name': 'read_source', 'result': {'source_id': canary, 'text': canary}}]}])
            save(root / 'review.json', {cell_id: {'accepted': True, 'passed_criteria': 1, 'flags': [], 'private_notes': canary}})
            save(root / 'native-stage-0.json', {'stage': 0, 'sources_verified': 1, 'vectors': {}, 'notes': [canary]})
            (root / 'provider-reuse.jsonl').write_text('\n'.join(json.dumps(row) for row in (
                {'kind': 'embedding', 'reused': True}, {'kind': 'embedding', 'reused': False},
                {'kind': 'extraction', 'reused': False}, {'kind': 'extraction', 'reused': False})))
            save(root / 'qualifier-audit.json', {
                'extraction': {'admitted_facts': 2, 'private_notes': canary},
                'storage': {'fact_rows': 2, 'all_stored_facts_match_admitted_clauses': True,
                            'private_payload': canary}, 'private_sources': canary})
            destination = Path(directory) / 'public'
            export(root, destination)
            self.assertTrue((destination / 'manifest.json').exists())
            reuse = json.loads((destination / 'provider-reuse.json').read_text())
            self.assertEqual(reuse['forwarded_embeddings'], 1)
            self.assertEqual(reuse['forwarded_extractions'], 2)
            metrics = json.loads((destination / 'measurements.json').read_text())
            self.assertIsNone(metrics['summary']['no_elf']['amortized_usd_per_task'])
            self.assertIn('Incremental replay cost', metrics['preparation_cost_basis'])
            qualifiers = json.loads((destination / 'qualifier-audit.json').read_text())
            self.assertEqual(qualifiers['storage']['fact_rows'], 2)
            for path in destination.iterdir():
                self.assertNotIn(canary, path.read_text(), path.name)


if __name__ == '__main__':
    unittest.main()
