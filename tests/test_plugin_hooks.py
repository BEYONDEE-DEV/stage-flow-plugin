from __future__ import annotations

import json
import os
import shutil
import subprocess
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = Path(os.environ.get("STAGEFLOW_TEST_TMP", str(ROOT / "tests" / ".tmp" / "plugin-hooks")))
TMP_ROOT.mkdir(parents=True, exist_ok=True)


class PluginHookDeclarationTests(unittest.TestCase):
    def load_hooks(self) -> dict[str, object]:
        return json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))

    def command_entries(self) -> list[str]:
        config = self.load_hooks()
        commands: list[str] = []
        for event_entries in config["hooks"].values():
            for event_entry in event_entries:
                for hook in event_entry["hooks"]:
                    commands.append(hook["command"])
        return commands

    def test_hooks_do_not_reference_target_cwd_relative_wrapper(self) -> None:
        for command in self.command_entries():
            with self.subTest(command=command):
                self.assertIn("stageflow_hook_check.py", command)
                self.assertIn("STAGEFLOW_PLUGIN_ROOT", command)
                self.assertNotIn("python hooks/stageflow_hook.py", command)
                self.assertNotIn("hooks/stageflow_hook.py", command)
                self.assertNotIn(r"hooks\stageflow_hook.py", command)
                self.assertNotIn("/home/kgh", command)
                self.assertNotIn("stock-auto-trade", command)

    def test_user_prompt_submit_hook_runs_from_target_project_cwd(self) -> None:
        commands = self.command_entries()
        command = next(item for item in commands if "user_prompt_submit" in item)
        payload = json.dumps({"session_id": "session-1", "prompt": "hello"})
        env = os.environ.copy()
        env["STAGEFLOW_PLUGIN_ROOT"] = str(ROOT)

        target_root = TMP_ROOT / f"case-{uuid.uuid4().hex}"
        target_root.mkdir(parents=True, exist_ok=False)
        try:
            (target_root / "hooks").mkdir()
            result = subprocess.run(
                command,
                input=payload,
                text=True,
                shell=True,
                cwd=target_root,
                env=env,
                capture_output=True,
                timeout=20,
            )
        finally:
            shutil.rmtree(target_root, ignore_errors=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
