# WP-36c history separation and evidence-bound T/S/P pre-registration

Status: **OWNER-AUTHORISED PRE-REGISTERED SHADOW CORRECTION — NOT A GATE**

WP-36b is retained unchanged. Its frozen run showed that dense multi-vector q17
and separate T/S/P can reach the pinned Python 10K tree, but it also exposed
three correction requirements: global channel rank is the wrong test for related
history statistics; T/S/P direct evidence was supplied manually by fixtures;
and semantic contradiction/inference require structural corroboration.

This package remains shadow-only. It does not alter the production compiler,
preview, commit path, frozen WP-36b artifacts, anchor bank or pinned runtime.

## Fixed corrections

1. **History dimensions are tested by controlled contrasts, not global rank.**
   Frequency remains the mean continuous similarity and recurrence remains the
   maximum. A many-moderate history must have greater frequency than a one-hit
   history; the one-hit history must have greater recurrence. Persistence remains
   the soft product-weighted recent run and must change when the same multiset is
   reordered. Burstiness remains the absolute recent/earlier mean change, but its
   signed change is retained; rising and falling cases must have opposite signs
   and equal magnitudes. A steady history must be less bursty than either.
2. **Novelty is no longer `1 - recurrence`.** When admitted history passage
   vectors are available, it is distance from their normalized centroid while
   recurrence remains best individual match. The two must respond differently
   in the frozen centroid case. Missing history vectors add no synthetic feature.
3. **Direct T/S/P evidence is compiled from the validated candidate.** Threat
   accepts contradiction/rejection spans, negative/opposing orientations and
   non-negated `prevents` relations. Sustenance accepts completion/memory spans
   and positive `supports`/`contains`/`owns` orientations. Procreation accepts
   future/inference spans and non-negated inferred/tentative/hypothetical causal
   relations. The value is the maximum cited confidence; every non-zero direct
   value retains all qualifying exact quote spans and paths. Callers cannot pass
   a numeric `driver_evidence` override.
4. **Contradiction and inference carry a structural-corroboration record.** A
   positive semantic measurement remains part of dense q17, but the channel is
   not structurally corroborated unless the current replayable structural load
   is positive and its canonical channel record has quoted support. This is
   telemetry for a future authority decision; WP-36c grants no authority.
5. The existing anchor prototypes, no-floor positive semantic formula,
   per-channel max across overlapping chunks, directed graph fingerprint and
   exact replay digest remain unchanged. Formula/analysis version advances only
   because the history and driver records change.

## Frozen observations

The exact cases and expected relations are in `wp36c_cases.json`:

- four paired history experiments covering mean/max separation, order-sensitive
  persistence, signed burst direction and centroid novelty;
- three single-driver candidates, one mixed candidate and one no-direct-evidence
  control, all validated against the existing candidate schema;
- corroborated contradiction, corroborated inference and two semantic-only
  controls;
- one directed causal reversal and one load-bearing tail case;
- one disposable clone application to the pinned Python
  `msr_8d_native_10k` seed using T/S/P compiled from candidate quotes.

Every observation must contain exactly 17 finite q17 values and three finite
drivers in `(0,1]`, replay exactly, and retain complete winning semantic support.
Every non-zero direct T/S/P evidence value must have at least one exact source
span. No global-rank success criterion applies to frequency, persistence,
burstiness or recurrence.

The tree observation requires a Python `TreeGrowthEngine`, 10,000 seed branches,
one tick, shapes 17/8/3, direct T/S/P equality between the compiler and pinned
plan inputs, and byte-identical untouched seed runtime state. The already-frozen
double-normalization exact comparison remains reported separately and is not
silently converted into a passing assertion.

## Stop rule and compact evidence

Any failed frozen relation, missing quote, override bypass, replay mismatch,
zero/non-finite load, unexpected tree lineage or production import keeps the
path shadow-only. Formula or case changes require a retained new version.

No provider generation, OAuth call, network request, Feeling Wheel, live project,
Rust mechanics path, production preview/commit, golden edit or G-gate verdict is
authorised. Only compact JSON/Markdown results may be retained; model weights,
case vectors, tree snapshots, databases and temporary test directories are not
committed.
