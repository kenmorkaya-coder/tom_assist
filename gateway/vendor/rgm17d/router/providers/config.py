# Module Overview [router/providers/config.py]
# Purpose: Defines configuration dataclasses for integration providers.
# Exclusions: Does not load or validate config; that is handled by config/loader.py.
# Phase dependency: Used by provider implementations and config/tunable_params.py.
# Inputs/Outputs: Frozen dataclass configurations with safe defaults.
# Invariants: All integrations are DISABLED by default; enabled requires explicit config.

"""
Integration Provider Configuration – ToM V4:P2

Defines configuration dataclasses for each integration type.
All integrations are DISABLED by default and must be explicitly enabled.

Subsystem: router.providers
Owns: Configuration dataclass definitions
Must Not: Load config files or access environment variables directly
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Tuple


# ---------------------------------------------------------------------------
# Web Search Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WebSearchIntegrationConfig:
    """
    Web search integration configuration.

    All settings have safe defaults. The integration is DISABLED by default
    and returns structured errors until explicitly enabled.

    Attributes:
        enabled: Master switch; when False, returns IntegrationDisabledError
        timeout_seconds: Request timeout (default 30s)
        max_retries: Maximum retry attempts for transient failures
        rate_limit_rpm: Requests per minute limit (0 = unlimited)
        max_results: Maximum results per query
        provider: Provider type ("disabled", "local", "external")
        external_url: URL for external search endpoint (if provider="external")
        external_api_key: API key for external endpoint
        audit_enabled: Enable audit logging for all requests
        audit_log_queries: Log query strings (may contain sensitive data)
    """
    enabled: bool = True
    timeout_seconds: float = 30.0
    max_retries: int = 2
    rate_limit_rpm: int = 60
    max_results: int = 10
    provider: str = "duckduckgo"
    external_url: str = ""
    external_api_key: str = ""
    audit_enabled: bool = True
    audit_log_queries: bool = False

    def apply_env_overrides(self) -> "WebSearchIntegrationConfig":
        """Apply environment variable overrides."""
        return WebSearchIntegrationConfig(
            enabled=_parse_bool(os.getenv("TOM_WEBSEARCH_ENABLED"), self.enabled),
            timeout_seconds=_parse_float(os.getenv("TOM_WEBSEARCH_TIMEOUT"), self.timeout_seconds),
            max_retries=_parse_int(os.getenv("TOM_WEBSEARCH_MAX_RETRIES"), self.max_retries),
            rate_limit_rpm=_parse_int(os.getenv("TOM_WEBSEARCH_RATE_LIMIT"), self.rate_limit_rpm),
            max_results=_parse_int(os.getenv("TOM_WEBSEARCH_MAX_RESULTS"), self.max_results),
            provider=os.getenv("TOM_WEBSEARCH_PROVIDER", self.provider),
            external_url=os.getenv("TOM_WEBSEARCH_EXTERNAL_URL", self.external_url),
            external_api_key=os.getenv("TOM_WEBSEARCH_EXTERNAL_API_KEY", self.external_api_key),
            audit_enabled=_parse_bool(os.getenv("TOM_WEBSEARCH_AUDIT_ENABLED"), self.audit_enabled),
            audit_log_queries=_parse_bool(os.getenv("TOM_WEBSEARCH_AUDIT_LOG_QUERIES"), self.audit_log_queries),
        )


# ---------------------------------------------------------------------------
# File Read Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FileReadIntegrationConfig:
    """
    File read integration configuration.

    All settings have safe defaults. The integration is DISABLED by default
    and requires a base_directory when enabled. Blocked paths are always
    denied regardless of other settings.

    Attributes:
        enabled: Master switch; when False, returns IntegrationDisabledError
        base_directory: Root directory for file access (required when enabled)
        allowed_paths: Glob patterns for allowed paths (empty = all within base)
        blocked_paths: Glob patterns for blocked paths (always denied)
        allowed_extensions: Allowed file extensions (empty = all)
        max_file_size_bytes: Maximum file size to read (default 10MB)
        follow_symlinks: Follow symlinks (default False for security)
        allow_absolute_paths: Allow absolute paths (default False)
        timeout_seconds: Read timeout (default 10s)
        audit_enabled: Enable audit logging for all requests
        audit_log_paths: Log requested paths in audit
    """
    enabled: bool = True
    base_directory: str = ""
    allowed_paths: Tuple[str, ...] = ()
    blocked_paths: Tuple[str, ...] = (
        "**/.env*",
        "**/*.env",
        "**/credentials*",
        "**/secrets*",
        "**/.ssh/**",
        "**/.aws/**",
        "**/.gnupg/**",
        "**/id_rsa*",
        "**/id_ed25519*",
        "**/*.pem",
        "**/*.key",
        "**/password*",
        "**/token*",
    )
    allowed_extensions: Tuple[str, ...] = ()
    max_file_size_bytes: int = 10_485_760  # 10MB
    follow_symlinks: bool = False
    allow_absolute_paths: bool = False
    timeout_seconds: float = 10.0
    audit_enabled: bool = True
    audit_log_paths: bool = True

    def apply_env_overrides(self) -> "FileReadIntegrationConfig":
        """Apply environment variable overrides."""
        return FileReadIntegrationConfig(
            enabled=_parse_bool(os.getenv("TOM_FILEREAD_ENABLED"), self.enabled),
            base_directory=os.getenv("TOM_FILEREAD_BASE_DIR", self.base_directory),
            allowed_paths=_parse_tuple(os.getenv("TOM_FILEREAD_ALLOWED_PATHS"), self.allowed_paths),
            blocked_paths=_parse_tuple(os.getenv("TOM_FILEREAD_BLOCKED_PATHS"), self.blocked_paths),
            allowed_extensions=_parse_tuple(os.getenv("TOM_FILEREAD_ALLOWED_EXTENSIONS"), self.allowed_extensions),
            max_file_size_bytes=_parse_int(os.getenv("TOM_FILEREAD_MAX_SIZE"), self.max_file_size_bytes),
            follow_symlinks=_parse_bool(os.getenv("TOM_FILEREAD_FOLLOW_SYMLINKS"), self.follow_symlinks),
            allow_absolute_paths=_parse_bool(os.getenv("TOM_FILEREAD_ALLOW_ABSOLUTE"), self.allow_absolute_paths),
            timeout_seconds=_parse_float(os.getenv("TOM_FILEREAD_TIMEOUT"), self.timeout_seconds),
            audit_enabled=_parse_bool(os.getenv("TOM_FILEREAD_AUDIT_ENABLED"), self.audit_enabled),
            audit_log_paths=_parse_bool(os.getenv("TOM_FILEREAD_AUDIT_LOG_PATHS"), self.audit_log_paths),
        )


# ---------------------------------------------------------------------------
# Sandbox Exec Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SandboxExecIntegrationConfig:
    """
    Sandbox execution integration configuration.

    All settings have safe defaults. The integration is DISABLED by default
    and requires explicit command allowlisting when enabled. Blocked commands
    are always denied regardless of other settings.

    Attributes:
        enabled: Master switch; when False, returns IntegrationDisabledError
        executor: Executor type ("disabled", "subprocess", "docker", "firejail")
        timeout_seconds: Execution timeout (default 60s)
        max_memory_mb: Maximum memory in MB (default 256)
        max_cpu_seconds: Maximum CPU time in seconds (default 30)
        max_output_bytes: Maximum output size (default 1MB)
        allowed_commands: Allowed commands (empty = deny all)
        blocked_commands: Blocked commands (always denied)
        inherit_env: Inherit environment from parent (default False)
        allowed_env_vars: Environment vars to pass if inherit_env=False
        sandbox_root: Root directory for sandbox (required when enabled)
        readonly_filesystem: Mount filesystem as read-only (default True)
        network_enabled: Allow network access (default False)
        use_pa_sandbox: Integrate with PA sandbox validation (default True)
        require_approval_token: Require approval token for execution (default True)
        audit_enabled: Enable audit logging
        audit_log_commands: Log executed commands
        audit_log_output: Log command output (may be large/sensitive)
    """
    enabled: bool = True
    executor: str = "disabled"
    timeout_seconds: float = 60.0
    max_memory_mb: int = 256
    max_cpu_seconds: float = 30.0
    max_output_bytes: int = 1_048_576  # 1MB
    allowed_commands: Tuple[str, ...] = ()
    blocked_commands: Tuple[str, ...] = (
        "rm", "rmdir", "del", "format", "mkfs",
        "dd", "shred", "wipe",
        "curl", "wget", "nc", "netcat", "ncat",
        "ssh", "scp", "sftp", "rsync",
        "sudo", "su", "doas", "pkexec",
        "chmod", "chown", "chgrp",
        "mount", "umount",
        "kill", "killall", "pkill",
        "shutdown", "reboot", "halt", "poweroff",
    )
    inherit_env: bool = False
    allowed_env_vars: Tuple[str, ...] = ("PATH", "HOME", "USER", "LANG", "LC_ALL")
    sandbox_root: str = ""
    readonly_filesystem: bool = True
    network_enabled: bool = False
    use_pa_sandbox: bool = True
    require_approval_token: bool = True
    audit_enabled: bool = True
    audit_log_commands: bool = True
    audit_log_output: bool = False

    def apply_env_overrides(self) -> "SandboxExecIntegrationConfig":
        """Apply environment variable overrides."""
        return SandboxExecIntegrationConfig(
            enabled=_parse_bool(os.getenv("TOM_SANDBOXEXEC_ENABLED"), self.enabled),
            executor=os.getenv("TOM_SANDBOXEXEC_EXECUTOR", self.executor),
            timeout_seconds=_parse_float(os.getenv("TOM_SANDBOXEXEC_TIMEOUT"), self.timeout_seconds),
            max_memory_mb=_parse_int(os.getenv("TOM_SANDBOXEXEC_MAX_MEMORY"), self.max_memory_mb),
            max_cpu_seconds=_parse_float(os.getenv("TOM_SANDBOXEXEC_MAX_CPU"), self.max_cpu_seconds),
            max_output_bytes=_parse_int(os.getenv("TOM_SANDBOXEXEC_MAX_OUTPUT"), self.max_output_bytes),
            allowed_commands=_parse_tuple(os.getenv("TOM_SANDBOXEXEC_ALLOWED_COMMANDS"), self.allowed_commands),
            blocked_commands=_parse_tuple(os.getenv("TOM_SANDBOXEXEC_BLOCKED_COMMANDS"), self.blocked_commands),
            inherit_env=_parse_bool(os.getenv("TOM_SANDBOXEXEC_INHERIT_ENV"), self.inherit_env),
            allowed_env_vars=_parse_tuple(os.getenv("TOM_SANDBOXEXEC_ALLOWED_ENV"), self.allowed_env_vars),
            sandbox_root=os.getenv("TOM_SANDBOXEXEC_ROOT", self.sandbox_root),
            readonly_filesystem=_parse_bool(os.getenv("TOM_SANDBOXEXEC_READONLY"), self.readonly_filesystem),
            network_enabled=_parse_bool(os.getenv("TOM_SANDBOXEXEC_NETWORK"), self.network_enabled),
            use_pa_sandbox=_parse_bool(os.getenv("TOM_SANDBOXEXEC_USE_PA_SANDBOX"), self.use_pa_sandbox),
            require_approval_token=_parse_bool(os.getenv("TOM_SANDBOXEXEC_REQUIRE_APPROVAL"), self.require_approval_token),
            audit_enabled=_parse_bool(os.getenv("TOM_SANDBOXEXEC_AUDIT_ENABLED"), self.audit_enabled),
            audit_log_commands=_parse_bool(os.getenv("TOM_SANDBOXEXEC_AUDIT_LOG_COMMANDS"), self.audit_log_commands),
            audit_log_output=_parse_bool(os.getenv("TOM_SANDBOXEXEC_AUDIT_LOG_OUTPUT"), self.audit_log_output),
        )


# ---------------------------------------------------------------------------
# File Write Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FileWriteIntegrationConfig:
    """
    File write integration configuration.

    All settings have safe defaults. The integration is DISABLED by default
    and requires a base_directory when enabled. Blocked paths are always
    denied regardless of other settings.

    Attributes:
        enabled: Master switch; when False, returns IntegrationDisabledError
        base_directory: Root directory for file access (required when enabled)
        allowed_paths: Glob patterns for allowed paths (empty = all within base)
        blocked_paths: Glob patterns for blocked paths (always denied)
        allowed_extensions: Allowed file extensions (empty = all)
        max_file_size_bytes: Maximum file size to write (default 5MB)
        create_directories: Create parent directories if missing (default False)
        follow_symlinks: Follow symlinks (default False for security)
        allow_absolute_paths: Allow absolute paths (default False)
        timeout_seconds: Write timeout (default 30s)
        audit_enabled: Enable audit logging for all requests
        audit_log_paths: Log requested paths in audit
    """
    enabled: bool = True
    base_directory: str = ""
    allowed_paths: Tuple[str, ...] = ()
    blocked_paths: Tuple[str, ...] = (
        "**/.env*",
        "**/*.env",
        "**/credentials*",
        "**/secrets*",
        "**/.ssh/**",
        "**/.aws/**",
        "**/.gnupg/**",
        "**/id_rsa*",
        "**/id_ed25519*",
        "**/*.pem",
        "**/*.key",
        "**/password*",
        "**/token*",
        "**/*.exe",
        "**/*.bat",
        "**/*.cmd",
        "**/*.ps1",
        "**/*.sh",
        "**/*.dll",
        "**/*.so",
    )
    allowed_extensions: Tuple[str, ...] = ()
    max_file_size_bytes: int = 5_242_880  # 5MB
    create_directories: bool = False
    follow_symlinks: bool = False
    allow_absolute_paths: bool = False
    timeout_seconds: float = 30.0
    audit_enabled: bool = True
    audit_log_paths: bool = True

    def apply_env_overrides(self) -> "FileWriteIntegrationConfig":
        """Apply environment variable overrides."""
        return FileWriteIntegrationConfig(
            enabled=_parse_bool(os.getenv("TOM_FILEWRITE_ENABLED"), self.enabled),
            base_directory=os.getenv("TOM_FILEWRITE_BASE_DIR", self.base_directory),
            allowed_paths=_parse_tuple(os.getenv("TOM_FILEWRITE_ALLOWED_PATHS"), self.allowed_paths),
            blocked_paths=_parse_tuple(os.getenv("TOM_FILEWRITE_BLOCKED_PATHS"), self.blocked_paths),
            allowed_extensions=_parse_tuple(os.getenv("TOM_FILEWRITE_ALLOWED_EXTENSIONS"), self.allowed_extensions),
            max_file_size_bytes=_parse_int(os.getenv("TOM_FILEWRITE_MAX_SIZE"), self.max_file_size_bytes),
            create_directories=_parse_bool(os.getenv("TOM_FILEWRITE_CREATE_DIRS"), self.create_directories),
            follow_symlinks=_parse_bool(os.getenv("TOM_FILEWRITE_FOLLOW_SYMLINKS"), self.follow_symlinks),
            allow_absolute_paths=_parse_bool(os.getenv("TOM_FILEWRITE_ALLOW_ABSOLUTE"), self.allow_absolute_paths),
            timeout_seconds=_parse_float(os.getenv("TOM_FILEWRITE_TIMEOUT"), self.timeout_seconds),
            audit_enabled=_parse_bool(os.getenv("TOM_FILEWRITE_AUDIT_ENABLED"), self.audit_enabled),
            audit_log_paths=_parse_bool(os.getenv("TOM_FILEWRITE_AUDIT_LOG_PATHS"), self.audit_log_paths),
        )


# ---------------------------------------------------------------------------
# Screen Capture Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScreenCaptureIntegrationConfig:
    """
    Screen capture integration configuration.

    Attributes:
        enabled: Master switch; when False, returns IntegrationDisabledError
        max_dimension: Maximum pixels on longest side (resized if larger)
        quality: JPEG compression quality (1-100)
        audit_enabled: Enable audit logging for all captures
    """
    enabled: bool = True
    max_dimension: int = 1920
    quality: int = 75
    audit_enabled: bool = True

    def apply_env_overrides(self) -> "ScreenCaptureIntegrationConfig":
        """Apply environment variable overrides."""
        return ScreenCaptureIntegrationConfig(
            enabled=_parse_bool(os.getenv("TOM_SCREENCAPTURE_ENABLED"), self.enabled),
            max_dimension=_parse_int(os.getenv("TOM_SCREENCAPTURE_MAX_DIM"), self.max_dimension),
            quality=_parse_int(os.getenv("TOM_SCREENCAPTURE_QUALITY"), self.quality),
            audit_enabled=_parse_bool(os.getenv("TOM_SCREENCAPTURE_AUDIT"), self.audit_enabled),
        )


# ---------------------------------------------------------------------------
# Desktop Action Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DesktopActionIntegrationConfig:
    """
    Desktop action integration configuration.

    Controls mouse/keyboard automation via pyautogui.
    DISABLED by default — must be explicitly enabled.

    Attributes:
        enabled: Master switch; when False, returns IntegrationDisabledError
        mouse_move_duration: Seconds for mouse travel animation (safety)
        type_interval: Seconds between keystrokes (safety)
        action_delay: Seconds to wait after each action (safety throttle)
        audit_enabled: Enable audit logging for all actions
    """
    enabled: bool = False
    mouse_move_duration: float = 0.3
    type_interval: float = 0.05
    action_delay: float = 0.1
    audit_enabled: bool = True

    def apply_env_overrides(self) -> "DesktopActionIntegrationConfig":
        """Apply environment variable overrides."""
        return DesktopActionIntegrationConfig(
            enabled=_parse_bool(os.getenv("TOM_DESKTOPACTION_ENABLED"), self.enabled),
            mouse_move_duration=_parse_float(os.getenv("TOM_DESKTOPACTION_MOUSE_DURATION"), self.mouse_move_duration),
            type_interval=_parse_float(os.getenv("TOM_DESKTOPACTION_TYPE_INTERVAL"), self.type_interval),
            action_delay=_parse_float(os.getenv("TOM_DESKTOPACTION_DELAY"), self.action_delay),
            audit_enabled=_parse_bool(os.getenv("TOM_DESKTOPACTION_AUDIT"), self.audit_enabled),
        )


# ---------------------------------------------------------------------------
# Aggregate Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntegrationsConfig:
    """
    Aggregate configuration for all integrations.

    This is the top-level container used in TunableParams.
    All integrations are DISABLED by default.

    Attributes:
        web_search: Web search configuration
        file_read: File read configuration
        sandbox_exec: Sandbox execution configuration
        file_write: File write configuration
        screen_capture: Screen capture configuration
        desktop_action: Desktop action configuration
    """
    web_search: WebSearchIntegrationConfig = field(default_factory=WebSearchIntegrationConfig)
    file_read: FileReadIntegrationConfig = field(default_factory=FileReadIntegrationConfig)
    sandbox_exec: SandboxExecIntegrationConfig = field(default_factory=SandboxExecIntegrationConfig)
    file_write: FileWriteIntegrationConfig = field(default_factory=FileWriteIntegrationConfig)
    screen_capture: ScreenCaptureIntegrationConfig = field(default_factory=ScreenCaptureIntegrationConfig)
    desktop_action: DesktopActionIntegrationConfig = field(default_factory=DesktopActionIntegrationConfig)

    def apply_env_overrides(self) -> "IntegrationsConfig":
        """Apply environment variable overrides to all sub-configs."""
        return IntegrationsConfig(
            web_search=self.web_search.apply_env_overrides(),
            file_read=self.file_read.apply_env_overrides(),
            sandbox_exec=self.sandbox_exec.apply_env_overrides(),
            file_write=self.file_write.apply_env_overrides(),
            screen_capture=self.screen_capture.apply_env_overrides(),
            desktop_action=self.desktop_action.apply_env_overrides(),
        )


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _parse_bool(value: str | None, default: bool) -> bool:
    """Parse boolean from environment variable string."""
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _parse_int(value: str | None, default: int) -> int:
    """Parse integer from environment variable string."""
    if value is None:
        return default
    try:
        return int(value.strip())
    except (ValueError, TypeError):
        return default


def _parse_float(value: str | None, default: float) -> float:
    """Parse float from environment variable string."""
    if value is None:
        return default
    try:
        return float(value.strip())
    except (ValueError, TypeError):
        return default


def _parse_tuple(value: str | None, default: Tuple[str, ...]) -> Tuple[str, ...]:
    """
    Parse tuple of strings from environment variable.

    Supports comma-separated values: "a,b,c" -> ("a", "b", "c")
    Empty string returns empty tuple.
    """
    if value is None:
        return default
    value = value.strip()
    if not value:
        return ()
    return tuple(s.strip() for s in value.split(",") if s.strip())
