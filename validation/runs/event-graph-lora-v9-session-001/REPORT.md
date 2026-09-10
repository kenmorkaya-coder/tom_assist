# V9 lower-rate continuation — verified development result

The bounded 480-update continuation completed at cumulative step 1440 and is
selected under the frozen rule. Exact accuracy increased by two records (1.5
percentage points), and all 132 outputs passed graph validation.

| Metric | Baseline, 960 steps | V9, 1440 steps |
|---|---:|---:|
| Exact / 132 | 121 (91.7%) | 123 (93.2%) |
| Valid / 132 | 130 (98.5%) | 132 (100%) |
| Invented authority | 0 | 0 |
| Paraphrase equality / 44 | 41 | 43 |
| Contrast distinction / 44 | 43 | 44 |

The selected adapter is `.tmp/event-graph-lora-v9-session-001/epoch-1/adapter`.
The baseline and all earlier adapters remain intact. No further training started.

Improvement is uneven: unless exact results increased from 3/6 to 5/6 and
multi-quantity from 2/6 to 5/6, while paragraph exact results fell from 6/6 to 3/6.
Direction remains 4/6 and approval 4/6. The nine remaining errors are semantically
incorrect despite valid graph structure. Development thresholds are not all met:
93.2% exact is below 95%, and several families remain below their required accuracy.
No fresh held-out, matrix discrimination or Tree gate was run.

Verification rehashed frozen inputs and adapters, reparsed all 264 saved outputs
(including the reused baseline), recomputed all metrics and selection, and checked
saved token IDs and finish reasons. RESULT.json records full reports and hashes.
This is development-only evidence, not a generalisation or downstream pass.
