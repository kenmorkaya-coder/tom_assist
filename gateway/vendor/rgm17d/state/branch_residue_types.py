"""Branch residue data types — TOM-TREE-OWNED-CAUSAL-RECALL Phase 1.

Domain-neutral structural memory cells attached to ``BranchState`` by
load resonance. Each branch carries a bounded tuple of these residues
so the tree can become the strategy carrier — when a similar load
shape recurs, the resonant branch surfaces its remembered causal path
and the authority gate may follow the proposal.

This module is the **leaf** of the state layer. It must import only
from the standard library — no ``agency/``, no ``memory/``, no
``integration/``. The dataclasses are pure data; lifecycle policy
(add / update / prune) lives in ``memory/branch_residues.py`` which
imports these types.

See ``docs/contracts/tree_owned_causal_recall_spec.md`` rev 3 for the
full design. This file ships Phase 1 only — no retrieval, no scorer
integration, no behavior change.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple


LOAD_DELTA_CHANNEL_COUNT = 17
LOAD_DELTA_SCHEMA_VERSION = 1
_ZERO_LOAD_DELTA_TUPLE = tuple(0.0 for _ in range(LOAD_DELTA_CHANNEL_COUNT))


AUTHORITY_GROUNDING_KINDS = frozenset(
    {
        "verifier_relief",
        "self_entity_moved",
        "controlled_entity_moved",
        "target_entity_state_changed",
        "route_or_option_gain",
    }
)


def _safe_finite_float(value: Any, *, default: float = 0.0) -> float:
    """Parse a float, returning ``default`` for None / non-finite /
    unparseable inputs. Used by ``from_dict`` paths so malformed
    snapshots (NaN / Inf / garbage strings) cannot poison the
    in-memory dataclass."""
    if value is None:
        return float(default)
    try:
        v = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(v):
        return float(default)
    return v


def _safe_clamped_float(
    value: Any,
    *,
    lo: float,
    hi: float,
    default: float = 0.0,
) -> float:
    """Like ``_safe_finite_float`` but additionally clamps to [lo, hi]."""
    v = _safe_finite_float(value, default=default)
    if v < lo:
        return float(lo)
    if v > hi:
        return float(hi)
    return v


@dataclass(frozen=True)
class ResidueEdgeRef:
    """One edge in a remembered causal path.

    References the canonical IDs already maintained by
    ``memory/causal_sequence_map.py`` (CausalEdge) and
    ``memory/backprop_credit.py`` (BackpropCreditRecord) and the
    RGM scene memory. The residue is a compact INDEX into the
    system's authoritative memory of what happened — not a copy.

    Only authority-grounded edges can drive tree proposals downstream;
    the ``grounding_kind`` field carries the categorisation so
    retrieval can filter weak evidence at recall time.
    """

    intervention_id: str
    operator_id: str
    outcome_kind: str
    grounding_kind: str
    grounding_confidence: float

    # Canonical references — pointers, not copies. Empty strings allowed
    # when a reference isn't available; retrieval filters on
    # ``grounding_kind`` rather than on these.
    causal_edge_id: str = ""
    backprop_record_id: str = ""
    rgm_snapshot_id: str = ""
    source_state_signature: str = ""
    post_state_signature: str = ""

    # Credit / evidence (authoritative copies of the small scalars)
    s_credit: float = 0.0
    p_credit: float = 0.0
    negative_credit: float = 0.0

    # Self-binding and predicate context — used by recall to reject a
    # residue if the current state doesn't satisfy the required
    # preconditions.
    self_binding_status: str = "unknown"
    self_entity_id: str = ""
    required_predicate_ids: Tuple[str, ...] = ()
    spatial_relation_ids: Tuple[str, ...] = ()
    entity_delta_refs: Tuple[str, ...] = ()

    # Saturation / failure flags lifted from causal_sequence_map at
    # deposit time. Carried so retrieval can see at a glance that a
    # residue's path is structurally compromised.
    saturated: bool = False
    failure_interpretation: str = ""

    # ----- Phase 2C (TOM-TREE-OWNED-CAUSAL-RECALL) — write-only metadata.
    # See ``docs/contracts/tree_owned_recall_phase2_spec.md``.
    #
    # The phase_signature_* fields carry the bridge-grounding catalog's
    # motif identity and outcome tendency at deposit time. The
    # grounding_* flags carry per-edge causal-binding evidence.
    #
    # **WRITE-ONLY METADATA.** Per Ken's Phase 2C approval condition,
    # NO selector, router, recall-priority, or routing decision code
    # path may read these fields. Phase 3 will gate when they become
    # consumable. CI / static-grep audit (acceptance criteria L8 in
    # the spec) enforces this constraint.
    phase_signature_motif_id: str | None = None
    phase_signature_slot: int | None = None
    # Frozen mapping → tuple of (label, weight) pairs sorted by label
    # so equality / hashing on the frozen dataclass stays deterministic.
    phase_signature_outcome_tendency: Tuple[Tuple[str, float], ...] | None = None
    phase_signature_catalog_version: str | None = None

    # Tri-state grounding flags. **DO NOT collapse None to False.**
    #   None  = "not enough evidence to know"
    #   False = "evidence exists; this was NOT bound to that kind"
    #   True  = "evidence exists; this WAS bound to that kind"
    grounding_self_bound: bool | None = None
    grounding_route_bound: bool | None = None
    grounding_target_state_bound: bool | None = None

    # ----- Phase 3 (TOM-TREE-OWNED-CAUSAL-RECALL) — conditional-
    # expectation record. WRITE-ONLY METADATA per Ken's standing
    # verdict. Recorded deposit-time branch information state; not
    # read by any selector / router / recall path (CI L8 audit
    # extended to cover all ten field names below). Phase 4 will
    # gate consumption.
    #
    # See ``docs/contracts/tree_owned_recall_phase3_spec.md``.

    # Closed-vocabulary lists of conditioning variables. EMPTY tuple
    # is DISTINCT from None: None = "we didn't try to record",
    # empty = "we tried, found none". Variable names sourced from
    # ``memory/conditional_projection.CONDITIONING_VARIABLE_VOCABULARY``.
    conditioning_variables_present: Tuple[str, ...] | None = None
    conditioning_variables_missing: Tuple[str, ...] | None = None

    # Provenance for the conditioning evidence — distinguishes the
    # "detector fired this tick" case (23%) from "scene_card carried
    # the tag from a prior tick" (additional 74pp to 97% effective
    # coverage observed on dc22-fdcac232). Closed vocabulary;
    # members come from CONDITIONING_PROVENANCE_VOCABULARY.
    conditioning_provenance: str | None = None

    # Predicted credit per S/P/T channel — derived from the motif's
    # outcome_tendency via the closed mapping table in
    # ``memory/conditional_projection``. Bounded [-0.5, +1.0].
    # None = "no prediction made".
    predicted_s_credit: float | None = None
    predicted_p_credit: float | None = None
    predicted_t_credit: float | None = None

    # Prediction error per channel = observed - predicted. None
    # when either side is None. Unbounded (positive = under-
    # predicted, negative = over-predicted).
    prediction_error_s: float | None = None
    prediction_error_p: float | None = None
    prediction_error_t: float | None = None

    # Observed T-channel credit. ResidueEdgeRef already has
    # `s_credit` and `p_credit` from Phase 1 but no explicit T
    # channel (only `negative_credit`, which is failure pressure,
    # NOT the T observation). Phase 3 adds `t_credit` symmetrically
    # so `prediction_error_t = t_credit - predicted_t_credit` is
    # unambiguous. Populated from the corresponding
    # `backprop_credit_record.t_credit` at deposit time. Default
    # 0.0 to stay symmetric with the existing s_credit / p_credit
    # defaults; "no observation" is distinguished from "observed
    # and zero" by the existing `backprop_record_id` field (empty
    # string = no observation).
    t_credit: float = 0.0

    # ----- Tree-as-reasoner Step 7 / P2 — edge-resident 17-channel
    # predictive-coding load delta. These replace the observer JSONL
    # as the live state home. None preserves sparse legacy state;
    # populated tuples are canonical 17-channel order from
    # utils.sicd_msr_channels.CHANNEL_NAMES.
    load_delta_predicted: Tuple[float, ...] | None = None
    load_delta_observed: Tuple[float, ...] | None = None
    load_prediction_error: Tuple[float, ...] | None = None
    pair_credit_by_channel: Tuple[float, ...] | None = None
    precision_by_channel: Tuple[float, ...] | None = None
    edge_prediction_last_tick: int | None = None
    load_delta_schema_version: int | None = None

    @property
    def authority_grounded(self) -> bool:
        return (
            self.grounding_kind in AUTHORITY_GROUNDING_KINDS
            and float(self.grounding_confidence) >= 0.70
        )

    def to_dict(self) -> dict[str, Any]:
        d = {
            "intervention_id": self.intervention_id,
            "operator_id": self.operator_id,
            "outcome_kind": self.outcome_kind,
            "grounding_kind": self.grounding_kind,
            "grounding_confidence": float(self.grounding_confidence),
            "causal_edge_id": self.causal_edge_id,
            "backprop_record_id": self.backprop_record_id,
            "rgm_snapshot_id": self.rgm_snapshot_id,
            "source_state_signature": self.source_state_signature,
            "post_state_signature": self.post_state_signature,
            "s_credit": float(self.s_credit),
            "p_credit": float(self.p_credit),
            "negative_credit": float(self.negative_credit),
            "self_binding_status": self.self_binding_status,
            "self_entity_id": self.self_entity_id,
            "required_predicate_ids": list(self.required_predicate_ids),
            "spatial_relation_ids": list(self.spatial_relation_ids),
            "entity_delta_refs": list(self.entity_delta_refs),
            "saturated": bool(self.saturated),
            "failure_interpretation": self.failure_interpretation,
        }
        # Phase 2C write-only metadata — emit ONLY when populated so
        # pre-Phase-2 readers see a backward-compatible payload. None
        # values are preserved (vs. False) so the tri-state semantics
        # on grounding_* flags survive round-trip.
        if self.phase_signature_motif_id is not None:
            d["phase_signature_motif_id"] = self.phase_signature_motif_id
        if self.phase_signature_slot is not None:
            d["phase_signature_slot"] = int(self.phase_signature_slot)
        if self.phase_signature_outcome_tendency is not None:
            d["phase_signature_outcome_tendency"] = [
                [str(k), float(v)] for k, v in self.phase_signature_outcome_tendency
            ]
        if self.phase_signature_catalog_version is not None:
            d["phase_signature_catalog_version"] = self.phase_signature_catalog_version
        if self.grounding_self_bound is not None:
            d["grounding_self_bound"] = bool(self.grounding_self_bound)
        if self.grounding_route_bound is not None:
            d["grounding_route_bound"] = bool(self.grounding_route_bound)
        if self.grounding_target_state_bound is not None:
            d["grounding_target_state_bound"] = bool(self.grounding_target_state_bound)
        # Phase 3 — write-only conditional-expectation record. Only
        # emit populated fields so pre-Phase-3 readers see a backward-
        # compatible payload. None values stay absent.
        if self.conditioning_variables_present is not None:
            d["conditioning_variables_present"] = list(self.conditioning_variables_present)
        if self.conditioning_variables_missing is not None:
            d["conditioning_variables_missing"] = list(self.conditioning_variables_missing)
        if self.conditioning_provenance is not None:
            d["conditioning_provenance"] = self.conditioning_provenance
        if self.predicted_s_credit is not None:
            d["predicted_s_credit"] = float(self.predicted_s_credit)
        if self.predicted_p_credit is not None:
            d["predicted_p_credit"] = float(self.predicted_p_credit)
        if self.predicted_t_credit is not None:
            d["predicted_t_credit"] = float(self.predicted_t_credit)
        if self.prediction_error_s is not None:
            d["prediction_error_s"] = float(self.prediction_error_s)
        if self.prediction_error_p is not None:
            d["prediction_error_p"] = float(self.prediction_error_p)
        if self.prediction_error_t is not None:
            d["prediction_error_t"] = float(self.prediction_error_t)
        # t_credit is non-Optional (default 0.0). Emit when non-zero
        # to keep legacy snapshots compact; absent value parses as 0.0.
        if float(self.t_credit) != 0.0:
            d["t_credit"] = float(self.t_credit)
        # Step 7 / P2 — edge-resident 17-channel load-delta state.
        # Emit only when populated so legacy/unbound residues remain
        # compact and backward-compatible.
        if self.load_delta_predicted is not None:
            d["load_delta_predicted"] = [float(v) for v in self.load_delta_predicted]
        if self.load_delta_observed is not None:
            d["load_delta_observed"] = [float(v) for v in self.load_delta_observed]
        if self.load_prediction_error is not None:
            d["load_prediction_error"] = [float(v) for v in self.load_prediction_error]
        if self.pair_credit_by_channel is not None:
            d["pair_credit_by_channel"] = [float(v) for v in self.pair_credit_by_channel]
        if self.precision_by_channel is not None:
            d["precision_by_channel"] = [float(v) for v in self.precision_by_channel]
        if self.edge_prediction_last_tick is not None:
            d["edge_prediction_last_tick"] = int(self.edge_prediction_last_tick)
        if self.load_delta_schema_version is not None:
            d["load_delta_schema_version"] = int(self.load_delta_schema_version)
        return d

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ResidueEdgeRef":
        # Float fields use ``_safe_finite_float`` so NaN / Inf /
        # garbage strings in a malformed snapshot do not poison the
        # in-memory dataclass. ``grounding_confidence`` is additionally
        # clamped to [0, 1] since the authority_grounded predicate
        # checks `>= 0.70` and out-of-range values would either
        # trivially clear or trivially miss that test.
        # Phase 2C tri-state parsing. Returns None when the key is
        # absent OR the stored value is null. Returns the bool value
        # otherwise. Strings "true"/"false" are tolerated for hand-
        # edited snapshots. DO NOT default to False — None carries the
        # "no evidence" semantic that False would destroy.
        def _tri_state_bool(key: str) -> bool | None:
            if key not in d:
                return None
            v = d[key]
            if v is None:
                return None
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return bool(v)
            if isinstance(v, str):
                low = v.strip().lower()
                if low in ("true", "1", "yes", "y"):
                    return True
                if low in ("false", "0", "no", "n"):
                    return False
                # Unrecognised string — preserve "no evidence" semantic.
                return None
            return None

        # Outcome tendency stored as list-of-[label, weight] pairs.
        raw_tendency = d.get("phase_signature_outcome_tendency")
        tendency: Tuple[Tuple[str, float], ...] | None = None
        if isinstance(raw_tendency, (list, tuple)):
            parsed: list[Tuple[str, float]] = []
            for item in raw_tendency:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    parsed.append((str(item[0]), _safe_finite_float(item[1])))
                elif isinstance(item, Mapping):
                    for k, v in item.items():
                        parsed.append((str(k), _safe_finite_float(v)))
            tendency = tuple(parsed) if parsed else None

        slot_raw = d.get("phase_signature_slot")
        slot: int | None = None
        if slot_raw is not None:
            try:
                slot_val = int(slot_raw)
                slot = slot_val if 0 <= slot_val <= 64 else None
            except (TypeError, ValueError):
                slot = None

        motif_id_raw = d.get("phase_signature_motif_id")
        motif_id = str(motif_id_raw) if motif_id_raw not in (None, "") else None
        catalog_ver_raw = d.get("phase_signature_catalog_version")
        catalog_ver = str(catalog_ver_raw) if catalog_ver_raw not in (None, "") else None

        # Phase 3 parsers. None when the key is absent. Empty tuple
        # when an explicit empty list was stored (DISTINCT semantic).
        def _phase3_tuple(key: str) -> Tuple[str, ...] | None:
            if key not in d:
                return None
            v = d[key]
            if v is None:
                return None
            if isinstance(v, (list, tuple)):
                return tuple(str(item) for item in v if item is not None)
            return None

        def _phase3_str(key: str) -> str | None:
            if key not in d:
                return None
            v = d[key]
            if v is None or v == "":
                return None
            return str(v)

        def _phase3_float(key: str) -> float | None:
            if key not in d:
                return None
            v = d[key]
            if v is None:
                return None
            try:
                f = float(v)
            except (TypeError, ValueError):
                return None
            if not math.isfinite(f):
                return None
            return f

        def _p2_float_tuple(key: str) -> Tuple[float, ...] | None:
            if key not in d:
                return None
            raw = d[key]
            if raw is None:
                return None
            if isinstance(raw, Mapping):
                # Older diagnostic payloads used channel-name maps.
                # State cannot import the channel order, so mapping
                # payloads are intentionally rejected here; memory-layer
                # writers must serialise canonical tuples/lists.
                return None
            if not isinstance(raw, (list, tuple)):
                return None
            if len(raw) != LOAD_DELTA_CHANNEL_COUNT:
                return None
            parsed: list[float] = []
            for item in raw:
                try:
                    f = float(item)
                except (TypeError, ValueError):
                    return None
                if not math.isfinite(f):
                    return None
                parsed.append(f)
            return tuple(parsed)

        def _p2_int(key: str) -> int | None:
            if key not in d:
                return None
            v = d[key]
            if v is None:
                return None
            try:
                return int(v)
            except (TypeError, ValueError):
                return None

        load_delta_predicted = _p2_float_tuple("load_delta_predicted")
        load_delta_observed = _p2_float_tuple("load_delta_observed")
        load_prediction_error = _p2_float_tuple("load_prediction_error")
        pair_credit_by_channel = _p2_float_tuple("pair_credit_by_channel")
        precision_by_channel = _p2_float_tuple("precision_by_channel")
        edge_prediction_last_tick = _p2_int("edge_prediction_last_tick")
        load_delta_schema_version = _p2_int("load_delta_schema_version")

        if motif_id is not None:
            # Step 7 / P2 migration: legacy motif-bound edges are the
            # sparse residency target, even when the observer JSONL has
            # been deleted. Backfill missing 17D state with the same
            # cold-start zero prior used by the former observer path.
            if (
                load_prediction_error is None
                and load_delta_predicted is not None
                and load_delta_observed is not None
            ):
                load_prediction_error = tuple(
                    float(load_delta_observed[index])
                    - float(load_delta_predicted[index])
                    for index in range(LOAD_DELTA_CHANNEL_COUNT)
                )
            load_delta_predicted = load_delta_predicted or _ZERO_LOAD_DELTA_TUPLE
            load_delta_observed = load_delta_observed or _ZERO_LOAD_DELTA_TUPLE
            load_prediction_error = load_prediction_error or _ZERO_LOAD_DELTA_TUPLE
            pair_credit_by_channel = pair_credit_by_channel or _ZERO_LOAD_DELTA_TUPLE
            precision_by_channel = precision_by_channel or _ZERO_LOAD_DELTA_TUPLE
            if edge_prediction_last_tick is None:
                edge_prediction_last_tick = 0
            load_delta_schema_version = LOAD_DELTA_SCHEMA_VERSION

        return cls(
            intervention_id=str(d.get("intervention_id") or ""),
            operator_id=str(d.get("operator_id") or ""),
            outcome_kind=str(d.get("outcome_kind") or ""),
            grounding_kind=str(d.get("grounding_kind") or ""),
            grounding_confidence=_safe_clamped_float(
                d.get("grounding_confidence"), lo=0.0, hi=1.0
            ),
            causal_edge_id=str(d.get("causal_edge_id") or ""),
            backprop_record_id=str(d.get("backprop_record_id") or ""),
            rgm_snapshot_id=str(d.get("rgm_snapshot_id") or ""),
            source_state_signature=str(d.get("source_state_signature") or ""),
            post_state_signature=str(d.get("post_state_signature") or ""),
            s_credit=_safe_finite_float(d.get("s_credit")),
            p_credit=_safe_finite_float(d.get("p_credit")),
            negative_credit=_safe_finite_float(d.get("negative_credit")),
            self_binding_status=str(d.get("self_binding_status") or "unknown"),
            self_entity_id=str(d.get("self_entity_id") or ""),
            required_predicate_ids=_tuple_text(d.get("required_predicate_ids")),
            spatial_relation_ids=_tuple_text(d.get("spatial_relation_ids")),
            entity_delta_refs=_tuple_text(d.get("entity_delta_refs")),
            saturated=bool(d.get("saturated", False)),
            failure_interpretation=str(d.get("failure_interpretation") or ""),
            phase_signature_motif_id=motif_id,
            phase_signature_slot=slot,
            phase_signature_outcome_tendency=tendency,
            phase_signature_catalog_version=catalog_ver,
            grounding_self_bound=_tri_state_bool("grounding_self_bound"),
            grounding_route_bound=_tri_state_bool("grounding_route_bound"),
            grounding_target_state_bound=_tri_state_bool("grounding_target_state_bound"),
            # Phase 3 — conditional-expectation record.
            conditioning_variables_present=_phase3_tuple("conditioning_variables_present"),
            conditioning_variables_missing=_phase3_tuple("conditioning_variables_missing"),
            conditioning_provenance=_phase3_str("conditioning_provenance"),
            predicted_s_credit=_phase3_float("predicted_s_credit"),
            predicted_p_credit=_phase3_float("predicted_p_credit"),
            predicted_t_credit=_phase3_float("predicted_t_credit"),
            prediction_error_s=_phase3_float("prediction_error_s"),
            prediction_error_p=_phase3_float("prediction_error_p"),
            prediction_error_t=_phase3_float("prediction_error_t"),
            t_credit=_safe_finite_float(d.get("t_credit"), default=0.0),
            load_delta_predicted=load_delta_predicted,
            load_delta_observed=load_delta_observed,
            load_prediction_error=load_prediction_error,
            pair_credit_by_channel=pair_credit_by_channel,
            precision_by_channel=precision_by_channel,
            edge_prediction_last_tick=edge_prediction_last_tick,
            load_delta_schema_version=load_delta_schema_version,
        )


@dataclass(frozen=True)
class CausalPathResidue:
    """A causal-path memory cell attached to a branch by load resonance.

    Identity is the (load_signature, sequence) pair — two residues
    with the same deposit-time load shape and the same ordered
    sequence of intervention-outcomes map to the same ``residue_id``.

    The ``deposit_load_vector`` preserves the full 17-channel
    LoadSignature snapshot at deposit time so retrieval (Phase 3) can
    derive any sub-vector (axis projection, driver projection,
    magnitude) without re-tracing the original observation.
    """

    residue_id: str
    load_signature: str
    deposit_load_vector: Tuple[float, ...]
    sequence: Tuple[ResidueEdgeRef, ...]

    # Lifecycle bookkeeping
    realised_relief: float = 0.0
    realised_option_gain: float = 0.0
    confidence: float = 0.0
    grounded: bool = False
    activation_count: int = 0
    relief_count: int = 0
    grounded_no_relief_count: int = 0
    last_outcome_kind: str = ""
    deposit_tick: int = 0
    last_update_tick: int = 0

    # Phase 2C — bridge-grounding motif sequence at deposit time.
    # WRITE-ONLY METADATA. Per spec: not read by any selector.
    phase_signature_sequence: Tuple[str, ...] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "residue_id": self.residue_id,
            "load_signature": self.load_signature,
            "deposit_load_vector": list(self.deposit_load_vector),
            "sequence": [edge.to_dict() for edge in self.sequence],
            "realised_relief": float(self.realised_relief),
            "realised_option_gain": float(self.realised_option_gain),
            "confidence": float(self.confidence),
            "grounded": bool(self.grounded),
            "activation_count": int(self.activation_count),
            "relief_count": int(self.relief_count),
            "grounded_no_relief_count": int(self.grounded_no_relief_count),
            "last_outcome_kind": self.last_outcome_kind,
            "deposit_tick": int(self.deposit_tick),
            "last_update_tick": int(self.last_update_tick),
        }
        if self.phase_signature_sequence is not None:
            d["phase_signature_sequence"] = list(self.phase_signature_sequence)
        return d

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "CausalPathResidue":
        raw_sequence = d.get("sequence") or ()
        sequence = tuple(
            ResidueEdgeRef.from_dict(edge)
            for edge in raw_sequence
            if isinstance(edge, Mapping)
        )
        # deposit_load_vector elements are floats — sanitize each so a
        # NaN / Inf in one position does not poison the whole vector.
        raw_vector = d.get("deposit_load_vector") or ()
        if isinstance(raw_vector, (list, tuple)):
            deposit_load_vector: Tuple[float, ...] = tuple(
                _safe_finite_float(x) for x in raw_vector
            )
        else:
            deposit_load_vector = ()
        # Float lifecycle fields use ``_safe_finite_float`` so a
        # malformed snapshot cannot land NaN / Inf in confidence or
        # the relief / option-gain accumulators. ``confidence`` is
        # clamped to [0, 1]; option-gain and realised-relief are
        # clamped at zero from below (they are non-negative by
        # construction).
        # Phase 2C — phase_signature_sequence is None on legacy
        # snapshots and a tuple of motif IDs on Phase-2 snapshots.
        raw_seq = d.get("phase_signature_sequence")
        if isinstance(raw_seq, (list, tuple)) and raw_seq:
            phase_signature_sequence: Tuple[str, ...] | None = tuple(
                str(item) for item in raw_seq if item is not None
            )
        else:
            phase_signature_sequence = None

        return cls(
            residue_id=str(d.get("residue_id") or ""),
            load_signature=str(d.get("load_signature") or ""),
            deposit_load_vector=deposit_load_vector,
            sequence=sequence,
            realised_relief=max(0.0, _safe_finite_float(d.get("realised_relief"))),
            realised_option_gain=max(0.0, _safe_finite_float(d.get("realised_option_gain"))),
            confidence=_safe_clamped_float(d.get("confidence"), lo=0.0, hi=1.0),
            grounded=bool(d.get("grounded", False)),
            activation_count=int(_safe_finite_float(d.get("activation_count"))),
            relief_count=int(_safe_finite_float(d.get("relief_count"))),
            grounded_no_relief_count=int(_safe_finite_float(d.get("grounded_no_relief_count"))),
            last_outcome_kind=str(d.get("last_outcome_kind") or ""),
            deposit_tick=int(_safe_finite_float(d.get("deposit_tick"))),
            last_update_tick=int(_safe_finite_float(d.get("last_update_tick"))),
            phase_signature_sequence=phase_signature_sequence,
        )


def _tuple_text(value: Any) -> Tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        items = value.split("|") if "|" in value else value.split(",")
    elif isinstance(value, (list, tuple)):
        items = value
    else:
        items = (value,)
    result: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return tuple(result)


__all__ = [
    "AUTHORITY_GROUNDING_KINDS",
    "CausalPathResidue",
    "ResidueEdgeRef",
]
