"""A text-only OpenRouter gateway with cumulative, conservative cost accounting."""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import math
import os
from pathlib import Path
import secrets
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CHAT_MODEL = "deepseek/deepseek-v4.1-flash"
EMBEDDING_MODEL = "qwen/qwen3-embedding-8b"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def explicit_cost(row):
    cost = (row.get("usage") or {}).get("cost")
    return cost if isinstance(cost, (int, float)) and math.isfinite(cost) and cost >= 0 else None


def totals(ledger):
    paid = exposure = ledger.get("prior_paid_usd", 0)
    for row in ledger["requests"]:
        cost = explicit_cost(row)
        paid += cost or 0
        exposure += cost if row["status"] == "completed" and cost is not None else max(row["reserved_usd"], cost or 0)
    return paid, exposure


def reservation(size, kind, output, chat_prompt_price=0.3, chat_completion_price=1.2):
    return ((size + 8192) * (chat_prompt_price if kind == "chat" else 0.1) + output * chat_completion_price) / 1_000_000


def prepare_request(body, kind, embedding_provider="deepinfra", embedding_dimensions=None, chat_max_tokens=8192, reasoning_effort="low", force_chat_max_tokens=False, chat_prompt_price=0.3, chat_completion_price=1.2):
    body = dict(body)
    streaming = body.get("stream") is True
    body["stream"] = False
    body.pop("stream_options", None)
    output = 0
    if kind == "chat":
        for message in body.get("messages", []):
            content = message.get("content")
            if isinstance(content, list) and any(part.get("type") not in {"text", "input_text"} for part in content):
                raise ValueError("text_only_benchmark_profile")
        if body.get("n", 1) != 1:
            raise ValueError("multiple_choices_not_allowed")
        output = min(chat_max_tokens, int(body.get("max_tokens") or body.get("max_completion_tokens") or chat_max_tokens))
        if force_chat_max_tokens:
            output = chat_max_tokens
        if output <= 0:
            raise ValueError("invalid_output_limit")
        body.update(model=CHAT_MODEL, max_tokens=output, reasoning={"effort": reasoning_effort},
            provider={"only": ["deepseek"], "allow_fallbacks": False, "max_price": {"prompt": chat_prompt_price, "completion": chat_completion_price}})
        body.pop("max_completion_tokens", None)
        body.pop("reasoning_effort", None)
    else:
        body.pop("stream", None)
        if embedding_dimensions is not None:
            body["dimensions"] = embedding_dimensions
        body.update(model=EMBEDDING_MODEL,
            provider={"only": [embedding_provider], "allow_fallbacks": False, "max_price": {"prompt": 0.1}})
    return body, streaming, output


def buffered_events(result):
    """Preserve a completed response in SSE framing; this does not measure TTFT."""
    common = {key: result.get(key) for key in ("id", "created", "model")}
    common["object"] = "chat.completion.chunk"
    choice = result["choices"][0]
    delta = dict(choice["message"])
    if delta.get("tool_calls"):
        delta["tool_calls"] = [{**call, "index": i} for i, call in enumerate(delta["tool_calls"])]
    chunks = [
        {**common, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
        {**common, "choices": [{"index": 0, "delta": {}, "finish_reason": choice["finish_reason"]}], "usage": result.get("usage", {})},
    ]
    return ("".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks) + "data: [DONE]\n\n").encode()


class Ledger:
    def __init__(self, path, ceiling, tranche):
        self.path, self.ceiling, self.tranche = path, ceiling, tranche
        self.value = json.loads(path.read_text()) if path.exists() else {"ceiling_usd": ceiling, "prior_paid_usd": 0, "requests": []}
        self.starting_exposure = totals(self.value)[1]
        self.mutex = threading.Lock()

    def save(self):
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(self.value, indent=2) + "\n")
        temporary.replace(self.path)

    def reserve(self, amount, kind):
        with self.mutex:
            exposure = totals(self.value)[1]
            if exposure + amount > self.ceiling or exposure - self.starting_exposure + amount > self.tranche:
                return None
            row = {"ordinal": len(self.value["requests"]) + 1, "kind": kind,
                   "reserved_usd": amount, "status": "in_flight"}
            self.value["requests"].append(row)
            self.save()
            return row

    def finish(self, row, **values):
        with self.mutex:
            row.update(values)
            self.save()
            paid, exposure = totals(self.value)
            print(json.dumps({"event": "usage", **row, "paid_total_usd": paid,
                              "reserved_total_usd": exposure}), flush=True)


