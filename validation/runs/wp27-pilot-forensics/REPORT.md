# WP-27 — post-hoc forensic audit of WP-25 frozen pilot v2

> **POST-HOC DIAGNOSTIC ONLY — ZERO GENERATIONS.** The frozen oracle, matrix, Appendix C, and hypothesis resolution were not changed. **H0 remains HOLDS exactly as frozen.** This report makes no G-gate verdict.

## Owner-review findings

1. **The `capture/lineage mismatch` label does not describe a failed capture.** All 165 responses were captured exactly once. The taxonomy attaches that label whenever `cited_state_ids` is not byte-for-byte/list-order equal and the row is neither exact nor an accepted SUB-E mismatch. Citation equality failed in all 165 rows, but 22 accepted SUB-E stale-version fallbacks exit taxonomy early; therefore Appendix C reports 143 label occurrences. The universal condition is citation-list inequality, not capture loss.
2. **Native-ID list order is the dominant exact-oracle failure.** Authored answers were sorted in logical ID space, then UUIDv5-mapped without re-sorting. The prompt asks providers to return sorted lists, so responses commonly sort the resulting UUID strings. The frozen oracle correctly applies its preregistered exact list-order rule; a diagnostic multiset comparison finds all fields semantically equal in 33/33 SUB-C rows. This observation is not a rescore and does not alter H0.
3. **SUB-D retrieved the load-bearing objects, but its renderer hid their object IDs.** The focus object was admitted in 33/33 packets, and all 207/207 expected current citation objects were admitted. Yet only 3/207 expected current IDs appear in the rendered state block (the WORKSTREAM ID in its header); object rows render text without `state_id`. Across the whole prompt, the 22 long cases expose only 2/138 current IDs and 0/44 historical IDs. The 11 no-rot controls expose all IDs through visible history, not through the packet renderer.
4. **Packet budget did not cause the misses.** Every SUB-D packet admitted 12/14 objects. The other 2 were the superseded old concept and old decision, excluded by `superseded-positive`, not budget. There were 0 `packet-budget` exclusions; packets used 453–484 estimated tokens of the configured 500-token budget.
5. **Appendix `Response SHA` is a mislabeled canonical-value digest.** The Rust driver applies `canonical_sha256` to a string, hashing its canonical JSON string encoding (quotes and escaping included). All 165 reported values match that encoding and 0/165 match SHA-256 of the raw UTF-8 response bytes. The correction table preserves both. The same label/encoding issue applies to `Prompt SHA`.
6. **SUB-D/SUB-E ID spaces are deterministic and distinct.** SUB-D response references are entirely its own arm-native UUID space. SUB-E's 22 stale-version cases use own-arm IDs and correctly return the accepted fallback; its 11 wrong-project cases are deliberately prefixed `FOREIGN-`, and their responses copy that foreign space rather than leaking another arm's UUIDs.
7. **Additional reporting defect:** the cluster-bootstrap implementation collapses the two arm rows for each case into one dictionary entry before pairing, producing 0 valid / 10,000 invalid replicates. Fixing that reporting code cannot rescue frozen H1 here: every arm's frozen exact rate is zero and the other primary H1 conditions still fail. H0 remains untouched.

## Capture/taxonomy accounting

- Captures: **165/165**; rows with `capture_count == 1`: **165/165**.
- Rows with exact `cited_state_ids`: **0/165**.
- Rows labeled `capture/lineage mismatch`: **143**.
- Accepted SUB-E explicit mismatches omitted from failure taxonomy: **22**.

## Per-field mismatch breakdown

`set/order` means multiset-equal rows / order-only rows. Missing and extra are item counts across the 33 rows. These columns are diagnostic only.

