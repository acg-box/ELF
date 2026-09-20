"""Benchmark contract regression contracts."""

from __future__ import annotations

from scripts.tests.benchmark_support import BenchmarkCase

from benchmark_contract import FAILURE_CLASSES
from benchmark_contract import FORBIDDEN_PRODUCT_KEYS
from benchmark_contract import NativeContextError
from pathlib import Path
from benchmark_contract import SUITE_IDS
from benchmark_contract import answer_cases
import copy
from benchmark_contract import evaluate_unit
import json
from benchmark_contract import materialize_product_fixtures
from benchmark_contract import opaque_evidence_id
from benchmark_runner import answers as runner_answers
from benchmark_contract import sha256_json
import tempfile
from benchmark_contract import validate_manifest
from benchmark_contract import validate_suite


class BenchmarkContractTests(BenchmarkCase):
    def test_manifest_and_exact_four_suites_validate(self) -> None:
        validate_manifest(self.manifest)
        self.assertEqual(set(self.suites), set(SUITE_IDS))
        self.assertEqual(len(self.manifest["targets"]), 12)
        self.assertEqual(self.manifest["runner"]["capacity"], 1)
        for suite_id, expected in {
            "common-core-v1": 24,
            "memory-lifecycle-v1": 8,
            "knowledge-structure-v1": 8,
            "repository-knowledge-v1": 8,
        }.items():
            validate_suite(self.suites[suite_id])
            self.assertEqual(len(self.suites[suite_id]["jobs"]), expected)


    def test_readiness_subset_keeps_canonical_suite_identity(self) -> None:
        suite = self.subset("memory-lifecycle-v1", 2)
        validate_suite(suite)
        self.assertEqual(suite["suite_id"], "memory-lifecycle-v1")
        self.assertEqual(len(suite["jobs"]), 2)


    def test_product_payload_is_opaque_and_preserves_native_operations(self) -> None:
        suite = self.subset("memory-lifecycle-v1")
        with tempfile.TemporaryDirectory() as directory:
            paths = materialize_product_fixtures(suite, Path(directory))
            self.assertEqual(len(paths), 1)
            payload = json.loads(paths[0].read_text(encoding="utf-8"))
        encoded = json.dumps(payload, sort_keys=True)
        for forbidden in FORBIDDEN_PRODUCT_KEYS:
            self.assertNotIn(f'"{forbidden}"', encoded)
        self.assertTrue(payload["job_id"].startswith("j_"))
        self.assertTrue(payload["corpus"]["items"][0]["evidence_id"].startswith("e_"))
        self.assertTrue(payload["operations"])
        self.assertTrue(payload["operations"][0]["evidence_id"].startswith("e_"))


    def test_product_evidence_identity_is_scoped_to_its_job(self) -> None:
        shared = "same-source-name"
        self.assertNotEqual(
            opaque_evidence_id(shared, "first-job"),
            opaque_evidence_id(shared, "second-job"),
        )


    def test_cross_job_evidence_cannot_receive_current_job_credit(self) -> None:
        suite = self.subset("common-core-v1", 2)
        unit = self.completed_unit("elf", suite)
        other_job = suite["jobs"][1]
        cross_job_id = opaque_evidence_id(
            other_job["corpus"][0]["evidence_id"], other_job["job_id"]
        )
        for phase in ("cold", "warm"):
            unit["phases"][phase]["jobs"][0]["evidence_ids"] = [cross_job_id]
            unit["phases"][phase]["jobs"][0]["returned_count"] = 1
        evaluated = evaluate_unit(suite, unit, self.targets["elf"])
        first = next(
            row
            for row in evaluated["phases"]["warm"]["jobs"]
            if row["job_id"] == suite["jobs"][0]["job_id"]
        )
        self.assertEqual(first["recall_at_5"], 0.0)
        self.assertEqual(first["source_trace_rate"], 0.0)


    def test_elf_and_external_adapter_have_identical_normalized_shape(self) -> None:
        suite = self.subset("common-core-v1", 2)
        elf = evaluate_unit(suite, self.completed_unit("elf", suite), self.targets["elf"])
        mem0 = evaluate_unit(
            suite, self.completed_unit("mem0", suite), self.targets["mem0"]
        )

        def shape(value):
            if isinstance(value, dict):
                return {key: shape(child) for key, child in value.items()}
            if isinstance(value, list):
                return [shape(value[0])] if value else []
            return type(value).__name__

        self.assertEqual(shape(elf), shape(mem0))
        self.assertEqual(elf["schema"], "elf.benchmark_result/v1")


    def test_every_typed_failure_is_preserved_and_unscored(self) -> None:
        suite = self.subset("common-core-v1")
        target = self.targets["elf"]
        for classification in FAILURE_CLASSES - {"completed"}:
            with self.subTest(classification=classification):
                unit = runner_answers.failure_unit(target, suite, classification, "typed failure")
                result = evaluate_unit(suite, unit, target)
                self.assertEqual(result["classification"], classification)
                self.assertFalse(result["phases"]["warm"]["quality_denominator"])
                self.assertEqual(result["phases"]["warm"]["counts"]["scored"], 0)


    def test_missing_native_operation_becomes_adapter_failure(self) -> None:
        suite = self.subset("memory-lifecycle-v1")
        unit = self.completed_unit("elf", suite)
        unit["phases"]["warm"]["jobs"][0]["operations"] = []
        result = evaluate_unit(suite, unit, self.targets["elf"])
        self.assertEqual(result["classification"], "adapter_failed")
        self.assertTrue(result["contract_failures"])
        self.assertEqual(result["phases"]["warm"]["counts"]["scored"], 0)


    def test_missing_mutation_readback_becomes_adapter_failure_before_answering(self) -> None:
        suite = self.subset("memory-lifecycle-v1")
        unit = self.completed_unit("elf", suite)
        del unit["phases"]["warm"]["jobs"][0]["contexts"]
        with self.assertRaises(NativeContextError):
            answer_cases(suite, unit, 12000)
        attached = runner_answers.attach_shared_answers(suite, unit, {}, 12000)
        self.assertEqual(attached["result_class"], "adapter_failed")
        result = evaluate_unit(suite, unit, self.targets["elf"])
        self.assertEqual(result["classification"], "adapter_failed")
        self.assertIn("omitted native ranked contexts", result["contract_failures"][0])


    def test_incomplete_completed_unit_becomes_adapter_failure(self) -> None:
        suite = self.subset("common-core-v1", 2)
        unit = self.completed_unit("elf", suite)
        unit["phases"]["warm"]["jobs"].pop()
        result = evaluate_unit(suite, unit, self.targets["elf"])
        self.assertEqual(result["classification"], "adapter_failed")
        self.assertIn(
            "warm phase did not return the exact scheduled job set",
            result["contract_failures"],
        )
        self.assertEqual(result["phases"]["warm"]["counts"]["scored"], 0)


    def test_failed_top_level_unit_cannot_enter_quality_denominator(self) -> None:
        suite = self.subset("common-core-v1")
        unit = self.completed_unit("elf", suite)
        unit["result_class"] = "adapter_failed"
        result = evaluate_unit(suite, unit, self.targets["elf"])
        self.assertEqual(result["classification"], "adapter_failed")
        self.assertFalse(result["phases"]["warm"]["quality_denominator"])
        self.assertIsNone(result["phases"]["warm"]["metrics"])
        self.assertEqual(result["phases"]["warm"]["counts"]["scored"], 0)


    def test_deterministic_scoring_replays_byte_identically(self) -> None:
        suite = self.subset("common-core-v1", 2)
        unit = self.completed_unit("elf", suite)
        first = evaluate_unit(suite, copy.deepcopy(unit), self.targets["elf"])
        second = evaluate_unit(suite, copy.deepcopy(unit), self.targets["elf"])
        self.assertEqual(sha256_json(first), sha256_json(second))
        self.assertEqual(first["phases"]["warm"]["metrics"]["mean_recall_at_5"], 1.0)


    def test_shared_answer_context_uses_native_post_update_text(self) -> None:
        suite = self.subset("memory-lifecycle-v1")
        unit = self.completed_unit("elf", suite)
        cases = answer_cases(suite, unit, 12000)
        replacement = suite["jobs"][0]["operations"][0]["text"]
        rendered = "\n".join(cases[0]["context"])
        self.assertIn(replacement, rendered)
        self.assertNotIn(suite["jobs"][0]["corpus"][0]["text"], rendered)

        unit["phases"]["warm"]["jobs"][0]["contexts"][0]["text"] = suite["jobs"][0][
            "corpus"
        ][0]["text"]
        stale = "\n".join(answer_cases(suite, unit, 12000)[0]["context"])
        self.assertNotIn(replacement, stale)


    def test_unsupported_answer_requires_unknown_text(self) -> None:
        suite = copy.deepcopy(self.suites["common-core-v1"])
        suite["jobs"] = [
            next(
                job
                for job in suite["jobs"]
                if job["qrels"].get("expect_unsupported")
            )
        ]
        suite["execution_mode"] = "readiness"
        unit = self.completed_unit("elf", suite)
        valid = evaluate_unit(suite, unit, self.targets["elf"])
        self.assertEqual(valid["phases"]["warm"]["jobs"][0]["answer_correct"], 1.0)
        self.assertEqual(
            valid["phases"]["warm"]["jobs"][0]["unsupported_answer_error"],
            0.0,
        )

        unit["phases"]["warm"]["jobs"][0]["answer"]["text"] = ""
        invalid = evaluate_unit(suite, unit, self.targets["elf"])
        self.assertEqual(
            invalid["phases"]["warm"]["jobs"][0]["answer_correct"], 0.0
        )
        self.assertEqual(
            invalid["phases"]["warm"]["jobs"][0]["unsupported_answer_error"],
            1.0,
        )


    def test_native_update_score_requires_receipt_and_post_update_readback(self) -> None:
        suite = self.subset("memory-lifecycle-v1")
        unit = self.completed_unit("elf", suite)
        replacement = suite["jobs"][0]["operations"][0]["text"]
        fresh = evaluate_unit(suite, unit, self.targets["elf"])
        self.assertEqual(
            fresh["phases"]["warm"]["jobs"][0]["native_update_success"], 1.0
        )

        unit["phases"]["warm"]["jobs"][0]["contexts"][0]["text"] = suite["jobs"][0][
            "corpus"
        ][0]["text"]
        stale = evaluate_unit(suite, unit, self.targets["elf"])
        self.assertNotIn(replacement, stale["phases"]["warm"]["jobs"][0]["native_contexts"][0]["text"])
        self.assertEqual(
            stale["phases"]["warm"]["jobs"][0]["native_update_success"], 0.0
        )


    def test_native_delete_score_requires_receipt_and_absent_post_delete_readback(self) -> None:
        suite = copy.deepcopy(self.suites["memory-lifecycle-v1"])
        suite["jobs"] = suite["jobs"][1:2]
        suite["execution_mode"] = "readiness"
        unit = self.completed_unit("elf", suite)
        deleted = suite["jobs"][0]["operations"][0]["evidence_id"]
        clean = evaluate_unit(suite, unit, self.targets["elf"])
        self.assertEqual(
            clean["phases"]["warm"]["jobs"][0]["native_delete_success"], 1.0
        )

        unit["phases"]["warm"]["jobs"][0]["contexts"].append(
            {
                "evidence_id": opaque_evidence_id(deleted, suite["jobs"][0]["job_id"]),
                "text": suite["jobs"][0]["corpus"][1]["text"],
            }
        )
        stale = evaluate_unit(suite, unit, self.targets["elf"])
        self.assertEqual(
            stale["phases"]["warm"]["jobs"][0]["native_delete_success"], 0.0
        )


