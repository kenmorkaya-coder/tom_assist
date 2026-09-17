# LoRA continuation session — verified development comparison

Both planned 480-step continuation epochs completed, with one full 132-record
development generation pass at each checkpoint and at the starting baseline.
The frozen input hashes, saved adapters, raw-to-parsed outputs, all aggregates and
the predeclared checkpoint selection were independently recomputed and verified.

| Cumulative steps | Exact graphs | Valid graphs |
|---|---:|---:|
| 512 baseline | 119/132 (90.2%) | 129/132 (97.7%) |
| 992, first additional epoch | **127/132 (96.2%)** | **130/132 (98.5%)** |
| 1472, second additional epoch | 116/132 (87.9%) | 126/132 (95.5%) |

**Selected checkpoint: 992 steps**, following the frozen development selection
rule. It improves exact extraction by 8 records (6.1 percentage points) over the
baseline. The final epoch regresses by 11 exact records relative to that peak,
and by 3 relative to the starting baseline. All checkpoints remain preserved;
the final weights do not replace the better 992-step candidate.

Paraphrase agreement across 44 groups: 39, 43, 41. Contrast distinction: 43, 43,
38. The scorer detected zero invented authorities among validated outputs at all
three stages; invalid outputs remain failures and are not certified by that count.
At the selected checkpoint, two outputs are invalid: one source-quote binding
failure and one dangling or mistyped reference. The final checkpoint has five
unreferenced-content failures and one source-quote binding failure.

The data, parser and learning rate stayed fixed. Each additional epoch resumed
saved weights with reset Adam state and a new predeclared shuffle seed. Thus this
session demonstrates development improvement followed by regression; it does not
isolate overfitting, optimizer resets or any single cause. Training loss alone did
not identify the best model.

These are reusable development measurements on synthetic data, not held-out
certification. The selected model still falls short of 100% valid graphs. No fresh
held-out, numerical matrix or Tree test ran. A fresh frozen final test is required
after development/model selection; the previously exposed test cannot be reused
as unseen evidence.

`RESULT.json` contains complete scores and artifact hashes. The selected local
adapter is `.tmp/event-graph-lora-v5-session-001/epoch-1/adapter` under this repository.
Weights, raw responses and training logs remain local. There were 396 local
development generations and zero cloud generations. The session is complete and
its monitoring heartbeat is paused; no extra training was silently started.
