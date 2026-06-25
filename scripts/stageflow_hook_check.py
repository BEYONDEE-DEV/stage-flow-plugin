#!/usr/bin/env python3
"""Fast hook auditor for the three-stage Stageflow model."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


PHASE_TO_VALIDATION = {
    "definition": "definition",
    "implementation-plan": "implementation-plan",
    "implementation": "implementation",
    "completed": "all",
}
WORKFLOW_TOKENS = ("stageflow", "stage flow", ".stageflow", "workflow", "\uc6cc\ud06c\ud50c\ub85c\uc6b0")
IMPLEMENTATION_TOKENS = (
    "implement",
    "implementation",
    "fix",
    "edit",
    "write",
    "change",
    "patch",
    "\uad6c\ud604",
    "\ubc18\uc601",
    "\uc218\uc815",
    "\ubcc0\uacbd",
    "\uace0\uccd0",
    "\uc801\uc6a9",
    "\ucd94\uac00",
    "\uc0ad\uc81c",
    "\uc800\uc7a5",
    "\ud328\uce58",
)
COMPLETION_TOKENS = ("complete", "completed", "done", "\uc644\ub8cc", "\ub05d")
OPTION_ITEM_RE = re.compile(r"(?:^|[;\n|]\s*)((?:Option\s*[1-9]\d*|선택지\s*[1-9]\d*|[A-Z])\s*:[^;\n|]+)", re.IGNORECASE)
AWAITING_USER_COMPLETION_CLAIM_RE = re.compile(
    r"\b(completed|done)\b|완료\s*확인|목표(?:를)?\s*(?:완료|달성)|"
    r"\bdefinition\s+(?:approved|approval|is approved)\b|정의(?:\s*단계)?(?:가|를|은|는)?\s*(?:승인|approved)|"
    r"다음\s*단계(?:로)?\s*(?:진행|이동)|서비스\s*계획(?:을)?\s*(?:작성|진행|시작)|"
    r"구현\s*계획(?:을)?\s*(?:작성|진행|시작)",
    re.IGNORECASE,
)
USER_STOP_SIGNAL_RE = re.compile(
    r"\b(proceed|go ahead|approve|approved|yes)\b|"
    r"구현\s*계획(?:으로|로)?\s*넘어가기|질문\s*그만|충분해?|진행|승인",
    re.IGNORECASE,
)
PENDING_ANSWER_RE = re.compile(
    r"\boption\s*[1-9]\d*\b|선택지\s*[1-9]\d*|"
    r"(?:^|[\s,;/])(?:[1-9]\d*)(?:\s*[,/]\s*[1-9]\d*)+(?:$|[\s,;/])|"
    r"^\s*[1-9]\d*\s*$",
    re.IGNORECASE,
)
PREFLIGHT_MARKER_PREFIX = "Stageflow preflight:"
WRITE_TOOL_TOKENS = (
    "edit",
    "write",
    "notebookedit",
    "apply_patch",
    "apply-patch",
)
SHELL_TOOL_TOKENS = ("bash", "shell", "shell_command", "powershell", "cmd")
WRITE_COMMAND_RE = re.compile(
    r"(\bset-content\b|\badd-content\b|\bout-file\b|\bnew-item\b|\bremove-item\b|"
    r"\bmove-item\b|\bcopy-item\b|\bmkdir\b|\btouch\b|\btee\b|>>|"
    r"(?<![<>=])>(?![>=])|\bpython\b.*\b(open|write_text|Path\().*['\"]w)",
    re.IGNORECASE | re.DOTALL,
)


def safe_segment(value: str) -> str:
    value = value.strip()
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)[:120]


def read_payload() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("hook payload must be a JSON object")
    return value


def extract_prompt(payload: dict[str, Any]) -> str:
    prompt = payload.get("prompt")
    if isinstance(prompt, str):
        return prompt
    messages = payload.get("messages")
    if isinstance(messages, list):
        for item in reversed(messages):
            if isinstance(item, dict) and item.get("role") == "user":
                content = item.get("content")
                if isinstance(content, str):
                    return content
    return ""


def extract_last_assistant(payload: dict[str, Any]) -> str:
    value = payload.get("last_assistant_message")
    if isinstance(value, str):
        return value
    messages = payload.get("messages")
    if isinstance(messages, list):
        for item in reversed(messages):
            if isinstance(item, dict) and item.get("role") == "assistant":
                content = item.get("content")
                if isinstance(content, str):
                    return content
    return ""


def is_explicit_workflow(prompt: str) -> bool:
    lowered = prompt.lower()
    return any(token in lowered for token in WORKFLOW_TOKENS)


def looks_like_implementation(prompt: str) -> bool:
    lowered = prompt.lower()
    return any(token in lowered for token in IMPLEMENTATION_TOKENS)


def looks_like_completion(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in COMPLETION_TOKENS)


def pending_output_requirements(pending_output: str) -> list[tuple[str, list[str]]]:
    requirements: list[tuple[str, list[str]]] = []
    for line in pending_output.splitlines():
        if "pending clarification" not in line or "Question: " not in line or " Options: " not in line:
            continue
        question = line.split("Question: ", 1)[1].split(" Options: ", 1)[0].strip()
        options = line.split(" Options: ", 1)[1].split(" Recommended: ", 1)[0].strip()
        scope = ""
        if "질문 범위: " in line and " Question: " in line:
            scope = line.split("질문 범위: ", 1)[1].split(" Question: ", 1)[0].strip()
            if " [" in scope:
                scope = scope.split(" [", 1)[0].strip()
        transition = ""
        if " Transition option: " in line and " Why this matters: " in line:
            transition = line.split(" Transition option: ", 1)[1].split(" Why this matters: ", 1)[0].strip()
        option_items = [item.strip() for item in OPTION_ITEM_RE.findall(options)]
        if transition.lower() in {"n/a", "none", "없음"}:
            transition = ""
        scope_label = f"[{scope}]" if scope else ""
        required_parts = [part for part in (scope_label, question, transition) if part]
        required_parts.extend(option_items)
        if len(option_items) < 2:
            required_parts.append("at least two explicit option labels such as Option 1: and Option 2:")
        requirements.append((question or "pending clarification", required_parts))
    return requirements


def pending_output_option_items(pending_output: str) -> list[str]:
    options: list[str] = []
    for _question, required_parts in pending_output_requirements(pending_output):
        for part in required_parts:
            if OPTION_ITEM_RE.match(part):
                options.append(part)
    return options


def option_body(option_item: str) -> str:
    if ":" not in option_item:
        return option_item.strip()
    return option_item.split(":", 1)[1].strip()


def classify_awaiting_user_prompt(prompt: str, pending_output: str) -> str:
    if USER_STOP_SIGNAL_RE.search(prompt):
        return "stop_signal"
    if PENDING_ANSWER_RE.search(prompt):
        return "pending_answer"
    lowered_prompt = prompt.lower()
    for option in pending_output_option_items(pending_output):
        body = option_body(option)
        if len(body) >= 8 and body.lower() in lowered_prompt:
            return "pending_answer"
    return "follow_up"


def missing_pending_response_parts(last_message: str, pending_output: str) -> list[str]:
    missing: list[str] = []
    for question_label, required_parts in pending_output_requirements(pending_output):
        for part in required_parts:
            if part and part not in last_message:
                missing.append(f"{question_label}: {part}")
    if not missing and pending_output and not pending_output_requirements(pending_output):
        if "pending clarification" not in last_message.lower() and "대기" not in last_message:
            missing.append("pending clarification summary")
    return missing


def subagent_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("agent_type", "role", "prompt", "task", "description", "instructions"):
        value = payload.get(key)
        if isinstance(value, str):
            parts.append(value)
    return " ".join(parts).lower()


def is_question_generation_subagent(payload: dict[str, Any]) -> bool:
    text = subagent_text(payload)
    return (
        ("question" in text or "clarification" in text or "질문" in text)
        and ("backlog" in text or "candidate" in text or "후보" in text)
    )


def resolve_root(args: argparse.Namespace, payload: dict[str, Any]) -> Path:
    root = args.root or payload.get("cwd") or "."
    return Path(str(root)).resolve()


def current_path(root: Path, payload: dict[str, Any]) -> Path:
    session_id = safe_segment(str(payload.get("session_id") or "")) or "no-session"
    return root / ".stageflow" / "sessions" / session_id / "current.json"


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def write_turn_state(root: Path, payload: dict[str, Any], result: dict[str, Any]) -> None:
    session_id = safe_segment(str(payload.get("session_id") or "")) or "no-session"
    agent_id = safe_segment(str(payload.get("agent_id") or ""))
    if agent_id:
        state_path = root / ".stageflow" / "hook-state" / "sessions" / session_id / "agents" / agent_id / "current-turn.json"
    else:
        state_path = root / ".stageflow" / "hook-state" / "sessions" / session_id / "main" / "current-turn.json"
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        mirror = root / ".stageflow" / "hook-state" / "current-turn.json"
        mirror.parent.mkdir(parents=True, exist_ok=True)
        mirror.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["hook_state_written"] = True
    except OSError as exc:
        result.setdefault("warnings", []).append(f"could not write Stageflow hook state: {exc}")
        result["hook_state_written"] = False

def read_turn_state(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    session_id = safe_segment(str(payload.get("session_id") or "")) or "no-session"
    state_path = root / ".stageflow" / "hook-state" / "sessions" / session_id / "main" / "current-turn.json"
    return load_json(state_path) or load_json(root / ".stageflow" / "hook-state" / "current-turn.json") or {}


def run_validator(root: Path, phase: str, payload: dict[str, Any]) -> dict[str, Any]:
    validator = Path(__file__).resolve().with_name("validate_stageflow.py")
    command = [sys.executable, str(validator), "--root", str(root), "--current", "--phase", phase]
    session_id = str(payload.get("session_id") or "").strip()
    if session_id:
        command.extend(["--session-id", session_id])
    proc = subprocess.run(command, text=True, capture_output=True)
    output = (proc.stdout + proc.stderr).strip()
    if proc.returncode == 0:
        status = "PASS"
    elif proc.returncode == 3 or output.startswith("AWAITING_USER"):
        status = "AWAITING_USER"
    else:
        status = "FAIL"
    return {
        "phase": phase,
        "status": status,
        "returncode": proc.returncode,
        "output": output,
    }


def base_result(event: str, root: Path) -> dict[str, Any]:
    return {
        "event": event,
        "root": str(root),
        "status": "PREPASS",
        "severity": "info",
        "preflight_required": False,
        "turn_start_action": "none",
        "state_handling_required": False,
        "warnings": [],
    }


def marker_for(request_id: str, phase: str, validation_status: str) -> str:
    return f"{PREFLIGHT_MARKER_PREFIX} current={request_id}, phase={phase}, validation={validation_status}"


def block_result(result: dict[str, Any], reason: str) -> None:
    result.update(
        {
            "status": "BLOCKED",
            "severity": "error",
            "decision": "block",
            "reason": reason,
        }
    )
    warnings = result.setdefault("warnings", [])
    if reason not in warnings:
        warnings.append(reason)


def set_turn_start_action(
    result: dict[str, Any],
    action: str,
    instruction: str,
    *,
    required: bool = True,
) -> None:
    result["turn_start_action"] = action
    result["turn_start_instruction"] = instruction
    result["state_handling_required"] = required


def user_prompt_additional_context(result: dict[str, Any]) -> str:
    lines = [
        "Stageflow hook state is available in `.stageflow/hook-state/`.",
        f"Stageflow status: {result.get('status')}",
        f"turn_start_action: {result.get('turn_start_action')}",
    ]
    for key, label in (
        ("preflight_marker", "preflight_marker"),
        ("turn_start_instruction", "instruction"),
        ("reason", "reason"),
    ):
        value = result.get(key)
        if value:
            lines.append(f"{label}: {value}")
    if result.get("current_request_id"):
        lines.append(f"current_request_id: {result.get('current_request_id')}")
    if result.get("phase"):
        lines.append(f"phase: {result.get('phase')}")
    pending = str(result.get("pending_clarification_output") or "").strip()
    if pending:
        lines.append("pending_clarifications:")
        lines.append(pending)
    return "\n".join(lines)


def wire_reason(result: dict[str, Any], fallback: str) -> str:
    warnings = [str(item).strip() for item in result.get("warnings", []) if str(item).strip()]
    if warnings:
        return "\n".join(warnings)
    reason = str(result.get("reason") or "").strip()
    return reason or fallback


def to_wire_output(event: str, result: dict[str, Any]) -> dict[str, Any] | None:
    is_blocked = result.get("decision") == "block"

    if event == "user_prompt_submit":
        if is_blocked:
            return {"decision": "block", "reason": wire_reason(result, "Stageflow user prompt blocked")}
        if result.get("status") == "PREPASS":
            return None
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": user_prompt_additional_context(result),
            }
        }

    if event == "pre_tool_use":
        if not is_blocked:
            return None
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": wire_reason(result, "Stageflow pre-tool-use gate denied this tool call"),
            }
        }

    if event == "stop":
        if not is_blocked:
            return None
        return {"decision": "block", "reason": wire_reason(result, "Stageflow stop gate blocked this turn")}

    if event == "subagent_start":
        if not is_blocked:
            return None
        return {
            "continue": False,
            "stopReason": wire_reason(result, "Stageflow subagent-start gate blocked this subagent"),
        }

    if event == "subagent_stop":
        if not is_blocked:
            return None
        return {"decision": "block", "reason": wire_reason(result, "Stageflow subagent-stop gate blocked this subagent")}

    return None

def handle_user_prompt_submit(root: Path, payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    prompt = extract_prompt(payload)
    explicit = is_explicit_workflow(prompt)
    stageflow_dir = root / ".stageflow"
    current = load_json(current_path(root, payload))

    if current is None:
        if explicit:
            result.update(
                {
                    "status": "REQUEST_REQUIRED",
                    "severity": "warning",
                    "preflight_required": True,
                    "preflight_marker": marker_for("none", "request-required", "REQUEST_REQUIRED"),
                    "request_creation_required": True,
                    "reason": "explicit Stageflow prompt has no session current pointer",
                }
            )
            set_turn_start_action(
                result,
                "create_request",
                "Inspect the project, create `.stageflow` request scaffolding, and write the session current pointer before any substantive workflow answer.",
            )
            write_turn_state(root, payload, result)
        return result

    request_id = str(current.get("request_id") or "").strip()
    request_dir = stageflow_dir / "requests" / request_id
    state = load_json(request_dir / "state.json") if request_id else None
    if not request_id or state is None:
        result.update(
            {
                "status": "INVALID_CURRENT",
                "severity": "warning",
                "preflight_required": True,
                "preflight_marker": marker_for(request_id or "none", "invalid-current", "FAIL"),
                "reason": "session current pointer does not reference a valid request",
            }
        )
        set_turn_start_action(
            result,
            "repair_current_pointer",
            "Repair or replace the session current pointer so it references an existing `.stageflow/requests/<request-id>` with matching `state.json` before continuing.",
        )
        write_turn_state(root, payload, result)
        return result

    phase = str(state.get("phase") or current.get("phase") or "").strip()
    validation_phase = PHASE_TO_VALIDATION.get(phase)
    if validation_phase is None:
        result.update(
            {
                "status": "INVALID_CURRENT",
                "severity": "warning",
                "preflight_required": True,
                "preflight_marker": marker_for(request_id, phase or "invalid-current", "FAIL"),
                "current_request_id": request_id,
                "phase": phase,
                "reason": "current request phase is not allowed",
            }
        )
        set_turn_start_action(
            result,
            "repair_current_state",
            "Repair `state.json` and the session current pointer so the phase is one of the allowed Stageflow phases before continuing.",
        )
        write_turn_state(root, payload, result)
        return result

    validation = run_validator(root, validation_phase, payload)
    marker = marker_for(request_id, phase, validation["status"])
    if validation["status"] == "PASS":
        status = "OK"
        severity = "info"
        action = "continue_current_stage"
        instruction = "Continue from the validated current Stageflow stage and do not advance until its required artifact, subagent review, and approval gates pass. Goal gates apply only after definition."
    elif validation["status"] == "AWAITING_USER":
        status = "AWAITING_USER"
        severity = "info"
        prompt_kind = classify_awaiting_user_prompt(prompt, validation.get("output", ""))
        if prompt_kind == "pending_answer":
            action = "apply_user_clarification_answer"
            instruction = (
                "The user answered the pending clarification batch. Reflect the answer in definition.md, compare any question-backlog.md candidates against the answer impact, then create the next pending clarification batch and stop for the user."
            )
        elif prompt_kind == "stop_signal":
            action = "run_definition_transition_risk_goal"
            instruction = (
                "The user explicitly stopped definition clarification. Record the stop signal in Clarification History, then run only the definition transition-risk goal: create or update `01-definition/transition-risk-goal.md` and `01-definition/transition-risk.md`, ask the user to confirm generated risk cases, and do not start review, approval, or implementation-plan work until the transition-risk gate is satisfied."
            )
        else:
            action = "answer_follow_up_and_restate_pending"
            instruction = (
                "The current Stageflow stage is waiting for user clarification. Answer the follow-up, restate every pending clarification question with all labeled options, and stop. Question-generation subagents may prepare question-backlog.md candidates in parallel, but the main response must not review, approve, or advance."
            )
    else:
        status = "WARNING"
        severity = "warning"
        action = "repair_current_stage"
        instruction = "Repair the current Stageflow stage artifacts until the current-stage validator passes before advancing or answering as if the stage is ready."
    if phase == "completed":
        status = "COMPLETED_CURRENT" if validation["status"] == "PASS" else "WARNING"
        severity = "warning"
        action = "start_new_request"
        instruction = (
            "The session current pointer references a completed Stageflow request; create or select a non-completed request before doing new workflow work."
        )
    result.update(
        {
            "status": status,
            "severity": severity,
            "current_request_id": request_id,
            "phase": phase,
            "validation_phase": validation_phase,
            "validation": validation,
            "preflight_required": True,
            "preflight_marker": marker,
        }
    )
    set_turn_start_action(result, action, instruction, required=action != "continue_current_stage")
    if validation["status"] == "FAIL":
        result["warnings"].append("current Stageflow stage validation failed")
    elif validation["status"] == "AWAITING_USER":
        result["pending_clarification_output"] = validation.get("output", "")
        result["awaiting_user_prompt_kind"] = classify_awaiting_user_prompt(prompt, validation.get("output", ""))

    if looks_like_implementation(prompt) and validation["status"] != "AWAITING_USER":
        entry_gate = run_validator(root, "implementation-plan", payload)
        result["implementation_entry_gate"] = entry_gate
        if entry_gate["status"] != "PASS":
            result["warnings"].append("implementation requested before implementation-plan stage passed")
            result["implementation_block_required"] = True
            result["status"] = "IMPLEMENTATION_BLOCKED"
            result["severity"] = "warning"
            set_turn_start_action(
                result,
                "repair_implementation_plan_gate",
                "Do not implement. Return to the implementation-plan stage and repair its goal, artifact, subagent review, and approval gates until `--phase implementation-plan` passes.",
            )

    write_turn_state(root, payload, result)
    return result


def handle_stop(root: Path, payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    turn = read_turn_state(root, payload)
    if turn.get("preflight_required"):
        marker = str(turn.get("preflight_marker") or "")
        last_message = extract_last_assistant(payload)
        if marker and marker not in last_message:
            block_result(result, "assistant response is missing required Stageflow preflight marker")

        if turn.get("request_creation_required") and load_json(current_path(root, payload)) is None:
            block_result(result, "explicit Stageflow prompt ended without creating a session current pointer")

        if turn.get("status") == "INVALID_CURRENT":
            current = load_json(current_path(root, payload))
            request_id = str((current or {}).get("request_id") or "").strip()
            state = load_json(root / ".stageflow" / "requests" / request_id / "state.json") if request_id else None
            if not request_id or state is None:
                block_result(result, "Stageflow session current pointer is still invalid")

        if turn.get("status") == "AWAITING_USER":
            if AWAITING_USER_COMPLETION_CLAIM_RE.search(last_message):
                block_result(result, "AWAITING_USER response must not claim completion or next-stage progress before the user answers")
            if turn.get("awaiting_user_prompt_kind") == "follow_up":
                missing_parts = missing_pending_response_parts(
                    last_message, str(turn.get("pending_clarification_output") or "")
                )
                if missing_parts:
                    block_result(
                        result,
                        "AWAITING_USER follow-up response must restate pending clarification questions and labeled options: "
                        + "; ".join(missing_parts[:20]),
                    )

        if looks_like_completion(last_message):
            validation = run_validator(root, "all", payload)
            result["completion_validation"] = validation
            if validation["status"] != "PASS":
                block_result(result, "completion-like response but three-stage validation failed")

    return result


def extract_tool_name(payload: dict[str, Any]) -> str:
    for key in ("tool_name", "tool", "name"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def extract_tool_input(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("tool_input")
    if isinstance(value, dict):
        return value
    value = payload.get("input")
    if isinstance(value, dict):
        return value
    return {}


def normalize_tool_path(value: str) -> str:
    return value.replace("\\", "/").strip()


def is_stageflow_path(value: str) -> bool:
    normalized = normalize_tool_path(value).lower()
    return (
        normalized == ".stageflow"
        or normalized.startswith(".stageflow/")
        or "/.stageflow/" in normalized
        or normalized.endswith("/.stageflow")
    )


def patch_paths(text: str) -> list[str]:
    paths: list[str] = []
    for line in text.splitlines():
        for prefix in ("*** Add File: ", "*** Update File: ", "*** Delete File: ", "*** Move to: "):
            if line.startswith(prefix):
                paths.append(line[len(prefix) :].strip())
    return paths


def payload_paths(tool_input: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for key in ("file_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            paths.append(value.strip())
    value = tool_input.get("paths")
    if isinstance(value, list):
        paths.extend(str(item).strip() for item in value if str(item).strip())
    for key in ("patch", "content", "input"):
        value = tool_input.get(key)
        if isinstance(value, str):
            paths.extend(patch_paths(value))
    return paths


def is_write_like_tool(payload: dict[str, Any]) -> bool:
    tool_name = extract_tool_name(payload).lower()
    tool_input = extract_tool_input(payload)
    if any(token in tool_name for token in WRITE_TOOL_TOKENS):
        return True
    if any(token in tool_name for token in SHELL_TOOL_TOKENS):
        command = str(tool_input.get("command") or "")
        return bool(WRITE_COMMAND_RE.search(command))
    return False


def is_stageflow_artifact_write(payload: dict[str, Any]) -> bool:
    tool_input = extract_tool_input(payload)
    paths = payload_paths(tool_input)
    if paths:
        return all(is_stageflow_path(path) for path in paths)

    command = str(tool_input.get("command") or "")
    if command and WRITE_COMMAND_RE.search(command):
        normalized = normalize_tool_path(command).lower()
        return ".stageflow/" in normalized or "\\.stageflow\\" in command.lower()

    return False


def is_question_backlog_write(payload: dict[str, Any]) -> bool:
    tool_input = extract_tool_input(payload)
    paths = payload_paths(tool_input)
    if paths:
        return all(normalize_tool_path(path).lower().endswith("/01-definition/question-backlog.md") for path in paths)
    command = str(tool_input.get("command") or "")
    return "question-backlog.md" in normalize_tool_path(command).lower()


def is_transition_risk_gate_write(payload: dict[str, Any]) -> bool:
    allowed_suffixes = (
        "/01-definition/definition.md",
        "/01-definition/transition-risk-goal.md",
        "/01-definition/transition-risk.md",
    )
    tool_input = extract_tool_input(payload)
    paths = payload_paths(tool_input)
    if paths:
        normalized_paths = [normalize_tool_path(path).lower() for path in paths]
        return all(any(path.endswith(suffix) for suffix in allowed_suffixes) for path in normalized_paths)
    command = normalize_tool_path(str(tool_input.get("command") or "")).lower()
    if not command:
        return False
    return (
        "01-definition/definition.md" in command
        or "01-definition/transition-risk-goal.md" in command
        or "01-definition/transition-risk.md" in command
    ) and "02-implementation-plan" not in command and "03-implementation" not in command


def active_request(root: Path, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    current = load_json(current_path(root, payload))
    if current is None:
        return None, None
    request_id = str(current.get("request_id") or "").strip()
    state = load_json(root / ".stageflow" / "requests" / request_id / "state.json") if request_id else None
    return current, state


def handle_pre_tool_use(root: Path, payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    result["event"] = "pre_tool_use"
    if not is_write_like_tool(payload):
        return result

    result["write_like_tool"] = True
    turn = read_turn_state(root, payload)
    if payload.get("agent_id") and turn.get("status") == "AWAITING_USER":
        if is_question_backlog_write(payload):
            result["question_backlog_write"] = True
            return result
        block_result(result, "AWAITING_USER subagents may only write `01-definition/question-backlog.md` helper candidates")
        return result

    if (
        turn.get("status") == "AWAITING_USER"
        and turn.get("awaiting_user_prompt_kind") == "stop_signal"
        and turn.get("turn_start_action") == "run_definition_transition_risk_goal"
        and is_stageflow_artifact_write(payload)
    ):
        if is_transition_risk_gate_write(payload):
            result["transition_risk_gate_write"] = True
            return result
        block_result(result, "definition stop-signal turns may only write `01-definition/definition.md`, `01-definition/transition-risk-goal.md`, or `01-definition/transition-risk.md` before transition risk confirmation")
        return result

    if is_stageflow_artifact_write(payload):
        result["stageflow_artifact_write"] = True
        return result

    current, state = active_request(root, payload)
    if current is None:
        if turn.get("request_creation_required") or turn.get("preflight_required"):
            block_result(
                result,
                "Stageflow is active but no session current pointer exists; create `.stageflow` request artifacts before non-Stageflow edits",
            )
        return result

    request_id = str(current.get("request_id") or "").strip()
    if state is None:
        block_result(result, "Stageflow session current pointer does not reference a valid request")
        return result

    phase = str(state.get("phase") or current.get("phase") or "").strip()
    result.update({"current_request_id": request_id, "phase": phase})
    if phase == "completed":
        block_result(result, "current Stageflow request is completed; start a new request before editing files")
        return result

    entry_gate = run_validator(root, "implementation-plan", payload)
    result["implementation_entry_gate"] = entry_gate
    if entry_gate["status"] != "PASS":
        block_result(result, "non-Stageflow file edit blocked until implementation-plan stage passes")

    return result

def handle_subagent(event: str, root: Path, payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    turn = read_turn_state(root, payload)
    result.update(
        {
            "status": "SUBAGENT_OBSERVED",
            "severity": "info",
            "agent_id": payload.get("agent_id"),
            "agent_type": payload.get("agent_type"),
            "role": payload.get("role"),
        }
    )
    if event == "subagent_start" and turn.get("status") == "AWAITING_USER":
        result["awaiting_user_prompt_kind"] = turn.get("awaiting_user_prompt_kind")
        if is_question_generation_subagent(payload):
            result["status"] = "QUESTION_BACKLOG_SUBAGENT_ALLOWED"
            result["question_backlog_allowed"] = True
        else:
            block_result(result, "AWAITING_USER allows only question-generation subagents for `01-definition/question-backlog.md` candidates")
    write_turn_state(root, payload, result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--event",
        choices=("user_prompt_submit", "pre_tool_use", "stop", "subagent_start", "subagent_stop"),
        default="user_prompt_submit",
    )
    parser.add_argument("--root")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        payload = read_payload()
    except Exception as exc:
        sys.stderr.write(json.dumps({"status": "ERROR", "severity": "error", "reason": str(exc)}) + "\n")
        raise SystemExit(1)

    root = resolve_root(args, payload)
    result = base_result(args.event, root)
    if args.event == "user_prompt_submit":
        result = handle_user_prompt_submit(root, payload, result)
    elif args.event == "pre_tool_use":
        result = handle_pre_tool_use(root, payload, result)
    elif args.event == "stop":
        result = handle_stop(root, payload, result)
    else:
        result = handle_subagent(args.event, root, payload, result)
    wire_output = to_wire_output(args.event, result)
    if wire_output is not None:
        print(json.dumps(wire_output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
