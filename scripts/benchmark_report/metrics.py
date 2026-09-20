"""Benchmark report metrics: derived only from measured bundle evidence."""

from __future__ import annotations

from typing import Any, Iterable

from .labels import LOWER_IS_BETTER, METRIC_NAMES, SHARED_ANSWER_METRICS


def fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def esc(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def warm(result: dict[str, Any]) -> dict[str, Any]:
    return result["evaluation"]["phases"]["warm"]


def metrics(result: dict[str, Any]) -> dict[str, Any]:
    return warm(result).get("metrics") or {}


def decision_metric(result: dict[str, Any], name: str) -> Any:
    value = metrics(result).get(name)
    if name in SHARED_ANSWER_METRICS:
        return None
    if (
        name
        in {
            "forbidden_or_stale_evidence_hit_rate",
            "privacy_scope_violation_rate",
        }
        and metrics(result).get("mean_recall_at_5") == 0
    ):
        return None
    return value


def retrieval_effective(result: dict[str, Any]) -> bool:
    value = metrics(result).get("mean_recall_at_5")
    return isinstance(value, (int, float)) and value > 0


def count_text(phase: dict[str, Any]) -> str:
    counts = phase["counts"]
    return "/".join(
        str(counts[name])
        for name in ("scheduled", "completed", "failed", "not_applicable", "scored")
    )


def comparable(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row["evaluation"]["classification"] == "completed"
        and row["evaluation"].get("score_eligible")
        and warm(row).get("quality_denominator")
    ]


def metric_leaders(
    rows: list[dict[str, Any]], metric_names: Iterable[str]
) -> list[str]:
    completed = comparable(rows)
    output: list[str] = []
    for name in metric_names:
        measured = [
            (row["target"], decision_metric(row, name))
            for row in completed
            if decision_metric(row, name) is not None
        ]
        if not measured:
            continue
        best = (
            min(value for _, value in measured)
            if name in LOWER_IS_BETTER
            else max(value for _, value in measured)
        )
        leaders = sorted(target for target, value in measured if value == best)
        output.append(f"{METRIC_NAMES[name]}: {', '.join(leaders)} ({fmt(best)})")
    return output

