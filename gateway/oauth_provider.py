"""Secret-free adapter to the Tom Assist-owned OAuth broker.

Only the broker can read Tom Assist's macOS Keychain entry or contact the
provider. The gateway uses an owner-only Unix socket and receives readiness
metadata or response text; tokens and account identifiers never cross this
boundary.
"""
import http.client
import json
import os
import socket
import stat
import threading
from pathlib import Path

CAPABILITIES = {
    "provider_surface": "tom-assist/openai-oauth",
    "visible_prompt_injection": True,
    "response_capture": True,
    "hidden_context_visibility": False,
    "model_internal_bias": "none",
    "supports_system_field": False,
}

_SAFE_BROKER_ERRORS = {
    "EXPLICIT_SEND_REQUIRED",
    "OAUTH_NOT_CONNECTED",
    "OAUTH_REFRESH_REQUIRED",
    "PROVIDER_BUSY",
    "PROVIDER_PROMPT_INVALID",
    "PROVIDER_REQUEST_FAILED",
    "PROVIDER_RESPONSE_INVALID",
    "PROVIDER_RESPONSE_FORMAT_INVALID",
    "PROVIDER_EMPTY_OR_OVERSIZE_RESPONSE",
}


class ProviderFailure(Exception):
    pass


class _UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path, timeout):
        super().__init__("localhost", timeout=timeout)
        # The product broker deliberately exposes a small HTTP/1.0-only
        # protocol over its owner-only Unix socket.  http.client defaults to
        # HTTP/1.1, so pin the wire version instead of relying on fixture
        # servers that accept both versions.
        self._http_vsn = 10
        self._http_vsn_str = "HTTP/1.0"
        self.socket_path = socket_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.socket_path)


class OAuthProvider:
    def __init__(self, socket_path=None):
        configured = (
            socket_path
            if socket_path is not None
            else os.environ.get("TOM_ASSIST_OAUTH_BROKER_SOCKET", "")
        )
        self.socket_path = str(configured)
        self.slot = threading.BoundedSemaphore(1)

    def validated_socket(self):
        if not self.socket_path or "\x00" in self.socket_path:
            raise ProviderFailure("OAUTH_BROKER_NOT_CONFIGURED")
        path = Path(self.socket_path)
        if not path.is_absolute() or len(os.fsencode(path)) >= 104:
            raise ProviderFailure("OAUTH_BROKER_NOT_CONFIGURED")
        try:
            mode = os.lstat(path).st_mode
        except OSError:
            raise ProviderFailure("OAUTH_BROKER_UNAVAILABLE") from None
        if not stat.S_ISSOCK(mode):
            raise ProviderFailure("OAUTH_BROKER_UNAVAILABLE")
        return str(path)

    def request(self, path, payload=None):
        connection = _UnixHTTPConnection(
            self.validated_socket(), timeout=180 if payload is not None else 3
        )
        try:
            body = (
                json.dumps(payload, separators=(",", ":")).encode()
                if payload is not None
                else None
            )
            connection.request(
                "POST" if body is not None else "GET",
                path,
                body=body,
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            raw = response.read(768 * 1024 + 1)
            if len(raw) > 768 * 1024:
                raise ProviderFailure("OAUTH_BROKER_INVALID_RESPONSE")
            try:
                value = json.loads(raw)
            except (TypeError, ValueError):
                raise ProviderFailure("OAUTH_BROKER_INVALID_RESPONSE") from None
            if response.status != 200:
                code = (
                    value.get("error", {}).get("code")
                    if isinstance(value, dict)
                    else None
                )
                raise ProviderFailure(
                    code
                    if code in _SAFE_BROKER_ERRORS
                    else "OAUTH_BROKER_REQUEST_FAILED"
                )
            if not isinstance(value, dict):
                raise ProviderFailure("OAUTH_BROKER_INVALID_RESPONSE")
            return value
        except ProviderFailure:
            raise
        except Exception:
            raise ProviderFailure("OAUTH_BROKER_UNAVAILABLE") from None
        finally:
            connection.close()

    def status(self):
        result = {
            "connected": False,
            "code": "OAUTH_NOT_CONNECTED",
            "capabilities": dict(CAPABILITIES),
            "streaming": False,
            "model": "broker-managed",
            "credential_owner": "tom-assist-keychain",
            "history_policy": "visible bounded local conversation history + current packet + draft",
        }
        try:
            status = self.request("/status")
            result["connected"] = status.get("connected") is True
            result["code"] = str(status.get("code", "OAUTH_NOT_CONNECTED"))
            if isinstance(status.get("model"), str):
                result["model"] = status["model"]
            if status.get("capabilities") == CAPABILITIES:
                result["capabilities"] = dict(CAPABILITIES)
        except ProviderFailure as error:
            result["code"] = str(error)
        return result

    def complete(self, prompt):
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 48_000:
            raise ProviderFailure("PROVIDER_PROMPT_INVALID")
        if not self.slot.acquire(blocking=False):
            raise ProviderFailure("PROVIDER_BUSY")
        try:
            if not self.status()["connected"]:
                raise ProviderFailure("OAUTH_NOT_CONNECTED")
            response = self.request(
                "/complete", {"explicit_send": True, "prompt": prompt}
            )
            text = response.get("text")
            model = response.get("model")
            if (
                not isinstance(text, str)
                or not text.strip()
                or len(text.encode()) > 512_000
                or not isinstance(model, str)
                or not model
                or response.get("complete") is not True
            ):
                raise ProviderFailure("PROVIDER_EMPTY_OR_OVERSIZE_RESPONSE")
            return {"text": text, "model": model, "complete": True}
        finally:
            self.slot.release()

    def complete_structured(self, prompt, response_format, *, explicit_send=False):
        """Make one explicit, schema-constrained provider call through the broker.

        This candidate-only surface is intentionally not exposed as a gateway
        preview route.  The broker remains the sole holder of credentials.
        """
        if explicit_send is not True:
            raise ProviderFailure("EXPLICIT_SEND_REQUIRED")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 48_000:
            raise ProviderFailure("PROVIDER_PROMPT_INVALID")
        if not isinstance(response_format, dict):
            raise ProviderFailure("PROVIDER_RESPONSE_FORMAT_INVALID")
        try:
            encoded_format = json.dumps(
                response_format, ensure_ascii=False, allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError):
            raise ProviderFailure("PROVIDER_RESPONSE_FORMAT_INVALID") from None
        if len(encoded_format) > 128 * 1024:
            raise ProviderFailure("PROVIDER_RESPONSE_FORMAT_INVALID")
        if not self.slot.acquire(blocking=False):
            raise ProviderFailure("PROVIDER_BUSY")
        try:
            if not self.status()["connected"]:
                raise ProviderFailure("OAUTH_NOT_CONNECTED")
            response = self.request(
                "/structured-complete",
                {
                    "explicit_send": True,
                    "prompt": prompt,
                    "response_format": response_format,
                },
            )
            text = response.get("text")
            model = response.get("model")
            if (
                not isinstance(text, str)
                or not text.strip()
                or len(text.encode()) > 512_000
                or not isinstance(model, str)
                or not model
                or response.get("complete") is not True
            ):
                raise ProviderFailure("PROVIDER_EMPTY_OR_OVERSIZE_RESPONSE")
            return {"text": text, "model": model, "complete": True}
        finally:
            self.slot.release()
