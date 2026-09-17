"""
Unified Configuration Loader.

This module provides a single entry point for loading configuration with
proper precedence chain and source tracking.

Precedence (later overrides earlier):
1. Dataclass defaults (built into ToMConfig)
2. defaults.yaml (repository defaults)
3. Profile file (config/profiles/{profile}.yaml)
3.5. Profile companion .env file (config/profiles/{profile}.env)
4. Environment variables (TOM_*)
5. CLI overrides (--config key=value)

Usage:
    from config.loader import ConfigLoader, load_config

    # Quick load with profile
    config = load_config(profile="local")

    # Full control with source tracking
    loader = ConfigLoader()
    config, sources = loader.load(profile="local", skip_env=False)

    # Check where a value came from
    print(sources["llm.provider"])  # ConfigValue(value="ollama", source=ENV, ...)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields, is_dataclass, field, MISSING
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type, Union
import copy


class ConfigSource(Enum):
    """Source of a configuration value."""
    DATACLASS = "dataclass"   # Built-in dataclass default
    DEFAULT = "default"        # From defaults.yaml
    PROFILE = "profile"        # From profile file (e.g., local.yaml)
    ENV = "env"                # From environment variable
    CLI = "cli"                # From CLI argument


@dataclass
class ConfigValue:
    """Tracks a config value and its source for config-dump."""
    value: Any
    source: ConfigSource
    source_detail: str = ""    # e.g., "TOM_LLM_MODEL" or "local.yaml"

    def __repr__(self) -> str:
        if self.source_detail:
            return f"ConfigValue({self.value!r}, {self.source.value}, {self.source_detail!r})"
        return f"ConfigValue({self.value!r}, {self.source.value})"


class ConfigLoader:
    """
    Unified configuration loader with source tracking.

    Loads configuration with proper precedence and tracks where each
    value came from for debugging and auditing.
    """

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """
        Initialize the config loader.

        Args:
            config_dir: Path to config directory. Defaults to this module's parent.
        """
        if config_dir is None:
            config_dir = Path(__file__).parent
        self._config_dir = config_dir
        self._sources: Dict[str, ConfigValue] = {}

    @property
    def config_dir(self) -> Path:
        """Get the config directory path."""
        return self._config_dir

    def load(
        self,
        profile: Optional[str] = None,
        cli_overrides: Optional[Dict[str, Any]] = None,
        skip_env: bool = False,
        skip_defaults_file: bool = False,
    ) -> Tuple[Any, Dict[str, ConfigValue]]:
        """
        Load configuration with precedence chain.

        Precedence (later overrides earlier):
        1. Dataclass defaults
        2. defaults.yaml (unless skip_defaults_file=True)
        3. Profile file (if profile specified)
        4. Environment variables (unless skip_env=True)
        5. CLI overrides (if provided)

        Args:
            profile: Profile name to load (e.g., "local", "ci")
            cli_overrides: Dict of config path -> value from CLI
            skip_env: If True, skip environment variable loading
            skip_defaults_file: If True, skip defaults.yaml loading

        Returns:
            Tuple of (config dict, sources dict)
        """
        self._sources = {}

        # Step 1: Start with dataclass defaults
        base_dict = self._get_dataclass_defaults()
        self._track_sources_recursive(base_dict, ConfigSource.DATACLASS, "dataclass", "")

        # Step 2: Merge defaults.yaml
        if not skip_defaults_file:
            defaults_path = self._config_dir / "defaults.yaml"
            if defaults_path.exists():
                defaults_dict = self._load_yaml(defaults_path)
                if defaults_dict:
                    self._deep_merge(base_dict, defaults_dict)
                    self._track_sources_recursive(defaults_dict, ConfigSource.DEFAULT, "defaults.yaml", "")

        # Step 3: Merge profile file(s) — YAML and/or .env
        if profile:
            profile_path = self._config_dir / "profiles" / f"{profile}.yaml"
            env_path = self._config_dir / "profiles" / f"{profile}.env"
            has_yaml = profile_path.exists()
            has_env = env_path.exists()

            if not has_yaml and not has_env:
                raise FileNotFoundError(
                    f"Profile '{profile}' not found: "
                    f"need {profile_path} and/or {env_path}"
                )

            if has_yaml:
                profile_dict = self._load_yaml(profile_path)
                if profile_dict:
                    self._deep_merge(base_dict, profile_dict)
                    self._track_sources_recursive(profile_dict, ConfigSource.PROFILE, f"{profile}.yaml", "")

            if has_env:
                env_dict = self._parse_profile_env(env_path, profile)
                if env_dict:
                    self._deep_merge(base_dict, env_dict)

        # Step 4: Apply env var overrides
        if not skip_env:
            env_overrides = self._collect_env_overrides()
            if env_overrides:
                self._deep_merge(base_dict, env_overrides)
                # Source tracking done in _collect_env_overrides

        # Step 5: Apply CLI overrides
        if cli_overrides:
            parsed_overrides = self._parse_cli_overrides(cli_overrides)
            if parsed_overrides:
                self._deep_merge(base_dict, parsed_overrides)
                self._track_sources_recursive(parsed_overrides, ConfigSource.CLI, "cli", "")

        return base_dict, self._sources

    def _get_dataclass_defaults(self) -> Dict[str, Any]:
        """Get defaults from ToMConfig dataclass and TunableParams."""
        result: Dict[str, Any] = {}

        # Try to import ToMConfig
        try:
            from gateway.vendor.rgm17d.registry.config_registry import ToMConfig
            result["tom"] = self._dataclass_to_dict(ToMConfig())
        except ImportError:
            pass

        # Try to import TunableParams
        try:
            from gateway.vendor.rgm17d.config.tunable_params import TunableParams
            result["tunable"] = self._dataclass_to_dict(TunableParams())
        except ImportError:
            pass

        return result

    def _dataclass_to_dict(self, obj: Any) -> Dict[str, Any]:
        """Convert a dataclass instance to a nested dict."""
        if not is_dataclass(obj) or isinstance(obj, type):
            return obj

        result = {}
        for f in fields(obj):
            value = getattr(obj, f.name)
            if is_dataclass(value) and not isinstance(value, type):
                result[f.name] = self._dataclass_to_dict(value)
            elif isinstance(value, (list, tuple)):
                result[f.name] = list(value)
            elif isinstance(value, dict):
                result[f.name] = dict(value)
            else:
                result[f.name] = value
        return result

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load a YAML file. Returns empty dict if file doesn't exist or parse fails."""
        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, dict) else {}
        except ImportError:
            # Fallback: try to parse simple YAML manually
            return self._parse_simple_yaml(path)
        except Exception:
            return {}

    def _parse_simple_yaml(self, path: Path) -> Dict[str, Any]:
        """Parse simple YAML without external dependencies."""
        result: Dict[str, Any] = {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                current_section = result
                section_stack: List[Tuple[Dict, int]] = [(result, -1)]

                for line in f:
                    stripped = line.rstrip()
                    if not stripped or stripped.startswith("#"):
                        continue

                    # Calculate indentation
                    indent = len(line) - len(line.lstrip())

                    # Pop sections that are no longer current
                    while section_stack and section_stack[-1][1] >= indent:
                        section_stack.pop()

                    current_section = section_stack[-1][0] if section_stack else result

                    # Parse key: value
                    if ":" in stripped:
                        key, _, value = stripped.partition(":")
                        key = key.strip()
                        value = value.strip()

                        if value:
                            # Simple value
                            current_section[key] = self._parse_yaml_value(value)
                        else:
                            # New section
                            new_section: Dict[str, Any] = {}
                            current_section[key] = new_section
                            section_stack.append((new_section, indent))

        except Exception:
            pass
        return result

    def _parse_yaml_value(self, value: str) -> Any:
        """Parse a simple YAML value."""
        value = value.strip()

        # Remove quotes
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]

        # Boolean
        if value.lower() in ("true", "yes", "on"):
            return True
        if value.lower() in ("false", "no", "off"):
            return False
        if value.lower() in ("null", "~", ""):
            return None

        # Number
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        return value

    def _deep_merge(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> None:
        """Deep merge overlay into base (mutates base)."""
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _collect_env_overrides(self) -> Dict[str, Any]:
        """Collect TOM_* env vars and convert to nested dict."""
        from gateway.vendor.rgm17d.config.env_mapping import ENV_TO_CONFIG_PATH, parse_env_value

        overrides: Dict[str, Any] = {}

        for env_var, config_path in ENV_TO_CONFIG_PATH.items():
            value = os.getenv(env_var)
            if value is not None:
                parsed_value = parse_env_value(env_var, value)
                self._set_nested(overrides, config_path, parsed_value)
                self._sources[config_path] = ConfigValue(
                    value=parsed_value,
                    source=ConfigSource.ENV,
                    source_detail=env_var,
                )

        return overrides

    def _parse_profile_env(self, env_path: Path, profile: str) -> Dict[str, Any]:
        """Parse companion .env file into config dict using ENV_TO_CONFIG_PATH.

        Does NOT mutate os.environ — runtime env injection for dataclass
        _env_float factories is handled separately by config/compat.py.
        Source tracked as (PROFILE, "{profile}.env") to distinguish from
        the .yaml profile and process env vars.
        """
        from gateway.vendor.rgm17d.config.env_mapping import ENV_TO_CONFIG_PATH, parse_env_value

        raw_vars: Dict[str, str] = {}
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
                if key:
                    raw_vars[key] = value

        result: Dict[str, Any] = {}
        keys_parsed = 0
        for env_var, raw_value in raw_vars.items():
            config_path = ENV_TO_CONFIG_PATH.get(env_var)
            if config_path is None:
                continue  # Env var not in mapping — skip
            parsed_value = parse_env_value(env_var, raw_value)
            self._set_nested(result, config_path, parsed_value)
            self._sources[config_path] = ConfigValue(
                value=parsed_value,
                source=ConfigSource.PROFILE,
                source_detail=f"{profile}.env",
            )
            keys_parsed += 1

        if keys_parsed:
            print(f"[ConfigLoader] Parsed {keys_parsed} config values from {profile}.env")

        return result

    def _parse_cli_overrides(self, cli_overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Parse CLI overrides from flat dict to nested dict."""
        result: Dict[str, Any] = {}
        for path, value in cli_overrides.items():
            self._set_nested(result, path, value)
        return result

    def _set_nested(self, d: Dict[str, Any], path: str, value: Any) -> None:
        """Set a nested value using dot-separated path."""
        parts = path.split(".")
        current = d
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def _get_nested(self, d: Dict[str, Any], path: str, default: Any = None) -> Any:
        """Get a nested value using dot-separated path."""
        parts = path.split(".")
        current = d
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def _track_sources_recursive(
        self,
        d: Dict[str, Any],
        source: ConfigSource,
        source_detail: str,
        prefix: str,
    ) -> None:
        """Recursively track sources for all values in dict."""
        for key, value in d.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                self._track_sources_recursive(value, source, source_detail, path)
            else:
                self._sources[path] = ConfigValue(
                    value=value,
                    source=source,
                    source_detail=source_detail,
                )


def load_config(
    profile: Optional[str] = None,
    cli_overrides: Optional[Dict[str, Any]] = None,
    skip_env: bool = False,
) -> Dict[str, Any]:
    """
    Quick helper to load configuration.

    Args:
        profile: Profile name to load (e.g., "local", "ci")
        cli_overrides: Dict of config path -> value from CLI
        skip_env: If True, skip environment variable loading

    Returns:
        Configuration dict
    """
    loader = ConfigLoader()
    config, _ = loader.load(profile=profile, cli_overrides=cli_overrides, skip_env=skip_env)
    return config


def load_config_with_sources(
    profile: Optional[str] = None,
    cli_overrides: Optional[Dict[str, Any]] = None,
    skip_env: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, ConfigValue]]:
    """
    Load configuration with source tracking.

    Args:
        profile: Profile name to load (e.g., "local", "ci")
        cli_overrides: Dict of config path -> value from CLI
        skip_env: If True, skip environment variable loading

    Returns:
        Tuple of (config dict, sources dict)
    """
    loader = ConfigLoader()
    return loader.load(profile=profile, cli_overrides=cli_overrides, skip_env=skip_env)


def format_config_dump(
    config: Dict[str, Any],
    sources: Dict[str, ConfigValue],
    format: str = "yaml",
    show_sources: bool = True,
    diff_from: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Format configuration for display.

    Args:
        config: Configuration dict
        sources: Sources dict from loader
        format: Output format ("yaml", "json", "table")
        show_sources: Whether to show source comments
        diff_from: Only show values different from this config

    Returns:
        Formatted string
    """
    if format == "json":
        import json
        return json.dumps(config, indent=2, default=str)

    elif format == "table":
        lines = ["Config Path                    | Value        | Source  | Detail"]
        lines.append("-" * 70)
        for path, cv in sorted(sources.items()):
            if diff_from and _get_nested_value(diff_from, path) == cv.value:
                continue
            value_str = str(cv.value)[:12]
            lines.append(f"{path:<30} | {value_str:<12} | {cv.source.value:<7} | {cv.source_detail}")
        return "\n".join(lines)

    else:  # yaml
        return _format_yaml_with_sources(config, sources, show_sources, diff_from)


def _format_yaml_with_sources(
    config: Dict[str, Any],
    sources: Dict[str, ConfigValue],
    show_sources: bool,
    diff_from: Optional[Dict[str, Any]],
    prefix: str = "",
    indent: int = 0,
) -> str:
    """Format config as YAML with optional source comments."""
    lines = []
    indent_str = "  " * indent

    for key, value in config.items():
        path = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            lines.append(f"{indent_str}{key}:")
            lines.append(_format_yaml_with_sources(
                value, sources, show_sources, diff_from, path, indent + 1
            ))
        else:
            if diff_from:
                old_value = _get_nested_value(diff_from, path)
                if old_value == value:
                    continue

            value_str = _yaml_value_str(value)
            if show_sources and path in sources:
                cv = sources[path]
                lines.append(f"{indent_str}{key}: {value_str}  # source: {cv.source.value} ({cv.source_detail})")
            else:
                lines.append(f"{indent_str}{key}: {value_str}")

    return "\n".join(lines)


def _yaml_value_str(value: Any) -> str:
    """Format a value for YAML output."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        if any(c in value for c in ":#{}[]&*!|>'\"%@`"):
            return f'"{value}"'
        return value
    return str(value)


def _get_nested_value(d: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Get nested value from dict using dot path."""
    parts = path.split(".")
    current = d
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current
