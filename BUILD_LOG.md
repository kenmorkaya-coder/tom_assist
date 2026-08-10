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
