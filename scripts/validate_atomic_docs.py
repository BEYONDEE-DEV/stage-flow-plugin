#!/usr/bin/env python3
"""Validate the minimal Atomic Docs v2 config and managed document contract."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

CONFIG_KEYS = {
    "version",
    "storage_mode",
    "docs_root",
    "source_root",
    "language",
    "last_full_source_commit",
    "auxiliary_sources",
}
AUX_KEYS = {"name", "path", "revision"}
ATOM_HEADINGS = [
    "Purpose",
    "Boundaries",
    "Contracts",
    "Implementation",
    "Sources",
    "Changes",
    "Open Questions",
]
GOAL_HEADINGS = ["Purpose", "Users", "Success", "Non-goals", "Sources"]
GLOSSARY_HEADER = [
    "Term",
    "Meaning",
    "Scope Or Owner",
    "Source Of Truth",
    "Do Not Confuse With",
    "Sources",
]
KEY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")
REVISION_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
RID_RE = re.compile(
    r"\[RID:(?P<atom>[a-z0-9]+(?:-[a-z0-9]+)*)\."
    r"(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\]"
)
RID_CANDIDATE_RE = re.compile(r"\[RID:[^\]\n]*\]")
LOCATOR_RE = re.compile(
    r"^(?P<source>[a-z0-9]+(?:-[a-z0-9]+)*):"
    r"(?P<path>[^#\n]+)#"
    r"(?P<symbol>[^\n]+)$"
)
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
LINE_SYMBOL_RE = re.compile(r"(?i)(?:^|[:@])L?\d+(?:[-:]L?\d+)?$")


@dataclass(frozen=True)
class SourceRoot:
    name: str
    path: Path
    revision: str | None = None
    git_object_prefix: str = ""


@dataclass
class Atom:
    path: Path
    key: str
    depends_on: list[str]
    sections: dict[str, str]


class Validator:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.errors: list[str] = []
        self.config: dict[str, Any] | None = None
        self.docs_root: Path | None = None
        self.sources: dict[str, SourceRoot] = {}
        self.atoms: list[Atom] = []
        self.rids: dict[str, Path] = {}

    def error(self, path: Path | str, field: str, cause: str, recovery: str) -> None:
        try:
            label = str(Path(path).resolve().relative_to(self.root))
        except (OSError, ValueError):
            label = str(path)
        self.errors.append(f"{label}: {field}: {cause}; recovery: {recovery}")

    def run(self) -> bool:
        self.validate_config()
        if self.docs_root is not None and self.sources:
            self.validate_managed_docs()
            self.validate_relationships()
        return not self.errors

    def validate_config(self) -> None:
        path = self.root / ".stageflow" / "atomic-docs.json"
        if not path.is_file():
            self.error(
                path,
                "config",
                "required config file is missing",
                "create the exact Atomic Docs v2 config",
            )
            return
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self.error(path, "config", f"cannot read valid JSON ({exc})", "write valid UTF-8 JSON")
            return
        if not isinstance(value, dict):
            self.error(path, "config", "top level must be an object", "write the exact v2 object")
            return
        self.config = value
        actual_keys = set(value)
        if actual_keys != CONFIG_KEYS:
            missing = sorted(CONFIG_KEYS - actual_keys)
            extra = sorted(actual_keys - CONFIG_KEYS)
            self.error(
                path,
                "config keys",
                f"expected exact keys; missing={missing}, extra={extra}",
                "add missing keys and remove unsupported keys",
            )
        if type(value.get("version")) is not int or value.get("version") != 2:
            self.error(path, "version", "must be integer 2", "set `version` to 2")
        if value.get("storage_mode") not in {"repository", "submodule"}:
            self.error(
                path,
                "storage_mode",
                "must be `repository` or `submodule`",
                "choose one supported storage mode",
            )
        language = value.get("language")
        if not isinstance(language, str) or not LANGUAGE_RE.fullmatch(language):
            self.error(
                path,
                "language",
                "must be a non-empty language tag such as `ko` or `en-US`",
                "set a valid language tag",
            )

        docs_root = self.resolve_primary_path(path, "docs_root", value.get("docs_root"), allow_dot=False)
        source_root = self.resolve_primary_path(path, "source_root", value.get("source_root"), allow_dot=True)
        if docs_root is not None:
            if not docs_root.is_dir():
                self.error(path, "docs_root", "configured directory does not exist", "create the accepted docs root")
            else:
                self.docs_root = docs_root
        if source_root is not None:
            if not source_root.is_dir():
                self.error(path, "source_root", "configured directory does not exist", "fix or create the source root")
            else:
                self.sources["primary"] = SourceRoot("primary", source_root)

        baseline = value.get("last_full_source_commit")
        if baseline is not None:
            if not isinstance(baseline, str) or not REVISION_RE.fullmatch(baseline):
                self.error(
                    path,
                    "last_full_source_commit",
                    "must be null or a full lowercase SHA-1/SHA-256 commit hash",
                    "set null or the full hash of a reachable primary commit",
                )
            elif source_root is not None and source_root.is_dir():
                self.validate_revision(path, "last_full_source_commit", source_root, baseline)

        auxiliaries = value.get("auxiliary_sources")
        if not isinstance(auxiliaries, list):
            self.error(
                path,
                "auxiliary_sources",
                "must be an array",
                "set an empty array or valid auxiliary source objects",
            )
            return
        names: set[str] = set()
        for index, item in enumerate(auxiliaries):
            field = f"auxiliary_sources[{index}]"
            if not isinstance(item, dict):
                self.error(path, field, "must be an object", "use name/path/revision object")
                continue
            if set(item) != AUX_KEYS:
                self.error(
                    path,
                    field,
                    f"must contain exact keys {sorted(AUX_KEYS)}",
                    "remove unsupported keys and add missing keys",
                )
            name = item.get("name")
            if not isinstance(name, str) or not KEY_RE.fullmatch(name) or name == "primary":
                self.error(
                    path,
                    f"{field}.name",
                    "must be a unique lower-kebab name other than `primary`",
                    "choose a valid auxiliary source name",
                )
                continue
            if name in names:
                self.error(path, f"{field}.name", "duplicates another source name", "choose a unique name")
                continue
            names.add(name)
            aux_root = self.resolve_aux_path(path, f"{field}.path", item.get("path"))
            revision = item.get("revision")
            if not isinstance(revision, str) or not REVISION_RE.fullmatch(revision):
                self.error(
                    path,
                    f"{field}.revision",
                    "must be a full lowercase SHA-1/SHA-256 commit hash",
                    "pin the full hash of a reachable auxiliary commit",
                )
            if aux_root is not None:
                if not aux_root.is_dir():
                    self.error(path, f"{field}.path", "configured directory does not exist", "fix the path")
                else:
                    self.sources[name] = SourceRoot(
                        name,
                        aux_root,
                        revision,
                        self.git_object_prefix(aux_root),
                    )
                    if isinstance(revision, str) and REVISION_RE.fullmatch(revision):
                        self.validate_revision(path, f"{field}.revision", aux_root, revision)

    def resolve_primary_path(
        self,
        config_path: Path,
        field: str,
        value: Any,
        *,
        allow_dot: bool,
    ) -> Path | None:
        if not isinstance(value, str) or not value:
            self.error(config_path, field, "must be a non-empty relative path", "set a portable path")
            return None
        if value == "." and allow_dot:
            return self.root
        if not self.is_portable_path(value, allow_parent=False):
            self.error(
                config_path,
                field,
                "must be a portable project-relative path without traversal",
                "use POSIX components inside the primary project",
            )
            return None
        resolved = (self.root / value).resolve()
        if not resolved.is_relative_to(self.root):
            self.error(config_path, field, "resolves outside the primary project", "use a contained path")
            return None
        return resolved

    def resolve_aux_path(self, config_path: Path, field: str, value: Any) -> Path | None:
        if not isinstance(value, str) or not value or not self.is_portable_path(value, allow_parent=True):
            self.error(
                config_path,
                field,
                "must be a portable relative path",
                "use a primary-project-relative POSIX path",
            )
            return None
        return (self.root / value).resolve()

    @staticmethod
    def is_portable_path(value: str, *, allow_parent: bool) -> bool:
        if "\\" in value or "\x00" in value or Path(value).is_absolute():
            return False
        pure = PurePosixPath(value)
        if pure.as_posix() != value:
            return False
        parts = pure.parts
        if not parts or any(part in {"", "."} for part in parts):
            return False
        if not allow_parent and ".." in parts:
            return False
        return all(part == ".." or re.fullmatch(r"[A-Za-z0-9._+@-]+", part) for part in parts)

    def validate_revision(self, config_path: Path, field: str, source_root: Path, revision: str) -> None:
        exists = subprocess.run(
            ["git", "-C", str(source_root), "cat-file", "-e", f"{revision}^{{commit}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if exists.returncode != 0:
            self.error(
                config_path,
                field,
                "revision is not a reachable commit in the configured source",
                "pin a commit available in that repository",
            )
            return
        ancestor = subprocess.run(
            ["git", "-C", str(source_root), "merge-base", "--is-ancestor", revision, "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if ancestor.returncode != 0:
            self.error(
                config_path,
                field,
                "revision is not reachable from current HEAD",
                "pin an ancestor of current HEAD or stabilize the source checkout",
            )

    @staticmethod
    def git_object_prefix(source_root: Path) -> str:
        result = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "--show-prefix"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return ""
        return result.stdout.rstrip("\r\n")

    def validate_managed_docs(self) -> None:
        assert self.docs_root is not None
        goal = self.docs_root / "project" / "project-goal.md"
        self.validate_project_goal(goal)
        glossary = self.docs_root / "project" / "project-glossary.md"
        if glossary.exists():
            self.validate_glossary(glossary)

        atom_paths = sorted(self.docs_root.rglob("*-atom.md"))
        if not atom_paths:
            self.error(
                self.docs_root,
                "Atoms",
                "no `*-atom.md` files exist",
                "create at least one source-backed Atom",
            )
        allowed = {goal.resolve(), glossary.resolve(), *(path.resolve() for path in atom_paths)}
        for path in sorted(self.docs_root.rglob("*")):
            if not path.is_file() or path.name == ".git":
                continue
            if path.resolve() not in allowed:
                self.error(
                    path,
                    "managed path",
                    "file is not a supported permanent Atomic Docs output",
                    "remove it or move non-Atomic-Docs content outside docs_root",
                )
        for path in atom_paths:
            relative = path.relative_to(self.docs_root)
            topic = path.name[: -len("-atom.md")]
            if len(relative.parts) != 2 or relative.parts[0] == "project":
                self.error(
                    path,
                    "managed path",
                    "Atom must be directly under one non-project domain directory",
                    "move it to `<docs-root>/<domain>/<topic>-atom.md`",
                )
            if not KEY_RE.fullmatch(relative.parts[0]) or not KEY_RE.fullmatch(topic):
                self.error(
                    path,
                    "managed path",
                    "domain and Atom topic must use lower-kebab names",
                    "rename the domain directory or Atom file",
                )
            atom = self.parse_atom(path)
            if atom is not None:
                self.atoms.append(atom)

    def validate_project_goal(self, path: Path) -> None:
        text = self.read_markdown(path, "project goal")
        if text is None:
            return
        self.validate_retired_identifiers(path, text, allow_rid=False)
        sections = self.validate_document_shape(path, text, GOAL_HEADINGS)
        if sections is None:
            return
        for heading in GOAL_HEADINGS[:-1]:
            self.require_meaningful(path, heading, sections[heading], allow_none=False)
        self.validate_sources(path, sections["Sources"], "Sources")

    def validate_glossary(self, path: Path) -> None:
        text = self.read_markdown(path, "project glossary")
        if text is None:
            return
        self.validate_retired_identifiers(path, text, allow_rid=False)
        sections = self.validate_document_shape(path, text, ["Terms"])
        if sections is None:
            return
        lines = [line.strip() for line in sections["Terms"].splitlines() if line.strip()]
        if len(lines) < 3:
            self.error(path, "Terms", "table requires a header, separator, and data row", "add a glossary row")
            return
        header = self.table_cells(lines[0])
        separator = self.table_cells(lines[1])
        if header != GLOSSARY_HEADER:
            self.error(path, "Terms header", "does not match the required columns", "use the exact glossary header")
        if len(separator) != len(GLOSSARY_HEADER) or not all(
            re.fullmatch(r":?-{3,}:?", cell) for cell in separator
        ):
            self.error(path, "Terms separator", "is not a valid six-column Markdown separator", "fix the table")
        for index, line in enumerate(lines[2:], start=1):
            cells = self.table_cells(line)
            if len(cells) != len(GLOSSARY_HEADER) or any(not cell for cell in cells):
                self.error(
                    path,
                    f"Terms row {index}",
                    "must have six non-empty cells",
                    "complete or remove the invalid row",
                )
                continue
            self.validate_sources(path, cells[-1], f"Terms row {index} Sources")

    @staticmethod
    def table_cells(line: str) -> list[str]:
        if not line.startswith("|") or not line.endswith("|"):
            return []
        return [cell.strip() for cell in line[1:-1].split("|")]

    def parse_atom(self, path: Path) -> Atom | None:
        text = self.read_markdown(path, "Atom")
        if text is None:
            return None
        parsed = self.parse_frontmatter(path, text)
        if parsed is None:
            return None
        key, depends_on, body = parsed
        self.validate_retired_identifiers(path, body, allow_rid=True)
        sections = self.validate_document_shape(path, body, ATOM_HEADINGS)
        if sections is None:
            return None
        for heading in ATOM_HEADINGS[:5]:
            if heading == "Sources":
                self.validate_sources(path, sections[heading], heading)
            else:
                self.require_meaningful(path, heading, sections[heading], allow_none=False)
        self.validate_optional_section(path, "Changes", sections["Changes"])
        self.validate_optional_section(path, "Open Questions", sections["Open Questions"])
        self.validate_rids(path, key, sections, body)
        return Atom(path=path, key=key, depends_on=depends_on, sections=sections)

    def parse_frontmatter(self, path: Path, text: str) -> tuple[str, list[str], str] | None:
        lines = text.splitlines()
        if not lines or lines[0] != "---":
            self.error(path, "frontmatter", "must start with `---`", "add atom_key and depends_on frontmatter")
            return None
        try:
            end = lines.index("---", 1)
        except ValueError:
            self.error(path, "frontmatter", "closing `---` is missing", "close the frontmatter")
            return None
        raw = lines[1:end]
        values: dict[str, Any] = {}
        index = 0
        while index < len(raw):
            line = raw[index]
            if line.startswith("atom_key:"):
                if "atom_key" in values:
                    self.error(path, "atom_key", "is duplicated", "keep one atom_key")
                values["atom_key"] = line.partition(":")[2].strip()
            elif line == "depends_on: []":
                if "depends_on" in values:
                    self.error(path, "depends_on", "is duplicated", "keep one depends_on")
                values["depends_on"] = []
            elif line == "depends_on:":
                if "depends_on" in values:
                    self.error(path, "depends_on", "is duplicated", "keep one depends_on")
                dependencies: list[str] = []
                index += 1
                while index < len(raw) and raw[index].startswith("  - "):
                    dependencies.append(raw[index][4:].strip())
                    index += 1
                if not dependencies:
                    self.error(
                        path,
                        "depends_on",
                        "empty dependencies must use exact `depends_on: []`",
                        "replace the empty YAML block with `depends_on: []`",
                    )
                values["depends_on"] = dependencies
                continue
            elif line.strip():
                self.error(
                    path,
                    "frontmatter",
                    f"unsupported line `{line}`",
                    "keep only atom_key and depends_on",
                )
            index += 1
        if set(values) != {"atom_key", "depends_on"}:
            self.error(
                path,
                "frontmatter",
                "requires exactly atom_key and depends_on",
                "add both required fields and remove extras",
            )
            return None
        key = values["atom_key"]
        dependencies = values["depends_on"]
        if not isinstance(key, str) or not KEY_RE.fullmatch(key):
            self.error(path, "atom_key", "must be lower-kebab text", "choose a stable valid key")
            return None
        if not isinstance(dependencies, list) or any(
            not isinstance(item, str) or not KEY_RE.fullmatch(item) for item in dependencies
        ):
            self.error(
                path,
                "depends_on",
                "must be [] or a YAML list of lower-kebab Atom keys",
                "fix the dependency list",
            )
            dependencies = []
        if len(dependencies) != len(set(dependencies)):
            self.error(path, "depends_on", "contains duplicate keys", "deduplicate direct dependencies")
        if key in dependencies:
            self.error(path, "depends_on", "contains its own atom_key", "remove the self dependency")
        return key, dependencies, "\n".join(lines[end + 1 :]) + "\n"

    def read_markdown(self, path: Path, kind: str) -> str | None:
        if not path.is_file():
            self.error(path, kind, "required file is missing", f"create the required {kind}")
            return None
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            self.error(path, kind, f"cannot read UTF-8 text ({exc})", "write readable UTF-8 Markdown")
            return None

    def validate_document_shape(
        self,
        path: Path,
        text: str,
        expected: list[str],
    ) -> dict[str, str] | None:
        headings = self.level_two_headings(text)
        names = [name for name, _, _ in headings]
        if names != expected:
            self.error(
                path,
                "headings",
                f"expected exact order {expected}, found {names}",
                "use each required level-two heading exactly once and remove extras",
            )
            return None
        h1 = [
            line
            for line in self.visible_lines(text)
            if line.startswith("# ") and not line.startswith("## ")
        ]
        if len(h1) != 1 or not h1[0][2:].strip():
            self.error(path, "title", "requires exactly one non-empty level-one title", "add one `# Title`")
        sections: dict[str, str] = {}
        lines = text.splitlines()
        for index, (name, line_index, _) in enumerate(headings):
            next_index = headings[index + 1][1] if index + 1 < len(headings) else len(lines)
            sections[name] = "\n".join(lines[line_index + 1 : next_index]).strip()
        return sections

    @staticmethod
    def visible_lines(text: str) -> list[str]:
        visible: list[str] = []
        fence: str | None = None
        for line in text.splitlines():
            stripped = line.lstrip()
            marker = stripped[:3] if stripped.startswith(("```", "~~~")) else None
            if marker:
                if fence is None:
                    fence = marker
                elif marker == fence:
                    fence = None
                continue
            if fence is None:
                visible.append(line)
        return visible

    def level_two_headings(self, text: str) -> list[tuple[str, int, str]]:
        headings: list[tuple[str, int, str]] = []
        fence: str | None = None
        for index, line in enumerate(text.splitlines()):
            stripped = line.lstrip()
            marker = stripped[:3] if stripped.startswith(("```", "~~~")) else None
            if marker:
                if fence is None:
                    fence = marker
                elif marker == fence:
                    fence = None
                continue
            if fence is None and line.startswith("## "):
                headings.append((line[3:].strip(), index, line))
        return headings

    def require_meaningful(self, path: Path, heading: str, content: str, *, allow_none: bool) -> None:
        if not content:
            self.error(path, heading, "section is empty", "add meaningful content")
        elif not allow_none and content.strip() == "- 없음":
            self.error(path, heading, "`- 없음` is not allowed here", "add meaningful content")

    def validate_optional_section(self, path: Path, heading: str, content: str) -> None:
        if not content:
            self.error(path, heading, "section is empty", "use exact `- 없음` or meaningful content")
            return
        if any(line.strip() == "- 없음" for line in content.splitlines()) and content.strip() != "- 없음":
            self.error(
                path,
                heading,
                "empty marker must be exact `- 없음` and stand alone",
                "use the exact empty marker or remove it",
            )

    def validate_sources(self, path: Path, content: str, field: str) -> None:
        locators = [
            token
            for token in INLINE_CODE_RE.findall(content)
            if ":" in token and "#" in token
        ]
        if not locators:
            self.error(
                path,
                field,
                "requires at least one inline-code source locator",
                "add `<source-name>:<relative-path>#<symbol>`",
            )
            return
        for locator in locators:
            match = LOCATOR_RE.fullmatch(locator)
            if match is None:
                self.error(
                    path,
                    field,
                    f"invalid source locator `{locator}`",
                    "use exact source:path#symbol syntax with a non-empty path and symbol",
                )
                continue
            source_name = match.group("source")
            relative = match.group("path")
            symbol = match.group("symbol")
            source = self.sources.get(source_name)
            if source is None:
                self.error(
                    path,
                    field,
                    f"source name `{source_name}` is not configured",
                    "use `primary` or a configured auxiliary name",
                )
                continue
            if not self.is_source_relative_path(relative):
                self.error(
                    path,
                    field,
                    f"locator path `{relative}` is not a contained POSIX path",
                    "use a normalized source-root-relative path",
                )
                continue
            if source.revision is not None:
                pinned = subprocess.run(
                    [
                        "git",
                        "-C",
                        str(source.path),
                        "cat-file",
                        "-t",
                        f"{source.revision}:{source.git_object_prefix}{relative}",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if pinned.returncode != 0 or pinned.stdout.strip() != "blob":
                    self.error(
                        path,
                        field,
                        f"locator file `{relative}` is not a file at pinned revision `{source.revision}`",
                        "fix the locator or pin the revision that owns the file",
                    )
            else:
                target = (source.path / relative).resolve()
                if not target.is_relative_to(source.path):
                    self.error(path, field, f"locator `{locator}` escapes its source root", "use a contained path")
                elif not target.is_file():
                    self.error(path, field, f"locator file `{relative}` does not exist", "fix the source path")
            if LINE_SYMBOL_RE.search(symbol):
                self.error(
                    path,
                    field,
                    f"locator symbol `{symbol}` looks like a line number or range",
                    "use a stable symbol or source anchor",
                )

    @staticmethod
    def is_source_relative_path(value: str) -> bool:
        if "\\" in value or "\x00" in value:
            return False
        pure = PurePosixPath(value)
        if pure.is_absolute() or pure.as_posix() != value:
            return False
        return bool(pure.parts) and all(part not in {"", ".", ".."} for part in pure.parts)

    def validate_rids(
        self,
        path: Path,
        atom_key: str,
        sections: dict[str, str],
        body: str,
    ) -> None:
        changes = sections["Changes"]
        all_candidates = RID_CANDIDATE_RE.findall(body)
        valid_tokens = [match.group(0) for match in RID_RE.finditer(body)]
        if sorted(all_candidates) != sorted(valid_tokens):
            self.error(path, "RID", "contains malformed RID syntax", "use `[RID:<atom_key>.<lower-kebab-slug>]`")
        change_tokens = [match.group(0) for match in RID_RE.finditer(changes)]
        if sorted(valid_tokens) != sorted(change_tokens):
            self.error(path, "RID", "RID appears outside Changes", "move the RID to the owning Changes item")
        if changes.strip() == "- 없음":
            if change_tokens:
                self.error(path, "Changes", "empty section contains a RID", "remove the RID or the empty marker")
            return
        if not change_tokens:
            self.error(
                path,
                "Changes",
                "non-empty active changes require at least one RID",
                "add one owning RID per change item",
            )
        for line in changes.splitlines():
            if line.startswith("- ") and len(RID_RE.findall(line)) != 1:
                self.error(
                    path,
                    "Changes",
                    "each top-level change item must contain exactly one RID",
                    "split or label the change items",
                )
        for match in RID_RE.finditer(changes):
            token = match.group(0)
            if match.group("atom") != atom_key:
                self.error(path, "RID", f"`{token}` does not match atom_key `{atom_key}`", "fix the RID owner prefix")
            if token in self.rids:
                self.error(path, "RID", f"`{token}` is duplicated", "keep the RID exactly once")
            else:
                self.rids[token] = path

    def validate_retired_identifiers(self, path: Path, text: str, *, allow_rid: bool) -> None:
        if "[AID:" in text or "[AID-REF:" in text:
            self.error(path, "identifiers", "retired AID/AID-REF syntax is present", "remove the legacy token")
        if "[RID-REF:" in text:
            self.error(path, "RID", "RID reference syntax is not supported", "keep the RID only in owning Changes")
        if not allow_rid and "[RID:" in text:
            self.error(path, "RID", "RID is allowed only in an Atom Changes section", "remove or move the RID")

    def validate_relationships(self) -> None:
        by_key: dict[str, Atom] = {}
        for atom in self.atoms:
            if atom.key in by_key:
                self.error(
                    atom.path,
                    "atom_key",
                    f"duplicates `{atom.key}` from {by_key[atom.key].path}",
                    "choose one globally unique stable key",
                )
            else:
                by_key[atom.key] = atom
        for atom in self.atoms:
            for dependency in atom.depends_on:
                if dependency not in by_key:
                    self.error(
                        atom.path,
                        "depends_on",
                        f"`{dependency}` does not resolve to an Atom",
                        "fix or remove the direct dependency",
                    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="primary project root")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    validator = Validator(Path(args.root))
    if validator.run():
        print(
            "PASS atomic-docs: "
            f"atoms={len(validator.atoms)} sources={len(validator.sources)} "
            f"docs_root={validator.docs_root}"
        )
        return 0
    print("FAIL atomic-docs")
    for error in validator.errors:
        print(f"- {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
