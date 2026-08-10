# TOM ASSIST — ONE-SHOT BUILD INSTRUCTION

**To:** Codex (implementing engineer)
**From:** Claude (build orchestrator), on behalf of Ken Morkaya (owner)
**Repo root:** `/Users/kenmorkaya/PycharmProjects/ToM_assist`
**Date issued:** 9 August 2026

You are implementing Tom Assist per specification v1.2 in a single sustained build. This document is your contract. Where it conflicts with the spec, **this document wins** — every deviation in here was deliberately decided by the owner and orchestrator. Where both are silent, you decide, and record the decision in `BUILD_LOG.md`.

Read these three documents before writing any code:

1. `docs/spec/Tom_Assist_Build_Spec_v1.2.txt` — the full product/engineering specification (converted from the v1.2 docx; tables are flattened but complete).
2. `docs/spec/runtime_inspection_findings.md` — **binding** answers to the two runtime questions (preview mutation semantics, verifier semantics), with file:line anchors into tom_master.
3. `docs/spec/references_and_evidence.md` — repo pins, evidence anchors, claim boundaries.

---

## 0. Ground rules

- **Read-only repos:** `tom_master` (pinned `8799ccbdd`), `tom_sicd_gemma`, `tom_master17D`. You may read the first two; you must never write to any of them. `tom_master17D` is off-limits entirely — do not read, import, or reference it.
- **This repo is yours.** Initialize git here (`main`), commit the docs first, then work on branch `build/one-shot-v1` with one commit per work package (conventional commit messages, e.g. `feat(wp-03): tom gateway with preview purity tests`).
- **No LLM APIs, no network services, no cloud.** The product is local-first; the build must not add any network dependency beyond package registries at build time.
- **No gate claims.** You are building instruments (tests, harnesses, reports). You never report a spec G-gate (G1–G17) as *passed* — that authority belongs to the validation programme, run later by the owner. In-shot tests are labeled as build verification, not gate verdicts.
- **Escalation instead of silent judgment calls:** if you hit a genuine contradiction, missing fact, or a decision with product consequences not covered here, write an `ESCALATE:` entry in `BUILD_LOG.md` (question, options, your recommendation), pick the safest reversible default, and continue with non-dependent work. Do not stall the shot.

## 1. Definition of done (this shot)

The shot is complete when **all** of the following hold:

1. The Rust workspace compiles clean (`cargo build --workspace`) and `cargo test --workspace` is green.
2. The Python gateway serves against the real tom_master and its test suite (pytest) is green — including the **preview-purity test** (§7.4, non-negotiable).
3. The extension builds, loads unpacked in Chromium, and passes its unit/fixture tests.
4. The Tauri desktop app launches, supports project CRUD, ledger inspection, intervention review, and settings against a seeded demo project.
5. End-to-end on fixtures: draft → PREPARE_TURN → packet preview → simulated send → EVALUATE_TURN → intervention → user-gated commit → event log + digest verified across restart.
6. The validation harness scaffold exists (arms plumbing, runner, Appendix-C-format report emitter) with zero batteries authored.
7. `BUILD_LOG.md` documents every WP with evidence (test output), every deviation, every escalation.
8. No forbidden action (§10) was taken.

Explicitly **out of scope for this shot:** live chatgpt.com selector verification (fixtures only; graceful detach on mismatch is required behavior), signing/notarization, SQLCipher/Keychain (interface stubbed behind a feature flag, default off), the G-gate batteries themselves, and any Layer 2 / governed-model path beyond the capability negotiation stub.

## 2. Locked decisions (do not relitigate)

