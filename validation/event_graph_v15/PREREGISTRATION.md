# V15 fresh held-out extraction after v14 selection

Freeze before any v15 model generation. Selected adapter: v14 epoch 1, cumulative
4,380 steps, SHA-256
c6a4708d9ceca6dab5d275ea0bff5ac172e392d085a4fda6b0d875e51d95a994.
The selected checkpoint meets the expanded development thresholds: 155/156 exact,
156/156 valid, original 132/132 retained. V12 remains RED and is already exposed;
neither its examples nor results are recast as fresh evidence.

Inventory: 132 new authored source records in 44 canonical/paraphrase/contrast
groups and 20 semantic families. All surface templates are separately written in
wording.py, with new qualified names, dates, document identifiers and most values.
Zero remains a deliberate boundary. Sources must have zero exact overlap with
all prior versioned train, development and held-out inventories. No training or
prompt/schema/parser change is permitted during this test.

Semantic graph construction inherits the earlier authored case definitions.
New text is manually authored to express those meanings, with source-bound evidence
and exact entity mentions validated before freeze. This is new wording with shared
semantic templates, not an independent naturalistic project-document benchmark.
A pass is evidence only for this bounded inventory. All triples must preserve
canonical/paraphrase semantics and alter contrast semantics; all gold labels must
round-trip through the unchanged span representation. Preflight uses the pinned
tokenizer and native prefix, with maximum gold sequence length 4096.

One deterministic local inference pass: seed 7, temperature 0, maximum 4096 output
tokens. Save all raw outputs, generated token IDs, finish reasons and parse errors.
No retries, dropped examples, edited outputs or post-hoc threshold changes.
Every record counts. Require jointly: 100% valid, at least 95% exact overall,
at least 90% exact in every family, zero invented authority, at least 95%
paraphrase equality and 100% contrast distinction. The inherited scorer canonicalizes
IDs/evidence and unit equivalents; evidence must be valid source spans, but exact
gold evidence-span equality is not an independent scoring requirement. Entity names,
action/role/condition binding and event ordering remain part of exactness.

Read and recompute the entire final aggregate before declaring GREEN or RED.
Preserve the original report and all artifacts. This run performs extraction only:
no training, matrix or Tree test starts automatically. Failure blocks downstream
gates; success must be verified before any separately executed matrix discrimination.
