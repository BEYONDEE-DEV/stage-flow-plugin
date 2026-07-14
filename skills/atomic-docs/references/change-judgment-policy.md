# Change Judgment Policy

## Responsibility

This reference defines how atomic docs support future code review judgments against the documented source baseline. It does not add top-level per-atom status fields. Record judgment labels on specific `Gaps`, change plan items, review findings, or evidence packet items.

The labels in this file are reusable controlled vocabulary. Explanatory prose in this file is not reusable managed-docs content and must not be copied into criteria documents, atom drafts, gaps, or review findings.

## Judgment Labels

Use this controlled vocabulary when classifying source behavior against atomic docs:

- `matches_confirmed_intent`: observed implementation matches confirmed `Intent`, `Outcomes`, `Boundaries`, `Rules`, accepted criteria, and any approved required change for the documented source baseline
- `bug_or_regression`: observed implementation conflicts with confirmed `Intent`, `Outcomes`, `Boundaries`, `Rules`, acceptance criteria, or previously documented `Current Implementation`
- `missing_required_behavior`: confirmed required behavior is absent from `Current Implementation`
- `unapproved_implemented_behavior`: behavior exists in `Current Implementation` but lacks confirmed user intent, approved plan, policy rule, or source boundary support
- `out_of_scope_behavior`: behavior is implemented or requested despite a confirmed non-goal, excluded behavior, adjacent-domain boundary, or policy boundary
- `deferred_decision`: the user or approved workflow explicitly chose to decide a specific policy, boundary, condition, API contract, or permission mapping later; this is a recorded deferral, not a request for immediate confirmation
- `confirmation_needed`: the evidence is inferred, ambiguous, stale, or lacks user/source approval needed for a stronger judgment
- `docs_stale`: the docs baseline does not cover the source commit or source diff needed to make a current judgment

Judgments may only use service logic that is written in the generated docs as natural-language behavior with source evidence. A source identifier, endpoint list, controller list, service class summary, method name, or missing `Gaps` item is not enough to prove that behavior matches the docs.

## Decision Order

Apply the first matching judgment that is supported by evidence:

1. If the docs baseline is older than the source behavior being judged and the diff has not been refreshed, use `docs_stale`.
2. If the user or approved workflow explicitly chose to decide the relevant policy, boundary, condition, API contract, or permission mapping later, use `deferred_decision`.
3. If the relevant service logic is absent from natural-language docs, use `confirmation_needed`.
4. If the relevant `Intent`, `Outcomes`, `Boundaries`, `Rules`, requirement, or source mapping is inferred or ambiguous, use `confirmation_needed`.
5. If behavior violates a confirmed non-goal, excluded behavior, adjacent-domain boundary, or policy boundary, use `out_of_scope_behavior`.
6. If behavior exists without confirmed user intent, approved plan, policy rule, or source boundary support, use `unapproved_implemented_behavior`.
7. If confirmed required behavior is missing from `Current Implementation`, use `missing_required_behavior`.
8. If observed implementation conflicts with confirmed `Intent`, `Outcomes`, `Boundaries`, `Rules`, acceptance criteria, or documented current behavior, use `bug_or_regression`.
9. If source evidence shows the implementation satisfies the confirmed criteria and no unresolved higher-priority judgment applies, use `matches_confirmed_intent`.

Do not classify behavior as required, out-of-scope, or matching from inferred `Intent`, `Outcomes`, `Boundaries`, or `Rules` alone. Use `confirmation_needed` until the user or an approved workflow confirms the meaning.

Do not use `confirmation_needed` for an answer the user has already resolved. If the user confirms a future implementation or behavior change, record the concrete future behavior as `approved_required_change` or `approved_optional_change`; when current source does not implement that confirmed future behavior, use `missing_required_behavior` for the mismatch. If the user chooses to decide the policy or mapping later, record `deferred_decision` and exclude it from `confirmation_needed` counts.

## Evidence Requirements

Every judgment item must name the atom path, stable `atom_key` when available, source evidence, judgment label, reason, affected behavior, and the confirmed or inferred basis for the judgment. Include related AID values when they exist and are independently referenceable. Otherwise identify the exact owning section and affected behavior instead of creating an AID solely for the judgment. The basis may be confirmed `Intent`, `Outcomes`, `Boundaries`, or `Rules`, approved required `Planned Changes`, source baseline metadata, or explicit user approval. Refer to the owning AID or section instead of repeating its complete behavior in the finding.

