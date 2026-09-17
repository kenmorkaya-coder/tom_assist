# V21 verified event-evidence pilot

Narrowing the four event-evidence fields did not improve the V20 run. All predeclared acceptance criteria failed. Retain the original 4,380-step checkpoint.

| Exact extraction | Retained baseline | V20 | V21 |
| --- | ---: | ---: | ---: |
| Original 132 development cases | 132 | 132 | 131 |
| Earlier extension 24 | 23 | 19 | 15 |
| Newer extension 36 | 36 | 36 | 33 |
| All development 192 | 191 | 187 | 179 |
| Unique causal diagnostic 56 | 47 | 43 | 42 |
| Original diagnostic anchors 4 | 3 | 3 | 2 |

Development graph validity declined from188/192 in V20 to182/192 in V21. All eight targeted revision cases are invalid again, compared with four in V20. The new run has eight invalid-source-span errors and two errors where a span object does not have the required fields. No invented authorities were reported in the development subsets.

Of the seven causal boundary regressions previously identified in V20, two became exact in V21: v18-rename_site-3-0 and v18-short_names-3-0. Five remain incorrect. Despite those recoveries, overall diagnostic exact accuracy fell from43/56 to42/56. The hypothesis that this event-evidence narrowing would repair the boundary failures while preserving revision reliability is not supported by the pilot.

Only four event-evidence fields in the same two training examples changed. Source text, entity names, semantic fields, revision evidence, other94examples, starting adapter, sample slots/order, update count, seed and learning rate were held fixed. The chosen spans were [0,17) and[17,43) in the first example, and[0,15) and[9,37) in the second. The final span retains the entity antecedent for “its continuation”. Both runs independently trained96updates from4,380 to4,476steps, at learning rate0.000005 and seed151 with optimizer reset. Actual telemetry confirms all96examples were sampled exactly once in the same order. Training configuration differences were limited to output path; alignment checks passed without truncation.

Verification checked the frozen artifact chain and trained adapter/configuration hashes, sample receipts and logs; reparsed248 new outputs and248 V20 outputs; checked integer token IDs and EOS against finish reasons; and recomputed both reports and the retained baseline. RESULT.json includes acceptance criteria, subset scores, eight revision cases, four anchor checks, seven tracked boundary cases and provenance hashes. Large artifacts remain at /Volumes/My Passport for Mac/gemmatraining/event-graph-lora-v21-pilot-001.

This single-seed comparison tests a particular evidence-label change in a small selected training mix. It does not establish a universal preference for broad evidence or explain every regression. No parser repair or score adjustment was applied. V12 and V15 remain RED; no fresh held-out, matrix or Tree run occurred. Monitoring is paused and no further run was launched. More local label changes are not justified by this result alone; the next decision needs a review of the accumulated pilot evidence before another training hypothesis.
