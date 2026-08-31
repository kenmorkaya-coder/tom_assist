"""Credential-free adapter to the owner's ALREADY connected runtime process.

Pinned upstream: interface/desktop_api.py:1671 -> llm_provider.make_llm
(:202, :518) -> auth_profiles CredentialType.OAUTH -> OpenAIClient.complete_text
/generate (:1721, :836). Never import the desktop server or copy its tokens.
The upstream client retains its semaphore/flock/TPM limits and refresh policy.
"""
import http.client
import json
import os
import threading
from urllib.parse import urlsplit

CAPABILITIES = {"provider_surface":"tom-master/openai-oauth", "visible_prompt_injection":True,
                "response_capture":True, "hidden_context_visibility":False,
                "model_internal_bias":"none", "supports_system_field":False}


class ProviderFailure(Exception):
    pass


class OAuthProvider:
    def __init__(self, runtime_url=None):
        self.url = runtime_url if runtime_url is not None else os.environ.get("TOM_ASSIST_OAUTH_RUNTIME_URL", "")
        self.slot = threading.BoundedSemaphore(1)  # Never increase the upstream cap.

    def address(self):
        url = urlsplit(self.url)
        if (url.scheme != "http" or url.hostname not in ("127.0.0.1", "::1")
                or not url.port or url.port == 18790 or url.username or url.password
                or url.path not in ("", "/") or url.query or url.fragment):
            raise ProviderFailure("OAUTH_RUNTIME_NOT_CONFIGURED")
        return url.hostname, url.port

    def request(self, path, payload=None):
        host, port = self.address()
        connection = http.client.HTTPConnection(host, port, timeout=180 if payload else 3)
        try:
            body = json.dumps(payload).encode() if payload is not None else None
            connection.request("POST" if body is not None else "GET", path, body=body,
                               headers={"Content-Type":"application/json"})
            response = connection.getresponse()
            raw = response.read(1024 * 1024 + 1)
            if response.status != 200 or len(raw) > 1024 * 1024:
                raise ProviderFailure("OAUTH_RUNTIME_REQUEST_FAILED")
            value = json.loads(raw)
            if not isinstance(value, dict): raise ProviderFailure("OAUTH_RUNTIME_INVALID_RESPONSE")
            return value
        except ProviderFailure:
            raise
        except Exception:
            # Upstream errors can include HTTP bodies; no credential-bearing
            # exception text, headers, auth status fields or config is forwarded.
            raise ProviderFailure("OAUTH_RUNTIME_UNAVAILABLE") from None
        finally:
            connection.close()

    def status(self):
        result = {"connected":False, "code":"OAUTH_DISCONNECTED", "capabilities":dict(CAPABILITIES),
                  "streaming":False, "model":"runtime-managed", "credentials":"runtime-owned",
                  "history_policy":"visible bounded local conversation history + current packet + draft"}
        try:
            status = self.request("/api/oauth/status")  # No auth refresh or LLM request.
            result["connected"] = status.get("ready") is True and status.get("mode") == "oauth"
            if result["connected"]: result["code"] = "OAUTH_READY"
        except (ProviderFailure, ValueError):
            result["code"] = "OAUTH_RUNTIME_UNAVAILABLE" if self.url else "OAUTH_RUNTIME_NOT_CONFIGURED"
        return result

    def complete(self, prompt):
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 48_000:
            raise ProviderFailure("PROVIDER_PROMPT_INVALID")
        if not self.slot.acquire(blocking=False): raise ProviderFailure("PROVIDER_BUSY")
        try:
            if not self.status()["connected"]: raise ProviderFailure("OAUTH_DISCONNECTED")
            # Only explicit SEND reaches this endpoint. Never query /llm/status
            # from preview/status: its API-key branch can validate a key remotely.
            status = self.request("/api/llm/status")
            if status.get("auth_mode") != "oauth" or status.get("oauth_ready") is not True or status.get("provider") != "openai":
                raise ProviderFailure("OAUTH_PROVIDER_MISMATCH")
            response = self.request("/api/llm/complete", {"prompt":prompt})
            text = response.get("text")
            if not isinstance(text, str) or not text.strip() or len(text.encode()) > 512_000:
                raise ProviderFailure("PROVIDER_EMPTY_OR_OVERSIZE_RESPONSE")
            # The endpoint reports 'default', not an authoritative resolved model.
            return {"text":text, "model":"runtime-managed", "complete":True}
        finally:
            self.slot.release()
