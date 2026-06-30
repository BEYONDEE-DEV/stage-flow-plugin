# Refresh Flow

## Responsibility

This reference defines full refresh and targeted docs operations against source code and existing atom files.

## Source Baseline

Freshness is tracked with one source-code commit hash stored in metadata at the documentation submodule root. The baseline metadata is outside individual atom files.

The baseline records the last source-code commit hash used for a confirmed docs refresh. The `atomic-docs` skill should compare `git diff <stored-source-hash>..HEAD` or the equivalent source-root diff to prioritize changed source behavior files.

When judging code against docs, first determine whether the relevant source behavior is covered by the stored baseline. If the source behavior is newer than the docs baseline and has not been refreshed, classify the finding as `docs_stale` or include it in the refresh scope before making a stronger judgment.

## Domain Context Discovery

Before assigning changed source behavior to a domain, inspect the context atoms that exist:

- `project/project-goal-atom.md` for project-wide purpose and success criteria
- `project/project-glossary-atom.md` for project-wide terms and domain-scoped terminology
- `common/common-context-atom.md` for shared concepts, policies, and code structures
- `<domain>/<domain>-context-atom.md` for existing domain goals and boundaries

If a new domain, new common atom, or domain move is plausible, include the candidate domain, evidence, affected atom files, and unresolved boundary questions in the change plan before writing docs.

If a domain candidate looks like a broad grouping instead of a durable ownership boundary, do not write it as confirmed structure. Present a split proposal using observed capabilities, workflows, responsibilities, contracts, or policies, and keep unresolved boundary questions in the change plan or `Gaps`.

## Atomization Criteria File-First Flow

When atomization criteria are needed, do not keep `Atomization Perspectives Reviewed` only in chat or only in the change plan. After the docs root is confirmed, make the first atomic-docs write action a limited draft creation or update of `<doc-root>/project/atomization-criteria-atom.md` as the criteria proposal.

If the current user request explicitly asks to start, redo, regenerate, or recreate atomic docs and confirms the managed docs root, treat the request itself as accepting the bootstrap write scope. In that case, do not stop at an approval request: create or update only `.stageflow/docs-submodule.json` when needed and `<doc-root>/project/atomization-criteria-atom.md` as a draft criteria proposal in the same turn, then stop for user review of the draft criteria.

Before that first draft write, present a narrow change plan that names only the docs root config write when needed, `project/atomization-criteria-atom.md`, and the draft criteria write action unless the current request already accepted that bootstrap scope. If `.stageflow/docs-submodule.json` is missing, the same first approved or bootstrap-accepted write scope may create that config and the criteria draft; it must not also create project goal, project glossary, common context, common policy atoms, domain atoms, graph edges, subagent work, or source baseline metadata.

The draft should first record criteria already stated in the user conversation and pending user approval state. It must not record reference example prose as criteria.

After the draft exists, use code exploration to enrich the criteria atom itself, not just the change plan. Source exploration should add or revise the `Atomization Perspectives Reviewed` entries for domain capability, entry surface, service/application flow, state transition, policy/rule, integration contract, persistence/side effect, core business term, and failure/recovery. For each perspective, record source evidence, proposed atom candidates, source-evidence-only treatment, not-applicable reasons, split/merge criteria, source evidence requirements, and unresolved questions in the criteria atom.

The user reviews, adds, removes, revises, and approves the criteria through the criteria atom. Until the criteria atom is approved, it is a draft review artifact and must not be used as the required input for domain writer subagents, review subagents, or confirmed atom writing. After approval, update the criteria atom from draft/pending state to approved state before starting domain atom work.

Expected project domains found during exploration are candidates until the approved criteria and accepted change plan confirm them. Do not treat candidate names as confirmed domain structure before criteria approval.

## Service Logic Inventory

When documenting source behavior, create a service logic inventory before drafting domain atoms. The inventory is behavior-oriented, not method-oriented: group source observations by meaningful runtime behavior rather than by endpoint, controller, service class, method, or file.

For each inventory item, record the inspected source identifiers, the natural-language behavior, conditions and branches, validation or permission checks, state transitions, persistence side effects, integration calls, emitted events, error handling, recovery behavior, inferred or confirmed basis, candidate owning atom, and judgment label when applicable.

Map every meaningful application, service, and domain logic item to an owning atom before claiming docs coverage. If ownership is unclear, record a coverage gap with source evidence and `confirmation_needed`; do not treat unmapped source behavior as healthy or covered.

Domain atom drafting must use the service logic inventory as input. A domain atom is incomplete when it only lists source files, endpoints, controllers, service classes, or method names without explaining the behavior in natural language.

## Domain Subagent Workflow

When the docs operation is large enough to split by domain, use domain writer subagents only after the criteria atom is approved. Each writer subagent must read the approved criteria atom and produce a service logic inventory plus a judgment-labeled domain evidence packet with inspected source files, perspectives reviewed, atom candidates, source evidence, inferred `Intent` or `Rules`, natural-language `Current Implementation` facts, `Planned Changes` classifications, `Gaps`, graph candidates, split/merge proposals, and relevant labels from `change-judgment-policy.md`.

