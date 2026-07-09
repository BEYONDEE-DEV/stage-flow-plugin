---
name: stageflow
description: "Use when the user explicitly asks to use Stageflow, stage-flow, stageflow, a Stageflow workflow, `.stageflow`, or the stageflow plugin, or when `.stageflow/sessions/<session-id>/current.json` has `active: true`. Enforces a fixed three-stage loop: definition, implementation plan, and implementation; definition requires artifact/review/approval, while later stages also require a goal handoff before advancement."
---

# Stageflow

Use Stageflow to keep substantial Codex work grounded in durable request artifacts instead of transient chat context.

## Core Contract

Every request moves through three fixed stage folders:

1. `01-definition`: definition -> subagent review -> user approval
2. `02-implementation-plan`: implementation plan -> goal handoff -> subagent review -> user approval
3. `03-implementation`: implementation evidence -> goal handoff -> completion audit subagent review -> fix/review cycle until PASS -> user approval/completion

Definition required files:

```text
.stageflow/requests/<request-id>/01-definition/
  definition.md
  definition-store/
  question-scope-transition-review.md
  transition-risk-goal.md
  transition-risk.md
  review/final.md
  review/subagents/001-full-bounded-review.md
  approval.md
```

Implementation-plan and implementation required files:

```text
.stageflow/requests/<request-id>/<stage-folder>/
  goal.md
  <stage-artifact>.md
  review/final.md
  review/subagents/001-full-bounded-review.md
  approval.md
```

`02-implementation-plan` also requires `review/subagents/002-flow-completeness-review.md`. Stage artifact names are `01-definition/definition.md`, `02-implementation-plan/implementation-plan.md`, and `03-implementation/implementation.md`.

Do not use the removed root-level gates as required artifacts: `context.md`, `source-requirements.md`, root `plan.md`, root `review.md`, root `approval.md`, root `goal.md`, `implementation-log.md`, `plan-compliance-review.md`, `code-review.md`, or `completion-summary.md`. Do not use retired four-stage folders for new requests.

## Non-Negotiable Rules

- Inspect the project before asking definition questions.
- Keep every request in `.stageflow/requests/<request-id>/`, and use `.stageflow/sessions/<session-id>/current.json` with `active: true` as the active request authority.
- Do not use `create_goal` or `goal.md` for normal definition clarification. After a user stop signal, the only allowed definition goal is the transition-risk audit recorded in `transition-risk-goal.md` and `transition-risk.md`; it is a goal-achievement decision readiness audit.
- Run `implementation-plan` and `implementation` as goals before writing or revising those later-stage artifacts, and record goal receipt in their `goal.md`.
- Review each stage artifact with a subagent. The main agent writes `review/final.md`; self-review never satisfies the review gate.
- Do not advance until the current stage has a passing subagent review and explicit user approval in `approval.md`.
- Do not implement code until `02-implementation-plan` has goal, artifact, subagent review, and approval.
- During `implementation`, audit every approved implementation-plan work item and complete flow before final user approval.
- Write user-facing questions, approvals, status updates, and artifact prose in the user's language. Apply `references/language-policy.md` while keeping validator-required headings, columns, identifiers, status values, paths, and commands exact.
- During definition, defer implementation-plan-only decisions such as modules, files, architecture, test commands, validation strategy, work items, and implementation order unless the answer changes approved service meaning.
- During active definition clarification, `definition-store/working-set.json.active_pending_questions` is the canonical live pending batch and `definition.md` is only the approval-ready snapshot.
- New Stageflow requests must create `01-definition/definition-store/` with `working-set.json`, `decision-ledger.jsonl`, `trace-index.json`, and `sync-state.json` before the first pending clarification batch is shown.
- During `AWAITING_USER`, answer follow-ups and restate the full active batch, or record valid store decision progress and either show the next full batch or set the required sync gate.
- Treat duplicate/derived pending questions as store decisions. Remember: already answered/reflected user decisions are not risk cases; carry them into implementation-plan coverage or constraints.
- Classify pending questions by `Question Scope` using the exact localized `Question Scope` label from the definition rules: `큰방향`, `주요결정`, or `세부확인`.
- Before moving to a lower-scope pending batch, run a question scope transition review subagent and record PASS in `question-scope-transition-review.md`.
- Helper subagents may prepare bounded next-turn inputs such as `01-definition/question-backlog.md` only after `SubagentStart` registers their role; the main agent must promote, revise, or discard helper output.
- If validation fails, repair artifacts or ask the user for the missing decision. Do not bypass the validator.

