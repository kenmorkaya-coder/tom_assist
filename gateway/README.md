# Tom gateway

`tom_gateway.py` is the byte-frozen pilot-v4 gateway for the pinned read-only
`tom_master` runtime. Production development and packaged-journey launchers use
`evidence_gateway.py`, its versioned evidence-backed subclass. Both serve
HTTP-shaped JSON over a user-only Unix socket.

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

## Evidence-backed local structure worker

The versioned replacement for prose-to-load keyword counting is available in
`shadow` and `authoritative` modes. It keeps two signals separate:

1. local MiniLM tokenizes the complete passage into sentence-preferred windows
   of at most 192 tokens with a 32-token overlap, then produces one
   unit-normalized 384-dimensional vector per window. Retrieval compares every
   query window with every stored window; the passage centroid is telemetry,
   never the only retrieval signal;
2. local Gemma fills one `structural-candidate/1.0` native tool call per window.
   Window-local spans are rebound to original passage offsets. The same directed
   relation with overlapping equivalent evidence is merged deterministically,
   including punctuation-only quote-boundary differences. Candidates contain entities,
   directed orientations, cause-to-effect relations, modality, negation and
   typed signals, but no 17D values. Product code supplies only trusted envelope
   metadata and missing empty signal containers; it never supplies a semantic
   fact, relationship, quote, direction or confidence on Gemma's behalf.

The parser boundary is versioned independently. Version 1.1 omits product-owned
metadata and empty signal keys from the model's tool schema, projects away only
unknown presentation fields, and can deterministically reparse malformed Gemma-4
container syntax. Evidence may be rebound only to source text already quoted by
the model, the entity's own source-present label, or the uniquely nearest/anchored
occurrence. Missing semantic fields and ambiguous ties still fail closed. Worker
telemetry reports planned, attempted and successful window calls plus the exact
failed window; it contains no prompts, vectors or credentials.

The gateway validates every quoted span and endpoint. Product-owned,
deterministic code calculates all 17 channels. Static channels use the strongest
bounded-window evidence rather than sums, so adding neutral chunks cannot
inflate the load. Frequency, persistence,
burstiness, novelty, recurrence, volatility and decay use only previously
committed semantic/structural history. The complete candidate, MiniLM and Gemma
model revisions, vectors, channel evidence, compiler/chunking versions and digest are
committed to the permanent library.
Prepared analyses are checkpoint-bound and replayed byte-for-byte at commit;
stale or altered analyses fail closed.

MiniLM/Gemma run in `.venv-structure`, never in `.venv-gateway` and never in
the pinned runtime process. Both checkpoints must already be local; the worker
does not download models and refuses API-key environments. Setup is deliberately
separate because the pinned runtime and Gemma require incompatible MLX versions:

```sh
python3 -m venv .venv-structure
.venv-structure/bin/python -m pip install -r gateway/requirements-structure.txt

export TOM_ASSIST_STRUCTURE_MODE=shadow
export TOM_ASSIST_STRUCTURE_PYTHON="$PWD/.venv-structure/bin/python"
export TOM_ASSIST_GEMMA_PYTHON="$PWD/.venv-structure/bin/python"
export TOM_ASSIST_MINILM_MODEL="/absolute/local/MiniLM/snapshot"
export TOM_ASSIST_GEMMA_MODEL="/absolute/local/Gemma/snapshot"
# Optional; default 600 seconds, permitted range 30..1800.
export TOM_ASSIST_STRUCTURE_TIMEOUT_SECONDS=600
```

Modes are:

- `legacy` (default): current frozen behavior; no local model call.
- `shadow`: build, validate, persist and report the evidence analysis, but keep
  the existing drive/ranking behavior for comparison.
- `authoritative`: use the validated 17D signature for the canonical pinned
  commit application and the MiniLM plus directed-graph score for retrieval.

An unavailable worker, malformed tool call, non-matching quote, unknown entity
endpoint, stale checkpoint or altered load fails the prepare/commit. There is no
silent fallback from `shadow` or `authoritative` to keyword counting. The
language parser never imports or uses an emotion lexicon.

Create the isolated environment and install only the resolved runtime and test
imports:

```sh
python3 -m venv .venv-gateway
.venv-gateway/bin/python -m pip install -r gateway/requirements-dev.txt
```
