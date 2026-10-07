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
    if not unit.get("score_eligible"):
        return unit
    try:
        cases = answer_cases(suite, unit, context_budget)
    except NativeContextError as error:
        failed = failure_unit(
            {
                "id": unit["target"],
                "adapter": unit.get("native_mode"),
                "score_eligible": unit.get("score_eligible"),
            },
            suite,
            "adapter_failed",
            str(error),
        )
        failed["native_retrieval"] = copy.deepcopy(unit)
        return failed
    if not cases:
        return unit
    original = copy.deepcopy(unit)
    unit = copy.deepcopy(unit)
    responses: list[dict[str, Any]] = []
    failures = []
    by_id = {row["job_id"]: row for row in unit["phases"]["warm"]["jobs"]}
    for case in cases:
        row = by_id[case["case_id"]]
        row.pop("answer", None)
        try:
            native = request_answers([case], env)
            responses.append(native)
            choice = native["choices"][0]
            if choice.get("finish_reason") == "length":
                raise ValueError("shared answer exhausted its output token limit")
            content = choice["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("shared answer returned no content")
            decoded = json.loads(content)["answers"]
            if (not isinstance(decoded, list) or len(decoded) != 1
                    or not isinstance(decoded[0], dict)
                    or decoded[0].get("case_id") != case["case_id"]):
                raise ValueError("shared answer case identities differ from the request")
            answer = decoded[0]
            text, supported = answer.get("text"), answer.get("supported")
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"shared answer returned empty text for {case['case_id']}")
            if not isinstance(supported, bool):
                raise TypeError(f"shared answer returned non-boolean supported for {case['case_id']}")
            if not supported and text.strip().casefold() != "unknown":
                raise ValueError(f"unsupported shared answer did not say unknown for {case['case_id']}")
            row["answer"] = {"text": text, "supported": supported}
        except Exception as error:
            message = f"shared target-blind answer request failed: {type(error).__name__}: {error}"
            failures.append({"case_id": case["case_id"], "message": message})
            row.update(classification="provider_failed", failure=message)
    if responses:
        unit["provider_raw"] = {"shared_answer": responses[0] if len(responses) == 1 else {"batches": responses}}
    unit["provider_usage"] = {
        f"shared_answer_{index + 1}": response.get("usage") or {}
        for index, response in enumerate(responses)
    }
    unit["answer_protocol"] = {"revision": "isolated_case_v1", "batch_size": ANSWER_BATCH_SIZE, "max_tokens": 4096}
    if failures:
        unit["native_retrieval"] = original
        unit["answer_errors"] = failures
        unit["result_class"] = "provider_failed"
        unit["phases"]["warm"]["status"] = "provider_failed"
        unit["failure"] = {"classification": "provider_failed", "message": failures[0]["message"]}
    return unit



ANSWER_BATCH_SIZE = 1


def request_answers(cases: list[dict[str, Any]], env: dict[str, str]) -> dict[str, Any]:
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
    with urllib.request.urlopen(request, timeout=remaining_seconds(300)) as response:
        return json.loads(response.read().decode())
