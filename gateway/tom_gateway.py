#!/usr/bin/env python3
"""Tom Assist boundary to the pinned read-only tom_master runtime.

The process owns one direct TreeGrowthEngine + ReflectionGatedMemory composition
per Tom Assist project. Preview never calls the client processing surface, the
SICD step surface, or RGM plastic recall. Explicit turn commit is the sole path
that advances the engine and writes an RGM anchor.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import hmac
import json
import logging
import os
import re
import shutil
import socketserver
import sqlite3
import subprocess
import sys
import tempfile
import threading
import uuid
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

PINNED_SHA = "e9fdef81c"
STATE_FORMAT_VERSION = "sicd-engine-save/1"
GATEWAY_VERSION = "tom-gateway/1.0"
SEED_PROFILE = "msr_8d_native_10k"
SEED_ARTIFACT_RELATIVE = Path("sandbox/scaling/snapshots/msr_8d_native_10k_tiered.json")
SEED_ARTIFACT_SHA256 = "d9aec9b424459d0948f569c7e424bb5632bd118ad01bda372f62df7ca17a82ac"
SEED_TICK = 4707
SEED_BRANCH_COUNT = 10_000
MECHANICS_PROFILE_RELATIVE = Path("config/profiles/msr_8d_native_10k.env")
EFFECTIVE_KAPPA_DECAY = 0.03
KAPPA_DECAY_SOURCE = "profile_env_reader_wp18_effective_0.03"
REQUIRED_KAPPA_PARAMETERS = frozenset(
    {
        "TOM_TAU1",
        "TOM_HEAL_RATE",
        "TOM_DAMAGE_RATE",
        "TOM_KAPPA_DECAY",
        "TOM_KAPPA_DELTA_CAP",
        "TOM_KAPPA_NOURISH_RECOVERY",
    }
)
DEFAULT_TOM_MASTER = Path("/Users/kenmorkaya/PycharmProjects/tom_master")
DEFAULT_DATA_DIR = Path.home() / "Library" / "Application Support" / "TomAssist"
MAX_REQUEST_BYTES = 2 * 1024 * 1024

LOGGER = logging.getLogger("tom_assist.gateway")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gateway.structural_preview import POLICY_VERSION, project_text, select_cohort, fuse_anchors
from gateway.permanent_library import PermanentLibrary, content_hash
from gateway.document_ingestion import (
    DOCUMENT_CHUNKING_VERSION,
    DOCUMENT_EMBEDDING_VERSION,
    DOCUMENT_PACKET_ADMISSION_VERSION,
    DocumentEmbeddingWorkerClient,
    MAX_DOCUMENT_CHUNKS,
    MAX_DOCUMENT_SOURCE_CHARS,
    build_document_query_profile,
    rank_document_chunks_for_packet,
)
from gateway.document_research import parse_research_intent
from gateway.declared_structure import (
    DECLARED_STRUCTURE_VERSION,
    build_declared_structure,
)
from gateway.project_glossary import (
    GLOSSARY_VERSION,
    MAX_GLOSSARY_CHARACTERS,
    MAX_GLOSSARY_TERMS,
    build_project_glossary,
)

COMMIT_DYNAMICS = ["step", "rgm_write", "leaf_vec_teach", "usage_rotation", "front_row_reseat"]
DEFAULT_SETTINGS = {"front_row_capacity": 4096, "teach_on_conflict": True}


class DocumentTreeMigrationRequired(ValueError):
    """Raised when retained documents need an explicit project-Tree migration."""


def canonical_json(value: Any) -> bytes:
    """Mirror D10 for JSON values accepted by the gateway."""
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_profile_environment(path: Path) -> dict[str, str]:
    """Parse the pinned shell profile without executing it, then apply it exactly."""
    if not path.is_file():
        raise ValueError(f"mechanics profile missing: {path}")
    parameters: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"export\s+(TOM_[A-Z0-9_]+)=(.*)", line)
        if match is None:
            raise ValueError(f"unsupported mechanics profile syntax at {path}:{line_number}")
        key, value = match.groups()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        parameters[key] = value
    missing = sorted(REQUIRED_KAPPA_PARAMETERS - parameters.keys())
    if missing:
        raise ValueError(f"mechanics profile missing required kappa parameters: {', '.join(missing)}")
    os.environ.update(parameters)
    return parameters


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _actual_sha(tom_master: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(tom_master), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _safe_project_id(project_id: Any) -> str:
    value = str(project_id or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ValueError("project_id must contain only letters, digits, underscore, or hyphen")
    return value


@dataclass(frozen=True)
class _RetrievalTrigger:
    """Pure subset of the pinned runtime's structural trigger record."""

    trigger_type: str
    intent: str | None = None
    query_keys: list[str] = field(default_factory=list)
    trigger_reason: str = ""


@dataclass(frozen=True)
class SeedConfiguration:
    profile: str
    artifact_path: Path
    artifact_sha256: str
    tick: int
    branch_count: int
    mechanics_profile_path: Path
    mechanics_profile_sha256: str
    mechanics_parameters: dict[str, str]


def _engine_config(seed: SeedConfiguration) -> Any:
    """Build the single audited Python 10K mechanics configuration."""
    from agency.mechanics.sicd_engine import TreeGrowthConfig

    config = TreeGrowthConfig()
    parameters = seed.mechanics_parameters
    config.tau1 = float(parameters["TOM_TAU1"])
    config.kappa_update.heal_rate = float(parameters["TOM_HEAL_RATE"])
    config.kappa_update.damage_rate = float(parameters["TOM_DAMAGE_RATE"])
    config.kappa_update.kappa_decay = float(parameters["TOM_KAPPA_DECAY"])
    if not abs(config.kappa_update.kappa_decay - EFFECTIVE_KAPPA_DECAY) <= 1e-12:
        raise ValueError("kappa_decay differs from audited effective physics (0.03)")
    config.kappa_update.kappa_delta_cap = float(parameters["TOM_KAPPA_DELTA_CAP"])
    config.kappa_update.kappa_nourish_recovery = float(
        parameters["TOM_KAPPA_NOURISH_RECOVERY"]
    )
    return config


def _compute_preview_triggers(committed_turn_count: int) -> list[_RetrievalTrigger]:
    """Mirror the only trigger applicable to draft preview without importing interface.__init__."""
    if committed_turn_count < 3:
        return []
    bounded_count = min(3, committed_turn_count)
    return [
        _RetrievalTrigger(
            trigger_type="conversation_continuity",
            trigger_reason=f"Ongoing conversation ({bounded_count} turns)",
        )
    ]


