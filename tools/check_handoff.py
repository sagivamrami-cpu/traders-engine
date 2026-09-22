"""Read-only handoff checks; prints paths/rules, never matched credential values.

This is a targeted publication preflight, not a comprehensive secret scanner.
Checks the prospective Git tree (tracked plus nonignored untracked files),
source-artifact hashes, and links in the current entrypoint documents.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINTS = (
    "README.md", "AGENTS.md", "CLAUDE.md", "PROJECT_STATE.md",
    "docs/architecture/YUVAL-HANDOFF.md",
    "docs/architecture/YUVAL-PROJECT-ONBOARDING.html",
    "docs/architecture/SAGIV-INPUTS-REQUIRED-FOR-PROJECT.html",
    "docs/architecture/SAGIV-INPUTS-REQUIRED-FOR-PROJECT.md",
)
ARTIFACTS = {
    "docs/sources/tr-hybrid-intelligence-tree.html": "f7de3d8cfac6e468268ec79a8b3b990a97d62608a1fbe68b58952534c107f1ad",
    "docs/sources/management/DYNAMIC_MANAGEMENT_TREE_HE.html": "18a14be8cf67d9c18e0a3f67c0ed0683c10e9c0e1a4c7f593243557828c377ee",
    "docs/sources/management/MANAGEMENT_DIAGRAMS_HE.html": "de0d71699f61e860b9e02c5b93f55c5fb4a136d6c793a986eb72f8c22f202f49",
    "docs/sources/management/ACCOUNT_1000_MANAGEMENT_REPORT_HE.html": "18b564d25e62562d97c50a64ec2203ae4dcf869755f2787a056fd97e8f85f007",
}
PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b"),
    "api_token": re.compile(r"\b(?:sk-(?:proj-|ant-api\d+-)?[A-Za-z0-9_-]{40,}|gsk_[A-Za-z0-9]{40,})\b"),
    "aws_access_key": re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    "telegram_token": re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{35}\b"),
}


def main() -> int:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, capture_output=True, check=True,
    )
    names = sorted(set(result.stdout.decode("utf-8").strip("\0").split("\0")))
    issues = []
    for name in names:
        path = ROOT / name
        if not path.is_file():
            issues.append({"path": name, "rule": "missing_file"})
            continue
        if path.stat().st_size > 20 * 1024 * 1024:
            issues.append({"path": name, "rule": "large_artifact"})
        is_fixture = name.startswith("tests/fixtures/")
        if ((path.suffix.lower() in {".parquet", ".dbn", ".zst", ".zip", ".pem", ".key"})
                or (path.suffix.lower() == ".csv" and not is_fixture)
                or (path.name.startswith(".env") and path.name != ".env.example")
                or name.startswith(("market-data/", ".source-checkouts/", ".venv/"))):
            issues.append({"path": name, "rule": "local_only_artifact"})
        content = path.read_bytes().decode("utf-8", errors="replace")
        for rule, pattern in PATTERNS.items():
            for match in pattern.finditer(content):
                issues.append({"path": name, "rule": rule,
                               "line": content.count("\n", 0, match.start()) + 1})
    for name, expected in ARTIFACTS.items():
        path = ROOT / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            issues.append({"path": name, "rule": "source_digest_mismatch"})
    links_checked = 0
    for name in ENTRYPOINTS:
        path = ROOT / name
        if not path.is_file():
            issues.append({"path": name, "rule": "missing_entrypoint"})
            continue
        content = path.read_text(encoding="utf-8")
        links = re.findall(r'\]\(([^)]+)\)', content)
        links += re.findall(r'href=["\']([^"\']+)["\']', content)
        for link in links:
            if re.match(r"(?:[a-z]+:|#)", link, re.I):
                continue
            target = unquote(link.split("#", 1)[0].split("?", 1)[0])
            if target:
                links_checked += 1
                if not (path.parent / target).exists():
                    issues.append({"path": name, "rule": "broken_local_link", "target": target})
    print(json.dumps({"files_checked": len(names), "links_checked": links_checked,
                      "artifact_hashes_checked": len(ARTIFACTS), "issues": issues}, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
