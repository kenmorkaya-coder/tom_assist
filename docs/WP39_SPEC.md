# WP-39 — Project document ingestion, and the aggregation fix

**To:** Codex (implementing engineer)
**From:** Claude (orchestrator), for Ken Morkaya (owner)
**Date:** 3 September 2026
**Branch:** `codex/wp-39-document-ingestion`, from the accepted head of the WP-37/38 line (state which in the log)
**Scope:** documents become stored, chunked, embedded, retrievable-in-shadow material. They never drive the tree. Nothing this package adds changes what reaches a packet.

No G-gate verdict. No change to the non-zero rule, preview purity, or the five dynamics.

---

## 0. Two findings that shape this package

**There is no document ingestion today.** All forty-odd protocol methods cover projects, workstreams, conversations, turns, state objects, packets, snapshots and interventions. None accepts a document. Material enters only as a conversation turn or as a typed state object someone declares. The existing chunker (`gateway/semantic_chunks.py`) is sentence-aware token windowing, up to 192 tokens with 32 overlap, capped at 128 chunks and 48,000 source characters. Those caps were sized for a chat turn.

**The current aggregation rule does not survive document scale.** Each of the 17 channels takes the maximum value found in any chunk (`gateway/structural_analysis.py`, `per_channel_max_across_bounded_chunks`). Across a handful of chunks that correctly means "the strongest local evidence in this utterance." Across the thousands of chunks in a real document, every channel saturates, because somewhere in fifty pages there is a sentence that reads like a contradiction, one that reads like a rule, and one that reads like a deadline. The load stops discriminating. Smaller chunks make this worse, not better.

## 1. The decision this package rests on

**A turn is an event. A document is inventory.**

A turn is admitted, compiled into one 17-channel load, and applied once to the tree as force: wind, nourishment, driver exposure, the five dynamics. A document is not an event. Ingesting a specification must not hit the tree with one enormous load, and the deformation that followed would be meaningless.

Therefore documents are stored, chunked, embedded and made findable, and **no ingestion path applies a load, advances the tick, or touches tree or memory state.** This extends the load/address separation already recorded in WP-37: material may be addressable without being a force.

**This decision also dissolves the aggregation problem rather than patching it.** Aggregation exists because a turn must yield exactly one load to drive the tree once. A document drives nothing, so it needs no single load. Each chunk keeps its own signature and its own address. Retrieval finds chunks; the document is a container with provenance, not a unit of meaning.

## 2. Ground rules

- `tom_master` read-only at `e9fdef81c`. `tom_master17D` off-limits. `tom_sicd_gemma` frozen.
- Preview purity holds. Ingestion is never reachable from a preview path.
- The tree, RGM state, checkpoint digest, five-dynamics order and existing tables are untouched by ingestion.
- Existing turn behaviour is byte-identical. The frozen WP-31 to WP-36 calibrations all ran under the current turn aggregation; nothing here may change it (see §4).
- Product default stays `legacy`.
- Escalate as `ESCALATE WP39-n`; take the safest reversible default; continue non-dependent work.

## 3. Deliverable A — storage, chunking, embedding

Two new tables in `gateway/permanent_library.py`, following the existing immutability discipline (original content is durably retained first and never overwritten):

**`documents`** — `document_id`, `display_name`, `content_sha256`, `content` (the immutable original text), `byte_length`, `media_type`, `chunking_version`, `embedding_version`, `ingested_tick`, `tombstoned_at` (null unless withdrawn).

**`document_chunks`** — `document_id`, `chunk_index`, `start`, `end`, `text_sha256`, `passage_vector` (float32/base64, the same encoding the anchor bank uses), and a null `analysis_digest`/`load_signature_json` reserved for §6.

Chunking reuses `gateway/semantic_chunks.py` unchanged, with two document-scoped limits raised and made explicit rather than inherited: a document may exceed the 48,000-character turn cap and the 128-chunk turn cap, under new named constants with owner-visible values. Report the values you choose and why. Do not silently reuse the turn constants for documents, and do not change the turn constants.

Removal is a tombstone, never a delete, consistent with the demotion log. A tombstoned document is excluded from retrieval and retained for audit.

Extraction of text from binary formats (PDF, docx) is **out of scope**. This package accepts plain text and UTF-8 markup only. Anything else is refused with a clear reason.

## 4. Deliverable B — the aggregation fix

**Documents: no aggregation.** Each chunk carries its own signature and its own address. There is no document-level 17-channel load, and none may be synthesised.

