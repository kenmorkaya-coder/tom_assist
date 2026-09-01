use serde_json::{Value, json};
use std::io::{BufRead, BufReader, Write};
use std::os::unix::fs::PermissionsExt;
use std::os::unix::net::UnixStream;
use std::sync::Arc;
use std::thread;
use tempfile::Builder;
use tom_assist_governance::GatewayVerifier;
use tom_assist_persistence::{Store, StoreError};
use tom_assist_protocol::{
    Actor, ActorType, Authority, BindingStrength, Envelope, Method, ModelInternalBias, PacketItem,
    PacketSection, ProviderCapabilities, StateObject, StateStatus, StateType,
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

// Real pinned runtime, production envelope dispatch, isolated Unix socket only.
#[test]
fn production_exchange_commits_manifest_once_and_defers_conflict_teaching() {
    use std::path::Path;
    use std::process::{Child, Command, Stdio};
    use std::time::Duration;
    use tom_assist_tom_adapter::GatewayClient;
    struct OwnGateway(Child);
    impl Drop for OwnGateway {
        fn drop(&mut self) {
            let _ = self.0.kill();
            let _ = self.0.wait();
        }
    }
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .unwrap();
    let temp = tempfile::tempdir_in("/tmp").unwrap();
    let socket = temp.path().join("gw.sock");
    let launch = || {
        let child = Command::new(root.join(".venv-gateway/bin/python"))
            .arg(root.join("gateway/tom_gateway.py"))
            .arg("--socket")
            .arg(&socket)
            .arg("--data-dir")
            .arg(temp.path().join("runtime"))
            .env("PYTHONDONTWRITEBYTECODE", "1")
            .stdout(Stdio::null())
            .stderr(Stdio::inherit())
            .spawn()
            .unwrap();
        let mut guard = OwnGateway(child);
        let client = GatewayClient::new(&socket);
        for _ in 0..500 {
            if client.health().is_ok() {
                return guard;
            }
            assert!(guard.0.try_wait().unwrap().is_none(), "test gateway exited");
            thread::sleep(Duration::from_millis(20));
        }
        panic!("test gateway did not become ready");
    };
    let child = launch();
    let gateway = GatewayClient::new(&socket);
    assert_eq!(gateway.health().unwrap()["pinned_sha_match"], true);
    let database = temp.path().join("assist.sqlite3");
    let mut store = Store::open(&database).unwrap();
    store
        .create_project(
            "project-a",
            "Experience",
            "local-default",
            "context-policy/1.1",
            "owner",
            "create",
            "2026-08-31T00:00:00Z",
        )
        .unwrap();
    let seed = gateway
        .commit_turn("project-a", "user", "A beam connects two columns", "seed")
        .unwrap();
    let service = AssistService::with_gateway(store, gateway.clone());
    let draft = "Describe the connected beam load path.";
    let mut prep = evaluation_envelope("", "prepare", "", 0);
    prep.method = Method::TurnPrepare;
    prep.payload = json!({"project_id":"project-a","workstream_id":"main","provider_session_id":"session-a",
        "user_draft":draft,"tom_checkpoint_digest":"untrusted","tom_activation_id":"untrusted",
        "activated_branch_ids":["forged-branch"],"retrieved_anchor_ids":["forged-anchor"],
        "provider_capabilities":provider_capabilities(),"created_at":"2026-08-31T00:00:01Z"});
    let prepared = service.handle_envelope(prep.clone());
    assert!(prepared.ok, "{prepared:?}");
    let packet = prepared.payload.unwrap()["packet"].clone();
    let digest = packet["packet_digest"].as_str().unwrap();
    assert!(
        !packet["activated_branch_ids"]
            .as_array()
            .unwrap()
            .is_empty()
    );
    assert!(
        !packet["activated_branch_ids"]
            .as_array()
            .unwrap()
            .contains(&json!("forged-branch"))
    );
    assert_eq!(packet["retrieved_anchor_ids"], json!([seed.anchor_id]));
    let response = "The connected beam transfers force to both columns.";
    let mut evaluation = evaluation_envelope(digest, "assistant-committed", response, 2);
    evaluation.payload["activated_branch_ids"] = json!(["response-forgery"]);
    evaluation.payload["admitted_anchor_ids"] = json!(["response-forgery"]);
    assert!(
        !service.handle_envelope(evaluation.clone()).ok,
        "unsent preview must never commit"
    );
    assert_eq!(
        gateway
            .preview_rank("project-a", draft, 10, 2000)
            .unwrap()
            .checkpoint_digest,
        seed.checkpoint_digest
    );
    let mut send = evaluation_envelope(digest, "send", "", 1);
    send.method = Method::TurnSent;
    send.payload = json!({"project_id":"project-a","packet_digest":digest,"user_draft":draft,
        "turn_id":"sent-user","ordinal":1,"idempotency_key":"sent-user","captured_at":"2026-08-31T00:00:02Z"});
    assert!(service.handle_envelope(send.clone()).ok);
    assert!(service.handle_envelope(send.clone()).ok);
    let mut second_send = send.clone();
    second_send.payload["turn_id"] = json!("another-sent-user");
    assert!(
        !service.handle_envelope(second_send).ok,
        "ambiguous packet reuse is rejected"
    );
    let evaluated = service.handle_envelope(evaluation.clone());
    assert!(evaluated.ok, "{evaluated:?}");
    assert_eq!(evaluated.payload.unwrap()["result"], "PASS");
    let observer = Store::open(&database).unwrap();
    let receipt = observer
        .runtime_commit_for_sent("sent-user")
        .unwrap()
        .unwrap();
    assert_eq!(receipt["engine_tick_after"], seed.engine_tick_after + 1);
    assert_eq!(receipt["taught"], true);
    let mut serving: Vec<String> =
        serde_json::from_value(packet["activated_branch_ids"].clone()).unwrap();
    serving.sort();
    assert_eq!(receipt["activated_branch_ids"], json!(serving));
    assert_eq!(
        receipt["admitted_anchor_ids"],
        packet["retrieved_anchor_ids"]
    );
    assert_eq!(receipt["commit_dynamics"].as_array().unwrap().len(), 5);
    let checkpoint = gateway
        .preview_rank("project-a", draft, 10, 2000)
        .unwrap()
        .checkpoint_digest;
    drop(service);
    drop(child);
    let _restarted_child = launch();
    let restarted = AssistService::with_gateway(Store::open(&database).unwrap(), gateway.clone());
    assert!(restarted.handle_envelope(evaluation).ok);
    assert_eq!(
        gateway
            .preview_rank("project-a", draft, 10, 2000)
            .unwrap()
            .checkpoint_digest,
        checkpoint
    );
    assert_eq!(
        observer
            .runtime_commit_for_sent("sent-user")
            .unwrap()
            .unwrap(),
        receipt
    );

    // The same production resolution function is used by desktop and daemon.
    let mut rejected = object("rejected-obsolete");
    rejected.workstream_id = Some("main".into());
    rejected.object_type = StateType::RejectedPath;
    rejected.status = StateStatus::Rejected;
    rejected.canonical_text = "use obsolete pipeline".into();
    restarted
        .commit_object(
            rejected,
            0,
            "owner",
            "reject-obsolete",
            "2026-08-31T00:01:00Z",
        )
        .unwrap();
    gateway
        .memory_settings("project-a", json!({"teach_on_conflict":false}))
        .unwrap();
    let conflict_draft = "Should we use obsolete pipeline?";
    prep.payload["user_draft"] = json!(conflict_draft);
    let prepared = restarted.handle_envelope(prep);
    assert!(prepared.ok, "{prepared:?}");
    let conflict_packet = prepared.payload.unwrap()["packet"].clone();
    let conflict_digest = conflict_packet["packet_digest"].as_str().unwrap();
    send.payload["packet_digest"] = json!(conflict_digest);
    send.payload["user_draft"] = json!(conflict_draft);
    send.payload["turn_id"] = json!("sent-conflict");
    assert!(restarted.handle_envelope(send).ok);
    let conflict = restarted.handle_envelope(evaluation_envelope(
        conflict_digest,
        "assistant-conflict",
        "Use obsolete pipeline for the release.",
        4,
    ));
    assert!(conflict.ok, "{conflict:?}");
    let result = conflict.payload.unwrap();
    assert_eq!(result["result"], "CONFLICT");
    assert!(
        observer
            .runtime_commit_for_sent("sent-conflict")
            .unwrap()
            .is_none()
    );
    assert_eq!(
        gateway
            .preview_rank("project-a", draft, 10, 2000)
            .unwrap()
            .checkpoint_digest,
        checkpoint
    );
    for id in result["intervention_ids"].as_array().unwrap() {
        let mut resolution = evaluation_envelope(conflict_digest, "resolution", "", 0);
        resolution.method = Method::InterventionResolve;
        resolution.payload = json!({"intervention_id":id,"status":"dismissed"});
        let resolved = restarted.handle_envelope(resolution.clone());
        assert!(resolved.ok, "{resolved:?}");
        assert!(restarted.handle_envelope(resolution).ok);
    }
    let receipt = observer
        .runtime_commit_for_sent("sent-conflict")
        .unwrap()
        .unwrap();
    assert_eq!(receipt["taught"], false);
    assert_eq!(receipt["teach_reason"], "conflict_dismissed_policy");
    assert_eq!(receipt["engine_tick_after"], seed.engine_tick_after + 2);
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
    prepare_with_sections(service, draft, vec![])
}

fn prepare_with_sections(
    service: &AssistService,
    draft: &str,
    sections: Vec<PacketSection>,
) -> tom_assistd::PreparedTurn {
    service
        .prepare_turn(PrepareTurnRequest {
            activated_branch_ids: vec![],
            candidate_trace: json!([]),
            project_id: "project-a".into(),
            workstream_id: "workstream-main".into(),
            provider_session_id: "session-a".into(),
            user_draft: draft.into(),
            tom_checkpoint_digest: "sha256:checkpoint-v0".into(),
            tom_activation_id: "sha256:activation-v0".into(),
            provider_capabilities: provider_capabilities(),
            sections,
            retrieved_anchor_ids: vec![],
            excluded: vec![],
            packet_text: "[TOM_ASSIST_STATE v1]\n[/TOM_ASSIST_STATE]".into(),
            warnings: vec![],
            latency_ms: 3,
            created_at: "2026-08-10T00:00:01Z".into(),
        })
        .unwrap()
}

fn evaluation_envelope(
    packet_digest: &str,
    turn_id: &str,
    response_text: &str,
    ordinal: u64,
) -> Envelope {
    Envelope {
        protocol: "tom-assist/1.0".into(),
        request_id: format!("request-{turn_id}"),
        idempotency_key: format!("evaluation-{turn_id}"),
        method: Method::ResponseEvaluate,
        actor: Actor {
            actor_type: ActorType::Extension,
            instance_id: "00000000-0000-4000-8000-000000000456".into(),
        },
        project_id: Some("project-a".into()),
        base_state_version: None,
        payload: json!({
            "project_id": "project-a",
            "packet_digest": packet_digest,
            "response_turn_id": turn_id,
            "response_text": response_text,
            "ordinal": ordinal,
            "complete": true,
            "created_at": "2026-08-10T00:00:06Z",
            "latency_ms": 2
        }),
        sent_at: "2026-08-10T00:00:06Z".into(),
    }
}

#[derive(Clone, Copy)]
struct BlockingVerifier;

impl GatewayVerifier for BlockingVerifier {
    fn verify_drift(&self, _payload: Value) -> Result<Value, String> {
        Ok(json!({"decision":"block"}))
    }

    fn verify_claims(&self, _payload: Value) -> Result<Value, String> {
        Ok(json!({"supported_count":0,"unsupported_count":0}))
    }

    fn adjudicate_structure(&self, _payload: Value) -> Result<Value, String> {
        Ok(json!({"accepted":true}))
    }
}

#[derive(Clone, Copy)]
struct DownVerifier;

impl GatewayVerifier for DownVerifier {
    fn health(&self) -> Result<(), String> {
        Err("fixture gateway is down".into())
    }

    fn verify_drift(&self, _payload: Value) -> Result<Value, String> {
        Err("fixture gateway is down".into())
    }

    fn verify_claims(&self, _payload: Value) -> Result<Value, String> {
        Err("fixture gateway is down".into())
    }

    fn adjudicate_structure(&self, _payload: Value) -> Result<Value, String> {
        Err("fixture gateway is down".into())
    }
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
    assert_eq!(prepared.packet.renderer_version, "authoritative-state/1.1");
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
fn production_dispatch_persists_conflicts_and_leaves_clean_responses_as_pass() {
    let directory = tempfile::tempdir().unwrap();
    let database = directory.path().join("production-governance.sqlite3");
    let mut store = Store::open(&database).unwrap();
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
    let service = AssistService::with_governance_verifier(store, BlockingVerifier);
    let prepared = prepare_with_sections(
        &service,
        "Evaluate the held decision.",
        vec![PacketSection {
            section_type: "HELD_DECISIONS".into(),
            items: vec![PacketItem {
                state_id: "decision-held".into(),
                text: "violate held decision".into(),
                authority: "user".into(),
                structural_score: 1.0,
                semantic_score: 1.0,
                reason_selected: "fixture".into(),
            }],
        }],
    );

    let conflict_wire = service.handle_envelope(evaluation_envelope(
        &prepared.packet.packet_digest,
        "turn-assistant-conflict",
        "The answer says violate held decision now.",
        2,
    ));
    assert!(conflict_wire.ok, "{:?}", conflict_wire.error);
    let conflict: tom_assistd::EvaluationResult =
        serde_json::from_value(conflict_wire.payload.unwrap()).unwrap();
    assert_eq!(conflict.result, EvaluationState::Conflict);
    assert_eq!(conflict.intervention_ids.len(), 1);
    assert!(conflict.diagnostics.is_empty());

    let clean_wire = service.handle_envelope(evaluation_envelope(
        &prepared.packet.packet_digest,
        "turn-assistant-clean",
        "Continue the approved local plan.",
        3,
    ));
    assert!(clean_wire.ok, "{:?}", clean_wire.error);
    let clean: tom_assistd::EvaluationResult =
        serde_json::from_value(clean_wire.payload.unwrap()).unwrap();
    assert_eq!(clean.result, EvaluationState::Pass);
    assert!(clean.intervention_ids.is_empty());
    drop(service);

    let reopened = Store::open(&database).unwrap();
    let persisted_conflict = reopened
        .response_evaluation(&conflict.evaluation_id)
        .unwrap()
        .unwrap();
    assert_eq!(persisted_conflict.result, "CONFLICT");
    assert_eq!(
        persisted_conflict.intervention_ids,
        conflict.intervention_ids
    );
    assert_eq!(persisted_conflict.policy_version, "governance-policy/1.0");
    let persisted_clean = reopened
        .response_evaluation(&clean.evaluation_id)
        .unwrap()
        .unwrap();
    assert_eq!(persisted_clean.result, "PASS");
    assert!(persisted_clean.intervention_ids.is_empty());
    let interventions = reopened.interventions("project-a").unwrap();
    assert_eq!(interventions.len(), 1);
    assert_eq!(interventions[0].id, conflict.intervention_ids[0]);
    assert_eq!(interventions[0].severity, "blocking_commit");
}

#[test]
fn gateway_down_preserves_capture_records_diagnostic_and_caps_at_review() {
    let directory = tempfile::tempdir().unwrap();
    let database = directory.path().join("gateway-down.sqlite3");
    let mut store = Store::open(&database).unwrap();
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
    let service = AssistService::with_governance_verifier(store, DownVerifier);
    let prepared = prepare(&service, "Evaluate while degraded.");
    let wire = service.handle_envelope(evaluation_envelope(
        &prepared.packet.packet_digest,
        "turn-assistant-degraded",
        "A clean response still needs verifier review.",
        2,
    ));
    assert!(
        wire.ok,
        "gateway loss must not fail capture: {:?}",
        wire.error
    );
    let evaluation: tom_assistd::EvaluationResult =
        serde_json::from_value(wire.payload.unwrap()).unwrap();
    assert_eq!(evaluation.result, EvaluationState::Review);
    assert_eq!(evaluation.diagnostics, vec!["gateway_unavailable"]);
    assert!(evaluation.intervention_ids.is_empty());
    drop(service);

    let reopened = Store::open(&database).unwrap();
    assert!(reopened.turn("turn-assistant-degraded").unwrap().is_some());
    let persisted = reopened
        .response_evaluation(&evaluation.evaluation_id)
        .unwrap()
        .unwrap();
    assert_eq!(persisted.result, "REVIEW");
    assert_eq!(persisted.policy_version, "governance-policy/1.0");
    let diagnostics = reopened.audit_records("project-a").unwrap();
    let diagnostic = diagnostics
        .iter()
        .find(|record| record.category == "gateway_unavailable")
        .expect("gateway_unavailable diagnostic persisted");
    assert_eq!(diagnostic.correlation_id, evaluation.evaluation_id);
    assert_eq!(diagnostic.details["native_rules_ran"], true);
    assert_eq!(diagnostic.details["result_capped_at"], "REVIEW");
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
fn quick_capture_records_a_user_candidate_without_advancing_authoritative_state() {
    let directory = tempfile::tempdir().unwrap();
    let database = directory.path().join("candidates.sqlite3");
    let mut store = Store::open(&database).unwrap();
    let before = store
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
    let service = AssistService::new(store);
    let response = service.handle_envelope(Envelope {
        protocol: "tom-assist/1.0".into(),
        request_id: "request-candidate".into(),
        idempotency_key: "00000000-0000-4000-8000-000000000123".into(),
        method: Method::StateCandidateCreate,
        actor: Actor {
            actor_type: ActorType::Extension,
            instance_id: "00000000-0000-4000-8000-000000000456".into(),
        },
        project_id: Some("project-a".into()),
        base_state_version: None,
        payload: json!({
            "kind": "Decision",
            "text": "Keep the local release path",
            "authority": "user",
            "requires_user_confirmation": true
        }),
        sent_at: "2026-08-10T00:00:01Z".into(),
    });
    assert!(response.ok, "{:?}", response.error);
    let candidate: tom_assist_protocol::StateMutationCandidate =
        serde_json::from_value(response.payload.unwrap()).unwrap();
    assert_eq!(candidate.proposed_by, Authority::User);
    assert_eq!(candidate.object["status"], "proposed");
    assert!(candidate.tom_check.requires_user_confirmation);
    drop(service);

    let reopened = Store::open(&database).unwrap();
    assert_eq!(
        reopened.candidate(&candidate.candidate_id).unwrap(),
        Some(candidate)
    );
    let after = reopened.project("project-a").unwrap().unwrap();
    assert_eq!(after.state_version, before.state_version);
    assert_eq!(after.state_digest, before.state_digest);
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
