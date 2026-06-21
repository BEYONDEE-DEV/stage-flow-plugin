#!/usr/bin/env python3
"""Plugin-provided hook wrapper for Stageflow."""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


EVENT_ALIASES = {
    "SubagentStart": "subagent_start",
    "SubagentStop": "subagent_stop",
    "subagent-start": "subagent_start",
    "subagent-stop": "subagent_stop",
    "subagent_start": "subagent_start",
    "subagent_stop": "subagent_stop",
    "pre-tool-use": "pre_tool_use",
    "pre_tool_use": "pre_tool_use",
    "PreToolUse": "pre_tool_use",
    "user-prompt-submit": "user_prompt_submit",
    "user_prompt_submit": "user_prompt_submit",
    "stop": "stop",
}


def main() -> int:
    event = EVENT_ALIASES.get(sys.argv[1] if len(sys.argv) > 1 else "")
    if not event:
        sys.stderr.write("Stageflow hook: unsupported or missing event; skipping hook.\n")
        return 0

    root = plugin_root()
    checker = root / "scripts" / "stageflow_hook_check.py"
    if not checker.is_file():
        sys.stderr.write(
            f"Stageflow hook: checker not found at {checker}; skipping hook.\n"
        )
        return 0

    sys.argv = [str(checker), "--event", event]
    runpy.run_path(str(checker), run_name="__main__")
    return 0


def plugin_root() -> Path:
    configured = (
        os.environ.get("PLUGIN_ROOT")
        or os.environ.get("CODEX_PLUGIN_ROOT")
        or os.environ.get("CLAUDE_PLUGIN_ROOT")
    )
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    raise SystemExit(main())
