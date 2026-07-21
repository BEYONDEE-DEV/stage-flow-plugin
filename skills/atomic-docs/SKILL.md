---
name: atomic-docs
description: "Use when the user says atomic-docs, atomic docs, the Stageflow atomic documentation skill, or asks Stageflow to create, update, inspect, refresh, or manage source-based atomic project docs that preserve intent, business rules, contracts, implementation context, planned changes, gaps, source evidence, or graph relationships for development decisions, implementation review, and change-impact analysis."
---

# Atomic Docs

Create source-based docs that give developers useful implementation context before code changes. Preserve purpose, important rules/contracts, non-obvious constraints, ownership/impact, approved requirements, and material unresolved decisions. Atomic docs guide source inspection; they are not a product-behavior specification, do not replace the source tree, and do not target docs-only reimplementation. Depth is sufficient when a developer can find relevant source, understand why an area exists, recognize key constraints/contract touchpoints, and identify conflicts. Exact fields, branches, state mechanics, and failure paths may remain in source.

## Core Contract

- Inspect the target project before writing confirmed atom docs. Treat source files as the default evidence, not workflow artifacts or identifier lists.
- Support both `repository` storage inside the current project and `submodule` storage in a separate documentation submodule. Never assume a hardcoded `docs/` root.
- Persist the accepted storage mode and managed docs root in `.stageflow/atomic-docs.json`. Explain storage and write scope in plain user language before showing config keys or paths.
- Keep managed docs inside the configured docs root. Keep resumable operation state under `.stageflow/atomic-docs/`; it is not managed docs output or direct implementation evidence.
- Do not create a submodule, remote, docs directory, migration, generated docs set, or baseline outside an accepted write action.
- When criteria are needed, first write `<doc-root>/project/atomization-criteria.md`. Bootstrap may also create request state and a domain-only inventory, but no other managed docs or detailed evidence.
- Criteria contains only durable split/merge, depth, evidence, identity, review, project-exception, and unresolved-decision rules. Domain proposals, locators, candidate status, and execution state remain operation-local; the criteria file owns only its own draft/approved marker.
- Before first approval, pin `source_commit_observed`, inspect only to domain-boundary depth, and write a domain proposal. Do not create Atom candidates, detailed evidence, project docs, graph, or baseline.
- Reuse one bootstrap reviewer for criteria structure and source-supported domain boundaries. Revise until both PASS or a domain needs user ownership judgment.
- The first approval jointly accepts criteria, source-supported domain boundaries, and selected write scope. Keep `needs_confirmation` domains outside scope without blocking approved domains.
- After that approval, require a Codex Goal naming approved domain paths before detailed evidence or managed-doc generation. A Goal does not replace approval, evidence, or review.
- Approved scope authorizes required subagents, reruns, current-operation Atom drops, and exact approved existing-Atom actions. Ask again only for unapproved actions, provenance/hash conflicts, migration, push, external calls, or user-decision blockers.
- Before the execution queue, route every selected risk trigger as a local or shared-contract concern, including when one domain has several shards. Close only high-fan-out permission, shared-identifier, money-entitlement, final-projection, and integration contracts before dependents; keep ordinary local owners provisional.
- After Goal handoff, initialize exact selection contract version 4 with mandatory closure/metrics, empty-first append-only bundle/contract retirement history, and metric-backed dispatch cutoffs. Only a pre-Goal bootstrap request may resume before selection exists; after Goal handoff, resume only exact version 4. Do not migrate or mutate a post-Goal v1-v3/unversioned state—start a new version-4 request instead. Reuse the persistent development reviewer for a pre-writer readiness PASS and stable bundle-scoped development/risk review; final request-bound and terminal checks revalidate current routing/readiness/dispatch/history. See `shared-contract-readiness.md`.
- Open semantic invalidation before a post-PASS meaning correction, stale only affected PASSes, and resolve it after impact-selected reruns. Reuse a risk PASS only when the development reviewer confirms the candidate-linked trigger, risky contract meaning, owner/route, adverse behavior, and evidence basis are all unchanged; uncertainty reruns risk review. See `semantic-review-closure.md` and `reviewer-perspectives.md`.
- Process domain bundles sequentially; one durable domain/shard bundle may contain several atoms. Reuse one writer, one development reviewer, and one conditional risk reviewer across the operation, with compact same-role handoff only when needed.
- Keep one revision-pinned locator index, not a field/branch/payload/failure inventory. Reviewers reopen changed or consequential claims instead of rediscovering every source surface.
- After each writer, run structural preflight. Meaning changes receive development review, structure-only changes scoped validation, and locator-only changes a narrow evidence check. Parallel development/risk review shares one bundle attempt; reruns follow actual impact.
- Keep reports findings-only. FAIL uses `remove`, `generalize`, or `correct_selected_claim`; tables are conditional tools. Correctable current-operation removal continues without another deletion approval.
- Once a reviewed shared owner is consumed by a dependent bundle, the dependent writer must reference it rather than silently redefine it. A contradiction reopens the shared-owner bundle and only dependents whose PASS basis changed.
- Write against accepted final owners/relationships, not queue-time availability. Keep unresolved progress relationships operation-local; never retain “does not exist yet” merely because a bundle is later.
- Use affected-closure integration review for changed shared contracts, ownership, or graph. Expand project-wide only for `initial-baseline` or `baseline-diff-refresh`, not merely for multiple domains.
- Final integration/baseline review independently reconciles the current corpus, can reopen affected local defects, and does not mechanically replay unchanged domain checklists.
- Give semantic reviewers both managed docs and the source/evidence needed to check decisions, fidelity, and impact. Do not deny source access as a quality test.
- Measure depth by implementation-context usefulness, not behavior completeness, coverage volume, counts, or source replacement. Retain costly-to-rediscover decisions, important owners/contracts, and impact-changing constraints, not mechanics merely because they exist.
- Keep project-native feature language visible, reject broad roots as domains, and continue below rejected roots to promote concrete business aggregates, workflows, policies, contracts, or state transitions.
- Explore enough to find durable domains, shared owners, and high-value context. Ordinary source-obvious behavior may be omitted without an atom/AID/gap/disposition row.
- Write natural-language decisions, not code inventories. `Current Implementation` orients important entry points, storage, integrations, constraints, and non-obvious behavior without replacing source inspection; include mechanics only when they change durable context.
- General source-context docs do not require a verification target for every observed behavior; keep one only for an approved implementation-basis change or important durable context. Do not preserve Cartesian test combinations in managed docs; use matrices only when their structure is itself durable context.
- For an implementation-basis change, keep the concise observable verification condition or invariant with each changed in-scope required AID. Do not require acceptance detail on unrelated historical descriptions or create another AID unless it is independently reviewable.
- Do not rely on existing graph edges alone when checking impact. Inspect relevant domain/common context, glossary source-of-truth terms, shared payload/state/storage/permission/integration contracts, and operation-inventory ownership before graph traversal.
- Only Atomic Impl or explicit compliance writes `## 구현 검증` in request-local `post-write-review.md`, limited to changed in-scope required AIDs and actual evidence/verdict.
- Use frontmatter `atom_key` as stable identity. Assign AIDs only to important rules/contracts, required changes, active judgments/gaps, or accepted downstream references. Plain observations have none by default. Preserve AIDs; never auto-clean or renumber them.
- Create `Gaps` only when uncertainty or missing evidence blocks trustworthy context or an approved implementation/compliance judgment. Omitted ordinary behavior, AI authorship, missing tests, possible exceptions, or isolated observations are not gaps by themselves.
- Do not expand into another repository or provider merely to inventory defects. Follow external evidence only when a retained claim's owner, shared/external contract, or change impact cannot be judged reliably from accepted local evidence. Keep non-blocking UI improvements, fallback details, and incidental anomalies outside managed Gaps.
- Keep graph edges for shared contracts, cross-domain dependency/conflict/replacement, or relationships needed for ownership and impact traversal. Do not add same-domain `related_to` edges merely for discoverability.
- Keep `Intent`, `Outcomes`, `Boundaries`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps` separate. Each meaning has one owning section; another section may cite its AID or heading with only the minimum context needed to read the reference. Distinguish source-established current contracts from approved desired changes and genuinely unresolved decisions under `atom-format-and-judgment.md`; AI authorship alone does not require an inference marker or Gap.
- Distinguish initial baseline, baseline diff refresh, change-impact refresh, targeted work, and inspection. Only an initial/global baseline considers every project-native feature area and reviews every selected context bundle; later refreshes start from source diff and graph impact and process affected bundles only.
- Create `source-baseline.json` only after the selected project-wide context and all applicable reviews PASS at one commit. It proves reviewed context, not complete behavior coverage. Carry unaffected PASSes only with diff/ownership/graph evidence; partial work never advances it.
- Track bundle attempt, changed artifacts, and finding fingerprint in operation state. Pause new dispatch for a late shared contract or consecutive first-attempt semantic FAILs only when they share one recorded candidate/contract root; resume shared-root work only after readiness PASSes at a strictly higher basis. Raw FAIL count and elapsed time are never quality thresholds.
- For version-4 removal/rollback, map each guarded snapshot path through its artifact/action `atom_key` to the exact stable queue `bundle_id`; invalidate that bundle's current development/risk PASSes, never another same-domain shard. If an approved-existing source key is absent from the queue, retain only final-gate protection instead of inferring a bundle.
- Version 4 retains `operation_metrics.version: "1"` for actual operation, bundle, role, validation, and rerun timing; metrics never choose readiness, pause, or semantic quality.
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
- `references/shared-contract-readiness.md` for the normative version-4 local/shared risk routes, bounded contract state, pre-writer readiness gate, late discovery, and adaptive FAIL diagnosis.
- `references/semantic-review-closure.md` for post-PASS semantic invalidation state, affected reruns, resolution, and request-bound final closure.
- `references/operation-metrics.md` for version-4 timing and rerun records, terminal checks, and snapshot progression.
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
7. For a new version-4 operation, classify `write|merge|drop`, route each selected risk trigger as local or shared-contract, close only bounded high-fan-out contracts, and initialize closure/metrics.
8. Create the persistent development reviewer, require its selection-readiness PASS, run structural selection validation, then create the writer. Record the compact write plan and report domain, bundle, risk, shared-owner, and final-review counts.
9. Reuse that reviewer and one writer across sequential selected bundles. Process each through writer, structural preflight, and applicable semantic review; parallel development/risk review only against the same attempt.
10. On post-readiness shared-contract discovery, record its matching episode with immutable metric cutoff and RFC3339 `paused_at` before any new dispatch; reject both sequence- and timestamp-based pause-window dispatch. Update the prepass and invalidate/rerun only bundle IDs with prior affected PASSes. Diagnose same-root first-attempt FAILs and obtain changed-basis readiness before dispatch.
11. Reapply final candidate admission, run lightweight integration lint after shared-owner or cross-domain relationship changes, and run the selected affected-closure or project-wide reviewer against the current corpus.
12. Resolve closure, retain inventory/evidence, and rerun final selection plus request-bound docs/baseline and both terminal checks against current routing/readiness/dispatch and append-only retirement history; retire temporary state only after terminal PASS.
13. Update the global source baseline only for a complete project-wide PASS. Keep partial-scope commit evidence operation-local.
14. Complete the Goal and report completion only when the accepted scope, applicable reviews, structural validation, and reporting conditions are satisfied.

## Boundaries

- Structural validation does not replace semantic writer/reviewer judgment.
- Stageflow artifacts may provide approved requirement evidence, but source remains the default refresh evidence.
- Managed docs may point developers to source for exact behavior and technical detail. Needing source for fields, branches, state mechanics, failure handling, or internal implementation is not a documentation failure unless an approved implementation-basis requirement makes that detail mandatory.
- Ask or record a labeled gap when ownership, product behavior, contract meaning, source mapping, graph relationship, or verification condition remains ambiguous.
