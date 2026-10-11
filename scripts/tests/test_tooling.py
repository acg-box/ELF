"""Regression checks for repository tooling and published evidence."""

import json
import os
import subprocess
import sys
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TASKS = tomllib.loads((ROOT / "makefiles/test.toml").read_text())["tasks"]


class IntegrationPrerequisites(unittest.TestCase):
    def run_guard(self, values):
        env = {
            key: value for key, value in os.environ.items()
            if key not in {"ELF_PG_DSN", "ELF_QDRANT_GRPC_URL", "ELF_QDRANT_URL"}
        }
        env.update(values)
        return subprocess.run(
            ["cargo", "make", "check-integration-env"], cwd=ROOT, env=env,
            capture_output=True, text=True, check=False,
        )

    def test_explicit_integration_modes_require_the_guard(self):
        for name in ("test-rust-all", "test-rust-integration"):
            self.assertIn("check-integration-env", TASKS[name]["dependencies"])

    def test_missing_or_blank_configuration_fails_without_disclosing_values(self):
        for values in (
            {},
            {"ELF_PG_DSN": "postgres://private-value"},
            {"ELF_PG_DSN": " ", "ELF_QDRANT_GRPC_URL": "http://private-value"},
            {"ELF_PG_DSN": "postgres://private-value", "ELF_QDRANT_GRPC_URL": "\t"},
        ):
            with self.subTest(values=list(values)):
                result = self.run_guard(values)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("private-value", result.stdout + result.stderr)

    def test_primary_and_legacy_qdrant_names_are_accepted(self):
        for name in ("ELF_QDRANT_GRPC_URL", "ELF_QDRANT_URL"):
            result = self.run_guard({"ELF_PG_DSN": "postgres://unused", name: "http://unused"})
            self.assertEqual(result.returncode, 0, result.stderr)


class RetrievalEvidencePackage(unittest.TestCase):
    def test_published_manifest_files_are_tracked_and_verifiable(self):
        for bundle in ["2026-10-10-retrieval-laboratory", "2026-10-11-memory-consistency-4096"]:
            with self.subTest(bundle=bundle):
                relative = Path("config/benchmark/evidence") / bundle
                manifest = json.loads((ROOT / relative / "manifest.json").read_text())
                tracked = set(subprocess.check_output(
                    ["git", "ls-files", "--", str(relative)], cwd=ROOT, text=True,
                ).splitlines())
                for name in ["manifest.json", *manifest]:
                    self.assertIn(str(relative / name), tracked, "Evidence file must be committed")
                result = subprocess.run(
                    [sys.executable, str(ROOT / relative / "verify.py")], cwd=ROOT,
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
