use serde_json::json;
use std::io::{BufRead, BufReader, Write};
use std::os::unix::fs::PermissionsExt;
use std::os::unix::net::UnixStream;
use std::sync::Arc;
use std::thread;
use tempfile::Builder;
use tom_assist_persistence::{Store, StoreError};
use tom_assist_protocol::{
    Actor, ActorType, Authority, BindingStrength, Envelope, Method, ModelInternalBias,
    ProviderCapabilities, StateObject, StateStatus, StateType,
};
use tom_assistd::{
    AssistService, EvaluateTurnRequest, EvaluationState, PrepareTurnRequest, SendTurnRequest,
    ServiceError, WireResponse, bind_unix, handle_stream,
};

fn provider_capabilities() -> ProviderCapabilities {
    ProviderCapabilities {
        provider_surface: "chatgpt.com/fixture".into(),
        visible_prompt_injection: true,
        response_capture: true,
        hidden_context_visibility: false,
        model_internal_bias: ModelInternalBias::None,
        max_context_tokens: None,
        exact_tokenizer: None,
        supports_system_field: Some(false),
    }
}

fn service() -> Arc<AssistService> {
    let mut store = Store::open_memory().unwrap();
    store
        .create_project(
            "project-a",
            "Project A",
            "local-default",
            "context-policy/1.1",
            "owner",
            "create-project-a",
            "2026-08-10T00:00:00Z",
        )
        .unwrap();
    Arc::new(AssistService::new(store))
}

fn prepare(service: &AssistService, draft: &str) -> tom_assistd::PreparedTurn {
    service
        .prepare_turn(PrepareTurnRequest {
            project_id: "project-a".into(),
            workstream_id: "workstream-main".into(),
            provider_session_id: "session-a".into(),
            user_draft: draft.into(),
            tom_checkpoint_digest: "sha256:checkpoint-v0".into(),
            tom_activation_id: "sha256:activation-v0".into(),
            provider_capabilities: provider_capabilities(),
            sections: vec![],
            retrieved_anchor_ids: vec![],
            excluded: vec![],
            packet_text: "[TOM_ASSIST_STATE v1]\n[/TOM_ASSIST_STATE]".into(),
            warnings: vec![],
            latency_ms: 3,
            created_at: "2026-08-10T00:00:01Z".into(),
        })
        .unwrap()
}

fn object(id: &str) -> StateObject {
    StateObject {
        id: id.into(),
        project_id: "project-a".into(),
        workstream_id: Some("workstream-main".into()),
        object_type: StateType::Decision,
        title: id.into(),
        canonical_text: format!("Authoritative decision {id}"),
        status: StateStatus::Active,
        authority: Authority::User,
        confidence: 1.0,
        binding_strength: Some(BindingStrength::Hard),
        source_turn_ids: vec![],
        evidence_ids: vec![],
        branch_refs: vec![],
        created_at: "2026-08-10T00:00:02Z".into(),
        updated_at: "2026-08-10T00:00:02Z".into(),
        effective_at: "2026-08-10T00:00:02Z".into(),
        supersedes_id: None,
        reconsideration_condition: None,
        content_hash: format!("sha256:{id}"),
        state_version: 0,
    }
}

#[test]
fn prepare_is_snapshot_bound_and_send_is_idempotent() {
    let service = service();
    let prepared = prepare(&service, "Keep the transaction pure.");
    assert_eq!(prepared.packet.project_state_version, 0);
    assert_eq!(prepared.packet.renderer_version, "authoritative-state/1.0");
    let request = SendTurnRequest {
        project_id: "project-a".into(),
        packet_digest: prepared.packet.packet_digest.clone(),
        user_draft: "Keep the transaction pure.".into(),
        turn_id: "turn-user-1".into(),
        ordinal: 1,
        idempotency_key: "send-1".into(),
        captured_at: "2026-08-10T00:00:03Z".into(),
    };
    let first = service.send_turn(request.clone()).unwrap();
    let duplicate = service.send_turn(request).unwrap();
    assert!(!first.duplicate);
    assert!(duplicate.duplicate);
    assert_eq!(first.packet_digest, duplicate.packet_digest);
}

