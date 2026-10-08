"""MemOS product API: native extraction, cube-scoped recall, and source replacement."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .unit_runtime import write_json


def request(path, value=None):
    base = os.environ.get("MEMOS_URL", "http://memos:8000")
    req = urllib.request.Request(base + path,
        data=None if value is None else json.dumps(value).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as response:
        return json.load(response)


def ready():
    deadline = time.monotonic() + 180
    while True:
        try:
            request("/health")
            return
        except (urllib.error.URLError, OSError):
            if time.monotonic() >= deadline:
                raise TimeoutError("MemOS native API did not become ready within 180 seconds")
            time.sleep(1)


def add(scope, item):
    native = request("/product/add", {"user_id": scope, "writable_cube_ids": [scope],
        "async_mode": "sync", "mode": "fine",
        "messages": [{"role": "user", "content": item["text"]}],
        "info": {"evidence_id": item["evidence_id"]}})
    if native.get("code") not in (0, 200):
        raise RuntimeError("MemOS native add did not succeed")
    return native


def recall(job, scope, operations):
    started = time.monotonic()
    native = request("/product/search", {"user_id": scope, "readable_cube_ids": [scope],
        "query": job["prompt"]["content"], "top_k": 5, "mode": "fine"})
    hits = [hit for bucket in native["data"].get("text_mem", []) for hit in bucket.get("memories", [])][:5]
    contexts = []
    for hit in hits:
        metadata = hit.get("metadata") or {}
        evidence_id = metadata.get("evidence_id") or (metadata.get("info") or {}).get("evidence_id")
        contexts.append({"evidence_id": evidence_id, "text": hit["memory"]})
    return {"job_id": job["job_id"], "classification": "completed",
        "evidence_ids": list(dict.fromkeys(c["evidence_id"] for c in contexts if c["evidence_id"])),
        "contexts": contexts, "returned_count": len(contexts),
        "latency_ms": (time.monotonic()-started)*1000, "native_status": "completed",
        "failure": None, "operations": operations}, native


def source_readback(scope, evidence_id):
    native = request("/product/get_memory", {"mem_cube_id": scope, "user_id": scope,
        "filter": {"evidence_id": evidence_id}})
    rows = [memory for buckets in native["data"].values() for bucket in buckets
            for memory in bucket.get("memories", [])]
    return rows, native


def run_memos(inputs: Path, artifacts: Path, state: Path):
    del state
    ready()
    phases = {phase: {"status": "completed", "jobs": []} for phase in ("cold", "warm")}
    receipts = []
    ingest_ms = 0.0
    for path in sorted(inputs.glob("*.json")):
        job = json.loads(path.read_text())
        scope = job["job_id"]
        receipt = {"job_id": scope, "ingest": [], "operations": []}
        receipts.append(receipt)
        started = time.monotonic()
        for item in job["corpus"]["items"]:
            receipt["ingest"].append(add(scope, item))
            write_json(artifacts / "raw/memos-receipts.json", receipts)
        ingest_ms += (time.monotonic()-started)*1000
        cold, receipt["cold"] = recall(job, scope, [])
        phases["cold"]["jobs"].append(cold)
        operations = []
        for op in job.get("operations", []):
            before, before_raw = source_readback(scope, op["evidence_id"])
            memory_ids = list(dict.fromkeys(memory["id"] for memory in before))
            deleted = (request("/product/delete_memory", {"writable_cube_ids": [scope],
                "memory_ids": memory_ids}) if memory_ids else
                {"code": None, "data": {"status": "not_attempted"},
                 "adapter_reason": "Native source readback returned no memory IDs"})
            after, after_raw = source_readback(scope, op["evidence_id"])
            replacement = add(scope, op) if op["type"] == "update" else None
            success = (deleted.get("code") in (0, 200)
                       and deleted.get("data", {}).get("status") == "success"
                       and bool(before) and not after)
            operations.append({"requested_type": op["type"],
                "native_type": "delete_then_add" if replacement else "delete",
                "native_delete_api": "delete_memory_by_ids",
                "classification": "completed", "native_success": success})
            receipt["operations"].append({"operation": op, "deleted": deleted,
                "before": before_raw, "after": after_raw, "replacement": replacement})
        warm, receipt["warm"] = recall(job, scope, operations)
        phases["warm"]["jobs"].append(warm)
        write_json(artifacts / "raw/memos-receipts.json", receipts)
    return {"schema": "elf.benchmark_unit_result/v4", "target": "memos",
        "native_mode": "native_fine_extract_recall", "score_eligible": True,
        "result_class": "completed", "warm_reused_state": True, "ingest_count": 1,
        "ingest_duration_ms": ingest_ms, "phases": phases}
