# Evaluation provenance record

The committed baseline manifest is
`validation/baselines/compiler-evaluation-20260909.json`.
The Git commit identifies the whole source tree; SHA-256 entries identify the
selected compiler/evaluation files. External records contain paths and hashes,
never model weights or predictions. Local timestamps are recorded observations,
not independently certified timestamps. A verified push is the remote provenance
point, not proof that earlier held-out output was unseen.

Every run must have a new append-only record with these fields:

| Field | Required content |
| --- | --- |
| Identity | Run ID, experiment version, owner task, parent run and purpose |
| Source | Full baseline commit SHA, source tree SHA, remote/ref, verified remote SHA and UTC time |
| Contract | Manifest SHA-256, prompt/schema/validator/compiler/scorer hashes and exact parser version |
| Data | Train/dev/held-out hashes, counts, generator hash, split policy and prior-exposure declaration |
| Model | Base model repository/revision/file hashes, adapter hash, external location |
| Training | Runtime versions, fixed configuration, seed, checkpoint-selection rule, actual start/end |
| Exposure | First held-out inference, first inspection, observer, and whether each occurred after remote lock |
| Evaluation | Exact invocation, denominator, missing/invalid policy, frozen gate version, external output hashes |
| Integrity | Clean checkout verification, manifest verification, drift checks, no unrecorded overrides |
| Decision | Literal frozen verdict, limitations, any post-hoc analysis clearly separated |

Unknown values remain `null` or explicitly unknown; never reconstruct a favorable
timeline from commit messages or file modification times. Any tuning prompted by
held-out observations requires a new version and fresh confirmatory data.

Use `python3 validation/verify_compiler_baseline.py --commit FULL_SHA` from an
isolated checkout of that commit. It checks the committed manifest against both
Git and local bytes without reading results or invoking a model. External model,
adapter and historical bundle verification remain separately required.

The baseline commit SHA and push verification belong in a subsequent receipt
referencing the baseline, not an amended baseline or a self-referential field.
