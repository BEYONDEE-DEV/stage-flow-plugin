---
name: atomic-docs
description: "Use when the user says atomic-docs, atomic docs, the Stageflow atomic documentation skill, or asks Stageflow to create, update, inspect, refresh, or manage source-based atomic project docs that preserve intent, rules, implementation, planned changes, gaps, source baselines, or graph relationships and support same-functional-behavior reconstruction."
---

# Atomic Docs

Create and maintain source-based project documentation in a configured managed docs root. Preserve user intent, rules, current implementation, planned changes, gaps, source evidence, and graph relationships well enough that a competent implementer can reproduce the same functional behavior without rereading source, except for explicitly excluded internals such as pixel-perfect CSS or library choice.

## Core Contract

- Inspect the target project before writing confirmed atom docs. Treat source files as the default evidence, not workflow artifacts or source identifier lists.
- Support both `repository` storage, which keeps docs inside the current project, and `submodule` storage, which keeps docs in a separate documentation submodule. Never assume a hardcoded `docs/` root.
- Persist the accepted storage mode and managed docs root in `.stageflow/atomic-docs.json`. Explain storage and write scope in plain user language before showing config keys or paths.
- Keep managed docs inside the configured docs root. Keep resumable operation state under `.stageflow/atomic-docs/`; it is not managed docs output or direct code-suitability evidence.
- Do not create a submodule, remote, docs directory, migration, generated docs set, or baseline outside an accepted write action.
- Make `<doc-root>/project/atomization-criteria.md` the first managed-docs write when criteria are needed. Bootstrap acceptance may authorize only config and the criteria draft.
- Run criteria-review/revision automatically until structural PASS, then give the user a decision-ready summary and require criteria approval before docs generation.
- Keep criteria durable and compact. Define shared atom, evidence, split/merge, and not-applicable rules once; record each atomization perspective through the compact result table defined in `atomization-criteria-contract.md`.
- After criteria approval, say that the writing criteria are approved but actual service-logic docs are not written, then ask for a user-enterable scope such as `전체 문서 작성 시작`, `특정 도메인만 작성`, `특정 기능/흐름만 작성`, or `기준을 더 수정`.
- Require a Codex Goal after criteria approval and accepted docs write scope, before inventory, writer/reviewer, graph, project-document, atom, or baseline work. A Goal does not replace user approval, evidence, or review.
- Treat required criteria, writer, reviewer, rerun, and post-write subagents as authorized parts of the accepted operation. Ask again only for deletion, migration, push, an external service call, or a blocker that cannot PASS without a user decision.
- Process multi-domain work sequentially. Each domain bundle uses exactly one writer and four independent draft reviewers for boundary/context, source closure/fact fidelity, implementation reconstruction/high-risk behavior, and domain reporting. Rerun only failed perspectives and perspectives affected by changed evidence.
- After all bundles PASS, run four independent final reviewers for project-wide cross-domain checks. Final reviewers do not repeat already PASSed domain detail unless cross-domain evidence changed or exposes a domain defect.
- Keep project-native feature language visible, reject broad roots as domains, and continue below rejected roots to promote concrete business aggregates, workflows, policies, contracts, or state transitions.
- Require source discovery closure: every meaningful route, controller, service, policy, persistence behavior, UI entry, job, event, integration, runtime schema, or runtime setting in scope must map to an atom/AID, a coverage gap, `out_of_scope`, or a justified not-applicable result.
- Treat behavior-relevant tests, DB or validation schemas, migrations, route configuration, and runtime settings as conditional evidence. Exclude generated, build, vendor, or format-only files only when they do not affect runtime behavior.
- Write natural-language behavior, not endpoint, class, method, or call-sequence inventories. Preserve relevant inputs, branches, validation, permissions, state changes, persistence, integrations, errors, and recovery.
- Use frontmatter `atom_key` as stable atom identity. New AIDs use the current atom's `atom_key`; when an existing meaning line moves, preserve its AID even if its historical prefix differs from the new owner. Resolve current ownership from frontmatter, not the AID prefix.
- Keep `Intent`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps` separate. Mark inferred intent/rules and use controlled judgment labels from `change-judgment-policy.md`.
- Create or update `source-baseline.json` only after project-wide scope is complete at one source commit and all domain and final reviews PASS. Partial work records `source_commit_observed` in operation state and never advances the global baseline.
- Use the selected docs language. Korean docs use Korean-first prose and labels around fixed schema headings, identifiers, AIDs, and controlled labels.
- Run the plugin-bundled validator from `<plugin-root>/scripts/validate_atomic_docs.py`; never look for that validator under the target project's `scripts/` directory.
- During local plugin iteration, use a fresh cachebuster, reinstall the plugin, and verify installed skill/reference/validator files match the source tree before testing in a new task.

## Required References

Read only the direct references needed for the current operation:

- `references/docs-root-and-config.md` for storage mode, docs-root discovery, config, and recovery.
- `references/atomic-document-contract.md` for atom paths, stable `atom_key`, project documents, and context atoms.
- `references/atomization-criteria-contract.md` for compact criteria structure, perspective results, and criteria-review rules.
- `references/source-convention-and-domain-policy.md` for source interpretation, domain discovery, naming, and boundary review.
- `references/service-logic-coverage.md` for reconstruction readiness, source closure, source fidelity, and Goal boundaries.
- `references/atom-format-and-judgment.md` for AIDs, required sections, judgment evidence, and atomicity.
- `references/language-policy.md` for docs language, Korean-first prose, and no-example-leakage rules.
- `references/refresh-flow.md` for full and targeted refresh routing.
- `references/criteria-flow.md` for bootstrap, criteria review, approval summary, and post-approval handoff.
- `references/docs-generation-flow.md` for Goal handoff, operation state, domain queue, and final review orchestration.
- `references/reviewer-perspectives.md` for the four domain and four final reviewer contracts.
- `references/project-documents-and-inventory.md` for non-atom project documents and inventory lifecycle.
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
5. Create or reuse a matching Codex Goal, then create or resume operation state and the operation-local behavior inventory.
6. Discover all behavior-relevant source surfaces in scope, including conditional schema/settings/test evidence, and close each to an atom/AID or explicit disposition.
7. Process each domain bundle through one writer and four draft reviewers until all four PASS before starting the next bundle.
8. Reopen affected bundles when later work changes their evidence, ownership, graph, shared contract, or reconstruction basis.
9. After all bundles PASS, run the four project-wide final reviewers and repair/review any reopened bundle before rerunning affected final perspectives.
10. Run structural validation at bootstrap, docs, and baseline phases as applicable.
11. Update the global source baseline only for a complete project-wide PASS. Keep partial-scope commit evidence operation-local.
12. Complete the Goal and report completion only when the accepted scope, required reviews, structural validation, and reporting conditions are satisfied.

## Boundaries

- Structural validation does not replace semantic writer/reviewer judgment.
- Stageflow artifacts may provide approved requirement evidence, but source remains the default refresh evidence.
- Ask or record a labeled gap when docs root, ownership, atom boundary, source mapping, or graph relationship remains ambiguous.
