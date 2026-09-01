use crate::{BROKER_PROTOCOL_VERSION, Broker, BrokerError, BrokerStatus, ProviderReply, Result};
use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::fs;
use std::io::{BufRead, BufReader, Read, Write};
use std::os::unix::fs::{FileTypeExt, PermissionsExt};
use std::os::unix::net::{UnixListener, UnixStream};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration;

const MAX_HEADER_BYTES: usize = 32 * 1024;
const MAX_REQUEST_BYTES: usize = 256 * 1024;
const MAX_RESPONSE_BYTES: usize = 768 * 1024;

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ExplicitAction {
    explicit_user_action: bool,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct CompletionRequest {
    explicit_send: bool,
    prompt: String,
}

#[derive(Debug, Serialize)]
struct ErrorBody<'a> {
    ok: bool,
    protocol: &'a str,
    error: ErrorCode<'a>,
}

#[derive(Debug, Serialize)]
struct ErrorCode<'a> {
    code: &'a str,
}

#[derive(Debug)]
struct Request {
    method: String,
    path: String,
    body: Vec<u8>,
}

#[derive(Debug, Clone)]
pub struct BrokerClient {
    socket_path: PathBuf,
}

impl BrokerClient {
    pub fn new(socket_path: impl Into<PathBuf>) -> Self {
        Self {
            socket_path: socket_path.into(),
        }
    }

    pub fn status(&self) -> Result<BrokerStatus> {
        self.request("GET", "/status", None::<&Value>, Duration::from_secs(10))
    }

    pub fn login(&self) -> Result<BrokerStatus> {
        self.request(
            "POST",
            "/login",
            Some(&json!({"explicit_user_action":true})),
            Duration::from_secs(330),
        )
    }

    pub fn logout(&self) -> Result<BrokerStatus> {
        self.request(
            "POST",
            "/logout",
            Some(&json!({"explicit_user_action":true})),
            Duration::from_secs(30),
        )
    }

    pub fn complete(&self, prompt: &str) -> Result<ProviderReply> {
        self.request(
            "POST",
            "/complete",
            Some(&json!({"explicit_send":true,"prompt":prompt})),
            Duration::from_secs(200),
        )
    }

    fn request<T: DeserializeOwned, B: Serialize>(
        &self,
        method: &str,
        path: &str,
        body: Option<&B>,
        timeout: Duration,
    ) -> Result<T> {
        let body = body
            .map(serde_json::to_vec)
            .transpose()
            .map_err(|_| BrokerError::new("BROKER_REQUEST_INVALID"))?
            .unwrap_or_default();
        if body.len() > MAX_REQUEST_BYTES {
            return Err(BrokerError::new("BROKER_REQUEST_OVERSIZE"));
        }
        let mut stream = UnixStream::connect(&self.socket_path)
            .map_err(|_| BrokerError::new("BROKER_UNAVAILABLE"))?;
        stream
            .set_read_timeout(Some(timeout))
            .map_err(|_| BrokerError::new("BROKER_UNAVAILABLE"))?;
        stream
            .set_write_timeout(Some(Duration::from_secs(10)))
            .map_err(|_| BrokerError::new("BROKER_UNAVAILABLE"))?;
        let header = format!(
            "{method} {path} HTTP/1.0\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
            body.len()
        );
        stream
            .write_all(header.as_bytes())
            .and_then(|_| stream.write_all(&body))
            .and_then(|_| stream.shutdown(std::net::Shutdown::Write))
            .map_err(|_| BrokerError::new("BROKER_UNAVAILABLE"))?;
        let mut response = Vec::new();
        stream
            .take(MAX_RESPONSE_BYTES as u64 + 1)
            .read_to_end(&mut response)
            .map_err(|_| BrokerError::new("BROKER_UNAVAILABLE"))?;
        if response.len() > MAX_RESPONSE_BYTES {
            return Err(BrokerError::new("BROKER_RESPONSE_OVERSIZE"));
        }
        let separator = response
            .windows(4)
            .position(|window| window == b"\r\n\r\n")
            .ok_or_else(|| BrokerError::new("BROKER_RESPONSE_INVALID"))?;
        let headers = std::str::from_utf8(&response[..separator])
            .map_err(|_| BrokerError::new("BROKER_RESPONSE_INVALID"))?;
        let status = headers
            .lines()
            .next()
            .and_then(|line| line.split_whitespace().nth(1))
            .and_then(|part| part.parse::<u16>().ok())
            .ok_or_else(|| BrokerError::new("BROKER_RESPONSE_INVALID"))?;
        let payload = &response[separator + 4..];
        if !(200..300).contains(&status) {
            let code = serde_json::from_slice::<Value>(payload)
                .ok()
                .and_then(|value| value.pointer("/error/code")?.as_str().map(str::to_owned));
            return Err(BrokerError::new(known_error_code(code.as_deref())));
        }
        serde_json::from_slice(payload).map_err(|_| BrokerError::new("BROKER_RESPONSE_INVALID"))
    }
}

