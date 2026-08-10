//! Evidence-linked interventions, candidate extraction, and the state commit gate.

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::BTreeMap;
use std::fmt::{Display, Formatter};
use tom_assist_protocol::{
    Authority, ErrorCode, Intervention, InterventionCode, InterventionSeverity, InterventionStatus,
    MutationOperation, ProtocolError, StateMutationCandidate, StateObject, StateStatus, StateType,
    TomCheck, canonical_sha256,
};
use tom_assist_tom_adapter::GatewayClient;

#[derive(Debug)]
pub enum GovernanceError {
    Json(serde_json::Error),
    Gateway(String),
    InvalidPolicy(String),
}

impl Display for GovernanceError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Json(error) => write!(f, "JSON error: {error}"),
            Self::Gateway(error) => write!(f, "gateway verifier error: {error}"),
            Self::InvalidPolicy(error) => write!(f, "invalid governance policy: {error}"),
        }
    }
}

impl std::error::Error for GovernanceError {}
impl From<serde_json::Error> for GovernanceError {
    fn from(value: serde_json::Error) -> Self {
        Self::Json(value)
    }
}
pub type Result<T> = std::result::Result<T, GovernanceError>;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GovernancePolicy {
    pub policy_version: String,
    pub direct_confidence: f64,
    pub gateway_confidence: f64,
    pub heuristic_confidence: f64,
    pub severity: BTreeMap<String, String>,
}

