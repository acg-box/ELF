"""Mem0 owns native memory identities, mutations, and cold/warm receipts."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .unit_runtime import combined_status, wait_port, write_json

def mem0_entries(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        for key in ("results", "memories"):
            rows = value.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    return []


def mapped_evidence(entries: list[dict[str, Any]]) -> list[str]:
    output: list[str] = []
    for entry in entries:
        metadata = entry.get("metadata")
        evidence_id = metadata.get("evidence_id") if isinstance(metadata, dict) else None
        if isinstance(evidence_id, str) and evidence_id not in output:
            output.append(evidence_id)
    return output


def mem0_contexts(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for entry in entries:
        text = entry.get("memory")
        if not isinstance(text, str):
            continue
        metadata = entry.get("metadata")
        evidence_id = metadata.get("evidence_id") if isinstance(metadata, dict) else None
        output.append({"evidence_id": evidence_id, "text": text})
    return output


def created_memory_ids(value: Any) -> list[str]:
    output: list[str] = []
    for entry in mem0_entries(value):
        memory_id = entry.get("id") or entry.get("memory_id")
        if isinstance(memory_id, str) and memory_id not in output:
            output.append(memory_id)
    return output


def mem0_config(job_dir: Path, collection: str) -> dict[str, Any]:
    return {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": collection,
                "host": "qdrant",
                "port": 6333,
                "embedding_model_dims": 4096,
            },
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": os.environ["EMBEDDING_MODEL"],
                "embedding_dims": int(os.environ["EMBEDDING_DIMENSIONS"]),
                "api_key": os.environ["EMBEDDING_API_KEY"],
                "openai_base_url": os.environ["EMBEDDING_API_BASE"],
            },
        },
        "llm": {
            "provider": "openai",
            "config": {
                "model": os.environ["CHAT_MODEL"],
                "api_key": os.environ["CHAT_API_KEY"],
                "openai_base_url": os.environ["CHAT_API_BASE"],
                "max_tokens": 4096,
            },
        },
        "history_db_path": str(job_dir / "history.db"),
        "version": "v1.1",
    }


def run_mem0(input_dir: Path, artifacts: Path, state_root: Path) -> dict[str, Any]:
    os.environ.setdefault("MEM0_TELEMETRY", "false")
    wait_port("qdrant", 6333)
    from mem0 import Memory

    loaded = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(input_dir.glob("*.json"))]
    phases: dict[str, Any] = {}
    cold_ingest_duration_ms = 0.0
    for phase in ("cold", "warm"):
        rows = []
        raw_rows = []
        for job in loaded:
            job_dir = state_root / "mem0" / job["job_id"]
            job_dir.mkdir(parents=True, exist_ok=True)
            receipt = job_dir / "cold-ingest-complete"
            if phase == "warm" and not receipt.is_file():
                raise RuntimeError(f"warm mem0 state is missing for {job['job_id']}")
            memory = Memory.from_config(
                mem0_config(job_dir, f"elf-proof-{job['job_id']}")
            )
            user_id = f"elf-proof-{job['job_id']}"
            adds = []
            operation_results = []
            if phase == "cold":
                ingest_started = time.monotonic()
                memory_ids: dict[str, str] = {}
                for item in job["corpus"]["items"]:
                    add_result = memory.add(
                        item["text"],
                        user_id=user_id,
                        metadata={"evidence_id": item["evidence_id"]},
                        infer=False,
                    )
                    adds.append(add_result)
                    ids = created_memory_ids(add_result)
                    if not ids:
                        raise RuntimeError(
                            f"mem0 add returned no memory id for {item['evidence_id']}"
                        )
                    memory_ids[item["evidence_id"]] = ids[0]
                cold_ingest_duration_ms += (
                    time.monotonic() - ingest_started
                ) * 1000.0
                write_json(receipt, {"memory_ids": memory_ids})
            else:
                receipt_value = json.loads(receipt.read_text(encoding="utf-8"))
                memory_ids = receipt_value.get("memory_ids") or {}
                for operation in job.get("operations") or []:
                    memory_id = memory_ids.get(operation["evidence_id"])
                    if not isinstance(memory_id, str):
                        raise RuntimeError(
                            f"mem0 operation has no native id for {operation['evidence_id']}"
                        )
                    if operation["type"] == "update":
                        native = memory.update(
                            memory_id,
                            operation["text"],
                            metadata={"evidence_id": operation["evidence_id"]},
                        )
                        native_type = "update"
                    elif operation["type"] == "delete":
                        native = memory.delete(memory_id)
                        native_type = "delete"
                    else:
                        raise RuntimeError(
                            f"unsupported mem0 operation {operation['type']}"
                        )
                    operation_results.append(
                        {
                            "requested_type": operation["type"],
                            "native_type": native_type,
                            "classification": "completed",
                            "native_success": True,
                            "native_result": native,
                        }
                    )
            started = time.monotonic()
            search = memory.search(
                job["prompt"]["content"],
                filters={"user_id": user_id},
                top_k=5,
                threshold=0.0,
            )
            latency_ms = (time.monotonic() - started) * 1000.0
            entries = mem0_entries(search)
            evidence_ids = mapped_evidence(entries)
            rows.append(
                {
                    "job_id": job["job_id"],
                    "classification": "completed",
                    "evidence_ids": evidence_ids,
                    "contexts": mem0_contexts(entries),
                    "returned_count": len(entries),
                    "latency_ms": latency_ms,
                    "native_status": "completed",
                    "failure": None,
                    "operations": operation_results,
                }
            )
            raw_rows.append(
                {
                    "job_id": job["job_id"],
                    "add_results": adds,
                    "search": search,
                }
            )
        write_json(artifacts / "raw" / f"mem0-{phase}.json", raw_rows)
        phases[phase] = {
            "status": "completed",
            "jobs": rows,
            "adapter_metadata": {"index_reused": phase == "warm"},
        }

    return {
        "schema": "elf.benchmark_unit_result/v4",
        "target": "mem0",
        "native_mode": "external_embedding",
        "score_eligible": True,
        "result_class": combined_status(phases),
        "warm_reused_state": True,
        "ingest_count": 1,
        "ingest_duration_ms": round(cold_ingest_duration_ms, 3),
        "phases": phases,
    }


