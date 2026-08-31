# WP-22: structural warnings and optional provider proposals

Implementation evidence only. No G-gate verdict or measured efficacy claim.

## Structural guardrails

Production response evaluation projects exact response spans and authoritative
guardrail object text with `gateway.structural_preview.project_text(...)[1].vector_8d`,
the same pinned 8D projection used for response teaching. It calls upstream
`agency.mechanics.preview_readout.rank_by_branch_resonance` on those vectors.
It does not retrieve plastic memory, activate/rotate branches, step the engine,
teach leaf vectors, update front-row residency, or mutate the permanent library.
Object anchors are ephemeral read-only projections, not new RGM writes.

Scope is the snapshot-consistent project ledger, including objects excluded by
packet budget: active constraints, rejected paths, and active/satisfied completed
work. Project-wide objects and the attached workstream are eligible; candidate,
superseded and archived objects are not. A stale native snapshot follows the
existing REVIEW path without silently substituting new state.

`guardrail-resonance/1` uses cosine >= 0.98, one highest-scoring exact span per
object, deterministic object-ID ordering and earliest-span ties. Span slices are
at most 320 Unicode characters. Text/anchor limits fail explicitly rather than
silently ignoring tail objects. The threshold is an uncalibrated prior. The native
coarse projection is not a semantic embedding and can collide for unrelated text;
even agreement with a constraint can resonate. These are **possible** violations
or revivals, always warning/REVIEW, never blocking merely from similarity.
Cosine is reported separately from heuristic confidence. Direct ledger rules
continue to supply their independent findings. The matched source quote and
object ID/text appear in the saved summary, with the full intervention (including
response excerpt and evidence turn IDs) in the local audit log. Review resolution
uses the existing explicit user actions and accepted-exchange commit policy.

## Default-off provider self-report

The daemon reads `TOM_ASSIST_PROVIDER_SELF_REPORT=1` at startup; all other values
leave the feature off. No flag change, status query, preview, ordinary chat send,
evaluation retry, restart or import initiates a self-report. With the flag enabled,
a captured exchange exposes **Preview self-report request**, then **Send one
self-report request**. This second send confirms a hash of the exact visible
prompt containing the captured request/response and project ledger. No silent
second call is attached to an ordinary send. The prompt has a 48,000-character
limit and stale-state sends are rejected; an oversized/stale draft is not sent.

Transport is the unchanged OAuth adapter -> owner's connected runtime -> existing
OpenAI client/auth profiles. No auth implementation, token storage, model choice,
concurrency increase, generation retry or schema-enforcement capability is added.
JSON is requested in the prompt, then strictly validated locally; provider-side
strict structured-output support is **not claimed**. The service durably claims
at most one follow-up per exchange before calling the adapter. Lost replies,
interrupted claims and verifier failures are not automatically resent. Upstream
internal retries remain upstream-owned; `logical_calls_claimed` is not a billable
request/token counter.

This distinction follows the [official Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs): a request for JSON does not itself establish schema adherence. A stale, still-unsent request can be explicitly refreshed and re-previewed; any previously approved hash then fails. Once claimed it cannot be refreshed or resent.

The envelope is `{"candidates": [...]}` (0..8). Each entry uses the fixed candidate
keys `candidate_id`, `project_id`, `source_turn_ids`, `proposed_by`, `operation`,
`object`, `tom_check`. IDs/provenance are server-bound; candidate IDs use supplied
deterministic UUID slots. The object keys are `type`, `title`, `canonical_text`,
`status`, `confidence`, `evidence_ids`, `target_state_id`, `reason`. Only DECISION,
CONSTRAINT, REJECTED_PATH, COMPLETED_WORK are allowed; CREATE/UPDATE/SUPERSEDE/REOPEN
remain proposals. Targets must be same-project/same-type, in a suitable status;
supersession/reopen require a reason. No invented evidence is admitted.

The existing upstream reasoning-structure adjudicator checks source dependency,
candidate-only authority, explicit confirmation, target/reason constraints and
invented-evidence flags. This is a declared-structure boundary, **not semantic
verification that the report truthfully describes a change**. Accepted outputs
are stored only in `state_mutation_candidates` as `provider_candidate`, proposed,
`tom_check.result=review`, with confirmation required. They do not change native
state version, the response badge, or any of the five runtime dynamics. Accuracy
labels do not promote candidates; the normal owner capture/supersession workflow
remains separate.

Instrumentation separates received/emitted candidates, shape-invalid batches,
adjudicator attempts/results/rejections and verifier failures. Precision is
`accurate / (accurate + false_positive)` from explicit owner labels only; null
before any labels. Unreviewed counts and review coverage are shown. Adjudicator
acceptance is not used as a precision label. Reports, candidates, prompts,
adjudication traces and labels persist/recover through complete project archives;
WP-20 and WP-21 archive inventories remain supported.

### Audit debt: existing source-ID format

WP-21 stores actual chat turn IDs as `<exchange-id>:assistant`, while the original
published candidate JSON Schema describes source turn IDs as UUIDs. This pathway
preserves those exact ledger IDs rather than inventing UUID provenance or
renaming existing turns. The fixed candidate keys and server bindings are checked,
but full UUID-format conformance for these existing chat IDs is not claimed.
Owner audit is needed before changing that shared schema/ID convention. The
experimental feature remains default-off.
