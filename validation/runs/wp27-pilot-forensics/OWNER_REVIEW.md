# WP-27+28 owner review — pilot forensics and governed-change stop

> **POST-HOC DIAGNOSTIC ONLY. ZERO GENERATIONS. FROZEN H0 UNTOUCHED. NO G-GATE VERDICT.**

## WP-27 findings

1. **No pilot exchange committed into ToM physics.** All 165 ledgers have zero `runtime_commit_receipts`; all evaluations remained unresolved REVIEW. The 33 SUB-D runtime trees are byte-identical at seed tick 4707 with zero branch usage. The observed committed-turn population for `semantic_target` and `wind_vec` is therefore empty. As a separate, explicitly counterfactual diagnostic, applying the old SHA-byte commit formula to the 165 sent user turns gives 0/165 near-uniform targets under the selector's ±1/60 rule and wind magnitude min/median/p95/max **0.032061 / 0.380386 / 0.814714 / 1.259567**.
2. **Uniform-axis fallback did not fire.** It was false in 0/33 SUB-D cases; the preserved branch trace agrees in all 33. Every selected branch had `usage_count=0`, so usage rotation contributed nothing. Comparing each 16-branch cohort with a pure stiffness/(1+usage) top-16 partitions every case as **4 stiffness-supported + 12 alignment-displaced**.
3. **The 3-axis and loading-aware 8D cohorts are completely different, but that did not cause this pilot's retrieval failure.** Offline canonical `rank_loading_aware_8d` re-ranking over the same stored trees and probe-derived load signatures gives **0/528 overlapping cohort slots**, mean Jaccard 0.000. However, all 33 per-project RGMs were empty, the stored retrieval traces had zero anchor candidates, typed state objects bypass that branch/anchor ranker, and every case's focus object was already admitted. Observed failures attributable to 3-axis selection in this matrix: **0**.
4. **Planted objects were native typed state, not merely transcript text.** All **2,310/2,310 objects** and **1,155/1,155 edges** were present across the 165 native ledgers. All 165 ID sets and core-field sets match the deterministic inputs. The ledgers contain only 330 captured user/assistant turns; none of the 2,310 object source-turn IDs are ledger turns. Each SUB-D packet admitted 12/14 objects, including the load-bearing focus object in **33/33** cases. The excluded pair was always superseded old concept + old decision (`superseded-positive`); `packet-budget` exclusions were **0**.
5. **Retrieval and answerability were conflated.** SUB-D admitted all **207/207 expected current citation objects**, but the provider-facing state block rendered only **3/207 object IDs** because ordinary packet lines emit text without `state_id`. Across the full prompt, long-context cases exposed only **2/138 current IDs** and **0/44 historical IDs**; no-rot histories exposed their IDs outside the packet. Thus the focus retrieval rate is 100%, while citation answerability is poor.
6. **`capture/lineage mismatch` is a taxonomy name, not capture loss.** All **165/165** responses were captured once. Exact `cited_state_ids` equality failed 165/165; the taxonomy emits its label for the 143 non-contained rows, while 22 accepted SUB-E stale-version fallbacks exit taxonomy early. Native UUID mapping preserved authored logical-list order without re-sorting; providers usually sorted UUID strings. Diagnostic multiset comparison matches every field in **33/33 SUB-C** rows, but this is not a rescore and H0 is unchanged.
7. **SUB-D/SUB-E ID spaces behaved deterministically.** SUB-D produced 108 citation/relationship references, all in its own arm-native UUID space. SUB-E produced 169 references, all deliberately planted `FOREIGN-` identifiers from its 11 wrong-project cases; its 22 stale-version cases returned the accepted empty-list fallback. No cross-arm UUID leakage was observed.
8. **Appendix `Response SHA` is mislabeled.** All 165 reported digests hash the canonical JSON encoding of the response string (including JSON quotes/escaping); **0/165** hash raw response UTF-8. The same issue applies to `Prompt SHA`. The correction mapping preserves reported, canonical-value, and raw-text hashes without editing the frozen Appendix or matrix.
9. **Additional reporting bug:** the cluster bootstrap overwrites one of each case's paired arm rows before sampling, causing 0 valid / 10,000 invalid replicates. This cannot rescue frozen H1: every frozen exact arm rate is zero and the remaining primary conditions still fail. Frozen H0 remains **HOLDS**.

