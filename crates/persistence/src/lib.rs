//! Event-sourced SQLite persistence with deterministic canonical digests.
pub mod conversations;
pub mod recovery;

use rusqlite::{
    Connection, OpenFlags, OptionalExtension, Transaction, TransactionBehavior, params,
};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fmt::{Display, Formatter};
use std::fs;
use std::path::{Path, PathBuf};
use tom_assist_protocol::{
    Authority, Intervention, InterventionStatus, StateEdge, StateMutationCandidate, StateObject,
    StateStatus, canonical_sha256,
};

pub const STATE_SCHEMA_VERSION: &str = "state-schema/1";
pub const EVENT_SCHEMA_VERSION: &str = "event-schema/1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StoreMode {
    ReadWrite,
    ReadOnlySafe,
}

pub struct RecoveredStore {
    pub store: Store,
    pub mode: StoreMode,
    pub backup_path: Option<PathBuf>,
    pub migration_error: Option<String>,
}

#[derive(Debug)]
pub enum StoreError {
    Sql(rusqlite::Error),
    Json(serde_json::Error),
    Io(std::io::Error),
    ProjectNotFound(String),
    StateVersionConflict { expected: u64, actual: u64 },
    CandidateAuthority,
    Integrity(String),
    EncryptionUnavailable,
}

impl Display for StoreError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Sql(error) => write!(f, "database error: {error}"),
            Self::Json(error) => write!(f, "JSON error: {error}"),
            Self::Io(error) => write!(f, "I/O error: {error}"),
            Self::ProjectNotFound(id) => write!(f, "project not found: {id}"),
            Self::StateVersionConflict { expected, actual } => {
                write!(
                    f,
                    "state version conflict: expected {expected}, actual {actual}"
                )
            }
            Self::CandidateAuthority => {
                write!(f, "candidate authority cannot commit authoritative state")
            }
            Self::Integrity(message) => write!(f, "integrity error: {message}"),
            Self::EncryptionUnavailable => {
                write!(f, "encrypted-store key loading is not wired in alpha")
            }
        }
    }
}

impl std::error::Error for StoreError {}
impl From<rusqlite::Error> for StoreError {
    fn from(value: rusqlite::Error) -> Self {
        Self::Sql(value)
    }
}
impl From<serde_json::Error> for StoreError {
    fn from(value: serde_json::Error) -> Self {
        Self::Json(value)
    }
}
impl From<std::io::Error> for StoreError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value)
    }
}

