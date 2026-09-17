# Binding and graph-reference audit

The audit found concrete output-structure defects and a testable representation
repair. It found no new token-prefix or streaming-decoder defect in known-token
replays. No model weights were loaded or trained and no new answers were generated.
All previous reports, gates and the best 992-step checkpoint remain unchanged.

## Findings

- The 480 training records contain 432 distinct source strings; the 132 development
  records contain 120. There are no conflicting canonical meanings for identical
  source text in either inventory. Repeats still limit example diversity.
- Only 24/480 training examples have five entities. The explicit actor/issuer/
  recipient family therefore has relatively few distinct training contexts.
- The first lower-rate epoch has 14 unreferenced-content failures, dominated by
  the model treating document framing such as “project instructions” as an entity.
- Its six dangling-reference failures refer to undeclared entity IDs: five use
  `n5` in notification cases and one uses `n6` in a paragraph case. These are not
  errors caused by the deterministic matrix compiler.
- The actual MLX tokenizer's inference encoding matches the aligned supervised
  prefix for every one of the 480 train and 132 development examples. All answer
  encode/decode and streaming-detokenizer replay checks reproduce the original
  answers exactly. Maximum supervised length is 1,693, below the 4,096 limit.

Known-token replay does not reconstruct historical sampled token streams, which
were not saved. It therefore narrows the runtime concern without proving that
no decoder issue could ever occur. Likewise, these observations do not uniquely
identify why optimizer continuation caused regression.

## Concrete repair prototype

`gateway/event_graph_span_wire.py` is an isolated source-span wire codec. The model
selects ranges in a deterministic lexical source table for entity roles, predicate
subjects and evidence. Code copies exactly those selected substrings and creates
only the referenced entity records. It never reads prose to infer roles, expands
shortened names, merges guessed referents, repairs references or drops bad content.

This removes free-form entity-name/evidence copying and separately declared entity
IDs from the proposed model-output contract. It cannot prevent wrong range choices
or misunderstood roles. Conditions, quantities, event ordering and other semantic
fields remain model outputs, and the existing strict graph validator still runs.
The existing deterministic matrix compiler is unchanged.

Canonical graph meanings survive roundtrips for 744 authored examples (train,
development and the already-exposed v6 test). Eleven new codec tests and the
relevant existing regressions pass: **99 tests in total**. These are software and
representation tests, not a model-accuracy result.

| Serialization measure | Train | Development |
|---|---:|---:|
| Existing answer bytes | 627,176 | 174,837 |
| Prototype answer bytes | 403,763 | 108,212 |
| Answer size reduction | 35.62% | 38.11% |
| Added source-table input bytes | 276,193 | 85,346 |

The prototype reduces repeated output text but adds input overhead. No end-to-end
speed or token saving is claimed.

## Next experiment

The repair design is recorded in
`validation/event_graph_diagnostics/REPAIR_DESIGN.md`. Before another training run,
freeze a new wire prompt/schema and broaden authored training examples for document
headers, complete entity names, multiple participants and explicit role contrasts.
Train the model to select spans and preserve semantic bindings; evaluate that
protocol independently. The old adapter cannot silently be given this new output
contract and judged as though it had been trained for it.

No training was started in this audit. No previous output was repaired or rescored
as a pass, and no matrix or Tree gate advanced. Runtime and structure evidence plus
input/source hashes are saved alongside this report.
