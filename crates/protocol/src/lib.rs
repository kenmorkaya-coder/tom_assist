//! Versioned wire and persistence contracts for Tom Assist.

mod digest;
mod model;

pub use digest::{PacketDigestInput, canonical_json, canonical_sha256, packet_digest};
pub use model::*;

pub const PROTOCOL_VERSION: &str = "tom-assist/1.0";
