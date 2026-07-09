---
name: simple-workflow
description: "Use when the user explicitly asks to use Simple Workflow, simple-workflow, `.simple`, or the Simple Workflow plugin, or when an active `.simple` session pointer exists. Enforces a small plan-centered workflow: listen to requirements, write `plan.md`, review `plan.md` with a subagent until it passes, then call `create_goal` only after the user says a proceed phrase such as approve, proceed, 승인, 진행, or 실행."
---

# Simple Workflow

Use this skill to keep Codex work tied to a single human-readable plan while preserving an internal review record.

## Core Rule

Follow exactly this sequence:

1. Listen to the user's requirements.
2. Inspect the project, infer the user's intent, and ask the user to confirm or correct that inferred intent before writing `plan.md`. Ask clarification questions from broad to narrow: 대분류 before 중분류, and 중분류 before 소분류.
3. Write `plan.md` from the confirmed intent and requirements.
4. Review `plan.md` with a subagent and write internal `review.md`.
5. If review fails, revise `plan.md` and repeat the subagent review until it passes.
6. When the user says `approve`, `go ahead`, `proceed`, `implement`, `승인`, `진행`, or `실행`, call `create_goal`.

Do not add approval files, requirements files, goal files, implementation logs, completion summaries, source-requirements, analysis files, service-plan files, plan-compliance reviews, code-review files, Direct Parallel queues, Evidence Map, Inventory matrices, or subagent-only review protocols.

## Request Storage

Keep request state under the target project:

```text
.simple/
  index.json
  sessions/<session-id>/current.json
  requests/<request-id>/
    state.json
    plan.md
    review.md
```

`index.json`, `current.json`, `state.json`, and `review.md` are internal metadata or internal review records. The only required human workflow artifact is `plan.md`.

Use request IDs in this form: `YYYYMMDD-HHMM-short-slug`.

Allowed phases are `plan`, `review`, and `completed`.

## Artifact Rules

`plan.md` must include `# Plan`, `## Summary`, `## Requirements Coverage` with a concrete execution plan for every `REQ-###`, `## Change Targets`, `## Flow Check`, `## Validation`, and `## Out Of Scope`.

## Shared Planning And Review Principles

Use the same principles when writing `plan.md`, reviewing `plan.md` with a subagent, and reviewing the implemented code after changes are made:

- Preserve the user's confirmed intent and the approved scope.
- Give every `REQ-###` a concrete, verifiable execution plan.
- Tell the user about relevant flow problems discovered while planning or implementing, even when they were pre-existing or outside the requested change.
- Clearly separate in-scope problems from out-of-scope issues; do not fix out-of-scope issues without user approval.
- Keep validation tied to the real affected product, feature, state, data, user, command, hook, or validator flow.
- Write human-readable artifact and review body text in Korean while preserving fixed control tokens.

`## Flow Check` in `plan.md` must state whether the affected product, feature, state, data, user, command, hook, and validation flows are coherent after considering the planned changes. It must tell the user about any relevant flow problem discovered during planning, even when the problem was pre-existing and was not caused by the requested change. Report flow breaks such as broken user journeys, inconsistent state transitions, missing failure or retry paths, contradictory behavior across entry points, data moving through the wrong owner, or a validation path that no longer proves the real flow. If a discovered problem is outside the requested scope, say so explicitly instead of hiding it.

`review.md` is internal. It must include `# Review`, `## Reviewed Plan Fingerprint` with `Reviewed Plan Fingerprint: sha256:<hex>`, `## Reviewer`, `## Verdict` with `PASS`, `## Blocking Issues` with `No blocking issues` or `None`, and `## Flow Check` with `No flow issues` or `None`. The internal review must use `Shared Planning And Review Principles`; its flow result must judge whether the plan exposes all relevant flow problems to the user and keeps the affected flow coherent, not merely whether the Simple Workflow procedure was followed.

`review.md` must also include `## Question Depth Check` with a no-blocking result such as `No unresolved higher-level questions`. This records that clarification did not skip broad or mid-level questions before plan review passed.

Do not ask the user to read `review.md` as part of the normal workflow. Summarize the review result and tell the user when the plan is ready for approval.

