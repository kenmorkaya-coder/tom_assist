"""
Tunable Parameters Configuration.

This module defines dataclasses for ALL tunable parameters discovered in the
codebase audit. These parameters were previously hardcoded across 25+ files.

Total: 150+ tunable parameters organized by subsystem.

Usage:
    from config.tunable_params import TunableParams
    params = TunableParams()
    kappa_decay = params.sicd.kappa_decay  # 0.03

Source Files (where hardcoded values were found):
    - agency/mechanics/sicd_kappa_update_codev.py
    - agency/mechanics/sicd_antifragility.py
    - agency/mechanics/sicd_stiffness.py
    - agency/drift_influence.py
    - agency/drift_control_enhanced.py
    - agency/dynamics.py
    - agency/agency_controller.py
    - ethos/ethos_system.py
    - policy/policy_guard.py
    - metrics/drift_verifier.py
    - integration/orchestrator.py
    - integration/openai_client.py
    - integration/ollama_client.py
    - integration/budget_manager.py
    - integration/context_manager.py
    - integration/compactor.py
    - coupling/handshake_controller.py
    - coupling/coupling_state_machine.py
    - memory/learning_memory.py
    - controller/tom_controller.py
    - interface/tom_voice.py
    - interface/chat_adapter.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Optional, Tuple

# Import from router.providers.config
from gateway.vendor.rgm17d.router.providers.config import (
    IntegrationsConfig,
    WebSearchIntegrationConfig,
    FileReadIntegrationConfig,
    SandboxExecIntegrationConfig,
)


# ============================================================================
# SICD / TREE MECHANICS
# ============================================================================

@dataclass(frozen=True)
class SICDKappaUpdateConfig:
    """
    SICD Kappa Update parameters.

    Source: agency/mechanics/sicd_kappa_update_codev.py
    """
    # Growth parameters
    g_max: float = 0.15          # Max axial growth rate (scaled by psi)
    r_min: float = 0.05          # Resource threshold
    c_grow: float = 0.5          # Resource growth threshold
    ell_min: float = 0.3         # Min element length
    ell_max: float = 5.0         # Max element length

    # Stress EMA smoothing
    sigma_ema_alpha: float = 0.05       # Stress EMA smoothing factor
    overload_ema_alpha: float = 0.05    # Overload EMA smoothing factor

    # Spawn sigma bands
    spawn_sigma_ema_low: float = 0.005  # Low spawn sigma band (calibrated to primary sigma_ema)
    spawn_sigma_ema_high: float = 1.50  # High spawn sigma band
    overload_ema_prune_thresh: float = 0.80  # Overload pruning threshold

    # Diversity and canopy
    diversity_min_deg: float = 10.0     # Min diversity in degrees
    canopy_bin_deg: float = 8.0         # Canopy binning in degrees
    canopy_max_density: float = 12.0    # Max canopy density (children per bin)
    max_children_per_node: int = 6      # Max children per parent

    # Spawn and pruning
    spawn_sweet_steps: int = 3          # Sustained good stress window
    prune_sigma_high: float = 2.5       # Overload pruning threshold
    min_branches_before_prune: int = 15 # Minimum branches before pruning starts
    prune_size_ref: int = 40            # Pruning reference size
    prune_size_power: float = 3.0       # Pruning power law exponent

    # Healing and damage
    heal_rate: float = 0.05             # Branch healing rate
    damage_rate: float = 0.10           # Branch damage rate

    # Kappa decay (CRITICAL)
    kappa_decay: float = 0.03           # Semantic kappa decay for over-rep axes

    # Leaf mechanics
    leaf_growth_rate: float = 0.15      # Leaf growth in sweet sigma band
    leaf_decay_rate: float = 0.02       # Leaf decay outside sweet band
    leaf_sigma_low: float = 0.3         # Lower sigma bound for leaf growth
    leaf_sigma_high: float = 2.5        # Upper sigma bound for leaf growth
    leaf_semantic_floor: float = 0.85   # Semantic influence floor on leaves
    leaf_spawn_gain: float = 0.8        # Leaf contribution to spawn
    leaf_spawn_max_effect: float = 1.0  # Max leaf effect on spawn

    # Leaf axes v2
    leaf_axes_v2_alpha: float = 0.7     # Leaf axis blend weight
    leaf_axes_v2_beta: float = 0.2      # Leaf axis EMA step size
    enable_leaf_axes_v2: bool = True    # Enable v2 axis reorientation

    # Semantic controller
    enable_semantic_controller: bool = True  # Gate for semantic steering
    tau_trunk: float = 0.4              # Trunk axis decay tau
    tau_sem: float = 1.0                # Semantic tau reference
    gamma_spawn_sem: float = 1.0        # Spawn-time semantic bias strength
    beta_sem: float = 1e-4              # Semantic pressure scaling
    eps_axis: float = 1e-4              # Axis normalization epsilon

    # Spawn axis jitter
    spawn_axis_jitter: float = 0.03     # Spawn axis exploration jitter
    spawn_axis_jitter_min: float = 0.005  # Minimum jitter floor
    spawn_axis_jitter_dev_scale: float = 0.50  # Dev-stage exploration scale
    spawn_axis_eps_floor: float = 0.01  # Axis weight epsilon floor
    spawn_axis_uniform_mix: float = 0.02   # Uniform weight blend at spawn
    spawn_axis_semantic_mix: float = 0.10  # Semantic weight blend at spawn
    spawn_axis_dirichlet_strength: float = 10.0  # Dirichlet noise strength
    spawn_axis_noise_by_siblings: float = 0.12   # Sibling-dependent noise scaling
    spawn_axis_dirichlet_sib_offset: int = 8     # Sibling count offset for strength
    spawn_axis_dirichlet_strength_cap: float = 4.0  # Max strength cap

    # Tau blend parameters
    tau_blend_alpha_max: float = 0.85   # From env or default
    tau_blend_s0: float = 0.3           # From env or default
    tau_blend_p: float = 2.0            # From env or default

    # Gain clamps
    kappa_gain_clamp_min: float = 0.80  # Gain update stability min
    kappa_gain_clamp_max: float = 1.25  # Gain update stability max

    # Per-leaf semantic vectors
    enable_leaf_vec: bool = True
    leaf_vec_ema_alpha: float = 0.15
    leaf_vec_confidence_gate: float = 0.3
    leaf_vec_decay_half_life: int = 50

    # Per-leaf semantic vectors — behavior coupling (Phase 3)
    leaf_vec_growth_gain: float = 0.3
    leaf_vec_spawn_mix: float = 0.05
    leaf_vec_prune_age_boost: float = 0.1

    # E5/M1 competitive district recruitment.
    district_owned_penalty: float = 0.5
    district_recruitment_occupancy_penalty: float = 0.05
    district_own_tau: float = 0.9847755204277407
    district_exclusion_strength: float = 0.3
    district_owner_alpha: float = 0.2
    district_owner_alpha_mode: str = "count_aware"
    district_owner_alpha_floor: float = 0.02
    district_stale_horizon: int = 200
    district_protection_gain: float = 99.0
    district_stale_strength_decay: float = 0.99
    district_content_source: str = "17d"
    district_routing_source: str = "17d"
    district_imprint_gate_17d: bool = True
    district_imprint_gate_17d_top_k: int = 50

    # ------------------------------------------------------------------
    # Selective leaf-vec-age prune (2026-05-01, P10 cascade fix).
    # Diagnosis: live P10 collapse came from synchronized
    # ``prune_leaf_vec_age`` waves. Old rule pruned at
    # ``sem_vec_age > 2 * leaf_vec_decay_half_life`` (~100 ticks),
    # which is too short for semantic memory and too coarse — it
    # treated age alone as sufficient cause for removal.
    #
    # New rule (in branch_physics_loop.py): a branch is age-prune
    # eligible only if ALL three are true:
    #   1. sem_vec_age >= leaf_vec_hard_stale_age_ticks  (truly stale)
    #   2. sigma_ema   <= leaf_vec_age_prune_sigma_max   (not load-bearing)
    #   3. kappa       <= leaf_vec_age_prune_kappa_max   (structurally weak)
    # Plus a per-step cap on age-prunes (engine.step) to prevent the
    # synchronized cascade even if many branches happen to qualify.
    #
    # The cap is the smaller of an absolute ceiling and a fraction of
    # the live tree:
    #   cap = min(max_per_step, max(1, int(N * max_fraction_per_step)))
    leaf_vec_hard_stale_age_ticks: int = 2000          # ~20× the old threshold
    leaf_vec_age_prune_sigma_max: float = 0.02         # any current activity preserves
    leaf_vec_age_prune_kappa_max: float = 0.08         # weak-only (mean κ ≈ 0.05)
    leaf_vec_age_prune_max_per_step: int = 100         # absolute ceiling
    leaf_vec_age_prune_max_fraction_per_step: float = 0.005  # 0.5% of tree per tick



@dataclass(frozen=True)
class SICDAntifragilityConfig:
    """
    SICD Antifragility parameters.

    Source: agency/mechanics/sicd_antifragility.py
    """
    sigma_min: float = 0.35     # Minimum stress threshold
    sigma_star: float = 0.55    # Target antifragile stress
    a1: float = 0.1             # Low-stress gain
    a2: float = 0.8             # Sweet-spot gain
    d1: float = 0.3             # Damage slope beyond sigma_star
    a_mid: float = 6.0          # Sigmoid steepness for stability (gamma_mid)
    e_ratio_floor: float = 0.05 # Hard floor to prevent collapse
    e_ratio_cap: float = 0.98   # Hard cap to prevent saturation


@dataclass(frozen=True)
class SICDStiffnessConfig:
    """
    SICD Stiffness parameters.

    Source: agency/mechanics/sicd_stiffness.py
    """
    kappa_min: float = 0.1      # Minimum stiffness
    kappa_max: float = 10.0     # Maximum stiffness
    e_ratio_max: float = 10.0   # Max energy ratio
    r_min: float = 0.05         # Min radius
    r_max: float = 5.0          # Max radius
    m_eff: float = 1.0          # Effective mass
    kappa_softening_factor: float = 0.9  # Negative stiffness softening
    R_ref: float = 6.0          # Reference E_p/E_k ratio


@dataclass(frozen=True)
class ToMDirectiveConstraintConfig:
    """ToM authority-throat directive constraint — Stage A of the throat
    plan. When enabled (default ON per CLAUDE.md feature-enable policy),
    the orchestrator inserts a RESPONSE SHAPE CONSTRAINT block into the
    LLM prompt whenever an organism authority action is available, and
    runs a one-shot validator + retry on the response.

    Flip enabled=False to revert the orchestrator to its prior behaviour
    (no constraint block, no validator, no retry). The wiring on the
    controller side stays active — meta["tom_authority_action"] is still
    set; the orchestrator just ignores it.

    Source: integration/tom_directive_constraint.py
    Spec:   docs/contracts/tom_authority_throat_plan.md §7.3 + §7.4
    """
    enabled: bool = True
    enable_validator: bool = True   # if False: constraint block in prompt only,
                                    # no post-response validation/retry
    max_retries: int = 1            # capped at 1 per plan §7.4
    log_passthrough: bool = True    # log the response when validator fails
                                    # both first try and retry


# ============================================================================
# DRIFT CONTROL
# ============================================================================

@dataclass(frozen=True)
class DriftVerifierConfig:
    """
    Drift Verifier parameters.

    Source: metrics/drift_verifier.py
    """
    # Main threshold
    threshold_block: float = 0.70       # Block threshold
    threshold_revise: float = 0.35      # Revise threshold

    # Residual component weights (for weighted aggregation)
    weight_uncited: float = 0.35
    weight_contradiction: float = 0.45
    weight_policy: float = 0.15
    weight_confidence: float = 0.03
    weight_goal_substitution: float = 0.02

    # Confidence detection
    overconfident_residual: float = 0.7  # R_confidence when ungrounded


@dataclass(frozen=True)
class DriftInfluenceConfig:
    """
    Drift Influence parameters.

    Source: agency/drift_influence.py
    """
    # Influence bounds
    influence_min: float = 0.8          # Worst-case drift influence floor
    influence_max: float = 1.0          # Zero drift produces exactly this

    # Decay parameters
    decay_rate_base: float = 0.05       # Base decay per tick (no violations)
    decay_rate_recovery: float = 0.10   # Accelerated decay (grounding improves)
    decay_minimum: float = 0.0          # Drift decays toward this

    # Influence calculation factors
    exploration_bias_factor: float = 0.5      # magnitude * this
    deliberation_weight_reduction: float = 0.1  # 1.0 - this * magnitude


# ============================================================================
# ETHOS SYSTEM
# ============================================================================

@dataclass(frozen=True)
class EthosConfig:
    """
    Ethos System parameters.

    Source: ethos/ethos_system.py
    """
    # Axis weights for phi_t
    w_valence: float = 0.35
    w_drive: float = 0.35
    w_stability: float = 0.30

    # Phi bounds
    phi_floor: float = 0.05
    phi_ceiling: float = 0.85
    phi_max_pb: float = 0.85     # Phase B phi maximum
    phi_base_pb: float = 0.10    # Phase B base phi
    phi_clip_max: float = 0.55   # CLIP mode cap for phi

    # Phase B policy weights
    alpha_U: float = 0.45        # Valence weight in Phase B
    alpha_R: float = 0.55        # Drive weight in Phase B
    alpha_T: float = 0.35        # Stability weight in Phase B

    # Weight initialization
    w_init: Tuple[float, float, float] = (0.34, 0.33, 0.33)
    eta: Tuple[float, float, float] = (0.01, 0.01, 0.01)  # Learning rates
    w_min: float = 0.15          # Minimum axis weight
    w_max: float = 0.70          # Maximum axis weight
    delta_w_max: float = 0.02    # Max weight change per step

    # Drift threshold
    theta_phi_drift: float = 0.40

    # Smoothing
    phi_smoothing_alpha: float = 0.45  # EMA smoothing on phi_t output

    # Fallback
    fallback_clip_threshold: float = 0.80  # Fraction triggering CLIP fallback


# ============================================================================
# POLICY / GUARD
# ============================================================================

@dataclass(frozen=True)
class PolicyGuardConfig:
    """
    Policy Guard parameters.

    Source: policy/policy_guard.py
    """
    # Thresholds
    high_frag: float = 1.00             # High fragmentation threshold
    high_overload: float = 1.00         # High overload threshold
    low_health: float = 0.15            # Low health threshold
    boot_ticks: int = 80                # Boot window duration

    # Emergency thresholds
    emergency_frag_threshold: float = 1.10
    emergency_overload_threshold: float = 1.05
    osc_unstable: float = 0.60          # Oscillation instability threshold
    e_ratio_overload: float = 0.85      # Energy ratio overload threshold

    # LLM access thresholds
    min_stability_for_llm: float = 0.25
    min_health_for_llm: float = 0.20

    # Sandbox mode
    sandbox_damping: float = 0.35       # Sandbox phi damping factor
    sandbox_min_dwell_ticks: int = 8
    sandbox_exit_stability_margin: float = 0.05
    sandbox_exit_overload_margin: float = 0.20

    # Stillness mode
    stillness_min_dwell_ticks: int = 6
    stillness_exit_health_margin: float = 0.05
    stillness_exit_stability_margin: float = 0.05

    # Normal mode
    normal_min_dwell_ticks: int = 4


# ============================================================================
# SUPERVISOR / CURRICULUM
# ============================================================================

@dataclass(frozen=True)
class SupervisorConfig:
    """
    Supervisor and Curriculum parameters.

    Source: registry/config_registry.py (SupervisorConfig section)
    """
    # Kappa statistics
    kappa_s_window: int = 64            # Window for structural statistics
    stability_horizon: int = 10         # Stability prediction horizon

    # Belief decay
    regime_forget: float = 0.1          # Regime belief decay
    stability_forget: float = 0.05      # Stability belief decay

    # Thresholds
    stability_threshold: float = 0.7
    tier_e_stability_threshold: float = 0.85

    # Override settings
    override_max_ticks: int = 5
    override_cooldown: int = 3
    override_cooldown_min: int = 1
    override_cooldown_max: int = 10

    # Tier E
    tier_e_stability_ticks: int = 10
    stillness_release_ticks: int = 3
    stillness_release_threshold: float = 0.05

    # S-equilibrium
    s_equilibrium_instability_threshold: float = 0.5
    s_equilibrium_tier_e_threshold: float = 0.35
    s_equilibrium_regime_weight: float = 0.1
    s_equilibrium_energy_weight: float = 0.2
    s_equilibrium_kappa_weight: float = 0.7  # CRITICAL: kappa dominance

    # Detection thresholds
    oscillation_threshold: float = 0.25
    churn_threshold: float = 0.1

    # Token budgets
    stillness_tokens: int = 0
    reflect_tokens: int = 512
    act_tokens: int = 4096
    tier_e_token_cap: int = 4096

    # Kappa S normalization
    kappa_s_epsilon: float = 1e-6
    kappa_s_norm_alpha: float = 0.2
    kappa_s_norm_min: float = 0.0
    kappa_s_norm_max: float = 5.0

    # Belief system
    belief_update_alpha: float = 0.2
    belief_floor: float = 0.0
    belief_ceiling: float = 1.0
    belief_update_interval: int = 20
    threshold_adapt_alpha: float = 0.1

    # Threshold ranges
    stability_threshold_min: float = 0.5
    stability_threshold_max: float = 0.9
    churn_threshold_min: float = 0.05
    churn_threshold_max: float = 0.2
    oscillation_threshold_min: float = 0.15
    oscillation_threshold_max: float = 0.4
    stillness_release_threshold_min: float = 0.01
    stillness_release_threshold_max: float = 0.1

    # Belief memory
    belief_memory_size: int = 64
    belief_attribution_window: int = 10
    belief_outcome_delay: int = 5
    belief_attribution_decay: float = 0.1

    # Authority
    authority_coherence_min: float = 0.25


# ============================================================================
# LLM INTEGRATION
# ============================================================================

@dataclass(frozen=True)
class LLMIntegrationConfig:
    """
    LLM Integration parameters.

    Source: integration/orchestrator.py, openai_client.py, ollama_client.py
    """
    # Response parsing
    json_prefix: str = "JSON="
    max_len_out: int = 400000           # Max output length (400KB)
    max_memory_items: int = 8           # Max memory context items
    max_retries: int = 2                # Max retry count

    # OpenAI defaults
    openai_timeout: float = 120.0       # Request timeout
    openai_max_tokens: int = 4096       # Max output tokens

    # Ollama defaults
    ollama_timeout: float = 60.0
    ollama_temperature: float = 0.7
    ollama_n_predict: int = 256


# ============================================================================
# COUPLING
# ============================================================================

@dataclass(frozen=True)
class CouplingConfig:
    """
    Coupling and Handshake parameters.

    Source: coupling/handshake_controller.py, coupling_state_machine.py
    """
    # Guard score
    min_guard_score: float = 0.60

    # Deliberation defaults
    num_candidates: int = 8
    max_deliberation_rounds: int = 3
    revise_top_n: int = 3
    easy_thresh: float = 0.85

    # State machine
    max_scale_drop: float = 0.2         # Minimum scale in REFLECT
    pred_weight: float = 0.7            # Prediction vs health weight
    kappa_scale_factor: float = 0.5     # Kappa-specific scale multiplier


# ============================================================================
# GOVERNANCE (Tom↔LLM coupling contract)
# ============================================================================

@dataclass(frozen=True)
class GovernanceConfig:
    """
    Governance contract configuration.

    Source: coupling/governance/tom_governance.py
    """
    # Master gate — entire governance layer.
    enable_governance_contract: bool = True

    # Phase 2 — compact governance brief replaces metrics dump in prompt.
    enable_governance_brief: bool = True

    # Phase 3 — post-LLM move validation against admissible moves.
    enable_move_validation: bool = True

    # Phase 4 — mode-driven turn policy (dynamic prompt directives).
    enable_turn_policy: bool = True

    # Phase 5 — episode persistence (cross-turn problem state).
    enable_episode_persistence: bool = True


# ============================================================================
# MEMORY / RGM
# ============================================================================

@dataclass(frozen=True)
class MemoryConfig:
    """
    Memory and Learning parameters.

    Source: memory/learning_memory.py, config_registry.py
    """
    # Stability history
    stability_history_capacity: int = 50
    learning_memory_capacity: int = 200

    # Caps
    cooldown_bias_cap: float = 0.2
    guard_threshold_bias_cap: float = 0.15
    initiative_damping_cap: float = 0.1

    # Storage policy (M5/zero-copy)
    default_storage_policy: str = "zero_copy_strict"
    allow_summary_in_content_for_embedding: bool = False


@dataclass(frozen=True)
class ActionLearningConfig:
    """Config for selective learning from agent action outcomes."""
    enabled: bool = True                    # ON — learn from agent action outcomes
    min_confidence: float = 0.6             # Minimum quality score to persist
    min_consistency: int = 2                # Require N consistent outcomes before persisting failures
    max_records_per_session: int = 20       # Cap per session
    max_store_size: int = 500               # Total cap per tenant
    retrieval_weight: float = 0.3           # RRF weight for action outcomes
    retrieval_max_items: int = 3            # Cap in retrieval results
    success_strength: float = 0.7           # Memory strength for successes
    failure_strength: float = 0.4           # Memory strength for failures
    store_ttl_days: int = 90                # Retrieval-side TTL


@dataclass(frozen=True)
class RGMEnhancementConfig:
    """
    RGM Enhancement parameters.

    Source: registry/config_registry.py (RGMEnhancementConfig)
    """
    # Resilience reinforcement
    reinforcement_eta: float = 0.1
    reinforcement_r_avg: float = 0.5

    # Pruning
    prune_period_ticks: int = 50
    prune_entropy_surge_threshold: float = 0.8
    prune_stability_recovery_threshold: float = 0.7
    prune_saturation_threshold: float = 0.9

    # Pruning weights
    prune_weight_alpha: float = 0.4     # Anchor strength weight
    prune_weight_access: float = 0.2    # Access count weight
    prune_weight_freshness: float = 0.2
    prune_weight_coherence: float = 0.1
    prune_weight_stability: float = 0.1

    # Audit
    audit_period_ticks: int = 100


# ============================================================================
# CONTEXT / TOKEN MANAGEMENT
# ============================================================================

@dataclass(frozen=True)
class ContextConfig:
    """
    Context and Token Management parameters.

    Source: integration/budget_manager.py, context_manager.py, compactor.py
    """
    # Token caps
    hard_cap_tokens: int = 128000
    soft_cap_tokens: int = 100000
    reserve_tokens: int = 16000

    # Compaction
    compaction_threshold: float = 0.8
    never_compact_last_n: int = 3
    max_summary_ratio: float = 0.3
    min_block_tokens_to_compact: int = 100
    confidence_threshold: float = 0.7

    # Memory anchors
    max_memory_anchors: int = 8
    min_memory_anchors: int = 2


# ============================================================================
# AGENCY DYNAMICS
# ============================================================================

@dataclass(frozen=True)
class AgencyDynamicsConfig:
    """
    Agency Dynamics parameters.

    Source: agency/dynamics.py, agency_controller.py
    """
    # Uncertainty
    uncertainty_gain: float = 1.0
    smooth_alpha: float = 0.15

    # Weights
    ethos_weight: float = 0.6
    health_weight: float = 0.3
    risk_weight: float = 0.5
    max_effect_factor: float = 0.1      # Max base delta effect (10% of base)


# ============================================================================
# TOOL GATING
# ============================================================================

@dataclass(frozen=True)
class ToolGatingConfig:
    """
    Phi-based tool gating thresholds.

    Controls the phi levels at which each tool tier becomes available.
    Used by agency/tool_gating.py to determine which tools the agent can access.

    Source: agency/tool_gating.py
    """
    observe_threshold: float = 0.0      # Phi threshold for observe tier (no tools)
    read_threshold: float = 0.2         # Phi threshold for read tier
    write_threshold: float = 0.4        # Phi threshold for write tier
    execute_threshold: float = 0.6      # Phi threshold for execute tier


# ============================================================================
# INITIATIVE PULSE (Phase 10)
# ============================================================================

@dataclass(frozen=True)
class InitiativePulseConfig:
    """
    Initiative Pulse parameters (Phase 10).

    Source: registry/config_registry.py (InitiativePulseConfig)
    """
    phi_baseline: float = 0.1
    pulse_alpha: float = 0.35
    pulse_delta_max: float = 0.05
    pulse_delta_max_stressed: float = 0.03
    decay_rate: float = 0.02            # Phi decay per tick
    decay_stillness_multiplier: float = 2.0
    decay_instability_multiplier: float = 1.5
    theta_phi_pulse: float = 0.35


# ============================================================================
# WARMUP
# ============================================================================

@dataclass(frozen=True)
class WarmupConfig:
    """
    Warmup and Initialization parameters.

    Source: controller/tom_controller.py
    """
    min_tick: int = 2000                # Min tick before warmup complete
    balance_tolerance: float = 0.05     # Rotation balance tolerance
    balanced_ticks_required: int = 5    # Min balanced ticks for warmup
    rotation_step: float = 2.39996323   # Golden angle in radians


# ============================================================================
# INTERFACE
# ============================================================================

@dataclass(frozen=True)
class InterfaceConfig:
    """
    Interface parameters.

    Source: interface/tom_voice.py, chat_adapter.py
    """
    # Health score thresholds
    health_threshold_excellent: float = 0.7
    health_threshold_good: float = 0.5
    health_threshold_fair: float = 0.35
    health_threshold_poor: float = 0.2

    # Stability thresholds
    stability_threshold_high: float = 0.7
    stability_threshold_medium: float = 0.5
    stability_threshold_low: float = 0.35

    # Activation
    activation_sigma_multiplier: float = 2.0

    # SLO
    slo_exceedance_threshold: float = 0.05


# ============================================================================
# EVIDENCE
# ============================================================================

@dataclass(frozen=True)
class EvidenceConfig:
    """
    Evidence parameters.

    Source: controller/tom_controller.py
    """
    max_spans: int = 8
    max_writes_per_tick: int = 12
    context_max_tokens: int = 2200
    semantic_target_quant_decimals: int = 1


# ============================================================================
# SUITE RUNNER (Phase 3 Hardening)
# ============================================================================

@dataclass(frozen=True)
class SuiteRunnerConfig:
    """
    Suite runner hardening parameters.

    Controls timeouts and guardrails for subprocess-based test suite runners
    (mem-suite, system-suite). Added in Phase 3 suite completeness work.

    Source: commands.py subprocess.run calls
    """
    # Subprocess timeout (seconds) - prevents indefinite hangs
    subprocess_timeout_seconds: int = 300

    # Max ticks per suite run - prevents runaway loops
    max_ticks_per_suite: int = 1000

    # Fail-fast mode - stop on first failure
    fail_fast: bool = True

    # Memory limit (MB) - informational, not enforced by Python
    max_memory_mb: int = 4096

    # Graceful shutdown timeout (seconds)
    shutdown_timeout_seconds: int = 30


# ============================================================================
# ENERGY FEEDBACK
# ============================================================================

@dataclass(frozen=True)
class EnergyFeedbackConfig:
    """
    Energy Feedback parameters.

    Controls how agentic loop energy signals modulate SICD tree physics
    (leaf growth and decay rates). Disabled by default.

    Source: agency/energy_feedback.py, agency/mechanics/sicd_kappa_update.py
    """
    # Leaf growth multiplier gain: leaf_growth_rate *= (1 + energy * energy_leaf_gain)
    energy_leaf_gain: float = 0.3

    # Leaf decay multiplier gain: leaf_decay_rate *= (1 + abs(energy) * energy_decay_gain)
    energy_decay_gain: float = 0.2

    # Kappa penalty scaling (reserved for future use)
    energy_kappa_penalty: float = 0.01

    # Master gate — ON, energy feedback active
    enabled: bool = True


# ============================================================================
# NOURISHMENT VALUATION
# ============================================================================

@dataclass(frozen=True)
class NourishmentValuationConfig:
    """
    Nourishment Valuation — Ip/Ie reward system.

    Telemetry always computes D/Ip/q/Ie on scoreable turns;
    nourishment modulation and phi_t uplift gated by enabled flag.

    Source: integrity/nourishment_valuation.py
    Integration: controller/tom_controller.py, agency/agency_controller.py
    """
    # Master gate — ON, nourishment valuation active
    enabled: bool = True

    # Ip deposit scaling: Ip = k_p * D
    k_p: float = 0.10

    # phi_t uplift: phi_t += k_phi * D (before dynamics, per-tick non-accumulating)
    k_phi: float = 0.02

    # Nourishment gain from Ie: nourishment += k_e * Ie
    k_e: float = 0.15

    # Quality conversion bounds: q = clamp(1 + delta_E, q_min, q_max)
    q_min: float = 0.2
    q_max: float = 1.5     # Matches delta_E range: max 1+0.5=1.5

    # D_estimate component weights (should sum to 1.0)
    w_intent: float = 0.4
    w_effort: float = 0.3
    w_outcome: float = 0.3


# ============================================================================
# SHADOW REWARD
# ============================================================================

@dataclass(frozen=True)
class ShadowRewardConfig:
    """Shadow reward system — potential-based R_total.

    Telemetry always available; nourishment modulation gated by enabled flag.
    Shadow mode: R_total logged per tick, no control wiring.

    Source: telemetry/reward_signal.py
    Integration: controller/tom_controller.py
    """
    # Master gate — ON, reward signal active
    enabled: bool = True

    # Per-tick reward cap
    rmax: float = 0.1

    # Axis weights (must sum to 1.0 ± 0.01, all non-negative)
    w_homeostasis: float = 0.4
    w_cohesion: float = 0.35
    w_hunt: float = 0.25

    # Hunt axis tuning
    hunt_staleness_cap: int = 20
    hunt_count_cap: int = 5

    # Felt coupling — wires R_total into nourishment_raw
    felt_coupling_enabled: bool = True    # ON — wires R_total into nourishment_raw
    felt_k_r: float = 0.03               # Gain: nourishment_raw += k_r * R_total
    felt_clamp_max: float = 0.03         # Per-tick clamp: ±0.03 max contribution

    def __post_init__(self) -> None:
        w_sum = self.w_homeostasis + self.w_cohesion + self.w_hunt
        if abs(w_sum - 1.0) > 0.01:
            raise ValueError(
                f"Axis weights must sum to 1.0 (got {w_sum:.4f}): "
                f"homeo={self.w_homeostasis}, cohesion={self.w_cohesion}, "
                f"hunt={self.w_hunt}"
            )
        for name, val in [("w_homeostasis", self.w_homeostasis),
                          ("w_cohesion", self.w_cohesion),
                          ("w_hunt", self.w_hunt),
                          ("rmax", self.rmax),
                          ("felt_k_r", self.felt_k_r),
                          ("felt_clamp_max", self.felt_clamp_max)]:
            if val < 0:
                raise ValueError(f"{name} must be non-negative (got {val})")


@dataclass(frozen=True)
class HungerDriveConfig:
    """Hunger signal feeds into agency controller drive(t) → phi_t uplift."""
    enabled: bool = True               # ON — hunger signal computation + phi_t uplift
    phi_effort_enabled: bool = True    # ON — φ → deliberation effort modulation
    w_reserve: float = 0.50            # Weight: structural resource scarcity
    w_staleness: float = 0.30          # Weight: mean goal age (normalized)
    w_pressure: float = 0.20           # Weight: active goal count / max
    phi_uplift_gain: float = 0.15      # Gain: phi_t += gain * H_ema (max ~0.15 uplift)
    ema_alpha: float = 0.30            # EMA smoothing for H (prevents runaway)

    def __post_init__(self) -> None:
        w_sum = self.w_reserve + self.w_staleness + self.w_pressure
        if abs(w_sum - 1.0) > 0.01:
            raise ValueError(f"Hunger weights must sum to 1.0 (got {w_sum})")
        for name, val in [("w_reserve", self.w_reserve),
                          ("w_staleness", self.w_staleness),
                          ("w_pressure", self.w_pressure),
                          ("phi_uplift_gain", self.phi_uplift_gain),
                          ("ema_alpha", self.ema_alpha)]:
            if val < 0:
                raise ValueError(f"{name} must be non-negative (got {val})")


@dataclass(frozen=True)
class AutonomicCouplingConfig:
    """Loop 3: Autonomic coupling — feelings modulate SICD mechanical parameters.

    Single authoritative definition. Imported by agency/mechanics/autonomic_coupling.py.
    """
    enabled: bool = True               # Gate: autonomic modulation (TOM_AUTONOMIC_ENABLED)
    tension_spawn_gain: float = 0.3    # M1: tension → spawn credit suppression
    fatigue_growth_gain: float = 0.25  # M2: fatigue → leaf growth suppression
    vitality_floor_gain: float = 0.04  # M3: vitality_sense → spawn floor boost
    groundedness_balance_gain: float = 0.5  # M4: groundedness → leaf-balance correction
    clarity_band_gain: float = 0.2     # M5: clarity → sigma band width

    def __post_init__(self) -> None:
        for name, val in [("tension_spawn_gain", self.tension_spawn_gain),
                          ("fatigue_growth_gain", self.fatigue_growth_gain),
                          ("vitality_floor_gain", self.vitality_floor_gain),
                          ("groundedness_balance_gain", self.groundedness_balance_gain),
                          ("clarity_band_gain", self.clarity_band_gain)]:
            if val < 0:
                raise ValueError(f"{name} must be non-negative (got {val})")


@dataclass(frozen=True)
class VectorVoiceConfig:
    """
    Vector-based state response configuration.

    Controls the deterministic x→y→text pipeline for state/status queries.
    """
    enabled: bool = True        # Feature flag (TOM_VECTOR_VOICE_ENABLED)
    ema_alpha: float = 0.3      # EMA smoothing factor (1.0 = no smoothing)


@dataclass(frozen=True)
class RealisationConfig:
    """
    MR → natural language realiser configuration.

    Controls the LLM surface realiser for vector voice state responses.
    If provider is empty, falls back to the main TOM LLM.
    """
    provider: str = ""           # "" = use main TOM LLM (TOM_REALISER_PROVIDER)
    model: str = ""              # TOM_REALISER_MODEL
    api_key: str = ""            # TOM_REALISER_API_KEY
    base_url: str = ""           # TOM_REALISER_BASE_URL
    temperature: float = 0.7     # TOM_REALISER_TEMPERATURE
    max_tokens: int = 1024       # TOM_REALISER_MAX_TOKENS (includes reasoning tokens for gpt-5-mini)
    timeout_s: float = 30.0      # TOM_REALISER_TIMEOUT_S
    realise_greetings: bool = False  # TOM_REALISER_GREETINGS


@dataclass(frozen=True)
class AgentLLMConfig:
    """
    Agent/tool-use LLM configuration (separate from main conversation LLM).

    When provider is empty, falls back to the main TOM LLM (TOM_LLM_*).
    This allows configuring a different model for agent work (web search,
    file ops, tool calling) vs the conversational/cognitive pipeline.
    """
    provider: str = ""           # "" = use main TOM LLM (TOM_AGENT_LLM_PROVIDER)
    model: str = ""              # TOM_AGENT_LLM_MODEL
    api_key: str = ""            # TOM_AGENT_LLM_API_KEY
    base_url: str = ""           # TOM_AGENT_LLM_BASE_URL
    temperature: float = 0.7     # TOM_AGENT_LLM_TEMPERATURE
    max_tokens: int = 4096       # TOM_AGENT_LLM_MAX_TOKENS
    timeout_s: float = 120.0     # TOM_AGENT_LLM_TIMEOUT_S


# ============================================================================
# DOCUMENT INGESTION
# ============================================================================

@dataclass(frozen=True)
class DocIngestConfig:
    """
    Document Ingestion parameters.

    Controls file size limits, scan limits, and anchor limits for
    document ingestion via chat attachment and knowledge folder scanning.

    Source: interface/doc_ingest.py
    """
    max_file_size_bytes: int = 10 * 1024 * 1024  # 10MB default
    max_files_per_scan: int = 500                  # Max files in a single folder scan
    max_anchors_per_doc: int = 50                  # Max memory anchors per document


# ============================================================================
# FINITE GEOMETRY RETRIEVER (FGR)
# ============================================================================

@dataclass(frozen=True)
class FgrConfig:
    """
    Finite Geometry Retriever parameters.

    Controls the covering-design-based post-retrieval selection layer
    that maximizes concept coverage using Cushing-Stewart decomposition.

    Source: memory/finite_geometry_retrieval.py
    """
    enabled: bool = True                    # Feature gate (TOM_FGR_ENABLED)
    pool_per_source: int = 15               # Candidates per retrieval source (BM25, vector)
    axis_balance: bool = True               # Enable L/S/T axis partitioning
    latency_budget_ms: int = 50             # Max FGR processing time before fallback (ms)
    channel_weights: str = "1.0,1.5,1.2"    # Hash, DSI, SEI concept channel weights
    adaptive_k: bool = True                 # Auto-scale K based on memory store size
    k_base: int = 5                         # Minimum chunks to select
    k_max: int = 12                         # Maximum chunks (token budget cap)
    k_scale_threshold: int = 50             # Dataset size at which scaling begins


# ============================================================================
# ENERGY FALLBACK POLICY
# ============================================================================

@dataclass(frozen=True)
class EnergyFallbackConfig:
    """
    Energy fallback policy: graceful intensity decay when LLM loads unavailable.

    When _safe_fallback() fires (guard block or schema parse fail), intensity
    decays exponentially from last valid LLM value toward a mode-specific
    baseline, rather than dropping to zero instantly.

    Source: controller/tom_controller.py (_apply_intensity_fallback)
    Policy: Draft v1.0, approved for implementation.
    """
    enabled: bool = True
    decay_rate: float = 0.15              # ~5 tick half-life (ln2/0.15 ≈ 4.6)
    baseline_default: float = 0.15        # conservative floor
    # Supervisor modes (state_types.SupervisorMode)
    #
    # POLICY NOTE: General fallback floor is 0.15–0.20 (Draft v1.0 §5).
    # STILLNESS and EMERGENCY are intentional safety carve-outs below this range.
    # Do not "normalize" these to 0.15 without policy review.
    baseline_stillness: float = 0.05      # SAFETY EXCEPTION — danger_evidence lockdown
    baseline_reflect: float = 0.15        # calm deliberation
    baseline_act: float = 0.20            # active execution
    # Global modes (state_types.GlobalMode)
    baseline_normal: float = 0.15         # moderate
    baseline_sandbox: float = 0.10        # SAFETY EXCEPTION — restricted operation
    baseline_reflection: float = 0.15     # same as reflect
    baseline_emergency: float = 0.05      # SAFETY EXCEPTION — critical instability

    def __post_init__(self):
        if self.decay_rate <= 0:
            raise ValueError(
                f"energy_fallback.decay_rate must be > 0, got {self.decay_rate}"
            )
        for fname in self.__dataclass_fields__:
            if fname.startswith("baseline_"):
                val = getattr(self, fname)
                if not (0.0 <= val <= 1.0):
                    raise ValueError(
                        f"energy_fallback.{fname} must be in [0, 1], got {val}"
                    )


# ============================================================================
# TOP-LEVEL CONTAINER
# ============================================================================

@dataclass(frozen=True)
class AudioSalienceConfig:
    """
    Audio salience input pipeline configuration.

    Sound as structural load on the tree.
    Source: tom_audio/audio/ (registry, wind, resource_guard)
    """
    provider: str = "stub"
    wind_gain: float = 0.2
    rate_limit_per_min: int = 60
    max_duration_s: float = 30.0
    compute_budget_s: float = 1.0


@dataclass(frozen=True)
class TTSConfig:
    """
    TTS output pipeline configuration — temporary Stage 1 bridge.

    The tree speaks through LLM text shaped by coupling brief.
    Stage 1 TTS voices that text with a register-to-speed bridge.
    This is a temporary seam — Stage 2 structural prosody will replace it.

    Source: tom_audio/tts/ (registry, register_bridge)
    """
    provider: str = "stub"       # "stub" | "kokoro"
    voice: str = "af_heart"      # Kokoro voice preset name
    enabled: bool = True         # ON — TTS active


@dataclass(frozen=True)
class StructuralAudioConfig:
    """
    Structural composition engine — tree state → sound.

    The tree IS the instrument. Structural metrics (sigma, kappa, axis balance)
    map to sonic parameters (pitch, timbre, dynamics).

    Source: tom_audio/composition/
    """
    enabled: bool = True                   # ON — structural audio active
    tone_duration_s: float = 2.5           # Duration of structural tone
    soothe_tension_threshold: float = 0.6  # FeelingVector.tension threshold for self-soothe
    soothe_cooldown_ticks: int = 3         # Minimum ticks between self-soothe events
    soothe_gain: float = 0.15              # Amplitude of calming tone (low to prevent runaway)
    audio_memory_enabled: bool = True      # Store audio traces as MemoryRecords


@dataclass(frozen=True)
class WordExcitationConfig:
    """
    Word-level excitation configuration — shadow production integration.

    Per-word identity enters the SICD engine through semantic_excitation.
    The excitation map (pre-computed from embeddings via PCA) gives each
    known word a unique 3D perturbation vector.

    Provisional combiner: uniform average of per-word perturbations.
    Adequate for shadow integration (observational only), not the
    long-term semantic aggregation rule.

    Source: agency/excitation/
    """
    enabled: bool = False           # OFF — superseded by FeelingWheelConfig
    shadow_only: bool = True        # Shadow only (inactive — feeling wheel is the live path)
                                    # False = return word-level excitation (live mode)
    gain: float = 0.02              # from F+++ (2% perturbation)
    map_path: str = ""              # empty = bundled default at agency/excitation/data/
    shadow_logging: bool = True     # log shadow comparison


@dataclass(frozen=True)
class FeelingWheelConfig:
    """
    Feeling wheel configuration — category-based excitation.

    Replaces 1000 exact-match words with ~100-150 feeling categories.
    Categories are structural load types with driver/axis weights.

    Source: agency/excitation/feeling_wheel_*.py
    Spec: docs/contracts/feeling_wheel_spec.md
    """
    enabled: bool = True            # ON — feeling wheel active
    shadow_only: bool = False       # LIVE — category excitation drives the tree
    gain: float = 0.02              # perturbation scale
    map_path: str = ""              # empty = bundled default at agency/excitation/data/


class ScaffoldAuthorityLevel:
    """Authority levels for hierarchical scaffold promotion."""
    SHADOW = 0
    SOFT_LEGALITY = 1
    SOFT_FAMILY = 2
    BOUNDED_OVERRIDE = 3
    FULL = 4


@dataclass(frozen=True)
class ScaffoldConfig:
    """Hierarchical scaffold configuration."""
    authority_level: int = 1
    carrier_t_freq: float = 1.0 / 12.0
    carrier_s_freq: float = 1.0 / 8.0
    plasticity_enabled: bool = True


@dataclass(frozen=True)
class OrganismRewardConfig:
    """Organism layer — homeostatic objective + graded reward coefficients.

    Defines the weights for J = w_V V + w_R R + w_O O − w_D D − w_E E,
    plus the per-driver reward coefficients (α, γ, λ, μ, ρ) used by
    agency.organism.reward.compute_* functions, plus the normalisation
    constants used by agency.organism.extractor.extract_* functions.

    Initial values are a defensible starting point but NOT tuned — the
    weights and coefficients shape the tree's "personality" (what it
    prioritises) and are expected to be revised once telemetry data
    from the Phase A sandbox diagnostic is reviewed.

    Phase A uses this config for telemetry-only. Phase B additions
    (forward model, selector) consume the same config. No separate
    Phase B config planned.
    """

    # -- Objective J weights -------------------------------------------
    # J = w_V·V + w_R·R + w_O·O − w_D·D − w_E·E
    weight_viability: float = 1.0          # health is the primary dimension
    weight_reserve: float = 0.5            # reserve matters half as much as V
    weight_opportunity: float = 0.3        # opportunity subordinate to survival
    weight_damage: float = 1.0             # damage cost equal to viability gain
    weight_threat_exposure: float = 1.5    # active threat weighted ABOVE damage
                                           # (unresolved threat predicts future loss
                                           # in R, O via cross-coupling, so higher weight)

    # -- Threat reward coefficients ------------------------------------
    # R_threat = α_E·ΔE_reduction + β·avoided_damage + γ_V·ΔV − λ·C − μ·X
    threat_alpha_E: float = 1.0            # reward for reducing E
    threat_beta_avoided_damage: float = 1.0  # Phase B: forward-model counterfactual
    threat_gamma_V: float = 0.5            # reward for preserving/restoring V
    threat_lambda_cost: float = 0.1        # action cost penalty
    threat_mu_collateral: float = 0.2      # collateral-harm penalty

    # -- Sustenance reward coefficients --------------------------------
    # R_sust = α_R·ΔR + γ_V·ΔV − λ·C − μ·waste − ρ_D·ΔD[if R↑]
    #
    # NOTE: β_repair DELETED in option-1 extractor rework (2026-04-24).
    # D is now a ratchet counter (extract_D uses kappa_min_ever), so
    # D_prev − D_cur ≤ 0 always — nourishment cannot earn "damage
    # repair" reward. The ρ_D cross-coupling still works to penalise
    # damage RISE coincident with R gain; the old β_repair term that
    # paid for damage recovery is gone because recovery is not a thing
    # under ratchet semantics. If the organism eventually needs to
    # model healing, switch extractor to the EMA-D variant (option a
    # in the architecture contract §Open issues).
    sustenance_alpha_R: float = 1.0        # reward for replenishment
    sustenance_gamma_V: float = 0.5        # reward for viability restoration
    sustenance_lambda_cost: float = 0.1    # uptake cost
    sustenance_mu_waste: float = 0.2       # spoilage / waste
    sustenance_rho_D_excess: float = 0.5   # penalise damage rise coincident with R gain

    # -- Procreation reward coefficients -------------------------------
    # R_proc = α_O·ΔO + β·persistence + γ_V·ΔV − λ·C − μ·pruning
    #        − ρ_E·ΔE[if O↑] − ρ_D·ΔD[if O↑]
    procreation_alpha_O: float = 1.0       # reward for opportunity gain
    procreation_beta_persistence: float = 0.5  # Phase B: multi-tick persistence
    procreation_gamma_V: float = 0.3       # viability gain from bandwidth
    procreation_lambda_cost: float = 0.1   # resource cost of extending
    procreation_mu_pruning: float = 0.3    # overreach / pruning waste
    procreation_rho_E_excess: float = 0.5  # penalise threat rise from growth
    procreation_rho_D_excess: float = 0.5  # penalise damage rise from growth

    # -- Normalisation constants (extractor) ---------------------------
    # Thresholds used by agency.organism.extractor to map raw engine
    # mechanics into the [0, 1] normalised state variables.
    kappa_health_floor: float = 0.5        # Branches below this are "damaged".
                                           # Used by extract_D (ratchet deficit
                                           # reference) and extract_R fallback
                                           # (kappa-headroom proxy).
    sigma_baseline: float = 0.01           # Retained for backward-compat / future
                                           # EMA-E variant; NOT currently used by
                                           # extract_E after the option-1 rework
                                           # (2026-04-24), which is count-based.
    sigma_ceiling: float = 1.0             # Retained for the same reason; count-
                                           # based E does not use the ceiling.
                                           # May still be consumed by rollout /
                                           # other subsystems.
    sigma_alarm_threshold: float = 0.8     # Branches with sigma_ema above this
                                           # are "in alarm state". E = fraction
                                           # of branches in alarm. Empirically
                                           # calibrated — under balanced load on
                                           # a warmed tree ~20% exceed this, so
                                           # baseline E ≈ 0.20 with stress
                                           # pushing it upward.
    spawn_credit_cap: float = 1000.0       # O = 1.0 when spawn_credit = cap.
                                           # Matches TOM_SPAWN_SOFT_CAP scale
                                           # for 2k-20k tier; 50k tier uses
                                           # larger caps (revisit for scale).

    # -- Phase B niche-persistence shadow flags ------------------------
    # Per docs/contracts/organism_specialist_energy_lifecycle_spec.md §3.3.
    # Both flags default OFF and are intentionally separated so that
    # state-population (additive shadow telemetry) and the kappa-update
    # plasticity scaling (live mechanics change) are gated independently.
    #
    # Mechanics-output bit-identical invariant: when BOTH flags are
    # OFF, the engine's mechanics-output (sigma_ema, kappa,
    # sweet_counter, etc.) is byte-equivalent to the
    # 216c4e42 / 0103cc11 / d84965e7 baseline, and the new BranchState
    # niche fields stay at their declared defaults. Old pre-Phase-B
    # pickles remain default-compatible — the four added fields
    # deserialise to their declared defaults via dataclass
    # default-on-absence. (The pickle byte stream is NOT claimed
    # byte-identical to the pre-Phase-B schema; the schema has changed
    # by addition.)
    enable_niche_state_observation: bool = True   # PRODUCTION ON (2026-06-17, Ken-approved): specialist
                                                    # persistence per docs/contracts/specialist_persistence_validation.md
                                                    # (VALIDATED 2026-04-30, ship mode G). Was False; now populating the new
                                                    # BranchState niche fields
                                                    # (locked_niche,
                                                    # driver_exposure_ema,
                                                    # niche_lock_tick,
                                                    # niche_lock_confidence)
                                                    # as additive shadow
                                                    # telemetry. When OFF the
                                                    # fields stay at their
                                                    # declared defaults.
    enable_niche_hysteresis: bool = True            # PRODUCTION ON (2026-06-17, Ken-approved): mode G,
                                                    # scale 0.10 (specialist_persistence_validation.md). Was False. Gate the path-2
                                                    # kappa-update plasticity
                                                    # scaling at §4 of the
                                                    # organism Phase B spec.
                                                    # When ON (separate
                                                    # explicit Ken approval),
                                                    # the per-branch
                                                    # plasticity_scale
                                                    # multiplier fires on
                                                    # kappa decay / recovery.
                                                    # Presupposes
                                                    # enable_niche_state_observation
                                                    # is also ON; engine.step
                                                    # raises RuntimeError when
                                                    # hysteresis is ON without
                                                    # observation (fail-closed).
    # Slice 5 numerical knobs. Defaults match the validated values from
    # docs/contracts/specialist_persistence_validation.md §3.6 sweep.
    # Only consulted when the corresponding flag is ON.
    niche_hysteresis_scale: float = 0.10            # Plasticity multiplier
                                                    # for kappa decay/recovery
                                                    # on branches whose
                                                    # locked_niche != incoming
                                                    # niche. Range [0, 1];
                                                    # 0.10 per validated Phase B
                                                    # hysteresis sweep.
    niche_lock_threshold: float = 0.45              # max(driver_exposure_ema)
                                                    # required to first lock a
                                                    # niche. Above this, the
                                                    # branch's niche identity
                                                    # crystallises.
    niche_exposure_ema_alpha: float = 0.30          # Learning rate for the
                                                    # per-branch driver
                                                    # exposure EMA when
                                                    # observation is ON.

    # -- Control-law parameters (Ken review 2026-04-24) ----------------
    # The selector previously ranked on (ΔJ − reversibility_penalty) alone,
    # leaving the per-driver rewards (R_T, R_S, R_P) as post-hoc telemetry
    # rather than drivers of decision. The driver-weighted composite makes
    # them load-bearing:
    #
    #   score(a) = (T·R_T + S·R_S + P·R_P) + γ·ΔJ − reversibility_penalty
    #
    # Conceptual framing (Ken 2026-04-24 reframing): a problem is a mixed
    # T/S/P load; solving it = reduce T + capture S + increase P. The
    # driver_mix IS the problem signature — defensive problems concentrate
    # mass on T, maintenance on S, expansionary on P, and mixed problems
    # land anywhere in the simplex. The driver-weighted sum reads this
    # signature per-tick and ranks candidates by how well their predicted
    # Δstate fits it. "Problem type" is not a separate concept — it's just
    # where driver_mix concentrates.
    #
    # γ = ranking_gamma controls ΔJ's role. Small γ makes ΔJ a tiebreaker
    # under balanced-driver conditions (when T, S, P are all ≈ 1/3 and the
    # driver-weighted term is nearly uniform across candidates), NOT a
    # co-ranker. Large γ collapses to the old driver-blind behaviour.
    # Default γ=0.3: driver-weighted term dominates by ~3× at typical
    # magnitudes. Revise after real-session trace analysis.
    ranking_gamma: float = 0.3

    # Multiplier on candidate.reversibility_penalty in the composite score:
    #   composite = driver_weighted_rewards + γ·ΔJ − w_irr·reversibility_penalty
    # Per Phase A.1 audit (LIVE_ORGANISM_RECOVERY_SPEC.md, 2026-04-28): the
    # maintain attractor is reversibility-penalty-dominated in 66.7% of the
    # observed suppression cases. With current default (1.0) and standard
    # expand-family penalty (0.02), a candidate needs ΔJ ≥ 0.067 just to
    # break even — order of magnitude above typical live ΔJ (≈ 0.005-0.010).
    # First-class config field as of Phase A.2 so it's auditable in
    # biaser_decision_audit and addressable via the same override plumbing
    # as biaser_w_V_override. Default 1.0 preserves current behaviour.
    irreversibility_weight: float = 1.0

    # ===== Phase A.8.3/A.8.4 V6 state-semantics gate =====
    # feature_version selects which extractors produce V/R/D/O/E.
    # Phase A.8 Step 9 promotion (V6_BOUNDED_OPPORTUNISM_PROMOTION_SPEC.md
    # §3.1.1): default flipped from "v3_nourishment" to "v6_plastic_memory"
    # so the bounded V6 model produced by Step 7-ter retrain (validated by
    # Step 6-quater Outcome A 11/11 + Step 8 incumbent comparison §5.4
    # PASS) sees in-distribution V6 features in the live load path. V3
    # rollback remains one-step via TOM_FEATURE_VERSION=v3_nourishment +
    # TOM_FORWARD_MODEL_PATH override (per §5.2 rollback procedure).
    feature_version: str = "v6_plastic_memory"

    # Phase A.8 Step 9 promotion (V6_BOUNDED_OPPORTUNISM_PROMOTION_SPEC.md
    # §3.1.2): NEW field tagging the active CONSEQUENCE_RULES table the
    # runtime expects. Default "v6_bounded_opportunism" matches the
    # bounded V6 model artefact (state_feature_version=
    # "v6_plastic_memory" + consequence_rules_version=
    # "v6_bounded_opportunism") promoted in Step 9. The runtime tag is
    # surfaced in audit rows + the health endpoint per §3.4 telemetry
    # contract; ShadowHook (§3.2) cross-checks the loaded model artefact
    # against this runtime tag at startup and aborts on mismatch (no
    # silent fallback). Allowed values are the same set
    # `get_consequence_rules` dispatches on:
    # {"v3", "v6", "v6_bounded_opportunism"}; __post_init__ rejects
    # anything else fail-loud (mirrors _ALLOWED_BIASER_MODES discipline).
    consequence_rules_version: str = "v6_bounded_opportunism"

    # V6 mechanical-failure floor — true numeric/physical instability
    # threshold, distinct from the plastic-memory saturation point at
    # ~0.0485. Branches with kappa above this floor are mechanically
    # functional even if plasticised; only branches BELOW count as
    # non-viable in V_capacity computation. Default 0.001 (well below the
    # observed saturation point, well above zero).
    v6_mechanical_failure_floor: float = 0.001

    # V6 starvation threshold (in ticks) — branches starved for this many
    # ticks count as fully starved in D_active's starvation component.
    # Default 100 ticks: short enough to detect resource-induced damage,
    # long enough to not flag transient nourishment dips.
    v6_starvation_threshold_ticks: int = 100

    # V6 D_active blend weights (sum to 1.0). Per spec recommendation:
    # equal third weight on overload, sigma-alarm fraction, and starvation.
    v6_d_weight_overload: float = 1.0 / 3
    v6_d_weight_sigma: float = 1.0 / 3
    v6_d_weight_starvation: float = 1.0 / 3

    # V6 V_capacity blend weights (sum to 1.0). Per spec recommendation:
    # equal third weight on viability fraction, spare capacity, and stability.
    v6_v_weight_viability: float = 1.0 / 3
    v6_v_weight_spare: float = 1.0 / 3
    v6_v_weight_stability: float = 1.0 / 3

    # Asymmetric urgency weights — Ken review open-issue #4: "Threat should
    # dominate interruption; procreation should not." Urgency is computed as
    # urgency = clamp(w_E·E + w_T·T + w_S·S + w_P·P, 0, 1).
    #
    # Under pure-T at 1.0 with E=0.5: urgency = 0.25 + 0.4 = 0.65. Under pure-P
    # at 1.0 with E=0.5: urgency = 0.25 + 0.1 = 0.35. Only threat (or residual
    # exposure E) crosses the 0.8 scaffold-interruption threshold; procreation
    # opportunity never forces an interrupt.
    urgency_weight_E: float = 0.5
    urgency_weight_T: float = 0.4
    urgency_weight_S: float = 0.25
    urgency_weight_P: float = 0.1

    # -- Driver-pressure reward modulation (Ken review #5) -------------
    # When enabled, each per-driver reward is multiplied by (1 + α·driver_read),
    # so resolving a real threat (T=0.9) scores strictly more than resolving a
    # non-threat (T=0.1). DEFAULT OFF — lower-risk rollout. Turn on after
    # driver-weighted ranking is validated with real-session trace data.
    driver_pressure_modulation: bool = False
    driver_pressure_alpha: float = 0.5

    # -- State-conditioned effective-driver reweighting (Ken 2026-04-24) --
    # Phase 5 simulation revealed: once the model learns P×expand correctly,
    # pure-P + high-E recruits expand even when E is structurally
    # threatening. Fix (Ken's modified-C): state-condition the driver
    # weights used in the composite so high residual threat exposure
    # re-introduces T weight and suppresses P weight, even if the external
    # driver_mix reads pure-P. Semantics: "opportunity is valid only when
    # the organism has enough safety margin to exploit it."
    #
    #   hazard = clamp((E − E_safe) / (1 − E_safe), 0, 1)
    #   T_eff = T + β·hazard
    #   S_eff = S
    #   P_eff = P·(1 − ρ·hazard)
    #   (then re-normalise to sum 1)
    #
    # Only affects the composite-weighting vector. The original driver_mix
    # remains in the feature vector (that's what the user expressed; the
    # forward model still predicts from it).
    hazard_E_safe: float = 0.35
    hazard_beta: float = 0.75    # T injection per unit hazard
    hazard_rho: float = 0.75     # P suppression per unit hazard

    # ------------------------------------------------------------------
    # Biaser mode (Route A end-to-end comparison spec, 2026-04-27)
    # Spec: sandbox/ROUTE_A_E2E_COMPARISON_SPEC.md
    # ------------------------------------------------------------------
    # Three-state model:
    #   "off"    — biaser code does NOT run. No predictions, no logging.
    #              Reserved for outcomes where biaser is empirically harmful
    #              (Outcome D / Outcome E from Route A).
    #   "shadow" — biaser code runs, computes predictions, applies bias_alpha=0
    #              (no influence on scaffold). Default; equivalent to current
    #              organism-shadow-mode. Used for Route A's baseline arm + interim
    #              + Outcomes B/C.
    #   "biaser" — biaser code runs with bias_alpha=biaser_alpha (=0.5 frozen
    #              for Route A). Influences scaffold op selection. Used for
    #              Route A's treatment arm and (post-Route-A-PASS) production.
    biaser_mode: str = "shadow"

    # Linear-combination blend weight when biaser_mode == "biaser":
    #   blended_score = (1 - biaser_alpha) * scaffold_score + biaser_alpha * bias_score
    # Frozen at 0.5 for Route A (half-effect midpoint, Bayesian-flat anchor).
    # Other values out of scope for Route A.
    biaser_alpha: float = 0.5

    # V-protective biaser composite (Ken 2026-04-27 Path 1 diagnostic).
    # When set, the biaser uses these weight overrides instead of the
    # default weight_viability / weight_threat_exposure for its J
    # computation. The rest of the organism keeps the default weights.
    # None = no override (use default weights). Recommended deployment:
    # biaser_mode='biaser', biaser_alpha=1.0, biaser_w_V_override=3.0
    # per sandbox/ROUTE_A_V_PROTECTED_VERDICT.md.
    # Production deployment is via runtime override (/api/biaser_config POST
    # or TOM_BIASER_* env vars), not code-baked defaults.
    biaser_w_V_override: Optional[float] = None
    biaser_w_E_override: Optional[float] = None

    # ------------------------------------------------------------------
    # Stage B of the ToM authority throat (plan §8) — the GATE.
    # ------------------------------------------------------------------
    # When False (default), the biaser scoring is byte-identical to the
    # current (Stage A) behaviour: only J = w_V·V + w_R·R + w_O·O − w_D·D − w_E·E
    # is computed; carrier_axis_amplitudes and proto_brain_posture are NOT
    # gathered, NOT consumed.
    #
    # When True (Stage B active), the biaser additionally scores each
    # candidate with axis_alignment + posture_alignment terms (see
    # agency/signal/biaser_signals.py + agency/organism/biaser.py).
    #
    # Per plan §6: this gate stays False until Stage A passes its
    # acceptance battery. Operator surface (env var):
    #   TOM_BIASER_CARRIER_READOUT_ENABLED=true
    enable_carrier_readout_signals: bool = False
    # Weights applied to the new scoring terms when the gate is True.
    # Defaults from plan §8.3. Setting either to 0.0 effectively disables
    # that term while leaving the gathering pipeline running (useful for
    # ablation diagnostics).
    axis_alignment_weight: float = 0.3
    posture_alignment_weight: float = 0.2

    # Allowed values for biaser_mode. Validation raises on invalid input
    # rather than silently enabling an unknown mode.
    _ALLOWED_BIASER_MODES: ClassVar[frozenset] = frozenset({"off", "shadow", "biaser"})

    # Phase A.8 Step 9 promotion: allowed values for
    # consequence_rules_version. Unknown values fail closed at config
    # construction; this matches the V6_INCUMBENT_COMPARISON_SPEC.md §3.3.1
    # "comparison_mode" guard and prevents silent contamination from a
    # fourth rule-table version someone might add later. Always keep this
    # set in sync with `sandbox.simulate_forced_exploration_synthetic.
    # get_consequence_rules`'s dispatch tables.
    _ALLOWED_CONSEQUENCE_RULES_VERSIONS: ClassVar[frozenset] = frozenset({
        "v3", "v6", "v6_bounded_opportunism",
    })

    def __post_init__(self) -> None:
        if self.biaser_mode not in self._ALLOWED_BIASER_MODES:
            raise ValueError(
                f"biaser_mode={self.biaser_mode!r} is not allowed. "
                f"Must be one of {sorted(self._ALLOWED_BIASER_MODES)}. "
                "Validation fails closed: invalid mode is rejected at "
                "config load time rather than silently enabling an "
                "unknown mode at runtime."
            )
        if (
            self.consequence_rules_version
            not in self._ALLOWED_CONSEQUENCE_RULES_VERSIONS
        ):
            raise ValueError(
                f"consequence_rules_version="
                f"{self.consequence_rules_version!r} is not allowed. "
                f"Must be one of "
                f"{sorted(self._ALLOWED_CONSEQUENCE_RULES_VERSIONS)}. "
                "Validation fails closed per "
                "V6_BOUNDED_OPPORTUNISM_PROMOTION_SPEC.md §3.1.2; an "
                "unknown rule-table tag would silently mis-attribute "
                "audit rows and break ShadowHook's load-time provenance "
                "check."
                )


@dataclass(frozen=True)
class MSRReferenceLoadConfig:
    """H2.4 deterministic topic-reference load component."""

    enabled: bool = True
    epsilon_ref: float = 1.0
    named_weight: float = 2.0
    common_weight: float = 1.0
    confidence_dim_scale: float = 0.0
    hash_key: str = "tom_ref_v1"
    stoplist_version: str = "v1"
    max_referents: int = 24


@dataclass(frozen=True)
class TunableParams:
    """
    Top-level container for all tunable parameters.

    This is the single source of truth for all hardcoded values
    that should be configurable.
    """
    sicd_kappa: SICDKappaUpdateConfig = field(default_factory=SICDKappaUpdateConfig)
    sicd_antifrag: SICDAntifragilityConfig = field(default_factory=SICDAntifragilityConfig)
    sicd_stiffness: SICDStiffnessConfig = field(default_factory=SICDStiffnessConfig)
    tom_directive_constraint: ToMDirectiveConstraintConfig = field(default_factory=ToMDirectiveConstraintConfig)
    drift_verifier: DriftVerifierConfig = field(default_factory=DriftVerifierConfig)
    drift_influence: DriftInfluenceConfig = field(default_factory=DriftInfluenceConfig)
    ethos: EthosConfig = field(default_factory=EthosConfig)
    policy_guard: PolicyGuardConfig = field(default_factory=PolicyGuardConfig)
    supervisor: SupervisorConfig = field(default_factory=SupervisorConfig)
    llm_integration: LLMIntegrationConfig = field(default_factory=LLMIntegrationConfig)
    coupling: CouplingConfig = field(default_factory=CouplingConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    rgm_enhancement: RGMEnhancementConfig = field(default_factory=RGMEnhancementConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    agency_dynamics: AgencyDynamicsConfig = field(default_factory=AgencyDynamicsConfig)
    tool_gating: ToolGatingConfig = field(default_factory=ToolGatingConfig)
    initiative_pulse: InitiativePulseConfig = field(default_factory=InitiativePulseConfig)
    warmup: WarmupConfig = field(default_factory=WarmupConfig)
    interface: InterfaceConfig = field(default_factory=InterfaceConfig)
    evidence: EvidenceConfig = field(default_factory=EvidenceConfig)
    integrations: IntegrationsConfig = field(default_factory=IntegrationsConfig)
    suite_runner: SuiteRunnerConfig = field(default_factory=SuiteRunnerConfig)
    energy_feedback: EnergyFeedbackConfig = field(default_factory=EnergyFeedbackConfig)
    nourishment_valuation: NourishmentValuationConfig = field(default_factory=NourishmentValuationConfig)
    hunger_drive: HungerDriveConfig = field(default_factory=HungerDriveConfig)
    shadow_reward: ShadowRewardConfig = field(default_factory=ShadowRewardConfig)
    vector_voice: VectorVoiceConfig = field(default_factory=VectorVoiceConfig)
    realiser: RealisationConfig = field(default_factory=RealisationConfig)
    agent_llm: AgentLLMConfig = field(default_factory=AgentLLMConfig)
    doc_ingest: DocIngestConfig = field(default_factory=DocIngestConfig)
    fgr: FgrConfig = field(default_factory=FgrConfig)
    energy_fallback: EnergyFallbackConfig = field(default_factory=EnergyFallbackConfig)
    msr_reference_load: MSRReferenceLoadConfig = field(default_factory=MSRReferenceLoadConfig)
    action_learning: ActionLearningConfig = field(default_factory=ActionLearningConfig)
    autonomic_coupling: AutonomicCouplingConfig = field(default_factory=AutonomicCouplingConfig)
    audio_salience: AudioSalienceConfig = field(default_factory=AudioSalienceConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    structural_audio: StructuralAudioConfig = field(default_factory=StructuralAudioConfig)
    word_excitation: WordExcitationConfig = field(default_factory=WordExcitationConfig)
    feeling_wheel: FeelingWheelConfig = field(default_factory=FeelingWheelConfig)
    governance: GovernanceConfig = field(default_factory=GovernanceConfig)
    scaffold: ScaffoldConfig = field(default_factory=ScaffoldConfig)
    organism_reward: OrganismRewardConfig = field(default_factory=OrganismRewardConfig)


# Module-level singleton for convenience
_default_params: TunableParams | None = None


def get_tunable_params() -> TunableParams:
    """Get the default tunable parameters singleton."""
    global _default_params
    if _default_params is None:
        _default_params = TunableParams()
    return _default_params
