# WP-29 Appendix C — frozen pre-registration v3 pilot v4

> PILOT OUTCOME ONLY. This report issues no specification G-gate verdict.

## Run identity

```json
{
  "captures": 165,
  "code_sha": "5ac4849d029da8d29240d33936644e8c944b2387",
  "completed": true,
  "freeze_sha256": "sha256:a02192b0f04646d2d2a740783fbabb98fc87cc842f2c2e97b2c176c8d35940cd",
  "logical_calls_claimed": 165,
  "observations_disposed": 165,
  "run_id": "wp29-pilot-v4",
  "unknown_outcomes": 0
}
```

## Substrate engagement

> Execution telemetry only: this establishes that the corrected ToM substrate was exercised; it is not an efficacy or G-gate verdict.

```json
{
  "all_rows_fully_engaged": true,
  "assistant_teaches": 5720,
  "assistant_turns": 5720,
  "canonical_17_channel_applications": 15345,
  "checkpoint_changed_rows": 165,
  "five_dynamics_receipts": 15345,
  "history_import_provider_calls": 0,
  "history_turns": 15345,
  "label": "EXECUTION-TELEMETRY-NOT-EFFICACY",
  "routing_basis_8d_applications": 15345,
  "rows_fully_engaged": 165,
  "rows_observed": 165,
  "tick_delta": 15345
}
```

## Observation dispositions and wall time

```json
{
  "captured": 165,
  "complete_cases": 33,
  "excluded_case_ids": [],
  "unknown_outcome_cap": 8,
  "unknown_outcomes": 0,
  "wall_time_seconds": {
    "count": 165,
    "max": 272.679774,
    "median": 202.930279,
    "min": 25.176463,
    "p95": 260.51110679999994,
    "total": 26900.464179
  }
}
```

| # | Test ID | Arm | Disposition | Wall seconds | Reason |
|---:|---|---|---|---:|---|
| — | — | — | no unknown outcomes | — | — |

## Frozen-hypothesis resolution

- **H1:** DOES_NOT_HOLD
- **H0:** HOLDS
- **H2:** NOT_TRIGGERED_REQUIRES_H1
- **H3:** NOT_OBSERVED

```json
{
  "H0": {
    "criterion": "one or more frozen H1 primary components does not hold",
    "outcome": "HOLDS"
  },
  "H1": {
    "components": {
      "complete_matrix": true,
      "sub_d_at_least_0.80_every_family": false,
      "sub_d_minus_sub_a_at_least_0.15": false,
      "sub_d_minus_sub_b_at_least_0.15": false,
      "sub_d_vs_sub_a_ci_excludes_zero_positive": false,
      "sub_d_vs_sub_b_ci_excludes_zero_positive": false
    },
    "outcome": "DOES_NOT_HOLD"
  },
  "H2": {
    "components": {
      "H2.1_no_rot_rate_within_0.05_of_A": true,
      "H2.1_zero_gratuitous_injections": false,
      "H2.2_long_D_within_0.05_of_C": true,
      "H2.3_D_exceeds_E_by_0.10_or_containment": false,
      "H2.4_supersession_D_at_least_0.80": null
    },
    "outcome": "NOT_TRIGGERED_REQUIRES_H1"
  },
  "H3": {
    "outcome": "NOT_OBSERVED",
    "rows": []
  },
  "cluster_bootstrap": {
    "SUB-A": {
      "baseline": "SUB-A",
      "ci95": [
        0.0,
        0.0
      ],
      "invalid_replicates": 7409,
      "replicates": 10000,
      "seed": 1729,
      "valid_replicates": 2591
    },
    "SUB-B": {
      "baseline": "SUB-B",
      "ci95": [
        -0.18181818181818182,
        0.0
      ],
      "invalid_replicates": 7409,
      "replicates": 10000,
      "seed": 1729,
      "valid_replicates": 2591
    }
  },
  "family_long_rates": {
    "ASSUMPTION": {
      "SUB-A": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-B": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-C": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-D": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-E": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      }
    },
    "COMPLETED_WORK": {
      "SUB-A": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-B": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-C": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-D": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-E": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      }
    },
    "CONCEPT": {
      "SUB-A": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-B": {
        "denominator": 2,
        "numerator": 1,
        "rate": 0.5
      },
      "SUB-C": {
        "denominator": 2,
        "numerator": 1,
        "rate": 0.5
      },
      "SUB-D": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-E": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      }
    },
    "CONSTRAINT": {
      "SUB-A": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-B": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-C": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-D": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-E": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      }
    },
    "DECISION": {
      "SUB-A": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-B": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-C": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-D": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-E": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      }
    },
    "EVIDENCE": {
      "SUB-A": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-B": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-C": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-D": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-E": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      }
    },
    "OBJECTIVE": {
      "SUB-A": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-B": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-C": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-D": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-E": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      }
    },
    "REJECTED_PATH": {
      "SUB-A": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-B": {
        "denominator": 2,
        "numerator": 1,
        "rate": 0.5
      },
      "SUB-C": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-D": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-E": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      }
    },
    "SUPERSESSION": {
      "SUB-A": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-B": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-C": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-D": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-E": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      }
    },
    "UNRESOLVED_DEPENDENCY": {
      "SUB-A": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-B": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-C": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-D": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-E": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      }
    },
    "WORKSTREAM": {
      "SUB-A": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-B": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-C": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-D": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-E": {
        "denominator": 2,
        "numerator": 0,
        "rate": 0.0
      }
    }
  },
  "macro_long_rates": {
    "SUB-A": 0.0,
    "SUB-B": 0.09090909090909091,
    "SUB-C": 0.045454545454545456,
    "SUB-D": 0.0,
    "SUB-E": 0.0
  },
  "paired_differences": {
    "SUB-D_minus_SUB-A": 0.0,
    "SUB-D_minus_SUB-B": -0.09090909090909091
  },
  "v3_validity": {
    "complete_case_ids": [
      "D23-ASSUMPTION-01",
      "D23-ASSUMPTION-02",
      "D23-ASSUMPTION-11",
      "D23-COMPLETED_WORK-01",
      "D23-COMPLETED_WORK-02",
      "D23-COMPLETED_WORK-11",
      "D23-CONCEPT-01",
      "D23-CONCEPT-02",
      "D23-CONCEPT-11",
      "D23-CONSTRAINT-01",
      "D23-CONSTRAINT-02",
      "D23-CONSTRAINT-11",
      "D23-DECISION-01",
      "D23-DECISION-02",
      "D23-DECISION-11",
      "D23-EVIDENCE-01",
      "D23-EVIDENCE-02",
      "D23-EVIDENCE-11",
      "D23-OBJECTIVE-01",
      "D23-OBJECTIVE-02",
      "D23-OBJECTIVE-11",
      "D23-REJECTED_PATH-01",
      "D23-REJECTED_PATH-02",
      "D23-REJECTED_PATH-11",
      "D23-SUPERSESSION-01",
      "D23-SUPERSESSION-02",
      "D23-SUPERSESSION-11",
      "D23-UNRESOLVED_DEPENDENCY-01",
      "D23-UNRESOLVED_DEPENDENCY-02",
      "D23-UNRESOLVED_DEPENDENCY-11",
      "D23-WORKSTREAM-01",
      "D23-WORKSTREAM-02",
      "D23-WORKSTREAM-11"
    ],
    "complete_cases": 33,
    "excluded_case_ids": [],
    "excluded_cases": 0,
    "h1_interpretable_min_complete_cases": 30,
    "selected_cases_reached": 33,
    "unknown_outcomes": 0
  }
}
```

## Paired-analysis exact action consistency by focus family

| Focus family | SUB-A | SUB-B | SUB-C | SUB-D | SUB-E |
|---|---|---|---|---|---|
| ASSUMPTION | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| COMPLETED_WORK | 0/3 (0.000) | 0/3 (0.000) | 1/3 (0.333) | 0/3 (0.000) | 0/3 (0.000) |
| CONCEPT | 0/3 (0.000) | 1/3 (0.333) | 1/3 (0.333) | 0/3 (0.000) | 0/3 (0.000) |
| CONSTRAINT | 0/3 (0.000) | 0/3 (0.000) | 1/3 (0.333) | 0/3 (0.000) | 0/3 (0.000) |
| DECISION | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| EVIDENCE | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| OBJECTIVE | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| REJECTED_PATH | 0/3 (0.000) | 2/3 (0.667) | 0/3 (0.000) | 1/3 (0.333) | 0/3 (0.000) |
| SUPERSESSION | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| UNRESOLVED_DEPENDENCY | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| WORKSTREAM | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |

## Paired-analysis exact action consistency by slice

| Slice | SUB-A | SUB-B | SUB-C | SUB-D | SUB-E |
|---|---|---|---|---|---|
| no_rot | 0/11 (0.000) | 1/11 (0.091) | 2/11 (0.182) | 1/11 (0.091) | 0/11 (0.000) |
| truncation | 0/22 (0.000) | 2/22 (0.091) | 1/22 (0.045) | 0/22 (0.000) | 0/22 (0.000) |

## Paired-analysis exact action consistency by domain

