# Atomic Impl Implementation Flow

## Purpose

Use this flow when a user wants code implemented from requirements, but the requirements first need to become atomic-docs quality implementation criteria. The output path is:

```text
user requirements -> implementation-basis atomic docs -> user approval -> code implementation -> implementation review -> user approval -> final atomic-docs update -> final docs/code compliance
```

## 1. Intake And Routing

1. Restate the requested product, service, workflow, API, UI, data, or operational behavior in the user's language.
2. Identify the target project, affected user/system surface, expected outcome, and explicit boundaries.
3. Inspect enough source and existing managed docs to determine whether the request is new docs work, targeted refresh, full refresh, or Stageflow-adjacent docs work.
4. Read `skills/atomic-docs/SKILL.md` before any managed docs action. Load only the `atomic-docs` reference files routed by that skill for the current operation.
5. Preserve the user's language for user-facing summaries and managed docs prose unless `atomic-docs` language policy selects another language.

## 2. Atomic Docs Gate

Before writing implementation code, ensure the requested behavior has an accepted atomic-docs path.

- If atomic-docs config or managed docs root is missing, follow the `atomic-docs` storage-mode and docs-root setup rules. Stop after the accepted bootstrap/criteria step requires user review.
- If `project/atomization-criteria.md` is missing, draft or update only the criteria document allowed by `atomic-docs`, run criteria review, summarize it, and stop for criteria approval.
- If criteria is approved but docs write scope is not accepted, ask the user to choose or confirm the docs write scope in plain language.
- If docs generation requires a Codex Goal, create or reuse the Goal as required by `atomic-docs` before writing project/common/domain docs, atom files, graph edges, source-baseline metadata, or operation-local inventory.
- Do not treat Stageflow plan approval, chat approval, or code implementation approval as managed-docs-root approval unless the approved docs paths and write actions are named.

## 3. Write Requirements As Implementation-Basis Docs

Write or update managed docs so the accepted behavior can be implemented from docs without rereading source for meaning.

For each meaningful behavior, preserve:

- user intent, confirmed rules, inferred rules marked as inferred, and explicit non-goals
- an observable verification condition or verifiable invariant inside each in-scope confirmed required AID meaning item; do not require a separate acceptance AID unless it is an independently reviewable meaning
- new requested behavior as `Planned Changes` until it is implemented and approved by the user
- existing source-observed behavior as `Current Implementation` only when source evidence proves it already exists
- input conditions, branches, validation/refusal/defaulting, permission or guard behavior
- state transitions, persistence effects, external calls, events, and side effects
- UI or API contract details, payload fields, forms, routes, empty/loading/error states, and save/delete scopes when applicable
- failure, retry, fallback, recovery, and runtime exception behavior
- source evidence, judgment labels, `Gaps`, related `atom_key`, AID, and graph relationships required by `atomic-docs`

Use `Intent` and `Rules` for confirmed purpose and policy. Use `Gaps` or `confirmation_needed` for missing decisions, uncertain behavior, or source evidence that does not yet prove a confirmed rule. Do not write not-yet-implemented requested behavior as `Current Implementation`.

Avoid endpoint lists, source identifier lists, class-role summaries, or method-call sequences as substitutes for natural-language service logic.

## 4. Review And User Approval Before Code

After the docs write/review gates pass, summarize the docs for the user before coding.

The relevant domain reconstruction reviewer must have PASSed from managed docs and approved project context without source access. If that reviewer needs source or an unstated implementation decision, return to docs writing rather than approving implementation.

The summary must include:

- changed docs paths and which path the user should inspect
- behavior that will be implemented from the docs
- important conditions, branches, validations, state changes, side effects, and failures
- unresolved `Gaps`, `confirmation_needed`, or out-of-scope behavior
- whether the docs are a partial-scope or full-scope implementation basis

Ask whether to implement code from those docs. Do not start code implementation until the user explicitly approves.

## 5. Code Implementation From Approved Docs

Implement only behavior covered by the approved docs and accepted scope.

- Use existing project patterns, modules, validators, tests, and integration points.
- If code inspection shows the approved docs are stale, contradictory, or missing required behavior detail, pause implementation and return to the docs update/approval gate.
- If the user requests behavior not in the approved docs, treat it as a docs scope change before coding it.
- Keep unrelated refactors out of scope unless they are necessary to satisfy the approved docs.

## 6. Implementation Review And User Approval

After implementation, validate and review the real affected flow before any final docs update.

1. Run the project tests, validators, linters, or targeted commands that prove the documented behavior.
2. Run `Intent Compliance Review`: compare the confirmed user requirement, approved atomic docs, actual diff, and validation results.
3. Run `Flow / Unexpected Issue Review`: inspect state transitions, data flow, validation, failure/recovery, side effects, changed implementation behavior, out-of-plan changes, and discovered pre-existing issues.
4. Fix implementation issues that are in scope and caused by the change, then rerun validation and both reviews.
5. If the implementation changed from the approved plan, introduced extra behavior, or revealed a pre-existing issue, report it to the user before treating it as approved.

Use the linked Atomic Docs operation's `.stageflow/atomic-docs/requests/<request-id>/post-write-review.md` for the implementation review record. Draft one `## 구현 검증` section with `docs basis` and `implementation basis` once, followed by changed in-scope required AID rows:

```text
관련 AID | 구현 근거 | 검증 근거 | 판정 또는 gap
```

Do not create a separate trace file or copy this table into atoms, project inventory, or `work-state.json`. A compliance-only operation creates or resumes an Atomic Docs request and uses the same path. If either basis changes, recheck only affected rows.

The post-implementation user summary must include:

- implementation summary
- items implemented exactly as the approved docs specified
- items changed from the plan
- extra out-of-plan changes or discovered pre-existing issues
- final atomic docs paths and update contents that will be written after approval

Ask whether to approve the implementation result and final docs update. Do not update final atomic docs until the user explicitly approves.

## 7. Final Atomic Docs Update

After the user approves the implementation result, update atomic docs through the existing `atomic-docs` gates.

- Keep docs write scope, writer/reviewer cycle, post-write gate, judgment labels, source evidence, AID, `atom_key`, and graph rules intact.
- Move completed approved items from `Planned Changes` to `Current Implementation`.
- Add or refresh source evidence and validation basis for the implemented behavior.
- Keep unimplemented, deferred, or unapproved behavior in `Planned Changes`, `Gaps`, `confirmation_needed`, out-of-scope, or discovered pre-existing issue entries as appropriate.
- Do not record out-of-plan changes as confirmed behavior unless the user explicitly approved those changes.
- If final docs update reveals that the implementation or docs are still inconsistent, return to the relevant implementation or docs approval gate instead of reporting completion.
- Preserve the draft `## 구현 검증` section in operation state; do not move it into `Current Implementation`.

## 8. Final Compliance Review

After final docs update, validate the real affected flow rather than only checking files.

1. Compare the confirmed user requirement, approved implementation result, final atomic docs, actual diff, and validation results.
2. Check for missing documented behavior, undocumented implementation behavior, stale docs, unresolved blocking gaps, or validation that does not prove the real flow.
3. Finalize the linked `post-write-review.md` `## 구현 검증` section. Every changed in-scope required AID needs implementation evidence, validation evidence, and a verdict or gap before `matches_confirmed_intent` may be used for that compliance result.
4. If the code differs from the final docs, update docs through the atomic-docs gate or revise code to match the docs before reporting completion.
5. Summarize the final docs/code compliance result, validations run, final docs paths, and remaining out-of-scope or pre-existing issues.
