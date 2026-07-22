---
name: simple-workflow
description: "Use when the user explicitly asks to use Simple Workflow, simple-workflow, `.simple`, or the Simple Workflow plugin, or when an active `.simple` session pointer exists. Enforces a small plan-centered workflow: challenge inferred intent before confirmation, write `plan.md`, review it with a subagent, let the agent determine explicit user approval from conversation context, and structurally gate `create_goal` against the reviewed request."
---

# Simple Workflow

Use this skill to keep Codex work tied to a single human-readable plan while preserving an internal review record.

## Core Rule

Follow exactly this sequence:

1. Listen to the user's requirements.
2. Inspect the project and infer the user's intent, expected outcome, boundaries, and assumptions.
3. Before the first user intent confirmation, run the bounded `Intent Challenge Review`. Disclose every material finding, obtain the user's decision without silently changing the request, and repeat the review until no unresolved material finding remains.
4. Ask the user to confirm or correct the challenged intent. Then ask any remaining clarification questions from broad to narrow: 대분류 before 중분류, and 중분류 before 소분류.
5. Write `plan.md` from the confirmed intent and requirements, including the observable outcome, completion criteria, and planned completion evidence for every requirement.
6. Review `plan.md` with a subagent and write internal `review.md`. The reviewer must check that the resolved Intent Challenge result, confirmed intent, and plan agree.
7. If review fails only for a non-material plan defect, revise `plan.md` and repeat the subagent review until it passes. If the reviewer finds a new material requirement problem, return to the user-decision flow in step 3 instead of automatically changing the plan.
8. When the agent determines from conversation context that the user clearly authorizes execution, first persist approval for the current reviewed fingerprint, then reconcile the Goal with `get_goal` and call `create_goal` at most once.
9. Execute the approved `plan.md`, adapt implementation details only inside the approved goal and scope, and run its validation commands.
10. Map every requirement to actual completion evidence, run both post-execution reviews, pass the completion pre-gate, complete the Goal, and then close the local request metadata.

Natural-language approval intent belongs to the agent applying this skill. Hooks must not classify approval with keyword or regular-expression matching. A `UserPromptSubmit` hook may report request readiness, while `PreToolUse(create_goal)` only enforces structural prerequisites after the agent has already determined that the user approved execution.

Do not add approval files, requirements files, goal files, implementation logs, completion summaries, source-requirements, analysis files, service-plan files, plan-compliance reviews, code-review files, Direct Parallel queues, Evidence Map, Inventory matrices, or subagent-only review protocols.

## Request Storage

Resolve the workflow root first, then keep request state under that root:

```text
.simple/
  index.json
  sessions/<session-id>/current.json
  requests/<request-id>/
    state.json
    plan.md
    review.md
```

`index.json`, `current.json`, `state.json`, and `review.md` are internal metadata or internal review records. The only required human workflow artifact is `plan.md`.

Use request IDs in this form: `YYYYMMDD-HHMM-short-slug`.

### Workflow Root Ownership

The workflow root owns the entire `.simple` tree for one request. Resolve it before reading or
writing `index.json`, a session pointer, or request artifacts, and keep every artifact for the
request under that one canonical root.

Use these modes and this precedence:

1. An explicit workflow root is authoritative and is not rediscovered.
2. For a user-declared bundle or a confirmed task spanning at least two independent repositories,
   use the plugin-bundled checker's read-only `--resolve-root --multi-repo --start <cwd>` mode. It
   may select a bundle automatically only from an exact `slot.path` in an ancestor
   `.stageflow-worktrees/slots.json`; if no valid exact match exists, require an explicit root.
3. For a hook continuation from a child repository, use the same resolver. Select the manifest
   bundle only when its `.simple/sessions/<session-id>/current.json` points to the same request.
4. Otherwise preserve the nearest single-repository root. Merely being inside a manifest-backed
   slot does not promote a new or pointerless single-repo request to the bundle.

Whenever the agent creates or selects a request, record the resolved canonical absolute root as
`workflow_root` in that session's `current.json`. This optional field is a
session-bound consistency assertion, not a discovery mechanism: the pointer lives under the root it describes. Existing
pointers without the field remain valid. Hooks read but never backfill or rewrite it.