impl Default for GovernancePolicy {
    fn default() -> Self {
        serde_json::from_str(include_str!("../policy/governance-policy-1.0.json"))
            .expect("bundled governance policy is valid")
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LedgerRule {
    pub code: InterventionCode,
    pub state_id: String,
    pub summary: String,
    pub match_phrases: Vec<String>,
    #[serde(default)]
    pub evidence_turn_ids: Vec<String>,
    pub suggested_context_patch: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EvidenceUse {
    pub evidence_id: String,
    pub integrity_status: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SupersessionAttempt {
    pub state_id: String,
    pub reason: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ClaimCheck {
    pub evidence_id: String,
    pub claim: String,
    pub corpus_chunks: Vec<Value>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StructureCheck {
    pub state_id: String,
    pub proposal: Value,
    pub expected: Value,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EvaluationRequest {
    pub project_id: String,
    pub workstream_id: String,
    pub packet_project_id: String,
    pub packet_workstream_id: String,
    pub turn_id: String,
    pub response_text: String,
    pub complete: bool,
    pub rules: Vec<LedgerRule>,
    #[serde(default)]
    pub asserted_candidates: Vec<StateMutationCandidate>,
    #[serde(default)]
    pub evidence_used: Vec<EvidenceUse>,
    #[serde(default)]
    pub supersession_attempts: Vec<SupersessionAttempt>,
    #[serde(default)]
    pub addressed_state_ids: Vec<String>,
    #[serde(default)]
    pub action_proposed: bool,
    #[serde(default)]
    pub claim_checks: Vec<ClaimCheck>,
    #[serde(default)]
    pub structure_check: Option<StructureCheck>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EvaluationState {
    Pass,
    Review,
    Conflict,
    Incomplete,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GovernanceResult {
    pub state: EvaluationState,
    pub interventions: Vec<Intervention>,
    pub correction_packet: Option<String>,
    pub policy_version: String,
}

pub trait GatewayVerifier: Send + Sync {
    fn verify_drift(&self, payload: Value) -> std::result::Result<Value, String>;
    fn verify_claims(&self, payload: Value) -> std::result::Result<Value, String>;
    fn adjudicate_structure(&self, payload: Value) -> std::result::Result<Value, String>;
}

impl GatewayVerifier for GatewayClient {
    fn verify_drift(&self, payload: Value) -> std::result::Result<Value, String> {
        GatewayClient::verify_drift(self, payload).map_err(|error| error.to_string())
    }

    fn verify_claims(&self, payload: Value) -> std::result::Result<Value, String> {
        GatewayClient::verify_claims(self, payload).map_err(|error| error.to_string())
    }

    fn adjudicate_structure(&self, payload: Value) -> std::result::Result<Value, String> {
        GatewayClient::adjudicate_structure(self, payload).map_err(|error| error.to_string())
    }
}

pub struct GovernanceEngine<V> {
    verifier: V,
    policy: GovernancePolicy,
}

impl<V: GatewayVerifier> GovernanceEngine<V> {
    pub fn new(verifier: V) -> Self {
        Self {
            verifier,
            policy: GovernancePolicy::default(),
        }
    }

    pub fn with_policy(verifier: V, policy: GovernancePolicy) -> Self {
        Self { verifier, policy }
    }

    pub fn evaluate(&self, request: EvaluationRequest) -> Result<GovernanceResult> {
        if !request.complete {
            return Ok(GovernanceResult {
                state: EvaluationState::Incomplete,
                interventions: vec![],
                correction_packet: None,
                policy_version: self.policy.policy_version.clone(),
            });
        }
        let response_lower = request.response_text.to_lowercase();
        let mut hits = Vec::<(
            InterventionCode,
            String,
            String,
            Vec<String>,
            Option<String>,
            f64,
        )>::new();

        if request.packet_project_id != request.project_id
            || request.packet_workstream_id != request.workstream_id
        {
            hits.push((
                InterventionCode::WrongProjectContext,
                "packet scope differs from the attached project/workstream".into(),
                "packet-lineage".into(),
                vec![],
                None,
                self.policy.direct_confidence,
            ));
        }

        let gateway_rules: Vec<&LedgerRule> = request
            .rules
            .iter()
            .filter(|rule| {
                matches!(
                    rule.code,
                    InterventionCode::Contradiction | InterventionCode::ConstraintDropped
                ) && phrase_match(&response_lower, &rule.match_phrases)
            })
            .collect();
        if !gateway_rules.is_empty() {
            let payload = json!({
                "answer_text": request.response_text,
                "tx_id": request.turn_id,
                "invariants": gateway_rules.iter().map(|rule| json!({
                    "id": rule.state_id,
                    "description": rule.summary,
                    "contradict_patterns": rule.match_phrases.iter().map(|phrase| regex_escape(phrase)).collect::<Vec<_>>()
                })).collect::<Vec<_>>()
            });
            let decision = self
                .verifier
                .verify_drift(payload)
                .map_err(GovernanceError::Gateway)?;
            if matches!(
                decision.get("decision").and_then(Value::as_str),
                Some("block" | "revise")
            ) {
                for rule in gateway_rules {
                    hits.push(rule_hit(rule, self.policy.gateway_confidence));
                }
            }
        }

        for check in &request.claim_checks {
            let result = self
                .verifier
                .verify_claims(json!({
                    "claims": [check.claim],
                    "corpus_chunks": check.corpus_chunks
                }))
                .map_err(GovernanceError::Gateway)?;
            if result
                .get("unsupported_count")
                .and_then(Value::as_u64)
                .unwrap_or(0)
                > 0
            {
                hits.push((
                    InterventionCode::StaleEvidenceUsed,
                    "a cited project claim is unsupported by the supplied evidence corpus".into(),
                    check.evidence_id.clone(),
                    vec![],
                    None,
                    self.policy.gateway_confidence,
                ));
            }
        }

        if let Some(check) = &request.structure_check {
            let result = self
                .verifier
                .adjudicate_structure(json!({
                    "proposal": check.proposal,
                    "expected": check.expected
                }))
                .map_err(GovernanceError::Gateway)?;
            if result.get("accepted") != Some(&Value::Bool(true)) {
                hits.push((
                    InterventionCode::UnsupportedStateChange,
                    "response reasoning structure omitted a required authority/constraint step"
                        .into(),
                    check.state_id.clone(),
                    vec![],
                    None,
                    self.policy.gateway_confidence,
                ));
            }
        }

        for rule in &request.rules {
            match rule.code {
                InterventionCode::SupersededPathRevived
                | InterventionCode::CompletedWorkReproposed
                | InterventionCode::ObjectiveDrift
                | InterventionCode::ConceptDrift => {
                    if phrase_match(&response_lower, &rule.match_phrases) {
                        let confidence = if matches!(
                            rule.code,
                            InterventionCode::ObjectiveDrift | InterventionCode::ConceptDrift
                        ) {
                            self.policy.heuristic_confidence
                        } else {
                            self.policy.direct_confidence
                        };
                        hits.push(rule_hit(rule, confidence));
                    }
                }
                InterventionCode::UnresolvedDependencyIgnored => {
                    if request.action_proposed
                        && !request.addressed_state_ids.contains(&rule.state_id)
                    {
                        hits.push(rule_hit(rule, self.policy.direct_confidence));
                    }
                }
                _ => {}
            }
        }

        for candidate in &request.asserted_candidates {
            if matches!(
                candidate.proposed_by,
                Authority::ProviderCandidate | Authority::LocalModelCandidate
            ) && candidate.object.get("asserted_as_authoritative") == Some(&Value::Bool(true))
            {
                hits.push((
                    InterventionCode::UnsupportedStateChange,
                    "provider/model candidate was asserted as authoritative".into(),
                    candidate.candidate_id.clone(),
                    candidate.source_turn_ids.clone(),
                    None,
                    self.policy.direct_confidence,
                ));
            }
        }

        for evidence in &request.evidence_used {
            if matches!(
                evidence.integrity_status.as_str(),
                "stale" | "invalid" | "superseded"
            ) {
                hits.push((
                    InterventionCode::StaleEvidenceUsed,
                    "response relies on evidence that is not currently valid".into(),
                    evidence.evidence_id.clone(),
                    vec![],
                    None,
                    self.policy.direct_confidence,
                ));
            }
        }

        for attempt in &request.supersession_attempts {
            if attempt.reason.trim().is_empty() {
                hits.push((
                    InterventionCode::SupersessionWithoutReason,
                    "held state was replaced without a reason".into(),
                    attempt.state_id.clone(),
                    vec![],
                    None,
                    self.policy.direct_confidence,
                ));
            }
        }

        hits.sort_by(|left, right| {
            code_name(left.0)
                .cmp(code_name(right.0))
                .then(left.2.as_bytes().cmp(right.2.as_bytes()))
        });
        hits.dedup_by(|left, right| left.0 == right.0 && left.2 == right.2);
        let interventions: Vec<Intervention> = hits
            .into_iter()
            .map(
                |(code, summary, state_id, evidence_turn_ids, patch, confidence)| {
                    let id = deterministic_uuid(&format!(
                        "{}\0{}\0{}\0{}",
                        request.project_id,
                        request.turn_id,
                        code_name(code),
                        state_id
                    ));
                    Intervention {
                        id,
                        project_id: request.project_id.clone(),
                        turn_id: request.turn_id.clone(),
                        code,
                        severity: self.severity(code),
                        confidence,
                        summary,
                        response_excerpt: bounded_excerpt(&request.response_text, 240),
                        conflicting_state_ids: if state_id == "packet-lineage" {
                            vec![]
                        } else {
                            vec![state_id]
                        },
                        evidence_turn_ids,
                        suggested_context_patch: patch,
                        status: InterventionStatus::Open,
                        policy_version: self.policy.policy_version.clone(),
                    }
                },
            )
            .collect();
        let state = if interventions
            .iter()
            .any(|item| item.severity == InterventionSeverity::BlockingCommit)
        {
            EvaluationState::Conflict
        } else if interventions.is_empty() {
            EvaluationState::Pass
        } else {
            EvaluationState::Review
        };
        let correction_packet =
            (!interventions.is_empty()).then(|| correction_packet(&interventions));
        Ok(GovernanceResult {
            state,
            interventions,
            correction_packet,
            policy_version: self.policy.policy_version.clone(),
        })
    }

    fn severity(&self, code: InterventionCode) -> InterventionSeverity {
        match self
            .policy
            .severity
            .get(code_name(code))
            .map(String::as_str)
        {
            Some("blocking_commit") => InterventionSeverity::BlockingCommit,
            Some("info") => InterventionSeverity::Info,
            _ => InterventionSeverity::Warning,
        }
    }
}

fn rule_hit(
    rule: &LedgerRule,
    confidence: f64,
) -> (
    InterventionCode,
    String,
    String,
    Vec<String>,
    Option<String>,
    f64,
) {
    (
        rule.code,
        rule.summary.clone(),
        rule.state_id.clone(),
        rule.evidence_turn_ids.clone(),
        rule.suggested_context_patch.clone(),
        confidence,
    )
}

fn phrase_match(response_lower: &str, phrases: &[String]) -> bool {
    phrases
        .iter()
        .filter(|phrase| phrase.trim().len() >= 4)
        .any(|phrase| response_lower.contains(&phrase.to_lowercase()))
}

fn regex_escape(value: &str) -> String {
    let mut escaped = String::new();
    for character in value.chars() {
        if ".^$*+?()[]{}|\\".contains(character) {
            escaped.push('\\');
        }
        escaped.push(character);
    }
    escaped
}

fn bounded_excerpt(value: &str, max_chars: usize) -> String {
    value.chars().take(max_chars).collect()
}

fn code_name(code: InterventionCode) -> &'static str {
    match code {
        InterventionCode::Contradiction => "CONTRADICTION",
        InterventionCode::SupersededPathRevived => "SUPERSEDED_PATH_REVIVED",
        InterventionCode::ConstraintDropped => "CONSTRAINT_DROPPED",
        InterventionCode::ObjectiveDrift => "OBJECTIVE_DRIFT",
        InterventionCode::CompletedWorkReproposed => "COMPLETED_WORK_REPROPOSED",
        InterventionCode::UnsupportedStateChange => "UNSUPPORTED_STATE_CHANGE",
        InterventionCode::StaleEvidenceUsed => "STALE_EVIDENCE_USED",
        InterventionCode::WrongProjectContext => "WRONG_PROJECT_CONTEXT",
        InterventionCode::SupersessionWithoutReason => "SUPERSESSION_WITHOUT_REASON",
        InterventionCode::UnresolvedDependencyIgnored => "UNRESOLVED_DEPENDENCY_IGNORED",
        InterventionCode::ConceptDrift => "CONCEPT_DRIFT",
    }
}

fn deterministic_uuid(seed: &str) -> String {
    let digest = canonical_sha256(&seed).expect("string digest cannot fail");
    let hex = digest.trim_start_matches("sha256:");
    format!(
        "{}-{}-4{}-a{}-{}",
        &hex[0..8],
        &hex[8..12],
        &hex[13..16],
        &hex[17..20],
        &hex[20..32]
    )
}

fn correction_packet(interventions: &[Intervention]) -> String {
    let mut lines = vec!["[TOM_ASSIST_CORRECTION v1]".to_owned()];
    for item in interventions {
        lines.push(format!("- {}: {}", code_name(item.code), item.summary));
        if let Some(patch) = &item.suggested_context_patch {
            lines.push(format!("  CONTEXT_PATCH: {patch}"));
        }
    }
    lines.push("[/TOM_ASSIST_CORRECTION]".into());
    lines.join("\n")
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CandidateChannel {
    ManualUser,
    DeterministicVisibleTurn,
}

pub fn extract_candidates(
    project_id: &str,
    turn_id: &str,
    text: &str,
    channel: CandidateChannel,
) -> Vec<StateMutationCandidate> {
    let patterns = [
        ("Decision:", StateType::Decision),
        ("Constraint:", StateType::Constraint),
        ("Rejected:", StateType::RejectedPath),
        ("Completed:", StateType::CompletedWork),
        ("Unresolved:", StateType::UnresolvedDependency),
    ];
    text.lines()
        .filter_map(|line| {
            let trimmed = line.trim();
            let (prefix, object_type) = patterns
                .iter()
                .find(|(prefix, _)| trimmed.starts_with(prefix))?;
            let canonical_text = trimmed[prefix.len()..].trim();
            if canonical_text.is_empty() {
                return None;
            }
            let candidate_id = deterministic_uuid(&format!(
                "candidate\0{project_id}\0{turn_id}\0{prefix}\0{canonical_text}"
            ));
            Some(StateMutationCandidate {
                candidate_id,
                project_id: project_id.into(),
                source_turn_ids: vec![turn_id.into()],
                proposed_by: match channel {
                    CandidateChannel::ManualUser => Authority::User,
                    CandidateChannel::DeterministicVisibleTurn => Authority::ProviderCandidate,
                },
                operation: MutationOperation::Create,
                object: json!({
                    "type": serde_json::to_value(object_type).expect("state type serializes"),
                    "title": canonical_text.chars().take(80).collect::<String>(),
                    "canonical_text": canonical_text,
                    "status": "proposed",
                    "authority": match channel { CandidateChannel::ManualUser => "user", CandidateChannel::DeterministicVisibleTurn => "provider_candidate" },
                    "asserted_as_authoritative": false
                }),
                tom_check: TomCheck {
                    result: "candidate_only".into(),
                    conflicts: vec![],
                    requires_user_confirmation: true,
                },
            })
        })
        .collect()
}

#[derive(Debug, Clone, PartialEq)]
pub enum CommitGateDecision {
    Permit,
    Reject(ProtocolError),
}

pub fn commit_gate(
    object: &StateObject,
    base_state_version: u64,
    current_state_version: u64,
    user_confirmed: bool,
    open_interventions: &[Intervention],
) -> CommitGateDecision {
    let reject = |code, message: &str| {
        CommitGateDecision::Reject(ProtocolError {
            code,
            message: message.into(),
            retryable: false,
            remediation: Some("review the candidate and current project state".into()),
            correlation_id: object.id.clone(),
        })
    };
    if base_state_version != current_state_version {
        return reject(
            ErrorCode::StateVersionConflict,
            "candidate must rebase before commit",
        );
    }
    if !user_confirmed {
        return reject(
            ErrorCode::PermissionDenied,
            "explicit user confirmation is required",
        );
    }
    if matches!(
        object.authority,
        Authority::ProviderCandidate | Authority::LocalModelCandidate
    ) || object.status == StateStatus::Proposed
    {
        return reject(
            ErrorCode::PermissionDenied,
            "candidate authority cannot commit authoritative state",
        );
    }
    if open_interventions.iter().any(|intervention| {
        intervention.status == InterventionStatus::Open
            && intervention.severity == InterventionSeverity::BlockingCommit
    }) {
        return reject(
            ErrorCode::ValidationFailed,
            "blocking intervention must be resolved before commit",
        );
    }
    CommitGateDecision::Permit
}

pub fn false_positive_status() -> InterventionStatus {
    InterventionStatus::FalsePositive
}
