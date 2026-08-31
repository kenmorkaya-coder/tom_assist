# Governed desktop chat (WP-21)

Implementation/build verification only, **NOT-A-GATE**. No product-owned login,
token refresh, credentials, API key, provider SDK or direct OpenAI HTTP transport.

## Connect the already running runtime

Connect OAuth in the owner's existing ToM runtime. Leave its provider set to
OpenAI and its auth mode set to OAuth while a send is in flight. Tom Assist does
not launch, reconfigure, log into or switch that runtime. Start the Tom Assist
gateway with `TOM_ASSIST_OAUTH_RUNTIME_URL` set to the existing runtime's HTTP
origin: literal `127.0.0.1` or `[::1]`, with its actual explicit port. There is no
default, scanning or discovery of owner services. Port **18790 is refused**.
Paths, credentials, query strings, fragments, remote hosts and redirects are
refused. The URL is configuration, never stored in the project ledger.

Desktop, daemon and gateway share `TOM_ASSIST_APP_SUPPORT`,
`TOM_ASSISTD_SOCKET` and `TOM_ASSIST_GATEWAY_SOCKET` as in the development runner.
The normal packaged app still requires these installed local services; this WP
does not add bundled sidecars or start an owner runtime. In Chat, Refresh
connection checks the credential-free readiness endpoint. Missing configuration,
unreachable runtime or disconnected OAuth permits local preparation but disables
Send. Tom Assist has no login button and never calls `/api/oauth/push`.

## Runtime reuse, not auth reimplementation

Read-only inspection of `tom_master` at
`e9fdef81c8a366ebbec07be9772189eea15cb2ac` found the existing thin endpoint
`interface/desktop_api.py` `/api/llm/complete`. It calls
`integration.llm_provider.make_llm()` → `_make_openai_client()` → the runtime's
process-local `AuthProfileManager` / `CredentialType.OAUTH` from `auth_profiles.py`
→ `integration.openai_client.OpenAIClient.complete_text()` / `generate()`.
The endpoint constructs its normal client using the connected process's auth
state; Tom Assist does not instantiate an independently authenticated client.
Importing that factory into a different process would not reuse those in-memory
profiles/tokens. The existing HTTP bridge preserves this boundary.

The upstream client's OAuth Responses transport, refresh, semaphore, cross-process
flock, TPM bucket and retry policy remain upstream-owned. Tom Assist adds a
single-flight gateway limit of one, never increases the runtime concurrency cap,
does not override model/generation settings, and adds **no generation retries**.
The existing upstream client may itself retry infrastructure failures. Model is
honestly reported as **runtime-managed**, not inferred from the endpoint's
non-authoritative `default` response label. Prompts ask for a minimal reply in
the live test; the runtime controls the actual output limit and quota.

Status calls only `/api/oauth/status`; it does not refresh auth or generate.
After explicit Send only, the adapter checks `/api/llm/status` for OAuth-ready
OpenAI and calls `/api/llm/complete` with the approved `prompt` only. It never
uses `/api/chat` or `/api/chat/stream`, which would run the owner's ToM loop.
Only whitelisted output fields and generic error codes leave the gateway;
upstream headers, config fields, masked keys and raw errors are discarded.

Boundary limitation: the pinned runtime does not expose an atomic
“OAuth-only completion” parameter. Its config could change between readiness
and completion. Keep provider/auth mode stable during sends; the adapter
preflights and refuses observed mismatches but cannot claim an atomic auth-mode
pin without an upstream change. No upstream change is made here. Readiness is
local auth state, not proof that a network request or quota check will succeed.
The upstream `/api/llm/status` API-key branch can validate remotely if the owner
changes mode between the two checks; it is consequently never part of preview.

OpenAI's [official authentication documentation](https://learn.chatgpt.com/docs/auth)
distinguishes ChatGPT sign-in from separately billed API keys and describes cached
credentials as private. This implementation reuses the runtime's existing
integration, not a new generally available OAuth client registration or a claim
of entitlement to API-key billing through ChatGPT sign-in.

