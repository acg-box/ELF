"""Native answer consumption must not add facts or trust a second citation authority."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark_agent.answer import parse_claim_answer


class ClaimAnswerTests(unittest.TestCase):
    def test_derive_references_without_changing_claims_or_text(self):
        claims = [{'text': 'Recorded fact', 'state': 'supported', 'citations': [
            {'kind': 'reference', 'reference': 'source-a'},
            {'kind': 'reference', 'reference': 'source-a'}]}]
        value = {'text': 'Recorded fact', 'supported': True, 'claims': claims,
                 'citations': [{'kind': 'reference', 'reference': 'wrong-second-list'}]}
        result = parse_claim_answer(json.dumps(value))
        self.assertEqual(result['claims'], claims)
        self.assertEqual(result['text'], value['text'])
        self.assertEqual(result['citations'], ['source-a'])
        self.assertFalse(result['legacy_envelope_valid'])

    def test_accept_native_claims_without_redundant_top_list(self):
        result = parse_claim_answer(json.dumps({'text': 'Unknown', 'supported': False,
            'claims': [{'text': 'Unknown', 'state': 'unknown', 'citations': []}]}))
        self.assertEqual(result['citations'], [])
        self.assertFalse(result['legacy_envelope_valid'])

    def test_preserve_legacy_note_and_source_claims(self):
        value = {'text': 'Fact', 'supported': True, 'citations': ['note-a', 'doc-a'],
                 'claims': [{'text': 'Fact', 'state': 'supported', 'citations': [
                     {'kind': 'note', 'note_id': 'note-a', 'quote': 'Fact'},
                     {'kind': 'source', 'doc_id': 'doc-a', 'content_hash': 'hash', 'quote': 'Fact'}]}]}
        result = parse_claim_answer(json.dumps(value))
        self.assertTrue(result['legacy_envelope_valid'])
        self.assertEqual(result['claims'], value['claims'])

    def test_existing_single_code_block_policy_is_preserved(self):
        from benchmark_agent.runner import parse_answer
        value = {'text': 'Known', 'supported': True, 'citations': ['a'],
                 'claims': [{'text': 'Known', 'state': 'supported', 'citations': [{'kind': 'reference', 'reference': 'a'}]}]}
        wrapped = '```json\n' + json.dumps(value) + '\n```'
        legacy, native = parse_answer(wrapped), parse_claim_answer(wrapped)
        self.assertEqual(legacy['claims'], native['claims'])
        self.assertEqual(legacy['text'], native['text'])
        self.assertFalse(legacy['format_compliant'])
        self.assertFalse(native['format_compliant'])
        with self.assertRaises(ValueError):
            parse_claim_answer(wrapped + '\n' + wrapped)

    def test_no_prose_salvage_or_unknown_citation_kind(self):
        with self.assertRaises(ValueError):
            parse_claim_answer('Explanation first. {"claims": []}')
        with self.assertRaises(ValueError):
            parse_claim_answer(json.dumps({'text': 'x', 'supported': True,
                'claims': [{'text': 'x', 'citations': [{'kind': 'invented', 'reference': 'x'}]}]}))


if __name__ == '__main__':
    unittest.main()
