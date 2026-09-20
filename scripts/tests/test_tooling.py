"""Regression checks for explicit integration prerequisites."""

import os
import subprocess
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
