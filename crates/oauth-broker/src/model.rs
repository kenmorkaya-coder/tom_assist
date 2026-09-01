use serde::{Deserialize, Serialize};
use zeroize::{Zeroize, ZeroizeOnDrop};

#[derive(Clone, Serialize, Deserialize, Zeroize, ZeroizeOnDrop)]
pub(crate) struct CredentialRecord {
    pub schema_version: u32,
    pub access_token: String,
    pub refresh_token: String,
    pub expires_at_ms: i64,
    pub chatgpt_account_id: String,
}

impl CredentialRecord {
    pub(crate) fn valid_shape(&self) -> bool {
        self.schema_version == 1
            && self.access_token.len() >= 20
            && self.refresh_token.len() >= 20
            && self.expires_at_ms > 0
            && !self.chatgpt_account_id.trim().is_empty()
            && self.chatgpt_account_id.len() <= 256
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BrokerStatus {
    pub connected: bool,
    pub code: String,
    pub credential_owner: String,
    pub model: String,
    pub streaming: bool,
    pub capabilities: serde_json::Value,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProviderReply {
    pub text: String,
    pub model: String,
    pub complete: bool,
}

#[derive(Deserialize, Zeroize, ZeroizeOnDrop)]
pub(crate) struct TokenResponse {
    pub access_token: String,
    pub refresh_token: Option<String>,
    pub id_token: Option<String>,
    pub expires_in: Option<i64>,
}

#[derive(Debug, Clone, Deserialize)]
pub(crate) struct IdClaims {
    pub nonce: Option<String>,
    #[serde(rename = "https://api.openai.com/auth", default)]
    pub auth: AuthClaim,
}

#[derive(Debug, Default, Clone, Deserialize)]
pub(crate) struct AuthClaim {
    pub chatgpt_account_id: Option<String>,
    pub account_id: Option<String>,
}

#[derive(Debug, Deserialize)]
pub(crate) struct SseEvent {
    #[serde(rename = "type")]
    pub event_type: String,
    pub delta: Option<String>,
    pub response: Option<serde_json::Value>,
}
