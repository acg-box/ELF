"""Tool-boundary tests for the repository repair pilot."""
from pathlib import Path
import sys
import io
import json
from unittest.mock import patch
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark_replay.agent import act, source_path, request, run, ProviderResponseError
from benchmark_replay.memory import bounded, lexical

class ReplayBoundaryTests(unittest.TestCase):
    def test_read_and_write_allowlists(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'source.py').write_text('before\n'); (root/'other.py').write_text('keep\n')
            task={'path':'source.py'}
            with self.assertRaises(ValueError): source_path(root, '../secret', ['source.py'])
            with self.assertRaises(ValueError): act({'action':'replace','path':'other.py','old':'keep','new':'lost'},task,root,root,['source.py','other.py'])
            act({'action':'replace','path':'source.py','old':'before','new':'after'},task,root,root,['source.py'])
            self.assertEqual((root/'source.py').read_text(),'after\n')
            self.assertEqual((root/'other.py').read_text(),'keep\n')
    def test_ambiguous_replace_does_not_mutate(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'a').write_text('same same')
            with self.assertRaises(ValueError): act({'action':'replace','path':'a','old':'same','new':'changed'},{'path':'a'},root,root,['a'])
            self.assertEqual((root/'a').read_text(),'same same')
    def test_context_budget_and_query_ranking(self):
        rows=[{'id':'b','text':'irrelevant text'}, {'id':'a','text':'subprocess cleanup'}]
        self.assertEqual(lexical(rows,'cleanup')[0]['evidence_id'],'a')
        self.assertEqual(sum(len(r['text']) for r in bounded([{'text':'abcdef'},{'text':'ghijk'}],8)),8)

    def test_truncated_response_retains_billed_usage(self):
        payload = {"choices": [{"message": {"content": None}, "finish_reason": "length"}],
                   "usage": {"cost": 0.001, "completion_tokens": 2048}}
        with patch.dict("os.environ", {"LITELLM_BASE_URL": "http://localhost/v1", "LITELLM_API_KEY": "fixture"}), patch(
            "urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())
        ):
            with self.assertRaises(ProviderResponseError) as caught:
                request([])
        self.assertEqual(caught.exception.receipt["usage"], payload["usage"])
        self.assertEqual(caught.exception.receipt["finish_reason"], "length")

    def test_invalid_json_consumes_a_turn_and_keeps_usage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch("benchmark_replay.agent.request", side_effect=[
                ProviderResponseError("invalid model action", {"usage": {"cost": 0.001}}, "{bad"),
                ({"action": "finish", "summary": "done"}, {"usage": {"cost": 0.002}}),
            ]) as provider, patch("benchmark_replay.agent.check", return_value={"passed": False}):
                result = run({"id": "fixture", "request": "repair", "path": "a"}, root, root, [], steps=2)
            self.assertEqual(result["turns"], 2)
            self.assertEqual(result["trace"][0]["provider"]["usage"]["cost"], 0.001)
            self.assertEqual(result["classification"], "completed")
            self.assertFalse(result["passed"])
            self.assertEqual(provider.call_count, 2)
