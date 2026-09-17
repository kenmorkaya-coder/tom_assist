"""
Persistent Memory Store for ToMchatbot

Provides cross-session memory persistence using JSONL files.
Memories survive session resets and process restarts.

Key Features:
- JSONL file-per-tenant storage (append-only, efficient)
- Deduplication by content_hash
- Bootstrap pack loading for fresh installs
- Write-through on memory writes
- Thread-safe operations

Usage:
    from memory.persistent_store import MemoryStore

    store = MemoryStore(tenant_id="user123")
    store.load()  # Load from disk
    store.append(record)  # Write-through
    records = store.get_all()  # Get all memories
"""

import hashlib
import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# =============================================================================
# CONFIGURATION
# =============================================================================

# Default storage directory (relative to project root)
DEFAULT_STORAGE_DIR = Path(__file__).parent.parent / ".memory_store"

# Bootstrap file location
BOOTSTRAP_FILE = Path(__file__).parent / "bootstrap_memories.json"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class MemoryRecord:
    """A single memory record for persistent storage."""
    memory_id: str
    content: str
    content_hash: str
    anchor_type: str  # identity | session_constraint | preference | episodic | reference_doc | task_playbook | policy
    axis_hint: Optional[str] = None  # L | S | T
    semantic_tags: List[str] = field(default_factory=list)
    strength: float = 1.0
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: Optional[float] = None
    source_session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    # RGM metrics (persisted from write-time cognitive state)
    novelty: Optional[float] = None
    S: Optional[float] = None
    C: Optional[float] = None
    H: Optional[float] = None
    criticality: Optional[float] = None
    # Zero-copy fields (M4-M5)
    source_content_hash: Optional[str] = None  # SHA-256[:12] of original source content (dedup key for zero-copy)
    storage_policy: str = "owner_full_copy"  # "owner_full_copy" | "zero_copy_strict"
    content_summary: str = ""  # Redacted summary (MUST NOT contain raw customer text)
    raw_content_ref: Optional[str] = None  # "file://..." (local) | "ext://..." (external API)
    source_version: Optional[str] = None  # Version/timestamp of source document at ingestion time
    leaf_vec: Optional[List[float]] = None  # 8-dim semantic signature at write time

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MemoryRecord":
        """Create from dict (JSON deserialization)."""
        # Normalize metadata: legacy records may store a string path instead of dict
        if isinstance(d.get("metadata"), str):
            path_str = d["metadata"]
            d = dict(d)  # Don't mutate caller's dict
            d["metadata"] = {"path": path_str, "filename": os.path.basename(path_str)}
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @staticmethod
    def compute_content_hash(content: str) -> str:
        """Compute deterministic hash of content for deduplication."""
        return hashlib.sha256(content.strip().lower().encode()).hexdigest()[:12]


# =============================================================================
# MEMORY STORE
# =============================================================================