| Arm | Field | Exact | Set/order | Missing | Extra |
|---|---|---:|---:|---:|---:|
| SUB-A | `action_id` | 12/33 | — | — | — |
| SUB-A | `rejected_action_ids` | 12/33 | 12/0 | 63 | 0 |
| SUB-A | `cited_state_ids` | 0/33 | 10/10 | 139 | 6 |
| SUB-A | `historical_state_ids` | 5/33 | 11/6 | 44 | 2 |
| SUB-A | `relationships` | 1/33 | 11/10 | 78 | 3 |
| SUB-A | `proposed_mutations` | 33/33 | 33/0 | 0 | 0 |
| SUB-A | `authority` | 33/33 | — | — | — |
| SUB-B | `action_id` | 33/33 | — | — | — |
| SUB-B | `rejected_action_ids` | 33/33 | 33/0 | 0 | 0 |
| SUB-B | `cited_state_ids` | 0/33 | 29/29 | 5 | 5 |
| SUB-B | `historical_state_ids` | 20/33 | 33/13 | 0 | 0 |
| SUB-B | `relationships` | 4/33 | 29/25 | 4 | 4 |
| SUB-B | `proposed_mutations` | 33/33 | 33/0 | 0 | 0 |
| SUB-B | `authority` | 33/33 | — | — | — |
| SUB-C | `action_id` | 33/33 | — | — | — |
| SUB-C | `rejected_action_ids` | 33/33 | 33/0 | 0 | 0 |
| SUB-C | `cited_state_ids` | 0/33 | 33/33 | 0 | 0 |
| SUB-C | `historical_state_ids` | 14/33 | 33/19 | 0 | 0 |
| SUB-C | `relationships` | 4/33 | 33/29 | 0 | 0 |
| SUB-C | `proposed_mutations` | 33/33 | 33/0 | 0 | 0 |
| SUB-C | `authority` | 33/33 | — | — | — |
| SUB-D | `action_id` | 7/33 | — | — | — |
| SUB-D | `rejected_action_ids` | 7/33 | 7/0 | 78 | 0 |
| SUB-D | `cited_state_ids` | 0/33 | 6/6 | 164 | 1 |
| SUB-D | `historical_state_ids` | 4/33 | 7/3 | 52 | 0 |
| SUB-D | `relationships` | 1/33 | 7/6 | 92 | 0 |
| SUB-D | `proposed_mutations` | 33/33 | 33/0 | 0 | 0 |
| SUB-D | `authority` | 33/33 | — | — | — |
| SUB-E | `action_id` | 11/33 | — | — | — |
| SUB-E | `rejected_action_ids` | 11/33 | 11/0 | 66 | 0 |
| SUB-E | `cited_state_ids` | 0/33 | 0/0 | 207 | 69 |
| SUB-E | `historical_state_ids` | 0/33 | 0/0 | 66 | 22 |
| SUB-E | `relationships` | 0/33 | 0/0 | 117 | 39 |
| SUB-E | `proposed_mutations` | 33/33 | 33/0 | 0 | 0 |
| SUB-E | `authority` | 33/33 | — | — | — |

Fallback action counts: SUB-A 21/33, SUB-B 0/33, SUB-C 0/33, SUB-D 26/33, SUB-E 22/33. All 165 answer shapes were valid; `proposed_mutations` and `authority` matched in every row.

## Native ID-space mapping

- SUB-D: 108 citation/relationship reference occurrences; {"own_arm_native":108}.
- SUB-E: 169 occurrences; {"foreign_ablation":169}.
- Mapping rule: per case and arm, each logical ID is converted with UUIDv5 namespace `3ed820e0-f06b-5e51-85b7-7a94864c9d6a` and name `<test_id>:<arm>\0<logical_id>`. Action IDs are not state-object IDs and remain authored strings.
- SUB-E ablation split: 22 stale-state/version rows (accepted explicit mismatch) and 11 wrong-project rows with planted `FOREIGN-` IDs (not contained). There is no observed cross-arm UUID leakage.

## SUB-D packet-content accounting

- Load-bearing focus retrieval: **33/33 (100%)**.
- Expected current objects admitted: **207/207**; object IDs rendered in state block: **3/207**; visible anywhere in full prompt: **71/207**.
- Expected historical objects admitted: **0/66**; IDs rendered in state block: **0/66**; visible anywhere in full prompt: **22/66**.
- Total admitted/excluded: **396 / 66**. Exclusion reasons: `{"superseded-positive":66}`. Budget exclusions: **0**.

