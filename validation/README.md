# Validation harness scaffold

This directory is instrumentation only and emits no gate verdicts. WP-23 adds [draft battery artifacts](batteries/wp23-draft/README.md), all **DRAFT-PENDING-OWNER-FREEZE**; they are not frozen validation batteries and cannot be replayed by this scaffold.

`harness.py` replays stored JSONL histories through SUB-A…SUB-E, invokes the deterministic oracle as a separate stdin/stdout process, records packet/event traces, and emits an Appendix-C-format Markdown report plus the G15 reproducibility fields. `fixtures/toy_cases.jsonl` is a three-case plumbing smoke fixture, not a product-validation corpus.

The original term oracle checks context plumbing only. The new `typed-action-oracle/1` checks separately captured structured answers against pre-registered keys; it never chooses an answer or searches the context for a desired answer. Draft contract checks use only prewritten synthetic inputs, not live or experimental runs. See the draft README for limits, static checks and the owner-freeze prerequisites.

Run from the repository root:

```sh
python3 -m unittest discover -s validation/tests -v
python3 -m validation.harness --input validation/fixtures/toy_cases.jsonl --output-dir /tmp/tom-assist-harness-smoke
```
