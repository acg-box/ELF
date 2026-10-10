"""Only native OCR annotations may enter a parser comparison."""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import patch
from scripts.tests.benchmark_support import REPO

spec = importlib.util.spec_from_file_location('document_ocr', REPO / 'scripts/benchmark-document-ocr.py')
ocr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ocr)


class DocumentOCRTests(TestCase):
    def test_annotations_preserve_source_text_without_generated_rewriting(self):
        response = {'choices': [{'message': {'content': 'invented replacement', 'annotations': [
            {'type': 'file', 'file': {'content': [{'type': 'text', 'text': 'original table'},
                                                  {'type': 'image_url', 'image_url': {'url': 'unused'}}]}}]}}]}
        self.assertEqual(ocr.annotation_text(response), ('original table', 1))

    def test_generated_answer_alone_is_not_an_ocr_receipt(self):
        with self.assertRaises(ValueError):
            ocr.annotation_text({'choices': [{'message': {'content': 'plausible text'}}]})

    def test_error_annotations_can_be_reused_without_another_paid_parse(self):
        response = {'error': {'metadata': {'file_annotations': [
            {'type': 'file', 'file': {'content': [{'type': 'text', 'text': 'original'}]}}]}}}
        self.assertEqual(ocr.annotation_text(response), ('original', 0))

    def test_resume_binds_receipt_to_fixture_pages_and_original_annotations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'document.pdf').write_bytes(b'frozen')
            digest = hashlib.sha256(b'frozen').hexdigest()
            (root / 'oracle-source.json').write_text(json.dumps([
                {'evidence_id': 'document', 'kind': 'mixed', 'file': 'document.pdf', 'sha256': digest, 'pages': 3}]))
            response = {'choices': [{'message': {'annotations': [
                {'type': 'file', 'file': {'content': [{'type': 'text', 'text': 'original'}]}}]}}]}
            receipt = {'source_sha256': digest, 'pages': 3, 'response': response}
            (root / 'document.json').write_text(json.dumps(receipt))
            (root / 'document.txt').write_text('original')
            argv = ['ocr', '--fixture-root', str(root), '--artifact-root', str(root), '--ledger', str(root / 'ledger.json')]
            with patch('sys.argv', argv), patch.dict(os.environ, {'OPENROUTER_API_KEY': 'unused-test-key'}), patch.object(ocr.urllib.request, 'build_opener') as opener:
                self.assertEqual(ocr.main(), 0)
                opener.return_value.open.assert_not_called()
                (root / 'document.txt').write_text('rewritten')
                with self.assertRaisesRegex(ValueError, 'original annotations'):
                    ocr.main()
                (root / 'document.txt').write_text('original')
                receipt['pages'] = 1
                (root / 'document.json').write_text(json.dumps(receipt))
                with self.assertRaisesRegex(ValueError, 'different source'):
                    ocr.main()
            self.assertFalse((root / 'ledger.lock').exists())
