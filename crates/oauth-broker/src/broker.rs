use crate::error::{BrokerError, Result};
use crate::model::{
    BrokerStatus, CredentialRecord, IdClaims, ProviderReply, SseEvent, TokenResponse,
};
use crate::store::{CredentialStore, KeychainStore};
use crate::{CALLBACK_PORT, DEFAULT_CLIENT_ID, DEFAULT_MODEL};
use base64::Engine;
use jsonwebtoken::jwk::JwkSet;
use jsonwebtoken::{Algorithm, DecodingKey, Validation, decode, decode_header};
use reqwest::blocking::Client;
use reqwest::redirect::Policy;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::process::Command;
use std::sync::{Arc, Mutex};
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use url::Url;
use zeroize::Zeroizing;

const AUTH_ENDPOINT: &str = "https://auth.openai.com/oauth/authorize";
const TOKEN_ENDPOINT: &str = "https://auth.openai.com/oauth/token";
const REVOKE_ENDPOINT: &str = "https://auth.openai.com/oauth/revoke";
const JWKS_ENDPOINT: &str = "https://auth.openai.com/.well-known/jwks.json";
const RESPONSES_ENDPOINT: &str = "https://chatgpt.com/backend-api/codex/responses";
const REFRESH_MARGIN_MS: i64 = 20 * 60 * 1000;
const LOGIN_TIMEOUT: Duration = Duration::from_secs(5 * 60);
const MAX_PROMPT_CHARS: usize = 48_000;
const MAX_REPLY_BYTES: usize = 512_000;

#[derive(Clone)]
pub struct BrokerConfig {
    pub client_id: String,
    pub model: String,
    auth_endpoint: String,
    token_endpoint: String,
    revoke_endpoint: String,
    jwks_endpoint: String,
    responses_endpoint: String,
    callback_port: u16,
    open_browser: bool,
}

impl Default for BrokerConfig {
    fn default() -> Self {
        Self {
            client_id: std::env::var("TOM_ASSIST_OPENAI_OAUTH_CLIENT_ID")
                .unwrap_or_else(|_| DEFAULT_CLIENT_ID.into()),
            model: std::env::var("TOM_ASSIST_OAUTH_MODEL").unwrap_or_else(|_| DEFAULT_MODEL.into()),
            auth_endpoint: AUTH_ENDPOINT.into(),
            token_endpoint: TOKEN_ENDPOINT.into(),
            revoke_endpoint: REVOKE_ENDPOINT.into(),
            jwks_endpoint: JWKS_ENDPOINT.into(),
            responses_endpoint: RESPONSES_ENDPOINT.into(),
            callback_port: CALLBACK_PORT,
            open_browser: true,
        }
    }
}

pub struct Broker {
    config: BrokerConfig,
    client: Client,
    store: Arc<dyn CredentialStore>,
    credential: Mutex<Option<CredentialRecord>>,
    generation_slot: Mutex<()>,
}

impl Broker {
    pub fn new(config: BrokerConfig) -> Result<Self> {
        Self::with_store(config, Arc::new(KeychainStore::default()))
    }

    pub(crate) fn with_store(
        config: BrokerConfig,
        store: Arc<dyn CredentialStore>,
    ) -> Result<Self> {
        validate_config(&config)?;
        let client = Client::builder()
            .redirect(Policy::none())
            .no_proxy()
            .connect_timeout(Duration::from_secs(10))
            .timeout(Duration::from_secs(180))
            .build()
            .map_err(|_| BrokerError::new("OAUTH_HTTP_CLIENT_FAILED"))?;
        let credential = store.load()?;
        Ok(Self {
            config,
            client,
            store,
            credential: Mutex::new(credential),
            generation_slot: Mutex::new(()),
        })
    }

