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
pub struct RankedDocumentChunk {
    pub id: String,
    pub document_id: String,
    pub display_name: String,
    pub chunk_index: u64,
    pub start: u64,
    pub end: u64,
    pub excerpt_start: u64,
    pub excerpt_end: u64,
    pub text: String,
    pub text_sha256: String,
    pub excerpt_sha256: String,
    #[serde(default)]
    pub source_segments: Vec<DocumentSourceSegment>,
    pub semantic_score: f64,
    pub best_chunk_score: f64,
    pub lexical_score: f64,
    pub dense_rank: u64,
    pub lexical_rank: Option<u64>,
    pub rrf_score: f64,
    pub rank: u64,
    pub score_space: String,
    pub packet_eligible: bool,
    pub structural_signature: Option<Value>,
    pub truncated: bool,
    #[serde(default)]
    pub clause_identifiers: Vec<String>,
    #[serde(default)]
    pub matched_clause_identifier: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DocumentSourceSegment {
    pub start: u64,
    pub end: u64,
    pub role: String,
    #[serde(default)]
    pub entry_id: String,
    #[serde(default)]
    pub identifier: String,
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
    #[serde(default)]
    pub ranked_document_chunks: Vec<RankedDocumentChunk>,
    #[serde(default)]
    pub document_research_trace: Option<Value>,
    pub checkpoint_digest: String,
    #[serde(default)]
    pub structural_load_mode: String,
    #[serde(default)]
    pub structural_analysis: Option<Value>,
    #[serde(default)]
    pub shadow_structural_retrieval: Vec<Value>,
    #[serde(default)]
    pub parser_glossary: Option<Value>,
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
    pub fn inspect_gemma(&self, payload: Value) -> Result<Value> {
        self.request("POST", "/inspection/gemma", Some(payload))
    }
    pub fn native_memory_answer(&self, payload: Value) -> Result<Value> {
        self.request("POST", "/document/native-memory/answer", Some(payload))
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
    pub fn document_research_intent(&self, user_text: &str) -> Result<Value> {
        self.request(
            "POST",
            "/document/research/intent",
            Some(json!({"user_text": user_text})),
        )
    }
    pub fn preview_rank(
        &self,
        project_id: &str,
        user_text: &str,
        k: u64,
        max_chars: u64,
    ) -> Result<RankPreview> {
        self.preview_rank_complete(project_id, user_text, k, max_chars, &[])
    }
    pub fn preview_rank_with_glossary_titles(
        &self,
        project_id: &str,
        user_text: &str,
        k: u64,
        max_chars: u64,
        declared_glossary_titles: &[String],
    ) -> Result<RankPreview> {
        self.preview_rank_complete(
            project_id,
            user_text,
            k,
            max_chars,
            declared_glossary_titles,
        )
    }

    /// Request one pure, read-only ranking page.  Callers that need explicit
    /// recovery control can retain the opaque continuation returned in the
    /// page trace and safely submit it again after a transport interruption.
    pub fn preview_rank_page(
        &self,
        project_id: &str,
        user_text: &str,
        k: u64,
        max_chars: u64,
        declared_glossary_titles: &[String],
        document_research_cursor: Option<&Value>,
    ) -> Result<RankPreview> {
        let mut payload = json!({
            "project_id": project_id,
            "user_text": user_text,
            "k": k,
            "max_chars": max_chars,
            "declared_glossary_titles": declared_glossary_titles,
        });
        if let Some(value) = document_research_cursor {
            payload["document_research_cursor"] = value.clone();
        }
        self.request("POST", "/preview/rank", Some(payload))
    }

    fn preview_rank_complete(
        &self,
        project_id: &str,
        user_text: &str,
        k: u64,
        max_chars: u64,
        declared_glossary_titles: &[String],
    ) -> Result<RankPreview> {
        let mut cursor: Option<Value> = None;
        for _ in 0..64 {
            let request_page = || {
                self.preview_rank_page(
                    project_id,
                    user_text,
                    k,
                    max_chars,
                    declared_glossary_titles,
                    cursor.as_ref(),
                )
            };
            let preview = match request_page() {
                Ok(preview) => preview,
                Err(error)
                    if matches!(
                        &error,
                        GatewayError::Io(_) | GatewayError::Json(_) | GatewayError::Protocol(_)
                    ) =>
                {
                    request_page()?
                }
                Err(error) => return Err(error),
            };
            let complete = preview
                .document_research_trace
                .as_ref()
                .and_then(|trace| trace.pointer("/processing_coverage/cursor/complete"))
                .and_then(Value::as_bool);
            if complete != Some(false) {
                return Ok(preview);
            }
            cursor = preview
                .document_research_trace
                .as_ref()
                .and_then(|trace| trace.pointer("/processing_coverage/cursor/continuation"))
                .filter(|value| !value.is_null())
                .cloned();
            if cursor.is_none() {
                return Err(GatewayError::Protocol(
                    "incomplete document research omitted its continuation cursor".into(),
                ));
            }
        }
        Err(GatewayError::Protocol(
            "document research exceeded the bounded continuation limit".into(),
        ))
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
    pub fn ingest_document(&self, payload: Value) -> Result<Value> {
        self.request("POST", "/document/ingest", Some(payload))
    }
    pub fn list_documents(&self, project_id: &str, include_withdrawn: bool) -> Result<Value> {
        self.request(
            "POST",
            "/document/list",
            Some(json!({
                "project_id": project_id,
                "include_withdrawn": include_withdrawn,
            })),
        )
    }
    pub fn get_document(&self, project_id: &str, document_id: &str) -> Result<Value> {
        self.request(
            "POST",
            "/document/get",
            Some(json!({"project_id":project_id,"document_id":document_id})),
        )
    }
    pub fn withdraw_document(&self, payload: Value) -> Result<Value> {
        self.request("POST", "/document/withdraw", Some(payload))
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
            if path == "/provider/complete"
                || path == "/inspection/gemma"
                || path == "/document/native-memory/answer"
            {
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

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::net::{UnixListener, UnixStream};
    use std::thread;

    fn request_body(mut stream: &UnixStream) -> Value {
        let mut bytes = Vec::new();
        stream.read_to_end(&mut bytes).unwrap();
        let split = bytes
            .windows(4)
            .position(|window| window == b"\r\n\r\n")
            .unwrap();
        serde_json::from_slice(&bytes[split + 4..]).unwrap()
    }

    fn reply(mut stream: UnixStream, complete: bool, continuation: Option<&str>) {
        let body = serde_json::to_vec(&json!({
            "activated_branch_ids": [],
            "candidate_trace": [],
            "branch_trace": [],
            "policy_version": "fixture",
            "activation_id": "fixture",
            "triggers": [],
            "ranked_anchors": [],
            "ranked_document_chunks": [],
            "document_research_trace": {
                "processing_coverage": {"cursor": {
                    "complete": complete,
                    "continuation": continuation,
                }}
            },
            "checkpoint_digest": "sha256:fixture",
        }))
        .unwrap();
        write!(
            stream,
            "HTTP/1.0 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\n\r\n",
            body.len()
        )
        .unwrap();
        stream.write_all(&body).unwrap();
    }

    #[test]
    fn complete_preview_retries_the_identical_pure_page_and_retains_cursor() {
        let directory = tempfile::tempdir().unwrap();
        let socket = directory.path().join("gateway.sock");
        let listener = UnixListener::bind(&socket).unwrap();
        let server = thread::spawn(move || {
            let first = listener.accept().unwrap().0;
            let first_body = request_body(&first);
            drop(first); // Deliberate transport loss after receiving the request.

            let second = listener.accept().unwrap().0;
            let second_body = request_body(&second);
            reply(second, false, Some("opaque.signed"));

            let third = listener.accept().unwrap().0;
            let third_body = request_body(&third);
            reply(third, true, None);
            (first_body, second_body, third_body)
        });

        let preview = GatewayClient::new(&socket)
            .preview_rank("project", "question", 64, 32_000)
            .unwrap();
        assert_eq!(
            preview
                .document_research_trace
                .as_ref()
                .and_then(|trace| trace.pointer("/processing_coverage/cursor/complete"))
                .and_then(Value::as_bool),
            Some(true)
        );
        let (first, second, third) = server.join().unwrap();
        assert_eq!(first, second);
        assert!(first.get("document_research_cursor").is_none());
        assert_eq!(
            third
                .get("document_research_cursor")
                .and_then(Value::as_str),
            Some("opaque.signed")
        );
    }
}
