# ORCHESTRATOR REVIEW 8 — Owner freeze of WP-23 batteries; WP-25 pilot authorization

**Date:** 1 September 2026
**Owner decisions (recorded verbatim from review):**

1. **Margins frozen as drafted** in `validation/batteries/wp23-draft/PREREGISTRATION.md` (wp23-prereg-draft/1 → to be versioned frozen by WP-25). H1 primary: SUB-D ≥ +0.15 macro-averaged exact action consistency over each of SUB-A and SUB-B, paired 95% CIs excluding zero, and ≥ 0.80 in every focus family. Secondaries (H2 components) as drafted. Post-freeze, no key/threshold/seed/comparator/exclusion change in response to results — corrections require a new pre-registration version before a new run.
2. **Pilot scale authorized: 33 cases × 5 arms = 165 logical generations** off the owner's OAuth quota. Deterministic pre-specified selection: per family, the first two long cases and the first no-rot control by lexicographic `test_id`. Pairing preserved (same cases across all five arms); arm order rotates per the pre-registration. The remaining 99 cases stay frozen for a later full pass under the same plan.
3. **No-rot "gratuitous injection" defined: floor-only allowed.** The non-evictable floor (active objective, hard constraints, active guardrails) is legitimate on no-rot cases; *gratuitous* = any optional anchors/background beyond the floor. Telemetry measures optional-content injection; the H2.1 expectation is zero gratuitous, floor permitted.

Orchestrator review completed before freeze: pre-registration read in full (faithful to the owner's paper discipline — H1/H0/H2/H3, cluster bootstrap seed 1729, no silent discards, stop rules); case/answer structure sampled; contract checker re-run (132 cases, 11×12, 6 slices × 22, provider_calls=0, no verdicts).

## WP-25 — Production battery runner, freeze mechanics, authorized pilot run

Codex latitude on mechanics; requirements:

1. **Freeze mechanics:** version the pre-registration per its own rules (draft → frozen v1 with the three owner decisions above and the freeze SHA recorded), set `owner_frozen:true`, record the pilot selection rule and the frozen case list. Answer keys and margins byte-unchanged.
2. **Production runner:** execute arms through the real product path (native state import per case, real PREPARE/EVALUATE pipeline, packet + injection telemetry implementing the floor-only rule), not the fixture renderers. Pins recorded per the pre-registration's required-artifacts list. Runtime may be started by the runner under the standing owner authorization (persisted OAuth, no interaction); stopped after.
3. **Run the authorized pilot:** 165 generations, one initial capture per case/arm, no retries/best-of/repair, unknown outcomes never auto-resent; stop rules from the pre-registration are binding. WP-22 self-report stays off.
4. **Report:** full Appendix-C-style report — raw paired matrix, per family/slice/domain/arm numerators and denominators, failure taxonomy, injection telemetry, H1/H0/H2/H3 outcome stated exactly as the frozen criteria resolve, nulls and partials reported without rescue framing. **A pilot outcome is a pilot outcome — no G-gate verdict may be issued or implied.** Evidence in BUILD_LOG; stop for orchestrator audit with the raw matrix.

Standing constraints unchanged (upstream repos, purity, quota respect, honest labels).
