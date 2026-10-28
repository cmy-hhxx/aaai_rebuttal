"""Small, audited client for OpenAI-compatible Chat Completions endpoints."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
from pathlib import Path
import threading
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request


class APIError(RuntimeError):
    """An infrastructure/response failure, never a generated puzzle sample."""

    def __init__(self, kind: str, *, status: int | None = None, attempts: int = 0):
        self.kind = kind
        self.status = status
        self.attempts = attempts
        super().__init__(f"ChatCompletion {kind}; status={status}; attempts={attempts}")


def normalize_endpoint(endpoint: str, *, allow_insecure_http: bool = False) -> str:
    parsed = urllib.parse.urlsplit(endpoint.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Provide an absolute http(s) endpoint or base URL")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Endpoint must not contain credentials or a fragment")
    sensitive_keys = {"key", "api_key", "api-key", "token", "access_token", "signature"}
    if any(k.lower() in sensitive_keys for k, _ in urllib.parse.parse_qsl(parsed.query)):
        raise ValueError("Put credentials in the configured environment variable")
    try:
        local = ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        local = parsed.hostname.lower() == "localhost"
    if parsed.scheme == "http" and not local and not allow_insecure_http:
        raise ValueError("Remote HTTP requires allow_insecure_http=True")
    path = parsed.path.rstrip("/")
    if not path.endswith("/chat/completions"):
        path += "/chat/completions"
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, ""))


class ChatClient:
    """Cache by task tag + endpoint + full payload; never persist the API key.

    ``max_calls`` counts actual HTTP attempts, including retries, across all prior
    entries in this cache directory. One client may be shared by many threads;
    multiple concurrent client/process writers to the same directory are unsupported.
    Distinct tags intentionally obtain independent samples for identical prompts.
    """

    def __init__(
        self,
        endpoint: str,
        model: str,
        cache_dir: str | Path,
        api_key_env: str = "OPENAI_API_KEY",
        parameters: dict[str, Any] | None = None,
        timeout: float = 120,
        retries: int = 3,
        max_calls: int = 10000,
        *,
        allow_insecure_http: bool = False,
        retry_backoff: float = 1,
    ):
        if not model or timeout <= 0 or retries < 0 or max_calls < 0 or retry_backoff < 0:
            raise ValueError("Invalid model, timeout, retry, or call-budget setting")
        self.endpoint = normalize_endpoint(endpoint, allow_insecure_http=allow_insecure_http)
        self.model = model
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.parameters = dict(parameters or {})
        if {"model", "messages", "stream"} & self.parameters.keys():
            raise ValueError("model/messages/stream cannot be overridden by parameters")
        self.api_key_env = api_key_env
        self.timeout = timeout
        self.retries = retries
        self.max_calls = max_calls
        self.retry_backoff = retry_backoff
        self.log_path = self.cache_dir / "requests.jsonl"
        self._calls = 0
        if self.log_path.exists():
            for line in self.log_path.read_text().splitlines():
                if line.strip():
                    self._calls += json.loads(line).get("event") == "request_start"
        self._state_lock = threading.Lock()
        self._log_lock = threading.Lock()
        self._task_locks: dict[str, Any] = {}

    def _redact(self, value: Any) -> Any:
        key = os.environ.get(self.api_key_env, "")
        if isinstance(value, str):
            return value.replace(key, "[REDACTED]") if key else value
        if isinstance(value, dict):
            return {k: self._redact(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._redact(v) for v in value]
        return value

    def _save(self, path: Path, value: Any) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(self._redact(value), ensure_ascii=False, indent=2))
        temporary.replace(path)

    def _log(self, event: str, **details: Any) -> None:
        line = json.dumps(self._redact({"event": event, "time": time.time(), **details}),
                          ensure_ascii=False) + "\n"
        with self._log_lock:
            with self.log_path.open("a", encoding="utf-8") as stream:
                stream.write(line)

    def _reserve_call(self, digest: str, tag: str, attempt: int) -> int:
        with self._state_lock:
            if self._calls >= self.max_calls:
                self._log("call_budget_exhausted", digest=digest, tag=tag, attempt=attempt)
                raise APIError("call_budget_exhausted", attempts=attempt - 1)
            self._calls += 1
            call_number = self._calls
            self._log("request_start", digest=digest, tag=tag, attempt=attempt, call_number=call_number)
            return call_number

    @staticmethod
    def _validate(response: Any) -> dict[str, Any]:
        if not isinstance(response, dict):
            raise APIError("invalid_response")
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise APIError("missing_choices")
        choice = choices[0]
        if choice.get("finish_reason") == "length":
            raise APIError("truncated_response")
        if choice.get("finish_reason") == "content_filter":
            raise APIError("content_filtered_response")
        message = choice.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise APIError("empty_response")
        return response

    def complete(self, messages: list[dict[str, Any]], tag: str) -> dict[str, Any]:
        if not messages or not tag:
            raise ValueError("messages and a stable task tag are required")
        payload = {**self.parameters, "model": self.model, "messages": messages, "stream": False}
        identity = {"version": 1, "endpoint": self.endpoint, "payload": payload, "tag": tag}
        encoded = json.dumps(identity, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
        digest = hashlib.sha256(encoded).hexdigest()
        # Freeze caller-owned messages before requests can overlap.
        identity = json.loads(encoded)
        with self._state_lock:
            task_lock = self._task_locks.setdefault(digest, threading.Lock())
        with task_lock:
            return self._complete(identity, digest)

    def _complete(self, identity: dict[str, Any], digest: str) -> dict[str, Any]:
        payload, tag = identity["payload"], identity["tag"]
        response_path = self.cache_dir / f"{digest}.json"
        if response_path.exists():
            saved = json.loads(response_path.read_text())
            result = self._validate(saved["response"])
            self._log("cache_hit", digest=digest, tag=tag)
            return result
        key = os.environ.get(self.api_key_env, "")
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()
        self._save(self.cache_dir / f"{digest}.request.json", identity)
        for attempt in range(1, self.retries + 2):
            call_number = self._reserve_call(digest, tag, attempt)
            retry_after = 0.0
            raw: Any = None
            try:
                request = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
                # Disable redirects: never forward a private prompt to an unrequested destination.
                opener = urllib.request.build_opener(_NoRedirect())
                with opener.open(request, timeout=self.timeout) as reply:
                    raw = json.loads(reply.read().decode("utf-8"))
                    response = self._validate(raw)
                    request_id = reply.headers.get("x-request-id") or reply.headers.get("openai-request-id")
                self._save(response_path, {**identity, "response": response,
                                           "http_request_id": request_id, "attempts": attempt,
                                           "completed_at": time.time()})
                self._log("request_success", digest=digest, tag=tag, attempt=attempt,
                          response_model=response.get("model"), usage=response.get("usage"),
                          system_fingerprint=response.get("system_fingerprint"), request_id=request_id)
                return response
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                error = APIError("http_error", status=exc.code, attempts=attempt)
                retryable = exc.code == 429 or 500 <= exc.code <= 599
                try:
                    retry_after = min(30, max(0, float(exc.headers.get("Retry-After", "0"))))
                except (TypeError, ValueError):
                    retry_after = 0
                exc.close()
            except (urllib.error.URLError, TimeoutError, OSError):
                error = APIError("transport_error", attempts=attempt)
                retryable = True
            except (json.JSONDecodeError, UnicodeDecodeError):
                error = APIError("invalid_json_response", attempts=attempt)
                retryable = False
            except APIError as exc:
                error = APIError(exc.kind, status=exc.status, attempts=attempt)
                retryable = False
            failure = {"kind": error.kind, "status": error.status, "attempt": attempt,
                       "retryable": retryable}
            self._save(self.cache_dir / f"{digest}.failure-{call_number}.json",
                       {**identity, **failure, "response": raw})
            self._log("request_failure", digest=digest, tag=tag, **failure)
            if not retryable or attempt > self.retries:
                raise error
            time.sleep(max(retry_after, min(30, self.retry_backoff * 2 ** (attempt - 1))))
        raise AssertionError("unreachable")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: Any, msg: Any,
                         headers: Any, newurl: Any) -> None:
        return None