| Case | Mode | Focus (section; selection) | Focus hit | Current admitted | Current ID visible | Historical ID visible | Tokens | Excluded |
|---|---|---|---:|---:|---:|---:|---:|---|
| D23-ASSUMPTION-01 | truncation | assumption (RETRIEVED_ANCHORS; hard-gate-pass + ranked) | yes | 7/7 | 0/7 | 0/2 | 474 | decision-old:superseded-positive, concept-old:superseded-positive |
| D23-ASSUMPTION-02 | truncation | assumption (RETRIEVED_ANCHORS; hard-gate-pass + ranked) | yes | 7/7 | 0/7 | 0/2 | 473 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-ASSUMPTION-11 | no_rot | assumption (RETRIEVED_ANCHORS; hard-gate-pass + ranked) | yes | 7/7 | 7/7 | 2/2 | 465 | decision-old:superseded-positive, concept-old:superseded-positive |
| D23-COMPLETED_WORK-01 | truncation | completed (COMPLETED_WORK - DO NOT REPROPOSE AS OPEN; hard-gate-pass + ranked) | yes | 7/7 | 0/7 | 0/2 | 455 | decision-old:superseded-positive, concept-old:superseded-positive |
| D23-COMPLETED_WORK-02 | truncation | completed (COMPLETED_WORK - DO NOT REPROPOSE AS OPEN; hard-gate-pass + ranked) | yes | 7/7 | 0/7 | 0/2 | 466 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-COMPLETED_WORK-11 | no_rot | completed (COMPLETED_WORK - DO NOT REPROPOSE AS OPEN; hard-gate-pass + ranked) | yes | 7/7 | 7/7 | 2/2 | 464 | decision-old:superseded-positive, concept-old:superseded-positive |
| D23-CONCEPT-01 | truncation | concept (LOAD_BEARING_CONCEPTS; hard-gate-pass + ranked) | yes | 5/5 | 0/5 | 0/2 | 469 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-CONCEPT-02 | truncation | concept (LOAD_BEARING_CONCEPTS; hard-gate-pass + ranked) | yes | 5/5 | 0/5 | 0/2 | 464 | decision-old:superseded-positive, concept-old:superseded-positive |
| D23-CONCEPT-11 | no_rot | concept (LOAD_BEARING_CONCEPTS; hard-gate-pass + ranked) | yes | 5/5 | 5/5 | 2/2 | 461 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-CONSTRAINT-01 | truncation | constraint (BINDING_CONSTRAINTS; hard-gate-pass + non-evictable) | yes | 5/5 | 0/5 | 0/2 | 463 | decision-old:superseded-positive, concept-old:superseded-positive |
| D23-CONSTRAINT-02 | truncation | constraint (BINDING_CONSTRAINTS; hard-gate-pass + non-evictable) | yes | 5/5 | 0/5 | 0/2 | 475 | decision-old:superseded-positive, concept-old:superseded-positive |
| D23-CONSTRAINT-11 | no_rot | constraint (BINDING_CONSTRAINTS; hard-gate-pass + non-evictable) | yes | 5/5 | 5/5 | 2/2 | 470 | decision-old:superseded-positive, concept-old:superseded-positive |
| D23-DECISION-01 | truncation | decision (HELD_DECISIONS; hard-gate-pass + ranked) | yes | 6/6 | 0/6 | 0/2 | 464 | decision-old:superseded-positive, concept-old:superseded-positive |
| D23-DECISION-02 | truncation | decision (HELD_DECISIONS; hard-gate-pass + ranked) | yes | 6/6 | 0/6 | 0/2 | 462 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-DECISION-11 | no_rot | decision (HELD_DECISIONS; hard-gate-pass + ranked) | yes | 6/6 | 6/6 | 2/2 | 484 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-EVIDENCE-01 | truncation | evidence (EVIDENCE_BOUNDARY; hard-gate-pass + ranked) | yes | 8/8 | 0/8 | 0/2 | 465 | decision-old:superseded-positive, concept-old:superseded-positive |
| D23-EVIDENCE-02 | truncation | evidence (EVIDENCE_BOUNDARY; hard-gate-pass + ranked) | yes | 8/8 | 0/8 | 0/2 | 474 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-EVIDENCE-11 | no_rot | evidence (EVIDENCE_BOUNDARY; hard-gate-pass + ranked) | yes | 8/8 | 8/8 | 2/2 | 453 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-OBJECTIVE-01 | truncation | objective (ACTIVE_OBJECTIVE; hard-gate-pass + non-evictable) | yes | 6/6 | 0/6 | 0/2 | 484 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-OBJECTIVE-02 | truncation | objective (ACTIVE_OBJECTIVE; hard-gate-pass + non-evictable) | yes | 6/6 | 0/6 | 0/2 | 469 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-OBJECTIVE-11 | no_rot | objective (ACTIVE_OBJECTIVE; hard-gate-pass + non-evictable) | yes | 6/6 | 6/6 | 2/2 | 470 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-REJECTED_PATH-01 | truncation | rejected (REJECTED_OR_SUPERSEDED - DO NOT REVIVE WITHOUT EXPLICIT RECONSIDERATION; hard-gate-pass + non-evictable) | yes | 6/6 | 0/6 | 0/2 | 475 | decision-old:superseded-positive, concept-old:superseded-positive |
| D23-REJECTED_PATH-02 | truncation | rejected (REJECTED_OR_SUPERSEDED - DO NOT REVIVE WITHOUT EXPLICIT RECONSIDERATION; hard-gate-pass + non-evictable) | yes | 6/6 | 0/6 | 0/2 | 455 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-REJECTED_PATH-11 | no_rot | rejected (REJECTED_OR_SUPERSEDED - DO NOT REVIVE WITHOUT EXPLICIT RECONSIDERATION; hard-gate-pass + non-evictable) | yes | 6/6 | 6/6 | 2/2 | 465 | decision-old:superseded-positive, concept-old:superseded-positive |
| D23-SUPERSESSION-01 | truncation | supersession (SUPERSESSION_NOTES; hard-gate-pass + ranked) | yes | 7/7 | 0/7 | 0/2 | 474 | decision-old:superseded-positive, concept-old:superseded-positive |
| D23-SUPERSESSION-02 | truncation | supersession (SUPERSESSION_NOTES; hard-gate-pass + ranked) | yes | 7/7 | 0/7 | 0/2 | 471 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-SUPERSESSION-11 | no_rot | supersession (SUPERSESSION_NOTES; hard-gate-pass + ranked) | yes | 7/7 | 7/7 | 2/2 | 466 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-UNRESOLVED_DEPENDENCY-01 | truncation | dependency (UNRESOLVED_DEPENDENCIES; hard-gate-pass + ranked) | yes | 6/6 | 0/6 | 0/2 | 468 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-UNRESOLVED_DEPENDENCY-02 | truncation | dependency (UNRESOLVED_DEPENDENCIES; hard-gate-pass + ranked) | yes | 6/6 | 0/6 | 0/2 | 468 | decision-old:superseded-positive, concept-old:superseded-positive |
| D23-UNRESOLVED_DEPENDENCY-11 | no_rot | dependency (UNRESOLVED_DEPENDENCIES; hard-gate-pass + ranked) | yes | 6/6 | 6/6 | 2/2 | 477 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-WORKSTREAM-01 | truncation | workstream (RETRIEVED_ANCHORS; hard-gate-pass + ranked) | yes | 6/6 | 1/6 | 0/2 | 470 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-WORKSTREAM-02 | truncation | workstream (RETRIEVED_ANCHORS; hard-gate-pass + ranked) | yes | 6/6 | 1/6 | 0/2 | 461 | concept-old:superseded-positive, decision-old:superseded-positive |
| D23-WORKSTREAM-11 | no_rot | workstream (RETRIEVED_ANCHORS; hard-gate-pass + ranked) | yes | 6/6 | 6/6 | 2/2 | 474 | decision-old:superseded-positive, concept-old:superseded-positive |

