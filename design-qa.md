# Chat workspace design QA

## Comparison target

- Source visual truth: `/Users/kenmorkaya/.codex/generated_images/01a09350-27fd-7cc2-b88d-d877dc802e00/exec-82f6b3a3-7714-4c4f-afcf-9791aa502cfb.png`
- Implementation: `http://127.0.0.1:1420/?design-preview=1`
- Implementation screenshot: browser capture displayed in the implementation thread on 19 September 2026. Browser security prevented exporting that already-captured image to a filesystem path; the live local preview remains the inspectable implementation source.
- Source pixels: 1,488 × 1,058.
- Implementation capture: 1,440 × 1,024 browser viewport at device scale 1.
- Normalisation: the source is a 1.03:1 scale variant of the same desktop ratio. Comparison used the complete 1,440 × 1,024 implementation viewport without browser chrome.
- State: Chat open; one question entered; supported result returned; three sources visible; first source expanded; discussion drawer open; form proposal open; profile panel closed.

## Full-view comparison evidence

The source and implementation were both opened during the same QA pass. The
implementation preserves the source's three-part hierarchy: dark project
navigation, verified result plus evidence in the working area, and a separate
discussion drawer. The verified result remains visually dominant. Evidence is
shown once with readable titles; exact text expands in place. The assistant
drawer is visually secondary and states that it cannot change the finding.

The implementation intentionally retains two controls absent from the visual
concept: the explicit `Answer from project documents` action and the governed
provider packet preview. They preserve the existing no-automatic-query and
explicit-send boundaries.

## Focused-region comparison evidence

- Header/model region: model location is visible; GPT is active; Gemma is
  visibly unavailable for ordinary chat; provider controls sit behind one
  settings affordance.
- Result/evidence region: 15px result copy, serif result heading, restrained
  verified tint, source count and expandable evidence match the selected
  hierarchy. Internal chunk filenames are visually hidden.
- Discussion region: profile disclosure, three suggested actions, form proposal
  and review action are contained in the drawer. Closing it exposes a floating
  `Ask Tom` control and reopening restores the drawer.
- Compact desktop: the initial 1,024 × 768 capture squeezed the main workspace
  and allowed the answer action to overflow. The drawer now becomes an overlay
  below 1,180px, leaving the evidence workspace at a usable width.

## Findings

No actionable P0, P1 or P2 findings remain.

- Fonts and typography: Georgia retains the existing editorial display voice;
  Inter/system UI text remains readable at 12–16px with 1.45–1.65 line height.
  Headings, labels and evidence text preserve the visual hierarchy.
- Spacing and layout rhythm: the 1,440px view matches the selected navigation,
  two-column evidence workspace and 350px assistant drawer. The compact-width
  overflow found in the first pass was repaired.
- Colors and visual tokens: forest green, pale mint, white and muted borders
  match the selected design. Semantic green is reserved for verified/supported
  states.
- Image quality and assets: the design contains no raster illustration. Tabler
  icons provide consistent production icons; no placeholder, emoji, CSS-drawn
  or handcrafted SVG assets were used.
- Copy and content: verified result, exact evidence, ToM relationship,
  discussion role, form review and profile boundary are distinct. Technical
  chunk filenames are retained only for accessibility and regression
  compatibility, not shown visually.

## Primary interactions tested

- create/select conversation;
- enter a project-document question and request the answer;
- expand an exact evidence source;
- open and close user-background disclosure;
- open a form proposal and hand it to the existing review form;
- close the discussion drawer and reopen it from `Ask Tom`;
- run the 1,440 × 1,024 and 1,024 × 768 layouts; and
- inspect browser logs: no warnings or errors.

## Comparison history

1. First compact capture: P1 horizontal overflow in the answer action and a
   compressed evidence workspace while the assistant drawer remained in-flow.
2. Fix: changed the drawer to a fixed overlay below 1,180px and allowed the
   evidence workspace to use the full content width.
3. Post-fix capture: controls remain reachable, the main workspace no longer
   collapses, and the drawer can be dismissed and reopened.

## Follow-up polish

- P3: the explicit answer and packet-preview controls add more vertical space
  than the visual concept. They remain because they are product safety gates.
- P3: the reviewed-structure action appears inside an expanded source; a later
  polish pass could move it behind an `Advanced` disclosure.

## Final result

final result: passed
