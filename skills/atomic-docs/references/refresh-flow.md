# Refresh Flow

## Responsibility

This reference routes full refresh and targeted docs operations against source code and existing atom files. Keep detailed phase rules in sibling references linked directly from `SKILL.md`; do not hide required gates behind nested reference chains.

## Contents

- [Refresh Operation Shape](#refresh-operation-shape)
- [Operation Profiles](#operation-profiles)
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

## Operation Profiles

Select one profile before source discovery and record it in operation state:

- `initial-baseline`: no trusted global baseline exists and the accepted scope is the whole project. Run project-wide ownership/evidence prepass, process every discovered bundle, run the project-wide reviewer, and create baseline metadata only after full PASS.
- `baseline-diff-refresh`: a trusted global baseline exists and the user wants it advanced. Start from `git diff <source_commit>..HEAD`, seed impacted atoms, expand through shared ownership/graph, process affected bundles only, then run the project-wide reviewer before updating the baseline. Record the prior/new commits, changed source surfaces, affected bundles, and rationale for carrying forward each unaffected bundle class.
- `change-impact-refresh`: inspect a source or requirement change and update affected bundles without claiming a new global baseline. Use diff/seed/graph impact and leave global baseline metadata unchanged.
- `targeted`: process only the user-accepted domain/feature plus adjacent contracts required for ownership and conflict judgment. Do not widen to project-wide work automatically.
- `inspection`: read and report without managed-doc writes, writer queues, or baseline changes unless the user later accepts a write operation.

Do not run the initial-baseline procedure for an ordinary refresh. Existing unchanged bundle PASS results remain reusable when they come from the trusted baseline and complete diff/ownership/shared-contract/graph/criteria impact analysis shows their basis is unaffected. This carry-forward is approved once by the baseline reviewer; it does not rerun unchanged domain reviewers at the new commit.

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
- `docs-generation-flow.md` for Atomic Docs Goal Gate, sequential domain bundles, conditional risk review, and conditional project-wide review.
- `reviewer-perspectives.md` for the required development-quality reviewer, conditional risk/contract reviewer, and project-wide integration/baseline reviewer.
- `project-documents-and-inventory.md` for `project/project-goal.md`, `project/project-glossary.md`, `project/service-logic-inventory.md`, `project/source-convention.md`, and service logic inventory rules.
- `source-baseline-and-change-plan.md` for source-code commit baseline metadata, full refresh sequencing, targeted docs scope, change plan requirements, and inference/gap judgment rules.
- `validation-contract.md` for plugin-bundled structural validator phases and limits.
