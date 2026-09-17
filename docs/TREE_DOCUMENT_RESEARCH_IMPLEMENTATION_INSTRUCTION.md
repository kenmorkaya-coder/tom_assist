# Tree-native document research — implementing-agent instruction

Status: approved for implementation by the owner (“proceed”), 5 September 2026.
Assigned to “ToM Assist 1”. The live-send and other authorization limits below
remain in force.

Owner amendment, 5 September 2026, relayed from the active implementing task:
“you have to push the tree to record docs? did you? also the instruction says
dedicated tree per project, use the 10k 8d/17d tree. don't share structural
territory.” This supersedes the earlier permission to share structural territory.
Each project must own a distinct canonical-10K-derived document Tree and receipt
store. Recording documents applies derived loads to that project's document
Tree; it does not mean a Git push or a change to the experience Tree.

Decision confirmation, 5 September 2026: after clarification that one Tree can
support multiple projects, the owner delegated this choice (“i will go with your
advice on this one”). The recommendation is separate document Trees per project
for independent retrieval behavior and reproducible testing. This is a product
isolation choice, not a claim that the Tree cannot support multiple projects.
Use the same pinned engine, canonical seed and retrieval implementation for all
projects; do not fork the mechanics or duplicate source documents between them.

Migration safeguard: do not create/backfill a legacy project's document Tree as
a side effect of preview, diagnostics, lazy project opening, or ordinary startup.
Expose a migration-required state and use an explicit, versioned migration
operation outside the serving read path. Test on an isolated recoverable copy
first. Do not migrate live SCAW data without separate authorization. Preserve the
legacy shared index and receipts, source/library records, experience Tree, and
canonical seed; any metadata changes must be enumerated, backed up, and approved.

## 1. Outcome and authority

Make Tom Assist answer this question in the actual app, with source-supported
requirements correctly classified:

> What must the contractor do before it starts construction work under the deed?

The acceptance artifact is the new assistant response in the app, not an
evidence preview, a successful build, a test count, or a hand-written answer
inserted into the conversation.

Read `tom_assist_turn.md` completely. Preserve its boundaries: dedicated
Tom Assist 10K-derived document Tree per project; evidence-derived 17D content and pinned
8D routing; document ingestion affects only the document Tree; preview/research
does not mutate either Tree; active-project isolation; permanent source text
and exact offsets; evidence is not authoritative state; explicit sending;
explicit acceptance before experience commit. Do not rewrite that document to
justify an implementation. Read the existing build instructions and their
required references, resolving historical instructions against the owner's
current directions. Never revive obsolete automatic-commit behavior.

Do not implement a parallel search engine, keyword-to-coordinate scheme, new
embedding model, invented Tree scoring formula, or deed-specific production
rules. Reuse the existing pinned Tree's pure retrieval functions. Preserve the
dirty worktree and all documents, historical receipts, and previous builds.
No commit, push, upstream modification, or live provider send is authorized by
this instruction.

## 2. What the evidence establishes—and what it does not

See `docs/TURN_ALIGNMENT_REVIEW_2026-09-05.md` for the reproducible baseline.
The still-running app displays an older 24-unit preview. The unlaunched
verification build contains the later alignment changes.

The historical-branch-overlap gate selects 137 of 1,466 project chunks and
produces ten authored units. **Ten is the result of that product gate, not a
demonstrated limit of the Tree's native retrieval mechanism.**

Three relevant code findings:

1. `gateway/document_tree.py::structural_scores` matches the branch IDs recorded
   during ingestion against the question's current top-32 branch IDs. Branch
   addresses were recorded after successive ingestion batches, while queries
   use the current Tree. Exact historical-ID intersection is not the native
   memory-ranking rule. Whether subsequent Tree growth materially worsens this
   mismatch must be measured, not assumed.
2. The pinned `agency.mechanics.preview_readout` exports
   `rank_by_branch_resonance`. Its implementation in `leaf_vectors.py` accepts
   memory records with an 8D `leaf_vec` and compares them with selected branch
   vectors. Tom Assist's ordinary memory fusion already calls this function.
   Document receipts retain an evidence-derived `routing_basis_8d.vector_8d`.
3. `_expanded_prestart_packet_rows` currently resolves reference targets using
   the already-ranked initial chunk subset. Consequently an exact declared
   reference can fail merely because its target was not an initial hit. Its
   blanket rejection of parents with children also needs examination: a precise
   named clause can legitimately contain several relevant subclauses.

