# V4: supervised-prefix infrastructure correction

V3 run 001 was terminated after the last reported step 80 when an actual
native-tokenizer probe demonstrated different training and inference prefixes.
No v3 held-out generation occurred. Preserve v3 logs and frozen inputs.

V4 reuses the unchanged v3 corpus, extraction parser, thresholds, final-adapter
selection and 512-step training configuration described in the frozen v3
PREREGISTRATION.md. Start fresh from the pinned base; do not resume aborted
weights. The sole experimental change is local supervised rendering: native
inference prefix + unchanged JSON answer + verified native turn suffix.
Neither the installed template nor checkpoint is modified. Check exact text
and token prefix equality and the complete unmasked answer for every train/dev
example using both the preflight and actual training tokenizers before updates.
Maximum sequence length remains 4096; reject truncation.

Freeze all source and data before training. Use the still-unexposed v3 held-out
inventory once after 512 steps, with no checkpoint selection from its results.
Retain every invalid output in denominators. This is a synthetic pilot, not an
independent naturalistic generalisation result. An infrastructure abort has no
GREEN/RED extraction verdict. Prior reports remain unchanged; this correction
does not retroactively rescue them. Numerical/Tree gates remain as declared in
v3, with no inherited result from a different compiler. Git coordination does
not pause training. No cloud generation, network downloads or committed weights.
