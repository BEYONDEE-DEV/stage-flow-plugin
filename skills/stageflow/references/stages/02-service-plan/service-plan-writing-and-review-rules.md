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

## Stage Artifact Format

```md
# Service Plan

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
| SP-RULE-001 | Reorganize approved requirements into a normal behavior model instead of repeating the requirements list. | `## Normal Behavior Model` explains corrected or desired behavior in service terms. | Confirm the artifact has a coherent model that a service/product reviewer can understand. | The artifact mostly repeats requirements rows without a normal behavior model. |
| SP-RULE-002 | Describe the user or system flow at behavior level. | `## User Flow` states visible states, actions, and outcomes. | Confirm user-facing behavior is understandable without code-level instructions. | User-visible behavior is missing or hidden behind implementation terms. |
| SP-RULE-003 | Convert meaningful behavior into explicit policy rules. | `## Policy Rules` table has `Rule ID`, `Trigger Or Condition`, `Policy`, `User/System Response`, `State/Data Responsibility`, `Failure/Recovery Behavior`, and `Source Requirement IDs` columns. | Confirm every material behavior has a policy, response, state/data responsibility, recovery behavior, and requirement trace. | A behavior is described without a concrete policy rule. |
| SP-RULE-004 | Keep integration flow and data responsibilities at service level. | `## Integration Flow And Data Responsibilities` describes relevant sequence and data responsibilities without file lists, type definitions, or code edits. | Confirm the plan explains how behavior moves through integrations only where needed. | Flow is absent when required, or it contains implementation file/type instructions. |
| SP-RULE-005 | Define boundaries and exclusions. | `## Boundaries` states in-scope and out-of-scope behavior. | Confirm the service plan prevents scope expansion during implementation planning. | Boundaries are missing or conflict with approved requirements. |
| SP-RULE-006 | Define regression prevention for bugfix or mixed requests. | `## Regression Prevention` lists behaviors, invariants, or problem resolutions that must keep working. | Confirm current problems from requirements are addressed as corrected behavior or prevention conditions. | A problem from requirements has no normal-behavior or regression-prevention coverage. |
| SP-RULE-007 | Define failure, empty, permission, validation, and exception recovery behavior. | `## Failure And Recovery Behavior` covers relevant failure and recovery cases. | Confirm expected non-happy-path behavior is reviewable. | Failure or recovery behavior is omitted for a material policy. |
| SP-RULE-008 | Do not introduce new requirements or implementation decisions. | Service rules trace back to approved requirement IDs and avoid unapproved product decisions. | Confirm the service plan organizes approved requirements but does not invent scope. | The service plan adds a new user requirement, UX policy, endpoint meaning, or implementation decision not grounded in requirements. |

## Repetition And Regression Review Triggers

FAIL the service-plan review when requirements rows are repeated as a new table without synthesis into `## Normal Behavior Model`, `## User Flow`, `## State And Policy Model`, and `## Regression Prevention`.

FAIL the service-plan review when a bugfix or mixed request lacks an explicit problem resolution model or regression model showing how `Current Problems` are resolved and prevented from recurring.

## Forbidden Content

Do not include implementation file lists, code edit instructions, TypeScript/interface design, test command details, or newly invented requirements in the service plan. When those details are user-specified or discovered constraints, preserve them only as service-level integration constraints and trace them back to requirements.
