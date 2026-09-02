# WP-31 owner review

**POST-HOC LOCAL DIAGNOSTIC — NOT A GATE. The frozen run is unchanged.**

## Plain result

The frozen run made **52 logical passage attempts**. It did not instrument the exact number of internal per-window Gemma calls for passages that failed partway through, so no exact local-generation total is claimed. Provider/OAuth calls were exactly **0**.

The exact pinned local parser produced strict usable analyses for **35/52** passages. It failed closed on **17**. End-to-end exact cases were **33/52**.

Across all attempted relation cases, **34/50** expected relations survived end to end. Among strict accepted analyses, every expected relation was directionally correct and there were **0 reversals**. Structural signals were weak: **1/10** survived end to end.

## Parser failure taxonomy

- `ambiguous_evidence_quote`: 4 — MR-01, MR-02, MR-03, SG-02
- `extra_schema_field`: 3 — LP-02, MR-04, PP-05A
- `invalid_tool_json`: 4 — LP-01, MR-05, OR-03, SG-04
- `missing_evidence_quote`: 5 — CD-08, CD-10, LP-05, SG-06, SG-08
- `missing_tool_call`: 1 — SG-01

## Multi-vector and paraphrase findings

- Long-position passages: 3/6 strict observations; 2 were actually multi-chunk.
- Overlap punctuation duplication occurred in: LP-03, LP-06.
- Paraphrases: 4/5 complete pairs; all 4 complete pairs had equal directed graphs, and 3 were mutual MiniLM top-1 neighbours.
- Paraphrase semantic similarity range: 0.885888–0.976266; 17D L1 range: 0.000000–0.194033.

## 17-channel interpretation

The accepted analyses always contained all 17 finite bounded values. Non-zero
counts across the 35 accepted passages were:

- `S_entity`: 35/35 (median 0.486583, max 0.736403)
- `S_dependency`: 23/35 (median 0.393469, max 0.632121)
- `S_topology`: 35/35 (median 0.393469, max 0.632121)
- `L_rule`: 0/35 (median 0.000000, max 0.000000)
- `L_contradiction`: 2/35 (median 0.000000, max 0.372911)
- `L_inference`: 20/35 (median 0.160543, max 0.490844)
- `T_sequence`: 23/35 (median 0.221199, max 0.393469)
- `T_memory`: 1/35 (median 0.000000, max 0.486583)
- `T_future`: 6/35 (median 0.000000, max 0.283469)
- `threat_amplitude`: 6/35 (median 0.000000, max 0.372911)
- `frequency`: 0/35 (median 0.000000, max 0.000000)
- `persistence`: 0/35 (median 0.000000, max 0.000000)
- `burstiness`: 0/35 (median 0.000000, max 0.000000)
- `volatility`: 1/35 (median 0.000000, max 0.170304)
- `novelty`: 35/35 (median 1.000000, max 1.000000)
- `recurrence`: 0/35 (median 0.000000, max 0.000000)
- `decay`: 35/35 (median 1.000000, max 1.000000)

Each case used empty committed history. Zero frequency/persistence/burstiness/recurrence and unit novelty/decay are expected here and do not measure history dynamics.

## Owner decision recommended

Do not activate or production-freeze the local parser yet. Direction was coherent whenever strict validation succeeded, but parser/schema reliability, signal extraction and multi-relation handling require a versioned correction before calibration v2. The overlap punctuation duplication found here was corrected deterministically after the run; the frozen observations remain unchanged.

Calibration v2 should retain this run, carry the deterministic overlap correction,
make the model-tool boundary more reliable for repeated entities and multiple
relations, and explicitly strengthen all eight signal instructions. It should
then rerun under a new identity; this result must not be overwritten.