Never infer a bundle from a path shape such as `worktrees/<name>` or from an individual
repository's `git rev-parse --show-toplevel`. In a confirmed multi-repo request, the bundle root—not
any child Git top-level—is the target project for Simple Workflow purposes.

When the canonical bundle and a child repository contain the same request id, compare
`plan.md`, `review.md`, and `state.json` without changing either copy. If all three files exist and
are byte-identical, warn with both paths and continue from the canonical bundle. If any file is
missing or different, report both paths and block only the in-scope Simple Workflow `create_goal`;
UserPrompt and Stop remain non-blocking, and unrelated Goal calls prepass. Never automatically
move, merge, align, or delete duplicate artifacts. Tell the user to remove the stale child copy or
align it manually, then allow the same canonical request and fingerprint to be retried.

Allowed phases are `plan`, `review`, and `completed`.

Use `state.json` as the local workflow source of truth. `current.json` and the selected `index.json` request entry must mirror its phase. New requests use integer `workflow_version: 2`, exact integer `intent_challenge_version: 1`, `plan_approval_status: pending|approved`, and may record `goal_status` as `pending`, `active`, `completing`, or `completed`. The intent marker means the request must use the structured Intent Challenge review contract. Marker-free existing v2 and legacy requests retain their previous review schema; any other marker value is invalid. After Goal creation, `goal_plan_fingerprint` permanently identifies the plan fingerprint named in the original Goal objective, while `approved_plan_fingerprint` identifies the latest plan explicitly approved for execution. Requests without `workflow_version` are legacy requests; unknown versions are invalid. Readers must accept legacy `id`/`request_id` and `phase`/`status` key variants, but the selected request id and phase values must agree.

The phase transitions are:

```text
plan -> review -> completed
```

- Enter `review` only after the current `plan.md` has a passing subagent review and matching fingerprint.
- Keep phase `review` while approval is pending, while approved work is executing, and during completion preparation. The only allowed v2 state triples are `plan|pending|pending`, `review|pending|pending`, `review|approved|pending`, `review|approved|active`, `review|pending|active`, `review|approved|completing`, and `completed|approved|completed` in `phase|plan_approval_status|goal_status` order.
- Enter `completed` only after approved work, validation, and both post-execution reviews pass and `update_goal(status="complete")` succeeds.

## Artifact Rules

For `workflow_version: 2`, `plan.md` must include `# Plan`, `## Summary`, `## Outcome And Completion Criteria`, `## Requirements Coverage`, `## Change Targets`, `## Flow Check`, `## Validation`, and `## Out Of Scope`. The outcome section must name the user-visible or system-visible final state and how it can be observed. The requirements table must use `Requirement | Plan | Completion Evidence`; every `REQ-###` needs a concrete execution plan and a concrete planned evidence source. Legacy requests keep their existing plan shape.

## Shared Planning And Review Principles

Use the same principles when writing `plan.md`, reviewing `plan.md` with a subagent, and reviewing the implemented code after changes are made:

- Preserve the user's confirmed intent and the approved scope.
- Give every `REQ-###` a concrete, verifiable execution plan.
- Define the observable outcome first and tie every `REQ-###` to planned and actual completion evidence.
- Tell the user about relevant flow problems discovered while planning or implementing, even when they were pre-existing or outside the requested change.
- Clearly separate in-scope problems from out-of-scope issues; do not fix out-of-scope issues without user approval.
- Keep validation tied to the real affected product, feature, state, data, user, command, hook, or validator flow.
- Write human-readable artifact and review body text in Korean while preserving fixed control tokens.

`## Flow Check` in `plan.md` must state whether the affected product, feature, state, data, user, command, hook, and validation flows are coherent after considering the planned changes. It must tell the user about any relevant flow problem discovered during planning, even when the problem was pre-existing and was not caused by the requested change. Report flow breaks such as broken user journeys, inconsistent state transitions, missing failure or retry paths, contradictory behavior across entry points, data moving through the wrong owner, or a validation path that no longer proves the real flow. If a discovered problem is outside the requested scope, say so explicitly instead of hiding it.