pub fn serve(socket_path: &Path, broker: Arc<Broker>) -> Result<()> {
    if !socket_path.is_absolute() {
        return Err(BrokerError::new("BROKER_SOCKET_PATH_INVALID"));
    }
    if let Some(parent) = socket_path.parent() {
        fs::create_dir_all(parent).map_err(|_| BrokerError::new("BROKER_SOCKET_BIND_FAILED"))?;
    }
    match fs::symlink_metadata(socket_path) {
        Ok(metadata) if metadata.file_type().is_socket() => {
            fs::remove_file(socket_path)
                .map_err(|_| BrokerError::new("BROKER_SOCKET_BIND_FAILED"))?;
        }
        Ok(_) => return Err(BrokerError::new("BROKER_SOCKET_PATH_OCCUPIED")),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
        Err(_) => return Err(BrokerError::new("BROKER_SOCKET_BIND_FAILED")),
    }
    let listener = UnixListener::bind(socket_path)
        .map_err(|_| BrokerError::new("BROKER_SOCKET_BIND_FAILED"))?;
    fs::set_permissions(socket_path, fs::Permissions::from_mode(0o600))
        .map_err(|_| BrokerError::new("BROKER_SOCKET_PERMISSION_FAILED"))?;
    for stream in listener.incoming() {
        let Ok(stream) = stream else { continue };
        let broker = Arc::clone(&broker);
        std::thread::spawn(move || {
            let _ = handle_connection(&broker, stream);
        });
    }
    Ok(())
}

fn handle_connection(broker: &Broker, mut stream: UnixStream) -> Result<()> {
    stream
        .set_read_timeout(Some(Duration::from_secs(15)))
        .map_err(|_| BrokerError::new("BROKER_REQUEST_INVALID"))?;
    stream
        .set_write_timeout(Some(Duration::from_secs(15)))
        .map_err(|_| BrokerError::new("BROKER_REQUEST_INVALID"))?;
    let request = match read_request(&stream) {
        Ok(value) => value,
        Err(error) => {
            write_error(&mut stream, 400, error.code());
            return Err(error);
        }
    };
    let result = route(broker, &request);
    match result {
        Ok(value) => write_json(&mut stream, 200, &value),
        Err(error) => {
            let status = match error.code() {
                "OAUTH_NOT_CONNECTED" | "OAUTH_REFRESH_REQUIRED" => 401,
                "PROVIDER_BUSY" => 409,
                "BROKER_ROUTE_NOT_FOUND" => 404,
                "EXPLICIT_USER_ACTION_REQUIRED"
                | "EXPLICIT_SEND_REQUIRED"
                | "BROKER_REQUEST_INVALID"
                | "PROVIDER_PROMPT_INVALID" => 400,
                _ => 503,
            };
            write_error(&mut stream, status, error.code());
            Err(error)
        }
    }
}

