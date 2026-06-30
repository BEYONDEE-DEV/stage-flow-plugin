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
        self.assertIn("stale installed cache path", text)
        self.assertIn("fresh cachebuster", text)
        self.assertIn("service logic as natural-language source-of-truth docs", text)
        self.assertIn("meaningful service logic in natural language", text)
        self.assertIn("endpoint lists, controller summaries, service class summaries", text)
        self.assertIn("not as the docs themselves or direct code suitability evidence", text)
        self.assertIn("domain partitioning criteria and a candidate or approved domain map", text)

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
        self.assertIn("Korean-First Template Policy", text)
        self.assertIn("Korean-first writing templates", text)
        self.assertIn("Do not draft an English skeleton first and then translate it into Korean", text)
        for korean_subheading in [
            "### 동작 흐름",
            "### 관찰된 판단 규칙",
            "### 상태와 저장 효과",
            "### 외부 연동과 이벤트",
            "### 실패와 복구 동작",
            "### Source Evidence",
        ]:
            self.assertIn(korean_subheading, text)
        self.assertIn("translated English", text)
        self.assertIn("English-first scaffold", text)
        self.assertIn("No Example Leakage", text)
        self.assertIn("Do not copy reference example wording", text)
        self.assertIn("Controlled judgment labels, fixed headings, schema keys", text)
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
        self.assertIn("explicitly selects a managed docs root and asks to start, redo, or recreate atomic docs", text)
        self.assertIn("paired draft criteria document allowed by `refresh-flow.md`", text)

    def test_docs_skill_requires_write_approval_for_managed_state(self) -> None:
        text = read(DOCS_SKILL)
        self.assertIn("accepted the explicit docs operation scope and change plan", text)
        self.assertIn("limited draft write action", text)
        self.assertIn("accepted bootstrap scope", text)
        self.assertIn("project/atomization-criteria.md", text)
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
        self.assertIn("criteria-review/revision cycles until the criteria draft has no blocking structure issues", text)
        self.assertIn("run an independent criteria-review subagent", text)
        self.assertIn("revise `project/atomization-criteria.md` until the reviewer reports no blocking issues", text)
        self.assertIn("criteria document itself as the center of user revision and approval after criteria-review PASS", text)
        self.assertIn("Do not start domain atom writing or domain writer/reviewer subagent work until the criteria document is approved", text)
        self.assertIn("Use only an approved criteria document as required input", text)
        self.assertIn("Do not require a Codex Goal for bootstrap criteria draft creation or criteria-review subagents", text)
        self.assertIn("current request already accepted bootstrap scope", text)
        self.assertIn("After criteria approval and accepted docs write scope", text)
        self.assertIn("create or reuse a Codex Goal before starting docs generation work", text)

    def test_atomic_document_contract_sections_and_boundaries(self) -> None:
        text = read(DOCS_REFS / "atomic-document-contract.md")
        self.assertIn("<doc-root>/<domain>/<atomic-target>-atom.md", text)
        self.assertIn("<doc-root>/project/atomization-criteria.md", text)
        self.assertIn("criteria document is not an atom", text)
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
        self.assertIn("Explanatory prose in this file is not reusable managed-docs content", text)

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

    def test_atomization_criteria_document_contract_is_persisted(self) -> None:
        text = read(DOCS_REFS / "atomic-document-contract.md")
        self.assertIn("Atomization Criteria Document", text)
        self.assertIn("<doc-root>/project/atomization-criteria.md", text)
        self.assertIn("Existing `<doc-root>/project/atomization-criteria-atom.md` files are legacy artifacts", text)
        self.assertIn("first atomic-docs write action", text)
        self.assertIn("draft criteria document is a review artifact", text)
        self.assertIn("Approval Status: draft, pending user approval", text)
        self.assertIn("Approval Status: approved by user", text)
        self.assertIn("must not be used as the required input for domain writer subagents", text)
        self.assertIn("Record user-conversation criteria in the draft before code exploration", text)
        self.assertIn("do not copy illustrative wording from skill references", text)
        self.assertIn("must not follow the `*-atom.md` path contract", text)
        self.assertIn("required atom sections `Intent`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps`", text)
        for section in [
            "Purpose",
            "Approval Status",
            "Managed Docs Root And Scope",
            "Domain Partitioning Criteria",
            "Candidate / Approved Domain Map",
            "Atomization Perspectives",
            "Service Logic Coverage Requirements",
            "Writer Subagent Instructions",
            "Reviewer Subagent Instructions",
            "Judgment Policy Usage",
            "Open Questions And Approval Blockers",
        ]:
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
            "Atom candidate criteria",
            "Source evidence only criteria",
            "Not applicable reason",
            "Split/merge criteria",
            "Source evidence requirement",
            "Unresolved questions",
        ]:
            self.assertIn(required_detail, text)
        self.assertIn("every entry under `Atomization Perspectives` with these exact subfields", text)
        self.assertIn("Do not accept one-line perspective summaries", text)
        self.assertIn("missing one of the required subfields", text)
        self.assertIn("empty or placeholder-only", text)
        self.assertIn("concrete `Not applicable reason` or `Unresolved questions`", text)
        for domain_detail in [
            "domain partitioning criteria",
            "candidate or approved domain map",
            "domain name",
            "owned behavior",
            "excluded behavior",
            "adjacent domain boundary",
            "why the atoms in that domain change together",
            "approval state",
            "`candidate`, `approved`, `rejected`, and `needs_confirmation`",
        ]:
            self.assertIn(domain_detail, text)
        self.assertIn("writer subagent and review subagent checklists", text)
        self.assertIn("not fixed document types", text)
        self.assertIn("Do not accept a criteria document that only lists perspective names or domain names", text)
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
        self.assertIn("one judgment label from `change-judgment-policy.md`", text)
        self.assertIn("Do not add top-level per-atom status fields", text)
        self.assertIn("lack of a `Gaps` item", text)
        self.assertIn("non-goals, excluded behavior, and adjacent-domain boundaries", text)

    def test_atomic_document_contract_requires_service_logic_natural_language_coverage(self) -> None:
        text = read(DOCS_REFS / "atomic-document-contract.md")
        self.assertIn("Service Logic Natural-Language Coverage", text)
        self.assertIn("natural-language service logic standard", text)
        self.assertIn("meaningful application, service, and domain logic", text)
        for required_behavior in [
            "conditions",
            "branches",
            "state transitions",
            "validation",
            "permission checks",
            "policy rules",
            "transaction or idempotency behavior",
            "persistence side effects",
            "external calls",
            "emitted events",
            "error handling",
            "recovery behavior",
        ]:
            self.assertIn(required_behavior, text)
        self.assertIn("endpoint lists, controller lists, service class names, method names", text)
        self.assertIn("source evidence only until the atom explains in natural language", text)
        self.assertIn("A bare list of source identifiers, endpoints, controllers, service classes, or methods is not sufficient", text)
        for korean_subheading in [
            "### 동작 흐름",
            "### 관찰된 판단 규칙",
            "### 상태와 저장 효과",
            "### 외부 연동과 이벤트",
            "### 실패와 복구 동작",
            "### Source Evidence",
        ]:
            self.assertIn(korean_subheading, text)
        self.assertIn("input conditions, branches or refusals, state changes, stored or external effects, and failure results", text)
        self.assertIn("translated English skeleton", text)
        self.assertIn("method-call sequence", text)
        self.assertIn("service logic coverage gaps", text)

    def test_atomic_document_contract_separates_goal_scope_from_judgment_evidence(self) -> None:
        text = read(DOCS_REFS / "atomic-document-contract.md")
        self.assertIn("Atomic Docs Goal Boundary", text)
        self.assertIn("execution scope for performing the accepted docs operation", text)
        self.assertIn("does not replace criteria approval, accepted docs write scope", text)
        self.assertIn("judgment labels, source evidence, user review, or source-baseline metadata", text)
        self.assertIn("Do not write Goal status or Goal completion as atom-level status", text)
        self.assertIn("Code suitability judgments still come from approved criteria, generated atoms, source evidence", text)

    def test_atomic_document_contract_rejects_evasive_split_or_identifier_only_coverage(self) -> None:
        text = read(DOCS_REFS / "atomic-document-contract.md")
        self.assertIn("Do not leave an evasive split or coverage gap", text)
        self.assertIn("in place of documenting inspected service logic", text)
        self.assertIn("proposed owners, unresolved question, and the behavior already observed", text)
        self.assertIn("Do not use source identifiers without natural-language behavior as proof", text)

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
        self.assertIn("Do not document a derived concept while its parent business term is missing or underdefined", text)
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
        self.assertIn("Update the docs-root source commit baseline metadata only after confirmed docs writes", text)
        self.assertIn("core business terms that require glossary or domain atom coverage", text)
        self.assertIn("parent business terms missing or underdefined in the glossary", text)
        self.assertIn("Build a service logic inventory", text)
        self.assertIn("service logic inventory items", text)
        self.assertIn("accepted change plan defines the only paths and write actions", text)
        self.assertIn("Do not write atom files, graph corrections, source-baseline metadata", text)

    def test_refresh_flow_creates_draft_criteria_before_subagents(self) -> None:
        text = read(DOCS_REFS / "refresh-flow.md")
        self.assertIn("Atomization Criteria File-First Flow", text)
        self.assertIn("Atomization Perspectives Reviewed", text)
        self.assertIn("project/atomization-criteria.md", text)
        self.assertIn("legacy `<doc-root>/project/atomization-criteria-atom.md` exists", text)
        self.assertIn("first atomic-docs write action", text)
        self.assertIn("limited draft creation or update", text)
        self.assertIn("draft criteria write action", text)
        self.assertIn("docs root config write when needed", text)
        self.assertIn("current user request explicitly asks to start, redo, regenerate, or recreate atomic docs", text)
        self.assertIn("do not stop at an approval request", text)
        self.assertIn("then run the Criteria Structure Review Gate and stop for user review only after criteria-review PASS", text)
        self.assertIn("must not also create project goal, project glossary, common context, common policy atoms, domain atoms", text)
        self.assertIn("domain writer/reviewer subagent work, service logic inventory, or source baseline metadata", text)
        self.assertIn("record criteria already stated in the user conversation", text)
        self.assertIn("use code exploration to enrich the criteria document itself", text)
        self.assertIn("not just the change plan", text)
        self.assertIn("Criteria Structure Review Gate", text)
        self.assertIn("Before asking the user to approve the criteria document, satisfy the Criteria Structure Review Gate", text)
        self.assertIn("Use an independent criteria-review subagent", text)
        self.assertIn("allowed before criteria approval and does not require a Codex Goal", text)
        self.assertIn("any `Atomization Perspectives` entry is missing one of the required subfields", text)
        self.assertIn("empty, placeholder-only, or a one-line summary", text)
        self.assertIn("the domain map is missing, source-unsupported", text)
        self.assertIn("unapproved destructive claims about legacy artifacts", text)
        self.assertIn("revise only `project/atomization-criteria.md`", text)
        self.assertIn("rerun the criteria-review subagent", text)
        self.assertIn("reports no blocking issues", text)
        self.assertIn("ready for user review and possible approval", text)
        self.assertIn("does not approve the criteria automatically", text)
        self.assertIn("draft review artifact", text)
        self.assertIn("must not be used as the required input for domain writer subagents", text)
        self.assertIn("candidate names as confirmed domain structure before criteria approval", text)
        self.assertIn("domain partitioning criteria", text)
        self.assertIn("candidate or approved domain map", text)
        self.assertIn("Domain Subagent Workflow", text)
        self.assertIn("only after the criteria document is approved", text)
        self.assertIn("Each writer subagent must read the approved criteria document", text)
        self.assertIn("service logic inventory plus a judgment-labeled domain evidence packet", text)
        self.assertIn("judgment-labeled domain evidence packet", text)
        self.assertIn("change-judgment-policy.md", text)
        self.assertIn("No Example Leakage rule", text)
        self.assertIn("the domain map is missing or unsupported", text)
        self.assertIn("meaningful source behavior is missing from the inventory", text)
        self.assertIn("source identifiers appear without natural-language behavior", text)
        self.assertIn("reference example prose appears without user/source trace", text)
        self.assertIn("Korean-first templates", text)
        self.assertIn("Do not produce an English skeleton and translate it afterward", text)
        self.assertIn("Korean docs retain English template residue", text)
        self.assertIn("translated-English phrasing", text)
        self.assertIn("English placeholders", text)
        self.assertIn("method-call-sequence-only `Current Implementation`", text)
        self.assertIn("cannot explain the implemented behavior from the docs alone", text)
        self.assertIn("cannot be used as code judgment criteria", text)
        self.assertIn("judgment labels are absent or unsupported", text)
        self.assertIn("missing required behavior is confused with out-of-scope behavior", text)
        self.assertIn("candidate domains are treated as confirmed without approval", text)
        self.assertIn("independent review subagents", text)
        self.assertIn("review subagent fails", text)
        self.assertIn("rerun review", text)

    def test_refresh_flow_requires_goal_after_criteria_approval_before_docs_generation(self) -> None:
        text = read(DOCS_REFS / "refresh-flow.md")
        self.assertIn("Atomic Docs Goal Gate", text)
        self.assertIn("Bootstrap criteria draft creation and the Criteria Structure Review Gate do not require a Codex Goal", text)
        self.assertIn("run criteria-review/revision cycles for that criteria draft", text)
        self.assertIn("then stop for user review after criteria-review PASS", text)
        self.assertIn("After the criteria document is approved and the user accepts a docs write scope, call Codex `create_goal`", text)
        for blocked_work in [
            "project, common, or domain atom writing",
            "service logic inventory creation",
            "domain writer or reviewer subagent execution",
            "graph edge writing",
            "source-baseline metadata updates",
        ]:
            self.assertIn(blocked_work, text)
        for objective_part in [
            "approved criteria document path",
            "docs root",
            "accepted docs write scope",
            "natural-language service logic coverage requirement",
            "writer/reviewer cycle",
            "completion condition",
        ]:
            self.assertIn(objective_part, text)
        self.assertIn("If `create_goal` is unavailable or fails, do not start docs generation", text)
        self.assertIn("domain writer/reviewer subagents", text)
        self.assertIn("Complete the Goal only after the accepted docs operation is actually complete", text)
        self.assertIn("waiting for user input, blocked by review FAIL", text)
        self.assertIn("Atomic Docs Goal Gate status", text)

    def test_refresh_flow_requires_service_logic_inventory_and_atom_mapping(self) -> None:
        text = read(DOCS_REFS / "refresh-flow.md")
        self.assertIn("Service Logic Inventory", text)
        self.assertIn("behavior-oriented, not method-oriented", text)
        self.assertIn("meaningful runtime behavior rather than by endpoint, controller, service class, method, or file", text)
        for inventory_field in [
            "inspected source identifiers",
            "natural-language behavior",
            "conditions and branches",
            "validation or permission checks",
            "state transitions",
            "persistence side effects",
            "integration calls",
            "emitted events",
            "error handling",
            "recovery behavior",
            "candidate owning atom",
        ]:
            self.assertIn(inventory_field, text)
        self.assertIn("Map every meaningful application, service, and domain logic item to an owning atom", text)
        self.assertIn("record a coverage gap with source evidence and `confirmation_needed`", text)
        self.assertIn("only lists source files, endpoints, controllers, service classes, or method names", text)

    def test_refresh_flow_requires_criteria_change_plan_entries(self) -> None:
        text = read(DOCS_REFS / "refresh-flow.md")
        self.assertIn("limited first write action for draft criteria creation or update", text)
        self.assertIn("whether the criteria document is draft or approved", text)
        self.assertIn("user-conversation criteria that must be recorded in the criteria document", text)
        self.assertIn("source exploration results that update the criteria document", text)
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
        self.assertIn("Source behavior absent from the docs is not implicitly correct", text)
        self.assertIn("coverage gap, `confirmation_needed`, or `docs_stale`", text)

    def test_change_judgment_policy_requires_natural_language_docs_for_matching(self) -> None:
        text = read(DOCS_REFS / "change-judgment-policy.md")
        self.assertIn("natural-language behavior with source evidence", text)
        self.assertIn("source identifier, endpoint list, controller list, service class summary, method name", text)
        self.assertIn("service logic is absent from natural-language docs", text)
        self.assertIn("do not classify it as matching", text)
        self.assertIn("Record a coverage gap or `confirmation_needed`", text)

    def test_docs_skill_prevents_reference_example_leakage(self) -> None:
        combined = "\n".join(
            read(path)
            for path in [
                DOCS_REFS / "atomic-document-contract.md",
                DOCS_REFS / "refresh-flow.md",
                DOCS_REFS / "change-judgment-policy.md",
            ]
        )
        self.assertNotIn("endpoint-based document structure", combined)
        self.assertNotIn("vague service state-transition split gaps", combined)
        self.assertNotIn("resource deduction", combined)
        self.assertNotIn("this service's detailed state transitions should be split into separate atoms", combined)
        self.assertIn("Do not copy reference example wording", read(DOCS_REFS / "language-policy.md"))

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
        self.assertIn("criteria document at `project/atomization-criteria.md` is not an atom file", text)
        self.assertIn("must not be used as a `graph_edges` source or target", text)
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
