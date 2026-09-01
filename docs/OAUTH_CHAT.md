# Governed desktop chat and Tom Assist OAuth

Implementation/build verification only, **NOT-A-GATE**. OAuth is now a
Tom Assist-owned package. It does not read TomOwner files, call the TomOwner app,
reuse its process, or share its credential store.

## Connect in Tom Assist

The packaged desktop starts `tom-assist-oauth` as its own sidecar. The developer
runner starts the same binary and gives the gateway its user-only Unix socket via
`TOM_ASSIST_OAUTH_BROKER_SOCKET`. No TCP service, port discovery or owner runtime
is involved. Port **18790 is never used**. In Chat, choose **Connect OAuth**. The
broker opens the provider authorization page and listens only on
`127.0.0.1:1455` for the registered callback. The user completes sign-in in the
browser; Tom Assist never asks the user to type credentials into its webview.

OAuth uses authorization-code PKCE-S256 with fresh verifier, state and nonce.
The callback requires the exact method, path and state. Before accepting tokens,
the broker requires an RS256 ID token and validates its signature from HTTPS
JWKS plus issuer, audience, expiry and nonce. Access/refresh tokens and the
provider account identifier are stored only in the macOS Keychain entry owned by
service `local.tom.assist.oauth`; in-memory secret records zeroize on drop. Logout
attempts provider revocation and always clears the local entry. Refresh occurs
inside the broker before a send and persists rotated refresh tokens.

The gateway sees only `/status` and `/complete` over a mode-0600 Unix socket.
Status is secret-free and never refreshes or generates. Completion accepts the
exact approved prompt only after both the desktop/daemon consent checks and the
broker's `explicit_send: true` check. The broker permits one concurrent
generation, makes one provider request, has no generation retry, and returns only
response text, resolved model label and completion state. No token, account ID,
authorization header or raw provider error crosses to the gateway, project
database, logs, recovery archive or webview.

The current provider exchange uses the owner-authorized compatibility client and
the provider's Codex Responses surface. It was derived from read-only inspection
of the previously approved integration behavior, but imports and calls none of
that source at runtime. This is intentionally documented as an owner-authorized,
undocumented compatibility path: OpenAI's public API reference documents API-key
and workload-identity bearer authentication, not a generally available third-party
ChatGPT subscription OAuth registration. It therefore must not be represented as
an official public OpenAI OAuth API or an entitlement/billing guarantee. A provider
contract change can require a product update. See the
[official API authentication reference](https://developers.openai.com/api/reference/overview).
An owner-issued replacement client registration can be supplied to the broker as
`TOM_ASSIST_OPENAI_OAUTH_CLIENT_ID`; no client secret is accepted or stored.

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
unowned `sending` intent becomes unknown. Check the Tom Assist connection and
provider account activity before a new send. A durably captured response can be evaluated/retried offline from that
capture; the five-dynamics idempotency key survives crash, restart and archive.
WP-20 archives without both new conversation tables remain readable; current
archives include both plus `provider_sessions`. Missing arbitrary tables still
fail closed. A recovery import never generates.

## Verification and opt-in live test

The normal Rust, gateway and UI tests use deterministic provider fixtures; the
real gateway still performs preview/governance/commit against disposable local
runtime state. The packaged journey also routes through the production provider
adapter but supplies a local Unix-socket broker fixture and makes zero real OAuth
exchanges. The packaged artifact separately contains the real broker binary. See
[project recovery](PROJECT_RECOVERY.md).

The single live test is ignored by default. Connect Tom Assist first, point the
gateway at that broker socket, opt in with `TOM_ASSIST_LIVE_OAUTH=1`, then run:

```sh
cargo test -p tom-assistd --test conversations live_oauth_one_disposable_exchange -- --ignored --nocapture
```

It cleanly reports SKIP if not opted in or OAuth is disconnected/unconfigured.
It uses a disposable project, one minimal logical exchange, no retry, no parallel
requests, and GET-only restart verification. The test process never reads
credentials and does not retry to turn a live failure green. A skipped test is
not evidence of a successful live exchange.
