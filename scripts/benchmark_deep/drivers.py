"""Native operations used by the shared-store capability protocol."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import uuid
from pathlib import Path


INGEST_TIMEOUT_SECONDS = 5400
ACTION_TIMEOUT_SECONDS = 1200


def rust_action(target, action, root):
    scope = action["scope"]
    store = root / "inputs" / scope
    store.mkdir(parents=True, exist_ok=True)
    corpus = root / (scope + ".corpus.json")
    if action["action"] == "ingest":
        corpus.write_text(json.dumps(action["items"]))
    job = {"schema": "elf.real_world_job/v1", "suite": "retrieval",
        "job_id": scope, "title": "Capability experiment", "memory_evolution": None,
        "corpus": {"items": json.loads(corpus.read_text())},
        "prompt": {"content": action.get("question", "Which operational decisions are recorded?")},
        "operations": []}
    if action["action"] in {"update", "delete"}:
        job["operations"] = [{"type": action["action"], "evidence_id": action["evidence_id"],
                              **({"text": action["text"]} if "text" in action else {})}]
    (store / "job.json").write_text(json.dumps(job))
    receipt = root / "native" / action["operation_id"]
    receipt.mkdir(parents=True)
    args = [os.environ.get("BENCHMARK_NATIVE_ADAPTER", "/usr/local/bin/real_world_live_adapter"), target,
        "--fixtures", str(store), "--out-fixtures", str(receipt / "fixtures"),
        "--evidence-out", str(receipt / "evidence.json"), "--work-dir", str(root / "native-state"),
        "--adapter-id", "elf-deep-v1"]
    env = dict(os.environ)
    if target == "elf":
        args += ["--config", "/opt/elf/elf.docker.toml"]
        env["ELF_REAL_WORLD_EXTERNAL_EMBEDDING"] = "1"
    else:
        from benchmark_targets.rust import QMD_REVISION

        args += ["--qmd-dir", os.environ.get("QMD_CHECKOUT", "/opt/qmd"),
                 "--qmd-revision", QMD_REVISION, "--rerank", "--shared-index"]
        for role, model in json.loads(Path(os.environ.get("QMD_MODEL_MANIFEST", "/opt/qmd-models.json")).read_text()).items():
            env[f"QMD_{role.upper()}_MODEL"] = model["path"]
    if action["action"] != "ingest":
        args += ["--reuse-index"]
    with (receipt / "process.log").open("w") as log:
        result = subprocess.run(args, env=env, stdout=log, stderr=subprocess.STDOUT,
            timeout=INGEST_TIMEOUT_SECONDS if action["action"] == "ingest" else ACTION_TIMEOUT_SECONDS)
    if not (receipt / "evidence.json").exists():
        raise RuntimeError(f"native {target} process exited {result.returncode}; see process.log")
    evidence = json.loads((receipt / "evidence.json").read_text())
    job_result = evidence["jobs"][0]
    if job_result.get("failure"):
        raise RuntimeError(job_result["failure"])
    return {"contexts": job_result.get("contexts", []), "native": evidence,
            "process_exit": result.returncode, "native_pid_boundary": True}


def hindsight_action(action, root):
    from benchmark_targets.hindsight import request, ready, drain, recall

    ready()
    bank = "/v1/default/banks/deep-" + action["scope"]
    kind = action["action"]
    if kind == "ingest":
        request("PUT", bank, {})
        receipts = []
        # Native batch calls share the same bank and index; avoid oversized requests.
        for offset in range(0, len(action["items"]), 20):
            native = request("POST", bank + "/memories", {"async": False, "items": [
                {"content": item["text"], "document_id": item["evidence_id"]}
                for item in action["items"][offset:offset+20]]})
            receipts.append(native)
            (root / (action["scope"] + "-ingest-progress.json")).write_text(json.dumps(receipts))
            if native.get("success") is not True:
                raise RuntimeError("Hindsight native retain failed")
        return {"native": receipts, "readiness": drain(bank)}
    if kind == "query":
        row, native = recall({"job_id": action["case_id"], "prompt": {"content": action["question"]}}, bank, [])
        return {"contexts": row["contexts"], "native": native}
    if kind == "update":
        native = request("POST", bank + "/memories", {"async": False, "items": [{
            "content": action["text"], "document_id": action["evidence_id"], "update_mode": "replace"}]})
    else:
        native = request("DELETE", bank + "/documents/" + action["evidence_id"])
    if native.get("success") is not True:
        raise RuntimeError("Hindsight native mutation did not succeed")
    return {"native": native, "readiness": drain(bank)}


def run_action(target, action, root):
    if target in {"files-search", "no-memory"}:
        from benchmark_runner.baselines import retrieve

        path = root / "files-shared.json"
        store = json.loads(path.read_text()) if path.exists() else {}
        scope, kind = action["scope"], action["action"]
        if kind == "ingest":
            store[scope] = {item["evidence_id"]: item for item in action["items"]}
        elif kind == "query":
            return {"contexts": retrieve(list(store[scope].values()), action["question"], target),
                    "boundary": "Application scope filter in a shared JSON file; no ACL claim"}
        elif kind == "update":
            store[scope][action["evidence_id"]] = {"evidence_id": action["evidence_id"], "text": action["text"]}
        else:
            del store[scope][action["evidence_id"]]
        path.write_text(json.dumps(store))
        return {"native": {"scope": scope, "documents": len(store[scope])}}
    if target in {"elf", "qmd"}:
        return rust_action(target, action, root)
    if target == "hindsight":
        return hindsight_action(action, root)
    if target == "gbrain":
        return gbrain_action(action, root)
    if target == "mem0":
        return mem0_action(action, root)
    if target == "sag-engine":
        import asyncio

        return asyncio.run(sag_action(action, root))
    raise ValueError(f"Deep native driver is not implemented for {target}")


def gbrain_action(action, root):
    from benchmark_targets.gbrain import invoke

    home = root / "gbrain-shared"
    marker = root / "gbrain-ready"
    if not marker.exists():
        invoke(home, ["init", "--pglite", "--non-interactive", "--db-only",
            "--embedding-model", "openrouter:" + os.environ["EMBEDDING_MODEL"],
            "--embedding-dimensions", os.environ["EMBEDDING_DIMENSIONS"], "--json"])
        marker.write_text("initialized")
    scope, kind = action["scope"], action["action"]
    suffix = ["--source-id", scope, "--json"]
    if kind == "ingest":
        content = root / "gbrain-content" / scope
        content.mkdir(parents=True)
        for item in action["items"]:
            (content / (item["evidence_id"] + ".md")).write_text(item["text"] + "\n")
        # Current GBrain source registration requires committed source files.
        for args in (["init"], ["add", "."], ["-c", "user.name=ELF Benchmark",
                "-c", "user.email=benchmark@example.invalid", "-c", "commit.gpgsign=false",
                "commit", "-m", "Add synthetic benchmark corpus"]):
            subprocess.run(["git", "-C", str(content), *args], check=True, capture_output=True)
        registered, _ = invoke(home, ["sources", "add", scope, "--path", str(content)], json_output=False)
        native, elapsed = invoke(home, ["import", str(content), *suffix])
        return {"native": native, "registered": registered, "native_ms": elapsed}
    if kind == "query":
        native, elapsed = invoke(home, ["search", action["question"], "--limit", "5",
            "--snippet-chars", "0", "--fields", "full", *suffix])
        return {"native": native, "native_ms": elapsed,
            "contexts": [{"evidence_id": row["slug"], "text": row["chunk_text"]} for row in native]}
    before, _ = invoke(home, ["get", action["evidence_id"], "--include-content", *suffix])
    args = ["put" if kind == "update" else "delete", action["evidence_id"],
            "--expected-revision", before["revision"], "--request-id", str(uuid.uuid4()), *suffix]
    if kind == "update":
        args += ["--content", action["text"]]
    native, _ = invoke(home, args)
    refresh = None
    if kind == "update":
        refresh, _ = invoke(home, ["embed", "--stale", "--max-usd", "0.05", *suffix])
    readback, _ = invoke(home, ["get", action["evidence_id"], "--include-content", "--include-deleted", *suffix])
    return {"native": native, "refresh": refresh, "readback": readback}


def mem0_action(action, root):
    from mem0 import Memory
    from benchmark_targets.mem0 import mem0_config, mem0_entries, mem0_contexts, created_memory_ids
    from benchmark_targets.unit_runtime import wait_port

    wait_port("qdrant", 6333)
    memory = Memory.from_config(mem0_config(root, "elf-deep-shared"))
    kind, scope = action["action"], action["scope"]
    path = root / (scope + "-mem0-ids.json")
    if kind == "ingest":
        ids, receipts = {}, []
        for item in action["items"]:
            native = memory.add(item["text"], user_id=scope,
                metadata={"evidence_id": item["evidence_id"]}, infer=True)
            ids[item["evidence_id"]] = created_memory_ids(native)
            receipts.append(native)
            path.write_text(json.dumps(ids))
            (root / (scope + "-mem0-progress.json")).write_text(json.dumps(receipts))
        return {"native": receipts, "extracted_id_count": sum(map(len, ids.values()))}
    if kind == "query":
        native = memory.search(action["question"], user_id=scope, limit=5)
        return {"native": native, "contexts": mem0_contexts(mem0_entries(native))}
    ids = json.loads(path.read_text())[action["evidence_id"]]
    if not ids:
        raise RuntimeError("Native extraction retained no identity for this source")
    receipts, readback = [], []
    for memory_id in ids:
        if kind == "update":
            receipts.append(memory.update(memory_id, action["text"], metadata={"evidence_id": action["evidence_id"]}))
        else:
            receipts.append(memory.delete(memory_id))
        readback.append(memory.get(memory_id))
    return {"native": receipts, "readback": readback}


async def sag_action(action, root):
    from zleap.sag import DataEngine
    from zleap.sag.operations import DeleteSourceRequest, OperationContext
    from benchmark_targets.sag_engine import configuration, ingest, search

    scope, kind = action["scope"], action["action"]
    async with DataEngine(configuration(root / "sag-shared"), data_source_id=scope) as engine:
        if kind == "ingest":
            receipts = []
            for item in action["items"]:
                receipts.append(await ingest(engine, scope, item))
                (root / (scope + "-sag-progress.json")).write_text(json.dumps(receipts))
            return {"native": receipts}
        if kind == "query":
            row, native = await search(engine, scope, {
                "job_id": action["case_id"], "prompt": {"content": action["question"]}}, [])
            return {"contexts": row["contexts"], "native": native}
        if kind == "update":
            return {"native": await ingest(engine, scope, action)}
        token = str(uuid.uuid4())
        result = await engine.delete_source(DeleteSourceRequest(data_source_id=scope,
            source_id=action["evidence_id"], context=OperationContext(
                operation_id=token, idempotency_key=token, owner_id="elf-benchmark",
                fence_scope=f"source:{scope}:{action['evidence_id']}", fence_token=1,
                request_digest=hashlib.sha256(json.dumps(action, sort_keys=True).encode()).hexdigest())))
        native = result.model_dump(mode="json")
        if native["status"] != "succeeded":
            raise RuntimeError("SAG native deletion did not succeed")
        return {"native": native}
