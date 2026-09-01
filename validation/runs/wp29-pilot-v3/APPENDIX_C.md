# WP-29 Appendix C — pilot v3 permanent stop record

> STOPPED INCOMPLETE: 5/165 captures. Observation 6 timed out after explicit send with an unknown provider outcome; no resume or resend is permitted. This report issues no specification G-gate verdict.

## Run identity

```json
{
  "captures": 5,
  "code_sha": "e081d663581d27c1b9eb3ac0b3ea41ae64203c3c",
  "completed": false,
  "freeze_sha256": "sha256:38f5f606be0a364d01dc7dc6fbb16bde36ba710be7db24969f2023aac043f220",
  "logical_calls_claimed": 6,
  "run_id": "wp29-pilot-v3"
}
```

## Substrate engagement

> Execution telemetry only: this establishes that the corrected ToM substrate was exercised; it is not an efficacy or G-gate verdict.

```json
{
  "all_rows_fully_engaged": true,
  "assistant_teaches": 288,
  "assistant_turns": 288,
  "canonical_17_channel_applications": 744,
  "captured_rows": 5,
  "checkpoint_changed_rows": 6,
  "five_dynamics_receipts": 744,
  "history_import_provider_calls": 0,
  "history_turns": 744,
  "label": "EXECUTION-TELEMETRY-NOT-EFFICACY",
  "routing_basis_8d_applications": 744,
  "rows_fully_engaged": 6,
  "rows_observed": 6,
  "stopped_observation": {
    "assistant_teaches": 58,
    "assistant_turns": 58,
    "canonical_17_channel_applications": 144,
    "checkpoint_after": "sha256:5157903cd4baa1ed1d698d5cb605e72dcf041c21f26d5b66e83009e6240b697a",
    "checkpoint_before": "sha256:aa566823c99d9d4d48f3178d8b58d4dbb50e1310fe0e81d5c96f02001a5e74a5",
    "explicit_send_recorded": true,
    "five_dynamics_receipts": 144,
    "history_turns": 144,
    "provider_outcome": "unknown",
    "response_capture_recorded": false,
    "routing_basis_8d_applications": 144,
    "sequence": 6,
    "tick_after": 4851,
    "tick_before": 4707
  },
  "tick_delta": 744
}
```

## Frozen-hypothesis resolution

- **H1:** INVALID_INCOMPLETE
- **H0:** UNRESOLVED_INCOMPLETE
- **H2:** UNRESOLVED_INCOMPLETE
- **H3:** NOT_OBSERVED

```json
{
  "H0": {
    "criterion": "one or more frozen H1 primary components does not hold",
    "outcome": "UNRESOLVED_INCOMPLETE"
  },
  "H1": {
    "components": {
      "complete_matrix": false,
      "sub_d_at_least_0.80_every_family": null,
      "sub_d_minus_sub_a_at_least_0.15": null,
      "sub_d_minus_sub_b_at_least_0.15": null,
      "sub_d_vs_sub_a_ci_excludes_zero_positive": null,
      "sub_d_vs_sub_b_ci_excludes_zero_positive": null
    },
    "outcome": "INVALID_INCOMPLETE"
  },
  "H2": {
    "components": {
      "H2.1_no_rot_rate_within_0.05_of_A": null,
      "H2.1_zero_gratuitous_injections": null,
      "H2.2_long_D_within_0.05_of_C": null,
      "H2.3_D_exceeds_E_by_0.10_or_containment": null,
      "H2.4_supersession_D_at_least_0.80": null
    },
    "outcome": "UNRESOLVED_INCOMPLETE"
  },
  "H3": {
    "outcome": "NOT_OBSERVED",
    "rows": []
  },
  "cluster_bootstrap": {
    "SUB-A": {
      "baseline": "SUB-A",
      "ci95": [
        null,
        null
      ],
      "invalid_replicates": 10000,
      "replicates": 10000,
      "seed": 1729,
      "valid_replicates": 0
    },
    "SUB-B": {
      "baseline": "SUB-B",
      "ci95": [
        null,
        null
      ],
      "invalid_replicates": 10000,
      "replicates": 10000,
      "seed": 1729,
      "valid_replicates": 0
    }
  },
  "family_long_rates": {
    "ASSUMPTION": {
      "SUB-A": {
        "denominator": 1,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-B": {
        "denominator": 1,
        "numerator": 1,
        "rate": 1.0
      },
      "SUB-C": {
        "denominator": 1,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-D": {
        "denominator": 1,
        "numerator": 0,
        "rate": 0.0
      },
      "SUB-E": {
        "denominator": 1,
        "numerator": 0,
        "rate": 0.0
      }
    },
    "COMPLETED_WORK": {
      "SUB-A": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-B": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-C": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-D": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-E": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      }
    },
    "CONCEPT": {
      "SUB-A": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-B": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-C": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-D": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-E": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      }
    },
    "CONSTRAINT": {
      "SUB-A": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-B": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-C": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-D": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-E": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      }
    },
    "DECISION": {
      "SUB-A": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-B": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-C": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-D": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-E": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      }
    },
    "EVIDENCE": {
      "SUB-A": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-B": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-C": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-D": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-E": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      }
    },
    "OBJECTIVE": {
      "SUB-A": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-B": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-C": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-D": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-E": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      }
    },
    "REJECTED_PATH": {
      "SUB-A": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-B": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-C": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-D": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-E": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      }
    },
    "SUPERSESSION": {
      "SUB-A": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-B": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-C": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-D": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-E": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      }
    },
    "UNRESOLVED_DEPENDENCY": {
      "SUB-A": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-B": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-C": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-D": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-E": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      }
    },
    "WORKSTREAM": {
      "SUB-A": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-B": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-C": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-D": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      },
      "SUB-E": {
        "denominator": 0,
        "numerator": 0,
        "rate": null
      }
    }
  },
  "macro_long_rates": {
    "SUB-A": null,
    "SUB-B": null,
    "SUB-C": null,
    "SUB-D": null,
    "SUB-E": null
  },
  "paired_differences": {
    "SUB-D_minus_SUB-A": null,
    "SUB-D_minus_SUB-B": null
  }
}
```

