"""Bootstrap conflict/idempotence checks use real Git and local transport only."""

import ast
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess

import pytest

from tools import prepare_tree_sources as prepare
from trading_system.tree_spec.baseline import load_baseline


ROOT = Path(__file__).resolve().parents[2]


def git(path, *args):
    return subprocess.check_output(
        ["git", "-c", "core.hooksPath=", "-c", "commit.gpgsign=false",
         "-C", str(path), *args], text=True, encoding="utf-8",
    ).strip()


@pytest.fixture
def local_source(tmp_path, monkeypatch):
    origin = tmp_path / "local-origin"
    origin.mkdir()
    git(origin, "init", "-q")
    git(origin, "config", "core.autocrlf", "false")
    git(origin, "config", "user.name", "Source fixture")
    git(origin, "config", "user.email", "fixture@example.invalid")
    (origin / "source.py").write_bytes(b"raise RuntimeError('never execute source')\n")
    git(origin, "add", "source.py")
    git(origin, "commit", "-qm", "pinned")
    pin = git(origin, "rev-parse", "HEAD")
    (origin / "source.py").write_bytes(b"raise RuntimeError('later, not pinned')\n")
    git(origin, "commit", "-qam", "later")
    url = "https://github.com/fixture/sample-desk"
    data = {
        "schema_version": "existing-alerts-baseline-v1", "baseline_id": "fixture",
        "repositories": [{
            "name": "sample-desk", "url": url, "commit": pin,
            "sources": [{"path": "source.py", "symbol": "module", "role": "audit"}],
        }],
        "producers": [{"id": "test", "repository": "sample-desk", "path": "source.py"}],
        "limitations": ["synthetic fixture"],
    }
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    baseline = load_baseline(manifest)
    run = subprocess.run
    calls = []

    def local_transport(command, **kwargs):
        # Real clone/checkout/status; replace only transport. Any attempted
        # network access is denied, even if the URL rewrite fails.
        env = dict(kwargs.get("env", os.environ))
        env["GIT_ALLOW_PROTOCOL"] = "file"
        kwargs["env"] = env
        command = list(command)
        calls.append(command)
        if "clone" in command or "fetch" in command:
            command[1:1] = ["-c", f"url.{origin.as_uri()}.insteadOf={url}"]
        return run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", local_transport)
    return baseline, manifest, tmp_path / "checkouts", origin, calls


def test_clone_exact_old_pin_with_lf_and_idempotent_reuse(local_source):
    baseline, _, root, _, calls = local_source
    [checkout] = prepare.prepare_sources(baseline, root)
    assert git(checkout, "rev-parse", "HEAD") == baseline.repositories[0].commit
    assert git(checkout, "config", "--local", "core.autocrlf") == "false"
    assert git(checkout, "config", "--local", "remote.origin.url") == baseline.repositories[0].url
    assert (checkout / "source.py").read_bytes() == b"raise RuntimeError('never execute source')\n"
    index_before = (checkout / ".git/index").read_bytes()
    config_before = (checkout / ".git/config").read_bytes()
    calls.clear()
    assert prepare.prepare_sources(baseline, root) == [checkout]
    assert not any("clone" in command or "checkout" in command for command in calls)
    assert (checkout / ".git/index").read_bytes() == index_before
    assert (checkout / ".git/config").read_bytes() == config_before
    assert not list(root.glob(".prepare-tree-*"))


