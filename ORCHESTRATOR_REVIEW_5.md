# ORCHESTRATOR REVIEW 5 — Governed tom_master changes: policy, WP-18 (upstream), WP-16 revision

**From:** Claude (build orchestrator)
**Date:** 31 August 2026
**Owner decisions:** (1) changes to tom_master are now allowed under the governed policy below; (2) fix `TOM_KAPPA_DECAY` upstream via env reader + corrected export; (3) WP-16's pure readout moves upstream as a tom_master module, gateway imports it.

## tom_master change policy (supersedes the blanket read-only rule)

This section supersedes `BUILD_INSTRUCTION.md` §0's "never write to tom_master" and the equivalent line in every earlier review. Changes are allowed, governed by class:

| Class | What | Governance |
|---|---|---|
| 1 — Additive surfaces | New files, new pure functions, optional flags defaulting to current behavior | Joint decision → branch commit → orchestrator audit → repin |
| 2 — Declaration hygiene | Making config/docs match actual behavior; zero effective change | Same as Class 1 |
| 3 — Physics changes | Engine equations, mechanical defaults, memory semantics | Same, PLUS: parity check, renewed effective-physics inspection, and the affected mechanism's claims shift from paper-anchored to product-gate-anchored |

Invariants that survive this policy: **tom_sicd_gemma is frozen forever** (reproducibility archive — changing it rewrites evidence). **tom_master17D is off-limits entirely** (owner directive, 31 Aug). Every change of any class goes through the standing rule: named to the owner, considered together, then executed as deliberate pinned commits.

## Working-tree safety protocol (non-negotiable for all upstream work)

tom_master's working tree contains the owner's uncommitted work (~53 modified files). Codex must protect it absolutely:

1. Do all upstream work in a **linked worktree**: `git -C tom_master worktree add <path-under-ToM_assist/.upstream-worktree> -b tom-assist/upstream-v1 8799ccbdd`. The owner's main checkout is never touched.
2. Stage files **only by explicit path** — `git add <file>` per file; `git add -A`, `-u`, or `.` are forbidden in the tom_master worktree.
3. Before starting, verify the files this WP touches are clean in the owner's main checkout (`git status -- <paths>`); if any target path is dirty with owner work, STOP and escalate.
4. Never stash, reset, checkout-over, or otherwise disturb the owner's uncommitted files. Never push anywhere.
5. When done, remove nothing: leave the worktree in place for orchestrator audit.

## WP-18 — Upstream: kappa reader/export fix + pure preview-readout module

On branch `tom-assist/upstream-v1` (from `8799ccbdd`, in the linked worktree), two commits:

**Commit 1 — `fix(kappa): add TOM_KAPPA_DECAY env reader and correct stale profile export`**
1. `agency/mechanics/sicd_kappa_update.py`: change `kappa_decay: float = 0.03` to an `_env_float("TOM_KAPPA_DECAY", 0.03)` field factory, exactly matching the neighboring `heal_rate`/`damage_rate` pattern. Default stays `0.03` — behavior changes nowhere that the variable is unset.
2. `config/profiles/msr_8d_native_10k.env`: correct `TOM_KAPPA_DECAY=0.053193359375` to `TOM_KAPPA_DECAY=0.03`, with a one-line comment: the old value was never read by any consumer; `0.03` is the production-swept value the 10k tree was actually grown and operated under.
3. Add/extend a test in tom_master's suite proving: unset env → `0.03`; env set → honored. Run the touched test files.

**Commit 2 — `feat(preview): add pure preview readout module for product previews`**
4. New module `agency/mechanics/preview_readout.py`: the read-only preview surface. Contents: `select_activated_branches_readonly(...)` — identical scoring to `leaf_vectors.py::select_activated_branches` (alignment gate × stiffness proxy × usage penalty, reading `usage_count` without writing it), returning the same shape; thin re-exports of `rank_by_branch_resonance` and the `msr_8d_loading_aware_readout` projection/ranking functions so products import one stable module. Docstring states the purity contract explicitly.
5. Tests in tom_master's suite: (a) readonly selection returns identical results to the mutating original on a fixed fixture tree (compare against a deep-copied tree run of the original), (b) purity — serialized engine state byte-identical across 100 readonly calls, (c) usage_count values influence the score identically in both paths.
6. No other files. Report both commit SHAs and stop for orchestrator audit. BUILD_LOG gets a WP-18 section (evidence includes the worktree path and `git status` of the owner's main checkout before/after, proving it untouched).

## Repin procedure (orchestrator-executed after WP-18 audit)

Audit: verify the two commits touch only the named files; run the new tests; confirm unset-env default preserves 0.03; confirm module purity; confirm owner's main checkout untouched. Then, with the owner: fast-forward the main tom_master checkout onto `tom-assist/upstream-v1` (target paths verified clean first), update the product pin from `8799ccbdd` to the new SHA (gateway startup check, docs, memory), and **retire the gateway's explicit kappa_decay override** — replaced by profile+reader with a creation-time assertion `kappa_decay == 0.03` kept as a tripwire.

## WP-16 revision (now WP-16b) and WP-17 — unchanged except the import

WP-16b: identical to Review 4's WP-16, except steps 1–3 **import `agency.mechanics.preview_readout`** from the pinned runtime instead of maintaining gateway mirrors. The mirror-drift coupling flagged in the revision register is retired. Fusion, manifest `activated_branch_ids`, policy bump to `context-policy/1.1`, numpy vectorization, extended purity test, latency guard, capabilities — all as written. WP-17 is unchanged. Both run on `build/commit-dynamics-v1` **after** the repin lands.

Sequencing: WP-18 → stop → orchestrator audit + joint repin → WP-16b → WP-17 → stop → orchestrator audit before merge.

## Standing constraints (restated)

tom_sicd_gemma frozen; 17D off-limits entirely; preview purity non-negotiable; no G-gate verdicts; Box 2 (translator) still held — no work authorized.
