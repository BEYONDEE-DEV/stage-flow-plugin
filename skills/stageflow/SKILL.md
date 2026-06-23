---
name: stageflow
description: "Use when the user explicitly asks to use Stageflow, workflow, stageflow, `.stageflow`, or the stageflow plugin, or when a session current pointer shows an active Stageflow request. Enforces a fixed three-stage loop: definition, implementation plan, and implementation; every stage requires a goal handoff, a stage artifact, subagent review, and explicit user approval before the next stage."
---

# Stageflow

Use Stageflow to keep substantial Codex work grounded in durable request artifacts instead of transient chat context.

## Core Contract

Every request always moves through three stage folders:

1. `01-definition`: definition -> subagent review -> user approval
2. `02-implementation-plan`: implementation plan -> subagent review -> user approval
3. `03-implementation`: implementation evidence -> subagent review -> user approval/completion

Each stage contains exactly these required files:

```text
.stageflow/requests/<request-id>/<stage-folder>/
  goal.md
  <stage-artifact>.md
  review.md
  approval.md
```

Stage artifact names are:

- `01-definition/definition.md`
- `02-implementation-plan/implementation-plan.md`
- `03-implementation/implementation.md`

Do not use the removed root-level gates as required artifacts: `context.md`, `source-requirements.md`, root `plan.md`, root `review.md`, root `approval.md`, root `goal.md`, `implementation-log.md`, `plan-compliance-review.md`, `code-review.md`, or `completion-summary.md`. Do not use the retired four-stage folders `01-requirements`, `02-service-plan`, `03-implementation-plan`, or `04-implementation` for new requests.

## Non-Negotiable Rules

- Inspect the project before asking definition questions.
- Keep every request in its own `.stageflow/requests/<request-id>/` folder.
- Use the session current pointer at `.stageflow/sessions/<session-id>/current.json` as the active request authority.
- Run each stage as a goal before writing or revising that stage artifact.
- Record the goal receipt in that stage's `goal.md`: stage, artifact path, artifact fingerprint, `Tool: create_goal`, `Invocation recorded: yes`, `Goal created: yes`, and goal status.
- When a definition turn presents `Pending Clarifications`, close the Codex goal before the final response and record `Goal status: completed` plus `Goal completion reason: awaiting user clarification`; the stage itself remains unapproved until the user answers and the review/approval gates pass.
- Review each stage artifact with a subagent. Self-review is allowed only as a private preliminary check and never satisfies the review gate.
- Record every review in the same stage's `review.md`, including review cycle history, current artifact fingerprint, latest verdict, blocking issues, and final verdict.
- Do not advance to the next stage until the current stage has a passing subagent review and explicit user approval in `approval.md`.
- Do not implement code until `02-implementation-plan` has goal, artifact, subagent review, and approval.
- Write user-facing questions, approvals, status updates, and artifact body text in the user's language. Keep validator-required headings exact.
- If validation fails, fix artifacts or ask the user for the missing decision. Do not bypass the validator.
- During `definition`, assume there is always more ambiguity to clarify until the user explicitly stops the question loop.
- After every user answer in `definition`, reflect the answer into `definition.md`, create the next concrete clarification question, keep it active in `Pending Clarifications`, and stop for the user.
- Never close `definition` because the agent judges the request `clear enough`, `충분함`, or has no more questions. Only the user can end the loop with an explicit stop signal: `구현 계획으로 넘어가기`, `질문 그만`, `충분해`, `진행`, `승인`, `proceed`, or `go ahead`.
- Treat `구현 계획으로 넘어가기` as a user stop signal, not as an option inside a pending clarification question.

## Implementation Feedback And Redefinition

When the user gives feedback after implementation has started or after implementation evidence is presented, classify the feedback before changing artifacts or claiming completion:

