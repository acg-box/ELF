"""Validate matched system inputs before paid ingestion."""
from unittest import TestCase
from scripts.tests.benchmark_support import load_script


class SystemComparisonTests(TestCase):
    def test_fixed_coverage_and_oracle_separation(self):
        module = load_script('system_comparison', 'scripts/benchmark-system-comparison.py')
        suites = module.suites()
        self.assertEqual(len(suites['documents']['items']), 14)
        self.assertEqual(len(suites['documents']['queries']), 50)
        memory = suites['memory']
        self.assertEqual(sum(q['split'] == 'test' for q in memory['queries']), 16)
        self.assertEqual(sum(q['split'] == 'dev' for q in memory['queries']), 4)
        for suite in suites.values():
            self.assertEqual(len({x['evidence_id'] for x in suite['items']}), len(suite['items']))
            for item in suite['items']:
                self.assertEqual(set(item) - {'evidence_id', 'text', 'timestamp'}, set())
                self.assertTrue(item['text'].strip())
            self.assertTrue(all(q['case_id'] in suite['oracle'] for q in suite['queries']))
