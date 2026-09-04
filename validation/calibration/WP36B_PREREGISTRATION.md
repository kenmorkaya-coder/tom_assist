# WP-36b dense 17D/T/S/P shadow calibration pre-registration

Status: **OWNER-AUTHORISED PRE-REGISTERED SHADOW CALIBRATION — NOT A GATE**

The owner directed Tom Assist to split incoming passages into multiple semantic
vectors, build a complete non-zero 17D load, preserve causal orientation, use
the non-Rust 10K 8D/17D Python tree, and test the construction before production
activation. This instrument fixes the first local deterministic implementation
and its hold-out observations. It does not change the authoritative compiler or
preview/commit path.

## Frozen construction

- The exact anchor sentences and arithmetic are in
  `wp36b_anchor_source.json`. The pinned local MiniLM revision embeds them once.
  The resulting vectors are a compact, hash-bound product artifact; no model is
  loaded in the gateway process.
- Every source chunk is compared with every channel's positive prototypes and
  the strongest prototype from the other channels. Absolute resonance is
  `exp(-6 * (1 - positive_cosine))`. Contrast specificity is
  `sigmoid((positive_cosine - strongest_other_cosine) / 0.08)`. Their product is
  the semantic measurement. It is mathematically strictly positive for the
  finite cosine range; no epsilon, floor, prior or replacement value is added.
- Each channel takes the maximum semantic measurement across the existing
  bounded overlapping MiniLM chunks. Existing quote/history evidence combines
  by probabilistic OR, preserving rather than replacing the semantic measure.
- Frequency uses mean continuous history similarity; persistence uses a soft
  recent run; burstiness uses the absolute recent-versus-earlier similarity-rate
  change with its sign recorded; volatility uses previous-turn semantic/static
  change; novelty and recurrence use distinct minimum-distance and maximum-match
  observations; decay uses an actual rise in classification confidence. Missing
  history adds no invented history feature; the semantic measurement remains.
- T/S/P use a separate three-way prototype bank and independent evidence values.
  They are supplied separately to the pinned application rather than inferred
  only from the q17 proxy.
- Direction and causality remain in the validated directed-graph fingerprint and
  the shadow digest. A scalar channel magnitude is not allowed to invent entity
  endpoints or relation direction.

## Frozen observations

The source cases are fixed in `wp36b_cases.json` before the hold-out run:

1. Seventeen named channel cases. Report raw semantic rank, combined rank,
   positive/contrast cosines, semantic value, evidence feature and final value.
2. Three independent driver cases. Report raw and evidence-combined T/S/P values
   and the dominant driver.
3. Two paraphrase pairs. Report whether both members preserve the declared
   family winner and their 17D cosine/L1 distance.
4. One forward/reversal pair. Require different graph fingerprints and different
   final shadow digests; report vector distance without asserting that magnitudes
   encode endpoints.
5. One long-tail passage. Require multiple chunks, full source coverage, and a
   winning support span that includes the final load-bearing text.
6. For every observation, require exactly 17 finite values in `(0,1]`, three
   finite drivers in `(0,1]`, exact replay validation, and complete semantic
   provenance.
7. Apply one held-out dense load plus its independent T/S/P tuple to a disposable
   clone of the pinned Python `TreeGrowthEngine`. Require the seed lineage to be
   `msr_8d_native_10k`, the pre-step branch count to be 10,000, q17/8D/driver
   shapes to be 17/8/3, the tick to advance exactly once, the routing basis sent
   to the engine to equal the pinned plan, and the untouched seed runtime bytes
   to remain identical.

## Interpretation and stop rule

This is a calibration, not a G-gate. The report must expose misranked channels,
weak margins and T/S/P confusion rather than tune or edit expectations after the
run. Any formula, anchor, case or expectation change requires a retained new
pre-registration version. Failure keeps the dense path shadow-only. No OAuth,
Gemma/GPT generation, network request, Feeling Wheel, live project, production
commit, preview mutation or frozen-pilot reinterpretation is authorised.

## Compact-artifact rule

Only the anchor vectors and compact JSON/Markdown observations may be committed.
No model weights, 384D per-case embeddings, tree snapshots, databases, Rust
builds or temporary caches are retained. Test output must be placed outside the
repository or removed after evidence is recorded.