- If the implementation result is wrong but the approved definition and implementation plan are still correct, stay in `implementation` and revise the implementation evidence, validation, and review as needed.
- If the implementation plan is wrong but the approved definition is still correct, return to `implementation-plan`, revise only the affected work items, coverage, risks, and validation strategy, then rerun the implementation-plan review and approval gate.
- If the approved definition itself is wrong, return to `definition` and revise the affected requirements, policy rules, acceptance criteria, resolved decisions, or boundaries. Preserve existing `implementation-plan` and `implementation` artifacts as reference material; do not automatically discard them.
- If the feedback is a separate new request rather than a correction to the active request, start a new `.stageflow/requests/<request-id>/` folder instead of mutating the current request.

Use selective rework instead of blanket invalidation. Keep downstream artifacts when they still match the revised definition, partially revise them when only some work items are affected, rewrite them when policy, requirements, acceptance criteria, or data responsibility changes make the old plan incorrect, and record any implementation rollback or correction in `03-implementation/implementation.md` under `## Plan Compliance And Deviations`.


## Turn Start Routine

At the start of every turn using this skill:

1. Read the latest `UserPromptSubmit` hook result first when it exists under `.stageflow/hook-state/sessions/<session-id>/main/current-turn.json`; fall back to `.stageflow/hook-state/current-turn.json` only when scoped state is unavailable.
2. Process the hook result by `status` and `turn_start_action` before any substantive answer:
   - `PREPASS` / `none`: treat the turn as outside Stageflow unless the skill was explicitly invoked.
   - `REQUEST_REQUIRED` / `create_request`: inspect the project, create a new request folder, scaffold all three stage folders, and write `.stageflow/sessions/<session-id>/current.json` before answering the workflow request.
   - `INVALID_CURRENT` / `repair_current_pointer` or `repair_current_state`: repair or replace the session current pointer and matching `state.json` before continuing.
   - `COMPLETED_CURRENT` / `start_new_request`: create or select a non-completed request before doing new workflow work.
   - `WARNING` / `repair_current_stage`: repair the current stage artifacts and rerun validation before advancing or asking for approval.
   - `AWAITING_USER` / `await_user_clarification`: answer any user follow-up, restate every pending clarification question with its options, and stop without review, approval, next-stage work, or blocked-goal handling. The matching `goal.md` must already be completed with `Goal completion reason: awaiting user clarification`.
   - `IMPLEMENTATION_BLOCKED` / `repair_implementation_plan_gate`: do not implement; return to the implementation-plan stage until its goal, artifact, subagent review, and approval gates pass.
   - `OK` / `continue_current_stage`: continue only from the validated current stage.
3. If Stageflow was explicitly invoked and no usable session current pointer exists, inspect the project, create a new request folder, scaffold all three stage folders, and write `.stageflow/sessions/<session-id>/current.json`.
4. Read `.stageflow/index.json`, `.stageflow/sessions/<session-id>/current.json`, the selected request's `state.json`, and the current stage files.
5. Decide whether the latest user message continues the current request or starts a separate request.
6. Run the validator for the current stage when artifacts exist.
7. Continue only from the validated current stage. If the hook returns `AWAITING_USER`, do not treat the stage as broken; show the pending question text and options, then wait for the user.

Treat `turn_start_instruction` in the hook result as mandatory next-action guidance. If it conflicts with memory or chat context, trust the hook state and durable artifacts first.

Use request IDs in this form:

```text
YYYYMMDD-HHMM-short-slug
```

Allowed request phases are `definition`, `implementation-plan`, `implementation`, and `completed`.

## Stage Instruction Files

Before authoring or revising a stage artifact, read the matching writing and review rule file:

- Definition: `references/stages/01-definition/definition-writing-and-review-rules.md`
- Implementation plan: `references/stages/02-implementation-plan/implementation-plan-writing-and-review-rules.md`
- Implementation: `references/stages/03-implementation/implementation-writing-and-review-rules.md`

Before running a stage review subagent, read and use the matching review agent prompt file:

