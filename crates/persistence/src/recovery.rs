//! Complete project archives. SQLite's writer lock spans the runtime snapshot;
//! runtime publication uses a recoverable intent, never an overwrite.
use super::*;
use rusqlite::types::Value as SqlValue;
use serde_json::{Value, json};
use std::path::Component;

const TABLES: &[&str] = &[
    "projects",
    "workstreams",
    "provider_sessions",
    "turns",
    "anchors",
    "state_objects",
    "state_edges",
    "evidence",
    "state_events",
    "state_mutation_candidates",
    "context_runs",
    "context_manifests",
    "response_evaluations",
    "interventions",
    "tom_checkpoints",
    "snapshots",
    "audit_events",
    "sent_contexts",
    "runtime_commit_receipts",
    "recovery_imports",
    "chat_conversations",
    "provider_exchanges",
    "provider_self_reports",
];
const FORMAT: &str = "tom-assist-recovery/2";

#[cfg(test)]
mod compatibility_tests {
    use super::*;

    #[test]
    fn wp20_inventory_without_chat_is_supported_but_other_omissions_are_not() {
        let mut source = Store::open_memory().unwrap();
        source
            .create_project(
                "old-project",
                "WP20",
                "full-local",
                "context-policy/1.1",
                "owner",
                "create",
                "2026-08-31T00:00:00Z",
            )
            .unwrap();
        let mut ledger = source.recovery_ledger("old-project").unwrap();
        ledger.tables.remove("chat_conversations");
        ledger.tables.remove("provider_exchanges");
        ledger.tables.remove("provider_self_reports");
        let restored = Store::open_memory().unwrap();
        restored.insert_recovery_ledger(&ledger, false).unwrap();
        assert_eq!(
            restored.project("old-project").unwrap(),
            source.project("old-project").unwrap()
        );
        assert!(restored.conversations("old-project").unwrap().is_empty());
        ledger.tables.remove("turns");
        assert!(
            Store::open_memory()
                .unwrap()
                .insert_recovery_ledger(&ledger, false)
                .is_err()
        );
        let mut current = source.recovery_ledger("old-project").unwrap();
        current.tables.remove("provider_exchanges");
        assert!(
            Store::open_memory()
                .unwrap()
                .insert_recovery_ledger(&current, false)
                .is_err()
        );
    }
}

#[derive(Serialize, Deserialize)]
struct Rows {
    columns: Vec<String>,
    rows: Vec<Vec<Value>>,
}
#[derive(Serialize, Deserialize)]
struct Ledger {
    project_id: String,
    tables: BTreeMap<String, Rows>,
}
#[derive(Serialize, Deserialize)]
struct Manifest {
    format: String,
    project_id: String,
    state_digest: String,
    raw_content: bool,
    runtime: Value,
    files: BTreeMap<String, String>,
}

fn integrity(message: impl Into<String>) -> StoreError {
    StoreError::Integrity(message.into())
}
fn columns(db: &Connection, table: &str) -> Result<Vec<String>> {
    Ok(db
        .prepare(&format!("PRAGMA table_info({table})"))?
        .query_map([], |row| row.get(1))?
        .collect::<std::result::Result<_, _>>()?)
}
fn inventory(root: &Path) -> Result<BTreeMap<String, String>> {
    fn walk(root: &Path, at: &Path, files: &mut BTreeMap<String, String>) -> Result<()> {
        for entry in fs::read_dir(at)? {
            let entry = entry?;
            let path = entry.path();
            let kind = entry.file_type()?;
            if kind.is_symlink() {
                return Err(integrity("archive symlinks are forbidden"));
            }
            if kind.is_dir() {
                walk(root, &path, files)?;
            } else if kind.is_file() {
                let name = path
                    .strip_prefix(root)
                    .map_err(|_| integrity("archive path escaped"))?
                    .to_string_lossy()
                    .into_owned();
                if name != "manifest.json" {
                    files.insert(name, hash_bytes(&fs::read(path)?));
                }
            } else {
                return Err(integrity("archive contains a special file"));
            }
        }
        Ok(())
    }
    if fs::symlink_metadata(root)?.file_type().is_symlink() {
        return Err(integrity("archive root is a symlink"));
    }
    let mut files = BTreeMap::new();
    walk(root, root, &mut files)?;
    Ok(files)
}

fn sync_directories(directory: &Path) -> Result<()> {
    for entry in fs::read_dir(directory)? {
        let entry = entry?;
        if entry.file_type()?.is_dir() {
            sync_directories(&entry.path())?;
        }
    }
    fs::File::open(directory)?.sync_all()?;
    Ok(())
}

