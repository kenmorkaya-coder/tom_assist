# WP-31 local multi-vector calibration

**LOCAL CALIBRATION — NOT A GATE. No G-gate verdict is issued or implied.**

## Summary

- Cases/local candidate attempts: 52/52
- Observed/parser errors: 35/17
- Exact pre-registered expectations: 33/35
- Expected relation matches: 34/34
- Reversed/unexpected relations: 0/3
- Expected signal matches: 1/3
- Chunk expectations: 34/35
- Valid 17-channel shapes: 35/35
- Provider/OAuth calls: 0

## Cases

| Case | Family | Status | Chunks | Relations | Signals | Reversed | Unexpected | Seconds |
|---|---|---|---:|---:|---:|---:|---:|---:|
| CD-01 | causal_direction | observed | 1 | 1/1 | 0/0 | 0 | 0 | 17.846 |
| CD-02 | causal_direction | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.685 |
| CD-03 | causal_direction | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.843 |
| CD-04 | causal_direction | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.727 |
| CD-05 | causal_direction | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.894 |
| CD-06 | causal_direction | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.726 |
| CD-07 | causal_direction | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.806 |
| CD-08 | causal_direction | parser_error:structureprovidererror | — | — | — | — | — | 7.508 |
| CD-09 | causal_direction | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.843 |
| CD-10 | causal_direction | parser_error:structureprovidererror | — | — | — | — | — | 7.549 |
| OR-01 | orientation | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.897 |
| OR-02 | orientation | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.802 |
| OR-03 | orientation | parser_error:structureprovidererror | — | — | — | — | — | 7.793 |
| OR-04 | orientation | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.868 |
| OR-05 | orientation | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.769 |
| OR-06 | orientation | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.929 |
| OR-07 | orientation | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.913 |
| OR-08 | orientation | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.964 |
| OR-09 | orientation | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.812 |
| OR-10 | orientation | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.755 |
| OR-11 | orientation | observed | 1 | 1/1 | 0/0 | 0 | 0 | 8.151 |
| OR-12 | orientation | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.981 |
| SG-01 | signal | parser_error:structureprovidererror | — | — | — | — | — | 34.062 |
| SG-02 | signal | parser_error:structureprovidererror | — | — | — | — | — | 10.996 |
| SG-03 | signal | observed | 1 | 0/0 | 0/1 | 0 | 1 | 8.522 |
| SG-04 | signal | parser_error:structureprovidererror | — | — | — | — | — | 8.230 |
| SG-05 | signal | observed | 1 | 0/0 | 1/1 | 0 | 0 | 7.110 |
| SG-06 | signal | parser_error:structureprovidererror | — | — | — | — | — | 7.540 |
| SG-07 | signal | observed | 1 | 0/0 | 0/1 | 0 | 0 | 8.130 |
| SG-08 | signal | parser_error:structureprovidererror | — | — | — | — | — | 7.175 |
| MR-01 | multi_relation | parser_error:structureprovidererror | — | — | — | — | — | 9.481 |
| MR-02 | multi_relation | parser_error:structureprovidererror | — | — | — | — | — | 9.072 |
| MR-03 | multi_relation | parser_error:structureprovidererror | — | — | — | — | — | 9.715 |
| MR-04 | multi_relation | parser_error:structureprovidererror | — | — | — | — | — | 9.937 |
| MR-05 | multi_relation | parser_error:structureprovidererror | — | — | — | — | — | 10.763 |
| MR-06 | multi_relation | observed | 1 | 2/2 | 0/0 | 0 | 0 | 9.491 |
| LP-01 | long_position | parser_error:structureprovidererror | — | — | — | — | — | 13.565 |
| LP-02 | long_position | parser_error:structureprovidererror | — | — | — | — | — | 14.220 |
| LP-03 | long_position | observed | 2 | 1/1 | 0/0 | 0 | 1 | 15.973 |
| LP-04 | long_position | observed | 1 | 2/2 | 0/0 | 0 | 0 | 10.199 |
| LP-05 | long_position | parser_error:structureprovidererror | — | — | — | — | — | 19.329 |
| LP-06 | long_position | observed | 2 | 1/1 | 0/0 | 0 | 1 | 15.966 |
| PP-01A | paraphrase | observed | 1 | 1/1 | 0/0 | 0 | 0 | 8.094 |
| PP-01B | paraphrase | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.894 |
| PP-02A | paraphrase | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.351 |
| PP-02B | paraphrase | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.800 |
| PP-03A | paraphrase | observed | 1 | 1/1 | 0/0 | 0 | 0 | 8.042 |
| PP-03B | paraphrase | observed | 1 | 1/1 | 0/0 | 0 | 0 | 8.562 |
| PP-04A | paraphrase | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.362 |
| PP-04B | paraphrase | observed | 1 | 1/1 | 0/0 | 0 | 0 | 7.843 |
| PP-05A | paraphrase | parser_error:structureprovidererror | — | — | — | — | — | 8.203 |
| PP-05B | paraphrase | observed | 1 | 1/1 | 0/0 | 0 | 0 | 8.112 |

## Paraphrase pairs

| Pair | Status | Semantic | 17D L1 | Graph equal | Ranks A→B/B→A |
|---|---|---:|---:|---|---|
| PP-01 | observed | 0.976266 | 0.000000 | true | 1/1 |
| PP-02 | observed | 0.908415 | 0.000000 | true | 2/1 |
| PP-03 | observed | 0.885888 | 0.194033 | true | 1/1 |
| PP-04 | observed | 0.960126 | 0.000000 | true | 1/1 |
| PP-05 | unavailable_parser_error | — | — | — | — |

The compact JSONL observation file contains the exact mismatches, evidence spans,
17D values, hashes and timing for owner review. It deliberately contains no 384D
vectors, model weights, runtime trees, databases or provider content.