`review.md` is internal. It must include `# Review`, `## Reviewed Plan Fingerprint` with `Reviewed Plan Fingerprint: sha256:<hex>`, `## Reviewer`, `## Verdict` whose complete trimmed body is exactly `PASS`, `## Blocking Issues` with a blocking-specific no-issue value such as `No blocking issues`, `None`, or `차단 없음`, and non-empty `## Flow Check` and `## Question Depth Check` results. Requests with `intent_challenge_version: 1` additionally require `## Intent Challenge Check`: its `Finding | User Decision Or Resolution | Verdict` table records each material finding once with a unique `IC-###`, a substantive Korean decision or resolution, and exact `PASS`; when there were no material findings it contains one `NONE` row with the review basis. `### Intent Challenge Final Verdict` must be exact `PASS`. A non-blocking flow observation does not invalidate a passing plan review. The internal review must use `Shared Planning And Review Principles` and verify that the resolved Intent Challenge result, user-confirmed intent, and `plan.md` agree; its flow result must judge whether the plan exposes all relevant flow problems to the user and keeps the affected flow coherent, not merely whether the Simple Workflow procedure was followed.

After execution reviews pass, append `## Completion Review` to the same `review.md`. It records the latest completion plan fingerprint, exactly one actual-evidence row and exact `PASS` verdict for every planned `REQ-###`, observable outcome evidence, and an exact final `PASS`. Do not create another evidence artifact.

Do not ask the user to read `review.md` as part of the normal workflow. Summarize the review result and tell the user when the plan is ready for approval.

## Language Policy

Write human-readable artifact body text in Korean. This applies to `plan.md` sections such as `## Summary`, `## Requirements Coverage`, `## Change Targets`, `## Flow Check`, `## Validation`, and `## Out Of Scope`, and to internal `review.md` body text such as blocking, flow, question-depth, Intent Challenge resolutions, and notes.

Keep fixed validator contract tokens unchanged when needed: headings, table column names, `REQ-###`, `PASS`, `FAIL`, `sha256`, file paths, commands, code identifiers, and validator status/control values may remain in English or code form.

## Operating Flow

At the start of a Simple Workflow turn, resolve the workflow root using `Workflow Root Ownership`,
then inspect `<workflow-root>/.simple/sessions/<session-id>/current.json` when it exists. When the
skill trigger applies and the pointer is missing, invalid, or completed, the skill-applying agent
creates or selects a request under that same root, writes its canonical absolute `workflow_root` to
the selected session pointer, and then continues. Hooks do not infer activation from prompt strings.

If an active session pointer exists for a request in `plan` or `review` phase, treat follow-up user messages as Simple Workflow continuation even when the prompt does not mention the plugin again. Short answers, confirmations, corrections, and renewed requests such as `응`, `맞아`, `그렇게 해줘`, or `수정해줘` must continue from the active request and follow the same `plan.md`, internal review, validator, and approval rules. A completed request must not capture unrelated follow-up prompts; explicit Simple Workflow invocation starts or selects another request.

Before asking the user to confirm the request, inspect the project enough to understand it and form a first inference of the intent, expected outcome, boundaries, assumptions, and notable affected-flow risks. Run the Intent Challenge Gate below against that first inference. Only after every material finding has a user decision or resolution and the gate passes, state the resulting intent and ask the user to confirm or correct it. Then apply the existing Question Depth Gate before writing `plan.md`.

## Intent Challenge Gate

This gate is mandatory once for every new request with `intent_challenge_version: 1`, after project inspection and the main agent's first inference but before the first user intent confirmation. It is an initial requirements-quality check, not an approval check and not a second implementation-plan review. Do not replay it merely because a later material replan uses the existing re-review and reapproval flow.

Run a bounded subagent review using only the user's request, inspected project facts, the inferred intent, expected outcome, boundaries and assumptions, and plausible alternatives grounded in those facts. Ask the reviewer to challenge:

