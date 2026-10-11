"""Reference semantics that must remain constant across all database adapters."""
import unittest
import numpy as np
from retrieval_lab.backends import lexical, rrf
from retrieval_lab.benchmark import exact, normalize, scale_data
from retrieval_lab.ablation import context
import tiktoken


class RetrievalLabTests(unittest.TestCase):
    def test_exact_filters_before_topk(self):
        vectors=normalize([[1.,0.],[.9,.1],[0.,1.]])
        self.assertEqual(exact(vectors,np.array([1.,0.]),np.array([0,1,1]),1,k=1),[1])

    def test_scale_is_reproducible_and_unit_length(self):
        base=normalize([[1.,0.],[0.,1.]])
        self.assertTrue(np.array_equal(scale_data(base,20),scale_data(base,20)))
        self.assertTrue(np.allclose(np.linalg.norm(scale_data(base,20),axis=1),1))

    def test_rrf_agreement_and_stable_ties(self):
        self.assertEqual(rrf([[2,1],[1,3]],k=3),[1,2,3])
        self.assertEqual(rrf([[2],[1]],k=2),[1,2])

    def test_multilingual_lexical_input_keeps_codes_and_han(self):
        self.assertEqual(lexical('中文 STREAM-42'), '中 文 stream 42')

    def test_budget_truncates_the_same_labeled_stream(self):
        encoding=tiktoken.get_encoding('cl100k_base')
        result=context([{'evidence_id':'x','text':'文档 '*100}],encoding,budget=20)
        self.assertEqual(result['tokens'],20)
        self.assertGreater(result['untruncated_tokens'],20)


if __name__ == '__main__':unittest.main()
