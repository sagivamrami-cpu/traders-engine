"""Verify the retained tracker lifecycle caller seam without executing retained source."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.tree_spec.tracker_lifecycle_caller_source import (  # noqa: E402
    audit_tracker_lifecycle_caller_source,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True)
    args = parser.parse_args(argv)
    try:
        report = audit_tracker_lifecycle_caller_source(Path(args.source_root))
    except Exception as exc:
        report = {
            "status": "BLOCKED", "source_subset_verified": False,
            "blockers": [f"AUDIT_UNREADABLE:{type(exc).__name__}"],
            "checked_projections": [], "dependencies": {}, "source_commits": {},
            "ready_for_replay": False, "ready_for_training": False,
        }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["source_subset_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