## Exact action consistency by focus family

| Focus family | SUB-A | SUB-B | SUB-C | SUB-D | SUB-E |
|---|---|---|---|---|---|
| ASSUMPTION | 0/1 (0.000) | 1/1 (1.000) | 0/1 (0.000) | 0/1 (0.000) | 0/1 (0.000) |

## Exact action consistency by slice

| Slice | SUB-A | SUB-B | SUB-C | SUB-D | SUB-E |
|---|---|---|---|---|---|
| truncation | 0/1 (0.000) | 1/1 (1.000) | 0/1 (0.000) | 0/1 (0.000) | 0/1 (0.000) |

## Exact action consistency by domain

| Domain | SUB-A | SUB-B | SUB-C | SUB-D | SUB-E |
|---|---|---|---|---|---|
| robot | 0/1 (0.000) | 1/1 (1.000) | 0/1 (0.000) | 0/1 (0.000) | 0/1 (0.000) |

## Failure taxonomy

| Failure | SUB-A | SUB-B | SUB-C | SUB-D | SUB-E | Total |
|---|---:|---:|---:|---:|---:|---:|
| citation-list inequality | 1 | 0 | 0 | 1 | 0 | 2 |
| enumeration/format failure | 1 | 0 | 0 | 1 | 0 | 2 |
| evidence overstatement/assumption promotion | 1 | 0 | 0 | 1 | 0 | 2 |
| supersession/history loss | 1 | 0 | 0 | 1 | 0 | 2 |
| wrong relationship direction | 1 | 0 | 1 | 1 | 0 | 3 |

## No-rot SUB-D injection telemetry (floor permitted)

| Test ID | Floor items | Optional items | Gratuitous | Packet chars |
|---|---:|---:|---|---:|

## Raw paired matrix

| # | Test ID | Family | Slice | Domain | Arm | Exact | SUB-E containment | Shape | Evaluation | Gratuitous | Failures | Prompt SHA | Response SHA |
|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | D23-ASSUMPTION-01 | ASSUMPTION | truncation | robot | SUB-A | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:c169924eda1fc7e5e52a7a2146e4cd7b371a34dea4155a4a1b38cc9d898cfc8f | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 2 | D23-ASSUMPTION-01 | ASSUMPTION | truncation | robot | SUB-B | true | false | true | REVIEW | false | none | sha256:9a4d78315d51efe9db250303e80a409521f24fe19b173ac524bd69e9684fa43b | sha256:a9abb8d1af695948f007e9ab80e72f183f179016d98d429f712710740d15615d |
| 3 | D23-ASSUMPTION-01 | ASSUMPTION | truncation | robot | SUB-C | false | false | true | REVIEW | false | wrong relationship direction | sha256:4f219fa11576af1d31026b8b2a7eb6ab8ed198d9d1c2894b38af2ad22ec8253a | sha256:8704086b04281d4a5e909fb6e8fcc23f2bae61a46f28fa2b26b7a1570773aa09 |
| 4 | D23-ASSUMPTION-01 | ASSUMPTION | truncation | robot | SUB-D | false | false | true | REVIEW | false | citation-list inequality, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:373d8ce59c6ce04043cc0feb02442f990a6864031175a87002463cfa26306857 | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |
| 5 | D23-ASSUMPTION-01 | ASSUMPTION | truncation | robot | SUB-E | false | true | true | REVIEW | false | none | sha256:16955c6d98ea71741d959e2152ce3949c7d98e7813fdad7cf0f2cec9a727604f | sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc |

Raw visible prompts, bounded responses, native ID maps, packet lineage and oracle outputs are preserved in `raw_matrix.jsonl`; call claims are preserved in `claims.jsonl`. No row was retried, repaired, selected best-of, or silently discarded.
