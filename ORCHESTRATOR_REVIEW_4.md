# ORCHESTRATOR REVIEW 4 — Box 1 architecture resolution: WP-16 (photograph) + WP-17 (experience)

**From:** Claude (build orchestrator)
**Date:** 31 August 2026
**Status:** Owner-decided architecture. Resolves the first UNSOLVED box in `one_turn.md` ("asking it = loading it"). The second box (prose→shape translation) remains held — no work authorized on it.

## The decided architecture, in one paragraph

**Drafts photograph; commits experience; the library never forgets.** Preview reads the tree's current bend as pure geometry — it never pushes, teaches, rotates, or strengthens anything. Every *sent* turn makes the tree experience the exchange exactly once, through all five dynamics: it bends (physics step), files (RGM write), **learns** what its branches mean from the response (A), **rotates** the branches that served the packet (B), and **re-seats its front row** — strengthening the anchors the packet actually used while unused ones fade toward demotion (C). Demotion returns a record to the permanent library; nothing is ever deleted. Validation batteries restore from checkpoints; production accumulates only through commits.

Owner decisions recorded: **A** — yes, the tree learns (commit-gated). **B** — yes, rotation at commit only. **C** — yes, strengthen/fade as front-row seating with demote-never-delete; **front-row capacity default raised to 4096 records per project** (owner: "a few thousand"), per-project configurable.

---

## WP-16 — The photograph: structural preview probe

Today's preview is lexical + triggers + ledger. This WP adds the branch-conditioned structural channel as **pure geometry**, recovering real Layer-1 semantics without touching the tree.

1. **Load projection (pure mirror):** project the draft into its load signature by mirroring the runtime's projection *computation* — never its application. Pure sources at the pin: `agency/mechanics/msr_8d_loading_aware_readout.py` (`project_load_signature_to_channel_separated_basis`, `loading_aware_8d_score`, `rank_loading_aware_8d` — zero mutation sites, audit-verified) and `agency/mechanics/sicd_msr_load.py`. Cite file:line in the mirror.
2. **Cohort selection (pure mirror of a mutating function):** `leaf_vectors.py::select_activated_branches` MUTATES (`usage_count += 1`) — **never call it in preview**. Reimplement its scoring in the gateway as a read-only mirror: alignment gate × stiffness proxy (`r^4·κ/ell`) × usage penalty, with `usage_count` **read but never written**. Top-K=16 default. Cite the mirrored lines.
3. **Anchor resonance:** score front-row anchors with `rank_by_branch_resonance` semantics (max cosine of anchor `leaf_vec` vs activated branches' `sem_vec`) — pure given the cohort.
4. **Fusion:** RRF-fuse the structural channel with the existing lexical channel, `w_leaf=0.6` as the calibration prior. Bump `policy_version` to `context-policy/1.1`; keep all decomposed scores in the candidate trace.
5. **Manifest addition:** the packet manifest / `context_runs` record persists `activated_branch_ids` alongside the existing admitted IDs — WP-17's commit crediting consumes exactly this.
6. **Performance:** vectorize the 10k-branch scan with numpy (already in `.venv-gateway`). Latency guard stays: p95 well inside budget over 20 calls, numbers recorded.
7. **Purity:** extend the 100-call preview-purity test to exercise the structural channel heavily; byte-identical engine+RGM state remains the hard requirement. Update golden-packet fixtures for the new policy version (byte-stable under the new scoring).
8. **Capabilities:** add `preview_channels=["lexical","structural_geometry"]`.

Commit: `feat(wp-16): add pure structural preview probe`.

## WP-17 — The experience: full commit dynamics + two-shelf memory

Commit currently does two of the runtime's dynamics (step + RGM write). This WP completes the set and installs the two-shelf rule.

1. **A — Teach (`apply_leaf_vec_update`):** at commit of an exchange, feed the provider's committed response through `apply_leaf_vec_update` (`agency/mechanics/sicd_engine.py:4869`), mirroring how the live controller invokes it (`controller/tom_controller.py:6381`). Inspect the expected `llm_output` dict shape at the pin and construct it faithfully; record the shape mapping in BUILD_LOG with file:line. Policy flag `teach_on_conflict` (default `true`): when `false`, exchanges whose evaluation was CONFLICT-dismissed do not teach.
2. **B — Rotate:** at commit, `usage_count += 1` on exactly the branches recorded in the sent packet's `activated_branch_ids` (from WP-16's manifest). Never during preview; never for unsent packets.
3. **C — Re-seat the front row:**
   - Reinforce the anchors listed in the sent packet's admitted IDs (mirror `ReflectionGatedMemory._reinforce` semantics via the public surface at the pin).
   - Then run one maintenance pass at commit — decay all, prune to capacity — mirroring the maintenance `read_memory` performs at read time (`memory/rgm.py:1338-1386`), relocated to commit so the fade dynamic exists without read-time impurity.
   - **Demote-never-delete:** before any record leaves the front row, verify its durable twin exists in the SQLite store (content-hash lookup) — the library-first invariant guarantees it; assert it anyway and fail loudly if violated. Log every demotion as an auditable event (record id, content hash, reason: decayed|capacity) surfaced in desktop diagnostics. Demoted records are readmitted on their next committed use.
   - **Capacity:** construct the per-project RGM with `capacity=4096` (owner default), exposed as a per-project setting; document that the two-shelf rule is what makes larger front rows safe.
4. **Library-first invariant (hard):** nothing enters the RGM front row without its permanent SQLite copy existing first. Turn ingest already satisfies this; add the assertion at the RGM-write seam.
5. **Ordering:** the five dynamics run in one commit transaction in this order: step → RGM write → teach (A) → rotate (B) → re-seat (C: reinforce, decay, prune). Idempotency: the existing `idempotency_key` dedup must cover the full quintuple — a replayed commit applies nothing twice.
6. **Capabilities:** add `commit_dynamics=["step","rgm_write","leaf_vec_teach","usage_rotation","front_row_reseat"]`, `front_row_capacity`, `teach_on_conflict`.
7. **Tests (gateway pytest + one Rust envelope test):**
   - Preview touches nothing: structural previews change zero bytes (WP-16's extended purity test covers this).
   - Commit changes exactly once: sem_vec EMA, usage counts (only serving branches), anchor strengths (only admitted anchors) move on commit; idempotent replay moves nothing.
   - `teach_on_conflict=false` respected for CONFLICT-dismissed exchanges.
   - Overflow at capacity 4096 demotes lowest-strength records with logged events and verified SQLite twins; readmission on next committed use works.
   - Checkpoint round-trip: save → commits → restore → byte-identical to pre-commit state (battery discipline intact).
8. **BUILD_LOG:** append WP-16 and WP-17 sections with evidence; no G-gate verdicts.

Commit: `feat(wp-17): full commit dynamics and two-shelf memory`.

Branch: `build/commit-dynamics-v1` off `main`; both WPs on it; stop after WP-17 and report for orchestrator audit before merge.

## Standing constraints (unchanged)

tom_master, tom_master17D, tom_sicd_gemma strictly read-only; all mirrors cite pinned file:line; preview purity is non-negotiable and now covers the structural channel; no G-gate verdicts; Box 2 (translator) remains held — do not implement anything for it.
