import { useState } from "preact/hooks";
import type { DesktopBackend, PreparedExchange } from "./backend";

// Local diagnostic fixture only: never sends a request to a provider.
export function Exchange({ projectId, backend }: { projectId: string; backend: DesktopBackend }) {
  const [draft, setDraft] = useState("Explain the connected beam and column load path.");
  const [response, setResponse] = useState("The connected beam transfers force to both columns.");
  const [prepared, setPrepared] = useState<PreparedExchange>();
  const [sent, setSent] = useState(false);
  const [result, setResult] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [session] = useState(() => crypto.randomUUID());
  const [turn] = useState(() => crypto.randomUUID());
  const [answer] = useState(() => crypto.randomUUID());
  async function run(action: () => Promise<void>) { setBusy(true); setError(""); try { await action(); } catch (e) { setError(String(e)); } finally { setBusy(false); } }
  return <section class="settings"><h3>Local exchange diagnostic</h3>
    <p>Simulated provider response only. No provider request is sent. Marking sent and evaluating applies real commit dynamics to this project; use a disposable test project.</p>
    {error && <p role="alert">{error}</p>}
    <label>Diagnostic draft<textarea aria-label="Diagnostic draft" disabled={sent} value={draft} onInput={e => { setDraft(e.currentTarget.value); setPrepared(undefined); }}/></label>
    <button disabled={busy || sent || !draft.trim()} onClick={() => void run(async () => {
      const packet = await backend.exchange(projectId, "turn.prepare", { workstream_id: "desktop-main", provider_session_id: session, user_draft: draft,
        tom_checkpoint_digest: "daemon-owned", tom_activation_id: "daemon-owned", created_at: new Date().toISOString(),
        provider_capabilities: { provider_surface: "desktop/local-fixture", visible_prompt_injection: true, response_capture: true, hidden_context_visibility: false, model_internal_bias: "none" } });
      setPrepared(packet as PreparedExchange);
    })}>Prepare diagnostic packet</button>
    {prepared && <><pre aria-label="Prepared packet">{prepared.packet_text}</pre><p>Packet digest: {prepared.packet.packet_digest}</p>
      <button disabled={busy || sent} onClick={() => void run(async () => {
        await backend.exchange(projectId, "turn.sent", { packet_digest: prepared.packet.packet_digest, user_draft: draft, turn_id: turn, ordinal: 1, idempotency_key: turn, captured_at: new Date().toISOString() }); setSent(true);
      })}>Mark diagnostic turn sent</button></>}
    {sent && <p role="status">Diagnostic turn sent; awaiting response evaluation.</p>}
    <label>Simulated provider response<textarea aria-label="Simulated provider response" value={response} disabled={!!result} onInput={e => setResponse(e.currentTarget.value)}/></label>
    <button disabled={busy || !sent || !!result || !response.trim()} onClick={() => void run(async () => {
      setResult(await backend.exchange(projectId, "response.evaluate", { packet_digest: prepared!.packet.packet_digest, response_turn_id: answer, response_text: response, ordinal: 2, complete: true, created_at: new Date().toISOString() }));
    })}>Evaluate diagnostic response and commit</button>
    {!!result && <pre aria-label="Exchange result">{JSON.stringify(result, null, 2)}</pre>}
  </section>;
}