| # | Decision | Source |
|---|---|---|
| D1 | Runtime binding target is **tom_master @ `8799ccbdd`**, consumed read-only via a Python gateway sidecar living in **this** repo. Zero files added to tom_master. | Owner decision; `references_and_evidence.md` |
| D2 | **PREPARE_TURN is read-only by construction.** Preview ranks against last-committed structural state; the draft contributes only as `user_text`. Never call `rgm.read_memory()`, `ToMClient.process()`, or `engine.step()` in any preview path. The draft's load is applied exactly once, at commit. | `runtime_inspection_findings.md` Q1 |
| D3 | `TomCapabilities` reports honestly: `supports_readonly_ranking=true`, `supports_checkpoint_restore=true`, `supports_nonmutating_load_preview=false`. | Q1 |
| D4 | Checkpoints = `engine.save()/load()` + RGM `serialize()`; `tom_checkpoint_digest` = sha256 over the canonicalized saved artifacts. | Q1 |
| D5 | §12.2 interventions are computed by rendering the ledger into tom_master's verifier inputs via the gateway (`DriftVerifier`, `adjudicate_reasoning_structure`, `claim_verifier`), plus Rust-native deterministic ledger gates. Mapping: `block/revise/permit` ≈ `CONFLICT/REVIEW/PASS`. | Q2 |
| D6 | **One** state-block template (§6.2 below), `renderer_version="authoritative-state/1.0"`. It supersedes all three template variants in the spec (§6.9/§6.9.3/§11.5). | Orchestrator; paper Fig. 2 |
| D7 | Packet budget default **500 tokens** (evidence-anchored ≈2000 chars), user-configurable up to **1200** (CTX-001 ceiling). Token estimate = ceil(chars/4), documented as a heuristic. | Paper operating point |
| D8 | assistd↔ToM transport is the gateway's **Unix-domain socket** (user-only, 0600). Extension↔assistd stays Chrome Native Messaging per spec §6.3. The spec's JSONL/stdin-stdout option for the ToM adapter is not used. | Owner-approved deviation |
| D9 | Native-messaging payloads: any host→extension message >900 KB is chunked (`{correlation_id, seq, total, chunk_b64}`) and reassembled in the service worker. | Spec gap closure |
| D10 | Digest canonicalization (§6.3 below) is normative for `packet_digest`, state digests, and checkpoint digests. | Spec gap closure |
| D11 | MV3 service-worker suspension: all held transaction state (pending PREPARE_TURN, pending sends) persists in `chrome.storage.session` keyed by correlation ID and is restored on worker wake. | Spec gap closure |
| D12 | Extension ID stability: generate a keypair once, pin `key` in `manifest.json`; native-host manifest allowlists that exact ID. Store the private key outside git (`.gitignore`), document regeneration. | Spec gap closure |
| D13 | Alpha storage is plain SQLite (WAL). SQLCipher sits behind cargo feature `encrypted-store` (default off) with the key-loading path stubbed; Keychain wiring deferred. | Scope decision |
| D14 | UI stack: Preact + TypeScript + Vite for both the extension panel and the Tauri 2 desktop UI. | Consistency |
| D15 | Schemas: JSON Schema (draft 2020-12) is the source of truth in `crates/protocol/schemas/`. TypeScript types generated (`json-schema-to-typescript`); Rust types hand-written with serde and proven equivalent by round-trip conformance tests against shared example fixtures. | Simplicity over codegen toolchains |

## 3. Repository layout to create

Per spec §7.1, adjusted for D1/D8 (gateway lives here):

```
ToM_assist/
  BUILD_INSTRUCTION.md          # this file
  BUILD_LOG.md                  # your running log (create at WP-00)
  docs/spec/                    # already present — commit as-is
  apps/
    desktop/                    # Tauri 2 app (Rust core + Preact UI)
    extension/                  # MV3 extension (TS, Preact, Vite)
  crates/
    protocol/                   # JSON Schemas + Rust types + conformance tests
    persistence/                # SQLite event store, snapshots, digests
    assistd/                    # tom-assistd service (PREPARE_TURN/EVALUATE_TURN)
    native-host/                # Chrome Native Messaging bridge binary
    governance/                 # interventions, authority gates, verifier client
    context-admission/          # candidate collection, gates, scoring, budget
    tom-adapter/                # Rust client for the Python gateway (UDS)
  gateway/
    tom_gateway.py              # Python sidecar binding tom_master (D1)
    purity/                     # preview-purity test fixtures
    tests/
  packages/
    provider-adapters/          # ChatGPT adapter + DOM fixtures
    ui-components/
    schema-generated/           # generated TS types (build artifact, committed)
  tests/
    fixtures/provider-dom/
    integration/
    replay/
  scripts/
    dev-run.sh                  # start gateway + assistd + desktop dev mode
    install-native-host/
    package-macos/              # unsigned dev packaging only
```

