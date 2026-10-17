# Quality Gate (ELI5++)

Run this gate after building the artifact and before writing any delivery message.

**The gate has three tiers, and the delivery statement must name which tiers actually ran.** This is the one rule that separates ELI5++ from its parents: an unrun check is never reported as a passed check.

## Tier 1 — Always required (static)

```bash
python3 scripts/check_html.py --strict /absolute/path/artifact.html
```

Must exit 0. Covers: remote runtime resources, CSS `url()` and `@import` remote fetches, `fetch`/`WebSocket`/`EventSource`/`XMLHttpRequest`, missing `alt`, `role="img"` without an accessible name, **inline `<svg>` without an accessible name**, unresolved placeholders, missing `lang`, missing viewport, `<main>` and `<h1>` cardinality.

## Tier 2 — Required whenever the artifact contains `<script>`

```bash
python3 scripts/check_js.py /absolute/path/artifact.html
```

Must exit 0. Parses every inline block and local `src` with `node --check`. Skips `application/ld+json`, `importmap`, and other non-executable types.

If `node` is unavailable, the script fails rather than passing silently — say that JS was **not** validated.

## Tier 3 — Only when a browser is available

"Only when available" describes **whether the check can run**, not whether its result is optional. If Playwright is present, run it and its verdict is binding. If it is absent, exit 2 records that geometry was never measured — which is a fact to report, not a pass to claim.

```bash
python3 scripts/check_geometry.py /absolute/path/artifact.html
```

Exit 0 = measured at 320 / 375 / 1440 px with no overflow, no escaping controls, no external requests, and correct `<main>`/`<h1>` counts. A `[PASS-WITH-WARNINGS]` result means warnings were found and need a human decision before delivery.

Exit 2 = **Playwright is not installed; geometry was not verified.** This is not a pass.

Without Tier 3 you may say: *"静态校验通过；未进行浏览器渲染，几何与视觉质量未验证。"*
You may not say: *"视觉正常"*, *"移动端适配良好"*, *"动画工作正常"*.

## Content

- The first scene makes the core relationship identifiable without a separate prose answer.
- Every factual claim is supportable from supplied material, local evidence, or an appropriate primary source.
- Every action is assigned to the correct actor; formats and protocols are not described as if they were sensors, circuits, or applications.
- Logical concepts are not silently narrowed to one physical implementation.
- Removing the analogy leaves a correct explanation.
- **Every important analogy has an explicit mapping and an explicit limit.**
- A process, calculation, diagnosis, or decision includes one concrete worked example.
- The artifact states the most likely boundary, exception, uncertainty, or misconception.
- A teach-back or transfer question appears only when the user's goal is learning.

## Visual Reasoning

- Remove decorative elements that do not explain a relationship.
- Use consistent color, shape, and placement to signal the same meaning throughout.
- Place labels beside the objects or connections they describe.
- Make visual quantities correspond exactly to displayed values.
- Preserve meaningful sign, direction, baseline, and order, or label the visual as intentionally simplified.
- Do not imitate buttons, play controls, sliders, or links unless they actually work.
- Keep each scene focused on one new relationship.
- Text stays subordinate to the visuals: if a section is mainly consecutive prose paragraphs, it is not a visual explainer.

## Motion

- Motion is present only where it encodes a real state change or data flow.
- No pulse, shimmer, or highlight on an already-finished result.
- `prefers-reduced-motion: reduce` yields the static final state, not a frozen mid-animation.
- A static or accessible path conveys the same information without watching the animation.
- Every control (pause, replay, step) actually works; nothing is drawn to look interactive without being interactive.
- No claim of animation that was not implemented or not observed working.

## Accessibility And Reflow

- One `h1`, logical headings, a semantic `main`, and a document `lang`.
- Every meaningful `img` has a useful `alt`.
- **Every inline `<svg>` has a `<title>`, or `role="img"` with `aria-label`, or `aria-hidden="true"` when decorative.**
- Diagram containers using `role="img"` have `aria-label` or `aria-labelledby`.
- Color is never the only way to distinguish states or categories.
- Required information is available without hover.
- Reflow at 320 CSS px without horizontal scrolling, clipping, or overlapping text.
- Readable text/background contrast; normal text at or above `4.5:1`. Bold weight does not excuse a near miss.
- Stable media dimensions.

## Validation Sequence

1. Run Tier 1. Fix every error; treat warnings as real until disproved.
2. Run Tier 2 if any `<script>` exists.
3. Run Tier 3 if a browser is available. If it is not, record that fact for the delivery statement.
4. Read the artifact again **with the analogy removed** and confirm the factual model still holds.
5. Write the delivery statement naming exactly which tiers ran.

Static checks and clean screenshots are evidence-aligned quality controls. They do not prove that a person learned the topic. Stronger validation requires representative novice users to explain the core idea or apply it to a new example without being coached.
