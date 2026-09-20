"""Host benchmark runtime responsibilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json
import subprocess


REPO = Path(__file__).resolve().parents[2]


def command(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    check: bool = True,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=REPO,
        env=env,
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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

