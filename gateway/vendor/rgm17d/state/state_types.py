# Module Overview [state/state_types.py]
# Purpose: Documents the module's role in the Phase 8–18 pipeline and what remains delegated to other subsystems.
# Exclusions: Avoids starting services, bypassing policy checks, or redefining shared contracts beyond the helpers defined here.
# Phase dependency: Imported by orchestrators, guards, or tests that compose the multi-phase loop; later phases rely on these bindings staying stable.
# Inputs/Outputs: Accepts typed arguments shown in signatures and returns structured values; any shared state mutations are annotated inline near the calls.
# Invariants: Preserve determinism, respect configured bounds, and avoid unsignaled ToMStateV4P2 mutations or external side effects.

"""
State dataclass definitions for Tree of Mind.

Subsystem: state
Owns: define canonical state structures
Must Not: implement controller/mechanics logic or LLM orchestration

FUTURE PHASE NOTICE:
This module defines record structures only. It does not enforce behavior,
select actions, or bind identity. Any use of memory data for decision
authority is explicitly deferred to Phase 19+ after value grounding and
binding semantics are introduced.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import enum
import math

from gateway.vendor.rgm17d.state.branch_residue_types import CausalPathResidue


BRANCH_LOAD_DIRECTIONS_DEGREES: Tuple[int, int, int] = (0, 120, 240)


def default_branch_load_vector() -> Dict[str, Any]:
    """Default branch-carried 8D/17D angular load metadata.

    This is structural state carried by the branch. Mechanics may read it in a
    later reviewed slice, but this field addition does not alter stress,
    kappa/sigma, routing, or public-answer behavior.
    """

    return {
        "angular_components": [
            {
                "direction_degrees": direction,
                "load_basis": f"native_load_vocabulary_axis_{direction}",
                "carried_by": "branch",
            }
            for direction in BRANCH_LOAD_DIRECTIONS_DEGREES
        ],
        "association": "branch_level_load_vector_evidence",
        "carriage": "runtime_branch_state",
        "mechanics_authority": "metadata_only_not_consumed_by_mechanics",
    }


# ---------------------------------------------------------------------------
# Global Mode
# ---------------------------------------------------------------------------

class Mode(enum.Enum):
    NORMAL = "normal"
    STILLNESS = "stillness"
    SANDBOX = "sandbox"
    REFLECTION = "reflection"
    EMERGENCY = "EMERGENCY"


class PolicyOutcome(enum.Enum):
    PERMIT = "permit"
    DEFER = "defer"
    BLOCK = "block"


@dataclass(frozen=True)
class CapabilityContract:
    """Controller-emitted contract: what this turn is allowed to do.

    Like a structural load permit — the tree says what the structure
    can bear this tick. Frozen to prevent presentation-layer mutation.
    chat_adapter reads this, never computes it.

    Computed by controller.step() from pre-step state snapshot (G3).
    """
    register: str = "REG_MEASURED"
    temperature: float = 0.6
    soft_max_chars: int = 500
    mechanics_visible: bool = False
    dominant_axis: str = "B"
    vitality: int = 1
    caution: int = 0
    route_mode: str = "normal"
    allow_tools: bool = False
    allow_external_actions: bool = False
    effective_phi: float = 0.05
    phi_floor_applied: bool = False
    vision_available: bool = False
    prior_coupling_ok: bool = True
    prior_semantic_ok: bool = True
    policy_basis: str = "pre_step"

    # Capability permits — mechanical booleans, not prose.
    # ALWAYS False: no code path exists for these capabilities.
    can_adjust_parameters: bool = False
    can_adjust_tone: bool = False
    can_adjust_verbosity: bool = False
    can_modify_config: bool = False
    can_simulate: bool = False
    can_execute_code: bool = False


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@dataclass
class MetricsSnapshot:
    S: float = 0.5
    C: float = 0.5
    H: float = 0.5
    C_phi: float = 0.5
    R: float = 0.5

    E_p: float = 0.0
    E_k: float = 0.0
    E_ratio: float = 0.0

    K_s: float = 0.0
    avg_k_raw: float = 0.0  # unclamped avg branch kappa; feeds oscillation detection
    I_eff: float = 0.0

    resource_entropy: float = 0.0
    kappa_var_window: float = 0.0
    axis_S_x: float = 0.0
    axis_S_y: float = 0.0
    axis_C_x: float = 0.5
    axis_C_y: float = 0.5
    stiffness_coupling: float = 0.5
    thematic_coupling: float = 0.0
    predictive_coupling: float = 0.5
    H_forecast: float = 0.5

    memory_pressure: float = 0.0
    memory_entropy: float = 0.0

    # --- r005 predictive fields ---
    delta_kappa_pred: float = 0.0
    health_pred: float = 0.5
    oscillation_index: float = 0.0
    stability_gate: float = 1.0
    instability_flag: bool = False
    health_valid: bool = True
    health_mode: str = "normal"
    health_bootstrap_H: float = 0.25
    runtime_health_H: float = 0.0
    danger_evidence: bool = False
    danger_reasons: List[str] = field(default_factory=list)

    # --- V6 cross-domain scalar (mechanics + ethos; computed later) ---
    S_equilibrium: float = 0.0

    # --- V6 supervisory metrics (computed in controller layer) ---
    kappa_s_raw: float = 0.0
    kappa_s_norm: float = 0.0
    kappa_s_median: float = 0.0
    kappa_s_iqr: float = 0.0

    # --- V6B arbitration telemetry ---
    coherence_signal: "CoherenceSignal" | None = None
    belief_memory_view: "BeliefMemoryView | None" = None

    # --- State mode classification ---
    tom_state_mode: str = "NORMAL"
    tom_state_reasons: List[str] = field(default_factory=list)
    mode_action: str | None = None
    mode_action_detail: str | None = None
    mode_scale: float = 1.0

    # --- Guard reconciliation telemetry ---
    guard_stillness_gated_by: str = "danger_evidence"
    guard_reconciliation_active: bool = True


# ---------------------------------------------------------------------------
# Interoception: Feeling Vector + Memory (Phase 1 shadow)
# ---------------------------------------------------------------------------

FEELING_NAMES = ('tension', 'clarity', 'fatigue', 'urgency', 'vitality_sense', 'sustainability', 'groundedness')


@dataclass
class FeelingVector:
    """ToM's interoceptive state. All [0, 1]. No text, no regex, pure mechanics."""
    tension: float = 0.0        # 0 = relaxed, 1 = maximal stress
    clarity: float = 1.0        # 1 = clear, 0 = foggy
    fatigue: float = 0.0        # 0 = fresh, 1 = exhausted
    urgency: float = 0.0        # 0 = calm, 1 = critical
    vitality_sense: float = 0.5 # 0 = depleted, 1 = thriving
    sustainability: float = 0.5 # 0 = energy deficit, 1 = sustainable
    groundedness: float = 0.5   # 0 = unbalanced, 1 = rooted


