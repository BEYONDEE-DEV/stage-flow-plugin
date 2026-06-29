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
            "change-judgment-policy.md",
            "atomic-graph.md",
            "stageflow-integration.md",
        ]:
            self.assertIn(reference, text)
        self.assertIn("Do not assume a hardcoded `docs/` root", text)
        self.assertIn("source-code commit hash baseline", text)
        self.assertIn("Respect Stageflow gates", text)
        self.assertIn("language policy", text)
        self.assertIn("controlled judgment labels", text)

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
        self.assertIn("Use atomic-docs to refresh atom files from source-code changes.", manifest)
        self.assertNotIn("refresh atomic.md docs", manifest)
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
        self.assertIn("accepted the docs-root setup scope and config write", text)

    def test_docs_skill_requires_write_approval_for_managed_state(self) -> None:
        text = read(DOCS_SKILL)
        self.assertIn("accepted the explicit docs operation scope and change plan", text)
        self.assertIn("limited draft write action", text)
        self.assertIn("project/atomization-criteria-atom.md", text)
        for write_target in [
            "managed docs",
            "atom files",
            "graph corrections",
            "source-baseline metadata",
            "`.stageflow/docs-submodule.json`",
        ]:
            self.assertIn(write_target, text)
        self.assertIn("Stageflow plan approval as separate from docs-submodule approval", text)
        self.assertIn("Write only the paths and actions accepted by the user", text)

    def test_docs_skill_uses_file_first_criteria_before_subagent_writing_and_review(self) -> None:
        text = read(DOCS_SKILL)
        self.assertIn("first atomic-docs write action", text)
        self.assertIn("limited draft creation or update", text)
        self.assertIn("user conversation criteria, prohibitions, atomization concerns", text)
        self.assertIn("criteria atom itself as the center of review, user revision, and approval", text)
        self.assertIn("Do not start domain atom writing or domain subagent work until the criteria atom is approved", text)
        self.assertIn("Use only an approved criteria atom as required input", text)

    def test_atomic_document_contract_sections_and_boundaries(self) -> None:
        text = read(DOCS_REFS / "atomic-document-contract.md")
        self.assertIn("<doc-root>/<domain>/<atomic-target>-atom.md", text)
        self.assertIn("<doc-root>/project/atomization-criteria-atom.md", text)
        self.assertIn("domain folder", text)
        self.assertIn("Every atom file must end with `-atom.md`", text)
        self.assertIn("globally unique", text)
        self.assertNotIn("<doc-root>/<domain>/<atomic-target>/atomic.md", text)
        for section in ["Intent", "Rules", "Current Implementation", "Planned Changes", "Gaps"]:
            self.assertIn(section, text)
        self.assertIn("marked as inferred", text)
        self.assertIn("Do not put per-atomic freshness/status fields inside atom files", text)
        self.assertIn("Do not store per-file commit status", text)
        self.assertNotIn("<doc-root>/<domain>/current-state", text)

    def test_change_judgment_policy_labels_and_priority(self) -> None:
        text = read(DOCS_REFS / "change-judgment-policy.md")
        self.assertIn("Change Judgment Policy", text)
        self.assertIn("does not add top-level per-atom status fields", text)
        for label in [
            "matches_confirmed_intent",
            "bug_or_regression",
            "missing_required_behavior",
            "unapproved_implemented_behavior",
            "out_of_scope_behavior",
            "confirmation_needed",
            "docs_stale",
        ]:
            self.assertIn(label, text)
        self.assertIn("Apply the first matching judgment", text)
        self.assertIn("docs baseline is older", text)
        self.assertIn("relevant `Intent`, `Rules`, requirement, boundary, or source mapping is inferred or ambiguous", text)
        self.assertIn("confirmed non-goal, excluded behavior, adjacent-domain boundary, or policy boundary", text)
        self.assertIn("confirmed required behavior is missing", text)
        self.assertIn("conflicts with confirmed `Intent`, `Rules`, acceptance criteria", text)
        self.assertIn("inferred `Intent` or inferred `Rules` alone", text)

    def test_change_judgment_policy_evidence_and_planned_change_types(self) -> None:
        text = read(DOCS_REFS / "change-judgment-policy.md")
        for required in [
            "atom, source evidence, judgment label, reason",
            "confirmed `Intent`",
            "approved required `Planned Changes`",
            "non-goals",
            "excluded behavior",
            "source baseline metadata",
            "not the absence of a `Gaps` item",
        ]:
            self.assertIn(required, text)
        for planned_type in [
            "approved_required_change",
            "approved_optional_change",
            "tentative_future_change",
            "implemented_pending_confirmation",
        ]:
            self.assertIn(planned_type, text)
        self.assertIn("Do not collapse bug, missing required behavior, unapproved implementation, out-of-scope behavior", text)

    def test_atomization_criteria_atom_contract_is_persisted(self) -> None:
        text = read(DOCS_REFS / "atomic-document-contract.md")
        self.assertIn("Atomization Criteria Atom", text)
        self.assertIn("<doc-root>/project/atomization-criteria-atom.md", text)
        self.assertIn("first atomic-docs write action", text)
        self.assertIn("draft criteria atom is a review artifact", text)
        self.assertIn("Criteria approval: draft, pending user approval", text)
        self.assertIn("Criteria approval: approved by user", text)
        self.assertIn("must not be used as the required input for domain writer subagents", text)
        self.assertIn("Record user-conversation criteria in the draft before code exploration", text)
        for section in ["Intent", "Rules", "Current Implementation", "Planned Changes", "Gaps"]:
            self.assertIn(section, text)
        for perspective in [
            "domain capability",
            "entry surface",
            "service/application flow",
            "state transition",
            "policy/rule",
            "integration contract",
            "persistence/side effect",
            "core business term",
            "failure/recovery",
        ]:
            self.assertIn(perspective, text)
        for required_detail in [
            "atom candidate criteria",
            "source evidence only criteria",
            "not applicable reason",
            "split/merge criteria",
            "source evidence requirement",
            "unresolved questions",
        ]:
            self.assertIn(required_detail, text)
        self.assertIn("writer subagent and review subagent checklists", text)
        self.assertIn("not fixed document types", text)
        self.assertIn("Do not accept a criteria atom that only lists perspective names", text)
        self.assertNotIn("endpoint document", text)

    def test_atomic_document_contract_supports_code_judgment_evidence(self) -> None:
        text = read(DOCS_REFS / "atomic-document-contract.md")
        self.assertIn("Judgment Evidence Policy", text)
        self.assertIn("required, optional, excluded, or boundary-defining", text)
        self.assertIn("acceptance criteria", text)
        self.assertIn("source-observed implementation facts with source evidence", text)
        for planned_type in [
            "approved_required_change",
            "approved_optional_change",
            "tentative_future_change",
            "implemented_pending_confirmation",
        ]:
            self.assertIn(planned_type, text)
        for label in [
            "bug_or_regression",
            "missing_required_behavior",
            "unapproved_implemented_behavior",
            "out_of_scope_behavior",
            "confirmation_needed",
            "docs_stale",
        ]:
            self.assertIn(label, text)
        self.assertIn("Do not add top-level per-atom status fields", text)
        self.assertIn("lack of a `Gaps` item", text)
        self.assertIn("non-goals, excluded behavior, and adjacent-domain boundaries", text)

    def test_domain_boundary_policy_uses_general_quality_gate(self) -> None:
        text = read(DOCS_REFS / "atomic-document-contract.md")
        self.assertIn("Domain Boundary Quality Gate", text)
        self.assertIn("durable ownership boundary", text)
        for criterion in [
            "product or business capability",
            "user-visible workflow",
            "operational responsibility",
            "integration contract",
            "shared policy or platform concern",
        ]:
            self.assertIn(criterion, text)
        for required_boundary in [
            "the behavior the domain owns",
            "the behavior the domain excludes",
            "the adjacent-domain boundary",
            "why the atom files in the domain tend to change together",
        ]:
            self.assertIn(required_boundary, text)
        self.assertIn("documentation section type, lifecycle state, task status, freshness state, review state", text)
        self.assertIn("temporary work grouping, code-layer grouping, screen grouping, or generic catch-all bucket", text)
        self.assertIn("split proposal based on observed capabilities", text)
        self.assertNotIn("Do not use document state names such as", text)


    def test_core_business_term_coverage_gate_prevents_parent_term_gaps(self) -> None:
        text = read(DOCS_REFS / "atomic-document-contract.md")
        self.assertIn("Core Business Term Coverage Gate", text)
        for evidence_source in [
            "type/interface names",
            "collection keys",
            "UI titles",
            "API payloads",
            "existing domain atoms",
        ]:
            self.assertIn(evidence_source, text)
        self.assertIn("source-repeated business nouns", text)
        self.assertIn("`project/project-glossary-atom.md`", text)
        self.assertIn("appropriate domain atom", text)
        self.assertIn("derived concept such as `resource deduction`", text)
        self.assertIn("parent business term such as `resource`", text)
        self.assertIn("Do not force admin, operator, or screen-centric language", text)
        self.assertIn("services, libraries, jobs, agents, or APIs", text)
        self.assertIn("caller, service, job, policy, or system flow", text)
        self.assertIn("UI or command entry point", text)
        for coverage_item in [
            "business meaning",
            "owning domain",
            "primary actor, user, or system action",
            "source of truth",
            "stored input fields versus API/computed output fields",
            "related status, hold, deduction, threshold, display, or availability rules",
            "aliases, related source identifiers, forbidden conflations, and uncertainty",
        ]:
            self.assertIn(coverage_item, text)
        self.assertIn("change plan or `Gaps`", text)

    def test_refresh_flow_contract_uses_source_baseline_and_change_plan(self) -> None:
        text = read(DOCS_REFS / "refresh-flow.md")
        self.assertIn("one source-code commit hash", text)
        self.assertIn("metadata at the documentation submodule root", text)
        self.assertIn("git diff <stored-source-hash>..HEAD", text)
        self.assertIn("classify the finding as `docs_stale`", text)
        self.assertIn("map baseline diffs to affected atoms", text)
        self.assertIn("changed source behavior files", text)
        self.assertIn("auxiliary files by default unless the user requested", text)
        self.assertIn("source-to-atom seed discovery", text)
        self.assertIn("domain-grouped change plan", text)
        self.assertIn("new domains, domain moves, atom splits, atom merges, and split proposals", text)
        self.assertIn("implemented-plan candidates", text)
        self.assertIn("rename/merge proposals", text)
        self.assertIn("source-baseline metadata updates and docs-root config writes", text)
        self.assertIn("core business terms that require glossary or domain atom coverage", text)
        self.assertIn("parent business terms missing or underdefined in the glossary", text)
        self.assertIn("accepted change plan defines the only paths and write actions", text)
        self.assertIn("Do not write atom files, graph corrections, source-baseline metadata", text)

    def test_refresh_flow_creates_draft_criteria_before_subagents(self) -> None:
        text = read(DOCS_REFS / "refresh-flow.md")
        self.assertIn("Atomization Criteria File-First Flow", text)
        self.assertIn("Atomization Perspectives Reviewed", text)
        self.assertIn("project/atomization-criteria-atom.md", text)
        self.assertIn("first atomic-docs write action", text)
        self.assertIn("limited draft creation or update", text)
        self.assertIn("draft criteria write action", text)
        self.assertIn("record criteria already stated in the user conversation", text)
        self.assertIn("use code exploration to enrich the criteria atom itself", text)
        self.assertIn("not just the change plan", text)
        self.assertIn("draft review artifact", text)
        self.assertIn("must not be used as the required input for domain writer subagents", text)
        self.assertIn("Domain Subagent Workflow", text)
        self.assertIn("only after the criteria atom is approved", text)
        self.assertIn("Each writer subagent must read the approved criteria atom", text)
        self.assertIn("judgment-labeled domain evidence packet", text)
        self.assertIn("change-judgment-policy.md", text)
        self.assertIn("judgment labels are absent or unsupported", text)
        self.assertIn("missing required behavior is confused with out-of-scope behavior", text)
        self.assertIn("independent review subagents", text)
        self.assertIn("review subagent fails", text)
        self.assertIn("rerun review", text)

    def test_refresh_flow_requires_criteria_change_plan_entries(self) -> None:
        text = read(DOCS_REFS / "refresh-flow.md")
        self.assertIn("limited first write action for draft criteria creation or update", text)
        self.assertIn("whether the criteria atom is draft or approved", text)
        self.assertIn("user-conversation criteria that must be recorded in the criteria atom", text)
        self.assertIn("source exploration results that update the criteria atom", text)
        self.assertIn("judgment labels for review findings", text)
        self.assertIn("matches_confirmed_intent", text)
        self.assertIn("unapproved_implemented_behavior", text)
        self.assertIn("out_of_scope_behavior", text)

    def test_refresh_flow_rejects_generic_or_absence_based_judgment(self) -> None:
        text = read(DOCS_REFS / "refresh-flow.md")
        self.assertIn("Inferred `Intent` or inferred `Rules` alone cannot create confirmed required behavior", text)
        self.assertIn("use `confirmation_needed`", text)
        self.assertIn("Do not write a generic gap", text)
        self.assertIn("missing required behavior, unapproved implementation, out-of-scope behavior, stale docs", text)
        self.assertIn("Do not classify behavior as healthy only because no related gap exists", text)

    def test_atomicity_policy_rejects_vague_split_gap(self) -> None:
        text = read(DOCS_REFS / "atomic-document-contract.md")
        self.assertIn("Do not write a vague split gap", text)
        for required in [
            "candidate atom slugs",
            "owning domain",
            "source files/classes/functions",
            "the split criterion",
            "each candidate atom's behavior/state/rule responsibility",
            "unresolved questions",
        ]:
            self.assertIn(required, text)

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
        self.assertIn("may only target existing atom files", text)
        self.assertIn("existing target `*-atom.md` file", text)
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
        self.assertIn("Stageflow plan approval alone is not docs-submodule approval", text)
        self.assertIn("names the affected docs paths and write actions", text)
        self.assertIn("Gaps", text)
        self.assertIn("Use a Stageflow artifact as required behavior evidence only when", text)
        self.assertIn("approved definition", text)
        self.assertIn("approved implementation plan", text)
        self.assertIn("Draft artifacts, workflow notes, review comments, pending plans", text)
        self.assertIn("not confirmed requirements", text)
        self.assertIn("move the confirmed implemented behavior from `Planned Changes` to `Current Implementation`", text)
        self.assertIn("judgment label from `change-judgment-policy.md`", text)


if __name__ == "__main__":
    unittest.main()
