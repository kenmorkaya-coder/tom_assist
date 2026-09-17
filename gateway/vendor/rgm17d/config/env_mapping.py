"""
Environment variable to config path mapping.

This is the canonical mapping of TOM_* environment variables to their
corresponding ToMConfig paths. Generated from comprehensive codebase analysis.

Total: 116 unique TOM_* environment variables.

Categories:
- LLM Configuration: 17 vars
- Ollama-specific: 5 vars
- OpenAI-specific: 3 vars
- Concurrency: 2 vars
- Deliberation: 5 vars
- Coupling & Verification: 6 vars
- Evidence & Context: 5 vars
- Warmup & Initialization: 5 vars
- Branch Growth & Leaf: 5 vars
- Semantic Control: 7 vars
- Canopy: 3 vars
- Background Physics: 6 vars
- Action: 5 vars
- Memory Test: 8 vars
- Test Injection: 6 vars
- Force Flags: 4 vars
- Session & Persistence: 4 vars
- Drift & Policy: 3 vars
- Feature Flags & Rendering: 9 vars
- Misc: 8 vars
"""

from __future__ import annotations

from typing import Dict

# ============================================================================
# ENV VAR -> CONFIG PATH MAPPING
# ============================================================================

ENV_TO_CONFIG_PATH: Dict[str, str] = {
    # =========================================================================
    # LLM CONFIGURATION (17 vars)
    # =========================================================================
    "TOM_LLM_PROVIDER": "llm.provider",
    "TOM_LLM_MODEL": "llm.model",
    "TOM_LLM_API_KEY": "llm.api_key",
    "TOM_LLM_BASE_URL": "llm.base_url",
    "TOM_LLM_TIMEOUT_S": "llm.timeout_seconds",
    "TOM_LLM_NUM_PREDICT": "llm.num_predict",
    "TOM_LLM_MAX_RETRIES": "llm.max_retries",
    "TOM_LLM_TEMPERATURE": "llm.temperature",
    "TOM_LLM_SEED": "llm.seed",
    "TOM_LLM_REASONING_EFFORT": "llm.reasoning_effort",
    "TOM_MAX_LLM_CONCURRENCY": "llm.max_concurrency",
    "TOM_AGENT_PLAN_EXECUTE": "llm.agent_plan_execute",

    # Ordinary-chat causal authority cutover.  The route is selected by
    # default, while a missing explicit root/revision remains an activation
    # preflight block rather than a fallback to the deterministic compiler.
    "TOM_DIRECT_CONTEXTUAL_17D_AUTHORITY_ENABLED": "direct_contextual_17d_authority.enabled",
    "TOM_DIRECT_CONTEXTUAL_17D_ROUTE_ROOT": "direct_contextual_17d_authority.route_root",
    "TOM_DIRECT_CONTEXTUAL_17D_EXPECTED_BACKEND_GIT_COMMIT": "direct_contextual_17d_authority.expected_backend_git_commit",

    # =========================================================================
    # OLLAMA-SPECIFIC (5 vars) - legacy, maps to llm.*
    # =========================================================================
    "TOM_OLLAMA_ENDPOINT": "llm.base_url",
    "TOM_OLLAMA_MODEL": "llm.model",
    "TOM_OLLAMA_TIMEOUT": "llm.timeout_seconds",
    "TOM_OLLAMA_TEMPERATURE": "llm.temperature",
    "TOM_OLLAMA_N_PREDICT": "llm.num_predict",

    # =========================================================================
    # OPENAI-SPECIFIC (3 vars)
    # =========================================================================
    "TOM_OPENAI_TPM_LIMIT": "llm.openai_tpm_limit",
    "TOM_OPENAI_TOKEN_ESTIMATE": "llm.openai_token_estimate",
    "TOM_DISABLE_TPM_BUCKET": "llm.disable_tpm_bucket",

    # =========================================================================
    # ANTHROPIC-SPECIFIC (2 vars)
    # =========================================================================
    "TOM_ANTHROPIC_TRANSPORT": "llm.anthropic_transport",
    "TOM_AGENT_ANTHROPIC_TRANSPORT": "llm.agent_anthropic_transport",

    # =========================================================================
    # CONCURRENCY & RATE LIMITING (2 vars)
    # =========================================================================
    "TOM_DISABLE_FLOCK": "concurrency.disable_flock",

    # =========================================================================
    # DELIBERATION (5 vars + 10 v2 vars)
    # =========================================================================
    "TOM_DELIBERATION_ENABLED": "deliberation.enabled",
    "TOM_NUM_CANDIDATES": "deliberation.num_candidates",
    "TOM_MAX_DELIBERATION_ROUNDS": "deliberation.max_rounds",
    "TOM_DELIBERATION_EASY_THRESH": "deliberation.easy_threshold",
    "TOM_FORCE_DELIBERATION": "deliberation.force_deliberation",
    "TOM_REVISE_TOP_N": "deliberation.revise_top_n",
    "TOM_MAX_REVISE_RETRIES": "deliberation.max_revise_retries",
    # v2 deliberation scoring
    "TOM_DELIBERATION_V2": "deliberation.v2_enabled",
    "TOM_SCORE_W_SEM": "deliberation.score.w_sem",
    "TOM_EPSILON_MEM": "deliberation.score.epsilon_mem",
    "TOM_EPSILON_SEM": "deliberation.score.epsilon_sem",
    "TOM_EPSILON_MARGIN": "deliberation.score.epsilon_margin",
    "TOM_EPSILON_IMPROVE": "deliberation.score.epsilon_improve",
    "TOM_GAMMA_DIMINISH": "deliberation.score.gamma",
    "TOM_DELIB_REINFORCEMENT": "deliberation.score.reinforcement_nudge",
    "TOM_MIN_DELIB_ROUNDS": "deliberation.score.min_rounds",
    "TOM_ESEM_MISSING": "deliberation.score.e_sem_missing",

    # =========================================================================
    # COUPLING & VERIFICATION GATES (6 vars)
    # =========================================================================
    "TOM_VERIFICATION_GATE_ENABLED": "verification.gate_enabled",
    "TOM_VERIFICATION_ENABLED": "verification.enabled",
    "TOM_FORCE_COUPLING": "coupling.force_coupling",
    "TOM_ALLOW_DEFER": "coupling.allow_defer",
    "TOM_MIN_GUARD_SCORE": "coupling.min_guard_score",

    # =========================================================================
    # EVIDENCE & CONTEXT LIMITS (5 vars)
    # =========================================================================
    "TOM_EVIDENCE_MAX_SPANS": "evidence.max_spans",
    "TOM_EVIDENCE_CONTEXT_MAX_TOKENS": "evidence.context_max_tokens",
    "TOM_EVIDENCE_PROVIDER_URL": "verification.evidence_provider_url",
    "TOM_EVIDENCE_PROVIDER_TIMEOUT": "verification.evidence_provider_timeout",
    "TOM_DRIFT_REQUIRE_CITATIONS": "drift.require_citations",

    # =========================================================================
    # WARMUP & INITIALIZATION (5 vars)
    # =========================================================================
    "TOM_WARMUP_MIN_TICK": "warmup.min_tick",
    "TOM_WARMUP_BALANCE_TOLERANCE": "warmup.balance_tolerance",
    "TOM_WARMUP_BALANCED_TICKS_REQUIRED": "warmup.balanced_ticks_required",
    "TOM_WARMUP_ROTATION_STEP": "warmup.rotation_step",
    "TOM_WARMUP_TICKS": "warmup.total_ticks",

    # =========================================================================
    # BRANCH GROWTH & LEAF MECHANICS (5 vars)
    # =========================================================================
    "TOM_LEAF_BALANCE_ENABLED": "sicd.leaf_balance_enabled",
    "TOM_LEAF_ALLOC_ENABLED": "sicd.leaf_alloc_enabled",
    "TOM_LEAF_V2": "sicd.leaf_v2_enabled",
    "TOM_LEAF_ALPHA": "sicd.leaf_alpha",
    "TOM_LEAF_BETA": "sicd.leaf_beta",
    "TOM_LEAF_VEC_ENABLED": "sicd.enable_leaf_vec",
    "TOM_LEAF_VEC_ALPHA": "sicd.leaf_vec_ema_alpha",
    "TOM_LEAF_VEC_CONFIDENCE_GATE": "sicd.leaf_vec_confidence_gate",
    "TOM_LEAF_VEC_DECAY_HALF_LIFE": "sicd.leaf_vec_decay_half_life",
    "TOM_RESIDUE_GATE_TOP_K": "sicd.residue_gate_top_k",
    "TOM_RESIDUE_ALPHA_BOUNDED": "sicd.residue_alpha_bounded",
    "TOM_MSR_MAGNITUDE_REF_RMS": "sicd.msr_magnitude_ref_rms",
    "TOM_DEPOSITION_CONDUCTION_SHARE": "sicd.deposition_conduction_share",
    "TOM_DISTRICT_OWNED_PENALTY": "sicd.district_owned_penalty",
    "TOM_DISTRICT_RECRUITMENT_OCCUPANCY_PENALTY": "sicd.district_recruitment_occupancy_penalty",
    "TOM_DISTRICT_OWN_TAU": "sicd.district_own_tau",
    "TOM_DISTRICT_EXCLUSION_STRENGTH": "sicd.district_exclusion_strength",
    "TOM_DISTRICT_OWNER_ALPHA": "sicd.district_owner_alpha",
    "TOM_DISTRICT_OWNER_ALPHA_MODE": "sicd.district_owner_alpha_mode",
    "TOM_DISTRICT_OWNER_ALPHA_FLOOR": "sicd.district_owner_alpha_floor",
    "TOM_DISTRICT_STALE_HORIZON": "sicd.district_stale_horizon",
    "TOM_DISTRICT_PROTECTION_GAIN": "sicd.district_protection_gain",
    "TOM_DISTRICT_STALE_STRENGTH_DECAY": "sicd.district_stale_strength_decay",
    "TOM_DISTRICT_CONTENT_SOURCE": "sicd.district_content_source",
    "TOM_DISTRICT_LIVE_RECALL": "tunable.agent_memory.district_live_recall_enabled",
    "TOM_DISTRICT_LIVE_RECALL_CONFIDENCE_FLOOR": "tunable.agent_memory.district_live_recall_confidence_floor",
    "TOM_DISTRICT_LIVE_RECALL_MATCH_FLOOR": "tunable.agent_memory.district_live_recall_match_floor",
    "TOM_DISTRICT_LIVE_RECALL_SELECTOR": "tunable.agent_memory.district_live_recall_selector",
    "TOM_DISTRICT_LIVE_RECALL_TOP_K": "tunable.agent_memory.district_live_recall_top_k",
    "TOM_DISTRICT_LIVE_RECALL_MAX_CHARS": "tunable.agent_memory.district_live_recall_max_chars",
    "TOM_CARILLON_LIVE_TERRITORY_ROUTING": "tunable.agent_memory.carillon_live_territory_routing_enabled",
    "TOM_E15_LIVE_CONSOLIDATION": "tunable.agent_memory.e15_live_consolidation_enabled",
    "TOM_MSR_REFERENCE_LOAD_ENABLED": "tunable.msr_reference_load.enabled",
    "TOM_MSR_REFERENCE_LOAD_EPSILON_REF": "tunable.msr_reference_load.epsilon_ref",
    "TOM_MSR_REFERENCE_LOAD_NAMED_WEIGHT": "tunable.msr_reference_load.named_weight",
    "TOM_MSR_REFERENCE_LOAD_COMMON_WEIGHT": "tunable.msr_reference_load.common_weight",
    "TOM_MSR_REFERENCE_LOAD_CONFIDENCE_DIM_SCALE": "tunable.msr_reference_load.confidence_dim_scale",
    "TOM_MSR_REFERENCE_LOAD_HASH_KEY": "tunable.msr_reference_load.hash_key",
    "TOM_MSR_REFERENCE_LOAD_MAX_REFERENTS": "tunable.msr_reference_load.max_referents",
    "TOM_DISTRICT_ROUTING_SOURCE": "sicd.district_routing_source",
    "TOM_DISTRICT_IMPRINT_GATE_17D": "sicd.district_imprint_gate_17d",
    "TOM_DISTRICT_IMPRINT_GATE_17D_TOP_K": "sicd.district_imprint_gate_17d_top_k",
    "TOM_LEAF_VEC_RETRIEVAL_WEIGHT": "sicd.leaf_vec_retrieval_weight",
    "TOM_LEAF_VEC_GROWTH_GAIN": "sicd.leaf_vec_growth_gain",
    "TOM_LEAF_VEC_SPAWN_MIX": "sicd.leaf_vec_spawn_mix",
    "TOM_LEAF_VEC_PRUNE_AGE_BOOST": "sicd.leaf_vec_prune_age_boost",

    # =========================================================================
    # SEMANTIC CONTROL & TARGETS (7 vars)
    # =========================================================================
    "TOM_SEMANTIC_CONTROLLER_ENABLED": "semantic.enabled",
    "TOM_DISABLE_SEM_CTRL": "semantic.disabled",
    "TOM_BETA_SEM": "semantic.beta_sem",
    "TOM_FORCE_SEMANTIC_TARGETS": "semantic.force_targets",
    "TOM_SEM_TARGET_HOLD_QUANT_DECIMALS": "semantic.target_hold_quant_decimals",
    "TOM_KAPPA_SEMANTIC_GAIN": "sicd.kappa_semantic_gain",
    "TOM_TAU_BLEND_ALPHA_MAX": "sicd.tau_blend_alpha_max",

    # =========================================================================
    # CANOPY BIAS & IMBALANCE (3 vars)
    # =========================================================================
    "TOM_CANOPY_ENV_BIAS_ENABLED": "canopy.env_bias_enabled",
    "TOM_CANOPY_IMBALANCE_LOW": "canopy.imbalance_low",
    "TOM_CANOPY_IMBALANCE_HIGH": "canopy.imbalance_high",

    # =========================================================================
    # BACKGROUND PHYSICS & IDLE AGE (6 vars)
    # =========================================================================
    "TOM_BG_PHYS_TICKS": "background_physics.max_ticks",
    "TOM_BG_PHYS_MAX_MS": "background_physics.max_ms",
    "TOM_BG_PHYS_LOG": "background_physics.log_enabled",
    "TOM_BG_PHYS_SLO_GUARD": "background_physics.slo_guard_enabled",
    "TOM_IDLE_AGE_TICKS_PER_SEC": "background_physics.idle_ticks_per_sec",
    "TOM_IDLE_AGE_MAX_TICKS": "background_physics.idle_max_ticks",

    # =========================================================================
    # ACTION OPERATORS & PRIORS (5 vars)
    # =========================================================================
    "TOM_ACTION_OPERATORS_ENABLED": "action.operators_enabled",
    "TOM_ACTION_DIVERGENCE_TEST": "action.divergence_test",
    "TOM_SPAWN_AXIS_GAIN_ENABLED": "sicd.spawn_axis_gain_enabled",

    # =========================================================================
    # MEMORY TEST CONFIGURATION (8 vars)
    # =========================================================================
    "TOM_MEM_TEST_MODE": "testing.mem_test_mode",
    "TOM_MEM_TICKS_PER_RUN": "testing.mem_ticks_per_run",
    "TOM_MEM_TARGET_BRANCHES": "testing.mem_target_branches",
    "TOM_MEM_MAX_TICKS": "testing.mem_max_ticks",
    "TOM_MEM_OBS_EVERY": "testing.mem_obs_every",
    "TOM_MEM_INFLUENCE_ENABLED": "testing.mem_influence_enabled",
    "TOM_MEM_INFLUENCE_COMPARE": "testing.mem_influence_compare",
    "TOM_MEM_SUITE_USE_LLM": "testing.mem_suite_use_llm",
    "TOM_MEM_EXTENDED": "testing.mem_extended",

    # =========================================================================
    # TEST INJECTION FLAGS (6 vars)
    # =========================================================================
    "TOM_TEST_FORCE_UNINITIALISED": "testing.force_uninitialised",
    "TOM_TEST_INJECT_MEMORY_WRITE": "testing.inject_memory_write",
    "TOM_TEST_INJECT_UNCITED": "testing.inject_uncited",
    "TOM_TEST_INJECT_CONTRADICTION": "testing.inject_contradiction",
    "TOM_TEST_INJECT_GOAL_SUBSTITUTION": "testing.inject_goal_substitution",
    "TOM_TEST_INJECT_QUARANTINE_WRITE": "testing.inject_quarantine_write",

    # =========================================================================
    # FORCE & OVERRIDE FLAGS (4 vars)
    # =========================================================================
    "TOM_FORCE_NO_STRUCTURAL": "feature_flags.force_no_structural",
    "TOM_FORCE_NO_MEMORY": "feature_flags.force_no_memory",
    "TOM_FORCE_NO_TOOLS": "feature_flags.force_no_tools",

    # =========================================================================
    # SESSION & PERSISTENCE (4 vars)
    # =========================================================================
    "TOM_SESSION_ID": "session.session_id",
    "TOM_PERSIST_DIR": "persistence.persistence_path",
    "TOM_RUN_ID": "session.run_id",
    "TOM_RUN_MODE": "session.run_mode",

    # =========================================================================
    # DRIFT & POLICY (3 vars)
    # =========================================================================
    "TOM_DRIFT_THRESHOLD": "drift.threshold_block",
    "TOM_POLICY_VERSION": "telemetry.policy_version",
    "TOM_V1_SCHEMA_DEPRECATED": "feature_flags.v1_schema_deprecated",

    # =========================================================================
    # FEATURE FLAGS & RENDERING (10 vars)
    # =========================================================================
    "TOM_SHADOW_RENDER_ENABLED": "interface.shadow_render_enabled",
    "TOM_PROPOSAL_MODE": "interface.proposal_mode",
    "TOM_DISABLE_REGEX_EXTRACTION": "interface.disable_regex_extraction",
    "TOM_REGEX_SELF_REF_ROUTING": "interface.regex_self_ref_routing",
    "TOM_SEMANTIC_LOADS_DISABLED": "semantic.loads_disabled",
    "TOM_REASONER_LIVE_SHADOW": "reasoner_live.shadow_enabled",
    "TOM_REASONER_LIVE_AUTHORITY_ADVISORY": (
        "reasoner_live.authority_advisory_enabled"
    ),
    "TOM_REASONER_LIVE_RELEASE_AUTHORITY": (
        "reasoner_live.release_authority_enabled"
    ),
    "TOM_REASONER_LIVE_AUTHORITY_PROOF_PATH": (
        "reasoner_live.authority_proof_path"
    ),
    "TOM_REASONER_LIVE_HEAVY_THRESHOLD": "reasoner_live.heavy_threshold",
    "TOM_FEATURE_BANNER": "interface.feature_banner",
    "TOM_EXPECTED_PRESET": "interface.expected_preset",

    # =========================================================================
    # IDLE AGE & REMINDERS (2 vars)
    # =========================================================================
    "TOM_IDLE_AGE_REMINDER": "interface.idle_age_reminder",
    "TOM_IDLE_AGE_REMINDER_DAYS": "interface.idle_age_reminder_days",

    # =========================================================================
    # PENDING INTERACTIONS (1 var)
    # =========================================================================
    "TOM_PENDING_EXPIRY_SECONDS": "interface.pending_expiry_seconds",

    # =========================================================================
    # BRILLIANCE HOOK (1 var)
    # =========================================================================
    "TOM_BRILLIANCE_HOOK_DISABLED": "interface.brilliance_hook_disabled",

    # =========================================================================
    # SPATIAL & VERIFICATION (3 vars)
    # =========================================================================
    "TOM_SPATIAL_ANCHOR_STORE_PATH": "spatial_memory.store_path",
    "TOM_ORG_ID": "verification.org_id",
    "TOM_ENABLE_SPATIAL_MEMORY": "spatial_memory.enabled",

    # =========================================================================
    # VERIFICATION MOCK (2 vars)
    # =========================================================================
    "TOM_MOCK_VERDICT": "verification.mock_verdict",
    "TOM_MOCK_CONFIDENCE": "verification.mock_confidence",

    # =========================================================================
    # TELEMETRY (2 vars)
    # =========================================================================
    "TOM_RUN_ARTIFACT_PREFIX": "telemetry.run_artifact_prefix",
    "TOM_RUN_LABEL": "telemetry.run_label",

    # =========================================================================
    # EVALUATION (2 vars)
    # =========================================================================
    "TOM_EVAL_PREHOLD_TICKS": "eval.prehold_ticks",
    "TOM_RUN_REAL_WORLD_EVAL_BATTERY": "eval.run_real_world_battery",

    # =========================================================================
    # GATEWAY (1 var)
    # =========================================================================
    "TOM_GATEWAY_TOKEN": "gateway.token",

    # =========================================================================
    # MISC / UTILITY (3 vars)
    # =========================================================================
    "TOM_LOCAL_LLM": "testing.local_llm",
    "TOM_LOCAL_LLM_SMOKE": "testing.local_llm_smoke",
    "TOM_STRICT_STATE_HASH": "testing.strict_state_hash",
    "TOM_SKIP_PERF_THRESHOLDS": "testing.skip_perf_thresholds",

    # =========================================================================
    # SUITE RUNNER CONFIGURATION (4 vars) - Phase 3 hardening
    # =========================================================================
    "TOM_SUITE_TIMEOUT_SECONDS": "suite_runner.subprocess_timeout_seconds",
    "TOM_SUITE_MAX_TICKS": "suite_runner.max_ticks_per_suite",
    "TOM_SUITE_FAIL_FAST": "suite_runner.fail_fast",
    "TOM_SHUTDOWN_TIMEOUT": "suite_runner.shutdown_timeout_seconds",

    # =========================================================================
    # INTEGRATIONS CONFIGURATION (12 vars)
    # =========================================================================
    "TOM_WEBSEARCH_ENABLED": "integrations.web_search.enabled",
    "TOM_WEBSEARCH_TIMEOUT": "integrations.web_search.timeout_seconds",
    "TOM_WEBSEARCH_RATE_LIMIT": "integrations.web_search.rate_limit_rpm",
    "TOM_WEBSEARCH_MAX_RESULTS": "integrations.web_search.max_results",
    "TOM_FILEREAD_ENABLED": "integrations.file_read.enabled",
    "TOM_FILEREAD_BASE_DIR": "integrations.file_read.base_directory",
    "TOM_FILEREAD_TIMEOUT": "integrations.file_read.timeout_seconds",
    "TOM_FILEREAD_MAX_SIZE": "integrations.file_read.max_file_size_bytes",
    "TOM_SANDBOXEXEC_ENABLED": "integrations.sandbox_exec.enabled",
    "TOM_SANDBOXEXEC_TIMEOUT": "integrations.sandbox_exec.timeout_seconds",
    "TOM_SANDBOXEXEC_MAX_MEMORY": "integrations.sandbox_exec.max_memory_mb",
    "TOM_SANDBOXEXEC_ROOT": "integrations.sandbox_exec.sandbox_root",

    # =========================================================================
    # AGENTIC MODE CONFIGURATION (6 vars)
    # =========================================================================
    "TOM_AGENTIC_ENABLED": "tunable.agentic.enabled",
    "TOM_AGENTIC_THRESHOLD": "tunable.agentic.threshold",
    "TOM_AGENTIC_REQUIRE_APPROVAL": "tunable.agentic.require_approval",
    "TOM_AGENTIC_ISOLATED_MODE": "tunable.agentic.isolated_mode",
    "TOM_AGENTIC_RATE_LIMIT": "tunable.agentic.rate_limit",

    # =========================================================================
    # ToM AUTHORITY THROAT — directive constraint (Stage A throat plan §7.3+§7.4)
    # =========================================================================
    # Controller seam at controller/tom_controller.py:LLMOrchestratorV4
    # construction reads these via config.compat.get_bool / get_int. Setting
    # TOM_DIRECTIVE_CONSTRAINT_ENABLED=false flips the live backend into
    # Arm A of the kill test (ToM directive constraint NOT injected; validator
    # NOT run). Reload the VS Code window to apply.
    "TOM_DIRECTIVE_CONSTRAINT_ENABLED": "tunable.tom_directive_constraint.enabled",
    "TOM_DIRECTIVE_CONSTRAINT_ENABLE_VALIDATOR": "tunable.tom_directive_constraint.enable_validator",
    "TOM_DIRECTIVE_CONSTRAINT_MAX_RETRIES": "tunable.tom_directive_constraint.max_retries",
    "TOM_DIRECTIVE_CONSTRAINT_LOG_PASSTHROUGH": "tunable.tom_directive_constraint.log_passthrough",

    # =========================================================================
    # ToM AUTHORITY THROAT — Stage B gate (carrier + proto-brain → biaser)
    # =========================================================================
    # The Stage B kill-test gate. Defaults to False; flip to True only after
    # Stage A has passed its acceptance battery. When True, biaser scoring
    # adds axis_alignment + posture_alignment terms from
    # agency/signal/biaser_signals.py.
    "TOM_BIASER_CARRIER_READOUT_ENABLED": "tunable.organism_reward.enable_carrier_readout_signals",
    "TOM_BIASER_AXIS_ALIGNMENT_WEIGHT": "tunable.organism_reward.axis_alignment_weight",
    "TOM_BIASER_POSTURE_ALIGNMENT_WEIGHT": "tunable.organism_reward.posture_alignment_weight",

    # =========================================================================
    # NOURISHMENT VALUATION (3 vars)
    # =========================================================================
    "TOM_NOURISHMENT_VALUATION_ENABLED": "tunable.nourishment_valuation.enabled",
    "TOM_NOURISHMENT_VALUATION_KP": "tunable.nourishment_valuation.k_p",
    "TOM_NOURISHMENT_VALUATION_KE": "tunable.nourishment_valuation.k_e",

    # =========================================================================
    # HUNGER DRIVE (2 vars)
    # =========================================================================
    "TOM_HUNGER_DRIVE_ENABLED": "tunable.hunger_drive.enabled",
    "TOM_PHI_EFFORT_ENABLED": "tunable.hunger_drive.phi_effort_enabled",

    # =========================================================================
    # SHADOW REWARD (2 vars)
    # =========================================================================
    "TOM_SHADOW_REWARD_ENABLED": "tunable.shadow_reward.enabled",
    "TOM_SHADOW_REWARD_FELT_ENABLED": "tunable.shadow_reward.felt_coupling_enabled",

    # =========================================================================
    # AUTONOMIC COUPLING (6 vars)
    # =========================================================================
    "TOM_AUTONOMIC_ENABLED": "tunable.autonomic_coupling.enabled",
    "TOM_AUTONOMIC_TENSION_SPAWN_GAIN": "tunable.autonomic_coupling.tension_spawn_gain",
    "TOM_AUTONOMIC_FATIGUE_GROWTH_GAIN": "tunable.autonomic_coupling.fatigue_growth_gain",
    "TOM_AUTONOMIC_VITALITY_FLOOR_GAIN": "tunable.autonomic_coupling.vitality_floor_gain",
    "TOM_AUTONOMIC_GROUNDEDNESS_BALANCE_GAIN": "tunable.autonomic_coupling.groundedness_balance_gain",
    "TOM_AUTONOMIC_CLARITY_BAND_GAIN": "tunable.autonomic_coupling.clarity_band_gain",

    # =========================================================================
    # GOVERNANCE (1 var)
    # =========================================================================
    "TOM_GOVERNANCE_ENABLED": "tunable.governance.enable_governance_contract",
    "TOM_GOVERNANCE_BRIEF": "tunable.governance.enable_governance_brief",
    "TOM_GOVERNANCE_VALIDATION": "tunable.governance.enable_move_validation",
    "TOM_GOVERNANCE_TURN_POLICY": "tunable.governance.enable_turn_policy",
    "TOM_GOVERNANCE_EPISODE": "tunable.governance.enable_episode_persistence",

    # =========================================================================
    # SCAFFOLD AUTHORITY (2 vars)
    # =========================================================================
    "TOM_SCAFFOLD_AUTHORITY": "tunable.scaffold.authority_level",
    "TOM_SCAFFOLD_PLASTICITY": "tunable.scaffold.plasticity_enabled",

    # =========================================================================
    # DOCUMENT INGESTION (3 vars)
    # =========================================================================
    "TOM_DOC_MAX_SIZE_BYTES": "tunable.doc_ingest.max_file_size_bytes",
    "TOM_DOC_MAX_FILES_SCAN": "tunable.doc_ingest.max_files_per_scan",
    "TOM_DOC_MAX_ANCHORS": "tunable.doc_ingest.max_anchors_per_doc",

    # =========================================================================
    # MEMORY STORAGE POLICY (2 vars)
    # =========================================================================
    "TOM_MEMORY_STORAGE_POLICY": "tunable.memory.default_storage_policy",
    "TOM_MEMORY_SUMMARY_IN_CONTENT": "tunable.memory.allow_summary_in_content_for_embedding",

    # =========================================================================
    # FINITE GEOMETRY RETRIEVER (5 vars)
    # =========================================================================
    "TOM_FGR_ENABLED": "tunable.fgr.enabled",
    "TOM_FGR_POOL_PER_SOURCE": "tunable.fgr.pool_per_source",
    "TOM_FGR_AXIS_BALANCE": "tunable.fgr.axis_balance",
    "TOM_FGR_LATENCY_BUDGET_MS": "tunable.fgr.latency_budget_ms",
    "TOM_FGR_CHANNEL_WEIGHTS": "tunable.fgr.channel_weights",
    "TOM_FGR_ADAPTIVE_K": "tunable.fgr.adaptive_k",
    "TOM_FGR_K_BASE": "tunable.fgr.k_base",
    "TOM_FGR_K_MAX": "tunable.fgr.k_max",
    "TOM_FGR_K_SCALE_THRESHOLD": "tunable.fgr.k_scale_threshold",

    # =========================================================================
    # IDENTITY BOOTSTRAP (1 var)
    # =========================================================================
    "TOM_ENABLE_IDENTITY_BOOTSTRAP": "identity.enable_identity_bootstrap",

    # =========================================================================
    # VECTOR VOICE (2 vars)
    # =========================================================================
    "TOM_VECTOR_VOICE_ENABLED": "tunable.vector_voice.enabled",
    "TOM_VECTOR_VOICE_EMA_ALPHA": "tunable.vector_voice.ema_alpha",

    # =========================================================================
    # REALISER CONFIGURATION (8 vars)
    # =========================================================================
    "TOM_REALISER_PROVIDER": "tunable.realiser.provider",
    "TOM_REALISER_MODEL": "tunable.realiser.model",
    "TOM_REALISER_API_KEY": "tunable.realiser.api_key",
    "TOM_REALISER_BASE_URL": "tunable.realiser.base_url",
    "TOM_REALISER_TEMPERATURE": "tunable.realiser.temperature",
    "TOM_REALISER_MAX_TOKENS": "tunable.realiser.max_tokens",
    "TOM_REALISER_TIMEOUT_S": "tunable.realiser.timeout_s",
    "TOM_REALISER_GREETINGS": "tunable.realiser.realise_greetings",

    # =========================================================================
    # AGENT LLM CONFIGURATION (7 vars)
    # =========================================================================
    "TOM_AGENT_LLM_PROVIDER": "tunable.agent_llm.provider",
    "TOM_AGENT_LLM_MODEL": "tunable.agent_llm.model",
    "TOM_AGENT_LLM_API_KEY": "tunable.agent_llm.api_key",
    "TOM_AGENT_LLM_BASE_URL": "tunable.agent_llm.base_url",
    "TOM_AGENT_LLM_TEMPERATURE": "tunable.agent_llm.temperature",
    "TOM_AGENT_LLM_MAX_TOKENS": "tunable.agent_llm.max_tokens",
    "TOM_AGENT_LLM_TIMEOUT_S": "tunable.agent_llm.timeout_s",

    # =========================================================================
    # AUDIO SALIENCE (5 vars) — input only, no TTS
    # =========================================================================
    "TOM_AUDIO_PROVIDER": "tunable.audio_salience.provider",
    "TOM_AUDIO_WIND_GAIN": "tunable.audio_salience.wind_gain",
    "TOM_AUDIO_RATE_LIMIT": "tunable.audio_salience.rate_limit_per_min",
    "TOM_AUDIO_MAX_DURATION_S": "tunable.audio_salience.max_duration_s",
    "TOM_AUDIO_COMPUTE_BUDGET_S": "tunable.audio_salience.compute_budget_s",

    # TTS OUTPUT (3 vars)
    "TOM_TTS_PROVIDER": "tunable.tts.provider",
    "TOM_TTS_VOICE": "tunable.tts.voice",
    "TOM_TTS_ENABLED": "tunable.tts.enabled",

    # WORD EXCITATION (4 vars)
    "TOM_WORD_EXCITATION_ENABLED": "tunable.word_excitation.enabled",
    "TOM_WORD_EXCITATION_SHADOW_ONLY": "tunable.word_excitation.shadow_only",
    "TOM_WORD_EXCITATION_GAIN": "tunable.word_excitation.gain",
    "TOM_WORD_EXCITATION_MAP_PATH": "tunable.word_excitation.map_path",

    # FEELING WHEEL (4 vars)
    "TOM_FEELING_WHEEL_ENABLED": "tunable.feeling_wheel.enabled",
    "TOM_FEELING_WHEEL_SHADOW_ONLY": "tunable.feeling_wheel.shadow_only",
    "TOM_FEELING_WHEEL_GAIN": "tunable.feeling_wheel.gain",
    "TOM_FEELING_WHEEL_MAP_PATH": "tunable.feeling_wheel.map_path",

    # Predictive metrics
    "TOM_PREDICTIVE_E_RATIO_STABILITY_GATE_THRESHOLD": "predictive.e_ratio_stability_gate_threshold",

    # =========================================================================
    # ENERGY FALLBACK POLICY (10 vars)
    # =========================================================================
    "TOM_ENERGY_FALLBACK_ENABLED": "tunable.energy_fallback.enabled",
    "TOM_ENERGY_FALLBACK_DECAY_RATE": "tunable.energy_fallback.decay_rate",
    "TOM_ENERGY_FALLBACK_BASELINE_DEFAULT": "tunable.energy_fallback.baseline_default",
    "TOM_ENERGY_FALLBACK_BASELINE_STILLNESS": "tunable.energy_fallback.baseline_stillness",
    "TOM_ENERGY_FALLBACK_BASELINE_REFLECT": "tunable.energy_fallback.baseline_reflect",
    "TOM_ENERGY_FALLBACK_BASELINE_ACT": "tunable.energy_fallback.baseline_act",
    "TOM_ENERGY_FALLBACK_BASELINE_NORMAL": "tunable.energy_fallback.baseline_normal",
    "TOM_ENERGY_FALLBACK_BASELINE_SANDBOX": "tunable.energy_fallback.baseline_sandbox",
    "TOM_ENERGY_FALLBACK_BASELINE_REFLECTION": "tunable.energy_fallback.baseline_reflection",
    "TOM_ENERGY_FALLBACK_BASELINE_EMERGENCY": "tunable.energy_fallback.baseline_emergency",

    # =========================================================================
    # SICD GROWTH BUDGET (18 vars) - Phase 2 stabilization (S1 + D3)
    # =========================================================================
    "TOM_SPAWN_SOFT_CAP": "budget.spawn_soft_cap",
    "TOM_SPAWN_HARD_CAP": "budget.spawn_hard_cap",
    "TOM_SPAWN_BUDGET_BASE": "budget.spawn_budget_base",
    "TOM_SPAWN_COST_BASE": "budget.spawn_cost_base",
    # D3: Leaf + Root resource system
    "TOM_ROOT_RESERVE_ENABLED": "budget.root_reserve_enabled",
    "TOM_LEAF_CAPTURE_GAIN": "budget.leaf_capture_gain",
    "TOM_LEAF_CAPTURE_CAP": "budget.leaf_capture_cap",
    "TOM_LEAF_FACTOR_FLOOR": "budget.leaf_factor_floor",
    "TOM_ROOT_SUPPLY_BASE": "budget.root_supply_base",
    "TOM_ROOT_CAP_PER_BRANCH": "budget.root_cap_per_branch",
    "TOM_RESERVE_CAP_CEILING": "budget.reserve_cap_ceiling",
    "TOM_ROOT_DEPOSIT_FRACTION": "budget.root_deposit_fraction",
    "TOM_ROOT_OVERFLOW_FRACTION": "budget.root_overflow_fraction",
    "TOM_ROOT_RELEASE_RATE": "budget.root_release_rate",
    "TOM_ROOT_MAINT_REDUCTION": "budget.root_maint_reduction",
    "TOM_ROOT_CAPACITY_BOOST": "budget.root_capacity_boost",
    "TOM_ROOT_DECAY": "budget.root_decay",
    "TOM_BRANCH_CAPACITY": "budget.branch_capacity",
    "TOM_MAINT_COST_PER_BRANCH": "budget.maint_cost_per_branch",
    "TOM_MAINT_COST_PER_LENGTH": "budget.maint_cost_per_length",
    # D3-T: Transport controller
    "TOM_TRANSPORT_ENABLED": "budget.transport_enabled",
    "TOM_TRANSPORT_A": "budget.transport_A",
    "TOM_TRANSPORT_KN": "budget.transport_kN",
    "TOM_TRANSPORT_KL": "budget.transport_kL",
    "TOM_TRANSPORT_R_LOW": "budget.transport_R_low",
    "TOM_TRANSPORT_R_HIGH": "budget.transport_R_high",
    "TOM_TRANSPORT_GRACE_TICKS": "budget.transport_grace_ticks",
    "TOM_TRANSPORT_RAMP_RATE": "budget.transport_ramp_rate",
    "TOM_TRANSPORT_BOOST_MAX": "budget.transport_boost_max",
    "TOM_TRANSPORT_SLEW_RATE": "budget.transport_slew_rate",

    # =========================================================================
    # TREE GROWTH CONFIG (1 var) - allocation sharpness
    # =========================================================================
    "TOM_TAU1": "growth.tau1",

    # =========================================================================
    # SICD KAPPA TUNING (9 vars) - Phase 2 stabilization + Phase 3
    # =========================================================================
    "TOM_MIN_METABOLIC_FRACTION": "tunable.sicd_kappa.min_metabolic_fraction",
    "TOM_NOURISH_EMA_FLOOR": "tunable.sicd_kappa.nourish_ema_floor",
    "TOM_KAPPA_RECOVERY_THRESH": "tunable.sicd_kappa.kappa_recovery_thresh",
    "TOM_ALLOCATION_UNIFORM_MIX": "tunable.sicd_kappa.allocation_uniform_mix",
    "TOM_HEAL_BASELINE_FACTOR": "tunable.sicd_kappa.heal_baseline_factor",
    "TOM_STIFFNESS_KAPPA_FLOOR": "tunable.sicd.stiffness_kappa_floor",
    "TOM_LEAF_VEC_KAPPA_FLOOR": "tunable.sicd.leaf_vec_kappa_floor",
    "TOM_ALPHA_SIGMA_FLOOR": "tunable.antifragility.alpha_sigma_floor",

    # =========================================================================
    # ACTION LEARNING CONFIGURATION (10 vars)
    # =========================================================================
    "TOM_ACTION_LEARNING_ENABLED": "tunable.action_learning.enabled",
    "TOM_ACTION_LEARNING_MIN_CONFIDENCE": "tunable.action_learning.min_confidence",
    "TOM_ACTION_LEARNING_MIN_CONSISTENCY": "tunable.action_learning.min_consistency",
    "TOM_ACTION_LEARNING_MAX_PER_SESSION": "tunable.action_learning.max_records_per_session",
    "TOM_ACTION_LEARNING_MAX_STORE": "tunable.action_learning.max_store_size",
    "TOM_ACTION_LEARNING_RETRIEVAL_WEIGHT": "tunable.action_learning.retrieval_weight",
    "TOM_ACTION_LEARNING_RETRIEVAL_MAX": "tunable.action_learning.retrieval_max_items",
    "TOM_ACTION_LEARNING_SUCCESS_STRENGTH": "tunable.action_learning.success_strength",
    "TOM_ACTION_LEARNING_FAILURE_STRENGTH": "tunable.action_learning.failure_strength",
    "TOM_ACTION_LEARNING_TTL_DAYS": "tunable.action_learning.store_ttl_days",

    # =========================================================================
    # ORGANISM BIASER (4 vars) — Route B paired-session config-override
    # =========================================================================
    # Per Ken 2026-04-27: env-driven flip of biaser_mode for paired Route B
    # runs without editing source. Defaults remain shadow/0.5/None/None.
    # Invalid biaser_mode raises at config load time (fails closed).
    "TOM_BIASER_MODE": "tunable.organism_reward.biaser_mode",
    "TOM_BIASER_ALPHA": "tunable.organism_reward.biaser_alpha",
    "TOM_BIASER_W_V_OVERRIDE": "tunable.organism_reward.biaser_w_V_override",
    "TOM_BIASER_W_E_OVERRIDE": "tunable.organism_reward.biaser_w_E_override",

    # =========================================================================
    # ORGANISM RUNTIME OVERRIDE (Phase A.8.1) — calibration knobs reachable
    # via env without flipping production defaults. Per Ken 2026-04-28:
    # spawn_credit_cap currently makes O telemetry useless (cap=1000 vs
    # observed spawn_credit ~0.1). Runtime override allows operator-driven
    # recalibration during live capture without changing the dataclass
    # default. Default 1000.0 unchanged in OrganismRewardConfig.
    # =========================================================================
    "TOM_SPAWN_CREDIT_CAP": "tunable.organism_reward.spawn_credit_cap",

    # =========================================================================
    # V6 BOUNDED-OPPORTUNISM PROMOTION (Phase A.8 Step 9, 3 vars) — rollback-
    # path env vars per V6_BOUNDED_OPPORTUNISM_PROMOTION_SPEC.md §3.1.4.
    # =========================================================================
    # TOM_FORWARD_MODEL_PATH overrides agency.organism.shadow_hook.
    # DEFAULT_MODEL_PATH at module-load time. Set to the V3 or
    # conservative V6 artefact path to roll back from bounded V6 (see
    # spec §5.2). Read directly via os.environ.get in shadow_hook;
    # documented here so /api/health and dashboards can surface the
    # binding. The "config path" is informational — no
    # OrganismRewardConfig field is modified by this env var.
    "TOM_FORWARD_MODEL_PATH": "tunable.organism.forward_model_path",

    # TOM_FEATURE_VERSION overrides OrganismRewardConfig.feature_version.
    # Default (post-promotion) is "v6_plastic_memory"; rollback uses
    # "v3_nourishment".
    "TOM_FEATURE_VERSION": "tunable.organism_reward.feature_version",

    # TOM_CONSEQUENCE_RULES_VERSION overrides OrganismRewardConfig.
    # consequence_rules_version. Default (post-promotion) is
    # "v6_bounded_opportunism"; rollback uses "v3" or "v6".
    "TOM_CONSEQUENCE_RULES_VERSION": "tunable.organism_reward.consequence_rules_version",
}

