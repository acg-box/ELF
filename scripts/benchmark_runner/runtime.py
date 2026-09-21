"""Host benchmark runtime responsibilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json
import subprocess
import os
import tempfile
import time
import signal
from contextlib import contextmanager


REPO = Path(__file__).resolve().parents[2]


DEADLINE: float | None = None


def remaining_seconds(maximum: float) -> float:
    if DEADLINE is None:
        return maximum
    remaining = min(maximum, DEADLINE - time.monotonic())
    if remaining <= 0:
        raise TimeoutError("benchmark wall-time budget exhausted")
    return remaining


@contextmanager
def cleanup_budget():
    global DEADLINE
    saved = DEADLINE
    DEADLINE = time.monotonic() + 180
    try:
        yield
    finally:
        DEADLINE = saved


def command(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    check: bool = True,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    limit = remaining_seconds(timeout if timeout is not None else 86400)
    with subprocess.Popen(args, cwd=REPO, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, start_new_session=True) as process:
        try:
            output, _ = process.communicate(timeout=limit)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as interrupted:
            # Terminate the command group, including compiler/test child processes.
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                output, _ = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                output, _ = process.communicate()
            if isinstance(interrupted, KeyboardInterrupt):
                raise interrupted
            raise subprocess.TimeoutExpired(args, limit, output=output) from None
        result = subprocess.CompletedProcess(args, process.returncode, output)
        if check:
            result.check_returncode()
        return result



def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=".receipt-", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)



def source_fingerprint() -> dict[str, Any]:
    head = command(["git", "rev-parse", "HEAD"]).stdout.strip()
    status = command(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"]
    ).stdout
    digest = hashlib.sha256()
    digest.update(command(["git", "diff", "--binary", "HEAD"]).stdout.encode())
    for relative in command(
        ["git", "ls-files", "--others", "--exclude-standard"]
    ).stdout.splitlines():
        path = REPO / relative
        if path.is_file():
            digest.update(relative.encode() + b"\0" + path.read_bytes())
    return {
        "head": head,
        "dirty": bool(status),
        "status_sha256": hashlib.sha256(status.encode()).hexdigest(),
        "content_sha256": digest.hexdigest(),
    }

