# Definition Writing And Review Rules

## Stage Artifact

Target: `01-definition/definition.md`

## Stage Responsibility

The definition stage combines requirements and service behavior into one approved artifact. It captures the user's goal, current problems, outcomes, constraints, decisions, requirements, acceptance criteria, normal behavior model, policy rules, boundaries, regression prevention, and failure recovery before implementation planning begins.

The definition may include technical constraints when supplied by the user or discovered through project inspection, but it must not assign code edits, TypeScript interfaces, file changes, or implementation work.

## Request Type Profiles

Record request shape as profile tags, not as a single exclusive type. Use `Primary` and optional `Secondary` values such as `feature`, `bugfix`, `feature-adjustment`, `refactor`, `docs`, or `tooling`.

- Feature-heavy requests emphasize desired outcomes, success criteria, normal behavior, user flow, and service policies.
- Bugfix-heavy requests emphasize current problems, expected-versus-actual behavior, corrected normal behavior, regression prevention, and validation needs.
- Mixed requests must include both desired outcomes and current problems, then connect them through requirements and service policy rules.

## Clarification Loop

After project inspection, do not close definition by deciding that the intent or behavior model is "clear enough" on the agent's own judgment. Ask concrete clarification questions that refine user intent, scope, success criteria, constraints, normal behavior, user/system flow, state and policy, integration responsibility, boundaries, regression prevention, and failure recovery until the user explicitly chooses to move to implementation planning.

A clarification round may contain one question or a batch of multiple questions. Record unanswered active questions in `## Pending Clarifications`; each pending row must include a concrete question, at least two meaningful proposal options, a recommended option, the explicit `구현 계획으로 넘어가기` transition option, why the answer matters, and Status `pending` or `awaiting`. After presenting a pending clarification batch, complete the Codex goal with `Goal completion reason: awaiting user clarification`, then stop and wait for the user. Do not run review, approval, next-stage work, or mark the goal blocked merely because the user has not answered yet.

If the user asks a follow-up about a pending option, answer that follow-up first, then restate every still-pending question with its options and stop again. Do not create a new question ID just to repeat the same pending question.

## Blocking Question Criteria

Mark an open question as blocking when its answer can change screen flow, authentication, authorization, payment, security, privacy, API responsibility, integration responsibility, data source responsibility, copied-project parity, scope, rollout boundary, acceptance criteria, validation method, service policy, failure recovery, or regression prevention.

Questions outside those criteria may be non-blocking only when the recommended option is safe to carry forward and the impact of deferring the decision is documented.

## Open Question Writing Rules

Each open question must be written as a decision request, not a vague concern. It must include the decision needed, context or conflict, recommended option, alternatives, impact, blocking status, and resolution target. The resolution target names where the answer will be reflected, such as `REQ-002`, `SP-001`, `Boundary`, `Acceptance Criteria`, or `Failure And Recovery Behavior`.

## Open Question Resolution Rules

When the user answers an open question, add a `Resolved Decisions` row with the question ID, answer source, decision, and reflected artifact area. Also update the target requirement, policy rule, constraint, boundary, or acceptance criteria. If a row is updated from the answer, its source must include `User answer to Q-###` or `User answer to CLAR-###`.

## Late Feedback And Redefinition

If implementation feedback shows that the approved definition is wrong, return to the definition stage and update only the affected definition content. Record the correction in `## Resolved Decisions`, update the affected `## Requirements`, `## Policy Rules`, `## Acceptance Criteria`, boundaries, or data responsibilities, and preserve later-stage artifacts as reference material until their impact is judged.

Do not automatically invalidate the implementation plan or implementation record. First decide whether each downstream work item still matches the revised definition, needs a partial update, needs a full rewrite, or belongs in a new request. Definition revisions must make that decision possible by clearly identifying which requirements or policy rules changed.


## Normal Behavior Transformation

The definition must transform requirements into behavior, not repeat requirement rows under a new heading. It should read like the service's approved operating model: what users do, what the system accepts or rejects, what state changes, what policies apply, what happens on failure, and what must not regress.

For bugfix or mixed requests, every material `Current Problems` row must appear as a corrected normal behavior, a regression prevention condition, or both. If the definition cannot explain how the problem is resolved, the stage is not ready.

## Stage Artifact Format

