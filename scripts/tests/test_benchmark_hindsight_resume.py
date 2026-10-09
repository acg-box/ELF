import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark_deep import hindsight_resume as resume
from benchmark_deep import drivers
from benchmark_deep.fixtures import workload

class HindsightResumeTests(unittest.TestCase):
 def test_restore_preparation_preserves_full_workload_and_original(self):
  with tempfile.TemporaryDirectory() as directory:
   base=Path(directory);previous=base/'previous';root=base/'new';root.mkdir()
   (previous/'input').mkdir(parents=True);(previous/'artifacts/deep-state').mkdir(parents=True)
   inputs,oracle=workload('scale-1000')
   bundle={'target':{'id':'hindsight'},'workload_group':'scale-1000','providers':{},'image_digest':'image',
    'cleanup':{'passed':True},'coverage':{'native_completed':0},'source':{'commit':'old'},'duration_seconds':123}
   for path,value in [('bundle.json',bundle),('input/workload.json',inputs),('oracle.json',oracle),
     ('artifacts/deep-state/scale-1000-ingest-progress.json',[{'success':True}]*50)]:
    (previous/path).write_text(json.dumps(value))
   archive=base/'checkpoint';archive.write_bytes(b'native-checkpoint')
   runtime=base/'runtime';(runtime/'bin').mkdir(parents=True);(runtime/'bin/postgres').touch()
   cache=base/'cache';cache.mkdir()
   descriptor=base/'state.json';descriptor.write_text(json.dumps({'original_artifact_root':str(previous),
    'original_bundle_sha256':resume.digest(previous/'bundle.json'),'archive':str(archive),
    'archive_sha256':resume.digest(archive),'postgres_runtime':str(runtime),'reranker_cache':str(cache)}))
   with self.assertRaises(ValueError):resume.prepare_hindsight_resume(descriptor,root,inputs,oracle,{},'different-image',Path('/scripts'))
   self.assertFalse((root/'native-state').exists())
   metadata,override=resume.prepare_hindsight_resume(descriptor,root,inputs,oracle,{},'image',Path('/scripts'))
   self.assertEqual(metadata['retained_source_records'],1000)
   self.assertEqual(metadata['original_duration_seconds'],123)
   self.assertEqual(len([a for a in inputs['actions'] if a['action']=='query']),10)
   self.assertEqual(json.loads((previous/'input/workload.json').read_text()),inputs)
   self.assertEqual((root/'native-state/checkpoint.dump').read_bytes(),archive.read_bytes())
   self.assertEqual(json.loads(override.read_text())['services']['hindsight']['command'],['python3','/restore-start.py'])
 def test_continuation_drains_without_duplicate_ingestion(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'hindsight-resume.json').write_text(json.dumps({'scope':'scale-1000','retained_source_records':1000}))
   action={'action':'ingest','scope':'scale-1000','items':[{}]*1000}
   with patch('benchmark_targets.hindsight.ready'),patch('benchmark_targets.hindsight.request') as request,patch('benchmark_targets.hindsight.drain',return_value={'pending':[]}) as drain:
    result=drivers.hindsight_action(action,root)
    request.assert_not_called();drain.assert_called_once_with('/v1/default/banks/deep-scale-1000',timeout_seconds=drivers.INGEST_TIMEOUT_SECONDS)
    self.assertEqual(result['readiness'],{'pending':[]})
 def test_changed_source_count_is_rejected_before_drain(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'hindsight-resume.json').write_text(json.dumps({'scope':'scale-1000','retained_source_records':1000}))
   with patch('benchmark_targets.hindsight.ready'),patch('benchmark_targets.hindsight.drain') as drain:
    with self.assertRaises(ValueError):drivers.hindsight_action({'action':'ingest','scope':'scale-1000','items':[{}]},root)
    drain.assert_not_called()

if __name__=='__main__':unittest.main()
