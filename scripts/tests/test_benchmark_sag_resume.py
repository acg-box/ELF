"""Prove that continuation skips only the completed source prefix."""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark_deep import resume
from benchmark_deep import drivers

class ResumeTests(unittest.TestCase):
    def test_native_ingest_reprocesses_first_incomplete_source(self):
        action = {'scope': 'scale-1000', 'action': 'ingest', 'items': [
            {'evidence_id': 'completed', 'text': 'one'}, {'evidence_id': 'incomplete', 'text': 'two'}]}
        receipt = {phase: {'source_id': 'completed', 'data_source_id': 'scale-1000',
            'relation_status': 'succeeded', 'vector_status': 'succeeded'} for phase in ('chunks','events')}
        class Engine:
            def __init__(self, *args, **kwargs): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=root/'scale-1000-sag-progress.json';path.write_text(json.dumps([receipt]))
            (root/'sag-resume.json').write_text(json.dumps({'scope':'scale-1000',
                'completed_source_records':1,'receipt_sha256':resume.digest(path)}))
            with patch.dict(sys.modules, {'zleap':SimpleNamespace(), 'zleap.sag':SimpleNamespace(DataEngine=Engine)}), \
                 patch('benchmark_targets.sag_engine.configuration', return_value={}), \
                 patch('benchmark_targets.sag_engine.ingest', new_callable=AsyncMock, return_value={'new':True}) as ingest:
                result=asyncio.run(drivers.sag_action(action,root))
                self.assertEqual(ingest.await_count,1)
                self.assertEqual(ingest.call_args.args[2]['evidence_id'],'incomplete')
                self.assertEqual(result['native'],[receipt,{'new':True}])
    def test_reject_failed_or_reordered_receipts(self):
        action={'scope':'scale-1000','items':[{'evidence_id':'a'},{'evidence_id':'b'}]}
        for source,status in [('b','succeeded'),('a','failed')]:
            row={p:{'source_id':source,'data_source_id':'scale-1000','relation_status':status,
                'vector_status':'succeeded'} for p in ('chunks','events')}
            with self.assertRaises(ValueError): resume.completed_prefix(action,[row])
    def test_copy_keeps_original_state_and_duration_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous, output = root / 'previous', root / 'output'
            state = previous / 'artifacts/deep-state'
            (state / 'sag-shared').mkdir(parents=True)
            (previous / 'input').mkdir()
            (state / 'sag-shared/sag.db').write_bytes(b'retained-native-state')
            inputs = {'actions': [{'action': 'ingest', 'scope': 'scale-1000',
                'items': [{'evidence_id': 'a'}, {'evidence_id': 'b'}]},
                {'action': 'query', 'scope': 'scale-1000', 'case_id': 'q'}]}
            receipt = {phase: {'source_id': 'a', 'data_source_id': 'scale-1000',
                'relation_status': 'succeeded', 'vector_status': 'succeeded'}
                for phase in ('chunks', 'events')}
            (state / 'scale-1000-sag-progress.json').write_text(json.dumps([receipt]))
            bundle = {'target': {'id': 'sag-engine'}, 'workload_group': 'scale-1000',
                'providers': {}, 'image_digest': 'same-image', 'cleanup': {'passed': True},
                'coverage': {'native_completed': 0}, 'duration_seconds': 123,
                'source': {'commit': 'original'}}
            for path, data in [(previous / 'bundle.json', bundle),
                    (previous / 'input/workload.json', inputs), (previous / 'oracle.json', {})]:
                path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                resume.prepare_sag_resume(previous, output, inputs, {}, {}, 'changed-image')
            self.assertFalse(output.exists())
            provenance = resume.prepare_sag_resume(previous, output, inputs, {}, {}, 'same-image')
            self.assertEqual(provenance['original_duration_seconds'], 123)
            self.assertEqual(provenance['remaining_source_records'], 1)
            self.assertEqual(provenance['state_file_count'], 1)
            copied = output / 'artifacts/deep-state/sag-shared/sag.db'
            self.assertEqual(copied.read_bytes(), b'retained-native-state')
            copied.write_bytes(b'continued')
            self.assertEqual((state / 'sag-shared/sag.db').read_bytes(), b'retained-native-state')
            self.assertEqual(provenance['original_bundle_sha256'], resume.digest(previous / 'bundle.json'))
            bundle['combined_attempt_duration_seconds'] = 456
            (previous / 'bundle.json').write_text(json.dumps(bundle))
            again = resume.prepare_sag_resume(previous, root / 'another', inputs, {}, {}, 'same-image')
            self.assertEqual(again['original_duration_seconds'], 456)
            self.assertEqual(again['previous_attempt_duration_seconds'], 123)

    def test_fresh_ingest_has_no_retained_receipts(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(resume.retained_receipts({},Path(d)),[])

if __name__ == '__main__': unittest.main()
