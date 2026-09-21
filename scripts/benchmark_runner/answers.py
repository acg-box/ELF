"""Host benchmark answers responsibilities."""

from __future__ import annotations

from typing import Any
import copy
import json
import urllib.error
import urllib.parse
import urllib.request

from benchmark_contract import NativeContextError, answer_cases


from .runtime import remaining_seconds

def failure_unit(
    target: dict[str, Any], suite: dict[str, Any], classification: str, message: str
) -> dict[str, Any]:
    jobs = [
        {
            "job_id": job["job_id"],
            "classification": classification,
            "evidence_ids": [],
            "returned_count": 0,
            "latency_ms": 0.0,
            "failure": message,
            "operations": [],
        }
        for job in suite["jobs"]
    ]
    return {
        "schema": "elf.benchmark_unit_result/v4",
        "target": target["id"],
        "native_mode": target["adapter"],
        "score_eligible": bool(target["score_eligible"]),
        "result_class": classification,
        "failure": {"classification": classification, "message": message},
        "warm_reused_state": False,
        "ingest_count": 0,
        "phases": {
            "cold": {"status": classification, "jobs": copy.deepcopy(jobs)},
            "warm": {"status": classification, "jobs": copy.deepcopy(jobs)},
        },
    }


def _api_endpoint(base: str, resource: str) -> str:
    parsed = urllib.parse.urlsplit(base.rstrip("/"))
    path = parsed.path.rstrip("/")
    if not path.endswith(f"/{resource}"):
        path = f"{path}/{resource}" if path.endswith("/v1") else f"{path}/v1/{resource}"
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))


def attach_shared_answers(
    suite: dict[str, Any], unit: dict[str, Any], env: dict[str, str], context_budget: int
) -> dict[str, Any]:
    if unit.get("result_class") != "completed" or not unit.get("score_eligible"):
        return unit
    try:
        cases = answer_cases(suite, unit, context_budget)
    except NativeContextError as error:
        return failure_unit(
            {
                "id": unit["target"],
                "adapter": unit.get("native_mode"),
                "score_eligible": unit.get("score_eligible"),
            },
            suite,
            "adapter_failed",
            str(error),
        )
    if not cases:
        return unit
    prompt = {
        "instruction": (
            "Answer each case only from its supplied context. Return one JSON object "
            "with key answers. Each answer must contain the unchanged case_id, text, and "
            "supported. The text value must never be empty. If supported=true, copy the "
            "concise requested fact from context into text. If the context does not support "
            "the fact, set supported=false and text exactly to unknown."
        ),
        "cases": cases,
    }
    request = urllib.request.Request(
        _api_endpoint(env["BENCHMARK_CHAT_API_BASE"], "chat/completions"),
        data=json.dumps(
            {
                "model": env["BENCHMARK_CHAT_MODEL"],
                "messages": [{"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}],
                "reasoning_effort": env["BENCHMARK_CHAT_REASONING_EFFORT"],
                "response_format": {"type": "json_object"},
                "stream": False,
                "max_tokens": 4096,
            }
        ).encode(),
        headers={
            "Authorization": f"Bearer {env['BENCHMARK_CHAT_API_KEY']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    native: dict[str, Any] | None = None
    try:
        with urllib.request.urlopen(request, timeout=remaining_seconds(300)) as response:
            native = json.loads(response.read().decode())
        unit["provider_raw"] = {"shared_answer": native}
        content = native["choices"][0]["message"]["content"]
        decoded = json.loads(content)
        answers = decoded["answers"]
        if not isinstance(answers, list):
            raise TypeError("answers is not a list")
        by_id = {
            row.get("case_id"): row
            for row in answers
            if isinstance(row, dict) and isinstance(row.get("case_id"), str)
        }
        for row in unit["phases"]["warm"]["jobs"]:
            if row.get("classification") == "completed":
                answer = by_id.get(row.get("job_id"))
                if answer is None:
                    raise ValueError(f"shared answer omitted case {row.get('job_id')}")
                text = answer.get("text")
                supported = answer.get("supported")
                if not isinstance(text, str) or not text.strip():
                    raise ValueError(
                        f"shared answer returned empty text for {row.get('job_id')}"
                    )
                if not isinstance(supported, bool):
                    raise TypeError(
                        f"shared answer returned non-boolean supported for {row.get('job_id')}"
                    )
                if not supported and text.strip().casefold() != "unknown":
                    raise ValueError(
                        f"unsupported shared answer did not say unknown for {row.get('job_id')}"
                    )
                row["answer"] = {
                    "text": text,
                    "supported": supported,
                }
        unit["provider_usage"] = {"shared_answer": native.get("usage") or {}}
        return unit
    except Exception as error:
        message = f"shared target-blind answer request failed: {type(error).__name__}: {error}"
        failed = failure_unit(
            {"id": unit["target"], "adapter": unit.get("native_mode"), "score_eligible": unit.get("score_eligible")},
            suite,
            "provider_failed",
            message,
        )
        if native is not None:
            failed["provider_raw"] = {"shared_answer": native}
        return failed