- Definition: `references/stages/01-definition/definition-review-agent-prompt.md`
- Implementation plan: `references/stages/02-implementation-plan/implementation-plan-review-agent-prompt.md`
- Implementation: `references/stages/03-implementation/implementation-review-agent-prompt.md`

Keep only the core workflow in this `SKILL.md`; stage-specific writing rules, review checks, and review prompts live in those reference files.

## Review And Approval

For every stage:

1. Compute the SHA-256 fingerprint of the current stage artifact.
2. Run a subagent review using the matching stage review agent prompt, against only that stage's artifact and the previous approved stage artifacts needed for context.
3. Record `Subagent review.` in `review.md` and the exact `Reviewed Artifact Fingerprint: sha256:<hex>`.
4. Record `## Writing And Review Rule Checklist` using every Rule ID from the matching stage rule file.
5. If the review finds blocking issues, revise the stage artifact and repeat the review cycle.
6. Ask the user for explicit approval only after review passes.
7. Record `Stage approved: yes`, `Approved By`, `Approved At`, and the user's explicit approval text in `approval.md`.

Approval text must contain clear positive intent such as `approve`, `approved`, `go ahead`, `proceed`, `yes`, `승인`, or `진행`. Silence or vague acknowledgement is not approval.

## Validator

Run the plugin-bundled validator against the target project root. Do not assume the target project contains its own `scripts/validate_stageflow.py` copy:

```powershell
python <plugin-root>/scripts/validate_stageflow.py --root <target-project-root> --current --session-id <session-id> --phase definition
python <plugin-root>/scripts/validate_stageflow.py --root <target-project-root> --current --session-id <session-id> --phase implementation-plan
python <plugin-root>/scripts/validate_stageflow.py --root <target-project-root> --current --session-id <session-id> --phase implementation
python <plugin-root>/scripts/validate_stageflow.py --root <target-project-root> --current --session-id <session-id> --phase all
```

Use `--print-template` to get exact starter files:

```powershell
python <plugin-root>/scripts/validate_stageflow.py --print-template stage-tree
python <plugin-root>/scripts/validate_stageflow.py --print-template goal
python <plugin-root>/scripts/validate_stageflow.py --print-template definition
python <plugin-root>/scripts/validate_stageflow.py --print-template implementation-plan
python <plugin-root>/scripts/validate_stageflow.py --print-template implementation
python <plugin-root>/scripts/validate_stageflow.py --print-template review
python <plugin-root>/scripts/validate_stageflow.py --print-template approval
```

The validator is an auditor. Treat failures as the next action to repair.

## Hooks

Plugin hooks are read-only for durable workflow artifacts except for runtime records under `.stageflow/hook-state/`. They may block premature tool use.

- `PreToolUse` blocks non-Stageflow file edits until `implementation-plan` validates, while allowing `.stageflow/**` artifact creation and repair.
- `UserPromptSubmit` checks the active stage, emits a preflight marker, and returns `turn_start_action` so the next turn is driven by durable state instead of chat memory.
- Implementation-like prompts validate `implementation-plan` before code work proceeds and return `IMPLEMENTATION_BLOCKED` with `turn_start_action: repair_implementation_plan_gate` when the gate fails.
- `Stop` blocks missing preflight markers, missing current pointers after explicit Stageflow prompts, invalid current pointers, and completion-like responses that fail `--phase all`.
- `AWAITING_USER` means a definition artifact has active `Pending Clarifications`; the assistant must not continue review/approval until the user answers the pending question, asks a follow-up that is answered with the pending choices restated, or explicitly gives a stop signal. The response must not claim goal/stage completion or next-stage progress.
- Subagent lifecycle hooks record lightweight observation state only.

See `references/artifact-format.md` for request-level and common artifact shapes, the matching stage writing and review rule file for stage artifact format, the matching stage review agent prompt for subagent review instructions, and `references/hooks.md` for hook behavior.
