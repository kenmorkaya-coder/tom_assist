# Tom gateway

## Native matrix memory → permanent evidence boundary (experimental)

`NativeEvidenceLibrary` in `native_memory.py` reuses `PermanentLibrary` for
immutable evidence records. It does not import the older RGM tree addressing,
add a scorer, replace RGM admission gates, or change the production answer path.
Every reference retains its ordered branch IDs and complete signed 32×32
matrices. Matching uses coordinate-by-coordinate equality; hashes authenticate
the saved reference and evidence link, not semantic similarity. Pinned binding
receipts reject modified sources, mismatched trees and exchanged links. Missing
or ambiguous matches return no evidence. Recalled evidence is not an approved
answer.

The `--rgm500-bridge teach|verify` stages in the existing native learned-recall
calibration runner exercise this boundary from the approved clean 500-branch
Stream 1 checkpoint. Two native exposures grow the experimental copy to 513
branches; two consequences then teach it without further growth. Capture keeps
all 513 routed input matrices and all 393 native memory-bank return matrices,
before combination. A separate process restores the learned tree and a reopened
evidence database. Both canonical matrix inputs recover their associated source;
untrained, branch-permuted and sign-reversed controls recover none. Exchanged
binding receipts are rejected. These identity controls do not establish semantic
or topology causality.

This is a mechanical storage-boundary test with synthetic source labels attached
to pre-existing matrix associations. It is **not** a paraphrase test, a natural
language understanding result, or evidence of improvement over RGM alone.
The original checkpoint is unchanged. Peak process memory was 1.13 GiB; the
233 MB learned checkpoint and 34 MB full-field archive remain under
`/Volumes/My Passport for Mac/tom_assist_test_results/native_learned_recall/rgm500_bridge_v1/`.
Compact evidence is the `native_rgm500_evidence_bridge` section of
`validation/runs/stream1-native-learned-recall.json`. Native determinant warnings
were observed; fields were finite and restore validation passed, but the warnings
have not been diagnosed. The focused native-memory suite passed 27 checks.

The subsequent `--rgm500-comparison baseline|native` diagnostic added the native
bridge to the same ordinary RGM candidates for four questions over the two
reversed synthetic sources. Both arms put the correct record first in 4/4
original questions; adding the tree changed no candidate or ordering. The RGM
tokenizer retains punctuation, so a separate `punctuation-baseline|punctuation-native`
control removed only each question's final full stop. All four then tied in RGM.
Both arms put the correct source first in 2/4, entirely subject to insertion
order; reversing insertion changed the first result in 4/4. Both sources remained
available in every case. The native arm reproduced 16/16 complete reference
fields across the two runs but resolved zero ties. No training, LLM, MiniLM,
new matrix score, or production route change occurred.

This diagnoses the current canonical-input bridge: RGM picks candidates, then
ToM receives each candidate's teaching matrix rather than the original question.
It validates learned returns without adding a question-dependent distinction.
It does not establish a limitation of question-driven tree recall or assess the
older system's complete contextual chat/branch-event pipeline. Results are kept
separately as `native_rgm500_access_comparison` and
`native_rgm500_access_punctuation_control` in the same compact master report.

The follow-up `--rgm500-structural-bridge forward|reverse` test passes the
question itself to the approved circa-500 native tree as a position-sensitive
event matrix. It uses the real RGM chunks for clauses 23.5 and 24.5 and their
retained source provenance. Their verified failure-party and cover-payer roles
are reversed, so this checks direction rather than punctuation or general topic.
The clauses write to 381 and 387 distinct native branch/slot locations with zero
overlap. All four held-out questions activate every location belonging to the
correct clause and zero locations belonging to the reversed clause. Reversing
the teaching order repeats the result: eight correct-only activations across the
two orders and no reversed activation. The same frozen RGM baseline ranks the
correct chunk first for three of the four questions.

This result preserves native branch order, every routed signed 32×32 input,
every terminal signed 32×32 return, and the uncollapsed per-slot selector fields.
No whole-tree score is calculated. The two complete archives are about 42.7 MB
each and remain under
`/Volumes/My Passport for Mac/tom_assist_test_results/native_learned_recall/rgm500_structural_bridge_v1/`.
Peak process memory was 1.22 GiB. The compact result is
`native_rgm500_structural_bridge` in the existing master report. Native
determinant warnings remain observable; all retained fields were finite and the
tree state was unchanged by reads.

The bounded `--rgm500-relational-discrimination` comparison then exercised the
full RGM contextual retrieval entry point over those same two real clauses and
four questions. Both source records remained available in all eight trials
(four questions across both source/teaching orders). RGM put the correct source
first in 6/8 trials. Adding only the exact, branch-position-preserving ToM
memory-slot activation map selected the correct relationship in 8/8 and repaired
both reversed-direction misses. RGM candidates, source text and provenance did
not change; there was no new tree run, training, model call, branch averaging or
whole-tree score. Complete signed terminal fields remain retained as evidence,
but are not compared with teaching-input fields because those are different
native object types. The first harness attempt made that invalid comparison and
is retained explicitly as `INVALID_OBJECT_COMPARISON`; it is not counted as a
ToM failure.

This is the first direct evidence of the intended division of labour: RGM finds
and preserves the exact plausible records, while ToM can disambiguate a learned
relationship direction that RGM's document/context ranking gets wrong. The test
is still limited to two reviewed mirrored relationships. It does not establish
automatic relationship extraction, a broad accuracy gain, or superiority over
every historical RGM branch-event experiment.

The next `--rgm500-sequence-discrimination` test isolates event order. Two
controlled records contain exactly the same entities, actions and native-RGM
word vector; only the event sequence changes. Across four unseen phrasings and
both record/teaching orders, RGM retained both records in 8/8 trials. Its native
vectors tied, so rank fusion followed insertion order in 8/8 and changed the
first result for all four questions when insertion was reversed. RGM therefore
put the correct sequence first in 4/8. The ToM temporal-link memories wrote to
381 and 387 distinct branch/slot locations with zero overlap. Their complete
native activation maps selected the correct sequence in 8/8, while the
untrained tree opened no memory.

Only the explicit temporal-link 32×32 matrix was taught; the two event loads
were held equal and excluded. No branch was averaged and no whole-tree score was
calculated. Complete routed inputs, signed terminal fields, slot scores and
activation maps for both teaching orders remain in two roughly 58.4 MB archives
under Passport `rgm500_sequence_discrimination_v1/`. The first completed report
used an incorrect acceptance rule that confused the native-vector tie with the
later rank-fusion scores; it is retained as
`MISCLASSIFIED_BY_ACCEPTANCE_RULE`. The rerun changed only that diagnostic rule.
This establishes a controlled sequence-memory gain, not automatic sequence
extraction or performance on natural project event histories.

The bounded `--rgm500-cross-source-motif` follow-up then uses real project
material. The unmodified RGM parser produced 315 native chunks from the executed
M12 Interface Agreement and SCAW D&C Deed; native admission retained 312 unique
chunks and rejected three exact duplicates. Two chunks in different contracts
state the same reviewed sequence motif: written notice before a required
meeting. For three structure-only questions, full RGM contextual retrieval with
a twenty-record allowance returned only one of the six expected source
occurrences and never returned both sources together. The target vector ranks
were 13–47.

That one reviewed sequence motif was learned once by the approved circa-500
tree and bound to both RGM chunk IDs. All three question forms reopened its
complete 381-location native slot map and returned both exact source pointers;
the untrained tree opened no memory. This is the intended shared-memory case:
one structural memory can connect several evidence locations, while RGM retains
their separate text and provenance. No branch was averaged and no whole-tree
score was calculated. Complete routed inputs, signed terminal fields, slot
scores and activation maps remain in the 38 MB Passport archive
`rgm500_cross_source_motif_v1/native_fields.npz`; the compact result is
`native_rgm500_cross_source_motif_comparison`.

