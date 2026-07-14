# Refresh Flow

## Responsibility

This reference is the normative owner of operation-profile selection and routes full refresh, targeted work, and inspection against source code and existing atom files. Detailed execution, reviewer, baseline-eligibility, and semantic domain rules stay in sibling references linked directly from `SKILL.md`.

## Contents

- [Refresh Operation Shape](#refresh-operation-shape)
- [Operation Profiles](#operation-profiles)
- [Domain Context Discovery](#domain-context-discovery)
- [Reference Routing](#reference-routing)

## Refresh Operation Shape

A full refresh is a first-class operation when the user explicitly asks for it. Targeted domain or atom work is also a first-class flow. When targeted work overlaps with full-refresh scope, prioritize the current user-requested target and put adjacent affected scope in follow-up proposals or `Gaps`.

For refresh or targeted docs work:

1. Confirm the configured docs root and source root.
2. If first setup lacks combined approval, route to `criteria-flow.md` and stop after its domain-only proposal. Otherwise, after accepted scope and Goal handoff, inspect changed or targeted source areas far enough to identify useful implementation context and verify claims selected for documentation. Include DB and validation schemas, migrations, route configuration, runtime settings, and behavior-describing tests when they clarify an important rule, contract, owner, constraint, or approved requirement. Treat tests as supporting evidence rather than a substitute for reachable production behavior. Exclude generated, build, vendor, formatting, and other auxiliary files when they do not affect selected context.
3. Inspect existing project, common, and domain context before assigning source behavior to a domain.
4. Use source-to-atom seed discovery only inside the approved domain paths and after Goal handoff to find context and Atom candidates.
5. Follow criteria, Goal, inventory, writer/reviewer, graph, source-baseline, and change-plan rules from the sibling references below.

## Operation Profiles

For an existing approved docs set, select one profile before detailed source discovery and record it in operation state. For first setup, record only project-wide or targeted bootstrap discovery scope before approval, then select the execution profile from the approved domain paths. Project-wide bootstrap discovery does not imply `initial-baseline`: partial domain approval selects `targeted` and cannot create or advance a global baseline.

- `initial-baseline`: no trusted global baseline exists, baseline creation was explicitly included in the combined approval, and the accepted scope contains every required project domain. Consider every project-native feature area, select durable high-value context bundles, run the ownership/evidence prepass and project-wide reviewer, and create baseline metadata only after every selected bundle PASSes. Do not turn source exploration into a behavior-disposition inventory.
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

If a new domain, common atom, category/subdomain path, or domain move is plausible, route its evidence and unresolved boundary questions through the domain rules in `source-convention-and-domain-policy.md` and the accepted change plan. This flow selects what context to inspect; it does not independently define candidate validity or broad-domain failure conditions.

## Reference Routing

Read these sibling references directly from `SKILL.md` as needed:

- `criteria-flow.md` for first setup, domain-boundary-depth discovery, bootstrap review, and the combined criteria/domain/scope approval handoff.
- `docs-generation-flow.md` for Atomic Docs Goal Gate, sequential domain bundles, conditional risk review, and conditional project-wide review.
- `reviewer-perspectives.md` for the required development-quality reviewer, conditional risk/contract reviewer, and project-wide integration/baseline reviewer.
- `project-documents-and-inventory.md` for `project/project-goal.md`, `project/project-glossary.md`, `project/service-logic-inventory.md`, `project/source-convention.md`, and service logic inventory rules.
- `source-baseline-and-change-plan.md` for source-code commit baseline schema and eligibility, carry-forward evidence, and change plan requirements.
- `change-judgment-policy.md` for inference, confirmation, conflict, planned-change, and gap classification.
- `validation-contract.md` for plugin-bundled structural validator phases and limits.