fn read_request(stream: &UnixStream) -> Result<Request> {
    let clone = stream
        .try_clone()
        .map_err(|_| BrokerError::new("BROKER_REQUEST_INVALID"))?;
    let mut reader = BufReader::new(clone);
    let mut header_bytes = 0_usize;
    let mut first = String::new();
    reader
        .read_line(&mut first)
        .map_err(|_| BrokerError::new("BROKER_REQUEST_INVALID"))?;
    header_bytes += first.len();
    if first.is_empty() || header_bytes > MAX_HEADER_BYTES {
        return Err(BrokerError::new("BROKER_REQUEST_INVALID"));
    }
    let mut parts = first.split_whitespace();
    let method = parts.next().unwrap_or_default();
    let path = parts.next().unwrap_or_default();
    let version = parts.next().unwrap_or_default();
    if !matches!(method, "GET" | "POST")
        || !path.starts_with('/')
        || path.contains('?')
        || version != "HTTP/1.0"
        || parts.next().is_some()
    {
        return Err(BrokerError::new("BROKER_REQUEST_INVALID"));
    }
    let mut content_length = None;
    loop {
        let mut line = String::new();
        reader
            .read_line(&mut line)
            .map_err(|_| BrokerError::new("BROKER_REQUEST_INVALID"))?;
        header_bytes += line.len();
        if line.is_empty() || header_bytes > MAX_HEADER_BYTES {
            return Err(BrokerError::new("BROKER_REQUEST_INVALID"));
        }
        if line == "\r\n" {
            break;
        }
        let (name, value) = line
            .trim_end_matches(['\r', '\n'])
            .split_once(':')
            .ok_or_else(|| BrokerError::new("BROKER_REQUEST_INVALID"))?;
        if name.eq_ignore_ascii_case("transfer-encoding") {
            return Err(BrokerError::new("BROKER_REQUEST_INVALID"));
        }
        if name.eq_ignore_ascii_case("content-length") {
            if content_length.is_some() {
                return Err(BrokerError::new("BROKER_REQUEST_INVALID"));
            }
            let length = value
                .trim()
                .parse::<usize>()
                .map_err(|_| BrokerError::new("BROKER_REQUEST_INVALID"))?;
            if length > MAX_REQUEST_BYTES {
                return Err(BrokerError::new("BROKER_REQUEST_OVERSIZE"));
            }
            content_length = Some(length);
        }
    }
    let length = content_length.unwrap_or(0);
    if method == "GET" && length != 0 {
        return Err(BrokerError::new("BROKER_REQUEST_INVALID"));
    }
    let mut body = vec![0_u8; length];
    reader
        .read_exact(&mut body)
        .map_err(|_| BrokerError::new("BROKER_REQUEST_INVALID"))?;
    Ok(Request {
        method: method.into(),
        path: path.into(),
        body,
    })
}

fn route(broker: &Broker, request: &Request) -> Result<Value> {
    match (request.method.as_str(), request.path.as_str()) {
        ("GET", "/health") => Ok(json!({"ok":true,"protocol":BROKER_PROTOCOL_VERSION})),
        ("GET", "/status") => serde_json::to_value(broker.status())
            .map_err(|_| BrokerError::new("BROKER_RESPONSE_INVALID")),
        ("POST", "/login") => {
            let action: ExplicitAction = parse_body(&request.body)?;
            if !action.explicit_user_action {
                return Err(BrokerError::new("EXPLICIT_USER_ACTION_REQUIRED"));
            }
            serde_json::to_value(broker.login()?)
                .map_err(|_| BrokerError::new("BROKER_RESPONSE_INVALID"))
        }
        ("POST", "/logout") => {
            let action: ExplicitAction = parse_body(&request.body)?;
            if !action.explicit_user_action {
                return Err(BrokerError::new("EXPLICIT_USER_ACTION_REQUIRED"));
            }
            serde_json::to_value(broker.logout()?)
                .map_err(|_| BrokerError::new("BROKER_RESPONSE_INVALID"))
        }
        ("POST", "/complete") => {
            let completion: CompletionRequest = parse_body(&request.body)?;
            if !completion.explicit_send {
                return Err(BrokerError::new("EXPLICIT_SEND_REQUIRED"));
            }
            serde_json::to_value(broker.complete(&completion.prompt)?)
                .map_err(|_| BrokerError::new("BROKER_RESPONSE_INVALID"))
        }
        _ => Err(BrokerError::new("BROKER_ROUTE_NOT_FOUND")),
    }
}

fn parse_body<T: DeserializeOwned>(body: &[u8]) -> Result<T> {
    if body.is_empty() {
        return Err(BrokerError::new("BROKER_REQUEST_INVALID"));
    }
    serde_json::from_slice(body).map_err(|_| BrokerError::new("BROKER_REQUEST_INVALID"))
}

fn write_json(stream: &mut UnixStream, status: u16, value: &Value) -> Result<()> {
    let body =
        serde_json::to_vec(value).map_err(|_| BrokerError::new("BROKER_RESPONSE_INVALID"))?;
    if body.len() > MAX_RESPONSE_BYTES {
        return Err(BrokerError::new("BROKER_RESPONSE_OVERSIZE"));
    }
    let reason = if status == 200 { "OK" } else { "Error" };
    let header = format!(
        "HTTP/1.0 {status} {reason}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n",
        body.len()
    );
    stream
        .write_all(header.as_bytes())
        .and_then(|_| stream.write_all(&body))
        .and_then(|_| stream.flush())
        .map_err(|_| BrokerError::new("BROKER_RESPONSE_WRITE_FAILED"))
}

fn write_error(stream: &mut UnixStream, status: u16, code: &'static str) {
    let body = serde_json::to_value(ErrorBody {
        ok: false,
        protocol: BROKER_PROTOCOL_VERSION,
        error: ErrorCode { code },
    })
    .unwrap_or_else(|_| json!({"ok":false}));
    let _ = write_json(stream, status, &body);
}

