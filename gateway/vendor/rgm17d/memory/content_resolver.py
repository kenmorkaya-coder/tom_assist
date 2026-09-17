"""
Content Resolution Abstraction (M3/DEF-06)

Provides resolve_content(anchor, purpose) as the single API for all content consumers.
Abstracts storage policy: handles full-copy, file:// refs, ext:// refs, and summary fallbacks.

Canonical telemetry contract:
  - resolution_skip: BM25/DSI full-text source unavailable (caller must skip anchor)
  - resolution_miss: no content/ref/summary available at all
  - no event: prompt/graph successful summary fallback

Feature flag: TOM_USE_RESOLVE_CONTENT (default "1", set to "0" to bypass).
"""

import os
import math
import sys
from typing import Any, Callable, Dict, List, Optional

# Telemetry collector — set externally to capture resolution events
_telemetry_callback: Optional[Callable[[str, str, str], None]] = None


def set_telemetry_callback(cb: Callable[[str, str, str], None]) -> None:
    """Set callback for resolution telemetry events.

    Callback signature: cb(event_type, anchor_id, purpose)
    """
    global _telemetry_callback
    _telemetry_callback = cb


def _emit_telemetry(event_type: str, anchor_id: str, purpose: str) -> None:
    """Emit a resolution telemetry event."""
    if _telemetry_callback is not None:
        try:
            _telemetry_callback(event_type, anchor_id, purpose)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Single-anchor resolution
# ---------------------------------------------------------------------------

def resolve_content(anchor: dict, purpose: str) -> Optional[str]:
    """Resolve content for a memory anchor, abstracting storage policy.

    Returns:
        str  — resolved content (full text or summary depending on purpose)
        None — content required but unresolvable (caller MUST skip this anchor)

    Resolution order:
        1. anchor["content"] — if non-empty string, return immediately
        2. anchor["raw_content_ref"] — fetch from source:
           a. "file://..." → read from local filesystem
           b. "ext://..." → delegate to batch resolver coordinator
        3. Purpose-dependent fallback:
           a. "bm25" / "dsi": return None + "resolution_skip" telemetry
           b. "prompt" / "graph": return anchor["content_summary"] (summary acceptable)
        4. If no summary either: return None + "resolution_miss" telemetry

    Purpose controls fallback behavior:
        "bm25":   Full text required. If unresolvable → None (skip anchor)
        "dsi":    Full text required. If unresolvable → None (skip anchor)
        "prompt": Summary acceptable. Falls back to content_summary
        "graph":  Summary acceptable. Falls back to content_summary

    Feature flag:
        TOM_USE_RESOLVE_CONTENT=0 → bypass, return anchor["content"] directly
    """
    # Feature flag bypass
    if os.environ.get("TOM_USE_RESOLVE_CONTENT", "1") == "0":
        return anchor.get("content", "")

    anchor_id = anchor.get("id", "")

    # 1. Direct content
    content = anchor.get("content", "")
    if content and content.strip():
        return content

    # 2. raw_content_ref resolution
    ref = anchor.get("raw_content_ref")
    if ref:
        resolved = _resolve_ref(ref)
        if resolved:
            # M6/DEF-05: Integrity check for ext:// refs
            source_hash = anchor.get("source_content_hash")
            if ref.startswith("ext://") and source_hash:
                import hashlib
                resolved_hash = hashlib.sha256(
                    resolved.strip().lower().encode()
                ).hexdigest()[:12]
                if resolved_hash != source_hash:
                    _emit_telemetry("content_hash_mismatch", anchor_id, purpose)
                    # Hash mismatch: reject for BM25/DSI, fall through to summary fallback
                    resolved = None
            if resolved:
                return resolved

    # 3. Purpose-dependent fallback
    if purpose in ("bm25", "dsi"):
        # Full text required, summary insufficient
        _emit_telemetry("resolution_skip", anchor_id, purpose)
        return None
    elif purpose in ("prompt", "graph"):
        summary = anchor.get("content_summary", "")
        if summary and summary.strip():
            # Summary acceptable — no telemetry event (canonical contract)
            return summary

    # 4. Nothing available
    _emit_telemetry("resolution_miss", anchor_id, purpose)
    return None


# ---------------------------------------------------------------------------
# Batch resolution
# ---------------------------------------------------------------------------

