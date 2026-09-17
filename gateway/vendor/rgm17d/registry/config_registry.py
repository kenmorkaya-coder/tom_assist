# Module Overview [registry/config_registry.py]
# Purpose: Documents the module's role in the Phase 8–18 pipeline and what remains delegated to other subsystems.
# Exclusions: Avoids starting services, bypassing policy checks, or redefining shared contracts beyond the helpers defined here.
# Phase dependency: Imported by orchestrators, guards, or tests that compose the multi-phase loop; later phases rely on these bindings staying stable.
# Inputs/Outputs: Accepts typed arguments shown in signatures and returns structured values; any shared state mutations are annotated inline near the calls.
# Invariants: Preserve determinism, respect configured bounds, and avoid unsignaled ToMStateV4P2 mutations or external side effects.

"""
Configuration registry definitions.

Subsystem: registry
Owns: define configuration dataclasses
Must Not: compute mechanics metrics or alter runtime policy
"""

from __future__ import annotations

"""config_registry.py – ToM V4:P2:r007

Central configuration registry (CPR) for ToM V4.

This rev007 update adds:
- Feature flags for new cognitive subsystems (world model, tasks, ethos v2, rgm v2)
- Tunables for slow cognitive loop frequency
- Parameters for world model and task manager capacity
- Backward-compatible defaults (all new features disabled)
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from gateway.vendor.rgm17d.state.state_types import PolicyOutcome


# ---------------------------------------------------------------------------
# Core ToM configuration groups
# ---------------------------------------------------------------------------

@dataclass
class IdentityConfig:
    name: str = "ToM V4"
    version: str = "4.0-P2-r007"
    instance_id: str = "default-instance"
    description: str = "Tree-of-Mind V4 Phase 2 agent (rev007)"
    enable_identity_bootstrap: bool = True


@dataclass
class TimingConfig:
    dt: float = 0.1
    history_window: int = 200

    # r007: slow cognitive loop period
    cognitive_loop_period: int = 10


@dataclass
class EnvironmentConfig:
    base_wind: float = 0.3
    base_nourishment: float = 0.6


@dataclass
class PersistenceConfig:
    enable_persistence: bool = False
    persistence_path: str = "state/"
    autosave_interval_ticks: int = 50
    persistence_version: str = "v1"
    multi_tenant: bool = False
    tenant_persist_root: str = ".tom_persist"


@dataclass
class DirectContextual17DAuthorityConfig:
    """Activation inputs for the ordinary GPT-5.5 causal route.

    The route is selected by the cutover, but remains fail-closed until the
    operator provides a narrow evidence root and the expected VS Code-managed
    backend revision.  Neither value may default into protected session state.
    """

    enabled: bool = True
    route_root: str = ""
    expected_backend_git_commit: str = ""


@dataclass
class LoggingConfig:
    log_level: str = "INFO"
    log_dir: str = "./logs"
    enable_console: bool = True
    enable_file: bool = False
    file_name: str = "tom_v4_telemetry.jsonl"


@dataclass
class InitiativePulseConfig:
    """Configuration for initiative growth pulses (Phase 10)."""

    phi_baseline: float = 0.1
    pulse_alpha: float = 0.35
    pulse_delta_max: float = 0.05
    pulse_delta_max_stressed: float = 0.03
    stability_min: float = 0.45
    coherence_min: float = 0.45
    phi_coherence_min: float = 0.35
    entropy_max: float = 0.65
    theta_phi_pulse: float = 0.35
    decay_rate: float = 0.02
    decay_stillness_multiplier: float = 2.0
    decay_instability_multiplier: float = 1.5
    damping_failure_step: float = 0.01
    damping_failure_cap: float = 0.1
    reflection_required: bool = True
    policy_required_outcome: PolicyOutcome = PolicyOutcome.PERMIT


# ---------------------------------------------------------------------------
# r007 Cognitive Feature Configuration
# ---------------------------------------------------------------------------

@dataclass
class CognitiveConfig:
    """
    r007 cognitive-layer configuration.
    All features default to OFF to ensure backward compatibility.
    """

    enable_world_model: bool = True
    enable_task_manager: bool = True
    enable_ethos_v2: bool = True
    enable_rgm_v2: bool = True

    enable_initiative_modulation: bool = True

    # *** r010/r011 addition ***
    enable_reflection_loop: bool = True

    # Constructive intelligence Stage 3+4 (candidate generation + scoring).
    # Stages 1+2 (person-state + situation) run unconditionally (no LLM cost).
    # Stage 3+4 are now deterministic (zero LLM calls).
    enable_constructive_scoring: bool = True

    # Constructive intelligence Stage 5 (multi-turn planning).
    # Requires enable_constructive_scoring=True (double-gated).
    # Plans 3-5 turns ahead based on person-state gaps.
    enable_multi_turn_planning: bool = True

    # Stage 6: Learning & reuse — extract and store reusable rhetorical patterns.
    # Triple-gated: requires enable_constructive_scoring + enable_multi_turn_planning.
    enable_pattern_learning: bool = True
    # Stage 0: CIE problem-state tracking — detect and track structured problems
    # during conversation. Computes G/M/C/R/H_p entropy per turn when active.
    enable_problem_solving: bool = True

    world_model_max_beliefs: int = 128
    task_manager_max_tasks: int = 32


# ---------------------------------------------------------------------------
# Phase 8.1 RGM Enhancement Configuration (feature-flagged, defaults OFF)
# ---------------------------------------------------------------------------

@dataclass
class RGMEnhancementConfig:
    """
    Phase 8.1 RGM enhancements configuration.
    All features default to OFF for baseline equivalence.

    FUTURE PHASE NOTICE:
    These enhancements improve RGM maintenance and recall quality but remain
    non-authoritative. No decision authority is introduced.
    """
    # Master enable flag - must be True for any enhancement to apply
    enable_rgm_enhancements: bool = True

    # 1. Anchor reinforcement: resilience-delta-scaled update
    # Whitepaper: α_new = clamp(α_old + η(R - R_avg), 0, 1)
    enable_resilience_reinforcement: bool = True
    reinforcement_eta: float = 0.1  # scaling factor for resilience delta
    reinforcement_r_avg: float = 0.5  # baseline resilience average

    # 2. Decay law: exponential vs linear
    # Whitepaper: α_new = α_old * e^(-λ*Δt)
    enable_exponential_decay: bool = True

    # 3. Pruning triggers: periodic + signal-based
    enable_enhanced_pruning_triggers: bool = True
    prune_period_ticks: int = 50  # periodic pruning interval
    prune_entropy_surge_threshold: float = 0.8  # H > threshold triggers prune
    prune_stability_recovery_threshold: float = 0.7  # S recovery trigger
    prune_saturation_threshold: float = 0.9  # capacity fraction trigger

    # 4. Pruning score: weighted multi-metric
    # Whitepaper: Score_i = w_α*α_i + w_C*C_i + w_S*S_i + w_F*f_i
    enable_weighted_pruning_score: bool = True
    prune_weight_alpha: float = 0.4  # anchor strength weight
    prune_weight_access: float = 0.2  # access count weight (normalized)
    prune_weight_freshness: float = 0.2  # freshness weight
    prune_weight_coherence: float = 0.1  # coherence proxy weight
    prune_weight_stability: float = 0.1  # stability proxy weight

    # 5. Recall ranking: alpha * similarity product
    # Whitepaper: score_i = α_i × similarity_i
    enable_similarity_weighted_recall: bool = True

    # 6. Audit integrity: periodic hash + drift detection
    enable_audit_integrity: bool = True
    audit_period_ticks: int = 100  # periodic integrity check interval


# ---------------------------------------------------------------------------
# Phase 9A/9B Observability Configuration (feature-flagged, defaults OFF)
# ---------------------------------------------------------------------------

@dataclass
class Phase9ObservabilityConfig:
    """
    Phase 9A/9B internal signal observability configuration.
    All features default to OFF for baseline equivalence.

    FUTURE PHASE NOTICE:
    Phase 9 is strictly observational. It exposes internal signals for
    inspection, debugging, and analysis but MUST NOT influence decisions,
    control flow, or action selection. Authority is deferred to Phase 19+.

    Phase 9A: Internal Signal Exposure & Structuring
    Phase 9B: Observability, Inspection & Audit Surface
    """
    # Master enable flag for Phase 9A signal emission
    enable_phase9a_signals: bool = True

    # Master enable flag for Phase 9B observability layer
    enable_phase9b_observability: bool = True

    # Signal history capacity (bounded buffer)
    signal_history_capacity: int = 500

    # Rolling window size for summaries
    rolling_window_size: int = 50

    # Export format options
    enable_json_export: bool = False

    # Signal emission throttle (min ticks between same-type emissions)
    emission_throttle_ticks: int = 0


# ---------------------------------------------------------------------------
# Phase 11 Epistemic Calibration Configuration (feature-flagged, defaults OFF)
# ---------------------------------------------------------------------------

@dataclass
class EpistemicCalibrationConfig:
    """
    Phase 11 epistemic calibration records configuration.
    All features default to OFF for baseline equivalence.

    FUTURE PHASE NOTICE:
    Calibration records are informational only. They do not select actions,
    enforce behavior, or bind identity. Authority is deferred to Phase 19+.
    """
    # Master enable flag
    enable_epistemic_calibration: bool = True

    # Rolling window size for calibration stats
    calibration_window: int = 100

    # Confidence bins for ECE calculation
    num_confidence_bins: int = 10

    # Error threshold for "miscalibrated" warning
    ece_warning_threshold: float = 0.15


# ---------------------------------------------------------------------------
# Phase 13.1 Drift Control Enhancement Configuration (feature-flagged)
# ---------------------------------------------------------------------------

@dataclass
class DriftControlConfig:
    """
    Phase 13.1 drift control enhancement configuration.
    All features default to OFF for baseline equivalence.

    FUTURE PHASE NOTICE:
    Drift control is bounded and non-authoritative. It can only damp initiative
    within hard clamps, not veto/override actions. Authority is deferred to Phase 19+.
    """
    # Master enable flag
    enable_drift_control_enhancements: bool = True

    # 13.1a Document indexing
    enable_document_indexing: bool = True
    default_chunk_size: int = 512  # bytes per chunk
    chunk_overlap: int = 64  # overlap between chunks

    # 13.1b Claim-source verification
    enable_claim_verification: bool = True
    verification_top_k: int = 5  # number of supporting chunks to retrieve
    verification_min_similarity: float = 0.3  # minimum similarity threshold

    # 13.1c Initiative damping tied to verification residual
    enable_residual_damping: bool = True
    damping_residual_gain: float = 0.1  # scaling factor
    damping_residual_clamp: float = 0.2  # hard clamp on damping effect

    # 13.1d Multi-candidate deliberation
    enable_deliberation: bool = True
    deliberation_weight_uncited: float = 0.4
    deliberation_weight_contradiction: float = 0.3
    deliberation_weight_goal_substitution: float = 0.3

    # Unified deliberation-coherence pipeline (Phase 2)
    # When True, coherence filtering (schema/action validation) runs inside
    # the deliberation candidate loop instead of as post-selection repair.
    enable_deliberation_coherence: bool = True


# ---------------------------------------------------------------------------
# Phase 12B Evidence Binding Scaffold Configuration (feature-flagged)
# ---------------------------------------------------------------------------

@dataclass
class EvidenceBindingConfig:
    """
    Phase 12B evidence binding scaffold configuration.
    ALL features default to OFF for baseline equivalence.

    FUTURE PHASE NOTICE - CRITICAL:
    Evidence binding is NON-OPERATIVE until Phase 19 authority interface exists.
    Even with enable_evidence_binding_scaffold=True, no binding occurs because
    authority_interface_exists will always be False until Phase 19.

    This double-gate ensures no accidental authority binding.

    Phase 12B MUST NOT:
    - Bind evidence into adaptation decisions
    - Influence action selection, guard modes, or supervisor outputs
    - Change regime selection or adaptation outcomes
    - Introduce goal semantics or uncontrolled optimization
    """
    # Master scaffold enable flag (default OFF)
    # When OFF: returns no-op proposals with FEATURE_DISABLED
    enable_evidence_binding_scaffold: bool = True

    # Authority interface existence check (ALWAYS False until Phase 19)
    # This is a hard gate that prevents binding even if scaffold is enabled
    # DO NOT set this to True until Phase 19 authority interface is implemented
    authority_interface_exists: bool = False

    # Proposal generation tunables (for future use)
    min_evidence_count: int = 10
    min_calibration_samples: int = 50
    min_proposal_confidence: float = 0.6

    # Delta clamps (bounded, small adjustments only)
    max_dev_stage_delta: float = 0.02
    max_curriculum_delta: float = 0.02
    max_learning_rate_delta: float = 0.01


# ---------------------------------------------------------------------------
# Phase 19 Authority Interface Configuration (feature-flagged)
# ---------------------------------------------------------------------------

@dataclass
class AuthorityInterfaceConfig:
    """
    Phase 19 Authority Interface configuration.
    ALL features default to OFF for baseline equivalence.

    This is the SINGLE authority interface for ToM. When enabled,
    records can bind behaviour through explicit, auditable mechanisms.

    Phase 19 acceptance criteria:
    - Single authority interface: one module owns what may influence decisions
    - Auditability: every decision cites evidence IDs and logs reason codes
    - Hard clamps: influence has strict magnitude caps
    - Global disable: can be disabled with zero behavioural delta
    """
    # Master enable flag (default OFF)
    # When OFF: all proposals are audited but nothing is applied
    enable_authority_interface: bool = True

    # Validation configuration
    max_evidence_staleness_ticks: int = 50
    min_total_evidence_count: int = 5
    min_calibration_records: int = 3
    min_proposal_confidence: float = 0.5
    min_calibration_score: float = 0.4

    # Risk gating thresholds
    high_risk_threshold: float = 0.7
    high_risk_min_confidence: float = 0.7
    high_risk_min_evidence_count: int = 10

    # Consistency requirements
    block_during_override: bool = True
    block_during_recovery: bool = True
    block_during_stillness: bool = True

    # Audit configuration
    enable_audit_logging: bool = True
    audit_buffer_size: int = 1000


# ---------------------------------------------------------------------------
# Phase 20 Authority Governance Configuration (feature-flagged)
# ---------------------------------------------------------------------------

@dataclass
class AuthorityGovernanceConfig:
    """
    Phase 20 Authority Governance configuration.
    ALL features default to OFF for baseline equivalence.

    CRITICAL INVARIANTS:
    - Phase 20 does NOT add new authority
    - Phase 20 constrains, audits, governs, and makes authority externally reviewable
    - All mechanisms are read-only observational or externally-controlled
    - The system MUST NOT autonomously intervene based on Phase 20 outputs
    - Humans pull information; the system never pushes

    Phase 20 closure criteria:
    - A) Authority usage is continuously observable and summarized
    - B) Authority behavior is checked against long-horizon invariants
    - C) Pathological authority patterns are detectable
    - D) Safe degradation mechanisms exist and are externally controlled
    - E) External humans can inspect, replay, and intervene
    - F) No authority exists outside the Phase 19 interface
    - G) All mechanisms are auditable, deterministic, and reversible
    """
    # Master enable flag (default OFF)
    # When OFF: Phase 20 is completely inert, zero behavioral change
    enable_authority_governance: bool = True

    # --- Section A: Authority Telemetry ---
    # When enabled, derives metrics from Phase 19 audit logs
    enable_telemetry: bool = True
    telemetry_history_capacity: int = 1000
    telemetry_window_size: int = 100  # Rolling window for rate calculations

    # --- Section B: Invariant Watchdog ---
    # When enabled, evaluates governance invariants on audit records
    enable_invariant_watchdog: bool = True
    watchdog_evaluation_period: int = 10  # Ticks between evaluations

    # Invariant thresholds (configurable bounds for governance checks)
    max_applications_per_window: int = 50  # Max authority applications per window
    cumulative_delta_cap: float = 0.5  # Max cumulative delta magnitude over horizon
    ratchet_detection_threshold: int = 10  # Consecutive same-direction deltas
    rejection_pattern_threshold: int = 20  # Consecutive rejections = malfunction

    # --- Section C: Safe Degradation ---
    # Degradation modes are EXTERNALLY controlled, never self-triggered
    # These states are read from external config/file, not computed internally
    degradation_mode: str = "normal"  # "normal" | "audit_only" | "clamped" | "suspended"

    # Clamped mode delta multiplier (reduces allowed deltas)
    clamped_delta_multiplier: float = 0.5  # When clamped, deltas are halved

    # --- Section D: Long-Horizon Drift Analysis ---
    # When enabled, computes drift metrics for external analysis
    enable_drift_analysis: bool = True
    drift_analysis_horizon: int = 500  # Ticks to analyze for drift patterns

    # --- Section E: External Review Interface ---
    # When enabled, exposes read-only query interface for external review
    enable_review_interface: bool = True
    review_export_format: str = "json"  # "json" | "jsonl"

    # --- Section F: Phase 20 Audit ---
    # When enabled, records Phase 20 evaluations alongside Phase 19 audits
    enable_phase20_audit: bool = True
    audit_include_telemetry: bool = True
    audit_include_invariants: bool = True
    audit_include_drift: bool = True


# ---------------------------------------------------------------------------
# Phase 21 Goal Formation Configuration (feature-flagged)
# ---------------------------------------------------------------------------

@dataclass
class GoalFormationConfig:
    """
    Phase 21 Goal Formation configuration.
    ALL features default to OFF for baseline equivalence.

    CRITICAL INVARIANTS:
    - Goals are EXPLICIT objects with bounded urgency
    - Goals are DESCRIPTIVE and DIRECTIVE, not reward signals
    - Goals CANNOT self-amplify, self-prioritise, or self-generate
    - Supervisor retains FINAL authority over action selection
    - Goals INFORM deliberation; they do NOT command actions
    - All goal effects are bounded, reversible, and auditable

    Phase 21 acceptance criteria:
    - A) Explicit goal objects exist with defined lifecycle
    - B) Goal prioritisation is bounded and monotonic
    - C) No reward loops or scalar optimisation targets exist
    - D) Supervisor retains final authority over action selection
    - E) Goals cannot generate or escalate themselves
    - F) All effects are auditable and reversible
    - G) Baseline equivalence when Phase 21 is OFF
    """
    # Master enable flag (default OFF)
    # When OFF: no goals exist, behavior is regression-identical to baseline
    enable_goal_formation: bool = True

    # --- Goal Registry Configuration ---
    max_active_goals: int = 16  # Maximum concurrent active goals
    max_total_goals: int = 64  # Maximum goals in registry (including suspended/completed)
    goal_expiry_ticks: int = 1000  # Default expiry if not specified

    # --- Urgency Bounds (CRITICAL: these are hard clamps) ---
    urgency_min: float = 0.0  # Minimum urgency value
    urgency_max: float = 1.0  # Maximum urgency value
    urgency_default: float = 0.5  # Default urgency for new goals

    # --- Priority Configuration ---
    # Priority is ORDINAL (rank-based), NOT continuous utility
    # No priority can exceed these bounds
    priority_rank_min: int = 1  # Lowest priority rank
    priority_rank_max: int = 100  # Highest priority rank
    priority_rank_default: int = 50  # Default priority rank

    # --- Formation Pathway Controls ---
    # Only these pathways may create goals:
    allow_external_input_goals: bool = True  # Goals from external input
    allow_supervisor_mediated_goals: bool = True  # Goals from supervisor inference
    allow_system_heuristic_goals: bool = False  # Pre-approved system heuristics (disabled by default)

    # Formation requires supervisor visibility
    require_supervisor_visibility: bool = True

    # --- Anti-Reward-Loop Safeguards ---
    enable_urgency_inflation_detector: bool = True
    enable_goal_recreation_detector: bool = True
    enable_persistence_detector: bool = True
    enable_satisfaction_correlation_detector: bool = True

    # Detector thresholds
    urgency_inflation_threshold: float = 0.1  # Max allowed urgency increase per tick
    goal_recreation_window_ticks: int = 50  # Window for detecting recreated goals
    goal_recreation_max_count: int = 3  # Max recreations before flagging
    persistence_max_ticks: int = 500  # Max goal persistence without external justification
    satisfaction_correlation_threshold: float = 0.7  # Correlation threshold for satisfaction-urgency

    # --- Audit Configuration ---
    enable_goal_audit: bool = True
    audit_buffer_size: int = 500

    # --- Supervisor Compatibility ---
    # Goals are advisory; supervisor has final authority
    goals_are_advisory: bool = True  # MUST be True - goals do not command
    supervisor_can_suspend: bool = True
    supervisor_can_retire: bool = True
    supervisor_can_reject: bool = True


# ---------------------------------------------------------------------------
# V6 Supervisory / curriculum / prompt policy configs
# ---------------------------------------------------------------------------


@dataclass
class SupervisorConfig:
    """
    Supervisory controller configuration (V6).

    These fields define buffers and thresholds only; behavioural decisions are
    implemented in the controller layer.
    """

    kappa_s_window: int = 64
    stability_horizon: int = 8  # tuned: was 10
    regime_forget: float = 0.1
    stability_forget: float = 0.05
    stability_threshold: float = 0.7
    tier_e_stability_threshold: float = 0.85
    override_max_ticks: int = 3  # tuned: was 5
    override_cooldown: int = 2  # tuned: was 3
    override_cooldown_min: int = 1
    override_cooldown_max: int = 10
    tier_e_stability_ticks: int = 10
    stillness_release_ticks: int = 3
    stillness_release_threshold: float = 0.08  # tuned: was 0.05
    s_equilibrium_instability_threshold: float = 0.5
    oscillation_threshold: float = 0.30  # tuned: was 0.25
    churn_threshold: float = 0.1
    stillness_tokens: int = 0
    reflect_tokens: int = 512
    act_tokens: int = 4096
    tier_e_token_cap: int = 4096
    s_equilibrium_tier_e_threshold: float = 0.35
    kappa_s_epsilon: float = 1e-6
    kappa_s_norm_alpha: float = 0.2
    kappa_s_norm_min: float = 0.0
    kappa_s_norm_max: float = 5.0
    kappa_s_norm_decay_alpha: float = 0.05  # Decay rate for kappa_s_norm outside ACT (toward neutral)
    kappa_s_norm_decay_raw_influence: float = 0.2  # Fraction of decay allocated to raw signal awareness
    s_equilibrium_regime_weight: float = 0.1
    s_equilibrium_energy_weight: float = 0.2
    s_equilibrium_kappa_weight: float = 0.7
    enable_regime_commitment_advisory: bool = True
    belief_update_alpha: float = 0.2
    belief_floor: float = 0.0
    belief_ceiling: float = 1.0
    belief_update_interval: int = 20
    threshold_adapt_alpha: float = 0.1
    stability_threshold_min: float = 0.5
    stability_threshold_max: float = 0.9
    churn_threshold_min: float = 0.05
    churn_threshold_max: float = 0.2
    oscillation_threshold_min: float = 0.15
    oscillation_threshold_max: float = 0.4
    stillness_release_threshold_min: float = 0.01
    stillness_release_threshold_max: float = 0.1
    belief_memory_size: int = 64
    belief_attribution_window: int = 10
    belief_outcome_delay: int = 5
    belief_attribution_decay: float = 0.1
    enable_regime_commitment_authority: bool = True
    enable_advisory_authority: bool = True
    min_candidate_ticks: int = 3
    min_commitment_confidence: float = 0.6
    envelope_gain: float = 0.5
    envelope_max: float = 0.2
    authority_coherence_min: float = 0.25
    # Rollout flag: False reverts to pre-tune baseline defaults for A/B comparison
    use_tuned_thresholds: bool = True

    def __post_init__(self):
        if not self.use_tuned_thresholds:
            self.oscillation_threshold = 0.25
            self.override_max_ticks = 5
            self.override_cooldown = 3
            self.stillness_release_threshold = 0.05
            self.stability_horizon = 10


@dataclass
class CurriculumV6Config:
    """Configuration for V6 curriculum shaping."""

    stillness_tokens: int = 0
    reflect_tokens: int = 512
    act_tokens: int = 1024
    intensity: float = 1.0
    exploration_rate: float = 0.1
    regulator_gain: float = 0.25
    coherence_gain: float = 0.35
    regulator_window: int = 8
    intensity_floor: float = 0.05
    intensity_ceiling: float = 1.0
    intensity_smoothing: float = 0.35


@dataclass
class HypothesisConfig:
    """Configuration for hypothesis lifecycle."""

    max_active: int = 8
    validation_window: int = 5
    archive_limit: int = 32
    mismatch_threshold: float = 0.2
    regulator_gain: float = 0.2
    coherence_gain: float = 0.25
    validation_window_min: int = 2
    validation_window_max: int = 10
    mismatch_threshold_min: float = 0.05
    mismatch_threshold_max: float = 0.5
    update_alpha: float = 0.2
    prior_default: float = 0.5
    retire_threshold: float = 0.2
    retire_patience: int = 10
    signature_epsilon: float = 1e-6
    max_regimes: int = 6
    regime_sigma: float = 0.25
    regime_update_alpha: float = 0.15
    new_regime_distance_threshold: float = 0.8
    likelihood_floor: float = 1e-6
    evidence_log_cap: float = 10.0
    regime_entropy_smoothing: float = 0.2

    # Regime commitment gate (Phase 7A)
    enable_regime_commitment_gate: bool = True
    commitment_posterior_enter_threshold: float = 0.6
    commitment_posterior_exit_threshold: float = 0.55
    commitment_entropy_enter_threshold: float = 0.5
    commitment_entropy_exit_threshold: float = 0.6
    commitment_stability_enter_threshold: float = 0.6
    commitment_stability_exit_threshold: float = 0.55
    commitment_override_enter_threshold: float = 0.4
    commitment_override_exit_threshold: float = 0.5
    commitment_persistence_ticks: int = 3
    commitment_cooldown_ticks: int = 5
    commitment_entropy_max: float = 1.0


@dataclass
class PromptPolicyConfig:
    """Prompt policy regulator configuration."""

    stability_threshold: float = 0.6
    guard_tighten_threshold: float = 0.2
    max_tokens_reflect: int = 512
    max_tokens_act: int = 1024
    tool_allowance_reflect: bool = False
    tool_allowance_act: bool = True
    regulator_gain: float = 0.2
    coherence_gain: float = 0.3
    tone_bias_limit: float = 0.25
    verbosity_bias_limit: float = 0.2
    verbosity_floor: float = 0.2
    verbosity_ceiling: float = 0.8


@dataclass
class AdaptationConfig:
    """Configuration for adaptation-related signal computation."""

    learning_window: int = 30
    recency_half_life: int = 10
    min_confidence: float = 0.15
    outcome_weight: float = 0.4
    volatility_penalty: float = 0.3
    setback_gain: float = 0.5
    max_pressure: float = 0.15


@dataclass
class CausalAttributionConfig:
    enable: bool = True
    capacity: int = 128


@dataclass
class RegretConfig:
    enable: bool = True
    capacity: int = 64
    decay_rate: float = 0.05
    bias_limit: float = 0.2


@dataclass
class CommitmentConfig:
    enable: bool = True
    capacity: int = 32
    decay_rate: float = 0.08
    cost_limit: float = 1.0
    pressure_gain: float = 0.6
    commitments: list = field(default_factory=list)


@dataclass
class SelfAuthorshipConfig:
    enable: bool = True
    decay_rate: float = 0.08
    recency_window: int = 12
    frequency_norm: int = 5


# ---------------------------------------------------------------------------
# Redaction Configuration (T1)
# ---------------------------------------------------------------------------

@dataclass
class RedactionConfig:
    """
    Redaction (T1) configuration.
    All features default to OFF for baseline equivalence.

    SECURITY CONTRACT:
    - When disabled (enabled=False), no redaction occurs
    - When enabled, sensitive data patterns are masked before logging
    - 14+ default patterns cover common API keys, tokens, credentials
    - Custom patterns can be added without modifying defaults

    CRITICAL INVARIANTS:
    - Redaction NEVER raises exceptions (fails silent, returns original)
    - PEM blocks preserve structure (BEGIN/END markers visible)
    - Partial masking preserves start/end chars for debugging
    """
    # Master enable flag (default OFF for backward compat)
    enabled: bool = False

    # Minimum token length for partial masking (shorter = full redaction)
    min_token_length: int = 18

    # Characters to preserve at start/end of masked tokens
    keep_start_chars: int = 6
    keep_end_chars: int = 4

    # Additional regex patterns to redact (merged with defaults)
    custom_patterns: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Auth Profile Configuration (T3)
# ---------------------------------------------------------------------------

@dataclass
class AuthProfileConfig:
    """
    Auth Profile (T3) configuration.
    All features default to OFF for baseline equivalence.

    SECURITY CONTRACT:
    - When disabled (enabled=False), falls back to single env var key
    - When enabled, manages multiple API keys with rotation and cooldown
    - Cooldown backoff: 1min → 5min → 25min → 1hr (exponential)
    - Billing failures use longer backoff (5hr → 24hr)

    CRITICAL INVARIANTS:
    - Profile rotation is round-robin (oldest lastUsed first)
    - Type preference: oauth > token > api_key
    - Cooldown profiles are tried last (sorted by soonest expiry)
    - Thread-safe updates with locking
    """
    # Master enable flag (default OFF for backward compat)
    enabled: bool = False

    # Cooldown timing (minutes for rate limits)
    cooldown_base_minutes: float = 1.0
    cooldown_max_minutes: float = 60.0
    cooldown_backoff_factor: float = 5.0

    # Billing error cooldown (hours)
    billing_cooldown_base_hours: float = 5.0
    billing_cooldown_max_hours: float = 24.0

    # Failure tracking window
    failure_window_hours: int = 24

    # Rotation strategy
    rotation_strategy: str = "round_robin"  # or "priority"

    # Environment variable patterns to scan for API keys
    env_key_patterns: List[str] = field(default_factory=lambda: [
        "OPENAI_API_KEY",
        "TOM_LLM_API_KEY",
        "ANTHROPIC_API_KEY",
    ])


# ---------------------------------------------------------------------------
# Subsystem Logging Configuration (T4)
# ---------------------------------------------------------------------------

@dataclass
class SubsystemLoggingConfig:
    """
    Subsystem Logging (T4) configuration.
    All features default to OFF for baseline equivalence.

    TELEMETRY CONTRACT:
    - When disabled (enabled=False), no subsystem logging occurs
    - When enabled, provides hierarchical subsystem-tagged logging
    - Console filtering supports wildcard patterns (e.g., "coupling/*")
    - Color coding is deterministic (hash-based per subsystem)

    CRITICAL INVARIANTS:
    - Logging NEVER raises exceptions (fails silent)
    - Console output respects level and filter settings
    - Child loggers inherit parent configuration
    - No metrics computation or policy enforcement
    """
    # Master enable flag (default OFF for backward compat)
    enabled: bool = False

    # Minimum level for console output (TRACE, DEBUG, INFO, WARN, ERROR, FATAL, SILENT)
    console_level: str = "WARN"

    # Minimum level for file output
    file_level: str = "INFO"

    # Subsystem patterns to show on console (wildcards supported)
    # If empty, all subsystems matching console_level are shown
    # Examples: ["coupling/*", "policy/*", "guard/pre"]
    console_subsystem_filter: List[str] = field(default_factory=list)

    # Output format: "pretty" (human-readable), "compact", or "json"
    console_style: str = "pretty"

    # Whether to use ANSI colors in console output
    enable_colors: bool = True

    # Whether to include timestamps in log output
    enable_timestamps: bool = True


# ---------------------------------------------------------------------------
# Payload Logger Configuration (T5)
# ---------------------------------------------------------------------------

@dataclass
class PayloadLoggerConfig:
    """
    Payload Logger (T5) configuration.
    All features default to OFF for baseline equivalence.

    TELEMETRY CONTRACT:
    - When disabled (enabled=False), no payload logging occurs
    - When enabled, logs LLM requests/responses to JSONL files
    - Supports digest computation for payload integrity
    - Redact mode logs metadata only, not prompt/response content

    CRITICAL INVARIANTS:
    - Logging NEVER raises exceptions (fails silent)
    - Payloads exceeding max_payload_size are truncated
    - Token usage statistics are tracked cumulatively
    - Thread-safe file writes
    """
    # Master enable flag (default OFF for backward compat)
    enabled: bool = False

    # Path to JSONL log file (supports ~ expansion)
    log_path: str = "~/.tom/logs/payloads.jsonl"

    # Whether to log LLM requests
    log_requests: bool = True

    # Whether to log LLM responses
    log_responses: bool = True

    # Whether to include token usage stats in logs
    include_usage: bool = True

    # Whether to include SHA-256 digests in logs
    include_digest: bool = True

    # Maximum payload size in bytes (larger payloads are truncated)
    max_payload_size: int = 102400  # 100KB

    # If True, log metadata only, not actual prompt/response content
    redact_prompts: bool = False


# ---------------------------------------------------------------------------
# Context Guard Configuration (T6)
# ---------------------------------------------------------------------------

@dataclass
class ContextGuardConfig:
    """
    Context Guard (T6) configuration.
    All features default to OFF for baseline equivalence.

    TELEMETRY CONTRACT:
    - When disabled (enabled=False), no context guard checks occur
    - When enabled, monitors token usage against configurable thresholds
    - Hard minimum (16k tokens) blocks further output to prevent context exhaustion
    - Warning threshold (32k tokens) emits advisories for proactive management

    CRITICAL INVARIANTS:
    - Guard is advisory only, does not block execution
    - Token estimation is approximate (chars/4 heuristic)
    - All thresholds are configurable
    """
    # Master enable flag (default OFF for backward compat)
    enabled: bool = False

    # Token thresholds
    hard_min_tokens: int = 16_000
    warn_below_tokens: int = 32_000

    # History management
    max_history_turns: int = 50

    # Compaction settings (optional sub-feature)
    enable_compaction: bool = True
    compaction_chunk_ratio: float = 0.4
    compaction_min_ratio: float = 0.15
    compaction_safety_margin: float = 1.2

    # Default context window size (fallback)
    default_context_tokens: int = 128_000


# ---------------------------------------------------------------------------
# Transcript Repair Configuration (T7)
# ---------------------------------------------------------------------------

@dataclass
class TranscriptRepairConfig:
    """
    Transcript Repair (T7) configuration.
    All features default to OFF for baseline equivalence.

    REPAIR CONTRACT:
    - When disabled (enabled=False), no repair occurs
    - When enabled, validates and repairs tool-call/tool-result pairing
    - Synthetic error results are injected for missing tool results
    - Duplicate results for the same tool call are dropped
    - Orphan results (no matching call) are removed
    - Results are reordered to immediately follow their tool calls

    CRITICAL INVARIANTS:
    - Repair NEVER raises exceptions (fails silent, returns original)
    - All changes are logged in TranscriptRepairReport
    - Synthetic messages are clearly marked with ToM prefix
    - Session cache is optional and bounded
    """
    # Master enable flag (default OFF for backward compat)
    enabled: bool = False

    # Session cache for pre-warming transcript state
    enable_session_cache: bool = True
    cache_ttl_seconds: int = 45
    cache_max_entries: int = 100

    # Error message for synthetic results (clearly marked as ToM-injected)
    synthetic_error_message: str = "[ToM] Missing tool result; inserted synthetic error result for transcript repair."


# ---------------------------------------------------------------------------
# Sandbox Path Protection Configuration (T2)
# ---------------------------------------------------------------------------

@dataclass
class SandboxConfig:
    """
    Sandbox Path Protection (T2) configuration.
    All features default to OFF for baseline equivalence.

    SECURITY CONTRACT:
    - When disabled (enabled=False), no path validation occurs
    - When enabled, all file paths are validated before use
    - block_symlinks prevents symlink-based sandbox escapes
    - block_dotdot prevents ../ traversal attacks
    - blocked_paths are expanded at validation time (supports ~/)

    CRITICAL INVARIANTS:
    - Paths MUST be validated before any file I/O
    - Unicode space normalization prevents visual spoofing
    - Symlink detection walks all path components
    - Blocked paths include sensitive system directories
    """
    # Master enable flag (default OFF for backward compat)
    enabled: bool = False

    # Workspace root directory (relative paths resolved from here)
    workspace_root: str = "./"

    # Block symlinks that could escape sandbox
    block_symlinks: bool = True

    # Block ../ traversal patterns
    block_dotdot: bool = True

    # If non-empty, only allow these file extensions
    allowed_extensions: List[str] = field(default_factory=list)

    # Paths that are always blocked (expanded at validation time)
    blocked_paths: List[str] = field(default_factory=lambda: [
        "/etc",
        "/var",
        "/usr",
        "~/.ssh",
        "~/.aws",
        "~/.config",
        # Windows equivalents
        "C:/Windows",
        "C:/Program Files",
        "C:/Program Files (x86)",
    ])


# ---------------------------------------------------------------------------
# Filesystem Isolation Configuration (Phase 10)
# ---------------------------------------------------------------------------

@dataclass
class FilesystemIsolationConfig:
    """
    Filesystem Isolation (Phase 10) configuration for PA sandbox.
    All features default to OFF for baseline equivalence.

    SECURITY CONTRACT:
    - When disabled (enabled=False), no path validation occurs
    - When enabled and fs_root is set, all file paths are validated
    - Path traversal (..) that escapes fs_root is blocked
    - Symlinks pointing outside fs_root are blocked by default
    - Absolute paths are blocked by default (relative to fs_root)

    CRITICAL INVARIANTS:
    - Feature flag enabled=False by default (existing behavior unchanged)
    - Path validation uses os.path.realpath for canonicalization
    - Allowlist patterns support glob matching
    - Never raises exceptions (returns validation errors instead)

    See: policy/path_validation.py for implementation details.
    """
    # Master enable flag (default OFF for backward compat)
    enabled: bool = False

    # Root directory for all file operations (empty = no restriction)
    # When set, all file paths are resolved relative to this root
    fs_root: str = ""

    # Whether to allow symlinks that stay within fs_root
    # False = symlinks that resolve outside fs_root are blocked
    allow_symlinks: bool = False

    # Whether to allow absolute paths
    # False = only paths relative to fs_root are allowed
    allow_absolute: bool = False

    # Additional paths allowed outside fs_root (exact match or glob)
    # Useful for specific project needs (e.g., ["/tmp/scratch/*"])
    allowed_paths: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Tool Policy Configuration (T9)
# ---------------------------------------------------------------------------

@dataclass
class ToolPolicyConfig:
    """
    Tool Policy (T9) configuration.
    All features default to OFF for baseline equivalence.

    POLICY CONTRACT:
    - When disabled (enabled=False), all tools are allowed (pass-through)
    - When enabled, cascading allow/deny rules are applied
    - Profiles define baseline tool sets: minimal, coding, messaging, full
    - Group expansion resolves group:memory, group:web, etc.
    - Aliases map tool names to canonical forms

    CRITICAL INVARIANTS:
    - Policy NEVER raises exceptions (fails silent, allows tool)
    - Deny list takes precedence over allow list
    - Emergency mode blocks most tools regardless of profile
    - Sandbox mode is more restrictive than normal mode
    """
    # Master enable flag (default OFF for backward compat)
    enabled: bool = False

    # Default profile: minimal, coding, messaging, full
    default_profile: str = "coding"

    # Explicit allow list (merged with profile tools)
    # Supports tool names and groups (group:memory, group:web, etc.)
    allow_list: List[str] = field(default_factory=list)

    # Explicit deny list (takes precedence over allow list)
    # Supports tool names and groups
    deny_list: List[str] = field(default_factory=list)

    # Tool name aliases for normalization
    # Maps alias -> canonical name (e.g., "search" -> "web.search")
    tool_aliases: Dict[str, str] = field(default_factory=dict)

    # Custom tool groups (merged with built-in groups)
    # Maps group name -> list of tool names
    custom_groups: Dict[str, List[str]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Hybrid Search Configuration (T8)
# ---------------------------------------------------------------------------

@dataclass
class HybridSearchConfig:
    """
    Hybrid Search (T8) configuration.
    Vector-only search. BM25 fields are DEPRECATED and ignored.

    SEARCH CONTRACT:
    - When disabled (enabled=False), hybrid search returns empty results
    - When enabled, performs vector (semantic) search
    - Score fusion: score = vector_weight * vector_score
    - Results sorted by score descending

    CRITICAL INVARIANTS:
    - Search NEVER raises exceptions (fails silent, returns empty)
    - Score fusion is deterministic and bounded [0, 1]
    - Statistics are tracked for observability
    """
    # Master enable flag — vector search is the default retrieval path
    enabled: bool = True

    # Score fusion weights — vector-only
    vector_weight: float = 1.0
    text_weight: float = 0.0  # DEPRECATED: ignored, kept for config compat

    # Result limits
    max_results: int = 10

    # Minimum score threshold (results below this are filtered)
    min_score_threshold: float = 0.1

    # DEPRECATED: BM25 parameters — ignored, kept for config deserialization compat
    bm25_k1: float = 1.2
    bm25_b: float = 0.75


# ---------------------------------------------------------------------------
# Approval Manager Configuration (T10)
# ---------------------------------------------------------------------------

@dataclass
class ApprovalManagerConfig:
    """
    Execution Approval Manager (T10) configuration.
    All features default to OFF for baseline equivalence.

    APPROVAL CONTRACT:
    - When disabled (enabled=False), no approval gates apply
    - When enabled, dangerous operations require explicit approval
    - Auto-approve safe operations (configurable)
    - Pending requests expire after configurable timeout
    - Maximum pending requests enforced to prevent memory exhaustion

    CRITICAL INVARIANTS:
    - Approval is ADVISORY; supervisor/policy guard retain final authority
    - Approval methods NEVER raise exceptions (fail silent)
    - Expired requests are automatically denied (TIMEOUT)
    - All decisions are timestamped and auditable
    - Thread-safe concurrent access to pending map
    """
    # Master enable flag (default OFF for backward compat)
    enabled: bool = False

    # Timeout for pending approvals (seconds)
    default_timeout_seconds: float = 300.0  # 5 minutes

    # Maximum pending requests to track
    max_pending: int = 100

    # Auto-approve operations classified as SAFE
    auto_approve_safe_ops: bool = True

    # Patterns that indicate dangerous operations
    dangerous_patterns: List[str] = field(default_factory=lambda: [
        "rm -rf",
        "sudo",
        "chmod 777",
        "DELETE FROM",
        "> /dev/",
        "DROP TABLE",
        "DROP DATABASE",
        "format C:",
        "dd if=",
        "mkfs",
        ":(){:|:&};:",  # Fork bomb
        "shutdown",
        "reboot",
        "init 0",
        "init 6",
    ])

    # Compiled patterns (internal cache, populated on first use by engine)
    # This field must exist for ApprovalManagerEngine compatibility
    _compiled_patterns: Optional[List[Any]] = field(
        default=None, repr=False, compare=False
    )


# ---------------------------------------------------------------------------
# Plugin SDK Configuration (T11)
# ---------------------------------------------------------------------------

@dataclass
class PluginConfig:
    """
    Plugin SDK (T11) configuration.
    All features default to OFF for baseline equivalence.

    PLUGIN CONTRACT:
    - When disabled (enabled=False), no plugin system is active
    - When enabled, plugins can register hooks, tools, services, commands
    - Hook execution respects catch_errors setting
    - Plugin directories are scanned for auto-loading
    - Plugins must be in allowlist to load (deny-by-default)

    CRITICAL INVARIANTS (Phase 7):
    - Plugins NEVER raise exceptions when catch_errors=True (fail silent)
    - Default enabled=False for backward compatibility
    - Statistics are non-authoritative telemetry only
    - All plugin effects are bounded, reversible, and auditable
    - Plugins cannot bypass policy/approval enforcement
    - Protected plugins cannot be unregistered by other plugins
    """
    # Master enable flag (default OFF for backward compat)
    enabled: bool = False

    # Directories to scan for plugins (relative to workspace root)
    plugin_dirs: List[str] = field(default_factory=list)

    # Whether to catch and log errors instead of raising
    catch_errors: bool = True

    # Whether to log hook execution details
    log_hook_execution: bool = False

    # Phase 7: Plugin Allowlist (deny-by-default)
    # Only plugins in this list can be loaded
    # Empty list = no plugins load (safest default)
    allowlist: List[str] = field(default_factory=list)

    # Phase 7: Protected plugin IDs that cannot be unregistered
    # These are system-critical plugins (e.g., policy enforcement)
    protected_plugins: List[str] = field(default_factory=lambda: [
        "phase6-policy-enforcement",
        "system-audit",
        "phase8-memory-pipeline",
    ])

    # Phase 7: Per-tenant plugin overrides
    # Format: {"tenant_id": {"allowlist": [...], "denylist": [...]}}
    tenant_overrides: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)

    # Phase 7: Rate limiting for hooks
    max_hook_runtime_ms: int = 5000  # Max execution time per hook call
    max_errors_before_disable: int = 10  # Auto-disable plugin after N errors

    # Phase 7: Audit all plugin actions
    audit_plugin_actions: bool = True


# ---------------------------------------------------------------------------
# Phase 5 Context Manager Configuration (DEFAULT ON per Phase 5 spec)
# ---------------------------------------------------------------------------

@dataclass
class ContextManagerConfig:
    """
    Phase 5 Context Manager configuration.
    DEFAULT ON for budget accounting and transcript repair.

    CRITICAL INVARIANTS:
    - Multi-app isolation enforced via isolation_key (tenant_id:app_id:session_id)
    - App A cannot see App B context even if session_id collides
    - Budget accounting and repair ON by default
    - Compaction OFF by default (opt-in)
    """
    # Master enable flag (DEFAULT ON per Phase 5 spec)
    enabled: bool = True

    # Budget configuration (ON by default)
    budget_enabled: bool = True
    hard_cap_tokens: int = 128_000
    soft_cap_tokens: int = 100_000
    reserve_tokens: int = 16_000

    # Transcript repair (ON by default)
    repair_enabled: bool = True

    # Compaction (OFF by default)
    compaction_enabled: bool = False
    compaction_mode: str = "deterministic"  # "deterministic" | "truncate"
    compaction_threshold: float = 0.8
    never_compact_last_n: int = 3

    # Memory configuration
    max_memory_anchors: int = 8
    min_memory_anchors: int = 2
    reduce_memory_under_pressure: bool = True

    # Compaction policy
    max_summary_ratio: float = 0.3
    min_block_tokens_to_compact: int = 100

    # Telemetry
    log_token_usage: bool = True
    log_compaction_events: bool = True


# ---------------------------------------------------------------------------
# Phase 6 Policy Cascade Configuration (DEFAULT ON per Phase 6 spec)
# ---------------------------------------------------------------------------

@dataclass
class PolicyCascadeConfig:
    """
    Phase 6 Policy Cascade configuration.
    DEFAULT ON per Phase 6 spec.

    The Policy Cascade enforces multi-layer safety policies:
    - Layer 1: HARD SAFETY (global invariants, never bypass)
    - Layer 2: CAPABILITY GATING (tools/channels by tenant/mode)
    - Layer 3: CONTEXTUAL RISK (approval triggers, rate limits)

    CRITICAL INVARIANTS:
    - Deny by default (no explicit allow = deny)
    - Layer ordering enforced (L1 > L2 > L3)
    - Hard safety errors CANNOT be caught/bypassed
    - Integrates with IsolationKey for multi-tenant policies
    """
    # Master enable flag (DEFAULT ON per Phase 6 spec)
    enabled: bool = True

    # Layer enables
    layer1_enabled: bool = True  # Hard safety
    layer2_enabled: bool = True  # Capability gating
    layer3_enabled: bool = True  # Contextual risk

    # Approval workflow
    approval_workflow_enabled: bool = True
    default_approval_timeout_seconds: int = 300

    # Risk mode
    risk_mode: str = "conservative"  # "conservative" | "permissive"

    # Audit settings
    audit_all_decisions: bool = True
    audit_redact_payloads: bool = True

    # Default channel settings (all disabled by default)
    channel_slack_enabled: bool = False
    channel_signal_enabled: bool = False
    channel_whatsapp_enabled: bool = False
    channel_imessage_enabled: bool = False


# ---------------------------------------------------------------------------
# Phase 8 Trace Policy Configuration (fail-closed by default)
# ---------------------------------------------------------------------------

@dataclass
class TracePolicyConfig:
    """
    Phase 8 Trace Policy configuration.
    FAIL-CLOSED BY DEFAULT per Phase 6 enforcement semantics.

    CRITICAL INVARIANTS:
    - fail_closed=True by default (trace writes denied if policy check fails)
    - allow_fail_open=False by default (escape hatch for dev only, explicit opt-in)
    - Retention limits prevent unbounded trace growth
    - All trace operations are audited when enabled
    """
    # Fail-closed enforcement (MUST default to True)
    fail_closed: bool = True

    # Dev-only escape hatch (MUST default to False)
    # Only set to True in dev/test environments after explicit review
    allow_fail_open: bool = False

    # Retention limits per isolation key (tenant:app:session)
    max_traces_per_session: int = 1000
    trace_ttl_hours: int = 168  # 7 days

    # Auto-cleanup settings
    auto_cleanup_enabled: bool = True
    cleanup_interval_hours: int = 24

    # Audit settings
    audit_trace_operations: bool = True


# ---------------------------------------------------------------------------
# Phase 8 Memory Pipeline Configuration (re-export for convenience)
# ---------------------------------------------------------------------------

@dataclass
class MemoryPipelineConfig:
    """
    Phase 8 Memory-to-Decision Pipeline configuration.
    Shadow mode by default - computes suggestions but does not change behavior.

    CRITICAL INVARIANTS:
    - shadow_mode=True by default (suggestions computed but not applied)
    - apply_to_planning=False by default (no behavior changes until Phase 8b)
    - Deterministic rule-based suggestion generation
    """
    enabled: bool = True
    shadow_mode: bool = True  # CRITICAL: Default ON
    apply_to_planning: bool = False  # CRITICAL: Default OFF
    min_hit_score: float = 0.3
    min_suggestion_confidence: float = 0.4
    max_hits_per_query: int = 10
    max_suggestions_per_query: int = 5
    max_context_block_tokens: int = 500
    max_plan_hint_tokens: int = 200
    max_total_suggestion_tokens: int = 800
    use_deterministic_rules: bool = True
    trace_enabled: bool = True
    trace_redaction: str = "strict"


# ---------------------------------------------------------------------------
# Top-level ToM configuration
# ---------------------------------------------------------------------------

@dataclass
class ToMConfig:
    identity: IdentityConfig = field(default_factory=IdentityConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)
    env: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)
    direct_contextual_17d_authority: DirectContextual17DAuthorityConfig = field(
        default_factory=DirectContextual17DAuthorityConfig
    )
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    initiative_pulse: InitiativePulseConfig = field(default_factory=InitiativePulseConfig)

    cognitive: CognitiveConfig = field(default_factory=CognitiveConfig)
    supervisor: SupervisorConfig = field(default_factory=SupervisorConfig)
    curriculum_v6: CurriculumV6Config = field(default_factory=CurriculumV6Config)
    hypothesis: HypothesisConfig = field(default_factory=HypothesisConfig)
    prompt_policy: PromptPolicyConfig = field(default_factory=PromptPolicyConfig)
    adaptation: AdaptationConfig = field(default_factory=AdaptationConfig)
    causal_attribution: CausalAttributionConfig = field(default_factory=CausalAttributionConfig)
    regret: RegretConfig = field(default_factory=RegretConfig)
    commitment: CommitmentConfig = field(default_factory=CommitmentConfig)
    self_authorship: SelfAuthorshipConfig = field(default_factory=SelfAuthorshipConfig)

    # Phase 8.1/9/11/12B/13.1/19/20/21 enhancement configs (all default OFF)
    rgm_enhancement: RGMEnhancementConfig = field(default_factory=RGMEnhancementConfig)
    phase9_observability: Phase9ObservabilityConfig = field(default_factory=Phase9ObservabilityConfig)
    epistemic_calibration: EpistemicCalibrationConfig = field(default_factory=EpistemicCalibrationConfig)
    evidence_binding: EvidenceBindingConfig = field(default_factory=EvidenceBindingConfig)
    drift_control: DriftControlConfig = field(default_factory=DriftControlConfig)
    authority_interface: AuthorityInterfaceConfig = field(default_factory=AuthorityInterfaceConfig)
    authority_governance: AuthorityGovernanceConfig = field(default_factory=AuthorityGovernanceConfig)
    goal_formation: GoalFormationConfig = field(default_factory=GoalFormationConfig)

    # Sandbox Path Protection (T2) config (default OFF)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)

    # Filesystem Isolation (Phase 10) config (default OFF)
    filesystem_isolation: "FilesystemIsolationConfig" = field(
        default_factory=lambda: FilesystemIsolationConfig()
    )

    # Redaction (T1) config (default OFF)
    redaction: "RedactionConfig" = field(default_factory=lambda: RedactionConfig())

    # Auth Profile (T3) config (default OFF)
    auth_profile: "AuthProfileConfig" = field(default_factory=lambda: AuthProfileConfig())

    # Subsystem Logging (T4) config (default OFF)
    subsystem_logging: "SubsystemLoggingConfig" = field(default_factory=lambda: SubsystemLoggingConfig())

    # Payload Logger (T5) config (default OFF)
    payload_logger: "PayloadLoggerConfig" = field(default_factory=lambda: PayloadLoggerConfig())

    # Context Guard (T6) config (default OFF)
    context_guard: "ContextGuardConfig" = field(default_factory=lambda: ContextGuardConfig())

    # Transcript Repair (T7) config (default OFF)
    transcript_repair: "TranscriptRepairConfig" = field(default_factory=lambda: TranscriptRepairConfig())

    # Context Manager (Phase 5) config (DEFAULT ON per spec)
    context_manager: ContextManagerConfig = field(default_factory=ContextManagerConfig)

    # Hybrid Search (T8) config (default OFF)
    hybrid_search: "HybridSearchConfig" = field(default_factory=lambda: HybridSearchConfig())

    # Tool Policy (T9) config (default OFF)
    tool_policy: "ToolPolicyConfig" = field(default_factory=lambda: ToolPolicyConfig())

    # Approval Manager (T10) config (default OFF)
    approval_manager: "ApprovalManagerConfig" = field(default_factory=lambda: ApprovalManagerConfig())

    # Plugin SDK (T11) config (default OFF)
    plugin: "PluginConfig" = field(default_factory=lambda: PluginConfig())

    # Policy Cascade (Phase 6) config (DEFAULT ON)
    policy_cascade: "PolicyCascadeConfig" = field(default_factory=lambda: PolicyCascadeConfig())

    # Phase 8 Memory Pipeline config (shadow mode ON by default)
    memory_pipeline: "MemoryPipelineConfig" = field(default_factory=lambda: MemoryPipelineConfig())

    # Phase 8 Trace Policy config (fail-closed by default)
    trace_policy: "TracePolicyConfig" = field(default_factory=lambda: TracePolicyConfig())

    # Shadow Reward (default OFF — config wired from tunable_params.py)
    shadow_reward: Any = None

    # Hunger Drive (default OFF — config wired from tunable_params.py)
    hunger_drive: Any = None

    # Autonomic Coupling (default ON — config wired from tunable_params.py)
    autonomic_coupling: Any = None

    # Legacy shim
    dt: float = 1.0


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class ConfigRegistry:
    def __init__(self, base_cfg: Optional[ToMConfig] = None) -> None:
        self._cfg: ToMConfig = base_cfg or ToMConfig()

    @property
    def cfg(self) -> ToMConfig:
        return self._cfg

    def as_dict(self) -> Dict[str, Any]:
        c = self._cfg
        return {
            "identity": vars(c.identity),
            "timing": vars(c.timing),
            "env": vars(c.env),
            "persistence": vars(c.persistence),
            "direct_contextual_17d_authority": vars(
                c.direct_contextual_17d_authority
            ),
            "logging": vars(c.logging),
            "initiative_pulse": vars(c.initiative_pulse),
            "cognitive": vars(c.cognitive),
            "supervisor": vars(c.supervisor),
            "curriculum_v6": vars(c.curriculum_v6),
            "hypothesis": vars(c.hypothesis),
            "prompt_policy": vars(c.prompt_policy),
            "adaptation": vars(c.adaptation),
            "causal_attribution": vars(c.causal_attribution),
            "regret": vars(c.regret),
            "commitment": vars(c.commitment),
            "self_authorship": vars(c.self_authorship),
            "rgm_enhancement": vars(c.rgm_enhancement),
            "phase9_observability": vars(c.phase9_observability),
            "epistemic_calibration": vars(c.epistemic_calibration),
            "evidence_binding": vars(c.evidence_binding),
            "drift_control": vars(c.drift_control),
            "authority_interface": vars(c.authority_interface),
            "authority_governance": vars(c.authority_governance),
            "goal_formation": vars(c.goal_formation),
            "sandbox": vars(c.sandbox),
            "redaction": vars(c.redaction),
            "auth_profile": vars(c.auth_profile),
            "subsystem_logging": vars(c.subsystem_logging),
            "payload_logger": vars(c.payload_logger),
            "context_guard": vars(c.context_guard),
            "transcript_repair": vars(c.transcript_repair),
            "hybrid_search": vars(c.hybrid_search),
            "tool_policy": vars(c.tool_policy),
            "approval_manager": vars(c.approval_manager),
            "plugin": vars(c.plugin),
            "policy_cascade": vars(c.policy_cascade),
            "memory_pipeline": vars(c.memory_pipeline),
            "trace_policy": vars(c.trace_policy),
        }

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        for section_name, section_data in (data or {}).items():
            section_obj = getattr(self._cfg, section_name, None)
            if section_obj is None or not isinstance(section_data, dict):
                continue
            for k, v in section_data.items():
                if hasattr(section_obj, k):
                    setattr(section_obj, k, v)


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    reg = ConfigRegistry()
    print("Initial cfg:", reg.as_dict())
    reg.update_from_dict({"timing": {"dt": 0.2}})
    print("Updated dt:", reg.cfg.timing.dt)
# COMMENTARY HOLD: Full per-symbol documentation deferred; existing logic left untouched to avoid accidental authority shifts.
