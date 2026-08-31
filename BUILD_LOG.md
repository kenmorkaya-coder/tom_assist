# Tom Assist One-Shot Build Log

This file is append-only. Verification statements describe build checks only and are never G-gate verdicts.

## WP-00 — Repository and workspace scaffold [DONE]

Commit: containing commit `chore(wp-00): scaffold Tom Assist workspace` (self-referential SHA recorded in FINAL mapping)

Evidence: `cargo build --workspace` → clean debug build; toolchains: `rustc 1.94.1`, `cargo 1.94.1`, `node v25.6.1`, `npm 11.9.0`, `Python 3.12.7`.

Decisions: Rust edition 2024 and workspace `rust-version = 1.94` follow the installed stable toolchain; crate names use the `tom-assist-*` prefix while directory names remain contract-exact. Extension private key material is ignored at `apps/extension/.keys/`; only the manifest public key will be committed in WP-05.

Deviations: none.

ESCALATE: 1. The required log format asks each WP section to contain the SHA of the same commit that contains that section, which is cryptographically self-referential and cannot be satisfied literally. Safe reversible default: identify each containing commit by its unique conventional message and append the resolved SHA mapping in `FINAL`.

## WP-01 — Protocol schemas and conformance [DONE]

Commit: containing commit `feat(wp-01): freeze protocol schemas and types` (resolved in FINAL)

Evidence: `cargo test -p tom-assist-protocol` → 4 passed; `npm run schema:validate` → 9 fixtures and 33 core methods validated; `npm run schema:generate` → committed 234-line TypeScript contract generated with `json-schema-to-typescript 15.0.4`.

Decisions: §14.2 grouped method names were expanded into 33 concrete wire methods so dispatch never interprets slash notation. IDs and timestamps remain strings in Rust to preserve byte-exact protocol round trips and avoid hidden normalization. The unspecified Tom parity fields are `engine_parity_profile` and `engine_parity_verified_at_commit`; they expose the claimed runtime lineage without turning parity into a product verdict. D10 canonicalization is implemented once in `tom-assist-protocol` with UTF-8 byte-key ordering and compact shortest-round-trip JSON numbers.

Deviations: none.

ESCALATE: none.

## WP-09 — Tauri desktop and seeded release console [DONE]

Commit: containing commit `feat(wp-09): add seeded Tauri desktop console` (resolved in FINAL)

Evidence: `npm run desktop:test` → 1 scripted UI smoke passed for project → capture → supersede → audit; `npm run typecheck -w @tom-assist/desktop-ui` → clean; `cargo test -p tom-assist-desktop` → 1 passed, asserting the neutral demo fixture has 1 objective, 2 concepts, 3 decisions, 2 constraints, 2 rejected paths, 2 completed items, 2 unresolved dependencies, 2 evidence items, exactly 1 supersession, and 30 turns; `cargo check -p tom-assist-desktop` and `cargo build -p tom-assist-desktop` → clean. The real native process stayed running and its app-data SQLite query returned `1|16|30` for projects/state objects/turns.

Decisions: Tauri owns the same `Store` behind a process mutex and exposes narrow commands for create/list/rename/archive, ledger capture/supersession, intervention disposition, diagnostics, and verified export/import. The seed runs idempotently in native setup as well as through the command boundary, so demo availability does not depend on webview scheduling. Project deletion is represented by recoverable archive status in this alpha. Settings retain D7's 500-token default and 1,200 ceiling; encrypted storage remains truthfully unavailable by default. The Preact smoke substitutes only the typed command adapter, while the Rust seed/replay test exercises real SQLite.

Deviations: macOS accessibility automation could not attach to the unbundled debug executable because it is not registered as an application bundle; no visual-QA claim is made. Native process survival, compiled web assets, scripted DOM smoke, and real seeded SQLite were verified. WP-12 supplies the `.app` packaging path for bundle-level walkthrough verification.

ESCALATE: none.

## WP-03 — ToM gateway and Rust adapter [DONE]

Commit: containing commit `feat(wp-03): add pure tom gateway and adapter` (resolved in FINAL)

Evidence: `PYTHONPATH=/Users/kenmorkaya/PycharmProjects/tom_master:$PWD .venv-gateway/bin/python -m pytest -q gateway/tests` → 6 passed, including 100 mixed preview calls with byte-identical engine/RGM serializations, unchanged engine/RGM ticks, deterministic output across runtime restart, commit idempotency, checkpoint restore, and all three verifier mappings. `cargo test -p tom-assist-tom-adapter --test live_gateway` → 1 passed against the real pinned runtime over a mode-0600 Unix socket. `cargo test -p tom-assist-protocol` → 5 passed including the shared Python/Rust canonical-digest fixture. The runtime SHA observed at startup was `8799ccbdddf3d5b5939360b91993581af7dab470`.

