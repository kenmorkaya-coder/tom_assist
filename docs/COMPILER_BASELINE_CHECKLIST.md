# Compiler/evaluation baseline lock — 9 September 2026

## Timing and scope

This is a **post-v1-training, post-v1-held-out-exposure repository lock**, not a
retroactive pre-training commit. The original local v1 freeze remains separate.
Its run metadata records training already completed; the parser-v2 documentation
records that v1 held-out output informed the transport repair. No model scores
or predictions were inspected to prepare this lock.

The baseline preserves two distinct experiments, not a validated joined system:

- `typed_matrix_compiler.py` plus `project_identity_matrix_compiler.py`: supplied
  typed events and registry identities, MiniLM semantic fields plus exact symbols.
- `typed_event_graph.py`, extraction validators and `event_graph_compiler.py`:
  paragraph graph experiment with SHA-derived identity encoding, not the same
  MiniLM compiler. Its numerical results cannot inherit the other compiler's gates.

No Tree changes, production wiring, provider call, model inference or threshold
changes are part of this lock. Existing unrelated app edits are excluded.
This preserves the governed/project-local boundaries in `tom_assist_turn.md`;
it does not establish that the app implements the experimental graph pipeline.

## Commit checklist

- [x] Freeze typed compiler, registry identity adapter and their negative tests.
- [x] Preserve v1 extraction parser and separately versioned v2 transport parser.
- [x] Include graph schema, validator, corpus generator and split definitions.
- [x] Keep the small synthetic split files already in Git; exclude model weights,
  caches, external evidence bundles, external datasets and temporary results.
- [x] Keep original compiler and paragraph gates unchanged, including RED rules.
- [x] Record source hashes, split hashes, local freeze lineage and runtime/model
  identifiers in `validation/baselines/compiler-evaluation-20260909.json`.
- [ ] Run the scoped build/validator tests from an isolated index export.
- [ ] Audit the exact staged paths and outgoing commits for excluded artifacts.
- [ ] Commit and push the feature branch without rewriting history.
- [ ] Verify remote HEAD equals the baseline commit and record its full SHA in
  a separate receipt. A commit cannot contain its own SHA without circularity.

The final receipt records completed checks and the actual Git/remote SHA; unchecked
items here are intentional until those actions occur, not assumed successes.

## Required before any future confirmatory training/evaluation

1. Choose and name the exact extractor/compiler pairing. Freeze its prompt,
   schema, binding policy, identity inputs, scorer, thresholds and selection rule.
2. Register a genuinely fresh evaluation split for any change informed by v1
   held-out output. The existing v1 split is a regression set for parser v2,
   not unseen confirmation. Do not relabel diagnostic rescoring as a fresh pass.
3. Freeze dataset and model hashes, runtime versions and training configuration.
   Check train/dev/test separation and record who may access held-out outputs.
4. Commit, push and verify the exact remote SHA **before** the new run starts.
5. Run from an isolated checkout of that SHA. Verify the manifest and pin the
   model/adapter hashes; never evaluate the shared dirty workspace.
6. Record training start/end, selected checkpoint, first inference and first human
   or agent result inspection separately. Stop on hash drift or prior exposure.
7. Score every item under the frozen denominator; missing, unresolved or invalid
   extractions do not vanish. Preserve RED unchanged. Numerical evaluation only
   follows the experiment's extraction gate, not an informal interpretation.

## Historical replay dependencies

The typed/identity runners deliberately retain their original external baseline
and previous-run hash checks. Exact historical replay requires their designated
external inputs and source snapshots. In particular the old run froze a dirty
`gateway/document_ingestion.py`; this commit does **not** absorb those unrelated
production edits. Its different hash is recorded explicitly in the provenance.
Do not weaken that check to make an old run execute from this newer checkout.
The Git lock is reproducible source state, not a claim that every prior runtime
dependency or evidence bundle has been copied into Git.
