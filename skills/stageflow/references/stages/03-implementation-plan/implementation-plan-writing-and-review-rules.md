# Implementation Plan Writing And Review Rules

## Stage Artifact

Target: `03-implementation-plan/implementation-plan.md`

## Stage Responsibility

The implementation-plan stage maps the approved service behavior model to concrete code, docs, tests, or assets. It is the first stage that should name implementation surfaces as work to perform. It must not create new requirements, new UX policy, new service meaning, or new endpoint semantics.

## Request Type Profiles

Use the approved request profile only to shape implementation evidence:

- Feature-heavy work maps service policies to implementation work and validation scenarios.
- Bugfix-heavy work records the confirmed or likely cause, the correction surface, and regression tests.
- Mixed work maps both desired outcomes and problem resolutions without changing the approved service model.

## Stage Artifact Format

```md
# Implementation Plan

## Change Areas

Describe the code, docs, tests, or assets expected to change.

## Cause Or Design Notes

Record only implementation-relevant cause analysis, design constraints, or assumptions grounded in the approved service plan.

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
- `## Cause Or Design Notes`
- `## Work Items`
- `## Coverage Matrix`
- `## Validation`
- `## Risks`
- `## Constraints`

## Writing And Review Rule Table

| Rule ID | Writing Rule | Required Artifact Evidence | Review Check | Blocking Condition |
| --- | --- | --- | --- | --- |
| IP-RULE-001 | Identify the code, docs, tests, or assets expected to change. | `## Change Areas` lists planned change areas at implementation granularity. | Confirm the plan names the affected areas clearly enough to execute. | The implementation surface is unclear or too broad to review. |
| IP-RULE-002 | Record implementation-relevant cause, design notes, or assumptions without changing service behavior. | `## Cause Or Design Notes` ties cause analysis or design constraints to approved service rules. | Confirm bugfix/root-cause notes and design assumptions are useful for implementation but do not invent product behavior. | Cause/design notes are absent when needed, or they create new service meaning. |
| IP-RULE-003 | Define concrete work items with evidence. | `## Work Items` table has `ID`, `Work Item`, and `Evidence` columns. | Confirm each work item is small enough to verify independently. | Work items are vague, bundled, or lack evidence. |
| IP-RULE-004 | Trace approved service policy rules to implementation work. | `## Coverage Matrix` table has `Service Rule ID`, `Work Item ID`, `Change Area`, `Validation Evidence`, and `Risk/Constraint` columns. | Confirm every service policy rule is covered by work and validation evidence. | A service policy rule is not mapped to implementation work. |
| IP-RULE-005 | Specify validation commands or checks. | `## Validation` lists concrete commands or manual checks. | Confirm validation evidence is sufficient for the planned changes. | Validation is missing, generic, or impossible to run. |
| IP-RULE-006 | Record risks and implementation constraints. | `## Risks` and `## Constraints` state material limits, assumptions, and guardrails. | Confirm the implementer has enough constraints to avoid scope drift. | Risks or constraints that affect implementation are omitted. |
| IP-RULE-007 | Do not implement code during this stage. | The artifact contains planning only and no implementation results. | Confirm no implementation work is claimed before user approval. | Code changes are made or recorded before implementation approval. |
| IP-RULE-008 | Do not create new requirements, UX policy, service behavior, or endpoint semantics. | Work items and coverage map only to approved service policy rules. | Confirm implementation planning maps service decisions to code work instead of making new service decisions. | The plan introduces new product behavior, UX structure, or API meaning that was not approved in service-plan. |
