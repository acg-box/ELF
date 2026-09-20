"""Host benchmark execution responsibilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import concurrent.futures
import copy
import hashlib
import os
import random
import subprocess
import time

from benchmark_contract import (
    evaluate_unit,
    load_json,
    materialize_product_fixtures,
    sha256_json,
)

from .answers import attach_shared_answers, failure_unit
from .docker import (
    TARGET_IMAGE_ENV,
    cleanup_project,
    compose_project_logs,
    compose_project_name,
    project_images,
)
from .runtime import command, write_json


def run_unit(
    *,
    target: dict[str, Any],
    suite: dict[str, Any],
    run_id: str,
    artifact_root: Path,
    compose_file: Path,
    container_env: dict[str, str],
    host_provider_env: dict[str, str],
    image: str | None,
    build_failure: str | None,
    timeout_seconds: int,
    context_budget: int,
) -> dict[str, Any]:
    target_id = target["id"]
    unit_root = artifact_root / "units" / suite["suite_id"] / target_id
    input_root = unit_root / "product-input"
    artifact_dir = unit_root / "artifacts"
    materialize_product_fixtures(suite, input_root)
    input_hash = hashlib.sha256(
        b"".join(path.read_bytes() for path in sorted(input_root.glob("*.json")))
    ).hexdigest()
    if build_failure or image is None:
        raw_unit = failure_unit(
            target, suite, "configuration_failed", build_failure or "image unavailable"
        )
        write_json(artifact_dir / "unit-result.json", raw_unit)
        evaluation = evaluate_unit(suite, raw_unit, target)
        return {
            "target": target_id,
            "project": None,
            "compose_exit_code": None,
            "duration_seconds": 0.0,
            "input_sha256": input_hash,
            "unit_result": raw_unit,
            "evaluation": evaluation,
            "deterministic_replay": {"passed": True, "sha256": sha256_json(evaluation)},
            "cleanup": {"passed": True, "not_started": True},
            "runtime_images": [],
        }

    project = compose_project_name(run_id, suite["suite_id"], target_id)
    env = dict(os.environ)
    env.update(container_env)
    env.update(
        {
            "BENCHMARK_IMAGE": image,
            "BENCHMARK_INPUT_HOST": str(input_root.resolve()),
            "BENCHMARK_ARTIFACT_HOST": str(artifact_dir.resolve()),
            "BENCHMARK_POSTGRES_PASSWORD": hashlib.sha256(project.encode()).hexdigest()[:24],
        }
    )
    image_env = TARGET_IMAGE_ENV.get(target_id)
    if image_env:
        env[image_env] = image
    started = time.monotonic()
    timed_out = False
    harness_error: str | None = None
    try:
        completed = command(
            [
                "docker",
                "compose",
                "--project-name",
                project,
                "--file",
                str(compose_file),
                "run",
                "--rm",
                "--no-TTY",
                f"{target_id}-unit",
            ],
            env=env,
            check=False,
            timeout=timeout_seconds,
        )
        compose_output = completed.stdout
        compose_exit = completed.returncode
    except subprocess.TimeoutExpired as error:
        timed_out = True
        timed_output = error.stdout or ""
        if isinstance(timed_output, bytes):
            timed_output = timed_output.decode(errors="replace")
        compose_output = timed_output + "\nunit timed out\n"
        compose_exit = 124
    except Exception as error:
        harness_error = f"Compose unit invocation failed: {type(error).__name__}: {error}"
        compose_output = harness_error + "\n"
        compose_exit = 125
    unit_root.mkdir(parents=True, exist_ok=True)
    runtime_images = project_images(project, compose_file, env)
    dependency_logs = compose_project_logs(project, compose_file, env)
    (unit_root / "compose.log").write_text(
        compose_output
        + "\n--- Compose dependency logs captured before cleanup ---\n"
        + dependency_logs,
        encoding="utf-8",
    )
    cleanup = cleanup_project(project, compose_file, env)
    result_path = artifact_dir / "unit-result.json"
    if timed_out:
        raw_unit = failure_unit(target, suite, "timeout_failed", "isolated unit timed out")
    elif harness_error:
        raw_unit = failure_unit(target, suite, "harness_failed", harness_error)
    elif not result_path.is_file():
        raw_unit = failure_unit(
            target, suite, "harness_failed", "unit did not write unit-result.json"
        )
    else:
        try:
            raw_unit = load_json(result_path)
        except Exception as error:
            raw_unit = failure_unit(
                target,
                suite,
                "adapter_failed",
                f"unit result is not valid JSON: {type(error).__name__}: {error}",
            )
    if not cleanup["passed"]:
        raw_unit = failure_unit(
            target, suite, "cleanup_failed", "Compose project cleanup was incomplete"
        )
    raw_unit = attach_shared_answers(
        suite, raw_unit, host_provider_env, context_budget
    )
    write_json(unit_root / "raw-unit-result.json", raw_unit)
    try:
        evaluation = evaluate_unit(suite, raw_unit, target)
    except Exception as error:
        raw_unit = failure_unit(
            target,
            suite,
            "adapter_failed",
            f"unit result violates the normalized contract: {type(error).__name__}: {error}",
        )
        evaluation = evaluate_unit(suite, raw_unit, target)
    replay = evaluate_unit(suite, copy.deepcopy(raw_unit), target)
    write_json(unit_root / "normalized-result.json", evaluation)
    return {
        "target": target_id,
        "project": project,
        "compose_exit_code": compose_exit,
        "duration_seconds": round(time.monotonic() - started, 3),
        "input_sha256": input_hash,
        "unit_result": raw_unit,
        "evaluation": evaluation,
        "deterministic_replay": {
            "passed": sha256_json(evaluation) == sha256_json(replay),
            "sha256": sha256_json(evaluation),
        },
        "cleanup": cleanup,
        "runtime_images": runtime_images,
    }


def run_matrix(
    *,
    targets: list[dict[str, Any]],
    capacity: int,
    suite: dict[str, Any],
    run_id: str,
    artifact_root: Path,
    compose_file: Path,
    container_env: dict[str, str],
    host_provider_env: dict[str, str],
    images: dict[str, str],
    build_failures: dict[str, str],
    timeout_seconds: int,
    context_budget: int,
) -> list[dict[str, Any]]:
    shuffled = list(targets)
    random.Random(f"{run_id}:{suite['suite_id']}").shuffle(shuffled)
    kwargs = [
        {
            "target": target,
            "suite": suite,
            "run_id": run_id,
            "artifact_root": artifact_root,
            "compose_file": compose_file,
            "container_env": container_env,
            "host_provider_env": host_provider_env,
            "image": images.get(target["id"]),
            "build_failure": build_failures.get(target["id"]),
            "timeout_seconds": timeout_seconds,
            "context_budget": context_budget,
        }
        for target in shuffled
    ]
    if capacity == 1:
        return [run_unit(**item) for item in kwargs]
    with concurrent.futures.ThreadPoolExecutor(max_workers=capacity) as pool:
        futures = [pool.submit(run_unit, **item) for item in kwargs]
        return [future.result() for future in futures]


def acceptance(bundle: dict[str, Any], full_run: bool) -> dict[str, Any]:
    if not full_run:
        return {"passed": True, "mode": "readiness_or_regression", "findings": []}
    findings: list[str] = []
    suites = bundle["suite_results"]
    common = suites["common-core-v1"]["results"]
    common_completed = [
        row["target"]
        for row in common
        if row["evaluation"]["classification"] == "completed"
        and row["evaluation"]["phases"]["warm"]["quality_denominator"]
    ]
    if "elf" not in common_completed:
        findings.append("ELF did not complete common-core")
    if len([target for target in common_completed if target != "elf"]) < 4:
        findings.append("fewer than four non-ELF common-core products completed")
    for suite_id in (
        "memory-lifecycle-v1",
        "knowledge-structure-v1",
        "repository-knowledge-v1",
    ):
        completed = [
            row["target"]
            for row in suites[suite_id]["results"]
            if row["evaluation"]["classification"] == "completed"
        ]
        if len(completed) < 2:
            findings.append(f"{suite_id} has fewer than two completed products")
    for suite in suites.values():
        for row in suite["results"]:
            if not row["cleanup"]["passed"]:
                findings.append(f"{row['target']} cleanup failed")
            if not row["deterministic_replay"]["passed"]:
                findings.append(f"{row['target']} deterministic replay failed")
    return {"passed": not findings, "mode": "complete_measured_run", "findings": findings}

