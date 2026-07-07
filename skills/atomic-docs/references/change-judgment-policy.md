# Change Judgment Policy

## Responsibility

This reference defines how atomic docs support future code review judgments against the documented source baseline. It does not add top-level per-atom status fields. Record judgment labels on specific `Gaps`, change plan items, review findings, or evidence packet items.

The labels in this file are reusable controlled vocabulary. Explanatory prose in this file is not reusable managed-docs content and must not be copied into criteria documents, atom drafts, gaps, or review findings.

## Judgment Labels

Use this controlled vocabulary when classifying source behavior against atomic docs:

- `matches_confirmed_intent`: observed implementation matches confirmed `Intent`, `Rules`, accepted criteria, and any approved required change for the documented source baseline
- `bug_or_regression`: observed implementation conflicts with confirmed `Intent`, `Rules`, acceptance criteria, or previously documented `Current Implementation`
- `missing_required_behavior`: confirmed required behavior is absent from `Current Implementation`
- `unapproved_implemented_behavior`: behavior exists in `Current Implementation` but lacks confirmed user intent, approved plan, policy rule, or source boundary support
- `out_of_scope_behavior`: behavior is implemented or requested despite a confirmed non-goal, excluded behavior, adjacent-domain boundary, or policy boundary
- `confirmation_needed`: the evidence is inferred, ambiguous, stale, or lacks user/source approval needed for a stronger judgment
- `docs_stale`: the docs baseline does not cover the source commit or source diff needed to make a current judgment

Judgments may only use service logic that is written in the generated docs as natural-language behavior with source evidence. A source identifier, endpoint list, controller list, service class summary, method name, or missing `Gaps` item is not enough to prove that behavior matches the docs.

## Decision Order

Apply the first matching judgment that is supported by evidence:

1. If the docs baseline is older than the source behavior being judged and the diff has not been refreshed, use `docs_stale`.
2. If the relevant service logic is absent from natural-language docs, use `confirmation_needed`.
3. If the relevant `Intent`, `Rules`, requirement, boundary, or source mapping is inferred or ambiguous, use `confirmation_needed`.
4. If behavior violates a confirmed non-goal, excluded behavior, adjacent-domain boundary, or policy boundary, use `out_of_scope_behavior`.
5. If behavior exists without confirmed user intent, approved plan, policy rule, or source boundary support, use `unapproved_implemented_behavior`.
6. If confirmed required behavior is missing from `Current Implementation`, use `missing_required_behavior`.
7. If observed implementation conflicts with confirmed `Intent`, `Rules`, acceptance criteria, or documented current behavior, use `bug_or_regression`.
8. If source evidence shows the implementation satisfies the confirmed criteria and no unresolved higher-priority judgment applies, use `matches_confirmed_intent`.

Do not classify behavior as required, out-of-scope, or matching from inferred `Intent` or inferred `Rules` alone. Use `confirmation_needed` until the user or an approved workflow confirms the requirement or boundary.

## Evidence Requirements

Every judgment item must name the atom path, stable `atom_key` when available, related AID values, source evidence, judgment label, reason, and the confirmed or inferred basis for the judgment. The basis may be confirmed `Intent`, confirmed `Rules`, approved required `Planned Changes`, non-goals, excluded behavior, adjacent-domain boundaries, source baseline metadata, or explicit user approval.

Judgments such as `matches_confirmed_intent`, `bug_or_regression`, and `missing_required_behavior` are sufficiently traceable only when they link to the specific AID lines that state the relevant intent, rule, current implementation, planned change, or gap. Those AID lines should live under a stable `atom_key`; path-only or slug-only references are insufficient for new atoms. If no AID-backed natural-language service logic exists for the behavior, use `confirmation_needed` or a coverage gap instead of a stronger judgment.

`matches_confirmed_intent` is an explicit review judgment, not the absence of a `Gaps` item. Do not mark behavior as matching unless the review inspected relevant source evidence and confirmed no higher-priority label applies.

When the source behavior is present in code but absent from natural-language docs, do not classify it as matching. Record a coverage gap or `confirmation_needed` unless an approved boundary makes it `out_of_scope_behavior`, an approved requirement makes it `missing_required_behavior`, or an approved baseline mismatch makes it `bug_or_regression`.

`Planned Changes` must distinguish:

- `approved_required_change`: confirmed behavior that should be implemented
- `approved_optional_change`: confirmed optional behavior that may be implemented without being required
- `tentative_future_change`: unconfirmed or future-facing idea that cannot create `missing_required_behavior`
- `implemented_pending_confirmation`: observed implementation that may satisfy a plan but still needs user or workflow confirmation before being treated as expected behavior

## Gap And Review Finding Shape

Use natural-language prose, but each judgment-bearing `Gaps` item or review finding must include:

- one judgment label from this policy
- the stable `atom_key` when the affected atom has one
- related AID values from the atom lines that support or are affected by the finding
- source evidence identifiers from the target project
- the confirmed or inferred basis
- the affected behavior
- the next action for resolving the finding

For Korean managed docs, keep the controlled judgment label unchanged but write the visible field labels and explanation prose in Korean. Use labels such as `판정 라벨`, `관련 atom_key`, `관련 AID`, `소스 근거`, `근거`, `영향받는 동작`, `다음 조치`, `조건/분기`, `검증/가드`, `상태 전이`, `저장 효과`, `외부 호출`, and `실패/복구` when the item is structured. Do not write English scaffold labels such as `affected behavior`, `next action`, `basis`, `source evidence`, `judgment label`, `conditions/branches`, `validation/guard`, `state transition`, `persistence side effect`, `external call`, or `error/recovery` as the visible shape of a Korean `Gaps` item or review finding.

Do not collapse bug, missing required behavior, unapproved implementation, out-of-scope behavior, and confirmation-needed uncertainty into a generic gap.
