# Atom Format And Judgment

## Responsibility

This reference is the normative owner of selective AID definitions/references, request-created AID lifecycle, required sections, section ownership, forbidden shapes, and atomicity. It owns where a judgment may appear inside an atom, while `change-judgment-policy.md` owns judgment labels, precedence, and evidence fields.

## Atom Line ID Policy

Assign a stable unique AID only when a meaning must be referenced independently by implementation planning, compliance review, change judgment, conflict analysis, or another managed decision. The downstream reference must already exist or be named by the accepted operation; importance, durability, or possible future reuse alone is insufficient. Eligible items are confirmed important rules, observable or shared contracts, changed required behavior, active judgments/gaps, and decisions with an actual downstream reference need.

Do not assign an AID merely because a statement is durable or appears under a required section. Do not preallocate one for every `Outcome`, `Boundary`, or `Rule`; use a plain bullet until an actual reference need exists. Plain `Current Implementation` observations, source locations, call summaries, inventory/evidence rows, explanatory prose, and behavior-neutral table rows have no AID by default. An atom with no currently referenceable decision may contain zero AIDs.

An ordinary docs judgment does not create an AID merely to make the judgment possible. When no related AID exists, identify the natural-language basis with the stable `atom_key`, the exact owning section, and the affected behavior. If that section does not contain an unambiguous basis, use `confirmation_needed` or a coverage gap instead of a stronger judgment. Atomic Impl and explicit compliance operations still require their changed in-scope required decisions to use the AID-based implementation-verification contract.

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
- `outcome` for `Outcomes`
- `boundary` for `Boundaries`
- `rules` for `Rules`
- `impl` for `Current Implementation`
- `plan` for `Planned Changes`
- `gap` for `Gaps`
- `source` for source evidence rows

Use `- [AID:...] 내용` for bullets, `[AID:...] 내용` for standalone paragraphs, and an `AID` column for tables. New AID values use the current owning atom's stable `atom_key` as their creation prefix and must be globally unique across the docs set, not just unique within one atom.

Do not require AID values on frontmatter, `graph_edges`, blank lines, section headings, code fence markers, or purely structural Markdown. Project documents such as `project/atomization-criteria.md`, `project/project-goal.md`, `project/project-glossary.md`, `project/service-logic-inventory.md`, and `project/source-convention.md` are not atoms and are not required to use AID values.

Preserve AID stability. If the same meaning line is edited, moved, split into another atom, merged into another atom, retained after an atom rename, or retained after a category/domain-path move, keep its existing AID when the meaning is still traceable. After a cross-atom move, the preserved AID prefix may identify the atom where the AID was created rather than the current owner; this is valid and must not be treated as an ownership mismatch. Category moves, file renames, path drift, atom slug changes, and cross-atom movement are not AID change reasons. Assign new AID values only to newly introduced referenceable meanings. Do not clean up, remove, or renumber existing AIDs automatically merely because the current policy is narrower. If migration is unavoidable and accepted, record it explicitly in the change plan and review findings. Resolve current ownership from the containing file's frontmatter `atom_key`, never from an older preserved AID prefix.

## AID Definition And Reference

Treat `[AID:<value>]` only as the unique definition of one independently referenceable meaning. Consume that meaning everywhere else with exact `[AID-REF:<value>]`; do not copy `[AID:<value>]` as a citation. A definition or a reference placed in that definition's same Markdown paragraph/list item never counts as its consumer. Keep the same wrapper-free `<value>` in both tokens.

Build one semantic Markdown definition/reference index across the entire managed Atom set regardless of expected-key scope. Parse CommonMark blocks/inlines with the plugin-vendored `markdown-it-py` AST and its GFM table rule; fail closed when that bundled parser is missing or corrupt rather than falling back to a handwritten scanner or host site-package. Index only rendered prose. Ignore token-looking text in YAML frontmatter, fenced or indented code, inline code, HTML comments, link/image destinations and titles, reference definitions, HTML tag attributes, and `script|style|pre|textarea` bodies; image alt text and ordinary visible HTML body text remain prose. An unclosed HTML comment hides the remainder instead of creating a token.

Use the nearest list item as one consumer block across its paragraph continuation, while each nested list item is distinct. Treat each GFM table row and each ordinary paragraph/heading as a separate block. A definition and reference in the same resulting block never establish consumption. Reject malformed AID-like tokens that remain in visible prose; Markdown syntax that does not parse as a link/code/comment remains visible rather than hiding a token. When a request ID is present, count only `inventory.md`, `evidence.md`, `post-write-review.md`, and the exact receipt-owned findings reports as request-local consumers. Arbitrary scratch, rollback, summary, or unowned Markdown never closes an orphan. Reject request-local definitions, every duplicate definition, and every indexed `[AID-REF:...]` with no definition immediately, including bundle-scoped validation. A short reference may add only the minimum local context needed to understand the owner; it must not restate the complete meaning.