@dataclass
class FeelingMemory:
    """Tracks per-feeling persistence & recovery across ticks.

    Typed field on ToMStateV4P2. Migrated for old pickles.
    """
    persistence: Dict[str, int] = field(default_factory=dict)
    recovery: Dict[str, int] = field(default_factory=dict)
    metric_history: Dict[str, List[float]] = field(default_factory=dict)
    last_updated_tick: int = -1
    last_feelings: Optional[FeelingVector] = None  # cached for idempotence
    last_fingerprint: Optional[Tuple[Any, ...]] = None  # sensor fingerprint for idempotence

    @classmethod
    def default(cls) -> "FeelingMemory":
        return cls(
            persistence={f: 0 for f in FEELING_NAMES},
            recovery={f: 0 for f in FEELING_NAMES},
            metric_history={},
            last_updated_tick=-1,
            last_feelings=None,
            last_fingerprint=None,
        )


# ---------------------------------------------------------------------------
# Regime commitment advisory (Phase 7B)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegimeCommitmentAdvisory:
    schema_version: str = "v1"
    is_candidate: bool = False
    candidate_regime_id: Optional[str] = None
    commitment_confidence: float = 0.0
    ticks_meeting_enter_conditions: int = 0
    ticks_as_candidate: int = 0
    cooldown_remaining: int = 0
    entropy_norm: float = 0.0
    diagnostic_reason: str = ""

    @staticmethod
    def neutral(reason: str = "") -> "RegimeCommitmentAdvisory":
        return RegimeCommitmentAdvisory(
            schema_version="v1",
            is_candidate=False,
            candidate_regime_id=None,
            commitment_confidence=0.0,
            ticks_meeting_enter_conditions=0,
            ticks_as_candidate=0,
            cooldown_remaining=0,
            entropy_norm=0.0,
            diagnostic_reason=reason or "neutral",
        )


# ---------------------------------------------------------------------------
# Ethos & Agency
# ---------------------------------------------------------------------------

@dataclass
class EthosState:
    E1: float = 0.5
    E2: float = 0.5
    E3: float = 0.5
    S_ethos: float = 0.5
    S_weighted: float = 0.5
    S_prime: float = 0.5
    verdict: str = "ALLOW"


@dataclass
class AgencyState:
    phi_t: float = 0.2
    phi_a: float = 0.05
    phi_next: float = 0.2
    phi_prev: float = 0.05  # [r006-fix] Track previous activation for φ̇

    phi_min: float = 0.0
    phi_max: float = 0.4

    error: float = 0.0
    integrator: float = 0.0
    v: float = 0.0
    zeta: float = 0.7
    gamma_inh: float = 0.0
    uncertainty: float = 0.0  # [r006-fix] Canonical uncertainty penalty term

    last_error: float = 0.0
    last_control: float = 0.0

    # Behavioural displacement tracking (controller-owned)
    delta_phi: float = 0.0
    delta_mode: float = 0.0
    delta_action_class: float = 0.0


# ---------------------------------------------------------------------------
# Arbitration scaffolding
# ---------------------------------------------------------------------------


@dataclass
class CoherenceSignal:
    """Bounded arbitration signal shared across regulators."""

    agreement_score: float = 0.0  # [-1, 1]
    confidence: float = 0.0  # [0, 1]
    notes: str = "coherence-neutral"

    @staticmethod
    def neutral(notes: str = "coherence-neutral") -> "CoherenceSignal":
        return CoherenceSignal(0.0, 0.0, notes)

    def bounded(self) -> "CoherenceSignal":
        return CoherenceSignal(
            agreement_score=_clamp(self.agreement_score, -1.0, 1.0),
            confidence=_clamp(self.confidence, 0.0, 1.0),
            notes=self.notes,
        )


# ---------------------------------------------------------------------------
# Coherence computation (canonical primitive)
# ---------------------------------------------------------------------------


