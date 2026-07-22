# Simple Workflow Hooks

The hook checker reports plan-centered workflow readiness and structurally gates `create_goal`.
It does not decide whether natural-language user text approves execution.

Codex runs hook commands with the session `cwd`, so plugin-bundled hooks must not use target-relative paths such as `python hooks/simple_workflow_hook.py ...`. The declared commands use a small inline Python bootstrap and try Python launchers in this order: `python3`, `py -3`, then `python`. The bootstrap resolves `scripts/simple_workflow_hook_check.py` from `SIMPLE_WORKFLOW_PLUGIN_ROOT`, `STAGEFLOW_PLUGIN_ROOT`, `CODEX_PLUGIN_ROOT`, `PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT`, the installed Codex plugin cache under `~/.codex/plugins/cache/**/stageflow*/**/scripts/simple_workflow_hook_check.py`, or the legacy standalone cache under `~/.codex/plugins/cache/**/simple-workflow-plugin/**/scripts/simple_workflow_hook_check.py`. If no checker is found, the hook writes a warning and exits successfully instead of blocking the user's project because of a stale path.

`simple_workflow_hook_check.py` resolves `validate_simple_workflow.py` from its own plugin `scripts` directory with `__file__`, so hook validation does not depend on the target project containing `hooks/simple_workflow_hook.py` or `scripts/validate_simple_workflow.py`.

Before reading `.simple`, the checker uses one read-only resolver for agent diagnostics and hook
execution. `--root` is authoritative. Agent-confirmed multi-repo work uses
`--resolve-root --multi-repo --start <cwd>` and succeeds automatically only when an ancestor
`.stageflow-worktrees/slots.json` contains an exact `slot.path` that contains the start path; a
missing or malformed manifest requires explicit `--root`. Without `--multi-repo`, a manifest-backed
child remains at its nearest repository root unless the exact bundle has the same session/request
pointer. No `worktrees/<name>` path heuristic or child `git rev-parse --show-toplevel` result can
promote a multi-repo request.

For `PreToolUse(create_goal)`, a new Goal objective supplies one additional bootstrap that does not
depend on hook cwd: exactly one canonical host-native absolute
`<workflow-root>/.simple/requests/<request-id>/plan.md` occurrence and exactly one fingerprint.
Paths containing whitespace must be quoted or backticked. The checker verifies exact path shape,
file existence/readability, canonical containment, no symlink alias/escape, the same session and
request pointer, and optional `current.json.workflow_root`. It then runs the existing resolver from
that location; the objective is accepted only when the resolver returns the same canonical
single-repository or bundle owner. Thus the absolute path bootstraps discovery but never overrides
ownership or duplicate policy.

Any Simple Workflow-like absolute candidate that is malformed, repeated, ambiguous, missing,
stale, drive-relative, foreign to the execution host, non-canonical, symlinked, or inconsistent
fails closed without cwd fallback. The same path or fingerprint repeated twice is also invalid.
Only candidate-free Goals prepass as unrelated. An exact relative plan objective remains a legacy
fallback only when cwd/session discovery already finds the root. UserPromptSubmit and Stop have no
objective and retain their existing non-blocking cwd behavior; no global session registry is added.

It keeps the session pointer model:

```text
.simple/sessions/<session-id>/current.json
```

The skill-applying agent owns new request activation and semantic approval judgment. Hooks do not
search prompt text for `simple workflow`, `.simple`, approval keywords, or any other activation
pattern. Without an active session pointer, `UserPromptSubmit` prepasses.

`UserPromptSubmit` emits valid hook wire output with `additionalContext` only when an active
`plan` or `review` pointer needs continuation context. It reads pointer, phase, approval, and Goal
status without repeatedly running the full validator.

It reports when:

- an active `plan` or `review` request receives a follow-up prompt that does not mention Simple Workflow again; this is a non-blocking continuation warning that reminds Codex to keep applying Simple Workflow rules
- a v2 plan has `plan_approval_status: pending`; readiness tells the agent that initial or revised execution is on hold until explicit approval
- a reviewed v2 plan is `approved + pending`; readiness tells the agent it may reconcile the Goal

A completed request never captures a prompt. When the skill trigger applies, the agent creates or
selects the next request itself.

`PreToolUse` ignores tools other than `create_goal`. It also prepasses unrelated `create_goal`
calls unless their objective contains an exact `.simple/requests/<request-id>/plan.md` path;
mentioning Simple Workflow or `.simple` as a topic is not enough. This keeps Stageflow and other
Goal flows independent. For an in-scope Simple Workflow `create_goal`, it emits
`hookSpecificOutput.permissionDecision: deny` unless all structural requirements hold:

- the selected request metadata is coherent and phase is exactly `review`
- plugin-bundled `--phase review` validation passes
- for v2, approval is `approved` and `approved_plan_fingerprint` matches the current plan; legacy requests keep the single-fingerprint gate
- the objective request id and fingerprint exactly match the selected request, review, approval, and current plan
- `review.md` has the current plan fingerprint and an exact uppercase `PASS` verdict
- local `goal_status` is exactly `pending`

The pre-tool hook does not prove user approval; the agent has already made that conversational
decision and persisted it before attempting the tool call. `Stop` never emits a deny or blocking
wire response and never runs the full validator. Invalid lightweight state may produce a diagnostic
warning on stderr, but Codex can always send the user-facing response.

For a canonical bundle request, the checker read-only compares any immediate child-repository copy
of the same request's `plan.md`, `review.md`, and `state.json`. An identical copy adds a warning with
the canonical and duplicate paths and continues from the bundle. A missing or changed file marks the
copy divergent: UserPrompt and Stop still only warn, unrelated Goals still prepass, and only the
in-scope Simple Workflow `create_goal` is denied. The warning directs manual removal or alignment;
the checker never changes either tree, and the same request may be retried after external recovery.

For material replan after Goal creation, `goal_plan_fingerprint` continues to identify the original
Goal objective and is never changed. `approved_plan_fingerprint` identifies the latest explicitly
approved plan. Review validation allows a coherent v2 `pending` state so Codex can ask for
reapproval, and `Stop` must not deadlock that response. After reapproval, the agent updates the
approved fingerprint and status, reruns review validation, and resumes the same Goal without another
`create_goal` call. Before Goal completion, the skill runs plugin-bundled `--phase completion`; this
is an agent-invoked hard gate that validates the durable Completion Review before `update_goal`, not
a natural-language approval classifier. `--phase all` remains backward compatible with completed v2
requests that predate Completion Review.

Run manually with the plugin-bundled checker against a target project root:

```powershell
python <plugin-root>/scripts/simple_workflow_hook_check.py --root <target-project-root> --event user_prompt_submit
python <plugin-root>/scripts/simple_workflow_hook_check.py --root <target-project-root> --event pre_tool_use
python <plugin-root>/scripts/simple_workflow_hook_check.py --root <target-project-root> --event stop
```

Resolve a root without running a hook event:

```powershell
python <plugin-root>/scripts/simple_workflow_hook_check.py --resolve-root --multi-repo --start <child-repo>
python <plugin-root>/scripts/simple_workflow_hook_check.py --resolve-root --start <single-repo>
```

These commands produce hook wire output. Add `--diagnostic` when manually inspecting the internal
audit result in tests or local debugging.
