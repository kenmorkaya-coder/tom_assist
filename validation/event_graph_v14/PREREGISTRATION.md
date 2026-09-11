# V14 shorter lower-rate continuation

Resume selected v13 adapter at cumulative step4020. The verified baseline has
154/156 exact,155/156 valid: original132/132 exact, extension22/24 exact. One
revision example emits an evidence range missing token_start; one paragraph
labels flow operation as use rather than discharge. No runtime repairs or schema
changes will be applied to make those outputs pass.

Test a single360-update continuation at learning rate0.000005 (half v13), seed139,
optimizer reset. This is one quarter of the unchanged1440-row training inventory;
not every row is guaranteed an update. Preserve the original adapter and all
previous results. Cumulative new checkpoint4380. LoRA rank16, last16 q/v, aligned
native prefix, mask and4096 sequence limit remain unchanged. Reverify inherited
preflight and source/model lineage. This changes rate, seed and update horizon;
it tests bounded improvement and retention, not a single-variable causal claim.

Development stays byte-for-byte the v13 inventory (156, original132+extension24).
Reuse the verified v13 aggregate and raw outputs as baseline block0 without model
generation. After training evaluate all156 once, preserving raw outputs, token IDs
and finish reasons. No exposed v12 held-out row enters this session or selection.

Frozen selection: prefer original132/132 exact retention first, then full exact,
valid, fewer invented authorities, paraphrase equality, contrast distinction,
earliest block. Keep baseline on regression or tie. Report original and extension
results separately. All thresholds remain unchanged, including100% validity.
No additional training block, retries, fresh held-out, matrix or Tree tests.
V12 remains RED. Further held-out claims require a new independently frozen test.
