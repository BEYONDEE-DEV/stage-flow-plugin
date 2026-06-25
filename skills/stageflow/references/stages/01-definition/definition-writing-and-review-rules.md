# Definition Writing And Review Rules

## Stage Artifact

Target: `01-definition/definition.md`

## Stage Responsibility

The definition stage combines requirements and service behavior into one approved artifact. It captures the user's goal, purpose and intent, current problems, outcomes, constraints, decisions, requirements, acceptance criteria, normal behavior model, policy rules, boundaries, regression prevention, and failure recovery before implementation planning begins.

The definition may include technical constraints when supplied by the user or discovered through project inspection, but it must not assign code edits, TypeScript interfaces, file changes, or implementation work.

## Request Type Profiles

Record request shape as profile tags, not as a single exclusive type. Use `Primary` and optional `Secondary` values such as `feature`, `bugfix`, `feature-adjustment`, `refactor`, `docs`, or `tooling`.

- Feature-heavy requests emphasize desired outcomes, success criteria, normal behavior, user flow, and service policies.
- Bugfix-heavy requests emphasize current problems, expected-versus-actual behavior, corrected normal behavior, regression prevention, and validation needs.
- Mixed requests must include both desired outcomes and current problems, then connect them through requirements and service policy rules.

## Clarification Loop

After project inspection, assume there are still ambiguities to clarify. Do not first decide whether ambiguity exists; behave as if it does, find the next useful definition question batch, and ask it. Ask breadth-first: start with 큰방향 questions, keep asking 큰방향 questions while 큰방향 ambiguities remain, and move to 주요결정 or 세부확인 questions only when `## Clarification History` or `## Resolved Decisions` records that the previous question scope has been sufficiently covered or that the user agreed to move deeper. Purpose is mandatory 큰방향 coverage: if `## Purpose And Intent` is `unknown` or `inferred`, the active pending batch must include at least one purpose-focused 큰방향 question before asking only 주요결정/세부확인 questions.

Question scope is based on answer impact:

- `큰방향`: the answer can change request identity, purpose/intent, top-level scope, target user/system surface, desired outcomes, current problem framing, or explicit boundaries. It can revise at the 큰방향 level `User Goal`, `Purpose And Intent`, `Request Profile`, `Desired Outcomes`, `Current Problems`, `Requirements`, or `Boundaries`.
- `주요결정`: the answer stays inside the approved 큰방향 scope but can change major behavior areas, user/system flow, state model, policy groups, integration responsibility, or data responsibility. It can revise `Normal Behavior Model`, `User Flow`, `State And Policy Model`, `Policy Rules`, or `Integration Flow And Data Responsibilities`.
- `세부확인`: the answer stays inside an approved behavior or policy direction and refines acceptance criteria, copy/text, fallback behavior, error handling, recovery behavior, validation method, or regression checks. It can revise `Acceptance Criteria`, specific `Policy Rules`, `Failure And Recovery Behavior`, or `Regression Prevention`.

After every user answer, reflect the answer into the appropriate definition rows, then create or maintain the next concrete clarification batch with 1-5 active questions. The agent must not close definition by judging the request or behavior model `clear enough`, `충분함`, or complete on its own authority. The loop ends only when the user explicitly gives a stop signal such as `구현 계획으로 넘어가기`, `질문 그만`, `충분해`, `진행`, `승인`, `proceed`, or `go ahead`.

Record unanswered active questions in `## Pending Clarifications`; before a user stop signal exists, this table must contain 1-5 active question rows. Each active row must include `Question Scope` (`큰방향`, `주요결정`, or `세부확인`), at least two explicit labeled proposal options such as `Option 1:` and `Option 2:`, a recommended option, user-facing context for why the question is being asked, why the answer matters, the definition area the answer will update, and Status `pending` or `awaiting`. `Why This Matters` must not be generic; it should say whether the answer changes scope, purpose, behavior, user flow, data responsibility, validation, policy, failure recovery, or regression prevention, and what wrong planning choice it prevents. `Option 3:` and higher are allowed. `구현 계획으로 넘어가기` is not a proposal option and must not be included inside the `Options` cell; it is only a user-authored stop signal recorded in `## Clarification History`. Do not write a pending question with only one recommendation, an unlabeled suggestion, unexplained internal terminology, or prose-only guidance. After presenting a pending clarification batch, stop and wait for the user. Do not create or complete a Codex goal for definition, run review, approval, next-stage work, or mark the goal blocked merely because the user has not answered yet.

