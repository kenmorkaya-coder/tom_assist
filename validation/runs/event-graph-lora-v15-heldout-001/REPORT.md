# V15 fresh held-out extraction — verified RED

The complete frozen aggregate has been read and independently recomputed from all
132 saved raw outputs. The unchanged extraction gate is RED: overall requirements
pass, but three families fall below the required 90% exactness.

| Metric | Result | Requirement |
|---|---:|---:|
| Exact |127/132 (96.2%)|At least 95%|
| Valid |132/132 (100%)|100%|
| Invented authority |0|0|
| Paraphrase equality |42/44 (95.5%)|At least 95%|
| Contrast distinction |44/44 (100%)|100%|
| Polarity exact |5/6 (83.3%)|At least 90%|
| Direction exact |5/6 (83.3%)|At least 90%|
| Paragraph exact |4/6 (66.7%)|At least 90%|
| Comparison bounds exact |17/18 (94.4%)|At least 90%|

Other families are exact on all examples. There are no parser errors. Five semantic
failures remain: one prohibition becomes an unnegated action with an exception
rather than its intended trigger; one causal target span truncates the entity;
two paragraphs include the verb “measuring” in the monitor entity; one comparison
case includes “measures” in that entity. The comparison-bounds family still passes.
All failures count; no labels, outputs or thresholds were changed after generation.

Tested checkpoint: v14 epoch 1, cumulative 4380 steps; adapter SHA-256
`c6a4708d9ceca6dab5d275ea0bff5ac172e392d085a4fda6b0d875e51d95a994`.
This new inventory changes surfaces, names and most values but shares authored
semantic templates. It is not naturalistic project-document validation. V12 remains
RED; percentages across these different inventories do not measure a controlled
improvement or regression between checkpoints.

No new training, matrix discrimination or Tree test was run. Matrix/Tree remain
NOT_RUN and blocked by this extraction result. V15 is now exposed; subsequent
held-out claims would require another independently frozen inventory.

Verification rehashed frozen source/model lineage, adapter and predictions,
reparsed all 132 raw outputs, recomputed all family and aggregate metrics, and
checked token IDs and finish reasons. RESULT.json records full reports and SHA-256
provenance. No model generation was repeated during verification.
