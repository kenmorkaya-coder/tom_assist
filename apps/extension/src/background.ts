import { ChunkAssembler } from "./chunks";
import {
  NATIVE_HOST_NAME,
  isTrustedSender,
  validateEnvelope,
  type Envelope,
} from "./protocol";
import {
  chromeSessionStorage,
  holdTransaction,
  releaseTransaction,
} from "./session";

const assembler = new ChunkAssembler();
let nativePort: chrome.runtime.Port | undefined;

function port(): chrome.runtime.Port {
  if (nativePort) return nativePort;
  nativePort = chrome.runtime.connectNative(NATIVE_HOST_NAME);
  nativePort.onMessage.addListener(async (message: unknown) => {
    const complete = assembler.accept(message);
    if (complete === undefined) return;
    const correlationId =
      complete && typeof complete === "object"
        ? String((complete as Record<string, unknown>).request_id ?? (complete as Record<string, unknown>).correlation_id ?? "")
        : "";
    if (correlationId) await releaseTransaction(chromeSessionStorage, correlationId);
    await chrome.runtime.sendMessage({ kind: "native.response", payload: complete });
  });
  nativePort.onDisconnect.addListener(() => {
    nativePort = undefined;
  });
  return nativePort;
}

chrome.runtime.onInstalled.addListener(async () => {
  await chrome.storage.session.setAccessLevel({ accessLevel: "TRUSTED_CONTEXTS" });
});

chrome.runtime.onMessage.addListener((message: unknown, sender, sendResponse) => {
  if (!isTrustedSender(sender.id, chrome.runtime.id)) {
    sendResponse({ ok: false, error: { code: "PERMISSION_DENIED" } });
    return false;
  }
  void (async () => {
    try {
      const envelope: Envelope = validateEnvelope(message);
      const phase = envelope.method === "turn.prepare" ? "PREPARE_TURN" : "PENDING_SEND";
      await holdTransaction(chromeSessionStorage, {
        correlationId: envelope.request_id,
        phase,
        envelope,
        heldAt: new Date().toISOString(),
      });
      port().postMessage(envelope);
      sendResponse({ ok: true, correlation_id: envelope.request_id });
    } catch (error) {
      sendResponse({
        ok: false,
        error: { code: "VALIDATION_FAILED", message: String(error) },
      });
    }
  })();
  return true;
});
