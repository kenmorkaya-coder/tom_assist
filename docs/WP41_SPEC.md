# WP-41 — Failure taxonomy, prose corpus assembly, and a redrafted glossary pre-registration

**To:** Codex (implementing engineer)
**From:** Claude (orchestrator), for Ken Morkaya (owner)
**Date:** 3 September 2026
**Branch:** `codex/wp-41-glossary-rerun-prep`, from `bf703e03fe0d017e74d21afd0c0a4a555c6c2887`

**THIS PACKAGE RUNS NO MODEL.** Local Gemma generations must be exactly zero. The rerun happens only under a separate, later, explicit owner authorisation. Stop before any generation.

WP-40's implementation stands accepted. Only its evaluation is void, because the corpus it used was the pilot's own machine instruction blocks rather than project prose. That corpus choice came from the orchestrator's spec, not from Codex.

---

## 1. Deliverable A — a closed failure taxonomy

The WP-40 runner recorded `str(error).split(":", 1)[0][:120]`, which collapsed all seventeen failures to the bare word `RuntimeError`. The run proved that parses failed and cannot say why. Replace it.

- **Derive the taxonomy from the code, not from guesswork.** Enumerate every raise site in the parse and validation chain: worker startup and transport, model invocation, tool-call extraction, JSON decoding, `validate_candidate`, span canonicalisation and exactness, endpoint resolution, kind/modality/polarity vocabularies, confidence bounds, chunk-plan agreement, and budget ceilings. Assign each a stable, short category code.
- **The set is closed.** Include an explicit `unclassified` bucket. A clean run must leave it empty, and any non-empty `unclassified` count is reported prominently rather than absorbed.
- **Record per failure:** the category code, a bounded detail string (cap it, state the cap), the chunk index, and the attempt ordinal. Never the raw exception text unbounded, and never a truncation that loses the cause.
- **Failures are data.** Do not retry, do not fall back, do not soften any existing fail-closed behaviour.

## 2. Deliverable B — attempt every chunk

WP-40 stopped a passage at its first failing chunk, so only the first failure per passage was ever observed. For diagnosis, attempt every chunk in the passage, record each chunk's outcome independently, then mark the passage failed if any chunk failed. Passage-level semantics are unchanged; only the observation is completed. Account for the higher generation count in the budget you propose.

## 3. Deliverable C — corpus candidates, proposed not chosen

**Codex does not choose the corpus.** That is what went wrong last time.

Produce a short candidate list of real project prose available locally, and for each candidate report: where it comes from, roughly how much prose it holds, whether it contains genuine causal, dependency, constraint and supersession statements, whether a project vocabulary can be derived for it, and its licensing or sensitivity status. Include at least one candidate drawn from this repository's own written material and at least one that would require the owner to supply text.

Recommend one, state why, and stop. The owner picks.

## 4. Deliverable D — label template, no labels

Build the label file format and its validator: per passage, the typed facts a competent reader would expect, bound to exact quoted spans, in the same shape `validate_candidate` already accepts, plus a free-text note field for the labeller.

**Codex authors no labels.** Ship the template, the validator, and a two-row synthetic example explicitly marked as plumbing and not evidence. The WP-37 harness already sets this precedent; follow it.

## 5. Deliverable E — draft pre-registration, unfrozen

Draft `validation/calibration/WP40_PREREGISTRATION_V2.md` covering: the chosen corpus left as an explicit blank for the owner, the labelled metrics, the label-free diagnostics carried over from v1, the new failure-category reporting, the generation budget implied by attempting every chunk, and the interpretation rule.

Mark it **DRAFT — NOT FROZEN — NOT AUTHORISED FOR GENERATION**. Freezing happens after the owner picks the corpus and supplies labels.

## 6. Ground rules

- `tom_master` read-only at `e9fdef81c`; `tom_master17D` off-limits; `tom_sicd_gemma` frozen.
- Zero local Gemma generations, zero cloud calls, zero OAuth.
- Do not modify WP-40's retained evidence, its frozen pre-registration, or any earlier frozen artifact. The v1 run stays exactly as recorded, including its void evaluation.
- No product behaviour change. Preview purity, the non-zero rule, the five dynamics and the default `legacy` mode are untouched.
- Escalate as `ESCALATE WP41-n` rather than making a corpus or labelling judgement yourself.

## 7. Tests

1. Every enumerated raise site maps to a distinct category, proven by a table-driven test that triggers each one.
2. `unclassified` stays empty across the whole taxonomy test.
3. A multi-chunk passage with one bad chunk records outcomes for all chunks and one passage-level failure.
4. The label validator accepts a well-formed file, rejects a span that does not match the source exactly, and rejects an unknown relation kind.
5. Detail strings respect their cap and never carry unbounded exception text.
6. Existing regression stays green.

Full regression required, as standing.

## 8. Reporting and done

Append one `## WP-41` section to `BUILD_LOG.md` in the standing format, **reporting zero generations explicitly**, with the protection proof against the recorded baselines. Remove the Rust `target/` directory and report its size.

Done when: the taxonomy is closed and tested, every chunk is observed, corpus candidates are proposed with a recommendation, the label template and validator exist with no labels authored, the v2 pre-registration is drafted and clearly unfrozen, no model ran, and the package is stopped for owner audit. No G-gate verdict.