## Conversation and consent

Select a project, create/select a conversation, compose, and choose **Preview
packet**. The entire exact outgoing prompt is visible: current governed packet,
at most 12 complete local historical messages totalling at most 12,000 characters,
and the current draft (maximum 16,000 characters). Oversize messages are omitted
whole; total prompt has a 48,000-character safety limit. These are character
bounds, not claims of an exact tokenizer. Prior text is marked untrusted, not
new authority. Each conversation has a session-specific workstream for packet
identity. New desktop/chat decisions are project-wide; existing workstream-scoped
objects retain their original scope. No golden, scoring policy or physics changed.

Only **Send with Tom** submits. Enter inserts a newline. Editing the draft or
native state invalidates the visible approval. Send checks project, session,
ordinal, state version, runtime checkpoint and the exact persisted prompt hash,
then atomically claims the exchange and binds its sent turn. One exchange can
be generating/evaluating per project. Ordinary repeated clicks, remounts and
restarts cannot claim it again. A packet already bound to a sent turn remains
bound: retrying the same unchanged draft after an unknown outcome may require
a genuinely new draft/context, not bypassing the duplicate-send guard.

The UI shows waiting state, then the full captured response. The pinned endpoint
buffers output: **no token streaming** is claimed. Honest ProviderCapabilities:
visible prompt injection and response capture true; hidden-context visibility
false; model-internal bias `none`; system-field support false. No hidden provider
history is assumed. Conversations, approved prompts, drafts, full responses,
governance results and receipts persist locally, including across restart.
**Chat retains full text, including in complete project archives; it is not
encrypted or automatically expired by the legacy retention selector.**

Captured output goes through the existing production governance path. PASS
applies the existing five-dynamics experience once; REVIEW without findings waits
for **Accept reviewed exchange**; CONFLICT/open findings wait for explicit
resolution. The badge describes the evaluation, not a spec gate. Pending runtime
commit can be retried against the saved response without contacting the provider.
Accept finding / false positive / dismiss retain WP-17's existing resolution and
teach-on-dismissal policy. The stored receipt identifies committed experience.

Assistant text is never automatically authoritative. **Review capture /
supersession** opens editable text. **Confirm decision** is a separate explicit
user action; the native boundary checks a complete assistant turn in this
project/session and refuses unresolved findings. Supersession also requires an
existing target, current state version and non-empty reason, preserving the old
object and source-turn lineage. Capture changes native state, not another runtime
experience step.

Timeout/lost response is an **unknown outcome**, not proof nothing was sent.
There is no automatic resend or remote cancellation. On daemon restart, an
unowned `sending` intent becomes unknown. Check the owner runtime before a new
send. A durably captured response can be evaluated/retried offline from that
capture; the five-dynamics idempotency key survives crash, restart and archive.
WP-20 archives without both new conversation tables remain readable; current
archives include both plus `provider_sessions`. Missing arbitrary tables still
fail closed. A recovery import never generates.

## Verification and opt-in live test

The normal Rust, gateway and UI tests use deterministic provider fixtures; the
real gateway still performs preview/governance/commit against disposable local
runtime state. The packaged journey also routes through the production provider
adapter but supplies a localhost HTTP fixture, overrides any inherited owner URL,
and makes zero real OAuth exchanges. See [project recovery](PROJECT_RECOVERY.md).

The single live test is ignored by default. Explicitly configure the real runtime
origin above, opt in with `TOM_ASSIST_LIVE_OAUTH=1`, then run:

```sh
cargo test -p tom-assistd --test conversations live_oauth_one_disposable_exchange -- --ignored --nocapture
```

It cleanly reports SKIP if not opted in or OAuth is disconnected/unconfigured.
It uses a disposable project, one minimal logical exchange (upstream retries may
apply), no parallel requests, and GET-only restart verification. It never reads
credentials and does not retry to turn a live failure green. A skipped test is
not evidence of a successful live exchange.
