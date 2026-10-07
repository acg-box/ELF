"""Protect scope separation, reuse, and the evaluator/product boundary."""

import json
from pathlib import Path
import sys
import unittest

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


if __name__ == "__main__":
    unittest.main()
