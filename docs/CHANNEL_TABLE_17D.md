# The 17 channels — what is measured, when it is zero, and what a zero-free definition would need

**For:** Ken Morkaya (owner decision). **From:** Claude (orchestrator). **Date:** 2 September 2026.
**Status:** decision document, not a spec. Nothing here is issued to Codex.

Sources, all read-only: the product compiler `gateway/structural_analysis.py` (`_static_load`, `compile_load`) at commit `a8cd854`; pinned tom_master `e9fdef81c`: the channel glossary in `docs/sicd_progressive_capability_stages.md`, upstream's own reference construction `integration/msr_field_packet.py::map_abstract_objects_to_load_signature`, and the consumers `agency/mechanics/sicd_msr_field_mapper.py` (`axis_projection`, `driver_projection`), `sicd_msr_load_application.py` (`_wind_vec`, `_effective_*`), `msr_8d_loading_aware_readout.py` (17→8 routing). `tom_master17D` was not read.

Standing rule (owner, reaffirmed 2 Sep): a completed authoritative load has no zero entries. No epsilon, floor, prior, model guess or replacement value.

---

## 0. Corrections after reading *The Mechanics of Reasoning* and Ken's Laws (2 Sep 2026, evening)

Owner directed me to the 17D paper `docs/papers/mechanics_of_reasoning.md`; it cites `docs/contracts/kens_laws.md` as its first grounding document, which I also read. Both are in the 17D checkout, read-only. The table below was written before reading them and is wrong or incomplete in the following ways. The table body is left as written so the corrections are auditable.

**C1. The 17 channels are admitted event content, not the load, and not the reading.** Law 15: *8D acts on the tree; 17D reads the tree.* The incoming `q17` is "words-as-load content", projected onto the 8D causal path. Authoritative 17D quantities (branch owner signatures, E15 member addresses and content readouts, Carillon prototypes) are derived afterwards by the tree from the applied 8D route, the admitted content and the tree's history. My table treated the 17 values as the force on the tree. They are the measurement that is admitted, then routed.

**C2. Where zeros actually do damage.** Not mainly in the driver `max` terms I listed. Three places:
- The `intensity` routing coordinate is `RMS17 + 0.20·mean(dynamics) + 0.10·L_inference`. This is present at the product's pin. Every zero lowers the RMS of the whole event and therefore its intensity address.
- In the 17D substrate the wind scalar carries a `magnitude gain = RMS17 / 0.30`. Zeros attenuate the entire event's wind, not just one axis. **This gain is absent at the product's pin.**
- Reading space. G1 member addresses are means of admitted 17D query vectors. Carillon territory and E15 member selection are cosines over full 17D vectors with floors of 0.7474 and 0.995, plus an ordinal law over the four strongest components. Sparse vectors that share a zero pattern look alike, the top-four ordinal comparison degenerates, and the 0.995 floor stops discriminating. **This is the mechanism behind the owner's objection that a load with zeros is not 17-dimensional.** A sparse `q17` produces sparse addresses, and the reading law assumes density.

**C3. The 17D reading space does not exist at the product's pinned substrate.** `tom_master` at the pin has no `owner_sig_17d`, no E15 member schema, no Carillon channel schema, no district readout, no territory router. The paper's baseline is 17D `origin/main`. In the product today, `q17` acts only through the 8D projection and the driver proxies. The density requirement is therefore a requirement on the transducer for the substrate the product will bind to, not something the current pin can exercise.

**C4. "Frequency is almost invisible" was wrong.** At the pin it enters `delta_F` and `phi` at 0.15 each. In reading space every channel is an equal-weight cosine coordinate.

**C5. The product supplies no T/S/P tuple.** The canonical route admits two separate inputs: an evidence-bound driver tuple `(T0, S0, P0)` and `q17`, coupled by `max` with the `q17` proxies. The product's commit path calls the canonical application with the load signature only. `threat_load`, `sustenance_potential` and `procreation_potential` default to zero, so the product's T/S/P are entirely the proxy projection of `q17`. The transducer never built drivers. This is larger than the zero question.

