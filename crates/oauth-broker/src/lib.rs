//! Tom Assist-owned OAuth broker.
//!
//! This crate is the credential boundary for the desktop product. Secrets are
//! held in the platform credential store and in this process only. They are
//! never returned by the broker protocol, written to the ledger, archived, or
//! exposed to the webview.

mod broker;
mod error;
mod model;
mod server;
mod store;

pub use broker::{Broker, BrokerConfig};
pub use error::{BrokerError, Result};
pub use model::{BrokerStatus, ProviderReply};
pub use server::{BrokerClient, serve};
pub use store::KeychainStore;

pub const BROKER_PROTOCOL_VERSION: &str = "tom-assist-oauth/1.0";
pub const DEFAULT_CLIENT_ID: &str = "app_EMoamEEZ73f0CkXaXp7hrann";
pub const DEFAULT_MODEL: &str = "gpt-5.5";
pub const CALLBACK_PORT: u16 = 1455;
