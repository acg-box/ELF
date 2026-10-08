"""LightRAG native HTTP indexing, retrieval, replacement and deletion."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from pathlib import Path

from .unit_runtime import classify_failure, combined_status, sanitized_error, wait_port, write_json

LIGHTRAG_QUERY_MODES = {"retrieval": "naive", "knowledge_structure": "mix",
                       "memory_lifecycle": "naive", "repository_knowledge": "mix"}


def lightrag_query_mode(job):
    return LIGHTRAG_QUERY_MODES[job["suite"]]


def request(method, path, value=None):
    req = urllib.request.Request(os.environ.get("LIGHTRAG_URL", "http://lightrag:9621") + path,
        data=None if value is None else json.dumps(value).encode(),
        headers={"Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=300) as response:
        return json.load(response)


def drain():
    deadline = time.monotonic() + 600
    while True:
        status = request("GET", "/documents/pipeline_status")
        if not any(status.get(k) for k in ("busy", "scanning", "pending_enqueues")):
            return status
        if time.monotonic() >= deadline:
            raise TimeoutError("LightRAG native pipeline did not drain within 600 seconds")
        time.sleep(1)


def documents():
    rows, page = [], 1
    while True:
        native = request("POST", "/documents/paginated", {"page": page, "page_size": 200})
        rows.extend(native["documents"])
        if not native["pagination"]["has_next"]:
            return rows
        page += 1


def ingest(items):
    native = request("POST", "/documents/texts", {
        "texts": [item["text"] for item in items],
        "file_sources": [item["evidence_id"] + ".md" for item in items],
        "chunking": {"strategy": "fixed_token", "params": {
            "chunk_token_size": 320, "chunk_overlap_token_size": 32}}})
    deadline = time.monotonic() + 600
    while True:
        status = request("GET", "/documents/track_status/" + native["track_id"])
        docs = status["documents"]
        terminal = {"processed", "failed"}
        if len(docs) == len(items) and all(str(d["status"]).lower() in terminal for d in docs):
            drain()
            if any(str(d["status"]).lower() == "failed" for d in docs):
                raise RuntimeError("LightRAG native indexing failed: " + json.dumps(docs))
            return {Path(d["file_path"]).stem: d["id"] for d in docs}, status
        if time.monotonic() >= deadline:
            raise TimeoutError("LightRAG native indexing exceeded 600 seconds")
        time.sleep(1)


def native_contexts(native, identities):
    rows = []
    for ref in native.get("references") or []:
        source = Path(ref.get("file_path") or "").stem
        evidence_id = source if source in identities else None
        content = ref.get("content") or []
        if isinstance(content, str):
            content = [content]
        for text in content:
            if text:
                rows.append({"evidence_id": evidence_id, "text": text})
    return rows


def query(job, identities, operations):
    started = time.monotonic()
    words = list(dict.fromkeys(re.findall(r"[A-Za-z0-9_-]+", job["prompt"]["content"])))[:12]
    native = request("POST", "/query", {"query": job["prompt"]["content"],
        "mode": lightrag_query_mode(job), "only_need_context": True,
        "include_references": True, "include_chunk_content": True, "enable_rerank": False,
        "top_k": 5, "chunk_top_k": 5, "hl_keywords": words, "ll_keywords": words, "stream": False})
    contexts = native_contexts(native, identities)
    return {"job_id": job["job_id"], "classification": "completed",
        "evidence_ids": list(dict.fromkeys(c["evidence_id"] for c in contexts if c["evidence_id"])),
        "contexts": contexts, "returned_count": len(contexts),
        "latency_ms": (time.monotonic()-started)*1000, "operations": operations,
        "native_status": "completed", "failure": None}, native


def run_lightrag_target(input_dir: Path, artifacts: Path, state_root: Path):
    del state_root
    wait_port("lightrag", 9621)
    phases = {p: {"status": "completed", "jobs": []} for p in ("cold", "warm")}
    receipts, ingest_ms = [], 0.0
    for path in sorted(input_dir.glob("*.json")):
        job = json.loads(path.read_text())
        receipt = {"job_id": job["job_id"]}
        receipts.append(receipt)
        phase = "cold"
        try:
            drain()
            receipt["clear"] = request("DELETE", "/documents")
            if receipt["clear"].get("status") != "success":
                raise RuntimeError("LightRAG native document clear failed")
            started = time.monotonic()
            identities, receipt["ingest"] = ingest(job["corpus"]["items"])
            ingest_ms += (time.monotonic()-started)*1000
            row, receipt["cold"] = query(job, identities, [])
            phases["cold"]["jobs"].append(row)
            phase, operations = "warm", []
            receipt["operations"] = []
            for op in job.get("operations", []):
                old_id = identities.pop(op["evidence_id"])
                deleted = request("DELETE", "/documents/delete_document", {
                    "doc_ids": [old_id], "delete_file": False, "delete_llm_cache": False})
                if deleted.get("status") != "deletion_started":
                    raise RuntimeError("LightRAG native deletion did not start")
                drain()
                readback = documents()
                if any(d["id"] == old_id for d in readback):
                    raise RuntimeError("LightRAG deleted document remains in native document list")
                replacement = None
                if op["type"] == "update":
                    new_ids, replacement = ingest([op])
                    identities.update(new_ids)
                operations.append({"requested_type": op["type"],
                    "native_type": "delete_then_insert" if replacement else "delete",
                    "classification": "completed", "native_success": True})
                receipt["operations"].append({"operation": op, "delete": deleted,
                    "readback": readback, "replacement": replacement})
            known_sources = {item["evidence_id"] for item in job["corpus"]["items"]}
            row, receipt["warm"] = query(job, known_sources, operations)
            phases["warm"]["jobs"].append(row)
        except Exception as error:
            message = sanitized_error(error)
            classification = classify_failure(message)
            receipt["failure"] = message
            for p in (("cold", "warm") if phase == "cold" else ("warm",)):
                phases[p]["status"] = classification
                phases[p]["jobs"].append({"job_id": job["job_id"],
                    "classification": classification, "evidence_ids": [], "contexts": [],
                    "returned_count": 0, "latency_ms": 0, "operations": [],
                    "native_status": "failed" if p == phase else "not_run", "failure": message})
        write_json(artifacts / "raw/lightrag-http-receipts.json", receipts)
    result_class = combined_status(phases)
    return {"schema": "elf.benchmark_unit_result/v4", "target": "lightrag",
        "native_mode": "native_http_context_and_document_mutations", "score_eligible": True,
        "result_class": result_class, "warm_reused_state": result_class == "completed",
        "ingest_count": 1, "ingest_duration_ms": ingest_ms, "phases": phases}
