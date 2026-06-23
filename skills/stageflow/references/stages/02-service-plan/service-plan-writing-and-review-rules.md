# Service Plan Writing And Review Rules

## Stage Artifact

Target: `02-service-plan/service-plan.md`

## Stage Responsibility

The service-plan stage reorganizes approved requirements into a coherent normal behavior model. It does not collect new requirements and it does not assign code edits. It explains how the service should behave, how state changes, what policies apply, how failures recover, and what regressions must be prevented.

The service plan may mention integration flow and data responsibilities when they are necessary to explain behavior. It must not design TypeScript interfaces, file changes, or implementation-specific API client work.

## Request Type Profiles

Use the approved request profile from requirements as guidance:

- Feature-heavy items become user flows, state transitions, and service policies.
- Bugfix-heavy items become corrected normal behavior, regression prevention conditions, and failure handling.
- Mixed items must preserve the problem-to-requirement mapping by explaining how the new normal behavior resolves the current problem.

## Normal Behavior Transformation

The service plan must transform requirements into behavior, not repeat requirements rows under a new heading. It should read like the service's approved operating model: what users do, what the system accepts or rejects, what state changes, what policies apply, what happens on failure, and what must not regress.

For bugfix or mixed requests, every material `Current Problems` row from requirements must appear as a corrected normal behavior, a regression prevention condition, or both. If the service plan cannot explain how the problem is resolved, the stage is not ready.
## Service Clarification Loop

After reading approved requirements, do not close the service plan by deciding that the behavior model is "clear enough" on the agent's own judgment. Ask concrete service-behavior questions that refine normal behavior, user/system flow, state and policy, integration responsibility, boundaries, regression prevention, and failure recovery until the user explicitly chooses to move to implementation planning.

A service clarification round may contain one question or a batch of multiple questions. Record unanswered active questions in `## Pending Clarifications`; each pending row must include a concrete service-behavior question, at least two meaningful proposal options, a recommended option, the explicit `구현 계획으로 넘어가기` transition option, why the answer matters, and Status `pending` or `awaiting`. After presenting a pending clarification batch, complete the Codex goal with `Goal completion reason: awaiting user clarification`, then stop and wait for the user. Do not run review, approval, next-stage work, or mark the goal blocked merely because the user has not answered yet.

If the user asks a follow-up about a pending option, answer that follow-up first, then restate every still-pending service question with its options and stop again. Do not create a new question ID just to repeat the same pending question.

If the user answers only part of a batch, update the relevant normal behavior model, user flow, state/policy model, policy rule, integration responsibility, boundary, regression prevention, or failure recovery section for the answered items, move those answers into `## Clarification History`, and keep the unanswered items in `## Pending Clarifications`. If the user selects `구현 계획으로 넘어가기` while pending questions remain, explicitly confirm whether the user wants to proceed with the current documented defaults for the remaining questions; the transition option must not silently adopt a proposal.

## Stage Artifact Format

```md
# Service Plan

## Normal Behavior Model

Describe the corrected or desired service behavior as an organized model.

## User Flow

Describe what the user or system does, sees, and receives in order.

## State And Policy Model

Describe states, transitions, permissions, validation rules, and product policies.

## Pending Clarifications

| ID | Question | Options | Recommended Option | Transition Option | Why This Matters | Status |
| --- | --- | --- | --- | --- | --- | --- |
| PENDING-000 | No pending clarification. | N/A | N/A | N/A | N/A | none |

## Clarification History

| Round ID | Questions Asked | User Response | Implementation Plan Option Offered | User Transition Signal | Reflected In |
| --- | --- | --- | --- | --- | --- |
| SVC-CLAR-001 | Which service behavior should the plan capture? Options: Proposal 1, Proposal 2, 구현 계획으로 넘어가기. | User selected a proposal or `구현 계획으로 넘어가기`. | yes | 구현 계획으로 넘어가기 | SP-001 or N/A |

## Policy Rules

| Rule ID | Trigger Or Condition | Policy | User/System Response | State/Data Responsibility | Failure/Recovery Behavior | Source Requirement IDs |
| --- | --- | --- | --- | --- | --- | --- |
| SP-001 | A relevant condition occurs. | The service follows the approved behavior. | The user or system sees the planned response. | State or data responsibility is described. | Recovery behavior is described. | REQ-001 |

## Integration Flow And Data Responsibilities

Describe service-level integration sequence and data responsibilities only where needed for behavior.

## Boundaries

Describe in-scope and out-of-scope behavior.

## Regression Prevention

Describe bugfix or mixed-request behaviors that must not regress.

## Failure And Recovery Behavior

Describe errors, empty states, permissions, validation failures, and recovery behavior.
```

