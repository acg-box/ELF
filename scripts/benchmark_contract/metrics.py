"""Independent scoring oracles for retrieval, answers, and mutation receipts."""

from __future__ import annotations

from typing import Any
from datetime import date
import math
import re
import statistics

from .fixtures import FAILURE_CLASSES


def _dedupe(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value not in output:
            output.append(value)
    return output


def _ndcg_at_five(retrieved: list[str], relevant: set[str]) -> float | None:
    if not relevant:
        return None
    dcg = sum(
        1.0 / math.log2(index + 2)
        for index, evidence_id in enumerate(retrieved[:5])
        if evidence_id in relevant
    )
    ideal = sum(1.0 / math.log2(index + 2) for index in range(min(5, len(relevant))))
    return dcg / ideal


def _mean(values: list[float | None]) -> float | None:
    measured = [value for value in values if value is not None]
    return sum(measured) / len(measured) if measured else None


def _rounded(value: float | None) -> float | None:
    return round(value, 6) if value is not None else None


def _ci95(values: list[float | None]) -> dict[str, Any] | None:
    measured = [value for value in values if value is not None]
    if not measured:
        return None
    mean = statistics.fmean(measured)
    if len(measured) == 1:
        lower = upper = mean
    else:
        margin = 1.96 * statistics.stdev(measured) / math.sqrt(len(measured))
        lower, upper = max(0.0, mean - margin), min(1.0, mean + margin)
    return {
        "method": "job_level_normal_approximation",
        "n": len(measured),
        "mean": _rounded(mean),
        "lower": _rounded(lower),
        "upper": _rounded(upper),
    }


def _normalized_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9._:/+-]+", value.casefold()))


_MONTH_NAMES = ('january', 'february', 'march', 'april', 'may', 'june',
                'july', 'august', 'september', 'october', 'november', 'december')
_MONTHS = {name: index for index, full in enumerate(_MONTH_NAMES, 1) for name in (full, full[:3])}
_MONTHS['sept'] = 9
_MONTH_PATTERN = '|'.join(sorted(_MONTHS, key=len, reverse=True))
_DATE_PATTERNS = [
    re.compile(rf'\b(?P<month>{_MONTH_PATTERN})\.?\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?(?:,\s*|\s+)(?P<year>\d{{4}})\b', re.I),
    re.compile(rf'\b(?P<day>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<month>{_MONTH_PATTERN})\.?(?:,\s*|\s+)(?P<year>\d{{4}})\b', re.I),
]


def _canonical_calendar_dates(value: str) -> str:
    def replace(match):
        try:
            return date(int(match['year']), _MONTHS[match['month'].casefold()], int(match['day'])).isoformat()
        except ValueError:
            return match[0]
    for pattern in _DATE_PATTERNS:
        value = pattern.sub(replace, value)
    return value


def _answer_scores(qrels: dict[str, Any], raw_answer: Any, *, canonical_dates: bool = False) -> tuple[Any, Any, list[str]]:
    if not isinstance(raw_answer, dict):
        return None, None, []
    text = str(raw_answer.get("text") or "")
    def normalize(value):
        return _normalized_text(_canonical_calendar_dates(value) if canonical_dates else value)
    normalized = normalize(text)
    forbidden = [
        fact
        for fact in qrels.get("forbidden_answer_facts") or []
        if normalize(str(fact)) in normalized
    ]
    if qrels.get("expect_unsupported"):
        unsupported_error = (
            raw_answer.get("supported") is not False or normalized != "unknown"
        )
        return float(not unsupported_error), float(unsupported_error), forbidden
    facts = [str(fact) for fact in qrels.get("answer_facts") or []]
    correct = bool(facts) and all(normalize(fact) in normalized for fact in facts)
    correct = correct and not forbidden and raw_answer.get("supported") is not False
    return float(correct), None, forbidden


def _normalized_native_contexts(
    raw: Any, evidence_id_map: dict[str, str]
) -> list[dict[str, Any]] | None:
    if not isinstance(raw, list):
        return None
    contexts: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("text"), str):
            return None
        evidence_id = item.get("evidence_id")
        if evidence_id is not None and not isinstance(evidence_id, str):
            return None
        contexts.append(
            {
                "evidence_id": evidence_id_map.get(evidence_id, evidence_id),
                "text": item["text"],
            }
        )
    return contexts


def _operation_scores(
    expected: list[str],
    operations: list[dict[str, Any]],
    native: Any,
    retrieved: list[str],
    contexts: list[dict[str, Any]] | None,
) -> tuple[float | None, float | None, list[str]]:
    rows = native if isinstance(native, list) else []
    missing: list[str] = []
    update_values: list[float] = []
    delete_values: list[float] = []
    for requested in expected:
        operation = next(
            (item for item in operations if item.get("type") == requested), None
        )
        row = next(
            (
                item
                for item in rows
                if isinstance(item, dict)
                and item.get("requested_type") == requested
                and item.get("classification") in FAILURE_CLASSES
            ),
            None,
        )
        if row is None:
            missing.append(requested)
            value = 0.0
            native_type = None
        else:
            native_type = row.get("native_type")
            value = 1.0 if (row.get("classification") == "completed"
                            and row.get("native_success") is True) else 0.0
        if requested == "update":
            exact = native_type in {"update", "replace", "reindex_update"}
            evidence_id = operation.get("evidence_id") if operation else None
            replacement = operation.get("text") if operation else None
            readback = bool(
                contexts is not None
                and isinstance(evidence_id, str)
                and isinstance(replacement, str)
                and evidence_id in retrieved
                and any(
                    context.get("evidence_id") == evidence_id
                    and _normalized_text(replacement)
                    in _normalized_text(str(context.get("text") or ""))
                    for context in contexts
                )
            )
            update_values.append(value if exact and readback else 0.0)
        elif requested == "delete":
            exact = native_type in {"delete", "forget", "session_delete"}
            evidence_id = operation.get("evidence_id") if operation else None
            readback = bool(
                contexts is not None
                and isinstance(evidence_id, str)
                and evidence_id not in retrieved
                and all(
                    context.get("evidence_id") != evidence_id for context in contexts
                )
            )
            delete_values.append(value if exact and readback else 0.0)
    return _mean(update_values), _mean(delete_values), missing
