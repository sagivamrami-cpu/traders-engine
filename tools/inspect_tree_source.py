"""Inspect pinned source evidence without executing scripts or training a model."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trading_system.tree_spec.catalog import load_catalog


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-ready", action="store_true", help="Exit 2 unless replay AND training are ready")
    parser.add_argument("--include-units", action="store_true", help="Include all guide evidence and source lines")
    args = parser.parse_args()
    try:
        manifest_path = ROOT / "docs/sources/tr-hybrid-intelligence-tree.manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        digest = manifest["sha256"]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise ValueError("manifest hash must be a 64-character SHA-256 hex string")
        catalog = load_catalog(manifest_path.parent / manifest["artifact"], digest)
        report = catalog.readiness(include_units=args.include_units)
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    # ASCII-safe JSON works in Windows legacy consoles and decodes back to Hebrew.
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if args.require_ready and not (report["ready_for_replay"] and report["ready_for_training"]):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
