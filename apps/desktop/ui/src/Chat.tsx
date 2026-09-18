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
  accepted_review?: boolean;
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
          requirement_components?: { source_start?: number; source_end?: number }[];
        }[];
        missing_sources?: { named_identifier?: string; reason_code?: string }[];
        exhaustiveness?: string;
      };
      processing_coverage?: {
        policy?: string;
        examined_count?: number;
        unexamined_count?: number;
        included_authored_unit_count?: number;
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
  const processingCoverage = prepared?.context_preview?.document_research
    ?.processing_coverage;
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
  const temporalEvidencePointCount = discoveredUnits.reduce(
    (total, row) => total + (row.requirement_components?.length ?? 0),
    0,
  );
  const completeRetainedReview = processingCoverage?.policy ===
    "tree_native_comprehensive_batches" && processingCoverage.unexamined_count === 0;
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
                      : e.accepted_review
                        ? "Response accepted by you; experience commit pending"
                        : evaluation
                          ? "Evaluated response awaiting your acceptance"
                          : "Experience awaiting evaluation"}
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
                        {e.accepted_review
                          ? "Retry governed commit"
                          : "Retry captured evaluation"}
                      </button>
                    )}
                    {!commit &&
                      evaluation &&
                      evaluation.result !== "INCOMPLETE" &&
                      !e.accepted_review &&
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
                          {evaluation.result === "PASS"
                            ? "Accept response and commit experience"
                            : "Accept reviewed response and commit experience"}
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
      <GemmaInspection key={project.id} project={project} objects={objects} draft={draft} backend={backend} />
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
          <NativeMemoryAnswer project={project} draft={draft} backend={backend} disabled={busy || waiting} />
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
                    {completeRetainedReview
                      ? "Tom Assist examined the full retained project-document inventory for this question."
                      : "This is a retrieved evidence subset, not a complete requirements inventory."}
                  </strong>
                  <p>
                    {selectedEvidenceCount} contract excerpt
                    {selectedEvidenceCount === 1 ? " is" : "s are"} shown
                    {excludedEvidenceCount
                      ? `; ${excludedEvidenceCount} other contract candidate${excludedEvidenceCount === 1 ? " was" : "s were"} excluded by the packet budget.`
                      : "."}
                    {completeRetainedReview
                      ? ` ${processingCoverage?.examined_count ?? 0} Tree-ranked passages were examined; this remains source evidence, not a legal conclusion.`
                      : " Tom Assist has not counted every requirement in the deed."}
                  </p>
                </div>
              )}
              {!!discoveredUnits.length && (
                <section class="chat-research-coverage" aria-label="Document research coverage">
                  <h4>Prerequisite coverage found in the project documents</h4>
                  <p>
                    Tom Assist found {discoveredUnits.length} authored evidence unit
                    {discoveredUnits.length === 1 ? "" : "s"}: {projectWideCount} project-wide and {activityConditionalCount} activity-conditional.
                    {" "}A unit may contain both kinds of condition.
                    {temporalEvidencePointCount
                      ? ` They contain ${temporalEvidencePointCount} distinct source-located pre-start trigger points; one point can govern several separately numbered actions.`
                      : ""}
                    {" "}{selectedEvidenceCount} fit in this outgoing packet; the remainder are still recorded below, not silently discarded.
                  </p>
                  <p>
                    <strong>Coverage boundary:</strong>{" "}
                    {completeRetainedReview
                      ? "Every retained passage was consumed in native Tree rank order, with exact authored expansions and references. Missing external schedules or referenced material remain outside that boundary."
                      : "This is limited to regions selected by the project document Tree and their exact authored expansions or references—not every requirement in the deed."}
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
                            {requirementCount} top-level numbered paragraph
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

type NativeAnswer = {
  status: "supported" | "partial" | "not_supported" | "ambiguous" | "blocked";
  answer: string;
  scope?: string;
  engine?: string;
  sources: { source_id: string; text: string; provenance: {
    clause?: string; pdf_page?: number; display_name?: string; doc_id?: string; chunk_id?: string;
    start?: number; end?: number; answer_start?: number; answer_end?: number;
  } }[];
  structural_sources?: { source_id: string; text: string; provenance: {
    display_name?: string; doc_id?: string; chunk_id?: string; start?: number; end?: number;
  } }[];
  authority_review?: {
    status: "unresolved";
    can_record: boolean;
    relation_kind: "replacement_cover" | "reimbursement" | "before" | "document_status";
    authority_scope?: { kind: "temporal_motif"; temporal_motif: {
      relation_kind: "sequence"; source_event: string; intermediate_event: string; target_event: string;
    } } | { kind: "source_claim"; claim_type: "document_status"; subject: string } | null;
    conflict_sources: AuthoritySource[];
    current_sources: AuthoritySource[];
  } | null;
};

type AuthoritySource = { source_id: string; text: string; reason?: string; active: boolean; provenance: {
  display_name?: string; doc_id: string; chunk_index: number; start: number; end: number;
} };

function SourceAuthorityReview({ project, backend, review }: {
  project: Project; backend: DesktopBackend; review: NonNullable<NativeAnswer["authority_review"]>;
}) {
  const choices = [...review.conflict_sources, ...review.current_sources].filter(
    (source, index, all) => all.findIndex((item) => item.source_id === source.source_id) === index);
  const [newer, setNewer] = useState(review.conflict_sources[0]?.source_id ?? choices[0]?.source_id ?? "");
  const [older, setOlder] = useState<string[]>([]);
  const [effectiveAt, setEffectiveAt] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  function toggle(sourceId: string) {
    setOlder((current) => current.includes(sourceId)
      ? current.filter((value) => value !== sourceId) : [...current, sourceId]);
  }
  async function record() {
    setBusy(true); setMessage(""); setError("");
    try {
      await backend.chat(project.id, "conversation.native_answer", {
        action: "resolve_source_authority", explicit_user_action: true,
        project_state_version: project.state_version, relation_kind: review.relation_kind,
        authority_scope: review.authority_scope,
        superseding_source_id: newer, superseded_source_ids: older,
        effective_at: effectiveAt.trim(), reason: reason.trim(),
      });
      setMessage("Source authority recorded. Ask the question again to apply it.");
    } catch (value) { setError(String(value)); }
    finally { setBusy(false); }
  }
  return <section class="source-authority-review" aria-label="Resolve conflicting source authority">
    <h4>Conflicting source authority</h4>
    <p>Choose the controlling passage and every passage it replaces for this exact relationship, event sequence or source claim. This does not change the ToM tree.</p>
    <label>Controlling passage<select aria-label="Controlling passage" value={newer}
      onChange={(event) => { const selected = event.currentTarget.value; setNewer(selected);
        setOlder((current) => current.filter((sourceId) => sourceId !== selected)); }} disabled={busy}>
      {choices.map((source) => <option value={source.source_id} key={source.source_id}>
        {source.provenance.display_name ?? source.provenance.doc_id} · passage {source.provenance.chunk_index + 1}
      </option>)}
    </select></label>
    {review.conflict_sources.map((source) => <details key={source.source_id}>
      <summary>{source.provenance.display_name ?? source.provenance.doc_id}: {source.reason}</summary>
      <p style={{ whiteSpace: "pre-wrap" }}>{source.text}</p>
    </details>)}
    {!review.can_record && <p>The recorded controlling passage was not among the retrieved evidence. No new authority decision can be made from this result.</p>}
    {review.can_record && <>
    <fieldset disabled={busy}><legend>Passages replaced</legend>
      {choices.filter((source) => source.source_id !== newer).map((source) => <div key={source.source_id}>
        <label><input type="checkbox" aria-label={`Replace ${source.provenance.display_name ?? source.provenance.doc_id} passage ${source.provenance.chunk_index + 1}`}
          checked={older.includes(source.source_id)} onChange={() => toggle(source.source_id)} />
          {source.provenance.display_name ?? source.provenance.doc_id} · passage {source.provenance.chunk_index + 1}
        </label>
        <details><summary>View passage</summary>
          <p style={{ whiteSpace: "pre-wrap" }}>{source.text}</p>
        </details>
      </div>)}
    </fieldset>
    <label>Effective time, including timezone<input aria-label="Source authority effective time"
      placeholder="2026-09-17T00:00:00+10:00" value={effectiveAt}
      onInput={(event) => setEffectiveAt(event.currentTarget.value)} disabled={busy} /></label>
    <label>Reason<input aria-label="Source authority reason" value={reason}
      onInput={(event) => setReason(event.currentTarget.value)} disabled={busy} /></label>
    <button disabled={busy || !newer || !older.length || !effectiveAt.trim() || !reason.trim()}
      onClick={() => void record()}>{busy ? "Recording source authority…" : "Record source supersession"}</button>
    </>}
    {message && <p role="status">{message}</p>}
    {error && <p role="alert">{error}</p>}
  </section>;
}

function ReviewedSituation({ project, backend, source }: {
  project: Project; backend: DesktopBackend; source: NativeAnswer["sources"][number];
}) {
  const proof = source.provenance;
  const chunk = proof.chunk_id?.match(/^chunk_(\d+)$/);
  const chunkIndex = chunk ? Number(chunk[1]) : -1;
  const [failureParty, setFailureParty] = useState("");
  const [coverPayer, setCoverPayer] = useState("");
  const [repaymentFrom, setRepaymentFrom] = useState("");
  const [repaymentTo, setRepaymentTo] = useState("");
  const [repaymentWhen, setRepaymentWhen] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  if (!proof.doc_id || chunkIndex < 0) return null;
  async function remember() {
    setBusy(true); setMessage(""); setError("");
    const roles = Object.fromEntries(Object.entries({
      failure_party: failureParty.trim(), cover_payer: coverPayer.trim(),
      repayment_from: repaymentFrom.trim(), repayment_to: repaymentTo.trim(),
      repayment_when: repaymentWhen.trim(),
    }).filter(([, value]) => value));
    try {
      const result = await backend.chat(project.id, "conversation.native_answer", {
        action: "learn_situation", explicit_user_action: true,
        project_state_version: project.state_version, document_id: proof.doc_id,
        chunk_index: chunkIndex, roles,
      }) as { duplicate?: boolean; write_count?: number };
      setMessage(result.duplicate
        ? "This reviewed relationship is already in ToM."
        : `Saved in ToM across ${Number(result.write_count ?? 0).toLocaleString()} memory locations.`);
    } catch (reason) { setError(String(reason)); }
    finally { setBusy(false); }
  }
  async function rememberNoticeBeforeMeeting() {
    setBusy(true); setMessage(""); setError("");
    try {
      const result = await backend.chat(project.id, "conversation.native_answer", {
        action: "learn_situation", explicit_user_action: true,
        project_state_version: project.state_version, document_id: proof.doc_id,
        chunk_index: chunkIndex, temporal_motif: {
          relation_kind: "before", source_event: "notify", target_event: "meeting",
        },
      }) as { duplicate?: boolean; write_count?: number; bound_existing_relationships?: number };
      setMessage(result.duplicate
        ? "This reviewed sequence is already in ToM."
        : result.write_count === 0
          ? "Linked this source to the existing ToM sequence memory."
          : `Saved the sequence in ToM across ${Number(result.write_count ?? 0).toLocaleString()} memory locations.`);
    } catch (reason) { setError(String(reason)); }
    finally { setBusy(false); }
  }
  return <details class="reviewed-situation">
    <summary>Save a reviewed structure in ToM</summary>
    <p>Use this only when the quoted passage says one party failed to show insurance compliance and another may buy replacement cover. Copy the party names exactly from the source.</p>
    <label>Party that failed to show compliance<input value={failureParty}
      onInput={(event) => setFailureParty(event.currentTarget.value)} disabled={busy} /></label>
    <label>Party that may buy replacement cover<input value={coverPayer}
      onInput={(event) => setCoverPayer(event.currentTarget.value)} disabled={busy} /></label>
    <label>Party that must repay, if stated<input value={repaymentFrom}
      onInput={(event) => setRepaymentFrom(event.currentTarget.value)} disabled={busy} /></label>
    <label>Party receiving repayment, if stated<input value={repaymentTo}
      onInput={(event) => setRepaymentTo(event.currentTarget.value)} disabled={busy} /></label>
    <label>When repayment is due, if stated<input value={repaymentWhen}
      onInput={(event) => setRepaymentWhen(event.currentTarget.value)} disabled={busy} /></label>
    <button disabled={busy || !failureParty.trim() || !coverPayer.trim()} onClick={() => void remember()}>
      {busy ? "Saving reviewed relationship…" : "Save reviewed relationship"}
    </button>
    <hr />
    <p>If this passage explicitly requires written notice before a meeting, save that reviewed sequence once or link this source to it.</p>
    <button disabled={busy} onClick={() => void rememberNoticeBeforeMeeting()}>
      {busy ? "Saving reviewed structure…" : "Save notice-before-meeting structure"}
    </button>
    {message && <p role="status">{message}</p>}
    {error && <p role="alert">{error}</p>}
  </details>;
}

export function NativeMemoryAnswer({ project, draft, backend, disabled = false }: {
  project: Project; draft: string; backend: DesktopBackend; disabled?: boolean;
}) {
  const [ready, setReady] = useState(false);
  const [scope, setScope] = useState("");
  const [engine, setEngine] = useState("native");
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState<NativeAnswer>();
  const [error, setError] = useState("");
  const revision = useRef(0);
  useEffect(() => {
    let active = true;
    setReady(false);
    void backend.chat(project.id, "conversation.native_answer", { action: "status" }).then((raw) => {
      if (!active) return;
      const state = raw as { ready: boolean; scope?: string; engine?: string };
      setReady(state.ready === true); setScope(state.scope ?? ""); setEngine(state.engine ?? "native");
    }).catch(() => { if (active) setReady(false); });
    return () => { active = false; };
  }, [project.id, project.state_version, backend]);
  useEffect(() => {
    revision.current += 1; setAnswer(undefined); setError(""); setBusy(false);
    return () => { revision.current += 1; };
  }, [project.id, project.state_version, draft]);
  async function ask() {
    const ticket = ++revision.current;
    setBusy(true); setAnswer(undefined); setError("");
    try {
      const result = await backend.chat(project.id, "conversation.native_answer", {
        action: "answer", explicit_answer: true, project_state_version: project.state_version, question: draft,
      }) as NativeAnswer;
      if (revision.current === ticket) {
        setAnswer(result);
        if (result.scope) setScope(result.scope);
        if (result.engine) setEngine(result.engine);
      }
    } catch (e) {
      if (revision.current === ticket) setError(String(e));
    } finally { if (revision.current === ticket) setBusy(false); }
  }
  if (!ready) return null;
  const rgmEngine = engine.startsWith("rgm");
  return <section class="chat-preview" aria-label={rgmEngine ? "Experimental document answers" : "Learned document answers"}>
    {scope && <p>{scope}</p>}
    <button disabled={disabled || busy || !draft.trim() || draft.length > 4000} onClick={() => void ask()}>
      {busy ? "Reading documents…" : rgmEngine ? "Answer from project documents" : "Answer from learned documents"}
    </button>
    {busy && <p role="status">Finding relevant passages and checking the evidence locally.</p>}
    {error && <p role="alert">{error}</p>}
    {answer && <article aria-label="Answer from learned documents">
      <h3>{({ supported: "Supported answer", partial: "Partly supported answer", not_supported: "Not supported",
        ambiguous: "Needs clarification", blocked: "Answer unavailable" })[answer.status]}</h3>
      <p style={{ whiteSpace: "pre-wrap" }}>{answer.answer}</p>
      {answer.authority_review && <SourceAuthorityReview project={project} backend={backend}
        review={answer.authority_review} />}
      {answer.sources.map((source) => {
        const proof = source.provenance;
        const points = Array.from(source.text);
        const from = (proof.answer_start ?? proof.start ?? 0) - (proof.start ?? 0);
        const to = (proof.answer_end ?? proof.start ?? 0) - (proof.start ?? 0);
        const highlight = from >= 0 && to > from && to <= points.length;
        return <details key={source.source_id}>
          <summary>{proof.display_name ? `Source: ${proof.display_name} · ${proof.chunk_id}`
            : `Source: clause ${proof.clause}, page ${proof.pdf_page}`}</summary>
          <p style={{ whiteSpace: "pre-wrap" }}>{highlight ? <>{points.slice(0, from).join("")}<mark>{points.slice(from, to).join("")}</mark>{points.slice(to).join("")}</> : source.text}</p>
          <ReviewedSituation project={project} backend={backend} source={source} />
        </details>;
      })}
      {!!answer.structural_sources?.length && <section aria-label="Evidence linked by learned structure">
        <h4>Evidence linked by the learned structure</h4>
        <p>ToM reopened this pattern. RGM supplied every exact passage linked to it.</p>
        {answer.structural_sources.map((source) => <details key={`structural-${source.source_id}`}>
          <summary>{source.provenance.display_name
            ? `${source.provenance.display_name} · ${source.provenance.chunk_id}`
            : source.source_id}</summary>
          <p style={{ whiteSpace: "pre-wrap" }}>{source.text}</p>
        </details>)}
      </section>}
    </article>}
  </section>;
}

type InspectionSpan = { start: number; end: number; quote: string };
type InspectionResult = {
  source?: { text: string; full_text: string; start: number; end: number; id: string; kind: string };
  stages: { stage: string; status: string; reason: string; elapsed_ms?: number }[];
  graph?: {
    entities: { id: string; name: string; mentions: InspectionSpan[] }[];
    events: { id: string; action: string; modality: string; negated: boolean; roles: Record<string, string | null>;
      condition: string | null; exception: string | null; evidence: InspectionSpan[] }[];
    predicates: { id: string; subject: string; comparator: string; value: string; unit: string; negated: boolean; evidence: InspectionSpan[] }[];
    conditions: unknown[]; links: unknown[]; unresolved: unknown[];
  };
  normalization?: { changed: boolean; policy: string };
  runtime?: { interpretation: string; responses: unknown[]; state_unchanged: boolean };
  compiled?: { loads: { id: string; kind: string; matrix_sha256: string; matrix: number[][] }[] };
  purity: Record<string, { unchanged?: boolean | null }>;
  quality_limits?: string;
};

/** Explicit inspection only; results are component state, never conversation state. */
export function GemmaInspection({ project, objects, draft, backend }: {
  project: Project; objects: StateObject[]; draft: string; backend: DesktopBackend;
}) {
  const [enabled, setEnabled] = useState(false);
  const [mode, setMode] = useState("saved");
  const [sourceId, setSourceId] = useState("draft");
  const [adapter, setAdapter] = useState("");
  const [query, setQuery] = useState(false);
  const [checkpoint, setCheckpoint] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<InspectionResult>();
  const [spans, setSpans] = useState<InspectionSpan[]>([]);
  const input = useRef<HTMLTextAreaElement>(null);
  const sequence = useRef(0);
  const selectedObject = objects.find((o) => o.id === sourceId && o.project_id === project.id && o.status === "active");
  const text = sourceId === "draft" ? draft : selectedObject?.canonical_text ?? "";
  useEffect(() => {
    sequence.current++;
    setResult(undefined); setError(""); setBusy(false); setSpans([]);
    return () => { sequence.current++; };
  }, [project.id, project.state_version, text, mode, sourceId, enabled, adapter, query, checkpoint]);
  async function inspect() {
    const current = ++sequence.current;
    const area = input.current;
    const from = area && area.selectionEnd > area.selectionStart ? Array.from(text.slice(0, area.selectionStart)).length : 0;
    const to = area && area.selectionEnd > area.selectionStart ? Array.from(text.slice(0, area.selectionEnd)).length : Array.from(text).length;
    const source = mode === "saved" ? { kind: "saved_example" } : {
      kind: sourceId === "draft" ? "draft" : "state_object", id: sourceId,
      version: selectedObject?.content_hash ?? `draft-at-project-version-${project.state_version}`,
      text, start: from, end: to,
    };
    setBusy(true); setError(""); setResult(undefined); setSpans([]);
    try {
      const next = await backend.chat(project.id, "inspection.gemma", {
        opt_in: true, explicit_inspect: true, project_state_version: project.state_version,
        extraction_mode: mode, adapter_id: adapter, source,
        query_stream1: query, checkpoint_id: checkpoint,
      }) as InspectionResult;
      if (current === sequence.current) setResult(next);
    } catch (e) {
      if (current === sequence.current) setError(String(e));
    } finally {
      if (current === sequence.current) setBusy(false);
    }
  }
  function highlighted(value: string) {
    const points = Array.from(value);
    const boundaries = [...new Set([0, points.length, ...spans.flatMap((s) => [s.start, s.end])])]
      .filter((n) => n >= 0 && n <= points.length).sort((a, b) => a - b);
    return boundaries.slice(0, -1).map((start, i) => {
      const end = boundaries[i + 1]!;
      const segment = points.slice(start, end).join("");
      return spans.some((s) => s.start <= start && s.end >= end)
        ? <mark key={start}>{segment}</mark> : <span key={start}>{segment}</span>;
    });
  }
  return <details class="chat-preview gemma-inspection">
    <summary>Experimental local inspection</summary>
    <label><input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.currentTarget.checked)} /> Enable inspection for this project view</label>
    {enabled && <section aria-label="Gemma inspection">
      <p>Inspect a proposed interpretation. Results stay in this panel and require semantic review.</p>
      <label>Extraction source <select aria-label="Extraction source" value={mode} onChange={(e) => setMode(e.currentTarget.value)}>
        <option value="saved">Saved V14 example — wiring check</option><option value="gemma">Local Gemma — selected passage</option>
      </select></label>
      <label>Selected adapter <select aria-label="Selected adapter" value={adapter} onChange={(e) => setAdapter(e.currentTarget.value)}>
        <option value="">Choose an adapter</option><option value="v14-4380">Retained V14 · 4,380 steps</option>
      </select></label>
      {mode === "saved" ? <p>The saved example contains a stop requirement and a notification sharing a condition. It is an exposed development example, not a fresh language check.</p> : <>
        <label>Passage source <select aria-label="Passage source" value={sourceId} onChange={(e) => setSourceId(e.currentTarget.value)}>
          <option value="draft">Current unsent draft</option>
          {objects.filter((o) => o.project_id === project.id && o.status === "active").map((o) => <option key={o.id} value={o.id}>{o.title}</option>)}
        </select></label>
        <label>Original passage — select a portion, or inspect the whole passage<textarea ref={input} aria-label="Inspection passage" value={text} readOnly rows={5} /></label>
        <p>At most 4,000 selected characters. Keep the preceding sentence when it supplies a name or shared condition.</p>
      </>}
      <label><input type="checkbox" checked={query} onChange={(e) => setQuery(e.currentTarget.checked)} /> Query separately loaded Stream 1 state</label>
      {query && <label>Experiment checkpoint <select aria-label="Experiment checkpoint" value={checkpoint} onChange={(e) => setCheckpoint(e.currentTarget.value)}>
        <option value="">Choose a checkpoint</option><option value="paired16-initial">Verified sixteen-branch starting state</option>
      </select></label>}
      {query && <p>Raw matrix diagnostics only. Understanding of this compiler’s encoding is unverified; no teaching or state updates occur.</p>}
      <button disabled={busy || !adapter || (query && !checkpoint) || (mode === "gemma" && !text)} onClick={() => void inspect()}>
        {mode === "saved" ? "Inspect saved example" : "Inspect selected passage"}
      </button>
      {busy && <p role="status">Inspecting locally…</p>}
      {error && <p role="alert">{error}</p>}
      {result && <section aria-label="Inspection results">
        <h3>Inspection outcomes</h3>
        <ol>{result.stages.map((s) => <li key={s.stage}><strong>{s.stage}: {s.status.replaceAll("_", " ")}</strong> — {s.reason}</li>)}</ol>
        {result.source && <>
          <h4>Exact inspected text</h4>
          <p>Source {result.source.id} · characters {result.source.start}–{result.source.end}. Choose a role or requirement to highlight its evidence.</p>
          <p style={{ whiteSpace: "pre-wrap" }}>{highlighted(result.source.text)}</p>
          <details><summary>Original source and selection</summary><pre style={{ whiteSpace: "pre-wrap" }}>{result.source.full_text}</pre></details>
        </>}
        {result.graph?.events.map((event) => <article key={event.id}>
          <h4><button onClick={() => setSpans(event.evidence)}>{event.id}: {event.negated ? "must not " : ""}{event.action} · {event.modality}</button></h4>
          <dl>{Object.entries(event.roles).map(([role, id]) => {
            const entity = result.graph?.entities.find((e) => e.id === id);
            return <div key={role}><dt>{role}</dt><dd>{entity ? <button onClick={() => setSpans(entity.mentions)}>{entity.name}</button> : "not specified"}</dd></div>;
          })}</dl>
          <p>Condition: {event.condition ?? "none"} · Exception: {event.exception ?? "none"}</p>
        </article>)}
        {!!result.graph?.predicates.length && <section aria-label="Extracted conditions"><h4>Conditions and quantities</h4>
          {result.graph.predicates.map((p) => <p key={p.id}><button onClick={() => setSpans(p.evidence)}>
            {p.id}: {p.negated ? "not " : ""}{result.graph?.entities.find((e) => e.id === p.subject)?.name ?? p.subject} {({ GT: ">", GE: "≥", LT: "<", LE: "≤", EQ: "=", NE: "≠" } as Record<string, string>)[p.comparator] ?? p.comparator} {p.value} {p.unit}
          </button></p>)}
        </section>}
        {result.graph && <details><summary>Conditions, quantities and event links</summary><pre>{JSON.stringify({ predicates: result.graph.predicates, conditions: result.graph.conditions, links: result.graph.links, unresolved: result.graph.unresolved }, null, 2)}</pre></details>}
        {result.normalization?.changed && <p role="note">The existing parser applied normalization. Both original and normalized graphs are retained below for review.</p>}
        {result.compiled && <details><summary>Ordered matrix loads ({result.compiled.loads.length})</summary>{result.compiled.loads.map((load, index) => <details key={load.id}>
          <summary>{index + 1}. {load.kind} {load.id} · {load.matrix_sha256.slice(0, 12)}</summary><pre style={{ maxHeight: "20rem", overflow: "auto" }}>{JSON.stringify(load, null, 2)}</pre>
        </details>)}</details>}
        {result.runtime && <><p>{result.runtime.interpretation}</p><details><summary>Raw Stream 1 response and trace</summary><pre style={{ maxHeight: "24rem", overflow: "auto" }}>{JSON.stringify(result.runtime, null, 2)}</pre></details></>}
        <p>Live runtime unchanged: {result.purity.live_runtime?.unchanged === true ? "verified" : "not verified"}. Project ledger unchanged: {result.purity.ledger?.unchanged === true ? "verified" : "not verified"}.</p>
        <p>{result.quality_limits}</p>
        <details><summary>Full diagnostic receipt: identities, evidence, timing and purity</summary><pre style={{ maxHeight: "24rem", overflow: "auto" }}>{JSON.stringify(result, null, 2)}</pre></details>
      </section>}
    </section>}
  </details>;
}
