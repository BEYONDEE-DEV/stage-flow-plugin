# Implementation Plan Writing And Review Rules

## Stage Artifact

Target: `02-implementation-plan/implementation-plan.md`

## Stage Responsibility

The implementation-plan stage maps the approved definition behavior model to a decision-complete technical implementation design. It is the first stage that should name implementation surfaces as work to perform, and it must explain how the work will be built: architecture choice, module responsibilities, control/data flow, edge cases, failure modes, and validation strategy.

The implementation plan must not create new requirements, new UX policy, new service meaning, new endpoint semantics, or a narrower UX interpretation of ambiguous definition wording. When technical decisions reveal a missing product decision, return to the earlier Stageflow stage instead of silently deciding it here.

## Request Type Profiles

Use the approved request profile only to shape implementation evidence:

- Feature-heavy work maps service policies to technical architecture, implementation units, and validation scenarios.
- Bugfix-heavy work records the confirmed or likely cause, correction surface, control/data flow change, and regression tests.
- Mixed work maps both desired outcomes and problem resolutions without changing the approved definition model.

## Technical Design Depth

A passing implementation plan must let another agent implement without inventing architecture. Avoid generic entries such as "code and tests", "implement behavior", or "run tests" as the only implementation guidance. Name the relevant modules, scripts, hooks, validators, schemas, commands, or artifact contracts when they are known from inspection.

## Definition Fidelity

Read `references/intent-fidelity.md` before planning technical UX, route, screen, state, data, API, or persistence interpretations. The implementation plan must include `## Definition Fidelity Matrix` to prove each work item preserves the approved definition meaning and returns to definition when ambiguous.

## Selective Rework After Definition Changes

When the definition is revised after an implementation plan already exists, do not rewrite the whole plan by default. Compare the revised requirements, policy rules, acceptance criteria, and data responsibilities with the current `## Work Items` and `## Coverage Matrix`.

Keep unaffected work items, partially update work items whose technical design still fits but needs adjusted scope or validation, and rewrite only the work items whose service rule coverage is no longer correct. Record the reason in `## Cause Or Design Notes`, update affected `## Work Items`, `## Coverage Matrix`, `## Validation Strategy`, and `## Risks`, then rerun the implementation-plan review and approval gate.


## Stage Artifact Format

```md
# Implementation Plan

## Technical Approach

Describe the selected implementation architecture, the alternatives considered, and why this approach fits the approved definition.

## Implementation Architecture

Describe module/script/component responsibilities, call flow, data flow, artifact/schema changes, and compatibility boundaries.

## Change Areas

Describe the code, docs, tests, or assets expected to change at implementation granularity.

## Cause Or Design Notes

Record only implementation-relevant cause analysis, design constraints, or assumptions grounded in the approved definition.

## Work Items

| ID | Implementation Unit | Technical Design | Completion Evidence |
| --- | --- | --- | --- |
| WORK-001 | One concrete implementation unit. | Exact technical approach, affected surface, and behavior to change. | Specific changed artifact and test/review evidence. |

## Coverage Matrix

| Service Rule ID | Work Item ID | Change Area | Validation Evidence | Risk/Constraint |
| --- | --- | --- | --- | --- |
| SP-001 | WORK-001 | Target module, script, docs, tests, or assets. | Specific automated or manual check proving the service rule. | Relevant implementation risk or constraint. |

## Definition Fidelity Matrix

| Work Item ID | Definition Source | Approved Meaning | Technical Interpretation | Must Not Interpret As | If Ambiguous |
| --- | --- | --- | --- | --- | --- |
| WORK-001 | REQ-001, SP-001, INTENT-001 | Approved requirement meaning from definition. | Technical implementation that preserves the approved meaning. | Unapproved narrower UX, route, screen, state, data, or API interpretation. | return-to-definition |

## Edge Cases And Failure Modes

Describe validation failures, missing state, malformed artifacts, backward compatibility, permissions, unavailable dependencies, rollback/recovery, and no-op behavior that matter to the implementation.

## Validation Strategy

List concrete commands, test cases, fixture scenarios, and review checks. Explain which technical decision or service rule each check proves.

## Risks

Record material technical risks and mitigation.

## Constraints

Keep implementation scoped to the approved definition and recorded technical architecture.
```

