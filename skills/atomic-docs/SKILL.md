---
name: atomic-docs
description: "Use when the user says atomic-docs, atomic docs, the Stageflow atomic documentation skill, or asks Stageflow to create, update, inspect, refresh, or manage source-based atomic project docs that preserve intent, business rules, contracts, implementation context, planned changes, gaps, source evidence, or graph relationships for development decisions, implementation review, and change-impact analysis."
---

# Atomic Docs

Create source-based project documentation that gives developers useful implementation context before code changes. Preserve selected purpose, important rules/contracts, non-obvious constraints, ownership/impact context, approved requirements, and material unresolved decisions. Atomic docs guide source inspection; they are not a product-behavior specification, do not replace the source tree, and do not target docs-only reimplementation. A scope is deep enough when a developer can find relevant source, understand why an area exists, recognize key constraints/contract touchpoints, and identify conflicts. Exact fields, branches, state mechanics, and failure paths may remain in source.

## Core Contract

- Inspect the target project before writing confirmed atom docs. Treat source files as the default evidence, not workflow artifacts or identifier lists.
- Support both `repository` storage inside the current project and `submodule` storage in a separate documentation submodule. Never assume a hardcoded `docs/` root.
- Persist the accepted storage mode and managed docs root in `.stageflow/atomic-docs.json`. Explain storage and write scope in plain user language before showing config keys or paths.
- Keep managed docs inside the configured docs root. Keep resumable operation state under `.stageflow/atomic-docs/`; it is not managed docs output or direct implementation evidence.
- Do not create a submodule, remote, docs directory, migration, generated docs set, or baseline outside an accepted write action.
- Make `<doc-root>/project/atomization-criteria.md` the first managed-docs write when criteria are needed. Bootstrap may also create Atomic Docs request state and a domain-only inventory, but no other managed docs or detailed evidence.
- Keep only durable split/merge, depth, evidence, identity, review, project-exception, and unresolved-decision rules in criteria. Keep domain proposals, source locators, candidate status, and execution state operation-local; the criteria file owns only its own draft/approved marker.
- Before first approval, confirm the discovery scope, pin `source_commit_observed`, inspect source to domain-boundary depth, and write a domain proposal. Do not create Atom candidates, detailed `evidence.md`, behavior inventory, project docs, graph, or baseline.
- Reuse one independent bootstrap reviewer for both criteria structure and source-supported domain-boundary review. Revise and rerun the affected review until both PASS or a domain needs a user ownership decision.
- Make the first user approval jointly approve the criteria, the source-supported domain boundaries, and the selected domain write scope. A `needs_confirmation` domain stays outside approval and later writing without blocking independently approved domains.
- Require a Codex Goal after that combined approval, naming the approved domain paths, before detailed evidence, Atom-candidate discovery, writer/reviewer bundles, graph, project-document, atom, or baseline work. A Goal does not replace user approval, evidence, or review.
- Treat required subagents and reruns as authorized operation steps. Current-operation Atom drop correction and exact approved existing-Atom delete/merge need no repeated approval. Ask for unapproved existing actions, provenance/hash conflicts, migration, push, external calls, or user-decision blockers.
- Before a multi-domain queue starts, run one lightweight ownership/evidence prepass. Confirm shared or high-fan-out owners that would reopen dependent bundles, keep ordinary local owners provisional, and order shared-owner bundles before their dependents. Do not freeze every aggregate owner before writing.
- New operations use selection contract version 2 and validate `write|merge|drop` before writing. Existing version-1 or unversioned operations continue without migration. Admission, evidence, and validator details belong to `service-logic-coverage.md`, `project-documents-and-inventory.md`, and `validation-contract.md`.
- Selection version 2 requires semantic review closure version 1 after Goal handoff. Open it before a post-PASS meaning correction, stale only affected PASSes, and resolve it after required reruns. Existing operations are not migrated. See `semantic-review-closure.md`.
- Process multi-domain bundles sequentially. A bundle is one durable domain or cohesive accepted shard and may contain several atoms; it is not one bundle per atom. Reuse one writer and one independent development-quality reviewer for the whole operation. Reuse one conditional risk/contract reviewer across triggered bundles. Replace an unavailable agent only through a compact role-preserving handoff.
- Keep one operation-local, revision-pinned locator index. Do not turn it into field, branch, payload, failure, or entry-point inventory. Reviewers reopen changed or consequential claims without rediscovering every source surface.
- After each writer, run structural bundle preflight before semantic review. New or meaning-changing docs receive development review; structural-only changes receive scoped validation, and source-locator-only changes receive a narrowed evidence check. When both domain and risk reviews apply, run them in parallel against the same recorded bundle attempt. Route reruns by changed meaning or evidence.
- Keep reviewer output findings-only. A FAIL chooses `remove`, `generalize`, or `correct_selected_claim`; comparison tables remain conditional risk, integration/baseline, or compliance tools. A correctable whole-Atom `remove` continues through the operation-local drop/removal flow instead of blocking the Goal for another deletion approval.
- Once a reviewed shared owner is consumed by a dependent bundle, the dependent writer must reference it rather than silently redefine it. A contradiction reopens the shared-owner bundle and only dependents whose PASS basis changed.
- Run one affected-closure integration reviewer when a shared cross-domain contract, ownership, or graph relationship changes. Expand that review to the whole project only for `initial-baseline` or `baseline-diff-refresh`; unrelated multi-domain changes do not require a final semantic reviewer merely because of bundle count.
- A required final integration/baseline reviewer must independently reconcile the current corpus rather than inherit upstream PASS conclusions. Compare current glossary, context, inventory, graph, canonical root decisions/Gaps, and final candidate admission; reopen affected bundles before final PASS when they disagree.
- Give semantic reviewers both managed docs and the source/evidence needed to check decisions, fidelity, and impact. Do not deny source access as a quality test.
- Measure document depth by implementation-context usefulness, not product-behavior completeness, source coverage volume, atom count, line count, or whether source can be discarded. Select context when rediscovery is costly, misunderstanding can change a product or operational decision, a shared/external contract or owner matters, or a non-obvious constraint changes impact. Do not document a field, branch, state, or failure merely because it exists.
- Keep project-native feature language visible, reject broad roots as domains, and continue below rejected roots to promote concrete business aggregates, workflows, policies, contracts, or state transitions.
- Explore the accepted source scope enough to identify durable domains, shared owners, and high-value context candidates. Do not require every behavior aggregate to become an atom/AID, gap, `out_of_scope`, or not-applicable row. Omitting ordinary source-obvious behavior is normal and is not a coverage gap.
- Write natural-language decisions and behavior, not endpoint, class, method, query, DTO, exploit-scenario, or call-sequence inventories. `Current Implementation` should orient the reader to important entry points, storage, integrations, constraints, and non-obvious behavior without replacing source inspection. Include sequence or branch mechanics only when they change a durable contract, transaction effect, observable result, or unresolved decision.
- General source-context docs do not require a verification target for every observed behavior. Keep one only for an approved implementation-basis change or important durable context. Do not preserve Cartesian test combinations in managed docs or routine review artifacts; derive repeatable cases in actual tests. Add a field, state, payload, or failure matrix only when it is itself a durable contract or necessary context.
- For an implementation-basis change, keep the concise observable verification condition or invariant with each changed in-scope required AID. Do not require acceptance detail on unrelated historical descriptions or create another AID unless it is independently reviewable.
- Do not rely on existing graph edges alone when checking impact. Inspect relevant domain/common context, glossary source-of-truth terms, shared payload/state/storage/permission/integration contracts, and operation-inventory ownership before graph traversal.
- Only Atomic Impl or an explicit docs/code compliance operation writes an implementation-verification table. Use `## 구현 검증` in `.stageflow/atomic-docs/requests/<request-id>/post-write-review.md` and list only changed in-scope required AIDs with implementation evidence, validation evidence, and verdict or gap.
- Use frontmatter `atom_key` as stable identity. Assign AIDs only to important rules, shared contracts, required changes, active judgments/gaps, or decisions with an existing or accepted downstream reference. Plain observations, locators, inventory rows, and explanatory prose have no AID by default. A judgment without an AID names its `atom_key`, owning section, and affected behavior; if ambiguous, use `confirmation_needed` or a gap. Preserve stable AIDs and never run cleanup or renumber migration automatically. Atomic Impl/compliance tracking remains unchanged.
- Create a `Gaps` item only when a mismatch, uncertainty, or missing evidence prevents trustworthy use of documented context or an approved implementation/compliance judgment. Omitted ordinary behavior, AI authorship, or the general absence of user approval does not create a gap. A missing test, possible runtime exception, or isolated source observation is not a gap by itself. Combine observations only when they share one judgment label, one unresolved decision, and a compatible resolution; keep different labels and independently resolvable high-impact concerns separate.
- Keep graph edges for shared contracts, cross-domain dependency/conflict/replacement, or relationships needed for ownership and impact traversal. Do not add same-domain `related_to` edges merely for discoverability.
- Keep `Intent`, `Outcomes`, `Boundaries`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps` separate. Each meaning has one owning section; another section may cite its AID or heading with only the minimum context needed to read the reference. Distinguish source-established current contracts from approved desired changes and genuinely unresolved decisions under `atom-format-and-judgment.md`; AI authorship alone does not require an inference marker or Gap.
- Distinguish initial baseline, baseline diff refresh, change-impact refresh, targeted work, and inspection. Only an initial/global baseline considers every project-native feature area and reviews every selected context bundle; later refreshes start from source diff and graph impact and process affected bundles only.
- Create `source-baseline.json` initially only after the selected project-wide context set and every applicable review PASS at one source commit. The baseline means project feature areas were considered and the retained context was reviewed; it does not claim every product behavior is documented. A later `baseline-diff-refresh` may carry forward unaffected PASS results only when diff/ownership/graph impact evidence proves their context basis unchanged. Partial work never advances the global baseline.
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
- `references/service-logic-coverage.md` for the normative context-selection, proportional-depth, risk-trigger, source-exploration, and source-fidelity contract.
- `references/atom-format-and-judgment.md` for the normative AID, required-section, section-ownership, and atomicity contract.
- `references/language-policy.md` for docs language, Korean-first prose, and no-example-leakage rules.
- `references/refresh-flow.md` for operation-profile selection and full or targeted refresh routing.
- `references/criteria-flow.md` for bootstrap sequencing, domain-proposal discovery/review, combined approval summary, and post-approval handoff.
- `references/docs-generation-flow.md` for bootstrap-to-execution operation state, Goal handoff, domain queue, and review orchestration.
- `references/semantic-review-closure.md` for post-PASS semantic invalidation state, affected reruns, resolution, and request-bound final closure.
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
3. When criteria are missing or changing, confirm the requested discovery scope, write config and the compact criteria draft, and create or resume Atomic Docs operation state with no accepted write scope yet.
4. Inspect source to domain-boundary depth and write only the operation-local domain proposal. Reuse one bootstrap reviewer for criteria structure and domain-boundary review until both PASS or a user decision is required.
5. Present the criteria, source-supported domain boundaries, unresolved domains, and selectable write scope together. Stop for one combined approval; exclude unresolved or unselected domains from accepted scope.
6. Select the execution profile, create or reuse the approved-domain Goal, then discover tentative context candidates and compact source locators. Partial domain approval is `targeted`, not `initial-baseline`.
7. For a version-2 selection operation, classify `write|merge|drop`, build the queue from write keys and merge targets, link applicable risk triggers to selected Atom keys/contracts, initialize semantic review closure, then run selection validation. Confirm shared/high-fan-out owners before dependents; targeted work checks only local and adjacent owners.
8. Record the compact write plan and report domain, bundle, risk, shared-owner, and final-review counts without pausing approved work.
9. Reuse one writer and one independent context-quality reviewer across the sequential selected domain bundles. Process each bundle through the writer, structural preflight, and applicable semantic reviewers; run development/risk reviewers in parallel when both apply to the same bundle attempt.
10. In a version-2 operation, open semantic review invalidation before a post-PASS meaning or ownership correction and route only affected reruns. Existing version-1 or unversioned operations use their recorded correction/review flow without adding closure state.
11. Reapply final candidate admission, run lightweight integration lint after shared-owner or cross-domain relationship changes, and run the selected affected-closure or project-wide reviewer against the current corpus.
12. Resolve semantic closure and run request-bound structural validation at final docs or baseline phases as applicable.
13. Update the global source baseline only for a complete project-wide PASS. Keep partial-scope commit evidence operation-local.
14. Complete the Goal and report completion only when the accepted scope, applicable reviews, structural validation, and reporting conditions are satisfied.

## Boundaries

- Structural validation does not replace semantic writer/reviewer judgment.
- Stageflow artifacts may provide approved requirement evidence, but source remains the default refresh evidence.
- Managed docs may point developers to source for exact behavior and technical detail. Needing source for fields, branches, state mechanics, failure handling, or internal implementation is not a documentation failure unless an approved implementation-basis requirement makes that detail mandatory.
- Ask or record a labeled gap when ownership, product behavior, contract meaning, source mapping, graph relationship, or verification condition remains ambiguous.
