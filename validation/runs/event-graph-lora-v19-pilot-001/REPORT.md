# V19 verified matched training pilot

The targeted coverage change failed every predeclared acceptance criterion. Retain the 4,380-step checkpoint. Both pilot checkpoints reached 4,476 cumulative steps, starting independently from the same weights.

| Exact extraction | Baseline | Control | Changed coverage |
| --- | ---: | ---: | ---: |
| Original 132 development cases | 132 | 132 | 131 |
| Earlier extension 24 | 23 | 16 | 16 |
| Newer extension 36 | 36 | 36 | 33 |
| All development 192 | 191 | 184 | 180 |
| Unique causal diagnostic 56 | 47 | 50 | 46 |
| Four original diagnostic anchors | 3 | 4 | 0 |

Development graph validity was 192/192 at baseline and 184/192 in both pilot arms. All 56 diagnostic graphs were structurally valid in each condition. Both arms produced invalid source token spans on the same eight earlier-extension cases. Changed coverage additionally damaged semantic extraction on four structurally valid development cases. It also lost correct source/target binding on the first three original diagnostic anchors; the fourth remained incorrect. No invented authorities were reported in the development subsets.

The only difference between the two pilot inputs was reversal of causal roles in eight effect-first examples. Both used the same 48 causal and 48 representative other records, the same seed 151, learning rate 0.000005, optimizer reset, 96 updates, base adapter and model configuration. All 96 records were sampled exactly once, in identical order across arms, verified against the logged sample IDs and training receipts. Supervised prompt alignment checks passed without truncation. This is a matched comparison within a small selected training mix, not a full-corpus continuation.

The changed coverage scored four fewer diagnostic cases correctly than the control and one fewer than baseline, and failed retention checks. This specific eight-example change is not supported by this pilot. The control's causal gains also came with unacceptable broader regressions. The shared invalid-span failures cannot be explained solely by the eight changed rows because they occurred in the control too. Their cause remains unestablished; inspecting those saved outputs and the shared training setup is the next diagnostic step before prescribing further training. A single seed does not establish that reversed-role examples are generally harmful.

Verification rechecked the frozen dependency chain, source and adapter hashes, both training configurations and receipts, alignment and sample telemetry; reparsed all 496 new saved predictions; checked integer token IDs and terminal EOS against stop/length; recomputed both reports and the frozen baseline; and checked the original four anchors' source/target correctness. RESULT.json records the scores, acceptance criteria, anchor roles and artifact hashes. Large weights, predictions and logs remain at /Volumes/My Passport for Mac/gemmatraining/event-graph-lora-v19-pilot-001. No full datasets were copied.

This pilot uses development and exposed synthetic diagnostic cases. V12 and V15 remain RED. No fresh held-out, matrix or Tree evaluation was run. Neither pilot checkpoint is promoted. The pilot is complete, monitoring is paused, and no further run was launched.

## Follow-up diagnosis: shared revision failures

Read-only inspection of all eight failed revision cases in each arm found one invalid field per output: events[1].evidence[0] is {token_start:37, token_end:37}. Each source has 53 lexical tokens. The generated span is empty; the strict binder correctly rejects it. All 16 generations ended normally with stop, so these failures were not output-length truncation. The source labels contain valid evidence spans.

As an isolation check only, replacing this one field in an in-memory copy with the authored event evidence made all 16 graphs validate and match the expected semantic graph. This uses known gold evidence; it is not an inference-time repair, a score correction, or proof that all original evidence was properly grounded. Saved predictions, parser behavior and reported scores remain unchanged. The model-generated empty evidence span is the immediate failure; the training cause is still unproven.

Both pilot datasets contained 48 V8 records and 48 V16 causal records. Their only two revision records were V8 canonical/paraphrase examples from the same group. All selected training spans were nonempty, so the empty span was not directly present in those labels. The selection code takes the first records of each family: it excluded the later revision-training extensions despite the full V16 inventory containing 96 revision records. Describing this as representative replay overstated its coverage. Both arms shared this selection weakness, so the eight-row causal intervention cannot alone explain the shared failure.

The next bounded experiment should isolate revision replay selection: replace the two older same-group revision records with two existing later revision-training records, keeping the control arm's other 94 examples, initialization, order, update budget and settings fixed. Compare against the completed control, with the frozen revision checks and broad retention checks. This would test a supported hypothesis, not assume replay omission is causal. No such run has started. No extra files or model outputs were created for this diagnosis.