The claim remains narrow. The motif was reviewed and supplied, automatic motif
extraction is not tested, and the two native RGM heading chunks are the parser's
4,003-character truncated outputs. The live app now admits this one reviewed
motif through the lossless RGM corpus path: the first source writes one ToM
memory, later sources bind without another tree write, and one retrieved source
can reopen every authenticated RGM passage linked to that structure.

The bounded live-tree verification used the approved 507-branch fixture. The
motif wrote to 381 native branch/slot locations. Three question forms reopened
the same complete signed distributed field and returned both source pointers;
every read left the saved tree unchanged. No branch response was averaged and
no whole-tree score was calculated. The 217 MB checkpoint and 2.9 MB reference
archive are on Passport under
`native_learned_recall/live_temporal_motif_bridge_v1/`; the compact result is
the adjacent `result.json`.

The result establishes a useful integration boundary: RGM retains exact text
and provenance, while a verified directed situation can address a distinct
distributed ToM memory. It does not validate automatic relationship extraction.
The event roles in this bounded test were already frozen and verified. The live
document path must not teach the tree from an unreviewed parser proposal.

The immediate trained-parser check confirms that boundary. The retained V14
event-graph adapter was run once on each mirrored real clause. Both proposals
identify the reimbursement direction correctly on manual review, but neither is
valid under its frozen graph schema. Clause 23.5 emits an unsupported
`Business Days` quantity unit and incorrectly represents SM as both actor and
recipient of its premium payment. Clause 24.5 emits unsupported contract-action
labels and produces four events where the mirrored clause produced two. Changing
the compiler to accept these outputs was rejected because it breaks the frozen
adapter contract; that attempted change was reverted.

The earlier narrow relationship extractor remains a useful control: for both
clauses it captured the failure party, substitute-cover payer, repayment
direction, 30-Business-Day period and on-demand timing with exact source spans.
That extractor is explicitly insurance-specific and does not justify general
automatic document learning. The safe integration remains reviewed or otherwise
verified relationship records → structured matrix → ToM memory, with RGM keeping
the exact source. Automatic full-graph ingestion is blocked. Raw proposals,
model identity, validation errors and the control are retained under
`native_rgm500_structure_parser_diagnosis` in the compact master report.

The bounded `--rgm500-persisted-situation-bridge` follow-up wires the safe
boundary directly. It stores the reviewed clause-23.5 situation as an RGM
snapshot containing directed relations plus the exact chunk provenance, then
serializes and reloads RGM before ToM sees it. The restored relation is the only
source-side structure used to teach a fresh copy of the approved 500-branch
tree. Both held-out questions open all 381 learned branch/slot locations and no
other locations; the untrained-tree control opens none. The questions produce
the same complete signed return as each other. That return differs from the
teaching load, as expected for a new question entering the learned structure.

No branch or 32×32 field is collapsed. The complete trained and untrained
fields are retained in the 29 MB Passport archive
`rgm500_structural_bridge_v1/rgm_persisted_n05_native_fields.npz`; the compact
record is `native_rgm500_persisted_situation_bridge` in the master report. Peak
process memory was 1.17 GiB. This proves the reviewed RGM-record → persistent
ToM-memory boundary for one real relationship. It does not prove automatic
relationship extraction. Tom 17D's current evidence validator cannot supply
that authority because it accepts both the correct and reversed direction when
both party names and the relation word occur in the source.

The next `--rgm500-persisted-situation-coexistence` control reloads both
mirrored RGM records together before teaching one fresh ToM copy. Clause 23.5
writes 381 locations and clause 24.5 writes 387 different locations, with zero
overlap. Each of the four held-out questions opens every location belonging to
its correct relationship, none belonging to the reversed relationship, and no
unowned location. The untrained tree again opens none. Thus multiple
source-bound structural memories can coexist without the two directions being
blended. Complete trained and untrained fields are retained in the 58.5 MB
Passport archive `rgm500_structural_bridge_v1/rgm_persisted_coexistence_native_fields.npz`.
The compact result is `native_rgm500_persisted_situation_coexistence`; peak
process memory was 1.31 GiB.

The subsequent `--rgm-document-ingestion` audit uses the actual unmodified
`tom_master17D/interface/doc_ingest.py:ingest_any_document` on the complete
executed M12 agreement, with native `auto` mode and default `zero_copy_strict`
storage. Its memory store is isolated in a temporary directory; exact native
chunks, anchors, persisted records, indexes and diagnostics are retained in
`rgm_native_agreement_ingestion` in the existing master report. Observation
wrappers preserve the original function results and writer. No controller,
provider or tree is started.

The native route reports success but creates 212 section chunks and keeps only
50. Insurance sections are zero-based chunks 54/55, outside that limit. The
section chunker also truncates each to 4,000 characters: 2,457 characters are lost
from section 23 and 3,194 from section 24. All twelve benchmark clauses exist in
the extracted PDF; only six remain complete after section truncation, and none
remain in the admitted fifty anchors. This coverage check removes whitespace
only to tolerate PDF extraction joining words; its earlier whitespace-collapsed
comparison is preserved separately.

All fifty stored `file://...pdf#section_N` references resolve to the same decoded
PDF file bytes rather than their extracted chunks (zero exact chunk recoveries).
All fifty section metadata ranges also have end_line before start_line. These
are ingestion/provenance defects upstream of tree retrieval. The comparison is
not ready: do not train or score either arm on this incomplete evidence corpus.
The source PDF, upstream modules and trees were not changed; no fix or settings
override was made during the audit.

The follow-up `--rgm-document-ingestion-repair` isolates three changes using that
same frozen extraction and native heading output. Removing only the anchor cap
recovers six of twelve complete clauses. The opt-in
`build_rgm_document_corpus` adapter in `document_ingestion.py` then maps native
headings back into the original extraction and partitions long sections instead
of truncating them: 212 sections, 248 chunks, all 272,620 characters retained,
and all twelve clauses complete within individual chunks. It retains stripped
headers too; it does not invent PDF page coordinates.

`retain_rgm_document_corpus` stores one extraction and range manifest in the
existing `PermanentLibrary`; `resolve_rgm_document_chunk` validates the manifest,
source and reference checksums before returning the exact extracted text.
All 248 references recovered exact text after a fresh reader process reopened
the saved library. The disposable 414 KB database was removed; the extraction,
manifest and references remain reproducible in the existing master report under
`rgm_native_agreement_ingestion_repair`. Seven focused tests cover preservation,
reopening and rejection of damaged imports/references. Upstream code and the
tree are unchanged. This corpus path is explicitly separate from default app
imports and legacy runtime archives. Retrieval comparison remains pending.

The complete-document component baseline is now recorded by
`--rgm-document-retrieval-baseline` and its diagnosed follow-up
`--rgm-document-retrieval-dedup-checked`. The first rehearsal stopped because
the harness expected every occurrence to become an anchor. Native RGM properly
rejected three exact duplicates. The follow-up accepts only checksum-duplicate
refusals whose full text exactly matches an admitted anchor: 248 source ranges
remain retained and 245 unique texts are indexed. Native gates were unchanged.

On the twelve frozen insurance questions, ten require identifiable evidence;
zero of those ten retrieve all required evidence at rank one or within the
top three. Correct chunks rank 4–33. All 36 returned references recover exact
source text; reversing insertion order changes no returned list. The two
reversed-premise rejection cases remain unscored because a retrieval reader
does not establish answer support. The partial-answer case is scored only for
its known clause, not its absent policy number. These are chunk-coverage results,
not answer accuracy or tests of the complete contextual chat stack.