## Definition Hot Path

Read `references/artifacts/definition-store.md` and `references/stages/01-definition/definition-clarification-rules.md` before handling active clarification.

The fast path uses only `definition-store/` for low-risk answers. Store progress means a valid `DEC-*` ledger row, turn-start `source_pending_id`, affected IDs, matching `trace-index.json`, and matching `sync-state.decision_sync`. If no sync gate is active, the active pending batch must change and the response must show every question and every labeled option.

Risk gates:

- `low`: store-only answer/follow-up; do not read or write full `definition.md`.
- `medium`: set `current_gate: "targeted-sync-required"` and use a registered targeted-sync subagent.
- `high`, scope-transition, stop-signal, review, or approval path: set `current_gate: "full-consistency-required"` or `snapshot-current` as required before touching the snapshot.

## Implementation Feedback And Redefinition

Use selective rework instead of blanket invalidation.

- If implementation is wrong but definition and implementation plan are correct, stay in `implementation` and rerun evidence/review as needed.
- If the implementation plan is wrong but the definition is correct, return to `implementation-plan` and revise only affected work items, coverage, risks, and validation strategy.
- If the approved definition is wrong, return to `definition`, revise affected requirements, policy rules, acceptance criteria, boundaries, or data responsibilities, then judge downstream impact.
- If the feedback is a separate new request, start a new `.stageflow/requests/<request-id>/` folder.

Detailed redefinition, behavior, flow, and intent rules live in `references/stages/01-definition/definition-behavior-rules.md`.

## Turn Start Routine

At the start of every turn using this skill:

1. Read the latest `UserPromptSubmit` hook result under `.stageflow/hook-state/sessions/<session-id>/main/current-turn.json`; fall back to `.stageflow/hook-state/current-turn.json` only when scoped state is unavailable.
2. Process `status` and `turn_start_action` before any substantive answer:
   - `PREPASS` / `none`: outside Stageflow unless explicitly invoked.
   - `REQUEST_REQUIRED` / `create_request`: inspect the project, create request scaffolding including `01-definition/definition-store/`, and write the session current pointer with `active: true`.
   - `DEFINITION_STORE_REQUIRED` / `create_definition_store`: create required store files and rerun current-stage validation before processing the user answer.
   - `INVALID_CURRENT` / repair action: repair or replace current pointer/state before continuing.
   - `COMPLETED_CURRENT` / `start_new_request`: create or select a non-completed request before new workflow work.
   - `WARNING` / `repair_current_stage`: repair artifacts and rerun validation before advancing or asking for approval.
   - `AWAITING_USER`: read `active_pending_questions`, decide semantically whether the user answered, asked a follow-up, challenged duplication, or stopped clarification, then update `definition-store/` or restate the full active batch and stop.
   - `TARGETED_SYNC_REQUIRED`: register a targeted-sync subagent and write only targeted sync artifacts until the gate is satisfied.
   - `FULL_CONSISTENCY_REQUIRED`: register a full-consistency subagent and require a PASS `full-consistency-report.json`.
   - `SNAPSHOT_CURRENT_REQUIRED`: sync `definition.md` from the store and update the store fingerprint.
   - `IMPLEMENTATION_BLOCKED`: return to implementation-plan until its gates pass.
   - `OK`: continue only from the validated current stage.
3. If Stageflow was explicitly invoked and no usable session current pointer exists, inspect the project, create a new request folder, scaffold all stage folders, and write `.stageflow/sessions/<session-id>/current.json` with `active: true`.
4. Read `.stageflow/index.json`, session current pointer, request `state.json`, and current stage files.
5. Decide whether the latest user message continues the current request or starts a separate request.
6. Run the validator for the current stage when artifacts exist.
7. Continue only from the validated current stage.