@pytest.mark.parametrize("conflict", [
    "tracked", "untracked", "staged", "wrong-commit", "wrong-origin", "autocrlf",
    "masked", "filter",
])
def test_existing_conflicts_are_not_changed(local_source, conflict):
    baseline, _, root, origin, calls = local_source
    [checkout] = prepare.prepare_sources(baseline, root)
    source = checkout / "source.py"
    if conflict in {"tracked", "staged", "masked"}:
        source.write_bytes(b"keep my edits\n")
        if conflict == "staged":
            git(checkout, "add", "source.py")
        elif conflict == "masked":
            git(checkout, "update-index", "--assume-unchanged", "source.py")
    elif conflict == "untracked":
        (checkout / "personal.txt").write_text("keep me", encoding="utf-8")
    elif conflict == "wrong-commit":
        git(checkout, "checkout", "--detach", git(origin, "rev-parse", "HEAD"))
    elif conflict == "wrong-origin":
        git(checkout, "remote", "set-url", "origin", "https://github.com/other/sample-desk")
    elif conflict == "autocrlf":
        git(checkout, "config", "core.autocrlf", "true")
    elif conflict == "filter":
        (checkout / ".git/info").mkdir(exist_ok=True)
        (checkout / ".git/info/attributes").write_text("*.py filter=unsafe\n", encoding="utf-8")
        git(checkout, "config", "filter.unsafe.clean", "this-must-never-run")
    before = {path.relative_to(checkout): path.read_bytes()
              for path in checkout.rglob("*") if path.is_file()}
    calls.clear()
    with pytest.raises(ValueError, match="Refusing"):
        prepare.prepare_sources(baseline, root)
    after = {path.relative_to(checkout): path.read_bytes()
             for path in checkout.rglob("*") if path.is_file()}
    assert after == before
    assert not any("clone" in command or "checkout" in command for command in calls)


@pytest.mark.parametrize("kind", ["file", "empty-directory", "nested-repository"])
def test_wrong_destination_is_preserved(local_source, kind):
    baseline, _, root, origin, _ = local_source
    if kind == "nested-repository":
        root = origin
    root.mkdir(exist_ok=True)
    checkout = root / "sample-desk"
    if kind == "file":
        checkout.write_text("keep", encoding="utf-8")
    else:
        checkout.mkdir()
    with pytest.raises(ValueError):
        prepare.prepare_sources(baseline, root)
    assert checkout.exists()
    if kind == "file":
        assert checkout.read_text(encoding="utf-8") == "keep"
    else:
        assert list(checkout.iterdir()) == []


def test_preflight_checks_all_destinations_before_cloning(local_source):
    baseline, _, root, _, calls = local_source
    root.mkdir()
    (root / "z-conflict").mkdir()
    second = replace(baseline.repositories[0], name="z-conflict")
    baseline = replace(baseline, repositories=(*baseline.repositories, second))
    with pytest.raises(ValueError):
        prepare.prepare_sources(baseline, root)
    assert not (root / "sample-desk").exists()
    assert not any("clone" in command for command in calls)


def test_failed_clone_leaves_no_destination(local_source, monkeypatch):
    baseline, _, root, _, _ = local_source

    def failed_clone(*args, **kwargs):
        raise ValueError("synthetic transport failure")

    monkeypatch.setattr(prepare, "_git", failed_clone)
    with pytest.raises(ValueError, match="transport failure"):
        prepare.prepare_sources(baseline, root)
    assert list(root.iterdir()) == []


