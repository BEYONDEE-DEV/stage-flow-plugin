# Stageflow Artifact Format

Stageflow uses one request folder with three fixed stage folders. This file defines request-level structure and common stage files. Stage-specific artifact formats live in each stage's writing and review rule file.

## Registry Files

`.stageflow/index.json`

```json
{
  "version": "1",
  "requests": [
    {
      "id": "20260621-1200-three-stage-workflow",
      "title": "Three stage workflow",
      "status": "definition",
      "created_at": "2026-06-21T03:00:00Z",
      "updated_at": "2026-06-21T03:00:00Z"
    }
  ]
}
```

`.stageflow/sessions/<session-id>/current.json`

```json
{
  "request_id": "20260621-1200-three-stage-workflow",
  "phase": "definition",
  "activated_by": "explicit_skill_invocation"
}
```

`.stageflow/requests/<request-id>/state.json`

```json
{
  "request_id": "20260621-1200-three-stage-workflow",
  "phase": "definition",
  "last_validated_at": null
}
```

Allowed phases are `definition`, `implementation-plan`, `implementation`, and `completed`.

## Request Tree

```text
.stageflow/requests/<request-id>/
  state.json
  01-definition/
    definition.md
    question-backlog.md       (optional helper)
    transition-risk-goal.md   (required after user stop signal before definition approval)
    transition-risk.md        (required after user stop signal before definition approval)
    review.md
    approval.md
  02-implementation-plan/
    goal.md
    implementation-plan.md
    review.md
    approval.md
  03-implementation/
    goal.md
    implementation.md
    review.md
    approval.md
```

Each stage must pass in order. A later stage validation also validates every earlier stage.

## Stage Writing And Review Rule Files

Before writing or reviewing a stage artifact, read the matching rule file:

- Definition: `references/stages/01-definition/definition-writing-and-review-rules.md`
- Implementation plan: `references/stages/02-implementation-plan/implementation-plan-writing-and-review-rules.md`
- Implementation: `references/stages/03-implementation/implementation-writing-and-review-rules.md`

Each rule file owns that stage's artifact format, required sections, writing rules, and review checks.

## Stage Review Agent Prompt Files

Before running a review subagent, use the matching prompt file:

- Definition: `references/stages/01-definition/definition-review-agent-prompt.md`
- Implementation plan: `references/stages/02-implementation-plan/implementation-plan-review-agent-prompt.md`
- Implementation: `references/stages/03-implementation/implementation-review-agent-prompt.md`

Each prompt file owns the review mission, allowed inputs, forbidden actions, review instructions, and required review output for that stage.

Use `references/intent-fidelity.md` when stage artifacts involve user wording that could be narrowed into unapproved UX, route, screen, state, data, API, or persistence behavior.

## Optional Definition Question Backlog

Definition artifacts include `## Purpose And Intent` as required first-class purpose coverage; confidence must be `confirmed`, `inferred`, or `unknown`, and inferred/unknown purpose requires a purpose-focused 큰방향 pending question.

`01-definition/question-backlog.md` may be created by a question-generation subagent in parallel while definition is waiting for user clarification. It is a helper artifact only: it does not replace `definition.md`, `review.md`, `approval.md`, or the current `Pending Clarifications`, and it is not required for validation. Use it to record candidate next questions, question scope (`큰방향`, `주요결정`, `세부확인`), labeled options, affected definition areas, and invalidation triggers before the main agent decides whether to promote, revise, or discard them after the user answer.

## Definition Transition Risk Gate

After the user gives a definition stop signal such as `구현 계획으로 넘어가기`, Stageflow must run a narrow transition-risk audit before definition review/approval. This is the only definition-stage `create_goal` exception, and it does not create `01-definition/goal.md`. It records `01-definition/transition-risk-goal.md` and produces `01-definition/transition-risk.md`. This audit is about goal-achievement decision readiness: before planning, ask whether the user goal can succeed without another definition-level decision. Generated risk cases are candidates only and must identify a missing required decision, a conflict between required decisions, or an ambiguity that can change how the goal is achieved. Before writing any row, compare the candidate against `Clarification History`, `Resolved Decisions`, `Intent Fidelity`, `Requirements`, `Acceptance Criteria`, `Policy Rules`, and `Boundaries`. Already-decided requirements, intent-fidelity rows, boundaries, policy rules, and already answered and reflected user decisions are not transition risks; carry them into implementation-plan coverage or constraints instead of listing them as `accepted-risk`. Reflect true missing decisions into `definition.md` only after user confirmation, or record unresolved material decision risk as out-of-scope, accepted residual risk, duplicate generated risk, or not applicable.

`transition-risk-goal.md` records:

```md
# Transition Risk Goal

Stage: definition

Purpose: transition-risk

Artifact Path: `01-definition/transition-risk.md`

Definition Artifact Fingerprint: sha256:<definition-fingerprint>

## Goal Invocation

Tool: create_goal

Invocation recorded: yes

Invocation result: goal created

## Goal Tool Status

Goal created: yes

Goal status: completed
```

