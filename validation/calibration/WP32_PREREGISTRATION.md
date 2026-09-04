# WP-32 local parser calibration v2 pre-registration

Status: **PRE-REGISTERED LOCAL CALIBRATION — NOT A GATE**

This version evaluates the corrected local Gemma parser boundary and the existing
deterministic multi-vector/17-channel compiler. It does not activate the pathway,
freeze a production model, use a provider, or make a G-gate claim. WP-31 and all
earlier frozen pilot artifacts remain unchanged.

## Fixed corpus

- Exactly 80 cases, in source order.
- The first 52 cases are byte-for-field retained from WP-31 before v2-only
  bookkeeping fields are added.
- 28 new cases: 8 parser-boundary cases, 8 explicit signal cases, 4 added
  multi-relation cases and 8 committed-history/compiler cases.
- Final families: 10 causal-direction, 12 orientation, 16 signal, 10
  multi-relation, 6 long-position, 10 paraphrase, 8 parser-boundary and 8 history.
- History turns are parsed in order, compiled through `build_analysis`, validated
  by exact replay, converted to the existing committed structural-record shape,
  and then supplied to the query analysis. No history value is inserted directly.

## Fixed execution

- MiniLM revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- Gemma revision `0d77464eeb233a2da68ebf9d7dc4edaac7db956d`.
- One local Gemma call for every visited semantic window. No retry, best-of,
  repair generation, prompt adjustment, manual answer edit or provider fallback.
- Exact passage attempts, planned windows, attempted Gemma calls, successful
  calls, failed-window index, native-versus-syntax-fallback parsing and harmless
  extra-field projection are recorded for every attempted passage.
- Syntax fallback may repair only Gemma-4 container syntax. Product normalization
  may drop only non-schema presentation fields and bind evidence to exact source
  text already supplied by the model or its source-present entity label. It may
  never add an entity, endpoint, relationship, direction, modality, negation,
  signal, confidence or load value. Missing semantic fields and ambiguous ties
  fail closed.
- Provider/OAuth calls and owner quota use are fixed at zero. Feeling Wheel use is
  forbidden and fixed off. Preview paths are not called.

## Fixed scoring

Relation matching retains WP-31's channel, vocabulary, direction, negation,
modality and entity-term rules. A v2 exact case additionally requires zero
unexpected relations unless the case explicitly permits otherwise (none do),
and every pre-registered history bound must hold. Parser errors score all
expected relations/signals for that case as missed in end-to-end rates.

Before seeing v2 outputs, the following engineering-readiness criteria are fixed:

| Criterion | Required |
|---|---:|
| Strict observation rate | >= 0.90 |
| Minimum observation rate in every family | >= 0.75 |
| Expected relation recall across all attempts | >= 0.90 |
| Reversed expected relations | 0 |
| Unexpected relation rate among emitted relations | <= 0.05 |
| Expected signal recall across all attempts | >= 0.80 |
| Exact multi-relation cases | >= 0.80 |
| History cases satisfying all bounds | >= 0.875 |
| Valid 17-channel shapes among strict observations | 1.00 |

Meeting every criterion means only `ready_for_owner_freeze:true` for this local
engineering instrument. It is not automatic activation, efficacy evidence, a
production checkpoint/license decision or a G-gate verdict. Failure of any
criterion leaves the default path unchanged and requires a new retained version
for any further correction.

## Compact evidence and stop policy

The output directory must not already exist. Repository evidence is limited to
compact JSONL observations/pair metrics, a JSON summary/manifest and a Markdown
report. It contains no 384D vectors, model weights, generated raw text, prompts,
runtime databases, trees or checkpoints. A missing/malformed accounting receipt,
model revision mismatch, invalid candidate, invalid history replay or timeout
fails the affected case closed; there is no resend. Temporary model caches,
test basetemps and Rust build products are removed after verification.
