# WP-32 local parser calibration v2

**LOCAL CALIBRATION — NOT A GATE. No G-gate verdict is issued or implied.**

## Accounting

- Cases: 80 (52 retained + 28 added)
- Logical passage attempts: 99
- Exact local chunk-model attempts/successes: 102/89
- Provider/OAuth calls: 0

## Outcomes

- Strict observations/parser errors: 67/13
- V2 exact cases: 58/80
- Expected relations end to end: 58/80
- Reversed/unexpected relations: 0/6
- Expected signals end to end: 17/21
- Valid 17-channel shapes: 67/80
- Native/fallback parse modes: {'deterministic_gemma4_reparse': 26, 'native': 63}
- Calls with harmless extra-field projection: 9

## Pre-registered readiness criteria

| Criterion | Value | Required | Met |
|---|---:|---:|---|
| `strict_observation_rate` | 0.837500 | 0.900000 | false |
| `minimum_family_observation_rate` | 0.625000 | 0.750000 | false |
| `end_to_end_relation_recall` | 0.725000 | 0.900000 | false |
| `maximum_reversed_relations` | 0.000000 | 0.000000 | true |
| `maximum_unexpected_relation_rate` | 0.093750 | 0.050000 | false |
| `end_to_end_signal_recall` | 0.809524 | 0.800000 | true |
| `multi_relation_exact_rate` | 0.400000 | 0.800000 | false |
| `history_case_rate` | 0.875000 | 0.875000 | true |
| `load_shape_rate` | 1.000000 | 1.000000 | true |

Owner-freeze readiness under this local instrument: **FALSE**.
This is an engineering calibration result only. Activation and production
model freeze remain owner decisions and no G-gate claim is made.
