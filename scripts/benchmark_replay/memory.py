"""Controlled experience storage; native ELF retrieval and a Git note baseline."""
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

from .agent import request
from .tasks import ROOT
from benchmark_runner.docker import cleanup_project
from benchmark_runner.providers import provider_environment


def learn(task, packet, directory):
    prompt = {"instruction": "Record concise reusable repository knowledge from this prior exploration. Do not repair code or predict a future task. Cite source paths; distinguish observed implementation from policy. Return JSON with memory_md (a short MEMORY.md linking notes/method.md) and method_md (source-grounded workflow notes). Total at most 1800 characters. Summarize the observed workflow; do not analyze fixes.", "topic": task["topic"], "sources": packet}
    content, receipt = request([{"role": "user", "content": json.dumps(prompt)}], 8192)
    if not all(isinstance(content.get(key), str) and content[key].strip() for key in ["memory_md", "method_md"]):
        raise ValueError("learner omitted its memory files")
    if sum(len(content[key]) for key in ["memory_md", "method_md"]) > 6000:
        raise ValueError("learner exceeded its file budget")
    directory.mkdir(parents=True)
    (directory / "notes").mkdir()
    (directory / "MEMORY.md").write_text(content["memory_md"])
    (directory / "notes/method.md").write_text(content["method_md"])
    subprocess.run(["git", "init", "--quiet", str(directory)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(directory), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(directory), "-c", "commit.gpgsign=false", "-c", "user.name=ELF Benchmark", "-c", "user.email=benchmark@example.invalid", "commit", "--quiet", "-m", "Record source exploration for the next session"], check=True, capture_output=True)
    receipt["git_commit"] = subprocess.check_output(["git", "-C", str(directory), "rev-parse", "HEAD"], text=True).strip()
    return receipt


def lexical(packet, query):
    terms = set(re.findall(r"\w+", query.lower()))
    ranked = sorted(packet, key=lambda row: (-len(terms & set(re.findall(r"\w+", row["text"].lower()))), row["id"]))
    return bounded([{"evidence_id": row["id"], "text": row["text"]} for row in ranked[:5]])


def bounded(rows, maximum=12000):
    result = []; used = 0
    for row in rows:
        text = row["text"][:maximum-used]
        if not text: break
        result.append({"evidence_id": row.get("evidence_id"), "text": text})
        used += len(text)
    return result


def elf_retrieve(episodes, output):
    return native_retrieve(episodes, output, "elf")


def native_retrieve(episodes, output, target, manifest=None):
    inputs = output / "native-input"; artifacts = output / "native-artifacts"
    inputs.mkdir(); artifacts.mkdir()
    for episode in episodes:
        fixture = {"schema": "elf.real_world_job/v1", "job_id": episode["key"], "suite": "retrieval", "title": "Repository follow-up task",
            "prompt": {"content": episode["task"]["request"]}, "corpus": {"items": [{"evidence_id": row["id"], "text": row["text"]} for row in episode["packet"]]}, "memory_evolution": None, "operations": []}
        (inputs / (episode["key"] + ".json")).write_text(json.dumps(fixture))
    if target == "qmd" and os.environ.get("QMD_CHECKOUT"):
        import hashlib
        import platform
        from benchmark_targets.rust import run_rust_target

        started = time.monotonic()
        (output / "native-runtime.json").write_text(json.dumps({"mode": "host QMD", "platform": platform.platform(),
            "adapter_sha256": hashlib.sha256(Path(os.environ["BENCHMARK_NATIVE_ADAPTER"]).read_bytes()).hexdigest(),
            "models": json.loads(Path(os.environ["QMD_MODEL_MANIFEST"]).read_text())}, indent=2))
        unit = run_rust_target("qmd", inputs, artifacts, output / "native-state")
        (artifacts / "unit-result.json").write_text(json.dumps(unit, indent=2))
        contexts = {row["job_id"]: bounded(row["contexts"]) for row in unit["phases"]["warm"]["jobs"]
                    if row["classification"] == "completed"}
        (output / "qmd-contexts.json").write_text(json.dumps(contexts, indent=2))
        (output / "native-cleanup.json").write_text(json.dumps({"passed": True, "mode": "host QMD processes exited"}))
        return {"seconds": time.monotonic()-started, "contexts": contexts,
                "native_status": unit["result_class"]}
    providers = {"chat": {"model": "deepseek/deepseek-v4.1-flash", "reasoning_effort": "low"}, "embedding": {"model": "qwen/qwen3-embedding-8b", "dimensions": 1536}}
    env = dict(os.environ); env.update(provider_environment(env, providers, inside_container=True))
    env.update(BENCHMARK_IMAGE=env.get("BENCHMARK_ELF_IMAGE", "elf-benchmark-elf:replay-drain"), BENCHMARK_ELF_IMAGE=env.get("BENCHMARK_ELF_IMAGE", "elf-benchmark-elf:replay-drain"), BENCHMARK_POSTGRES_PASSWORD=uuid.uuid4().hex,
        BENCHMARK_INPUT_HOST=str(inputs.resolve()), BENCHMARK_ARTIFACT_HOST=str(artifacts.resolve()))
    if manifest is not None:
        from benchmark_runner.docker import TARGET_IMAGE_ENV, image_id

        selected = next(row for row in manifest["targets"] if row["id"] == target)
        image = selected.get("image", manifest["runner"]["image"])
        env["BENCHMARK_IMAGE"] = image
        if target in TARGET_IMAGE_ENV:
            env[TARGET_IMAGE_ENV[target]] = image
        (output / "native-runtime.json").write_text(json.dumps({"target": selected,
            "image_digest": image_id(image), "providers": providers}, indent=2))
    project = "elf-replay-" + uuid.uuid4().hex[:12]; compose = ROOT / "docker/benchmark/compose.yml"
    started = time.monotonic()
    try:
        result = subprocess.run(["docker", "compose", "-p", project, "-f", str(compose), "run", "--rm", "--no-TTY", f"{target}-unit"], env=env, text=True, capture_output=True, timeout=1800)
        # Compose output is retained only after removing all process credentials.
        log = result.stdout + result.stderr
        for key in ["LITELLM_API_KEY", "EMBEDDING_API_KEY", "BENCHMARK_CHAT_API_KEY", "BENCHMARK_EMBEDDING_API_KEY", "BENCHMARK_POSTGRES_PASSWORD"]:
            if env.get(key): log = log.replace(env[key], "[redacted]")
        (output / "native.log").write_text(log)
        unit_path = artifacts / "unit-result.json"
        unit = json.loads(unit_path.read_text()) if unit_path.exists() else {}
        contexts = {row["job_id"]: bounded(row["contexts"])
                    for row in unit.get("phases", {}).get("warm", {}).get("jobs", [])
                    if row.get("classification") == "completed"}
        (output / f"{target}-contexts.json").write_text(json.dumps(contexts, indent=2))
    finally:
        cleanup = cleanup_project(project, compose, env)
        (output / "native-cleanup.json").write_text(json.dumps(cleanup, indent=2))
    if not cleanup["passed"]: raise RuntimeError("native memory cleanup failed")
    return {"seconds": round(time.monotonic()-started, 3), "contexts": contexts,
            "native_status": unit.get("result_class", "harness_failed"), "exit_code": result.returncode}
