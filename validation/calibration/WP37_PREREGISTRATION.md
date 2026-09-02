# WP-37 evidence-addressed shadow retrieval pre-registration

Status: **FROZEN BEFORE RUN — LABEL-FREE SHADOW DIAGNOSTIC — NOT A GATE**

`owner_frozen: true`

This document freezes the WP-37 corpus and diagnostics before any WP-37 run.
It evaluates neither relevance nor quality. It must not be used to call either
ranking better, and it makes no G-gate claim.

## Frozen mechanism

The shipping `legacy` result remains the control. In `shadow` mode only, the
comparison arm uses:

1. the query's evidence-compiled 17-channel signature as a read-only address,
   projected by the pinned `project_load_signature_to_routing_basis` function;
2. the same projection of each anchor's retained frozen structural commit at
   query time, with the anchor's stored `leaf_vec` retained as the explicit
   fallback when no such commit exists; and
3. `rank_structural_history` as the semantic-channel rank, followed by an
   explicitly separate unscored tail. Dense and hashed scalar values are never
   compared or sorted together.

The sparse evidence signature is an address only. It must not reach load
application, `engine.step`, nourishment, wind, kappa, or any other force path.
The WP-35 authoritative rule requiring all 17 channels to be strictly positive
remains unchanged.

## Frozen corpus

The exact corpus is `validation/calibration/wp37_shadow_corpus.json`, version
`tom-assist-wp37-shadow-corpus/1.0`. It contains three legacy committed turns,
eight shadow committed turns with retained structural evidence, and eight
queries. The runner uses the pinned 10K seed, the fixture structural candidate
provider, and the already-pinned local MiniLM snapshot for deterministic dense
profiles. It performs no provider generation and no live call.

The texts and structural fixture declarations are inputs, not relevance labels.
No expected anchor, expected ranking, preferred arm, or relevance judgement is
registered. The WP-25/27 pilot corpus is excluded because it has no usable RGM
anchor inventory for this question.

## Frozen observations and formulae

For each query, emit both complete side-by-side traces and the following
label-free observations:

- cohort change: exact legacy/evidence branch-ID lists, overlap count, symmetric
  difference count, Jaccard similarity, and whether the lists differ;
- top-anchor change: the two top IDs (or null) and equality only;
- full fused-rank divergence: for every ID in the union, current and proposed
  1-based ranks and absolute delta; an absent ID receives `union_size + 1`;
- evidence coverage: counts and sorted IDs for anchors with retained structural
  evidence and anchors using their stored-vector fallback;
- hash collision rate: group distinct anchors by the exact 256-value hashed-bag
  vector already stored by the RGM; collision participants divided by total
  anchors, with zero for an empty inventory; and
- dense-versus-hash rank correlation: deterministic ranks are formed by
  `(-score, record_id)` over dense-scored anchors common to both channels, then
  ordinary Pearson correlation of those integer rank positions. Report null
  when fewer than two common records or either rank has zero variance.

Across the eight queries, report counts and distributions for cohort symmetric
difference, top change, per-anchor absolute fused-rank delta, evidence coverage,
collision rate, and rank correlation. Distribution summaries are count, minimum,
median, p90 (nearest-rank), maximum and arithmetic mean; empty inputs are null.

## Frozen protections

- Run each query twice in one process and once after a gateway restart; all
  comparison objects must be byte-identical for identical committed state.
- One query is repeated 100 times for the purity proof. Before/after engine
  bytes, RGM bytes, tick, retained-commit count, library schema and stored
  `leaf_vec` bytes must be identical.
- Returned `activated_branch_ids`, `ranked_anchors`, `candidate_trace`,
  `branch_trace`, packet-facing limits and checkpoint digest must equal the
  pre-change control path. Only the additive shadow comparison may differ.
- A zero-bearing shadow address must complete without state mutation. The same
  zero-bearing load must still fail authoritative preview and authoritative
  direct commit with the existing WP-35 message, before `LoadSignature` and
  before the tree.
- No preview path may call `rgm.read_memory`, `ToMClient.process`, or
  `engine.step`. No write-path, schema, stored vector, fusion weight, RRF
  constant, cohort size, seed, golden, or frozen prior artifact may change.

## External-label harness boundary

The reusable harness accepts a ranking file and a separately supplied external
relevance-label file, and emits precision at k, reciprocal rank/mean reciprocal
rank, and per-query arm deltas. WP-37 supplies no corpus relevance labels and
runs no corpus relevance score. A tiny separate fixture marked
`PLUMBING-ONLY-SYNTHETIC-NOT-EVIDENCE` may exercise input validation and metric
arithmetic in unit tests; its output is not a result and must not enter the
diagnostic report.

## Stop rule

Stop and report if any packet-facing value changes, any purity or WP-35
protection fails, a required pinned pure function is unavailable, an anchor
without evidence would require an invented vector, or a real relevance label is
needed. Otherwise report observations only and stop for owner audit. No G-gate
verdict.