For every v5 operation, create top-level `created_aids` in `work-state.json` as the current set of active definitions created by this request, using unique wrapper-free AID values; initialize it as `[]`. Add a value when the request creates its definition. If semantic review rejects a new mechanical or invalid AID, remove its definition, references, and ledger value together before rerunning; removing only the ledger value while its definition remains fails the final baseline comparison. Do not list an existing preserved or moved definition as new, and do not infer creation from its historical prefix.

During intermediate bundle validation, allow a listed `created_aids` definition to have no consumer yet because an accepted later bundle or Atomic Impl compliance row may add it. At the final request-bound selection/docs/baseline and terminal gates, require every listed value to have at least one actual `[AID-REF:<value>]` consumer in managed docs or a recognized request-local artifact. A planned consumer name, plain-text AID value, or definition token does not close the orphan. Do not apply this final orphan rule retroactively to existing AIDs absent from `created_aids`; duplicate and dangling checks still apply globally.

## Required Atom Sections

Each atom file must preserve these sections. Each must appear exactly once as a rendered top-level plain ATX `##` heading. Heading-like text inside a code fence, indented code block, blockquote, list, or another nested block does not count:

- `Intent`
- `Outcomes`
- `Boundaries`
- `Rules`
- `Current Implementation`
- `Planned Changes`
- `Gaps`

The headings provide a stable place for each kind of context; they are not a completeness checklist. Write only material context in its owning section. When no material meaning applies, use a concise empty/none statement rather than searching source for content to fill the heading. Another section may use `[AID-REF:...]`, `atom_key`, or the owning heading and add only the minimum local context needed to understand it. Repeating the same meaning across sections is invalid even when wording differs.

| Section | Question and owned meaning | Must not own |
| --- | --- | --- |
| `Intent` | Why does this atom exist? Record only the durable purpose. | Expected results, scope, rules, source realization, or unresolved questions. |
| `Outcomes` | What smallest normal result helps orient a reader to this atom? | A complete result catalog, preconditions, branch logic, implementation sequence, or failure analysis. |
| `Boundaries` | Which important ownership, inclusion/exclusion, or adjacent handoff prevents confusion? | Exhaustive scope, domain-wide boundaries repeated from a context atom, graph metadata, source classes, or implementation flow. |
| `Rules` | Which non-obvious rule, invariant, refusal, or shared/external contract is important before changing this area? | Every source condition, normal-result summary, source mechanics, or unresolved findings. |
| `Current Implementation` | Where does the important implementation live, and which non-obvious constraints help a developer inspect it? | A second specification of complete fields, conditions, branches, results, failures, or contracts. |
| `Planned Changes` | Which approved or classified future delta is not yet current implementation? | Existing behavior, unresolved evidence, or unapproved ideas disguised as plans. |
| `Gaps` | Which specific mismatch, uncertainty, missing evidence, or unresolved decision prevents a stronger judgment? | A complete restatement of the owning rule, outcome, boundary, implementation flow, or source inventory. |

`Intent` answers only why the atom exists. Do not use it as a summary of every other section. `Outcomes` records only the normal result needed to recognize the documented area. `Boundaries` records an ownership or handoff distinction only when it prevents confusion. `Rules` keeps selected important rules and contracts, not every condition or branch. A domain context atom owns domain-wide boundaries, while graph frontmatter owns only machine-traversable relationship metadata.

`Outcomes`, `Boundaries`, and `Rules` may describe selected source-established context without separate user approval when reachable behavior and supporting evidence satisfy `service-logic-coverage.md`. Write it in present tense and trace it once through `Current Implementation` `Source Evidence` plus the applicable global source baseline or operation-local `source_commit_observed`; do not add per-line provenance fields. AI authorship alone does not make the meaning inferred or require a `Gaps` item. Omitted ordinary behavior is not an implicit gap.

`Intent` may state the smallest source-supported functional purpose needed to understand the atom, but must not claim that inferred product strategy or necessity is user-approved. When competing purpose interpretations would materially change an outcome, boundary, rule, or implementation judgment, record that specific decision in `Gaps`. Approved desired behavior keeps its approval basis and required/optional/excluded/boundary meaning where applicable; unimplemented approved deltas belong in `Planned Changes`.

Do not promote an observed anomaly, accidental fallback, security weakness, or source quirk into a normal `Outcome` or required `Rule`. Keep a non-blocking non-obvious observation in `Current Implementation` only when it helps understand a documented decision. If source contradicts an approved requirement or source-established current contract and blocks a stronger judgment, record only the differential fact and impact as the applicable `Gaps` item. Do not repeat the full observed behavior in both places.

Every changed in-scope required AID used as an implementation basis must include an observable verification condition or a verifiable invariant in that same item. Include only the precondition, result, refusal/failure, state/effect, or exclusion needed to judge that change. This is a durable verification target, not a request to enumerate every input/state/failure combination or test execution step. Historical descriptions outside the implementation scope do not need acceptance detail added merely for completeness. Do not require a separate acceptance AID; assign another AID only when the verification condition is a separate independently reviewable meaning. Make every implementation-basis and compliance consumer use `[AID-REF:<value>]`.

