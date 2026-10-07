"""Behavior checks executed in a network-disabled container, never on the host."""
import json
from pathlib import Path
import signal
import re
import subprocess
import sys
import tempfile
import uuid
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/workspace/scripts")
kind = sys.argv[1]
checks = []

def check(name, predicate):
    checks.append({"name": name, "passed": bool(predicate)})

if kind == "receipt-origin":
    from benchmark_runner import checkpoints as module
    from benchmark_contract import sha256_json
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "receipt.json"
        old = str(Path(directory) / (uuid.uuid4().hex + ".json"))
        def load(row, identity="run", digest=None):
            path.write_text(json.dumps({"identity": identity, "sha256": digest or sha256_json(row), "row": row}))
            return module.read_checkpoint(path, "run", {}, {})
        with patch.object(module, "reusable", return_value=True):
            first = load({"payload": "measured"})
            check("first-origin", first["reuse"]["original_receipt"] == str(path.resolve()))
            second = load({"payload": "measured", "reuse": {"reused": True, "original_receipt": old}})
            check("chained-origin", second["reuse"]["original_receipt"] == old)
            check("identity-rejected", load({}, "another") is None)
            check("digest-rejected", load({}, digest="tampered") is None)
        with patch.object(module, "reusable", return_value=False):
            check("ineligible-rejected", load({}) is None)
elif kind == "interrupt-cleanup":
    from benchmark_runner import runtime as module
    module.DEADLINE = None
    for interrupted, label in [(KeyboardInterrupt(), "interrupt"), (subprocess.TimeoutExpired(["test"], 2), "timeout")]:
        for stubborn in [False, True]:
            process = MagicMock(); process.pid = 12345; process.returncode = 0
            process.__enter__.return_value = process
            responses = [interrupted]
            if stubborn: responses.append(subprocess.TimeoutExpired(["test"], 5))
            responses.append(("drained", None))
            process.communicate.side_effect = responses
            caught = None
            with patch.object(module.subprocess, "Popen", return_value=process) as popen, patch.object(module.os, "killpg") as kill:
                try: module.command(["test"], timeout=2)
                except BaseException as error: caught = error
            calls = [call.args for call in kill.call_args_list]
            required = [(12345, signal.SIGTERM)] + ([(12345, signal.SIGKILL)] if stubborn else [])
            grace = process.communicate.call_args_list[1].kwargs.get("timeout") if process.communicate.call_count > 1 else None
            check(f"{label}-bounded-grace-{stubborn}", isinstance(grace, (int, float)) and 0 < grace <= 10)
            check(f"{label}-{'stubborn' if stubborn else 'graceful'}", isinstance(caught, type(interrupted)) and calls == required and process.communicate.call_count == len(responses) and popen.call_args.kwargs.get("start_new_session") is True)
            if label == "timeout": check(f"{label}-output-{stubborn}", getattr(caught, "output", None) == "drained")
    process = MagicMock(); process.__enter__.return_value = process; process.returncode = 0; process.communicate.return_value = ("ok", None)
    with patch.object(module.subprocess, "Popen", return_value=process):
        check("successful-command", module.command(["test"]).stdout == "ok")
elif kind == "floating-builder":
    path = Path('/workspace/docker/benchmark/openviking.Dockerfile')
    lines = path.read_text().splitlines(); original = Path('/original/docker/benchmark/openviking.Dockerfile').read_text().splitlines()
    check("floating-stable-distribution", bool(re.fullmatch(r"FROM\s+rust:(?:stable-)?trixie\s+AS\s+rust-toolchain\s*", lines[0], re.IGNORECASE)))
    check("unrelated-instructions-preserved", lines[1:] == original[1:])
else: raise ValueError("unknown task")
print(json.dumps({"checks": checks, "passed": all(c["passed"] for c in checks)}))
sys.exit(0 if all(c["passed"] for c in checks) else 1)
