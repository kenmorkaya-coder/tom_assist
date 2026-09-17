"""
Backward-Compatible Configuration Accessors.

This module provides config-aware getters that:
1. Try to read from the unified config system first
2. Fall back to environment variables for backward compatibility
3. Support type conversion and defaults

Usage:
    from config.compat import get_config_value, get_bool, get_int, get_float

    # Gets from config first, falls back to TOM_LLM_PROVIDER env var
    provider = get_config_value("llm.provider", "TOM_LLM_PROVIDER", default="openai")

    # Type-specific helpers
    enabled = get_bool("deliberation.enabled", "TOM_DELIBERATION_ENABLED", default=False)
    threshold = get_float("drift.threshold_block", "TOM_DRIFT_THRESHOLD", default=0.70)
    num = get_int("deliberation.num_candidates", "TOM_NUM_CANDIDATES", default=8)

This allows gradual migration: code can start using these helpers, and they
will transparently read from the config system when available while preserving
env var fallback.
"""

from __future__ import annotations

import os
from typing import Any, Optional, TypeVar, Union

T = TypeVar("T")

# Module-level cache for loaded config
_config_cache: Optional[dict] = None
_config_loaded: bool = False


def _load_config() -> dict:
    """Load config once and cache it."""
    global _config_cache, _config_loaded

    if _config_loaded:
        return _config_cache or {}

    try:
        from gateway.vendor.rgm17d.config.loader import load_config
        _config_cache = load_config()
        _config_loaded = True
    except Exception:
        _config_cache = {}
        _config_loaded = True

    return _config_cache or {}


def _get_nested(d: dict, path: str, default: Any = None) -> Any:
    """Get nested value from dict using dot-separated path."""
    if not d:
        return default

    parts = path.split(".")
    current = d
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _set_nested(d: dict, path: str, value: Any) -> None:
    """Set a nested value in dict using dot-separated path."""
    parts = path.split(".")
    current = d
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def set_config_value(config_path: str, value: Any) -> None:
    """
    Set a value in the config cache (runtime override).

    Subsequent calls to get_config_value / get_bool will return this value
    since the config cache has highest precedence.
    """
    config = _load_config()
    _set_nested(config, config_path, value)


def get_config_value(
    config_path: str,
    env_var: Optional[str] = None,
    default: Any = None,
) -> Any:
    """
    Get a configuration value with env var fallback.

    Order of precedence:
    1. Config system (if available and has value)
    2. Environment variable (if specified and set)
    3. Default value

    Args:
        config_path: Dot-separated path in config (e.g., "llm.provider")
        env_var: Environment variable name to fall back to (e.g., "TOM_LLM_PROVIDER")
        default: Default value if not found in config or env

    Returns:
        The configuration value
    """
    # Try config first
    config = _load_config()
    value = _get_nested(config, config_path)
    if value is not None:
        return value

    # Fall back to env var
    if env_var:
        env_value = os.getenv(env_var)
        if env_value is not None:
            return env_value

    return default


def get_bool(
    config_path: str,
    env_var: Optional[str] = None,
    default: bool = False,
) -> bool:
    """
    Get a boolean configuration value.

    For env vars, recognizes: "1", "true", "yes", "on" as True (case-insensitive)
    """
    value = get_config_value(config_path, env_var, default=None)

    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")

    return bool(value)


def get_int(
    config_path: str,
    env_var: Optional[str] = None,
    default: int = 0,
) -> int:
    """Get an integer configuration value."""
    value = get_config_value(config_path, env_var, default=None)

    if value is None:
        return default

    if isinstance(value, int):
        return value

    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return default


def get_float(
    config_path: str,
    env_var: Optional[str] = None,
    default: float = 0.0,
) -> float:
    """Get a float configuration value."""
    value = get_config_value(config_path, env_var, default=None)

    if value is None:
        return default

    if isinstance(value, (int, float)):
        return float(value)

    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return default


def get_str(
    config_path: str,
    env_var: Optional[str] = None,
    default: str = "",
) -> str:
    """Get a string configuration value."""
    value = get_config_value(config_path, env_var, default=None)

    if value is None:
        return default

    return str(value).strip()


