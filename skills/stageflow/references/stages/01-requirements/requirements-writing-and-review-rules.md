# Requirements Writing And Review Rules

## Stage Artifact

Target: `01-requirements/requirements.md`

## Stage Responsibility

The requirements stage expands and lists the user's request. It captures desired outcomes, current problems, explicit constraints, discovered constraints, resolved decisions, and open questions before any service model or implementation plan is approved.

Requirements may include technical details when the user supplied them or project inspection discovered them. The artifact must keep those details tied to their source instead of turning model guesses into approved requirements.

## Request Type Profiles

Record request shape as profile tags, not as a single exclusive type. Use `Primary` and optional `Secondary` values such as `feature`, `bugfix`, `feature-adjustment`, `refactor`, `docs`, or `tooling`.

- Feature-heavy requests emphasize desired outcomes and success criteria.
- Bugfix-heavy requests emphasize current problems, expected-versus-actual behavior, reproduction context, impact, and regression prevention needs.
- Mixed requests must include both desired outcomes and current problems, then connect them in `Problem-To-Requirement Mapping`.

## Clarification Loop

After project inspection, do not close requirements by deciding that the intent is "clear enough" on the agent's own judgment. Ask concrete clarification questions that refine user intent, scope, success criteria, constraints, and tradeoffs until the user explicitly chooses to move to service planning.

A clarification round may contain one question or a batch of multiple questions. Record unanswered active questions in `## Pending Clarifications`; each pending row must include a concrete question, at least two meaningful proposal options, a recommended option, the explicit `서비스 계획으로 넘어가기` transition option, why the answer matters, and Status `pending` or `awaiting`. After presenting a pending clarification batch, stop and wait for the user. Do not run review, approval, next-stage work, or mark the goal blocked merely because the user has not answered yet.

If the user asks a follow-up about a pending option, answer that follow-up first, then restate every still-pending question with its options and stop again. Do not create a new question ID just to repeat the same pending question.

If the user answers only part of a batch, update the relevant desired outcome, current problem, requirement, constraint, boundary, or acceptance criteria for the answered items, move those answers into `## Clarification History` and `## Resolved Decisions`, and keep the unanswered items in `## Pending Clarifications`. If the user selects `서비스 계획으로 넘어가기` while pending questions remain, explicitly confirm whether the user wants to proceed with the current documented defaults for the remaining questions; the transition option must not silently adopt a proposal.

## Blocking Question Criteria

Mark an open question as blocking when its answer can change any of these:

- Screen flow or navigation.
- Authentication, authorization, payment, security, or privacy behavior.
- API, integration, or data source responsibility.
- Reference-project parity or intentional difference from a copied project.
- Scope, exclusions, or rollout boundary.
- Acceptance criteria or success signal.
- Validation, test, or review method.

Questions outside those criteria may be non-blocking only when the recommended option is safe to carry forward and the impact of deferring the decision is documented.

## Open Question Writing Rules

Each open question must be written as a decision request, not a vague concern. It must include the decision needed, context or conflict, recommended option, alternatives, impact, blocking status, and resolution target. The resolution target names where the answer will be reflected, such as `REQ-002`, `Boundary`, `Acceptance Criteria`, or `Discovered Constraints`.

## Open Question Resolution Rules

When the user answers an open question, add a `Resolved Decisions` row with the question ID, answer source, decision, and reflected artifact area. Also update the target requirement, constraint, boundary, or acceptance criteria. If a requirement row is updated from the answer, its `Source` must include `User answer to Q-###`.

## Stage Artifact Format

