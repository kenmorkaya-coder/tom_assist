//! Narrow HTTP-over-Unix-socket client for the Python tom_master gateway.

use serde::{Deserialize, Serialize, de::DeserializeOwned};
use serde_json::{Value, json};
use std::fmt::{Display, Formatter};
use std::io::{Read, Write};
use std::os::unix::net::UnixStream;
use std::path::{Path, PathBuf};
use tom_assist_protocol::TomCapabilities;

pub const GATEWAY_PROTOCOL_VERSION: &str = "tom-gateway/1.0";

#[derive(Debug)]
pub enum GatewayError {
    Io(std::io::Error),
    Json(serde_json::Error),
    Protocol(String),
    Http { status: u16, body: String },
}

impl Display for GatewayError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(error) => write!(f, "gateway I/O error: {error}"),
            Self::Json(error) => write!(f, "gateway JSON error: {error}"),
            Self::Protocol(message) => write!(f, "gateway protocol error: {message}"),
            Self::Http { status, body } => write!(f, "gateway HTTP {status}: {body}"),
        }
    }
}

impl std::error::Error for GatewayError {}
impl From<std::io::Error> for GatewayError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value)
    }
}
impl From<serde_json::Error> for GatewayError {
    fn from(value: serde_json::Error) -> Self {
        Self::Json(value)
    }
}
pub type Result<T> = std::result::Result<T, GatewayError>;

