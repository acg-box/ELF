"""Benchmark lightrag regression contracts."""

from __future__ import annotations

from scripts.tests.benchmark_support import BenchmarkCase

from benchmark_targets import lightrag as LIGHTRAG
from pathlib import Path
import json
from unittest import mock
import tempfile


class BenchmarkLightragTests(BenchmarkCase):
    def test_lightrag_pairs_cold_and_warm_inside_each_isolated_job(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_dir = root / "input"
            input_dir.mkdir()
            for index in range(2):
                job = {
                    "job_id": f"j_{index}",
                    "suite": "knowledge_structure",
                    "prompt": {"content": f"question {index}"},
                    "corpus": {
                        "items": [
                            {"evidence_id": f"e_{index}", "text": f"source {index}"}
                        ]
                    },
                    "operations": [],
                }
                (input_dir / f"j_{index}.json").write_text(
                    json.dumps(job), encoding="utf-8"
                )

            calls: list[list[str]] = []

            def fake_run(command, log_path, env):
                calls.append(command)
                fixture_dir = Path(command[command.index("--fixtures") + 1])
                job = json.loads(next(fixture_dir.glob("*.json")).read_text(encoding="utf-8"))
                warm_phase = "--reuse-index" in command
                evidence_path = Path(command[command.index("--evidence-out") + 1])
                evidence_path.parent.mkdir(parents=True, exist_ok=True)
                evidence_path.write_text(
                    json.dumps(
                        {
                            "metadata": {"index_reused": warm_phase},
                            "jobs": [
                                {
                                    "job_id": job["job_id"],
                                    "status": "completed",
                                    "evidence_ids": [job["corpus"]["items"][0]["evidence_id"]],
                                    "returned_count": 1,
                                    "latency_ms": 5.0,
                                    "contexts": [
                                        {
                                            "evidence_id": job["corpus"]["items"][0]["evidence_id"],
                                            "text": job["corpus"]["items"][0]["text"],
                                        }
                                    ],
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_path.write_text("ok\n", encoding="utf-8")
                return 10.0

            with (
                mock.patch.object(LIGHTRAG, "ADAPTER", Path("/adapter")),
                mock.patch.object(LIGHTRAG, "wait_port"),
                mock.patch.object(LIGHTRAG, "run_command", side_effect=fake_run),
            ):
                result = LIGHTRAG.run_lightrag_target(input_dir, root / "artifacts", root / "state")

        self.assertEqual(result["result_class"], "completed")
        self.assertTrue(result["warm_reused_state"])
        self.assertEqual(["--reset-index" in call for call in calls], [True, False, True, False])
        self.assertEqual(["--reuse-index" in call for call in calls], [False, True, False, True])
        self.assertEqual(
            [call[call.index("--query-mode") + 1] for call in calls],
            ["mix", "mix", "mix", "mix"],
        )
        self.assertEqual(
            result["phases"]["cold"]["adapter_metadata"]["job_isolation"],
            "native_document_clear_before_each_cold_job",
        )
        self.assertEqual(
            result["phases"]["cold"]["adapter_metadata"]["query_modes"],
            ["mix"],
        )


    def test_lightrag_query_modes_are_locked_to_suite_kind(self) -> None:
        self.assertEqual(LIGHTRAG.lightrag_query_mode({"suite": "retrieval"}), "naive")
        self.assertEqual(
            LIGHTRAG.lightrag_query_mode({"suite": "knowledge_structure"}), "mix"
        )
        with self.assertRaisesRegex(RuntimeError, "unsupported LightRAG benchmark suite"):
            LIGHTRAG.lightrag_query_mode({"suite": "repository_knowledge"})


