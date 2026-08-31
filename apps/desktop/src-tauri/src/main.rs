use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::io::{BufRead, BufReader, Write};
use std::os::unix::net::UnixStream;
use std::sync::Mutex;
use std::time::Duration;
use tauri::Manager;
use tom_assist_persistence::{
    CanonicalState, EventRecord, InterventionRecord, Project, Store, StoreMode, TurnRecord,
};
use tom_assist_protocol::{
    Authority, BindingStrength, StateObject, StateStatus, StateType, canonical_sha256,
};

struct DesktopState {
    store: Mutex<Store>,
    store_mode: StoreMode,
    migration_backup: Option<String>,
    migration_error: Option<String>,
}

#[derive(Debug, Deserialize)]
struct CreateProjectRequest {
    id: String,
    name: String,
    retention_profile: String,
    created_at: String,
}

#[derive(Debug, Deserialize)]
struct CaptureRequest {
    object: StateObject,
    base_state_version: u64,
    actor_id: String,
    idempotency_key: String,
    created_at: String,
}

#[derive(Debug, Deserialize)]
struct SupersedeRequest {
    project_id: String,
    old_id: String,
    replacement: StateObject,
    reason: String,
    base_state_version: u64,
    actor_id: String,
    idempotency_key: String,
    created_at: String,
}

#[derive(Debug, Serialize)]
struct Diagnostics {
    database_path: String,
    database_replay_ok: bool,
    storage_mode: String,
    migration_backup: Option<String>,
    migration_error: Option<String>,
    network_services: bool,
    memory: Value,
}

fn gateway(store: &Store) -> tom_assist_tom_adapter::GatewayClient {
    let socket = std::env::var_os("TOM_ASSIST_GATEWAY_SOCKET")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|| store.path().with_file_name("tom_gateway.sock"));
    tom_assist_tom_adapter::GatewayClient::new(socket)
}

#[tauri::command]
fn exchange_request(
    envelope: tom_assist_protocol::Envelope,
    state: tauri::State<'_, DesktopState>,
) -> Result<Value, String> {
    use tom_assist_protocol::Method;
    if !matches!(
        envelope.method,
        Method::TurnPrepare | Method::TurnSent | Method::ResponseEvaluate
    ) {
        return Err("local exchange diagnostics only support prepare, sent and evaluate".into());
    }
    let store = locked(&state);
    let project = envelope
        .project_id
        .as_deref()
        .ok_or("project is required")?;
    if envelope.payload["project_id"].as_str() != Some(project)
        || store.project(project).map_err(|e| e.to_string())?.is_none()
    {
        return Err("exchange project mismatch".into());
    }
    let socket = std::env::var_os("TOM_ASSISTD_SOCKET")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|| store.path().with_file_name("tom-assistd.sock"));
    drop(store);
    let mut stream = UnixStream::connect(socket).map_err(|e| e.to_string())?;
    stream
        .set_read_timeout(Some(Duration::from_secs(60)))
        .map_err(|e| e.to_string())?;
    stream
        .set_write_timeout(Some(Duration::from_secs(60)))
        .map_err(|e| e.to_string())?;
    serde_json::to_writer(&mut stream, &envelope).map_err(|e| e.to_string())?;
    stream.write_all(b"\n").map_err(|e| e.to_string())?;
    let mut line = String::new();
    BufReader::new(stream)
        .read_line(&mut line)
        .map_err(|e| e.to_string())?;
    let response: tom_assistd::WireResponse =
        serde_json::from_str(&line).map_err(|e| e.to_string())?;
    if !response.ok {
        return Err(serde_json::to_string(&response.error).unwrap_or_default());
    }
    response
        .payload
        .ok_or_else(|| "daemon response was empty".into())
}

fn locked<'a>(state: &'a tauri::State<'_, DesktopState>) -> std::sync::MutexGuard<'a, Store> {
    state.store.lock().expect("desktop store poisoned")
}

#[tauri::command]
fn list_projects(state: tauri::State<'_, DesktopState>) -> Result<Vec<Project>, String> {
    locked(&state)
        .list_projects()
        .map_err(|error| error.to_string())
}

#[tauri::command]
fn create_project(
    request: CreateProjectRequest,
    state: tauri::State<'_, DesktopState>,
) -> Result<Project, String> {
    locked(&state)
        .create_project(
            &request.id,
            &request.name,
            &request.retention_profile,
            "context-policy/1.1",
            "desktop-user",
            &format!("project-create:{}", request.id),
            &request.created_at,
        )
        .map_err(|error| error.to_string())
}

