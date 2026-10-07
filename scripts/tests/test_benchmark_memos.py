"""A successful HTTP response does not establish a successful MemOS mutation."""
from scripts.tests.benchmark_support import BenchmarkCase
from benchmark_targets import memos
from unittest.mock import patch
from pathlib import Path
import tempfile
import json


class MemOSReceiptTests(BenchmarkCase):
    def test_delete_failure_with_code_200_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); inputs = root / "input"; inputs.mkdir()
            job = {"job_id": "j_one", "prompt": {"content": "question"},
                "corpus": {"items": [{"evidence_id": "e_one", "text": "fact"}]},
                "operations": [{"type": "delete", "evidence_id": "e_one"}]}
            (inputs / "job.json").write_text(json.dumps(job))
            def recall(job, scope, operations):
                return {"job_id": job["job_id"], "classification": "completed", "operations": operations}, {}
            with patch.object(memos, "ready"), patch.object(memos, "add", return_value={"code":200}), \
                 patch.object(memos, "recall", side_effect=recall), \
                 patch.object(memos, "source_readback", side_effect=[([{"id":"m_one"}],{}),([], {})]), \
                 patch.object(memos, "request", return_value={"code":200,"data":{"status":"failure"}}):
                result = memos.run_memos(inputs, root / "artifacts", root / "state")
            self.assertFalse(result["phases"]["warm"]["jobs"][0]["operations"][0]["native_success"])