- whether the requested solution fits the underlying problem;
- false assumptions, contradictions, omissions, and unclear success conditions;
- affected users, systems, owners, and responsibility boundaries;
- simpler or safer alternatives that preserve the intended outcome;
- failure paths, edge cases, irreversible effects, and material risk; and
- mismatches between the request or inference and the actual project.

The reviewer identifies findings; it does not replace the user's intent or authorize a requirement change. For every material finding, the main agent must tell the user the supporting fact, likely impact, and decision needed. Never silently or automatically apply the reviewer's preferred alternative. Include the user's correction or explicit tradeoff acceptance in the next bounded review and repeat until the reviewer returns `PASS` with no unresolved material finding. Only then ask for the first intent confirmation and proceed to the Question Depth Gate.

Do not create a challenge artifact. Preserve the durable result later in the existing `review.md` under `## Intent Challenge Check`. Record every material finding as one unique `IC-###` row with the user's decision or resolution and exact `PASS`, or use one `NONE` row with a substantive Korean review basis when there was no material finding. The final verdict must be exact `PASS`.

## Question Depth Gate

Use three clarification depths:

- `대분류`: request identity, purpose, top-level scope, target user or system surface, expected outcome, and explicit boundaries.
- `중분류`: major behavior areas, ownership, sequencing, state or data responsibility, integration responsibility, and review/approval flow.
- `소분류`: copy/text, exact fallback behavior, edge case detail, validation detail, and small acceptance refinements.

Question depth is adaptive, not a quota. Ask a question only when its answer can materially change the goal, scope, expected outcome, ownership, sequencing, irreversible risk, or validation standard. Infer reversible low-risk details from inspected project facts and record the assumption in `plan.md` when it matters. A depth may have no user question when the bounded subagent check confirms that no decision at that depth can change the plan. Do not ask preference questions whose answers only choose between behaviorally equivalent implementation details.

Before moving from `대분류` to `중분류`, run a bounded subagent check asking whether any unresolved `대분류` question remains. Before moving from `중분류` to `소분류`, run another bounded subagent check asking whether any unresolved `중분류` question remains. Give the subagent only the user's request, inspected project facts, answered questions, and the candidate next-depth questions. The subagent must return `PASS` only when no higher-level question is still needed for `plan.md`.

If the subagent finds a missing higher-level question, ask that question before descending. Do not write `plan.md` while a broad or mid-level decision that can change the plan is still open. Do not create a new artifact for these checks; summarize the latest checkpoint to the user when asking the next batch and record the final result in `review.md` under `## Question Depth Check`.

During the initial `plan.md` review, the reviewer must re-check the resolved Intent Challenge result, the user's confirmed intent, and the plan for consistency. If this review discovers a new material requirement problem, do not automatically revise the requirement or plan. Tell the user the new fact, impact, and decision needed; repeat the Intent Challenge Review with that decision, rerun any Question Depth checkpoints affected by it, rewrite and re-review the plan, and obtain execution approval for the final reviewed fingerprint.

Before moving to the next step, run the plugin-bundled validator against the target project root. The validator lives under the Simple Workflow plugin root, not under the target project's `scripts/` directory:

```powershell
python <plugin-root>/scripts/validate_simple_workflow.py --root <target-project-root> --current --session-id <session-id> --phase plan
python <plugin-root>/scripts/validate_simple_workflow.py --root <target-project-root> --current --session-id <session-id> --phase review
```

Treat validator failures as the next action. Fix the artifact or ask the user for the missing decision.

## Goal Gate And Recovery

After review passes, the agent—not the hook—decides whether the user's latest message clearly approves execution. Words such as `approve`, `proceed`, `승인`, `진행`, or `실행` are examples, not a regular-expression contract; negations, status questions, quoted text, and unrelated uses are not approval.

Immediately after recognizing approval and before `get_goal` or `create_goal`, durably set `plan_approval_status: approved` and `approved_plan_fingerprint` to the current reviewed plan fingerprint. If that write fails, do not call `create_goal`. This `approved + pending` state is the retry-safe proof that the exact plan was authorized.

Before calling `create_goal`, call `get_goal` and reconcile it with the selected request id and reviewed plan fingerprint:

