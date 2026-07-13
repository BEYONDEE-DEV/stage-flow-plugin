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

from tests.test_simple_workflow_validator import (
    REQUEST_ID,
    SESSION_ID,
    make_project,
    make_v2_project,
    sha256,
    temp_project,
    write_json,
)


class HookCheckTests(unittest.TestCase):
    def run_hook(self, root: Path, payload: dict[str, object], event: str = "user_prompt_submit") -> dict[str, object]:
        result = subprocess.run(
            [sys.executable, str(HOOK_CHECK), "--root", str(root), "--event", event, "--diagnostic"],
            input=json.dumps(payload),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def run_wire(self, root: Path, payload: dict[str, object], event: str) -> tuple[dict[str, object], str]:
        result = subprocess.run(
            [sys.executable, str(HOOK_CHECK), "--root", str(root), "--event", event],
            input=json.dumps(payload),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return (json.loads(result.stdout) if result.stdout.strip() else {}, result.stderr)

    def test_prompt_text_never_activates_or_creates_request(self) -> None:
        for prompt in ("Use Simple Workflow", ".simple status", "simple workflow를 수정해줘", "workflow status"):
            with self.subTest(prompt=prompt), temp_project() as td:
                result = self.run_hook(Path(td), {"session_id": SESSION_ID, "prompt": prompt})
                self.assertEqual(result["status"], "PREPASS")
                self.assertFalse(result["request_creation_required"])
                self.assertFalse(result["prompt_relevant"])

    def test_completed_pointer_never_captures_prompt(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="completed", approval_status="approved", goal_status="completed")
            result = self.run_hook(root, {"session_id": SESSION_ID, "prompt": "simple-workflow"})
            self.assertEqual(result["status"], "PREPASS")
            self.assertFalse(result["prompt_relevant"])
            self.assertFalse(result["request_creation_required"])

    def test_active_pointer_supplies_lightweight_continuation_context(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", approval_status="approved", goal_status="active")
            result = self.run_hook(root, {"session_id": SESSION_ID, "prompt": "상태 알려줘"})
            self.assertEqual(result["status"], "WARN")
            self.assertTrue(result["prompt_relevant"])
            self.assertTrue(result["continuation_required"])
            self.assertEqual(result["validation"]["status"], "SKIPPED")
            self.assertIn("lightweight state checks", result["validation"]["reason"])

    def test_pending_approval_and_approved_pending_are_reported_from_state(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", approval_status="pending", goal_status="pending")
            result = self.run_hook(root, {"session_id": SESSION_ID, "prompt": "승인하지 마"})
            self.assertTrue(any("awaits explicit user approval" in warning for warning in result["warnings"]))
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", approval_status="approved", goal_status="pending")
            result = self.run_hook(root, {"session_id": SESSION_ID, "prompt": "진행 상황"})
            self.assertTrue(any("ready for Goal reconciliation" in warning for warning in result["warnings"]))

    def test_create_goal_requires_approved_pending_current_fingerprint(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", approval_status="approved", goal_status="pending")
            result = self.run_hook(root, goal_payload(root, tool_name="functions.create_goal"), "pre_tool_use")
            self.assertEqual(result["status"], "CREATE_GOAL_ALLOWED")
            self.assertEqual(result["validation"]["status"], "PASS")
            self.assertEqual(result["review_status"]["status"], "pass")

    def test_legacy_review_create_goal_keeps_single_fingerprint_compatibility(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), phase="review")
            result = self.run_hook(root, goal_payload(root), "pre_tool_use")
            self.assertEqual(result["status"], "CREATE_GOAL_ALLOWED")
            self.assertEqual(result["validation"]["status"], "PASS")

    def test_create_goal_rejects_unapproved_plan(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", approval_status="pending", goal_status="pending")
            result = self.run_hook(root, goal_payload(root), "pre_tool_use")
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("recorded user approval", result["reason"])

    def test_create_goal_rejects_stale_approved_or_objective_fingerprint(self) -> None:
        with temp_project() as td:
            root = make_v2_project(
                Path(td),
                phase="review",
                approval_status="approved",
                goal_status="pending",
                approved_fingerprint="sha256:" + "0" * 64,
            )
            result = self.run_hook(root, goal_payload(root), "pre_tool_use")
            self.assertIn("approved_plan_fingerprint", result["reason"])
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", approval_status="approved", goal_status="pending")
            objective = f".simple/requests/{REQUEST_ID}/plan.md sha256:{'0' * 64}"
            result = self.run_hook(root, goal_payload(objective=objective), "pre_tool_use")
            self.assertIn("current plan fingerprint", result["reason"])

    def test_create_goal_rejects_stale_review_after_approval_was_refreshed(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", approval_status="approved", goal_status="pending")
            request_dir = root / ".simple" / "requests" / REQUEST_ID
            plan = request_dir / "plan.md"
            plan.write_text(plan.read_text(encoding="utf-8") + "\n변경됨.\n", encoding="utf-8")
            state_path = request_dir / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["approved_plan_fingerprint"] = "sha256:" + sha256(plan)
            write_json(state_path, state)
            result = self.run_hook(root, goal_payload(root), "pre_tool_use")
            self.assertEqual(result["validation"]["status"], "FAIL")
            self.assertEqual(result["review_status"]["status"], "stale")

    def test_create_goal_requires_exact_pass_and_pending_goal(self) -> None:
        with temp_project() as td:
            root = make_v2_project(
                Path(td),
                phase="review",
                approval_status="approved",
                goal_status="pending",
                review_verdict="pass",
            )
            result = self.run_hook(root, goal_payload(root), "pre_tool_use")
            self.assertEqual(result["validation"]["status"], "FAIL")
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", approval_status="approved", goal_status="active")
            result = self.run_hook(root, goal_payload(root), "pre_tool_use")
            self.assertIn("already", result["reason"])

    def test_unrelated_create_goal_always_prepasses(self) -> None:
        for with_request in (False, True):
            with self.subTest(with_request=with_request), temp_project() as td:
                root = Path(td)
                if with_request:
                    root = make_v2_project(root, phase="review", approval_status="approved", goal_status="pending")
                result = self.run_hook(root, goal_payload(objective="Stageflow implementation request"), "pre_tool_use")
                self.assertEqual(result["status"], "PREPASS")

    def test_simple_goal_requires_active_pointer_selected_request_and_exact_path(self) -> None:
        objective = f".simple/requests/{REQUEST_ID}/plan.md sha256:{'0' * 64}"
        with temp_project() as td:
            result = self.run_hook(Path(td), goal_payload(objective=objective), "pre_tool_use")
            self.assertIn("active Simple Workflow", result["reason"])
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", approval_status="approved", goal_status="pending")
            other = objective.replace(REQUEST_ID, "20260710-1200-other")
            self.assertIn("selected request id", self.run_hook(root, goal_payload(objective=other), "pre_tool_use")["reason"])
            suffix = objective.replace("plan.md", "plan.md.bak")
            self.assertEqual(self.run_hook(root, goal_payload(objective=suffix), "pre_tool_use")["status"], "PREPASS")
            prefixed = objective.replace(".simple/", "not.simple/")
            self.assertEqual(self.run_hook(root, goal_payload(objective=prefixed), "pre_tool_use")["status"], "PREPASS")

    def test_stop_never_emits_wire_block_and_warns_only_on_stderr(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", approval_status="pending", goal_status="active")
            diagnostic = self.run_hook(root, {"session_id": SESSION_ID}, "stop")
            self.assertEqual(diagnostic["status"], "WARN")
            self.assertNotIn("decision", diagnostic)
            wire, stderr = self.run_wire(root, {"session_id": SESSION_ID}, "stop")
            self.assertEqual(wire, {})
            self.assertIn("Simple Workflow WARN", stderr)

    def test_stop_does_not_run_full_validator_for_invalid_artifacts(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", approval_status="approved", goal_status="active")
            (root / ".simple" / "requests" / REQUEST_ID / "plan.md").unlink()
            result = self.run_hook(root, {"session_id": SESSION_ID}, "stop")
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["validation"]["status"], "SKIPPED")
            wire, _ = self.run_wire(root, {"session_id": SESSION_ID}, "stop")
            self.assertEqual(wire, {})

    def test_invalid_pointer_stop_is_diagnostic_only(self) -> None:
        with temp_project() as td:
            root = Path(td)
            current = root / ".simple" / "sessions" / SESSION_ID / "current.json"
            write_json(current, {"phase": "review"})
            result = self.run_hook(root, {"session_id": SESSION_ID}, "stop")
            self.assertEqual(result["status"], "INVALID_CURRENT")
            self.assertNotIn("decision", result)
            wire, stderr = self.run_wire(root, {"session_id": SESSION_ID}, "stop")
            self.assertEqual(wire, {})
            self.assertIn("Simple Workflow WARN", stderr)

    def test_user_prompt_and_pretool_wire_contracts(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", approval_status="approved", goal_status="active")
            wire, _ = self.run_wire(root, {"session_id": SESSION_ID, "prompt": "상태"}, "user_prompt_submit")
            self.assertEqual(wire["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="plan", approval_status="pending", goal_status="pending")
            wire, _ = self.run_wire(root, goal_payload(root), "pre_tool_use")
            self.assertEqual(wire["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_hook_source_has_no_prompt_activation_regex(self) -> None:
        text = HOOK_CHECK.read_text(encoding="utf-8")
        self.assertNotIn("EXPLICIT_RE", text)
        self.assertNotIn("extract_prompt(payload)", text)

    def test_plugin_local_validator_resolution_and_hook_bootstrap(self) -> None:
        module = load_hook_check_module()
        original_file = module.__file__
        try:
            with temp_project() as td:
                module.__file__ = str(Path(td) / "scripts" / "simple_workflow_hook_check.py")
                result = module.run_validator(Path(td), SESSION_ID, "plan")
        finally:
            module.__file__ = original_file
        self.assertEqual(result["status"], "SKIPPED")

        payload = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        commands = [
            hook["command"]
            for groups in payload["hooks"].values()
            for group in groups
            for hook in group["hooks"]
            if "simple_workflow_hook_check.py" in hook["command"]
        ]
        self.assertTrue(commands)
        for command in commands:
            self.assertIn("SIMPLE_WORKFLOW_PLUGIN_ROOT", command)
            self.assertIn("STAGEFLOW_PLUGIN_ROOT", command)
            self.assertNotIn("python hooks/simple_workflow_hook.py", command)

        wrapper = HOOK_WRAPPER.read_text(encoding="utf-8-sig")
        self.assertIn('"PreToolUse": "pre_tool_use"', wrapper)


def goal_payload(
    root: Path | None = None,
    *,
    tool_name: str = "create_goal",
    objective: str | None = None,
) -> dict[str, object]:
    if objective is None:
        fingerprint = "0" * 64
        if root is not None:
            fingerprint = sha256(root / ".simple" / "requests" / REQUEST_ID / "plan.md")
        objective = f".simple/requests/{REQUEST_ID}/plan.md Reviewed Plan Fingerprint sha256:{fingerprint}"
    return {
        "session_id": SESSION_ID,
        "tool_name": tool_name,
        "tool_input": {"objective": objective},
    }


def load_hook_check_module():
    spec = importlib.util.spec_from_file_location("simple_workflow_hook_check_under_test", HOOK_CHECK)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()
