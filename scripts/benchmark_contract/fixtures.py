"""Validate suite authority and build opaque, scoring-blind product input."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json


PRODUCT_IDS = {
    "elf",
    "mem0",
    "qmd",
    "lightrag",
    "openviking",
    "graphrag",
    "graphiti",
    "letta",
    "sag",
    "pageindex",
    "openkb",
    "honcho",
}
SUITE_IDS = {
    "common-core-v1": 24,
    "memory-lifecycle-v1": 8,
    "knowledge-structure-v1": 8,
    "repository-knowledge-v1": 8,
}
FAILURE_CLASSES = {
    "completed",
    "product_failed",
    "adapter_failed",
    "harness_failed",
    "provider_failed",
    "configuration_failed",
    "timeout_failed",
    "cleanup_failed",
    "not_applicable",
}
FORBIDDEN_PRODUCT_KEYS = {
    "answer_facts",
    "expected_answer",
    "expect_unsupported",
    "forbidden_answer_facts",
    "forbidden_evidence",
    "negative_traps",
    "privacy",
    "qrels",
    "required_evidence",
    "required_operations",
    "scoring_rubric",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def opaque_identifier(kind: str, value: str) -> str:
    digest = hashlib.sha256(
        f"elf-benchmark-v4:{kind}:{value}".encode("utf-8")
    ).hexdigest()[:24]
    return f"{kind[:1]}_{digest}"


def opaque_job_id(job_id: str) -> str:
    return opaque_identifier("job", job_id)


def opaque_evidence_id(evidence_id: str, job_id: str) -> str:
    return opaque_identifier("evidence", f"{job_id}\0{evidence_id}")


def assert_product_payload_is_blind(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        leaked = FORBIDDEN_PRODUCT_KEYS.intersection(value)
        if leaked:
            raise ValueError(
                f"product payload leaks evaluator keys at {path}: "
                + ", ".join(sorted(leaked))
            )
        for key, child in value.items():
            assert_product_payload_is_blind(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_product_payload_is_blind(child, f"{path}[{index}]")


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema") != "elf.benchmark_manifest/v4":
        raise ValueError("manifest schema must be elf.benchmark_manifest/v4")
    runner = manifest.get("runner")
    if not isinstance(runner, dict) or int(runner.get("capacity", 0)) not in {1, 2}:
        raise ValueError("runner capacity must be one or two")
    targets = manifest.get("targets")
    if not isinstance(targets, list):
        raise ValueError("manifest targets must be a list")
    target_ids = [target.get("id") for target in targets if isinstance(target, dict)]
    if set(target_ids) != PRODUCT_IDS or len(target_ids) != len(PRODUCT_IDS):
        raise ValueError("manifest must contain every retained product exactly once")
    suites = manifest.get("suites")
    if not isinstance(suites, list):
        raise ValueError("manifest suites must be a list")
    suite_ids = [suite.get("id") for suite in suites if isinstance(suite, dict)]
    if set(suite_ids) != set(SUITE_IDS) or len(suite_ids) != len(SUITE_IDS):
        raise ValueError("manifest must contain common-core and exactly three capability suites")
    if set(manifest.get("failure_classes") or {}) != FAILURE_CLASSES:
        raise ValueError("manifest failure taxonomy differs from the normalized schema")
    for target in targets:
        pin = target.get("pin")
        if not isinstance(pin, dict) or not pin.get("kind"):
            raise ValueError(f"{target.get('id')} has no pinned runtime identity")
        target_suites = target.get("suites")
        if not isinstance(target_suites, list) or not set(target_suites) <= set(SUITE_IDS):
            raise ValueError(f"{target.get('id')} has invalid suite eligibility")


def validate_suite(suite: dict[str, Any]) -> None:
    suite_id = suite.get("suite_id")
    if suite_id not in SUITE_IDS:
        raise ValueError(f"unknown suite id: {suite_id}")
    jobs = suite.get("jobs")
    expected_job_count = SUITE_IDS[suite_id]
    readiness_subset = suite.get("execution_mode") == "readiness"
    valid_job_count = (
        isinstance(jobs, list)
        and (
            1 <= len(jobs) <= expected_job_count
            if readiness_subset
            else len(jobs) == expected_job_count
        )
    )
    if not valid_job_count:
        raise ValueError(
            f"{suite_id} must contain exactly {expected_job_count} jobs"
            if not readiness_subset
            else f"{suite_id} readiness subset must contain 1-{expected_job_count} jobs"
        )
    job_ids: set[str] = set()
    for job in jobs:
        if not isinstance(job, dict):
            raise ValueError(f"{suite_id} contains a non-object job")
        job_id = job.get("job_id")
        if not isinstance(job_id, str) or not job_id or job_id in job_ids:
            raise ValueError(f"{suite_id} has an invalid or duplicate job id")
        job_ids.add(job_id)
        corpus = job.get("corpus")
        if not isinstance(corpus, list) or not corpus:
            raise ValueError(f"{job_id} has no corpus")
        evidence_ids = [item.get("evidence_id") for item in corpus]
        if any(not isinstance(value, str) or not value for value in evidence_ids):
            raise ValueError(f"{job_id} has an invalid evidence id")
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError(f"{job_id} has duplicate evidence ids")
        qrels = job.get("qrels")
        if not isinstance(qrels, dict):
            raise ValueError(f"{job_id} has no scorer-only qrels")
        referenced = set(qrels.get("relevant_evidence") or []) | set(
            qrels.get("forbidden_evidence") or []
        )
        if not referenced <= set(evidence_ids):
            raise ValueError(f"{job_id} qrels reference unknown evidence")
        operations = job.get("operations") or []
        if suite.get("kind") in {"memory_lifecycle", "repository_knowledge"}:
            if not operations:
                raise ValueError(f"{job_id} must execute a native operation")
        for operation in operations:
            if operation.get("type") not in {"update", "delete"}:
                raise ValueError(f"{job_id} has an unsupported operation")
            if operation.get("evidence_id") not in evidence_ids:
                raise ValueError(f"{job_id} operation references unknown evidence")
            if operation["type"] == "update" and not operation.get("text"):
                raise ValueError(f"{job_id} update has no replacement text")


def product_job(job: dict[str, Any], suite: dict[str, Any]) -> dict[str, Any]:
    operations = []
    for operation in job.get("operations") or []:
        product_operation = {
            "type": operation["type"],
            "evidence_id": opaque_evidence_id(
                operation["evidence_id"], job["job_id"]
            ),
        }
        if operation.get("text") is not None:
            product_operation["text"] = operation["text"]
        operations.append(product_operation)
    payload = {
        "schema": "elf.real_world_job/v1",
        "job_id": opaque_job_id(job["job_id"]),
        "suite": suite["kind"],
        "title": "Benchmark task",
        "corpus": {
            "items": [
                {
                    "evidence_id": opaque_evidence_id(
                        item["evidence_id"], job["job_id"]
                    ),
                    "text": item["text"],
                }
                for item in job["corpus"]
            ]
        },
        "prompt": {"content": job["query"]},
        "operations": operations,
        "memory_evolution": None,
    }
    assert_product_payload_is_blind(payload)
    return payload


def materialize_product_fixtures(
    suite: dict[str, Any], destination: Path
) -> list[Path]:
    validate_suite(suite)
    destination.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for job in suite["jobs"]:
        payload = product_job(job, suite)
        path = destination / f"{opaque_job_id(job['job_id'])}.json"
        path.write_bytes(canonical_json(payload))
        paths.append(path)
    return paths


