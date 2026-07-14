---
name: atomic-docs
description: "Use when the user says atomic-docs, atomic docs, the Stageflow atomic documentation skill, or asks Stageflow to create, update, inspect, refresh, or manage source-based atomic project docs that preserve intent, business rules, contracts, implementation context, planned changes, gaps, source evidence, or graph relationships for development decisions, implementation review, and change-impact analysis."
---

# Atomic Docs

Create and maintain source-based project documentation that preserves the decisions developers must not have to rediscover or invent. Atomic docs guide source inspection; they do not replace the source tree or mirror every implementation branch. A scope is documented deeply enough when product behavior is unambiguous, verification can be derived, and affected contracts or conflicts are visible while internal technical choices remain free.

## Core Contract

- Inspect the target project before writing confirmed atom docs. Treat source files as the default evidence, not workflow artifacts or identifier lists.
- Support both `repository` storage inside the current project and `submodule` storage in a separate documentation submodule. Never assume a hardcoded `docs/` root.
- Persist the accepted storage mode and managed docs root in `.stageflow/atomic-docs.json`. Explain storage and write scope in plain user language before showing config keys or paths.
- Keep managed docs inside the configured docs root. Keep resumable operation state under `.stageflow/atomic-docs/`; it is not managed docs output or direct implementation evidence.
- Do not create a submodule, remote, docs directory, migration, generated docs set, or baseline outside an accepted write action.
- Make `<doc-root>/project/atomization-criteria.md` the first managed-docs write when criteria are needed. Bootstrap acceptance may authorize only config and the criteria draft.
- Run one lightweight criteria reviewer and reuse it for revision cycles until structural PASS, then give the user a decision-ready summary and require criteria approval before docs generation.
- Keep criteria durable and compact. Store only split/merge, decision-depth, evidence, selective identity, review, project-exception, and unresolved-decision rules. Do not perform domain/atom discovery or store candidates, source inventories, dispositions, or execution state in criteria.
- After criteria approval, say that the writing criteria are approved but actual service-logic docs are not written, then ask for a user-enterable scope such as `전체 문서 작성 시작`, `특정 도메인만 작성`, `특정 기능/흐름만 작성`, or `기준을 더 수정`.
- Require a Codex Goal after criteria approval and accepted docs write scope, before inventory, writer/reviewer, graph, project-document, atom, or baseline work. A Goal does not replace user approval, evidence, or review.
- Treat required criteria, writer, reviewer, rerun, and post-write subagents as authorized parts of the accepted operation. Ask again only for deletion, migration, push, an external service call, or a blocker that cannot PASS without a user decision.
- Before a multi-domain queue starts, run one lightweight ownership/evidence prepass. Confirm shared or high-fan-out owners that would reopen dependent bundles, keep ordinary local owners provisional, and order shared-owner bundles before their dependents. Do not freeze every aggregate owner before writing.
- Process multi-domain bundles sequentially. A bundle is one durable domain or cohesive accepted shard and may contain several atoms; it is not one bundle per atom. Reuse one writer and one independent development-quality reviewer for the whole operation. Reuse one conditional risk/contract reviewer across triggered bundles. Replace an unavailable agent only through a compact role-preserving handoff.
- Build one operation-local source evidence index pinned to `source_commit_observed` and reuse it as a navigation seed. Reviewers independently recheck changed or risk-bearing claims and sample unchanged high-consequence claims; they do not rediscover every entry point or reread every cited line.
- After each writer, run structural bundle preflight before semantic review. New or meaning-changing docs receive development review; structural-only changes receive scoped validation, and source-locator-only changes receive a narrowed evidence check. When both domain and risk reviews apply, run them in parallel against the same recorded bundle attempt. Route reruns by changed meaning or evidence.
- Keep reviewer output findings-only. A normal PASS records scope, source/revision, verdict, representative evidence, and rerun need; detailed comparison tables are conditional risk, integration/baseline, or explicit compliance tools rather than routine PASS artifacts.
- Once a reviewed shared owner is consumed by a dependent bundle, the dependent writer must reference it rather than silently redefine it. A contradiction reopens the shared-owner bundle and only dependents whose PASS basis changed.
- Run one affected-closure integration reviewer when a shared cross-domain contract, ownership, or graph relationship changes. Expand that review to the whole project only for `initial-baseline` or `baseline-diff-refresh`; unrelated multi-domain changes do not require a final semantic reviewer merely because of bundle count.
- Give semantic reviewers both managed docs and the source/evidence needed to check decisions, fidelity, and impact. Do not deny source access as a quality test.
- Measure document depth by decision completeness, not source coverage volume, atom count, line count, or whether source can be discarded. Record why the behavior exists, required rules, observable contracts, consequential branches, state/side effects, failures, concise verification targets, dependencies, and unresolved decisions when applicable.
- Keep project-native feature language visible, reject broad roots as domains, and continue below rejected roots to promote concrete business aggregates, workflows, policies, contracts, or state transitions.
- Close every meaningful behavior aggregate in the accepted scope to an atom/AID, a coverage gap, `out_of_scope`, or a justified not-applicable result. Do not require a separate documentation row for mechanical routes, methods, DTO copying, framework wiring, generated code, or behavior-neutral tests/settings.
- Write natural-language decisions and behavior, not endpoint, class, method, query, DTO, exploit-scenario, or call-sequence inventories. `Current Implementation` should orient the reader to important entry points, storage, integrations, constraints, and non-obvious behavior without replacing source inspection. Include sequence or branch mechanics only when they change a durable contract, transaction effect, observable result, or unresolved decision.
- Keep the durable verification target or invariant in the atom, not an exhaustive test design. Do not enumerate Cartesian products of inputs, states, failures, actor variants, or execution steps merely to prove completeness. Derive detailed cases during implementation or review and put repeatable checks in actual tests; do not create another artifact by default. Add a field list, state table, payload matrix, or failure matrix only when that structure is itself a durable product or contract decision that prose would make ambiguous.
- For an implementation-basis change, keep the concise observable verification condition or invariant with each changed in-scope required AID. Do not require acceptance detail on unrelated historical descriptions or create another AID unless it is independently reviewable.
- Do not rely on existing graph edges alone when checking impact. Inspect relevant domain/common context, glossary source-of-truth terms, shared payload/state/storage/permission/integration contracts, and operation-inventory ownership before graph traversal.
- Only Atomic Impl or an explicit docs/code compliance operation writes an implementation-verification table. Use `## 구현 검증` in `.stageflow/atomic-docs/requests/<request-id>/post-write-review.md` and list only changed in-scope required AIDs with implementation evidence, validation evidence, and verdict or gap.
- Use frontmatter `atom_key` as stable atom identity. Assign AIDs only to confirmed important rules, observable or shared contracts, required changes, active judgments/gaps, or decisions actually needing independent reference. Plain source observations, locators, inventory rows, and explanatory prose have no AID by default. An ordinary docs judgment without an AID identifies its basis by `atom_key`, owning section, and affected behavior; if that natural-language basis is missing or ambiguous, use `confirmation_needed` or a coverage gap instead of a stronger judgment. Explicit Atomic Impl/compliance tracking for changed required AIDs remains unchanged. Preserve existing AIDs when their meaning remains stable; never run cleanup or renumber migration automatically.
- Create a `Gaps` item only when a mismatch, uncertainty, or missing evidence prevents a stronger implementation or review judgment. A missing test, possible runtime exception, or isolated source observation is not a gap by itself. Combine observations only when they share one judgment label, one unresolved decision, and a compatible resolution; keep different labels, independently resolvable behavior, high-risk contracts, adverse branches, and verification outcomes separate.
- Keep graph edges for shared contracts, cross-domain dependency/conflict/replacement, or relationships needed for ownership and impact traversal. Do not add same-domain `related_to` edges merely for discoverability.
- Keep `Intent`, `Outcomes`, `Boundaries`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps` separate. Each meaning has one owning section; another section may cite its AID or heading with only the minimum context needed to read the reference. Mark inferred intent, outcomes, boundaries, or rules and use controlled judgment labels from `change-judgment-policy.md`.
- Distinguish initial baseline, baseline diff refresh, change-impact refresh, targeted work, and inspection. Only an initial/global baseline uses every project bundle; later refreshes start from source diff and graph impact and process affected bundles only.
- Create `source-baseline.json` initially only after every required review PASSes at one source commit. A later `baseline-diff-refresh` may carry forward unaffected PASS results from that trusted baseline only when complete diff/ownership/graph impact evidence and the baseline reviewer prove their basis unchanged. Partial work never advances the global baseline.
- Track bundle attempt, changed artifacts, and finding fingerprint in operation state. A completed writer run with no expected artifact/evidence change or the same blocking finding repeated without basis change must trigger diagnosis and queue adjustment, not another blind review cycle.
- Use the selected docs language. Korean docs use Korean-first prose and labels around fixed schema headings, identifiers, AIDs, and controlled labels.
- Run the plugin-bundled validator from `<plugin-root>/scripts/validate_atomic_docs.py`; never look for that validator under the target project's `scripts/` directory.
- During local plugin iteration, use a fresh cachebuster, reinstall the plugin, and verify installed skill/reference/validator files match the source tree before testing in a new task.
- Treat each direct reference as the detailed owner named in its routing description. Core rules and flow files may summarize when a rule applies, but they must point to the detailed owner instead of independently redefining its failure conditions, state transitions, schema, or controlled vocabulary.

## Required References

Read only the direct references needed for the current operation:

- `references/docs-root-and-config.md` for storage mode, docs-root discovery, config, and recovery.
- `references/atomic-document-contract.md` for the structural path, identity, project-document kind, and context-atom contract.
- `references/atomization-criteria-contract.md` for the normative criteria structure, allowed content, and criteria-review failure contract.
- `references/source-convention-and-domain-policy.md` for the normative source-convention meaning, domain discovery, naming, and boundary gates.
- `references/service-logic-coverage.md` for the normative decision-depth, risk-trigger, accepted-scope coverage, and source-fidelity contract.
- `references/atom-format-and-judgment.md` for the normative AID, required-section, section-ownership, and atomicity contract.
- `references/language-policy.md` for docs language, Korean-first prose, and no-example-leakage rules.
- `references/refresh-flow.md` for operation-profile selection and full or targeted refresh routing.
- `references/criteria-flow.md` for bootstrap sequencing, criteria-review invocation, approval summary, and post-approval handoff.
- `references/docs-generation-flow.md` for Goal handoff, operation state, domain queue, and review orchestration.
- `references/reviewer-perspectives.md` for the normative reviewer selection, verdict, report, and rerun contract.
- `references/project-documents-and-inventory.md` for non-atom project-document lifecycle and operation inventory/evidence flow.
- `references/source-baseline-and-change-plan.md` for the normative baseline eligibility, source commit contract, and accepted change-plan shape.
- `references/validation-contract.md` for validator location, phases, checks, and limits.
- `references/change-judgment-policy.md` for the normative judgment labels, decision order, and evidence requirements.
- `references/atomic-graph.md` for graph keys, paths, traversal, and conflicts.
- `references/stageflow-integration.md` for work inside Stageflow-controlled requests.

## Normal Operation

1. Classify the request as setup, full refresh, targeted work, inspection, graph maintenance, or Stageflow-adjacent docs work.
2. Read config and confirm storage mode, managed docs root, source root, language, and accepted write action.
3. When criteria are missing or changing, write only config and the compact criteria draft. Inspect source only for a user-named code boundary, then run the lightweight criteria-review/revision cycle to PASS.
4. Summarize criteria in user language and stop for user approval. After approval, ask for the docs write scope.
5. Create or reuse a matching Codex Goal, select the operation profile, then create or resume operation state pinned to `source_commit_observed`.
6. Discover domain/atom candidates only now, then build a lightweight behavior/decision inventory and reusable source evidence index for the accepted scope.
7. For initial-baseline or multi-domain work, run the ownership prepass, confirm only shared/high-fan-out owners, and order shared-owner bundles before dependents. For targeted work, inspect only the target's local owner and adjacent contracts.
8. Record a compact domain-grouped write plan and give a non-blocking scale summary with domain, bundle, risk-bundle, shared-owner, and final-review counts. Continue without a second approval when it stays inside accepted paths/actions and boundaries.
9. Reuse one writer and one independent development reviewer across the sequential domain bundles. Process each bundle through the writer, structural preflight, and applicable semantic reviewers; run development/risk reviewers in parallel when both apply to the same bundle attempt.
10. Route reruns from the changed artifact/evidence type and reopen only bundles whose PASS basis changed.
11. Run lightweight integration lint after shared-owner or cross-domain relationship changes. Run one affected-closure integration reviewer only when those relationships changed, and expand it to a project-wide baseline review only for a baseline profile.
12. Run structural validation at bootstrap, docs, and baseline phases as applicable.
13. Update the global source baseline only for a complete project-wide PASS. Keep partial-scope commit evidence operation-local.
14. Complete the Goal and report completion only when the accepted scope, applicable reviews, structural validation, and reporting conditions are satisfied.

## Boundaries

- Structural validation does not replace semantic writer/reviewer judgment.
- Stageflow artifacts may provide approved requirement evidence, but source remains the default refresh evidence.
- Managed docs may point developers to source for technical detail; needing source for internal implementation mechanics is not a documentation failure.
- Ask or record a labeled gap when ownership, product behavior, contract meaning, source mapping, graph relationship, or verification condition remains ambiguous.
