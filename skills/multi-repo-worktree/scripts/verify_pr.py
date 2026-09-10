#!/usr/bin/env python3
"""Read-only exact PR identity/file/patch verification; no whitespace-insensitive patch IDs."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


class VerificationError(RuntimeError):
    pass


def command(argv: list[str], cwd: Path | None = None, *, timeout: int = 120) -> bytes:
    result = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if result.returncode:
        detail = (result.stderr or result.stdout).decode(errors="replace")[-1500:]
        raise VerificationError(f"{argv[0]} failed: {detail}")
    return result.stdout


def git(repo: Path, *args: str) -> bytes:
    return command(["git", "--no-optional-locks", "-C", str(repo), *args])


def github_repository(url: str) -> str:
    match = re.fullmatch(r"(?:git@github\.com:|https://github\.com/|ssh://git@github\.com/)([\w.-]+/[\w.-]+?)(?:\.git)?/?", url)
    if not match:
        raise VerificationError("remote must identify an exact github.com repository; other hosts need explicit handling")
    return match[1]


def pr_number(url: str, repository: str) -> int:
    match = re.fullmatch(r"https://github\.com/" + re.escape(repository) + r"/pull/([1-9][0-9]*)", url)
    if not match:
        raise VerificationError("PR URL does not match the bound repository")
    return int(match[1])


class GitHub:
    def api(self, endpoint: str, *, paginate: bool = False, diff: bool = False) -> Any:
        args = ["gh", "api", "--hostname", "github.com", "--method", "GET", endpoint]
        if paginate:
            args += ["--paginate", "--slurp"]
        if diff:
            args += ["-H", "Accept: application/vnd.github.diff"]
        raw = command(args)
        if diff:
            return raw
        data = json.loads(raw)
        return [item for page in data for item in page] if paginate else data

    def view(self, repository: str, number: int) -> dict[str, Any]:
        return self.api(f"repos/{repository}/pulls/{number}")

    def find(self, repository: str, branch: str) -> list[dict[str, Any]]:
        from urllib.parse import urlencode
        query = urlencode({"state": "all", "head": repository.split('/')[0] + ':' + branch, "per_page": 100})
        return self.api(f"repos/{repository}/pulls?{query}", paginate=True)

    def create(self, repository: str, base: str, head: str, title: str, body: str) -> str:
        return command(["gh", "pr", "create", "--repo", repository, "--base", base,
                        "--head", head, "--title", title, "--body", body]).decode().strip()


def check_identity(pr: dict[str, Any], repository: str, base: str, head: str,
                   head_sha: str, *, state: str = "OPEN", source_sha: str | None = None) -> None:
    actual_state = "MERGED" if pr.get("merged_at") else str(pr.get("state", "")).upper()
    if actual_state != state or pr.get("draft") is not False:
        raise VerificationError(f"expected ready {state} PR")
    for side, branch in (("base", base), ("head", head)):
        value = pr.get(side) or {}
        if (value.get("repo") or {}).get("full_name") != repository or value.get("ref") != branch:
            raise VerificationError(f"PR {side} repository/branch mismatch")
    if pr["head"].get("sha") != head_sha:
        raise VerificationError("PR head SHA mismatch")
    if source_sha is not None and pr["base"].get("sha") != source_sha:
        raise VerificationError("PR base SHA advanced or mismatched; revalidate before recording")
    if pr_number(pr.get("html_url", ""), repository) != pr.get("number"):
        raise VerificationError("PR number/URL mismatch")
    if state == "MERGED" and not pr.get("merge_commit_sha"):
        raise VerificationError("merged PR lacks merge commit evidence")


def compare_patches(local: bytes, remote: bytes) -> None:
    """Only index abbreviation and trailing function labels are presentation metadata.

    Code bytes, whitespace, EOF markers, modes, rename headers and binary data remain exact.
    Hashes must be matching prefixes, not arbitrary discarded index lines.
    """
    left, right = local.split(b"\n"), remote.split(b"\n")
    if len(left) != len(right):
        raise VerificationError("PR patch length differs (possibly truncated)")
    index = re.compile(rb"index ([0-9a-f]{7,64})\.\.([0-9a-f]{7,64})( [0-7]{6})?")
    hunk = re.compile(rb"(@@ -[0-9]+(?:,[0-9]+)? \+[0-9]+(?:,[0-9]+)? @@)(?: .*)?")
    for number, (a, b) in enumerate(zip(left, right), 1):
        if a == b:
            continue
        ai, bi = index.fullmatch(a), index.fullmatch(b)
        if ai and bi and ai[3] == bi[3]:
            if all(x.startswith(y) or y.startswith(x) for x, y in zip(ai.group(1, 2), bi.group(1, 2))):
                continue
        ah, bh = hunk.fullmatch(a), hunk.fullmatch(b)
        if ah and bh and ah[1] == bh[1]:
            continue
        raise VerificationError(f"PR patch differs at line {number}; code/paths/modes are not normalized")


def local_diff(repo: Path, source: str, head: str) -> bytes:
    return git(repo, "-c", "diff.algorithm=myers", "-c", "diff.indentHeuristic=true",
               "diff", "--no-ext-diff", "--no-textconv", "--no-color", "--full-index", "--binary",
               "--find-renames=50%", "--no-relative", "--src-prefix=a/", "--dst-prefix=b/",
               "--unified=3", "--inter-hunk-context=0", f"{source}...{head}", "--")


def verify(repo: Path, repository: str, number: int, base: str, head: str,
           source_sha: str, head_sha: str, api: GitHub | None = None) -> dict[str, Any]:
    api = api or GitHub()
    pr = api.view(repository, number)
    check_identity(pr, repository, base, head, head_sha, source_sha=source_sha)
    expected = set(git(repo, "diff", "--name-only", "-z", "--find-renames=50%",
                       f"{source_sha}...{head_sha}", "--").decode(errors="surrogateescape").split("\0")) - {""}
    files = api.api(f"repos/{repository}/pulls/{number}/files?per_page=100", paginate=True)
    paths = [item["filename"] for item in files]
    if len(paths) != len(set(paths)) or len(paths) != pr.get("changed_files") or set(paths) != expected:
        raise VerificationError("PR changed-files mismatch or incomplete GitHub file response")
    patch = local_diff(repo, source_sha, head_sha)
    compare_patches(patch, api.api(f"repos/{repository}/pulls/{number}", diff=True))
    # Detect a moving PR between the metadata, file-list and patch requests.
    check_identity(api.view(repository, number), repository, base, head, head_sha, source_sha=source_sha)
    return {"verified": True, "pr": pr["html_url"], "head_sha": head_sha,
            "source_sha": source_sha, "files": len(paths), "patch_sha256": hashlib.sha256(patch).hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo", "repository", "pr", "base", "head", "source-sha", "head-sha"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    try:
        result = verify(Path(args.repo).resolve(), args.repository, pr_number(args.pr, args.repository),
                        args.base, args.head, args.source_sha, args.head_sha)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (VerificationError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"verified": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
