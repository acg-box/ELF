"""Protect complete verdicts and exact host-owned references across the reader boundary."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark_pilot.evidence import EvidenceHandles, compact_check
from benchmark_pilot.reuse import key_for
from benchmark_pilot.tools import SourceTools, schemas
from benchmark_pilot.runner import request


class EvidenceClientTests(unittest.TestCase):
    def test_repeated_original_is_compact_only_after_it_reaches_the_reader(self):
        registry = EvidenceHandles()
        original = {'reference': 'elf-source-v1/doc/hash/0/12', 'text': 'Original'}
        first = registry.project(original)
        self.assertEqual(registry.project(original)['text'], 'Original')
        registry.expose(first)
        repeated = registry.project(original)
        self.assertTrue(repeated['already_read'])
        self.assertNotIn('text', repeated)
        self.assertEqual(repeated['reference'], first['reference'])
        self.assertEqual(original['text'], 'Original')

    def test_native_read_fits_remaining_budget_and_keeps_returned_reference(self):
        calls = []
        def api(path, body):
            calls.append(body)
            # Escaping is deliberately more expensive than the raw UTF-8 cap.
            text = '\t' * body['max_bytes']
            return {'doc_id': 'doc', 'excerpt': text, 'start_offset': 100,
                    'end_offset': 100 + len(text), 'reference': f'elf-source-v1/doc/hash/100/{100 + len(text)}',
                    'verification': {'verified': True}}
        host = SourceTools('source_only', [{'id': 's1', 'timestamp': 't'}],
            {'s1': {'doc_id': 'doc'}}, api,
            {'client_v3': True, 'max_evidence_bytes': 4500, 'max_tool_result_bytes': 12000})
        result = host.call('elf_docs_excerpts_get', {'doc_id': 'doc', 'position': {'start': 100, 'end': 8000}, 'level': 'L1'})
        self.assertEqual(len(calls), 2)
        self.assertLess(calls[-1]['max_bytes'], calls[0]['max_bytes'])
        self.assertNotIn('error', result)
        self.assertGreaterEqual(host.remaining, 2048)
        self.assertEqual(len(result['excerpt']), result['end_offset'] - result['start_offset'])
        self.assertEqual(host.handles.native[result['reference']], f'elf-source-v1/doc/hash/100/{result["end_offset"]}')

    def test_discovery_keeps_only_read_locator_and_source_time(self):
        pointer = {'hashes': {'content_hash': 'h'}, 'locator': {'position': {'start': 3, 'end': 9}, 'span_id': 'span'}, 'ref': {'doc_id': 'doc'}}
        host = SourceTools('source_only', [{'id': 's1', 'timestamp': '2026-01-01'}],
            {'s1': {'doc_id': 'doc'}}, lambda *args: {'items': [{'doc_id': 'doc', 'pointer': pointer, 'snippet': 'Discovery'}]},
            {'client_v3': True, 'max_evidence_bytes': 32768, 'max_tool_result_bytes': 12000})
        item = host.call('elf_docs_search_l0', {'query': 'q'})['items'][0]
        self.assertEqual(item['pointer'], {'locator': {'position': {'start': 3, 'end': 9}}})
        self.assertEqual(item['source_timestamp'], '2026-01-01')
        self.assertEqual(host.handles.visible, set())

    def test_cached_expansion_omits_only_candidates_already_delivered(self):
        rows = [{'note_id': str(i), 'summary': 'x' * 450} for i in range(4)]
        host = SourceTools('full_elf', [], {}, lambda *args: {'search_id': 's', 'items': list(rows), 'total': 8, 'has_more': True},
            {'client_v3': True, 'max_evidence_bytes': 32768, 'max_tool_result_bytes': 900})
        first = host.call('elf_searches_create', {'query': 'q'})
        self.assertLess(len(first['items']), 4)
        second = host.call('elf_searches_get', {'search_id': 's', 'top_k': 8})
        self.assertEqual(second['already_returned_note_ids'], [r['note_id'] for r in first['items']])
        self.assertTrue(second['items'])
        self.assertNotEqual(second['items'][0]['note_id'], first['items'][0]['note_id'])

    def test_file_read_returns_complete_lines_that_fit_and_a_continuation(self):
        source = {'id': 's1', 'title': 'Original', 'timestamp': 't', 'text': 'Subject and condition.\n' * 100}
        host = SourceTools('no_elf', [source], {'s1': {'doc_id': 'doc', 'content_hash': 'hash'}}, None,
            {'client_v3': True, 'max_evidence_bytes': 2800, 'max_tool_result_bytes': 12000})
        result = host.call('read_source', {'source_id': 's1', 'line_count': 100})
        self.assertNotIn('error', result)
        self.assertLess(result['next_line'], 101)
        self.assertEqual(result['text'], source['text'].encode()[result['start']:result['end']].decode())
        self.assertGreaterEqual(host.remaining, 2048)

    def test_only_exposed_handles_resolve_and_inputs_remain_immutable(self):
        registry = EvidenceHandles()
        original = {'sources': [{'reference': 'elf-source-v1/doc/hash/0/12', 'text': 'Original'}]}
        projected = registry.project(original)
        claims = [{'text': 'Fact', 'state': 'supported', 'citations': [{'kind': 'reference', 'reference': 'E1'}]}]
        with self.assertRaises(ValueError):
            registry.resolve(claims)
        registry.expose(projected)
        self.assertEqual(registry.resolve(claims)[0]['citations'][0]['reference'], original['sources'][0]['reference'])
        self.assertEqual(claims[0]['citations'][0]['reference'], 'E1')
        self.assertEqual(projected['sources'][0]['reference'], 'E1')
        self.assertTrue(original['sources'][0]['reference'].startswith('elf-source-v1/'))

    def test_compact_check_retains_every_failure_and_dependency_slot(self):
        full = {'semantic_support': 'not_evaluated', 'claims': [
            {'claim_index': i, 'binding_verified': i != 11, 'citation_verified': [True, i != 11],
             'citation_claim_indices': [i, 0], 'resolved_citations': [{'quote': 'x' * 32000}]}
            for i in range(12)]}
        result = compact_check(full)
        self.assertEqual(len(result['claims']), 12)
        self.assertFalse(result['claims'][-1]['binding_verified'])
        self.assertEqual(result['claims'][-1]['citation_claim_indices'], [11, 0])
        self.assertLess(len(json.dumps(result)), 2048)

    def test_submit_checks_the_same_claims_that_the_host_returns(self):
        seen = []
        def api(path, body):
            seen.append(body['claims'])
            return {'claims': [{'claim_index': 0, 'binding_verified': True}], 'semantic_support': 'not_evaluated'}
        host = SourceTools('no_elf', [{'id': 's1', 'title': 'Original', 'timestamp': 't', 'text': 'Original\n'}],
            {'s1': {'doc_id': 'doc', 'content_hash': 'hash'}}, api,
            {'client_v3': True, 'max_evidence_bytes': 32768, 'max_tool_result_bytes': 12000})
        source = host.call('read_source', {'source_id': 's1'})
        answer = {'text': 'Fact', 'supported': True, 'claims': [{'text': 'Fact', 'state': 'supported',
            'citations': [{'kind': 'reference', 'reference': source['reference']}]}]}
        final = host.finalize(answer)
        self.assertEqual(final['answer']['claims'], seen[-1])
        self.assertTrue(final['all_references_seen'])
        answer['claims'][0]['citations'][0]['reference'] = 'E999'
        with self.assertRaises(ValueError):
            host.finalize(answer)
        self.assertEqual(len(seen), 1)

    def test_known_candidates_can_be_expanded_without_losing_progress(self):
        host = SourceTools('full_elf', [], {}, lambda *args: {'search_id': 's', 'items': [], 'total': 45, 'has_more': True},
            {'client_v3': True, 'max_evidence_bytes': 32768, 'max_tool_result_bytes': 12000})
        result = host.call('elf_searches_get', {'search_id': 's', 'top_k': 8})
        self.assertEqual(result['total'], 45)
        self.assertTrue(result['has_more'])

    def test_exact_source_arm_has_no_discovery_or_memory_tools(self):
        names = {t['function']['name'] for t in schemas('exact_source', True)}
        self.assertEqual(names, {'submit_answer', 'elf_evidence_check'})

    def test_submission_is_host_owned_and_never_routes_to_graph(self):
        seen = []
        host = SourceTools('full_elf', [], {}, lambda *args: seen.append(args),
            {'client_v3': True, 'max_evidence_bytes': 32768, 'max_tool_result_bytes': 12000})
        with self.assertRaises(ValueError):
            host.execute('submit_answer', {})
        self.assertEqual(seen, [])

    def test_client_requires_tools_and_closes_with_submission(self):
        protocol = {'model': 'reader', 'max_output_tokens': 128000, 'reasoning': 'medium', 'client_v3': True}
        with patch.dict('os.environ', {'LITELLM_BASE_URL': 'http://localhost', 'LITELLM_API_KEY': 'local'}), patch('urllib.request.urlopen') as send:
            send.return_value.__enter__.return_value.read.return_value = '{}'
            normal, _ = request([], 'full_elf', False, protocol)
            closing, _ = request([], 'full_elf', True, protocol)
        self.assertEqual(normal['tool_choice'], 'required')
        self.assertEqual(closing['tool_choice']['function']['name'], 'submit_answer')
        self.assertEqual(len(closing['tools']), 1)

    def test_provider_reuse_keys_preserve_input_and_full_dimensions(self):
        body = {'model': 'qwen/qwen3-embedding-8b', 'input': ['原文'], 'dimensions': 4096}
        self.assertNotEqual(key_for(body, 'embedding'), key_for({**body, 'dimensions': 1536}, 'embedding'))
        self.assertNotEqual(key_for(body, 'embedding'), key_for({**body, 'input': ['changed']}, 'embedding'))
        make = lambda limit: {'messages': [{'content': 'Return an instance matching this JSON Schema:\nMAX_NOTE_CHARS = ' + str(limit) + '\n[{"content":"same original"}]'}]}
        self.assertEqual(key_for(make(240), 'extraction'), key_for(make(512), 'extraction'))
        self.assertIsNone(key_for({'messages': [{'content': 'Ordinary reader task'}]}, 'extraction'))
