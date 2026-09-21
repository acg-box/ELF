"""Explicit scenario coverage and honest sampled-run acceptance."""
from __future__ import annotations

import copy
import hashlib
from typing import Any

# The selected scenarios cover distinct behaviors, rather than a corpus prefix.
SMOKE_JOBS = {
    "common-core-v1": ["core-direct-region", "core-synthesis-runtime-storage",
        "core-correction-falcon", "core-resume-harbor", "core-scope-orion",
        "core-unsupported-lyra"],
    "memory-lifecycle-v1": ["memory-update-channel", "memory-delete-credential",
        "memory-resume-migration", "memory-update-and-delete-release"],
    "knowledge-structure-v1": ["knowledge-cobalt-stack", "knowledge-orion-policy-tree",
        "knowledge-juniper-ownership-graph", "knowledge-lyra-citation-boundary"],
    "repository-knowledge-v1": ["repo-change-validation-command",
        "repo-delete-secret-example", "repo-delete-deprecated-module",
        "repo-update-release-resume"],
}


def select_suite(suite: dict[str, Any], mode: str, limit: int | None) -> dict[str, Any]:
    result = copy.deepcopy(suite)
    jobs = result["jobs"]
    if mode != "compare":
        by_id = {job["job_id"]: job for job in jobs}
        jobs = [by_id[name] for name in SMOKE_JOBS[suite["suite_id"]]]
    if limit is not None:
        if not 1 <= limit <= len(jobs):
            raise ValueError("job limit is outside the selected profile")
        # Stable selection for an explicit diagnostic override, never a full claim.
        jobs = sorted(jobs, key=lambda job: hashlib.sha256(job["job_id"].encode()).digest())[:limit]
    result["jobs"] = jobs
    if len(jobs) != len(suite["jobs"]):
        result["execution_mode"] = "readiness"
    return result


def integrity_findings(bundle: dict[str, Any]) -> list[str]:
    findings = []
    suites = bundle.get("suite_results") or {}
    if not suites:
        return ["no suites executed"]
    for name, suite in suites.items():
        rows = suite.get("results") or []
        planned = suite.get("scheduled_targets") or []
        actual = [row.get("target") for row in rows]
        if not planned or sorted(actual) != sorted(planned) or len(set(actual)) != len(actual):
            findings.append(f"{name}: missing, duplicate, or unexpected targets")
        for row in rows:
            label = f"{name}/{row.get('target')}"
            evaluation = row.get("evaluation") or {}
            if evaluation.get("classification") != "completed":
                findings.append(f"{label}: {evaluation.get('classification', 'missing evaluation')}")
            for phase in ("cold", "warm"):
                result = (evaluation.get("phases") or {}).get(phase) or {}
                if not (result.get("coverage") or {}).get("passed"):
                    findings.append(f"{label}/{phase}: incomplete coverage")
            if not (row.get("cleanup") or {}).get("passed"):
                findings.append(f"{label}: cleanup failed")
            if not (row.get("deterministic_replay") or {}).get("passed"):
                findings.append(f"{label}: replay failed")
    return findings


def quality_summary(bundle: dict[str, Any]) -> dict[str, Any]:
    """Report seeded warm-state violations separately from execution success."""
    failures = []
    for suite in bundle.get("suite_results", {}).values():
        for row in suite["results"]:
            for job in row["evaluation"].get("phases", {}).get("warm", {}).get("jobs", []):
                if job.get("forbidden_evidence_hits") or job.get("privacy_scope_violation") or job.get("forbidden_answer_facts"):
                    failures.append({"target": row["target"], "job": job["job_id"], "reason": "forbidden or private content"})
                for metric in ("native_update_success", "native_delete_success"):
                    if job.get(metric) is not None and job[metric] < 1:
                        failures.append({"target": row["target"], "job": job["job_id"], "reason": metric})
    return {"elf_seeded_invariants_passed": not any(f["target"] == "elf" for f in failures),
            "seeded_violations": failures, "product_safety_proven": False,
            "note": "Execution acceptance is not product superiority or full safety coverage."}
