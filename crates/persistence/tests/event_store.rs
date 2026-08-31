use tempfile::tempdir;
use tom_assist_persistence::{Store, StoreError, StoreMode};
use tom_assist_protocol::{
    Authority, BindingStrength, EdgeType, StateEdge, StateObject, StateStatus, StateType,
    canonical_sha256,
};

const NOW: &str = "2026-08-09T12:00:00Z";

fn object(project: &str, id: &str, object_type: StateType, text: &str) -> StateObject {
    StateObject {
        id: id.into(),
        project_id: project.into(),
        workstream_id: Some("workstream-1".into()),
        object_type,
        title: text.into(),
        canonical_text: text.into(),
        status: StateStatus::Active,
        authority: Authority::User,
        confidence: 1.0,
        binding_strength: Some(BindingStrength::Hard),
        source_turn_ids: vec![],
        evidence_ids: vec![],
        branch_refs: vec![],
        created_at: NOW.into(),
        updated_at: NOW.into(),
        effective_at: NOW.into(),
        supersedes_id: None,
        reconsideration_condition: None,
        content_hash: format!("sha256:{:0>64}", id),
        state_version: 0,
    }
}

fn seed(store: &mut Store, project: &str) {
    store
        .create_project(
            project,
            "Demo",
            "state-focused",
            "default",
            "user-1",
            "create-1",
            NOW,
        )
        .unwrap();
    store
        .commit_object(
            object(
                project,
                "1",
                StateType::Objective,
                "Ship a deterministic local companion",
            ),
            0,
            "user",
            "user-1",
            "commit-1",
            NOW,
        )
        .unwrap();
    store
        .commit_object(
            object(
                project,
                "2",
                StateType::Constraint,
                "Never auto-commit provider text",
            ),
            1,
            "user",
            "user-1",
            "commit-2",
            NOW,
        )
        .unwrap();
}

#[test]
fn event_replay_is_deterministic_idempotent_and_cas_guarded() {
    let mut store = Store::open_memory().unwrap();
    seed(&mut store, "project-1");
    let before_duplicate = store.project("project-1").unwrap().unwrap();
    let duplicate = store
        .commit_object(
            object(
                "project-1",
                "2",
                StateType::Constraint,
                "Never auto-commit provider text",
            ),
            1,
            "user",
            "user-1",
            "commit-2",
            NOW,
        )
        .unwrap();
    assert_eq!(duplicate.base_state_version, 1);
    assert_eq!(
        store.project("project-1").unwrap().unwrap(),
        before_duplicate
    );

    let current = store.current_state("project-1").unwrap();
    let replayed = store.replay("project-1").unwrap();
    assert_eq!(current, replayed);
    assert_eq!(
        canonical_sha256(&current).unwrap(),
        before_duplicate.state_digest
    );

    let stale = store.commit_object(
        object("project-1", "3", StateType::Decision, "Use CAS"),
        1,
        "user",
        "user-1",
        "stale",
        NOW,
    );
    assert!(matches!(
        stale,
        Err(StoreError::StateVersionConflict {
            expected: 1,
            actual: 2
        })
    ));
}

#[test]
fn provider_candidates_cannot_cross_the_authority_gate() {
    let mut store = Store::open_memory().unwrap();
    store
        .create_project(
            "project-1",
            "Demo",
            "state-focused",
            "default",
            "user-1",
            "create",
            NOW,
        )
        .unwrap();
    let mut candidate = object(
        "project-1",
        "candidate",
        StateType::Decision,
        "Untrusted output",
    );
    candidate.authority = Authority::ProviderCandidate;
    assert!(matches!(
        store.commit_object(candidate, 0, "provider", "provider", "candidate", NOW),
        Err(StoreError::CandidateAuthority)
    ));
    assert_eq!(
        store.project("project-1").unwrap().unwrap().state_version,
        0
    );
}

