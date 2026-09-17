"""Project-local Tom Assist document Trees with evidence-addressed receipts."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
from typing import Any, Mapping, Sequence

from gateway.dense_load17 import (
    DOCUMENT_DENSE_LOAD_VERSION,
    compile_document_dense_load,
)
from gateway.document_ingestion import DOCUMENT_EMBEDDING_VERSION, decode_vector_f32
from gateway.structural_analysis import CHANNELS


DOCUMENT_TREE_VERSION = "tom-assist-project-document-tree/2.0"
DOCUMENT_TREE_RETRIEVAL_VERSION = "tom-assist-document-tree-native-resonance/1.0"
DOCUMENT_TREE_LOAD_BATCH_SIZE = 16
DOCUMENT_TREE_ADDRESS_BRANCHES = 32
DOCUMENT_ROUTING_BASIS_NAMES = (
    "L_axis", "S_axis", "T_axis", "delta_x", "delta_F", "phi",
    "intensity", "confidence",
)


def bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _overlaps(row: Mapping[str, Any], start: int, end: int) -> bool:
    span = row.get("span")
    return (
        isinstance(span, Mapping)
        and type(span.get("start")) is int
        and type(span.get("end")) is int
        and span["start"] < end
        and span["end"] > start
    )


def declared_graph_for_chunk(
    declared_structure: Mapping[str, Any] | None,
    *,
    document_id: str,
    chunk_index: int,
    start: int,
    end: int,
) -> list[list[str]]:
    """Return only exact authored dependency/precedence edges touching a chunk."""
    if not isinstance(declared_structure, Mapping):
        return []
    source = f"{document_id}:chunk:{chunk_index}"
    graph: list[list[str]] = []
    references = declared_structure.get("references", {}).get("references", [])
    for row in references if isinstance(references, list) else ():
        target = row.get("named_identifier") if isinstance(row, Mapping) else None
        if (
            isinstance(row, Mapping)
            and _overlaps(row, start, end)
            and row.get("outcome") == "resolved"
            and isinstance(target, str)
            and target
        ):
            graph.append([source, "references", target])
    relations = declared_structure.get("declared_precedence", {}).get("relations", [])
    for row in relations if isinstance(relations, list) else ():
        if not isinstance(row, Mapping) or not _overlaps(row, start, end):
            continue
        if row.get("relation_kind") == "precedes":
            higher, lower = row.get("higher_identifier"), row.get("lower_identifier")
            if isinstance(higher, str) and higher and isinstance(lower, str) and lower:
                graph.append([higher, "precedes", lower])
        elif row.get("relation_kind") == "notwithstanding":
            target = row.get("target_identifier")
            if isinstance(target, str) and target:
                graph.append([source, "notwithstanding", target])
    return sorted(graph)


def clause_provenance_for_chunk(
    declared_structure: Mapping[str, Any] | None,
    *,
    start: int,
    end: int,
) -> list[dict[str, Any]]:
    """Return every exact authored address whose span overlaps the chunk."""
    if not isinstance(declared_structure, Mapping):
        return []
    index = declared_structure.get("clause_index", {})
    entries = index.get("entries", []) if isinstance(index, Mapping) else []
    rows = []
    for entry in entries if isinstance(entries, list) else ():
        if not isinstance(entry, Mapping) or not _overlaps(entry, start, end):
            continue
        rows.append({
            "entry_id": str(entry.get("entry_id") or ""),
            "kind": str(entry.get("kind") or ""),
            "identifier": str(entry.get("identifier") or ""),
            "display_identifier": str(entry.get("display_identifier") or ""),
            "title": str(entry.get("title") or ""),
            "span": {
                "start": int(entry["span"]["start"]),
                "end": int(entry["span"]["end"]),
            },
            "status": str(entry.get("status") or ""),
        })
    return sorted(rows, key=lambda row: (
        row["span"]["start"], row["span"]["end"], row["entry_id"],
    ))


class Stream1DocumentIndex:
    """Source pointers ranked by native routing patterns on a prepared Stream 1 Tree.

    This is a ToM_assist retrieval policy, not a document-ranking API supplied by
    Stream 1. The caller owns the Tree and MiniLM-to-matrix encoder. Construction
    stores source records; every query routes every candidate through one fresh,
    frozen set of native readings. No slot-to-document identity is assumed and
    neither construction nor retrieval teaches or saves the Tree.
    """

    VERSION = "tom-assist-stream1-strongest-branch/1.0"

    def __init__(self, tree, sources, *, encode_text, encoder_id):
        import numpy as np
        from tom_matrix import Stream1Tree

        if not isinstance(tree, Stream1Tree):
            raise ValueError("the current native Stream1Tree is required")
        if not callable(encode_text) or not isinstance(encoder_id, str) or not encoder_id:
            raise ValueError("a named MiniLM-to-matrix encoder is required")
        self.tree = tree
        self.encode_text = encode_text
        self.encoder_id = encoder_id
        self.lock = threading.RLock()
        self.sources = []
        seen = set()
        for source in sources:
            row = {key: source[key] for key in (
                "source_id", "document_id", "start", "end", "text", "text_sha256",
            )}
            if (not isinstance(row["source_id"], str) or not row["source_id"]
                    or row["source_id"] in seen
                    or not isinstance(row["document_id"], str) or not row["document_id"]):
                raise ValueError("unique source IDs and document IDs are required")
            if (type(row["start"]) is not int or type(row["end"]) is not int
                    or not 0 <= row["start"] < row["end"]
                    or not isinstance(row["text"], str)
                    or len(row["text"]) != row["end"] - row["start"]
                    or hashlib.sha256(row["text"].encode()).hexdigest() != row["text_sha256"]):
                raise ValueError("source text, offsets and hash must agree")
            matrix = self._matrix(source["matrix"])
            matrix.setflags(write=False)
            self.sources.append((row, matrix))
            seen.add(row["source_id"])
        if not self.sources:
            raise ValueError("source passages are required")

    @staticmethod
    def _matrix(value):
        import numpy as np
        matrix = np.array(value, dtype=np.float64, copy=True)
        if (matrix.shape != (32, 32) or not np.isfinite(matrix).all()
                or not np.any(matrix)):
            raise ValueError("a finite, nonzero signed 32 by 32 matrix is required")
        return matrix

    def retrieve(self, question):
        """Return exact source passages with scores and Tree-processing evidence."""
        import numpy as np
        from tom_matrix.core.integrity import array_digest
        from tom_matrix.input import matrix_address as address
        from tom_matrix.relations.precision_routing import (
            capture_precision_readings, precision_route_from_readings,
        )
        from tom_matrix.relations.spectrum import normalized

        if not isinstance(question, str) or not question.strip():
            raise ValueError("a retrieval question is required")
        query_matrix = self._matrix(self.encode_text(question))
        with self.lock:
            state_before = self.tree.state_hash()
            readings = capture_precision_readings(self.tree)
            path = precision_route_from_readings(query_matrix, readings)
            fork = next((b for b in path.order if len(path.children[b]) > 1), None)
            if fork is None:
                raise ValueError("the Tree has no main branching point")
            limbs = path.children[fork]
            public, _, _ = self.tree._terminal_returns(path)
            returned = dict(public)
            for branch in reversed(path.order):
                if path.children[branch]:
                    returned[branch] = sum((
                        path.adjoint(child, returned[child])
                        for child in path.children[branch]
                    ), np.zeros((32, 32)))
            strengths = {}
            for limb in limbs:
                value = path.adjoint(limb, returned[limb])
                parent = fork
                while parent != path.root:
                    value = path.adjoint(parent, value)
                    parent = path.parents[parent]
                value = path.frames[path.root].to_global(value)
                strengths[limb] = float(np.linalg.norm(value))
            if not all(np.isfinite(v) for v in strengths.values()) or max(strengths.values()) <= 0:
                raise ValueError("the Tree returned no finite main-branch strength")
            strongest = max(limbs, key=lambda branch: strengths[branch])
            width = address.linewidth("spectrum", True)
            query_patterns = {
                branch: address.encode(normalized(path.precision["response"][branch]), "spectrum")
                for branch in limbs
            }
            rows = []
            for source, matrix in self.sources:
                candidate = precision_route_from_readings(matrix, readings)
                scores = {
                    branch: float(address.response(
                        query_patterns[branch],
                        address.encode(normalized(candidate.precision["response"][branch]), "spectrum"),
                        width,
                    )[0]) for branch in limbs
                }
                if not all(np.isfinite(v) for v in scores.values()):
                    raise ValueError("the native matcher returned a nonfinite score")
                rows.append(dict(source, score=scores[strongest], branch_scores=scores,
                    input_matrix_sha256=array_digest(matrix),
                    pattern_sha256={branch: array_digest(candidate.precision["response"][branch])
                                    for branch in limbs}))
                del candidate
            rows.sort(key=lambda row: (-row["score"], row["source_id"]))
            matches = [row for row in rows if row["score"] >= address.MATCH]
            state_after = self.tree.state_hash()
            if state_after != state_before:
                raise ValueError("Tree changed during retrieval; results discarded")
            tied = len(matches) > 1 and matches[0]["score"] == matches[1]["score"]
            return {
                "policy": self.VERSION,
                "question": question,
                "encoder_id": self.encoder_id,
                "status": "ambiguous" if tied else "matched" if matches else "no_match",
                "matches": matches,
                "candidates": rows,
                "telemetry": {
                    "tree_class": type(self.tree).__module__ + "." + type(self.tree).__name__,
                    "state_before": state_before, "state_after": state_after,
                    "branch_count": len(readings["ids"]),
                    "first_fork": fork, "main_branches": list(limbs),
                    "branch_return_strengths": strengths, "strongest_branch": strongest,
                    "strength_tied": sum(v == strengths[strongest] for v in strengths.values()) > 1,
                    "threshold": address.MATCH,
                    "pattern_stage": "native_precision_stiffness_response_before_memory_readout",
                    "query_matrix_sha256": array_digest(query_matrix),
                    "query_pattern_sha256": {branch: array_digest(path.precision["response"][branch])
                                             for branch in limbs},
                    "query_return_sha256": array_digest(path.frames[path.root].to_global(returned[path.root])),
                    "sources_routed": len(rows), "query_routed": True,
                    "tree_mutated": False, "fallback_used": False,
                },
            }


class ProjectDocumentTreeIndex:
    """One mutable 10K-derived document Tree owned by exactly one project.

    Original document prose remains in the project's permanent library. This
    directory contains only that project's evolving Tree and replayable
    evidence receipts. A second project begins from a fresh byte copy of the
    canonical seed, so structural influence cannot cross the project boundary.
    """

    def __init__(
        self, state_dir: Path, project_id: str, seed: Any, config: Any,
    ) -> None:
        from agency.mechanics.sicd_engine import TreeGrowthEngine
        from gateway.tom_gateway import _safe_project_id

        self.project_id = _safe_project_id(project_id)
        self.state_dir = Path(state_dir).resolve() / "document-index"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.state_dir, 0o700)
        self.path = self.state_dir / "tree_state.json"
        self.db_path = self.state_dir / "receipts.sqlite3"
        self.seed = seed
        self.config = config
        self.lock = threading.RLock()
        self.db = sqlite3.connect(
            self.db_path, isolation_level=None, check_same_thread=False,
        )
        os.chmod(self.db_path, 0o600)
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=FULL;
            PRAGMA busy_timeout=5000;
            CREATE TABLE IF NOT EXISTS tree_head(
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                tree BLOB NOT NULL, tree_digest TEXT NOT NULL,
                seed_artifact_sha256 TEXT NOT NULL,
                mechanism_version TEXT NOT NULL,
                tick INTEGER NOT NULL CHECK(tick>=0),
                branch_count INTEGER NOT NULL CHECK(branch_count>0));
            CREATE TABLE IF NOT EXISTS chunk_commits(
                commit_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL CHECK(chunk_index>=0),
                text_sha256 TEXT NOT NULL,
                analysis_digest TEXT NOT NULL,
                analysis_json TEXT NOT NULL,
                routing_basis_8d_json TEXT NOT NULL,
                address_branches_json TEXT NOT NULL,
                clause_provenance_json TEXT NOT NULL,
                tick_before INTEGER NOT NULL CHECK(tick_before>=0),
                tick_after INTEGER NOT NULL CHECK(tick_after>tick_before),
                batch_tree_digest TEXT NOT NULL,
                branch_count_after INTEGER NOT NULL CHECK(branch_count_after>0),
                UNIQUE(project_id,document_id,chunk_index));
            CREATE TABLE IF NOT EXISTS activation_events(
                event_id INTEGER PRIMARY KEY,
                project_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                event_type TEXT NOT NULL CHECK(event_type IN ('activated','withdrawn','backfilled')),
                event_time TEXT NOT NULL,
                tree_digest TEXT NOT NULL);
        """)
        foreign_projects = {
            str(row[0])
            for table in ("chunk_commits", "activation_events")
            for row in self.db.execute(f"SELECT DISTINCT project_id FROM {table}")
        } - {self.project_id}
        if foreign_projects:
            raise ValueError("project document Tree contains foreign-project receipts")
        head = self.db.execute(
            "SELECT tree,tree_digest,seed_artifact_sha256,mechanism_version,tick,"
            "branch_count FROM tree_head WHERE singleton=1"
        ).fetchone()
        if head is None:
            tree = seed.artifact_path.read_bytes()
            if hashlib.sha256(tree).hexdigest() != seed.artifact_sha256:
                raise ValueError("document Tree seed digest mismatch")
            self._write(tree)
            self.engine = TreeGrowthEngine.load(str(self.path), cfg=config)
            self._restore_fields(tree)
            if int(self.engine.state.tick) != seed.tick or len(self.engine.state.branches) != seed.branch_count:
                raise ValueError("document Tree seed lineage mismatch")
            self._set_head(tree)
        else:
            tree, digest, seed_sha, version, tick, branches = head
            if (
                bytes_digest(tree) != digest
                or seed_sha != seed.artifact_sha256
                or version != DOCUMENT_TREE_VERSION
            ):
                raise ValueError("document Tree head provenance mismatch")
            self._write(tree)
            self.engine = TreeGrowthEngine.load(str(self.path), cfg=config)
            self._restore_fields(tree)
            if int(self.engine.state.tick) != tick or len(self.engine.state.branches) != branches:
                raise ValueError("document Tree head lineage mismatch")

    def _require_project(self, project_id: str) -> None:
        if str(project_id) != self.project_id:
            raise ValueError("project document Tree refuses a foreign project")

    def _write(self, tree: bytes) -> None:
        from gateway.tom_gateway import _atomic_write
        _atomic_write(self.path, tree)

    def _restore_fields(self, tree: bytes) -> None:
        data = json.loads(tree)
        for saved in data.get("branches", []):
            branch = self.engine.state.branches.get(str(saved["id"]))
            if branch is not None:
                branch.axis_w = list(saved.get("axis_w", branch.axis_w))
                branch.sem_vec_age = int(saved.get("sem_vec_age", 0))
        self.engine.state.last_leaf_vec_update_tick = data.get("last_leaf_vec_update_tick")

    def serialize(self) -> bytes:
        descriptor, name = tempfile.mkstemp(
            prefix=".document-tree.", suffix=".json", dir=str(self.state_dir),
        )
        os.close(descriptor)
        target = Path(name)
        try:
            self.engine.save(str(target))
            return target.read_bytes()
        finally:
            target.unlink(missing_ok=True)

    def _set_head(self, tree: bytes) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO tree_head VALUES(1,?,?,?,?,?,?)",
            (
                tree, bytes_digest(tree), self.seed.artifact_sha256,
                DOCUMENT_TREE_VERSION, int(self.engine.state.tick),
                len(self.engine.state.branches),
            ),
        )

    def restore(self, tree: bytes) -> None:
        from agency.mechanics.sicd_engine import TreeGrowthEngine
        self._write(tree)
        self.engine = TreeGrowthEngine.load(str(self.path), cfg=self.config)
        self._restore_fields(tree)

    def indexed_chunk_keys(self, project_id: str) -> set[tuple[str, int]]:
        self._require_project(project_id)
        return {
            (document_id, int(index))
            for document_id, index in self.db.execute(
                "SELECT document_id,chunk_index FROM chunk_commits WHERE project_id=?",
                (project_id,),
            )
        }

    def project_commits(self, project_id: str) -> list[dict[str, Any]]:
        self._require_project(project_id)
        rows = self.db.execute(
            "SELECT document_id,chunk_index,analysis_json,address_branches_json,"
            "clause_provenance_json FROM chunk_commits "
            "WHERE project_id=? ORDER BY tick_after",
            (project_id,),
        ).fetchall()
        return [
            {
                "document_id": document_id,
                "chunk_index": int(index),
                "analysis": json.loads(encoded),
                "address_branches": json.loads(branches),
                "clause_provenance": json.loads(provenance),
            }
            for document_id, index, encoded, branches, provenance in rows
        ]

    def project_commit_count(self, project_id: str) -> int:
        self._require_project(project_id)
        return int(self.db.execute(
            "SELECT COUNT(*) FROM chunk_commits WHERE project_id=?", (project_id,),
        ).fetchone()[0])

    def project_chunk_metadata(self, project_id: str) -> dict[tuple[str, int], dict[str, Any]]:
        self._require_project(project_id)
        rows = self.db.execute(
            "SELECT document_id,chunk_index,routing_basis_8d_json,"
            "address_branches_json,clause_provenance_json FROM chunk_commits "
            "WHERE project_id=?",
            (project_id,),
        ).fetchall()
        return {
            (str(document_id), int(index)): {
                "routing_basis_8d": json.loads(routing),
                "address_branches": json.loads(branches),
                "clause_provenance": json.loads(provenance),
            }
            for document_id, index, routing, branches, provenance in rows
        }

    def durable_tree_bytes(self) -> bytes:
        with self.lock:
            return bytes(self.db.execute(
                "SELECT tree FROM tree_head WHERE singleton=1"
            ).fetchone()[0])

    def head_metadata(self) -> dict[str, Any]:
        """Return text-free provenance for diagnostics and archive proofs."""
        with self.lock:
            row = self.db.execute(
                "SELECT tree_digest,seed_artifact_sha256,mechanism_version,tick,"
                "branch_count FROM tree_head WHERE singleton=1"
            ).fetchone()
            receipt_count = int(self.db.execute(
                "SELECT COUNT(*) FROM chunk_commits"
            ).fetchone()[0])
        return {
            "project_id": self.project_id,
            "isolation": "dedicated_project_tree",
            "tree_digest": str(row[0]),
            "seed_artifact_sha256": str(row[1]),
            "mechanism_version": str(row[2]),
            "tick": int(row[3]),
            "branch_count": int(row[4]),
            "chunk_receipt_count": receipt_count,
        }

    @staticmethod
    def compile_chunk(document_id, chunk, declared_structure):
        index = int(chunk["index"] if "index" in chunk else chunk["chunk_index"])
        graph = declared_graph_for_chunk(
            declared_structure,
            document_id=document_id,
            chunk_index=index,
            start=int(chunk["start"]),
            end=int(chunk["end"]),
        )
        return compile_document_dense_load(
            str(chunk["text"]),
            decode_vector_f32(str(chunk["passage_vector"])),
            source_embedding_version=DOCUMENT_EMBEDDING_VERSION,
            directed_graph=graph,
        )

    def apply_document(self, project_id, document_id, chunks, declared_structure, event_type, event_time):
        from agency.mechanics.sicd_msr_load import LoadSignature
        from agency.mechanics.sicd_msr_load_application import apply_msr_load_to_sicd_engine

        self._require_project(project_id)
        with self.lock:
            prior = self.serialize()
            analyses, receipts = [], []
            try:
                compiled = []
                for raw in chunks:
                    chunk = dict(raw)
                    index = int(chunk["index"] if "index" in chunk else chunk["chunk_index"])
                    analysis = self.compile_chunk(document_id, chunk, declared_structure)
                    if tuple(analysis["load_signature"]) != CHANNELS or any(
                        float(value) <= 0.0 for value in analysis["load_signature"].values()
                    ):
                        raise ValueError("document Tree refuses a non-positive 17D load")
                    compiled.append((chunk, index, analysis))
                for batch_start in range(0, len(compiled), DOCUMENT_TREE_LOAD_BATCH_SIZE):
                    batch = compiled[
                        batch_start:batch_start + DOCUMENT_TREE_LOAD_BATCH_SIZE
                    ]
                    load = {
                        name: sum(item[2]["load_signature"][name] for item in batch) / len(batch)
                        for name in CHANNELS
                    }
                    drivers = {
                        name: sum(item[2]["driver_loads"][name] for item in batch) / len(batch)
                        for name in ("threat_load", "sustenance_potential", "procreation_potential")
                    }
                    signature = LoadSignature.from_mapping(load, strict=True)
                    application = apply_msr_load_to_sicd_engine(
                        self.engine, signature,
                        threat_load=drivers["threat_load"],
                        sustenance_potential=drivers["sustenance_potential"],
                        procreation_potential=drivers["procreation_potential"],
                        source=(
                            f"tom_assist_document_index:{project_id}:{document_id}:"
                            f"chunks:{batch[0][1]}-{batch[-1][1]}"
                        ),
                    )
                    if not application.applied or application.tick_after != application.tick_before + 1:
                        raise ValueError("document Tree load application failed")
                    for chunk, index, analysis in batch:
                        chunk_signature = LoadSignature.from_mapping(
                            analysis["load_signature"], strict=True,
                        )
                        from agency.mechanics.preview_readout import rank_loading_aware_8d
                        address_branches = [
                            {
                                "branch_id": branch_id,
                                "rank": rank,
                                "score": float(score),
                            }
                            for rank, (score, branch_id, _) in enumerate(
                                rank_loading_aware_8d(
                                    self.engine.state.branches.items(),
                                    chunk_signature,
                                    top_k=DOCUMENT_TREE_ADDRESS_BRANCHES,
                                ),
                                1,
                            )
                        ]
                        if not address_branches:
                            raise ValueError("document Tree produced no branch address")
                        clause_provenance = clause_provenance_for_chunk(
                            declared_structure,
                            start=int(chunk["start"]),
                            end=int(chunk["end"]),
                        )
                        analyses.append(analysis)
                        receipts.append({
                            "commit_id": "document-tree-" + hashlib.sha256(
                                f"{project_id}\0{document_id}\0{index}\0{analysis['analysis_digest']}".encode()
                            ).hexdigest()[:32],
                            "project_id": project_id,
                            "document_id": document_id,
                            "chunk_index": index,
                            "text_sha256": str(chunk["text_sha256"]),
                            "tick_before": int(application.tick_before),
                            "tick_after": int(application.tick_after),
                            "branch_count_after": int(application.branch_count_after),
                            "routing_basis_8d": analysis["routing_basis_8d"],
                            "address_branches": address_branches,
                            "clause_provenance": clause_provenance,
                        })
                tree = self.serialize()
                digest = bytes_digest(tree)
                self.db.execute("BEGIN IMMEDIATE")
                for receipt, analysis in zip(receipts, analyses):
                    values = (
                        receipt["commit_id"], project_id, document_id,
                        receipt["chunk_index"], receipt["text_sha256"],
                        analysis["analysis_digest"],
                        json.dumps(analysis, sort_keys=True, separators=(",", ":")),
                        json.dumps(
                            receipt["routing_basis_8d"],
                            sort_keys=True, separators=(",", ":"),
                        ),
                        json.dumps(
                            receipt["address_branches"],
                            sort_keys=True, separators=(",", ":"),
                        ),
                        json.dumps(
                            receipt["clause_provenance"],
                            sort_keys=True, separators=(",", ":"),
                        ),
                        receipt["tick_before"], receipt["tick_after"], digest,
                        receipt["branch_count_after"],
                    )
                    self.db.execute(
                        "INSERT INTO chunk_commits VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", values,
                    )
                self._set_head(tree)
                self.db.execute(
                    "INSERT INTO activation_events(project_id,document_id,event_type,event_time,tree_digest) "
                    "VALUES(?,?,?,?,?)",
                    (project_id, document_id, event_type, event_time, digest),
                )
                self.db.execute("COMMIT")
                self._write(tree)
                return tree, receipts, analyses
            except BaseException:
                if self.db.in_transaction:
                    self.db.execute("ROLLBACK")
                self.restore(prior)
                raise

    def record_withdrawal(self, project_id, document_id, event_time):
        self._require_project(project_id)
        with self.lock:
            head = self.db.execute("SELECT tree_digest FROM tree_head").fetchone()
            self.db.execute(
                "INSERT INTO activation_events(project_id,document_id,event_type,event_time,tree_digest) "
                "VALUES(?,?,'withdrawn',?,?)",
                (project_id, document_id, event_time, head[0]),
            )

    def set_project_chunk_analyses(self, library, document_id, receipts, analyses):
        for receipt, analysis in zip(receipts, analyses):
            encoded = json.dumps(analysis["load_signature"], sort_keys=True, separators=(",", ":"))
            library.db.execute(
                "UPDATE document_chunks SET analysis_digest=?,load_signature_json=? "
                "WHERE document_id=? AND chunk_index=? AND analysis_digest IS NULL "
                "AND load_signature_json IS NULL",
                (analysis["analysis_digest"], encoded, document_id, receipt["chunk_index"]),
            )
            if library.db.execute("SELECT changes()").fetchone()[0] != 1:
                existing = library.db.execute(
                    "SELECT analysis_digest,load_signature_json FROM document_chunks "
                    "WHERE document_id=? AND chunk_index=?",
                    (document_id, receipt["chunk_index"]),
                ).fetchone()
                if existing is not None and existing[1] == encoded:
                    # An unshipped earlier receipt format retained the same
                    # canonical 17D address but did not include the replayable
                    # 8D projection in its digest. Upgrade only that metadata;
                    # source text, vector and load values remain byte-identical.
                    library.db.execute(
                        "UPDATE document_chunks SET analysis_digest=? WHERE "
                        "document_id=? AND chunk_index=?",
                        (
                            analysis["analysis_digest"], document_id,
                            receipt["chunk_index"],
                        ),
                    )
                elif existing != (analysis["analysis_digest"], encoded):
                    raise ValueError("project document analysis identity conflict")

    def query_address(self, query_text, query_profile):
        from agency.mechanics.sicd_msr_load import LoadSignature
        from agency.mechanics.preview_readout import rank_loading_aware_8d

        vector = query_profile.get("passage_vector")
        analysis = compile_document_dense_load(
            query_text, vector, source_embedding_version=DOCUMENT_EMBEDDING_VERSION,
        )
        signature = LoadSignature.from_mapping(analysis["load_signature"], strict=True)
        with self.lock:
            ranked = rank_loading_aware_8d(
                self.engine.state.branches.items(), signature,
                top_k=DOCUMENT_TREE_ADDRESS_BRANCHES,
            )
            cohort = [
                (branch_id, list(branch.sem_vec), float(score))
                for score, branch_id, branch in ranked
            ]
            trace = [
                {
                    "branch_id": branch_id,
                    "rank": rank,
                    "loading_aware_8d_score": float(score),
                }
                for rank, (score, branch_id, _) in enumerate(ranked, 1)
            ]
        return analysis, cohort, trace

    def structural_scores(self, project_id, chunks, cohort):
        """Rank retained 8D document addresses through the pinned Tree reader.

        The historic branch-ID intersection is retained only as a diagnostic.
        Branch IDs captured while the Tree was growing are not a valid admission
        gate for a later Tree snapshot.  Source text is never part of this call.
        """
        self._require_project(project_id)
        import math
        from agency.mechanics.preview_readout import rank_by_branch_resonance

        query_ranks = {
            str(branch_id): (rank, float(score))
            for rank, (branch_id, _, score) in enumerate(cohort, 1)
        }
        if not query_ranks:
            raise ValueError("document Tree query produced no active region")
        for branch_id, branch_vector, _ in cohort:
            if (
                not isinstance(branch_id, str)
                or len(branch_vector) != 8
                or not all(math.isfinite(float(value)) for value in branch_vector)
                or math.sqrt(sum(float(value) ** 2 for value in branch_vector)) < 1e-12
            ):
                raise ValueError("document Tree query region has an invalid 8D branch vector")

        records = {}
        receipt_metadata = {}
        for row in chunks:
            row_id = f"{row['document_id']}:chunk:{int(row['chunk_index'])}"
            address = self.db.execute(
                "SELECT commit_id,analysis_digest,routing_basis_8d_json,"
                "address_branches_json,tick_after,batch_tree_digest "
                "FROM chunk_commits WHERE "
                "project_id=? AND document_id=? AND chunk_index=?",
                (project_id, row["document_id"], int(row["chunk_index"])),
            ).fetchone()
            if address is None:
                raise ValueError("active project chunk is absent from the document Tree")
            routing = json.loads(address[2])
            vector = routing.get("vector_8d") if isinstance(routing, Mapping) else None
            basis_names = routing.get("basis_names") if isinstance(routing, Mapping) else None
            if (
                list(basis_names or ()) != list(DOCUMENT_ROUTING_BASIS_NAMES)
                or not isinstance(vector, list)
                or len(vector) != 8
                or not all(math.isfinite(float(value)) for value in vector)
            ):
                raise ValueError("document Tree receipt has an invalid or incompatible 8D address")
            norm = math.sqrt(sum(float(value) ** 2 for value in vector))
            if abs(norm - 1.0) > 1e-9:
                raise ValueError("document Tree receipt 8D address is not normalized")
            records[row_id] = {"leaf_vec": [float(value) for value in vector]}

            overlaps = []
            for branch in json.loads(address[3]):
                branch_id = str(branch["branch_id"])
                query = query_ranks.get(branch_id)
                if query is None:
                    continue
                query_rank, query_score = query
                chunk_rank = int(branch["rank"])
                overlaps.append({
                    "branch_id": branch_id,
                    "query_rank": query_rank,
                    "chunk_rank": chunk_rank,
                    "query_score": query_score,
                    "chunk_score": float(branch["score"]),
                    "overlap_score": (
                        1.0 / (60.0 + query_rank)
                        + 1.0 / (60.0 + chunk_rank)
                    ),
                })
            overlaps.sort(key=lambda item: (
                -item["overlap_score"], item["branch_id"],
            ))
            receipt_metadata[row_id] = {
                "receipt_id": str(address[0]),
                "receipt_analysis_digest": str(address[1]),
                "routing_basis_names": list(basis_names),
                "routing_vector_8d": [float(value) for value in vector],
                "routing_vector_norm": norm,
                "receipt_tick_after": int(address[4]),
                "receipt_batch_tree_digest": str(address[5]),
                "historical_branch_overlap_count": len(overlaps),
                "historical_best_overlap_branch_id": (
                    overlaps[0]["branch_id"] if overlaps else None
                ),
            }

        ordered_records = {row_id: records[row_id] for row_id in sorted(records)}
        native_ranks, native_details = rank_by_branch_resonance(
            ordered_records, list(cohort),
        )
        if len(native_ranks) != len(ordered_records) or len(native_details) != len(ordered_records):
            raise ValueError("pinned document Tree reader did not rank every valid receipt")
        detail_by_id = {
            str(row_id): (str(branch_id), float(score))
            for row_id, branch_id, score in native_details
        }
        if set(detail_by_id) != set(ordered_records) or set(native_ranks) != set(ordered_records):
            raise ValueError("pinned document Tree reader returned an incomplete identity set")

        query_region_identity = bytes_digest(json.dumps(
            [
                [str(branch_id), [float(value) for value in branch_vector], float(score)]
                for branch_id, branch_vector, score in cohort
            ],
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8"))
        head = self.head_metadata()
        result = {}
        raw_scores = []
        for row_id in ordered_records:
            matched_branch_id, score = detail_by_id[row_id]
            raw_scores.append(score)
            result[row_id] = {
                "score": score,
                "matched_branch_id": matched_branch_id,
                "native_rank": int(native_ranks[row_id]),
                "query_region_identity": query_region_identity,
                "retrieval_version": DOCUMENT_TREE_RETRIEVAL_VERSION,
                "current_tree_digest": head["tree_digest"],
                **receipt_metadata[row_id],
            }
        minimum = min(raw_scores, default=0.0)
        maximum = max(raw_scores, default=0.0)
        spread = maximum - minimum
        informative = maximum > 0.0 and spread > 1e-12
        return result, {
            "retrieval_version": DOCUMENT_TREE_RETRIEVAL_VERSION,
            "reader": "agency.mechanics.preview_readout.rank_by_branch_resonance",
            "routing_basis_names": list(DOCUMENT_ROUTING_BASIS_NAMES),
            "same_basis_validated": True,
            "informative": informative,
            "score_min": minimum,
            "score_max": maximum,
            "score_spread": spread,
            "ranked_receipt_count": len(result),
            "query_branch_count": len(query_ranks),
            "query_region_identity": query_region_identity,
            "tree_digest": head["tree_digest"],
            "historical_overlap_only_count": sum(
                int(row["historical_branch_overlap_count"] > 0)
                for row in receipt_metadata.values()
            ),
            "historical_overlap_is_diagnostic_only": True,
        }