If the user asks a follow-up about a pending option, the main response answers that follow-up first, then restates every still-pending question with its explicit labeled options and stops again. During this wait, a question-generation subagent may run in parallel to prepare optional `01-definition/question-backlog.md` candidates, limited to future candidate questions. When the user answers, judge answer impact against the backlog: reuse unaffected candidates as the next pending batch, revise partially affected candidates, or regenerate the backlog when the answer invalidates it.


## User-Facing Question Presentation

When returning a pending clarification batch to the user, render the table rows as understandable decisions rather than raw artifact maintenance. Use this order by default: current context, decision needed, labeled options, recommended option, why the answer matters, and where the answer will be reflected. If showing `큰방향`, `주요결정`, or `세부확인`, include a short plain-language explanation of the label in the user's language.

Each question should make the tradeoff visible. For example, say that a scope answer will update `## Boundaries` and prevent the implementation plan from including adjacent behavior, or that a validation answer will update `## Acceptance Criteria` and prevent the plan from choosing the wrong evidence source. Do not ask context-free questions such as "Which validation boundary should definition capture?" unless the preceding sentence explains the current request context and why that boundary is unresolved.

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

## Intent Fidelity Guard

Read `references/intent-fidelity.md` when user wording could be narrowed into UX, route, screen, state, data, API, or persistence behavior. Definition must preserve user meaning in `## Intent Fidelity` before expanding it into requirements, acceptance criteria, user flow, policy rules, failure recovery, or boundaries.

## Stage Artifact Format