```md
# Requirements

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

| Round ID | Questions Asked | User Response | Service Plan Option Offered | User Transition Signal | Reflected In |
| --- | --- | --- | --- | --- | --- |
| CLAR-001 | Which concrete direction should requirements capture? Options: Proposal 1, Proposal 2, 서비스 계획으로 넘어가기. | User selected a proposal or `서비스 계획으로 넘어가기`. | yes | 서비스 계획으로 넘어가기 | REQ-001 or N/A |

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

## Writing And Review Rule Table

| Rule ID | Writing Rule | Required Artifact Evidence | Review Check | Blocking Condition |
| --- | --- | --- | --- | --- |
| REQ-RULE-001 | Inspect the project before asking implementation-affecting questions. | `## User Goal`, `## Discovered Constraints`, or requirement rows mention discovered project context when it affects the request. | Confirm requirements are grounded in the existing project instead of only chat assumptions. | Requirements ignore relevant discovered project constraints. |
| REQ-RULE-002 | Record request type as primary and optional secondary profile tags. | `## Request Profile` records `Primary:` and `Secondary:` values. | Confirm the request can be treated as feature, bugfix, mixed, refactor, docs, or tooling without forcing an exclusive type. | Request shape is absent or incorrectly collapses a mixed request into one exclusive type. |
| REQ-RULE-003 | Capture desired outcomes and current problems separately. | `## Desired Outcomes` and `## Current Problems` contain reviewable rows, using `N/A` only when a side is genuinely absent. | Confirm user goals and bug/problem facts are not merged into one vague requirement list. | A mixed request lacks either desired outcomes or current problems. |
| REQ-RULE-004 | Link problems to resolving requirements when problems are present. | `## Problem-To-Requirement Mapping` maps each material problem ID to one or more requirement IDs. | Confirm each current problem has a stated required outcome or prevention path. | A material problem has no linked requirement or resolution. |
| REQ-RULE-005 | Capture each implementation-affecting requirement as a sourced, verifiable row. | `## Requirements` has `ID`, `Type`, `Source`, `Requirement Detail`, `Boundary Or Exclusion`, and `Linked Outcomes Or Problems` columns. | Confirm every requirement has a source, concrete detail, boundary, and trace to outcomes or problems. | A requirement cannot be reviewed because source, detail, boundary, or trace is missing. |
| REQ-RULE-006 | Keep user-specified and discovered technical constraints visible without inventing implementation decisions. | `## User-Specified Constraints` and `## Discovered Constraints` separate explicit user constraints from project inspection facts. | Confirm files, endpoints, commands, screens, or reference systems are retained when supplied or discovered, and model guesses are not promoted to requirements. | User-specified technical constraints are dropped, or inferred implementation decisions are recorded as requirements without source. |
| REQ-RULE-007 | Manage clarification batches without losing pending questions. | `## Pending Clarifications` records unanswered question batches with concrete questions, proposal options, recommended option, transition option, rationale, and status; `## Clarification History` records answered items and transition choices. | Confirm the agent stops after asking, answers follow-up questions by restating still-pending questions/options, does not repeat the same pending question as a new round, and does not close requirements without a user transition choice. | Pending clarifications are missing their question/options, the agent keeps running review/approval while waiting for an answer, a follow-up answer omits the still-pending choices, a pending question is duplicated as a new round, a proposal answer is not reflected, or requirements are closed without a user transition choice. |
| REQ-RULE-008 | Write open questions as actionable decision records. | `## Open Questions` has `ID`, `Decision Needed`, `Context Or Conflict`, `Recommended Option`, `Alternatives`, `Impact`, `Blocking`, and `Resolution Target` columns. | Confirm each question states the decision, context, recommendation, alternatives, impact, blocking status, and where the answer will be applied. | A question lacks recommendation, alternative, impact, blocking status, or resolution target, or is only a vague concern. |
| REQ-RULE-009 | Trace resolved user answers into requirements. | `## Resolved Decisions` records answered question or clarification IDs, answer source, decision, and reflected artifact area; updated requirement sources include `User answer to Q-###` or `User answer to CLAR-###` when applicable. | Confirm user answers are not lost and can be traced to requirements, constraints, boundaries, or acceptance criteria. | A user answer exists but is not represented in `## Resolved Decisions`, `## Clarification History`, or a relevant requirement `Source`. |
| REQ-RULE-010 | Keep acceptance criteria traceable to requirement IDs. | `## Acceptance Criteria` references requirement IDs and linked outcomes or problems. | Confirm acceptance criteria cover the requirement rows. | Acceptance criteria are generic or disconnected from requirement IDs. |

## Verification Meaning

A requirement is ready for service planning when the reviewer can identify what the user wants, what problem it resolves when applicable, where the requirement came from, what is out of scope, whether user answers were carried forward, whether the user chose `서비스 계획으로 넘어가기`, and whether any behavior-changing question is still blocking.
