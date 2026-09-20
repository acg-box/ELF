"""Build answer context only from native ranked readback after mutations."""

from __future__ import annotations

from typing import Any

from .fixtures import opaque_evidence_id, opaque_job_id


class NativeContextError(ValueError):
    """A mutation job omitted or malformed its native ranked readback."""


def answer_cases(
    suite: dict[str, Any], unit: dict[str, Any], context_budget_chars: int
) -> list[dict[str, Any]]:
    """Build target-blind warm answer cases from only retrieved source context."""
    jobs = {opaque_job_id(job["job_id"]): job for job in suite["jobs"]}
    jobs.update({job["job_id"]: job for job in suite["jobs"]})
    cases: list[dict[str, Any]] = []
    for raw in (unit.get("phases") or {}).get("warm", {}).get("jobs", []):
        job = jobs.get(raw.get("job_id"))
        if job is None or raw.get("classification") != "completed":
            continue
        source_evidence = {item["evidence_id"]: item["text"] for item in job["corpus"]}
        evidence = {
            key: text
            for evidence_id, text in source_evidence.items()
            for key in (evidence_id, opaque_evidence_id(evidence_id, job["job_id"]))
        }
        context = []
        used = 0
        if "contexts" in raw:
            native_contexts = raw.get("contexts")
            if not isinstance(native_contexts, list) or any(
                not isinstance(item, dict)
                or not isinstance(item.get("text"), str)
                or (
                    item.get("evidence_id") is not None
                    and not isinstance(item.get("evidence_id"), str)
                )
                for item in native_contexts
            ):
                raise NativeContextError(
                    f"{raw.get('job_id')} returned malformed native ranked contexts"
                )
            ranked_contexts = native_contexts
        elif job.get("operations"):
            raise NativeContextError(
                f"{raw.get('job_id')} omitted native ranked contexts after mutation"
            )
        else:
            ranked_contexts = [
                {"evidence_id": evidence_id, "text": evidence.get(evidence_id)}
                for evidence_id in raw.get("evidence_ids") or []
            ]
        for rank, item in enumerate(ranked_contexts, start=1):
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if text is None:
                continue
            rendered = f"[{rank}] {text}"
            if used + len(rendered) > context_budget_chars:
                break
            context.append(rendered)
            used += len(rendered)
        cases.append(
            {
                "case_id": raw["job_id"],
                "question": job["query"],
                "context": context,
            }
        )
    return cases
