# Evidence-bound matrix-event GPT comparison

Status: **FROZEN — OWNER AUTHORISED FOUR EXPLICIT GPT CALLS**

Frozen on: 2026-09-08 Australia/Sydney

The cached local Gemma diagnostic completed with zero matrix-bearing passages.
This minimal comparison sends exactly two SCAW passages and two predeclared
questions through Tom Assist's existing OAuth structured-output pathway using
the same evidence-bound matrix-event schema. It does not rerun Gemma and does
not tune the schema from provider output.

The exact external corpus reference, two passage IDs, two questions, relevance
IDs, maximum four calls, matrix formula and Tree limits are frozen in
`validation/calibration/matrix_event_gpt_fixture.json`.

- fixture SHA-256: `144dc638f69404f82619c33ba25539902162e1aef5cb766c6045b5076633546e`
- GET-only OAuth status is checked before any generation
- if OAuth is disconnected, the run records a clean skip with zero calls
- every source is attempted once, in fixture order; no retry or fallback
- explicit_send is true for each of the four visible structured prompts
- exact quote binding and all null-endpoint rules remain unchanged
- every emitted 32x32 matrix must contain no exact-zero entry
- raw contract-derived candidates remain outside Git
- relevance and parser coverage are reported without a pass threshold

This is a shadow diagnostic, not a production replacement or G-gate. It does
not change packets, commit dynamics, the WP-35 non-zero rule, or any upstream
repository.
