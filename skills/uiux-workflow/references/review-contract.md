# UIUX Review Contract

Use this contract for both review cycles. Keep the criteria stable across cycles and apply only criteria relevant to the requested surface.

## Reviewer Boundary

The reviewer is independent from the main implementing agent. Start each review in isolated context with no inherited conversation history: use `fork_turns: "none"` when supported, or an equivalent fresh subagent/session. The reviewer inspects and reports; it does not edit source, generate replacement files, expand scope, or choose a material product decision.

Give the reviewer raw task evidence rather than the main agent's diagnosis or preferred verdict:

- the user's current UI/UX request and confirmed boundaries;
- each target root and its exact `design.md`, or an explicit absent marker;
- when `design.md` is absent, inspected existing component, token, style, and interaction-pattern evidence;
- relevant source, current diff, and affected routes or components;
- validation commands and their actual output; and
- rendered screenshots, browser observations, stories, or an explicit rendering gap.

Do not include author commentary, suspected defects, desired corrections, a preferred verdict, or the expected answer. For Cycle 2, include Cycle 1's raw findings, the complete new source/diff, and new validation/render evidence; do not include the main agent's interpretation of how well its fix worked.

## Fixed Review Criteria

Judge these criteria when applicable to the requested outcome:

1. User intent and scope: the visible result satisfies the current request without unrelated redesign.
2. Guideline fidelity: the implementation follows every applicable `design.md` rule and explains any explicit user override.
3. Existing-system consistency: components, tokens, spacing, typography, color, icons, and interaction patterns reuse the target project's evidence instead of inventing a parallel system.
4. Layout and responsiveness: relevant viewports preserve hierarchy, alignment, density, overflow, and content readability.
5. Interaction states: relevant hover, focus, active, selected, loading, empty, error, disabled, success, and transition behavior are coherent.
6. Accessibility: relevant semantics, labels, keyboard flow, focus visibility, contrast, motion, and assistive-technology behavior are supported.
7. Implementation integrity: the diff is scoped, preserves existing behavior, and has relevant test/build/type/lint evidence.
8. Observable outcome: critical user-visible or interactive claims are supported by rendered evidence. Source assertions may prove source-level conformance, but they do not prove actual appearance or interaction.

Do not fail a task for a non-applicable state or invent a new feature. Do fail an unverified critical claim, an applicable guideline violation, an in-scope regression, or evidence that does not observe the requested result. A missing browser or runnable surface explains a gap; it does not convert a critical gap into `PASS`.

## Review Output

Return this shape:

```markdown
VERDICT: PASS|FAIL
CYCLE: 1|2

FINDINGS:
- [criterion] evidence, impact, and required correction

UNVERIFIED:
- missing observation or `None`
```

Use `VERDICT: PASS` only when no actionable in-scope finding or critical verification gap remains. `PASS` with a critical item under `UNVERIFIED` is invalid; use `VERDICT: FAIL` instead. Keep every finding evidence-backed and identify the affected file, component, state, viewport, or rendered surface when possible.

## Cycle Rules

- Cycle 1 establishes the complete applicable criteria and findings.
- The main agent fixes actionable in-scope findings and reruns affected validation.
- If the only blocker is a material user decision or critical evidence that source edits cannot produce, stop after Cycle 1 and report it.
- Cycle 2 rechecks the complete current outcome plus Cycle 1 findings under the same criteria.
- A regression caused by the fix is still in scope; a newly invented preference is not.
- Cycle 2 `FAIL` is terminal for automatic review. Report it to the user without another review/fix cycle.
