# Intent Fidelity

Use this reference when definition or implementation planning could reinterpret user wording, especially for UX flow, screen, route, state, data, API, or persistence behavior.

## Definition Guard

Definition must preserve user meaning before expanding it into requirements, acceptance criteria, user flow, policy rules, failure recovery, or boundaries.

Intent fidelity is semantic, not lexical. Do not mechanically expand a user phrase into a fixed checklist because a specific word appears. Instead, compare the user's top-level intent with the normalized behavior that the definition records. When the definition narrows, limits, defers, makes read-only/manual, or excludes part of a plausible approved behavior space, the narrowing must be traceable to a user answer, a discovered system constraint reflected in the definition, a requirement, a policy rule, or a boundary that cites an ID-bearing definition source.

Record core user answers in `## Intent Fidelity` with:

| ID | User Wording | Normalized Requirement | Allowed Interpretations | Disallowed Interpretations | Linked Requirement/Policy |
| --- | --- | --- | --- | --- | --- |

Reviewers must fail definition when:

- the same concept changes meaning across `Requirements`, `Acceptance Criteria`, `User Flow`, `Policy Rules`, or `Failure And Recovery Behavior`;
- user wording is narrowed into a more specific UX or technical behavior without an explicit `Resolved Decisions` row;
- a broad user goal is normalized into a narrower included/excluded behavior set without traceable evidence in `Resolved Decisions`, `Requirements`, `Policy Rules`, or this `Intent Fidelity` table;
- a technical interpretation is not listed as allowed in `Intent Fidelity`.

Example blocking drift: `수정 모드` must not silently become `수정 화면`, `edit route`, route navigation, modal-internal editing, or inline editing unless that interpretation is explicitly approved.

Example scope drift: a broad administrator responsibility must not silently become assignment-only behavior, read-only lookup, manual account operations, or deferred lifecycle management unless the definition records the source that approved that narrowing. This example is about evidence for the narrowing, not a keyword list that must always be decomposed.

## Implementation Plan Guard

Implementation plans must include `## Definition Fidelity Matrix`:

| Work Item ID | Definition Source | Approved Meaning | Technical Interpretation | Must Not Interpret As | If Ambiguous |
| --- | --- | --- | --- | --- | --- |

For each work item, prove that the technical interpretation preserves the approved definition meaning. Technical terms such as `navigate`, `route`, `screen`, `modal state`, `inline edit`, data source, API command, or persistence behavior are allowed only when definition explicitly supports them.

If approved definition wording is ambiguous, set `If Ambiguous` to `return-to-definition` or equivalent. Do not choose one interpretation silently.

If a work item narrows the approved meaning to an API/UI/data subset, excludes an adjacent capability, or treats a behavior as read-only/manual/future work, the `Definition Fidelity Matrix` must cite the definition source that approved that narrowing. Without that source, the plan must return to definition instead of inventing a new service decision.

Example blocking drift: a plan must not turn `수정 모드` into `edit route navigation` without explicit definition support.
