# Tom Assist Capability

**Status:** living capability reference  
**Last updated:** 18 September 2026

This document states what Tom Assist can do now, what has only been proved in a
bounded experiment, and what has not yet been established. It is deliberately
separate from [tom_assist_turn.md](tom_assist_turn.md), which is the chronological
record of how the work was performed, and [BUILD_LOG.md](BUILD_LOG.md), which is
the implementation and verification ledger.

## Capability labels

- **Available:** implemented in the application and covered by repository checks.
- **Bounded:** implemented and demonstrated for the named structures and data;
  it is not yet a general capability.
- **Shadow:** measured or recorded without controlling the user-facing result.
- **Not established:** no current product claim.

## What Tom Assist is for

Tom Assist keeps project state, prepares relevant context before a message is
sent, records what was actually sent and received, and checks the resulting
answer against the project's evidence and decisions.

For document questions, the current division of labour is:

```text
question
   ↓
Reflection-Gated Memory (RGM)
finds and retains exact passages, text and provenance
   ↓
ToM structural memory
recognises reviewed relationships, direction and event order
   ↓
RGM source resolution
reopens every exact source linked to the returned structure
   ↓
evidence checking
decides supported, partly supported, unsupported or ambiguous
   ↓
language model
words only what the evidence layer permits
```

RGM is not treated as a simple vector database. It provides persistent governed
memory, contextual retrieval, source provenance, structured snapshots and
document ingestion. ToM adds persistent, position-sensitive structural memory
where exact wording alone does not reliably identify a relationship or a
sequence of events.

## Non-negotiable tree representation rule

Tom Assist does **not** average or collapse a learned tree return into one
whole-tree score for the structural-memory capabilities described below.

It preserves:

- native branch identity and branch order;
- every signed 32×32 branch field;
- native memory-slot identity;
- selector values and activated locations; and
- the exact source pointers bound to the learned structure.

Complete returned fields and exact slot maps are compared like for like.
Counts, plots and branch magnitudes are display telemetry only.

## Current capability matrix

| Capability | Status | What it currently does | Boundary |
| --- | --- | --- | --- |
| Project-local state | Available | Keeps objectives, decisions, constraints, rejected paths, completed work, unresolved dependencies and evidence inside the active project. | Nothing carries between projects. |
| Event-sourced history | Available | Records changes without overwriting the earlier record; supports replay, snapshots, export, import and supersession history. | A recorded rejection is not yet used to suppress the same suggestion later. |
| Governed message preparation | Available | Holds a draft, prepares bounded project context, and sends only after the user allows it. | Provider behaviour remains external to Tom Assist. |
| Read-only preview | Available | Reads current state and tree-derived context without advancing the tree or memory clock. | A committed sent turn is required before experience learning occurs. |
| Experience-tree learning | Available | A committed turn changes the project's experience tree; draft inspection does not. | The tree does not store the literal transcript. |
| Local document library | Available | Stores imported source text, chunks, source offsets, checksums and project-local provenance. | Imported text without PDF provenance does not receive invented page numbers. |
| Exact evidence answering | Available in the opt-in document path | Returns source quotations and expandable original passages, with exact-span and source-integrity checks. | Oversized or altered evidence is rejected rather than silently shortened or repaired. |
| Multiple supporting sources | Available | Keeps and displays every exact source linked to an accepted answer or reviewed structural memory. | The evidence reader may still decline broad questions even when relevant structural sources were found. |
| Conflicting sources | Available | Shows both sides with provenance and returns an ambiguous result while authority is unresolved. | Neither ToM nor the language model silently chooses a winner. |
| Explicit source authority | Available | Lets the user record that one exact source supersedes named older sources, with time and reason, while retaining the older evidence. | Authority is never inferred from filenames, dates or amendment wording. |
| Relationship direction | Bounded | Distinguishes who acted on whom in the reviewed mirrored insurance relationships. | Demonstrated on two clauses and four questions, not arbitrary relations. |
| Event-order memory | Bounded | Distinguishes records containing the same entities and actions in a different order. | Demonstrated with supplied temporal links; automatic temporal extraction is not established. |
| Shared structural memory | Bounded | Learns a reviewed structure once and binds exact evidence from several source locations without teaching the tree again. | Supported for the admitted structures listed below. |
| Structural source recovery | Bounded | Reopens exact RGM passages from a learned structure even when ordinary RGM retrieval supplies no correct initial candidate. | Requires an already reviewed and learned structure. |
| Structure review queue | Bounded | Runs the copied RGM contextual-vector and native-vector passes, fuses their rankings, scans every active chunk with the admitted regex rules, then shows only passages that pass strict local event-order validation. | Semantic/vector hits alone cannot teach the tree; every source still requires explicit review and Save. |
| Dense 17-channel prose loading | Shadow, default off | Extracts evidence-bound structured candidates and records diagnostics. | Ordinary prose still leaves too many channels empty for authorised tree admission. |
| Outcome memory | Capture only | Records what context was offered and what the user actually used. | Nothing reads this history yet. |

