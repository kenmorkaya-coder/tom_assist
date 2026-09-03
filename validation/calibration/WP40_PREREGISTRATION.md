# WP-40 parser-glossary paired evaluation pre-registration

Status: **FROZEN BEFORE GENERATION — LABEL-FREE DIAGNOSTIC — NOT A GATE**

This document freezes the WP-40 evaluation before any local Gemma generation.
It does not alter or reinterpret a prior pilot, activate the glossary, measure
accuracy, or make a G-gate claim.

## Fixed corpus

The corpus is exactly 11 preserved SUB-A inputs from
`/private/tmp/tom-assist-wp25-pilot-v2`, one from every WP-23 object family.
Each source text is the immutable `probe` field. Its glossary source is the
same case's native SQLite `state_objects`, opened read-only/immutable; titles
with current `active`, `satisfied`, or `rejected` status are included, while
`proposed`, `superseded`, and `archived` titles are excluded. The runner must
prove that these titles equal the corresponding immutable input objects before
the first generation. No document is added to this evaluation corpus.

| Seq | Frozen file | Family | Input SHA-256 | Probe SHA-256 | Chunks/arm |
|---:|---|---|---|---|---:|
| 1 | `001-D23-ASSUMPTION-01-SUB-A.json` | ASSUMPTION | `185965bdbdb9eaad7a69993356a4703b11f42761c0986b294463bec04ec3be88` | `14fcd69c8e7d3507e0c8d8207170ecf584db46374ae478e50dffdd8ac09bd251` | 4 |
| 18 | `018-D23-COMPLETED_WORK-01-SUB-A.json` | COMPLETED_WORK | `3fd004a529ad7a02c05445249cab25edc8f28f58f4eceba01d904d8866850dd6` | `93a0a2ec1bc43403a746ae68f4183008b884d5f5647349fadd6f16133f0a83ec` | 4 |
| 35 | `035-D23-CONCEPT-01-SUB-A.json` | CONCEPT | `2f4fd9271190ef0ab6563b4630ffed0ea05d3f00ec6338ec035713cd1e48b2b7` | `a98ec581a44adcfc2000b509fbea4bfe712f179190f94e1981c8feedb5046247` | 4 |
| 47 | `047-D23-CONSTRAINT-01-SUB-A.json` | CONSTRAINT | `5e6b443465552d950c1ee7e98e5131e239ac48a51bba798020927343bf7bbca5` | `0bbb5466dfb71c29977e76b7859bd1fe598f083389bbc5842992b02db4439e7a` | 4 |
| 64 | `064-D23-DECISION-01-SUB-A.json` | DECISION | `de12b7fa802c7b53ac02ca2ec269f506b20f2215db0091a59273f14cf464718a` | `90da34880d9e90d2ecf63ae492bdcc8667fa2e9567d93820484c08155b5b06b3` | 3 |
| 76 | `076-D23-EVIDENCE-01-SUB-A.json` | EVIDENCE | `e995f856dd94d572dfcba02ed1b01424d0518a102bb997285e3db7eb36c0eb90` | `4940ad20168ee63f19f0057c7b7d32d71db539df2609a55a44dce2806b30ebff` | 4 |
| 93 | `093-D23-OBJECTIVE-01-SUB-A.json` | OBJECTIVE | `1e5c214f0c9dba8d451415291b42f36e0195b9d516168e564c8b0f51eaf7c2ad` | `902c1bbd59cba850309d4d40ccd5c31c2f62a6c89d6963377dd6208c9f79a991` | 4 |
| 110 | `110-D23-REJECTED_PATH-01-SUB-A.json` | REJECTED_PATH | `09c833b77dfdc3b60c3c8437aca2275450b3fd413cc4760fbb38d9b0ae185b3c` | `827199b61f435aa69eb0f1c014268c55ccb5fcd4282435bbadc8eebd561e2db4` | 4 |
| 122 | `122-D23-SUPERSESSION-01-SUB-A.json` | SUPERSESSION | `a14e5847090bafbb346f79db1c2a757cccf248c1ae826431709cc92d9465c766` | `31a59ff98cf237e8b0649f0f566d45040ef8104464187218431361e751f5240e` | 4 |
| 139 | `139-D23-UNRESOLVED_DEPENDENCY-01-SUB-A.json` | UNRESOLVED_DEPENDENCY | `f340e08de3f2e4d9054f467741c5d23e99ad0a29f0bd64b404a1b0b618262044` | `0c01bd357afd33f8fd5324b1a051717a6d18928f88ee6f3d8f54c05601bb2b91` | 4 |
| 151 | `151-D23-WORKSTREAM-01-SUB-A.json` | WORKSTREAM | `77237617d3600ea568525dc38a99fa86ea4c4270bb8dadce2e5eb1d726096513` | `1506ba338b4e8119d4a17f53f9469f2cd9a02ce40d429ceba0afc7a7661af437` | 4 |

The canonical case-descriptor SHA-256 is
`e3a27aeae8ed7a38945ce243543b1ed32de2d96b3b5615e956be7fd45cbceee8`.

## Fixed execution and budget

- MiniLM revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- Gemma revision: `0d77464eeb233a2da68ebf9d7dc4edaac7db956d`.
- Exactly one persistent structure worker and its one persistent Gemma child,
  seeded by the worker's existing fixed seed and deterministic zero-temperature
  sampler.
- Source order is the table order. Within each source the order is glossary off,
  then glossary on. Both arms use the same source, chunk plan, worker and seed.
- There are 22 logical parse attempts and 43 planned chunks per arm. The hard
  maximum is therefore **86 local Gemma generations**. Every attempted chunk is
  counted whether it succeeds or fails closed.
- There is no retry, resend, best-of, repair generation, manual output change,
  provider fallback or prompt change after this freeze.
- Local parser failures are observations: the current passage fails closed, its
  remaining chunks are not generated, and the runner continues to the next
  locked arm. The budget is a maximum, not a success target.
- Cloud/provider generations, OAuth calls, network requests and owner quota use
  are fixed at zero. Feeling Wheel use is forbidden and forced off. The tree,
  RGM, project runtime and every preserved pilot file remain untouched.

The run stops before generation if a corpus hash, source hash, native title
multiset, model revision, chunk plan, pre-existing output directory or local
configuration differs. It stops immediately if the 86-generation ceiling would
be exceeded.

## Fixed diagnostics

For glossary-off and glossary-on separately, report: logical and observed parse
counts; fail-closed count/rate; attempted and successful local Gemma generations;
entity count and entity-weighted mean exact span length; orientation-plus-causal
relation count; signal count; unknown-field count; fraction of successful parses
with at least one unknown field; and total wall time.

For each pair, report whether the candidate digest changed. Change size is the
multiset symmetric difference over normalized structural atoms: entities;
relations with endpoint label/kind substituted for internal IDs; signals; and
unknown-field entries. Report the distribution including `not_comparable` when
either arm failed closed. Directed-graph agreement is exact digest equality over
the existing directed-graph fingerprint among pairs where both parses succeeded.
For changed pairs, report whether at least one selected glossary surface form
occurs case-insensitively in the immutable source.

## Fixed interpretation

These are label-free difference and failure diagnostics only. There is no
owner-authored parse ground truth in this corpus, so no output may call either arm
more accurate, better, improved, ready, or suitable for activation. A correctness
verdict requires a separate owner-authored labelled set. Product default remains
glossary off regardless of the observed differences. No G-gate verdict is issued
or implied.
