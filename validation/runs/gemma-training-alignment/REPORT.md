# Gemma supervised-prefix correction

The pinned Gemma template renders a complete assistant training message with
`<|turn>model` immediately followed by the answer, but its native generation
prompt inserts an empty thought-channel boundary before the answer. The stock
MLX masked-prompt dataset uses the length of that generation prompt as the
supervision offset. A real-tokenizer probe confirmed unequal text and token
prefixes, causing part of the JSON opening to fall inside the prompt mask.

V3 run 001 was terminated for this infrastructure defect after its last logged
step 80 (exit 143). No v3 held-out inference took place. It has no extraction
verdict. Its frozen inputs and log are preserved locally.

V4 starts fresh from the same pinned base and retains v3's frozen data, parsing,
thresholds and 512-step configuration. The local tokenizer adapter constructs
the native inference prefix followed by the unchanged supervised answer and
verified native turn suffix. The installed tokenizer and checkpoint stay intact.
Exact text/token alignment and the complete answer boundary passed for all 480
training and 132 development examples, including checks with the actual training
tokenizer before updates. Maximum aligned length is 1,693 tokens, below 4,096.
The combined relevant regression suite passed 135 tests.

This discovery does not change the immutable v1 aggregate result. It identifies
a training confound; it does not establish that this defect caused every v1
semantic or formatting error. The corrected experiment must pass its own held-out
extraction and subsequent numerical gates. Training loss alone is not that result.

`EVIDENCE.json` records the tokenizer probe, checks and v4 freeze hash. Training
continues independently of source commits. Weights and temporary run outputs
remain local and outside this report.
