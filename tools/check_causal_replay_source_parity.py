"""CLI for the static market-watch closed-bar causal replay source audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.tree_spec.causal_replay_source import check_source_parity


def _blocked(exc):
    return {
        "status": "BLOCKED", "source_subset_verified": False,
        "blockers": [f"AUDIT_UNREADABLE:{type(exc).__name__}"],
        "checked_projections": [], "projection": {}, "source_commits": {},
        "ready_for_replay": False, "ready_for_training": False,
    }


def _valid_report(report):
    if not (isinstance(report, dict) and report.get("status") in {"VERIFIED", "BLOCKED"}
            and type(report.get("source_subset_verified")) is bool
            and isinstance(report.get("blockers"), list)
            and all(isinstance(row, str) and row for row in report["blockers"])
            and isinstance(report.get("checked_projections"), list)
            and isinstance(report.get("projection"), dict)
            and isinstance(report.get("source_commits"), dict)
            and report.get("ready_for_replay") is False
            and report.get("ready_for_training") is False):
        return False
    try:
        json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return ((report["status"] == "VERIFIED") == (report["source_subset_verified"] is True and report["blockers"] == []))


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    try:
        parser = _Parser()
        parser.add_argument("--source-root", required=True)
        args = parser.parse_args(argv)
        report = check_source_parity(Path(args.source_root))
        if not _valid_report(report):
            raise TypeError("AUDIT_REPORT_SHAPE")
    except BaseException as exc:
        report = _blocked(exc)
    try:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
    except BaseException as exc:
        print(json.dumps(_blocked(exc), ensure_ascii=False, sort_keys=True, allow_nan=False))
        report = _blocked(exc)
    return 0 if report.get("status") == "VERIFIED" and report.get("source_subset_verified") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
