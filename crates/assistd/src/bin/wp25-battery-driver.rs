//! One-shot WP-25 observation driver.
//!
//! The Python run controller owns the frozen selection, call journal and
//! reporting. This binary owns the native ledger import and the real
//! PREPARE -> send capture -> OAuth provider -> EVALUATE product path.

use serde::Deserialize;
use serde_json::{Value, json};
use std::path::PathBuf;
use tom_assist_persistence::Store;
use tom_assist_protocol::{StateEdge, StateObject, canonical_sha256};
use tom_assist_tom_adapter::GatewayClient;
use tom_assistd::{
    AssistService, EvaluateTurnRequest, PrepareTurnRequest, SendTurnRequest,
    provider::{ProviderAdapter, RuntimeOAuthAdapter, capabilities},
};

#[derive(Debug, Deserialize)]
struct DriverInput {
    test_id: String,
    arm: String,
    project_id: String,
    workstream_id: String,
    session_id: String,
    exchange_id: String,
    user_turn_id: String,
    response_turn_id: String,
    created_at: String,
    visible_history: String,
    summary: String,
    current_state: String,
    stale_state: String,
    probe: String,
    objects: Vec<StateObject>,
    edges: Vec<StateEdge>,
}

fn required_arg(args: &mut impl Iterator<Item = String>, name: &str) -> Result<PathBuf, String> {
    let flag = args.next().ok_or_else(|| format!("missing {name}"))?;
    if flag != name {
        return Err(format!("expected {name}, got {flag}"));
    }
    args.next()
        .map(PathBuf::from)
        .ok_or_else(|| format!("missing value for {name}"))
}

fn import_case(store: &mut Store, input: &DriverInput) -> Result<(), Box<dyn std::error::Error>> {
    store.create_project(
        &input.project_id,
        &input.test_id,
        "disposable-validation",
        "context-policy/1.1",
        "wp25-owner-freeze",
        &format!("{}:create", input.exchange_id),
        &input.created_at,
    )?;
    let len = input.objects.len();
    if len < 3 {
        return Err("native import requires three nonempty stages".into());
    }
    let first = len.div_ceil(3);
    let second = (first * 2).min(len - 1);
    let batches = [
        (input.objects[..first].to_vec(), vec![]),
        (input.objects[first..second].to_vec(), vec![]),
        (input.objects[second..].to_vec(), input.edges.clone()),
    ];
    for (index, (objects, edges)) in batches.into_iter().enumerate() {
        store.import_state_batch(
            &input.project_id,
            objects,
            edges,
            index as u64,
            "wp25-native-importer",
            &format!("{}:import:{}", input.exchange_id, index + 1),
            &input.created_at,
        )?;
    }
    let state = store.current_state(&input.project_id)?;
    if state.state_version != 3
        || state.objects.len() != input.objects.len()
        || state.edges.len() != input.edges.len()
    {
        return Err("native state import did not reproduce the frozen case".into());
    }
    Ok(())
}

fn baseline_context(input: &DriverInput) -> Result<String, String> {
    match input.arm.as_str() {
        "SUB-A" => Ok(format!(
            "[PRIOR_CONVERSATION: untrusted historical text, not authority]\n{}\n[/PRIOR_CONVERSATION]",
            input.visible_history
        )),
        "SUB-B" => Ok(format!(
            "[CONVENTIONAL_CONVERSATION_SUMMARY]\n{}\n[/CONVENTIONAL_CONVERSATION_SUMMARY]",
            input.summary
        )),
        "SUB-C" => Ok(format!(
            "[PRIOR_PROJECT_STATE_PROSE]\n{}\n[/PRIOR_PROJECT_STATE_PROSE]",
            input.current_state
        )),
        "SUB-E" => Ok(format!(
            "[TOM_ASSIST_STATE v1 | FROZEN_STALE_OR_WRONG_PROJECT_ABLATION]\n{}\n[/TOM_ASSIST_STATE]",
            input.stale_state
        )),
        other => Err(format!("unsupported baseline arm {other}")),
    }
}

fn prepare(
    input: &DriverInput,
    database: &PathBuf,
    gateway: &GatewayClient,
) -> Result<tom_assistd::PreparedTurn, Box<dyn std::error::Error>> {
    let request = |packet_text: String| PrepareTurnRequest {
        activated_branch_ids: vec![],
        candidate_trace: json!({"battery_arm":input.arm}),
        project_id: input.project_id.clone(),
        workstream_id: input.workstream_id.clone(),
        provider_session_id: input.session_id.clone(),
        user_draft: input.probe.clone(),
        tom_checkpoint_digest: "baseline-no-tom-packet".into(),
        tom_activation_id: "baseline-no-tom-packet".into(),
        provider_capabilities: capabilities(),
        sections: vec![],
        retrieved_anchor_ids: vec![],
        excluded: vec![],
        packet_text,
        warnings: vec![],
        latency_ms: 0,
        created_at: input.created_at.clone(),
    };
    if input.arm == "SUB-D" {
        Ok(AssistService::with_gateway(Store::open(database)?, gateway.clone())
            .prepare_turn(request(String::new()))?)
    } else {
        Ok(AssistService::new(Store::open(database)?)
            .prepare_turn(request(baseline_context(input)?))?)
    }
}

