# Event graph extraction v3 — frozen repair experiment

V1 was formally evaluated after the coordination hold was withdrawn. Its original
manifest, source, adapter, predictions and aggregate remain unchanged. V2 is only
a separately versioned Markdown-fence transport repair; it has no held-out GREEN.
This v3 experiment is motivated by general defects, not fitting v1 held-out answers.

## Changes selected before v3 training or evaluation

- Explicit `{quote, occurrence}` evidence at the model boundary. The zero-based
  occurrence is selected by the model; code binds exactly that occurrence and
  rejects absent, invalid or unspecified positions. No guessing across repeats.
- Compact entity mention evidence and clause evidence where authored templates
  provide it; no model-generated labels or inference of labels from predictions.
- Typed-only normalization of redundant unary all/any wrappers and negated numeric
  comparison operators. Event negation, roles, dates, modality and logical scope
  are never repaired. V1's schema/validator/compiler remain unchanged.
- Domain-consistent role names: works as affected objects, crews as actors,
  superintendents as recipients when notified, explicitly named issuers as
  authorities. A new role-triple family changes issuer and recipient positions.
- All six numeric comparators, strict/inclusive bounds, negative and zero values.
- A fresh LoRA run from the same pinned base checkpoint: 512 steps, batch 1,
  last 16 layers, rank 16, query/value attention projections, scale 16, learning
  rate 1e-4, seed 7, masked prompt loss, gradient checkpointing, 4096-token cap.
  V1 weights are NOT resumed. 512 steps cover the complete 480-example training
  inventory once and start a second pass. The final adapter is selected in advance.
  Development loss is measured on 16 batches at each 128-step checkpoint; no
  checkpoint selection from held-out scores. Inputs exceeding the cap abort.

## Inventories and provenance

480 train / 132 development / 132 fresh held-out examples, in 20 contrast
families. Each group has canonical wording, a paraphrase and a semantic contrast.
The additional comparison family covers all six operators in development/test.
The semantic contrast definitions of v1 are reused, but v1 held-out sentences and
predictions are never training targets. Fresh test wording is explicitly authored
in this version's generator, with different entity names and principal values.
Auxiliary values and task ontology are shared. This remains a synthetic,
template-based pilot, not independently authored naturalistic hard OOD evidence.

The training-library directory contains only train and valid, never held-out.
The source-bound graph schema stays `tom-assist-event-graph/1`; `wire_schema.json`
specifies the v3 pre-binding occurrence protocol. Runtime checks additionally
validate references, cycles, evidence and supported dimensions.

`experiment.py freeze` records SHA-256 hashes of this specification, source code,
wire schema, all data splits, training examples, tests and local checkpoint files
before training. Each stage verifies the manifest. No frozen file or result may
be edited to turn a failure into a pass. Outputs use exclusive creation. V1
results may be examined as development evidence but never reclaimed as unseen.

## Gates and stop rules

Keep the prior declared extraction thresholds: 100% valid resolved graphs,
95% exact canonical graphs overall, at least 90% per family, zero invented
issuing authorities, 100% critical-contrast distinction, 95% paraphrase agreement.
With small family samples these thresholds can require every item in a family
correct; report denominators. Unary and numeric-negation equivalence are fixed
before v3 scoring, not a post-score rescue. Unsupported/omitted/invalid outputs
remain failures. No retries, partial-JSON closure, silent role remapping, date
remapping, or modality repair.

Only after extraction GREEN may this run invoke its numerical discrimination
instrument. It retains individual event/link loads, original weights, rank and
conditioning checks, and symbols-off artifacts. This graph compiler uses a
separate experimental SHA identity encoding; it inherits NO result from the
MiniLM+symbol or project-register compiler experiments. A numerical pass alone
would not authorize Tree integration: the relevant original regression and
independent review remain necessary. No production state, Tree, project registry
or source baseline is modified. A RED stops this version and is preserved.

No model, data or threshold changes after observing the v3 held-out outputs.
No cloud generation or network model/data fetches. Model artifacts remain local,
outside Git; source commits and pushes never interrupt or gate training.
