CREATE TABLE IF NOT EXISTS experience_acceptances (
  evaluation_id TEXT PRIMARY KEY REFERENCES response_evaluations(id),
  project_id TEXT NOT NULL REFERENCES projects(id),
  response_turn_id TEXT NOT NULL UNIQUE REFERENCES turns(id),
  sent_turn_id TEXT NOT NULL UNIQUE REFERENCES turns(id),
  accepted_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_experience_acceptances_project
  ON experience_acceptances(project_id, accepted_at);
