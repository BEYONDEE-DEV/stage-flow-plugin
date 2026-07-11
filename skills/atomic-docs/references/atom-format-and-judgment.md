# Atom Format And Judgment

## Responsibility

This reference defines selective atom IDs, required atom sections, judgment evidence, forbidden shapes, and atomicity rules.

## Atom Line ID Policy

Assign a stable unique AID only to a durable, independently referenceable meaning used by implementation planning, compliance review, change judgment, or conflict analysis. Typical AID-bearing items are confirmed intent, business rules, observable contracts, changed required behavior, active judgments, and gaps. Do not assign AIDs to routine explanatory prose, mechanical source summaries, every evidence row, or every table row merely because it can be numbered.

Use this format:

```text
[AID:<atom_key>.<section-code>.<NNN>]
```

For example:

```text
- [AID:paid-order-processing.impl.003] paid line마다 ticket group 하나를 만들고 저장한다.
```

Section codes are:

- `intent` for `Intent`
- `rules` for `Rules`
- `impl` for `Current Implementation`
- `plan` for `Planned Changes`
- `gap` for `Gaps`
- `source` for source evidence rows

Use `- [AID:...] 내용` for bullets, `[AID:...] 내용` for standalone paragraphs, and an `AID` column for tables. New AID values use the current owning atom's stable `atom_key` as their creation prefix and must be globally unique across the docs set, not just unique within one atom.

Do not require AID values on frontmatter, `graph_edges`, blank lines, section headings, code fence markers, or purely structural Markdown. Project documents such as `project/atomization-criteria.md`, `project/project-goal.md`, `project/project-glossary.md`, `project/service-logic-inventory.md`, and `project/source-convention.md` are not atoms and are not required to use AID values.

Preserve AID stability. If the same meaning line is edited, moved, split into another atom, merged into another atom, retained after an atom rename, or retained after a category/domain-path move, keep its existing AID when the meaning is still traceable. After a cross-atom move, the preserved AID prefix may identify the atom where the AID was created rather than the current owner; this is valid and must not be treated as an ownership mismatch. Category moves, file renames, path drift, atom slug changes, and cross-atom movement are not AID change reasons. Assign new AID values only to newly introduced meaning lines. Do not renumber existing AID values for cosmetic ordering. If an AID migration is unavoidable, record it explicitly in the change plan and review findings. Resolve current ownership from the containing file's frontmatter `atom_key`, never from an older preserved AID prefix.

## Required Atom Sections

Each atom file must preserve these sections:

- `Intent`
- `Rules`
- `Current Implementation`
- `Planned Changes`
- `Gaps`

`Intent` and `Rules` describe confirmed user intent only when the user or approved workflow has confirmed them. AI-written intent or rules must be marked as inferred until confirmed and must be linked to `Gaps`. When intent or rules are confirmed, include the confirmation basis and whether the behavior is required, optional, excluded, or boundary-defining.

Every changed in-scope required AID used as an implementation basis must include an observable verification condition or a verifiable invariant in that same item. Include only the precondition, result, refusal/failure, state/effect, or exclusion needed to judge that change. Historical descriptions outside the implementation scope do not need acceptance detail added merely for completeness. Do not require a separate acceptance AID; assign another AID only when the verification condition is a separate independently reviewable meaning.

`Current Implementation` records source-observed implementation context needed to find and understand the documented decisions. Include important entry points, states, storage effects, integration points, non-obvious constraints, and source identifiers as applicable. Do not mirror every source branch, method call, DTO field, or internal structure. A bare list of identifiers is not sufficient, but a concise decision-oriented explanation may point the reader back to source for mechanics.

For Korean managed docs, write the prose under `Current Implementation` with Korean-first structure when that structure helps the atom explain behavior. Recommended subheadings are:

- `### 동작 흐름`
- `### 관찰된 판단 규칙`
- `### 상태와 저장 효과`
- `### 외부 연동과 이벤트`
- `### 실패와 복구 동작`
- `### Source Evidence`

Do not force every atom to include every subheading. Use only the subsections needed to preserve decisions and orient source inspection. Do not write `Current Implementation` as a translated English skeleton or a method-call sequence. Include conditions, state/effects, and failures only when they affect a product rule, observable contract, verification result, or change impact.

