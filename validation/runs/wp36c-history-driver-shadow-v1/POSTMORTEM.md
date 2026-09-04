# WP-36c v1 post-mortem

**FAILED FROZEN SHADOW RUN — RETAINED; NOT A GATE**

All reported v1 pairwise checks passed, but the 10K plan exposed first-turn
`novelty: 1.0` and `decay: 1.0`. The semantic/history combiner had incorrectly
fallen through to the legacy sparse compiler whenever a new history feature was
absent. That contradicted the frozen rule that missing history adds no synthetic
feature. V1 is retained unchanged as diagnostic evidence and cannot support
activation. V2 pre-registered the single correction before implementation.
