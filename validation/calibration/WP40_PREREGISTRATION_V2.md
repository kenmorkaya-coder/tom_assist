# WP-40 parser-glossary paired evaluation pre-registration v2

Status: **DRAFT — NOT FROZEN — NOT AUTHORISED FOR GENERATION**

`owner_frozen: false`

This draft retains the accepted WP-40 implementation and replaces only the
design of its void evaluation. The frozen v1 pre-registration and retained v1
evidence remain unchanged. Nothing in this document authorises Gemma, a cloud
provider, OAuth, network access, or quota use.

## Owner fields that must be completed before freeze

- Chosen corpus candidate ID: **________________**
- Exact corpus path / immutable artifact ID: **________________**
- Corpus provenance and permission statement: **________________**
- Passage count: **________________**
- Canonical corpus SHA-256: **________________**
- Frozen ordered passage-ID list SHA-256: **________________**
- Owner-authored label file path: **________________**
- Validated label file SHA-256: **________________**
- Derived glossary source and SHA-256: **________________**
- MiniLM revision: **________________**
- Gemma revision: **________________**
- Total planned chunks over all passages: **________________**
- Exact local-generation ceiling, twice the preceding value: **________________**
- Primary acceptance threshold(s): **________________**
- Safety/non-regression threshold(s): **________________**
- Owner freeze date and frozen Git SHA: **________________**

The owner chooses the corpus and supplies the labels. Codex does not fill any
of these fields, choose passages, or author project-prose labels.

## Proposed locked execution

After owner freeze and separate live authorisation, run each passage once with
the glossary off and once with it on, in the frozen passage order and fixed arm
order `glossary_off`, then `glossary_on`. Use one persistent local structure
worker and its one persistent Gemma child with deterministic zero-temperature
sampling.

Every planned chunk is attempted exactly once in each arm even if an earlier
chunk fails. There are no retries, resends, best-of choices, fallback models,
manual repairs or post-freeze prompt changes. Each chunk records its zero-based
chunk index, one-based attempt ordinal and success/failure outcome. A passage
is fail-closed if any of its chunks fails, even when other chunks succeed.

The exact budget is:

`maximum_local_gemma_generations = 2 * sum(planned_chunks_per_passage)`

The owner must freeze the numeric result after the selected corpus has been
tokenised in a zero-generation preflight. Every attempted chunk counts against
that ceiling. Cloud/provider generations, OAuth calls and network requests are
zero. Feeling Wheel use is forbidden and forced off. The Python 10K tree, RGM,
project runtime and every prior frozen artifact remain untouched.

The run stops before generation if any corpus, passage-order, source, label,
glossary, model or pre-registration digest differs; if the label validator
rejects any row; if the chunk plan differs from its frozen preflight; if the
output directory already exists; or if local configuration is incomplete. It
stops if the frozen generation ceiling would be exceeded.

## Proposed owner-labelled metrics

Labels use `tom-assist-parser-labels/1.0`. Each expected candidate is validated
against the exact source text before scoring. The two synthetic WP-41 rows are
plumbing only and are excluded from every corpus, denominator and report.

Normalize each accepted candidate into multisets without model-local IDs:

- entity atoms: label, kind and exact evidence span;
- orientation atoms: source and target entity label/kind, kind, polarity,
  modality, negation and exact relation-evidence span;
- causal atoms: cause and effect entity label/kind, kind, modality, negation
  and exact relation-evidence span;
- signal atoms: signal family and exact evidence span; and
- unknown-field atoms: the declared field name.

Confidence is reported separately and is not used to decide whether a typed
fact matches. For the union of all labelled passages, report multiset true
positives, false positives and false negatives and micro precision, recall and
F1 for each atom family and overall. Report exact-passage match rate, relation
direction reversals, unexpected-relation rate, expected relation recall,
expected signal recall, and passage fail-closed rate. A failed passage predicts
an empty atom multiset. A metric with no labelled positive and no prediction is
`not_applicable`, never silently scored as success.

Report each arm independently and the paired `glossary_on - glossary_off`
delta for every numeric labelled metric. Labels are never altered in response
to a parser output.

## Label-free diagnostics retained from v1

For each arm retain logical/observed/fail-closed parse counts; attempted and
successful local generations; entity count; entity-weighted mean exact span
length; orientation-plus-causal relation count; signal count; unknown-field
count and successful-parse rate; and wall time.

For each passage pair retain candidate-digest change, normalized-atom multiset
symmetric difference, directed-graph digest agreement when both candidates
exist, glossary-term presence in the immutable source, and `not_comparable`
when either passage fails closed. These remain difference diagnostics, not
correctness measures.

## Failure taxonomy reporting

Use `tom-assist-structure-failures/1.1`. Each failure record contains its
stable category, a detail bounded to 240 characters while preserving both ends,
zero-based chunk index and one-based attempt ordinal. Report every chunk
outcome, per-passage category counts, per-arm category counts and whole-run
category counts.

The explicit `unclassified` count must be printed prominently. A non-zero count
marks the taxonomy incomplete and prevents any accuracy or activation
interpretation, but does not cause retry or fallback. Fail-closed behaviour is
unchanged.

## Interpretation rule to freeze

No arm may be called more accurate, better or activation-ready unless all of
the following are true: the owner-selected corpus and complete owner labels
were frozen before generation; every protected digest and budget check passed;
`unclassified == 0`; the glossary-on arm meets the owner-filled primary
thresholds; and it meets every owner-filled safety/non-regression threshold.
Failure of any condition yields `insufficient_or_not_better_under_frozen_rule`.

The thresholds above are deliberately blank in this draft. They must be chosen
by the owner before freeze, not inferred after results. Product default remains
legacy/glossary-off regardless of the result. This is parser evaluation only;
it cannot establish whole-tree efficacy and makes no G-gate verdict.