- If no Goal exists, call `create_goal` with an objective naming the request id, exact `.simple/requests/<request-id>/plan.md` path, and reviewed plan fingerprint.
- If a matching Goal is already active, do not call `create_goal` again; repair local `goal_status: active` and continue the same work.
- If a matching Goal is already complete, do not call `create_goal` again; repair the local completed metadata.
- If another unfinished Goal exists, stop and report the conflict instead of replacing it.

The plugin `PreToolUse(create_goal)` hook is a structural gate only. Scope the gate only to Goal objectives containing an exact `.simple/requests/<request-id>/plan.md` path; mentioning Simple Workflow or `.simple` as a topic is not enough. Unrelated Stageflow or other `create_goal` calls must prepass. For an in-scope call, deny the tool unless the path's request id exactly equals the selected request, the selected request is in `review`, metadata is coherent, plugin-bundled review validation passes, the review, current plan, and objective fingerprints match, the review verdict is exactly uppercase `PASS`, and local Goal status is `pending`. V2 additionally requires `approved`, with the approved plan fingerprint matching the same plan; legacy requests retain their existing single-fingerprint gate. Do not write `goal.md`.

For every new Simple Workflow Goal, the objective must contain the canonical host-native absolute
`<workflow-root>/.simple/requests/<request-id>/plan.md` and its `sha256:<64-hex>` fingerprint,
each exactly once. Quote or backtick an absolute path that contains whitespace. The absolute plan
path bootstraps `create_goal` discovery when the hook process cwd differs from the workflow root;
it does not override canonical single-repo or bundle ownership. The hook binds the derived root to
the same session/request, checks optional `current.json.workflow_root`, applies the existing
resolver and duplicate policy, and only then runs the existing review/approval/fingerprint gate.

If an absolute Simple Workflow-like candidate is malformed, repeated, missing, stale, unreadable,
drive-relative, foreign to the execution host, non-canonical, symlinked, or conflicts with another
root/owner/source, fail closed and do not retry discovery from cwd. Only a Goal with no Simple
Workflow plan candidate prepasses as unrelated. Exact legacy relative
`.simple/requests/<request-id>/plan.md` objectives remain compatible only when the existing cwd and
session resolver already finds their root. This bootstrap applies only to `create_goal`;
UserPromptSubmit and Stop keep their existing non-blocking cwd behavior.

After `create_goal` succeeds for a v2 request, record the objective fingerprint as `goal_plan_fingerprint` and set `goal_status: active`; approval was already recorded and must not be rewritten. If `create_goal` fails, preserve `approved + pending` and retry with the same approval. If the post-success state write fails, use the matching active Goal request id and objective fingerprint returned by `get_goal` as authoritative on the next turn, repair `goal_plan_fingerprint` and Goal status, and never call `create_goal` again for recovery. Legacy requests keep the existing single-fingerprint behavior.

## Adaptive Execution And Material Replan

Keep execution flexible without silently changing the approved goal:

- A method-only adaptation changes implementation mechanics but preserves every approved requirement, scope boundary, expected outcome, owner, and validation standard. Do not rewrite `plan.md` or ask for another approval. Explain the deviation and prove equivalent or better completion evidence in both post-execution reviews.
- A material change modifies a requirement, scope boundary, expected outcome, ownership, irreversible risk, or validation standard. Stop before executing the changed work and tell the user what new fact was discovered plus the retry, goal-preserving fallback, or rescope choices.
- Before editing a material plan, obtain the user's decision about the change. Then durably set `plan_approval_status: pending`, revise `plan.md`, repeat the internal review and `--phase review` validation, summarize the revision, and ask for explicit execution approval again.
- Do not repeat the initial Intent Challenge Gate during material replan, including its plan review. Use the existing material-change user decision, affected Question Depth checkpoints, plan review, and reapproval flow instead.
- While a v2 plan is pending approval, `UserPromptSubmit` readiness must say that execution is on hold. `Stop` must still allow Codex to send the reapproval request; hooks must not decide the user's answer.
- After explicit reapproval, update only `approved_plan_fingerprint` to the current reviewed plan fingerprint, set `plan_approval_status: approved`, rerun `--phase review`, and continue the same active Goal. Never call `create_goal` again and never change the immutable `goal_plan_fingerprint`.

