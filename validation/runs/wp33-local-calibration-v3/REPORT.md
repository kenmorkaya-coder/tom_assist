# WP-33 local parser calibration v3

**LOCAL CALIBRATION — NOT A GATE. No G-gate verdict is issued or implied.**

- Cases: 94 (80 retained + 14 added)
- Exact local chunk-model attempts/successes: 123/99
- Provider/OAuth calls: 0
- Strict observations/parser errors: 70/24
- Expected relations: 78/117
- Reversed/unexpected relations: 0/5
- Expected signals: 17/24
- Valid 17-channel shapes: 70/70

| Criterion | Value | Required | Met |
|---|---:|---:|---|
| `strict_observation_rate` | 0.744681 | 0.900000 | false |
| `minimum_family_observation_rate` | 0.400000 | 0.750000 | false |
| `end_to_end_relation_recall` | 0.666667 | 0.900000 | false |
| `maximum_reversed_relations` | 0.000000 | 0.000000 | true |
| `maximum_unexpected_relation_rate` | 0.060241 | 0.050000 | false |
| `end_to_end_signal_recall` | 0.708333 | 0.800000 | false |
| `multi_relation_exact_rate` | 0.437500 | 0.800000 | false |
| `history_case_rate` | 1.000000 | 0.875000 | true |
| `load_shape_rate` | 1.000000 | 1.000000 | true |

Ready for owner consideration of shadow mode: **FALSE**.
This result cannot activate the parser, establish whole-tree efficacy, or pass a G-gate.