`Planned Changes` records future intended work that is not yet confirmed as implemented and must classify each planned item as `approved_required_change`, `approved_optional_change`, `tentative_future_change`, `implemented_pending_confirmation`, or `deferred_decision`. A user-confirmed future implementation or behavior change is not `confirmation_needed`; record the concrete future behavior as `approved_required_change` or `approved_optional_change`. A user-confirmed plan to decide a policy, boundary, condition, API contract, or permission mapping later is `deferred_decision`. `Gaps` records judgment-labeled mismatches, uncertain inference, bug candidates, missing required behavior, missing intent, unapproved implementation, out-of-scope behavior, docs-stale findings, implemented-plan candidates, deferred-decision blockers, rename/merge candidates, service logic coverage gaps, and confirmation-needed boundaries.

## Judgment Evidence Policy

Atomic docs should let a reviewer determine what is implemented, what should be implemented, what is missing, what is buggy, what is unapproved or out of scope, and what still needs confirmation for the documented source baseline.

Do not add top-level per-atom status fields for these judgments. Instead, attach controlled judgment labels from `change-judgment-policy.md` to specific `Gaps`, change plan items, review findings, or domain evidence packet items.

Each judgment-bearing item must include:

- one judgment label from `change-judgment-policy.md`
- source evidence for the observed behavior or missing behavior
- confirmed or inferred basis from the relevant atom section, boundary, baseline metadata, or user approval
- next action for resolving the finding

For Korean managed docs, write judgment-bearing `Gaps`, `Planned Changes`, change plan items, and review findings with Korean-visible field labels or Korean sentence wording. Keep the controlled judgment label itself unchanged, but render the surrounding structure as `판정 라벨`, `소스 근거`, `근거`, `영향받는 동작`, `다음 조치`, and `관련 AID` when structured fields are useful. Do not use English scaffold labels such as `affected behavior`, `next action`, `basis`, `source evidence`, or `judgment label` inside Korean atom prose.

`matches_confirmed_intent` is allowed only as an explicit review finding after the reviewer inspects source evidence and confirms that no higher-priority judgment label applies. Do not treat the lack of a `Gaps` item as proof that code matches confirmed intent.

Approved project documents may provide context such as non-goals or terminology boundaries, and domain context atoms must preserve excluded behavior and adjacent-domain boundaries clearly enough for `out_of_scope_behavior` review. A service judgment still needs service logic atom content, source evidence, baseline metadata, and a controlled judgment label.

## Forbidden Shapes

- Do not split state into type folders such as `current-state/`, `future-plan/`, or `gap/`.
- Do not put per-atomic freshness/status fields inside atom files.
- Do not store per-file commit status in the atomic document.
- Do not collapse `Intent`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps` into one undifferentiated narrative.
- Do not present AI inference as confirmed user intent.
- Do not use project-specific example domain names as skill-level rules.
- Do not leave an evasive split or coverage gap in place of documenting inspected service logic. A note that logic should be split later is invalid unless it also records the concrete source evidence, proposed owners, unresolved question, and the behavior already observed.
- Do not use source identifiers without natural-language behavior as proof that service logic is covered.

## Atomicity Policy

An atom is too broad when it covers unrelated behaviors, policies, rules, states, planned changes, or gap boundaries. Split or propose a split before writing confirmed docs. If the split is ambiguous, keep candidates in the change plan or `Gaps` and ask the user.

An atom is over-compressed when it bundles responsibilities that have independent product decisions, change approval, verification, ownership, or conflict boundaries. Shared entry points, methods, states, or persistence effects do not require separate atoms by themselves. Do not keep genuinely independent decisions inside one generic atom only because they share a domain, screen, service class, or folder.

Choose split boundaries from decision, ownership, change, and judgment independence, not from a project-specific domain list or source structure. Entry point, user action, saved aggregate, API contract, state transition, failure/recovery path, and persistence side effect are split evidence only when they create different durable decisions or review findings.

Do not write a vague split gap that says more precision is needed without concrete evidence. A split proposal must name candidate atom keys, tentative paths or slugs, owning domain path, source files/classes/functions or other source identifiers, the split criterion, each candidate atom's behavior/state/rule responsibility, and unresolved questions. If that evidence is missing, record the missing evidence as a `Gaps` item instead of pretending the split is already specified.
