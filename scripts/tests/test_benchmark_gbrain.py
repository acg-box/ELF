"""Check mutation ordering and strict native context use without paid calls."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.tests.benchmark_support import BenchmarkCase
from benchmark_targets import gbrain


class GBrainTests(BenchmarkCase):
    def test_update_preserves_immediate_readback_and_refreshes_before_warm(self):
        commands = []

        def native(home, args):
            commands.append(args[0])
            if args[0] == "get":
                return {"revision": "r1", "content": "new value"}, 1
            if args[0] == "search":
                return [{"slug": "e_one", "chunk_text": "native text"}], 1
            return {}, 1

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = root / "inputs"
            inputs.mkdir()
            (inputs / "job.json").write_text(json.dumps({
                "job_id": "j_one", "corpus": {"items": [
                    {"evidence_id": "e_one", "text": "old value"}]},
                "prompt": {"content": "current value?"},
                "operations": [{"type": "update", "evidence_id": "e_one",
                                "text": "new value"}],
            }))
            with patch.dict("os.environ", {"EMBEDDING_MODEL": "test",
                                            "EMBEDDING_DIMENSIONS": "1536"}), \
                    patch.object(gbrain, "invoke", side_effect=native):
                result = gbrain.run_gbrain(inputs, root / "artifacts", root / "state")
            receipt = json.loads((root / "artifacts/raw/gbrain-receipts.json").read_text())[0]
        self.assertEqual(commands, ["init", "import", "search", "get", "put",
                                    "get", "search", "embed", "search"])
        self.assertEqual(receipt["immediate"]["contexts"][0]["text"], "native text")
        warm = result["phases"]["warm"]["jobs"][0]
        self.assertTrue(warm["operations"][0]["native_success"])
        self.assertEqual(warm["contexts"][0]["text"], "native text")

    def test_search_does_not_synthesize_missing_native_context(self):
        with patch.object(gbrain, "invoke", return_value=([{"slug": "e_one"}], 1)):
            with self.assertRaises(KeyError):
                gbrain.search({"job_id": "j_one", "prompt": {"content": "q"}}, Path("/tmp"), [])


if __name__ == "__main__":
    unittest.main()
