# Project identity compiler: fresh frozen diagnostic v1

Two fixed arms: the unchanged typed compiler v1 and a registry-bound identity
adapter feeding that same compiler. This is compiler-only. No Tree, memory,
generation, LoRA training, provider call, product integration or numerical
reasoning claim is permitted. Old RED artifacts stay immutable.

## Mechanism, fixed before scores

Identity is `(project_id, entity_id, entity_kind)` from an explicit supplied
project register. The register is a CSV source with fixed columns, and aliases
are additional rows for the same identity. The adapter validates registry shape,
project namespace, alias uniqueness within the project and consistent entity
kind. It binds literal labels in event fields to registry record ordinals and
the complete register's digest. Unbound, conflicting and ambiguous names fail
closed. It does not manufacture an identity for every distinct string.

Replace a resolved label in semantic input with `registered <entity_kind>` and
add the registry identity as an exact symbol to that field. Keep the original
label and binding evidence in the prepared record. This uses the same v1
symbol-vector code and the already frozen 1:1 semantic/symbol mix. No new seed,
matrix weights, dimension, view, aggregation rule or downstream mechanism.
Unannotated events pass through unchanged.

The experiment uses manually authored **synthetic project-register records**.
It demonstrates handling of explicit supplied identity/alias evidence, NOT
automatic identity discovery, truth of a project registry, or disambiguation of
an ambiguous paragraph. Identical labels in different projects are separable
only because the active project and register are additional supplied facts.
Ambiguous labels within one project must be rejected, not assigned at random.

## Fresh battery and acceptance

Twelve fresh three-identity families, none using Quartz/Granite/Basalt. Six have
similar labels in one project; six use identical labels in distinct project
namespaces. Each family includes V1/V2/V3, a paraphrase P2 of V2, and A2 with a
different registered alias for V2 but otherwise identical wording. Five items
per family, 60 items total; both arms compile all items.

Primary identity arm gates:

- all 12 final canonical bases rank 3 and condition <=10;
- all 12 P2 variants nearest V2, changed/same ratio >=1.25 and substitution
  basis condition <=10 (no weaker gate than the original battery);
- all 12 A2 aliases produce the exact same final matrix as V2;
- all canonical identity changes produce different matrices;
- finite, unit-normalized, nonzero and deterministic outputs;
- no symbol-code collision in this observed inventory;
- both arms produce byte-identical outputs on all 192 unannotated original and
  holdout inputs from typed compiler v1. These remain compiler regressions, not
  a relabelling of the earlier RED as GREEN;
- existing 18 exact-direction controls unchanged, and add 12 registry-identity
  source/target swap controls; require transpose error <=1e-12 and nonidentity;
- identity validator negative tests must reject missing scope, conflicting
  identity kind, unknown labels and within-project ambiguous aliases.

Current arm scores are a baseline, not a gate for the identity hypothesis.
Record every case, not just winners. Freeze code, design, register/input data and
scorer before embedding. Save embeddings and all intermediate arrays before
loading the separate scoring key. No post-score seed or mixing-weight choice.

Trace: raw 384D semantic fields; projected 32D semantic fields; target field after
identity mixing; combined mixed fields; weighted outer-product components;
individual normalized views; unnormalized sum of views; final normalized matrix.
Also preserve symbol vectors. Conditioning of concatenated fields measures
relative discrimination, not irreversible deletion of the target information.

On any RED, preserve and diagnose without tuning. A local GREEN supports only
this identity hypothesis under supplied records and no-regression controls;
moving to a Gemma/LoRA experiment requires its own frozen extraction design and
does not follow automatically from an isolated compiler score.
