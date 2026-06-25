---
name: docs
description: "Use when the user asks to create, update, inspect, refresh, or manage project docs as a submodule-backed natural-language knowledge base, especially docs that preserve intent, rules, current implementation, planned changes, gaps, source-code commit baselines, or atomic graph relationships."
---

# Docs

Use this skill to create, update, inspect, refresh, and manage durable project documentation in a configured documentation submodule. The goal is to preserve user intent, rules, current implementation facts, planned changes, and gaps so future AI/code review can distinguish intended behavior from bugs or uncertain inference.

## Core Contract

- Inspect the target project before writing docs.
- Do not assume a hardcoded `docs/` root.
- Use the documentation submodule root selected through the docs-root discovery contract.
- Ask the user to confirm the docs submodule root even when `.gitmodules` contains exactly one candidate.
- Persist the confirmed root in target-project config at `.stageflow/docs-submodule.json`.
- Keep docs output inside the configured documentation submodule by default.
- Do not create a real submodule, remote repository, generated docs set, or migration unless the user separately asks for that operation.
- Treat source files as the default evidence for docs refresh, not Stageflow request artifacts.
- Respect Stageflow gates when invoked during Stageflow-controlled work.

## Required References

Before acting, read only the references needed for the requested operation:

- `references/docs-root-and-config.md` for docs submodule discovery, confirmation, config, and recovery.
- `references/atomic-document-contract.md` for domain folders, atomic target folders, `atomic.md` sections, confirmed/inferred wording, and forbidden per-atomic status metadata.
- `references/language-policy.md` for choosing the natural language used in docs content while preserving fixed schema headings and code identifiers.
- `references/refresh-flow.md` for full refresh, targeted docs work, source-code commit baseline metadata, changed source behavior files, and change-plan review.
- `references/atomic-graph.md` for `graph_edges`, target keys, traversal, edge validity, duplicate-key conflicts, and path-drift correction.
- `references/stageflow-integration.md` for behavior inside Stageflow requests and approval gates.

## Normal Operation

1. Identify whether the user wants root setup, full refresh, targeted docs work, inspection, graph maintenance, or Stageflow-adjacent documentation.
2. Read the relevant reference files before making changes.
3. Inspect source state and docs-submodule state.
4. Present a change plan before writing docs when refresh or targeted updates would modify documentation.
5. Mark inferred `Intent` or `Rules` as inferred and connect uncertainty to `Gaps` until the user confirms it.
6. Preserve `Current Implementation`, `Planned Changes`, and `Gaps` as separate knowledge categories.
7. Follow the docs language policy: use the user-requested language, otherwise the existing docs-submodule dominant language, otherwise the current conversation language.
8. Store freshness as one source-code commit hash baseline in docs-root metadata, not as per-atomic freshness/status fields inside `atomic.md`.

## Boundaries

- This skill is instruction-first. It does not imply a runtime parser, generator script, external service, or automatic docs write outside the configured documentation submodule.
- Stageflow request artifacts may explain workflow state, but docs refresh evidence defaults to source files.
- If the docs root, domain boundary, atomic target, source-to-atomic mapping, or graph relationship is ambiguous, ask or put the uncertainty in a change plan or `Gaps` instead of writing confirmed intent.

