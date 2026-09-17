> **WITHDRAWN 2 September 2026 by owner review. Do not implement.** The evidenced-zero policy below legitimises a load that is not genuinely 17-dimensional. Superseded by a channel-semantics redesign decision, pending owner.

# WP-36a — Evidenced 17-channel load records and the evidenced-zero policy

**To:** Codex (implementing engineer)
**From:** Claude (orchestrator), for Ken Morkaya (owner)
**Date:** 2 September 2026
**Owner status:** approved 2 September 2026 with three corrections (§2.2 volatility support, §2.4 `no_change` and extended `no_match_in_window`) and two WP-36b decisions (§6). All are incorporated below. No formula changes.
**Branch:** `codex/wp-36a-evidenced-load17`, created from accepted WP-35 commit `a8cd854dde575721f8ea11729d4f8fe858c5b11b`
**Supersedes:** the WP-35 strict-positive policy (`tom-assist-strict-positive-load17/1.0`). This is a deliberate owner reversal of the "no zeros" directive: zeros are permitted when, and only when, the evidence record proves what the zero means.

No model generations. No tree replay campaign (that is WP-36b). No G-gate verdict issued or implied.

---

## 0. Why

WP-35 proved that the current compiler can never produce an all-positive 17-channel load, so authoritative mode is fully blocked. Replacing zeros with epsilons would falsely excite every channel and distort the 10K tree. The correct distinction is not "positive vs zero" but "evidenced vs unevidenced". Every channel must carry its value, how it was derived, what supports it, a deterministic confidence, and a rendered reason. A zero passes only when its recorded cause is one the owner has classified as honest.

Fact established in audit: every channel is *always* calculated by `compile_load` in `gateway/structural_analysis.py`. There is no "not calculated" state today. WP-36a makes that provable per channel rather than assumed.

## 1. Ground rules (unchanged)

- `tom_master` read-only at pinned `e9fdef81c8a366ebbec07be9772189eea15cb2ac`. `tom_master17D` off-limits. `tom_sicd_gemma` frozen.
- Do not modify `gateway/tom_gateway.py`, any frozen calibration artifact under `validation/runs/`, any pre-registration, golden, or the 10K seed artifact.
- Preview purity holds: no preview path calls `rgm.read_memory`, `ToMClient.process`, or `engine.step`. `gateway/tests/test_preview_purity.py` must stay green.
- Every path that constructs or applies a 17-channel load operates on the pinned Python 10K tree only.
- Product default mode stays `legacy` (`TOM_ASSIST_STRUCTURE_MODE` default in `gateway/evidence_gateway.py`). WP-36a makes authoritative mode *passable* under test; it does not activate it in the product.
- Escalate contradictions in `BUILD_LOG.md` with `ESCALATE WP36a-n`; pick the safest reversible default; continue non-dependent work.

## 2. Deliverable 1 — per-channel evidence records

`compile_load` returns a new key `channel_records`: a list of exactly 17 objects, in canonical `CHANNELS` order. It sits inside the `base` dict of `build_analysis`, so it is covered by `analysis_digest`, replayed exactly by `validate_frozen_analysis`, and archived at commit via `retain_structural_commit`.

Each record:

| field | type | rule |
|---|---|---|
| `channel` | string | canonical channel name |
| `value` | float | byte-identical to `load_signature[channel]` |
| `derivation` | string | fixed per-channel formula string from the table in §2.1; never free text |
| `inputs` | object | the scalar intermediates actually used (e.g. `entity_weight`, `turns_since_match`, `recent_rate`, `earlier_rate`, `max_similarity`); all finite floats/ints/null |
| `support` | list | zero or more support items (§2.2). Non-empty whenever `value > 0`. |
| `confidence` | float in [0,1] | deterministic, from §2.3 |
| `zero_kind` | string or null | null iff `value > 0`; otherwise one of the enum in §2.4 |
| `reason` | string | rendered from a fixed per-channel template over the record's own fields (§2.5) |

### 2.1 Derivation table

