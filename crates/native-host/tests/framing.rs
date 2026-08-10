use serde_json::json;
use sha2::{Digest, Sha256};
use tom_assist_native_host::{
    ALLOWED_ORIGIN, CHUNK_THRESHOLD_BYTES, EXTENSION_ID, HostError, chunk_response,
    read_native_frame, validate_envelope, validate_origin, write_native_frame,
};

#[test]
fn manifest_public_key_derives_the_allowlisted_extension_id() {
    let manifest: serde_json::Value =
        serde_json::from_str(include_str!("../../../apps/extension/manifest.json")).unwrap();
    let public_key = base64::Engine::decode(
        &base64::engine::general_purpose::STANDARD,
        manifest["key"].as_str().unwrap(),
    )
    .unwrap();
    let digest = Sha256::digest(public_key);
    let id: String = digest[..16]
        .iter()
        .flat_map(|byte| [byte >> 4, byte & 0x0f])
        .map(|nibble| char::from(b'a' + nibble))
        .collect();
    assert_eq!(id, EXTENSION_ID);
    let host_manifest: serde_json::Value =
        serde_json::from_str(include_str!("../tom.assist.native.json")).unwrap();
    assert_eq!(host_manifest["allowed_origins"][0], ALLOWED_ORIGIN);
}

#[test]
fn native_framing_round_trips_and_validates_schema() {
    let envelope = json!({
        "protocol":"tom-assist/1.0",
        "request_id":"00000000-0000-4000-8000-000000000001",
        "idempotency_key":"00000000-0000-4000-8000-000000000002",
        "method":"capabilities.get",
        "actor":{"type":"extension","instance_id":"00000000-0000-4000-8000-000000000003"},
        "payload":{},
        "sent_at":"2026-08-10T00:00:00Z"
    });
    let mut bytes = Vec::new();
    write_native_frame(&mut bytes, &envelope).unwrap();
    let decoded = read_native_frame(&mut bytes.as_slice()).unwrap().unwrap();
    assert_eq!(
        validate_envelope(decoded).unwrap().request_id,
        "00000000-0000-4000-8000-000000000001"
    );
}

#[test]
fn oversized_payload_chunks_and_reassembles_exactly() {
    let value = json!({"payload":"x".repeat(CHUNK_THRESHOLD_BYTES + 37)});
    let frames = chunk_response("correlation-large", &value).unwrap();
    assert!(frames.len() > 1);
    let mut joined = Vec::new();
    for (index, frame) in frames.iter().enumerate() {
        assert_eq!(frame["correlation_id"], "correlation-large");
        assert_eq!(frame["seq"], index);
        assert_eq!(frame["total"], frames.len());
        let bytes = base64::Engine::decode(
            &base64::engine::general_purpose::STANDARD,
            frame["chunk_b64"].as_str().unwrap(),
        )
        .unwrap();
        joined.extend(bytes);
        assert!(serde_json::to_vec(frame).unwrap().len() <= CHUNK_THRESHOLD_BYTES);
    }
    assert_eq!(
        serde_json::from_slice::<serde_json::Value>(&joined).unwrap(),
        value
    );
}

#[test]
fn forged_extension_origin_and_protocol_are_rejected() {
    validate_origin(ALLOWED_ORIGIN).unwrap();
    assert!(matches!(
        validate_origin("chrome-extension://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/"),
        Err(HostError::ForbiddenOrigin)
    ));
    let forged = json!({
        "protocol":"tom-assist/999",
        "request_id":"00000000-0000-4000-8000-000000000004",
        "idempotency_key":"00000000-0000-4000-8000-000000000005",
        "method":"capabilities.get",
        "actor":{"type":"extension","instance_id":"00000000-0000-4000-8000-000000000006"},
        "payload":{},
        "sent_at":"2026-08-10T00:00:00Z"
    });
    assert!(matches!(
        validate_envelope(forged),
        Err(HostError::ProtocolMismatch)
    ));
}
