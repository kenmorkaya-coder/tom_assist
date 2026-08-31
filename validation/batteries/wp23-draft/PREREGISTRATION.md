# DRAFT-PENDING-OWNER-FREEZE — WP-23 pre-registration proposal

Version `wp23-prereg-draft/1`, 1 September 2026 (Australia/Sydney). Owner signature,
freeze SHA, execution configuration and live authorization: **NOT ISSUED**. Runs:
**none**. Numbers below are draft pilot choices requiring owner review, not
substituted specification gates. This document makes no efficacy/G-gate verdict.

## Scope and source convention

Spec v1.2 §18.2.1: typed project-level action consistency, SUB-A/B/C/D/E, no Layer 2
router/expert bias. WP-22 self-report stays **off** in the primary comparison:
no extra call, repair, correction resend or post-hoc answer selection. Studying
self-report later needs its own frozen plan and explicit quota authorization.

Hypothesis names follow Appendix A, printed pp. 20–21 of the owner-supplied paper
`/Users/kenmorkaya/Desktop/sicd_three_mode_arxiv.pdf`, SHA-256
`8fabb62fad65df4926044bbb4958a86bf74db5277845e9409c1be996c55eb238`:
H1 primary, H0 null, H2 partial, H3 new failure mode. Text and rendered page 21 were
inspected. The paper's Gemma 4 26B 4-bit MLX/20-case/64K results do not transfer to
this product/provider/corpus. Only the pre-registration convention is reused.

## Design fixed in this draft

132 cases, **12 per each of 11 focus families**: OBJECTIVE, CONCEPT, DECISION,
CONSTRAINT, REJECTED_PATH, COMPLETED_WORK, UNRESOLVED_DEPENDENCY, EVIDENCE,
ASSUMPTION, SUPERSESSION, WORKSTREAM. Every case also plants all canonical types.
Each family contains two cases each of truncation, cross-session continuation,
explicit supersession, paraphrase revival, dilution/distraction and no-rot.
Long subset: 110 cases (10/family), 120/144 turns. Controls: 22 (2/family), 15 fully
visible turns. No family may be dropped or offset by another's fact-recall score.

Plants are distributed across long histories. Explicit owner revisions update
method/definition with a reason and retain old objects; later assistant proposals
are not authority. Alternatives revive rejected approaches in different language,
repropose completed work, substitute goals, ignore dependencies, or overstate
evidence. Goals/subgoals, constraints, scope and relationships must survive together.
Twelve fictional domains are reused across families: templated cases are correlated,
not 132 independent replications. This small pilot is not an independently authored
holdout or a power-supported efficacy study.

Supersession-slice cases reiterate the authorized revision in the last three
visible turns, isolating acceptance of legitimate change from missing context.
Paraphrase-slice cases place the unauthorized revived suggestion in the penultimate
visible turn. Truncation/cross-session slices withhold the old transcript; dilution
retains the full distracting history. Short controls contain no drift.

The history and question are identical across arms. SUB-B's generous conventional
summary retains needed facts and IDs, avoiding a rigged baseline. SUB-C/D use
matched content in prose/authoritative framing. SUB-E receives stale version-1
statuses or another project's IDs; exposed lineage can itself enable containment,
which is not proof of structural retrieval efficacy. WP-11 renderers are fixture
input adapters, not evidence of production-arm equivalence.

After a separate owner freeze, proposed execution is one initial capture per
case/arm with no best-of/repair selection. Case order: lexicographic `test_id`;
arm order rotates by case index modulo five. Pin model/provider/version, exposed
temperature/seed (otherwise record unavailable), context/token limits, adapter,
runtime, policies, renderer, code and corpus SHAs. A full first pass would require
132 × 5 = 660 logical generations **if later authorized**. This is not a quota
authorization. No calibration or freeze preparation may spend quota now.

## Hypothesis slots — all unexecuted proposals

**H1 (primary).** On long cases, SUB-D improves macro-averaged exact action
consistency by at least **0.15 over each of SUB-A and SUB-B**, both paired 95%
intervals exclude zero, and SUB-D is at least **0.80 in every focus family**.
Macro means the mean of 11 family rates (denominator 10 each). A strong decision
score cannot rescue weak concepts, goals, constraints or relationships. This
pilot criterion is not a statement that G16 or any other product claim is earned.

**H0 (null).** Any primary component does not hold. Record each failed component
without switching baseline, subset, margin or outcome. Missing paired data blocks
the primary interpretation; an invalid/incomplete study is explicitly invalid,
not scientific proof of the null. No post-hoc rescue framing.

