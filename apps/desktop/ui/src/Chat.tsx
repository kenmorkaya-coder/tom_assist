import { useEffect, useRef, useState } from "preact/hooks";
import type { ChatMethod, DesktopBackend } from "./backend";
import type { Project, StateObject, InterventionRecord } from "./types";
import { SelfReport, type SelfReportRecord } from "./SelfReport";

export interface Conversation {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
}
export interface Exchange {
  id: string;
  project_id: string;
  session_id: string;
  packet_digest: string;
  user_draft: string;
  prompt: string;
  prompt_hash: string;
  status: string;
  response_text?: string;
  error_code?: string;
  context_preview?: {
    sections: {
      type: string;
      items: {
        state_id: string;
        text: string;
        authority: string;
        structural_score: number;
        semantic_score: number;
        reason_selected: string;
      }[];
    }[];
    excluded: { id: string; reason: string }[];
    document_research?: {
      final_evidence_coverage?: {
        discovered_units?: {
          evidence_id: string;
          clause_identifier?: string;
          conditionality?: string[];
          packet_admitted?: boolean;
          packet_exclusion_reason?: string;
        }[];
        missing_sources?: { named_identifier?: string; reason_code?: string }[];
        exhaustiveness?: string;
      };
    };
  };
}
export interface ConversationView {
  session: Conversation;
  exchanges: {
    exchange: Exchange;
    evaluation?: { result: string; turn_id: string };
    commit?: unknown;
    self_report?: SelfReportRecord;
  }[];
  interventions: (InterventionRecord & { turn_id: string })[];
}
export interface ProviderStatus {
  connected: boolean;
  self_report_enabled?: boolean;
  code: string;
  model?: string;
  streaming?: boolean;
  capabilities?: Record<string, unknown>;
}

function readableEvidence(text: string) {
  const blocks = text
    .trim()
    .split(/\n\s*\n+/)
    .map((block) => block.split("\n").map((line) => line.trim()).join(" "))
    .filter(Boolean);
  if (blocks.length <= 1) return { heading: "Selected project material", paragraphs: blocks };
  return { heading: blocks[0], paragraphs: blocks.slice(1) };
}

function topLevelRequirementCount(text: string) {
  const markers = [...text.matchAll(/^([ \t]*)\(([A-Za-z0-9]+)\)[ \t]+/gm)];
  if (!markers.length || !/\b(?:must|must not|may not)\b/i.test(text)) return 0;
  const shallowest = Math.min(...markers.map((match) => (match[1] ?? "").length));
  return markers.filter((match) => (match[1] ?? "").length === shallowest).length;
}

function readableResponse(text: string) {
  return text.replace(/\*\*([^*]+)\*\*/g, "$1").replace(/\*([^*]+)\*/g, "$1");
}

function sectionLabel(section: string) {
  const labels: Record<string, string> = {
    EVIDENCE_BOUNDARY: "Contract evidence",
    BINDING_CONSTRAINTS: "Project constraints",
    HELD_DECISIONS: "Project decisions",
    ACTIVE_OBJECTIVE: "Project objectives",
    "REJECTED_OR_SUPERSEDED - DO NOT REVIVE WITHOUT EXPLICIT RECONSIDERATION": "Rejected or superseded paths",
    "COMPLETED_WORK - DO NOT REPROPOSE AS OPEN": "Completed work",
  };
  return labels[section] ?? section.toLowerCase().replaceAll("_", " ");
}

function sourceLabel(id: string) {
  const match = id.match(/^document-[^:]+:chunk:(\d+)$/);
  if (match) return `Retained contract source · chunk ${match[1]}`;
  if (/^document-[^:]+:unit:/.test(id)) return "Retained authored contract clause";
  return "Retained project state";
}

