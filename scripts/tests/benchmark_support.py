"""Shared fixture builders for independent benchmark contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import copy
from benchmark_contract import load_json
from benchmark_contract import opaque_evidence_id
from benchmark_contract import opaque_job_id
import unittest


def load_script(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, REPO / path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module



class BenchmarkCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_json(REPO / "config/benchmark/benchmark-v3.json")
        cls.suites = {
            entry["id"]: load_json(REPO / entry["path"])
            for entry in cls.manifest["suites"]
        }
        cls.targets = {target["id"]: target for target in cls.manifest["targets"]}


    def subset(self, suite_id: str, count: int = 1) -> dict:
        suite = copy.deepcopy(self.suites[suite_id])
        suite["jobs"] = suite["jobs"][:count]
        suite["execution_mode"] = "readiness"
        return suite


    def completed_unit(self, target: str, suite: dict) -> dict:
        cold_jobs = []
        warm_jobs = []
        for job in suite["jobs"]:
            relevant = job["qrels"].get("relevant_evidence") or []
            retrieved = [opaque_evidence_id(value, job["job_id"]) for value in relevant]
            cold_text = {item["evidence_id"]: item["text"] for item in job["corpus"]}
            warm_text = dict(cold_text)
            for operation in job.get("operations") or []:
                if operation["type"] == "update":
                    warm_text[operation["evidence_id"]] = operation["text"]
                elif operation["type"] == "delete":
                    warm_text.pop(operation["evidence_id"], None)
            cold_contexts = [
                {
                    "evidence_id": opaque_evidence_id(value, job["job_id"]),
                    "text": cold_text[value],
                }
                for value in relevant
                if value in cold_text
            ]
            warm_contexts = [
                {
                    "evidence_id": opaque_evidence_id(value, job["job_id"]),
                    "text": warm_text[value],
                }
                for value in relevant
                if value in warm_text
            ]
            answer = {
                "text": " ".join(job["qrels"].get("answer_facts") or []) or "unknown",
                "supported": not bool(job["qrels"].get("expect_unsupported")),
            }
            cold_jobs.append(
                {
                    "job_id": opaque_job_id(job["job_id"]),
                    "classification": "completed",
                    "evidence_ids": retrieved,
                    "contexts": cold_contexts,
                    "returned_count": len(retrieved),
                    "latency_ms": 10.0,
                    "operations": [],
                }
            )
            operations = [
                {
                    "requested_type": operation,
                    "native_type": "update" if operation == "update" else "delete",
                    "classification": "completed",
                    "native_success": True,
                }
                for operation in job["qrels"].get("required_operations") or []
            ]
            warm_jobs.append(
                {
                    **cold_jobs[-1],
                    "contexts": warm_contexts,
                    "answer": answer,
                    "operations": operations,
                }
            )
        return {
            "schema": "elf.benchmark_unit_result/v4",
            "target": target,
            "native_mode": self.targets[target]["adapter"],
            "score_eligible": self.targets[target]["score_eligible"],
            "result_class": "completed",
            "warm_reused_state": True,
            "ingest_count": 1,
            "ingest_duration_ms": 100.0,
            "phases": {
                "cold": {"status": "completed", "jobs": cold_jobs},
                "warm": {"status": "completed", "jobs": warm_jobs},
            },
        }


