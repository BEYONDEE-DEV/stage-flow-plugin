from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_atomic_docs.py"


class AtomicDocsValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.docs = self.root / "docs"
        (self.root / ".stageflow").mkdir()
        (self.docs / "project").mkdir(parents=True)
        (self.docs / "project" / "atomization-criteria.md").write_text(
            "# 문서 작성 기준\n", encoding="utf-8"
        )
        (self.root / ".stageflow" / "atomic-docs.json").write_text(
            json.dumps(
                {
                    "storage_mode": "repository",
                    "docs_root": "docs",
                    "source_root": ".",
                    "baseline_metadata_path": "source-baseline.json",
                }
            ),
            encoding="utf-8",
        )
        self._git("init")
        self._git("config", "user.email", "atomic-docs@example.com")
        self._git("config", "user.name", "Atomic Docs Test")
        (self.root / "source.txt").write_text("source\n", encoding="utf-8")
        self._git("add", "source.txt")
        self._git("commit", "-m", "source baseline")
        self.commit = self._git("rev-parse", "HEAD").stdout.strip()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def run_validator(
        self, phase: str, *expected_atom_keys: str
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(VALIDATOR),
            "--root",
            str(self.root),
            "--phase",
            phase,
        ]
        for atom_key in expected_atom_keys:
            command.extend(["--expect-atom-key", atom_key])
        return subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def write_atom(
        self,
        rel_path: str,
        atom_key: str,
        *,
        aid_key: str | None = None,
        edges: list[dict[str, str]] | None = None,
        omit_section: str | None = None,
    ) -> Path:
        path = self.docs / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        prefix = aid_key or atom_key
        frontmatter = ["---", f"atom_key: {atom_key}"]
        if edges:
            frontmatter.append("graph_edges:")
            for edge in edges:
                frontmatter.append(f"  - type: {edge['type']}")
                frontmatter.append(f"    target_key: {edge['target_key']}")
                frontmatter.append(f"    target_path: {edge['target_path']}")
                frontmatter.append(f"    reason: {edge['reason']}")
        else:
            frontmatter.append("graph_edges: []")
        frontmatter.append("---")
        sections = [
            ("Intent", "intent", "의도"),
            ("Rules", "rules", "규칙"),
            ("Current Implementation", "impl", "현재 동작"),
            ("Planned Changes", "plan", "계획"),
            ("Gaps", "gap", "차이"),
        ]
        body: list[str] = []
        for heading, code, prose in sections:
            if heading == omit_section:
                continue
            body.extend(["", f"## {heading}", "", f"- [AID:{prefix}.{code}.001] {prose}"])
        path.write_text("\n".join(frontmatter + body) + "\n", encoding="utf-8")
        return path

    def write_baseline(self, coverage: str = "project-wide") -> None:
        (self.docs / "source-baseline.json").write_text(
            json.dumps(
                {
                    "version": "1",
                    "source_commit": self.commit,
                    "coverage": coverage,
                }
            ),
            encoding="utf-8",
        )

    def test_bootstrap_passes_without_atoms_or_baseline(self) -> None:
        result = self.run_validator("bootstrap")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("PASS bootstrap", result.stdout)

    def test_docs_and_project_wide_baseline_pass(self) -> None:
        self.write_atom("domain/example-atom.md", "example")
        docs_result = self.run_validator("docs")
        self.assertEqual(0, docs_result.returncode, docs_result.stdout + docs_result.stderr)
        self.assertIn("1 atoms", docs_result.stdout)
        self.assertIn("5 AIDs", docs_result.stdout)

        self.write_baseline()
        baseline_result = self.run_validator("baseline")
        self.assertEqual(0, baseline_result.returncode, baseline_result.stdout + baseline_result.stderr)
        self.assertIn("PASS baseline", baseline_result.stdout)

    def test_duplicate_atom_key_and_aid_fail(self) -> None:
        self.write_atom("domain/first-atom.md", "duplicate")
        self.write_atom("domain/second-atom.md", "duplicate")
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("duplicate atom_key `duplicate`", result.stdout)
        self.assertIn("duplicate AID `[AID:duplicate.intent.001]`", result.stdout)

    def test_duplicate_aid_across_different_atoms_fails(self) -> None:
        self.write_atom("domain/first-atom.md", "first", aid_key="shared-origin")
        self.write_atom("domain/second-atom.md", "second", aid_key="shared-origin")
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("duplicate AID `[AID:shared-origin.intent.001]`", result.stdout)

    def test_missing_required_section_fails(self) -> None:
        self.write_atom("domain/example-atom.md", "example", omit_section="Gaps")
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("must contain exactly one `## Gaps` section", result.stdout)

    def test_graph_target_must_exist_and_match_key(self) -> None:
        self.write_atom("domain/target-atom.md", "target")
        self.write_atom("domain/other-atom.md", "other")
        source = self.write_atom(
            "domain/source-atom.md",
            "source",
            edges=[
                {
                    "type": "depends_on",
                    "target_key": "target",
                    "target_path": "domain/other-atom.md",
                    "reason": "계약을 사용한다.",
                }
            ],
        )
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("resolve to different atoms", result.stdout)

        text = source.read_text(encoding="utf-8").replace(
            "target_path: domain/other-atom.md", "target_path: domain/missing-atom.md"
        )
        source.write_text(text, encoding="utf-8")
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("does not exist", result.stdout)

    def test_partial_baseline_is_rejected(self) -> None:
        self.write_atom("domain/example-atom.md", "example")
        self.write_baseline("partial")
        result = self.run_validator("baseline")
        self.assertEqual(1, result.returncode)
        self.assertIn("partial baselines are invalid", result.stdout)

    def test_moved_meaning_may_keep_historical_aid_prefix(self) -> None:
        self.write_atom("domain/new-owner-atom.md", "new-owner", aid_key="original-owner")
        result = self.run_validator("docs")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_aid_section_code_must_match_containing_section(self) -> None:
        path = self.write_atom("domain/example-atom.md", "example")
        text = path.read_text(encoding="utf-8").replace(
            "[AID:example.intent.001]", "[AID:example.gap.001]"
        )
        path.write_text(text, encoding="utf-8")
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("belongs under `## Gaps`, not `Intent`", result.stdout)

    def test_config_paths_cannot_escape_project(self) -> None:
        config_path = self.root / ".stageflow" / "atomic-docs.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        data["docs_root"] = "../outside"
        config_path.write_text(json.dumps(data), encoding="utf-8")
        result = self.run_validator("bootstrap")
        self.assertEqual(1, result.returncode)
        self.assertIn("`docs_root` must be a safe relative path", result.stdout)

    def test_standard_yaml_frontmatter_is_parsed(self) -> None:
        target = self.write_atom("domain/target-atom.md", "target")
        source = self.write_atom("domain/source-atom.md", "source")
        text = source.read_text(encoding="utf-8").replace(
            "atom_key: source\ngraph_edges: []",
            "atom_key: 'source'\n"
            "title: \"Source: contract\"\n"
            "graph_edges:\n"
            "  - type: depends_on\n"
            "    target_key: target\n"
            "    target_path: domain/target-atom.md\n"
            "    reason: \"Uses target: contract\"",
        )
        source.write_text(text, encoding="utf-8")

        result = self.run_validator("docs", "source", "target")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertTrue(target.is_file())

    def test_invalid_or_duplicate_yaml_frontmatter_fails(self) -> None:
        path = self.write_atom("domain/example-atom.md", "example")
        text = path.read_text(encoding="utf-8").replace(
            "atom_key: example", "atom_key: example\natom_key: duplicate"
        )
        path.write_text(text, encoding="utf-8")
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("invalid YAML frontmatter", result.stdout)
        self.assertIn("duplicate key", result.stdout)

    def test_bundle_expected_atom_keys_must_exist(self) -> None:
        self.write_atom("domain/example-atom.md", "example")

        result = self.run_validator("docs", "example", "missing-owner")
        self.assertEqual(1, result.returncode)
        self.assertIn("expected atom key `missing-owner` does not exist", result.stdout)

    def test_bundle_scope_ignores_unrelated_structure_but_full_docs_does_not(self) -> None:
        self.write_atom("domain/active-atom.md", "active")
        self.write_atom("other/broken-atom.md", "broken", omit_section="Gaps")

        scoped = self.run_validator("docs", "active")
        self.assertEqual(0, scoped.returncode, scoped.stdout + scoped.stderr)
        self.assertIn("1 scoped atoms", scoped.stdout)

        full = self.run_validator("docs")
        self.assertEqual(1, full.returncode)
        self.assertIn("`docs/other/broken-atom.md` must contain exactly one `## Gaps`", full.stdout)

    def test_bundle_scope_still_checks_global_aid_collisions(self) -> None:
        self.write_atom("domain/active-atom.md", "active", aid_key="shared-origin")
        self.write_atom("other/other-atom.md", "other", aid_key="shared-origin")

        result = self.run_validator("docs", "active")
        self.assertEqual(1, result.returncode)
        self.assertIn("duplicate AID `[AID:shared-origin.intent.001]`", result.stdout)

    def test_expected_atom_key_requires_docs_phase(self) -> None:
        result = self.run_validator("bootstrap", "example")
        self.assertEqual(1, result.returncode)
        self.assertIn("requires `--phase docs`", result.stdout)

        self.write_atom("domain/example-atom.md", "example")
        self.write_baseline()
        result = self.run_validator("baseline", "example")
        self.assertEqual(1, result.returncode)
        self.assertIn("requires `--phase docs`", result.stdout)


if __name__ == "__main__":
    unittest.main()
