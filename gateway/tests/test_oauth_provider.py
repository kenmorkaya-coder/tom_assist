"""Offline broker-boundary tests; no Keychain or real provider calls."""
import json
import socketserver
import tempfile
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread

import pytest

from gateway.oauth_provider import CAPABILITIES, OAuthProvider, ProviderFailure
from gateway.tom_gateway import TomGateway


@pytest.fixture
def broker():
    class Handler(BaseHTTPRequestHandler):
        calls = []
        request_versions = []
        connected = True
        reply = {
            "text": "Local broker fixture only",
            "model": "fixture-model",
            "complete": True,
        }
        failure = False

        def log_message(self, *_):
            pass

        def do_GET(self):
            self.request_versions.append(self.request_version)
            self.calls.append((self.path, None, dict(self.headers)))
            self.answer(
                {
                    "connected": self.connected,
                    "code": "OAUTH_READY"
                    if self.connected
                    else "OAUTH_NOT_CONNECTED",
                    "credential_owner": "tom-assist-keychain",
                    "model": "fixture-model",
                    "streaming": False,
                    "capabilities": CAPABILITIES,
                }
            )

        def do_POST(self):
            self.request_versions.append(self.request_version)
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.calls.append((self.path, body, dict(self.headers)))
            self.answer(self.reply)

        def answer(self, body):
            self.send_response(503 if self.failure else 200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            value = (
                {"ok": False, "error": {"code": "PROVIDER_REQUEST_FAILED"}}
                if self.failure
                else body
            )
            self.wfile.write(json.dumps(value).encode())

    class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
        daemon_threads = True

    temporary = tempfile.TemporaryDirectory(prefix="ta-oauth-", dir="/private/tmp")
    socket_path = Path(temporary.name) / "oauth.sock"
    server = Server(str(socket_path), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield OAuthProvider(socket_path), Handler
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
        temporary.cleanup()


@pytest.mark.parametrize("path", ["", "relative.sock", "/tmp/not-present.sock"])
def test_rejects_unsafe_or_unspecified_broker_paths(path):
    provider = OAuthProvider(path)
    assert provider.status()["connected"] is False
    with pytest.raises(ProviderFailure):
        provider.complete("minimal")


def test_status_never_generates_or_exposes_auth_fields(broker):
    provider, handler = broker
    status = provider.status()
    assert status["connected"] is True
    assert status["capabilities"] == CAPABILITIES
    assert status["streaming"] is False
    assert [path for path, _, _ in handler.calls] == ["/status"]
    assert handler.request_versions == ["HTTP/1.0"]
    serialized = json.dumps(status)
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized
    handler.connected = False
    assert provider.status()["connected"] is False
    with pytest.raises(ProviderFailure, match="OAUTH_NOT_CONNECTED"):
        provider.complete("never sent")
    assert all(path == "/status" for path, _, _ in handler.calls)


def test_explicit_completion_uses_only_broker_and_no_auth_header(broker):
    provider, handler = broker
    result = provider.complete("exact visible prompt")
    assert result == {
        "text": "Local broker fixture only",
        "model": "fixture-model",
        "complete": True,
    }
    assert [path for path, _, _ in handler.calls] == ["/status", "/complete"]
    assert handler.request_versions == ["HTTP/1.0", "HTTP/1.0"]
    assert handler.calls[-1][1] == {
        "explicit_send": True,
        "prompt": "exact visible prompt",
    }
    assert all("Authorization" not in headers for _, _, headers in handler.calls)


def test_structured_completion_requires_explicit_send_and_forwards_schema(broker):
    provider, handler = broker
    response_format = {
        "type": "json_schema",
        "name": "test_shape",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
        },
    }
    with pytest.raises(ProviderFailure, match="EXPLICIT_SEND_REQUIRED"):
        provider.complete_structured("parse", response_format)
    assert handler.calls == []
    result = provider.complete_structured(
        "parse exact visible source", response_format, explicit_send=True
    )
    assert result["complete"] is True
    assert [path for path, _, _ in handler.calls] == [
        "/status", "/structured-complete"
    ]
    assert handler.calls[-1][1] == {
        "explicit_send": True,
        "prompt": "parse exact visible source",
        "response_format": response_format,
    }
    assert all("Authorization" not in headers for _, _, headers in handler.calls)


def test_broker_errors_and_busy_never_retry(broker):
    provider, handler = broker
    provider.slot.acquire()
    with pytest.raises(ProviderFailure, match="PROVIDER_BUSY"):
        provider.complete("not sent")
    provider.slot.release()
    assert handler.calls == []
    handler.failure = True
    with pytest.raises(ProviderFailure) as error:
        provider.request("/complete", {"explicit_send": True, "prompt": "once"})
    assert str(error.value) == "PROVIDER_REQUEST_FAILED"
    assert len(handler.calls) == 1


def test_gateway_requires_explicit_send_without_touching_broker(tmp_path, broker):
    provider, handler = broker
    gateway = TomGateway(
        tmp_path, Path("/Users/kenmorkaya/PycharmProjects/tom_master")
    )
    gateway.oauth_provider = provider
    code, _ = gateway.handle(
        "POST", "/provider/complete", {"prompt": "not sent"}
    )
    assert code == 409
    assert handler.calls == []
    code, result = gateway.handle(
        "POST",
        "/provider/complete",
        {"prompt": "visible", "explicit_send": True},
    )
    assert code == 200 and result["complete"]
