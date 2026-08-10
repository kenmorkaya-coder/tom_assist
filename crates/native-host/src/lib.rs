//! Chrome Native Messaging framing and the exact-extension trust boundary.

use base64::Engine;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::fmt::{Display, Formatter};
use std::io::{Read, Write};
use std::os::unix::net::UnixStream;
use std::path::Path;
use tom_assist_protocol::{Envelope, PROTOCOL_VERSION};

pub const EXTENSION_ID: &str = "mollhhfpcdpgbnlinhhghkndeniglfba";
pub const ALLOWED_ORIGIN: &str = "chrome-extension://mollhhfpcdpgbnlinhhghkndeniglfba/";
pub const NATIVE_HOST_NAME: &str = "tom.assist.native";
pub const MAX_INBOUND_BYTES: usize = 16 * 1024 * 1024;
pub const CHUNK_THRESHOLD_BYTES: usize = 900 * 1024;
const CHUNK_RAW_BYTES: usize = 600 * 1024;

#[derive(Debug)]
pub enum HostError {
    Io(std::io::Error),
    Json(serde_json::Error),
    ForbiddenOrigin,
    ProtocolMismatch,
    InvalidLength(usize),
    AssistdClosed,
}

impl Display for HostError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(error) => write!(f, "I/O error: {error}"),
            Self::Json(error) => write!(f, "JSON error: {error}"),
            Self::ForbiddenOrigin => write!(f, "native message origin is not allowlisted"),
            Self::ProtocolMismatch => write!(f, "protocol mismatch"),
            Self::InvalidLength(length) => write!(f, "invalid native message length: {length}"),
            Self::AssistdClosed => write!(f, "assistd closed without a response"),
        }
    }
}

impl std::error::Error for HostError {}
impl From<std::io::Error> for HostError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value)
    }
}
impl From<serde_json::Error> for HostError {
    fn from(value: serde_json::Error) -> Self {
        Self::Json(value)
    }
}
pub type Result<T> = std::result::Result<T, HostError>;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ChunkFrame {
    pub correlation_id: String,
    pub seq: usize,
    pub total: usize,
    pub chunk_b64: String,
}

pub fn validate_origin(origin: &str) -> Result<()> {
    if origin == ALLOWED_ORIGIN {
        Ok(())
    } else {
        Err(HostError::ForbiddenOrigin)
    }
}

pub fn validate_envelope(value: Value) -> Result<Envelope> {
    let envelope: Envelope = serde_json::from_value(value)?;
    if envelope.protocol != PROTOCOL_VERSION {
        return Err(HostError::ProtocolMismatch);
    }
    if !is_uuid(&envelope.request_id)
        || !is_uuid(&envelope.idempotency_key)
        || !is_uuid(&envelope.actor.instance_id)
        || envelope
            .project_id
            .as_deref()
            .is_some_and(|value| !is_uuid(value))
        || !envelope.sent_at.ends_with('Z')
    {
        return Err(HostError::Json(serde_json::Error::io(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            "envelope format constraint failed",
        ))));
    }
    Ok(envelope)
}

fn is_uuid(value: &str) -> bool {
    let bytes = value.as_bytes();
    bytes.len() == 36
        && [8, 13, 18, 23]
            .into_iter()
            .all(|index| bytes[index] == b'-')
        && bytes
            .iter()
            .enumerate()
            .all(|(index, byte)| [8, 13, 18, 23].contains(&index) || byte.is_ascii_hexdigit())
}

pub fn read_native_frame<R: Read>(reader: &mut R) -> Result<Option<Value>> {
    let mut header = [0u8; 4];
    match reader.read_exact(&mut header) {
        Ok(()) => {}
        Err(error) if error.kind() == std::io::ErrorKind::UnexpectedEof => return Ok(None),
        Err(error) => return Err(error.into()),
    }
    let length = u32::from_le_bytes(header) as usize;
    if length == 0 || length > MAX_INBOUND_BYTES {
        return Err(HostError::InvalidLength(length));
    }
    let mut payload = vec![0; length];
    reader.read_exact(&mut payload)?;
    Ok(Some(serde_json::from_slice(&payload)?))
}

pub fn write_native_frame<W: Write>(writer: &mut W, value: &Value) -> Result<()> {
    let payload = serde_json::to_vec(value)?;
    if payload.len() > u32::MAX as usize {
        return Err(HostError::InvalidLength(payload.len()));
    }
    writer.write_all(&(payload.len() as u32).to_le_bytes())?;
    writer.write_all(&payload)?;
    writer.flush()?;
    Ok(())
}

/// Chunk a serialized host response only when the original message crosses D9's
/// 900 KB boundary. Raw chunks are 600 KB so base64 + JSON framing also stays
/// below that boundary.
pub fn chunk_response(correlation_id: &str, value: &Value) -> Result<Vec<Value>> {
    let payload = serde_json::to_vec(value)?;
    if payload.len() <= CHUNK_THRESHOLD_BYTES {
        return Ok(vec![value.clone()]);
    }
    let total = payload.len().div_ceil(CHUNK_RAW_BYTES);
    Ok(payload
        .chunks(CHUNK_RAW_BYTES)
        .enumerate()
        .map(|(seq, bytes)| {
            serde_json::to_value(ChunkFrame {
                correlation_id: correlation_id.to_owned(),
                seq,
                total,
                chunk_b64: base64::engine::general_purpose::STANDARD.encode(bytes),
            })
            .expect("ChunkFrame is JSON serializable")
        })
        .collect())
}

pub fn forward_to_assistd(socket_path: &Path, envelope: &Envelope) -> Result<Value> {
    let mut stream = UnixStream::connect(socket_path)?;
    serde_json::to_writer(&mut stream, envelope)?;
    stream.write_all(b"\n")?;
    stream.flush()?;
    let mut response = Vec::new();
    stream.read_to_end(&mut response)?;
    let line = response
        .split(|byte| *byte == b'\n')
        .next()
        .filter(|line| !line.is_empty())
        .ok_or(HostError::AssistdClosed)?;
    Ok(serde_json::from_slice(line)?)
}

pub fn error_frame(correlation_id: &str, error: &HostError) -> Value {
    json!({
        "protocol": PROTOCOL_VERSION,
        "correlation_id": correlation_id,
        "ok": false,
        "error": {"code": match error {
            HostError::ForbiddenOrigin => "PERMISSION_DENIED",
            HostError::ProtocolMismatch => "PROTOCOL_MISMATCH",
            HostError::InvalidLength(_) | HostError::Json(_) => "VALIDATION_FAILED",
            _ => "SERVICE_UNAVAILABLE"
        }, "message": error.to_string()}
    })
}
