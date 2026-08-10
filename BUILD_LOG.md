# Tom Assist One-Shot Build Log

This file is append-only. Verification statements describe build checks only and are never G-gate verdicts.

## WP-00 — Repository and workspace scaffold [DONE]

Commit: containing commit `chore(wp-00): scaffold Tom Assist workspace` (self-referential SHA recorded in FINAL mapping)

Evidence: `cargo build --workspace` → clean debug build; toolchains: `rustc 1.94.1`, `cargo 1.94.1`, `node v25.6.1`, `npm 11.9.0`, `Python 3.12.7`.

Decisions: Rust edition 2024 and workspace `rust-version = 1.94` follow the installed stable toolchain; crate names use the `tom-assist-*` prefix while directory names remain contract-exact. Extension private key material is ignored at `apps/extension/.keys/`; only the manifest public key will be committed in WP-05.

Deviations: none.

ESCALATE: 1. The required log format asks each WP section to contain the SHA of the same commit that contains that section, which is cryptographically self-referential and cannot be satisfied literally. Safe reversible default: identify each containing commit by its unique conventional message and append the resolved SHA mapping in `FINAL`.
