---
name: atomic-impl
description: "Use when the user asks to implement code from requirements through atomic-docs first, invokes atomic-impl, wants requirements written into atomic docs before coding, asks for docs-first implementation, or wants implementation based on approved atomic-docs managed documentation. Guides Codex from requirements to implementation-basis atomic docs under existing atomic-docs gates, user approval, code implementation, implementation review, user approval, final atomic-docs update, and final docs/code compliance review."
---

# Atomic Impl

Use this skill to turn user requirements into approved atomic-docs implementation criteria before changing code. The goal is to prevent shallow implementation by making the required behavior explicit in managed docs first.

Required path: `requirements -> implementation-basis atomic docs -> user approval -> code implementation -> implementation review -> user approval -> final atomic-docs update -> final docs/code compliance`.

## Core Contract

- Treat the written or updated atomic docs as the implementation source of truth for this request.
- Do not implement code before the relevant atomic docs are written or updated, summarized for the user, and explicitly approved as the implementation basis.
- During the initial implementation-basis docs write, put new requested behavior mainly in `Planned Changes`; use `Intent` and `Rules` for purpose and policy, `Gaps` or `confirmation_needed` for uncertainty, and `Current Implementation` only for behavior already observed in source.
- Do not bypass `atomic-docs` setup, docs-root discovery, criteria approval, docs write scope approval, Goal gate, writer/reviewer cycle, post-write gate, language policy, source-baseline, judgment label, AID, `atom_key`, or graph rules.
- If `.stageflow/atomic-docs.json`, the managed docs root, or `project/atomization-criteria.md` is missing or unapproved, follow the `atomic-docs` bootstrap/criteria flow and stop for approval before docs generation or code implementation.
- Keep the managed docs write scope separate from code implementation approval. Writing docs does not automatically approve code changes.
- If the written docs still contain blocking `confirmation_needed` gaps for the requested behavior, ask the user to resolve them before implementing that behavior.
- After code implementation, run `Intent Compliance Review` and `Flow / Unexpected Issue Review`, summarize the implementation result for the user, and require explicit user approval before final atomic-docs update.
- After that approval, update final atomic docs through the existing `atomic-docs` gates; move completed approved items from `Planned Changes` to `Current Implementation` with source evidence and validation basis.
- Do not record out-of-plan changes, changed implementation behavior, or discovered pre-existing issues as confirmed behavior before user approval.

## Required Reference

Read `references/implementation-flow.md` before taking action. It defines the required sequence from requirement intake through docs write approval, implementation, implementation review, final docs update, and compliance review.

When writing or updating managed docs, also load `skills/atomic-docs/SKILL.md` and only the `atomic-docs` references it routes for the current docs operation.

## User-Facing Approval Gate

After the atomic docs write/review step and before code changes, show the user:

- the changed or newly written docs paths
- a concise behavior summary from those docs
- any remaining `Gaps`, `confirmation_needed`, or out-of-scope items
- the exact implementation basis you will follow

Then ask for explicit approval to implement from those docs. Continue to code only after the user gives a clear positive approval.

## Implementation Basis

During code implementation, compare every behavior change against the approved docs. If implementation reveals the docs are stale, incomplete, contradictory, or too shallow to implement safely, return to the docs update/approval step instead of guessing in code.

## Final Docs Update Gate

After implementation review, show the user the implementation summary, items implemented exactly as approved docs specified, items changed from plan, out-of-plan changes or discovered pre-existing issues, and final atomic docs paths/update contents. Only after explicit approval may completed `Planned Changes` become `Current Implementation`.
