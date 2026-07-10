---
name: simple-workflow
description: "Use when the user explicitly asks to use Simple Workflow, simple-workflow, `.simple`, or the Simple Workflow plugin, or when an active `.simple` session pointer exists. Enforces a small plan-centered workflow: listen to requirements, write `plan.md`, review it with a subagent, let the agent determine explicit user approval from conversation context, and structurally gate `create_goal` against the reviewed request."
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
6. When the agent determines from conversation context that the user clearly authorizes execution, reconcile the current Goal with `get_goal`, call `create_goal` at most once for the reviewed request, and record the successful Goal start in `state.json`.
7. Execute the approved `plan.md` and run its validation commands.
8. Run both post-execution reviews, complete the Goal, and then close the local request metadata.

Natural-language approval intent belongs to the agent applying this skill. Hooks must not classify approval with keyword or regular-expression matching. A `UserPromptSubmit` hook may report request readiness, while `PreToolUse(create_goal)` only enforces structural prerequisites after the agent has already determined that the user approved execution.

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

Use `state.json` as the local workflow source of truth. `current.json` and the selected `index.json` request entry must mirror its phase. New requests may record `goal_status` as `pending`, `active`, `completing`, or `completed`, plus `goal_plan_fingerprint` after Goal creation. Readers must accept legacy `id`/`request_id` and `phase`/`status` key variants, but the selected request id and phase values must agree.

The phase transitions are:

```text
plan -> review -> completed
```

- Enter `review` only after the current `plan.md` has a passing subagent review and matching fingerprint.
- Keep phase `review` while the approved work is executing; set `goal_status: active` only after `create_goal` succeeds.
- Enter `completed` only after approved work, validation, and both post-execution reviews pass and `update_goal(status="complete")` succeeds.

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

`review.md` is internal. It must include `# Review`, `## Reviewed Plan Fingerprint` with `Reviewed Plan Fingerprint: sha256:<hex>`, `## Reviewer`, `## Verdict` whose complete trimmed body is exactly `PASS`, `## Blocking Issues` with a blocking-specific no-issue value such as `No blocking issues`, `None`, or `차단 없음`, and `## Flow Check` with a flow-specific no-issue value such as `No flow issues`, `None`, or `흐름 문제 없음`. Do not interchange blocking and flow status vocabulary. The internal review must use `Shared Planning And Review Principles`; its flow result must judge whether the plan exposes all relevant flow problems to the user and keeps the affected flow coherent, not merely whether the Simple Workflow procedure was followed.

`review.md` must also include `## Question Depth Check` with a no-blocking result such as `No unresolved higher-level questions`. This records that clarification did not skip broad or mid-level questions before plan review passed.

Do not ask the user to read `review.md` as part of the normal workflow. Summarize the review result and tell the user when the plan is ready for approval.

## Language Policy

Write human-readable artifact body text in Korean. This applies to `plan.md` sections such as `## Summary`, `## Requirements Coverage`, `## Change Targets`, `## Flow Check`, `## Validation`, and `## Out Of Scope`, and to internal `review.md` body text such as blocking, flow, question-depth, and notes.

Keep fixed validator contract tokens unchanged when needed: headings, table column names, `REQ-###`, `PASS`, `FAIL`, `sha256`, file paths, commands, code identifiers, and validator status/control values may remain in English or code form.

## Operating Flow

At the start of a Simple Workflow turn, inspect `.simple/sessions/<session-id>/current.json` when it exists. If the pointer is missing, invalid, or points to a completed request and the user explicitly invoked Simple Workflow, create or select a request before continuing.

If an active session pointer exists for a request in `plan` or `review` phase, treat follow-up user messages as Simple Workflow continuation even when the prompt does not mention the plugin again. Short answers, confirmations, corrections, and renewed requests such as `응`, `맞아`, `그렇게 해줘`, or `수정해줘` must continue from the active request and follow the same `plan.md`, internal review, validator, and approval rules. A completed request must not capture unrelated follow-up prompts; explicit Simple Workflow invocation starts or selects another request.

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

