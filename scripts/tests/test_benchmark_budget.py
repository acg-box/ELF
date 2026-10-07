"""Verify monetary reservations and native protocol framing without paid calls."""

import concurrent.futures
import json
import math
from pathlib import Path
import tempfile
from unittest import TestCase

from scripts.tests.benchmark_support import REPO
from benchmark_budget import Ledger, buffered_events, prepare_request, reservation, totals


class BudgetTests(TestCase):
    def test_unknown_and_invalid_costs_cannot_release_reservations(self):
        for cost in (None, -1, math.nan, "0"):
            ledger = {"prior_paid_usd": 0.1, "requests": [{
                "reserved_usd": 0.02, "status": "completed_cost_unknown", "usage": {"cost": cost}}]}
            paid, exposure = totals(ledger)
            self.assertEqual(paid, 0.1)
            self.assertAlmostEqual(exposure, 0.12)
        ledger["requests"][0].update(status="completed", usage={"cost": 0.001})
        self.assertAlmostEqual(totals(ledger)[1], 0.101)

    def test_parallel_reservations_share_one_ceiling_and_survive_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.json"
            ledger = Ledger(path, 0.125, 0.0625)
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                rows = list(pool.map(lambda _: ledger.reserve(0.03125, "chat"), range(8)))
            self.assertEqual(sum(row is not None for row in rows), 2)
            restarted = Ledger(path, 0.125, 0.0625)
            self.assertIsNotNone(restarted.reserve(0.03125, "chat"))
            self.assertIsNotNone(restarted.reserve(0.03125, "chat"))
            self.assertIsNone(restarted.reserve(0.03125, "chat"))
            self.assertEqual(totals(json.loads(path.read_text())), (0, 0.125))

    def test_profile_controls_routing_output_and_multiple_choices(self):
        body, streaming, limit = prepare_request({"model": "other", "stream": True,
            "max_completion_tokens": 50000, "provider": {"allow_fallbacks": True}}, "chat")
        self.assertTrue(streaming)
        self.assertFalse(body["stream"])
        self.assertEqual(limit, 8192)
        self.assertEqual(body["model"], "deepseek/deepseek-v4.1-flash")
        self.assertEqual(body["provider"]["only"], ["deepseek"])
        self.assertFalse(body["provider"]["allow_fallbacks"])
        self.assertNotIn("max_completion_tokens", body)
        with self.assertRaises(ValueError):
            prepare_request({"n": 2}, "chat")
        self.assertGreater(reservation(10000, "chat", 8192), 0.015)

    def test_buffered_sse_preserves_tool_arguments_usage_and_completion(self):
        result = {"id": "completion", "model": "model", "created": 1,
            "choices": [{"message": {"role": "assistant", "content": None,
                "tool_calls": [{"id": "call", "type": "function", "function": {
                    "name": "read", "arguments": '{"path":"source.py"}'}}]}, "finish_reason": "tool_calls"}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 10, "cost": 0.001}}
        events = buffered_events(result).decode().split("\n\n")
        first, last = [json.loads(event.removeprefix("data: ")) for event in events[:2]]
        call = first["choices"][0]["delta"]["tool_calls"][0]
        self.assertEqual(call["index"], 0)
        self.assertEqual(json.loads(call["function"]["arguments"]), {"path": "source.py"})
        self.assertEqual(last["choices"][0]["finish_reason"], "tool_calls")
        self.assertEqual(last["usage"], result["usage"])
        self.assertEqual(events[2], "data: [DONE]")