| Domain | SUB-A | SUB-B | SUB-C | SUB-D | SUB-E |
|---|---|---|---|---|---|
| archive | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| catalog | 0/3 (0.000) | 0/3 (0.000) | 1/3 (0.333) | 0/3 (0.000) | 0/3 (0.000) |
| dataset | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| game | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) |
| garden | 0/3 (0.000) | 1/3 (0.333) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| library | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| release | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) |
| robot | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| sensor | 0/3 (0.000) | 2/3 (0.667) | 1/3 (0.333) | 1/3 (0.333) | 0/3 (0.000) |
| subtitle | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) |
| theatre | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| workshop | 0/3 (0.000) | 0/3 (0.000) | 1/3 (0.333) | 0/3 (0.000) | 0/3 (0.000) |

## Failure taxonomy (paired-analysis cases)

| Failure | SUB-A | SUB-B | SUB-C | SUB-D | SUB-E | Total |
|---|---:|---:|---:|---:|---:|---:|
| citation-list inequality | 25 | 7 | 0 | 25 | 11 | 68 |
| completed-work reproposal | 2 | 0 | 0 | 2 | 0 | 4 |
| constraint violation | 1 | 0 | 0 | 2 | 0 | 3 |
| dependency ignored | 2 | 0 | 0 | 2 | 0 | 4 |
| enumeration/format failure | 20 | 0 | 0 | 25 | 0 | 45 |
| evidence overstatement/assumption promotion | 4 | 0 | 0 | 5 | 0 | 9 |
| objective/workstream substitution | 4 | 0 | 0 | 5 | 0 | 9 |
| rejected-path revival | 2 | 0 | 0 | 2 | 0 | 4 |
| supersession/history loss | 22 | 2 | 0 | 26 | 11 | 61 |
| wrong action | 3 | 0 | 0 | 5 | 0 | 8 |
| wrong relationship direction | 32 | 30 | 30 | 32 | 11 | 135 |

## Full raw observation matrix

