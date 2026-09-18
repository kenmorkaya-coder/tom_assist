# One Turn Through Tom Assist

The current capability reference is maintained separately in
[tom_assist_capability.md](tom_assist_capability.md). This file remains the
chronological evidence and decision record.

## Current end-to-end flow — 18 September 2026

The current document-answer path has two complementary retrieval lanes. RGM
(Reflection-Gated Memory) keeps and finds exact text. ToM recognises a reviewed
relationship or event order and can reopen every exact RGM source bound to that
learned structure. The two lanes meet at evidence checking.

```text
                              USER QUESTION
                                    |
                  +-----------------+-----------------+
                  |                                   |
                  v                                   v
          RGM SEMANTIC ACCESS                 QUERY STRUCTURE CHECK
       likely exact text passages        ordered event, or candidate-bound
                                             party relationship?
                  |                                   |
                  |                          no ------+------ yes
                  |                                   |
                  |                    +--------------+--------------+
                  |                    |                             |
                  |                    v                             v
                  |          REVIEWED OPPOSITE FOUND       LEARNED RELATION FOUND
                  |          exact reverse/opposed state    distributed ToM recall
                  |          zero tree or model calls       complete branch identity
                  |                    |                    + signed 32x32 fields
                  |                    |                    + exact slot maps
                  |                    |                    never one whole-tree score
                  |                    +--------------+--------------+
                  |                                   |
                  |                                   v
                  |                        BOUND RGM SOURCE IDs
                  |                                   |
                  +-----------------+-----------------+
                                    |
                                    v
                         EXACT RGM SOURCE PASSAGES
                         text + provenance + offsets
                                    |
                                    v
                         SOURCE CONFLICT CHECK
                  +-----------------+-----------------+
                  | no                                | yes
                  |                                   v
                  |                     SHOW EVERY EXACT SOURCE
                  |                     return ambiguous while no
                  |                     effective decision exists
                  |                                   |
                  |                                   v
                  |                     EXPLICIT USER AUTHORITY
                  |             exact relationship/event/source claim
                  |                  controlling + replaced passages
                  |                    effective time + reason
                  |                                   |
                  |                                   v
                  |                     READ-ONLY AUTHORITY HISTORY
                  |                     exact passages + provenance
                  |                     scope + time + reason
                  |                     active or future-dated
                  |                                   |
                  +-----------------+-----------------+
                                    |
                                    v
                            EVIDENCE CHECKER
             supported / partly supported / not supported / ambiguous
                                    |
                                    v
                            LANGUAGE MODEL
                  words only the evidence-approved result
                                    |
                                    v
                       ANSWER WITH SOURCE REFERENCES
```

Reviewed structural memory enters the system through a separate, explicit
path. Detection does not teach the tree. A person must inspect and save each
source.

```text
                       AUTHENTICATED RGM PASSAGES
                                    |
                  +-----------------+-----------------+
                  |                                   |
                  v                                   v
        RGM SEMANTIC QUERY SWEEPS            FULL-SOURCE REGEX SCAN
          contextual vector pass              every active RGM chunk
          native RGM vector pass
          Reciprocal Rank Fusion
                  |                                   |
                  +-----------------+-----------------+
                                    |
                                    v
                    STRICT LOCAL EVENT-ORDER CHECK
                 semantic hits cannot bypass this check
                 zero tree calls; zero automatic learning
                                    |
                                    v
                         STRUCTURES TO REVIEW
                                    |
                            explicit Save only
                                    |
                                    v
                    SOURCE-LOCAL VALIDATION REPEATED
                                    |
                  +-----------------+-----------------+
                  |                                   |
                  v                                   v
          NEW REVIEWED STRUCTURE              EXISTING STRUCTURE
       teach distributed ToM memory       bind another exact RGM source
                  |                            zero new tree writes
                  +-----------------+-----------------+
                                    |
                                    v
                    REVIEWED STRUCTURE + SOURCE LINKS
```

The normal conversation path remains governed separately:

```text
draft held in Tom Assist
  -> read project record and experience tree without changing them
  -> build a visible, bounded context packet
  -> user allows send
  -> capture the provider's answer
  -> check it against the exact packet and project constraints
  -> user accepts, rejects or edits
  -> accepted experience may be committed to the experience tree
```

## Earlier Gemma inspection integration — 15 September 2026

This section distinguishes the existing application from the opt-in inspection
harness implemented on `codex/gemma-lora-typed-event-graph`. It supersedes the older “only sent turns” description below: sending
and capturing a response do not themselves authorize experience learning.
`crates/assistd/src/experience.rs` requires a recorded, explicit response
acceptance and resolution of applicable findings before experience commit.
The older diagram remains historical context, not an instruction to bypass this.

### Larger-document check — M12 Interface Agreement, 15 September 2026

The owner selected the executed M12 Interface Agreement on Passport instead of
the previously proposed repository build specification. The original PDF was
read unchanged: 129 pages, 2,564,200 bytes, approximately 41,731 extracted words.
PDF SHA-256: `29383bf63b32d42edebbfafd85adca9e2ce7be9a1b38ad49a0d28f4d859077ba`.
Read-only `pdftotext -layout` extraction produced 354,736 Unicode characters;
UTF-8 text SHA-256: `8e5fe1b6c3e84d559b0679edec397654d2f1e185fd0dc5a1c07bb255ad7f74e4`.
The existing ingest endpoint accepts text, so this was a full extracted-text
ingestion attempt, not a demonstration of native binary-PDF import or graphics
understanding. Temporary data was kept outside the repository.

Three questions were fixed before ingestion, with expected evidence located
in the source PDF. Page numbers below are physical PDF pages:

1. After the peer review design documents are made available, how long does
   the Peer Reviewer have to issue a report or reject them, and who receives
   the report? Expected evidence: clause 10.3, page 36, including its deadline,
   report recipients and rejection alternative.
2. Can a party enter a SAS Interface Zone without notice during an emergency?
   Expected evidence: clause 4.2(b), page 23, including the emergency condition.
3. Can Sydney Metro begin major piling if the Peer Reviewer has neither issued
   a report nor rejected the design documents? What conditions and risk
   allocation apply? Expected evidence: clauses 10.4(a)–(c) and the referenced
   clause 10.3 period, page 36, including both the main rule and exception.

**Result: ingestion failed before embeddings, retrieval or trained Gemma ran.**
One request was sent through the real local `assistd` `document.ingest` method
to the existing gateway, using an empty project created in the native inspection
app. The response was `VALIDATION_FAILED`, wrapping gateway HTTP 400:
`DeclaredStructureError: duplicate exact defined-term surfaces: Peer Review`.
Gateway elapsed time was 0.863 seconds; the service round trip was 0.875 seconds.
No automatic retries or source-text alterations were made.

Diagnosis: `gateway/declared_structure.py::_definition_candidates` rejects a
repeated exact surface across the entire extracted document. It detects one
definition in the main deed on page 14 (source offset 45087) and another in
Schedule 4, Peer Reviewer's Deed Poll, on page 97 (offset 294000). The latter
explicitly refers back to the Interface Deed. Both are under separately located
clause 1.1 headings. The duplicate guard does not distinguish those instrument
scopes; the downstream term binder also searches the whole document. Simply
removing the duplicate guard would therefore leave ambiguous bindings.

A tiny in-memory synthetic diagnostic changed one variable: a main definition
alone passed, its referring attachment alone passed, and combining the two
failed with the same duplicate-surface error. Relevant PDF pages were visually
checked. The isolated project retained zero documents, zero document chunks,
zero structural commits and zero document chunk commits. Project-runtime
initialization did create its standard seed storage before validation; this
was not successful document ingestion. There were zero provider sends and
zero Gemma inspections. None of the three retrieval questions was executed,
so there is no retrieval or generated-answer result to report.

The next implementation step is to represent instrument scopes and explicit
definition references without silently choosing, merging or dropping a
definition, then rerun this unchanged document and these fixed questions.
This check changed no product code, adapter or Stream 1 state. Only this compact
record is retained; the owned test processes and temporary project/render data
were cleaned up after inspection.

### Definition fix and unchanged-document retry — 15 September 2026

The owner authorized the proposed fix and retry. `gateway/declared_structure.py`
now records definition scope IDs and exact source ranges, using explicit deed /
agreement openings and authored schedule / attachment headings as boundaries.
Definitions with the same exact surface in different scopes are retained
separately; occurrences bind only within the recorded scope. Duplicate surfaces
within one scope still fail. A numbering reset alone does not create a scope,
and a new attachment cannot inherit the preceding definitions heading.
References to another instrument remain verbatim in the definition body;
the importer does not infer equivalence, inherit definitions or resolve an
instrument alias by guessing. Unrecognised instrument boundaries remain a
limitation. This is bounded source parsing, not a complete legal-scope resolver.

New structures and term bindings use version 1.1. Existing version 1.0
structures remain readable, including through archive validation. The shared
schema and generated types were updated. Validation reconstructs scoped
definitions and bindings from the original source and rejects a binding moved
to another instrument. All edits used existing architectural files and the
existing `gateway/tests/test_declared_structure.py` test file.

Verification: 17 declared-structure checks passed; one optional external held
corpus check was unavailable and skipped. The document archive round-trip check
passed. Shared protocol validation passed (12 fixtures, 48 methods); desktop
frontend build and whitespace checks passed. The full agreement's retained
structure exactly matches the final code's reconstruction: 135 definitions,
2,230 bindings and structure digest
`sha256:ae0ef8709d6271906859bafe6cf11fddfde25668bcea83a011c0558ca6a9d562`.
The two Peer Review definitions have distinct scopes and retain their original
source offsets. Clause-address parsing was not changed in this fix; repeated
clause numbers in attachments can still be marked ambiguous/malformed.

