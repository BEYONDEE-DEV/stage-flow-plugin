# Refresh Flow

## Responsibility

This reference routes full refresh and targeted docs operations against source code and existing atom files. Keep detailed phase rules in sibling references linked directly from `SKILL.md`; do not hide required gates behind nested reference chains.

## Contents

- [Refresh Operation Shape](#refresh-operation-shape)
- [Domain Context Discovery](#domain-context-discovery)
- [Reference Routing](#reference-routing)

## Refresh Operation Shape

A full refresh is a first-class operation when the user explicitly asks for it. Targeted domain or atom work is also a first-class flow. When targeted work overlaps with full-refresh scope, prioritize the current user-requested target and put adjacent affected scope in follow-up proposals or `Gaps`.

For refresh or targeted docs work:

1. Confirm the configured docs root and source root.
2. Inspect changed or targeted source behavior files and classify runtime-relevant schemas, migrations, settings, route configuration, and behavior-describing tests instead of excluding those file classes by default.
3. Inspect existing project, common, and domain context before assigning source behavior to a domain.
4. Use source-to-atom seed discovery to find likely domain and atom candidates.
5. Follow criteria, Goal, inventory, writer/reviewer, graph, source-baseline, and change-plan rules from the sibling references below.

## Domain Context Discovery

Before assigning changed source behavior to a domain, inspect the context atoms that exist:

- `project/project-goal.md` for project-wide service/product purpose, target callers, success criteria, non-goals, and confirmation-needed project context
- `project/project-glossary.md` for project-wide terms and domain-scoped terminology
- `project/service-logic-inventory.md` when an existing behavior inventory is present
- `project/source-convention.md` when source interpretation conventions affect review
- `common/common-context-atom.md` for shared concepts, policies, and code structures
- `<domain>/<domain>-context-atom.md` for existing domain goals and boundaries

If legacy `project/project-goal-atom.md` or `project/project-glossary-atom.md` exists, treat it as migration source material and propose a move/update to the non-atom project document paths instead of using the legacy atom paths as defaults.

If a new domain, new common atom, category/subdomain path, or domain move is plausible, include the candidate domain path, evidence, affected atom files, and unresolved boundary questions in the change plan before writing docs.

If a domain candidate or category grouping looks broad instead of being a durable ownership boundary, do not write it as confirmed structure and do not keep it as `candidate`, `approved`, or `needs_confirmation`. Record it as a `rejected` broad grouping or present a split proposal using observed capabilities, workflows, responsibilities, contracts, or policies, and keep unresolved boundary questions in the change plan or `Gaps`.

## Reference Routing

Read these sibling references directly from `SKILL.md` as needed:

- `criteria-flow.md` for the first setup step, `project/atomization-criteria.md`, Criteria Structure Review Gate, criteria approval summary, and criteria approval handoff.
- `docs-generation-flow.md` for Atomic Docs Goal Gate, sequential domain bundles, and project-wide final review orchestration.
- `reviewer-perspectives.md` for the four independent domain reviewers and four cross-domain final reviewers.
- `project-documents-and-inventory.md` for `project/project-goal.md`, `project/project-glossary.md`, `project/service-logic-inventory.md`, `project/source-convention.md`, and service logic inventory rules.
- `source-baseline-and-change-plan.md` for source-code commit baseline metadata, full refresh sequencing, targeted docs scope, change plan requirements, and inference/gap judgment rules.
- `validation-contract.md` for plugin-bundled structural validator phases and limits.
