from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "atomic-impl" / "SKILL.md"
FLOW = ROOT / "skills" / "atomic-impl" / "references" / "implementation-flow.md"
OPENAI = ROOT / "skills" / "atomic-impl" / "agents" / "openai.yaml"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class AtomicImplSkillTests(unittest.TestCase):
    def test_flow_has_two_user_approval_gates(self) -> None:
        text = read(SKILL) + read(FLOW)
        self.assertIn("explicit user approval before code implementation", text)
        self.assertIn("explicit user approval before final Atomic Docs promotion", text)
        self.assertIn("Do not start code until the user explicitly approves", text)
        self.assertIn("Do not finalize Atomic Docs before explicit result approval", text)

    def test_requirements_use_one_owning_rid(self) -> None:
        text = read(SKILL) + read(FLOW)
        for required in (
            "[RID:<atom_key>.<lower-kebab-slug>]",
            "exactly once",
            "owning Atom's `Changes`",
            "There is no RID reference",
            "required outcome or invariant",
            "future boundary change in its RID item",
            "established `Boundaries`",
        ):
            self.assertIn(required, text)

    def test_completion_promotes_semantics_and_removes_rid(self) -> None:
        text = read(SKILL) + read(FLOW)
        for required in (
            "remove the RID",
            "`Contracts` or `Boundaries`",
            "`Implementation` and `Sources`",
            "Completed work has no RID left",
            "Use exact `- 없음`",
            "validate the final reviewed docs again",
        ):
            self.assertIn(required, text)

    def test_old_atomic_docs_control_plane_is_not_used(self) -> None:
        text = read(SKILL) + read(FLOW)
        for retired in (
            "context_selection.version",
            "post-write-review.md",
            "[AID-REF:",
            "source-baseline.json",
            "operation-events.jsonl",
            "acceptance fingerprint",
        ):
            self.assertNotIn(retired, text)

    def test_implementation_review_uses_docs_diff_and_validation(self) -> None:
        text = read(FLOW)
        for required in (
            "approved docs basis",
            "actual code diff",
            "validation output",
            "RID coverage",
            "data/state flow",
            "side effects",
            "failure/recovery",
            "test evidence",
            "scope drift",
        ):
            self.assertIn(required, text)

    def test_metadata_and_manifest_use_rid_flow(self) -> None:
        metadata = read(OPENAI)
        manifest = json.loads(read(ROOT / ".codex-plugin" / "plugin.json"))
        self.assertIn('display_name: "Atomic Impl"', metadata)
        self.assertIn("record requirements as Atomic Docs RIDs", metadata)
        self.assertIn(
            "Use atomic-impl to record requirements as RIDs before implementing code.",
            manifest["interface"]["defaultPrompt"],
        )


if __name__ == "__main__":
    unittest.main()
