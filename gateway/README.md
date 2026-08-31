# Tom gateway

`tom_gateway.py` is Tom Assist's narrow Python sidecar for the pinned read-only
`tom_master` runtime. It serves HTTP-shaped JSON over a user-only Unix socket.

Preview purity is structural: preview uses the pinned upstream `preview_readout`
pure projection/selection/resonance exports, product RRF glue, a local mirror of
the applicable structural trigger, and RGM's `VectorStore.query`. Importing the
pinned `interface` package would also initialize unrelated chat/provider code,
so the 20-line upstream trigger wrapper is not imported.
The upstream `retrieve_ltm_with_stm_triggers` wrapper is intentionally not used
because the pinned implementation contains a mutating RGM read.

Sent, captured exchanges experience five ordered phases: step, RGM write,
response teaching, sent-packet usage rotation, then front-row reinforcement,
decay and pruning. Drafts never enter this path. The existing pure projection
supplies the teacher's required shape; this does not add a prose-to-shape model.

Each project's `tom/library.sqlite3` permanently retains full content before
front-row admission and atomically journals engine/RGM snapshots, idempotency
and demotions. The JSON runtime files are recoverable projections of that head.
Back up the project directory, including this database; the desktop's ledger
export is not a runtime-library backup. Do not delete the library to reset a tree.
Checkpoint restore resets the working tree/front row and commit keys/settings,
but intentionally keeps permanent content and demotion history.

`POST /project/settings` accepts `project_id` and `settings` (empty object reads
current settings). Defaults: `front_row_capacity=4096`, `teach_on_conflict=true`.
Capacity is an integer from 1 to 1,000,000 and takes effect on the next commit.
Current-packet anchors are protected from capacity eviction for that commit;
other lowest-strength anchors are demoted with stable ID tie-breaking.
`POST /memory/diagnostics` returns counts and up to 200 demotions, including
record ID, content hash, reason, commit key and tick. Pass its `next_event_id` as
`after_event_id` to retrieve subsequent pages. Demotion never removes the library
twin. Readmission occurs on a later committed packet referencing that record.

CONFLICT exchanges wait for intervention resolution. Dismissal suppresses only
teaching when `teach_on_conflict=false`; the other dynamics still run once.
Capture/evaluation survive runtime failures and report `runtime_commit_pending`;
replay the same evaluation or resolution to retry with the same sent-turn key.
There is no background retry and previews never retry commits. A packet may bind
only one sent turn; ambiguous reuse is rejected. Pre-WP-17 truncated anchors
without their original full content fail the library-first migration closed;
legacy checkpoints lacking commit-key/settings snapshots are not silently restored.

Create the isolated environment and install only the resolved runtime and test
imports:

```sh
python3 -m venv .venv-gateway
.venv-gateway/bin/python -m pip install -r gateway/requirements-dev.txt
```
