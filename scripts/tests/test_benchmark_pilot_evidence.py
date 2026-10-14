"""Protect complete verdicts and exact host-owned references across the reader boundary."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark_pilot.evidence import EvidenceHandles, compact_check
from benchmark_pilot.reuse import key_for
from benchmark_pilot.tools import SourceTools, schemas


class EvidenceClientTests(unittest.TestCase):
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

    def test_provider_reuse_keys_preserve_input_and_full_dimensions(self):
        body = {'model': 'qwen/qwen3-embedding-8b', 'input': ['原文'], 'dimensions': 4096}
        self.assertNotEqual(key_for(body, 'embedding'), key_for({**body, 'dimensions': 1536}, 'embedding'))
        self.assertNotEqual(key_for(body, 'embedding'), key_for({**body, 'input': ['changed']}, 'embedding'))
        make = lambda limit: {'messages': [{'content': 'Return an instance matching this JSON Schema:\nMAX_NOTE_CHARS = ' + str(limit) + '\n[{"content":"same original"}]'}]}
        self.assertEqual(key_for(make(240), 'extraction'), key_for(make(512), 'extraction'))
        self.assertIsNone(key_for({'messages': [{'content': 'Ordinary reader task'}]}, 'extraction'))
