# Complete project recovery (WP-20)

This is local alpha recovery/build verification, **NOT-A-GATE**. No upstream
checkout is modified. Recovery requires a compatible Tom Assist installation
with the reviewed runtime pin `e9fdef81c8a366ebbec07be9772189eea15cb2ac`, bundled
seed artifact and mechanics profile. Different runtime/seed/profile archives
fail closed; this is not a migration between physics versions.

## Export, backup and restore

In Settings → Complete project recovery, choose a new directory and select
**Export complete project archive**. **Create complete project backup** uses the
same verified format at a timestamped sibling directory. Neither overwrites an
existing archive. The local gateway must be running.

These archives include retained original conversations. They are **unencrypted,
not redacted diagnostic exports**. Keep the whole directory private. Its initial
root permissions are 0700. Checksums detect corruption, not a malicious author
who can rewrite both data and hashes; accept archives only from a trusted source.

To recover into another local store, enter the archive directory, select
**Verify recovery archive**, then **Import verified recovery archive**. Import
revalidates regardless of UI verification. Project identity is preserved, so an
existing project/runtime with that ID is refused, even if its name is different.
Other projects remain untouched. A cold restart reconstructs runtime projections
from the imported permanent library without applying experience again.

## Directory format

`manifest.json` identifies `tom-assist-recovery/2`, project/state digests, explicit
`raw_content: true`, the runtime manifest and SHA-256 of every other file.

- `ledger.json`: exact columns and all selected-project rows for projects,
  workstreams, sessions, turns, anchors, state objects/edges, evidence, events,
  candidates, context runs/manifests, evaluations, interventions, checkpoints,
  snapshots, audit events, sent bindings, runtime receipts and recovery receipts.
  WP-21 also includes chat conversation metadata and durable provider exchanges
  (approved prompts, drafts, response captures, review acceptance and send status).
  Earlier WP-20 archives without both new tables load with empty chat tables;
  arbitrary missing tables still fail closed. Interrupted sends never auto-resend.
- `state.json`, `events.jsonl`: canonical materialized state and replayable events.
- `transcript-policy.json`: retention profile and explicit full-content warning.
- `runtime/library.sqlite3`: SQLite online backup, including WAL-committed data;
  full original records/hash links, demotion history and the authoritative
  runtime head (exact engine/RGM bytes, commit-key results and settings).
- `runtime/creation_metadata.json`: original project runtime metadata.
- `runtime/checkpoints/<id>/`: every retained checkpoint's tree, RGM, commit
  state/settings and metadata, with their original digests.
- `runtime/runtime-manifest.json`: runtime pin, seed/profile hashes, head digest
  and runtime file inventory.

Transient WAL/SHM files and recoverable JSON projections are not copied. No other
project, application executable, credentials or upstream checkout is included.
The application recreates its schema/migration journal. Audit table integer row
IDs are allocated in the destination to avoid unrelated-project collisions;
event UUIDs, payloads, digests and all project/turn/packet identities are preserved.
The old low-level format-1 redacted ledger export is **not** a runtime recovery
archive and is not accepted by these controls.

## Consistency and interruption handling

Export holds the ledger writer lock while taking the per-project runtime lock
and a SQLite online backup. It validates native event replay, exact inventories,
content hashes, durable anchor twins, checkpoint digests and runtime compatibility.
Files and directories are synced before the staged archive is renamed into place.
Preview/recall/physics mutation is never part of export or verification.

Import copies the verified archive into private staging and verifies that frozen
copy again. Unknown schemas, missing/extra files, symlinks, traversal, bad content
hashes, incompatible pins and non-identical runtime restoration are refused.
The destination ledger transaction and a runtime import intent coordinate
publication. A durable ledger recovery receipt authorizes finalization.

- Before publication: the destination project is not visible.
- Failed publication/ledger write: relational rows roll back; only the newly
  staged runtime is quarantined under `recovery-staging/<token>.aborted`.
- Crash after publication but before ledger commit: project runtime access fails
  closed. Retry the same verified archive to resume; do not create that project.
- Crash after ledger commit but before finalization: the next project load checks
  the committed receipt and finalizes without a second import or experience step.

Unpublished staging and quarantined failure evidence are retained for inspection;
there is no automatic deletion or overwrite repair. A commit whose gateway reply
was lost may be present in the runtime key map before its ledger receipt exists.
Replaying the captured evaluation uses that original key/result, not another step.

This WP adds explicit complete per-project backups. The pre-existing migration
failure `.bak` remains a ledger-only incident copy, **not** a complete project
backup. Automatic update/migration backup scheduling is not added by this WP;
take a verified complete project backup before changing the installation.

## Repeatable packaged-app journey

This drives the real unsigned release `.app` through macOS accessibility controls,
native Tauri IPC, the release daemon and real pinned gateway. There is no injected
WebView driver or fake desktop backend. WP-21 replaces the Exchange diagnostic
with the real Chat surface: create a conversation, preview the full prompt,
explicitly Send, capture, evaluate and commit. The helper supplies an offline
loopback HTTP runtime fixture to the **production provider adapter**, overriding
any inherited owner URL. No actual OAuth/provider quota is consumed. Use only
the helper's disposable project. The separate ignored live test is described in
`OAUTH_CHAT.md`.

Build a separate artifact (choose a fresh output path each run):

```sh
scripts/package-macos/package-unsigned-app.sh --output-dir .tmp/wp21-package \
  --bundle-id local.tom.assist.wp21
cargo build --release -p tom-assistd
PYTHONDONTWRITEBYTECODE=1 .venv-gateway/bin/python \
  scripts/package-macos/journey-runtime.py \
  --app "$PWD/.tmp/wp21-package/Tom Assist.app" \
  --run-root /tmp/tom-assist-wp21-journey
```

The run root must not already exist. The helper controls only its three child PIDs
and isolated stores/sockets plus one disposable localhost HTTP fixture on a
system-assigned ephemeral port (never 18790); it never controls the GUI. In a
Codex Computer Use `node_repl` session, import the test and run each phase (separate
calls make progress and failures visible):

```js
var sky = (await import('@oai/sky')).sky;
var { PackagedJourney } = await import('/absolute/ToM_assist/scripts/package-macos/packaged-journey.mjs');
var journey = new PackagedJourney(sky, '/absolute/ToM_assist/.tmp/wp21-package/Tom Assist.app', '/private/tmp/tom-assist-wp21-journey');
await journey.capture();
await journey.commit();
await journey.backup();
await journey.restart();
await journey.recover();
await journey.finish();
```

Assertions cover create/capture, repeat-preview byte purity, real evaluation and
one commit, full Unicode originals, verified archive/backup, cold restart, import
into a fresh store, another cold restart, and idempotent evaluation replay. The
helper uses read-only observations for evidence; only explicit UI exchange and
recovery commands mutate project state. `journey-evidence.json`, AX transcripts,
screenshots and child logs remain in the run root. On failure inspect that state;
`await journey.control('stop')` stops only the owned children. Rerun from a fresh
root instead of reusing a partly completed journey.