    pub fn status(&self) -> BrokerStatus {
        let now = now_ms();
        let credential = self.credential.lock().expect("credential mutex poisoned");
        let (connected, code) = match credential.as_ref() {
            Some(record) if record.valid_shape() && record.expires_at_ms > now => {
                (true, "OAUTH_READY")
            }
            Some(record) if record.valid_shape() => (true, "OAUTH_REFRESH_REQUIRED"),
            Some(_) => (false, "OAUTH_CREDENTIAL_INVALID"),
            None => (false, "OAUTH_NOT_CONNECTED"),
        };
        BrokerStatus {
            connected,
            code: code.into(),
            credential_owner: "tom-assist-keychain".into(),
            model: self.config.model.clone(),
            streaming: false,
            capabilities: json!({
                "provider_surface":"tom-assist/openai-oauth",
                "visible_prompt_injection":true,
                "response_capture":true,
                "hidden_context_visibility":false,
                "model_internal_bias":"none",
                "supports_system_field":false
            }),
        }
    }

    pub fn login(&self) -> Result<BrokerStatus> {
        let verifier = random_base64url::<96>()?;
        let state = random_base64url::<32>()?;
        let nonce = random_base64url::<32>()?;
        let challenge = base64::engine::general_purpose::URL_SAFE_NO_PAD
            .encode(Sha256::digest(verifier.as_bytes()));
        let redirect_uri = format!(
            "http://localhost:{}/auth/callback",
            self.config.callback_port
        );
        let listener = TcpListener::bind(("127.0.0.1", self.config.callback_port))
            .map_err(|_| BrokerError::new("OAUTH_CALLBACK_PORT_UNAVAILABLE"))?;
        listener
            .set_nonblocking(true)
            .map_err(|_| BrokerError::new("OAUTH_CALLBACK_FAILED"))?;
        let authorization_url =
            self.authorization_url(&challenge, &state, &nonce, &redirect_uri)?;
        if self.config.open_browser {
            Command::new("/usr/bin/open")
                .arg(authorization_url.as_str())
                .spawn()
                .map_err(|_| BrokerError::new("OAUTH_BROWSER_OPEN_FAILED"))?;
        }

        let deadline = std::time::Instant::now() + LOGIN_TIMEOUT;
        let callback = loop {
            if std::time::Instant::now() >= deadline {
                return Err(BrokerError::new("OAUTH_LOGIN_TIMEOUT"));
            }
            match listener.accept() {
                Ok((mut stream, _)) => {
                    stream.set_read_timeout(Some(Duration::from_secs(5))).ok();
                    let parsed = parse_callback(&mut stream, &state);
                    let success = parsed.is_ok();
                    serve_callback_page(&mut stream, success);
                    match parsed {
                        Ok(code) => break code,
                        Err(error)
                            if matches!(
                                error.code(),
                                "OAUTH_CALLBACK_INVALID" | "OAUTH_STATE_MISMATCH"
                            ) =>
                        {
                            continue;
                        }
                        Err(error) => return Err(error),
                    }
                }
                Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                    std::thread::sleep(Duration::from_millis(50));
                }
                Err(_) => return Err(BrokerError::new("OAUTH_CALLBACK_FAILED")),
            }
        };