```md
# Definition

## User Goal

Describe the user's goal in their language.

## Purpose And Intent

| Purpose | User Value | Business/Product Value | Source | Confidence |
| --- | --- | --- | --- | --- |
| The purpose still needs user confirmation. | Clarifies why the result matters to the user. | Clarifies product or workflow value before planning. | user request needs clarification | unknown |

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

| ID | Question Scope | Question | Options | Recommended Option | Transition Option | Why This Matters | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PENDING-001 | 큰방향 | 현재 목적은 아직 확인되지 않았습니다. 이 변경이 우선 달성해야 할 목적은 무엇인가요? | Option 1: solve the immediate workflow problem the user raised; Option 2: create reusable product flexibility for follow-up changes | Option 1 | N/A | 이 답변은 `Purpose And Intent`와 `Desired Outcomes`에 반영되어 이후 범위와 검증 기준의 기준점이 됩니다. | pending |
| PENDING-002 | 큰방향 | 현재 요청 범위가 핵심 변경에만 머물지, 인접 동작까지 포함할지 열려 있습니다. 상위 범위는 어디까지로 잡을까요? | Option 1: narrow the request boundary to the directly requested behavior; Option 2: include adjacent behavior that would otherwise be affected later | Option 1 | N/A | 이 답변은 `Requirements`와 `Boundaries`에 반영되어 구현 계획이 불필요한 인접 동작까지 포함하지 않도록 합니다. | pending |
| PENDING-003 | 큰방향 | 현재 영향 대상이 사용자 화면/경험인지 내부 workflow인지 아직 확정되지 않았습니다. 주된 적용 표면은 무엇인가요? | Option 1: user-facing behavior; Option 2: internal workflow behavior; Option 3: both user-facing and internal behavior | Option 1 | N/A | 이 답변은 `User Flow`, `Normal Behavior Model`, `Policy Rules`에 반영되어 이후 동작 질문의 기준을 정합니다. | pending |

## Clarification History

| Round ID | Questions Asked | User Response | Implementation Plan Option Offered | User Transition Signal | Reflected In |
| --- | --- | --- | --- | --- | --- |
| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |

## Open Questions

| ID | Decision Needed | Context Or Conflict | Recommended Option | Alternatives | Impact | Blocking | Resolution Target |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q-001 | No open question. | N/A | N/A | N/A | N/A | no | N/A |

## Resolved Decisions

| ID | Source Question ID | Answer Source | Decision | Reflected In |
| --- | --- | --- | --- | --- |
| DEC-001 | N/A | N/A | No resolved decision yet. | N/A |

## Intent Fidelity

| ID | User Wording | Normalized Requirement | Allowed Interpretations | Disallowed Interpretations | Linked Requirement/Policy |
| --- | --- | --- | --- | --- | --- |
| INTENT-001 | User's exact or faithfully summarized wording. | Requirement meaning preserved from the user wording. | Interpretations explicitly supported by user answers or resolved decisions. | Narrower, broader, or technical interpretations that are not approved. | REQ-001, SP-001 |

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

## Optional Question Backlog

`01-definition/question-backlog.md` is an optional helper artifact prepared by a question-generation subagent in parallel while the main agent waits for the user. It is not a review or approval gate and does not replace `Pending Clarifications`. It should record candidate question ID, question scope, question text, at least two labeled options, affected definition areas, and invalidation triggers. After the user answers, the main agent judges impact and only then promotes unaffected candidates, revises affected candidates, or regenerates the backlog.


## Definition Transition Risk Gate

When the user gives a stop signal such as `구현 계획으로 넘어가기`, definition does not go straight to review or approval. First run the narrow transition-risk goal exception and record `01-definition/transition-risk-goal.md` plus `01-definition/transition-risk.md`. This goal is a goal-achievement decision readiness audit: it checks whether any decision required for the user goal to succeed is still missing, conflicting, or ambiguous before implementation planning. It is not an implementation-plan goal and must not create `01-definition/goal.md`.

`transition-risk-goal.md` must record `Stage: definition`, `Purpose: transition-risk`, `Artifact Path: 01-definition/transition-risk.md`, the current `Definition Artifact Fingerprint`, `Tool: create_goal`, `Invocation recorded: yes`, `Goal created: yes`, and `Goal status: completed`.

`transition-risk.md` must include `## Risk Generation Basis`, `## Generated Risk Cases`, `## Suggested Definition Updates`, `## User Confirmation`, and `## Final Disposition`. The risk table must have `ID`, `Category`, `Risk Case`, `Affected Definition Area`, `Definition Coverage`, `Prior Answer Check`, `Suggested Handling`, `User Confirmation`, and `Disposition`. `Definition Coverage` must be `uncovered`, `conflicting`, `ambiguous`, or `not-applicable`: `uncovered` means a goal-critical decision is missing from definition, `conflicting` means goal-critical decisions conflict inside definition, `ambiguous` means a goal-critical decision can be interpreted multiple ways, and `not-applicable` means the audit found no material decision gap; only the explicit `No material transition risks found` row may use `not-applicable`. `Prior Answer Check` must be `not-answered`, `answered-not-reflected`, `answered-conflicting`, or `not-applicable`: use it to prove the candidate was compared against `Clarification History`, `Resolved Decisions`, `Requirements`, `Acceptance Criteria`, `Policy Rules`, and `Boundaries` before it became a risk row. `not-applicable` is only for the explicit no-material-risk row. If the user already answered the issue and the definition already reflects it, do not write a risk case; carry that decision into implementation-plan coverage or constraints. If the user answered but the definition failed to reflect it or now conflicts with it, use `answered-not-reflected` or `answered-conflicting` and resolve it with `apply-to-definition` or `ask-follow-up`. Allowed categories are `scope`, `acceptance`, `policy-data`, `failure-recovery`, `regression`, `integration`, `user-flow`, `security-privacy`, and `implementation-readiness`. Allowed dispositions are `apply-to-definition`, `ask-follow-up`, `out-of-scope`, `accepted-risk`, `duplicate`, and `not-applicable`.

Generated risk cases are not automatically requirements, and they are not a place to restate decisions that are already answered by the user and settled in `definition.md`. For each candidate, ask two questions: `이 목표를 달성하려면 이 결정이 definition 단계에서 이미 정해져 있어야 하는가?` and `그 결정이 현재 definition에 없거나, 충돌하거나, 애매한가?` A risk case must expose a required decision the definition does not currently settle, a required decision that conflicts with another definition decision, or a required decision that is ambiguous enough to let implementation planning choose the wrong path. Already-decided requirements, boundaries, policy rules, and already answered/reflected user answers must move to implementation-plan coverage or constraints instead.

