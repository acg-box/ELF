"""Benchmark report decisions: derived only from measured bundle evidence."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .labels import LOWER_IS_BETTER, METRIC_NAMES
from .metrics import comparable, decision_metric, fmt, metrics, retrieval_effective
from .roadmap import roadmap


def product_observations(bundle: dict[str, Any]) -> list[str]:
    by_target: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for suite_id, suite in bundle["suite_results"].items():
        for row in suite["results"]:
            by_target[row["target"]].append((suite_id, row))
    lines: list[str] = []
    for target in sorted(bundle.get("target_pins") or {}):
        raw_attempts = by_target.get(target, [])
        attempts = (
            [item for item in raw_attempts if comparable([item[1]])]
            if target == "elf"
            else raw_attempts
        )
        completed = [
            suite_id
            for suite_id, row in attempts
            if row["evaluation"]["classification"] == "completed"
        ]
        failed = [
            f"{suite_id}:{row['evaluation']['classification']}"
            for suite_id, row in attempts
            if row["evaluation"]["classification"] != "completed"
        ]
        measured: list[tuple[str, float]] = []
        for _, row in attempts:
            if not comparable([row]):
                continue
            for name in METRIC_NAMES:
                value = decision_metric(row, name)
                if isinstance(value, (int, float)) and name != "mean_query_latency_ms":
                    desirable = 1.0 - float(value) if name in LOWER_IS_BETTER else float(value)
                    measured.append((name, desirable))
        details: list[str] = []
        if measured:
            strongest = max(measured, key=lambda item: item[1])
            weakest = min(measured, key=lambda item: item[1])
            if strongest[1] > 0:
                details.append(
                    f"measured relative strength: {METRIC_NAMES[strongest[0]]} (directional value {fmt(strongest[1])})"
                )
            else:
                details.append("no positive measured quality strength")
            details.append(
                f"measured relative weakness: {METRIC_NAMES[weakest[0]]} (directional value {fmt(weakest[1])})"
            )
        if completed:
            details.insert(0, f"completed {', '.join(completed)}")
        if failed:
            details.append(f"failed or not comparable: {', '.join(failed)}")
        performance = []
        for suite_id, row in attempts:
            if not comparable([row]):
                continue
            performance.append(
                f"{suite_id} ingest {fmt(row['evaluation'].get('cold_ingest_duration_ms'), 1)} ms / warm {fmt(metrics(row).get('mean_query_latency_ms'), 1)} ms"
            )
            if (
                metrics(row).get("mean_recall_at_5") == 0
                and metrics(row).get("forbidden_or_stale_evidence_hit_rate") == 0
            ):
                details.append(
                    f"{suite_id} has zero stale hits and zero recall; this is not a stale-suppression strength"
                )
        if performance:
            details.append("performance: " + "; ".join(performance))
        if not attempts:
            details.append(
                "no comparable completed quality row; an unscored unit cannot support a measured strength or weakness"
                if raw_attempts
                else "retained in the manifest, but no suite applies in this run"
            )
        lines.append(f"- **{target}**: {'; '.join(details)}.")
    return lines


def quality_anchor(rows: list[dict[str, Any]]) -> list[str]:
    candidates = comparable(rows)
    for name in ("mean_recall_at_5", "mean_ndcg_at_5"):
        measured = [
            row
            for row in candidates
            if isinstance(decision_metric(row, name), (int, float))
        ]
        if not measured:
            continue
        best = max(float(decision_metric(row, name)) for row in measured)
        candidates = [
            row for row in measured if float(decision_metric(row, name)) == best
        ]
    return sorted(row["target"] for row in candidates)


def fastest_targets(
    rows: list[dict[str, Any]], field: str
) -> tuple[list[str], float | None]:
    measured: list[tuple[str, float]] = []
    for row in comparable(rows):
        value = (
            row["evaluation"].get("cold_ingest_duration_ms")
            if field == "ingest"
            else metrics(row).get("mean_query_latency_ms")
        )
        if isinstance(value, (int, float)):
            measured.append((row["target"], float(value)))
    if not measured:
        return [], None
    best = min(value for _, value in measured)
    return sorted(target for target, value in measured if value == best), best


def suite_performance_disposition(
    suite_id: str, rows: list[dict[str, Any]]
) -> str | None:
    elf = next(
        (row for row in rows if row["target"] == "elf" and comparable([row])), None
    )
    competitors = [
        row
        for row in comparable(rows)
        if row["target"] != "elf" and retrieval_effective(row)
    ]
    if elf is None or not competitors:
        return None
    ingest_values = [
        float(row["evaluation"]["cold_ingest_duration_ms"])
        for row in competitors
        if isinstance(row["evaluation"].get("cold_ingest_duration_ms"), (int, float))
        and row["evaluation"]["cold_ingest_duration_ms"] > 0
    ]
    latency_values = [
        float(metrics(row)["mean_query_latency_ms"])
        for row in competitors
        if isinstance(metrics(row).get("mean_query_latency_ms"), (int, float))
        and metrics(row)["mean_query_latency_ms"] > 0
    ]
    elf_ingest = elf["evaluation"].get("cold_ingest_duration_ms")
    elf_latency = metrics(elf).get("mean_query_latency_ms")
    details = []
    if isinstance(elf_ingest, (int, float)) and ingest_values:
        details.append(f"ingest is {float(elf_ingest) / min(ingest_values):.1f}× the fastest non-ELF row")
    if isinstance(elf_latency, (int, float)) and latency_values:
        details.append(f"warm is {float(elf_latency) / min(latency_values):.1f}× the fastest non-ELF row")
    return f"{suite_id}: " + ", ".join(details) if details else None


def five_decisions(bundle: dict[str, Any]) -> list[str]:
    suites = bundle.get("suite_results") or {}
    common_rows = (suites.get("common-core-v1") or {}).get("results") or []
    repository_rows = (suites.get("repository-knowledge-v1") or {}).get("results") or []
    memory_rows = (suites.get("memory-lifecycle-v1") or {}).get("results") or []
    knowledge_rows = (suites.get("knowledge-structure-v1") or {}).get("results") or []

    source_parts = []
    common_elf = next(
        (row for row in common_rows if row["target"] == "elf" and comparable([row])), None
    )
    if common_elf is not None:
        source_parts.append(
            "Common Core ELF Recall@5/nDCG@5/source trace is "
            f"{fmt(metrics(common_elf).get('mean_recall_at_5'))}/"
            f"{fmt(metrics(common_elf).get('mean_ndcg_at_5'))}/"
            f"{fmt(metrics(common_elf).get('source_or_citation_trace_rate'))}"
        )
    non_elf_anchor = quality_anchor(
        [row for row in common_rows if row["target"] != "elf"]
    )
    if non_elf_anchor:
        source_parts.append(
            "the non-ELF quality anchor (Recall first, then nDCG) is "
            + ", ".join(non_elf_anchor)
        )
    repository_elf = next(
        (row for row in repository_rows if row["target"] == "elf" and comparable([row])),
        None,
    )
    if repository_elf is not None:
        source_parts.append(
            "Repository Knowledge ELF Recall@5/nDCG@5 is "
            f"{fmt(metrics(repository_elf).get('mean_recall_at_5'))}/"
            f"{fmt(metrics(repository_elf).get('mean_ndcg_at_5'))}"
        )

    lifecycle_parts = []
    for row in comparable(memory_rows):
        value = metrics(row)
        lifecycle_parts.append(
            f"{row['target']} update/delete/stale/privacy="
            f"{fmt(value.get('native_correction_and_update_success'))}/"
            f"{fmt(value.get('native_deletion_or_forgetting_success'))}/"
            f"{fmt(value.get('forbidden_or_stale_evidence_hit_rate'))}/"
            f"{fmt(value.get('privacy_scope_violation_rate'))}, warm {fmt(value.get('mean_query_latency_ms'), 1)} ms"
        )

    trace_parts = []
    knowledge_anchor = quality_anchor(knowledge_rows)
    if knowledge_anchor:
        trace_parts.append("Knowledge Structure quality anchor: " + ", ".join(knowledge_anchor))
    knowledge_elf = next(
        (row for row in knowledge_rows if row["target"] == "elf" and comparable([row])), None
    )
    if knowledge_elf is not None:
        value = metrics(knowledge_elf)
        trace_parts.append(
            "ELF source trace="
            f"{fmt(value.get('source_or_citation_trace_rate'))}; "
            "shared answer correct/unsupported="
            f"{fmt(value.get('programmatic_answer_correctness'))}/"
            f"{fmt(value.get('unsupported_answer_rate'))} "
            "(end-to-end observation, not product or roadmap attribution)"
        )

    capability_parts = []
    performance_parts = []
    for suite_id, suite in suites.items():
        rows = suite.get("results") or []
        quality = quality_anchor(rows)
        ingest_targets, ingest_value = fastest_targets(rows, "ingest")
        warm_targets, warm_value = fastest_targets(rows, "warm")
        capability_parts.append(
            f"{suite_id}: quality anchor={', '.join(quality) or 'none'}, "
            f"fastest ingest={', '.join(ingest_targets) or 'none'} ({fmt(ingest_value, 1)} ms), "
            f"fastest warm={', '.join(warm_targets) or 'none'} ({fmt(warm_value, 1)} ms)"
        )
        disposition = suite_performance_disposition(suite_id, rows)
        if disposition:
            performance_parts.append(disposition)

    action_titles = [
        line.split("**", 2)[1] for line in roadmap(bundle) if line.count("**") >= 2
    ]
    return [
        "1. **Source-linked retrieval comparison** — "
        + ("; ".join(source_parts) or "no comparable completed source-linked row")
        + ".",
        "2. **Temporal state, correction, deletion, scope, and continuity** — "
        + ("; ".join(lifecycle_parts) or "no comparable completed lifecycle row")
        + ".",
        "3. **Source, citation, refusal, and organization reliability** — "
        + ("; ".join(trace_parts) or "no comparable completed knowledge-structure row")
        + ".",
        "4. **Strongest evidence by capability and performance trade-off** — No aggregate score is used. The quality anchor compares Recall@5 first and nDCG@5 second. A performance leader must be read with the quality anchor; zero recall is not a quality strength. "
        + "; ".join(capability_parts)
        + (". ELF performance disposition: " + "; ".join(performance_parts) if performance_parts else "")
        + ".",
        "5. **What ELF should change first** — "
        + (" → ".join(action_titles) if action_titles else "no attributable product change")
        + "; the full jobs, causes, metrics, changes, and regression conditions are in the ELF Development Order section.",
    ]

