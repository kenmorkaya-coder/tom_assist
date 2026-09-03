//! Commit-only experience wiring. Preview must never call these functions.
use crate::{Result, ServiceError};
use serde_json::{Value, json};
use tom_assist_persistence::{ResponseEvaluationRecord, Store};
use tom_assist_protocol::{InterventionStatus, canonical_sha256};
use tom_assist_tom_adapter::GatewayClient;

pub fn commit_captured_exchange(
    store: &Store,
    gateway: &GatewayClient,
    evaluation: &ResponseEvaluationRecord,
) -> Result<Option<Value>> {
    if evaluation.result == "INCOMPLETE" {
        return Ok(None);
    }
    let sent = store
        .sent_turn_for_packet(&evaluation.project_id, &evaluation.packet_digest)?
        .ok_or(ServiceError::PacketMismatch)?;
    let response = store
        .turn(&evaluation.turn_id)?
        .ok_or(ServiceError::CaptureIncomplete)?;
    if sent.project_id != evaluation.project_id
        || sent.role != "user"
        || response.role != "assistant"
        || response.project_id != evaluation.project_id
        || response.packet_digest != evaluation.packet_digest
        || response.completeness != "complete"
        || canonical_sha256(&sent.normalized_text)? != sent.content_hash
        || canonical_sha256(&response.normalized_text)? != response.content_hash
    {
        return Err(ServiceError::PacketMismatch);
    }
    // One experience per sent turn, even if the provider recaptures/regenerates a response.
    if let Some(receipt) = store.runtime_commit_for_sent(&sent.id)? {
        return Ok(Some(receipt));
    }
    if evaluation.result != "PASS"
        && evaluation.intervention_ids.is_empty()
        && !store.reviewed_exchange_accepted(&sent.id)?
    {
        return Ok(None);
    }
    let mut dismissed = false;
    // Native conflicts can be persisted as REVIEW while the gateway is down.
    // They still require resolution before any experience is applied.
    if !evaluation.intervention_ids.is_empty() {
        for id in &evaluation.intervention_ids {
            match store.intervention_status(id)? {
                None | Some(InterventionStatus::Open) => return Ok(None),
                Some(InterventionStatus::Dismissed) => dismissed = true,
                _ => {}
            }
        }
    }
    let context = store
        .context_run_by_digest(&evaluation.project_id, &evaluation.packet_digest)?
        .ok_or(ServiceError::UnknownPacket)?;
    // The only manifest authority is the durable sent context, never response payload IDs.
    let trace: Value = serde_json::from_str(&context.candidate_trace_json)?;
    let mut payload = json!({
        "project_id": evaluation.project_id, "role":"user", "text":sent.normalized_text,
        "response_text": response.normalized_text, "idempotency_key":format!("sent-turn:{}",sent.id),
        "packet_digest": context.packet_digest, "activated_branch_ids":context.activated_branch_ids,
        "admitted_anchor_ids":context.admitted_anchor_ids, "conflict_dismissed":dismissed,
    });
    if let Some(analysis) = trace
        .get("structural_analysis")
        .filter(|value| !value.is_null())
    {
        payload["structural_analysis"] = analysis.clone();
    }
    if let Some(retrieval) = trace.get("retrieval").filter(|value| value.is_array()) {
        payload["retrieval_trace"] = retrieval.clone();
    }
    let result = gateway
        .commit_exchange(payload)
        .map_err(|error| ServiceError::Invalid(format!("runtime_commit_pending: {error}")))?;
    // Gateway's durable idempotency covers a lost reply or a crash before this receipt.
    store.record_runtime_commit(&sent.id, &evaluation.id, &result)?;
    Ok(Some(result))
}

pub fn resolve_intervention_with_runtime(
    store: &Store,
    gateway: Option<&GatewayClient>,
    project_id: &str,
    id: &str,
    status: InterventionStatus,
    at: &str,
) -> Result<()> {
    let intervention = store
        .interventions(project_id)?
        .into_iter()
        .find(|item| item.id == id)
        .ok_or_else(|| ServiceError::Invalid("intervention does not belong to project".into()))?;
    store.resolve_intervention(id, status, at)?;
    if let Some(gateway) = gateway {
        if let Some(turn) = store.turn(&intervention.turn_id)? {
            let evaluation_id = canonical_sha256(
                &json!({"kind":"evaluation","turn_id":turn.id,"packet_digest":turn.packet_digest}),
            )?;
            if let Some(evaluation) = store.response_evaluation(&evaluation_id)? {
                commit_captured_exchange(store, gateway, &evaluation)?;
            }
        }
    }
    Ok(())
}
