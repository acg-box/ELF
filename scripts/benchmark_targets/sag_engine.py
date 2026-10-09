"""Current SAG engine: native ingestion, extraction, graph search and mutations."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.metadata
import json
import os
import time
import uuid
from pathlib import Path

from .unit_runtime import write_json


def configuration(state):
    from zleap.sag import EngineConfig
    from zleap.sag.config import EmbeddingConfig, LLMConfig

    return EngineConfig(storage_mode="normal", data_dir=str(state), language="en",
        llm=LLMConfig(api_key=os.environ["CHAT_API_KEY"],
            base_url=os.environ["CHAT_API_BASE"], model=os.environ["CHAT_MODEL"],
            max_tokens=8192, max_retries=1, timeout=90, structured_output_mode="json_object"),
        embedding=EmbeddingConfig(model=os.environ["EMBEDDING_MODEL"],
            base_url=os.environ["EMBEDDING_API_BASE"], api_key=os.environ["EMBEDDING_API_KEY"],
            schema_dimensions=int(os.environ["EMBEDDING_DIMENSIONS"]),
            request_dimensions=int(os.environ["EMBEDDING_DIMENSIONS"])))


async def ingest(engine, scope, item):
    from zleap.sag.pipeline import SourceDescriptor, IndexOptions, ExtractionOptions

    chunks = await engine.ingest(item["text"], descriptor=SourceDescriptor(
        data_source_id=scope, source_type="text", source_id=item["evidence_id"]),
        index_options=IndexOptions(replace_policy="replace_current"))
    events = await engine.extract(chunks, ExtractionOptions(max_retries=1))
    return {"chunks": chunks.model_dump(mode="json"), "events": events.model_dump(mode="json")}


async def search(engine, scope, job, operations):
    from zleap.sag.pipeline import SearchRequest, SearchScope, SearchOptions

    started = time.monotonic()
    native = await engine.search(SearchRequest(query=job["prompt"]["content"],
        scope=SearchScope(data_source_ids=(scope,)),
        options=SearchOptions(strategy="full_expand", top_k=5, return_type="chunk")))
    hits = native.chunks[:5]
    return {"job_id": job["job_id"], "classification": "completed",
        "evidence_ids": list(dict.fromkeys(hit.source_id for hit in hits)),
        "contexts": [{"evidence_id": hit.source_id, "text": hit.content} for hit in hits],
        "returned_count": len(hits), "latency_ms": (time.monotonic() - started) * 1000,
        "operations": operations, "native_status": "completed", "failure": None}, native.model_dump(mode="json")


async def delete_source(engine, scope, item, fence_token):
    from zleap.sag.operations import DeleteSourceRequest, OperationContext

    operation_id = str(uuid.uuid4())
    payload = {"data_source_id": scope, "source_id": item["evidence_id"]}
    result = await engine.delete_source(DeleteSourceRequest(**payload,
        context=OperationContext(operation_id=operation_id, idempotency_key=operation_id,
            request_digest=hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
            fence_scope=scope, fence_token=fence_token, owner_id="elf-benchmark")))
    return result.model_dump(mode="json")


async def run(inputs: Path, artifacts: Path, state: Path):
    from zleap.sag import DataEngine

    version = importlib.metadata.version("zleap-sag")
    if version != "0.13.0":
        raise ValueError("SAG package differs from the frozen comparison version")
    phases = {phase: {"status": "completed", "jobs": []} for phase in ("cold", "warm")}
    receipts = []
    ingest_ms = 0.0
    for path in sorted(inputs.glob("*.json")):
        job = json.loads(path.read_text())
        scope = hashlib.sha256(job["job_id"].encode()).hexdigest()[:32]
        receipt = {"job_id": job["job_id"], "scope": scope, "ingest": [], "operations": []}
        receipts.append(receipt)
        async with DataEngine(configuration(state / scope), data_source_id=scope) as engine:
            started = time.monotonic()
            for item in job["corpus"]["items"]:
                receipt["ingest"].append(await ingest(engine, scope, item))
                write_json(artifacts / "raw/sag-engine-receipts.json", receipts)
            ingest_ms += (time.monotonic() - started) * 1000
            cold, receipt["cold"] = await search(engine, scope, job, [])
            phases["cold"]["jobs"].append(cold)
            operations = []
            for operation_index, op in enumerate(job.get("operations", [])):
                if op["type"] == "update":
                    native = await ingest(engine, scope, op)
                    success = not native["chunks"].get("failed_items") and not native["events"].get("failed_items")
                else:
                    native = await delete_source(engine, scope, op, operation_index + 1)
                    success = native["status"] == "succeeded"
                operations.append({"requested_type": op["type"], "native_type": op["type"],
                    "classification": "completed", "native_success": success})
                receipt["operations"].append({"operation": op, "native": native})
                write_json(artifacts / "raw/sag-engine-receipts.json", receipts)
            warm, receipt["warm"] = await search(engine, scope, job, operations)
            phases["warm"]["jobs"].append(warm)
            write_json(artifacts / "raw/sag-engine-receipts.json", receipts)
    return {"schema": "elf.benchmark_unit_result/v4", "target": "sag-engine",
        "native_mode": "native_extract_full_expand", "score_eligible": True,
        "result_class": "completed", "warm_reused_state": True, "ingest_count": 1,
        "ingest_duration_ms": ingest_ms, "phases": phases, "package_version": version}


def run_sag_engine(inputs, artifacts, state):
    return asyncio.run(run(inputs, artifacts, state))
