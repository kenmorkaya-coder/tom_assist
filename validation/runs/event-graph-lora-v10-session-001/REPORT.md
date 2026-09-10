# V10 augmented continuation — verified development result

The full 1200-update pass completed at cumulative step 2640. The frozen selection
rule selects the new adapter over v9: seven additional exact answers, an increase
of 5.3 percentage points. Training is complete; no further cycle started.

| Metric | V9 baseline, 1440 steps | V10, 2640 steps |
|---|---:|---:|
| Exact / 132 | 123 (93.2%) | 130 (98.5%) |
| Valid / 132 | 132 (100%) | 132 (100%) |
| Invented authority | 0 | 0 |
| Paraphrase equality / 44 | 43 | 42 |
| Contrast distinction / 44 | 44 | 44 |

Selected adapter: `.tmp/event-graph-lora-v10-session-001/epoch-1/adapter`.
All prior checkpoints remain intact. The development set and parser are unchanged;
training added 240 authored examples informed by previous development failures.
These results therefore remain tuning evidence, not fresh generalisation evidence.

Unless, direction and multi-quantity families now score 6/6 exact. Paragraph
improves from 3/6 to 5/6 and approval from 4/6 to 5/6. Other families remain perfect.
The two remaining failures (v8-dev-22-1 and v8-dev-25-1) select “Continuation of” as
part of the works entity, affecting two event object roles in each graph. Both are
paraphrase variants. Paraphrase equality consequently falls from 43/44 to 42/44,
while still exceeding the 95% aggregate paraphrase threshold.

Development thresholds are NOT all met: paragraph and approval each score 83.3%,
below the predeclared 90% per-family requirement. No threshold was relaxed. No
fresh held-out, matrix discrimination or Tree gate ran; none is claimed passed.

Verification rehashed frozen inputs and both adapters, reparsed all 264 saved raw
outputs (including reused baseline), recomputed all development metrics and
selection, and checked token IDs and finish reasons. Full reports and provenance
hashes are recorded in RESULT.json. No new generation was needed for verification.
