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


class EmbeddingRecoveryTests(TestCase):
    def request(self, responses, kind="embedding", retries=3, tranche=1.0):
        import contextlib
        import http.client
        import io
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import Mock, patch
        from benchmark_budget import handler_for

        opener = Mock()
        opener.open.side_effect = responses
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            ledger = Ledger(Path(directory) / "ledger.json", 1, tranche)
            with patch("benchmark_budget.urllib.request.build_opener", return_value=opener), \
                    patch("benchmark_budget.time.sleep") as sleep:
                server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(ledger, "upstream-key", "local-token", retries))
                thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
                thread.start()
                client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                try:
                    route = "/v1/embeddings" if kind == "embedding" else "/v1/chat/completions"
                    client.request("POST", route, json.dumps({"input": "synthetic fact"}),
                        {"Authorization": "Bearer local-token", "Content-Type": "application/json"})
                    response = client.getresponse()
                    status, payload = response.status, json.loads(response.read())
                finally:
                    client.close()
                    server.shutdown()
                    server.server_close()
                    thread.join()
                return status, payload, ledger.value, opener.open.call_args_list, sleep.call_args_list

    @staticmethod
    def failure(status=429, retry_after=None):
        import io
        from urllib.error import HTTPError

        headers = {} if retry_after is None else {"Retry-After": retry_after}
        return HTTPError("https://provider.invalid", status, "failed", headers,
            io.BytesIO(b'{"error":{"message":"busy upstream-key local-token"}}'))

    @staticmethod
    def success():
        import io

        return io.BytesIO(b'{"data":[{"embedding":[0.1]}],"usage":{"cost":0.000001}}')

    def test_embedding_retry_keeps_request_and_charges_separate_attempts(self):
        status, payload, ledger, calls, sleeps = self.request([self.failure(retry_after="3"), self.success()])
        self.assertEqual(status, 200)
        self.assertEqual(payload["data"][0]["embedding"], [0.1])
        self.assertEqual(calls[0].args[0].data, calls[1].args[0].data)
        self.assertEqual([c.args[0] for c in sleeps], [3])
        rows = ledger["requests"]
        self.assertEqual([r["status"] for r in rows], ["provider_failed", "completed"])
        self.assertEqual([r["attempt"] for r in rows], [1, 2])
        self.assertEqual([r["request_ordinal"] for r in rows], [1, 1])
        self.assertNotIn("upstream-key", rows[0]["provider_error"])
        self.assertAlmostEqual(totals(ledger)[1], rows[0]["reserved_usd"] + 0.000001)

    def test_retry_stops_at_attempt_cap_and_budget_cap(self):
        status, _, ledger, calls, sleeps = self.request([self.failure() for _ in range(4)])
        self.assertEqual((status, len(calls), len(ledger["requests"])), (429, 4, 4))
        self.assertEqual([c.args[0] for c in sleeps], [2, 4, 8])
        status, _, ledger, calls, _ = self.request([self.failure()], tranche=0.0015)
        self.assertEqual((status, len(calls), len(ledger["requests"])), (402, 1, 1))

    def test_no_replay_of_chat_other_errors_or_uncertain_transport(self):
        for kind, failure, retries, expected in (
            ("chat", self.failure(), 3, 429),
            ("embedding", self.failure(503), 3, 503),
            ("embedding", TimeoutError(), 3, 502),
            ("embedding", self.failure(), 0, 429),
            ("embedding", self.failure(retry_after="60"), 3, 429),
        ):
            with self.subTest(kind=kind, expected=expected, retries=retries):
                status, _, ledger, calls, sleeps = self.request([failure], kind, retries)
                self.assertEqual((status, len(calls), len(ledger["requests"])), (expected, 1, 1))
                self.assertEqual(sleeps, [])
