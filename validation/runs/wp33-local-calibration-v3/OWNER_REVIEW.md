# WP-33 owner review

**POST-HOC LOCAL DIAGNOSTIC — NOT A GATE. The frozen v3 run is unchanged.**

## Plain result

V3 parsed **63/80** retained cases, compared with **67/80** in v2. Across the full expanded corpus it parsed **70/94**. It is not ready for shadow mode.

Direction did not reverse, and every accepted result had a valid bounded 17D shape. Those are necessary safety properties, but the parser still dropped too many passages and relations to be useful.

## Frozen readiness matrix

| Criterion | Value | Required | Met |
|---|---:|---:|---|
| `end_to_end_relation_recall` | 0.666667 | 0.900000 | false |
| `end_to_end_signal_recall` | 0.708333 | 0.800000 | false |
| `history_case_rate` | 1.000000 | 0.875000 | true |
| `load_shape_rate` | 1.000000 | 1.000000 | true |
| `maximum_reversed_relations` | 0.000000 | 0.000000 | true |
| `maximum_unexpected_relation_rate` | 0.060241 | 0.050000 | false |
| `minimum_family_observation_rate` | 0.400000 | 0.750000 | false |
| `multi_relation_exact_rate` | 0.437500 | 0.800000 | false |
| `strict_observation_rate` | 0.744681 | 0.900000 | false |

## Fail-closed causes

- `invalid_structured_value`: 17 — CD-05, CD-08, CD-09, M3-05, M3-06, MR-01, MR-06, P3-01, P3-02, PB-07, PP-01A, PP-02B, PP-03A, PP-03B, PP-04A, PP-04B, SG-06
- `malformed_container_type`: 1 — MR-02
- `missing_or_extra_schema_field`: 1 — MR-04
- `unknown_relation_endpoint`: 2 — L3-02, L3-04
- `unsupported_entity_kind`: 1 — SG-01
- `unsupported_relation_vocabulary`: 2 — M2-03, P3-03

## What this means

- Recovered retained cases: LP-05, LP-06, M2-01, M2-04, MR-03, PB-04, PB-08, PP-05A, PP-05B, S2-08.
- Regressed retained cases: CD-05, CD-09, M2-03, MR-01, MR-02, MR-04, MR-06, PP-01A, PP-02B, PP-03A, PP-03B, PP-04A, PP-04B, SG-06.
- The overlap correction worked on the earlier LP-03/LP-06 cases and the history family reached 8/8, but dense coordination and ordinary paraphrases remained fragile.
- Seventeen failures still contained invalid structured values after syntax fallback. Because raw model output was not retained, adding another guessed repair would not be robust.
- The parser remains inactive. The correct Python 10K tree wiring is separately guarded; this failed calibration is about producing reliable inputs for it, not the tree itself.

## Recommended next decision

Do not run v4 yet. First change the local model boundary so constrained structure is produced reliably—for example, a smaller staged extraction with one relation per bounded record or a grammar-constrained decoder—then pre-register a retained comparison. Do not keep adding post-hoc syntax guesses to malformed whole-passage tool calls.
