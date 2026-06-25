from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_SKILL = ROOT / "skills" / "atomic-docs" / "SKILL.md"
DOCS_REFS = ROOT / "skills" / "atomic-docs" / "references"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class DocsSkillTests(unittest.TestCase):
    def test_docs_skill_entry_references_required_contracts(self) -> None:
        text = read(DOCS_SKILL)
        self.assertIn("name: atomic-docs", text)
        self.assertIn("create, update, inspect, refresh, and manage", text)
        for reference in [
            "docs-root-and-config.md",
            "atomic-document-contract.md",
            "language-policy.md",
            "refresh-flow.md",
            "atomic-graph.md",
            "stageflow-integration.md",
        ]:
            self.assertIn(reference, text)
        self.assertIn("Do not assume a hardcoded `docs/` root", text)
        self.assertIn("source-code commit hash baseline", text)
        self.assertIn("Respect Stageflow gates", text)
        self.assertIn("language policy", text)

    def test_language_policy_chooses_user_or_existing_docs_language(self) -> None:
        text = read(DOCS_REFS / "language-policy.md")
        self.assertIn("language explicitly requested by the user", text)
        self.assertIn("dominant language already used", text)
        self.assertIn("current conversation language", text)
        self.assertIn("default to Korean", text)
        self.assertIn("managed docs prose, docs change plans", text)
        for fixed_term in [
            "Intent",
            "Rules",
            "Current Implementation",
            "Planned Changes",
            "Gaps",
            "graph_edges",
            "docs_root",
            "source-code identifiers",
            "option labels",
            "Stageflow artifact",
        ]:
            self.assertIn(fixed_term, text)
        self.assertIn("Do not translate code identifiers or schema keys", text)
        self.assertIn("ask before writing confirmed docs", text)
        self.assertIn("leftover English filler text", text)
        self.assertIn("change plan and managed docs prose should use the user/artifact language", text)


    def test_plugin_manifest_exposes_docs_skill_prompts(self) -> None:
        manifest = read(ROOT / ".codex-plugin" / "plugin.json")
        self.assertIn('"skills": "./skills/"', manifest)
        self.assertIn("Documentation", manifest)
        self.assertIn("expose an atomic-docs skill", manifest)
        self.assertIn("Use atomic-docs to create submodule-backed project documentation.", manifest)
        self.assertIn("Use atomic-docs to refresh atomic.md docs from source-code changes.", manifest)
        self.assertIn("Use atomic-docs to inspect intent, implementation, planned changes, and gaps.", manifest)

    def test_docs_root_contract_preserves_submodule_and_confirmation_rules(self) -> None:
        text = read(DOCS_REFS / "docs-root-and-config.md")
        self.assertIn("Do not assume a hardcoded `docs/` root", text)
        self.assertIn("inspect `.gitmodules`", text)
        self.assertIn("exactly one candidate, still ask the user to confirm", text)
        self.assertIn("`.stageflow/docs-submodule.json`", text)
        for field in ["docs_root", "source_root", "baseline_metadata_path"]:
            self.assertIn(field, text)
        self.assertIn("source repository root used for diffs", text)
        self.assertIn("Do not silently create a real submodule", text)

    def test_atomic_document_contract_sections_and_boundaries(self) -> None:
        text = read(DOCS_REFS / "atomic-document-contract.md")
        self.assertIn("<doc-root>/<domain>/<atomic-target>/atomic.md", text)
        self.assertIn("domain folder", text)
        self.assertIn("globally unique", text)
        for section in ["Intent", "Rules", "Current Implementation", "Planned Changes", "Gaps"]:
            self.assertIn(section, text)
        self.assertIn("marked as inferred", text)
        self.assertIn("Do not put per-atomic freshness/status fields inside `atomic.md`", text)
        self.assertIn("Do not store per-file commit status", text)
        self.assertNotIn("<doc-root>/<domain>/current-state", text)

    def test_refresh_flow_contract_uses_source_baseline_and_change_plan(self) -> None:
        text = read(DOCS_REFS / "refresh-flow.md")
        self.assertIn("one source-code commit hash", text)
        self.assertIn("metadata at the documentation submodule root", text)
        self.assertIn("git diff <stored-source-hash>..HEAD", text)
        self.assertIn("changed source behavior files", text)
        self.assertIn("auxiliary files by default unless the user requested", text)
        self.assertIn("source-to-atomic seed discovery", text)
        self.assertIn("domain-grouped change plan", text)
        self.assertIn("implemented-plan candidates", text)
        self.assertIn("rename/merge proposals", text)

    def test_atomic_graph_contract_fields_and_traversal(self) -> None:
        text = read(DOCS_REFS / "atomic-graph.md")
        self.assertIn("graph_edges", text)
        for field in ["type", "target_key", "target_path", "reason"]:
            self.assertIn(field, text)
        self.assertIn("Duplicate `target_key` values are invalid conflicts", text)
        self.assertIn("Do not silently auto-prefix", text)
        self.assertIn("correct the path", text)
        self.assertIn("controlled vocabulary", text)
        self.assertIn("directional", text)
        self.assertIn("explicit inverse edges only when", text)
        self.assertIn("may only target existing `atomic.md` files", text)
        self.assertIn("Stop when no further modification candidates appear", text)
        self.assertIn("Do not create a root graph output by default", text)
        self.assertIn("not strength or priority fields", text)
        self.assertIn("Do not add relationship strength, priority", text)

    def test_stageflow_integration_contract_respects_gates_and_source_evidence(self) -> None:
        text = read(DOCS_REFS / "stageflow-integration.md")
        self.assertIn("Respect Stageflow definition", text)
        self.assertIn("implementation-plan gate passes", text)
        self.assertIn("Source files are the default evidence source", text)
        self.assertIn("Stageflow artifacts are not the default docs refresh evidence source", text)
        self.assertIn("modify only files inside the configured documentation submodule root", text)
        self.assertIn("prioritize the current explicit user-requested scope", text)
        self.assertIn("Gaps", text)


if __name__ == "__main__":
    unittest.main()

