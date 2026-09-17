# WP-43 — Document self-declared structure: reference resolution and defined-term binding

**To:** Codex (implementing engineer)
**From:** Claude (orchestrator), for Ken Morkaya (owner)
**Date:** 4 September 2026
**Branch:** `codex/wp-43-declared-structure`, from `d9df1a303221ffa021b450744bf1eaebc2bfd192`

**This is product mechanism, not a validation script.** It lives in `gateway/`, carries a version, has a schema, and is tested like anything else that ships. Nothing about it may be a throwaway helper under `validation/`.

No model generations. No G-gate verdict.

---

## 0. Why

A drafted instrument declares its own structure. The SCAW deed defines 531 terms explicitly, cross-references its own clauses thousands of times, and states its order of precedence in clause 1.5. That structure is authored, unambiguous and machine-checkable.

The consequence: for entities, dependencies and supersession, ground truth does not have to be transcribed by a person. It can be resolved from the document. Only causation genuinely needs judgement, and this package does not pretend otherwise.

This is not a testing convenience. Resolving a reference to the clause it names, and binding a name to the term the document defines, is what the product should do with any ingested document. Building it as mechanism is the point.

## 1. Ground rules

- `tom_master` read-only at `e9fdef81c`; `tom_master17D` off-limits; `tom_sicd_gemma` frozen.
- Preview purity holds. The WP-35 non-zero rule, the five dynamics and commit dynamics are untouched.
- Product default stays `legacy`. This package adds capability; it activates nothing.
- **Deterministic and fail-closed.** No fuzzy matching, no nearest-match, no confidence heuristic. A reference either resolves exactly or is recorded as unresolved.
- Escalate as `ESCALATE WP43-n` rather than inventing a resolution rule.

## 2. Deliverable A — a clause index for an ingested document

Derive, deterministically, the document's own structure: every numbered clause and sub-clause, every schedule and exhibit, every named section, with its identifier, its character span in the immutable stored text, and its parent.

The index is built once at ingestion, hashed, and stored beside the document. It is derived from the text and nothing else. Where numbering is ambiguous or malformed, record it as such rather than guessing.

## 3. Deliverable B — reference resolution

Detect explicit references in any passage: `clause 23.1`, `clause 12.1(f)`, `clause 16.13(j)(ii)(B)`, `Schedule A26`, `section 9.1 of the General Specification`, `Schedule D5`.

For each, record the reference as written, its exact span, the identifier it names, and whether that identifier exists in the clause index. Three outcomes only: resolved, unresolved because the target is absent, or unparsed because the form was not recognised. Never a guess.

**This yields checkable dependency ground truth.** A parser that asserts a dependency on clause 23.1 can be checked against whether clause 23.1 exists and whether the passage actually references it. A parser that invents a reference is detectable without anyone writing a label.

## 4. Deliverable C — defined-term binding

Extract the document's definitions deterministically, in the `Term means ...` form WP-42 already located, producing the term surface, its defining clause and its span. Surface forms only for any prompt use, per WP-40; the definition body stays in the index and never reaches a model prompt.

Then bind: for any span in a passage, report whether it exactly matches a defined term. Exact matching only, with a recorded case-folding rule. **This yields checkable entity ground truth.**

## 5. Deliverable D — declared precedence

Where a document states an order of precedence, extract the declared ordering as a directed relation between the named documents, with the span it came from. Clause 1.5 of the SCAW deed is the worked example. Where a clause opens with `notwithstanding` and names a target, record that target.

**This yields checkable supersession ground truth for the cases the document declares.** It does not attempt to infer supersession anywhere else, and must not.

## 6. What this deliberately does not do

- It does not label causation. Causation is not self-declared and this package makes no claim about it. Say so in the report.
- It does not score the parser. Scoring is a later package that consumes these three derived truths.
- It does not change what reaches a packet, drive the tree, or alter the load compiler.
- It does not replace owner labels where owner labels are genuinely needed. It removes the need for them in three families out of four.

## 7. Tests

1. The clause index over the WP-42 extraction is deterministic across two builds and hash-identical.
2. Every index entry's span resolves to text beginning with its own identifier.
3. A reference to a clause that exists resolves; a reference to a fabricated identifier is recorded unresolved, never silently dropped.
4. An unrecognised reference form is recorded unparsed rather than guessed at.
5. Defined-term binding is exact: a near-miss surface does not bind, and the case rule is asserted.
6. The declared precedence extractor reproduces clause 1.5's ordering, and produces nothing on a clause that declares no ordering.
7. No definition body can reach a prompt, proven by scanning the rendered prompt.
8. Preview purity and the frozen-artifact scan stay green.

Full regression as standing.

## 8. Reporting and done

Append one `## WP-43` section to `BUILD_LOG.md` in the standing format, reporting zero generations, the counts resolved, unresolved and unparsed over the SCAW deed, and the protection proof. Remove the Rust `target/` directory and report its size.

Done when: the clause index, reference resolver, defined-term binder and precedence extractor exist as versioned product mechanism with schema and tests; all three derived truths are produced over the SCAW deed with honest counts including failures; nothing is scored, activated or labelled by hand; stopped for owner audit.
