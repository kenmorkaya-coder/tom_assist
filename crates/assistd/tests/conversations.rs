//! Production orchestration + real pinned gateway, deterministic provider transport.
//! These are build checks, not spec G-gates. Live OAuth is separately ignored.
use serde_json::{Value, json};
use std::{
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::{
        Arc, Barrier, Mutex,
        atomic::{AtomicUsize, Ordering},
    },
    thread,
    time::Duration,
};
use tom_assist_persistence::Store;
use tom_assist_tom_adapter::GatewayClient;
use tom_assistd::{AssistService, provider::ProviderAdapter, recovery};
const AT: &str = "2026-08-31T00:00:00Z";

struct Gateway(Child, GatewayClient);
impl Gateway {
    fn start(data: &Path, socket: &Path) -> Self {
        let root = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../..")
            .canonicalize()
            .unwrap();
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
        let mut gateway = Self(child, GatewayClient::new(socket));
        for _ in 0..500 {
            if gateway.1.health().is_ok() {
                return gateway;
            }
            assert!(gateway.0.try_wait().unwrap().is_none());
            thread::sleep(Duration::from_millis(20));
        }
        panic!("gateway did not start");
    }
}
impl Drop for Gateway {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

#[derive(Clone)]
struct Fixture {
    calls: Arc<AtomicUsize>,
    prompts: Arc<Mutex<Vec<String>>>,
    connected: bool,
    fail: bool,
    barriers: Option<(Arc<Barrier>, Arc<Barrier>)>,
    response: String,
}
impl Default for Fixture {
    fn default() -> Self {
        Self {
            calls: Arc::new(AtomicUsize::new(0)),
            prompts: Arc::default(),
            connected: true,
            fail: false,
            barriers: None,
            response: "The connected beam transfers force to both columns. ".repeat(24),
        }
    }
}
impl ProviderAdapter for Fixture {
    fn status(&self) -> tom_assistd::Result<Value> {
        Ok(json!({"connected":self.connected}))
    }
    fn complete(&self, prompt: &str) -> tom_assistd::Result<String> {
        self.calls.fetch_add(1, Ordering::SeqCst);
        self.prompts.lock().unwrap().push(prompt.into());
        if let Some((start, finish)) = &self.barriers {
            start.wait();
            finish.wait();
        }
        if self.fail {
            return Err(tom_assistd::ServiceError::Invalid(
                "synthetic lost provider reply".into(),
            ));
        }
        Ok(self.response.clone())
    }
}
struct Harness {
    _tmp: tempfile::TempDir,
    database: PathBuf,
    gateway: Gateway,
}
impl Harness {
    fn new() -> Self {
        let tmp = tempfile::tempdir_in("/tmp").unwrap();
        let database = tmp.path().join("ledger.sqlite3");
        let mut store = Store::open(&database).unwrap();
        for project in ["chat-project", "other-project"] {
            store
                .create_project(
                    project,
                    project,
                    "full-local",
                    "context-policy/1.1",
                    "owner",
                    project,
                    AT,
                )
                .unwrap();
            store
                .create_conversation(
                    project,
                    &format!("{project}-session"),
                    "Project conversation",
                    AT,
                )
                .unwrap();
        }
        let gateway = Gateway::start(
            &tmp.path().join("runtime"),
            &tmp.path().join("gateway.sock"),
        );
        Self {
            _tmp: tmp,
            database,
            gateway,
        }
    }
    fn service(&self, fixture: Fixture) -> AssistService {
        AssistService::with_gateway(Store::open(&self.database).unwrap(), self.gateway.1.clone())
            .with_provider_adapter(fixture)
    }
    fn observer(&self) -> Store {
        Store::open(&self.database).unwrap()
    }
}
fn prepare(s: &AssistService, id: &str, draft: &str) -> Value {
    s.conversation_prepare(
        "chat-project",
        &json!({"session_id":"chat-project-session","exchange_id":id,"user_draft":draft}),
        AT,
    )
    .unwrap()
}
fn send_payload(p: &Value) -> Value {
    json!({"exchange_id":p["id"],"confirmed_prompt_hash":p["prompt_hash"],"explicit_send":true})
}

fn capture_request(source: &str) -> tom_assistd::chat_capture::ChatCaptureRequest {
    serde_json::from_value(json!({"project_id":"chat-project","source_turn_id":source,"text":"Owner-confirmed new decision","object_id":"captured-decision","idempotency_key":"capture","base_state_version":0,"confirmed":true,"created_at":AT})).unwrap()
}

#[derive(Clone, Default)]
struct ReportFixture {
    calls: Arc<AtomicUsize>,
    reply: Arc<Mutex<Option<String>>>,
    fail: bool,
}
impl ProviderAdapter for ReportFixture {
    fn status(&self) -> tom_assistd::Result<Value> {
        Ok(json!({"connected":true}))
    }
    fn complete(&self, prompt: &str) -> tom_assistd::Result<String> {
        self.calls.fetch_add(1, Ordering::SeqCst);
        if prompt.starts_with("[TOM_ASSIST_SELF_REPORT") {
            if self.fail {
                return Err(tom_assistd::ServiceError::Invalid(
                    "fixture lost reply".into(),
                ));
            }
            return Ok(self
                .reply
                .lock()
                .unwrap()
                .clone()
                .expect("fixture reply configured"));
        }
        Ok("The beam transfers force through the connected columns.".into())
    }
}
fn report_candidate(report: &Value) -> Value {
    json!({"candidate_id":report["candidate_slots"][0],"project_id":"chat-project",
        "source_turn_ids":[report["source_turn_id"]],"proposed_by":"provider_candidate","operation":"CREATE",
        "object":{"type":"CONSTRAINT","title":"Local only","canonical_text":"Keep all processing local.",
            "status":"proposed","confidence":0.5,"evidence_ids":[],"target_state_id":null,"reason":null},
        "tom_check":{"result":"review","conflicts":[],"requires_user_confirmation":true}})
}
fn report_send(report: &Value) -> Value {
    json!({"exchange_id":report["exchange_id"],"confirmed_prompt_hash":report["prompt_hash"],"explicit_send":true})
}
fn report_service(h: &Harness, fixture: &ReportFixture, enabled: bool) -> AssistService {
    AssistService::with_gateway(h.observer(), h.gateway.1.clone())
        .with_provider_adapter(fixture.clone())
        .with_provider_self_report(enabled)
}

#[test]
fn structural_guardrails_are_review_only_pure_and_quote_the_matched_span() {
    let h = Harness::new();
    for (n, (kind, status)) in [
        ("REJECTED_PATH", "rejected"),
        ("CONSTRAINT", "active"),
        ("COMPLETED_WORK", "satisfied"),
    ]
    .iter()
    .enumerate()
    {
        let mut object = json!(decision(
            "A beam connects two columns and supports load.",
            "active"
        ));
        object["type"] = json!(kind);
        object["status"] = json!(status);
        object["id"] = json!(format!("guard-{n}"));
        h.observer()
            .commit_object(
                serde_json::from_value(object).unwrap(),
                n as u64,
                "user",
                "owner",
                &format!("plant-{n}"),
                AT,
            )
            .unwrap();
    }
    let fixture = ReportFixture::default();
    let service = report_service(&h, &fixture, false);
    let prepared = prepare(&service, "resonance", "Describe the structure.");
    let before = h.gateway.1.memory_diagnostics("chat-project", 0).unwrap();
    let view = service
        .conversation_send("chat-project", &send_payload(&prepared), AT)
        .unwrap();
    assert_eq!(view["exchanges"][0]["evaluation"]["result"], "REVIEW");
    assert!(view["exchanges"][0]["commit"].is_null());
    let findings = view["interventions"].as_array().unwrap();
    assert_eq!(findings.len(), 3);
    for finding in findings {
        assert_eq!(finding["severity"], "warning");
        assert_eq!(finding["policy_version"], "guardrail-resonance/1");
        assert!(
            finding["summary"]
                .as_str()
                .unwrap()
                .contains("The beam transfers force through the connected columns.")
        );
    }
    assert_eq!(
        before,
        h.gateway.1.memory_diagnostics("chat-project", 0).unwrap()
    );
    assert_eq!(
        h.observer()
            .current_state("chat-project")
            .unwrap()
            .state_version,
        3
    );
    assert_eq!(fixture.calls.load(Ordering::SeqCst), 1);
}

#[test]
fn self_report_is_explicit_once_candidate_only_labelled_and_recoverable() {
    let h = Harness::new();
    let f = ReportFixture::default();
    let disabled = report_service(&h, &f, false);
    let p = prepare(&disabled, "report", "Describe the structure.");
    disabled
        .conversation_send("chat-project", &send_payload(&p), AT)
        .unwrap();
    assert!(
        disabled
            .self_report_prepare("chat-project", "report", AT)
            .is_err()
    );
    let s = report_service(&h, &f, true);
    let before = h.gateway.1.memory_diagnostics("chat-project", 0).unwrap();
    let r = s.self_report_prepare("chat-project", "report", AT).unwrap();
    assert_eq!(
        r,
        s.self_report_prepare("chat-project", "report", AT).unwrap()
    );
    assert_eq!(f.calls.load(Ordering::SeqCst), 1);
    let mut forged = report_send(&r);
    forged["explicit_send"] = json!(false);
    assert!(s.self_report_send("chat-project", &forged, AT).is_err());
    forged = report_send(&r);
    forged["confirmed_prompt_hash"] = json!("wrong");
    assert!(s.self_report_send("chat-project", &forged, AT).is_err());
    assert!(
        s.self_report_send("other-project", &report_send(&r), AT)
            .is_err()
    );
    let candidates: Vec<Value> = ["CONSTRAINT", "DECISION", "REJECTED_PATH", "COMPLETED_WORK"]
        .iter()
        .enumerate()
        .map(|(n, kind)| {
            let mut candidate = report_candidate(&r);
            candidate["candidate_id"] = r["candidate_slots"][n].clone();
            candidate["object"]["type"] = json!(kind);
            candidate
        })
        .collect();
    *f.reply.lock().unwrap() = Some(json!({"candidates":candidates}).to_string());
    let result = s
        .self_report_send("chat-project", &report_send(&r), AT)
        .unwrap();
    assert_eq!(result["status"], "complete");
    assert_eq!(result["metrics"]["logical_calls_claimed"], 1);
    assert_eq!(result["metrics"]["adjudicated"], 4);
    assert_eq!(result["metrics"]["emitted"], 4);
    assert_eq!(result["adjudications"][0]["result"]["accepted"], true);
    assert!(result["precision"]["value"].is_null());
    let cid = result["candidates"][0]["candidate_id"].as_str().unwrap();
    let saved = h.observer().candidate(cid).unwrap().unwrap();
    assert_eq!(
        saved.proposed_by,
        tom_assist_protocol::Authority::ProviderCandidate
    );
    assert_eq!(saved.object["status"], "proposed");
    assert_eq!(saved.tom_check.result, "review");
    assert!(saved.tom_check.requires_user_confirmation);
    for (label, value) in [
        ("accurate", json!(1.0)),
        ("false_positive", json!(0.0)),
        ("unreviewed", Value::Null),
    ] {
        let labelled = h
            .observer()
            .label_self_report("chat-project", "report", cid, label, AT)
            .unwrap();
        assert_eq!(
            tom_assistd::self_report::measured(labelled)["precision"]["value"],
            value
        );
    }
    assert_eq!(
        h.observer()
            .current_state("chat-project")
            .unwrap()
            .state_version,
        0
    );
    assert_eq!(
        before,
        h.gateway.1.memory_diagnostics("chat-project", 0).unwrap()
    );
    s.conversation_evaluate("chat-project", &json!({"exchange_id":"report"}), AT)
        .unwrap();
    let restarted = report_service(&h, &f, true);
    restarted
        .self_report_send("chat-project", &report_send(&r), AT)
        .unwrap();
    assert_eq!(f.calls.load(Ordering::SeqCst), 2); // One ordinary exchange + one follow-up.
    let saved_report = h.observer().self_report("chat-project", "report").unwrap();
    let archive = h._tmp.path().join("self-report-backup");
    recovery::export_project(&h.observer(), &h.gateway.1, "chat-project", &archive).unwrap();
    let target = Gateway::start(
        &h._tmp.path().join("restored-runtime"),
        &h._tmp.path().join("restored.sock"),
    );
    let mut restored = Store::open(h._tmp.path().join("restored.sqlite3")).unwrap();
    recovery::import_project(&mut restored, &target.1, &archive).unwrap();
    assert_eq!(
        restored.self_report("chat-project", "report").unwrap(),
        saved_report
    );
    assert_eq!(restored.candidate(cid).unwrap(), Some(saved));
}

#[test]
fn self_report_rejects_forgery_invented_evidence_invalid_json_and_lost_reply_without_resend() {
    let h = Harness::new();
    for (n, mode) in [
        "authority",
        "evidence",
        "target",
        "foreign",
        "extra",
        "json",
        "lost",
    ]
    .iter()
    .enumerate()
    {
        let f = ReportFixture {
            fail: *mode == "lost",
            ..ReportFixture::default()
        };
        let s = report_service(&h, &f, true);
        let exchange = format!("bad-report-{n}");
        let p = prepare(&s, &exchange, "Describe the structure.");
        s.conversation_send("chat-project", &send_payload(&p), AT)
            .unwrap();
        let r = s
            .self_report_prepare("chat-project", &exchange, AT)
            .unwrap();
        let mut candidate = report_candidate(&r);
        match *mode {
            "authority" => candidate["proposed_by"] = json!("tom_verified"),
            "evidence" => candidate["object"]["evidence_ids"] = json!(["invented"]),
            "target" => {
                candidate["operation"] = json!("SUPERSEDE");
                candidate["object"]["target_state_id"] = json!("foreign-target");
            }
            "foreign" => candidate["project_id"] = json!("other-project"),
            "extra" => candidate["approve"] = json!(true),
            _ => {}
        }
        *f.reply.lock().unwrap() = Some(if *mode == "json" {
            "not JSON".into()
        } else {
            json!({"candidates":[candidate]}).to_string()
        });
        let result = s
            .self_report_send("chat-project", &report_send(&r), AT)
            .unwrap();
        assert_eq!(result["candidates"], json!([]), "{mode}");
        if ["authority", "evidence", "target"].contains(mode) {
            assert_eq!(result["metrics"]["adjudicator_rejected"], 1, "{mode}");
            assert_eq!(result["adjudications"][0]["result"]["accepted"], false);
        }
        s.self_report_send("chat-project", &report_send(&r), AT)
            .unwrap();
        report_service(&h, &f, true)
            .self_report_send("chat-project", &report_send(&r), AT)
            .unwrap();
        assert_eq!(f.calls.load(Ordering::SeqCst), 2);
        assert!(
            h.observer()
                .candidate(r["candidate_slots"][0].as_str().unwrap())
                .unwrap()
                .is_none()
        );
    }
    assert_eq!(
        h.observer()
            .current_state("chat-project")
            .unwrap()
            .state_version,
        0
    );
}

#[test]
fn self_report_stale_and_interrupted_claim_never_infer_authority_or_resend() {
    let h = Harness::new();
    let f = ReportFixture::default();
    let s = report_service(&h, &f, true);
    let p = prepare(&s, "crash-report", "Describe the structure.");
    s.conversation_send("chat-project", &send_payload(&p), AT)
        .unwrap();
    let r = s
        .self_report_prepare("chat-project", "crash-report", AT)
        .unwrap();
    h.observer()
        .commit_object(
            decision("Later owner decision", "active"),
            0,
            "user",
            "owner",
            "changed",
            AT,
        )
        .unwrap();
    assert!(
        s.self_report_send("chat-project", &report_send(&r), AT)
            .is_err()
    );
    assert!(
        !h.observer()
            .claim_self_report("chat-project", "crash-report")
            .unwrap()
    );
    let refreshed = s
        .self_report_prepare("chat-project", "crash-report", AT)
        .unwrap();
    assert_ne!(refreshed["prompt_hash"], r["prompt_hash"]);
    assert!(
        s.self_report_send("chat-project", &report_send(&r), AT)
            .is_err()
    );
    assert!(
        h.observer()
            .claim_self_report("chat-project", "crash-report")
            .unwrap()
    );
    let restarted = report_service(&h, &f, true);
    assert_eq!(
        restarted
            .self_report_send("chat-project", &report_send(&refreshed), AT)
            .unwrap()["status"],
        "sending"
    );
    assert_eq!(f.calls.load(Ordering::SeqCst), 1);
}

fn decision(text: &str, status: &str) -> tom_assist_protocol::StateObject {
    serde_json::from_value(json!({"id":"owner-decision","project_id":"chat-project","type":if status=="rejected" {"REJECTED_PATH"} else {"DECISION"},"title":text,"canonical_text":text,"status":status,"authority":"user","confidence":1,"binding_strength":"hard","source_turn_ids":[],"evidence_ids":[],"branch_refs":[],"created_at":AT,"updated_at":AT,"effective_at":AT,"content_hash":tom_assist_protocol::canonical_sha256(&text).unwrap(),"state_version":1})).unwrap()
}

#[test]
fn stale_native_state_requires_explicit_review_acceptance_then_commits_once() {
    let h = Harness::new();
    let start = Arc::new(Barrier::new(2));
    let finish = Arc::new(Barrier::new(2));
    let f = Fixture {
        barriers: Some((start.clone(), finish.clone())),
        ..Fixture::default()
    };
    let s = Arc::new(h.service(f.clone()));
    let p = prepare(&s, "review", "One pending response.");
    let worker = {
        let s = s.clone();
        let p = p.clone();
        thread::spawn(move || {
            s.conversation_send("chat-project", &send_payload(&p), AT)
                .unwrap()
        })
    };
    start.wait();
    h.observer()
        .commit_object(
            decision("New owner decision during generation", "active"),
            0,
            "user",
            "owner",
            "decision",
            AT,
        )
        .unwrap();
    finish.wait();
    let view = worker.join().unwrap();
    assert_eq!(view["exchanges"][0]["evaluation"]["result"], "REVIEW");
    assert!(view["exchanges"][0]["commit"].is_null());
    s.conversation_evaluate("chat-project", &json!({"exchange_id":"review"}), AT)
        .unwrap();
    assert!(
        h.observer()
            .runtime_commit_for_sent("review:user")
            .unwrap()
            .is_none()
    );
    let accepted = s
        .conversation_evaluate(
            "chat-project",
            &json!({"exchange_id":"review","accept_reviewed":true}),
            AT,
        )
        .unwrap();
    assert!(accepted["exchanges"][0]["commit"].is_object());
    let before = h.gateway.1.memory_diagnostics("chat-project", 0).unwrap();
    s.conversation_evaluate(
        "chat-project",
        &json!({"exchange_id":"review","accept_reviewed":true}),
        AT,
    )
    .unwrap();
    assert_eq!(
        h.gateway.1.memory_diagnostics("chat-project", 0).unwrap(),
        before
    );
    assert_eq!(f.calls.load(Ordering::SeqCst), 1);
    let stale = prepare(&s, "stale-native", "Reject before contacting provider.");
    let mut changed = decision("Another owner decision", "active");
    changed.id = "second-decision".into();
    h.observer()
        .commit_object(changed, 1, "user", "owner", "change", AT)
        .unwrap();
    assert!(
        s.conversation_send("chat-project", &send_payload(&stale), AT)
            .is_err()
    );
    assert_eq!(f.calls.load(Ordering::SeqCst), 1);
}

#[test]
fn conflict_holds_experience_until_every_user_finding_resolution() {
    let h = Harness::new();
    h.observer()
        .commit_object(
            decision("use obsolete pipeline", "rejected"),
            0,
            "user",
            "owner",
            "reject",
            AT,
        )
        .unwrap();
    let f = Fixture {
        response: "Use obsolete pipeline for the release. ".repeat(24),
        ..Fixture::default()
    };
    let s = h.service(f.clone());
    let p = prepare(&s, "conflict", "Should we use obsolete pipeline?");
    assert!(
        p["prompt"]
            .as_str()
            .unwrap()
            .contains("REJECTED_OR_SUPERSEDED")
    );
    let view = s
        .conversation_send("chat-project", &send_payload(&p), AT)
        .unwrap();
    assert_eq!(view["exchanges"][0]["evaluation"]["result"], "CONFLICT");
    assert!(view["exchanges"][0]["commit"].is_null());
    let mut capture = capture_request("conflict:assistant");
    capture.base_state_version = 1;
    assert!(tom_assistd::chat_capture::capture_decision(&mut h.observer(), capture).is_err());
    assert!(
        s.conversation_evaluate(
            "chat-project",
            &json!({"exchange_id":"conflict","accept_reviewed":true}),
            AT
        )
        .is_err()
    );
    let store = h.observer();
    let findings = store.interventions("chat-project").unwrap();
    assert!(!findings.is_empty());
    for finding in findings {
        tom_assistd::experience::resolve_intervention_with_runtime(
            &store,
            Some(&h.gateway.1),
            "chat-project",
            &finding.id,
            tom_assist_protocol::InterventionStatus::Dismissed,
            AT,
        )
        .unwrap();
    }
    let receipt = store
        .runtime_commit_for_sent("conflict:user")
        .unwrap()
        .unwrap();
    assert!(receipt.is_object());
    assert_eq!(f.calls.load(Ordering::SeqCst), 1);
}

#[test]
fn explicit_send_full_governance_commit_history_restart_and_archive() {
    let h = Harness::new();
    let fixture = Fixture::default();
    let s = h.service(fixture.clone());
    let p = prepare(&s, "first", "Check the beam-column load path.");
    let before = h.gateway.1.memory_diagnostics("chat-project", 0).unwrap();
    assert_eq!(prepare(&s, "first", "Check the beam-column load path."), p);
    let _another_preview = prepare(&s, "unapproved", "This is only a preview.");
    assert_eq!(
        h.gateway.1.memory_diagnostics("chat-project", 0).unwrap(),
        before
    );
    assert_eq!(fixture.calls.load(Ordering::SeqCst), 0);
    let mut invalid = send_payload(&p);
    invalid["explicit_send"] = json!(false);
    assert!(s.conversation_send("chat-project", &invalid, AT).is_err());
    invalid = send_payload(&p);
    invalid["confirmed_prompt_hash"] = json!("forged");
    assert!(s.conversation_send("chat-project", &invalid, AT).is_err());
    assert!(
        s.conversation_send("other-project", &send_payload(&p), AT)
            .is_err()
    );
    assert_eq!(fixture.calls.load(Ordering::SeqCst), 0);
    let view = s
        .conversation_send("chat-project", &send_payload(&p), AT)
        .unwrap();
    let row = &view["exchanges"][0];
    assert_eq!(row["exchange"]["status"], "completed");
    assert_eq!(row["evaluation"]["result"], "PASS");
    assert!(row["commit"].is_object());
    assert_eq!(row["commit"]["engine_tick_after"], 4708);
    assert_eq!(
        fixture.prompts.lock().unwrap()[0],
        p["prompt"].as_str().unwrap()
    );
    assert!(
        h.observer()
            .current_state("chat-project")
            .unwrap()
            .objects
            .is_empty(),
        "captured assistant is not authoritative state"
    );
    assert_eq!(fixture.calls.load(Ordering::SeqCst), 1);
    s.conversation_send("chat-project", &send_payload(&p), AT)
        .unwrap();
    s.conversation_evaluate("chat-project", &json!({"exchange_id":"first"}), AT)
        .unwrap();
    assert_eq!(fixture.calls.load(Ordering::SeqCst), 1);
    let committed = h.gateway.1.memory_diagnostics("chat-project", 0).unwrap();
    let next = prepare(&s, "second", "Follow up locally.");
    assert!(next["prompt"].as_str().unwrap().contains(&fixture.response));
    assert_eq!(next["ordinal"], 3);
    let other=s.conversation_prepare("other-project",&json!({"session_id":"other-project-session","exchange_id":"other","user_draft":"Private other question"}),AT).unwrap();
    assert!(
        !other["prompt"]
            .as_str()
            .unwrap()
            .contains(&fixture.response)
    );
    assert!(
        s.conversation_get("other-project", "chat-project-session")
            .is_err()
    );
    drop(s);
    let restarted = h.service(fixture.clone());
    assert_eq!(
        restarted
            .conversation_get("chat-project", "chat-project-session")
            .unwrap()["turns"],
        view["turns"]
    );
    restarted
        .conversation_send("chat-project", &send_payload(&p), AT)
        .unwrap();
    assert_eq!(fixture.calls.load(Ordering::SeqCst), 1);
    assert_eq!(
        h.gateway.1.memory_diagnostics("chat-project", 0).unwrap(),
        committed
    );
    let archive = h._tmp.path().join("archive");
    recovery::export_project(&h.observer(), &h.gateway.1, "chat-project", &archive).unwrap();
    let target = Gateway::start(
        &h._tmp.path().join("restored-runtime"),
        &h._tmp.path().join("restore.sock"),
    );
    let mut ledger = Store::open(h._tmp.path().join("restore.sqlite3")).unwrap();
    recovery::import_project(&mut ledger, &target.1, &archive).unwrap();
    assert_eq!(
        ledger
            .conversation_view("chat-project", "chat-project-session")
            .unwrap(),
        h.observer()
            .conversation_view("chat-project", "chat-project-session")
            .unwrap()
    );
    assert!(ledger.conversations("other-project").unwrap().is_empty());
    let restored = AssistService::with_gateway(ledger, target.1.clone())
        .with_provider_adapter(fixture.clone());
    restored
        .conversation_evaluate("chat-project", &json!({"exchange_id":"first"}), AT)
        .unwrap();
    assert_eq!(
        target.1.memory_diagnostics("chat-project", 0).unwrap(),
        committed
    );
    assert_eq!(fixture.calls.load(Ordering::SeqCst), 1);
}

#[test]
fn lost_reply_and_interrupted_process_never_automatically_resend() {
    let h = Harness::new();
    let f = Fixture {
        fail: true,
        ..Fixture::default()
    };
    let s = h.service(f.clone());
    let p = prepare(&s, "lost", "An explicit test request.");
    let view = s
        .conversation_send("chat-project", &send_payload(&p), AT)
        .unwrap();
    assert_eq!(view["exchanges"][0]["exchange"]["status"], "unknown");
    drop(s);
    let restarted = h.service(f.clone());
    restarted
        .conversation_send("chat-project", &send_payload(&p), AT)
        .unwrap();
    assert_eq!(f.calls.load(Ordering::SeqCst), 1);
    let q = prepare(&restarted, "crashed", "Simulate crash after durable claim.");
    let ledger = h.observer();
    let record = ledger
        .provider_exchange("chat-project", "crashed")
        .unwrap()
        .unwrap();
    ledger
        .claim_provider_exchange(&record, q["prompt_hash"].as_str().unwrap())
        .unwrap();
    drop(restarted);
    let restarted = h.service(f.clone());
    let view = restarted
        .conversation_get("chat-project", "chat-project-session")
        .unwrap();
    assert_eq!(view["exchanges"][1]["exchange"]["status"], "unknown");
    restarted
        .conversation_send("chat-project", &send_payload(&q), AT)
        .unwrap();
    assert_eq!(f.calls.load(Ordering::SeqCst), 1);
    assert!(
        ledger
            .runtime_commit_for_sent("lost:user")
            .unwrap()
            .is_none()
    );
}

#[test]
fn concurrent_send_is_single_and_stale_physics_preview_is_rejected() {
    let h = Harness::new();
    let start = Arc::new(Barrier::new(2));
    let finish = Arc::new(Barrier::new(2));
    let f = Fixture {
        barriers: Some((start.clone(), finish.clone())),
        ..Fixture::default()
    };
    let s = Arc::new(h.service(f.clone()));
    let p = prepare(&s, "slow", "One request only.");
    let q = prepare(&s, "stale", "This preview will become stale.");
    let worker = {
        let s = s.clone();
        let p = p.clone();
        thread::spawn(move || {
            s.conversation_send("chat-project", &send_payload(&p), AT)
                .unwrap()
        })
    };
    start.wait();
    assert_eq!(
        s.conversation_get("chat-project", "chat-project-session")
            .unwrap()["exchanges"][0]["exchange"]["status"],
        "sending"
    );
    s.conversation_send("chat-project", &send_payload(&p), AT)
        .unwrap();
    assert!(
        s.conversation_send("chat-project", &send_payload(&q), AT)
            .is_err()
    );
    finish.wait();
    worker.join().unwrap();
    assert!(
        s.conversation_send("chat-project", &send_payload(&q), AT)
            .is_err()
    );
    assert_eq!(f.calls.load(Ordering::SeqCst), 1);
}

#[test]
fn disconnected_is_local_and_dispatch_rejects_non_user_actor() {
    let h = Harness::new();
    let f = Fixture {
        connected: false,
        ..Fixture::default()
    };
    let s = h.service(f.clone());
    let p = prepare(&s, "offline", "Can preview while disconnected.");
    assert!(
        s.conversation_send("chat-project", &send_payload(&p), AT)
            .is_err()
    );
    assert_eq!(f.calls.load(Ordering::SeqCst), 0);
    assert!(
        h.observer()
            .conversation_turns("chat-project", "chat-project-session")
            .unwrap()
            .is_empty()
    );
    let envelope=serde_json::from_value(json!({"protocol":"tom-assist/1.0","request_id":"r","idempotency_key":"i","method":"conversation.send","actor":{"type":"extension","instance_id":"e"},"project_id":"chat-project","payload":{"project_id":"chat-project","exchange_id":"offline","explicit_send":true,"confirmed_prompt_hash":p["prompt_hash"]},"sent_at":AT})).unwrap();
    assert!(s.dispatch_conversation(envelope).is_err());
}

#[test]
fn authoritative_chat_capture_has_source_project_confirmation_and_supersession_guards() {
    let h = Harness::new();
    let s = h.service(Fixture::default());
    let p = prepare(&s, "capture", "Check the beam.");
    s.conversation_send("chat-project", &send_payload(&p), AT)
        .unwrap();
    let good = capture_request("capture:assistant");
    let mut forged = good.clone();
    forged.confirmed = false;
    assert!(tom_assistd::chat_capture::capture_decision(&mut h.observer(), forged).is_err());
    let mut forged = good.clone();
    forged.project_id = "other-project".into();
    assert!(tom_assistd::chat_capture::capture_decision(&mut h.observer(), forged).is_err());
    let mut forged = good.clone();
    forged.source_turn_id = "capture:user".into();
    assert!(tom_assistd::chat_capture::capture_decision(&mut h.observer(), forged).is_err());
    tom_assistd::chat_capture::capture_decision(&mut h.observer(), good.clone()).unwrap();
    let state = h.observer().current_state("chat-project").unwrap();
    assert_eq!(state.objects.len(), 1);
    assert!(
        state.objects[0].workstream_id.is_none(),
        "confirmed decision is project-wide"
    );
    assert_eq!(state.objects[0].source_turn_ids, vec!["capture:assistant"]);
    let mut replacement = good;
    replacement.object_id = "replacement".into();
    replacement.idempotency_key = "supersede".into();
    replacement.old_id = Some("captured-decision".into());
    replacement.base_state_version = 1;
    assert!(
        tom_assistd::chat_capture::capture_decision(&mut h.observer(), replacement.clone())
            .is_err()
    );
    replacement.reason = Some("Owner revised scope".into());
    tom_assistd::chat_capture::capture_decision(&mut h.observer(), replacement).unwrap();
    let state = h.observer().current_state("chat-project").unwrap();
    assert_eq!(state.objects.len(), 2);
    assert_eq!(state.state_version, 2);
    assert_eq!(
        state
            .objects
            .iter()
            .find(|o| o.id == "captured-decision")
            .unwrap()
            .status,
        tom_assist_protocol::StateStatus::Superseded
    );
}

#[test]
fn visible_history_is_whole_message_bounded_and_session_local() {
    let h = Harness::new();
    let store = h.observer();
    for ordinal in 1..=30 {
        let text = format!("HISTORY-MARKER-{ordinal:02} {}🙂", "x".repeat(1200));
        store
            .record_turn(&tom_assist_persistence::TurnRecord {
                id: format!("history-{ordinal}"),
                session_id: "chat-project-session".into(),
                project_id: "chat-project".into(),
                workstream_id: "chat:chat-project-session".into(),
                role: if ordinal % 2 == 1 {
                    "user"
                } else {
                    "assistant"
                }
                .into(),
                ordinal,
                normalized_text: text.clone(),
                content_hash: tom_assist_protocol::canonical_sha256(&text).unwrap(),
                packet_digest: "history-fixture".into(),
                completeness: "complete".into(),
                captured_at: AT.into(),
                provider_timestamp: None,
            })
            .unwrap();
    }
    let f = Fixture::default();
    let s = h.service(f.clone());
    let p = prepare(&s, "bounded", "A new question.");
    let prompt = p["prompt"].as_str().unwrap();
    assert!(prompt.contains("HISTORY-MARKER-30"));
    assert!(!prompt.contains("HISTORY-MARKER-20"));
    assert!(!prompt.contains("HISTORY-MARKER-01"));
    let history: Vec<Value> = serde_json::from_str(prompt.split('\n').nth(1).unwrap()).unwrap();
    assert!(history.len() <= 12);
    assert!(
        history
            .iter()
            .map(|v| v["content"].as_str().unwrap().chars().count())
            .sum::<usize>()
            <= 12000
    );
    assert_eq!(f.calls.load(Ordering::SeqCst), 0);
}

#[test]
#[ignore = "Opt-in: TOM_ASSIST_LIVE_OAUTH=1 and explicit loopback TOM_ASSIST_OAUTH_RUNTIME_URL; one owner-quota exchange"]
fn live_oauth_one_disposable_exchange() {
    if std::env::var("TOM_ASSIST_LIVE_OAUTH").as_deref() != Ok("1") {
        eprintln!("SKIP: live OAuth not opted in");
        return;
    }
    let h = Harness::new();
    if h.gateway.1.provider_status().unwrap_or_default()["connected"] != true {
        eprintln!("SKIP: runtime OAuth disconnected/unconfigured");
        return;
    }
    let s = AssistService::with_gateway(Store::open(&h.database).unwrap(), h.gateway.1.clone());
    let p = prepare(
        &s,
        "live-once",
        "Reply with exactly: Ready. No tools, no explanation.",
    );
    let view = s
        .conversation_send("chat-project", &send_payload(&p), AT)
        .unwrap();
    assert!(
        view["exchanges"][0]["exchange"]["response_text"]
            .as_str()
            .is_some_and(|s| !s.is_empty())
    );
    assert!(view["exchanges"][0]["evaluation"].is_object());
    assert_eq!(view["exchanges"][0]["evaluation"]["result"], "PASS");
    assert!(
        view["exchanges"][0]["commit"].is_object(),
        "live acceptance must have a five-dynamics receipt"
    );
    let head = h.gateway.1.memory_diagnostics("chat-project", 0).unwrap();
    drop(s);
    let restarted =
        AssistService::with_gateway(Store::open(&h.database).unwrap(), h.gateway.1.clone());
    assert_eq!(
        restarted
            .conversation_get("chat-project", "chat-project-session")
            .unwrap(),
        view
    );
    // GET-only verification after restart. Never retry the provider on a failed assertion.
    assert_eq!(
        h.gateway.1.memory_diagnostics("chat-project", 0).unwrap(),
        head
    );
}
