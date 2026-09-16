"""CLI for the inert full-tree supplied-evidence capture audit."""
from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.tree_spec.full_tree_capture_source import check_full_tree_capture_source


def main() -> int:
    report = check_full_tree_capture_source()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    return 0 if report["source_subset_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
