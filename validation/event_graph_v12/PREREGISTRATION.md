# V12 post-selection held-out extraction

Freeze before any v12 model generation. Selected checkpoint: v11 epoch 1,
cumulative step 3300, adapter SHA-256
4d5201649f27778c53db424a3b0631d6434d3ef017085d1314b0387b43d68e23.
Development meets all predeclared extraction thresholds (132/132 exact and valid).
No additional training, checkpoint selection, prompt tuning or semantic repair
is allowed during this test.

132 records, 44 canonical/paraphrase/contrast groups, 20 semantic families.
New authored sentence structures appear in wording.py. Names, dates, revisions,
qualified recipients and most values differ from earlier batteries. Zero remains
as a deliberate numeric boundary. The semantic graph construction derives from
the earlier authored v6 case definitions; evidence is rebound to the new prose.
This is a fresh surface-form test with shared semantic templates, NOT an independent
naturalistic benchmark or evidence about all project English. Neither v12 sources
nor labels enter training. Exact-source overlap is checked against all earlier
versioned training, development and held-out inventories. Each triple must preserve
canonical/paraphrase meaning and change contrast meaning. Gold must validate and
round-trip through the current source-span representation before freeze.

One deterministic local inference pass: temperature 0, seed 7, maximum 4096 new
tokens, existing native inference prefix and unchanged source-span prompt/parser.
Retain raw strings, token IDs, finish reasons and errors. No retries or edited outputs.
All 132 rows count; malformed, truncated, missing or unresolved outputs fail exactness.
The unchanged inherited extraction thresholds are: 100% valid, >=95% exact overall,
>=90% exact in EVERY family, zero invented authority, >=95% paraphrase equality,
and 100% contrast distinction. All conditions are required together. Existing
scorer counts semantic meaning after ID/evidence normalization and exact unit
conversion; it does not require exact model-generated evidence spans to match gold,
but selected evidence must be valid substrings. Role entity names remain exact.

This session performs extraction only. Formally read and independently recompute
the full saved aggregate before reporting GREEN or RED. No matrix or Tree test is
run automatically, even on extraction GREEN. A failure blocks downstream gates.
Preserve all artifacts. Previously exposed v1/v4/v6 outcomes remain unchanged.
