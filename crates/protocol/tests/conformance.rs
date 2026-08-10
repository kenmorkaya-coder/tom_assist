use serde::{Serialize, de::DeserializeOwned};
use serde_json::Value;
use tom_assist_protocol::{
    ContinuityPacket, Envelope, Intervention, ProtocolError, ProviderCapabilities, StateEdge,
    StateMutationCandidate, StateObject, TomCapabilities,
};

fn round_trip<T>(value: &Value)
where
    T: DeserializeOwned + Serialize,
{
    let decoded: T = serde_json::from_value(value.clone()).expect("fixture decodes");
    let encoded = serde_json::to_value(decoded).expect("type encodes");
    assert_eq!(&encoded, value);
}

#[test]
fn shared_examples_round_trip_through_handwritten_rust_types() {
    let fixture: Value = serde_json::from_str(include_str!(
        "../../../tests/fixtures/protocol/examples.json"
    ))
    .unwrap();
    round_trip::<Envelope>(&fixture["envelope"]);
    round_trip::<ProviderCapabilities>(&fixture["provider_capabilities"]);
    round_trip::<TomCapabilities>(&fixture["tom_capabilities"]);
    round_trip::<StateObject>(&fixture["state_object"]);
    round_trip::<StateEdge>(&fixture["state_edge"]);
    round_trip::<ContinuityPacket>(&fixture["continuity_packet"]);
    round_trip::<StateMutationCandidate>(&fixture["state_mutation_candidate"]);
    round_trip::<Intervention>(&fixture["intervention"]);
    round_trip::<ProtocolError>(&fixture["error"]);
}

#[test]
fn provider_candidates_remain_candidates_after_round_trip() {
    let fixture: Value = serde_json::from_str(include_str!(
        "../../../tests/fixtures/protocol/examples.json"
    ))
    .unwrap();
    let candidate: StateMutationCandidate =
        serde_json::from_value(fixture["state_mutation_candidate"].clone()).unwrap();
    assert!(candidate.tom_check.requires_user_confirmation);
    assert_eq!(candidate.object["status"], "proposed");
}
