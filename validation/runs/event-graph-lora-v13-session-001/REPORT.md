# V13 expanded development continuation — verified result

The 720-update continuation completed at cumulative step 4020. The frozen selection
rule selects this checkpoint: all 132 original cases remain exact, while the 24 new
development cases improve from 15 to 22 exact. No extra training cycle was started.

| Metric | Baseline, 3300 steps | V13, 4020 steps |
|---|---:|---:|
| Original exact / 132 | 132 | 132 |
| Extension exact / 24 | 15 | 22 |
| Combined exact / 156 | 147 (94.2%) | 154 (98.7%) |
| Combined valid / 156 | 156 (100%) | 155 (99.4%) |
| Invented authority | 0 | 0 |
| Paraphrase equality / 52 | 47 | 50 |
| Contrast distinction / 52 | 48 | 52 |

Validity regressed by one output. The remaining revision failure, v13-dev-revision-1-1,
emits an evidence range missing token_start. The remaining paragraph failure,
v13-dev-paragraph-1-1, labels the final flow event as use instead of discharge.
The two affected families each score 17/18 (94.4%), above the per-family threshold.
All original families/cases remain correct. The 100% validity requirement is still
unmet, so development thresholds do NOT all pass despite increased exact accuracy.

Selected adapter: `.tmp/event-graph-lora-v13-session-001/epoch-1/adapter`.
Previous checkpoints remain intact. These 156 examples are development data, including
an extension informed by exposed failure classes. No fresh held-out, matrix or Tree
experiment ran. V12 remains RED and exposed. No downstream pass is implied.

Verification rehashed frozen inputs and both adapters, reparsed all 312 raw outputs,
recomputed aggregate and subset metrics and the retention-first checkpoint selection,
and checked token IDs and finish reasons. RESULT.json contains the full reports and
SHA-256 provenance. No model generation was repeated for this verification.
