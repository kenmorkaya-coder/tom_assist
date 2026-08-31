use serde_json::{Value, json};
use std::collections::BTreeSet;
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::thread;
use std::time::Duration;
use tempfile::Builder;
use tom_assist_governance::{
    CandidateChannel, ClaimCheck, CommitGateDecision, EvaluationRequest, EvaluationState,
    EvidenceUse, GatewayVerifier, GovernanceEngine, LedgerRule, StructureCheck,
    SupersessionAttempt, commit_gate, extract_candidates,
};
use tom_assist_persistence::Store;
use tom_assist_protocol::{
    Authority, BindingStrength, InterventionCode, InterventionStatus, MutationOperation,
    StateMutationCandidate, StateObject, StateStatus, StateType, TomCheck,
};
use tom_assist_tom_adapter::GatewayClient;

#[derive(Clone, Copy)]
struct DeterministicVerifier;

impl GatewayVerifier for DeterministicVerifier {
    fn verify_drift(&self, payload: Value) -> Result<Value, String> {
        Ok(json!({
            "decision": if payload["invariants"].as_array().is_some_and(|rows| !rows.is_empty()) { "block" } else { "permit" },
            "residual_total": 1.0
        }))
    }

    fn verify_claims(&self, _payload: Value) -> Result<Value, String> {
        Ok(json!({"supported_count": 0}))
    }

    fn adjudicate_structure(&self, _payload: Value) -> Result<Value, String> {
        Ok(json!({"accepted": true}))
    }
}

#[derive(Clone, Copy)]
struct RejectingVerifier;

impl GatewayVerifier for RejectingVerifier {
    fn verify_drift(&self, _payload: Value) -> Result<Value, String> {
        Ok(json!({"decision":"permit"}))
    }

    fn verify_claims(&self, _payload: Value) -> Result<Value, String> {
        Ok(json!({"unsupported_count":1}))
    }

    fn adjudicate_structure(&self, _payload: Value) -> Result<Value, String> {
        Ok(json!({"accepted":false,"rejection_codes":["missing_constraint"]}))
    }
}

fn rule(code: InterventionCode, id: &str, phrase: &str) -> LedgerRule {
    LedgerRule {
        code,
        state_id: id.into(),
        summary: format!("crafted {code:?} fixture"),
        match_phrases: vec![phrase.into()],
        evidence_turn_ids: vec!["00000000-0000-4000-8000-000000000090".into()],
        suggested_context_patch: Some(format!("retain {id}")),
    }
}

fn base(response: &str) -> EvaluationRequest {
    EvaluationRequest {
        project_id: "00000000-0000-4000-8000-000000000001".into(),
        workstream_id: "00000000-0000-4000-8000-000000000002".into(),
        packet_project_id: "00000000-0000-4000-8000-000000000001".into(),
        packet_workstream_id: "00000000-0000-4000-8000-000000000002".into(),
        turn_id: "00000000-0000-4000-8000-000000000003".into(),
        response_text: response.into(),
        complete: true,
        rules: vec![],
        guardrail_anchors: vec![],
        asserted_candidates: vec![],
        evidence_used: vec![],
        supersession_attempts: vec![],
        addressed_state_ids: vec![],
        action_proposed: false,
        claim_checks: vec![],
        structure_check: None,
    }
}

fn asserted_candidate() -> StateMutationCandidate {
    StateMutationCandidate {
        candidate_id: "00000000-0000-4000-8000-000000000010".into(),
        project_id: "00000000-0000-4000-8000-000000000001".into(),
        source_turn_ids: vec!["00000000-0000-4000-8000-000000000003".into()],
        proposed_by: Authority::ProviderCandidate,
        operation: MutationOperation::Create,
        object: json!({"type":"DECISION","asserted_as_authoritative":true}),
        tom_check: TomCheck {
            result: "candidate_only".into(),
            conflicts: vec![],
            requires_user_confirmation: true,
        },
    }
}

