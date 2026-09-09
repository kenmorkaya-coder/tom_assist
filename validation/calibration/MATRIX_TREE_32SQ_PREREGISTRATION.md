# Direct 32×32 matrix Tree diagnostic

Status: **FROZEN FOR LOCAL SHADOW DIAGNOSTIC — NO PROVIDER CALLS**

Frozen on: 2026-09-08 Australia/Sydney

This instrument tests a replacement document-address mechanism. It does not
alter the product and does not use the existing 17D or 8D document route.

The frozen teacher interpretations, relevance IDs, matrix weights, projection,
Tree search limits and diagnostic expectations are in
`validation/calibration/matrix_tree_32sq_fixture.json`.

- fixture SHA-256: `8ad95a36318e6e4e0e29fc43b950e097da70857ff6e1230dfe370a24b00d3a4f`
- matrix: 32×32, float64 during this diagnostic
- source and target: cached MiniLM 384D vectors projected to 32D through one
  fixed Rademacher Johnson–Lindenstrauss projection
- relation and context: encoded through the same semantic path
- event matrix: normalized `1.0*outer(source,target) +
  0.5*outer(relation,relation) + 0.25*outer(context,context)`
- Tree: deterministic binary prototype Tree, leaf capacity 2, beam width 2
- no full-inventory fallback is permitted during Tree search

The fixed relevant passage IDs were declared before the first execution.
Parsing is deliberately outside scope: the fixture supplies the teacher's
event records. Results therefore measure only semantic projection, matrix
construction, direction preservation, Tree search and reload stability.

This is not a G-gate and cannot establish production readiness. A successful
result would still require a separately tested parser, project persistence,
preview-purity integration, migration and owner audit before product use.
