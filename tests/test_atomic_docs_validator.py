from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_atomic_docs.py"


class AtomicDocsValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="atomic-docs-v2-"))
        (self.tmp / ".stageflow").mkdir()
        (self.tmp / "src").mkdir()
        (self.tmp / "src" / "checkout.py").write_text(
            "def charge():\n    return True\n\ndef refund():\n    return True\n",
            encoding="utf-8",
        )
        (self.tmp / "docs" / "project").mkdir(parents=True)
        (self.tmp / "docs" / "payments").mkdir()
        self.write_config()
        self.write_goal()
        self.write_atom("checkout-payment")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_config(self, **overrides: object) -> None:
        config: dict[str, object] = {
            "version": 2,
            "storage_mode": "repository",
            "docs_root": "docs",
            "source_root": "src",
            "language": "ko",
            "last_full_source_commit": None,
            "auxiliary_sources": [],
        }
        config.update(overrides)
        (self.tmp / ".stageflow" / "atomic-docs.json").write_text(
            json.dumps(config),
            encoding="utf-8",
        )

    def write_goal(self, *, source: str = "primary:checkout.py#charge") -> None:
        (self.tmp / "docs" / "project" / "project-goal.md").write_text(
            f"""# Project Goal

## Purpose

결제를 처리한다.

## Users

구매자와 운영자.

## Success

결제 결과가 일관된다.

## Non-goals

배송은 다루지 않는다.

## Sources

- `{source}`
""",
            encoding="utf-8",
        )

    def atom_text(
        self,
        key: str,
        *,
        depends_on: list[str] | None = None,
        source: str = "primary:checkout.py#charge",
        changes: str = "- 없음",
        questions: str = "- 없음",
    ) -> str:
        if depends_on:
            dependencies = "depends_on:\n" + "\n".join(f"  - {item}" for item in depends_on)
        else:
            dependencies = "depends_on: []"
        return f"""---
atom_key: {key}
{dependencies}
---

# {key}

## Purpose

결제 결과를 소유한다.

## Boundaries

배송을 제외하고 결제만 처리한다.

## Contracts

승인 결과를 호출자에게 반환한다.

## Implementation

checkout 모듈이 진입점이다.

## Sources

- `{source}`

## Changes

{changes}

## Open Questions

{questions}
"""

    def write_atom(self, key: str, **kwargs: object) -> Path:
        path = self.tmp / "docs" / "payments" / f"{key}-atom.md"
        path.write_text(self.atom_text(key, **kwargs), encoding="utf-8")
        return path

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(VALIDATOR), "--root", str(self.tmp)],
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "PYTHONPATH": ""},
        )

    def assert_fails(self, expected: str) -> None:
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(expected, result.stdout)
        self.assertIn("recovery:", result.stdout)

    def test_valid_minimal_docs_pass(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("PASS atomic-docs: atoms=1 sources=1", result.stdout)

    def test_config_requires_exact_v2_schema(self) -> None:
        self.write_config(version="2", source_baseline="legacy")
        self.assert_fails("expected exact keys")
        self.assert_fails("version: must be integer 2")

    def test_project_goal_requires_exact_heading_order(self) -> None:
        goal = self.tmp / "docs" / "project" / "project-goal.md"
        goal.write_text(goal.read_text(encoding="utf-8").replace("## Users", "## Audience"), encoding="utf-8")
        self.assert_fails("expected exact order")

    def test_atom_requires_exact_headings_and_meaningful_required_sections(self) -> None:
        atom = self.tmp / "docs" / "payments" / "checkout-payment-atom.md"
        atom.write_text(atom.read_text(encoding="utf-8").replace("결제 결과를 소유한다.", "- 없음"), encoding="utf-8")
        self.assert_fails("Purpose: `- 없음` is not allowed here")

    def test_empty_changes_and_questions_use_exact_marker(self) -> None:
        atom = self.tmp / "docs" / "payments" / "checkout-payment-atom.md"
        atom.write_text(
            atom.read_text(encoding="utf-8").replace(
                "- 없음",
                "- 없음\n- [RID:checkout-payment.add-rule] 규칙을 추가한다.",
                1,
            ),
            encoding="utf-8",
        )
        self.assert_fails("empty marker must be exact `- 없음`")
        self.write_atom(
            "checkout-payment",
            questions="- 현재 명확한 소유자가 없음 — 결정 필요",
        )
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_source_locator_resolves_configured_source_and_file(self) -> None:
        self.write_atom("checkout-payment", source="unknown:checkout.py#charge")
        self.assert_fails("source name `unknown` is not configured")
        self.write_atom("checkout-payment", source="primary:missing.py#charge")
        self.assert_fails("locator file `missing.py` does not exist")
        self.write_atom("checkout-payment", source="primary:checkout.py#charge:L12-L14")
        self.assert_fails("looks like a line number or range")

    def test_source_locator_accepts_unicode_path_and_heading_symbol(self) -> None:
        (self.tmp / "src" / "결제 흐름.md").write_text("# Payment Approval Flow\n", encoding="utf-8")
        self.write_atom(
            "checkout-payment",
            source="primary:결제 흐름.md#Payment Approval Flow",
        )
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_depends_on_resolves_direct_atom_key(self) -> None:
        self.write_atom("checkout-payment", depends_on=["customer-credit"])
        self.assert_fails("`customer-credit` does not resolve to an Atom")
        self.write_atom("customer-credit", source="primary:checkout.py#refund")
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_empty_depends_on_block_must_use_exact_empty_list(self) -> None:
        atom = self.tmp / "docs" / "payments" / "checkout-payment-atom.md"
        atom.write_text(
            atom.read_text(encoding="utf-8").replace("depends_on: []", "depends_on:"),
            encoding="utf-8",
        )
        self.assert_fails("empty dependencies must use exact `depends_on: []`")

    def test_atom_keys_are_globally_unique(self) -> None:
        duplicate = self.tmp / "docs" / "other"
        duplicate.mkdir()
        (duplicate / "duplicate-atom.md").write_text(self.atom_text("checkout-payment"), encoding="utf-8")
        self.assert_fails("duplicates `checkout-payment`")

    def test_rid_is_exactly_once_in_owning_changes(self) -> None:
        self.write_atom(
            "checkout-payment",
            changes="- [RID:checkout-payment.reject-expired-card] 만료 카드를 거부한다.",
        )
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout)

        self.write_atom(
            "checkout-payment",
            changes="- [RID:customer-credit.reject-expired-card] 만료 카드를 거부한다.",
        )
        self.assert_fails("does not match atom_key `checkout-payment`")

    def test_nonempty_changes_require_one_rid_per_item(self) -> None:
        self.write_atom("checkout-payment", changes="- 만료 카드를 거부한다.")
        self.assert_fails("non-empty active changes require at least one RID")
        self.assert_fails("each top-level change item must contain exactly one RID")

    def test_rid_sentence_may_contain_korean_none_word(self) -> None:
        self.write_atom(
            "checkout-payment",
            changes=(
                "- [RID:checkout-payment.no-duplicate-charge] "
                "중복 청구가 없음을 보장한다."
            ),
        )
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_rid_outside_changes_and_legacy_aid_are_rejected(self) -> None:
        atom = self.tmp / "docs" / "payments" / "checkout-payment-atom.md"
        text = atom.read_text(encoding="utf-8").replace(
            "결제 결과를 소유한다.",
            "[RID:checkout-payment.reject-expired-card] 결제 결과를 소유한다. [AID:legacy]",
        )
        atom.write_text(text, encoding="utf-8")
        self.assert_fails("RID appears outside Changes")
        self.assert_fails("retired AID/AID-REF syntax is present")
        atom.write_text(text.replace("[AID:legacy]", "[RID-REF:legacy]"), encoding="utf-8")
        self.assert_fails("RID reference syntax is not supported")

    def test_project_docs_cannot_hold_aid_or_rid(self) -> None:
        goal = self.tmp / "docs" / "project" / "project-goal.md"
        goal.write_text(
            goal.read_text(encoding="utf-8").replace(
                "결제를 처리한다.",
                "[AID:legacy] [RID:checkout-payment.move-me] 결제를 처리한다.",
            ),
            encoding="utf-8",
        )
        self.assert_fails("retired AID/AID-REF syntax is present")
        self.assert_fails("RID is allowed only in an Atom Changes section")

    def test_optional_glossary_requires_exact_table_and_sources(self) -> None:
        glossary = self.tmp / "docs" / "project" / "project-glossary.md"
        glossary.write_text(
            """# Project Glossary

## Terms

| Term | Meaning | Scope Or Owner | Source Of Truth | Do Not Confuse With | Sources |
| --- | --- | --- | --- | --- | --- |
| 승인 | 결제 승인 | 결제 | checkout | 환불 | `primary:checkout.py#charge` |
""",
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout)
        glossary.write_text(glossary.read_text(encoding="utf-8").replace("| Sources |", "| Evidence |"), encoding="utf-8")
        self.assert_fails("does not match the required columns")

    def test_unapproved_permanent_file_is_rejected(self) -> None:
        (self.tmp / "docs" / "project" / "atomization-criteria.md").write_text("# Legacy\n", encoding="utf-8")
        self.assert_fails("not a supported permanent Atomic Docs output")

    def test_auxiliary_source_uses_unique_name_path_and_reachable_revision(self) -> None:
        auxiliary = self.tmp / "shared"
        package = auxiliary / "package"
        package.mkdir(parents=True)
        (package / "contract.md").write_text("# Contract\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(auxiliary)], check=True)
        subprocess.run(["git", "-C", str(auxiliary), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(auxiliary), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(auxiliary), "add", "package/contract.md"], check=True)
        subprocess.run(["git", "-C", str(auxiliary), "commit", "-qm", "fixture"], check=True)
        revision = subprocess.check_output(
            ["git", "-C", str(auxiliary), "rev-parse", "HEAD"],
            text=True,
        ).strip()
        self.write_config(
            auxiliary_sources=[
                {"name": "shared-contracts", "path": "shared/package", "revision": revision}
            ]
        )
        self.write_atom("checkout-payment", source="shared-contracts:contract.md#Contract")
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout)

        (package / "future.md").write_text("# Future\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(auxiliary), "add", "package/future.md"], check=True)
        subprocess.run(["git", "-C", str(auxiliary), "commit", "-qm", "future"], check=True)
        self.write_atom("checkout-payment", source="shared-contracts:future.md#Future")
        self.assert_fails("is not a file at pinned revision")

        self.write_config(
            auxiliary_sources=[
                {"name": "shared-contracts", "path": "shared/package", "revision": "f" * 40}
            ]
        )
        self.assert_fails("revision is not a reachable commit")

    def test_reachable_baseline_commit_passes_and_unknown_commit_fails(self) -> None:
        subprocess.run(["git", "init", "-q", str(self.tmp / "src")], check=True)
        subprocess.run(["git", "-C", str(self.tmp / "src"), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(self.tmp / "src"), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(self.tmp / "src"), "add", "checkout.py"], check=True)
        subprocess.run(["git", "-C", str(self.tmp / "src"), "commit", "-qm", "fixture"], check=True)
        revision = subprocess.check_output(
            ["git", "-C", str(self.tmp / "src"), "rev-parse", "HEAD"],
            text=True,
        ).strip()
        self.write_config(last_full_source_commit=revision)
        self.assertEqual(self.run_validator().returncode, 0)
        self.write_config(last_full_source_commit="d" * 40)
        self.assert_fails("revision is not a reachable commit")


if __name__ == "__main__":
    unittest.main()
