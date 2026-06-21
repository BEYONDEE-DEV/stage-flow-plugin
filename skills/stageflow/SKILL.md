---
name: stageflow
description: Use when the user explicitly asks to use Stageflow, workflow, stageflow, `.stageflow`, or the stageflow plugin, or when a session current pointer shows an active Stageflow request. Enforces a fixed four-stage loop: requirements, service plan, implementation plan, and implementation; every stage requires a goal handoff, a stage artifact, subagent review, and explicit user approval before the next stage.
---

# Stageflow

Use Stageflow to keep substantial Codex work grounded in durable request artifacts instead of transient chat context.

## Core Contract

Every request always moves through four stage folders:

1. `01-requirements`: requirements -> subagent review -> user approval
2. `02-service-plan`: service plan -> subagent review -> user approval
3. `03-implementation-plan`: implementation plan -> subagent review -> user approval
4. `04-implementation`: implementation evidence -> subagent review -> user approval/completion

Each stage contains exactly these required files:

```text
.stageflow/requests/<request-id>/<stage-folder>/
  goal.md
  <stage-artifact>.md
  review.md
  approval.md
```

Stage artifact names are:

- `01-requirements/requirements.md`
- `02-service-plan/service-plan.md`
- `03-implementation-plan/implementation-plan.md`
- `04-implementation/implementation.md`

Do not use the removed root-level gates as required artifacts: `context.md`, `source-requirements.md`, root `plan.md`, root `review.md`, root `approval.md`, root `goal.md`, `implementation-log.md`, `plan-compliance-review.md`, `code-review.md`, or `completion-summary.md`.

## Non-Negotiable Rules

- Inspect the project before asking requirement questions.
- Keep every request in its own `.stageflow/requests/<request-id>/` folder.
- Use the session current pointer at `.stageflow/sessions/<session-id>/current.json` as the active request authority.
- Run each stage as a goal before writing or revising that stage artifact.
- Record the goal receipt in that stage's `goal.md`: stage, artifact path, artifact fingerprint, `Tool: create_goal`, `Invocation recorded: yes`, `Goal created: yes`, and goal status.
- Review each stage artifact with a subagent. Self-review is allowed only as a private preliminary check and never satisfies the review gate.
- Record every review in the same stage's `review.md`, including review cycle history, current artifact fingerprint, latest verdict, blocking issues, and final verdict.
- Do not advance to the next stage until the current stage has a passing subagent review and explicit user approval in `approval.md`.
- Do not implement code until `03-implementation-plan` has goal, artifact, subagent review, and approval.
- Write user-facing questions, approvals, status updates, and artifact body text in the user's language. Keep validator-required headings exact.
- If validation fails, fix artifacts or ask the user for the missing decision. Do not bypass the validator.

## Turn Start Routine

At the start of every turn using this skill:

1. If Stageflow was explicitly invoked and no usable session current pointer exists, inspect the project, create a new request folder, scaffold all four stage folders, and write `.stageflow/sessions/<session-id>/current.json`.
2. Read `.stageflow/index.json`, `.stageflow/sessions/<session-id>/current.json`, the selected request's `state.json`, and the current stage files.
3. Decide whether the latest user message continues the current request or starts a separate request.
4. Run the validator for the current stage when artifacts exist.
5. Continue only from the validated current stage.

Use request IDs in this form:

```text
YYYYMMDD-HHMM-short-slug
```

Allowed request phases are `requirements`, `service-plan`, `implementation-plan`, `implementation`, and `completed`.

## Stage Instruction Files

Before authoring or revising a stage artifact, read the matching writing and review rule file:

- Requirements: `references/stages/01-requirements/requirements-writing-and-review-rules.md`
- Service plan: `references/stages/02-service-plan/service-plan-writing-and-review-rules.md`
- Implementation plan: `references/stages/03-implementation-plan/implementation-plan-writing-and-review-rules.md`
- Implementation: `references/stages/04-implementation/implementation-writing-and-review-rules.md`

Before running a stage review subagent, read and use the matching review agent prompt file:

- Requirements: `references/stages/01-requirements/requirements-review-agent-prompt.md`
- Service plan: `references/stages/02-service-plan/service-plan-review-agent-prompt.md`
- Implementation plan: `references/stages/03-implementation-plan/implementation-plan-review-agent-prompt.md`
- Implementation: `references/stages/04-implementation/implementation-review-agent-prompt.md`

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

Run the validator from the target project root:

```powershell
python scripts/validate_stageflow.py --current --session-id <session-id> --phase requirements
python scripts/validate_stageflow.py --current --session-id <session-id> --phase service-plan
python scripts/validate_stageflow.py --current --session-id <session-id> --phase implementation-plan
python scripts/validate_stageflow.py --current --session-id <session-id> --phase implementation
python scripts/validate_stageflow.py --current --session-id <session-id> --phase all
```

Use `--print-template` to get exact starter files:

```powershell
python scripts/validate_stageflow.py --print-template stage-tree
python scripts/validate_stageflow.py --print-template goal
python scripts/validate_stageflow.py --print-template requirements
python scripts/validate_stageflow.py --print-template service-plan
python scripts/validate_stageflow.py --print-template implementation-plan
python scripts/validate_stageflow.py --print-template implementation
python scripts/validate_stageflow.py --print-template review
python scripts/validate_stageflow.py --print-template approval
```

The validator is an auditor. Treat failures as the next action to repair.

## Hooks

Plugin hooks are read-only guards except for runtime records under `.stageflow/hook-state/`.

- `UserPromptSubmit` checks the active stage and emits a preflight marker.
- Implementation-like prompts validate `implementation-plan` before code work proceeds.
- `Stop` checks that a required preflight marker appeared in the assistant response.
- Completion-like responses validate `--phase all`.
- Subagent lifecycle hooks record lightweight observation state only.

See `references/artifact-format.md` for request-level and common artifact shapes, the matching stage writing and review rule file for stage artifact format, the matching stage review agent prompt for subagent review instructions, and `references/hooks.md` for hook behavior.


