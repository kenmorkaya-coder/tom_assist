import { render } from "preact";
import { useEffect, useState } from "preact/hooks";
import { ChatGptAdapter, type ProviderTurn } from "@tom-assist/provider-adapters";
import { PromptGateController, type EvaluationBadge, type ExtensionService, type GateSnapshot, type PacketPreview } from "./gate";
import { PROTOCOL_VERSION } from "./protocol";

function requestId(): string { return crypto.randomUUID(); }
function now(): string { return new Date().toISOString(); }

class NativeExtensionService implements ExtensionService {
  private async call(method: string, projectId: string, payload: unknown): Promise<any> {
    const request_id = requestId();
    const envelope = { protocol: PROTOCOL_VERSION, request_id, idempotency_key: requestId(), method, actor: { type: "extension", instance_id: chrome.runtime.id }, project_id: projectId, payload, sent_at: now() };
    return new Promise((resolve, reject) => {
      const timeout = window.setTimeout(() => { chrome.runtime.onMessage.removeListener(listener); reject(new Error("native response timeout")); }, 4000);
      const listener = (message: any) => {
        const response = message?.kind === "native.response" ? message.payload : undefined;
        if (response?.request_id !== request_id) return;
        window.clearTimeout(timeout); chrome.runtime.onMessage.removeListener(listener);
        response.ok ? resolve(response.payload) : reject(new Error(response.error?.message ?? "local service rejected request"));
      };
      chrome.runtime.onMessage.addListener(listener);
      void chrome.runtime.sendMessage(envelope).then((ack) => { if (!ack?.ok) throw new Error(ack?.error?.message ?? ack?.error?.code ?? "native host unavailable"); }).catch((error) => { window.clearTimeout(timeout); chrome.runtime.onMessage.removeListener(listener); reject(error); });
    });
  }
  async prepare(projectId: string, draft: string): Promise<PacketPreview> {
    const value = await this.call("turn.prepare", projectId, { project_id: projectId, workstream_id: "provider-main", provider_session_id: location.pathname, user_draft: draft, tom_checkpoint_digest: "sha256:unavailable", tom_activation_id: "extension", provider_capabilities: { provider: "chatgpt", adapter_version: "chatgpt-visible-dom/1.0", can_read_visible_turns: true, can_read_streaming_state: true, can_read_composer: true, can_write_composer: true, can_intercept_submit: true, can_mount_panel: true }, sections: [], retrieved_anchor_ids: [], excluded: [], created_at: now() });
    const packet = value.packet ?? {};
    return { packetText: value.packet_text ?? "", packetDigest: packet.packet_digest ?? "", includedCategories: (packet.sections ?? []).map((section: any) => section.section_type), warnings: packet.warnings ?? [], excludedItems: (packet.excluded ?? []).map((item: any) => item.reason) };
  }
  async markSent(projectId: string, draft: string, packetDigest: string): Promise<void> { await this.call("turn.sent", projectId, { project_id: projectId, packet_digest: packetDigest, user_draft: draft, turn_id: requestId(), ordinal: Date.now(), idempotency_key: requestId(), captured_at: now() }); }
  async evaluate(projectId: string, turn: ProviderTurn, packetDigest: string): Promise<EvaluationBadge> { const result = await this.call("response.evaluate", projectId, { project_id: projectId, packet_digest: packetDigest, response_turn_id: turn.contentHash, response_text: turn.normalizedText, ordinal: turn.ordinal, complete: turn.complete, created_at: now() }); return { result: result.result, count: result.intervention_ids?.length ?? 0, severity: result.result === "CONFLICT" ? "blocking" : result.result === "REVIEW" ? "warning" : "info" }; }
  async capture(projectId: string, kind: string, text: string): Promise<void> { await this.call("state.propose", projectId, { kind, text, authority: "user", requires_user_confirmation: true }); }
}

function GateView({ controller }: { controller: PromptGateController }) {
  const [state, setState] = useState<GateSnapshot>(controller.snapshot());
  useEffect(() => controller.subscribe(setState), [controller]);
  return <section class="tom-assist-page" aria-label="Tom Assist"><header><b>TOM ASSIST</b><span class="project-chip">{state.projectName ?? "Detached"}</span></header>{state.warning && <p role="alert">{state.warning}</p>}{state.phase === "preparing" && <p>Preparing snapshot-bound context…</p>}{(state.phase === "preview" || state.phase === "unavailable") && <div class="pre-send-drawer"><h2>Pre-send preview</h2>{state.preview && <><label>Visible packet<textarea value={state.editablePacket} onInput={(event) => controller.editPacket(event.currentTarget.value)}/></label><p>{state.editablePacket.length} characters · {state.preview.includedCategories.join(", ") || "no state categories"}</p><p>Warnings: {state.preview.warnings.join(", ") || "none"}</p><p>Excluded stale items: {state.preview.excludedItems.join(", ") || "none"}</p><button onClick={() => void controller.sendWithTom()}>Send with Tom</button></>}<button onClick={() => controller.sendOnceWithoutTom()}>Send once without Tom</button><button onClick={() => controller.cancel()}>Cancel</button><button onClick={() => controller.detachProject()}>Detach project</button></div>}{state.badge && <p class={`badge ${state.badge.result.toLowerCase()}`}>{state.badge.result} · {state.badge.count} · {state.badge.severity}</p>}<div class="quick-capture" aria-label="Quick capture">{["Decision", "Constraint", "Reject", "Complete", "Unresolved", "Evidence"].map((kind) => <button disabled={!state.projectId} onClick={() => void controller.quickCapture(kind)}>{kind}</button>)}</div><details><summary>Project continuity</summary><p>Active objective, held decisions, rejected paths, unresolved dependencies and recent interventions are available in the desktop ledger.</p><small>{state.capturedTurns} complete assistant responses evaluated</small></details></section>;
}

const style = document.createElement("style");
style.textContent = `#tom-assist-extension-root{position:fixed;right:18px;bottom:18px;z-index:2147483647;width:360px;color:#eaf0f6;font:13px system-ui}.tom-assist-page{background:#111a22;border:1px solid #3b5364;border-radius:14px;padding:14px;box-shadow:0 20px 60px #0008}.tom-assist-page header{display:flex;justify-content:space-between}.project-chip,.badge{padding:4px 8px;border-radius:999px;background:#24495a}.pre-send-drawer textarea{display:block;width:100%;height:140px;margin:8px 0;background:#0a1117;color:#eaf0f6}.tom-assist-page button{margin:5px 5px 0 0}.quick-capture{margin-top:10px}.pass{background:#235a42}.review{background:#705917}.conflict{background:#783c3c}`;
document.head.append(style);
const host = document.createElement("div"); host.id = "tom-assist-extension-root"; document.body.append(host);
const adapter = new ChatGptAdapter(document, location, (reason) => host.setAttribute("data-detached-reason", reason));
const controller = new PromptGateController(adapter, new NativeExtensionService());
render(<GateView controller={controller}/>, host);
void chrome.storage.local.get(["activeProjectId", "activeProjectName"]).then((stored) => { if (stored.activeProjectId) controller.attachProject(String(stored.activeProjectId), String(stored.activeProjectName ?? stored.activeProjectId)); return controller.start(); });
chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "local" || !("activeProjectId" in changes || "activeProjectName" in changes)) return;
  void chrome.storage.local.get(["activeProjectId", "activeProjectName"]).then((stored) => {
    if (stored.activeProjectId) controller.attachProject(String(stored.activeProjectId), String(stored.activeProjectName ?? stored.activeProjectId));
    else controller.detachProject();
  });
});
