use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::thread;
use std::time::Duration;
use tempfile::Builder;
use tom_assist_tom_adapter::GatewayClient;

struct ChildGuard(Child);
impl Drop for ChildGuard {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

#[test]
fn live_gateway_handshake_commit_preview_and_checkpoint() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .unwrap();
    let tom_master = Path::new("/Users/kenmorkaya/PycharmProjects/tom_master");
    assert!(tom_master.join("controller/external_api.py").exists());
    let scratch_root = root.join(".tmp");
    fs::create_dir_all(&scratch_root).unwrap();
    let temporary = Builder::new()
        .prefix("tom-assist-gw-")
        .tempdir_in(scratch_root)
        .unwrap();
    let socket = temporary.path().join("gateway.sock");
    let gateway_python = root.join(".venv-gateway/bin/python");
    assert!(
        gateway_python.exists(),
        "create .venv-gateway per gateway/README.md"
    );
    let child = Command::new(gateway_python)
        .arg(root.join("gateway/tom_gateway.py"))
        .arg("--socket")
        .arg(&socket)
        .arg("--data-dir")
        .arg(temporary.path().join("data"))
        .arg("--tom-master")
        .arg(tom_master)
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
    assert!(socket.exists(), "gateway socket did not appear");
    assert_eq!(
        fs::metadata(&socket).unwrap().permissions().mode() & 0o777,
        0o600
    );

    let client = GatewayClient::new(&socket);
    assert_eq!(client.health().unwrap()["pinned_sha_match"], true);
    let capabilities = client.capabilities().unwrap();
    assert!(capabilities.supports_readonly_ranking);
    assert!(!capabilities.supports_nonmutating_load_preview);
    assert_eq!(capabilities.seed_profile, "msr_8d_native_10k");
    assert_eq!(capabilities.seed_tick, 4707);
    assert_eq!(capabilities.seed_branch_count, 10_000);
    assert_eq!(
        capabilities.kappa_decay_source,
        "profile_env_reader_wp18_effective_0.03"
    );
    let committed = client
        .commit_turn("rust-live", "user", "Keep preview pure.", "turn-1")
        .unwrap();
    assert_eq!(committed.engine_tick_before, capabilities.seed_tick);
    assert_eq!(committed.engine_tick_after, capabilities.seed_tick + 1);
    assert_eq!(committed.seed_profile, capabilities.seed_profile);
    assert_eq!(
        committed.prior_checkpoint_digest,
        committed.seed_checkpoint_digest
    );
    assert_ne!(
        committed.checkpoint_digest,
        committed.prior_checkpoint_digest
    );
    assert_ne!(committed.anchor_id, "deferred");
    let preview = client
        .preview_rank("rust-live", "What must stay pure?", 10, 2000)
        .unwrap();
    assert_eq!(preview.ranked_anchors.len(), 1);
    assert_eq!(preview.checkpoint_digest, committed.checkpoint_digest);
    assert!(client.save_checkpoint("rust-live").unwrap()["checkpoint_id"].is_string());
}
