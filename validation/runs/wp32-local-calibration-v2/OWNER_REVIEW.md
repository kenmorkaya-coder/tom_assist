# WP-32 owner review

**POST-HOC LOCAL DIAGNOSTIC — NOT A GATE. The frozen v2 run is unchanged.**

## Plain result

The parser improved the retained corpus from **35/52** strict observations to **45/52**, but the full v2 corpus produced only **67/80** strict observations. It is not ready to activate or freeze.

Direction remained coherent: **58/80** expected relations survived end to end and there were **0 reversals**. Signal recovery reached **17/21**. History bounds passed in **7/8** cases, and all 67 strict observations carried valid bounded 17D shapes.

## Frozen readiness matrix

| Criterion | Value | Required | Met |
|---|---:|---:|---|
| `end_to_end_relation_recall` | 0.725000 | 0.900000 | false |
| `end_to_end_signal_recall` | 0.809524 | 0.800000 | true |
| `history_case_rate` | 0.875000 | 0.875000 | true |
| `load_shape_rate` | 1.000000 | 1.000000 | true |
| `maximum_reversed_relations` | 0.000000 | 0.000000 | true |
| `maximum_unexpected_relation_rate` | 0.093750 | 0.050000 | false |
| `minimum_family_observation_rate` | 0.625000 | 0.750000 | false |
| `multi_relation_exact_rate` | 0.400000 | 0.800000 | false |
| `strict_observation_rate` | 0.837500 | 0.900000 | false |

## Fail-closed taxonomy

- `invalid_tool_json`: 8 — CD-08, LP-05, LP-06, MR-03, PB-04, PB-08, PP-05A, PP-05B
- `missing_evidence_quote`: 3 — M2-01, M2-04, S2-08
- `unbalanced_tool_call`: 1 — PB-07
- `unsupported_entity_kind`: 1 — SG-01

## What improved and what remains

- Previously failing cases recovered: CD-10, LP-01, LP-02, MR-01, MR-02, MR-04, MR-05, OR-03, SG-02, SG-04, SG-06, SG-08.
- Previously strict cases that regressed: LP-06, PP-05B.
- The syntax-only fallback successfully recovered 26 calls; eight JSON-value
  errors and one unbalanced call remained. No raw generated text was retained.
- LP-03 exposed a second overlap issue: the same endpoint labels were assigned
  different evidence granularity, so relation deduplication saw different entity IDs.
- HD-05's persistence result was mechanically correct at 4/6; its frozen 1.0
  expectation was a preregistration mistake and remains scored as a miss.
- Some 'unexpected' relations were plausible extra structure (SG-02, MR-05),
  while MR-06, PB-05 and M2-03 added or transformed relations contrary to the
  fixed ontology. The frozen unexpected-rate failure is therefore retained.

## Recommended next version

Retain v2. Before any new run, version the overlap entity merge, add safe binding
from valid model-supplied offsets when a quote field is absent, and instrument
syntax failure categories without retaining raw prose. Correct the HD-05 case
bound explicitly as a preregistration amendment. Then freeze a v3 corpus and run
only under fresh authorization. Do not activate the parser from this result.
