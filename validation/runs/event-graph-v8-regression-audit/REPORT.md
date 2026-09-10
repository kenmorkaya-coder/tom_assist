# V8 regression diagnosis

Verified all saved raw predictions, aggregate metrics, frozen sources and adapter
hashes. Epoch 2 introduced 12 new failures and recovered two, accounting for the
net loss of ten exact answers. Nine failures persisted; 109 records stayed correct.

Eight regressed records involve participant or predicate-subject source selection:
spans absorb action wording, numeric thresholds or pronoun phrases instead of
selecting the named entity. The four other new failures are one dropped prohibition,
one LT-to-LE comparator change, one revision transcription error and one dangling
reference. Neither comparator nor negation errors can be dismissed as formatting.
The persistent errors also include exception-versus-condition binding and overly
broad spans in causal and multi-quantity prose. Full leaf-level diffs are in RESULT.json.

The selected checkpoint's source spans remain fallible despite deterministic binding:
the binder faithfully copies an incorrect range if the model selects one. No parser
repair or label editing was applied. Both epochs' 132 saved token streams replay
exactly through the pinned streaming detokenizer, including the misspelled revision.
This rules out a discrepancy between saved token streams and displayed output in
these runs; it does not prove all runtime behavior is correct or identify a single
cause of regression.

Next experiment: resume v8 epoch 1 for 480 updates at one tenth the learning rate,
keeping data, format and seed 73 unchanged relative to the previous continuation.
The optimizer is reset as before. The reduced rate and shorter horizon are both
changes, so this is a bounded retention test, not causal isolation. Evaluate the same
132 development examples and retain baseline on regression. The frozen protocol is
validation/event_graph_v9/PREREGISTRATION.md. No fresh held-out or downstream gate
is included or claimed passed.
