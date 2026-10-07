"""Letta Code's native two-session memory workflow on the frozen repair tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

from . import agent
from .tasks import ROOT, TASKS, experience, snapshot
from benchmark_runner.providers import container_url
from benchmark_runner.runtime import write_json

IMAGE = "elf-benchmark-letta-code:v1"


def invoke(arguments, workspace, state, prefix):
    env = {**os.environ, "CHAT_API_BASE": container_url(os.environ["LITELLM_BASE_URL"]),
           "CHAT_API_KEY": os.environ["LITELLM_API_KEY"]}
    name = "elf-letta-" + uuid.uuid4().hex[:12]
    command = ["docker", "run", "--rm", "--name", name,
        "--add-host", "host.docker.internal:host-gateway", "--workdir", "/workspace",
        "--env", "CHAT_API_BASE", "--env", "CHAT_API_KEY",
        "--env", "HOME=/state/home", "--env", "LETTA_LOCAL_BACKEND_DIR=/state/local",
        "--env", "GIT_AUTHOR_NAME=ELF Benchmark", "--env", "GIT_COMMITTER_NAME=ELF Benchmark",
        "--env", "GIT_AUTHOR_EMAIL=benchmark@example.invalid", "--env", "GIT_COMMITTER_EMAIL=benchmark@example.invalid",
        "--volume", f"{workspace}:/workspace", "--volume", f"{state}:/state",
        "--volume", f"{ROOT / 'scripts/benchmark_replay/letta_container.py'}:/letta_container.py:ro",
        "--entrypoint", "python3", IMAGE, "/letta_container.py", *arguments]
    started = time.monotonic()
    try:
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=600)
        stdout, stderr = result.stdout, result.stderr
        for value in (env["CHAT_API_KEY"],):
            stdout, stderr = stdout.replace(value, "[redacted]"), stderr.replace(value, "[redacted]")
        prefix.with_suffix(".stdout.log").write_text(stdout)
        prefix.with_suffix(".stderr.log").write_text(stderr)
        value = json.loads(stdout) if stdout.strip().startswith("{") else None
        return {"exit_code": result.returncode, "native": value,
                "seconds": time.monotonic()-started}
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=30)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.out.resolve()
    root.mkdir(parents=True, exist_ok=False)
    image = subprocess.check_output(["docker", "image", "inspect", "--format", "{{.Id}}", IMAGE], text=True).strip()
    write_json(root / "protocol.json", {"image": image, "package_version": "0.34.4",
        "tasks": 3, "repeats": 2, "max_turns_per_session": 6,
        "scope": "Native explicit memory write, new process and conversation, native repair tools. Separate from the common JSON-action agent comparison.",
        "reflection": "off", "tools": ["Read", "Edit", "Write", "Bash"],
        "transport": "buffered SSE; no time-to-first-token claim"})
    results = []
    for task in TASKS:
        original = root / "source" / task["id"]
        provenance = snapshot(task, original)
        packet = experience(task, original)
        for repeat in (1, 2):
            trial = root / "trials" / f"{task['id']}-{repeat}"
            seed = trial / "seed-workspace"
            workspace = trial / "workspace"
            state = trial / "state"
            shutil.copytree(original, seed)
            shutil.copytree(original, workspace)
            state.mkdir()
            learning = json.dumps({"instruction": "Record concise reusable knowledge in your native persistent memory from this prior exploration. Do not repair source code, analyze fixes, or predict a future task. Cite source paths and distinguish observed implementation from policy. Keep the retained notes concise.", "topic": task["topic"], "sources": packet})
            boundary = "Work only with the supplied files and your native memory. Do not delegate, send messages, schedule tasks, access network services, or push Git changes.\n\n"
            write_json(state / "seed-prompt.json", {"prompt": boundary + learning})
            write_json(state / "repair-prompt.json", {"prompt": boundary + task["request"]})
            row = {"task": task["id"], "repeat": repeat, "arm": "letta-code-native", "source": provenance}
            try:
                learned = invoke(["seed"], seed, state, trial / "seed")
                row["learning"] = learned
                native = learned.get("native") or {}
                if learned["exit_code"] or native.get("is_error") or not native.get("agent_id"):
                    raise RuntimeError("Native memory session did not complete")
                write_json(state / "agent.json", {"agent_id": native["agent_id"]})
                memory_root = state / "local/memfs" / native["agent_id"] / "memory"
                memory_files = []
                for path in sorted(memory_root.rglob("*")):
                    if path.is_symlink() or not path.is_file() or ".git" in path.parts:
                        continue
                    if not path.resolve().is_relative_to(state.resolve()):
                        raise RuntimeError("Native memory file escaped the isolated state directory")
                    data = path.read_bytes()
                    memory_files.append({"path": str(path.relative_to(memory_root)),
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "text": data.decode(errors="replace")[:12000]})
                write_json(trial / "seed-memory.json", memory_files)
                memory_text = "\n".join(f["text"] for f in memory_files)
                row["memory_source_paths_observed"] = [p["path"] for p in packet if p["path"] in memory_text]
                repair = invoke(["repair"], workspace, state, trial / "repair")
                row["repair"] = repair
                repaired = repair.get("native") or {}
                row["new_conversation_same_agent_verified"] = (
                    repaired.get("agent_id") == native["agent_id"]
                    and bool(repaired.get("conversation_id"))
                    and repaired["conversation_id"] != native.get("conversation_id"))
                row["check"] = agent.check(task, workspace, original)
                row["passed"] = row["check"]["passed"]
            except Exception as error:
                row.update(passed=False, failure=f"{type(error).__name__}: {error}")
            finally:
                # The native CLI only received a temporary local gateway credential.
                # Keep memory artifacts, but remove its credential store after use.
                (state / "local/providers/auth.json").unlink(missing_ok=True)
                write_json(trial / "result.json", row)
            results.append(row)
            write_json(root / "results.json", results)
            print(json.dumps({"task": task["id"], "repeat": repeat, "passed": row["passed"],
                              "failure": row.get("failure")}), flush=True)
    return 0 if len(results) == 6 and all(row["passed"] for row in results) else 1