**Full-text import succeeded.** One real `document.ingest` service request
completed in 55.95 seconds (55.69 seconds in the gateway), using the unchanged
PDF/extraction hashes above. The native app's Memory view showed one active
document and 501 chunks. Read-only checks verified exact retained text,
every chunk's source hash, overlapping coverage from character 0 through
354736, and 501 committed document-Tree receipts. Embedding used the existing
local MiniLM snapshot `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.

The three previously fixed questions were then entered into the actual native
Chat view and each Preview packet action ran once. No provider send was made.
All three gateway previews returned HTTP 200 and preserved the project runtime
snapshot. Normal prepared-packet records were written to the isolated app
ledger; that expected write is separate from Tree mutation or experience
learning. Results, using zero-based chunk IDs and physical PDF pages:

| Question | Expected source | Native ranks of overlapping chunks | Visible packet result |
| --- | --- | --- | --- |
| Peer-review deadline and recipients | Clause 10.3, p36; chars 110163–110789; chunks 213, 214 | 360, 112 | Empty. Three unrelated candidates were excluded by packet budget. |
| Emergency access without notice | Clause 4.2(b), p23; chars 69459–69959; chunks 158, 159 | 71, 220 | Empty. Three candidates omitted the expected emergency-access exception and were excluded by packet budget. |
| Starting piling without report/rejection | Clause 10.4, p36; chars 110789–111714; chunks 214, 215 | 116, 353 | One unrelated licence housekeeping excerpt, chunk 398, p89. Three other candidates were excluded by packet budget. |

**Relevant-evidence result: 0/3.** This is a retrieval assessment, not a generated
answer score. The source passages were retained, but all six question/chunk
matches were marked `UNEXAMINED_TREE_NATIVE_PAGE_LIMIT`: ordinary queries only
allow the first 64 Tree-ranked chunks into subsequent semantic ranking. The
correct clauses were therefore removed before semantic ranking or packet
admission could recover them. The ordinary service request also uses a
500-token packet budget, including framing/provenance; its trace explicitly
records the additional budget exclusions. Raising that budget alone would not
recover the missing correct clauses. No thresholds, candidate limits, queries,
retrieval code or packet budgets were changed for these checks.

The next step is to diagnose and correct ordinary-question candidate selection
first, then recheck the same questions before changing packet sizing. The
experimental trained-Gemma/Stream 1 path remains separate and was not invoked;
there were zero Gemma inspections, provider sends or experience commits.
Owned local test processes and temporary app data were removed after recording
this compact evidence. The Passport original remains unchanged; no contract
prose or large diagnostic export was added to the repository.

### Passage selection and packet sizing retry — 15 September 2026

The owner authorized correcting passage selection and repeating the same three
questions. The unchanged extracted text was imported once into a fresh isolated
project, `e3995d91-f76c-4097-bccf-32a2935484b7`, in 43.38 seconds. All 501 chunk
hashes and complete overlapping source coverage were verified. That same source,
index and project were reused across both changes; no re-ingestion was used to
improve retrieval. The document Tree retained 501 receipts, 10,067 branches,
tick 4739 and digest
`sha256:3770a8af45d5ed0dcb1781938ef1f36f644e40cc861a291f36a97664fdc0420c`.

**Selection diagnosis and fix.** A read-only comparison used existing stored
MiniLM vectors after the pinned native reader had validated and ranked all
project receipts. The two required chunks for each question had semantic ranks
1/5, 1/2 and 1/2 respectively, despite native ranks 360/112, 71/220 and 116/353.
Native score spreads were about 0.00204, 0.00205 and 0.00203; a non-flat response
is not evidence that those ranks measure question relevance.

Ordinary queries now choose the existing 64-chunk text-analysis allowance using
those stored semantic scores. Native branch, score, rank and receipt provenance
remain mandatory and visible. The existing semantic/text ranker determines
ordinary passage priority; the former 60% native-rank contribution is no longer
applied to ordinary questions. This changes product selection policy, not the
pinned Tree mathematics, routing basis, address compiler or embeddings. Broad
document research retains its prior native paging/fusion behavior. The trace
distinguishes metadata comparisons from source-text analysis: 501 stored vectors
compared, 64 source chunks examined, 437 not examined. Packet admission version
is 1.7 and document research trace version is 1.6.

Three real native-app previews after this change retrieved the relevant clauses,
but all three final packets were empty: the separate 500-token service budget
excluded every excerpt once framing and provenance were counted.

**Packet sizing fix, then a second three-preview check.** Eligible ordinary
document evidence now requests the existing Standard ceiling of 1,200 tokens.
Non-document previews retain 500; broad research retains 9,000. No ceiling,
source-excerpt character allowance or candidate count was increased. The app
and service were rebuilt before repeating the identical questions in the native
Chat view, using Preview packet only.

| Question | Evidence visible in final packet | Result against fixed expectations |
| --- | --- | --- |
| Deadline and recipients | Chunks 211, 213, 214; all 626 source characters of clause 10.3 covered; deadline, recipients and rejection alternative present | Complete evidence for this question |
| Emergency access | Chunks 158, 159, 260; all 500 expected characters around clause 4.2(b) covered; emergency requiring presence and no-notice exception present | Complete evidence for this question; an unrelated contamination excerpt also remains |
| Piling without report/rejection | Chunks 214, 215, 450; all 925 source characters of clause 10.4 covered, including scope, reasonable steps and own-risk exception | Partial: the packet cites clause 10.3's period but omits its actual 10-business-day deadline |

These packets contained 3,583 / 3,579 / 3,583 characters, estimated by the app at
896 / 895 / 896 tokens, with no final budget exclusions. Every selected excerpt
was checked against its exact retained source range and the rendered packet.
All three main clauses are now retrieved, but **only two of three fixed evidence
checks are complete**. This is not a generated-answer score. The third preview
has zero reference traversals: ordinary queries bypass the existing expansion
path, which is restricted to recognized pre-start duty queries. The unchanged
third question is classified as an ordinary query. The next step is bounded,
scope-aware retrieval of explicit referenced clauses for ordinary questions,
including clause 10.3 here, before assessing generated answers. Do not substitute
a wording change or a hard-coded deadline for that missing evidence.

Validation: seven focused gateway checks passed, covering selection outside the
old native page, deterministic ordering, no text analysis outside the 64-chunk
selection, native provenance, exact references, prerequisite ranking and project
isolation/purity. A new check in the existing service conversation test file
passed through the real local gateway: retained source and provenance fit under
1,200, an empty document preview remains at 500, and preparation neither sends
to a provider nor changes project state. The native app/service build passed.

All six measured gateway previews returned HTTP 200 and preserved runtime
snapshots. Only three additional prepared exchanges and their packet/manifest
records were created in each phase. The isolated project remained at state
version 0, with zero state objects, conversation turns, experience acceptances
or runtime commits. There were zero provider sends and zero Gemma inspections.
This remains MiniLM/document-Tree retrieval, not the LoRA-trained Gemma path.
Original PDF and extracted-text hashes still match the recorded values above.
Only this compact evidence is retained; owned test processes and temporary
project data are cleaned up after the check. No contract prose or full trace was
added to the repository. No new source/test files, commit or push were made.

### Owner correction and actual trained-Gemma passage checks — 15 September 2026

The owner rejected testing MiniLM instead of trained Gemma and presenting detail
only in this file. Results must be shown directly in the conversation, including
the input, actual model output, expected meaning, failures and what path ran.
The earlier document retrieval results are not trained-Gemma results. Prior
training history does not excuse failing to use the trained model in those tests.

Three fresh sequential extractions now used the retained V14 adapter at 4,380
cumulative steps, through the existing `GemmaInspection.inspect` gateway class
with `extraction_mode=gemma`. The worker verified all ten model-file hashes and
the adapter weights/configuration before loading with `adapter_path`. Adapter
SHA-256 remains `c6a4708d9ceca6dab5d275ea0bff5ac172e392d085a4fda6b0d875e51d95a994`.
There was no training, saved-output replay, MiniLM retrieval or Tree query in
these three checks. The question was the assessment target, not an
answer-generation prompt. Inputs were exact PDF-extracted source passages,
supplied directly to the detached inspector as drafts. This isolates extraction;
it is not a native-app or full-document integration test.

| Assessment | Exact extracted-text input | Actual trained-model output and failures |
| --- | --- | --- |
| Deadline and recipients | Clause 10.3, physical p36; chars 110163–110789 (626 chars) | Produced value `10`, unit `Business Days`, comparator `LE`; actor `Peer Reviewer`; recipient span `SM and TfNSW`; actions `issue`, `reject`, `procure`. Validation stopped at `unsupported unit`; all three action names are also outside the current format. The graph does not encode the report-or-reject choice or when the period starts; the issue event's object is the design documents, not the report. |
| Emergency access | Clause 4.2(b), physical p23; chars 69459–69681 (222 chars) | Produced one `access` event, modality `permission`, with `condition:null`, `exception:null`, and no predicates or links. The emergency requirement and no-notice qualification were omitted. Validation stopped at `unsupported action, modality or negation` because `access` is unsupported. |
| Piling and linked deadline | Clauses 10.3–10.4, physical p36; chars 110163–111714 (1,551 chars) | Produced actions `issue`, `reject`, `procure`, `ensure`, `use`. The permission to use documents points to the same `LE 10 Business Days` predicate as the reporting obligation. No explicit neither-report-nor-rejection condition, elapsed-period trigger, own-risk qualification or event links was retained. Validation stopped at `unsupported unit`; several actions are also unsupported. |

**Result: 0/3 usable validated extractions, with substantive meaning errors.**
Generation itself reached a complete end-of-turn each time. Merely permitting
new unit/action strings would not repair the missing conditions, alternatives,
deadline anchor or risk allocation. The current format has nine allowed actions,
physical quantities and seconds/minutes; it lacks a supported business-day
deadline representation and general nonnumeric condition structure. This is a
representation and model-generalization problem, not evidence that the three
source passages were absent.

The three raw output SHA-256 values are, in question order:
`0139044c9be889b656507ed94ee3a42f08c8660839e7310c678ca90376e2325e`,
`2f3d1068cea8000495f6319149a8b2c913f808a245790ba0f42b3aeef5271d24`,
`711a1d3932fedfcf26f679a9efb0a4ad384472d33772799a50accc0f56cde3a8`.
Prompt/generated tokens were 2015/404, 1232/132 and 3893/611; gateway elapsed
times were 21.81, 13.26 and 25.45 seconds. Model allocation peaks were 15.55,
15.26 and 15.89 decimal GB. Only one model worker ran at a time. Every worker
exited; the temporary inspector directory was removed. No provider calls,
compilation loads, live state writes or source/adapter modifications occurred.

The owner explicitly asked whether the information came from the Tree. It did
not: these passages were selected directly from the PDF for diagnosis. The
earlier tests used document Tree retrieval without Gemma; these used trained
Gemma without Tree retrieval. The complete document → trained Gemma → Tree →
retrieval workflow remains undemonstrated. Future work must address and verify
that intended path, rather than continuing to improve a bypass in its place.

### File-to-Tree write and native retrieval verification — 15 September 2026

The owner made Tree-controlled retrieval the priority: calling the Tree while
MiniLM independently chooses the returned passages does not satisfy the intended
architecture. This supersedes the earlier ordinary-query semantic-selection
recommendation. That override remains in serving code and is a diagnosed defect;
the earlier improved evidence previews must not be represented as successful
Tree-controlled retrieval.

One fresh isolated project, `m12-tree-processing-verification`, ingested the
unchanged agreement's complete extracted text through the existing gateway
`/document/ingest` handler. No source passages were manually supplied to the
retrieval calls. A transparent observation wrapper called the original pinned
`apply_msr_load_to_sicd_engine` unchanged and counted actual applications.

**Write verification passed:** 501 source sections matched 501 Tree receipts,
including exact text hashes, analysis digests and routing vectors. Overlapping
coverage included every one of the 354,736 extracted characters. There were 32
native load applications: sections 0–15 through 496–500, in batches of at most
16. The Tree advanced from tick 4707 to 4739 and from 10,000 to 10,067 branches;
all 10,000 pre-existing branch semantic vectors changed. The experience Tree
was unchanged. Import took 37.16 seconds. The document Tree changed from the
canonical seed digest
`sha256:d9aec9b424459d0948f569c7e424bb5632bd118ad01bda372f62df7ca17a82ac`
to `sha256:326e7bb06bc1234d3b5cebbb9d971e89e769dfbffe1559dc78d3ce215a9e6cd9`.

**Native retrieval was exercised, but relevance failed.** Each unchanged question
selected 32 Tree branches and ranked all 501 retained section addresses using
the pinned `rank_by_branch_resonance` reader. Its inputs were document IDs and
section indices, from which the reader loaded stored routing vectors. No corpus
prose, expected passage, keyword search or semantic reranking selected the hits.
Only after ranking were returned IDs resolved to retained source text.

| Question | Ranks of required sections in this run | Native top-three sections |
| --- | --- | --- |
| Deadline and recipients | 360 and 112 | 399, 341, 288 |
| Emergency access | 64 and 226 | 399, 341, 288 |
| Piling without report/rejection | 116 and 353 | 399, 341, 288 |

The same leading sections concern a licence condition survey/works (physical
p89), dispute referral (p66) and liability limits (p53), rather than the required
clauses. Zero of the three native top-three sets contained a required section.
Score spreads were approximately 0.002036, 0.002034 and 0.002027. The emergency
ranks differ from the earlier isolated run; these are the actual measurements,
not copied baseline ranks. No cause for that cross-run difference is claimed.

All three reads preserved both runtime snapshots. Reopening the persisted
document Tree reproduced its exact head and all 501 results for the first
query. The original PDF remained unchanged. Temporary local data and owned
embedding workers were removed after verification; no large evidence export or
new source/test file was created. No product code changed in this verification.

This checks the existing MiniLM-input, 10K-derived document Tree. It does not
show a trained-Gemma-to-Stream-1 write or retrieval. The factual findings were
presented directly to the owner: file-to-Tree write passes; native ranking
returns irrelevant leaders; ordinary serving selection is overridden by MiniLM.
Correcting the override and diagnosing the Tree's input/ranking are distinct
subsequent changes. Do not conceal the native relevance failure behind another
retriever or change several variables together.

### Native app retrieval dependency and preserved order — 15 September 2026

This supersedes the MiniLM selection override described above. The owner
requires Tree-controlled retrieval and identifies the proven Tree ranking as
the reference. The pinned Tree algorithm was not changed. The ordinary document
path now processes its native first 64 records and preserves native rank for
selection; independent semantic scores remain diagnostics, not an override.
Document packet admission is version 1.8 and research trace version 1.7.

An actual native-app preview exposed a separate downstream defect: the gateway
returned records 399, 341, 288, but packet construction and manifest rendering
sorted them by record ID. Both now preserve document admission order. Renderer
version 1.7, its protocol schema, generated types and existing fixtures agree.
All changes used existing architectural source and test files.

The unchanged full agreement was imported once through the real local service
into an isolated app project: 501 chunks, 354,736 characters, with the original
extracted-text hash above. Every chunk hash and complete overlapping source
coverage were verified. In the native app's conversation "Tree retrieval
evidence", the first fixed question above was entered and Preview packet used.
A transparent in-memory observer called the original pinned reader unchanged
and recorded the real gateway invocation at document_tree.py:645. It supplied
501 record vectors and a 32-branch Tree cohort. Reader implementation:
`tom_master/agency/mechanics/leaf_vectors.py`, SHA-256
`c3f2e73693ec858a5418bebd0788b0e84bfd08c7946f77114ccf084d2b8259ba`.
The observed cohort hash was
`a99e5511084befbb44393a2c73559b3b345f4b8858b65e0b08f6ed9d46579059`.

| Native rank | Chunk | Branch | Native score | Actual selected material |
|---|---|---|---|---|
| 1 | 399 | 179416 | 0.9936731783508896 | Licence works obligations |
| 2 | 341 | 122762 | 0.9932520105685495 | Dispute referral to the Secretary |
| 3 | 288 | 122762 | 0.9931549188773721 | Liability limits |

The final gateway result, persisted manifest, outgoing prompt and native app
display all had this exact order. Selected excerpts matched source ranges
278277–278957, 205019–205685 and 166072–166726 respectively. The Tree selects
record IDs; their verbatim prose is resolved from the retained document library.

With only the native reader deliberately made unavailable, the same app
question failed visibly with "Native document Tree reader deliberately
unavailable for dependency check" and returned zero passages (0.318 seconds).
Restoring that reader returned the exact same IDs, branches, scores and order
(0.340 seconds). Both warm reads preserved the full runtime snapshot; document
and experience Tree file hashes independently remained unchanged. The first
cold preview's aggregate snapshot comparison was false because it includes
in-memory runtime initialization; it is not recorded as a purity pass.
The ledger contained two distinct packet records (versions 1.6 and 1.7), three
prepared exchanges, zero sent contexts and zero experience acceptances. There
were zero provider-send calls and zero Gemma inspection calls.

Verification passed: ten focused gateway checks, nine packet checks, one
transaction check, protocol validation, frontend and native builds, and
whitespace checks. The controlled failure was repeated on the final build.
These checks prove Tree dependency and preserved order for this ordinary
question; they do not establish every query mode or semantic correctness.
The selected passages still fail to answer the peer-review question. The next
diagnosis concerns inputs and integration against the proven Tree reference,
not replacing its algorithm. This remains MiniLM-encoded document retrieval;
it does not demonstrate trained Gemma ingestion or retrieval. Results were
also presented directly in the conversation, not only recorded here.
Owned app/service processes and the embedding worker were stopped; the isolated
83 MB temporary project was removed after verification. No large trace export
or additional source/test file was retained.

### Document-input diagnostic — 15 September 2026

The next owner-authorized diagnostic traced input construction without changing
the Tree, its ranking functions, production code or retained projects. Five
standalone inputs were examined in memory: fixed question 1, the exact correct
clause 10.3 (source offsets 110163–110789), and the three displayed excerpts
listed above. The same source-text SHA-256 was checked before extraction.
The existing offline MiniLM worker and production document compiler were used;
each input fitted one chunk. This is an input-conversion diagnostic, not a
replay of the original full chunk vectors or of the full-document retrieval.
No document was reingested and no Gemma inference was run.

The active code path is document/query text → 384-component MiniLM vector →
anchor-bank comparisons → 17 positive loads → eight-component routing address.
Document writes average up to 16 section loads per Tree update. Authored edges
are retained alongside the address but do not alter these scalar loads.
The trained-Gemma inspection path instead validates typed events and compiles
separate signed 32×32 matrices; its optional Stream 1 operation queries a fixed
checkpoint, without writing these documents. The two paths are not connected.
Thus the earlier verified document writes were real writes to the existing
document Tree, not trained-Gemma-to-Stream-1 ingestion.

Measured cosine similarities to question 1 (numeric direction, not confidence
or an assessment of legal correctness):

| Standalone passage | MiniLM, 384 components | Derived 17 loads | Stored-address projection, 8 components |
|---|---|---|---|
| Correct clause 10.3 | 0.794003 | 0.446560 | 0.999988 |
| Displayed works excerpt 399 | 0.242957 | 0.214488 | 0.999986 |
| Displayed dispute excerpt 341 | 0.301145 | 0.945780 | 0.999950 |
| Displayed liability excerpt 288 | 0.174978 | 0.053778 | 0.999911 |

The anchor conversion gives the question its strongest channel at
L_contradiction (0.007744748), whereas the correct clause's strongest channel
is T_sequence (0.011316811). The dispute excerpt's L_contradiction is
0.022702772. The 17-load similarity therefore favours the dispute excerpt over
the correct clause in this small comparison, before any Tree ranking occurs.
This is diagnostic evidence about the representation, not a replacement scorer.

The stored-address projection fixes its raw confidence coordinate at 1.0 for
these nonzero loads. It accounts for 99.997348% of the question's squared
normalized magnitude and 99.994487%, 99.990655%, 99.977630%, 99.973497% of the
four passages respectively. Content coordinates are correspondingly small.
This directly demonstrates concentration around that constant; it does not
establish that this alone caused the earlier final rankings.

The actual question-region selector uses the pinned channel-separated
projection, not that stored-address projection. A pure replay of the measured
question load gave raw confidence 0.350128366 and squared normalized share
99.940012%. The two projections have matching basis labels but different
formulas (maximum coordinate difference 0.017134068 for this question).
The loading-aware selector also uses an angular gate. Therefore the eight-
component cosine column above must not be described as the actual branch
selection score. Different projections are an integration-contract question;
this diagnostic does not establish that the pinned readout is defective.

The existing anchor bank uses beta 6.0 and contrast temperature 0.08. Model
snapshot: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Question SHA-256:
`21b1f9a320df086c748d387477800f6b9db3d5bd0d3f20a23fdf3cd723802003`.
Correct-clause SHA-256:
`16c9941ed598aee22ca6a7dad6d04d33f75ee4cfdb83f30bb01ce1a2cf6ade98`.
Existing functions and these source ranges permit reproduction without a new
fixture or retained source copy. The worker was closed after the five inputs.
No new files, model training, Tree writes, provider sends or scoring changes.
Findings were also reported in plain English directly to the owner.

The next bounded step should address the failed trained-Gemma extraction of
one real clause and its intended Tree write contract. A successful call or
changed Tree state alone is insufficient: extracted actors, actions, timing
and conditions must first match that clause. Do not silently rescale these
loads, change the pinned projections or claim that Gemma is already connected.

### One-clause trained-Gemma diagnosis and writer boundary — 15 September 2026

The owner authorized proceeding with one clause before further retrieval.
Clause 10.3 was again taken directly from the unchanged extracted PDF at
110163–110789, with source SHA-256
`16c9941ed598aee22ca6a7dad6d04d33f75ee4cfdb83f30bb01ce1a2cf6ade98`.
Neither run retrieved its input from the Tree. Two sequential offline
generations used the actual retained V14 adapter at 4,380 steps, SHA-256
`c6a4708d9ceca6dab5d275ea0bff5ac172e392d085a4fda6b0d875e51d95a994`.
The unchanged inspection worker verified all model files and adapter config,
loaded with adapter_path, and retained its read-only worker restrictions.
Only the prompt instruction was replaced in process memory; production prompts,
training corpora, weights, schemas and Tree mechanisms were not edited.

The first diagnostic asked for a source-token-bound requirements structure
allowing source verbs, nested all/any alternatives, deadline quantity/unit/
anchor, triggered follow-on duties and stated purposes. It supplied no answer
values or example derived from this clause. This was deliberately a new
diagnostic format, not the V14 training format and not a production graph.
Instruction SHA-256:
`f3cb2ecbe4c2a2e57c054bead736009c053ae8f7279edbf4c09543cf35e2865d`.

**Structured result FAILED.** It ended normally after 736 generated tokens,
but JSON parsing failed at character 1197 (expected comma delimiter). Its raw
output also contained two reversed source ranges (92–90), recipient strings
instead of source spans, a deadline value selecting "10 Business Days" rather
than just the quantity, an anchor ending at "under" before the clause reference,
and an all-actions obligation alongside a contradictory alternative group.
The purported verb for SM's duty selected "SM must procure". No malformed
output was repaired, compiled or loaded. Raw SHA-256:
`3317d41b406f8d588d8626ddd12b3bd43a4fedd6f439fc4990b4d0cdb8ede0da`.
Prompt/generation tokens: 1701/736. Worker time: 24.079 seconds; parent wall
time: 24.848 seconds. Peak model allocation: 15,353,262,446 bytes.

The second diagnostic changed only the instruction to ask for plain-English
obligations, retaining the source, source-token table, trained adapter, seed,
runtime and generation settings. Instruction SHA-256:
`d11efc5ec5805b5f926dfad2c1c85fc8718535cb865fd296c618ec0b70bd870c`.
This is a narrower comprehension diagnostic, not a loadable extraction.

Actual trained-model findings, checked against the clause:

| Fact | Actual plain-English result | Assessment |
|---|---|---|
| Actor and review | Peer Reviewer; Peer Review for Design Stage 3 | Correct |
| Deadline | Within 10 Business Days | Correct |
| Start of period | Documents made available under clause 10.2(a) | Correct |
| Choice | Issue report OR reject documents AND provide reasons | Correct |
| Report recipients/form | SM and TfNSW; Schedule 7 | Correct |
| Follow-on duty | Following rejection, SM procures that issues are addressed | Correct in the conditional explanation |
| Purpose | Reviewer is in a position to issue the report | Correctly stated, then overstated in the final sentence |

The model's final sentence was: "The desired outcome is the eventual issuance
of the Schedule 7 report." The source stops at being in a position to issue
the report. That additional inference prevents treating the prose as an exact
complete extraction. Its opening summary also stated SM's duty without its
condition; the condition was supplied later. No agent corrections were fed back
into the output or presented as model-generated structured facts.
Prompt/generation tokens: 1335/285; complete end-of-turn. Worker time:
16.543 seconds; parent wall time: 16.838 seconds. Peak model allocation:
15,250,582,446 bytes. Both workers exited; no additional training ran.

The intended writer was inspected separately. Tom Assist currently connects
to `tom_matrix.relations.matched_recall.Recall`, whose observe method explicitly
raises "This is a recall-only adapter; new observations are not authorized
here." The underlying Whole observer expects an input matrix AND an observed
consequence. Choosing consequences, substituting self-reconstruction or
bypassing Recall.observe would be a new integration decision, not a verified
document write. No such substitution was made.

An additional dependency check found the current Stream 1 source-package hash
`eebcd67a38684aa7b342f918dd664ca818c5949490b200a04bbef99c1d8e562c`
differs from Tom Assist's recorded pin
`906d7705e60af668c2a2ba3408d21935ff25c637a69621ef5484012eab70379c`.
The checkpoint and V14 adapter still match their recorded hashes. The Stream 1
checkout contains separate work; none was changed or reverted. The package
identity guard was not bypassed or updated blindly.

**Outcome: useful plain-English comprehension evidence, failed structured
extraction, zero matrix loads, zero Tree writes and zero Tree retrievals.**
This does not fulfil the complete clause-to-Tree objective. Required work is a
versioned source-grounded extraction representation and its bounded validation,
plus review of the current writable Stream 1 interface and the document-to-
observation contract. Do not describe prompt-only diagnosis as successful
training, validated ingestion or repaired retrieval. Results and remaining
failures were also shown directly in the conversation.

### Explicit interrogation of Tree parsing, writing and retrieval — 15 September 2026

The owner redirected the work to what the Tree itself and its app integration
actually do. No Gemma inference, training, product edit or ranking change ran.
This examines the active 10K-derived 8D/17D document Tree, not the separate
matrix-native Stream 1 inspection checkpoint.

Code trace establishes these boundaries:

1. `ingest_document` parses authored headings, definitions, references and
   precedence outside the Tree, using `build_declared_structure`. It does not
   extract a complete set of actors, actions, deadlines and Boolean duties.
2. MiniLM produces passage vectors. `compile_document_dense_load` converts
   anchor comparisons into 17 positive loads and three drivers. Source text,
   offsets and reference edges are retained separately; the Tree step receives
   derived numerical inputs, not the contract text or a typed requirements graph.
3. `apply_document` averages up to 16 passage loads per native application.
   `apply_msr_load_to_sicd_engine` projects those values and calls the real
   engine step. Branch state changes, while each passage's immutable address
   is retained in the receipt store. Source hashes and receipts establish
   coverage/application, not faithful preservation of each contract fact.
4. `query_address` converts the question and calls `rank_loading_aware_8d` to
   select 32 current branches using a channel-separated projection and angular
   gate. It passes their IDs, numeric vectors and branch scores onward.
5. `structural_scores` supplies externally retained passage addresses to
   `rank_by_branch_resonance`. That reader ranks each record by its greatest
   cosine similarity to any selected branch vector. It does not use the branch
   scores, branch rank, original prose, declared reference graph or ingestion
   receipt; the surrounding app checks receipts before calling it. The reader
   returns record IDs/ranks/matched branches/scores, not reconstructed facts.
6. The app resolves returned IDs to stored source text. Ordinary retrieval
   processes the native first 64 and preserves native ordering for admission.
   Exact-reference expansion, excerpt positioning and packet budgets remain
   downstream app operations. Broad research retains its separate hybrid
   ordering; the ordinary-path proof is not a proof of universal Tree-only order.

A bounded mechanism probe loaded the actual canonical 10,000-branch seed into
memory with the app's mechanics profile, restoring the same saved fields as
ProjectDocumentTreeIndex. Seed SHA-256 remained
`d9aec9b424459d0948f569c7e424bb5632bd118ad01bda372f62df7ca17a82ac`.
The source-verified clause 10.3 and the three previously displayed excerpts
were separately embedded with the existing worker, compiled and supplied as
four address records. These are standalone excerpts, not their original full
chunk vectors. One four-passage mean batch was applied through the unchanged
native engine function. This was not a full-PDF reimport or an app preview.

The native write advanced tick 4707→4708, branches 10000→10002, and changed all
10,000 existing branch vectors. Nineteen of the 32 question-selected branches
were shared before/after. Passage addresses remained unchanged. Every read
preserved a complete in-memory engine fingerprint; the seed file was unchanged.

| Passage record | Rank before this write | Rank after this write | After-write raw score / matched branch |
|---|---|---|---|
| Dispute excerpt 341 | 1 | 1 | 0.958281703 / 224676 |
| Liability excerpt 288 | 2 | 2 | 0.958008504 / 224676 |
| Works excerpt 399 | 3 | 3 | 0.957117757 / 224676 |
| Correct clause 10.3 | 4 | 4 | 0.956423738 / 215802 |

Before-write ranking deliberately supplied the four records directly to the
native reader; it did not claim they were already ingested or bypass the app's
receipt guard. This demonstrates that the reader can score supplied addresses
against an existing Tree without proving those documents were learned.

Two controls changed one variable at a time:

- Keeping branch IDs and vectors fixed but replacing only branch scores left
  all passage ranks, matched branches and raw scores exactly identical, before
  and after the write. This reproduces the native reader's score-ignoring
  contract; it is not an allegation that its mathematics is incorrectly coded.
- Including versus omitting the actually resolved clause-10.2(a) reference edge
  changed the analysis digest but left all 17 loads, drivers and routing values
  exactly identical. The reference is metadata, not a Tree load relationship.

This directly interrogates the active Tree's inputs, state change and reader,
and exposes the distinction between branch ranking and document ranking. It
does not establish that all incorrect retrieval is caused by one conversion,
that numerical Tree state contains no information, or that a replacement
ranking algorithm would be better. The unresolved architectural question is
whether externally retained passage-address matching against Tree branches is
the intended retrieval contract, and how exact document relationships should
be represented and recovered. No new mechanism was installed. The embedding
worker exited, and no project copy, checkpoint or new source/test file was saved.
The mechanism and concrete results were also reported directly to the owner.

### Owner correction: start at MiniLM → 32×32 → Tree — 15 September 2026

The owner explicitly specified the investigation boundary: MiniLM's 384-value
representations are converted into multiple 32×32 matrices and supplied to the
Tree. This supersedes continuing to diagnose the legacy 8D/17D route as though
it were the intended matrix route. The previous mechanism probe is evidence
only about the legacy implementation; it is not evidence about matrix-native
document parsing, loading or retrieval.

The requested converter does exist in this repository:

- `validation/calibration/matrix_tree_32sq_runner.py::project_384_to_32` maps
  each supplied 384-component semantic field to 32 components. `event_matrix`
  combines source/target, relation and context using the frozen outer-product
  formula and produces 1,024 numbers representing a signed 32×32 matrix.
- `matrix_event_scaw_runner.py::compile_event_views` produces up to three views
  per accepted event. Its prototype builder combines the views per passage for
  a separate binary prototype index. That index is not the native mechanics Tree.
- `gateway/typed_matrix_compiler.py::compile_prepared` produces three views per
  prepared event, then sums/normalizes them into one final passage matrix. It
  requires supplied event fields and embeddings; it is not a plain-document
  parser or a Tree writer. Its header explicitly says it is not wired into the
  app. The project-identity adapter prepares this same compiler's inputs.
- `dynamic_matrix_tree_runner.py` is a distinct frozen native-Tree diagnostic.
  It converts supplied event fields to matrices and calls `memory_tick`; its
  assertions compare the actual Tree event input byte-for-byte to the compiled
  matrix and compare routed matrices. It is an experimental runner, not the
  app's document-ingest implementation. No historical runner was launched here.

The connection audit found no calls to compile_prepared, event_matrix or
compile_event_views in non-test gateway Python files. The app ingest path still
calls ProjectDocumentTreeIndex.apply_document → compile_document_dense_load →
the 17-channel native load function. The matrix compiler callers found are
tests and calibration runners. This is a static call-site diagnosis, not a
new runtime count of emitted matrices.

Consequently the prior M12 write receipts do not establish delivery of any
32×32 document matrices. They establish the legacy load applications already
reported. A matrix-native claim requires tracing the selected actual converter,
its per-event/per-passage aggregation, the number and identities of matrices
delivered, and the receiving Tree implementation before interpreting retrieval.
Do not treat the binary prototype index, legacy document Tree, dynamic native
runner and recall-only Stream 1 checkpoint as interchangeable. No converter,
Tree, production wiring or frozen evidence was changed in this audit.

### The core application at that point

```text
Message held in the app
  -> active-project record + pure experience/document retrieval
  -> governed, visible context packet
  -> explicit send to the answer provider (for example ChatGPT)
  -> captured answer + checks against the sent packet
  -> user accepts / rejects / edits
  -> governed acceptance permits experience commit
