# V10 source-span and condition-binding augmentation

Resume the verified v9 selected adapter at cumulative step 1440 (123/132 exact,
132/132 valid). Preserve old adapters. Same base, wire format, prompt, binder,
scorer, development records and thresholds. No runtime semantic repair.

## Diagnosis and authored training data

V9 has nine development errors: two causal span errors, three paragraph span
errors, two approval span errors, one cross-sentence monitor reference span error
and one exception-versus-condition error. These are wrong meanings in valid graphs.
Development-informed curriculum design means development remains a tuning set,
not an unbiased generalisation estimate. No claim of causal diagnosis is made.

Retain all 960 v8 training records and append 240 authored examples: 16 three-way
canonical/paraphrase/contrast groups in each of unless, direction, paragraph,
approval and multi-quantity families. New site/entity names and varied values are
used; no development or held-out row is copied into training. General patterns
include nominalized actions versus named participants, reversed causal clauses,
shared monitor references, multiple thresholds, approval complements, and if versus
unless. Labels are authored with the existing graph builder, never model predictions.
Full entity-name spans are explicit, and coreferences bind to the named entity.
All original examples remain to retain coverage of the other fifteen families.

Frozen training inventory: 1200 rows. Development: byte-identical 132-example
validation messages from v8, and unchanged gold rows through inherited provenance.
All training targets round-trip to the authored meaning; group equivalence/contrast,
role/reference invariants and source non-overlap are tested. Preflight checks all
1332 messages with the pinned tokenizer, native inference-prefix alignment, and
maximum sequence length 4096. No truncation allowed.

## Bounded schedule and selection

One full 1200-update pass at learning rate 0.00001, batch size 1, seed 97; optimizer
reset as in earlier sessions. Rank 16, last 16 layers, q/v LoRA remain unchanged.
This changes curriculum and update count and seed; it is not a single-variable
comparison. Checkpoint cumulative step 2640. No automatic additional cycle.

Reuse verified v9 predictions for baseline block 0; no baseline regeneration.
After the full pass generate all 132 development cases deterministically, keeping
raw strings, token IDs and finish reasons. Select baseline or new checkpoint by
exact count, valid count, fewer invented authorities, paraphrase equality, contrast
distinction, then earliest block. Retain baseline if continuation regresses.

No new held-out, matrix or Tree test in this session. No gate is inferred from
training loss. On completion verify aggregates and preserve both checkpoints;
a separate fresh held-out protocol is required before downstream testing.
