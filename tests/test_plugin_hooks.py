from __future__ import annotations

import importlib.util
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


def load_stageflow_hook_check():
    spec = importlib.util.spec_from_file_location(
        "stageflow_hook_check",
        ROOT / "scripts" / "stageflow_hook_check.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load stageflow_hook_check.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
                self.assertIn("python3 -c", command)
                self.assertIn("py -3 -c", command)
                self.assertIn("python -c", command)
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


class PluginHookAtomicDocsStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.hook = load_stageflow_hook_check()

    def test_atomic_docs_state_paths_are_not_stageflow_workflow_artifacts(self) -> None:
        atomic_state_paths = [
            ".stageflow/atomic-docs.json",
            ".stageflow/atomic-docs/requests/req-1/work-state.json",
            "/repo/.stageflow/atomic-docs/sessions/default/current.json",
            r".stageflow\atomic-docs\requests\req-1\post-write-review.md",
        ]
        for path in atomic_state_paths:
            with self.subTest(path=path):
                self.assertTrue(self.hook.is_atomic_docs_state_path(path))
                self.assertFalse(self.hook.is_stageflow_path(path))

        self.assertTrue(self.hook.is_stageflow_path(".stageflow/requests/req-1/state.json"))

    def test_atomic_docs_state_writes_are_not_stageflow_artifact_writes(self) -> None:
        patch_payload = {
            "tool_name": "apply_patch",
            "tool_input": {
                "patch": "*** Begin Patch\n*** Add File: .stageflow/atomic-docs/requests/req-1/work-state.json\n+{}\n*** End Patch\n"
            },
        }
        self.assertFalse(self.hook.is_stageflow_artifact_write(patch_payload))

        shell_payload = {
            "tool_name": "shell",
            "tool_input": {"command": "touch .stageflow/atomic-docs/requests/req-1/post-write-review.md"},
        }
        self.assertFalse(self.hook.is_stageflow_artifact_write(shell_payload))

        redirection_payload = {
            "tool_name": "shell",
            "tool_input": {"command": "echo '{}' >.stageflow/atomic-docs/requests/req-1/work-state.json"},
        }
        self.assertFalse(self.hook.is_stageflow_artifact_write(redirection_payload))

        config_redirection_payload = {
            "tool_name": "shell",
            "tool_input": {"command": "cat >.stageflow/atomic-docs.json"},
        }
        self.assertFalse(self.hook.is_stageflow_artifact_write(config_redirection_payload))

        mixed_stageflow_payload = {
            "tool_name": "shell",
            "tool_input": {
                "command": "touch .stageflow/atomic-docs/requests/req-1/work-state.json .stageflow/requests/req-1/state.json"
            },
        }
        self.assertTrue(self.hook.is_stageflow_artifact_write(mixed_stageflow_payload))

        stageflow_payload = {
            "tool_name": "apply_patch",
            "tool_input": {
                "patch": "*** Begin Patch\n*** Add File: .stageflow/requests/req-1/state.json\n+{}\n*** End Patch\n"
            },
        }
        self.assertTrue(self.hook.is_stageflow_artifact_write(stageflow_payload))


if __name__ == "__main__":
    unittest.main()