`--rgm-document-reader-diagnosis` decomposes twenty saved winner/correct scores
exactly. The unchanged native `VectorStore` uses 256 hashed whitespace-token
counts, retaining punctuation. Collisions give unrelated words matching weight;
for example `insurance` and `or`. No alternative ranking is fitted or tested.
The broader STM/LTM path uses this same vector reader but adds other channels
not exercised here. Its historical 8D/17D tree is not the selected native 500
tree. The existing 500-branch bridge knows two synthetic associations, not this
document; no ToM advantage was tested or claimed. All three result sections
are retained separately in the existing master report, including the stopped
rehearsal. No upstream source, tree, provider or model changed.

The paired MiniLM comparison now runs through
`--rgm-document-minilm-encode` (existing local Python/model) and
`--rgm-document-minilm-read` (isolated older RGM reader). It replaces only the
reader's text representation: the same native cosine/read/write logic consumes
384-dimensional MiniLM vectors instead of 256-bucket token counts. The native
VectorStore instance receives the frozen encoder and matching dimension; no
upstream source is edited. Corpus, questions, context, deduplication and top-three
limit match the baseline. No additional clauses or candidate windows are indexed.

Long chunks use the existing token-window planner (188 tokens, overlap 32) and
semantic-profile passage centroid weighted by newly covered source characters.
This includes the entire source, while preserving one candidate per original
RGM chunk; it is not a best-window scorer. Encoding retained 650 internal window
vectors for 248 source chunks and 12 questions. Ninety-one source chunks needed
multiple windows. Actual model inputs never exceeded 190 tokens and no input
was truncated. The model tokenizer emitted a length warning while calculating
full-source offsets; that unsplit sequence was never passed into the model.
The loader reported only the pre-existing position_ids buffer as unexpected.

Required-evidence coverage improved from 0/10 to 4/10 at rank one and from
0/10 to 7/10 within three results. Remaining top-three misses are L02 (SM
premiums, rank 4), L04 (SM excess, rank 6), and L10 (SM deductible evidence,
rank 4). All target chunk ranks are now 1–6. All 36 returned source references
resolve exactly and reversing insertion order changes no results. The two
reversed-premise cases remain unscored; no answer generation/refusal claim is
made. These results concern the frozen single-vector-per-chunk MiniLM readout,
not ToM added value or the broader contextual RGM system. Full fields of the
tree were never read, reduced or changed. Existing report sections
`rgm_complete_document_minilm_encoding` and
`rgm_complete_document_minilm_baseline` retain model identity, window offsets,
vectors, full ranks and paired results. Nine focused preservation/window tests
pass; all earlier reports remain unchanged.

### Broader RGM capability audit — 16 September 2026

The earlier ordinary-reader comparisons do **not** evaluate the full RGM.
The read-only audit inspected checkout `cb0d90c1` and locally saved
`origin/main` `1b1cf823`; no remote fetch or live deployment inspection occurred.
The source repository and its working-tree status remained unchanged.

| Capability | Implementation and observed boundary |
| --- | --- |
| Persistent governed memory | Admission, quarantine, reinforcement, decay, source references, and causal/identity/commitment indexes in `memory/rgm.py`. |
| Structured snapshots | Stores supplied entities, relationships, goals, constraints, changes, outcomes and graph/visual projections. Seven existing checks passed. Storage of supplied structure does not prove extraction of those relationships from arbitrary prose. |
| Contextual retrieval | Combines document-vector, RGM, cross-session, action-outcome and agent-observation candidates, plus active-branch resonance. Conversation state can supply retrieval triggers. This exceeds the ordinary `read_memory` path tested earlier. |
| Document navigation and evidence | Document Skills Index selects sections; Structured Evidence Index supports numeric facts and heading counts. These are not general legal-obligation extraction. |
| Branch-event memory joint | Saved main adds immutable branch/event bindings, source/load receipts, cold validation, transactional learning/write rollback, and bidirectional branch/memory recall. These modules are absent from the inspected checkout. |
| Feedback-grounded branch recall | Saved-main recall scans all branch-event memories and follows bound branches; feedback changes which supported path returns. Four existing checks passed, including a supported path behind 256 distractors and tampered-address refusal. These use fixture branch states, not the selected native matrix tree. |
| Live structural context | Saved-main chat calls district-live recall to add context from owner signatures and persisted members. No ordinary chat caller was established for the newer branch-event runtime joint. Available components must not be equated with a fully connected deployment. |

Three existing structural gate artifacts passed their stored integrity checks.
The copied 10,000-branch recall evidence shows grounded feedback choosing the
supported valve path despite a higher-cosine alarm distractor; feedback-off and
shuffled-feedback controls change the result. Its capacity follow-up reopens
512 memories: **two branch-event memories and 510 ordinary distractors**, not
512 independently learned events. Those are historical results, not fresh
mature-tree runs. The earlier relational-retrieval certification also remains
blocked by a wrong-root result; held-out testing there was not opened. The audit
does not claim universally successful structural retrieval.

The new document replay calls the actual retrieval, context-formatting and
evidence-policy functions over the repaired 248-chunk corpus. Eight selected
functions have identical syntax trees in checkout and saved main. It supplies
no conversation history, continuity/action stores or learned branch state;
therefore it is a document-path diagnostic, not full chat or branch-context
performance. Original native ingestion indexes are retained unchanged: 41
document skills, 369 headings, zero extracted numeric facts. They do not cover
the repaired corpus completely.

| Complete required-clause coverage, ten evidence-bearing questions | Native word counts | Frozen MiniLM |
| --- | ---: | ---: |
| Full source text behind returned results | 1/10 | 9/10 |
| Returned excerpts, bounded to 500 characters each | 0/10 | 0/10 |
| Formatted context, bounded to 200 characters per excerpt | 0/10 | 0/10 |

This is full-clause coverage, not an answer-accuracy score. The real fusion path
allows ten items but its 2,000-character budget retained four 500-character
excerpts in these runs. It is not a like-for-like top-three improvement over the
earlier benchmark. The observed loss is truncation during evidence handoff.

Two further wiring defects were exposed:

- The ordinary section-injection path is gated by `_is_recall_intent`, which
  unconditionally returns false in both revisions. It was intentionally disabled
  to prevent raw-document reply bypasses; this audit does not enable it. Evidence
  policy can still consult the indexes independently. Reopening the original
  fifty document-store records in a fresh process restored neither index; this
  establishes that simple store reopening does not rebuild them, not that every
  possible application restoration path fails.
- Evidence policy wrongly verifies a heading count for L01 (who pays clause
  23.1 premiums) and L09 (premium and deductible responsibilities). Both encoder
  arms return `section_4_count is 3`. Section lookup selects an access section;
  the policy accepts its count before establishing that the question requests a
  count. The actual chat branch would return this reply before calling the
  language model. The other ten questions return open-intent `not_found`, which
  does **not** force the same early refusal. No live chat/provider call was made.

The architecture conclusion changes: RGM already contains structural and
branch-linked machinery, so it should not be reduced to an exact-text archive
while duplicating that machinery elsewhere. Reuse its provenance/binding design,
repair evidence handoff and question-appropriate verification in the ToM Assist
boundary, then measure whether the approved circa-500 native matrix tree adds
useful discrimination. The older 8D address/branch mechanics are not a drop-in
replacement for native signed 32×32 returns. Preserve those fields throughout.

Reproduce the bounded audit with the existing calibration runner's
`--rgm-capability-audit-system-python` and
`--rgm-capability-audit-evidence-policy` modes. Existing component checks use
`--rgm-existing-capability-checks snapshots|branch-recall`. The initial isolated
gateway-environment attempt stopped on missing `requests`; it remains recorded.
System Python successfully ran the actual functions with installed dependencies.
All results are separate sections of the existing
`validation/runs/stream1-native-learned-recall.json`; previous results are retained.
No upstream changes, native tree steps, new model, provider call or PDF occurred.