# Reverse mapping: config.path -> ENV_VAR
CONFIG_PATH_TO_ENV: Dict[str, str] = {v: k for k, v in ENV_TO_CONFIG_PATH.items()}


# ============================================================================
# TYPE INFORMATION FOR PARSING
# ============================================================================

ENV_VAR_TYPES: Dict[str, str] = {
    # Boolean flags (parse "1"/"0" or "true"/"false")
    "TOM_DELIBERATION_ENABLED": "bool",
    "TOM_DELIBERATION_V2": "bool",
    "TOM_FORCE_DELIBERATION": "bool",
    "TOM_VERIFICATION_GATE_ENABLED": "bool",
    "TOM_VERIFICATION_ENABLED": "bool",
    "TOM_FORCE_COUPLING": "bool",
    "TOM_ALLOW_DEFER": "bool",
    "TOM_DRIFT_REQUIRE_CITATIONS": "bool",
    "TOM_LEAF_BALANCE_ENABLED": "bool",
    "TOM_LEAF_ALLOC_ENABLED": "bool",
    "TOM_LEAF_V2": "bool",
    "TOM_SEMANTIC_CONTROLLER_ENABLED": "bool",
    "TOM_DISABLE_SEM_CTRL": "bool",
    "TOM_CANOPY_ENV_BIAS_ENABLED": "bool",
    "TOM_BG_PHYS_LOG": "bool",
    "TOM_BG_PHYS_SLO_GUARD": "bool",
    "TOM_ACTION_OPERATORS_ENABLED": "bool",
    "TOM_ACTION_DIVERGENCE_TEST": "bool",
    "TOM_SPAWN_AXIS_GAIN_ENABLED": "bool",
    "TOM_MEM_INFLUENCE_ENABLED": "bool",
    "TOM_MEM_INFLUENCE_COMPARE": "bool",
    "TOM_MEM_SUITE_USE_LLM": "bool",
    "TOM_MEM_EXTENDED": "bool",
    "TOM_TEST_FORCE_UNINITIALISED": "bool",
    "TOM_TEST_INJECT_MEMORY_WRITE": "bool",
    "TOM_TEST_INJECT_UNCITED": "bool",
    "TOM_TEST_INJECT_CONTRADICTION": "bool",
    "TOM_TEST_INJECT_GOAL_SUBSTITUTION": "bool",
    "TOM_TEST_INJECT_QUARANTINE_WRITE": "bool",
    "TOM_FORCE_NO_STRUCTURAL": "bool",
    "TOM_FORCE_NO_MEMORY": "bool",
    "TOM_FORCE_NO_TOOLS": "bool",
    "TOM_V1_SCHEMA_DEPRECATED": "bool",
    "TOM_SHADOW_RENDER_ENABLED": "bool",
    "TOM_PROPOSAL_MODE": "bool",
    "TOM_DISABLE_REGEX_EXTRACTION": "bool",
    "TOM_REGEX_SELF_REF_ROUTING": "bool",
    "TOM_NOURISHMENT_VALUATION_ENABLED": "bool",
    "TOM_REASONER_LIVE_SHADOW": "bool",
    "TOM_REASONER_LIVE_AUTHORITY_ADVISORY": "bool",
    "TOM_REASONER_LIVE_RELEASE_AUTHORITY": "bool",
    "TOM_REASONER_LIVE_HEAVY_THRESHOLD": "float",
    "TOM_HUNGER_DRIVE_ENABLED": "bool",
    "TOM_PHI_EFFORT_ENABLED": "bool",
    "TOM_SHADOW_REWARD_ENABLED": "bool",
    "TOM_SHADOW_REWARD_FELT_ENABLED": "bool",
    "TOM_AUTONOMIC_ENABLED": "bool",
    "TOM_AUTONOMIC_TENSION_SPAWN_GAIN": "float",
    "TOM_AUTONOMIC_FATIGUE_GROWTH_GAIN": "float",
    "TOM_AUTONOMIC_VITALITY_FLOOR_GAIN": "float",
    "TOM_AUTONOMIC_GROUNDEDNESS_BALANCE_GAIN": "float",
    "TOM_AUTONOMIC_CLARITY_BAND_GAIN": "float",
    "TOM_GOVERNANCE_ENABLED": "bool",
    "TOM_GOVERNANCE_BRIEF": "bool",
    "TOM_GOVERNANCE_VALIDATION": "bool",
    "TOM_GOVERNANCE_TURN_POLICY": "bool",
    "TOM_GOVERNANCE_EPISODE": "bool",
    "TOM_SCAFFOLD_AUTHORITY": "int",
    "TOM_SCAFFOLD_PLASTICITY": "bool",
    "TOM_VECTOR_VOICE_ENABLED": "bool",
    "TOM_REALISER_GREETINGS": "bool",
    "TOM_ENABLE_IDENTITY_BOOTSTRAP": "bool",
    "TOM_SEMANTIC_LOADS_DISABLED": "bool",
    "TOM_FEATURE_BANNER": "bool",
    "TOM_IDLE_AGE_REMINDER": "bool",
    "TOM_BRILLIANCE_HOOK_DISABLED": "bool",
    "TOM_ENABLE_SPATIAL_MEMORY": "bool",
    "TOM_DISABLE_TPM_BUCKET": "bool",
    "TOM_DISABLE_FLOCK": "bool",
    "TOM_LOCAL_LLM": "bool",
    "TOM_LOCAL_LLM_SMOKE": "bool",
    "TOM_STRICT_STATE_HASH": "bool",
    "TOM_SKIP_PERF_THRESHOLDS": "bool",
    "TOM_RUN_REAL_WORLD_EVAL_BATTERY": "bool",
    "TOM_WEBSEARCH_ENABLED": "bool",
    "TOM_FILEREAD_ENABLED": "bool",
    "TOM_SANDBOXEXEC_ENABLED": "bool",
    "TOM_AGENTIC_ENABLED": "bool",
    "TOM_AGENT_PLAN_EXECUTE": "bool",
    "TOM_AGENTIC_REQUIRE_APPROVAL": "bool",
    "TOM_AGENTIC_ISOLATED_MODE": "bool",
    "TOM_DIRECTIVE_CONSTRAINT_ENABLED": "bool",
    "TOM_DIRECTIVE_CONSTRAINT_ENABLE_VALIDATOR": "bool",
    "TOM_DIRECTIVE_CONSTRAINT_MAX_RETRIES": "int",
    "TOM_DIRECTIVE_CONSTRAINT_LOG_PASSTHROUGH": "bool",
    "TOM_DIRECT_CONTEXTUAL_17D_AUTHORITY_ENABLED": "bool",
    "TOM_BIASER_CARRIER_READOUT_ENABLED": "bool",
    "TOM_BIASER_AXIS_ALIGNMENT_WEIGHT": "float",
    "TOM_BIASER_POSTURE_ALIGNMENT_WEIGHT": "float",
    "TOM_LEAF_VEC_ENABLED": "bool",

    # Float values (leaf vec)
    "TOM_LEAF_VEC_RETRIEVAL_WEIGHT": "float",
    "TOM_LEAF_VEC_GROWTH_GAIN": "float",
    "TOM_LEAF_VEC_SPAWN_MIX": "float",
    "TOM_LEAF_VEC_PRUNE_AGE_BOOST": "float",

    # Integer values
    "TOM_NUM_CANDIDATES": "int",
    "TOM_MAX_DELIBERATION_ROUNDS": "int",
    "TOM_REVISE_TOP_N": "int",
    "TOM_MAX_REVISE_RETRIES": "int",
    "TOM_MIN_DELIB_ROUNDS": "int",
    "TOM_EVIDENCE_MAX_SPANS": "int",
    "TOM_EVIDENCE_CONTEXT_MAX_TOKENS": "int",
    "TOM_WARMUP_MIN_TICK": "int",
    "TOM_WARMUP_BALANCED_TICKS_REQUIRED": "int",
    "TOM_WARMUP_TICKS": "int",
    "TOM_BG_PHYS_TICKS": "int",
    "TOM_IDLE_AGE_MAX_TICKS": "int",
    "TOM_MEM_TICKS_PER_RUN": "int",
    "TOM_MEM_TARGET_BRANCHES": "int",
    "TOM_MEM_MAX_TICKS": "int",
    "TOM_MEM_OBS_EVERY": "int",
    "TOM_PENDING_EXPIRY_SECONDS": "int",
    "TOM_IDLE_AGE_REMINDER_DAYS": "int",
    "TOM_EVAL_PREHOLD_TICKS": "int",
    "TOM_MAX_LLM_CONCURRENCY": "int",
    "TOM_LLM_NUM_PREDICT": "int",
    "TOM_LLM_MAX_RETRIES": "int",
    "TOM_LLM_SEED": "int",
    "TOM_OLLAMA_N_PREDICT": "int",
    "TOM_OPENAI_TPM_LIMIT": "int",
    "TOM_OPENAI_TOKEN_ESTIMATE": "int",
    "TOM_SEM_TARGET_HOLD_QUANT_DECIMALS": "int",
    "TOM_WEBSEARCH_RATE_LIMIT": "int",
    "TOM_WEBSEARCH_MAX_RESULTS": "int",
    "TOM_FILEREAD_MAX_SIZE": "int",
    "TOM_SANDBOXEXEC_MAX_MEMORY": "int",
    "TOM_AGENTIC_RATE_LIMIT": "int",
    "TOM_LEAF_VEC_DECAY_HALF_LIFE": "int",

    # Float values
    "TOM_DELIBERATION_EASY_THRESH": "float",
    "TOM_MIN_GUARD_SCORE": "float",
    "TOM_SCORE_W_SEM": "float",
    "TOM_EPSILON_MEM": "float",
    "TOM_EPSILON_SEM": "float",
    "TOM_EPSILON_MARGIN": "float",
    "TOM_EPSILON_IMPROVE": "float",
    "TOM_GAMMA_DIMINISH": "float",
    "TOM_DELIB_REINFORCEMENT": "float",
    "TOM_ESEM_MISSING": "float",
    "TOM_EVIDENCE_PROVIDER_TIMEOUT": "float",
    "TOM_WARMUP_BALANCE_TOLERANCE": "float",
    "TOM_WARMUP_ROTATION_STEP": "float",
    "TOM_LEAF_ALPHA": "float",
    "TOM_LEAF_BETA": "float",
    "TOM_BETA_SEM": "float",
    "TOM_KAPPA_SEMANTIC_GAIN": "float",
    "TOM_TAU_BLEND_ALPHA_MAX": "float",
    "TOM_CANOPY_IMBALANCE_LOW": "float",
    "TOM_CANOPY_IMBALANCE_HIGH": "float",
    "TOM_BG_PHYS_MAX_MS": "float",
    "TOM_IDLE_AGE_TICKS_PER_SEC": "float",
    "TOM_DRIFT_THRESHOLD": "float",
    "TOM_MOCK_CONFIDENCE": "float",
    "TOM_LLM_TIMEOUT_S": "float",
    "TOM_LLM_TEMPERATURE": "float",
    "TOM_OLLAMA_TIMEOUT": "float",
    "TOM_OLLAMA_TEMPERATURE": "float",
    "TOM_WEBSEARCH_TIMEOUT": "float",
    "TOM_FILEREAD_TIMEOUT": "float",
    "TOM_SANDBOXEXEC_TIMEOUT": "float",
    "TOM_AGENTIC_THRESHOLD": "float",
    "TOM_LEAF_VEC_ALPHA": "float",
    "TOM_LEAF_VEC_CONFIDENCE_GATE": "float",
    "TOM_RESIDUE_GATE_TOP_K": "int",
    "TOM_RESIDUE_ALPHA_BOUNDED": "bool",
    "TOM_MSR_MAGNITUDE_REF_RMS": "float",
    "TOM_DEPOSITION_CONDUCTION_SHARE": "float",
    "TOM_DISTRICT_OWNED_PENALTY": "float",
    "TOM_DISTRICT_RECRUITMENT_OCCUPANCY_PENALTY": "float",
    "TOM_DISTRICT_OWN_TAU": "float",
    "TOM_DISTRICT_EXCLUSION_STRENGTH": "float",
    "TOM_DISTRICT_OWNER_ALPHA": "float",
    "TOM_DISTRICT_OWNER_ALPHA_MODE": "str",
    "TOM_DISTRICT_OWNER_ALPHA_FLOOR": "float",
    "TOM_DISTRICT_STALE_HORIZON": "int",
    "TOM_DISTRICT_PROTECTION_GAIN": "float",
    "TOM_DISTRICT_STALE_STRENGTH_DECAY": "float",
    "TOM_DISTRICT_CONTENT_SOURCE": "str",
    "TOM_MSR_REFERENCE_LOAD_ENABLED": "bool",
    "TOM_MSR_REFERENCE_LOAD_EPSILON_REF": "float",
    "TOM_MSR_REFERENCE_LOAD_NAMED_WEIGHT": "float",
    "TOM_MSR_REFERENCE_LOAD_COMMON_WEIGHT": "float",
    "TOM_MSR_REFERENCE_LOAD_CONFIDENCE_DIM_SCALE": "float",
    "TOM_MSR_REFERENCE_LOAD_HASH_KEY": "str",
    "TOM_MSR_REFERENCE_LOAD_MAX_REFERENTS": "int",
    "TOM_DISTRICT_ROUTING_SOURCE": "str",
    "TOM_DISTRICT_IMPRINT_GATE_17D": "bool",
    "TOM_DISTRICT_IMPRINT_GATE_17D_TOP_K": "int",
    "TOM_NOURISHMENT_VALUATION_KP": "float",
    "TOM_NOURISHMENT_VALUATION_KE": "float",
    "TOM_VECTOR_VOICE_EMA_ALPHA": "float",
    "TOM_REALISER_TEMPERATURE": "float",
    "TOM_REALISER_TIMEOUT_S": "float",
    "TOM_AGENT_LLM_TEMPERATURE": "float",
    "TOM_AGENT_LLM_TIMEOUT_S": "float",

    # Realiser
    "TOM_REALISER_MAX_TOKENS": "int",

    # Agent LLM
    "TOM_AGENT_LLM_MAX_TOKENS": "int",

    # Document ingestion
    "TOM_DOC_MAX_SIZE_BYTES": "int",
    "TOM_DOC_MAX_FILES_SCAN": "int",
    "TOM_DOC_MAX_ANCHORS": "int",

    # Finite Geometry Retriever
    "TOM_FGR_ENABLED": "bool",
    "TOM_FGR_POOL_PER_SOURCE": "int",
    "TOM_FGR_AXIS_BALANCE": "bool",
    "TOM_FGR_LATENCY_BUDGET_MS": "int",
    # TOM_FGR_CHANNEL_WEIGHTS is a string ("1.0,1.5,1.2")

    # Suite runner (Phase 3 hardening)
    "TOM_SUITE_TIMEOUT_SECONDS": "int",
    "TOM_SUITE_MAX_TICKS": "int",
    "TOM_SUITE_FAIL_FAST": "bool",
    "TOM_SHUTDOWN_TIMEOUT": "int",

    # SICD growth budget (Phase 2 stabilization + D3)
    "TOM_SPAWN_SOFT_CAP": "int",
    "TOM_SPAWN_HARD_CAP": "int",
    "TOM_SPAWN_BUDGET_BASE": "float",
    "TOM_SPAWN_COST_BASE": "float",
    "TOM_ROOT_RESERVE_ENABLED": "bool",
    "TOM_LEAF_CAPTURE_GAIN": "float",
    "TOM_LEAF_CAPTURE_CAP": "float",
    "TOM_LEAF_FACTOR_FLOOR": "float",
    "TOM_ROOT_SUPPLY_BASE": "float",
    "TOM_ROOT_CAP_PER_BRANCH": "float",
    "TOM_ROOT_DEPOSIT_FRACTION": "float",
    "TOM_ROOT_OVERFLOW_FRACTION": "float",
    "TOM_ROOT_RELEASE_RATE": "float",
    "TOM_ROOT_MAINT_REDUCTION": "float",
    "TOM_ROOT_CAPACITY_BOOST": "float",
    "TOM_ROOT_DECAY": "float",
    "TOM_BRANCH_CAPACITY": "int",
    # D3-T: Transport controller
    "TOM_TRANSPORT_ENABLED": "bool",
    "TOM_TRANSPORT_A": "float",
    "TOM_TRANSPORT_KN": "float",
    "TOM_TRANSPORT_KL": "float",
    "TOM_TRANSPORT_R_LOW": "float",
    "TOM_TRANSPORT_R_HIGH": "float",
    "TOM_TRANSPORT_GRACE_TICKS": "int",
    "TOM_TRANSPORT_RAMP_RATE": "float",
    "TOM_TRANSPORT_BOOST_MAX": "float",
    "TOM_TRANSPORT_SLEW_RATE": "float",

    # Tree growth config
    "TOM_TAU1": "float",

    # SICD kappa tuning (Phase 2 stabilization)
    "TOM_MIN_METABOLIC_FRACTION": "float",
    "TOM_NOURISH_EMA_FLOOR": "float",
    "TOM_KAPPA_RECOVERY_THRESH": "float",
    "TOM_ALLOCATION_UNIFORM_MIX": "float",

    # Energy fallback
    "TOM_ENERGY_FALLBACK_ENABLED": "bool",
    "TOM_ENERGY_FALLBACK_DECAY_RATE": "float",
    "TOM_ENERGY_FALLBACK_BASELINE_DEFAULT": "float",
    "TOM_ENERGY_FALLBACK_BASELINE_STILLNESS": "float",
    "TOM_ENERGY_FALLBACK_BASELINE_REFLECT": "float",
    "TOM_ENERGY_FALLBACK_BASELINE_ACT": "float",
    "TOM_ENERGY_FALLBACK_BASELINE_NORMAL": "float",
    "TOM_ENERGY_FALLBACK_BASELINE_SANDBOX": "float",
    "TOM_ENERGY_FALLBACK_BASELINE_REFLECTION": "float",
    "TOM_ENERGY_FALLBACK_BASELINE_EMERGENCY": "float",

    # Action learning
    "TOM_ACTION_LEARNING_ENABLED": "bool",
    "TOM_ACTION_LEARNING_MIN_CONFIDENCE": "float",
    "TOM_ACTION_LEARNING_MIN_CONSISTENCY": "int",
    "TOM_ACTION_LEARNING_MAX_PER_SESSION": "int",
    "TOM_ACTION_LEARNING_MAX_STORE": "int",
    "TOM_ACTION_LEARNING_RETRIEVAL_WEIGHT": "float",
    "TOM_ACTION_LEARNING_RETRIEVAL_MAX": "int",
    "TOM_ACTION_LEARNING_SUCCESS_STRENGTH": "float",
    "TOM_ACTION_LEARNING_FAILURE_STRENGTH": "float",
    "TOM_ACTION_LEARNING_TTL_DAYS": "int",

    # Organism biaser (Route B paired-session override). TOM_BIASER_MODE
    # parses as string (left out — default str). TOM_BIASER_ALPHA is a
    # float in [0, 1]. TOM_BIASER_W_V_OVERRIDE and TOM_BIASER_W_E_OVERRIDE
    # parse as float; empty string is treated as None by the consumer.
    "TOM_BIASER_ALPHA": "float",
    "TOM_BIASER_W_V_OVERRIDE": "float",
    "TOM_BIASER_W_E_OVERRIDE": "float",

    # Phase A.8.1 organism runtime override (Ken 2026-04-28). Empty string
    # is treated as None / unset by the consumer.
    "TOM_SPAWN_CREDIT_CAP": "float",

    # String values (default type, no need to list all)
}


def get_env_var_type(env_var: str) -> str:
    """Get the type of an environment variable for parsing."""
    return ENV_VAR_TYPES.get(env_var, "str")


def parse_env_value(env_var: str, value: str) -> object:
    """Parse an environment variable value to its appropriate type."""
    var_type = get_env_var_type(env_var)

    if var_type == "bool":
        return value.strip().lower() in ("1", "true", "yes", "on")
    elif var_type == "int":
        try:
            return int(value.strip())
        except ValueError:
            return value
    elif var_type == "float":
        try:
            return float(value.strip())
        except ValueError:
            return value
    else:
        return value