## Language Policy

Write human-readable artifact body text in Korean. This applies to `plan.md` sections such as `## Summary`, `## Requirements Coverage`, `## Change Targets`, `## Flow Check`, `## Validation`, and `## Out Of Scope`, and to internal `review.md` body text such as blocking, flow, question-depth, and notes.

Keep fixed validator contract tokens unchanged when needed: headings, table column names, `REQ-###`, `PASS`, `FAIL`, `sha256`, file paths, commands, code identifiers, and validator status/control values may remain in English or code form.

## Operating Flow

At the start of a Simple Workflow turn, inspect `.simple/sessions/<session-id>/current.json` when it exists. If the pointer is missing, invalid, or points to a completed request and the user explicitly invoked Simple Workflow, create or select a request before continuing.

If an active session pointer exists for a request in `plan` or `review` phase, treat follow-up user messages as Simple Workflow continuation even when the prompt does not mention the plugin again. Short answers, confirmations, corrections, and renewed requests such as `응`, `맞아`, `그렇게 해줘`, or `수정해줘` must continue from the active request and follow the same `plan.md`, internal review, validator, and approval rules.

Before asking questions, inspect the project enough to understand the request. Then state the inferred intent, expected outcome, and notable flow risks or assumptions from the affected product or system flow, including relevant pre-existing issues discovered while planning, and ask the user to confirm or correct that intent before writing `plan.md`.

## Question Depth Gate

Use three clarification depths:

- `대분류`: request identity, purpose, top-level scope, target user or system surface, expected outcome, and explicit boundaries.
- `중분류`: major behavior areas, ownership, sequencing, state or data responsibility, integration responsibility, and review/approval flow.
- `소분류`: copy/text, exact fallback behavior, edge case detail, validation detail, and small acceptance refinements.

Before moving from `대분류` to `중분류`, run a bounded subagent check asking whether any unresolved `대분류` question remains. Before moving from `중분류` to `소분류`, run another bounded subagent check asking whether any unresolved `중분류` question remains. Give the subagent only the user's request, inspected project facts, answered questions, and the candidate next-depth questions. The subagent must return `PASS` only when no higher-level question is still needed for `plan.md`.

If the subagent finds a missing higher-level question, ask that question before descending. Do not write `plan.md` while a broad or mid-level decision that can change the plan is still open. Do not create a new artifact for these checks; summarize the latest checkpoint to the user when asking the next batch and record the final result in `review.md` under `## Question Depth Check`.

Before moving to the next step, run the plugin-bundled validator against the target project root. The validator lives under the Simple Workflow plugin root, not under the target project's `scripts/` directory:

```powershell
python <plugin-root>/scripts/validate_simple_workflow.py --root <target-project-root> --current --session-id <session-id> --phase plan
python <plugin-root>/scripts/validate_simple_workflow.py --root <target-project-root> --current --session-id <session-id> --phase review
```

Treat validator failures as the next action. Fix the artifact or ask the user for the missing decision.

When the user gives a proceed phrase after review passes, call `create_goal` with an objective that names the request id, `plan.md`, and the reviewed plan fingerprint. Do not write `goal.md`.

## Post-Implementation Review

After code changes and validation commands are complete, run bounded subagent review from two perspectives before the final user response. Both reviews must use `Shared Planning And Review Principles`.

1. `Intent Compliance Review`: compare the confirmed user intent, approved `plan.md`, actual diff, and validation results. If the implementation misses the intent, violates the approved plan, introduces an in-scope regression, or leaves an expected validation failing, Codex must fix it automatically and repeat validation plus both post-implementation reviews.
2. `Flow / Unexpected Issue Review`: inspect the affected user, state, data, failure or recovery, command, hook, and validator flows. If a relevant issue is in scope or caused by the implementation, Codex must fix it automatically and repeat validation plus both post-implementation reviews. If the issue is outside the user's intent, pre-existing, or requires expanded scope, Codex must tell the user before changing it.

Do not create new user-facing artifacts for post-implementation review. Summarize the two review results in the final response. If an out-of-scope or pre-existing issue blocks safe completion, explain the blocker and wait for the user's decision.
