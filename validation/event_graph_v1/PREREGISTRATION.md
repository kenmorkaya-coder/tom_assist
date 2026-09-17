# Gemma LoRA event graph v1 — bounded viability experiment

Owner-authorized architecture, 9 September 2026. Feature branch:
`codex/gemma-lora-typed-event-graph`. This is an isolated local experiment;
existing compiler versions, frozen results, production and Tree mechanics are untouched.

## Frozen sequence

Schema and runtime validator → authored train/dev/held-out inventories and
split audit → local Gemma LoRA → held-out extraction gate → held-out numerical
discrimination gate → independent review and original compiler regression →
only then separately instrumented temporal-authority testing. No downstream
result can waive an extraction failure. No production or G-gate claim follows.

`experiment.py freeze` hashes schema, prompt, compiler, generator, scorer,
training files, labeled splits and checkpoint files before any training. Files
are verified again before each stage. Output files are exclusive-create; failed
runs and held-out predictions must never be overwritten. Model revision is
`mlx-community/gemma-4-26b-a4b-it-4bit` snapshot
`0d77464eeb233a2da68ebf9d7dc4edaac7db956d`, using local MLX 0.31.1 / mlx-lm 0.31.2.
The base checkpoint and the archived runtime environment are read-only.

## Contract

The extractor outputs entity mentions, typed comparison predicates, Boolean
conditions, separate events, and explicit directed links. Actor, object, source,
target, recipient and authority are separate nullable roles. Approval of another
action uses a complement event, rather than losing the action being approved.
Possible approval events have hypothetical modality, never an invented occurrence.
Event-level and predicate-level negation have separate scopes. References resolve
within the supplied source; persistent cross-document project identity is a
separate dependency, not demonstrated by this version.

The model selects unique verbatim quotes. Deterministic binding supplies character
offsets and rejects ambiguous/absent quotes. This is syntax/evidence checking, not
a claim that source overlap proves the inferred meaning. The extraction gate
compares the complete event/link semantics to authored labels. No model-generated
training labels, silent repair, retry, whole-paragraph semantic fallback, or
source-text parsing in the numerical compiler is allowed.

The bounded vocabulary and units are explicit in `schema.json`. Unsupported
language is reported in `unresolved`, which blocks all loads for that source.
The schema can express more than the synthetic corpus tests; do not equate schema
coverage with learned coverage. Real project prose, independently authored hard
OOD documents, document-wide references, entity registries, time normalization,
open-vocabulary actions, and fully general exception logic remain unproven.

## Corpus and leakage controls

18 authored contrast families × 8 training groups × 3 variants = 432 training
examples; development and held-out each have 18 × 2 × 3 = 108 examples.
Each group has canonical wording, an equivalent paraphrase, and one critical
change. Family templates, entity prefixes and principal numeric inventories
are distinct by split. Fixed auxiliary quantities (2 m / 3 m), syntax vocabulary
and the task ontology are shared; this is not a claim of total token disjointness.
Groups never cross splits. Training-library directory contains train and valid
only; held-out labels are never supplied to the optimizer. Shared synthetic
construction remains a limitation: this pilot is not an independently authored
naturalistic OOD battery or a conclusive viability result.

Families: quantity, comparator, action polarity, notification recipient, explicit
authority, unless, Boolean conjunction/disjunction, causal reversal, before/after,
revision supersession, date identity, paragraph decomposition/reference sharing,
hypothetical approval exceptions, nested Boolean expressions, predicate negation,
conflicts, swapped thresholds and equivalent units.

## Fixed training and gates

One pilot: seed 7, 128 optimizer steps, batch 1, last eight transformer layers,
LoRA rank 8 on attention query/value projections, scale 16, learning rate 1e-4,
prompt loss masked, context limit 4096, gradient checkpointing enabled.
No truncation of labels is permitted. Development loss is telemetry; use the
final 128-step adapter, not a checkpoint picked after held-out scoring.
This is a bounded engineering pilot, not a guaranteed sufficient training budget.

Extraction thresholds, fixed in `experiment.py`: 100% structurally valid resolved
graphs, ≥95% exact semantic graphs, ≥90% exact in every family, zero invented
issuing authorities, 100% contrast distinction, ≥95% paraphrase agreement.
All 108 examples remain in denominators, including errors and omitted examples.
Unknown/duplicate prediction IDs invalidate scoring. Field exactness, family
results, raw generations, adapter hash and local generation counts are retained.
No online services, cloud generation, or remote dataset fetches.

After extraction GREEN only, numerical gate checks all graph loads: finite 32×32
signed matrices, deterministic replay, rank 3 and condition number ≤10, equivalent
paraphrases within 1e-8, and contrast distance margin ≥0.05. All groups must pass.
No alternate seed, weights or thresholds may be selected after a RED. Symbols-off
artifacts are retained for analysis. The prior compiler's unchanged regression
and independent review are still required before Tree testing; this new gate
is not a substitute for that regression.

## Matrix representation and limits

Each event and explicit link emits its own load, retaining source event order and
link endpoints. There is no paragraph-average matrix. Structured source roles,
target roles, action/modality/polarity and context are encoded as fixed signed
SHA-256 identity vectors under a versioned domain and seed 539362568. Exact
rational normalization equates supported units (including L/min). No model or
embedding is invoked by the compiler, and evidence wording/offsets are excluded
from numerical features.

For unit-normalized vectors s,t,r,c:
`normalize(s tᵀ + 0.5 r rᵀ + 0.25 c cᵀ)`.

This deliberately isolated candidate changes the field representation, not the
outer-product equation. Codes distinguish canonical structured identities; they
do not represent numeric ordering, execute Boolean logic, prove collision freedom,
or establish semantic-family geometry for previously unseen entities. Such
properties require separate evidence before downstream adoption.

A RED stops progression. A defect found in held-out evaluation may motivate a
new version and independently held-out corpus; never retrain against this test
and then reuse it as unseen evidence. Infrastructure failures may be repaired
in a separately identified run, preserving the original failure and manifest.
