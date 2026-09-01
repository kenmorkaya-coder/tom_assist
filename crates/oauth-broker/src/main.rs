use std::path::PathBuf;
use std::sync::Arc;
use tom_assist_oauth::{Broker, BrokerClient, BrokerConfig, serve};

fn main() {
    if let Err(code) = run() {
        eprintln!("{code}");
        std::process::exit(2);
    }
}

fn run() -> std::result::Result<(), &'static str> {
    let mut args = std::env::args().skip(1);
    let command = args.next().ok_or("USAGE_ERROR")?;
    if args.next().as_deref() != Some("--socket") {
        return Err("USAGE_ERROR");
    }
    let socket = PathBuf::from(args.next().ok_or("USAGE_ERROR")?);
    if args.next().is_some() {
        return Err("USAGE_ERROR");
    }
    match command.as_str() {
        "serve" => {
            let broker = Broker::new(BrokerConfig::default()).map_err(|error| error.code())?;
            serve(&socket, Arc::new(broker)).map_err(|error| error.code())
        }
        "status" => print_json(BrokerClient::new(socket).status()),
        "login" => print_json(BrokerClient::new(socket).login()),
        "logout" => print_json(BrokerClient::new(socket).logout()),
        _ => Err("USAGE_ERROR"),
    }
}

fn print_json<T: serde::Serialize>(
    value: tom_assist_oauth::Result<T>,
) -> std::result::Result<(), &'static str> {
    let value = value.map_err(|error| error.code())?;
    println!(
        "{}",
        serde_json::to_string(&value).map_err(|_| "BROKER_RESPONSE_INVALID")?
    );
    Ok(())
}