#[tauri::command]
fn archive_project(
    project_id: String,
    updated_at: String,
    state: tauri::State<'_, DesktopState>,
) -> Result<Project, String> {
    let store = locked(&state);
    let project = store
        .project(&project_id)
        .map_err(|error| error.to_string())?
        .ok_or_else(|| format!("project not found: {project_id}"))?;
    store
        .update_project_metadata(&project_id, &project.name, "archived", &updated_at)
        .map_err(|error| error.to_string())
}

#[tauri::command]
fn rename_project(
    project_id: String,
    name: String,
    updated_at: String,
    state: tauri::State<'_, DesktopState>,
) -> Result<Project, String> {
    let store = locked(&state);
    let project = store
        .project(&project_id)
        .map_err(|error| error.to_string())?
        .ok_or_else(|| format!("project not found: {project_id}"))?;
    let name = name.trim();
    if name.is_empty() {
        return Err("project name must not be empty".into());
    }
    store
        .update_project_metadata(&project_id, name, &project.status, &updated_at)
        .map_err(|error| error.to_string())
}

#[tauri::command]
fn project_state(
    project_id: String,
    state: tauri::State<'_, DesktopState>,
) -> Result<CanonicalState, String> {
    locked(&state)
        .current_state(&project_id)
        .map_err(|error| error.to_string())
}

#[tauri::command]
fn capture_state(
    request: CaptureRequest,
    state: tauri::State<'_, DesktopState>,
) -> Result<EventRecord, String> {
    locked(&state)
        .commit_object(
            request.object,
            request.base_state_version,
            "user",
            &request.actor_id,
            &request.idempotency_key,
            &request.created_at,
        )
        .map_err(|error| error.to_string())
}

#[tauri::command]
fn supersede_state(
    request: SupersedeRequest,
    state: tauri::State<'_, DesktopState>,
) -> Result<EventRecord, String> {
    locked(&state)
        .supersede(
            &request.project_id,
            &request.old_id,
            request.replacement,
            &request.reason,
            request.base_state_version,
            &request.actor_id,
            &request.idempotency_key,
            &request.created_at,
        )
        .map_err(|error| error.to_string())
}

#[tauri::command]
fn audit_events(
    project_id: String,
    state: tauri::State<'_, DesktopState>,
) -> Result<Vec<EventRecord>, String> {
    locked(&state)
        .events(&project_id)
        .map_err(|error| error.to_string())
}

#[tauri::command]
fn list_interventions(
    project_id: String,
    state: tauri::State<'_, DesktopState>,
) -> Result<Vec<InterventionRecord>, String> {
    locked(&state)
        .interventions(&project_id)
        .map_err(|error| error.to_string())
}

#[tauri::command]
fn resolve_intervention(
    project_id: String,
    intervention_id: String,
    status: tom_assist_protocol::InterventionStatus,
    resolved_at: String,
    state: tauri::State<'_, DesktopState>,
) -> Result<(), String> {
    let store = locked(&state);
    tom_assistd::experience::resolve_intervention_with_runtime(
        &store,
        Some(&gateway(&store)),
        &project_id,
        &intervention_id,
        status,
        &resolved_at,
    )
    .map_err(|error| error.to_string())
}

#[tauri::command]
fn memory_settings(
    project_id: String,
    settings: Value,
    state: tauri::State<'_, DesktopState>,
) -> Result<Value, String> {
    if state.store_mode != StoreMode::ReadWrite {
        return Err("settings unavailable in safe mode".into());
    }
    let store = locked(&state);
    store
        .project(&project_id)
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "project not found".to_owned())?;
    gateway(&store)
        .memory_settings(&project_id, settings)
        .map_err(|error| error.to_string())
}

#[tauri::command]
fn export_project(
    project_id: String,
    directory: String,
    state: tauri::State<'_, DesktopState>,
) -> Result<String, String> {
    let store = locked(&state);
    tom_assistd::recovery::export_project(
        &store,
        &gateway(&store),
        &project_id,
        std::path::Path::new(&directory),
    )
    .map(|path| path.display().to_string())
    .map_err(|error| error.to_string())
}

#[tauri::command]
fn import_project(
    directory: String,
    state: tauri::State<'_, DesktopState>,
) -> Result<Project, String> {
    let mut store = locked(&state);
    let client = gateway(&store);
    tom_assistd::recovery::import_project(&mut store, &client, std::path::Path::new(&directory))
        .map_err(|error| error.to_string())
}

#[tauri::command]
fn backup_project(
    project_id: String,
    directory: String,
    state: tauri::State<'_, DesktopState>,
) -> Result<String, String> {
    // A backup is the same verified complete archive, not a raw WAL-file copy.
    export_project(project_id, directory, state)
}

