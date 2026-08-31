use serde_json::{Value, json};
use std::{
    path::Path,
    process::{Child, Command, Stdio},
    thread,
    time::Duration,
};
use tom_assist_persistence::Store;
use tom_assist_tom_adapter::GatewayClient;
use tom_assistd::{
    AssistService, EvaluateTurnRequest, PrepareTurnRequest, SendTurnRequest, recovery,
};

struct Gateway(Child, GatewayClient);
impl Gateway {
    fn start(root: &Path, data: &Path, socket: &Path) -> Self {
        let child = Command::new(root.join(".venv-gateway/bin/python"))
            .arg(root.join("gateway/tom_gateway.py"))
            .arg("--socket")
            .arg(socket)
            .arg("--data-dir")
            .arg(data)
            .env("PYTHONDONTWRITEBYTECODE", "1")
            .stdout(Stdio::null())
            .stderr(Stdio::inherit())
            .spawn()
            .unwrap();
        let mut process = Self(child, GatewayClient::new(socket));
        for _ in 0..500 {
            if process.1.health().is_ok() {
                return process;
            }
            assert!(process.0.try_wait().unwrap().is_none());
            thread::sleep(Duration::from_millis(20));
        }
        panic!("test gateway failed to start");
    }
}
impl Drop for Gateway {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

#[test]
fn complete_archive_restores_wal_ledger_runtime_and_exactly_once_lineage() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .unwrap();
    let tmp = tempfile::tempdir_in("/tmp").unwrap();
    let source = Gateway::start(
        &root,
        &tmp.path().join("source-runtime"),
        &tmp.path().join("source.sock"),
    );
    let database = tmp.path().join("source.sqlite3");
    let mut store = Store::open(&database).unwrap();
    store
        .create_project(
            "archive-project",
            "Archive me",
            "full-local",
            "context-policy/1.1",
            "owner",
            "create-a",
            "2026-08-31T00:00:00Z",
        )
        .unwrap();
    store
        .create_project(
            "private-other",
            "DO NOT EXPORT OTHER PROJECT",
            "full-local",
            "context-policy/1.1",
            "owner",
            "create-b",
            "2026-08-31T00:00:00Z",
        )
        .unwrap();
    let service = AssistService::with_gateway(store, source.1.clone());
    let draft = "Check the connected beam-column load path.";
    let prepared = service.prepare_turn(serde_json::from_value::<PrepareTurnRequest>(json!({
        "project_id":"archive-project","workstream_id":"main","provider_session_id":"archive-session","user_draft":draft,
        "tom_checkpoint_digest":"daemon-owned","tom_activation_id":"daemon-owned","created_at":"2026-08-31T00:00:01Z",
        "provider_capabilities":{"provider_surface":"local-fixture","visible_prompt_injection":true,"response_capture":true,"hidden_context_visibility":false,"model_internal_bias":"none"}
    })).unwrap()).unwrap();
    service
        .send_turn(SendTurnRequest {
            project_id: "archive-project".into(),
            packet_digest: prepared.packet.packet_digest.clone(),
            user_draft: draft.into(),
            turn_id: "archive-sent".into(),
            ordinal: 1,
            idempotency_key: "send".into(),
            captured_at: "2026-08-31T00:00:02Z".into(),
        })
        .unwrap();
    let evaluate = EvaluateTurnRequest {
        project_id: "archive-project".into(),
        packet_digest: prepared.packet.packet_digest.clone(),
        response_turn_id: "archive-response".into(),
        response_text: "The connected beam transfers force to both columns. ".repeat(20),
        ordinal: 2,
        complete: true,
        created_at: "2026-08-31T00:00:03Z".into(),
        latency_ms: 0,
    };
    service.evaluate_turn(evaluate.clone()).unwrap();
    source.1.save_checkpoint("archive-project").unwrap();
    source
        .1
        .memory_settings(
            "archive-project",
            json!({"front_row_capacity":32,"teach_on_conflict":false}),
        )
        .unwrap();
    let observer = Store::open(&database).unwrap();
    let receipt = observer
        .runtime_commit_for_sent("archive-sent")
        .unwrap()
        .unwrap();
    let expected_diagnostics = source.1.memory_diagnostics("archive-project", 0).unwrap();
    assert!(
        std::fs::metadata(database.with_extension("sqlite3-wal"))
            .unwrap()
            .len()
            > 0
    );
    let archive = tmp.path().join("complete-archive");
    let dangling = tmp.path().join("existing-dangling-link");
    std::os::unix::fs::symlink(tmp.path().join("absent"), &dangling).unwrap();
    assert!(recovery::export_project(&observer, &source.1, "archive-project", &dangling).is_err());
    assert!(
        std::fs::symlink_metadata(&dangling)
            .unwrap()
            .file_type()
            .is_symlink()
    );
    recovery::export_project(&observer, &source.1, "archive-project", &archive).unwrap();
    assert!(
        !std::fs::read_to_string(archive.join("ledger.json"))
            .unwrap()
            .contains("DO NOT EXPORT OTHER PROJECT")
    );
    let verified = recovery::verify_project(&source.1, &archive).unwrap();
    assert_eq!(verified["project_id"], "archive-project");
    assert_eq!(
        source.1.memory_diagnostics("archive-project", 0).unwrap(),
        expected_diagnostics
    );
    assert!(
        recovery::export_project(&observer, &source.1, "archive-project", &archive).is_err(),
        "never overwrite an archive"
    );

