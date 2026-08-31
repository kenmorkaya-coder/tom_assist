# DRAFT-PENDING-OWNER-FREEZE

WP-23 authoring artifacts only. **No battery run, live exchange, quota use, owner
freeze, efficacy result or G-gate verdict is present.** File/oracle contract checks
are not results on experimental arms.

## Inventory and inputs

Eleven family files contain **12 recipes each (132 cases)**. Every case plants all
11 canonical types, including the evidence/assumption boundary. Each family has
two cases for each slice: truncation, cross-session continuation, supersession,
paraphrase revival, dilution/distraction, and no-rot. There are **110 long cases
(120 or 144 turns)** and **22 short controls (15 fully visible turns)**. Domain
content is fictional and synthetically templated across 12 domains, not independent
replication material or private owner conversations.

`cases/*.jsonl` contains reviewable recipes. `domains.json` contains the complete
authored text inventory. `validation/draft_cases.py` deterministically expands them
into full histories, typed objects/relations, plant turn IDs, session IDs, action
alternatives and SUB-A..SUB-E inputs. Expansion uses no randomness, model, runtime
import or expected-answer file. `manifest.json` pins source and materialized-case
digests; recipes are the corpus storage format, not permission to regenerate labels
after observations.

`answers/*.jsonl` is a separate committed key, never included in provider-visible
inputs. Tasks require one concrete action, rejection of other choices, current
citations, retained historical IDs, exact relationships and no unauthorized state
mutations. The question declares the exact list/citation contract; there are no
hidden required-word rules or model-based semantic judges.

## Allowed authoring checks (not experiments)

From the repo root:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-gateway/bin/python -m validation.draft_contract
PYTHONDONTWRITEBYTECODE=1 .venv-gateway/bin/python -m unittest discover -s validation/tests -v
```

These check family counts, source bindings, types, history lengths, supersession,
no-rot visibility, markers, checksums, answer-key separation, and synthetic
positive/negative oracle inputs. Stdin/stdout tests use **prewritten answers**, not
provider responses. No experiment report is produced. The old three-case toy test
remains NOT-A-GATE. `harness.replay/run` refuses these draft files before any oracle
call or output directory creation, with no override flag.

## Stdin/stdout oracle contract

For a future separately authorized captured answer, load a recipe with
`validation.harness.load_histories` and its key with
`validation.draft_contract.load_answers`. Then
`request_for_answer(case, key, arm, captured_answer)` produces an input to the
existing `validation.harness.oracle` subprocess boundary. JSON sent to
`python -m validation.oracle_worker` has this illustrative shape (not a case key):

```json
{"oracle_version":"typed-action-oracle/1","case_id":"case-id","arm":"SUB-D","expected_answer":{"action_id":"...","rejected_action_ids":[],"cited_state_ids":[],"historical_state_ids":[],"relationships":[],"proposed_mutations":[],"authority":"ledger_only"},"answer":{"action_id":"...","rejected_action_ids":[],"cited_state_ids":[],"historical_state_ids":[],"relationships":[],"proposed_mutations":[],"authority":"ledger_only"}}
```

Stdout is `{"ok":true,"result":...}` or a protocol error with nonzero exit. Context
and probe text are ignored by the typed oracle: a key pasted into context cannot
rescue a wrong answer. Dict key order is ignored; values and all pre-registered
list ordering are exact. Only SUB-E may receive separate containment credit for
the exact current-state request. `explicit_mismatch` is **not** action accuracy;
do not use the `observed_match` union as action accuracy. Refusal on SUB-D is not a
correct action. `gate_verdict` is always null.

For no-rot SUB-D, optionally pass the actually observed `packet_injected` boolean
to `request_for_answer`. `packet_policy_match` is null when unmeasured, false for
gratuitous injection, true for no injection; it does not change action correctness.

## Limits requiring owner review before freeze

- Closed-action-choice tasks are not proof of arbitrary free-prose governance,
  native structural semantics, model-internal access or real-work generalization.
- WP-11 renderers remain fixture plumbing, not production retrieval or a live
  provider runner. SUB-B gets a generous summary retaining all facts/IDs/relations;
  it is not made impossible by removing citation IDs. SUB-C/D use matched current
  content with different framing. SUB-E gets wrong/stale lineage. All arms have
  identical histories and questions.
- The fixture renderer still prepends a block on no-rot SUB-D. The authored target
  is **no gratuitous injection**, to be tested with future production telemetry,
  not a claim this renderer/product meets it. Missing telemetry is not success.
- Session/restart boundaries are input recipes, not evidence of real browser or
  service restarts. Recipe IDs are fixture IDs, not ready-made native UUID imports.
- Owner freeze must audit content/labels, realistic pressure, baselines, native
  import/production runner, run pins, model/token budget, statistics, stop rules
  and consent. No live command is supplied. Do not alter a key/criterion after
  seeing an outcome; create a new version before a separately authorized run.

See `PREREGISTRATION.md`. Every artifact remains **DRAFT-PENDING-OWNER-FREEZE**;
the manifest has `owner_frozen:false`, `runs:[]`, and no verdicts.