```

The project record holds authoritative decisions and constraints. The document
library retains source text and exact locations. Each project has its own
document Tree and receipts; document ingestion updates that Tree, not the
experience Tree. Preview and retrieval read both Trees without changing them.
Retrieved evidence and a model's proposed interpretation are not automatically
authoritative project state. Acceptance does not automatically promote every
extracted statement into a project decision.

### Implemented harness: an isolated inspection view

The first integration is an opt-in diagnostic view under Chat → Experimental
local inspection. Enable inspection for the current project view, explicitly
select the retained V14 adapter, and choose Inspect. A separate checkbox and
checkpoint selection authorize an isolated Stream 1 query. The existing app
workflow remains unchanged. Inspection is not a replacement for retrieval,
the answer provider or the live Tree runtime. It runs only on an explicit
inspection action. Typing, opening the panel and opting in do not invoke Gemma.
Results remain in component memory and are discarded on input/project changes.

Input currently supports a selected portion of the unsent draft or an active
project-state object's canonical text. The service verifies active-project
ownership, source version and project-state version. Selection offsets are
Unicode code points, including when the UI contains emoji. A fixed saved V14
example is also available for wiring checks; it cannot be applied to different
source text. Document ingestion/retrieval remains the existing separate path;
this panel does not add a document browser or change either live Tree.

```text
Selected draft or active-project source passage
  -> snapshot of project ID, source ID/version, exact text and offsets
  -> pinned local Gemma base + explicitly selected LoRA adapter
  -> source-grounded typed event graph
  -> strict graph and source-span validation
       invalid / unresolved -> visible explanation; stop this lane
       valid -> deterministic event/link compiler
  -> multiple linked signed 32x32 matrix loads
  -> inspection panel: source highlights, roles, conditions, links and load IDs
  -> optional separately loaded, hash-verified Stream 1 query per load
  -> raw matrix response and trace; interpretation unavailable; no live commit
```

Gemma performs language extraction and binding. It does not generate 1,024 raw
matrix values or write directly into ToM. The compiler handles validated typed
structure reproducibly; it does not reinterpret prose. A paragraph can produce
several events with shared triggers and explicit links. Preserve recipient
versus authority, actor/object, source/target, quantities, units, comparators,
negation, conditions/exceptions, modality, revisions and temporal order. Exact
text spans must remain inspectable, including context required for pronouns.

Structural validity is not semantic correctness. A valid but incorrect entity
span or role must remain visible as an unverified model proposal. An extraction
failure must not be hidden by substituting an older parser or fabricated load.
The existing app path remains usable independently, with the comparison failure
clearly shown. Future automatic packet use requires separate acceptance gates.

### Verified mechanical interface and remaining semantic boundary

The currently wired app uses the canonical Python 10K Tree with 8D routing and
17D load contracts. The experimental Gemma compiler produces signed 32x32
matrices. These interfaces are not interchangeable. Do not flatten, pad,
project or relabel a matrix to pass an existing 17D endpoint. The existing
`legacy/shadow/authoritative` structure modes belong to the current structure
pipeline; their names do not mean this matrix integration already exists.

The runtime source is specifically
`/Users/kenmorkaya/PycharmProjects/tom_matrix_native_stream1`, not the original
mixed repository. Both that checkout and its separate Passport copy are
read-only owner boundaries. The harness installs nothing there, disables Python
bytecode writes and rejects worker file writes/network connections. Each query
worker uses a separate interpreter, inserts the exact source package path and
rejects pre-imported or foreign `tom_matrix` modules.

The verified checkpoint is `data/checkpoints/paired16_initial.pkl`, loaded using
Stream 1's existing `load_legacy` and the trusted SHA-256
`801c7720e5e1284446b17a8b5273d15872b844f39551c05c853bf479615ad964`.
The package's 115 Python/configuration files are pinned to aggregate hash
`906d7705e60af668c2a2ba3408d21935ff25c637a69621ef5484012eab70379c`.
The restored class is `tom_matrix.learning.weighted_credit.Learner`; its actual
query resolves to `tom_matrix.relations.matched_recall.Recall.query`, not the
base `NativePaired.query`. State fingerprint is checked before querying.

The compiler supplies finite signed 32×32 matrices with unit Frobenius norm.
The worker validates that norm and each exact load hash; it does not reshape,
project, pad, clip or renormalize a load. Input/output coordinates are global;
Stream 1 converts locally with `source.T @ global @ target`. A frame round-trip
is checked for each input. Event and link loads are queried independently, in
their recorded sequence, against unchanged experiment state. There is no
paragraph aggregation, consequence selection, output feedback or text decoder.

The small starting state contains 16 prepared branches, 18 occupied banks and
192 historical observations. It is neither a newly grown tree nor evidence of
learning this compiler's encoding. The two saved-example queries return zero
matrices with valid routing traces. Full serialized experiment-state hashes
before/after are equal (`148d4f1bcd05a03f9e7ba37ae182ce76b91a853fff0604bbebc39b534442a060`),
and checkpoint/package hashes remain unchanged. This establishes mechanical
wiring and pure query for these inputs. The panel explicitly reports
**interpretation unavailable**. A zero matrix is not decoded as a textual answer.

The mature `MaturePairedTree` query/preview operations were inspected read-only;
no mature owner is attached by this harness. Its teaching default, bounded
retention evidence, fixed-routing migration qualifications and subsequent
capability diagnostics do not transfer to arbitrary compiler loads. No observe,
teaching, advance/preview-advance commits, learning or live-state updates are
part of this endpoint. Future input/consequence pairing is a separate design.

### App presentation and memory boundaries

The diagnostic panel shows the original passage alongside its extracted
requirements, highlight each role's source text, and identify missing or invalid
fields in plain English. Click a role, requirement or numeric condition to
highlight its exact evidence. Matrix details can be expanded for diagnosis.
Separate input, extraction, validation, compilation and runtime outcomes include
timings and visible failure reasons. A successful stage does not imply
downstream success or semantic correctness.

For example, “If vibration exceeds 5 mm/s, stop excavation and notify the
superintendent” should show one shared trigger, a stop obligation and a notify
obligation whose recipient is the superintendent. No issuing authority is
invented. The compiler retains separate event/link loads rather than pooling
the sentence into a single matrix.

The strict span binder and the same trained-evaluation parser are used. Invalid
spans, duplicate JSON fields, missing fields and unresolved clauses stop the
experimental path; no alternative parser or field repair is substituted.
Existing comparator/Boolean normalization is disclosed, with raw output,
original bound graph and normalized graph all retained in the receipt.

The endpoint does not write experiment outputs into the live project record, document index,
experience Tree or provider prompt. Any later runtime probe uses isolated state;
pure readout and learning are separate operations. This harness calls only query.
Real project experience still follows explicit acceptance. Document
ingestion and experience learning remain separate even after eventual rollout.

### Build evidence and limits

The actual saved V14 development output `v8-dev-6-0` is the small wiring example:
two cross-sentence requirements share a condition, notification has a recipient
and no invented authority. Representative gateway checks cover that real output,
strict failure stops, disclosed normalization, resource rejection and the actual
isolated Stream 1 query. A service check uses the real local gateway and verifies
zero provider calls, unchanged project state and unchanged ledger/runtime hashes.
UI checks cover explicit action, Unicode selection and rejection of a late result
after project change. These are integration checks, not a language campaign.

Receipts record source/project/version/offsets, model and adapter identity,
parser/compiler/runtime hashes, raw output, ordered load hashes, response matrices,
traces and timing. Purity evidence includes active-project runtime file hashes,
in-memory runtime snapshots when already loaded, canonical project-state hashes,
and main ledger/WAL byte hashes. SQLite shared-memory coordination is excluded.
Concurrent live changes make a purity observation inconclusive; a matching hash
is scoped evidence, not an assertion about every possible operation.

V14 at 4,380 steps remains selected, with adapter SHA-256
`c6a4708d9ceca6dab5d275ea0bff5ac172e392d085a4fda6b0d875e51d95a994`.
V22 was reviewed and rejected (188/192 development exact, 189 valid, 48/56 causal).
V23 completed 96 updates but has only 50/248 verified evaluations after resource
interruptions; it is not selected. V12/V15 held-out failures remain exposed and
cannot be reused as fresh confirmation.

Local inference uses the pinned Gemma snapshot, explicit V14 adapter, frozen
MLX/Transformers versions, native no-thinking prompt and greedy generation.
It checks model/configuration hashes before loading. Input and output are bounded;
there is no truncation, automatic retry or training. The initial 28 GiB startup
threshold was carried over from a training policy and was not a measured
inference requirement. Training, Gemma inspection and the detached Stream 1
query are separate operations; their memory must not be added together. The
Gemma child exits before the Stream 1 child starts.

The authorized single-passage follow-up on 15 September verified all ten pinned
Gemma files plus V14 weights/configuration; all twelve hashes matched. Inspecting
the tensor headers and installed loader showed 14,200,055,868 bytes of language
weights; the text loader discards the vision weights. The adapter file adds
11,918,394 bytes. The inspection collector was retaining each generated token's
vocabulary-sized probability array. It now retains only text and scalar evidence,
while preserving the complete end-of-turn check. Four focused checks verify
release of those arrays and refusal of empty/incomplete generations; all nine
inspection checks pass. The run receipt now includes model-engine memory readings.

The revised startup budget is **22 GiB estimated reclaimable memory**, derived
from the pinned text weights, adapter, up to 0.704 GiB float32 attention-cache
storage at the existing 8192 combined-token bound, 4 GiB temporary-allocation
allowance and 4 GiB system reserve, rounded up. This is a conservative budget,
not a measured minimum, allocation cap or general guarantee. Other model/large
Python jobs are still excluded and the worker still stops on conflict or below
2 GiB estimated remaining headroom. No other process is stopped by the harness.

**The first fresh V14 extraction completed through the gateway** with 28,231,548,928 bytes estimated
reclaimable before loading. The real gateway path used the same exposed
`v8-dev-6-0` passage, 1197 prompt tokens and 274 generated tokens, reaching token
106 with `finish_reason=stop`. Extraction took 16.99 seconds including worker
startup; extraction through isolated query took 18.15 seconds. The fresh raw
answer, normalized graph and both compiler loads exactly matched the saved
example. Semantic inspection confirmed the stop obligation, notification to the
superintendent and shared vibration > 1.7 mm/s condition, with no invented
authority or actor. This is a controlled integration check, not new held-out
language evidence.

Measured MLX active allocation after model loading was 14,202,810,516 bytes;
peak active allocation through generation was **15,239,479,190 bytes (15.24
decimal GB)**. Cache at completion was 247,611,364 bytes. macOS reported peak
resident process memory of 11,623,350,272 bytes; this is a different accounting
measure and must not be added to the MLX figure or treated as total GPU memory.
These are workload-specific observations, not a maximum for all passages.

Fresh raw-output SHA-256:
`a3c44bd1dac1097f25fc0cacd6c99fc582dd33da0fb532e5cc78f7b0604cb2f2`.
The two ordered compiler-load hashes are
`2a8b7e787d0c727e6a78c80b4613b286ddb6b744740b699d66ec7ffbbe432395`
and `be16b1602600c07d50ad659a698dd92434be624778d5738ae485bd406eac44bb`.
The subsequent real Stream 1 queries again returned zero matrices, with unchanged
checkpoint/package and serialized-state hashes reported above; interpretation
remains unavailable. That first run used a detached diagnostic project directly
through the gateway, without a live project store. It did not exercise the native
desktop; the subsequent app-window check below closes that integration gap.
No training, provider send, new artifact file or model copy was involved.

### Native app-window check — 15 September 2026

The current frontend and native desktop/service were built offline, using the
standard `target/` build directory with debug symbols and incremental compilation
disabled to limit artifact size. A separately identified development window,
**Tom Assist Inspection**, used the compiled app at
`target/gemma-inspection/Tom Assist Inspection.app`. Its executable is a hard link
to the 25 MB build output, not a second model or binary copy. Automatic local app
data for this check lives in `.tmp/gemma-ui-7mt_yki2/data` (about 2.5 MB). These
paths are inside this repository; the existing installed app and its data were
not changed. No new source files were needed.

The actual native window was operated through its visible controls: Chat,
an isolated local conversation, the same 185-character unsent draft, explicit
inspection enablement, Local Gemma, retained V14 at 4,380 steps, and the verified
Stream 1 starting state. Setup and typing produced zero inspection calls.
Pressing **Inspect selected passage** produced exactly one fresh model run through
the native app → service → gateway → pinned Gemma/V14 → validator → compiler →
separately loaded Stream 1 path. All five stages visibly passed. Generation again
used 1197 prompt tokens and 274 generated tokens, with the same raw-output hash,
normalized graph and two compiler-load hashes as the preceding gateway check.
Extraction took 21.11 seconds; the full gateway path took 21.75 seconds. Model
allocation peaked at 15,239,479,190 bytes again; cache at completion was
247,602,668 bytes. These are two measurements of one exposed passage, not a
language evaluation campaign.

Visual checks in the native window confirmed the stop obligation, notification
recipient, shared `p1` condition and vibration > 1.7 mm/s display. Clicking
the excavation highlighted exactly characters 15–42; clicking the superintendent
highlighted 111–142. Clicking the shared condition highlighted its bound evidence
at 15–185. Missing actor and authority were visibly "not specified". The original
draft remained intact. Stream 1 returned the same two zero matrices, and the app
kept interpretation unavailable rather than displaying a fabricated answer.

The app visibly reported both runtime and project-ledger purity as verified.
An independent read-only snapshot of the isolated SQLite store before and after
the inspection/highlight actions had the same logical-dump SHA-256:
`3a6dfe928dfb79496559eb2145ff7f4c58c791603c8104776bcc4bed15261023`.
All table counts were unchanged, including 16 state objects, 17 state events,
30 seeded turns, zero provider exchanges, zero experience acceptances and zero
runtime-commit receipts. No live runtime was initialized and zero provider sends
occurred. The isolated conversation was created before this comparison began.
This evidence applies to this controlled app check, not every possible input or
production use. The result window is left open for review; Gemma and Stream 1
query workers have exited, leaving only the lightweight local app/services.

Native executable SHA-256:
`073af09ec194d9013f4712af9e6a0a098805bbe361d1226752d1859376a3796e`.
Service executable SHA-256:
`6d401cb831d57b8fce991bf9c6e8e7811100bf7d5325bfa54032ddea582eb8ed`.
Frontend JavaScript SHA-256:
`17fdd8ab279b25ccad36cf1a706079584928493e528fbf757cf0166795343aa1`.

New Gemma inference must respect other local jobs. A resource refusal requires
a later explicit inspection action; it does not queue a retry. Checkpoint
selection remains explicit and must not silently advance to newer weights.

### Architectural placement

All application source and checks remain inside
`/Users/kenmorkaya/PycharmProjects/ToM_assist`; paths in this section are relative
to that repository. This implementation creates no new source files or folders.

The implementation reuses the existing desktop view in `apps/desktop/ui/src/`, service orchestration
in `crates/assistd/src/`, and gateway client boundary in `crates/tom-adapter/src/`.
Reusable local inference and graph/load orchestration belong in `gateway/`,
beside `event_graph_span_extractor.py`, `event_graph_span_wire.py`,
`typed_event_graph.py` and `event_graph_compiler.py`. Do not put runtime code in
`validation/` or name system modules as tests. Confirm any new filenames and
locations with the owner before creating them. `GemmaInspection` lives in `gateway/tom_gateway.py`,
and the UI component in `apps/desktop/ui/src/Chat.tsx`. The separate
`inspection.gemma` method uses the existing Tauri/service/gateway boundaries.
It bypasses conversation prepare/send/evaluate, candidates and commits.

Actual tests belong in the existing `gateway/tests/`, `crates/assistd/tests/`,
`crates/tom-adapter/tests/` if present (otherwise use that crate's established
test layout), and `apps/desktop/ui/tests/`. Use small representative fixtures.
Keep large model and diagnostic artifacts on Passport under `gemmatraining`,
outside live project storage. Preserve existing frozen training files and the
shared worktree's unrelated changes.

The harness is built and remains opt-in. It is not deployed or enabled by default.
Normal-use enablement still requires fresh held-out extraction evidence,
matrix discrimination and downstream temporal/authority checks. No production
migration, checkpoint promotion, Stream 1 modification or new learning is authorized
or claimed by this implementation.

## Workflow development history

The earlier diagram in this section described the 3 September state, when the
17-channel prose parser was built but switched off. That diagram became
misleading after the native distributed-memory and RGM integration work. The
progression is now:

```text
31 August
  pure preview proved: looking does not change the experience tree
       |
       v
3 September
  evidence-bound 17-channel prose parser built but kept off
  because ordinary prose produced incomplete loads
       |
       v
15-16 September
  native 32x32 distributed tree returns isolated and causally tested
  RGM document ingestion, source recovery and evidence reading integrated
       |
       v
17 September
  reviewed relationship direction and event order stored in the small ToM tree
  exact RGM passages bound to learned distributed structures
       |
       v
18 September
  read-only structure review queue added
  explicit Save teaches or binds; detection never teaches automatically
  learned structures can reopen exact sources even with zero RGM candidates
```

The 17-channel general prose-loading lane remains separate and default off. The
live bounded structural-memory lane uses explicitly reviewed 32×32 inputs and
complete native distributed returns. The current end-to-end diagrams are at the
top of this document.

## What remembers what

Each memory system has a different job. Project history and source records are
retained or superseded with an audit trail instead of being silently rewritten.

```text
                         ONE TOM ASSIST PROJECT
                                  |
       +--------------------------+--------------------------+
       |                          |                          |
       v                          v                          v
 PROJECT RECORD            CONVERSATION MEMORY          RGM DOCUMENT MEMORY
 goals, decisions,         front shelf: active          exact source text
 constraints, rejected     long shelf: retained         chunks and offsets
 paths and open work       movement reasons logged      hashes and provenance
       |                          |                          |
       +--------------------------+--------------------------+
                                  |
                 +----------------+----------------+
                 |                                 |
                 v                                 v
          EXPERIENCE TREE                REVIEWED STRUCTURAL ToM TREE
      changed only by governed          changed only by explicit teaching
      accepted conversation turns       of an approved 32x32 structure
      the changed shape is memory       complete distributed state is memory
                 |                                 |
                 v                                 v
      helps select project context      recognises relationship direction
                                        and event order, then returns exact
                                        pointers into RGM document memory
                 |                                 |
                 +----------------+----------------+
                                  |
                                  v
                           OUTCOME RECORD
                  what was offered and what was used
                         is retained for later work
