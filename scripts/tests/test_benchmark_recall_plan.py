"""Retrieval planning must not receive oracle answers or invent search subjects."""
import importlib.util
import json
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('evidence_context', Path(__file__).parents[1] / 'benchmark-evidence-context.py')
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class RecallPlanningTests(unittest.TestCase):
    def test_planner_input_excludes_oracle_and_source_answers(self):
        work = {'items': [{'timestamp': '2026-08-22', 'text': 'secret expected answer'}],
                'queries': [{'case_id': 'q', 'question': 'State for Cedar?', 'expected': 'hidden'}],
                'oracle': {'q': 'oracle secret'}}
        payload = json.loads(RUNNER.recall_plan_request(work)['messages'][1]['content'])
        self.assertEqual(payload, {'record_years': ['2026'], 'queries': [{'case_id': 'q', 'question': 'State for Cedar?'}]})
        plan = {'plans': [{'case_id': 'q', 'subjects': ['Cedar'], 'as_of': None}]}
        self.assertEqual(RUNNER.validate_recall_plans(plan, work)['q']['subjects'], ['Cedar'])
        plan['plans'][0]['subjects'] = ['Cedar', 'invented answer']
        projected = RUNNER.validate_recall_plans(plan, work)['q']
        self.assertEqual(projected['subjects'], ['Cedar'])
        self.assertEqual(projected['rejected_subjects'], ['invented answer'])
        plan['plans'][0]['subjects'] = ['invented answer']
        with self.assertRaises(ValueError):
            RUNNER.validate_recall_plans(plan, work)

    def test_explicit_temporal_target_does_not_change_unspecified_queries(self):
        query = {'question': 'What was in use then?'}
        data = {'pack': {}, 'supplemental_recall': {'as_of': None}}
        self.assertEqual(RUNNER.reader_request(query, data), RUNNER.reader_request(query, data, True))
        data['supplemental_recall']['as_of'] = '2026-08-08T23:59:59Z'
        request = RUNNER.reader_request(query, data, True)
        self.assertEqual(json.loads(request['messages'][1]['content'])['requested_as_of'], data['supplemental_recall']['as_of'])
        self.assertIn('not the next approval', request['messages'][0]['content'])

    def test_production_contract_is_used_without_benchmark_specific_instructions(self):
        data = {'pack': {'sources': []}, 'supplemental_recall': {'as_of': '2026-09-04T23:59:59Z'}}
        request = RUNNER.reader_request({'question': 'Who held the role?', 'rubric': 'must not leak'}, data, agent_contract=True)
        contract = (Path(__file__).parents[2] / 'config/agent/evidence-reader.md').read_text()
        self.assertEqual(request['messages'][0]['content'], contract)
        payload = json.loads(request['messages'][1]['content'])
        self.assertEqual(set(payload), {'question', 'evidence_pack', 'supplemental_recall', 'requested_as_of'})
        self.assertEqual(payload['requested_as_of'], data['supplemental_recall']['as_of'])
