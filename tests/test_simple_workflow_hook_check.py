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

from tests.test_simple_workflow_validator import REQUEST_ID, SESSION_ID, make_project, make_v2_project, review_text, sha256, temp_project, write_json


class HookCheckTests(unittest.TestCase):
    def run_hook(self, root: Path, payload: dict[str, object], event: str = "user_prompt_submit") -> dict[str, object]:
        result = subprocess.run(
            [sys.executable, str(HOOK_CHECK), "--root", str(root), "--event", event, "--diagnostic"],
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

    def run_wire(self, root: Path, payload: dict[str, object], event: str) -> dict[str, object]:
        result = subprocess.run(
            [sys.executable, str(HOOK_CHECK), "--root", str(root), "--event", event],
            input=json.dumps(payload),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        return json.loads(result.stdout) if result.stdout.strip() else {}

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

    def test_create_goal_before_review_pass_is_structurally_blocked(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_blocking=True)
            result = self.run_hook(
                root,
                goal_payload(root),
                event="pre_tool_use",
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["validation"]["status"], "FAIL")

    def test_create_goal_after_review_pass_is_structurally_allowed(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            set_phase(root, "review")
            result = self.run_hook(
                root,
                goal_payload(root, tool_name="functions.create_goal"),
                event="pre_tool_use",
            )
            self.assertEqual(result["status"], "CREATE_GOAL_ALLOWED")
            self.assertEqual(result["review_status"]["status"], "pass")
            self.assertFalse(result["continuation_required"])

    def test_user_prompt_hook_does_not_classify_approval_language(self) -> None:
        prompts = ("승인", "승인하지 마", "do not proceed", "진행 상황만 알려줘", "실행은 아직 하지 마")
        with temp_project() as td:
            root = make_project(Path(td))
            for prompt in prompts:
                with self.subTest(prompt=prompt):
                    result = self.run_hook(root, {"session_id": SESSION_ID, "prompt": prompt})
                    self.assertEqual(result["status"], "WARN")
                    self.assertTrue(result["continuation_required"])
                    self.assertNotIn("proceed_prompt", result)
                    self.assertNotIn("review_status", result)

    def test_create_goal_is_blocked_outside_review_phase(self) -> None:
        for phase in ("plan", "completed"):
            with self.subTest(phase=phase), temp_project() as td:
                root = make_project(Path(td), phase=phase)
                result = self.run_hook(
                    root,
                    goal_payload(root),
                    event="pre_tool_use",
                )
                self.assertEqual(result["status"], "BLOCKED")
                self.assertIn("only", result["reason"])

    def test_completed_request_does_not_capture_unrelated_prompt(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), phase="completed")
            result = self.run_hook(root, {"session_id": SESSION_ID, "prompt": "다른 작업을 진행해줘"})
            self.assertEqual(result["status"], "PREPASS")
            self.assertFalse(result["prompt_relevant"])

    def test_duplicate_create_goal_is_blocked_by_local_goal_status(self) -> None:
        for goal_status in ("active", "completing"):
            with self.subTest(goal_status=goal_status), temp_project() as td:
                root = make_project(Path(td))
                request_dir = root / ".simple" / "requests" / REQUEST_ID
                write_json(
                    request_dir / "state.json",
                    {
                        "request_id": REQUEST_ID,
                        "phase": "review",
                        "goal_status": goal_status,
                        "goal_plan_fingerprint": "sha256:" + sha256(request_dir / "plan.md"),
                    },
                )
                result = self.run_hook(
                    root,
                    goal_payload(root),
                    event="pre_tool_use",
                )
                self.assertEqual(result["status"], "BLOCKED")
                self.assertIn("already", result["reason"])

    def test_unrelated_create_goal_prepasses_without_simple_request(self) -> None:
        with temp_project() as td:
            result = self.run_hook(
                Path(td),
                goal_payload(objective="Stageflow implementation-plan request"),
                event="pre_tool_use",
            )
            self.assertEqual(result["status"], "PREPASS")
            self.assertFalse(result["simple_workflow_goal_candidate"])

    def test_unrelated_create_goal_prepasses_with_active_simple_pointer(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            result = self.run_hook(
                root,
                goal_payload(objective="Atomic Docs accepted write scope"),
                event="pre_tool_use",
            )
            self.assertEqual(result["status"], "PREPASS")
            self.assertFalse(result["simple_workflow_goal_candidate"])

    def test_stageflow_goal_about_simple_workflow_source_still_prepasses(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            result = self.run_hook(
                root,
                goal_payload(objective="Stageflow goal: harden Simple Workflow hooks and .simple state"),
                event="pre_tool_use",
            )
            self.assertEqual(result["status"], "PREPASS")
            self.assertFalse(result["simple_workflow_goal_candidate"])

    def test_unrelated_create_goal_prepasses_with_completed_simple_pointer(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), phase="completed")
            result = self.run_hook(
                root,
                goal_payload(objective="Stageflow implementation request"),
                event="pre_tool_use",
            )
            self.assertEqual(result["status"], "PREPASS")

    def test_simple_goal_objective_must_name_selected_request(self) -> None:
        other_ids = ("20260710-1200-other", REQUEST_ID + "-other")
        for other_id in other_ids:
            with self.subTest(other_id=other_id), temp_project() as td:
                root = make_project(Path(td))
                result = self.run_hook(
                    root,
                    goal_payload(
                        objective=(
                            f".simple/requests/{other_id}/plan.md "
                            "Reviewed Plan Fingerprint sha256:" + "0" * 64
                        )
                    ),
                    event="pre_tool_use",
                )
                self.assertEqual(result["status"], "BLOCKED")
                self.assertIn("selected request id", result["reason"])

    def test_simple_plan_path_requires_exact_token_boundary(self) -> None:
        suffixes = (".bak", "/extra", "?draft")
        for suffix in suffixes:
            with self.subTest(suffix=suffix), temp_project() as td:
                root = make_project(Path(td))
                result = self.run_hook(
                    root,
                    goal_payload(
                        objective=(
                            f"Stageflow goal mentioning .simple/requests/{REQUEST_ID}/plan.md{suffix} "
                            "while hardening Simple Workflow source"
                        )
                    ),
                    event="pre_tool_use",
                )
                self.assertEqual(result["status"], "PREPASS")
                self.assertFalse(result["simple_workflow_goal_candidate"])

    def test_simple_goal_objective_fingerprint_must_match_current_plan(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            objective = (
                f".simple/requests/{REQUEST_ID}/plan.md "
                "Reviewed Plan Fingerprint sha256:" + "0" * 64
            )
            result = self.run_hook(
                root,
                goal_payload(objective=objective),
                event="pre_tool_use",
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("current plan fingerprint", result["reason"])

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

    def test_v2_pending_plan_readiness_holds_execution_for_approval(self) -> None:
        with temp_project() as td:
            root = make_v2_project(
                Path(td),
                phase="review",
                goal_status="active",
                approval_status="pending",
                goal_fingerprint="sha256:" + "1" * 64,
                approved_fingerprint="sha256:" + "2" * 64,
            )
            result = self.run_hook(root, {"session_id": SESSION_ID, "prompt": "상태 알려줘"})
            self.assertEqual(result["status"], "WARN")
            self.assertEqual(result["workflow_version"], 2)
            self.assertEqual(result["plan_approval_status"], "pending")
            self.assertTrue(any("awaits explicit user approval" in warning for warning in result["warnings"]))

    def test_v2_pending_plan_stop_allows_reapproval_response(self) -> None:
        with temp_project() as td:
            root = make_v2_project(
                Path(td),
                phase="review",
                goal_status="active",
                approval_status="pending",
                goal_fingerprint="sha256:" + "1" * 64,
                approved_fingerprint="sha256:" + "2" * 64,
            )
            result = self.run_hook(root, {"session_id": SESSION_ID}, event="stop")
            self.assertEqual(result["status"], "PASS")
            self.assertNotIn("decision", result)

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
            result = self.run_hook(
                root,
                goal_payload(root),
                event="pre_tool_use",
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["review_status"]["status"], "stale")

    def test_review_flow_issue_blocks_proceed(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_flow_issue=True)
            result = self.run_hook(
                root,
                goal_payload(root),
                event="pre_tool_use",
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["validation"]["status"], "FAIL")

    def test_review_question_depth_issue_blocks_proceed(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_question_depth_issue=True)
            result = self.run_hook(
                root,
                goal_payload(root),
                event="pre_tool_use",
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["validation"]["status"], "FAIL")

    def test_fail_text_containing_pass_blocks_create_goal(self) -> None:
        for verdict in ("FAIL: do not PASS", "pass", "Pass"):
            with self.subTest(verdict=verdict), temp_project() as td:
                root = make_project(Path(td))
                review = root / ".simple" / "requests" / REQUEST_ID / "review.md"
                review.write_text(
                    review.read_text(encoding="utf-8").replace("\nPASS\n", f"\n{verdict}\n"),
                    encoding="utf-8",
                )
                result = self.run_hook(
                    root,
                    goal_payload(root),
                    event="pre_tool_use",
                )
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual(result["validation"]["status"], "FAIL")

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
        pretool_commands = [command for command in commands if "e='pre_tool_use'" in command]
        self.assertEqual(len(pretool_commands), 1)

    def test_user_prompt_wire_output_uses_additional_context(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            wire = self.run_wire(root, {"session_id": SESSION_ID, "prompt": "상태 알려줘"}, "user_prompt_submit")
            output = wire["hookSpecificOutput"]
            self.assertEqual(output["hookEventName"], "UserPromptSubmit")
            context = json.loads(output["additionalContext"])
            self.assertEqual(context["status"], "WARN")

    def test_create_goal_block_uses_pretool_deny_wire_output(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), phase="plan")
            wire = self.run_wire(
                root,
                goal_payload(root),
                "pre_tool_use",
            )
            output = wire["hookSpecificOutput"]
            self.assertEqual(output["hookEventName"], "PreToolUse")
            self.assertEqual(output["permissionDecision"], "deny")

    def test_allowed_create_goal_emits_no_wire_block(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            wire = self.run_wire(
                root,
                goal_payload(root),
                "pre_tool_use",
            )
            self.assertEqual(wire, {})

    def test_hook_wrapper_prefers_stageflow_cache_before_legacy_cache(self) -> None:
        text = HOOK_WRAPPER.read_text(encoding="utf-8-sig")

        self.assertIn("return existing[0] if existing else", text)
        self.assertIn('"PreToolUse": "pre_tool_use"', text)
        self.assertNotIn("max(existing", text)
        self.assertLess(
            text.index(".codex/plugins/cache/**/stageflow*/**/scripts/simple_workflow_hook_check.py"),
            text.index(".codex/plugins/cache/**/simple-workflow-plugin/**/scripts/simple_workflow_hook_check.py"),
        )

    def test_stop_event_checks_current_request(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), write_plan=False)
            result = self.run_hook(root, {"session_id": SESSION_ID}, event="stop")
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("plan.md", result["reason"])


def set_phase(root: Path, phase: str) -> None:
    request_dir = root / ".simple" / "requests" / REQUEST_ID
    current_dir = root / ".simple" / "sessions" / SESSION_ID
    write_json(request_dir / "state.json", {"request_id": REQUEST_ID, "phase": phase, "last_validated_at": None})
    write_json(current_dir / "current.json", {"request_id": REQUEST_ID, "phase": phase, "activated_by": "test"})
    write_json(root / ".simple" / "index.json", {"version": "1", "requests": [{"id": REQUEST_ID, "title": "Test", "status": phase}]})
    if phase == "review":
        fp = sha256(request_dir / "plan.md")
        (request_dir / "review.md").write_text(review_text(fp), encoding="utf-8")


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
        objective = (
            f"Simple Workflow request {REQUEST_ID} "
            f".simple/requests/{REQUEST_ID}/plan.md "
            f"Reviewed Plan Fingerprint sha256:{fingerprint}"
        )
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