Machine-readable evidence is in:

- `report.json`, `field_mismatch_rows.jsonl`, `sub_d_packet_analysis.jsonl`, `response_sha_audit.jsonl`;
- `native_report.json`, `native_case_analysis.jsonl`, `commit_projection_analysis.jsonl`, `cohort_rerank_analysis.jsonl`;
- human-readable full field/packet report `REPORT.md` and native/cohort report `NATIVE_FINDINGS.md`.

Frozen inputs remain unchanged: `raw_matrix.jsonl` SHA-256 `f30e87a6ccfed975228a2ac346f2fc178d549c13b5c6624b28cbf1f652d16454`; Appendix C SHA-256 `9aa7030c084c9fa25540398b54c314e74c5533ad2811480d4e3ba7a15ccc5b32`; run manifest SHA-256 `ca809467e5a818140a7b49913b4b9db5a7bf580e2572eb54b4d861b3a1f2fb56`.

## WP-28 — STOPPED before product changes

**ESCALATE WP28-1: the pinned runtime does not expose the canonical loading-aware commit-drive surface described by the work package.** No WP-28 product code was changed.

Read-only inspection at pinned upstream SHA `e9fdef81c8a366ebbec07be9772189eea15cb2ac` found:

- `agency/mechanics/msr_8d_loading_aware_readout.py:1-6` explicitly labels the channel-separated loading-aware 8D machinery **shadow/read-only** and says it does not turn on authority or replace the production routing basis. Its pure projection is at `:49-100`; its pure ranker is at `:153-184`.
- `controller/tom_controller.py:4354-4368` calls `sicd.step` with 3D `semantic_target` / `semantic_excitation` and does **not** pass `semantic_routing_basis` or `semantic_routing_confidence`. Its micro-tick path at `:5615-5626` also remains 3D.
- `agency/mechanics/sicd_engine.py:2709-2721,2903-2913` accepts and applies an 8D routing basis, so the low-level engine parameter exists.
- `agency/mechanics/sicd_msr_load_application.py:94-142,164-215` provides a separate canonical 17D-to-step plan/application and passes an 8D routing basis, but it uses `sicd_msr_routing_basis.project_load_signature_to_routing_basis` (`:15-17,109-110`), **not** the channel-separated loading-aware projection.
- Product commit currently uses an unrelated 3-byte SHA projection and 2D difference wind (`gateway/tom_gateway.py:537-545`). Product retrieval currently collapses the channel-separated projection back to its first three raw axes before calling the old selector (`gateway/structural_preview.py:29-49`).

The requested retrieval replacement has an exact upstream pure function. The requested commit replacement would require composing a shadow-only loading-aware projection with the separate canonical MSR step plan, or substituting it for that plan's distinct production routing basis. The pin contains no authoritative function or controller call defining that composition. Doing so product-side would invent the missing binding the instruction expressly forbids approximating.

Safest reversible default taken: finish WP-27 evidence; make no partial retrieval-only change that would leave serving and commit bases inconsistent; preserve preview purity, five-dynamics ordering, checkpoints, frozen artifacts and upstream checkouts; stop for owner/orchestrator direction. The governed next step is an upstream authoritative surface (for example, a tested canonical loading-aware MSR step-plan/application) or an explicit ruling that the product may promote and compose the shadow channel-separated basis despite its current claim boundary. A pilot rerun still requires preregistration v2 and fresh generation authorization.

No provider, broker, OAuth, gateway server, preview endpoint, `engine.step`, `ToMClient.process`, or `rgm.read_memory` was called by this audit. Port 18790 was not used. No upstream file, golden, preregistration or frozen pilot artifact was modified.