def compute_coherence_signal_from_belief(
    belief_view: "BeliefMemoryView", notes: Optional[str] = None
) -> CoherenceSignal:
    """Compute bounded coherence from belief-derived regulator directions.

    This is the single canonical coherence computation primitive; all
    arbitration resolution must call this function instead of duplicating
    the projection logic elsewhere.
    """

    progression_signal = max(belief_view.rolling_attribution_mean, 0.0)
    setback_signal = max(-belief_view.rolling_attribution_mean, 0.0)
    stability_bonus = max(belief_view.stability_trend, 0.0)
    curriculum_direction = progression_signal + 0.5 * stability_bonus - 0.75 * setback_signal

    hypothesis_direction = belief_view.rolling_attribution_mean

    prompt_direction = belief_view.recent_outcome_polarity
    prompt_direction += 0.5 * belief_view.stability_trend
    prompt_direction += belief_view.rolling_attribution_mean

    bounded_curriculum = _clamp(curriculum_direction, -1.0, 1.0)
    bounded_hypothesis = _clamp(hypothesis_direction, -1.0, 1.0)
    bounded_prompt = _clamp(prompt_direction, -1.0, 1.0)

    active = [
        d
        for d in (bounded_curriculum, bounded_hypothesis, bounded_prompt)
        if abs(d) > 1e-6
    ]
    if not active:
        return CoherenceSignal.neutral(notes or "coherence-neutral: no active regulators")

    pairwise = []
    directions = [bounded_curriculum, bounded_hypothesis, bounded_prompt]
    for i in range(len(directions)):
        for j in range(i + 1, len(directions)):
            if directions[i] == 0.0 or directions[j] == 0.0:
                continue
            pairwise.append(_clamp(directions[i] * directions[j], -1.0, 1.0))

    agreement_score = sum(pairwise) / len(pairwise) if pairwise else 0.0
    confidence = _clamp(sum(abs(v) for v in active) / 3.0, 0.0, 1.0)
    note_text = notes or (
        f"curr={bounded_curriculum:+.2f}, hyp={bounded_hypothesis:+.2f}, prompt={bounded_prompt:+.2f}"
    )

    return CoherenceSignal(
        agreement_score=_clamp(agreement_score, -1.0, 1.0),
        confidence=confidence,
        notes=note_text,
    )


# ---------------------------------------------------------------------------
# Supervisory state (controller-owned)
# ---------------------------------------------------------------------------


class SupervisorMode(enum.Enum):
    STILLNESS = "STILLNESS"
    REFLECT = "REFLECT"
    ACT = "ACT"


@dataclass
class KappaSStats:
    history: List[float] = field(default_factory=list)
    median: float = 0.0
    iqr: float = 0.0


@dataclass
class SupervisorBelief:
    regime_posterior: Dict[str, float] = field(default_factory=dict)
    energy_posterior: Dict[str, float] = field(default_factory=dict)
    stability_posterior: Dict[str, float] = field(default_factory=dict)
    stable_ticks: int = 0
    last_mode: SupervisorMode = SupervisorMode.REFLECT
    stability_belief: float = 0.5
    risk_belief: float = 0.5
    readiness_belief: float = 0.5


@dataclass
class BeliefMemoryRecord:
    """Immutable belief snapshot; only outcome/attribution may change after write."""

    tick_index: int
    mode: SupervisorMode
    stability_belief: float
    risk_belief: float
    readiness_belief: float
    kappa_s_norm: float
    s_equilibrium: float
    override_active: bool
    adapted_thresholds: Dict[str, float]
    outcome: Optional[float] = None
    attribution: float = 0.0


@dataclass
class BeliefMemoryView:
    """Read-only summary of belief memory used by regulators."""

    rolling_attribution_mean: float = 0.0
    recent_outcome_polarity: float = 0.0
    stability_trend: float = 0.0
    override_frequency: float = 0.0
    window: int = 0
    samples: int = 0

    @staticmethod
    def neutral(window: int = 0) -> "BeliefMemoryView":
        return BeliefMemoryView(window=window)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def compute_belief_memory_view(
    records: Optional[List[BeliefMemoryRecord]],
    window: int = 10,
) -> BeliefMemoryView:
    """Compute a bounded summary from belief memory without mutation."""

    if not records:
        return BeliefMemoryView.neutral(window=window)

    subset = list(records[-max(1, window) :])
    sample_count = len(subset)

    attribution_vals = [float(getattr(r, "attribution", 0.0) or 0.0) for r in subset]
    rolling_attribution_mean = _clamp(sum(attribution_vals) / sample_count, -1.0, 1.0)

    outcomes = [float(o) for o in [getattr(r, "outcome", None) for r in subset] if o is not None]
    if outcomes:
        recent_outcome_polarity = _clamp(sum(outcomes) / len(outcomes), -1.0, 1.0)
    else:
        recent_outcome_polarity = 0.0

    stability_start = float(getattr(subset[0], "stability_belief", 0.0) or 0.0)
    stability_end = float(getattr(subset[-1], "stability_belief", 0.0) or 0.0)
    stability_trend = _clamp(stability_end - stability_start, -1.0, 1.0)

    override_hits = sum(1 for r in subset if bool(getattr(r, "override_active", False)))
    override_frequency = _clamp(override_hits / sample_count, 0.0, 1.0)

    return BeliefMemoryView(
        rolling_attribution_mean=rolling_attribution_mean,
        recent_outcome_polarity=recent_outcome_polarity,
        stability_trend=stability_trend,
        override_frequency=override_frequency,
        window=window,
        samples=sample_count,
    )


@dataclass
class SupervisorState:
    mode: SupervisorMode = SupervisorMode.REFLECT
    kappa_s: float = 0.0
    kappa_s_normalized: float = 0.0
    kappa_s_raw: float = 0.0
    kappa_s_norm: float = 0.0
    kappa_s_stats: KappaSStats = field(default_factory=KappaSStats)
    stability_horizon: int = 0
    override_active: bool = False
    override_ticks_remaining: int = 0
    tier_e_enabled: bool = False
    belief: SupervisorBelief = field(default_factory=SupervisorBelief)
    s_equilibrium: float = 0.0
    last_delta_x_norm: float = 0.0
    last_delta_f: float = 0.0
    last_delta_action_class: float = 0.0
    stillness_ticks: int = 0
    ticks_since_adaptation: int = 0
    adapted_thresholds: Dict[str, float] = field(default_factory=dict)
    belief_memory: List[BeliefMemoryRecord] = field(default_factory=list)
    danger_evidence: bool = False
    kappa_s_frozen_ticks: int = 0  # consecutive ticks kappa_s_norm unchanged (within epsilon)


# ---------------------------------------------------------------------------
# Tree structure (branches)
# ---------------------------------------------------------------------------

