# Typed matrix compiler v1: frozen-before-score mechanism

This is an offline compiler experiment, not a product, extraction-model, Tree,
memory or retrieval result. No existing compiler or upstream file is changed.

## Mechanism selected before any repaired score

The new compiler consumes quote-bound events. A bounded, deterministic adapter
extracts symbolic fields from those quotes. It does not read category names,
expected labels, version roles or paraphrase memberships from the scorer.
The adapter normalizes decimal/spelled quantities and an explicit unit table
using Decimal arithmetic; comparators retain strict/inclusive identity. Exact
symbols are evidence-bound with field-local spans and linked to their event.
Unsupported quantities, multiple quantity scopes and ambiguous conditions fail
closed. This deliberately does not claim arbitrary English interpretation.

Explicit condition evidence takes precedence over ambient context. For legacy
events lacking it, recognize bounded conditional introducers and bind their
literal span. Otherwise use only an explicit leading During/Throughout ambient
span. Never substitute the complete relation sentence. Missing context outside
this grammar fails closed. The original null-context battery is not edited.

Symbolic spans are replaced by generic type placeholders before semantic
embedding. MiniLM thus represents the remaining open-class wording, not exact
values. Canonical symbols remain in an inspectable evidence record.

Each canonical field-symbol sequence gets a deterministic 32D signed code from
SHA-256 blocks, using the fixed domain `tom-assist-typed-field/1`. This is an
identity code, NOT a numerical-order embedding, semantic hash or proof of
collision-free encoding. Equivalent normalized values get the same code. A
changed tuple generally gets a different code; observed collisions must be
reported. Numerical comparisons remain explicit typed operations, not claims
that cosine similarity executes arithmetic.

For a field with symbols:

    field32 = normalize(existing_project384to32(MiniLM(masked_text)) + symbol32)

Both terms have unit norm. The 1:1 combination is fixed before scoring. Fields
without symbols retain the existing semantic projection. Relation modality and
polarity are explicit typed symbols. The existing projection seed 539362568
and outer-product weights 1 / 0.5 / 0.25 are unchanged. All original event
views and their summed normalized aggregate are retained. No centering, extra
matrix, appended dimensions or downstream reranking is introduced.

An ablation drops only the deterministic symbol term; it keeps the same masked
semantic text and exact context binding. It measures whether symbols actually
affect matrix discrimination rather than existing solely as metadata.

## Experiment and stop rule

Before embeddings/scoring, hash code, this design, original immutable inputs,
new holdout inputs, and scorer. Original 24 sets and fresh 24 sets are reported
separately. Retain rank 3, condition <=10, correct paraphrase nearest, original
distance-margin requirements, substitution conditioning, orientation and
integrity gates. Unsupported items remain failures with fixed denominators.

Use only already installed local MiniLM. Do not run extraction models or access
providers. Save matrix/stage artifacts before scoring. Original baseline files
are read-only. No selecting alternative seeds, mixing weights or mechanisms
after observing results. A RED ends this version; report its causes rather than
changing the test. Temporal-authority work is conditional on two reviewed GREEN
outcomes and is not part of this compiler run.

Dates, identifiers, ranges and arbitrary Boolean scope are not silently coerced
into quantities. If not supported by v1, explicitly report them as limitations.