#[tauri::command]
fn verify_archive(
    directory: String,
    state: tauri::State<'_, DesktopState>,
) -> Result<Value, String> {
    let store = locked(&state);
    tom_assistd::recovery::verify_project(&gateway(&store), std::path::Path::new(&directory))
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn diagnostics(
    project_id: String,
    after_event_id: Option<u64>,
    state: tauri::State<'_, DesktopState>,
) -> Result<Diagnostics, String> {
    let store = locked(&state);
    let replay_ok = store
        .list_projects()
        .map_err(|error| error.to_string())?
        .iter()
        .all(|project| store.replay(&project.id).is_ok());
    Ok(Diagnostics {
        database_path: store.path().display().to_string(),
        database_replay_ok: replay_ok,
        storage_mode: match state.store_mode {
            StoreMode::ReadWrite => "sqlite-wal-plaintext-alpha",
            StoreMode::ReadOnlySafe => "sqlite-read-only-safe-mode",
        }
        .into(),
        migration_backup: state.migration_backup.clone(),
        migration_error: state.migration_error.clone(),
        network_services: false,
        memory: gateway(&store)
            .memory_diagnostics(&project_id, after_event_id.unwrap_or(0))
            .unwrap_or_else(|error| serde_json::json!({"unavailable":error.to_string()})),
    })
}

#[tauri::command]
fn seed_demo(state: tauri::State<'_, DesktopState>) -> Result<Project, String> {
    let mut store = locked(&state);
    seed_demo_store(&mut store).map_err(|error| error.to_string())
}

fn seed_demo_store(store: &mut Store) -> Result<Project, Box<dyn std::error::Error>> {
    let rows: Vec<Value> = include_str!("../../../../tests/fixtures/demo_project.jsonl")
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(serde_json::from_str)
        .collect::<Result<_, _>>()?;
    let project_row = rows
        .iter()
        .find(|row| row["kind"] == "project")
        .ok_or("demo project row missing")?;
    let project_id = project_row["id"]
        .as_str()
        .ok_or("demo project id missing")?;
    let mut project = store.create_project(
        project_id,
        project_row["name"].as_str().unwrap_or("Demo"),
        project_row["retention_profile"]
            .as_str()
            .unwrap_or("state-focused"),
        project_row["policy_profile"]
            .as_str()
            .unwrap_or("context-policy/1.1"),
        "demo-seeder",
        "demo-project-create",
        "2026-08-10T00:00:00Z",
    )?;
    if project.state_version == 0 {
        for (index, row) in rows.iter().filter(|row| row["kind"] == "state").enumerate() {
            let timestamp = format!("2026-08-10T00:{:02}:00Z", index + 1);
            let object = demo_object(project_id, row, &timestamp)?;
            store.commit_object(
                object,
                project.state_version,
                "user",
                "demo-seeder",
                &format!("demo-state-{}", row["id"].as_str().unwrap_or("unknown")),
                &timestamp,
            )?;
            project = store
                .project(project_id)?
                .ok_or("seeded project disappeared")?;
        }
    }
    for row in rows.iter().filter(|row| row["kind"] == "turn") {
        let text = row["text"].as_str().unwrap_or_default();
        store.record_turn(&TurnRecord {
            id: row["id"].as_str().unwrap_or_default().into(),
            session_id: "demo-session".into(),
            project_id: project_id.into(),
            workstream_id: "demo-main".into(),
            role: row["role"].as_str().unwrap_or("user").into(),
            ordinal: row["ordinal"].as_u64().unwrap_or(0),
            normalized_text: text.into(),
            content_hash: canonical_sha256(&text)?,
            packet_digest: String::new(),
            completeness: "complete".into(),
            captured_at: "2026-08-10T01:00:00Z".into(),
            provider_timestamp: None,
        })?;
    }
    Ok(store.project(project_id)?.ok_or("seeded project missing")?)
}

fn demo_object(
    project_id: &str,
    row: &Value,
    timestamp: &str,
) -> Result<StateObject, Box<dyn std::error::Error>> {
    let object_type = match row["type"].as_str().unwrap_or_default() {
        "OBJECTIVE" => StateType::Objective,
        "CONCEPT" => StateType::Concept,
        "DECISION" => StateType::Decision,
        "CONSTRAINT" => StateType::Constraint,
        "REJECTED_PATH" => StateType::RejectedPath,
        "COMPLETED_WORK" => StateType::CompletedWork,
        "UNRESOLVED_DEPENDENCY" => StateType::UnresolvedDependency,
        "EVIDENCE" => StateType::Evidence,
        other => return Err(format!("unsupported demo state type: {other}").into()),
    };
    let status = match row["status"].as_str().unwrap_or("active") {
        "active" => StateStatus::Active,
        "rejected" => StateStatus::Rejected,
        "superseded" => StateStatus::Superseded,
        other => return Err(format!("unsupported demo status: {other}").into()),
    };
    let binding_strength = match row["binding"].as_str().unwrap_or("soft") {
        "hard" => BindingStrength::Hard,
        "soft" => BindingStrength::Soft,
        _ => BindingStrength::Advisory,
    };
    let text = row["text"].as_str().unwrap_or_default();
    Ok(StateObject {
        id: row["id"].as_str().unwrap_or_default().into(),
        project_id: project_id.into(),
        workstream_id: Some("demo-main".into()),
        object_type,
        title: row["title"].as_str().unwrap_or_default().into(),
        canonical_text: text.into(),
        status,
        authority: Authority::User,
        confidence: 1.0,
        binding_strength: Some(binding_strength),
        source_turn_ids: vec![],
        evidence_ids: row["evidence_ids"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
            .map(str::to_owned)
            .collect(),
        branch_refs: vec![],
        created_at: timestamp.into(),
        updated_at: timestamp.into(),
        effective_at: timestamp.into(),
        supersedes_id: row["supersedes_id"].as_str().map(str::to_owned),
        reconsideration_condition: row["reconsideration_condition"].as_str().map(str::to_owned),
        content_hash: canonical_sha256(&text)?,
        state_version: 0,
    })
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // The dev runner supplies the daemon's directory. Preserve the old
            // standalone location unless the owner explicitly selects a store.
            let data_dir = std::env::var_os("TOM_ASSIST_APP_SUPPORT")
                .map(std::path::PathBuf::from)
                .unwrap_or(app.path().app_data_dir()?);
            std::fs::create_dir_all(&data_dir)?;
            let mut recovered = Store::open_with_recovery(data_dir.join("tom-assist.sqlite3"))?;
            // Keep the alpha deterministic even if the webview has not invoked a
            // command yet. Never seed or mutate a failed-migration database.
            if recovered.mode == StoreMode::ReadWrite {
                seed_demo_store(&mut recovered.store)?;
            }
            app.manage(DesktopState {
                store: Mutex::new(recovered.store),
                store_mode: recovered.mode,
                migration_backup: recovered.backup_path.map(|path| path.display().to_string()),
                migration_error: recovered.migration_error,
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            list_projects,
            create_project,
            archive_project,
            rename_project,
            project_state,
            capture_state,
            supersede_state,
            audit_events,
            list_interventions,
            resolve_intervention,
            export_project,
            import_project,
            backup_project,
            verify_archive,
            exchange_request,
            diagnostics,
            memory_settings,
            seed_demo
        ])
        .run(tauri::generate_context!())
        .expect("failed to run Tom Assist desktop");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn seeded_demo_has_contract_counts_and_auditable_supersession() {
        let mut store = Store::open_memory().unwrap();
        let project = seed_demo_store(&mut store).unwrap();
        let state = store.current_state(&project.id).unwrap();
        assert_eq!(state.objects.len(), 16);
        assert_eq!(
            state
                .objects
                .iter()
                .filter(|object| object.object_type == StateType::Objective)
                .count(),
            1
        );
        assert_eq!(
            state
                .objects
                .iter()
                .filter(|object| object.object_type == StateType::Concept)
                .count(),
            2
        );
        assert_eq!(
            state
                .objects
                .iter()
                .filter(|object| object.object_type == StateType::Decision)
                .count(),
            3
        );
        assert_eq!(
            state
                .objects
                .iter()
                .filter(|object| object.object_type == StateType::Constraint)
                .count(),
            2
        );
        assert_eq!(
            state
                .objects
                .iter()
                .filter(|object| object.object_type == StateType::RejectedPath)
                .count(),
            2
        );
        assert_eq!(
            state
                .objects
                .iter()
                .filter(|object| object.object_type == StateType::CompletedWork)
                .count(),
            2
        );
        assert_eq!(
            state
                .objects
                .iter()
                .filter(|object| object.object_type == StateType::UnresolvedDependency)
                .count(),
            2
        );
        assert_eq!(
            state
                .objects
                .iter()
                .filter(|object| object.supersedes_id.is_some())
                .count(),
            1
        );
        let turn_count = include_str!("../../../../tests/fixtures/demo_project.jsonl")
            .lines()
            .filter(|line| line.contains("\"kind\":\"turn\""))
            .count();
        assert_eq!(turn_count, 30);
        assert_eq!(store.replay(&project.id).unwrap(), state);
    }
}
