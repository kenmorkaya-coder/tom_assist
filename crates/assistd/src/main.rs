use std::path::PathBuf;
use std::sync::Arc;
use tom_assist_persistence::Store;
use tom_assist_tom_adapter::GatewayClient;
use tom_assistd::{AssistService, serve_unix};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args_os().skip(1);
    let socket = args
        .next()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("tom-assistd.sock"));
    let database = args
        .next()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("tom-assist.sqlite3"));
    let gateway_socket = args
        .next()
        .map(PathBuf::from)
        .unwrap_or_else(|| socket.with_file_name("tom_gateway.sock"));
    let service = Arc::new(AssistService::with_governance_verifier(
        Store::open(database)?,
        GatewayClient::new(gateway_socket),
    ));
    serve_unix(&socket, service)?;
    Ok(())
}
