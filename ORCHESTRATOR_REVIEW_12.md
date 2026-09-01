# ORCHESTRATOR REVIEW 12 — v3 stop accepted; pre-registration v3 approved; pilot v4 authorized

**Date:** 1 September 2026

**Pilot v3 stop: accepted as correct execution.** Five captures preserved; observation 6 unknown-outcome after the frozen 240s limit; zero resends; substrate telemetry proved the tree in the loop (744 five-dynamics commits, 288/288 assistant turns taught, checkpoints advancing) — the owner's telemetry rule, working. Frozen outcomes recorded honestly (H1 INVALID_INCOMPLETE). The run identity is permanent and closed.

**Design finding:** the v1/v2 stop rule conflates scientific-integrity events (retry-fishing, resuming — must remain fatal) with routine provider latency (one slow call in 165 — statistically near-certain). As frozen, a full run completes with probability <0.2 at even a 1% per-observation slow-call rate. Corrected by versioned pre-registration, never by bending a frozen rule mid-run.

**Owner decisions (1 Sep 2026): pre-registration v3 approved with exactly five changes; pilot v4 authorized at a fresh 165 generations.**

1. Per-observation `unknown_outcome` disposition: record, never resend that observation, continue with the next independent observation; affected cases excluded from paired analysis and reported.
2. Invalidity cap: >8 unknown outcomes (≈5%) permanently stops and invalidates the run.
3. Primary validity bound: H1 interpretable only with ≥30/33 cases complete across all five arms; otherwise INVALID_INCOMPLETE.
4. Observation timeout 600s; per-observation wall time recorded in telemetry (gap found in v3: durations were not captured).
5. All else byte-unchanged from frozen v2 (margins, selection, seed 1729, multiset oracle, self-report off, stop rules for integrity events).

Execution: Codex drafts v3 as a new version retaining v2's artifacts → orchestrator verifies the delta is exactly these five changes → freeze applies (owner_frozen:true, freeze SHA) → pilot v4 runs under fresh explicit live authorization (`TOM_ASSIST_WP29_V4_LIVE=1` or equivalent), substrate telemetry leading the report → full Appendix-C matrix, H-slots resolved as frozen → stop for audit. No G-gate verdicts.
