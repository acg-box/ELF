"""Regression checks for selection, false-green prevention, and resumable evidence."""
from __future__ import annotations

import copy
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

from scripts.tests.benchmark_support import BenchmarkCase
from benchmark_contract import evaluate_unit, materialize_product_fixtures
from benchmark_runner.baselines import run_baseline, target_contract
from benchmark_runner.checkpoints import read_checkpoint, save_checkpoint
from benchmark_runner.execution import acceptance
from benchmark_runner.profiles import select_suite
from benchmark_runner import runtime, cli, docker
from benchmark_report import publish


class BenchmarkModeTests(BenchmarkCase):
    def row(self):
        suite = self.subset("common-core-v1")
        unit = self.completed_unit("elf", suite)
        row = {"target": "elf", "unit_result": unit,
               "evaluation": evaluate_unit(suite, unit, self.targets["elf"]),
               "cleanup": {"passed": True}, "deterministic_replay": {"passed": True}}
        return suite, row

    def test_partial_run_failures_and_missing_units_do_not_pass(self):
        suite, row = self.row()
        bundle = {"suite_results": {suite["suite_id"]: {
            "scheduled_targets": ["elf"], "results": [row]}}}
        self.assertTrue(acceptance(bundle, False)["passed"])
        for failure in ("product_failed", "adapter_failed", "timeout_failed", "provider_failed"):
            changed = copy.deepcopy(bundle)
            changed["suite_results"][suite["suite_id"]]["results"][0]["evaluation"]["classification"] = failure
            self.assertFalse(acceptance(changed, False)["passed"])
        bundle["suite_results"][suite["suite_id"]]["results"] = []
        self.assertFalse(acceptance(bundle, False)["passed"])
        self.assertFalse(acceptance({"suite_results": {}}, False)["passed"])

    def test_named_sample_covers_late_unsupported_and_scope_cases(self):
        selected = select_suite(self.suites["common-core-v1"], "measure", None)
        ids = {j["job_id"] for j in selected["jobs"]}
        self.assertIn("core-unsupported-lyra", ids)
        self.assertIn("core-scope-orion", ids)
        self.assertEqual(len(ids), 6)
        with self.assertRaises(ValueError):
            select_suite(selected, "measure", 0)

    def test_checkpoint_revalidates_raw_result_and_identity(self):
        suite, row = self.row()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            save_checkpoint(path, "same", row)
            self.assertTrue(read_checkpoint(path, "same", suite, self.targets["elf"])["reuse"]["reused"])
            self.assertIsNone(read_checkpoint(path, "changed", suite, self.targets["elf"]))
            row["unit_result"]["phases"]["warm"]["jobs"][0]["evidence_ids"] = []
            save_checkpoint(path, "same", row)
            self.assertIsNone(read_checkpoint(path, "same", suite, self.targets["elf"]))

    def test_files_apply_updates_and_deletes_without_gold_answers(self):
        suite = self.subset("memory-lifecycle-v1", 2)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            materialize_product_fixtures(suite, root / "input")
            for name in ("files-search", "no-memory"):
                result = run_baseline(name, root / "input", root / name)
                self.assertNotIn("answer", result["phases"]["warm"]["jobs"][0])
                scored = evaluate_unit(suite, result, target_contract(name, [suite["suite_id"]]))
                self.assertEqual(scored["classification"], "completed")
                rows = result["phases"]["warm"]["jobs"]
                self.assertTrue(all(j["operations"] for j in rows))
                if name == "no-memory":
                    self.assertTrue(all(not j["contexts"] for j in rows))
                persisted = " ".join(p.read_text() for p in (root / name).glob("*.json"))
                # Assert the actual operation target, not corpus order.
                op = suite["jobs"][1]["operations"][0]
                deleted_text = next(i["text"] for i in suite["jobs"][1]["corpus"] if i["evidence_id"] == op["evidence_id"])
                self.assertNotIn(deleted_text, persisted)

    def test_expired_budget_does_not_launch_subprocess(self):
        old = runtime.DEADLINE
        runtime.DEADLINE = 0
        try:
            with mock.patch.object(runtime.subprocess, "run") as run:
                with self.assertRaises(TimeoutError):
                    runtime.command(["must-not-run"])
                run.assert_not_called()
            with runtime.cleanup_budget():
                self.assertEqual(runtime.remaining_seconds(90), 90)
            self.assertEqual(runtime.DEADLINE, 0)
        finally:
            runtime.DEADLINE = old

    def test_quick_cli_budget_resume_and_report_without_providers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(mode="quick", manifest=cli.DEFAULT_MANIFEST, suites=None,
                only_target=None, job_limit=None, artifact_root=root / "first", resume=None,
                max_seconds=60, max_units=32, skip_build=False, allow_dirty=False, plan=False)
            source = {"head": "test", "dirty": False}
            with mock.patch.object(cli, "parse_args", return_value=args), \
                 mock.patch.object(cli, "source_fingerprint", return_value=source), \
                 mock.patch.object(cli, "command", return_value=subprocess.CompletedProcess([], 0, "pass")), \
                 mock.patch.object(cli, "provider_preflight") as provider, \
                 mock.patch.object(cli, "build_images") as build:
                self.assertEqual(cli.main(), 0)
                first = args.artifact_root
                provider.assert_not_called()
                build.assert_not_called()
                args.resume = first
                args.artifact_root = root / "resumed"
                with mock.patch.object(cli, "local_row", side_effect=AssertionError("must reuse")):
                    self.assertEqual(cli.main(), 0)
                resumed = json.loads((args.artifact_root / "bundle.json").read_text())
                self.assertEqual(resumed["schema"], "elf.benchmark_bundle/v2")
                self.assertEqual(publish(resumed), (args.artifact_root / "report.md").read_text())
                self.assertNotIn("This complete measured run", publish(resumed))
                self.assertTrue(all(r["reuse"]["reused"] for s in resumed["suite_results"].values() for r in s["results"]))
                args.resume = args.artifact_root
                args.artifact_root = root / "resumed-again"
                with mock.patch.object(cli, "local_row", side_effect=AssertionError("must reuse twice")):
                    self.assertEqual(cli.main(), 0)
                args.resume = None
                args.max_units = 1
                args.artifact_root = root / "limited"
                self.assertEqual(cli.main(), 1)
                limited = json.loads((args.artifact_root / "bundle.json").read_text())
                self.assertFalse(limited["acceptance"]["passed"])
                self.assertIn("timeout_failed", (args.artifact_root / "report.md").read_text())

    def test_elf_build_selects_only_the_dedicated_stage(self):
        elf = self.targets["elf"]
        with mock.patch.object(docker, "build_image", return_value="sha256:elf") as build:
            tags, digests, failures = docker.build_images(self.manifest, [elf], skip_build=False)
        build.assert_called_once_with(elf["image"], elf["dockerfile"], "elf-runtime")
        self.assertEqual(digests, {"elf": "sha256:elf"})
        self.assertFalse(failures)

    def test_cached_elf_image_with_stale_revision_is_rejected(self):
        with mock.patch.object(docker, "image_id", return_value="sha256:old"), \
             mock.patch.object(docker, "command", side_effect=[
                 subprocess.CompletedProcess([], 0, "current"),
                 subprocess.CompletedProcess([], 0, "stale")]):
            _, _, failures = docker.build_images(self.manifest, [self.targets["elf"]], skip_build=True)
        self.assertIn("source differs", failures["elf"])

    def test_command_timeout_terminates_child_group(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            runtime.command(["python3", "-c", "import time; time.sleep(30)"], timeout=0.05)
