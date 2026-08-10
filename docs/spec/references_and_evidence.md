# References, Evidence Anchors and Claim Boundaries

## Repositories (all READ-ONLY for this build)

| Repo | Path | Role | Pin |
|---|---|---|---|
| tom_master | `/Users/kenmorkaya/PycharmProjects/tom_master` | The ToM runtime this product binds to. Public remote: github.com/kenmorkaya-coder/Tree_of_Mind | commit `8799ccbdd` |
| tom_sicd_gemma | `/Users/kenmorkaya/PycharmProjects/tom_sicd_gemma` | [R1] experiment repo: generator, runner, coupling code, result JSONs, experiment contract | branch `feat/rgm-memory-bridge` |
| tom_master17D | `/Users/kenmorkaya/PycharmProjects/tom_master17D` | Ken's research fork. **OFF-LIMITS: never import from, reference, or modify.** | — |

## Primary evidence [R1]

"Eliminating Context Rot in Frozen LLMs: A Three-Mode Structural State-Coupling Architecture", 23 April 2026.
PDF: `/Users/kenmorkaya/Desktop/sicd_three_mode_arxiv.pdf`

Key facts this build relies on:
- Layer 1 (branch-conditioned retrieval) rescued forced context removal: BASE 1/40 (2.5%) → 40/40 (100%), paired Δ +0.975, CI [+0.925, +1.000] (Run 10.7).
- Pooled 64K results: BASE 17/20, L1-prose 17/20, L2 19/20, L1+L2-prose 16/20 (negative composition), L1-state 19/20, FULL 20/20 (Wilson CI [0.84, 1.00]).
- Prose preludes are **unreliable** (invite enumeration loops); authoritative-state format with precedence + anti-enumeration instruction is **reliable** (5/5 on every batch).
- Layer 1 tested operating point: top-K=16 activated branches, top-k=10 anchors, 2000-char budget, w_leaf=0.6 in RRF. These are calibration priors, not frozen production constants (spec §11.3).
- Layer 2 (MoE expert bias) requires router access — **not available** through closed subscription providers. Subscription Companion Mode = Layer 1 + state block only, and must never be described as the paper's FULL condition.
- The paper's evaluator is tom_master's `scripts/verify_plant_recall.py` (SHA `8c977554`), invoked out-of-process: JSON batch `{case_id, plant_key, plant_value, question, answer_text}` on stdin → `VERIFIED`/`NOT_FOUND` per case on stdout, word-boundary case-insensitive match. **This is the oracle pattern for the validation harness.**
- Engine lineage: `tom_sicd_gemma/tests/test_engine_parity.py` holds the experiment engine in parity with `tom_master.agency.mechanics.sicd_engine` (±1% on σ/κ/branch-count over the canonical 400-tick warmup; bit-exact at fixture time). All three papers predate tom_master's fork point with 17D; tom_master's only post-fork commits touch `interface/tom_as_assurance_gateway.py`.

## Integration precedent

`tom_master/interface/tom_as_assurance_gateway.py` — the ToM Assurance Suite binds to tom_master as a separate product through one thin localhost gateway file and `create_client("tom_as")` (`controller/external_api.py:2722`), with tom_master otherwise read-only from the product side. Tom Assist's gateway copies this pattern **but lives in this repo** (imports tom_master via PYTHONPATH; adds zero files to tom_master).

## Claim boundaries (binding on all UI copy, docs, logs)

Per spec §2.4: paper-proven claims stay attributed to the paper's tested configuration (frozen Gemma 4 26B, Variant F benchmark). Tom Assist may NOT claim: context-rot elimination, FULL-condition equivalence, or concept/goal continuity as proven. Everything product-level is "must be proven by Tom Assist" until the G-gates pass. No G-gate may be reported as passed by this build — the build ships the instruments, not the verdicts.
