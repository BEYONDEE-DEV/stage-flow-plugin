# Implementation Writing And Review Rules

## Stage Artifact

Target: `03-implementation/implementation.md`

## Stage Responsibility

The implementation stage records what actually changed, how it was validated, and how the result compares with the approved implementation plan, including its `Definition Fidelity Matrix`. It is evidence, not another planning stage.

## Selective Rework After Feedback

When user feedback arrives during implementation review, classify whether the implementation result, implementation plan, or approved definition is wrong. Do not mark the request completed while that classification is unresolved.

If only implementation work is wrong, update `## Work Completed`, `## Validation`, and `## Review Result` after the correction. If actual work exposes an unapproved interpretation, treat the approved plan's `Definition Fidelity Matrix` as the deciding constraint and return to implementation-plan or definition as appropriate. If the plan or definition changes, preserve the existing implementation record as evidence and use `## Plan Compliance And Deviations` to state which completed work remains valid, which work was corrected, which work was rolled back, and which work is no longer applicable.


## Request Type Profiles

Use the approved request profile only to shape evidence:

- Feature-heavy work records completed behavior and acceptance validation.
- Bugfix-heavy work records reproduction or regression evidence proving the problem no longer occurs.
- Mixed work records both completed desired outcomes and resolved current problems.

## Stage Artifact Format

```md
# Implementation

## Work Completed

Record the actual work completed.

## Plan Compliance And Deviations

Record whether the implementation matched the approved plan, including deviations, skipped work, or incomplete work.

## Validation

Record commands, checks, and results.

## Review Result

Record the implementation review result.

## Completion Summary

Record the final plan-vs-actual outcome for the user.
```

## Required Artifact Sections

- `## Work Completed`
- `## Plan Compliance And Deviations`
- `## Validation`
- `## Review Result`
- `## Completion Summary`

## Writing And Review Rule Table

| Rule ID | Writing Rule | Required Artifact Evidence | Review Check | Blocking Condition |
| --- | --- | --- | --- | --- |
| IMPL-RULE-001 | Implement only the approved implementation plan. | `## Work Completed` references completed work items and `## Plan Compliance And Deviations` states whether the plan and its `Definition Fidelity Matrix` were followed. | Confirm actual work stays within the approved implementation plan and does not violate the approved definition meaning. | Work is outside the approved plan, violates Definition Fidelity Matrix constraints, or lacks explicit deviation handling. |
| IMPL-RULE-002 | Record validation commands, checks, and results. | `## Validation` lists commands or checks with outcomes. | Confirm validation evidence supports completion and covers planned work. | Validation is missing, failed without explanation, or not tied to work items. |
| IMPL-RULE-003 | Record deviations, skipped work, incomplete work, or no deviations directly. | `## Plan Compliance And Deviations` states deviations or says none. | Confirm the implementation record is honest about plan-vs-actual differences. | Deviations or incomplete work are hidden. |
| IMPL-RULE-004 | For bugfix or mixed requests, record problem-resolution or regression evidence. | `## Validation` or `## Completion Summary` includes evidence that current problems from definition are resolved or protected by regression checks. | Confirm bugfix evidence proves the reported problem no longer reproduces or is guarded. | Bugfix/mixed work lacks reproduction, regression, or equivalent problem-resolution evidence. |
| IMPL-RULE-005 | Record the subagent implementation review result. | `## Review Result` states review outcome and blocking issue status. | Confirm review result matches the stage review gate. | Review result is missing or contradicts `review.md`. |
| IMPL-RULE-006 | Summarize final outcome for user approval. | `## Completion Summary` explains the completed outcome and residual risk. | Confirm the user can approve or reject completion from the summary. | Completion summary is missing or too vague for final approval. |
