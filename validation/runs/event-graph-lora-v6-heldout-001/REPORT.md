# Fresh held-out evaluation of the 992-step LoRA model

**Frozen extraction verdict: RED.** The selected adapter produced 116/132 exact
graphs (87.9%) and 124/132 valid resolved graphs (93.9%) on the fresh synthetic
held-out battery. The frozen requirements are 95% exact overall and 100% valid,
plus family and contrast requirements. This is an extraction accuracy result,
not a training crash or a conclusion that LoRA cannot work.

All 132 unique source passages were new, with zero exact overlap with prior v1/v3
train/development/held-out inventories. The model, parser and scoring rules stayed
fixed. The source, labels and evaluation plan were frozen and committed as
`dffa45e` before inference. Verification checked inherited and new frozen inputs,
selected adapter hash, every raw-to-parsed output, complete row inventory and
aggregate recomputation. All checks agree with the saved aggregate.

| Measure | Result | Required |
|---|---:|---:|
| Exact graphs | 116/132 (87.9%) | 95% |
| Valid graphs | 124/132 (93.9%) | 100% |
| Paraphrase agreement | 37/44 (84.1%) | 95% |
| Critical contrast distinction | 40/44 (90.9%) | 100% |
| Scorer authority mismatches | 2 | 0 |

## What failed

Eight outputs were invalid: five exact source-quote binding failures, two
unreferenced-content failures and one malformed JSON response. Eight additional
outputs were valid but differed from the authored graph:

- Four shortened entity names by omitting the site identifier: two authority
  names and two water-level names.
- Two paragraph cases attached the discharge rate to excavation instead of the
  discharge entity.
- Two role-binding cases omitted the explicitly instructed actor from the stop
  event.

The scorer labels the two shortened authority names as `invented_authority`.
Inspection shows omitted name qualifiers, not a newly invented issuing person.
They still fail the frozen identity comparison. Original parser errors are retained
in predictions and FAILURE_ANALYSIS.json even where aggregate details replace
those errors with a missing-graph message. No output or score was repaired.

| Family | Valid | Exact |
|---|---:|---:|
| quantity | 6/6 | 6/6 |
| comparator | 6/6 | 6/6 |
| polarity | 6/6 | 6/6 |
| recipient | 6/6 | 6/6 |
| authority | 6/6 | 4/6 |
| unless | 6/6 | 6/6 |
| nested | 6/6 | 6/6 |
| direction | 5/6 | 5/6 |
| temporal | 4/6 | 4/6 |
| revision | 6/6 | 6/6 |
| time | 4/6 | 4/6 |
| paragraph | 6/6 | 4/6 |
| approval | 6/6 | 6/6 |
| nested_boolean | 6/6 | 6/6 |
| negation_scope | 6/6 | 6/6 |
| conflict | 6/6 | 6/6 |
| multi_quantity | 6/6 | 6/6 |
| unit_equivalence | 6/6 | 4/6 |
| comparison_bounds | 18/18 | 18/18 |
| notification_roles | 3/6 | 1/6 |

## Disposition and limits

The matrix gate was invoked and correctly refused to advance. No numerical
artifacts or Tree tests ran. The 992-step adapter remains preserved and selected
from the earlier development session; no further model selection used this test.
Its earlier 96.2% exact development score did not carry over to this fresh battery.
Because the test inventories differ, these scores are not a controlled estimate
of isolated improvement or regression relative to older held-out versions.

This battery has new authored wording/entities/values but shared semantic families
and synthetic templates. Its author knew previous failure classes. It is not an
independently collected naturalistic project-document evaluation. It is now
exposed and cannot be treated as unseen in later development.

There were 132 local generations and zero cloud generations. Relevant corpus,
parser, gate-control and compiler checks passed 115 tests before evaluation.
The next development work should target qualified entity identity, source-span
copying and explicit actor/object binding; simply continuing the same training
schedule is not established as the fix. A future repair requires separate
training/development work and another fresh final test.

RESULT.json records the verified metrics and artifact hashes. FAILURE_ANALYSIS.json
contains the exact mismatches. FREEZE.json and GATE_BLOCK.json preserve the freeze
and downstream refusal. Raw outputs and model weights remain local under
`/Users/kenmorkaya/PycharmProjects/ToM_assist/.tmp/event-graph-lora-v6-heldout-001` and the selected v5 epoch-1 adapter directory.