One fixed string per channel, checked into code as a constant mapping, e.g. `S_entity: "saturate(entity_weight, 3.0)"`, `decay: "1.0 if turns_since_match is None else clamp(turns_since_match / HISTORY_WINDOW)"`, `T_memory: "clamp(1 - (1 - saturate(memory_weight, 1.5)) * (1 - 0.65 * recurrence))"`. The strings document the existing arithmetic. **No channel formula changes in WP-36a.**

### 2.2 Support items

Static channels and `threat_amplitude`: one item per contributing parser row, `{"kind":"span","chunk":i,"path":"entities[2].evidence","start":..,"end":..,"quote":..,"weight":..,"confidence":..}` where `path` is the validated row path and `weight` is that row's contribution (including the fractional multipliers already in `_static_load`). Only rows with non-zero contribution are listed.

Dynamic channels: `{"kind":"history","commit_key":..,"combined_similarity":..,"near":bool}` for each bounded history item consulted, plus one `{"kind":"history_window","bounded_count":n,"window":HISTORY_WINDOW,"near_threshold":NEAR_SEMANTIC_THRESHOLD}`. `T_memory` lists both its span items and its recurrence history items, because its value blends both.

`volatility` blends two sources and must list both: the previous committed `static_load` record it was measured against (a `history` item carrying `static_distance_from_previous`), and, whenever `change_evidence > 0`, one `span` item per contributing current-turn contradiction, rejection or `supersedes` orientation row. A positive volatility driven by a contradiction or rejection is not adequately supported by history records alone.

Support items must be derived from data already validated by the compiler. Offsets come from the resolved spans, never from a model.

### 2.3 Confidence (deterministic)

- Static channel with support: maximum `confidence` among supporting rows.
- Static channel with no support (evidence absent): the candidate-level `confidence` from the parser (its confidence that the declared structure is complete). This is the confidence that the absence is real.
- Dynamic channel, empty bounded history: `1.0`.
- Dynamic channel, non-empty history: the candidate-level `confidence` of the current turn (the history side is committed and fixed).

Codex may propose a different table in an `ESCALATE` if this one is unsound, but the implemented table must use only inputs already in the record and must be byte-stable.

### 2.4 Zero kinds

| `zero_kind` | applies to | meaning | authoritative |
|---|---|---|---|
| `absent_evidence` | 9 static, `threat_amplitude` | no parser row contributed weight | allowed |
| `empty_history` | `frequency`, `persistence`, `burstiness`, `recurrence`, `volatility` | bounded history empty (for `volatility`, also no change evidence) | allowed |
| `no_match_in_window` | `frequency`, `persistence`, `recurrence` | history present and no near match at all (`near_count == 0`); for `recurrence`, history present and `max_similarity == 0.0` (orthogonal history) | allowed |
| `no_change` | `volatility` | history present, `static_distance_from_previous == 0.0` and `change_evidence == 0.0` | allowed |
| `streak_broken` | `persistence` | `near_count > 0` but the latest history item did not near-match | allowed |
| `fresh_match` | `decay` | latest history item near-matched (`turns_since_match == 0`) | allowed |
| `rate_unchanged` | `burstiness` | `recent_rate == earlier_rate` | allowed |
| `exact_recurrence` | `novelty` | `max_similarity == 1.0` | allowed |
| `clamped_negative` | `burstiness` | `recent_rate < earlier_rate`; sign discarded by `_clamp` | **disallowed — fail closed** |

Rationale for the one disallowed kind: it is the only zero in the current compiler that destroys information. Every other zero is a true statement supported by a named span or history record. Persistence and decay are mutually exclusive in support but each zero is honestly evidenced by the latest history record, so they are allowed.

Classification is deterministic and exclusive: exactly one kind applies to a given zero. For `persistence`, `no_match_in_window` takes precedence over `streak_broken` (an all-miss window is not a broken streak). A value of `0.0` reached with a `zero_kind` outside this table, or with an ambiguous cause, is a compiler bug: raise, do not classify. `-0.0` is normalised to `0.0` before classification.

### 2.5 Reason

