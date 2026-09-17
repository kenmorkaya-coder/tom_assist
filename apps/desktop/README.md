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
OAuth response capture, governance review and confirmed decision capture or
supersession. **Connect OAuth** runs the Tom Assist broker's browser PKCE flow;
credentials stay in Tom Assist's macOS Keychain entry and never enter the ledger
or archives. The packaged desktop owns the broker sidecar; the developer runner
passes its Unix socket as `TOM_ASSIST_OAUTH_BROKER_SOCKET`. See
`docs/OAUTH_CHAT.md` for setup, capabilities, recovery and the ignored live test.

The opt-in **Answer from learned documents** action uses `conversation.native_answer`.
It is available only in the project named by the gateway's operator-configured
`TOM_ASSIST_NATIVE_MEMORY_PROFILE`. This path runs MiniLM access, native learned
memory return, evidence selection and local Gemma wording sequentially. Complete
signed branch fields are compared at their original positions. The tree, its
selector and its learning state remain unchanged. Answers retain source IDs,
clause numbers and pages; unsupported requests receive a refusal.

This initial integration is limited to the six frozen insurance facts. Final
wording is an exact copy of approved evidence (apart from whitespace), checked
before display. A narrowly scoped yes/no party check may precede it, verified
against the cited obligation and the party named in the question. It does not yet produce free-form summaries or save these local
answers to conversation history. It does not migrate existing document indexes.

For a registered isolated project, export the existing frozen collection with:
`python3 validation/calibration/stream1_native_learned_recall_runner.py --export-native-memory-profile /tmp/tom-native-memory-profile.json PROJECT_ID`
from the repository root, then start the gateway with that absolute profile path
in `TOM_ASSIST_NATIVE_MEMORY_PROFILE`. The exporter verifies source provenance and
retains a small exact package snapshot beside the profile if the owner checkout
has changed; it never edits the native repository. Passport must remain mounted.
The opt-in held-out service test is
`native_memory_frozen_heldout_answers_through_service` in the designated service
test suite. It preserves first-pass results and refuses to overwrite them.

The 16 September 2026 first-pass battery passed **17/20**, not an acceptance gate.
All 60 candidate returns matched the complete frozen native fields. H08 lost the
question's repayment direction and falsely reported support; H09 refused an
answerable yes/no question; H20's top-three access candidates omitted one needed
memory. The real native window displayed the verified premium answer and its
expandable clause/page citation. This feature remains an opt-in six-fact
integration, not a general document-answering release. Observed answers took
70–87 seconds. Full records and the unchanged frozen fixture are under
`validation/runs/stream1-native-learned-recall.json` → `native_memory_end_to_end`.

The follow-up repair separates a proposition being questioned from conditions
that the evidence must satisfy, and preserves explicit repayment directions in
active/passive wording. Its limited question grammar refuses recognized negated
propositions it cannot interpret; it is not a general contract reasoner.
Compound questions are now split **before** access. Each part uses the same
MiniLM top-three method; the deduplicated union goes through native recall.
Evidence selection uses the same frozen rules and the final text retains each
approved clause in full. Planning, embedding, tree recall and final language
workers run sequentially.

The bounded follow-up is reproducible with:
`python3 validation/calibration/stream1_native_learned_recall_runner.py --verify-native-memory-repairs /tmp/tom-native-memory-profile.json`
It resumes only unfinished checks, refuses changes to the frozen runtime, and
preserves the original 17/20 result. Its three previous failures and six newly
frozen questions are recorded separately under `native_memory_repairs`.

Follow-up completed: **3/3 previous failures repaired; 6/6 newly frozen checks
passed**, including the intended partial answer when the requested bank-account
detail is absent. All **30/30** native returns exactly matched full signed
3,217×32×32 fields; tree state remained unchanged, with zero training/root
assembly calls. The 19 focused Python checks passed. Two resource-blocked
attempts remain recorded separately; the identical frozen runtime was resumed
after the competing process finished. Completed answers took 63–100 seconds.
This remains a six-fact integration, not proof of general document recall.

The real isolated desktop action also completed: the combined question displays
both complete source clauses, 23.2 and 23.3 (page 55), as a supported answer.

The next frozen check enlarges the collection to twelve clauses from the same
contract. Its fixture, learning receipts, source extractions, full-field identity
checks and question results are in the existing report under
`native_memory_larger_collection`. The original six-fact collection is preserved.
The unchanged checker cannot represent disclosure or notification duties; those
questions are counted as failures if it refuses them, not as successful refusals
of nonexistent information. Large artifacts remain on Passport under
`native_learned_recall/larger_collection12/`. No runtime scoring, prompt or
threshold was changed for this enlargement.

The enlarged run passed **7/12** questions. There were three address-access
misses, one false approval of the opposite repayment direction, and one refusal
of a correctly recalled disclosure clause. All **39/39** selected native returns
matched the complete saved fields. The false approval was also reproduced in the
real isolated desktop window. This result does **not** qualify the feature for
broader use. Full failures and single-variable diagnostic replays are retained in
`native_memory_larger_collection`; original results remain unchanged.

### Experimental local RGM document path — 17 September 2026

With `TOM_ASSIST_RGM_DOCUMENT_ANSWERS=1`, Memory exposes an explicit local-file
import for PDF, TXT and Markdown. It uses the RGM copy in this repository,
stores full source text and lossless chunks in the selected project's library,
and prepares local MiniLM vectors. Chat's **Answer from project documents**
then runs local RGM retrieval and Gemma evidence reading. Expand a source below
the answer to inspect its original passage and highlighted quotation.

This mode does not initialize or use a ToM tree, send to the connected cloud
provider, or save these experimental answers in conversation history. Other
Chat actions retain their existing behavior. Keep it opt-in. The earlier
reversed-party block remains recorded as a failure; its bounded repair now says
**No** and displays the complete cited clause only when that one clause proves
the exact opposite party direction. See the gateway README for the guard's
limits, runtime settings and bounds.

The actual isolated Tauri window has now imported the full M12 agreement into
248 RGM passages and displayed its notice answer with an expandable source.
The missing policy number was refused. The reversed-party failure was reproduced
visibly, then the repaired result was rerun in the same window and its clause
23.5 citation opened. Results are recorded under `rgm_desktop_ui_integration`
and `rgm_desktop_repayment_direction_repair` in the existing learned-recall
report; that historical filename does not imply tree recall was used here.