## Required Artifact Sections

- `## Technical Approach`
- `## Implementation Architecture`
- `## Change Areas`
- `## Cause Or Design Notes`
- `## Work Items`
- `## Coverage Matrix`
- `## Definition Fidelity Matrix`
- `## Edge Cases And Failure Modes`
- `## Validation Strategy`
- `## Risks`
- `## Constraints`

## Writing And Review Rule Table

| Rule ID | Writing Rule | Required Artifact Evidence | Review Check | Blocking Condition |
| --- | --- | --- | --- | --- |
| IP-RULE-001 | Define the selected technical approach and architecture. | `## Technical Approach` and `## Implementation Architecture` explain architecture choice, alternatives, responsibilities, call/data flow, and compatibility boundaries. | Confirm another implementer would not need to choose the architecture. | Technical approach or architecture is absent, generic, or leaves major design choices open. |
| IP-RULE-002 | Record implementation-relevant cause, design notes, or assumptions without changing service behavior. | `## Cause Or Design Notes` ties cause analysis or design constraints to approved service rules. | Confirm bugfix/root-cause notes and design assumptions are useful for implementation but do not invent product behavior. | Cause/design notes are absent when needed, or they create new service meaning. |
| IP-RULE-003 | Define concrete work items with technical design and evidence. | `## Work Items` table has `ID`, `Implementation Unit`, `Technical Design`, and `Completion Evidence` columns. | Confirm each work item is small enough to verify independently and detailed enough to implement directly. | Work items are vague, bundled, file-list-only, or lack technical design/evidence. |
| IP-RULE-004 | Trace approved service policy rules from the definition to technical work. | `## Coverage Matrix` table has `Service Rule ID`, `Work Item ID`, `Change Area`, `Validation Evidence`, and `Risk/Constraint` columns; `## Definition Fidelity Matrix` links work items back to definition sources. | Confirm every service policy rule is covered by implementation work, validation evidence, and fidelity evidence. | A service policy rule is not mapped to technical work, validation, or definition fidelity evidence. |
| IP-RULE-005 | Specify validation strategy, commands, and scenarios. | `## Validation Strategy` lists concrete commands, test cases, fixture scenarios, and what each proves. | Confirm validation evidence is sufficient for the planned technical changes. | Validation is missing, generic, impossible to run, or disconnected from service rules. |
| IP-RULE-006 | Record edge cases, failure modes, risks, and constraints. | `## Edge Cases And Failure Modes`, `## Risks`, and `## Constraints` state material limits, assumptions, and guardrails. | Confirm the implementer has enough constraints to avoid scope drift and predictable failure gaps. | Failure modes, risks, or constraints that affect implementation are omitted. |
| IP-RULE-007 | Do not implement code during this stage. | The artifact contains planning only and no implementation results. | Confirm no implementation work is claimed before user approval. | Code changes are made or recorded before implementation approval. |
| IP-RULE-008 | Do not create new requirements, UX policy, service behavior, endpoint semantics, or unapproved UX interpretations. | Work items, coverage, and `## Definition Fidelity Matrix` map only to approved service policy rules and Intent Fidelity rows from the definition. | Confirm implementation planning applies `references/intent-fidelity.md`, maps service decisions to code work, and returns to definition when approved meaning is ambiguous. | The plan introduces new product behavior, UX structure, API meaning, or technical interpretation that was not approved in definition, or chooses an interpretation for ambiguous wording instead of returning to definition. |

## Verification Meaning

An implementation plan is ready for implementation only when another agent can execute it without deciding architecture, interfaces, module responsibilities, edge-case behavior, or validation strategy.
