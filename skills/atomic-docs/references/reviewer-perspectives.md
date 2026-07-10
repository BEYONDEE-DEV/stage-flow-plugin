# Reviewer Perspectives

## Responsibility

This reference defines the four independent domain draft reviewers and the four independent project-wide final reviewers. Domain reviewers prove local completeness. Final reviewers prove cross-domain coherence without repeating unchanged domain detail.

## Shared Report Contract

Every reviewer report must include:

- `review scope`: the domain bundle or project-wide cross-domain surface reviewed
- `perspective`: exactly one assigned perspective
- `principle files reviewed`: every required principle file for that perspective
- `verdict`: `PASS`, `FAIL`, or `provisional`
- blocking findings with source evidence and affected `atom_key`/AID when known
- evidence that changed since the previous run
- rerun requirement and affected perspectives

A reviewer must not issue PASS when a required principle file was not read. The main agent aggregates reports but cannot replace a missing reviewer or issue that perspective's PASS itself.

## Domain Draft Reviewers

Each active domain bundle uses exactly one writer followed by these four independent reviewers.

### Domain Draft Atom Boundary / Context Hygiene Reviewer

Read `atomic-document-contract.md`, `atom-format-and-judgment.md`, `atomization-criteria-contract.md`, and `source-convention-and-domain-policy.md`.

FAIL when the bundle hides behavior in context atoms, mixes domains and behavior candidates, keeps a broad grouping, uses unsupported naming, produces an over-compressed atom, or leaves a vague split proposal.

### Domain Draft Source Closure / Fact Fidelity Reviewer

Read `service-logic-coverage.md`, `change-judgment-policy.md`, and `atom-format-and-judgment.md`.

FAIL when a meaningful source surface lacks an atom/AID or explicit disposition, source identifiers replace natural-language behavior, or a documented validation, fallback, state, persistence, integration, error, or recovery claim disagrees with the inspected source path.

### Domain Draft Implementation Reconstruction / High-Risk Reviewer

Read `service-logic-coverage.md`, `atom-format-and-judgment.md`, and `atomic-document-contract.md`.

FAIL when implementing the domain from docs still requires arbitrary choices or rereading source, or when applicable forms, payloads, branches, state effects, transactions, permissions, integrations, or failure paths are absent. Require the applicable high-risk matrices or a specific not-applicable reason.

### Domain Draft Reporting Reviewer

Read `source-baseline-and-change-plan.md`, `docs-generation-flow.md`, `change-judgment-policy.md`, and `project-documents-and-inventory.md`.

FAIL when domain evidence, operation state, labels, unresolved decisions, or partial-scope wording is inconsistent. This reviewer may confirm that the bundle is ready to join the project-wide final review, but it must not approve or update the global source baseline.

## Domain Reviewer Answer Sheet

The source and reconstruction reviewers must answer:

- Can the same domain behavior be implemented from these docs alone?
- Which fields, branches, validations, state effects, or failures still require source?
- Do any source identifiers appear without natural-language behavior?
- Does every meaningful source surface have an atom/AID, gap, `out_of_scope`, or not-applicable result?
- Which judgment-bearing claims were checked against their actual entry and branch paths?

Use a claim audit shape equivalent to `AID claim -> checked entry path -> null/blank/default/fallback/exception branch -> source evidence` where the claim needs source fidelity review.

## Project-Wide Final Reviewers

Run these four independent reviewers only after every accepted domain bundle has four PASS results. Final reviewers trust unchanged domain-level evidence and focus on project-wide relationships. They do not repeat every row-level or branch-level domain check.

### Final Atom Boundary / Context Hygiene Reviewer

Check cross-domain ownership, duplicate responsibilities, hidden shared behavior, project/common promotion, context boundaries, and graph consistency. Reopen a domain when the project-wide view exposes a local boundary defect.

### Final Source Closure / Fact Fidelity Reviewer

Check project-wide inventory closure, source surfaces that cross domains, shared persistence or integration ownership, and evidence changed after a domain PASS. Recheck local source claims only when cross-domain evidence changed or reveals a contradiction.

### Final Implementation Reconstruction / High-Risk Reviewer

Check end-to-end flows that cross domains, frontend/backend contract continuity, shared state transitions, error propagation, recovery, and high-risk behavior spanning more than one bundle. Do not redo isolated domain matrices that remain unchanged and already PASSed.

### Final Baseline / Reporting Reviewer

Decide whether the accepted scope is actually project-wide, every domain and final perspective PASSed at one source commit, no blocker prevents project-wide reconstruction/judgment readiness, and user-facing completion claims match that state. This is the only reviewer perspective that can approve global baseline creation or update.

## Rerun Policy

- After a domain FAIL, rerun the failed perspective and any perspective whose evidence changed.
- Do not rerun unaffected perspectives merely because another perspective failed.
- When a final reviewer finds a domain-specific defect, reopen that bundle, rerun its writer and affected domain reviewers, then rerun every final perspective whose basis changed.
- Reviewer FAIL is not completion and is not a Goal blocker when it can be corrected inside the accepted scope.
- Ask the user only when PASS requires a user decision or a separately authorized destructive or external action.
