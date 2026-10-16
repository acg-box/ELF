"""Native answer consumption must not add facts or trust a second citation authority."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark_agent.answer import AnswerRejected, finalize_answer, parse_claim_answer


class ClaimAnswerTests(unittest.TestCase):
    def test_final_gate_retains_the_recorded_bad_quote_as_a_rejected_draft(self):
        root = Path(__file__).resolve().parents[2] / 'config/benchmark/evidence/2026-10-15-elf-native-kb-memory'
        recorded = json.loads((root / 'answers/elf-formal-post-memory-1-0.json').read_text())['answer']
        claims = []
        for citation in recorded['citations']:
            _, doc, content_hash, _, _ = citation['handle'].split('/')
            claims.append({'text': citation['quote'], 'state': 'supported', 'citations': [
                {'kind': 'source', 'doc_id': doc, 'content_hash': content_hash, 'quote': citation['quote']}]})
        draft = {'text': recorded['answer'], 'supported': True, 'claims': claims}
        before = json.dumps(draft, sort_keys=True)
        bindings = json.loads((root / 'native/elf-formal-post-memory-1-0-bindings.json').read_text())
        def api(path, body):
            self.assertEqual(path, '/v2/evidence/check')
            self.assertEqual(body['claims'], claims)
            return bindings
        with self.assertRaises(AnswerRejected) as rejected:
            finalize_answer(draft, api)
        self.assertEqual(rejected.exception.bindings, bindings)
        self.assertEqual(json.dumps(draft, sort_keys=True), before)
        self.assertIn(' ... ', draft['claims'][0]['citations'][0]['quote'])

    def test_final_gate_requires_all_verdicts_and_does_not_accept_truthy_strings(self):
        draft = {'text': 'Fact', 'supported': True, 'claims': [
            {'text': 'Fact', 'state': 'supported', 'citations': []}]}
        for rows in [[], [{'claim_index': 1, 'binding_verified': True}],
                     [{'claim_index': 0, 'binding_verified': True}] * 2]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                finalize_answer(draft, lambda *args: {'claims': rows})
        with self.assertRaises(AnswerRejected):
            finalize_answer(draft, lambda *args: {'claims': [{'claim_index': 0, 'binding_verified': 'false'}]})
        with self.assertRaises(ValueError):
            finalize_answer({**draft, 'claims': []}, lambda *args: self.fail('Empty claims must not reach the checker'))

    def test_checked_answer_is_a_snapshot_and_unknown_is_not_forced_into_a_claim(self):
        draft = {'text': 'Not established.', 'supported': False, 'claims': [
            {'text': 'Not established.', 'state': 'unknown', 'citations': []}]}
        calls = []
        bindings = {'claims': [{'claim_index': 0, 'binding_verified': True}],
                    'semantic_support': 'not_evaluated'}
        def api(path, body):
            calls.append(body)
            return bindings
        final = finalize_answer(draft, api)
        self.assertEqual(final['answer'], draft)
        self.assertEqual(final['answer']['claims'], calls[0]['claims'])
        draft['claims'][0]['text'] = 'Changed after verification'
        self.assertEqual(final['answer']['claims'][0]['text'], 'Not established.')
        self.assertEqual(final['claim_bindings']['semantic_support'], 'not_evaluated')

    def test_checker_unavailability_never_returns_an_answer(self):
        draft = {'text': 'Fact', 'supported': True, 'claims': [
            {'text': 'Fact', 'state': 'supported', 'citations': []}]}
        def unavailable(*args):
            raise OSError('Native checker unavailable')
        with self.assertRaises(OSError):
            finalize_answer(draft, unavailable)

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