@dataclass
class BranchCreditAccumulator:
    s_credit_accum: float = 0.0
    p_credit_accum: float = 0.0
    t_credit_accum: float = 0.0
    evidence_credit_accum: float = 0.0
    structural_support_credit_accum: float = 0.0
    negative_credit_accum: float = 0.0
    prediction_error_credit_accum: float = 0.0
    prediction_error_debit_accum: float = 0.0
    prediction_error_improved_count: int = 0
    prediction_error_worsened_count: int = 0
    prediction_error_stable_count: int = 0
    prior_prediction_error_l1: float = 0.0
    last_prediction_error_l1: float = 0.0
    last_prediction_error_delta: float = 0.0
    prediction_error_credibility_weight: float = 0.0
    attempt_count: int = 0
    no_effect_count: int = 0
    no_meaningful_change_count: int = 0
    unresolved_change_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    entity_delta_backed_count: int = 0
    last_outcome_kind: str = ""
    last_update_tick: int = 0
    entity_delta_signature_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["entity_delta_signature_counts"] = dict(self.entity_delta_signature_counts)
        return data

    @classmethod
    def from_mapping(cls, value: Any) -> "BranchCreditAccumulator":
        if not isinstance(value, dict):
            return cls()

        def _float_field(name: str) -> float:
            try:
                raw = float(value.get(name, 0.0))
            except (TypeError, ValueError):
                return 0.0
            return raw if math.isfinite(raw) else 0.0

        def _int_field(name: str) -> int:
            try:
                raw = int(value.get(name, 0))
            except (TypeError, ValueError):
                return 0
            return max(0, raw)

        raw_signatures = value.get("entity_delta_signature_counts")
        signatures: Dict[str, int] = {}
        if isinstance(raw_signatures, dict):
            for key, raw_count in raw_signatures.items():
                text = str(key or "").strip()
                if not text:
                    continue
                try:
                    count = int(raw_count)
                except (TypeError, ValueError):
                    continue
                if count > 0:
                    signatures[text] = count

        return cls(
            s_credit_accum=_float_field("s_credit_accum"),
            p_credit_accum=_float_field("p_credit_accum"),
            t_credit_accum=_float_field("t_credit_accum"),
            evidence_credit_accum=_float_field("evidence_credit_accum"),
            structural_support_credit_accum=_float_field(
                "structural_support_credit_accum"
            ),
            negative_credit_accum=_float_field("negative_credit_accum"),
            prediction_error_credit_accum=_float_field(
                "prediction_error_credit_accum"
            ),
            prediction_error_debit_accum=_float_field(
                "prediction_error_debit_accum"
            ),
            prediction_error_improved_count=_int_field(
                "prediction_error_improved_count"
            ),
            prediction_error_worsened_count=_int_field(
                "prediction_error_worsened_count"
            ),
            prediction_error_stable_count=_int_field(
                "prediction_error_stable_count"
            ),
            prior_prediction_error_l1=_float_field("prior_prediction_error_l1"),
            last_prediction_error_l1=_float_field("last_prediction_error_l1"),
            last_prediction_error_delta=_float_field(
                "last_prediction_error_delta"
            ),
            prediction_error_credibility_weight=_float_field(
                "prediction_error_credibility_weight"
            ),
            attempt_count=_int_field("attempt_count"),
            no_effect_count=_int_field("no_effect_count"),
            no_meaningful_change_count=_int_field("no_meaningful_change_count"),
            unresolved_change_count=_int_field("unresolved_change_count"),
            positive_count=_int_field("positive_count"),
            negative_count=_int_field("negative_count"),
            neutral_count=_int_field("neutral_count"),
            entity_delta_backed_count=_int_field("entity_delta_backed_count"),
            last_outcome_kind=str(value.get("last_outcome_kind") or ""),
            last_update_tick=_int_field("last_update_tick"),
            entity_delta_signature_counts=signatures,
        )


