"""One benchmark entrypoint: offline quick checks, ELF measurement, and comparison."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from benchmark_report.modes import publish_modes
from benchmark_contract import evaluate_unit, load_json, materialize_product_fixtures, sha256_json, validate_manifest, validate_suite
from . import runtime
from .answers import attach_shared_answers, failure_unit
from .baselines import BASELINES, run_baseline, target_contract
from .checkpoints import read_checkpoint, save_checkpoint
from .docker import build_images
from .execution import acceptance, run_unit
from .profiles import quality_summary, select_suite
from .providers import load_local_env, provider_environment, provider_preflight
from .runtime import REPO, command, source_fingerprint, write_json

DEFAULT_MANIFEST = REPO / "config/benchmark/benchmark-v3.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", action="store_true", help="Print selected targets and coverage without execution")
    parser.add_argument("--mode", choices=("quick", "measure", "compare"), default="quick")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--suite", action="append", dest="suites")
    parser.add_argument("--only-target")
    parser.add_argument("--job-limit", type=int)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--resume", type=Path, help="Reuse successful receipts from a matching prior run")
    parser.add_argument("--max-seconds", type=int, default=1800)
    parser.add_argument("--max-units", type=int, default=32)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    return parser.parse_args()


def local_row(target, suite, root, env, context_budget=12000):
    started = time.monotonic()
    inputs = root / "product-input"
    materialize_product_fixtures(suite, inputs)
    unit = run_baseline(target["id"], inputs, root / "state")
    if env is not None:
        unit = attach_shared_answers(suite, unit, env, context_budget)
    evaluation = evaluate_unit(suite, unit, target)
    replay = evaluate_unit(suite, json.loads(json.dumps(unit)), target)
    return {"target": target["id"], "unit_result": unit, "evaluation": evaluation,
            "duration_seconds": round(time.monotonic() - started, 3),
            "cleanup": {"passed": True, "not_started": True},
            "deterministic_replay": {"passed": evaluation == replay},
            "answer_measurement": "live" if env is not None else "not_measured"}


def failed_row(target, suite, reason):
    unit = failure_unit(target, suite, "timeout_failed", reason)
    return {"target": target["id"], "unit_result": unit,
            "evaluation": evaluate_unit(suite, unit, target),
            "cleanup": {"passed": True, "not_started": True},
            "deterministic_replay": {"passed": True}, "duration_seconds": 0}




def main() -> int:
    args = parse_args()
    if args.max_seconds <= 0 or args.max_units <= 0:
        raise ValueError("budgets must be positive")
    manifest = load_json(args.manifest)
    validate_manifest(manifest)
    known = {t["id"] for t in manifest["targets"]} | set(BASELINES)
    if args.only_target and args.only_target not in known:
        raise ValueError(f"unknown or retired target: {args.only_target}")
    if args.mode == "quick" and args.only_target and args.only_target not in BASELINES:
        raise ValueError("quick mode is offline; select measure or compare for a product")
    selected = args.suites or [s["id"] for s in manifest["suites"]]
    if set(selected) - {s["id"] for s in manifest["suites"]} or len(selected) != len(set(selected)):
        raise ValueError("unknown or duplicate suites")
    suites = {}
    for entry in manifest["suites"]:
        if entry["id"] in selected:
            original = load_json(REPO / entry["path"])
            validate_suite(original)
            suites[entry["id"]] = select_suite(original, args.mode, args.job_limit)
    targets = [target_contract(name, selected) for name in BASELINES]
    if args.mode != "quick":
        targets += [t for t in manifest["targets"] if args.mode == "compare" or t["id"] == "elf"]
    if args.only_target:
        # Explicit measured single-target diagnosis may select any maintained target.
        targets = [t for t in targets + manifest["targets"] if t["id"] == args.only_target][:1]
    targets = [t for t in targets if set(t["suites"]) & set(selected)]
    if not targets:
        raise ValueError("no targets eligible for the selected suites")
    if args.plan:
        print(json.dumps({"mode": args.mode, "targets": [t["id"] for t in targets],
            "coverage": {k: [j["job_id"] for j in v["jobs"]] for k, v in suites.items()},
            "target_pins": {t["id"]: t["pin"] for t in targets},
            "scheduled_units": sum(len(set(t["suites"]) & set(suites)) for t in targets),
            "budget": {"seconds": args.max_seconds, "units": args.max_units}}, indent=2))
        return 0
    source = source_fingerprint()
    if args.mode != "quick" and source["dirty"] and not args.allow_dirty:
        raise ValueError("live measurement requires a clean fixed source commit or --allow-dirty")
    if args.skip_build and source["dirty"] and any(t["id"] == "elf" for t in targets):
        raise ValueError("dirty ELF source cannot be verified against a cached image")
    started = time.monotonic()
    runtime.DEADLINE = started + args.max_seconds
    now = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run_id = hashlib.sha256(f"{now}:{os.getpid()}".encode()).hexdigest()[:10]
    root = args.artifact_root or REPO / "tmp/benchmark-v5" / f"{now}-{run_id}"
    root.mkdir(parents=True, exist_ok=False)
    bundle: dict[str, Any] = {"schema": "elf.benchmark_bundle/v2", "mode": args.mode,
        "run_id": run_id, "source": source, "created_at": now,
        "classification": "incomplete", "suite_results": {}, "timings": {},
        "budget": {"max_seconds": args.max_seconds, "max_units": args.max_units,
                   "boundary": "Whole-run subprocess/HTTP timeouts; cleanup has a separate bounded reserve. Internal product model calls are not a money cap."},
        "coverage": {k: [j["job_id"] for j in s["jobs"]] for k, s in suites.items()},
        "target_pins": {t["id"]: t["pin"] for t in targets},
        "manifest_sha256": sha256_json(manifest),
        "provider_routes": {"chat_model": manifest["providers"]["chat"]["model"],
                            "chat_reasoning_effort": manifest["providers"]["chat"]["reasoning_effort"],
                            "embedding_model": manifest["providers"]["embedding"]["model"],
                            "embedding_dimensions": manifest["providers"]["embedding"]["dimensions"]},
        "target_contracts": {t["id"]: t for t in targets}}
    write_json(root / "bundle.json", bundle)
    images, digests, failures = {}, {}, {}
    host_env = None
    container_env = {}
    try:
        if args.mode == "quick":
            test = command(["cargo", "make", "test"], check=False)
            (root / "contract-tests.log").write_text(test.stdout)
            if test.returncode:
                raise RuntimeError("repository tests failed")
        else:
            local = load_local_env()
            bundle["provider_configuration"] = {
                "EMBEDDING_API_BASE": bool(local.get("EMBEDDING_API_BASE")),
                "EMBEDDING_API_KEY": bool(local.get("EMBEDDING_API_KEY")),
                "LITELLM_BASE_URL_or_COMPAT": bool(local.get("LITELLM_CHAT_COMPAT_BASE_URL") or local.get("LITELLM_BASE_URL")),
                "LITELLM_API_KEY": bool(local.get("LITELLM_API_KEY")),
            }
            write_json(root / "bundle.json", bundle)
            host_env = dict(os.environ)
            host_env.update(provider_environment(local, manifest["providers"], inside_container=False))
            container_env = provider_environment(local, manifest["providers"], inside_container=True)
            preflight = provider_preflight(host_env, root)
            if preflight.get("classification") != "completed":
                raise RuntimeError("provider preflight failed; see provider-preflight.json")
            bundle["provider_preflight"] = preflight
        bundle["timings"]["preflight_seconds"] = round(time.monotonic() - started, 3)
        build_started = time.monotonic()
        live_targets = [t for t in targets if t["id"] not in BASELINES]
        if live_targets:
            images, digests, failures = build_images(manifest, live_targets, skip_build=args.skip_build)
        bundle["timings"]["build_seconds"] = round(time.monotonic() - build_started, 3)
        bundle["target_image_digests"] = digests
        provider_identity = {k: v for k, v in (host_env or {}).items()
                             if k.startswith("BENCHMARK_") and not k.endswith("KEY")}
        identity = sha256_json({"source": source, "manifest": manifest, "suites": suites,
                               "mode": args.mode, "providers": provider_identity, "images": digests})
        attempted = 0
        for suite_id, suite in suites.items():
            eligible = [t for t in targets if suite_id in t["suites"]]
            section = {"suite_sha256": sha256_json(suite), "scheduled_targets": [t["id"] for t in eligible], "results": []}
            bundle["suite_results"][suite_id] = section
            for target in eligible:
                name = target["id"]
                receipt = Path("receipts") / suite_id / f"{name}.json"
                row = read_checkpoint(args.resume / receipt, identity, suite, target) if args.resume else None
                if row is None:
                    if attempted >= args.max_units or time.monotonic() >= runtime.DEADLINE:
                        row = failed_row(target, suite, "run budget exhausted; unit not started")
                    else:
                        attempted += 1
                        unit_root = root / "units" / suite_id / name
                        if name in BASELINES:
                            row = local_row(target, suite, unit_root, host_env, int(manifest["runner"]["context_budget_chars"]))
                        else:
                            row = run_unit(target=target, suite=suite, run_id=run_id,
                                artifact_root=root, compose_file=REPO / manifest["runner"]["compose_file"],
                                container_env=container_env, host_provider_env=host_env,
                                image=images.get(name), build_failure=failures.get(name),
                                timeout_seconds=int(manifest["runner"]["unit_timeout_seconds"]),
                                context_budget=int(manifest["runner"]["context_budget_chars"]))
                save_checkpoint(root / receipt, identity, row)
                section["results"].append(row)
                write_json(root / "bundle.json", bundle)
        bundle["acceptance"] = acceptance(bundle, False)
        bundle["quality"] = quality_summary(bundle)
        bundle["classification"] = "completed" if bundle["acceptance"]["passed"] else "failed"
    except Exception as error:
        # Avoid printing exception text that could contain a provider credential.
        bundle["classification"] = "configuration_or_execution_failed"
        bundle["acceptance"] = {"passed": False, "findings": [f"{type(error).__name__}: run stopped; inspect stage artifacts"]}
    finally:
        runtime.DEADLINE = None
    bundle["timings"]["total_seconds"] = round(time.monotonic() - started, 3)
    write_json(root / "bundle.json", bundle)
    (root / "report.md").write_text(publish_modes(bundle))
    print(root / "report.md")
    return 0 if bundle["acceptance"]["passed"] and bundle.get("quality", {}).get("elf_seeded_invariants_passed", True) else 1
