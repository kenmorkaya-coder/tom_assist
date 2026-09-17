# V16 verified development comparison

The 792-update training block completed at 5,172 cumulative steps. The frozen selection rule retains the previous 4,380-step checkpoint: the new checkpoint recovered one paragraph action but introduced three causal source/target errors.

| Development subset | Previous checkpoint | New checkpoint |
| --- | ---: | ---: |
| Original 132 | 132/132 exact | 132/132 exact |
| Previous extension 24 | 23/24 exact | 24/24 exact |
| New boundary/negation 36 | 36/36 exact | 33/36 exact |
| Total | 191/192 (99.5%) | 189/192 (98.4%) |
| Valid graphs | 192/192 | 192/192 |
| Invented authorities | 0 | 0 |
| Paraphrase agreement | 63/64 | 64/64 |
| Contrast discrimination | 64/64 | 63/64 |

The previous checkpoint meets the development thresholds. The new checkpoint fails them, including the requirement to distinguish every contrast. Three newly incorrect cases use “The process bringing about X is Y”: the new checkpoint misbinds causal source and target; two also select an overlong entity span. The recovered paragraph changes the final action from “use” to the expected “discharge”. There are 188 unchanged correct cases, one recovery and three regressions. Exact case differences are preserved in TRANSITIONS.json.

Training used learning rate 0.000005, seed 151, an optimizer reset and 792 updates: half a pass over 1,584 rows, including 144 added examples. This does not guarantee every added example was sampled. The baseline already answered all 36 new development cases correctly, so these additions provided limited evidence about previously observed held-out weaknesses. These are authored template families; repeated development selection does not establish generalisation to independent project prose.

Verification rechecked the frozen provenance chain and adapter hashes, reparsed all 384 saved predictions, recomputed aggregate and subset scores and selection, and checked saved token IDs against finish reasons. RESULT.json preserves reports and artifact hashes. No new inference was required for verification.

Selected checkpoint: .tmp/event-graph-lora-v14-session-001/epoch-1/adapter, 4,380 cumulative steps. Its adapter SHA-256 is c6a4708d9ceca6dab5d275ea0bff5ac172e392d085a4fda6b0d875e51d95a994.

No fresh held-out, matrix or Tree evaluation was run. V12 and V15 remain RED and exposed; this development comparison does not replace those results. Training is complete and monitoring is paused. No further training was launched.
