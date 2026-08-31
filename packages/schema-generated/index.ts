/* Generated from crates/protocol/schemas. Do not edit directly. */

/**
 * Root schema used to generate the committed TypeScript contract.
 */
export type TomAssistProtocol =
  | Envelope
  | ProviderCapabilities
  | TomCapabilities
  | StateObject
  | StateEdge
  | ContinuityPacket
  | StateMutationCandidate
  | Intervention
  | ProtocolError;
export type Method =
  | "capabilities.get"
  | "project.create"
  | "project.list"
  | "project.get"
  | "project.update"
  | "project.archive"
  | "workstream.create"
  | "workstream.get"
  | "workstream.update"
  | "workstream.archive"
  | "session.attach"
  | "session.fork"
  | "session.detach"
  | "session.reconcile"
  | "turn.ingest"
  | "turn.prepare"
  | "turn.sent"
  | "response.evaluate"
  | "packet.get"
  | "packet.verify"
  | "state.candidate.create"
  | "state.commit"
  | "state.supersede"
  | "state.reopen"
  | "intervention.resolve"
  | "model.bias.preview"
  | "model.bias.apply"
  | "snapshot.create"
  | "snapshot.verify"
  | "snapshot.restore"
  | "project.export"
  | "project.import"
  | "diagnostics.run";

export interface Envelope {
  protocol: "tom-assist/1.0";
  request_id: string;
  idempotency_key: string;
  method: Method;
  actor: {
    type: "extension" | "desktop" | "native_host" | "service" | "user";
    instance_id: string;
  };
  project_id?: string;
  base_state_version?: number;
  payload: {
    [k: string]: unknown;
  };
  sent_at: string;
}
export interface ProviderCapabilities {
  provider_surface: string;
  visible_prompt_injection: boolean;
  response_capture: boolean;
  hidden_context_visibility: boolean;
  model_internal_bias: "none" | "moe_expert_logits";
  max_context_tokens?: number;
  exact_tokenizer?: string;
  supports_system_field?: boolean;
}
export interface TomCapabilities {
  /**
   * @minItems 2
   * @maxItems 2
   */
  preview_channels?: [unknown, unknown];
  runtime_version: string;
  state_format_version: "sicd-engine-save/1";
  supports_load_ingest: boolean;
  supports_branch_activation: boolean;
  supports_candidate_ranking: boolean;
  supports_state_snapshot: boolean;
  supports_commit: boolean;
  supports_conflict_check: boolean;
  supports_trajectory_digest: boolean;
  supports_readonly_ranking: true;
  supports_checkpoint_restore: true;
  supports_nonmutating_load_preview: false;
  engine_parity_profile: string;
  engine_parity_verified_at_commit: string;
  seed_profile: "msr_8d_native_10k";
  seed_artifact_sha256: string;
  seed_tick: 4707;
  seed_branch_count: 10000;
  mechanics_profile: "msr_8d_native_10k.env";
  mechanics_profile_sha256: string;
  mechanics_parameters: {
    [k: string]: string;
  };
  kappa_decay_source: "profile_env_reader_wp18_effective_0.03";
}
export interface StateObject {
  id: string;
  project_id: string;
  workstream_id?: string;
  type:
    | "OBJECTIVE"
    | "CONCEPT"
    | "DECISION"
    | "CONSTRAINT"
    | "REJECTED_PATH"
    | "COMPLETED_WORK"
    | "UNRESOLVED_DEPENDENCY"
    | "EVIDENCE"
    | "ASSUMPTION"
    | "SUPERSESSION"
    | "WORKSTREAM";
  title: string;
  canonical_text: string;
  status: "proposed" | "active" | "satisfied" | "rejected" | "superseded" | "archived";
  authority: "user" | "tom_verified" | "imported" | "provider_candidate" | "local_model_candidate";
  confidence: number;
  binding_strength?: "hard" | "soft" | "advisory";
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
}
export interface StateEdge {
  id: string;
  project_id: string;
  from_state_id: string;
  edge_type:
    | "supports"
    | "contradicts"
    | "depends_on"
    | "resolves"
    | "supersedes"
    | "derived_from"
    | "scoped_to"
    | "reopens"
    | "defines"
    | "refines";
  to_state_id: string;
  created_event_id: string;
}
export interface ContinuityPacket {
  activated_branch_ids?: string[];
  packet_id: string;
  packet_digest: string;
  project_id: string;
  workstream_id: string;
  provider_session_id: string;
  project_state_version: number;
  project_state_digest: string;
  tom_checkpoint_digest: string;
  draft_hash: string;
  policy_version: string;
  renderer_version: "authoritative-state/1.0";
  provider_capabilities: ProviderCapabilities;
  tom_activation_id: string;
  sections: {
    type: string;
    items: {
      state_id: string;
      text: string;
      authority: string;
      structural_score: number;
      semantic_score: number;
      reason_selected: string;
    }[];
  }[];
  retrieved_anchor_ids: string[];
  excluded: {
    id: string;
    reason: string;
  }[];
  estimated_tokens: number;
  warnings: string[];
}
export interface StateMutationCandidate {
  candidate_id: string;
  project_id: string;
  source_turn_ids: string[];
  proposed_by: "user" | "tom_verified" | "imported" | "provider_candidate" | "local_model_candidate";
  operation: "CREATE" | "UPDATE" | "SUPERSEDE" | "REOPEN";
  object: {
    [k: string]: unknown;
  };
  tom_check: {
    result: "compatible" | "review" | "conflict";
    conflicts: string[];
    requires_user_confirmation: true;
  };
}
export interface Intervention {
  id: string;
  project_id: string;
  turn_id: string;
  code:
    | "CONTRADICTION"
    | "SUPERSEDED_PATH_REVIVED"
    | "CONSTRAINT_DROPPED"
    | "OBJECTIVE_DRIFT"
    | "COMPLETED_WORK_REPROPOSED"
    | "UNSUPPORTED_STATE_CHANGE"
    | "STALE_EVIDENCE_USED"
    | "WRONG_PROJECT_CONTEXT"
    | "SUPERSESSION_WITHOUT_REASON"
    | "UNRESOLVED_DEPENDENCY_IGNORED"
    | "CONCEPT_DRIFT";
  severity: "info" | "warning" | "blocking_commit";
  confidence: number;
  summary: string;
  response_excerpt: string;
  conflicting_state_ids: string[];
  evidence_turn_ids: string[];
  suggested_context_patch?: string;
  status: "open" | "accepted" | "dismissed" | "false_positive" | "resolved";
  policy_version: string;
}
export interface ProtocolError {
  code:
    | "PROTOCOL_MISMATCH"
    | "SERVICE_UNAVAILABLE"
    | "PROJECT_NOT_FOUND"
    | "STATE_VERSION_CONFLICT"
    | "TOM_RUNTIME_UNAVAILABLE"
    | "CAPTURE_INCOMPLETE"
    | "VALIDATION_FAILED"
    | "PERMISSION_DENIED"
    | "DATABASE_INTEGRITY_ERROR"
    | "ADAPTER_UNSUPPORTED";
  message: string;
  retryable: boolean;
  remediation?: string;
  correlation_id: string;
}
