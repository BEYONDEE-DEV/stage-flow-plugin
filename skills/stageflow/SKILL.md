---
name: stageflow
description: "Use when the user explicitly asks to use Stageflow, stage-flow, stageflow, a Stageflow workflow, `.stageflow`, or the stageflow plugin, or when a session current pointer shows an active Stageflow request. Enforces a fixed three-stage loop: definition, implementation plan, and implementation; definition requires artifact/review/approval, while later stages also require a goal handoff before advancement."
---

# Stageflow

Use Stageflow to keep substantial Codex work grounded in durable request artifacts instead of transient chat context.

## Core Contract

Every request always moves through three stage folders:

1. `01-definition`: definition -> subagent review -> user approval
2. `02-implementation-plan`: implementation plan -> subagent review -> user approval
3. `03-implementation`: implementation evidence -> completion audit subagent review -> fix/review cycle until PASS -> user approval/completion

Definition contains these required files, plus a conditional transition-risk pair after the user stops clarification:

```text
.stageflow/requests/<request-id>/01-definition/
  definition.md
  transition-risk-goal.md  (required after user stop signal before definition approval)
  transition-risk.md       (required after user stop signal before definition approval)
  review/final.md
  review/subagents/001-full-bounded-review.md
  approval.md
```

Implementation-plan and implementation contain exactly these required files:

