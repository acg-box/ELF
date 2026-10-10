#!/usr/bin/env python3
"""Execute and score shared-store capability workloads with retained failure evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path

from benchmark_deep.fixtures import WORKLOAD_GROUPS, workload
from benchmark_deep.resume import prepare_sag_resume
from benchmark_deep.hindsight_resume import prepare_hindsight_resume
from benchmark_deep.drivers import ACTION_TIMEOUT_SECONDS, INGEST_TIMEOUT_SECONDS
from benchmark_runner.answers import ANSWER_BATCH_SIZE, request_answers
from benchmark_deep.scoring import score_answer
from benchmark_runner.baselines import BASELINES, target_contract
from benchmark_runner.docker import TARGET_IMAGE_ENV, cleanup_project, compose_project_logs, image_id
from benchmark_runner.providers import provider_environment
from benchmark_runner.runtime import REPO, command, source_fingerprint, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, choices=("elf", "qmd", "ragflow", "hindsight", "gbrain", "mem0", "sag-engine", *BASELINES))
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--max-seconds", type=int, default=7200)
    parser.add_argument("--ingest-seconds", type=int, default=INGEST_TIMEOUT_SECONDS,
                        help="Per-ingest deadline, including index readiness; default 5400")
    parser.add_argument("--workload-group", choices=('all', *WORKLOAD_GROUPS),
                        help="Run a fixed group in fresh native state; default is all groups")
    parser.add_argument("--qmd-host", action="store_true")
    parser.add_argument("--native-only", action="store_true")
    parser.add_argument("--reanswer", type=Path)
    parser.add_argument("--resume-sag", type=Path, help="Continue a retained failed SAG scale-1000 ingest in copied state")
    parser.add_argument("--resume-hindsight", type=Path, help="Continue a retained Hindsight checkpoint after a failed scale-1000 run")
    args = parser.parse_args()
    if args.resume_hindsight and (args.target != "hindsight" or args.workload_group != "scale-1000" or args.reanswer or args.resume_sag):
        parser.error("--resume-hindsight requires Hindsight scale-1000 and cannot combine with other recovery modes")
    if args.resume_sag and (args.target != "sag-engine" or args.workload_group != "scale-1000" or args.reanswer):
        parser.error("--resume-sag requires SAG scale-1000 and cannot combine with --reanswer")
    if args.ingest_seconds <= 0:
        parser.error('--ingest-seconds must be positive')
    if args.qmd_host and args.target != "qmd":
        parser.error("--qmd-host requires --target qmd")
    if args.reanswer and args.native_only:
        parser.error("Reanswer requires the shared reader")
    manifest = json.loads(args.manifest.read_text())
    target = (target_contract(args.target, []) if args.target in BASELINES
              else next(t for t in manifest["targets"] if t["id"] == args.target))
    host_execution = args.qmd_host or args.target in BASELINES
    root = args.artifact_root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    retained = None
    workload_group = args.workload_group or 'all'
    if args.reanswer:
        retained = json.loads((args.reanswer / "bundle.json").read_text())
        workload_group = retained.get('workload_group', 'all')
        if args.workload_group is not None and args.workload_group != workload_group:
            raise ValueError('Reanswer must preserve the retained workload group')
        inputs = json.loads((args.reanswer / "input/workload.json").read_text())
        oracle = json.loads((args.reanswer / "oracle.json").read_text())
        if retained["target"]["id"] != args.target or retained["providers"] != manifest["providers"]:
            raise ValueError("Reanswer must preserve target and providers")
        if hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest() != retained["workload_sha256"]:
            raise ValueError("Retained deep workload changed")
        if (inputs, oracle) != workload(workload_group):
            raise ValueError("Reanswer requires the unchanged versioned workload and oracle")
    else:
        inputs, oracle = workload(workload_group)
    write_json(root / "input/workload.json", inputs)
    write_json(root / "oracle.json", oracle)
    image = target.get("image", manifest["runner"]["image"])
    digest = retained["image_digest"] if retained else (None if host_execution else image_id(image))
    source = source_fingerprint()
    project = "elfdeep-" + hashlib.sha256(str(root).encode()).hexdigest()[:12]
    provider = {} if args.native_only else provider_environment(dict(os.environ), manifest["providers"], inside_container=not args.qmd_host)
    env = {**os.environ, **provider,
        "BENCHMARK_IMAGE": image,
        **({TARGET_IMAGE_ENV[args.target]: image} if args.target in TARGET_IMAGE_ENV else {}),
        "BENCHMARK_INPUT_HOST": str(root / "input"), "BENCHMARK_ARTIFACT_HOST": str(root / "artifacts"),
        "BENCHMARK_DEEP_INGEST_TIMEOUT_SECONDS": str(args.ingest_seconds),
        "BENCHMARK_POSTGRES_PASSWORD": hashlib.sha256(project.encode()).hexdigest()[:24]}
    (root / "artifacts").mkdir()
    continuation = (prepare_sag_resume(args.resume_sag, root, inputs, oracle, manifest["providers"], digest)
                    if args.resume_sag else None)
    hindsight_override = None
    if args.resume_hindsight:
        continuation, hindsight_override = prepare_hindsight_resume(
            args.resume_hindsight, root, inputs, oracle, manifest["providers"], digest, REPO / "scripts")
    compose = REPO / manifest["runner"]["compose_file"]
    prefix = ["docker", "compose", "--project-name", project, "--file", str(compose)]
    if hindsight_override:
        prefix.extend(["--file", str(hindsight_override)])
    started = time.monotonic()
    execution_error = None
    try:
        invocation = [*prefix, "run", "--rm", "--no-TTY",
            "--env", f"BENCHMARK_DEEP_INGEST_TIMEOUT_SECONDS={args.ingest_seconds}",
            "--volume", f"{REPO / 'scripts'}:/opt/deep:ro",
            f"{args.target}-unit", "python3", "/opt/deep/benchmark-deep-unit.py",
            "--target", args.target]
        if host_execution:
            for name in (("BENCHMARK_NATIVE_ADAPTER", "QMD_CHECKOUT", "QMD_MODEL_MANIFEST") if args.qmd_host else ()):
                if not env.get(name):
                    raise ValueError(f"Host QMD requires {name}")
            env["BENCHMARK_DEEP_ROOT"] = str(root)
            invocation = [sys.executable, str(REPO / "scripts/benchmark-deep-unit.py"), "--target", args.target]
        if retained:
            exit_code = retained["exit_code"]
            execution_error = retained["execution_error"]
        else:
            result = command(invocation, env=env, check=False, timeout=args.max_seconds)
            (root / "execution.log").write_text(result.stdout)
            exit_code = result.returncode
    except Exception as error:
        execution_error = f"{type(error).__name__}: {error}"
        exit_code = None
    finally:
        if retained:
            cleanup = retained["cleanup"]
        elif host_execution:
            cleanup = {"passed": True, "mode": "host_processes_exited; retained isolated artifact state"}
        else:
            (root / "dependencies.log").write_text(compose_project_logs(project, compose, env))
            cleanup = cleanup_project(project, compose, env)
        write_json(root / "cleanup.json", cleanup)
    raw_path = root / "artifacts/deep-result.json"
    native = retained["native"] if retained else (json.loads(raw_path.read_text()) if raw_path.exists() else {"results": []})
    by_id = {r["case_id"]: r for r in native["results"] if r.get("case_id")}
    host = None if args.native_only else provider_environment(dict(os.environ), manifest["providers"], inside_container=False)
    queries = [a for a in inputs["actions"] if a["action"] == "query"]
    answers, responses = {}, []
    answer_errors = []
    available = []
    for query in queries:
        row = by_id.get(query["case_id"], {})
        if row.get("status") == "completed":
            context = "\n".join(c["text"] for c in row.get("contexts", []))[:12000]
            available.append({"case_id": query["case_id"], "question": query["question"], "context": [context]})
    for offset in range(0, 0 if args.native_only else len(available), ANSWER_BATCH_SIZE):
        batch = available[offset:offset+ANSWER_BATCH_SIZE]
        try:
            response = request_answers(batch, host)
            responses.append(response)
            write_json(root / "answer-responses.json", responses)
            choice = response["choices"][0]
            if choice.get("finish_reason") == "length":
                raise ValueError("Shared reader exceeded its output limit")
            decoded = json.loads(choice["message"]["content"])["answers"]
            if len(decoded) != len(batch) or {a["case_id"] for a in decoded} != {a["case_id"] for a in batch}:
                raise ValueError("Shared reader changed case identities")
            for answer in decoded:
                if not isinstance(answer.get("supported"), bool) or not isinstance(answer.get("text"), str):
                    raise ValueError("Shared reader returned an invalid answer")
            answers.update({a["case_id"]: a for a in decoded})
        except Exception as error:
            answer_errors.append({"cases": [a["case_id"] for a in batch], "failure": str(error)})
    scores = []
    for case_id, expected in oracle.items():
        row, answer = by_id.get(case_id, {}), answers.get(case_id)
        contexts = row.get("contexts", [])
        supplied_context = "\n".join(c["text"] for c in contexts)[:12000]
        context = supplied_context.casefold()
        correctness = score_answer(expected, answer, supplied_context)
        scores.append({"case_id": case_id, "lane": expected["lane"],
            "execution": row.get("status", "not_run"), "answer": answer, **correctness,
            "required_evidence_found": all(e in {c.get("evidence_id") for c in contexts} for e in expected["evidence"]),
            "forbidden_context_hits": [f for f in expected["forbidden"] if f.casefold() in context],
            "duration_seconds": row.get("duration_seconds")})
    bundle = {"schema": "elf.deep_bundle/v2", "target": target, "image_digest": digest,
        "workload_group": workload_group,
        "answer_protocol": {"revision": "isolated_case_v1", "batch_size": ANSWER_BATCH_SIZE,
                            "grounding": "Expected factual values must occur in the case's supplied context."},
        "providers": manifest["providers"], "source": source,
        "execution_limits": (retained.get("execution_limits", {"status": "not_recorded_in_original_bundle"})
            if retained else {"native_total_seconds": args.max_seconds,
                              "ingest_action_seconds": args.ingest_seconds,
                              "other_action_seconds": ACTION_TIMEOUT_SECONDS}),
        "runtime": {"host_execution": host_execution, "host_qmd": args.qmd_host, "platform": platform.platform(), "native_only": args.native_only},
        "workload_sha256": hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest(),
        "oracle_sha256": hashlib.sha256(json.dumps(oracle,sort_keys=True).encode()).hexdigest(),
        "native": native, "scores": scores, "cleanup": cleanup, "exit_code": exit_code,
        "execution_error": execution_error, "answer_errors": answer_errors,
        "duration_seconds": time.monotonic()-started,
        "coverage": {"planned_queries": len(scores), "native_completed": sum(s["execution"]=="completed" for s in scores),
                     "answered": sum(s["answer"] is not None for s in scores), "correct": sum(s["correct"] is True for s in scores)}}
    if continuation:
        bundle["continuation"] = continuation
        bundle["combined_attempt_duration_seconds"] = continuation["original_duration_seconds"] + bundle["duration_seconds"]
    if retained:
        bundle["retrieval_source"] = retained["source"]
        bundle["retrieval_runtime"] = retained["runtime"]
        bundle["retrieval_bundle_sha256"] = hashlib.sha256((args.reanswer / "bundle.json").read_bytes()).hexdigest()
    write_json(root / "bundle.json", bundle)
    print(json.dumps(bundle["coverage"]))
    passed = (all(s["execution"] == "completed" for s in scores) if args.native_only
              else all(s["correct"] is True for s in scores))
    return 0 if cleanup["passed"] and passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
