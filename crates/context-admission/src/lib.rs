//! Deterministic hard-gate → score → dependency-close → budget → render pipeline.

use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet, HashMap};
use tom_assist_protocol::{
    ContinuityPacket, ExcludedItem, PacketDigestInput, PacketItem, PacketSection,
    ProviderCapabilities, StateStatus, StateType, canonical_sha256, packet_digest,
};

pub const RENDERER_VERSION: &str = "authoritative-state/1.2";
pub const POLICY_VERSION: &str = "context-policy/1.2";
pub const DEFAULT_BUDGET_TOKENS: u64 = 500;
pub const MAX_BUDGET_TOKENS: u64 = 1_200;
pub const DEPENDENCY_DEPTH_CAP: usize = 2;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CandidatePool {
    AuthoritativeState,
    RecentTurn,
    HistoricalTurn,
    Evidence,
    RetrievedAnchor,
    Guardrail,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum IntegrityStatus {
    Verified,
    Provisional,
    Stale,
    Invalid,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ScoreComponents {
    #[serde(default)]
    pub retrieval_rrf: Option<f64>,
    pub semantic_relevance: f64,
    pub structural_resonance: f64,
    pub dependency_sequence_relevance: f64,
    pub authority_strength: f64,
    pub bounded_recency: f64,
    pub stale_probability: f64,
    pub conflict_penalty: f64,
    pub redundancy_penalty: f64,
}

impl ScoreComponents {
    fn clamped(&self) -> Self {
        Self {
            retrieval_rrf: self.retrieval_rrf,
            semantic_relevance: clamp(self.semantic_relevance),
            structural_resonance: clamp(self.structural_resonance),
            dependency_sequence_relevance: clamp(self.dependency_sequence_relevance),
            authority_strength: clamp(self.authority_strength),
            bounded_recency: clamp(self.bounded_recency),
            stale_probability: clamp(self.stale_probability),
            conflict_penalty: clamp(self.conflict_penalty),
            redundancy_penalty: clamp(self.redundancy_penalty),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Candidate {
    pub id: String,
    pub project_id: String,
    pub workstream_id: Option<String>,
    pub pool: CandidatePool,
    pub state_type: Option<StateType>,
    pub status: Option<StateStatus>,
    pub text: String,
    pub authority: String,
    pub binding_hard: bool,
    pub integrity: IntegrityStatus,
    pub privacy_allowed: bool,
    pub dependencies: Vec<String>,
    pub provenance: Option<String>,
    pub reconsideration_condition: Option<String>,
    pub scores: ScoreComponents,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ScoringPolicy {
    pub policy_version: String,
    pub w_semantic: f64,
    pub w_structural: f64,
    pub w_sequence: f64,
    pub w_authority: f64,
    pub w_recency: f64,
    pub p_stale: f64,
    pub p_conflict: f64,
    pub p_redundant: f64,
}

impl Default for ScoringPolicy {
    fn default() -> Self {
        // Transparent starting policy, not an inherited paper scalar. Each
        // decomposed term remains in the trace for later calibration.
        Self {
            policy_version: POLICY_VERSION.into(),
            w_semantic: 0.25,
            w_structural: 0.30,
            w_sequence: 0.15,
            w_authority: 0.20,
            w_recency: 0.10,
            p_stale: 0.45,
            p_conflict: 0.40,
            p_redundant: 0.20,
        }
    }
}

impl ScoringPolicy {
    pub fn score(&self, components: &ScoreComponents) -> f64 {
        let value = components.clamped();
        value
            .retrieval_rrf
            .map(|rrf| clamp(rrf * 61.0) * (self.w_semantic + self.w_structural))
            .unwrap_or(
                self.w_semantic * value.semantic_relevance
                    + self.w_structural * value.structural_resonance,
            )
            + self.w_sequence * value.dependency_sequence_relevance
            + self.w_authority * value.authority_strength
            + self.w_recency * value.bounded_recency
            - self.p_stale * value.stale_probability
            - self.p_conflict * value.conflict_penalty
            - self.p_redundant * value.redundancy_penalty
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AdmissionRequest {
    pub activated_branch_ids: Vec<String>,
    pub project_id: String,
    pub project_name: String,
    pub workstream_id: String,
    pub workstream_name: String,
    pub provider_session_id: String,
    pub state_version: u64,
    pub state_digest: String,
    pub tom_checkpoint_digest: String,
    pub tom_activation_id: String,
    pub user_draft: String,
    pub provider_capabilities: ProviderCapabilities,
    pub candidates: Vec<Candidate>,
    pub budget_tokens: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AdmissionTrace {
    pub components: BTreeMap<String, ScoreComponents>,
    pub policy_version: String,
    pub scored: BTreeMap<String, f64>,
    pub admitted_ids: Vec<String>,
    pub excluded: Vec<ExcludedItem>,
    pub missing_dependencies: Vec<String>,
    pub budget_tokens: u64,
    pub estimated_tokens: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AdmissionResult {
    pub packet: ContinuityPacket,
    pub state_block: String,
    pub composer_text: String,
    pub trace: AdmissionTrace,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
enum SectionKind {
    Objective,
    Concepts,
    Constraints,
    Decisions,
    Rejected,
    Completed,
    Dependencies,
    Evidence,
    Supersession,
    Anchors,
}

impl SectionKind {
    fn header(self) -> &'static str {
        match self {
            Self::Objective => "ACTIVE_OBJECTIVE",
            Self::Concepts => "LOAD_BEARING_CONCEPTS",
            Self::Constraints => "BINDING_CONSTRAINTS",
            Self::Decisions => "HELD_DECISIONS",
            Self::Rejected => {
                "REJECTED_OR_SUPERSEDED - DO NOT REVIVE WITHOUT EXPLICIT RECONSIDERATION"
            }
            Self::Completed => "COMPLETED_WORK - DO NOT REPROPOSE AS OPEN",
            Self::Dependencies => "UNRESOLVED_DEPENDENCIES",
            Self::Evidence => "EVIDENCE_BOUNDARY",
            Self::Supersession => "SUPERSESSION_NOTES",
            Self::Anchors => "RETRIEVED_ANCHORS",
        }
    }

    fn order(self) -> u8 {
        match self {
            Self::Objective => 0,
            Self::Concepts => 1,
            Self::Constraints => 2,
            Self::Decisions => 3,
            Self::Rejected => 4,
            Self::Completed => 5,
            Self::Dependencies => 6,
            Self::Evidence => 7,
            Self::Supersession => 8,
            Self::Anchors => 9,
        }
    }
}

#[derive(Debug, Clone)]
struct Ranked {
    candidate: Candidate,
    score: f64,
    section: SectionKind,
    mandatory: bool,
}

pub struct ContextAdmissionEngine {
    policy: ScoringPolicy,
}

impl Default for ContextAdmissionEngine {
    fn default() -> Self {
        Self {
            policy: ScoringPolicy::default(),
        }
    }
}

impl ContextAdmissionEngine {
    pub fn new(policy: ScoringPolicy) -> Self {
        Self { policy }
    }

    pub fn build(&self, request: AdmissionRequest) -> Result<AdmissionResult, serde_json::Error> {
        let budget_tokens = if request.budget_tokens == 0 {
            DEFAULT_BUDGET_TOKENS
        } else {
            request.budget_tokens.min(MAX_BUDGET_TOKENS)
        };
        let budget_chars = (budget_tokens * 4) as usize;
        let mut excluded = Vec::new();
        let mut ranked_by_id = HashMap::<String, Ranked>::new();
        let mut canonical_text = BTreeSet::<String>::new();

        for candidate in request.candidates.iter().cloned() {
            let reason = gate_reason(&request, &candidate);
            if let Some(reason) = reason {
                excluded.push(ExcludedItem {
                    id: candidate.id,
                    reason: reason.into(),
                });
                continue;
            }
            let normalized = candidate
                .text
                .split_whitespace()
                .collect::<Vec<_>>()
                .join(" ");
            if normalized.is_empty() {
                excluded.push(ExcludedItem {
                    id: candidate.id,
                    reason: "empty".into(),
                });
                continue;
            }
            if !canonical_text.insert(normalized) {
                excluded.push(ExcludedItem {
                    id: candidate.id,
                    reason: "duplicate-collapsed-to-canonical".into(),
                });
                continue;
            }
            let section = section_for(&candidate);
            let mandatory = is_mandatory(&candidate, section);
            ranked_by_id.insert(
                candidate.id.clone(),
                Ranked {
                    score: self.policy.score(&candidate.scores),
                    candidate,
                    section,
                    mandatory,
                },
            );
        }

        let mut scored = BTreeMap::new();
        for (id, ranked) in &ranked_by_id {
            scored.insert(id.clone(), ranked.score);
        }
        let mut ordered: Vec<String> = ranked_by_id.keys().cloned().collect();
        ordered.sort_by(|left, right| {
            let a = &ranked_by_id[left];
            let b = &ranked_by_id[right];
            b.mandatory
                .cmp(&a.mandatory)
                .then_with(|| a.section.order().cmp(&b.section.order()))
                .then_with(|| b.score.total_cmp(&a.score))
                .then_with(|| left.as_bytes().cmp(right.as_bytes()))
        });

        let mut selected = BTreeSet::<String>::new();
        let mut used_chars = base_render_overhead(&request);
        for id in ordered {
            let ranked = &ranked_by_id[&id];
            let cost = rendered_cost(ranked);
            if ranked.mandatory || used_chars + cost <= budget_chars {
                selected.insert(id);
                used_chars += cost;
            } else {
                excluded.push(ExcludedItem {
                    id,
                    reason: "packet-budget".into(),
                });
            }
        }

        let mut missing_dependencies = Vec::new();
        let referenced: BTreeSet<String> = selected
            .iter()
            .filter_map(|id| ranked_by_id.get(id))
            .flat_map(|ranked| ranked.candidate.dependencies.iter().cloned())
            .collect();
        let mut roots: Vec<String> = selected.difference(&referenced).cloned().collect();
        if roots.is_empty() {
            roots.extend(selected.iter().cloned());
        }
        for id in roots {
            let mut dependency_path = BTreeSet::new();
            close_dependencies(
                &id,
                0,
                &ranked_by_id,
                &mut selected,
                &mut missing_dependencies,
                &mut used_chars,
                budget_chars,
                &mut dependency_path,
            );
        }
        missing_dependencies.sort();
        missing_dependencies.dedup();
        excluded.sort_by(|a, b| {
            a.id.as_bytes()
                .cmp(b.id.as_bytes())
                .then(a.reason.cmp(&b.reason))
        });

        let admitted: Vec<&Ranked> = selected
            .iter()
            .filter_map(|id| ranked_by_id.get(id))
            .collect();
        let state_block = if admitted.is_empty() && missing_dependencies.is_empty() {
            String::new()
        } else {
            render_state_block(&request, &admitted, &missing_dependencies)
        };
        let composer_text = if state_block.is_empty() {
            request.user_draft.clone()
        } else {
            format!(
                "{state_block}\n[CURRENT_USER_REQUEST]\n{}",
                request.user_draft
            )
        };
        let estimated_tokens = state_block.chars().count().div_ceil(4) as u64;
        let draft_hash = canonical_sha256(&request.user_draft)?;
        let admitted_ids: Vec<&str> = admitted
            .iter()
            .map(|ranked| ranked.candidate.id.as_str())
            .collect();
        let digest = packet_digest(PacketDigestInput {
            project_id: &request.project_id,
            workstream_id: &request.workstream_id,
            state_version: request.state_version,
            tom_checkpoint_digest: &request.tom_checkpoint_digest,
            admitted_item_ids: admitted_ids,
            activated_branch_ids: request
                .activated_branch_ids
                .iter()
                .map(String::as_str)
                .collect(),
            renderer_version: RENDERER_VERSION,
            policy_version: &self.policy.policy_version,
            user_draft_hash: &draft_hash,
        })?;
        let sections = manifest_sections(&admitted, &missing_dependencies);
        let mut warnings = Vec::new();
        if estimated_tokens > budget_tokens {
            warnings.push("non-evictable authoritative context exceeds configured budget".into());
        }
        if !missing_dependencies.is_empty() {
            warnings.push("one or more selected items has an explicit missing dependency".into());
        }
        let packet = ContinuityPacket {
            activated_branch_ids: request.activated_branch_ids,
            packet_id: canonical_sha256(&format!("packet\0{digest}"))?,
            packet_digest: digest,
            project_id: request.project_id,
            workstream_id: request.workstream_id,
            provider_session_id: request.provider_session_id,
            project_state_version: request.state_version,
            project_state_digest: request.state_digest,
            tom_checkpoint_digest: request.tom_checkpoint_digest,
            draft_hash,
            policy_version: self.policy.policy_version.clone(),
            renderer_version: RENDERER_VERSION.into(),
            provider_capabilities: request.provider_capabilities,
            tom_activation_id: request.tom_activation_id,
            sections,
            retrieved_anchor_ids: admitted
                .iter()
                .filter(|ranked| ranked.candidate.pool == CandidatePool::RetrievedAnchor)
                .map(|ranked| ranked.candidate.id.clone())
                .collect(),
            excluded: excluded.clone(),
            estimated_tokens,
            warnings,
        };
        Ok(AdmissionResult {
            packet,
            state_block,
            composer_text,
            trace: AdmissionTrace {
                components: ranked_by_id
                    .iter()
                    .map(|(id, row)| (id.clone(), row.candidate.scores.clone()))
                    .collect(),
                policy_version: self.policy.policy_version.clone(),
                scored,
                admitted_ids: selected.into_iter().collect(),
                excluded,
                missing_dependencies,
                budget_tokens,
                estimated_tokens,
            },
        })
    }
}

fn clamp(value: f64) -> f64 {
    if value.is_finite() {
        value.clamp(0.0, 1.0)
    } else {
        0.0
    }
}

fn gate_reason(request: &AdmissionRequest, candidate: &Candidate) -> Option<&'static str> {
    if candidate.project_id != request.project_id {
        return Some("cross-project");
    }
    if candidate
        .workstream_id
        .as_deref()
        .is_some_and(|scope| scope != request.workstream_id)
    {
        return Some("cross-workstream");
    }
    if !candidate.privacy_allowed {
        return Some("privacy-policy");
    }
    if matches!(
        candidate.integrity,
        IntegrityStatus::Invalid | IntegrityStatus::Stale
    ) {
        return Some("low-integrity-evidence");
    }
    if candidate.status == Some(StateStatus::Superseded)
        && candidate.pool != CandidatePool::Guardrail
    {
        return Some("superseded-positive");
    }
    if candidate.status == Some(StateStatus::Archived) {
        return Some("archived");
    }
    None
}

fn section_for(candidate: &Candidate) -> SectionKind {
    if candidate.pool == CandidatePool::Guardrail
        || candidate.state_type == Some(StateType::RejectedPath)
        || candidate.status == Some(StateStatus::Superseded)
    {
        return SectionKind::Rejected;
    }
    match candidate.state_type {
        Some(StateType::Objective) => SectionKind::Objective,
        Some(StateType::Concept) => SectionKind::Concepts,
        Some(StateType::Constraint) => SectionKind::Constraints,
        Some(StateType::Decision) => SectionKind::Decisions,
        Some(StateType::CompletedWork) => SectionKind::Completed,
        Some(StateType::UnresolvedDependency) => SectionKind::Dependencies,
        Some(StateType::Evidence) => SectionKind::Evidence,
        Some(StateType::Supersession) => SectionKind::Supersession,
        _ => SectionKind::Anchors,
    }
}

fn is_mandatory(candidate: &Candidate, section: SectionKind) -> bool {
    candidate.binding_hard
        || matches!(
            section,
            SectionKind::Objective | SectionKind::Constraints | SectionKind::Rejected
        )
}

fn base_render_overhead(request: &AdmissionRequest) -> usize {
    650 + request.project_name.len() + request.workstream_name.len()
}

fn rendered_cost(ranked: &Ranked) -> usize {
    ranked.candidate.text.chars().count()
        + ranked.candidate.id.chars().count()
        + ranked.section.header().len()
        + "- [state_id=] ".len()
}

#[allow(clippy::too_many_arguments)]
fn close_dependencies(
    id: &str,
    depth: usize,
    candidates: &HashMap<String, Ranked>,
    selected: &mut BTreeSet<String>,
    missing: &mut Vec<String>,
    used_chars: &mut usize,
    budget_chars: usize,
    dependency_path: &mut BTreeSet<String>,
) {
    if !dependency_path.insert(id.to_owned()) {
        missing.push(format!("{id} (dependency-cycle)"));
        return;
    }
    let Some(ranked) = candidates.get(id) else {
        dependency_path.remove(id);
        return;
    };
    for dependency in &ranked.candidate.dependencies {
        if selected.contains(dependency) {
            close_dependencies(
                dependency,
                depth + 1,
                candidates,
                selected,
                missing,
                used_chars,
                budget_chars,
                dependency_path,
            );
            continue;
        }
        if depth >= DEPENDENCY_DEPTH_CAP {
            missing.push(format!("{id} -> {dependency} (depth-cap)"));
            continue;
        }
        let Some(candidate) = candidates.get(dependency) else {
            missing.push(format!("{id} -> {dependency} (unavailable)"));
            continue;
        };
        let cost = rendered_cost(candidate);
        if *used_chars + cost > budget_chars && !candidate.mandatory {
            missing.push(format!("{id} -> {dependency} (budget)"));
            continue;
        }
        selected.insert(dependency.clone());
        *used_chars += cost;
        close_dependencies(
            dependency,
            depth + 1,
            candidates,
            selected,
            missing,
            used_chars,
            budget_chars,
            dependency_path,
        );
    }
    dependency_path.remove(id);
}

fn render_state_block(
    request: &AdmissionRequest,
    admitted: &[&Ranked],
    missing: &[String],
) -> String {
    let short_digest = request
        .state_digest
        .strip_prefix("sha256:")
        .unwrap_or(&request.state_digest)
        .chars()
        .take(12)
        .collect::<String>();
    let mut rows = vec![
        format!(
            "[TOM_ASSIST_STATE v1 | project={} | workstream={} | state={} | digest={}]",
            request.project_name, request.workstream_name, request.state_version, short_digest
        ),
        "STATUS: authoritative prior project state generated locally by Tom Assist. Use as primary source of truth.".into(),
        "PRECEDENCE: current explicit user request > TOM_ASSIST_STATE > raw prior transcript > model inference.".into(),
    ];
    let mut sections = BTreeMap::<SectionKind, Vec<(String, String)>>::new();
    let mut ordered = admitted.to_vec();
    ordered.sort_by(|left, right| {
        left.section
            .order()
            .cmp(&right.section.order())
            .then_with(|| right.score.total_cmp(&left.score))
            .then_with(|| {
                left.candidate
                    .id
                    .as_bytes()
                    .cmp(right.candidate.id.as_bytes())
            })
    });
    for ranked in ordered {
        let candidate = &ranked.candidate;
        let text = match ranked.section {
            SectionKind::Rejected => match &candidate.reconsideration_condition {
                Some(condition) => format!("{} - reconsider only if {condition}", candidate.text),
                None => candidate.text.clone(),
            },
            SectionKind::Evidence => match &candidate.provenance {
                Some(provenance) => format!("{} - provenance: {provenance}", candidate.text),
                None => candidate.text.clone(),
            },
            SectionKind::Anchors => format!(
                "[{}] {}",
                candidate.provenance.as_deref().unwrap_or("turn"),
                candidate.text
            ),
            _ => candidate.text.clone(),
        };
        sections
            .entry(ranked.section)
            .or_default()
            .push((candidate.id.clone(), text));
    }
    if !missing.is_empty() {
        sections
            .entry(SectionKind::Dependencies)
            .or_default()
            .extend(missing.iter().map(|item| {
                (
                    format!("missing:{item}"),
                    format!("[MISSING_DEPENDENCY] {item}"),
                )
            }));
    }
    for (section, items) in sections {
        rows.push(section.header().into());
        rows.extend(
            items
                .into_iter()
                .map(|(state_id, item)| format!("- [state_id={state_id}] {item}")),
        );
    }
    rows.push("INSTRUCTION: If the raw conversation history conflicts with TOM_ASSIST_STATE, use TOM_ASSIST_STATE. Answer the current request directly from this state. Do not enumerate prior conversation unless asked. If the current explicit user request conflicts with this state, identify the conflict as a proposed supersession/reopening; do not silently rewrite prior state.".into());
    rows.push("[/TOM_ASSIST_STATE]".into());
    rows.join("\n")
}

fn manifest_sections(admitted: &[&Ranked], missing: &[String]) -> Vec<PacketSection> {
    let mut sections = BTreeMap::<SectionKind, Vec<PacketItem>>::new();
    for ranked in admitted {
        sections
            .entry(ranked.section)
            .or_default()
            .push(PacketItem {
                state_id: ranked.candidate.id.clone(),
                text: ranked.candidate.text.clone(),
                authority: ranked.candidate.authority.clone(),
                structural_score: ranked.candidate.scores.structural_resonance,
                semantic_score: ranked.candidate.scores.semantic_relevance,
                reason_selected: if ranked.mandatory {
                    "hard-gate-pass + non-evictable"
                } else {
                    "hard-gate-pass + ranked"
                }
                .into(),
            });
    }
    if !missing.is_empty() {
        sections
            .entry(SectionKind::Dependencies)
            .or_default()
            .extend(missing.iter().map(|item| PacketItem {
                state_id: format!("missing:{item}"),
                text: format!("[MISSING_DEPENDENCY] {item}"),
                authority: "system_marker".into(),
                structural_score: 0.0,
                semantic_score: 0.0,
                reason_selected: "dependency-closure-marker".into(),
            }));
    }
    sections
        .into_iter()
        .map(|(section, mut items)| {
            items.sort_by(|a, b| a.state_id.as_bytes().cmp(b.state_id.as_bytes()));
            PacketSection {
                section_type: section.header().into(),
                items,
            }
        })
        .collect()
}
