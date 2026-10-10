"""Only native OCR annotations may enter a parser comparison."""
import importlib.util
from unittest import TestCase
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
