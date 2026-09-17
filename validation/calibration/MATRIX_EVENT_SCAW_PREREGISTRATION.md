# Evidence-bound matrix-event SCAW diagnostic

Status: **FROZEN — OWNER AUTHORISED LOCAL GEMMA GENERATION**

Frozen on: 2026-09-08 Australia/Sydney

This is a small, real-prose diagnostic of the missing language-to-matrix layer.
It is not a production replacement and does not change packet admission. Ten
owner-selected SCAW shortlist passages and five questions are each sent once to
the cached local Gemma model through the evidence-bound matrix-event tool.

The exact corpus reference, passage IDs, questions, relevance IDs, cached model
revisions, maximum 15 local generations, matrix formula, matrix views and Tree
search limits are frozen in
`validation/calibration/matrix_event_scaw_fixture.json`.

- fixture SHA-256: `5840309d26d6d9ef36613848e9cfce7ff39de95842ba6b02e7c2d0b26cb3f9bb`
- no OAuth, GPT, cloud, network or model download
- one attempt per source; no retry or fallback parser
- every provider quote is rebound to one exact source span or fails closed
- an unanswered question endpoint remains null; it is never invented
- passage events may create full, source-context and context-target matrix views
- every emitted 32x32 matrix must contain no exact-zero entry
- Tree search has no full-corpus fallback
- parser failures, matrix-bearing coverage and recall are reported without a
  pass threshold
- raw source-derived records and matrices remain outside Git under the selected
  run directory

The WP-35 non-zero 17D rule is untouched. This diagnostic does not use 17D or
8D document loads and cannot drive the pinned 10K tree. It tests a proposed
replacement boundary only. It is not a G-gate and does not claim that the
matrix-native repository has an approved growth or learning law.
