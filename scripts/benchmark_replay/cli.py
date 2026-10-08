"""Prepare, validate, and execute paired repository repair trials."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from . import agent, memory
from .tasks import TASKS, ROOT, experience, snapshot
from benchmark_contract.fixtures import PRODUCT_IDS, OPTIONAL_PRODUCT_IDS

ARMS = ["no-memory", "files-search", "git-memory", "elf"]


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["prepare", "validate", "learn", "retrieve", "run", "report"])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--arm", choices=sorted(set(ARMS) | PRODUCT_IDS | OPTIONAL_PRODUCT_IDS))
    parser.add_argument("--target", choices=sorted(PRODUCT_IDS | OPTIONAL_PRODUCT_IDS))
    parser.add_argument("--manifest", type=Path, default=ROOT / "config/benchmark/benchmark-v3.json")
    parser.add_argument("--repeat", type=int, choices=[1, 2])
    args = parser.parse_args(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    if args.phase == "prepare":
        if (out / "episodes.json").exists(): raise ValueError("refuse to replace an existing replay")
        episodes = []
        for task in TASKS:
            original = out / "source" / task["id"]
            provenance = snapshot(task, original)
            for repeat in [1, 2]:
                key = "j_" + hashlib.sha256(f"{task['id']}:{repeat}".encode()).hexdigest()[:24]
                episodes.append({"key": key, "repeat": repeat, "task": task, "source": provenance, "packet": experience(task, original)})
        save(out / "episodes.json", episodes)
        save(out / "protocol.json", {"arms": [args.target] if args.target else ARMS, "repeats": 2, "tasks": 3, "max_turns": 6,
            "boundary": "Controlled prior exploration from historical source, followed by real repair actions. Independent repeats; no persistent learning between repeats. Git memory is a model-maintained file baseline, not the Agent Memory Repo product.",
            "image_digest": subprocess.check_output(["docker", "image", "inspect", "--format", "{{.Id}}", agent.IMAGE], text=True).strip()})
    elif args.phase == "validate":
        results = []
        for task in TASKS:
            original = out / "source" / task["id"]
            fixed = out / "known-fixes" / task["id"]
            snapshot(task, fixed, fixed=True)
            before = agent.check(task, original, original); after = agent.check(task, fixed, original)
            results.append({"task": task["id"], "before": before, "reference_fix": after})
        save(out / "oracle-validation.json", results)
        if not all(not row["before"]["passed"] and row["reference_fix"]["passed"] for row in results): raise RuntimeError("historical oracle sensitivity failed")
    elif args.phase == "learn":
        receipts = []
        for episode in json.loads((out / "episodes.json").read_text()):
            receipt = memory.learn(episode["task"], episode["packet"], out / "git-memory" / episode["key"])
            receipts.append({"episode": episode["key"], **receipt}); save(out / "learning.json", receipts)
            print(json.dumps({"phase": "learn", "episode": episode["key"], "cost": receipt["usage"].get("cost")}), flush=True)
    elif args.phase == "retrieve":
        result = memory.native_retrieve(json.loads((out / "episodes.json").read_text()), out,
            args.target or "elf", json.loads(args.manifest.read_text()))
        save(out / "native-summary.json", {key: value for key, value in result.items() if key != "contexts"})
    elif args.phase == "run":
        if not args.arm or not args.repeat: raise ValueError("run requires an arm and repeat")
        episodes = json.loads((out / "episodes.json").read_text())
        for episode in episodes:
            if episode["repeat"] != args.repeat: continue
            task = episode["task"]; root = out / "trials" / args.arm / episode["key"]
            if root.exists(): raise ValueError("refuse to overwrite a measured trial")
            workspace = root / "workspace"; original = out / "source" / task["id"]
            shutil.copytree(original, workspace)
            if args.arm == "no-memory": contexts = []
            elif args.arm == "files-search": contexts = memory.lexical(episode["packet"], task["request"])
            elif args.arm == "git-memory":
                directory = out / "git-memory" / episode["key"]
                contexts = memory.bounded([{"evidence_id": path, "text": (directory / path).read_text()} for path in ["MEMORY.md", "notes/method.md"]])
            else:
                context_path = out / f"{args.arm}-contexts.json"
                retained = json.loads(context_path.read_text()) if context_path.exists() else {}
                if episode["key"] not in retained:
                    save(root / "result.json", {"task": task["id"], "repeat": args.repeat,
                        "arm": args.arm, "classification": "blocked_by_native_retrieval",
                        "passed": False, "turns": 0, "seconds": 0, "trace": [],
                        "failure": "Native retrieval did not produce completed evidence for this episode"})
                    continue
                contexts = retained[episode["key"]]
            save(root / "context.json", contexts)
            result = agent.run(task, workspace, original, contexts)
            result.update(task=task["id"], repeat=args.repeat, arm=args.arm, context_chars=sum(len(row["text"]) for row in contexts))
            save(root / "result.json", result)
            print(json.dumps({key: result[key] for key in ["task", "arm", "repeat", "passed", "turns", "seconds"]}), flush=True)
    else:
        rows = [json.loads(path.read_text()) for path in sorted((out / "trials").glob("*/*/result.json"))]
        save(out / "results.json", rows)
        summary = []
        arms = json.loads((out / "protocol.json").read_text())["arms"]
        for arm in arms:
            selected = [row for row in rows if row["arm"] == arm]
            blocked = sum(row.get("classification") == "blocked_by_native_retrieval" for row in selected)
            summary.append({"arm": arm, "completed_trials": len(selected)-blocked, "blocked_trials": blocked, "passed": sum(row["passed"] for row in selected), "turns": sum(row["turns"] for row in selected), "seconds": round(sum(row["seconds"] for row in selected), 3), "chat_cost": sum(turn.get("provider", {}).get("usage", {}).get("cost", 0) for row in selected for turn in row["trace"])})
        save(out / "summary.json", summary); print(json.dumps(summary, indent=2))
        if len(rows) != len(arms) * 6: raise RuntimeError("incomplete trial coverage")
    return 0