### Complete source handoff — 16 September 2026

`build_rgm_evidence_context` in `document_ingestion.py` now resolves each selected
document memory through its ingestion-owned `(document ID, chunk ID)` reference
and the permanent corpus shelf. It validates the selected range and hash,
restores the entire passage, and supplies both full-content memory records for
evidence checking and full source-labelled context for answering. Candidate order,
scores and native metadata types are preserved. Missing, swapped or damaged
references fail rather than falling back to excerpts. An optional caller context
budget rejects overflow explicitly; it never truncates text or drops candidates.
This adapter accepts document-chunk memories with one source range each. It does
not claim to handle arbitrary multi-source memory records.

The existing runner's `--rgm-document-evidence-handoff-v2` stage connects this
adapter immediately after the unchanged native document retrieval. It uses the
same questions, corpus, frozen encodings and evidence policy as the audit. Both
encoders repeat twelve questions. All 24 candidate lists, rank-fusion scores and
pre-repair contexts match the frozen audit exactly. The adapter reads a reopened
temporary permanent shelf and restores **96/96 selected passages exactly** into
the context. Four selected passages require 3,562–13,790 source characters per
question; source-labelled context is 7,573–17,798 characters. Temporary databases
are removed. No new model or tree run occurs.

| Complete required-clause coverage, ten evidence-bearing questions | Before handoff repair | After handoff repair |
| --- | ---: | ---: |
| Native word counts, final answer context | 0/10 | 1/10 |
| Frozen MiniLM, final answer context | 0/10 | 9/10 |

The remaining MiniLM miss is L04 (SM policy excess): chunk_79 was not selected.
Restoring evidence cannot repair candidate selection. L07/L08 remain unscored
for answer correctness; L10 only measures delivery of its known clause, not
support for its absent policy number. These numbers establish evidence delivery,
not correct answers. The unchanged evidence policy still incorrectly verifies
`section_4_count is 3` for L01/L09 and returns open-intent `not_found` for the other
ten questions. Its decisions/replies remain identical to the earlier audit.

The first handoff run stopped before completing any question: copying native
metadata through JSON rejected a set. It is retained as
`rgm_17d_capability_audit_system_python_evidence_policy_source_handoff`, status
`STOPPED_HANDOFF_METADATA_COPY`. The correction preserves native types with a
deep copy; the completed run is the separate `_source_handoff_v2` section.
Fourteen focused corpus/handoff checks pass, including native set metadata,
reopened storage, full passage tails, rank preservation, budget overflow and
damaged provenance. Older reports and upstream source remain unchanged.

This repair is active in the explicit RGM corpus integration/replay. It does not
modify upstream Tom 17D, enable default desktop wiring, or fix its evidence
policy. The next separate change is question-appropriate evidence verification.

### Reject unrequested section counts — 16 September 2026

The next isolated change is `guard_rgm_heading_count` in `native_memory.py`,
called after the unchanged upstream evidence policy in the explicit corpus
integration. Diagnosis: upstream `_try_sei_extraction` falls back from key lookup
to a matching section's heading count without first establishing that a count was
requested. `decide` then infers numeric intent from the extracted number and
marks it VERIFIED. Thus finding a count changes the supposed question type.

The ToM Assist guard recognizes the structured `section_N_count` result, not
specific insurance questions or answer labels. To retain that automatic reply,
the question must explicitly request a subsection/subheading count for the same
section (or that exact named count), with its index source bound to the sole
active document. It accepts a small explicit grammar; ambiguous, compound or
unsupported wording goes to evidence reading instead of being declared absent.
Wrong question type, section or document cannot retain automatic approval.
This checks request/source alignment, not the correctness of the upstream count
calculation or the relevance of other kinds of answers.

Rejected results become `needs_evidence_reading`, with no answer text and no
automatic reply. The upstream decision remains separately recorded. Complete
source context stays available; the guard does not generate an answer or enable
unrestricted language-model completion. Non-count and already-unverified results
are unchanged. No source index, selector, threshold, ranking or tree is modified.

`--rgm-document-question-check` reruns the same twelve questions under both
encoders. All 24 runs match the previous source-handoff stage in selected IDs,
rank-fusion scores, full context and upstream decision/reply before the guard.
It rejects L01 and L09 in both arms (four false approvals across two unique
questions). The other twenty decisions/replies remain unchanged. MiniLM still
delivers all required clauses for 9/10 evidence-bearing questions; this is not
9/10 verified answers. L01/L09 now need a source-evidence reader; the other ten
questions still receive upstream open-intent `not_found`, not an enforced refusal.

All 45 native-memory boundary checks pass, including 18 checks for wrong answer
type, wrong/ambiguous document, wrong section, compound/negative wording, retention
of matching count requests, and unchanged non-count results. Count-positive
checks use component fixtures; no end-to-end count-accuracy claim is made.
The completed report is the new `_source_handoff_v2_question_check` section;
the previous failures/results remain intact. This is an experimental integration
guard, not a change to upstream Tom 17D or default desktop wiring. The next
unresolved task is selecting the actual supporting evidence and answering from it.

### Full-passage evidence reader — 16 September 2026

`read_rgm_source_evidence` now connects the full-source packet to the existing
local Gemma instruction model, using the frozen MiniLM candidate outputs. It
splits compound questions with the existing question planner, gives every part
all selected passages, and validates each returned source ID and contiguous
quotation. Answers are source quotations with extracted-text offsets and original
provenance; no second free-form completion changes their wording. No expected
facts, pre-extracted source roles or answer labels enter the reader. This remains
the explicit integration, not default desktop wiring or native-tree recall.

The local model is the existing Gemma 4 26B A4B 4-bit snapshot, without an adapter
or training. Fifteen generations cover twelve questions (including planning and
separate parts); zero external provider calls. Maximum input was 4,167 tokens,
without truncation, under the existing memory-budget calculation's 8,192-token
envelope. Measured peak MLX allocation was 14.83 GiB; the tree was not loaded.
All model files were hash-checked. The initial sandbox process-inspection refusal
was resolved through approved execution permissions before model loading.

| Case | Requested evidence | Reviewed result |
| --- | --- | --- |
| L01 | Clause 23.1 premium payer | TfNSW; exact clause 23.2 quotation. |
| L02 | Clause 24.1 premium payer | Reader identifies SM but its quote is blocked: PDF extraction says `p ayable`, reader writes `payable`. |
| L03 | Clause 23.1 deductible payer | TfNSW; exact clause 23.3 quotation. |
| L04 | Clause 24.1 excess | Reader declines: necessary chunk_79 was not selected. Retrieval miss remains. |
| L05 | SM buys replacement insurance after TfNSW fails | TfNSW reimburses SM on demand; clause 23.5(b). |
| L06 | TfNSW buys replacement insurance after SM fails | SM reimburses TfNSW on demand; clause 24.5(b). |
| L07 | Reversed repayment with SM as replacement buyer | Reader incorrectly claims support from a different situation; non-exact quotation is blocked. |
| L08 | Reversed repayment with TfNSW as replacement buyer | Reader incorrectly claims support from a genuine opposite-direction quote. Initially passed citation checks; added direction check now blocks it. |
| L09 | Clause 23.1 premiums and deductibles | Both requested obligations quoted separately, clauses 23.2 and 23.3. |
| L10 | Clause 24.1 deductible payer and policy number | SM obligation quoted; absent policy number separately refused. Correct partial answer. |
| L11 | Full/true insurer information under 23.4(a) | TfNSW duty and contractor-procurement condition preserved. |
| L12 | Notice to TfNSW under 24.7 | SM duty, timing, policy scope and further-notice condition preserved. |

