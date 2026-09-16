"""Prepare pinned audit sources without importing or running their Python code.

Existing checkouts are verified, never repaired. New clones use isolated Git
configuration, disabled hooks, and LF checkout behavior. No dependencies are
installed and no submodules are initialized.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trading_system.tree_spec.baseline import load_baseline, verify_checkouts


MANIFEST = ROOT / "configs/trees/existing-alerts-baseline.json"


def default_source_root() -> Path:
    return Path(os.environ.get("TR_TREE_SOURCE_ROOT", ROOT / ".source-checkouts"))


def _credential_options(url: str) -> list[str]:
    # Read only the operator's effective URL-matched helper. Authentication may be
    # needed even for an originally public source; never read/print tokens or
    # copy credentials into the new checkout. Helpers run only if Git needs them.
    result = subprocess.run(
        ["git", "config", "--null", "--get-urlmatch", "credential.helper", url],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=15,
        check=False,
    )
    if result.returncode == 1:
        return []
    if result.returncode:
        raise ValueError("Could not read configured Git credential helpers")
    return [item for helper in result.stdout.split("\0")[:-1]
            for item in ("-c", f"credential.helper={helper}")]


def _git(path: Path, *args: str, credential_url: str | None = None) -> str:
    # Keep templates, filters, URL rewrites and GIT_DIR overrides isolated.
    # Network operations may use only the configured credential helper.
    credential_options = _credential_options(credential_url) if credential_url else []
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_TERMINAL_PROMPT="0",
        GIT_ALLOW_PROTOCOL="https",
        GIT_NO_LAZY_FETCH="1",
        GIT_OPTIONAL_LOCKS="0",
        GCM_INTERACTIVE="never",
    )
    result = subprocess.run(
        ["git", "--no-replace-objects", *credential_options, "-c", "core.hooksPath=",
         "-c", "core.fsmonitor=false", "-C", str(path), *args],
        env=env, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=300, check=False,
    )
    if result.returncode:
        raise ValueError(f"Git failed in {path}: {result.stderr.strip() or ' '.join(args)}")
    return result.stdout.strip()


def _verify(baseline, pin, root: Path) -> None:
    checkout = root / pin.name
    if checkout.is_symlink() or checkout.resolve().parent != root.resolve():
        raise ValueError(f"Refusing redirected checkout: {checkout}")
    # Reuse the existing audit verifier, including full SHA identity, exact
    # repository root, untracked files, hidden index changes and filter checks.
    report = verify_checkouts(replace(baseline, repositories=(pin,)), root)
    if not report["source_verified"]:
        blockers = report["repositories"][0]["blockers"]
        raise ValueError(f"Refusing existing checkout {checkout}: {', '.join(blockers)}")
    origin = _git(checkout, "config", "--local", "--get", "remote.origin.url")
    if origin.rstrip("/").removesuffix(".git") != pin.url.rstrip("/").removesuffix(".git"):
        raise ValueError(f"Refusing checkout with wrong origin: {checkout}")
    if _git(checkout, "config", "--local", "--bool", "--get", "core.autocrlf") != "false":
        raise ValueError(f"Refusing checkout without local core.autocrlf=false: {checkout}")


def prepare_sources(baseline, source_root: Path) -> list[Path]:
    """Prepare a validated baseline (from load_baseline); reject conflicts first."""
    root = Path(source_root).absolute()
    if root.is_symlink() or root.resolve() != root:
        raise ValueError(f"Refusing redirected or noncanonical source root: {root}")
    if root.exists() and not root.is_dir():
        raise ValueError(f"Source root is not a directory: {root}")

    # Check *all* occupied destinations before creating any new checkouts.
    for pin in baseline.repositories:
        checkout = root / pin.name
        if checkout.exists() or checkout.is_symlink():
            _verify(baseline, pin, root)

    root.mkdir(parents=True, exist_ok=True)
    prepared = []
    for pin in baseline.repositories:
        checkout = root / pin.name
        if not checkout.exists():
            # A failed fetch/checkout only removes this owned temporary clone.
            # Never reset, clean, pull, or change config in an existing checkout.
            with tempfile.TemporaryDirectory(prefix=".prepare-tree-", dir=root) as stage:
                stage_root = Path(stage)
                staged = stage_root / pin.name
                _git(stage_root, "clone", "--no-checkout", "--no-local", "--template=",
                     "--config", "core.autocrlf=false", "--", pin.url, str(staged),
                     credential_url=pin.url)
                try:
                    _git(staged, "cat-file", "-e", f"{pin.commit}^{{commit}}")
                except ValueError:
                    # A pin may no longer be reachable from advertised heads.
                    # Request the exact full identity; never substitute HEAD.
                    _git(staged, "fetch", "--no-tags", "origin", pin.commit,
                         credential_url=pin.url)
                _git(staged, "checkout", "--detach", pin.commit)
                _verify(baseline, pin, stage_root)
                if checkout.exists() or checkout.is_symlink():
                    raise ValueError(f"Destination appeared during preparation: {checkout}")
                staged.rename(checkout)
        prepared.append(checkout)
    return prepared


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=default_source_root(),
                        help="Checkout parent (default: TR_TREE_SOURCE_ROOT or repository .source-checkouts)")
    parser.add_argument("--manifest", type=Path, default=MANIFEST,
                        help="Pinned source manifest (default: existing-alerts-baseline.json)")
    args = parser.parse_args(argv)
    try:
        baseline = load_baseline(args.manifest)
        paths = prepare_sources(baseline, args.source_root)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"Source preparation failed: {exc}", file=sys.stderr)
        return 2
    for pin, path in zip(baseline.repositories, paths):
        print(f"Verified {pin.name} {pin.commit} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
