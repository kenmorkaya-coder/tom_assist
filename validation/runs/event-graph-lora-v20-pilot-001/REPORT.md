# V20 verified revision replay pilot

Replacing two older revision training examples repaired four of the eight shared revision failures, but reduced causal diagnostic accuracy. The pilot does not meet its predeclared requirements. Retain the 4,380-step checkpoint.

| Exact extraction | Baseline | V19 control | V20 revision replay |
| --- | ---: | ---: | ---: |
| Original 132 development cases | 132 | 132 | 132 |
| Earlier extension 24 | 23 | 16 | 19 |
| Newer extension 36 | 36 | 36 | 36 |
| All development 192 | 191 | 184 | 187 |
| Unique causal diagnostic 56 | 47 | 50 | 43 |
| Four original diagnostic anchors | 3 | 4 | 3 |

Development graph validity improved from 184/192 in the control to 188/192, still below the baseline's 192/192. Four of the eight revision cases remain invalid with source-span errors; four are now valid and exact. One other development case is structurally valid but semantically wrong. All original132 and newer36 cases remain exact. The revised arm scored seven fewer causal diagnostic cases correctly than control, and four fewer than baseline. It lost the control's correct target binding on the fourth original diagnostic anchor. No invented authorities were reported in the development subsets.

The first two existing V13 revision training examples replaced the two V8 revision examples in the same sample slots. The other 94 examples, starting adapter, settings and complete sample order matched the V19 control. Each arm used 96 updates with learning rate0.000005 and seed151, independently reaching4,476 cumulative steps from4,380. All96 slots were sampled exactly once. Alignment passed without truncation; configuration differences were limited to output path. The matched comparison supports a partial effect of this revision replay replacement, accompanied by unacceptable tradeoffs. It does not establish whether wording or evidence style within those replacement examples caused the effect, nor that replay coverage is the sole cause of the original regression.

Only the original132 retention criterion passed. The pilot failed the requirements to repair all eight revision cases, retain at least155/156 earlier development cases, achieve at least191/192 exact with all graphs valid, maintain at least50/56 causal diagnostic exact, and retain all four anchor roles achieved by control.

Verification rechecked frozen source and artifact hashes, both trained adapters/configurations, training receipts and actual sample logs; reparsed all248 new outputs and248 control outputs; checked token IDs and EOS against finish reasons; and recomputed both scores and the retained baseline. RESULT.json records detailed scores, revision cases, anchor-role checks, acceptance criteria and provenance. Large outputs remain at /Volumes/My Passport for Mac/gemmatraining/event-graph-lora-v20-pilot-001.

No checkpoint promotion or additional model run occurred. V12 and V15 remain RED; this exposed development pilot is not a held-out generalisation result. Monitoring is paused. The next decision should use the remaining saved span errors and the causal regressions; repeating or extending training is not justified by this result alone.

## Follow-up diagnosis: seven causal regressions

Comparison of the 56 unique saved diagnostic outputs gives 43 retained correct, seven regressions, six persistent failures and no recoveries. The seven losses are all entity-span selection errors; none is an exact-name source/target swap or a change to another semantic event field. The two prediction-file hashes match the verified RESULT.json provenance.

| Case | Changed field | Expected entity | Selected text |
| --- | --- | --- | --- |
| v18-anchor-0-1 | target | Marsh Gallery D00-K groundwater pumping | Marsh Gallery D00- |
| v18-anchor-1-1 | target | Flint Tunnel D01-K groundwater pumping | Flint Tunnel D01- |
| v18-short_names-1-2 | source | Process B1 | B1 |
| v18-anchor-2-1 | target | Flint Tunnel D03-K groundwater pumping | Flint Tunnel D03- |
| v18-anchor-3-0 | target | Unit Delta flow restriction | Entire sentence without final full stop |
| v18-rename_site-3-0 | source | Silver Court R03-M flow | Entire sentence without final full stop |
| v18-short_names-3-0 | source | Process A3 | Process A3 brings about |

Four spans are too short and three too long. These predictions remain structurally valid: their token ranges are nonempty and in bounds, but identify the wrong text. This differs from the empty event-evidence spans that invalidate the revision cases. No interpretation-time correction was applied.

The original two V8 revision examples use narrower event-evidence spans: [4,22), [22,43) and [3,25), [25,46). The two V13 replacements use the whole source for all four event-evidence spans: [0,43) twice and [0,37) twice. The first revision identifier's evidence also changes from a narrow identifier span to whole-source evidence; the second remains narrow. Role-object labels remain exact entity-name spans in both versions. Wording, entity names and revision identifiers also differ, so this replacement comparison does not isolate evidence granularity as the cause. Whole-source evidence is allowed by the current schema and is not automatically an incorrect label.

The next narrowly defined experiment would keep the V20 source text, entities, revision identifiers, role labels, revision-evidence spans, training settings and sample order unchanged, changing only the four event-evidence spans to manually verified supporting clauses. Compare with the completed V20 arm and measure both entity-boundary errors and revision validity. Preserve cross-sentence support where necessary rather than forcing every event into a single sentence. This would isolate event-evidence granularity; it must not be presented as a proven fix. No new training or inference was launched for this diagnosis, and no new working files were created.
