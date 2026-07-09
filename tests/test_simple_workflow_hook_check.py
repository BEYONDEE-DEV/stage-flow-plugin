from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK_CHECK = ROOT / "scripts" / "simple_workflow_hook_check.py"
HOOKS_JSON = ROOT / "hooks" / "hooks.json"
HOOK_WRAPPER = ROOT / "hooks" / "simple_workflow_hook.py"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.test_simple_workflow_validator import REQUEST_ID, SESSION_ID, make_project, review_text, sha256, temp_project, write_json


class HookCheckTests(unittest.TestCase):
    def run_hook(self, root: Path, payload: dict[str, object], event: str = "user_prompt_submit") -> dict[str, object]:
        result = subprocess.run(
            [sys.executable, str(HOOK_CHECK), "--root", str(root), "--event", event],
            input=json.dumps(payload),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"hook output was not JSON: {exc}\n{result.stdout}")

    def test_explicit_prompt_without_current_requires_request(self) -> None:
        with temp_project() as td:
            result = self.run_hook(Path(td), {"session_id": SESSION_ID, "prompt": "Use Simple Workflow"})
            self.assertEqual(result["status"], "REQUEST_REQUIRED")
            self.assertTrue(result["request_creation_required"])

    def test_dot_simple_prompt_without_current_requires_request(self) -> None:
        with temp_project() as td:
            result = self.run_hook(Path(td), {"session_id": SESSION_ID, "prompt": ".simple status"})
            self.assertEqual(result["status"], "REQUEST_REQUIRED")
            self.assertTrue(result["request_creation_required"])

    def test_bare_workflow_prompt_without_current_prepasses(self) -> None:
        with temp_project() as td:
            result = self.run_hook(Path(td), {"session_id": SESSION_ID, "prompt": "workflow status"})
            self.assertEqual(result["status"], "PREPASS")
            self.assertFalse(result["request_creation_required"])

    def test_stageflow_maintenance_prompt_without_current_prepasses(self) -> None:
        with temp_project() as td:
            result = self.run_hook(Path(td), {"session_id": SESSION_ID, "prompt": "fix Stageflow plugin hook docs"})
            self.assertEqual(result["status"], "PREPASS")
            self.assertFalse(result["request_creation_required"])

    def test_completed_current_explicit_requires_new_request(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            set_phase(root, "completed")
            result = self.run_hook(root, {"session_id": SESSION_ID, "prompt": "simple-workflow"})
            self.assertEqual(result["status"], "COMPLETED_CURRENT")
            self.assertTrue(result["request_creation_required"])

    def test_proceed_before_review_pass_blocks_goal(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_blocking=True)
            result = self.run_hook(root, {"session_id": SESSION_ID, "prompt": "진행"})
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["review_status"]["status"], "blocking")

    def test_proceed_after_review_pass_allows_goal(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            set_phase(root, "review")
            result = self.run_hook(root, {"session_id": SESSION_ID, "prompt": "승인"})
            self.assertEqual(result["status"], "PROCEED_ALLOWED")
            self.assertEqual(result["review_status"]["status"], "pass")
            self.assertFalse(result["continuation_required"])

    def test_active_plan_request_warns_on_followup_prompt_without_plugin_name(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), phase="plan")
            result = self.run_hook(root, {"session_id": SESSION_ID, "prompt": "응 맞아"})
            self.assertEqual(result["status"], "WARN")
            self.assertTrue(result["continuation_required"])
            self.assertTrue(result["prompt_relevant"])
            self.assertTrue(any("Active Simple Workflow request exists" in warning for warning in result["warnings"]))

    def test_active_review_request_warns_on_followup_prompt_without_plugin_name(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), phase="review")
            result = self.run_hook(root, {"session_id": SESSION_ID, "prompt": "수정해줘"})
            self.assertEqual(result["status"], "WARN")
            self.assertTrue(result["continuation_required"])
            self.assertTrue(any("Active Simple Workflow request exists" in warning for warning in result["warnings"]))

    def test_general_prompt_without_active_request_still_prepasses(self) -> None:
        with temp_project() as td:
            result = self.run_hook(Path(td), {"session_id": SESSION_ID, "prompt": "응 맞아"})
            self.assertEqual(result["status"], "PREPASS")
            self.assertFalse(result["continuation_required"])

    def test_review_stale_fingerprint_blocks_proceed(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            request_dir = root / ".simple" / "requests" / REQUEST_ID
            (request_dir / "plan.md").write_text((request_dir / "plan.md").read_text(encoding="utf-8") + "\nChanged after review.\n", encoding="utf-8")
            result = self.run_hook(root, {"session_id": SESSION_ID, "prompt": "implement"})
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["review_status"]["status"], "stale")

    def test_review_flow_issue_blocks_proceed(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_flow_issue=True)
            result = self.run_hook(root, {"session_id": SESSION_ID, "prompt": "implement"})
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["review_status"]["status"], "blocking")
            self.assertIn("flow", result["review_status"]["reason"])

    def test_review_question_depth_issue_blocks_proceed(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_question_depth_issue=True)
            result = self.run_hook(root, {"session_id": SESSION_ID, "prompt": "implement"})
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["review_status"]["status"], "blocking")
            self.assertIn("higher-level questions", result["review_status"]["reason"])

    def test_session_current_pointer_is_used(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            result = self.run_hook(root, {"session_id": SESSION_ID, "prompt": "status"})
            self.assertEqual(result["status"], "WARN")
            self.assertTrue(result["continuation_required"])
            self.assertEqual(result["validation"]["status"], "PASS")
            self.assertEqual(result["current_request_id"], REQUEST_ID)
            self.assertIn(f".simple/sessions/{SESSION_ID}/current.json", result["current_path"])

    def test_plugin_local_validator_does_not_require_target_project_script(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            self.assertFalse((root / "scripts" / "validate_simple_workflow.py").exists())
            result = self.run_hook(root, {"session_id": SESSION_ID, "prompt": "status"})
            self.assertEqual(result["validation"]["status"], "PASS")

    def test_missing_plugin_validator_reports_plugin_bundled_reason(self) -> None:
        module = load_hook_check_module()
        original_file = module.__file__
        try:
            with temp_project() as td:
                module.__file__ = str(Path(td) / "scripts" / "simple_workflow_hook_check.py")
                result = module.run_validator(Path(td), SESSION_ID, "plan")
        finally:
            module.__file__ = original_file
        self.assertEqual(result["status"], "SKIPPED")
        self.assertIn("plugin-bundled validator missing", result["reason"])
        self.assertNotIn("target", result["reason"].lower())

    def test_hooks_json_uses_plugin_resolving_bootstrap(self) -> None:
        payload = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        commands = [
            hook["command"]
            for groups in payload["hooks"].values()
            for group in groups
            for hook in group["hooks"]
            if "simple_workflow_hook_check.py" in hook["command"]
        ]
        self.assertGreater(len(commands), 0)
        for command in commands:
            self.assertNotIn("python hooks/simple_workflow_hook.py", command)
            self.assertIn("SIMPLE_WORKFLOW_PLUGIN_ROOT", command)
            self.assertIn("STAGEFLOW_PLUGIN_ROOT", command)
            self.assertIn(".codex/plugins/cache/**/stageflow*/**/scripts/simple_workflow_hook_check.py", command)
            self.assertIn(".codex/plugins/cache/**/simple-workflow-plugin/**/scripts/simple_workflow_hook_check.py", command)
            self.assertIn("p=next(iter(c),None)", command)
            self.assertNotIn("max(c,key=", command)

    def test_hook_wrapper_prefers_stageflow_cache_before_legacy_cache(self) -> None:
        text = HOOK_WRAPPER.read_text(encoding="utf-8-sig")

        self.assertIn("return existing[0] if existing else", text)
        self.assertNotIn("max(existing", text)
        self.assertLess(
            text.index(".codex/plugins/cache/**/stageflow*/**/scripts/simple_workflow_hook_check.py"),
            text.index(".codex/plugins/cache/**/simple-workflow-plugin/**/scripts/simple_workflow_hook_check.py"),
        )

    def test_stop_event_checks_current_request(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), write_plan=False)
            result = self.run_hook(root, {"session_id": SESSION_ID}, event="stop")
            self.assertEqual(result["status"], "WARN")
            self.assertIn("plan.md", result["reason"])


def set_phase(root: Path, phase: str) -> None:
    request_dir = root / ".simple" / "requests" / REQUEST_ID
    current_dir = root / ".simple" / "sessions" / SESSION_ID
    write_json(request_dir / "state.json", {"request_id": REQUEST_ID, "phase": phase, "last_validated_at": None})
    write_json(current_dir / "current.json", {"request_id": REQUEST_ID, "phase": phase, "activated_by": "test"})
    if phase == "review":
        fp = sha256(request_dir / "plan.md")
        (request_dir / "review.md").write_text(review_text(fp), encoding="utf-8")


def load_hook_check_module():
    spec = importlib.util.spec_from_file_location("simple_workflow_hook_check_under_test", HOOK_CHECK)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()
