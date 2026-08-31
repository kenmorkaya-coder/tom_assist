use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Actor {
    #[serde(rename = "type")]
    pub actor_type: ActorType,
    pub instance_id: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ActorType {
    Extension,
    Desktop,
    NativeHost,
    Service,
    User,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Envelope {
    pub protocol: String,
    pub request_id: String,
    pub idempotency_key: String,
    pub method: Method,
    pub actor: Actor,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub project_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub base_state_version: Option<u64>,
    pub payload: Value,
    pub sent_at: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Method {
    #[serde(rename = "capabilities.get")]
    CapabilitiesGet,
    #[serde(rename = "project.create")]
    ProjectCreate,
    #[serde(rename = "project.list")]
    ProjectList,
    #[serde(rename = "project.get")]
    ProjectGet,
    #[serde(rename = "project.update")]
    ProjectUpdate,
    #[serde(rename = "project.archive")]
    ProjectArchive,
    #[serde(rename = "workstream.create")]
    WorkstreamCreate,
    #[serde(rename = "workstream.get")]
    WorkstreamGet,
    #[serde(rename = "workstream.update")]
    WorkstreamUpdate,
    #[serde(rename = "workstream.archive")]
    WorkstreamArchive,
    #[serde(rename = "session.attach")]
    SessionAttach,
    #[serde(rename = "session.fork")]
    SessionFork,
    #[serde(rename = "session.detach")]
    SessionDetach,
    #[serde(rename = "session.reconcile")]
    SessionReconcile,
    #[serde(rename = "turn.ingest")]
    TurnIngest,
    #[serde(rename = "turn.prepare")]
    TurnPrepare,
    #[serde(rename = "turn.sent")]
    TurnSent,
    #[serde(rename = "response.evaluate")]
    ResponseEvaluate,
    #[serde(rename = "packet.get")]
    PacketGet,
    #[serde(rename = "packet.verify")]
    PacketVerify,
    #[serde(rename = "state.candidate.create")]
    StateCandidateCreate,
    #[serde(rename = "state.commit")]
    StateCommit,
    #[serde(rename = "state.supersede")]
    StateSupersede,
    #[serde(rename = "state.reopen")]
    StateReopen,
    #[serde(rename = "intervention.resolve")]
    InterventionResolve,
    #[serde(rename = "model.bias.preview")]
    ModelBiasPreview,
    #[serde(rename = "model.bias.apply")]
    ModelBiasApply,
    #[serde(rename = "snapshot.create")]
    SnapshotCreate,
    #[serde(rename = "snapshot.verify")]
    SnapshotVerify,
    #[serde(rename = "snapshot.restore")]
    SnapshotRestore,
    #[serde(rename = "project.export")]
    ProjectExport,
    #[serde(rename = "project.import")]
    ProjectImport,
    #[serde(rename = "diagnostics.run")]
    DiagnosticsRun,
    #[serde(rename = "provider.status")]
    ProviderStatus,
    #[serde(rename = "conversation.list")]
    ConversationList,
    #[serde(rename = "conversation.create")]
    ConversationCreate,
    #[serde(rename = "conversation.get")]
    ConversationGet,
    #[serde(rename = "conversation.prepare")]
    ConversationPrepare,
    #[serde(rename = "conversation.send")]
    ConversationSend,
    #[serde(rename = "conversation.evaluate")]
    ConversationEvaluate,
    #[serde(rename = "conversation.self_report.prepare")]
    SelfReportPrepare,
    #[serde(rename = "conversation.self_report.send")]
    SelfReportSend,
    #[serde(rename = "conversation.self_report.label")]
    SelfReportLabel,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProviderCapabilities {
    pub provider_surface: String,
    pub visible_prompt_injection: bool,
    pub response_capture: bool,
    pub hidden_context_visibility: bool,
    pub model_internal_bias: ModelInternalBias,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_context_tokens: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub exact_tokenizer: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub supports_system_field: Option<bool>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ModelInternalBias {
    None,
    MoeExpertLogits,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TomCapabilities {
    pub runtime_version: String,
    pub state_format_version: String,
    pub supports_load_ingest: bool,
    pub supports_branch_activation: bool,
    pub supports_candidate_ranking: bool,
    pub supports_state_snapshot: bool,
    pub supports_commit: bool,
    pub supports_conflict_check: bool,
    pub supports_trajectory_digest: bool,
    pub supports_readonly_ranking: bool,
    pub supports_checkpoint_restore: bool,
    pub supports_nonmutating_load_preview: bool,
    pub engine_parity_profile: String,
    pub engine_parity_verified_at_commit: String,
    pub seed_profile: String,
    pub seed_artifact_sha256: String,
    pub seed_tick: u64,
    pub seed_branch_count: u64,
    pub mechanics_profile: String,
    pub mechanics_profile_sha256: String,
    pub mechanics_parameters: BTreeMap<String, String>,
    pub kappa_decay_source: String,
    pub commit_dynamics: Vec<String>,
    pub front_row_capacity: u64,
    pub teach_on_conflict: bool,
    pub preview_channels: Vec<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum StateType {
    Objective,
    Concept,
    Decision,
    Constraint,
    RejectedPath,
    CompletedWork,
    UnresolvedDependency,
    Evidence,
    Assumption,
    Supersession,
    Workstream,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StateStatus {
    Proposed,
    Active,
    Satisfied,
    Rejected,
    Superseded,
    Archived,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Authority {
    User,
    TomVerified,
    Imported,
    ProviderCandidate,
    LocalModelCandidate,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BindingStrength {
    Hard,
    Soft,
    Advisory,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StateObject {
    pub id: String,
    pub project_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub workstream_id: Option<String>,
    #[serde(rename = "type")]
    pub object_type: StateType,
    pub title: String,
    pub canonical_text: String,
    pub status: StateStatus,
    pub authority: Authority,
    pub confidence: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub binding_strength: Option<BindingStrength>,
    pub source_turn_ids: Vec<String>,
    pub evidence_ids: Vec<String>,
    pub branch_refs: Vec<String>,
    pub created_at: String,
    pub updated_at: String,
    pub effective_at: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub supersedes_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reconsideration_condition: Option<String>,
    pub content_hash: String,
    pub state_version: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EdgeType {
    Supports,
    Contradicts,
    DependsOn,
    Resolves,
    Supersedes,
    DerivedFrom,
    ScopedTo,
    Reopens,
    Defines,
    Refines,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StateEdge {
    pub id: String,
    pub project_id: String,
    pub from_state_id: String,
    pub edge_type: EdgeType,
    pub to_state_id: String,
    pub created_event_id: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PacketItem {
    pub state_id: String,
    pub text: String,
    pub authority: String,
    pub structural_score: f64,
    pub semantic_score: f64,
    pub reason_selected: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PacketSection {
    #[serde(rename = "type")]
    pub section_type: String,
    pub items: Vec<PacketItem>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExcludedItem {
    pub id: String,
    pub reason: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ContinuityPacket {
    #[serde(default)]
    pub activated_branch_ids: Vec<String>,
    pub packet_id: String,
    pub packet_digest: String,
    pub project_id: String,
    pub workstream_id: String,
    pub provider_session_id: String,
    pub project_state_version: u64,
    pub project_state_digest: String,
    pub tom_checkpoint_digest: String,
    pub draft_hash: String,
    pub policy_version: String,
    pub renderer_version: String,
    pub provider_capabilities: ProviderCapabilities,
    pub tom_activation_id: String,
    pub sections: Vec<PacketSection>,
    pub retrieved_anchor_ids: Vec<String>,
    pub excluded: Vec<ExcludedItem>,
    pub estimated_tokens: u64,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TomCheck {
    pub result: String,
    pub conflicts: Vec<String>,
    pub requires_user_confirmation: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StateMutationCandidate {
    pub candidate_id: String,
    pub project_id: String,
    pub source_turn_ids: Vec<String>,
    pub proposed_by: Authority,
    pub operation: MutationOperation,
    pub object: Value,
    pub tom_check: TomCheck,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum MutationOperation {
    Create,
    Update,
    Supersede,
    Reopen,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum InterventionCode {
    Contradiction,
    SupersededPathRevived,
    ConstraintDropped,
    ObjectiveDrift,
    CompletedWorkReproposed,
    UnsupportedStateChange,
    StaleEvidenceUsed,
    WrongProjectContext,
    SupersessionWithoutReason,
    UnresolvedDependencyIgnored,
    ConceptDrift,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InterventionSeverity {
    Info,
    Warning,
    BlockingCommit,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InterventionStatus {
    Open,
    Accepted,
    Dismissed,
    FalsePositive,
    Resolved,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Intervention {
    pub id: String,
    pub project_id: String,
    pub turn_id: String,
    pub code: InterventionCode,
    pub severity: InterventionSeverity,
    pub confidence: f64,
    pub summary: String,
    pub response_excerpt: String,
    pub conflicting_state_ids: Vec<String>,
    pub evidence_turn_ids: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub suggested_context_patch: Option<String>,
    pub status: InterventionStatus,
    pub policy_version: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ErrorCode {
    ProtocolMismatch,
    ServiceUnavailable,
    ProjectNotFound,
    StateVersionConflict,
    TomRuntimeUnavailable,
    CaptureIncomplete,
    ValidationFailed,
    PermissionDenied,
    DatabaseIntegrityError,
    AdapterUnsupported,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProtocolError {
    pub code: ErrorCode,
    pub message: String,
    pub retryable: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub remediation: Option<String>,
    pub correlation_id: String,
}
