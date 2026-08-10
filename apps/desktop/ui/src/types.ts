export interface Project {
  id: string;
  name: string;
  status: string;
  state_version: number;
  state_digest: string;
  retention_profile: string;
  policy_profile: string;
  created_at: string;
  updated_at: string;
}

export interface StateObject {
  id: string;
  project_id: string;
  workstream_id?: string;
  type: string;
  title: string;
  canonical_text: string;
  status: string;
  authority: string;
  confidence: number;
  binding_strength?: string;
  source_turn_ids: string[];
  evidence_ids: string[];
  branch_refs: string[];
  created_at: string;
  updated_at: string;
  effective_at: string;
  supersedes_id?: string;
  reconsideration_condition?: string;
  content_hash: string;
  state_version: number;
  last_selection_reason?: string;
}

export interface CanonicalState {
  project_id: string;
  state_version: number;
  objects: StateObject[];
  edges: unknown[];
}

export interface AuditEvent {
  id: string;
  event_type: string;
  actor_type: string;
  actor_id: string;
  base_state_version: number;
  prior_digest: string;
  resulting_digest: string;
  created_at: string;
}

export interface InterventionRecord {
  id: string;
  code: string;
  severity: string;
  confidence: number;
  summary: string;
  status: string;
  conflicting_state_ids: string[];
}
