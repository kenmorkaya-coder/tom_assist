CREATE TABLE IF NOT EXISTS chat_conversations(
 id TEXT PRIMARY KEY REFERENCES provider_sessions(id), project_id TEXT NOT NULL REFERENCES projects(id),
 title TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS provider_exchanges(
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
 session_id TEXT NOT NULL REFERENCES provider_sessions(id), packet_digest TEXT NOT NULL,
 user_draft TEXT NOT NULL, prompt TEXT NOT NULL, prompt_hash TEXT NOT NULL,
 ordinal INTEGER NOT NULL, status TEXT NOT NULL, response_text TEXT,
 error_code TEXT, accepted_review INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS provider_one_inflight ON provider_exchanges(project_id)
 WHERE status IN ('sending','evaluation_pending');
