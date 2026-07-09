# Simple Workflow Hooks

The hook checker is a lightweight auditor for the plan-centered workflow.

Codex runs hook commands with the session `cwd`, so plugin-bundled hooks must not use target-relative paths such as `python hooks/simple_workflow_hook.py ...`. The declared commands use a small inline Python bootstrap and try Python launchers in this order: `python3`, `py -3`, then `python`. The bootstrap resolves `scripts/simple_workflow_hook_check.py` from `SIMPLE_WORKFLOW_PLUGIN_ROOT`, `STAGEFLOW_PLUGIN_ROOT`, `CODEX_PLUGIN_ROOT`, `PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT`, the installed Codex plugin cache under `~/.codex/plugins/cache/**/stageflow*/**/scripts/simple_workflow_hook_check.py`, or the legacy standalone cache under `~/.codex/plugins/cache/**/simple-workflow-plugin/**/scripts/simple_workflow_hook_check.py`. If no checker is found, the hook writes a warning and exits successfully instead of blocking the user's project because of a stale path.

`simple_workflow_hook_check.py` resolves `validate_simple_workflow.py` from its own plugin `scripts` directory with `__file__`, so hook validation does not depend on the target project containing `hooks/simple_workflow_hook.py` or `scripts/validate_simple_workflow.py`.

It keeps the session pointer model:

```text
.simple/sessions/<session-id>/current.json
```

It warns when:

- an explicit Simple Workflow prompt has no active request
- an active `plan` or `review` request receives a follow-up prompt that does not mention Simple Workflow again; this is a non-blocking continuation warning that reminds Codex to keep applying Simple Workflow rules
- the active request points to a missing or completed request
- `plan.md` is missing for the plan phase
- internal `review.md` is missing for the review or completed phase
- the user says a proceed phrase before internal `review.md` passes
- internal `review.md` has a stale plan fingerprint

Run manually with the plugin-bundled checker against a target project root:

```powershell
python <plugin-root>/scripts/simple_workflow_hook_check.py --root <target-project-root> --event user_prompt_submit
python <plugin-root>/scripts/simple_workflow_hook_check.py --root <target-project-root> --event stop
```