def embedding_retry_delay(kind, status, attempt, retries, retry_after):
    """Retry explicit embedding throttling only; never replay uncertain requests."""
    if kind != "embedding" or status != 429 or attempt >= retries:
        return None
    if retry_after is not None:
        if not retry_after.isdigit() or not 0 < int(retry_after) <= 30:
            return None
        return int(retry_after)
    return 2 ** (attempt + 1)


def handler_for(ledger, key, token, embedding_429_retries=0, embedding_provider="deepinfra", embedding_dimensions=None, chat_max_tokens=8192, request_timeout=90, reasoning_effort="low", force_chat_max_tokens=False, chat_prompt_price=0.3, chat_completion_price=1.2, receipt_dir=None):
    opener = urllib.request.build_opener(NoRedirect)
    maximum_profile_lock = threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, code, value, retry_after=None):
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            if retry_after and retry_after.isdigit():
                self.send_header("Retry-After", retry_after)
            self.end_headers()
            self.wfile.write(json.dumps(value).encode())

        def error(self, code, message, retry_after=None):
            self.reply(code, {"error": {"message": message}}, retry_after)

        def authenticated(self):
            return secrets.compare_digest(self.headers.get("Authorization", ""), "Bearer " + token)

        def do_GET(self):
            if not self.authenticated():
                return self.error(401, "unauthorized")
            if self.path != "/v1/models":
                return self.error(404, "route_not_allowed")
            self.reply(200, {"object": "list", "data": [{"id": CHAT_MODEL,
                "object": "model", "created": 0, "owned_by": "benchmark-route"}]})

        def do_POST(self):
            # Full provider-output reservations are large; keep this opt-in profile serial.
            with maximum_profile_lock if force_chat_max_tokens else nullcontext():
                self.process_post()

        def process_post(self):
            if not self.authenticated():
                return self.error(401, "unauthorized")
            kind = {"/v1/chat/completions": "chat", "/v1/embeddings": "embedding"}.get(self.path)
            if kind is None:
                return self.error(400, "route_not_allowed")
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size <= 0 or size > 262144:
                    return self.error(413, "input_limit")
                body, streaming, output = prepare_request(json.loads(self.rfile.read(size)), kind, embedding_provider, embedding_dimensions, chat_max_tokens, reasoning_effort, force_chat_max_tokens, chat_prompt_price, chat_completion_price)
                data = json.dumps(body).encode()
            except (ValueError, TypeError) as error:
                return self.error(400, str(error))
            request = urllib.request.Request("https://openrouter.ai/api" + self.path,
                data=data, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
            result = None
            first_ordinal = None
            retries = embedding_429_retries if kind == "embedding" else 0
            for attempt in range(retries + 1):
                row = ledger.reserve(reservation(len(data), kind, output, chat_prompt_price, chat_completion_price), kind)
                if row is None:
                    return self.error(402, "local_budget_exhausted")
                if first_ordinal is None:
                    first_ordinal = row["ordinal"]
                attempt_metadata = {"attempt": attempt + 1, "request_ordinal": first_ordinal,
                    "requested_provider": embedding_provider if kind == "embedding" else "deepseek"}
                if kind == "chat":
                    attempt_metadata.update(requested_max_tokens=output, reasoning_effort=body["reasoning"]["effort"],
                        max_price=body["provider"]["max_price"])
                started = time.monotonic()
                try:
                    with opener.open(request, timeout=request_timeout) as response:
                        result = json.load(response)
                    if receipt_dir is not None:
                        receipt_dir.mkdir(parents=True, exist_ok=True)
                        receipt_path = receipt_dir / (str(row['ordinal']) + '.json')
                        receipt_path.write_text(json.dumps({'request':body,'response':result},indent=2)+'\n')
                        receipt_path.chmod(0o600)
                    usage = result.get("usage") or {}
                    state = "completed" if explicit_cost({"usage": usage}) is not None else "completed_cost_unknown"
                    ledger.finish(row, status=state, http_status=200, usage=usage,
                        model=result.get("model"), provider=result.get("provider"),
                        seconds=time.monotonic()-started, **attempt_metadata)
                    break
                except urllib.error.HTTPError as error:
                    try:
                        detail = str(json.load(error).get("error", {}).get("message", ""))
                    except (ValueError, AttributeError):
                        detail = ""
                    finally:
                        error.close()
                    detail = detail.replace(key, "[redacted]").replace(token, "[redacted]")[:600]
                    retry_after = error.headers.get("Retry-After")
                    delay = embedding_retry_delay(kind, error.code, attempt, retries, retry_after)
                    ledger.finish(row, status="provider_failed", http_status=error.code,
                        provider_error=detail, seconds=time.monotonic()-started,
                        retry_delay_seconds=delay, **attempt_metadata)
                    if delay is None:
                        return self.error(error.code, f"upstream_http_{error.code}: {detail}", retry_after)
                    time.sleep(delay)
                except Exception as error:
                    ledger.finish(row, status="uncertain", seconds=time.monotonic()-started,
                        **attempt_metadata)
                    return self.error(502, type(error).__name__)
            try:
                if streaming and kind == "chat":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.end_headers()
                    self.wfile.write(buffered_events(result))
                else:
                    self.reply(200, result)
            except (BrokenPipeError, ConnectionResetError):
                pass  # The completed provider charge remains in the ledger.
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt-dir", type=Path, help="Optional private provider request/response evidence directory; excludes authentication headers")
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--ceiling", type=float, default=10)
    parser.add_argument("--tranche", type=float, default=0.5)
    parser.add_argument("--embedding-provider", choices=("deepinfra", "nebius"), default="deepinfra")
    parser.add_argument("--embedding-dimensions", type=int,
                        help="Fix the shared Qwen embedding dimension for clients without a dimension setting")
    parser.add_argument("--embedding-429-retries", type=int, choices=range(4), default=0)
    parser.add_argument("--chat-max-tokens", type=int, default=8192)
    parser.add_argument("--chat-prompt-price", type=float, default=0.3, help="Enforced provider USD per million input tokens")
    parser.add_argument("--chat-completion-price", type=float, default=1.2, help="Enforced provider USD per million output tokens")
    parser.add_argument("--request-timeout", type=int, default=90)
    parser.add_argument("--force-chat-max-tokens", action="store_true", help="Override native internal output limits for a provider-maximum capability profile")
    parser.add_argument("--reasoning-effort", choices=("low", "high", "max"), default="low")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.embedding_dimensions is not None and not 1 <= args.embedding_dimensions <= 4096:
        parser.error("embedding dimensions must be between 1 and 4096")
    if args.chat_max_tokens <= 0 or args.request_timeout <= 0:
        parser.error("chat output and request timeout must be positive")
    if any(not math.isfinite(p) or p <= 0 for p in (args.chat_prompt_price, args.chat_completion_price)):
        parser.error("chat prices must be finite and positive")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or not 0 < args.tranche <= args.ceiling or not math.isfinite(args.ceiling):
        parser.error("Provide a command and finite positive limits with tranche <= ceiling")
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        parser.error("Inject OPENROUTER_API_KEY into this gateway process")
    path = args.ledger.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".lock")
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    try:
        ledger = Ledger(path, args.ceiling, args.tranche)
        ledger.save()
        token = secrets.token_hex(24)
        server = ThreadingHTTPServer(("0.0.0.0", 0), handler_for(ledger, key, token, args.embedding_429_retries, args.embedding_provider, args.embedding_dimensions, args.chat_max_tokens, args.request_timeout, args.reasoning_effort, args.force_chat_max_tokens, args.chat_prompt_price, args.chat_completion_price, args.receipt_dir))
        server.daemon_threads = False
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}/v1"
        env = dict(os.environ)
        env.pop("OPENROUTER_API_KEY", None)
        env.update(LITELLM_API_KEY=token, LITELLM_BASE_URL=base, LITELLM_CHAT_COMPAT_BASE_URL=base,
            EMBEDDING_API_KEY=token, EMBEDDING_API_BASE=base,
            OPENAI_API_KEY=token, OPENAI_BASE_URL=base, OPENAI_API_BASE=base)
        print(json.dumps({"event": "budget_start", "ceiling_usd": args.ceiling,
            "tranche_reservation_usd": args.tranche, "paid_total_usd": totals(ledger.value)[0],
            "embedding_429_retries": args.embedding_429_retries,
            "force_chat_max_tokens": args.force_chat_max_tokens,
            "chat_prompt_price": args.chat_prompt_price, "chat_completion_price": args.chat_completion_price,
            "chat_max_tokens": args.chat_max_tokens, "request_timeout": args.request_timeout, "reasoning_effort": args.reasoning_effort,
            "embedding_provider": args.embedding_provider, "embedding_dimensions": args.embedding_dimensions,
            "transport": "nonstream_upstream_with_optional_buffered_sse"}), flush=True)
        def interrupted(signum, frame):
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, interrupted)
        child = None
        try:
            child = subprocess.Popen(command, env=env, start_new_session=True)
            exit_code = child.wait()
        except KeyboardInterrupt:
            if child is not None and child.poll() is None:
                os.killpg(child.pid, signal.SIGINT)
                try:
                    child.wait(timeout=180)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
            exit_code = 130
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        paid, exposure = totals(ledger.value)
        print(json.dumps({"event": "budget_finish", "consumer_exit": exit_code,
            "paid_total_usd": paid, "reserved_total_usd": exposure}), flush=True)
        return exit_code
    finally:
        lock.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
