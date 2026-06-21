# Service Plan Writing And Review Rules

## Stage Artifact

Target: `02-service-plan/service-plan.md`

## Stage Artifact Format

```md
# Service Plan

## User Visible Behavior

Describe what the user will see and how the experience behaves.

## Service Behavior

Describe the service or product behavior in natural language.

## Policy Rules

| Rule ID | Trigger Or Condition | Policy | User/System Response | Data/State/API Effect | Failure/Exception Behavior | Source Requirement IDs |
| --- | --- | --- | --- | --- | --- | --- |
| SP-001 | A relevant condition occurs. | The service follows the approved behavior. | The user or system sees the planned response. | State, data, or API effects are described. | Failure behavior is described. | REQ-001 |

## Service API Or Data Flow

Describe API, data, state, source, inventory, or parity flow only when it matters.

## Boundaries

Describe in-scope and out-of-scope behavior.

## Failure And Exception Behavior

Describe errors, empty states, permissions, and recovery behavior.
```

## Required Artifact Sections

- `## User Visible Behavior`
- `## Service Behavior`
- `## Policy Rules`
- `## Service API Or Data Flow`
- `## Boundaries`
- `## Failure And Exception Behavior`

## Writing And Review Rule Table

| Rule ID | Writing Rule | Required Artifact Evidence | Review Check | Blocking Condition |
| --- | --- | --- | --- | --- |
| SP-RULE-001 | Describe the behavior the user will see without code-level details. | `## User Visible Behavior` states visible states, actions, and outcomes. | Confirm a user-facing reviewer can understand the experience. | User-visible behavior is missing or hidden behind implementation terms. |
| SP-RULE-002 | Convert meaningful behavior into explicit policy rules. | `## Policy Rules` table has `Rule ID`, `Trigger Or Condition`, `Policy`, `User/System Response`, `Data/State/API Effect`, `Failure/Exception Behavior`, and `Source Requirement IDs` columns. | Confirm every material behavior has a policy, response, effect, failure behavior, and requirement trace. | A behavior is described without a concrete policy rule. |
| SP-RULE-003 | Keep service, API, data, state, source, inventory, or parity flow at behavior level. | `## Service API Or Data Flow` describes relevant flow without file lists or code edits. | Confirm the plan explains how behavior moves through services or data only where needed. | Flow is absent when required, or it contains implementation file instructions. |
| SP-RULE-004 | Define boundaries and exclusions. | `## Boundaries` states in-scope and out-of-scope behavior. | Confirm the service plan prevents scope expansion during implementation planning. | Boundaries are missing or conflict with approved requirements. |
| SP-RULE-005 | Define failure, empty, permission, validation, and exception behavior. | `## Failure And Exception Behavior` covers relevant failure and recovery cases. | Confirm expected non-happy-path behavior is reviewable. | Failure or exception behavior is omitted for a material policy. |

## Forbidden Content

Do not include implementation file lists, code edit instructions, or test command details in the service plan.