"""GBrain native import, search, revision-aware mutations, and index refresh."""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from .unit_runtime import sanitized_error, write_json


def invoke(home: Path, arguments: list[str], *, json_output: bool = True) -> tuple[Any, float]:
    env = dict(os.environ, GBRAIN_HOME=str(home),
               OPENROUTER_API_KEY=os.environ["EMBEDDING_API_KEY"],
               OPENROUTER_BASE_URL=os.environ["EMBEDDING_API_BASE"])
    started = time.monotonic()
    result = subprocess.run(
        ["bun", "run", "src/cli.ts", *arguments],
        cwd=os.environ.get("GBRAIN_REPO_DIR", "/opt/gbrain"),
        env=env, text=True, capture_output=True, timeout=180,
    )
    if result.returncode:
        raise RuntimeError(sanitized_error(RuntimeError(
            f"GBrain command {arguments[0]} exited {result.returncode}: "
            + (result.stdout + result.stderr)[-4000:])))
    value = json.loads(result.stdout) if json_output else result.stdout
    return value, (time.monotonic() - started) * 1000


def search(job: dict[str, Any], home: Path, operations: list) -> dict[str, Any]:
    result, elapsed = invoke(home, ["search", job["prompt"]["content"],
        "--limit", "5", "--snippet-chars", "0", "--fields", "full", "--json"])
    if not isinstance(result, list):
        raise ValueError("GBrain search did not return a ranked list")
    return {
        "job_id": job["job_id"], "classification": "completed",
        "evidence_ids": [row["slug"] for row in result],
        "contexts": [{"evidence_id": row["slug"], "text": row["chunk_text"]}
                     for row in result],
        "returned_count": len(result), "latency_ms": elapsed,
        "native_status": "completed", "failure": None, "operations": operations,
    }


def run_gbrain(input_dir: Path, artifacts: Path, state: Path) -> dict[str, Any]:
    phases = {phase: {"status": "completed", "jobs": []}
              for phase in ("cold", "warm")}
    receipts = []
    ingest_ms = 0.0
    for path in sorted(input_dir.glob("*.json")):
        job = json.loads(path.read_text())
        home = state / job["job_id"] / "home"
        content = home.parent / "content"
        content.mkdir(parents=True)
        for item in job["corpus"]["items"]:
            (content / f"{item['evidence_id']}.md").write_text(
                f"# {item['evidence_id']}\n\n{item['text']}\n")
        invoke(home, ["init", "--pglite", "--non-interactive", "--db-only",
            "--embedding-model", "openrouter:" + os.environ["EMBEDDING_MODEL"],
            "--embedding-dimensions", os.environ["EMBEDDING_DIMENSIONS"], "--json"])
        imported, elapsed = invoke(home, ["import", str(content), "--json"])
        ingest_ms += elapsed
        phases["cold"]["jobs"].append(search(job, home, []))
        operations = []
        native_receipts = []
        for operation in job.get("operations", []):
            slug = operation["evidence_id"]
            before, _ = invoke(home, ["get", slug, "--include-content", "--json"])
            args = ["put" if operation["type"] == "update" else "delete", slug,
                "--expected-revision", before["revision"],
                "--request-id", str(uuid.uuid4()), "--json"]
            if operation["type"] == "update":
                args += ["--content", f"# {slug}\n\n{operation['text']}\n"]
            native, _ = invoke(home, args)
            after, _ = invoke(home, ["get", slug, "--include-content",
                                     "--include-deleted", "--json"])
            success = (bool(after.get("deleted_at")) if operation["type"] == "delete"
                       else operation["text"] in after.get("content", ""))
            operations.append({"requested_type": operation["type"],
                "native_type": operation["type"], "classification": "completed",
                "native_success": success})
            native_receipts.append({"operation": operation, "receipt": native,
                                    "readback": after})
        immediate = search(job, home, operations) if operations else None
        refresh = None
        refresh_ms = 0.0
        if any(op["type"] == "update" for op in job.get("operations", [])):
            refresh, refresh_ms = invoke(home,
                ["embed", "--stale", "--max-usd", "0.05", "--json"])
        phases["warm"]["jobs"].append(search(job, home, operations))
        receipts.append({"job_id": job["job_id"], "import": imported,
            "operations": native_receipts, "immediate": immediate,
            "refresh": refresh, "refresh_duration_ms": refresh_ms})
        write_json(artifacts / "raw/gbrain-receipts.json", receipts)
    return {
        "schema": "elf.benchmark_unit_result/v4", "target": "gbrain",
        "native_mode": "native_hybrid_search_after_index_refresh",
        "score_eligible": True, "result_class": "completed",
        "warm_reused_state": True, "ingest_count": 1,
        "ingest_duration_ms": ingest_ms, "phases": phases,
    }