Decisions: selected the contract-authorized direct `TreeGrowthEngine` + `ReflectionGatedMemory` composition. Explicit turn commit performs exactly one mechanical pass at pinned `agency/mechanics/sicd_engine.py:2709-2734`, then one RGM write; checkpoints use pinned engine save/load (`:1392`, `:1580`) and RGM serialize/restore (`memory/rgm.py:1608`, `:1622`). Preview uses only pinned `VectorStore.query` (`memory/rgm.py:681-733`) and an exact local mirror of the applicable conversation-continuity trigger. The local mirror avoids importing `interface.__init__`, whose unrelated provider initialization expands the dependency and side-effect boundary. Equal retrieval scores are tie-broken by record ID because restored and live vector stores retain different insertion orders. The isolated `.venv-gateway` contains runtime dependencies `numpy==2.3.5` and `PyYAML==6.0.3`; its test-only dependency is `pytest==9.0.2` (plus pytest's transitive packages).

Deviations: The live Unix-socket integration check must run outside the managed filesystem sandbox because macOS `socket.bind` is denied there with `EPERM`; this is a test-runner constraint, not a transport fallback. No runtime pin or capability claim was relaxed.

ESCALATE: 2. The binding inspection document identifies `retrieve_ltm_with_stm_triggers` as sanctioned for pure retrieval, but the pinned implementation at `interface/stm_ltm_retrieval.py:187-193` invokes forbidden mutating `rgm.read_memory`. Options: (a) split a pure upstream wrapper in a future pinned runtime, or (b) keep Tom Assist on direct `VectorStore.query`. Recommendation and safe reversible default: (b), implemented and purity-tested here.

ESCALATE: 3. A commit-path probe through pinned `ToMClient.process` with the documented stub provider still entered an internal dependency-extraction HTTP path, so it could not establish the no-network build boundary. Options: (a) add an upstream fully-offline process mode and repin after review, or (b) retain the direct engine+RGM composition explicitly allowed by this instruction. Recommendation and safe reversible default: (b), implemented here; no preview path ever called `ToMClient.process`, `engine.step`, or `rgm.read_memory`.

## WP-02 — Event-sourced persistence [DONE]

Commit: containing commit `feat(wp-02): add deterministic event store` (resolved in FINAL)

Evidence: `cargo test -p tom-assist-persistence --all-features` → 5 passed, including event replay equality, candidate-authority rejection, CAS conflict, supersession audit lineage, snapshot/export/import verification, and canonical digest equality across 25 cold reopens.

Decisions: SQLite is bundled through `rusqlite 0.37.0` for reproducible local builds. Materialized object/edge rows retain their full canonical JSON alongside query columns so replay equality is tested without lossy relational reconstruction. Project creation is an immutable version-0 event; authoritative state mutations alone increment `state_version`. Portable alpha exports are documented files (`events.jsonl`, `state.json`, transcript policy, canonical manifest/checksums) rather than a custom binary archive.

Deviations: SQLCipher is represented by the compile-tested `encrypted-store` feature and an explicit unavailable key-loading result, default off per D13; no encryption capability is claimed.

ESCALATE: none.

Log-order note: WP-03 was executed after the WP-02 commit, but its append operation matched the earlier identical `ESCALATE: none.` anchor and placed the section above WP-02. In keeping with the append-only rule, that history is not moved or rewritten; commit ancestry remains the authoritative execution order.

## WP-04 — assistd transaction service [DONE]

Commit: containing commit `feat(wp-04): add snapshot-bound assistd transactions` (resolved in FINAL)

Evidence: `cargo test -p tom-assistd -- --skip unix_socket_is_user_only_and_protocol_versioned` → 4 passed; `cargo test -p tom-assistd unix_socket_is_user_only_and_protocol_versioned` → 1 passed outside the socket-binding sandbox. Checks cover snapshot-bound PREPARE_TURN, D10 packet binding, immutable/idempotent USER_TURN_SENT capture, incomplete EVALUATE_TURN capture, stale packet rejection after V→V+1, two-tab concurrent commit serialization with one deterministic SQLite CAS conflict, versioned JSON framing, and mode-0600 UDS permissions. `cargo test -p tom-assist-persistence` remained 5 passed after adding context-run, turn, response-evaluation, and audit persistence APIs.

Decisions: assistd uses a process-local per-project mutex for logical single-writer ordering while SQLite `BEGIN IMMEDIATE` plus `state_version` CAS remains the durable/cross-process authority. PREPARE_TURN is persisted as a non-authoritative `context_runs` record and never advances state. `turn.sent` requires a locally stored packet digest, identical draft hash, and unchanged state version before persisting the user turn. EVALUATE_TURN persists exact packet lineage and represents incomplete capture explicitly; WP-08 supplies the intervention engine while WP-04's clean lineage baseline is `PASS`, stale lineage is `REVIEW`, and incomplete capture is `INCOMPLETE`. Newline-delimited protocol envelopes travel over the user-only UDS.

Deviations: the UDS permission/framing test requires execution outside the managed filesystem sandbox because sandboxed `socket.bind` returns `EPERM`. No product transport behavior differs.

ESCALATE: none.

## WP-05 — native host and MV3 extension boundary [DONE]

Commit: containing commit `feat(wp-05): secure native messaging boundary` (resolved in FINAL)

Evidence: `cargo test -p tom-assist-native-host` → 4 passed for 4-byte native framing, JSON/envelope validation, exact-origin rejection, >900 KB chunk/reassembly equality, and derivation of the allowlisted extension ID from the committed public key. `npm run extension:test` → 4 passed for schema/version handshake, forged-sender rejection, out-of-order chunk reassembly, and held transaction restore. `npm run typecheck -w @tom-assist/extension` → clean. `npm run extension:build` → production MV3 output (background 133.97 kB, side panel 11.76 kB) with manifest copied into `dist/`. `npm audit --omit=dev --json` → zero production dependency advisories after updating Ajv and Preact.

Decisions: Chrome Native Messaging uses its normative little-endian 32-bit frame and a 16 MB defensive input ceiling. D9 splitting begins only when the serialized response exceeds 900 KiB; 600 KiB raw pieces keep base64-wrapped chunk frames below the same ceiling. The generated RSA public key pins extension ID `mollhhfpcdpgbnlinhhghkndeniglfba`; the ignored private key is retained at `apps/extension/.keys/extension-private.pem`, and coordinated regeneration steps are documented. Both Rust and the native-host manifest allowlist exactly `chrome-extension://mollhhfpcdpgbnlinhhghkndeniglfba/`. The MV3 worker accepts only its own runtime sender ID and stores pending PREPARE_TURN/PENDING_SEND envelopes in `chrome.storage.session` before forwarding.

Deviations: the full development-dependency audit retains one low-severity esbuild advisory limited to a Windows development-server file-read scenario; Tom Assist's target is macOS, the production dependency audit is empty, and production builds do not start a dev server. No vulnerable runtime dependency is shipped.

ESCALATE: none.

## WP-06 — ChatGPT provider adapter fixtures [DONE]

Commit: containing commit `feat(wp-06): add visible DOM provider adapter` (resolved in FINAL)

Evidence: `npm run adapters:test` → 4 passed over four authored static fixtures, covering standard and fallback composer selectors, stable role/order/hash capture, streaming-incomplete state, exact EXT-013 deduplication key, visible composer read/write, and unknown-DOM clean detach. `npm run typecheck -w @tom-assist/provider-adapters` and `npm run build -w @tom-assist/provider-adapters` → clean.

Decisions: the §8.1 `ProviderAdapter` method shape is preserved verbatim behind typed support records. Layered selectors prioritize semantic `data-testid`/`data-message-author-role` attributes, then constrained ID/ARIA/content-class fallbacks. Capture hashes normalized visible text with SHA-256 and deduplicates on conversation identity + ordinal + hash. Streaming is incomplete whenever a visible stop/streaming control remains. Submit interception ignores synthetic events, pauses the original trusted submit, and replays only after the interceptor returns explicit `continue`; missing submission surfaces detach instead of guessing. Fixture HTML is neutral and authored locally rather than scraped from a live provider.

Deviations: live chatgpt.com selector verification remains deliberately out of scope; these checks are fixture-level only and the adapter fails closed into a clean detached state when selectors do not match.

ESCALATE: none.

## WP-07 — context admission and authoritative renderer [DONE]

Commit: containing commit `feat(wp-07): add deterministic context admission` (resolved in FINAL)

Evidence: `cargo test -p tom-assist-context-admission` → 4 passed. The golden fixture asserts byte-identical renderer output, manifest equality, two cross-input rebuilds, and fixed packet digest `sha256:a7292077bb2dfb40f92d7d051a0fa7ba900f57050d1b4edc1e0cddb5b6f83910`. Additional checks cover cross-project/superseded exclusion, hard-constraint survival under a tiny budget, optional-background eviction, explicit depth-2 missing-dependency markers, the 500-token default, and the 1,200-token maximum.

Decisions: the versioned starting policy keeps all nine §11.3 components decomposed in the trace; weights are transparent initial product settings rather than importing the archived paper's scalar as an unexplained constant. Hard gates run before scoring for project/workstream scope, privacy, evidence integrity, supersession, and archive state. Canonical text duplicates collapse deterministically. Active objectives, hard constraints, and guardrails are non-evictable; optional context ranks by section priority, total decomposed score, then byte-order ID. Dependency closure traverses only graph roots, caps at depth 2, detects cycles, and renders explicit `[MISSING_DEPENDENCY]` markers when closure is impossible. Token estimates use D7's documented `ceil(chars/4)` heuristic. The only production renderer is `authoritative-state/1.0`, and the original draft is appended verbatim outside its state block.

Deviations: none.

ESCALATE: none.

## WP-08 — governance and authority gates [DONE]

Commit: containing commit `feat(wp-08): add evidence-linked governance` (resolved in FINAL)

Evidence: `cargo test -p tom-assist-governance -- --skip live_gateway_drift_verifier_drives_contradiction_mapping` → 4 passed: every one of the 11 intervention codes fires once on its crafted direct-evidence fixture, the same rule set remains silent on a clean response, claim/structure inputs route through the gateway contract, deterministic/manual extraction remains candidate-only, commit authority/version/blocking gates reject unsafe transitions, correction packets are generated, and false-positive resolution persists without advancing state. `cargo test -p tom-assist-governance live_gateway_drift_verifier_drives_contradiction_mapping -- --ignored` → 1 passed against pinned tom_master's real DriftVerifier over UDS. `cargo test -p tom-assist-persistence` remained 5 passed after adding intervention persistence.

Decisions: all confidence values and severities live in `governance-policy/1.0`. Direct ledger evidence may block state commit; objective/concept drift remain warning-only at 0.65 confidence. CONTRADICTION and CONSTRAINT_DROPPED require a block/revise result from `/verify/drift` over conservatively escaped project phrases. Cited-claim support routes through `/verify/claims`; reasoning authority/constraint shape routes through `/adjudicate/structure`. Remaining scope, supersession, dependency, completed/rejected path, evidence-integrity, and authority rules are Rust-native deterministic checks. Deterministic visible-turn extraction maps to `provider_candidate` because the protocol has no separate deterministic-candidate authority; manual user capture maps to `user`, but both produce `status=proposed` and `requires_user_confirmation=true`. Candidate IDs and intervention IDs are deterministic UUID-shaped hashes. Provider/model candidates never auto-commit.

Deviations: the real gateway integration case is marked ignored in the default workspace suite because it requires the pinned external runtime and an unsandboxed local socket; it is run explicitly as WP evidence. No evaluator result is promoted to a validation-gate verdict.

ESCALATE: none.

Log-order note: WP-09 was executed after WP-08, but its append operation matched an earlier repeated `ESCALATE: none.` anchor and placed the section near the start of the file. In keeping with the append-only rule, that history is not moved or rewritten; commit ancestry remains the authoritative execution order.

## WP-10 — extension prompt gate and page UX [DONE]

Commit: containing commit `feat(wp-10): add explicit extension prompt gate` (resolved in FINAL)

Evidence: `npm run extension:test` → 6 passed across boundary and fixture-e2e suites. The authored ChatGPT fixture exercises pause → preview (categories, warning, stale exclusion) → explicit approval → visible composer insertion → sent-lineage capture → complete-response evaluation badge. A separate offline case proves the held submission does not settle until the user explicitly chooses “Send once without Tom.” `npm run typecheck -w @tom-assist/extension` → clean. `npm run extension:build` → MV3 output with background, content script, and side panel (content 12.87 kB; no remote assets).

Decisions: `PromptGateController` is the sole user-event-bound state machine. It holds the adapter's trusted submit promise through PREPARE_TURN and resolves it only for Send with Tom, explicit fail-open, or cancel. The packet plus original draft are written through `ProviderAdapter.writeDraft`, keeping inserted context visible. Native messaging remains the only service transport. The content surface contains the attachment chip, preview/edit drawer, warnings/exclusions, quick-capture toolbar, and post-response badge; the side panel owns explicit attach/detach and the requested ledger summary categories.

Deviations: live chatgpt.com selector verification remains explicitly out of scope; unpacked loading and all DOM behavior are fixture/build-level. The native boundary's state-proposal payload remains candidate-only and requires user confirmation.

ESCALATE: none.

## WP-11 — validation harness scaffold [DONE]

Commit: containing commit `feat(wp-11): scaffold reproducible validation harness` (resolved in FINAL)

Evidence: `python3 -m unittest discover -s validation/tests -v` → 2 passed. `python3 -m validation.harness --input validation/fixtures/toy_cases.jsonl --output-dir .tmp/wp11-harness` → a complete Markdown report, run manifest, event trace, and packet trace for 3 toy cases × SUB-A…SUB-E = 15 observations. The report headline and manifest label are `NOT-A-GATE`, `gate_verdicts` is zero, and no acceptance threshold is evaluated.

Decisions: arms are explicit typed plumbing for SUB-A recent-visible context, SUB-B conventional summary, SUB-C prose structural prelude, SUB-D authoritative state block, and SUB-E wrong/stale structural state. Each arm receives identical stored history/probe input. The oracle is a fresh deterministic stdin/stdout subprocess per observation and records its version plus term-level evidence. The G15-shaped manifest freezes code SHA, provider/adapter versions, state policy, renderer, exact arms, input digest, event/packet trace names, timestamps, and result summary. Output uses Appendix C's scenario/expected/observed/evidence shape without interpreting an observation as success against a gate.

Deviations: `validation/fixtures/toy_cases.jsonl` is intentionally a three-case plumbing smoke fixture, not a frozen battery. Zero validation batteries are authored in this shot.

ESCALATE: none.

## WP-12 — developer launch, install, packaging, and runbook [DONE]

Commit: containing commit `chore(wp-12): add local install and release runbook` (resolved in FINAL)

Evidence: `scripts/dev-run.sh --check` → pinned tom_master `8799ccbdddf3d5b5939360b91993581af7dab470` and local prerequisites ready. `scripts/install-native-host/install.sh --target-root "$PWD/.tmp/wp12-home" --binary "$PWD/target/debug/tom-assist-native-host"` → executable launcher plus valid Chrome manifest under the correct redirected macOS directory, with exact extension ID `mollhhfpcdpgbnlinhhghkndeniglfba`. `scripts/package-macos/package-unsigned-app.sh --output-dir "$PWD/.tmp/wp12-final"` → optimized unsigned `.app`, bundle ID `local.tom.assist`. A real clean launch exposed `tauri://localhost`, `Release console`, seeded `Local Release Console`, STATE V16, 16 objects, 17 audit events, and all six navigation views to macOS accessibility inspection. `cargo test -p tom-assistd --test full_fixture` → 1 passed for draft → prepared visible packet → sent turn → evaluated response → evidence-linked intervention → rejected unconfirmed commit → accepted intervention → confirmed authoritative commit → replay/digest/intervention equality after SQLite restart. `sh -n` checks and the full runbook command suite are included in final verification.

Decisions: the dev runner owns and cleans up only its gateway, assistd, Vite, and desktop child processes; persistent user data is never removed. The native-host installer uses Chrome's per-user `NativeMessagingHosts` directory and a launcher that fixes the user-local assistd socket. `--target-root` makes installation testable without changing the user's Chrome profile. The unsigned packager builds only an optimized Tauri `custom-protocol` binary so assets are embedded; debug binaries are rejected because they require the Vite server. Existing package output is preserved once as a `.previous.app` rather than silently overwritten. The runbook calls out every out-of-scope claim and labels harness output NOT-A-GATE.

Deviations: signing/notarization and an actual write into the user's live Chrome profile remain out of scope; the installer was exercised against a redirected home. Live chatgpt.com selectors were not tested. The fresh-checkout sequence was command-verified in the working checkout rather than by making a second network clone.

ESCALATE: none.

WP-12 verification supplement: Chrome 151 no longer honors command-line `--load-extension`, so the build followed Chrome's documented replacement and used temporary Puppeteer + Chrome for Testing from ignored `.tmp`. The unpacked build registered the exact MV3 service worker `chrome-extension://mollhhfpcdpgbnlinhhghkndeniglfba/background.js`; Puppeteer/Chrome for Testing are verification-only and were not added to product dependencies. The final T-catalog audit also added `Store::open_with_recovery`: a failed migration is copied byte-for-byte to a non-overwriting backup and reopened read-only, surfaced by desktop diagnostics. `cargo test -p tom-assist-persistence` → 6 passed including that T-016 recovery case.

WP-12 boundary supplement: final wire audit corrected the content script's actor instance to a UUID and made its `ProviderCapabilities` payload match the frozen Rust/schema contract exactly; quick capture uses the normative `state.candidate.create` method name. Extension tests/typecheck/build remained green, and the rebuilt service worker reloaded under the pinned Chromium ID.

WP-12 candidate-path supplement: the normative quick-capture method is now dispatched by assistd and persisted in `state_mutation_candidates`. `cargo test -p tom-assistd --test transactions` → 6 passed, including an envelope-level regression proving the user candidate remains `status=proposed`, requires confirmation, is recoverable after SQLite reopen, and does not advance authoritative `state_version` or `state_digest`. Evidence capture is supported as the sixth manual candidate kind. No quick-capture path calls an authoritative commit.

## FINAL

### Definition of done

- [x] Rust workspace: `cargo build --workspace` completed cleanly; final `cargo test --workspace` completed with every selected test passing (32 build-verification tests, 0 failures, 1 explicitly ignored live-governance case). The ignored case was then run explicitly against the real gateway and passed 1/1. Evidence: [workspace manifests](Cargo.toml), [assistd transaction tests](crates/assistd/tests/transactions.rs), [live adapter test](crates/tom-adapter/tests/live_gateway.rs), and [live governance test](crates/governance/tests/interventions.rs).
- [x] Real pinned ToM gateway: `.venv-gateway/bin/python -m pytest -q gateway/tests` → 6 passed, including the 100-call byte/tick preview-purity check and restart determinism. The Rust live-gateway integration is also green. Evidence: [gateway endpoint tests](gateway/tests/test_gateway_endpoints.py), [preview-purity test](gateway/tests/test_preview_purity.py), and [Rust gateway integration](crates/tom-adapter/tests/live_gateway.rs).
- [x] Extension: schemas validated 9 fixtures and all 33 method names; provider fixtures passed 4/4; extension fixtures passed 6/6; typecheck and optimized build completed; the unpacked final build registered the pinned-ID MV3 service worker in Chrome for Testing. Evidence: [schema validator](scripts/validate_protocol_schemas.py), [provider tests](packages/provider-adapters/tests/chatgpt.test.ts), [prompt-gate e2e](apps/extension/tests/prompt-gate.e2e.test.ts), and [native-boundary tests](apps/extension/tests/boundary.test.ts).
- [x] Desktop: UI smoke passed 1/1 and the optimized frontend built; the unsigned `custom-protocol` `.app` launched from a clean process and exposed the seeded project, state/audit counts, and all six requested areas. Project CRUD, state capture/supersession, ledger/audit, intervention review, settings/diagnostics, and export/import are backed by Tauri commands. Evidence: [desktop UI smoke](apps/desktop/ui/tests/smoke.test.tsx), [Tauri command surface](apps/desktop/src-tauri/src/main.rs), and [runbook](docs/DEV_RUNBOOK.md).
- [x] Fixture lifecycle: `cargo test -p tom-assistd --test full_fixture` → 1 passed for draft → PREPARE_TURN → visible packet → simulated send → response record → governance intervention → rejected unconfirmed commit → accepted intervention → user-confirmed commit → event replay/digest/intervention equality after restart. This is a cross-crate fixture composition; the production orchestration seam is called out below. Evidence: [full fixture](crates/assistd/tests/full_fixture.rs).
- [x] Validation scaffold: unit tests passed 2/2; the dry-run emitted report, manifest, event trace, and packet trace for 3 toy cases × 5 subscription arms = 15 observations. It authored zero validation batteries and emitted zero gate verdicts. Evidence: [harness tests](validation/tests/test_harness.py), [arms](validation/arms.py), and [harness](validation/harness.py).
- [x] Reporting: WP-00 through WP-12 each have a commit and evidence entry. The two append-anchor ordering mistakes remain documented in place; commit ancestry below records the actual execution order.
- [x] Forbidden-action audit: no build command wrote to either permitted read-only upstream repository, and the entirely off-limits repository was not inspected or imported. Preview purity is enforced by tests; no preview path calls a mutating runtime entry point. No LLM/API, telemetry, analytics, auto-update, hidden submit, credential storage, or provider/model auto-commit path was added.

### Commit map

| Scope | Commit | Subject |
|---|---:|---|
| Contract baseline on `main` | `e0c971c` | `docs: freeze Tom Assist build contract` |
| WP-00 | `d2ee7a0` | `chore(wp-00): scaffold Tom Assist workspace` |
| WP-01 | `c3b1b42` | `feat(wp-01): freeze protocol schemas and types` |
| WP-02 | `517dba2` | `feat(wp-02): add deterministic event store` |
| WP-03 | `2715cdf` | `feat(wp-03): add pure tom gateway and adapter` |
| WP-04 | `258bf0b` | `feat(wp-04): add snapshot-bound assistd transactions` |
| WP-05 | `fb9b36a` | `feat(wp-05): secure native messaging boundary` |
| WP-06 | `3e461a9` | `feat(wp-06): add visible DOM provider adapter` |
| WP-07 | `d011b74` | `feat(wp-07): add deterministic context admission` |
| WP-08 | `96ba4e2` | `feat(wp-08): add evidence-linked governance` |
| WP-09 | `8b63af5` | `feat(wp-09): add seeded Tauri desktop console` |
| WP-10 | `f18057f` | `feat(wp-10): add explicit extension prompt gate` |
| WP-11 | `17a47a5` | `feat(wp-11): scaffold reproducible validation harness` |
| WP-12 | `b04a1fb` | `chore(wp-12): add local install and release runbook` |

### T-catalogue coverage

These results are build verification only. `PASS` below does not mean or imply a specification G-gate verdict.

| Test | Shot status | Evidence |
|---|---|---|
| T-001 | PASS (fixture build verification) | [prompt-gate e2e](apps/extension/tests/prompt-gate.e2e.test.ts) |
| T-002 | PASS (fixture build verification) | [ChatGPT DOM adapter fixtures](packages/provider-adapters/tests/chatgpt.test.ts) |
| T-003 | PASS (fixture build verification) | [prompt interception and explicit approval tests](apps/extension/tests/prompt-gate.e2e.test.ts) |
| T-004 | PASS (fixture build verification) | [byte-stable packet fixture](crates/context-admission/tests/golden_packet.rs) |
| T-005 | DEFERRED (live validation) | Requires the frozen live semantic/paraphrase battery, outside this shot. |
| T-006 | PASS (fixture build verification) | [crafted intervention fixtures](crates/governance/tests/interventions.rs) |
| T-007 | PASS (fixture build verification) | [authority and intervention fixtures](crates/governance/tests/interventions.rs) |
| T-008 | PASS (fixture build verification) | [hard-gate and dependency fixtures](crates/context-admission/tests/golden_packet.rs) |
| T-009 | DEFERRED (live validation) | Requires the frozen live causal battery, outside this shot. |
| T-010 | PASS (fixture build verification) | [event replay/idempotency tests](crates/persistence/tests/event_store.rs) |
| T-011 | PASS (fixture build verification) | [real pinned gateway integration](crates/tom-adapter/tests/live_gateway.rs) |
| T-012 | PASS (fixture build verification) | [100-call preview-purity and restart tests](gateway/tests/test_preview_purity.py) |
| T-013 | PASS (fixture build verification) | [candidate extraction and explicit commit gate](crates/governance/tests/interventions.rs) |
| T-014 | PASS (fixture build verification) | [stale packet invalidation](crates/assistd/tests/transactions.rs) |
| T-015 | PASS (fixture build verification) | [25-reopen digest equality](crates/persistence/tests/event_store.rs) |
| T-016 | PASS (fixture build verification) | [migration backup and read-only safe mode](crates/persistence/tests/event_store.rs) |
| T-017 | PASS (fixture build verification) | [framing, allowlist, chunk, and forged-origin tests](crates/native-host/tests/framing.rs) |
| T-018 | PASS (fixture build verification) | [typed admission and closure tests](crates/context-admission/tests/golden_packet.rs) |
| T-019 | PASS (fixture build verification) | [auditable supersession test](crates/persistence/tests/event_store.rs) |
| T-020 | PASS (fixture build verification) | [false-positive resolution test](crates/governance/tests/interventions.rs) |
| T-021 | DEFERRED (live validation) | Requires a live new-provider-chat run; live selectors are outside this shot. |
| T-022 | PASS (renderer A/B plumbing only) | [SUB-A…SUB-E arm plumbing](validation/arms.py) and [harness tests](validation/tests/test_harness.py); no model or gate verdict. |
| T-023 | PASS (fixture build verification) | [candidate-only quick capture](crates/assistd/tests/transactions.rs) and [commit gate](crates/governance/tests/interventions.rs) |
| T-024 | PASS (fixture build verification) | [candidate authority isolation](crates/persistence/tests/event_store.rs) and [forged extension rejection](crates/native-host/tests/framing.rs) |
| T-025 | PASS (fixture build verification) | [concurrent-tab serialization/CAS](crates/assistd/tests/transactions.rs) |
| T-026 | PASS (fixture build verification) | [capability conformance](crates/protocol/tests/conformance.rs) and [Layer-1 renderer fixture](crates/context-admission/tests/golden_packet.rs) |
| T-027 | DEFERRED (live validation) | Requires the frozen adversarial/live validation programme, outside this shot. |
| T-028 | PASS (fixture build verification) | [budget defaults, cap, eviction, and compactness](crates/context-admission/tests/golden_packet.rs) |

### Open escalations

1. ESCALATE 2 remains open for the owner: the sanctioned upstream retrieval wrapper calls a forbidden mutating memory entry point in the pinned runtime. The shipped reversible default uses direct `VectorStore.query`; an upstream pure wrapper plus a reviewed repin remains the cleaner long-term option.
2. ESCALATE 3 remains open for the owner: `ToMClient.process` enters an internal dependency-extraction HTTP path even with the inspected stub provider. The shipped reversible default uses the instruction-authorized direct engine+RGM composition; a fully offline upstream process mode could replace it after review.
3. ESCALATE 1 is closed as an accounting issue: a commit cannot contain its own SHA, so WP sections identify unique commit subjects and the resolved SHA map is recorded above.

### Weakest points to probe first

1. `AssistService::evaluate_turn` owns packet lineage, immutable response recording, and PASS/REVIEW/INCOMPLETE state, while `GovernanceEngine` owns the 11 evidence-linked rules. The full fixture composes both real crates explicitly, but production `response.evaluate` does not yet inject a live `GovernanceEngine` into the assistd dispatch. Review this orchestration seam first before treating the badge as production governance coverage.
2. The ChatGPT adapter is intentionally fixture-verified only. Selector health, completion timing, and clean detach should be rerun against the then-current live site before release.
3. The unpacked MV3 proof used Chrome for Testing with Puppeteer's extension-enablement API because current stable Chrome removed the old command-line loading flag. It proves manifest/key/service-worker loading, not a signed-store install or a live ChatGPT journey.
4. The native-host installer was exercised against a redirected target root, not the user's active Chrome profile. Signing/notarization, first-run permissions, browser restart behavior, and user-facing uninstall remain release work.
5. The desktop UI smoke uses its deterministic backend, while the packaged app launch separately proves the real Tauri command surface and seeded store. A single automated GUI test that drives every CRUD/review/import action through the packaged binary would strengthen this boundary.
6. The gateway deliberately bypasses the impure sanctioned wrapper and the network-entering `ToMClient.process` route. The direct engine+RGM path is pinned and integration-tested, but runtime upgrades need a renewed inspection rather than a blind SHA bump.
7. The validation harness contains only three toy plumbing cases and zero frozen batteries. Its outputs are instrumentation artifacts labeled `NOT-A-GATE`, not product efficacy evidence.

No G-gate verdicts were made or reported as passed.

## WP-13 — production response governance wiring [DONE]

Commit: containing commit `feat(wp-13): wire governance into production evaluation`

Evidence: `cargo test -p tom-assistd` → 9 passed: the envelope-dispatched production path returns `CONFLICT` with a persisted blocking intervention ID for the seeded conflicting response, returns `PASS` with no intervention IDs for the clean response, records both results under `governance-policy/1.0`, and degrades a gateway-down evaluation to `REVIEW` while preserving the captured turn and persisting a correlated `gateway_unavailable` diagnostic. The rewritten full fixture passes using the `GovernanceEngine` injected into `AssistService`; it no longer constructs a second engine outside production evaluation. `cargo test --workspace` → 34 passed, 0 failed, 1 explicitly ignored live-governance case. `cargo test -p tom-assist-governance live_gateway_drift_verifier_drives_contradiction_mapping -- --ignored` → 1 passed against the real pinned gateway. `npm run extension:test` → 6 passed; extension typecheck and optimized build completed cleanly. `cargo fmt --all -- --check` → clean.

Decisions: production `tom-assistd` now constructs `AssistService` with a real `GatewayClient` and the default `governance-policy/1.0`; its optional third CLI argument is the gateway socket, defaulting to `tom_gateway.sock` beside the assistd socket used by the existing dev runner. Complete, non-stale evaluation reconstructs governance rules from the exact packet sections persisted in `context_runs.selected_json`, runs deterministic visible-turn candidate extraction as candidate-only, invokes the injected engine, persists every returned intervention, and stores/returns the same intervention IDs. `INCOMPLETE` and stale-`REVIEW` take precedence and skip governance. Gateway health or verifier-call failure reruns the request through the same policy with verifier-backed checks disabled and Rust-native rules active, records `gateway_unavailable` in both the wire diagnostic list and `audit_events`, and forces `REVIEW`; capture is not failed and degraded evaluation can never silently return `PASS`. No intervention rule, severity, policy, or endpoint changed.

Decisions resolving prior entries: per `ORCHESTRATOR_REVIEW_1.md`, ESCALATE 2 and ESCALATE 3 option (b) defaults are owner-ratified as permanent for the current runtime pin. Direct `VectorStore.query` preview and direct engine+RGM commit composition remain; adopting a future upstream alternative requires renewed inspection and a reviewed repin. ESCALATE 1 remains closed under the accepted commit-subject mapping convention.

Deviations: none. This entry supersedes FINAL's first “weakest point”: production `response.evaluate` now owns and invokes governance rather than relying on fixture-only composition. Deferred live-selector, packaged-GUI, signing/install, encryption, and validation-battery work remains unchanged.

ESCALATE: none.

No G-gate verdict was made or reported as passed.

## WP-14 — bare 8D-native 10k project seeding [DONE]

Commit: containing commit `feat(wp-14): seed projects from bare 8d-native 10k tree`

Evidence: `shasum -a 256` verified the read-only seed artifact as `d9aec9b424459d0948f569c7e424bb5632bd118ad01bda372f62df7ca17a82ac` and the mechanics profile as `d5ad378c7358f1eb3f2a4088f742e20594c7441d9e21714e85d6324a78a110d6`; both paths are tracked and clean at pinned upstream commit `8799ccbdddf3d5b5939360b91993581af7dab470`. `.venv-gateway/bin/python -m pytest -q -s gateway/tests` → 9 passed, including two-project byte/digest determinism, corrupt-seed fail-closed behavior, the existing mixed 100-preview byte-purity proof on a 10,000-branch project, seeded commit/digest-chain sanity, restart determinism, and 20-call preview latency of p50 `0.004 ms`, p95 `0.006 ms`, max `0.007 ms` (local build verification only). `cargo test --workspace` → 34 passed, 0 failed, 1 explicitly ignored live-governance case. `cargo test -p tom-assist-tom-adapter --test live_gateway` → 1 passed against the real pinned runtime. `cargo test -p tom-assist-governance live_gateway_drift_verifier_drives_contradiction_mapping -- --ignored` → 1 passed. `npm run schema:validate` → 9 fixtures and 33 core methods; `npm run extension:test` → 6 passed, and extension typecheck/build completed cleanly. `cargo fmt --all -- --check` and `git diff --check` → clean.

Decisions: fresh projects verify the canonical seed hash before calling `TreeGrowthEngine.load`, then assert tick `4707` and branch count `10000`; any missing, changed, or structurally wrong artifact fails creation without an empty-tree fallback. Each fresh project gets a new empty `ReflectionGatedMemory`, byte-stable persisted tree/RGM artifacts, `creation_metadata.json`, and a cached initial checkpoint digest. Creation metadata, checkpoint metadata, commit summaries, `/capabilities`, the shared schema, generated TypeScript, and the Rust adapter now carry seed/profile lineage; each commit links the seed checkpoint, prior checkpoint, and resulting checkpoint digests. Existing pre-WP-14 projects remain readable and are explicitly labeled `legacy_pre_wp14` when they lack creation metadata.

Applied mechanics parameter set: gateway startup parses and applies every assignment in read-only `tom_master/config/profiles/msr_8d_native_10k.env:11-75`: `TOM_TAU1=4.0`, `TOM_HEAL_RATE=0.03263671875`, `TOM_DAMAGE_RATE=0.1034375`, `TOM_KAPPA_DECAY=0.053193359375`, `TOM_KAPPA_DELTA_CAP=0.026884765625`, `TOM_KAPPA_NOURISH_RECOVERY=0.002`, `TOM_SPAWN_SOFT_CAP=10200`, `TOM_SPAWN_HARD_CAP=12000`, `TOM_SPAWN_BUDGET_BASE=5.5`, `TOM_SPAWN_COST_BASE=0.25`, `TOM_SPAWN_R_MIN_SCALE=0.25`, `TOM_MIN_METABOLIC_FRACTION=0.10`, `TOM_NOURISH_EMA_FLOOR=0.15`, `TOM_ROOT_RESERVE_ENABLED=true`, `TOM_LEAF_CAPTURE_GAIN=0.50`, `TOM_LEAF_CAPTURE_CAP=2.5`, `TOM_LEAF_FACTOR_FLOOR=1.6`, `TOM_ROOT_SUPPLY_BASE=3.7`, `TOM_ROOT_CAP_PER_BRANCH=0.001`, `TOM_ROOT_DEPOSIT_FRACTION=0.15`, `TOM_ROOT_OVERFLOW_FRACTION=0.50`, `TOM_ROOT_RELEASE_RATE=0.08`, `TOM_ROOT_MAINT_REDUCTION=0.40`, `TOM_ROOT_CAPACITY_BOOST=0.5`, `TOM_ROOT_DECAY=0.001`, `TOM_BRANCH_CAPACITY=10000`, `TOM_SIZE_L_TARGET=3000`, `TOM_MAINT_COST_PER_BRANCH=0.000179`, `TOM_MAINT_COST_PER_LENGTH=0.00005`, `TOM_STIFFNESS_KAPPA_FLOOR=0.3`, `TOM_LEAF_VEC_KAPPA_FLOOR=0.3`, `TOM_ALPHA_SIGMA_FLOOR=0.15`, and `TOM_SICD_WARMUP_SNAPSHOT=sandbox/scaling/snapshots/msr_8d_native_10k_tiered.json`. Upstream environment application is evidenced by `agency/mechanics/sicd_engine.py:169-185,204-275,368-376` and `agency/mechanics/sicd_kappa_update.py:194-195,372-380`; the verified config is passed to the load path at `agency/mechanics/sicd_engine.py:1580-1595`. The six required kappa controls are additionally assigned from the parsed values onto every per-project config and asserted in the deterministic creation test, preventing an upstream default from silently replacing the declared envelope.

Deviations: the pinned profile exports `TOM_KAPPA_DECAY`, but the pinned `KappaUpdateConfig.kappa_decay` is a literal `0.03` at `agency/mechanics/sicd_kappa_update.py:205` and has no environment reader. The gateway therefore binds the profile's declared `0.053193359375` explicitly; no upstream file was changed.

ESCALATE: 4. Question: on a future reviewed runtime repin, should the owner add the missing upstream `TOM_KAPPA_DECAY` environment binding, or retain the gateway-side explicit binding? Options: (a) correct the upstream config field and adopt it only with renewed inspection and a reviewed repin; (b) retain the explicit gateway assignment for each supported pin. Recommendation: (a) for a single authoritative profile application path. Safest reversible default shipped now: (b), with all six declared kappa values explicitly applied and tested, so committed-turn physics matches the seed profile without modifying `tom_master`.

No G-gate verdict was made or reported as passed.

## WP-15 — effective kappa-decay physics binding [DONE]

Commit: containing commit `fix(wp-15): bind kappa_decay to effective growth physics`

Evidence: `.venv-gateway/bin/python -m pytest -q -s gateway/tests` → 9 passed, including explicit `kappa_decay == 0.03`, stale-profile-value inequality, creation-metadata provenance, capability provenance, seeded commit behavior, and 100-call preview purity; the local 20-call preview measurement was p50 `0.005 ms`, p95 `0.007 ms`, max `0.009 ms` (build verification only). `cargo test --workspace` → 34 passed, 0 failed, 1 explicitly ignored live-governance case, with the real live-gateway test passing and asserting the new capability field. `npm run schema:validate` → 9 fixtures and 33 core methods. `cargo fmt --all -- --check` and `git diff --check` → clean.

Decisions: `gateway/tom_gateway.py:39-40,251-258` now explicitly binds effective `kappa_decay=0.03` and identifies its provenance as `upstream_literal_0.03_growth_effective`. The other five mechanics controls remain bound to the profile values actually read during growth and live operation: `TOM_TAU1=4.0`, `TOM_HEAL_RATE=0.03263671875`, `TOM_DAMAGE_RATE=0.1034375`, `TOM_KAPPA_DELTA_CAP=0.026884765625`, and `TOM_KAPPA_NOURISH_RECOVERY=0.002`. Source evidence at pinned `tom_master` commit `8799ccbdddf3d5b5939360b91993581af7dab470`: `agency/mechanics/sicd_kappa_update.py:193-205` reads heal/damage but defines decay as literal `0.03` and documents `0.05` as recovery-degrading; `:353` reads only the distinct `TOM_KAPPA_DECAY_SIGMA_REF`; `sandbox/scaling/grow_msr_8d_channel_separated_10k.py:501-507` sources the profile before constructing the grower. No Python consumer of `TOM_KAPPA_DECAY` exists in the pin. Fresh-project `creation_metadata.json`, `/capabilities`, the capability schema/types, and protocol fixtures carry the provenance string so the exception is machine-readable and a future repin must re-derive effective physics.

Deviations: this section corrects and supersedes WP-14's gateway-side binding of the inert profile export `0.053193359375`. It does not rewrite the append-only WP-14 record and does not modify `tom_master`; the profile/export inconsistency remains an upstream owner item.

ESCALATE: none. ESCALATE 4 is resolved by `ORCHESTRATOR_REVIEW_3.md`: this runtime pin binds `0.03`; any future repin requires renewed effective-physics inspection rather than trusting profile declarations.

No G-gate verdict was made or reported as passed.

## WP-16 — Pure structural preview probe (31 August 2026)

Implemented on `build/commit-dynamics-v1`, created from main `87a6a98`. The pre-existing untracked `one_turn.md` is left untouched and excluded from commits.

Changes: the gateway now vectorizes a 10,000-branch read-only alignment × stiffness × inverse-usage scan, selects 16 branches, computes max-cosine anchor resonance, and RRF-fuses lexical/structural ranks with `w_leaf=0.6`, `k=60`. Candidate traces retain channel scores, ranks, matched branches, RRF and admission components; branch traces retain alignment, stiffness, usage and loading-aware scores. Production `turn.prepare` now obtains gateway ranking and runs native admission instead of trusting page-supplied placeholder sections/manifests. Packet digests bind the serving cohort; SQLite context manifests atomically retain activated branch IDs, admitted anchors and traces. Capabilities advertise both preview channels. The local RGM serializer preserves committed anchor leaf vectors across restarts.

Decisions: `context-policy/1.1` was already declared on main; this WP makes the new scoring implement that version rather than inventing 1.2. Projection reuses only the existing pinned pure text preparation chain (`integration/tomowner_msr_runtime_bridge.py:85-103`, `integration/msr_prompt_text_projection.py:15-181`, `integration/msr_field_packet.py:158-226`) followed by pure load projection (`agency/mechanics/msr_8d_loading_aware_readout.py:49-124`, `sicd_msr_load.py:65-124`). No new prose-to-shape translator is introduced; Box 2 remains held. The vectorized mirror cites `leaf_vectors.py:197-253` and deliberately excludes its mutation at 255-257; stiffness cites `semantic_metrics.py:303-318`; anchor cosine cites `leaf_vectors.py:262-304`. All source references are within pinned tom_master `8799ccbdd`. Loading-aware scores are exposed separately without changing the expressly specified cohort-selection formula. RRF is normalized by its rank-one maximum for admission weighting; authoritative hard constraints remain non-evictable. Absent historical leaf vectors retain lexical-only eligibility.

Evidence: gateway pytest **11 passed**, including mirror-vs-pinned selection on an isolated clone, loading-aware-score parity, RRF ordering, restart determinism, and **100 mixed structural previews byte-identical in engine and RGM** while forbidden entrypoints are instrumented to fail. Twenty 10k-tree previews: p50 **17.066 ms**, p95 **29.325 ms**, max **30.352 ms** (500 ms guard). `cargo test --workspace`: **34 passed, 1 ignored**; updated byte-stable golden digest `sha256:d601e32f29e48c70c10030209e0bd89706a8f43175b051a860e36aa5a7c78601`; cohort changes alter the digest. Schema generation/validation: **9 fixtures, 33 methods**. Extension tests: **6 passed**; desktop tests: **1 passed**. Initial golden/conformance failures were expected fixture additions and were corrected before the passing rerun.

ESCALATE: none. No upstream files changed, no TCP listener or forbidden port used, and no G-gate verdict asserted. WP-17 remains a separate commit and this branch will not be merged before orchestrator audit.

## WP-18 — Governed upstream kappa declaration and pure preview surface [DONE; AUDIT HOLD]

Authority/sequencing: `ORCHESTRATOR_REVIEW_5.md` and the owner's subsequent instruction supersede Review 4's sequencing. WP-16 `38883bf` is accepted as interim. WP-17 was stopped before any implementation edits; WP-16b and WP-17 are not started and require the orchestrator-issued repin. No product runtime pin, gateway override, mirror or production code was changed in WP-18.

Isolation: upstream branch `tom-assist/upstream-v1`, based exactly on `8799ccbdddf3d5b5939360b91993581af7dab470`, lives at `/Users/kenmorkaya/PycharmProjects/ToM_assist/.upstream-worktree/tom-master-wp18`. Before creating it, `git status --porcelain=v1 -- <five target paths>` in the owner's checkout was empty. All upstream edits and tests ran in the linked worktree, with bytecode writing disabled and pytest's cache disabled. Every staging operation named one explicit file; no broad staging, stash, reset, owner checkout switch, merge, push or worktree removal occurred.

Exactly two upstream commits (`git rev-list --count 8799ccbdd..HEAD` = **2**):

1. `6dbd5c6c49d76e7cf755c6682bda1bf691bd1fea` — `fix(kappa): add TOM_KAPPA_DECAY env reader and correct stale profile export`. Only `agency/mechanics/sicd_kappa_update.py`, `config/profiles/msr_8d_native_10k.env`, `tests/test_kappa_decay_config.py`. The field at line 205 now uses the neighboring `_env_float` factory pattern with unchanged default `0.03`; the profile export at line 15 is corrected to `0.03` with the required provenance comment. Tests cover unset/default, construction-time environment overrides (including zero), invalid input fallback, explicit constructor precedence, and the corrected profile. No equation or mechanical default changes; explicit non-default environment values are now honored by design.
2. `e9fdef81c8a366ebbec07be9772189eea15cb2ac` — `feat(preview): add pure preview readout module for product previews`. Only `agency/mechanics/preview_readout.py`, `tests/test_preview_readout.py`. The selector preserves the original alignment gate, `stiffness_proxy`, usage penalty, input-order ties, axis fallback, filtering and return shape, while omitting usage mutation. It never calls the mutating selector. Existing resonance, channel-separated projection, readout angle, loading-aware score and ranking are direct re-exports. The module explicitly documents purity and the existing read-only-reference return semantics. No translator or commit dynamics added.

Build-verification evidence (linked worktree, product `.venv-gateway/bin/python`, stub provider; no services):

- First commit tests: `pytest -q -o addopts='' -p no:cacheprovider tests/test_kappa_decay_config.py tests/test_kappa_patchD_semantic_decay.py` → **8 passed**.
- Final required tests plus adjacent kappa regressions: `pytest -q -o addopts='' -p no:cacheprovider tests/test_kappa_decay_config.py tests/test_preview_readout.py tests/test_kappa_patchD_semantic_decay.py` → **59 passed in 3.78 s** (57 new tests and 2 existing regressions).
- Exact selector equality against the mutating original on deep-copied fixtures across 48 axis/K/container cases; stable ties and usage penalties verified separately. **100 mixed readonly calls over the real 10,000-branch seed left serialized engine bytes, every usage count and sample anchor contents identical**, while step, teaching and the mutating selector were instrumented to fail. The 100-call test also exercises re-exported resonance and loading-aware ranking.
- Additional existing leaf-vector regressions: **50 passed, 1 deselected in 0.22 s**. The initially attempted full four-file run produced **109 passed, 1 failed**: the unchanged `TestStage1gFullPoolCoverage::test_leaf_rank_covers_score_rank_and_cos_rank_pools` imports the controller/interface stack and fails on missing `requests` in the minimal gateway environment. It is not a pure-preview test; no dependencies or unrelated source files were changed to mask it.
- Both commit hooks (`gitleaks`) passed; `git diff --check` clean; final linked-worktree `git status --short` empty. The range diff contains exactly the five authorized source/config/test paths above.

Owner-checkout protection evidence, before **and** after both commits/tests:

| Check in `/Users/kenmorkaya/PycharmProjects/tom_master` | Identical before/after result |
| --- | --- |
| `git rev-parse HEAD` | `8799ccbdddf3d5b5939360b91993581af7dab470` |
| `git symbolic-ref HEAD` | `refs/heads/tom-as/assurance-promote-handler` |
| `git --no-optional-locks status --porcelain=v1` | Byte-identical: **53 tracked modifications**, **1,970 untracked entries** |
| SHA-256 of full status output | `efd935faf8a04042f9f2c8c1e0df5cd7a8f1c98f04c5d881a90868ad156ba809` |
| SHA-256 of `git diff --binary HEAD` | `86cb4a857e782653e21d24b24b336304b42c4aaade9ea07823ba1797e8bbbdc9` |
| SHA-256 of `git diff --cached --binary` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty) |
| Status restricted to the five WP-18 target paths | Empty before and after |

