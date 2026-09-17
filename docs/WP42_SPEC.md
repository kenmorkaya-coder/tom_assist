# WP-42 — Corpus preparation from the owner-supplied SCAW deed

**To:** Codex (implementing engineer)
**From:** Claude (orchestrator), for Ken Morkaya (owner)
**Date:** 4 September 2026
**Branch:** `codex/wp-42-scaw-corpus-prep`, from `a616e504c6034b93d354903511f3183ef43f541a`

**THIS PACKAGE RUNS NO MODEL.** Zero local Gemma generations, zero cloud, zero OAuth. It prepares a corpus. It does not evaluate anything.

**AND IT COMMITS NO CONTRACT TEXT** until the owner has ruled on §4.

---

## 1. The corpus is chosen. You are not choosing it.

The owner has selected:

```
/Volumes/My Passport for Mac/tom_as projects/sydney_metro_wsa/SCAW Contract/
  SCAW D_C Deed - Executed 1 March 2022.pdf
```

Verified: 343 pages, about 21 MB, PDF 1.6, with a real text layer rather than scanned images. `pdftotext -layout` returns clean text. Parties are Sydney Metro and CPB Contractors, contract WSA-300-SCAW.

Your job is extraction, provenance and a passage shortlist. The owner ratifies the passages and writes the labels.

## 2. Extraction is validation-only

WP-39 deliberately deferred binary format extraction, and this package does not reverse that. **Do not add PDF handling to the gateway, the product, or any shipping path.** The extractor lives under `validation/` as a one-off utility.

Requirements:

- Deterministic. The same PDF yields byte-identical text. Record the tool and its version.
- **Self-contained freeze.** The source lives on a removable drive that will not always be mounted. Record the source PDF's SHA-256, then copy the extracted passages into the frozen corpus so nothing later depends on that volume being present.
- Provenance per passage: page number, clause or section identifier where determinable, character offsets into the extracted text, and the text's own hash.
- Read the PDF read-only. Never write to that volume.

## 3. Use the deed's own definitions as the glossary

This corpus has a property the earlier candidates lacked: it carries its own vocabulary. Pages roughly 20 to 60 hold a definitions clause in `Term means ...` form, with several hundred entries.

That is a human-authored, exhaustive, unambiguous project vocabulary, and it is a far better glossary source than frequency-counted phrases. Extract those defined terms deterministically as a candidate glossary alongside the passages.

**The surface-only rule from WP-40 still binds.** Extract the defined term itself. Never the definition body, never a type or category, never anything that tells the parser what a term means. If a term's own name embeds a classification, that is the owner's problem to rule on, not yours to interpret.

## 4. Sensitivity: report, then stop

This is a real executed commercial contract between a government agency and a named contractor. Whether its text may be committed into this repository is the owner's decision and yours to surface, not to make.

Produce a written sensitivity report covering: how many characters of contract text the shortlist would commit, which parties and commercial terms appear in it, whether the passages contain pricing, personal names or anything else the owner would not want permanently recorded, and the fact that this repository has no licence file.

Then **stop before committing any contract text.** Commit the extractor, the shortlist manifest with hashes, page references and family tags, and the sensitivity report. Hold the passage text itself outside the repository until the owner rules. State plainly where you held it.

## 5. Passage shortlist, with a spread that makes failure interpretable

Propose about forty candidate passages, each a paragraph or two. Tag each with which of the four statement families it carries: causation, dependency, rule or constraint, supersession. All four must be well represented.

**Deliberately include a difficulty spread, and label it.** A deed is dense legal drafting: deeply nested sub-clauses, cross-references such as "under clause 23.1", and long enumerated lists that the parser's bounded windows will cut through. Include plain narrative passages such as recitals, background and scope descriptions alongside the hard nested clause text.

The reason is not tidiness. If everything fails again, a spread lets the owner tell whether the parser is broken or whether legal register is simply outside what it was built for. Without it, a second null result would be as uninformative as the first.

Recommend nothing about which passages to keep. Present them tagged and let the owner cut.

## 6. Out of scope

- Authoring any label. Still the owner's, per WP-41.
- Running any model.
- Adding PDF support to the product.
- Freezing the v2 pre-registration. It stays a draft until the owner fills in the corpus fields.
- Optical character recognition. Not needed; the text layer is real.

## 7. Tests

1. Extraction is deterministic across two runs on the same source.
2. Every shortlisted passage's recorded offsets and hash resolve exactly against the extracted text.
3. The defined-term extractor returns surface forms only, proven by scanning its output for definition bodies.
4. The frozen corpus manifest is self-contained: no path in it depends on the removable volume.
5. A missing or unmounted source fails closed with a clear message rather than producing a partial corpus.
6. Existing regression stays green.

## 8. Reporting and done

Append one `## WP-42` section to `BUILD_LOG.md` in the standing format, reporting zero generations explicitly, the source PDF hash, the shortlist size and family coverage, and the protection proof. Remove the Rust `target/` directory and report its size.

Done when: extraction is deterministic and self-contained, the defined-term glossary candidate exists as surface forms only, about forty passages are shortlisted and tagged by family and difficulty, the sensitivity report is written, no contract text is committed, no model ran, and the package is stopped for owner audit. No G-gate verdict.
