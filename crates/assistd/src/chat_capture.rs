//! Explicit user authority over captured provider text; never automatic extraction.
use crate::*;

#[derive(Deserialize, Clone)]
pub struct ChatCaptureRequest {
    pub project_id: String,
    pub source_turn_id: String,
    pub text: String,
    pub object_id: String,
    pub idempotency_key: String,
    pub base_state_version: u64,
    pub old_id: Option<String>,
    pub reason: Option<String>,
    pub confirmed: bool,
    pub created_at: String,
}

pub fn capture_decision(store: &mut Store, request: ChatCaptureRequest) -> Result<()> {
    if !request.confirmed || request.text.trim().is_empty() || request.text.chars().count() > 16_000
    {
        return Err(ServiceError::Invalid(
            "Explicit confirmation and bounded text required".into(),
        ));
    }
    let source = store
        .turn(&request.source_turn_id)?
        .ok_or(ServiceError::CaptureIncomplete)?;
    if source.project_id != request.project_id
        || source.role != "assistant"
        || source.completeness != "complete"
        || store
            .conversation(&request.project_id, &source.session_id)?
            .is_none()
    {
        return Err(ServiceError::PacketMismatch);
    }
    if store
        .interventions(&request.project_id)?
        .iter()
        .any(|i| i.turn_id == source.id && i.status == "open")
    {
        return Err(ServiceError::Invalid(
            "Resolve the response's open findings before authoritative capture".into(),
        ));
    }
    let next = request
        .base_state_version
        .checked_add(1)
        .ok_or_else(|| ServiceError::Invalid("Invalid state version".into()))?;
    let object: StateObject = serde_json::from_value(
        json!({"id":request.object_id,"project_id":request.project_id,"type":"DECISION","title":request.text.chars().take(80).collect::<String>(),"canonical_text":request.text,"status":"active","authority":"user","confidence":1,"binding_strength":"hard","source_turn_ids":[source.id],"evidence_ids":[],"branch_refs":[],"created_at":request.created_at,"updated_at":request.created_at,"effective_at":request.created_at,"content_hash":canonical_sha256(&request.text)?,"state_version":next}),
    )?;
    if let Some(old) = request.old_id {
        let reason = request
            .reason
            .filter(|r| !r.trim().is_empty())
            .ok_or_else(|| ServiceError::Invalid("Supersession reason required".into()))?;
        store.supersede(
            &request.project_id,
            &old,
            object,
            &reason,
            request.base_state_version,
            "desktop-user",
            &request.idempotency_key,
            &request.created_at,
        )?;
    } else {
        store.commit_object(
            object,
            request.base_state_version,
            "user",
            "desktop-user",
            &request.idempotency_key,
            &request.created_at,
        )?;
    }
    Ok(())
}
