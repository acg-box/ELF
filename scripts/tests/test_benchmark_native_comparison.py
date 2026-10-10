"""Contracts for the matched-budget comparison and held-out memory fixture."""
import importlib.util
from pathlib import Path
import unittest
import json
import tempfile
from benchmark_deep.memory_comparison import workload
from benchmark_targets.hindsight import contexts_from_native, chunk_contexts_from_native

path=Path(__file__).resolve().parents[1]/'benchmark-native-comparison.py'
spec=importlib.util.spec_from_file_location('native_comparison',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class NativeComparisonTests(unittest.TestCase):
    def test_raw_chunks_use_native_text_and_source_identity(self):
        native={'results':[{'document_id':'doc-b','chunk_id':'b','text':'Compressed fact'}],
                'source_facts':{'f':{'document_id':'doc-a','chunk_id':'a','text':'Parent fact'}},
                'chunks':{'a':{'text':'Original A','chunk_index':0},'b':{'text':'Original B','chunk_index':0}}}
        rows=chunk_contexts_from_native(native)
        self.assertEqual([(r['evidence_id'],r['text']) for r in rows],[('doc-b','Original B'),('doc-a','Original A')])
        self.assertNotIn('Compressed fact',str(rows))

    def test_raw_chunks_reject_conflicting_native_sources(self):
        native={'results':[{'document_id':'a','chunk_id':'c'},{'document_id':'b','chunk_id':'c'}],
                'chunks':{'c':{'text':'Original'}}}
        with self.assertRaises(ValueError):chunk_contexts_from_native(native)

    def test_full_native_budget_keeps_sixth_fact(self):
        native={'results':[{'document_id':f'd{i}','text':str(i)} for i in range(7)]}
        self.assertEqual(len(contexts_from_native(native)),5)
        self.assertEqual(len(contexts_from_native(native,limit=None)),7)

    def test_resume_rejects_changed_frozen_workload(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'frozen.json'
            module.freeze(path,{'items':['original']})
            module.freeze(path,{'items':['original']})
            with self.assertRaises(ValueError):
                module.freeze(path,{'items':['changed']})

    def test_reader_accepts_one_identified_object_without_selecting_an_answer(self):
        answer={'case_id':'case','text':'value','supported':True}
        for shape in (answer,[answer]):
            response={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'answers':shape})}}]}
            self.assertEqual(module.decode_answer(response,'case'),answer)
            with self.assertRaises(ValueError):module.decode_answer(response,'other')

    def test_current_answer_rejects_stale_addition(self):
        e={'supported':True,'facts':['new-code'],'forbidden':['old-code']}
        self.assertTrue(module.score(e,'new-code'))
        self.assertFalse(module.score(e,'new-code or old-code'))

    def test_fixture_has_separate_dev_entity_and_no_oracle_in_sources(self):
        data,oracle=workload()
        self.assertEqual(len(data['items']),20)
        self.assertEqual(sum(q['split']=='test' for q in data['queries']),16)
        self.assertEqual(sum(q['split']=='dev' for q in data['queries']),4)
        self.assertTrue(all(set(i)=={'evidence_id','text','timestamp'} for i in data['items']))
        for q in data['queries']:
            self.assertEqual(q['split']=='dev','Devon' in q['question'])
            self.assertIn(q['case_id'],oracle)

if __name__=='__main__':unittest.main()
