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

When atomization criteria are needed, do not keep reviewed atomization perspectives only in chat or only in the change plan. For Korean managed docs, record this as `검토된 Atom화 관점`. After the docs root is confirmed, make the first atomic-docs write action a limited draft creation or update of `<doc-root>/project/atomization-criteria.md` as the criteria proposal.

If the current user request explicitly asks to start, redo, regenerate, or recreate atomic docs and confirms the managed docs root, treat the request itself as accepting the bootstrap write scope. In that case, do not stop at an approval request: create or update only `.stageflow/docs-submodule.json` when needed and `<doc-root>/project/atomization-criteria.md` as a draft criteria proposal in the same turn, then run the Criteria Structure Review Gate and stop for user review only after criteria-review PASS.

Before that first draft write, present a narrow change plan that names only the docs root config write when needed, `project/atomization-criteria.md`, and the draft criteria write action unless the current request already accepted that bootstrap scope. If `.stageflow/docs-submodule.json` is missing, the same first approved or bootstrap-accepted write scope may create that config and the criteria draft; it must not also create project goal, project glossary, common context, common policy atoms, domain atoms, graph edges, domain writer/reviewer subagent work, service logic inventory, or source baseline metadata.

The draft should first record criteria already stated in the user conversation and pending user approval state. It must not record reference example prose as criteria.

After the draft exists, use code exploration to enrich the criteria document itself, not just the change plan. Source exploration should add or revise `도메인 분할 기준`, `후보/승인 도메인 맵`, `검토된 Atom화 관점`, and `작성/리뷰 공통 품질 기준` entries for domain capability, entry surface, service/application flow, state transition, policy/rule, integration contract, persistence/side effect, core business term, and failure/recovery. For each perspective in Korean managed docs, record `Atom 후보 기준`, `소스 근거로만 둘 기준`, `해당 없음 사유`, `분리/병합 기준`, `소스 근거 요구사항`, and `미해결 질문` in the criteria document. Use `서브에이전트 역할 분담` only to explain how writer subagents produce artifacts for the shared criteria and reviewer subagents verify the same criteria.

Before asking the user to approve the criteria document, satisfy the Criteria Structure Review Gate below. After criteria-review PASS, tell the user the criteria document path, summarize the actual written content, and ask the user to inspect the file and approve it or request changes. The summary should cover the docs root and scope, domain partitioning criteria, candidate or approved domain map, atomization perspectives, shared writer/reviewer quality criteria, service logic coverage requirements, judgment policy usage, and open blockers. Do not treat the summary as a substitute for the file. The user reviews, adds, removes, revises, and approves the criteria through the criteria document only after that gate passes. Until the criteria document is approved, it is a draft review artifact and must not be used as the required input for domain writer subagents, review subagents, or confirmed atom writing. After approval, update the criteria document from draft/pending state to approved state before starting domain atom work.

Expected project domains found during exploration are candidates until the approved criteria and accepted change plan confirm them. Do not treat candidate names as confirmed domain structure before criteria approval.

If a legacy `<doc-root>/project/atomization-criteria-atom.md` exists, treat it as a migration/update candidate. Do not write new criteria to the legacy path unless the accepted change plan explicitly covers migration from that legacy artifact.

## Criteria Structure Review Gate

Run this gate after the criteria draft is created or enriched, and before asking the user for criteria approval.

Use an independent criteria-review subagent to review only the criteria draft, source exploration evidence, and accepted draft scope. This review subagent is allowed before criteria approval and does not require a Codex Goal because it is part of criteria-draft quality control, not docs generation.

The criteria-review subagent must fail the draft when:

- any `Atom화 관점` entry is missing one of the required Korean subfields: `Atom 후보 기준`, `소스 근거로만 둘 기준`, `해당 없음 사유`, `분리/병합 기준`, `소스 근거 요구사항`, or `미해결 질문`
- a required perspective subfield is empty, placeholder-only, or a one-line summary that does not explain the criterion
- Korean managed criteria docs use English visible labels for criteria sections or fields, such as `Purpose`, `Approval Status`, `Atomization Perspectives`, `Atom candidate criteria`, `Source evidence only criteria`, or `Unresolved questions`
- source evidence is absent and the perspective does not record a concrete `해당 없음 사유` or `미해결 질문`
- the domain map is missing, source-unsupported, or treats candidate domains as approved before user approval
- writer and reviewer rules are written as divergent role-specific checklists instead of one `작성/리뷰 공통 품질 기준`
- any reviewer FAIL condition lacks a matching shared criterion or explicit phase gate, or any writer obligation is not reviewable by the same shared criterion
- the draft makes unapproved destructive claims about legacy artifacts, including deleting `atomization-criteria-atom.md` without an accepted migration/delete action
- reference example prose leaks into the criteria document without target-project user or source trace
- source-derived intent, rules, domain ownership, or boundaries are not marked as inferred or `needs_confirmation` while still unapproved

