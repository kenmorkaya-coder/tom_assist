# Fresh held-out evaluation after development selection

Evaluate exactly the v5 epoch-1 adapter, selected at 992 cumulative training steps
under the predeclared development selection rule. Do not train, alter its weights,
change the prompt/parser/compiler, select another checkpoint, or retry failed
generations during this experiment. Preserve prior runs and their results.

The new authored battery has 132 unique passages, 44 groups and 20 semantic
families. Each group contains a canonical requirement, a meaning-equivalent
paraphrase and a critical contrast. Comparison bounds cover all six operators,
including zero and negative values. Other families cover quantities, polarity,
recipients versus issuers/actors, exceptions, nested conditions, cause direction,
event order, revisions/supersession, dates, hypothetical approvals, conflicting
rules, unit equivalence, multiple thresholds and linked paragraph events.

Wording is newly authored with fresh entity identifiers and principal values;
exact source overlap with every v1/v3 train/development/held-out inventory is
forbidden. All 132 source strings must be distinct. Semantic ontology and family
structure are intentionally shared. The author has seen previous failure classes,
but neither labels nor wording are model-generated outputs. This is a fresh
synthetic held-out battery, not an independently authored or naturalistic project
document test. Shared family templates remain a generalisation limitation.

Validate all authored graphs, exact source spans, wire binding, paraphrase
equivalence and contrast differences before inference. Freeze the generator,
entire corpus, evaluation driver, this plan, tests, parent session manifest and
selected adapter hash before the first model call. Record source commit timing
honestly. Verify inherited model/source/data hashes at every stage.

One native-prompt generation per row, temperature zero, seed 7, maximum 4096
tokens; no retries, cleanup beyond the frozen v3 parser, action remapping, evidence
repair or post-score canonicalization. Invalid outputs remain in denominators.
Use the unchanged scorer and thresholds: 100% valid resolved graphs, 95% exact
overall, 90% exact in every family, zero invented authorities detected by the
scorer, 95% paraphrase agreement, 100% critical contrast distinction. Keep full
family and error counts. Small six-item families effectively require all correct.
The scorer's authority count applies to validated graphs; invalid graphs already
fail the validity gate. Its aggregate error details may mask the parser's original
error; original prediction records preserve it for separate diagnosis.

Formally read the complete aggregate after verifying adapter/prediction hashes,
reparsing raw outputs and reproducing all metrics. Only extraction GREEN may
advance to the existing experimental numerical discrimination gate. A numerical
pass still requires original regressions and independent review before Tree.
No inherited MiniLM+symbol compiler result, production change or Tree claim.
On extraction RED, preserve the result and diagnose without repairing this test
or treating its now-exposed examples as unseen in another version.
