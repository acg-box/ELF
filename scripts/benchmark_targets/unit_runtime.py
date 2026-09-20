"""Container unit protocol: process I/O, readiness, and failure classification."""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, default=str, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def wait_port(host: str, port: int, timeout: float = 90.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return
        except OSError:
            time.sleep(1)
    raise RuntimeError(f"service did not become ready at {host}:{port}")


def sanitized_error(error: BaseException) -> str:
    message = str(error)
    for name in ("EMBEDDING_API_KEY", "LITELLM_API_KEY", "CHAT_API_KEY"):
        value = os.environ.get(name)
        if value:
            message = message.replace(value, "[redacted]")
    return message


def classify_failure(message: str) -> str:
    lowered = message.lower()
    if re.search(r"(?:provider http|error code|http status|status):\s*[45]\d\d", lowered):
        return "provider_failed"
    if any(token in lowered for token in ("401", "403", "429", "rate limit", "quota exhausted")):
        return "provider_failed"
    if any(
        token in lowered
        for token in ("provider api", "provider request", "provider error", "api key")
    ):
        return "provider_failed"
    return "adapter_failed"


def run_command(command: list[str], log_path: Path, env: dict[str, str]) -> float:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        check=False,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode:
        output = completed.stdout[-6000:]
        raise RuntimeError(
            f"adapter exited {completed.returncode} after "
            f"{time.monotonic() - started:.3f}s; output follows:\n{output}"
        )
    return (time.monotonic() - started) * 1000.0


def combined_status(phases: dict[str, Any]) -> str:
    for phase in ("cold", "warm"):
        if phases[phase]["status"] != "completed":
            return phases[phase]["status"]
    return "completed"