A read-only native-ranking probe used the saved 32 question branches and all
1,466 retained receipt vectors. It returned 1,466 rankings; scores ranged from
0.9996330048826613 to 0.9998757577015814. This proves API compatibility for those
inputs, **not semantic usefulness, correct coordinate conventions, completeness,
or a fixed app**. The narrow spread must be included in the evaluation.

## 3. Implementation sequence

### A. Establish a traceable reference before changing serving behavior

- Freeze a test snapshot: project ID, full source and structure digests, Tree
  digest/tick, runtime pin, address compiler/projection versions, query, budgets.
  Use read-only access or an isolated recoverable copy of live data.
- Build a source-checked requirements fixture. Start with the previously shown
  clauses, then review the retained deed for omissions and dependencies. The old
  24 units are neither ground truth nor necessarily 24 distinct requirements.
  Each expected requirement needs exact source offsets, clause address, actor,
  action, timing/trigger, condition/exception, and its classification rationale.
  Mark unresolved source interpretation for review; do not guess it into gold.
- For every expected requirement, report its fate through source addressing,
  Tree retrieval, clause/reference expansion, classification, packet admission,
  and answer coverage. Separate a missing source from a retained source that the
  retriever missed. Keep source review fixtures out of serving code.

Deliver the baseline and mechanism comparison before any new rebuild.

### B. Replace the invented historical-ID gate with native memory retrieval

- Verify the pinned routing/reading basis contracts against the retained receipt
  vector and actual branch vectors. Do not interchange different 8D bases simply
  because both have eight elements. Reproduce representative calculations.
- Adapt only valid active-project document receipts to the native memory-record
  interface, using their verified retained 8D addresses as `leaf_vec` if the
  basis check succeeds. Keep project and source provenance outside the geometry.
- Select the question region with the existing approved pure Tree mechanism;
  call `rank_by_branch_resonance` through the pinned pure export. Do not copy its
  mathematics into another scorer. Verify output equivalence with a direct call.
- Retain native best-branch, raw score, native rank, query-region identity,
  receipt identity, vector/version, and current Tree digest for each result.
  Historical branch overlap can remain diagnostic, not an admission requirement.
- Remove the overlap-only test assumption introduced in the last alignment
  patch. Replace it with tests requiring an actual native retrieval result or
  an exact-reference expansion from one. Do not restore the earlier independent
  whole-inventory text scan under a new label.
- Missing/invalid addresses fail visibly. Do not manufacture positive channels,
  overwrite original receipts, repeatedly push documents to improve a score, or
  refresh addresses during preview. Any necessary migration requires a separate
  justified, recoverable design before execution.

### C. Separate best-match retrieval from comprehensive review

Keep ordinary questions bounded. For an explicit deed-wide requirements request,
review the native Tree-ranked document results in deterministic batches, rather
than treating the first top-K results as the whole answer.

This is a proposed **coverage policy using the existing retrieval engine**, not
a new Tree mechanism. It deliberately may examine every valid, reachable
active-project document unit. Do not disguise that cost or describe every ranked
record as relevant.

- Rank project receipt metadata through the Tree first. Read/classify source
  text only as Tree-ranked results or justified exact expansions are consumed.
  A direct full-text/regex sweep must not supply extra candidates independently.
- Reuse existing persistence where practical; use the smallest batch/cursor
  representation needed. Do not add a general agent planner, job framework,
  autonomous LLM search loop, or bespoke vector database.
- Bind coverage to the frozen Tree, source inventory, question, and policy
  versions. Deduplicate units. A changed snapshot invalidates the old cursor or
  remains explicitly pinned; it must not silently combine incompatible runs.
- Expose examined, included, excluded-with-reason, unresolved, and unexamined
  counts. Terminate as complete-in-scope only when every in-scope retained unit
  is accounted for. Rank convergence or finding 24 units is not a stopping proof.
- Keep processing and outgoing-packet budgets distinct. If work/time limits are
  reached, preserve resumable progress and say partial. Do not silently truncate,
  increase limits until a fixture passes, or transmit hidden extra context.
- Centralize the broad-query mode decision across gateway and daemon so they
  agree on scope. Provide an explicit UI scope choice if inference is ambiguous.

### D. Follow authored structure and classify requirements, not card counts

- Expand a retrieved hit to its exact authored unit with necessary governing
  actor/condition text. Follow precise references through the project's permanent
  source index even if the target was not in the first page of native matches.
