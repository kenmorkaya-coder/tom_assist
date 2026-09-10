# V11 bounded framing continuation

Resume selected v10 checkpoint at cumulative 2640 steps. Baseline development:
130/132 exact, 132/132 valid, zero invented authority, 42/44 paraphrase equality,
44/44 contrast distinction. The two remaining errors bind nominalized action
wording to works entities in paragraph and approval paraphrases. Development is
already used for curriculum design; passing it would not prove generalisation.

Append 120 authored rows to the unchanged 1200-row training corpus: 20 groups of
canonical, framing paraphrase and contrast in each of paragraph and approval.
Use new indexed names and values via v10's authored builder, with six document
headers and occasional nested framing. Equivalent variants deliberately retain
nominalized action wording under different headers. Only source offsets shift;
roles and conditions never derive from a model prediction. No development source
or label is added to training. This tests a general framing pattern, but shares
semantic templates and is not naturalistic data diversification.

Keep the 132 development messages byte-identical, parser and compiler unchanged.
Preflight all 1452 messages for aligned inference-prefix tokens and max length4096.
Tests validate preserved old examples, source separation, shifted evidence, entity
boundaries, full target round-trips and group contrasts before freeze.

One block of 660 updates, half a pass of the 1320-row shuffled corpus, seed109,
batch1, learning rate0.00001, optimizer reset as before. Native batch iteration
samples distinct rows within this half pass; not every added row is guaranteed
an update. Cumulative checkpoint3300. No automatic extra cycle. Rank16 and last16
q/v adapter targets remain unchanged. Preserve all prior adapters.

Reuse verified baseline predictions without generation. After the block generate
all132 development examples, saving raw text, token IDs and finish reasons.
Select by exact, valid, fewer invented authorities, paraphrase, contrast, earliest.
Retain baseline on regression. No thresholds relaxed, including90% per family.
No fresh held-out, matrix or Tree tests in this training session. If development
passes, separately freeze a fresh held-out protocol and selected adapter before
that next evaluation. Verification precedes reporting any pass.