## Goal Gate And Recovery

After review passes, the agent—not the hook—decides whether the user's latest message clearly approves execution. Words such as `approve`, `proceed`, `승인`, `진행`, or `실행` are examples, not a regular-expression contract; negations, status questions, quoted text, and unrelated uses are not approval.

Before calling `create_goal`, call `get_goal` and reconcile it with the selected request id and reviewed plan fingerprint:

- If no Goal exists, call `create_goal` with an objective naming the request id, exact `.simple/requests/<request-id>/plan.md` path, and reviewed plan fingerprint.
- If a matching Goal is already active, do not call `create_goal` again; repair local `goal_status: active` and continue the same work.
- If a matching Goal is already complete, do not call `create_goal` again; repair the local completed metadata.
- If another unfinished Goal exists, stop and report the conflict instead of replacing it.

The plugin `PreToolUse(create_goal)` hook is a structural gate only. Scope the gate only to Goal objectives containing an exact `.simple/requests/<request-id>/plan.md` path; mentioning Simple Workflow or `.simple` as a topic is not enough. Unrelated Stageflow or other `create_goal` calls must prepass. For an in-scope call, deny the tool unless the path's request id exactly equals the selected request, the selected request is in `review`, metadata is coherent, plugin-bundled review validation passes, the objective fingerprint equals the current plan fingerprint, the review verdict body is exactly uppercase `PASS`, and local `goal_status` is not already `active`, `completing`, or `completed`. Do not write `goal.md`.

After `create_goal` succeeds, record `goal_status: active` and `goal_plan_fingerprint: sha256:<hex>` in `state.json`. If that local write fails, use the matching active Goal returned by `get_goal` as authoritative on the next turn and retry only the local metadata write; never call `create_goal` again for recovery.

## Post-Implementation Review

After approved work and validation commands are complete, run bounded subagent review from two perspectives before the final user response. Both reviews must use `Shared Planning And Review Principles`. This gate applies to code-changing and read-only work.

1. `Intent Compliance Review`: compare the confirmed user intent, approved `plan.md`, actual diff when code changed, or actual outputs and commands when work was read-only, plus validation results. If the work misses the intent, violates the approved plan, introduces an in-scope regression, or leaves an expected validation failing, Codex must fix it automatically and repeat validation plus both post-implementation reviews.
2. `Flow / Unexpected Issue Review`: inspect the affected user, state, data, failure or recovery, command, hook, and validator flows. If a relevant issue is in scope or caused by the implementation, Codex must fix it automatically and repeat validation plus both post-implementation reviews. If the issue is outside the user's intent, pre-existing, or requires expanded scope, Codex must tell the user before changing it.

Do not create new user-facing artifacts for post-implementation review. Summarize the two review results in the final response. If an out-of-scope or pre-existing issue blocks safe completion, explain the blocker and wait for the user's decision.

## Completion And Partial-Failure Recovery

Complete only when every approved requirement has evidence, validation passes, and both post-execution reviews pass. Use this order:

1. While phase remains `review`, durably set `state.json` `goal_status: completing`. If this write fails, do not call `update_goal`.
2. Call `update_goal(status="complete")`; this is the first completed transition.
3. After Goal completion succeeds, set the selected `state.json`, session `current.json`, and matching `index.json` entry to phase `completed`; set `state.json` `goal_status` to `completed` while preserving the reviewed fingerprint.
4. Run plugin-bundled validation with `--phase all` and then give the final response.

If `update_goal` fails, keep local phase `review` and `goal_status: completing`; use `get_goal` to determine whether the Goal remains active before retrying Goal completion. If Goal completion succeeds but local completion metadata fails, the durable `completing` marker records the recovery path: a matching complete Goal, or no unfinished Goal after completion was requested, means repair only local completed metadata and validation on the next turn. Never create a replacement Goal from `completing`. For read-only work, the same completion order applies after the two reviews compare the approved plan with actual outputs, commands, and validation results.
