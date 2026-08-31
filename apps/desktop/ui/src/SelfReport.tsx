import type { ChatMethod } from "./backend";

export interface SelfReportRecord {
  status: string;
  prompt: string;
  prompt_hash: string;
  error_code?: string;
  candidates: { candidate_id: string; operation: string; object: { type: string; canonical_text: string } }[];
  labels: Record<string, string>;
  precision: { value: number | null; accurate: number; false_positive: number; reviewed: number; emitted: number; unreviewed: number };
  metrics: Record<string, number>;
}

export function SelfReport({ enabled, report, exchangeId, busy, act }: {
  enabled: boolean; report?: SelfReportRecord; exchangeId: string; busy: boolean;
  act(method: ChatMethod, payload: Record<string, unknown>): void;
}) {
  if (!enabled && !report) return null;
  return <section aria-label="Experimental provider self-report" class="chat-finding">
    <h4>Provider self-report · experimental</h4>
    <p>Optional extra OAuth call. Reports are proposals, not ledger truth. Nothing here changes project state or teaches the runtime. Accuracy labels measure proposals only; use the normal capture workflow for an authoritative change.</p>
    {!report && <button disabled={busy || !enabled} onClick={() => act("conversation.self_report.prepare", { exchange_id: exchangeId })}>Preview self-report request</button>}
    {report && <>
      <p>Status: {report.status}{report.status === "sending" && " — if interrupted, outcome is unknown; never automatically resent"}</p>
      <details open={report.status === "prepared"}><summary>Exact extra request</summary><pre>{report.prompt}</pre></details>
      {report.status === "prepared" && <button disabled={busy || !enabled} onClick={() => act("conversation.self_report.send", { exchange_id: exchangeId, confirmed_prompt_hash: report.prompt_hash, explicit_send: true })}>Send one self-report request</button>}
      {report.status === "prepared" && <button disabled={busy || !enabled} onClick={() => act("conversation.self_report.prepare", { exchange_id: exchangeId })}>Refresh self-report preview</button>}
      {report.error_code && <p role="alert">{report.error_code}</p>}
      {report.candidates.map(c => <div key={c.candidate_id}>
        <strong>{c.object.type} · {c.operation} · candidate only</strong>
        <p>{c.object.canonical_text}</p>
        <p>Label: {report.labels[c.candidate_id] ?? "unreviewed"}</p>
        {(["accurate", "false_positive", "unreviewed"] as const).map((label, i) => <button disabled={busy} onClick={() => act("conversation.self_report.label", { exchange_id: exchangeId, candidate_id: c.candidate_id, label, confirmed: true })}>{["Mark accurate proposal", "Mark false positive proposal", "Clear accuracy label"][i]}</button>)}
      </div>)}
      <p>Owner-labelled precision: {report.precision.value === null ? "not measured" : `${report.precision.accurate}/${report.precision.reviewed}`} · {report.precision.unreviewed} unreviewed of {report.precision.emitted} emitted. Machine adjudication is not an accuracy label.</p>
      <details><summary>Instrumentation</summary><pre>{JSON.stringify(report.metrics, null, 2)}</pre></details>
    </>}
  </section>;
}
