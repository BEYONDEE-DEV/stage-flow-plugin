# Implementation Writing And Review Rules

## Stage Artifact

Target: `04-implementation/implementation.md`

## Stage Artifact Format

```md
# Implementation

## Work Completed

Record the actual work completed, including deviations or skipped work.

## Validation

Record commands, checks, and results.

## Review Result

Record the implementation review result.

## Completion Summary

Record the final plan-vs-actual outcome for the user.
```

## Required Artifact Sections

- `## Work Completed`
- `## Validation`
- `## Review Result`
- `## Completion Summary`

## Writing And Review Rule Table

| Rule ID | Writing Rule | Required Artifact Evidence | Review Check | Blocking Condition |
| --- | --- | --- | --- | --- |
| IMPL-RULE-001 | Implement only the approved implementation plan. | `## Work Completed` references completed work items and any deviations. | Confirm actual work stays within the approved implementation plan. | Work is outside the approved plan without explicit deviation handling. |
| IMPL-RULE-002 | Record validation commands, checks, and results. | `## Validation` lists commands or checks with outcomes. | Confirm validation evidence supports completion. | Validation is missing, failed without explanation, or not tied to work items. |
| IMPL-RULE-003 | Record deviations, skipped work, or incomplete work directly. | `## Work Completed` or `## Completion Summary` states deviations or says none. | Confirm the implementation record is honest about plan-vs-actual differences. | Deviations or incomplete work are hidden. |
| IMPL-RULE-004 | Record the subagent implementation review result. | `## Review Result` states review outcome and blocking issue status. | Confirm review result matches the stage review gate. | Review result is missing or contradicts `review.md`. |
| IMPL-RULE-005 | Summarize final outcome for user approval. | `## Completion Summary` explains the completed outcome and residual risk. | Confirm the user can approve or reject completion from the summary. | Completion summary is missing or too vague for final approval. |