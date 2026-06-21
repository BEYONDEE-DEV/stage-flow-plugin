# Requirements Writing And Review Rules

## Stage Artifact

Target: `01-requirements/requirements.md`

## Stage Artifact Format

```md
# Requirements

## User Goal

Describe the user's goal in their language.

## Requirements

| ID | Actor | Trigger | Observable Behavior | Acceptance Evidence | Boundary Or Exclusion | Requirement |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-001 | User | User asks for the behavior. | The reviewed artifact records the accepted behavior. | `REQ-001` is covered by acceptance criteria. | Out-of-scope behavior is explicit. | One concrete requirement. |

## Acceptance Criteria

- `REQ-001` is satisfied by the reviewed behavior and evidence.
```

## Required Artifact Sections

- `## User Goal`
- `## Requirements`
- `## Acceptance Criteria`

## Writing And Review Rule Table

| Rule ID | Writing Rule | Required Artifact Evidence | Review Check | Blocking Condition |
| --- | --- | --- | --- | --- |
| REQ-RULE-001 | Inspect the project before asking implementation-affecting questions. | `## User Goal` or `## Requirements` mentions discovered project context when it affects the request. | Confirm requirements are grounded in the existing project instead of only chat assumptions. | Requirements ignore relevant discovered project constraints. |
| REQ-RULE-002 | Capture each implementation-affecting requirement as a verifiable row. | The `## Requirements` table has `ID`, `Actor`, `Trigger`, `Observable Behavior`, `Acceptance Evidence`, `Boundary Or Exclusion`, and `Requirement` columns. | Confirm every requirement has an actor, trigger, observable result, evidence, and boundary or exclusion. | A requirement cannot be reviewed because expected behavior or evidence is missing. |
| REQ-RULE-003 | Resolve ambiguity that would change implementation behavior. | Open decisions are either answered in requirements or represented as explicit boundaries/exclusions. | Confirm no unresolved choice could lead to materially different service behavior. | A material user decision is still open. |
| REQ-RULE-004 | Keep acceptance criteria traceable to requirement IDs. | `## Acceptance Criteria` references the requirement IDs it verifies. | Confirm acceptance criteria cover the requirement rows. | Acceptance criteria are generic or disconnected from requirement IDs. |

## Verification Meaning

A requirement is testable or verifiable when a reviewer can identify the actor, trigger, observable behavior, acceptance evidence, and boundary or exclusion needed to confirm it.