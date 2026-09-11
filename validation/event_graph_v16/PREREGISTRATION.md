# V16 boundary and negation development expansion

V12 and V15 remain RED and exposed. The v15 failures include a prohibited action
misbound as an exception, a truncated causal entity, and monitor spans absorbing
nearby verbs. Do not repair those outputs, train on those exact rows or reuse them
as fresh tests. No held-out inference is included in this session.

Resume selected v14 adapter at cumulative 4380 steps. Preserve schema, prompt,
binder, compiler and old weights. Append 144 authored training examples across
polarity, direction and paragraph: 16 three-way groups per family with varied site
identifiers, entity names, values and measurement verbs. Polarity contrasts retain
trigger binding and change only event negation. Source-bound names exclude adjacent
verbs. Direction contrasts reverse named endpoints. Paragraphs retain all four
events and shared triggers. Labels use authored builders, not model predictions.

Retain all 1440 prior training rows and all 156 prior development rows. Add 36
separately authored DEVELOPMENT cases, four groups per family, with separate names
and wording. These are failure-informed development data, not independent held-out
evidence. Check exact-source disjointness against every earlier inventory, gold
round-trips, contrasts, negation and boundary invariants before freezing. Preflight
all 1776 training/development targets for native-prefix alignment and length <=4096.

First generate a fresh baseline on all 192 development rows using v14; prior156
scores do not substitute for that measurement. Then run one 792-update block,
half a pass of the 1584-row training corpus, learning rate 0.000005, seed151,
optimizer reset. Not every new row is guaranteed an update. Batch1, rank16, last16
q/v targets remain unchanged. New cumulative checkpoint5172. Then generate all192
again, preserving raw strings, token IDs and finish reasons. No automatic extra block.

Selection first prefers original132/132 exact retention, then at least155/156 exact
on the prior expanded inventory, then full192 exact, valid, fewer invented authorities,
paraphrase equality, contrast distinction and earliest block. Report original132,
extension24 and new36 separately. Preserve the baseline if it wins or ties.
All extraction thresholds remain unchanged; results are DEVELOPMENT only.
No held-out, matrix or Tree tests or downstream success claims in this session.