The packet manifest and provider-visible text are different evidence surfaces. `packet_sections` proves retrieval/admission; only `prompt` proves what the provider could cite. The renderer includes project/workstream metadata in the header but omits `PacketItem.state_id` from ordinary object lines.

## Response-SHA correction

- Reported equals canonical JSON-string SHA: **165/165**.
- Reported equals raw UTF-8 response SHA: **0/165**.
- Distinct response texts / reported digests: **97 / 97**; no digest-to-multiple-text binding was observed.
- Sequence 1 example: reported `sha256:562d8da9d0238370c21867e572b5a4194ad4a4e8b0673d4ec74914a6e5564535`; raw UTF-8 `sha256:43ce04f25b6d884a5d1819b2b0c7edab3124399f50857dc6d8aefdaa8db981bc`.

## Reproducibility and boundaries

- Frozen source matrix: `sha256:f30e87a6ccfed975228a2ac346f2fc178d549c13b5c6624b28cbf1f652d16454` (165 rows).
- Frozen Appendix C: `sha256:9aa7030c084c9fa25540398b54c314e74c5533ad2811480d4e3ba7a15ccc5b32`.
- Frozen run manifest: `sha256:ca809467e5a818140a7b49913b4b9db5a7bf580e2572eb54b4d861b3a1f2fb56`.
- Derived row-level evidence: `field_mismatch_rows.jsonl`, `sub_d_packet_analysis.jsonl`, and `response_sha_audit.jsonl`. `report.json` contains the machine-readable summaries.
- The forensic program only reads frozen files and writes this derivative directory. Provider calls/generations: **0**. No gateway, broker, runtime, OAuth, preview, upstream checkout, frozen golden, or frozen artifact was invoked or modified. Port 18790 was not used.

## Frozen outcome boundary

**H1 DOES_NOT_HOLD; H0 HOLDS; H2 NOT_TRIGGERED_REQUIRES_H1; H3 NOT_OBSERVED — unchanged from the frozen Appendix C.** Ordering-normalized comparisons, renderer answerability, SHA corrections, and bootstrap-code diagnosis are post-hoc explanations only. They are not substituted metrics, not amended preregistration, not a rerun, and not a G-gate verdict.
