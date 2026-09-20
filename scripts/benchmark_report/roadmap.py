"""Benchmark report roadmap: derived only from measured bundle evidence."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .metrics import comparable, fmt, retrieval_effective, warm


def job_desirability(job: dict[str, Any]) -> float | None:
    values: list[float] = []
    for name in (
        "recall_at_5",
        "ndcg_at_5",
        "source_trace_rate",
        "native_update_success",
        "native_delete_success",
    ):
        value = job.get(name)
        if isinstance(value, (int, float)):
            values.append(float(value))
    value = job.get("privacy_scope_violation")
    if isinstance(value, (int, float)):
        values.append(1.0 - float(value))
    if job.get("forbidden_evidence_hits") is not None:
        values.append(float(not bool(job["forbidden_evidence_hits"])))
    return sum(values) / len(values) if values else None


def elf_jobs(bundle: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    output: list[tuple[str, dict[str, Any]]] = []
    for suite_id, suite in bundle["suite_results"].items():
        row = next((item for item in suite["results"] if item["target"] == "elf"), None)
        if row is None or not comparable([row]):
            continue
        output.extend((suite_id, job) for job in warm(row).get("jobs") or [])
    return output


def elf_unscored_units(bundle: dict[str, Any]) -> list[tuple[str, str]]:
    output = []
    for suite_id, suite in bundle["suite_results"].items():
        row = next((item for item in suite["results"] if item["target"] == "elf"), None)
        if row is not None and not comparable([row]):
            output.append((suite_id, row["evaluation"]["classification"]))
    return output


def performance_regression_jobs(
    bundle: dict[str, Any], multiplier: float = 10.0
) -> set[str]:
    output: set[str] = set()
    for suite_id, suite in bundle["suite_results"].items():
        elf = next(
            (
                row
                for row in suite["results"]
                if row["target"] == "elf" and comparable([row])
            ),
            None,
        )
        competitors = [
            row
            for row in comparable(suite["results"])
            if row["target"] != "elf" and retrieval_effective(row)
        ]
        if elf is None or not competitors:
            continue
        competitor_latency: dict[str, list[float]] = defaultdict(list)
        for row in competitors:
            for job in warm(row).get("jobs") or []:
                value = job.get("latency_ms")
                if (
                    job.get("classification") == "completed"
                    and isinstance(value, (int, float))
                    and value > 0
                ):
                    competitor_latency[job["job_id"]].append(float(value))
        for job in warm(elf).get("jobs") or []:
            value = job.get("latency_ms")
            baselines = competitor_latency.get(job.get("job_id")) or []
            if (
                job.get("classification") == "completed"
                and isinstance(value, (int, float))
                and baselines
                and float(value) > multiplier * min(baselines)
            ):
                output.add(f"{suite_id}/{job['job_id']}")
    return output


def elf_job_summary(bundle: dict[str, Any]) -> list[str]:
    measured = [
        (suite, job, job_desirability(job))
        for suite, job in elf_jobs(bundle)
        if job.get("classification") == "completed" and job_desirability(job) is not None
    ]
    failed = [
        f"{suite}/* ({classification}; whole unit unscored)"
        for suite, classification in elf_unscored_units(bundle)
    ]
    lines: list[str] = []
    if measured:
        ordered = sorted(measured, key=lambda item: (item[2], item[0], item[1]["job_id"]))
        weakest = ordered[: min(5, len(ordered))]
        strongest = list(reversed(ordered[-min(5, len(ordered)) :]))
        lines.append(
            "- Strongest scenarios: "
            + ", ".join(
                f"`{suite}/{job['job_id']}` ({fmt(score)})"
                for suite, job, score in strongest
            )
            + "."
        )
        lines.append(
            "- Weakest scenarios: "
            + ", ".join(
                f"`{suite}/{job['job_id']}` ({fmt(score)})"
                for suite, job, score in weakest
            )
            + "."
        )
    if failed:
        lines.append("- Incomplete scenarios: " + ", ".join(failed) + ".")
    if not lines:
        lines.append("- ELF did not enter a scored denominator, so no strength claim is possible.")
    return lines


def roadmap(bundle: dict[str, Any]) -> list[str]:
    categories: dict[str, set[str]] = defaultdict(set)
    for suite_id, job in elf_jobs(bundle):
        identity = f"{suite_id}/{job['job_id']}"
        if isinstance(job.get("recall_at_5"), (int, float)) and job["recall_at_5"] < 1:
            categories["retrieval"].add(identity)
        if job.get("forbidden_evidence_hits"):
            categories["stale"].add(identity)
        if job.get("privacy_scope_violation") == 1:
            categories["privacy"].add(identity)
        if isinstance(job.get("source_trace_rate"), (int, float)) and job["source_trace_rate"] < 1:
            categories["trace"].add(identity)
        if job.get("native_update_success") == 0 or job.get("native_delete_success") == 0:
            categories["lifecycle"].add(identity)
    categories["performance"].update(performance_regression_jobs(bundle))

    definitions = [
        (
            "retrieval",
            "Improve evidence recall and ranking",
            "Candidate generation, chunking, or scope routing did not place expected evidence in the top five; confirm the cause from the trace.",
            "Tune candidate recall, chunking, and scope activation before reranking.",
            "Recall@5 and nDCG@5",
            "failed jobs",
            "Rerun the same frozen suite and jobs.",
        ),
        (
            "stale",
            "Strengthen stale-evidence suppression",
            "Current and stale evidence both reached the candidate set or final top five; confirm the filter boundary from hit traces.",
            "Apply supersession and current-state filters before final retrieval and retain an audit reason.",
            "Forbidden or stale evidence hit rate",
            "failed jobs",
            "Rerun the same frozen suite and jobs.",
        ),
        (
            "privacy",
            "Repair privacy-scope isolation",
            "A scope filter did not apply before retrieval; confirm the cause from the violating hit trace.",
            "Apply private scope as a hard pre-retrieval filter and record the rejection reason.",
            "Privacy-scope violation rate",
            "failed jobs",
            "Rerun the same frozen suite and jobs.",
        ),
        (
            "trace",
            "Complete stable source identity",
            "A native result did not map back to a stable source reference.",
            "Carry a non-inferred native source reference on every candidate and final evidence item.",
            "Source or citation trace rate",
            "failed jobs",
            "Rerun the same frozen suite and jobs.",
        ),
        (
            "performance",
            "Shorten the retrieval and ingest critical path",
            "ELF warm latency exceeded the fastest effective non-ELF row for the same job by more than 10 times.",
            "Use existing traces to separate embedding, storage, candidate generation, and rerank time, then optimize only the dominant stage.",
            "Warm query latency and cold ingest duration, with Recall@5, nDCG@5, and source trace as quality guardrails",
            "jobs above the 10× same-job latency threshold",
            "Rerun the same frozen suite and jobs; latency must return below the threshold without reducing a quality guardrail.",
        ),
        (
            "lifecycle",
            "Repair the native update or deletion loop",
            "A native mutation receipt or later visibility check failed.",
            "Repair update or deletion, asynchronous indexing, and read-after-write state handling.",
            "Native update success and native deletion success",
            "failed jobs",
            "Rerun the same frozen suite and jobs.",
        ),
    ]
    actions: list[str] = []
    for key, title, cause, change, expected, job_label, regression in definitions:
        jobs = sorted(categories.get(key) or [])
        if not jobs:
            continue
        identities = ", ".join(f"`{job}`" for job in jobs)
        actions.append(
            f"{len(actions) + 1}. **{title}** — {job_label} ({len(jobs)}): {identities}. "
            f"Possible cause: {cause} Suggested change: {change} Expected metrics: {expected}. Regression: {regression}"
        )
        if len(actions) == 5:
            break
    if not actions:
        actions.append(
            "1. This run produced no attributable ELF metric failure. Do not infer a product change; retain the benchmark as a regression baseline."
        )
    return actions

