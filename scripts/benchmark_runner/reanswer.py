"""Recompute shared answers from retained native readback without reingestion."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import time

from benchmark_contract import evaluate_unit, load_json, sha256_json
from benchmark_contract.review import review_suite
from benchmark_report.modes import publish_modes
from . import runtime
from .answers import ANSWER_BATCH_SIZE, attach_shared_answers
from .execution import acceptance
from .profiles import quality_summary, select_suite
from .providers import load_local_env, provider_environment
from .runtime import REPO, source_fingerprint, write_json


def run(args) -> int:
    score_only = bool(getattr(args, "rescore", None))
    if score_only and args.reanswer:
        raise ValueError("select either --rescore or --reanswer")
    source_root = args.rescore if score_only else args.reanswer
    action = "rescore" if score_only else "reanswer"
    if args.artifact_root is None:
        raise ValueError("rescore/reanswer requires a new --artifact-root")
    source = load_json(source_root / "bundle.json")
    manifest = load_json(args.manifest)
    contract = load_json(REPO / manifest["answer_contract"]) if manifest.get("answer_contract") else None
    routes = source["provider_routes"]
    chat = manifest["providers"]["chat"]
    if not score_only and (routes["chat_model"], routes["chat_reasoning_effort"]) != (
            chat["model"], chat["reasoning_effort"]):
        raise ValueError("reanswer must retain the original model and reasoning level")
    if args.only_target or args.suites or args.job_limit or args.resume:
        raise ValueError("reanswer processes the complete retained bundle without selection")
    args.artifact_root.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    if not score_only:
        env.update(provider_environment(load_local_env(), manifest["providers"], inside_container=False))
    bundle = copy.deepcopy(source)
    bundle["retrieval_source"] = source["source"]
    bundle["source"] = source_fingerprint()
    bundle["answer_contract"] = contract
    bundle[action] = {
        "source_bundle_sha256": hashlib.sha256((source_root / "bundle.json").read_bytes()).hexdigest(),
        "provider_calls": "none" if score_only else "recomputed",
        "batch_size": None if score_only else ANSWER_BATCH_SIZE,
        "native_state_reused": True,
        "native_result_sha256": {},
    }
    bundle["created_at"] = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    started = time.monotonic()
    runtime.DEADLINE = started + args.max_seconds
    try:
        for suite_id, section in bundle["suite_results"].items():
            suite_entry = next(item for item in manifest["suites"] if item["id"] == suite_id)
            suite = load_json(REPO / suite_entry["path"])
            suite = select_suite(suite, "compare", None)
            previous_suite = review_suite(suite, source.get("answer_contract"))
            if sha256_json(previous_suite) != section["suite_sha256"]:
                raise ValueError("retained suite hash differs from current evaluator")
            if [job["job_id"] for job in suite["jobs"]] != source["coverage"][suite_id]:
                raise ValueError("reanswer requires the complete unchanged suite")
            suite = review_suite(suite, contract)
            section["suite_sha256"] = sha256_json(suite)
            for row in section["results"]:
                name = row["target"]
                native_path = source_root / "units" / suite_id / name / "artifacts/unit-result.json"
                if score_only:
                    native = copy.deepcopy(row["unit_result"])
                    digest = sha256_json(native)
                elif native_path.is_file():
                    native = load_json(native_path)
                    digest = hashlib.sha256(native_path.read_bytes()).hexdigest()
                else:
                    native = copy.deepcopy(row["unit_result"].get("native_retrieval", row["unit_result"]))
                    digest = hashlib.sha256(json.dumps(native, sort_keys=True).encode()).hexdigest()
                bundle[action]["native_result_sha256"][f"{suite_id}/{name}"] = digest
                if not score_only:
                    for key in ("provider_raw", "provider_usage", "answer_protocol"):
                        native.pop(key, None)
                    for phase in native.get("phases", {}).values():
                        for job in phase["jobs"]:
                            job.pop("answer", None)
                    row["unit_result"] = attach_shared_answers(suite, native, env,
                        int(manifest["runner"]["context_budget_chars"]))
                row["evaluation"] = evaluate_unit(suite, row["unit_result"],
                    source["target_contracts"][name])
                replay = evaluate_unit(suite, copy.deepcopy(row["unit_result"]),
                    source["target_contracts"][name])
                row["deterministic_replay"] = {"passed": replay == row["evaluation"]}
                write_json(args.artifact_root / "bundle.json", bundle)
        bundle["acceptance"] = acceptance(bundle, False)
        bundle["quality"] = quality_summary(bundle)
        bundle["classification"] = "completed" if bundle["acceptance"]["passed"] else "failed"
    finally:
        runtime.DEADLINE = None
    bundle[action]["seconds"] = round(time.monotonic() - started, 3)
    write_json(args.artifact_root / "bundle.json", bundle)
    (args.artifact_root / "report.md").write_text(publish_modes(bundle))
    print(args.artifact_root / "report.md")
    return 0 if (bundle["acceptance"]["passed"]
                 and bundle["quality"].get("elf_seeded_invariants_passed", True)) else 1
