#!/usr/bin/env python3
"""Fast hook auditor for the four-stage Stageflow model."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


PHASE_TO_VALIDATION = {
    "requirements": "requirements",
    "service-plan": "service-plan",
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
    return {
        "phase": phase,
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "returncode": proc.returncode,
        "output": (proc.stdout + proc.stderr).strip(),
    }


def base_result(event: str, root: Path) -> dict[str, Any]:
    return {
        "event": event,
        "root": str(root),
        "status": "PREPASS",
        "severity": "info",
        "preflight_required": False,
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
        write_turn_state(root, payload, result)
        return result

    validation = run_validator(root, validation_phase, payload)
    marker = marker_for(request_id, phase, validation["status"])
    result.update(
        {
            "status": "OK" if validation["status"] == "PASS" else "WARNING",
            "severity": "info" if validation["status"] == "PASS" else "warning",
            "current_request_id": request_id,
            "phase": phase,
            "validation_phase": validation_phase,
            "validation": validation,
            "preflight_required": True,
            "preflight_marker": marker,
        }
    )
    if validation["status"] != "PASS":
        result["warnings"].append("current Stageflow stage validation failed")

    if looks_like_implementation(prompt):
        entry_gate = run_validator(root, "implementation-plan", payload)
        result["implementation_entry_gate"] = entry_gate
        if entry_gate["status"] != "PASS":
            result["warnings"].append("implementation requested before implementation-plan stage passed")
            result["implementation_block_required"] = True
            result["status"] = "WARNING"
            result["severity"] = "warning"

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

        if looks_like_completion(last_message):
            validation = run_validator(root, "all", payload)
            result["completion_validation"] = validation
            if validation["status"] != "PASS":
                block_result(result, "completion-like response but four-stage validation failed")

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
    if is_stageflow_artifact_write(payload):
        result["stageflow_artifact_write"] = True
        return result

    turn = read_turn_state(root, payload)
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
    result.update(
        {
            "status": "SUBAGENT_OBSERVED",
            "severity": "info",
            "agent_id": payload.get("agent_id"),
            "agent_type": payload.get("agent_type"),
            "role": payload.get("role"),
        }
    )
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
        print(json.dumps({"status": "ERROR", "severity": "error", "reason": str(exc)}))
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
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("decision") == "block":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
