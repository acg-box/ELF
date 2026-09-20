"""Benchmark runner regression contracts."""

from __future__ import annotations

from scripts.tests.benchmark_support import BenchmarkCase, REPO, load_script

from pathlib import Path
import copy
import json
from unittest import mock
from benchmark_contract import opaque_job_id
from benchmark_runner import answers as runner_answers
from benchmark_runner import docker as runner_docker
import subprocess

PREFLIGHT = load_script(
    "benchmark_provider_preflight", "scripts/benchmark-provider-preflight.py"
)


class BenchmarkRunnerTests(BenchmarkCase):
    def test_shared_answer_requires_nonempty_text_and_preserves_raw_response(self) -> None:
        suite = self.subset("common-core-v1")
        case_id = opaque_job_id(suite["jobs"][0]["job_id"])
        unit = self.completed_unit("elf", suite)
        native = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "answers": [
                                    {
                                        "case_id": case_id,
                                        "text": "supported fact",
                                        "supported": True,
                                    }
                                ]
                            }
                        )
                    }
                }
            ],
            "usage": {"total_tokens": 10},
        }
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(native).encode()
        env = {
            "BENCHMARK_CHAT_API_BASE": "https://provider.test/v1",
            "BENCHMARK_CHAT_MODEL": "model",
            "BENCHMARK_CHAT_REASONING_EFFORT": "high",
            "BENCHMARK_CHAT_API_KEY": "protected",
        }
        with mock.patch.object(
            runner_answers.urllib.request, "urlopen", return_value=response
        ) as urlopen:
            attached = runner_answers.attach_shared_answers(suite, unit, env, 12000)
        request_body = json.loads(urlopen.call_args.args[0].data)
        prompt = json.loads(request_body["messages"][0]["content"])
        self.assertIn("must never be empty", prompt["instruction"])
        self.assertEqual(attached["provider_raw"]["shared_answer"], native)
        self.assertEqual(
            attached["phases"]["warm"]["jobs"][0]["answer"]["text"],
            "supported fact",
        )

        invalid_native = copy.deepcopy(native)
        invalid_native["choices"][0]["message"]["content"] = json.dumps(
            {
                "answers": [
                    {"case_id": case_id, "text": "", "supported": True}
                ]
            }
        )
        invalid_response = mock.MagicMock()
        invalid_response.__enter__.return_value.read.return_value = json.dumps(
            invalid_native
        ).encode()
        with mock.patch.object(
            runner_answers.urllib.request, "urlopen", return_value=invalid_response
        ):
            failed = runner_answers.attach_shared_answers(
                suite, self.completed_unit("elf", suite), env, 12000
            )
        self.assertEqual(failed["result_class"], "provider_failed")
        self.assertIn("empty text", failed["failure"]["message"])
        self.assertEqual(failed["provider_raw"]["shared_answer"], invalid_native)


    def test_compose_names_are_isolated_and_bounded(self) -> None:
        names = {
            runner_docker.compose_project_name("run", suite, target)
            for suite in self.suites
            for target in self.targets
        }
        self.assertEqual(len(names), len(self.suites) * len(self.targets))
        self.assertTrue(all(name.startswith("elfb-") and len(name) <= 63 for name in names))


    def test_cleanup_checks_containers_volumes_and_networks(self) -> None:
        responses = [
            subprocess.CompletedProcess([], 0, "down"),
            subprocess.CompletedProcess([], 0, ""),
            subprocess.CompletedProcess([], 0, ""),
            subprocess.CompletedProcess([], 0, ""),
        ]
        with mock.patch.object(runner_docker, "command", side_effect=responses):
            cleanup = runner_docker.cleanup_project("elfb-test", Path("compose.yml"), {})
        self.assertTrue(cleanup["passed"])
        self.assertEqual(cleanup["remaining"], {"containers": [], "volumes": [], "networks": []})


    def test_compose_dependency_logs_are_captured_before_cleanup(self) -> None:
        completed = subprocess.CompletedProcess([], 0, "honcho-api | startup failed\n")
        with mock.patch.object(runner_docker, "command", return_value=completed) as command:
            output = runner_docker.compose_project_logs("elfb-test", Path("compose.yml"), {})
        self.assertIn("startup failed", output)
        self.assertIn("logs", command.call_args.args[0])
        self.assertIn("--timestamps", command.call_args.args[0])


    def test_provider_preflight_paths_are_openai_compatible(self) -> None:
        self.assertEqual(
            PREFLIGHT.endpoint("https://provider.test/v1", "embeddings"),
            "https://provider.test/v1/embeddings",
        )
        self.assertEqual(
            PREFLIGHT.endpoint("https://provider.test", "chat/completions"),
            "https://provider.test/v1/chat/completions",
        )


    def test_canonical_cargo_make_entrypoint_forwards_runner_arguments(self) -> None:
        makefile = (REPO / "makefiles/benchmark-core.toml").read_text(encoding="utf-8")
        benchmark_task = makefile.split("[tasks.benchmark-competitors]", 1)[1].split(
            "[tasks.", 1
        )[0]
        self.assertIn('"${@}"', benchmark_task)


