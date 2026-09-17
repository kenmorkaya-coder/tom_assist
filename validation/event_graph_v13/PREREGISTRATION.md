# V13 revision-link and paragraph-completeness continuation

V12 remains RED: 130/132 exact, 131/132 valid; the revision contrast created an
unsupported supersede action, and the paragraph paraphrase omitted notification.
The now-exposed held-out set must not be reused as an unbiased test. It is neither
copied into training nor used for this session's checkpoint selection. Subsequent
held-out claims require another separately frozen fresh inventory.

Resume the v11 selected adapter at cumulative step 3300, preserving all prior
weights. Keep schema, prompt, binder, compiler and scoring definitions unchanged.
Append 120 authored training records to the retained 1320: twenty groups in each
of revision and paragraph, three variants per group. Revision labels contain two
requirement events and a supersedes link from newer to older; repeated revision
mentions do not create an action. Paragraph labels retain four events including
notification under the same trigger as stopping, alongside a separate flow limit.
Vary names, identifiers and quantities; use no model-generated supervision.

Add 24 separately authored development cases with different wording and names to
unchanged original 132 cases. These cases are explicitly DEVELOPMENT, informed by
failure classes; not fresh held-out evidence. Freeze all 156 before baseline
inference. Generate baseline on all 156 using v11, then train and generate all156
again. Do not reuse 132-example scores as if they covered the extension.

One bounded 720-update block: half a pass of the 1440-row shuffled training corpus,
batch1, seed127, learning rate0.00001, optimizer reset. Not every new row is guaranteed
an update. LoRA rank16, last16 q/v targets and4096 sequence limit unchanged; check
all1596 training/development labels for alignment and truncation before freeze.
Cumulative new checkpoint4020. No automatic second block or retry.

Selection first prefers checkpoints retaining 132/132 exact on the original
inventory. Then compare full156 exact count, valid count, fewer invented authorities,
paraphrase equality, contrast distinction, and earliest block. Report original and
extension scores separately, including regressions. Ties retain baseline. The
unchanged extraction thresholds describe development only; no downstream pass.

Preserve raw outputs, token IDs, finish reasons, frozen hashes and every aggregate.
Reparse and recompute before milestone reports. This session runs no held-out,
matrix discrimination or Tree tests and makes no generalisation claim.
