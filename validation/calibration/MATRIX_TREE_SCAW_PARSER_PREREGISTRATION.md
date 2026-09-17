# Automatic-parser SCAW matrix Tree diagnostic

Status: **FROZEN — OWNER AUTHORISED LOCAL GEMMA GENERATION**

Frozen on: 2026-09-08 Australia/Sydney

This is the required language-to-matrix test before any production replacement
of Tom Assist's document index. The existing local Gemma structural parser
receives all 41 owner-selected SCAW shortlist passages and ten frozen questions.
Its accepted entity/relation records are compiled into signed 32×32 matrices;
no 17D or 8D document projection participates.

The external corpus remains subject to the WP-42 sensitivity boundary and is
not copied into Git. The exact file, hashes, questions, relevance IDs, model
revisions, maximum 76 local chunk generations, matrix formula and Tree search
limits are frozen in
`validation/calibration/matrix_tree_scaw_parser_fixture.json`.

- fixture SHA-256: `d1d8f35065379b18f7f6070cbb8cb3736b86f82c5db8cddb7a025e69769dad4f`
- no OAuth, cloud provider, network or model download
- every planned parser chunk is attempted once; no retries or fallback parser
- any failed chunk fails that passage or query closed
- a successfully parsed source with no directed relation produces no matrix
- Tree search has no full-corpus fallback
- direct matrix and selective Tree ranks are reported separately
- there is no pass threshold for relevance; the observed recall is the result

This is not a G-gate. It neither authorises matrix-native growth mechanics nor
claims the current matrix-native repository has an approved growth law.
