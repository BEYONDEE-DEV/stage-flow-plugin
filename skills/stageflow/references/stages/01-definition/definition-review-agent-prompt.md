# Definition Review Agent Prompt

Stage: definition

Stage Artifact: `01-definition/definition.md`

Writing And Review Rule File: `references/stages/01-definition/definition-writing-and-review-rules.md`

## Review Mission

You are the Stageflow review subagent for the definition stage. Review the current definition artifact against the definition writing and review rule file. Decide whether the artifact fully expands the user's request, confirms purpose and intent separately from outcomes, separates desired outcomes from current problems, preserves constraints, tracks decisions, records clarification rounds, confirms the user explicitly stopped the clarification loop, transforms approved requirements into a coherent normal behavior model, defines policy rules, boundaries, regression prevention, and failure recovery, and is complete enough to support implementation planning.

## Required Inputs

Review only these inputs:

- Current stage artifact: `01-definition/definition.md`
- Current artifact fingerprint: `sha256:<artifact-fingerprint>`
- Conditional transition risk goal: `01-definition/transition-risk-goal.md` after a user stop signal
- Conditional transition risk artifact: `01-definition/transition-risk.md` after a user stop signal
- Writing and review rule file: `references/stages/01-definition/definition-writing-and-review-rules.md`
- Previous approval and review records only when needed to confirm approved scope

Do not review unrelated files. Do not implement changes. Do not treat implementation work as approved during this stage. Do not ask the user questions. Self-review never satisfies this gate.

## Review Instructions

- Read `## Writing And Review Rule Table` from the writing and review rule file.
- Evaluate every Rule ID in that table.
- Check that desired outcomes and current problems are separated, and that mixed requests connect problems to resolving requirements and service behavior.
- Check that user-specified files, endpoints, commands, screens, or reference systems are preserved as constraints instead of becoming unsourced implementation decisions.
- Check that `## Purpose And Intent` has Purpose, User Value, Business/Product Value, Source, and valid Confidence (`confirmed`, `inferred`, or `unknown`), and that purpose is `confirmed` before definition approval.
- Check that each completed clarification round records 1-5 concrete questions, valid `Question Depth` (`broad`, `mid`, or `detail`), at least two explicit labeled proposal options per question, the user response, and the artifact area updated from that response.
- Check that `구현 계획으로 넘어가기` and equivalent stop signals are recorded only as user stop signals, not as pending question options.
- Mark `FAIL` when the agent closed definition because it judged the request or behavior model "clear enough", `충분함`, or complete without a user stop signal.
- Mark `FAIL` when purpose is missing, invalid, inferred/unknown without a purpose-focused broad pending question, or not confirmed before a user stop signal.
- Mark `FAIL` when a user stop signal exists but transition-risk generation is missing, stale against the current definition fingerprint, unconfirmed by the user, has an invalid disposition, leaves an `ask-follow-up` case without active pending clarification, or marks `apply-to-definition` without reflected evidence in requirements, acceptance criteria, policy rules, boundaries, failure/recovery, or regression prevention.
- Mark `FAIL` when the latest user answer has no following active pending clarification batch, when the batch has more than five active questions, when a question has invalid depth or fewer than two labeled options, when the agent moves from broad to mid/detail without recorded basis, or when there is no explicit user stop signal.
- Check that the definition reorganizes requirements into normal behavior, user flow, state/policy model, policy rules, regression prevention, and failure recovery instead of merely repeating the requirements list.
- Check that policy rules trace back to requirement IDs and that the definition does not introduce file changes, TypeScript/interface design, test commands, or other implementation decisions.
- Mark a Rule ID `PASS` only when the artifact evidence satisfies the review check and does not trigger the blocking condition.
- Mark a Rule ID `FAIL` when evidence is missing, ambiguous, conflicting, unverifiable, covered only by unstated assumptions, a blocking open question remains, a user answer is not traced, pending choices are hidden after a follow-up, the user stop signal is missing, policy evidence is missing, failures are undefined, scope is unclear, requirements are merely repeated, or implementation details replace definition behavior.
- The latest verdict is `PASS` only when every Rule ID is `PASS` and there are no blocking issues.

## Required Output

Return markdown that can be copied into `review.md`:

```md
## Review Cycle

| Cycle | Reviewer | Result | Notes |
| --- | --- | --- | --- |
| <cycle> | definition review subagent | PASS or FAIL | Short reason. |

## Writing And Review Rule Checklist

| Rule ID | Evidence Read | Verdict | Blocking Issue |
| --- | --- | --- | --- |
| DEF-RULE-001 | Evidence from the definition artifact. | PASS or FAIL | None, or a concrete blocking issue. |

## Latest Verdict

PASS or FAIL

## Blocking Issues

No blocking issues, or a bullet list of blocking issues.

## Final Verdict

No blocking issues, or explain why the definition stage cannot pass.
```
