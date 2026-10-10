"""Regression coverage for mixed PDFs and parser-stress scoring."""
import json
import gzip
from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import patch

from benchmark_deep import page_ocr, parser_stress
from scripts.tests.benchmark_support import REPO, load_script


class PageOCRTests(TestCase):
    def test_mixed_pdf_keeps_text_page_and_ocr_on_scans_with_live_headers(self):
        def command(args):
            program = args[0]
            page = int(args[args.index('-f') + 1]) if '-f' in args else None
            if program == 'pdfinfo':
                return 'Pages: 3' if page is None else f'Page {page} size: 612 x 792 pts'
            if program == 'pdftotext':
                return {1: 'Digital body', 2: '', 3: 'Live header only'}[page]
            if program == 'pdfimages':
                return '' if page == 1 else f'{page} 0 image 612 792 rgb 3 8 image no 1 0 72 72 1K 1%'
            if program == 'tesseract':
                return 'Scanned body ' + Path(args[1]).stem
            raise AssertionError(args)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'mixed.pdf'
            source.write_bytes(b'fixture')
            with patch.object(page_ocr, 'output', side_effect=command), patch.object(page_ocr.subprocess, 'run') as render:
                result = page_ocr.extract(source)
        self.assertEqual([p['mode'] for p in result['pages']], ['poppler-layout', 'tesseract-page', 'tesseract-page'])
        self.assertEqual(render.call_count, 2)
        self.assertEqual(result['text'], '[Page 1]\nDigital body\n\n[Page 2]\nScanned body page-2\n\n[Page 3]\nScanned body page-3')

    def test_small_logo_does_not_replace_good_text_and_masks_do_not_double_count(self):
        listing = '1 0 image 100 100 rgb 3 8 image no 1 0 72 72 1K 1%\n1 1 smask 100 100 gray 1 8 image no 1 0 72 72 1K 1%'
        coverage = page_ocr.raster_coverage(listing, 612 * 792)
        self.assertAlmostEqual(coverage, 10000 / (612 * 792))
        self.assertFalse(page_ocr.needs_ocr('Good text', coverage))
        self.assertTrue(page_ocr.needs_ocr('', coverage))

    def test_numeric_fact_does_not_match_a_longer_number_or_citation(self):
        expected = {'supported': True, 'facts': ['420'], 'forbidden': ['42']}
        self.assertTrue(parser_stress.score(expected, '420 [42]'))
        self.assertFalse(parser_stress.score(expected, '1420'))
        self.assertFalse(parser_stress.score(expected, '420 or 42'))
        self.assertFalse(parser_stress.score({'supported': True, 'facts': ['8'], 'forbidden': []}, '18 [8]'))

    def test_cjk_spacing_is_not_an_ocr_error_but_wrong_name_is(self):
        expected = {'supported': True, 'facts': ['周宁'], 'forbidden': ['许岚']}
        self.assertTrue(parser_stress.score(expected, '周 宁'))
        self.assertFalse(parser_stress.score(expected, '周末'))

    def test_source_spans_preserve_numeric_cell_boundaries(self):
        self.assertTrue(parser_stress.span_present('<td>420</td><td>8</td>', '420'))
        self.assertTrue(parser_stress.span_present('420 8 42', '42'))
        self.assertFalse(parser_stress.span_present('420 8', '42'))
        self.assertTrue(parser_stress.span_present('1,420 CNY', '1420'))

    def test_stress_sources_do_not_include_oracle_and_require_matching_extraction(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'source.pdf').write_bytes(b'pdf')
            digest = hashlib.sha256(b'pdf').hexdigest()
            doc = {'evidence_id': 'source', 'file': 'source.pdf', 'sha256': digest, 'pages': 1,
                   'questions': [{'lane': 'probe', 'question': 'Question?', 'facts': ['secret oracle'], 'forbidden': []}]}
            (root / 'oracle-source.json').write_text(json.dumps([doc]))
            parsed = {'source_sha256': digest, 'pages': [{}], 'text': 'Original content'}
            (root / 'source.json').write_text(json.dumps(parsed))
            data, oracle = parser_stress.workload(root, root)
            self.assertNotIn('secret oracle', json.dumps(data['actions'][0]))
            self.assertEqual(oracle['stress-000']['facts'], ['secret oracle'])
            parsed['pages'] = []
            (root / 'source.json').write_text(json.dumps(parsed))
            with self.assertRaises(ValueError):
                parser_stress.workload(root, root)

    def test_historical_parser_run_retains_its_exact_frozen_protocol(self):
        runner = load_script('ragflow_parsers', 'scripts/benchmark-ragflow-parsers.py')
        evidence = REPO / 'config/benchmark/evidence/2026-10-10-ragflow-ocr'
        expected = json.loads((evidence / 'protocol.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'ocr').mkdir()
            with gzip.open(evidence / 'parser-outputs.jsonl.gz', 'rt') as stream:
                for line in stream:
                    row = json.loads(line)
                    if row['parser'] == 'mistral-ocr':
                        (root / 'ocr' / (row['evidence_id'] + '.txt')).write_text(row['text'])
            def stop_before_network(path, actual):
                self.assertEqual(actual, expected)
                raise InterruptedError('Verified protocol; do not call providers')
            with patch('sys.argv', ['parsers', '--artifact-root', str(root)]), patch.object(runner.common, 'freeze', side_effect=stop_before_network):
                with self.assertRaises(InterruptedError):
                    runner.main()
