---
name: atomic-docs
description: "Use when the user says atomic-docs, atomic docs, atomic docs, the Stageflow atomic documentation skill, or asks Stageflow to create, update, inspect, refresh, or manage atomic project docs as a submodule-backed natural-language knowledge base, especially docs that preserve intent, rules, current implementation, planned changes, gaps, source-code commit baselines, or atomic graph relationships."
---

# Atomic Docs

Use this skill to create, update, inspect, refresh, and manage durable project documentation in a configured documentation submodule. The goal is to preserve service logic as natural-language source-of-truth docs: user intent, rules, current implementation facts, planned changes, and gaps must be detailed enough that future AI/code review can judge whether source code matches the approved docs baseline, is buggy, is missing required behavior, implements unapproved behavior, is out of scope, is stale, or still needs confirmation.

## Core Contract

- Inspect the target project before writing confirmed atom docs. A criteria draft may be created first from the user's conversation after the docs root and limited draft write action are accepted.
- Do not assume a hardcoded `docs/` root.
- Use the documentation submodule root selected through the docs-root discovery contract.
- Ask the user to confirm the docs submodule root even when `.gitmodules` contains exactly one candidate.
- Persist the confirmed root in target-project config at `.stageflow/docs-submodule.json`.
- Keep docs output inside the configured documentation submodule by default.
- Do not create a real submodule, remote repository, generated docs set, or migration unless the user separately asks for that operation.
- Treat source files as the default evidence for docs refresh, not Stageflow request artifacts.
- Respect Stageflow gates when invoked during Stageflow-controlled work.
- Do not write managed docs, atom files, graph corrections, source-baseline metadata, migrations, or `.stageflow/docs-submodule.json` until the user has accepted the explicit docs operation scope and change plan.
- If the current user request explicitly asks to start, redo, or recreate atomic docs and confirms the managed docs root, treat that request as accepted bootstrap scope for only `.stageflow/docs-submodule.json` and `<doc-root>/project/atomization-criteria-atom.md`; write those bootstrap files in the same turn and then stop for criteria review.
- Treat Stageflow plan approval as separate from docs-submodule approval unless the approved docs operation names the affected docs paths and write actions.
- Make `project/atomization-criteria-atom.md` the first atomic-docs write action after docs-root confirmation when atomization criteria are needed. Use it as a draft review artifact until the user approves the criteria.
- Use only an approved criteria atom as required input for domain writer and review subagents.
- Do not require a Codex Goal for bootstrap criteria draft creation. After criteria approval, require a Codex `create_goal` call before starting docs generation work such as project/common/domain atom writing, service logic inventory, writer/reviewer subagents, graph edges, or source-baseline updates.
- The Atomic Docs Goal must cover the approved criteria atom path, docs root, accepted docs write scope, natural-language service logic coverage, writer/reviewer cycle, and completion condition. If an active Goal already covers the same atomic-docs operation, continue inside that Goal; if Goal creation is unavailable or fails, stop before docs generation and report the blocker.
- A Codex Goal does not replace criteria approval, accepted docs scope, judgment labels, source evidence, or user review. Complete the Goal only after the accepted docs operation is actually complete; do not complete it while work is incomplete, waiting for user input, or failing review.
- Treat approved criteria as the rule for producing docs, not as the docs themselves. The generated docs set must contain the meaningful service logic in natural language before it can be used as a code suitability standard.
- Document meaningful application, service, and domain logic in natural language, including conditions, branches, state transitions, validation, permissions, policy rules, persistence effects, external integrations, errors, and recovery behavior when they affect runtime or product/operations meaning.
- Do not count endpoint lists, controller summaries, service class summaries, file names, method names, or source identifiers alone as coverage.
- Use controlled judgment labels from `references/change-judgment-policy.md` for code review findings, `Gaps`, and change plan items. Do not infer healthy behavior from the absence of a gap.
- During local plugin iteration, do not start atomic-docs work from a stale installed cache path. Reinstall the plugin with a fresh cachebuster and verify the installed cache includes `change-judgment-policy.md`, criteria file-first rules, and No Example Leakage rules.

## Required References

Before acting, read only the references needed for the requested operation:

- `references/docs-root-and-config.md` for docs submodule discovery, confirmation, config, and recovery.
- `references/atomic-document-contract.md` for domain folders, file-based `*-atom.md` atoms, project/common/domain context atoms, required sections, confirmed/inferred wording, and forbidden per-atomic status metadata.
- `references/language-policy.md` for choosing the natural language used in docs content, preventing reference-example leakage into managed docs, and preserving fixed schema headings and code identifiers.
- `references/refresh-flow.md` for full refresh, targeted docs work, source-code commit baseline metadata, changed source behavior files, and change-plan review.
- `references/change-judgment-policy.md` for classifying source behavior as matching confirmed intent, bug/regression, missing required behavior, unapproved implementation, out-of-scope behavior, confirmation needed, or stale docs.
- `references/atomic-graph.md` for `graph_edges`, target keys, traversal, edge validity, duplicate-key conflicts, and path-drift correction.
- `references/stageflow-integration.md` for behavior inside Stageflow requests and approval gates.

## Normal Operation

1. Identify whether the user wants root setup, full refresh, targeted docs work, inspection, graph maintenance, or Stageflow-adjacent documentation.
2. Read the relevant reference files before making changes.
3. Confirm the docs-submodule root and inspect existing docs-submodule state. Treat an explicit user-selected managed docs root in the current request as confirmed for the bootstrap scope.
4. If atomization criteria are needed, make the first atomic-docs write action a limited draft creation or update of `project/atomization-criteria-atom.md`. When the current request already accepted bootstrap scope, create or update the config and criteria draft before stopping.
5. Put user conversation criteria, prohibitions, atomization concerns, and pending approval state into that criteria draft before relying on chat summaries.
6. Inspect source state to enrich the criteria draft with evidence, not just the change plan.
7. Use the criteria atom itself as the center of review, user revision, and approval. Do not start domain atom writing or domain subagent work until the criteria atom is approved.
8. After criteria approval and accepted docs write scope, create or reuse a Codex Goal before starting docs generation work; stop if Goal creation is unavailable or fails.
9. Mark inferred `Intent` or `Rules` as inferred and connect uncertainty to `Gaps` until the user confirms it.
10. Preserve `Current Implementation`, `Planned Changes`, and `Gaps` as separate knowledge categories.
11. Build a service logic inventory before domain atom drafting when source behavior is being documented. Map each meaningful logic item to an owning atom or record a coverage gap.
12. Write `Current Implementation` as natural-language behavior facts with source identifiers, not as source identifier lists.
13. Use judgment labels on `Gaps`, change plan items, review findings, or evidence packet items when deciding whether source behavior is implemented, required, missing, buggy, unapproved, out of scope, stale, or confirmation-needed.
14. Follow the docs language policy: use the user-requested language, otherwise the existing docs-submodule dominant language, otherwise the current conversation language.
15. Store freshness as one source-code commit hash baseline in docs-root metadata, not as per-atomic freshness/status fields inside atom files.
16. Write only the paths and actions accepted by the user for the current docs operation.

## Boundaries

- This skill is instruction-first. It does not imply a runtime parser, generator script, external service, or automatic docs write outside the configured documentation submodule.
- Stageflow request artifacts may explain workflow state, but docs refresh evidence defaults to source files.
- If the docs root, domain boundary, atom target, source-to-atom mapping, or graph relationship is ambiguous, ask or put the uncertainty in a change plan or `Gaps` instead of writing confirmed intent.
