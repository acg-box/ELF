"""Benchmark report regression contracts."""

from __future__ import annotations

from scripts.tests.benchmark_support import BenchmarkCase, load_script

import copy
from benchmark_report import coverage
from benchmark_contract import evaluate_unit
import re
from benchmark_report import decisions as report_decisions
from benchmark_report import metrics as report_metrics
from benchmark_report import roadmap as report_roadmap

REPORT = load_script("benchmark_report_cli", "scripts/benchmark-report.py")


class BenchmarkReportTests(BenchmarkCase):
    def test_report_has_required_english_decision_sections(self) -> None:
        suite = self.subset("common-core-v1")
        unit = self.completed_unit("elf", suite)
        evaluation = evaluate_unit(suite, unit, self.targets["elf"])
        row = {
            "target": "elf",
            "unit_result": unit,
            "evaluation": evaluation,
            "cleanup": {"passed": True},
        }
        bundle = {
            "schema": "elf.benchmark_bundle/v1",
            "mode": "complete_measured_run",
            "source": {"head": "abc", "dirty": False, "content_sha256": "def"},
            "provider_routes": {},
            "provider_preflight": {},
            "acceptance": {"passed": True, "findings": []},
            "target_pins": {"elf": {}},
            "target_contracts": {
                "pageindex": {
                    "not_applicable": {
                        "common-core-v1": "The pinned revision constructs a hierarchy but exposes no native ranked retrieval operation."
                    }
                }
            },
            "target_image_digests": {},
            "suite_results": {"common-core-v1": {"results": [row]}},
        }
        report = REPORT.publish(bundle)
        for heading in (
            "Decision Summary",
            "Five Product Decisions",
            "Coverage and Failures",
            "Measured Product Observations",
            "ELF Development Order",
        ):
            self.assertIn(heading, report)
        self.assertIsNone(re.search(r"[\u3400-\u9fff]", report))
        self.assertNotIn("N/A", report)
        self.assertIn("Not applicable", report)
        self.assertIn(
            "The pinned revision constructs a hierarchy but exposes no native ranked retrieval operation.",
            report,
        )


    def test_report_does_not_interpret_jobs_from_reclassified_elf_unit(self) -> None:
        suite = self.subset("memory-lifecycle-v1")
        unit = self.completed_unit("elf", suite)
        unit["phases"]["warm"]["jobs"][0]["operations"] = []
        evaluation = evaluate_unit(suite, unit, self.targets["elf"])
        row = {
            "target": "elf",
            "unit_result": unit,
            "evaluation": evaluation,
            "cleanup": {"passed": True},
        }
        bundle = {
            "target_pins": {"elf": {}},
            "suite_results": {"memory-lifecycle-v1": {"results": [row]}},
        }
        self.assertEqual(evaluation["classification"], "adapter_failed")
        self.assertEqual(report_roadmap.elf_jobs(bundle), [])
        summary = "\n".join(report_roadmap.elf_job_summary(bundle))
        self.assertIn("whole unit unscored", summary)
        self.assertNotIn("Strongest scenarios", summary)
        roadmap = "\n".join(report_roadmap.roadmap(bundle))
        self.assertIn("no attributable ELF metric failure", roadmap)
        self.assertNotIn("Eliminate native ELF runtime failures", roadmap)
        observations = "\n".join(report_decisions.product_observations(bundle))
        self.assertIn("an unscored unit cannot support a measured strength", observations)
        self.assertNotIn("memory-lifecycle-v1:adapter_failed", observations)


    def test_zero_retrieval_does_not_become_stale_suppression_strength(self) -> None:
        suite = self.subset("common-core-v1")
        elf = {
            "target": "elf",
            "evaluation": evaluate_unit(
                suite, self.completed_unit("elf", suite), self.targets["elf"]
            ),
            "cleanup": {"passed": True},
        }
        qmd = {
            "target": "qmd",
            "evaluation": evaluate_unit(
                suite, self.completed_unit("qmd", suite), self.targets["qmd"]
            ),
            "cleanup": {"passed": True},
        }
        qmd_metrics = qmd["evaluation"]["phases"]["warm"]["metrics"]
        qmd_metrics["mean_recall_at_5"] = 0.0
        qmd_metrics["mean_ndcg_at_5"] = 0.0
        qmd_metrics["forbidden_or_stale_evidence_hit_rate"] = 0.0
        qmd_metrics["privacy_scope_violation_rate"] = 0.0
        qmd_metrics["source_or_citation_trace_rate"] = None
        leaders = "\n".join(
            report_metrics.metric_leaders(
                [elf, qmd],
                [
                    "forbidden_or_stale_evidence_hit_rate",
                    "privacy_scope_violation_rate",
                ],
            )
        )
        self.assertNotIn("qmd", leaders)
        bundle = {
            "target_pins": {"elf": {}, "qmd": {}},
            "suite_results": {"common-core-v1": {"results": [elf, qmd]}},
        }
        observations = "\n".join(report_decisions.product_observations(bundle))
        self.assertIn("zero stale hits and zero recall", observations)
        qmd_line = next(line for line in observations.splitlines() if "**qmd**" in line)
        self.assertNotIn("Forbidden or stale evidence hit rate (directional value 1.000)", qmd_line)
        self.assertNotIn("measured relative strength: Recall@5 (directional value 0.000)", qmd_line)


    def test_shared_answer_metrics_remain_observations_without_product_attribution(self) -> None:
        suite = self.subset("knowledge-structure-v1")
        evaluation = evaluate_unit(
            suite, self.completed_unit("elf", suite), self.targets["elf"]
        )
        job = evaluation["phases"]["warm"]["jobs"][0]
        job["answer_correct"] = 0.0
        job["unsupported_answer_error"] = 1.0
        row = {
            "target": "elf",
            "evaluation": evaluation,
            "cleanup": {"passed": True},
        }
        bundle = {
            "schema": "elf.benchmark_bundle/v1",
            "mode": "complete_measured_run",
            "source": {"head": "abc", "dirty": False},
            "provider_routes": {},
            "provider_preflight": {},
            "acceptance": {"passed": True, "findings": []},
            "target_pins": {"elf": {}},
            "target_contracts": {},
            "target_image_digests": {},
            "suite_results": {"knowledge-structure-v1": {"results": [row]}},
        }

        table = "\n".join(coverage.result_table([row]))
        self.assertIn("0.000", table)
        self.assertEqual(
            report_metrics.metric_leaders(
                [row],
                ["programmatic_answer_correctness", "unsupported_answer_rate"],
            ),
            [],
        )
        observations = "\n".join(report_decisions.product_observations(bundle))
        self.assertNotIn("Programmatic answer correctness (directional value", observations)
        self.assertNotIn("Unsupported-answer rate (directional value", observations)
        roadmap = "\n".join(report_roadmap.roadmap(bundle))
        self.assertNotIn("Tighten evidence-bound answers and refusal", roadmap)

        without_answer = copy.deepcopy(job)
        without_answer["answer_correct"] = 1.0
        without_answer["unsupported_answer_error"] = 0.0
        self.assertEqual(
            report_roadmap.job_desirability(job), report_roadmap.job_desirability(without_answer)
        )

        report = REPORT.publish(bundle)
        self.assertIn("end-to-end observation, not product or roadmap attribution", report)
        self.assertIn("do not declare product strengths, winners, ELF scenario strengths, or roadmap actions", report)


    def test_quality_table_excludes_failed_rows_without_hiding_coverage(self) -> None:
        suite = self.subset("common-core-v1")
        row = {
            "target": "elf",
            "evaluation": evaluate_unit(
                suite,
                self.completed_unit("elf", suite),
                self.targets["elf"],
            ),
            "cleanup": {"passed": True},
        }
        row["evaluation"]["classification"] = "adapter_failed"
        row["evaluation"]["phases"]["warm"]["quality_denominator"] = False
        self.assertNotIn("elf", "\n".join(coverage.result_table([row], "common-core-v1")))
        self.assertIn(
            "elf",
            "\n".join(
                coverage.coverage_table(
                    {"suite_results": {"common-core-v1": {"results": [row]}}}
                )
            ),
        )


    def test_roadmap_lists_all_failures_and_separates_privacy(self) -> None:
        suite = self.subset("common-core-v1", 10)
        evaluation = evaluate_unit(
            suite, self.completed_unit("elf", suite), self.targets["elf"]
        )
        for job in evaluation["phases"]["warm"]["jobs"]:
            job["forbidden_evidence_hits"] = ["stale"]
            job["privacy_scope_violation"] = 0.0
            job["answer_correct"] = 1.0
        bundle = {
            "target_pins": {"elf": {}},
            "suite_results": {
                "common-core-v1": {
                    "results": [
                        {
                            "target": "elf",
                            "evaluation": evaluation,
                            "cleanup": {"passed": True},
                        }
                    ]
                }
            },
        }
        roadmap = "\n".join(report_roadmap.roadmap(bundle))
        self.assertIn("Strengthen stale-evidence suppression", roadmap)
        self.assertIn("failed jobs (10)", roadmap)
        self.assertNotIn("Repair privacy-scope isolation", roadmap)
        for job in suite["jobs"]:
            self.assertIn(job["job_id"], roadmap)


    def test_decisions_disclose_performance_and_add_thresholded_action(self) -> None:
        suite = self.subset("common-core-v1", 2)
        rows = []
        for target, latency, ingest in (("elf", 100.0, 1000.0), ("qmd", 5.0, 10.0)):
            evaluation = evaluate_unit(
                suite, self.completed_unit(target, suite), self.targets[target]
            )
            evaluation["cold_ingest_duration_ms"] = ingest
            evaluation["phases"]["warm"]["metrics"]["mean_query_latency_ms"] = latency
            for job in evaluation["phases"]["warm"]["jobs"]:
                job["latency_ms"] = latency
                job["answer_correct"] = 1.0
                job["forbidden_evidence_hits"] = []
            rows.append(
                {
                    "target": target,
                    "evaluation": evaluation,
                    "cleanup": {"passed": True},
                }
            )
        bundle = {
            "target_pins": {"elf": {}, "qmd": {}},
            "suite_results": {"common-core-v1": {"results": rows}},
        }
        decisions = "\n".join(report_decisions.five_decisions(bundle))
        roadmap = "\n".join(report_roadmap.roadmap(bundle))
        self.assertIn("ELF performance disposition", decisions)
        self.assertIn("warm is 20.0× the fastest non-ELF row", decisions)
        self.assertIn("Shorten the retrieval and ingest critical path", roadmap)
        self.assertIn("jobs above the 10× same-job latency threshold (2)", roadmap)
        for job in suite["jobs"]:
            self.assertIn(job["job_id"], roadmap)