        let mut token: TokenResponse = self
            .client
            .post(&self.config.token_endpoint)
            .form(&[
                ("grant_type", "authorization_code"),
                ("client_id", self.config.client_id.as_str()),
                ("code", callback.as_str()),
                ("redirect_uri", redirect_uri.as_str()),
                ("code_verifier", verifier.as_str()),
            ])
            .timeout(Duration::from_secs(20))
            .send()
            .map_err(|_| BrokerError::new("OAUTH_TOKEN_EXCHANGE_FAILED"))?
            .error_for_status()
            .map_err(|_| BrokerError::new("OAUTH_TOKEN_EXCHANGE_FAILED"))?
            .json()
            .map_err(|_| BrokerError::new("OAUTH_TOKEN_RESPONSE_INVALID"))?;
        let id_token = token
            .id_token
            .as_deref()
            .ok_or_else(|| BrokerError::new("OAUTH_ID_TOKEN_MISSING"))?;
        let account_id = self.validate_id_token(id_token, &nonce)?;
        let record = CredentialRecord {
            schema_version: 1,
            access_token: std::mem::take(&mut token.access_token),
            refresh_token: token
                .refresh_token
                .take()
                .ok_or_else(|| BrokerError::new("OAUTH_REFRESH_TOKEN_MISSING"))?,
            expires_at_ms: now_ms() + token.expires_in.unwrap_or(3600).max(60) * 1000,
            chatgpt_account_id: account_id,
        };
        if !record.valid_shape() {
            return Err(BrokerError::new("OAUTH_TOKEN_RESPONSE_INVALID"));
        }
        self.store.save(&record)?;
        *self.credential.lock().expect("credential mutex poisoned") = Some(record);
        Ok(self.status())
    }

    pub fn logout(&self) -> Result<BrokerStatus> {
        let previous = self
            .credential
            .lock()
            .expect("credential mutex poisoned")
            .take();
        if let Some(record) = previous.as_ref() {
            let _ = self
                .client
                .post(&self.config.revoke_endpoint)
                .json(&json!({
                    "client_id":self.config.client_id,
                    "token":record.refresh_token,
                    "token_type_hint":"refresh_token"
                }))
                .timeout(Duration::from_secs(15))
                .send();
        }
        self.store.clear()?;
        Ok(self.status())
    }

    pub fn complete(&self, prompt: &str) -> Result<ProviderReply> {
        self.complete_request(prompt, None)
    }

    pub fn complete_structured(
        &self,
        prompt: &str,
        response_format: &Value,
    ) -> Result<ProviderReply> {
        validate_response_format(response_format)?;
        self.complete_request(prompt, Some(response_format))
    }

    fn complete_request(
        &self,
        prompt: &str,
        response_format: Option<&Value>,
    ) -> Result<ProviderReply> {
        if prompt.trim().is_empty() || prompt.chars().count() > MAX_PROMPT_CHARS {
            return Err(BrokerError::new("PROVIDER_PROMPT_INVALID"));
        }
        let _slot = self
            .generation_slot
            .try_lock()
            .map_err(|_| BrokerError::new("PROVIDER_BUSY"))?;
        self.ensure_fresh()?;
        let credential = self
            .credential
            .lock()
            .expect("credential mutex poisoned")
            .clone()
            .ok_or_else(|| BrokerError::new("OAUTH_NOT_CONNECTED"))?;
        let mut payload = json!({
            "model":self.config.model,
            "input":[{"role":"user","content":prompt}],
            "instructions":"You are a helpful assistant.",
            "store":false,
            "stream":true
        });
        if let Some(format) = response_format {
            payload["instructions"] = Value::String(
                "Extract only source-backed structure and return the required schema. Do not answer the user."
                    .into(),
            );
            payload["max_output_tokens"] = Value::from(8192_u64);
            payload["text"] = json!({"format":format});
        }
        let response = self
            .client
            .post(&self.config.responses_endpoint)
            .bearer_auth(&credential.access_token)
            .header("ChatGPT-Account-Id", &credential.chatgpt_account_id)
            .json(&payload)
            .timeout(Duration::from_secs(180))
            .send()
            .map_err(|_| BrokerError::new("PROVIDER_REQUEST_FAILED"))?
            .error_for_status()
            .map_err(|_| BrokerError::new("PROVIDER_REQUEST_FAILED"))?;
        let text = parse_sse(response)?;
        Ok(ProviderReply {
            text,
            model: self.config.model.clone(),
            complete: true,
        })
    }

    fn ensure_fresh(&self) -> Result<()> {
        let needs_refresh = {
            let credential = self.credential.lock().expect("credential mutex poisoned");
            match credential.as_ref() {
                Some(record) => record.expires_at_ms <= now_ms() + REFRESH_MARGIN_MS,
                None => return Err(BrokerError::new("OAUTH_NOT_CONNECTED")),
            }
        };
        if !needs_refresh {
            return Ok(());
        }
        let current = self
            .credential
            .lock()
            .expect("credential mutex poisoned")
            .clone()
            .ok_or_else(|| BrokerError::new("OAUTH_NOT_CONNECTED"))?;
        let mut token: TokenResponse = self
            .client
            .post(&self.config.token_endpoint)
            .json(&json!({
                "grant_type":"refresh_token",
                "client_id":self.config.client_id,
                "refresh_token":current.refresh_token
            }))
            .timeout(Duration::from_secs(20))
            .send()
            .map_err(|_| BrokerError::new("OAUTH_REFRESH_FAILED"))?
            .error_for_status()
            .map_err(|_| BrokerError::new("OAUTH_REFRESH_FAILED"))?
            .json()
            .map_err(|_| BrokerError::new("OAUTH_REFRESH_RESPONSE_INVALID"))?;
        if token.access_token.len() < 20 {
            return Err(BrokerError::new("OAUTH_REFRESH_RESPONSE_INVALID"));
        }
        let refreshed = CredentialRecord {
            schema_version: 1,
            access_token: std::mem::take(&mut token.access_token),
            refresh_token: token
                .refresh_token
                .take()
                .unwrap_or(current.refresh_token.clone()),
            expires_at_ms: now_ms() + token.expires_in.unwrap_or(3600).max(60) * 1000,
            chatgpt_account_id: current.chatgpt_account_id.clone(),
        };
        self.store.save(&refreshed)?;
        *self.credential.lock().expect("credential mutex poisoned") = Some(refreshed);
        Ok(())
    }

    fn authorization_url(
        &self,
        challenge: &str,
        state: &str,
        nonce: &str,
        redirect_uri: &str,
    ) -> Result<Url> {
        let mut url = Url::parse(&self.config.auth_endpoint)
            .map_err(|_| BrokerError::new("OAUTH_CONFIGURATION_INVALID"))?;
        url.query_pairs_mut()
            .append_pair("client_id", &self.config.client_id)
            .append_pair("redirect_uri", redirect_uri)
            .append_pair("response_type", "code")
            .append_pair("scope", "openid profile email offline_access")
            .append_pair("code_challenge", challenge)
            .append_pair("code_challenge_method", "S256")
            .append_pair("state", state)
            .append_pair("nonce", nonce)
            .append_pair("id_token_add_organizations", "true")
            .append_pair("codex_cli_simplified_flow", "true")
            .append_pair("originator", "codex_cli");
        Ok(url)
    }

    fn validate_id_token(&self, token: &str, expected_nonce: &str) -> Result<String> {
        let header =
            decode_header(token).map_err(|_| BrokerError::new("OAUTH_ID_TOKEN_INVALID"))?;
        if header.alg != Algorithm::RS256 {
            return Err(BrokerError::new("OAUTH_ID_TOKEN_INVALID"));
        }
        if header.kid.is_none() {
            return Err(BrokerError::new("OAUTH_ID_TOKEN_INVALID"));
        }
        let jwks: JwkSet = self
            .client
            .get(&self.config.jwks_endpoint)
            .timeout(Duration::from_secs(10))
            .send()
            .map_err(|_| BrokerError::new("OAUTH_JWKS_UNAVAILABLE"))?
            .error_for_status()
            .map_err(|_| BrokerError::new("OAUTH_JWKS_UNAVAILABLE"))?
            .json()
            .map_err(|_| BrokerError::new("OAUTH_JWKS_INVALID"))?;
        validate_id_token_with_jwks(token, expected_nonce, &self.config.client_id, &jwks)
    }
}

