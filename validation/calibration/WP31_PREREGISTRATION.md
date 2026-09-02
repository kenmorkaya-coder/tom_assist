# WP-31 local multi-vector calibration pre-registration

Status: **PRE-REGISTERED LOCAL CALIBRATION — NOT A GATE**

This instrument evaluates the inactive WP-30b evidence-backed path before any
production-model or policy freeze. It makes no G-gate or product-efficacy claim.
It uses no OAuth provider, owner quota, network request, Feeling Wheel, preview
mutation, golden adjustment or frozen-pilot reinterpretation.

## Fixed run inputs

- 52 cases from `wp31_cases.py`, in source order.
- Families: 10 causal-direction, 12 orientation, 8 structural-signal, 6
  multi-relation, 6 long-position/overlap, and 10 paraphrases forming 5 pairs.
- One local Gemma candidate attempt per case window. No retry, repair generation,
  best-of selection or manual answer editing.
- MiniLM and Gemma revisions are supplied as absolute local paths and recorded by
  revision in the run manifest. This is a run pin, not the unresolved production
  packaging/licensing freeze.
- The deterministic WP-30b validator/compiler is authoritative. It may bind
  envelope metadata, normalize local IDs, and repair only uniquely located exact
  quotes. It may never add a semantic fact or relationship.

## Pre-registered measurements

1. Exact expected relation recall by channel/kind/direction/negation/modality.
2. Unexpected-relation count and reversed-endpoint count.
3. Expected structural-signal recall.
4. Exact evidence binding and successful deterministic analysis replay.
5. Chunk count, full-source coverage, overlap and tail/middle relation survival.
6. Presence, finiteness and range of all 17 load channels; non-zero patterns are
   reported, not post-hoc declared correct.
7. Paraphrase-pair 17D L1 distance, directed-graph equality, MiniLM multi-vector
   similarity and nearest-neighbour rank among all 52 cases.
8. Per-case wall time and parser-error taxonomy.

There is deliberately no pass threshold in this calibration run. Results may
support a later owner decision about model freeze, prompt revision and compiler
scaling, but the case expectations and raw observations remain unchanged. Any
subsequent tuned run requires a new version and retains this result.

## Compact-artifact rule

No 384D vectors, model weights, runtime trees, databases, checkpoints, prompts,
provider responses or temporary model caches are written into the repository.
Committed evidence is limited to compact JSONL observations, a summary, a
manifest and a Markdown report. The runner refuses an existing output directory
and records each artifact's byte size and SHA-256.
