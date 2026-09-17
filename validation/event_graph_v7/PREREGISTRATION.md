# Lower-rate continuation from the 992-step checkpoint

User authorized another training session after the fresh v6 test. Start from the
best development-selected v5 epoch-1 adapter (992 cumulative steps), not the worse
1472-step adapter. Continue for two full 480-example epochs at learning rate 2e-5,
one fifth of the previous rate. Seeds are 41 and 53. All other LoRA settings,
training/development data, supervised alignment, prompt and parser remain fixed.
This tests a smaller update rate; it does not assert that this will repair the
observed generalisation errors. No v6 or other held-out labels enter training.

Each block resumes weights with reset Adam state. Record this discontinuity;
there is no saved optimizer state to restore. Stop only for an infrastructure
failure during the planned two blocks, preserving partial outputs without silent
retries. A development regression is reported and does not erase a checkpoint.

Reuse the 992-step development baseline (127/132 exact, 130/132 valid), only after
checking its adapter/prediction hashes, reparsing every saved raw response and
recomputing all metrics. Copy its immutable prediction records into epoch-0 with
explicit baseline-reuse provenance; perform zero new baseline generations.
Generate one full 132-row development pass after each 480-step block, at 1472 and
1952 cumulative steps. These are different weights from the prior higher-rate
1472-step model; identify both run and step count when reporting.

Use the unchanged development scorer, temperature zero, seed 7, native inference
prompt and 4096-token generation cap. Preserve all invalid outputs in denominators.
Select by exact count, valid count, fewer authority mismatches, paraphrase agreement,
contrast distinction, then earliest checkpoint. Keep the 992 baseline if neither
new checkpoint improves this ordering. Report improvements, ties and regressions.

Freeze this plan, driver and tests plus parent manifest, baseline report/raw outputs
and selected adapter hashes before training. Verify inherited frozen source/data/
model files at each stage. Training and generation run sequentially on the local
GPU. Old sources/results are immutable. Weights and raw runs remain outside Git.

These are reused development measurements on synthetic data. No held-out GREEN,
matrix/Tree testing or production readiness follows from them. Both previous
held-out batteries are exposed and may not be reclaimed as unseen. Another fresh
test follows future development/model selection, outside this training session.
