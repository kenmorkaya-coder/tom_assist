import { useEffect, useRef, useState } from "preact/hooks";
import type { ChatMethod, DesktopBackend } from "./backend";
import type { Project, StateObject, InterventionRecord } from "./types";

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
}
export interface ConversationView {
  session: Conversation;
  exchanges: {
    exchange: Exchange;
    evaluation?: { result: string; turn_id: string };
    commit?: unknown;
  }[];
  interventions: (InterventionRecord & { turn_id: string })[];
}
export interface ProviderStatus {
  connected: boolean;
  code: string;
  model?: string;
  streaming?: boolean;
  capabilities?: Record<string, unknown>;
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
              ? "Runtime OAuth connected"
              : "OAuth not connected — connect in the ToM runtime"}{" "}
            · model: {provider?.model ?? "runtime-managed"}
          </p>
        </div>
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
        Only Send with Tom transmits your visible packet, bounded conversation
        history and draft. Credentials stay in the connected runtime. Responses
        arrive when complete; no token streaming or hidden-context visibility is
        claimed. Conversation text and approved prompts are retained locally and
        in complete archives, unencrypted. No automatic expiry is applied.
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
          .map(({ exchange: e, evaluation, commit }) => (
            <article key={e.id} class="chat-exchange">
              <div class="chat-message user">
                <strong>You</strong>
                <p>{e.user_draft}</p>
              </div>
              <div class="chat-message assistant">
                <strong>Assistant</strong>
                {e.response_text ? (
                  <p>{e.response_text}</p>
                ) : (
                  <p role="status">
                    {e.status === "sending"
                      ? "Waiting for the connected runtime…"
                      : "No response captured. Provider outcome may be unknown; check the runtime before a new send."}
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
              <h3>Review before sending</h3>
              <p>Packet digest: {prepared.packet_digest}</p>
              <details open>
                <summary>Exactly what will be sent</summary>
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
