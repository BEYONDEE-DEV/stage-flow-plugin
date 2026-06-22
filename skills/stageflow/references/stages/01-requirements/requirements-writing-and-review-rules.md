# Requirements Writing And Review Rules

## Stage Artifact

Target: `01-requirements/requirements.md`

## Stage Responsibility

The requirements stage expands and lists the user's request. It captures desired outcomes, current problems, explicit constraints, discovered constraints, and open questions before any service model or implementation plan is approved.

Requirements may include technical details when the user supplied them or project inspection discovered them. The artifact must keep those details tied to their source instead of turning model guesses into approved requirements.

## Request Type Profiles

Record request shape as profile tags, not as a single exclusive type. Use `Primary` and optional `Secondary` values such as `feature`, `bugfix`, `feature-adjustment`, `refactor`, `docs`, or `tooling`.

- Feature-heavy requests emphasize desired outcomes and success criteria.
- Bugfix-heavy requests emphasize current problems, expected-versus-actual behavior, reproduction context, impact, and regression prevention needs.
- Mixed requests must include both desired outcomes and current problems, then connect them in `Problem-To-Requirement Mapping`.

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

## Open Questions

| ID | Question | Recommended Option | Alternatives | Impact | Blocking |
| --- | --- | --- | --- | --- | --- |
| Q-001 | No open question. | N/A | N/A | N/A | no |

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
- `## Open Questions`
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
| REQ-RULE-007 | Resolve or block on ambiguity that would change implementation behavior. | `## Open Questions` lists each open question with recommended option, alternatives, impact, and `Blocking` status. | Confirm blocking questions are answered before approval, and non-blocking questions are explicitly marked. | A blocking implementation-affecting question remains open at approval time. |
| REQ-RULE-008 | Keep acceptance criteria traceable to requirement IDs. | `## Acceptance Criteria` references requirement IDs and linked outcomes or problems. | Confirm acceptance criteria cover the requirement rows. | Acceptance criteria are generic or disconnected from requirement IDs. |

## Verification Meaning

A requirement is ready for service planning when the reviewer can identify what the user wants, what problem it resolves when applicable, where the requirement came from, what is out of scope, and whether any implementation-affecting question is still blocking.
