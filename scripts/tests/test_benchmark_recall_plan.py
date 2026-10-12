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