fn validate_response_format(value: &Value) -> Result<()> {
    let object = value
        .as_object()
        .ok_or_else(|| BrokerError::new("PROVIDER_RESPONSE_FORMAT_INVALID"))?;
    if object.len() != 4
        || value.get("type").and_then(Value::as_str) != Some("json_schema")
        || value.get("strict").and_then(Value::as_bool) != Some(true)
        || !value.get("schema").is_some_and(Value::is_object)
    {
        return Err(BrokerError::new("PROVIDER_RESPONSE_FORMAT_INVALID"));
    }
    let name = value
        .get("name")
        .and_then(Value::as_str)
        .unwrap_or_default();
    if name.is_empty()
        || name.len() > 64
        || !name
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-'))
        || serde_json::to_vec(value)
            .map(|encoded| encoded.len() > 128 * 1024)
            .unwrap_or(true)
    {
        return Err(BrokerError::new("PROVIDER_RESPONSE_FORMAT_INVALID"));
    }
    Ok(())
}

fn validate_id_token_with_jwks(
    token: &str,
    expected_nonce: &str,
    client_id: &str,
    jwks: &JwkSet,
) -> Result<String> {
    let header = decode_header(token).map_err(|_| BrokerError::new("OAUTH_ID_TOKEN_INVALID"))?;
    if header.alg != Algorithm::RS256 {
        return Err(BrokerError::new("OAUTH_ID_TOKEN_INVALID"));
    }
    let kid = header
        .kid
        .as_deref()
        .ok_or_else(|| BrokerError::new("OAUTH_ID_TOKEN_INVALID"))?;
    let jwk = jwks
        .find(kid)
        .ok_or_else(|| BrokerError::new("OAUTH_JWKS_KEY_MISSING"))?;
    let key = DecodingKey::from_jwk(jwk).map_err(|_| BrokerError::new("OAUTH_JWKS_INVALID"))?;
    let mut validation = Validation::new(Algorithm::RS256);
    validation.set_issuer(&["https://auth.openai.com"]);
    validation.set_audience(&[client_id]);
    validation.leeway = 60;
    let claims = decode::<IdClaims>(token, &key, &validation)
        .map_err(|_| BrokerError::new("OAUTH_ID_TOKEN_INVALID"))?
        .claims;
    if claims.nonce.as_deref() != Some(expected_nonce) {
        return Err(BrokerError::new("OAUTH_ID_TOKEN_NONCE_MISMATCH"));
    }
    claims
        .auth
        .chatgpt_account_id
        .or(claims.auth.account_id)
        .filter(|value| !value.trim().is_empty() && value.len() <= 256)
        .ok_or_else(|| BrokerError::new("OAUTH_ACCOUNT_ID_MISSING"))
}