## Proven structural-memory capabilities

### Directional relationships

Two near-identical insurance clauses were used to isolate relationship
direction. RGM retained the correct source in all eight candidate sets and put
it first in six. RGM plus ToM selected the correct relationship in **8/8** cases,
including both reversed-direction cases that RGM ranked incorrectly.

The two learned relationships wrote to 381 and 387 different native
branch/slot locations with zero overlap. Reversing the teaching order did not
change which relationship opened. An untrained tree opened none.

### Event order

Two controlled records contained the same entities, actions and word bag but a
different event order. Their native RGM vectors were equal, so RGM ordering
followed insertion order and was correct in **4/8** trials. The two ToM
temporal memories selected the correct order in **8/8** trials. The untrained
tree selected nothing.

### One structure, evidence from several locations

Interface Agreement clause 11 and D&C Deed clause 31 both contain the reviewed
sequence:

```text
written notice → meeting
```

Across three structural questions, ordinary RGM retrieval returned only one of
the six expected source occurrences in its candidate lists and never returned
both sources together. One ToM memory reopened both exact source pointers for
all three questions: **6/6 expected occurrences**.

The first reviewed source taught the distributed memory. Reviewing the second
source added its provenance with **zero additional tree writes**.

### Recovery when ordinary RGM retrieval misses

A second admitted structure is stored as two independent ordered memories:

```text
required action fails
    → another party performs the action
    → the resulting cost is recovered
```

The frozen 512-chunk RGM corpus contained the target passages, but three
structure-only questions retrieved neither passage. The reviewed ToM path
reopened both exact passages for all three wordings.

The decisive control supplied **zero RGM candidates**. ToM still returned the
reviewed M12 clause 14.4 and D&C clause 13.6 source locations, restored their
exact passages from RGM, preserved the two complete distributed returns, and
left the saved tree unchanged.

After D&C clause 16.7 was explicitly reviewed and attached to the same learned
structure, the same zero-candidate control returned all three source locations.
The attachment made zero tree writes and did not change the tree or checkpoint
hash.

### Unseen third-document check

The previously unused Noise and Vibration Construction Environmental Management
Plan supplied a third reviewed notice-before-meeting source. Its full 205-chunk
RGM corpus contained the target passage, but ordinary RGM did not return that
passage for any of three fixed structural questions.

After explicit review, the new source bound to the existing distributed memory
with zero tree writes. RGM plus ToM returned all three reviewed notice sources
for **3/3** questions. The same **3/3** result held with an empty initial RGM
candidate packet. The complete branch-local signed 32×32 return and native slot
map were compared each time; the 242.5 MB tree remained byte-for-byte unchanged.

The diagnostic first exposed two access defects: plural `meetings` was absent
from the bounded grammar, and the notice memory required an initial RGM hit even
though the ordered query itself identified the reviewed structure. Those defects
were repaired independently before the successful rerun. Party and repayment
memories remain candidate-gated.

This result is limited to one new document, one already learned structure and
three question wordings. It does not establish automatic structure discovery or
general accuracy on unseen documents.

### Different project family and different sequence

The next check used the five-page Middleton planning mitigation document rather
than Sydney Metro contract material. Its reviewed procedure states:

```text
human remains discovered
    → nearby work stops and the area is secured
    → Police and Heritage NSW are notified
```

RGM retrieved the passage for both correct structural questions. It also
retrieved the same passage for the reversed question and for the false request
to continue excavation after human remains were found. RGM therefore supplied
strong topic access but did not enforce the event order or the stop-work state.

