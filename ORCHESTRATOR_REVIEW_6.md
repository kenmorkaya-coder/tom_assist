# ORCHESTRATOR REVIEW 6 — WP-18 accepted; WP-19 repin, WP-16b conversion, WP-17

**From:** Claude (build orchestrator)
**Date:** 31 August 2026
**WP-18 audit verdict:** ACCEPTED. Both commits touch exactly the specified files; the reader preserves the 0.03 default; the module's purity contract and pinned-line citations check out; 57/57 upstream tests passed under the orchestrator's own run; the owner's main checkout was verified untouched throughout. The pre-existing missing-`requests` controller test failure is an environment gap unrelated to WP-18.

## PRECONDITION (owner-only action — Codex must NOT perform it)

The owner switches the main tom_master checkout onto the audited branch:

```
git -C /Users/kenmorkaya/PycharmProjects/tom_master checkout tom-assist/upstream-v1
```

Codex verifies before any work: `git -C /Users/kenmorkaya/PycharmProjects/tom_master rev-parse HEAD` == `e9fdef81c8a366ebbec07be9772189eea15cb2ac`. **If it does not match, STOP and report — do not switch the owner's checkout yourself under any circumstances** (working-tree safety protocol, Review 5).

## WP-19 — Product-side repin (pin, kappa retirement, provenance)

1. `gateway/tom_gateway.py`:
   - `PINNED_SHA` (line ~30): `"8799ccbdd"` → `"e9fdef81c"`.
   - Kappa block in the config builder (~lines 245–266): the profile is now authoritative — the upstream reader exists and the export is corrected. Replace the explicit binding with `config.kappa_update.kappa_decay = float(parameters["TOM_KAPPA_DECAY"])`, followed by a **fail-closed tripwire**: if the resulting value differs from `EFFECTIVE_KAPPA_DECAY` (0.03) by more than 1e-12, raise and refuse project creation. Replace the four-point comment with a short WP-18/WP-19 note: profile+reader authoritative as of `e9fdef81c`; 0.03 is the audited effective growth/operating value (Review 3); any future divergence must be a deliberate reviewed decision, which is what the tripwire enforces.
   - `KAPPA_DECAY_SOURCE` → `"profile_env_reader_wp18_effective_0.03"`.
2. `crates/tom-adapter/tests/live_gateway.rs` (~line 73): update the hardcoded provenance string to the new value.
3. `docs/spec/references_and_evidence.md`: tom_master pin cell → `commit e9fdef81c (WP-18 repin, 31 Aug 2026)`.
4. `BUILD_LOG.md`: commit the currently-uncommitted WP-18 section as-is, and append a WP-19 section.
5. Evidence run (all must be green against the repinned runtime): gateway pytest (11), `cargo test -p tom-assist-tom-adapter --test live_gateway`, `cargo test --workspace`, `npm run extension:test`. The seeded-project kappa assertion (== 0.03) must pass unchanged — the value is identical; only its source changed.
6. Commit: `chore(wp-19): repin runtime to e9fdef81c and retire kappa override`.

## WP-16b — Convert gateway mirrors to upstream imports

1. `gateway/structural_preview.py`: replace the mirrored selector/scoring implementations with imports from `agency.mechanics.preview_readout` (`select_activated_branches_readonly` and the re-exported projection/resonance functions). The module remains as the product-side adapter (fusion glue, RRF, trigger integration stay here); the duplicated upstream scoring logic is deleted.
2. Behavior must be identical: all existing structural-preview, purity (100-call byte-identity), golden-packet, and latency tests pass **unchanged** — same outputs, same digests, `context-policy/1.1` unchanged. If any output differs, STOP and report the divergence rather than adjusting a golden.
3. Commit: `refactor(wp-16b): import upstream preview_readout, retire gateway mirrors`.

## WP-17 — The experience (unchanged from Review 4)

Execute exactly as specified in `ORCHESTRATOR_REVIEW_4.md` WP-17: five commit dynamics in order (step → RGM write → teach A → rotate B → re-seat C), two-shelf rule with library-first assertion, capacity 4096, `teach_on_conflict` flag, demotion events, idempotent quintuple, full test set. Note for step A: `apply_leaf_vec_update` is unchanged between the old and new pin; cite the new-pin line numbers in BUILD_LOG.

Commit: `feat(wp-17): full commit dynamics and two-shelf memory`.

## Sequencing and boundaries

Precondition check → WP-19 → WP-16b → WP-17 → **STOP for orchestrator audit before any merge**. All work on `build/commit-dynamics-v1`. The linked worktree at `.upstream-worktree/tom-master-wp18` stays retained. No pushes anywhere; no further tom_master changes (the upstream branch is frozen at `e9fdef81c` pending this cycle); tom_sicd_gemma frozen; 17D off-limits entirely; no G-gate verdicts; Box 2 still held.