fn validate_config(config: &BrokerConfig) -> Result<()> {
    if config.client_id.trim().is_empty()
        || config.client_id.len() > 256
        || config.model.trim().is_empty()
        || config.model.len() > 128
    {
        return Err(BrokerError::new("OAUTH_CONFIGURATION_INVALID"));
    }
    for endpoint in [
        &config.auth_endpoint,
        &config.token_endpoint,
        &config.revoke_endpoint,
        &config.jwks_endpoint,
        &config.responses_endpoint,
    ] {
        let url =
            Url::parse(endpoint).map_err(|_| BrokerError::new("OAUTH_CONFIGURATION_INVALID"))?;
        if url.scheme() != "https" || url.host_str().is_none() {
            return Err(BrokerError::new("OAUTH_CONFIGURATION_INVALID"));
        }
    }
    if config.callback_port == 0 || config.callback_port == 18790 {
        return Err(BrokerError::new("OAUTH_CONFIGURATION_INVALID"));
    }
    Ok(())
}

fn random_base64url<const N: usize>() -> Result<String> {
    let mut bytes = Zeroizing::new([0_u8; N]);
    getrandom::fill(bytes.as_mut()).map_err(|_| BrokerError::new("OAUTH_RANDOM_FAILED"))?;
    Ok(base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(bytes.as_ref()))
}

fn parse_callback(stream: &mut TcpStream, expected_state: &str) -> Result<String> {
    let mut reader = BufReader::new(
        stream
            .try_clone()
            .map_err(|_| BrokerError::new("OAUTH_CALLBACK_FAILED"))?,
    );
    let mut first_line = String::new();
    reader
        .by_ref()
        .take(8193)
        .read_line(&mut first_line)
        .map_err(|_| BrokerError::new("OAUTH_CALLBACK_FAILED"))?;
    if first_line.len() > 8192 {
        return Err(BrokerError::new("OAUTH_CALLBACK_INVALID"));
    }
    parse_callback_request_line(&first_line, expected_state)
}

