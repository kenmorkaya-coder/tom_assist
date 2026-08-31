"""Offline boundary tests; no token reads, auth mutation or real provider calls."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from gateway.oauth_provider import CAPABILITIES, OAuthProvider, ProviderFailure
from gateway.tom_gateway import TomGateway


@pytest.fixture
def runtime():
    class Handler(BaseHTTPRequestHandler):
        calls = []
        oauth = {"ready": True, "mode": "oauth"}
        status = {"auth_mode": "oauth", "oauth_ready": True, "provider": "openai", "key_prefix": "DO-NOT-COPY"}
        reply = {"text": "Local transport fixture only", "model": "default"}
        failure = False

        def log_message(self, *_): pass

        def do_GET(self):
            self.calls.append((self.path, None, dict(self.headers)))
            self.answer(self.oauth if self.path == "/api/oauth/status" else self.status)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.calls.append((self.path, body, dict(self.headers)))
            self.answer(self.reply)

        def answer(self, body):
            self.send_response(500 if self.failure else 200)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "SECRET-UPSTREAM-ERROR"} if self.failure else body).encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    assert server.server_port != 18790
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try: yield OAuthProvider(f"http://127.0.0.1:{server.server_port}"), Handler
    finally:
        server.shutdown(); server.server_close(); worker.join()


@pytest.mark.parametrize("url", ["", "http://localhost:12345", "https://127.0.0.1:12345", "http://127.0.0.1:18790", "http://user:secret@127.0.0.1:12345", "http://127.0.0.1:12345/token", "http://127.0.0.1:12345/?key=secret", "http://example.com:12345", "http://127.0.0.1:99999"])
def test_reject_unsafe_or_unspecified_runtime_origins(url):
    provider = OAuthProvider(url)
    assert provider.status()["connected"] is False
    with pytest.raises(ProviderFailure): provider.complete("minimal")


def test_status_never_generates_or_copies_auth_fields(runtime):
    provider, handler = runtime
    status = provider.status()
    assert status["connected"] is True
    assert status["capabilities"] == CAPABILITIES
    assert status["streaming"] is False
    assert [path for path, _, _ in handler.calls] == ["/api/oauth/status"]
    assert "DO-NOT-COPY" not in json.dumps(status)
    handler.oauth = {"ready": True, "mode": "api_key"}
    assert provider.status()["connected"] is False
    with pytest.raises(ProviderFailure, match="OAUTH_DISCONNECTED"): provider.complete("never sent")
    assert all(path == "/api/oauth/status" for path, _, _ in handler.calls)


def test_explicit_completion_uses_only_runtime_thin_generation_and_no_auth_header(runtime):
    provider, handler = runtime
    result = provider.complete("exact visible prompt")
    assert result == {"text": "Local transport fixture only", "model": "runtime-managed", "complete": True}
    assert [path for path, _, _ in handler.calls] == ["/api/oauth/status", "/api/llm/status", "/api/llm/complete"]
    assert handler.calls[-1][1] == {"prompt": "exact visible prompt"}
    assert all("Authorization" not in headers for _, _, headers in handler.calls)
    assert "DO-NOT-COPY" not in json.dumps(result)


def test_provider_mismatch_errors_and_busy_never_retry(runtime):
    provider, handler = runtime
    handler.status = {"auth_mode": "oauth", "oauth_ready": True, "provider": "anthropic"}
    with pytest.raises(ProviderFailure, match="OAUTH_PROVIDER_MISMATCH"): provider.complete("not sent")
    assert len(handler.calls) == 2
    provider.slot.acquire()
    with pytest.raises(ProviderFailure, match="PROVIDER_BUSY"): provider.complete("not sent")
    provider.slot.release()
    assert len(handler.calls) == 2
    handler.failure = True
    with pytest.raises(ProviderFailure) as error: provider.request("/api/llm/complete", {"prompt":"once"})
    assert str(error.value) == "OAUTH_RUNTIME_REQUEST_FAILED"
    assert len(handler.calls) == 3


def test_gateway_requires_explicit_send_without_touching_runtime(tmp_path, runtime):
    provider, handler = runtime
    gateway = TomGateway(tmp_path, __import__("pathlib").Path("/Users/kenmorkaya/PycharmProjects/tom_master"))
    gateway.oauth_provider = provider
    code, _ = gateway.handle("POST", "/provider/complete", {"prompt":"not sent"})
    assert code == 409
    assert handler.calls == []
    code, result = gateway.handle("POST", "/provider/complete", {"prompt":"visible", "explicit_send":True})
    assert code == 200 and result["complete"]