If criteria-review fails, revise only `project/atomization-criteria.md` within the accepted criteria draft scope, then rerun the criteria-review subagent. Repeat this cycle until the criteria-review subagent reports no blocking issues. A PASS means the criteria draft is ready for user review and possible approval; it does not approve the criteria automatically.

When criteria-review PASS is reached, respond to the user with:

- the criteria document file path, normally `<doc-root>/project/atomization-criteria.md`
- a concise Korean summary of what was written, including docs root/scope, domain partitioning criteria, candidate or approved domain map, atomization perspectives, shared writer/reviewer quality criteria, service logic coverage requirements, judgment policy usage, and open blockers
- a clear request for the user to inspect the file content and either approve it, say there is no issue, or request corrections

Do not proceed to criteria approval state update, Codex Goal creation, service logic inventory, domain writer/reviewer subagents, project/common/domain atom writing, graph writing, or source-baseline update until the user confirms the criteria content has no issue or explicitly approves it.

## Atomic Docs Goal Gate

Bootstrap criteria draft creation and the Criteria Structure Review Gate do not require a Codex Goal. The first bootstrap scope may create or update only `.stageflow/docs-submodule.json` and `<doc-root>/project/atomization-criteria.md`, run criteria-review/revision cycles for that criteria draft, then stop for user review after criteria-review PASS.

After the criteria document is approved and the user accepts a docs write scope, call Codex `create_goal` before starting docs generation work. Docs generation work includes project, common, or domain atom writing; service logic inventory creation; domain writer or reviewer subagent execution; graph edge writing; and source-baseline metadata updates.

The Goal objective must name the approved criteria document path, docs root, accepted docs write scope, natural-language service logic coverage requirement, writer/reviewer cycle, and completion condition for the accepted docs operation. If an active Codex Goal already covers the same atomic-docs operation, continue inside that Goal instead of creating a duplicate.

If `create_goal` is unavailable or fails, do not start docs generation. Report the Goal creation blocker to the user and leave project/common/domain atoms, service logic inventory, domain writer/reviewer subagents, graph edges, and source-baseline metadata untouched.

Complete the Goal only after the accepted docs operation is actually complete. Do not mark the Goal complete while work is incomplete, waiting for user input, blocked by review FAIL, or waiting for criteria/scope approval.

## Service Logic Inventory

When documenting source behavior, create a service logic inventory before drafting domain atoms. The inventory is behavior-oriented, not method-oriented: group source observations by meaningful runtime behavior rather than by endpoint, controller, service class, method, or file.

For each inventory item, record the inspected source identifiers, the natural-language behavior, conditions and branches, validation or permission checks, state transitions, persistence side effects, integration calls, emitted events, error handling, recovery behavior, inferred or confirmed basis, candidate owning atom, candidate or assigned AID, and judgment label when applicable.

Map every meaningful application, service, and domain logic item to an owning atom before claiming docs coverage. If ownership is unclear, record a coverage gap with source evidence and `confirmation_needed`; do not treat unmapped source behavior as healthy or covered.

Domain atom drafting must use the service logic inventory as input. A domain atom is incomplete when it only lists source files, endpoints, controllers, service classes, or method names without explaining the behavior in natural language.

## Domain Subagent Workflow

When the docs operation is large enough to split by domain, use domain writer subagents only after the criteria document is approved, the docs write scope is accepted, and the Atomic Docs Goal Gate is satisfied. Each writer subagent must read the approved criteria document and produce a service logic inventory plus a judgment-labeled domain evidence packet that maps its output to the same `작성/리뷰 공통 품질 기준` used by reviewers. The packet must include inspected source files, domain-map coverage, perspectives reviewed, atom candidates, source evidence, inferred `Intent` or `Rules`, natural-language `Current Implementation` facts, `Planned Changes` classifications, `Gaps`, graph candidates, split/merge proposals, stable AID assignments for each meaning line, and relevant labels from `change-judgment-policy.md`.

For Korean managed docs, writer subagents must draft directly with Korean-first templates, Korean checklist wording, and Korean behavior substructure under fixed schema headings. Do not produce an English skeleton and translate it afterward.

