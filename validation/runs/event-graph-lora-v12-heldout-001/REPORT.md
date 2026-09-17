# V12 fresh held-out extraction — verified RED

The single frozen held-out pass completed. All raw predictions were reparsed and
the complete aggregate recomputed before this verdict. The unchanged extraction
gate is **RED** despite high overall accuracy.

| Metric | Result | Requirement |
|---|---:|---:|
| Exact | 130/132 (98.5%) | At least 95% |
| Valid | 131/132 (99.2%) | 100% |
| Invented authority | 0 | 0 |
| Paraphrase equality | 43/44 (97.7%) | At least 95% |
| Contrast distinction | 43/44 (97.7%) | 100% |
| Revision family exact | 5/6 (83.3%) | At least 90% |
| Paragraph family exact | 5/6 (83.3%) | At least 90% |

The other 18 families are exact on every example. The gate fails validity, contrast
distinction, and two per-family requirements. No thresholds were relaxed.

The revision contrast v12-revision-0-2 emits an unsupported `supersede` action as an
extra event and attaches the supersedes link to that event instead of expressing
the intended revision relationship between the two requirements. Validation rejects
it. The paragraph paraphrase v12-paragraph-0-1 contains only three extracted events
where four are required. These are model output errors, not label repairs or accepted
partial answers. Original outputs and reports remain intact.

Selected tested adapter: v11 epoch 1, cumulative step 3300; SHA-256
`4d5201649f27778c53db424a3b0631d6434d3ef017085d1314b0387b43d68e23`.
The fresh test changes wording, entities and most values while retaining authored
semantic templates. It is not naturalistic project-document validation. The previous
132/132 development result remains true but does not confer held-out success.

No new training, matrix discrimination or Tree test was run. Matrix and Tree gates
remain NOT_RUN and blocked by this extraction result. This held-out set is now
exposed; any subsequent tuning would require another independently frozen test.

Verification checked frozen source/model lineage, selected adapter and prediction
hashes, reparsed all 132 saved raw outputs, recomputed every family and aggregate
metric, and checked token IDs and finish reasons. RESULT.json preserves full results
and SHA-256 provenance. No generation was repeated during verification.
