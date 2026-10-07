#!/usr/bin/env python3
"""Run each capability action in a new client process against retained native state."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from benchmark_deep.drivers import run_action
from benchmark_targets.unit_runtime import sanitized_error, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--action", type=Path)
    args = parser.parse_args()
    benchmark_root = Path(os.environ.get("BENCHMARK_DEEP_ROOT", "/benchmark"))
    root = benchmark_root / "artifacts/deep-state"
    root.mkdir(parents=True, exist_ok=True)
    if args.action:
        action = json.loads(args.action.read_text())
        output = args.action.with_suffix(".result.json")
        started = time.monotonic()
        try:
            row = {"status": "completed", **run_action(args.target, action, root)}
        except Exception as error:
            row = {"status": "failed", "failure": sanitized_error(error)}
        row.update(duration_seconds=time.monotonic()-started, pid=os.getpid())
        write_json(output, row)
        return 0 if row["status"] == "completed" else 1
    workload = json.loads((benchmark_root / "input/workload.json").read_text())
    results = []
    unavailable = set()
    for index, action in enumerate(workload["actions"]):
        action = {**action, "operation_id": f"operation-{index:03d}"}
        path = root / (action["operation_id"] + ".json")
        write_json(path, action)
        if action["scope"] in unavailable:
            row = {"status": "blocked_by_ingest", "failure": "Native scope ingestion did not complete"}
        else:
            try:
                with path.with_suffix(".log").open("w") as log:
                    subprocess.run([sys.executable, __file__, "--target", args.target,
                        "--action", str(path)], stdout=log, stderr=subprocess.STDOUT, timeout=1200)
                row = json.loads(path.with_suffix(".result.json").read_text())
            except (subprocess.TimeoutExpired, FileNotFoundError) as error:
                row = {"status": "failed", "failure": sanitized_error(error)}
        if action["action"] == "ingest" and row["status"] != "completed":
            unavailable.add(action["scope"])
        results.append({"operation_id": action["operation_id"], "action": action["action"],
            "scope": action["scope"], "case_id": action.get("case_id"), **row})
        write_json(benchmark_root / "artifacts/deep-result.json", {
            "schema": "elf.deep_result/v1", "target": args.target,
            "process_boundary": "new client process per native operation; server retained",
            "results": results})
    return 0 if all(row["status"] == "completed" for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
