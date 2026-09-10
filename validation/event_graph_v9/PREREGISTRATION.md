# V9 bounded lower-rate continuation

Frozen before updates. Resume the selected v8 epoch-1 adapter (960 steps, 121/132
exact and 130/132 valid), preserving all previous checkpoints. Keep the v8 training
and development data, source-span prompt, binder, base weights, rank and projection
selection unchanged. Development remains exposed synthetic development, not held-out.

V8 comparison found 12 regressed, two recovered, nine persistent failures and 109
unchanged correct records. Eight newly regressed records have wrong participant or
predicate-subject spans; other regressions concern negation, comparator, revision
copying and a dangling reference. All 264 saved token streams replay exactly through
the pinned streaming decoder. No decoding-replay discrepancy explains the errors.
This does not prove overfitting or exclude other runtime or data problems.

Test one smaller continuation: 480 updates at learning rate 0.00001 (one tenth of
v8), batch size 1, seed 73, from v8 epoch 1, optimizer reset. Seed 73 matches the
previous continuation; the native batch iterator samples 480 distinct examples from
the 960-row training permutation. This is half a corpus pass, not a full epoch.
The shorter horizon and lower rate are both changed; this is a bounded retention
experiment, not a single-variable causal claim. No new labels or dev examples enter
training. Do not edit frozen data to repair individual observed failures.

Reuse the fully verified v8 epoch-1 development predictions as block 0 (zero new
baseline generations). After all 480 updates, evaluate every one of the same 132
records, retaining raw output, token IDs and finish reasons. Native inference-prefix
alignment and max sequence length 4096 remain unchanged. Select baseline or new
checkpoint by exact, valid, fewer invented authorities, paraphrase equality, contrast
distinction and earliest block. Cumulative steps: 960 baseline, 1440 new checkpoint.
Keep baseline if continuation regresses. No additional block or silent restart.

This session runs no fresh held-out, matrix discrimination or Tree gate. Development
thresholds and score definitions remain unchanged. Stop after the full report and
verification; the next change depends on that evidence. Frozen v8 sources and model
hashes plus new controller, tests and this protocol are checked before each stage.
