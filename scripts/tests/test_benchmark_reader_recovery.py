"""Missing-output recovery must never select improved answers after scoring."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


class ReaderRecoveryTests(unittest.TestCase):
    def test_wrong_completed_answer_is_retained_and_only_missing_output_is_requested(self):
        path = Path(__file__).resolve().parents[1] / 'benchmark-deep.py'
        spec = importlib.util.spec_from_file_location('reader_recovery_test', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); old = root / 'old'; new = root / 'new'
            (old / 'input').mkdir(parents=True)
            inputs = {'actions': [{'action': 'query', 'case_id': c, 'scope': 's', 'question': c} for c in ('a', 'b')]}
            oracle = {c: {'lane': 'test', 'facts': ['right'], 'supported': True, 'evidence': ['source'], 'forbidden': []} for c in ('a', 'b')}
            wrong = {'case_id': 'a', 'supported': True, 'text': 'wrong'}
            target = {'id': 'elf'}
            bundle = {'target': target, 'providers': {}, 'image_digest': 'pinned-image', 'workload_group': 'test',
                      'workload_sha256': hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest(),
                      'source': {'commit': 'previous-reader'}, 'retrieval_source': {'commit': 'original-native'},
                      'runtime': {}, 'exit_code': 0, 'execution_error': None, 'cleanup': {'passed': True},
                      'answer_protocol': {'source_labels': True},
                      'native': {'results': [{'case_id': c, 'status': 'completed', 'contexts': [{'evidence_id': 'source', 'text': 'right'}]} for c in ('a', 'b')]},
                      'scores': [{'case_id': 'a', 'answer': wrong}, {'case_id': 'b', 'answer': None}]}
            for name, value in [('bundle.json', bundle), ('oracle.json', oracle), ('input/workload.json', inputs)]:
                (old / name).write_text(json.dumps(value))
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({'targets': [target], 'providers': {}, 'runner': {'image': 'image', 'compose_file': 'unused.yml'}}))
            response = {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({'answers': [{'case_id': 'b', 'supported': True, 'text': 'right'}]})}}]}
            argv = ['benchmark-deep.py', '--target', 'elf', '--manifest', str(manifest), '--artifact-root', str(new), '--reanswer', str(old), '--retry-answer-errors']
            with patch.object(sys, 'argv', argv), patch.object(module, 'workload', return_value=(inputs, oracle)), patch.object(module, 'source_fingerprint', return_value={'commit': 'new-reader'}), patch.object(module, 'provider_environment', return_value={}), patch.object(module, 'request_answers', return_value=response) as ask:
                self.assertEqual(module.main(), 1)  # The original wrong answer stays wrong.
            self.assertEqual([x['case_id'] for x in ask.call_args.args[0]], ['b'])
            result = json.loads((new / 'bundle.json').read_text())
            self.assertEqual(result['scores'][0]['answer'], wrong)
            self.assertEqual(result['coverage']['answered'], 2)
            self.assertEqual(result['coverage']['correct'], 1)
            self.assertEqual(result['retrieval_source'], {'commit': 'original-native'})
            self.assertEqual(result['answer_recovery']['retried_cases'], ['b'])


if __name__ == '__main__':
    unittest.main()