If the pending marker write succeeds but a later plan edit or review fails, remain pending and repair that sequence. If the user declines the material change, do not reduce scope silently; either continue the previously approved work when still valid or present a plan-preserving fallback. A rescope becomes executable only after revised plan review and explicit approval.

## Post-Implementation Review

After approved work and validation commands are complete, run bounded subagent review from two perspectives before the final user response. Both reviews must use `Shared Planning And Review Principles`. This gate applies to code-changing and read-only work.

1. `Intent Compliance Review`: compare the confirmed user intent, latest approved `plan.md`, actual diff when code changed, or actual outputs and commands when work was read-only, plus validation results. Its response must list every `REQ-###` with the actual evidence that proves it and identify any method-only adaptation. If the work misses the intent, lacks evidence for a requirement, violates the approved goal or scope, introduces an in-scope regression, or leaves an expected validation failing, Codex must fix it automatically and repeat validation plus both post-implementation reviews.
2. `Flow / Unexpected Issue Review`: inspect the affected user, state, data, failure or recovery, command, hook, and validator flows and independently challenge whether the evidence proves the observable outcome. Its response must cover every `REQ-###`; a test command alone is insufficient when it does not observe the real affected result. If a relevant issue is in scope or caused by the implementation, Codex must fix it automatically and repeat validation plus both post-implementation reviews. If the issue is outside the user's intent, pre-existing, or requires expanded scope, Codex must tell the user before changing it.

Keep requirement-to-evidence coverage in the bounded reviewer responses while reviewing. After both pass, the main agent consolidates their actual evidence into the existing `review.md` Completion Review; do not create a new artifact. A critical outcome that cannot be observed is a verification gap, not a pass. Obtain the smallest missing user-supplied evidence or present retry/fallback/rescope choices instead of claiming completion. Summarize the two review results in the final response. If an out-of-scope or pre-existing issue blocks safe completion, explain the blocker and wait for the user's decision.

## Completion And Partial-Failure Recovery

Complete only when every approved requirement has actual evidence, the observable outcome is proven, validation passes, and both post-execution reviews pass. Use this order:

1. While phase and mirrored metadata remain `review`, write the Completion Review into `review.md`, then run plugin-bundled validation with `--phase completion`. For v2 this requires the latest passing review, current completion fingerprint, exactly one non-empty actual-evidence row with exact `PASS` for every REQ, non-empty observable outcome evidence, exact final `PASS`, `plan_approval_status: approved`, and `approved_plan_fingerprint` equal to the current plan. Do not continue on failure.
2. While phase remains `review`, durably set `state.json` `goal_status: completing`. If this write fails, do not call `update_goal`.
3. Call `update_goal(status="complete")`; this is the first completed transition.
4. After Goal completion succeeds, set the selected `state.json`, session `current.json`, and matching `index.json` entry to phase `completed`; set `state.json` `goal_status` to `completed` while preserving both fingerprints and approval status.
5. Run plugin-bundled validation with `--phase all` and then give the final response. For backward compatibility, `--phase all` accepts an existing completed v2 request without Completion Review; if the section exists, it must be valid. Every new completion must pass step 1 first.

If `update_goal` fails, keep local phase `review` and `goal_status: completing`; use `get_goal` to determine whether the Goal remains active before retrying Goal completion. If Goal completion succeeds but local completion metadata fails, the durable `completing` marker records the recovery path: a matching complete Goal, or no unfinished Goal after completion was requested, means repair only local completed metadata and validation on the next turn. Never create a replacement Goal from `completing`. For read-only work, the same completion order applies after the two reviews compare the approved plan with actual outputs, commands, and validation results.

If any REQ remains unmet, do not label partial work complete. Retry in scope when safe, offer a fallback only when it preserves the approved outcome, or ask the user to approve a material rescope through the replan flow. Completion convenience never overrides the approved goal.
