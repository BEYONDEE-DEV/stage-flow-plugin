# Intent Fidelity

Use this reference when definition or implementation planning could reinterpret user wording, especially for UX flow, screen, route, state, data, API, or persistence behavior.

## Definition Guard

Definition must preserve user meaning before expanding it into requirements, acceptance criteria, user flow, policy rules, failure recovery, or boundaries.

Record core user answers in `## Intent Fidelity` with:

| ID | User Wording | Normalized Requirement | Allowed Interpretations | Disallowed Interpretations | Linked Requirement/Policy |
| --- | --- | --- | --- | --- | --- |

Reviewers must fail definition when:

- the same concept changes meaning across `Requirements`, `Acceptance Criteria`, `User Flow`, `Policy Rules`, or `Failure And Recovery Behavior`;
- user wording is narrowed into a more specific UX or technical behavior without an explicit `Resolved Decisions` row;
- a technical interpretation is not listed as allowed in `Intent Fidelity`.

Example blocking drift: `수정 모드` must not silently become `수정 화면`, `edit route`, route navigation, modal-internal editing, or inline editing unless that interpretation is explicitly approved.

## Implementation Plan Guard

Implementation plans must include `## Definition Fidelity Matrix`:

| Work Item ID | Definition Source | Approved Meaning | Technical Interpretation | Must Not Interpret As | If Ambiguous |
| --- | --- | --- | --- | --- | --- |

For each work item, prove that the technical interpretation preserves the approved definition meaning. Technical terms such as `navigate`, `route`, `screen`, `modal state`, `inline edit`, data source, API command, or persistence behavior are allowed only when definition explicitly supports them.

If approved definition wording is ambiguous, set `If Ambiguous` to `return-to-definition` or equivalent. Do not choose one interpretation silently.

Example blocking drift: a plan must not turn `수정 모드` into `edit route navigation` without explicit definition support.
