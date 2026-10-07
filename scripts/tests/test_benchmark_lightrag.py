"""Native LightRAG provenance, isolation and deletion readback contracts."""
from scripts.tests.benchmark_support import BenchmarkCase
from benchmark_targets import lightrag as L
from pathlib import Path
from unittest import mock
import json
import tempfile


class BenchmarkLightragTests(BenchmarkCase):
    def test_context_is_native_even_when_unmapped(self):
        rows = L.native_contexts({"references": [
            {"file_path": "e_a.md", "content": ["native stale value"]},
            {"file_path": "foreign.md", "content": ["foreign canary"]}]}, {"e_a": "doc-a"})
        self.assertEqual(rows, [{"evidence_id": "e_a", "text": "native stale value"},
                                {"evidence_id": None, "text": "foreign canary"}])

    def test_retained_document_makes_deletion_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); inputs = root / "input"; inputs.mkdir()
            job = {"job_id": "j_a", "suite": "memory_lifecycle",
                "prompt": {"content": "Which fact remains?"},
                "corpus": {"items": [{"evidence_id": "e_a", "text": "private fact"}]},
                "operations": [{"type": "delete", "evidence_id": "e_a"}]}
            (inputs / "job.json").write_text(json.dumps(job))
            def request(method, path, value=None):
                if path == "/documents": return {"status": "success"}
                if path == "/documents/delete_document": return {"status": "deletion_started"}
                raise AssertionError(path)
            cold = {"job_id": "j_a", "classification": "completed", "contexts": []}
            with mock.patch.object(L, "wait_port"), mock.patch.object(L, "drain"), \
                 mock.patch.object(L, "request", side_effect=request), \
                 mock.patch.object(L, "ingest", return_value=({"e_a": "doc-a"}, {})), \
                 mock.patch.object(L, "query", return_value=(cold, {})), \
                 mock.patch.object(L, "documents", return_value=[{"id": "doc-a"}]):
                result = L.run_lightrag_target(inputs, root / "artifacts", root / "state")
            self.assertEqual(result["phases"]["cold"]["jobs"][0]["classification"], "completed")
            self.assertEqual(result["phases"]["warm"]["jobs"][0]["classification"], "adapter_failed")
            self.assertIn("remains", result["phases"]["warm"]["jobs"][0]["failure"])

    def test_all_suite_modes_have_native_queries(self):
        self.assertEqual(L.lightrag_query_mode({"suite": "retrieval"}), "naive")
        self.assertEqual(L.lightrag_query_mode({"suite": "knowledge_structure"}), "mix")
        self.assertEqual(L.lightrag_query_mode({"suite": "memory_lifecycle"}), "naive")
        self.assertEqual(L.lightrag_query_mode({"suite": "repository_knowledge"}), "mix")