Judgments such as `matches_confirmed_intent`, `bug_or_regression`, and `missing_required_behavior` must identify the specific natural-language intent, outcome, boundary, rule, current implementation, planned change, or gap that supports them. Use its AID when one already exists or the meaning independently needs one. For an ordinary docs judgment without an AID, the stable `atom_key`, exact owning section, and affected behavior are sufficient only when they identify an unambiguous natural-language basis. Path-only, slug-only, identifier-only, or ambiguous section references are insufficient; use `confirmation_needed` or a coverage gap instead of a stronger judgment. Atomic Impl and explicit compliance operations continue to require AID-backed rows for changed in-scope required decisions.

`matches_confirmed_intent` is an explicit review judgment, not the absence of a `Gaps` item. Do not mark behavior as matching unless the review inspected relevant source evidence and confirmed no higher-priority label applies.

When the source behavior is present in code but absent from natural-language docs, do not classify it as matching. Record a coverage gap or `confirmation_needed` only when the missing basis matters to the accepted implementation or review judgment, unless an approved boundary makes it `out_of_scope_behavior`, an approved requirement makes it `missing_required_behavior`, or an approved baseline mismatch makes it `bug_or_regression`. Do not create a gap for every untested branch, possible runtime exception, or source observation outside that decision need.

`Planned Changes` must distinguish:

- `approved_required_change`: confirmed behavior that should be implemented
- `approved_optional_change`: confirmed optional behavior that may be implemented without being required
- `tentative_future_change`: unconfirmed or future-facing idea that cannot create `missing_required_behavior`
- `implemented_pending_confirmation`: observed implementation that may satisfy a plan but still needs user or workflow confirmation before being treated as expected behavior
- `deferred_decision`: confirmed plan to decide a specific policy, boundary, condition, API contract, or permission mapping later; this must stay separate from `confirmation_needed`

## Explicit Implementation Compliance

Only Atomic Impl or an explicit docs/code compliance operation writes the lightweight implementation-verification table. Use `## 구현 검증` in `.stageflow/atomic-docs/requests/<request-id>/post-write-review.md`. Record `docs basis` and `implementation basis` once for the operation, then one row per changed in-scope required AID:

```text
관련 AID | 구현 근거 | 검증 근거 | 판정 또는 gap
```

Draft the section after implementation review and finalize the same section after final docs update and compliance review. Normal docs generation and source refresh continue to use the ordinary judgment evidence contract and do not require this table. Do not put the table in managed atom files, project inventory, `work-state.json`, or a new trace artifact. When a basis changes, rerun only the affected AID rows before reusing a prior verdict.

Within an explicit compliance operation, do not issue `matches_confirmed_intent` for an in-scope required AID whose row lacks implementation and validation evidence. This does not add a second evidence format to ordinary docs refresh findings.

## Gap And Review Finding Shape

Use natural-language prose, but each judgment-bearing `Gaps` item or review finding must include:

- one judgment label from this policy
- the stable `atom_key` when the affected atom has one
- related AID values when they exist; otherwise the exact owning section and affected behavior
- source evidence identifiers from the target project
- the confirmed or inferred basis
- the affected behavior
- the next action for resolving the finding

For Korean managed docs, keep the controlled judgment label unchanged but write the visible field labels and explanation prose in Korean. Use labels such as `판정 라벨`, `관련 atom_key`, `관련 AID`, `소스 근거`, `근거`, `영향받는 동작`, `다음 조치`, `조건/분기`, `검증/가드`, `상태 전이`, `저장 효과`, `외부 호출`, and `실패/복구` when the item is structured. Do not write English scaffold labels such as `affected behavior`, `next action`, `basis`, `source evidence`, `judgment label`, `conditions/branches`, `validation/guard`, `state transition`, `persistence side effect`, `external call`, or `error/recovery` as the visible shape of a Korean `Gaps` item or review finding.

Do not collapse bug, missing required behavior, unapproved implementation, out-of-scope behavior, and confirmation-needed uncertainty into a generic gap.

Create a managed `Gaps` item only when the finding prevents a stronger implementation or review judgment. Test absence, a possible runtime exception, or an isolated source observation is supporting evidence, not automatically a separate gap. Combine observations only when they share one judgment label, one unresolved decision, and compatible evidence and resolution. Keep different labels, independently resolvable behavior, high-risk contracts, adverse branches, and verification outcomes separate even when their owner or next action is the same.