def _empty_or_none(value: Any) -> bool:
    """True iff value is None or an empty string after strip."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def resolve_biaser_overrides() -> dict:
    """Return organism biaser config overrides for fields whose env vars are
    set (non-empty) at call time.

    The unified config tree is consulted for parsed values, but the
    decision of WHETHER to override is gated on the env var being
    explicitly set — the cached tree mixes env-set and default values,
    and we must only override fields the operator deliberately set.

    Reads through standard paths registered in config/env_mapping.py so
    config-dump source tracking sees these vars. The dataclass itself
    does not read os.environ; the override is applied at the call site
    (controller seam) via dataclasses.replace.

    Validation: biaser_mode must be in {"off", "shadow", "biaser"} —
    raises ValueError on invalid mode (fails closed at config-load time
    rather than silently enabling an unknown mode).

    Returns:
        Dict suitable for dataclasses.replace(OrganismRewardConfig(),
        **overrides). Empty dict means no env overrides — defaults used.
    """
    _ALLOWED_MODES = frozenset({"off", "shadow", "biaser"})
    overrides: dict = {}

    def _env_set(name: str) -> bool:
        v = os.environ.get(name)
        return v is not None and v.strip() != ""

    if _env_set("TOM_BIASER_MODE"):
        # Read parsed value from the unified config tree (source-tracked
        # via env_mapping.py) instead of os.environ directly.
        mode_value = get_config_value(
            "tunable.organism_reward.biaser_mode",
            env_var="TOM_BIASER_MODE", default=None,
        )
        if mode_value is not None:
            mode_str = str(mode_value).strip()
            if mode_str not in _ALLOWED_MODES:
                raise ValueError(
                    f"TOM_BIASER_MODE={mode_str!r} is not allowed. "
                    f"Must be one of {sorted(_ALLOWED_MODES)}. "
                    "Validation fails closed: invalid mode is rejected "
                    "at config load time rather than silently enabling "
                    "an unknown mode."
                )
            overrides["biaser_mode"] = mode_str

    if _env_set("TOM_BIASER_ALPHA"):
        alpha_value = get_config_value(
            "tunable.organism_reward.biaser_alpha",
            env_var="TOM_BIASER_ALPHA", default=None,
        )
        if alpha_value is not None:
            try:
                overrides["biaser_alpha"] = float(alpha_value)
            except (TypeError, ValueError):
                pass

    for field_name, env_name in (
        ("biaser_w_V_override", "TOM_BIASER_W_V_OVERRIDE"),
        ("biaser_w_E_override", "TOM_BIASER_W_E_OVERRIDE"),
    ):
        if not _env_set(env_name):
            continue
        raw = get_config_value(
            f"tunable.organism_reward.{field_name}",
            env_var=env_name, default=None,
        )
        if raw is None:
            continue
        try:
            overrides[field_name] = float(raw)
        except (TypeError, ValueError):
            pass

    # Stage B of the throat plan (§8) — carrier/readout gate + weights.
    # These are read here so the existing apply_biaser_overrides() pipeline
    # carries them into the live OrganismRewardConfig the controller seam
    # passes into shadow_step → apply_biaser_to_decomposition.
    if _env_set("TOM_BIASER_CARRIER_READOUT_ENABLED"):
        raw = get_config_value(
            "tunable.organism_reward.enable_carrier_readout_signals",
            env_var="TOM_BIASER_CARRIER_READOUT_ENABLED", default=None,
        )
        if raw is not None:
            if isinstance(raw, bool):
                overrides["enable_carrier_readout_signals"] = raw
            elif isinstance(raw, str):
                overrides["enable_carrier_readout_signals"] = (
                    raw.strip().lower() in ("1", "true", "yes", "on")
                )
            else:
                overrides["enable_carrier_readout_signals"] = bool(raw)

    for field_name, env_name in (
        ("axis_alignment_weight", "TOM_BIASER_AXIS_ALIGNMENT_WEIGHT"),
        ("posture_alignment_weight", "TOM_BIASER_POSTURE_ALIGNMENT_WEIGHT"),
    ):
        if not _env_set(env_name):
            continue
        raw = get_config_value(
            f"tunable.organism_reward.{field_name}",
            env_var=env_name, default=None,
        )
        if raw is None:
            continue
        try:
            overrides[field_name] = float(raw)
        except (TypeError, ValueError):
            pass

    return overrides


def apply_biaser_overrides(config: Any) -> Any:
    """Return a copy of `config` with TOM_BIASER_* env-driven overrides applied.

    Convenience wrapper around dataclasses.replace + resolve_biaser_overrides.
    If no overrides are set, returns the input unchanged.
    """
    overrides = resolve_biaser_overrides()
    if not overrides:
        return config
    import dataclasses as _dc
    return _dc.replace(config, **overrides)


# ---------------------------------------------------------------------------
# Phase A.8.1 — organism runtime overrides (parallel to biaser overrides)
# ---------------------------------------------------------------------------

def resolve_organism_runtime_overrides() -> dict:
    """Return organism runtime config overrides for fields whose env vars
    are set (non-empty) at call time.

    Phase A.8.1 (LIVE_ORGANISM_RECOVERY_SPEC.md, Ken 2026-04-28): runtime
    override path for organism calibration knobs (e.g. spawn_credit_cap)
    that should be tunable during live capture WITHOUT flipping the
    production default in OrganismRewardConfig.

    Distinct from resolve_biaser_overrides() — this helper is for organism
    state-extraction / scoring calibration knobs (currently spawn_credit_cap),
    not biaser-mode/blend fields. Two helpers exist to keep the doctrinal
    separation clear: biaser overrides shape ROUTING; organism runtime
    overrides shape STATE-EXTRACTION SCALES.

    Validation: spawn_credit_cap must be a positive float — fails closed
    on negative or non-numeric values.

    Returns:
        Dict suitable for dataclasses.replace(OrganismRewardConfig(),
        **overrides). Empty dict means no env overrides — defaults used.
    """
    overrides: dict = {}

    def _env_set(name: str) -> bool:
        v = os.environ.get(name)
        return v is not None and v.strip() != ""

    if _env_set("TOM_SPAWN_CREDIT_CAP"):
        raw = get_config_value(
            "tunable.organism_reward.spawn_credit_cap",
            env_var="TOM_SPAWN_CREDIT_CAP", default=None,
        )
        if raw is not None:
            try:
                cap_value = float(raw)
            except (TypeError, ValueError):
                raise ValueError(
                    f"TOM_SPAWN_CREDIT_CAP={raw!r} is not a valid float. "
                    "Validation fails closed: invalid cap is rejected at "
                    "config load time rather than producing undefined "
                    "extractor behaviour."
                )
            if cap_value <= 0.0:
                raise ValueError(
                    f"TOM_SPAWN_CREDIT_CAP={cap_value} must be > 0. "
                    "extract_O divides by this value; non-positive caps "
                    "would produce divide-by-zero or negative O. "
                    "Validation fails closed."
                )
            overrides["spawn_credit_cap"] = cap_value

    return overrides


def apply_organism_runtime_overrides(config: Any) -> Any:
    """Return a copy of `config` with organism runtime env-driven overrides
    applied (currently TOM_SPAWN_CREDIT_CAP).

    Convenience wrapper around dataclasses.replace +
    resolve_organism_runtime_overrides. If no overrides are set, returns
    the input unchanged.
    """
    overrides = resolve_organism_runtime_overrides()
    if not overrides:
        return config
    import dataclasses as _dc
    return _dc.replace(config, **overrides)


# ---------------------------------------------------------------------------
# Phase A.8 Step 9 — V6 bounded-opportunism promotion overrides
# (V6_BOUNDED_OPPORTUNISM_PROMOTION_SPEC.md §3.1.4)
# ---------------------------------------------------------------------------

# Allowed values for the promotion env vars. Mirrors
# OrganismRewardConfig._ALLOWED_CONSEQUENCE_RULES_VERSIONS so override-time
# validation matches dataclass-construction-time validation.
_PROMOTION_ALLOWED_FEATURE_VERSIONS = frozenset({
    "v3_nourishment", "v6_plastic_memory",
})
_PROMOTION_ALLOWED_CONSEQUENCE_RULES_VERSIONS = frozenset({
    "v3", "v6", "v6_bounded_opportunism",
})


def resolve_promotion_overrides() -> dict:
    """Return promotion env-var overrides for OrganismRewardConfig.

    Phase A.8 Step 9 (V6_BOUNDED_OPPORTUNISM_PROMOTION_SPEC.md §3.1.4):
    rollback path uses TOM_FEATURE_VERSION + TOM_CONSEQUENCE_RULES_VERSION
    to flip the runtime tags back to V3 or conservative V6 without a
    redeployment. Both vars validate fail-closed against the allowed sets;
    invalid values raise at config load time rather than silently
    enabling an unknown configuration.

    TOM_FORWARD_MODEL_PATH is NOT consumed here — it is read directly by
    `agency.organism.shadow_hook.DEFAULT_MODEL_PATH` at module-import time
    (see spec §3.1.3), since the model path is not an
    OrganismRewardConfig field.

    Returns:
        Dict suitable for dataclasses.replace(OrganismRewardConfig(),
        **overrides). Empty dict means no env overrides — defaults used.
    """
    overrides: dict = {}

    def _env_set(name: str) -> bool:
        v = os.environ.get(name)
        return v is not None and v.strip() != ""

    if _env_set("TOM_FEATURE_VERSION"):
        raw = get_config_value(
            "tunable.organism_reward.feature_version",
            env_var="TOM_FEATURE_VERSION", default=None,
        )
        if raw is not None:
            value = str(raw).strip()
            if value not in _PROMOTION_ALLOWED_FEATURE_VERSIONS:
                raise ValueError(
                    f"TOM_FEATURE_VERSION={value!r} is not allowed. "
                    f"Must be one of "
                    f"{sorted(_PROMOTION_ALLOWED_FEATURE_VERSIONS)}. "
                    "Validation fails closed per "
                    "V6_BOUNDED_OPPORTUNISM_PROMOTION_SPEC.md §3.1.4 — "
                    "an unknown feature_version would silently mis-route "
                    "selector and extractor calls."
                )
            overrides["feature_version"] = value

    if _env_set("TOM_CONSEQUENCE_RULES_VERSION"):
        raw = get_config_value(
            "tunable.organism_reward.consequence_rules_version",
            env_var="TOM_CONSEQUENCE_RULES_VERSION", default=None,
        )
        if raw is not None:
            value = str(raw).strip()
            if (
                value
                not in _PROMOTION_ALLOWED_CONSEQUENCE_RULES_VERSIONS
            ):
                raise ValueError(
                    f"TOM_CONSEQUENCE_RULES_VERSION={value!r} is not "
                    f"allowed. Must be one of "
                    f"{sorted(_PROMOTION_ALLOWED_CONSEQUENCE_RULES_VERSIONS)}. "
                    "Validation fails closed per "
                    "V6_BOUNDED_OPPORTUNISM_PROMOTION_SPEC.md §3.1.4 — "
                    "an unknown rule-table tag would mis-attribute audit "
                    "rows and break ShadowHook's load-time provenance check."
                )
            overrides["consequence_rules_version"] = value

    return overrides


def apply_promotion_overrides(config: Any) -> Any:
    """Return a copy of `config` with TOM_FEATURE_VERSION /
    TOM_CONSEQUENCE_RULES_VERSION env-driven overrides applied.

    Convenience wrapper around dataclasses.replace +
    resolve_promotion_overrides. If no overrides are set, returns the
    input unchanged. Per spec §5.2 rollback procedure: setting both env
    vars to V3 / conservative-V6 values redirects runtime config without
    a code redeployment.
    """
    overrides = resolve_promotion_overrides()
    if not overrides:
        return config
    import dataclasses as _dc
    return _dc.replace(config, **overrides)


def reset_config_cache() -> None:
    """Reset the config cache (useful for testing)."""
    global _config_cache, _config_loaded
    _config_cache = None
    _config_loaded = False


def set_config_cache(config: dict) -> None:
    """Set the config cache explicitly (for profile loading).

    This allows commands.py to pre-load a profile and have all
    downstream code use the same config without re-loading.

    Args:
        config: The loaded configuration dict
    """
    global _config_cache, _config_loaded
    _config_cache = config
    _config_loaded = True


# Track env keys injected by _inject_profile_env for cleanup on profile switch
_injected_env_keys: set = set()


def _inject_profile_env(profile: str) -> None:
    """Inject companion .env vars into os.environ for dataclass factories.

    Dataclasses like KappaUpdateConfig use field(default_factory=lambda:
    _env_float("TOM_*", default)) which reads os.environ directly.
    This injection ensures those factories see profile .env values.

    Tracks injected keys so they can be cleaned up on profile switch
    (prevents cross-profile leakage).
    """
    global _injected_env_keys
    import os
    from pathlib import Path

    # Clean up keys injected by a previous profile load
    for key in _injected_env_keys:
        if key in os.environ:
            del os.environ[key]
    _injected_env_keys = set()

    env_path = Path(__file__).parent / "profiles" / f"{profile}.env"
    if not env_path.exists():
        return

    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:]
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if not key:
                continue
            os.environ[key] = value
            _injected_env_keys.add(key)


def load_profile(profile: str) -> dict:
    """Load a config profile and set it as the active config.

    This is the main entry point for profile-based configuration.
    Call this early in the application startup to set the config
    that all compat helpers will use.

    Dual-path loading:
    - Path 1 (config dict): ConfigLoader parses .env → config dict
    - Path 2 (process env): _inject_profile_env sets os.environ for
      dataclass _env_float factories

    Args:
        profile: Profile name (local, ci, test, prod-like, profile_2k)

    Returns:
        The loaded configuration dict

    Raises:
        FileNotFoundError: If profile doesn't exist
    """
    global _config_cache, _config_loaded

    # Path 2: inject .env into os.environ for dataclass factories
    _inject_profile_env(profile)

    try:
        from gateway.vendor.rgm17d.config.loader import load_config
        _config_cache = load_config(profile=profile)
        _config_loaded = True
        return _config_cache
    except Exception as e:
        # On error, reset to allow fallback to env vars
        _config_cache = {}
        _config_loaded = True
        raise


# Convenience aliases for common patterns
def get_llm_provider(default: str = "openai") -> str:
    """Get LLM provider setting."""
    return get_str("llm.provider", "TOM_LLM_PROVIDER", default).lower()


def get_llm_model(default: str = "") -> str:
    """Get LLM model setting."""
    return get_str("llm.model", "TOM_LLM_MODEL", default)


def get_llm_base_url(default: str = "") -> str:
    """Get LLM base URL setting."""
    return get_str("llm.base_url", "TOM_LLM_BASE_URL", default)


def get_llm_timeout(default: float = 120.0) -> float:
    """Get LLM timeout setting."""
    return get_float("llm.timeout_seconds", "TOM_LLM_TIMEOUT_S", default)


def get_drift_threshold(default: float = 0.70) -> float:
    """Get drift threshold setting."""
    return get_float("drift.threshold_block", "TOM_DRIFT_THRESHOLD", default)


def is_deliberation_enabled(default: bool = False) -> bool:
    """DEPRECATED: no call sites. Read controller.cfg.drift_control.enable_deliberation directly."""
    import warnings
    warnings.warn("is_deliberation_enabled() is deprecated and has no callers", DeprecationWarning, stacklevel=2)
    return get_bool("deliberation.enabled", "TOM_DELIBERATION_ENABLED", default)


def get_num_candidates(default: int = 8) -> int:
    """Get number of deliberation candidates."""
    return get_int("deliberation.num_candidates", "TOM_NUM_CANDIDATES", default)


# LLM-specific helpers for openai_client.py migration
def get_llm_api_key(default: str = "") -> str:
    """Get LLM API key (TOM_LLM_API_KEY or OPENAI_API_KEY fallback)."""
    # Try TOM_LLM_API_KEY first via config, then env var fallback
    value = get_str("llm.api_key", "TOM_LLM_API_KEY", default="")
    if value:
        return value
    # Direct env var fallback for OPENAI_API_KEY (not in config mapping)
    import os
    return os.getenv("OPENAI_API_KEY", default)


def get_llm_temperature(default: float | None = None) -> float | None:
    """Get LLM temperature setting (None means model default)."""
    value = get_config_value("llm.temperature", "TOM_LLM_TEMPERATURE", default=None)
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def get_llm_num_predict(default: int = 4096) -> int:
    """Get LLM max output tokens setting."""
    return get_int("llm.num_predict", "TOM_LLM_NUM_PREDICT", default)


def get_llm_reasoning_effort(default: str = "") -> str:
    """Get LLM reasoning effort for reasoning models (low, medium, high)."""
    value = get_str("llm.reasoning_effort", "TOM_LLM_REASONING_EFFORT", default)
    if value and value.lower() in ("low", "medium", "high"):
        return value.lower()
    return ""


def get_llm_max_concurrency(default: int = 1) -> int:
    """Get max LLM concurrency setting."""
    return get_int("llm.max_concurrency", "TOM_MAX_LLM_CONCURRENCY", default)


def get_agent_plan_execute(default: bool = False) -> bool:
    """Enable plan-then-execute flow for the agentic chat path."""
    return get_bool("llm.agent_plan_execute", "TOM_AGENT_PLAN_EXECUTE", default)


def is_flock_disabled(default: bool = False) -> bool:
    """Check if flock-based locking is disabled."""
    return get_bool("llm.disable_flock", "TOM_DISABLE_FLOCK", default)


def is_tpm_bucket_disabled(default: bool = False) -> bool:
    """Check if TPM bucket rate limiting is disabled."""
    return get_bool("llm.disable_tpm_bucket", "TOM_DISABLE_TPM_BUCKET", default)


def get_openai_tpm_limit(default: int = 150000) -> int:
    """Get OpenAI TPM (tokens per minute) limit."""
    return get_int("llm.openai_tpm_limit", "TOM_OPENAI_TPM_LIMIT", default)


def get_openai_token_estimate(default: int = 120000) -> int:
    """Get estimated tokens per OpenAI request."""
    return get_int("llm.openai_token_estimate", "TOM_OPENAI_TOKEN_ESTIMATE", default)


def get_llm_seed(default: int | None = None) -> int | None:
    """Get LLM seed for deterministic generation (None means random)."""
    value = get_config_value("llm.seed", "TOM_LLM_SEED", default=None)
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# Controller-specific helpers for tom_controller.py migration
def get_warmup_balance_tolerance(default: float = 0.05) -> float:
    """Get warmup balance tolerance."""
    return get_float("controller.warmup_balance_tolerance", "TOM_WARMUP_BALANCE_TOLERANCE", default)


def get_warmup_balanced_ticks(default: int = 5) -> int:
    """Get warmup balanced ticks required."""
    return get_int("controller.warmup_balanced_ticks", "TOM_WARMUP_BALANCED_TICKS", default)


def get_warmup_min_tick(default: int = 2000) -> int:
    """Get minimum tick before warmup can complete."""
    return get_int("controller.warmup_min_tick", "TOM_WARMUP_MIN_TICK", default)


def get_warmup_rotation_step(default: float = 0.381966) -> float:
    """Get warmup rotation step (default: golden angle)."""
    return get_float("controller.warmup_rotation_step", "TOM_WARMUP_ROTATION_STEP", default)


def get_evidence_max_spans(default: int = 8) -> int:
    """Get max evidence spans."""
    return get_int("evidence.max_spans", "TOM_EVIDENCE_MAX_SPANS", default)


def get_evidence_context_max_tokens(default: int = 2200) -> int:
    """Get max tokens for evidence context."""
    return get_int("evidence.context_max_tokens", "TOM_EVIDENCE_CONTEXT_MAX_TOKENS", default)


def is_force_no_structural(default: bool = False) -> bool:
    """Check if structural changes are force-disabled."""
    return get_bool("feature_flags.force_no_structural", "TOM_FORCE_NO_STRUCTURAL", default)


def is_force_no_memory(default: bool = False) -> bool:
    """Check if memory writes are force-disabled."""
    return get_bool("feature_flags.force_no_memory", "TOM_FORCE_NO_MEMORY", default)


def is_force_no_tools(default: bool = False) -> bool:
    """Check if tool execution is force-disabled."""
    return get_bool("feature_flags.force_no_tools", "TOM_FORCE_NO_TOOLS", default)


def is_drift_require_citations(default: bool = False) -> bool:
    """Check if citations are required for drift."""
    return get_bool("drift.require_citations", "TOM_DRIFT_REQUIRE_CITATIONS", default)


def get_policy_version(default: str = "unknown") -> str:
    """Get policy version string."""
    return get_str("policy.version", "TOM_POLICY_VERSION", default)


# Coupling/Handshake controller helpers
def is_verification_gate_enabled(default: bool = False) -> bool:
    """Check if verification gate is enabled."""
    return get_bool("coupling.verification_gate_enabled", "TOM_VERIFICATION_GATE_ENABLED", default)


def get_max_revise_retries(default: int = 2) -> int:
    """Get max revise retries."""
    return get_int("coupling.max_revise_retries", "TOM_MAX_REVISE_RETRIES", default)


def get_deliberation_easy_threshold(default: float = 0.85) -> float:
    """Get deliberation easy threshold (skip deliberation above this)."""
    return get_float("deliberation.easy_threshold", "TOM_DELIBERATION_EASY_THRESH", default)


def is_test_force_uninitialised(default: bool = False) -> bool:
    """Check if force uninitialised state is enabled (for testing)."""
    return get_bool("testing.force_uninitialised", "TOM_TEST_FORCE_UNINITIALISED", default)


def is_force_coupling(default: bool = False) -> bool:
    """Check if coupling is force-enabled in danger state."""
    return get_bool("coupling.force_coupling", "TOM_FORCE_COUPLING", default)


def is_allow_defer(default: bool = False) -> bool:
    """Check if defer is allowed."""
    return get_bool("coupling.allow_defer", "TOM_ALLOW_DEFER", default)


# Orchestrator helpers
def is_action_divergence_test(default: bool = False) -> bool:
    """Check if action divergence test mode is enabled."""
    return get_bool("testing.action_divergence_test", "TOM_ACTION_DIVERGENCE_TEST", default)


def get_canopy_imbalance_low(default: float = 0.05) -> float:
    """Get canopy imbalance low threshold."""
    return get_float("canopy.imbalance_low", "TOM_CANOPY_IMBALANCE_LOW", default)


def get_canopy_imbalance_high(default: float = 0.15) -> float:
    """Get canopy imbalance high threshold."""
    return get_float("canopy.imbalance_high", "TOM_CANOPY_IMBALANCE_HIGH", default)


# Chat adapter helpers
def is_shadow_render_enabled(default: bool = False) -> bool:
    """Check if shadow render is enabled."""
    return get_bool("chat.shadow_render_enabled", "TOM_SHADOW_RENDER_ENABLED", default)


def is_proposal_mode_enabled(default: bool = False) -> bool:
    """Check if proposal mode is enabled."""
    return get_bool("chat.proposal_mode", "TOM_PROPOSAL_MODE", default)


def is_regex_extraction_disabled(default: bool = False) -> bool:
    """Check if regex extraction is disabled."""
    return get_bool("chat.disable_regex_extraction", "TOM_DISABLE_REGEX_EXTRACTION", default)


def get_beta_sem(default: str = "") -> str:
    """Get beta semantic value (empty string = not set)."""
    return get_str("chat.beta_sem", "TOM_BETA_SEM", default)


def is_semantic_controller_enabled(default: bool | None = None) -> bool | None:
    """Check if semantic controller is enabled (None = not explicitly set)."""
    value = get_config_value("chat.semantic_controller_enabled", "TOM_SEMANTIC_CONTROLLER_ENABLED", default=None)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    return bool(value)


def is_leaf_balance_enabled(default: bool | None = None) -> bool | None:
    """Check if leaf balance is enabled (None = not explicitly set)."""
    value = get_config_value("chat.leaf_balance_enabled", "TOM_LEAF_BALANCE_ENABLED", default=None)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    return bool(value)


def get_bg_phys_ticks(default: int = 0) -> int:
    """Get background physics max ticks."""
    return get_int("chat.bg_phys_ticks", "TOM_BG_PHYS_TICKS", default)


def get_bg_phys_max_ms(default: float = 20.0) -> float:
    """Get background physics max milliseconds."""
    return get_float("chat.bg_phys_max_ms", "TOM_BG_PHYS_MAX_MS", default)


def get_idle_age_ticks_per_sec(default: float = 0.1) -> float:
    """Get idle age ticks per second."""
    return get_float("chat.idle_age_ticks_per_sec", "TOM_IDLE_AGE_TICKS_PER_SEC", default)


def get_idle_age_max_ticks(default: int = 0) -> int:
    """Get idle age max ticks (0 = disabled)."""
    return get_int("chat.idle_age_max_ticks", "TOM_IDLE_AGE_MAX_TICKS", default)


def is_bg_phys_log_enabled(default: bool = False) -> bool:
    """Check if background physics logging is enabled."""
    return get_bool("chat.bg_phys_log", "TOM_BG_PHYS_LOG", default)


def is_bg_phys_slo_guard_enabled(default: bool = False) -> bool:
    """Check if background physics SLO guard is enabled."""
    return get_bool("chat.bg_phys_slo_guard", "TOM_BG_PHYS_SLO_GUARD", default)


def get_force_semantic_targets(default: str = "") -> str:
    """Get forced semantic targets (empty = not forced)."""
    return get_str("chat.force_semantic_targets", "TOM_FORCE_SEMANTIC_TARGETS", default)


def get_pending_expiry_seconds(default: int = 3600) -> int:
    """Get pending interaction expiry in seconds."""
    return get_int("chat.pending_expiry_seconds", "TOM_PENDING_EXPIRY_SECONDS", default)


def is_semantic_loads_disabled(default: bool = False) -> bool:
    """Check if semantic loads are disabled."""
    value = get_config_value("chat.semantic_loads_disabled", "TOM_SEMANTIC_LOADS_DISABLED", default=None)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    return bool(value)


def is_regex_self_ref_routing_enabled(default: bool = False) -> bool:
    """Check if regex self-ref routing is enabled."""
    return get_bool("chat.regex_self_ref_routing", "TOM_REGEX_SELF_REF_ROUTING", default)


# Verification helpers
def get_evidence_provider_url(default: str = "http://localhost:8000") -> str:
    """Get evidence provider base URL."""
    return get_str("verification.evidence_provider_url", "TOM_EVIDENCE_PROVIDER_URL", default)


def is_verification_enabled(default: bool = False) -> bool:
    """Check if verification is enabled."""
    return get_bool("verification.enabled", "TOM_VERIFICATION_ENABLED", default)


def get_evidence_provider_timeout(default: float = 5.0) -> float:
    """Get evidence provider timeout in seconds."""
    canonical = get_config_value(
        "verification.evidence_provider_timeout",
        "TOM_EVIDENCE_PROVIDER_TIMEOUT",
        default=None,
    )
    if canonical is not None:
        try:
            return float(str(canonical).strip())
        except (ValueError, TypeError):
            return default
    return get_float("evidence.provider_timeout", default=default)


def get_org_id(default: str = "00Dxx0000000000AAA") -> str:
    """Get organization ID."""
    return get_str("verification.org_id", "TOM_ORG_ID", default)


def get_mock_verdict(default: str = "SUPPORTED") -> str:
    """Get mock verdict for testing."""
    return get_str("verification.mock_verdict", "TOM_MOCK_VERDICT", default)


def get_mock_confidence(default: float = 0.9) -> float:
    """Get mock confidence for testing."""
    return get_float("verification.mock_confidence", "TOM_MOCK_CONFIDENCE", default)


# Telemetry helpers
def get_run_artifact_prefix(default: str = "") -> str:
    """Get run artifact prefix for telemetry files."""
    return get_str("telemetry.run_artifact_prefix", "TOM_RUN_ARTIFACT_PREFIX", default)


# Feature flag banner helpers
def is_feature_banner_enabled(default: bool = True) -> bool:
    """Check if feature banner is enabled."""
    return get_bool("ui.feature_banner", "TOM_FEATURE_BANNER", default)


def is_idle_age_reminder_enabled(default: bool = True) -> bool:
    """Check if idle age reminder is enabled."""
    return get_bool("ui.idle_age_reminder", "TOM_IDLE_AGE_REMINDER", default)


def get_idle_age_reminder_days(default: float = 7.0) -> float:
    """Get idle age reminder threshold in days."""
    return get_float("ui.idle_age_reminder_days", "TOM_IDLE_AGE_REMINDER_DAYS", default)


# ---------------------------------------------------------------------------
# Integration Configuration Helpers
# ---------------------------------------------------------------------------

def is_web_search_enabled(default: bool = False) -> bool:
    """Check if web search integration is enabled."""
    return get_bool("integrations.web_search.enabled", "TOM_WEBSEARCH_ENABLED", default)

def get_web_search_timeout(default: float = 30.0) -> float:
    """Get web search timeout in seconds."""
    return get_float("integrations.web_search.timeout_seconds", "TOM_WEBSEARCH_TIMEOUT", default)

def is_file_read_enabled(default: bool = False) -> bool:
    """Check if file read integration is enabled."""
    return get_bool("integrations.file_read.enabled", "TOM_FILEREAD_ENABLED", default)

def get_file_read_base_dir(default: str = "") -> str:
    """Get file read base directory."""
    return get_config_value("integrations.file_read.base_directory", "TOM_FILEREAD_BASE_DIR", default)

def get_file_read_timeout(default: float = 10.0) -> float:
    """Get file read timeout in seconds."""
    return get_float("integrations.file_read.timeout_seconds", "TOM_FILEREAD_TIMEOUT", default)

def is_sandbox_exec_enabled(default: bool = False) -> bool:
    """Check if sandbox exec integration is enabled."""
    return get_bool("integrations.sandbox_exec.enabled", "TOM_SANDBOXEXEC_ENABLED", default)

def get_sandbox_exec_timeout(default: float = 60.0) -> float:
    """Get sandbox exec timeout in seconds."""
    return get_float("integrations.sandbox_exec.timeout_seconds", "TOM_SANDBOXEXEC_TIMEOUT", default)

def get_sandbox_exec_root(default: str = "") -> str:
    """Get sandbox exec root directory."""
    return get_config_value("integrations.sandbox_exec.sandbox_root", "TOM_SANDBOXEXEC_ROOT", default)


# ============================================================================
# REALISER CONFIGURATION
# ============================================================================

def get_realiser_provider(default: str = "") -> str:
    """Get realiser LLM provider (empty = use main TOM LLM)."""
    return get_str("tunable.realiser.provider", "TOM_REALISER_PROVIDER", default)

def get_realiser_model(default: str = "") -> str:
    """Get realiser model name."""
    return get_str("tunable.realiser.model", "TOM_REALISER_MODEL", default)

def get_realiser_api_key(default: str = "") -> str:
    """Get realiser API key."""
    return get_str("tunable.realiser.api_key", "TOM_REALISER_API_KEY", default)

def get_realiser_base_url(default: str = "") -> str:
    """Get realiser base URL."""
    return get_str("tunable.realiser.base_url", "TOM_REALISER_BASE_URL", default)

def get_realiser_temperature(default: float = 0.7) -> float:
    """Get realiser temperature."""
    return get_float("tunable.realiser.temperature", "TOM_REALISER_TEMPERATURE", default)

def get_realiser_max_tokens(default: int = 80) -> int:
    """Get realiser max output tokens."""
    return get_int("tunable.realiser.max_tokens", "TOM_REALISER_MAX_TOKENS", default)

def get_realiser_timeout(default: float = 10.0) -> float:
    """Get realiser timeout in seconds."""
    return get_float("tunable.realiser.timeout_s", "TOM_REALISER_TIMEOUT_S", default)

def is_realiser_greetings_enabled(default: bool = False) -> bool:
    """Check if greetings should be realised via LLM."""
    return get_bool("tunable.realiser.realise_greetings", "TOM_REALISER_GREETINGS", default)


# ============================================================================
# AGENT LLM CONFIGURATION
# ============================================================================

def get_agent_llm_provider(default: str = "") -> str:
    """Get agent LLM provider (empty = use main TOM LLM)."""
    return get_str("tunable.agent_llm.provider", "TOM_AGENT_LLM_PROVIDER", default)

def get_agent_llm_model(default: str = "") -> str:
    """Get agent LLM model name."""
    return get_str("tunable.agent_llm.model", "TOM_AGENT_LLM_MODEL", default)

def get_agent_llm_api_key(default: str = "") -> str:
    """Get agent LLM API key."""
    return get_str("tunable.agent_llm.api_key", "TOM_AGENT_LLM_API_KEY", default)

def get_agent_llm_base_url(default: str = "") -> str:
    """Get agent LLM base URL."""
    return get_str("tunable.agent_llm.base_url", "TOM_AGENT_LLM_BASE_URL", default)

def get_agent_llm_temperature(default: float = 0.7) -> float:
    """Get agent LLM temperature."""
    return get_float("tunable.agent_llm.temperature", "TOM_AGENT_LLM_TEMPERATURE", default)

def get_agent_llm_max_tokens(default: int = 4096) -> int:
    """Get agent LLM max output tokens."""
    return get_int("tunable.agent_llm.max_tokens", "TOM_AGENT_LLM_MAX_TOKENS", default)

def get_agent_llm_timeout(default: float = 120.0) -> float:
    """Get agent LLM timeout in seconds."""
    return get_float("tunable.agent_llm.timeout_s", "TOM_AGENT_LLM_TIMEOUT_S", default)


# ============================================================================
# ANTHROPIC TRANSPORT CONFIGURATION
# ============================================================================

def get_anthropic_transport(default: str = "direct") -> str:
    """Get Anthropic transport mode: 'direct' (SDK) or 'proxy'."""
    return get_str("llm.anthropic_transport", "TOM_ANTHROPIC_TRANSPORT", default)

def get_agent_anthropic_transport(default: str = "") -> str:
    """Get agent-specific Anthropic transport. Empty = fallback to main.

    Reads new path first (llm.agent_anthropic_transport), then transitional
    old path (tunable.agent_llm.anthropic_transport) with deprecation warning.
    """
    # New path first
    val = get_str("llm.agent_anthropic_transport", "TOM_AGENT_ANTHROPIC_TRANSPORT", "")
    if val:
        return val
    # Transitional: read old path for one release cycle
    old_val = get_str("tunable.agent_llm.anthropic_transport", "", "")
    if old_val:
        import logging
        logging.getLogger(__name__).warning(
            "Deprecated config path 'tunable.agent_llm.anthropic_transport' — "
            "migrate to 'llm.agent_anthropic_transport'"
        )
        return old_val
    return default


# ============================================================================
# ACTION LEARNING CONFIGURATION
# ============================================================================

def get_action_learning_enabled(default: bool = False) -> bool:
    """Check if action learning from agent outcomes is enabled."""
    return get_bool("tunable.action_learning.enabled", "TOM_ACTION_LEARNING_ENABLED", default)

def get_action_learning_min_confidence(default: float = 0.6) -> float:
    """Get minimum quality score to persist an action outcome."""
    return get_float("tunable.action_learning.min_confidence", "TOM_ACTION_LEARNING_MIN_CONFIDENCE", default)

def get_action_learning_min_consistency(default: int = 2) -> int:
    """Get required consecutive failures before persisting failure outcomes."""
    return get_int("tunable.action_learning.min_consistency", "TOM_ACTION_LEARNING_MIN_CONSISTENCY", default)

def get_action_learning_max_per_session(default: int = 20) -> int:
    """Get max action outcomes persisted per session."""
    return get_int("tunable.action_learning.max_records_per_session", "TOM_ACTION_LEARNING_MAX_PER_SESSION", default)

def get_action_learning_max_store(default: int = 500) -> int:
    """Get max total action outcomes per tenant store."""
    return get_int("tunable.action_learning.max_store_size", "TOM_ACTION_LEARNING_MAX_STORE", default)

def get_action_learning_retrieval_weight(default: float = 0.3) -> float:
    """Get RRF weight for action outcome retrieval."""
    return get_float("tunable.action_learning.retrieval_weight", "TOM_ACTION_LEARNING_RETRIEVAL_WEIGHT", default)

def get_leaf_vec_retrieval_weight(default: float = 0.6) -> float:
    """Get RRF weight for leaf-vector cosine rank."""
    return get_float("sicd.leaf_vec_retrieval_weight", "TOM_LEAF_VEC_RETRIEVAL_WEIGHT", default)

def get_action_learning_retrieval_max(default: int = 3) -> int:
    """Get max action outcome items in retrieval results."""
    return get_int("tunable.action_learning.retrieval_max_items", "TOM_ACTION_LEARNING_RETRIEVAL_MAX", default)

def get_action_learning_success_strength(default: float = 0.7) -> float:
    """Get memory strength for successful action outcomes."""
    return get_float("tunable.action_learning.success_strength", "TOM_ACTION_LEARNING_SUCCESS_STRENGTH", default)

def get_action_learning_failure_strength(default: float = 0.4) -> float:
    """Get memory strength for failed action outcomes."""
    return get_float("tunable.action_learning.failure_strength", "TOM_ACTION_LEARNING_FAILURE_STRENGTH", default)

def get_action_learning_ttl_days(default: int = 90) -> int:
    """Get retrieval-side TTL for action outcomes in days."""
    return get_int("tunable.action_learning.store_ttl_days", "TOM_ACTION_LEARNING_TTL_DAYS", default)


# ============================================================================
# AGENT MEMORY CONFIGURATION
# ============================================================================

def get_agent_memory_enabled(default: bool = True) -> bool:
    """Check if agent observation memory (cross-session) is enabled."""
    return get_bool("tunable.agent_memory.enabled", "TOM_AGENT_MEMORY_ENABLED", default)

def get_agent_memory_retrieval_weight(default: float = 0.2) -> float:
    """Get RRF weight for agent observation retrieval in chatbot path."""
    return get_float("tunable.agent_memory.retrieval_weight", "TOM_AGENT_MEMORY_RETRIEVAL_WEIGHT", default)

def get_agent_memory_retrieval_max(default: int = 2) -> int:
    """Get max agent observation items in chatbot retrieval results."""
    return get_int("tunable.agent_memory.retrieval_max_items", "TOM_AGENT_MEMORY_RETRIEVAL_MAX", default)

def get_agent_memory_max_store(default: int = 300) -> int:
    """Get max total agent observations per tenant store."""
    return get_int("tunable.agent_memory.max_store_size", "TOM_AGENT_MEMORY_MAX_STORE", default)


def get_district_live_recall_enabled(default: bool = True) -> bool:
    """Check if live district-owner recall is enabled in chat harvest path."""
    return get_bool(
        "tunable.agent_memory.district_live_recall_enabled",
        "TOM_DISTRICT_LIVE_RECALL",
        default,
    )

def get_carillon_live_territory_routing_enabled(default: bool = True) -> bool:
    """Check if canonical Carillon pre-provider premise routing is enabled."""
    return get_bool(
        "tunable.agent_memory.carillon_live_territory_routing_enabled",
        "TOM_CARILLON_LIVE_TERRITORY_ROUTING",
        default,
    )

def get_agent_memory_ttl_days(default: int = 90) -> int:
    """Get retrieval-side TTL for agent observations in days."""
    return get_int("tunable.agent_memory.store_ttl_days", "TOM_AGENT_MEMORY_TTL_DAYS", default)