#[test]
fn each_intervention_code_fires_on_its_crafted_fixture_and_clean_stays_clean() {
    let engine = GovernanceEngine::new(DeterministicVerifier);
    let mut scenarios = Vec::new();

    let mut contradiction = base("The answer says violate held decision now.");
    contradiction.rules = vec![rule(
        InterventionCode::Contradiction,
        "decision-1",
        "violate held decision",
    )];
    scenarios.push((InterventionCode::Contradiction, contradiction));

    let mut constraint = base("We should drop encryption constraint today.");
    constraint.rules = vec![rule(
        InterventionCode::ConstraintDropped,
        "constraint-1",
        "drop encryption constraint",
    )];
    scenarios.push((InterventionCode::ConstraintDropped, constraint));

    let mut superseded = base("Use obsolete pipeline for the next release.");
    superseded.rules = vec![rule(
        InterventionCode::SupersededPathRevived,
        "rejected-1",
        "use obsolete pipeline",
    )];
    scenarios.push((InterventionCode::SupersededPathRevived, superseded));

    let mut completed = base("Repeat finished migration as the next task.");
    completed.rules = vec![rule(
        InterventionCode::CompletedWorkReproposed,
        "completed-1",
        "repeat finished migration",
    )];
    scenarios.push((InterventionCode::CompletedWorkReproposed, completed));

    let mut objective = base("Optimize marketing instead of the active objective.");
    objective.rules = vec![rule(
        InterventionCode::ObjectiveDrift,
        "objective-1",
        "optimize marketing instead",
    )];
    scenarios.push((InterventionCode::ObjectiveDrift, objective));

    let mut concept = base("Treat packet lineage as optional metadata.");
    concept.rules = vec![rule(
        InterventionCode::ConceptDrift,
        "concept-1",
        "lineage as optional metadata",
    )];
    scenarios.push((InterventionCode::ConceptDrift, concept));

    let mut unsupported = base("The provider claims a proposal is final.");
    unsupported.asserted_candidates = vec![asserted_candidate()];
    scenarios.push((InterventionCode::UnsupportedStateChange, unsupported));

    let mut stale = base("Use the cited old benchmark.");
    stale.evidence_used = vec![EvidenceUse {
        evidence_id: "evidence-stale".into(),
        integrity_status: "stale".into(),
    }];
    scenarios.push((InterventionCode::StaleEvidenceUsed, stale));

    let mut wrong = base("Answer from the wrong attachment.");
    wrong.packet_project_id = "00000000-0000-4000-8000-000000000099".into();
    scenarios.push((InterventionCode::WrongProjectContext, wrong));

    let mut no_reason = base("Replace the held decision.");
    no_reason.supersession_attempts = vec![SupersessionAttempt {
        state_id: "decision-held".into(),
        reason: "".into(),
    }];
    scenarios.push((InterventionCode::SupersessionWithoutReason, no_reason));

    let mut unresolved = base("Proceed with deployment.");
    unresolved.action_proposed = true;
    unresolved.rules = vec![rule(
        InterventionCode::UnresolvedDependencyIgnored,
        "dependency-1",
        "dependency marker unused for this code",
    )];
    scenarios.push((InterventionCode::UnresolvedDependencyIgnored, unresolved));

    let observed: BTreeSet<String> = scenarios
        .into_iter()
        .map(|(expected, request)| {
            let result = engine.evaluate(request).unwrap();
            assert_eq!(result.interventions.len(), 1, "fixture for {expected:?}");
            assert_eq!(result.interventions[0].code, expected);
            assert!(result.correction_packet.is_some());
            format!("{expected:?}")
        })
        .collect();
    assert_eq!(observed.len(), 11);
    let mut clean_request = base("Continue the approved local plan.");
    clean_request.rules = vec![
        rule(
            InterventionCode::Contradiction,
            "decision-clean",
            "violate held decision",
        ),
        rule(
            InterventionCode::ConstraintDropped,
            "constraint-clean",
            "drop encryption constraint",
        ),
        rule(
            InterventionCode::SupersededPathRevived,
            "rejected-clean",
            "use obsolete pipeline",
        ),
        rule(
            InterventionCode::CompletedWorkReproposed,
            "completed-clean",
            "repeat finished migration",
        ),
        rule(
            InterventionCode::ObjectiveDrift,
            "objective-clean",
            "optimize marketing instead",
        ),
        rule(
            InterventionCode::ConceptDrift,
            "concept-clean",
            "lineage as optional metadata",
        ),
        rule(
            InterventionCode::UnresolvedDependencyIgnored,
            "dependency-clean",
            "unused",
        ),
    ];
    let clean = engine.evaluate(clean_request).unwrap();
    assert_eq!(clean.state, EvaluationState::Pass);
    assert!(clean.interventions.is_empty());
}

