# V8 source-span training session

Frozen before any v8 model updates. This is a new extraction protocol and adapter,
initialized from the same locally pinned Gemma 4 26B A4B 4-bit base. The selected
old-protocol 992-step adapter is preserved and is not resumed or converted.

## Data and representation

960 training records and 132 development records; 20 semantic families. Training
contains 320 three-record canonical/paraphrase/contrast groups, development 44.
All labels derive from the existing authored training/development templates with
split-specific qualified entity names and document headers. Extra training groups
increase explicit actor/issuer/recipient coverage. Development uses separate names
and headers but shares template families: this is not an independent held-out test
or a claim of naturalistic generalisation. Prior exposed held-out labels are not
training inputs. Corpus construction and group meaning are checked before freeze.

The new wire protocol emits lexical source ranges instead of entity declarations,
entity ID references or copied evidence quotes. A deterministic binder copies only
selected source ranges and constructs referenced entity records. It does not infer
missing roles, repair wrong source selections or merge paragraphs. Existing typed
graph validation and deterministic matrix compiler remain separate. Graph meaning,
full entity qualifiers and roles remain part of exact scoring.

## Schedule and selection

Two 960-update epochs, batch size 1, learning rate 0.0001, seeds 61 and 73. Epoch 1
initializes fresh rank-16 LoRA adapters on q/v projections in the last 16 layers;
epoch 2 resumes epoch 1 weights with a reset optimizer, as in earlier controllers.
This is two full corpus passes with an optimizer reset, not uninterrupted optimizer
continuation. Native inference-prefix alignment and prompt masking apply. Maximum
sequence length 4096; all 1092 labels preflight below that limit, with no truncation.
Validation loss samples 16 batches at the configured intervals and is diagnostic.

After each epoch, generate all 132 development records deterministically (temperature
0, maximum 4096 generated tokens), retaining raw output and streamed token IDs.
Compare exact count, valid count, fewer invented-authority errors, paraphrase equality,
contrast distinction and then earliest epoch, in that priority order. No early
stopping or extra updates based on individual cases. Epoch 1 is the first trained
reference; do not compare these percentages directly with the different old wire
protocol and development corpus. Retain the best checkpoint even if epoch 2 regresses.
Development thresholds inherit the existing strict metrics but confer no gate pass.

No held-out inference, matrix discrimination or Tree testing in this session. A fresh
held-out protocol must be frozen separately before evaluating the selected adapter.
Failures preserve artifacts and stop the controller; no silent retries. Frozen hashes
cover corpus, prompt, binder, controller, tests and the inherited pinned runtime/model
provenance. Training and checkpoint storage remain local and offline. No base weights,
installed environment, prior reports or adapters are modified.