Manual semantic review finds **8/12 correct question outcomes**, including the
partial answer. L04's safe refusal does not fix its retrieval failure. L07/L08
are reader failures, not successful comprehension merely because the application
withholds their outputs. A real quotation can answer a different question.

After preserving the original fifteen model outputs, the consumer now reuses
`interpret_native_question` to compare explicit named repayment directions in the
question and quote. Mismatches invalidate the proposed answer. The exact cached
outputs were replayed with every input/instruction hash checked; only L08 changes
from supported to invalid. No new model generation or prompt tuning occurred.
This is a narrow explicit-relation guard, not a general conditional verifier;
the seven unaffected correct complete answers and correct partial answer remain.
Word-boundary checks were not relaxed to hide L02's extraction problem.

All 51 native-memory boundary tests pass. Raw generations and failures remain
in `rgm_document_source_answers`; the separate
`rgm_document_source_answers_relation_check` section records replay and semantic
review with status `COMPLETE_WITH_READER_FAILURES`. Runner modes are
`--rgm-document-source-answers` and `--rgm-document-source-answer-replay`.
Neither RGM nor either tree was changed. Before automatic answering is ready,
the reader still needs reliable checking of the complete stated situation,
including who failed and who bought cover, alongside the known source-copy and
candidate-selection failures.

### Linked insurance situation check — 16 September 2026

`check_rgm_replacement_chain` now independently compares four explicit roles:
failure party, replacement-cover purchaser, repayment debtor and repayment
creditor. Names and supporting spans come from the question and selected source
text. It does not assume that the failing party owes repayment, or fill any role
from the expected answers. Unasked question roles remain unset.

The source parser keeps a complete clause together. The failure/purchase relation
must appear in subsection (a), the debt and matching reimbursement obligation in
(b), and the latter must refer to that clause's (a). The payer and repeated
debtor/creditor references must agree. Extra/missing subsections, negation,
additional qualifiers, unresolved repayment provisions and ambiguous matches
remain unverified. Parsed fields include their original source spans. PDF line
wraps are accepted as whitespace; word spelling and source ranges do not change.
Unknown question wording also remains unverified. This is deliberately bounded
to the observed compliance/replacement-insurance grammar, not general contract
reasoning or a new tree capability.

When one complete chain matches, the application returns the whole linked clause,
including its condition and repayment obligation. It independently selects that
clause from the already-retrieved passages rather than accepting the reader's
quote proposal. If all recognized chains conflict and none is unresolved, it
returns not_supported for the supplied evidence. Non-applicable questions keep
the existing reader and exact-quotation path. Retrieval remains unchanged.

| Source | Failure | Cover purchaser | Repayment |
| --- | --- | --- | --- |
| 23.5 | TfNSW | SM | TfNSW → SM, on demand |
| 24.5 | SM | TfNSW | SM → TfNSW, on demand |

The first reversed question (L07) conflicts with 23.5 on repayment direction and
with 24.5 on failure/purchaser. L08 conflicts with 24.5 on repayment and with 23.5
on failure/purchaser. Neither can be answered by borrowing roles from both clauses.
L05 and L06 retain the correct answers with the full linked clauses attached.

The unchanged fifteen saved model outputs and input hashes were replayed across
all twelve questions. **10/12 outcomes now match the frozen expectations**, with
manual source review: eight correct complete/partial answers and two grounded
refusals. L02 still fails exact quotation because of `p ayable`; L04 still lacks
its required selected passage. No new model generation, training or tree run.
This is regression on exposed questions, not held-out language validation.

All 65 native-memory tests pass. Controls change each role independently, rename
parties, prohibit combining partial matches, check clause links and subsection
boundaries, and defer unsupported/negative/qualified wording. The initial parser
rehearsal missed a line-wrapped phrase; a separate unit assertion incorrectly
included a final newline in an exact quote. Both observations and corrections
are recorded. The first chain replay is preserved; the final boundary-strengthened
replay is `rgm_document_source_answers_chain_check_v2`, produced by
`--rgm-document-chain-check-v2`. Earlier raw reader failures remain unchanged.
The experimental integration is not activated in the default desktop path.

### PDF quotation spacing check — 16 September 2026

The optional `make_rgm_pdf_quote_resolver` source-layer check repairs the L02
quotation refusal without editing the stored extraction. PDF page 57 (printed
52) shows `payable`; the old extraction inserted a space in `p ayable`. A fresh
pdfplumber reading of the checksum-bound PDF confirms the word boundary. The
resolver requires one source occurrence and one matching location in that PDF,
including up to 64 unchanged non-whitespace characters on either side (at least
32 context characters). It then requires the proposed quotation's actual word
boundaries in the independent extraction. Compact strings locate the span only;
they do not authorize joining words. Ambiguous/changed text remains refused.

`read_rgm_source_evidence(..., spacing_resolver=resolver)` uses this only after
ordinary exact-span matching fails. It returns the original stored quotation,
source hash, and original absolute offsets, with separate PDF verification
telemetry. The optional resolver requires pdfplumber and is not enabled in the
default desktop path. It does not certify semantic support or alter retrieval.

`--rgm-document-pdf-spacing-check` replays the same fifteen saved model calls
and exact input hashes. **11/12 exposed question outcomes are correct**, up
from 10/12. Only L02 changes; SM's clause 24.2 answer now passes. L04 remains
a retrieval miss because the required chunk is not selected. No new generation,
tree run, corpus rewrite or PDF creation. All prior report sections remain
unchanged; the appended result is `rgm_document_source_answers_pdf_spacing_check`.
There are 78 passing native-memory tests and 14 passing RGM corpus/handoff tests.
Spacing controls reject altered actors, numbers, negation, ambiguous locations,
wrong document hashes and meaningful word-boundary changes.

### Candidate handoff diagnosis — 16 September 2026

L04 is not absent from retrieval. Its required `chunk_79` ranks sixth in both
native candidate channels and after their fusion. The unchanged 2,000-character
preview bound passes four 500-character excerpts, then stops. The correct
passage would bring the cumulative preview length to 3,000 characters.

`--rgm-document-candidate-budget-diagnosis-v3` reruns the real document-only
native path with frozen vectors, queries and corpus, varying only `max_chars`
from 2,000 to 5,000 and retaining `max_items=10`. All twelve original selections
are reproduced in the control arm. Both arms have identical captured pre-bound
inputs and identical native rankings/scores. Required source coverage improves
from 9/10 to 10/10 answerable questions, evaluated only after selection. L04's
seven complete sources resolve correctly (27,188 characters including labels).
This is source availability, not a new answer-accuracy result; the reader was
not rerun and the previous 11/12 answer result remains the latest.

The expanded arm exposes a separate upstream defect: candidates built by the
vector-only fusion path omit `source_refs`. Complete evidence handoff refuses
L01/L02 (`chunk_76`) and L12 (`chunk_92`). Native source confirms that path copies
content/tags but omits provenance, while scored candidates retain it. Also,
vector-only candidates carry full text rather than uniform 500-character
previews, so a larger preview bound is not a reliable candidate-count policy.
The 5,000-character setting is diagnostic only, not a default app change.
Source provenance must be preserved before expanding the production handoff;
complete-source language-model context capacity also remains to be checked.

No tree, model, training, network or upstream edits. The initial runner lookup
error and second run's genuine missing-reference refusal remain recorded in
`rgm_document_candidate_budget_diagnosis` and `_v2`. The completed `_v3` records
all twelve comparisons and handoff refusals rather than silently dropping them.

### Restore vector-only citations — 16 September 2026