Treat hook `turn_start_instruction` as mandatory structural guidance. Do not quote raw hook JSON, `additionalContext`, Stop hook feedback, or hook-state content in user-visible responses.

Use request IDs in this form:

```text
YYYYMMDD-HHMM-short-slug
```

Allowed request phases are `definition`, `implementation-plan`, `implementation`, and `completed`.

## Stage Instruction Files

Before authoring or revising any Stageflow artifact or user-facing workflow message, read `references/language-policy.md`.

Before definition work, read `references/stages/01-definition/definition-writing-and-review-rules.md`, then load the focused file for the task:

- `references/stages/01-definition/definition-clarification-rules.md` for active pending questions, store hot path, question scope, backlog, and follow-up/answer handling.
- `references/stages/01-definition/definition-behavior-rules.md` for purpose, intent, normal behavior, scope narrowing, approved flow inventory, and redefinition.
- `references/stages/01-definition/definition-artifact-template.md` for the full `definition.md` starter format.
- `references/stages/01-definition/definition-transition-risk-rules.md` after a user stop signal.

Before implementation-plan work, read `references/stages/02-implementation-plan/implementation-plan-writing-and-review-rules.md`. Before implementation work, read `references/stages/03-implementation/implementation-writing-and-review-rules.md`.

Read `references/intent-fidelity.md` when definition or planning could reinterpret user wording, especially for UX flow, screen, route, state, data, API, or persistence behavior.

Before review subagents, read the matching prompt:

- Definition: `references/stages/01-definition/definition-review-agent-prompt.md`
- Implementation plan: `references/stages/02-implementation-plan/implementation-plan-review-agent-prompt.md`
- Implementation: `references/stages/03-implementation/implementation-review-agent-prompt.md`

For common artifact shapes, read `references/artifact-format.md`, then its focused `references/artifacts/` files as routed.

## Review And Approval

For every stage:

1. Compute the SHA-256 fingerprint of the current stage artifact.
2. Split non-trivial review work into bounded subagent shards; `02-implementation-plan` always includes a separate `flow-completeness` shard.
3. The main agent writes `review/final.md` with `Subagent review.`, exact reviewed artifact fingerprint, listed shard files, complete Rule ID checklist, latest verdict, blocking issues, and final verdict.
4. If any shard or final synthesis finds blocking issues, revise the artifact and rerun review. During implementation, incomplete or unverifiable approved work items or complete flows are blocking issues.
5. Ask for explicit user approval only after `review/final.md` passes validation.
6. Record `Stage approved: yes`, `Approved By`, `Approved At`, and the explicit approval text in `approval.md`.

Approval text must contain clear positive intent such as `approve`, `approved`, `go ahead`, `proceed`, `yes`, or equivalent wording in the user's language.

## Validator

Run the skill-local validator wrapper against the target project root. The wrapper delegates to `<plugin-root>/scripts/validate_stageflow.py`, so agents can use a skill-local script path while hooks still resolve the bundled plugin script directly:

```bash
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --root <target-project-root> --current --session-id <session-id> --phase definition
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --root <target-project-root> --current --session-id <session-id> --phase implementation-plan
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --root <target-project-root> --current --session-id <session-id> --phase implementation
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --root <target-project-root> --current --session-id <session-id> --phase all
```

Use `--print-template` for exact starter files. The validator is an auditor; treat failures as the next repair action.

## Hooks

Plugin hooks are read-only for durable workflow artifacts except for runtime records under `.stageflow/hook-state/`. They may block premature tool use.

- `UserPromptSubmit` records structural status, `turn_start_action`, pending clarification context, and gate guidance.
- `PreToolUse` enforces the current gate, including store-only clarification paths that must not read or write `01-definition/definition.md`.
- `Stop` blocks unsafe completion or advancement claims and enforces `AWAITING_USER` continuity with lightweight store checks.
- `SubagentStart` registers bounded helper roles for question backlog, scope transition review, targeted sync, full consistency, and store helper files.

See `references/hooks.md` for hook behavior.
