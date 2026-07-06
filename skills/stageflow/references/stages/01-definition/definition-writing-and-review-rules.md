# Definition Writing And Review Rules

This file is the definition-stage router and Rule ID checklist source. Read it before authoring or reviewing `01-definition/definition.md`, then load the focused reference files below for the part of the stage you are touching. The focused reference files preserve the detailed rules that used to live in this one large file.

## Contents

- [Stage Artifact](#stage-artifact)
- [Focused Rule Files](#focused-rule-files)
- [Stage Responsibility](#stage-responsibility)
- [Stage Artifact Format](#stage-artifact-format)
- [Required Artifact Sections](#required-artifact-sections)
- [Writing And Review Rule Table](#writing-and-review-rule-table)
- [Verification Meaning](#verification-meaning)

## Stage Artifact

Target: `01-definition/definition.md`

## Focused Rule Files

Read these files by need, and read all of them before final definition review:

- `definition-behavior-rules.md`: stage responsibility, request type profiles, late feedback and redefinition, normal behavior transformation, intent fidelity, scope narrowing evidence, flow extraction, approved flow inventory, and `references/language-policy.md` requirements.
- `definition-clarification-rules.md`: clarification loop, implementation-plan-only deferral, user-facing question presentation, open question rules, `definition-store/working-set.json.active_pending_questions`, duplicate/derived retire decisions, `Question Scope` progression, question backlog, and scope transition review.
- `definition-artifact-template.md`: exact starter `definition.md` shape, required headings, table columns, and Korean-ready starter prose.
- `definition-transition-risk-rules.md`: stop-signal transition-risk goal exception, goal-achievement decision readiness audit, `Prior Answer Check`, accepted dispositions, and labeled risk resolution options.

Also read `references/language-policy.md` before writing or revising definition prose, and read `references/intent-fidelity.md` when user wording could be narrowed into unapproved UX, route, screen, state, data, API, or persistence behavior.

## Stage Responsibility

Definition captures the user's goal, purpose and intent, current problems, outcomes, constraints, decisions, requirements, acceptance criteria, normal behavior model, policy rules, boundaries, regression prevention, failure recovery, and approved `DFLOW-*` inventory before implementation planning. It may record user-supplied or discovered technical constraints, but it must not assign code edits, TypeScript interfaces, file changes, or implementation work.

Detailed behavior, intent, and flow rules live in `definition-behavior-rules.md`.

## Request Type Profiles

Record request shape as profile tags, not as a single exclusive type. Use `Primary` and optional `Secondary` values such as `feature`, `bugfix`, `feature-adjustment`, `refactor`, `docs`, or `tooling`. Detailed profile guidance lives in `definition-behavior-rules.md`.

## Stage Artifact Format

Use `definition-artifact-template.md` for the full starter template and exact required table columns. This compact skeleton remains here because the validator checks the fixed stage rule file for required headings.

```md
# Definition

## User Goal

## Purpose And Intent

## Request Profile

## Desired Outcomes

## Current Problems

## Problem-To-Requirement Mapping

## User-Specified Constraints

## Discovered Constraints

## Pending Clarifications

## Clarification History

## Open Questions

## Resolved Decisions

## Intent Fidelity

## Requirements

## Acceptance Criteria

## Normal Behavior Model

## User Flow

## State And Policy Model

## Approved Flow Inventory

## Policy Rules

## Integration Flow And Data Responsibilities

## Boundaries

## Regression Prevention

## Failure And Recovery Behavior
```

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
- `## Approved Flow Inventory`
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
| DEF-RULE-007 | Keep asking definition-level questions breadth-first until the user explicitly stops, and defer implementation-plan-only decisions. | `definition-store/working-set.json.active_pending_questions` or the synced `## Pending Clarifications` snapshot shows 1-5 concrete definition-level questions, valid `Question Scope`, at least two explicit labeled proposal options, recommended options, contextual `Why This Matters` explanations, and store rows for decisions, traces, and `sync-state.current_gate`; `## Clarification History` shows user responses and any explicit user stop signal; `01-definition/question-scope-transition-review.md` and full-consistency evidence exist before lower-scope pending questions. | Confirm the agent classifies question stage before asking, asks only definition-level questions, defers module/file/test command/architecture/work item decisions to implementation-plan, starts with 큰방향 questions, explains the practical meaning of the scope label, uses one active question scope per batch, records answers in the store, stays store-only for low-risk answers, escalates medium/high answer impact through registered subagent gates, moves deeper only with recorded basis plus passing review evidence, restates still-pending choices after follow-ups with context and labeled options, excludes stop signals from question options, and does not close definition without a user stop signal. | Pending clarifications are incomplete, duplicated, hidden after follow-up, context-free, over five active questions, mixed across scopes in one active batch, invalid question scope, missing labeled options, include a stop signal as an option, ask implementation-plan-only decisions, use unexplained internal shorthand, skip breadth-first progression, read/write full `definition.md` during a store-only answer path, move to lower-scope questions without current PASS evidence, have stale or unsynced definition-store evidence, or definition closes because the agent judged it clear enough without a user stop signal. |
| DEF-RULE-008 | Write open questions as actionable definition-level decision records. | `## Open Questions` has `ID`, `Decision Needed`, `Context Or Conflict`, `Recommended Option`, `Alternatives`, `Impact`, `Blocking`, and `Resolution Target` columns. | Confirm each question states the definition-level decision, context, recommendation, alternatives, impact, blocking status, and where the answer will be applied. | A question lacks recommendation, alternative, impact, blocking status, or resolution target, is only a vague concern, or records an implementation-plan-only decision as a definition question. |
| DEF-RULE-009 | Trace resolved user answers into definition content and preserve intent fidelity. | `## Resolved Decisions` records answered question or clarification IDs, answer source, decision, and reflected artifact area; `## Intent Fidelity` records core user wording, normalized requirement meaning, allowed interpretations, disallowed interpretations, and linked requirement/policy IDs. | Confirm user answers are not lost, can be traced to requirements, policies, constraints, boundaries, or acceptance criteria, and are not narrowed into unapproved UX or technical interpretations. | A user answer exists but is not represented in decision history or a relevant updated row source, or core user wording is missing from Intent Fidelity. |
| DEF-RULE-010 | Keep acceptance criteria traceable to requirement IDs. | `## Acceptance Criteria` references requirement IDs and linked outcomes or problems. | Confirm acceptance criteria cover the requirement rows. | Acceptance criteria are generic or disconnected from requirement IDs. |
| DEF-RULE-011 | Transform requirements into a normal behavior model instead of repeating the requirements list. | `## Normal Behavior Model`, `## User Flow`, and `## State And Policy Model` explain corrected or desired behavior in service terms. | Confirm the artifact has a coherent model that a service/product reviewer can understand. | Behavior sections mostly repeat requirements rows without a normal behavior model. |
| DEF-RULE-018 | Record approved flows before implementation planning. | `## Approved Flow Inventory` records `DFLOW-*`, source IDs, trigger or entry, actor or consumer, target outcome, state/data responsibility, failure or empty behavior, and boundary status for every major approved user, system, policy, integration, and boundary flow; every `REQ-*` and `SP-*` appears in at least one flow `Source IDs` cell. | Confirm implementation planning can map `DFLOW-*` rows directly instead of inferring flows from scattered prose, every row cites `DEC-*`, `REQ-*`, `SP-*`, or `INTENT-*` sources, and missing rows derivable from approved `REQ-*`/`SP-*` were repaired as artifact updates rather than transition-risk questions. | A major approved flow is missing, a `REQ-*` or `SP-*` is not covered by any `DFLOW-*`, a flow lacks source support, a boundary/failure/empty-state flow is hidden in prose only, or boundary status is not one of `in-scope`, `out-of-scope-by-definition`, or `external-boundary-by-definition`. |
| DEF-RULE-012 | Convert meaningful behavior into explicit policy rules. | `## Policy Rules` table has `Rule ID`, `Trigger Or Condition`, `Policy`, `User/System Response`, `State/Data Responsibility`, `Failure/Recovery Behavior`, and `Source Requirement IDs` columns. | Confirm every material behavior has a policy, response, state/data responsibility, recovery behavior, and requirement trace. | A behavior is described without a concrete policy rule. |
| DEF-RULE-013 | Define integration responsibilities, boundaries, regression prevention, and failure recovery at service level. | `## Integration Flow And Data Responsibilities`, `## Boundaries`, `## Regression Prevention`, and `## Failure And Recovery Behavior` describe service-level behavior without code edit instructions. | Confirm the definition prevents scope expansion and covers non-happy-path behavior. | Boundaries, regression prevention, or failure recovery are missing for material behavior, or implementation details replace service behavior. |
| DEF-RULE-016 | Run and confirm transition risk before definition approval after a user stop signal. | `01-definition/transition-risk-goal.md` records the transition-risk goal receipt and `01-definition/transition-risk.md` records generated risk cases, definition coverage, user confirmations, dispositions, and reflected definition updates or exclusions. | Confirm every risk case is a real goal-achievement decision readiness issue with `Definition Coverage` of uncovered, conflicting, or ambiguous, not an already-decided checkpoint; confirm every material case explains the risk and has at least two labeled resolution options in `Suggested Handling`; confirm every case is user-confirmed, dispositions are allowed, `accepted-risk` has explicit residual-risk acceptance, `ask-follow-up` reopens pending clarification, and `apply-to-definition` evidence appears in the relevant definition sections before approval. | A stop signal goes directly to review/approval, transition-risk files are missing or stale, a risk case restates already-decided or already answered/reflected definition content, lacks a valid `Prior Answer Check`, a material risk lacks two labeled resolution options, a risk case lacks user confirmation or disposition, `accepted-risk` is used for already-confirmed content, a follow-up risk has no active pending clarification, or an applied risk is not reflected in the definition. |
| DEF-RULE-014 | Do not introduce implementation decisions or semantic drift. | Requirements, acceptance criteria, user flow, policy rules, failure/recovery behavior, and Intent Fidelity use consistent meaning and avoid file lists, type definitions, code edits, route/navigation choices, screen-state choices, and test command details unless recorded as explicit user decisions or discovered constraints. | Confirm definition leaves implementation design to the implementation-plan stage and applies `references/intent-fidelity.md` for semantic-drift checks. | The definition assigns implementation work, creates code-level decisions not supplied by the user or discovered constraints, changes the same concept across definition sections, or narrows user wording without explicit approval. |
| DEF-RULE-017 | Record traceable evidence for scope narrowing and exclusions. | `## Boundaries`, `## Requirements`, `## Policy Rules`, `## Resolved Decisions`, and `## Intent Fidelity` identify the user answer, discovered constraint, requirement, or policy source that supports any narrowed, read-only, manual, future, or out-of-scope behavior. | Confirm scope narrowing is based on traceable ID-bearing evidence rather than a hidden implementation-plan assumption, and that unresolved narrowing remains in pending clarification or transition-risk instead of approval-ready definition. | A broad user goal is narrowed, limited, deferred, or excluded without traceable source evidence, or the definition treats an unresolved scope decision as settled. |

## Verification Meaning

A definition is ready for implementation planning only when the reviewer can identify what the user wants, why the request matters, what user/product value it serves, what problem it resolves when applicable, where each requirement came from, what behavior and policies are approved, which `DFLOW-*` rows represent the approved flows, what is out of scope, whether any narrowing or exclusion has traceable source evidence, whether user answers were carried forward, whether core user wording is preserved in `## Intent Fidelity`, whether the user explicitly gave a clarification stop signal such as `구현 계획으로 넘어가기`, `질문 그만`, `충분해`, `stop asking`, `enough`, `proceed`, or `go ahead`, and whether transition-risk cases were generated, user-confirmed, and either reflected or explicitly disposed before approval. Without that user stop signal, the artifact must keep an active pending clarification batch with 1-5 questions, valid question scope, and at least two labeled options per question.
