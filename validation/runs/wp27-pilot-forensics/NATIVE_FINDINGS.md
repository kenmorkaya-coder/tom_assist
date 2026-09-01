# WP-27 native-store and cohort forensics

> **POST-HOC DIAGNOSTIC ONLY — ZERO GENERATIONS.** Preserved stores were opened immutable/read-only. Frozen H0 is untouched; no G-gate verdict is made.

## Findings

- **No battery exchange committed into ToM physics.** Runtime commit receipts: **0/165**. All evaluations were unresolved REVIEW; the 33 created SUB-D trees remain byte-identical at seed tick 4707 with zero usage rotation. Therefore the observed committed-turn `semantic_target`/`wind_vec` population is empty.
- **Counterfactual old commit projection, not observed physics:** applying the then-current SHA-byte formula to the 165 sent user turns yields **0/165** near-uniform targets under the native selector's ±1/60 rule. `wind_vec` magnitude min/median/p95/max is **0.032061 / 0.380386 / 0.814714 / 1.259567** (mean 0.404164). Row-level values are in `commit_projection_analysis.jsonl`.
- **Native import was complete and typed:** **2310/2310** objects and **1155/1155** edges were present across 165 ledgers; all **165/165** ID sets and **165/165** core-field sets matched. The ledgers contain only the captured user/assistant turns (**330 total**), not the planted history turns; **0/2310** object source IDs exist as ledger turns. The objects were not merely turn text.
- **Uniform-axis fallback never fired:** **0/33** SUB-D previews; stored alignment traces agree in 33/33. All selected-branch usage counts were zero, so usage rotation contributed nothing.
- **3-axis cohort composition:** of 528 selected slots, **132** were also in stiffness/usage-only top-16 and **396** were displaced into the cohort by alignment. This is 4 stiffness-supported + 12 alignment-displaced in every case.
- **Offline 8D re-rank:** current 3-axis and native `rank_loading_aware_8d` top-16 cohorts overlap in **0/528** slots (mean overlap 0.0; mean Jaccard 0.000). Each method produced 2 / 2 distinct cohort sets across 33 cases.
- **Observed retrieval/citation failure attributable to 3-axis selection: 0 cases.** SUB-D typed focus objects were admitted in **33/33** packets. Every per-project RGM was empty, so both the stored 3-axis trace and the offline 8D alternative have **0 anchor candidates**. Cohort replacement radically changes branch IDs but cannot create a missing anchor or affect typed-state admission in these artifacts.

## Per-case cohort composition and 8D comparison

`Stiffness-supported` is overlap with the pure stiffness/(1+usage) top-16. `Alignment-displaced` is the remainder of the selected 3-axis cohort. This partitions the stored cohort without claiming a causal model.

| Case | Mode | Fallback | Stiffness-supported | Alignment-displaced | 3D∩8D | Jaccard | RGM candidates | Focus hit |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| D23-ASSUMPTION-01 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-ASSUMPTION-02 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-ASSUMPTION-11 | no_rot | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-COMPLETED_WORK-01 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-COMPLETED_WORK-02 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-COMPLETED_WORK-11 | no_rot | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-CONCEPT-01 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-CONCEPT-02 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-CONCEPT-11 | no_rot | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-CONSTRAINT-01 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-CONSTRAINT-02 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-CONSTRAINT-11 | no_rot | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-DECISION-01 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-DECISION-02 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-DECISION-11 | no_rot | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-EVIDENCE-01 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-EVIDENCE-02 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-EVIDENCE-11 | no_rot | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-OBJECTIVE-01 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-OBJECTIVE-02 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-OBJECTIVE-11 | no_rot | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-REJECTED_PATH-01 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-REJECTED_PATH-02 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-REJECTED_PATH-11 | no_rot | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-SUPERSESSION-01 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-SUPERSESSION-02 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-SUPERSESSION-11 | no_rot | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-UNRESOLVED_DEPENDENCY-01 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-UNRESOLVED_DEPENDENCY-02 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-UNRESOLVED_DEPENDENCY-11 | no_rot | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-WORKSTREAM-01 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-WORKSTREAM-02 | truncation | false | 4 | 12 | 0 | 0.000 | 0 | true |
| D23-WORKSTREAM-11 | no_rot | false | 4 | 12 | 0 | 0.000 | 0 | true |

## Boundary

The 8D comparison calls only the pinned pure `rank_loading_aware_8d` over inert copies of each stored seed tree and the same stored probe-derived load signature. It does not call `engine.step`, `ToMClient.process`, `rgm.read_memory`, gateway preview endpoints, a provider, or a broker. No frozen file, per-case database, tree, upstream checkout, golden, or preregistration was modified.
