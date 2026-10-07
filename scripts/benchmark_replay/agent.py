"""A bounded JSON-action agent with identical source tools in every arm."""
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
import uuid

IMAGE = os.environ.get("BENCHMARK_ELF_IMAGE", "elf-benchmark-elf:replay-drain")
CHECKER = Path(__file__).with_name("checker.py")


class ProviderResponseError(RuntimeError):
    def __init__(self, message, receipt, response_text=None):
        super().__init__(message)
        self.receipt = receipt
        self.response_text = response_text


def request(messages, maximum=8192):
    base = os.environ["LITELLM_BASE_URL"].rstrip("/")
    body = {"model": "deepseek/deepseek-v4.1-flash", "messages": messages,
            "response_format": {"type": "json_object"}, "reasoning_effort": "low",
            "max_tokens": maximum, "stream": False}
    req = urllib.request.Request(base + "/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + os.environ["LITELLM_API_KEY"], "Content-Type": "application/json"})
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=100) as response:
        data = json.load(response)
    text = data["choices"][0]["message"]["content"]
    receipt = {"usage": data.get("usage", {}), "seconds": round(time.monotonic()-started, 3), "finish_reason": data["choices"][0].get("finish_reason")}
    if not isinstance(text, str) or receipt["finish_reason"] == "length":
        raise ProviderResponseError("incomplete model response", receipt, text)
    try:
        decoded = json.loads(text)
        if not isinstance(decoded, dict): raise ValueError("JSON object required")
    except ValueError as error:
        raise ProviderResponseError("invalid model action", receipt, text) from error
    return decoded, receipt


def check(task, workspace, original):
    name = "elf-replay-check-" + uuid.uuid4().hex[:12]
    args = ["docker", "run", "--rm", "--name", name, "--network", "none", "--read-only", "--user", "65534:65534",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "64", "--memory", "512m", "--cpus", "1",
        "--tmpfs", "/tmp:rw,nosuid,size=32m", "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-v", str(workspace.resolve()) + ":/workspace:ro", "-v", str(original.resolve()) + ":/original:ro",
        "-v", str(CHECKER.resolve()) + ":/checks/checker.py:ro", IMAGE, "python3", "/checks/checker.py", task["id"]]
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        try: parsed = json.loads(result.stdout)
        except (ValueError, TypeError): parsed = {"passed": False, "error": result.stderr[-3000:]}
        return dict(parsed, exit_code=result.returncode)
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=15)


def source_path(workspace, relative, allowed):
    if relative not in allowed or (workspace / relative).is_symlink():
        raise ValueError("path is outside the frozen source allowlist")
    return workspace / relative


def act(action, task, workspace, original, allowed):
    kind = action.get("action")
    if kind == "read":
        return {"path": action["path"], "content": source_path(workspace, action["path"], allowed).read_text()[:12000]}
    if kind == "search":
        needle = str(action["query"]).lower()
        if not 2 <= len(needle) <= 100: raise ValueError("search requires 2-100 literal characters")
        matches = []
        for path in sorted(allowed):
            for number, line in enumerate((workspace / path).read_text().splitlines(), 1):
                if needle in line.lower(): matches.append({"path": path, "line": number, "text": line[:250]})
        return {"matches": matches[:35]}
    if kind == "replace":
        path = source_path(workspace, action["path"], [task["path"]])
        old, new = action["old"], action["new"]
        if not isinstance(old, str) or not isinstance(new, str) or not old or len(new) > 12000:
            raise ValueError("invalid replacement")
        text = path.read_text()
        if text.count(old) != 1: raise ValueError("old text must match exactly once; read the file first")
        path.write_text(text.replace(old, new, 1))
        return {"changed": action["path"]}
    if kind == "test": return check(task, workspace, original)
    raise ValueError("unknown action")


def run(task, workspace, original, memory, steps=6):
    allowed = sorted(str(path.relative_to(workspace)) for path in workspace.rglob("*") if path.is_file())
    instruction = ("Repair the frozen repository workspace. Treat recalled notes as potentially stale evidence; the current task requirements take priority. "
        "Return exactly one JSON action per turn: {action:read,path}, {action:search,query}, {action:replace,path,old,new}, {action:test}, or {action:finish,summary}. "
        "Use valid quoted JSON keys. There is no shell, network, package installation, or access outside the listed files. "
        "Only the task's target file is writable. Preserve unrelated behavior. Tests are available through action:test. "
        f"You have at most {steps} turns. Finish after a tested repair; do not invent test results.")
    messages = [{"role": "system", "content": instruction}, {"role": "user", "content": json.dumps({
        "task": task["request"], "target_file": task["path"], "files": allowed, "recalled_context": memory}, ensure_ascii=False)}]
    trace = []; started = time.monotonic(); classification = "turn_limit"
    for index in range(steps):
        try:
            action, receipt = request(messages)
        except ProviderResponseError as error:
            trace.append({"turn": index + 1, "error": str(error), "provider": error.receipt,
                          "response_text": error.response_text})
            if isinstance(error.response_text, str):
                messages.append({"role": "assistant", "content": error.response_text})
            messages.append({"role": "user", "content": f"No action was executed. Return exactly one valid JSON object for the next action. This formatting error used one of your {steps} turns."})
            continue
        except Exception as error:
            classification = "provider_failed"
            trace.append({"turn": index + 1, "error": type(error).__name__})
            break
        row = {"turn": index + 1, "action": action, "provider": receipt}; trace.append(row)
        messages.append({"role": "assistant", "content": json.dumps(action)})
        if action.get("action") == "finish": classification = "completed"; break
        try: observation = act(action, task, workspace, original, allowed)
        except Exception as error: observation = {"error": str(error)}
        row["observation"] = observation
        messages.append({"role": "user", "content": json.dumps({"tool_result": observation})})
    validation = check(task, workspace, original)
    return {"classification": classification, "passed": validation["passed"], "validation": validation,
            "turns": len(trace), "seconds": round(time.monotonic()-started, 3), "trace": trace}
