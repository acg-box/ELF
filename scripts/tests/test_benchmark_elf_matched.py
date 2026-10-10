"""Prove that benchmark hydration cannot substitute source-oracle context."""
from unittest import TestCase
from scripts.tests.benchmark_support import load_script


class ElfMatchedTests(TestCase):
    def setUp(self):
        self.module = load_script('elf_matched', 'scripts/benchmark-elf-matched.py')

    def test_only_selected_chunk_is_hydrated_and_duplicate_is_removed(self):
        calls = []
        ref = {'doc_id':'selected','chunk_id':'chunk'}
        def api(path, body=None):
            calls.append((path, body))
            if path == '/v2/context-packs':
                return {'items':[{'item_ref':ref},{'item_ref':ref}]}
            self.assertEqual(path, '/v2/docs/excerpts')
            self.assertEqual(body['doc_id'], 'selected')
            return {'excerpt':'Native selected text','verification':{'verified':True}}
        rows, _ = self.module.retrieve(api,'Question','documents',True,
                                       {'selected':'source-id','unselected':'oracle-id'})
        self.assertEqual(rows,[{'evidence_id':'source-id','text':'Native selected text'}])
        self.assertEqual(len(calls),2)

    def test_unverified_excerpt_never_reaches_reader(self):
        def api(path, body=None):
            if path == '/v2/docs/search/l0':
                return {'items':[{'doc_id':'d','chunk_id':'c'}]}
            return {'excerpt':'Invalid text','verification':{'verified':False}}
        with self.assertRaisesRegex(ValueError,'Unverified'):
            self.module.retrieve(api,'Question','documents',False,{'d':'source-id'})
