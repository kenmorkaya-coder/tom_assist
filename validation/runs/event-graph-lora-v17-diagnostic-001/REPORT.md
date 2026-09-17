# V17 verified causal-binding diagnostic

Both checkpoints scored 71/72 exact (98.6%) and 72/72 structurally valid. There were no recoveries or regressions between checkpoints on this diagnostic: 71 cases were correct in both, and one failed in both. The diagnostic did not reproduce the V16 process-cleft regression with these different entity names. It does not demonstrate improvement or invalidate the earlier failures.

| Sentence form | Retained 4,380 steps | Rejected 5,172 steps |
| --- | ---: | ---: |
| Active | 11/12 | 11/12 |
| Passive | 12/12 | 12/12 |
| Cause cleft | 12/12 | 12/12 |
| Process cleft | 12/12 | 12/12 |
| Result | 12/12 | 12/12 |
| Effect | 12/12 | 12/12 |
| Paraphrase agreement | 23/24 | 23/24 |
| Contrast discrimination | 24/24 | 24/24 |

The shared error is: “Unit Delta flow brings about Unit Delta flow restriction.” Both checkpoints select the entire sentence without the final full stop as the target, instead of the exact entity “Unit Delta flow restriction”. The source role is correct. This is an observed entity-boundary failure involving overlapping names. These results do not establish that overlapping names alone cause it, or identify the causal contribution of learning rate, optimizer reset or sampling.

The 4,380-step checkpoint remains selected under the predeclared protocol. No training, checkpoint promotion, fresh held-out, matrix or Tree run occurred. V12 and V15 remain RED and exposed. This is synthetic diagnostic development data with an exposed sentence form, not independent generalisation evidence.

Verification checked the inherited freeze chain, both adapter hashes and all frozen artifacts; reparsed all 144 raw predictions; checked recorded token IDs and EOS termination against finish reasons; recomputed every score and per-case transition; and compared saved report and prediction hashes. RESULT.json contains the complete scores, differences and provenance.

The next evidence-gathering step is a controlled comparison that keeps the original failing V16 sentences as anchors and changes one factor at a time: entity names, shared prefixes, name length, and causal wording. Include the newly observed shared boundary error as another anchor. This should distinguish sensitivity to names and boundaries from sensitivity to syntax before prescribing another training change. Such cases must remain diagnostic development data.

The diagnostic is complete and monitoring is paused. No further model job was launched.