**C6. The tree-grounded candidate definitions in §2 are withdrawn.** I proposed grounding `novelty`, `recurrence` and `decay` in branch leaf vectors and cohort alignment. Law 15 says a compiler output that depends on live tree state is a *derived reading*, not admitted content. Building `q17` from tree state would collapse the cause/reading separation the law exists to protect. Admitted `q17` may draw only on the words and the canonically admitted context (the committed conversation history is admitted context). The first-turn problem for history-based channels therefore stands.

**C7. What the canon says about zeros, stated as fact.** For the driver tuple, the City admission law is explicit: every nonzero load must cite evidence bound to the admitted context; a zero load must carry no citations and the fixed zero-evidence basis. For `q17` the paper states only that every component is clipped to [0,1]; it states no positivity law. The functional case for density in `q17` is C2. The law itself is the owner's to state.

**C8. The strategic fork the paper exposes (Law 7: options to the owner before any work order).** In the City campaign the interpreter that authored `q17` and T/S/P was a provider, evidence-bound, validated and hash-bound. The product forbids model-generated load values and compiles `q17` deterministically from typed facts. Deterministic compilation from sparse facts is exactly why `q17` is sparse. The options are:
- (a) **Keep deterministic compilation.** Then density needs continuous evidenced measurements for every channel on every event: calibrated semantic projections for the static channels (the perception-gate-2 corpus), continuous similarity statistics for the dynamics, and shadow-only first turns where history channels have nothing to measure. Cost: a calibration campaign before any dense load exists; the values become degrees, not counts.
- (b) **Adopt the City admission law in the product.** The interpreter (local Gemma, or GPT) authors `q17` and T/S/P values, each nonzero value citing quote-bound evidence, validated and hash-bound, with the deterministic compiler retained as a shadow cross-check. Cost: reverses the product's `model_generated_load_values: false` commitment; density then depends on the interpreter's discipline, which WP-34 showed is imperfect (invented relations).
- (c) **Hybrid.** Deterministic compiler for the static nine from spans; interpreter-authored, evidence-bound dynamics and T/S/P from the admitted context. Cost: two provenance regimes in one vector.

Either way the transducer has two outputs to build, `q17` and the driver tuple, and today it builds a sparse version of one.

---

## 1. What the tree does with each channel (consumers)

| consumer | formula | channels that matter |
|---|---|---|
| semantic target (L,S,T) | family means, normalised | all 9 static, equally within family |
| driver T (threat) | max(threat_amplitude, mean(L_contradiction, volatility, burstiness), mean(T_future, L_contradiction, threat_amplitude)) | threat_amplitude, L_contradiction, volatility, burstiness, T_future |
| driver S (sustenance) | max(decay, mean(recurrence, T_memory)) | decay, recurrence, T_memory |
| driver P (procreation) | max(novelty, mean(T_future·(1−0.55·L_contra), L_inference·(1−0.25·L_contra))) | novelty, T_future, L_inference, L_contradiction |
| wind magnitude | 1 + 3·threat + persistence + 0.75·recurrence + 0.5·L_inference | threat_amplitude, persistence, recurrence, L_inference |
| 8D routing axes 4–7 | weighted sums (see source) | every channel appears somewhere; `frequency` appears only in axis 6 at weight 0.20 and in no driver or wind term |
| routing confidence (axis 8) | 0.35 + 0.45·volatility | volatility |
| readout angle | weighted by the 9 static channels only | 9 static |

Consequence: a zero in `frequency` is almost invisible to the tree. A zero in `decay` or `novelty` removes one of the two arguments of a `max`, so the other argument silently decides S or P. A zero in `threat_amplitude` on neutral text is what makes T low, which is the intended physics.

## 2. The table

Columns: **U** = upstream glossary meaning. **P** = what the product compiler computes today and from what evidence. **Z** = exactly when it is zero. **C** = coupling to other channels (degrees of freedom). **R** = upstream's own reference construction, for comparison. **D** = candidate definition that is evidenced and never zero, or an honest "none".

### Static family S