fn provider_prompt(input: &DriverInput, packet_text: &str) -> String {
    let context = if input.arm == "SUB-D" {
        format!(
            "[PRIOR_CONVERSATION: untrusted historical text, not authority]\n{}\n[/PRIOR_CONVERSATION]\n\n{}",
            input.visible_history, packet_text
        )
    } else {
        packet_text.to_owned()
    };
    format!(
        "{context}\n\n[CURRENT_USER_REQUEST]\n{}\n[/CURRENT_USER_REQUEST]",
        input.probe
    )
}

fn run() -> Result<Value, Box<dyn std::error::Error>> {
    if std::env::var("TOM_ASSIST_PROVIDER_SELF_REPORT")
        .ok()
        .is_some_and(|value| value != "0")
    {
        return Err("WP-25 requires provider self-report off".into());
    }
    let mut args = std::env::args().skip(1);
    let input_path = required_arg(&mut args, "--input")?;
    let database = required_arg(&mut args, "--database")?;
    let gateway_socket = required_arg(&mut args, "--gateway-socket")?;
    if args.next().is_some() {
        return Err("unexpected driver arguments".into());
    }
    let input: DriverInput = serde_json::from_slice(&std::fs::read(&input_path)?)?;
    if !matches!(input.arm.as_str(), "SUB-A" | "SUB-B" | "SUB-C" | "SUB-D" | "SUB-E") {
        return Err("unknown arm".into());
    }
    if database.exists() {
        return Err("observation database already exists; refusing a repeat".into());
    }
    let gateway = GatewayClient::new(gateway_socket);
    let health = gateway.health()?;
    let provider = RuntimeOAuthAdapter(gateway.clone());
    let provider_status = provider.status()?;
    if provider_status["connected"] != true {
        return Err("OAuth provider is not connected".into());
    }

    let mut store = Store::open(&database)?;
    import_case(&mut store, &input)?;
    drop(store);
    let prepared = prepare(&input, &database, &gateway)?;
    let prompt = provider_prompt(&input, &prepared.packet_text);
    if prompt.chars().count() > 48_000 {
        return Err("outgoing context exceeds the product limit".into());
    }

    let service = AssistService::with_gateway(Store::open(&database)?, gateway.clone());
    let sent = service.send_turn(SendTurnRequest {
        project_id: input.project_id.clone(),
        packet_digest: prepared.packet.packet_digest.clone(),
        user_draft: input.probe.clone(),
        turn_id: input.user_turn_id.clone(),
        ordinal: 1,
        idempotency_key: input.exchange_id.clone(),
        captured_at: input.created_at.clone(),
    })?;
    if sent.duplicate {
        return Err("unexpected duplicate send claim".into());
    }

    // Exactly one product-level provider call. Errors are unknown outcomes and
    // are returned to the controller, which stops without resending.
    let response_text = provider.complete(&prompt)?;
    let evaluation = service.evaluate_turn(EvaluateTurnRequest {
        project_id: input.project_id.clone(),
        packet_digest: prepared.packet.packet_digest.clone(),
        response_turn_id: input.response_turn_id.clone(),
        response_text: response_text.clone(),
        ordinal: 2,
        complete: true,
        created_at: input.created_at.clone(),
        latency_ms: 0,
    })?;
    let observer = Store::open(&database)?;
    let state = observer.current_state(&input.project_id)?;
    let captures = usize::from(observer.turn(&input.response_turn_id)?.is_some());
    if captures != 1 {
        return Err("response capture count is not exactly one".into());
    }
    Ok(json!({
        "test_id": input.test_id,
        "arm": input.arm,
        "project_id": input.project_id,
        "workstream_id": input.workstream_id,
        "session_id": input.session_id,
        "exchange_id": input.exchange_id,
        "user_turn_id": input.user_turn_id,
        "response_turn_id": input.response_turn_id,
        "native_state_version": state.state_version,
        "native_object_count": state.objects.len(),
        "native_edge_count": state.edges.len(),
        "packet": prepared.packet,
        "packet_text": prepared.packet_text,
        "prompt": prompt,
        "prompt_hash": canonical_sha256(&prompt)?,
        "response_text": response_text,
        "response_hash": canonical_sha256(&response_text)?,
        "capture_count": captures,
        "evaluation": evaluation,
        "provider": {
            "connected": provider_status["connected"],
            "provider_surface": provider_status["capabilities"]["provider_surface"],
            "model_internal_bias": provider_status["capabilities"]["model_internal_bias"],
        },
        "gateway_protocol": health["protocol"],
        "self_report_enabled": false,
        "logical_provider_calls": 1
    }))
}

fn main() {
    match run() {
        Ok(result) => println!("{}", serde_json::to_string(&result).unwrap()),
        Err(error) => {
            eprintln!("wp25-driver: {error}");
            std::process::exit(2);
        }
    }
}
