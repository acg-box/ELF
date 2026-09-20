"""LightRAG owns per-job index isolation and native query-mode selection."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from .rust import ADAPTER, normalize_rust_phase, skipped_warm_phase
from .unit_runtime import combined_status, run_command, wait_port

LIGHTRAG_QUERY_MODES = {
    "retrieval": "naive",
    "knowledge_structure": "mix",
}


def _rows_status(rows: list[dict[str, Any]]) -> str:
    for classification in (
        "configuration_failed",
        "provider_failed",
        "product_failed",
        "adapter_failed",
    ):
        if any(row["classification"] == classification for row in rows):
            return classification
    return "completed"


def lightrag_query_mode(job: dict[str, Any]) -> str:
    suite = str(job.get("suite") or "")
    try:
        return LIGHTRAG_QUERY_MODES[suite]
    except KeyError as error:
        raise RuntimeError(f"unsupported LightRAG benchmark suite kind: {suite}") from error


def run_lightrag_target(input_dir: Path, artifacts: Path, state_root: Path) -> dict[str, Any]:
    """Run isolated LightRAG cold/warm pairs in the existing unit protocol."""
    wait_port("lightrag", 9621)
    state_dir = state_root / "lightrag"
    state_dir.mkdir(parents=True, exist_ok=True)
    loaded = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(input_dir.glob("*.json"))]
    phases: dict[str, Any] = {
        "cold": {"jobs": []},
        "warm": {"jobs": []},
    }
    ingest_duration_ms = 0.0
    env = os.environ.copy()

    for fixture_path, job in zip(sorted(input_dir.glob("*.json")), loaded, strict=True):
        job_id = str(job["job_id"])
        job_input = state_dir / "job-input" / job_id
        job_input.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fixture_path, job_input / fixture_path.name)
        job_state = state_dir / "jobs" / job_id
        job_fixtures = {job_id: job}
        query_mode = lightrag_query_mode(job)
        cold_status = "completed"

        for phase in ("cold", "warm"):
            if phase == "warm" and cold_status != "completed":
                skipped = skipped_warm_phase(
                    {"status": cold_status, "jobs": [phases["cold"]["jobs"][-1]]}
                )
                phases["warm"]["jobs"].extend(skipped["jobs"])
                break

            raw_dir = artifacts / "raw" / phase / job_id
            evidence_path = raw_dir / "evidence.json"
            command = [
                str(ADAPTER),
                "lightrag",
                "--fixtures",
                str(job_input),
                "--out-fixtures",
                str(raw_dir / "fixtures"),
                "--evidence-out",
                str(evidence_path),
                "--work-dir",
                str(job_state),
                "--adapter-id",
                "lightrag-competitor-benchmark",
                "--api-base",
                "http://lightrag:9621",
                "--query-mode",
                query_mode,
            ]
            command.append("--reset-index" if phase == "cold" else "--reuse-index")
            duration_ms = run_command(command, raw_dir / "adapter.log", env)
            normalized = normalize_rust_phase(
                evidence_path,
                target="lightrag",
                phase=phase,
                fixtures=job_fixtures,
            )
            if len(normalized["jobs"]) != 1 or normalized["jobs"][0]["job_id"] != job_id:
                raise RuntimeError(
                    f"LightRAG isolated adapter returned an invalid job identity for {job_id}"
                )
            phases[phase]["jobs"].extend(normalized["jobs"])
            if phase == "cold":
                cold_status = normalized["status"]
                native_query_ms = float(normalized["jobs"][0].get("latency_ms") or 0.0)
                ingest_duration_ms += max(0.0, duration_ms - native_query_ms)

        native_dir = job_state / "native"
        if native_dir.is_dir():
            shutil.copytree(
                native_dir,
                artifacts / "raw" / "lightrag-native" / job_id,
                dirs_exist_ok=True,
            )

    for phase in ("cold", "warm"):
        phases[phase]["status"] = _rows_status(phases[phase]["jobs"])
        phases[phase]["adapter_metadata"] = {
            "index_reused": phase == "warm"
            and all(row["classification"] == "completed" for row in phases[phase]["jobs"]),
            "job_count": len(phases[phase]["jobs"]),
            "job_isolation": "native_document_clear_before_each_cold_job",
            "query_modes": sorted(
                {lightrag_query_mode(job) for job in loaded}
            ),
        }

    result_class = combined_status(phases)
    return {
        "schema": "elf.benchmark_unit_result/v4",
        "target": "lightrag",
        "native_mode": "external_embedding",
        "score_eligible": True,
        "result_class": result_class,
        "warm_reused_state": result_class == "completed",
        "ingest_count": 1,
        "ingest_duration_ms": round(ingest_duration_ms, 3),
        "ingest_duration_measurement": (
            "sum of isolated cold adapter wall times minus native query latency"
        ),
        "phases": phases,
    }


