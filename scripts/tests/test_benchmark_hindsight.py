"""Do not declare Hindsight ready while native operations remain incomplete."""

from pathlib import Path
from unittest.mock import patch

from scripts.tests.benchmark_support import BenchmarkCase
from benchmark_targets import hindsight


class HindsightTests(BenchmarkCase):
    def test_observation_keeps_native_parent_provenance_without_corpus_fallback(self):
        native = {"results": [{"type": "observation", "text": "Combined native fact",
                    "source_fact_ids": ["f1"], "document_id": None}],
                  "source_facts": {"f1": {"document_id": "e_one", "text": "Native parent fact"}}}
        job = {"job_id": "j_one", "prompt": {"content": "query"},
               "corpus": {"items": [{"evidence_id": "e_one", "text": "Do not substitute this corpus text"}]}}
        with patch.object(hindsight, "request", return_value=native) as request:
            row, _ = hindsight.recall(job, "/bank", [])
        self.assertEqual(row["evidence_ids"], ["e_one"])
        self.assertIn("Combined native fact", row["contexts"][0]["text"])
        self.assertNotIn("Native parent fact", row["contexts"][0]["text"])
        self.assertIsNone(row["contexts"][0]["evidence_id"])
        self.assertEqual(row["contexts"][0]["source_evidence_ids"], ["e_one"])
        self.assertEqual(row["contexts"][1], {"evidence_id": "e_one", "text": "Native parent fact"})
        self.assertNotIn("substitute", row["contexts"][0]["text"])
        self.assertIn("source_facts", request.call_args.args[2]["include"])
        native["source_facts"] = {}
        with patch.object(hindsight, "request", return_value=native):
            row, _ = hindsight.recall(job, "/bank", [])
        self.assertEqual(row["evidence_ids"], [])
        self.assertEqual(row["contexts"], [{"evidence_id": None, "text": "Derived observation: Combined native fact", "source_evidence_ids": []}])

    def test_observation_is_not_broadcast_to_each_document_and_facts_are_deduplicated(self):
        native = {"results": [
            {"text": "Derived summary", "source_fact_ids": ["f1", "f2"]},
            {"text": "Second summary", "source_fact_ids": ["f1", "f2"]}],
            "source_facts": {"f1": {"document_id": "a", "text": "A"},
                             "f2": {"document_id": "b", "text": "B"}}}
        rows = hindsight.contexts_from_native(native)
        self.assertEqual(len(rows), 4)
        self.assertEqual([r["text"] for r in rows if r["evidence_id"]], ["A", "B"])
        self.assertTrue(all(r["evidence_id"] is None for r in rows if "summary" in r["text"]))
        self.assertEqual(rows[0]["source_evidence_ids"], ["a", "b"])

    def test_drain_waits_for_processing_and_rejects_cancelled_work(self):
        calls = []

        def response(method, path):
            calls.append(path)
            return {"operations": [{"status": "processing"}] if len(calls) == 2 else []}

        with patch.object(hindsight, "request", side_effect=response), \
                patch.object(hindsight.time, "sleep") as sleep:
            result = hindsight.drain("/bank")
        self.assertEqual(len(calls), 8)
        self.assertEqual(result["processing"]["operations"], [])
        sleep.assert_called_once_with(1)
        with patch.object(hindsight, "request", side_effect=lambda method, path: {
                "operations": [{}] if "cancelled" in path else []}):
            with self.assertRaisesRegex(RuntimeError, "background operation failed"):
                hindsight.drain("/bank")

    def test_missing_queue_shape_cannot_pass_readiness(self):
        with patch.object(hindsight, "request", return_value={}):
            with self.assertRaises(KeyError):
                hindsight.drain("/bank")
