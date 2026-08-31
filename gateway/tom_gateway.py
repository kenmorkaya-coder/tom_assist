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
import json
import logging
import os
import re
import shutil
import socketserver
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

COMMIT_DYNAMICS = ["step", "rgm_write", "leaf_vec_teach", "usage_rotation", "front_row_reseat"]
DEFAULT_SETTINGS = {"front_row_capacity": 4096, "teach_on_conflict": True}


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
    ) -> None:
        self.project_id = _safe_project_id(project_id)
        self.state_dir = state_dir.resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.state_dir, 0o700)
        self.runtime_sha = runtime_sha
        self.seed = seed
        self.lock = threading.RLock()
        self._idempotency_path = self.state_dir / "turn_idempotency.json"
        self.library = PermanentLibrary(self.state_dir / "library.sqlite3")
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
        # Legacy short anchors can be migrated losslessly. Never pretend a
        # truncated summary is the durable twin of unavailable original content.
        for record in self.rgm.state.anchors.values():
            self.library.retain(record, self.rgm._record_to_dict(record))
        if head is None:
            self.library.set_head(self._tree_path.read_bytes(), self._rgm_path.read_bytes(),
                                  self._idempotency, self.settings)

    @property
    def _tree_path(self) -> Path:
        return self.state_dir / "tree_state.json"

    @property
    def _rgm_path(self) -> Path:
        return self.state_dir / "rgm_state.json"

    @property
    def _creation_metadata_path(self) -> Path:
        return self.state_dir / "creation_metadata.json"

    def _new_engine_config(self) -> Any:
        """Apply the audited profile and reject unreviewed effective-physics changes."""
        from agency.mechanics.sicd_engine import TreeGrowthConfig

        config = TreeGrowthConfig()
        parameters = self.seed.mechanics_parameters
        config.tau1 = float(parameters["TOM_TAU1"])
        config.kappa_update.heal_rate = float(parameters["TOM_HEAL_RATE"])
        config.kappa_update.damage_rate = float(parameters["TOM_DAMAGE_RATE"])
        # WP-18/WP-19: profile + reader are authoritative as of e9fdef81c.
        # Review 3 audited 0.03 as the effective growth/operating value;
        # any future divergence requires an explicit reviewed decision.
        config.kappa_update.kappa_decay = float(parameters["TOM_KAPPA_DECAY"])
        if not abs(config.kappa_update.kappa_decay - EFFECTIVE_KAPPA_DECAY) <= 1e-12:
            raise ValueError("kappa_decay differs from audited effective physics (0.03)")
        config.kappa_update.kappa_delta_cap = float(parameters["TOM_KAPPA_DELTA_CAP"])
        config.kappa_update.kappa_nourish_recovery = float(
            parameters["TOM_KAPPA_NOURISH_RECOVERY"]
        )
        return config

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
            return {**self.settings, "front_row_count": len(self.rgm.state.anchors),
                    "library_count": self.library.db.execute("SELECT COUNT(*) FROM library_records").fetchone()[0],
                    "demotion_count": self.library.db.execute("SELECT COUNT(*) FROM demotions").fetchone()[0],
                    "demotions": events, "next_event_id": events[-1]["event_id"] if events else after}

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

    def preview_rank(self, user_text: str, k: int, max_chars: int) -> dict[str, Any]:
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
            checkpoint_digest = self._current_checkpoint_digest()
            activation_id = canonical_digest(
                {
                    "project_id": self.project_id,
                    "user_text": user_text,
                    "k": k,
                    "max_chars": max_chars,
                    "checkpoint_digest": checkpoint_digest,
                }
            )
            return {
                "activation_id": activation_id,
                "triggers": [asdict(trigger) for trigger in triggers],
                "ranked_anchors": ranked,
                "activated_branch_ids": [bid for bid, _, _ in cohort],
                "candidate_trace": fused,
                "branch_trace": branch_trace,
                "load_signature": signature.as_dict(),
                "policy_version": POLICY_VERSION,
                "checkpoint_digest": checkpoint_digest,
            }

    def commit_turn(self, role: str, text: str, idempotency_key: str, *,
                    response_text=None, activated_branch_ids=(), admitted_anchor_ids=(),
                    conflict_dismissed=False, packet_digest=None) -> dict[str, Any]:
        """Atomic quintuple. SQLite head is authoritative; JSON files are projections."""
        from gateway.front_row import FrontRowMemory
        from memory.rgm import MemoryRecord, PolicyOutcome

        with self.lock:
            if idempotency_key in self._idempotency:
                return self._idempotency[idempotency_key]
            if not text or type(conflict_dismissed) is not bool:
                raise ValueError("nonempty committed text and boolean conflict_dismissed required")
            branch_ids = sorted(set(str(bid) for bid in activated_branch_ids))
            anchor_ids = sorted(set(str(rid) for rid in admitted_anchor_ids))
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
                raw = hashlib.sha256(text.encode("utf-8")).digest()
                axes = [1.0 + raw[index] for index in range(3)]
                semantic_target = tuple(value / sum(axes) for value in axes)
                self.engine.state.tick = before_tick + 1
                # Existing commit load preserved; no new Box-2 translator.
                metrics = self.engine.step(
                    wind_vec=(semantic_target[0] - semantic_target[2], semantic_target[1] - semantic_target[2]),
                    nourishment=min(1.0, max(0.05, len(text) / 2000.0)),
                    semantic_target=semantic_target)
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
                    "K_total": float(getattr(metrics, "K_total", 0.0) or 0.0), "runtime_error_code": None,
                    "seed_profile": self.creation_metadata.get("seed_profile"),
                    "seed_checkpoint_digest": self.creation_metadata.get("initial_checkpoint_digest"),
                    "prior_checkpoint_digest": prior_digest, "checkpoint_digest": checkpoint_digest,
                    "commit_dynamics": list(COMMIT_DYNAMICS), "taught": taught, "teach_reason": teach_reason,
                    "activated_branch_ids": branch_ids, "admitted_anchor_ids": anchor_ids,
                    "readmitted_anchor_ids": readmitted_ids, "packet_digest": packet_digest,
                }
                self._idempotency[idempotency_key] = result
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


