"""Atomic, identity-bound successful unit receipts; failures always rerun."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from benchmark_contract import evaluate_unit, load_json, sha256_json
from .profiles import integrity_findings
from .runtime import write_json


def reusable(row: dict[str, Any], suite: dict[str, Any], target: dict[str, Any]) -> bool:
    try:
        fresh = evaluate_unit(suite, row["unit_result"], target)
        if fresh != row["evaluation"]:
            return False
        return not integrity_findings({"suite_results": {suite["suite_id"]: {
            "scheduled_targets": [target["id"]], "results": [row]}}})
    except (KeyError, TypeError, ValueError):
        return False


def read_checkpoint(path: Path, identity: str, suite: dict[str, Any], target: dict[str, Any]) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        record = load_json(path)
        row = record["row"]
        if record["identity"] != identity or record["sha256"] != sha256_json(row):
            return None
        if not reusable(row, suite, target):
            return None
        row["reuse"] = {"reused": True, "original_receipt": str(path.resolve()),
                       "note": "Prior measurement; not a fresh timing sample."}
        return row
    except (KeyError, ValueError, TypeError, OSError):
        return None


def save_checkpoint(path: Path, identity: str, row: dict[str, Any]) -> None:
    write_json(path, {"identity": identity, "sha256": sha256_json(row), "row": row})
