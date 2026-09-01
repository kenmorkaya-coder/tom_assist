# Validation harness scaffold

This directory is instrumentation only and emits no G-gate verdicts. WP-23's authored battery sources remain byte-preserved; Review 8 freezes them through the [WP-25 frozen overlay](batteries/wp23-draft/FROZEN_V1.md) for the explicitly authorized 33-case production pilot. The old fixture replay stays disabled; `production_runner.py` is the stop-rule-bound real-product runner.

`harness.py` replays stored JSONL histories through SUB-A…SUB-E, invokes the deterministic oracle as a separate stdin/stdout process, records packet/event traces, and emits an Appendix-C-format Markdown report plus the G15 reproducibility fields. `fixtures/toy_cases.jsonl` is a three-case plumbing smoke fixture, not a product-validation corpus.

The original term oracle checks context plumbing only. The new `typed-action-oracle/1` checks separately captured structured answers against pre-registered keys; it never chooses an answer or searches the context for a desired answer. Draft contract checks use only prewritten synthetic inputs, not live or experimental runs. See the draft README for limits, static checks and the owner-freeze prerequisites.

Run from the repository root:

```sh
python3 -m unittest discover -s validation/tests -v
python3 -m validation.harness --input validation/fixtures/toy_cases.jsonl --output-dir /tmp/tom-assist-harness-smoke
```

The frozen live pilot additionally requires the owner-authorized exact budget,
a running connected Tom Assist OAuth broker, and the pinned structural-preview
checkout (OAuth does not use that checkout):

```sh
TOM_ASSIST_WP25_LIVE=1 python3 -m validation.production_runner run \
  --output validation/runs/wp25-pilot-frozen-v1 \
  --temp /private/tmp/tom-assist-wp25-pilot-v1 \
  --driver target/debug/wp25-battery-driver \
  --oauth-broker-socket "$HOME/Library/Application Support/TomAssist/tom-assist-oauth.sock" \
  --tom-master ../tom_master --authorized-generations 165
```

The runner refuses existing output/temp paths and never resumes or resends an
unknown outcome. This command is evidence for the frozen pilot only, never a
G-gate verdict.
