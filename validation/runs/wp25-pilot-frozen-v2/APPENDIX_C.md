# WP-25 Appendix C — frozen 33-case production pilot

> PILOT OUTCOME ONLY. This report issues no specification G-gate verdict.

## Run identity

```json
{
  "captures": 165,
  "code_sha": "d5157628689ca6bebe23c581d052ccde64583f20",
  "completed": true,
  "freeze_sha256": "sha256:04123dfc3ddd8033264977894fec2b5c7410a9df11b341cdcc72475b53a8a1d9",
  "logical_calls_claimed": 165,
  "run_id": "wp25-pilot-frozen-v2"
}
```

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
    "SUB-B": 0.0,
    "SUB-C": 0.0,
    "SUB-D": 0.0,
    "SUB-E": 0.0
  },
  "paired_differences": {
    "SUB-D_minus_SUB-A": 0.0,
    "SUB-D_minus_SUB-B": 0.0
  }
}
```

## Exact action consistency by focus family

| Focus family | SUB-A | SUB-B | SUB-C | SUB-D | SUB-E |
|---|---|---|---|---|---|
| ASSUMPTION | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| COMPLETED_WORK | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| CONCEPT | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| CONSTRAINT | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| DECISION | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| EVIDENCE | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| OBJECTIVE | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| REJECTED_PATH | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| SUPERSESSION | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| UNRESOLVED_DEPENDENCY | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| WORKSTREAM | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |

## Exact action consistency by slice

| Slice | SUB-A | SUB-B | SUB-C | SUB-D | SUB-E |
|---|---|---|---|---|---|
| no_rot | 0/11 (0.000) | 0/11 (0.000) | 0/11 (0.000) | 0/11 (0.000) | 0/11 (0.000) |
| truncation | 0/22 (0.000) | 0/22 (0.000) | 0/22 (0.000) | 0/22 (0.000) | 0/22 (0.000) |

## Exact action consistency by domain

| Domain | SUB-A | SUB-B | SUB-C | SUB-D | SUB-E |
|---|---|---|---|---|---|
| archive | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| catalog | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| dataset | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| game | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) |
| garden | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| library | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| release | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) |
| robot | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| sensor | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| subtitle | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) | 0/2 (0.000) |
| theatre | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |
| workshop | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) | 0/3 (0.000) |

## Failure taxonomy

| Failure | SUB-A | SUB-B | SUB-C | SUB-D | SUB-E | Total |
|---|---:|---:|---:|---:|---:|---:|
| capture/lineage mismatch | 33 | 33 | 33 | 33 | 11 | 143 |
| completed-work reproposal | 2 | 0 | 0 | 2 | 0 | 4 |
| constraint violation | 1 | 0 | 0 | 2 | 0 | 3 |
| dependency ignored | 2 | 0 | 0 | 2 | 0 | 4 |
| enumeration/format failure | 21 | 0 | 0 | 26 | 0 | 47 |
| evidence overstatement/assumption promotion | 4 | 0 | 0 | 6 | 0 | 10 |
| objective/workstream substitution | 4 | 0 | 0 | 5 | 0 | 9 |
| rejected-path revival | 2 | 0 | 0 | 2 | 0 | 4 |
| supersession/history loss | 28 | 13 | 19 | 29 | 11 | 100 |
| wrong action | 4 | 0 | 0 | 5 | 0 | 9 |
| wrong relationship direction | 32 | 29 | 29 | 32 | 11 | 133 |

## No-rot SUB-D injection telemetry (floor permitted)

| Test ID | Floor items | Optional items | Gratuitous | Packet chars |
|---|---:|---:|---|---:|
| D23-ASSUMPTION-11 | 5 | 7 | true | 1859 |
| D23-COMPLETED_WORK-11 | 5 | 7 | true | 1853 |
| D23-CONCEPT-11 | 5 | 7 | true | 1841 |
| D23-CONSTRAINT-11 | 5 | 7 | true | 1877 |
| D23-DECISION-11 | 5 | 7 | true | 1934 |
| D23-EVIDENCE-11 | 5 | 7 | true | 1812 |
| D23-OBJECTIVE-11 | 5 | 7 | true | 1878 |
| D23-REJECTED_PATH-11 | 5 | 7 | true | 1860 |
| D23-SUPERSESSION-11 | 5 | 7 | true | 1861 |
| D23-UNRESOLVED_DEPENDENCY-11 | 5 | 7 | true | 1908 |
| D23-WORKSTREAM-11 | 5 | 7 | true | 1896 |

## Raw paired matrix

| # | Test ID | Family | Slice | Domain | Arm | Exact | SUB-E containment | Shape | Evaluation | Gratuitous | Failures | Prompt SHA | Response SHA |
|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | D23-ASSUMPTION-01 | ASSUMPTION | truncation | robot | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:ff2909461fae8cba7782b91448da5b66c3057002678b95b843db6ef02b990b18 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 2 | D23-ASSUMPTION-01 | ASSUMPTION | truncation | robot | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch | sha256:f1c2c5941aee822b31357f7068c283e6ea6b69c4127defe7c3e728f836e05dd9 | sha256:e6dfb34d8eaa46b008da812eab3b69077ef3a08116eb229882fc734de40c9658 |
| 3 | D23-ASSUMPTION-01 | ASSUMPTION | truncation | robot | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:f5984d699d1faeb197baffd8fde9efc3d5263f956881d5de4d6c5db43275b83f | sha256:10ae65a9dbfce185f486736ec2afa5f63ddfe9ff2325f5225b11b174de547d7e |
| 4 | D23-ASSUMPTION-01 | ASSUMPTION | truncation | robot | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:f9ecd28a87983e9a16f3f4bc3c196fa1c28f1d9e6ec49596951bbce2822a7f94 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 5 | D23-ASSUMPTION-01 | ASSUMPTION | truncation | robot | SUB-E | false | true | true | REVIEW | false | none | sha256:9b99fdac23b22264b93d10994475710e07de59f81819438d3db7f433ee4b8d2c | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 6 | D23-ASSUMPTION-02 | ASSUMPTION | truncation | subtitle | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:c61cddcd39ed304e05286eb14288bee5983ffba35131a69c04d06242f9f38a25 | sha256:d3c6da564588ed5edac586985c7f57ab43751493a11e966930059ecb6294b437 |
| 7 | D23-ASSUMPTION-02 | ASSUMPTION | truncation | subtitle | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:e39c8cc21ad0d0d77d4c25ccf0992c8923b6925c816ec6139184f078fef72a4e | sha256:41283eda3b09dbe7f4f5d1b1e237a7a8b9b06e6715797dd7d7113d1a6e142ccb |
| 8 | D23-ASSUMPTION-02 | ASSUMPTION | truncation | subtitle | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:4fd5368e0391cc112871f4571c133c14442a461a2b7663e2582d688f8cf586bd | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 9 | D23-ASSUMPTION-02 | ASSUMPTION | truncation | subtitle | SUB-E | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:32c3b644633908efd8dfdc250b42fd849af9985eae62293c29167054c25abe31 | sha256:35c6c6e449bd49a9dda3cd1e1ac2fd55d6205b59c30278b3c8721388df1b3fbd |
| 10 | D23-ASSUMPTION-02 | ASSUMPTION | truncation | subtitle | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:62a22da32d081d13bc43d64d18ba9f61805ab9c26da13e941b32b996fbb92161 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 11 | D23-ASSUMPTION-11 | ASSUMPTION | no_rot | theatre | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:50c0ad1ccc484ef20179a8be471e279a0dfef498d4fc9a008a51c8f57905114c | sha256:40bffdbd0f80aa6e2bc235eb3f9b1380a46cdda7ea38682da996669327849796 |
| 12 | D23-ASSUMPTION-11 | ASSUMPTION | no_rot | theatre | SUB-D | false | false | true | REVIEW | true | capture/lineage mismatch, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:787a2bf298704fe1fb71c247996ebff47294abac126b0ff37233c8854442f3db | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 13 | D23-ASSUMPTION-11 | ASSUMPTION | no_rot | theatre | SUB-E | false | true | true | REVIEW | false | none | sha256:379274a19f7f7dc3bb6ed3f1feca02bbcb4140326c824d678dcd66fac0fb8f53 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 14 | D23-ASSUMPTION-11 | ASSUMPTION | no_rot | theatre | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:7488dd71032d814623421784c3565017d1321131cb7ea8d7edc356cd1d37595d | sha256:1bcc9ef4d89396c4a7408d100d43edd339dfd7e18910b487dc948e8902846e59 |
| 15 | D23-ASSUMPTION-11 | ASSUMPTION | no_rot | theatre | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:ff4892d0dce8e160373b6c7bd52dfc6a8eb3bfb2ef077de8ea600b09c4b37d82 | sha256:65e6596368ad33333ac220457a04e53540094bfaf8ae387cc64842004b5e5d4b |
| 16 | D23-COMPLETED_WORK-01 | COMPLETED_WORK | truncation | garden | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, completed-work reproposal, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:95d9978254226e5a9e12dfe28a0735ec74ff43e603614d6cd147316f28e37097 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 17 | D23-COMPLETED_WORK-01 | COMPLETED_WORK | truncation | garden | SUB-E | false | true | true | REVIEW | false | none | sha256:f25b105b1a87a4c56306dd045f53a1120c5c057b05392473e9f99fc653899bd5 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 18 | D23-COMPLETED_WORK-01 | COMPLETED_WORK | truncation | garden | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, completed-work reproposal, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:6e1472ef3656cec682bbc00b66b6c555f95ec3dd1e584f59df1a11c86c27912d | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 19 | D23-COMPLETED_WORK-01 | COMPLETED_WORK | truncation | garden | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:a8e1ed9692443098903a31a8a2b15eb4f906a4cf382f4b4a278c137205f671df | sha256:f373033985d2ca061447f2a86236e94ffc3cca69734b8c7eab56c29d7acb26c6 |
| 20 | D23-COMPLETED_WORK-01 | COMPLETED_WORK | truncation | garden | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:a29bb419c5274e2ddb577d06224ad56cd22cc8e6439975855140bbf1ff993d90 | sha256:feab98b312740e5a38f3ba45c7e00c5d477617f571e64399a620dbfde852b41a |
| 21 | D23-COMPLETED_WORK-02 | COMPLETED_WORK | truncation | theatre | SUB-E | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:891cc484325543075ef0b05096fd58c39deef91029e88c750dc524d9133ed4c0 | sha256:108f1d62eb86aec346a97a0ca12f780f0b58bc1767b5d2813b967c8b50e56aa6 |
| 22 | D23-COMPLETED_WORK-02 | COMPLETED_WORK | truncation | theatre | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, completed-work reproposal, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:487a3aa8ae6d34ffa4c6e3e0b220668201dc7807a7d1edd78a3607c03b7b887f | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 23 | D23-COMPLETED_WORK-02 | COMPLETED_WORK | truncation | theatre | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:afd32ecb8ffb158b8ffdca21582cf919f3736501cfbb7af8c8491066a9afb3b0 | sha256:4867dbd548c46eb9743e048d3be9b38d451be8355daf97c11a05b31535a6e5e1 |
| 24 | D23-COMPLETED_WORK-02 | COMPLETED_WORK | truncation | theatre | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:35781be507babad9b9768d1999d47ee5d379e93582471d1c23ba00ceb1354fcc | sha256:3bdccbe51720bcc5fd621f3998d230dfd221f1903fc758070d26346b4db1df8d |
| 25 | D23-COMPLETED_WORK-02 | COMPLETED_WORK | truncation | theatre | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, completed-work reproposal, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:fd160edcea5951928f327ec8a13e9f36598fc9c4039e3c0a498082459550593e | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 26 | D23-COMPLETED_WORK-11 | COMPLETED_WORK | no_rot | workshop | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:3c4f06d8b62f939da9f46a95fe9f1e084f0e15c82a347a084c1a59810e3ae7c4 | sha256:619c9cda5743a262fe41585beb54a4773e42a2c1acf76533017c83dea5939487 |
| 27 | D23-COMPLETED_WORK-11 | COMPLETED_WORK | no_rot | workshop | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:ecaa126405c12ec38707055586f7f04d0392ae4ea73b92db5fb9d0a353bdb021 | sha256:942259e5b942ca97a3e81e1ee63bd4c4069af12cfbeebfbe26bf35207779fa8d |
| 28 | D23-COMPLETED_WORK-11 | COMPLETED_WORK | no_rot | workshop | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss | sha256:32f18fb4d69dda7e09a574dcce2d9a2d2eef4e46d1b59d136f9691edce803635 | sha256:fc56d4b1250fba3a8f645159560136a558455fabb42a4fd87941963bf59f23c4 |
| 29 | D23-COMPLETED_WORK-11 | COMPLETED_WORK | no_rot | workshop | SUB-D | false | false | true | REVIEW | true | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:a59ebc18fd101a2e58124a5489cd7a2037b29ccd74ef958db175dc5b2a1fecc9 | sha256:cd9c7c007da0f3e20dc31ff7e5634c3f747d9baf56d435c47a680ac2c1191ca5 |
| 30 | D23-COMPLETED_WORK-11 | COMPLETED_WORK | no_rot | workshop | SUB-E | false | true | true | REVIEW | false | none | sha256:89db06c26da384a8c76899a7245f4d0fd0ca90251ee6810654b134442b6be7ca | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 31 | D23-CONCEPT-01 | CONCEPT | truncation | catalog | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:3a87d65392a245b29a58977a1259f2592bbe857b1c07f6f58721b48b0ab6ef20 | sha256:1c03830391e4221358b3586aad1530531a596e2d20fc4f934a6a80692ba44ee0 |
| 32 | D23-CONCEPT-01 | CONCEPT | truncation | catalog | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:55e1e5791ae5353af16f18ca93d987e901dc31543362ebd034916458eb92aad2 | sha256:2f7a96f50e133c0a41b546c15ddfed36b40c5fbb26aacc7ba8ef559734039dbf |
| 33 | D23-CONCEPT-01 | CONCEPT | truncation | catalog | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, supersession/history loss, wrong action, wrong relationship direction | sha256:346c1b8f0019bdde8d851ac3658547c27b7bb5d48f07a33314dfcbd6c16072cb | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 34 | D23-CONCEPT-01 | CONCEPT | truncation | catalog | SUB-E | false | true | true | REVIEW | false | none | sha256:6d0b5f3f773e213077befe947febcac797618ca0a2dcbadd15f9ed6226456223 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 35 | D23-CONCEPT-01 | CONCEPT | truncation | catalog | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, supersession/history loss, wrong action, wrong relationship direction | sha256:eee6e997d1d4d729ce34c8fb88ee3dbb8191af9e1426b8982443eab6f3061c6f | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 36 | D23-CONCEPT-02 | CONCEPT | truncation | sensor | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss | sha256:a90102f302d0bfd3bdcdb32b80e153fde5eff70f5047337a59058778d8fd1571 | sha256:badc57eac2db43ad71b4cdfecd44e16c3f029b38812cc8fe72b798cbb7f39cd4 |
| 37 | D23-CONCEPT-02 | CONCEPT | truncation | sensor | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, supersession/history loss, wrong action, wrong relationship direction | sha256:86ee8fdd8861b7c591a82d0ae1e25cf0df179acb005defc9e8f5e8e781809ff0 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 38 | D23-CONCEPT-02 | CONCEPT | truncation | sensor | SUB-E | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:83dad3a1701ddc5eddaa4365ed5c97f318dff18fcb3cfa8507f7fbedabd468cb | sha256:4e2f3c981ebd6dbace721367bf6b1517815f6a3efb6be5ad6b84223dbcc0388b |
| 39 | D23-CONCEPT-02 | CONCEPT | truncation | sensor | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, supersession/history loss, wrong action, wrong relationship direction | sha256:718556e8293c730796726665d4d2ed669531d646d0016017316ee70e033e9234 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 40 | D23-CONCEPT-02 | CONCEPT | truncation | sensor | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch | sha256:a6683202f727f48975a1a7d939ba383fee7882dc51a97f6477f6646e218b877f | sha256:93562e43529bb4954cdf62fca5cd9466c0dfc4e17cc8b38477046191ffa98d7e |
| 41 | D23-CONCEPT-11 | CONCEPT | no_rot | game | SUB-D | false | false | true | REVIEW | true | capture/lineage mismatch, enumeration/format failure, supersession/history loss, wrong action, wrong relationship direction | sha256:cbf523cb0c55a9d257d01f6ba8ed4a6e070b6d621ef53403890b4d88ac8b88c8 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 42 | D23-CONCEPT-11 | CONCEPT | no_rot | game | SUB-E | false | true | true | REVIEW | false | none | sha256:0e8c2bb13f824402d569db2d363309af3d7eb2152b717262ba29e656235a551e | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 43 | D23-CONCEPT-11 | CONCEPT | no_rot | game | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:ffc655e52f4af0140428a699efddbcf1b6088eeb0afcd36b7f73a53eaac1f29c | sha256:098c4de00cb2fed8ed1f876f7fb4f2cf1c07b429f9198e3d32bac8cf238c44f3 |
| 44 | D23-CONCEPT-11 | CONCEPT | no_rot | game | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:d8457419f7d2adf8c1e8d67b3c5ce3421517bed3c445a761ebe9608f1bc2054a | sha256:dd0a513e216e7261787ecb5aaa61566341e0ef308da8ae13822969d210315e90 |
| 45 | D23-CONCEPT-11 | CONCEPT | no_rot | game | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:d16df501f852cff43bb6e2a7dfbd55eafa5fd79075862033185b00fcb35d6424 | sha256:93309febbd9ea34c2bec36aaf16516a6d345a1264a7e48a05ae0d6a4007ad293 |
| 46 | D23-CONSTRAINT-01 | CONSTRAINT | truncation | workshop | SUB-E | false | true | true | REVIEW | false | none | sha256:dc691699358d4c5e2d81d91e897f22b8f4898775a5a1b83456eac80e0c35eff8 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 47 | D23-CONSTRAINT-01 | CONSTRAINT | truncation | workshop | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, constraint violation, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:72631ccf17678dff36ac68466eb19f638e797f534e757d3074f6114aee347271 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 48 | D23-CONSTRAINT-01 | CONSTRAINT | truncation | workshop | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:e392c79b61ccb905cc01b8a72db78f81fc4c968c36b0306b7f5d1ffbda748360 | sha256:552fc054d7c04d17a85594c414d5a8e5b15f3178af53242103cde40edb3eeb77 |
| 49 | D23-CONSTRAINT-01 | CONSTRAINT | truncation | workshop | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:e4a4a51280c8ab9c38b85e8ef96b584cd859af53b0e2a39e3111bda8c050be27 | sha256:454a79343201030395b9fdd071c10b9b57ed1dea27d1df1af6951cbc7ea860ff |
| 50 | D23-CONSTRAINT-01 | CONSTRAINT | truncation | workshop | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, constraint violation, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:8655c3c37424d7ba36b5b75ffab86f36bf0e1f945b25fb74f1bafd5f251ca6fd | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 51 | D23-CONSTRAINT-02 | CONSTRAINT | truncation | archive | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:31577f14b18afebaa83e7a1cafd1d33cfae7988014ced010e6f9f2dc48eccdf7 | sha256:81f34fc9cc226ee40e36a6d8488533303b60c1575c6f09bba245f742f3b4b65b |
| 52 | D23-CONSTRAINT-02 | CONSTRAINT | truncation | archive | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:fee366ffa1eb7e40568d683ad0a409566c283b9d5cf546a7e9b720fd93822c36 | sha256:b18002a3addf126269e38d4ab6c7bea5e3d314864e03f0429b8fbb870af9eadf |
| 53 | D23-CONSTRAINT-02 | CONSTRAINT | truncation | archive | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:b52932d33a5c404e6121e33054e1f639c8f4f995c8ec4d73e3a7354677a254e2 | sha256:8ee354287d5b15d697683cc30cdc0210ee000d08526a3977b4f8d39397a1e2b7 |
| 54 | D23-CONSTRAINT-02 | CONSTRAINT | truncation | archive | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, constraint violation, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:a2e2a12c407cc213d14bee790b8a42871b0654b2ec9d431a5bd719e68b01abff | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 55 | D23-CONSTRAINT-02 | CONSTRAINT | truncation | archive | SUB-E | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:ecef3fba1be0e0cc6e5a304731f4c3d89cffd2d321af7f21d2d0fe6837d428e6 | sha256:34b50b0277cbf5f5af647d26e47c5e6f6a1ef65d1bb0ec29de77adba4829c306 |
| 56 | D23-CONSTRAINT-11 | CONSTRAINT | no_rot | catalog | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:e8d8c71e2ca1292fed0b278a0f0041e2776443a401fc4a1db5a1d4b5b3085cea | sha256:05e7d89135002cf165b013ecf7f50211da6336252f821b713f5aa6c81c2d8368 |
| 57 | D23-CONSTRAINT-11 | CONSTRAINT | no_rot | catalog | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch | sha256:5a4c88f35c62c1a945692aafec340aadb1a646e92da32243ebdf7610e5d3baf1 | sha256:cafb696a6c330fd8a79cb1414d911aadb49c7e134b3efb82a74e122db6880f04 |
| 58 | D23-CONSTRAINT-11 | CONSTRAINT | no_rot | catalog | SUB-D | false | false | true | REVIEW | true | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:9b8c46b51e44cf6f322ebf9f21098ccbe7ad03a7a28d2610d9407a345d9ca0bd | sha256:64bc930ac58c2b938c908cd41e81c07f77730c41957baacebe173056352fc05f |
| 59 | D23-CONSTRAINT-11 | CONSTRAINT | no_rot | catalog | SUB-E | false | true | true | REVIEW | false | none | sha256:d5ac0bb0cf6f1b3409c779a82095c3d2b0c496542244c84894bcc6a216ada76e | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 60 | D23-CONSTRAINT-11 | CONSTRAINT | no_rot | catalog | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:5afae58c4f969d8fb8989c95e6c88f4881f37dacbc8fd08829dbb174c48b3b46 | sha256:5a61a32625af2ed9a3558f0c487548266709fa9e80375dc4beb239ad46a7e340 |
| 61 | D23-DECISION-01 | DECISION | truncation | sensor | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:3980584e006d8214cba3150cdd9284dfe7ad9daf0a1e8d3f02cc70bb2b773638 | sha256:20469e787b11d3941286663a3338d050f783d5f3303f8ba29aa664a353156cb2 |
| 62 | D23-DECISION-01 | DECISION | truncation | sensor | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, supersession/history loss, wrong action, wrong relationship direction | sha256:ac052c53bd1151a6f809ecc25a537828b3c2e54ebeffce11a714d088928462d4 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 63 | D23-DECISION-01 | DECISION | truncation | sensor | SUB-E | false | true | true | REVIEW | false | none | sha256:2d46097c7631a1377034549e4bd04f4a2be5ff1dd68ff16a18ebcccca7da6e7e | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 64 | D23-DECISION-01 | DECISION | truncation | sensor | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, supersession/history loss, wrong action, wrong relationship direction | sha256:11c93fdfbb05fa50b1c5b6efb58b7d4811eb939a8acd9f3908721d63e3c49012 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 65 | D23-DECISION-01 | DECISION | truncation | sensor | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:bd8235c189b206f6a918b3d0f1779de7e85e1d16b670a0388682f95fd8ac39b0 | sha256:f912312631bfa3f46fc65f63e8fc7190c8b3842afb0f0ad73cf56ad1d22065d5 |
| 66 | D23-DECISION-02 | DECISION | truncation | workshop | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, supersession/history loss, wrong action, wrong relationship direction | sha256:0be14560975c9ddad93e757cf450824c5263ae44fc272adec7de7af58ead51a6 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 67 | D23-DECISION-02 | DECISION | truncation | workshop | SUB-E | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:b199fd3e138af3ce04baf0326266da807ddc7c635ca85df4fcb3e468da2ffe7e | sha256:473a80e0351e5c24b3342fb3cc84ae0a86920924d71c70610efac4eb43f3dde4 |
| 68 | D23-DECISION-02 | DECISION | truncation | workshop | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, supersession/history loss, wrong action, wrong relationship direction | sha256:0c772419bdd1367df4e7fe4f9f58bce92f4b5926184b0ce543075095b9a46c50 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 69 | D23-DECISION-02 | DECISION | truncation | workshop | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:ca1dc93903bc5f3dd99bbe031f6f83ccb0c347eef08979cfb4b4942216abd932 | sha256:074b5f496c070e3f20922681d5085acf1f5f32e2d28c57d33db2f32c5494e94a |
| 70 | D23-DECISION-02 | DECISION | truncation | workshop | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:4c4ba9671706483a96462628063a1726edec0c5b7babecf5daf5e2c2dab497a3 | sha256:2fe783c1b2cdd96cabcfbf0985e04e59e730407c4b09e2089f09784b1cd62b6f |
| 71 | D23-DECISION-11 | DECISION | no_rot | release | SUB-E | false | true | true | REVIEW | false | none | sha256:be2b85cd44dce106f259adac21c0b7247f9fa4e0a0bb4b60e39b21404955e835 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 72 | D23-DECISION-11 | DECISION | no_rot | release | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:cf305124f80bd7ee99adb1c93f9bd6424ae7a17a48e560ba15dc82fac31c669a | sha256:50f0e123c54c9efdb42333456372524daadd3b157ad6512a8db848cb24203d61 |
| 73 | D23-DECISION-11 | DECISION | no_rot | release | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:441f57f045f6d5e4216d83611e069c0fc894f55985bd04c848df0ea774ff840f | sha256:3e146abeb9556830a99454fdbd6d20a65831fb0d2bb986a512c8809b61b7d83b |
| 74 | D23-DECISION-11 | DECISION | no_rot | release | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:271a6223ec8be4b8d58b453dbfe4b3ecbd42f64be8bb83512221b1d591411bc4 | sha256:da018e880d7e7eb67d9f2356836f3870f2e9a0f8ca0468f791cb5b40e406ed90 |
| 75 | D23-DECISION-11 | DECISION | no_rot | release | SUB-D | false | false | true | REVIEW | true | capture/lineage mismatch, wrong relationship direction | sha256:35d4471e601041f21e17fd91043c419bcb6a4b80a5949695305884f7a968c52c | sha256:3bb5b69cf74c09b5a9ab3150ec1c9a77f575a2d7b6aab46047d036a4dd3d6a5e |
| 76 | D23-EVIDENCE-01 | EVIDENCE | truncation | library | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:d8aafaf0bfbb4be1dc9c518795c422197e1c334b79d074de1716acbcbf3e6098 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 77 | D23-EVIDENCE-01 | EVIDENCE | truncation | library | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:e5c915c9d340f129886e4b538211616ca016f1fffb91d155b8dbec33ac98b11d | sha256:096dd7ec23706af1e8d11a6e4c417080f950203322e608323a2d85689c182806 |
| 78 | D23-EVIDENCE-01 | EVIDENCE | truncation | library | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:2cf3acd85a10377a7a4a85b3746846f82ab7929b4e2d63b5fe34f3bb627999ad | sha256:5bd761817ce3fa3e5e7070e7adde0693ed3a0611bb02cdb6e931c2fd2820d122 |
| 79 | D23-EVIDENCE-01 | EVIDENCE | truncation | library | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:8a367785ab3f6304290957a85c99bfe3fc2027babe947e26ba32a144241c060b | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 80 | D23-EVIDENCE-01 | EVIDENCE | truncation | library | SUB-E | false | true | true | REVIEW | false | none | sha256:cb9ceb00f9233e942f76e75eb9506a9f21881018a094c4e400f1840a928b679e | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 81 | D23-EVIDENCE-02 | EVIDENCE | truncation | robot | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:19d9cd6d03b1fcfee493e0c353b2349cb9a625f6703d01aa5406c17383d7c89e | sha256:85662c3f401014707ce30d83a6a3497efb95f8357b8d71802f6518f0ac6d9488 |
| 82 | D23-EVIDENCE-02 | EVIDENCE | truncation | robot | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:fb8fa124ef693312d39bf8a814f5a42c50b767c6bed8417e54dbaf078f8161cf | sha256:1785b9b3a9288048ad69d651aa7de1cef7160063d8045053cfe6f6ff4b178163 |
| 83 | D23-EVIDENCE-02 | EVIDENCE | truncation | robot | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:3d6d2586f43a74c655a350d9cd1827b993af8bcdc4c6c55e95fc2b74d2886b42 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 84 | D23-EVIDENCE-02 | EVIDENCE | truncation | robot | SUB-E | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:0afdfd4394e2b11d77b06174d2352e63c328f1407d8d7b798629f3de2e295103 | sha256:b6a8da7135468080801c1b5595b7532cc6ba4d898034884c82794ddcae53a314 |
| 85 | D23-EVIDENCE-02 | EVIDENCE | truncation | robot | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:297cebbfcca77f368573a27e7bb6d7acf8673f47eee79dee2d2d376ca1d0a47e | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 86 | D23-EVIDENCE-11 | EVIDENCE | no_rot | garden | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:d8cd8c1b110c26a85d246f0b2bd5d9adb4ba8a534af02d93b88f322b9f534ef3 | sha256:088fc94eb6d9abfab75f126b186f790595e6a86908df955df89e2d4ffc37484f |
| 87 | D23-EVIDENCE-11 | EVIDENCE | no_rot | garden | SUB-D | false | false | true | REVIEW | true | capture/lineage mismatch, enumeration/format failure, evidence overstatement/assumption promotion, supersession/history loss, wrong relationship direction | sha256:ee89f270e6ef68328043c81a8778dd2de930db685a6124822dd8ab6a7f557d11 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 88 | D23-EVIDENCE-11 | EVIDENCE | no_rot | garden | SUB-E | false | true | true | REVIEW | false | none | sha256:4488651a32d66c432aa0a4636676c0b20d52b67067d33ef50f9a30bc024b5c84 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 89 | D23-EVIDENCE-11 | EVIDENCE | no_rot | garden | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch | sha256:91e9af4b015679fa56538e3cef0ff15d49f03b951338c5b2d11218fd7baa0a38 | sha256:4ba07ff73ae6f56f4144f475b77d51e76202a146d36e9667b572861935501cf9 |
| 90 | D23-EVIDENCE-11 | EVIDENCE | no_rot | garden | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:e77636a3b000bbebe721dde8e5a96514e5f5e2ebbfe4463c54011e6684517dc3 | sha256:b81d5e8060e16441f4df9e5895b66ec27df564d52960f4f5b60253bc0e935af8 |
| 91 | D23-OBJECTIVE-01 | OBJECTIVE | truncation | release | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:77d8a8cf3584934f3c9da35c131e655ba4c1dc28982b15267feff6eef7ad4e69 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 92 | D23-OBJECTIVE-01 | OBJECTIVE | truncation | release | SUB-E | false | true | true | REVIEW | false | none | sha256:773bc4ca49bcd60adb347f601894028e2a02061689cb7f051734c5cedab2b9e6 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 93 | D23-OBJECTIVE-01 | OBJECTIVE | truncation | release | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:6feab2d14deaad4350e67ae16419bea7fdcd386f1640b3b8aa757d79cc0c60ec | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 94 | D23-OBJECTIVE-01 | OBJECTIVE | truncation | release | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:74f3cb3baf634c442ed66cb598f63e7edb52fdb60b474180d44f3b1a66ef38af | sha256:b5d9d33548a45cfbed45e07558578f34cc20f08c9350c54bfcab4c0d4688d8ce |
| 95 | D23-OBJECTIVE-01 | OBJECTIVE | truncation | release | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:6c5662f07e7fe52150fdb84434cb9dbffb49d31bedbcbfc70a301f55769843fb | sha256:733615611f1aac10b6baa14b00d2033e4989bbd0ca89f2600fc9717a53fbddaa |
| 96 | D23-OBJECTIVE-02 | OBJECTIVE | truncation | catalog | SUB-E | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:8253634b44c6467ecb032cbe999dc3f5264dd507ba459ce1a6762edd515b6bda | sha256:09d17fe93f0dd995ba233612810e7ae2ccd8158d1f10c584a886e614a57eddc3 |
| 97 | D23-OBJECTIVE-02 | OBJECTIVE | truncation | catalog | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:ce4f57e6cef493c64ef82a007f16bb2e33d043bd9ce7089925517cf640ec7388 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 98 | D23-OBJECTIVE-02 | OBJECTIVE | truncation | catalog | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:e0c33fac914fed08a1abf910953a3e5649b5b6e438b511aba54a9232d70d2acf | sha256:501e78cd8ca606fa4b9e552e473e4cdc7d13ece51e8cb9d5a9e56fb367d2c7e7 |
| 99 | D23-OBJECTIVE-02 | OBJECTIVE | truncation | catalog | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:317ff457917d9ad28e44207020fbebc59498aeda1ba4bfb6d55c81ae0c1b5a90 | sha256:b4165006a8d39abfca4bebf0f564fa22a80a06ad192f348d30647fd1352bfbd2 |
| 100 | D23-OBJECTIVE-02 | OBJECTIVE | truncation | catalog | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:961de77f4bf8aa5b15bd52bdcb17e171f7e5276933623ed116c29f29af6d1841 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 101 | D23-OBJECTIVE-11 | OBJECTIVE | no_rot | dataset | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:a934214466fc3281054944a40baa765730d5ba61eab547de3a5c5a9bc68d3038 | sha256:6de9bd297606b21ff6ced9180f1c02c4dbad08679d59edcfbc7c3fa6d4e66a03 |
| 102 | D23-OBJECTIVE-11 | OBJECTIVE | no_rot | dataset | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:08be4956d9187aeabf6bc364646cdfd42aaa468ce8b077b417197083ad3da5bd | sha256:8f4db848a1d494ccb753f5eca5fad156bcf1b7f5793b7f24654bfbbd5cd3a4a1 |
| 103 | D23-OBJECTIVE-11 | OBJECTIVE | no_rot | dataset | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:08b5558657403dbba138bf8eb7f700e5421c32fa8d22994f0cd1f5699cd79c68 | sha256:c351bcd6863be141686b1bd12174318108c6e6cf8edfe02c29c6d31998918cdf |
| 104 | D23-OBJECTIVE-11 | OBJECTIVE | no_rot | dataset | SUB-D | false | false | true | REVIEW | true | capture/lineage mismatch, wrong relationship direction | sha256:873c3eb622d15579667dd5e6980683b42122a0afb73efb74d1793293c263b9b8 | sha256:c214487abee701c082c78a5f05d9bf70ef8ee4f07c761ff6e66e5c0e4edfc35a |
| 105 | D23-OBJECTIVE-11 | OBJECTIVE | no_rot | dataset | SUB-E | false | true | true | REVIEW | false | none | sha256:be0b079b499f02933e9009b1ac4ff15d0ec9a873ee8de2328f3576ce04e57665 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 106 | D23-REJECTED_PATH-01 | REJECTED_PATH | truncation | archive | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:063ef08ac43eede875c8530f42e96892111fe862dac86a6a1a0d37ca4a3f58a1 | sha256:86da5f73049282a883b2e63092ef3298ec46c6b4fe8ef2ad0c9c998fa9d9c9ff |
| 107 | D23-REJECTED_PATH-01 | REJECTED_PATH | truncation | archive | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:ef3a256e043fbcc7421ae9e597dcf52a69d24fd0b0ba8ff6d3ea3e687eab42e8 | sha256:5818684979b59048d8497bfda06f0a8e5c11864d314b330efe8d937008d6f31d |
| 108 | D23-REJECTED_PATH-01 | REJECTED_PATH | truncation | archive | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, rejected-path revival, supersession/history loss, wrong relationship direction | sha256:624e44c0784ea2945b02efe6db0c6c187421b70a21cc2d3a1a4d3113c1b8acd8 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 109 | D23-REJECTED_PATH-01 | REJECTED_PATH | truncation | archive | SUB-E | false | true | true | REVIEW | false | none | sha256:cedcb1f41062f3cacf2f4328402b64c920c9709e8abba88250ad252324c82a7a | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 110 | D23-REJECTED_PATH-01 | REJECTED_PATH | truncation | archive | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, rejected-path revival, supersession/history loss, wrong relationship direction | sha256:5b724ea0cc492aa3c884dbccf2242d267b53d321d97f5013918a6b4445bd5cbd | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 111 | D23-REJECTED_PATH-02 | REJECTED_PATH | truncation | garden | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:fd29dc36506cb575ae3ee466e8d03334a562e805660373ac63f50eb324546a0c | sha256:ef9b38bfee089bffad5fa1e9f7acbc76a49a726a9febd11cc4ce29964a86c134 |
| 112 | D23-REJECTED_PATH-02 | REJECTED_PATH | truncation | garden | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, rejected-path revival, supersession/history loss, wrong relationship direction | sha256:51903fd3bcba20ea13c397db110fc86fde934b839716e27f29a72beb94d4db13 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 113 | D23-REJECTED_PATH-02 | REJECTED_PATH | truncation | garden | SUB-E | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:1a133ab679890c04e505a8c2f3a896b7cdf13ce40bfdebbcb04511723b19efd1 | sha256:d2f11f6147fd22ab67e2dff15caac91555818c15490e2680a2be884fac1293aa |
| 114 | D23-REJECTED_PATH-02 | REJECTED_PATH | truncation | garden | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, rejected-path revival, supersession/history loss, wrong relationship direction | sha256:43bf574517c6d1a88f5859180a94d44a0acc9b7befa177c9eb75969a49c74fc6 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 115 | D23-REJECTED_PATH-02 | REJECTED_PATH | truncation | garden | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss | sha256:f7c19f5494dda293285f6cb78d4d3b285b7dcc7ec865b319a6ff48d356245a3b | sha256:7e149721ed33c15f731d12bbfa982cb63376bf2b0a4116e6cedfc0e17f68ade2 |
| 116 | D23-REJECTED_PATH-11 | REJECTED_PATH | no_rot | sensor | SUB-D | false | false | true | REVIEW | true | capture/lineage mismatch, supersession/history loss | sha256:897626c1726aa4d63a3f6fd489fbcb984c005d976817511df6fad96c48f08b8a | sha256:3e5f28a793dda99d26e072806c2f76de96a0a2a7e541bc730ac1d93d07ac400d |
| 117 | D23-REJECTED_PATH-11 | REJECTED_PATH | no_rot | sensor | SUB-E | false | true | true | REVIEW | false | none | sha256:e4a4e303862681f2ce81f9aaa149cfd3c106e22a70e746088a48fd61bec46d39 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 118 | D23-REJECTED_PATH-11 | REJECTED_PATH | no_rot | sensor | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:8cce8a93f10f546c5b60d6118a71f9fe521618f3b5d3c9834ab0bdd44fbae0b3 | sha256:b392f505849666c6a19882eab0495ece9ef00046aa9d3efe716c14c986c4ea91 |
| 119 | D23-REJECTED_PATH-11 | REJECTED_PATH | no_rot | sensor | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss | sha256:7d61bbbf356d35f5d1499e0eee57c7c351b72de2b4bdc4a1795e179ea16062fe | sha256:79777e688afa91331d2df7215bbf8daf827c0bc4b215d0aeda75f11ef2388b63 |
| 120 | D23-REJECTED_PATH-11 | REJECTED_PATH | no_rot | sensor | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:d82e34724a124c12f51c9dd5fad148ef0651346303992882017c1f7eb3c32cec | sha256:bf91e99b6ffe878dc8ddd49816e2786838900fd5fa81bb81c7fe45bdd19a57c1 |
| 121 | D23-SUPERSESSION-01 | SUPERSESSION | truncation | subtitle | SUB-E | false | true | true | REVIEW | false | none | sha256:ee00d153eb8806ed9b02de365283ad9460f26b9db67ab4eb00ed4e7e7a7f14cc | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 122 | D23-SUPERSESSION-01 | SUPERSESSION | truncation | subtitle | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:aef3f6d62baf58290b744c35a0457eac396f37808d0234b1a4cbaa26b820b7aa | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 123 | D23-SUPERSESSION-01 | SUPERSESSION | truncation | subtitle | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:30f1118c077e074b19d45642cce75ee8f169b7dd6a1684fd0362f8740c0f549c | sha256:9c6cf09d6b681eb73abbc024ce56e0f6fc4160059d16f2a2e7646982b0d5e44b |
| 124 | D23-SUPERSESSION-01 | SUPERSESSION | truncation | subtitle | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:c9d9949757d0315b40bb7fd2f18f952b6da73e2bc3e85c09b51f52e7f51997cf | sha256:417a3222d06f9bd4f851192ed3f077fe3d8ef9af98fa13c2b42cc67f4b7299fe |
| 125 | D23-SUPERSESSION-01 | SUPERSESSION | truncation | subtitle | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:008efa0630499537a7f26ad4668d1cd239ff1ca12c69787056538eccc11bffca | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 126 | D23-SUPERSESSION-02 | SUPERSESSION | truncation | dataset | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:7ab5ab67290639e60bc33e65f8d2ff2bb5ab9c8cd3507ff63cb34d65475f4a79 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 127 | D23-SUPERSESSION-02 | SUPERSESSION | truncation | dataset | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:f1ff886645ce9ac5a7b6637987276b8bb0c15811c74819a9d7ceec25d388c68a | sha256:11db99717ba27542901c477dbcec0235c43b41474c89393212c5f516d3d40168 |
| 128 | D23-SUPERSESSION-02 | SUPERSESSION | truncation | dataset | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:c557b1201d9310641c081e96265b2459ca11c0603fc1fbb912bfb7e5b07b283d | sha256:f51046820f64942f9911cf87a7b59a63f4b6ec54c5bd40430f20391b8126d533 |
| 129 | D23-SUPERSESSION-02 | SUPERSESSION | truncation | dataset | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:cf69808b25bd89aa663f70a49e9d1fcde0cc3964ffe38eb2113cbb74525e2c52 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 130 | D23-SUPERSESSION-02 | SUPERSESSION | truncation | dataset | SUB-E | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:c1e74c2725bfa1ddce4b354cc17644ad2fb289f02df4251ad66fe8a807bff24f | sha256:15e11d61fbf517667b78c433def104a2e2c6dcc9048571e2097057fcaf6754fc |
| 131 | D23-SUPERSESSION-11 | SUPERSESSION | no_rot | library | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:571db889959fed8b139fa9f074f3d62cd595c78f694446053854f6ef245a0afe | sha256:d3c3b986ca3e09280adc14c64479151ab944cc155184c159b1f3caacdc24cdd5 |
| 132 | D23-SUPERSESSION-11 | SUPERSESSION | no_rot | library | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:04da24fac0827218ae7160a4379f7ae295422eba6ab7fd4a55a51aeba424ce24 | sha256:8646c4b0eaa0bc80a0202a567cf08770471b095217fc70adc133ac10b5856b6e |
| 133 | D23-SUPERSESSION-11 | SUPERSESSION | no_rot | library | SUB-D | false | false | true | REVIEW | true | capture/lineage mismatch, wrong relationship direction | sha256:444c03d9accce0da96ba37cb5af004c50f6354325bbd30bc2767a25e4bdf310e | sha256:d4c0f6452df3b0ef2a0f6a67fa342d993d585d8abc586e7c1666f7d57dddd77d |
| 134 | D23-SUPERSESSION-11 | SUPERSESSION | no_rot | library | SUB-E | false | true | true | REVIEW | false | none | sha256:740aebbf089aab16ac99da425b52168c5b9a70d337df5e31bb50b7bdf8e0aad3 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 135 | D23-SUPERSESSION-11 | SUPERSESSION | no_rot | library | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:670fcf793969f022ab28b5b08e9a2d7c6236bd8a58bd6b349530bd2394d83518 | sha256:62560ecf43c24d54e4d5fb788f18b518956b0db98e5bf066f84c24cad1e439da |
| 136 | D23-UNRESOLVED_DEPENDENCY-01 | UNRESOLVED_DEPENDENCY | truncation | theatre | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:db42cace8b4180170c7fd0bb6080f695a038346e5afd1399d4ce6cb5152861bd | sha256:77b05e1e3e06e2c090f811cf6b401af4fb0076c51cc91d2957bfa0b51dfe34ed |
| 137 | D23-UNRESOLVED_DEPENDENCY-01 | UNRESOLVED_DEPENDENCY | truncation | theatre | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, dependency ignored, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:75fcf54732b12e42f449c5cafbad392a173ae3d0d7352fcabd834920db7c7925 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 138 | D23-UNRESOLVED_DEPENDENCY-01 | UNRESOLVED_DEPENDENCY | truncation | theatre | SUB-E | false | true | true | REVIEW | false | none | sha256:fa7b4b1a3038a8e8e8d27fbecec7dffdfffb2a62c9052b337857dc89a8b03715 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 139 | D23-UNRESOLVED_DEPENDENCY-01 | UNRESOLVED_DEPENDENCY | truncation | theatre | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, dependency ignored, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:6dd109196d3bbce76ac8bb5883d883ac6d5775657e03d584f6cb9e16740715c4 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 140 | D23-UNRESOLVED_DEPENDENCY-01 | UNRESOLVED_DEPENDENCY | truncation | theatre | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:580ebc0f444d4b96169a540fb91c6b81a249d88553197bb08c2ae4551fea2d40 | sha256:2fdb21ede2415bec0d06d4332710fe302f46f93a17dd273c1f284cd65615a3fc |
| 141 | D23-UNRESOLVED_DEPENDENCY-02 | UNRESOLVED_DEPENDENCY | truncation | library | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, dependency ignored, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:36ec916f0aa1b1f7abeed4c3af9109fa9afaec446fc44d9a51266ebc6c5d711b | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 142 | D23-UNRESOLVED_DEPENDENCY-02 | UNRESOLVED_DEPENDENCY | truncation | library | SUB-E | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:5fd1a1e2192031088273e582fe6c36938f8fd7f5c59916195b052fac506279d4 | sha256:f06c8a40caa6274691943c7667befbe3806815076689f05935a17d9665f5ed1d |
| 143 | D23-UNRESOLVED_DEPENDENCY-02 | UNRESOLVED_DEPENDENCY | truncation | library | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, dependency ignored, enumeration/format failure, supersession/history loss, wrong relationship direction | sha256:9c6fd9fbbb3108b185486029674374d23d52b10e4b33b75551e2f30a1715eb20 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 144 | D23-UNRESOLVED_DEPENDENCY-02 | UNRESOLVED_DEPENDENCY | truncation | library | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:88f21d13d0f45196cc6eeb238c7fa67754c75bdfe722e25e9a083166b1d0a556 | sha256:59e0fae1a45c155da511fd90ca9369dca16f6bfd307f19a141f0bb2c08dbacf0 |
| 145 | D23-UNRESOLVED_DEPENDENCY-02 | UNRESOLVED_DEPENDENCY | truncation | library | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:bf6d40de56824098cfc4c3ff8a1b80d98cb07cf63ab72d7a78d1051ba67fa03d | sha256:e8663bf5564d0376f1c2556d49cabfdd28118628061312aa81cb93cd1229fb3a |
| 146 | D23-UNRESOLVED_DEPENDENCY-11 | UNRESOLVED_DEPENDENCY | no_rot | archive | SUB-E | false | true | true | REVIEW | false | none | sha256:0d371ff6010a859fff499e877aa702ec89f2d9cb912123d5b57d2acfbfbd478a | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 147 | D23-UNRESOLVED_DEPENDENCY-11 | UNRESOLVED_DEPENDENCY | no_rot | archive | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:d31a1e38f19890bed007376e7129a6b7abedb81b86921e954e59a9d55c2fdf3a | sha256:742cb0fc16a97f5280e908ec97971314809fb6c31c2ccc338956da07a4b184e9 |
| 148 | D23-UNRESOLVED_DEPENDENCY-11 | UNRESOLVED_DEPENDENCY | no_rot | archive | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:7dfe1a8f10dfe3caae74709b86393057f9a38c7ae3f4ff0d985076829b666279 | sha256:36e5531d622b8aca43725e978d9ca3340b569399b290536c5037a5ae025606d9 |
| 149 | D23-UNRESOLVED_DEPENDENCY-11 | UNRESOLVED_DEPENDENCY | no_rot | archive | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:6814008ddacf9086c09cd8a005a7a050c3d79f00f06b6adb00b261e1ec8b02bd | sha256:8ced302cc9ac8e31e8a7fe8886b51d598437e8095737f5937dce690001a5ca17 |
| 150 | D23-UNRESOLVED_DEPENDENCY-11 | UNRESOLVED_DEPENDENCY | no_rot | archive | SUB-D | false | false | true | REVIEW | true | capture/lineage mismatch, wrong relationship direction | sha256:7ed5670f777030da22e296077fbb3d3ec1a4e6e62d82060aee0b74679e0a2a71 | sha256:039d9f569f12d4e42e9a13bddf5fab7c7f2b4ac1cba7c9f86bcc65ee4134b29d |
| 151 | D23-WORKSTREAM-01 | WORKSTREAM | truncation | dataset | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:d0b20b682dee1698b688d1ebb5e04837c3db3c10b8e8d4739edd614f97372b40 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 152 | D23-WORKSTREAM-01 | WORKSTREAM | truncation | dataset | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:1d7d888966bba563c55560b0c165176082577fd47733d01e45eef0d12fedd482 | sha256:17f0b741d8711dd58d796723eb3f38eaaecf17cccb9a8010667f5a25600ccf44 |
| 153 | D23-WORKSTREAM-01 | WORKSTREAM | truncation | dataset | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss | sha256:76aecf7448ca7e62cf9b52cb655101297e9025d737d0faebe73e9ce178437bcb | sha256:c7ad889a4720be1f9991fbf23a7a3e4a80e4063d0218bf02144d81db1b897d95 |
| 154 | D23-WORKSTREAM-01 | WORKSTREAM | truncation | dataset | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:5ec5f56f665a8eff1d70364e613a19b768e5a3d296ef62d8755dd24ed6e5bc0a | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 155 | D23-WORKSTREAM-01 | WORKSTREAM | truncation | dataset | SUB-E | false | true | true | REVIEW | false | none | sha256:6f8f55477fd43eb1375c935d999c835ccb78edb1d856e7288d4e8be64c96103d | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 156 | D23-WORKSTREAM-02 | WORKSTREAM | truncation | game | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:46bb78a4f417c91a129280afeef610c0dd20dc9522a68bbe7d87e5995f19eec8 | sha256:75a4aa9901ab286509c863391ae809cc6d8c889a6e38cdafe8fd7dec2046688a |
| 157 | D23-WORKSTREAM-02 | WORKSTREAM | truncation | game | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:bb8508e29a9d29c2604385f0d2b8ccbfc8c072ab82e8d2b0e03f89e184fc78a6 | sha256:ac81c802e2275dab8cc7490785f0999739e62eba3efeee77e464378ec2048a09 |
| 158 | D23-WORKSTREAM-02 | WORKSTREAM | truncation | game | SUB-D | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:13a5668f49a952f42cb07b2513abeb01b41763b599dfe41f9b1e6b2abe863a37 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 159 | D23-WORKSTREAM-02 | WORKSTREAM | truncation | game | SUB-E | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:ff7f925182a1143998442b205e26398d8c3ae2ca10aca48bc178a4721f08b60f | sha256:7b3b71f3b57651351ff5f2d57636541ea1fe0c9bc19a452437b9def81f426fd9 |
| 160 | D23-WORKSTREAM-02 | WORKSTREAM | truncation | game | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:a68a9aa05a01b03f46e57e34abd053050a31fd81318c38ea4292ccabc42dab4e | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 161 | D23-WORKSTREAM-11 | WORKSTREAM | no_rot | robot | SUB-C | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:ce26b4e26136d8704aee04a7d61c1c96f2ed8b52d3f9a546717e8aa8025987e9 | sha256:ea7182f4c5b1cb8121caa576f0801a9fb4ee269b9a206c0ae2d19f66c4a8a632 |
| 162 | D23-WORKSTREAM-11 | WORKSTREAM | no_rot | robot | SUB-D | false | false | true | REVIEW | true | capture/lineage mismatch, enumeration/format failure, objective/workstream substitution, supersession/history loss, wrong relationship direction | sha256:9a4334af451e58c4700e686fefdfcbf99a3c9d47a39278dd476e9bb4cd69ecd2 | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 163 | D23-WORKSTREAM-11 | WORKSTREAM | no_rot | robot | SUB-E | false | true | true | REVIEW | false | none | sha256:b74eda9d65ca775a910b5334ec8a94b89c4d9d3d27d185838ad0546bc20f484b | sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535 |
| 164 | D23-WORKSTREAM-11 | WORKSTREAM | no_rot | robot | SUB-A | false | false | true | REVIEW | false | capture/lineage mismatch, supersession/history loss, wrong relationship direction | sha256:7dcc0d79e7ec8f495e1109bc35af4109d43ebaef40476978b398b47f6f1bcfc7 | sha256:bdf559173c61c5923d5c9968e6b4adc27e871bbde408dcb71985904db9ee4ae7 |
| 165 | D23-WORKSTREAM-11 | WORKSTREAM | no_rot | robot | SUB-B | false | false | true | REVIEW | false | capture/lineage mismatch, wrong relationship direction | sha256:e0211b8ee2b13671ea720ca7cffe2da06c276aa17e4a08f3aefef6a868b4d2d4 | sha256:67a7892aef52de13507c73eb79e93b539f631a677d7b146e3980f7f51f46b818 |

Raw visible prompts, bounded responses, native ID maps, packet lineage and oracle outputs are preserved in `raw_matrix.jsonl`; call claims are preserved in `claims.jsonl`. No row was retried, repaired, selected best-of, or silently discarded.
