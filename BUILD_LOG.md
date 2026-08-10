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

## WP-02 — Event-sourced persistence [DONE]

Commit: containing commit `feat(wp-02): add deterministic event store` (resolved in FINAL)

Evidence: `cargo test -p tom-assist-persistence --all-features` → 5 passed, including event replay equality, candidate-authority rejection, CAS conflict, supersession audit lineage, snapshot/export/import verification, and canonical digest equality across 25 cold reopens.

Decisions: SQLite is bundled through `rusqlite 0.37.0` for reproducible local builds. Materialized object/edge rows retain their full canonical JSON alongside query columns so replay equality is tested without lossy relational reconstruction. Project creation is an immutable version-0 event; authoritative state mutations alone increment `state_version`. Portable alpha exports are documented files (`events.jsonl`, `state.json`, transcript policy, canonical manifest/checksums) rather than a custom binary archive.

Deviations: SQLCipher is represented by the compile-tested `encrypted-store` feature and an explicit unavailable key-loading result, default off per D13; no encryption capability is claimed.

ESCALATE: none.