**H2 (partial).** H1 holds but any attached secondary expectation does not:

1. No-rot SUB-D action rate is no more than **0.05** below SUB-A and **zero**
   gratuitous packet injections occur. Missing injection telemetry is unresolved,
   never success. The two controls per family support only descriptive slices.
2. Long-case SUB-D is no more than **0.05** below SUB-C. Report enumeration/history
   replay and answer-format failures separately; length is not proof of framing.
3. SUB-D exceeds SUB-E in actual action accuracy by **0.10**, or SUB-E explicitly
   contains wrong/stale lineage on at least **0.80** while SUB-D action accuracy
   is at least **0.80**. Separate these mechanisms; a metadata alarm does not
   establish structural-retrieval causality.
4. SUB-D exact action/relationship consistency is at least **0.80** in the
   supersession slice. Report correct new state, preserved old IDs and correct
   supersedes/refines direction separately, including any false blocking of change.

**H3 (new failure mode).** A reproducible failure outside the fixed taxonomy below
is retained with raw capture, lineage and pins. This flag may coexist with the
primary/partial finding; it cannot erase that result or retroactively expand the
taxonomy to salvage H1. Stop for owner review before targeted tuning/reruns.

## Oracle and analysis

`answers/*.jsonl` pre-registers the exact independent key. The stdin/stdout oracle
compares a separately captured answer, never searches context or generates one.
Primary action success requires all seven fields: action, rejected alternatives,
current citations, retained historic IDs, directed relationships, no mutations,
ledger-only authority. Dict key order is immaterial; values/list ordering are
exact, as declared in each question. Useful free prose can still be a format
mismatch under this narrow draft; no post-hoc semantic judge is allowed. Component
scores separate wrong next actions from syntax/citation mistakes.

SUB-E's exact current-state request is containment, **not** primary action success;
never compute action rates from the oracle's `observed_match` union. No-rot packet
policy is a separate measured boolean, null when unmeasured. Self-report precision
and structural-warning precision are not measured by these answer fixtures.

Report numerator/denominator per arm/family/slice/domain, including all allocated
IDs, malformed outputs, timeouts, disconnects, captures and lineage mismatches.
No silently discarded cases. An incomplete matrix blocks efficacy interpretation
and requires owner review; missing observations are not successes. Unknown
provider outcomes must not automatically be resent.

Draft statistics for a later complete matrix: absolute rates with Wilson 95% CIs
(descriptive under clustered templates); paired differences with **domain-cluster
bootstrap**, 10,000 resamples, seed **1729**. Preserve all case/arm pairings inside
sampled domains, then macro-average by family. A replicate lacking a family's long
cases is invalid and its count reported, not silently converted to IID case
bootstrap. Twelve clusters are a serious uncertainty limit. Publish the raw paired
matrix and every domain/family rate; no significance-only selective reporting.

Fixed draft failure taxonomy: wrong action; rejected-path revival; completed-work
reproposal; constraint violation; objective/workstream substitution; dependency
ignored; supersession/history loss; wrong relationship direction; evidence
overstatement/assumption promotion; unauthorized mutation; enumeration/format
failure; capture/lineage mismatch; operational failure. Unexplained new mechanisms
trigger H3, not a relabelled success.

## Freeze prerequisites, stops and artifacts

Owner must audit source/materialized hashes, labels and domain realism, context
pressure, baseline fairness, native state import/provenance and actual arm runner,
criteria/statistics, model/quota budget, consent and run pins before a separate
freeze and before any live use. Freeze alone does not imply missing production
runner/injection telemetry exists. Cross-session input recipes are not evidence
of real restart execution. No native fixture import is implemented by WP-23.

After freeze: no key/threshold/seed/comparator/exclusion changes in response to
results. Corrections require a new version before a new run, retaining the old
artifacts. Stop on wrong-project disclosure, missing consent, credential exposure,
unexpected calls/retries, quota boundaries, corrupted key/oracle, or unknown H3
mechanism. Preserve partial traces and seek owner direction; never silently repeat.

Required future artifacts (none produced here): frozen code/corpus/run manifest;
visible inputs/raw bounded responses and digests; ordered request IDs; project,
session, native-state, checkpoint and packet lineage; oracle inputs/outputs;
generation counts/settings; packet injection/overhead telemetry; per-family/slice/
domain counts and taxonomy; paired matrix and statistics seed; Appendix-C-style
report preserving null/partial/new failures. The draft manifest has
`owner_frozen:false`, `runs:[]`, and no verdicts.

**DRAFT-PENDING-OWNER-FREEZE. Stop for orchestrator audit.**
