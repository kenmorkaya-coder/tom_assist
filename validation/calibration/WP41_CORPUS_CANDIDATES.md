# WP-41 project-prose corpus candidates

Status: **PROPOSED — NO CORPUS CHOSEN — OWNER DECISION REQUIRED**

These are candidates for a later, separately authorised WP-40 glossary rerun.
They are not inputs to WP-41, have not been sent to any model, and are not
labels. Counts below are whole-file UTF-8 character and whitespace-word counts;
a later frozen corpus must name its exact passage boundaries and hashes.

| ID | Candidate and source | Available prose | Genuine causal statements | Genuine dependency statements | Genuine constraints | Genuine supersession statements | Vocabulary derivable? | Licensing / sensitivity |
|---|---|---:|---|---|---|---|---|---|
| `C1` | Tom Assist v1.2 build specification, `docs/spec/Tom_Assist_Build_Spec_v1.2.txt` | 118,480 chars; about 14,698 words | Yes: it explains why architectural choices lead to particular behaviours and failure modes. | Yes: it states component and workflow dependencies. | Yes: normative requirements and prohibited behaviours are central. | Yes: it defines replacement, reopening and supersession behaviour. | Yes: repeated project terms can be derived locally and deterministically. | Owner-controlled repository material; no repository licence file was found, so treat as private/internal unless the owner says otherwise. |
| `C2` | Tom Assist engineering narrative, `BUILD_LOG.md` | 315,740 chars; about 36,877 words | Yes: implementation findings include explicit causes and consequences. | Yes: package, runtime and evidence dependencies are described. | Yes: each package records retained constraints. | Yes: later packages and accepted corrections explicitly supersede earlier mechanics. | Yes, although hashes, tables and test output would require an owner-approved prose-only extraction rule before freezing. | Owner-controlled and highly sensitive internal engineering history; no repository licence file was found. |
| `C3` | Owner-supplied, de-identified excerpts from real ToM Assist project conversations or design notes | **OWNER TO SUPPLY AND MEASURE** | Unknown until supplied; eligibility requires confirmed examples. | Unknown until supplied; eligibility requires confirmed examples. | Unknown until supplied; eligibility requires confirmed examples. | Unknown until supplied; eligibility requires confirmed examples. | Yes if the excerpts retain real project terminology; the eventual glossary derivation must be frozen with the corpus. | Owner-supplied; owner must confirm permission, remove secrets/personal data, and set the handling boundary. |
| `C4` | Tom Assist build contract, `BUILD_INSTRUCTION.md` | 23,468 chars; about 2,960 words | Some: rationale appears alongside safety boundaries. | Yes: ordered work packages and runtime dependencies are explicit. | Yes: mandatory and prohibited actions dominate the text. | Limited: revision rules exist, but natural supersession prose is sparse. | Yes, but the vocabulary is dominated by build/governance terms. | Owner-controlled repository material; no repository licence file was found, so treat as private/internal. |

## Recommendation, not selection

Recommend **C3**, provided the owner can supply enough de-identified real
project prose to cover all four statement families and can author its labels.
It is the only candidate that directly samples the language the glossary is
intended to help parse. C1 is the strongest fully local fallback because it is
substantial, coherent project prose and contains all four relation families.

The owner must select the corpus, exact passages, sensitivity boundary and
label provenance. Until then the v2 corpus fields remain blank and no model run
is authorised.
