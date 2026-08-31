# WP-25 owner freeze — `wp25-prereg-frozen/1`

Frozen 1 September 2026 (Australia/Sydney) under `ORCHESTRATOR_REVIEW_8.md`.
This overlay versions the authored WP-23 proposal without changing its case files,
answer files, or numeric margins. The binding criteria remain byte-for-byte in
`PREREGISTRATION.md` (SHA-256
`0321f8a55847ee9159dbf923ffd86f0dd5eb1e7d01c059e62ead48b97218bce6`).
The pre-freeze authoring manifest SHA-256 is
`0bffc6ed6136e47fb2e76607c27b00ac0ad12eaf8c022999370250f0ae3a8d0a`.

## Frozen owner decisions

1. Margins are frozen exactly as drafted. H1 is primary; H0 is null; H2 is
   partial; H3 is a new failure mode. The domain-cluster bootstrap uses 10,000
   resamples and seed 1729. No post-result key, threshold, seed, comparator or
   exclusion change is permitted; a correction requires a new pre-registration.
2. The pilot is exactly 33 paired cases × five arms = 165 logical generations.
   Within each family choose the first two long cases and first no-rot case by
   lexicographic `test_id`. Case order is lexicographic and arm order rotates by
   case index modulo five. The unselected 99 cases remain frozen and unrun.
3. No-rot injection uses the floor-only definition: active objectives, active
   hard constraints, and active rejected/completed guardrails are legitimate.
   `gratuitous_packet_injected` means one or more optional state/anchor items
   beyond that floor. Missing telemetry is null, never success.
4. Each case/arm gets one initial capture only. There is no retry, best-of,
   repair, silent discard, or automatic resend of an unknown outcome. Stop rules
   in the source pre-registration bind. WP-22 provider self-report stays off.
5. This authorized pilot can resolve only its frozen pilot criteria and nulls.
   It cannot issue or imply a specification G-gate verdict.

## Frozen case IDs

```text
D23-ASSUMPTION-01
D23-ASSUMPTION-02
D23-ASSUMPTION-11
D23-COMPLETED_WORK-01
D23-COMPLETED_WORK-02
D23-COMPLETED_WORK-11
D23-CONCEPT-01
D23-CONCEPT-02
D23-CONCEPT-11
D23-CONSTRAINT-01
D23-CONSTRAINT-02
D23-CONSTRAINT-11
D23-DECISION-01
D23-DECISION-02
D23-DECISION-11
D23-EVIDENCE-01
D23-EVIDENCE-02
D23-EVIDENCE-11
D23-OBJECTIVE-01
D23-OBJECTIVE-02
D23-OBJECTIVE-11
D23-REJECTED_PATH-01
D23-REJECTED_PATH-02
D23-REJECTED_PATH-11
D23-SUPERSESSION-01
D23-SUPERSESSION-02
D23-SUPERSESSION-11
D23-UNRESOLVED_DEPENDENCY-01
D23-UNRESOLVED_DEPENDENCY-02
D23-UNRESOLVED_DEPENDENCY-11
D23-WORKSTREAM-01
D23-WORKSTREAM-02
D23-WORKSTREAM-11
```

The machine-readable manifest stores the canonical freeze payload and its SHA-256.