@dataclass
class BranchState:
    id: str
    parent_id: Optional[str]
    depth: int

    ell: float
    r: float
    s: float
    kappa: float
    theta: float

    leaves: List[float] = field(default_factory=list)
    # Semantic axis weights (L/S/T). Must sum to 1.0; controller may renormalise.
    axis_w: List[float] = field(default_factory=lambda: [1 / 3, 1 / 3, 1 / 3])
    sweet_counter: int = 0
    sigma_ema: float = 0.0
    overload_ema: float = 0.0
    theta_hist: List[float] = field(default_factory=list)

    micro_stiffness: float = 0.0

    vitality: float = 0.3
    usage_count: int = 0

    resource_bias: float = 0.0
    # NOTE: axis_w already defined above. Do not redefine; duplicate fields can silently
    # override dataclass defaults and break downstream assumptions.

    # Per-leaf semantic vector: 8-dim [L,S,T,dx,dF,phi,I,conf] (L2-normalized)
    sem_vec: Optional[List[float]] = None
    sem_vec_age: int = 0  # Ticks since last confidence-gated refresh
    # E5/M1 competitive district recruitment: mechanical ownership state.
    # Derived from imprint history only; no family labels enter mechanics.
    owner_sig_8d: Optional[List[float]] = None
    owner_sig_17d: Optional[List[float]] = None
    owner_strength: float = 0.0
    owner_last_tick: int = -1
    owner_update_count: int = 0

    # E15 frozen path-consolidation member discovery schema.
    # Sparse, inert branch-resident state: mechanics do not consume this field.
    # The sandbox E15 harness uses it only to rediscover ordinary consolidated
    # member groupings after engine save/load while address/content authority
    # remains in the canonical owner_sig_17d + owner_strength fields above.
    e15_member_schema: Optional[Dict[str, Any]] = None

    # Carillon structural-modal resonance.  A channel lives on one ordinary
    # anchor branch; participating branches keep at most a parent and a child
    # structural reference.  Both fields are sparse and default-on-absence so
    # legacy snapshots remain loadable.  Routing validates the schema before
    # it can have any authority; audit labels are intentionally not represented.
    carillon_channel_schema: Optional[Dict[str, Any]] = None
    carillon_channel_refs: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)
    # Independently earned topology membership is deliberately separate from
    # legacy E15 channel refs.  Only carillon_topology_membership.v1 records
    # formed from ordinary dominant-deformation corridor episodes may carry
    # topology authority; absent state remains compatible with older trees.
    carillon_topology_memberships: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)

    # Phase 3 Stage 3: Nourishment-competitive kappa maintenance
    nourish_ema: float = 1.0       # Smoothed nourishment ratio (1.0 = average)
    starvation_ticks: int = 0      # Consecutive ticks with s < 0

    # Gate 1: Retrieval resonance observation (NO control authority).
    # Accumulated by accumulate_resonance() in agency/mechanics/leaf_vectors.py.
    # Promotion to spawn/routing requires ablation proof of decision-point gain.
    resonance_ema: float = 0.0     # EMA of max cosine similarity when activated
    resonance_count: int = 0       # Total turns this branch matched a retrieved memory
    last_match_tick: int = 0       # Tick of most recent resonance match

    # Organism layer: plastic-strain ratchet. Tracks the lowest kappa
    # ever reached for this branch; monotone non-increasing.
    # Initialized to 1.0 (the engine's typical kappa ceiling) and
    # updated in sicd_kappa_update.py after each per-tick kappa write.
    # The organism extractor's D uses this to compute accumulated
    # damage: D_i = max(0, kappa_health_floor − kappa_min_ever_i),
    # normalised to [0, 1]. Engine-lifetime persistent: survives
    # pickle/unpickle via default-on-absence.
    kappa_min_ever: float = 1.0

    # Phase B niche persistence (additive shadow telemetry; no
    # mechanics consume these fields under default flags).
    # Per docs/contracts/organism_specialist_energy_lifecycle_spec.md §3.
    #
    # locked_niche: 9-channel niche label (L/S/T axis × Th/Su/Pr driver),
    #   e.g. "L_Th", "S_Su", "T_Pr". None = unlocked. Set when
    #   max(driver_exposure_ema) crosses niche_lock_threshold.
    # driver_exposure_ema: per-tick exposure EMA over (T, S, P) drivers.
    #   Updated by agency.organism.niche_persistence helpers when the
    #   enable_niche_state_observation flag is ON.
    # niche_lock_tick: tick at which niche was first locked (0 = unlocked).
    # niche_lock_confidence: max(driver_exposure_ema) at lock time.
    #
    # All four default to "unlocked / zero" so old pre-Phase-B pickles
    # remain default-compatible: the new fields deserialise to their
    # declared defaults via dataclass default-on-absence. (The pickle
    # byte stream is NOT claimed byte-identical to the pre-Phase-B
    # schema — the schema has changed by addition.) No mechanics path
    # reads these fields under enable_niche_hysteresis=False.
    locked_niche: Optional[str] = None
    driver_exposure_ema: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    niche_lock_tick: int = 0
    niche_lock_confidence: float = 0.0

    # ------------------------------------------------------------------
    # Decomposed prune-pressure channels (Level 0 telemetry, additive).
    # Per docs/contracts/tree_thermodynamics_prune_pressure_decomposition_plan.md §2.
    # See also docs/contracts/tree_thermodynamics_metric_closure_spec.md §1.A.
    #
    # Five per-branch float fields in [0, 1] expose the engine's existing
    # prune-trigger inputs as continuous Level-0 channels, BEFORE the
    # boolean reduction that produces prune_flag. No mechanics path
    # consumes these fields — they are pure read-only telemetry that V's
    # ridge regression in S1V0 / S1V-full will calibrate against §21
    # scenarios.
    #
    # Seven per-branch bool flags expose which trigger condition(s) fired
    # this tick, with the age trigger split into its 4-stage pipeline
    # (eligibility gate → rng boost → per-step cap → final removal).
    #
    # All fields are per-tick state: reset/overwritten on each engine
    # step. The flags are instantaneous — for branches that are removed
    # this tick, the audit value is captured pre-removal in the engine's
    # tick-level prune counters (prune_overload_count, etc.).
    #
    # Empirical zero-fit prior (S1P-ter, 2026-05-03): production
    # checkpoints fire only age + overload naturally. starvation /
    # length_resource / weakness are homeostasis-suppressed; their
    # fields stay at 0.0 in real engine state. See decomposition
    # plan §0.4 for the empirical record.
    #
    # Default-on-absence in engine.save / engine.load: legacy snapshots
    # without these fields load cleanly with all values at their
    # declared defaults below.
    # ------------------------------------------------------------------
    overload_prune_pressure: float = 0.0
    starvation_prune_pressure: float = 0.0
    length_resource_pressure: float = 0.0
    age_prune_pressure: float = 0.0
    weakness_pressure: float = 0.0
    # Per-trigger boolean flags (per-tick audit). All False by default;
    # set during engine.step in the per-branch trigger evaluation
    # (sicd_kappa_update.update_branch_physics) and the age multi-stage
    # pipeline (branch_physics_loop.process_branch_tick + engine.step
    # prune-budget loop).
    overload_trigger_flag: bool = False
    length_resource_trigger_flag: bool = False
    starvation_trigger_flag: bool = False
    age_candidate_flag: bool = False
    age_selected_flag: bool = False
    age_capped_flag: bool = False
    age_removed_flag: bool = False

    # TOM-TREE-OWNED-CAUSAL-RECALL Phase 1: typed sequence memory
    # attached to this branch by load resonance. Each residue is a
    # frozen `CausalPathResidue` carrying ordered grounded edges (via
    # ResidueEdgeRef) and lifecycle bookkeeping. The field is a tuple
    # so the BranchState dataclass stays trivially copyable.
    #
    # Bounded by confidence-priority eviction (NOT LRU) — see
    # `memory/branch_residues.add_residue_to_branch`. A high-confidence
    # relief-bearing residue stays even if it hasn't been retrieved
    # recently; freshness alone does not protect a low-confidence one.
    #
    # Population is performed by `memory/branch_residue_population.py`
    # (Phase 2). Retrieval against current load is performed by
    # `memory/branch_path_recall.py` (Phase 3). Lifecycle helpers
    # (add / update / prune) live in `memory/branch_residues.py`.
    # SICD mechanics modules do NOT touch this field.
    #
    # Default-on-absence: legacy pickles / snapshots without this
    # field deserialise to the empty tuple via dataclass default.
    causal_path_residues: Tuple[CausalPathResidue, ...] = field(default_factory=tuple)

    # P7 compact trace-window fallback. Stores recent canonical 17D
    # load signatures as tuples so cold-branch motif binding can resume
    # after a backend restart without relying on process-local buffers.
    # Default-on-absence: legacy snapshots load with no branch fallback.
    recent_trace_window_17d: Tuple[Tuple[float, ...], ...] = field(default_factory=tuple)
    recent_trace_window_last_tick: int = 0

    # Native 8D/17D branch-load carriage. The branch carries the load-vector
    # directions required by the release POP as structured runtime state:
    # 0, 120, and 240 degrees. This is metadata-only in this slice; no SICD
    # stress, kappa/sigma, spawn, routing, authority, residue, or learning
    # mechanics consume it yet. Default-on-absence keeps old snapshots loadable
    # through dataclass reconstruction.
    load_vector: Dict[str, Any] = field(default_factory=default_branch_load_vector)

    def __setstate__(self, state: Dict[str, Any]) -> None:
        self.__dict__.update(state)
        if not hasattr(self, "load_vector") or self.load_vector is None:
            self.load_vector = default_branch_load_vector()
        if not hasattr(self, "e15_member_schema"):
            self.e15_member_schema = None
        if not hasattr(self, "carillon_channel_schema"):
            self.carillon_channel_schema = None
        if not hasattr(self, "carillon_channel_refs") or self.carillon_channel_refs is None:
            self.carillon_channel_refs = ()
        if not hasattr(self, "carillon_topology_memberships") or self.carillon_topology_memberships is None:
            self.carillon_topology_memberships = ()

    # P1 branch-resident credit substrate. Sparse map keyed by deterministic
    # intervention/operator/action-family/predicate-family scope strings.
    credit_accum_by_scope: Dict[str, BranchCreditAccumulator] = field(
        default_factory=dict
    )

    # P8 sparse branch-resident path credit. Branches without saturation
    # evidence must keep these maps as None to avoid dense per-branch storage.
    path_credit_no_relief_count: Optional[Dict[str, int]] = None
    saturation_state_by_scope: Optional[Dict[str, str]] = None
    saturation_last_evidence_tick: Optional[int] = None

    # Step 10 / EITA re-source. Sparse branch-resident transition state
    # replacing the authoritative CTE JSONL reload path. The schema scalar
    # preserves the old version-gated reload semantics: a bumped value causes
    # branch transition state to be re-derived before it is read.
    eita_transition_schema_version: int = 0
    eita_transition_cells: Optional[Tuple[Dict[str, Any], ...]] = None
    eita_transition_memory_by_action: Optional[Dict[str, Dict[str, Any]]] = None


