# Simple Workflow Hooks

The hook checker reports plan-centered workflow readiness and structurally gates `create_goal`.
It does not decide whether natural-language user text approves execution.

Codex runs hook commands with the session `cwd`, so plugin-bundled hooks must not use target-relative paths such as `python hooks/simple_workflow_hook.py ...`. The declared commands use a small inline Python bootstrap and try Python launchers in this order: `python3`, `py -3`, then `python`. The bootstrap resolves `scripts/simple_workflow_hook_check.py` from `SIMPLE_WORKFLOW_PLUGIN_ROOT`, `STAGEFLOW_PLUGIN_ROOT`, `CODEX_PLUGIN_ROOT`, `PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT`, the installed Codex plugin cache under `~/.codex/plugins/cache/**/stageflow*/**/scripts/simple_workflow_hook_check.py`, or the legacy standalone cache under `~/.codex/plugins/cache/**/simple-workflow-plugin/**/scripts/simple_workflow_hook_check.py`. If no checker is found, the hook writes a warning and exits successfully instead of blocking the user's project because of a stale path.

`simple_workflow_hook_check.py` resolves `validate_simple_workflow.py` from its own plugin `scripts` directory with `__file__`, so hook validation does not depend on the target project containing `hooks/simple_workflow_hook.py` or `scripts/validate_simple_workflow.py`.

It keeps the session pointer model:

```text
.simple/sessions/<session-id>/current.json
```

`UserPromptSubmit` emits valid hook wire output with `additionalContext` when the agent needs
Simple Workflow readiness or continuation context. It never emits `PROCEED_ALLOWED` and does not
search prompts for approval keywords. The skill-applying agent owns semantic approval judgment.

It reports when:

- an explicit Simple Workflow prompt has no active request
- an active `plan` or `review` request receives a follow-up prompt that does not mention Simple Workflow again; this is a non-blocking continuation warning that reminds Codex to keep applying Simple Workflow rules
- the active request points to a missing or completed request
- an active plan request is still drafting before `plan.md` exists; this is an expected awaiting-input state, so readiness preserves continuation context and `Stop` allows the user-facing question without running plan validation
- internal `review.md` is missing for the review or completed phase
- internal `review.md` has a stale plan fingerprint
- a v2 plan has `plan_approval_status: pending`; readiness tells the agent that initial or revised execution is on hold until explicit approval

A completed request does not capture unrelated prompts. Explicit Simple Workflow invocation with a
completed pointer asks the agent to create or select a new request.

`PreToolUse` ignores tools other than `create_goal`. It also prepasses unrelated `create_goal`
calls unless their objective contains an exact `.simple/requests/<request-id>/plan.md` path;
mentioning Simple Workflow or `.simple` as a topic is not enough. This keeps Stageflow and other
Goal flows independent. For an in-scope Simple Workflow `create_goal`, it emits
`hookSpecificOutput.permissionDecision: deny` unless all structural requirements hold:

- the selected request metadata is coherent and phase is exactly `review`
- plugin-bundled `--phase review` validation passes
- the objective request id and fingerprint exactly match the selected request and current plan
- `review.md` has the current plan fingerprint and an exact uppercase `PASS` verdict
- local `goal_status` is not already `active`, `completing`, or `completed`

The pre-tool hook does not prove user approval; the agent has already made that conversational
decision before attempting the tool call. Once `plan.md` exists, plan validation resumes normally.
`Stop` emits a blocking wire response only when the current phase's required artifacts or validation
are invalid, while a plan request that has not written `plan.md` yet remains a non-blocking drafting
state so Codex can ask for the user input required to write it.

For material replan after Goal creation, `goal_plan_fingerprint` continues to identify the original
Goal objective and is never changed. `approved_plan_fingerprint` identifies the latest explicitly
approved plan. Review validation allows a coherent v2 `pending` state so Codex can ask for
reapproval, and `Stop` must not deadlock that response. After reapproval, the agent updates the
approved fingerprint and status, reruns review validation, and resumes the same Goal without another
`create_goal` call. Before Goal completion, the skill runs plugin-bundled `--phase completion`; this
is a pre-`update_goal` structural check, not a natural-language approval classifier.

Run manually with the plugin-bundled checker against a target project root:

```powershell
python <plugin-root>/scripts/simple_workflow_hook_check.py --root <target-project-root> --event user_prompt_submit
python <plugin-root>/scripts/simple_workflow_hook_check.py --root <target-project-root> --event pre_tool_use
python <plugin-root>/scripts/simple_workflow_hook_check.py --root <target-project-root> --event stop
```

These commands produce hook wire output. Add `--diagnostic` when manually inspecting the internal
audit result in tests or local debugging.