**Turns: rule unchanged, saturation made visible.** The per-channel maximum stays exactly as it is, because every frozen calibration from WP-31 onward ran under it and changing it would invalidate them. Add to the existing analysis, inside the digest, a per-channel saturation observation: how many chunks were within a small epsilon of the winning value, the spread between the winning and median chunk values, and the chunk count. Record observations, not a verdict. Whether long turns need a different rule is a calibration question reserved for the owner, and this telemetry is what would answer it.

State plainly in the log that the turn aggregation is unchanged and that document scale is handled by not aggregating.

## 5. Deliverable C — protocol surface

Add `document.ingest`, `document.list`, `document.get` and `document.withdraw` to the core methods, with schema, hand-written Rust types, generated TypeScript and shared fixtures updated together. `npm run schema:validate` must pass. Capabilities gain a document-support declaration and the document chunking/embedding versions.

Ingestion is explicit and user-initiated. There is no watched folder, no automatic import, and no network fetch.

## 6. Deliverable D — shadow retrieval visibility only

Document chunks become **reported** retrieval candidates, ranked alongside anchors in the shadow comparison WP-37 introduces, and **never admitted to a packet** in this package. Report their ranks, scores and how often a document chunk would have displaced an anchor.

Document chunks participate in the dense semantic channel only. They have no structural signature and therefore no tree address, because producing one requires a parse of every chunk by the local structure worker, whose model pins remain behind an unpassed owner gate, and whose cost at document scale is unbudgeted. That is a deliberate boundary, not an oversight. Record it.

## 7. Explicitly deferred, with reasons

- **Structural parsing of document chunks**, and therefore the tree channel over documents. Blocked on the model-pin gate and on a parsing-cost budget.
- **Admitting document chunks to packets.** A chunk is up to 192 tokens against a default packet budget of 500. Admission policy needs its own decision.
- **Binary format extraction.**
- **Whether an ingested document should ever produce an event.** It does not here.

## 8. Tests (deterministic, fixture provider only)

1. **Ingestion is inert.** Ingesting a large document leaves engine bytes, RGM bytes, tick, checkpoint digest and structural-commit count identical.
2. **Original content is immutable.** Re-ingesting identical bytes is idempotent; ingesting different content under the same name creates a distinct document; the stored original is never rewritten.
3. **Chunk plan is exact and complete.** Chunks cover the source with the declared overlap; every chunk's offsets resolve to its recorded hash; a document larger than the turn caps chunks successfully under the document caps.
4. **No document load exists.** There is no code path producing a document-level 17-channel signature, proven by importer scan as well as by test.
5. **Turn behaviour byte-identical.** A turn analysis at this commit equals the same analysis at the parent commit, except for the new saturation observations, and frozen replay still passes.
6. **Saturation telemetry is honest.** A synthetic long turn where many chunks tie at the maximum reports a high tie count; a turn with one dominant chunk reports a low one.
7. **Tombstone.** A withdrawn document leaves retrieval candidates and is retained in the table.
8. **Shadow only.** Document chunks appear in the reported comparison and never in `activated_branch_ids` or packet text.
9. **Refusal.** A binary or non-UTF-8 payload is refused with a clear reason and stores nothing.
10. **Archive round trip** preserves both new tables; a pre-change archive still imports.
11. **Preview purity** and the frozen-artifact scan stay green.

Full regression required: Python `gateway/tests validation/tests`, `cargo test --workspace`, `cargo fmt --all -- --check`, `git diff --check`, `npm run extension:test`, `npm run desktop:test`, `npm run adapters:test`, `npm run schema:validate`.

## 9. Reporting

Append one `## WP-39` section to `BUILD_LOG.md` in the standing format: commit, evidence with counts, decisions with `file:line`, deviations, escalations, protection proof against the recorded baselines. Report the chosen document caps and the storage cost per thousand chunks. Remove the Rust `target/` directory after testing and report its size. Stop for owner audit.

## 10. Definition of done

1. Documents are stored immutably, chunked, embedded and withdrawable by tombstone.
2. No document produces a 17-channel load, advances the tick, or touches tree or memory state.
3. Turn aggregation is unchanged; per-channel saturation is observable inside the digest.
4. Protocol, schema, Rust, TypeScript and fixtures move together; schema validation green.
5. Document chunks are reported as shadow retrieval candidates and admitted to nothing.
6. Tests §8.1–8.11 green, full regression green, protection proof recorded, stopped for audit.