## 4. Work packages, in order

Each WP ends with: tests green for that WP, a commit, and a `BUILD_LOG.md` entry with evidence. Do not start a WP whose dependency failed — escalate and reorder to non-dependent work.

| WP | Scope | Exit criteria |
|---|---|---|
| WP-00 | git init, commit docs, scaffold workspace, toolchain check (rustc, node, python3), `BUILD_LOG.md` created with toolchain versions | Workspace skeleton compiles (`cargo build`) |
| WP-01 | `crates/protocol`: JSON Schemas for envelope (§14.1), all §14.2 methods, ProviderCapabilities (§6.6), TomCapabilities (D3 flags + runtime_version + parity fields), StateObject (§10.3), edges (§10.4), ContinuityPacket (Appendix A.1), StateMutationCandidate (A.2), Intervention (§12.3), Error (§14.4). Generated TS. Rust serde types + round-trip conformance tests | Conformance tests green over shared example fixtures |
| WP-02 | `crates/persistence`: migrations for Appendix B tables; append-only event log with idempotency keys; materialized state; snapshots; canonical digests (D10); CAS on `state_version` (STATE-001..005, DB-001..005) | Event replay determinism test + 25× reopen digest-equality test green |
| WP-03 | `gateway/` + `crates/tom-adapter`: the ToM boundary (§7) | Gateway pytest green **including preview-purity**; Rust adapter integration test against live gateway green |
| WP-04 | `crates/assistd`: UDS server, protocol versioning, PREPARE_TURN and EVALUATE_TURN transactions (§6.7/§6.10 flow), single-writer-per-project, `packet_digest` binding, stale-packet invalidation (T-014/T-025 semantics) | Transaction tests green incl. concurrent-tab CAS conflict |
| WP-05 | `crates/native-host` + extension skeleton: framing, extension-ID allowlist, schema validation, correlation IDs, chunking (D9), session persistence (D11), pinned key (D12) | Handshake + oversize-payload + forged-message tests green (T-017 analog) |
| WP-06 | `packages/provider-adapters`: ProviderAdapter interface (§8.1 verbatim); ChatGPT adapter against **authored static fixtures** (composer, streaming, turn enumeration); health-check + detach-on-mismatch (§9.4); capture dedup (EXT-013) | Fixture suite green; unknown-DOM fixture triggers clean detach |
| WP-07 | `crates/context-admission` + renderer: candidate pools (§11.1), hard gates (§11.4), scoring contract (§11.3 shape, decomposed scores from gateway, policy_version logged), dependency-closed bundles with depth cap 2 and explicit missing-dependency marker (CTX-009), budget controller (D7, CTX-002/005), single renderer (D6, CTX-006/007/010) | Golden-packet tests green: given seeded ledger + draft → byte-stable packet + manifest + digest |
| WP-08 | `crates/governance`: EVALUATE_TURN evaluation states (§12.1), all 11 intervention codes (§12.2) computed per D5 (ledger→verifier rendering via gateway + native ledger gates), candidate mutations (deterministic + manual channels only, §7.3), commit gate (§10.5), correction-packet generation, false-positive recording | Seeded-conflict tests: each intervention code fires on its crafted fixture and not on clean fixtures |
| WP-09 | `apps/desktop`: Tauri 2 shell; project CRUD; ledger views (§9.1); state cards (§15.3 required fields); intervention review; supersede/reopen forms; settings; diagnostics panel; export/import (DB-005) | App launches; scripted UI smoke (project → capture → supersede → audit) passes |
| WP-10 | Extension UX: project chip, pre-send drawer (packet preview, warnings, exclusions), post-response badge, quick-capture toolbar, side panel (§8.4); EXT-020..025 behaviors incl. fail-open-with-warning | Extension e2e on fixture page: pause → preview → approve → insert → capture response |
| WP-11 | Validation harness scaffold: arms SUB-A..SUB-E plumbing (§18.1), replay runner over stored histories, deterministic out-of-process oracle interface copying the `verify_plant_recall.py` stdin/stdout pattern, Appendix-C-format report emitter, run manifest (G15 fields) | Harness dry-run on a 3-case toy battery emits a complete report; clearly labeled NOT-A-GATE |
| WP-12 | `scripts/`: dev-run, native-host installer (manifest to correct Chrome dir), unsigned .app packaging; end-to-end walkthrough doc `docs/DEV_RUNBOOK.md` | Fresh-checkout runbook works top to bottom |

