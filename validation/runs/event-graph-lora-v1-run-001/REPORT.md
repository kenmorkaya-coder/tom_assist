# Gemma LoRA event graph v1 — formally evaluated result

**Frozen extraction verdict: RED.** All 108 held-out generations were rejected by the original bare-JSON parser (0 valid / 0 exact). The saved manifest, adapter hash, prediction hash and aggregate score were verified, and the frozen scorer reproduced the aggregate exactly.

LoRA training completed all 128 planned steps. The saved adapter remains local. There were 108 local held-out generations and zero cloud generations. The numerical gate was invoked and correctly refused to proceed; no matrix discrimination or Tree test ran.

## Separate post-hoc diagnosis

107 outputs had a complete Markdown fence. Removing only that presentation wrapper for diagnosis yielded 39 exact canonical graphs, 35 valid but nonmatching graphs, and 34 remaining validation/refusal failures. These are post-hoc counts, not a repaired gate result or a v2 held-out pass.

| Family | Exact after presentation-only unwrapping | Total |
|---|---:|---:|
| quantity | 6 | 6 |
| comparator | 6 | 6 |
| polarity | 4 | 6 |
| recipient | 0 | 6 |
| authority | 4 | 6 |
| unless | 1 | 6 |
| nested | 6 | 6 |
| direction | 1 | 6 |
| temporal | 0 | 6 |
| revision | 0 | 6 |
| time | 0 | 6 |
| paragraph | 0 | 6 |
| approval | 0 | 6 |
| nested_boolean | 1 | 6 |
| negation_scope | 3 | 6 |
| conflict | 0 | 6 |
| multi_quantity | 3 | 6 |
| unit_equivalence | 4 | 6 |

Examples of substantive defects include notification recipients assigned to target, calendar dates assigned to revision, permission labeled assertion, hypothetical approvals labeled asserted, and a prohibition trigger moved into exception. Repeated-quote binding also fails. Some exact mismatches instead reflect harmless unary Boolean wrappers or an ambiguous actor/object convention in the synthetic labels; the 35 nonmatches must not all be described as incorrect language understanding.

## Next version and boundaries

V1 stays immutable. Parser v2 is only a separately versioned fence repair. V3 has been frozen separately to address explicit quote occurrences, typed canonicalization, role-consistent authored examples, all six comparison operators, and full training-inventory exposure with a larger LoRA adapter. It uses fresh test wording and is trained from the pinned base, not against v1 predictions. No v3 verdict is asserted here.

Both corpora are synthetic; this is not independently authored naturalistic OOD evidence. The v1 held-out inventory contains 108 records but 96 unique source strings because some controlled contrasts share base sentences. No confidence interval treats those records as independent.

The graph compiler uses separate experimental SHA identity encoding. It inherits no matrix result from the MiniLM+symbol/project-register compiler. Production, Tree integration and project-wide identity resolution remain outside this result.

## Reproduction and provenance

`RESULT.json` records the exact artifact hashes and local run location. The local run retains the original freeze, adapter, training log, raw predictions, aggregate and diagnostic. Model weights, intermediate checkpoints and temporary run outputs are not added to Git.

Training began 2026-09-09 08:36:02 UTC and completed 08:44:15 UTC. The prediction file was created 08:45:05 UTC. Early outputs were inspected before the coordination hold; the aggregate was formally verified only after that hold was withdrawn. The later source lock is explicitly post-training/post-partial-exposure, not a retroactive pre-exposure baseline.
