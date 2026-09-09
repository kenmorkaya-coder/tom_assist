# Typed event graph LoRA experiment

Feature branch: `codex/gemma-lora-typed-event-graph`.

This experimental path implements English → local Gemma with LoRA → a
source-grounded typed event graph → deterministic signed 32×32 loads.
The production gateway and ToM are not connected to this path.

## Files

- `gateway/typed_event_graph.py`: strict typed graph validation, exact rational
  units, graph/reference checks and ID-independent semantic representation.
- `gateway/event_graph_extractor.py`: versioned extraction prompt, JSON parsing,
  and unique exact-quote binding. Character offsets are supplied by code.
- `gateway/event_graph_compiler.py`: reproducible individual event/link loads;
  no prose interpretation, embeddings, model calls or paragraph averaging.
- `validation/event_graph_v1/schema.json`: published graph JSON Schema;
  cross-reference, evidence and cycle constraints additionally require the runtime validator.
- `validation/event_graph_v1/data/`: authored labels and group/split metadata.
- `validation/event_graph_v1/training/`: train/dev chat examples only.
- `validation/event_graph_v1/experiment.py`: immutable manifests, pinned local
  LoRA training, held-out generation/scoring and conditional matrix gate.
- `validation/event_graph_v1/PREREGISTRATION.md`: experimental design,
  thresholds, stop rules and claim limitations.

## Reproduction

Run from the repository root. Set `LOCAL_GEMMA_PYTHON` to an existing environment
with MLX 0.31.1, mlx-lm 0.31.2 and Transformers. The checkpoint path is explicitly
pinned in the experiment module. The environment and checkpoint remain read-only;
outputs go into the selected local run directory. Metal GPU access is necessary.
Use a fresh run directory; do not overwrite an earlier experiment.

```sh
export PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
.venv-gateway/bin/python validation/event_graph_v1/experiment.py freeze --run .tmp/event-graph-lora-v1-new-run
"$LOCAL_GEMMA_PYTHON" validation/event_graph_v1/experiment.py train --run .tmp/event-graph-lora-v1-new-run
"$LOCAL_GEMMA_PYTHON" validation/event_graph_v1/experiment.py infer --run .tmp/event-graph-lora-v1-new-run --split heldout
"$LOCAL_GEMMA_PYTHON" validation/event_graph_v1/experiment.py matrix --run .tmp/event-graph-lora-v1-new-run
```

The last command refuses to proceed without a recomputed extraction GREEN.
Missing predictions remain failures in the original denominator. Do not rerun
held-out scoring as a tuning loop. A new model/configuration selected after
seeing this held-out set requires newly held-out evidence.

Training and held-out inference are substantial GPU jobs. Interruptions preserve
logs and partial predictions; they are not successful runs. There is no automatic
resume that could silently evaluate the same held-out item twice.

## Boundaries

The initial corpus is synthetic and bounded. Schema support for a role or link
is not evidence that Gemma reliably extracts it. Likewise, evidence spans prove
source overlap, not correct language interpretation. The extraction gate checks
meaning against authored labels, separately from matrix discrimination.

The compiler's signed identity vectors preserve exact typed distinctions. They
do not imply numeric-order geometry, general semantic similarity, collision-free
encoding, or logical reasoning by matrix arithmetic. Hypothetical events retain
explicit modality; downstream treatment must be validated before adoption.

Entity references currently resolve within one input passage. A persistent
project-wide registry and cross-document identity resolution are not implemented
by this experiment. Explicit date/revision strings are preserved; date reasoning
and unit spellings outside the schema are not inferred by compiler code.

Original regression, independent review and the temporal-authority battery
remain required downstream of the two gates. Nothing here changes an existing
frozen compiler result, production feature flag, Tree, memory or project data.
