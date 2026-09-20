"""Check the supported host and packaged-container Python entrypoints."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


class BenchmarkEntrypointTests(unittest.TestCase):
    def test_host_entrypoints_resolve_modules_outside_the_repository_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for script, option in (
                ("benchmark-runner.py", "--manifest"),
                ("benchmark-report.py", "--bundle"),
            ):
                with self.subTest(script=script):
                    result = subprocess.run(
                        [sys.executable, str(REPO / "scripts" / script), "--help"],
                        cwd=directory,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    self.assertIn(option, result.stdout)

    def test_unit_entrypoint_loads_with_only_docker_copy_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy2(REPO / "scripts/benchmark-unit.py", root)
            shutil.copytree(
                REPO / "scripts/benchmark_targets",
                root / "benchmark_targets",
                ignore=shutil.ignore_patterns("__pycache__"),
            )
            result = subprocess.run(
                [sys.executable, str(root / "benchmark-unit.py"), "--help"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("--target", result.stdout)
            self.assertIn("lightrag", result.stdout)
            self.assertIn("mem0", result.stdout)
            query = root / "benchmark_targets/openkb_query.py"
            compile(query.read_text(encoding="utf-8"), str(query), "exec")