Use independent review subagents to review writer packets or atom drafts against the same approved criteria document, `작성/리뷰 공통 품질 기준`, `change-judgment-policy.md`, the service logic inventory, and the No Example Leakage rule. A review subagent must not invent hidden reviewer-only quality bars. It fails the packet or draft only when a shared criterion or explicit phase gate is not satisfied, including when required perspectives are missing without a not-applicable reason, the domain map is missing or unsupported, meaningful source behavior is missing from the inventory, docs do not explain what the service does under relevant conditions, branches, validations, permissions, state transitions, persistence effects, integrations, errors, or recovery paths, an atom is too broad, a split gap is vague or evasive, inferred intent/rules are unmarked, source evidence is missing, source identifiers appear without natural-language behavior, reference example prose appears without user/source trace, judgment labels are absent or unsupported, missing required behavior is confused with out-of-scope behavior, unapproved implementation is confused with implemented-plan candidates, candidate domains are treated as confirmed without approval, Korean docs retain English template residue, translated-English phrasing, English placeholders, or method-call-sequence-only `Current Implementation`, any judgment-relevant meaning line is missing an AID, any AID is duplicated across the docs set, existing AID values are renumbered instead of preserved, judgment-bearing lines or source evidence lines have no AID, change plans or review findings omit related AID values when they can be known, the reviewer cannot explain the implemented behavior from the docs alone, the docs cannot be used as code judgment criteria, or `Current Implementation`, `Planned Changes`, and `Gaps` are collapsed. If review fails, revise the criteria document, change plan, evidence packet, service logic inventory, or atom draft as needed and rerun review.

## Full Refresh

A full refresh is a first-class operation when the user explicitly asks for it.

1. Read the configured docs root and source root.
2. Read the docs-root source commit baseline metadata.
3. If atomization criteria are needed and no approved criteria document exists, create or update the draft criteria document through the file-first flow before domain atom work.
4. After criteria approval and accepted docs write scope, satisfy the Atomic Docs Goal Gate before docs generation work.
5. Inspect changed source behavior files since the stored source commit hash and map baseline diffs to affected atoms through source-to-atom discovery and graph traversal.
6. Ignore tests, settings, schema, build, and auxiliary files by default unless the user requested auxiliary-file reflection.
7. Inspect project, common, and relevant domain context atoms when they exist.
8. Use source-to-atom seed discovery to find likely domain and atom candidates.
9. Build a service logic inventory for meaningful changed or targeted source behavior.
10. Expand affected scope through atomic graph traversal.
11. Stop graph expansion when related atom files no longer create modification candidates.
12. Present a domain-grouped change plan before writing domain atom docs.
13. Write confirmed updates only after the change plan is accepted.
14. Update the docs-root source commit baseline metadata only after confirmed docs writes for the accepted operation are complete.

## Targeted Docs Operation

Targeted domain or atom work is also a first-class flow. When targeted work overlaps with full-refresh scope, prioritize the current user-requested target. Put adjacent affected scope in follow-up proposals or `Gaps`.

For domain-level work, update the domain context atom when the domain goal, responsibility, included behavior, excluded behavior, adjacent boundary, or common-promotion rule changes. Update `project/project-glossary-atom.md` when source or user intent changes project-wide terms, aliases, forbidden conflations, or domain-scoped terminology.

## Change Plan Requirements

A change plan should group by domain and list:

- the limited first write action for draft criteria creation or update at `project/atomization-criteria.md` when criteria are new or changed
- `검토된 Atom화 관점`, including user-visible criteria additions, removals, revisions, approval status, and whether the criteria document is draft or approved
- user-conversation criteria that must be recorded in the criteria document before source-derived atom drafting
- source exploration results that update the criteria document instead of remaining only in the change plan
- Atomic Docs Goal Gate status, including whether `create_goal` was created or an active Goal already covers the accepted docs operation
- source behavior files inspected
- service logic inventory items, including natural-language behavior, source identifiers, candidate owning atom, and coverage gaps
- AID assignments for new or changed atom meaning lines, and explicit AID migrations when existing IDs cannot be preserved
- affected atom files
- affected atom sections
- judgment labels for review findings, including `matches_confirmed_intent`, `bug_or_regression`, `missing_required_behavior`, `unapproved_implemented_behavior`, `out_of_scope_behavior`, `confirmation_needed`, or `docs_stale`
- related AID values for judgment labels, review findings, coverage gaps, and source evidence mappings whenever the referenced atom lines are known
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
