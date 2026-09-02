# WP-36c shadow correction pre-registration v2

Status: **OWNER-AUTHORISED PRE-REGISTERED SHADOW CORRECTION V2 — NOT A GATE**

V1 and its artifacts are retained. V1 satisfied its reported pairwise checks but
post-run tree telemetry exposed a contradiction with the already-frozen rule:
when a new history feature was unavailable, the combiner fell through to the old
sparse compiler value. On first turns that made novelty and decay exactly `1.0`,
even though v1 explicitly said missing history must add no synthetic feature.
V1 is therefore diagnostic-only and not a successful correction.

## Exact v2 delta

One implementation correction is authorised: for frequency, persistence,
burstiness, volatility, novelty, recurrence and decay, only the newly defined
history feature may combine with semantic resonance. If that feature is absent,
`combined_evidence` is null and the final value equals the strictly positive
semantic measurement. The old sparse compiler value is never a fallback for
these seven channels. `threat_amplitude` continues to use direct current-turn
structural evidence. Static channels are unchanged.

No anchor, semantic formula, history formula, T/S/P rule, corroboration rule,
case text, expected pairwise relation, graph rule or tree rule changes. V2 uses
the exact `wp36c_cases.json` corpus and adds these pre-registered assertions to
every observation whose source analysis has empty history and no classification
confidence change:

1. the seven named history channels have `combined_evidence: null`;
2. each final channel value equals its semantic value exactly;
3. none can become `1.0` through a legacy default;
4. the mixed candidate used for the 10K tree must still pass its candidate-bound
   T/S/P tuple to the pinned plan exactly.

All v1 constraints remain binding. Results go to a new v2 directory; v1 files
are not edited or reinterpreted. Zero provider generations, no Feeling Wheel,
no production wiring, no Rust mechanics and no G-gate verdict.