fn known_error_code(code: Option<&str>) -> &'static str {
    match code {
        Some("OAUTH_NOT_CONNECTED") => "OAUTH_NOT_CONNECTED",
        Some("OAUTH_REFRESH_REQUIRED") => "OAUTH_REFRESH_REQUIRED",
        Some("PROVIDER_BUSY") => "PROVIDER_BUSY",
        Some("PROVIDER_PROMPT_INVALID") => "PROVIDER_PROMPT_INVALID",
        Some("EXPLICIT_USER_ACTION_REQUIRED") => "EXPLICIT_USER_ACTION_REQUIRED",
        Some("EXPLICIT_SEND_REQUIRED") => "EXPLICIT_SEND_REQUIRED",
        Some("OAUTH_LOGIN_TIMEOUT") => "OAUTH_LOGIN_TIMEOUT",
        Some("OAUTH_CALLBACK_PORT_UNAVAILABLE") => "OAUTH_CALLBACK_PORT_UNAVAILABLE",
        Some("OAUTH_AUTHORIZATION_DENIED") => "OAUTH_AUTHORIZATION_DENIED",
        Some("OAUTH_TOKEN_EXCHANGE_FAILED") => "OAUTH_TOKEN_EXCHANGE_FAILED",
        Some("OAUTH_ID_TOKEN_INVALID") => "OAUTH_ID_TOKEN_INVALID",
        Some("OAUTH_ID_TOKEN_NONCE_MISMATCH") => "OAUTH_ID_TOKEN_NONCE_MISMATCH",
        Some("OAUTH_KEYCHAIN_UNAVAILABLE") => "OAUTH_KEYCHAIN_UNAVAILABLE",
        Some("OAUTH_KEYCHAIN_READ_FAILED") => "OAUTH_KEYCHAIN_READ_FAILED",
        Some("OAUTH_KEYCHAIN_WRITE_FAILED") => "OAUTH_KEYCHAIN_WRITE_FAILED",
        Some("OAUTH_KEYCHAIN_DELETE_FAILED") => "OAUTH_KEYCHAIN_DELETE_FAILED",
        Some("OAUTH_REFRESH_FAILED") => "OAUTH_REFRESH_FAILED",
        Some("PROVIDER_REQUEST_FAILED") => "PROVIDER_REQUEST_FAILED",
        Some("PROVIDER_RESPONSE_INVALID") => "PROVIDER_RESPONSE_INVALID",
        Some("PROVIDER_EMPTY_OR_OVERSIZE_RESPONSE") => "PROVIDER_EMPTY_OR_OVERSIZE_RESPONSE",
        _ => "BROKER_REQUEST_FAILED",
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::BrokerConfig;
    use crate::store::MemoryStore;

    fn exchange(request: &[u8]) -> Vec<u8> {
        let broker =
            Broker::with_store(BrokerConfig::default(), Arc::new(MemoryStore::default())).unwrap();
        let (mut client, server) = UnixStream::pair().unwrap();
        let worker = std::thread::spawn(move || {
            let _ = handle_connection(&broker, server);
        });
        client.write_all(request).unwrap();
        client.shutdown(std::net::Shutdown::Write).unwrap();
        let mut response = Vec::new();
        client.read_to_end(&mut response).unwrap();
        worker.join().unwrap();
        response
    }

    #[test]
    fn rejects_missing_explicit_send_without_echoing_prompt() {
        let body = br#"{"explicit_send":false,"prompt":"secret prompt marker"}"#;
        let request = format!(
            "POST /complete HTTP/1.0\r\nContent-Length: {}\r\n\r\n",
            body.len()
        );
        let mut bytes = request.into_bytes();
        bytes.extend_from_slice(body);
        let response = exchange(&bytes);
        let text = String::from_utf8(response).unwrap();
        assert!(text.contains("EXPLICIT_SEND_REQUIRED"));
        assert!(!text.contains("secret prompt marker"));
    }

    #[test]
    fn rejects_transfer_encoding_and_oversize_lengths() {
        let response = exchange(b"POST /login HTTP/1.0\r\nTransfer-Encoding: chunked\r\n\r\n");
        assert!(
            String::from_utf8(response)
                .unwrap()
                .contains("BROKER_REQUEST_INVALID")
        );
        let response = exchange(b"POST /login HTTP/1.0\r\nContent-Length: 999999\r\n\r\n");
        assert!(
            String::from_utf8(response)
                .unwrap()
                .contains("BROKER_REQUEST_OVERSIZE")
        );
    }
}
