"""Benchmark openkb regression contracts."""

from __future__ import annotations

from scripts.tests.benchmark_support import BenchmarkCase, REPO, load_script

from pathlib import Path
from unittest import mock
import subprocess
import tempfile

OPENKB = load_script("benchmark_openkb", "scripts/benchmark_targets/openkb.py")


class BenchmarkOpenkbTests(BenchmarkCase):
    def test_openkb_scale_timeouts_and_native_trace_contexts_are_bounded(self) -> None:
        jobs = [{"corpus": {"items": [{} for _ in range(74)]}}]
        self.assertEqual(
            OPENKB._bounded_timeouts(jobs, 1200),
            {"init": 300, "ingest": 2220, "query": 180, "mutation": 600},
        )
        capped = [{"corpus": {"items": [{} for _ in range(200)]}}]
        self.assertEqual(OPENKB._bounded_timeouts(capped, 1200)["ingest"], 2700)

        with tempfile.TemporaryDirectory() as directory:
            wiki = Path(directory)
            page = wiki / "sources" / "native.json"
            page.parent.mkdir(parents=True)
            page.write_text('{"content":"native replacement"}\n', encoding="utf-8")
            contexts = OPENKB._native_contexts_from_trace(
                [
                    {
                        "wiki_path": "summaries/failed-native-read",
                        "evidence_ids": [],
                    },
                    {
                        "wiki_path": "sources/native.json",
                        "evidence_ids": ["e_native"],
                    }
                ],
                wiki,
            )
            with self.assertRaises(OPENKB.OpenKBAdapterFailure):
                OPENKB._native_contexts_from_trace(
                    [
                        {
                            "wiki_path": "sources/missing.json",
                            "evidence_ids": ["e_missing"],
                        }
                    ],
                    wiki,
                )
        self.assertEqual(
            contexts,
            [
                {
                    "evidence_id": "e_native",
                    "text": '{"content":"native replacement"}\n',
                }
            ],
        )


    def test_openkb_requires_exact_registry_and_removed_document_absence(self) -> None:
        with self.assertRaises(OPENKB.OpenKBProductFailure):
            OPENKB._native_document_map(
                {
                    "active": {"doc_name": "active"},
                    "stale": {"doc_name": "stale"},
                },
                {"active": "e_active"},
            )

        with tempfile.TemporaryDirectory() as directory:
            kb = Path(directory)
            registry = kb / ".openkb" / "hashes.json"
            registry.parent.mkdir(parents=True)
            registry.write_text("{}\n", encoding="utf-8")
            stale = kb / "wiki" / "summaries" / "removed.md"
            stale.parent.mkdir(parents=True)
            stale.write_text("stale\n", encoding="utf-8")
            with self.assertRaises(OPENKB.OpenKBProductFailure):
                OPENKB._assert_native_document_absent(kb, "old-hash", "removed")
            stale.unlink()
            readback = OPENKB._assert_native_document_absent(
                kb, "old-hash", "removed"
            )
        self.assertTrue(readback["file_hash_absent"])
        self.assertTrue(readback["doc_name_absent"])


    def test_openkb_timeout_preserves_bytes_and_product_failure(self) -> None:
        timeout = subprocess.TimeoutExpired(
            ["openkb"], 1, output=b"partial stdout\n", stderr=b"partial stderr\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stdout_path = root / "stdout.log"
            stderr_path = root / "stderr.log"
            with mock.patch.object(OPENKB.subprocess, "run", side_effect=timeout):
                with self.assertRaisesRegex(
                    OPENKB.OpenKBProductFailure, "native operation timed out"
                ):
                    OPENKB._run_native(
                        ["openkb"],
                        cwd=root,
                        env={},
                        stdout_path=stdout_path,
                        stderr_path=stderr_path,
                        timeout=1,
                    )
            self.assertEqual(stdout_path.read_text(encoding="utf-8"), "partial stdout\n")
            self.assertEqual(stderr_path.read_text(encoding="utf-8"), "partial stderr\n")


    def test_openkb_native_command_can_skip_its_interactive_key_prompt(self) -> None:
        completed = subprocess.CompletedProcess(["openkb"], 0, "ready\n", "")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(OPENKB.subprocess, "run", return_value=completed) as run:
                stdout, _ = OPENKB._run_native(
                    ["openkb"],
                    cwd=root,
                    env={"LLM_API_KEY": "protected"},
                    stdout_path=root / "stdout.log",
                    stderr_path=root / "stderr.log",
                    timeout=1,
                    stdin_text="\n",
                )
        self.assertEqual(stdout, "ready\n")
        self.assertEqual(run.call_args.kwargs["input"], "\n")


    def test_openkb_uses_explicit_litellm_transport_and_job_scoped_sources(self) -> None:
        self.assertEqual(OPENKB._litellm_model("gpt-5.6-luna"), "openai/gpt-5.6-luna")
        self.assertEqual(
            OPENKB._litellm_model("anthropic/claude-example"),
            "anthropic/claude-example",
        )
        jobs = [
            {
                "job_id": "j_first",
                "corpus": {"items": [{"evidence_id": "e_shared", "text": "old"}]},
            },
            {
                "job_id": "j_second",
                "corpus": {"items": [{"evidence_id": "e_shared", "text": "new"}]},
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hashes = OPENKB._materialize_sources(jobs, root / "sources")
            config = root / "kb" / ".openkb" / "config.yaml"
            config.parent.mkdir(parents=True)
            config.write_text("model: openai/gpt-5.6-luna\n", encoding="utf-8")
            OPENKB._configure_litellm_api_base(root / "kb", "http://proxy.test/v1")
            rendered = config.read_text(encoding="utf-8")
            source_names = sorted(path.name for path in (root / "sources").glob("*.md"))
        self.assertEqual(len(hashes), 2)
        self.assertEqual(len(source_names), 2)
        self.assertTrue(all(name.startswith("source-") for name in source_names))
        self.assertIn("litellm:", rendered)
        self.assertIn('api_base: "http://proxy.test/v1"', rendered)
        self.assertIn("OpenAIChatCompletionsModel", (REPO / "scripts/benchmark_targets/openkb_query.py").read_text(encoding="utf-8"))
        self.assertIn('model=os.environ["CHAT_MODEL"]', (REPO / "scripts/benchmark_targets/openkb_query.py").read_text(encoding="utf-8"))
        self.assertNotIn("LitellmModel(", (REPO / "scripts/benchmark_targets/openkb_query.py").read_text(encoding="utf-8"))


    def test_openkb_failure_detail_is_bounded_and_redacts_injected_secrets(self) -> None:
        detail = OPENKB._bounded_failure_detail(
            "",
            "provider rejected secret-value " + ("x" * 5000),
            {"CHAT_API_KEY": "secret-value"},
        )
        self.assertNotIn("secret-value", detail)
        self.assertIn("<redacted>", detail)
        self.assertIn("[truncated; inspect the preserved native log]", detail)


