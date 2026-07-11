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
        self.assertIn("requirements -> implementation-basis atomic docs", text)
        self.assertIn("code implementation -> implementation review -> user approval -> final atomic-docs update", text)
        self.assertIn("final docs/code compliance", text)
        self.assertIn("Read `references/implementation-flow.md` before taking action", text)
        self.assertIn("skills/atomic-docs/SKILL.md", text)
        self.assertIn("source of truth for product decisions, required behavior, verification conditions, and boundaries", text)
        self.assertIn("Use project source and conventions for internal implementation mechanics", text)
        self.assertIn("Do not implement code before the relevant atomic docs are written or updated", text)
        self.assertIn("put new requested behavior mainly in `Planned Changes`", text)
        self.assertIn("`Current Implementation` only for behavior already observed in source", text)
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
        self.assertIn("run `Intent Compliance Review` and `Flow / Unexpected Issue Review`", text)
        self.assertIn("require explicit user approval before final atomic-docs update", text)
        self.assertIn("move completed approved items from `Planned Changes` to `Current Implementation`", text)
        self.assertIn("Do not record out-of-plan changes", text)
        self.assertNotIn("TODO", text)

    def test_implementation_flow_preserves_atomic_docs_gates_before_code(self) -> None:
        text = read(FLOW)

        self.assertIn("user requirements -> implementation-basis atomic docs -> user approval -> code implementation", text)
        self.assertIn("Read `skills/atomic-docs/SKILL.md` before any managed docs action", text)
        self.assertIn("If atomic-docs config or managed docs root is missing", text)
        self.assertIn("Stop after the accepted bootstrap/criteria step requires user review", text)
        self.assertIn("If `project/atomization-criteria.md` is missing", text)
        self.assertIn("stop for criteria approval", text)
        self.assertIn("docs write scope is not accepted", text)
        self.assertIn("If docs generation requires a Codex Goal", text)
        self.assertIn("Do not treat Stageflow plan approval, chat approval, or code implementation approval as managed-docs-root approval", text)
        self.assertIn("Do not start code implementation until the user explicitly approves", text)

    def test_implementation_flow_requires_decision_complete_proportional_detail(self) -> None:
        text = read(FLOW)

        for required_detail in [
            "user intent, confirmed rules, inferred rules marked as inferred",
            "new requested behavior as `Planned Changes`",
            "existing source-observed behavior as `Current Implementation` only when source evidence proves it already exists",
            "when they change a product decision or observable result",
            "when they are part of the required contract",
            "only when fields, routes, states, payloads, or save/delete scope affect required behavior or verification",
            "when the requirement assigns a specific outcome",
            "source evidence, judgment labels, `Gaps`, related `atom_key`, AID, and graph relationships",
            "Avoid endpoint lists, source identifier lists, class-role summaries, or method-call sequences",
            "avoid copying behavior-neutral source detail",
        ]:
            self.assertIn(required_detail, text)

    def test_implementation_requires_inline_verification_and_source_aware_review(self) -> None:
        text = read(SKILL) + read(FLOW)
        for required in (
            "observable verification condition or verifiable invariant",
            "do not require a separate acceptance AID",
            "domain development-quality reviewer",
            "applicable risk/contract reviewer",
            "relevant source evidence",
            "Needing source for internal mechanics is expected",
            "return to docs writing rather than approving implementation",
        ):
            self.assertIn(required, text)

    def test_implementation_compliance_uses_linked_post_write_review(self) -> None:
        text = read(SKILL) + read(FLOW)
        for required in (
            ".stageflow/atomic-docs/requests/<request-id>/post-write-review.md",
            "## 구현 검증",
            "docs basis",
            "implementation basis",
            "관련 AID | 구현 근거 | 검증 근거 | 판정 또는 gap",
            "changed in-scope required AID",
            "Do not create a separate trace file",
            "recheck only affected rows",
            "Draft one `## 구현 검증` section",
            "Preserve the draft `## 구현 검증` section",
            "Finalize the linked `post-write-review.md` `## 구현 검증` section",
        ):
            self.assertIn(required, text)
        self.assertNotIn("verification-trace.json", text)

    def test_implementation_flow_requires_user_summary_with_doc_paths(self) -> None:
        text = read(FLOW)

        self.assertIn("changed docs paths and which path the user should inspect", text)
        self.assertIn("behavior that will be implemented from the docs", text)
        self.assertIn("important decisions, contracts, validations, state changes, side effects, failures, and verification conditions", text)
        self.assertIn("unresolved `Gaps`, `confirmation_needed`, or out-of-scope behavior", text)
        self.assertIn("partial-scope or full-scope implementation basis", text)

    def test_implementation_flow_requires_post_implementation_compliance_review(self) -> None:
        text = read(FLOW)

        self.assertIn("Run the project tests, validators, linters, or targeted commands", text)
        self.assertIn("Run `Intent Compliance Review`", text)
        self.assertIn("Run `Flow / Unexpected Issue Review`", text)
        self.assertIn("compare the confirmed user requirement, approved atomic docs, actual diff, and validation results", text)
        self.assertIn("state transitions, data flow, validation, failure/recovery, side effects", text)
        self.assertIn("Ask whether to approve the implementation result and final docs update", text)
        self.assertIn("missing documented behavior, undocumented implementation behavior, stale docs", text)
        self.assertIn("If the code differs from the final docs", text)
        self.assertIn("Summarize the final docs/code compliance result", text)

    def test_final_docs_update_requires_user_approval_and_atomic_docs_gates(self) -> None:
        text = read(FLOW)

        self.assertIn("Do not update final atomic docs until the user explicitly approves", text)
        self.assertIn("update atomic docs through the existing `atomic-docs` gates", text)
        self.assertIn("Move completed approved items from `Planned Changes` to `Current Implementation`", text)
        self.assertIn("Add or refresh source evidence and validation basis", text)
        self.assertIn("Do not record out-of-plan changes as confirmed behavior unless the user explicitly approved those changes", text)
        self.assertIn("Compare the confirmed user requirement, approved implementation result, final atomic docs, actual diff, and validation results", text)

    def test_atomic_impl_openai_metadata_mentions_skill_name(self) -> None:
        text = read(OPENAI_YAML)

        self.assertIn('display_name: "Atomic Impl"', text)
        self.assertIn('short_description: "Implement and verify from approved atomic docs."', text)
        self.assertIn("Use $atomic-impl", text)
        self.assertIn("verify changed required AIDs", text)
        self.assertNotIn("Use -impl", text)

    def test_plugin_manifest_exposes_atomic_impl_prompt(self) -> None:
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        prompts = manifest["interface"]["defaultPrompt"]

        self.assertIn("atomic-impl for docs-first implementation", manifest["interface"]["longDescription"])
        self.assertIn("Use atomic-impl to write requirements into atomic docs before implementing code.", prompts)


if __name__ == "__main__":
    unittest.main()
