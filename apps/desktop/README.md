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
Product IPC uses Unix sockets. An unavailable gateway is reported, not replaced with
mock memory state. Accept/false-positive/dismiss actions share the daemon's
commit-aware intervention resolution path.

Settings complete export/import/backup includes the permanent runtime library,
provider sessions, captured conversations and exactly-once receipts. See
`docs/PROJECT_RECOVERY.md`; archives contain unencrypted full text.

Chat provides project conversations, visible packet preparation, explicit Send,
runtime OAuth response capture, governance review and confirmed decision capture
or supersession. Credentials stay in the already connected owner runtime. Set
`TOM_ASSIST_OAUTH_RUNTIME_URL` only on the gateway to that runtime's existing
loopback HTTP origin; there is no automatic send or login. See
`docs/OAUTH_CHAT.md` for setup, capabilities, recovery and the ignored live test.
