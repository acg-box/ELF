"""Hindsight's native bank, retain, recall, and document mutation workflow."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .unit_runtime import write_json


def request(method, path, value=None):
    base = os.environ.get("HINDSIGHT_URL", "http://hindsight:8888")
    req = urllib.request.Request(base + path,
        data=None if value is None else json.dumps(value).encode(),
        headers={"Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=300) as response:
        return json.load(response)


def ready():
    deadline = time.monotonic() + 180
    while True:
        try:
            request("GET", "/health")
            return
        except (urllib.error.URLError, OSError):
            if time.monotonic() >= deadline:
                raise TimeoutError("Hindsight API startup exceeded 180 seconds")
            time.sleep(1)


def drain(bank, *, timeout_seconds=180):
    deadline = time.monotonic() + timeout_seconds
    while True:
        states = {status: request("GET", bank + "/operations?status=" + status + "&limit=1")
                  for status in ("pending", "processing", "failed", "cancelled")}
        if states["failed"]["operations"] or states["cancelled"]["operations"]:
            raise RuntimeError("Hindsight native background operation failed")
        if not any(states[s]["operations"] for s in ("pending", "processing")):
            return states
        if time.monotonic() >= deadline:
            raise TimeoutError("Hindsight native background queue did not drain")
        time.sleep(1)


def contexts_from_native(native, *, limit=5):
    """Keep derived observations separate from the native facts that support them."""
    rows, seen_facts = [], set()
    source_facts = native.get("source_facts") or {}

    def add_fact(fact):
        key = (fact.get("document_id"), fact["text"])
        if key not in seen_facts:
            seen_facts.add(key)
            rows.append({"evidence_id": fact.get("document_id"), "text": fact["text"]})

    for hit in native["results"] if limit is None else native["results"][:limit]:
        if hit.get("document_id"):
            add_fact(hit)
            continue
        parents = [source_facts[fact_id] for fact_id in hit.get("source_fact_ids") or []
                   if fact_id in source_facts and source_facts[fact_id].get("document_id")]
        rows.append({"evidence_id": None, "text": "Derived observation: " + hit["text"],
                     "source_evidence_ids": list(dict.fromkeys(p["document_id"] for p in parents))})
        for parent in parents:
            add_fact(parent)
    return rows


def recall(job, bank, operations):
    started = time.monotonic()
    native = request("POST", bank + "/memories/recall", {
        "query": job["prompt"]["content"], "budget": "mid", "max_tokens": 4096,
        "trace": True,
        "include": {"source_facts": {"max_tokens": 8192}},
    })
    rows = contexts_from_native(native)
    return {
        "job_id": job["job_id"], "classification": "completed",
        "evidence_ids": list(dict.fromkeys(r["evidence_id"] for r in rows if r["evidence_id"])),
        "contexts": rows, "returned_count": len(rows),
        "latency_ms": (time.monotonic() - started) * 1000,
        "operations": operations, "native_status": "completed", "failure": None,
    }, native


def run_hindsight(inputs: Path, artifacts: Path, state: Path):
    del state
    ready()
    phases = {phase: {"status": "completed", "jobs": []} for phase in ("cold", "warm")}
    receipts = []
    ingest_ms = 0.0
    for path in sorted(inputs.glob("*.json")):
        job = json.loads(path.read_text())
        bank = "/v1/default/banks/" + job["job_id"]
        request("PUT", bank, {})
        started = time.monotonic()
        retained = request("POST", bank + "/memories", {"async": False, "items": [
            {"content": item["text"], "document_id": item["evidence_id"]}
            for item in job["corpus"]["items"]]})
        if retained.get("success") is not True:
            raise RuntimeError("Hindsight native retain did not succeed")
        cold_ready = drain(bank)
        ingest_ms += (time.monotonic() - started) * 1000
        cold, cold_raw = recall(job, bank, [])
        phases["cold"]["jobs"].append(cold)
        operations = []
        changes = []
        for op in job.get("operations", []):
            doc = bank + "/documents/" + op["evidence_id"]
            if op["type"] == "update":
                native = request("POST", bank + "/memories", {"async": False, "items": [{
                    "content": op["text"], "document_id": op["evidence_id"], "update_mode": "replace"}]})
                readback = request("GET", doc)
                success = readback.get("original_text") == op["text"]
            else:
                native = request("DELETE", doc)
                try:
                    readback = request("GET", doc)
                    success = False
                except urllib.error.HTTPError as error:
                    if error.code != 404:
                        raise
                    readback = {"http_status": 404}
                    success = native.get("success") is True
            operations.append({"requested_type": op["type"], "native_type": op["type"],
                "classification": "completed", "native_success": success})
            changes.append({"operation": op, "native": native, "readback": readback})
        warm_ready = drain(bank)
        warm, warm_raw = recall(job, bank, operations)
        phases["warm"]["jobs"].append(warm)
        receipts.append({"job_id": job["job_id"], "retain": retained, "changes": changes,
            "cold": cold_raw, "warm": warm_raw, "cold_readiness": cold_ready, "warm_readiness": warm_ready})
        write_json(artifacts / "raw/hindsight-receipts.json", receipts)
    return {"schema": "elf.benchmark_unit_result/v4", "target": "hindsight",
        "native_mode": "native_retain_recall_after_consolidation", "score_eligible": True,
        "result_class": "completed", "warm_reused_state": True, "ingest_count": 1,
        "ingest_duration_ms": ingest_ms, "phases": phases}