## 5. The ToM gateway (WP-03) — precise contract

**Precedent to study (read, do not copy blindly):** `tom_master/interface/tom_as_assurance_gateway.py` — the existing pattern for a product binding tom_master. Yours lives in this repo and imports tom_master via `PYTHONPATH=/Users/kenmorkaya/PycharmProjects/tom_master`.

**Startup:** verify `git -C tom_master rev-parse HEAD` == `8799ccbdd`; if not, log a warning and expose the actual SHA in capabilities (`runtime_version`). Probe imports; create `.venv-gateway` and install only what the imports actually require (record the resolved dependency list in BUILD_LOG). Serve JSON over a Unix socket at `~/Library/Application Support/TomAssist/tom_gateway.sock` (0600).

**Per-project state:** one engine+memory instance per Tom Assist project, state directory `~/Library/Application Support/TomAssist/projects/<project_id>/tom/`. Inspect `controller/external_api.py::create_client` (`:2722`) and choose: (a) one ToMClient per project with isolated state paths, or (b) direct `TreeGrowthEngine` + RGM composition mirroring what `retrieve_ltm_with_stm_triggers` needs. Either is acceptable; the purity invariant (D2) is not negotiable. Record the choice with file:line evidence.

**Endpoints:**

| Endpoint | Semantics | Mutation |
|---|---|---|
| `GET /health` | liveness + pinned-SHA check | none |
| `GET /capabilities` | TomCapabilities (D3) + runtime_version + state_format_version | none |
| `POST /preview/rank` | `{project_id, user_text, k=10, max_chars=2000}` → triggers + ranked anchors + decomposed scores. **Pure path only** (D2): `compute_retrieval_triggers` / `vector_store.query`-style scoring. | **none — enforced** |
| `POST /turn/commit` | `{project_id, role, text, idempotency_key}` → exactly one processing pass; returns activation summary + optional new checkpoint digest | one step |
| `POST /checkpoint/save` | → engine.save + RGM serialize → `{checkpoint_id, digest}` | writes files |
| `POST /checkpoint/restore` | `{project_id, checkpoint_id}` | replaces in-memory state |
| `POST /verify/drift` | `{answer_text, invariants[], provenance}` → DriftVerifier decision + residuals + reasons | none |
| `POST /verify/claims` | `{claims[], corpus_chunks[]}` → support levels + citations | none |
| `POST /adjudicate/structure` | `{proposal, expected}` → adjudication + rejection codes | none |

**Idempotency:** `turn.commit` deduplicates on `idempotency_key` (return original result).

### 5.1 Preview-purity test (non-negotiable, part of WP-03 exit)

