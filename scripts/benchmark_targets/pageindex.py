"""PageIndex local PDF indexing and native tool-using question answering."""

from __future__ import annotations

import importlib.metadata
import json
import os
import time
from pathlib import Path
from unittest.mock import patch
from xml.sax.saxutils import escape

from .unit_runtime import write_json


def write_pdf(path, text):
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate

    SimpleDocTemplate(str(path)).build([
        Paragraph(escape(text).replace("\n", "<br/>"), getSampleStyleSheet()["BodyText"])])


def query(client, job, doc_ids, operations, names):
    from pageindex import agent_tools

    traces = []
    original = agent_tools.call_tool

    def traced(client, name, arguments, *args, **kwargs):
        result, failed = original(client, name, arguments, *args, **kwargs)
        traces.append({"name": name, "arguments": arguments,
                       "result": json.loads(result), "failed": failed})
        return result, failed

    started = time.monotonic()
    with patch.object(agent_tools, "call_tool", traced):
        answer = client.chat(job["prompt"]["content"], doc_id=list(doc_ids.values()),
            protocol="chat_completions", citations=True, max_turns=12,
            reasoning_effort=os.environ["CHAT_REASONING_EFFORT"], stream=False)
    contexts = []
    for trace in traces:
        if trace["failed"] or trace["name"] not in {
            "get_page_content", "get_document_structure", "get_document"}:
            continue
        name = (trace["arguments"] or {}).get("doc_name")
        evidence_id = names.get(name)
        if evidence_id:
            contexts.append({"evidence_id": evidence_id,
                             "text": json.dumps(trace["result"], ensure_ascii=False)})
    return {"job_id": job["job_id"], "classification": "completed",
        "evidence_ids": list(dict.fromkeys(c["evidence_id"] for c in contexts)),
        "contexts": contexts, "returned_count": len(contexts),
        "latency_ms": (time.monotonic() - started) * 1000,
        "operations": operations, "native_status": "completed", "failure": None}, {
            "answer": answer, "tool_calls": traces}


def run_pageindex(inputs: Path, artifacts: Path, state: Path):
    from pageindex import PageIndexLocalClient

    version = importlib.metadata.version("pageindex")
    if version != "0.2.21":
        raise ValueError("PageIndex package differs from the frozen comparison version")
    phases = {phase: {"status": "completed", "jobs": []} for phase in ("cold", "warm")}
    receipts = []
    ingest_ms = 0.0
    for path in sorted(inputs.glob("*.json")):
        job = json.loads(path.read_text())
        home = state / job["job_id"]
        home.mkdir(parents=True)
        backend = {"api_key": os.environ["CHAT_API_KEY"], "api_base": os.environ["CHAT_API_BASE"]}
        model = "openai/" + os.environ["CHAT_MODEL"]
        client = PageIndexLocalClient(index_model=model, chat_model=model,
            index_backend=backend, chat_backend=backend,
            storage_path=str(home / "index"), summary_concurrency=1)
        docs, names = {}, {}
        receipt = {"job_id": job["job_id"], "ingest": [], "operations": []}
        receipts.append(receipt)

        def add(item):
            pdf = home / (item["evidence_id"] + ".pdf")
            write_pdf(pdf, item["text"])
            result = client.submit_document(str(pdf), wait=True)
            docs[item["evidence_id"]] = result["doc_id"]
            names[result["name"]] = item["evidence_id"]
            return result

        started = time.monotonic()
        for item in job["corpus"]["items"]:
            receipt["ingest"].append(add(item))
            write_json(artifacts / "raw/pageindex-local-receipts.json", receipts)
        ingest_ms += (time.monotonic() - started) * 1000
        cold, receipt["cold"] = query(client, job, docs, [], names)
        phases["cold"]["jobs"].append(cold)
        operations = []
        for op in job.get("operations", []):
            from pageindex.errors import PageIndexAPIError

            old_id = docs.pop(op["evidence_id"])
            deleted = client.delete_document(old_id)
            try:
                client.get_document(old_id)
            except PageIndexAPIError as error:
                if "Document not found" not in str(error):
                    raise
                readback = {"document_absent": True, "native_error": str(error)}
            else:
                raise RuntimeError("PageIndex deleted document remains readable")
            replacement = add(op) if op["type"] == "update" else None
            operations.append({"requested_type": op["type"],
                "native_type": "replace_document" if replacement else "delete_document",
                "classification": "completed", "native_success": True})
            receipt["operations"].append({"operation": op, "delete": deleted,
                                          "readback": readback, "replace": replacement})
        warm, receipt["warm"] = query(client, job, docs, operations, names)
        phases["warm"]["jobs"].append(warm)
        write_json(artifacts / "raw/pageindex-local-receipts.json", receipts)
    return {"schema": "elf.benchmark_unit_result/v4", "target": "pageindex",
        "native_mode": "native_local_pdf_agent", "score_eligible": True,
        "result_class": "completed", "warm_reused_state": True, "ingest_count": 1,
        "ingest_duration_ms": ingest_ms, "phases": phases, "package_version": version}
