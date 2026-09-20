"""Apply coverage and eligibility gates before publishing phase metrics."""

from __future__ import annotations

from typing import Any

from .fixtures import FAILURE_CLASSES, opaque_evidence_id, opaque_job_id, validate_suite
from .metrics import (
    _answer_scores,
    _ci95,
    _dedupe,
    _mean,
    _ndcg_at_five,
    _normalized_native_contexts,
    _operation_scores,
    _rounded,
)


def evaluate_unit(
    suite: dict[str, Any], unit: dict[str, Any], target: dict[str, Any]
) -> dict[str, Any]:
    """Normalize one native unit and score only centrally visible evidence."""
    validate_suite(suite)
    target_id = target["id"]
    if unit.get("schema") != "elf.benchmark_unit_result/v4":
        raise ValueError(f"{target_id} unit schema is not v4")
    if unit.get("target") != target_id:
        raise ValueError(f"{target_id} unit target identity differs from the manifest")
    if unit.get("result_class") not in FAILURE_CLASSES:
        raise ValueError(f"{target_id} unit has an unknown result class")
    if unit.get("result_class") == "completed":
        if unit.get("ingest_count") != 1:
            raise ValueError(f"{target_id} completed unit did not ingest exactly once")
        if unit.get("warm_reused_state") is not True:
            raise ValueError(f"{target_id} completed unit did not reuse cold state for warm")
    score_eligible = bool(unit.get("score_eligible"))
    if score_eligible != bool(target.get("score_eligible")):
        raise ValueError(f"{target_id} score eligibility differs from the manifest")

    jobs_by_id = {job["job_id"]: job for job in suite["jobs"]}
    job_id_map = {opaque_job_id(job_id): job_id for job_id in jobs_by_id}
    suite_kind = suite["kind"]
    contract_failures: list[str] = []
    phases: dict[str, Any] = {}
    for phase_name in ("cold", "warm"):
        raw_phase = (unit.get("phases") or {}).get(phase_name) or {
            "status": unit.get("result_class", "harness_failed"),
            "jobs": [],
        }
        normalized_rows: list[dict[str, Any]] = []
        normalized_job_ids: list[str] = []
        for raw_job in raw_phase.get("jobs") or []:
            if raw_job.get("classification") not in FAILURE_CLASSES:
                raise ValueError(f"{target_id} job has an unknown failure classification")
            raw_job_id = str(raw_job.get("job_id") or "unknown")
            job_id = job_id_map.get(raw_job_id, raw_job_id)
            normalized_job_ids.append(job_id)
            definition = jobs_by_id.get(job_id)
            if definition is None:
                continue
            evidence_id_map = {
                opaque_evidence_id(item["evidence_id"], job_id): item["evidence_id"]
                for item in definition["corpus"]
            }
            qrels = definition["qrels"]
            raw_evidence = _dedupe(
                [str(evidence_id) for evidence_id in raw_job.get("evidence_ids") or []]
            )[:5]
            original_evidence_ids = set(evidence_id_map.values())
            retrieved = [
                evidence_id_map.get(evidence_id, evidence_id)
                for evidence_id in raw_evidence
            ]
            native_contexts = (
                _normalized_native_contexts(raw_job.get("contexts"), evidence_id_map)
                if "contexts" in raw_job
                else None
            )
            requires_native_readback = bool(definition.get("operations"))
            if phase_name == "warm" and requires_native_readback:
                if "contexts" not in raw_job:
                    contract_failures.append(
                        f"{job_id} omitted native ranked contexts after mutation"
                    )
                elif native_contexts is None:
                    contract_failures.append(
                        f"{job_id} returned malformed native ranked contexts after mutation"
                    )
            relevant = set(qrels.get("relevant_evidence") or [])
            forbidden = set(qrels.get("forbidden_evidence") or [])
            relevant_hits = [value for value in retrieved if value in relevant]
            forbidden_hits = [value for value in retrieved if value in forbidden]
            returned_count = int(raw_job.get("returned_count") or 0)
            mapped_count = sum(
                evidence_id in evidence_id_map or evidence_id in original_evidence_ids
                for evidence_id in raw_evidence
            )
            trace_rate = (
                mapped_count / min(5, returned_count)
                if returned_count > 0
                else None
            )
            answer_correct, unsupported_error, forbidden_answer = _answer_scores(
                qrels, raw_job.get("answer")
            )
            update_success, delete_success, missing_operations = _operation_scores(
                list(qrels.get("required_operations") or []),
                list(definition.get("operations") or []),
                raw_job.get("operations"),
                retrieved,
                native_contexts,
            )
            if phase_name == "warm" and missing_operations:
                contract_failures.append(
                    f"{job_id} omitted native operations: {', '.join(missing_operations)}"
                )
            privacy_violation = None
            if qrels.get("privacy"):
                privacy_violation = float(bool(forbidden_hits or forbidden_answer))
            normalized_rows.append(
                {
                    "job_id": job_id,
                    "classification": raw_job.get(
                        "classification", raw_phase.get("status")
                    ),
                    "retrieved_evidence": retrieved,
                    "native_contexts": native_contexts or [],
                    "recall_at_5": _rounded(
                        len(relevant_hits) / len(relevant) if relevant else None
                    ),
                    "ndcg_at_5": _rounded(_ndcg_at_five(retrieved, relevant)),
                    "forbidden_evidence_hits": forbidden_hits,
                    "source_trace_rate": _rounded(trace_rate),
                    "answer": raw_job.get("answer"),
                    "answer_correct": answer_correct,
                    "unsupported_answer_error": unsupported_error,
                    "forbidden_answer_facts": forbidden_answer,
                    "native_operations": raw_job.get("operations") or [],
                    "native_update_success": update_success,
                    "native_delete_success": delete_success,
                    "privacy_scope_violation": privacy_violation,
                    "latency_ms": raw_job.get("latency_ms"),
                    "failure": raw_job.get("failure"),
                }
            )

        expected_ids = set(jobs_by_id)
        actual_ids = set(normalized_job_ids)
        duplicates = sorted(
            job_id
            for job_id in actual_ids
            if normalized_job_ids.count(job_id) > 1
        )
        coverage = {
            "expected": len(expected_ids),
            "actual": len(normalized_job_ids),
            "missing": sorted(expected_ids - actual_ids),
            "unexpected": sorted(actual_ids - expected_ids),
            "duplicates": duplicates,
            "passed": expected_ids == actual_ids
            and not duplicates
            and len(normalized_job_ids) == len(expected_ids),
        }
        completed_rows = [
            row for row in normalized_rows if row["classification"] == "completed"
        ]
        phase_class = raw_phase.get("status", unit.get("result_class"))
        if unit.get("result_class") == "completed":
            if phase_class != "completed":
                contract_failures.append(
                    f"{phase_name} phase reported {phase_class} in a completed unit"
                )
            if not coverage["passed"]:
                contract_failures.append(
                    f"{phase_name} phase did not return the exact scheduled job set"
                )
            if len(completed_rows) != len(normalized_rows):
                contract_failures.append(
                    f"{phase_name} phase contains non-completed job rows"
                )
        quality_denominator = bool(
            unit.get("result_class") == "completed"
            and score_eligible
            and phase_class == "completed"
            and coverage["passed"]
            and len(completed_rows) == len(normalized_rows)
            and not (phase_name == "cold" and suite_kind != "retrieval")
        )
        metric_rows = completed_rows if quality_denominator else []
        metrics = None
        if metric_rows:
            metrics = {
                "mean_recall_at_5": _rounded(
                    _mean([row["recall_at_5"] for row in metric_rows])
                ),
                "mean_ndcg_at_5": _rounded(
                    _mean([row["ndcg_at_5"] for row in metric_rows])
                ),
                "forbidden_or_stale_evidence_hit_rate": _rounded(
                    _mean(
                        [float(bool(row["forbidden_evidence_hits"])) for row in metric_rows]
                    )
                ),
                "source_or_citation_trace_rate": _rounded(
                    _mean([row["source_trace_rate"] for row in metric_rows])
                ),
                "programmatic_answer_correctness": _rounded(
                    _mean([row["answer_correct"] for row in metric_rows])
                ),
                "native_correction_and_update_success": _rounded(
                    _mean([row["native_update_success"] for row in metric_rows])
                ),
                "native_deletion_or_forgetting_success": _rounded(
                    _mean([row["native_delete_success"] for row in metric_rows])
                ),
                "privacy_scope_violation_rate": _rounded(
                    _mean([row["privacy_scope_violation"] for row in metric_rows])
                ),
                "unsupported_answer_rate": _rounded(
                    _mean([row["unsupported_answer_error"] for row in metric_rows])
                ),
                "mean_query_latency_ms": _rounded(
                    _mean(
                        [
                            float(row["latency_ms"])
                            for row in metric_rows
                            if row["latency_ms"] is not None
                        ]
                    )
                ),
            }
            if suite["suite_id"] == "common-core-v1":
                metrics["job_level_95ci"] = {
                    "recall_at_5": _ci95([row["recall_at_5"] for row in metric_rows]),
                    "ndcg_at_5": _ci95([row["ndcg_at_5"] for row in metric_rows]),
                    "answer_correctness": _ci95(
                        [row["answer_correct"] for row in metric_rows]
                    ),
                }
        phases[phase_name] = {
            "classification": phase_class,
            "quality_denominator": quality_denominator,
            "coverage": coverage,
            "counts": {
                "scheduled": len(expected_ids),
                "completed": len(completed_rows),
                "failed": sum(
                    row["classification"] not in {"completed", "not_applicable"}
                    for row in normalized_rows
                ),
                "not_applicable": sum(
                    row["classification"] == "not_applicable"
                    for row in normalized_rows
                ),
                "scored": len(metric_rows),
            },
            "metrics": metrics,
            "native_metadata": raw_phase.get("adapter_metadata") or {},
            "jobs": sorted(normalized_rows, key=lambda row: row["job_id"]),
        }

    classification = str(unit.get("result_class") or "harness_failed")
    if classification == "completed" and contract_failures:
        classification = "adapter_failed"
        for phase in phases.values():
            phase["quality_denominator"] = False
            phase["metrics"] = None
            phase["counts"]["scored"] = 0
    return {
        "schema": "elf.benchmark_result/v1",
        "suite_id": suite["suite_id"],
        "suite_kind": suite_kind,
        "target": target_id,
        "classification": classification,
        "score_eligible": score_eligible,
        "native_mode": unit.get("native_mode"),
        "contract_failures": contract_failures,
        "cold_ingest_duration_ms": unit.get("ingest_duration_ms"),
        "provider_usage": unit.get("provider_usage") or {},
        "phases": phases,
    }