**S_entity**
U: entities, variables, objects involved.
P: saturate(Σ entity-row confidence, 3.0); evidence = parser entity spans.
Z: text with no parsed entity.
C: independent; also leaks into S_topology at 0.25.
R: log_norm(#entities, 20).
D: none from spans alone. The only zero-free route is a continuous semantic estimate: cosine of the MiniLM passage vector against a frozen "entity-bearing" reference direction, mapped (1+cos)/2. Requires a frozen calibration corpus (this is WP-30 escalation 2, the unpassed perception gate). Changes meaning from "how many entities" to "how entity-like the text reads". Spans stay attached as support when present.

**S_dependency**
U: which depends on which.
P: saturate(depends_on/controls/contains/owns rows + active causal rows, 2.0).
Z: no non-negated dependency or causal relation.
C: shares active causal rows with S_topology (1.0), L_inference (0.35), T_sequence (0.5).
R: log_norm(#relations, 30).
D: same as S_entity: none from spans; continuous semantic estimate only, same cost.

**S_topology**
U: domain geometry, layout, dimensionality.
P: saturate(all non-negated orientations + active causal + 0.25·entity_weight, 3.0).
Z: no relations and no entities.
C: near-collinear with S_dependency and S_entity (it is a weighted sum of their inputs).
R: 0.45·entity + 0.45·dependency + 0.10·log_norm(#evidence, 20). Upstream's is also a sum of the other two.
D: as above. Note this channel is not a separate degree of freedom in either construction. A genuine topology measure would be a graph statistic of the directed fingerprint (density, longest path, branching), which is zero on an empty graph.

### Static family L

**L_rule**
U: applicable rules, laws, methods.
P: saturate(rule signals + constraint entities + 0.5·depends_on rows, 2.0).
Z: no rule signal, constraint entity or depends_on row.
C: mostly independent.
R: 0.55·log_norm(#constraints, 12) + 0.45·log_norm(#goals, 8).
D: none from spans; semantic estimate only.

**L_contradiction**
U: internal inconsistency.
P: saturate(contradiction signals + rejection signals + 0.7·negative/opposes/supersedes orientations, 1.5).
Z: no contradiction, rejection or negative orientation.
C: near-collinear with threat_amplitude (same rows, see below).
R: 0.45·contradiction deltas + 0.35·log_norm(#quarantine, 4) + 0.20·uncertainty.conflict + pressure.
D: none honest. A text with no inconsistency has zero inconsistency. This is the clearest case where the true value is zero.

**L_inference**
U: depth of inference required.
P: saturate(inference signals + inferred-modality causal rows + 0.35·active causal, 2.0).
Z: no inference signal and no causal relation.
C: shares active causal with S_dependency/S_topology/T_sequence.
R: 0.30·rule + 0.30·dependency + 0.20·log_norm(#deltas, 10) + 0.20·uncertainty.unknown + pressures. Upstream's is largely a function of two other channels.
D: "depth required" could be a graph statistic (longest directed chain in the fingerprint), which is ≥1 whenever any relation exists and undefined otherwise. Not zero-free.

### Static family T

**T_sequence**
U: required ordering of steps.
P: saturate(sequence signals + precedes/follows/supersedes rows + 0.5·active causal, 2.0).
Z: no temporal signal and no causal relation.
C: shares active causal.
R: 0.55·log_norm(#interventions + #observed_delta, 12) + 0.45·dependency.
D: none from spans; semantic estimate only.

**T_memory**
U: relevance of prior state.
P: clamp(1 − (1 − saturate(memory signals + 0.4·completions, 1.5))·(1 − 0.65·recurrence)). Blends spans with the recurrence channel.
Z: no memory/completion signal **and** recurrence = 0 (first turn, or orthogonal history).
C: not independent of recurrence by construction.
R: log_norm(memory_size, 12).
D: "relevance of prior state" is a property of the conversation, not the sentence. Candidate: the best chunk-pair similarity between this turn and the committed history, (1+cos)/2, plus explicit memory spans as support. Zero-free once history exists. **First turn has no prior state; no honest positive value exists.**

**T_future**
U: concern with later consequence.
P: saturate(future signals + 0.5·hypothetical rows + 0.25·outcome/state entities, 1.5).
Z: none of those.
C: independent.
R: 0.55·log_norm(#goals + #expected_delta, 10) + 0.45·inference + …
D: none from spans; semantic estimate only.

### Dynamics family

**threat_amplitude**
U: overall T_d pressure.
P: saturate(contradictions + rejections + 0.6·opposes/negative orientations + 0.7·non-negated prevents, 1.5), max over chunks.
Z: no contradiction, rejection, opposition or prevents relation.
C: shares almost every input with L_contradiction; effectively L_contradiction plus `prevents`. Not a separate degree of freedom today.
R: 0.36·contradiction + 0.25·future + 0.19·log_norm(#goals, 8) + typed failure pressure.
D: as a property of the sentence: none honest, neutral text carries no threat. As a property of the conversation state: unresolved contradictions in the committed history (count of committed contradiction spans not yet superseded) gives a genuine second degree of freedom, but is zero until the first contradiction ever appears.

**frequency**
U: recurrence rate of similar loads.
P: near_count / bounded_history_count, where near = combined similarity ≥ 0.70.
Z: empty history, or no item above threshold.
C: a statistic of the same boolean `near` series as persistence, burstiness and decay.
R: `frequency = recurrence` literally. Zero extra degrees of freedom upstream.
D: mean normalised similarity over the bounded window, (1+cos)/2, unthresholded. A true rate, distinct from recurrence (which is the max). Zero-free once history exists. **Undefined on the first turn.**

**persistence**
U: how long load holds.
P: trailing run of near matches / min(6, window).
Z: empty history, or the latest item not near.
C: same `near` series.
R: 0.42·recurrence + 0.25·sequence + 0.20·threat + pressures. A linear function of other channels upstream.
D: soft run-length: Σ_k Π_{i≤k} s_i over the window from most recent backwards, with s = normalised similarity, divided by the window. Zero-free once history exists (every s > 0 unless antipodal). **Undefined on the first turn.**

**burstiness**
U: sudden contradictions or events.
P: clamp(recent near-rate − earlier near-rate); negative change discarded.
Z: empty history, equal rates, or a falling rate (information destroyed).
C: same `near` series.
R: 0.50·terminal_failure/spike deltas + 0.50·volatility.
D: |recent mean similarity − earlier mean similarity| with the sign recorded separately (your decision). Zero only when the two means are exactly equal, which has measure zero with continuous similarities. Needs at least two history items to form two windows. **Undefined on turns 1–2.** Note the upstream meaning is about contradiction events, not similarity rates; the product has redefined this channel.

**volatility**
U: how quickly the structure changes.
P: clamp(0.65·‖static_now − static_prev‖/3 + 0.35·saturate(contradiction + rejection + supersedes rows, 1.5)).
Z: first turn with no change evidence, or identical static load and no change evidence.
C: depends on the 9 static channels of two turns; distinct statistic.
R: 0.45·contradiction + 0.35·state_change deltas + 0.20·threat.
D: add the semantic component: 1 − cos(passage_now, passage_prev). Then zero only when the text is semantically identical to the previous turn **and** structurally identical **and** carries no change evidence. A repeated identical sentence honestly has zero volatility. Not zero-free in that case; the zero would be true.

**novelty**
U: unfamiliar features.
P: 1 − max combined similarity; 1.0 on empty history.
Z: only when max similarity is exactly 1.0 (exact repeat).
C: **exactly 1 − recurrence.** Zero degrees of freedom.
R: 0.55·entity + 0.25·uncertainty.novelty (default 0.5, a prior) + 0.20·(1 − recurrence).
D: to make it a real channel it must measure something recurrence does not: distance from the centroid of committed history vectors (or, on the first turn, from the seed tree's leaf-vector distribution, which always exists). Nearest-neighbour similarity and centroid distance are different statistics. Zero only if the turn equals the centroid exactly. Tree-grounded on the first turn.

**recurrence**
U: match to prior signatures.
P: max combined similarity (0.8·chunk-pair cosine + 0.2·directed-graph Jaccard); 0.0 on empty history.
Z: empty history, or orthogonal history (exactly zero similarity).
C: drives novelty (exactly), T_memory (blend), and the `near` series.
R: 0.46·memory + 0.30·recurrence deltas + 0.24·pressure + …
D: keep as max similarity but on (1+cos)/2 so it is positive unless antipodal. **First turn: the conversation has no prior signatures.** The only always-present population of prior signatures is the seed tree's 10,000 branch leaf vectors. Defining first-turn recurrence as the best match of the load's static 8D projection against branch leaf vectors is evidenced and tree-grounded, but changes meaning from "conversation memory" to "tree familiarity" and must use the static-only projection to avoid circularity.

**decay**
U: **how uncertainty drops with classification.** This is not a staleness measure.
P: turns since last near match / 12; 1.0 when never matched. The product redefined this channel as staleness.
Z: latest item near-matched.
C: same `near` series; mutually exclusive in support with persistence.
R: clamp(1 − max(threat, persistence, inference)). Zero degrees of freedom upstream.
D: return to the upstream meaning with a tree-grounded statistic: classification margin, 1 − (second-best branch alignment / best branch alignment) over the cohort selection the gateway already computes read-only. Always defined, positive unless the top two branches tie exactly, and a genuinely new degree of freedom (how decisively the load lands on a niche). Feeds S as "sustenance from a clear classification", which matches the upstream driver.

## 3. Degrees of freedom, honestly counted

Product compiler today: nine static channels with shared inputs (roughly 7–8 independent), threat ≈ L_contradiction (≈0.3), novelty = 1 − recurrence (0), frequency/persistence/burstiness/decay = four statistics of one boolean series (≈2–3), volatility (1). **About thirteen.**

Upstream's own reference adapter: frequency = recurrence (0), decay = f(threat, persistence, inference) (0), persistence/volatility/burstiness/threat are linear combinations of other channels plus event counts, novelty carries a 0.5 prior. It is also not seventeen. The substrate does not currently define seventeen independent quantities either. Whether the 17D research fork does, only you can say.

## 4. The decision

With the no-zero rule fixed, the table shows three facts.

1. **The 8 dynamics channels can be made zero-free and mostly independent**, by replacing thresholded counts with continuous similarity statistics and by grounding `novelty`, `recurrence` and `decay` in the tree's own always-present population (branch leaf vectors, cohort alignment). Cost: `decay` and `burstiness` change meaning (decay back to upstream's; burstiness away from upstream's), and `T_memory`, `frequency`, `persistence` remain undefined on the first turn of a fresh project because there is no prior turn. Five of the eight need at least one committed turn.

2. **The 9 static channels and threat_amplitude cannot be made zero-free from spans.** A sentence with no contradiction has zero contradiction. The only zero-free construction is a continuous semantic estimate against frozen reference directions, which requires the calibration corpus you have not yet authorised (perception gate 2) and changes the channels from counts to degrees. Whether a calibrated MiniLM projection counts as evidence rather than a model guess is your call; MiniLM similarity already drives recurrence today.

3. **These three constraints are jointly unsatisfiable on a first-turn neutral sentence:** no zeros, no priors, text-only evidence. One must give. The options, each honest:
   - (a) admit tree state and conversation state as evidence (dynamics become zero-free after turn one; statics still need option b or c);
   - (b) admit calibrated continuous semantic estimates for the static channels;
   - (c) do not commit turns whose evidence does not cover all 17, which is WP-35 today and blocks nearly every turn;
   - (d) relax the no-zero rule, which you have rejected.

My recommendation, for you to accept or reject: (a) plus (b), sequenced. First the dynamics redesign with tree grounding, which needs no model calibration and can be replayed through the 10K tree immediately (the WP-36b shape). Then the static-channel calibration as the perception-gate-2 run it already is, so the same corpus serves both purposes. The first turn of a fresh project is committed in shadow mode only, since three channels have no prior to measure; authoritative commits begin at turn two.