Pytest that: seeds a project, commits N turns, snapshots the serialized engine+RGM state to bytes, runs **100 mixed `/preview/rank` calls** (varying drafts, k, budgets), re-serializes, and asserts **byte-identical** state. Also assert `/preview/rank` never advances RGM `current_tick`. A second determinism test: identical preview inputs → identical outputs across process restarts. If purity cannot be achieved with the chosen composition, that is a **stop-and-escalate** — do not "fix" it by tolerating drift.

## 6. Normative formats

### 6.1 TomCapabilities (extends spec §9.3)

```json
{
  "runtime_version": "<tom_master git SHA>",
  "state_format_version": "sicd-engine-save/1",
  "supports_load_ingest": true,
  "supports_branch_activation": true,
  "supports_candidate_ranking": true,
  "supports_state_snapshot": true,
  "supports_commit": true,
  "supports_conflict_check": true,
  "supports_trajectory_digest": true,
  "supports_readonly_ranking": true,
  "supports_checkpoint_restore": true,
  "supports_nonmutating_load_preview": false
}
```

### 6.2 State block — the single template (D6)

Rendered by `crates/context-admission`'s renderer, `renderer_version="authoritative-state/1.0"`. Optional sections are omitted entirely when empty. Header style is underscore-caps exactly as shown. This merges the paper's Figure-2 instruction semantics (precedence over raw history, answer directly, anti-enumeration) with the spec's typed sections and §6.9.3 ordering:

```
[TOM_ASSIST_STATE v1 | project=<id> | workstream=<id> | state=<V> | digest=<first-12-hex>]
STATUS: authoritative prior project state generated locally by Tom Assist. Use as primary source of truth.
PRECEDENCE: current explicit user request > TOM_ASSIST_STATE > raw prior transcript > model inference.
ACTIVE_OBJECTIVE
- <...>
LOAD_BEARING_CONCEPTS
- <canonical definition/mechanism required by this turn>
BINDING_CONSTRAINTS
- <...>
HELD_DECISIONS
- <...>
REJECTED_OR_SUPERSEDED - DO NOT REVIVE WITHOUT EXPLICIT RECONSIDERATION
- <path> - <reason / reconsideration condition>
COMPLETED_WORK - DO NOT REPROPOSE AS OPEN
- <result> - <next boundary>
UNRESOLVED_DEPENDENCIES
- <...>
EVIDENCE_BOUNDARY
- <minimum provenance/integrity note needed to justify the above>
SUPERSESSION_NOTES
- <only where this turn touches changed/reopened state>
RETRIEVED_ANCHORS
- [<source|turn>] <...>
INSTRUCTION: If the raw conversation history conflicts with TOM_ASSIST_STATE, use TOM_ASSIST_STATE. Answer the current request directly from this state. Do not enumerate prior conversation unless asked. If the current explicit user request conflicts with this state, identify the conflict as a proposed supersession/reopening; do not silently rewrite prior state.
[/TOM_ASSIST_STATE]
[CURRENT_USER_REQUEST]
<original user draft, verbatim, never edited by the renderer>
```

### 6.3 Canonical digests (D10)

`canonical_json(x)`: UTF-8, object keys sorted lexicographically (byte order), no insignificant whitespace, numbers as shortest round-trip decimal, arrays in given order. Use RFC 8785 (JCS) via `serde_jcs` if available; otherwise implement minimally with tests.

`packet_digest = sha256(canonical_json({project_id, workstream_id, state_version, tom_checkpoint_digest, admitted_item_ids, renderer_version, policy_version, user_draft_hash}))` with `admitted_item_ids` pre-sorted lexicographically. State/event digests per DB-002 use the same canonicalization. One shared Rust implementation in `crates/protocol`; the Python gateway mirrors it for checkpoint digests with a cross-language equality test fixture.

## 7. Governance wiring (WP-08) — how §12.2 maps