One template per channel, rendered with the record's `value`, `inputs`, `zero_kind` and support count. Example: `"S_entity = 0.42: saturate(entity_weight=1.60, 3.0); 3 entity spans, max confidence 0.80."` The reason is display-only. Nothing may parse it. A test asserts that re-rendering the template from the stored record reproduces the stored string exactly.

## 3. Deliverable 2 — evidenced-load policy replaces strict-positive

- Remove `require_strictly_positive_load` and `STRICT_POSITIVE_LOAD_POLICY`.
- Add `require_evidenced_load(analysis) -> dict[str, float]` in `gateway/structural_analysis.py`. It passes iff: exactly 17 records in canonical order; each `value` equals `load_signature`; each `value > 0` has non-empty support and `zero_kind is None`; each `value == 0` has an allowed `zero_kind`; all confidences finite in [0,1]; each `reason` re-renders exactly. On failure it raises naming every failing channel with its `zero_kind` and the policy identity. It never rewrites a value.
- Policy identity `tom-assist-evidenced-load17/1.0`. `COMPILER_VERSION` → `tom-assist-evidence-load17/1.2`. `ANALYSIS_VERSION` → `tom-assist-structural-analysis/1.3`. `EVIDENCE_GATEWAY_VERSION` → `tom-gateway-evidence/1.2`.
- Guard runs at the same two points as WP-35 in `gateway/evidence_gateway.py`: after `build_analysis` in authoritative preview, and after `validate_frozen_analysis` at authoritative commit before `LoadSignature` construction. Shadow mode exposes `channel_records` and the would-be policy result in preview and commit output but never gates.

### 3.1 Capabilities contract, changed in lockstep

Remove `strict_positive_load_policy` and `authoritative_requires_all_17_channels_positive`. Add:

```
"load_evidence_policy": {"const": "tom-assist-evidenced-load17/1.0"},
"authoritative_requires_all_17_channels_evidenced": {"const": true},
"authoritative_disallowed_zero_kinds": {"const": ["clamped_negative"]}
```

Update together: `crates/protocol/schemas/tom-capabilities.schema.json`, `crates/protocol/src/model.rs` (`#[serde(default)]`), `packages/schema-generated/index.ts`, `tests/fixtures/protocol/examples.json`, and the `structural_load_compiler_version` const. `npm run schema:validate` must pass.

## 4. Tests (required, deterministic, fixture provider only)

Use the existing `_Provider` fixtures in `gateway/tests/test_evidence_loads.py`; extend them only as needed. No model calls.

1. **Shape and identity.** 17 records, canonical order, `value` byte-equal to `load_signature`, `derivation` matches the constant table, every positive has support, every zero has an allowed-or-disallowed kind, `reason` re-renders exactly.
2. **Determinism.** `channel_records` byte-identical across gateway restart and across `validate_frozen_analysis` replay. A hand-edited record fails replay with "does not replay exactly".
3. **Pre-declared zero-kind table.** For each case below, the test declares the expected `zero_kind` per channel *before* asserting:
   - **Case 1**, first turn `"A causes B."` → static absences `absent_evidence`, `threat_amplitude` `absent_evidence`, `frequency`/`persistence`/`burstiness`/`recurrence`/`volatility` `empty_history`, `novelty`=1.0, `decay`=1.0.
   - **Case 2**, second turn `"A causes B."` → `persistence > 0`, `recurrence > 0`, `burstiness > 0`, `decay` zero `fresh_match`, `volatility` zero `no_change` (identical static load, no change evidence).
   - **Case 3**, `"A causes B."`, `"A causes B."`, then `"B causes A."` → assert against the computed near flags and `max_similarity`, not assumed ones. If the fixture profiles are orthogonal and the reversed graph has zero overlap: `frequency`/`persistence` `no_match_in_window`, `recurrence` `no_match_in_window` with `max_similarity == 0.0`, `decay`=1.0, `burstiness` `rate_unchanged`, `volatility` `no_change` (static magnitudes are label-blind, so a reversal leaves them identical; the record must make that visible).
   - **Case 4**, `"A causes B."`, `"B causes A."`, then `"A causes B."` → `near == [True, False]`: `persistence` `streak_broken`, `frequency == 0.5`, `decay > 0`.
   - **Case 5**, a declining-rate sequence (near matches early, none in the last four, at least 5 committed turns so `earlier` is non-empty) → `burstiness` `clamped_negative`.
   Declare the full 17-entry expected table for every case in the test source before the assertions.
