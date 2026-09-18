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
| Structure review queue | Bounded | Scans authenticated RGM chunks for the admitted failure/action/cost pattern, shows exact trigger phrases, and requires an explicit Save for each source. | Scanning is read-only and cannot teach the tree automatically. |
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
written notice → required meeting
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

### Explicit review before learning

The Memory screen exposes **Structures to review** for the bounded
failure/action/cost structure. The scan:

- reads only active authenticated RGM chunks;
- shows the exact passage and the three locally matched event phrases;
- makes zero tree calls;
- performs no automatic learning; and
- repeats source-local validation when the user chooses Save.

On the two frozen contract corpora, the local-procedure detector found 12 valid
passages across 563 native chunks. Nearby clauses lacking substitute
performance and a deliberately separated phrase control were rejected. This is
a bounded source-admission rule, not a general structure extractor.

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
2. written notice before a required meeting; and
3. failure before substitute action, followed by substitute action before cost
   recovery.

The last structure is represented by two independently routed learned
relationships. Both complete distributed returns and both exact slot maps must
match before their shared sources reopen.

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

The latest integrated review-queue verification recorded:

- **252** relevant gateway tests passing;
- **19** desktop tests passing;
- TypeScript checking passing; and
- the production desktop interface build passing.

These counts describe the relevant integration suite at the recorded revision;
they are not a general accuracy score.

## Evidence locations

Compact and reviewable evidence is retained in the repository:

- [tom_assist_turn.md](tom_assist_turn.md) — chronological findings, failures,
  corrections and live checks;
- [BUILD_LOG.md](BUILD_LOG.md) — work-package implementation and verification;
- [gateway/README.md](gateway/README.md) — gateway behaviour and operating
  boundaries;
- [validation/runs/stream1-native-learned-recall.json](validation/runs/stream1-native-learned-recall.json)
  — immutable native-memory result sections; and
- [gateway/tests/test_native_memory.py](gateway/tests/test_native_memory.py) —
  source binding, structural recall, conflict and evidence-boundary checks.

Large tree checkpoints and complete distributed fields remain outside Git under
`/Volumes/My Passport for Mac/tom_assist_test_results/native_learned_recall/`.
They are evidence artifacts, not application source.

## Next capability gates

The next work should extend capability one variable at a time:

1. Test the frozen reviewed structures on genuinely unseen contracts and
   wording, without changing the tree or selector.
2. Measure false positives and misses in the read-only review queue before
   admitting another structure.
3. Add a new reviewed structure only after its source-local recognition,
   native distributed return and destructive controls are independently proven.
4. Keep exact evidence selection and conflict presentation separate from
   structural recall.
5. Do not introduce branch averaging, a whole-tree score or automatic teaching
   to make a failed result look successful.