Use independent review subagents to review writer packets or atom drafts against the same approved criteria atom, `change-judgment-policy.md`, the service logic inventory, and the No Example Leakage rule. A review subagent fails the packet or draft when required perspectives are missing without a not-applicable reason, meaningful source behavior is missing from the inventory, docs do not explain what the service does under relevant conditions, branches, validations, permissions, state transitions, persistence effects, integrations, errors, or recovery paths, an atom is too broad, a split gap is vague or evasive, inferred intent/rules are unmarked, source evidence is missing, source identifiers appear without natural-language behavior, reference example prose appears without user/source trace, judgment labels are absent or unsupported, missing required behavior is confused with out-of-scope behavior, unapproved implementation is confused with implemented-plan candidates, candidate domains are treated as confirmed without approval, or `Current Implementation`, `Planned Changes`, and `Gaps` are collapsed. If review fails, revise the criteria atom, change plan, evidence packet, service logic inventory, or atom draft as needed and rerun review.

## Full Refresh

A full refresh is a first-class operation when the user explicitly asks for it.

1. Read the configured docs root and source root.
2. Read the docs-root source commit baseline metadata.
3. If atomization criteria are needed and no approved criteria atom exists, create or update the draft criteria atom through the file-first flow before domain atom work.
4. Inspect changed source behavior files since the stored source commit hash and map baseline diffs to affected atoms through source-to-atom discovery and graph traversal.
5. Ignore tests, settings, schema, build, and auxiliary files by default unless the user requested auxiliary-file reflection.
6. Inspect project, common, and relevant domain context atoms when they exist.
7. Use source-to-atom seed discovery to find likely domain and atom candidates.
8. Build a service logic inventory for meaningful changed or targeted source behavior.
9. Expand affected scope through atomic graph traversal.
10. Stop graph expansion when related atom files no longer create modification candidates.
11. Present a domain-grouped change plan before writing domain atom docs.
12. Write confirmed updates only after the change plan is accepted.
13. Update the docs-root source commit baseline metadata only after confirmed docs writes for the accepted operation are complete.

## Targeted Docs Operation

Targeted domain or atom work is also a first-class flow. When targeted work overlaps with full-refresh scope, prioritize the current user-requested target. Put adjacent affected scope in follow-up proposals or `Gaps`.

For domain-level work, update the domain context atom when the domain goal, responsibility, included behavior, excluded behavior, adjacent boundary, or common-promotion rule changes. Update `project/project-glossary-atom.md` when source or user intent changes project-wide terms, aliases, forbidden conflations, or domain-scoped terminology.

## Change Plan Requirements

A change plan should group by domain and list:

- the limited first write action for draft criteria creation or update at `project/atomization-criteria-atom.md` when criteria are new or changed
- `Atomization Perspectives Reviewed`, including user-visible criteria additions, removals, revisions, approval status, and whether the criteria atom is draft or approved
- user-conversation criteria that must be recorded in the criteria atom before source-derived atom drafting
- source exploration results that update the criteria atom instead of remaining only in the change plan
- source behavior files inspected
- service logic inventory items, including natural-language behavior, source identifiers, candidate owning atom, and coverage gaps
- affected atom files
- affected atom sections
- judgment labels for review findings, including `matches_confirmed_intent`, `bug_or_regression`, `missing_required_behavior`, `unapproved_implemented_behavior`, `out_of_scope_behavior`, `confirmation_needed`, or `docs_stale`
- new domains, domain moves, atom splits, atom merges, and split proposals
- project goal, project glossary, common context, or domain context changes
- core business terms that require glossary or domain atom coverage before derived behavior is treated as covered
- parent business terms missing or underdefined in the glossary, including their source evidence and whether they belong in `Gaps`
- inferred `Intent` or `Rules` that require confirmation
- natural-language `Current Implementation` changes
- `Planned Changes` reconciliation candidates
- `Gaps`, bug candidates, uncertain mappings, rename/merge proposals, and implemented-plan candidates
- graph path corrections or target-key conflicts
- source-baseline metadata updates and docs-root config writes
- unresolved boundary questions that must be accepted before writing confirmed structure

The accepted change plan defines the only paths and write actions allowed for the current docs operation. Do not write atom files, graph corrections, source-baseline metadata, docs-root config, or docs-submodule structure before that acceptance.

## Inference And Gaps

The skill may draft `Current Implementation`, `Gaps`, and inferred `Intent` or `Rules` from code. Inferred `Intent` and `Rules` remain inferred until confirmed by the user. Inferred `Intent` or inferred `Rules` alone cannot create confirmed required behavior, confirmed out-of-scope behavior, or `matches_confirmed_intent`; use `confirmation_needed` until the user or approved workflow confirms the basis.

If observed code conflicts with confirmed intent or rules, do not resolve the conflict silently; preserve it as a `bug_or_regression` or another judgment-labeled gap. Do not write a generic gap when the issue is specifically missing required behavior, unapproved implementation, out-of-scope behavior, stale docs, or confirmation-needed uncertainty. Do not classify behavior as healthy only because no related gap exists.

Docs may only judge source behavior against service logic that is actually recorded in natural language. Source behavior absent from the docs is not implicitly correct; record it as a coverage gap, `confirmation_needed`, or `docs_stale` depending on the baseline and evidence.
