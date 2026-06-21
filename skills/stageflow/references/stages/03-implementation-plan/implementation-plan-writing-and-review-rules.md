# Implementation Plan Writing And Review Rules

## Stage Artifact

Target: `03-implementation-plan/implementation-plan.md`

## Stage Artifact Format

```md
# Implementation Plan

## Change Areas

Describe the code, docs, tests, or assets expected to change.

## Work Items

| ID | Work Item | Evidence |
| --- | --- | --- |
| WORK-001 | Implement the reviewed service behavior. | Changed files and test output. |

## Coverage Matrix

| Service Rule ID | Work Item ID | Change Area | Validation Evidence | Risk/Constraint |
| --- | --- | --- | --- | --- |
| SP-001 | WORK-001 | Target code, docs, tests, or assets. | Test or review evidence. | Relevant risk or constraint. |

## Validation

- Run the targeted validator or tests.

## Risks

None.

## Constraints

Keep implementation scoped to the approved service plan.
```

## Required Artifact Sections

- `## Change Areas`
- `## Work Items`
- `## Coverage Matrix`
- `## Validation`
- `## Risks`
- `## Constraints`

## Writing And Review Rule Table

| Rule ID | Writing Rule | Required Artifact Evidence | Review Check | Blocking Condition |
| --- | --- | --- | --- | --- |
| IP-RULE-001 | Identify the code, docs, tests, or assets expected to change. | `## Change Areas` lists planned change areas at implementation granularity. | Confirm the plan names the affected areas clearly enough to execute. | The implementation surface is unclear or too broad to review. |
| IP-RULE-002 | Define concrete work items with evidence. | `## Work Items` table has `ID`, `Work Item`, and `Evidence` columns. | Confirm each work item is small enough to verify independently. | Work items are vague, bundled, or lack evidence. |
| IP-RULE-003 | Trace approved service policy rules to implementation work. | `## Coverage Matrix` table has `Service Rule ID`, `Work Item ID`, `Change Area`, `Validation Evidence`, and `Risk/Constraint` columns. | Confirm every service policy rule is covered by work and validation evidence. | A service policy rule is not mapped to implementation work. |
| IP-RULE-004 | Specify validation commands or checks. | `## Validation` lists concrete commands or manual checks. | Confirm validation evidence is sufficient for the planned changes. | Validation is missing, generic, or impossible to run. |
| IP-RULE-005 | Record risks and implementation constraints. | `## Risks` and `## Constraints` state material limits, assumptions, and guardrails. | Confirm the implementer has enough constraints to avoid scope drift. | Risks or constraints that affect implementation are omitted. |
| IP-RULE-006 | Do not implement code during this stage. | The artifact contains planning only and no implementation results. | Confirm no implementation work is claimed before user approval. | Code changes are made or recorded before implementation approval. |