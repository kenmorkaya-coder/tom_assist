use tom_assist_context_admission::{
    AdmissionRequest, Candidate, CandidatePool, ContextAdmissionEngine, IntegrityStatus,
    ScoreComponents,
};
use tom_assist_protocol::{ModelInternalBias, ProviderCapabilities, StateStatus, StateType};

fn scores(structural: f64, semantic: f64) -> ScoreComponents {
    ScoreComponents {
        retrieval_rrf: None,
        semantic_relevance: semantic,
        structural_resonance: structural,
        dependency_sequence_relevance: 0.5,
        authority_strength: 1.0,
        bounded_recency: 0.5,
        stale_probability: 0.0,
        conflict_penalty: 0.0,
        redundancy_penalty: 0.0,
    }
}

fn candidate(id: &str, state_type: StateType, text: &str) -> Candidate {
    Candidate {
        id: id.into(),
        project_id: "project-alpha".into(),
        workstream_id: Some("workstream-core".into()),
        pool: CandidatePool::AuthoritativeState,
        state_type: Some(state_type),
        status: Some(StateStatus::Active),
        text: text.into(),
        authority: "user".into(),
        binding_hard: false,
        integrity: IntegrityStatus::Verified,
        privacy_allowed: true,
        dependencies: vec![],
        provenance: None,
        reconsideration_condition: None,
        scores: scores(0.8, 0.7),
    }
}

fn request(mut candidates: Vec<Candidate>) -> AdmissionRequest {
    // Deliberately unsorted input proves the engine owns deterministic ordering.
    candidates.reverse();
    AdmissionRequest {
        activated_branch_ids: vec!["branch-golden".into()],
        project_id: "project-alpha".into(),
        project_name: "Alpha".into(),
        workstream_id: "workstream-core".into(),
        workstream_name: "Core".into(),
        provider_session_id: "session-fixture".into(),
        state_version: 7,
        state_digest: "sha256:abcdef0123456789".into(),
        tom_checkpoint_digest: "sha256:checkpoint-v7".into(),
        tom_activation_id: "sha256:activation-v7".into(),
        user_draft: "What should I implement next?\nKeep the answer concise.".into(),
        provider_capabilities: ProviderCapabilities {
            provider_surface: "chatgpt.com/fixture".into(),
            visible_prompt_injection: true,
            response_capture: true,
            hidden_context_visibility: false,
            model_internal_bias: ModelInternalBias::None,
            max_context_tokens: None,
            exact_tokenizer: None,
            supports_system_field: Some(false),
        },
        candidates,
        budget_tokens: 500,
    }
}

fn golden_candidates() -> Vec<Candidate> {
    let mut objective = candidate(
        "objective-1",
        StateType::Objective,
        "Ship a local-first continuity assistant.",
    );
    objective.binding_hard = true;
    let concept = candidate(
        "concept-1",
        StateType::Concept,
        "Packet lineage binds a response to admitted state.",
    );
    let mut constraint = candidate(
        "constraint-1",
        StateType::Constraint,
        "Never upload project state.",
    );
    constraint.binding_hard = true;
    constraint.dependencies = vec!["concept-1".into()];
    let decision = candidate(
        "decision-1",
        StateType::Decision,
        "Use SQLite WAL for the event store.",
    );
    let mut rejected = candidate(
        "rejected-1",
        StateType::RejectedPath,
        "Do not use cloud sync.",
    );
    rejected.pool = CandidatePool::Guardrail;
    rejected.status = Some(StateStatus::Rejected);
    rejected.reconsideration_condition = Some("the owner approves an encrypted sync design".into());
    let completed = candidate(
        "completed-1",
        StateType::CompletedWork,
        "Protocol schemas are frozen; next boundary is transaction wiring.",
    );
    let dependency = candidate(
        "dependency-1",
        StateType::UnresolvedDependency,
        "Native-host installation must be completed before browser use.",
    );
    let mut evidence = candidate(
        "evidence-1",
        StateType::Evidence,
        "Local runtime inspection confirms the UDS boundary.",
    );
    evidence.provenance = Some("docs/spec/runtime_inspection_findings.md".into());
    let mut anchor = candidate(
        "anchor-1",
        StateType::Assumption,
        "The owner requested an inspectable visible state block.",
    );
    anchor.pool = CandidatePool::RetrievedAnchor;
    anchor.provenance = Some("turn-12".into());
    let mut wrong_project = candidate(
        "wrong-project",
        StateType::Decision,
        "Leak another project's decision.",
    );
    wrong_project.project_id = "project-other".into();
    let mut superseded = candidate(
        "superseded-positive",
        StateType::Decision,
        "Revive an obsolete decision.",
    );
    superseded.status = Some(StateStatus::Superseded);
    vec![
        objective,
        concept,
        constraint,
        decision,
        rejected,
        completed,
        dependency,
        evidence,
        anchor,
        wrong_project,
        superseded,
    ]
}