```

Four things it still does not remember.

Nothing carries between projects. Project records, conversation history,
document candidates, document receipts and document-Tree geometry all belong
to the active project. Every project starts with its own byte copy of the same
canonical 10K seed. Ingesting one project's documents can therefore change
only that project's document Tree; neither text, identifiers nor structural
influence crosses the project boundary.

Nothing ages. Something from the first message competes on equal terms with
something from the last.

A no is now written down but never read. When you dismiss a clash, that is
recorded against everything that was on offer at the time. Nothing consults it,
so the same rejected thing can still come back.

Nothing outside a single project can retrieve or receive that project's
document text.

## What is honest about the middle of that picture

There are now three separate tree jobs. Accepted conversation experience drives
the project's experience Tree only after the governed commit. The legacy
document-index Tree receives evidence-addressed 17-channel document loads and
remains distinct from the matrix-native structural work. The reviewed
structural-memory path uses the approved small Stream 1 ToM tree and explicit
signed 32×32 inputs. These trees are not interchangeable.

Documents never drive the experience Tree. At legacy document ingestion, each
immutable chunk is embedded, compiled into a fully positive evidence-addressed
17-channel load, projected through the pinned eight-component routing basis and
applied to that project's dedicated copy of the canonical Python 10K Tree held
under its `tom/document-index/` directory. The whole document and exact source
offsets remain in the project-local permanent library; the document-index Tree
stores structural territory and receipts, not the contract prose.

At preview, Tom Assist projects the question through the same document address
path and reads the document Tree without stepping it. Candidate chunks must
carry a Tree receipt for the active project. Broad document research may then
expand a Tree-addressed hit to its exact authored clause, follow only precise
declared references and classify explicit temporal duties. Every included or
excluded unit keeps its clause address, Tree receipt, actor support and reason.
The resulting cited document evidence may enter the visible packet, but it is
never presented as committed Tom state and never becomes experience merely by
being retrieved.

In the reviewed structural path, a validated source relationship is compiled
into a signed 32×32 input and taught only after explicit review. Query-time
recall preserves native branch identity, every signed 32×32 field and exact slot
maps. Matching returns source pointers into RGM; RGM remains responsible for
the exact text. The structural return is never reduced to a branch average or a
whole-tree score.

What was offered to you and what you actually used is now written down. Nothing
reads it yet. It is accumulating so that a later decision can be made on real
numbers rather than a guess.


## 16 September 2026 — frozen native-memory app integration

Approved runtime placement: `gateway/native_memory.py`, isolated worker
`gateway/native_memory_worker.py`, boundary checks in
`gateway/tests/test_native_memory.py`, and the held-out fixture in
`validation/calibration/stream1_native_memory_e2e_fixture.json`.
The desktop's explicit **Answer from learned documents** action calls
`conversation.native_answer` through the service and gateway. Only the registered
project receives its frozen collection. No automatic provider send, training,
experience commit or migration occurs. Heavy workers run sequentially.

The MiniLM top-three access method, encoder, native selector, saved memories,
full-field exact matcher and evidence selector were frozen throughout inference.
All 3,217 native return branches retain their signed 32×32 matrices and original
positions; 4,051 total branches belong to this saved tree. No whole-tree score,
root assembly or branch pruning was introduced. Anonymous full-field identity
precedes source binding. Existing large reference arrays/checkpoints stay on
Passport; identical fresh returns refer to those complete arrays by hash.
The native owner checkout changed during integration. An exact hash-verified
package snapshot reproduces the checkpoint's original machinery without editing
that checkout or relaxing its checkpoint validation.

Twenty new questions were frozen before inference. **17/20 passed**; this is
**not acceptance or reliable general recall**. All **60/60** candidate fields
matched their complete stored references, and the tree remained unchanged.
H08 dropped the explicitly stated `SM → TfNSW` reimbursement direction and
falsely approved clause 23.5 (`TfNSW → SM`). Restoring just the omitted question
roles in an offline diagnostic makes the unchanged selector reject the source.
H09 treated a disputed actor as a required condition and refused a question that
could be answered “No.” H20 correctly split a two-part request, but MiniLM had
already omitted the needed premium memory from its three candidates, leaving
only the deductible answer. No first-pass case was tuned or silently repaired.
The previously broad unscored case remains unscored.

Final local Gemma wording is strictly extractive: every approved source must
appear once with all words intact; citations are attached from provenance. This
is not free-form summarisation, and answers are not yet persisted to conversation
history. The real built Tauri window, service and gateway displayed the premium
answer with clause 23.2/page 55 and expanded source text in a separate temporary
project store. The normal user projects were not migrated. Median latency was
77.475 seconds (range 70.09–87.16 seconds).

Checks: eight Python boundary checks, two UI checks, service isolation, protocol
validation, UI typecheck, and desktop/service build passed. The 20-case service
runner completed, but its semantic acceptance result is 17/20. Setup failures
are preserved separately. A test-report serialization defect rounded 18 old
telemetry values in their last binary digits; the original historical sections
were restored to their exact pre-run SHA-256 checksums, and the writer now
updates only this experiment through a lossless historical JSON round trip.
All five frozen historical section hashes and runtime file hashes pass audit.
No numerical tree fields or checkpoints were rewritten.

Results, actual answers, first-pass failures, diagnostic replay and limitations:
`validation/runs/stream1-native-learned-recall.json`, section
`native_memory_end_to_end`. Next engineering work is question-role completeness,
yes/no contradiction handling, and access coverage for compound questions;
keep the native tree frozen while addressing these separately.


## 16 September 2026 — native answer interpretation and compound access repair

The two variables were diagnosed and changed separately. First, replaying the
original extractions and the original recalled sources through corrected
question interpretation selects expected evidence in 19/20 cases (diagnostic
replay, not a new held-out score). Explicit active/passive reimbursement
relations now retain the parties stated in the question. A narrowly scoped
question disputing the party named in a cited obligation receives a checked
yes/no verdict, followed by the unchanged complete source clause. Recognized
negated propositions outside this grammar are refused; ordinary negated failure
conditions remain valid. This grammar does not claim general language coverage.

Second, the existing question planner now runs before candidate access. Each
independent part keeps the original MiniLM top-three operation. Their union is
recalled through the unchanged tree and complete signed native-field identity
check. The premium/deductible miss gains the missing premium source this way.
The evidence selector, full-field matcher, source roles, tree and native
threshold were not changed. No tree response was averaged or reduced.

Live verification has now repaired all three original failures: H08 rejects the
reversed repayment claim, H09 answers No with clause 23.3, and H20 returns both
clauses 23.2 and 23.3. Two attempted checks were interrupted at the language
stage by a separate local model/test process; their blocked records are retained
separately from subsequent results. Workers remain sequential, and validation
pauses when the existing resource safeguard reports another competing process.
The original 17/20 first-pass section remains unchanged. See
`native_memory_repairs` in the existing compact JSON report for the bounded
follow-up, independent six-question fixture, runtime freeze and actual answers.

Follow-up completed: **3/3 previous failures repaired; 6/6 newly frozen checks
passed**, including the intended partial answer when the requested bank-account
detail is absent. All **30/30** native returns exactly matched full signed
3,217×32×32 fields; tree state remained unchanged, with zero training/root
assembly calls. The 19 focused Python checks passed. Two resource-blocked
attempts remain recorded separately; the identical frozen runtime was resumed
after the competing process finished. Completed answers took 63–100 seconds.
This remains a six-fact integration, not proof of general document recall.

The real isolated desktop action also completed: the combined question displays
both complete source clauses, 23.2 and 23.3 (page 55), as a supported answer.


## Larger learned collection — frozen twelve-clause check

The follow-up doubles the registered source collection from six to twelve clauses
of the same M12 Interface Agreement. The original six-fact checkpoint and every
previous result remain intact. Six native teaching events run individually on a
separate tree copy, with unchanged native machinery, encoder, selector, source
pattern comparison and answer pipeline. New clauses cover disclosure, keeping
insurance in force and notification, including near-matching duties for SM and
TfNSW. The fixture and twelve questions were frozen before inference in
`native_memory_larger_collection` in the existing JSON results file.

The existing evidence checker has a known, explicit scope limit: it represents
premiums, deductibles and replacement-cover obligations, but not disclosure or
notification duties. Questions about new duties count as failures if unanswered;
they are not scored as successful absent-evidence refusals. Each failure is
traced to candidate access, native return, evidence selection or wording. The
same question's MiniLM scores restricted to the original six candidates provide
a control for shortlist changes, without modifying or collapsing any tree field.

All larger checkpoints and complete numeric fields are held under
`/Volumes/My Passport for Mac/tom_assist_test_results/native_learned_recall/larger_collection12/`.
The existing calibration runner contains the reproducible stages. Production
runtime files remain hash-frozen. Numerical determinant warnings arose while
new branch orientations were constructed; captured stacks identify their origin,
and subsequent native restore validation and complete-field checks are retained.

Completed twelve-clause result: **7/12 questions passed; five failed**. All
**39/39 selected native memory returns** exactly matched their full signed
3,264×32×32 fields. The saved tree contains 4,099 branches; twelve canonical
fields were finite, nonzero and distinct after reload. No runtime file, selector,
scorer or prompt was changed. The original six-fact tree and historical results
remain intact.

Failures are retained individually:
- L01: the TfNSW premium source was omitted from the address shortlist, including
  in the six-candidate control using the same query scores.
- L07: an explicit SM→TfNSW repayment direction was dropped. The app falsely
  marked clause 23.5 (TfNSW→SM) as supported. The narrow literal guard did not
  recognize “requires SM to reimburse.” This false support was reproduced in the
  real desktop window with the twelve-clause profile.
- L09: a newly added disclosure clause displaced the needed TfNSW premium source
  from the shortlist. The same wording retained it in the six-candidate control.
  Only the deductible part was answered.
- L11: the correct newly learned disclosure source was recalled but rejected as
  outside the fixed evidence schema.
- L12: the notification source was omitted by address access. A diagnostic replay
  supplying that source still failed the evidence schema; it is not a successful
  retrieval or a revised test grade.

Controlled replays changed one variable: supplying the missing source repairs
L01 and L09 at the evidence stage; restoring L07's stated direction produces the
required rejection; supplying L12's source does not overcome the scope limit.
These remain diagnostics, separate from the 7/12 first-pass result. Source/reader
scope is not general document reasoning. The first corrective priority is the
false “supported” result, followed by access coverage and broader evidence
checking, while keeping native field handling intact.

One live attempt was resource-blocked and resumed unchanged; a later preflight
pause avoided starting another request while competing local work held memory.
Teaching peaked at about 6.9 GiB per worker. Complete answers took 42–131 seconds.
Native orientation-calculation warnings and their stacks are preserved; reload
validation passed and no invalid values appeared in the complete return fields.
The superseded intermediate tree was removed. Final checkpoint and full numeric
fields remain on Passport; no PDF or HTML report was generated.

### 2026-09-16 — small native-tree / evidence-library boundary

Owner requested the prebuilt roughly 500-branch Stream 1 tree and a review of
RGM in tom_master17D, then authorized proceeding with the smallest reusable
boundary. Review found Tom Assist already has PermanentLibrary and an existing
older RGM integration. No bulk copy, upstream edit, old tree-mechanics import,
new source filename, model call, commit or push was needed.

Added opt-in NativeEvidenceLibrary to the existing gateway/native_memory.py.
It stores exact source text and provenance with a pinned tree/reference binding
in the existing PermanentLibrary. The existing complete-field equality matcher
remains the only readout. No branch averaging, scalar ranking, evidence approval
or production answer-path wiring was added. All sources are returned only after
a unique exact signed-field match; source or link substitution refuses.

Existing gateway/tests/test_native_memory.py now passes 27 checks, including
database reopen, branch/sign/cell changes, altered sources, resealed substitutions,
wrong trees, missing records, immutable bindings and ambiguous matches.

The existing calibration runner now provides --rgm500-bridge teach|verify.
It restored the hash-verified clean 500-branch fixture, applied two native input
exposures (513 branches), captured the untrained memory returns, then delivered
two consequences at that same geometry. Teaching and preparation balancing were
disabled for final capture/save. A separate process restored the learned tree;
all 393 signed 32×32 bank returns reproduced exactly for both canonical inputs.
The archive also preserves all 513 routed input matrices, public terminal
matrices, baseline fields, learning differences, branch identities and topology.
No examiner root assembly or whole-tree similarity was used. Native teaching
retains its unchanged internal machinery and telemetry.

Result: 2/2 canonical returns recovered the bound evidence; both learning
differences were nonzero; 0/2 untrained controls returned evidence; branch-position
and sign reversal controls returned none; swapped binding receipts refused.
Identity rejection is not a semantic or topology-causality claim. Synthetic
source labels were deliberately attached to pre-existing matrix associations;
there was no language encoder, unseen wording, RGM-alone comparison, or proof
that the matrices encode the prose relationship. This completes the mechanical
connection only, not the desired complementarity experiment.

Master report: native_rgm500_evidence_bridge; all historical sections verified
unchanged. Passport folder: native_learned_recall/rgm500_bridge_v1 (233,225,750-byte
checkpoint, 34,484,220-byte field archive, 77,824-byte SQLite library). Peak process
memory 1.13 GiB. Original fixture remains unchanged. Three native determinant
warnings occurred during teaching (divide-by-zero, overflow, invalid); recorded
verbatim, fields finite and restore valid, no claim that warnings are resolved.

Next: a fair RGM-alone versus matrix-ToM-assisted evidence-access test using the
same source content and explicit input-generation boundary. Do not count this
canonical identity replay as proof of relational language understanding. The
earlier 12-clause app battery remains 7/12, including its false-supported case.

### 2026-09-16 — controlled RGM / small-tree access comparison

Owner authorized proceeding with RGM-alone versus RGM + the native matrix tree.
Inspection first established that the current bridge feeds each candidate's
canonical teaching input to the tree; it does not feed the actual question.
The bounded experiment therefore measures the current connection's incremental
effect, without inventing a new query encoder or scorer.

Added --rgm500-comparison baseline|native and paired punctuation-baseline|punctuation-native
stages to the existing calibration runner. Baseline imports only the unchanged
ordinary RGM memory reader from the local tom_master17D checkout in its own
process. The native process imports no older tree or RGM modules. Each baseline
question starts from identical newly admitted two-record RGM state; insertion
order is tested separately. Both arms use the same source texts, candidates and
ordering. The second arm merely validates the same candidates through their
canonical native returns, then fetches their exact evidence from the existing
read-only experimental database. Evaluator source labels never choose matrices.

Original four questions: RGM first record correct 4/4, plus ToM also 4/4;
all candidate lists/orders unchanged. The source/query final full stop was a
confounding lexical cue because RGM tokenization retains punctuation. Preserved
the full original result, then removed only each question's final full stop.
All four controlled questions tie, both arms first-record correct 2/4, and
reversing record insertion changes the first result in all four. There is no
semantic winner in that tie. Both candidates contain the correct source in 4/4.
ToM resolves zero ambiguities. All 16 requested native fields across the two arms
are exact at all 393×32×32 coordinates, with ordered branch identities retained
and the original full archive referenced for each return. No retraining, model
calls, root assembly by the examiner, new readout score, tree/source writes, or
new bulk files. The 500-origin learned tree remains 513 branches and unchanged.

Report sections native_rgm500_access_comparison and
native_rgm500_access_punctuation_control are separate; earlier outcomes unchanged.
This is an ordinary RGM read / canonical bridge diagnostic, not a comparison with
the entire older contextual chat stack and not evidence against the potential
of query-driven ToM. Synthetic source associations still have the narrow scope
documented above. Next experiment requires actual query-dependent matrix access,
with identical language processing available to both arms; replaying the two
candidate teaching inputs cannot establish relational comprehension or an added
contextual retrieval benefit.

### 2026-09-16 — actual RGM document ingestion, before any comparison

Owner corrected the prior synthetic test: the document must pass through RGM's
own chunker. Added --rgm-document-ingestion to the existing calibration runner
and ran the unchanged native ingest_any_document on the full executed M12 PDF.
Native auto mode, limits and zero_copy_strict policy were unchanged. Loaded only
doc_ingest.py directly to avoid interface/__init__ initializing unrelated chat
code. Observation wrappers retained identical arguments, objects and write calls.
The native MemoryStore used its explicit storage_dir option in disposable
/private/tmp space, registered under an isolated tenant. Its records survived
cold reload and are fully retained in the master report before temporary cleanup.
No user store, upstream source, native tree, provider, or chunk setting changed.

Result: ingestion says success; 212 native chunks produced, only first 50
retained/persisted. Actual insurance sections are section_54 and section_55, so
the 50-anchor limit excludes both. Separately, the native chunker cuts sections
at 4,000 characters instead of splitting. Exact prefix checks show section 23
loses 2,457 of 6,457 characters and section 24 loses 3,194 of 7,194 characters.
All 12 known clause texts are present in extracted PDF text (exact comparison
after whitespace removal only); 6 survive complete in the native chunks; 0
survive in admitted anchors. The earlier whitespace-collapsed coverage result
is retained and explicitly distinguished from the whitespace-agnostic check.

Source resolution is independently broken on this path: all 50 persisted PDF
references return the same raw PDF decoded as UTF-8, starting %PDF-, ignoring
section_N fragments. None returns its actual extracted chunk. All 50 supplied
source line ranges also have end_line < start_line. This is observed native
behavior, not a tree recall failure. Do not run the RGM/ToM comparison until
document coverage and exact-source resolution are fixed and rechecked.

Master report section: rgm_native_agreement_ingestion. It retains native text
extraction, heading detection, all 212 chunks, all 50 created anchors and cold
records, exact source references, source-resolution hashes, both native indexes,
coverage at each stage, stderr cap warning, source and module hashes. Historical
sections are unchanged. No new PDF, standalone report or large artifact created.
User must receive these failures directly, not just a link to the report.

### 2026-09-16 — lossless RGM-heading corpus adapter and exact source recovery

Owner authorized proceeding with the ingestion repair. Added an explicit adapter
in gateway/document_ingestion.py using the original RGM heading-detector output.
It maps headings back into the immutable extracted text, retains all sections,
partitions oversized sections at native subsection/newline boundaries, and keeps
source-character and line ranges with checksums. It preserves even repeated
headers stripped by the native detector. One extraction plus its manifest is
retained in the existing PermanentLibrary schema; references resolve extracted
text rather than reopening PDF bytes. This is an opt-in comparison boundary,
not a change to upstream RGM, default application ingestion, or the tree.

Ran --rgm-document-ingestion-repair in the existing runner. Frozen native
extraction and headings were reused to isolate each change. Removing only the
50-anchor cap leaves 6/12 clauses complete because native truncation remains.
Lossless partitioning preserves all 272,620 extracted characters, 212 sections
and 248 chunks (largest 3,997 characters). All 12 insurance clauses occur in
full within individual chunks. A separate fresh process reopened the saved
SQLite library and recovered 248/248 exact chunks; concatenation reproduces the
source checksum. The disposable database was 413,696 bytes and was removed.
The source extraction already retained in the master report plus the added
manifest/references reproduce it without a second permanent document copy.

Seven focused tests passed: tail sections beyond 50, long-section splitting,
Unicode/form-feed handling, removed-header preservation, exact reopened source
resolution, rejection of altered references/content, and rejection of gaps,
overlaps, wrong hashes, missing tails and source changes before persistence.
The actual PDF and upstream RGM modules match their original hashes. Historical
master-report sections remain unchanged; new section is
rgm_native_agreement_ingestion_repair. No tree/model calls or generated PDF.

Remaining: run the RGM-alone retrieval baseline over this repaired corpus, then
compare with the approved native 500-branch ToM using identical evidence. This
repair establishes extraction retention and source recovery, not retrieval
accuracy, full PDF extraction correctness or an improvement contributed by ToM.

### 2026-09-16 — complete-document ordinary RGM baseline: failed retrieval

Owner said Go. Added bounded baseline/diagnosis modes to the existing runner;
used all 248 repaired chunks and the twelve existing larger-collection questions
unchanged. This explicitly tests ReflectionGatedMemory.write_memory/read_memory,
not the entire contextual chat/STM fusion system. Native default gates, 512
capacity, 256-bucket VectorStore and top-three read are unchanged. Uniform
record context is recorded; all question trials begin from fresh identical
admission, preventing read reinforcement leaking between questions. Evaluation
labels are accessed only after retrieval. No tree or model is invoked.

The first cheap rehearsal stopped: three writes were checksum_duplicate
refusals (one repeated date and two repeated deed-poll provisions). That stopped
result remains frozen as rgm_complete_document_retrieval_baseline. Follow-up
rgm_complete_document_retrieval_baseline_dedup_checked changes only the harness
check: allow a native duplicate refusal if full text exactly matches an already
admitted record. All 248 source occurrences remain retained in the corpus;
245 unique texts are indexed. Nothing bypasses the native gate.

Result: 0/10 required-evidence coverage at rank one; 0/10 within top three.
Correct ranks by question: L01 16, L02 13, L03 18, L04 20, L05 13,
L06 8, L09 20, L10 33, L11 33, L12 4. L07/L08 have no supporting
answer and are not scored as retrieval accuracy. L10 checks only recall of its
known deductible clause; absent policy number is not validated. All 36 returned
references resolve exact source. Reverse insertion changes 0/12 returned lists.
The full 245-candidate rankings, questions, exact-source refs and metadata are
retained. Run took 5.57 seconds. Original PDF/upstream modules unchanged.

Then decomposed the existing winner/correct scores for all ten cases: all twenty
reconstructed to 1e-12. Native encoding lowercases, splits on whitespace and
hashes token counts into 256 buckets. Punctuation persists; unrelated tokens
collide (insurance/or, carries/dispute, excess?/bridge, 24.7,/the). This explains
the mechanics of the observed reader, not a proven benefit from replacing it.
No score, threshold or ranking was changed. Separate frozen section:
rgm_complete_document_reader_diagnosis. Historical results remain unchanged.

ToM-added-value comparison was NOT RUN. The existing 500-branch-derived bridge
has two synthetic associations, not document learning; canonical candidate
replay also cannot add a question-dependent ordering. Broad context fusion was
not exercised: it adds continuity, actions, observations, priors and older-tree
resonance around this same vector reader. Do not present 0/10 as a test of that
whole system, or use its older tree as the owner-selected 500-branch substitute.
Next work must establish the document/query access path for the comparison;
neither unrelated synthetic memory replay nor basic hashed matching establishes
how the proposed structural-memory + exact-evidence architecture performs.

### 2026-09-16 — same corpus and questions, MiniLM instead of hashed counts

Owner approved replacing only text similarity with MiniLM. Added encode/read
modes to the existing runner and reused the exact previously approved local
all-MiniLM-L6-v2 checkpoint, verifying all six recorded model/tokenizer files.
Encoding and RGM retrieval ran in separate processes; no model download,
training, ToM load, native-tree change or upstream edit occurred. Read stage
uses unchanged native RGM gates and cosine with a 384-dimensional VectorStore
instance whose text encoder resolves frozen MiniLM vectors. Unknown inputs fail
instead of falling back. The same 248 source occurrences/245 unique indexed
records, twelve questions, uniform record context, top-three bound and duplicate
accounting were verified against the prior baseline.

Frozen encoding rule uses existing build_token_chunks(max188, overlap32) and
build_semantic_profile's normalized centroid weighted by newly covered source
characters. Each original RGM chunk remains one candidate; internal windows
never become separate retrieval candidates. Full 272,620 characters represented
by 650 windows across 248 source chunks and twelve questions; 91 source chunks
needed multiple windows. Largest actual model input 190 tokens, zero truncation.
Tokenizer warned on unsplit source offsets (up to 2,599 tokens), but the model
only received the bounded windows. Loader reported an unexpected position_ids
buffer; no missing parameter was reported. Both observations are recorded here.

Results: first-place required-evidence coverage 4/10 (previously 0/10); top-three
7/10 (previously 0/10). Correct ranks: L01 1, L02 4, L03 1, L04 6,
L05 3, L06 1, L09 1, L10 4, L11 3, L12 2. The three top-three misses
all require chunk_79: SM premiums/deductibles. L05 still puts opposite-direction
insurance evidence first while correct evidence is third. Do not claim actor
or repayment direction is solved. L07/L08 rejection cases remain unscored;
L10 counts only recall of the known clause, not its missing policy number.
All 36 references resolve exact source. Reversing insertion changes 0/12 lists.

Nine focused source-preservation/token-window tests passed. Master report now
41.75 MB, with separate immutable encoding and paired-baseline sections; all
historical section hashes checked unchanged. Encoding took 10.31 seconds with
peak 1.05 GiB; isolated reader took 10.00 seconds with peak 1.65 GiB. No new
permanent file created. Native tree comparison is still pending: this is evidence
that semantic access improves document candidate retrieval, not that ToM adds
structural distinction. Do not retune scores or widen top-k to hide the misses.

### 2026-09-16 — broader RGM capability and actual document-path audit

Owner rejected treating the ordinary reader as an exploration of RGM and asked
for a proper audit. Inspected tom_master17D checkout cb0d90c1 and locally saved
origin/main 1b1cf823 without fetching, changing upstream files, starting a live
backend, calling a provider, or loading either tree. Expanded only the existing
calibration runner and results file; the gateway README now records the capability
inventory, wiring boundaries, positive and contrary evidence, and reproduction.

RGM is materially broader than previous tests: persistent governed memory;
causal, identity and commitment indexes; entity/relationship/goal/change/outcome
snapshot projections; contextual multi-source retrieval; section navigation and
numeric evidence; branch resonance; district-live context; and, on saved main,
transactional branch-event/memory bindings and feedback-grounded recall. Snapshot
structure is supplied by callers, not proof of autonomous prose understanding.
Saved-main branch-event modules are absent from the checkout. No ordinary chat
caller for that newer runtime joint was established, although district-live
recall does have a chat caller. Do not conflate these paths or imply deployment.

Fresh existing component checks: seven snapshot checks and four saved-main branch
recall checks all pass. The latter include supported recall behind 256 distractors,
feedback-off/shuffle controls, tampered-address refusal and exclusion of ordinary
memories as branch-event authority. Saved-main modules and tests were loaded
verbatim from pinned Git objects in an isolated process; fixture BranchState
objects were used, not a new mature-tree experiment. Temporary payloads removed.

Three historical structural gate artifacts verified against their stored seals.
Copied 10K-tree evidence supports grounded branch/memory recall rather than pure
cosine selection; the capacity report reopens 512 records, specifically two
branch-event memories plus 510 ordinary distractors. Production use and language
understanding are not established. The earlier Carillon relational certification
is also recorded as blocked by a wrong-root result, with held-out testing unopened.

The first actual document-path import stopped in .venv-gateway due to missing
requests. Preserved that result and used existing system Python successfully.
Replayed actual retrieval, fusion, bounds, formatting, then evidence policy on
the repaired corpus with native word counts and frozen MiniLM, twelve questions
each. Eight relevant function syntax trees match checkout and saved main.
No conversation/continuity/action stores or learned branch state were supplied.
Full-source required-clause coverage is 1/10 and 9/10 respectively; 500-character
excerpts and final 200-character snippets each retain zero complete target clauses.
This diagnoses lost evidence during packing, not final answer accuracy. The real
2,000-character budget retained four excerpts; do not compare it as the same
top-three ranking metric used previously.

Original native indexes contain 41 skills, 369 headings, zero numeric facts, and
remain the limited-ingestion indexes. Simple fresh-process reopening restores
fifty document records but neither index. The ordinary section-injection gate
always returns false; do not re-enable this intentionally disabled bypass.
Evidence policy still independently consults the indexes. For both encoder arms,
L01 (premium payer) and L09 (premium/deductible responsibility) incorrectly receive
a VERIFIED reply, section_4_count is 3, from an unrelated access section. The
policy accepts the count before checking that a count was requested; the chat
branch would return it before the language model. Other ten questions return
open-intent not_found and would not force that early response. Full chat not run.

Conclusion: the earlier basic-reader results understated RGM and cannot support
a simple split of RGM as dumb archive versus ToM as structure. Preserve/reuse the
existing provenance and branch-binding design. Before a fair circa-500 native
ToM comparison, repair evidence handoff and question-appropriate verification in
ToM Assist. Do not copy the older 8D tree machinery into the native32×32 system,
change thresholds, collapse native returns, or alter the upstream repos.
Results remain in separate capability-audit/component-check sections of the
existing master report, including failed imports. No new permanent files or PDF.

### 2026-09-16 — restore complete selected passages before evidence checking

Owner approved fixing the source-passage handoff first, one variable at a time.
Added build_rgm_evidence_context to existing gateway/document_ingestion.py and
used it in the existing native learned-recall runner's explicit RGM document
path. Source resolution uses the ingestion registry, exact corpus range/checksum,
and reopened PermanentLibrary. Selected candidates/order/scores remain fixed;
the adapter returns complete memory content and source-labelled answer context.
Missing or altered provenance fails; a caller budget rejects overflow instead
of truncating or silently discarding a candidate. This is the one-range-per-chunk
document adapter, not an arbitrary multi-source memory formatter.

The first native replay stopped before completing a question because my metadata
copy used JSON and native retrieval metadata contains a set. Preserved that
attempt as STOPPED_HANDOFF_METADATA_COPY in the original source_handoff section.
Changed only the copy to preserve native types and added that regression case.
The separate --rgm-document-evidence-handoff-v2 replay completed all 24 cases
(twelve questions, native word counts and frozen MiniLM). All selected IDs,
rank-fusion scores and original pre-repair contexts exactly match the frozen
audit. All 96 selected source passages resolve exactly and remain complete in
the new answer context after reopening storage. Payload text ranges from 3,562
to 13,790 characters; including provenance, 7,573 to 17,798 characters. No models
or trees loaded; temporary databases removed.

Complete-clause delivery to answer context improves from 0/10 to 1/10 with native
word counts and from 0/10 to 9/10 with MiniLM. L04 still lacks chunk_79 in its
selected set; source restoration cannot fix this retrieval miss. No claim of
correct answers or support for absent facts. The unchanged evidence policy gives
the same decisions/replies: false VERIFIED section_4_count is 3 for L01/L09;
open-intent not_found for the other ten questions. That defect is the next
separate issue, not hidden by the improved delivery figure.

Fourteen focused existing-file corpus/handoff checks pass. Results are in the
existing master report's separate _source_handoff_v2 section; the failed attempt
and earlier results are preserved. Upstream hashes/status unchanged. No new
permanent files, PDF, tree/scorer/threshold changes or default desktop wiring.

### 2026-09-16 — prevent heading counts answering unrelated questions

Owner approved the next isolated evidence-checker fix. Confirmed the cause in
unchanged upstream evidence_policy: section-index lookup can produce a heading
count without a count request; decide infers numeric intent from that result
and verifies it before checking what the question asked.

Added guard_rgm_heading_count to existing gateway/native_memory.py, using plain
policy/evidence records and no upstream import. It identifies section_N_count
results, accepts only explicit same-section subsection/subheading-count requests
or exact named-count requests with one matching active document, and otherwise
returns needs_evidence_reading with no reply. Unsupported/compound wording is
unverified, not proof that evidence is absent. Original policy output remains
recorded. Count extraction, retrieval, source handoff and non-count/unverified
results are untouched. This is request/source alignment, not a general semantic
answer verifier or proof that the native index counts correctly.

New existing-runner mode --rgm-document-question-check completed all 24 paired
runs. Candidate IDs, rank-fusion scores, full source context and raw upstream
decision/reply match the prior handoff stage exactly. False section_4_count
approvals for L01/L09 are rejected in both encoder arms; all other twenty
decisions/replies unchanged. Required complete evidence remains 9/10 with MiniLM
and 1/10 with word counts. L04 remains a candidate-selection miss. The two newly
unverified questions are not yet correctly answered; other ten still get
upstream open-intent not_found. No final answer or language-model call occurred.

All 45 gateway/tests/test_native_memory.py checks pass (18 new count-guard
checks). Positive request-alignment controls are component fixtures, not a new
document count benchmark. Report section _source_handoff_v2_question_check is
separate from all prior evidence. Native source hashes/status and full 32×32 tree
machinery unchanged. Existing files only; no PDF, upstream change or default
desktop activation. Next task: evidence reading/selection using intact passages.

### 2026-09-16 — full-passage reading: eight correct outcomes, reader failures exposed

Owner approved selecting supporting clauses from the complete frozen passages
and producing source-backed answers. Added the explicit reader orchestration to
gateway/native_memory.py, reusing source-span validation and compound-question
planning. It takes only question/full selected passages, never expected labels
or known source-role fixtures. Returned answers are exact quotations with source
identity and extraction offsets. Existing local Gemma runs without a LoRA adapter
or training; MiniLM selections, corpus, source handoff and tree remain unchanged.

Preflight process inspection was initially sandbox-denied; approved execution
permissions allowed the existing resource check and offline model worker. No
competing-model blocker was present. Fifteen local generations completed twelve
questions, including split questions and one planning generation. Max prompt
4,167 tokens, no truncation; 14.83 GiB measured peak MLX allocation. No tree or
external provider ran. Temporary source shelf removed. No new permanent files.

Reviewed correct: L01 TfNSW premiums (23.2), L03 TfNSW deductibles (23.3), L05
TfNSW reimburses SM on demand (23.5(b)), L06 SM reimburses TfNSW (24.5(b)),
L09 both TfNSW obligations, L10 SM deductible plus refusal of missing policy
number, L11 TfNSW insurer-information duty (23.4(a)), L12 SM notice (24.7).
Thus 8/12 correct question outcomes, including one correct partial answer.

Remaining four: L02 identifies SM but fails exact quotation because extracted
source contains 'p ayable' and the model writes 'payable'. L04 correctly declines
given its selected sources, but remains an upstream selection miss (chunk_79).
L07/L08 both fool the reader on reversed situations. L07 is blocked by non-exact
quotation. L08 initially passes quote integrity while citing the opposite
repayment direction: a genuine quote is not proof it answers the question.

Preserved all original generations/results. Added the existing explicit named
repayment grammar as a consumer comparison between question and quote; mismatch
invalidates the answer. Replayed all fifteen cached calls with identical input
and instruction hashes, zero new generations. Only L08 changes from supported
to invalid. Do not count either reversed-party case as correct understanding.
Do not claim the narrow direction check verifies all conditional situations.
Did not loosen source-copy checks to hide the PDF word-splitting failure.

All 51 native-memory tests pass, including altered/missing sources, partial
answers, changed quotations, and renamed-party direction controls. Original run
is rgm_document_source_answers; separate replay/semantic review is
rgm_document_source_answers_relation_check, COMPLETE_WITH_READER_FAILURES.
No upstream change, retrieval retuning, tree change, PDF or default desktop
activation. Next unresolved issue: verify the whole stated situation (failure
party, cover purchaser, repayment direction), plus the independent source-copy
and missing-candidate defects. This result is not completion of automatic answers.

### 2026-09-16 — check the complete linked replacement-insurance situation

Owner authorized proceeding on failure party, cover purchaser and repayment.
Added check_rgm_replacement_chain to the existing evidence boundary, with no
source IDs, expected labels or party names hard-coded. It extracts four named
roles and spans from question/selected text, and checks the same clause's (a)/(b)
condition and debt link. Repeated payer/debtor/creditor statements must agree;
it does not assume the failing party is the debtor. Unknown wording, qualifiers,
negation, missing/extra subsections and unresolved repayment provisions defer.
This grammar is limited to observed compliance/replacement-insurance wording.

One matching full chain supplies the whole clause as a source-bound quotation.
Conflicting chains cannot donate separate roles to a fabricated combined match.
For L07, 23.5 matches failure/buyer but conflicts on repayment; 24.5 does the
opposite. For L08 the complementary mismatches are reversed. Both now return
not_supported on the selected evidence. L05/L06 keep correct source answers,
now with their complete conditions attached. Other reader paths remain unchanged.

Cheap source rehearsal initially deferred all four because a PDF newline inside
'remedies available' prevented recognizing 24.5; source phrase whitespace now
accepts line wraps, with no text or word changes. Initial unit run: 62 passed,
one assertion incorrectly expected a final newline inside the quote. Corrected
the assertion to the existing validator's last-word boundary, not the runtime.
Strengthened the source join to require actual ordered (a)/(b) markers and an
If condition, not just a matching clause-number string; first replay preserved.

Final replay verifies all fifteen original model input/instruction hashes and
uses the saved raw generations unchanged. Zero new model calls. Ten of twelve
question outcomes are correct on this exposed fixture (eight complete/partial
answers, two supported-evidence refusals). L02 remains blocked by the extracted
'p ayable'; L04 remains the missing chunk_79 retrieval case. Evaluation labels
are used only after selection; status and manual semantic checks both count.

All 65 native-memory tests pass, including independent four-role mutations,
renamed parties, incomplete/negative/additionally-qualified source conditions,
wrong clause/subsection links, ambiguous candidates and wrong model proposals.
New results: rgm_document_source_answers_chain_check and the final _v2 section.
Original reader errors/relation replay stay intact. No upstream/tree change,
retrieval tuning, new permanent files, PDF, training or default desktop activation.

### 2026-09-16 — verify PDF word spacing without rewriting evidence

Owner authorized the next step. Diagnosed L02 against the original PDF: page 57
(printed 52) shows payable as one word. pdfplumber independently confirms it;
the p-to-a glyph gap is about 0.401 points against adjacent word gaps around 4.2.
Whole-chunk alignment was rejected because the historical extraction contains a
different footer number. Did not rewrite that historical text or conceal this.

Added optional source-owned spacing resolver in document_ingestion.py. It binds
the source to a checksum-verified PDF, locates the quotation's unchanged letters
and punctuation with unique surrounding context, and verifies actual word
boundaries in the independent extraction. At most 64 non-whitespace context
characters per side, minimum 32 total. It never treats all space deletion as
valid. The quote validator invokes it only after exact matching fails and still
returns the original immutable extraction span, offsets and separate proof.
Missing/ambiguous correspondence fails closed. Requires pdfplumber; no default
desktop activation. No retrieval, tree, source-corpus or model changes.

Replayed all fifteen saved generation calls with identical input hashes, zero
new calls. Only L02 changes invalid to supported: SM must pay/cause premiums to
be paid under clause 24.2. Original absolute span 149723:149994 is retained,
including p ayable. Eleven of twelve exposed outcomes are now correct. L04 is
still a retrieval failure: required chunk_79 not selected. This is not held-out
validation or completion of app integration.

78 native-memory tests and 14 RGM corpus/handoff tests pass. New controls cover
wrong PDF/source identity, changed names/numbers/negation, meaningful word
boundaries (now here/nowhere, a part/apart), repeated locations and insufficient
context. Appended rgm_document_source_answers_pdf_spacing_check; historical
sections and their failures preserved. No new permanent artifact or PDF.

### 2026-09-16 — locate the remaining excess-clause retrieval failure

Owner authorized tracing where L04 loses its correct source. Native telemetry
and source identify the exact point: chunk_79 is rank six in both retrieval
channels and fused ranking. The 2,000-character preview limit admits four
500-character previews and breaks at rank five. The correct sixth candidate
would require 3,000 cumulative preview characters. This is a handoff loss.

Added a bounded replay mode in the existing calibration runner. Reconstructs
the same document-only native state, corpus, frozen MiniLM vectors and original
indexes, with fresh isolated objects per arm. Native function wrapper observes
the inputs to the existing bounds function and delegates unchanged. All twelve
questions run at 2,000 and 5,000 preview characters; ten-item limit unchanged.
Control selections match all twelve archived results. Pre-bounds projections,
rankings and scores remain identical. Evaluation labels are read only afterward.

Required source availability is 9/10 versus 10/10 answerable questions. L04's
correct chunk survives and all seven selected complete passages authenticate.
No new reader answer was generated; 11/12 remains the latest answer accuracy.

First attempt stopped before retrieval because the runner expected doc_id in a
corpus range rather than taking the known document registry identity. Preserved.
Second attempt then exposed a real boundary defect: the vector-only fusion path
omits source_refs. Preserved that refusal too. Final v3 records both successful
handoffs and refusals; L01/L02 lack refs on added chunk_76, L12 on chunk_92.
The source checker rejects those complete packets. No citation was invented or
candidate silently dropped. Vector-only records also retain full text instead
of 500-character previews, so raising max_chars is not a uniform candidate cap.

Completed rgm_document_candidate_budget_diagnosis_v3. No production limit change,
upstream edit, tree operation, model call, training, network access, new artifact
file or PDF. Next engineering boundary is preserving authenticated provenance
for vector-only candidates, then checking the reader's complete-source budget.

### 2026-09-16 — restore original citations and measure expanded reader inputs

Owner authorized the next step. Added optional original_anchors_by_source to the
existing source handoff. Recovery applies only to vector-only document records
whose source_refs field is absent. Requires exactly one document tag, matching
original ingestion anchor identity/content, one original reference and exact
resolved persistent-corpus text. Does not infer citations from answer labels,
replace existing malformed references, alter ranks or mutate incoming objects.
No upstream source changes; absent trusted registry keeps strict refusal.

Replayed both frozen preview-budget arms on the same twelve questions. All
24 complete-source handoffs pass. Exactly three refs recovered: chunk_76 for
L01/L02 and chunk_92 for L12. Candidate IDs, captured pre-bounds projections,
scores and previously valid citations remain identical. Ten of ten answerable
questions have complete required sources in the expanded arm. Preserved all
prior failures; new section rgm_document_candidate_provenance_repair.

Measured exact reader inputs without loading model weights. Initial mlx_lm
tokenizer import aborted on unavailable sandbox Metal device. CPU AutoTokenizer
reproduces the fourteen archived prompt hashes and token counts exactly, then
measures expanded inputs at 5,338–7,247 tokens. All fit the existing <8,192
prompt limit; L04 uses 6,233. No truncation, provider/model/tree call or threshold
change. rgm_document_expanded_reader_preflight records all measurements and
identities. Reused the frozen question parts; no new answers or planner calls.
The answer result remains 11/12 pending fresh reading of these expanded sources.

28 focused RGM source tests pass. Broader native-memory/document suite: 149 pass,
one fails in saved Stream1 inspection because current Stream1 package identity
differs from pinned GemmaInspection.STREAM_SHA. Guard left intact; external tree
source untouched. This is not a clean full-suite claim. No default desktop
activation, large/new permanent artifacts, PDF, commit or push.

### 2026-09-17 — expanded reader run blocked before loading the model

Owner authorized rerunning the twelve questions. Extended the existing reader
runner with an expanded-source mode: use the frozen authenticated wider candidate
sets, unchanged Gemma reader/instruction, same source/chain checks, and the exact
fourteen inputs already measured by preflight. Reuse only the unchanged question
decomposition call; answers must be generated fresh. PDF spacing verification
uses the existing bundled PDF runtime because the model runtime lacks pdfplumber.

Attempt stopped before model loading: estimated available memory 23,082,483,712
bytes versus the unchanged 23,622,320,128-byte (22 GiB) headroom allowance.
Two read-only follow-up checks remained below the allowance; final estimate
22,540,763,136 bytes (about 21 GiB). This is a conservative existing headroom
check, not measured model consumption. No process/app was stopped, threshold
lowered, model loaded or generation spent. Source repositories untouched.

Preserved rgm_document_expanded_source_answers with STOPPED_SOURCE_READER and
zero calls/results, plus rgm_document_expanded_reader_memory_followup. Separate
attempt2 entry point is prepared to preserve the first attempt; it has not run.
All 78 native-memory checks pass. Latest answer accuracy remains 11/12; no claim
that the expanded evidence improved answers yet. Additional free memory is the
remaining execution prerequisite.

### 2026-09-17 — complete the expanded-source reader test

Owner directed retry and then explicitly to run. Fresh resource check passed
with no competing process blocker; no guard bypass/exclusion was needed. Ran
the prepared attempt2 mode using the same Gemma base reader (no LoRA), fourteen
fresh answers and one identical cached question-decomposition call. No tree
loaded. All fourteen exact prompts matched verified preflight identities/counts.
Original source checks, four-role checks and optional independent PDF spacing
verification remained unchanged. Runtime 194.65 seconds; MLX peak 15.04 GiB.

Outcome: 11/12, unchanged overall. L04 is fixed: correct complete clause 24.3
now reaches the reader and it answers SM. L12 regresses to not_supported even
though complete 24.7 is in supplied chunk_80: SM must notify TfNSW as soon as
reasonably practicable of the stated claims/events. Prompt identity proves the
source was supplied. This is a reader false refusal, not a retrieval absence.
Other final outcomes remain correct, including the absent-policy-number partial
answer. Raw Gemma still proposes wrong support for L07/L08; the existing full
situation checks catch both. Do not claim Gemma alone achieves 11/12.

Manual post-run review verifies all returned absolute source spans; all previous
results remain sealed unchanged. Initial review assertion mixed bare chunk ID
with corpus-qualified source ID; corrected that review assertion only, without
regeneration or altered outcomes. Raw run is
rgm_document_expanded_source_answers_attempt2; appended semantic review is
rgm_document_expanded_source_answers_attempt2_review. Existing upstream module
hashes and repository status still match. No production activation, training,
tree/retrieval modification, PDF or new permanent artifact file.

Next diagnostic: hold the L12 question and reader fixed and compare the original
four passages with the expanded eight, retaining raw outputs. Do not yet assume
which added passage or context effect explains the false refusal.

### 2026-09-17 — repair notification false refusal and rerun all twelve

Owner explicitly requested repair and retest. First ran a two-arm fresh diagnosis
with the same L12 question, reader/instruction, reset seed and source checks.
Original four sources return supported; expanded eight return not_supported.
Exact old/expanded prompt hashes and token counts match their frozen records.
This reproduces context sensitivity without assuming one distracting passage.
Preserved rgm_notification_context_diagnosis before implementing the repair.

Added find_rgm_cited_clause and one bounded refusal recheck in native_memory.py.
After ordinary not_supported only, an explicit unique clause present in selected
evidence may be read on its own with the unchanged question and instruction.
Requires a following clause boundary; ambiguous/absent references do not guess.
Four-role refusals are not retried. Exact quote binding must stay inside that
same source/clause. Both raw generations persist. No answer/party/clause-number
constants, ranking change, thresholds, new tree work or model training.

The first full retest stopped before loading due to another small CPU tree job.
Owner's prior explicit direction to run alongside that job was applied narrowly:
verified process 95379 as native_500_strengthened_cue_reasoning.py in Stream1,
with no MLX library, and excluded only it from concurrency checks. Memory
headroom and 19 GiB model allocation cap unchanged; no process stopped.
Successful run took 203.80 seconds, model allocation peak 15.04 GiB. Fourteen
fresh initial readings plus one focused L12 reading; unchanged question plan
replayed. Focused reading took 3.18 seconds with 518 input tokens.

All twelve final outcomes correct. Other eleven answer objects identical to the
previous reviewed run. L12 now identifies SM's clause 24.7 notice duty. Its
focused model highlight omitted the additional policy-required notice sentence,
so final deterministic rendering returns the whole matched clause. Retained the
highlight separately and replayed all fifteen exact generation inputs/outputs
through final code, zero new model calls; source offsets remain exact.

Fresh outputs: rgm_document_cited_refusal_recheck_answers_attempt2. Final exact
replay and semantic review: rgm_cited_refusal_recheck_final. Initial refusal,
earlier context failure and blocked attempts remain untouched. Existing four-role
checks still catch the raw model's reversed-party mistakes. Missing policy number
still refused. All 89 native-memory tests pass, including clause/party renaming,
ambiguous/missing references, invented/outside quotes and preserving omitted
conditions. Existing exposed battery only, not held-out validation or evidence
of new ToM capability. No default app activation, new permanent file or PDF.

### 2026-09-17 — copy RGM locally and wire the experimental document path

Owner approved gateway/vendor/rgm17d/ after asking whether RGM had actually
been copied. It had not: earlier diagnostics imported 17D directly. Copied 18
modules (681,166 bytes) with internal imports namespaced. Seventeen are complete;
chat_adapter contains only its unchanged _retrieve_relevant_memories function
and the required standard imports. SOURCE.json pins upstream commit, dirty-state
hash, all source/copy hashes and the slice. AST comparison proved only namespace
relocation changed each retained function/module. Original repositories untouched.
No models, checkpoints, large documents or validation fixtures copied.

Exact frozen candidate parity: all twelve prior queries return the identical
ordered source lists using the local copy, without importing upstream modules.
An initial duplicate-admission assertion compared RGM's intentionally erased raw
content; fixed it to check the native checksum_duplicate rejection plus the
original ingestion registry. Native admission/scoring unchanged.

Experimental EvidenceTomGateway path enabled only by
TOM_ASSIST_RGM_DOCUMENT_ANSWERS=1, using the existing explicit document-answer
endpoint. Uses active project documents, native heading detection, lossless
corpus ranges, persisted model/code-bound embeddings, unchanged contextual RGM
retrieval and the repaired evidence reader. Rebuilds isolated RGM for each query,
no live tree creation/mutation or claim of ToM learned recall. Project capacity
limited to unchanged native 512 chunks to prevent silent pruning. Source cache
and corpus live in existing project library. Worker exits between MiniLM/Gemma.
Existing frontend now labels this mode Answer from project documents; citations
expand full original source with Unicode-safe answer-span highlights. No page
number invented for plain imported text. Earlier native memory mode stays separate.
Default launch configuration was not activated or existing user session restarted.

Real local Unix HTTP gateway test with full PDF re-extracted using the copied
native reader, four new questions and real local models. Temporary project only;
no fixture/report data entered runtime. Three semantically correct outcomes:
SM notification duty with all conditions; absent policy number refused; two-part
premium/excess answer cites TfNSW clause23.2 and SM clause24.3. APP04 literal
expectation incorrectly required the word excess, but the verified source says
deductibles; preserved false mechanical check and added manual review.

APP03 FAILED desired verdict: model proposed supported using the opposite
repayment direction. Existing validator rejected it and app returned blocked.
Did not hide or count this as successful refusal. First response lacked diagnostic
trace; fixed blocked output to retain the raw generation and reason. Fresh paired
APP03 rerun reproduced it: exact source quote, wrong requested relationship,
'quoted repayment direction does not match the explicit question'. No new scorer,
threshold, prompt or party-specific fix. Initial failure and rerun remain sealed.

95 native-memory checks pass; 91 selected RGM/native-answer checks across both
Python test files pass; UI typecheck and all14 smoke checks pass (including
click/open citation, astral Unicode span and no guessed page). New UI test first
failed because its hand-authored end offset omitted the period; corrected fixture
end127. Existing Rust explicit-action/project-state test passes with local-socket
permission; initial sandbox run could not bind Unix socket. No full suite claim:
known unrelated Stream1 source-pin mismatch remains outside this work. No full
Tauri user-session run, no default activation, no ToM-versus-RGM benefit claim.

Reports: rgm_local_app_integration and rgm_local_app_integration_refusal_diagnosis.
All initial report sections retained unchanged. Further work should address
reader relation-verdict coverage before making this the default; do not weaken
source/direction verification to turn APP03 into a pass.

### 2026-09-17 — actual desktop import and answer verification

Owner authorized the real desktop check. Found and repaired an integration gap:
Memory had no import control, and the old ingest endpoint initialized legacy
trees. The opt-in RGM mode now imports an explicit local PDF/TXT/Markdown path
with the copied native reader, lossless chunker and real MiniLM vectors directly
into the existing project library. List/get/withdraw/diagnostics use that same
library without initializing either tree. Original file/text hashes retained;
the unchanged 512-chunk capacity is enforced before encoding. Existing files
only; no owner-repository changes or new PDF.

Launched a real isolated Tauri build in /private/tmp/tom-rgm-desktop-Dabg9F and
used native UI automation throughout. Created project
cfbcf00e-b3d8-4eee-802e-9494f5d5c06e, imported the full M12 agreement through
Memory, and confirmed 248 chunks, one document and zero runtime-head rows/tree
files. Clicked only the explicit local-answer action, never provider Send.

Initial reader attempt blocked before model loading: the guard classified the
known circa-500 CPU test as a competing large Python process and required the
older 22 GiB estimate. Verified that exact job's command, Stream1 working
directory, sub-4-GiB resident memory and absence of MLX. Added a narrow optional
operator PID allowance with those checks. Based on the prior measured 15.04 GiB
reader peak, use a 17 GiB MLX allocation setting plus 2 GiB available reserve;
other model blockers remain. The separate test was never stopped. Once it ended,
restarted only this gateway without that temporary allowance.

Real desktop outcomes: 3/4 correct. Notice question correctly identifies SM and
as-soon-as-reasonably-practicable, with all source conditions; missing policy
number refused; two-source question returns TfNSW premiums and SM deductibles.
Opened all three supporting source references in the actual UI. Reversed-party
repayment still FAILED: Answer unavailable, not the desired clear correction.
Its prior raw-output diagnosis remains applicable, but no fresh raw worker
trace is claimed from this UI run. Do not count blocking as a fourth pass.

96 native-memory tests and 15 UI smoke tests passed; UI typecheck passed and
diff check clean. No new >100 MB files in build/app/temporary runtime scan.
Full suite not claimed; unrelated prior Stream1 source-pin mismatch remains.
All 95 earlier report sections preserved by digest; new sealed record is
rgm_desktop_ui_integration in the existing report. This tests local RGM desktop
integration, not ToM learned recall or ToM added value. Feature remains opt-in;
experimental answers are not yet saved in conversation history. Isolated app
is left showing the two-source answer for review.

### 2026-09-17 — reversed repayment answer repaired

Kept the original failed desktop result and diagnosis unchanged. The failure
was not retrieval: RGM supplied clause 23.5 and Gemma quoted its exact repayment
sentence. The verifier correctly noticed that TfNSW→SM was the reverse of the
question's SM→TfNSW claim, but converted that useful contradiction into an
invalid result and the UI's generic Answer unavailable message.

Added one bounded evidence-verdict path. It applies only to an explicit yes/no
reimburse/repay question that cites exactly one complete clause and names both
parties. The clause must expose both repayment parties, and the relationship
must exactly match or exactly reverse the question. Only the reverse case emits
the fixed prefix “No. The cited clause states the opposite repayment direction,”
followed by the complete exact clause and its existing source reference. No
model paraphrase becomes evidence. Uncited, incomplete, duplicate, ambiguous,
third-party and open-ended clause questions retain the prior fail-closed path.

Focused repayment checks passed 9/9. The complete native-memory file now passes
100/100; UI smoke passes 15/15, typecheck passes, and diff check is clean. The
same APP03 wording was rerun in the real isolated Tauri window. It displayed No,
the complete clause 23.5, and chunk_78; opening the citation showed TfNSW must
reimburse SM. This repairs the known fourth desktop outcome without changing
RGM retrieval, MiniLM, Gemma, the ToM tree, thresholds, or source-direction
verification. A new sealed report section preserves the original failure.

### 2026-09-17 — verified ToM capability beside RGM

The owner redirected the architecture away from making ToM reproduce every
document detail. The tested division of labour is now:

```text
                              question
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
          RGM semantic retrieval       reviewed query structure
          likely exact passages        relationship / event order
                    |                           |
                    |                           v
                    |                 ToM distributed recall
                    |              branch identity + signed 32x32
                    |                fields + exact slot maps
                    |                           |
                    |                           v
                    |                   bound RGM source IDs
                    |                           |
                    +-------------+-------------+
                                  |
                                  v
                    exact RGM text and provenance
                                  |
                                  v
                 independent per-source evidence checks
                 retain every direct supporting source
                                  |
                                  v
                     supported wording or clear
                     partial / unsupported / ambiguous result