class MemoryStore:
    """
    Persistent memory store with JSONL file backend.

    Each tenant gets their own JSONL file:
        .memory_store/{tenant_id}.jsonl

    File format (one JSON object per line):
        {"memory_id": "...", "content": "...", ...}
        {"memory_id": "...", "content": "...", ...}
    """

    def __init__(
        self,
        tenant_id: str = "default",
        storage_dir: Optional[Path] = None,
        auto_load: bool = True,
    ):
        """
        Initialize the memory store.

        Args:
            tenant_id: Unique identifier for the tenant/user
            storage_dir: Directory for JSONL files (default: .memory_store)
            auto_load: If True, load from disk on init
        """
        self.tenant_id = tenant_id
        self.storage_dir = storage_dir or DEFAULT_STORAGE_DIR
        self._records: Dict[str, MemoryRecord] = {}  # memory_id -> record
        self._content_hashes: Set[str] = set()  # For dedup
        self._lock = threading.Lock()
        self._loaded = False

        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        if auto_load:
            self.load()

    @property
    def file_path(self) -> Path:
        """Path to the JSONL file for this tenant."""
        return self.storage_dir / f"{self.tenant_id}.jsonl"

    def load(self) -> int:
        """
        Load memories from JSONL file.

        Returns:
            Number of records loaded
        """
        with self._lock:
            if self._loaded:
                return len(self._records)

            loaded = 0

            # Load from tenant file
            if self.file_path.exists():
                try:
                    with open(self.file_path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                                record = MemoryRecord.from_dict(data)
                                self._records[record.memory_id] = record
                                # M4/DEF-03: Use canonical dedup key order
                                dedup_key = record.source_content_hash if record.source_content_hash else record.content_hash
                                self._content_hashes.add(dedup_key)
                                loaded += 1
                            except (json.JSONDecodeError, TypeError) as e:
                                print(f"[MemoryStore] Skipping malformed record: {e}")
                except IOError as e:
                    print(f"[MemoryStore] Error loading {self.file_path}: {e}")

            # Load bootstrap if store is empty
            if len(self._records) == 0:
                loaded += self._load_bootstrap()

            self._loaded = True

            # One-time migration: fix stale axis labels in bootstrap records
            overview = self._records.get("playbook_tom_overview")
            if overview and isinstance(overview.content, str) and "Sentiment" in overview.content:
                old_hash = overview.source_content_hash if overview.source_content_hash else overview.content_hash
                self._content_hashes.discard(old_hash)
                overview.content = overview.content.replace(
                    "Logic/Sentiment/Thematic", "Logical/Spatial/Temporal"
                )
                overview.content_hash = MemoryRecord.compute_content_hash(overview.content)
                new_hash = overview.source_content_hash if overview.source_content_hash else overview.content_hash
                self._content_hashes.add(new_hash)
                self._flush_to_disk()
                print("[MemoryStore] Migrated playbook_tom_overview axis labels")

            return loaded

    def _load_bootstrap(self) -> int:
        """Load bootstrap memories if available."""
        if not BOOTSTRAP_FILE.exists():
            return 0

        loaded = 0
        try:
            with open(BOOTSTRAP_FILE, "r") as f:
                bootstrap_data = json.load(f)

            for item in bootstrap_data.get("memories", []):
                # Compute content_hash before creating record if not provided
                if "content_hash" not in item and "content" in item:
                    item["content_hash"] = MemoryRecord.compute_content_hash(item["content"])
                record = MemoryRecord.from_dict(item)

                # M4/DEF-03: Canonical dedup key order for bootstrap records
                dedup_key = record.source_content_hash if record.source_content_hash else record.content_hash
                if dedup_key in self._content_hashes:
                    continue

                self._records[record.memory_id] = record
                self._content_hashes.add(dedup_key)
                loaded += 1

            if loaded > 0:
                # Persist bootstrap memories
                self._flush_to_disk()
                print(f"[MemoryStore] Loaded {loaded} bootstrap memories")
        except Exception as e:
            print(f"[MemoryStore] Error loading bootstrap: {e}")

        return loaded

    def append(
        self,
        memory_id: str,
        content: str,
        anchor_type: str,
        *,
        axis_hint: Optional[str] = None,
        semantic_tags: Optional[List[str]] = None,
        strength: float = 1.0,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        novelty: Optional[float] = None,
        S: Optional[float] = None,
        C: Optional[float] = None,
        H: Optional[float] = None,
        criticality: Optional[float] = None,
        source_content_hash: Optional[str] = None,
        storage_policy: str = "owner_full_copy",
        content_summary: str = "",
        raw_content_ref: Optional[str] = None,
        source_version: Optional[str] = None,
        leaf_vec: Optional[List[float]] = None,
    ) -> Optional[MemoryRecord]:
        """
        Append a memory record (write-through to disk).

        Dedup key order (M4/DEF-03):
          1. source_content_hash if present (zero-copy records)
          2. content_hash computed from content (full-copy records)
          3. memory_id fallback

        Returns:
            MemoryRecord if written, None if duplicate
        """
        content_hash = MemoryRecord.compute_content_hash(content)

        # M4/DEF-03: Canonical dedup key order
        dedup_key = source_content_hash if source_content_hash else content_hash

        with self._lock:
            # Dedup check
            if dedup_key in self._content_hashes:
                return None

            record = MemoryRecord(
                memory_id=memory_id,
                content=content,
                content_hash=content_hash,
                anchor_type=anchor_type,
                axis_hint=axis_hint,
                semantic_tags=semantic_tags or [],
                strength=strength,
                source_session_id=session_id,
                metadata=metadata or {},
                novelty=novelty,
                S=S,
                C=C,
                H=H,
                criticality=criticality,
                source_content_hash=source_content_hash,
                storage_policy=storage_policy,
                content_summary=content_summary,
                raw_content_ref=raw_content_ref,
                source_version=source_version,
                leaf_vec=leaf_vec,
            )

            self._records[memory_id] = record
            self._content_hashes.add(dedup_key)

            # Write-through to disk
            self._append_to_file(record)

            return record

    def _append_to_file(self, record: MemoryRecord) -> None:
        """Append a single record to the JSONL file."""
        try:
            with open(self.file_path, "a") as f:
                f.write(json.dumps(record.to_dict()) + "\n")
        except IOError as e:
            print(f"[MemoryStore] Error writing to {self.file_path}: {e}")

    def _flush_to_disk(self) -> None:
        """Rewrite entire file (used after dedup or compaction)."""
        try:
            with open(self.file_path, "w") as f:
                for record in self._records.values():
                    f.write(json.dumps(record.to_dict()) + "\n")
        except IOError as e:
            print(f"[MemoryStore] Error flushing to {self.file_path}: {e}")

    def get(self, memory_id: str) -> Optional[MemoryRecord]:
        """Get a memory by ID."""
        with self._lock:
            record = self._records.get(memory_id)
            if record:
                record.access_count += 1
                record.last_accessed = time.time()
            return record

    def get_all(self) -> List[MemoryRecord]:
        """Get all memories."""
        with self._lock:
            return list(self._records.values())

    def get_by_type(self, anchor_type: str) -> List[MemoryRecord]:
        """Get all memories of a specific type."""
        with self._lock:
            return [r for r in self._records.values() if r.anchor_type == anchor_type]

    def size(self) -> int:
        """Get number of memories."""
        with self._lock:
            return len(self._records)

    def to_anchors_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Convert to format compatible with state.memory.anchors.

        This allows hydrating controller state from persistent store.

        Returns:
            Dict mapping memory_id to anchor dict
        """
        with self._lock:
            anchors = {}
            for record in self._records.values():
                anchors[record.memory_id] = {
                    "id": record.memory_id,
                    "content": record.content,
                    "content_summary": record.content_summary or (
                        record.content[:50] + "..." if len(record.content) > 50 else record.content
                    ),
                    "content_hash": record.content_hash,
                    "anchor_type": record.anchor_type,
                    "axis_hint": record.axis_hint,
                    "semantic_tags": record.semantic_tags,
                    "anchor_strength": record.strength,
                    "metadata": record.metadata,  # Include for source_ref provenance
                    "created_tick": 0,  # Not applicable for persistent store
                    "access_count": record.access_count,
                    # Zero-copy fields (M4)
                    "source_content_hash": record.source_content_hash,
                    "storage_policy": record.storage_policy,
                    "raw_content_ref": record.raw_content_ref,
                    "source_version": record.source_version,
                    # RGM cognitive metrics (write-time snapshots)
                    "novelty_score": record.novelty,
                    "S": record.S,
                    "C": record.C,
                    "H": record.H,
                    "criticality": record.criticality,
                }
            return anchors

    def clear(self) -> None:
        """Clear all memories (for testing)."""
        with self._lock:
            self._records.clear()
            self._content_hashes.clear()
            if self.file_path.exists():
                self.file_path.unlink()


# =============================================================================
# GLOBAL STORE ACCESSOR
# =============================================================================

_global_stores: Dict[str, MemoryStore] = {}
_global_lock = threading.Lock()


def get_memory_store(tenant_id: str = "default") -> MemoryStore:
    """
    Get or create a MemoryStore for a tenant.

    Args:
        tenant_id: Tenant/user identifier

    Returns:
        MemoryStore instance
    """
    with _global_lock:
        if tenant_id not in _global_stores:
            _global_stores[tenant_id] = MemoryStore(tenant_id=tenant_id)
        return _global_stores[tenant_id]


# Track active doc_ids per tenant (for deterministic doc scoping)
_active_doc_ids: Dict[str, Set[str]] = {}


def register_active_doc(tenant_id: str, doc_id: str) -> None:
    """
    Register a document as active for a tenant.

    This enables deterministic scoping in retrieval - when a doc is active,
    retrieval will prioritize reference_doc anchors with matching DOC: tag.

    Args:
        tenant_id: Tenant/session identifier
        doc_id: Document identifier (e.g., "tom_whitepaper_v1")
    """
    with _global_lock:
        if tenant_id not in _active_doc_ids:
            _active_doc_ids[tenant_id] = set()
        _active_doc_ids[tenant_id].add(doc_id)


def get_active_doc_ids(tenant_id: str) -> List[str]:
    """
    Get list of active document IDs for a tenant.

    Returns:
        List of active doc_ids, empty if none
    """
    with _global_lock:
        return list(_active_doc_ids.get(tenant_id, set()))


def clear_active_docs(tenant_id: str) -> None:
    """Clear active documents for a tenant."""
    with _global_lock:
        if tenant_id in _active_doc_ids:
            del _active_doc_ids[tenant_id]


# =====================================================================
# STRUCTURED EVIDENCE INDEX (SEI)
# Pre-computed facts and headings from ingested documents.
# Populated during ingest_markdown_document(), queried by evidence_policy.
# =====================================================================

SEI_VERSION = 1

# tenant_id -> doc_id -> sei_data
_sei_store: Dict[str, Dict[str, Dict[str, Any]]] = {}


def register_sei(
    tenant_id: str,
    doc_id: str,
    doc_hash: str,
    facts: Dict[str, Dict[str, Any]],
    headings: List[Dict[str, Any]],
) -> None:
    """Register a Structured Evidence Index entry for a document."""
    with _global_lock:
        if tenant_id not in _sei_store:
            _sei_store[tenant_id] = {}
        _sei_store[tenant_id][doc_id] = {
            "sei_version": SEI_VERSION,
            "doc_id": doc_id,
            "doc_hash": doc_hash,
            "facts": facts,
            "headings": headings,
        }


def get_sei(tenant_id: str, doc_id: str) -> Optional[Dict[str, Any]]:
    """Get SEI entry for a specific document."""
    with _global_lock:
        return _sei_store.get(tenant_id, {}).get(doc_id)


def query_sei_fact(tenant_id: str, key: str, doc_ids: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Look up a fact by key, optionally scoped to active doc_ids."""
    with _global_lock:
        tenant_docs = _sei_store.get(tenant_id, {})
        for doc_id, sei_entry in tenant_docs.items():
            if doc_ids is not None and doc_id not in doc_ids:
                continue
            facts = sei_entry.get("facts", {})
            if key in facts:
                fact = facts[key]
                return {
                    "value": fact["value"],
                    "doc_id": doc_id,
                    "section_id": fact.get("section_id", ""),
                    "line": fact.get("line", 0),
                    "raw": fact.get("raw", ""),
                }
    return None


def query_sei_heading_count(
    tenant_id: str,
    parent_section: str,
    heading_level: int,
    doc_ids: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Count headings with matching parent and level, optionally scoped to active doc_ids."""
    with _global_lock:
        tenant_docs = _sei_store.get(tenant_id, {})
        for doc_id, sei_entry in tenant_docs.items():
            if doc_ids is not None and doc_id not in doc_ids:
                continue
            all_headings = sei_entry.get("headings", [])
            matched = [
                h for h in all_headings
                if h.get("parent") == parent_section
                and h.get("level") == heading_level
            ]
            if matched:
                return {
                    "count": len(matched),
                    "doc_id": doc_id,
                    "headings": matched,
                }
    return None


def clear_sei(tenant_id: str) -> None:
    """Clear SEI data for a tenant."""
    with _global_lock:
        if tenant_id in _sei_store:
            del _sei_store[tenant_id]


# ---------------------------------------------------------------------------
# Document Skills Index (DSI)
# Maps query topics → subsections with character offsets for deterministic
# subsection extraction. Populated at document ingestion time.
#
# Design principles:
# - NO hardcoded stopwords or language-specific lists
# - All vocabulary discrimination is document-derived (IDF from full content)
# - Unicode tokenisation (works for any language)
# - Structure over language: heading hierarchy, bold, list leaders
# ---------------------------------------------------------------------------

DSI_VERSION = 3
_dsi_store: Dict[str, Dict[str, Dict[str, Any]]] = {}  # tenant_id → doc_id → dsi_data


def _dsi_tokenize(text: str) -> Set[str]:
    """Language-agnostic Unicode tokeniser for DSI.

    Uses NFKC normalisation + casefold + Unicode word extraction.
    Returns set of tokens with len >= 2.
    """
    import re as _re
    import unicodedata
    norm = unicodedata.normalize("NFKC", text).casefold()
    # \w matches Unicode letters, digits, underscore
    tokens = _re.findall(r'[\w]+', norm, _re.UNICODE)
    return {t for t in tokens if len(t) >= 2}


def _compute_content_idf(skills: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compute IDF from full subsection content tokens.

    Uses content_tokens (all tokens from subsection text) for DF computation.
    This gives natural language frequency: common words like "the", "and"
    appear in most subsections → low IDF. Domain terms appear in few → high IDF.

    idf(t) = log((N + 1) / (df(t) + 1)) + 1
    """
    import math
    n = len(skills)
    token_df: Dict[str, int] = {}
    for skill in skills:
        # Use content_tokens if available (all tokens from subsection text)
        # Fall back to topics + title tokens
        content_toks = skill.get("content_tokens")
        if content_toks:
            unique = set(content_toks)
        else:
            unique = set(skill.get("topics", []))
            unique |= _dsi_tokenize(skill.get("title", ""))
        for t in unique:
            token_df[t] = token_df.get(t, 0) + 1
    idf = {}
    for t, df in token_df.items():
        idf[t] = math.log((n + 1) / (df + 1)) + 1
    return idf


def register_dsi(
    tenant_id: str,
    doc_id: str,
    doc_hash: str,
    skills: List[Dict[str, Any]],
) -> None:
    """Store DSI entry with content-derived IDF. Thread-safe via _global_lock."""
    idf = _compute_content_idf(skills)
    entry = {
        "dsi_version": DSI_VERSION,
        "doc_id": doc_id,
        "doc_hash": doc_hash,
        "skills": skills,
        "idf": idf,
        "n_skills": len(skills),
    }
    with _global_lock:
        if tenant_id not in _dsi_store:
            _dsi_store[tenant_id] = {}
        _dsi_store[tenant_id][doc_id] = entry


def query_dsi_section(
    tenant_id: str,
    query: str,
    doc_ids: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Find best-matching DSI skill using IDF-weighted scoring.

    Language-agnostic, no hardcoded stopwords. All discrimination
    comes from document-derived IDF weights.

    Algorithm:
    1. Unicode-tokenize query.
    2. For each verified skill:
       a. Match query tokens against skill topics + title tokens
       b. title_idf = sum of IDF for tokens matching the title
       c. topic_idf = sum of IDF for all matched tokens
       d. score = 2 * title_idf + topic_idf
          (title gets 2x weight because heading structure is
           the strongest language-agnostic signal)
    3. Require score >= threshold AND relative margin vs runner-up.
    4. Return best match or None.
    """
    if not tenant_id or not query:
        return None

    with _global_lock:
        tenant_docs = _dsi_store.get(tenant_id)
        if not tenant_docs:
            return None

        q_tokens = _dsi_tokenize(query)
        if not q_tokens:
            return None

        best = None
        best_score = 0.0
        runner_up_score = 0.0

        for doc_id, dsi_entry in tenant_docs.items():
            if doc_ids is not None and doc_id not in doc_ids:
                continue
            idf = dsi_entry.get("idf", {})
            doc_hash = dsi_entry.get("doc_hash", "")

            for skill in dsi_entry.get("skills", []):
                if not skill.get("verified", False):
                    continue

                topics = set(skill.get("topics", []))
                title_tokens = _dsi_tokenize(skill.get("title", ""))

                # IDF-weighted overlap against topics + title
                topic_matched = q_tokens & topics
                title_matched = q_tokens & title_tokens

                all_matched = topic_matched | title_matched
                if not all_matched:
                    continue

                # Score: title overlap weighted 2x (structure signal)
                topic_idf = sum(idf.get(t, 0.0) for t in all_matched)
                title_idf = sum(idf.get(t, 0.0) for t in title_matched)
                score = 2.0 * title_idf + topic_idf

                # Track best and runner-up
                if score > best_score:
                    runner_up_score = best_score
                    best_score = score
                    best = {
                        "section_id": skill.get("section_id", ""),
                        "parent_chunk_id": skill.get("parent_chunk_id", ""),
                        "title": skill.get("title", ""),
                        "match_score": round(score, 2),
                        "doc_id": skill.get("doc_id", doc_id),
                        "doc_hash": doc_hash,
                        "content_start": skill.get("content_start", 0),
                        "content_end": skill.get("content_end", 0),
                        "topics": skill.get("topics", []),
                    }
                elif score > runner_up_score:
                    runner_up_score = score

        if best is None or best_score < 3.0:
            return None

        # Relative margin: best must exceed runner-up by >= 50%
        # This prevents ambiguous matches where multiple sections score similarly
        if runner_up_score > 0 and best_score < runner_up_score * 1.5:
            return None

        return best


def get_dsi(tenant_id: str, doc_id: str) -> Optional[Dict[str, Any]]:
    """Get full DSI for a document."""
    with _global_lock:
        tenant_docs = _dsi_store.get(tenant_id)
        if not tenant_docs:
            return None
        return tenant_docs.get(doc_id)


def get_idf_scores(tenant_id: str, doc_ids: Optional[List[str]] = None) -> Dict[str, float]:
    """Get merged IDF scores, optionally scoped to active doc_ids.

    Returns token → IDF score mapping. Used for language-agnostic
    low-information token filtering (replaces hardcoded stop word lists).
    """
    merged: Dict[str, float] = {}
    with _global_lock:
        tenant_docs = _dsi_store.get(tenant_id, {})
        for doc_id, dsi_entry in tenant_docs.items():
            if doc_ids is not None and doc_id not in doc_ids:
                continue
            idf = dsi_entry.get("idf", {})
            for token, score in idf.items():
                # Keep max IDF across documents (most discriminating)
                if score > merged.get(token, 0.0):
                    merged[token] = score
    return merged


def clear_dsi(tenant_id: str) -> None:
    """Clear DSI data for a tenant."""
    with _global_lock:
        if tenant_id in _dsi_store:
            del _dsi_store[tenant_id]


def hydrate_state_memory(state: Any, tenant_id: str = "default", org_id: Optional[str] = None) -> int:
    """
    Hydrate state.memory.anchors from persistent store.

    Loads from "default" (user-level) first, then the org-level store (ingested
    documents), then overlays session-specific store.  This ensures baseline
    preferences/docs are always available, ingested knowledge is accessible,
    and session constraints can override for the current session.

    Args:
        state: ToMStateV4P2 instance
        tenant_id: Session-specific tenant ID (treated as session_id)
        org_id: Org-level tenant ID for ingested documents (e.g. from knowledge sources)

    Returns:
        Number of memories hydrated
    """
    if state is None:
        return 0

    # Get or create memory object on state
    memory = getattr(state, "memory", None)
    if memory is None:
        try:
            from types import SimpleNamespace
            state.memory = SimpleNamespace(anchors={})
            memory = state.memory
        except Exception:
            return 0

    # Ensure anchors dict exists
    if not hasattr(memory, "anchors"):
        memory.anchors = {}

    hydrated = 0
    session_id = tenant_id  # tenant_id IS the session_id (no prefix)

    # 1. Load user-level store ("default") - baseline preferences, reference docs
    user_store = get_memory_store("default")
    user_anchors = user_store.to_anchors_dict()
    for mem_id, anchor in user_anchors.items():
        if mem_id not in memory.anchors:
            memory.anchors[mem_id] = anchor
            hydrated += 1

    # 2. Load org-level store (ingested documents from knowledge sources)
    if org_id and org_id != "default" and org_id != session_id:
        org_store = get_memory_store(org_id)
        org_anchors = org_store.to_anchors_dict()
        for mem_id, anchor in org_anchors.items():
            if mem_id not in memory.anchors:
                memory.anchors[mem_id] = anchor
                hydrated += 1

    # 3. Overlay session-specific store (can override)
    if session_id and session_id != "default":
        session_store = get_memory_store(session_id)
        session_anchors = session_store.to_anchors_dict()
        for mem_id, anchor in session_anchors.items():
            memory.anchors[mem_id] = anchor  # Session overrides user
            hydrated += 1

    # 4. Merge active_doc_ids from all levels
    active_docs = get_active_doc_ids("default")
    if org_id and org_id != "default":
        org_docs = get_active_doc_ids(org_id)
        active_docs.extend(org_docs)
    if session_id and session_id != "default":
        session_docs = get_active_doc_ids(session_id)
        active_docs.extend(session_docs)
    if active_docs:
        memory.active_doc_ids = list(set(active_docs))  # Dedupe

    return hydrated


def persist_memory(
    memory_id: str,
    content: str,
    anchor_type: str,
    *,
    tenant_id: str = "default",
    axis_hint: Optional[str] = None,
    session_id: Optional[str] = None,
    semantic_tags: Optional[List[str]] = None,
    strength: float = 1.0,
    metadata: Optional[Dict[str, Any]] = None,
    novelty: Optional[float] = None,
    S: Optional[float] = None,
    C: Optional[float] = None,
    H: Optional[float] = None,
    criticality: Optional[float] = None,
    source_content_hash: Optional[str] = None,
    storage_policy: str = "owner_full_copy",
    content_summary: str = "",
    raw_content_ref: Optional[str] = None,
    source_version: Optional[str] = None,
    leaf_vec: Optional[List[float]] = None,
) -> bool:
    """
    Persist a memory to the store (write-through).

    Args:
        memory_id: Memory ID
        content: Memory content
        anchor_type: Anchor type
        tenant_id: Tenant ID
        axis_hint: Semantic axis hint
        session_id: Source session
        semantic_tags: Tags for retrieval filtering (e.g., ["DOC:doc_id", "SECTION:7"])
        strength: Memory strength (0-1)
        metadata: Additional metadata
        novelty: Novelty score at write time (0-1)
        S: Stability at write time (0-1)
        C: Coherence at write time (0-1)
        H: Entropy at write time (0-1)
        criticality: Criticality at write time (0-1)
        source_content_hash: SHA-256[:12] of original source content (dedup key for zero-copy)
        storage_policy: "owner_full_copy" or "zero_copy_strict"
        content_summary: Redacted summary for zero-copy records
        raw_content_ref: Content reference URI (file:// or ext://)
        source_version: Version/timestamp of source document at ingestion time
        leaf_vec: 8-dim semantic signature at write time

    Returns:
        True if written, False if duplicate
    """
    store = get_memory_store(tenant_id)
    record = store.append(
        memory_id=memory_id,
        content=content,
        anchor_type=anchor_type,
        axis_hint=axis_hint,
        session_id=session_id,
        semantic_tags=semantic_tags,
        strength=strength,
        metadata=metadata,
        novelty=novelty,
        S=S,
        C=C,
        H=H,
        criticality=criticality,
        source_content_hash=source_content_hash,
        storage_policy=storage_policy,
        content_summary=content_summary,
        raw_content_ref=raw_content_ref,
        source_version=source_version,
        leaf_vec=leaf_vec,
    )
    return record is not None


# =============================================================================
# TEST HELPER
# =============================================================================

def seed_memory_store(
    state: Any,
    memories: List[Dict[str, Any]],
    *,
    tenant_id: str = "test",
    clear_first: bool = True,
) -> int:
    """
    Seed memory store with test fixtures.

    Use this in tests to inject deterministic memories before running prompts.

    Args:
        state: ToMStateV4P2 instance (or None to use only persistent store)
        memories: List of memory dicts with keys:
            - memory_id: str
            - content: str
            - anchor_type: str
            - axis_hint: Optional[str]
        tenant_id: Tenant ID for isolation
        clear_first: If True, clear existing memories first

    Returns:
        Number of memories seeded

    Example:
        seed_memory_store(controller.state, [
            {
                "memory_id": "constraint_test_001",
                "content": "Keep responses concise.",
                "anchor_type": "session_constraint",
                "axis_hint": "L",
            },
            {
                "memory_id": "preference_test_001",
                "content": "User prefers technical explanations.",
                "anchor_type": "preference",
            },
        ])
    """
    store = get_memory_store(tenant_id)

    if clear_first:
        store.clear()
        # Also clear state memory if provided
        if state is not None:
            memory = getattr(state, "memory", None)
            if memory is not None and hasattr(memory, "anchors"):
                memory.anchors.clear()

    seeded = 0
    for mem in memories:
        record = store.append(
            memory_id=mem["memory_id"],
            content=mem["content"],
            anchor_type=mem["anchor_type"],
            axis_hint=mem.get("axis_hint"),
            semantic_tags=mem.get("semantic_tags", []),
            strength=mem.get("strength", 1.0),
        )
        if record is not None:
            seeded += 1

    # Hydrate state if provided
    if state is not None:
        hydrate_state_memory(state, tenant_id)

    return seeded
