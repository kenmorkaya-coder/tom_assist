use serde::Serialize;
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};

#[derive(Debug, Clone, Serialize)]
pub struct PacketDigestInput<'a> {
    pub project_id: &'a str,
    pub workstream_id: &'a str,
    pub state_version: u64,
    pub tom_checkpoint_digest: &'a str,
    pub admitted_item_ids: Vec<&'a str>,
    pub activated_branch_ids: Vec<&'a str>,
    pub renderer_version: &'a str,
    pub policy_version: &'a str,
    pub user_draft_hash: &'a str,
}

fn normalize(value: Value) -> Value {
    match value {
        Value::Object(object) => {
            let mut entries: Vec<_> = object.into_iter().collect();
            entries.sort_by(|(left, _), (right, _)| left.as_bytes().cmp(right.as_bytes()));
            let mut normalized = Map::new();
            for (key, value) in entries {
                normalized.insert(key, normalize(value));
            }
            Value::Object(normalized)
        }
        Value::Array(values) => Value::Array(values.into_iter().map(normalize).collect()),
        other => other,
    }
}

/// Contract D10 canonical JSON: UTF-8, byte-sorted object keys, compact encoding,
/// shortest round-trip JSON numbers, and array order preserved.
pub fn canonical_json<T: Serialize>(value: &T) -> Result<Vec<u8>, serde_json::Error> {
    serde_json::to_vec(&normalize(serde_json::to_value(value)?))
}

pub fn canonical_sha256<T: Serialize>(value: &T) -> Result<String, serde_json::Error> {
    let bytes = canonical_json(value)?;
    Ok(format!("sha256:{}", hex::encode(Sha256::digest(bytes))))
}

pub fn packet_digest(mut input: PacketDigestInput<'_>) -> Result<String, serde_json::Error> {
    input.activated_branch_ids.sort_unstable();
    input.activated_branch_ids.dedup();
    input
        .admitted_item_ids
        .sort_unstable_by(|a, b| a.as_bytes().cmp(b.as_bytes()));
    input.admitted_item_ids.dedup();
    canonical_sha256(&input)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn canonicalization_sorts_recursively_and_preserves_arrays() {
        let value = json!({"z": {"b": 2, "a": 1}, "a": [3, 2, 1]});
        assert_eq!(
            String::from_utf8(canonical_json(&value).unwrap()).unwrap(),
            r#"{"a":[3,2,1],"z":{"a":1,"b":2}}"#
        );
    }

    #[test]
    fn packet_admitted_ids_are_order_independent() {
        let base = |ids| PacketDigestInput {
            project_id: "p",
            workstream_id: "w",
            state_version: 7,
            tom_checkpoint_digest: "sha256:checkpoint",
            admitted_item_ids: ids,
            activated_branch_ids: vec!["branch-1"],
            renderer_version: "authoritative-state/1.0",
            policy_version: "context-policy/1.0",
            user_draft_hash: "sha256:draft",
        };
        assert_eq!(
            packet_digest(base(vec!["b", "a"])).unwrap(),
            packet_digest(base(vec!["a", "b"])).unwrap()
        );
        let mut different_cohort = base(vec!["a", "b"]);
        different_cohort.activated_branch_ids = vec!["branch-2"];
        assert_ne!(
            packet_digest(base(vec!["a", "b"])).unwrap(),
            packet_digest(different_cohort).unwrap()
        );
    }
}