fn authoritative_object() -> StateObject {
    StateObject {
        id: "00000000-0000-4000-8000-000000000020".into(),
        project_id: "00000000-0000-4000-8000-000000000001".into(),
        workstream_id: None,
        object_type: StateType::Decision,
        title: "Approved decision".into(),
        canonical_text: "Use the local transaction service.".into(),
        status: StateStatus::Active,
        authority: Authority::User,
        confidence: 1.0,
        binding_strength: Some(BindingStrength::Hard),
        source_turn_ids: vec![],
        evidence_ids: vec![],
        branch_refs: vec![],
        created_at: "2026-08-10T00:00:00Z".into(),
        updated_at: "2026-08-10T00:00:00Z".into(),
        effective_at: "2026-08-10T00:00:00Z".into(),
        supersedes_id: None,
        reconsideration_condition: None,
        content_hash: "sha256:approved".into(),
        state_version: 1,
    }
}

#[test]
fn deterministic_and_manual_extraction_are_candidate_only_and_commit_gate_is_explicit() {
    let deterministic = extract_candidates(
        "00000000-0000-4000-8000-000000000001",
        "00000000-0000-4000-8000-000000000003",
        "Decision: Use a local queue\nConstraint: Never export cookies",
        CandidateChannel::DeterministicVisibleTurn,
    );
    assert_eq!(deterministic.len(), 2);
    assert!(deterministic.iter().all(|candidate| {
        candidate.proposed_by == Authority::ProviderCandidate
            && candidate.tom_check.requires_user_confirmation
            && candidate.object["status"] == "proposed"
    }));
    let manual = extract_candidates(
        "00000000-0000-4000-8000-000000000001",
        "00000000-0000-4000-8000-000000000004",
        "Completed: Protocol fixture authored",
        CandidateChannel::ManualUser,
    );
    assert_eq!(manual[0].proposed_by, Authority::User);
    let object = authoritative_object();
    assert!(matches!(
        commit_gate(&object, 1, 1, true, &[]),
        CommitGateDecision::Permit
    ));
    assert!(matches!(
        commit_gate(&object, 0, 1, true, &[]),
        CommitGateDecision::Reject(_)
    ));
    assert!(matches!(
        commit_gate(&object, 1, 1, false, &[]),
        CommitGateDecision::Reject(_)
    ));
    let mut conflict_request = base("Use obsolete pipeline now.");
    conflict_request.rules = vec![rule(
        InterventionCode::SupersededPathRevived,
        "rejected-commit",
        "use obsolete pipeline",
    )];
    let blocking = GovernanceEngine::new(DeterministicVerifier)
        .evaluate(conflict_request)
        .unwrap()
        .interventions;
    assert!(matches!(
        commit_gate(&object, 1, 1, true, &blocking),
        CommitGateDecision::Reject(_)
    ));
}

