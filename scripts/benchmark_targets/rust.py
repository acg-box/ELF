"""Cold/warm execution and receipt normalization for Rust-backed targets."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .unit_runtime import classify_failure, combined_status, run_command, wait_port

ADAPTER = Path("/usr/local/bin/real_world_live_adapter")
QMD_REVISION = "e428df76bc0274d9e93eb7ca3e95673315c42e90"

def native_operation_receipts(
    target: str, phase: str, fixture: dict[str, Any] | None
) -> list[dict[str, Any]]:
    if phase != "warm" or fixture is None:
        return []
    native_types = {
        "elf": {"update": "update", "delete": "delete"},
        "qmd": {"update": "reindex_update", "delete": "delete"},
    }
    mapping = native_types.get(target)
    if mapping is None:
        return []
    return [
        {
            "requested_type": operation["type"],
            "native_type": mapping[operation["type"]],
            "classification": "completed",
            "native_success": True,
        }
        for operation in fixture.get("operations") or []
    ]


def normalize_rust_phase(
    evidence_path: Path,
    *,
    target: str,
    phase: str,
    fixtures: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    jobs = []
    phase_status = "completed"
    for job in evidence["jobs"]:
        failure = job.get("failure")
        classification = classify_failure(failure) if failure else "completed"
        if classification != "completed":
            phase_status = classification
        row = {
            "job_id": job["job_id"],
            "classification": classification,
            "evidence_ids": list(job.get("evidence_ids") or []),
            "returned_count": int(job.get("returned_count") or 0),
            "latency_ms": float(job.get("latency_ms") or 0.0),
            "native_status": job.get("status"),
            "failure": failure,
            "operations": native_operation_receipts(
                target, phase, fixtures.get(job["job_id"])
            ) if classification == "completed" else [],
        }
        if "contexts" in job:
            row["contexts"] = job["contexts"]
        jobs.append(row)
    return {
        "status": phase_status,
        "jobs": jobs,
        "adapter_metadata": evidence.get("metadata") or {},
    }


def skipped_warm_phase(cold: dict[str, Any]) -> dict[str, Any]:
    classification = cold["status"]
    return {
        "status": classification,
        "jobs": [
            {
                "job_id": job["job_id"],
                "classification": classification,
                "evidence_ids": [],
                "returned_count": 0,
                "latency_ms": 0.0,
                "native_status": "not_run",
                "failure": f"warm phase not run because cold ended as {classification}",
                "operations": [],
            }
            for job in cold["jobs"]
        ],
        "adapter_metadata": {
            "index_reused": False,
            "skipped_due_to_cold": True,
        },
    }


def run_rust_target(target: str, input_dir: Path, artifacts: Path, state_root: Path) -> dict[str, Any]:
    if target == "elf":
        wait_port("postgres", 5432)
        wait_port("qdrant", 6334)
    state_dir = state_root / target
    state_dir.mkdir(parents=True, exist_ok=True)
    phases: dict[str, Any] = {}
    fixtures = {
        job["job_id"]: job
        for job in (
            json.loads(path.read_text(encoding="utf-8")) for path in sorted(input_dir.glob("*.json"))
        )
    }
    ingest_duration_ms = 0.0
    env = os.environ.copy()
    if target == "elf":
        env["ELF_REAL_WORLD_EXTERNAL_EMBEDDING"] = "1"

    for phase in ("cold", "warm"):
        if phase == "warm" and phases["cold"]["status"] != "completed":
            phases["warm"] = skipped_warm_phase(phases["cold"])
            break
        raw_dir = artifacts / "raw" / phase
        evidence_path = raw_dir / "evidence.json"
        command = [
            str(ADAPTER),
            target,
            "--fixtures",
            str(input_dir),
            "--out-fixtures",
            str(raw_dir / "fixtures"),
            "--evidence-out",
            str(evidence_path),
            "--work-dir",
            str(state_dir),
            "--adapter-id",
            f"{target}-competitor-benchmark",
        ]
        if target == "elf":
            command.extend(("--config", "/opt/elf/elf.docker.toml"))
        elif target == "qmd":
            command.extend(
                (
                    "--qmd-dir",
                    "/opt/qmd",
                    "--qmd-revision",
                    QMD_REVISION,
                    "--lexical-only",
                )
            )
        if phase == "warm":
            command.append("--reuse-index")
        duration_ms = run_command(command, raw_dir / "adapter.log", env)
        phases[phase] = normalize_rust_phase(
            evidence_path,
            target=target,
            phase=phase,
            fixtures=fixtures,
        )
        if phase == "cold":
            native_query_ms = sum(
                float(row.get("latency_ms") or 0.0) for row in phases[phase]["jobs"]
            )
            ingest_duration_ms = max(0.0, duration_ms - native_query_ms)

    warm_reused = (
        phases["warm"]["status"] == "completed"
        and phases["warm"]["adapter_metadata"].get("index_reused") is True
    )
    return {
        "schema": "elf.benchmark_unit_result/v4",
        "target": target,
        "native_mode": "lexical" if target == "qmd" else "external_embedding",
        "score_eligible": True,
        "result_class": combined_status(phases),
        "warm_reused_state": warm_reused,
        "ingest_count": 1,
        "ingest_duration_ms": round(ingest_duration_ms, 3),
        "ingest_duration_measurement": "cold adapter wall time minus native query latency",
        "phases": phases,
    }


