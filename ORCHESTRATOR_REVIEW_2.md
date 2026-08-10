# ORCHESTRATOR REVIEW 2 — Project tree seeding decision + WP-14

**From:** Claude (build orchestrator)
**Date:** 10 August 2026
**Owner decision:** fresh Tom Assist projects start from the **bare 8D-native 10k-branch tree** (structure mature, memory empty), not from an empty root and not from the paper's 400-tick parity warmup.

## Rationale (recorded)

- `msr_8d_native_10k` is the runtime's **current production operating envelope** — the live backend's `active_profile`, with the legacy 50k profile explicitly blocked by the shadow preflight. The 400-tick warmup is the *engine-parity verification protocol* from the paper repo, not an operating tree; per-project trees built from it would be structurally immature relative to the runtime's proven envelope.
- It matches the owner's held decision (8D-native tree grown from the 17-channel vocabulary; legacy S/L/T snapshots intentionally excluded — documented in the profile header itself).
- A canonical artifact exists, is git-tracked at the pinned tom_master commit, and loads in one call — deterministic, fast, and better lineage than re-running growth per project.
- Engine-level paper parity is unaffected: parity was established for the physics, not for a particular tree instance.

## Canonical seed artifact (pinned)

| Property | Value |
|---|---|
| Path | `/Users/kenmorkaya/PycharmProjects/tom_master/sandbox/scaling/snapshots/msr_8d_native_10k_tiered.json` |
| Format | `TreeGrowthEngine.save()` JSON (verified: top-level keys match `sicd_engine.py:1392` save fields) |
| Branches / tick | 10,000 / 4707 |
| sha256 | `d9aec9b424459d0948f569c7e424bb5632bd118ad01bda372f62df7ca17a82ac` |
| Mechanics envelope | `config/profiles/msr_8d_native_10k.env` (kappa params the tree was grown under) |

## WP-14 — Seed fresh projects from the bare 10k tree (required)

1. **Load-at-creation:** in `gateway/tom_gateway.py::ProjectRuntime`, a project whose `tree_state.json` does not yet exist initializes via `TreeGrowthEngine.load(<seed artifact path>)` instead of `TreeGrowthEngine()`. Verify the artifact's sha256 against the pinned value above **before** loading; on mismatch, fail project creation closed with an explicit error (no silent fallback to an empty tree). RGM remains fresh and empty — the tree is bare of memories by design.
2. **Mechanics envelope:** committed-turn physics must run under the same kappa parameters the tree was grown with. Inspect how tom_master applies `config/profiles/msr_8d_native_10k.env` (env → `TreeGrowthConfig` path) and replicate that application for the per-project engine. Record the applied parameter set in `BUILD_LOG.md` with file:line evidence; do not guess values — read them from the profile file at gateway startup so a repin picks up profile changes deliberately.
3. **Lineage:** record `seed_profile="msr_8d_native_10k"`, the artifact sha256, and seed tick (4707) in the project's creation metadata and expose them through `/capabilities` (or a per-project info endpoint) and the initial checkpoint digest chain.
4. **Tests (gateway pytest):**
   - Creation determinism: two fresh projects yield byte-identical initial `tree_state.json` and identical initial checkpoint digests.
   - Digest-mismatch fails closed (corrupted copy fixture).
   - **Preview purity re-proven at 10k scale:** the existing 100-call purity test runs against a seeded 10k project (byte-identical engine+RGM state after mixed previews).
   - Commit sanity: one committed turn on a seeded project advances tick/state and produces a changed checkpoint digest.
   - Latency guard: `/preview/rank` on the 10k tree stays comfortably inside the preparation budget (assert a generous local bound, e.g. p95 < 500 ms over 20 calls, and record observed numbers — build verification, not a G14 verdict).
5. One commit: `feat(wp-14): seed projects from bare 8d-native 10k tree`. Append the WP-14 section to `BUILD_LOG.md` with evidence. Re-run the full gateway suite plus the Rust live-gateway and live-governance tests as regression evidence.

Sequencing: WP-13 (Review 1) and WP-14 are independent; either order is fine, both are required before merge to `main`.

## Standing constraints (unchanged)

tom_master stays read-only — the seed artifact is **read and verified in place**, never copied into tom_master or modified. Preview purity remains non-negotiable. No G-gate verdicts.