#[test]
fn golden_packet_renderer_manifest_and_digest_are_byte_stable() {
    let engine = ContextAdmissionEngine::default();
    let first = engine.build(request(golden_candidates())).unwrap();
    let second = engine.build(request(golden_candidates())).unwrap();
    assert_eq!(first, second);
    assert_eq!(
        first.state_block,
        include_str!("../../../tests/fixtures/protocol/golden_state_block.txt")
            .trim_end_matches('\n')
    );
    assert_eq!(first.packet.sections.len(), 9);
    assert_eq!(first.packet.excluded.len(), 2);
    assert_eq!(
        first.packet.packet_digest,
        "sha256:7cde573887477b423218c8dee21199ad72173414b77aa20e87d691aa37e61c55"
    );
    assert!(first.composer_text.ends_with(
        "[CURRENT_USER_REQUEST]\nWhat should I implement next?\nKeep the answer concise."
    ));
}

#[test]
fn fresh_project_first_packet_is_the_user_draft_without_an_authority_scaffold() {
    let request = request(vec![]);
    let draft = request.user_draft.clone();
    let result = ContextAdmissionEngine::default().build(request).unwrap();

    assert_eq!(result.state_block, "");
    assert_eq!(result.composer_text, draft);
    assert!(result.packet.sections.is_empty());
    assert_eq!(result.packet.estimated_tokens, 0);
    assert_eq!(result.packet.renderer_version, "authoritative-state/1.2");
    assert!(!result.composer_text.contains("TOM_ASSIST_STATE"));
}

#[test]
fn dependency_closure_stops_at_depth_two_with_an_explicit_marker() {
    let mut root = candidate("root", StateType::Decision, "Root decision");
    root.binding_hard = true;
    root.dependencies = vec!["depth-1".into()];
    let mut one = candidate("depth-1", StateType::Concept, "First dependency");
    one.dependencies = vec!["depth-2".into()];
    let mut two = candidate("depth-2", StateType::Concept, "Second dependency");
    two.dependencies = vec!["depth-3".into()];
    let three = candidate(
        "depth-3",
        StateType::Evidence,
        &format!("Too-deep dependency {}", "background ".repeat(300)),
    );
    let result = ContextAdmissionEngine::default()
        .build(request(vec![root, one, two, three]))
        .unwrap();
    assert!(result.trace.admitted_ids.contains(&"depth-2".into()));
    assert!(!result.trace.admitted_ids.contains(&"depth-3".into()));
    assert_eq!(
        result.trace.missing_dependencies,
        ["depth-2 -> depth-3 (depth-cap)"]
    );
    assert!(result.state_block.contains("[MISSING_DEPENDENCY]"));
}

#[test]
fn hard_constraints_survive_a_tiny_budget_and_optional_background_is_excluded() {
    let mut constraint = candidate(
        "constraint-hard",
        StateType::Constraint,
        "This binding constraint must survive.",
    );
    constraint.binding_hard = true;
    let background = candidate(
        "background-optional",
        StateType::Assumption,
        &"optional background ".repeat(100),
    );
    let mut tiny = request(vec![constraint, background]);
    tiny.budget_tokens = 1;
    let result = ContextAdmissionEngine::default().build(tiny).unwrap();
    assert!(
        result
            .trace
            .admitted_ids
            .contains(&"constraint-hard".into())
    );
    assert!(
        !result
            .trace
            .admitted_ids
            .contains(&"background-optional".into())
    );
    assert!(
        result
            .packet
            .warnings
            .iter()
            .any(|warning| warning.contains("exceeds"))
    );
}

#[test]
fn zero_budget_selects_the_documented_default_and_large_values_cap_at_twelve_hundred() {
    let mut defaults = request(vec![]);
    defaults.budget_tokens = 0;
    assert_eq!(
        ContextAdmissionEngine::default()
            .build(defaults)
            .unwrap()
            .trace
            .budget_tokens,
        500
    );
    let mut capped = request(vec![]);
    capped.budget_tokens = 99_000;
    assert_eq!(
        ContextAdmissionEngine::default()
            .build(capped)
            .unwrap()
            .trace
            .budget_tokens,
        1_200
    );
}