- Preserve a complete provenance chain: native hit and Tree witness → exact
  reference/definition → target document/clause/offsets and target receipt. A
  target's historic receipt does not itself prove that a reference was followed.
- A precisely named composite clause may be read as that bounded clause; do not
  arbitrarily pick its first temporal child or reject it solely for having
  children. Ambiguous/unresolved references remain unresolved. Detect cycles and
  duplicate targets; if a declared traversal limit stops work, record the gap.
- Distinguish project-wide commencement prerequisites, site/access conditions,
  activity/location-specific prerequisites, and timing/trigger exceptions.
  Identify Principal-only duties and historical acknowledgements separately;
  do not turn them into Contractor prerequisites. Preserve shared obligations.
- Represent separate actions inside one clause distinctly. Preserve exceptions,
  waiver conditions, and compound requirements. Do not double-count a requirement
  merely because parent and child excerpts overlap or it has two classifications.
- Prefer existing evidence-bound parsing/classification. When source wording is
  ambiguous, show an unresolved item; do not invent a deed-specific regex or turn
  on the currently disabled semantic/feeling subsystem to force a result.

### E. Put the evidence through the actual app

- Preserve the separate source-evidence block and explicit acceptance gate.
- Show research coverage and budget exclusions before sending. If the reviewed
  requirements do not fit the authorized packet, state that limitation; do not
  call a smaller answer comprehensive. Any multi-send workflow needs explicit
  user authorization and visible packets.
- Tell the answer generator to group supported requirements by the above
  conditions, cite clauses, preserve individual actions and exceptions, and state
  missing referenced material. This instruction must be general, not a hard-coded
  SCAW answer or a private list of expected clause numbers.
- Display build/daemon/policy identity and distinguish prior answers, current
  previews, and unsent evidence. They must not appear to be the same proof.

## 4. Verification and stopping conditions

Use small focused suites first. Do not repeatedly rebuild unchanged code.

Required checks:

- Native ranking equivalence; same-basis validation; deterministic output across
  restart; score-spread/rank-stability analysis. An all-positive result is not a
  relevance test. Report address discrimination problems honestly.
- Preview/research byte-purity for both Trees, including repeated and resumed
  batches. Ingestion remains confined to the document Tree. No automatic
  experience commit from response arrival, PASS, or finding resolution.
- Strict two-project isolation with separate document Trees, including identical
  seed geometry and documents that would occupy overlapping structural regions,
  duplicate content, tombstones, changed snapshots, and exact-reference lookup.
- First preview against unopened legacy data must fail with migration-required
  without changing Tree or library bytes. Explicit migration must be recoverable,
  repeat-safe, and preserve the old index. Verify purity again after migration.
- Requirements split across chunk boundaries; composite undertakings; conditional
  access; precise targets outside the initial page; nested references/cycles;
  malformed OCR; missing schedules; unrelated Principal duties; post-completion
  and historical clauses; overlapping excerpts and evidence budgets.
- Held-out source wording, changed numbering, ingestion order, and additional
  documents. No production clause-ID whitelist, answer fixture, or tuned count.
- Trace the reviewed SCAW requirement fixture end to end. Report misses at the
  stage they occur. Changes to fixture expectations need explicit source-backed
  justification, not adjustment to make a failing test green.

Only after these checks: build one uniquely named verification app, preserve old
bundles/build outputs, verify hashes and service versions, and manually preview
the exact question in the real app against the intended saved project.

The decisive check requires a fresh, explicitly authorized provider send of the
visible packet, question, and bounded history. Earlier send approvals are not
reusable. Without fresh authorization, stop at “ready for live acceptance test.”
Never inject a prepared answer or fixture response as live proof.

Compare the resulting app response with the independently source-reviewed
requirements fixture: coverage, actor, action, timing, conditions/exceptions,
classification, and citations. Every expected in-scope requirement must be
correctly covered, or the test is not passed. Missing external material must
remain explicit. Do not automatically accept the response to produce experience.

## 5. Handoff and escalation

Provide: change summary; native call paths; the source-checked requirements
fixture; before/after per-requirement coverage; text-free trace; test results;
artifact/service identities; screenshot and persisted lineage of the actual
response when authorized; remaining limitations.

Do not declare “fixed” from a build, matching item count, or packet alone. If
native addressing is incompatible or insufficient, report the measured defect
and a bounded proposed repair before inventing machinery. The owner must approve
any changed Tree mechanics, address compiler, new inference service, or broader
transmission workflow. Continue independent safe checks while awaiting that choice.
