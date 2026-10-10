"""Keep RAGFlow evidence mapping independent of source text and unknown hits."""
import unittest
from unittest.mock import patch
from benchmark_targets.ragflow import contexts_from_chunks, wait_parsed
from benchmark_budget import prepare_request


class RagflowContextTests(unittest.TestCase):
    def test_go_terminal_ingestion_receipt_does_not_wait_for_removed_run_field(self):
        docs = [{'id':'native-a','ingestion_status':'COMPLETED','chunk_count':1}]
        with patch('benchmark_targets.ragflow.request', return_value={'docs':docs}), \
             patch('benchmark_targets.ragflow.time.sleep', side_effect=AssertionError('Unexpected wait')):
            self.assertEqual(wait_parsed('dataset', ['native-a']), docs)
        with patch('benchmark_targets.ragflow.request', return_value={'docs':[{'id':'native-a','ingestion_status':'FAILED'}]}):
            with self.assertRaisesRegex(RuntimeError, 'parsing failed'):
                wait_parsed('dataset', ['native-a'])

    def test_dimension_profile_is_explicit_and_preserves_default(self):
        body = {'input': ['example'], 'dimensions': 4096}
        default, _, _ = prepare_request(body, 'embedding')
        fixed, _, _ = prepare_request(body, 'embedding', 'nebius', 1536)
        self.assertEqual(default['dimensions'], 4096)
        self.assertEqual(fixed['dimensions'], 1536)
        self.assertEqual(body['dimensions'], 4096)
        self.assertEqual(fixed['provider']['only'], ['nebius'])

    def test_document_identity_not_answer_text_maps_evidence(self):
        rows = contexts_from_chunks([
            {'id':'c1','document_id':'native-a','content':'same text'},
            {'id':'c2','document_id':'native-b','content':'same text'},
            {'id':'c3','document_id':'unknown','content':'same text'}],
            {'source-a':'native-a','source-b':'native-b'})
        self.assertEqual([r['evidence_id'] for r in rows], ['source-a','source-b',None])
        self.assertEqual([r['native_chunk_id'] for r in rows], ['c1','c2','c3'])
        self.assertEqual(len(rows),3)


if __name__ == '__main__':
    unittest.main()