#[derive(Debug, Clone)]
pub struct GatewayClient {
    socket_path: PathBuf,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RankedAnchor {
    pub rrf_score: f64,
    pub lexical_rank: Option<u64>,
    pub structural_rank: Option<u64>,
    pub matched_branch_id: Option<String>,
    pub id: String,
    pub text: String,
    pub semantic_score: f64,
    pub structural_resonance: f64,
    pub dependency_relevance: f64,
    pub authority_strength: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RankPreview {
    pub activated_branch_ids: Vec<String>,
    pub candidate_trace: Vec<Value>,
    pub branch_trace: Vec<Value>,
    pub policy_version: String,
    pub activation_id: String,
    pub triggers: Vec<Value>,
    pub ranked_anchors: Vec<RankedAnchor>,
    pub checkpoint_digest: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CommitSummary {
    pub idempotency_key: String,
    pub role: String,
    pub text_hash: String,
    pub engine_tick_before: u64,
    pub engine_tick_after: u64,
    pub rgm_current_tick: u64,
    pub branch_count: u64,
    pub anchor_id: String,
    #[serde(rename = "K_total")]
    pub k_total: f64,
    pub runtime_error_code: Option<String>,
    pub seed_profile: String,
    pub seed_checkpoint_digest: String,
    pub prior_checkpoint_digest: String,
    pub checkpoint_digest: String,
}

impl GatewayClient {
    pub fn new(socket_path: impl AsRef<Path>) -> Self {
        Self {
            socket_path: socket_path.as_ref().to_path_buf(),
        }
    }
    pub fn socket_path(&self) -> &Path {
        &self.socket_path
    }
    pub fn health(&self) -> Result<Value> {
        self.request("GET", "/health", None)
    }
    pub fn provider_status(&self) -> Result<Value> {
        self.request("GET", "/provider/status", None)
    }
    pub fn provider_complete(&self, prompt: &str) -> Result<Value> {
        self.request(
            "POST",
            "/provider/complete",
            Some(json!({"prompt":prompt,"explicit_send":true})),
        )
    }
    pub fn export_runtime(&self, project_id: &str, directory: &Path) -> Result<Value> {
        self.request(
            "POST",
            "/archive/runtime/export",
            Some(json!({"project_id":project_id,"directory":directory})),
        )
    }
    pub fn verify_runtime(&self, directory: &Path) -> Result<Value> {
        self.request(
            "POST",
            "/archive/runtime/verify",
            Some(json!({"directory":directory})),
        )
    }
    pub fn import_runtime(&self, action: &str, directory: &Path, context: &Value) -> Result<Value> {
        self.request(
            "POST",
            "/archive/runtime/import",
            Some(json!({"action":action,"directory":directory,"context":context})),
        )
    }
    pub fn capabilities(&self) -> Result<TomCapabilities> {
        self.request("GET", "/capabilities", None)
    }
    pub fn preview_rank(
        &self,
        project_id: &str,
        user_text: &str,
        k: u64,
        max_chars: u64,
    ) -> Result<RankPreview> {
        self.request(
            "POST",
            "/preview/rank",
            Some(
                json!({"project_id":project_id,"user_text":user_text,"k":k,"max_chars":max_chars}),
            ),
        )
    }
    pub fn commit_turn(
        &self,
        project_id: &str,
        role: &str,
        text: &str,
        idempotency_key: &str,
    ) -> Result<CommitSummary> {
        self.request("POST", "/turn/commit", Some(json!({"project_id":project_id,"role":role,"text":text,"idempotency_key":idempotency_key})))
    }
    pub fn save_checkpoint(&self, project_id: &str) -> Result<Value> {
        self.request(
            "POST",
            "/checkpoint/save",
            Some(json!({"project_id":project_id})),
        )
    }

    pub fn commit_exchange(&self, payload: Value) -> Result<Value> {
        self.request("POST", "/turn/commit", Some(payload))
    }

    pub fn memory_settings(&self, project_id: &str, settings: Value) -> Result<Value> {
        self.request(
            "POST",
            "/project/settings",
            Some(json!({"project_id":project_id,"settings":settings})),
        )
    }

    pub fn memory_diagnostics(&self, project_id: &str, after_event_id: u64) -> Result<Value> {
        self.request(
            "POST",
            "/memory/diagnostics",
            Some(json!({"project_id":project_id,"after_event_id":after_event_id})),
        )
    }
    pub fn restore_checkpoint(&self, project_id: &str, checkpoint_id: &str) -> Result<Value> {
        self.request(
            "POST",
            "/checkpoint/restore",
            Some(json!({"project_id":project_id,"checkpoint_id":checkpoint_id})),
        )
    }
    pub fn verify_drift(&self, payload: Value) -> Result<Value> {
        self.request("POST", "/verify/drift", Some(payload))
    }
    pub fn resonate_guardrails(&self, payload: Value) -> Result<Value> {
        self.request("POST", "/verify/guardrails", Some(payload))
    }
    pub fn verify_claims(&self, payload: Value) -> Result<Value> {
        self.request("POST", "/verify/claims", Some(payload))
    }
    pub fn adjudicate_structure(&self, payload: Value) -> Result<Value> {
        self.request("POST", "/adjudicate/structure", Some(payload))
    }

    fn request<T: DeserializeOwned>(
        &self,
        method: &str,
        path: &str,
        body: Option<Value>,
    ) -> Result<T> {
        let body = body
            .map(|value| serde_json::to_vec(&value))
            .transpose()?
            .unwrap_or_default();
        let mut stream = UnixStream::connect(&self.socket_path)?;
        stream.set_read_timeout(Some(std::time::Duration::from_secs(
            if path == "/provider/complete" {
                200
            } else {
                60
            },
        )))?;
        stream.set_write_timeout(Some(std::time::Duration::from_secs(60)))?;
        let header = format!(
            "{method} {path} HTTP/1.0\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
            body.len()
        );
        stream.write_all(header.as_bytes())?;
        stream.write_all(&body)?;
        stream.shutdown(std::net::Shutdown::Write)?;
        let mut response = Vec::new();
        stream.read_to_end(&mut response)?;
        let separator = response
            .windows(4)
            .position(|window| window == b"\r\n\r\n")
            .ok_or_else(|| GatewayError::Protocol("missing HTTP header separator".into()))?;
        let header_text = std::str::from_utf8(&response[..separator])
            .map_err(|error| GatewayError::Protocol(error.to_string()))?;
        let status: u16 = header_text
            .lines()
            .next()
            .and_then(|line| line.split_whitespace().nth(1))
            .and_then(|value| value.parse().ok())
            .ok_or_else(|| GatewayError::Protocol("missing HTTP status".into()))?;
        let response_body = &response[separator + 4..];
        if !(200..300).contains(&status) {
            return Err(GatewayError::Http {
                status,
                body: String::from_utf8_lossy(response_body).into_owned(),
            });
        }
        Ok(serde_json::from_slice(response_body)?)
    }
}
