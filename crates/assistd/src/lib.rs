//! Snapshot-bound PREPARE_TURN / EVALUATE_TURN orchestration.
pub mod chat_capture;
pub mod conversations;
pub mod experience;
pub mod provider;
pub mod recovery;

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::HashMap;
use std::fmt::{Display, Formatter};
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::os::unix::fs::PermissionsExt;
use std::os::unix::net::{UnixListener, UnixStream};
use std::path::Path;
use std::sync::{Arc, Mutex};
use tom_assist_context_admission::{
    AdmissionRequest, Candidate, CandidatePool, ContextAdmissionEngine, IntegrityStatus,
    ScoreComponents,
};
use tom_assist_governance::{
    CandidateChannel, EvaluationRequest, EvaluationState as GovernanceEvaluationState,
    GatewayVerifier, GovernanceEngine, GovernanceError, LedgerRule, extract_candidates,
};
use tom_assist_persistence::{
    ContextRunRecord, ResponseEvaluationRecord, Store, StoreError, TurnRecord,
};
use tom_assist_protocol::{
    ContinuityPacket, Envelope, ExcludedItem, InterventionCode, Method, PacketDigestInput,
    PacketSection, ProviderCapabilities, StateMutationCandidate, StateObject, canonical_sha256,
    packet_digest,
};
use tom_assist_tom_adapter::GatewayClient;

pub const SERVICE_VERSION: &str = env!("CARGO_PKG_VERSION");
pub const SERVICE_PROTOCOL_VERSION: &str = tom_assist_protocol::PROTOCOL_VERSION;
pub const POLICY_VERSION: &str = "context-policy/1.1";
pub const RENDERER_VERSION: &str = "authoritative-state/1.0";

#[derive(Debug)]
pub enum ServiceError {
    Store(StoreError),
    Json(serde_json::Error),
    Io(std::io::Error),
    ProtocolMismatch { expected: String, actual: String },
    UnsupportedMethod(String),
    MissingProject,
    UnknownPacket,
    PacketMismatch,
    StalePacket { prepared: u64, current: u64 },
    CaptureIncomplete,
    Invalid(String),
}

impl Display for ServiceError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Store(error) => write!(f, "store error: {error}"),
            Self::Json(error) => write!(f, "JSON error: {error}"),
            Self::Io(error) => write!(f, "I/O error: {error}"),
            Self::ProtocolMismatch { expected, actual } => {
                write!(f, "protocol mismatch: expected {expected}, got {actual}")
            }
            Self::UnsupportedMethod(method) => write!(f, "unsupported method: {method}"),
            Self::MissingProject => write!(f, "project_id is required"),
            Self::UnknownPacket => write!(f, "packet digest is not a prepared local packet"),
            Self::PacketMismatch => write!(f, "packet lineage does not match the request"),
            Self::StalePacket { prepared, current } => write!(
                f,
                "STATE_VERSION_CONFLICT: packet prepared at {prepared}, current state is {current}; rebuild required"
            ),
            Self::CaptureIncomplete => write!(f, "assistant capture is incomplete"),
            Self::Invalid(message) => write!(f, "invalid request: {message}"),
        }
    }
}

