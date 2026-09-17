# V11 framing continuation — verified development result

The 660-update continuation completed at cumulative step 3300. The frozen selection
rule selects the new checkpoint. Both remaining development errors were resolved.

| Metric | V10 baseline, 2640 steps | V11, 3300 steps |
|---|---:|---:|
| Exact / 132 | 130 (98.5%) | 132 (100%) |
| Valid / 132 | 132 (100%) | 132 (100%) |
| Invented authority | 0 | 0 |
| Paraphrase equality / 44 | 42 | 44 |
| Contrast distinction / 44 | 44 | 44 |

All 20 development families are exact on every example, and all predeclared
extraction development thresholds are met. No family regressed. This is a
DEVELOPMENT result: repeated curriculum design used development failure analysis,
so this does not establish fresh generalisation or a held-out gate pass.

Selected adapter: `.tmp/event-graph-lora-v11-session-001/epoch-1/adapter`.
SHA-256: `4d5201649f27778c53db424a3b0631d6434d3ef017085d1314b0387b43d68e23`.
Previous checkpoints remain intact. No further training was started. No fresh
held-out, matrix discrimination or Tree test was run. The next experimental stage
requires a separately frozen fresh held-out extraction protocol and this selected
adapter before any new test generation.

Verification rehashed frozen sources and adapters, reparsed all 264 raw outputs
including the reused baseline, recomputed full development scores and selection,
and checked saved token IDs and finish reasons. RESULT.json contains full reports
and provenance hashes. No new generation was performed during verification.