`build_rgm_evidence_context` accepts the optional ingestion-owned
`original_anchors_by_source` registry. A vector-only document candidate with
absent `source_refs` must name one document, match its original anchor identity
and complete content, and match the authenticated persistent corpus text. Only
then are the original references copied into the returned packet. Present but
empty, malformed or conflicting references are never replaced. Candidate order,
scores, text and input objects remain unchanged; recovery is recorded separately.
Callers without the trusted registry retain the previous strict refusal.

`--rgm-document-candidate-provenance-repair` reproduces both prior budget arms:
**24/24 handoffs now succeed**, with exactly three missing references recovered.
All selections and captured pre-bound inputs match the preceding diagnosis;
already-valid citations remain identical. The expanded arm retains the required
sources for all ten answerable questions. This remains opt-in experimental
consumer wiring, not activation of a larger default desktop retrieval budget.

`--rgm-document-expanded-reader-preflight` uses only the frozen local tokenizer.
Its template hashes and token counts reproduce all fourteen original reader
prompts exactly before measuring the expanded sources. All fourteen expanded
inputs fit the unchanged 8,192-token prompt bound: maximum **7,247**; L04 uses
6,233. Original question parts are reused, with no generation, truncation,
model-weight loading or answer-accuracy claim. The latest answer score stays
11/12 until the reader is rerun. Initial MLX tokenizer import failed on sandbox
Metal access; CPU AutoTokenizer supplied the verified equivalent template.

Focused source tests: 28 pass. The broader native-memory/document suite returns
149 passes and one failure in the separate saved Stream1 inspection path: its
package identity differs from the pinned `GemmaInspection.STREAM_SHA`. That
guard and external source are unchanged. The new controls reject unknown or
ambiguous document identities, truncated/altered content, corrupted retained
text and attempts to replace present invalid references.

### Expanded answer run status — 17 September 2026

`--rgm-document-expanded-source-answers` is prepared for the twelve questions,
using the frozen expanded candidates, unchanged reader/checks and preflight
input hashes. Only the unchanged question-decomposition output is reused;
answer generations are fresh. The first attempt stopped before model loading
because available memory was below the existing 22 GiB headroom allowance.
Two follow-up checks remained below it. No model call or new answer occurred;
11/12 remains the latest answer result. The stopped run and memory measurements
are preserved. `--rgm-document-expanded-source-answers-attempt2` is available
once the unchanged resource check passes. No app was closed or guard weakened.

### Fresh expanded reader results — 17 September 2026

The authorized second attempt completed after the existing memory/concurrency
check passed normally. No guard override or tree load was needed. Fourteen new
local Gemma readings covered twelve questions; the single unchanged question
decomposition was replayed. All prompt hashes/token counts matched preflight,
and the source/instruction/model checks remained fixed. Runtime was 194.65
seconds; peak MLX allocation was **15.04 GiB** (not whole-system memory).

**Final evidence-checked outcomes remain 11/12.** L04 now correctly identifies
SM's deductible obligation in clause 24.3. L12 regresses: the raw reader refuses
the notification question despite the complete clause 24.7 being present in
chunk_80 and the verified prompt. That clause requires SM to notify TfNSW as
soon as reasonably practicable of the specified claims/events. This is a reader
false refusal, not missing evidence. Do not describe expanded context as an
overall accuracy improvement or assert that more context caused the regression
without a controlled follow-up.

Gemma also incorrectly proposes support for both reversed-party questions;
the unchanged four-role evidence checks reject those proposals correctly.
Therefore 11/12 describes the complete reader-plus-checks pipeline, not Gemma
alone. The absent policy number is correctly refused while the supported
deductible part is answered. All returned text has exact original source offsets.

Raw outputs are preserved in `rgm_document_expanded_source_answers_attempt2`;
post-run semantic review, including the missed clause, is in the appended
`rgm_document_expanded_source_answers_attempt2_review`. This is the same exposed
battery, not held-out validation or proof of ToM recall. No default activation,
retrieval reranking, prompt change, training or upstream edit occurred.

### Cited-clause refusal repair — 17 September 2026

A paired fresh diagnosis reproduced L12's problem: the identical question and
reader answered correctly with the original four passages and refused with the
expanded eight. Both exact prompt identities were checked and the seed reset
between arms. This establishes context sensitivity for that pair; it does not
identify one particular distracting passage. Diagnosis is preserved in
`rgm_notification_context_diagnosis`.

`find_rgm_cited_clause` now locates a unique explicit clause citation inside the
already-selected evidence. Only after an ordinary reader refusal, with no
applicable four-role chain override, may the same reader examine that full clause
once. No answer, party or clause number is hard-coded. Multiple/absent citations,
duplicate clause identities and missing end boundaries do not trigger a guessed
view. Existing invalid/ambiguous outputs and situation-check refusals are not
overridden. No retrieval, source text, model instruction or tree state changes.

The second response must cite that same source and an exact span inside the
clause. A supported result returns the whole matched clause so omitted conditions
cannot disappear with a shorter model highlight. Both raw responses and the
validated highlight remain in the trace; all returned offsets still address
the original immutable source. A second refusal remains a refusal. This is a
bounded consumer repair, not a general semantic verifier.

Fresh retest: **12/12 correct final outcomes** on the existing exposed questions.
L12 now returns SM's notice duty to TfNSW under clause 24.7, with timing, policy
scope and the additional policy-required notice condition. The other eleven
answers are identical. The two raw reversed-party mistakes are still caught by
the original four-role checks; the absent policy number remains refused.

There were fourteen initial reader calls plus one clause recheck (518 input
tokens, 3.18 seconds), and one cached unchanged question plan. Model peak remained
15.04 GiB; run time was 203.80 seconds. A first retest stopped before model load
on the concurrent CPU tree process. The explicitly authorized rerun verified
and excluded only that small CPU job from the concurrency check; memory headroom
and the 19 GiB model allocation cap remained unchanged. No process was stopped.

The successful focused reading initially highlighted only the main notice duty.
Final deterministic rendering returns the complete clause, verified by replaying
all fifteen exact saved model inputs/outputs with zero new generations. Fresh
run: `rgm_document_cited_refusal_recheck_answers_attempt2`; final replay/review:
`rgm_cited_refusal_recheck_final`. All historical failures remain visible.
All 89 focused native-memory tests pass, including renamed clauses/parties,
duplicate/missing sources, outside-clause quotations, invented details and
retention of a condition omitted from the model highlight. No held-out claim,
default desktop activation, tree test, upstream edit or training is implied.

`tom_gateway.py` is the byte-frozen pilot-v4 gateway for the pinned read-only
`tom_master` runtime. Production development and packaged-journey launchers use
`evidence_gateway.py`, its versioned evidence-backed subclass. Both serve
HTTP-shaped JSON over a user-only Unix socket.

Preview purity is structural: preview uses the pinned upstream `preview_readout`
pure projection/selection/resonance exports, product RRF glue, a local mirror of
the applicable structural trigger, and RGM's `VectorStore.query`. Importing the
pinned `interface` package would also initialize unrelated chat/provider code,
so the 20-line upstream trigger wrapper is not imported.
The upstream `retrieve_ltm_with_stm_triggers` wrapper is intentionally not used
because the pinned implementation contains a mutating RGM read.

Sent, captured exchanges experience five ordered phases: step, RGM write,
response teaching, sent-packet usage rotation, then front-row reinforcement,
decay and pruning. Drafts never enter this path. The existing pure projection
supplies the teacher's required shape; this does not add a prose-to-shape model.

Each project's `tom/library.sqlite3` permanently retains full content before
front-row admission and atomically journals engine/RGM snapshots, idempotency
and demotions. The JSON runtime files are recoverable projections of that head.
Back up the project directory, including this database; the desktop's ledger
export is not a runtime-library backup. Do not delete the library to reset a tree.
Checkpoint restore resets the working tree/front row and commit keys/settings,
but intentionally keeps permanent content and demotion history.