class TomGateway:
    def __init__(
        self,
        data_dir: Path = DEFAULT_DATA_DIR,
        tom_master: Path = DEFAULT_TOM_MASTER,
        *,
        seed_artifact: Path | None = None,
        mechanics_profile: Path | None = None,
    ) -> None:
        self.data_dir = data_dir.expanduser().resolve()
        self.tom_master = tom_master.expanduser().resolve()
        sys.dont_write_bytecode = True  # Imports must not write caches in frozen upstream.
        self.data_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.data_dir, 0o700)
        bootstrap = self.data_dir / "runtime-bootstrap"
        bootstrap.mkdir(parents=True, exist_ok=True)
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
        if str(self.tom_master) not in sys.path:
            sys.path.insert(0, str(self.tom_master))
        self.runtime_sha = _actual_sha(self.tom_master)
        self.pinned_sha_match = self.runtime_sha.startswith(PINNED_SHA)
        if not self.pinned_sha_match:
            LOGGER.warning("tom_master pin mismatch: expected %s, actual %s", PINNED_SHA, self.runtime_sha)
        self._projects: dict[str, ProjectRuntime] = {}
        self._projects_lock = threading.Lock()
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
                runtime = ProjectRuntime(
                    project_id,
                    self.data_dir / "projects" / project_id / "tom",
                    self.runtime_sha,
                    self.seed,
                )
                self._projects[project_id] = runtime
            return runtime

    def capabilities(self) -> dict[str, Any]:
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
            "preview_channels": ["lexical", "structural_geometry"],
            "commit_dynamics": list(COMMIT_DYNAMICS),
            **DEFAULT_SETTINGS,
        }

    def handle(self, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
        payload = payload or {}
        try:
            if method == "GET" and path == "/health":
                return 200, {"status": "ok", "gateway_version": GATEWAY_VERSION, "runtime_version": self.runtime_sha, "pinned_sha_match": self.pinned_sha_match}
            if method == "GET" and path == "/capabilities":
                return 200, self.capabilities()
            if method == "POST" and path == "/preview/rank":
                k = max(1, min(int(payload.get("k", 10)), 100))
                max_chars = max(1, min(int(payload.get("max_chars", 2000)), 12000))
                return 200, self.project(payload.get("project_id")).preview_rank(str(payload.get("user_text") or ""), k, max_chars)
            if method == "POST" and path == "/turn/commit":
                key = str(payload.get("idempotency_key") or "")
                if not key: raise ValueError("idempotency_key is required")
                return 200, self.project(payload.get("project_id")).commit_turn(
                    str(payload.get("role") or "user"), str(payload.get("text") or ""), key,
                    response_text=payload.get("response_text"),
                    activated_branch_ids=payload.get("activated_branch_ids") or [],
                    admitted_anchor_ids=payload.get("admitted_anchor_ids") or [],
                    conflict_dismissed=payload.get("conflict_dismissed", False),
                    packet_digest=payload.get("packet_digest"))
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
