"""Prove chronology, evidence budgets, and condition boundaries before paid work."""
import json
import gzip
import hashlib
from pathlib import Path
import sys
import unittest
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark_pilot.corpus import load, spans
from benchmark_pilot.corpus import save
from benchmark_pilot.export import export
from benchmark_pilot.tools import SourceTools


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

    def test_future_source_is_not_readable_or_resolvable(self):
        host = self.host('full_elf')
        self.assertIn('error', host.call('read_source', {'source_id': 'future'}))
        with self.assertRaises(ValueError):
            host.project_pack({'sources': [{'doc_id': 'future'}], 'notes': []})

    def test_no_memory_calls_in_baselines(self):
        def forbidden(*args):
            self.fail('Ablated native API must not be called')
        for condition in ('no_elf', 'source_only'):
            self.assertIn('error', self.host(condition, forbidden).call('search_memories', {'query': 'decision'}))
        self.assertIn('error', self.host('no_elf', forbidden).call('search_sources', {'query': 'decision'}))

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
            save(fixture / 'protocol.json', {'conditions': ['no_elf'], 'formal_repetitions': 1, 'private_annotation': canary})
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
evidence_max_quote_chars = 320
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
            destination = Path(directory) / 'public'
            export(root, destination)
            self.assertTrue((destination / 'manifest.json').exists())
            for path in destination.iterdir():
                self.assertNotIn(canary, path.read_text(), path.name)


if __name__ == '__main__':
    unittest.main()