`POST /project/settings` accepts `project_id` and `settings` (empty object reads
current settings). Defaults: `front_row_capacity=4096`, `teach_on_conflict=true`.
Capacity is an integer from 1 to 1,000,000 and takes effect on the next commit.
Current-packet anchors are protected from capacity eviction for that commit;
other lowest-strength anchors are demoted with stable ID tie-breaking.
`POST /memory/diagnostics` returns counts and up to 200 demotions, including
record ID, content hash, reason, commit key and tick. Pass its `next_event_id` as
`after_event_id` to retrieve subsequent pages. Demotion never removes the library
twin. Readmission occurs on a later committed packet referencing that record.

CONFLICT exchanges wait for intervention resolution. Dismissal suppresses only
teaching when `teach_on_conflict=false`; the other dynamics still run once.
Capture/evaluation survive runtime failures and report `runtime_commit_pending`;
replay the same evaluation or resolution to retry with the same sent-turn key.
There is no background retry and previews never retry commits. A packet may bind
only one sent turn; ambiguous reuse is rejected. Pre-WP-17 truncated anchors
without their original full content fail the library-first migration closed;
legacy checkpoints lacking commit-key/settings snapshots are not silently restored.

## Evidence-backed local structure worker

The versioned replacement for prose-to-load keyword counting is available in
`shadow` and `authoritative` modes. It keeps two signals separate:

1. local MiniLM tokenizes the complete passage into sentence-preferred windows
   of at most 192 tokens with a 32-token overlap, then produces one
   unit-normalized 384-dimensional vector per window. Retrieval compares every
   query window with every stored window; the passage centroid is telemetry,
   never the only retrieval signal;
2. local Gemma fills one `structural-candidate/1.0` native tool call per window.
   Window-local spans are rebound to original passage offsets. The same directed
   relation with overlapping equivalent evidence is merged deterministically,
   including punctuation-only quote-boundary differences. Candidates contain entities,
   directed orientations, cause-to-effect relations, modality, negation and
   typed signals, but no 17D values. Product code supplies only trusted envelope
   metadata and missing empty signal containers; it never supplies a semantic
   fact, relationship, quote, direction or confidence on Gemma's behalf.

The parser boundary is versioned independently. Version 1.1 omits product-owned
metadata and empty signal keys from the model's tool schema, projects away only
unknown presentation fields, and can deterministically reparse malformed Gemma-4
container syntax. Evidence may be rebound only to source text already quoted by
the model, the entity's own source-present label, or the uniquely nearest/anchored
occurrence. Missing semantic fields and ambiguous ties still fail closed. Worker
telemetry reports planned, attempted and successful window calls plus the exact
failed window; it contains no prompts, vectors or credentials.

The gateway validates every quoted span and endpoint. Product-owned,
deterministic code calculates all 17 channels. Static channels use the strongest
bounded-window evidence rather than sums, so adding neutral chunks cannot
inflate the load. Frequency, persistence,
burstiness, novelty, recurrence, volatility and decay use only previously
committed semantic/structural history. The complete candidate, MiniLM and Gemma
model revisions, vectors, channel evidence, compiler/chunking versions and digest are
committed to the permanent library.
Prepared analyses are checkpoint-bound and replayed byte-for-byte at commit;
stale or altered analyses fail closed.

MiniLM/Gemma run in `.venv-structure`, never in `.venv-gateway` and never in
the pinned runtime process. Both checkpoints must already be local; the worker
does not download models and refuses API-key environments. Setup is deliberately
separate because the pinned runtime and Gemma require incompatible MLX versions:

```sh
python3 -m venv .venv-structure
.venv-structure/bin/python -m pip install -r gateway/requirements-structure.txt

export TOM_ASSIST_STRUCTURE_MODE=shadow
export TOM_ASSIST_STRUCTURE_PYTHON="$PWD/.venv-structure/bin/python"
export TOM_ASSIST_GEMMA_PYTHON="$PWD/.venv-structure/bin/python"
export TOM_ASSIST_MINILM_MODEL="/absolute/local/MiniLM/snapshot"
export TOM_ASSIST_GEMMA_MODEL="/absolute/local/Gemma/snapshot"
# Optional; default 600 seconds, permitted range 30..1800.
export TOM_ASSIST_STRUCTURE_TIMEOUT_SECONDS=600
```

Modes are:

- `legacy` (default): keyword/structural tree behavior for retained anchors. When
  a project has active documents, preview additionally runs local MiniLM query
  embedding so dense document excerpts can enter the visible packet; Gemma is
  not called.
- `shadow`: build, validate, persist and report the evidence analysis, but keep
  the existing drive/ranking behavior for comparison.
- `authoritative`: use the validated 17D signature for the canonical pinned
  commit application and the MiniLM plus directed-graph score for retrieval.

An unavailable worker, malformed tool call, non-matching quote, unknown entity
endpoint, stale checkpoint or altered load fails the prepare/commit. There is no
silent fallback from `shadow` or `authoritative` to keyword counting. The
language parser never imports or uses an emotion lexicon.

Create the isolated environment and install only the resolved runtime and test
imports:

```sh
python3 -m venv .venv-gateway
.venv-gateway/bin/python -m pip install -r gateway/requirements-dev.txt
```

### Experimental RGM document answers (local copy, September 2026)

The document retrieval machinery now lives in `gateway/vendor/rgm17d/`.
`SOURCE.json` records the upstream commit, source hashes and copied-file hashes.
Seventeen complete modules and the unchanged `_retrieve_relevant_memories`
function from `chat_adapter.py` are retained; internal imports are namespaced.
The upstream chat orchestration, model files, documents and tree are not copied.
The running document path does not import or read `tom_master17D`.

Enable explicitly when launching the **evidence gateway**:

```sh
export TOM_ASSIST_RGM_DOCUMENT_ANSWERS=1
export TOM_ASSIST_STRUCTURE_PYTHON=/absolute/path/to/python-with-torch-and-transformers
export TOM_ASSIST_MINILM_MODEL=/absolute/path/to/local/all-MiniLM-L6-v2/snapshot
export TOM_ASSIST_RGM_READER_PYTHON=/absolute/path/to/python-with-mlx-lm
```

Reviewed structural memory uses the approved 500-branch Stream 1 fixture and
must be configured separately. The base fixture remains read-only in its owner
repository. Every learned project checkpoint is larger than 100 MB, so the
state root must be on a mounted external volume:

```sh
export TOM_ASSIST_RGM_TOM_PYTHON=/absolute/path/to/python-with-numpy
export TOM_ASSIST_RGM_TOM_NATIVE_ROOT=/Users/you/PycharmProjects/tom_matrix_native_stream1
export TOM_ASSIST_RGM_TOM_BASE_CHECKPOINT=/Users/you/PycharmProjects/tom_matrix_native_stream1/artifacts/runs/native_500_branch_fixture_v1/native_500_branch_fixture.pkl
export TOM_ASSIST_RGM_TOM_STATE_ROOT="/Volumes/Your Passport/tom_assist_data/rgm_tom_states"
```

In Memory, enter a local PDF, TXT or Markdown path and explicitly choose
**Import document**. With this option enabled, extraction uses the copied RGM
reader, and ingestion stores its lossless chunks and MiniLM vectors directly in
the project library without initializing a tree. Files are limited to 100 MB,
extracted text to two million characters, and the active collection to 512
chunks. Original file/text hashes are retained. In Chat,
**Answer from project documents** reads only that project's active imported
text. It does not send the question to a cloud provider or commit a conversation
turn. Existing project text is partitioned by the copied RGM heading detector
and the tested lossless range adapter. Existing token-window embedding and
native contextual retrieval are used; `max_items=10`, `max_chars=5000` remains
the tested preview allowance. Complete source passages are then restored.

