#!/usr/bin/env python3
"""Plugin-provided hook wrapper for Simple Workflow."""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


EVENT_ALIASES = {
    "user-prompt-submit": "user_prompt_submit",
    "user_prompt_submit": "user_prompt_submit",
    "UserPromptSubmit": "user_prompt_submit",
    "pre-tool-use": "pre_tool_use",
    "pre_tool_use": "pre_tool_use",
    "PreToolUse": "pre_tool_use",
    "stop": "stop",
    "Stop": "stop",
}


def main() -> int:
    event = EVENT_ALIASES.get(sys.argv[1] if len(sys.argv) > 1 else "")
    if not event:
        sys.stderr.write("Simple Workflow hook: unsupported or missing event; skipping hook.\n")
        return 0

    checker = find_checker()
    if not checker.is_file():
        sys.stderr.write("Simple Workflow hook: checker not found; skipping hook.\n")
        return 0

    sys.argv = [str(checker), "--event", event]
    runpy.run_path(str(checker), run_name="__main__")
    return 0


def find_checker() -> Path:
    candidates = []
    for key in ("SIMPLE_WORKFLOW_PLUGIN_ROOT", "STAGEFLOW_PLUGIN_ROOT", "CODEX_PLUGIN_ROOT", "PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT"):
        configured = os.environ.get(key)
        if configured:
            candidates.append(Path(configured).resolve() / "scripts" / "simple_workflow_hook_check.py")
    candidates.append(Path(__file__).resolve().parents[1] / "scripts" / "simple_workflow_hook_check.py")
    candidates.extend(newest_cache_matches(".codex/plugins/cache/**/stageflow*/**/scripts/simple_workflow_hook_check.py"))
    candidates.extend(newest_cache_matches(".codex/plugins/cache/**/simple-workflow-plugin/**/scripts/simple_workflow_hook_check.py"))
    existing = [path for path in candidates if path.is_file()]
    return existing[0] if existing else Path("__missing_simple_workflow_hook_check__")


def newest_cache_matches(pattern: str) -> list[Path]:
    return sorted(
        [path for path in Path.home().glob(pattern) if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
