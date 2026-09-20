"""Benchmark report coverage: derived only from measured bundle evidence."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .labels import BASE_TABLE_METRICS, SUITE_TABLE_METRICS, TABLE_LABELS
from .metrics import comparable, count_text, esc, fmt, metrics, warm


def result_table(
    rows: list[dict[str, Any]], suite_id: str | None = None
) -> list[str]:
    rows = comparable(rows)
    selected = [
        name
        for name in SUITE_TABLE_METRICS.get(suite_id, BASE_TABLE_METRICS)
        if any(metrics(row).get(name) is not None for row in rows)
    ]
    if suite_id is None:
        optional = (
            "native_correction_and_update_success",
            "native_deletion_or_forgetting_success",
            "privacy_scope_violation_rate",
        )
        selected.extend(
            name
            for name in optional
            if any(metrics(row).get(name) is not None for row in rows)
        )
    headers = [
        "Product",
        "Result",
        "Scheduled/Completed/Failed/Not applicable/Scored",
        *(TABLE_LABELS[name] for name in selected),
        "Cold ingest (ms)",
        "Warm query (ms)",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---", "---", "---:"] + ["---:"] * (len(headers) - 3)) + "|",
    ]
    for row in rows:
        evaluation = row["evaluation"]
        phase = warm(row)
        value = metrics(row)
        fields = [
            esc(row["target"]),
            esc(evaluation["classification"]),
            count_text(phase),
            *(fmt(value.get(name)) for name in selected),
            fmt(evaluation.get("cold_ingest_duration_ms"), 1),
            fmt(value.get("mean_query_latency_ms"), 1),
        ]
        lines.append("| " + " | ".join(fields) + " |")
    return lines


def failure_message(row: dict[str, Any]) -> str:
    unit = row.get("unit_result") or {}
    failure = unit.get("failure")
    if isinstance(failure, dict) and failure.get("message"):
        return str(failure["message"])
    failures = row["evaluation"].get("contract_failures") or []
    if failures:
        return "; ".join(map(str, failures))
    for phase_name in ("cold", "warm"):
        for job in row["evaluation"]["phases"][phase_name].get("jobs") or []:
            if job.get("failure"):
                return str(job["failure"])
    return "No additional error detail was provided"


def coverage_table(bundle: dict[str, Any]) -> list[str]:
    lines = [
        "| Suite | Product | Result | Scheduled | Completed | Failed | Not applicable | Scored | Cleanup passed |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for suite_id, suite in bundle["suite_results"].items():
        for row in suite["results"]:
            counts = warm(row)["counts"]
            lines.append(
                "| {suite} | {target} | {result} | {scheduled} | {completed} | {failed} | {not_applicable} | {scored} | {cleanup} |".format(
                    suite=esc(suite_id),
                    target=esc(row["target"]),
                    result=esc(row["evaluation"]["classification"]),
                    scheduled=counts["scheduled"],
                    completed=counts["completed"],
                    failed=counts["failed"],
                    not_applicable=counts["not_applicable"],
                    scored=counts["scored"],
                    cleanup=fmt(row["cleanup"].get("passed")),
                )
            )
    return lines


def failure_table(bundle: dict[str, Any]) -> list[str]:
    lines = [
        "| Suite | Product | Type | Detail |",
        "|---|---|---|---|",
    ]
    found = False
    for suite_id, suite in bundle["suite_results"].items():
        for row in suite["results"]:
            classification = row["evaluation"]["classification"]
            if classification == "completed":
                continue
            found = True
            lines.append(
                f"| {esc(suite_id)} | {esc(row['target'])} | {esc(classification)} | {esc(failure_message(row))} |"
            )
    if not found:
        lines.append("| — | — | — | No typed failures |")
    return lines


def common_ci(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| Product | Metric | n | Mean | 95% CI |",
        "|---|---|---:|---:|---:|",
    ]
    found = False
    for row in comparable(rows):
        ci = metrics(row).get("job_level_95ci") or {}
        for name, label in (
            ("recall_at_5", "Recall@5"),
            ("ndcg_at_5", "nDCG@5"),
            ("answer_correctness", "Answer correctness"),
        ):
            value = ci.get(name)
            if not value:
                continue
            found = True
            lines.append(
                f"| {esc(row['target'])} | {label} | {value['n']} | {fmt(value['mean'])} | [{fmt(value['lower'])}, {fmt(value['upper'])}] |"
            )
    if not found:
        lines.append("| — | — | 0 | — | — |")
    return lines


def native_contract_boundaries(bundle: dict[str, Any]) -> list[str]:
    lines = [
        "| Product | Type | Suite or field | Exact contract statement |",
        "|---|---|---|---|",
    ]
    found = False
    for target, contract in sorted((bundle.get("target_contracts") or {}).items()):
        for suite_id, reason in sorted((contract.get("not_applicable") or {}).items()):
            found = True
            lines.append(
                f"| {esc(target)} | not_applicable | {esc(suite_id)} | {esc(reason)} |"
            )
        for field, reason in sorted((contract.get("native_deviations") or {}).items()):
            found = True
            lines.append(
                f"| {esc(target)} | native_deviation | {esc(field)} | {esc(reason)} |"
            )
    if not found:
        lines.append("| — | — | — | No declared native-interface boundary |")
    return lines


def provider_usage(bundle: dict[str, Any]) -> Counter[str]:
    usage: Counter[str] = Counter()
    for suite in bundle["suite_results"].values():
        for row in suite["results"]:
            for provider_value in (row["evaluation"].get("provider_usage") or {}).values():
                if not isinstance(provider_value, dict):
                    continue
                for name, value in provider_value.items():
                    if isinstance(value, int):
                        usage[name] += value
    return usage

