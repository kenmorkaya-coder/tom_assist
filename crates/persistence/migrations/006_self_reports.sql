CREATE TABLE IF NOT EXISTS provider_self_reports(
 exchange_id TEXT PRIMARY KEY REFERENCES provider_exchanges(id),
 project_id TEXT NOT NULL REFERENCES projects(id),
 status TEXT NOT NULL, report_json TEXT NOT NULL
);
