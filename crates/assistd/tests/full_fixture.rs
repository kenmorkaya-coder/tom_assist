use serde_json::{Value, json};
use tempfile::tempdir;
use tom_assist_governance::{
    CommitGateDecision, EvaluationRequest, GatewayVerifier, GovernanceEngine, LedgerRule,
    commit_gate,
};
use tom_assist_persistence::Store;
use tom_assist_protocol::{
    Authority, BindingStrength, InterventionCode, InterventionStatus, ModelInternalBias,
    ProviderCapabilities, StateObject, StateStatus, StateType, canonical_sha256,
};
use tom_assistd::{AssistService, EvaluateTurnRequest, PrepareTurnRequest, SendTurnRequest};

#[derive(Clone, Copy)]
struct FixtureVerifier;
impl GatewayVerifier for FixtureVerifier {
    fn verify_drift(&self, _payload: Value) -> Result<Value, String> {
        Ok(json!({"decision":"permit"}))
    }
    fn verify_claims(&self, _payload: Value) -> Result<Value, String> {
        Ok(json!({"supported_count":0}))
    }
    fn adjudicate_structure(&self, _payload: Value) -> Result<Value, String> {
        Ok(json!({"accepted":true}))
    }
}

fn object() -> StateObject {
    StateObject {
        id: "decision-corrected".into(),
        project_id: "fixture-project".into(),
        workstream_id: Some("main".into()),
        object_type: StateType::Decision,
        title: "Keep the current pipeline".into(),
        canonical_text: "Keep the current pipeline after explicit review.".into(),
        status: StateStatus::Active,
        authority: Authority::User,
        confidence: 1.0,
        binding_strength: Some(BindingStrength::Hard),
        source_turn_ids: vec!["assistant-1".into()],
        evidence_ids: vec![],
        branch_refs: vec![],
        created_at: "2026-08-10T00:00:05Z".into(),
        updated_at: "2026-08-10T00:00:05Z".into(),
        effective_at: "2026-08-10T00:00:05Z".into(),
        supersedes_id: None,
        reconsideration_condition: None,
        content_hash: "sha256:corrected".into(),
        state_version: 1,
    }
}

#[test]
fn fixture_lineage_survives_response_intervention_user_gate_and_restart() {
    let directory = tempdir().unwrap();
    let database = directory.path().join("fixture.sqlite3");
    let mut initial = Store::open(&database).unwrap();
    initial
        .create_project(
            "fixture-project",
            "Fixture",
            "state-focused",
            "context-policy/1.1",
            "user",
            "create-fixture",
            "2026-08-10T00:00:00Z",
        )
        .unwrap();
    drop(initial);
    let service = AssistService::new(Store::open(&database).unwrap());
    let draft = "Should we revive the obsolete pipeline?";
    let prepared = service.prepare_turn(PrepareTurnRequest {
        project_id: "fixture-project".into(), workstream_id: "main".into(), provider_session_id: "fixture-session".into(), user_draft: draft.into(),
        tom_checkpoint_digest: "sha256:checkpoint-v0".into(), tom_activation_id: "fixture-activation".into(),
        provider_capabilities: ProviderCapabilities { provider_surface: "fixture".into(), visible_prompt_injection: true, response_capture: true, hidden_context_visibility: false, model_internal_bias: ModelInternalBias::None, max_context_tokens: None, exact_tokenizer: None, supports_system_field: Some(false) },
        sections: vec![], retrieved_anchor_ids: vec![], excluded: vec![], packet_text: "[TOM_ASSIST_STATE v1]\nREJECTED_OR_SUPERSEDED\n- obsolete pipeline\n[/TOM_ASSIST_STATE]".into(), warnings: vec![], latency_ms: 1, created_at: "2026-08-10T00:00:01Z".into(),
    }).unwrap();
    assert!(prepared.packet_text.contains("obsolete pipeline"));
    service
        .send_turn(SendTurnRequest {
            project_id: "fixture-project".into(),
            packet_digest: prepared.packet.packet_digest.clone(),
            user_draft: draft.into(),
            turn_id: "user-1".into(),
            ordinal: 1,
            idempotency_key: "send-user-1".into(),
            captured_at: "2026-08-10T00:00:02Z".into(),
        })
        .unwrap();
    let response_text = "Use obsolete pipeline for the release.";
    service
        .evaluate_turn(EvaluateTurnRequest {
            project_id: "fixture-project".into(),
            packet_digest: prepared.packet.packet_digest.clone(),
            response_turn_id: "assistant-1".into(),
            response_text: response_text.into(),
            ordinal: 2,
            complete: true,
            created_at: "2026-08-10T00:00:03Z".into(),
            latency_ms: 1,
        })
        .unwrap();

    let governance = GovernanceEngine::new(FixtureVerifier)
        .evaluate(EvaluationRequest {
            project_id: "fixture-project".into(),
            workstream_id: "main".into(),
            packet_project_id: "fixture-project".into(),
            packet_workstream_id: "main".into(),
            turn_id: "assistant-1".into(),
            response_text: response_text.into(),
            complete: true,
            rules: vec![LedgerRule {
                code: InterventionCode::SupersededPathRevived,
                state_id: "rejected-obsolete".into(),
                summary: "obsolete pipeline was rejected".into(),
                match_phrases: vec!["use obsolete pipeline".into()],
                evidence_turn_ids: vec!["user-0".into()],
                suggested_context_patch: Some("retain current pipeline".into()),
            }],
            asserted_candidates: vec![],
            evidence_used: vec![],
            supersession_attempts: vec![],
            addressed_state_ids: vec![],
            action_proposed: false,
            claim_checks: vec![],
            structure_check: None,
        })
        .unwrap();
    assert_eq!(governance.interventions.len(), 1);
    assert!(matches!(
        commit_gate(&object(), 0, 0, false, &governance.interventions),
        CommitGateDecision::Reject(_)
    ));

    let ledger = Store::open(&database).unwrap();
    ledger
        .record_intervention(&governance.interventions[0], "2026-08-10T00:00:04Z")
        .unwrap();
    ledger
        .resolve_intervention(
            &governance.interventions[0].id,
            InterventionStatus::Accepted,
            "2026-08-10T00:00:05Z",
        )
        .unwrap();
    drop(ledger);
    assert!(matches!(
        commit_gate(&object(), 0, 0, true, &[]),
        CommitGateDecision::Permit
    ));
    service
        .commit_object(
            object(),
            0,
            "desktop-user",
            "commit-corrected",
            "2026-08-10T00:00:05Z",
        )
        .unwrap();
    drop(service);

    let restarted = Store::open(&database).unwrap();
    let state = restarted.current_state("fixture-project").unwrap();
    let project = restarted.project("fixture-project").unwrap().unwrap();
    assert_eq!(state.state_version, 1);
    assert_eq!(state.objects[0].id, "decision-corrected");
    assert_eq!(restarted.replay("fixture-project").unwrap(), state);
    assert_eq!(canonical_sha256(&state).unwrap(), project.state_digest);
    assert_eq!(
        restarted
            .intervention_status(&governance.interventions[0].id)
            .unwrap(),
        Some(InterventionStatus::Accepted)
    );
    assert_eq!(restarted.events("fixture-project").unwrap().len(), 2);
}
