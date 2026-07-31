from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "atomic-docs" / "SKILL.md"
REFS = ROOT / "skills" / "atomic-docs" / "references"
OPENAI = ROOT / "skills" / "atomic-docs" / "agents" / "openai.yaml"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class AtomicDocsSkillTests(unittest.TestCase):
    def test_changed_scope_fixture_observes_seed_one_hop_and_unmapped_boundaries(self) -> None:
        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "atomic-docs-changed-scope.json").read_text(
                encoding="utf-8"
            )
        )
        changed = set(fixture["changed_files"])
        atoms = fixture["atoms"]
        seeds = {
            atom["atom_key"]
            for atom in atoms
            if changed.intersection(atom["source_files"])
        }
        forward = {
            dependency
            for atom in atoms
            if atom["atom_key"] in seeds
            for dependency in atom["depends_on"]
        }
        reverse = {
            atom["atom_key"]
            for atom in atoms
            if seeds.intersection(atom["depends_on"])
        }
        mapped_files = {
            source
            for atom in atoms
            for source in atom["source_files"]
            if atom["atom_key"] in seeds
        }
        actual = {
            "seed_atoms": sorted(seeds),
            "adjacent_atoms": sorted((forward | reverse) - seeds),
            "unmapped_changed_files": sorted(changed - mapped_files),
            "uninspected_atoms": sorted(
                atom["atom_key"]
                for atom in atoms
                if atom["atom_key"] not in seeds | forward | reverse
            ),
        }
        self.assertEqual(actual, fixture["expected"])

    def test_skill_exposes_only_minimal_permanent_outputs(self) -> None:
        text = read(SKILL)
        for required in (
            ".stageflow/atomic-docs.json",
            "project/project-goal.md",
            "project/project-glossary.md",
            "<docs-root>/<domain>/*-atom.md",
            "Do not create any other permanent Atomic Docs output",
            "does not create a Goal",
        ):
            self.assertIn(required, text)

    def test_atom_contract_is_exact(self) -> None:
        text = read(REFS / "atomic-document-contract.md")
        for required in (
            "atom_key",
            "depends_on",
            "`Purpose`",
            "`Boundaries`",
            "`Contracts`",
            "`Implementation`",
            "`Sources`",
            "`Changes`",
            "`Open Questions`",
            "`- 없음`",
            "[RID:<atom_key>.<lower-kebab-slug>]",
            "There is no RID reference token",
        ):
            self.assertIn(required, text)
        for legacy in ("Intent", "Outcomes", "Current Implementation", "Planned Changes", "Gaps"):
            self.assertNotIn(f"`{legacy}`", text)

    def test_glossary_contract_is_a_general_project_dictionary(self) -> None:
        skill = read(SKILL)
        contract = read(REFS / "atomic-document-contract.md")
        validation = read(REFS / "validation-contract.md")
        for required in (
            "general project glossary",
            "a new developer must understand",
            "even when a term belongs to only one Atom",
            "Use only `Term` and `Definition`",
            "without adding ownership, source, evidence, or control columns",
            "do not invent artificial terms",
        ):
            self.assertIn(required, skill)
        for required in (
            "This is a general project glossary",
            "| Term | Definition |",
            "Terms owned by one Atom still qualify",
            "user roles and actors",
            "core domain entities",
            "business actions, workflows, states, and results",
            "project-specific identifiers, acronyms, aliases",
            "a concise, non-circular explanation",
            "do not invent artificial names",
            "Do not put source locators, ownership metadata, source-of-truth claims, or review evidence",
        ):
            self.assertIn(required, contract)
        glossary_section = contract.split("## Project Glossary", 1)[1].split("## Atom", 1)[0]
        for retired_column in (
            "| Term | Meaning | Scope Or Owner |",
            "`Scope Or Owner`",
            "`Source Of Truth`",
            "`Do Not Confuse With`",
        ):
            self.assertNotIn(retired_column, glossary_section)
        self.assertNotIn("At least two Atom responsibilities", glossary_section)
        self.assertIn("unique non-empty `Term` and `Definition` cells", validation)
        self.assertIn("glossary coverage or definition accuracy", validation)

    def test_writer_and_reviewer_share_minimal_decision_contract(self) -> None:
        skill = read(SKILL)
        contract = read(REFS / "atomic-document-contract.md")
        flow = read(REFS / "refresh-flow.md")
        reviewer = read(REFS / "reviewer-perspectives.md")
        skill_flat = " ".join(skill.split())
        contract_flat = " ".join(contract.split())
        flow_flat = " ".join(flow.split())
        reviewer_flat = " ".join(reviewer.split())

        for required in (
            "project-level outcomes observable by the intended human or system consumers",
            "natural owning Atom",
            "must survive an implementation change",
            "domain-specific result or additional condition",
            "Do not create a shared Atom solely to deduplicate mechanics",
        ):
            self.assertIn(required, skill_flat)

        for required in (
            "project-level outcomes observable by the intended human or system consumers",
            "Do not assume every project has a human UI",
            "must survive a change of implementation",
            "natural Atom that owns the rule",
            "domain-specific consequence or additional condition",
            "Classify content by meaning, not vocabulary",
            "put it in `Implementation` or omit it",
        ):
            self.assertIn(required, contract_flat)

        for required in (
            "selected and directly inspected scope",
            "instead of expanding automatically",
            "project-level observable outcomes",
            "natural Atom owner without inventing a shared hub",
            "Separate contracts that must survive implementation changes",
            "Remove copied generic mechanics",
        ):
            self.assertIn(required, flow_flat)

        for required in (
            "Return `FAIL` when a material project `Success` statement",
            "generic rule with a natural owning Atom is materially copied",
            "`Contracts` contains current mechanics",
            "Do not require an artificial shared Atom",
            "domain-specific consequence or additional condition",
            "reject an item merely because it mentions a route",
            "whether another consumer can observe or rely on it",
        ):
            self.assertIn(required, reviewer_flat)

    def test_config_is_exact_v2_without_baseline_artifact(self) -> None:
        text = read(REFS / "docs-root-and-config.md")
        for required in (
            '"version": 2',
            '"storage_mode"',
            '"docs_root"',
            '"source_root"',
            '"language"',
            '"last_full_source_commit": null',
            '"auxiliary_sources"',
            "All seven top-level keys are required",
            "Do not add a separate baseline file",
            "below the Git top level",
        ):
            self.assertIn(required, text)

    def test_operations_are_small_and_changed_scope_is_one_hop(self) -> None:
        skill = read(SKILL)
        flow = read(REFS / "refresh-flow.md")
        for required in (
            "`inspect`",
            "`update all`",
            "`update changed`",
            "`update targeted`",
            "direct `depends_on`",
            "direct reverse dependents",
            "Never claim complete transitive closure",
        ):
            self.assertIn(required, skill)
        for required in (
            "seed Atoms",
            "direct dependency and reverse-dependent Atom keys",
            "boundaries not inspected",
            "not proof of complete closure",
        ):
            self.assertIn(required, flow)

    def test_single_bounded_reviewer_has_one_correction(self) -> None:
        text = read(REFS / "reviewer-perspectives.md")
        for required in (
            "one independent semantic reviewer",
            "complete managed-docs diff",
            "development",
            "faithful",
            "`Boundaries`",
            "`depends_on`",
            "corrects the findings once",
            "same reviewer",
            "stop and ask the user",
            "Run structural validation on the corrected docs",
            "final reviewed docs",
        ):
            self.assertIn(required, text)
        self.assertIn("Do not add another reviewer, audit, challenge", text)
        self.assertIn("Do not persist review metadata or state", text)
        for required in (
            "project goal and the selected Atom/source scope",
            "needed by a new developer is omitted",
            "circular, vague, source-symbol-only",
            "artificial terms are invented",
            "does not need cross-Atom use",
            "contains only `Term` and `Definition`",
        ):
            self.assertIn(required, text)

    def test_existing_delete_or_merge_needs_exact_key_approval(self) -> None:
        text = read(SKILL) + read(REFS / "refresh-flow.md")
        self.assertIn("exact source and target `atom_key` list", text)
        self.assertIn("explicit user approval", text)
        self.assertIn("Use Git for recovery", text)
        self.assertIn("create no separate recovery artifact", text)

    def test_reference_surface_is_exactly_seven_files(self) -> None:
        expected = {
            "atomic-document-contract.md",
            "docs-root-and-config.md",
            "language-policy.md",
            "refresh-flow.md",
            "reviewer-perspectives.md",
            "stageflow-integration.md",
            "validation-contract.md",
        }
        self.assertEqual({path.name for path in REFS.glob("*.md")}, expected)

    def test_retired_control_vocabulary_is_not_an_active_contract(self) -> None:
        text = "\n".join(read(path) for path in [SKILL, *sorted(REFS.glob("*.md"))])
        for retired in (
            "context_selection.version",
            "acceptance fingerprint",
            "basis revision",
            "semantic closure",
            "persistent reviewer",
            "blind terminal challenger",
            "operation-events.jsonl",
            "source-baseline.json",
            "[AID-REF:",
        ):
            self.assertNotIn(retired, text)

    def test_metadata_and_manifest_describe_new_commands(self) -> None:
        metadata = read(OPENAI)
        manifest = json.loads(read(ROOT / ".codex-plugin" / "plugin.json"))
        self.assertIn('display_name: "Atomic Docs"', metadata)
        self.assertIn("inspect or update purpose, boundaries, contracts", metadata)
        prompts = manifest["interface"]["defaultPrompt"]
        self.assertIn("Use atomic-docs update all to create source-guided project documentation.", prompts)
        self.assertIn("Use atomic-docs update changed to refresh affected Atom files.", prompts)
        usage = read(ROOT / "USAGE.ko.md")
        self.assertIn("별도 request/work/review operation 디렉터리를 만들지 않습니다", usage)


if __name__ == "__main__":
    unittest.main()
