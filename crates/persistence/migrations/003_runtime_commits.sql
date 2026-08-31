CREATE TABLE IF NOT EXISTS sent_contexts (
    project_id TEXT NOT NULL, packet_digest TEXT NOT NULL,
    turn_id TEXT NOT NULL REFERENCES turns(id),
    PRIMARY KEY(project_id, packet_digest)
);
CREATE TABLE IF NOT EXISTS runtime_commit_receipts (
    sent_turn_id TEXT PRIMARY KEY REFERENCES turns(id),
    evaluation_id TEXT NOT NULL, result_json TEXT NOT NULL
);