`transition-risk.md` contains `## Risk Generation Basis`, `## Generated Risk Cases`, `## Suggested Definition Updates`, `## User Confirmation`, and `## Final Disposition`. `Generated Risk Cases` must use columns `ID`, `Category`, `Risk Case`, `Affected Definition Area`, `Definition Coverage`, `Prior Answer Check`, `Suggested Handling`, `User Confirmation`, and `Disposition`. `Definition Coverage` must be `uncovered`, `conflicting`, `ambiguous`, or `not-applicable`: `uncovered` means a goal-critical decision is missing from definition, `conflicting` means goal-critical decisions conflict inside definition, `ambiguous` means a goal-critical decision can be interpreted multiple ways, and `not-applicable` means the audit found no material decision gap. `Prior Answer Check` must be `not-answered`, `answered-not-reflected`, `answered-conflicting`, or `not-applicable`: `not-answered` means no prior user answer or resolved decision covers the candidate, `answered-not-reflected` means the user answered but definition failed to carry it forward, `answered-conflicting` means a prior answer exists but the current definition conflicts with it, and `not-applicable` is only for the explicit no-material-risk row. Already answered and reflected decisions are not risk cases. Material risks cannot use `not-applicable` for either `Definition Coverage` or `Prior Answer Check`. If `Prior Answer Check` is `answered-not-reflected` or `answered-conflicting`, the disposition must be `apply-to-definition` or `ask-follow-up`. For every material risk, `Risk Case` explains the risk and `Suggested Handling` must contain at least two labeled resolution options such as `Option 1:` and `Option 2:` so the user can answer it like a clarification question. Allowed categories are `scope`, `acceptance`, `policy-data`, `failure-recovery`, `regression`, `integration`, `user-flow`, `security-privacy`, and `implementation-readiness`. Allowed dispositions are `apply-to-definition`, `ask-follow-up`, `out-of-scope`, `accepted-risk`, `duplicate`, and `not-applicable`; `accepted-risk` requires explicit user acceptance of a real residual risk, not a statement that the item was already decided.

## goal.md

`goal.md` is required only for `02-implementation-plan` and `03-implementation`. Normal `01-definition` clarification does not use `create_goal`; the stop-signal transition-risk audit is the only exception and is recorded as `transition-risk-goal.md`, not `goal.md`. For later stages, `goal.md` records the goal handoff for that stage artifact, not the whole request.

```md
# Goal

Stage: implementation-plan

Artifact Path: `02-implementation-plan/implementation-plan.md`

Artifact Fingerprint: sha256:<artifact-fingerprint>

## Goal Invocation

Tool: create_goal

Invocation recorded: yes

Invocation result: goal created

## Goal Objective

Advance this later-stage artifact to the next required approval gate.

## Goal Tool Status

Goal created: yes

Goal status: active
```

Required values:

- `Stage` must match the folder phase.
- `Artifact Fingerprint` must be the SHA-256 of the current stage artifact bytes.
- `Tool: create_goal`, `Invocation recorded: yes`, and `Goal created: yes` are required.
- `Goal status` must be active, in progress, complete, completed, or another non-pending success state.

## review.md

Every stage has one `review.md`. Use it as a compact review cycle ledger.

```md
# Review

Stage: definition

Reviewed Artifact Fingerprint: sha256:<artifact-fingerprint>

## Review Method

Subagent review.

## Reviewer

reviewer subagent

## Review Cycle

| Cycle | Reviewer | Result | Notes |
| --- | --- | --- | --- |
| 1 | reviewer subagent | PASS | No blocking issues. |

## Writing And Review Rule Checklist

| Rule ID | Evidence Read | Verdict | Blocking Issue |
| --- | --- | --- | --- |
| DEF-RULE-001 | Project context and definition were checked. | PASS | None |

## Latest Verdict

PASS

## Blocking Issues

No blocking issues

## Final Verdict

No blocking issues.
```

A passing review requires:

- `Subagent review.` in `## Review Method`.
- A reviewed artifact fingerprint matching the current stage artifact.
- `## Writing And Review Rule Checklist` containing every Rule ID from the matching stage rule file.
- `PASS` for each required Rule ID in the checklist.
- No blocking issue for each required Rule ID in the checklist.
- `PASS` as the latest verdict.
- No blocking issues.
- A final verdict confirming no blocking issues.

Self-review never satisfies the gate.

## approval.md

Every stage has one `approval.md`. It records the user's explicit approval for that stage only.

```md
# Approval

Stage: definition

Stage approved: yes

Approved By: user

Approved At: 2026-06-21T03:00:00Z

## Approval Text

Approved.
```

Approval text must contain a positive approval intent such as `approve`, `approved`, `go ahead`, `proceed`, `yes`, `승인`, or `진행`. Negative approval text fails validation.

## Validator Templates

The validator is bundled with the Stageflow plugin. Run it from the plugin root, and pass `--root <target-project-root>` when validating a target project rather than assuming that project has its own validator script.

The validator can print starter templates:

```powershell
python <plugin-root>/scripts/validate_stageflow.py --print-template stage-tree
python <plugin-root>/scripts/validate_stageflow.py --print-template goal  # implementation-plan/implementation only
python <plugin-root>/scripts/validate_stageflow.py --print-template definition
python <plugin-root>/scripts/validate_stageflow.py --print-template implementation-plan
python <plugin-root>/scripts/validate_stageflow.py --print-template implementation
python <plugin-root>/scripts/validate_stageflow.py --print-template review
python <plugin-root>/scripts/validate_stageflow.py --print-template approval
```

Validate a target project with:

```powershell
python <plugin-root>/scripts/validate_stageflow.py --root <target-project-root> --current --session-id <session-id> --phase <phase>
```
