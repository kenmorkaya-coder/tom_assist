CREATE TABLE IF NOT EXISTS context_manifests(context_id TEXT PRIMARY KEY, activated_branch_ids_json TEXT NOT NULL, admitted_anchor_ids_json TEXT NOT NULL, candidate_trace_json TEXT NOT NULL);