# ---------------------------------------------------------------------------
# Memory / RGM
# ---------------------------------------------------------------------------


@dataclass
class MemoryRecordState:
    # Non-authoritative memory record. Holds bounded metadata only; no semantics are applied here.
    id: str = ""
    content: str = ""
    content_summary: Optional[str] = None
    content_hash: str = ""
    embedding: Optional[List[float]] = None
    raw_content_ref: Optional[str] = None
    source_refs: List[Dict[str, Any]] = field(default_factory=list)
    anchor_type: str = "episodic"
    anchor_strength: float = 0.0
    decay_rate: float = 0.0
    ttl: Optional[int] = None
    S: float = 0.0
    C: float = 0.0
    H: float = 0.0
    C_phi: float = 0.0
    phi: float = 0.0
    resilience: Optional[float] = None
    novelty_score: float = 0.0
    sensitivity: str = "low"
    sensitivity_score: Optional[float] = None
    policy_outcome: PolicyOutcome = PolicyOutcome.BLOCK
    policy_version: str = "unknown"
    model: str = "unknown"
    critical: bool = False
    criticality: float = 0.0
    reflection_id: Optional[str] = None
    source: str = "system"
    persona_tag: Optional[str] = None
    regime_id: Optional[str] = None
    checksum: str = ""
    created_tick: int = 0
    last_access_tick: int = 0
    access_count: int = 0
    rejection_reason: Optional[str] = None
    quarantine_attempts: int = 0
    revision_history: List[Dict[str, Any]] = field(default_factory=list)
    semantic_tags: List[str] = field(default_factory=list)
    meaning_hashes: List[str] = field(default_factory=list)
    regret_ids: List[str] = field(default_factory=list)
    commitment_ids: List[str] = field(default_factory=list)
    identity_proposal_ids: List[str] = field(default_factory=list)
    causal_record_ids: List[str] = field(default_factory=list)
    leaf_vec: Optional[List[float]] = None  # 8-dim semantic signature at write time


@dataclass
class MemoryState:
    # Structural substrate only. Counters and indices are telemetry; controllers remain read-only.
    schema_version: str = "phase18.1"
    anchors: Dict[str, MemoryRecordState] = field(default_factory=dict)
    quarantine: Dict[str, MemoryRecordState] = field(default_factory=dict)
    telemetry: List[Dict[str, Any]] = field(default_factory=list)
    current_tick: int = 0
    commitment_refs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    regret_index: Dict[str, List[str]] = field(default_factory=dict)
    commitment_index: Dict[str, List[str]] = field(default_factory=dict)
    identity_index: Dict[str, List[str]] = field(default_factory=dict)
    causal_index: Dict[str, List[str]] = field(default_factory=dict)
    long_horizon_counters: Dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Coupling
# ---------------------------------------------------------------------------

