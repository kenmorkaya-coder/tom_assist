# Source-span repair prototype

This is an isolated, untrained transport prototype in
`gateway/event_graph_span_wire.py`, not a replacement for any frozen parser.
The best 992-step adapter and all old scores remain unchanged.

The model receives the original source and a deterministic lexical token table.
The table indexes words/numbers and punctuation; it does not identify nouns,
clauses, participants or semantic roles. Model output uses half-open token ranges
`{token_start, token_end}` for evidence, predicate subjects and event roles.
The model still selects which source occurrence identifies each participant,
including resolving pronouns to the intended earlier mention.

Unlike the current protocol, the wire format has no separately generated entity
list or free-form entity name. For each model-selected role/subject range, the
binder copies that exact source substring, assigns an internal entity ID and
uses it consistently wherever that same range was selected. It does not merge
separate mentions by guessed identity or expand incomplete names. Only referenced
entities are declared. Arbitrary missing entity IDs cannot be emitted through a
role field; that field requires a valid source range instead.

Conditions, predicates, event IDs, event order, links, units, numeric values,
comparators, polarity, modality, time, revision, exceptions and complements remain
explicit model outputs. The existing graph validator checks them after binding.
Dangling event/condition references, unused predicates, malformed ranges and
unexpected fields fail. Wrong but valid source ranges remain wrong; the binder
never fixes role choices by reading the prose.

The binder produces the existing `tom-assist-event-graph/1` runtime graph for the
unchanged deterministic compiler. The new wire version is
`tom-assist-span-wire/1`. Old adapters do not know this protocol and must not be
silently switched to it or evaluated with repaired outputs.

Offline representation tests preserve canonical meanings for all 480 train,
132 development and 132 already-exposed v6 authored graphs. This is codec coverage,
not a new held-out model result. Supervised output bytes shrink by 35.62% on train
and 38.11% on development; the indexed input table adds overhead, so these numbers
do not establish end-to-end token or speed savings.

A next experiment should separately freeze this wire schema/prompt, convert only
training/development labels, broaden training contexts with irrelevant headers and
diverse qualified entity names, and measure source-range selection and whole-graph
accuracy at checkpoints. Contrast actor/issuer/recipient assignments explicitly.
Capture generated token IDs as well as text for future decoder audits. Do not use
v6 held-out answers as fresh supervision while claiming an unseen final test.
Freeze another untouched final battery after development/model selection. This
prototype does not start that training, choose its hyperparameters or certify an
accuracy improvement.