4. **Authoritative round trip succeeds.** First turn `"A causes B."` in authoritative mode passes the guard, reaches the pinned 10K tree, and commits: engine tick advances by exactly one step of the five-dynamics commit, `structural_commits` count +1, and the plan carries a 17-entry `load_signature_17`, an all-positive 3-entry `driver_vec`, a 3-entry `semantic_target`, an 8-entry `routing_basis_8d`, `routing_basis_confidence > 0`, `wind_magnitude > 0`. This restores the assertions WP-35 deleted.
5. **Authoritative fail-closed on the disallowed kind.** The declining-rate sequence in authoritative mode raises at preview naming `burstiness` and `clamped_negative`; serialized engine/RGM bytes, tree tick and `structural_commits` count are unchanged. A direct commit posting that analysis also fails before `LoadSignature`.
6. **Shadow never gates.** The same declining-rate sequence in shadow mode commits, and the result exposes the records and the would-be policy failure.
7. **Preview purity** suite unchanged and green. **Frozen-artifact scan** unchanged and green.

Full regression required: Python `gateway/tests validation/tests`, `cargo test --workspace`, `cargo fmt --all -- --check`, `git diff --check`, `npm run extension:test`, `npm run desktop:test`, `npm run schema:validate`.

## 5. Frozen artifact caution

WP-31 to WP-34 runs under `validation/runs/` recorded compiler version 1.1 outputs. If any existing test replays a frozen artifact through the *current* compiler and compares digests, the version bump will break it. That is an `ESCALATE`, not a golden edit and not a version pin-back. Report it and stop that test's dependency from being silently rewritten.

## 6. Out of scope for WP-36a (owner decisions before WP-36b)

1. **Burstiness semantics — DECIDED (owner, 2 Sep 2026).** Redefine `burstiness` as the absolute change magnitude `|recent_rate - earlier_rate|`, with the original sign recorded separately in the record's `inputs`. This is a distinct compiler-version change, implemented in its own numbered package after WP-36a, not folded into 36a. Until it lands, `clamped_negative` remains the disallowed kind.
2. **Near-zero authoritative loads — DECIDED (owner, 2 Sep 2026).** Do not invent a threshold. Initially skip a tree step only when the canonical projected driver/wind is exactly zero. Genuinely small non-zero loads are characterised from WP-36b telemetry before any threshold is selected.
3. **WP-36b replay** of causal, reversal, persistence, decay and neutral cases through the real 10K tree, recording `17D evidence → T/S/P → 8D routing → wind → selected branches → tree change`, with expected directions pre-registered before the run and a shadow-mode baseline for each case.

## 7. Housekeeping and reporting

- Remove the Rust `target/` build output after testing; report its size.
- Append one `## WP-36a` section to `BUILD_LOG.md` in the §11 format: commit, evidence lines with counts, decisions with `file:line`, deviations, escalations, protection proof (tom_master HEAD, status/diff SHA-256s against the recorded baselines `efd935fa…` and `86cb4a85…`).
- Stop for owner audit. No G-gate verdict.

## 8. Definition of done

1. `channel_records` present in every analysis, digest-covered, archived, replay-exact.
2. Strict-positive policy removed; evidenced-load policy enforced at both authoritative points; shadow exposes but never gates.
3. Capabilities, schema, Rust, TypeScript and fixture updated together; `schema:validate` green.
4. Tests §4.1–4.7 green; authoritative round trip on first-turn `"A causes B."` reaches the pinned 10K tree and the WP-35-deleted telemetry assertions are back.
5. Full regression green; frozen artifacts untouched; upstream protection proof recorded.
6. `BUILD_LOG.md` section appended; escalations listed; stopped for audit.
