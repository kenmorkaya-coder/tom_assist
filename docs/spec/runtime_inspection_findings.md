# tom_master Runtime Inspection Findings (binding for this build)

Date: 9 August 2026. Method: read-only code inspection of `tom_master` @ `8799ccbdd`.
These findings close the two WP-05 blockers in spec v1.2 (§9.3 preview semantics, §12.2 verifier semantics) and are **binding facts** for the adapter/gateway implementation. Do not re-derive them; verify file:line anchors still exist at the pinned commit and cite them in code comments where relied upon.

## Q1 — Preview / activation mutation semantics

**Mutating surfaces (must never be called in any preview path):**

| Surface | Location | Why it mutates |
|---|---|---|
| `TreeGrowthEngine.step()` | `agency/mechanics/sicd_engine.py:2709` | Full physics pass: σ/κ update, spawning, pruning. Strict monotonic-tick guard at `:2762` — the API contract assumes step advances time. No dry-run flag exists. |
| `ToMClient.process()` | `controller/external_api.py:2070` | Docstring: "All processing routes through ToMController.step()". No read-only mode. |
| `ReflectionGatedMemory.read_memory()` | `memory/rgm.py:1338` | Mutating **by design**: `current_tick += 1`, `_apply_decay`, `_reinforce` on every recalled anchor, `_prune`. Recall is plastic. |

**Read-only surfaces (the sanctioned preview path):**

| Surface | Location | Notes |
|---|---|---|
| `retrieve_ltm_with_stm_triggers()` | `interface/stm_ltm_retrieval.py:99` | The Layer-1 retrieval surface. Defaults `max_items=10, max_chars=2000` — exactly the paper's tested operating point. |
| `compute_retrieval_triggers()` | `interface/stm_ltm_retrieval.py:42` | Triggers from STM state, not engine stepping. |
| `_retrieve_relevant_memories()` | `interface/chat_adapter.py:1595` | Scores via `rgm.vector_store.query()` — bypasses `read_memory()`. Telemetry choke point 1. |
| `VectorStore.query()` | `memory/rgm.py:726` | **Pure function**: deterministic sha256-bucket encoding + cosine + sort. No state touched, no RNG. |
| Shadow-probe precedent | `integration/tomowner_msr_shadow_preflight.py` (served at `interface/desktop_api.py:1051`) | Existing shadow toolkit; docstring: exercises the bridge "without calling chat, LLMs, policy selection, action selection, or tree stepping". |

**Checkpoint/restore (native, complete):**

| Surface | Location | Notes |
|---|---|---|
| `TreeGrowthEngine.save(path)` | `agency/mechanics/sicd_engine.py:1392` | Serializes full per-branch state (κ, σ_ema, axis_w, sem_vec, geometry, niche, prune-pressure channels) — commented "for engine-snapshot fidelity". |
| `TreeGrowthEngine.load(path)` | `agency/mechanics/sicd_engine.py:1580` | Classmethod reconstruction. |
| `ReflectionGatedMemory.serialize()` | `memory/rgm.py:1608` | RGM state serialization. |
| `ToMClient.persist_now()` | `controller/external_api.py:1457` | Client-level persistence hook. |

**Binding design consequence:** `PREPARE_TURN` is **read-only by construction** — it ranks against the tree state as of the last committed turn; the user draft contributes only as `user_text` semantic evidence (this is spec P2 verbatim). The draft's load is applied exactly once, at commit, via one `process()`/`step()` pass — where RGM reinforcement is semantically correct. Previews, cancels, edits, and stale-version rebuilds cause zero substrate deformation. G16's five-arm "identical histories" requirement is satisfied by restoring each arm from the same saved checkpoint.

**TomCapabilities must report:** `supports_readonly_ranking=true`, `supports_checkpoint_restore=true`, `supports_nonmutating_load_preview=false` (the feature is honestly absent; do not emulate it by step-and-ignore).

## Q2 — Verifier surfaces and relation coverage

| Verifier | Location | What it computes |
|---|---|---|
| `adjudicate_reasoning_structure(proposal, expected)` | `agency/reasoning/structure_repair_loop.py:173` | Deterministic gate against `ExpectedReasoningStructure` (`expected_operator`, `required_dependencies`, `required_constraints`, `required_evidence`, `forbidden_evidence`, `forbidden_moves`, `stakes`, `failure_action="block_final_answer"`). Typed rejection codes (`invented_evidence`, `operator_mismatch`, `final_answer_before_structure_acceptance`, …). Consumed by the schema-first loop in `agency/reasoning/structure_first_answering.py` (LLM proposes structure → ToM adjudicates → prose only after acceptance; bounded repair). |
| `DriftVerifier.verify_llm_output()` | `metrics/drift_verifier.py:116` | `DriftDecision`: `permit\|revise\|defer\|block` + six residual channels (`R_uncited`, `R_contradiction`, `R_policy`, `R_confidence`, `R_goal_substitution`, `R_envelope`) + reason codes + evidence refs. Contradiction = regex `contradict_patterns` on **declared `Invariant` objects** (`default_invariants()` at `:38` ships one). |
| `verify_claim` / `verify_claims` | `metrics/claim_verifier.py:266/:383` | Deterministic BM25-style claim→chunk verification over a `GroundingIndex`: `SUPPORTED/WEAK/UNSUPPORTED` + chunk citations + bounded drift residual. Non-authoritative by contract; feature flag default OFF. `extract_claims_from_text` at `:470` (regex-level). |
| `compute_integrity_score` | `integrity/answer_verifier.py` | Pure integrity scoring (provenance, claim-verified, tool-required, evidence-missing) → energy delta into nourishment. |

**Relation coverage vs spec G16 classes:** `supports` — covered (claim_verifier). `depends_on`, `contradicts` — validated **when declared** (required_dependencies / invariant patterns); never derived from prose. `supersedes`/`reopens` — data flags only (`requires_new_evidence_before_reopen` in semantic-geometry tables). `defines/refines` — absent.

**Binding design consequence:** §12.2 interventions are computed by **rendering the Tom Assist ledger into these verifiers' declared inputs**: constraints → invariant `contradict_patterns` + `required_constraints`; rejected paths → `forbidden_moves`/`forbidden_evidence`; unresolved dependencies → `required_dependencies`; evidence → claim corpus. Gate mapping: `block/revise/permit` ≈ `CONFLICT/REVIEW/PASS`. Prose→structure extraction remains unvalidated (spec P12/RISK-1: shadow, candidate-only). G16's relationship-fidelity oracle comes from the ledger's explicit edges, never from runtime inference.