## Required Artifact Sections

- `## Normal Behavior Model`
- `## User Flow`
- `## State And Policy Model`
- `## Pending Clarifications`
- `## Clarification History`
- `## Policy Rules`
- `## Integration Flow And Data Responsibilities`
- `## Boundaries`
- `## Regression Prevention`
- `## Failure And Recovery Behavior`

## Writing And Review Rule Table

| Rule ID | Writing Rule | Required Artifact Evidence | Review Check | Blocking Condition |
| --- | --- | --- | --- | --- |
| SP-RULE-001 | Reorganize approved requirements into a normal behavior model instead of repeating the requirements list. | `## Normal Behavior Model` explains corrected or desired behavior in service terms. | Confirm the artifact has a coherent model that a service/product reviewer can understand. | The artifact mostly repeats requirements rows without a normal behavior model. |
| SP-RULE-002 | Describe the user or system flow at behavior level. | `## User Flow` states visible states, actions, and outcomes. | Confirm user-facing behavior is understandable without code-level instructions. | User-visible behavior is missing or hidden behind implementation terms. |
| SP-RULE-003 | Convert meaningful behavior into explicit policy rules. | `## Policy Rules` table has `Rule ID`, `Trigger Or Condition`, `Policy`, `User/System Response`, `State/Data Responsibility`, `Failure/Recovery Behavior`, and `Source Requirement IDs` columns. | Confirm every material behavior has a policy, response, state/data responsibility, recovery behavior, and requirement trace. | A behavior is described without a concrete policy rule. |
| SP-RULE-004 | Manage service clarification batches without losing pending questions. | `## Pending Clarifications` records unanswered service questions with concrete questions, proposal options, recommended option, transition option, rationale, and status; `## Clarification History` records answered items and transition choices. | Confirm the agent stops after asking, answers follow-up questions by restating still-pending questions/options, does not repeat the same pending question as a new round, and does not close service planning without a user transition choice. | Pending service clarifications are missing their question/options, the agent keeps running review/approval while waiting for an answer, a follow-up answer omits the still-pending choices, a pending question is duplicated as a new round, a proposal answer is not reflected, or service planning is closed without a user transition choice. |
| SP-RULE-005 | Keep integration flow and data responsibilities at service level. | `## Integration Flow And Data Responsibilities` describes relevant sequence and data responsibilities without file lists, type definitions, or code edits. | Confirm the plan explains how behavior moves through integrations only where needed. | Flow is absent when required, or it contains implementation file/type instructions. |
| SP-RULE-006 | Define boundaries and exclusions. | `## Boundaries` states in-scope and out-of-scope behavior. | Confirm the service plan prevents scope expansion during implementation planning. | Boundaries are missing or conflict with approved requirements. |
| SP-RULE-007 | Define regression prevention for bugfix or mixed requests. | `## Regression Prevention` lists behaviors, invariants, or problem resolutions that must keep working. | Confirm current problems from requirements are addressed as corrected behavior or prevention conditions. | A problem from requirements has no normal-behavior or regression-prevention coverage. |
| SP-RULE-008 | Define failure, empty, permission, validation, and exception recovery behavior. | `## Failure And Recovery Behavior` covers relevant failure and recovery cases. | Confirm expected non-happy-path behavior is reviewable. | Failure or recovery behavior is omitted for a material policy. |
| SP-RULE-009 | Do not introduce new requirements or implementation decisions. | Service rules trace back to approved requirement IDs and avoid unapproved product decisions. | Confirm the service plan organizes approved requirements but does not invent scope. | The service plan adds a new user requirement, UX policy, endpoint meaning, or implementation decision not grounded in requirements. |

## Repetition And Regression Review Triggers

FAIL the service-plan review when requirements rows are repeated as a new table without synthesis into `## Normal Behavior Model`, `## User Flow`, `## State And Policy Model`, and `## Regression Prevention`.

FAIL the service-plan review when a bugfix or mixed request lacks an explicit problem resolution model or regression model showing how `Current Problems` are resolved and prevented from recurring.

## Forbidden Content

Do not include implementation file lists, code edit instructions, TypeScript/interface design, test command details, or newly invented requirements in the service plan. When those details are user-specified or discovered constraints, preserve them only as service-level integration constraints and trace them back to requirements.
