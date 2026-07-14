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
        self,
        phase: str,
        *expected_atom_keys: str,
        request_id: str | None = None,
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
        if request_id is not None:
            command.extend(["--request-id", request_id])
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
        with_aids: bool = True,
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
            ("Outcomes", "outcome", "관찰 결과"),
            ("Boundaries", "boundary", "책임 경계"),
            ("Rules", "rules", "규칙"),
            ("Current Implementation", "impl", "현재 동작"),
            ("Planned Changes", "plan", "계획"),
            ("Gaps", "gap", "차이"),
        ]
        body: list[str] = []
        for heading, code, prose in sections:
            if heading == omit_section:
                continue
            content = f"- [AID:{prefix}.{code}.001] {prose}" if with_aids else f"- {prose}"
            body.extend(["", f"## {heading}", "", content])
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

    def write_selection_state(
        self,
        candidates: list[dict[str, object]],
        *,
        bundle_keys: list[str],
        risk_triggers: list[dict[str, object]] | None = None,
        request_id: str = "20260714-120000-selection-test",
        accepted_scope: list[str] | None = None,
        bundle_domain: str = "domain",
        selection_version: str | None = "1",
        source_commit: str | None = None,
    ) -> str:
        request_root = self.root / ".stageflow" / "atomic-docs" / "requests" / request_id
        request_root.mkdir(parents=True)
        (request_root / "inventory.md").write_text("# 후보\n", encoding="utf-8")
        observed = source_commit or self.commit
        evidence = ["# 근거 색인", "", f"source_commit_observed: `{observed}`"]
        for candidate in candidates:
            candidate_id = candidate.get("candidate_id")
            if isinstance(candidate_id, str):
                evidence.extend(
                    ["", f"## {candidate_id}", "", "- `source.txt:1` 후보 판단 근거"]
                )
        (request_root / "evidence.md").write_text(
            "\n".join(evidence) + "\n", encoding="utf-8"
        )
        context_selection: dict[str, object] = {"candidates": candidates}
        if selection_version is not None:
            context_selection["version"] = selection_version
        (request_root / "work-state.json").write_text(
            json.dumps(
                {
                    "accepted_scope": ["domain"] if accepted_scope is None else accepted_scope,
                    "source_commit_observed": observed,
                    "context_selection": context_selection,
                    "bundle_queue": [
                        {"domain": bundle_domain, "expected_atom_keys": bundle_keys}
                    ],
                    "risk_triggers": risk_triggers or [],
                }
            ),
            encoding="utf-8",
        )
        return request_id

    def test_bootstrap_passes_without_atoms_or_baseline(self) -> None:
        result = self.run_validator("bootstrap")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("PASS bootstrap", result.stdout)

    def test_selection_accepts_write_merge_drop_and_candidate_linked_risk(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "공유 소유권을 소스 한 곳에서 찾기 어렵다.",
                    "candidate_atom_keys": ["domain-context"],
                },
                {
                    "candidate_id": "durable-contract",
                    "domain": "domain",
                    "candidate": "지속적인 계약",
                    "disposition": "write",
                    "selection_basis": "다른 도메인이 사용하는 계약이다.",
                    "candidate_atom_keys": ["durable-contract"],
                },
                {
                    "candidate_id": "supporting-context",
                    "domain": "domain",
                    "candidate": "중복된 보조 흐름",
                    "disposition": "merge",
                    "selection_basis": "독립 소유권 없이 기존 계약의 읽기 맥락만 보완한다.",
                    "merge_target_atom_key": "durable-contract",
                },
                {
                    "candidate_id": "dormant-mutation",
                    "domain": "domain",
                    "candidate": "호출되지 않는 mutation",
                    "disposition": "drop",
                    "selection_basis": "현재 consumer와 승인된 활성화 계획이 없다.",
                },
            ],
            bundle_keys=["domain-context", "durable-contract"],
            risk_triggers=[
                {
                    "candidate_id": "durable-contract",
                    "atom_key": "durable-contract",
                    "triggers": ["shared policy contract"],
                    "basis": "선택된 계약을 다른 도메인이 소비한다.",
                },
                {
                    "candidate_id": "supporting-context",
                    "atom_key": "durable-contract",
                    "triggers": ["money contract"],
                    "basis": "합쳐지는 결제 맥락이 같은 계약에 위험 검토를 요구한다.",
                }
            ],
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("PASS selection", result.stdout)

    def test_selection_rejects_blank_basis_and_unknown_merge_target(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": " ",
                    "candidate_atom_keys": ["domain-context"],
                },
                {
                    "candidate_id": "merge-context",
                    "domain": "domain",
                    "candidate": "합칠 후보",
                    "disposition": "merge",
                    "selection_basis": "기존 문맥에 포함한다.",
                    "merge_target_atom_key": "missing-owner",
                },
            ],
            bundle_keys=["domain-context"],
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("must include non-empty `selection_basis`", result.stdout)
        self.assertIn("merge target `missing-owner` is not a write candidate atom", result.stdout)

    def test_selection_rejects_drop_output_and_domain_level_risk_reference(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "도메인 소유권을 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                },
                {
                    "candidate_id": "dropped-detail",
                    "domain": "domain",
                    "candidate": "제외할 상세",
                    "disposition": "drop",
                    "selection_basis": "소스에서 바로 확인되는 내부 동작이다.",
                    "candidate_atom_keys": ["dropped-detail"],
                },
            ],
            bundle_keys=["domain-context", "dropped-detail"],
            risk_triggers=[
                {
                    "candidate_id": "dropped-detail",
                    "atom_key": "dropped-detail",
                    "triggers": ["destructive method"],
                    "basis": "코드에 위험한 이름이 있다.",
                }
            ],
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("with disposition `drop` must not create atom keys", result.stdout)
        self.assertIn("must not reference dropped candidate `dropped-detail`", result.stdout)
        self.assertIn("bundle queue atom key `dropped-detail` has no write candidate", result.stdout)

    def test_selection_rejects_empty_scope_and_wrong_bundle_domain(self) -> None:
        empty_scope = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            accepted_scope=[],
            request_id="20260714-120001-empty-scope",
        )
        result = self.run_validator("selection", request_id=empty_scope)
        self.assertEqual(1, result.returncode)
        self.assertIn("must contain at least one approved domain path", result.stdout)
        self.assertIn("domain `domain` is outside `accepted_scope`", result.stdout)

        wrong_domain = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            bundle_domain="other-domain",
            request_id="20260714-120002-wrong-domain",
        )
        result = self.run_validator("selection", request_id=wrong_domain)
        self.assertEqual(1, result.returncode)
        self.assertIn("domain `other-domain` is outside `accepted_scope`", result.stdout)
        self.assertIn("belongs to domain `domain`, not `other-domain`", result.stdout)

    def test_selection_requires_version_revision_candidate_id_and_evidence_locator(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            selection_version=None,
            source_commit="0" * 40,
            request_id="20260714-120003-bad-evidence",
        )
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("`context_selection.version` must be `1`", result.stdout)
        self.assertIn("source commit `0000000000000000000000000000000000000000` is not reachable", result.stdout)
        self.assertIn("must include lower-kebab-case `candidate_id`", result.stdout)

        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120004-empty-evidence",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            f"# 근거 색인\n\nsource_commit_observed: `{self.commit}`\n\n## domain-context\n",
            encoding="utf-8",
        )
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("needs a source locator and concise relevance", result.stdout)

    def test_selection_rejects_evidence_header_that_declares_another_revision(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120005-contradictory-revision",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "",
                    f"source_commit_observed: `{'0' * 40}`",
                    "",
                    "## domain-context",
                    "",
                    f"- `source.txt:1` 실제 상태 hash는 {self.commit}",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            f"evidence source commit `{'0' * 40}` does not match work-state `{self.commit}`",
            result.stdout,
        )

    def test_selection_rejects_multiline_evidence_revision_declaration(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120015-multiline-revision",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "source_commit_observed:",
                    "",
                    f"`{self.commit}`",
                    "## domain-context",
                    "- `source.txt:1` 실제 표시되는 근거",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "must declare exactly one `source_commit_observed` line",
            result.stdout,
        )

    def test_selection_rejects_duplicate_json_keys_in_operation_state(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120006-duplicate-json-key",
        )
        state_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "work-state.json"
        )
        state_text = state_path.read_text(encoding="utf-8")
        state_path.write_text(
            state_text.replace(
                '{"accepted_scope": ["domain"]',
                '{"accepted_scope": [], "accepted_scope": ["domain"]',
                1,
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("duplicate JSON key 'accepted_scope'", result.stdout)

    def test_selection_rejects_fenced_evidence_shape(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120007-fenced-evidence",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "",
                    "```bad`info",
                    f"source_commit_observed: `{self.commit}`",
                    "",
                    "## domain-context",
                    "- `source.txt:1` 코드 예시 안의 가짜 근거",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("evidence index must not contain fenced code", result.stdout)

    def test_selection_ignores_evidence_shape_inside_hidden_html(self) -> None:
        wrappers = {
            "comment": (["<!--"], ["-->"]),
            "pre": (["<pre>"], ["</pre>"]),
            "multiline-pre": (["<pre", 'class="hidden">'], ["</pre>"]),
            "multiline-pre-quoted-close": (
                ["<pre", 'data="</pre>">'],
                ["</pre>"],
            ),
            "active-pre-nested-attribute": (
                ["<pre>", '<span data="</pre>">'],
                ["</span>", "</pre>"],
            ),
            "active-pre-comment": (
                ["<pre>", "<!-- </pre> -->"],
                ["</pre>"],
            ),
            "closed-root-trailing-hidden-root": (
                ["<pre></pre><div hidden>"],
                ["</div>"],
            ),
            "void-root-trailing-hidden-root": (
                ["<hr><div hidden>"],
                ["</div>"],
            ),
            "comment-trailing-hidden-root": (
                ["<!-- closed --><div hidden>"],
                ["</div>"],
            ),
            "processing-instruction-trailing-hidden-root": (
                ["<?closed?><div hidden>"],
                ["</div>"],
            ),
            "multiline-void-quoted-delimiter": (
                ["<img", 'alt=">"'],
                [">"],
            ),
            "processing-instruction": (["<?hidden"], ["?>"]),
            "processing-instruction-with-fake-close": (
                ["<div>", '<?pi data="> </div>"?>'],
                ["</div>"],
            ),
            "cdata": (["<![CDATA["], ["]]>"]),
            "self-closing-nonvoid": (["<div/>"], []),
            "slash-newline-tag": (["<div/", ">"], []),
            "slash-tab-tag": (["<img/", "\talt=x>"], []),
            "namespaced-tag": (["<svg:path>"], ["</svg:path>"]),
            "underscore-tag": (["<x_widget>"], ["</x_widget>"]),
            "generic-blank-boundary": (["<section>", ""], ["</section>"]),
            "escaped-backticks": ([r"\`<div hidden>\`"], []),
        }
        for suffix, (opening_lines, closing_lines) in wrappers.items():
            with self.subTest(suffix=suffix):
                request_id = self.write_selection_state(
                    [
                        {
                            "candidate_id": "domain-context",
                            "domain": "domain",
                            "candidate": "도메인 맥락",
                            "disposition": "write",
                            "selection_basis": "승인된 경계를 설명한다.",
                            "candidate_atom_keys": ["domain-context"],
                        }
                    ],
                    bundle_keys=["domain-context"],
                    request_id=f"20260714-120008-hidden-{suffix}",
                )
                evidence_path = (
                    self.root
                    / ".stageflow"
                    / "atomic-docs"
                    / "requests"
                    / request_id
                    / "evidence.md"
                )
                evidence_path.write_text(
                    "\n".join(
                        [
                            "# 근거 색인",
                            "",
                            *opening_lines,
                            f"source_commit_observed: `{self.commit}`",
                            "",
                            "## domain-context",
                            "- `source.txt:1` 숨겨진 HTML 안의 가짜 근거",
                            *closing_lines,
                            "",
                        ]
                    ),
                    encoding="utf-8",
                )

                result = self.run_validator("selection", request_id=request_id)
                self.assertEqual(1, result.returncode)
                self.assertIn(
                    "must not contain raw HTML-like syntax",
                    result.stdout,
                )

    def test_selection_rejects_raw_html_before_visible_evidence(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120009-void-html",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "",
                    "<img",
                    'alt="표시용 구분선">',
                    f"source_commit_observed: `{self.commit}`",
                    "",
                    "## domain-context",
                    "- `source.txt:1` 실제 표시되는 근거",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "must not contain raw HTML-like syntax",
            result.stdout,
        )

    def test_selection_rejects_nested_and_mixed_indented_evidence(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120010-indented-html",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "",
                    ">     exact payload/parser dump",
                    "-     exact nested-list dump",
                    "   \texact serializer detail",
                    f"source_commit_observed: `{self.commit}`",
                    "",
                    "## domain-context",
                    "- `source.txt:1` 실제 표시되는 근거",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("evidence index must not contain indented code", result.stdout)

    def test_selection_rejects_tab_padded_locator(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120014-tab-locator",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    f"source_commit_observed: `{self.commit}`",
                    "## domain-context",
                    "-\t`source.txt:1` tab으로 구분한 locator",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("evidence index must not contain tab characters", result.stdout)
        self.assertIn(
            "evidence section `## domain-context` needs a source locator",
            result.stdout,
        )

    def test_selection_rejects_html_text_inside_inline_code(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120011-inline-html",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "",
                    "`<div hidden>`은 코드 예시일 뿐이다.",
                    f"source_commit_observed: `{self.commit}`",
                    "",
                    "## domain-context",
                    "- `source.txt:1` 실제 표시되는 근거",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("must not contain raw HTML-like syntax", result.stdout)

    def test_selection_rejects_multiline_inline_code_evidence_shape(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120012-multiline-inline",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "prefix ``code",
                    f"source_commit_observed: `{self.commit}`",
                    "## domain-context",
                    "- `source.txt:1` 코드 span 안의 가짜 근거",
                    "end`` suffix",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "evidence inline code must open and close on the same line",
            result.stdout,
        )

    def test_selection_handles_backslash_inside_line_local_code_span(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120013-backslash-code",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "코드 표기: `path\\`",
                    f"source_commit_observed: `{self.commit}`",
                    "## domain-context",
                    "- `source.txt:1` 실제 표시되는 근거",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "prefix `first\\` tail`",
                    f"source_commit_observed: `{self.commit}`",
                    "## domain-context",
                    "- `source.txt:1` 다음 줄까지 이어지는 가짜 code span",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "evidence inline code must open and close on the same line",
            result.stdout,
        )

    def test_selection_requires_request_id_and_keeps_existing_phases_compatible(self) -> None:
        selection = self.run_validator("selection")
        self.assertEqual(1, selection.returncode)
        self.assertIn("requires `--request-id`", selection.stdout)

        bootstrap = self.run_validator("bootstrap")
        self.assertEqual(0, bootstrap.returncode, bootstrap.stdout + bootstrap.stderr)

        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "소유권을 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
        )
        wrong_phase = self.run_validator("bootstrap", request_id=request_id)
        self.assertEqual(1, wrong_phase.returncode)
        self.assertIn("`--request-id` requires `--phase selection`", wrong_phase.stdout)

    def test_docs_and_project_wide_baseline_pass(self) -> None:
        self.write_atom("domain/example-atom.md", "example")
        docs_result = self.run_validator("docs")
        self.assertEqual(0, docs_result.returncode, docs_result.stdout + docs_result.stderr)
        self.assertIn("1 atoms", docs_result.stdout)
        self.assertIn("7 AIDs", docs_result.stdout)

        self.write_baseline()
        baseline_result = self.run_validator("baseline")
        self.assertEqual(0, baseline_result.returncode, baseline_result.stdout + baseline_result.stderr)
        self.assertIn("PASS baseline", baseline_result.stdout)

    def test_atom_without_aids_is_valid(self) -> None:
        self.write_atom("domain/context-atom.md", "context", with_aids=False)

        result = self.run_validator("docs")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("1 atoms", result.stdout)
        self.assertIn("0 AIDs", result.stdout)

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
        self.write_atom("domain/example-atom.md", "example", omit_section="Outcomes")
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("must contain exactly one `## Outcomes` section", result.stdout)

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
            "[AID:example.outcome.001]", "[AID:example.boundary.001]"
        )
        path.write_text(text, encoding="utf-8")
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("belongs under `## Boundaries`, not `Outcomes`", result.stdout)

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