def test_credential_helpers_are_url_matched_transient_and_not_inherited_by_checkout(
    local_source, monkeypatch, tmp_path,
):
    baseline, _, root, _, calls = local_source
    config = tmp_path / "operator.gitconfig"
    config.write_text(
        '[credential]\n    helper = !unmatched-helper\n'
        '[credential "https://github.com"]\n'
        '    helper =\n'
        '    helper = !fixture-helper-must-not-run-on-local-transport\n'
        '[core]\n    autocrlf = true\n', encoding="utf-8",
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    [checkout] = prepare.prepare_sources(baseline, root)
    clone = next(command for command in calls if "clone" in command)
    assert "credential.helper=!unmatched-helper" not in clone
    assert "credential.helper=!fixture-helper-must-not-run-on-local-transport" in clone
    assert "credential" not in (checkout / ".git/config").read_text(encoding="utf-8")
    assert git(checkout, "config", "--local", "core.autocrlf") == "false"
    calls.clear()
    prepare.prepare_sources(baseline, root)
    assert not any("--get-urlmatch" in command for command in calls)


def test_missing_full_commit_leaves_no_partial_checkout(local_source):
    baseline, _, root, _, _ = local_source
    pin = replace(baseline.repositories[0], commit="a" * 40)
    with pytest.raises(ValueError, match="Git failed"):
        prepare.prepare_sources(replace(baseline, repositories=(pin,)), root)
    assert list(root.iterdir()) == []


def test_fetches_exact_pin_not_reachable_from_advertised_heads(local_source):
    baseline, _, root, origin, calls = local_source
    old_pin = baseline.repositories[0].commit
    unreachable = git(origin, "commit-tree", f"{old_pin}^{{tree}}", "-p", old_pin,
                      "-m", "unadvertised fixture commit")
    pin = replace(baseline.repositories[0], commit=unreachable)
    [checkout] = prepare.prepare_sources(replace(baseline, repositories=(pin,)), root)
    assert git(checkout, "rev-parse", "HEAD") == unreachable
    assert any(command[-4:] == ["fetch", "--no-tags", "origin", unreachable]
               for command in calls)
    assert (checkout / "source.py").read_bytes() == b"raise RuntimeError('never execute source')\n"


def test_redirected_checkout_is_refused(local_source):
    baseline, _, root, origin, calls = local_source
    root.mkdir()
    checkout = root / "sample-desk"
    try:
        checkout.symlink_to(origin, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable to this account")
    with pytest.raises(ValueError, match="redirected checkout"):
        prepare.prepare_sources(baseline, root)
    assert checkout.is_symlink()
    assert not calls


def test_cli_manifest_default_env_and_explicit_root(local_source, monkeypatch, capsys):
    baseline, manifest, root, _, _ = local_source
    monkeypatch.delenv("TR_TREE_SOURCE_ROOT", raising=False)
    assert prepare.default_source_root() == ROOT / ".source-checkouts"
    monkeypatch.setenv("TR_TREE_SOURCE_ROOT", str(root))
    assert prepare.main(["--manifest", str(manifest)]) == 0
    assert baseline.repositories[0].commit in capsys.readouterr().out
    explicit = root.parent / "explicit"
    assert prepare.main(["--manifest", str(manifest), "--source-root", str(explicit)]) == 0
    assert (explicit / "sample-desk/source.py").is_file()


def test_cli_rejects_abbreviated_pin_before_creating_root(local_source, capsys):
    _, manifest, root, _, calls = local_source
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["repositories"][0]["commit"] = data["repositories"][0]["commit"][:12]
    manifest.write_text(json.dumps(data), encoding="utf-8")
    assert prepare.main(["--manifest", str(manifest), "--source-root", str(root)]) == 2
    assert "full lowercase SHA1" in capsys.readouterr().err
    assert not root.exists()
    assert not calls


def test_production_manifest_has_six_full_pins():
    baseline = load_baseline(prepare.MANIFEST)
    assert len(baseline.repositories) == 6
    assert all(len(pin.commit) == 40 for pin in baseline.repositories)


@pytest.mark.parametrize("tree_override,chart_override", [
    (None, None), ("custom-tree", None), (None, "custom-chart"),
    ("custom-tree", "custom-chart"),
])
def test_all_source_defaults_are_portable_and_honor_overrides(
    monkeypatch, tmp_path, tree_override, chart_override,
):
    # Evaluate only the path expression, without importing or executing test
    # modules or their source fixtures. Changing CWD must not change defaults.
    monkeypatch.chdir(tmp_path)
    for name, value in (("TR_TREE_SOURCE_ROOT", tree_override),
                        ("TR_CHARTDESK_SOURCE_ROOT", chart_override)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    count = 0
    for directory in (ROOT / "tests/tree_replay", ROOT / "tests/tree_spec"):
        for path in directory.glob("test_*.py"):
            if path.name == Path(__file__).name:
                continue
            text = path.read_text(encoding="utf-8")
            assert "4efd65cf2e284d97a81199af6195f149" not in text
            for node in ast.parse(text).body:
                if not isinstance(node, ast.Assign):
                    continue
                expression = ast.get_source_segment(text, node.value)
                if ".source-checkouts" not in expression:
                    continue
                count += 1
                expected = Path(tree_override) if tree_override else ROOT / ".source-checkouts"
                if "TR_CHARTDESK_SOURCE_ROOT" in expression:
                    expected = Path(chart_override) if chart_override else expected / "chart-desk"
                result = eval(compile(ast.Expression(node.value), str(path), "eval"),
                              {"Path": Path, "os": os, "__file__": str(path)})
                assert result == expected, path
    assert count == 42
