# Tom Assist Desktop

Tauri 2 + Preact desktop control application. The Rust shell opens the shared
SQLite event store in the per-user app-data directory; the UI invokes only
explicit commands for project, state, intervention, audit, and archive flows.

Settings → Commit memory exposes per-project front-row capacity (default 4096)
and learning from dismissed conflicts (default enabled). Demotion keeps the full
record in the permanent local library. Diagnostics displays memory counts and
paginated demotion events (ID, content hash and reason). These controls use the
local gateway Unix socket, default `tom_gateway.sock` beside the desktop database;
set `TOM_ASSIST_GATEWAY_SOCKET` to the daemon's gateway socket if it differs.
Use `TOM_ASSIST_APP_SUPPORT` to select the daemon's database directory as well;
the dev runner supplies both. Standalone launch preserves its legacy store by default.
No TCP listener is used. An unavailable gateway is reported, not replaced with
mock memory state. Accept/false-positive/dismiss actions share the daemon's
commit-aware intervention resolution path.

The ledger export does not include the gateway's runtime library. Back up the
whole gateway project directory separately for full runtime recovery.
