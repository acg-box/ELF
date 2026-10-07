"""Historical repair tasks; source experiences contain no reference patch."""
from pathlib import Path
import hashlib
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TASKS = [
    {"id": "receipt-origin", "base": "86e68cff^", "fixed": "86e68cff",
     "path": "scripts/benchmark_runner/checkpoints.py",
     "topic": "Understand how benchmark receipts preserve measurement provenance across resumes.",
     "request": "Fix chained benchmark resumes: after saving a reused receipt and resuming again, original_receipt must still identify the first measured receipt. First reuse must record its absolute source path. Preserve identity, integrity and eligibility rejection behavior. Change only the checkpoint module."},
    {"id": "interrupt-cleanup", "base": "b7d2f925^", "fixed": "b7d2f925",
     "path": "scripts/benchmark_runner/runtime.py",
     "topic": "Understand the benchmark subprocess lifecycle, process groups and timeout cleanup.",
     "request": "Fix Ctrl-C handling in the benchmark command runner. KeyboardInterrupt must terminate the subprocess group, allow bounded graceful exit, escalate to SIGKILL if needed, drain output, then propagate KeyboardInterrupt. Preserve existing TimeoutExpired behavior and successful command results. Change only the runtime module."},
    {"id": "floating-builder", "base": "11fda482^", "fixed": "11fda482",
     "path": "docker/benchmark/openviking.Dockerfile",
     "topic": "Understand repository Rust channel conventions and the OpenViking container stages.",
     "request": "Update the OpenViking benchmark Rust builder to follow the unversioned stable Rust release on its existing Debian distribution. Do not select a numeric compiler version or nightly. Preserve the stage name, all subsequent Docker instructions, and the pinned OpenViking revision. Change only the OpenViking Dockerfile."},
]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def snapshot(task, destination, fixed=False):
    ref = task["fixed"] if fixed else task["base"]
    revision = git("rev-parse", ref).strip()
    paths = git("ls-tree", "-r", "--name-only", revision, "scripts/benchmark_runner", "scripts/benchmark_contract", "config/benchmark/suites", "makefiles/format.toml", "rust-toolchain.toml", "docker/benchmark/openviking.Dockerfile", "docs/runbook/agent-setup.md").splitlines()
    hashes = {}
    for name in paths:
        mode = git("ls-tree", revision, name).split()[0]
        if mode != "100644":
            raise ValueError("snapshot requires plain tracked files")
        content = git("show", f"{revision}:{name}")
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        hashes[name] = hashlib.sha256(content.encode()).hexdigest()
    return {"revision": revision, "files": hashes}


def experience(task, workspace):
    # A controlled prior-session packet assembled from source, not a claim to
    # reproduce an actual human conversation or to reveal the historical fix.
    paths = [task["path"], "scripts/benchmark_runner/checkpoints.py", "scripts/benchmark_runner/runtime.py", "makefiles/format.toml", "rust-toolchain.toml", "docker/benchmark/openviking.Dockerfile"]
    return [{"id": f"source-{index}", "path": path,
             "text": f"Source: {path}\n" + (workspace / path).read_text()}
            for index, path in enumerate(dict.fromkeys(paths))]
