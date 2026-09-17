# V18 verified anchored diagnostic

All four original sentences reproduced their earlier outputs on both adapters: all eight comparisons matched semantically, in raw text, in token IDs and in finish reason. The earlier failures are reproducible. The results support sensitivity to the combination of entity naming and causal wording, rather than a defect confined to one sentence form.

## Primary comparison: canonical sentence for each of four anchors

| Intervention | Retained 4,380 steps | Rejected 5,172 steps |
| --- | ---: | ---: |
| Original sentence | 3/4 exact | 0/4 exact |
| Rename both site prefixes | 4/4 | 4/4 |
| Change target site prefix only | 2/4 | 2/4 |
| Short neutral names | 4/4 | 4/4 |
| Change causal wording, preserve names and order | 4/4 | 4/4 |

Renaming both prefixes repaired all four canonical anchors, including the overlapping-name case. Changing only the target prefix did not consistently help: both adapters reversed cause and effect for two Flint Tunnel cases, while selecting the exact entity names. Therefore shared prefixes alone do not explain the defect. With the original names, changing the three process-cleft sentences to passive wording repaired the new checkpoint's causal errors; changing “brings about” to “causes” repaired the shared boundary error. These are observations on four selected failures, not population estimates or isolated causal estimates of individual token features.

## Secondary comparison: canonical, paraphrase and reversal records

| Condition | Retained 4,380 steps | Rejected 5,172 steps |
| --- | ---: | ---: |
| Original anchor triplets | 8/12 | 5/12 |
| Rename both prefixes | 12/12 | 12/12 |
| Distinct prefixes | 7/12 | 7/12 |
| Short neutral names | 12/12 | 12/12 |
| Changed wording | 9/12 | 10/12 |
| Total exact | 48/60 | 46/60 |
| Structurally valid | 60/60 | 60/60 |
| Paraphrase agreement | 12/20 | 12/20 |
| Contrast discrimination | 18/20 | 17/20 |

There are 56 unique source sentences: four result-form paraphrases repeat across the anchor and wording conditions. The 60-record counts are protocol-weighted, not 60 independent observations. Deduplicated exact scores are 47/56 and 44/56. Among unique failing sentences, the retained adapter has five errors involving wrong entity spans and four involving exact names bound to wrong roles; the new adapter has eight and four respectively. A wrong-span classification may also include a wrong role. Across the 60 records, 44 remain correct, 10 remain incorrect, four regress and two recover; the two recovery records repeat one source sentence.

## Supported next change

Prepare a bounded causal-role and entity-boundary training extension from the retained 4,380-step adapter. Cross fresh multiword names, identifiers, overlapping and distinct prefixes with active, passive, process-cleft and result-form wording. Balance both causal directions so entity names do not predict roles. Preserve the existing broad training mix and development retention checks. Use exact source-span supervision and retain these exposed failures as diagnostic regressions, without copying their exact sentences into training. Freeze a separate development extension with disjoint names before choosing an update budget. The current evidence supports this curriculum change; it does not establish that changing learning rate or merely adding more cycles will help.

All 120 saved raw outputs were reparsed, token IDs and EOS termination checked, aggregate scores and per-case roles recomputed, and frozen provenance and adapter/prediction hashes verified. RESULT.json preserves the primary per-anchor comparisons, full error differences, original-output reproduction checks and hashes.

The 4,380-step adapter remains selected. No training or downstream run was performed. This diagnostic uses authored, exposed development cases; V12 and V15 remain RED. No fresh held-out verdict is implied. Monitoring is paused, with no follow-on model job launched.
