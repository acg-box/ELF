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


if __name__ == '__main__':
    unittest.main()