`Current Implementation` records source-observed context needed to find and understand the documented area. Include key entry points, storage or integration owners, and non-obvious constraints only when useful. Refer to the owning `Outcomes`, `Boundaries`, or `Rules` AID instead of restating its behavior. Do not mirror every source branch, method call, query predicate, DTO field, internal structure, failure path, or possible exploit/test scenario. A bare list of identifiers is not sufficient, but a concise explanation may point the reader back to source for exact behavior. Record execution order only when it is important contract or change-impact context.

For Korean managed docs, write the prose under `Current Implementation` with Korean-first structure when that structure helps the atom explain behavior. Recommended subheadings are:

- `### 동작 흐름`
- `### 관찰된 판단 규칙`
- `### 상태와 저장 효과`
- `### 외부 연동과 이벤트`
- `### 실패와 복구 동작`
- `### Source Evidence`

Do not force every atom to include every subheading. Use only the subsections needed to orient source inspection and preserve important context. Do not write `Current Implementation` as a translated English skeleton, a complete method-call sequence, or a substitute for reopening source. Include conditions, state/effects, and failures only when they are non-obvious context or part of an approved implementation-basis requirement. Stop before source-level mechanics whose only value is specification completeness.

`Source Evidence` is a locator inside `Current Implementation`, not another semantic section. List the smallest authoritative file, test, schema, setting, or approved artifact identifiers needed to verify the owning claims. Do not repeat the behavior narrative, rule, boundary, or gap under each locator.

`Planned Changes` records future intended work that is not yet confirmed as implemented. Classify each item with the controlled planned-change values and decision rules in `change-judgment-policy.md`; this section owns the future delta, not the label vocabulary.

`Gaps` owns only an unresolved difference or missing evidence that prevents a stronger implementation or review judgment. Classify the item under `change-judgment-policy.md`, point to the owning AID or section, and record only the differential fact, impact, and decision or action needed. A missing test, possible runtime exception, nullable field, or isolated source observation is not a gap by itself. When a gap is resolved, put the resulting durable meaning in its proper owning section; do not preserve a resolved question by copying its full narrative into both places.

Combine several observations into one gap only when they use the same judgment label, support one unresolved decision, and lead to a compatible resolution. Do not merge different labels, independently resolvable behavior, separate high-risk contracts, adverse branches, or verification outcomes merely because they share an owner or next action. A gap keeps a concise verification target when needed; it does not own a Cartesian test matrix or step-by-step test procedure.

## Judgment Evidence Policy

This section owns only atom-local placement: do not add top-level per-atom status fields, and keep judgment-bearing future deltas in `Planned Changes` and unresolved differences in `Gaps`. The complete controlled vocabulary, precedence, evidence fields, confirmation behavior, and Korean-visible finding shape come from `change-judgment-policy.md` and `language-policy.md`; do not maintain a second judgment contract here.

## Forbidden Shapes

- Do not split state into type folders such as `current-state/`, `future-plan/`, or `gap/`.
- Do not put per-atomic freshness/status fields inside atom files.
- Do not store per-file commit status in the atomic document.
- Do not collapse `Intent`, `Outcomes`, `Boundaries`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps` into one undifferentiated narrative.
- Do not repeat one meaning across sections as a completeness or review aid; keep one complete owner and use a short reference elsewhere.
- Do not present AI inference as confirmed user intent.
- Do not use project-specific example domain names as skill-level rules.
- Do not leave an evasive split or coverage gap in place of documenting inspected service logic. A note that logic should be split later is invalid unless it also records the concrete source evidence, proposed owners, unresolved question, and the behavior already observed.
- Do not use source identifiers without natural-language behavior as proof that service logic is covered.

## Atomicity Policy

An atom is too broad when it covers unrelated behaviors, policies, rules, states, planned changes, or gap boundaries. Split or propose a split before writing confirmed docs. If the split is ambiguous, keep candidates in the change plan or `Gaps` and ask the user.

An atom is over-compressed when combined responsibilities make the purpose, durable owner, important shared contract, or change-impact boundary misleading or difficult to navigate. Independent source branches, entry points, methods, states, persistence effects, or verification cases do not require separate atoms by themselves. Do not keep distinct durable owners inside one generic atom only because they share a domain, screen, service class, or folder.

Choose split boundaries from durable purpose, ownership, shared-contract, navigation, and change-impact independence, not from a project-specific domain list or source structure. Entry point, user action, saved aggregate, API contract, state transition, failure/recovery path, and persistence side effect are split evidence only when they create a different important context boundary.

Do not write a vague split gap that says more precision is needed without concrete evidence. A split proposal must name candidate atom keys, tentative paths or slugs, owning domain path, source files/classes/functions or other source identifiers, the split criterion, each candidate atom's behavior/state/rule responsibility, and unresolved questions. If that evidence is missing, record the missing evidence as a `Gaps` item instead of pretending the split is already specified.
