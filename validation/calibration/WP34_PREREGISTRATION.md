# WP-34 GPT parser comparison pre-registration

Status: **OWNER-AUTHORIZED LIVE ENGINEERING COMPARISON — NOT A GATE**

## Question and locked corpus

This run asks whether GPT parses the same fixed structural language corpus better
than the WP-33 local Gemma candidate. It retains all 94 WP-33 cases and their
pre-registered expected relations, directions, negations, signals, history
bounds and unexpected-relation allowances without modification.

- Case digest: `sha256:eeff2aaff7f10c62cac88ab997d3697715212565281d262c52099ca7ddcddb13`
- Frozen Gemma summary: `sha256:de0a971036cbbb7157051b40e16016984a9e6423cd042559aa69684d7b4fb23c`
- 94 cases; 113 logical passages including committed-history turns.
- Exact MiniLM revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- The unchanged token planner yields 124 logical chunk slots, 88 unique
  passages and 97 unique chunk texts.

## Candidate and call budget

The candidate is Tom Assist's own OAuth broker using model `gpt-5.5`. The fixed
strict response schema digest is
`sha256:63001cf4ff74ca064b4e9043547cb2b1bdc31814d7b4aea71b45909bfcc24eb6`.
The schema asks for typed entities, directed orientation/causal relations,
signals and exact evidence quotes. It contains no offset fields and no load
fields. Tom Assist resolves every quote to an exact source span, rejects absent
or ambiguous evidence, and uses the existing deterministic compiler for all 17
load values.

One explicit provider generation is allowed per unique chunk text: exactly 97
generations if preflight succeeds. Exact duplicate chunks use the first validated
result. Calls are serial, retries are zero, and any broker/provider boundary
failure stops the run. A schema-valid response that fails source binding is a
known parser error and does not authorize another call. Raw provider text is not
retained; the validated candidate, response digest, byte count and wall time are.

The Feeling Wheel is disabled and unused. No upstream repository is written.
No preview route can invoke this parser. No tree step is run.

## Scoring and frozen comparison rule

The WP-33 scorer and thresholds are reused unchanged. The report resolves every
metric against the preserved Gemma v3 values. `GPT better` is true only if all
four core metrics strictly improve:

1. strict observation rate;
2. end-to-end relation recall;
3. end-to-end signal recall; and
4. multi-relation exact rate;

and all three safety conditions do not regress:

1. direction reversals are no greater than Gemma;
2. unexpected-relation rate is no greater than Gemma; and
3. valid bounded 17D shape rate is no lower than Gemma.

Every individual metric and delta is reported even if the combined rule is
false. Passing the comparison does not activate the parser, validate the Python
10K tree, or establish any G-gate. The branch stops for owner audit after the
run.
