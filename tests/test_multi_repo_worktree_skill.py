from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "multi-repo-worktree"
SKILL = SKILL_DIR / "SKILL.md"
REFERENCE = SKILL_DIR / "references" / "worktree-operations.md"
INSPECTOR = SKILL_DIR / "scripts" / "inspect_worktrees.py"
SLOT_MANIFEST = SKILL_DIR / "scripts" / "slot_manifest.py"
PR_SUBMISSION = SKILL_DIR / "scripts" / "inspect_pr_submission.py"
OPENAI_YAML = SKILL_DIR / "agents" / "openai.yaml"
PLUGIN_JSON = ROOT / ".codex-plugin" / "plugin.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class MultiRepoWorktreeSkillTests(unittest.TestCase):
    def test_skill_declares_explicit_only_multi_repo_scope(self) -> None:
        text = read(SKILL)

        self.assertIn("name: multi-repo-worktree", text)
        self.assertIn("Use only when the user explicitly invokes", text)
        self.assertIn("Do not use for ordinary Git, single-repo, or single-worktree requests", text)
        self.assertIn("multiple independent Git repositories", text)
        self.assertIn("help, status, create, recycle, submit, integrate, merge, and sync", text)
        self.assertIn("$stageflow:multi-repo-worktree <keyword> [free-form intent]", text)
        self.assertIn("[$stageflow:multi-repo-worktree](...)", text)
        self.assertIn("references/worktree-operations.md", text)
        self.assertIn("scripts/inspect_worktrees.py", text)
        self.assertIn('python3 "<skill-dir>/scripts/inspect_worktrees.py"', text)
        self.assertIn("do not assume the current working directory is the plugin root", text)
        self.assertNotIn("**Setup**", text)
        self.assertNotIn("TODO", text)

    def test_skill_records_source_and_derived_branch_safety_rules(self) -> None:
        text = read(SKILL)

        self.assertIn("source branch as a repo-specific, user-confirmed fact", text)
        self.assertIn("derived branches", text)
        self.assertIn("Git does not record the branch from which another branch was originally created", text)
        self.assertIn("Before any Git write", text)
        self.assertIn("Accept approval only after presenting that exact plan", text)
        self.assertIn("Approval applies only to the displayed batch", text)
        self.assertIn("Never execute a write using an inferred or ambiguous source branch", text)
        self.assertIn("Never reset, clean, force checkout, force push, or delete a branch", text)
        self.assertIn("Default to merge", text)
        self.assertIn("explicit approval", text)
        self.assertIn("Missing upstream blocks push or remote synchronization", text)
        self.assertIn("does not by itself block local create, merge, or sync", text)

    def test_reference_covers_required_operations(self) -> None:
        text = read(REFERENCE)

        for phrase in [
            "## Keyword Contract",
            "## Status",
            "## Create",
            "## Merge",
            "## Sync",
            "`help`",
            "`status`",
            "`create`",
            "`merge`",
            "`sync`",
            "## Recycle",
            "## Submit",
            "## Integrate",
            "## Dependencies And Partial Remote Results",
            "Normalize older wording without advertising it",
            "Preflight the complete batch",
            "Receive explicit approval after the plan",
            "source branch",
            "derived branch",
            "List repos independently even when branch names match",
            "A blocker in any repo blocks the batch plan",
            "Git does not retain a branch's creation parent",
            "Missing upstream does not block local merge",
        ]:
            self.assertIn(phrase, text)

    def test_pr_slot_workflow_has_explicit_roles_and_safety_gates(self) -> None:
        skill = read(SKILL)
        reference = read(REFERENCE)

        for phrase in [
            ".stageflow-worktrees/slots.json",
            "Only the exact active development owner",
            "release its slot and recycle it for the next independent task",
            "Integration must not release, claim, recycle",
            "GitHub owns source-branch updates",
            "outside every development bundle",
            "one-shot approved batch",
            "machine-readable",
            "stageflow-submitted-sha",
            "A later head change invalidates the handoff",
            "--match-head-commit",
            "runtime merge policy and strategy",
            "Do not add `--auto`, `--admin`, or `--delete-branch`",
            "provider is actually merged",
            "recovery-required",
            "never auto-rollback",
        ]:
            self.assertIn(phrase, skill)

        for phrase in [
            "create once",
            "Development owner",
            "Integration session",
            "GitHub",
            "Same-owner claim is idempotent",
            "wrong-owner release",
            "Recycle reuses a fixed directory",
            "prior local HEAD equals its pushed SHA",
            "Submission is bound to the full SHA",
            "provider merge request or queue admission is not enough",
            "Never auto-revert a merged provider",
        ]:
            self.assertIn(phrase, reference)

        for legacy in [
            "submit Draft",
            "submit Ready",
            "stageflow-ready-sha",
            "inspect_pr_readiness.py",
        ]:
            self.assertNotIn(legacy, skill)
            self.assertNotIn(legacy, reference)

        self.assertNotIn("merge-ready", skill)

    def test_single_submit_and_direct_integrate_contract(self) -> None:
        skill = read(SKILL)
        reference = read(REFERENCE)

        for phrase in [
            "submit regular PR at exact SHA",
            "stageflow-submitted-sha",
            "Write the title and all explanatory body prose in Korean",
            "exact Korean title and body",
            "Do not pass `--draft` or run `gh pr ready`",
            "Release the slot only after every participating repo is recorded successfully",
            "Reviews, status updates, and unrelated PR comments do not invalidate an unchanged head",
            "If a problem is found before integration",
            "latest submitted-SHA comment",
            "Do not add `--auto`, `--admin`, or `--delete-branch`",
            "If GitHub rejects a merge",
        ]:
            self.assertIn(phrase, reference)

        self.assertIn("Create or update regular non-Draft PRs", skill)
        self.assertIn("Write every PR title and all explanatory prose in its body in Korean", skill)
        self.assertIn("Show the exact Korean title and body before approval", skill)
        self.assertIn("latest submitted SHA", skill)
        self.assertIn("confirmed-strategy-flag", skill)
        self.assertNotIn("Draft submission", skill)
        self.assertNotIn("Ready submission", skill)

    def test_merge_requires_post_merge_push_prompt(self) -> None:
        skill = read(SKILL)
        reference = read(REFERENCE)

        self.assertIn("After successful merges, summarize results and ask", skill)
        self.assertIn("never include push in the merge batch", skill)
        self.assertIn("push까지 진행할까요?", skill)
        self.assertIn("After all requested merges succeed", reference)
        self.assertIn("Ask `push까지 진행할까요?`", reference)
        self.assertIn("Never include `git push` in the merge command batch", reference)
        self.assertIn("Do not ask to push a mixed or conflicted result", reference)

    def test_status_output_policy_uses_single_line_repo_summary(self) -> None:
        skill = read(SKILL)
        reference = read(REFERENCE)

        for text in [skill, reference]:
            self.assertIn("기준 폴더", text)
            self.assertIn("현재 브랜치", text)
            self.assertIn("변경상태", text)
            self.assertIn("dirty", text)
            self.assertIn("clean", text)

        self.assertIn("Do not use a Markdown table", skill)
        self.assertIn("원본 브랜치: feature-etc (추정)", skill)
        self.assertIn("majoong_events_api: 폴더 majoong_events_api / 현재 브랜치 feature-etc-docs / 변경상태 dirty", skill)
        self.assertIn("Do not use a Markdown table for status", reference)
        self.assertIn("<source-branch (추정)|확인 필요>", reference)
        self.assertIn("<repo>: 폴더 <relative-folder> / 현재 브랜치 <branch> / 변경상태 <dirty|clean>", reference)
        self.assertIn("Show each participating repo on one line", reference)
        self.assertIn("Make `폴더` relative to `기준 폴더`", reference)
        self.assertIn("Keep upstream, HEAD, locks, prunable state, and operation state out", reference)
        self.assertIn("filter to it and do not mix the workspace or sibling bundles", reference)

    def test_inspector_is_read_only_and_avoids_mutating_git_commands(self) -> None:
        text = read(INSPECTOR)
        tree = ast.parse(text)
        git_commands: list[tuple[str, ...]] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "run_git" or len(node.args) < 2 or not isinstance(node.args[1], ast.List):
                continue
            values = tuple(
                item.value for item in node.args[1].elts if isinstance(item, ast.Constant) and isinstance(item.value, str)
            )
            if values:
                git_commands.append(values)

        forbidden = {"add", "merge", "rebase", "push", "pull", "fetch", "reset", "switch", "checkout"}
        self.assertFalse({command[0] for command in git_commands} & forbidden)
        self.assertNotIn(("branch", "-D"), git_commands)

        self.assertIn('"worktree", "list", "--porcelain"', text)
        self.assertIn('"status", "--porcelain"', text)
        self.assertIn('"rev-parse", "--show-toplevel"', text)
        self.assertIn('"rev-parse", "--git-path", name', text)
        self.assertIn('"operation_state": operation_state(path)', text)
        self.assertIn('key in {"locked", "prunable"}', text)
        self.assertIn('parser.add_argument("--bundle"', text)
        self.assertIn('"GIT_OPTIONAL_LOCKS"] = "0"', text)
        self.assertIn('"git", "--no-optional-locks"', text)
        self.assertNotIn("repo별 다름", text)

    @unittest.skipIf(shutil.which("git") is None, "git is required for inspector smoke test")
    def test_inspector_reports_git_repo_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "service-a"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            result = subprocess.run(
                [sys.executable, str(INSPECTOR), "--root", str(root), "--max-depth", "2", "--json"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            data = json.loads(result.stdout)

            self.assertEqual(data["repository_group_count"], 1)
            self.assertGreaterEqual(data["worktree_count"], 1)
            self.assertEqual(data["groups"][0]["worktrees"][0]["dirty"], "clean")

    @unittest.skipIf(shutil.which("git") is None, "git is required for inspector smoke test")
    def test_inspector_filtered_output_uses_bundle_and_single_line_repos(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "service-a"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
            subprocess.run(["git", "checkout", "-b", "feature-etc"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (repo / "README.md").write_text("hello\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            bundle_repo = root / "worktrees" / "feature-etc-docs" / "service-a"
            subprocess.run(
                ["git", "worktree", "add", "-b", "feature-etc-docs", str(bundle_repo), "feature-etc"],
                cwd=repo,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(INSPECTOR),
                    "--root",
                    str(root),
                    "--max-depth",
                    "4",
                    "--bundle",
                    "worktrees/feature-etc-docs",
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            output = result.stdout

            self.assertIn("대상 묶음: worktrees/feature-etc-docs", output)
            self.assertIn("원본 브랜치: feature-etc (추정)", output)
            self.assertIn(f"기준 폴더: {bundle_repo.parent}", output)
            self.assertIn(
                "service-a: 폴더 service-a / 현재 브랜치 feature-etc-docs / 변경상태 clean",
                output,
            )
            self.assertNotIn("| Worktree Path |", output)
            self.assertNotIn("| --- |", output)
            self.assertNotIn("Upstream", output)
            self.assertNotIn("Workspace:", output)
            self.assertNotIn("Repository groups:", output)
            self.assertNotIn("Worktrees:", output)
            self.assertNotIn("대상 묶음: workspace", output)

            json_result = subprocess.run(
                [
                    sys.executable,
                    str(INSPECTOR),
                    "--root",
                    str(root),
                    "--max-depth",
                    "4",
                    "--bundle",
                    str(bundle_repo.parent),
                    "--json",
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            bundle_data = json.loads(json_result.stdout)

            self.assertEqual([bundle["name"] for bundle in bundle_data["bundles"]], ["worktrees/feature-etc-docs"])
            self.assertEqual(bundle_data["bundles"][0]["items"][0]["operation_state"], "-")

            bundle_result = subprocess.run(
                [sys.executable, str(INSPECTOR), "--root", str(bundle_repo.parent), "--max-depth", "2"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            bundle_output = bundle_result.stdout

            self.assertIn("대상 묶음: worktrees/feature-etc-docs", bundle_output)
            self.assertIn("원본 브랜치: 확인 필요", bundle_output)
            self.assertIn(f"기준 폴더: {bundle_repo.parent}", bundle_output)
            self.assertIn(
                "service-a: 폴더 service-a / 현재 브랜치 feature-etc-docs / 변경상태 clean",
                bundle_output,
            )
            self.assertNotIn("outside workspace", bundle_output)
            self.assertNotIn("폴더 /", bundle_output)
            self.assertNotIn("Workspace:", bundle_output)

    @unittest.skipIf(shutil.which("git") is None, "git is required for inspector smoke test")
    def test_inspector_reports_in_progress_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "service-a"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
            subprocess.run(["git", "checkout", "-b", "main"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            tracked = repo / "tracked.txt"
            tracked.write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "base"], cwd=repo, check=True, stdout=subprocess.PIPE)
            subprocess.run(["git", "checkout", "-b", "topic"], cwd=repo, check=True, stdout=subprocess.PIPE)
            tracked.write_text("topic\n", encoding="utf-8")
            subprocess.run(["git", "commit", "-am", "topic"], cwd=repo, check=True, stdout=subprocess.PIPE)
            subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, stdout=subprocess.PIPE)
            tracked.write_text("main\n", encoding="utf-8")
            subprocess.run(["git", "commit", "-am", "main"], cwd=repo, check=True, stdout=subprocess.PIPE)
            merge = subprocess.run(
                ["git", "merge", "topic"],
                cwd=repo,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(merge.returncode, 0)

            result = subprocess.run(
                [sys.executable, str(INSPECTOR), "--root", str(root), "--max-depth", "2", "--json"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            data = json.loads(result.stdout)

            self.assertEqual(data["groups"][0]["worktrees"][0]["operation_state"], "merge")

    @unittest.skipIf(shutil.which("git") is None, "git is required for inspector smoke test")
    def test_inspector_requires_confirmation_when_any_bundle_source_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            root = parent / "workspace"
            root.mkdir()

            repo_a = root / "service-a"
            repo_a.mkdir()
            subprocess.run(["git", "init"], cwd=repo_a, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_a, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_a, check=True)
            subprocess.run(["git", "checkout", "-b", "feature-base"], cwd=repo_a, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (repo_a / "README.md").write_text("hello\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repo_a, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_a, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "-b",
                    "feature-docs",
                    str(root / "worktrees" / "feature-docs" / "service-a"),
                    "feature-base",
                ],
                cwd=repo_a,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            repo_b = parent / "external-service-b"
            repo_b.mkdir()
            subprocess.run(["git", "init"], cwd=repo_b, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_b, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_b, check=True)
            subprocess.run(["git", "checkout", "-b", "other-base"], cwd=repo_b, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (repo_b / "README.md").write_text("hello\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repo_b, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_b, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "-b",
                    "feature-docs-b",
                    str(root / "worktrees" / "feature-docs" / "service-b"),
                    "other-base",
                ],
                cwd=repo_b,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            result = subprocess.run(
                [sys.executable, str(INSPECTOR), "--root", str(root), "--max-depth", "4"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            output = result.stdout
            bundle_section = output.split("대상 묶음: worktrees/feature-docs", maxsplit=1)[1]
            bundle_section = bundle_section.split("\n\n대상 묶음:", maxsplit=1)[0]

            self.assertIn("원본 브랜치: 확인 필요", bundle_section)
            self.assertIn("service-a: 폴더 service-a / 현재 브랜치 feature-docs / 변경상태 clean", bundle_section)
            self.assertIn("service-b: 폴더 service-b / 현재 브랜치 feature-docs-b / 변경상태 clean", bundle_section)
            self.assertNotIn("원본 브랜치: feature-base (추정)", bundle_section)

    @unittest.skipIf(shutil.which("git") is None, "git is required for inspector smoke test")
    def test_inspector_requires_confirmation_for_ambiguous_workspace_siblings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "service-a"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
            subprocess.run(["git", "checkout", "-b", "feature-base"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (repo / "README.md").write_text("hello\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "worktree", "add", "-b", "other-base", str(root / "service-a-alt"), "feature-base"],
                cwd=repo,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "-b",
                    "feature-docs",
                    str(root / "worktrees" / "feature-docs" / "service-a"),
                    "feature-base",
                ],
                cwd=repo,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            result = subprocess.run(
                [sys.executable, str(INSPECTOR), "--root", str(root), "--max-depth", "4"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            output = result.stdout
            bundle_section = output.split("대상 묶음: worktrees/feature-docs", maxsplit=1)[1]
            bundle_section = bundle_section.split("\n\n대상 묶음:", maxsplit=1)[0]

            self.assertIn("원본 브랜치: 확인 필요", bundle_section)
            self.assertNotIn("원본 브랜치: feature-base (추정)", bundle_section)
            self.assertNotIn("원본 브랜치: other-base (추정)", bundle_section)

    def test_openai_metadata_is_explicit_only(self) -> None:
        text = read(OPENAI_YAML)

        self.assertIn('display_name: "Multi Repo Worktree"', text)
        self.assertIn('short_description: "Safe multi-repo worktree and PR coordination."', text)
        self.assertIn("Use $stageflow:multi-repo-worktree status", text)
        self.assertIn("allow_implicit_invocation: false", text)

    def test_plugin_manifest_exposes_multi_repo_worktree_prompt(self) -> None:
        manifest = json.loads(read(PLUGIN_JSON))
        interface = manifest["interface"]

        self.assertIn("multi-repo-worktree", interface["longDescription"])
        self.assertIn(
            "help, status, create, recycle, submit, integrate, merge, and sync keywords",
            interface["longDescription"],
        )
        self.assertIn(
            "Use $stageflow:multi-repo-worktree status to inspect a multi-repo Git worktree or PR slot bundle.",
            interface["defaultPrompt"],
        )


class SlotManifestTests(unittest.TestCase):
    def run_manifest(self, root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SLOT_MANIFEST), "--root", str(root), *arguments],
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_claim_is_idempotent_for_exact_owner_and_rejects_other_owner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "worktrees" / "slot-1"
            first = self.run_manifest(
                root, "claim", "--slot", "slot-1", "--owner", "task-a", "--path", str(path)
            )
            second = self.run_manifest(
                root, "claim", "--slot", "slot-1", "--owner", "task-a", "--path", str(path)
            )
            conflict = self.run_manifest(
                root,
                "claim",
                "--slot",
                "slot-1",
                "--owner",
                "task-b",
                "--path",
                str(path),
                check=False,
            )

            self.assertEqual(json.loads(first.stdout)["result"], json.loads(second.stdout)["result"])
            self.assertEqual(conflict.returncode, 2)
            self.assertIn("owner mismatch", conflict.stderr)

    def test_concurrent_claims_have_one_owner_and_leave_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "worktrees" / "slot-1"
            commands = [
                [
                    sys.executable,
                    str(SLOT_MANIFEST),
                    "--root",
                    str(root),
                    "claim",
                    "--slot",
                    "slot-1",
                    "--owner",
                    owner,
                    "--path",
                    str(path),
                ]
                for owner in ["task-a", "task-b"]
            ]
            processes = [
                subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                for command in commands
            ]
            results = [process.communicate(timeout=10) + (process.returncode,) for process in processes]

            self.assertEqual(sorted(result[2] for result in results), [0, 2])
            status = json.loads(self.run_manifest(root, "status", "--slot", "slot-1").stdout)["result"]
            self.assertIn(status["owner"], {"task-a", "task-b"})
            self.assertEqual(status["state"], "active")

    def test_only_active_exact_owner_can_record_and_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "worktrees" / "slot-1"
            self.run_manifest(root, "claim", "--slot", "slot-1", "--owner", "task-a", "--path", str(path))

            integration_release = self.run_manifest(
                root, "release", "--slot", "slot-1", "--owner", "integration", check=False
            )
            self.assertEqual(integration_release.returncode, 2)

            self.run_manifest(
                root,
                "record",
                "--slot",
                "slot-1",
                "--owner",
                "task-a",
                "--repo",
                "service-a",
                "--branch",
                "task-a",
                "--head-sha",
                "a" * 40,
                "--pushed-sha",
                "a" * 40,
                "--pr",
                "17",
            )
            released = self.run_manifest(
                root, "release", "--slot", "slot-1", "--owner", "task-a"
            )
            stale_release = self.run_manifest(
                root, "release", "--slot", "slot-1", "--owner", "task-a", check=False
            )

            result = json.loads(released.stdout)["result"]
            self.assertEqual(result["state"], "released")
            self.assertEqual(result["repositories"]["service-a"]["pr"], "17")
            self.assertEqual(stale_release.returncode, 2)
            self.assertIn("not active", stale_release.stderr)

    def test_released_slot_can_be_claimed_by_new_owner_without_branch_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "worktrees" / "slot-1"
            self.run_manifest(root, "claim", "--slot", "slot-1", "--owner", "task-a", "--path", str(path))
            self.run_manifest(root, "release", "--slot", "slot-1", "--owner", "task-a")
            claimed = self.run_manifest(
                root, "claim", "--slot", "slot-1", "--owner", "task-b", "--path", str(path)
            )
            old_owner = self.run_manifest(
                root, "release", "--slot", "slot-1", "--owner", "task-a", check=False
            )

            result = json.loads(claimed.stdout)["result"]
            self.assertEqual(result["owner"], "task-b")
            self.assertEqual(result["repositories"], {})
            self.assertEqual(old_owner.returncode, 2)
            self.assertNotIn("subprocess", read(SLOT_MANIFEST))

    def test_record_stays_active_until_release_and_correction_owner_can_resubmit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "worktrees" / "slot-1"
            self.run_manifest(root, "claim", "--slot", "slot-1", "--owner", "task-a", "--path", str(path))
            self.run_manifest(
                root,
                "record",
                "--slot", "slot-1",
                "--owner", "task-a",
                "--repo", "service-a",
                "--branch", "task-a",
                "--head-sha", "a" * 40,
                "--pushed-sha", "a" * 40,
                "--pr", "17",
            )

            active = json.loads(self.run_manifest(root, "status", "--slot", "slot-1").stdout)["result"]
            self.assertEqual(active["state"], "active")

            self.run_manifest(root, "release", "--slot", "slot-1", "--owner", "task-a")
            self.run_manifest(root, "claim", "--slot", "slot-1", "--owner", "correction-a", "--path", str(path))
            self.run_manifest(
                root,
                "record",
                "--slot", "slot-1",
                "--owner", "correction-a",
                "--repo", "service-a",
                "--branch", "task-a",
                "--head-sha", "b" * 40,
                "--pushed-sha", "b" * 40,
                "--pr", "17",
            )
            corrected = json.loads(
                self.run_manifest(root, "release", "--slot", "slot-1", "--owner", "correction-a").stdout
            )["result"]

            self.assertEqual(corrected["state"], "released")
            self.assertEqual(corrected["repositories"]["service-a"]["head_sha"], "b" * 40)
            self.assertEqual(corrected["repositories"]["service-a"]["pr"], "17")

    def test_released_fixed_slot_rejects_a_different_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / "worktrees" / "slot-1"
            replacement = root / "worktrees" / "other-slot"
            self.run_manifest(root, "claim", "--slot", "slot-1", "--owner", "task-a", "--path", str(original))
            self.run_manifest(root, "release", "--slot", "slot-1", "--owner", "task-a")
            result = self.run_manifest(
                root,
                "claim",
                "--slot",
                "slot-1",
                "--owner",
                "task-b",
                "--path",
                str(replacement),
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("fixed slot path mismatch", result.stderr)
            status = json.loads(self.run_manifest(root, "status", "--slot", "slot-1").stdout)["result"]
            self.assertEqual(status["path"], str(original))

    def test_malformed_manifest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".stageflow-worktrees"
            state.mkdir()
            (state / "slots.json").write_text("{broken", encoding="utf-8")
            result = self.run_manifest(root, "status", check=False)

            self.assertEqual(result.returncode, 2)
            self.assertIn("cannot read manifest", result.stderr)


class PrSubmissionTests(unittest.TestCase):
    def fixture(
        self,
        path: Path,
        *,
        head: str = "a" * 40,
        submitted_sha: str | None = None,
        submitted_created_at: str = "2026-07-20T07:00:00Z",
        **updates: object,
    ) -> None:
        data: dict[str, object] = {
            "number": 17,
            "url": "https://github.example/pr/17",
            "state": "OPEN",
            "isDraft": False,
            "baseRefName": "feature-etc",
            "headRefName": "task-a",
            "headRefOid": head,
            "reviewDecision": "APPROVED",
            "statusCheckRollup": [{"name": "test", "conclusion": "SUCCESS"}],
            "mergeStateStatus": "CLEAN",
            "mergeable": "MERGEABLE",
            "updatedAt": "2026-07-20T07:05:00Z",
            "comments": [{
                "body": f"<!-- stageflow-submitted-sha: {submitted_sha or head} -->",
                "createdAt": submitted_created_at,
            }],
        }
        data.update(updates)
        path.write_text(json.dumps(data), encoding="utf-8")

    def inspect(self, fixture: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(PR_SUBMISSION),
                "--input",
                str(fixture),
                "--base",
                "feature-etc",
            ],
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_exact_submitted_sha_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "pr.json"
            self.fixture(fixture)
            result = json.loads(self.inspect(fixture).stdout)

            self.assertTrue(result["submitted"])
            self.assertEqual(result["head_sha"], "a" * 40)
            self.assertEqual(result["latest_submitted_sha"], "a" * 40)

    def test_closed_draft_wrong_base_and_conflict_fail_closed(self) -> None:
        cases = [
            {"state": "CLOSED"},
            {"isDraft": True},
            {"baseRefName": "main"},
            {"comments": []},
            {"mergeable": "CONFLICTING"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for index, updates in enumerate(cases):
                with self.subTest(updates=updates):
                    fixture = Path(tmp) / f"pr-{index}.json"
                    self.fixture(fixture, **updates)
                    result = self.inspect(fixture, check=False)
                    self.assertEqual(result.returncode, 1)
                    self.assertFalse(json.loads(result.stdout)["submitted"])

    def test_head_move_invalidates_old_submission_until_resubmitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "pr.json"
            old_head = "a" * 40
            new_head = "b" * 40
            self.fixture(fixture, head=new_head, submitted_sha=old_head)
            stale = self.inspect(fixture, check=False)

            self.assertEqual(stale.returncode, 1)
            self.assertIn("latest submitted SHA declaration does not match current head", stale.stdout)

            self.fixture(fixture, head=new_head, submitted_sha=new_head)
            recovered = json.loads(self.inspect(fixture).stdout)
            self.assertTrue(recovered["submitted"])
            self.assertEqual(recovered["submitted_shas"], [new_head])

    def test_latest_submission_marker_controls_after_correction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "pr.json"
            head = "a" * 40
            self.fixture(fixture, head=head)
            data = json.loads(fixture.read_text(encoding="utf-8"))
            data["comments"].append({
                "body": f"<!-- stageflow-submitted-sha: {'b' * 40} -->",
                "createdAt": "2026-07-20T07:06:00Z",
            })
            fixture.write_text(json.dumps(data), encoding="utf-8")
            returned = self.inspect(fixture, check=False)

            self.assertEqual(returned.returncode, 1)
            self.assertIn("latest submitted SHA declaration does not match current head", returned.stdout)

            self.fixture(
                fixture,
                head=head,
                submitted_sha=head,
                submitted_created_at="2026-07-20T07:07:00Z",
            )
            self.assertTrue(json.loads(self.inspect(fixture).stdout)["submitted"])

    def test_review_checks_merge_state_and_later_pr_activity_do_not_block_unchanged_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "pr.json"
            self.fixture(
                fixture,
                reviewDecision="REVIEW_REQUIRED",
                statusCheckRollup=[{"name": "test", "conclusion": "FAILURE"}],
                mergeStateStatus="BLOCKED",
                updatedAt="2026-07-20T08:00:00Z",
            )
            data = json.loads(fixture.read_text(encoding="utf-8"))
            data["comments"].append({
                "body": "review note without a submission marker",
                "createdAt": "2026-07-20T08:00:00Z",
            })
            fixture.write_text(json.dumps(data), encoding="utf-8")

            result = json.loads(self.inspect(fixture).stdout)
            self.assertTrue(result["submitted"])

    def test_helper_contains_only_read_only_gh_commands(self) -> None:
        text = read(PR_SUBMISSION)
        self.assertIn('["gh", "auth", "status"]', text)
        self.assertIn('"gh", "pr", "view"', text)
        for command in ["pr create", "pr edit", "pr ready", "pr merge", "api --method"]:
            self.assertNotIn(command, text)


if __name__ == "__main__":
    unittest.main()