pub type Result<T> = std::result::Result<T, StoreError>;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Project {
    pub id: String,
    pub name: String,
    pub status: String,
    pub created_at: String,
    pub updated_at: String,
    pub state_version: u64,
    pub state_digest: String,
    pub retention_profile: String,
    pub policy_profile: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EventRecord {
    pub id: String,
    pub project_id: String,
    pub event_type: String,
    pub actor_type: String,
    pub actor_id: String,
    pub payload: EventPayload,
    pub idempotency_key: String,
    pub base_state_version: u64,
    pub prior_digest: String,
    pub resulting_digest: String,
    pub created_at: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum EventPayload {
    ProjectCreated {
        name: String,
        retention_profile: String,
        policy_profile: String,
    },
    Mutation {
        upserts: Vec<StateObject>,
        edges: Vec<StateEdge>,
    },
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CanonicalState {
    pub project_id: String,
    pub state_version: u64,
    pub objects: Vec<StateObject>,
    pub edges: Vec<StateEdge>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Snapshot {
    pub id: String,
    pub project_id: String,
    pub state_version: u64,
    pub state_digest: String,
    pub tom_checkpoint_digest: String,
    pub runtime_version: String,
    pub state_json: String,
    pub verified_at: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ContextRunRecord {
    pub activated_branch_ids: Vec<String>,
    pub admitted_anchor_ids: Vec<String>,
    pub candidate_trace_json: String,
    pub id: String,
    pub project_id: String,
    pub workstream_id: String,
    pub provider_session_id: String,
    pub draft_hash: String,
    pub state_version: u64,
    pub tom_checkpoint_digest: String,
    pub activation_id: String,
    pub policy_version: String,
    pub renderer_version: String,
    pub selected_json: String,
    pub excluded_json: String,
    pub packet_text: String,
    pub packet_digest: String,
    pub estimated_tokens: u64,
    pub latency_ms: u64,
    pub created_at: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TurnRecord {
    pub id: String,
    pub session_id: String,
    pub project_id: String,
    pub workstream_id: String,
    pub role: String,
    pub ordinal: u64,
    pub normalized_text: String,
    pub content_hash: String,
    pub packet_digest: String,
    pub completeness: String,
    pub captured_at: String,
    pub provider_timestamp: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ResponseEvaluationRecord {
    pub id: String,
    pub project_id: String,
    pub turn_id: String,
    pub packet_digest: String,
    pub state_version: u64,
    pub result: String,
    pub intervention_ids: Vec<String>,
    pub policy_version: String,
    pub latency_ms: u64,
    pub created_at: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct InterventionRecord {
    pub id: String,
    pub project_id: String,
    pub turn_id: String,
    pub code: String,
    pub severity: String,
    pub confidence: f64,
    pub summary: String,
    pub conflicting_state_ids: Vec<String>,
    pub status: String,
    pub policy_version: String,
    pub created_at: String,
    pub resolved_at: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AuditRecord {
    pub project_id: String,
    pub category: String,
    pub correlation_id: String,
    pub details: serde_json::Value,
    pub created_at: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
struct ExportManifest {
    format: String,
    project_id: String,
    state_schema_version: String,
    event_schema_version: String,
    files: BTreeMap<String, String>,
}

pub struct Store {
    connection: Connection,
    path: PathBuf,
}

impl Store {
    pub fn open(path: impl AsRef<Path>) -> Result<Self> {
        let path = path.as_ref().to_path_buf();
        let connection = Connection::open(&path)?;
        connection.execute_batch(
            "PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;",
        )?;
        connection.execute_batch(include_str!("../migrations/001_init.sql"))?;
        connection.execute_batch(include_str!("../migrations/002_context_manifests.sql"))?;
        connection.execute_batch(include_str!("../migrations/003_runtime_commits.sql"))?;
        connection.execute_batch(include_str!("../migrations/004_recovery.sql"))?;
        connection.execute_batch(include_str!("../migrations/005_conversations.sql"))?;
        connection.execute_batch(include_str!("../migrations/006_self_reports.sql"))?;
        Ok(Self { connection, path })
    }

    pub fn open_memory() -> Result<Self> {
        let connection = Connection::open_in_memory()?;
        connection.execute_batch("PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL;")?;
        connection.execute_batch(include_str!("../migrations/001_init.sql"))?;
        connection.execute_batch(include_str!("../migrations/002_context_manifests.sql"))?;
        connection.execute_batch(include_str!("../migrations/003_runtime_commits.sql"))?;
        connection.execute_batch(include_str!("../migrations/004_recovery.sql"))?;
        connection.execute_batch(include_str!("../migrations/005_conversations.sql"))?;
        connection.execute_batch(include_str!("../migrations/006_self_reports.sql"))?;
        Ok(Self {
            connection,
            path: PathBuf::from(":memory:"),
        })
    }

    /// Preserve a failing database byte-for-byte and reopen it read-only so the
    /// UI can offer diagnostics/export rather than attempting further writes.
    pub fn open_with_recovery(path: impl AsRef<Path>) -> Result<RecoveredStore> {
        let path = path.as_ref().to_path_buf();
        match Self::open(&path) {
            Ok(store) => Ok(RecoveredStore {
                store,
                mode: StoreMode::ReadWrite,
                backup_path: None,
                migration_error: None,
            }),
            Err(error) if path.exists() => {
                let backup = path.with_extension("migration-failed.bak");
                if backup.exists() {
                    return Err(StoreError::Integrity(format!(
                        "refusing to overwrite migration backup: {}",
                        backup.display()
                    )));
                }
                fs::copy(&path, &backup)?;
                let connection = Connection::open_with_flags(
                    &path,
                    OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
                )?;
                Ok(RecoveredStore {
                    store: Self { connection, path },
                    mode: StoreMode::ReadOnlySafe,
                    backup_path: Some(backup),
                    migration_error: Some(error.to_string()),
                })
            }
            Err(error) => Err(error),
        }
    }

    #[cfg(feature = "encrypted-store")]
    pub fn open_encrypted(_path: impl AsRef<Path>) -> Result<Self> {
        Err(StoreError::EncryptionUnavailable)
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn create_project(
        &mut self,
        id: &str,
        name: &str,
        retention_profile: &str,
        policy_profile: &str,
        actor_id: &str,
        idempotency_key: &str,
        created_at: &str,
    ) -> Result<Project> {
        if let Some(project) = self.project(id)? {
            return Ok(project);
        }
        let empty = CanonicalState {
            project_id: id.to_owned(),
            state_version: 0,
            objects: vec![],
            edges: vec![],
        };
        let digest = canonical_sha256(&empty)?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        transaction.execute(
            "INSERT INTO projects(id,name,status,created_at,updated_at,state_version,state_digest,retention_profile,policy_profile) VALUES(?1,?2,'active',?3,?3,0,?4,?5,?6)",
            params![id, name, created_at, digest, retention_profile, policy_profile],
        )?;
        let payload = EventPayload::ProjectCreated {
            name: name.to_owned(),
            retention_profile: retention_profile.to_owned(),
            policy_profile: policy_profile.to_owned(),
        };
        let event_id = event_id(id, idempotency_key, "PROJECT_CREATED");
        transaction.execute(
            "INSERT INTO state_events(id,project_id,event_type,actor_type,actor_id,payload_json,idempotency_key,base_state_version,prior_digest,resulting_digest,created_at) VALUES(?1,?2,'PROJECT_CREATED','user',?3,?4,?5,0,?6,?6,?7)",
            params![event_id, id, actor_id, serde_json::to_string(&payload)?, idempotency_key, digest, created_at],
        )?;
        transaction.commit()?;
        self.project(id)?
            .ok_or_else(|| StoreError::ProjectNotFound(id.to_owned()))
    }

    pub fn project(&self, project_id: &str) -> Result<Option<Project>> {
        self.connection.query_row(
            "SELECT id,name,status,created_at,updated_at,state_version,state_digest,retention_profile,policy_profile FROM projects WHERE id=?1",
            [project_id],
            |row| Ok(Project { id: row.get(0)?, name: row.get(1)?, status: row.get(2)?, created_at: row.get(3)?, updated_at: row.get(4)?, state_version: row.get(5)?, state_digest: row.get(6)?, retention_profile: row.get(7)?, policy_profile: row.get(8)? }),
        ).optional().map_err(Into::into)
    }

    pub fn list_projects(&self) -> Result<Vec<Project>> {
        let mut statement = self.connection.prepare(
            "SELECT id,name,status,created_at,updated_at,state_version,state_digest,retention_profile,policy_profile FROM projects ORDER BY updated_at DESC,id",
        )?;
        let rows = statement.query_map([], |row| {
            Ok(Project {
                id: row.get(0)?,
                name: row.get(1)?,
                status: row.get(2)?,
                created_at: row.get(3)?,
                updated_at: row.get(4)?,
                state_version: row.get(5)?,
                state_digest: row.get(6)?,
                retention_profile: row.get(7)?,
                policy_profile: row.get(8)?,
            })
        })?;
        rows.map(|row| row.map_err(Into::into)).collect()
    }

    pub fn record_candidate(
        &self,
        candidate: &StateMutationCandidate,
        created_at: &str,
    ) -> Result<()> {
        if self.project(&candidate.project_id)?.is_none() {
            return Err(StoreError::ProjectNotFound(candidate.project_id.clone()));
        }
        let proposed_by = serde_json::to_value(candidate.proposed_by)?
            .as_str()
            .ok_or_else(|| {
                StoreError::Integrity("candidate authority did not serialize as text".into())
            })?
            .to_owned();
        let operation = serde_json::to_value(candidate.operation)?
            .as_str()
            .ok_or_else(|| {
                StoreError::Integrity("candidate operation did not serialize as text".into())
            })?
            .to_owned();
        self.connection.execute(
            "INSERT OR IGNORE INTO state_mutation_candidates(id,project_id,source_turn_id,proposed_by,operation,payload_json,status,created_at,resolved_at) VALUES(?1,?2,?3,?4,?5,?6,'proposed',?7,NULL)",
            params![
                candidate.candidate_id,
                candidate.project_id,
                candidate.source_turn_ids.first(),
                proposed_by,
                operation,
                serde_json::to_string(candidate)?,
                created_at,
            ],
        )?;
        Ok(())
    }

    pub fn candidate(&self, candidate_id: &str) -> Result<Option<StateMutationCandidate>> {
        let payload: Option<String> = self
            .connection
            .query_row(
                "SELECT payload_json FROM state_mutation_candidates WHERE id=?1",
                [candidate_id],
                |row| row.get(0),
            )
            .optional()?;
        payload
            .map(|value| serde_json::from_str(&value).map_err(Into::into))
            .transpose()
    }

    pub fn update_project_metadata(
        &self,
        project_id: &str,
        name: &str,
        status: &str,
        updated_at: &str,
    ) -> Result<Project> {
        let changed = self.connection.execute(
            "UPDATE projects SET name=?2,status=?3,updated_at=?4 WHERE id=?1",
            params![project_id, name, status, updated_at],
        )?;
        if changed != 1 {
            return Err(StoreError::ProjectNotFound(project_id.into()));
        }
        self.audit(
            project_id,
            "PROJECT_METADATA_UPDATED",
            project_id,
            &serde_json::json!({"name":name,"status":status}),
            updated_at,
        )?;
        self.project(project_id)?
            .ok_or_else(|| StoreError::ProjectNotFound(project_id.into()))
    }

    pub fn commit_object(
        &mut self,
        mut object: StateObject,
        base_state_version: u64,
        actor_type: &str,
        actor_id: &str,
        idempotency_key: &str,
        created_at: &str,
    ) -> Result<EventRecord> {
        if matches!(
            object.authority,
            Authority::ProviderCandidate | Authority::LocalModelCandidate
        ) {
            return Err(StoreError::CandidateAuthority);
        }
        object.state_version = base_state_version + 1;
        self.commit_mutation(
            object.project_id.clone(),
            vec![object],
            vec![],
            base_state_version,
            actor_type,
            actor_id,
            idempotency_key,
            created_at,
            "STATE_COMMITTED",
        )
    }

    pub fn supersede(
        &mut self,
        project_id: &str,
        old_id: &str,
        mut replacement: StateObject,
        reason: &str,
        base_state_version: u64,
        actor_id: &str,
        idempotency_key: &str,
        created_at: &str,
    ) -> Result<EventRecord> {
        if reason.trim().is_empty() {
            return Err(StoreError::Integrity(
                "supersession reason is required".into(),
            ));
        }
        let mut old = self
            .state_object(project_id, old_id)?
            .ok_or_else(|| StoreError::Integrity(format!("state object not found: {old_id}")))?;
        old.status = StateStatus::Superseded;
        old.updated_at = created_at.to_owned();
        old.state_version = base_state_version + 1;
        replacement.project_id = project_id.to_owned();
        replacement.supersedes_id = Some(old_id.to_owned());
        replacement.state_version = base_state_version + 1;
        let edge = StateEdge {
            id: event_id(project_id, idempotency_key, "edge"),
            project_id: project_id.to_owned(),
            from_state_id: replacement.id.clone(),
            edge_type: tom_assist_protocol::EdgeType::Supersedes,
            to_state_id: old_id.to_owned(),
            created_event_id: event_id(project_id, idempotency_key, "STATE_SUPERSEDED"),
        };
        self.commit_mutation(
            project_id.to_owned(),
            vec![old, replacement],
            vec![edge],
            base_state_version,
            "user",
            actor_id,
            idempotency_key,
            created_at,
            "STATE_SUPERSEDED",
        )
    }

    #[allow(clippy::too_many_arguments)]
    fn commit_mutation(
        &mut self,
        project_id: String,
        upserts: Vec<StateObject>,
        edges: Vec<StateEdge>,
        base_state_version: u64,
        actor_type: &str,
        actor_id: &str,
        idempotency_key: &str,
        created_at: &str,
        event_type: &str,
    ) -> Result<EventRecord> {
        if let Some(existing) = self.event_by_idempotency(&project_id, idempotency_key)? {
            return Ok(existing);
        }
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        let (current_version, prior_digest): (u64, String) = transaction
            .query_row(
                "SELECT state_version,state_digest FROM projects WHERE id=?1",
                [&project_id],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .optional()?
            .ok_or_else(|| StoreError::ProjectNotFound(project_id.clone()))?;
        if current_version != base_state_version {
            return Err(StoreError::StateVersionConflict {
                expected: base_state_version,
                actual: current_version,
            });
        }
        let next_version = current_version + 1;
        for object in &upserts {
            upsert_state_object(&transaction, object)?;
        }
        for edge in &edges {
            insert_edge(&transaction, edge)?;
        }
        let state = load_canonical_state(&transaction, &project_id, next_version)?;
        let resulting_digest = canonical_sha256(&state)?;
        let payload = EventPayload::Mutation { upserts, edges };
        let id = event_id(&project_id, idempotency_key, event_type);
        transaction.execute(
            "INSERT INTO state_events(id,project_id,event_type,actor_type,actor_id,payload_json,idempotency_key,base_state_version,prior_digest,resulting_digest,created_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11)",
            params![id, project_id, event_type, actor_type, actor_id, serde_json::to_string(&payload)?, idempotency_key, base_state_version, prior_digest, resulting_digest, created_at],
        )?;
        transaction.execute(
            "UPDATE projects SET state_version=?2,state_digest=?3,updated_at=?4 WHERE id=?1",
            params![project_id, next_version, resulting_digest, created_at],
        )?;
        transaction.commit()?;
        self.event_by_idempotency(&project_id, idempotency_key)?
            .ok_or_else(|| StoreError::Integrity("committed event missing".into()))
    }

    pub fn state_object(&self, project_id: &str, object_id: &str) -> Result<Option<StateObject>> {
        let value: Option<String> = self
            .connection
            .query_row(
                "SELECT object_json FROM state_objects WHERE project_id=?1 AND id=?2",
                params![project_id, object_id],
                |row| row.get(0),
            )
            .optional()?;
        value
            .map(|json| serde_json::from_str(&json).map_err(Into::into))
            .transpose()
    }

    pub fn current_state(&self, project_id: &str) -> Result<CanonicalState> {
        let version = self
            .project(project_id)?
            .ok_or_else(|| StoreError::ProjectNotFound(project_id.to_owned()))?
            .state_version;
        load_canonical_state(&self.connection, project_id, version)
    }

    pub fn replay(&self, project_id: &str) -> Result<CanonicalState> {
        let mut statement = self.connection.prepare("SELECT payload_json,base_state_version,resulting_digest FROM state_events WHERE project_id=?1 ORDER BY rowid")?;
        let rows = statement.query_map([project_id], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, u64>(1)?,
                row.get::<_, String>(2)?,
            ))
        })?;
        let mut objects = BTreeMap::new();
        let mut edges = BTreeMap::new();
        let mut version = 0;
        for row in rows {
            let (payload_json, base_version, expected_digest) = row?;
            match serde_json::from_str::<EventPayload>(&payload_json)? {
                EventPayload::ProjectCreated { .. } => {}
                EventPayload::Mutation {
                    upserts,
                    edges: additions,
                } => {
                    if base_version != version {
                        return Err(StoreError::Integrity(
                            "non-contiguous event versions".into(),
                        ));
                    }
                    version += 1;
                    for object in upserts {
                        objects.insert(object.id.clone(), object);
                    }
                    for edge in additions {
                        edges.insert(edge.id.clone(), edge);
                    }
                    let state = CanonicalState {
                        project_id: project_id.to_owned(),
                        state_version: version,
                        objects: objects.values().cloned().collect(),
                        edges: edges.values().cloned().collect(),
                    };
                    if canonical_sha256(&state)? != expected_digest {
                        return Err(StoreError::Integrity(format!(
                            "event digest mismatch at version {version}"
                        )));
                    }
                }
            }
        }
        Ok(CanonicalState {
            project_id: project_id.to_owned(),
            state_version: version,
            objects: objects.into_values().collect(),
            edges: edges.into_values().collect(),
        })
    }

    pub fn create_snapshot(
        &mut self,
        project_id: &str,
        tom_checkpoint_digest: &str,
        runtime_version: &str,
        verified_at: &str,
    ) -> Result<Snapshot> {
        let state = self.current_state(project_id)?;
        let state_digest = canonical_sha256(&state)?;
        let id = event_id(project_id, &state_digest, "snapshot");
        let state_json = String::from_utf8(tom_assist_protocol::canonical_json(&state)?)
            .map_err(|error| StoreError::Integrity(error.to_string()))?;
        self.connection.execute(
            "INSERT OR IGNORE INTO snapshots(id,project_id,state_version,state_digest,tom_checkpoint_digest,runtime_version,schema_versions_json,archive_path,state_json,verified_at) VALUES(?1,?2,?3,?4,?5,?6,?7,'',?8,?9)",
            params![id, project_id, state.state_version, state_digest, tom_checkpoint_digest, runtime_version, serde_json::json!({"state":STATE_SCHEMA_VERSION,"events":EVENT_SCHEMA_VERSION}).to_string(), state_json, verified_at],
        )?;
        Ok(Snapshot {
            id,
            project_id: project_id.to_owned(),
            state_version: state.state_version,
            state_digest,
            tom_checkpoint_digest: tom_checkpoint_digest.to_owned(),
            runtime_version: runtime_version.to_owned(),
            state_json,
            verified_at: verified_at.to_owned(),
        })
    }

    pub fn verify_snapshot(&self, snapshot: &Snapshot) -> Result<()> {
        let state: CanonicalState = serde_json::from_str(&snapshot.state_json)?;
        if state.project_id != snapshot.project_id
            || state.state_version != snapshot.state_version
            || canonical_sha256(&state)? != snapshot.state_digest
        {
            return Err(StoreError::Integrity(
                "snapshot identity or digest mismatch".into(),
            ));
        }
        Ok(())
    }

    pub fn export_project(&self, project_id: &str, directory: impl AsRef<Path>) -> Result<PathBuf> {
        let directory = directory.as_ref();
        fs::create_dir_all(directory)?;
        let state = self.current_state(project_id)?;
        let events = self.events(project_id)?;
        let state_bytes = tom_assist_protocol::canonical_json(&state)?;
        let mut events_bytes = Vec::new();
        for event in &events {
            events_bytes.extend(serde_json::to_vec(event)?);
            events_bytes.push(b'\n');
        }
        fs::write(directory.join("state.json"), &state_bytes)?;
        fs::write(directory.join("events.jsonl"), &events_bytes)?;
        fs::write(
            directory.join("transcript-policy.json"),
            b"{\"raw_content\":false}\n",
        )?;
        let mut files = BTreeMap::new();
        for name in ["events.jsonl", "state.json", "transcript-policy.json"] {
            files.insert(
                name.to_owned(),
                hash_bytes(&fs::read(directory.join(name))?),
            );
        }
        let manifest = ExportManifest {
            format: "tom-assist-export/1".into(),
            project_id: project_id.into(),
            state_schema_version: STATE_SCHEMA_VERSION.into(),
            event_schema_version: EVENT_SCHEMA_VERSION.into(),
            files,
        };
        fs::write(
            directory.join("manifest.json"),
            tom_assist_protocol::canonical_json(&manifest)?,
        )?;
        Ok(directory.to_path_buf())
    }

    pub fn import_project(&mut self, directory: impl AsRef<Path>) -> Result<Project> {
        let directory = directory.as_ref();
        Self::verify_export(directory)?;
        let expected_state: CanonicalState =
            serde_json::from_slice(&fs::read(directory.join("state.json"))?)?;
        let events_text = String::from_utf8(fs::read(directory.join("events.jsonl"))?)
            .map_err(|error| StoreError::Integrity(error.to_string()))?;
        let events: Vec<EventRecord> = events_text
            .lines()
            .filter(|line| !line.trim().is_empty())
            .map(serde_json::from_str)
            .collect::<std::result::Result<_, _>>()?;
        for event in events {
            match event.payload {
                EventPayload::ProjectCreated {
                    name,
                    retention_profile,
                    policy_profile,
                } => {
                    self.create_project(
                        &event.project_id,
                        &name,
                        &retention_profile,
                        &policy_profile,
                        &event.actor_id,
                        &event.idempotency_key,
                        &event.created_at,
                    )?;
                }
                EventPayload::Mutation { upserts, edges } => {
                    self.commit_mutation(
                        event.project_id,
                        upserts,
                        edges,
                        event.base_state_version,
                        &event.actor_type,
                        &event.actor_id,
                        &event.idempotency_key,
                        &event.created_at,
                        &event.event_type,
                    )?;
                }
            }
        }
        let actual = self.current_state(&expected_state.project_id)?;
        if actual != expected_state {
            return Err(StoreError::Integrity(
                "imported state differs from export".into(),
            ));
        }
        self.project(&expected_state.project_id)?
            .ok_or_else(|| StoreError::ProjectNotFound(expected_state.project_id))
    }

    pub fn verify_export(directory: impl AsRef<Path>) -> Result<()> {
        let directory = directory.as_ref();
        let manifest: ExportManifest =
            serde_json::from_slice(&fs::read(directory.join("manifest.json"))?)?;
        if manifest.format != "tom-assist-export/1" {
            return Err(StoreError::Integrity("unsupported export format".into()));
        }
        for (name, expected) in manifest.files {
            let actual = hash_bytes(&fs::read(directory.join(&name))?);
            if actual != expected {
                return Err(StoreError::Integrity(format!("checksum mismatch: {name}")));
            }
        }
        Ok(())
    }

    pub fn events(&self, project_id: &str) -> Result<Vec<EventRecord>> {
        let mut statement = self.connection.prepare("SELECT id,project_id,event_type,actor_type,actor_id,payload_json,idempotency_key,base_state_version,prior_digest,resulting_digest,created_at FROM state_events WHERE project_id=?1 ORDER BY rowid")?;
        let rows = statement.query_map([project_id], row_to_event)?;
        rows.map(|row| row.map_err(Into::into)).collect()
    }

    pub fn record_context_run(&self, record: &ContextRunRecord) -> Result<()> {
        let transaction = self.connection.unchecked_transaction()?;
        transaction.execute(
            "INSERT OR IGNORE INTO context_manifests(context_id,activated_branch_ids_json,admitted_anchor_ids_json,candidate_trace_json) VALUES(?1,?2,?3,?4)",
            params![record.id, serde_json::to_string(&record.activated_branch_ids)?, serde_json::to_string(&record.admitted_anchor_ids)?, record.candidate_trace_json],
        )?;
        transaction.execute(
            "INSERT OR IGNORE INTO context_runs(id,project_id,workstream_id,provider_session_id,draft_hash,state_version,tom_checkpoint_digest,activation_id,policy_version,renderer_version,selected_json,excluded_json,packet_text,packet_digest,estimated_tokens,latency_ms,created_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17)",
            params![record.id, record.project_id, record.workstream_id, record.provider_session_id, record.draft_hash, record.state_version, record.tom_checkpoint_digest, record.activation_id, record.policy_version, record.renderer_version, record.selected_json, record.excluded_json, record.packet_text, record.packet_digest, record.estimated_tokens, record.latency_ms, record.created_at],
        )?;
        transaction.commit()?;
        Ok(())
    }

    pub fn context_run_by_digest(
        &self,
        project_id: &str,
        digest: &str,
    ) -> Result<Option<ContextRunRecord>> {
        let record = self.connection.query_row(
            "SELECT id,project_id,COALESCE(workstream_id,''),COALESCE(provider_session_id,''),draft_hash,state_version,tom_checkpoint_digest,activation_id,policy_version,renderer_version,selected_json,excluded_json,packet_text,packet_digest,estimated_tokens,latency_ms,created_at FROM context_runs WHERE project_id=?1 AND packet_digest=?2 ORDER BY rowid DESC LIMIT 1",
            params![project_id, digest],
            |row| Ok(ContextRunRecord { activated_branch_ids: vec![], admitted_anchor_ids: vec![], candidate_trace_json: "[]".into(), id: row.get(0)?, project_id: row.get(1)?, workstream_id: row.get(2)?, provider_session_id: row.get(3)?, draft_hash: row.get(4)?, state_version: row.get(5)?, tom_checkpoint_digest: row.get(6)?, activation_id: row.get(7)?, policy_version: row.get(8)?, renderer_version: row.get(9)?, selected_json: row.get(10)?, excluded_json: row.get(11)?, packet_text: row.get(12)?, packet_digest: row.get(13)?, estimated_tokens: row.get(14)?, latency_ms: row.get(15)?, created_at: row.get(16)? }),
        ).optional()?;
        if let Some(mut record) = record {
            if let Some((branches, anchors, trace)) = self.connection.query_row(
                "SELECT activated_branch_ids_json,admitted_anchor_ids_json,candidate_trace_json FROM context_manifests WHERE context_id=?1",
                [&record.id], |row| Ok((row.get::<_,String>(0)?,row.get::<_,String>(1)?,row.get::<_,String>(2)?)),
            ).optional()? {
                record.activated_branch_ids = serde_json::from_str(&branches)?;
                record.admitted_anchor_ids = serde_json::from_str(&anchors)?;
                record.candidate_trace_json = trace;
            }
            Ok(Some(record))
        } else {
            Ok(None)
        }
    }

    pub fn record_turn(&self, record: &TurnRecord) -> Result<()> {
        self.connection.execute(
            "INSERT OR IGNORE INTO turns(id,session_id,project_id,workstream_id,role,ordinal,normalized_text,content_hash,packet_digest,completeness,captured_at,provider_timestamp) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12)",
            params![record.id, record.session_id, record.project_id, record.workstream_id, record.role, record.ordinal, record.normalized_text, record.content_hash, record.packet_digest, record.completeness, record.captured_at, record.provider_timestamp],
        )?;
        Ok(())
    }

    pub fn mark_context_sent(
        &self,
        project_id: &str,
        packet_digest: &str,
        turn_id: &str,
    ) -> Result<()> {
        self.connection.execute(
            "INSERT OR IGNORE INTO sent_contexts VALUES(?1,?2,?3)",
            params![project_id, packet_digest, turn_id],
        )?;
        if self
            .sent_turn_for_packet(project_id, packet_digest)?
            .is_none_or(|sent| sent.id != turn_id)
        {
            return Err(StoreError::Integrity(
                "packet already bound to another sent turn".into(),
            ));
        }
        Ok(())
    }

    pub fn sent_turn_for_packet(
        &self,
        project_id: &str,
        packet_digest: &str,
    ) -> Result<Option<TurnRecord>> {
        let id: Option<String> = self
            .connection
            .query_row(
                "SELECT turn_id FROM sent_contexts WHERE project_id=?1 AND packet_digest=?2",
                params![project_id, packet_digest],
                |row| row.get(0),
            )
            .optional()?;
        match id {
            Some(id) => self.turn(&id),
            None => Ok(None),
        }
    }

    pub fn runtime_commit_for_sent(&self, turn_id: &str) -> Result<Option<serde_json::Value>> {
        let raw: Option<String> = self
            .connection
            .query_row(
                "SELECT result_json FROM runtime_commit_receipts WHERE sent_turn_id=?1",
                [turn_id],
                |row| row.get(0),
            )
            .optional()?;
        raw.map(|text| serde_json::from_str(&text).map_err(Into::into))
            .transpose()
    }

    pub fn record_runtime_commit(
        &self,
        sent_turn_id: &str,
        evaluation_id: &str,
        result: &serde_json::Value,
    ) -> Result<()> {
        self.connection.execute(
            "INSERT OR IGNORE INTO runtime_commit_receipts VALUES(?1,?2,?3)",
            params![sent_turn_id, evaluation_id, serde_json::to_string(result)?],
        )?;
        Ok(())
    }

    pub fn turn(&self, turn_id: &str) -> Result<Option<TurnRecord>> {
        self.connection.query_row(
            "SELECT id,COALESCE(session_id,''),project_id,COALESCE(workstream_id,''),role,ordinal,COALESCE(normalized_text,''),content_hash,COALESCE(packet_digest,''),completeness,captured_at,provider_timestamp FROM turns WHERE id=?1",
            [turn_id],
            |row| Ok(TurnRecord { id: row.get(0)?, session_id: row.get(1)?, project_id: row.get(2)?, workstream_id: row.get(3)?, role: row.get(4)?, ordinal: row.get(5)?, normalized_text: row.get(6)?, content_hash: row.get(7)?, packet_digest: row.get(8)?, completeness: row.get(9)?, captured_at: row.get(10)?, provider_timestamp: row.get(11)? }),
        ).optional().map_err(Into::into)
    }

    pub fn record_response_evaluation(&self, record: &ResponseEvaluationRecord) -> Result<()> {
        self.connection.execute(
            "INSERT OR IGNORE INTO response_evaluations(id,project_id,turn_id,packet_digest,state_version,result,intervention_ids_json,policy_version,latency_ms,created_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10)",
            params![record.id, record.project_id, record.turn_id, record.packet_digest, record.state_version, record.result, serde_json::to_string(&record.intervention_ids)?, record.policy_version, record.latency_ms, record.created_at],
        )?;
        Ok(())
    }

    pub fn response_evaluation(
        &self,
        evaluation_id: &str,
    ) -> Result<Option<ResponseEvaluationRecord>> {
        self.connection
            .query_row(
                "SELECT id,project_id,turn_id,packet_digest,state_version,result,intervention_ids_json,policy_version,latency_ms,created_at FROM response_evaluations WHERE id=?1",
                [evaluation_id],
                |row| {
                    let intervention_ids: String = row.get(6)?;
                    Ok(ResponseEvaluationRecord {
                        id: row.get(0)?,
                        project_id: row.get(1)?,
                        turn_id: row.get(2)?,
                        packet_digest: row.get(3)?,
                        state_version: row.get(4)?,
                        result: row.get(5)?,
                        intervention_ids: serde_json::from_str(&intervention_ids).map_err(
                            |error| {
                                rusqlite::Error::FromSqlConversionFailure(
                                    6,
                                    rusqlite::types::Type::Text,
                                    Box::new(error),
                                )
                            },
                        )?,
                        policy_version: row.get(7)?,
                        latency_ms: row.get(8)?,
                        created_at: row.get(9)?,
                    })
                },
            )
            .optional()
            .map_err(Into::into)
    }

    pub fn audit(
        &self,
        project_id: &str,
        category: &str,
        correlation_id: &str,
        details: &serde_json::Value,
        created_at: &str,
    ) -> Result<()> {
        self.connection.execute(
            "INSERT INTO audit_events(project_id,category,correlation_id,details_json,created_at) VALUES(?1,?2,?3,?4,?5)",
            params![project_id, category, correlation_id, serde_json::to_string(details)?, created_at],
        )?;
        Ok(())
    }

    pub fn audit_records(&self, project_id: &str) -> Result<Vec<AuditRecord>> {
        let mut statement = self.connection.prepare(
            "SELECT project_id,category,correlation_id,details_json,created_at FROM audit_events WHERE project_id=?1 ORDER BY id",
        )?;
        let rows = statement.query_map([project_id], |row| {
            let details: String = row.get(3)?;
            Ok(AuditRecord {
                project_id: row.get(0)?,
                category: row.get(1)?,
                correlation_id: row.get(2)?,
                details: serde_json::from_str(&details).map_err(|error| {
                    rusqlite::Error::FromSqlConversionFailure(
                        3,
                        rusqlite::types::Type::Text,
                        Box::new(error),
                    )
                })?,
                created_at: row.get(4)?,
            })
        })?;
        rows.map(|row| row.map_err(Into::into)).collect()
    }

    pub fn record_intervention(&self, intervention: &Intervention, created_at: &str) -> Result<()> {
        let inserted = self.connection.execute(
            "INSERT OR IGNORE INTO interventions(id,project_id,turn_id,code,severity,confidence,summary,conflicting_state_ids_json,status,policy_version,created_at,resolved_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,NULL)",
            params![intervention.id, intervention.project_id, intervention.turn_id, serde_json::to_value(intervention.code)?.as_str(), serde_json::to_value(intervention.severity)?.as_str(), intervention.confidence, intervention.summary, serde_json::to_string(&intervention.conflicting_state_ids)?, serde_json::to_value(intervention.status)?.as_str(), intervention.policy_version, created_at],
        )?;
        if inserted == 1 && intervention.policy_version == "guardrail-resonance/1" {
            self.audit(
                &intervention.project_id,
                "STRUCTURAL_GUARDRAIL_REVIEW",
                &intervention.id,
                &serde_json::to_value(intervention)?,
                created_at,
            )?;
        }
        Ok(())
    }

    pub fn resolve_intervention(
        &self,
        intervention_id: &str,
        status: InterventionStatus,
        resolved_at: &str,
    ) -> Result<()> {
        let changed = self.connection.execute(
            "UPDATE interventions SET status=?2,resolved_at=?3 WHERE id=?1",
            params![
                intervention_id,
                serde_json::to_value(status)?.as_str(),
                resolved_at
            ],
        )?;
        if changed != 1 {
            return Err(StoreError::Integrity(format!(
                "intervention not found: {intervention_id}"
            )));
        }
        Ok(())
    }

    pub fn intervention_status(&self, intervention_id: &str) -> Result<Option<InterventionStatus>> {
        let value: Option<String> = self
            .connection
            .query_row(
                "SELECT status FROM interventions WHERE id=?1",
                [intervention_id],
                |row| row.get(0),
            )
            .optional()?;
        value
            .map(|status| {
                serde_json::from_value(serde_json::Value::String(status)).map_err(Into::into)
            })
            .transpose()
    }

    pub fn interventions(&self, project_id: &str) -> Result<Vec<InterventionRecord>> {
        let mut statement = self.connection.prepare(
            "SELECT id,project_id,turn_id,code,severity,confidence,summary,conflicting_state_ids_json,status,policy_version,created_at,resolved_at FROM interventions WHERE project_id=?1 ORDER BY created_at DESC,id",
        )?;
        let rows = statement.query_map([project_id], |row| {
            let state_ids: String = row.get(7)?;
            Ok(InterventionRecord {
                id: row.get(0)?,
                project_id: row.get(1)?,
                turn_id: row.get(2)?,
                code: row.get(3)?,
                severity: row.get(4)?,
                confidence: row.get(5)?,
                summary: row.get(6)?,
                conflicting_state_ids: serde_json::from_str(&state_ids).map_err(|error| {
                    rusqlite::Error::FromSqlConversionFailure(
                        7,
                        rusqlite::types::Type::Text,
                        Box::new(error),
                    )
                })?,
                status: row.get(8)?,
                policy_version: row.get(9)?,
                created_at: row.get(10)?,
                resolved_at: row.get(11)?,
            })
        })?;
        rows.map(|row| row.map_err(Into::into)).collect()
    }

    fn event_by_idempotency(&self, project_id: &str, key: &str) -> Result<Option<EventRecord>> {
        self.connection.query_row(
            "SELECT id,project_id,event_type,actor_type,actor_id,payload_json,idempotency_key,base_state_version,prior_digest,resulting_digest,created_at FROM state_events WHERE project_id=?1 AND idempotency_key=?2",
            params![project_id, key], row_to_event,
        ).optional().map_err(Into::into)
    }
}

fn row_to_event(row: &rusqlite::Row<'_>) -> rusqlite::Result<EventRecord> {
    let payload_json: String = row.get(5)?;
    let payload = serde_json::from_str(&payload_json).map_err(|error| {
        rusqlite::Error::FromSqlConversionFailure(5, rusqlite::types::Type::Text, Box::new(error))
    })?;
    Ok(EventRecord {
        id: row.get(0)?,
        project_id: row.get(1)?,
        event_type: row.get(2)?,
        actor_type: row.get(3)?,
        actor_id: row.get(4)?,
        payload,
        idempotency_key: row.get(6)?,
        base_state_version: row.get(7)?,
        prior_digest: row.get(8)?,
        resulting_digest: row.get(9)?,
        created_at: row.get(10)?,
    })
}

fn upsert_state_object(transaction: &Transaction<'_>, object: &StateObject) -> Result<()> {
    transaction.execute(
        "INSERT INTO state_objects(id,project_id,workstream_id,type,title,canonical_text,status,authority,confidence,binding_strength,source_json,content_hash,created_at,updated_at,effective_at,supersedes_id,state_version,object_json) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18) ON CONFLICT(id) DO UPDATE SET status=excluded.status,updated_at=excluded.updated_at,supersedes_id=excluded.supersedes_id,state_version=excluded.state_version,object_json=excluded.object_json",
        params![object.id, object.project_id, object.workstream_id, serde_json::to_value(object.object_type)?.as_str(), object.title, object.canonical_text, serde_json::to_value(object.status)?.as_str(), serde_json::to_value(object.authority)?.as_str(), object.confidence, object.binding_strength.and_then(|value| serde_json::to_value(value).ok()).and_then(|value| value.as_str().map(str::to_owned)), serde_json::json!({"source_turn_ids":object.source_turn_ids,"evidence_ids":object.evidence_ids,"branch_refs":object.branch_refs}).to_string(), object.content_hash, object.created_at, object.updated_at, object.effective_at, object.supersedes_id, object.state_version, serde_json::to_string(object)?],
    )?;
    Ok(())
}

fn insert_edge(transaction: &Transaction<'_>, edge: &StateEdge) -> Result<()> {
    transaction.execute(
        "INSERT OR REPLACE INTO state_edges(id,project_id,from_state_id,edge_type,to_state_id,created_event_id,edge_json) VALUES(?1,?2,?3,?4,?5,?6,?7)",
        params![edge.id, edge.project_id, edge.from_state_id, serde_json::to_value(edge.edge_type)?.as_str(), edge.to_state_id, edge.created_event_id, serde_json::to_string(edge)?],
    )?;
    Ok(())
}

trait ConnectionLike {
    fn prepare_state(&self, sql: &str) -> rusqlite::Result<rusqlite::Statement<'_>>;
}
impl ConnectionLike for Connection {
    fn prepare_state(&self, sql: &str) -> rusqlite::Result<rusqlite::Statement<'_>> {
        self.prepare(sql)
    }
}
impl ConnectionLike for Transaction<'_> {
    fn prepare_state(&self, sql: &str) -> rusqlite::Result<rusqlite::Statement<'_>> {
        self.prepare(sql)
    }
}

fn load_canonical_state(
    connection: &impl ConnectionLike,
    project_id: &str,
    state_version: u64,
) -> Result<CanonicalState> {
    let mut object_statement = connection
        .prepare_state("SELECT object_json FROM state_objects WHERE project_id=?1 ORDER BY id")?;
    let objects = object_statement
        .query_map([project_id], |row| row.get::<_, String>(0))?
        .map(|row| Ok(serde_json::from_str(&row?)?))
        .collect::<Result<Vec<StateObject>>>()?;
    let mut edge_statement = connection
        .prepare_state("SELECT edge_json FROM state_edges WHERE project_id=?1 ORDER BY id")?;
    let edges = edge_statement
        .query_map([project_id], |row| row.get::<_, String>(0))?
        .map(|row| Ok(serde_json::from_str(&row?)?))
        .collect::<Result<Vec<StateEdge>>>()?;
    Ok(CanonicalState {
        project_id: project_id.to_owned(),
        state_version,
        objects,
        edges,
    })
}

fn event_id(project_id: &str, key: &str, kind: &str) -> String {
    let digest = hash_bytes(format!("{project_id}\0{key}\0{kind}").as_bytes());
    format!("event:{}", digest.trim_start_matches("sha256:"))
}

fn hash_bytes(bytes: &[u8]) -> String {
    format!("sha256:{}", hex::encode(Sha256::digest(bytes)))
}
