"""Host benchmark providers responsibilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from .runtime import REPO, command, write_json


def load_local_env() -> dict[str, str]:
    values = dict(os.environ)
    common_dir = Path(command(["git", "rev-parse", "--git-common-dir"]).stdout.strip())
    if not common_dir.is_absolute():
        common_dir = (REPO / common_dir).resolve()
    for path in (common_dir.parent / ".env", REPO / ".env"):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            name, value = stripped.split("=", 1)
            values.setdefault(name.strip(), value.strip().strip('"').strip("'"))
    return values


def container_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value.rstrip("/"))
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        return value.rstrip("/")
    host = "host.docker.internal"
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urllib.parse.urlunsplit(
        (parsed.scheme, host, parsed.path.rstrip("/"), parsed.query, parsed.fragment)
    )


def provider_environment(
    source: dict[str, str], providers: dict[str, Any], *, inside_container: bool
) -> dict[str, str]:
    embedding_base = source.get("EMBEDDING_API_BASE")
    embedding_key = source.get("EMBEDDING_API_KEY")
    chat_base = (
        source.get("LITELLM_CHAT_COMPAT_BASE_URL")
        or source.get("LITELLM_BASE_URL")
    )
    chat_key = source.get("LITELLM_API_KEY")
    missing = [
        name
        for name, value in (
            ("EMBEDDING_API_BASE", embedding_base),
            ("EMBEDDING_API_KEY", embedding_key),
            ("LITELLM_CHAT_COMPAT_BASE_URL or LITELLM_BASE_URL", chat_base),
            ("LITELLM_API_KEY", chat_key),
        )
        if not value
    ]
    if missing:
        raise KeyError("missing benchmark provider configuration: " + ", ".join(missing))
    transform = container_url if inside_container else lambda value: value.rstrip("/")
    return {
        "BENCHMARK_EMBEDDING_API_BASE": transform(str(embedding_base)),
        "BENCHMARK_EMBEDDING_API_KEY": str(embedding_key),
        "BENCHMARK_EMBEDDING_MODEL": providers["embedding"]["model"],
        "BENCHMARK_EMBEDDING_DIMENSIONS": str(providers["embedding"]["dimensions"]),
        "BENCHMARK_CHAT_API_BASE": transform(str(chat_base)),
        "BENCHMARK_CHAT_API_KEY": str(chat_key),
        "BENCHMARK_CHAT_MODEL": providers["chat"]["model"],
        "BENCHMARK_CHAT_REASONING_EFFORT": providers["chat"]["reasoning_effort"],
    }


def provider_preflight(env: dict[str, str], artifact_root: Path) -> dict[str, Any]:
    completed = command(
        [sys.executable, "scripts/benchmark-provider-preflight.py"],
        env=env,
        check=False,
        timeout=180,
    )
    try:
        result = json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        result = {
            "schema": "elf.benchmark_provider_preflight/v1",
            "classification": "harness_failed",
            "message": "provider preflight did not return typed JSON",
        }
    result["exit_code"] = completed.returncode
    write_json(artifact_root / "provider-preflight.json", result)
    return result