```

RGM is not classified as a simple vector store. The broader audit of
`tom_master17D` verified governed persistent memory, exact source provenance,
contextual retrieval, commitment/identity/causal indexes, structured snapshots,
branch-event components and document ingestion. The selected circa-500-branch
Stream 1 tree is being tested only for a narrower addition: persistent,
position-sensitive structural memory that can connect and distinguish exact RGM
sources when their wording is similar or when the common structure is spread
across different topics.

#### Native learned structural memory

The real-clause structural bridge used mirrored insurance clauses 23.5 and 24.5
from the executed M12 Interface Agreement. Reviewed failure-party and
replacement-cover roles were compiled into signed 32×32 matrices and taught to
fresh copies of the hash-verified small tree. The two relationships wrote 381
and 387 different native branch/slot locations with zero overlap. Four held-out
questions, repeated under both teaching orders, opened only the correct
relationship: 8/8 correct-only activations and zero reversed-source activations.
The corresponding frozen RGM baseline put the correct chunk first for 3/4
questions.

The reviewed relationship was then stored as an RGM-native structural snapshot,
serialized, reloaded and used as the only source-side structure supplied to the
tree. Two unseen questions reopened all 381 learned locations; the untrained
tree opened none. Teaching-input and returned-answer fields were deliberately
kept as different native object types. A coexistence control loaded both
mirrored RGM structural records together: all four questions opened only their
own relationship's locations and no unowned location.

This establishes persistent reviewed RGM structure → ToM learned state → unseen
query reactivation. It does not establish automatic extraction. The retained
V14 full-graph parser produced directionally plausible proposals on manual
review but 0/2 were valid under its frozen schema and their graph shapes were
inconsistent. Automatic full-graph teaching therefore remains blocked.

#### What ToM added over the full RGM retrieval path

Three bounded comparisons now identify two capabilities RGM did not supply in
these cases.

| Capability | RGM result | RGM plus ToM result | Claim boundary |
| --- | ---: | ---: | --- |
| Relationship direction over two near-identical real clauses | Correct source remained in all 8 candidate sets; correct first in 6/8 | Correct relationship selected in 8/8; both reversed-direction misses repaired | Two reviewed mirrored clauses and four questions over two order controls |
| Event order with equal entities, actions and native RGM word vector | Native vectors tied in 8/8; rank fusion followed insertion order; correct first in 4/8 | Correct learned sequence selected in 8/8; untrained tree selected nothing | Controlled synthetic order isolation; supplied temporal links |
| One structural motif across two real contracts | Across three structure-only questions, only 1/6 expected source occurrences appeared in the twenty returned candidates; both sources together in 0/3 | Both source pointers returned in 3/3; 6/6 expected occurrences; untrained tree selected nothing | One reviewed two-event motif, two native RGM chunks, three questions |

The relationship comparison used the unchanged full contextual entry point
`interface.stm_ltm_retrieval.retrieve_ltm_with_stm_triggers`. ToM received the
same candidate set and selected by exact equality of the complete native memory
slot map. There was no new training run, model call, branch averaging or
whole-tree score in that comparison. RGM continued to own the exact text and
provenance.

The sequence comparison changed only event order. Two records contained the
same entities, actions and word bag. RGM's underlying vectors were exactly equal;
reversing insertion order changed its first result for all four questions. The
two ToM temporal-link memories occupied non-overlapping locations and resolved
all eight trials. Only the explicit temporal-link matrix was taught; equal event
loads were excluded.

The real cross-source comparison used the unmodified RGM parser on two executed
project documents:

- `SMWSA M12 Interface Agreement - Fully Executed 2 February 2022.pdf`, SHA-256
  `29383bf63b32d42edebbfafd85adca9e2ce7be9a1b38ad49a0d28f4d859077ba`;
- `SCAW D_C Deed - Executed 1 March 2022.pdf`, SHA-256
  `a9dda3b6376d27bd76a01adc4a7692838b4271a9967c53f69fa6883dafc14f99`.

It produced 315 native chunks; RGM admitted 312 and correctly rejected three
exact duplicates. Interface clause 11 and D&C clause 31 each contain the
reviewed sequence written notice → required meeting, despite describing
different project situations. Their native vector ranks for the three
structure-only questions were 47/22, 30/33 and 13/32. One ToM memory learned the
shared notice-before-meeting structure once and retained both chunk IDs. Every
question reopened its complete 381-location slot map and therefore released
both exact RGM source pointers. This is the tested form of “one learned structure,
evidence from multiple locations.”

The cross-source test intentionally used the upstream native heading chunks,
including their 4,003-character truncation. Tom Assist's separate lossless RGM
corpus adapter remains responsible for complete production evidence. The result
proves that the shared structural source index works on two real chunks.

#### Live notice-before-meeting integration

The existing reviewed RGM–ToM bridge now supports that one temporal motif in the
live document path. A user can explicitly mark an exact RGM passage as stating
reviewed notice before a meeting. The first passage teaches one
temporal-link 32×32 matrix. Reviewing another passage with the same structure
adds its exact source pointer to the existing memory and performs zero further
tree writes. Automatic motif extraction remains disabled.

Recall no longer limits a shared temporal memory to sources already present in
the initial RGM candidate packet. An explicitly ordered query can open a
reviewed temporal memory even when RGM supplies no candidate. The bridge then
reopens every active bound passage from the lossless RGM corpus and exposes
them separately to the evidence reader and desktop source display. Party and
repayment memories remain candidate-gated. Unknown or reversed event order
does not call the tree and returns no structural source.

The real approved fixture was exercised through the same isolated native worker:
507 branches, 387 terminal branches and 381 learned locations. Each of three
question forms reopened the exact 381-location map, returned both bound source
IDs and left the saved tree unchanged. The complete branch-local signed fields
were compared; there was no branch averaging or whole-tree score. The large
217 MB checkpoint and 2.9 MB reference archive are stored only on Passport at
`native_learned_recall/live_temporal_motif_bridge_v1/`. The 4 KB `result.json`
in the same folder records the checkpoint and field hashes.

The implementation check also exercised the actual answer boundary. With only
one source in the initial RGM packet, the returned app response contained both
exact linked passages under “Evidence linked by the learned structure.”

#### Multiple sources, conflicts and authority

The live reviewed-relationship bridge stores each unique relationship once in
ToM. Further reviewed RGM sources describing the same relationship attach their
exact text and provenance to that existing memory without teaching the matrix
again. One exact distributed return can therefore release several source
locations.

Conflicting sources are not hidden and do not stop the user from seeing an
answer. A source that explicitly negates a relationship or claims to supersede
it cannot be silently attached as confirming evidence. When authority is
unresolved, the app returns an ambiguous result and presents every exact
conflicting and currently bound source with provenance. Neither ToM nor the
language model chooses a winner. An optional explicit user decision can record
that one exact source supersedes specified older sources for one relationship,
with an effective timestamp and reason. This authority record does not change
the tree and keeps the superseded text for audit.

At that stage the bridge was bounded to the reviewed insurance relationships
plus the notice-before-meeting motif and six orthogonal learned addresses. The
later failure/substitute-action/cost-recovery result below adds one further
reviewed structure. General temporal motifs, automatic pattern discovery and
arbitrary event graphs are not product capabilities yet.

#### Distributed-field rule and retained evidence

None of these results collapses the tree response. Native branch identity,
branch order, signed 32×32 matrices, selector scores and slot activations remain
preserved. Selection uses the complete native slot constellation or exact full
field identity, depending on the frozen experiment. Display counts are
telemetry only.

Complete evidence remains outside Git on Passport:

- relationship structural-bridge fields: two approximately 42.7 MB archives in
  `native_learned_recall/rgm500_structural_bridge_v1/`;
- event-order fields: two approximately 58.4 MB archives in
  `native_learned_recall/rgm500_sequence_discrimination_v1/`;
- real cross-source fields: 39,976,817-byte
  `native_learned_recall/rgm500_cross_source_motif_v1/native_fields.npz`,
  SHA-256 `6564acbc4085e3a48acba09ef8ca4d388c4efe0c03946d58b5d3f8fff6f19d8c`.
- live temporal-motif tree and reference: approximately 217 MB under
  `native_learned_recall/live_temporal_motif_bridge_v1/`, with compact hashes in
  the adjacent `result.json`.

The compact, reproducible records are separate immutable sections of
`validation/runs/stream1-native-learned-recall.json`:

- `native_rgm500_structural_bridge`;
- `native_rgm500_structure_parser_diagnosis`;
- `native_rgm500_persisted_situation_bridge`;
- `native_rgm500_persisted_situation_coexistence`;
- `native_rgm500_relational_discrimination_invalid_attempt1`;
- `native_rgm500_relational_discrimination_comparison`;
- `native_rgm500_sequence_discrimination_initial_acceptance`;
- `native_rgm500_sequence_discrimination_comparison`;
- `native_rgm500_cross_source_motif_comparison`.

#### Failures and corrections retained

No failed step is counted as a ToM or RGM result:

1. The first relationship harness compared a raw terminal return with a teaching
   input. Those are different native object types. It produced zero valid matches
   and is retained as `INVALID_OBJECT_COMPARISON`. The valid comparison uses
   like-for-like complete slot maps.
2. The first completed sequence report labelled the result as no gain because
   its acceptance rule expected the final rank-fusion scores to tie. The actual
   native RGM vectors did tie; rank fusion then assigned insertion-order ranks.
   The bad label is retained as `MISCLASSIFIED_BY_ACCEPTANCE_RULE`; the corrected
   run changed only the acceptance logic.
3. The first real cross-source run stopped before the tree because its source
   guard required literal spaces where the native PDF chunk contained a line
   break. Only the guard changed to whitespace-normalized matching; source text,
   chunks, questions and evidence remained unchanged.
4. The first post-run test invocation omitted the repository from Python's
   import path and failed during collection before running a test. The same
   tests were rerun with the correct repository path: 192 passed.
5. Native determinant warnings were observable during tree construction. All
   archived fields were finite, saved-tree restore passed and reads left tree
   state unchanged. The warnings are not described as resolved.

The RGM source repository remained byte- and status-unchanged. The small-tree
checkpoint remained hash-verified and unchanged. The latest bounded result and
runner were committed as `8bf5b4a` on
`codex/rgm-tom-structural-bridge`; pull request 5 contains the complete branch.

### 2026-09-17 — live desktop cross-contract structural recall

The next product check was completed in the real isolated desktop app. The full
documents could not both be admitted to one unchanged RGM project: the lossless
Tom Assist chunker produced 248 M12 chunks and 315 D&C deed chunks, for 563
against the fixed 512-chunk capacity. The test therefore used exact text from
M12 original PDF page 37 and D&C deed original PDF page 327. Each small input
records the original contract path and page. This is a controlled two-passage
product test, not a claim that both complete contracts were loaded together.

The first reviewed passage taught the notice-before-meeting memory at 381 native
locations. The second passage attached to that existing memory with zero new
tree writes. In the actual UI, all three frozen questions showed both exact
contract passages under “Evidence linked by the learned structure”:

| Question | Evidence reader | ToM-linked exact sources |
| --- | --- | --- |
| Which procedures require a written notice, followed by a meeting? | Supported; quoted D&C clause 31 | M12 clause 11 and D&C clause 31 |
| Where does notification happen, then people meet? | Reader declined the broad wording; app reports partial structural evidence | M12 clause 11 and D&C clause 31 |
| Find the sequence notice, meeting, response. | Reader declined the broad wording; app reports partial structural evidence | M12 clause 11 and D&C clause 31 |

A separate live telemetry replay deliberately supplied only one initial RGM
source. For every question, one ToM query route reopened both bound source IDs,
selected both exact passages, preserved every branch/cell coordinate, used no
root assembly or whole-tree score, and left the saved tree unchanged. All three
returns had the same saved-tree state hash
`1df6cd1a2ad54a83cda0f3ad15a67acdab9f91ab434b6f6c4a3917c63c8f0a64`.
The compact record is on Passport at
`native_learned_recall/live_desktop_temporal_motif_v1/live_desktop_result.json`;
the approximately 214 MB tree and 2.9 MB reference field remain beside it and
outside Git.

The run exposed and repaired one evidence-reader integration defect. The reader
selected the correct passage and exact quotation, but copied an 83-character
authenticated source ID as an incorrect 80-character ID. The verifier correctly
rejected the unbound answer. The reader now sees short deterministic source
aliases; the server binds an accepted alias back to the complete authenticated
ID before any answer leaves the gateway. Exact-span and source-integrity checks
remain unchanged. Focused reader tests pass 23/23.

The two broad-wording traces were then inspected directly. In both cases ToM
returned both reviewed source IDs, but the reader itself emitted an explicit
`not_supported` result. The earlier UI consequently made the false stronger
statement that the information was absent. That presentation is repaired: when
reviewed ToM structure exists but the reader cannot verify a complete direct
answer, the app reports **Partly supported answer**, explains that the learned
structure found reviewed passages, and displays every linked exact source. It
does not promote those passages into a model-written answer or claim that every
word in the request was proved. Both broad questions were rerun successfully in
the real desktop with this result.

The final UI review also exposed a stale scope label: the page still displayed
the pre-learning sentence that ToM was not used, even though the answer payload
correctly reported `rgm+tom`. The answer component now refreshes its engine and
scope from each completed answer. The real desktop was rerun and now states that
reviewed structures may reactivate persistent distributed ToM memory before
evidence checking. Desktop tests remain 18/18; typecheck and production build
also pass.

The remaining limitation is the evidence reader's inability to quote a direct
answer for those two broad structural requests. This no longer hides the ToM
result or falsely says the evidence is absent. Automatic motif extraction and
general structural-question wording remain separate validation gates.

### 2026-09-18 — ToM recovers a structural situation that RGM misses

The next diagnostic tested a different relationship rather than extending the
notice-before-meeting result. The reviewed structure was:

```text
required action fails → another party performs it → cost is recovered
```

The exact sources were M12 clause 14.4, where SM's failure allows TfNSW to take
the emergency action at SM's cost, and D&C clause 13.6, where the contractor's
failure allows the Principal to employ others and makes the resulting loss a
debt. An earlier proposed contamination/change-order pairing was rejected before
learning because the clauses did not express the same relationship.

RGM was tested first over a capacity-valid 512-chunk corpus made from all 248
native M12 chunks and the first 264 native D&C chunks. The target passages were
present as M12 chunks 62/64 and D&C chunk 171. Three structure-only questions
returned neither correct passage. The result therefore identified a real RGM
gap rather than assuming that ToM would help.

The reviewed bridge now admits this one additional event chain. It stores the
chain as two distinct ordered memories—failure before substitute action, then
substitute action before cost recovery. Each relationship routes independently
through ToM. Their complete native branch-position-preserving signed 32×32
fields and exact slot maps must both match. They are never averaged or combined
into a whole-tree score. The final source set is the intersection of the exact
sources bound to both returned relationships.

On the real approved small tree, the first source created both distributed
memories with 780 total native writes. The resulting saved tree had 520 branches
and 399 terminal branches. The second contract source bound to the same two
memories with zero new tree writes. The two learned return fields were:

- `de26a5ce700c23b12e8adc3a88476c5ef769c120edd5ebd20a45f75cf6a0afc8`;
- `abea835beb76600be379c270ad9284dad07af6b18ff65a9c56575cb24028b5f1`.

All three frozen wording variants produced exact matches to both fields and both
native slot maps. In the live answer path, both reviewed source locations were
reopened and the evidence reader selected and quoted the D&C clause 13.6 passage
that directly states failure, substitute performance and debt. The answer kept
both M12 and D&C passages visible as structural sources.

The decisive control then supplied **zero RGM candidates** to the real recall
path. For every wording, ToM still returned both reviewed source IDs, reopened
both exact RGM passages, preserved every branch/cell coordinate, used two query
routes and no root assembly or whole-tree score, and left state
`bc634d0071db4b296c58b50d6bc2b6da0979ef46bdc327b9f5e3fcb0d2740386`
unchanged. This demonstrates the complementary role directly: RGM retains exact
text and provenance; ToM can recognize a learned cross-document situation and
recover the RGM source locations when ordinary RGM retrieval supplies none.

This remains a reviewed, bounded capability. The app does not yet discover the
motif automatically or accept arbitrary event chains. The large tree and field
archive remain on Passport under
`native_learned_recall/live_desktop_temporal_motif_v1/`; no large artifact was
added to Git.

#### Clause-local source recognition diagnostic

The next diagnostic scanned every one of the 248 M12 and 315 D&C native RGM
chunks before changing the learning path. The original narrow phrase guard
admitted five passages. Manual inspection confirmed that all five expressed the
reviewed failure → substitute action → cost-recovery structure, but the guard
missed seven other clear instances. The missed drafting forms included one
party effecting insurance for another, corrective work being carried out by
others, direct protective action and incident response.

A broad whole-chunk keyword rule was rejected. It combined a failure in one
clause with an unrelated action or debt elsewhere in the same chunk. The source
guard now requires the three events to form one local procedure. It explicitly
handles three observed legal drafting layouts: ordinary failure/action/cost
order; cost allocation immediately before the substitute action; and a clause
that first grants the substitute action and then describes the omitted duty.
It does not combine event phrases separated by more than 1,200 source
characters.

The revised guard found exactly 12 candidate passages in the unchanged
563-chunk corpus: M12 chunks 62, 64, 78 and 80, plus D&C chunks 171, 194, 195,
205, 261, 263, 265 and 303. Every match was inspected and contains the complete
procedure. Nearby clauses containing failure and debt but no substitute
performance were rejected, as was a deliberately separated three-phrase
control. Existing learned-memory receipts retain their original event offsets,
and the live project loaded all four older bridge records unchanged.

This change improves the exact-source admission check only. It does not alter
the tree, automatically teach detected passages or collapse a distributed ToM
return. The relevant gateway suite passes 251 tests.

#### Explicit review queue for detected structures

The Memory screen now has a **Structures to review** action. It scans only the
active authenticated RGM chunks and lists each locally complete
failure/substitute-action/cost-recovery candidate with its exact passage and
the three phrases that triggered the candidate. Scanning is read-only: it makes
zero tree calls and cannot teach a memory. Each passage has its own explicit
Save action; the gateway repeats the source-local validation before it writes or
binds any ToM memory.

The integration diagnostic exposed a separate storage problem before the user
interface was wired: a source passage was keyed only by source identity, so it
could hold either its reviewed insurance relationship or its reviewed event
chain, but not both. Reviewed records are now keyed by source identity plus the
reviewed structure identity. A controlled check stored both structure types
from one exact passage as separate records and retained four distinct ToM
relationships. A second, conflicting set of party roles for that same source is
still rejected.

On the live project the read-only scan inspected four active chunks and returned
the two expected passages. Both were correctly marked as already reviewed. It
reported zero tree calls and no automatic learning. The full relevant gateway
suite passes 252 tests; the desktop suite passes 19 tests, TypeScript checking
passes, and the production interface build passes.

A final live Save check imported the exact D&C clause 16.7 chunk that had been
inspected during the diagnostic. The queue first marked it unreviewed and showed
the three matched phrases: `but does not take`, `take any action necessary` and
`debt due`. The explicit Save action created zero tree writes and bound the new
source to the two existing ordered ToM memories. The learned relationship count
remained 3, the reviewed source count increased from 4 to 5, and both the tree
state hash and checkpoint hash remained exactly unchanged. A second scan marked
the passage reviewed and again reported zero tree calls and no automatic
learning.

The new binding was then tested with an empty RGM candidate packet. The unchanged
ToM tree returned all three reviewed source locations—M12 clause 14.4, D&C
clause 13.6 and the newly linked D&C clause 16.7—through the two independent
ordered query routes. All native branch/cell coordinates were compared, no
whole-tree score was used, and the tree remained unchanged. This confirms that
the review queue adds usable source provenance to the existing distributed
structure rather than merely changing an interface label.

#### Multi-source evidence completeness repair

The next end-to-end run used that unchanged three-source memory. It first found
a persistence compatibility defect before recall: version 5 permits a reviewed
source to bind to existing ToM memories with zero new memory records, but the
current loader's zero-write allow-list accidentally omitted version 5. Adding
that existing version to the allow-list restored the saved project without
altering its database or tree.

With the project readable, the broad debt wording showed the actual integration
loss. ToM reopened all three source locations through two independent routes,
preserved every branch-local signed 32×32 coordinate and left tree state
`bc634d0071db4b296c58b50d6bc2b6da0979ef46bdc327b9f5e3fcb0d2740386`
unchanged. The evidence reader received the three passages together and kept
only D&C clause 13.6. The query structure was also missing from the aggregated
two-route return, preventing the answer layer from identifying this bounded
chain.

The repair preserves the multi-route query structure and, only for the exact
reviewed failure → substitute action → cost-recovery chain, checks every
ToM-returned RGM passage independently. The same debt wording now returns D&C
clauses 13.6 and 16.7; it correctly excludes M12 clause 14.4 because that source
says `at the cost of SM` rather than `debt`. Changing only the wording to ask
about cost recovery returns all three clauses. No ranking, tree threshold,
learned state, branch identity or 32×32 cell was changed. The native-memory test
file passes 169 tests.

### 2026-09-18 — unseen Noise and Vibration plan generalisation

The next check changed only the document source. It used the previously unused
`Noise and Vibration CEMP.pdf`, SHA-256
`40e92ef553e75a9f37ed0159a5b326d2d1cc9a87668c86382e71b0ed8631c967`.
The unchanged RGM extractor produced 205 chunks. Chunk 172 contains the source
phrase `notification of any upcoming project community meetings / forums`, a
third reviewed example of notice before a meeting.

The first attempt stopped before any tree call. The bounded source grammar
accepted `meeting` but not the ordinary plural `meetings`. The same omission
existed in the query grammar. The repair added only that plural form to the four
matching locations and added a focused regression check. It did not change the
learned matrix, routing, selector or tree.

The repaired diagnostic used an isolated SQLite backup of the live project.
The live database was not written. Across three fixed wording variants, ordinary
RGM considered 210 native candidates and did not return the new source in any
top-10 packet. The returned packet sizes were 7, 8 and 10.

Explicitly reviewing the new source bound it to the existing notice-before-
meeting memory with zero tree writes. The memory then owned three exact source
locations. Before the access repair, ToM recovered all three locations for two
questions where RGM happened to return an older bound source. The third question
and all empty-packet controls stopped at `no_candidate_situation`. Telemetry
therefore located the remaining problem in the access gate, before the tree.

The failure/substitute-action/cost path already allowed an explicit ordered
query to access its reviewed memory without an initial RGM candidate. That same
rule now applies to all admitted `before` relationships. Party and repayment
relationships remain candidate-gated. After this one-variable change:

- RGM alone missed the new source in **3/3** questions;
- RGM plus ToM returned all three reviewed notice sources in **3/3**;
- an empty RGM candidate packet also returned all three sources in **3/3**;
- every ToM return preserved complete branch-local signed 32×32 fields and
  exact native slot maps; and
- no branch averaging or whole-tree score was used.

The 242,504,340-byte saved tree had SHA-256
`323a40e31a9b56b9c06d8ea22a9a6ef14c5263953f9bfa6349e4d1db4a5341fd`
and state hash
`bc634d0071db4b296c58b50d6bc2b6da0979ef46bdc327b9f5e3fcb0d2740386`
before and after the run. Its size, modification time, file hash and state hash
were unchanged.

This is a bounded third-document result, not general event understanding. The
source still required explicit review, and only the previously learned
notice-before-meeting structure was exercised. The compact result is
`validation/runs/rgm-tom-unseen-document-generalisation.json`; no new large
artifact was created.

The complete native-memory file passes 144/144 after the repair, including an
explicit control that party/repayment relationships remain candidate-gated.
The broader sandboxed gateway run completed with 590 passes, one expected skip,
one unrelated pre-existing event-graph fixture-overlap failure and five OAuth
setup errors caused by denied local socket binding. The OAuth file was rerun
outside that socket restriction and passed 8/8.

### 2026-09-18 — Middleton event-order generalisation

The next diagnostic changed both project family and reviewed structure. It used
`Appendix C - Mitigation Measures.pdf` from the Middleton planning submission,
SHA-256
`7e31e674bd1f9f36a20ef81cf6485c8a7e48091a70a942c38f9f0daaac9c9c3a`.
The unchanged RGM extractor produced three chunks. Chunk 2 contains a local
procedure in which clearly identifiable human remains are uncovered, nearby
work immediately stops, the find is secured, and Police and Heritage NSW are
notified.

The baseline isolated database contained six documents and eight native RGM
chunks. RGM returned the target for both correct structural questions, but it
also returned it at rank 1 for the reversed notification-before-stop question
and rank 2 for the false continue-excavation question. This showed that RGM had
good access to the topic while leaving the event order and stop/continue state
unresolved.

One bounded source grammar and two event relations were then added:

```text
human_remains_discovered → stop_work → notify_authorities
```

The source guard requires those three events to occur locally in that order. A
reversed-source control is rejected. Query parsing admits either the explicit
stop-work-before-notification pair or the complete three-event chain. Reversed
order is represented as a different relationship and is rejected before a tree
call; a continue-work question contains no admitted structure.

A fresh copy of the approved small Stream 1 fixture learned the two relations.
The resulting tree had 513 branches and 393 terminal return branches. The
correct pair recalled the exact RGM source through one route, and the complete
chain recalled it through two independent routes. The reversed and absent
controls returned no structural source. The topic-only question remained an
RGM question because it did not state an ordered relationship.

Every successful route compared the complete signed branch-local 32×32 field
and exact native slot map. There was no whole-tree score or branch averaging.
The 233,213,726-byte checkpoint had SHA-256
`9eb96cf72ed2a413fba3f37e2097f773cb6e87d2490e589d95919376c9b1bc13`
and state hash
`d8b66790c29315149b90eea188c84aed1d37e0259f57f496b1f74a4aa6b7b750`
before and after recall. The 6,091,380-byte full-field archive also retained its
SHA-256
`b149755816c7ee5e9b42e4b95093b9bd0ced1217083dbd7fdb56457e7a93ecd8`.

The large checkpoint and field archive are stored only under
`/Volumes/My Passport for Mac/tom_assist_test_results/native_learned_recall/middleton_human_remains_v1/`.
The compact result is
`validation/runs/rgm-tom-middleton-sequence-generalisation.json`. Temporary
diagnostic databases were deleted. The native-memory suite passes 146/146.

This remains a bounded test of one explicitly reviewed procedure. It does not
show automatic structure discovery, arbitrary event-graph parsing or general
accuracy across planning documents. At that recorded stage, the desktop review
queue did not yet offer this new structure; the next section records its
addition and the live-answer check.

### 2026-09-18 — Middleton desktop review and live answer boundary

The desktop **Structures to review** queue now scans the bounded human-remains
procedure as well as the existing failure/substitute-action/cost procedure. It
shows the exact passage and the three matched events. Scanning remains
read-only: it makes zero tree calls and cannot teach automatically. Only the
existing explicit Save action can review and learn or bind the source.

The first production-path answer run failed. The correct-order question used
the complete distributed ToM return and produced the exact source. ToM also
correctly rejected the reversed notification-before-stop relationship and the
absent continue-excavation relationship. The final evidence reader nevertheless
treated the topically relevant RGM passage as support for both bad questions.
This located the fault after structural recall: the answer boundary ignored
ToM's structural rejection and fell back to semantic evidence.

The repair changes only that boundary. When a question states the exact reverse
of, or a state explicitly opposed by, one reviewed relationship, Tom Assist
reopens the exact RGM source for that relationship and gives a sourced No. It
does not call the language reader or route the tree for that negative result.
Conflicting sources are unaffected and remain visible together.

The repaired run produced:

- correct order: `supported`, one real distributed ToM recall, exact chunk 2;
- notification before stopping: `not_supported`, exact chunk 2 shown, zero
  language-model calls and zero tree calls; and
- continue excavation after discovery: `not_supported`, exact chunk 2 shown,
  zero language-model calls and zero tree calls.

The correct answer quoted the procedure requiring all work near the find to
stop immediately, the area to be cordoned off, and the manager to notify NSW
Police and Heritage NSW. The reversed answer states that the reviewed source
records the opposite order. The absent-state answer states that the procedure
requires work to stop and does not require excavation to continue.

The 513-branch tree and its complete signed branch-local 32x32 return were not
collapsed or averaged. The checkpoint remained 233,213,726 bytes with SHA-256
`16417dfebb261f50331e9389e9a105677aaeb4a82354e35d22590bd57d19165e`
and state hash
`d8b66790c29315149b90eea188c84aed1d37e0259f57f496b1f74a4aa6b7b750`.
The 6,091,380-byte full-field reference retained SHA-256
`b149755816c7ee5e9b42e4b95093b9bd0ced1217083dbd7fdb56457e7a93ecd8`.
Large artifacts are on Passport under
`/Volumes/My Passport for Mac/tom_assist_test_results/native_learned_recall/middleton_human_remains_e2e_v1/`.
The compact result is
`validation/runs/rgm-tom-middleton-live-answer.json`; its temporary database was
deleted.

Verification passes all 147 native-memory tests and all 20 desktop tests.
TypeScript checking and the production desktop interface build also pass.

### 2026-09-18 — second human-remains source without a duplicate memory

The next check changed only the source wording. It used `Appendix AB -
Aboriginal Cultural Heritage Assessment.pdf`, SHA-256
`11929bf098a5684884871fddd969fefe0aeab23d81e23dc23c700b4774e04421`.
The existing RGM path produced 42 chunks. The procedure says suspected human
remains are discovered, personnel must `immediately cease all works`, secure
the area, and notify NSW Police and Heritage NSW.

The first read-only scan returned zero candidates. No tree call occurred. The
diagnosis was exact: the bounded source grammar accepted `stop work` but did
not accept `cease all works`. The repair added only that stop-work wording. It
did not change the motif, tree, routes, selector or question grammar.

The unchanged document then produced two valid queue candidates: its summary
at RGM chunk 1 and its main recommendation at chunk 39. The main recommendation
was explicitly reviewed. Appendix C had already written the two learned event
relationships; Appendix AB bound to those same relationships with:

- **0** new tree writes;
- **2** existing relationship bindings; and
- **2** learned relationship memories in total.

An actual two-route ToM recall with an empty RGM candidate packet reopened both
exact passages: Appendix C chunk 2 and Appendix AB chunk 39. It compared every
native branch/cell coordinate and used no whole-tree score. The 513-branch
checkpoint, 393 terminal branches, complete reference fields, file sizes,
hashes, modification times and tree state hash were identical before binding,
after binding and after recall.

The temporary duplicate checkpoint and temporary database were deleted. The
compact evidence is retained in the `shared_source_binding` section of
`validation/runs/rgm-tom-middleton-live-answer.json`. The native-memory suite
now passes 148/148.

### 2026-09-18 — RGM semantic and vector sweep integration repair

The next diagnosis found an integration gap in that review queue. The copied
RGM machinery already implemented two vector candidate passes and Reciprocal
Rank Fusion, but the queue never called it. It ran only the final regex scan.
The semantic sweep was therefore absent from structure discovery even though
RGM itself supported it.

The repaired queue now runs four bounded structure queries through the copied
RGM retrieval path. For every query it runs the contextual vector pass, the
native RGM vector-store pass and Reciprocal Rank Fusion. Independently, it runs
the regex rules across every active source chunk. The two result sets are
joined, but a passage appears in the review queue only if the exact local
events are present in the required order. A semantic or vector hit alone cannot
authorize a candidate or teach ToM.

The unchanged 42-chunk Appendix AB document verified the repaired path. RGM's
native vector pass ranked the two human-remains passages at ranks 2 and 1. Rank
fusion placed them at ranks 1 and 4. The contextual vector pass found the
summary passage at rank 4 and did not place the main recommendation in its top
ten. The independent regex/order pass found both, so both became validated
review candidates. Eleven other semantic source hits, representing twelve
source-and-structure pairings, were rejected by the strict local check.

A separate control passage contained related words but no ordered procedure.
It entered the semantic candidate set and was rejected: zero regex candidates
and zero review candidates. The complete review made zero tree calls and no
automatic learning. The Memory screen now shows the discovery channels and
ranks for each candidate. Verification passes all 149 native-memory tests and
all 20 desktop tests; TypeScript checking passes.

### 2026-09-18 — read-only review accuracy check

The repaired discovery path was then checked against the complete production
ingestion of four real PDFs. The positive labels were the passages previously
inspected by hand: four M12 procedures, eight D&C Deed procedures and three
Middleton human-remains procedures. The production RGM file reader and chunker
produced 248 M12 chunks, 315 D&C chunks and 48 Middleton chunks, for 611 real
chunks in total.

The first harness attempt used `pdftotext -layout`. It produced incompatible
contract corpora of 198 and 393 chunks, so its accuracy calculation was invalid
and discarded. The final run used the same `source_path` import route as the
desktop app. Under that reader, the known Appendix AB main recommendation is
chunk 41 rather than chunk 39. Its exact discovery, cease-work and authority-
notification wording was verified before the final score was calculated.

The final read-only result was:

- M12: **4/4** known valid passages, zero extras;
- D&C Deed: **8/8** known valid passages, zero extras;
- Middleton: **3/3** known valid passages, zero extras; and
- combined: **15/15**, with zero false positives and zero false negatives in
  this bounded labelled set.

The channel telemetry explains why the combined design matters. Of the 15
validated passages, the final semantic return contained 7, the contextual
vector top ten contained 7, the native RGM vector top ten contained 8, and
Reciprocal Rank Fusion contained 9. The independent full-source regex/order
check recovered and validated all 15.

Four negative controls were also run: topic-only wording, reversed event order,
an incomplete procedure and the three event phrases separated beyond the local
limit. RGM returned all four semantically, while the regex/order validator
rejected all four. No review candidate was produced. The complete diagnostic
made zero tree calls, performed no automatic learning and deleted its temporary
databases. The compact result is in `review_accuracy_check` inside
`validation/runs/rgm-tom-middleton-live-answer.json`. The four controls are now
permanent regression cases; all 152 native-memory tests pass.

### 2026-09-18 — temporal source-conflict presentation

The next diagnostic held the reviewed tree memory fixed and added one retrieved
RGM source that stated an opposing human-remains procedure. The first run
failed: Tom Assist returned a sourced **No** from the reviewed stop-then-notify
procedure and omitted the retrieved source that said notify before stopping.
The cause was precise. The reviewed-structure contradiction shortcut ran before
the answer path checked RGM passages for exact opposing temporal evidence.

The bounded answer path now performs that source check first. It recognises two
oppositions to the reviewed discovery → stop work → notify sequence:

1. discovery → notify authorities → stop work; and
2. discovery → continue work.

For either opposition, Tom Assist returns **Ambiguous** and shows the reviewed
source and every exact conflicting retrieved source with provenance. It does
not choose a winner, call the tree, call the language reader or alter learned
memory. At this stage temporal authority recording remained unavailable, so an
operator could not apply the party-relationship authority action to event
order. The later temporal-authority change below closes that bounded gap.

Three controlled paths now pass: a question phrased in the reversed order, a
question phrased in the reviewed order, and a continue-work question. Each
returns both exact sources. The production-ingestion regression was then rerun
over the same 611 real chunks and remained 15 true positives, zero false
positives and zero false negatives, with zero tree calls and no automatic
learning. All 155 native-memory tests pass. Compact evidence is stored in the
`temporal_source_conflict` section of
`validation/runs/rgm-tom-middleton-live-answer.json`.

### 2026-09-18 — real-document temporal conflict

The controlled conflict repair was then tested against real document ingestion.
The local document screen first examined 17 likely heritage, environmental and
planning PDFs with the production RGM reader. Six files contained the admitted
human-remains procedure, and all six said stop work before notification. That
collection therefore contained no genuine opposing source and was not presented
as a conflict result.

A public Northern Midlands Council planning attachment supplied a genuine
opposite sequence. Its Palmerston Battery heritage procedure says:

```text
discovery of skeletal material
    → call Police immediately
    → notify workers that earth-disturbance work must cease