def resolve_content_batch(
    anchors: List[dict],
    purpose: str,
) -> Dict[str, Optional[str]]:
    """Batch-resolve content for multiple anchors in a single pass.

    Callers (BM25 scoring, DSI injection) should collect all anchors needing
    resolution, call this once, then use the returned map. This avoids N+1
    external resolver calls.

    Returns:
        dict mapping anchor_id → resolved_content_or_None
    """
    # Feature flag bypass
    if os.environ.get("TOM_USE_RESOLVE_CONTENT", "1") == "0":
        return {
            a.get("id", ""): a.get("content", "")
            for a in anchors
        }

    results: Dict[str, Optional[str]] = {}

    # Partition anchors
    has_content = []
    local_refs = []
    ext_refs = []

    for anchor in anchors:
        anchor_id = anchor.get("id", "")
        content = anchor.get("content", "")
        if content and content.strip():
            results[anchor_id] = content
            continue

        ref = anchor.get("raw_content_ref", "")
        if ref and ref.startswith("ext://"):
            ext_refs.append(anchor)
        elif ref and ref.startswith("file://"):
            local_refs.append(anchor)
        else:
            results[anchor_id] = _apply_fallback(anchor, purpose)

    # Resolve local file refs
    for anchor in local_refs:
        anchor_id = anchor.get("id", "")
        ref = anchor.get("raw_content_ref", "")
        resolved = _resolve_file_ref(ref)
        if resolved:
            results[anchor_id] = resolved
        else:
            results[anchor_id] = _apply_fallback(anchor, purpose)

    # Batch resolve external refs
    if ext_refs:
        batch_results = _resolve_external_batch(ext_refs)
        for anchor in ext_refs:
            anchor_id = anchor.get("id", "")
            ref = anchor.get("raw_content_ref", "")
            ext_content = batch_results.get(ref)
            if ext_content:
                # Integrity check: verify hash matches source_content_hash
                source_hash = anchor.get("source_content_hash")
                if source_hash:
                    import hashlib
                    resolved_hash = hashlib.sha256(ext_content.strip().lower().encode()).hexdigest()[:12]
                    if resolved_hash != source_hash:
                        _emit_telemetry("content_hash_mismatch", anchor_id, purpose)
                        results[anchor_id] = _apply_fallback(anchor, purpose)
                        continue
                results[anchor_id] = ext_content
            else:
                results[anchor_id] = _apply_fallback(anchor, purpose)

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_ref(ref: str) -> Optional[str]:
    """Resolve a raw_content_ref to content."""
    if not ref:
        return None

    if ref.startswith("file://"):
        return _resolve_file_ref(ref)
    elif ref.startswith("ext://"):
        # Single ext:// refs are resolved via the batch path
        # to avoid N+1 calls. For single-anchor resolve_content(),
        # we make a minimal batch call.
        return _resolve_single_ext_ref(ref)

    return None


def _resolve_file_ref(ref: str) -> Optional[str]:
    """Read content from a file:// reference.

    Format: file://{abs_path} or file://{abs_path}#{offset}:{length}
    """
    try:
        path_part = ref[7:]  # Strip "file://"

        # Check for chunk offset
        offset = None
        length = None
        if "#" in path_part:
            path_part, fragment = path_part.rsplit("#", 1)
            if ":" in fragment:
                parts = fragment.split(":")
                offset = int(parts[0])
                length = int(parts[1])

        if not os.path.isfile(path_part):
            return None

        with open(path_part, "r", encoding="utf-8", errors="replace") as f:
            if offset is not None and length is not None:
                f.seek(offset)
                return f.read(length)
            return f.read()

    except Exception:
        return None


def _resolve_single_ext_ref(ref: str) -> Optional[str]:
    """Resolve a single ext:// ref via the batch resolver (minimal call)."""
    # Construct a minimal anchor for batch resolution
    fake_anchor = {"id": "_single", "raw_content_ref": ref}
    batch_result = _resolve_external_batch([fake_anchor])
    return batch_result.get(ref)


# External resolver endpoint — set externally for integration
_external_resolver_url: Optional[str] = None
_external_resolver_timeout_ms: int = 5000


def set_external_resolver(url: str, timeout_ms: int = 5000) -> None:
    """Configure the external content resolver endpoint."""
    global _external_resolver_url, _external_resolver_timeout_ms
    _external_resolver_url = url
    _external_resolver_timeout_ms = timeout_ms


def _resolve_external_batch(anchors: List[dict]) -> Dict[str, Optional[str]]:
    """Call POST /api/content/resolve for ext:// refs.

    Batches in chunks of <= 50 refs per request.
    Returns: {ref_string: content_or_None}
    """
    if not _external_resolver_url:
        return {}

    results: Dict[str, Optional[str]] = {}

    # Collect all ext:// refs
    refs_to_resolve = []
    for anchor in anchors:
        ref = anchor.get("raw_content_ref", "")
        if ref and ref.startswith("ext://"):
            # Extract org_id from ref: ext://{org_id}/{doc_id}/{chunk_id}
            parts = ref[6:].split("/", 1)  # Strip "ext://"
            purpose = "bm25"  # Default; in batch resolve, purpose is informational
            refs_to_resolve.append({"ref": ref, "purpose": purpose})

    if not refs_to_resolve:
        return results

    # Batch in chunks of 50
    batch_size = 50
    timeout_s = _external_resolver_timeout_ms / 1000.0

    for i in range(0, len(refs_to_resolve), batch_size):
        batch = refs_to_resolve[i:i + batch_size]

        # Extract org_id from first ref for request body
        first_ref = batch[0]["ref"]
        org_id = first_ref[6:].split("/")[0] if first_ref.startswith("ext://") else ""

        try:
            import requests
            response = requests.post(
                _external_resolver_url,
                json={"org_id": org_id, "refs": batch},
                timeout=timeout_s,
            )
            if response.status_code == 200:
                data = response.json()
                for item in data.get("results", []):
                    ref = item.get("ref", "")
                    content = item.get("content")
                    status = item.get("status", "")
                    if status == "ok" and content:
                        results[ref] = content
        except Exception:
            pass  # Timeout or error — caller handles fallback

    return results


def _apply_fallback(anchor: dict, purpose: str) -> Optional[str]:
    """Apply purpose-dependent fallback for unresolvable anchors."""
    anchor_id = anchor.get("id", "")

    if purpose in ("bm25", "dsi"):
        _emit_telemetry("resolution_skip", anchor_id, purpose)
        return None
    elif purpose in ("prompt", "graph"):
        summary = anchor.get("content_summary", "")
        if summary and summary.strip():
            # No telemetry event for successful summary fallback
            return summary

    _emit_telemetry("resolution_miss", anchor_id, purpose)
    return None
