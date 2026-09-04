"""Shared Tom Assist document-index Tree with project-filtered evidence receipts."""
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


DOCUMENT_TREE_VERSION = "tom-assist-shared-document-tree/1.1"
DOCUMENT_TREE_LOAD_BATCH_SIZE = 16
DOCUMENT_TREE_ADDRESS_BRANCHES = 32


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


class SharedDocumentTreeIndex:
    """One dedicated mutable document Tree shared by Tom Assist projects.

    Shared structural influence is intentional.  Receipts carry project IDs and
    retrieval callers may pass only chunks from their active project, preventing
    document text or candidate IDs from crossing the project boundary.
    """

    def __init__(self, data_dir: Path, seed: Any, config: Any) -> None:
        from agency.mechanics.sicd_engine import TreeGrowthEngine

        self.state_dir = Path(data_dir).resolve() / "document-index"
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
        return {
            (document_id, int(index))
            for document_id, index in self.db.execute(
                "SELECT document_id,chunk_index FROM chunk_commits WHERE project_id=?",
                (project_id,),
            )
        }

    def project_commits(self, project_id: str) -> list[dict[str, Any]]:
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
        return int(self.db.execute(
            "SELECT COUNT(*) FROM chunk_commits WHERE project_id=?", (project_id,),
        ).fetchone()[0])

    def project_chunk_metadata(self, project_id: str) -> dict[tuple[str, int], dict[str, Any]]:
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
        """Score overlap between retained chunk addresses and the query region.

        This is a Tree lookup, not a second embedding cosine.  If the query and
        every candidate have the same/no branch overlap, callers receive an
        explicit non-informative channel and must not manufacture a ranking from
        floating-point noise.
        """
        query_ranks = {
            str(branch_id): (rank, float(score))
            for rank, (branch_id, _, score) in enumerate(cohort, 1)
        }
        result = {}
        raw_scores = []
        for row in chunks:
            address = self.db.execute(
                "SELECT address_branches_json FROM chunk_commits WHERE "
                "project_id=? AND document_id=? AND chunk_index=?",
                (project_id, row["document_id"], int(row["chunk_index"])),
            ).fetchone()
            if address is None:
                raise ValueError("active project chunk is absent from the document Tree")
            overlaps = []
            for branch in json.loads(address[0]):
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
            score = sum(item["overlap_score"] for item in overlaps)
            raw_scores.append(score)
            row_id = f"{row['document_id']}:chunk:{int(row['chunk_index'])}"
            result[row_id] = {
                "score": score,
                "matched_branch_id": overlaps[0]["branch_id"] if overlaps else "",
                "branch_overlap_count": len(overlaps),
            }
        minimum = min(raw_scores, default=0.0)
        maximum = max(raw_scores, default=0.0)
        informative = maximum > 0.0 and maximum - minimum > 1e-12
        return result, {
            "informative": informative,
            "score_min": minimum,
            "score_max": maximum,
            "score_spread": maximum - minimum,
            "query_branch_count": len(query_ranks),
        }