```

The first production-reader diagnostic failed to recognise that passage. The
extraction was correct; the bounded parser admitted `human remains`, `notify`
and `stop work`, but not the source's `skeletal material`, `call Police` and
`works cease`. Only those verified wording variants were added. The required
event order and 1,200-character source-local limit were unchanged.

The full gateway check then ingested the three-chunk Middleton PDF and the
136-chunk Northern Midlands PDF, encoded them with the configured MiniLM and ran
the copied RGM retrieval. RGM returned Middleton chunk 2 and Northern Midlands
chunk 63. Tom Assist returned **Ambiguous** and displayed both exact passages
with provenance. The answer made zero tree calls, zero language-reader calls
and no whole-tree score. Temporal authority remained unavailable during this
real-document diagnostic.

These documents concern different projects and jurisdictions. The result proves
that real opposing source text remains visible; it does not say the documents
govern the same work or decide which is legally controlling. The downloaded
3.2 MB diagnostic PDF and temporary database were deleted after hashes and the
official source URL were recorded. No large artifact was created.

The expanded wording was checked against the unchanged 611-chunk production
set: 15 true positives, zero false positives and zero false negatives, with no
tree calls or automatic learning. All 157 native-memory tests pass. Compact
evidence is in `real_document_temporal_conflict` inside
`validation/runs/rgm-tom-middleton-live-answer.json`.

### 2026-09-18 — explicit temporal source authority

The next change added a user-controlled decision for the bounded human-remains
conflict. It does not treat every `before` relationship as the same thing. Each
record is tied to the exact discovery → stop work → notify-authorities motif,
the exact retained passage identities and text hashes, an effective time, and
the user's reason.

The app displays both sides in the authority form. The user may choose either
the reviewed stop-then-notify passage or the conflicting notify-then-stop
passage as controlling, then identify the passage it replaces. Before the
record's effective time, the answer remains **Ambiguous** and shows both
sources. From the effective time onward, only the chosen exact passage reaches
evidence checking. The superseded text stays in the RGM library and the ToM
tree is neither called nor changed.

Two controlled end-to-end cases exercised both possible choices. Both rejected
a generic `before` scope, rejected a reverse link that would create a cycle,
kept both sources visible before the effective time, and selected only the
chosen source afterward. The gateway suite passes **159** checks. The desktop
suite passes **21** checks and confirms the exact motif scope is returned to the
gateway. This proves the bounded authority mechanism; it does not decide which
of the two real documents governs a project.

### 2026-09-18 — same-project revision control

The first real same-project check compared two genuine versions of the SCAW
Aboriginal Cultural Heritage Construction Environmental Management Plan: the
November 2021 contract copy and the official June 2023 Revision 06. The source
texts were inspected before any authority test. Both versions say that work
ceases first and authorities are notified afterward. They are different PDF
and extracted-text hashes, but they do not contain competing procedures.

Both complete PDFs were then run through the production RGM extraction,
chunking, MiniLM semantic sweeps, native vector sweep, contextual vector sweep,
Reciprocal Rank Fusion and full-source regex/order check. The documents produced
367 and 106 chunks. The correct passage in each version was found by every
discovery channel and admitted as the same discovery → stop work → notify
authorities motif. Twenty-one semantic source/motif hits failed the strict local
check and were rejected.

The result is a passed negative control: Tom Assist made zero tree calls,
performed no automatic learning and did not invent a conflict from the later
revision number or date. It is not a successful real authority-resolution
test, because the sources agree. That gate still requires two genuine versions
from one project that actually state different procedures.

### 2026-09-18 — read-only source-authority history

The Memory screen now shows every recorded source-authority decision from the
selected project's verified library. Each entry displays the bounded scope, the
exact controlling passage, every exact replaced passage, source/chunk
provenance, the effective time, the user's reason and an Active or Future
status. Separate user actions remain separate entries; several replacements
recorded in one action are grouped together.

The server checks the retained record content, hashes, source bindings and cycle
constraints before returning the history. The view is read-only, makes zero
tree calls and cannot edit or revoke a decision. Superseded source text remains
available for audit.

### 2026-09-18 — real same-project remediation-plan revision

A second same-project revision pair supplied the missing genuine state change.
Revision 04 of the SCAW SMF Final Package says the contaminated-soil Remediation
Action Plan is a draft under site-auditor review and that the approved plan will
be attached to a future submission. Revision 05 removes that draft statement,
identifies revised plan `SMWSASCA-CPU-1NL-NL000-CT-RPT-000028`, and says it is
attached in Appendix M. The PDF and extracted-text hashes differ and were
recorded for both sources.

The first production import stopped before embedding because the two reports
produced 2,201 RGM chunks, above the then-current 512-chunk collection bound.
No source was pruned. A shadow run changed only the request-local RGM capacity
to 4,096 and successfully admitted and searched all 2,201 chunks. The product
bound and request-local RGM capacity were then changed together to 4,096, with
collections above that size still rejected before model work. The document
cache version was advanced so earlier vectors cannot be silently reused under
the new collection contract.

The updated production retrieval returned the real revision-history evidence.
For the direct draft-status question, Revision 05 chunk 74 ranked first,
Revision 04 chunk 71 ranked second and Revision 05 chunk 79 ranked third; all
three were present in the final ten-source packet. The other two questions also
returned the relevant short revision passages at the top. The complete Section
4.3.4 source chunks ranked 78/89, 95/102 and 527/786, so the semantic and vector
sweeps succeeded through the concise change-history evidence rather than the
long clauses.

This test used production PDF extraction, production RGM chunking, the frozen
MiniLM encoder, the copied RGM native and contextual vector passes, Reciprocal
Rank Fusion and the final RGM packet. It made zero ToM tree calls, performed no
automatic learning and deleted the temporary database. It proves that the RGM
integration can retrieve a genuine version change from the full pair. The next
gap is explicit: the current source-authority scopes cannot yet represent this
plan-status claim, so the app has not yet proved that it will show both versions
and apply a user-recorded controlling-source decision for this case.

### 2026-09-18 — bounded remediation-plan source authority

That exact gap was then closed without changing retrieval or the ToM tree. The
answer path recognises only the contaminated-soil Remediation Action Plan status
family and classifies exact retrieved passages as either draft-under-review or
revised-attached. It prefers the concise change notes and an opposing source
from another retained document. This made the selected pair stable across the
three fixed questions: Revision 05 chunk 74 and Revision 04 chunk 71.

Before any decision, the live path returned **Ambiguous**, displayed both exact
passages and enabled the existing source-authority form. Conflict presentation
made zero language-model calls and zero ToM calls. A temporary real-project
decision then marked Revision 05 chunk 74 as controlling with an effective time
and reason. The same question remained ambiguous immediately before that time.
At the effective time, the authority filter supplied only chunk 74 to a
deterministic exact-quote reader, which returned supported evidence. The
read-only authority history showed the controlling and replaced passages.

Two controlled cases also chose each side in turn, rejected a reverse cycle and
kept future decisions inactive. The desktop displays the source-claim scope and
passes it back unchanged. This is a bounded plan-status capability, not a
general amendment or legal-authority detector. Authority is still never
inferred from dates, filenames or revision labels.

Verification passes all 162 native-memory tests and all 22 desktop tests,
including TypeScript checking and the production build. The broader gateway
run reports 608 passes and one skip, with the unchanged unrelated event-graph
fixture-overlap failure and five sandbox-only Unix-socket setup errors. The
complete OAuth socket module passes 8/8 with local socket binding available.

### 2026-09-18 — second real source-change family

The second family tested the `For Review` watermark across the same complete
Revision 04 and Revision 05 SCAW reports. The production RGM path again searched
all 2,201 chunks. Revision 05 chunk 72 explicitly states that the watermark on
the previous Revision 04 Issued for Review submission was removed. That exact
change note ranked 1, 6 and 1 for three differently worded questions.

This diagnostic did not reproduce the remediation-plan conflict. The later
passage itself records both the historical state and the transition. The older
document does not yield one stable opposing passage: the words `for review`
also occur in issue history, review sheets and ordinary review instructions.
Treating one such old chunk as the controlling opposite would be arbitrary.

The production local reader was then run on the direct question, “Does Revision
05 still carry the For Review watermark from Revision 04?” It returned
**Supported** and quoted the removal statement from Revision 05 chunk 72 with
the exact file and chunk provenance. Peak local model allocation was
15,138,471,706 bytes. The run made zero ToM calls, no training calls, no
whole-tree score and no authority record, and deleted its temporary database.

The architectural result is that explicit historical change evidence should
go straight to evidence reading. Source authority remains for genuine
unresolved disagreements. No classifier, threshold or tree behaviour was
changed for this result.

### 2026-09-18 — one learned contamination situation, two exact sources

The next comparison focused on a place where ToM can add something the RGM
reader did not provide by itself. The production RGM path searched the complete
executed SCAW D&C Deed and M12 Interface Agreement: 315 plus 248 chunks. It
found D&C chunk 156 and Interface Agreement chunk 66 as the only passages that
passed the local contamination-discovery then notification check.

The specific RGM answers were already correct. The broad question, “What
notifications are required when contamination is discovered?”, also retrieved
both passages in its final ten candidates, but the evidence reader returned only
the Interface Agreement clause. The failure was therefore broad-answer
completeness after retrieval, not a semantic-search miss.

One reviewed structure was added:

```text
contamination discovered → notification
```

The first real clause wrote to 381 native locations in the approved small tree.
The second clause bound its exact source pointer to that same relationship and
made zero additional tree writes. Three questions then reopened both source
pointers through the same exact native return. The field shape was 387 terminal
branches × 32 × 32 cells. Branch identity, native position, sign, magnitude and
exact memory-slot map were preserved. There was no averaging and no whole-tree
score.

The first end-to-end attempt exposed an integration defect: the service returned
the native field but dropped the parsed query structure, so the multi-source
reader did not know to evaluate each linked source separately. The deed-specific
question was blocked and the broad question again showed only one source. The
query structure is now preserved beside the native return, and each linked
source is evaluated independently for this admitted motif. Both specific
questions then returned exactly their own applicable clause.

The broad replay exposed a second, narrower failure. The reader correctly found
the deed obligation, but its proposed quote skipped the PDF page header embedded
inside that one clause. The exact-span guard rejected the altered span. The
broad evidence check now returns one contiguous exact source provision from the
already validated local relationship, including intervening page furniture. A
follow-up diagnostic caught and repaired a sentence-boundary error that stopped
at the decimal point in `12.20`; numeric clause-reference dots are now ignored.

The final real run returned **Supported** with both exact provisions and their
file/chunk provenance. Specific D&C and Interface Agreement questions each
returned one applicable source. The tree remained unchanged during all queries,
and training occurred only during the explicit reviewed Save. All 167
native-memory checks pass.

Large artifacts are stored only on Passport at
`native_learned_recall/scaw-contam-notice-20260918/`: a 224,060,581-byte tree
checkpoint and a 3,024,219-byte complete-field reference archive. The owner
repositories remained read-only.
