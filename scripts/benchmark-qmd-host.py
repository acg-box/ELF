#!/usr/bin/env python3
"""Run the frozen QMD native workflow on host Metal with the shared suite contract."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import time
from pathlib import Path

from benchmark_contract import evaluate_unit, materialize_product_fixtures
from benchmark_contract.review import review_suite
from benchmark_runner.answers import attach_shared_answers
from benchmark_runner.providers import provider_environment
from benchmark_runner.runtime import REPO, source_fingerprint, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--native-only", action="store_true")
    parser.add_argument("--reanswer", type=Path)
    args = parser.parse_args()
    if args.reanswer and args.native_only:
        parser.error("Reanswer requires the shared reader")
    root = args.artifact_root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(args.manifest.read_text())
    models = json.loads(args.models.read_text())
    for entry in models.values():
        if hashlib.sha256(Path(entry["path"]).read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("QMD model differs from its frozen digest")
    os.environ.update(BENCHMARK_NATIVE_ADAPTER=str(args.adapter.resolve()),
        QMD_CHECKOUT=str(args.checkout.resolve()), QMD_MODEL_MANIFEST=str(args.models.resolve()))
    from benchmark_targets.rust import run_rust_target

    target = next(t for t in manifest["targets"] if t["id"] == "qmd")
    contract = json.loads((REPO / manifest["answer_contract"]).read_text())
    provider = None if args.native_only else provider_environment(dict(os.environ), manifest["providers"], inside_container=False)
    bundle = {"schema": "elf.qmd_host_bundle/v1", "source": source_fingerprint(),
        "target": target, "platform": platform.platform(), "models": models,
        "adapter_sha256": hashlib.sha256(args.adapter.read_bytes()).hexdigest(),
        "dependency_lock_sha256": hashlib.sha256((args.checkout / "package-lock.json").read_bytes()).hexdigest(),
        "native_only": args.native_only, "units": []}
    retained = None
    if args.reanswer:
        retained = json.loads((args.reanswer / "bundle.json").read_text())
        if retained["schema"] != bundle["schema"] or len(retained["units"]) != len(manifest["suites"]):
            raise ValueError("Reanswer requires the complete QMD native bundle")
        bundle["retrieval_source"] = retained
        bundle["retrieval_source_sha256"] = hashlib.sha256((args.reanswer / "bundle.json").read_bytes()).hexdigest()
    started = time.monotonic()
    for entry in manifest["suites"]:
        suite = review_suite(json.loads((REPO / entry["path"]).read_text()), contract)
        unit = root / entry["id"]
        materialize_product_fixtures(suite, unit / "input")
        if retained is None:
            raw = run_rust_target("qmd", unit / "input", unit / "artifacts", unit / "state")
        else:
            prior = next(u for u in retained["units"] if u["suite"]["suite_id"] == suite["suite_id"])
            if prior["suite"] != suite:
                raise ValueError("QMD suite changed since native retrieval")
            raw = prior["unit_result"]
        write_json(unit / "native-result.json", raw)
        if provider:
            raw = attach_shared_answers(suite, raw, provider, manifest["runner"]["context_budget_chars"])
        write_json(unit / "unit-result.json", raw)
        evaluation = evaluate_unit(suite, raw, target)
        bundle["units"].append({"suite": suite, "unit_result": raw, "evaluation": evaluation})
        bundle["duration_seconds"] = time.monotonic()-started
        write_json(root / "bundle.json", bundle)
        print(entry["id"], raw["result_class"], flush=True)
    return 0 if all(u["unit_result"]["result_class"] == "completed" for u in bundle["units"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
