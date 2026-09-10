# V8 source-span LoRA session — verified development result

Both scheduled epochs completed. Epoch 2 reduced exact development accuracy by
10 records (7.6 percentage points), despite increasing valid outputs by one.
The frozen selection rule retains **epoch 1, 960 steps**.

| Checkpoint | Exact / 132 | Valid / 132 | Invented authority | Paraphrase / 44 | Contrast / 44 |
|---|---:|---:|---:|---:|---:|
| Epoch 1, 960 steps | 121 (91.7%) | 130 (98.5%) | 0 | 41 | 43 |
| Epoch 2, 1920 steps | 111 (84.1%) | 131 (99.2%) | 0 | 38 | 42 |

Epoch 1 had two cyclic-condition validation failures. Epoch 2 had one dangling
or mistyped reference. These results show regression in exact extraction with
this additional training cycle; they do not establish its cause.

The selected checkpoint is `.tmp/event-graph-lora-v8-session-001/epoch-1/adapter`.
The prior 992-step adapter remains intact. Its scores use a different representation
and corpus and are not directly comparable. No fresh held-out, matrix or Tree gate
was run. Neither epoch meets all development thresholds.

Verification rehashed the frozen inputs and both adapters, reparsed all 264 raw
outputs, recomputed all development metrics and checkpoint selection, and checked
saved token IDs and finish reasons. Complete reports and SHA-256 provenance are
in RESULT.json. No new model generation or training was performed during verification.
