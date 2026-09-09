# Gemma LoRA event graph v4 — formally evaluated result

**Frozen extraction verdict: RED.** The corrected run completed all 512 training
steps and one local held-out pass of 132 records. Formal verification checked all
frozen source/data/checkpoint hashes, the final adapter, every raw-to-parsed output,
the row inventory and the recomputed aggregate. They agree with the saved report.

| Extraction requirement | Observed | Frozen threshold |
|---|---:|---:|
| Valid resolved graphs | 103/132 (78.0%) | 100% |
| Exact canonical graphs | 91/132 (68.9%) | 95% |
| Per-family exactness | See table below | At least 90% each |
| Invented issuing authorities detected | 0 | 0 |
| Paraphrase agreement | 29/44 groups (65.9%) | 95% |
| Critical contrast distinction | 29/44 groups (65.9%) | 100% |

The authority count is the frozen scorer's count over validated outputs. Invalid
outputs already fail the validity gate; zero here is not a claim that all raw
outputs have been certified free of role errors. Group metrics retain failed
outputs in their denominators. The 132 records contain 120 unique source strings;
shared canonical/paraphrase cases are not independent observations.

## Failure analysis

All 132 generations are parseable bare JSON. Of the 29 rejected graphs, 25 have
source quotes that cannot be bound at the selected exact occurrence, and four
reach an unsupported-action validation error (for example `permission` or
`proceed` emitted as an action instead of the supported action). Failures can
contain additional defects beyond the first validation error.

The remaining 12 failures are valid but nonmatching graphs. Four paragraph cases
place discharge before notification instead of preserving source event order.
Other examples include assigning an issuing superintendent as the actor as well
as authority, including a reporting verb in the entity name, omitting an entity
qualifier, treating a causal assertion as an obligation, and adding an exception
to a prohibition. These are general extraction/binding defects to address in a
separate version; no quotes, roles, actions or scores were repaired in this run.

The frozen aggregate detail strings replace parser failures with a missing-graph
error. `FAILURE_ANALYSIS.json` uses the original parser errors retained in the
prediction records. This diagnostic limitation does not change any count or gate.

| Family | Valid | Exact |
|---|---:|---:|
| quantity | 3/6 | 3/6 |
| comparator | 3/6 | 3/6 |
| polarity | 3/6 | 2/6 |
| recipient | 6/6 | 6/6 |
| authority | 4/6 | 2/6 |
| unless | 6/6 | 4/6 |
| nested | 6/6 | 6/6 |
| direction | 6/6 | 5/6 |
| temporal | 1/6 | 1/6 |
| revision | 5/6 | 5/6 |
| time | 6/6 | 6/6 |
| paragraph | 4/6 | 0/6 |
| approval | 5/6 | 3/6 |
| nested_boolean | 6/6 | 6/6 |
| negation_scope | 5/6 | 5/6 |
| conflict | 6/6 | 6/6 |
| multi_quantity | 4/6 | 4/6 |
| unit_equivalence | 4/6 | 4/6 |
| comparison_bounds | 17/18 | 17/18 |
| notification_roles | 3/6 | 3/6 |

## Downstream disposition

The numerical gate was invoked and correctly refused because extraction was not
GREEN. No numerical matrix artifacts or Tree tests were produced. `GATE_BLOCK.json`
records that check. The experimental SHA graph compiler inherits no result from
the MiniLM+symbol/project-register compiler. This report does not establish that
Gemma outperforms MiniLM under a common battery, or that the system is ready for
production or Tree integration.

## Training and provenance

The native supervised/inference prefix mismatch was corrected locally and verified
for all 480 train and 132 development examples using the actual training tokenizer.
V3 was preserved as an infrastructure abort. V4 started fresh from the pinned base;
no interrupted weights were resumed. The corpus, parser, thresholds, 512-step
configuration and final-adapter selection froze before v4 training. Source commit
`a99eda6` occurred during training, before held-out inference; it is not claimed as
a pre-training commit. The manifest is the pre-training file freeze.

Training record start: 2026-09-09T09:42:10.012072+00:00.
Training completion: 2026-09-09T10:29:18.105528+00:00.
Final development loss: 0.003. Peak reported training memory: 19.272 GB.
The relevant extraction/compiler regression suite passed 135 tests. These tests
and low training loss are separate from held-out extraction success.

There were 132 local generations and zero cloud generations. Inputs are synthetic
and template-based, not independently authored naturalistic hard OOD evidence.
The v3/v4 held-out corpus is now exposed and cannot be reclaimed as unseen for a
future repair. The v1 and v4 inventories/protocols differ, so their scores are not
a controlled estimate of the isolated benefit of the token-alignment correction.

`RESULT.json` contains artifact hashes and the formal aggregate. Raw predictions,
weights, checkpoints, original freeze and logs remain local under `/Users/kenmorkaya/PycharmProjects/ToM_assist/.tmp/event-graph-lora-v4-run-001`.

## Next bounded repair

Prioritize reliable source binding and action/event ordering before adding more
training steps. A separately preregistered version can test model-selected indexed
source spans to avoid repeated verbatim evidence copying, schema-constrained action
selection, and broader role/order contrasts. Retain model responsibility for
extraction and binding, keep the compiler deterministic, freeze a fresh test set,
and apply the same gate sequence. This report does not start or claim that repair.