Import prepares and caches source vectors in the project's existing library;
questions reuse them, rebuilding an outdated cache if necessary. Cache identity includes the copied RGM
version and local MiniLM file hashes. RGM read reinforcement occurs in an
isolated request-local instance. This path does not claim persistent ToM learned
recall and does not use the app's live tree. Source text and range references
remain in the permanent project library.

An expanded source below a document answer now offers **Save a reviewed
structure in ToM**. The owner must copy the failing party and the party that
may obtain replacement cover from that exact source. Optional repayment roles
are retained in RGM. The gateway rejects values absent from the source, changed
source ranges, stale project state and unreviewed calls. Automatic relationship
extraction remains disabled because the current parser did not preserve party
direction reliably.

The reviewed source relations are first persisted as native RGM snapshots with
their exact document/chunk provenance. An isolated worker teaches one structured
32×32 ToM memory for each unique relationship. Replacement cover uses
source→target roles; reimbursement uses actor→recipient roles. Further reviewed
RGM sources describing the same relationship bind to that existing ToM memory;
they do not teach the same matrix at another address. This lets one distributed
return release several exact evidence locations without duplicating the learned
relationship. A source that explicitly negates a relationship or declares
supersession cannot be attached to the positive memory. If such evidence is in
the current RGM candidates, ToM does not narrow the evidence set. The answer
reports that the sources disagree and presents every exact conflicting and
currently bound passage with its provenance. No model or ToM process chooses a
winner. An optional explicit user action can record that one exact RGM passage
supersedes one or more older passages for one relationship, with an effective
timestamp and reason. The app never infers this authority from filenames, dates
or amendment wording. Once effective, and only
when every competing reviewed source has been covered, the newer passage goes
to evidence checking without a tree call. Older text and the ToM memory remain
unchanged for audit. The current integration is deliberately bounded to six
unique structural memories, matching the six orthogonal addresses already
tested. A
new structure must write non-overlapping tree locations; otherwise it is
rejected. Only the newest large checkpoint and reference archive are retained.

The bounded bridge supports three reviewed event structures: notice before a
meeting; failure followed by substitute action followed by cost recovery; and
human remains discovered followed by work stopping followed by authority
notification. Each multi-event structure is retained as separate ordered
relationships. Every complete distributed return and native slot map must
match before its source locations reopen. Reviewing another passage with the
same structure binds its immutable RGM source pointer without another ToM
write. These ordered structures can reopen their reviewed sources from an
explicitly ordered query even when RGM supplies no correct initial candidate.
Party and repayment relationships remain candidate-gated. The read-only review
queue currently scans only the failure/substitute/cost structure; the other
structures still require an explicit bounded review action. This does not
perform automatic motif extraction or accept arbitrary event graphs.

The failure/substitute/cost source guard checks one local procedure rather than
combining keywords from anywhere in a long RGM chunk. On the two frozen contract
corpora it recognized 12 reviewed procedures across 563 native chunks, including
insurance substitution, corrective work, emergency action and general step-in
wording. Nearby failure/debt clauses without substitute performance were
rejected. This remains a bounded admission check for an explicitly reviewed
motif; it does not automatically teach every detected passage.

Memory now exposes a read-only **Structures to review** scan for that bounded
motif. It lists the exact RGM passage and the three matched event phrases. The
scan makes no tree call. Each candidate requires a separate explicit Save
action, and the server repeats the source-local validation before teaching or
binding it. One source passage may retain different reviewed structure types;
it may not retain two conflicting versions of the same party relationship.

During an answer, MiniLM/RGM still locates candidate source passages when they
are available. When the question explicitly states an admitted event sequence,
the reviewed temporal structure can be accessed from the query alone. Reviewed
insurance relationships continue to require a matching candidate source. Each
relationship is compiled into one 32×32 field and routed independently through
the saved tree. The worker compares each complete returned
branch-position-preserving signed field and exact native slot map with the
candidate memories. It does not replay every candidate's teaching input, average
branches or compute a whole-tree score.

Only exact native returns bind the evidence reader to reviewed RGM passages.
The language reader sees short request-local source aliases rather than the
long authenticated corpus hashes. A supported alias is rebound to the complete
server-owned source ID before exact-span validation; an unknown alias or altered
source still fails closed. This prevents a correct quotation from being lost
because a language model copied a long hash incorrectly without weakening the
source binding.
If the complete language reader declines a broad structural request after an
exact reviewed ToM return, the response is labelled partly supported. It states
only that reviewed structural passages were found and displays all of them; it
does not say the information is absent or convert the structural match into an
unverified direct answer.
Document-style party names such as `Transport for NSW` / `TfNSW` and
`Sydney Metro` / `SM` are matched mechanically. If the question does not state
one complete relationship, ToM makes no selection claim and the existing RGM
candidate path remains available. The bounded insurance evidence check then
verifies the complete linked reimbursement clause; an ambiguous, qualified or
unparsed chain fails closed. ToM supplies persistent structural memory; RGM
supplies exact text and provenance.

MiniLM exits before the fixed local Gemma reader loads. Gemma uses the same
8,192-token prompt bound. The reader now caps allocation at 17 GiB, following
the measured 15.04 GiB peak, and requires another 2 GiB of available headroom.
Competing model processes remain blocked. The optional operator setting
`TOM_ASSIST_RGM_CPU_JOB_PID` permits the previously authorized small Stream1 CPU
test only after checking its command, working directory, loaded libraries and
resident memory (at most 4 GiB); it is not a general process exclusion.
Oversized complete evidence is rejected rather than silently shortened. Final
answers contain source quotations with expandable, highlighted original
passages. Withdrawn or changed documents invalidate an in-flight answer.
No page number is invented for imported text without PDF page provenance.
PDF spacing repair requires independently retained PDF provenance; this import
path currently uses exact imported-text matching and may refuse malformed
extraction rather than repair it speculatively.

The option is off by default. It takes precedence over the earlier frozen
native-memory profile on this explicit answer endpoint when enabled; other
chat/preview/commit paths remain independent. The isolated desktop run now
exercises import, reviewed teaching, shared-source binding and three live recall
questions. It establishes the bounded cross-contract source-linking behavior;
it does not establish general document-answer accuracy or automatic motif
extraction.

Initial app-path check: three of four new questions produced correct outcomes.
The fourth, a reversed repayment question, elicited a wrong supported proposal
from Gemma; the existing repayment-direction check rejected it. The app returned
`blocked`, not the desired clear `not_supported` verdict. Its raw output and
validation reason are retained in the refusal-diagnosis report section. That
initial block remains recorded as a failure. The two-source answer was manually
checked: the source says “deductibles”, correctly answering “excess”; the initial
literal-word check was too narrow and remains preserved.

The bounded repayment repair does not weaken that direction check. For a yes/no
repayment question it can answer **No** only when the question cites exactly one
complete clause, names both parties, and that clause states the exact reverse
direction. The returned evidence is the complete cited clause; ambiguous,
incomplete, uncited and open-ended “which clause” questions still fail closed.
The original APP03 wording now returns “No”, followed by clause 23.5 showing that
TfNSW reimburses SM. This was verified in the actual isolated desktop window and
its source disclosure opens to the same clause.

The experimental project collection is bounded to 512 RGM chunks, matching the
unchanged native capacity. Larger collections are rejected before model work;
no source is silently pruned to make them fit. Changing that bound needs a
separate capacity check. The encoder implementation hash also binds vector
caches, so code changes cannot silently reuse old encoding results.
