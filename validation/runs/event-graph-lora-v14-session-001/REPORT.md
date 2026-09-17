# V14 shorter continuation — verified development result

The 360-update continuation completed at cumulative step4380 and is selected by
the frozen rule. The malformed revision evidence is resolved; the paragraph action
label mismatch remains. All predeclared development thresholds now pass.

| Metric | V13 baseline,4020 steps | V14,4380 steps |
|---|---:|---:|
| Original exact /132 |132|132|
| Extension exact /24 |22|23|
| Combined exact /156 |154 (98.7%)|155 (99.4%)|
| Combined valid /156 |155 (99.4%)|156 (100%)|
| Invented authority |0|0|
| Paraphrase equality /52 |50|51|
| Contrast distinction /52 |52|52|

Paragraph exactness is17/18 (94.4%), above the90% per-family threshold. Every other
family is perfect. The remaining example v13-dev-paragraph-1-1 uses action `use`
instead of `discharge` for the final flow requirement. It still counts as incorrect.
No threshold was relaxed and no original case regressed.

Selected adapter: `.tmp/event-graph-lora-v14-session-001/epoch-1/adapter`.
SHA-256: `c6a4708d9ceca6dab5d275ea0bff5ac172e392d085a4fda6b0d875e51d95a994`.
Prior adapters are preserved. No further training, held-out, matrix or Tree test ran.
V12 remains RED and exposed. This is development-only evidence; the next held-out
claim requires a new separately frozen test and this selected checkpoint.

Verification rehashed frozen sources and adapters, reparsed all312 saved raw outputs
including reused baseline, recomputed all full/subset metrics and selection, and
checked token IDs and finish reasons. RESULT.json records full reports and hashes.
