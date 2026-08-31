CREATE TABLE IF NOT EXISTS recovery_imports (
    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
    archive_digest TEXT NOT NULL
);