class ProjectRuntime:
    """One isolated direct engine+RGM composition with exact save artifacts."""

    def __init__(
        self,
        project_id: str,
        state_dir: Path,
        runtime_sha: str,
        seed: SeedConfiguration,
        document_embedding_provider=None,
        document_index=None,
        allow_document_index_migration: bool = False,
        document_research_cursor_key: bytes | None = None,
    ) -> None:
        self.project_id = _safe_project_id(project_id)
        self.state_dir = state_dir.resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.state_dir, 0o700)
        self.runtime_sha = runtime_sha
        self.seed = seed
        if (
            not isinstance(document_research_cursor_key, bytes)
            or len(document_research_cursor_key) != 32
        ):
            raise ValueError("document research cursor key is unavailable")
        self.document_research_cursor_key = document_research_cursor_key
        self.document_embedding_provider = document_embedding_provider
        self.lock = threading.RLock()
        self._idempotency_path = self.state_dir / "turn_idempotency.json"
        index_dir = self.state_dir / "document-index"
        index_files = (index_dir / "tree_state.json", index_dir / "receipts.sqlite3")
        index_presence = tuple(path.exists() for path in index_files)
        if any(index_presence) and not all(index_presence):
            raise DocumentTreeMigrationRequired(
                "project document Tree migration is incomplete; run the explicit migration"
            )
        library_path = self.state_dir / "library.sqlite3"
        retained_document_count = 0
        if library_path.is_file() and not all(index_presence):
            wal_path = Path(str(library_path) + "-wal")
            probe_mode = (
                "?mode=ro" if wal_path.is_file() and wal_path.stat().st_size > 0
                else "?mode=ro&immutable=1"
            )
            probe = sqlite3.connect(
                library_path.resolve().as_uri() + probe_mode, uri=True,
            )
            try:
                present = probe.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='documents'"
                ).fetchone()
                if present is not None:
                    retained_document_count = int(
                        probe.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
                    )
            finally:
                probe.close()
        if (
            document_index is None
            and retained_document_count > 0
            and not all(index_presence)
            and not allow_document_index_migration
        ):
            raise DocumentTreeMigrationRequired(
                "project has retained documents but no dedicated document Tree; "
                "run the explicit project document-Tree migration before preview"
            )
        self.library = PermanentLibrary(library_path)
        self._backfill_declared_document_structures()
        if document_index is None:
            from gateway.document_tree import ProjectDocumentTreeIndex
            document_index = ProjectDocumentTreeIndex(
                self.state_dir, self.project_id, self.seed, _engine_config(self.seed),
            )
        elif getattr(document_index, "project_id", None) != self.project_id:
            self.library.db.close()
            raise ValueError("project runtime refuses a foreign document Tree")
        self.document_index = document_index
        head = self.library.head()
        self.settings = json.loads(head[3]) if head else dict(DEFAULT_SETTINGS)
        if head:
            self._write_head_artifacts(head)
        self._idempotency: dict[str, dict[str, Any]] = self._load_idempotency()

        # Direct composition is the contract-authorized alternative to
        # create_client (external_api.py:2722). It keeps runtime state in this
        # project's exact directory and avoids controller-owned provider paths.
        from agency.mechanics.sicd_engine import TreeGrowthEngine
        from gateway.front_row import FrontRowMemory as ReflectionGatedMemory

        fresh_project = not self._tree_path.exists()
        config = self._new_engine_config()
        if fresh_project:
            actual_sha256 = _sha256_file(self.seed.artifact_path) if self.seed.artifact_path.is_file() else "missing"
            if actual_sha256 != self.seed.artifact_sha256:
                raise ValueError(
                    "seed artifact sha256 mismatch: "
                    f"expected {self.seed.artifact_sha256}, got {actual_sha256}"
                )
            self.engine = TreeGrowthEngine.load(str(self.seed.artifact_path), cfg=config)
            actual_tick = int(getattr(self.engine.state, "tick", 0) or 0)
            actual_branches = len(getattr(self.engine.state, "branches", {}) or {})
            if actual_tick != self.seed.tick or actual_branches != self.seed.branch_count:
                raise ValueError(
                    "seed artifact lineage mismatch after load: "
                    f"expected tick/branches {self.seed.tick}/{self.seed.branch_count}, "
                    f"got {actual_tick}/{actual_branches}"
                )
            self.rgm = ReflectionGatedMemory(self.library, self.settings["front_row_capacity"])
            initial_digest = self._persist_current_artifacts()
            self.creation_metadata = self._seed_creation_metadata(initial_digest)
            _atomic_write(self._creation_metadata_path, canonical_json(self.creation_metadata))
        else:
            self.engine = TreeGrowthEngine.load(str(self._tree_path), cfg=config)
            self.rgm = ReflectionGatedMemory(self.library, self.settings["front_row_capacity"])
            if self._rgm_path.exists():
                self.rgm.restore(self._rgm_path.read_text(encoding="utf-8"))
                self._checkpoint_digest = self._compute_checkpoint_digest()
            else:
                self._checkpoint_digest = self._persist_current_artifacts()
            self.creation_metadata = self._load_creation_metadata()
            self._restore_serialized_fields()
        self._assert_native_10k_tree_lineage()
        # Legacy short anchors can be migrated losslessly. Never pretend a
        # truncated summary is the durable twin of unavailable original content.
        for record in self.rgm.state.anchors.values():
            self.library.retain(record, self.rgm._record_to_dict(record))
        if head is None:
            self.library.set_head(self._tree_path.read_bytes(), self._rgm_path.read_bytes(),
                                  self._idempotency, self.settings)
        self._backfill_document_index(
            allow_missing=allow_document_index_migration,
        )

    def _backfill_declared_document_structures(self) -> None:
        """Migrate pre-WP-43 immutable documents using only their stored text."""
        pending = []
        for row in self.library.documents(include_withdrawn=True):
            document = self.library.document(row["document_id"], include_chunks=False)
            if document["declared_structure"] is None:
                pending.append((document["document_id"], document["content"]))
        if not pending:
            return
        self.library.db.execute("BEGIN IMMEDIATE")
        try:
            for document_id, content in pending:
                self.library.retain_document_declared_structure(
                    document_id, build_declared_structure(content),
                )
            self.library.db.execute("COMMIT")
        except BaseException:
            if self.library.db.in_transaction:
                self.library.db.execute("ROLLBACK")
            raise

    @property
    def _tree_path(self) -> Path:
        return self.state_dir / "tree_state.json"

    @property
    def _rgm_path(self) -> Path:
        return self.state_dir / "rgm_state.json"

    @property
    def _creation_metadata_path(self) -> Path:
        return self.state_dir / "creation_metadata.json"

    def _backfill_document_index(self, *, allow_missing: bool = False) -> None:
        """Validate receipts, or explicitly migrate retained pre-index documents."""
        committed = self.document_index.project_commits(self.project_id)
        if committed:
            self.library.db.execute("BEGIN IMMEDIATE")
            try:
                by_document = {}
                for row in committed:
                    by_document.setdefault(row["document_id"], []).append(row)
                for document_id, rows in by_document.items():
                    self.document_index.set_project_chunk_analyses(
                        self.library,
                        document_id,
                        [{"chunk_index": row["chunk_index"]} for row in rows],
                        [row["analysis"] for row in rows],
                    )
                self.library.db.execute("COMMIT")
            except BaseException:
                if self.library.db.in_transaction:
                    self.library.db.execute("ROLLBACK")
                raise
        existing = self.document_index.indexed_chunk_keys(self.project_id)
        for document_row in self.library.documents(include_withdrawn=True):
            document_id = document_row["document_id"]
            chunks = self.library.document_chunks(document_id=document_id)
            missing = [
                row for row in chunks
                if (document_id, row["chunk_index"]) not in existing
            ]
            if not missing:
                continue
            if not allow_missing:
                raise DocumentTreeMigrationRequired(
                    "project document Tree is missing retained document receipts; "
                    "run the explicit project document-Tree migration before preview"
                )
            tree_bytes, receipts, analyses = self.document_index.apply_document(
                self.project_id,
                document_id,
                missing,
                self.library.document_declared_structure(document_id),
                "backfilled",
                "migration:tom-assist-project-document-tree/2.0",
            )
            self.library.db.execute("BEGIN IMMEDIATE")
            try:
                self.document_index.set_project_chunk_analyses(
                    self.library, document_id, receipts, analyses,
                )
                self.library.db.execute("COMMIT")
            except BaseException:
                if self.library.db.in_transaction:
                    self.library.db.execute("ROLLBACK")
                raise
            if document_row["tombstoned_at"] is not None:
                self.document_index.record_withdrawal(
                    self.project_id, document_id, document_row["tombstoned_at"],
                )

    def _new_engine_config(self) -> Any:
        """Apply the audited profile and reject unreviewed effective-physics changes."""
        return _engine_config(self.seed)

    def _seed_creation_metadata(self, initial_checkpoint_digest: str) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "runtime_version": self.runtime_sha,
            "seed_profile": self.seed.profile,
            "seed_artifact_sha256": self.seed.artifact_sha256,
            "seed_tick": self.seed.tick,
            "seed_branch_count": self.seed.branch_count,
            "mechanics_profile": self.seed.mechanics_profile_path.name,
            "mechanics_profile_sha256": self.seed.mechanics_profile_sha256,
            "mechanics_parameters": dict(sorted(self.seed.mechanics_parameters.items())),
            "kappa_decay_source": KAPPA_DECAY_SOURCE,
            "initial_checkpoint_digest": initial_checkpoint_digest,
        }

    def _assert_native_10k_tree_lineage(self) -> None:
        """Fail closed before any 17D projection can reach a non-native tree."""
        expected = {
            "seed_profile": SEED_PROFILE,
            "seed_artifact_sha256": SEED_ARTIFACT_SHA256,
            "seed_tick": SEED_TICK,
            "seed_branch_count": SEED_BRANCH_COUNT,
        }
        mismatches = {
            key: self.creation_metadata.get(key)
            for key, value in expected.items()
            if self.creation_metadata.get(key) != value
        }
        initial_digest = self.creation_metadata.get("initial_checkpoint_digest")
        engine_type = type(self.engine)
        if (
            mismatches
            or not isinstance(initial_digest, str)
            or not initial_digest.startswith("sha256:")
            or engine_type.__module__ != "agency.mechanics.sicd_engine"
            or engine_type.__name__ != "TreeGrowthEngine"
        ):
            raise ValueError(
                "17D operation requires verified Python msr_8d_native_10k tree lineage"
            )

    def _load_creation_metadata(self) -> dict[str, Any]:
        if not self._creation_metadata_path.exists():
            return {
                "project_id": self.project_id,
                "runtime_version": self.runtime_sha,
                "seed_profile": "legacy_pre_wp14",
                "seed_artifact_sha256": None,
                "seed_tick": None,
                "initial_checkpoint_digest": None,
            }
        loaded = json.loads(self._creation_metadata_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("project creation metadata must be a JSON object")
        return loaded

    def _load_idempotency(self) -> dict[str, dict[str, Any]]:
        if not self._idempotency_path.exists():
            return {}
        loaded = json.loads(self._idempotency_path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}

    def _restore_current_artifacts_if_present(self) -> None:
        if not self._tree_path.exists() or not self._rgm_path.exists():
            return
        from agency.mechanics.sicd_engine import TreeGrowthEngine
        from gateway.front_row import FrontRowMemory as ReflectionGatedMemory

        self.engine = TreeGrowthEngine.load(str(self._tree_path), cfg=self._new_engine_config())
        self._restore_serialized_fields()
        self.rgm = ReflectionGatedMemory(self.library, self.settings["front_row_capacity"])
        self.rgm.restore(self._rgm_path.read_text(encoding="utf-8"))
        self._checkpoint_digest = self._compute_checkpoint_digest()

    def _restore_serialized_fields(self):
        # Product checkpoints are exact snapshots, not unsupervised growth seeds.
        # Upstream load :1641,1855-1865 normalizes axes/resets ages; undo only those
        # load-time adaptations for our already-serialized checkpoint fields.
        data = json.loads(self._tree_path.read_bytes())
        for saved in data["branches"]:
            branch = self.engine.state.branches[str(saved["id"])]
            branch.axis_w = list(saved["axis_w"])
            branch.sem_vec_age = saved.get("sem_vec_age", 0)
        self.engine.state.last_leaf_vec_update_tick = data.get("last_leaf_vec_update_tick")

    def _write_head_artifacts(self, head):
        _atomic_write(self._tree_path, head[0])
        _atomic_write(self._rgm_path, head[1])
        _atomic_write(self._idempotency_path, head[2].encode("utf-8"))

    def update_settings(self, values):
        with self.lock:
            settings = {**self.settings, **values}
            if set(settings) != set(DEFAULT_SETTINGS):
                raise ValueError("unknown project memory setting")
            capacity = settings["front_row_capacity"]
            if type(capacity) is not int or not 1 <= capacity <= 1_000_000:
                raise ValueError("front_row_capacity must be an integer in 1..1000000")
            if type(settings["teach_on_conflict"]) is not bool:
                raise ValueError("teach_on_conflict must be boolean")
            tree, rgm = self.serialized_state_bytes()
            self.library.set_head(tree, rgm, self._idempotency, settings)
            self.settings = settings
            self.rgm.capacity = capacity  # Demotions wait for the next commit.
            return dict(settings)

    def memory_diagnostics(self, after=0):
        with self.lock:
            events = self.library.events(after)
            active_documents = self.library.documents(include_withdrawn=False)
            all_documents = self.library.documents(include_withdrawn=True)
            return {**self.settings, "front_row_count": len(self.rgm.state.anchors),
                    "engine_tick": self.engine.state.tick, "rgm_current_tick": self.rgm.state.current_tick,
                    "checkpoint_digest": self._current_checkpoint_digest(), "commit_count": len(self._idempotency),
                    "library_count": self.library.db.execute("SELECT COUNT(*) FROM library_records").fetchone()[0],
                    "document_count": len(active_documents),
                    "document_count_all": len(all_documents),
                    "document_bytes": sum(row["byte_length"] for row in active_documents),
                    "document_chunk_count": self.library.db.execute(
                        "SELECT COUNT(*) FROM document_chunks c JOIN documents d "
                        "ON d.document_id=c.document_id WHERE d.tombstoned_at IS NULL"
                    ).fetchone()[0],
                    "document_tree_tick": int(self.document_index.engine.state.tick),
                    "document_tree_branch_count": len(self.document_index.engine.state.branches),
                    "document_tree_commit_count": self.document_index.project_commit_count(
                        self.project_id
                    ),
                    "document_tree_isolation": "dedicated_project_tree",
                    "document_tree_seed_artifact_sha256": self.seed.artifact_sha256,
                    "document_tree_path": "document-index/tree_state.json",
                    "demotion_count": self.library.db.execute("SELECT COUNT(*) FROM demotions").fetchone()[0],
                    "demotions": events, "next_event_id": events[-1]["event_id"] if events else after}

    def ingest_document(self, display_name, content, media_type):
        """Store explicitly supplied text inventory without touching runtime state."""
        from gateway.document_ingestion import (
            DOCUMENT_CHUNKING_VERSION,
            DOCUMENT_EMBEDDING_VERSION,
            DocumentEmbeddingWorkerClient,
            validate_document_input,
            validate_embedding_result,
        )

        display_name, content, media_type, byte_length = validate_document_input(
            display_name, content, media_type
        )
        digest = content_hash(content)
        document_id = "document-" + digest[:32]
        with self.lock:
            existing = self.library.document(document_id)
            if existing is not None:
                if existing["content_sha256"] != digest or existing["content"] != content:
                    raise ValueError("document content identity conflict")
                if existing["declared_structure"] is None:
                    declared_structure = build_declared_structure(content)
                    self.library.db.execute("BEGIN IMMEDIATE")
                    try:
                        self.library.retain_document_declared_structure(
                            document_id, declared_structure,
                        )
                        self.library.db.execute("COMMIT")
                    except BaseException:
                        if self.library.db.in_transaction:
                            self.library.db.execute("ROLLBACK")
                        raise
                    existing = self.library.document(document_id)
                self._backfill_document_index()
                existing = self.library.document(document_id)
                return self._public_document(existing, duplicate=True)
            declared_structure = build_declared_structure(content)
            provider = self.document_embedding_provider
            if provider is None:
                provider = DocumentEmbeddingWorkerClient.from_environment()
                self.document_embedding_provider = provider
            embedded = validate_embedding_result(content, provider.embed_document(content))
            chunks = []
            for row in embedded["chunks"]:
                chunk_text = content[row["start"]:row["end"]]
                chunks.append({
                    "index": row["index"],
                    "start": row["start"],
                    "end": row["end"],
                    "text_sha256": content_hash(chunk_text),
                    "passage_vector": row["vector_f32_le_base64"],
                })
            document = {
                "document_id": document_id,
                "display_name": display_name,
                "content_sha256": digest,
                "content": content,
                "byte_length": byte_length,
                "media_type": media_type,
                "chunking_version": DOCUMENT_CHUNKING_VERSION,
                "embedding_version": DOCUMENT_EMBEDDING_VERSION,
                "ingested_tick": int(self.engine.state.tick),
                "tombstoned_at": None,
            }
            self.library.db.execute("BEGIN IMMEDIATE")
            try:
                retained = self.library.retain_document(
                    document, chunks, declared_structure,
                )
                self.library.db.execute("COMMIT")
            except BaseException:
                if self.library.db.in_transaction:
                    self.library.db.execute("ROLLBACK")
                raise
            tree_chunks = [
                {
                    **row,
                    "text": content[row["start"]:row["end"]],
                }
                for row in chunks
            ]
            _, receipts, analyses = self.document_index.apply_document(
                self.project_id,
                document_id,
                tree_chunks,
                declared_structure,
                "activated",
                f"ingested_tick:{document['ingested_tick']}",
            )
            self.library.db.execute("BEGIN IMMEDIATE")
            try:
                self.document_index.set_project_chunk_analyses(
                    self.library, document_id, receipts, analyses,
                )
                self.library.db.execute("COMMIT")
            except BaseException:
                if self.library.db.in_transaction:
                    self.library.db.execute("ROLLBACK")
                raise
            retained = self.library.document(document_id)
            return self._public_document(retained, duplicate=False)

    @staticmethod
    def _public_document(document, *, duplicate=None):
        chunks = [
            {
                key: row[key]
                for key in ("chunk_index", "start", "end", "text_sha256")
            }
            for row in document.get("chunks", [])
        ]
        public = {
            key: document[key]
            for key in (
                "document_id", "display_name", "content_sha256", "content",
                "byte_length", "media_type", "chunking_version", "embedding_version",
                "ingested_tick", "tombstoned_at",
            )
        }
        public["chunks"] = chunks
        public["chunk_count"] = len(chunks)
        public["declared_structure"] = document.get("declared_structure")
        if duplicate is not None:
            public["duplicate"] = duplicate
        return public

    def list_documents(self, include_withdrawn=False):
        with self.lock:
            result = []
            for row in self.library.documents(include_withdrawn=bool(include_withdrawn)):
                count = self.library.db.execute(
                    "SELECT COUNT(*) FROM document_chunks WHERE document_id=?",
                    (row["document_id"],),
                ).fetchone()[0]
                result.append({**row, "chunk_count": count})
            return result

    def get_document(self, document_id):
        with self.lock:
            document = self.library.document(str(document_id))
            if document is None:
                raise ValueError("document does not exist")
            return self._public_document(document)

    def withdraw_document(self, document_id, tombstoned_at):
        if not isinstance(tombstoned_at, str) or not tombstoned_at.strip():
            raise ValueError("document withdrawal timestamp is required")
        with self.lock:
            self.library.db.execute("BEGIN IMMEDIATE")
            try:
                document = self.library.withdraw_document(
                    str(document_id), tombstoned_at.strip()
                )
                self.library.db.execute("COMMIT")
            except BaseException:
                if self.library.db.in_transaction:
                    self.library.db.execute("ROLLBACK")
                raise
            self.document_index.record_withdrawal(
                self.project_id, str(document_id), tombstoned_at.strip(),
            )
            return self._public_document(document)

    def _artifact_payload(self, tree_bytes: bytes, rgm_bytes: bytes) -> dict[str, Any]:
        return {
            "engine": json.loads(tree_bytes.decode("utf-8")),
            "rgm": json.loads(rgm_bytes.decode("utf-8")),
        }

    def _compute_checkpoint_digest(self) -> str:
        return canonical_digest(self._artifact_payload(self._tree_path.read_bytes(), self._rgm_path.read_bytes()))

    def _current_checkpoint_digest(self) -> str:
        return self._checkpoint_digest

    def _persist_current_artifacts(self) -> str:
        descriptor, temporary = tempfile.mkstemp(prefix=".tree.", suffix=".json", dir=str(self.state_dir))
        os.close(descriptor)
        temporary_path = Path(temporary)
        try:
            self.engine.save(str(temporary_path))
            tree_bytes = temporary_path.read_bytes()
        finally:
            temporary_path.unlink(missing_ok=True)
        rgm_bytes = self.rgm.serialize().encode("utf-8")
        _atomic_write(self._tree_path, tree_bytes)
        _atomic_write(self._rgm_path, rgm_bytes)
        self._checkpoint_digest = canonical_digest(self._artifact_payload(tree_bytes, rgm_bytes))
        return self._checkpoint_digest

    def serialized_state_bytes(self) -> tuple[bytes, bytes]:
        """Test-only diagnostic snapshot; this does not participate in preview."""
        with self.lock:
            descriptor, temporary = tempfile.mkstemp(prefix=".purity.", suffix=".json", dir=str(self.state_dir))
            os.close(descriptor)
            temporary_path = Path(temporary)
            try:
                self.engine.save(str(temporary_path))
                tree = temporary_path.read_bytes()
            finally:
                temporary_path.unlink(missing_ok=True)
            return tree, self.rgm.serialize().encode("utf-8")

    def _rank_document_packet(
        self, user_text: str, k: int, max_chars: int, *, query_profile=None,
        processing_cursor=None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        chunks = self.library.document_chunks(active_only=True)
        if not chunks:
            return [], {
                "version": "tom-assist-document-research-trace/1.0",
                "intent": parse_research_intent(user_text),
                "inventory": {
                    "active_document_count": 0,
                    "active_chunk_count": 0,
                    "documents": [],
                    "unresolved_external_reference_count": 0,
                },
                "final_evidence_coverage": {
                    "discovered_units": [],
                    "selected_evidence_ids": [],
                    "missing_sources": [],
                    "exhaustiveness": "no_active_project_documents",
                },
            }
        metadata = self.document_index.project_chunk_metadata(self.project_id)
        chunks = [
            {
                **row,
                **metadata.get((str(row["document_id"]), int(row["chunk_index"])), {}),
            }
            for row in chunks
        ]
        if query_profile is None:
            provider = self.document_embedding_provider
            if provider is None:
                provider = DocumentEmbeddingWorkerClient.from_environment()
                self.document_embedding_provider = provider
            query_profile = build_document_query_profile(user_text, provider)
        query_analysis, cohort, query_branch_trace = self.document_index.query_address(
            user_text, query_profile,
        )
        structural_scores, structural_telemetry = self.document_index.structural_scores(
            self.project_id, chunks, cohort,
        )
        document_sources = {}
        for document_id in sorted({str(row["document_id"]) for row in chunks}):
            source = self.library.document(document_id, include_chunks=False)
            if source is None or source.get("tombstoned_at") is not None:
                raise ValueError("active document chunk has no active permanent source")
            source["chunk_count"] = sum(
                row["document_id"] == document_id for row in chunks
            )
            document_sources[document_id] = source
        ranked, research_trace = rank_document_chunks_for_packet(
            user_text, query_profile, chunks, k=k, max_chars=max_chars,
            structural_scores=structural_scores,
            structural_telemetry=structural_telemetry,
            document_sources=document_sources,
            return_trace=True,
            processing_cursor=processing_cursor,
            cursor_auth_key=self.document_research_cursor_key,
        )
        for row in ranked:
            from gateway.document_tree import DOCUMENT_TREE_VERSION
            source = next(item for item in chunks if (
                item["document_id"] == row["document_id"]
                and item["chunk_index"] == row["chunk_index"]
            ))
            row["structural_signature"] = {
                "document_tree_version": DOCUMENT_TREE_VERSION,
                "query_analysis_digest": query_analysis["analysis_digest"],
                "chunk_analysis_digest": source["analysis_digest"],
                "matched_branch_id": row.get("matched_document_branch_id"),
                "tree_channel": structural_telemetry,
                "clause_identifiers": row.get("clause_identifiers", []),
                "matched_clause_identifier": row.get("matched_clause_identifier"),
            }
        research_trace["document_tree"].update({
            "head": self.document_index.head_metadata(),
            "query_analysis_digest": query_analysis["analysis_digest"],
            "query_source_text_sha256": query_analysis["source_text_sha256"],
            "query_branch_trace": query_branch_trace,
            "project_chunk_receipt_count": self.document_index.project_commit_count(
                self.project_id
            ),
        })
        return ranked, research_trace

    def preview_rank(
        self, user_text: str, k: int, max_chars: int,
        declared_glossary_titles=(), processing_cursor=None,
    ) -> dict[str, Any]:
        """Pure ranking over last-committed state plus the draft as user_text only."""
        with self.lock:
            # Binding source evidence: rgm.py:681-733 defines VectorStore.query
            # as deterministic encode/cosine/sort without state mutation. We
            # deliberately do not call retrieve_ltm_with_stm_triggers because
            # its pinned implementation contains plastic recall at lines 187-193.
            triggers = _compute_preview_triggers(len(self._idempotency))
            signature, projection, angle = project_text(user_text)
            cohort, branch_trace = select_cohort(self.engine.state.branches, signature)
            candidates = self.rgm.vector_store.query(user_text, k=max(1, len(self.rgm.state.anchors)))
            # The pinned vector store sorts only on similarity. Its in-memory
            # and restored insertion orders differ, so make equal-score ordering
            # explicit before applying both result and character limits.
            fused = fuse_anchors(self.rgm.state.anchors, candidates, cohort)
            ranked: list[dict[str, Any]] = []
            used_chars = 0
            for scores in fused:
                record_id = scores["id"]
                record = self.rgm.state.anchors.get(record_id)
                if record is None:
                    continue
                text = str(record.content_summary or record.content or "")
                if not text:
                    continue
                remaining = max_chars - used_chars
                if remaining <= 0:
                    break
                bounded = text[:remaining]
                used_chars += len(bounded)
                ranked.append(
                    {
                        "id": str(record_id),
                        "text": bounded,
                        **scores,
                        "dependency_relevance": 0.0,
                        "authority_strength": 1.0 if record.policy_outcome.value == "permit" else 0.0,
                    }
                )
                if len(ranked) >= k:
                    break
            ranked_documents, document_research_trace = self._rank_document_packet(
                user_text, k, max_chars, processing_cursor=processing_cursor,
            )
            checkpoint_digest = self._current_checkpoint_digest()
            activation_id = canonical_digest(
                {
                    "project_id": self.project_id,
                    "user_text": user_text,
                    "k": k,
                    "max_chars": max_chars,
                    "checkpoint_digest": checkpoint_digest,
                    "document_packet_candidates": [
                        [
                            row["id"], row["excerpt_sha256"],
                            row["semantic_score"],
                        ]
                        for row in ranked_documents
                    ],
                }
            )
            return {
                "activation_id": activation_id,
                "triggers": [asdict(trigger) for trigger in triggers],
                "ranked_anchors": ranked,
                "ranked_document_chunks": ranked_documents,
                "document_research_trace": document_research_trace,
                "activated_branch_ids": [bid for bid, _, _ in cohort],
                "candidate_trace": fused,
                "branch_trace": branch_trace,
                "load_signature": signature.as_dict(),
                "policy_version": POLICY_VERSION,
                "checkpoint_digest": checkpoint_digest,
            }

    def commit_turn(self, role: str, text: str, idempotency_key: str, *,
                    response_text=None, activated_branch_ids=(), admitted_anchor_ids=(),
                    conflict_dismissed=False, packet_digest=None,
                    retrieval_trace=()) -> dict[str, Any]:
        """Atomic quintuple. SQLite head is authoritative; JSON files are projections."""
        from gateway.front_row import FrontRowMemory
        from memory.rgm import MemoryRecord, PolicyOutcome

        with self.lock:
            if idempotency_key in self._idempotency:
                return self._idempotency[idempotency_key]
            if not text or type(conflict_dismissed) is not bool:
                raise ValueError("nonempty committed text and boolean conflict_dismissed required")
            branch_ids = sorted(set(str(bid) for bid in activated_branch_ids))
            packet_anchor_ids = [str(rid) for rid in admitted_anchor_ids]
            if len(packet_anchor_ids) != len(set(packet_anchor_ids)):
                raise ValueError("admitted anchor ids must be unique and ordered")
            anchor_ids = sorted(set(packet_anchor_ids))
            for bid in branch_ids:
                if bid not in self.engine.state.branches:
                    raise ValueError(f"sent packet branch no longer exists: {bid}")
            for rid in anchor_ids:
                if self.library.get(rid) is None:
                    raise ValueError(f"sent packet anchor has no durable twin: {rid}")
            if response_text is None and role == "assistant":
                response_text = text
            stored_text = text if response_text is None or role == "assistant" else (
                "USER\n" + text + "\nASSISTANT\n" + response_text)
            before_tick = int(self.engine.state.tick)
            anchor_id = "turn-" + hashlib.sha256(
                f"{self.project_id}\0{idempotency_key}".encode("utf-8")).hexdigest()[:32]
            anchor_id = self.library.first_id_for_hash(content_hash(stored_text)) or anchor_id
            record = MemoryRecord(
                id=anchor_id, content=stored_text, content_summary=stored_text,
                content_hash=content_hash(stored_text), anchor_type="conversation_turn",
                anchor_strength=1.0, decay_rate=0.002, novelty_score=1.0,
                S=1.0, C=1.0, H=0.0, sensitivity="low", policy_outcome=PolicyOutcome.PERMIT,
                policy_version="tom-assist-commit/1.1", model="direct-engine",
                source="tom_assist_committed_exchange", semantic_tags=[role, f"project:{self.project_id}"],
                created_tick=before_tick + 1)
            record.leaf_vec = list(project_text(stored_text)[1].vector_8d)
            # This autocommit precedes the dynamics transaction: a crash may leave
            # an unused library item, but can never leave an unbacked front-row item.
            self.library.retain(record, self.rgm._record_to_dict(record))
            prior_engine, prior_rgm = self.engine, self.rgm
            prior_idempotency = dict(self._idempotency)
            prior_digest = self._current_checkpoint_digest()
            self.library.db.execute("BEGIN IMMEDIATE")
            try:
                head = self.library.head()
                durable_idempotency = json.loads(head[2])
                if idempotency_key in durable_idempotency:
                    self.library.db.execute("ROLLBACK")
                    self._idempotency = durable_idempotency
                    self._write_head_artifacts(head)
                    self.settings = json.loads(head[3])
                    self._restore_current_artifacts_if_present()
                    return durable_idempotency[idempotency_key]
                if canonical_digest(self._artifact_payload(head[0], head[1])) != prior_digest:
                    raise ValueError("runtime advanced in another process; reopen before committing")
                # Work on isolated copies. Any phase failure rolls back all five.
                self.engine = copy.deepcopy(prior_engine)
                self.rgm = FrontRowMemory(self.library, self.settings["front_row_capacity"])
                self.rgm.restore(prior_rgm.serialize())
                self.rgm.state = copy.deepcopy(prior_rgm.state)
                # Owner-ratified canonical path at pinned e9fdef81c:
                # sicd_msr_load_application.py:164-215. The product supplies the
                # real 17-channel text signature and the upstream application
                # owns every step parameter, including semantic_routing_basis.
                from agency.mechanics.sicd_msr_load_application import (
                    apply_msr_load_to_sicd_engine,
                )
                load_signature = project_text(text)[0]
                application = apply_msr_load_to_sicd_engine(
                    self.engine,
                    load_signature,
                    source="tom_assist_committed_exchange",
                )
                if not application.applied:
                    raise ValueError(f"canonical commit drive refused load: {application.reason}")
                stored_id = self.rgm.write(record)
                if stored_id == "deferred":
                    raise ValueError("committed exchange RGM admission refused")

                taught = False
                teach_reason = "no_provider_response"
                if response_text is not None:
                    teach_reason = "conflict_dismissed_policy" if (
                        conflict_dismissed and not self.settings["teach_on_conflict"]) else "confidence_gate"
                    if teach_reason != "conflict_dismissed_policy":
                        # sicd_engine.py:4869-4935 / controller.py:6381 at e9fdef81c.
                        # Reuse only the existing pure projection, not a new translator.
                        projection = project_text(response_text)[1]
                        raw_response = projection.raw_8d
                        llm_output = {"semantic_axis": list(raw_response[:3]),
                                      "loads": dict(zip(("delta_x", "delta_F", "phi", "intensity"), raw_response[3:7])),
                                      "confidence": raw_response[7]}
                        if not self.engine.cfg.kappa_update.enable_leaf_vec:
                            raise ValueError("commit teaching requires enabled leaf vectors")
                        self.engine.apply_leaf_vec_update(llm_output)
                        taught = self.engine.state.last_leaf_vec_update_tick == self.engine.state.tick
                        if raw_response[7] >= self.engine.cfg.kappa_update.leaf_vec_confidence_gate and not taught:
                            raise ValueError("confident leaf-vector teaching did not complete")
                        if taught:
                            teach_reason = "committed_response"

                for bid in branch_ids:
                    if bid not in self.engine.state.branches:
                        raise ValueError(f"physics removed a serving branch; prepare again: {bid}")
                    self.engine.state.branches[bid].usage_count += 1
                readmitted_ids = self.rgm.reseat(anchor_ids, idempotency_key)
                tree_bytes, rgm_bytes = self.serialized_state_bytes()
                checkpoint_digest = canonical_digest(self._artifact_payload(tree_bytes, rgm_bytes))
                result = {
                    "idempotency_key": idempotency_key, "role": role, "text_hash": canonical_digest(text),
                    "engine_tick_before": before_tick, "engine_tick_after": int(self.engine.state.tick),
                    "rgm_current_tick": int(self.rgm.state.current_tick),
                    "branch_count": len(self.engine.state.branches), "anchor_id": stored_id,
                    "K_total": float(application.kappa_total_after or 0.0), "runtime_error_code": None,
                    "seed_profile": self.creation_metadata.get("seed_profile"),
                    "seed_checkpoint_digest": self.creation_metadata.get("initial_checkpoint_digest"),
                    "prior_checkpoint_digest": prior_digest, "checkpoint_digest": checkpoint_digest,
                    "commit_dynamics": list(COMMIT_DYNAMICS), "taught": taught, "teach_reason": teach_reason,
                    "commit_drive": application.as_dict(),
                    "activated_branch_ids": branch_ids, "admitted_anchor_ids": anchor_ids,
                    "readmitted_anchor_ids": readmitted_ids, "packet_digest": packet_digest,
                }
                self._idempotency[idempotency_key] = result
                self.library.retain_retrieval_outcomes(
                    idempotency_key, packet_anchor_ids, retrieval_trace, stored_text,
                    conflict_dismissed, int(self.engine.state.tick),
                )
                self.library.set_head(tree_bytes, rgm_bytes, self._idempotency, self.settings)
                self.library.db.execute("COMMIT")
            except BaseException:
                if self.library.db.in_transaction:
                    self.library.db.execute("ROLLBACK")
                self.engine, self.rgm = prior_engine, prior_rgm
                self._idempotency = prior_idempotency
                self._checkpoint_digest = prior_digest
                raise
            self._checkpoint_digest = checkpoint_digest
            try:
                self._write_head_artifacts(self.library.head())
            except OSError:
                # Commit is durable. Startup/retry recovers from the SQLite head.
                LOGGER.exception("committed runtime head is durable; JSON projection needs recovery")
            return result

    def save_checkpoint(self) -> dict[str, Any]:
        with self.lock:
            digest = self._persist_current_artifacts()
            checkpoint_id = str(uuid.uuid4())
            destination = self.state_dir / "checkpoints" / checkpoint_id
            destination.mkdir(parents=True, exist_ok=False)
            os.chmod(destination, 0o700)
            shutil.copy2(self._tree_path, destination / "tree_state.json")
            shutil.copy2(self._rgm_path, destination / "rgm_state.json")
            commit_state = {"idempotency": self._idempotency, "settings": self.settings}
            _atomic_write(destination / "commit_state.json", canonical_json(commit_state))
            self.library.set_head(self._tree_path.read_bytes(), self._rgm_path.read_bytes(),
                                  self._idempotency, self.settings)
            metadata = {
                "commit_state_digest": canonical_digest(commit_state),
                "checkpoint_id": checkpoint_id,
                "digest": digest,
                "runtime_version": self.runtime_sha,
                "seed_profile": self.creation_metadata.get("seed_profile"),
                "seed_artifact_sha256": self.creation_metadata.get("seed_artifact_sha256"),
                "initial_checkpoint_digest": self.creation_metadata.get("initial_checkpoint_digest"),
            }
            _atomic_write(destination / "metadata.json", canonical_json(metadata))
            return metadata

    def restore_checkpoint(self, checkpoint_id: str) -> dict[str, Any]:
        with self.lock:
            if not re.fullmatch(r"[0-9a-f-]{36}", checkpoint_id):
                raise ValueError("invalid checkpoint_id")
            source = self.state_dir / "checkpoints" / checkpoint_id
            metadata = json.loads((source / "metadata.json").read_text(encoding="utf-8"))
            payload = self._artifact_payload((source / "tree_state.json").read_bytes(), (source / "rgm_state.json").read_bytes())
            if canonical_digest(payload) != metadata.get("digest"):
                raise ValueError("checkpoint digest mismatch")
            commit_state = json.loads((source / "commit_state.json").read_bytes())
            if canonical_digest(commit_state) != metadata.get("commit_state_digest"):
                raise ValueError("checkpoint commit-state digest mismatch")
            for encoded in payload["rgm"]["anchors"].values():
                self.library.assert_twin(self.rgm._dict_to_record(encoded))
            self.library.set_head((source / "tree_state.json").read_bytes(), (source / "rgm_state.json").read_bytes(),
                                  commit_state["idempotency"], commit_state["settings"])
            self.settings = commit_state["settings"]
            self._idempotency = commit_state["idempotency"]
            self._write_head_artifacts(self.library.head())
            self._restore_current_artifacts_if_present()
            return {"checkpoint_id": checkpoint_id, "digest": metadata["digest"], "restored": True}


class GemmaInspection:
    """Explicit, detached inspection. Never obtains or creates a live runtime.

    Kept in the existing gateway boundary to avoid unnecessary system files.
    Workers have separate interpreters, read-only imports, no provider and no writer.
    """
    ROOT = Path(__file__).resolve().parents[1]
    STREAM = ROOT.parent / "tom_matrix_native_stream1"
    STREAM_SHA = "906d7705e60af668c2a2ba3408d21935ff25c637a69621ef5484012eab70379c"
    CHECKPOINT_SHA = "801c7720e5e1284446b17a8b5273d15872b844f39551c05c853bf479615ad964"
    FINGERPRINT = "897982fd8e6584471bb859ec852c25aa3003b4cd40340fb9a8e18620d38f8470"
    MODEL = Path.home() / ".cache/huggingface/hub/models--mlx-community--gemma-4-26b-a4b-it-4bit/snapshots/0d77464eeb233a2da68ebf9d7dc4edaac7db956d"
    ADAPTER = ROOT / ".tmp/event-graph-lora-v14-session-001/epoch-1/adapter"
    ADAPTER_SHA = "c6a4708d9ceca6dab5d275ea0bff5ac172e392d085a4fda6b0d875e51d95a994"
    ADAPTER_CONFIG_SHA = "77d4e446d2d3fee1469a8cf5641e0d525a0dca1d4b4086b95d36a0c53ba4b0b5"
    MODEL_HASHES = {
        "model-00001-of-00003.safetensors": "683f420ee09550b8027bf0335c4202e196b37eb520b60a4bcbe8690b9e388c07",
        "model-00002-of-00003.safetensors": "feab2873c2976fb7ed666f8462549564a29409364388e0c8f6b015729d165e15",
        "model-00003-of-00003.safetensors": "bc607486deb1de5bc7e459932fda5c776a4f816b368feaa661bab8cfbb47e567",
        "chat_template.jinja": "36e3a42e5cf14cd0020e72d92e1fdd9970f59b82170e421f0cbe1bb42bead3f0",
        "config.json": "419e13a27ec359654c1ce7dd06d1a87149fd07d0c8af9f770494185e62e1b2ba",
        "generation_config.json": "d4226bbe3117d2d253ba4609720ba82c6c4ce4627a9a6ae05387c78983ac03de",
        "model.safetensors.index.json": "bf198c9f5ea6462addca1966e5dd669c407537a876e82cf06db9084c5c850b13",
        "processor_config.json": "de3e580aebdc98272d4c4547daffe6525fcbae18a83a0e0bcf0d7444d4ee6f37",
        "tokenizer.json": "cc8d3a0ce36466ccc1278bf987df5f71db1719b9ca6b4118264f45cb627bfe0f",
        "tokenizer_config.json": "080d9e1aff284e2f6043889cd05367966f7c7b80e025fbc0b06745e218158656",
    }
    SAVED_SOURCE = "Site briefing: Canal Reach D006 excavation must stop when Canal Reach D006 vibration is greater than 1.7 mm/s. Canal Reach D006 superintendent must be notified under the same condition."
    SAVED_RAW = '{"version":"tom-assist-span-wire/1","predicates":[{"id":"p1","subject":{"token_start":10,"token_end":14},"value":"1.7","unit":"mm/s","comparator":"GT","negated":false,"evidence":[{"token_start":3,"token_end":36}]}],"conditions":[],"events":[{"id":"e1","action":"stop","roles":{"actor":null,"object":{"token_start":3,"token_end":7},"source":null,"target":null,"recipient":null,"authority":null},"modality":"obligation","negated":false,"condition":"p1","exception":null,"complement":null,"revision":null,"time":null,"evidence":[{"token_start":3,"token_end":24}]},{"id":"e2","action":"notify","roles":{"actor":null,"object":null,"source":null,"target":null,"recipient":{"token_start":24,"token_end":28},"authority":null},"modality":"obligation","negated":false,"condition":"p1","exception":null,"complement":null,"revision":null,"time":null,"evidence":[{"token_start":24,"token_end":36}]}],"links":[],"unresolved":[]}'
    LOCK = threading.Lock()

    @staticmethod
    def file_hash(path):
        value = hashlib.sha256()
        with Path(path).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                value.update(chunk)
        return value.hexdigest()

    @staticmethod
    def collect_extraction(stream, eos_token_ids):
        # GenerationResponse also owns a vocabulary-sized GPU probability array.
        # Retain only text and scalar evidence, never one such array per token.
        parts, last, count = [], None, 0
        for chunk in stream:
            parts.append(chunk.text)
            count += 1
            last = {"token": int(chunk.token), "finish_reason": chunk.finish_reason,
                    "prompt_tokens": int(chunk.prompt_tokens),
                    "generation_tokens": int(chunk.generation_tokens),
                    "engine_peak_bytes": round(chunk.peak_memory * 1e9)}
        if last is None or last["finish_reason"] != "stop" or last["token"] not in eos_token_ids:
            raise ValueError("extraction did not reach a complete end-of-turn")
        return {"raw": "".join(parts), "tokens": count, **last}

    @classmethod
    def package_hash(cls):
        package = cls.STREAM / "src/tom_matrix"
        files = {str(p.relative_to(package)): cls.file_hash(p) for p in sorted(package.rglob("*"))
                 if p.is_file() and "__pycache__" not in p.parts and p.suffix in (".py", ".json", ".yaml", ".yml", ".toml")}
        return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @classmethod
    def live_snapshot(cls, gateway, project):
        # Reading files does not initialise the project's document or experience Trees.
        directory = gateway.data_dir / "projects" / project
        hashes = {str(p.relative_to(directory)): cls.file_hash(p) for p in sorted(directory.rglob("*"))
                  if p.is_file() and not p.name.endswith("-shm")}
        runtime = gateway._projects.get(project)
        memory = None
        if runtime is not None:
            memory = [hashlib.sha256(part).hexdigest() for part in runtime.serialized_state_bytes()]
        return {"files_sha256": hashlib.sha256(canonical_json(hashes)).hexdigest(),
                "file_count": len(hashes), "in_memory_sha256": memory,
                "scope": "active-project runtime files, including document and experience storage; SQLite shared-memory coordination excluded"}

    @staticmethod
    def resources(*, before_load=True, exclude=()):
        """Fail closed on competing model/large Python jobs; no process is modified."""
        import time
        raw = subprocess.check_output(["ps", "-axo", "pid=,ppid=,rss=,comm="], text=True, timeout=10)
        processes = [line.strip().split(None, 3) for line in raw.splitlines()]
        own = {os.getpid(), *exclude}
        while True:
            expanded = own | {int(p[0]) for p in processes if len(p) == 4 and int(p[1]) in own}
            if expanded == own:
                break
            own = expanded
        reasons = []
        for p in processes:
            if len(p) != 4 or int(p[0]) in own:
                continue
            name = Path(p[3]).name.lower()
            if name.startswith("python") or any(x in name for x in ("ollama", "llama-server", "mlx")):
                probe = subprocess.run(["lsof", "-a", "-p", p[0], "-d", "txt", "-Fn"], capture_output=True, text=True, timeout=10)
                if probe.returncode not in (0, 1):
                    raise ValueError("cannot inspect competing process libraries")
                if probe.returncode == 1 and not probe.stdout:
                    alive = subprocess.run(["ps", "-p", p[0], "-o", "pid="], capture_output=True, text=True)
                    if alive.stdout.strip():
                        reasons.append(f"process {p[0]} could not be inspected")
                if "libmlx" in probe.stdout.lower() or any(x in name for x in ("ollama", "llama-server", "mlx")) or int(p[2]) * 1024 >= 2 * 1024**3:
                    reasons.append(f"competing model or large Python process {p[0]}")
        vm = subprocess.check_output(["vm_stat"], text=True, timeout=10)
        page = re.search(r"page size of (\d+) bytes", vm)
        counts = [re.search(r"^" + key + r":\s+(\d+)", vm, re.M) for key in ("Pages free", "Pages inactive", "Pages speculative")]
        if page is None or any(c is None for c in counts):
            raise ValueError("memory headroom could not be measured")
        available = int(page[1]) * sum(int(c[1]) for c in counts)
        # Inference only, one worker at a time. Verified text tensors: 14.200 GB;
        # V14: 0.012 GB. At 8192 tokens, float32 KV storage is at most 0.704 GiB
        # (25 sliding 1024-token layers + 5 full layers). Add 4 GiB for temporary
        # allocations/cache and 4 GiB system reserve, then round up to 22 GiB.
        # This is an initial budget estimate, not a measured minimum or hard cap.
        required = (22 if before_load else 2) * 1024**3
        if available < required:
            reasons.append("insufficient estimated memory headroom")
        return {"time": time.time(), "estimated_available_bytes": available, "required_bytes": required,
                "budget_basis": "pinned text weights + V14 + bounded attention cache + temporary allocation allowance + system reserve; inference only, no training or simultaneous Stream 1 worker",
                "blockers": reasons, "limitation": "free + inactive + speculative pages are an estimate; this is not a system-wide lock"}

    @classmethod
    def launch_worker(cls, operation, payload):
        import time
        executable = (cls.ROOT.parent / "tom_sicd_gemma/.venv/bin/python" if operation == "gemma"
                      else cls.ROOT / ".venv-gateway/bin/python")
        code = f"import sys;sys.path.insert(0,{str(cls.ROOT)!r});from gateway.tom_gateway import GemmaInspection;GemmaInspection.worker({operation!r})"
        env = {k: v for k, v in os.environ.items() if k in ("HOME", "PATH", "TMPDIR", "LANG")}
        env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false",
                   PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
        child = subprocess.Popen([str(executable), "-I", "-B", "-c", code], cwd=cls.ROOT, env=env,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.monotonic() + 150
        request = json.dumps(payload)
        try:
            while True:
                try:
                    out, err = child.communicate(input=request, timeout=3)
                    break
                except subprocess.TimeoutExpired:
                    request = None
                    if time.monotonic() >= deadline:
                        raise ValueError("inspection worker timed out; no retry was started")
                    if operation == "gemma" and cls.resources(before_load=False, exclude=(child.pid,))["blockers"]:
                        raise ValueError("Gemma stopped because a resource conflict appeared")
            if child.returncode:
                raise ValueError(f"{operation} worker failed: {err[-700:]}")
            if len(out) > 2 * 1024 * 1024:
                raise ValueError("inspection output exceeded its bound")
            return json.loads(out)
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate()

    @classmethod
    def worker(cls, operation):
        import contextlib
        import time
        payload = json.load(sys.stdin)
        # Package imports cannot write caches, change either owner checkout or use a network.
        def readonly(event, args):
            if event == "open":
                _, mode, flags = args
                if (isinstance(mode, str) and any(c in mode for c in "wax+")) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
                    raise PermissionError("inspection worker is read-only")
            if event in ("os.mkdir", "os.remove", "os.rename", "os.rmdir", "os.symlink", "os.chmod", "socket.connect", "subprocess.Popen"):
                raise PermissionError("inspection worker refuses " + event)
        sys.addaudithook(readonly)
        started = time.monotonic()
        with contextlib.redirect_stdout(sys.stderr):
            if operation == "gemma":
                import importlib.metadata
                versions = {n: importlib.metadata.version(n) for n in ("mlx", "mlx-lm", "transformers")}
                if versions != {"mlx": "0.31.1", "mlx-lm": "0.31.2", "transformers": "5.5.3"}:
                    raise ValueError("Gemma runtime versions changed")
                for name, expected in cls.MODEL_HASHES.items():
                    if cls.file_hash(cls.MODEL / name) != expected:
                        raise ValueError("pinned model file changed: " + name)
                if cls.file_hash(cls.ADAPTER / "adapters.safetensors") != cls.ADAPTER_SHA or cls.file_hash(cls.ADAPTER / "adapter_config.json") != cls.ADAPTER_CONFIG_SHA:
                    raise ValueError("selected V14 adapter changed")
                from gateway.event_graph_span_extractor import prompt
                from mlx_lm import load, stream_generate
                from mlx_lm.sample_utils import make_sampler
                import mlx.core as mx
                mx.random.seed(7)
                mx.reset_peak_memory()
                model, tokenizer = load(str(cls.MODEL), adapter_path=str(cls.ADAPTER))
                memory = {"loaded_active_bytes": mx.get_active_memory(),
                          "load_peak_bytes": mx.get_peak_memory()}
                text = tokenizer.apply_chat_template([{"role": "user", "content": prompt(payload["text"])}],
                    tokenize=False, add_generation_prompt=True, enable_thinking=False)
                if len(tokenizer.encode(text, add_special_tokens=False)) > 4096:
                    raise ValueError("input exceeds the inspection token limit; select a shorter passage")
                result = cls.collect_extraction(
                    stream_generate(model, tokenizer, prompt=text, max_tokens=4096, sampler=make_sampler(temp=0.0)),
                    tokenizer.eos_token_ids)
                import resource
                memory.update(engine_peak_bytes=mx.get_peak_memory(), cache_bytes_at_completion=mx.get_cache_memory(),
                              process_peak_resident_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                              scope="MLX active allocation peak and macOS process peak resident bytes; not whole-system memory")
                result.update(versions=versions, model_files_sha256=cls.MODEL_HASHES,
                              local_generations=1, memory=memory)
            elif operation == "stream1":
                import pickle
                import numpy as np
                if cls.package_hash() != cls.STREAM_SHA:
                    raise ValueError("Stream 1 source identity changed; contract review required")
                package = cls.STREAM / "src/tom_matrix"
                if any(n == "tom_matrix" or n.startswith("tom_matrix.") for n in sys.modules):
                    raise ValueError("a tom_matrix package was already imported")
                sys.path.insert(0, str(cls.STREAM / "src"))
                from tom_matrix.core.migration import load_legacy
                from tom_matrix.relations.matched_recall import Recall
                from gateway.typed_event_graph import digest
                checkpoint = cls.STREAM / "data/checkpoints/paired16_initial.pkl"
                tree = load_legacy(checkpoint, expected_sha256=cls.CHECKPOINT_SHA)
                if tree.fingerprint() != cls.FINGERPRINT or type(tree).query is not Recall.query:
                    raise ValueError("Stream 1 checkpoint or query implementation mismatch")
                imported = {name: str(Path(mod.__file__).resolve()) for name, mod in sys.modules.items()
                            if (name == "tom_matrix" or name.startswith("tom_matrix.")) and getattr(mod, "__file__", None)}
                if any(not Path(path).is_relative_to(package) for path in imported.values()):
                    raise ValueError("wrong tom_matrix implementation loaded")
                if not 0 < len(payload["loads"]) <= 32:
                    raise ValueError("inspection requires 1–32 ordered loads")
                frame = tree.readings["frames"][tree.readings["root"]]
                before = hashlib.sha256(pickle.dumps(tree, protocol=5)).hexdigest()
                answers = []
                for index, load in enumerate(payload["loads"]):
                    x = np.asarray(load["matrix"], dtype=np.float64)
                    if x.shape != (32, 32) or not np.isfinite(x).all() or abs(float(np.linalg.norm(x)) - 1) > 1e-12:
                        raise ValueError("expected the unchanged signed, unit-Frobenius 32×32 compiler load")
                    if digest(x.ravel().tolist()) != load["matrix_sha256"]:
                        raise ValueError("load identity mismatch")
                    if not np.allclose(frame.to_global(frame.to_local(x)), x, rtol=0, atol=1e-12):
                        raise ValueError("global/local frame round-trip failed")
                    y, trace = tree.query(x, details=True)
                    after = hashlib.sha256(pickle.dumps(tree, protocol=5)).hexdigest()
                    if before != after or y.shape != (32, 32) or not np.isfinite(y).all():
                        raise ValueError("query changed state or returned an invalid matrix")
                    answers.append({"load_id": load["id"], "sequence_index": index,
                                    "input_sha256": load["matrix_sha256"], "matrix": y.tolist(),
                                    "response_sha256": digest(y.ravel().tolist()), "trace": trace})
                if cls.package_hash() != cls.STREAM_SHA or cls.file_hash(checkpoint) != cls.CHECKPOINT_SHA:
                    raise ValueError("runtime or checkpoint changed during inspection")
                result = {"responses": answers, "state_before": before, "state_after": after,
                          "state_unchanged": True, "checkpoint_sha256": cls.CHECKPOINT_SHA,
                          "package_sha256": cls.STREAM_SHA, "package_path": str(package),
                          "python_executable": sys.executable, "python_version": sys.version,
                          "numpy_version": np.__version__,
                          "query_implementation": "tom_matrix.relations.matched_recall.Recall.query",
                          "frame": "global input/output; local = source.T @ global @ target",
                          "normalization": "compiler unit Frobenius; passed unchanged; native routing retains amplitude",
                          "operation": "independent query for each ordered event/link load; no aggregation or feedback",
                          "interpretation": "unavailable: this checkpoint's learning has not been verified for the compiler encoding",
                          "occupied_banks": int(tree.occupied.sum()), "observations": tree.observations}
            else:
                raise ValueError("unsupported worker operation")
        result["elapsed_ms"] = round((time.monotonic() - started) * 1000, 2)
        print(json.dumps(result, allow_nan=False, default=lambda value: value.tolist()), flush=True)

    @classmethod
    def inspect(cls, gateway, payload):
        import time
        from gateway.event_graph_span_extractor import parse_output
        from gateway.event_graph_span_wire import bind
        from gateway.event_graph_compiler import compile_graph, VERSION as compiler_version
        if payload.get("opt_in") is not True or payload.get("explicit_inspect") is not True:
            raise ValueError("explicit experimental inspection required")
        project = _safe_project_id(payload.get("project_id"))
        result = {"version": "tom-assist-gemma-inspection/1", "project_id": project,
                  "stages": [], "purity": {}, "semantic_review": "required",
                  "quality_limits": "Saved wiring evidence is not held-out success. V12/V15 held-out failures remain exposed. V22 rejected; V23 evaluation incomplete; V14 retained.",
                  "identities": {"model": str(cls.MODEL), "adapter_id": "v14-4380", "adapter_sha256": cls.ADAPTER_SHA,
                                 "compiler": compiler_version, "compiler_sha256": cls.file_hash(cls.ROOT / "gateway/event_graph_compiler.py"),
                                 "parser_sha256": cls.file_hash(cls.ROOT / "gateway/event_graph_span_extractor.py"),
                                 "stream1_package_sha256": cls.STREAM_SHA, "stream1_checkpoint_sha256": cls.CHECKPOINT_SHA}}
        if not cls.LOCK.acquire(blocking=False):
            raise ValueError("another inspection is already running")
        stage = "input"
        started = phase = time.monotonic()
        before = None
        def passed(name, reason):
            nonlocal phase
            result["stages"].append({"stage": name, "status": "passed", "reason": reason,
                                     "elapsed_ms": round((time.monotonic()-phase)*1000, 2)})
            phase = time.monotonic()
        try:
            before = cls.live_snapshot(gateway, project)
            source = dict(payload.get("source") or {})
            mode = payload.get("extraction_mode")
            if payload.get("adapter_id") != "v14-4380":
                raise ValueError("explicitly select the retained V14 adapter")
            if mode == "saved":
                if source.get("kind") != "saved_example":
                    raise ValueError("saved extraction belongs only to its saved source")
                source = {"kind": "saved_example", "id": "v8-dev-6-0", "text": cls.SAVED_SOURCE,
                          "version": hashlib.sha256(cls.SAVED_SOURCE.encode()).hexdigest(), "start": 0, "end": len(cls.SAVED_SOURCE)}
            elif mode != "gemma" or source.get("kind") not in ("draft", "state_object"):
                raise ValueError("choose a saved example, draft or active-project passage")
            full = source.get("text")
            start, end = source.get("start"), source.get("end")
            if not isinstance(full, str) or not 0 < len(full) <= 16000 or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(full) or end-start > 4000:
                raise ValueError("select 1–4000 characters from the bounded original source")
            text = full[start:end]
            result["source"] = {**source, "full_text": full, "text": text, "offset_unit": "Unicode code points",
                                "sha256": hashlib.sha256(text.encode()).hexdigest(), "project_state_version": payload.get("project_state_version")}
            passed(stage, "Exact selected source retained; interpretation remains a proposal")
            stage = "extraction"
            if mode == "saved":
                extraction = {"raw": cls.SAVED_RAW, "local_generations": 0, "origin": "saved V14 output, v8-dev-6-0; exposed development example"}
            else:
                resources = cls.resources()
                result["resources"] = resources
                if resources["blockers"]:
                    raise ValueError("Local Gemma did not start: " + "; ".join(resources["blockers"]))
                extraction = cls.launch_worker("gemma", {"text": text})
            result["extraction"] = extraction
            extraction["raw_sha256"] = hashlib.sha256(extraction["raw"].encode()).hexdigest()
            passed(stage, "Saved extraction replayed" if mode == "saved" else "Pinned local Gemma extraction completed")
            stage = "validation"
            # Use the same parser as evaluation, disclosing its exact normalization.
            stripped = extraction["raw"].strip()
            fenced = re.fullmatch(r"```(?:json)?[ \t]*\r?\n(.*)\r?\n```", stripped, re.DOTALL)
            def unique_fields(pairs):
                value = {}
                for key, item in pairs:
                    if key in value:
                        raise ValueError("duplicate extraction field: " + key)
                    value[key] = item
                return value
            original = bind(json.loads(fenced.group(1) if fenced else stripped, object_pairs_hook=unique_fields), text)
            graph = parse_output(extraction["raw"], text)
            result.update(graph=graph, original_bound_graph=original,
                          normalization={"changed": original != graph,
                            "policy": "existing parser: inverse negated comparators and Boolean alias canonicalization; original and normalized graphs both shown"})
            if graph["unresolved"]:
                raise ValueError("Unresolved extraction: " + "; ".join(r["reason"] for r in graph["unresolved"]))
            if not graph["events"]:
                raise ValueError("No supported requirement or relationship was extracted")
            passed(stage, "Structure and source spans valid; semantic review still required")
            stage = "compilation"
            compiled = compile_graph(graph, text)
            if len(compiled["loads"]) > 32:
                raise ValueError("more than 32 loads; select a smaller passage")
            result["compiled"] = compiled
            passed(stage, f"{len(compiled['loads'])} ordered signed 32×32 event/link loads; no pooling")
            stage = "runtime"
            if payload.get("query_stream1") is True:
                if payload.get("checkpoint_id") != "paired16-initial":
                    raise ValueError("explicitly select the trusted sixteen-branch experiment checkpoint")
                result["runtime"] = cls.launch_worker("stream1", {"loads": compiled["loads"]})
                passed(stage, "Isolated Stream 1 queries completed; interpretation unavailable")
            else:
                result["stages"].append({"stage": stage, "status": "not_requested", "reason": "Stream 1 query requires a separate explicit selection"})
        except Exception as error:
            result["stages"].append({"stage": stage, "status": "blocked", "reason": str(error), "elapsed_ms": round((time.monotonic()-phase)*1000, 2)})
        finally:
            if before is not None:
                try:
                    after = cls.live_snapshot(gateway, project)
                    result["purity"]["live_runtime"] = {"before": before, "after": after, "unchanged": before == after,
                        "note": "A concurrent live change makes this observation inconclusive; this path performs no live writes"}
                except Exception as error:
                    result["purity"]["live_runtime"] = {"unchanged": None, "reason": str(error)}
            result["elapsed_ms"] = round((time.monotonic()-started)*1000, 2)
            cls.LOCK.release()
        completed = {row["stage"] for row in result["stages"]}
        for name in ("input", "extraction", "validation", "compilation", "runtime"):
            if name not in completed:
                result["stages"].append({"stage": name, "status": "not_run", "reason": "An earlier stage stopped"})
        return result


class TomGateway:
    def __init__(
        self,
        data_dir: Path = DEFAULT_DATA_DIR,
        tom_master: Path = DEFAULT_TOM_MASTER,
        *,
        seed_artifact: Path | None = None,
        mechanics_profile: Path | None = None,
        document_embedding_provider=None,
        stream1_document_indexes=None,
    ) -> None:
        self.data_dir = data_dir.expanduser().resolve()
        self.tom_master = tom_master.expanduser().resolve()
        self.document_embedding_provider = document_embedding_provider
        # Explicit caller-owned native sessions. This route never creates a
        # ProjectRuntime or falls back to the historical document index.
        self.stream1_document_indexes = dict(stream1_document_indexes or {})
        sys.dont_write_bytecode = True  # Imports must not write caches in frozen upstream.
        self.data_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.data_dir, 0o700)
        bootstrap = self.data_dir / "runtime-bootstrap"
        bootstrap.mkdir(parents=True, exist_ok=True)
        cursor_key_path = bootstrap / "document-research-cursor.key"
        if cursor_key_path.is_file():
            self._document_research_cursor_master_key = cursor_key_path.read_bytes()
        else:
            self._document_research_cursor_master_key = os.urandom(32)
            _atomic_write(
                cursor_key_path, self._document_research_cursor_master_key,
            )
            os.chmod(cursor_key_path, 0o600)
        if len(self._document_research_cursor_master_key) != 32:
            raise ValueError("document research cursor key is invalid")
        # Force all upstream scratch/cache writes into Tom Assist's state root and
        # force the deterministic local stub provider. The gateway never permits
        # an inherited provider configuration to create a network LLM call.
        os.environ["TOM_PERSIST_DIR"] = str(bootstrap)
        os.environ["TOM_LLM_PROVIDER"] = "stub"
        os.environ["TOM_AGENT_LLM_PROVIDER"] = "stub"
        os.environ["TOM_FEELING_WHEEL_ENABLED"] = "0"
        mechanics_profile_path = (
            mechanics_profile.expanduser().resolve()
            if mechanics_profile is not None
            else self.tom_master / MECHANICS_PROFILE_RELATIVE
        )
        mechanics_parameters = _load_profile_environment(mechanics_profile_path)
        seed_artifact_path = (
            seed_artifact.expanduser().resolve()
            if seed_artifact is not None
            else self.tom_master / SEED_ARTIFACT_RELATIVE
        )
        self.seed = SeedConfiguration(
            profile=SEED_PROFILE,
            artifact_path=seed_artifact_path,
            artifact_sha256=SEED_ARTIFACT_SHA256,
            tick=SEED_TICK,
            branch_count=SEED_BRANCH_COUNT,
            mechanics_profile_path=mechanics_profile_path,
            mechanics_profile_sha256=_sha256_file(mechanics_profile_path),
            mechanics_parameters=mechanics_parameters,
        )
        actual_seed_sha256 = (
            _sha256_file(seed_artifact_path)
            if seed_artifact_path.is_file() else "missing"
        )
        if actual_seed_sha256 != self.seed.artifact_sha256:
            raise ValueError(
                "document Tree seed digest mismatch: "
                f"expected {self.seed.artifact_sha256}, got {actual_seed_sha256}"
            )
        if str(self.tom_master) not in sys.path:
            sys.path.insert(0, str(self.tom_master))
        self.runtime_sha = _actual_sha(self.tom_master)
        self.pinned_sha_match = self.runtime_sha.startswith(PINNED_SHA)
        if not self.pinned_sha_match:
            LOGGER.warning("tom_master pin mismatch: expected %s, actual %s", PINNED_SHA, self.runtime_sha)
        self._projects: dict[str, ProjectRuntime] = {}
        self._projects_lock = threading.Lock()
        from gateway.oauth_provider import OAuthProvider
        self.oauth_provider = OAuthProvider()
        self._probe_imports()

    @staticmethod
    def _probe_imports() -> None:
        from agency.mechanics.sicd_engine import TreeGrowthEngine as _engine
        from agency.reasoning.structure_repair_loop import adjudicate_reasoning_structure as _structure
        from memory.rgm import ReflectionGatedMemory as _memory
        from metrics.claim_verifier import verify_claims as _claims
        from metrics.drift_verifier import DriftVerifier as _drift
        assert all((_engine, _memory, _structure, _claims, _drift))

    def project(self, project_id: Any) -> ProjectRuntime:
        project_id = _safe_project_id(project_id)
        with self._projects_lock:
            runtime = self._projects.get(project_id)
            if runtime is None:
                from gateway.runtime_archive import finalize_pending
                finalize_pending(self.data_dir / "projects" / project_id)
                runtime = self.create_project_runtime(
                    project_id, self.data_dir / "projects" / project_id / "tom",
                )
                self._projects[project_id] = runtime
            return runtime

    def create_project_runtime(
        self, project_id: str, state_dir: Path, *,
        allow_document_index_migration: bool = False,
    ):
        return ProjectRuntime(
            project_id,
            state_dir,
            self.runtime_sha,
            self.seed,
            self.document_embedding_provider,
            allow_document_index_migration=allow_document_index_migration,
            document_research_cursor_key=self.document_research_cursor_key(project_id),
        )

    def document_research_cursor_key(self, project_id: Any) -> bytes:
        project_id = _safe_project_id(project_id)
        return hmac.new(
            self._document_research_cursor_master_key,
            project_id.encode("utf-8"),
            hashlib.sha256,
        ).digest()

    def migrate_project_document_tree(self, project_id: Any) -> dict[str, Any]:
        """Explicitly build/repair one project's dedicated document Tree.

        This operation is deliberately separate from preview, diagnostics and
        ordinary project opening. The permanent source inventory is the
        migration authority; the legacy shared index, when present, is retained
        unchanged as recoverable historical evidence.
        """
        project_id = _safe_project_id(project_id)
        with self._projects_lock:
            if project_id in self._projects:
                runtime = self._projects[project_id]
                return {
                    "status": "already_ready",
                    "project_id": project_id,
                    "document_tree": runtime.document_index.head_metadata(),
                    "metadata_changes": [],
                    "declared_structure_changes": [],
                }
            from gateway.runtime_archive import finalize_pending
            project_root = self.data_dir / "projects" / project_id
            finalize_pending(project_root)
            state_dir = project_root / "tom"
            library_path = state_dir / "library.sqlite3"
            if not library_path.is_file():
                raise ValueError("project permanent library does not exist")

            def inventory(database: sqlite3.Connection):
                documents = database.execute(
                    "SELECT document_id,content_sha256,byte_length,tombstoned_at "
                    "FROM documents ORDER BY document_id"
                ).fetchall()
                chunks = database.execute(
                    "SELECT document_id,chunk_index,analysis_digest,load_signature_json "
                    "FROM document_chunks ORDER BY document_id,chunk_index"
                ).fetchall()
                structures = database.execute(
                    "SELECT document_id,structure_digest FROM document_declared_structures "
                    "ORDER BY document_id"
                ).fetchall()
                return documents, chunks, structures

            before_db = sqlite3.connect(library_path)
            try:
                before_documents, before_chunks, before_structures = inventory(before_db)
            finally:
                before_db.close()
            experience_before = {
                name: path.read_bytes()
                for name, path in (
                    ("tree_state.json", state_dir / "tree_state.json"),
                    ("rgm_state.json", state_dir / "rgm_state.json"),
                )
                if path.is_file()
            }
            seed_before = _sha256_file(self.seed.artifact_path)
            legacy_root = self.data_dir / "document-index"
            legacy_before = {
                path.name: _sha256_file(path)
                for path in sorted(legacy_root.glob("*"))
                if path.is_file()
            }
            runtime = self.create_project_runtime(
                project_id, state_dir, allow_document_index_migration=True,
            )
            after_documents, after_chunks, after_structures = inventory(runtime.library.db)
            if after_documents != before_documents:
                raise ValueError("document Tree migration changed permanent source identity")
            before_chunk_ids = [(row[0], int(row[1])) for row in before_chunks]
            after_chunk_ids = [(row[0], int(row[1])) for row in after_chunks]
            if after_chunk_ids != before_chunk_ids:
                raise ValueError("document Tree migration changed permanent chunk identity")
            if seed_before != _sha256_file(self.seed.artifact_path):
                raise ValueError("document Tree migration changed the canonical seed")
            for name, data in experience_before.items():
                if (state_dir / name).read_bytes() != data:
                    raise ValueError("document Tree migration changed the experience Tree")
            legacy_after = {
                path.name: _sha256_file(path)
                for path in sorted(legacy_root.glob("*"))
                if path.is_file()
            }
            if legacy_after != legacy_before:
                raise ValueError("document Tree migration changed the legacy shared index")
            metadata_changes = [
                {
                    "document_id": after[0],
                    "chunk_index": int(after[1]),
                    "analysis_digest_before": before[2],
                    "analysis_digest_after": after[2],
                    "load_signature_added": before[3] is None and after[3] is not None,
                }
                for before, after in zip(before_chunks, after_chunks)
                if before != after
            ]
            before_structure_map = {row[0]: row[1] for row in before_structures}
            after_structure_map = {row[0]: row[1] for row in after_structures}
            declared_structure_changes = [
                {
                    "document_id": document_id,
                    "structure_digest_before": before_structure_map.get(document_id),
                    "structure_digest_after": after_structure_map.get(document_id),
                }
                for document_id in sorted(
                    set(before_structure_map) | set(after_structure_map)
                )
                if before_structure_map.get(document_id) != after_structure_map.get(document_id)
            ]
            self._projects[project_id] = runtime
            return {
                "status": "migrated",
                "migration_version": "tom-assist-project-document-tree-migration/1.0",
                "project_id": project_id,
                "document_count": len(after_documents),
                "chunk_count": len(after_chunks),
                "declared_structure_count_before": len(before_structures),
                "declared_structure_count_after": len(after_structures),
                "metadata_changes": metadata_changes,
                "declared_structure_changes": declared_structure_changes,
                "source_inventory_unchanged": True,
                "experience_tree_unchanged": True,
                "canonical_seed_unchanged": True,
                "legacy_shared_index_preserved": legacy_after == legacy_before,
                "document_tree": runtime.document_index.head_metadata(),
            }

    def capabilities(self) -> dict[str, Any]:
        from gateway.document_tree import DOCUMENT_TREE_VERSION
        return {
            "runtime_version": self.runtime_sha,
            "state_format_version": STATE_FORMAT_VERSION,
            "supports_load_ingest": True,
            "supports_branch_activation": True,
            "supports_candidate_ranking": True,
            "supports_state_snapshot": True,
            "supports_commit": True,
            "supports_conflict_check": True,
            "supports_trajectory_digest": True,
            "supports_readonly_ranking": True,
            "supports_checkpoint_restore": True,
            "supports_nonmutating_load_preview": False,
            "engine_parity_profile": "tom-master/direct",
            "engine_parity_verified_at_commit": PINNED_SHA,
            "seed_profile": self.seed.profile,
            "seed_artifact_sha256": self.seed.artifact_sha256,
            "seed_tick": self.seed.tick,
            "seed_branch_count": self.seed.branch_count,
            "mechanics_profile": self.seed.mechanics_profile_path.name,
            "mechanics_profile_sha256": self.seed.mechanics_profile_sha256,
            "mechanics_parameters": dict(sorted(self.seed.mechanics_parameters.items())),
            "kappa_decay_source": KAPPA_DECAY_SOURCE,
            "preview_channels": ["lexical", "structural_geometry", "document_dense"],
            "commit_dynamics": list(COMMIT_DYNAMICS),
            "supports_documents": True,
            "document_chunking_version": DOCUMENT_CHUNKING_VERSION,
            "document_embedding_version": DOCUMENT_EMBEDDING_VERSION,
            "document_max_source_chars": MAX_DOCUMENT_SOURCE_CHARS,
            "document_max_chunks": MAX_DOCUMENT_CHUNKS,
            "document_structural_parsing": False,
            "document_packet_admission": True,
            "document_packet_admission_version": DOCUMENT_PACKET_ADMISSION_VERSION,
            "document_tree_version": DOCUMENT_TREE_VERSION,
            "document_tree_isolation": "dedicated_per_project",
            "supports_document_declared_structure": True,
            "document_declared_structure_version": DECLARED_STRUCTURE_VERSION,
            "parser_glossary_enabled": False,
            "parser_glossary_version": GLOSSARY_VERSION,
            "parser_glossary_term_count": 0,
            "parser_glossary_sha256": build_project_glossary([], [])["sha256"],
            "parser_glossary_max_terms": MAX_GLOSSARY_TERMS,
            "parser_glossary_max_characters": MAX_GLOSSARY_CHARACTERS,
            **DEFAULT_SETTINGS,
        }

    def handle(self, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
        payload = payload or {}
        try:
            if method == "POST" and path == "/document/native-memory/answer":
                project_id = _safe_project_id(payload.get("project_id"))
                action = payload.get("action", "answer")
                if action not in ("status", "answer"):
                    raise ValueError("unsupported native answer action")
                if action == "answer" and payload.get("explicit_answer") is not True:
                    raise ValueError("explicit local answer action required")
                service = getattr(self, "native_memory_service", None)
                profile = os.environ.get("TOM_ASSIST_NATIVE_MEMORY_PROFILE")
                if service is None and profile:
                    # Only an operator-configured profile can attach a frozen tree.
                    # The request cannot supply a checkpoint or another project's sources.
                    from gateway.native_memory import NativeMemoryService
                    with self._projects_lock:
                        service = getattr(self, "native_memory_service", None)
                        if service is None:
                            service = NativeMemoryService.from_profile(Path(profile))
                            self.native_memory_service = service
                if service is None:
                    if action == "status":
                        return 200, {"ready": False, "scope": "No learned document collection is attached to this project."}
                    return 503, {"error": "no learned document collection is attached to this project"}
                if action == "status":
                    return 200, service.status(project_id)
                return 200, service.answer(project_id, payload.get("question"))
            if method == "POST" and path == "/document/stream1/retrieve":
                project_id = _safe_project_id(payload.get("project_id"))
                index = getattr(self, "stream1_document_indexes", {}).get(project_id)
                if index is None:
                    return 503, {"error": "no prepared Stream 1 document session for this project"}
                return 200, index.retrieve(payload.get("question"))
            if method == "POST" and path == "/inspection/gemma":
                return 200, GemmaInspection.inspect(self, payload)
            if method == "GET" and path == "/provider/status":
                return 200, self.oauth_provider.status()
            if method == "POST" and path == "/provider/complete":
                from gateway.oauth_provider import ProviderFailure
                try:
                    if payload.get("explicit_send") is not True:
                        raise ProviderFailure("EXPLICIT_SEND_REQUIRED")
                    return 200, self.oauth_provider.complete(payload.get("prompt"))
                except ProviderFailure as error:
                    return 409, {"error":str(error)}
            if method == "GET" and path == "/health":
                return 200, {"status": "ok", "gateway_version": GATEWAY_VERSION, "runtime_version": self.runtime_sha, "pinned_sha_match": self.pinned_sha_match}
            if method == "GET" and path == "/capabilities":
                return 200, self.capabilities()
            if method == "POST" and path == "/document/research/intent":
                return 200, parse_research_intent(
                    str(payload.get("user_text") or "")
                )
            if method == "POST" and path == "/archive/runtime/export":
                from gateway.runtime_archive import export_snapshot
                return 200, export_snapshot(self, _safe_project_id(payload.get("project_id")), payload["directory"])
            if method == "POST" and path == "/archive/runtime/verify":
                from gateway.runtime_archive import validate_snapshot
                return 200, validate_snapshot(self, Path(payload["directory"]))
            if method == "POST" and path == "/archive/runtime/import":
                from gateway.runtime_archive import import_snapshot
                with self._projects_lock:
                    if payload["context"]["project_id"] in self._projects:
                        raise ValueError("runtime project is already active; import never overwrites")
                    return 200, import_snapshot(self, payload["action"], payload["directory"], payload["context"])
            if method == "POST" and path == "/preview/rank":
                k = max(1, min(int(payload.get("k", 10)), 100))
                max_chars = max(1, min(int(payload.get("max_chars", 2000)), 32000))
                return 200, self.project(payload.get("project_id")).preview_rank(
                    str(payload.get("user_text") or ""), k, max_chars,
                    payload.get("declared_glossary_titles") or [],
                    payload.get("document_research_cursor"),
                )
            if method == "POST" and path == "/turn/commit":
                key = str(payload.get("idempotency_key") or "")
                if not key: raise ValueError("idempotency_key is required")
                return 200, self.project(payload.get("project_id")).commit_turn(
                    str(payload.get("role") or "user"), str(payload.get("text") or ""), key,
                    response_text=payload.get("response_text"),
                    activated_branch_ids=payload.get("activated_branch_ids") or [],
                    admitted_anchor_ids=payload.get("admitted_anchor_ids") or [],
                    conflict_dismissed=payload.get("conflict_dismissed", False),
                    packet_digest=payload.get("packet_digest"),
                    retrieval_trace=payload.get("retrieval_trace") or [])
            if method == "POST" and path == "/document/ingest":
                if payload.get("explicit_user_action") is not True:
                    raise ValueError("document ingestion requires an explicit user action")
                return 200, self.project(payload.get("project_id")).ingest_document(
                    payload.get("display_name"), payload.get("content"),
                    payload.get("media_type"),
                )
            if method == "POST" and path == "/document/tree/migrate":
                if payload.get("explicit_user_action") is not True:
                    raise ValueError("document Tree migration requires an explicit user action")
                return 200, self.migrate_project_document_tree(payload.get("project_id"))
            if method == "POST" and path == "/document/list":
                return 200, {"documents": self.project(
                    payload.get("project_id")
                ).list_documents(payload.get("include_withdrawn", False))}
            if method == "POST" and path == "/document/get":
                return 200, self.project(payload.get("project_id")).get_document(
                    payload.get("document_id")
                )
            if method == "POST" and path == "/document/withdraw":
                if payload.get("explicit_user_action") is not True:
                    raise ValueError("document withdrawal requires an explicit user action")
                return 200, self.project(payload.get("project_id")).withdraw_document(
                    payload.get("document_id"), payload.get("tombstoned_at")
                )
            if method == "POST" and path == "/project/settings":
                runtime = self.project(payload.get("project_id"))
                return 200, runtime.update_settings(payload.get("settings") or {})
            if method == "POST" and path == "/memory/diagnostics":
                return 200, self.project(payload.get("project_id")).memory_diagnostics(int(payload.get("after_event_id", 0)))
            if method == "POST" and path == "/checkpoint/save":
                return 200, self.project(payload.get("project_id")).save_checkpoint()
            if method == "POST" and path == "/checkpoint/restore":
                return 200, self.project(payload.get("project_id")).restore_checkpoint(str(payload.get("checkpoint_id") or ""))
            if method == "POST" and path == "/verify/drift":
                return 200, self._verify_drift(payload)
            if method == "POST" and path == "/verify/guardrails":
                from gateway.guardrail_resonance import resonate_guardrails
                return 200, resonate_guardrails(payload)
            if method == "POST" and path == "/verify/claims":
                return 200, self._verify_claims(payload)
            if method == "POST" and path == "/adjudicate/structure":
                return 200, self._adjudicate_structure(payload)
            return 404, {"error": "not_found", "path": path}
        except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as error:
            return 400, {"error": error.__class__.__name__, "message": str(error)}
        except Exception as error:
            LOGGER.exception("gateway request failed: %s %s", method, path)
            return 500, {"error": error.__class__.__name__, "message": str(error)[:500]}

    @staticmethod
    def _verify_drift(payload: dict[str, Any]) -> dict[str, Any]:
        from metrics.drift_verifier import DriftVerifier, Invariant

        verifier = DriftVerifier()
        invariants = []
        for row in list(payload.get("invariants") or [])[:100]:
            patterns = tuple(re.compile(str(pattern), re.IGNORECASE) for pattern in list(row.get("contradict_patterns") or [])[:20])
            invariants.append(Invariant(str(row.get("id") or row.get("invariant_id") or "ledger"), str(row.get("description") or "ledger invariant"), patterns))
        verifier.invariants = invariants
        answer = str(payload.get("answer_text") or "")
        decision = verifier.verify_llm_output(
            llm_output={"plan": {"summary": answer}},
            tx_id=str(payload.get("tx_id") or "tom-assist"),
            tick=None,
            guard_outcome=None,
            llm_output_hash=hashlib.sha256(answer.encode("utf-8")).hexdigest(),
        )
        return asdict(decision)

    @staticmethod
    def _verify_claims(payload: dict[str, Any]) -> dict[str, Any]:
        from metrics.claim_verifier import verify_claims
        from metrics.grounding_index import ChunkRecord, GroundingIndex

        records = []
        for index, raw in enumerate(list(payload.get("corpus_chunks") or [])[:1000]):
            row = raw if isinstance(raw, dict) else {"text": str(raw)}
            content = str(row.get("text") or row.get("content") or "")
            source = str(row.get("source") or row.get("source_path") or f"chunk-{index}")
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            records.append(ChunkRecord(
                chunk_id=str(row.get("id") or hashlib.sha256(f"{source}:{index}:{content_hash}".encode()).hexdigest()[:32]),
                source_path=source, start_offset=0, end_offset=len(content.encode("utf-8")),
                content_hash=content_hash, content_length=len(content.encode("utf-8")),
                chunk_index=index, total_chunks_in_source=1, content=content,
            ))
        summary = verify_claims([str(claim) for claim in list(payload.get("claims") or [])[:100]], GroundingIndex(chunks=records), override_enabled=True)
        result = summary.to_dict()
        result["results"] = [item.to_dict() for item in summary.results]
        return result

    @staticmethod
    def _adjudicate_structure(payload: dict[str, Any]) -> dict[str, Any]:
        from agency.reasoning.structure_repair_loop import ExpectedReasoningStructure, ReasoningStructureProposal, adjudicate_reasoning_structure

        proposal_raw = dict(payload.get("proposal") or {})
        expected_raw = dict(payload.get("expected") or {})
        proposal = ReasoningStructureProposal(
            selected_operator=str(proposal_raw.get("selected_operator") or ""),
            dependency_steps=tuple(proposal_raw.get("dependency_steps") or ()),
            constraints_checked=tuple(proposal_raw.get("constraints_checked") or ()),
            evidence_used=tuple(proposal_raw.get("evidence_used") or ()),
            proposed_conclusion=str(proposal_raw.get("proposed_conclusion") or ""),
            final_answer_attempted=bool(proposal_raw.get("final_answer_attempted", False)),
            invented_evidence=bool(proposal_raw.get("invented_evidence", False)),
        )
        expected = ExpectedReasoningStructure(
            expected_operator=str(expected_raw.get("expected_operator") or ""),
            required_dependencies=tuple(expected_raw.get("required_dependencies") or ()),
            required_constraints=tuple(expected_raw.get("required_constraints") or ()),
            required_evidence=tuple(expected_raw.get("required_evidence") or ()),
            forbidden_evidence=tuple(expected_raw.get("forbidden_evidence") or ()),
            forbidden_moves=tuple(expected_raw.get("forbidden_moves") or ()),
            stakes=str(expected_raw.get("stakes") or "normal"),
            failure_action=str(expected_raw.get("failure_action") or "block_final_answer"),
        )
        return adjudicate_reasoning_structure(proposal, expected).to_dict()


class _UnixHTTPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, socket_path: str, gateway: TomGateway) -> None:
        self.gateway = gateway
        super().__init__(socket_path, _RequestHandler)


class _RequestHandler(BaseHTTPRequestHandler):
    server: _UnixHTTPServer
    protocol_version = "HTTP/1.0"

    def log_message(self, format_string: str, *args: Any) -> None:
        LOGGER.debug(format_string, *args)

    def do_GET(self) -> None:
        self._dispatch(None)

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0") or 0)
        if length > MAX_REQUEST_BYTES:
            self._respond(413, {"error": "request_too_large"})
            return
        raw = self.rfile.read(length)
        payload = json.loads(raw or b"{}")
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        self._dispatch(payload)

    def _dispatch(self, payload: dict[str, Any] | None) -> None:
        status, response = self.server.gateway.handle(self.command, self.path, payload)
        self._respond(status, response)

    def _respond(self, status: int, payload: dict[str, Any]) -> None:
        data = canonical_json(payload)
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve(socket_path: Path, gateway: TomGateway) -> None:
    socket_path = socket_path.expanduser().resolve()
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    if socket_path.exists():
        socket_path.unlink()
    server = _UnixHTTPServer(str(socket_path), gateway)
    os.chmod(socket_path, 0o600)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()
        socket_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", type=Path, default=DEFAULT_DATA_DIR / "tom_gateway.sock")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--tom-master", type=Path, default=DEFAULT_TOM_MASTER)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    serve(args.socket, TomGateway(args.data_dir, args.tom_master))


if __name__ == "__main__":
    main()
