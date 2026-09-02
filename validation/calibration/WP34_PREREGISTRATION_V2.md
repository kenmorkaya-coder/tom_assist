# WP-34 GPT parser comparison pre-registration v2

Status: **DRAFT-PENDING-FRESH-OWNER-AUTHORIZATION — NOT A GATE**

This version retains WP-34 v1's 94-case corpus, expectations, scoring,
comparison rule, model, strict quote-only schema, local MiniLM revision,
duplicate caching, 97-call budget, serial execution, zero retries, evidence
policy and all safety boundaries exactly.

The sole request change is removal of `max_output_tokens` from the ChatGPT OAuth
Codex-proxy payload. Read-only inspection of the pinned provider client's own
OAuth implementation establishes that this proxy accepts Responses API
`text.format` but rejects `max_output_tokens` as an unsupported parameter. The
broker's existing 512 KiB parsed-output limit and 768 KiB response limit remain.

V1 stopped correctly after its first provider attempt returned
`PROVIDER_REQUEST_FAILED`; it made no retry and produced no candidate. Its 8 KiB
stop artifact remains at `validation/runs/wp34-gpt-parser-comparison-v1/`.
V2, if freshly authorized, uses a new output directory and 97 new explicit
provider generations. Nothing from the stopped request is reused or scored.

All other terms are incorporated unchanged from
`validation/calibration/WP34_PREREGISTRATION.md`. GPT remains candidate-only and
inactive; the Feeling Wheel remains disabled and unused; no tree step or
upstream write occurs; and no G-gate verdict can be issued.