#[test]
fn stale_packet_is_rejected_after_authoritative_state_advances() {
    let service = service();
    let prepared = prepare(&service, "Prepare against V0.");
    service
        .commit_object(
            object("decision-v1"),
            0,
            "owner",
            "commit-v1",
            "2026-08-10T00:00:04Z",
        )
        .unwrap();
    let error = service
        .send_turn(SendTurnRequest {
            project_id: "project-a".into(),
            packet_digest: prepared.packet.packet_digest,
            user_draft: "Prepare against V0.".into(),
            turn_id: "turn-stale".into(),
            ordinal: 2,
            idempotency_key: "send-stale".into(),
            captured_at: "2026-08-10T00:00:05Z".into(),
        })
        .unwrap_err();
    assert!(matches!(
        error,
        ServiceError::StalePacket {
            prepared: 0,
            current: 1
        }
    ));
}

#[test]
fn evaluate_binds_response_to_packet_and_marks_incomplete_capture() {
    let service = service();
    let prepared = prepare(&service, "Evaluate this response.");
    let result = service
        .evaluate_turn(EvaluateTurnRequest {
            project_id: "project-a".into(),
            packet_digest: prepared.packet.packet_digest,
            response_turn_id: "turn-assistant-1".into(),
            response_text: "partial".into(),
            ordinal: 2,
            complete: false,
            created_at: "2026-08-10T00:00:06Z".into(),
            latency_ms: 2,
        })
        .unwrap();
    assert_eq!(result.result, EvaluationState::Incomplete);
    assert!(!result.stale);
}

#[test]
fn concurrent_tabs_are_serialized_and_sqlite_cas_rejects_one() {
    let service = service();
    let left = Arc::clone(&service);
    let right = Arc::clone(&service);
    let a = thread::spawn(move || {
        left.commit_object(
            object("decision-left"),
            0,
            "tab-left",
            "commit-left",
            "2026-08-10T00:00:07Z",
        )
    });
    let b = thread::spawn(move || {
        right.commit_object(
            object("decision-right"),
            0,
            "tab-right",
            "commit-right",
            "2026-08-10T00:00:07Z",
        )
    });
    let results = [a.join().unwrap(), b.join().unwrap()];
    assert_eq!(results.iter().filter(|result| result.is_ok()).count(), 1);
    assert_eq!(
        results
            .iter()
            .filter(|result| matches!(
                result,
                Err(ServiceError::Store(StoreError::StateVersionConflict {
                    expected: 0,
                    actual: 1
                }))
            ))
            .count(),
        1
    );
}

#[test]
fn unix_socket_is_user_only_and_protocol_versioned() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .unwrap();
    std::fs::create_dir_all(root.join(".tmp")).unwrap();
    let temporary = Builder::new()
        .prefix("assistd-uds-")
        .tempdir_in(root.join(".tmp"))
        .unwrap();
    let socket = temporary.path().join("assistd.sock");
    let listener = bind_unix(&socket).unwrap();
    assert_eq!(
        std::fs::metadata(&socket).unwrap().permissions().mode() & 0o777,
        0o600
    );
    let service = service();
    let worker = thread::spawn(move || {
        let (stream, _) = listener.accept().unwrap();
        handle_stream(&service, stream).unwrap();
    });
    let mut stream = UnixStream::connect(&socket).unwrap();
    let envelope = Envelope {
        protocol: "tom-assist/1.0".into(),
        request_id: "request-capabilities".into(),
        idempotency_key: "capabilities-1".into(),
        method: Method::CapabilitiesGet,
        actor: Actor {
            actor_type: ActorType::NativeHost,
            instance_id: "native-host-test".into(),
        },
        project_id: None,
        base_state_version: None,
        payload: json!({}),
        sent_at: "2026-08-10T00:00:08Z".into(),
    };
    serde_json::to_writer(&mut stream, &envelope).unwrap();
    stream.write_all(b"\n").unwrap();
    let mut line = String::new();
    BufReader::new(stream).read_line(&mut line).unwrap();
    let response: WireResponse = serde_json::from_str(&line).unwrap();
    assert!(response.ok);
    assert_eq!(response.protocol, "tom-assist/1.0");
    assert_eq!(response.payload.unwrap()["prepare_readonly"], true);
    worker.join().unwrap();
}
