# WP-40 — Project glossary for the structure parser (candidate, default off)

**To:** Codex (implementing engineer)
**From:** Claude (orchestrator), for Ken Morkaya (owner)
**Date:** 3 September 2026
**Branch:** `codex/wp-40-parser-glossary`, from the accepted WP-39 head (state it in the log)
**Scope:** give the local structure parser the project's own vocabulary through its prompt, without moving a single model weight. Flag-gated, default off, evaluated but not activated.

**This package runs the local Gemma model.** Every prior package in this line reported zero generations. This one will not. It needs an explicit generation budget, declared in the pre-registration and counted in the report. No cloud provider, no OAuth, no network.

---

## 0. Why this rather than fine-tuning

The parser is an extractor, not an answerer. It reads a sentence and returns typed facts bound to exact quoted spans. Training it on project documents would teach it what those documents say; its job is to recognise shape, and its measured weaknesses are extraction weaknesses (roughly a third of relations missed, multiple-relation sentences exactly right under half the time in the WP-34 frozen comparison). Documents do not fix those.

What documents *can* supply is vocabulary. A parser that has never seen your project's terms segments entities worse than one that has. That benefit is available through the prompt, which is a fixed template with a single interpolation slot (`build_gemma_prompt`, `gateway/structural_analysis.py:2055`). No weights move, determinism is preserved, the change is versioned and reversible.

**Replay is unaffected.** `validate_frozen_analysis` rebuilds from the stored chunk candidates and never re-runs the parser. The glossary therefore changes live parses only; every retained analysis continues to replay byte-for-byte.

## 1. Hard constraint: surface forms only

The glossary carries **terms and nothing else**. No kinds, no types, no relations, no hint about what a term is or how it behaves.

Typed state objects carry a declared `object_type` and `status`. The `object_type` **must never reach the prompt**. Telling the parser that a term is a constraint, an outcome or a decision is supplying structure, which is a prose-to-shape translator by another name, and Box 2 is held. The glossary tells the parser which strings are worth treating as one entity. It never tells it what they mean.

If Codex sees a way this constraint could be circumvented by ordering, grouping or naming within the prompt, raise `ESCALATE WP40-n` rather than proceeding.

## 2. Ground rules

- `tom_master` read-only at `e9fdef81c`. `tom_master17D` off-limits. `tom_sicd_gemma` frozen.
- Preview purity holds. The non-zero rule, the five dynamics and commit dynamics are untouched.
- No frozen calibration artifact, pre-registration, golden or seed artifact is modified.
- Product default stays `legacy`, and the glossary itself defaults **off** independently of the mode.
- No network request, no OAuth, no cloud provider, no port 18790.

## 3. Deliverable A — glossary construction (deterministic, no model)

Build a per-project glossary from two sources, in order:

1. **Declared typed state objects.** The `title` of every active, non-superseded object in the project. These are human-declared and are the highest-quality source available.
2. **Ingested document text**, only to top up when the first source is thin: repeated multi-word phrases above a frequency floor, selected deterministically. No model, no embedding, no clustering.

Bounding and determinism:

- A hard cap on term count and on total glossary characters, both as named constants with owner-visible values. Report the values you choose and the reasoning.
- Selection is by frequency, ties broken lexicographically, so the same project always yields the same glossary.
- Terms are normalised (whitespace, case-folding for comparison only) and deduplicated; the surface form emitted is the most frequent original spelling.
- The glossary has a canonical serialisation and a content hash.

## 4. Deliverable B — prompt integration and provenance

- The glossary is appended to the existing prompt as a plainly delimited term list, introduced by fixed wording that asks only that these strings be treated as single entities where they appear. Do not reword the existing prompt.
- `validate_parser_model` currently requires the exact field set `{version, model, revision}`. Add an **optional** `glossary_sha256`. Analyses without it must continue to validate unchanged; a glossary-enabled parse must carry it. Prove both shapes in test.
- Bump `PARSER_VERSION` for the glossary-enabled parser and keep the current version in the supported set, so existing retained analyses stay valid.
- Capabilities report whether the glossary is enabled, its version, its term count and its hash. Schema, Rust type, generated TypeScript and fixtures move together; `npm run schema:validate` passes.
- Gate on an environment flag, default off. With it off, the emitted prompt is byte-identical to today's.

