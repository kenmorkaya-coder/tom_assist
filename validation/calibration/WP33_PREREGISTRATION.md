# WP-33 local parser calibration v3 pre-registration

Status: **PRE-REGISTERED LOCAL CALIBRATION — NOT A GATE**

This version tests the parser-boundary corrections made after frozen WP-32. It
does not activate the parser, measure whole-tree reasoning efficacy, use a live
provider, or make a G-gate claim. WP-31, WP-32 and all earlier run artifacts
remain unchanged.

## Fixed corpus

- Exactly **94 cases**, in source order.
- The first 80 retain WP-32 text, relations, signals, chunk expectations and
  scoring fields. The sole declared amendment is HD-05's deterministic
  persistence bound: four matching suffix turns over the six-turn denominator
  is fixed at exactly `2/3`, replacing the known-wrong minimum of `1.0`.
- Fourteen additions are fixed before the run: 4 parser-boundary cases, 6
  multi-relation cases and 4 long-position/overlap cases.
- Final families: 10 causal-direction, 12 orientation, 16 signal, 16
  multi-relation, 10 long-position, 10 paraphrase, 12 parser-boundary and 8
  history cases.
- The additions stress coordinated lists, negated orientations, passive
  direction, mixed causal/non-causal relations, `requires` direction, multiple
  negated causal edges, combined signals, repeated names and relations near or
  across deterministic token-window overlaps.

## Fixed implementation boundary

- Gemma still proposes entities, endpoints, direction, relation vocabulary,
  modality, negation, signals, confidence and evidence. It never supplies a 17D
  load value.
- The deterministic fallback may quote container keys, restore Gemma string
  delimiters, normalize booleans/null, remove trailing commas, quote a bare
  identifier value without changing that value, accept Python-style quoted
  string syntax, and close only still-open list/object delimiters at the end of
  a tool call. Strict schema and evidence validation follows every repair.
- A missing evidence quote may be copied from source only when Gemma supplied
  valid non-empty start/end offsets. A wrong quote, invalid offset, absent fact
  or ambiguous evidence still fails closed.
- Across overlapping windows, two entities merge only when their normalized
  labels and kinds match and their evidence covers the same source occurrence
  of that label (or their overlapping evidence is punctuation-equivalent).
  Separate occurrences remain separate. Relation direction, vocabulary,
  modality and negation must still match before relation deduplication.
- The structural analysis/parser versions advance to 1.2. The numeric 17D
  compiler remains `tom-assist-evidence-load17/1.1`; its arithmetic is unchanged.

## Fixed execution

- MiniLM revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- Gemma revision `0d77464eeb233a2da68ebf9d7dc4edaac7db956d`.
- One local Gemma call for each visited semantic window, `max_tokens=3072`,
  deterministic sampling and source order.
- No retry, resend, best-of, repair generation, manual answer change, prompt
  adjustment after freeze, or provider fallback.
- Every passage attempt records planned, attempted and successful windows,
  failed-window index, parse mode, harmless-field projection and wall time.
- Provider/OAuth calls and owner quota use are exactly zero. Feeling Wheel use is
  forbidden and fixed off. No preview mutation surface is called.

## Fixed scoring

The WP-32 direction-sensitive matcher and thresholds are retained unchanged.
Parser errors count all expected relations/signals in that case as misses.

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

Meeting every criterion means only `ready_for_shadow_review:true`. Shadow-mode
activation remains a separate owner decision. It does not establish usefulness,
whole-tree reasoning, a production model freeze or a G-gate verdict.

## Evidence and cleanup

The output directory must not already exist. Permanent evidence is limited to
compact JSONL observations/pair metrics, JSON summary/manifest and a Markdown
report. It contains no raw generated prose, prompts, 384D vectors, model weights,
runtime trees, databases or credentials. Large model caches and disposable test
data are removed after verification.
