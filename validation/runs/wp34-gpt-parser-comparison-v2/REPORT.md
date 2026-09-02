# WP-34 GPT parser comparison

**LIVE ENGINEERING COMPARISON — NOT A GATE. No G-gate verdict is issued or implied.**

- Cases: 94
- Explicit provider generations: 97
- Successful structured generations: 77
- Strict observations/parser errors: 75/19
- Expected relations: 76/117
- Reversed/unexpected relations: 0/21
- Expected signals: 19/24
- Valid 17-channel shapes: 75/75

| Metric | GPT | Gemma v3 | Delta |
|---|---:|---:|---:|
| `strict_observation_rate` | 0.797872 | 0.744681 | +0.053191 |
| `minimum_family_observation_rate` | 0.375000 | 0.400000 | -0.025000 |
| `end_to_end_relation_recall` | 0.649573 | 0.666667 | -0.017094 |
| `maximum_reversed_relations` | 0.000000 | 0.000000 | +0.000000 |
| `maximum_unexpected_relation_rate` | 0.216495 | 0.060241 | +0.156254 |
| `end_to_end_signal_recall` | 0.791667 | 0.708333 | +0.083333 |
| `multi_relation_exact_rate` | 0.250000 | 0.437500 | -0.187500 |
| `history_case_rate` | 1.000000 | 1.000000 | +0.000000 |
| `load_shape_rate` | 1.000000 | 1.000000 | +0.000000 |

Pre-registered core improvement: **FALSE**.
Pre-registered safety non-regression: **FALSE**.
GPT better on the pre-registered rule: **FALSE**.

The GPT parser remains candidate-only and inactive pending owner audit. The model supplied quotes and typed facts only; Tom Assist bound offsets and compiled all 17 channels. This run did not advance the Python 10K tree.
