# Project-identity compiler: independent review

Status: fresh local identity diagnostic passes its frozen controls. This is not
a product, paragraph-extraction, Tree, memory or G-gate verdict. The earlier
typed-compiler experiment remains RED and immutable.

## Scope and artifacts

- Adapter: `gateway/project_identity_matrix_compiler.py` (experimental/unwired).
- Design: `validation/calibration/PROJECT_IDENTITY_COMPILER_V1_DESIGN.md`.
- Runner: `validation/calibration/project_identity_compiler_runner.py`.
- Completed run: `validation/runs/project-identity-compiler-20260909-v1b/`.
- Freeze: `bb6e1bc492f68f608c3cd374846675c0961a99b120e9ebd4afec304f8f240eeb`.

An initial run in `project-identity-compiler-20260909-v1/` stopped before scoring
because the diagnostic instrument passed an ndarray to a list-only helper.
Its source snapshot and inputs are preserved with ABORTED.md. The new freeze
changes only that harness conversion and an added instrument regression test.
Both freezes have identical blind inputs/scorer hashes and compiler hashes.
No score-informed changes to weights, seeds, labels or thresholds occurred.

## What was actually tested

Twelve fresh families: six similar-label identities within one project and six
identical-label identities across different project namespaces. Each has three
canonical identities, a paraphrase of the middle identity and an alternate
registered label for that same identity. There are also twelve identity-backed
direction controls, giving 84 fresh/control inputs, each compiled by both arms.

The registry is manually authored synthetic CSV evidence. Identity comes from
its project/entity/kind record, NOT from assigning every string its own code.
Alias rows share an identity. Cross-project examples deliberately supply the
active project as additional information. A text-only compiler cannot infer
which project identical prose belongs to; this comparison is not a claim that
the identity arm discovered unavailable information.

The adapter replaces resolved labels in semantic input with a common entity-kind
placeholder and adds the exact record identity to existing field symbols. It
does not change typed compiler v1, its projection, 1:1 field mix, matrix weights,
views, dimensions or final aggregation. Unknown and ambiguous labels fail
closed. This is not automatic entity resolution from arbitrary prose.

## Results

| Check | Current compiler | Project-identity arm |
|---|---:|---:|
| Final canonical conditioning passes | 2/12 | 12/12 |
| Correct paraphrase nearest | 6/12 | 12/12 |
| Paraphrase distance-margin passes | 3/12 | 12/12 |
| Paraphrase substitution passes | 4/12 | 12/12 |
| Exact equality across registered aliases | 0/12 | 12/12 |
| Distinct canonical identities | 6/12 | 12/12 |

Identity arm worst canonical condition: 6.5695504428 (limit 10).
Worst substitution condition: 6.3566995753. Minimum paraphrase ratio: 2.1439845289
(minimum 1.25). All twelve new direction controls in each arm have zero measured
transpose error and are nonidentical when reversed.

All 192 unannotated events from both prior batteries compile to exactly the same
matrices as their retained v1 results (maximum absolute difference 0). Thus all
48 previous category outcomes and 18 earlier direction controls are unchanged;
the old 23/24 holdout result has not been retrospectively labelled GREEN.

## Stage diagnosis

The saved arrays contain raw embeddings, projected semantic fields, symbolic
fields, mixed target/combined fields, weighted components, individual views,
unnormalized view sum and final matrix. They were saved and hashed before the
separate score key was opened.

Representative fresh current-arm conditions:

| Family | Raw target 384D | Projected target 32D | Combined fields | Final matrix |
|---|---:|---:|---:|---:|
| Valve Inlet / Outlet / Bypass | 4.335 | 6.299 | 12.888 | 12.694 |
| Gate Upper / Lower / Central | 7.162 | 10.328 | 21.047 | 21.624 |
| Sensor East / West / North | 8.237 | 7.582 | 15.552 | 16.144 |

This supports the dilution hypothesis but not an exclusive diagnosis: projection
also worsens the fresh gate example beyond the condition limit. Concatenating
shared fields changes conditioning without deleting the target subvector. The
source-context view contains no changing target in these controls and is
identical across canonical versions; its shared contribution further changes
the final geometry. No matrix-weight change was needed for the tested identity
arm: its corresponding final conditions are 5.413, 5.118 and 6.349.

In the identity arm the semantic label placeholders are intentionally identical
within a family, so their pre-symbol semantic basis is rank deficient by design.
The record-bound symbolic field supplies identity distinction. That must not be
reported as a MiniLM improvement or a new semantic-geometry capability.

## Independent checks and limits

- Independently recomputed final canonical/substitution conditions and
  paraphrase/alias counts from saved arrays; zero gate discrepancies.
- Independently checked all 108 identity bindings against exact event-field
  text, active project, registry row and full registry digest; zero mismatches.
- All 23 completed-run manifest entries match recorded hashes and lengths.
- All outputs were finite, deterministic, unit-normalized and nonzero; the
  independent assembly instrument matches within 1e-12. No observed symbol-code
  collision. This is not a general collision-free guarantee.
- 67 targeted unit/fixture tests pass, including ambiguous/missing registry,
  conflicting identity kind, alias identity, namespace separation, unannotated
  compatibility and the corrected instrument boundary.
- 303 local MiniLM strings embedded; zero model generations, provider calls,
  Tree operations or memory operations. Run elapsed about 21.4 seconds.
- Tracked worktree content and old experiment artifacts were unchanged during
  execution. Existing unrelated work by other tasks was preserved.

Matrix construction for this tested route is now frozen pending extraction
work. The existing separate task `Define Gemma ToM compiler pipeline` has been
sent the result and claim boundaries. Its independent pure-hash graph compiler
is a different representation and inherits no validation from this experiment.
No training or feature integration was started by this supervisory task.

The next independent question is paragraph-to-event-graph correctness, including
roles, quantities, scope, aliases/references and missing facts. Compiler success
does not establish that extraction succeeds. Identity codes do not establish
numeric order, arithmetic, chronology or logical reasoning.