#[test]
fn native_import_batches_preserve_authority_provenance_and_event_versions() {
    let mut store = Store::open_memory().unwrap();
    store
        .create_project(
            "project-1",
            "Imported fixture",
            "state-focused",
            "default",
            "owner",
            "create-import",
            NOW,
        )
        .unwrap();
    let first = object("project-1", "old", StateType::Decision, "Old method");
    let mut second = object("project-1", "new", StateType::Decision, "New method");
    second.authority = Authority::ProviderCandidate;
    second.status = StateStatus::Proposed;
    second.source_turn_ids = vec!["60000000-0000-4000-8000-000000000001:assistant".into()];
    store
        .import_state_batch(
            "project-1",
            vec![first],
            vec![],
            0,
            "wp25-importer",
            "import-1",
            NOW,
        )
        .unwrap();
    store
        .import_state_batch(
            "project-1",
            vec![second],
            vec![StateEdge {
                id: "edge-1".into(),
                project_id: "project-1".into(),
                from_state_id: "new".into(),
                edge_type: EdgeType::Supersedes,
                to_state_id: "old".into(),
                created_event_id: "import-2".into(),
            }],
            1,
            "wp25-importer",
            "import-2",
            NOW,
        )
        .unwrap();
    let state = store.current_state("project-1").unwrap();
    assert_eq!(state.state_version, 2);
    assert_eq!(state.edges.len(), 1);
    let imported = state.objects.iter().find(|row| row.id == "new").unwrap();
    assert_eq!(imported.authority, Authority::ProviderCandidate);
    assert_eq!(imported.status, StateStatus::Proposed);
    assert_eq!(imported.source_turn_ids[0], "60000000-0000-4000-8000-000000000001:assistant");
    assert_eq!(store.replay("project-1").unwrap(), state);
}

#[test]
fn canonical_digest_survives_twenty_five_reopens() {
    let directory = tempdir().unwrap();
    let path = directory.path().join("assist.sqlite");
    let (expected_state, expected_digest) = {
        let mut store = Store::open(&path).unwrap();
        seed(&mut store, "project-1");
        let state = store.current_state("project-1").unwrap();
        let digest = store.project("project-1").unwrap().unwrap().state_digest;
        (state, digest)
    };
    for _ in 0..25 {
        let store = Store::open(&path).unwrap();
        assert_eq!(store.current_state("project-1").unwrap(), expected_state);
        assert_eq!(store.replay("project-1").unwrap(), expected_state);
        assert_eq!(
            store.project("project-1").unwrap().unwrap().state_digest,
            expected_digest
        );
    }
}

#[test]
fn snapshot_and_portable_export_verify_and_import() {
    let directory = tempdir().unwrap();
    let export = directory.path().join("export");
    let mut source = Store::open(directory.path().join("source.sqlite")).unwrap();
    seed(&mut source, "project-1");
    let snapshot = source
        .create_snapshot("project-1", "sha256:checkpoint", "8799ccbdd", NOW)
        .unwrap();
    source.verify_snapshot(&snapshot).unwrap();
    source.export_project("project-1", &export).unwrap();
    Store::verify_export(&export).unwrap();

    let mut destination = Store::open(directory.path().join("destination.sqlite")).unwrap();
    destination.import_project(&export).unwrap();
    assert_eq!(
        source.current_state("project-1").unwrap(),
        destination.current_state("project-1").unwrap()
    );
    assert_eq!(
        source.events("project-1").unwrap(),
        destination.events("project-1").unwrap()
    );
}

#[test]
fn supersession_keeps_prior_state_auditable() {
    let mut store = Store::open_memory().unwrap();
    seed(&mut store, "project-1");
    let replacement = object(
        "project-1",
        "3",
        StateType::Decision,
        "Use the revised path",
    );
    store
        .supersede(
            "project-1",
            "1",
            replacement,
            "new evidence",
            2,
            "user-1",
            "supersede-1",
            NOW,
        )
        .unwrap();
    let old = store.state_object("project-1", "1").unwrap().unwrap();
    let new = store.state_object("project-1", "3").unwrap().unwrap();
    assert_eq!(old.status, StateStatus::Superseded);
    assert_eq!(new.supersedes_id.as_deref(), Some("1"));
    assert_eq!(store.current_state("project-1").unwrap().edges.len(), 1);
}

#[test]
fn migration_failure_preserves_backup_and_enters_read_only_safe_mode() {
    let directory = tempdir().unwrap();
    let path = directory.path().join("damaged.sqlite3");
    let damaged = b"not-a-sqlite-database\0preserve-me";
    std::fs::write(&path, damaged).unwrap();
    let recovered = Store::open_with_recovery(&path).unwrap();
    assert_eq!(recovered.mode, StoreMode::ReadOnlySafe);
    assert!(
        recovered
            .migration_error
            .as_deref()
            .is_some_and(|message| !message.is_empty())
    );
    let backup = recovered.backup_path.unwrap();
    assert_eq!(std::fs::read(backup).unwrap(), damaged);
    assert!(recovered.store.project("anything").is_err());
}
