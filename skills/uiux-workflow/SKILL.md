---
name: uiux-workflow
description: "Use only when the user explicitly invokes `$stageflow:uiux-workflow` or `[$stageflow:uiux-workflow](...)` to implement or modify UI/UX code, styles, or assets with project guidelines and a bounded subagent review/fix cycle. Never invoke implicitly for ordinary UI, UX, frontend, visual-design, accessibility, responsive-design, or design.md requests."
---

# UIUX Workflow

Implement UI/UX changes against the target project's own guidance, then use an independent reviewer subagent for at most two review cycles.

## Invocation Boundary

Use this skill only after one of these explicit user invocations:

```text
$stageflow:uiux-workflow [free-form UI/UX intent]
[$stageflow:uiux-workflow](...) [free-form UI/UX intent]
```

Do not infer activation from UI, UX, frontend, visual design, accessibility, responsive behavior, or `design.md` being mentioned or present. Do not continue this workflow in a later task unless the user explicitly invokes it again. If an explicit invocation has no actionable intent, ask for the target and intended outcome before changing files.

## Workflow

### 1. Resolve Target Roots

Treat a user-specified project root as authoritative. Otherwise use the canonical project root for a single-project task. For a confirmed multi-repository task, resolve each changed repository independently and keep its guidance scoped to that repository.

Do not apply one repository's UI guidance to another repository. Do not infer a shared UI contract merely because repositories belong to one bundle or use similar technology.

### 2. Select The Design Basis

For each target root, check only the case-sensitive exact path `<target-root>/design.md`. Do not recursively search for another `design.md`, accept differently cased filenames, or promote a nested package document to project-wide guidance.

After controlling system and developer instructions, interpret UI requirements in this order:

1. the user's explicit current requirements;
2. the applicable root `design.md`;
3. observed existing components, tokens, styles, and project conventions.

If `design.md` is absent, continue from the user's requirements and inspected project evidence. State that fallback briefly; do not invent a missing design guideline.

When a material conflict makes it unclear whether the user intended to override `design.md`, would expand scope, or would cause a destructive UI change, report the conflicting facts, likely effect, and decision needed before implementing that part. Do not silently rewrite the user's intent or `design.md`.

### 3. Inspect Before Editing

Inspect only the surfaces relevant to the requested change. Establish the applicable basis from:

- the affected user flow and visible outcome;
- existing reusable components and design tokens;
- layout and responsive behavior;
- interaction, focus, keyboard, loading, empty, error, disabled, and success states when applicable;
- accessibility semantics and contrast when applicable; and
- existing tests, preview routes, stories, screenshots, or render commands.

Prefer existing primitives and patterns. Do not turn a scoped UI/UX request into a broad redesign or new design-system project.

### 4. Implement And Validate

Implement the requested UI code, styles, and assets within the confirmed scope. Preserve unrelated behavior and follow the target repository's normal architecture and commands.

Run the narrowest relevant tests, type checks, lint, build, stories, or preview commands. When the project is runnable and the affected surface is renderable, inspect the actual rendered UI with available browser, screenshot, or application evidence at the relevant viewport and state. Static source inspection alone does not prove a critical visual outcome that can be rendered.

Use already available project tooling first. Do not install packages, download a browser, or introduce preview infrastructure solely for review without the user's authorization.

If a critical user-visible or interactive outcome cannot be observed, record the exact verification gap and what evidence is missing. That gap requires `FAIL`; do not return or report `PASS` with a critical gap. Do not claim visual PASS from unrelated tests or source assertions.

### 5. Run The Bounded Review Cycle

Read [references/review-contract.md](references/review-contract.md) completely before starting review. Use an independent subagent reviewer; the main agent remains the only implementation owner.

Start every reviewer without inherited conversation history: use `fork_turns: "none"` when the subagent API supports it, or an equivalent fresh-context reviewer otherwise. Pass only the raw inputs listed in the review contract. Do not include implementation commentary, the main agent's diagnosis, a preferred verdict, or hidden expected findings.

Use at most two total review cycles:

1. Cycle 1 reviews the current implementation and evidence against the fixed applicable criteria.
2. If Cycle 1 returns `PASS`, stop reviewing.
3. If Cycle 1 returns actionable in-scope `FAIL`, have the main agent fix those findings and rerun affected validation.
4. If Cycle 1 fails only because of a material user decision or critical evidence that source changes cannot provide, stop and report it without spending Cycle 2 on the same unchanged blocker.
5. Otherwise start a fresh-context Cycle 2 reviewer with the complete current result, the same fixed criteria, Cycle 1's raw findings, and new raw validation/render evidence. Do not pass the main agent's interpretation of its fix. Do not add a new quality bar merely because another cycle exists.
6. If Cycle 2 returns `FAIL`, stop. Report the remaining evidence-backed blockers, verification gaps, or user decisions. Do not start Cycle 3.

Do not auto-fix a finding that materially changes requirements, scope, ownership, irreversible risk, or the validation standard. Return that decision to the user.

### 6. Report The Result

Summarize:

- which target root and `design.md` basis were used or absent;
- what UI/UX outcome changed;
- tests and rendered evidence actually observed;
- the final review cycle and verdict; and
- any remaining blocker or verification gap.

Never describe the workflow as complete when Cycle 2 is `FAIL` or a critical requested outcome remains unobserved.