When a material risk case is presented to the user, write it in the same user-answerable form as clarification questions: explain the risk in plain language, name the affected definition area, explain why it can block the goal, and put at least two labeled resolution options in `Suggested Handling` such as `Option 1:` and `Option 2:`. Do not use a single recommendation, an unlabeled sentence, or implementation-only TODOs as the handling. If the user confirms `apply-to-definition`, reflect the update in `## Requirements`, `## Acceptance Criteria`, `## Policy Rules`, `## Boundaries`, `## Failure And Recovery Behavior`, or `## Regression Prevention`. If a case needs more input, use `ask-follow-up` and restore active `Pending Clarifications`. If the user explicitly accepts a true residual risk, use `accepted-risk`; do not use `accepted-risk` to mean “already confirmed”.


## Required Artifact Sections

- `## User Goal`
- `## Purpose And Intent`
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
- `## Intent Fidelity`
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
| DEF-RULE-015 | Confirm purpose and intent before closing definition. | `## Purpose And Intent` records Purpose, User Value, Business/Product Value, Source, and Confidence; pending clarifications include a purpose-focused 큰방향 question when confidence is `unknown` or `inferred`. | Confirm purpose is distinct from outcome, sourced to user request/answer or inspected context, and `confirmed` before approval. | Purpose is missing, source/confidence is absent or invalid, purpose is inferred/unknown without a purpose-focused 큰방향 question, or definition stops before purpose is confirmed. |
| DEF-RULE-004 | Link problems to resolving requirements and service behavior. | `## Problem-To-Requirement Mapping`, `## Requirements`, `## Normal Behavior Model`, and `## Regression Prevention` connect material problems to resolution. | Confirm each current problem has a stated requirement and corrected/prevented behavior. | A material problem has no linked requirement, behavior model, or regression prevention. |
| DEF-RULE-005 | Capture each implementation-affecting requirement as a sourced, verifiable row. | `## Requirements` has `ID`, `Type`, `Source`, `Requirement Detail`, `Boundary Or Exclusion`, and `Linked Outcomes Or Problems` columns. | Confirm every requirement has a source, concrete detail, boundary, and trace to outcomes or problems. | A requirement cannot be reviewed because source, detail, boundary, or trace is missing. |
| DEF-RULE-006 | Keep user-specified and discovered technical constraints visible without inventing implementation decisions. | `## User-Specified Constraints` and `## Discovered Constraints` separate explicit user constraints from project inspection facts. | Confirm supplied or discovered files, endpoints, commands, screens, or reference systems are retained without promoting model guesses to requirements. | User-specified technical constraints are dropped, or inferred implementation decisions are recorded as requirements without source. |
| DEF-RULE-007 | Keep asking definition questions breadth-first until the user explicitly stops, and make each question understandable from its context. | `## Pending Clarifications` and `## Clarification History` show 1-5 concrete questions, valid `Question Scope`, at least two explicit labeled proposal options, recommended options, user responses, reflected areas, contextual `Why This Matters` explanations, and any explicit user stop signal. | Confirm the agent assumes ambiguities remain, starts with 큰방향 questions, explains the practical meaning of the scope label, moves deeper only with recorded basis, restates still-pending choices after follow-ups with context and labeled options, excludes stop signals from question options, and does not close definition without a user stop signal. | Pending clarifications are incomplete, duplicated, hidden after follow-up, context-free, over five active questions, invalid question scope, missing labeled options, include a stop signal as an option, use unexplained internal shorthand, skip breadth-first progression, or definition closes because the agent judged it clear enough without a user stop signal. |
| DEF-RULE-008 | Write open questions as actionable decision records. | `## Open Questions` has `ID`, `Decision Needed`, `Context Or Conflict`, `Recommended Option`, `Alternatives`, `Impact`, `Blocking`, and `Resolution Target` columns. | Confirm each question states the decision, context, recommendation, alternatives, impact, blocking status, and where the answer will be applied. | A question lacks recommendation, alternative, impact, blocking status, or resolution target, or is only a vague concern. |
| DEF-RULE-009 | Trace resolved user answers into definition content and preserve intent fidelity. | `## Resolved Decisions` records answered question or clarification IDs, answer source, decision, and reflected artifact area; `## Intent Fidelity` records core user wording, normalized requirement meaning, allowed interpretations, disallowed interpretations, and linked requirement/policy IDs. | Confirm user answers are not lost, can be traced to requirements, policies, constraints, boundaries, or acceptance criteria, and are not narrowed into unapproved UX or technical interpretations. | A user answer exists but is not represented in decision history or a relevant updated row source, or core user wording is missing from Intent Fidelity. |
| DEF-RULE-010 | Keep acceptance criteria traceable to requirement IDs. | `## Acceptance Criteria` references requirement IDs and linked outcomes or problems. | Confirm acceptance criteria cover the requirement rows. | Acceptance criteria are generic or disconnected from requirement IDs. |
| DEF-RULE-011 | Transform requirements into a normal behavior model instead of repeating the requirements list. | `## Normal Behavior Model`, `## User Flow`, and `## State And Policy Model` explain corrected or desired behavior in service terms. | Confirm the artifact has a coherent model that a service/product reviewer can understand. | Behavior sections mostly repeat requirements rows without a normal behavior model. |
| DEF-RULE-012 | Convert meaningful behavior into explicit policy rules. | `## Policy Rules` table has `Rule ID`, `Trigger Or Condition`, `Policy`, `User/System Response`, `State/Data Responsibility`, `Failure/Recovery Behavior`, and `Source Requirement IDs` columns. | Confirm every material behavior has a policy, response, state/data responsibility, recovery behavior, and requirement trace. | A behavior is described without a concrete policy rule. |
| DEF-RULE-013 | Define integration responsibilities, boundaries, regression prevention, and failure recovery at service level. | `## Integration Flow And Data Responsibilities`, `## Boundaries`, `## Regression Prevention`, and `## Failure And Recovery Behavior` describe service-level behavior without code edit instructions. | Confirm the definition prevents scope expansion and covers non-happy-path behavior. | Boundaries, regression prevention, or failure recovery are missing for material behavior, or implementation details replace service behavior. |
| DEF-RULE-016 | Run and confirm transition risk before definition approval after a user stop signal. | `01-definition/transition-risk-goal.md` records the transition-risk goal receipt and `01-definition/transition-risk.md` records generated risk cases, definition coverage, user confirmations, dispositions, and reflected definition updates or exclusions. | Confirm every risk case is a real goal-achievement decision readiness issue with `Definition Coverage` of uncovered, conflicting, or ambiguous, not an already-decided checkpoint; confirm every material case explains the risk and has at least two labeled resolution options in `Suggested Handling`; confirm every case is user-confirmed, dispositions are allowed, `accepted-risk` has explicit residual-risk acceptance, `ask-follow-up` reopens pending clarification, and `apply-to-definition` evidence appears in the relevant definition sections before approval. | A stop signal goes directly to review/approval, transition-risk files are missing or stale, a risk case restates already-decided or already answered/reflected definition content, lacks a valid `Prior Answer Check`, a material risk lacks two labeled resolution options, a risk case lacks user confirmation or disposition, `accepted-risk` is used for already-confirmed content, a follow-up risk has no active pending clarification, or an applied risk is not reflected in the definition. |
| DEF-RULE-014 | Do not introduce implementation decisions or semantic drift. | Requirements, acceptance criteria, user flow, policy rules, failure/recovery behavior, and Intent Fidelity use consistent meaning and avoid file lists, type definitions, code edits, route/navigation choices, screen-state choices, and test command details unless recorded as explicit user decisions or discovered constraints. | Confirm definition leaves implementation design to the implementation-plan stage and applies `references/intent-fidelity.md` for semantic-drift checks. | The definition assigns implementation work, creates code-level decisions not supplied by the user or discovered constraints, changes the same concept across definition sections, or narrows user wording without explicit approval. |

## Verification Meaning

A definition is ready for implementation planning only when the reviewer can identify what the user wants, why the request matters, what user/product value it serves, what problem it resolves when applicable, where each requirement came from, what behavior and policies are approved, what is out of scope, whether user answers were carried forward, whether core user wording is preserved in `## Intent Fidelity`, whether the user explicitly gave a stop signal such as `구현 계획으로 넘어가기`, `질문 그만`, `충분해`, `진행`, `승인`, `proceed`, or `go ahead`, and whether transition-risk cases were generated, user-confirmed, and either reflected or explicitly disposed before approval. Without that user stop signal, the artifact must keep an active pending clarification batch with 1-5 questions, valid question scope, and at least two labeled options per question.
