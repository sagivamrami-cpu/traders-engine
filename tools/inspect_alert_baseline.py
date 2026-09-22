"""Read-only source inventory; never runs or authorizes the trading system."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trading_system.tree_spec.baseline import load_baseline, verify_checkouts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "configs/trees/existing-alerts-baseline.json")
    parser.add_argument("--root", type=Path, help="Directory containing the six pinned checkouts")
    parser.add_argument("--require-source-verified", action="store_true")
    args = parser.parse_args()
    try:
        baseline = load_baseline(args.manifest)
        report = verify_checkouts(baseline, args.root) if args.root else baseline.to_payload()
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2))
    return 2 if args.require_source_verified and not report["source_verified"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