## 5. Deliverable C — frozen paired evaluation

Freeze `validation/calibration/WP40_PREREGISTRATION.md` before any generation, declaring the corpus, the generation budget, the diagnostics and the interpretation rule.

**Corpus.** Domain text that has a declared vocabulary. The retained pilot stores hold planted typed state objects alongside their turn text and may be read **read-only and immutable**, exactly as WP-27 read them. Do not modify, re-run or reinterpret any frozen pilot artifact.

**Method.** The same corpus parsed twice, glossary off and glossary on, same seed, same worker, paired by source text. Every generation counted.

**Report these, all label-free:**

- how many parses changed at all, and the distribution of change size;
- entity count and mean entity span length, both runs;
- relation and signal counts, both runs;
- fail-closed rate and unknown-field rate, both runs;
- agreement between runs on the directed graph fingerprint;
- for changed parses, whether a glossary term is present in the source text.

**Do not report an accuracy improvement.** There is no domain-labelled ground truth in the repository, so correctness cannot be measured here. Say so plainly. A verdict requires a small owner-authored labelled set, which is a separate follow-on.

## 6. Deferred, with preconditions

**A frozen LoRA adapter** remains the right tool later, and is out of scope here. Its preconditions, so the package is already scoped when authorised: labelled parse pairs rather than documents; labels not sourced from the parser's own accepted outputs, since ambiguous cases already fail closed and would be systematically excluded, teaching it that its misses were correct; the WP-34 GPT parses as a first audited label source, given GPT measured better at signal recall; adoption only as a pinned version bump scored against the existing frozen corpora; and never any background updating, which would conflict with the model-pin gate and with owner Law 2.

Also deferred: any activation of the glossary by default, and any correctness verdict.

## 7. Tests (deterministic; model runs only in the evaluation, not the suite)

1. **Flag off is byte-identical.** The emitted prompt with the glossary disabled equals today's prompt exactly.
2. **Determinism.** The same project yields the same glossary, term list and hash across restarts.
3. **Surface forms only.** No object type, status, authority, confidence or relation ever appears in the emitted prompt, proven by scanning the rendered prompt for every enum value.
4. **Bounds hold.** A project with far more terms than the cap yields exactly the cap, chosen by the declared rule.
5. **Supersession respected.** A superseded state object's title is excluded.
6. **Backward compatibility.** An analysis with the three-field parser model validates; one with the glossary hash validates; a wrong hash fails.
7. **Replay untouched.** Retained analyses from the parent commit replay byte-for-byte with the glossary both on and off.
8. **No document contamination.** A tombstoned document contributes no terms.
9. **Preview purity** and the frozen-artifact scan stay green.

Full regression required: Python `gateway/tests validation/tests`, `cargo test --workspace`, `cargo fmt --all -- --check`, `git diff --check`, `npm run extension:test`, `npm run desktop:test`, `npm run adapters:test`, `npm run schema:validate`.

## 8. Reporting

Append one `## WP-40` section to `BUILD_LOG.md` in the standing format: commit, evidence with counts, decisions with `file:line`, deviations, escalations, protection proof against the recorded baselines. **Report the exact local Gemma generation count** and confirm zero cloud generations and zero OAuth use. Remove the Rust `target/` directory after testing and report its size. Stop for owner audit. No G-gate verdict.

## 9. Definition of done

1. A deterministic, bounded, hashed per-project glossary built from declared objects and, if needed, ingested documents.
2. Surface forms only, provably, with no type or relation information reaching the prompt.
3. Flag-gated and default off; prompt byte-identical when off; provenance recorded and backward compatible.
4. Frozen pre-registration before any generation; paired evaluation run; label-free diagnostics reported; no accuracy claim made.
5. Tests §7.1–7.9 green, full regression green, generation count reported, protection proof recorded, stopped for audit.