| # | Test ID | Family | Slice | Domain | Arm | Disposition | Wall seconds | Exact | SUB-E containment | Shape | Evaluation | Gratuitous | Failures | Prompt SHA | Response SHA |
|---:|---|---|---|---|---|---|---:|---|---|---|---|---|---|---|---|
| 1 | D23-ASSUMPTION-01 | ASSUMPTION | truncation | robot | SUB-A | captured | 171.457419 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:c169924eda1fc7e5e52a7a2146e4cd7b371a34dea4155a4a1b38cc9d898cfc8f | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 2 | D23-ASSUMPTION-01 | ASSUMPTION | truncation | robot | SUB-B | captured | 197.024598 | false | false | true | REVIEW | false | citation-list inequality, wrong relationship direction | sha256:9a4d78315d51efe9db250303e80a409521f24fe19b173ac524bd69e9684fa43b | sha256:4f4ee502f3a6b55cc6386cb162cf5708138a40e6d3ce215d1e1cf2e63b71fb4a |
| 3 | D23-ASSUMPTION-01 | ASSUMPTION | truncation | robot | SUB-C | captured | 184.756350 | false | false | true | REVIEW | false | wrong relationship direction | sha256:4f219fa11576af1d31026b8b2a7eb6ab8ed198d9d1c2894b38af2ad22ec8253a | sha256:8704086b04281d4a5e909fb6e8fcc23f2bae61a46f28fa2b26b7a1570773aa09 |
| 4 | D23-ASSUMPTION-01 | ASSUMPTION | truncation | robot | SUB-D | captured | 177.563428 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:373d8ce59c6ce04043cc0feb02442f990a6864031175a87002463cfa26306857 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 5 | D23-ASSUMPTION-01 | ASSUMPTION | truncation | robot | SUB-E | captured | 179.950242 | false | true | true | REVIEW | false | none | sha256:16955c6d98ea71741d959e2152ce3949c7d98e7813fdad7cf0f2cec9a727604f | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 6 | D23-ASSUMPTION-02 | ASSUMPTION | truncation | subtitle | SUB-B | captured | 257.813286 | false | false | true | REVIEW | false | citation-list inequality, wrong relationship direction | sha256:bbac99e608d6a0b304f1f02c5264f805f84daa22e9be90ffc072891f0d8a8431 | sha256:de8c2fc7588fb7fb927ccca2e4d11ba5080509ae907fecf29abfb61f80959a36 |
| 7 | D23-ASSUMPTION-02 | ASSUMPTION | truncation | subtitle | SUB-C | captured | 237.135953 | false | false | true | REVIEW | false | wrong relationship direction | sha256:f7ee23cceb782f1f68e340fc94cdec54bf98b7e9c1ef48793b6794f3fb061858 | sha256:899792bfaaeb120dde44faa22fa33f77853f34d7c4c8e67709fd41798382a2da |
| 8 | D23-ASSUMPTION-02 | ASSUMPTION | truncation | subtitle | SUB-D | captured | 241.958461 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:4182de13c041eb2d62ca239fd1b7a90a2d036f948ce38d80dafb0cc40c2f61b3 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 9 | D23-ASSUMPTION-02 | ASSUMPTION | truncation | subtitle | SUB-E | captured | 235.197846 | false | false | true | REVIEW | false | citation-list inequality, supersession/history loss, wrong relationship direction | sha256:58548b0afbfd1b3ea3a5648f6be0420b65ce2e1490c04f98b27e4193f99aa543 | sha256:1f18c9d074573978faa32046901d06fc565065005f103e9781efffa96b93e3dd |
| 10 | D23-ASSUMPTION-02 | ASSUMPTION | truncation | subtitle | SUB-A | captured | 226.989189 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:6479c436ffa0088cec79e7b59a19813b99e4885b3a3ea411108daae9c8582cd9 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 11 | D23-ASSUMPTION-11 | ASSUMPTION | no_rot | theatre | SUB-C | captured | 112.704325 | false | false | true | REVIEW | false | wrong relationship direction | sha256:a7f23133c78714fa1242d509b0d18918695318c2a3633c0836de65f68583a7a2 | sha256:1216189e18f82dd6852e9db19465249e8fe9d6a4f5e7e080c201febf6730de7b |
| 12 | D23-ASSUMPTION-11 | ASSUMPTION | no_rot | theatre | SUB-D | captured | 39.507304 | false | false | true | REVIEW | true | citation-list inequality, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:a72030651c4e51a1298d95d314a11104bb073becd5617016f0ab01243ae1ed0e | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 13 | D23-ASSUMPTION-11 | ASSUMPTION | no_rot | theatre | SUB-E | captured | 28.212776 | false | true | true | REVIEW | false | none | sha256:3fc6c9e261eb673ab4a8072b08801b6b12c5167a89b4432b595b64013c269f82 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 14 | D23-ASSUMPTION-11 | ASSUMPTION | no_rot | theatre | SUB-A | captured | 40.518527 | false | false | true | REVIEW | false | wrong relationship direction | sha256:f3c2cbcb02f70812c4e37b12a0d85573379a5fef836605c526e5726e4f4c57f3 | sha256:3af79b1ac5de28e32a0f3d52d007d120d7c22be54f8b3a7ead736b2187d721b2 |
| 15 | D23-ASSUMPTION-11 | ASSUMPTION | no_rot | theatre | SUB-B | captured | 52.364235 | false | false | true | REVIEW | false | wrong relationship direction | sha256:6a6f353aa2624989b5947cd934892c2546a9770e1c31aad795be19740c64cb4f | sha256:a1d965185a34c932a1d4fdc70b216243789cbeeb09926aa52fbdad81b32541f9 |
| 16 | D23-COMPLETED_WORK-01 | COMPLETED_WORK | truncation | garden | SUB-D | captured | 196.706494 | false | false | true | REVIEW | false | citation-list inequality, completed-work reproposal, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:204421c8943530149db5c12689e4494edbef481834ac37b27cf05c4af07f8ee2 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 17 | D23-COMPLETED_WORK-01 | COMPLETED_WORK | truncation | garden | SUB-E | captured | 189.233105 | false | true | true | REVIEW | false | none | sha256:40da02e6a3b36853d04e5369b5a1f73663bdd6ce77ad9d00550d33c62936d389 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 18 | D23-COMPLETED_WORK-01 | COMPLETED_WORK | truncation | garden | SUB-A | captured | 200.285466 | false | false | true | REVIEW | false | citation-list inequality, completed-work reproposal, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:332798c8df1d3b6b9287fd8c05fd5f67ba72542eaa8d31fef7cbf042f9cd558f | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 19 | D23-COMPLETED_WORK-01 | COMPLETED_WORK | truncation | garden | SUB-B | captured | 212.976583 | false | false | true | REVIEW | false | wrong relationship direction | sha256:866691a09ea3b376f84d32465e9d2a1a8620012c3555c44051fffe30af817c92 | sha256:3717316015856ed7d156f25e11932f27922e60dabd6df8dc88d1297d85be4f9d |
| 20 | D23-COMPLETED_WORK-01 | COMPLETED_WORK | truncation | garden | SUB-C | captured | 209.337093 | false | false | true | REVIEW | false | wrong relationship direction | sha256:9bf4887ccafacbb17d54ff140ca38ffca38dfc21e63e8a1869b711c6c5808550 | sha256:d311a09e47f3d5dee2a611d6e5e7734728505f22503e76f5128210a26ebe6982 |
| 21 | D23-COMPLETED_WORK-02 | COMPLETED_WORK | truncation | theatre | SUB-E | captured | 249.113573 | false | false | true | REVIEW | false | citation-list inequality, supersession/history loss, wrong relationship direction | sha256:5c627360ae0d8415a4e282000bb38de4bed5ec0fc02920c2b2426537ddccb364 | sha256:4997b94730a1c6fa7e5747265c6d14f2491ff5c4ac8917284ff92dad8abfadb8 |
| 22 | D23-COMPLETED_WORK-02 | COMPLETED_WORK | truncation | theatre | SUB-A | captured | 232.850630 | false | false | true | REVIEW | false | citation-list inequality, completed-work reproposal, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:2993d7f09191d02bf137642cc4a40d8bfa23c928ca3732de89f11599c0aa3deb | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 23 | D23-COMPLETED_WORK-02 | COMPLETED_WORK | truncation | theatre | SUB-B | captured | 269.721686 | false | false | true | REVIEW | false | wrong relationship direction | sha256:a6f9b26e477fb25fba3c0f99391e6fa6a8fcc081b9413c0342dd58ec031103d2 | sha256:81dcb7c9ac29642959af8a12c117e419ad5b63eea0f9331d6668774f57c824a1 |
| 24 | D23-COMPLETED_WORK-02 | COMPLETED_WORK | truncation | theatre | SUB-C | captured | 243.337665 | false | false | true | REVIEW | false | wrong relationship direction | sha256:6c963883ff85973c428324690ab047923e5e0793ac8655b084a4c96de36a8be9 | sha256:7b995e6a5dd38b350f7e110c7dd99b28a49565890287fbe5c806847c3f9acb0d |
| 25 | D23-COMPLETED_WORK-02 | COMPLETED_WORK | truncation | theatre | SUB-D | captured | 242.778181 | false | false | true | REVIEW | false | citation-list inequality, completed-work reproposal, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:b79d138b03bcc03783d8c00adad319a9da0a84709266f2546a20b51b1e8146ef | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 26 | D23-COMPLETED_WORK-11 | COMPLETED_WORK | no_rot | workshop | SUB-A | captured | 46.133622 | false | false | true | REVIEW | false | wrong relationship direction | sha256:bf99e819ee566dd370b4f0a2ff9a26b826f5a5f372e2e2f40756dfc97947b7c3 | sha256:c03fcb26cf35b5f9c960d838f0706ca1db0069d7503826b74597c77f30e573bd |
| 27 | D23-COMPLETED_WORK-11 | COMPLETED_WORK | no_rot | workshop | SUB-B | captured | 59.752221 | false | false | true | REVIEW | false | wrong relationship direction | sha256:9b81a6a0b50909b11b7d110505f80f1b68a8ac91f2fbf28ce9519444a4e5859a | sha256:004b021fba5db56c96618a419a5dc54d8cdb8a6368dc0566dbdd5052e996beca |
| 28 | D23-COMPLETED_WORK-11 | COMPLETED_WORK | no_rot | workshop | SUB-C | captured | 39.852000 | true | false | true | REVIEW | false | none | sha256:98e589530abe9de19aa6746851374f0024298392ea6ae6b6751ce9b98c7ca6b0 | sha256:46725fc231d52346a6b80c6f9eb428d9fea72025cc58dee6c24acffb9fd57714 |
| 29 | D23-COMPLETED_WORK-11 | COMPLETED_WORK | no_rot | workshop | SUB-D | captured | 42.809329 | false | false | true | REVIEW | true | wrong relationship direction | sha256:98cfe3a8a187c57abf97678e41f1dfb9b2340d8e56e645818427dbb2319b135e | sha256:9d355f5d7f8ddffba11cce1de02b5237f1c054c173762363cb406804e834c31a |
| 30 | D23-COMPLETED_WORK-11 | COMPLETED_WORK | no_rot | workshop | SUB-E | captured | 34.991431 | false | true | true | REVIEW | false | none | sha256:330a08db25ec5e9ebfc73f825d8bd994cc52a50f9dc20f1fe619fdf4ded7bfbf | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 31 | D23-CONCEPT-01 | CONCEPT | truncation | catalog | SUB-B | captured | 207.640989 | false | false | true | REVIEW | false | wrong relationship direction | sha256:db5849ca4f106717440a2049762e3fd29b2f74e029fb3d5cca04684e0879de36 | sha256:6cf69fa028a4a6f66ecb0c01be4063ff3411224ba524f738f36e21f50afa36f6 |
| 32 | D23-CONCEPT-01 | CONCEPT | truncation | catalog | SUB-C | captured | 206.684139 | false | false | true | REVIEW | false | wrong relationship direction | sha256:71759c58d13b2d059475ebae9d1b4e06c6ef3d7e0d43e7b6da4c5009a18ad638 | sha256:a08666eb91243f00ede00560f292533ebbb4b5e7deb4baee97a7f6a020e19b6b |
| 33 | D23-CONCEPT-01 | CONCEPT | truncation | catalog | SUB-D | captured | 202.280046 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, supersession/history loss, wrong action, wrong relationship direction | sha256:610628def3c2608c701c4b03e8ddea32b950cb8dae0faf9cac87812f4ed4a0b2 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 34 | D23-CONCEPT-01 | CONCEPT | truncation | catalog | SUB-E | captured | 191.906874 | false | true | true | REVIEW | false | none | sha256:af58419b30694828632dbdc118498962b8b53b59ab9b70c5ac3e8bc15622b3f9 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 35 | D23-CONCEPT-01 | CONCEPT | truncation | catalog | SUB-A | captured | 200.480923 | false | false | true | REVIEW | false | citation-list inequality, supersession/history loss, wrong relationship direction | sha256:a122555e43725fd42479e5bfd085cf2239cb0b94da7accf2838ceb20a7ba83cd | sha256:2bcbea219e2bf1e2ca47ed2e3c19e9c285f91374066c50856ca7cdf955072df6 |
| 36 | D23-CONCEPT-02 | CONCEPT | truncation | sensor | SUB-C | captured | 238.801168 | true | false | true | REVIEW | false | none | sha256:645b11ce9dc0972bb04189ac74172b04448ec2331b8e275797f5e2cfdd843516 | sha256:b7ad826060ecfc2144435132ca9718c5cab59c00d5de1bbd133ad0e8f3643869 |
| 37 | D23-CONCEPT-02 | CONCEPT | truncation | sensor | SUB-D | captured | 228.754006 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, supersession/history loss, wrong action, wrong relationship direction | sha256:a262c8872fccf553a91cb059f3109b36a89008041872d18dd0d69296b8382255 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 38 | D23-CONCEPT-02 | CONCEPT | truncation | sensor | SUB-E | captured | 241.953983 | false | false | true | REVIEW | false | citation-list inequality, supersession/history loss, wrong relationship direction | sha256:355c54da77687e016ecb2f843535036f6190464e46b2eecc7c02ce5af12a06df | sha256:c870c55e09ee8c8e1113b0f8dc27847f416c1f00f721e7dcfcb0dc73e1b03436 |
| 39 | D23-CONCEPT-02 | CONCEPT | truncation | sensor | SUB-A | captured | 230.858558 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, supersession/history loss, wrong action, wrong relationship direction | sha256:7e3fbee2439275ac09737e68341fc361f9677d2760927ed23717b5890d42f663 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 40 | D23-CONCEPT-02 | CONCEPT | truncation | sensor | SUB-B | captured | 245.758750 | true | false | true | REVIEW | false | none | sha256:e4a1d7b46353eb77c99aec019c1482fe5fc1371695e9f01153df2421252de532 | sha256:10ee2ea01d5771fccbf1e1d51fd0d4f12c2282935fa33d62df38662ebfec79ef |
| 41 | D23-CONCEPT-11 | CONCEPT | no_rot | game | SUB-D | captured | 44.433761 | false | false | true | REVIEW | true | citation-list inequality, enumeration/format failure, supersession/history loss, wrong action, wrong relationship direction | sha256:13dbfc2af9452a656694d4d5258618ccafeef33d423899d072b4374e3f61e746 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 42 | D23-CONCEPT-11 | CONCEPT | no_rot | game | SUB-E | captured | 30.220499 | false | true | true | REVIEW | false | none | sha256:f7a294a531dee7729a385c0a4d5ab4121ec89801b46d4e948808b7b4ca0f56f0 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 43 | D23-CONCEPT-11 | CONCEPT | no_rot | game | SUB-A | captured | 38.171015 | false | false | true | REVIEW | false | wrong relationship direction | sha256:97508e33028ebd21de7a66ffabc09f2989c7fe0636412dfb2c6c647c3b8b72da | sha256:8b9b358d04690389a00f73df92434b00dd4ad84caac6534f490978765a26af12 |
| 44 | D23-CONCEPT-11 | CONCEPT | no_rot | game | SUB-B | captured | 44.447951 | false | false | true | REVIEW | false | wrong relationship direction | sha256:7eec0b9c4a733bca584e169a7c32a994d9c3a4ce588714e7dfc6c31f79bddff3 | sha256:8a90f933751f31f0e3cce92e956195b947c42e0858133aedeafb8592759f0555 |
| 45 | D23-CONCEPT-11 | CONCEPT | no_rot | game | SUB-C | captured | 35.085683 | false | false | true | REVIEW | false | wrong relationship direction | sha256:97fb5b0bfc080cc2fa8b37264c1858110789564cf94c48fbe440aafa740d63bd | sha256:e3139a75761fc9e6295ff27350df29d65ddc7a0230965de42b29094c87b70f4f |
| 46 | D23-CONSTRAINT-01 | CONSTRAINT | truncation | workshop | SUB-E | captured | 188.978255 | false | true | true | REVIEW | false | none | sha256:d8c03e7f14334fabd3c954629a7b19fc99be714099adf012f30fbd2d83d4d03e | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 47 | D23-CONSTRAINT-01 | CONSTRAINT | truncation | workshop | SUB-A | captured | 197.406874 | false | false | true | REVIEW | false | citation-list inequality, constraint violation, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:b556c9ccd05fa13193bf48157a4c874554d3f013116026ee514796a7c924d0e5 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 48 | D23-CONSTRAINT-01 | CONSTRAINT | truncation | workshop | SUB-B | captured | 209.868887 | false | false | true | REVIEW | false | wrong relationship direction | sha256:7a0847e0dafc18826ecd67cbc48ee0befb5166aa6b658e511c76393269e3eec3 | sha256:149abff3274c115c1261b23de5afa0d51dace80c69f7fe914bfbb766cf1d75b6 |
| 49 | D23-CONSTRAINT-01 | CONSTRAINT | truncation | workshop | SUB-C | captured | 209.578011 | false | false | true | REVIEW | false | wrong relationship direction | sha256:6956f86e2f481a4721d7c08186ec15e9e250134eb2ec56b7acfe4e6bf697347d | sha256:50772724212c1b8b67abcb1ad3a6ac2fffc32cb2a2337ffc25d222041830bbbb |
| 50 | D23-CONSTRAINT-01 | CONSTRAINT | truncation | workshop | SUB-D | captured | 195.094388 | false | false | true | REVIEW | false | citation-list inequality, constraint violation, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:fb7664849cf366fb9cf5b0ed380543550c1eeca46c4ecf9fbad97f2946edb298 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 51 | D23-CONSTRAINT-02 | CONSTRAINT | truncation | archive | SUB-A | captured | 239.450339 | false | false | true | REVIEW | false | citation-list inequality, supersession/history loss, wrong relationship direction | sha256:7f5790267653c9bc27223c60bb20b4fb4c8dde790871e1de29cc38be773c8b87 | sha256:464827756ef7e6dffb1d5659dcb4dd44a35e15adf516cd03e22134fff1054fe4 |
| 52 | D23-CONSTRAINT-02 | CONSTRAINT | truncation | archive | SUB-B | captured | 242.045599 | false | false | true | REVIEW | false | wrong relationship direction | sha256:d1a12b67bc0c51381dcd2f3e13318f6b1a9fddbeb5220d0b4d32cd552fa5805f | sha256:b661b87f8c545047ae9cd71d40c2881990c7889d132776edcaad30e437ffb113 |
| 53 | D23-CONSTRAINT-02 | CONSTRAINT | truncation | archive | SUB-C | captured | 236.208855 | false | false | true | REVIEW | false | wrong relationship direction | sha256:ec0b3a1e73eceb6acd3b8d18bd12d720b18a87305a2b4e15ecee919f4890af87 | sha256:5a2fb7c70ee3e7000384875ecb68f3cb86ea7eca6b7a45ba1871fd87844b89b4 |
| 54 | D23-CONSTRAINT-02 | CONSTRAINT | truncation | archive | SUB-D | captured | 231.355769 | false | false | true | REVIEW | false | citation-list inequality, constraint violation, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:3a969b6ea87461d7e10b439a8eec555871a56463a5b11893bcd699b2483b41d4 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 55 | D23-CONSTRAINT-02 | CONSTRAINT | truncation | archive | SUB-E | captured | 240.303146 | false | false | true | REVIEW | false | citation-list inequality, supersession/history loss, wrong relationship direction | sha256:7a6052724a0adf9f27f9644cc5391fd7061d141247845bbf437db83c90b48d93 | sha256:28a9524363e006f1d12f7038355d8033c7ac4815164cff4ff4da9c9a6f77dcf6 |
| 56 | D23-CONSTRAINT-11 | CONSTRAINT | no_rot | catalog | SUB-B | captured | 47.751487 | false | false | true | REVIEW | false | wrong relationship direction | sha256:b5ad5d145b5333a6b298206ef545e354d58d91286e3f1e8cc4371517947f0271 | sha256:8d866cacbdd78a95f0e9521b7e18dd3642fc0835420e68cec6b3fd1503887839 |
| 57 | D23-CONSTRAINT-11 | CONSTRAINT | no_rot | catalog | SUB-C | captured | 37.284891 | true | false | true | REVIEW | false | none | sha256:f8678022151fbe91f5a711f79a56b715befd772725ab90be71db3f711c84229a | sha256:92d91b15ead14113185b20bebaf43785083734bd673c9cdfd49b8ea8c3442da2 |
| 58 | D23-CONSTRAINT-11 | CONSTRAINT | no_rot | catalog | SUB-D | captured | 35.695976 | false | false | true | REVIEW | true | wrong relationship direction | sha256:9a459409b20b34c8781ccf6a7f2710c0ad8e2491927bd596ac940c0d8cff91c6 | sha256:1cde5aec101e19cbdbd735be5223140220cb9eda558f0857b67742a2257fb3f2 |
| 59 | D23-CONSTRAINT-11 | CONSTRAINT | no_rot | catalog | SUB-E | captured | 27.304123 | false | true | true | REVIEW | false | none | sha256:276b53a1dfe7a53c1fc06fb2e04bc11817903b586b0af84ae2f07e782831bc4f | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 60 | D23-CONSTRAINT-11 | CONSTRAINT | no_rot | catalog | SUB-A | captured | 41.936245 | false | false | true | REVIEW | false | citation-list inequality, wrong relationship direction | sha256:c555c445fef9f1c420371ddf7da774c649e4e6f6a4fb2791b25c7df34c158d18 | sha256:7c4ea440d2e630663b22f51e883a5e661baa5893324ccce4cb1a8736a5688b13 |
| 61 | D23-DECISION-01 | DECISION | truncation | sensor | SUB-C | captured | 207.734951 | false | false | true | REVIEW | false | wrong relationship direction | sha256:aaecd24bb995f748e0957e60ffda4244c1723c9db4f2b0a4814eb7631ebe26be | sha256:987bc1f400f0899a28e595d135db32f445814e36ec1cae684867a556c9bab427 |
| 62 | D23-DECISION-01 | DECISION | truncation | sensor | SUB-D | captured | 220.506350 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, supersession/history loss, wrong action, wrong relationship direction | sha256:abab94b1eee9fa1525369c60367f79626d530b118892a6e7b6fcfcd49ce77584 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 63 | D23-DECISION-01 | DECISION | truncation | sensor | SUB-E | captured | 188.939646 | false | true | true | REVIEW | false | none | sha256:0cd819f28b0d85c0283b6b9672d4a57ce92156467d3aa1d60139ff6a60322879 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 64 | D23-DECISION-01 | DECISION | truncation | sensor | SUB-A | captured | 192.501879 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, supersession/history loss, wrong action, wrong relationship direction | sha256:3042bd2a78706495f0ca8b3c61a893da62ed50519c70b6fb79972f21558647e3 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 65 | D23-DECISION-01 | DECISION | truncation | sensor | SUB-B | captured | 200.358464 | false | false | true | REVIEW | false | wrong relationship direction | sha256:947410d09a2fd626d7b60411da8386a8faa5524481fce89038902f1ed4a57426 | sha256:500db6cd6fa8215dea05d004b947d0647e95a1eefc161aeb6f5f2da3db5b88c7 |
| 66 | D23-DECISION-02 | DECISION | truncation | workshop | SUB-D | captured | 230.805973 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, supersession/history loss, wrong action, wrong relationship direction | sha256:890fc99579d49f14e20034b6d6ca08581ee71e6a53055076dd9c6f983c357b39 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 67 | D23-DECISION-02 | DECISION | truncation | workshop | SUB-E | captured | 245.435055 | false | false | true | REVIEW | false | citation-list inequality, supersession/history loss, wrong relationship direction | sha256:6d5aa5d9fb9efa8ba16a64f6b46730c4d59ddededca8844a3523e436304df3ee | sha256:f54fa4fdad6c4096bdd52e125d3f331e738b7d7fca1cb3a3ee76999d6b1a2f9f |
| 68 | D23-DECISION-02 | DECISION | truncation | workshop | SUB-A | captured | 234.043620 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, supersession/history loss, wrong action, wrong relationship direction | sha256:13d681ef178bd474f686ec0ad6e3189f0740c9452d609338d5b1bf037df42ada | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 69 | D23-DECISION-02 | DECISION | truncation | workshop | SUB-B | captured | 245.825024 | false | false | true | REVIEW | false | wrong relationship direction | sha256:0bc5f11edab8cc8f50f356ff8dbd5063ec987f97bec8c982e0880d964bd83cfc | sha256:1a3a6ecb5930722d898c8ebfc383516363dbfb277f01b7212b49c9a13d8a5e75 |
| 70 | D23-DECISION-02 | DECISION | truncation | workshop | SUB-C | captured | 238.207375 | false | false | true | REVIEW | false | wrong relationship direction | sha256:ee32ae9b024152e45bef76687b5dc225250057a7d190034af6e3338eb2d9dba2 | sha256:b9917dbad8f3d6384d79dc7d8d0fe17551c9e42938e9226b145c0e09542312bf |
| 71 | D23-DECISION-11 | DECISION | no_rot | release | SUB-E | captured | 27.878340 | false | true | true | REVIEW | false | none | sha256:26ad58668fc73c33c89be464adcdbb5de360002daa5aa1df75fdc26a745847ce | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 72 | D23-DECISION-11 | DECISION | no_rot | release | SUB-A | captured | 41.814482 | false | false | true | REVIEW | false | citation-list inequality, wrong relationship direction | sha256:70632eeaaa7a695e74ed413a22674401e165eb5ca8f6c367ffa85f2bce4730f0 | sha256:bd5fa6ef135076477c0c1dad2f9e37f775bd8d2407c76f3c17653682e31656df |
| 73 | D23-DECISION-11 | DECISION | no_rot | release | SUB-B | captured | 41.644079 | false | false | true | REVIEW | false | wrong relationship direction | sha256:626738482a334e4e75f301f8e823bd9cb9bcd651b829a6c82a1578810ad3a098 | sha256:6f418377b67dbd838415005f64875e50aaaf7abf29e1204007c06d0c44cf440f |
| 74 | D23-DECISION-11 | DECISION | no_rot | release | SUB-C | captured | 39.935066 | false | false | true | REVIEW | false | wrong relationship direction | sha256:724dec864083f3db81ece3cc05f61e700a63bb40f1488bbdf9cf04321fec1e4f | sha256:e80a459a5308fee261bb89050d280e79b4461461fd97f382367602d4bd02a3b8 |
| 75 | D23-DECISION-11 | DECISION | no_rot | release | SUB-D | captured | 38.639457 | false | false | true | REVIEW | true | wrong relationship direction | sha256:9e95bcbb3122ea40ab3dbe03603c5b1b47e527979bc99fcf16d375073e207fc4 | sha256:a05b667d10cba88fa0c9c7aa72ce64fac16ad10d4adb23c2ebc682aaef31bb70 |
| 76 | D23-EVIDENCE-01 | EVIDENCE | truncation | library | SUB-A | captured | 190.576539 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:c839f067cc6a39d6dc2c80c0cf470fd679c01b9f6fb32f0c03a438673069d20e | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 77 | D23-EVIDENCE-01 | EVIDENCE | truncation | library | SUB-B | captured | 213.774944 | false | false | true | REVIEW | false | wrong relationship direction | sha256:709b97cfb4ce6b55c584cb75ab1666ba27ddc1f69bd3d00d1f55260d73165f4d | sha256:697723bbd296395cb4e939f6dd18b19f325797a03be62f2105329ee9d068c4cd |
| 78 | D23-EVIDENCE-01 | EVIDENCE | truncation | library | SUB-C | captured | 209.625780 | false | false | true | REVIEW | false | wrong relationship direction | sha256:db0eb633980c82b49e61f6ef8853854d20716cdb9dc53f97298edf57525df6c0 | sha256:43ad952340c06ad0f574339dd4d307172b4cc996b0d1c4c76fcc7a59eefd149f |
| 79 | D23-EVIDENCE-01 | EVIDENCE | truncation | library | SUB-D | captured | 247.371793 | false | false | true | REVIEW | false | supersession/history loss, wrong relationship direction | sha256:61cf0ed843ad6b60cdfcddd78a6fe575c8327e1ffc6fffd2ffe07e3e786f1465 | sha256:7ef58160aabcd2f6c85305dbbefd1692d3ffe3a7dc7a16a977e2c812700a5e43 |
| 80 | D23-EVIDENCE-01 | EVIDENCE | truncation | library | SUB-E | captured | 200.008332 | false | true | true | REVIEW | false | none | sha256:a86ffc1cb80276dcbb6d15c8c310b67d5eb953ea4e76771b89abbff79e7b5353 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 81 | D23-EVIDENCE-02 | EVIDENCE | truncation | robot | SUB-B | captured | 265.389710 | false | false | true | REVIEW | false | wrong relationship direction | sha256:77a1e37778a8ab4c54d69f2da6348fae987d49096994e625728b995f6f73fd15 | sha256:ac3a152f906a05d5d7d0875c4dcc58c3ea481bd3c840c434b2bd96a4420259c6 |
| 82 | D23-EVIDENCE-02 | EVIDENCE | truncation | robot | SUB-C | captured | 269.989105 | false | false | true | REVIEW | false | wrong relationship direction | sha256:8053a1ce9928e4851b6927f3b9c8ec955d4a02e7f38149c65d2bc4057cf9f988 | sha256:aa097689608e3e5fb42f1e77eeb7b489993f785833ab5edec4864fee57e9b5b5 |
| 83 | D23-EVIDENCE-02 | EVIDENCE | truncation | robot | SUB-D | captured | 263.140198 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:6a03b90ee3b78737cc63a8a303ca33e47b54a79f3cc71b90f86f0078ead2653f | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 84 | D23-EVIDENCE-02 | EVIDENCE | truncation | robot | SUB-E | captured | 269.897001 | false | false | true | REVIEW | false | citation-list inequality, supersession/history loss, wrong relationship direction | sha256:81fe04abfa68b6f26b63e9e66ffafa3dd1744d687d16e5315b937bbafd88ae86 | sha256:d755dae39c398cc2340bfc24e4d8e97479f97ea92409cff90e7e1bcf47ebd066 |
| 85 | D23-EVIDENCE-02 | EVIDENCE | truncation | robot | SUB-A | captured | 260.825523 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:e98d883b2cca6c92d92bfe016b92cfc19e536e9167a09718966dfe3c0f826733 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 86 | D23-EVIDENCE-11 | EVIDENCE | no_rot | garden | SUB-C | captured | 48.447511 | false | false | true | REVIEW | false | wrong relationship direction | sha256:23c4695dcb8e5d4ccb6aa9ec6d46f17d35132b92e95dce88756721bc3c4132aa | sha256:48f1060b79866cda75d0b34545dff5e8dc7fd551e6ed58f7f7341a1abdd59cdb |
| 87 | D23-EVIDENCE-11 | EVIDENCE | no_rot | garden | SUB-D | captured | 37.864451 | false | false | true | REVIEW | true | citation-list inequality, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:6ef92c67ee003fb71b126cb1ab666b2493b6f6e6c289ff182fa770ad2bc3baa5 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 88 | D23-EVIDENCE-11 | EVIDENCE | no_rot | garden | SUB-E | captured | 29.524169 | false | true | true | REVIEW | false | none | sha256:4249c2e2b92c5ed223a8bb1411c64ad6880a1e38604ab97e4cbd4c9e69fb4622 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 89 | D23-EVIDENCE-11 | EVIDENCE | no_rot | garden | SUB-A | captured | 48.687014 | false | false | true | REVIEW | false | citation-list inequality | sha256:47ac291bf4f3b1cefe7a3ee2229d4506130b50eaabd000e5c4ab6172afa8e802 | sha256:d4b3c92644c88021a663a0c24dde9c5157114ac84475110941def89a82c8b8aa |
| 90 | D23-EVIDENCE-11 | EVIDENCE | no_rot | garden | SUB-B | captured | 55.625563 | false | false | true | REVIEW | false | citation-list inequality, wrong relationship direction | sha256:248cd659e93bb1ff3c20467f21427dbce4f1650c08854d8c95baf601b8503f3d | sha256:0f72360be7b0ab8f0468c1d839979f615ff8cdec88f154569b2295cf1bbb59fa |
| 91 | D23-OBJECTIVE-01 | OBJECTIVE | truncation | release | SUB-D | captured | 217.667545 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:67ca4f2dd46b099e2fddfe4608ac5599a33e4d618dc69765f6db8a48bed167ba | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 92 | D23-OBJECTIVE-01 | OBJECTIVE | truncation | release | SUB-E | captured | 211.042263 | false | true | true | REVIEW | false | none | sha256:299b2395cdec63516d7d6ed792d3b58a0a9297419e122a87732ee0c221027830 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 93 | D23-OBJECTIVE-01 | OBJECTIVE | truncation | release | SUB-A | captured | 213.169020 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:51d1803100850c927b59bc482961f1935faf33a27e3a9ef45a51c171c1e61677 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 94 | D23-OBJECTIVE-01 | OBJECTIVE | truncation | release | SUB-B | captured | 230.880044 | false | false | true | REVIEW | false | wrong relationship direction | sha256:0f0dfc6799b1ffce254ee02e454395a3387c0b626fa3015aa4571a49ef9deca2 | sha256:5454f78a58c216f3ff811e0c638c160a0a700964d35ccd23c83c0d7e7cc4c3ec |
| 95 | D23-OBJECTIVE-01 | OBJECTIVE | truncation | release | SUB-C | captured | 229.734706 | false | false | true | REVIEW | false | wrong relationship direction | sha256:eebf9726176ed114bca4e98460fc6607e7776b3b23ea7b58c237ddd5280046ae | sha256:804cfe8289e660c19e28e27ce2c4bfe45ecb6ea78f0910d0da12765570ce71d1 |
| 96 | D23-OBJECTIVE-02 | OBJECTIVE | truncation | catalog | SUB-E | captured | 272.679774 | false | false | true | REVIEW | false | citation-list inequality, supersession/history loss, wrong relationship direction | sha256:0192acca9fddbcce1612678e0de7b662dd2c644898883f50df2d50c79c071117 | sha256:97b55ccf821c6cf4aab8bfdcc85e523eb2977b0bd7ac9a84415e403b3d54c882 |
| 97 | D23-OBJECTIVE-02 | OBJECTIVE | truncation | catalog | SUB-A | captured | 265.128940 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:0f329d393a65bb5899a5f679d4121d18650f86e7eef2732bfdb133777dd0b52d | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 98 | D23-OBJECTIVE-02 | OBJECTIVE | truncation | catalog | SUB-B | captured | 259.253442 | false | false | true | REVIEW | false | wrong relationship direction | sha256:e5389b6c7445333651677ccbecdf8480ce4ab67c373a4a43bd8c35bb2e8fc445 | sha256:309ecc01494997b07f9dd88627b6d8e22fa570b79da9459eb5685466caaae67e |
| 99 | D23-OBJECTIVE-02 | OBJECTIVE | truncation | catalog | SUB-C | captured | 242.338854 | false | false | true | REVIEW | false | wrong relationship direction | sha256:85280fd598a682c4b173a7637555006e85570cc7e41b5d30afc8f3167d682718 | sha256:accea792763bcdd546d61d5839782113e83c3379566164db793af6b62f48211b |
| 100 | D23-OBJECTIVE-02 | OBJECTIVE | truncation | catalog | SUB-D | captured | 233.818252 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:fc41ac656d7f3041c731f419d0085462d5df8d642998f3b46b4c0b6bb10ef407 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 101 | D23-OBJECTIVE-11 | OBJECTIVE | no_rot | dataset | SUB-A | captured | 42.705659 | false | false | true | REVIEW | false | wrong relationship direction | sha256:6259d18cb068d0e4a5a578a72a3d978892b0a53f2065c9be4ff68312a72c17fe | sha256:951867b3485e8943fe7b2d51e598172650a35e878186546593233e1a386d8b0c |
| 102 | D23-OBJECTIVE-11 | OBJECTIVE | no_rot | dataset | SUB-B | captured | 71.502610 | false | false | true | REVIEW | false | supersession/history loss, wrong relationship direction | sha256:eb4d3996a98f58f79890f40de902c484cf6aebbbb2bcc5ccdef5db62ad20e339 | sha256:dd5bff86222dfe52e12b20376d7f63032682f6da9aa025f537b6a42476db391c |
| 103 | D23-OBJECTIVE-11 | OBJECTIVE | no_rot | dataset | SUB-C | captured | 37.658290 | false | false | true | REVIEW | false | wrong relationship direction | sha256:cce11d622c4ed92a26ad22e58a213a6bfc2aca3f50da06169045e2fbe6f5d568 | sha256:3c80ada540e176f39f67da03c1a0286f8bfda297c07dee78da5c2d7d9ff3c83c |
| 104 | D23-OBJECTIVE-11 | OBJECTIVE | no_rot | dataset | SUB-D | captured | 39.507415 | false | false | true | REVIEW | true | wrong relationship direction | sha256:dd49b11a9c1d80096352b3e6e2a6fd03b1b5eae3e3edfb9554747ac0bd1f06c0 | sha256:02b4a6e3a64bd4229ca7184b473cf9a17012f7927d0ac90386c727b430163ffd |
| 105 | D23-OBJECTIVE-11 | OBJECTIVE | no_rot | dataset | SUB-E | captured | 28.056608 | false | true | true | REVIEW | false | none | sha256:c9d7c982adde994f59be4882c3f60937240e64ab88f158bb1becf577930d4543 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 106 | D23-REJECTED_PATH-01 | REJECTED_PATH | truncation | archive | SUB-B | captured | 203.885353 | false | false | true | REVIEW | false | citation-list inequality, wrong relationship direction | sha256:24c02c53b552222425535e93015b9e9bc5828ab48bf7e5ece9969f5b531cf404 | sha256:2048e75352944d921e1d793be51df1a64330c05922112db5c20637079652c8d6 |
| 107 | D23-REJECTED_PATH-01 | REJECTED_PATH | truncation | archive | SUB-C | captured | 204.533712 | false | false | true | REVIEW | false | wrong relationship direction | sha256:9cb2e07fb795a9bcfde1f7bf8b4c383ee4d872a7371a21fd5b56a75dfd3cc718 | sha256:2ea1903d318cbcb8c2b897200551a68a5cfd5cc446ddf8afbea0d2af142a0518 |
| 108 | D23-REJECTED_PATH-01 | REJECTED_PATH | truncation | archive | SUB-D | captured | 202.930279 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, rejected-path revival, supersession/history loss, wrong relationship direction | sha256:2149679e0d119478c874df0d104e23be6f933bb80be997cc4fa3b441498265a0 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 109 | D23-REJECTED_PATH-01 | REJECTED_PATH | truncation | archive | SUB-E | captured | 196.686872 | false | true | true | REVIEW | false | none | sha256:90bfdfdf99f1665c797837367b043f461eaad978e7f783a40876f26d078ab77e | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 110 | D23-REJECTED_PATH-01 | REJECTED_PATH | truncation | archive | SUB-A | captured | 202.613028 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, rejected-path revival, supersession/history loss, wrong relationship direction | sha256:79ac822f34f45bedb89cd8515ada97f8ed4e51c95a18971f4776c6ffd0ca790e | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 111 | D23-REJECTED_PATH-02 | REJECTED_PATH | truncation | garden | SUB-C | captured | 242.642677 | false | false | true | REVIEW | false | wrong relationship direction | sha256:eea54fe328525c19e30442a6ac495adceda78a3d371b2634793f57103c65e94b | sha256:c78dc15c1d852272872047c33c0ec505c45acc1d17a8ea85706c0ec5e72edab3 |
| 112 | D23-REJECTED_PATH-02 | REJECTED_PATH | truncation | garden | SUB-D | captured | 230.969170 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, rejected-path revival, supersession/history loss, wrong relationship direction | sha256:03e11378ccf6859cf1a9201d0267dba26c3944e574638900cb4eab61cc409fb9 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 113 | D23-REJECTED_PATH-02 | REJECTED_PATH | truncation | garden | SUB-E | captured | 238.489183 | false | false | true | REVIEW | false | citation-list inequality, supersession/history loss, wrong relationship direction | sha256:7e7e8bc3cb7f06e2c165e5e30873475b3d27589f7ec80e9bab8cae7b1d9f95ac | sha256:5833fb282ba83a78f1141f058fbe206feb7bb1ee3c82005382b809e867c76223 |
| 114 | D23-REJECTED_PATH-02 | REJECTED_PATH | truncation | garden | SUB-A | captured | 229.421447 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, rejected-path revival, supersession/history loss, wrong relationship direction | sha256:c21c8cee5e9d1540a10e4f8d6b8ba0b4bce647dc449f01e26c1ad8d270e56f70 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 115 | D23-REJECTED_PATH-02 | REJECTED_PATH | truncation | garden | SUB-B | captured | 241.184350 | true | false | true | REVIEW | false | none | sha256:d9e2f07c48f348cd758fd4a77e42e4665b3e0e97e29d6f10fd447babe25968b3 | sha256:d84122beae5bfdab6578116e6481d131fb588b0efcd280d44d19aaf880e733d6 |
| 116 | D23-REJECTED_PATH-11 | REJECTED_PATH | no_rot | sensor | SUB-D | captured | 38.448340 | true | false | true | REVIEW | true | none | sha256:df1bad32bd32eb933d6b58fbaf2c2463431302fac5b9e2eea4865f67fe0cbc1e | sha256:d35c395febe7494e9bbb763a61abfe683b9b8547e62d84b1f6c06ad6162a1906 |
| 117 | D23-REJECTED_PATH-11 | REJECTED_PATH | no_rot | sensor | SUB-E | captured | 25.176463 | false | true | true | REVIEW | false | none | sha256:8764ba5d1ec7385b1df476367491b307c795764c0cd88a48c853254ccd8edf8c | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 118 | D23-REJECTED_PATH-11 | REJECTED_PATH | no_rot | sensor | SUB-A | captured | 42.652136 | false | false | true | REVIEW | false | wrong relationship direction | sha256:3e133e99f3dce7532bdedb61209fee8ba62e3c50c022983d7221b3eb1deadd03 | sha256:87aa13e76fd5a5acc2eae346dbb1e9aedcf9fc1fa3bd8579e08901b5eea27f14 |
| 119 | D23-REJECTED_PATH-11 | REJECTED_PATH | no_rot | sensor | SUB-B | captured | 49.230247 | true | false | true | REVIEW | false | none | sha256:fea49f35810ca87d37c9c1628976b402f4ee76d530800b54e99c4a2d992285c5 | sha256:25804a1ba93546d0d437102cb5102256e03f41f4295bd1404ee4a0f5663a6141 |
| 120 | D23-REJECTED_PATH-11 | REJECTED_PATH | no_rot | sensor | SUB-C | captured | 38.775610 | false | false | true | REVIEW | false | wrong relationship direction | sha256:bcc28b95e942e243c79fae1ace2084bcf3404542486f4043640774ae070d5f01 | sha256:017a0ed93ef9221d2328ae370b6f425d3af2c2fcea11314db6e6fe797fd582c8 |
| 121 | D23-SUPERSESSION-01 | SUPERSESSION | truncation | subtitle | SUB-E | captured | 191.583982 | false | true | true | REVIEW | false | none | sha256:e7a8fcc1f461aaabae5790baea7d75d41bb8e0e2972b0e727d809f6d0e3302cc | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 122 | D23-SUPERSESSION-01 | SUPERSESSION | truncation | subtitle | SUB-A | captured | 200.653630 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:904e14a17dbd40633a157fba3c1e586cb72f3d26920e3914906eee9a4dd11def | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 123 | D23-SUPERSESSION-01 | SUPERSESSION | truncation | subtitle | SUB-B | captured | 225.602626 | false | false | true | REVIEW | false | wrong relationship direction | sha256:06e11728a38f8c0f8939290750a6877073b96c54b035031a659420a181028e00 | sha256:950b013a8cc607d0fcca3fff191311fe88cddcf4dd577c060468f70d3e8725e8 |
| 124 | D23-SUPERSESSION-01 | SUPERSESSION | truncation | subtitle | SUB-C | captured | 216.609688 | false | false | true | REVIEW | false | wrong relationship direction | sha256:87b99cb487071cb39b121e96f04e5fdeb5a062df21f5f7a4e9f624886661b21d | sha256:2f381089769d6dc2bbfce0f488b8550798a92210d8feaaaca29e2c578ceb778c |
| 125 | D23-SUPERSESSION-01 | SUPERSESSION | truncation | subtitle | SUB-D | captured | 203.021599 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:17a47aff2399bf2a5417b6c5dbcd090f29ae2e355fa97c5b658a079c9f2a57c8 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 126 | D23-SUPERSESSION-02 | SUPERSESSION | truncation | dataset | SUB-A | captured | 235.438035 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:87f8aad4752855e9714f3ceb30d8ec1b3c5fa8b27a57bdda272b6a72900ce026 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 127 | D23-SUPERSESSION-02 | SUPERSESSION | truncation | dataset | SUB-B | captured | 265.515852 | false | false | true | REVIEW | false | wrong relationship direction | sha256:c04bdef9130a72ab1357d17f249cbbf0605c5ac9983132fec81dbd3060ed60e5 | sha256:be962a0b2aeda1d42c80d761e0378f2ebd07d4257c1d8ece12e7de26c0ee571e |
| 128 | D23-SUPERSESSION-02 | SUPERSESSION | truncation | dataset | SUB-C | captured | 248.204549 | false | false | true | REVIEW | false | wrong relationship direction | sha256:a02cbe59c1f68ba92442c673c3401eefaaae5e6db7bca13d85fb3d1911f18037 | sha256:6d99f2e57fe0705aa76f1eb48dbd1e387024ee8a4f7160a18c2c9cc90d4dd01a |
| 129 | D23-SUPERSESSION-02 | SUPERSESSION | truncation | dataset | SUB-D | captured | 248.203946 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:d8f7a202bbe0976d2209a86d686b6be388fdfab01f4a38c0a6a5407cae30575b | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 130 | D23-SUPERSESSION-02 | SUPERSESSION | truncation | dataset | SUB-E | captured | 252.111874 | false | false | true | REVIEW | false | citation-list inequality, supersession/history loss, wrong relationship direction | sha256:17d1700ca519b9c31aada8a0484c51d8b8899fe36df790498beaa069e0059f1b | sha256:ed4983e539d4de01f116ea5b778c4322aa0966b6b1ea2ca35aee8daf47e2e3cc |
| 131 | D23-SUPERSESSION-11 | SUPERSESSION | no_rot | library | SUB-B | captured | 43.275045 | false | false | true | REVIEW | false | wrong relationship direction | sha256:7f776c067013a66291895d78245825a0c08d9516dcce091985dcf89a3a53d9b6 | sha256:5b7bad775fe9f44ea013742acfd0e06fd8a4ca771f5ce0c60da29b3c74ec2fba |
| 132 | D23-SUPERSESSION-11 | SUPERSESSION | no_rot | library | SUB-C | captured | 44.110824 | false | false | true | REVIEW | false | wrong relationship direction | sha256:51bfc0b4e2c6733c6d126c46254542fd76f090af3792be3ad795f77afbf5753d | sha256:17481c3987a344c70a359538ee32ae337fe46c06efc6a79b41edd3010fd2769f |
| 133 | D23-SUPERSESSION-11 | SUPERSESSION | no_rot | library | SUB-D | captured | 40.820463 | false | false | true | REVIEW | true | wrong relationship direction | sha256:ea34c603ed4efb32c673d5db3d8598d2bb52bbe9d4a7e48e1f8f735598170867 | sha256:3d01b2a12984db12d27b8bd8f89af2050c49070de5c7aead2fa919c59ff76240 |
| 134 | D23-SUPERSESSION-11 | SUPERSESSION | no_rot | library | SUB-E | captured | 27.163153 | false | true | true | REVIEW | false | none | sha256:b7acf21c19e43ab1342ac5a72cf6a2db9c2585d8fe1f940d18e6b840b140e341 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 135 | D23-SUPERSESSION-11 | SUPERSESSION | no_rot | library | SUB-A | captured | 43.068826 | false | false | true | REVIEW | false | wrong relationship direction | sha256:8f5a142ae491df7db7b1a1b08e7482e78fd1054ea748d580e62af455ec1c5c45 | sha256:a116a4c57a269ef0a422503c333599a89a7267c6dfbbaf891300e429caa44c27 |
| 136 | D23-UNRESOLVED_DEPENDENCY-01 | UNRESOLVED_DEPENDENCY | truncation | theatre | SUB-C | captured | 206.436417 | false | false | true | REVIEW | false | wrong relationship direction | sha256:79a8f28110873646ccfba8e69cdb1f6fa02e542a888adcfbbe78994c334834f1 | sha256:fca42be97a6fec24bc6d88001235f84760bb56fd62187250e1eebe2e04a82d3d |
| 137 | D23-UNRESOLVED_DEPENDENCY-01 | UNRESOLVED_DEPENDENCY | truncation | theatre | SUB-D | captured | 198.565527 | false | false | true | REVIEW | false | citation-list inequality, dependency ignored, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:10fd689ec3bef2338475ae25f4a60fbf16487c473bff74829acc32f5b9736464 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 138 | D23-UNRESOLVED_DEPENDENCY-01 | UNRESOLVED_DEPENDENCY | truncation | theatre | SUB-E | captured | 212.670103 | false | true | true | REVIEW | false | none | sha256:812ee59d75b92df7daf04194e3a83a5842d992a3bbe233d00bf5783a27e2f806 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 139 | D23-UNRESOLVED_DEPENDENCY-01 | UNRESOLVED_DEPENDENCY | truncation | theatre | SUB-A | captured | 212.252024 | false | false | true | REVIEW | false | citation-list inequality, dependency ignored, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:407c6cd400934ce38c07ea215b2b275e1a1b500c3f6f9cb56fee680fb15df6f7 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 140 | D23-UNRESOLVED_DEPENDENCY-01 | UNRESOLVED_DEPENDENCY | truncation | theatre | SUB-B | captured | 222.510201 | false | false | true | REVIEW | false | citation-list inequality, supersession/history loss, wrong relationship direction | sha256:08268b7d86c26edb4ae59217388e1fda8733f0ea3d8559ee6f8d00f3c8f3b78b | sha256:1a4aa72999a76d03f4d910fa63078139bd631a128a5006917516b1e71969ef38 |
| 141 | D23-UNRESOLVED_DEPENDENCY-02 | UNRESOLVED_DEPENDENCY | truncation | library | SUB-D | captured | 238.900595 | false | false | true | REVIEW | false | citation-list inequality, dependency ignored, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:195418257303e5ae3b0fbaf51b329aee4c696bbe5dbd4b00287ed2120c342b33 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 142 | D23-UNRESOLVED_DEPENDENCY-02 | UNRESOLVED_DEPENDENCY | truncation | library | SUB-E | captured | 249.387210 | false | false | true | REVIEW | false | citation-list inequality, supersession/history loss, wrong relationship direction | sha256:1ffea2d5a1043a459099ee4b6c0f70ca30690a0378f6e7ee41d1226c47b7b8d6 | sha256:0d45cb8be8959576a0c004f18c529078707132a47ecc954ee916e4c0b9169596 |
| 143 | D23-UNRESOLVED_DEPENDENCY-02 | UNRESOLVED_DEPENDENCY | truncation | library | SUB-A | captured | 243.917181 | false | false | true | REVIEW | false | citation-list inequality, dependency ignored, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:19a0a05466679c7a9a50bf01ceb5022937ad0623162b8615c671a70e07266f8d | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 144 | D23-UNRESOLVED_DEPENDENCY-02 | UNRESOLVED_DEPENDENCY | truncation | library | SUB-B | captured | 241.420332 | false | false | true | REVIEW | false | wrong relationship direction | sha256:a8c09de2748d8484448d46f3b212f951fec450bc00a020998cee7911abec0b2d | sha256:384d1d0c2ecd2638f7a5711d0d6c991cf98da2141a63e505a17a8f9d92d9e20c |
| 145 | D23-UNRESOLVED_DEPENDENCY-02 | UNRESOLVED_DEPENDENCY | truncation | library | SUB-C | captured | 233.972349 | false | false | true | REVIEW | false | wrong relationship direction | sha256:a481c7daf41b8024ce3b44d4cf02e060eaecba6f48f973fdab3165637d944389 | sha256:9107d6498faf380b0b2acdcfa3f97782954f207a2db94fe6e4e91032dc32c745 |
| 146 | D23-UNRESOLVED_DEPENDENCY-11 | UNRESOLVED_DEPENDENCY | no_rot | archive | SUB-E | captured | 26.624362 | false | true | true | REVIEW | false | none | sha256:16bd919d0827e08efe809c027bab786eafae3adbb1b87bc44b6bd167ae93dbc7 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 147 | D23-UNRESOLVED_DEPENDENCY-11 | UNRESOLVED_DEPENDENCY | no_rot | archive | SUB-A | captured | 38.223839 | false | false | true | REVIEW | false | wrong relationship direction | sha256:5a89f24fed9994c4e5be8f8901fa6d73958418a163b3d6e24016abe78472d72a | sha256:568db0f260369aa7f970eba1504181db8b623fe00079552c854cb3b3a054c958 |
| 148 | D23-UNRESOLVED_DEPENDENCY-11 | UNRESOLVED_DEPENDENCY | no_rot | archive | SUB-B | captured | 44.337085 | false | false | true | REVIEW | false | wrong relationship direction | sha256:0586f22660edfd26c81002777edb14caaacbcbd6e70309347d0dd93b44f2f6f1 | sha256:304653665c54a4c5f4b55139cbf4b9c62becdabedc9e8f82295d251805adbcb8 |
| 149 | D23-UNRESOLVED_DEPENDENCY-11 | UNRESOLVED_DEPENDENCY | no_rot | archive | SUB-C | captured | 36.644794 | false | false | true | REVIEW | false | wrong relationship direction | sha256:f2fb7abd051819c7e2d34f5fb7c4c022ca1aa3c72e0c3e2925c630b72dceedf3 | sha256:1b510d82cf987c2ce266a16c18e08b1712a6b3ae678fe7c075d9c320f9575d37 |
| 150 | D23-UNRESOLVED_DEPENDENCY-11 | UNRESOLVED_DEPENDENCY | no_rot | archive | SUB-D | captured | 35.702974 | false | false | true | REVIEW | true | wrong relationship direction | sha256:3aa5674104c92ac00baac395e1c761404b8137404a8274fd287a70286305664d | sha256:4fb47409996e4cf1dc8b506e71a0ac5030257670a060cb35d6b6f79cf720ff61 |
| 151 | D23-WORKSTREAM-01 | WORKSTREAM | truncation | dataset | SUB-A | captured | 189.418596 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:9bb3297fb6452ffd69ab81e10a5f786e54640c99c1d85c284916ef1a04c33964 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 152 | D23-WORKSTREAM-01 | WORKSTREAM | truncation | dataset | SUB-B | captured | 209.684421 | false | false | true | REVIEW | false | citation-list inequality, wrong relationship direction | sha256:e4d72af7eecb5d7d11a7031d02f7600196e4eac0f7c952041256c3dd65feb935 | sha256:d9d00bbac68f5e4a671f2aab40bbec14c0639c69edea1e0bf7ae58cef302ef9f |
| 153 | D23-WORKSTREAM-01 | WORKSTREAM | truncation | dataset | SUB-C | captured | 206.124564 | false | false | true | REVIEW | false | wrong relationship direction | sha256:a76aa8e8cfa5f5351bdaa5f29a16147f6f57d80d48537da3db7bd1c718e3f5a7 | sha256:00cc9e2f77a0ac554eefa01a7fa0f2d959acb9c6dd6a23701d9bc827d4bdccdd |
| 154 | D23-WORKSTREAM-01 | WORKSTREAM | truncation | dataset | SUB-D | captured | 184.663788 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:dd722d764e4f4459400443e1d89dd01f13b1f90bc3307d190a5c3c738e0055c3 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 155 | D23-WORKSTREAM-01 | WORKSTREAM | truncation | dataset | SUB-E | captured | 192.480549 | false | true | true | REVIEW | false | none | sha256:d4c7a93d129ff97d4495f85345abf8f0017cc05e68c4c6d0101d036361df29c2 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 156 | D23-WORKSTREAM-02 | WORKSTREAM | truncation | game | SUB-B | captured | 244.695605 | false | false | true | REVIEW | false | citation-list inequality, wrong relationship direction | sha256:27b4f5614e84efbf0cef0f990c3250ac1833f69e5ef25fa94ba96703ce1b5fdf | sha256:1340b47ea1cf6a1a581ed38f81f90f2ba0f066b69300bb67f0879158f318b574 |
| 157 | D23-WORKSTREAM-02 | WORKSTREAM | truncation | game | SUB-C | captured | 229.962127 | false | false | true | REVIEW | false | wrong relationship direction | sha256:8e3518595fa878aae7fd0b6cfdb19b0e31f91c5eb019fdf059192712e9eddb94 | sha256:8182847fa6e6fcf23c6a2332b22c818b112ddc1fe6016f64ac7b6e55611a8a5c |
| 158 | D23-WORKSTREAM-02 | WORKSTREAM | truncation | game | SUB-D | captured | 220.071663 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:678be36b3f59279163671414414b8f3afedcf82f37526bba42c66436e56f48c8 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 159 | D23-WORKSTREAM-02 | WORKSTREAM | truncation | game | SUB-E | captured | 255.847891 | false | false | true | REVIEW | false | citation-list inequality, supersession/history loss, wrong relationship direction | sha256:4de703efff818c3182cadb828c887556a142b57beaa00389b7ebcf1037ddea72 | sha256:01801ca6e0df8dd13f7d1516c62fdd49117108b24d7ad1607e629d453e8e7a27 |
| 160 | D23-WORKSTREAM-02 | WORKSTREAM | truncation | game | SUB-A | captured | 240.675267 | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:d99de9d96e8987a8574ac2901f636ad56b9fedb5618c4f89297942724d560a45 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 161 | D23-WORKSTREAM-11 | WORKSTREAM | no_rot | robot | SUB-C | captured | 42.294654 | false | false | true | REVIEW | false | wrong relationship direction | sha256:40042c1dadd8745832aedf3f5141a5d61f1a5fa5c097585e4922a85a98b505c9 | sha256:0053d9c57a3ad1fdc0d26763238be22501d41ab55f33694696503873d4611bcd |
| 162 | D23-WORKSTREAM-11 | WORKSTREAM | no_rot | robot | SUB-D | captured | 35.108727 | false | false | true | REVIEW | true | citation-list inequality, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:aceaacac17508e9ccf8c5dd7d678e361a2fc7a3d41ff2a47d6ef1442612bddeb | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 163 | D23-WORKSTREAM-11 | WORKSTREAM | no_rot | robot | SUB-E | captured | 27.747944 | false | true | true | REVIEW | false | none | sha256:66c23fecee757f5e586f5cba167643315cec7b0af8b26f9d606fa9cbb714355a | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 164 | D23-WORKSTREAM-11 | WORKSTREAM | no_rot | robot | SUB-A | captured | 43.476510 | false | false | true | REVIEW | false | wrong relationship direction | sha256:b3ceb5483c216a104f6ba3d90decf5618118ca7b64927128de0b6d3101e79994 | sha256:f58b866ce0dd7cfb9acdb6c33cb631a296432786398cfd8d2d099a221291cef5 |
| 165 | D23-WORKSTREAM-11 | WORKSTREAM | no_rot | robot | SUB-B | captured | 42.688897 | false | false | true | REVIEW | false | wrong relationship direction | sha256:7b820906a05dd1b62e723d2308f6150898a97ab8b4cfb57d2d537258c565d32f | sha256:20836ec80ad35d47758493562d03926462d92ea6c378f0990c735901e7e069dd |

All 165 planned dispositions are preserved in `raw_matrix.jsonl` when the run reaches its normal end. Captured prompts/responses, native ID maps, packet lineage and oracle outputs remain inline; unknown outcomes contain only preserved send/no-capture evidence. No observation was retried, repaired, selected best-of, or silently discarded.