```md
# Definition

## User Goal

Describe the user's goal in their language.

## Request Profile

Primary: feature
Secondary: none

## Desired Outcomes

| ID | Outcome | Source | Success Signal |
| --- | --- | --- | --- |
| OUT-001 | The requested result is visible or verifiable. | User request. | A reviewer can confirm the outcome. |

## Current Problems

| ID | Problem | Expected Behavior | Actual Behavior | Evidence Or Reproduction | Impact |
| --- | --- | --- | --- | --- | --- |
| PROB-001 | No current problem identified. | N/A | N/A | N/A | N/A |

## Problem-To-Requirement Mapping

| Problem ID | Requirement ID | Resolution |
| --- | --- | --- |
| PROB-001 | REQ-001 | The requirement resolves or prevents the problem. |

## User-Specified Constraints

- Constraint explicitly supplied by the user, or `None specified.`

## Discovered Constraints

- Constraint discovered during project inspection, or `None discovered.`

## Pending Clarifications

| ID | Question | Options | Recommended Option | Transition Option | Why This Matters | Status |
| --- | --- | --- | --- | --- | --- | --- |
| PENDING-000 | No pending clarification. | N/A | N/A | N/A | N/A | none |

## Clarification History

| Round ID | Questions Asked | User Response | Implementation Plan Option Offered | User Transition Signal | Reflected In |
| --- | --- | --- | --- | --- | --- |
| CLAR-001 | Which concrete definition should this request use? Options: Proposal 1, Proposal 2, 구현 계획으로 넘어가기. | User selected a proposal or `구현 계획으로 넘어가기`. | yes | 구현 계획으로 넘어가기 | REQ-001, SP-001, or N/A |

## Open Questions

| ID | Decision Needed | Context Or Conflict | Recommended Option | Alternatives | Impact | Blocking | Resolution Target |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q-001 | No open question. | N/A | N/A | N/A | N/A | no | N/A |

## Resolved Decisions

| ID | Source Question ID | Answer Source | Decision | Reflected In |
| --- | --- | --- | --- | --- |
| DEC-001 | N/A | N/A | No resolved decision yet. | N/A |

## Requirements

| ID | Type | Source | Requirement Detail | Boundary Or Exclusion | Linked Outcomes Or Problems |
| --- | --- | --- | --- | --- | --- |
| REQ-001 | feature | User request. | One concrete requirement. | Out-of-scope behavior is explicit. | OUT-001 |

## Acceptance Criteria

- `REQ-001` is satisfied when the linked outcome or problem resolution is verifiable.

## Normal Behavior Model

Describe the corrected or desired service behavior as an organized model.

## User Flow

Describe what the user or system does, sees, and receives in order.

## State And Policy Model

Describe states, transitions, permissions, validation rules, and product policies.

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

- `## User Goal`
- `## Request Profile`
- `## Desired Outcomes`
- `## Current Problems`
- `## Problem-To-Requirement Mapping`
- `## User-Specified Constraints`
- `## Discovered Constraints`
- `## Pending Clarifications`
- `## Clarification History`
- `## Open Questions`
- `## Resolved Decisions`
- `## Requirements`
- `## Acceptance Criteria`
- `## Normal Behavior Model`
- `## User Flow`
- `## State And Policy Model`
- `## Policy Rules`
- `## Integration Flow And Data Responsibilities`
- `## Boundaries`
- `## Regression Prevention`
- `## Failure And Recovery Behavior`

## Writing And Review Rule Table

