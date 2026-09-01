//! OAuth transport is separate from governance and experience. No auth objects.
use crate::*;

pub trait ProviderAdapter: Send + Sync {
    fn status(&self) -> Result<Value>;
    fn complete(&self, prompt: &str) -> Result<String>;
}
pub struct OAuthBrokerAdapter(pub GatewayClient);
impl ProviderAdapter for OAuthBrokerAdapter {
    fn status(&self) -> Result<Value> {
        self.0
            .provider_status()
            .map_err(|_| ServiceError::Invalid("OAUTH_BROKER_UNAVAILABLE".into()))
    }
    fn complete(&self, prompt: &str) -> Result<String> {
        let result = self
            .0
            .provider_complete(prompt)
            .map_err(|_| ServiceError::Invalid("PROVIDER_OUTCOME_UNKNOWN".into()))?;
        result["text"]
            .as_str()
            .filter(|s| !s.trim().is_empty())
            .map(str::to_owned)
            .ok_or_else(|| ServiceError::Invalid("PROVIDER_OUTCOME_UNKNOWN".into()))
    }
}
pub struct DisconnectedProvider;
impl ProviderAdapter for DisconnectedProvider {
    fn status(&self) -> Result<Value> {
        Ok(
            json!({"connected":false,"code":"OAUTH_BROKER_UNAVAILABLE","capabilities":capabilities()}),
        )
    }
    fn complete(&self, _: &str) -> Result<String> {
        Err(ServiceError::Invalid("OAUTH_DISCONNECTED".into()))
    }
}
pub fn capabilities() -> ProviderCapabilities {
    serde_json::from_value(json!({"provider_surface":"tom-assist/openai-oauth","visible_prompt_injection":true,"response_capture":true,"hidden_context_visibility":false,"model_internal_bias":"none","supports_system_field":false})).unwrap()
}
