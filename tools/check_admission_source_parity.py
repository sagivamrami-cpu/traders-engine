"""Audit admission calculations from an explicit pinned checkout parent root."""

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.tree_spec.admission_source import audit_admission_source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True,
                        help="Parent of pinned chart-desk and trading-floor checkouts")
    report = audit_admission_source(parser.parse_args().source_root)
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["source_subset_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
