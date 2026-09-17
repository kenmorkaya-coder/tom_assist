# WP-37 — Evidence-addressed shadow retrieval (tree channel fed real coordinates)

**To:** Codex (implementing engineer)
**From:** Claude (orchestrator), for Ken Morkaya (owner)
**Date:** 3 September 2026
**Owner status:** ISSUED 3 September 2026. Scope is the mechanism plus label-free diagnostics only; the labelled evaluation is a separate follow-on (§4).
**Branch:** `codex/wp-37-shadow-dense-retrieval`, from accepted WP-36c commit `a91dbbb`
**Status of the non-zero rule:** UNCHANGED AND AUTHORITATIVE. This package does not touch it, weaken it, or route around it. See §1.

No model generations beyond the existing local MiniLM/Gemma structure worker. No production default changes. No G-gate verdict.

---

## 0. The finding this package acts on

Retrieval today fuses two channels by reciprocal rank (`gateway/structural_preview.py:59`):

| channel | weight | what it ranks by |
|---|---:|---|
| structural (tree) | 0.60 | each anchor's 8D `leaf_vec` resonance against the activated branch cohort |
| lexical | 0.40 | a 256-bucket hashed word-count cosine (`memory/rgm.py:681` at the pin) |

**The tree is already the primary retrieval mechanism.** It addresses territory by projecting a load signature to the 8D routing basis and taking the 16 best-aligned branches (`select_cohort`), then asks which anchors resonate with that territory (`rank_by_branch_resonance`).

Both of its inputs are currently derived from the upstream keyword-cue text projection, not from evidence:

- **Query side:** in `legacy` and `shadow`, the cohort signature is `base.project_text(user_text)`. Only `authoritative` uses the evidence-compiled signature (`gateway/evidence_gateway.py:100-107`).
- **Anchor side:** `record.leaf_vec = list(project_text(stored_text)[1].vector_8d)` at commit (`gateway/tom_gateway.py:539`).

So the tree performs the right operation on meaningless coordinates. Separately, the evidence-derived dense semantic ranking is computed on every shadow preview and then discarded for ranking purposes (`gateway/evidence_gateway.py:111-121`); it only affects the result in `authoritative`, which the non-zero rule blocks.

This package feeds the existing tree channel evidence-derived coordinates on both sides, and stops discarding the dense semantic channel — entirely in shadow, entirely read-only, and without applying any load to the tree.

## 1. The load/address separation (decision, must be recorded)

**A sparse 17-channel load may address territory. It may not drive the tree.**

The WP-35 rule exists to stop a hollow load being applied as *force* — wind, nourishment, driver exposure, kappa. Selecting a branch cohort and scoring anchor resonance apply no force: they are pure cosine reads that mutate nothing. Ken's Law 15 supports the distinction directly, and the pinned routing basis is documented as the load *address* space.

Therefore: authoritative commit keeps requiring 17 strictly positive channels; shadow retrieval may use the same compiled signature purely as an address. If Codex believes this reads as an end-run around WP-35, raise `ESCALATE WP37-n` rather than proceeding.

## 2. Ground rules (unchanged)

- `tom_master` read-only at `e9fdef81c`. `tom_master17D` off-limits. `tom_sicd_gemma` frozen.
- Do not modify `gateway/tom_gateway.py`, any frozen calibration artifact under `validation/runs/`, any pre-registration, golden, or the 10K seed artifact.
- **Preview purity is non-negotiable.** No preview path may call `rgm.read_memory`, `ToMClient.process` or `engine.step`. `gateway/tests/test_preview_purity.py` stays green.
- **No write-path change.** Stored `leaf_vec` values, the permanent library schema, commit dynamics and the five-dynamics order are untouched. Everything in §3 is computed at read time.
- Product default stays `legacy`. Nothing here changes what ships.

## 3. Deliverables

### 3.1 Evidence-addressed cohort (query side)

In `shadow` mode, select the branch cohort from the evidence-compiled `load_signature` via the same pinned `project_load_signature_to_routing_basis` path `authoritative` already uses, instead of `base.project_text(user_text)`. Retain the legacy-signature cohort as well; both are computed, both are reported (§4).

### 3.2 Evidence-addressed anchors (anchor side, read-only)

Do **not** change what is written at commit. At retrieval time, for each anchor that has a retained structural commit, read its stored frozen analysis from the permanent library (`structural_commits` already carries `load_signature` per `commit_key`/`record_id`), project that signature to 8D with the same pinned function, and use the result as the anchor's resonance vector for a second, shadow ranking.

Anchors with no retained structural commit keep their existing stored `leaf_vec` and must be counted and reported separately. Never synthesise a vector for an anchor that has no evidence.

### 3.3 Dense semantic channel (lexical side)

Stop discarding `rank_structural_history`. In shadow, produce a second lexical-channel ranking whose scores are the dense multi-vector score (0.8 chunk-pair cosine + 0.2 directed-graph similarity) instead of the hashed word count, and rank the two channels separately before fusion.

