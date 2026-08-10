# ORCHESTRATOR REVIEW 1

**From:** Claude (build orchestrator)
**Re:** One-shot build, `build/one-shot-v1` @ `9b1fc63`
**Date:** 10 August 2026

## Audit verdict

**Accepted, with one follow-up work package (WP-13) required before this branch merges to `main`.**

All definition-of-done claims were independently re-verified by the orchestrator on this machine, not taken from the log:

| Claim | Orchestrator verification |
|---|---|
| Gateway suite incl. 100-call preview purity | `pytest -q gateway/tests` → **6 passed** (re-run) |
| Rust workspace | `cargo test --workspace` → **32 passed, 0 failed** (re-run); ignored live-governance case run explicitly → **1 passed** against the real pinned runtime |
| Extension / adapters / schemas / desktop | **6 / 4 / (9 fixtures, 33 methods) / smoke** all green (re-run) |
| Upstream repos untouched | `tom_master` HEAD still `8799ccbdd`; working-tree modifications in all three upstream repos carry mtimes of **27 June** — pre-existing owner work, predating the 10 Aug build window. No build side effects found, including `.tom_persist/`. |
| ESCALATE 2 factual claim | **Confirmed against source.** `interface/stm_ltm_retrieval.py:187-193` does call mutating `rgm.read_memory()`. The binding inspection document was wrong to list the wrapper as pure; it has been corrected in place (`docs/spec/runtime_inspection_findings.md`), with credit to the build's audit. |
| Production governance seam | **Confirmed.** `crates/assistd/src/lib.rs:349-414` computes PASS/REVIEW/INCOMPLETE from lineage/completeness only and always returns `intervention_ids: []`. The 11 rules run only where the fixture composes `GovernanceEngine` manually. |

The build's own disclosure quality was high: both open escalations were factually correct, the weakest-points list identified the real production gap first, and no gate verdicts were claimed anywhere.

## Escalation resolutions (owner-ratified defaults)

1. **ESCALATE 2 — resolved: option (b) is permanent for this runtime pin.** Preview stays on the direct `VectorStore.query` + trigger-mirror composition, protected by the purity test. An upstream pure wrapper in tom_master is a possible future change **by the owner only**; the product build never modifies tom_master. If such a wrapper lands, adoption requires a renewed inspection and a reviewed repin — not a blind SHA bump.
2. **ESCALATE 3 — resolved: option (b) is permanent for this runtime pin.** `ToMClient.process` is not used anywhere; the direct engine+RGM commit path stands. Same repin discipline applies.
3. **ESCALATE 1 — closed** as recorded (commit-subject mapping in FINAL is the accepted convention).

## WP-13 — Wire GovernanceEngine into production `response.evaluate` (required)

The gap: a real user today gets evaluation badges that can never show CONFLICT, because production dispatch never runs the intervention rules that WP-08 built and tested. Close it exactly as the fixture already composes it:

1. Inject the WP-08 `GovernanceEngine` (with its gateway client and `governance-policy/1.0`) into `AssistService`, and invoke it inside `evaluate_turn` after lineage checks, for complete + non-stale responses. Precedence: `INCOMPLETE` and stale-`REVIEW` semantics are unchanged; otherwise the evaluation state derives from intervention severity (`blocking_commit` present → `CONFLICT`; any warning-level → `REVIEW`; none → `PASS`).
2. Persist the produced interventions and return their real IDs in `EvaluationResult.intervention_ids` and the stored `ResponseEvaluationRecord`.
3. Degradation honesty: if the gateway is unreachable at evaluation time, run the Rust-native rules, mark the evaluation with a recorded `gateway_unavailable` diagnostic, and cap the result at `REVIEW` (never silently `PASS` a response that skipped verifier-backed rules; never fail the capture).
4. Tests: (a) an envelope-level production-path test through the same dispatch as WP-04's transaction tests — seeded conflicting fixture → `CONFLICT` with persisted intervention IDs; clean fixture → `PASS` with empty list; (b) a gateway-down test asserting the `REVIEW` cap + diagnostic; (c) the existing full-fixture test rewritten to consume the injected engine rather than composing it externally, proving the seam is gone.
5. Update `BUILD_LOG.md` (append-only) with a WP-13 section and re-run the full workspace + extension suites as evidence. One commit: `feat(wp-13): wire governance into production evaluation`.

Explicitly unchanged: no new intervention rules, no severity/policy changes, no new endpoints. This is orchestration wiring only.

## Deferred items (tracked, not blocking WP-13)

- **Live ChatGPT selector session** — first post-merge activity, run jointly with the owner logged in (fixture-verified adapter + detach behavior is the accepted baseline until then).
- **Packaged-binary GUI drive-through** (weakest point 5) — nice-to-have; schedule with release hardening.
- **Signing/notarization, live Chrome-profile native-host install, SQLCipher/Keychain** — release work with the owner (needs credentials), per the original instruction's scope.
- **Validation batteries** — authored under the owner's pre-registration discipline (spec §18, Appendix C pattern); the harness scaffold is accepted as the instrument.

## Standing constraints (unchanged)

Read-only upstreams; preview purity non-negotiable; no G-gate verdicts; claim boundaries per `docs/spec/references_and_evidence.md`. The corrected `runtime_inspection_findings.md` is the current binding text.
