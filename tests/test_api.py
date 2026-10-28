from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Any
import unittest
from unittest.mock import patch

from experiment.api import APIError, ChatClient, normalize_endpoint


def completion(content: str = "a puzzle", reason: str = "stop") -> dict:
    return {"id": "fake-completion", "model": "mock-snapshot", "system_fingerprint": "fp_mock",
            "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": reason}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}


class Handler(BaseHTTPRequestHandler):
    queued: list[tuple[int, dict]] = []
    received: list[dict] = []
    lock = threading.Lock()
    barrier: threading.Barrier | None = None
    active = 0
    peak = 0

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        with Handler.lock:
            Handler.received.append({"path": self.path, "body": body, "auth": self.headers.get("Authorization")})
            status, result = Handler.queued.pop(0)
            Handler.active += 1
            Handler.peak = max(Handler.peak, Handler.active)
        try:
            if Handler.barrier:
                try:
                    Handler.barrier.wait(timeout=5)
                except threading.BrokenBarrierError:
                    status, result = 500, {"error": "Requests did not run concurrently"}
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("x-request-id", "request-mock")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        finally:
            with Handler.lock:
                Handler.active -= 1

    def log_message(self, format: str, *args: Any) -> None:
        pass


class APITests(unittest.TestCase):
    def setUp(self) -> None:
        Handler.queued = []
        Handler.received = []
        Handler.barrier = None
        Handler.active = Handler.peak = 0
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}/v1"
        self.messages = [{"role": "user", "content": "Create a puzzle"}]
        self.env = patch.dict(os.environ, {"MOCK_API_KEY": "secret-do-not-save"})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def client(self, **kwargs: Any) -> ChatClient:
        options = {"api_key_env": "MOCK_API_KEY", "retry_backoff": 0, **kwargs}
        return ChatClient(self.endpoint, "mock-model", self.cache, **options)

    def test_normalize_and_validate_endpoint(self) -> None:
        self.assertEqual(normalize_endpoint("https://example.com/v1/"), "https://example.com/v1/chat/completions")
        self.assertEqual(normalize_endpoint("https://example.com/v1/chat/completions"),
                         "https://example.com/v1/chat/completions")
        with self.assertRaises(ValueError):
            normalize_endpoint("http://example.com/v1")
        with self.assertRaises(ValueError):
            normalize_endpoint("https://example.com/v1?api_key=secret")

    def test_cache_replay_records_metadata_without_credentials(self) -> None:
        Handler.queued = [(200, completion())]
        client = self.client(parameters={"temperature": 0.7})
        first = client.complete(self.messages, "seed-1")
        replay = self.client(max_calls=1, parameters={"temperature": 0.7}).complete(self.messages, "seed-1")
        self.assertEqual(first, replay)
        self.assertEqual(len(Handler.received), 1)
        self.assertFalse(Handler.received[0]["body"]["stream"])
        self.assertEqual(Handler.received[0]["auth"], "Bearer secret-do-not-save")
        saved = "\n".join(p.read_text() for p in self.cache.iterdir())
        self.assertNotIn("secret-do-not-save", saved)
        self.assertNotIn("Authorization", saved)
        self.assertIn("fp_mock", saved)
        self.assertIn("request-mock", saved)

    def test_retry_and_budget_persist_across_clients(self) -> None:
        Handler.queued = [(429, {"error": "rate limit"}), (500, {"error": "temporary"}), (200, completion())]
        self.client(max_calls=3).complete(self.messages, "seed-1")
        self.assertEqual(len(Handler.received), 3)
        with self.assertRaises(APIError) as caught:
            self.client(max_calls=3).complete(self.messages, "seed-2")
        self.assertEqual(caught.exception.kind, "call_budget_exhausted")
        self.assertEqual(len(Handler.received), 3)

    def test_authentication_error_is_not_retried_or_returned_as_data(self) -> None:
        Handler.queued = [(401, {"error": "secret-do-not-save"})]
        with self.assertRaises(APIError) as caught:
            self.client().complete(self.messages, "seed-1")
        self.assertEqual(caught.exception.status, 401)
        self.assertEqual(len(Handler.received), 1)
        saved = "\n".join(p.read_text() for p in self.cache.iterdir())
        self.assertNotIn("secret-do-not-save", saved)

    def test_truncated_and_empty_outputs_fail_clearly(self) -> None:
        for index, (content, reason, kind) in enumerate([
            ("partial", "length", "truncated_response"), (" ", "stop", "empty_response")
        ]):
            Handler.queued = [(200, completion(content, reason))]
            with self.assertRaises(APIError) as caught:
                self.client().complete(self.messages, f"bad-{index}")
            self.assertEqual(caught.exception.kind, kind)
        self.assertEqual(len(Handler.received), 2)

    def test_models_and_task_tags_have_independent_cache_entries(self) -> None:
        Handler.queued = [(200, completion()) for _ in range(3)]
        self.client().complete(self.messages, "seed-1")
        ChatClient(self.endpoint, "another-model", self.cache, retry_backoff=0).complete(self.messages, "seed-1")
        self.client().complete(self.messages, "seed-2")
        self.assertEqual(len(Handler.received), 3)

    def test_reserved_parameters_cannot_silently_override_request(self) -> None:
        with self.assertRaises(ValueError):
            self.client(parameters={"stream": True})

    def test_distinct_tasks_reach_http_server_concurrently(self) -> None:
        Handler.queued = [(200, completion()) for _ in range(4)]
        Handler.barrier = threading.Barrier(4)
        client = self.client(retries=0, max_calls=4)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda i: client.complete(self.messages, f"seed-{i}"), range(4)))
        self.assertEqual(len(results), 4)
        self.assertEqual(Handler.peak, 4)
        self.assertEqual(len(Handler.received), 4)

    def test_same_task_concurrent_requests_pay_once(self) -> None:
        Handler.queued = [(200, completion())]
        client = self.client(retries=0, max_calls=1)
        start = threading.Barrier(8)
        def request(_: int) -> dict:
            start.wait(timeout=5)
            return client.complete(self.messages, "same-task")
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(request, range(8)))
        self.assertTrue(all(row == results[0] for row in results))
        self.assertEqual(len(Handler.received), 1)
        events = [json.loads(line) for line in client.log_path.read_text().splitlines()]
        self.assertEqual(sum(e["event"] == "request_start" for e in events), 1)
        self.assertEqual(sum(e["event"] == "cache_hit" for e in events), 7)

    def test_concurrent_requests_respect_hard_cap_and_resumed_cache(self) -> None:
        Handler.queued = [(200, completion()) for _ in range(3)]
        client = self.client(retries=0, max_calls=3)
        start = threading.Barrier(8)
        def request(index: int) -> tuple[str, dict | APIError]:
            tag = f"concurrent-{index}"
            start.wait(timeout=5)
            try:
                return tag, client.complete(self.messages, tag)
            except APIError as exc:
                return tag, exc
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(request, range(8)))
        successes = [(tag, result) for tag, result in results if not isinstance(result, APIError)]
        failures = [result for _, result in results if isinstance(result, APIError)]
        self.assertEqual((len(successes), len(failures), len(Handler.received)), (3, 5, 3))
        self.assertTrue(all(result.kind == "call_budget_exhausted" for result in failures))
        events = [json.loads(line) for line in client.log_path.read_text().splitlines()]
        starts = [event for event in events if event["event"] == "request_start"]
        self.assertEqual([event["call_number"] for event in starts], [1, 2, 3])
        resumed = self.client(retries=0, max_calls=3)
        self.assertEqual(resumed.complete(self.messages, successes[0][0]), successes[0][1])
        with self.assertRaises(APIError):
            resumed.complete(self.messages, "new-task")
        self.assertEqual(len(Handler.received), 3)
        saved = "\n".join(path.read_text() for path in self.cache.iterdir())
        self.assertNotIn("secret-do-not-save", saved)

    def test_concurrent_retries_share_cap_and_keep_own_attempt_files(self) -> None:
        Handler.queued = [(500, {"error": "secret-do-not-save"}) for _ in range(5)]
        client = self.client(retries=3, max_calls=5)
        def request(index: int) -> APIError:
            try:
                client.complete(self.messages, f"retry-{index}")
            except APIError as exc:
                return exc
            self.fail("All mock responses should fail")
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(request, range(4)))
        self.assertEqual(len(Handler.received), 5)
        self.assertTrue(all(result.kind in ("http_error", "call_budget_exhausted") for result in results))
        events = [json.loads(line) for line in client.log_path.read_text().splitlines()]
        starts = {event["call_number"]: event["digest"] for event in events if event["event"] == "request_start"}
        self.assertEqual(set(starts), set(range(1, 6)))
        failures = list(self.cache.glob("*.failure-*.json"))
        self.assertEqual(len(failures), 5)
        for path in failures:
            digest, number = path.stem.split(".failure-")
            self.assertEqual(starts[int(number)], digest)
            self.assertNotIn("secret-do-not-save", path.read_text())


if __name__ == "__main__":
    unittest.main()
