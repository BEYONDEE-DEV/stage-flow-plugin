---
name: atomic-docs
description: "Use when the user says atomic-docs, atomic docs, atomic docs, the Stageflow atomic documentation skill, or asks Stageflow to create, update, inspect, refresh, or manage atomic project docs as a submodule-backed natural-language knowledge base, especially docs that preserve intent, rules, current implementation, planned changes, gaps, source-code commit baselines, or atomic graph relationships."
---

# Atomic Docs

Use this skill to create, update, inspect, refresh, and manage durable project documentation in a configured documentation submodule. The goal is to preserve user intent, rules, current implementation facts, planned changes, and gaps so future AI/code review can distinguish intended behavior from bugs or uncertain inference.

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
- Treat Stageflow plan approval as separate from docs-submodule approval unless the approved docs operation names the affected docs paths and write actions.
- Make `project/atomization-criteria-atom.md` the first atomic-docs write action after docs-root confirmation when atomization criteria are needed. Use it as a draft review artifact until the user approves the criteria.
- Use only an approved criteria atom as required input for domain writer and review subagents.

## Required References

Before acting, read only the references needed for the requested operation:

- `references/docs-root-and-config.md` for docs submodule discovery, confirmation, config, and recovery.
- `references/atomic-document-contract.md` for domain folders, file-based `*-atom.md` atoms, project/common/domain context atoms, required sections, confirmed/inferred wording, and forbidden per-atomic status metadata.
- `references/language-policy.md` for choosing the natural language used in docs content while preserving fixed schema headings and code identifiers.
- `references/refresh-flow.md` for full refresh, targeted docs work, source-code commit baseline metadata, changed source behavior files, and change-plan review.
- `references/atomic-graph.md` for `graph_edges`, target keys, traversal, edge validity, duplicate-key conflicts, and path-drift correction.
- `references/stageflow-integration.md` for behavior inside Stageflow requests and approval gates.

## Normal Operation

1. Identify whether the user wants root setup, full refresh, targeted docs work, inspection, graph maintenance, or Stageflow-adjacent documentation.
2. Read the relevant reference files before making changes.
3. Confirm the docs-submodule root and inspect existing docs-submodule state.
4. If atomization criteria are needed, make the first atomic-docs write action a limited draft creation or update of `project/atomization-criteria-atom.md`.
5. Put user conversation criteria, prohibitions, atomization concerns, and pending approval state into that criteria draft before relying on chat summaries.
6. Inspect source state to enrich the criteria draft with evidence, not just the change plan.
7. Use the criteria atom itself as the center of review, user revision, and approval. Do not start domain atom writing or domain subagent work until the criteria atom is approved.
8. Mark inferred `Intent` or `Rules` as inferred and connect uncertainty to `Gaps` until the user confirms it.
9. Preserve `Current Implementation`, `Planned Changes`, and `Gaps` as separate knowledge categories.
10. Follow the docs language policy: use the user-requested language, otherwise the existing docs-submodule dominant language, otherwise the current conversation language.
11. Store freshness as one source-code commit hash baseline in docs-root metadata, not as per-atomic freshness/status fields inside atom files.
12. Write only the paths and actions accepted by the user for the current docs operation.

## Boundaries

- This skill is instruction-first. It does not imply a runtime parser, generator script, external service, or automatic docs write outside the configured documentation submodule.
- Stageflow request artifacts may explain workflow state, but docs refresh evidence defaults to source files.
- If the docs root, domain boundary, atom target, source-to-atom mapping, or graph relationship is ambiguous, ask or put the uncertainty in a change plan or `Gaps` instead of writing confirmed intent.
