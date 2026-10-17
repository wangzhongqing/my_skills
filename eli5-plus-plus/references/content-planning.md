# Content Planning Guide (ELI5++)

Use this guide before drawing the artifact. The goal is not to make the topic merely look simple; it is to give a novice a small, correct mental model they can use.

## 1. Separate Fact From Analogy

Write two private lists before composing scenes:

- **Facts:** claims that must remain true when the visual metaphor is removed.
- **Analogy:** familiar objects or actions used only to make relationships easier to see.

Never use an analogy as evidence. If the explanation becomes false after removing it, revise the factual model first.

Assign every action to the correct actor. Distinguish a data format or rule from the sensor, circuit, program, or process that produces or applies it. For example, do not say a representation format performs the physical measurement that precedes encoding.

Keep the abstraction level honest. If the concept guarantees a shared logical channel, do not redefine it as one physical wire unless that physical implementation is explicitly the subject.

For every important analogy, fill this table. **It is not optional in ELI5++** — the third column is what stops a vivid analogy from becoming a wrong mental model.

| Familiar element | Target element | Where the match stops |
|---|---|---|
| The known object or action | The technical object or relationship it represents | One important difference the viewer must not infer |

Show the boundary **in the artifact** when a likely misconception would otherwise remain. Use the `.boundary` block for this; it renders in warning color so it cannot be mistaken for ordinary supporting copy.

## 2. Build The Smallest Useful Model

Choose from these five parts:

1. **Core idea:** the one sentence and relationship the viewer should remember.
2. **Mechanism:** the minimum sequence or cause-and-effect chain needed to make the core idea believable.
3. **Concrete example:** one real input moving through the mechanism to a visible result.
4. **Boundary:** the most likely wrong inference, exception, or uncertainty.
5. **Understanding check:** one optional teach-back or transfer question when learning is the goal.

These are planning units, not mandatory headings. Select only what the topic needs.

## 3. Size The Work Before Choosing Scenes

Length follows what the reader will *do* with the artifact, not a "keep it short" reflex. Three tiers:

| Tier | Scenes | Chinese chars | When |
|---|---|---|---|
| **Brief** | 2–3 | ~600–900 | One concept, quick reference, reader won't come back |
| **Standard** (default) | 4–6 | ~1200–2000 | Reader must genuinely understand and will act on it |
| **Deep** | 6–9 | ~2500–4000 | Layered mechanisms, several boundaries, or the reader will teach it to someone else |

Default to **Standard**. When the user has not specified, err toward depth: a reader can skim a long page, but cannot recover a mechanism you compressed into a slogan. Drop to Brief only when the user asked for brevity, the task is a definition lookup, or the prerequisites were covered elsewhere.

Going Deep usually means **splitting a part**, not adding new parts: turn "mechanism" into two or three scenes (one causal step each), split "boundary" into "common misconception" and "real limitation", and add "how this differs from the adjacent concept".

Split when a scene would introduce more than one new relationship. Combine when two scenes repeat the same relationship with different decoration. Let the viewer process each scene at their own pace.

**Sufficiency test:** after reading, can the viewer explain this to someone else *and* say when it stops being true? If they can only restate the conclusion, the mechanism is thin — add a scene, not an adjective.

## 4. Prepare Unavoidable Terms

Replace jargon with ordinary words when precision survives. When a technical term is necessary:

1. show the familiar meaning or visible role first;
2. place the term next to the object it names;
3. reuse the same term consistently afterward.

Do not place a glossary far away from the visual it explains.

## 5. Match The Visual To The Relationship

Choose the simplest suitable pattern. In ELI5++ the mapping is deliberate, not aesthetic:

| Relationship | Pattern | Template class |
|---|---|---|
| Ordered steps, movement, transformation, handoff | Flow | `.flow` |
| Before/after, same/different, alternatives | Comparison | `.comparison` |
| Containment, hierarchy, dependencies, abstraction | Layers | `.layers` |
| Interaction over time | Sequence | `.stage` + controls |
| State change | State diagram or **meaningful motion** | `.stage` + controls |

Use position, connecting lines, and repeated shape before adding prose. Keep labels physically close to the objects or connections they explain.

## 6. Use One Worked Example

For a process, calculation, diagnosis, or decision, show one specific example from start to finish. Values, bar heights, positions, counts, and labels must correspond exactly. Preserve meaningful sign, direction, baseline, and ordering; if an intentional simplification removes one of them, label that limitation. Do not add a decorative chart whose geometry contradicts its numbers.

## 7. Decide Whether Motion Earns Its Place

Ask: **does the reader learn something from seeing this change over time that they could not learn from a static final state?**

- If yes: use the `.stage` pattern. It already provides controls, a static fallback, and `prefers-reduced-motion` handling.
- If no: do not animate. A fade-in or a pulse on an already-finished result is decoration, and ELI5+ explicitly forbids it.

Never animate to make a page feel dynamic. Motion that does not encode a state change is a defect, not a feature.

## 8. Add A Check Only When It Helps

When the user wants to learn the topic, end with one optional prompt such as:

- "In your own words, what changes between step 1 and step 2?"
- "Which part would fail if this input disappeared?"
- "Where would you place this new example?"

For quick reference, troubleshooting, or executive scanning, omit the check unless it adds clear value.

When the artifact is meant to stand on its own, pair a check with concise feedback. A native `details` disclosure can preserve retrieval effort while still letting the viewer verify their answer.