Full status snapshots are retained for local audit at `.upstream-worktree/wp18-evidence/owner-status.before.txt` and `owner-status.after.txt`; they compare byte-for-byte equal. The worktree and evidence remain in place and are intentionally not staged into the product repository. Shared Git metadata necessarily gains the requested linked-worktree registration, branch and two commits; the owner's checkout branch, index diff and working-file diff are unchanged.

ESCALATE (non-blocking environment limitation): the optional older controller-import regression needs `requests`, absent from the minimal gateway venv. Safest default: leave dependencies and that unrelated test untouched, disclose the failure, and run all required WP-18 tests successfully. The orchestrator may use a full upstream test environment for that additional regression during audit.

STOP: awaiting orchestrator audit and joint repin. No WP-16b/WP-17 implementation, no merge, no push, no use of port 18790, no access to the off-limits runtime, and no G-gate verdict. This evidence is appended to the product BUILD_LOG; the upstream branch contains exactly the two requested commits.

## WP-19 — Runtime repin and kappa override retirement [DONE]

Commit: containing commit `chore(wp-19): repin runtime to e9fdef81c and retire kappa override`.

Authority/precondition: Review 6 initially stopped on owner HEAD `8799ccbdd`. The owner's subsequent explicit instruction, “YOU DO IT”, authorized the checkout previously reserved for the owner. After verifying all five upstream target paths clean, the clean linked audit worktree was detached at its existing audited commit (retained in place), freeing `tom-assist/upstream-v1`; the owner's checkout was then switched to that branch. Verified HEAD `e9fdef81c8a366ebbec07be9772189eea15cb2ac`. All 53 tracked modifications and 1,970 untracked status entries remained byte-identical; before/after working diff hash `86cb4a857e782653e21d24b24b336304b42c4aaade9ea07823ba1797e8bbbdc9`, staged diff hash `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. No stash, force switch, reset, upstream edit, merge or push.

Changes: product pin `e9fdef81c`; profile-derived kappa assignment replaces the literal override, guarded at project creation by an absolute-difference tolerance of `1e-12` around audited effective `0.03` (also rejects NaN/infinity). Provenance becomes `profile_env_reader_wp18_effective_0.03`. References pin, capability schema/generated type/shared example and the live Rust provenance assertion agree. The prior WP-18 log section is committed as-is.

Decisions: the protocol capability schema uses a const, so its provenance and example needed coordinated updates beyond the four named Review 6 paths. Existing tests asserting the old inert profile export and inequality were updated to the corrected `0.03` export and equality; the actual seeded-project assertion `kappa_decay == EFFECTIVE_KAPPA_DECAY == 0.03` is unchanged. No packet golden or canonical digest fixture changed. Added three explicit fail-closed cases for stale `0.053193359375`, NaN and infinity.

Evidence against the audited owner checkout: gateway pytest **14 passed** (all prior 11 plus three tripwire cases), 100-preview byte purity intact; 20-call latency p50 **16.327 ms**, p95 **28.430 ms**, max **32.412 ms**. Dedicated live Rust gateway test **1 passed**. `cargo test --workspace`: **34 passed, 1 ignored**, including the unchanged packet golden. Extension tests **6 passed**. Schema generation/validation **9 fixtures, 33 methods**. `git diff --check` clean. Local build verification only; no G-gate verdict.

ESCALATE: none. Proceed next to WP-16b's strict unchanged-output check; any divergence must be reported without changing goldens.

## WP-16b — Upstream import conversion [STOPPED: strict output-parity divergence]

Preflight at product commit `cbc3f87`, runtime `e9fdef81c8a366ebbec07be9772189eea15cb2ac`: compared the existing `gateway.structural_preview.select_cohort` output directly with `agency.mechanics.preview_readout.select_activated_branches_readonly`, using the same fresh 10,000-branch project, ID-sorted input, identical projected axes and K=16. Compared each current loading-aware trace score with the upstream exported `loading_aware_8d_score`. All inputs were read-only; the comparison used a disposable product-local temporary project, never a live owner runtime or service.

The branch IDs and their order were identical for all four sampled drafts: “first then after the construction stage”, “connected beam column load path”, “rule contradiction equations”, and “warm the deterministic query path”. Numeric output equality was **not** exact. Examples:

| Draft / field / branch | Gateway mirror | Audited upstream |
| --- | --- | --- |
| construction stage / selection score / `108486` | `0.00019005414645648184` | `0.0001900541464564818` |
| rule contradiction / selection score / `3` | `0.008997110523346763` | `0.008997110523346761` |
| construction stage / loading trace / `93686` | `0.4632659227078507` | `0.46326592270785094` |

Observed maximum absolute differences in this sample: selection score `1.734723475976807e-18`, loading trace `2.220446049250313e-16`. These are consistent with NumPy-versus-scalar floating-point evaluation differences; the existing geometry tests compare these scores using `pytest.approx`, so their passing result does not establish bit-identical outputs. This preflight does not establish full packet/anchor equivalence after conversion.

ESCALATE: Review 6 explicitly requires STOP on any output divergence. Question: may WP-16b accept a documented numerical tolerance (recommended `1e-12` for score fields only), while still requiring exact branch/anchor identity and ordering, unchanged packet text/digests and untouched goldens? Alternative: require bit-exact diagnostics and commission a separately reviewed canonical arithmetic change; upstream is currently frozen, so that is not authorized here. Safest reversible default: leave the gateway mirror and every golden unchanged; do not implement or commit the conversion, and do not start WP-17. WP-19 remains complete as `cbc3f87`. This blocked section is appended for audit, not a completion claim or G-gate verdict.

## WP-16b — Canonical upstream import conversion [DONE]

Commit: containing commit `refactor(wp-16b): import upstream preview_readout, retire gateway mirrors`.

Resolution: owner/orchestrator approved `1e-12` only for raw-score floats in the transitional mirror-versus-upstream comparison; selection, ordering, packet text, ID lists and digests remain exact. The difference comes from NumPy vector operations (power, normalization, dot-product reduction and trigonometry) versus the pure-Python scalar operation order in the audited upstream implementation. No formula, weight, policy or golden was changed to absorb those last-bit differences. **Upstream `e9fdef81c` arithmetic is now canonical.**

Changes: gateway projection, branch selection and anchor resonance delegate to `agency.mechanics.preview_readout`; duplicated NumPy scoring is removed. Product ID sorting, trace assembly, triggers and RRF (`w_leaf=0.6`, `k=60`) remain product glue. Trace stiffness uses upstream `semantic_metrics.stiffness_proxy`; alignment is decomposed from the canonical selection result rather than implementing a second selector. The upstream scalar scan meets the latency guard, so no parallel arithmetic implementation is retained merely to preserve vectorization. `context-policy/1.1` is unchanged.

Evidence: a one-time, non-persistent transition comparison loaded the exact old mirror from product commit `cbc3f87` and compared **20 full previews** against the new adapter on the same seeded project with three committed anchors. Every non-score field, branch/anchor ID and ordering, text, activation ID and checkpoint digest matched exactly. 855 raw-score differences were bounded by **3.885780586188048e-16**, below the authorized `1e-12`; engine+RGM bytes unchanged. This temporary tolerance comparison is retired, not added to the regression suite. The permanent structural test is re-pinned to the canonical upstream selector and loading-aware score using exact equality, with no tolerance.

Gateway tests **14 passed**, including unchanged 100-preview byte purity and restart determinism; 20-call preview latency p50 **13.253 ms**, p95 **24.872 ms**, max **25.035 ms**. Rust workspace **34 passed, 1 ignored**; packet renderer/text/manifest golden and digest `sha256:d601e32f29e48c70c10030209e0bd89706a8f43175b051a860e36aa5a7c78601` pass unchanged. No golden files were edited. Schema validation **9 fixtures, 33 methods**; extension **6 passed**. `git diff --check` clean. No upstream changes or G-gate verdicts.

ESCALATE: resolved by the explicitly limited transitional tolerance; proceed to WP-17.

## WP-17 — Full commit dynamics and two-shelf memory [DONE; AUDIT HOLD]

Commit: containing commit `feat(wp-17): full commit dynamics and two-shelf memory`. Preceded on `build/commit-dynamics-v1` by WP-16b commit `aca576f`. Runtime remains `e9fdef81c8a366ebbec07be9772189eea15cb2ac`; Review 4's experience requirements apply after Review 6's repin/conversion sequencing. No new translator, runtime repin or golden adjustment.

### Commit transaction and production binding

`ProjectRuntime.commit_turn` executes **step → RGM write → response teaching → sent-branch usage rotation → front-row reinforcement/decay/prune** on isolated engine/RGM copies under the project lock. A project-owned SQLite `library.sqlite3` in `projects/<id>/tom/` durably retains the complete original content and its SHA-256 **before** any RGM admission. Its `runtime_head` row atomically commits serialized engine/RGM bytes, the full idempotency map and settings alongside all demotion events in one `BEGIN IMMEDIATE` transaction. Any phase exception restores the prior in-memory objects and rolls back the entire quintuple and its events/keys. An aborted attempt may leave a harmless, unused permanent-library copy; it cannot leave an unbacked front-row item. JSON tree/RGM/key files are recoverable projections of the SQLite head, not separate commit authorities. A projection-write failure leaves the successful commit durable and is logged; restart reconstructs it. A stale runtime-head digest refuses another process's conflicting commit.

The daemon now binds an explicit `turn.sent` to the persisted context manifest, captures the provider response in the existing turn store, evaluates it, and calls the same commit gateway for the completed exchange. Migration `003_runtime_commits.sql` adds sent-context bindings and runtime receipts. Branch and admitted-anchor IDs come only from `context_runs`, never response payloads; forged IDs in the production test are ignored. The stable key is `sent-turn:<sent user turn id>`, covering all five dynamics, repeated responses, lost replies, restart and repeat resolution. A packet already bound to a different sent turn is rejected instead of guessing which exchange a response belongs to. Draft-only/unsent contexts cannot commit.

Open interventions defer the quintuple until resolved, including native conflicts preserved as REVIEW during gateway failure. Both desktop and daemon use `resolve_intervention_with_runtime`; any dismissed finding sets `conflict_dismissed`, and `teach_on_conflict=false` skips only teaching. Accepted/false-positive findings do not disable teaching. Gateway failure preserves captured/evaluated data and reports `runtime_commit_pending`; replaying evaluation or resolution retries the same durable key. No preview-triggered or background retry is introduced. The low-level legacy user-only commit API remains usable for fixtures/seeding, with teaching explicitly marked `no_provider_response`; production supplies both sides of the exchange.

### A — Expected teacher shape at the new pin

Inspected pinned `agency/mechanics/sicd_engine.py:4869-4935`: `apply_leaf_vec_update` consumes `semantic_axis`, `loads`, and raw `confidence`, composes an eight-dimensional vector, gates at configured confidence (profile default 0.3), and applies axis-weighted normalized EMA to branches. `controller/tom_controller.py:6375-6383` invokes it after the response in the same tick. `agency/mechanics/leaf_vectors.py:44-94` defines the raw-confidence contract and normalized EMA. Product mapping at `gateway/tom_gateway.py:554-566` reuses the **existing pinned pure text projection** already used by WP-16b, not a new prose-to-shape model:

| Teacher input | Existing channel-separated projection output |
| --- | --- |
| `semantic_axis` | `raw_8d[0:3]`, as a three-element list |
| `loads.delta_x`, `delta_F`, `phi`, `intensity` | `raw_8d[3:7]`, in that order |
| `confidence` | `raw_8d[7]`, never the normalized vector component |

Projection preparation is the pinned chain cited in `gateway/structural_preview.py:9-27`: `integration/msr_prompt_text_projection.py`, `integration/msr_field_packet.py`, and upstream `preview_readout`'s channel-separated projection export. The existing user-text-to-physics commit load is unchanged. Teaching requires enabled leaf vectors and verifies the last-teach tick after a confident update, because upstream deliberately swallows internal teaching exceptions. The exact-EMA test compares one post-physics branch to the pinned composition/EMA formula with exact equality. Upstream arithmetic remains canonical; WP-16b's transitional tolerance is not reused here.

### B/C — Exact credit and permanent seating

Only the deduplicated branch IDs in the sent manifest receive `usage_count += 1`; a missing/removed serving branch fails the transaction rather than substituting a cohort. The new RGM-write seam asserts the durable content-hash twin. Full exchange content is retained before upstream's zero-copy storage (`memory/rgm.py:794-807`, which clears content and bounds summaries to 256 characters).

Reinforcement mirrors the baseline at `memory/rgm.py:949-978`: public `anchor` (`:1546-1551`, backed by `anchor_memory :1426-1442`) supplies the +0.05/cap-at-1 strength change; product bookkeeping increments access count and sets the current access tick. It is applied only to admitted anchors. Public `run_decay_and_compaction :1513-1517` then advances the RGM tick once, decays every anchor, and invokes the product demotion override. Immediate pruning from upstream `write_memory :1238` is deferred until this last phase. Neither `read_memory :1338-1386` nor the mutating branch selector is called from preview.

Decisions: new conversation anchors use decay rate **0.002**, matching upstream's conversation examples (`memory/rgm.py:326,496`); the record-type default of zero would otherwise prevent the owner-requested unused-anchor fade. The baseline fixed reinforcement is used, because this path has no resilience input. Zero-strength records demote with reason `decayed`; excess capacity demotes the weakest eligible records with reason `capacity`, then access count and ID as deterministic ties. Capacity defaults to **4096** per project (configurable integer 1..1,000,000), and pruning stops at capacity rather than using upstream's 90%-capacity batch. Current-packet admitted anchors are protected from **capacity** eviction for that commit so a weak readmitted anchor is not immediately evicted again; they become eligible on the next commit. Capacity below the number of admitted anchors fails closed. This is the seating policy chosen to reconcile readmission with strict capacity.

Every demotion verifies the full SQLite twin again before removal from the front-row/vector/symbolic indexes, preserves the original content/hash, saves seating metadata, and records ID, content hash, reason, commit key and tick. Readmission restores that full durable record on its next committed manifest use. Content-checksum duplicates reuse the first durable ID without reinforcing an unadmitted existing anchor; otherwise upstream's duplicate-write gate (`memory/rgm.py:851-854`) would quarantine repeated identical committed exchanges. Distinct sent turns still experience physics/teaching/rotation once each.

The larger front row is safe from permanent-record loss because capacity affects only seating: permanent content is never deleted by pruning or checkpoint restore. Capabilities/schema/Rust/generated TypeScript expose all five `commit_dynamics`, `front_row_capacity`, and `teach_on_conflict`. Desktop Settings persists the two controls per project; Diagnostics displays paginated demotion events and counts through the same local gateway, with an explicit unavailable error if it is down.

Integration decision: the prior dev runner used a daemon database separate from the desktop's Tauri-default database. It now passes explicit `TOM_ASSIST_APP_SUPPORT` and `TOM_ASSIST_GATEWAY_SOCKET` to the desktop, so settings, intervention resolution and diagnostics address the daemon's selected projects/runtime. Standalone desktop behavior retains its old store unless explicitly configured; no existing database is moved or overwritten. The dev-run prerequisite warning was also brought into agreement with the already-approved `e9fdef81c` pin. Ledger export still does **not** include the runtime library; gateway/desktop documentation now explicitly requires backing up the full gateway project directory for runtime recovery.

### Checkpoints and verification evidence

Runtime checkpoints now include an integrity-checked commit-key/settings snapshot. Restore resets engine/RGM, settings and gateway deduplication exactly, but preserves the permanent library and demotion audit. Upstream load normalizes `axis_w` at `sicd_engine.py:1641` and resets semantic ages for unsupervised seeds at `:1855-1865`; product checkpoint loading restores the saved axis/age/last-teach fields after load, while fresh seed initialization retains the upstream behavior. This makes the required post-teaching save → commits → restore engine/RGM byte identity real, not just a metadata-digest comparison. These are runtime checkpoints, not rollbacks of the separate authoritative ledger.

Final local build checks:

- `PYTHONDONTWRITEBYTECODE=1 .venv-gateway/bin/python -m pytest gateway/tests -q -s` → **29 passed in 72.87 s**. Includes exact teacher EMA and phase order; only-serving usage; only-admitted reinforcement; both conflict-policy values; replay/restart identity; injected failures in step/write/teach/rotation/reseating/journal with whole-quintuple rollback; missing-twin failures at write and demotion; capacity **4096** overflow, lowest-strength demotion, readmission and decay; preservation of long Unicode originals after upstream zero-copy, demotion and restart; exact post-teaching checkpoint restore; project-local durable settings; and recovery after failed JSON projection writes.
- The existing **100-call** structural preview test remains byte-identical for engine/RGM and now also checks the entire logical permanent-library database dump unchanged. Teaching, engine step, RGM read and the mutating selector are instrumented to fail if preview reaches them. Final 20-call preview timing: p50 **13.101 ms**, p95 **25.102 ms**, max **26.112 ms**.
- `cargo test --workspace` → **35 passed, 0 failed, 1 explicitly ignored** existing live-governance test. The additional real-gateway production-envelope test proves unsent rejection, trusted manifest IDs, one complete exchange/receipt, replay after restarting daemon and gateway, deferred CONFLICT, and exactly-once dismissal with teaching disabled. Live adapter handshake/checkpoint test also passes. Tests use disposable Unix sockets only. An initial sandbox-only run could not bind a Unix socket; the authorized rerun passed without any TCP listener or existing service manipulation.
- `npm run schema:validate` → **9 fixtures, 33 methods**; schema regenerated. Extension **6 passed**, desktop **2 passed** (including project-isolated memory settings), provider adapters **4 passed**. All available workspace TypeScript typechecks pass; desktop and extension optimized builds pass. `cargo fmt --all -- --check`, `sh -n scripts/dev-run.sh`, and `git diff --check` are clean.
- Packet golden text/test and digest remain unchanged from WP-16b; the Rust golden test passes. No golden fixture or packet scoring/policy was adjusted.

### Audit limitations, escalation and protected state

ESCALATE (legacy migration data gap): an old zero-copy anchor may have only a truncated summary and no available original matching its stored hash; an old checkpoint may lack a saved idempotency/settings snapshot. Question for audit: supply an explicitly hash-verified original-content migration and legacy checkpoint policy, or retain fail-closed compatibility? Recommendation/safest shipped default: migrate only verifiable full/short originals, refuse unverifiable anchors and legacy checkpoints rather than invent content or a false exact restore. This does not block new or fully verifiable projects. Permanent-library backup/export integration and a packaged end-to-end GUI journey remain explicit follow-up work; no claim that the deterministic UI test exercises the packaged window.

Final protected-checkout proof: owner `tom_master` HEAD remains **e9fdef81c8a366ebbec07be9772189eea15cb2ac**. Full status-output SHA-256 remains `efd935faf8a04042f9f2c8c1e0df5cd7a8f1c98f04c5d881a90868ad156ba809` (the same 53 tracked modifications and 1,970 untracked entries); working diff SHA-256 remains `86cb4a857e782653e21d24b24b336304b42c4aaade9ea07823ba1797e8bbbdc9`; staged diff is still empty (`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`). The inspected runtime source/profile paths are clean. Gateway upstream imports now explicitly disable bytecode writes. The linked audit worktree is retained and clean. No protected runtime source was edited, no off-limits runtime was read/imported, and no port 18790 was used.

STOP after WP-17 for orchestrator audit. No merge, push, branch deletion or linked-worktree removal. All results above are implementation/build verification, not G-gate verdicts.

## WP-20 — Complete project recovery and packaged-app journey [DONE; AUDIT HOLD]

Authority: owner's WP-20 instruction (31 August 2026), with latitude on mechanics; upstream repositories untouched, preview purity retained, no G-gate claims. Branch **`codex/wp-20-runtime-recovery`** was created directly from main **`7d1003407f0dbfc665aa5f84c55d96ccc2e3f162`**. Initial status contained only the previously authorized untracked `.upstream-worktree/`. Commit: containing commit **`feat(wp-20): complete project recovery and packaged journey`** (same self-reference convention as prior WPs). Main is not moved.

### Recovery implementation and decisions

The production desktop export/import commands now use the shared Rust `assistd::recovery` coordinator plus gateway runtime-archive endpoints. Settings provides an editable destination, explicit complete export, complete backup, verification and verified import. Import independently revalidates; changing the directory or failed verification disables UI import. The warning explicitly discloses retained full conversations and unencrypted local storage. These are not redacted diagnostic bundles.

Decision: use a documented directory archive **`tom-assist-recovery/2`**, rather than add a compression dependency. It contains all selected-project relational rows, canonical state/events, transcript policy, WAL-aware SQLite online backup of the permanent library, original creation metadata and all retained runtime checkpoints. The library includes full original records, content hashes, demotion history, exact engine/RGM head bytes, settings and the complete runtime idempotency-result map. The ledger includes turns, sent bindings, context manifests, response evaluations, interventions and runtime receipts, not merely state objects. Runtime/seed/profile identity and each file's SHA-256 are recorded. The application/runtime dependencies are prerequisites, not copied upstream repositories; legacy format-1 redacted exports are explicitly not recovery archives.

Decision: explicit per-project backup uses exactly the same verified complete format, at a fresh timestamped sibling path. The existing migration-failure `.bak` remains a ledger-only incident copy, not a complete backup; automatic update/migration backup scheduling is not added by this WP. This distinction and the instruction to take a complete backup before installation changes are in `docs/PROJECT_RECOVERY.md`. No old log entry was rewritten: this section supersedes WP-17's outstanding permanent-library export/backup integration and packaged-window journey limitations.

Export holds SQLite's ledger writer lock while snapshotting the runtime under its project lock. It verifies native replay/digests and runtime integrity, syncs files/directories and publishes a private staged archive. Unknown schemas refuse an incomplete backup. Existing destinations, including dangling symlinks, are refused. Import freezes/reverifies the input in private staging; exact schema/inventory/checksum, project identity, runtime pin/seed/profile, durable content twins and checkpoint digests are checked. A staged ProjectRuntime must serialize to the exact archived engine/RGM bytes. No scoring, golden, physics or upstream source change is involved.

Decision: preserve project/turn/event/packet identity and refuse any pre-existing target project/runtime; no overwrite/merge or invented missing originals. Audit-table integer row IDs alone are reallocated to avoid collisions with unrelated projects. The target ledger transaction and runtime intent coordinate publication via new `004_recovery.sql` receipts. Failed publication/ledger writes roll back ledger rows and quarantine only the new import. A crash before ledger COMMIT fails closed and can resume with the same archive; a lost finalization reply after COMMIT is finalized from the durable receipt on next project load. Unpublished staging/quarantine evidence is retained, not silently deleted. Captured evaluation replay retains WP-17's exactly-once key across archive/restart, including the gateway-result/ledger-receipt gap. Full details and recovery instructions: `docs/PROJECT_RECOVERY.md`.

### Actual packaged-app journey

The Computer Use skill was used to exercise the real packaged window. `scripts/package-macos/packaged-journey.mjs` is a repeatable accessibility-driven assertion test, not an injected DOM driver or fake backend. `journey-runtime.py` launches only its owned unsigned release app, release daemon and real pinned Python gateway, using disposable stores and Unix sockets. It supplies read-only database evidence and process restart/replay controls; UI actions go through the real controls and Tauri IPC. A separate `local.tom.assist.wp20` bundle ID avoids the owner's app identity; the compiled production binary has no test-only hooks.

Decision: expose an explicitly labeled **Local exchange diagnostic** in the desktop. It prepares a real packet, requires explicit marked-sent confirmation, then evaluates a simulated provider response through the production daemon path. It makes no provider/API/network request. Its warning requires a disposable project because evaluation applies real experience. The pre-existing fixture-oriented capture UI supplies the synthetic decision. Native exchange IPC allows only prepare/sent/evaluate and checks project identity. UI regression tests cover the sent/evaluate gate and recovery verification/path invalidation.

Final audit run completed all seven scripted stages: **create/capture → repeated pure packet preparation → evaluate/commit → export/verify/backup/verify → cold restart + replay → fresh-store import → recovered cold restart + replay**. Native evaluation returned `PASS` for the synthetic response (an evaluation result, not a spec gate verdict). Captured decision remains visible in the packaged Ledger after both restarts. Snapshot comparisons require exact equality, not tolerance. Result: one state object, two events, two captured turns, one context, one evaluation, one runtime key/receipt, one full 1,741-code-point Unicode original. Engine tick **4707 → 4708**, final RGM tick **4709**, response teaching true, **16** serving branch IDs; repeated preparation and both evaluation replays add no experience. The complete library original/hash, settings, key/result map, receipt, native state and engine/RGM bytes survive fresh-store import and restart exactly.

Final artifact: `.tmp/wp20-final-package.B55x5O/Tom Assist.app`; binary SHA-256 **`593c5f32de7417f430f577220ca455465436d43f1849ad70bb48057e4f369802`**. Release daemon SHA-256 **`adfd0c4e5abb270162e66faed82e8601aee110df0aaa9941c736bf378e0606c2`**. Local raw evidence is retained under **`/private/tmp/tom-assist-wp20-audit-20260831/`**: `journey-evidence.json`, seven `.ax.txt` transcripts, seven screenshots, child logs, complete archive, complete backup, source and recovered stores. All three owned children were stopped successfully; no existing service was stopped. Earlier exploratory artifacts are retained separately.

Evidence identities from that run:

- Project: `d7ebb446-b45d-4af9-9688-16e19f126b8c`.
- Raw journey report SHA-256: `1a199eaafb5123aa72754f869c86db103a3c951ec9910581f6c94e9c7744960a`.
- Complete archive manifest SHA-256: `01acc70eb0040cf2c49c4661f5fe21ad392102559fb56a6d973a011968f5dda4`.
- Canonical native state: `sha256:fbeb5e20600ee70b8dfdfe5bd13724c0adf00805b12553a4f3a70b30cf80afc0`.
- Packet: `sha256:f83265ed22dabd295159d7e16977ee02906d5338146dd642be18b9eb1124e850`.
- Runtime checkpoint: `sha256:cecd474d60c332e22ab9142ba4aa57b9f8c3050b514f3b78c3bbf221a159703c`.
- Exact engine bytes SHA-256: `d191a2efd0f8fdc8a38e757d04a6a71ad877233ffd623678c4551bb5a3495f07`; exact RGM bytes: `e6f81c8c564525184c832bb9eb14e173186ea0f9e88bfdae1a46bf8e13698596`.
- Full retained Unicode original SHA-256: `cf34fa6d3e686dab399b1f7347660b161e0824338241859499744abba4017638`.

### Final build verification and audit boundary

- `cargo test --workspace` → **36 passed, 0 failed, 1 explicitly ignored** existing live-governance test. New real-gateway recovery integration passes in **47.04 s**: WAL data included, other-project exclusion/preservation, full ledger/runtime restore, settings/checkpoint history, existing/dangling destinations refused, faults before and after runtime publication roll back/quarantine, lost finalization reply recovers, retry succeeds, and restarted evaluation does not double commit.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD:/Users/kenmorkaya/PycharmProjects/tom_master" .venv-gateway/bin/python -m pytest -q gateway/tests` → **40 passed in 137.97 s**. Eleven archive tests cover long Unicode originals, settings/demotions/keys/checkpoints/exact bytes, read-only verification, both crash windows, abort quarantine, existing/dangling destination refusal, missing/changed files, pin mismatch, symlink/traversal and rehashed-but-invalid content/twins/settings. The existing 100-call preview-purity/forbidden-call instrumentation remains green with exact state/library equality; no golden was modified.
- Desktop UI **4 passed**; provider adapters **4 passed**; extension **6 passed**; schema validation **9 fixtures, 33 core methods**; all available workspace TypeScript typechecks pass; harness instrumentation **2 passed**.
- Release daemon and unsigned packaged desktop builds pass. `cargo fmt --all -- --check`, `git diff --check`, shell syntax and journey JavaScript syntax checks pass. An intermediate verification-endpoint error conversion failed Rust compilation, was corrected, and the full suite/build/journey were rerun on the final code. Early exploratory AX clipboard/menu readiness failures led to settable controls, fresh AX lookup and lifecycle readiness checks; the final scripted audit run completed without those failures.

Protected checkout proof: owner's `tom_master` remains **`e9fdef81c8a366ebbec07be9772189eea15cb2ac`** on **`tom-assist/upstream-v1`**. `git status --short` output SHA-256 matches the baseline **`efd935faf8a04042f9f2c8c1e0df5cd7a8f1c98f04c5d881a90868ad156ba809`**; working diff SHA-256 remains **`86cb4a857e782653e21d24b24b336304b42c4aaade9ea07823ba1797e8bbbdc9`**; staged diff remains empty (**`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`**). Imports disable bytecode writes. No upstream source, owner checkout, linked worktree or excluded runtime was changed; the off-limits runtime was not read/imported. No TCP listener, port 18790, provider contact, push or merge.

ESCALATE: none newly blocking. Existing fail-closed legacy-original/checkpoint compatibility remains; no missing original is fabricated. Archives are unencrypted alpha data and require the matching installed runtime/seed/profile. Signing, notarization, standalone bundled sidecar distribution, live-provider testing, automatic backup scheduling and validation-programme batteries remain outside this verification. **STOP for orchestrator audit after WP-20. No G-gate verdicts.**
