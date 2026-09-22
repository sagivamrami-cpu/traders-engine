"""Pinned source inventory. Verification never imports the trading repositories.

Source identity is not proof of executable coverage, causal replay, deployment,
or model readiness. This module intentionally cannot authorize any of those.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


SCHEMA = "existing-alerts-baseline-v1"


def _text(value, name):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be a nonempty trimmed string")
    return value


def _path(value):
    _text(value, "path")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", value):
        raise ValueError("source path must be canonical and relative")
    if any(part in (".", "..") for part in value.split("/")):
        raise ValueError("source path cannot traverse directories")
    return value


def _fields(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected.split()):
        raise ValueError(f"expected exact fields: {expected}")


def _items(value, name):
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a nonempty list")
    return value


def _unique(items, name):
    if len(items) != len(set(items)):
        raise ValueError(f"duplicate {name}")


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


@dataclass(frozen=True)
class Source:
    path: str
    symbol: str
    role: str


@dataclass(frozen=True)
class Repository:
    name: str
    url: str
    commit: str
    sources: tuple[Source, ...]


@dataclass(frozen=True)
class Producer:
    id: str
    repository: str
    path: str


@dataclass(frozen=True)
class Baseline:
    baseline_id: str
    repositories: tuple[Repository, ...]
    producers: tuple[Producer, ...]
    limitations: tuple[str, ...]

    def _manifest(self):
        return {"schema_version": SCHEMA, "baseline_id": self.baseline_id,
                "repositories": [asdict(r) for r in self.repositories],
                "producers": [asdict(p) for p in self.producers],
                "limitations": list(self.limitations)}

    @property
    def manifest_sha256(self):
        encoded = json.dumps(self._manifest(), ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_payload(self):
        return {**self._manifest(), "manifest_sha256": self.manifest_sha256,
                "source_verified": False, "ready_for_replay": False,
                "ready_for_training": False}


def load_baseline(path: Path) -> Baseline:
    data = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_object)
    _fields(data, "schema_version baseline_id repositories producers limitations")
    if data["schema_version"] != SCHEMA:
        raise ValueError("unsupported baseline schema")
    name = _text(data["baseline_id"], "baseline_id")
    repos = []
    for row in _items(data["repositories"], "repositories"):
        _fields(row, "name url commit sources")
        slug = _text(row["name"], "repository name")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValueError("invalid repository name")
        url = _text(row["url"], "url")
        if not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/" + re.escape(slug), url):
            raise ValueError("repository URL must match its GitHub name")
        commit = _text(row["commit"], "commit")
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError("commit must be a full lowercase SHA1")
        sources = []
        for item in _items(row["sources"], "sources"):
            _fields(item, "path symbol role")
            sources.append(Source(_path(item["path"]), _text(item["symbol"], "symbol"),
                                  _text(item["role"], "role")))
        _unique([(s.path, s.symbol) for s in sources], "source reference")
        repos.append(Repository(slug, url, commit, tuple(sorted(sources, key=lambda s: (s.path, s.symbol)))))
    _unique([r.name for r in repos], "repository")
    paths = {r.name: {s.path for s in r.sources} for r in repos}
    producers = []
    for row in _items(data["producers"], "producers"):
        _fields(row, "id repository path")
        producer = Producer(_text(row["id"], "producer id"),
                            _text(row["repository"], "repository"), _path(row["path"]))
        if producer.repository not in paths or producer.path not in paths[producer.repository]:
            raise ValueError("producer must reference a listed repository/source path")
        producers.append(producer)
    _unique([p.id for p in producers], "producer")
    limitations = tuple(_text(s, "limitation") for s in _items(data["limitations"], "limitations"))
    _unique(limitations, "limitation")
    return Baseline(name, tuple(sorted(repos, key=lambda r: r.name)),
                    tuple(sorted(producers, key=lambda p: p.id)), tuple(sorted(limitations)))


def _git(path: Path, *args: str, input_text: str | None = None) -> str:
    # Status can otherwise refresh the index; missing promisor blobs can fetch.
    # Disable those behaviors even when the caller environment enables them.
    env = {**os.environ, "GIT_ALLOW_PROTOCOL": "", "GIT_TERMINAL_PROMPT": "0",
           "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1"}
    result = subprocess.run(
        ["git", "--no-optional-locks", "--no-lazy-fetch", "--no-replace-objects",
         "-c", "core.fsmonitor=false", "-C", str(path), *args],
        capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=15,
        env=env, input=input_text,
    )
    if result.returncode:
        raise ValueError("git inspection failed")
    # In particular, NUL-delimited filenames must retain leading whitespace.
    return result.stdout


def _worktree_blockers(path: Path, sources: set[str]) -> list[str]:
    """Check metadata before status, which may run configured content filters.

    Unused global filters (e.g. LFS) are harmless; any filter attribute on a
    tracked path is unsupported. Sparse paths outside the pinned source list
    are allowed, but assume-unchanged entries can conceal arbitrary changes.
    """
    blockers = []
    flags = _git(path, "ls-files", "-v", "-z").split("\0")
    if any(row and (row[0].islower() or (row[0] == "S" and row[2:] in sources))
           for row in flags):
        blockers.append("MASKED_WORKTREE_ENTRY")
    staged = _git(path, "ls-files", "--stage", "-z").split("\0")
    if any(row.startswith("160000 ") for row in staged):
        blockers.append("UNSUPPORTED_SUBMODULE")
    tracked = _git(path, "ls-files", "-z")
    if tracked:
        attrs = _git(path, "check-attr", "-z", "--stdin", "filter",
                     input_text=tracked).split("\0")
        if any(value not in ("unspecified", "unset") for value in attrs[2::3]):
            blockers.append("EXTERNAL_GIT_FILTER")
    # Never enter status when its content conversion or submodule traversal
    # could execute repository-configured external processes.
    if not blockers and _git(path, "status", "--porcelain", "--untracked-files=all",
                             "--ignore-submodules=none"):
        blockers.append("DIRTY_CHECKOUT")
    return blockers


def verify_checkouts(baseline: Baseline, root: Path) -> dict:
    """Inspect only; never fetch, change branches, import modules, or run hooks.

    The caller must use load_baseline for untrusted manifests. This verifies
    commits and tracked source paths, not the named functions' semantics.
    """
    rows = []
    for pin in baseline.repositories:
        path = Path(root).resolve() / pin.name
        blockers = []
        actual = None
        if not path.is_dir():
            blockers.append("MISSING_CHECKOUT")
        else:
            try:
                top = Path(_git(path, "rev-parse", "--show-toplevel").strip()).resolve()
                if top != path.resolve():
                    blockers.append("NOT_REPOSITORY_ROOT")
                else:
                    actual = _git(path, "rev-parse", "HEAD").strip()
                    if actual != pin.commit:
                        blockers.append("COMMIT_MISMATCH")
                    sources = {s.path for s in pin.sources}
                    blockers.extend(_worktree_blockers(path, sources))
                    for source in sorted(sources):
                        try:
                            kind = _git(path, "cat-file", "-t", f"{pin.commit}:{source}").strip()
                            if kind != "blob" or not (path / source).is_file():
                                blockers.append(f"MISSING_SOURCE:{source}")
                        except ValueError:
                            blockers.append(f"MISSING_SOURCE:{source}")
            except (OSError, ValueError, subprocess.TimeoutExpired):
                blockers.append("GIT_INSPECTION_FAILED")
        rows.append({"name": pin.name, "expected_commit": pin.commit,
                     "actual_commit": actual, "blockers": blockers,
                     "source_verified": not blockers})
    return {**baseline.to_payload(), "repositories": rows,
            "source_verified": bool(rows) and all(r["source_verified"] for r in rows)}
