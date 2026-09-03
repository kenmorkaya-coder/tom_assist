"""Project-local permanent SQLite shelf and atomic runtime commit journal."""
import hashlib
import json
import math
import os
import sqlite3


def content_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class PermanentLibrary:
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        os.chmod(path, 0o600)
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=FULL;
            PRAGMA busy_timeout=5000;
            CREATE TABLE IF NOT EXISTS library_records(
                record_id TEXT PRIMARY KEY, content_hash TEXT NOT NULL,
                content TEXT NOT NULL, record_json TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS library_content_hash ON library_records(content_hash);
            CREATE TABLE IF NOT EXISTS runtime_head(
                singleton INTEGER PRIMARY KEY CHECK(singleton=1), tree BLOB NOT NULL,
                rgm BLOB NOT NULL, idempotency TEXT NOT NULL, settings TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS demotions(
                event_id INTEGER PRIMARY KEY, record_id TEXT NOT NULL, content_hash TEXT NOT NULL,
                reason TEXT NOT NULL CHECK(reason IN ('decayed','capacity')),
                commit_key TEXT NOT NULL, tick INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS structural_commits(
                commit_key TEXT PRIMARY KEY,
                record_id TEXT NOT NULL,
                source_text_sha256 TEXT NOT NULL,
                compiler_version TEXT NOT NULL,
                analysis_digest TEXT NOT NULL,
                analysis_json TEXT NOT NULL,
                tick INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS retrieval_outcomes(
                commit_key TEXT NOT NULL,
                record_id TEXT NOT NULL,
                rank INTEGER NOT NULL CHECK(rank > 0),
                rrf_score REAL,
                lexical_rank INTEGER CHECK(lexical_rank IS NULL OR lexical_rank > 0),
                structural_rank INTEGER CHECK(structural_rank IS NULL OR structural_rank > 0),
                matched_branch_id TEXT,
                verbatim_overlap_chars INTEGER NOT NULL CHECK(verbatim_overlap_chars >= 0),
                structural_similarity REAL,
                conflict_dismissed INTEGER NOT NULL CHECK(conflict_dismissed IN (0,1)),
                tick INTEGER NOT NULL CHECK(tick >= 0),
                PRIMARY KEY(commit_key, record_id));
            CREATE TABLE IF NOT EXISTS documents(
                document_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                content_sha256 TEXT NOT NULL UNIQUE,
                content TEXT NOT NULL,
                byte_length INTEGER NOT NULL CHECK(byte_length > 0),
                media_type TEXT NOT NULL,
                chunking_version TEXT NOT NULL,
                embedding_version TEXT NOT NULL,
                ingested_tick INTEGER NOT NULL CHECK(ingested_tick >= 0),
                tombstoned_at TEXT);
            CREATE TABLE IF NOT EXISTS document_chunks(
                document_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL CHECK(chunk_index >= 0),
                start INTEGER NOT NULL CHECK(start >= 0),
                end INTEGER NOT NULL CHECK(end > start),
                text_sha256 TEXT NOT NULL,
                passage_vector TEXT NOT NULL,
                analysis_digest TEXT,
                load_signature_json TEXT,
                PRIMARY KEY(document_id, chunk_index));
        """)

    def retain(self, record, encoded):
        """Durably ingest original content before any RGM admission. Never overwrite it."""
        existing = self.get(record.id)
        if existing:
            self.assert_twin(record)
            return
        text = record.content or record.content_summary or ""
        if content_hash(text) != record.content_hash:
            raise ValueError(f"library-first: full original content required for {record.id}")
        self.db.execute("INSERT INTO library_records VALUES(?,?,?,?)",
                        (record.id, record.content_hash, text, json.dumps(encoded)))

    def get(self, record_id):
        row = self.db.execute("SELECT content_hash,content,record_json FROM library_records WHERE record_id=?",
                              (record_id,)).fetchone()
        return None if row is None else {"content_hash": row[0], "content": row[1], "record": json.loads(row[2])}

    def first_id_for_hash(self, digest):
        row = self.db.execute("SELECT record_id FROM library_records WHERE content_hash=? ORDER BY rowid LIMIT 1", (digest,)).fetchone()
        return row[0] if row else None

    def assert_twin(self, record):
        row = self.db.execute("SELECT content FROM library_records WHERE content_hash=? AND record_id=?",
                              (record.content_hash, record.id)).fetchone()
        if row is None or content_hash(row[0]) != record.content_hash:
            raise ValueError(f"library-first invariant violated: {record.id}")

    def demote(self, record, encoded, reason, commit_key, tick):
        self.assert_twin(record)
        # Only seating metadata is updated; permanent content/hash are immutable.
        self.db.execute("UPDATE library_records SET record_json=? WHERE record_id=?",
                        (json.dumps(encoded), record.id))
        self.db.execute("INSERT INTO demotions(record_id,content_hash,reason,commit_key,tick) VALUES(?,?,?,?,?)",
                        (record.id, record.content_hash, reason, commit_key, tick))

    def head(self):
        return self.db.execute("SELECT tree,rgm,idempotency,settings FROM runtime_head WHERE singleton=1").fetchone()

    def set_head(self, tree, rgm, idempotency, settings):
        self.db.execute("INSERT OR REPLACE INTO runtime_head VALUES(1,?,?,?,?)",
                        (tree, rgm, json.dumps(idempotency, sort_keys=True), json.dumps(settings, sort_keys=True)))

    def events(self, after=0, limit=200):
        rows = self.db.execute("SELECT event_id,record_id,content_hash,reason,commit_key,tick FROM demotions WHERE event_id>? ORDER BY event_id LIMIT ?",
                               (after, limit)).fetchall()
        names = ("event_id", "record_id", "content_hash", "reason", "commit_key", "tick")
        return [dict(zip(names, row)) for row in rows]

    def retain_structural_commit(self, commit_key, record_id, analysis, tick):
        """Atomically retain the validated analysis used by one runtime commit."""
        encoded = json.dumps(analysis, sort_keys=True, separators=(",", ":"))
        existing = self.db.execute(
            "SELECT record_id,analysis_json,tick FROM structural_commits WHERE commit_key=?",
            (commit_key,),
        ).fetchone()
        if existing is not None:
            if existing != (record_id, encoded, tick):
                raise ValueError("structural commit idempotency conflict")
            return
        self.db.execute(
            "INSERT INTO structural_commits VALUES(?,?,?,?,?,?,?)",
            (
                commit_key,
                record_id,
                analysis["source_text_sha256"],
                analysis["compiler_version"],
                analysis["analysis_digest"],
                encoded,
                tick,
            ),
        )

    def structural_history(self, active_commit_keys=None):
        rows = self.db.execute(
            "SELECT commit_key,record_id,analysis_json,tick "
            "FROM structural_commits ORDER BY tick, rowid"
        ).fetchall()
        allowed = None if active_commit_keys is None else set(active_commit_keys)
        result = []
        for commit_key, record_id, encoded, tick in rows:
            if allowed is not None and commit_key not in allowed:
                continue
            analysis = json.loads(encoded)
            semantic_profile = analysis.get("semantic_profile")
            if semantic_profile is None and "semantic_vector" in analysis:
                # Read-only compatibility for the unactivated WP-30 single-vector
                # prototype. New commits always use the multi-vector profile.
                semantic_profile = {
                    "chunks": [{"index": 0, "values": analysis["semantic_vector"]["values"]}]
                }
            result.append({
                "commit_key": commit_key,
                "record_id": record_id,
                "tick": tick,
                "candidate": analysis["candidate"],
                "semantic_profile": semantic_profile,
                "static_load": analysis["static_load"],
                "load_signature": analysis["load_signature"],
                "analysis_digest": analysis["analysis_digest"],
            })
        return result

    def structural_analysis(self, commit_key):
        row = self.db.execute(
            "SELECT analysis_json FROM structural_commits WHERE commit_key=?", (commit_key,)
        ).fetchone()
        return None if row is None else json.loads(row[0])

    def retain_retrieval_outcomes(
        self, commit_key, admitted_anchor_ids, retrieval_trace, committed_text,
        conflict_dismissed, tick, structural_similarities=None,
    ):
        """Record packet/response observations inside the caller's transaction."""
        supplied_ids = [str(value) for value in admitted_anchor_ids]
        ordered_ids = list(dict.fromkeys(supplied_ids))
        if len(ordered_ids) != len(supplied_ids):
            raise ValueError("admitted anchor ids must be unique and ordered")
        trace_by_id = {}
        for row in retrieval_trace or ():
            if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                raise ValueError("retrieval trace rows require string ids")
            record_id = row["id"]
            if record_id in trace_by_id:
                raise ValueError("retrieval trace contains duplicate anchor ids")
            trace_by_id[record_id] = row
        if trace_by_id:
            missing = [record_id for record_id in ordered_ids if record_id not in trace_by_id]
            if missing:
                raise ValueError(f"admitted anchors absent from retrieval trace: {missing}")
        similarities = structural_similarities or {}
        for rank, record_id in enumerate(ordered_ids, 1):
            original = self.get(record_id)
            if original is None:
                raise ValueError(f"outcome anchor has no durable twin: {record_id}")
            trace = trace_by_id.get(record_id, {})
            rrf_score = _optional_finite_float(trace.get("rrf_score"), "rrf_score")
            lexical_rank = _optional_positive_int(trace.get("lexical_rank"), "lexical_rank")
            structural_rank = _optional_positive_int(
                trace.get("structural_rank"), "structural_rank"
            )
            matched_branch_id = trace.get("matched_branch_id")
            if matched_branch_id is not None and not isinstance(matched_branch_id, str):
                raise ValueError("matched_branch_id must be a string or null")
            structural_similarity = _optional_finite_float(
                similarities.get(record_id), "structural_similarity"
            )
            values = (
                commit_key, record_id, rank, rrf_score, lexical_rank,
                structural_rank, matched_branch_id,
                longest_common_substring_chars(original["content"], committed_text),
                structural_similarity, int(conflict_dismissed), tick,
            )
            existing = self.db.execute(
                "SELECT commit_key,record_id,rank,rrf_score,lexical_rank,"
                "structural_rank,matched_branch_id,verbatim_overlap_chars,"
                "structural_similarity,conflict_dismissed,tick "
                "FROM retrieval_outcomes WHERE commit_key=? AND record_id=?",
                (commit_key, record_id),
            ).fetchone()
            if existing is not None:
                if existing != values:
                    raise ValueError("retrieval outcome idempotency conflict")
                continue
            self.db.execute(
                "INSERT INTO retrieval_outcomes VALUES(?,?,?,?,?,?,?,?,?,?,?)", values
            )

    def retrieval_outcomes(self, commit_key=None):
        query = (
            "SELECT commit_key,record_id,rank,rrf_score,lexical_rank,"
            "structural_rank,matched_branch_id,verbatim_overlap_chars,"
            "structural_similarity,conflict_dismissed,tick FROM retrieval_outcomes"
        )
        parameters = ()
        if commit_key is not None:
            query += " WHERE commit_key=?"
            parameters = (commit_key,)
        query += " ORDER BY commit_key,rank,record_id"
        names = (
            "commit_key", "record_id", "rank", "rrf_score", "lexical_rank",
            "structural_rank", "matched_branch_id", "verbatim_overlap_chars",
            "structural_similarity", "conflict_dismissed", "tick",
        )
        return [dict(zip(names, row)) for row in self.db.execute(query, parameters)]

    def document(self, document_id, *, include_chunks=True):
        row = self.db.execute(
            "SELECT document_id,display_name,content_sha256,content,byte_length,"
            "media_type,chunking_version,embedding_version,ingested_tick,tombstoned_at "
            "FROM documents WHERE document_id=?", (document_id,),
        ).fetchone()
        if row is None:
            return None
        names = (
            "document_id", "display_name", "content_sha256", "content", "byte_length",
            "media_type", "chunking_version", "embedding_version", "ingested_tick",
            "tombstoned_at",
        )
        result = dict(zip(names, row))
        if include_chunks:
            result["chunks"] = self.document_chunks(document_id=document_id)
        return result

    def documents(self, *, include_withdrawn=False):
        query = (
            "SELECT document_id,display_name,content_sha256,byte_length,media_type,"
            "chunking_version,embedding_version,ingested_tick,tombstoned_at "
            "FROM documents"
        )
        if not include_withdrawn:
            query += " WHERE tombstoned_at IS NULL"
        query += " ORDER BY ingested_tick,document_id"
        names = (
            "document_id", "display_name", "content_sha256", "byte_length",
            "media_type", "chunking_version", "embedding_version", "ingested_tick",
            "tombstoned_at",
        )
        return [dict(zip(names, row)) for row in self.db.execute(query)]

    def retain_document(self, document, chunks):
        existing = self.document(document["document_id"])
        if existing is not None:
            comparable = {key: existing[key] for key in document}
            if comparable != document:
                raise ValueError("document idempotency conflict")
            return existing
        self.db.execute(
            "INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)",
            tuple(document[key] for key in (
                "document_id", "display_name", "content_sha256", "content",
                "byte_length", "media_type", "chunking_version", "embedding_version",
                "ingested_tick", "tombstoned_at",
            )),
        )
        for chunk in chunks:
            self.db.execute(
                "INSERT INTO document_chunks VALUES(?,?,?,?,?,?,?,?)",
                (
                    document["document_id"], chunk["index"], chunk["start"], chunk["end"],
                    chunk["text_sha256"], chunk["passage_vector"], None, None,
                ),
            )
        return self.document(document["document_id"])

    def withdraw_document(self, document_id, tombstoned_at):
        existing = self.document(document_id)
        if existing is None:
            raise ValueError("document does not exist")
        if existing["tombstoned_at"] is None:
            self.db.execute(
                "UPDATE documents SET tombstoned_at=? WHERE document_id=?",
                (tombstoned_at, document_id),
            )
        return self.document(document_id)

    def document_chunks(self, *, document_id=None, active_only=False):
        query = (
            "SELECT c.document_id,c.chunk_index,c.start,c.end,c.text_sha256,"
            "c.passage_vector,c.analysis_digest,c.load_signature_json,d.display_name,"
            "d.content,d.tombstoned_at FROM document_chunks c "
            "JOIN documents d ON d.document_id=c.document_id"
        )
        clauses = []
        parameters = []
        if document_id is not None:
            clauses.append("c.document_id=?")
            parameters.append(document_id)
        if active_only:
            clauses.append("d.tombstoned_at IS NULL")
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY c.document_id,c.chunk_index"
        result = []
        for row in self.db.execute(query, parameters):
            item = {
                "document_id": row[0], "chunk_index": row[1],
                "start": row[2], "end": row[3], "text_sha256": row[4],
                "passage_vector": row[5], "analysis_digest": row[6],
                "load_signature_json": row[7], "display_name": row[8],
                "text": row[9][row[2]:row[3]], "tombstoned_at": row[10],
            }
            result.append(item)
        return result


def _optional_positive_int(value, name):
    if value is None:
        return None
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer or null")
    return value


def _optional_finite_float(value, name):
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite or null")
    return float(value)


def longest_common_substring_chars(left, right):
    """Exact Unicode-character LCS substring length in linear time."""
    states = [{"length": 0, "link": -1, "next": {}}]
    last = 0
    for character in left:
        current = len(states)
        states.append({"length": states[last]["length"] + 1, "link": 0, "next": {}})
        parent = last
        while parent >= 0 and character not in states[parent]["next"]:
            states[parent]["next"][character] = current
            parent = states[parent]["link"]
        if parent >= 0:
            target = states[parent]["next"][character]
            if states[parent]["length"] + 1 == states[target]["length"]:
                states[current]["link"] = target
            else:
                clone = len(states)
                states.append({
                    "length": states[parent]["length"] + 1,
                    "link": states[target]["link"],
                    "next": dict(states[target]["next"]),
                })
                while parent >= 0 and states[parent]["next"].get(character) == target:
                    states[parent]["next"][character] = clone
                    parent = states[parent]["link"]
                states[target]["link"] = clone
                states[current]["link"] = clone
        last = current
    state = length = best = 0
    for character in right:
        while state and character not in states[state]["next"]:
            state = states[state]["link"]
            length = min(length, states[state]["length"])
        target = states[state]["next"].get(character)
        if target is None:
            state = length = 0
            continue
        state = target
        length += 1
        best = max(best, length)
    return best
