# Lower-rate LoRA continuation — verified development result

Both planned 480-step epochs completed at learning rate 2e-5, starting from the
selected v5 epoch-1 992-step adapter. All frozen inputs and adapter hashes,
raw-to-parsed predictions, development aggregates and selection were verified.

| Model | Exact graphs | Valid graphs |
|---|---:|---:|
| Reused 992-step baseline | **127/132 (96.2%)** | **130/132 (98.5%)** |
| V7 epoch 1, 1472 cumulative steps | 97/132 (73.5%) | 100/132 (75.8%) |
| V7 epoch 2, 1952 cumulative steps | 117/132 (88.6%) | 124/132 (93.9%) |

**Selected model remains the original 992-step baseline.** Neither lower-rate
checkpoint improves it. Epoch 2 recovers 20 exact records relative to epoch 1,
but remains 10 exact records below the baseline (7.6 percentage points). Both
new checkpoints remain preserved; neither replaces the best saved weights.

The final checkpoint has eight source-quote binding failures and seven additional
valid but nonexact graphs. The first checkpoint had 32 invalid outputs involving
unreferenced content, source quotes, dangling references and extra JSON data.
Paraphrase agreement across 44 groups was 43, 24, 37; contrast distinction was
43, 36, 42. Zero authority mismatches were detected among validated outputs.

The baseline's original 132 generations were reused and reverified; this session
made 264 new local development generations and zero cloud generations. Two full
epochs used the unchanged 480-example training inventory. Adam state was reset
per block, with fixed predeclared seeds 41 and 53. No data, schema, parser or
prompt repair occurred. These results do not establish a unique cause for the
regression, and low training loss did not predict generation accuracy.

These are repeated development measurements, not held-out certification. The v7
1472-step adapter is distinct from the earlier higher-rate 1472-step adapter.
No fresh held-out, matrix or Tree test ran in this session. The selected baseline
already scored 116/132 exact (87.9%) on the separate v6 fresh held-out test; its
generalisation shortfall remains unresolved.

Further repetition of this unchanged training setup is not supported by these
results as a demonstrated improvement. The best checkpoint is preserved for
subsequent diagnosis and separately specified development work. This bounded
session is complete; no more training has been started and its monitor is paused.

RESULT.json records full metrics, hashes and the local run path. Selected weights
remain under .tmp/event-graph-lora-v5-session-001/epoch-1/adapter. All raw outputs
and weights remain local and outside Git.