Native (Rust, deterministic, no gateway needed): `WRONG_PROJECT_CONTEXT` (scope gates), `UNSUPPORTED_STATE_CHANGE` / `SUPERSESSION_WITHOUT_REASON` (commit-gate rules §10.5), `STALE_EVIDENCE_USED` (evidence integrity status), `UNRESOLVED_DEPENDENCY_IGNORED` (declared `depends_on` edges vs response's proposed action), `COMPLETED_WORK_REPROPOSED` and `SUPERSEDED_PATH_REVIVED` (lexical + anchor-match against ledger objects; conservative thresholds; every hit carries evidence refs).

Gateway-assisted: `CONTRADICTION` and `CONSTRAINT_DROPPED` via `/verify/drift` with invariants rendered from active hard constraints and held decisions (each constraint contributes `contradict_patterns` built from its canonical_text; keep patterns conservative — precision over recall, per G10's ≤5% blocking false-positive target). `OBJECTIVE_DRIFT` and `CONCEPT_DRIFT` fire only at `REVIEW` severity in this build (weak instruments; honest severity). Claim-support checks via `/verify/claims` where the response cites project evidence.

Severity policy: `blocking_commit` is reserved for interventions with direct ledger-object evidence. Everything heuristic is `warning` or `info`. All thresholds live in one versioned policy file (`policy_version` logged everywhere, §17.1).

## 8. Seeded demo project (used by WP-09/WP-10 e2e and the harness dry-run)

Author `tests/fixtures/demo_project.jsonl`: a small realistic ledger — 1 objective, 2 concepts, 3 decisions, 2 hard constraints, 2 rejected paths (with reasons + reconsideration conditions), 2 completed-work items, 2 unresolved dependencies, evidence links, 1 supersession — plus a 30-turn synthetic transcript. Content must be neutral engineering material; do **not** copy text from the owner's real conversations or the papers beyond short factual phrases.

## 9. Testing map (T-catalogue coverage in this shot)

In-shot (fixture-level): T-001..T-004, T-006..T-008, T-010..T-020, T-022 (renderer A/B plumbing only — no model), T-023, T-024, T-025, T-026, T-028 (packet-compactness assertion). Deferred to live validation: T-005, T-009, T-021 (live), T-027, and every G-gate verdict. Record this table with pass/fail links in `BUILD_LOG.md`.

## 10. Forbidden actions

1. Writing to `tom_master`, `tom_master17D`, or `tom_sicd_gemma` — including "helpful" fixes. Report needed upstream changes as ESCALATE entries.
2. Calling `rgm.read_memory()`, `ToMClient.process()`, or `engine.step()` from any preview/ranking path, or emulating preview via step-and-rollback without an explicit owner decision.
3. Reporting any G-gate as passed; describing product capability using the paper's results as if product-proven (claim boundaries in `references_and_evidence.md`).
4. Adding LLM API calls, telemetry egress, analytics, or auto-update mechanisms.
5. Storing provider credentials/cookies; requesting broad host permissions; any hidden or unattended prompt submission path (EXT-023).
6. Auto-committing any provider- or model-generated state mutation (P1/P12; candidates only).
7. Deleting or rewriting `BUILD_LOG.md` history; force-pushing.
8. Pulling in heavyweight frameworks not listed in D14/D15 without an ESCALATE entry first.

## 11. Reporting protocol

`BUILD_LOG.md` is append-only, one section per WP:

```
## WP-03 — ToM gateway            [DONE | PARTIAL | BLOCKED]
Commit: <sha>
Evidence: <test command> → <summary line, e.g. "14 passed">
Decisions: <what you chose where this doc left latitude, with file:line>
Deviations: <spec/instruction deltas, if any>
ESCALATE: <numbered questions for the orchestrator, if any>
```

Finish the shot with a `## FINAL` section: definition-of-done checklist (§1) with evidence links, the T-catalogue table (§9), open escalations, and a candid list of the weakest points a reviewer should probe first. The orchestrator (Claude) reviews this log, and follow-up instructions will arrive as `ORCHESTRATOR_REVIEW_<n>.md` files in the repo root.
