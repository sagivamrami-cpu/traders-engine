"""Source identity must block stale/mutated checkouts without executing code."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from trading_system.tree_spec.baseline import load_baseline, verify_checkouts


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "configs/trees/existing-alerts-baseline.json"


def git(path, *args):
    return subprocess.check_output(
        ["git", "-C", str(path), *args], text=True, encoding="utf-8"
    ).strip()


@pytest.fixture
def source_fixture(tmp_path):
    repo = tmp_path / "sample-desk"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")
    (repo / "calc.py").write_text("raise RuntimeError('never import me')\n", encoding="utf-8")
    git(repo, "add", "calc.py")
    git(repo, "-c", "core.hooksPath=", "commit", "-qm", "synthetic source")
    data = {
        "schema_version": "existing-alerts-baseline-v1",
        "baseline_id": "fixture-v1",
        "repositories": [{
            "name": "sample-desk", "url": "https://github.com/fixture/sample-desk",
            "commit": git(repo, "rev-parse", "HEAD"),
            "sources": [{"path": "calc.py", "symbol": "module", "role": "calculation"}],
        }],
        "producers": [{"id": "tree:house", "repository": "sample-desk", "path": "calc.py"}],
        "limitations": ["No runtime or historical data verified"],
    }
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return tmp_path, repo, path, data


def rewrite(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return load_baseline(path)


def test_clean_pinned_source_is_verified_but_not_replay_ready(source_fixture):
    root, _, path, _ = source_fixture
    report = verify_checkouts(load_baseline(path), root)
    assert report["source_verified"] is True
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False
    assert report["repositories"][0]["blockers"] == []


def test_source_files_are_never_imported(source_fixture):
    root, _, path, _ = source_fixture
    assert verify_checkouts(load_baseline(path), root)["source_verified"] is True


@pytest.mark.parametrize("mutation,expected", [
    ("tracked", "DIRTY_CHECKOUT"), ("untracked", "DIRTY_CHECKOUT"),
    ("commit", "COMMIT_MISMATCH"), ("missing", "MISSING_CHECKOUT"),
    ("source", "MISSING_SOURCE:absent.py"),
])
def test_changed_or_missing_sources_block(source_fixture, mutation, expected):
    root, repo, path, data = source_fixture
    if mutation == "tracked":
        (repo / "calc.py").write_text("changed\n", encoding="utf-8")
    elif mutation == "untracked":
        (repo / "other.py").write_text("extra\n", encoding="utf-8")
    elif mutation == "commit":
        git(repo, "-c", "core.hooksPath=", "commit", "--allow-empty", "-qm", "later")
    elif mutation == "missing":
        repo.rename(root / "moved")
    else:
        data["repositories"][0]["sources"][0]["path"] = "absent.py"
        data["producers"][0]["path"] = "absent.py"
        rewrite(path, data)
    report = verify_checkouts(load_baseline(path), root)
    assert report["source_verified"] is False
    assert expected in report["repositories"][0]["blockers"]


def test_nested_directory_cannot_masquerade_as_repo(source_fixture):
    root, repo, path, data = source_fixture
    nested = repo / "sample-desk"
    nested.mkdir()
    report = verify_checkouts(load_baseline(path), repo)
    assert "NOT_REPOSITORY_ROOT" in report["repositories"][0]["blockers"]


@pytest.mark.parametrize("bad_path", ["../calc.py", "/calc.py", "C:/calc.py", "x\\calc.py", "./calc.py", "x//calc.py"])
def test_noncanonical_source_paths_rejected(source_fixture, bad_path):
    _, _, path, data = source_fixture
    data["repositories"][0]["sources"][0]["path"] = bad_path
    with pytest.raises(ValueError, match="path"):
        rewrite(path, data)


@pytest.mark.parametrize("mutation", ["hash", "repo_duplicate", "producer_duplicate", "unknown_repo", "unknown_source", "empty", "unknown_field", "bad_schema"])
def test_malformed_manifests_fail_closed(source_fixture, mutation):
    _, _, path, data = source_fixture
    if mutation == "hash":
        data["repositories"][0]["commit"] = "latest"
    elif mutation == "repo_duplicate":
        data["repositories"].append(copy.deepcopy(data["repositories"][0]))
    elif mutation == "producer_duplicate":
        data["producers"].append(copy.deepcopy(data["producers"][0]))
    elif mutation == "unknown_repo":
        data["producers"][0]["repository"] = "other"
    elif mutation == "unknown_source":
        data["producers"][0]["path"] = "not-listed.py"
    elif mutation == "empty":
        data["repositories"] = []
    elif mutation == "unknown_field":
        data["ready_for_training"] = True
    else:
        data["schema_version"] = "unknown"
    with pytest.raises(ValueError):
        rewrite(path, data)


def test_duplicate_json_keys_rejected(source_fixture):
    _, _, path, _ = source_fixture
    path.write_text('{"schema_version": "a", "schema_version": "b"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_baseline(path)


def test_identity_is_order_independent_and_payload_is_copy_safe(source_fixture):
    _, _, path, data = source_fixture
    baseline = load_baseline(path)
    before = baseline.to_payload()
    before["repositories"][0]["commit"] = "0" * 40
    assert baseline.to_payload()["repositories"][0]["commit"] != "0" * 40
    reordered = dict(reversed(list(data.items())))
    assert rewrite(path, reordered).manifest_sha256 == baseline.manifest_sha256
    data["limitations"].append("additional limitation")
    assert rewrite(path, data).manifest_sha256 != baseline.manifest_sha256


def test_real_manifest_covers_distinct_producers_without_readiness_claim():
    report = load_baseline(MANIFEST).to_payload()
    assert len(report["repositories"]) == 6
    assert {p["id"] for p in report["producers"]} == {
        "tree:house", "tree:strict", "engine:intraday", "engine:swing",
        "level_reversal:5m", "level_reversal:15m", "trend_reaction:5m", "trend_reaction:15m",
    }
    assert report["ready_for_training"] is False


def test_cli_inventory_and_required_verification_exit_codes(source_fixture):
    root, _, path, _ = source_fixture
    command = [sys.executable, str(ROOT / "tools/inspect_alert_baseline.py"), "--manifest", str(path)]
    inventory = subprocess.run(command, capture_output=True, text=True)
    assert inventory.returncode == 0, inventory.stderr
    assert json.loads(inventory.stdout)["source_verified"] is False
    blocked = subprocess.run(command + ["--require-source-verified"], capture_output=True, text=True)
    assert blocked.returncode == 2
    verified = subprocess.run(command + ["--root", str(root), "--require-source-verified"], capture_output=True, text=True)
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["ready_for_training"] is False
    path.write_text("{}", encoding="utf-8")
    invalid = subprocess.run(command, capture_output=True, text=True)
    assert invalid.returncode == 1


def test_assume_unchanged_does_not_hide_changed_source(source_fixture):
    root, repo, path, _ = source_fixture
    git(repo, "update-index", "--assume-unchanged", "calc.py")
    (repo / "calc.py").write_text("silently_changed = True\n", encoding="utf-8")
    assert verify_checkouts(load_baseline(path), root)["source_verified"] is False


def test_inspection_preserves_index_when_stat_metadata_changed(source_fixture):
    root, repo, path, _ = source_fixture
    file = repo / "calc.py"
    index = repo / ".git/index"
    stat = file.stat()
    os.utime(file, ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))
    before = index.read_bytes()
    report = verify_checkouts(load_baseline(path), root)
    assert report["source_verified"] is True
    assert index.read_bytes() == before


@pytest.mark.parametrize("filename", ["calc.py", " filtered.py"])
def test_external_filters_are_not_executed(source_fixture, filename):
    root, repo, path, data = source_fixture
    if filename != "calc.py":
        (repo / filename).write_text("synthetic = True\n", encoding="utf-8")
        git(repo, "add", "--", filename)
    (repo / ".gitattributes").write_text(f'"{filename}" filter=probe\n', encoding="utf-8")
    git(repo, "add", ".gitattributes")
    git(repo, "-c", "core.hooksPath=", "commit", "-qm", "attributes")
    data["repositories"][0]["commit"] = git(repo, "rev-parse", "HEAD")
    rewrite(path, data)
    git(repo, "config", "filter.probe.clean", "echo invoked >> filter.marker; cat")
    file = repo / filename
    stat = file.stat()
    os.utime(file, ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))
    report = verify_checkouts(load_baseline(path), root)
    assert not (repo / "filter.marker").exists()
    assert report["source_verified"] is False
    assert "EXTERNAL_GIT_FILTER" in report["repositories"][0]["blockers"]


def test_missing_promisor_object_never_invokes_remote_helper(source_fixture, monkeypatch):
    root, repo, path, data = source_fixture
    # Missing pinned object must not start the configured remote helper.
    helper = repo / "git-remote-probe"
    helper.write_text("#!/bin/sh\necho invoked >> remote.marker\nexit 1\n", encoding="utf-8")
    helper.chmod(0o755)
    monkeypatch.setenv("PATH", str(repo) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "probe")
    git(repo, "config", "extensions.partialClone", "origin")
    git(repo, "config", "remote.origin.promisor", "true")
    git(repo, "config", "remote.origin.url", "probe::fixture")
    data["repositories"][0]["commit"] = "1" * 40
    rewrite(path, data)
    # This smoke case also remains blocked without contacting any real network.
    report = verify_checkouts(load_baseline(path), root)
    assert report["source_verified"] is False
    assert not (repo / "remote.marker").exists()


def test_manifest_list_order_does_not_change_identity(source_fixture):
    _, _, path, data = source_fixture
    extra = copy.deepcopy(data["repositories"][0])
    extra.update(name="other-desk", url="https://github.com/fixture/other-desk")
    data["repositories"].append(extra)
    data["repositories"][0]["sources"].append({"path": "more.py", "symbol": "second", "role": "context"})
    data["producers"].append({"id": "other", "repository": "other-desk", "path": "calc.py"})
    data["limitations"].append("Second limitation")
    original = rewrite(path, data).manifest_sha256
    for repo in data["repositories"]:
        repo["sources"].reverse()
    for field in ("repositories", "producers", "limitations"):
        data[field].reverse()
    assert rewrite(path, data).manifest_sha256 == original