impl Store {
    fn recovery_ledger(&self, project_id: &str) -> Result<Ledger> {
        let actual = self
            .connection
            .prepare(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
            )?
            .query_map([], |row| row.get::<_, String>(0))?
            .collect::<std::result::Result<std::collections::BTreeSet<_>, _>>()?;
        let expected: std::collections::BTreeSet<String> = TABLES
            .iter()
            .copied()
            .chain(["schema_migrations"])
            .map(str::to_owned)
            .collect();
        if actual != expected {
            return Err(integrity(
                "unrecognized ledger schema; refusing incomplete backup",
            ));
        }
        let mut tables = BTreeMap::new();
        for table in TABLES {
            let predicate = match *table {
                "projects" => "id=?1",
                "context_manifests" => {
                    "context_id IN (SELECT id FROM context_runs WHERE project_id=?1)"
                }
                "runtime_commit_receipts" => {
                    "sent_turn_id IN (SELECT id FROM turns WHERE project_id=?1)"
                }
                _ => "project_id=?1",
            };
            let cols = columns(&self.connection, table)?;
            let mut statement = self.connection.prepare(&format!(
                "SELECT * FROM {table} WHERE {predicate} ORDER BY rowid"
            ))?;
            let rows = statement
                .query_map([project_id], |row| {
                    (0..cols.len())
                        .map(|index| match row.get::<_, SqlValue>(index)? {
                            SqlValue::Null => Ok(Value::Null),
                            SqlValue::Integer(v) => Ok(json!(v)),
                            SqlValue::Real(v) => Ok(json!(v)),
                            SqlValue::Text(v) => Ok(json!(v)),
                            SqlValue::Blob(_) => Err(rusqlite::Error::InvalidQuery),
                        })
                        .collect::<std::result::Result<Vec<_>, _>>()
                })?
                .collect::<std::result::Result<_, _>>()?;
            tables.insert(
                (*table).into(),
                Rows {
                    columns: cols,
                    rows,
                },
            );
        }
        Ok(Ledger {
            project_id: project_id.into(),
            tables,
        })
    }

    fn insert_recovery_ledger(&self, ledger: &Ledger, remap_audit_ids: bool) -> Result<()> {
        let actual: std::collections::BTreeSet<_> =
            ledger.tables.keys().map(String::as_str).collect();
        let expected: std::collections::BTreeSet<_> = TABLES.iter().copied().collect();
        let legacy: std::collections::BTreeSet<_> = TABLES
            .iter()
            .copied()
            .filter(|t| {
                !matches!(
                    *t,
                    "chat_conversations" | "provider_exchanges" | "provider_self_reports"
                )
            })
            .collect();
        let wp21: std::collections::BTreeSet<_> = TABLES
            .iter()
            .copied()
            .filter(|t| *t != "provider_self_reports")
            .collect();
        if actual != expected && actual != legacy && actual != wp21 {
            return Err(integrity("archive table inventory mismatch"));
        }
        for table in TABLES {
            // WP-20 archives predate chat; their missing chat tables mean empty,
            // not missing runtime recovery content. No other omissions accepted.
            let empty = Rows {
                columns: columns(&self.connection, table)?,
                rows: vec![],
            };
            let data = ledger.tables.get(*table).unwrap_or(&empty);
            if data.columns != columns(&self.connection, table)? {
                return Err(integrity(format!("archive schema mismatch: {table}")));
            }
            let skip = usize::from(*table == "audit_events" && remap_audit_ids);
            let sql = format!(
                "INSERT INTO {table} ({}) VALUES ({})",
                data.columns[skip..].join(","),
                vec!["?"; data.columns.len() - skip].join(",")
            );
            for row in &data.rows {
                if row.len() != data.columns.len() {
                    return Err(integrity("archive row width mismatch"));
                }
                if let Some(index) = data
                    .columns
                    .iter()
                    .position(|c| c == "project_id" || (*table == "projects" && c == "id"))
                {
                    if row[index] != ledger.project_id {
                        return Err(integrity("cross-project archive row"));
                    }
                }
                let values = row[skip..]
                    .iter()
                    .map(|value| match value {
                        Value::Null => Ok(SqlValue::Null),
                        Value::String(s) => Ok(SqlValue::Text(s.clone())),
                        Value::Number(n) if n.is_i64() => {
                            Ok(SqlValue::Integer(n.as_i64().unwrap()))
                        }
                        Value::Number(n) => n
                            .as_f64()
                            .filter(|v| v.is_finite())
                            .map(SqlValue::Real)
                            .ok_or_else(|| integrity("invalid number")),
                        _ => Err(integrity("non-scalar database value")),
                    })
                    .collect::<Result<Vec<_>>>()?;
                self.connection
                    .execute(&sql, rusqlite::params_from_iter(values))?;
            }
        }
        if self
            .connection
            .prepare("PRAGMA foreign_key_check")?
            .exists([])?
        {
            return Err(integrity("archive foreign key mismatch"));
        }
        let orphan_manifests: u64 = self.connection.query_row("SELECT count(*) FROM context_manifests WHERE context_id NOT IN (SELECT id FROM context_runs)", [], |r| r.get(0))?;
        let orphan_receipts: u64 = self.connection.query_row("SELECT count(*) FROM runtime_commit_receipts WHERE evaluation_id NOT IN (SELECT id FROM response_evaluations)", [], |r| r.get(0))?;
        if orphan_manifests + orphan_receipts > 0 {
            return Err(integrity("orphan archive manifest/receipt"));
        }
        Ok(())
    }

