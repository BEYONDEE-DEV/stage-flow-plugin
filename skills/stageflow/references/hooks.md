# Stageflow Codex Hooks

## Contents

- [Events](#events)
- [Stdout Wire Output](#stdout-wire-output)
- [PreToolUse](#pretooluse)
- [UserPromptSubmit](#userpromptsubmit)
- [Stop](#stop)
- [Subagent Hooks](#subagent-hooks)
- [Runtime State](#runtime-state)
- [Manual Checks](#manual-checks)

Stageflow ships plugin-provided hooks that audit the three-stage workflow model and block premature file edits. The hooks do not create or repair request artifacts and do not classify natural-language user intent. They record structural state under `.stageflow/hook-state/`, write only Codex hook wire-schema output to stdout, and block unsafe writes until the relevant workflow gate passes.

## Events

`hooks/hooks.json` declares command hooks for:

- `PreToolUse`
- `UserPromptSubmit`
- `Stop`
- `SubagentStart`
- `SubagentStop`

Codex runs hook commands with the session `cwd`, so plugin-bundled hook commands must not use target-relative paths such as `python hooks/stageflow_hook.py ...`. The declared commands use a small inline Python bootstrap and try Python launchers in this order: `python3`, `py -3`, then `python`. This supports POSIX-style environments where `python3` is standard and Windows environments where the Python launcher commonly provides `py -3`. The bootstrap resolves `scripts/stageflow_hook_check.py` from `STAGEFLOW_PLUGIN_ROOT`, `CODEX_PLUGIN_ROOT`, `PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT`, or the installed Codex plugin cache under `~/.codex/plugins/cache/**/stageflow*/**/scripts/stageflow_hook_check.py`. If no checker is found, the hook writes a warning and exits successfully instead of blocking the user's project because of a stale path.

`stageflow_hook_check.py` resolves `validate_stageflow.py` from its own plugin `scripts` directory with `__file__`, so hook validation does not depend on the target project containing `hooks/stageflow_hook.py` or `scripts/validate_stageflow.py`.

The hook resolves the Stageflow project root from the provided root or payload `cwd` by walking upward to the nearest `.stageflow/sessions/<session-id>/current.json`, then falling back to the nearest `.stageflow/index.json` or `.stageflow/requests/`. It intentionally does not use the Git repository root, because Stageflow may live in an orchestration directory that contains multiple nested Git worktrees.

## Stdout Wire Output

`stageflow_hook_check.py` keeps Stageflow's internal audit result separate from the Codex hook stdout response. Internal fields such as `event`, `status`, `severity`, `turn_start_action`, `validation`, `warnings`, and pending clarification details are stored under `.stageflow/hook-state/`; they must not be emitted as top-level stdout JSON fields because Codex hook schemas reject unknown properties.

Hook stdout and `additionalContext` are model-facing workflow guidance, not user-visible transcript text. Codex CLI may show Stop hook `reason` text when a turn is blocked, so Stop reasons must be short, safe, and non-diagnostic. Do not copy raw hook diagnostics, `.stageflow/hook-state` JSON, `turn_start_instruction`, Stop feedback, or preflight marker strings into assistant responses.

Stdout follows the generated Codex hook output schemas:

- No control needed: write nothing to stdout and exit `0`.
- `UserPromptSubmit`: write `hookSpecificOutput.hookEventName: "UserPromptSubmit"` plus `additionalContext` when Stageflow needs to guide the next turn. Use top-level `decision: "block"` only for prompt submission blocks.
- `PreToolUse`: write `hookSpecificOutput.hookEventName: "PreToolUse"`, `permissionDecision: "deny"`, and `permissionDecisionReason` when blocking a tool call.
- `Stop` and `SubagentStop`: write top-level `decision: "block"` and `reason` when blocking. Stop uses a generic public reason while detailed validation state remains in `.stageflow/hook-state/`.
- `SubagentStart`: write `continue: false` and `stopReason` when blocking a subagent start.

Normal hook policy decisions, including deny/block outputs, exit `0`. Only hook execution failures such as invalid input JSON exit non-zero.

## PreToolUse

The hook inspects write-like tools before they run.

Behavior:

- Writes to `.stageflow/**` artifacts are allowed so the workflow can be created or repaired, except that while `DEFINITION_STORE_REQUIRED` is active the main agent is limited to required `01-definition/definition-store/` files. During store-backed definition clarification, live `sync-state.current_gate` controls access before stale turn-start state: store-only gates block `01-definition/definition.md` read/write, targeted-sync gates allow only targeted sync store files, full-consistency gates allow only full-consistency store reports, and `snapshot-current` allows the main agent to sync `definition.md`.
- Read-like tools that target `01-definition/definition.md` are blocked during store-only definition answer turns. The hot path must use `definition-store/working-set.json` instead of repeatedly reading the full snapshot.
- Non-write tools and read-only shell commands return `PREPASS`.
- Non-Stageflow file edits are blocked while an active Stageflow request lacks a valid session current pointer or while the plugin-bundled validator fails `--phase implementation-plan` for the target project root.
- Completed Stageflow requests do not gate unrelated non-Stageflow edits. Explicit Stageflow resume/status/start prompts against a completed current request still return `COMPLETED_CURRENT`.

## UserPromptSubmit

The hook reads `.stageflow/sessions/<session-id>/current.json`, then validates the current request stage with the plugin-bundled `scripts/validate_stageflow.py` against the target project root.

Behavior:

- Command-like Stageflow prompts without a session current pointer, such as `workflow status`, `use Stageflow`, or `resume Stageflow`, record `REQUEST_REQUIRED`, `turn_start_action: create_request`, an internal preflight marker, and store turn state for the Stop hook. Request creation must include `01-definition/definition-store/` with `working-set.json`, `decision-ledger.jsonl`, `trace-index.json`, and `sync-state.json`.
- Non-Stageflow prompts without a session current pointer, including maintenance mentions such as Stageflow plugin docs or hook debugging, record `PREPASS` and `turn_start_action: none`; stdout is empty. This PREPASS state overwrites any stale prior turn state so Stop does not block unrelated later turns.
- Invalid or stale current pointers record `INVALID_CURRENT` with `turn_start_action: repair_current_pointer` or `repair_current_state`.
- Completed current requests record `COMPLETED_CURRENT` with `turn_start_action: start_new_request` only for explicit Stageflow prompts. Non-Stageflow prompts with a completed current pointer record `PREPASS`.
- Active requests record an internal preflight marker:

```text
Stageflow preflight: current=<request-id>, phase=<phase>, validation=<PASS|FAIL|AWAITING_USER>
```

- Active requests also record structural `turn_start_action`: `continue_current_stage` when validation passes; `create_definition_store` when definition has active pending clarifications but no required store; `handle_awaiting_user_clarification` when definition has an active pending clarification batch with a valid store; or `repair_current_stage` when the current stage fails validation for another reason.
- These values are internal hook-state fields. The preflight marker is not required in assistant responses. `UserPromptSubmit` stdout is empty for `PREPASS`; otherwise it uses `hookSpecificOutput.hookEventName: "UserPromptSubmit"` with `additionalContext`, except true prompt blocks use top-level `decision: "block"` and `reason`.
- Pending clarification validation records `AWAITING_USER`; this is normal user-answer waiting, not artifact repair. If the active pending batch lacks `definition-store/`, the hook records `DEFINITION_STORE_REQUIRED` instead and blocks direct `definition.md` handling until the store exists. When `working-set.json.active_pending_questions` exists, `UserPromptSubmit` can use it as a fast path before full validation, return the pending batch from the store, and save a lightweight store snapshot for Stop.
- `UserPromptSubmit` does not classify the user prompt as a follow-up, answer, or stop signal. Stageflow skill instructions must compare the latest user message with the pending batch semantically. Answer turns update `definition-store/`, classify risk in the main agent, set `sync-state.current_gate`, use optional helper candidates, and avoid `definition.md` during store-only gates. Medium-risk answers use `TARGETED_SYNC_REQUIRED`; high-risk, stop, transition, review, or approval paths use `FULL_CONSISTENCY_REQUIRED` or `SNAPSHOT_CURRENT_REQUIRED`.
- Follow-up responses must answer and restate all pending questions/labeled options, then stop. Answer turns must either show the full current or next store batch with every labeled option, or leave `sync-state.current_gate` on `targeted-sync-required`, `full-consistency-required`, or `snapshot-current` for the next turn. Stop-signal turns must record the stop, run the definition transition-risk audit goal, write `01-definition/transition-risk-goal.md` and `01-definition/transition-risk.md`, and ask the user to confirm risk cases before definition review/approval. Definition still does not use `01-definition/goal.md` for this status.
- Implementation-like prompts also validate `--phase implementation-plan`. If that gate fails, the hook records `IMPLEMENTATION_BLOCKED`, `implementation_block_required: true`, and `turn_start_action: repair_implementation_plan_gate`; implementation must not proceed.
- `turn_start_instruction` is mandatory next-action guidance for the main agent.
## Stop

The stop hook reads the previous turn state from `.stageflow/hook-state/`.

Behavior:

- The preflight marker is internal tracking state; the stop hook does not check whether the assistant response includes it.
- `AWAITING_USER` responses must not claim completion or next-stage progress. The Stop hook compares the saved start snapshot with the current `definition-store/` using lightweight JSON state only. Answer-like prompts such as option selections, duplicate challenges, and narrow stop signals require a valid new store decision: `DEC-*` ledger row, turn-start `source_pending_id`, affected IDs, matching trace, and matching `decision_sync`. If the current gate is `targeted-sync-required`, `full-consistency-required`, or `snapshot-current`, that valid decision lets Stop end the turn and the next `UserPromptSubmit`/`PreToolUse` enforces the gate. Otherwise, the valid decision must also change the active pending batch. Follow-up prompts may leave the store unchanged only when the assistant response shows every active pending question and every labeled option (`Option N:`, `선택지 N:`, or `A:` style) from the current store batch. A store with no active pending questions and no recognized sync gate is blocked.
- `TARGETED_SYNC_REQUIRED`, `FULL_CONSISTENCY_REQUIRED`, and `SNAPSHOT_CURRENT_REQUIRED` responses run definition validation on Stop and block if required gate artifacts or fingerprints are incomplete.
- Non-`AWAITING_USER` completion-like responses validate `--phase all`.
- Missing current pointers after explicit Stageflow prompts, missing `definition-store/` after request creation or store repair, invalid current pointers, `AWAITING_USER` completion/next-stage claims, and completion validation failures return a block decision instead of silently warning.

## Subagent Hooks

`SubagentStart` and `SubagentStop` record lightweight lifecycle observations. During definition clarification, `SubagentStart` reads the live store gate, then registers `agent_id -> role -> allowed_gate` under hook state. `PreToolUse` trusts only that registry plus the current live gate, not role text repeated in later tool payloads. Registered roles may write only their matching files: question backlog, question scope transition review, definition-store helper JSON, targeted-sync plan/report JSON, or full-consistency report JSON. They do not count as stage review evidence by themselves. A stage review only passes when the stage's `review/final.md` records `Subagent review.`, matching artifact fingerprints, listed `review/subagents/` shard files, `PASS`, and no blocking issues.

## Runtime State

Hook runtime state may appear at:

```text
.stageflow/hook-state/current-turn.json
.stageflow/hook-state/sessions/<session-id>/main/current-turn.json
.stageflow/hook-state/sessions/<session-id>/agents/<agent-id>/current-turn.json
.stageflow/hook-state/sessions/<session-id>/agents/<agent-id>/role.json
```

Do not treat hook-state files as durable workflow artifacts. Durable request state belongs under `.stageflow/requests/<request-id>/`.

## Manual Checks

Run a pre-tool edit gate check:

```bash
'{"hook_event_name":"PreToolUse","session_id":"session-1","tool_name":"Write","tool_input":{"file_path":"src/app.ts"}}' | python3 <plugin-root>/scripts/stageflow_hook_check.py --event pre_tool_use --root <target-project-root>
```

Run a prompt check:

```bash
'{"hook_event_name":"UserPromptSubmit","session_id":"session-1","prompt":"[$stageflow:stageflow] 상태 확인"}' | python3 <plugin-root>/scripts/stageflow_hook_check.py --event user_prompt_submit --root <target-project-root>
```

Run a stop check:

```bash
'{"hook_event_name":"Stop","session_id":"session-1","last_assistant_message":"구현 완료했습니다."}' | python3 <plugin-root>/scripts/stageflow_hook_check.py --event stop --root <target-project-root>
```

On Windows native shells, use `py -3` instead of `python3` for the same manual checks:

```powershell
'{"hook_event_name":"UserPromptSubmit","session_id":"session-1","prompt":"[$stageflow:stageflow] 상태 확인"}' | py -3 <plugin-root>/scripts/stageflow_hook_check.py --event user_prompt_submit --root <target-project-root>
```
