"""Keep scoring repairs uniform and separate from immutable product input."""

from scripts.tests.benchmark_support import BenchmarkCase, REPO
from benchmark_contract import evaluate_unit, load_json, materialize_product_fixtures
from benchmark_contract.review import review_suite
from benchmark_contract.metrics import _answer_scores, _operation_scores
from benchmark_runner.profiles import integrity_findings
import tempfile
from pathlib import Path


class ScoringReviewTests(BenchmarkCase):
    def test_provenance_counts_native_rows_without_penalizing_shared_sources(self):
        contract = load_json(REPO / "config/benchmark/scoring-contract-v3.json")
        suite = review_suite(self.subset("common-core-v1"), contract)
        unit = self.completed_unit("elf", suite)
        row = unit["phases"]["warm"]["jobs"][0]
        context = row["contexts"][0]
        row["contexts"] = [dict(context), dict(context), {"evidence_id": None, "text": "Unattributed native text"}]
        row["evidence_ids"] = [context["evidence_id"]]
        row["returned_count"] = 3
        score = evaluate_unit(suite, unit, self.targets["elf"])["phases"]["warm"]["jobs"][0]
        self.assertEqual(score["source_trace_rate"], 0.666667)
        suite.pop("source_trace_measurement")
        legacy = evaluate_unit(suite, unit, self.targets["elf"])["phases"]["warm"]["jobs"][0]
        self.assertEqual(legacy["source_trace_rate"], 0.333333)

    def test_ineligible_empty_suite_is_not_a_failed_product(self):
        bundle = {"target_contracts": {"mem0": {"suites": ["memory-lifecycle-v1"]}},
                  "coverage": {"knowledge-structure-v1": []},
                  "suite_results": {"knowledge-structure-v1": {
                      "scheduled_targets": [], "results": []}}}
        self.assertEqual(integrity_findings(bundle), [])
        bundle["coverage"]["memory-lifecycle-v1"] = ["planned-job"]
        self.assertIn("memory-lifecycle-v1: eligible suite was not executed", integrity_findings(bundle))

    def test_reported_native_failure_is_zero_success_not_a_missing_receipt(self):
        operation = {"type": "update", "evidence_id": "e_one", "text": "new fact"}
        failed = {"requested_type": "update", "native_type": "update",
                  "classification": "product_failed", "native_success": False}
        self.assertEqual(_operation_scores(["update"], [operation], [failed], [], []),
                         (0.0, None, []))
        self.assertEqual(_operation_scores(["update"], [operation], [], [], []),
                         (0.0, None, ["update"]))

    def test_review_scores_the_requested_facts_and_rejects_wrong_paths(self):
        contract = load_json(REPO / "config/benchmark/answer-contract-v2.json")
        jobs = {job["job_id"]: job for suite in self.suites.values()
                for job in review_suite(suite, contract)["jobs"]}
        for case_id, text, supported in [
            ("knowledge-meridian-recovery", "Drain the failed Meridian canary, then restore the last signed release.", True),
            ("repo-delete-retired-runbook", "docs/runbooks/meridian.md", True),
            ("core-scope-nova", "unknown", False),
        ]:
            self.assertEqual(_answer_scores(jobs[case_id]["qrels"],
                {"text": text, "supported": supported})[0], 1.0)
        self.assertEqual(_answer_scores(jobs["repo-delete-retired-runbook"]["qrels"],
            {"text": "docs/legacy/meridian-unsafe.md", "supported": True})[0], 0.0)

    def test_review_preserves_exact_product_payload(self):
        contract = load_json(REPO / "config/benchmark/answer-contract-v2.json")
        with tempfile.TemporaryDirectory() as directory:
            for key, suite in self.suites.items():
                before = materialize_product_fixtures(suite, Path(directory) / key / "before")
                after = materialize_product_fixtures(review_suite(suite, contract), Path(directory) / key / "after")
                self.assertEqual([p.read_bytes() for p in before], [p.read_bytes() for p in after])

    def test_review_rejects_a_different_question(self):
        contract = load_json(REPO / "config/benchmark/answer-contract-v2.json")
        suite = self.subset("knowledge-structure-v1", 2)
        suite["jobs"][1]["query"] = "A different question"
        with self.assertRaisesRegex(ValueError, "question differs"):
            review_suite(suite, contract)