impl std::error::Error for ServiceError {}
impl From<StoreError> for ServiceError {
    fn from(value: StoreError) -> Self {
        Self::Store(value)
    }
}
impl From<serde_json::Error> for ServiceError {
    fn from(value: serde_json::Error) -> Self {
        Self::Json(value)
    }
}
impl From<std::io::Error> for ServiceError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value)
    }
}
pub type Result<T> = std::result::Result<T, ServiceError>;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrepareTurnRequest {
    #[serde(default)]
    pub activated_branch_ids: Vec<String>,
    #[serde(default)]
    pub candidate_trace: Value,
    pub project_id: String,
    pub workstream_id: String,
    pub provider_session_id: String,
    pub user_draft: String,
    pub tom_checkpoint_digest: String,
    pub tom_activation_id: String,
    pub provider_capabilities: ProviderCapabilities,
    #[serde(default)]
    pub sections: Vec<PacketSection>,
    #[serde(default)]
    pub retrieved_anchor_ids: Vec<String>,
    #[serde(default)]
    pub excluded: Vec<ExcludedItem>,
    #[serde(default)]
    pub packet_text: String,
    #[serde(default)]
    pub warnings: Vec<String>,
    #[serde(default)]
    pub latency_ms: u64,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PreparedTurn {
    pub packet: ContinuityPacket,
    pub packet_text: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SendTurnRequest {
    pub project_id: String,
    pub packet_digest: String,
    pub user_draft: String,
    pub turn_id: String,
    pub ordinal: u64,
    pub idempotency_key: String,
    pub captured_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SentTurn {
    pub turn_id: String,
    pub packet_digest: String,
    pub state_version: u64,
    pub duplicate: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvaluateTurnRequest {
    pub project_id: String,
    pub packet_digest: String,
    pub response_turn_id: String,
    pub response_text: String,
    pub ordinal: u64,
    pub complete: bool,
    pub created_at: String,
    #[serde(default)]
    pub latency_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateCandidateRequest {
    pub kind: String,
    pub text: String,
    #[serde(default)]
    pub authority: Option<String>,
    #[serde(default)]
    pub requires_user_confirmation: Option<bool>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EvaluationState {
    Pass,
    Review,
    Conflict,
    Incomplete,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvaluationResult {
    pub evaluation_id: String,
    pub response_turn_id: String,
    pub packet_digest: String,
    pub state_version: u64,
    pub result: EvaluationState,
    pub intervention_ids: Vec<String>,
    pub stale: bool,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub diagnostics: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WireResponse {
    pub protocol: String,
    pub request_id: String,
    pub ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub payload: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<WireError>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WireError {
    pub code: String,
    pub message: String,
    pub retryable: bool,
}

/// Process-local service core. SQLite remains the cross-process CAS authority;
/// these locks ensure one logical writer enters a project transaction at a time.
pub struct AssistService {
    gateway: Option<GatewayClient>,
    store: Mutex<Store>,
    project_writers: Mutex<HashMap<String, Arc<Mutex<()>>>>,
    governance_verifier: Arc<dyn GatewayVerifier>,
    provider: Arc<dyn provider::ProviderAdapter>,
    provider_inflight: Mutex<std::collections::HashSet<String>>,
}

impl AssistService {
    pub fn new(store: Store) -> Self {
        Self::with_governance_verifier(store, NativeOnlyVerifier)
    }

    pub fn with_governance_verifier<V>(store: Store, verifier: V) -> Self
    where
        V: GatewayVerifier + 'static,
    {
        Self {
            gateway: None,
            store: Mutex::new(store),
            project_writers: Mutex::new(HashMap::new()),
            governance_verifier: Arc::new(verifier),
            provider: Arc::new(provider::DisconnectedProvider),
            provider_inflight: Mutex::new(std::collections::HashSet::new()),
        }
    }

    pub fn with_gateway(store: Store, gateway: GatewayClient) -> Self {
        let mut service = Self::with_governance_verifier(store, gateway.clone());
        service.gateway = Some(gateway);
        service.provider = Arc::new(provider::RuntimeOAuthAdapter(
            service.gateway.as_ref().unwrap().clone(),
        ));
        service
    }

    fn project_lock(&self, project_id: &str) -> Arc<Mutex<()>> {
        self.project_writers
            .lock()
            .expect("project lock map poisoned")
            .entry(project_id.to_owned())
            .or_insert_with(|| Arc::new(Mutex::new(())))
            .clone()
    }

    pub fn prepare_turn(&self, mut request: PrepareTurnRequest) -> Result<PreparedTurn> {
        let project_lock = self.project_lock(&request.project_id);
        let _writer = project_lock.lock().expect("project lock poisoned");
        let store = self.store.lock().expect("store poisoned");
        let project = store
            .project(&request.project_id)?
            .ok_or_else(|| StoreError::ProjectNotFound(request.project_id.clone()))?;
        let state = store.current_state(&request.project_id)?;
        if let Some(gateway) = &self.gateway {
            // Production owns projection/admission; page-provided manifests are not trusted.
            let preview = gateway
                .preview_rank(&request.project_id, &request.user_draft, 10, 2000)
                .map_err(|error| {
                    ServiceError::Invalid(format!("TOM_RUNTIME_UNAVAILABLE: {error}"))
                })?;
            let mut candidates: Vec<Candidate> = state
                .objects
                .iter()
                .map(|object| Candidate {
                    id: object.id.clone(),
                    project_id: object.project_id.clone(),
                    workstream_id: object.workstream_id.clone(),
                    pool: CandidatePool::AuthoritativeState,
                    state_type: Some(object.object_type),
                    status: Some(object.status),
                    text: object.canonical_text.clone(),
                    authority: serde_json::to_value(object.authority)
                        .unwrap()
                        .as_str()
                        .unwrap()
                        .into(),
                    binding_hard: object.binding_strength
                        == Some(tom_assist_protocol::BindingStrength::Hard),
                    integrity: IntegrityStatus::Verified,
                    privacy_allowed: true,
                    dependencies: vec![],
                    provenance: None,
                    reconsideration_condition: object.reconsideration_condition.clone(),
                    scores: ScoreComponents {
                        retrieval_rrf: None,
                        semantic_relevance: 0.0,
                        structural_resonance: 0.0,
                        dependency_sequence_relevance: 0.0,
                        authority_strength: 1.0,
                        bounded_recency: 0.0,
                        stale_probability: 0.0,
                        conflict_penalty: 0.0,
                        redundancy_penalty: 0.0,
                    },
                })
                .collect();
            candidates.extend(preview.ranked_anchors.iter().map(|anchor| Candidate {
                id: anchor.id.clone(),
                project_id: request.project_id.clone(),
                workstream_id: Some(request.workstream_id.clone()),
                pool: CandidatePool::RetrievedAnchor,
                state_type: None,
                status: None,
                text: anchor.text.clone(),
                authority: "observation".into(),
                binding_hard: false,
                integrity: IntegrityStatus::Verified,
                privacy_allowed: true,
                dependencies: vec![],
                provenance: Some(anchor.id.clone()),
                reconsideration_condition: None,
                scores: ScoreComponents {
                    retrieval_rrf: Some(anchor.rrf_score),
                    semantic_relevance: anchor.semantic_score,
                    structural_resonance: anchor.structural_resonance,
                    dependency_sequence_relevance: 0.0,
                    authority_strength: 0.0,
                    bounded_recency: 0.0,
                    stale_probability: 0.0,
                    conflict_penalty: 0.0,
                    redundancy_penalty: 0.0,
                },
            }));
            let admitted = ContextAdmissionEngine::default().build(AdmissionRequest {
                project_id: request.project_id.clone(),
                project_name: project.name.clone(),
                workstream_id: request.workstream_id.clone(),
                workstream_name: request.workstream_id.clone(),
                provider_session_id: request.provider_session_id.clone(),
                state_version: state.state_version,
                state_digest: project.state_digest.clone(),
                tom_checkpoint_digest: preview.checkpoint_digest.clone(),
                tom_activation_id: preview.activation_id.clone(),
                activated_branch_ids: preview.activated_branch_ids.clone(),
                user_draft: request.user_draft.clone(),
                provider_capabilities: request.provider_capabilities.clone(),
                candidates,
                budget_tokens: 500,
            })?;
            request.tom_checkpoint_digest = preview.checkpoint_digest;
            request.tom_activation_id = preview.activation_id;
            request.activated_branch_ids = preview.activated_branch_ids;
            request.candidate_trace = json!({"retrieval":preview.candidate_trace,"branches":preview.branch_trace,"admission":admitted.trace});
            request.sections = admitted.packet.sections;
            request.retrieved_anchor_ids = admitted.packet.retrieved_anchor_ids;
            request.excluded = admitted.packet.excluded;
            request.warnings = admitted.packet.warnings;
            request.packet_text = admitted.state_block;
        }
        let draft_hash = canonical_sha256(&request.user_draft)?;
        let mut admitted_item_ids: Vec<&str> = request
            .sections
            .iter()
            .flat_map(|section| section.items.iter().map(|item| item.state_id.as_str()))
            .collect();
        admitted_item_ids.extend(request.retrieved_anchor_ids.iter().map(String::as_str));
        let digest = packet_digest(PacketDigestInput {
            project_id: &request.project_id,
            workstream_id: &request.workstream_id,
            state_version: state.state_version,
            tom_checkpoint_digest: &request.tom_checkpoint_digest,
            admitted_item_ids,
            activated_branch_ids: request
                .activated_branch_ids
                .iter()
                .map(String::as_str)
                .collect(),
            renderer_version: RENDERER_VERSION,
            policy_version: POLICY_VERSION,
            user_draft_hash: &draft_hash,
        })?;
        let packet_id = canonical_sha256(&json!({"kind":"packet","digest":digest}))?;
        let estimated_tokens = request.packet_text.chars().count().div_ceil(4) as u64;
        let packet = ContinuityPacket {
            activated_branch_ids: request.activated_branch_ids.clone(),
            packet_id: packet_id.clone(),
            packet_digest: digest.clone(),
            project_id: request.project_id.clone(),
            workstream_id: request.workstream_id.clone(),
            provider_session_id: request.provider_session_id.clone(),
            project_state_version: state.state_version,
            project_state_digest: project.state_digest,
            tom_checkpoint_digest: request.tom_checkpoint_digest.clone(),
            draft_hash: draft_hash.clone(),
            policy_version: POLICY_VERSION.into(),
            renderer_version: RENDERER_VERSION.into(),
            provider_capabilities: request.provider_capabilities,
            tom_activation_id: request.tom_activation_id.clone(),
            sections: request.sections,
            retrieved_anchor_ids: request.retrieved_anchor_ids,
            excluded: request.excluded,
            estimated_tokens,
            warnings: request.warnings,
        };
        store.record_context_run(&ContextRunRecord {
            activated_branch_ids: request.activated_branch_ids,
            admitted_anchor_ids: packet.retrieved_anchor_ids.clone(),
            candidate_trace_json: serde_json::to_string(&request.candidate_trace)?,
            id: packet_id,
            project_id: request.project_id,
            workstream_id: request.workstream_id,
            provider_session_id: request.provider_session_id,
            draft_hash,
            state_version: state.state_version,
            tom_checkpoint_digest: request.tom_checkpoint_digest,
            activation_id: request.tom_activation_id,
            policy_version: POLICY_VERSION.into(),
            renderer_version: RENDERER_VERSION.into(),
            selected_json: serde_json::to_string(&packet.sections)?,
            excluded_json: serde_json::to_string(&packet.excluded)?,
            packet_text: request.packet_text.clone(),
            packet_digest: digest,
            estimated_tokens,
            latency_ms: request.latency_ms,
            created_at: request.created_at,
        })?;
        Ok(PreparedTurn {
            packet,
            packet_text: request.packet_text,
        })
    }

    pub fn send_turn(&self, request: SendTurnRequest) -> Result<SentTurn> {
        let project_lock = self.project_lock(&request.project_id);
        let _writer = project_lock.lock().expect("project lock poisoned");
        let store = self.store.lock().expect("store poisoned");
        if store
            .sent_turn_for_packet(&request.project_id, &request.packet_digest)?
            .is_some_and(|sent| sent.id != request.turn_id)
        {
            return Err(ServiceError::Invalid(
                "packet already bound to another sent turn; prepare a new exchange".into(),
            ));
        }
        if let Some(existing) = store.turn(&request.turn_id)? {
            if existing.packet_digest == request.packet_digest
                && existing.project_id == request.project_id
                && existing.role == "user"
                && existing.content_hash == canonical_sha256(&request.user_draft)?
            {
                store.mark_context_sent(
                    &request.project_id,
                    &request.packet_digest,
                    &existing.id,
                )?;
                return Ok(SentTurn {
                    turn_id: existing.id,
                    packet_digest: existing.packet_digest,
                    state_version: store
                        .project(&request.project_id)?
                        .ok_or_else(|| StoreError::ProjectNotFound(request.project_id.clone()))?
                        .state_version,
                    duplicate: true,
                });
            }
            return Err(ServiceError::PacketMismatch);
        }
        let context = store
            .context_run_by_digest(&request.project_id, &request.packet_digest)?
            .ok_or(ServiceError::UnknownPacket)?;
        let project = store
            .project(&request.project_id)?
            .ok_or_else(|| StoreError::ProjectNotFound(request.project_id.clone()))?;
        if project.state_version != context.state_version {
            store.audit(
                &request.project_id,
                "STALE_PACKET_REJECTED",
                &request.idempotency_key,
                &json!({"packet_digest":request.packet_digest,"prepared":context.state_version,"current":project.state_version}),
                &request.captured_at,
            )?;
            return Err(ServiceError::StalePacket {
                prepared: context.state_version,
                current: project.state_version,
            });
        }
        if canonical_sha256(&request.user_draft)? != context.draft_hash {
            return Err(ServiceError::PacketMismatch);
        }
        store.record_turn(&TurnRecord {
            id: request.turn_id.clone(),
            session_id: context.provider_session_id,
            project_id: request.project_id.clone(),
            workstream_id: context.workstream_id,
            role: "user".into(),
            ordinal: request.ordinal,
            normalized_text: request.user_draft.clone(),
            content_hash: canonical_sha256(&request.user_draft)?,
            packet_digest: request.packet_digest.clone(),
            completeness: "complete".into(),
            captured_at: request.captured_at,
            provider_timestamp: None,
        })?;
        store.mark_context_sent(
            &request.project_id,
            &request.packet_digest,
            &request.turn_id,
        )?;
        Ok(SentTurn {
            turn_id: request.turn_id,
            packet_digest: request.packet_digest,
            state_version: project.state_version,
            duplicate: false,
        })
    }

    pub fn evaluate_turn(&self, request: EvaluateTurnRequest) -> Result<EvaluationResult> {
        let project_lock = self.project_lock(&request.project_id);
        let _writer = project_lock.lock().expect("project lock poisoned");
        let store = self.store.lock().expect("store poisoned");
        let context = store
            .context_run_by_digest(&request.project_id, &request.packet_digest)?
            .ok_or(ServiceError::UnknownPacket)?;
        let project = store
            .project(&request.project_id)?
            .ok_or_else(|| StoreError::ProjectNotFound(request.project_id.clone()))?;
        let stale = context.state_version != project.state_version;
        if self.gateway.is_some()
            && store
                .sent_turn_for_packet(&request.project_id, &request.packet_digest)?
                .is_none()
        {
            return Err(ServiceError::PacketMismatch);
        }
        if let Some(existing) = store.turn(&request.response_turn_id)? {
            if existing.project_id != request.project_id
                || existing.packet_digest != request.packet_digest
                || existing.content_hash != canonical_sha256(&request.response_text)?
            {
                return Err(ServiceError::PacketMismatch);
            }
        }
        store.record_turn(&TurnRecord {
            id: request.response_turn_id.clone(),
            session_id: context.provider_session_id,
            project_id: request.project_id.clone(),
            workstream_id: context.workstream_id.clone(),
            role: "assistant".into(),
            ordinal: request.ordinal,
            normalized_text: request.response_text.clone(),
            content_hash: canonical_sha256(&request.response_text)?,
            packet_digest: request.packet_digest.clone(),
            completeness: if request.complete {
                "complete"
            } else {
                "incomplete"
            }
            .into(),
            captured_at: request.created_at.clone(),
            provider_timestamp: None,
        })?;
        let evaluation_id = canonical_sha256(
            &json!({"kind":"evaluation","turn_id":request.response_turn_id,"packet_digest":request.packet_digest}),
        )?;
        let mut intervention_ids = Vec::new();
        let mut diagnostics = Vec::new();
        let mut evaluation_policy_version = context.policy_version.clone();
        let result = if !request.complete {
            EvaluationState::Incomplete
        } else if stale {
            EvaluationState::Review
        } else {
            let sections: Vec<PacketSection> = serde_json::from_str(&context.selected_json)?;
            let candidates = extract_candidates(
                &request.project_id,
                &request.response_turn_id,
                &request.response_text,
                CandidateChannel::DeterministicVisibleTurn,
            );
            for candidate in &candidates {
                store.record_candidate(candidate, &request.created_at)?;
            }
            let governance_request = EvaluationRequest {
                project_id: request.project_id.clone(),
                workstream_id: context.workstream_id.clone(),
                packet_project_id: context.project_id.clone(),
                packet_workstream_id: context.workstream_id.clone(),
                turn_id: request.response_turn_id.clone(),
                response_text: request.response_text.clone(),
                complete: true,
                rules: governance_rules(&sections),
                asserted_candidates: candidates.clone(),
                evidence_used: vec![],
                supersession_attempts: vec![],
                addressed_state_ids: vec![],
                action_proposed: !candidates.is_empty(),
                claim_checks: vec![],
                structure_check: None,
            };
            let (governance, gateway_error) = match self.governance_verifier.health() {
                Ok(()) => match GovernanceEngine::new(Arc::clone(&self.governance_verifier))
                    .evaluate(governance_request.clone())
                {
                    Ok(result) => (result, None),
                    Err(GovernanceError::Gateway(error)) => {
                        (native_governance(governance_request)?, Some(error))
                    }
                    Err(error) => {
                        return Err(ServiceError::Invalid(format!(
                            "governance evaluation failed: {error}"
                        )));
                    }
                },
                Err(error) => (native_governance(governance_request)?, Some(error)),
            };
            evaluation_policy_version = governance.policy_version.clone();
            for intervention in &governance.interventions {
                store.record_intervention(intervention, &request.created_at)?;
            }
            intervention_ids = governance
                .interventions
                .iter()
                .map(|intervention| intervention.id.clone())
                .collect();
            if let Some(error) = gateway_error {
                diagnostics.push("gateway_unavailable".into());
                store.audit(
                    &request.project_id,
                    "gateway_unavailable",
                    &evaluation_id,
                    &json!({
                        "evaluation_id": evaluation_id,
                        "error": error,
                        "native_rules_ran": true,
                        "result_capped_at": "REVIEW"
                    }),
                    &request.created_at,
                )?;
                EvaluationState::Review
            } else {
                map_governance_state(governance.state)
            }
        };
        let mut response = EvaluationResult {
            evaluation_id: evaluation_id.clone(),
            response_turn_id: request.response_turn_id.clone(),
            packet_digest: request.packet_digest.clone(),
            state_version: context.state_version,
            result,
            intervention_ids: intervention_ids.clone(),
            stale,
            diagnostics,
        };
        store.record_response_evaluation(&ResponseEvaluationRecord {
            id: evaluation_id,
            project_id: request.project_id,
            turn_id: request.response_turn_id,
            packet_digest: request.packet_digest,
            state_version: context.state_version,
            result: serde_json::to_value(result)?
                .as_str()
                .unwrap_or("PASS")
                .to_owned(),
            intervention_ids,
            policy_version: evaluation_policy_version,
            latency_ms: request.latency_ms,
            created_at: request.created_at,
        })?;
        if let Some(gateway) = &self.gateway {
            let evaluation = store
                .response_evaluation(&response.evaluation_id)?
                .expect("evaluation just stored");
            match experience::commit_captured_exchange(&store, gateway, &evaluation) {
                Ok(Some(_)) => {}
                Ok(None) if request.complete => response
                    .diagnostics
                    .push("runtime_commit_awaiting_resolution".into()),
                Ok(None) => {}
                Err(error) => {
                    response
                        .diagnostics
                        .push(format!("runtime_commit_pending: {error}"));
                    response.result = EvaluationState::Review;
                }
            }
        }
        Ok(response)
    }

    pub fn commit_object(
        &self,
        object: StateObject,
        base_state_version: u64,
        actor_id: &str,
        idempotency_key: &str,
        created_at: &str,
    ) -> Result<()> {
        let project_lock = self.project_lock(&object.project_id);
        let _writer = project_lock.lock().expect("project lock poisoned");
        self.store.lock().expect("store poisoned").commit_object(
            object,
            base_state_version,
            "user",
            actor_id,
            idempotency_key,
            created_at,
        )?;
        Ok(())
    }

    pub fn create_manual_candidate(
        &self,
        project_id: &str,
        source_id: &str,
        request: CreateCandidateRequest,
        created_at: &str,
    ) -> Result<StateMutationCandidate> {
        if request.text.trim().is_empty() {
            return Err(ServiceError::Invalid("candidate text is required".into()));
        }
        if request
            .authority
            .as_deref()
            .is_some_and(|value| value != "user")
        {
            return Err(ServiceError::Invalid(
                "quick capture only accepts explicit user authority".into(),
            ));
        }
        if request.requires_user_confirmation == Some(false) {
            return Err(ServiceError::Invalid(
                "candidate must require explicit user confirmation".into(),
            ));
        }
        let prefix = match request.kind.to_ascii_lowercase().as_str() {
            "decision" => "Decision",
            "constraint" => "Constraint",
            "reject" | "rejected" | "rejected_path" => "Rejected",
            "complete" | "completed" | "completed_work" => "Completed",
            "unresolved" | "unresolved_dependency" => "Unresolved",
            "evidence" => "Evidence",
            _ => {
                return Err(ServiceError::Invalid(format!(
                    "unsupported candidate kind: {}",
                    request.kind
                )));
            }
        };
        let tagged = format!("{prefix}: {}", request.text.trim());
        let candidate =
            extract_candidates(project_id, source_id, &tagged, CandidateChannel::ManualUser)
                .into_iter()
                .next()
                .ok_or_else(|| {
                    ServiceError::Invalid("candidate extraction produced no result".into())
                })?;
        self.store
            .lock()
            .expect("store poisoned")
            .record_candidate(&candidate, created_at)?;
        Ok(candidate)
    }

    pub fn handle_envelope(&self, envelope: Envelope) -> WireResponse {
        let request_id = envelope.request_id.clone();
        let result = self.dispatch(envelope);
        match result {
            Ok(payload) => WireResponse {
                protocol: SERVICE_PROTOCOL_VERSION.into(),
                request_id,
                ok: true,
                payload: Some(payload),
                error: None,
            },
            Err(error) => WireResponse {
                protocol: SERVICE_PROTOCOL_VERSION.into(),
                request_id,
                ok: false,
                payload: None,
                error: Some(WireError {
                    code: error_code(&error).into(),
                    message: error.to_string(),
                    retryable: matches!(error, ServiceError::StalePacket { .. }),
                }),
            },
        }
    }

    fn dispatch(&self, envelope: Envelope) -> Result<Value> {
        if envelope.protocol != SERVICE_PROTOCOL_VERSION {
            return Err(ServiceError::ProtocolMismatch {
                expected: SERVICE_PROTOCOL_VERSION.into(),
                actual: envelope.protocol,
            });
        }
        match envelope.method {
            Method::ProviderStatus
            | Method::ConversationList
            | Method::ConversationCreate
            | Method::ConversationGet
            | Method::ConversationPrepare
            | Method::ConversationSend
            | Method::ConversationEvaluate => self.dispatch_conversation(envelope),
            Method::CapabilitiesGet => Ok(json!({
                "protocol": SERVICE_PROTOCOL_VERSION,
                "service_version": SERVICE_VERSION,
                "prepare_readonly": true,
                "single_writer_per_project": true
            })),
            Method::TurnPrepare => Ok(serde_json::to_value(
                self.prepare_turn(serde_json::from_value(envelope.payload)?)?,
            )?),
            Method::TurnSent => Ok(serde_json::to_value(
                self.send_turn(serde_json::from_value(envelope.payload)?)?,
            )?),
            Method::ResponseEvaluate => Ok(serde_json::to_value(
                self.evaluate_turn(serde_json::from_value(envelope.payload)?)?,
            )?),
            Method::InterventionResolve => {
                let project = envelope.project_id.ok_or(ServiceError::MissingProject)?;
                let lock = self.project_lock(&project);
                let _writer = lock.lock().expect("project lock poisoned");
                let store = self.store.lock().expect("store poisoned");
                let id = envelope.payload["intervention_id"]
                    .as_str()
                    .ok_or_else(|| ServiceError::Invalid("intervention_id required".into()))?;
                let status = serde_json::from_value(envelope.payload["status"].clone())?;
                experience::resolve_intervention_with_runtime(
                    &store,
                    self.gateway.as_ref(),
                    &project,
                    id,
                    status,
                    &envelope.sent_at,
                )?;
                Ok(json!({"resolved":true}))
            }
            Method::StateCandidateCreate => {
                let project_id = envelope.project_id.ok_or(ServiceError::MissingProject)?;
                Ok(serde_json::to_value(self.create_manual_candidate(
                    &project_id,
                    &envelope.idempotency_key,
                    serde_json::from_value(envelope.payload)?,
                    &envelope.sent_at,
                )?)?)
            }
            method => Err(ServiceError::UnsupportedMethod(format!("{method:?}"))),
        }
    }
}

#[derive(Debug, Clone, Copy)]
struct NativeOnlyVerifier;

impl GatewayVerifier for NativeOnlyVerifier {
    fn verify_drift(&self, _payload: Value) -> std::result::Result<Value, String> {
        Ok(json!({"decision":"permit"}))
    }

    fn verify_claims(&self, _payload: Value) -> std::result::Result<Value, String> {
        Ok(json!({"supported_count":0,"unsupported_count":0}))
    }

    fn adjudicate_structure(&self, _payload: Value) -> std::result::Result<Value, String> {
        Ok(json!({"accepted":true}))
    }
}

fn native_governance(
    request: EvaluationRequest,
) -> Result<tom_assist_governance::GovernanceResult> {
    GovernanceEngine::new(NativeOnlyVerifier)
        .evaluate(request)
        .map_err(|error| ServiceError::Invalid(format!("native governance failed: {error}")))
}

fn map_governance_state(state: GovernanceEvaluationState) -> EvaluationState {
    match state {
        GovernanceEvaluationState::Pass => EvaluationState::Pass,
        GovernanceEvaluationState::Review => EvaluationState::Review,
        GovernanceEvaluationState::Conflict => EvaluationState::Conflict,
        GovernanceEvaluationState::Incomplete => EvaluationState::Incomplete,
    }
}

fn governance_rules(sections: &[PacketSection]) -> Vec<LedgerRule> {
    let mut rules = Vec::new();
    for section in sections {
        let code = if section.section_type == "HELD_DECISIONS" {
            Some(InterventionCode::Contradiction)
        } else if section.section_type == "BINDING_CONSTRAINTS" {
            Some(InterventionCode::ConstraintDropped)
        } else if section.section_type.starts_with("REJECTED_OR_SUPERSEDED") {
            Some(InterventionCode::SupersededPathRevived)
        } else if section.section_type.starts_with("COMPLETED_WORK") {
            Some(InterventionCode::CompletedWorkReproposed)
        } else if section.section_type == "ACTIVE_OBJECTIVE" {
            Some(InterventionCode::ObjectiveDrift)
        } else if section.section_type == "LOAD_BEARING_CONCEPTS" {
            Some(InterventionCode::ConceptDrift)
        } else if section.section_type == "UNRESOLVED_DEPENDENCIES" {
            Some(InterventionCode::UnresolvedDependencyIgnored)
        } else {
            None
        };
        let Some(code) = code else { continue };
        rules.extend(section.items.iter().map(|item| LedgerRule {
            code,
            state_id: item.state_id.clone(),
            summary: item.text.clone(),
            match_phrases: vec![item.text.clone()],
            evidence_turn_ids: vec![],
            suggested_context_patch: Some(item.text.clone()),
        }));
    }
    rules
}

fn error_code(error: &ServiceError) -> &'static str {
    match error {
        ServiceError::ProtocolMismatch { .. } => "PROTOCOL_MISMATCH",
        ServiceError::StalePacket { .. } => "STATE_VERSION_CONFLICT",
        ServiceError::UnknownPacket | ServiceError::PacketMismatch => "VALIDATION_FAILED",
        ServiceError::CaptureIncomplete => "CAPTURE_INCOMPLETE",
        ServiceError::Store(StoreError::ProjectNotFound(_)) => "PROJECT_NOT_FOUND",
        ServiceError::Store(StoreError::StateVersionConflict { .. }) => "STATE_VERSION_CONFLICT",
        ServiceError::Store(_) => "DATABASE_INTEGRITY_ERROR",
        _ => "VALIDATION_FAILED",
    }
}

pub fn bind_unix(path: &Path) -> Result<UnixListener> {
    if path.exists() {
        fs::remove_file(path)?;
    }
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let listener = UnixListener::bind(path)?;
    fs::set_permissions(path, fs::Permissions::from_mode(0o600))?;
    Ok(listener)
}

pub fn handle_stream(service: &AssistService, mut stream: UnixStream) -> Result<()> {
    let mut request = String::new();
    BufReader::new(stream.try_clone()?).read_line(&mut request)?;
    let envelope: Envelope = serde_json::from_str(&request)?;
    let response = service.handle_envelope(envelope);
    serde_json::to_writer(&mut stream, &response)?;
    stream.write_all(b"\n")?;
    stream.flush()?;
    Ok(())
}

pub fn serve_unix(path: &Path, service: Arc<AssistService>) -> Result<()> {
    let listener = bind_unix(path)?;
    for stream in listener.incoming() {
        let stream = stream?;
        let service = Arc::clone(&service);
        std::thread::spawn(move || {
            let _ = handle_stream(&service, stream);
        });
    }
    Ok(())
}