fn parse_callback_request_line(first_line: &str, expected_state: &str) -> Result<String> {
    let mut parts = first_line.split_whitespace();
    if parts.next() != Some("GET") {
        return Err(BrokerError::new("OAUTH_CALLBACK_INVALID"));
    }
    let target = parts
        .next()
        .ok_or_else(|| BrokerError::new("OAUTH_CALLBACK_INVALID"))?;
    let url = Url::parse(&format!("http://localhost{target}"))
        .map_err(|_| BrokerError::new("OAUTH_CALLBACK_INVALID"))?;
    if url.path() != "/auth/callback" {
        return Err(BrokerError::new("OAUTH_CALLBACK_INVALID"));
    }
    let state = url
        .query_pairs()
        .find(|(key, _)| key == "state")
        .map(|(_, value)| value.into_owned());
    if state.as_deref() != Some(expected_state) {
        return Err(BrokerError::new("OAUTH_STATE_MISMATCH"));
    }
    url.query_pairs()
        .find(|(key, _)| key == "code")
        .map(|(_, value)| value.into_owned())
        .filter(|value| !value.is_empty() && value.len() <= 4096)
        .ok_or_else(|| BrokerError::new("OAUTH_AUTHORIZATION_DENIED"))
}

fn serve_callback_page(stream: &mut TcpStream, success: bool) {
    let title = if success {
        "Authentication successful"
    } else {
        "Authentication failed"
    };
    let body = format!(
        "<!doctype html><meta charset=utf-8><title>{title}</title><h1>{title}</h1><p>You may close this tab and return to Tom Assist.</p>"
    );
    let response = format!(
        "HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {}\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n{}",
        body.len(),
        body
    );
    let _ = stream.write_all(response.as_bytes());
}

fn parse_sse(response: reqwest::blocking::Response) -> Result<String> {
    let mut text = String::new();
    let mut completed: Option<Value> = None;
    let reader = BufReader::new(response);
    for line in reader.lines() {
        let line = line.map_err(|_| BrokerError::new("PROVIDER_RESPONSE_INVALID"))?;
        let Some(payload) = line.strip_prefix("data: ") else {
            continue;
        };
        if payload == "[DONE]" {
            break;
        }
        let event: SseEvent = serde_json::from_str(payload)
            .map_err(|_| BrokerError::new("PROVIDER_RESPONSE_INVALID"))?;
        if event.event_type == "response.output_text.delta" {
            if let Some(delta) = event.delta {
                text.push_str(&delta);
            }
        } else if event.event_type == "response.completed" {
            completed = event.response;
        }
        if text.len() > MAX_REPLY_BYTES {
            return Err(BrokerError::new("PROVIDER_RESPONSE_OVERSIZE"));
        }
    }
    if text.trim().is_empty() {
        if let Some(response) = completed.as_ref() {
            text = extract_output_text(response).unwrap_or_default();
        }
    }
    if text.trim().is_empty() || text.len() > MAX_REPLY_BYTES {
        return Err(BrokerError::new("PROVIDER_EMPTY_OR_OVERSIZE_RESPONSE"));
    }
    Ok(text)
}

fn extract_output_text(response: &Value) -> Option<String> {
    if let Some(value) = response.get("output_text").and_then(Value::as_str) {
        if !value.is_empty() {
            return Some(value.into());
        }
    }
    for item in response.get("output")?.as_array()? {
        for content in item.get("content")?.as_array()? {
            if let Some(value) = content.get("text").and_then(Value::as_str) {
                if !value.is_empty() {
                    return Some(value.into());
                }
            }
        }
    }
    None
}