A fresh copy of the approved circa-500-branch tree learned the two ordered
relationships. ToM recalled the exact source for the correct pair and complete
chain, rejected the reversed order, and did not admit the absent continue-work
structure. The correct pair used one native route and the chain used two. Each
route compared the complete signed branch-local 32×32 return and exact native
slot map. No whole-tree score or branch averaging was used.

The learned tree contained 513 branches and 393 terminal return branches. Its
233,213,726-byte checkpoint, state hash and 6,091,380-byte full-field reference
archive were identical before and after all recall checks. The large artifacts
remain on Passport. This is one explicitly reviewed procedure, not evidence of
automatic event extraction or general planning-document understanding.

The same reviewed structure was then exercised through the live answer path.
The first run failed: the tree rejected the reversed and absent relationships,
but the final evidence reader treated the topically relevant RGM passage as
support anyway. The fault was therefore at the final evidence boundary, not in
the tree return.

The repair makes a reviewed opposite relationship authoritative at that
boundary. Tom Assist reopens the exact bound RGM source and returns a sourced
No without calling the language reader or the tree again. On the repaired run,
the correct-order question returned the exact source through one complete
distributed ToM recall. The reversed-order and false continue-excavation
questions both returned `not_supported`, showed the same exact source, made
zero language-model calls and made zero tree calls. Conflicting sources remain
a separate case and are still all displayed.

### Explicit review before learning

The Memory screen exposes **Structures to review** for two bounded structures:

- failure, substitute action and cost recovery; and
- human remains discovered, work stopped and authorities notified.

The scan:

- reads only active authenticated RGM chunks;
- runs the RGM contextual vector pass and native vector-store pass;
- combines those rankings with Reciprocal Rank Fusion;
- independently runs the source regex over every active chunk;
- requires the exact local events in the required order after joining those
  discovery channels;
- shows the exact passage and the three locally matched event phrases;
- makes zero tree calls;
- performs no automatic learning; and
- repeats source-local validation when the user chooses Save.

A second source document, the Middleton Aboriginal Cultural Heritage
Assessment, expresses the same procedure as `immediately cease all works`.
The first read-only scan found zero candidates across its 42 RGM chunks. The
cause was narrow and visible: the bounded source grammar accepted `stop` but
not `cease`. Adding only the `cease all works` wording exposed the procedure in
the document summary and in the main recommendation.

The main recommendation was reviewed and attached to the two existing learned
relationships with **zero new tree writes**. One actual two-route ToM recall
then reopened the exact Appendix C and Appendix AB passages together. The
513-branch checkpoint, complete signed 32×32 reference fields and state hash
were unchanged. This establishes bounded shared-source binding across two
differently worded documents; it does not establish general paraphrase parsing.

On the two frozen contract corpora, the local-procedure detector found 12 valid
passages across 563 native chunks. Nearby clauses lacking substitute
performance and a deliberately separated phrase control were rejected. This is
a bounded source-admission rule, not a general structure extractor.

The integration was checked on the unchanged 42-chunk Appendix AB document.
The native RGM vector pass ranked the two valid human-remains passages at 2 and
1, and Reciprocal Rank Fusion placed them at 1 and 4. The contextual pass found
one at rank 4. The full-source regex/order check found and validated both. A
control passage containing related words without an ordered local procedure was
found semantically and rejected before review. The queue made zero tree calls
and performed no automatic learning.

A larger bounded check then used the production RGM file-ingestion path on 611
real chunks across the complete M12 agreement, D&C Deed and two Middleton
documents. It recovered all 15 previously hand-inspected valid passages and
produced no additional candidates. Semantic return alone contained 7 of those
15, the contextual vector top ten contained 7, the native vector top ten
contained 8, and Reciprocal Rank Fusion contained 9. The full-source regex and
local-order validator recovered all 15. Four related negative passages were
returned semantically and all four were rejected before review. This is a
bounded regression result over the already inspected structures, not general
document accuracy.

## Evidence and answer behaviour

The evidence layer can return four materially different results:

- **Supported:** the selected source directly supports the answer.
- **Partly supported:** an exact reviewed ToM structure found relevant sources,
  but the reader could not verify a complete direct answer.
- **Not supported:** the required evidence is absent from the supplied sources.
- **Ambiguous:** available sources conflict or more than one interpretation
  remains valid.

Conflicting sources do not stop the answer. Tom Assist presents all conflicting
and currently bound passages. It does not combine fragments from opposing
sources into a fabricated answer.

