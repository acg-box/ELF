"""Host benchmark cli responsibilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import argparse
import copy
import hashlib
import os
import sys
import time

from benchmark_contract import load_json, sha256_json, validate_manifest, validate_suite

from .docker import build_images
from .execution import acceptance, run_matrix
from .providers import load_local_env, provider_environment, provider_preflight
from .runtime import REPO, command, source_fingerprint, write_json


DEFAULT_MANIFEST = REPO / "config/benchmark/benchmark-v3.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--suite", action="append", dest="suites")
    parser.add_argument("--only-target")
    parser.add_argument("--job-limit", type=int)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_json(args.manifest)
    validate_manifest(manifest)
    selected_suite_ids = args.suites or [entry["id"] for entry in manifest["suites"]]
    unknown = set(selected_suite_ids) - {entry["id"] for entry in manifest["suites"]}
    if unknown:
        raise ValueError(f"unknown suites: {sorted(unknown)}")
    full_run = not args.suites and not args.only_target and not args.job_limit
    now = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run_id = hashlib.sha256(f"{now}-{os.getpid()}".encode()).hexdigest()[:10]
    artifact_root = args.artifact_root or REPO / "tmp/benchmark-v4" / f"{now}-{run_id}"
    artifact_root.mkdir(parents=True, exist_ok=False)
    source = source_fingerprint()
    if full_run and source["dirty"] and not args.allow_dirty:
        result = {
            "schema": "elf.benchmark_bundle/v1",
            "classification": "configuration_failed",
            "message": "complete measured run requires a clean fixed source commit",
            "source": source,
        }
        write_json(artifact_root / "bundle.json", result)
        print(artifact_root / "bundle.json")
        return 2
    try:
        local_env = load_local_env()
        host_provider_env = dict(os.environ)
        host_provider_env.update(
            provider_environment(local_env, manifest["providers"], inside_container=False)
        )
        container_provider_env = provider_environment(
            local_env, manifest["providers"], inside_container=True
        )
    except KeyError as error:
        result = {
            "schema": "elf.benchmark_provider_preflight/v1",
            "classification": "configuration_failed",
            "message": str(error),
        }
        write_json(artifact_root / "provider-preflight.json", result)
        print(artifact_root / "provider-preflight.json")
        return 2
    preflight = provider_preflight(host_provider_env, artifact_root)
    if preflight.get("classification") != "completed":
        bundle = {
            "schema": "elf.benchmark_bundle/v1",
            "classification": preflight.get("classification"),
            "source": source,
            "provider_preflight": preflight,
            "suite_results": {},
        }
        write_json(artifact_root / "bundle.json", bundle)
        print(artifact_root / "bundle.json")
        return 2

    entries = {
        entry["id"]: entry for entry in manifest["suites"] if entry["id"] in selected_suite_ids
    }
    suites: dict[str, dict[str, Any]] = {}
    for suite_id, entry in entries.items():
        suite = load_json(REPO / entry["path"])
        validate_suite(suite)
        if args.job_limit:
            if args.job_limit < 1 or args.job_limit > len(suite["jobs"]):
                raise ValueError("job limit is outside the suite")
            suite = copy.deepcopy(suite)
            suite["jobs"] = suite["jobs"][: args.job_limit]
            suite["execution_mode"] = "readiness"
        suites[suite_id] = suite
    selected_targets = [
        target
        for target in manifest["targets"]
        if any(suite_id in target["suites"] for suite_id in selected_suite_ids)
        and (args.only_target is None or target["id"] == args.only_target)
    ]
    if args.only_target and not selected_targets:
        raise ValueError(f"target {args.only_target} is not eligible for selected suites")
    images, image_digests, build_failures = build_images(
        manifest, selected_targets, skip_build=args.skip_build
    )
    docker_version = command(["docker", "version", "--format", "{{.Server.Version}}"]).stdout.strip()
    compose_file = REPO / manifest["runner"]["compose_file"]
    suite_results: dict[str, Any] = {}
    for suite_id, suite in suites.items():
        targets = [
            target
            for target in selected_targets
            if suite_id in target["suites"]
        ]
        rows = run_matrix(
            targets=targets,
            capacity=int(manifest["runner"]["capacity"]),
            suite=suite,
            run_id=run_id,
            artifact_root=artifact_root,
            compose_file=compose_file,
            container_env=container_provider_env,
            host_provider_env=host_provider_env,
            images=images,
            build_failures=build_failures,
            timeout_seconds=int(manifest["runner"]["unit_timeout_seconds"]),
            context_budget=int(manifest["runner"]["context_budget_chars"]),
        )
        suite_results[suite_id] = {
            "suite_sha256": sha256_json(suite),
            "scheduled_targets": [target["id"] for target in targets],
            "results": sorted(rows, key=lambda row: row["target"]),
        }
        write_json(artifact_root / "suites" / suite_id / "summary.json", suite_results[suite_id])
    bundle = {
        "schema": "elf.benchmark_bundle/v1",
        "classification": "completed",
        "mode": "complete_measured_run" if full_run else "readiness_or_regression",
        "run_id": run_id,
        "created_at": now,
        "source": source,
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "provider_routes": {
            "chat_model": manifest["providers"]["chat"]["model"],
            "chat_reasoning_effort": manifest["providers"]["chat"]["reasoning_effort"],
            "embedding_model": manifest["providers"]["embedding"]["model"],
            "embedding_dimensions": manifest["providers"]["embedding"]["dimensions"],
        },
        "provider_preflight": preflight,
        "docker_server_version": docker_version,
        "target_image_tags": images,
        "target_image_digests": image_digests,
        "target_pins": {target["id"]: target["pin"] for target in manifest["targets"]},
        "target_contracts": {
            target["id"]: {
                key: target[key]
                for key in (
                    "adapter",
                    "score_eligible",
                    "suites",
                    "native_deviations",
                    "not_applicable",
                )
                if key in target
            }
            for target in manifest["targets"]
        },
        "build_failures": build_failures,
        "suite_results": suite_results,
    }
    bundle["acceptance"] = acceptance(bundle, full_run)
    bundle_path = artifact_root / "bundle.json"
    write_json(bundle_path, bundle)
    if full_run:
        report_path = artifact_root / "report.en.md"
        report = command(
            [
                sys.executable,
                "scripts/benchmark-report.py",
                "--bundle",
                str(bundle_path),
                "--out",
                str(report_path),
            ],
            check=False,
        )
        (artifact_root / "report.log").write_text(report.stdout, encoding="utf-8")
        if report.returncode:
            print(bundle_path)
            return 1
    print(bundle_path)
    return 0 if bundle["acceptance"]["passed"] else 1

