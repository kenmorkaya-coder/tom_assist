"""Project-local permanent SQLite shelf and atomic runtime commit journal."""
import hashlib
import json
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