```text
.stageflow/requests/<request-id>/<stage-folder>/
  goal.md
  <stage-artifact>.md
  review/final.md
  review/subagents/001-full-bounded-review.md
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
- Do not use `create_goal` or require `goal.md` for normal `definition` clarification; after a user stop signal, the only allowed definition goal is the transition-risk audit recorded in `01-definition/transition-risk-goal.md` and `01-definition/transition-risk.md`.
- Run `implementation-plan` and `implementation` as goals before writing or revising those stage artifacts.
- Record the goal receipt in those later stage `goal.md` files: stage, artifact path, artifact fingerprint, `Tool: create_goal`, `Invocation recorded: yes`, `Goal created: yes`, and goal status.
- When a definition turn presents `Pending Clarifications`, record an active batch of 1-5 questions in `definition.md`, return the full batch to the user, and stop; the stage itself remains unapproved until the user answers and the review/approval gates pass.
- Review each stage artifact with a subagent. Self-review is allowed only as a private preliminary check and never satisfies the review gate.
- Record review synthesis in the same stage's `review/final.md`, and record each bounded subagent shard in `review/subagents/<cycle>-<slice>.md`. The main agent owns conflict resolution, complete Rule ID checklist coverage, latest verdict, blocking issues, and final verdict in `review/final.md`.
- Do not advance to the next stage until the current stage has a passing subagent review and explicit user approval in `approval.md`.
- Do not implement code until `02-implementation-plan` has goal, artifact, subagent review, and approval.
- During `implementation`, the review subagent must audit completion against every approved implementation-plan work item before final user approval. If any work item is incomplete, unverifiable, out of scope, insufficiently validated, or hidden as a deviation, do not ask for user approval; revise the implementation and `03-implementation/implementation.md`, then rerun the subagent review cycle until the latest review verdict is PASS.
- Write user-facing questions, approvals, status updates, and artifact body text in the user's language. Keep validator-required headings exact.
- Apply `references/language-policy.md` for all Stageflow artifact prose, pending clarification options, review evidence, and completion summaries: keep fixed headings/table columns unchanged, but write natural-language content in the user-selected or inferred artifact language.
- When presenting definition questions to the user, lead with the currently known context so the user understands why the question is being asked. Each visible question must name the decision needed, show all labeled options, state the recommended option, explain why the answer matters in user-facing terms, and say which definition area the answer will update.
- If validation fails, fix artifacts or ask the user for the missing decision. Do not bypass the validator.
- During `definition`, assume only definition-level ambiguity remains to clarify until the user explicitly stops the question loop. Treat purpose and intent as first-class definition content, separate from outcomes: if purpose is not confirmed, keep a purpose-focused top-direction (`Question Scope`) question active before moving deeper; defer implementation-plan-only decisions such as modules, files, architecture, test commands, validation strategy, work items, and implementation order.
- After every user answer in `definition`, reflect the answer into `definition.md`, then create or maintain the next clarification batch with 1-5 active questions in `Pending Clarifications`, and stop for the user.
- Never close `definition` because the agent judges the request `clear enough`, complete, or has no more questions. Only the user can end the question loop with an explicit stop signal listed in the definition writing rules, such as `proceed` or `go ahead`. That stop signal opens the transition-risk gate; it does not by itself approve definition or authorize implementation planning. Transition-risk is a goal-achievement decision readiness audit: ask whether a decision must be settled in definition for the user goal to succeed, then record only decisions that are missing, conflicting, or ambiguous. Already-decided requirements, boundaries, policies, and already answered/reflected user decisions are not risk cases and must be carried into implementation-plan coverage or constraints instead. Before writing any transition-risk row, compare the candidate against `Clarification History`, `Resolved Decisions`, requirements, acceptance criteria, policy rules, and boundaries.
- Treat implementation-plan transition stop signals as user stop signals, not as options inside pending clarification questions. Use the exact stop-signal examples from the definition writing rules.
- Every pending clarification question shown to the user must include at least two explicit labeled options such as `Option 1:` and `Option 2:`; `Option 3:` and higher are allowed and must be shown when present. Never ask with only one recommendation or an unlabeled suggestion.
- Classify each pending question by `Question Scope` using the exact labels from the definition writing rules. Start with top-direction batches, keep asking top-direction questions while top-direction ambiguities remain, and move to major-decision or detail-check questions only when clarification history or resolved decisions show the previous question scope has been sufficiently covered.
- During `AWAITING_USER`, the main response answers follow-ups, restates pending questions/options, and stops, while a question-generation subagent may prepare optional `01-definition/question-backlog.md` candidates in parallel. Backlog candidates are not final pending questions until the main agent evaluates the user answer impact and promotes, revises, or discards them.

## Definition Question Scope Criteria

Use answer impact to classify pending clarification questions, then write the exact localized `Question Scope` label from `references/stages/01-definition/definition-writing-and-review-rules.md`.

- Top-direction: the answer can change request identity, purpose/intent, top-level scope, target user/system surface, desired outcomes, current problem framing, or explicit boundaries.
- Major-decision: the answer stays inside the approved top-direction scope but can change major behavior areas, user/system flow, state model, policy groups, integration responsibility, or data responsibility.
- Detail-check: the answer stays inside an approved behavior or policy direction and refines acceptance outcome, copy/text, fallback behavior, error handling, recovery semantics, or regression boundary; implementation-plan-only test commands and validation strategy are deferred.

When showing scope labels to the user, briefly explain their practical meaning in the user's language instead of relying on the internal label alone.

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
   - `AWAITING_USER`: classify the user prompt as `follow_up`, `pending_answer`, or `stop_signal`. For `follow_up`, answer, restate every pending question with all labeled options, and stop. For `pending_answer`, reflect the answer into `definition.md`, compare `question-backlog.md` candidates against answer impact, and create the next pending batch. For `stop_signal`, record the stop signal, create the transition-risk audit goal, write `01-definition/transition-risk-goal.md` and `01-definition/transition-risk.md`, ask the user to confirm generated risk cases, and only then proceed to definition review/approval. No definition `goal.md` is required.
   - `IMPLEMENTATION_BLOCKED` / `repair_implementation_plan_gate`: do not implement; return to the implementation-plan stage until its goal, artifact, subagent review, and approval gates pass.
   - `OK` / `continue_current_stage`: continue only from the validated current stage.
3. If Stageflow was explicitly invoked and no usable session current pointer exists, inspect the project, create a new request folder, scaffold all three stage folders, and write `.stageflow/sessions/<session-id>/current.json`.
4. Read `.stageflow/index.json`, `.stageflow/sessions/<session-id>/current.json`, the selected request's `state.json`, and the current stage files.
5. Decide whether the latest user message continues the current request or starts a separate request.
6. Run the validator for the current stage when artifacts exist.
7. Continue only from the validated current stage. If the hook returns `AWAITING_USER`, do not treat the stage as broken; show every pending question in the batch with its explicit labeled options, then wait for the user.

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

Read `references/language-policy.md` before authoring or revising any Stageflow artifact or user-facing workflow message so prose uses the selected user/artifact language while validator-required headings, table columns, status values, identifiers, paths, and commands remain unchanged.

Read `references/intent-fidelity.md` when definition or implementation planning could reinterpret user wording, especially for UX flow, screen, route, state, data, API, or persistence behavior.

Before running a stage review subagent, read and use the matching review agent prompt file:

- Definition: `references/stages/01-definition/definition-review-agent-prompt.md`
- Implementation plan: `references/stages/02-implementation-plan/implementation-plan-review-agent-prompt.md`
- Implementation: `references/stages/03-implementation/implementation-review-agent-prompt.md`

Keep only the core workflow in this `SKILL.md`; stage-specific writing rules, review checks, and review prompts live in those reference files.

## Review And Approval

For every stage:

1. Compute the SHA-256 fingerprint of the current stage artifact.
2. Split non-trivial review work into bounded shard scopes. Prefer parallel subagents when there are independent rule clusters, domains, changed areas, or implementation work items. A small/simple stage may use one `review/subagents/001-full-bounded-review.md` shard.
3. Run subagent reviews using the matching stage review agent prompt. Each subagent writes only its assigned shard under `review/subagents/<cycle>-<slice>.md`, with explicit inputs, shard scope, verdict, and blocking issues.
4. The main agent writes `review/final.md`. It must list every shard in `## Subagent Review Shards`, resolve shard conflicts or missing coverage, record `Subagent review.`, the exact `Reviewed Artifact Fingerprint: sha256:<hex>`, and a complete `## Writing And Review Rule Checklist` using every Rule ID from the matching stage rule file.
5. If any shard or final synthesis finds blocking issues, revise the stage artifact and repeat the shard review cycle. During `implementation`, blocking issues include any approved implementation-plan work item that is incomplete, unverifiable, out of scope, insufficiently validated, or not mapped to implementation evidence.
6. Ask the user for explicit approval only after `review/final.md` passes validation.
7. Record `Stage approved: yes`, `Approved By`, `Approved At`, and the user's explicit approval text in `approval.md`.

