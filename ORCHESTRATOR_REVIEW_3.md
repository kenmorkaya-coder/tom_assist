# ORCHESTRATOR REVIEW 3 — WP-13/WP-14 audit, ESCALATE 4 resolution, WP-15

**From:** Claude (build orchestrator)
**Re:** `18f009c` (WP-13), `632c7c4` (WP-14) on `build/one-shot-v1`
**Date:** 10 August 2026

## WP-13 — accepted

Independently verified: `GovernanceEngine` is constructed inside the production `evaluate_turn` dispatch with the real `GatewayVerifier` (`crates/assistd/src/lib.rs:433`); the gateway-down path records `gateway_unavailable` in both wire diagnostics and audit events and caps at `REVIEW` via a native-only rerun (`:458-661`); the full fixture now consumes the injected engine. My runs: `cargo test --workspace` → 34 passed; live governance case → 1 passed. The Review-1 seam is closed.

## WP-14 — accepted, with one required correction (WP-15)

Independently verified: digest-checked seed load, fail-closed corrupt-seed behavior, two-project creation determinism, purity re-proven at 10k scale, seed lineage in checkpoints and capabilities. My runs: gateway pytest → 9 passed.

The deviation Codex flagged (and correctly escalated) resolves against the *declared* value, however. The orchestrator audit established the effective physics from source:

1. `KappaUpdateConfig.kappa_decay` is a literal `0.03` with **no environment reader** (`agency/mechanics/sicd_kappa_update.py:205`); the only similar reader is `TOM_KAPPA_DECAY_SIGMA_REF` (`:353`), a different parameter.
2. The grower (`sandbox/scaling/grow_msr_8d_channel_separated_10k.py:501-507`) **sources the profile env** before growing — so the five env-read controls (`TOM_TAU1`, `TOM_HEAL_RATE`, `TOM_DAMAGE_RATE`, `TOM_KAPPA_DELTA_CAP`, `TOM_KAPPA_NOURISH_RECOVERY`) took the profile's values during growth, but `kappa_decay` remained `0.03`.
3. The live backend stands the tree up the same way (profile env + config-from-env), so its operating physics is also `0.03`.
4. Upstream documents `0.03` as selected via production sweep, with an explicit warning that ~`0.05` "degrades recovery" — the profile's `0.053193359375` export has therefore **never been in effect anywhere** and sits in the documented degraded range.

Binding `0.0531` in the gateway would make Tom Assist the only runtime ever to run this tree under that value — diverging from both its growth physics and the live backend, in the direction upstream warns against.

### WP-15 — bind the tree's true physics (required, small)

1. In the gateway's per-project config application, set `kappa_decay = 0.03` (the effective growth/operating value), keeping the five env-read controls at the profile's declared values. Keep the assignment explicit (do not rely on the upstream default silently) with a comment citing the four facts above.
2. Update the creation-determinism test's parameter assertions accordingly, and add one assertion that `kappa_decay == 0.03` specifically, so a future profile or upstream change surfaces as a deliberate decision.
3. Record in `creation_metadata.json` / capabilities lineage: `kappa_decay_source="upstream_literal_0.03_growth_effective"` (or equivalent), so the provenance of the exception is machine-readable.
4. One commit: `fix(wp-15): bind kappa_decay to effective growth physics`. Append WP-15 to `BUILD_LOG.md`; re-run gateway suite + workspace as evidence.

### ESCALATE 4 — resolved

The value question is settled by the facts above: for this pin, the product binds `0.03`. The *upstream* inconsistency — a profile exporting `TOM_KAPPA_DECAY` that nothing reads — is real, but fixing it (adding an env reader, or deleting the stale export) is an **owner decision in tom_master**, out of scope for the product build permanently, not just for this shot. Recorded as an owner item. On any future repin, renewed inspection re-derives the effective parameter set rather than trusting profile declarations; this episode is the standing justification for that rule.

## Merge plan (after WP-15)

1. Orchestrator commits its own uncommitted artifacts (the three review files and the corrected `docs/spec/runtime_inspection_findings.md`) as a docs commit on the branch.
2. Fast-forward-or-merge `build/one-shot-v1` → `main` (owner's call to execute or delegate).
3. First post-merge activity: the live ChatGPT selector session with the owner at the keyboard.

No G-gate verdicts were made or implied in this review.
