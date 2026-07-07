from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ATOMIC_IMPL = ROOT / "skills" / "atomic-impl"
SKILL = ATOMIC_IMPL / "SKILL.md"
FLOW = ATOMIC_IMPL / "references" / "implementation-flow.md"
OPENAI_YAML = ATOMIC_IMPL / "agents" / "openai.yaml"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class AtomicImplSkillTests(unittest.TestCase):
    def test_atomic_impl_skill_entry_defines_docs_first_implementation(self) -> None:
        text = read(SKILL)

        self.assertIn("name: atomic-impl", text)
        self.assertIn("requirements -> atomic-docs managed docs", text)
        self.assertIn("user summary and document-path approval", text)
        self.assertIn("code implementation -> docs/code compliance review", text)
        self.assertIn("Read `references/implementation-flow.md` before taking action", text)
        self.assertIn("skills/atomic-docs/SKILL.md", text)
        self.assertIn("Treat the written or updated atomic docs as the implementation source of truth", text)
        self.assertIn("Do not implement code before the relevant atomic docs are written or updated", text)
        self.assertIn("explicitly approved as the implementation basis", text)
        self.assertIn("Do not bypass `atomic-docs` setup", text)
        self.assertIn("criteria approval", text)
        self.assertIn("docs write scope approval", text)
        self.assertIn("Goal gate", text)
        self.assertIn("writer/reviewer cycle", text)
        self.assertIn("post-write gate", text)
        self.assertIn("`.stageflow/atomic-docs.json`", text)
        self.assertIn("`project/atomization-criteria.md`", text)
        self.assertIn("blocking `confirmation_needed` gaps", text)
        self.assertNotIn("TODO", text)

    def test_implementation_flow_preserves_atomic_docs_gates_before_code(self) -> None:
        text = read(FLOW)

        self.assertIn("user requirements -> atomic-docs managed docs -> user approval -> code implementation", text)
        self.assertIn("Read `skills/atomic-docs/SKILL.md` before any managed docs action", text)
        self.assertIn("If atomic-docs config or managed docs root is missing", text)
        self.assertIn("Stop after the accepted bootstrap/criteria step requires user review", text)
        self.assertIn("If `project/atomization-criteria.md` is missing", text)
        self.assertIn("stop for criteria approval", text)
        self.assertIn("docs write scope is not accepted", text)
        self.assertIn("If docs generation requires a Codex Goal", text)
        self.assertIn("Do not treat Stageflow plan approval, chat approval, or code implementation approval as managed-docs-root approval", text)
        self.assertIn("Do not start code implementation until the user explicitly approves", text)

    def test_implementation_flow_requires_reconstruction_ready_detail(self) -> None:
        text = read(FLOW)

        for required_detail in [
            "user intent, confirmed rules, inferred rules marked as inferred",
            "input conditions, branches, validation/refusal/defaulting",
            "state transitions, persistence effects, external calls, events, and side effects",
            "UI or API contract details, payload fields, forms, routes",
            "failure, retry, fallback, recovery, and runtime exception behavior",
            "source evidence, judgment labels, `Gaps`, related `atom_key`, AID, and graph relationships",
            "Avoid endpoint lists, source identifier lists, class-role summaries, or method-call sequences",
        ]:
            self.assertIn(required_detail, text)

    def test_implementation_flow_requires_user_summary_with_doc_paths(self) -> None:
        text = read(FLOW)

        self.assertIn("changed docs paths and which path the user should inspect", text)
        self.assertIn("behavior that will be implemented from the docs", text)
        self.assertIn("important conditions, branches, validations, state changes, side effects, and failures", text)
        self.assertIn("unresolved `Gaps`, `confirmation_needed`, or out-of-scope behavior", text)
        self.assertIn("partial-scope or full-scope implementation basis", text)

    def test_implementation_flow_requires_post_implementation_compliance_review(self) -> None:
        text = read(FLOW)

        self.assertIn("Run the project tests, validators, linters, or targeted commands", text)
        self.assertIn("Compare the confirmed user requirement, approved atomic docs, actual diff, and validation results", text)
        self.assertIn("missing documented behavior, undocumented implementation behavior, stale docs", text)
        self.assertIn("If the code differs from the approved docs", text)
        self.assertIn("Summarize the final docs/code compliance result", text)

    def test_atomic_impl_openai_metadata_mentions_skill_name(self) -> None:
        text = read(OPENAI_YAML)

        self.assertIn('display_name: "Atomic Impl"', text)
        self.assertIn('short_description: "Atomic-docs guided implementation flow."', text)
        self.assertIn("Use $atomic-impl", text)
        self.assertNotIn("Use -impl", text)

    def test_plugin_manifest_exposes_atomic_impl_prompt(self) -> None:
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        prompts = manifest["interface"]["defaultPrompt"]

        self.assertIn("atomic-impl for docs-first implementation", manifest["interface"]["longDescription"])
        self.assertIn("Use atomic-impl to write requirements into atomic docs before implementing code.", prompts)


if __name__ == "__main__":
    unittest.main()