fn now_ms() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis()
        .try_into()
        .unwrap_or(i64::MAX)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::store::MemoryStore;
    use jsonwebtoken::{EncodingKey, Header, encode};
    use rand::rngs::OsRng;
    use rsa::RsaPrivateKey;
    use rsa::pkcs1::EncodeRsaPrivateKey;
    use rsa::traits::PublicKeyParts;

    fn jwks_for(key: &RsaPrivateKey, kid: &str) -> JwkSet {
        serde_json::from_value(json!({"keys":[{
            "kty":"RSA",
            "kid":kid,
            "alg":"RS256",
            "use":"sig",
            "n":base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(key.n().to_bytes_be()),
            "e":base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(key.e().to_bytes_be())
        }]}))
        .unwrap()
    }

    fn signed_token(key: &RsaPrivateKey, kid: &str, claims: Value) -> String {
        let der = key.to_pkcs1_der().unwrap();
        let mut header = Header::new(Algorithm::RS256);
        header.kid = Some(kid.into());
        encode(&header, &claims, &EncodingKey::from_rsa_der(der.as_bytes())).unwrap()
    }

    #[test]
    fn authorization_url_is_pkce_state_nonce_and_compatibility_originated() {
        let mut config = BrokerConfig::default();
        config.open_browser = false;
        let broker = Broker::with_store(config, Arc::new(MemoryStore::default())).unwrap();
        let url = broker
            .authorization_url(
                "challenge",
                "state",
                "nonce",
                "http://localhost:1455/auth/callback",
            )
            .unwrap();
        let query: std::collections::HashMap<_, _> = url.query_pairs().into_owned().collect();
        assert_eq!(query["code_challenge_method"], "S256");
        assert_eq!(query["state"], "state");
        assert_eq!(query["nonce"], "nonce");
        assert_eq!(query["originator"], "codex_cli");
        assert_eq!(query["scope"], "openid profile email offline_access");
    }

    #[test]
    fn status_is_secret_free_and_never_refreshes() {
        let store = Arc::new(MemoryStore::default());
        store
            .save(&CredentialRecord {
                schema_version: 1,
                access_token: "a".repeat(32),
                refresh_token: "r".repeat(32),
                expires_at_ms: now_ms() + 3_600_000,
                chatgpt_account_id: "account-private".into(),
            })
            .unwrap();
        let broker = Broker::with_store(BrokerConfig::default(), store).unwrap();
        let serialized = serde_json::to_string(&broker.status()).unwrap();
        assert!(broker.status().connected);
        assert!(!serialized.contains(&"a".repeat(32)));
        assert!(!serialized.contains("account-private"));
        assert_eq!(broker.status().credential_owner, "tom-assist-keychain");
    }

    #[test]
    fn expired_access_token_stays_send_eligible_for_explicit_refresh() {
        let store = Arc::new(MemoryStore::default());
        store
            .save(&CredentialRecord {
                schema_version: 1,
                access_token: "a".repeat(32),
                refresh_token: "r".repeat(32),
                expires_at_ms: now_ms() - 1,
                chatgpt_account_id: "account-private".into(),
            })
            .unwrap();
        let broker = Broker::with_store(BrokerConfig::default(), store).unwrap();
        assert!(broker.status().connected);
        assert_eq!(broker.status().code, "OAUTH_REFRESH_REQUIRED");
    }

    #[test]
    fn id_token_requires_signature_issuer_audience_expiry_and_nonce() {
        let key = RsaPrivateKey::new(&mut OsRng, 2048).unwrap();
        let jwks = jwks_for(&key, "primary");
        let now = now_ms() / 1000;
        let claims = json!({
            "iss":"https://auth.openai.com",
            "aud":DEFAULT_CLIENT_ID,
            "exp":now + 3600,
            "nonce":"expected-nonce",
            "https://api.openai.com/auth":{"chatgpt_account_id":"account-test"}
        });
        let token = signed_token(&key, "primary", claims.clone());
        assert_eq!(
            validate_id_token_with_jwks(&token, "expected-nonce", DEFAULT_CLIENT_ID, &jwks)
                .unwrap(),
            "account-test"
        );
        assert_eq!(
            validate_id_token_with_jwks(&token, "wrong", DEFAULT_CLIENT_ID, &jwks)
                .unwrap_err()
                .code(),
            "OAUTH_ID_TOKEN_NONCE_MISMATCH"
        );
        for invalid in [
            json!({
                "iss":"https://not-the-issuer.invalid","aud":DEFAULT_CLIENT_ID,
                "exp":now + 3600,"nonce":"expected-nonce",
                "https://api.openai.com/auth":{"chatgpt_account_id":"account-test"}
            }),
            json!({
                "iss":"https://auth.openai.com","aud":"wrong-client",
                "exp":now + 3600,"nonce":"expected-nonce",
                "https://api.openai.com/auth":{"chatgpt_account_id":"account-test"}
            }),
            json!({
                "iss":"https://auth.openai.com","aud":DEFAULT_CLIENT_ID,
                "exp":now - 120,"nonce":"expected-nonce",
                "https://api.openai.com/auth":{"chatgpt_account_id":"account-test"}
            }),
        ] {
            let token = signed_token(&key, "primary", invalid);
            assert_eq!(
                validate_id_token_with_jwks(&token, "expected-nonce", DEFAULT_CLIENT_ID, &jwks)
                    .unwrap_err()
                    .code(),
                "OAUTH_ID_TOKEN_INVALID"
            );
        }
        let other_key = RsaPrivateKey::new(&mut OsRng, 2048).unwrap();
        assert_eq!(
            validate_id_token_with_jwks(
                &token,
                "expected-nonce",
                DEFAULT_CLIENT_ID,
                &jwks_for(&other_key, "primary")
            )
            .unwrap_err()
            .code(),
            "OAUTH_ID_TOKEN_INVALID"
        );
    }

    #[test]
    fn callback_requires_exact_path_method_and_state() {
        assert_eq!(
            parse_callback_request_line(
                "GET /auth/callback?code=abc&state=good HTTP/1.0\r\n\r\n",
                "good"
            )
            .unwrap(),
            "abc"
        );
        assert_eq!(
            parse_callback_request_line(
                "GET /auth/callback?code=abc&state=bad HTTP/1.0\r\n\r\n",
                "good"
            )
            .unwrap_err()
            .code(),
            "OAUTH_STATE_MISMATCH"
        );
        assert!(
            parse_callback_request_line(
                "POST /auth/callback?code=abc&state=good HTTP/1.0\r\n\r\n",
                "good"
            )
            .is_err()
        );
        assert!(
            parse_callback_request_line("GET /wrong?code=abc&state=good HTTP/1.0\r\n\r\n", "good")
                .is_err()
        );
    }

    #[test]
    fn invalid_configuration_refuses_non_https_and_forbidden_port() {
        let mut config = BrokerConfig::default();
        config.responses_endpoint = "http://127.0.0.1:9999/responses".into();
        assert_eq!(
            Broker::with_store(config, Arc::new(MemoryStore::default()))
                .err()
                .unwrap()
                .code(),
            "OAUTH_CONFIGURATION_INVALID"
        );
        let mut config = BrokerConfig::default();
        config.callback_port = 18790;
        assert_eq!(
            Broker::with_store(config, Arc::new(MemoryStore::default()))
                .err()
                .unwrap()
                .code(),
            "OAUTH_CONFIGURATION_INVALID"
        );
    }

    #[test]
    fn structured_format_is_strict_bounded_json_schema_only() {
        let valid = json!({
            "type":"json_schema",
            "name":"tom_assist_parser_v1",
            "strict":true,
            "schema":{
                "type":"object",
                "additionalProperties":false,
                "properties":{"ok":{"type":"boolean"}},
                "required":["ok"]
            }
        });
        assert!(validate_response_format(&valid).is_ok());
        for invalid in [
            json!({"type":"json_object","name":"x","strict":true,"schema":{}}),
            json!({"type":"json_schema","name":"bad name","strict":true,"schema":{}}),
            json!({"type":"json_schema","name":"x","strict":false,"schema":{}}),
            json!({"type":"json_schema","name":"x","strict":true,"schema":[],"extra":1}),
        ] {
            assert_eq!(
                validate_response_format(&invalid).unwrap_err().code(),
                "PROVIDER_RESPONSE_FORMAT_INVALID"
            );
        }
    }
}
