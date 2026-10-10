"""Protect raw PDF transport and the independent source/answer boundary."""
import base64
import unittest
from unittest.mock import patch

from benchmark_deep.complex_documents import workload
from benchmark_targets import ragflow


class ComplexDocumentsTests(unittest.TestCase):
    def test_binary_upload_preserves_bytes_and_opaque_filename(self):
        payload = b'%PDF-1.4\n\x00\xff\xfe\n'
        item = {'evidence_id': 'e_sample', 'text': 'Do not upload this extracted text',
                'file_base64': base64.b64encode(payload).decode(),
                'file_extension': '.pdf', 'content_type': 'application/pdf'}
        with patch.object(ragflow, 'request', return_value=[{'id': 'native'}]) as request:
            self.assertEqual(ragflow.upload('dataset', item), 'native')
        body = request.call_args.kwargs['data']
        self.assertIn(payload, body)
        self.assertIn(b'filename="e_sample.pdf"', body)
        self.assertNotIn(item['text'].encode(), body)

    def test_questions_and_oracle_are_not_in_ingestion_items(self):
        inputs, oracle = workload()
        self.assertEqual(len(oracle), 24)
        for item in inputs['actions'][0]['items']:
            self.assertEqual(set(item), {'evidence_id', 'text', 'file_base64', 'file_extension', 'content_type'})
            self.assertTrue(base64.b64decode(item['file_base64']).startswith(b'%PDF-'))
        self.assertEqual(sum(not v['supported'] for v in oracle.values()), 8)


if __name__ == '__main__':
    unittest.main()
