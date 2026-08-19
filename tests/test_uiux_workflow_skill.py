from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "uiux-workflow"
SKILL = SKILL_DIR / "SKILL.md"
REVIEW = SKILL_DIR / "references" / "review-contract.md"
OPENAI = SKILL_DIR / "agents" / "openai.yaml"
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class UIUXWorkflowSkillTests(unittest.TestCase):
    def test_explicit_invocation_is_the_only_trigger(self) -> None:
        skill = read(SKILL)
        metadata = read(OPENAI)

        self.assertIn("name: uiux-workflow", skill)
        self.assertIn("Use only when the user explicitly invokes", skill)
        self.assertIn("$stageflow:uiux-workflow", skill)
        self.assertIn("[$stageflow:uiux-workflow](...)", skill)
        self.assertIn("Do not infer activation", skill)
        self.assertIn("Never invoke implicitly", skill)
        self.assertIn("allow_implicit_invocation: false", metadata)
        self.assertIn("Use $stageflow:uiux-workflow", metadata)
        self.assertNotIn("TODO", skill + metadata)

    def test_design_basis_is_root_owned_and_optional(self) -> None:
        skill = read(SKILL)

        for required in (
            "user-specified project root as authoritative",
            "resolve each changed repository independently",
            "case-sensitive exact path `<target-root>/design.md`",
            "Do not recursively search",
            "If `design.md` is absent",
            "Do not apply one repository's UI guidance to another repository",
            "the user's explicit current requirements",
            "the applicable root `design.md`",
            "observed existing components, tokens, styles, and project conventions",
        ):
            self.assertIn(required, skill)

    def test_conflicts_require_material_user_decisions(self) -> None:
        skill = read(SKILL)

        self.assertIn("material conflict", skill)
        self.assertIn("scope", skill)
        self.assertIn("destructive UI change", skill)
        self.assertIn("decision needed before implementing", skill)
        self.assertIn("Do not silently rewrite", skill)

    def test_implementation_and_observation_cover_uiux_flow(self) -> None:
        skill = read(SKILL)

        for required in (
            "existing reusable components and design tokens",
            "layout and responsive behavior",
            "accessibility semantics and contrast",
            "Implement the requested UI code, styles, and assets",
            "inspect the actual rendered UI",
            "Do not install packages, download a browser",
            "record the exact verification gap",
            "That gap requires `FAIL`",
            "Do not claim visual PASS from unrelated tests",
        ):
            self.assertIn(required, skill)

    def test_review_contract_uses_raw_evidence_and_fixed_criteria(self) -> None:
        contract = read(REVIEW)

        for required in (
            "raw task evidence",
            'fork_turns: "none"',
            "no inherited conversation history",
            "does not edit source",
            "inspected existing component, token, style, and interaction-pattern evidence",
            "## Fixed Review Criteria",
            "User intent and scope",
            "Guideline fidelity",
            "Existing-system consistency",
            "Layout and responsiveness",
            "Interaction states",
            "Accessibility",
            "Implementation integrity",
            "Observable outcome",
            "they do not prove actual appearance or interaction",
            "VERDICT: PASS|FAIL",
            "CYCLE: 1|2",
            "`PASS` with a critical item under `UNVERIFIED` is invalid",
            "Do not include author commentary",
            "do not include the main agent's interpretation",
        ):
            self.assertIn(required, contract)

    def test_review_cycle_is_bounded_to_two_passes(self) -> None:
        text = read(SKILL) + read(REVIEW)

        for required in (
            "at most two total review cycles",
            "Cycle 1",
            "Cycle 2",
            "Do not start Cycle 3",
            "Do not add a new quality bar",
            "Cycle 2 `FAIL` is terminal",
            "stop after Cycle 1 and report it",
            "main agent remains the only implementation owner",
        ):
            self.assertIn(required, text)

    def test_plugin_manifest_exposes_explicit_uiux_prompt(self) -> None:
        manifest = json.loads(read(PLUGIN))
        interface = manifest["interface"]

        self.assertIn("uiux-workflow", interface["longDescription"])
        self.assertIn("UI/UX Workflow", interface["capabilities"])
        self.assertIn(
            "Use $stageflow:uiux-workflow to implement and review a UI/UX change against the target project's design.md.",
            interface["defaultPrompt"],
        )


if __name__ == "__main__":
    unittest.main()
