use serde_json::Value;
use std::path::PathBuf;
use tom_assist_native_host::{
    chunk_response, error_frame, forward_to_assistd, read_native_frame, validate_envelope,
    validate_origin, write_native_frame,
};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let origin = std::env::args()
        .nth(1)
        .ok_or("Chrome origin argument is required")?;
    validate_origin(&origin)?;
    let socket = std::env::var_os("TOM_ASSISTD_SOCKET")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("tom-assistd.sock"));
    let mut input = std::io::stdin().lock();
    let mut output = std::io::stdout().lock();
    while let Some(value) = read_native_frame(&mut input)? {
        let correlation_id = value
            .get("request_id")
            .and_then(Value::as_str)
            .unwrap_or("unknown")
            .to_owned();
        let response = match validate_envelope(value) {
            Ok(envelope) => forward_to_assistd(&socket, &envelope)
                .unwrap_or_else(|error| error_frame(&correlation_id, &error)),
            Err(error) => error_frame(&correlation_id, &error),
        };
        for frame in chunk_response(&correlation_id, &response)? {
            write_native_frame(&mut output, &frame)?;
        }
    }
    Ok(())
}
