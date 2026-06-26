# Implementation Writing And Review Rules

## Stage Artifact

Target: `03-implementation/implementation.md`

## Stage Responsibility

The implementation stage records what actually changed, how it was validated, and how the result compares with the approved implementation plan, including its `Definition Fidelity Matrix`. It is evidence, not another planning stage. Before final user approval, the implementation review subagent must audit every approved implementation-plan work item for completion and keep the implementation stage in a fix/review cycle until the latest review verdict is PASS.

## Selective Rework After Feedback

When user feedback or subagent completion-audit feedback arrives during implementation review, classify whether the implementation result, implementation plan, or approved definition is wrong. Do not mark the request completed while that classification is unresolved.

If only implementation work is wrong, update `## Work Completed`, `## Validation`, and `## Review Result` after the correction, then rerun the implementation review subagent. If actual work exposes an unapproved interpretation, treat the approved plan's `Definition Fidelity Matrix` as the deciding constraint and return to implementation-plan or definition as appropriate. If the plan or definition changes, preserve the existing implementation record as evidence and use `## Plan Compliance And Deviations` to state which completed work remains valid, which work was corrected, which work was rolled back, and which work is no longer applicable.


## Request Type Profiles

Use the approved request profile only to shape evidence:

- Feature-heavy work records completed behavior and acceptance validation.
- Bugfix-heavy work records reproduction or regression evidence proving the problem no longer occurs.
- Mixed work records both completed desired outcomes and resolved current problems.

## Language Policy

Read `references/language-policy.md` before writing or revising the implementation artifact. Keep required headings, table columns, rule IDs, paths, commands, code identifiers, and review status values unchanged, but write completed-work descriptions, deviation explanations, validation summaries, review evidence, and completion summaries in the selected user/artifact language.

For a Korean workflow, new implementation prose should default to Korean. English starter filler such as `Record the actual work completed.` is not review-ready content unless the selected artifact language is English.

## Stage Artifact Format

```md
# Implementation

## Work Completed

실제로 완료한 작업을 기록한다.

## Plan Compliance And Deviations

구현이 승인된 plan과 일치했는지, deviation, 생략된 작업, 미완료 작업, work item별 완료 증거를 포함해 기록한다.

## Validation

명령, 확인 항목, 결과를 기록한다.

## Review Result

implementation review 결과를 기록한다.

## Completion Summary

사용자가 승인할 수 있도록 plan 대비 실제 완료 결과와 남은 work item 리스크를 기록한다.
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
| IMPL-RULE-007 | Audit completion of every approved implementation-plan work item before user approval. | `## Work Completed`, `## Plan Compliance And Deviations`, `## Validation`, and `## Completion Summary` map each approved `Work Item ID` from `02-implementation-plan/implementation-plan.md` to actual changes, validation evidence, and final outcome. `## Review Result` records that the implementation review subagent checked the work-item completion audit and found no blocking issues. | Confirm the review subagent compared the approved implementation plan, implementation artifact, changed-file or diff evidence, and test output; classify every approved work item as completed before final user approval. | Any approved work item is missing from implementation evidence, partially completed, unverifiable, out of scope, insufficiently validated, hidden as a deviation, or not re-reviewed after a fix. |