    // Both sides of publication must roll back relational rows and quarantine
    // only this newly staged runtime. Lost finalization replies recover lazily.
    for fault in ["before-publish", "after-publish", "finalize"] {
        let data = tmp.path().join(fault);
        let failing = Gateway::start(&root, &data, &tmp.path().join(format!("{fault}.sock")));
        let mut ledger = Store::open(tmp.path().join(format!("{fault}.sqlite3"))).unwrap();
        let result = ledger.import_recovery_archive(&archive, |action, path, context| {
            if (fault == "before-publish" && action == "publish")
                || (fault == "finalize" && action == "finalize")
            {
                return Err(tom_assist_persistence::StoreError::Integrity(
                    "injected lifecycle failure".into(),
                ));
            }
            let result = failing
                .1
                .import_runtime(action, path, context)
                .map_err(|e| tom_assist_persistence::StoreError::Integrity(e.to_string()))?;
            if fault == "after-publish" && action == "publish" {
                return Err(tom_assist_persistence::StoreError::Integrity(
                    "injected lost publication reply".into(),
                ));
            }
            Ok(result)
        });
        if fault == "finalize" {
            result.unwrap();
            assert_eq!(
                failing.1.memory_diagnostics("archive-project", 0).unwrap(),
                expected_diagnostics
            );
            assert!(
                !data
                    .join("projects/archive-project/tom/recovery-intent.json")
                    .exists()
            );
        } else {
            assert!(result.is_err());
            assert!(ledger.list_projects().unwrap().is_empty());
            assert!(!data.join("projects/archive-project").exists());
            assert_eq!(
                std::fs::read_dir(data.join("recovery-staging"))
                    .unwrap()
                    .count(),
                1
            );
            recovery::import_project(&mut ledger, &failing.1, &archive).unwrap();
        }
    }

    let target_dir = tmp.path().join("target-runtime");
    let target_socket = tmp.path().join("target.sock");
    let target = Gateway::start(&root, &target_dir, &target_socket);
    let target_database = tmp.path().join("target.sqlite3");
    let mut restored = Store::open(&target_database).unwrap();
    restored
        .create_project(
            "existing-unrelated",
            "Keep me",
            "full-local",
            "context-policy/1.1",
            "owner",
            "create-c",
            "2026-08-31T00:00:00Z",
        )
        .unwrap();
    recovery::import_project(&mut restored, &target.1, &archive).unwrap();
    assert_eq!(restored.list_projects().unwrap().len(), 2);
    assert!(restored.project("private-other").unwrap().is_none());
    assert_eq!(
        restored.current_state("archive-project").unwrap(),
        observer.current_state("archive-project").unwrap()
    );
    assert_eq!(
        restored.events("archive-project").unwrap(),
        observer.events("archive-project").unwrap()
    );
    assert_eq!(
        restored
            .runtime_commit_for_sent("archive-sent")
            .unwrap()
            .unwrap(),
        receipt
    );
    assert_eq!(
        restored
            .context_run_by_digest("archive-project", &prepared.packet.packet_digest)
            .unwrap(),
        observer
            .context_run_by_digest("archive-project", &prepared.packet.packet_digest)
            .unwrap()
    );
    assert_eq!(
        target.1.memory_diagnostics("archive-project", 0).unwrap(),
        expected_diagnostics
    );
    assert!(recovery::import_project(&mut restored, &target.1, &archive).is_err());
    drop(restored);
    drop(target);
    let restarted = Gateway::start(&root, &target_dir, &target_socket);
    let restarted_service =
        AssistService::with_gateway(Store::open(&target_database).unwrap(), restarted.1.clone());
    restarted_service.evaluate_turn(evaluate).unwrap();
    assert_eq!(
        restarted
            .1
            .memory_diagnostics("archive-project", 0)
            .unwrap(),
        expected_diagnostics,
        "replayed evaluation must not double commit after recovery/restart"
    );

    // Manifest tampering/path traversal is rejected before lifecycle staging.
    let mut manifest: Value =
        serde_json::from_slice(&std::fs::read(archive.join("manifest.json")).unwrap()).unwrap();
    manifest["files"]["../outside"] = json!("sha256:forged");
    std::fs::write(
        archive.join("manifest.json"),
        serde_json::to_vec(&manifest).unwrap(),
    )
    .unwrap();
    assert!(Store::verify_recovery_archive(&archive).is_err());
}