    pub fn export_recovery_archive<F>(
        &self,
        project_id: &str,
        directory: impl AsRef<Path>,
        export_runtime: F,
    ) -> Result<PathBuf>
    where
        F: FnOnce(&Path) -> Result<Value>,
    {
        let directory = directory.as_ref();
        match fs::symlink_metadata(directory) {
            Ok(_) => return Err(integrity("archive destination must not exist")),
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
            Err(error) => return Err(error.into()),
        }
        let parent = directory
            .parent()
            .ok_or_else(|| integrity("archive destination has no parent"))?;
        fs::create_dir_all(parent)?;
        let stage = tempfile::Builder::new()
            .prefix(".tom-archive-")
            .tempdir_in(parent)?;
        self.connection.execute_batch("BEGIN IMMEDIATE")?;
        let result = (|| {
            let project = self
                .project(project_id)?
                .ok_or_else(|| StoreError::ProjectNotFound(project_id.into()))?;
            let state = self.current_state(project_id)?;
            if self.replay(project_id)? != state
                || canonical_sha256(&state)? != project.state_digest
            {
                return Err(integrity("source ledger replay mismatch"));
            }
            let ledger = self.recovery_ledger(project_id)?;
            fs::write(
                stage.path().join("ledger.json"),
                tom_assist_protocol::canonical_json(&ledger)?,
            )?;
            fs::write(
                stage.path().join("state.json"),
                tom_assist_protocol::canonical_json(&state)?,
            )?;
            let mut events = Vec::new();
            for event in self.events(project_id)? {
                events.extend(serde_json::to_vec(&event)?);
                events.push(b'\n');
            }
            fs::write(stage.path().join("events.jsonl"), events)?;
            fs::write(
                stage.path().join("transcript-policy.json"),
                tom_assist_protocol::canonical_json(
                    &json!({"raw_content":true,"purpose":"complete local runtime recovery","retention_profile":project.retention_profile,"warning":"Contains all retained original conversation content; not a redacted diagnostic export."}),
                )?,
            )?;
            let runtime = export_runtime(&stage.path().join("runtime"))?;
            let manifest = Manifest {
                format: FORMAT.into(),
                project_id: project_id.into(),
                state_digest: project.state_digest,
                raw_content: true,
                runtime,
                files: inventory(stage.path())?,
            };
            fs::write(
                stage.path().join("manifest.json"),
                tom_assist_protocol::canonical_json(&manifest)?,
            )?;
            Self::verify_recovery_archive(stage.path())?;
            // No partial archive is ever advertised at the requested destination.
            for name in manifest
                .files
                .keys()
                .chain(std::iter::once(&"manifest.json".to_owned()))
            {
                fs::File::open(stage.path().join(name))?.sync_all()?;
            }
            sync_directories(stage.path())?;
            fs::rename(stage.path(), directory)?;
            fs::File::open(parent)?.sync_all()?;
            Ok(directory.to_path_buf())
        })();
        let release = self.connection.execute_batch("ROLLBACK");
        release?;
        result
    }

