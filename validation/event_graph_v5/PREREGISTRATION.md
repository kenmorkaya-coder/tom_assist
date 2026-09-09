# V5 continuation session: monitor development improvement

Continue the verified v4 512-step LoRA weights for two further full passes through
the unchanged 480-example training inventory. Compare complete deterministic
generation on all 132 development records at cumulative steps 512, 992 and 1472.
Measure the 512 baseline before any additional update. The development set is
explicitly reusable for monitoring and selection; it is not an unseen final test.

Each 480-step block resumes the previous block's weights, with the same rank-16,
last-16-layer query/value LoRA, learning rate 1e-4, batch size 1, aligned supervised
template and 4096-token limit. The first block resumes v4. Seeds 17 and 29 shuffle
each full pass independently. Adam state is reset for each block because these
artifacts store weights only. This is a weight-continuation experiment, not an
uninterrupted optimizer trajectory or a controlled estimate of epoch count alone.
No labels, source text, prompt, action schema, parser or compiler are repaired in
this session. No former held-out generations enter training. The previously
examined held-out battery is not rerun for checkpoint selection.

Evaluate development with the native inference prompt, temperature zero,
maximum 4096 generated tokens and one response per record per checkpoint. Retain
all invalid outputs in denominators. Track exact and valid graphs, original
parser errors, family/field counts, invented-authority count, paraphrase agreement
and contrast distinction. The baseline and subsequent scores use the same scorer.
Source-order differences remain failures under the existing canonical comparison.

Predeclare selection by descending exact count, then valid count, fewer invented
authorities, paraphrase agreement, contrast distinction, then earliest checkpoint.
Retain the 512 baseline if extra training does not improve that ordering. Report
absolute changes, including zero improvement or regression. Complete both planned
epochs unless a runtime/integrity defect prevents it; preserve failures and do not
silently rerun an incomplete stage. A dropped development score is information,
not a reason to discard the checkpoint or restart with new settings mid-session.

Freeze this driver, tests and plan, plus the parent manifest/adapter/config hashes,
before measuring the baseline. Each stage verifies the inherited source/data/model
freeze. Run training and generation sequentially to avoid loading two GPU models
at once. Outputs and logs are exclusive per stage; state/progress files may update.
Parent artifacts are read-only. No cloud generations, downloads or external sends.

Development threshold satisfaction is labeled development-only, never a held-out
GREEN or permission to enter matrix/Tree gates. A fresh frozen final test is required
after selecting a model; it is outside this monitoring session. These data remain
synthetic, with template sharing and repeated sources. There is no claim of
naturalistic generalisation or a controlled comparison with MiniLM.
