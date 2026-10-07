"""Protect scope separation, reuse, and the evaluator/product boundary."""

import json
import importlib.util
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark_deep.fixtures import workload


class DeepContractTests(unittest.TestCase):
    def test_scale_ingests_once_per_size_and_has_absent_controls(self):
        inputs, oracle = workload()
        self.assertEqual(len(oracle), 62)
        for size in (100, 1000):
            actions = [a for a in inputs["actions"] if a["scope"] == f"scale-{size}"]
            self.assertEqual([a["action"] for a in actions], ["ingest"] + ["query"] * 10)
            self.assertEqual(len(actions[0]["items"]), size)
            self.assertEqual(sum(not oracle[a["case_id"]]["supported"] for a in actions[1:]), 2)
        self.assertEqual(workload(), (inputs, oracle))

    def test_both_scopes_are_populated_before_canary_reads(self):
        inputs, oracle = workload()
        actions = [a for a in inputs["actions"] if a["scope"].startswith("scope-")]
        self.assertEqual([a["action"] for a in actions[:2]], ["ingest", "ingest"])
        self.assertEqual({a["scope"] for a in actions[:2]}, {"scope-a", "scope-b"})
        for action in actions[2:]:
            expected = oracle[action["case_id"]]
            foreign = "scope-b" if action["scope"] == "scope-a" else "scope-a"
            self.assertEqual(len(expected["forbidden"]), 6)
            self.assertTrue(all(foreign in word for word in expected["forbidden"]))

    def test_oracle_keys_never_enter_product_input(self):
        inputs, oracle = workload()
        forbidden = {"facts", "evidence", "forbidden", "supported", "expected_answer"}

        def walk(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(inputs)
        self.assertTrue(oracle)

    def test_mutations_precede_restart_queries_without_reingestion(self):
        inputs, _ = workload()
        actions = [a["action"] for a in inputs["actions"] if a["scope"] == "mutations"]
        self.assertEqual(actions, ["ingest"] + ["update"] * 6 + ["query"] * 6 + ["delete"] * 6 + ["query"] * 6)

class DeepGroundingTests(unittest.TestCase):
    def test_correct_value_without_case_context_is_not_a_supported_answer(self):
        from benchmark_deep.scoring import score_answer
        expected={'supported':True,'facts':['current-2-green']}
        answer={'supported':True,'text':'current-2-green'}
        scored=score_answer(expected,answer,'Dune-2 used retired-2-blue.')
        self.assertTrue(scored['answer_matches_expected'])
        self.assertFalse(scored['fact_in_supplied_context'])
        self.assertFalse(scored['correct'])
        self.assertTrue(score_answer(expected,answer,'The approved route is current-2-green.')['correct'])


class DeepProcessTests(unittest.TestCase):
    def test_action_timeout_stops_native_descendant_and_retains_failure(self):
        source = Path(__file__).resolve().parents[1] / 'benchmark-deep-unit.py'
        spec = importlib.util.spec_from_file_location('deep_unit_timeout_test', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'input').mkdir()
            (root / 'input/workload.json').write_text(json.dumps({'actions': [
                {'action': 'ingest', 'scope': 'probe', 'items': []},
                {'action': 'query', 'scope': 'probe', 'case_id': 'probe-query'},
            ]}))
            fake = root / 'native.py'
            fake.write_text('''import os, signal, subprocess, sys, time
from pathlib import Path
root = Path(__file__).parent
if '--leaf' in sys.argv:
    def stop(signum, frame):
        (root / 'stopped').write_text('terminated')
        sys.exit(0)
    signal.signal(signal.SIGTERM, stop)
    (root / 'child.pid').write_text(str(os.getpid()))
    print('native-started', flush=True)
    time.sleep(30)
else:
    child = subprocess.Popen([sys.executable, __file__, '--leaf'])
    def stop(signum, frame):
        child.wait(timeout=3)
        sys.exit(0)
    signal.signal(signal.SIGTERM, stop)
    child.wait()
''')
            try:
                with patch.object(module, '__file__', str(fake)), \
                     patch.object(module, 'INGEST_TIMEOUT_SECONDS', 1), \
                     patch.dict(os.environ, {'BENCHMARK_DEEP_ROOT': str(root)}), \
                     patch.object(sys, 'argv', [str(source), '--target', 'elf']):
                    self.assertEqual(module.main(), 1)
                self.assertEqual((root / 'stopped').read_text(), 'terminated')
                with self.assertRaises(ProcessLookupError):
                    os.kill(int((root / 'child.pid').read_text()), 0)
                result = json.loads((root / 'artifacts/deep-result.json').read_text())
                self.assertEqual([r['status'] for r in result['results']], ['failed', 'blocked_by_ingest'])
                self.assertIn('native-started', (root / 'artifacts/deep-state/operation-000.log').read_text())
            finally:
                if (root / 'child.pid').exists():
                    try:
                        os.kill(int((root / 'child.pid').read_text()), signal.SIGTERM)
                    except ProcessLookupError:
                        pass


if __name__ == "__main__":
    unittest.main()
