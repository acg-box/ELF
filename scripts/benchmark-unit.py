#!/usr/bin/env python3
"""Dispatch one isolated benchmark target and persist its unit result."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from benchmark_targets.lightrag import run_lightrag_target
from benchmark_targets.mem0 import run_mem0
from benchmark_targets.pageindex import PageIndexProductFailure, run_pageindex
from benchmark_targets.rust import run_rust_target
from benchmark_targets.unit_runtime import classify_failure, sanitized_error, write_json

ROOT = Path("/benchmark")
INPUT = ROOT / "input"
ARTIFACTS = ROOT / "artifacts"
STATE = ROOT / "state"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        required=True,
        choices=(
            "elf",
            "mem0",
            "qmd",
            "lightrag",
            "openviking",
            "graphiti",
            "graphrag",
            "pageindex",
            "openkb",
            "honcho",
        ),
    )
    return parser.parse_args()


def failure_result(
    target: str,
    classification: str,
    error: BaseException,
    job_ids: list[str] | None = None,
) -> dict[str, Any]:
    score_eligible = target != "pageindex"
    native_mode = {
        "qmd": "lexical",
        "pageindex": "hierarchical_tree_construction",
        "openviking": "native_resource_find",
        "graphiti": "native_temporal_graph_search",
        "graphrag": "native_local_search",
        "openkb": "agent_query_with_native_source_trace",
        "honcho": "native_hybrid_message_search",
    }.get(target, "external_embedding")
    job_ids = job_ids or [path.stem for path in sorted(INPUT.glob("*.json"))]
    phases = {
        phase: {
            "status": classification,
            "jobs": [
                {
                    "job_id": job_id,
                    "classification": classification,
                    "evidence_ids": [],
                    "returned_count": 0,
                    "latency_ms": 0.0,
                    "native_status": "not_run",
                    "failure": sanitized_error(error),
                    "operations": [],
                }
                for job_id in job_ids
            ],
            "adapter_metadata": {"skipped_due_to_failure": True},
        }
        for phase in ("cold", "warm")
    }
    return {
        "schema": "elf.benchmark_unit_result/v4",
        "target": target,
        "native_mode": native_mode,
        "score_eligible": score_eligible,
        "result_class": classification,
        "warm_reused_state": False,
        "ingest_count": 0,
        "failure": {
            "classification": classification,
            "message": sanitized_error(error),
        },
        "phases": phases,
    }


def main() -> int:
    args = parse_args()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    job_ids = [path.stem for path in sorted(INPUT.glob("*.json"))]
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        required: tuple[str, ...] = ()
        if args.target in {
            "elf",
            "mem0",
            "lightrag",
            "openviking",
            "graphiti",
            "graphrag",
            "honcho",
        }:
            required += (
                "EMBEDDING_API_BASE",
                "EMBEDDING_API_KEY",
                "EMBEDDING_MODEL",
                "EMBEDDING_DIMENSIONS",
            )
        if args.target in {
            "mem0",
            "lightrag",
            "graphiti",
            "openkb",
            "honcho",
        }:
            required += (
                "CHAT_API_BASE",
                "CHAT_API_KEY",
                "CHAT_MODEL",
                "CHAT_REASONING_EFFORT",
            )
        missing = [name for name in required if not os.environ.get(name)]
        if missing:
            raise KeyError(f"missing required configuration: {', '.join(missing)}")
        exit_code = 0
        if args.target == "mem0":
            result = run_mem0(INPUT, ARTIFACTS, STATE)
        elif args.target == "openviking":
            from benchmark_targets.openviking import (
                OpenVikingAdapterFailure,
                OpenVikingProductFailure,
                run_openviking,
            )

            try:
                result = run_openviking(INPUT, ARTIFACTS, STATE / "openviking")
            except OpenVikingProductFailure as error:
                result = failure_result(args.target, "product_failed", error, job_ids)
                exit_code = 1
            except OpenVikingAdapterFailure as error:
                result = failure_result(args.target, "adapter_failed", error, job_ids)
                exit_code = 1
        elif args.target == "graphiti":
            from benchmark_targets.graphiti import (
                GraphitiAdapterFailure,
                GraphitiProductFailure,
                run_graphiti,
            )

            try:
                result = run_graphiti(INPUT, ARTIFACTS, STATE / "graphiti")
            except GraphitiProductFailure as error:
                result = failure_result(args.target, "product_failed", error, job_ids)
                exit_code = 1
            except GraphitiAdapterFailure as error:
                result = failure_result(args.target, "adapter_failed", error, job_ids)
                exit_code = 1
        elif args.target == "graphrag":
            from benchmark_targets.graphrag import (
                GraphRAGAdapterFailure,
                GraphRAGProductFailure,
                run_graphrag,
            )

            try:
                result = run_graphrag(INPUT, ARTIFACTS, STATE / "graphrag")
            except GraphRAGProductFailure as error:
                result = failure_result(args.target, "product_failed", error, job_ids)
                exit_code = 1
            except GraphRAGAdapterFailure as error:
                result = failure_result(args.target, "adapter_failed", error, job_ids)
                exit_code = 1
        elif args.target == "pageindex":
            result = run_pageindex(INPUT, ARTIFACTS, STATE / "pageindex")
        elif args.target == "openkb":
            from benchmark_targets.openkb import run_openkb

            result = run_openkb(INPUT, ARTIFACTS, STATE / "openkb")
        elif args.target == "honcho":
            from benchmark_targets.honcho import (
                HonchoAdapterFailure,
                HonchoProductFailure,
                run_honcho,
            )

            try:
                result = run_honcho(INPUT, ARTIFACTS, STATE / "honcho")
            except HonchoProductFailure as error:
                result = failure_result(args.target, "product_failed", error, job_ids)
                exit_code = 1
            except HonchoAdapterFailure as error:
                result = failure_result(args.target, "adapter_failed", error, job_ids)
                exit_code = 1
        elif args.target == "lightrag":
            result = run_lightrag_target(INPUT, ARTIFACTS, STATE)
        else:
            result = run_rust_target(args.target, INPUT, ARTIFACTS, STATE)
    except KeyError as error:
        result = failure_result(args.target, "configuration_failed", error, job_ids)
        exit_code = 2
    except PageIndexProductFailure as error:
        result = failure_result(args.target, "product_failed", error, job_ids)
        exit_code = 1
    except Exception as error:
        classification = classify_failure(sanitized_error(error))
        result = failure_result(args.target, classification, error, job_ids)
        exit_code = 1
    write_json(ARTIFACTS / "unit-result.json", result)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
