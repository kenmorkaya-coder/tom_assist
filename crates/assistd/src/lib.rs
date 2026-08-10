//! Snapshot-bound PREPARE_TURN / EVALUATE_TURN orchestration.

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
use tom_assist_persistence::{
    ContextRunRecord, ResponseEvaluationRecord, Store, StoreError, TurnRecord,
};
use tom_assist_protocol::{
    ContinuityPacket, Envelope, ExcludedItem, Method, PacketDigestInput, PacketSection,
    ProviderCapabilities, StateObject, canonical_sha256, packet_digest,
};

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
    store: Mutex<Store>,
    project_writers: Mutex<HashMap<String, Arc<Mutex<()>>>>,
}

impl AssistService {
    pub fn new(store: Store) -> Self {
        Self {
            store: Mutex::new(store),
            project_writers: Mutex::new(HashMap::new()),
        }
    }

    fn project_lock(&self, project_id: &str) -> Arc<Mutex<()>> {
        self.project_writers
            .lock()
            .expect("project lock map poisoned")
            .entry(project_id.to_owned())
            .or_insert_with(|| Arc::new(Mutex::new(())))
            .clone()
    }

    pub fn prepare_turn(&self, request: PrepareTurnRequest) -> Result<PreparedTurn> {
        let store = self.store.lock().expect("store poisoned");
        let project = store
            .project(&request.project_id)?
            .ok_or_else(|| StoreError::ProjectNotFound(request.project_id.clone()))?;
        let state = store.current_state(&request.project_id)?;
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
            renderer_version: RENDERER_VERSION,
            policy_version: POLICY_VERSION,
            user_draft_hash: &draft_hash,
        })?;
        let packet_id = canonical_sha256(&json!({"kind":"packet","digest":digest}))?;
        let estimated_tokens = request.packet_text.chars().count().div_ceil(4) as u64;
        let packet = ContinuityPacket {
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
        if let Some(existing) = store.turn(&request.turn_id)? {
            if existing.packet_digest == request.packet_digest {
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
            project_id: request.project_id,
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
        let result = if !request.complete {
            EvaluationState::Incomplete
        } else if stale {
            EvaluationState::Review
        } else {
            EvaluationState::Pass
        };
        store.record_turn(&TurnRecord {
            id: request.response_turn_id.clone(),
            session_id: context.provider_session_id,
            project_id: request.project_id.clone(),
            workstream_id: context.workstream_id,
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
        let response = EvaluationResult {
            evaluation_id: evaluation_id.clone(),
            response_turn_id: request.response_turn_id.clone(),
            packet_digest: request.packet_digest.clone(),
            state_version: context.state_version,
            result,
            intervention_ids: vec![],
            stale,
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
            intervention_ids: vec![],
            policy_version: POLICY_VERSION.into(),
            latency_ms: request.latency_ms,
            created_at: request.created_at,
        })?;
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
            method => Err(ServiceError::UnsupportedMethod(format!("{method:?}"))),
        }
    }
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