| Rule ID | Writing Rule | Required Artifact Evidence | Review Check | Blocking Condition |
| --- | --- | --- | --- | --- |
| DEF-RULE-001 | Inspect the project before asking implementation-affecting questions. | `## User Goal`, `## Discovered Constraints`, requirement rows, or policy rows mention discovered project context when it affects the request. | Confirm the definition is grounded in the existing project instead of only chat assumptions. | Definition ignores relevant discovered project constraints. |
| DEF-RULE-002 | Record request type as primary and optional secondary profile tags. | `## Request Profile` records `Primary:` and `Secondary:` values. | Confirm the request can be treated as feature, bugfix, mixed, refactor, docs, or tooling without forcing an exclusive type. | Request shape is absent or incorrectly collapses a mixed request into one exclusive type. |
| DEF-RULE-003 | Capture desired outcomes and current problems separately. | `## Desired Outcomes` and `## Current Problems` contain reviewable rows, using `N/A` only when a side is genuinely absent. | Confirm user goals and bug/problem facts are not merged into one vague requirement list. | A mixed request lacks either desired outcomes or current problems. |
| DEF-RULE-004 | Link problems to resolving requirements and service behavior. | `## Problem-To-Requirement Mapping`, `## Requirements`, `## Normal Behavior Model`, and `## Regression Prevention` connect material problems to resolution. | Confirm each current problem has a stated requirement and corrected/prevented behavior. | A material problem has no linked requirement, behavior model, or regression prevention. |
| DEF-RULE-005 | Capture each implementation-affecting requirement as a sourced, verifiable row. | `## Requirements` has `ID`, `Type`, `Source`, `Requirement Detail`, `Boundary Or Exclusion`, and `Linked Outcomes Or Problems` columns. | Confirm every requirement has a source, concrete detail, boundary, and trace to outcomes or problems. | A requirement cannot be reviewed because source, detail, boundary, or trace is missing. |
| DEF-RULE-006 | Keep user-specified and discovered technical constraints visible without inventing implementation decisions. | `## User-Specified Constraints` and `## Discovered Constraints` separate explicit user constraints from project inspection facts. | Confirm supplied or discovered files, endpoints, commands, screens, or reference systems are retained without promoting model guesses to requirements. | User-specified technical constraints are dropped, or inferred implementation decisions are recorded as requirements without source. |
| DEF-RULE-007 | Manage clarification batches without losing pending questions. | `## Pending Clarifications` and `## Clarification History` record concrete questions, options, recommended option, `구현 계획으로 넘어가기`, user responses, and reflected areas. | Confirm the agent stops while pending, restates still-pending choices after follow-ups, and does not close definition without a user transition choice. | Pending clarifications are incomplete, duplicated, hidden after follow-up, or definition closes without the implementation-plan transition choice. |
| DEF-RULE-008 | Write open questions as actionable decision records. | `## Open Questions` has `ID`, `Decision Needed`, `Context Or Conflict`, `Recommended Option`, `Alternatives`, `Impact`, `Blocking`, and `Resolution Target` columns. | Confirm each question states the decision, context, recommendation, alternatives, impact, blocking status, and where the answer will be applied. | A question lacks recommendation, alternative, impact, blocking status, or resolution target, or is only a vague concern. |
| DEF-RULE-009 | Trace resolved user answers into definition content. | `## Resolved Decisions` records answered question or clarification IDs, answer source, decision, and reflected artifact area; updated rows cite user answers when applicable. | Confirm user answers are not lost and can be traced to requirements, policies, constraints, boundaries, or acceptance criteria. | A user answer exists but is not represented in decision history or a relevant updated row source. |
| DEF-RULE-010 | Keep acceptance criteria traceable to requirement IDs. | `## Acceptance Criteria` references requirement IDs and linked outcomes or problems. | Confirm acceptance criteria cover the requirement rows. | Acceptance criteria are generic or disconnected from requirement IDs. |
| DEF-RULE-011 | Transform requirements into a normal behavior model instead of repeating the requirements list. | `## Normal Behavior Model`, `## User Flow`, and `## State And Policy Model` explain corrected or desired behavior in service terms. | Confirm the artifact has a coherent model that a service/product reviewer can understand. | Behavior sections mostly repeat requirements rows without a normal behavior model. |
| DEF-RULE-012 | Convert meaningful behavior into explicit policy rules. | `## Policy Rules` table has `Rule ID`, `Trigger Or Condition`, `Policy`, `User/System Response`, `State/Data Responsibility`, `Failure/Recovery Behavior`, and `Source Requirement IDs` columns. | Confirm every material behavior has a policy, response, state/data responsibility, recovery behavior, and requirement trace. | A behavior is described without a concrete policy rule. |
| DEF-RULE-013 | Define integration responsibilities, boundaries, regression prevention, and failure recovery at service level. | `## Integration Flow And Data Responsibilities`, `## Boundaries`, `## Regression Prevention`, and `## Failure And Recovery Behavior` describe service-level behavior without code edit instructions. | Confirm the definition prevents scope expansion and covers non-happy-path behavior. | Boundaries, regression prevention, or failure recovery are missing for material behavior, or implementation details replace service behavior. |
| DEF-RULE-014 | Do not introduce implementation decisions. | Requirements, policy rules, and behavior sections avoid file lists, type definitions, code edits, and test command details unless recorded as constraints. | Confirm definition organizes approved behavior but leaves implementation design to the implementation-plan stage. | The definition assigns implementation work or creates code-level decisions not supplied by the user or discovered constraints. |

## Verification Meaning

A definition is ready for implementation planning when the reviewer can identify what the user wants, what problem it resolves when applicable, where each requirement came from, what behavior and policies are approved, what is out of scope, whether user answers were carried forward, whether the user chose `구현 계획으로 넘어가기`, and whether any behavior-changing question remains blocking.