export function Chat({
  project,
  objects,
  backend,
  onChanged,
}: {
  project: Project;
  objects: StateObject[];
  backend: DesktopBackend;
  onChanged(): Promise<void>;
}) {
  const [sessions, setSessions] = useState<Conversation[]>([]);
  const [view, setView] = useState<ConversationView>();
  const [provider, setProvider] = useState<ProviderStatus>();
  const [title, setTitle] = useState("New conversation");
  const [draft, setDraft] = useState("");
  const [prepared, setPrepared] = useState<Exchange>();
  const [busy, setBusy] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [capture, setCapture] = useState<{
    turn: string;
    text: string;
    old: string;
    reason: string;
  }>();
  const selected = useRef("");
  const mounted = useRef(true);
  const request = async <T,>(
    method: ChatMethod,
    payload: Record<string, unknown> = {},
  ) => (await backend.chat(project.id, method, payload)) as T;
  async function load(id: string) {
    const next = await request<ConversationView>("conversation.get", {
      session_id: id,
    });
    if (mounted.current && selected.current === id) setView(next);
  }
  async function choose(id: string) {
    selected.current = id;
    setPrepared(undefined);
    setDraft("");
    setCapture(undefined);
    setView(undefined);
    await load(id);
  }
  async function run(work: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await work();
    } catch (e) {
      if (mounted.current) setError(String(e));
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  useEffect(() => {
    mounted.current = true;
    void Promise.all([
      request<ProviderStatus>("provider.status"),
      request<Conversation[]>("conversation.list"),
    ])
      .then(([status, rows]) => {
        if (!mounted.current) return;
        setProvider(status);
        setSessions(rows);
        if (rows[0]) void choose(rows[0].id).catch((e) => setError(String(e)));
      })
      .catch((e) => setError(String(e)));
    return () => {
      mounted.current = false;
    };
  }, [project.id]);
  useEffect(() => setPrepared(undefined), [project.state_version]);
  const waiting = view?.exchanges.some((row) =>
    ["sending", "evaluation_pending"].includes(row.exchange.status),
  );
  const previewSections = prepared?.context_preview?.sections ?? [];
  const evidenceSections = previewSections.filter(
    (section) => section.type === "EVIDENCE_BOUNDARY",
  );
  const otherContextSections = previewSections.filter(
    (section) => section.type !== "EVIDENCE_BOUNDARY",
  );
  const selectedEvidenceCount = evidenceSections.reduce(
    (total, section) => total + section.items.length,
    0,
  );
  const excludedEvidenceCount = (prepared?.context_preview?.excluded ?? []).filter(
    (item) => item.id.startsWith("document-"),
  ).length;
  const researchCoverage = prepared?.context_preview?.document_research
    ?.final_evidence_coverage;
  const discoveredUnits = researchCoverage?.discovered_units ?? [];
  const projectWideCount = discoveredUnits.filter((row) =>
    row.conditionality?.includes("project_wide"),
  ).length;
  const activityConditionalCount = discoveredUnits.filter((row) =>
    row.conditionality?.includes("activity_conditional"),
  ).length;
  const discoveredClauses = [...new Set(
    discoveredUnits.map((row) => row.clause_identifier).filter(Boolean),
  )];
  useEffect(() => {
    if ((!waiting && !sending) || !view) return;
    const timer = setInterval(
      () => void load(view.session.id).catch((e) => setError(String(e))),
      1500,
    );
    return () => clearInterval(timer);
  }, [waiting, sending, view?.session.id]);
  const reload = async () => {
    if (selected.current) await load(selected.current);
    await onChanged();
  };
  return (
    <section class="chat" aria-label="Governed project chat">
      <div class="chat-connection">
        <div>
          <strong>Governed chat</strong>
          <p>
            {provider?.connected
              ? "Tom Assist OAuth connected"
              : "OAuth not connected — connect Tom Assist"}{" "}
            · model: {provider?.model ?? "broker-managed"}
          </p>
        </div>
        <button
          disabled={busy}
          onClick={() =>
            void run(async () => {
              if (provider?.connected) await backend.oauthLogout();
              else await backend.oauthLogin();
              setProvider(await request<ProviderStatus>("provider.status"));
            })
          }
        >
          {provider?.connected ? "Disconnect OAuth" : "Connect OAuth"}
        </button>
        <button
          disabled={busy}
          onClick={() =>
            void run(async () =>
              setProvider(await request<ProviderStatus>("provider.status")),
            )
          }
        >
          Refresh connection
        </button>
      </div>
      <p class="chat-boundary">
        Send with Tom transmits your visible packet, bounded conversation
        history and draft. Credentials stay in Tom Assist's macOS Keychain and
        credential broker; they never enter the project ledger or archive.
        Responses arrive when complete; no token streaming or hidden-context
        visibility is claimed. Conversation text and approved prompts are
        retained locally and in complete archives, unencrypted. No automatic expiry is applied.
        Experimental provider self-report is off by default and requires a
        separate preview and explicit send for its one extra call.
      </p>
      {provider && (
        <details>
          <summary>Provider capabilities</summary>
          <pre>{JSON.stringify(provider.capabilities, null, 2)}</pre>
        </details>
      )}
      {error && <p role="alert">{error}</p>}
      <div class="chat-sessions">
        <label>
          Conversation
          <select
            aria-label="Conversation"
            value={view?.session.id ?? ""}
            disabled={busy}
            onChange={(e) => void run(() => choose(e.currentTarget.value))}
          >
            <option value="" disabled>
              Select a conversation
            </option>
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
          </select>
        </label>
        <label>
          Conversation name
          <input
            aria-label="Conversation name"
            maxLength={120}
            value={title}
            onInput={(e) => setTitle(e.currentTarget.value)}
          />
        </label>
        <button
          disabled={busy || !title.trim()}
          onClick={() =>
            void run(async () => {
              const s = await request<Conversation>("conversation.create", {
                session_id: crypto.randomUUID(),
                title,
              });
              setSessions(await request<Conversation[]>("conversation.list"));
              await choose(s.id);
            })
          }
        >
          New conversation
        </button>
      </div>
      <div
        class="chat-transcript"
        aria-label="Conversation transcript"
        aria-live="polite"
      >
        {!view && (
          <p>
            Select or create a project conversation. Nothing is sent
            automatically.
          </p>
        )}
        {view?.exchanges
          .filter((row) => row.exchange.status !== "prepared")
          .map(({ exchange: e, evaluation, commit, self_report }) => (
            <article key={e.id} class="chat-exchange">
              <div class="chat-message user">
                <strong>You</strong>
                <p>{e.user_draft}</p>
              </div>
              <div class="chat-message assistant">
                <strong>Assistant</strong>
                {e.response_text ? (
                  <p>{readableResponse(e.response_text)}</p>
                ) : (
                  <p role="status">
                    {e.status === "sending"
                      ? "Waiting for the connected provider…"
                      : "No response captured. Provider outcome may be unknown; check the connection before a new send."}
                  </p>
                )}
                {evaluation && (
                  <span class={`chat-badge ${evaluation.result.toLowerCase()}`}>
                    {evaluation.result}
                  </span>
                )}
                {e.response_text && (
                  <span class="chat-commit">
                    {commit
                      ? "Five-dynamics experience committed"
                      : "Experience awaiting evaluation or your review"}
                  </span>
                )}
                {e.error_code && <p role="alert">{e.error_code}</p>}
                {e.response_text && (
                  <div class="chat-actions">
                    <button
                      disabled={busy}
                      onClick={() => {
                        setPrepared(undefined);
                        setCapture({
                          turn: `${e.id}:assistant`,
                          text: e.response_text!,
                          old: "",
                          reason: "",
                        });
                      }}
                    >
                      Review capture / supersession
                    </button>
                    {!commit && (
                      <button
                        disabled={busy}
                        onClick={() =>
                          void run(async () => {
                            await request("conversation.evaluate", {
                              exchange_id: e.id,
                            });
                            await reload();
                          })
                        }
                      >
                        Retry captured evaluation
                      </button>
                    )}
                    {!commit &&
                      evaluation &&
                      evaluation.result !== "PASS" &&
                      !view.interventions.some(
                        (i) =>
                          i.turn_id === `${e.id}:assistant` &&
                          i.status === "open",
                      ) && (
                        <button
                          disabled={busy}
                          onClick={() =>
                            void run(async () => {
                              await request("conversation.evaluate", {
                                exchange_id: e.id,
                                accept_reviewed: true,
                              });
                              await reload();
                            })
                          }
                        >
                          Accept reviewed exchange
                        </button>
                      )}
                  </div>
                )}
                {view.interventions
                  .filter((i) => i.turn_id === `${e.id}:assistant`)
                  .map((i) => (
                    <div key={i.id} class="chat-finding">
                      <strong>
                        {i.code} · {i.status}
                      </strong>
                      <p>{i.summary}</p>
                      {i.status === "open" &&
                        (
                          ["accepted", "false_positive", "dismissed"] as const
                        ).map((status, index) => (
                          <button
                            disabled={busy}
                            onClick={() =>
                              void run(async () => {
                                await backend.resolveIntervention(
                                  project.id,
                                  i.id,
                                  status,
                                );
                                await reload();
                              })
                            }
                          >
                            {
                              [
                                "Accept finding",
                                "Mark false positive",
                                "Dismiss finding",
                              ][index]
                            }
                          </button>
                        ))}
                    </div>
                  ))}
                {e.response_text && <SelfReport enabled={provider?.self_report_enabled === true} report={self_report} exchangeId={e.id} busy={busy}
                  act={(method, payload) => void run(async () => { await request(method, payload); await reload(); })} />}
              </div>
            </article>
          ))}
      </div>
      {capture && (
        <section class="settings">
          <h3>Confirm authoritative decision</h3>
          <p>
            Assistant text is only a proposal. Edit it, then explicitly confirm.
            Supersession preserves the old decision and requires your reason.
          </p>
          <label>
            Decision text
            <textarea
              aria-label="Decision text"
              value={capture.text}
              maxLength={16000}
              onInput={(e) =>
                setCapture({ ...capture, text: e.currentTarget.value })
              }
            />
          </label>
          <label>
            Supersede decision
            <select
              aria-label="Supersede decision"
              value={capture.old}
              onChange={(e) =>
                setCapture({ ...capture, old: e.currentTarget.value })
              }
            >
              <option value="">Capture as a new decision</option>
              {objects
                .filter((o) => o.status === "active")
                .map((o) => (
                  <option value={o.id}>{o.title}</option>
                ))}
            </select>
          </label>
          {capture.old && (
            <label>
              Supersession reason
              <input
                aria-label="Supersession reason"
                value={capture.reason}
                onInput={(e) =>
                  setCapture({ ...capture, reason: e.currentTarget.value })
                }
              />
            </label>
          )}
          <button
            disabled={
              busy ||
              !capture.text.trim() ||
              (!!capture.old && !capture.reason.trim())
            }
            onClick={() =>
              void run(async () => {
                await backend.captureChatState(
                  project,
                  capture.turn,
                  capture.text,
                  capture.old || undefined,
                  capture.reason || undefined,
                );
                setCapture(undefined);
                setPrepared(undefined);
                await reload();
              })
            }
          >
            Confirm decision
          </button>
          <button disabled={busy} onClick={() => setCapture(undefined)}>
            Cancel capture
          </button>
        </section>
      )}
      {view && (
        <section class="chat-composer">
          <label>
            Message
            <textarea
              aria-label="Message"
              placeholder="Ask about this project…"
              value={draft}
              maxLength={16000}
              disabled={busy || waiting}
              onInput={(e) => {
                setDraft(e.currentTarget.value);
                setPrepared(undefined);
              }}
            />
          </label>
          <button
            disabled={busy || waiting || !draft.trim()}
            onClick={() =>
              void run(async () =>
                setPrepared(
                  await request<Exchange>("conversation.prepare", {
                    session_id: view.session.id,
                    exchange_id: crypto.randomUUID(),
                    user_draft: draft,
                  }),
                ),
              )
            }
          >
            Preview packet
          </button>
          {prepared && (
            <section class="chat-preview">
              <h3>Evidence selected for your question</h3>
              <p class="chat-preview-intro">
                {evidenceSections.some((section) => section.items.length)
                  ? "Tom Assist found the following project material. Review it before you choose Send with Tom. Nothing has been sent yet."
                  : otherContextSections.some((section) => section.items.length)
                    ? "Tom Assist found retained project context but no document evidence for this question. Nothing has been sent yet."
                    : "No retained project material was selected. Your message will be sent as written if you choose Send with Tom."}
              </p>
              {!!selectedEvidenceCount && (
                <div class="chat-preview-coverage" role="note">
                  <strong>
                    This is a retrieved evidence subset, not a complete requirements inventory.
                  </strong>
                  <p>
                    {selectedEvidenceCount} contract excerpt
                    {selectedEvidenceCount === 1 ? " is" : "s are"} shown
                    {excludedEvidenceCount
                      ? `; ${excludedEvidenceCount} other contract candidate${excludedEvidenceCount === 1 ? " was" : "s were"} excluded by the packet budget.`
                      : "."}
                    {" "}Tom Assist has not counted every requirement in the deed.
                  </p>
                </div>
              )}
              {!!discoveredUnits.length && (
                <section class="chat-research-coverage" aria-label="Document research coverage">
                  <h4>Prerequisite coverage found in the project documents</h4>
                  <p>
                    Tom Assist found {discoveredUnits.length} authored evidence unit
                    {discoveredUnits.length === 1 ? "" : "s"}: {projectWideCount} project-wide and {activityConditionalCount} activity-conditional.
                    {" "}{selectedEvidenceCount} fit in this outgoing packet; the remainder are still recorded below, not silently discarded.
                  </p>
                  <p><strong>Clause addresses:</strong> {discoveredClauses.join(", ")}</p>
                  {!!researchCoverage?.missing_sources?.length && (
                    <p role="alert">
                      Not exhaustive: the deed refers to material that is not addressable in the retained source ({researchCoverage.missing_sources
                        .map((row) => row.named_identifier ?? "unresolved reference")
                        .join(", ")}).
                    </p>
                  )}
                  <details>
                    <summary>Why discovered items did or did not reach the packet</summary>
                    <ul>
                      {discoveredUnits.map((row) => (
                        <li key={row.evidence_id}>
                          {row.clause_identifier ?? row.evidence_id}: {row.packet_admitted
                            ? "included"
                            : row.packet_exclusion_reason ?? "not selected by the gateway"}
                        </li>
                      ))}
                    </ul>
                  </details>
                </section>
              )}
              <div class="chat-preview-evidence" aria-label="Selected project evidence">
                {evidenceSections.map((section) =>
                  section.items.map((item) => {
                    const evidence = readableEvidence(item.text);
                    const requirementCount = topLevelRequirementCount(item.text);
                    return (
                      <article class="chat-preview-source" key={item.state_id}>
                        <span class="chat-preview-kind">{sectionLabel(section.type)}</span>
                        <h4>{evidence.heading}</h4>
                        {!!requirementCount && (
                          <p class="chat-preview-requirement-count">
                            {requirementCount} requirement
                            {requirementCount === 1 ? "" : "s"} in this selected clause
                          </p>
                        )}
                        <div class="chat-preview-quote">
                          {evidence.paragraphs.map((paragraph) => (
                            <p>{paragraph}</p>
                          ))}
                        </div>
                        <p class="chat-preview-citation">{sourceLabel(item.state_id)}</p>
                      </article>
                    );
                  }),
                )}
              </div>
              {!!otherContextSections.length && (
                <details class="chat-preview-other">
                  <summary>Other retained project context</summary>
                  {otherContextSections.map((section) =>
                    section.items.map((item) => (
                      <p key={item.state_id}>
                        <strong>{sectionLabel(section.type)}:</strong>{" "}
                        {readableResponse(item.text)}
                      </p>
                    )),
                  )}
                </details>
              )}
              {!!prepared.context_preview?.excluded.length && (
                <p class="chat-preview-excluded">
                  {prepared.context_preview.excluded.length} other candidate
                  {prepared.context_preview.excluded.length === 1 ? " was" : "s were"} not included within this packet's evidence budget.
                </p>
              )}
              <details class="chat-preview-technical">
                <summary>Technical send details</summary>
                <p>Packet digest: {prepared.packet_digest}</p>
                <pre aria-label="Outgoing provider prompt">
                  {prepared.prompt}
                </pre>
              </details>
              <button
                disabled={busy || waiting || !provider?.connected}
                onClick={() =>
                  void run(async () => {
                    const id = selected.current;
                    setSending(true);
                    try {
                      const result = await request<ConversationView>(
                        "conversation.send",
                        {
                          exchange_id: prepared.id,
                          confirmed_prompt_hash: prepared.prompt_hash,
                          explicit_send: true,
                        },
                      );
                      if (mounted.current && selected.current === id) {
                        setView(result);
                        setPrepared(undefined);
                        setDraft("");
                      }
                      await onChanged();
                    } finally {
                      if (mounted.current) {
                        setSending(false);
                        await load(id);
                      }
                    }
                  })
                }
              >
                Send with Tom
              </button>
              <button disabled={busy} onClick={() => setPrepared(undefined)}>
                Cancel preview
              </button>
            </section>
          )}
          {busy && (
            <p role="status">
              Working locally or waiting for the runtime. No automatic resend.
            </p>
          )}
        </section>
      )}
    </section>
  );
}
