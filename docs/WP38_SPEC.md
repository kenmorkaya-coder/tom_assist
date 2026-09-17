# WP-38 — Outcome memory: recording what retrieval produced and what the user did with it

**To:** Codex (implementing engineer)
**From:** Claude (orchestrator), for Ken Morkaya (owner)
**Date:** 3 September 2026
**Branch:** `codex/wp-38-outcome-memory`, from the accepted WP-37 head (or from `a91dbbb` if WP-37 has not landed; state which in the log)
**Scope:** capture only. Nothing in this package consults the new store, changes a ranking, or alters what reaches a packet.

No model generations. No G-gate verdict.

---

## 0. Why, and the finding that shaped this

Tom Assist has about seven memory stores. It has none for **outcomes**: what a retrieval decision produced, and what the person then did about it.

Two consequences today:

- **Nothing remembers a no.** `conflict_dismissed` is a per-commit boolean (`gateway/evidence_gateway.py:181,191,200`) whose only effect is deciding whether the response teaches the tree. It is never written anywhere retrieval can see. The same rejected material can be surfaced forever.
- **Nothing remembers what was used.** Every packet records what it admitted; every committed exchange records what came back. Nothing compares them.

**The back catalogue cannot supply this retroactively. I checked.** The WP-29 pilot matrix has authored relevance labels on all 165 queries, five to eight objects each. They are unusable for our purpose for three independent reasons: they label typed state objects, not memory anchors; WP-27 established that every per-project memory was empty and every stored retrieval trace had zero anchor candidates, so there was no anchor ranking to evaluate; and the observed citation failures were a rendering defect, with only three of 207 expected identifiers appearing in the state block at all, so the model could not cite what it could not see. Any relevance metric computed from that run would be measuring the renderer.

Therefore the signal has to be accumulated going forward. This package builds the capture so that a later, separately authorised package can use it.

## 1. Ground rules

- `tom_master` read-only at `e9fdef81c`. `tom_master17D` off-limits. `tom_sicd_gemma` frozen.
- Preview purity holds. Nothing here runs in a preview path.
- **The five-dynamics commit order, the tree, the RGM state and the checkpoint digest are untouched.** The checkpoint digest covers tree bytes and RGM bytes; this package writes neither.
- No existing table is altered. One new table only.
- Product default stays `legacy`. This capture runs in every mode, because it observes rather than decides.
- Escalate contradictions as `ESCALATE WP38-n`, pick the safest reversible default, continue non-dependent work.

## 2. Deliverable: one new table, written inside the existing commit transaction

Add `retrieval_outcomes` to `gateway/permanent_library.py`. One row per admitted anchor per commit:

| column | meaning |
|---|---|
| `commit_key` | the committing turn |
| `record_id` | the admitted anchor |
| `rank` | its position in the packet ranking |
| `rrf_score`, `lexical_rank`, `structural_rank`, `matched_branch_id` | the fusion fields already produced by `fuse_anchors` |
| `verbatim_overlap_chars` | longest exact substring shared between the anchor text and the committed exchange text |
| `structural_similarity` | the existing combined score (0.8 chunk-pair cosine + 0.2 directed-graph) between this turn's analysis and the anchor's retained analysis, or null if the anchor has no retained structural commit |
| `conflict_dismissed` | the commit's existing boolean |
| `tick` | engine tick at commit |

**Record observations, never verdicts.** Do not add a `was_useful` column, a threshold, a label or a score. Whether an overlap of a given length means "used" is a calibration question for a later package. Codex must not decide it here.

Constraints:

- The write happens inside the same transaction as the existing structural commit, so a crash cannot leave outcomes without their commit or the reverse.
- Commit is idempotent today; re-committing the same key must produce identical rows or raise the existing idempotency conflict, never duplicate.
- `verbatim_overlap_chars` is computed deterministically from the immutable stored texts. No model, no embedding, no fuzzy matching.
- Anchors admitted with no retained structural commit get a null similarity and are counted, never imputed.

## 3. Archive and recovery integration

`gateway/runtime_archive.py` validates and restores the library. Extend export, import and validation to carry `retrieval_outcomes`, and prove that an archive round trip preserves it byte-for-byte. An archive written before this package must still import, with the table simply empty. State explicitly in the log whether the archive format version changes and, if so, that both directions were tested.

## 4. Tests (deterministic, fixture provider only)

1. **Rows appear and match the packet.** After a commit with a non-empty packet, there is exactly one row per admitted anchor, ranks match the packet order, and the fusion fields equal what the preview returned.
2. **Empty packet.** A commit that admitted nothing writes no rows and does not fail.
3. **Idempotency.** Re-committing the same key leaves the row set byte-identical.
4. **Atomicity.** A forced failure after the outcome write and before commit completion leaves no orphan rows.
5. **Overlap is exact.** A committed exchange quoting an anchor verbatim records the true longest shared substring length; a paraphrase records the short incidental overlap, not a similarity guess.
6. **Dismissal is captured.** A commit with the conflict dismissed records that against every anchor in that packet.
7. **No-evidence anchors.** An anchor with no retained structural commit records a null similarity and is counted.
8. **Nothing else moves.** Tree bytes, RGM bytes, engine tick, checkpoint digest, the five-dynamics order, the existing tables and the packet itself are all identical to the pre-change behaviour on the same inputs.
9. **Archive round trip** preserves the rows; a pre-change archive still imports.
10. **Preview purity** and the frozen-artifact scan stay green.

Full regression required: Python `gateway/tests validation/tests`, `cargo test --workspace`, `cargo fmt --all -- --check`, `git diff --check`, `npm run extension:test`, `npm run desktop:test`, `npm run adapters:test`, `npm run schema:validate`.

## 5. Out of scope

- Using the store for anything. No ranking change, no down-weighting, no re-ranking, no threshold, no decay of dismissed material. That is a later package once real rows exist.
- Deciding what counts as "used". Explicitly reserved for the owner.
- Any change to the tree, commit dynamics, the write path for existing tables, or the checkpoint digest.
- Cross-project memory, recency in ranking, and the standing-preferences gap. All real, all separate.

## 6. Reporting

Append one `## WP-38` section to `BUILD_LOG.md` in the standing format: commit, evidence with counts, decisions with `file:line`, deviations, escalations, and the protection proof (tom_master HEAD plus status and working-diff SHA-256 against the recorded baselines). Remove the Rust `target/` directory after testing and report its size. Stop for owner audit. No G-gate verdict.

## 7. Definition of done

1. One new table, written transactionally with the existing structural commit, holding observations only.
2. Dismissals and admitted-anchor outcomes both captured, with exact overlap and existing structural similarity, and nulls where evidence is absent.
3. Archive export, import and validation carry it; old archives still import.
4. Nothing that reaches a packet changes; tree, checkpoint and existing tables provably identical.
5. Tests §4.1–4.10 green, full regression green, upstream protection proof recorded, stopped for audit.
