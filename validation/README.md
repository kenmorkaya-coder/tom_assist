# Validation harness scaffold

This directory is instrumentation only. It authors zero G-gate batteries and emits no gate verdicts.

`harness.py` replays stored JSONL histories through SUB-A…SUB-E, invokes the deterministic oracle as a separate stdin/stdout process, records packet/event traces, and emits an Appendix-C-format Markdown report plus the G15 reproducibility fields. `fixtures/toy_cases.jsonl` is a three-case plumbing smoke fixture, not a product-validation corpus.

Run from the repository root:

```sh
python3 -m unittest discover -s validation/tests -v
python3 -m validation.harness --input validation/fixtures/toy_cases.jsonl --output-dir /tmp/tom-assist-harness-smoke
```
