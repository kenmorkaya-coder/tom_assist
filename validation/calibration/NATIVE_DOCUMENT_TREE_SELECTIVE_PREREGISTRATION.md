# Native document Tree selective retrieval diagnostic

Status: **FROZEN FOR LOCAL DIAGNOSTIC — NO PROVIDER CALLS**

Frozen on: 2026-09-08 Australia/Sydney

This instrument tests one narrow question: whether the product's real cached
MiniLM address path and its pinned Python 10K Tree reader selectively rank a
predeclared relevant passage above unrelated passages at small fixed depths.
It is diagnostic evidence, not a product gate and not a claim about the SCAW
deed.

## Frozen inputs and outcomes

The exact fixture is
`validation/calibration/document_tree_native_selective_fixture.json`.
Its SHA-256 is recorded below before the first execution of the runner.

- fixture SHA-256: `0d42b6bc7b32710db90e1b2c9724557fa815b6477fc67c0c57666f54659226fd`
- fixed depths: 1, 3, 5
- query families: prestart safety, prestart insurance, water discharge,
  utility isolation, traffic closure
- observations: one direct question and one paraphrase per family
- relevant passage IDs: exactly the `relevant_passage_ids` arrays frozen in
  the fixture
- distractors: every other frozen passage

No passage, query, label, depth, or comparison rule may change after the
fixture hash is inserted. A later instrument must receive a new version.

## Measurements

For every observation, report the predeclared relevant passage's rank and
recall at each fixed depth for these separate spaces:

1. local MiniLM passage-vector cosine (diagnostic reference only);
2. cosine over the compiled positive 17D load;
3. cosine over the pinned routing projection's 8D vector;
4. pinned `rank_by_branch_resonance` native receipt rank.

Also report score spread in each space, the query's selected branch IDs and
scores, branch-region change across queries, exact restart stability, and
source-byte fidelity. A score spread greater than `1e-12` is merely numeric
variation; it is not relevance evidence.

## Non-successes

The following never count as native selective retrieval success:

- scanning or admitting the full corpus;
- clause/reference expansion;
- lexical, hybrid, or reranked packet order;
- the relevant item merely appearing somewhere in a 25-item packet;
- a nonzero score spread without the predeclared item appearing at the fixed
  depth.

The runner must not change product defaults, write to an upstream checkout,
call a provider, download a model, invoke Gemma, or drive the experience Tree.
Each diagnostic project must receive its own copy of the canonical Python
10K 8D/17D seed and use the project-local document Tree only.
