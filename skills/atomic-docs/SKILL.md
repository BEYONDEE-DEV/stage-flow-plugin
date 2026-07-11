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
- Run criteria-review/revision automatically until structural PASS, then give the user a decision-ready summary and require criteria approval before docs generation.
- Keep criteria durable and compact. Define shared atom, evidence, split/merge, decision-depth, and not-applicable rules once; record project-specific results through the compact table in `atomization-criteria-contract.md`.
- After criteria approval, say that the writing criteria are approved but actual service-logic docs are not written, then ask for a user-enterable scope such as `전체 문서 작성 시작`, `특정 도메인만 작성`, `특정 기능/흐름만 작성`, or `기준을 더 수정`.
- Require a Codex Goal after criteria approval and accepted docs write scope, before inventory, writer/reviewer, graph, project-document, atom, or baseline work. A Goal does not replace user approval, evidence, or review.
- Treat required criteria, writer, reviewer, rerun, and post-write subagents as authorized parts of the accepted operation. Ask again only for deletion, migration, push, an external service call, or a blocker that cannot PASS without a user decision.
- Process multi-domain work sequentially. Each domain bundle uses one writer and one independent development-quality reviewer. Add one independent risk/contract reviewer only when the bundle includes authorization or security, money, destructive actions, external integration, irreversible/high-impact or concurrency-sensitive state transitions, transaction/idempotency, async retry/recovery, privacy-sensitive data, or a shared cross-domain contract. Ordinary CRUD or preference persistence is not a risk trigger by itself.
- Run one project-wide integration/baseline reviewer only when the accepted operation is project-wide, changes more than one domain, changes a shared contract, or seeks a global source baseline. A targeted single-domain operation without those conditions does not need a final reviewer.
- Give semantic reviewers both managed docs and the source/evidence needed to check decisions, fidelity, and impact. Do not deny source access as a quality test.
- Measure document depth by decision completeness, not source coverage volume, atom count, line count, or whether source can be discarded. Record why the behavior exists, required rules, observable contracts, consequential branches, state/side effects, failures, verification conditions, dependencies, and unresolved decisions when applicable.
- Keep project-native feature language visible, reject broad roots as domains, and continue below rejected roots to promote concrete business aggregates, workflows, policies, contracts, or state transitions.
- Close every meaningful behavior aggregate in the accepted scope to an atom/AID, a coverage gap, `out_of_scope`, or a justified not-applicable result. Do not require a separate documentation row for mechanical routes, methods, DTO copying, framework wiring, generated code, or behavior-neutral tests/settings.
- Write natural-language decisions and behavior, not endpoint, class, method, or call-sequence inventories. `Current Implementation` should orient the reader to important entry points, storage, integrations, constraints, and non-obvious behavior without duplicating source.
- Add field lists, branch tables, payload matrices, state matrices, or failure matrices only when compact prose would leave a product, contract, safety, or verification decision ambiguous. Detail display-only fields or internal mappings only when they affect behavior.
- For an implementation-basis change, keep the observable verification condition or invariant with each changed in-scope required AID. Do not require acceptance detail on unrelated historical descriptions or create another AID unless it is independently reviewable.
- Do not rely on existing graph edges alone when checking impact. Inspect relevant domain/common context, glossary source-of-truth terms, shared payload/state/storage/permission/integration contracts, and operation-inventory ownership before graph traversal.
- Only Atomic Impl or an explicit docs/code compliance operation writes an implementation-verification table. Use `## 구현 검증` in `.stageflow/atomic-docs/requests/<request-id>/post-write-review.md` and list only changed in-scope required AIDs with implementation evidence, validation evidence, and verdict or gap.
- Use frontmatter `atom_key` as stable atom identity. Assign AIDs only to durable, independently referenceable intent, rule, contract, required change, judgment, or gap items. Preserve existing AIDs when their meaning remains stable; resolve current ownership from frontmatter, not the AID prefix.
- Keep `Intent`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps` separate. Mark inferred intent/rules and use controlled judgment labels from `change-judgment-policy.md`.
- Create or update `source-baseline.json` only after project-wide scope is complete at one source commit and every required domain, risk, and project-wide review PASSes. Partial work records `source_commit_observed` in operation state and never advances the global baseline.
- Use the selected docs language. Korean docs use Korean-first prose and labels around fixed schema headings, identifiers, AIDs, and controlled labels.
- Run the plugin-bundled validator from `<plugin-root>/scripts/validate_atomic_docs.py`; never look for that validator under the target project's `scripts/` directory.
- During local plugin iteration, use a fresh cachebuster, reinstall the plugin, and verify installed skill/reference/validator files match the source tree before testing in a new task.

## Required References

Read only the direct references needed for the current operation:

- `references/docs-root-and-config.md` for storage mode, docs-root discovery, config, and recovery.
- `references/atomic-document-contract.md` for atom paths, stable `atom_key`, project documents, and context atoms.
- `references/atomization-criteria-contract.md` for compact criteria structure, decision depth, and criteria-review rules.
- `references/source-convention-and-domain-policy.md` for source interpretation, domain discovery, naming, and boundary review.
- `references/service-logic-coverage.md` for decision-complete behavior coverage, conditional detail, source fidelity, and Goal boundaries.
- `references/atom-format-and-judgment.md` for selective AIDs, required sections, judgment evidence, and atomicity.
- `references/language-policy.md` for docs language, Korean-first prose, and no-example-leakage rules.
- `references/refresh-flow.md` for full and targeted refresh routing.
- `references/criteria-flow.md` for bootstrap, criteria review, approval summary, and post-approval handoff.
- `references/docs-generation-flow.md` for Goal handoff, operation state, domain queue, and conditional review orchestration.
- `references/reviewer-perspectives.md` for the required domain reviewer, conditional risk reviewer, and project-wide reviewer.
- `references/project-documents-and-inventory.md` for non-atom project documents and lightweight inventory lifecycle.
- `references/source-baseline-and-change-plan.md` for full-only baseline, source diff sequencing, and accepted change plans.
- `references/validation-contract.md` for validator location, phases, checks, and limits.
- `references/change-judgment-policy.md` for controlled implementation judgments.
- `references/atomic-graph.md` for graph keys, paths, traversal, and conflicts.
- `references/stageflow-integration.md` for work inside Stageflow-controlled requests.

## Normal Operation

1. Classify the request as setup, full refresh, targeted work, inspection, graph maintenance, or Stageflow-adjacent docs work.
2. Read config and confirm storage mode, managed docs root, source root, language, and accepted write action.
3. When criteria are missing or changing, write only config and the compact criteria draft, inspect source to enrich it, and run criteria-review/revision to PASS.
4. Summarize criteria in user language and stop for user approval. After approval, ask for the docs write scope.
5. Create or reuse a matching Codex Goal, then create or resume operation state and a lightweight behavior/decision inventory.
6. Discover the decision-relevant behavior aggregates in scope and close each to an atom/AID or explicit disposition.
7. Record a compact domain-grouped write plan. Continue without a second approval when it stays inside the already accepted paths/actions and approved boundaries; ask only when it expands scope or changes a protected boundary/action.
8. Process each domain bundle through one writer and the required development-quality reviewer. Run the additional risk/contract reviewer only when a recorded trigger applies.
9. Reopen affected bundles when later work changes their evidence, ownership, graph, shared contract, or decision basis.
10. Run one project-wide integration/baseline reviewer only for project-wide, multi-domain, shared-contract, or global-baseline work.
11. Run structural validation at bootstrap, docs, and baseline phases as applicable.
12. Update the global source baseline only for a complete project-wide PASS. Keep partial-scope commit evidence operation-local.
13. Complete the Goal and report completion only when the accepted scope, applicable reviews, structural validation, and reporting conditions are satisfied.

## Boundaries

- Structural validation does not replace semantic writer/reviewer judgment.
- Stageflow artifacts may provide approved requirement evidence, but source remains the default refresh evidence.
- Managed docs may point developers to source for technical detail; needing source for internal implementation mechanics is not a documentation failure.
- Ask or record a labeled gap when ownership, product behavior, contract meaning, source mapping, graph relationship, or verification condition remains ambiguous.