    pub fn verify_recovery_archive(directory: impl AsRef<Path>) -> Result<Value> {
        let directory = directory.as_ref();
        if fs::symlink_metadata(directory)?.file_type().is_symlink() {
            return Err(integrity("archive root is a symlink"));
        }
        let manifest: Manifest =
            serde_json::from_slice(&fs::read(directory.join("manifest.json"))?)?;
        if manifest.format != FORMAT || !manifest.raw_content {
            return Err(integrity("not a complete recovery archive"));
        }
        for name in manifest.files.keys() {
            if Path::new(name)
                .components()
                .any(|c| !matches!(c, Component::Normal(_)))
                || name.contains('\\')
            {
                return Err(integrity("unsafe archive path"));
            }
        }
        for required in [
            "ledger.json",
            "state.json",
            "events.jsonl",
            "transcript-policy.json",
            "runtime/runtime-manifest.json",
            "runtime/library.sqlite3",
            "runtime/creation_metadata.json",
        ] {
            if !manifest.files.contains_key(required) {
                return Err(integrity(format!(
                    "missing required archive file: {required}"
                )));
            }
        }
        if inventory(directory)? != manifest.files {
            return Err(integrity("archive checksum/inventory mismatch"));
        }
        let runtime_manifest: Value =
            serde_json::from_slice(&fs::read(directory.join("runtime/runtime-manifest.json"))?)?;
        if runtime_manifest != manifest.runtime
            || runtime_manifest["project_id"] != manifest.project_id
        {
            return Err(integrity("runtime manifest identity mismatch"));
        }
        let ledger: Ledger = serde_json::from_slice(&fs::read(directory.join("ledger.json"))?)?;
        if ledger.project_id != manifest.project_id {
            return Err(integrity("archive project mismatch"));
        }
        let scratch = Store::open_memory()?;
        scratch.insert_recovery_ledger(&ledger, false)?;
        let state = scratch.current_state(&ledger.project_id)?;
        let expected: CanonicalState =
            serde_json::from_slice(&fs::read(directory.join("state.json"))?)?;
        if scratch.list_projects()?.len() != 1
            || state != expected
            || scratch.replay(&ledger.project_id)? != state
            || canonical_sha256(&state)? != manifest.state_digest
            || scratch.project(&ledger.project_id)?.unwrap().state_digest != manifest.state_digest
        {
            return Err(integrity("archive ledger identity/replay mismatch"));
        }
        let event_text = fs::read_to_string(directory.join("events.jsonl"))?;
        let events: Vec<EventRecord> = event_text
            .lines()
            .map(serde_json::from_str)
            .collect::<std::result::Result<_, _>>()?;
        if events != scratch.events(&ledger.project_id)? {
            return Err(integrity("archive event mismatch"));
        }
        Ok(
            json!({"project_id":manifest.project_id,"state_digest":manifest.state_digest,"runtime":manifest.runtime,"archive_digest":hash_bytes(&fs::read(directory.join("manifest.json"))?)}),
        )
    }

    pub fn import_recovery_archive<F>(
        &mut self,
        directory: impl AsRef<Path>,
        mut runtime: F,
    ) -> Result<Project>
    where
        F: FnMut(&str, &Path, &Value) -> Result<Value>,
    {
        let source = directory.as_ref();
        let original = Self::verify_recovery_archive(source)?;
        // Freeze the verified input before importing. A user-selected directory
        // can otherwise change between validation, ledger reads and runtime copy.
        let frozen = tempfile::Builder::new().prefix(".tom-import-").tempdir_in(
            self.path
                .parent()
                .ok_or_else(|| integrity("ledger has no parent"))?,
        )?;
        for name in inventory(source)?
            .keys()
            .chain(std::iter::once(&"manifest.json".to_owned()))
        {
            let destination = frozen.path().join(name);
            fs::create_dir_all(destination.parent().unwrap())?;
            fs::copy(source.join(name), destination)?;
        }
        let directory = frozen.path();
        let verified = Self::verify_recovery_archive(directory)?;
        if verified != original {
            return Err(integrity("archive changed during import snapshot"));
        }
        let id = verified["project_id"]
            .as_str()
            .ok_or_else(|| integrity("project id missing"))?;
        if self.project(id)?.is_some() {
            return Err(integrity("project already exists; import never overwrites"));
        }
        let ledger: Ledger = serde_json::from_slice(&fs::read(directory.join("ledger.json"))?)?;
        let context = json!({"project_id":id,"state_digest":verified["state_digest"],"archive_digest":verified["archive_digest"],"ledger_path":self.path.canonicalize()?});
        let token = runtime("stage", &directory.join("runtime"), &context)?;
        if let Err(error) = self.connection.execute_batch("BEGIN IMMEDIATE") {
            let _ = runtime("abort", &directory.join("runtime"), &token);
            return Err(error.into());
        }
        let result = (|| {
            if self.project(id)?.is_some() {
                return Err(integrity("project appeared during import"));
            }
            self.insert_recovery_ledger(&ledger, true)?;
            self.connection.execute(
                "INSERT INTO recovery_imports VALUES(?1,?2,?3)",
                params![
                    token["token"]
                        .as_str()
                        .ok_or_else(|| integrity("runtime token missing"))?,
                    id,
                    verified["archive_digest"].as_str()
                ],
            )?;
            runtime("publish", &directory.join("runtime"), &token)?;
            self.connection.execute_batch("COMMIT")?;
            Ok(())
        })();
        if let Err(error) = result {
            let _ = self.connection.execute_batch("ROLLBACK");
            let _ = runtime("abort", &directory.join("runtime"), &token);
            return Err(error);
        }
        // Finalization is recoverable from the intent and committed ledger. Do
        // not misreport a durable import as rolled back after a lost reply.
        let _ = runtime("finalize", &directory.join("runtime"), &token);
        self.project(id)?
            .ok_or_else(|| StoreError::ProjectNotFound(id.into()))
    }
}