#[test]
fn claim_and_structure_inputs_are_routed_through_the_gateway_contract() {
    let mut request = base("Cite the fixture and change state.");
    request.claim_checks = vec![ClaimCheck {
        evidence_id: "evidence-claim".into(),
        claim: "A claim without corpus support".into(),
        corpus_chunks: vec![json!({"id":"chunk-1","text":"unrelated text"})],
    }];
    request.structure_check = Some(StructureCheck {
        state_id: "decision-structure".into(),
        proposal: json!({"selected_operator":"replace","constraints_checked":[]}),
        expected: json!({"expected_operator":"replace","required_constraints":["authority"]}),
    });
    let result = GovernanceEngine::new(RejectingVerifier)
        .evaluate(request)
        .unwrap();
    let codes: BTreeSet<String> = result
        .interventions
        .iter()
        .map(|item| format!("{:?}", item.code))
        .collect();
    assert_eq!(
        codes,
        BTreeSet::from(["StaleEvidenceUsed".into(), "UnsupportedStateChange".into()])
    );
}

#[test]
fn false_positive_resolution_is_persisted_without_changing_state() {
    let engine = GovernanceEngine::new(DeterministicVerifier);
    let mut request = base("Use obsolete pipeline for the next release.");
    request.rules = vec![rule(
        InterventionCode::SupersededPathRevived,
        "rejected-1",
        "use obsolete pipeline",
    )];
    let intervention = engine.evaluate(request).unwrap().interventions.remove(0);
    let mut store = Store::open_memory().unwrap();
    store
        .create_project(
            &intervention.project_id,
            "Fixture",
            "local-default",
            "governance-policy/1.0",
            "owner",
            "create",
            "2026-08-10T00:00:00Z",
        )
        .unwrap();
    store
        .record_intervention(&intervention, "2026-08-10T00:00:01Z")
        .unwrap();
    store
        .resolve_intervention(
            &intervention.id,
            InterventionStatus::FalsePositive,
            "2026-08-10T00:00:02Z",
        )
        .unwrap();
    assert_eq!(
        store.intervention_status(&intervention.id).unwrap(),
        Some(InterventionStatus::FalsePositive)
    );
    assert_eq!(
        store
            .project(&intervention.project_id)
            .unwrap()
            .unwrap()
            .state_version,
        0
    );
}

struct ChildGuard(Child);
impl Drop for ChildGuard {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

#[test]
#[ignore = "requires the real pinned gateway and permission to bind a Unix socket"]
fn live_gateway_drift_verifier_drives_contradiction_mapping() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .unwrap();
    std::fs::create_dir_all(root.join(".tmp")).unwrap();
    let temporary = Builder::new()
        .prefix("governance-live-")
        .tempdir_in(root.join(".tmp"))
        .unwrap();
    let socket = temporary.path().join("gateway.sock");
    let child = Command::new(root.join(".venv-gateway/bin/python"))
        .arg(root.join("gateway/tom_gateway.py"))
        .arg("--socket")
        .arg(&socket)
        .arg("--data-dir")
        .arg(temporary.path().join("data"))
        .arg("--tom-master")
        .arg("/Users/kenmorkaya/PycharmProjects/tom_master")
        .stdout(Stdio::null())
        .stderr(Stdio::inherit())
        .spawn()
        .unwrap();
    let _guard = ChildGuard(child);
    for _ in 0..200 {
        if socket.exists() {
            break;
        }
        thread::sleep(Duration::from_millis(20));
    }
    let engine = GovernanceEngine::new(GatewayClient::new(socket));
    let mut request = base("We will upload all state to a public service.");
    request.rules = vec![rule(
        InterventionCode::Contradiction,
        "constraint-local",
        "upload all state",
    )];
    let result = engine.evaluate(request).unwrap();
    assert_eq!(
        result.interventions[0].code,
        InterventionCode::Contradiction
    );
    assert_eq!(result.state, EvaluationState::Conflict);
}