@dataclass
class CouplingMatrices:
    stiffness_coupling: Dict[Tuple[str, str], float] = field(default_factory=dict)
    thematic_coupling: Dict[Tuple[str, str], float] = field(default_factory=dict)
    predictive_coupling: Dict[Tuple[str, str], float] = field(default_factory=dict)
    ethos_initiative_gain: float = 0.2
    memory_orientation_gain: float = 0.1
    audio_wind: Optional[Tuple[float, float]] = None


@dataclass
class CouplingSMState:
    last_phase: str = "idle"
    last_reason: str = ""
    last_scale: float = 1.0


# ---------------------------------------------------------------------------
# Actions / tools
# ---------------------------------------------------------------------------

@dataclass
class ActionState:
    last_action: Optional[str] = None
    last_tool: Optional[str] = None
    last_tool_args: Dict[str, Any] = field(default_factory=dict)
    last_tool_result: Optional[str] = None
    tool_registry: Dict[str, Dict[str, Any]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Safety / telemetry
# ---------------------------------------------------------------------------

@dataclass
class SafetyEvent:
    tick: int
    level: str
    code: str
    message: str


@dataclass
class SafetyState:
    last_guard_mode: Optional[Mode] = None
    last_guard_reason: str = ""
    events: List[SafetyEvent] = field(default_factory=list)


@dataclass
class TelemetryState:
    last_tick_duration: float = 0.0
    cpu_load: float = 0.0
    mem_used: float = 0.0
    tick_log: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
# NOTE (Phase 10–12):
# ReflectionSummary is informational, not binding.
#
# TODO (Future Phase):
# Reflection may later be extended with:
# - Value-weighted outcomes
# - Cross-episode reflection memory
# - Regret accumulation beyond simple risk counts
#
# Reflection MUST remain advisory until value grounding exists.
class ReflectionSummary:
    """Canonical reflection status for gating initiative pulses."""

    completed: bool = True
    outcome: float = 0.0
    last_tick: int = 0
    notes: str = "neutral"

    @staticmethod
    def neutral() -> "ReflectionSummary":
        return ReflectionSummary(completed=True, outcome=0.0, last_tick=0, notes="neutral")


# ---------------------------------------------------------------------------
# Pending Interaction State (TIER 1: Deterministic Continuity)
# ---------------------------------------------------------------------------

@dataclass
class PendingInteraction:
    """
    Structured state for pending user responses (CHOICE/CLARIFY/POLICY).
    Used to deterministically resolve user input without relying on LLM memory.

    Example CHOICE:
        choices={"A": "Use steel frame", "B": "Use timber frame"}
        User replies "A" → resolved to "User selected option A: Use steel frame"

    Example CLARIFY:
        clarify_context="What is the span length?"
        User replies "20m" → resolved to "Clarification for 'What is the span length?': 20m"

    Example POLICY:
        policy_id="allow_destructive_action"
        User replies "yes" → resolved to "Policy response for '...': yes"
    """
    id: str  # Unique ID (e.g., "pq_abc123")
    type: str  # "CHOICE" | "CLARIFY" | "POLICY"
    prompt: str  # The question ToM asked
    created_at: float  # Unix timestamp
    expires_at: float  # Auto-expire after N minutes

    # LLM intent at time of creation (for retrieval triggers)
    intent: Optional[str] = None

    # For CHOICE type
    choices: Optional[Dict[str, str]] = None  # {"A": "description", "B": "..."}

    # For CLARIFY type
    clarify_context: Optional[str] = None  # What needs clarification

    # For POLICY type
    policy_id: Optional[str] = None  # Which policy needs approval


# ---------------------------------------------------------------------------
# Top-level ToM state
# ---------------------------------------------------------------------------

@dataclass
class ToMStateV4P2:
    tick: int = 0
    t_sim: float = 0.0
    mode: Mode = Mode.NORMAL

    branches: Dict[str, BranchState] = field(default_factory=dict)
    canopy_density: Dict[str, float] = field(default_factory=dict)
    scars: List[str] = field(default_factory=list)
    next_branch_id: int = 0

    coupling: CouplingMatrices = field(default_factory=CouplingMatrices)
    coupling_sm: CouplingSMState = field(default_factory=CouplingSMState)

    metrics: MetricsSnapshot = field(default_factory=MetricsSnapshot)
    ethos: EthosState = field(default_factory=EthosState)
    agency: AgencyState = field(default_factory=AgencyState)
    memory: MemoryState = field(default_factory=MemoryState)

    # Optional cognitive diagnostics
    world_model_state: Optional[Any] = None
    world_model_errors: List[Any] = field(default_factory=list)
    # CIE Problem Layer state — persists structured problem state (knowns,
    # unknowns, governing relationships, candidate models, entropy trajectory)
    problem_state: Optional[Dict[str, Any]] = None
    counterfactual_comparison: Optional[Any] = None
    regret_records: List[Any] = field(default_factory=list)
    regret_influence: Dict[str, float] = field(default_factory=dict)
    commitment_identity_pressure: Dict[str, float] = field(default_factory=dict)
    commitment_violations: List[Dict[str, Any]] = field(default_factory=list)
    identity_proposals: List[Dict[str, Any]] = field(default_factory=list)

    actions: ActionState = field(default_factory=ActionState)
    safety: SafetyState = field(default_factory=SafetyState)
    telemetry: TelemetryState = field(default_factory=TelemetryState)
    reflection_summary: ReflectionSummary = field(default_factory=ReflectionSummary.neutral)

    # Canonical policy guard output for downstream gating
    guard_decision: Optional[Any] = None
    guard_policy_outcome: PolicyOutcome = PolicyOutcome.PERMIT
    memory_influence_enabled: bool = True
    supervisor: SupervisorState = field(default_factory=SupervisorState)

    history: List[MetricsSnapshot] = field(default_factory=list)

    last_user_input: Optional[str] = None
    last_external_output: Optional[str] = None
    last_llm_json: Optional[dict] = None

    # -----------------------------------------------------------------------
    # TIER 1: Structured Pending Interaction (Deterministic Continuity)
    # -----------------------------------------------------------------------
    pending_interaction: Optional[PendingInteraction] = None

    # -----------------------------------------------------------------------
    # TIER 2: Conversation Context (Response Quality)
    # -----------------------------------------------------------------------
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    conversation_history_max_turns: int = 20  # Keep last N turns

    # -----------------------------------------------------------------------
    # SICD mechanics scratch fields (written by sicd_engine.step)
    # Declared explicitly to avoid relying on runtime monkey-patching.
    # -----------------------------------------------------------------------
    last_axis_load: Optional[Tuple[float, float, float]] = None
    semantic_targets: Optional[Tuple[float, float, float]] = None
    # structural_shares(...) returns a 3-tuple of floats in the SICD engine usage.
    structural_shares: Optional[Tuple[float, float, float]] = None
    # Tick of last confident semantic vector update (for age-prune gating)
    last_leaf_vec_update_tick: Optional[int] = None

    # Arbitration telemetry
    coherence_signal: CoherenceSignal = field(default_factory=CoherenceSignal.neutral)

    # Spawn credit accumulator (synced from sicd._spawn_credit for persistence)
    spawn_credit: float = 0.0

    # Root reserve accumulator (synced from sicd._root_reserve for persistence)
    root_reserve: float = 0.0

    # Versioned adaptive-engine continuity captured only by the ordinary
    # session-pickle path.  None preserves legacy profile-built defaults.
    sicd_session_continuity: Optional[Dict[str, Any]] = None

    # Hunger drive state (controller-owned, written before agency update)
    hunger_ema: float = 0.0         # EMA-smoothed hunger signal H ∈ [0,1]
    hunger_phi_gain: float = 0.0    # Current phi_t uplift gain (0 when disabled)

    # Controller-owned boot/dev tracking
    boot_active: bool = False  # [r006-fix] Canonical boot flag surfaced to all modules
    boot_phase: float = 0.0  # [r006-fix] Normalised boot progression 0→1
    boot_ticks_remaining: int = 0  # [r006-fix] Deterministic boot countdown
    dev_stage: float = 0.0  # [r006-fix] Canonical development stage signal
    curriculum_phase: str = "REFLECT"
    curriculum_intensity: float = 1.0
    curriculum_task: Optional[str] = None
    curriculum_shaping: Optional[Any] = None

    # Context Pack integration (Advisory only)
    codev_context_pack: Optional[dict] = None  # Read-only Codev context
    codev_context_loaded: bool = False  # Flag: context pack was successfully loaded

    # Background physics / idle-time ageing (Phase BG)
    # Timestamps are Unix epoch floats; None means "never active"
    last_active_ts: Optional[float] = None  # Last user turn timestamp (for idle ageing)
    idle_age_reminder_ts: Optional[float] = None  # Last nag timer timestamp (persisted)

    # Interoception: feeling memory for self-assessment (Phase 1 shadow)
    feeling_memory: "FeelingMemory" = field(default_factory=lambda: FeelingMemory.default())

    # Answer Energy: written by chat_adapter, read by tom_controller
    last_answer_energy_delta: float = 0.0
    last_answer_energy_reasons: List[str] = field(default_factory=list)

    # Nourishment Valuation: written by chat_adapter, read by tom_controller + agency_controller
    last_D_estimate: float = 1.0
    last_Ip_deposit: float = 0.0
    last_q_conversion: float = 1.0
    last_Ie_award: float = 0.0
    last_genuine_attempt: bool = False
    last_valuation_reasons: List[str] = field(default_factory=list)

    # Behavioural continuity snapshots (written before pickle, restored on resume)
    # See state/behavioural_continuity.py for the persist/restore/rebind chain.
    goal_registry_snapshot: Optional[Dict[str, Any]] = None
    last_llm_loads_snapshot: Optional[Dict[str, float]] = None
    last_person_state_estimate: Optional[Dict[str, float]] = None
    last_trajectory_class: Optional[str] = None

    # Production E15 evidence counters before a member reaches k=3, plus a
    # bounded audit trail. Formed members remain discoverable only from their
    # branch-resident e15_member_schema state.
    e15_live_support: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    e15_live_events: List[Dict[str, Any]] = field(default_factory=list)
    # Versioned formation-only cursor linking a persisted G1 readout to the
    # next ordinary G1 address. It stores ids/digests only, never a free vector.
    e15_recursive_continuation_cursor: Optional[Dict[str, Any]] = None

    def ensure_root(self) -> None:
        if self.branches:
            return
        root_id = "root"
        self.branches[root_id] = BranchState(
            id=root_id,
            parent_id=None,
            depth=0,
            ell=0.2,
            r=0.5,
            s=0.2,
            kappa=0.3,
            theta=0.0,
            leaves=[0.0, 0.0, 0.0],
            sweet_counter=0,
            sigma_ema=0.0,
            overload_ema=0.0,
            theta_hist=[0.0],
            micro_stiffness=0.0,
            vitality=0.4,
            usage_count=0,
            resource_bias=0.0,
            axis_w=[1 / 3, 1 / 3, 1 / 3],
        )  # [r006-fix] Deterministic canonical root instantiatio
        self.next_branch_id = max(self.next_branch_id, 1)
        self.canopy_density.setdefault(root_id, 0.0)

    @property
    def total_kappa(self) -> float:
        """Sum of branch kappa values only (no micro_stiffness, no leaves)."""
        return sum(float(getattr(b, "kappa", 0.0) or 0.0) for b in self.branches.values())

    @property
    def total_stiffness(self) -> float:
        total = 0.0
        for b in self.branches.values():
            leaf_sum = sum(getattr(b, "leaves", []) or [])
            total += getattr(b, "kappa", 0.0) + getattr(b, "micro_stiffness", 0.0) + leaf_sum
        return total

    @property
    def total_resource(self) -> float:
        return sum(getattr(b, "r", 0.0) for b in self.branches.values())

# COMMENTARY HOLD: Full per-symbol documentation deferred; existing logic left untouched to avoid accidental authority shifts.
