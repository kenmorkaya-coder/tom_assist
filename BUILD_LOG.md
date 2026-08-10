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
