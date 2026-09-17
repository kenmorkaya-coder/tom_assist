# WP-44 — Operate the real app on real material and record what it retrieves

**To:** Codex (implementing engineer)
**From:** Claude (orchestrator), for Ken Morkaya (owner)
**Date:** 4 September 2026
**Branch:** `codex/wp-44-live-operation`, from the accepted WP-43 head, or from `d9df1a30` if WP-43 has not landed. State which.

The owner wants to see the product working on real material with real questions. Not fixtures, not a synthetic corpus, not a unit test. The actual app, an actual project, actual contract text, actual queries, and an honest record of what came back.

**No provider call is needed and none is authorised.** We are not measuring ChatGPT's answer. We are looking at what Tom Assist retrieves and assembles, which is the part that is ours. Zero OAuth, zero cloud, zero quota.

---

## 1. What to run

The real thing, as a user would meet it. Either the packaged desktop app or `scripts/dev-run.sh`, the same path WP-20 drove through its seven-stage journey. Say which you used and why.

Create a genuine project. Do not reuse the seeded demo project except as a control.

## 2. What to load

The WP-42 corpus, held at `/private/tmp/tom-assist-wp42-scaw-corpus-prep-a9dda3b6/`, in its corrected form `SCAW_SHORTLIST_TEXT_CORRECTED.json`: 41 passages of the SCAW deed, about 46,800 characters. That is comfortably inside the document limits WP-39 set.

Ingest through the real `document.ingest` route, as a user would. Not by writing to the database.

The passages stay out of the repository, per the owner's ruling. They live in the project's own store on the owner's machine, which is where document text belongs.

## 3. What to ask

Between fifteen and twenty questions a person working on this contract would actually ask. Write them before you run anything and commit them first, so the queries cannot drift toward what retrieval happens to be good at.

Cover the shapes the corpus contains, for example: what must happen before construction work starts; which document prevails when the specification and the planning approval conflict; what follows if substantial completion is missed; what the contractor must do when an artefact is found; who carries the risk of delay. Include two or three questions whose answer is genuinely not in the corpus, so refusal and empty retrieval are observable.

## 4. What to record

For every query, capture what the product actually produced:

- the packet as assembled, in full;
- which anchors and documents were admitted, in rank order, with their scores;
- what was excluded and why;
- the branch cohort the tree selected;
- the shadow comparison from WP-37, so the current and proposed rankings are visible on real queries rather than the eight synthetic ones it has seen so far;
- timings.

Run every query in `legacy`, which is what ships today, and in `shadow`. Report both. Do not switch the product default.

**And capture the app itself.** The owner asked to see it operating. Screenshots or accessibility dumps at each stage: the project created, the documents listed, a query prepared, the packet visible before sending. Enough that someone who was not there can see it happened.

## 4a. Every non-answer must say why

An empty or thin result is not a result until it explains itself. For any query
where little or nothing is retrieved, record the reason in the product's own
terms, not as a narrative afterwards: no anchor cleared admission, the budget
excluded it, the material was superseded, the passage was ineligible, the parse
failed closed and why. If the product cannot currently state a reason, that is
itself the finding and must be reported as a gap rather than filled in by hand.

**A known one to expect.** WP-39 deferred document packet admission, so an
ingested document cannot reach a packet at all today, in any mode. Queries
against the deed will therefore retrieve nothing from it in `legacy`, and the
passages will appear only in the `shadow` comparison marked ineligible. Report
that plainly as the current state. Do not treat it as a failure of retrieval,
and do not work around it by admitting documents.

## 5. What to conclude, and what not to

Report plainly, for each query, whether the material that should have been retrieved was retrieved. You may judge that, because you can read the passages and the question. Say when it failed and say when you are unsure.

**Do not compute an accuracy score.** There are no frozen relevance labels, and a number invented here would look like evidence when it is a reading. A per-query verdict with your reasoning is worth more and claims less.

**Do not tune anything.** If retrieval is poor, that is the finding. No weight, threshold, cohort size or fusion constant may be touched in this package.

## 6. Ground rules

- `tom_master` read-only at `e9fdef81c`; `tom_master17D` off-limits.
- Preview purity, the non-zero rule, the five dynamics and commit dynamics untouched.
- Product default stays `legacy`.
- No provider, OAuth, cloud or network generation. Local MiniLM and Gemma only, and only if `shadow` requires them; report the count.
- Contract passages are never committed. Queries, packets, rankings and screenshots are evidence and may be, provided the sensitivity rule from WP-42 is applied: report what committing them would disclose, and if the packets quote contract text, hold them outside the repository too and say where.

## 7. Reporting and done

Append one `## WP-44` section to `BUILD_LOG.md`: how the app was launched, project and document identities with hashes, the frozen query list and its hash, per-query outcomes for both modes, generation counts, and the protection proof. Remove the Rust `target/` directory and report its size.

Done when: the real app ran, the real corpus was ingested through the real route, fifteen to twenty pre-committed queries were put to it in both modes, everything returned was captured, the app was visually recorded, an honest per-query reading is given with no invented score and nothing tuned, and the package is stopped for owner audit. No G-gate verdict.
