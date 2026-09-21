"""Scoring-blind local baselines over persisted files, without external services."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from benchmark_contract import assert_product_payload_is_blind, load_json
from .runtime import write_json

BASELINES = ("no-memory", "files-search")


def target_contract(name: str, suites: list[str]) -> dict[str, Any]:
    return {"id": name, "adapter": name, "suites": suites, "score_eligible": True,
            "pin": {"kind": "benchmark_source_commit"}}


def terms(text: str) -> set[str]:
    return set(re.findall(r"[\w]+", text.casefold()))


def retrieve(items: list[dict[str, Any]], query: str, name: str) -> list[dict[str, Any]]:
    if name == "no-memory":
        return []
    query_terms = terms(query)
    ranked = [(len(query_terms & terms(item["text"])), item) for item in items]
    ranked.sort(key=lambda pair: (-pair[0], pair[1]["evidence_id"]))
    return [item for score, item in ranked[:5] if score > 0]


def run_baseline(name: str, inputs: Path, state: Path) -> dict[str, Any]:
    if name not in BASELINES:
        raise ValueError("unknown baseline")
    ingest_ms = 0.0
    phases: dict[str, Any] = {p: {"status": "completed", "jobs": []} for p in ("cold", "warm")}
    for path in sorted(inputs.glob("*.json")):
        job = load_json(path)
        assert_product_payload_is_blind(job)
        store = state / (job["job_id"] + ".json")
        items = {item["evidence_id"]: item for item in job["corpus"]["items"]}
        ingest_started = time.monotonic()
        write_json(store, items)
        ingest_ms += (time.monotonic() - ingest_started) * 1000
        for phase in ("cold", "warm"):
            operations = []
            items = json.loads(store.read_text())
            if phase == "warm":
                for operation in job.get("operations", []):
                    key = operation["evidence_id"]
                    if operation["type"] == "delete":
                        items.pop(key, None)
                    elif operation["type"] == "update":
                        items[key] = {"evidence_id": key, "text": operation["text"]}
                    else:
                        raise ValueError("unsupported file operation")
                    operations.append({"requested_type": operation["type"],
                        "native_type": operation["type"], "classification": "completed",
                        "native_success": True})
                write_json(store, items)
                items = json.loads(store.read_text())
            query_started = time.monotonic()
            contexts = retrieve(list(items.values()), job["prompt"]["content"], name)
            phases[phase]["jobs"].append({"job_id": job["job_id"], "classification": "completed",
                "evidence_ids": [item["evidence_id"] for item in contexts],
                "contexts": contexts, "returned_count": len(contexts),
                "latency_ms": (time.monotonic() - query_started) * 1000,
                "operations": operations})
    return {"schema": "elf.benchmark_unit_result/v4", "target": name,
        "native_mode": name, "score_eligible": True, "result_class": "completed",
        "ingest_count": 1, "warm_reused_state": True,
        "ingest_duration_ms": ingest_ms, "phases": phases,
        "baseline_boundary": "Lexical token-overlap file search; no native host memory, agent actions, or ACL enforcement."}