The language model receives request-local source aliases. The gateway binds an
accepted alias back to the complete server-owned source identity before the
answer leaves the application. Unknown aliases, altered text and invalid source
spans fail closed.

## Current admitted structures

The live reviewed bridge currently supports:

1. the bounded mirrored insurance relationships used for party and repayment
   direction;
2. reviewed notice before a meeting;
3. failure before substitute action, followed by substitute action before cost
   recovery; and
4. human remains discovered before work stops, followed by work stopping before
   authority notification.

The two three-event structures are represented by two independently routed
learned relationships. Both complete distributed returns and both exact slot
maps must match before their source reopens. Both structures are exposed by the
desktop review queue and still require an explicit per-source Save.

## What is not established

Tom Assist does not currently claim:

- automatic discovery or automatic teaching of arbitrary structures;
- reliable parsing of arbitrary event graphs from ordinary prose;
- general document-question accuracy across unseen document classes;
- that ToM should store names, dates, amounts or clause wording better than RGM;
- that one branch count, averaged branch response or whole-tree scalar explains
  retrieval;
- that a relevant structural source automatically proves every word in a broad
  question;
- learning or retrieval across project boundaries;
- age-based forgetting or recency weighting;
- automatic use of previously rejected suggestions; or
- authority resolution without an explicit user decision.

The intended split is that RGM retains exact detail and provenance while ToM
retains reviewed relational and temporal structure. ToM should help RGM find
the right situation and its connected sources; it should not duplicate RGM's
high-resolution document memory.

## Operational status

The RGM plus ToM document-answer path is opt-in. It does not replace the normal
conversation prepare, send, evaluate or commit paths. Query-time structural
recall does not train the tree. The current implementation uses the approved
small Stream 1 tree for bounded testing and keeps large checkpoints and full
field archives outside Git on the Passport drive.

The earlier integrated review-queue verification recorded:

- **252** relevant gateway tests passing;
- **19** desktop tests passing;
- TypeScript checking passing; and
- the production desktop interface build passing.

These counts describe the relevant integration suite at the recorded revision;
they are not a general accuracy score.

The later unseen-document access repair passed all **144** native-memory tests.
The read-only review accuracy repair passes all **152** native-memory tests. The
desktop suite passes **20** tests, TypeScript checking passes, and the production
desktop interface build passes.
The broader gateway run recorded 595 passes, one expected skip, one unrelated
event-graph fixture-overlap failure, and five sandbox-only local-socket setup
errors. The affected OAuth file passed **8/8** when rerun with local socket
binding available.

## Evidence locations

Compact and reviewable evidence is retained in the repository:

- [tom_assist_turn.md](tom_assist_turn.md) — chronological findings, failures,
  corrections and live checks;
- [BUILD_LOG.md](BUILD_LOG.md) — work-package implementation and verification;
- [gateway/README.md](gateway/README.md) — gateway behaviour and operating
  boundaries;
- [validation/runs/stream1-native-learned-recall.json](validation/runs/stream1-native-learned-recall.json)
  — immutable native-memory result sections; and
- [validation/runs/rgm-tom-unseen-document-generalisation.json](validation/runs/rgm-tom-unseen-document-generalisation.json)
  — compact third-document RGM-versus-ToM result; and
- [validation/runs/rgm-tom-middleton-sequence-generalisation.json](validation/runs/rgm-tom-middleton-sequence-generalisation.json)
  — compact different-project-family order-discrimination result; and
- [validation/runs/rgm-tom-middleton-live-answer.json](validation/runs/rgm-tom-middleton-live-answer.json)
  — initial live-answer failure, repaired end-to-end result and differently
  worded shared-source binding; and
- [gateway/tests/test_native_memory.py](gateway/tests/test_native_memory.py) —
  source binding, structural recall, conflict and evidence-boundary checks.

Large tree checkpoints and complete distributed fields remain outside Git under
`/Volumes/My Passport for Mac/tom_assist_test_results/native_learned_recall/`.
They are evidence artifacts, not application source.

## Next capability gates

The next work should extend capability one variable at a time:

1. Exercise conflict and explicit-authority handling for this temporal motif.
2. Keep exact evidence selection and conflict presentation separate from
   structural recall.
3. Do not introduce branch averaging, a whole-tree score or automatic teaching
   to make a failed result look successful.