**Scale defect to fix in the same change:** the current `authoritative` merge replaces some scores with dense values and leaves others as hashed-bag cosines, then sorts the mixed list to produce the rank fed to reciprocal-rank fusion. Do not reproduce that. A record without a dense score must be ranked in a separate, explicitly reported tail, never interleaved by an incomparable scalar.

### 3.4 Side-by-side reporting, no switch

Every shadow preview returns both rankings under a new key, e.g. `shadow_retrieval_comparison`, containing: the current fused ranking, the proposed fused ranking, per-channel ranks for both, the cohort branch IDs for both signatures, counts of anchors with and without retained structural evidence, and rank-divergence statistics. The returned `activated_branch_ids` and packet remain exactly what they are today.

Nothing in this package changes which anchors reach a packet. It measures what would change.

## 4. Evaluation, and an honest warning about the corpus

**The WP-25/27 pilot corpus cannot measure this.** Its forensics recorded every per-project RGM empty, zero anchor candidates in every stored retrieval trace, typed state objects bypassing the branch/anchor ranker entirely, and focus retrieval already at 100%. There is no ranking headroom and no anchor inventory in it. Do not report an improvement against it.

**Codex does not author relevance labels.** Authoring them would make the instrument grade its own output. This package therefore delivers the mechanism and label-free evidence only, and stops. The labelled evaluation is a separate owner-authorised follow-on once labels exist.

Required in this package:

1. **A frozen pre-registration** (`validation/calibration/WP37_PREREGISTRATION.md`) committed before any run, declaring the corpus, the diagnostics, and the explicit statement that no relevance verdict is issued.
2. **Diagnostics that need no labels**, over a committed shadow conversation corpus: how often the two cohorts differ and by how many branches; how often the top-ranked anchor changes; the full rank-divergence distribution between current and proposed; how many anchors have and lack retained structural evidence; the hashed-bag collision rate (distinct anchors sharing a bucket profile); and the dense-versus-hash rank correlation.
3. **A reusable evaluation harness** that accepts an external relevance-label file and emits precision at k, mean reciprocal rank and per-query deltas, with **no labels supplied and no scores run**. Prove it with a tiny synthetic label file that is explicitly marked as a plumbing fixture, not evidence.

Report the diagnostics as observations. Do not call either ranking better.

## 5. Tests (deterministic, fixture provider only)

1. **Purity.** All four new paths are pure: 100 repeated previews leave engine bytes, RGM bytes, tree tick and structural-commit count identical. The preview-purity scan stays green.
2. **No write-path change.** Stored `leaf_vec` values and the library schema are byte-identical before and after a shadow preview; a commit still writes exactly what it wrote at `a91dbbb`.
3. **Non-zero rule intact.** An authoritative preview and an authoritative direct commit with a zero-bearing load still fail closed with the existing message, before `LoadSignature` and before the tree.
4. **Address-without-force.** A shadow preview built from a load containing zeros produces a cohort and a ranking, and applies nothing: engine bytes, tick and commit count unchanged.
5. **Evidence anchors.** An anchor with a retained structural commit is ranked on its stored signature; an anchor without one is ranked on its existing `leaf_vec` and appears in the reported no-evidence count. No vector is invented.
6. **No mixed-scale sort.** A fixture with some dense-scored and some unscored anchors proves the unscored ones form a reported tail rather than being interleaved.
7. **Determinism.** Both rankings are byte-identical across gateway restart and identical inputs.
8. **Default unchanged.** In `legacy`, behaviour and output are byte-identical to `a91dbbb`.

Full regression required: Python `gateway/tests validation/tests`, `cargo test --workspace`, `cargo fmt --all -- --check`, `git diff --check`, `npm run extension:test`, `npm run desktop:test`, `npm run adapters:test`, `npm run schema:validate`.

## 6. Out of scope

- Changing the shipping default, the fusion weight (0.60), the reciprocal-rank constant, or the cohort size (16). Report what they do; do not tune them.
- Any change to commit dynamics, the five-dynamics order, the write path, or stored state.
- Any dense-load or T/S/P work. WP-36c stands as audited.
- Member formation, Carillon, or 17D reading space. None of it exists at the pin.

## 7. Reporting

Append one `## WP-37` section to `BUILD_LOG.md` in the standing format: commit, evidence lines with counts, decisions with `file:line`, deviations, escalations, and the protection proof (tom_master HEAD plus status and working-diff SHA-256 against the recorded baselines). Remove the Rust `target/` build output after testing and report its size. Stop for owner audit. No G-gate verdict.

## 8. Definition of done

1. The tree channel is fed evidence-derived coordinates on both sides in shadow, read-only, with no write-path change.
2. The dense semantic channel is used for ranking in shadow instead of being discarded, without a mixed-scale sort.
3. Both rankings are reported side by side; nothing that reaches a packet changes.
4. The non-zero rule is provably intact and the load/address separation is recorded as a decision.
5. Pre-registration frozen before the run; label-free diagnostics reported; the label harness built but unused; no ranking called better and no improvement claimed against the pilot corpus.
6. Tests §5.1–5.8 green, full regression green, upstream protection proof recorded, stopped for audit.
