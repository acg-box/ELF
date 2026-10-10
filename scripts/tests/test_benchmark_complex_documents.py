"""Protect raw PDF transport and the independent source/answer boundary."""
import base64
import unittest
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from benchmark_deep.complex_documents import workload
from benchmark_targets import ragflow
from benchmark_deep.contexts import reader_context
from benchmark_deep.ragflow_resume import prepare_ragflow_resume


class ComplexDocumentsTests(unittest.TestCase):
    def test_source_labels_preserve_native_fact_boundaries_without_oracle(self):
        rows = [{'evidence_id': 'source-a', 'text': 'Title A'}, {'evidence_id': 'source-a', 'text': 'Fact A'}, {'evidence_id': 'source-b', 'text': 'Fact B'}]
        self.assertEqual(reader_context(rows), 'Title A\nFact A\nFact B')
        labeled = reader_context(rows, True)
        self.assertEqual(labeled.count('[Source: source-a]'), 2)
        unresolved = reader_context([{'text': 'a'}, {'text': 'b'}], True)
        self.assertIn('[Source identity unavailable; passage 1]', unresolved)
        self.assertIn('[Source identity unavailable; passage 2]', unresolved)
        self.assertIn('[Source: source-b]\nFact B', labeled)
        self.assertEqual(len(reader_context([{'text': 'x' * 15000}], True)), 12000)

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

    def test_continuation_rejects_changed_sources_and_preserves_native_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old, new = root / 'old', root / 'new'
            (old / 'input').mkdir(parents=True)
            state = old / 'artifacts/deep-state'
            state.mkdir(parents=True)
            inputs = {'actions': [{'action': 'ingest', 'scope': 'docs', 'items': [{'evidence_id': 'e_one'}]}]}
            (old / 'input/workload.json').write_text(json.dumps(inputs))
            (old / 'oracle.json').write_text('{}')
            (old / 'bundle.json').write_text(json.dumps({'target': {'id': 'ragflow'}, 'providers': {}, 'image_digest': 'image', 'duration_seconds': 600}))
            native = {'dataset_id': 'native-dataset', 'documents': {'e_one': 'native-doc'}}
            (state / 'ragflow-docs.json').write_text(json.dumps(native))
            continuation = prepare_ragflow_resume(old, new, inputs, {}, {}, 'image')
            self.assertEqual(continuation['original_duration_seconds'], 600)
            self.assertEqual(json.loads((new / 'artifacts/deep-state/ragflow-docs.json').read_text()), native)
            inputs['actions'][0]['items'][0]['evidence_id'] = 'changed'
            with self.assertRaisesRegex(ValueError, 'unchanged workload'):
                prepare_ragflow_resume(old, root / 'bad', inputs, {}, {}, 'image')


if __name__ == '__main__':
    unittest.main()
