"""Contracts for the matched-budget comparison and held-out memory fixture."""
import importlib.util
from pathlib import Path
import unittest
from benchmark_deep.memory_comparison import workload
from benchmark_targets.hindsight import contexts_from_native

path=Path(__file__).resolve().parents[1]/'benchmark-native-comparison.py'
spec=importlib.util.spec_from_file_location('native_comparison',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class NativeComparisonTests(unittest.TestCase):
    def test_full_native_budget_keeps_sixth_fact(self):
        native={'results':[{'document_id':f'd{i}','text':str(i)} for i in range(7)]}
        self.assertEqual(len(contexts_from_native(native)),5)
        self.assertEqual(len(contexts_from_native(native,limit=None)),7)

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