Approval text must contain clear positive intent such as `approve`, `approved`, `go ahead`, `proceed`, `yes`, or equivalent approval wording in the user's language. Silence or vague acknowledgement is not approval.

## Validator

Run the skill-local validator wrapper against the target project root. The wrapper delegates to `<plugin-root>/scripts/validate_stageflow.py`, so agents can use a skill-local script path while hooks still resolve the bundled plugin script directly:

```bash
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --root <target-project-root> --current --session-id <session-id> --phase definition
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --root <target-project-root> --current --session-id <session-id> --phase implementation-plan
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --root <target-project-root> --current --session-id <session-id> --phase implementation
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --root <target-project-root> --current --session-id <session-id> --phase all
```

Use `--print-template` to get exact starter files:

```bash
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template stage-tree
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template goal  # implementation-plan/implementation only
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template definition
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template implementation-plan
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template implementation
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template review
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template approval
```

The validator is an auditor. Treat failures as the next action to repair.

## Hooks

Plugin hooks are read-only for durable workflow artifacts except for runtime records under `.stageflow/hook-state/`. They may block premature tool use.

- `PreToolUse` blocks non-Stageflow file edits until `implementation-plan` validates, while allowing `.stageflow/**` artifact creation and repair.
- `UserPromptSubmit` checks the active stage, records `status` and `turn_start_action` under `.stageflow/hook-state/`, and passes next-turn guidance through Codex hook wire output `additionalContext` instead of top-level internal JSON fields.
- Implementation-like prompts validate `implementation-plan` before code work proceeds and record `IMPLEMENTATION_BLOCKED` with `turn_start_action: repair_implementation_plan_gate` in hook state/additional context when the gate fails.
- `Stop` blocks missing preflight markers, missing current pointers after explicit Stageflow prompts, invalid current pointers, and completion-like responses that fail `--phase all`.
- `AWAITING_USER` means a definition artifact has an active `Pending Clarifications` batch. The main response must not claim completion or next-stage progress. Follow-up turns must restate all pending labeled choices; answer turns may revise `definition.md` and create the next pending batch; stop-signal turns must run the definition transition-risk goal before review, approval, or implementation-plan work.
- Question-generation subagents may run in parallel during `AWAITING_USER` only to prepare optional `01-definition/question-backlog.md` candidates. Other subagent roles or subagent writes to stage artifacts/review/approval are blocked in that wait state.

See `references/artifact-format.md` for request-level and common artifact shapes, the matching stage writing and review rule file for stage artifact format, the matching stage review agent prompt for subagent review instructions, and `references/hooks.md` for hook behavior.
