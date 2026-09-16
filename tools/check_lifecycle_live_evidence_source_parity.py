"""CLI entrypoint for inert lifecycle live-evidence source verification."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.tree_spec.lifecycle_live_evidence_source import (
    audit_lifecycle_live_evidence_source,
)


def _blocked(exc):
    return {
        "status": "BLOCKED",
        "source_subset_verified": False,
        "blockers": [f"AUDIT_UNREADABLE:{type(exc).__name__}"],
        "checked_projections": [],
        "dependencies": {},
        "source_commits": {},
        "ready_for_replay": False,
        "ready_for_training": False,
    }


def _valid_report(report):
    basic = (
        isinstance(report, dict)
        and report.get("status") in {"VERIFIED", "BLOCKED"}
        and type(report.get("source_subset_verified")) is bool
        and isinstance(report.get("blockers"), list)
        and all(isinstance(row, str) for row in report["blockers"])
        and isinstance(report.get("checked_projections"), list)
        and isinstance(report.get("dependencies"), dict)
        and isinstance(report.get("source_commits"), dict)
        and report.get("ready_for_replay") is False
        and report.get("ready_for_training") is False
    )
    if not basic:
        return False
    if report["status"] == "VERIFIED":
        return report["source_subset_verified"] is True and report["blockers"] == []
    return report["source_subset_verified"] is False and bool(report["blockers"])


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    try:
        parser = _Parser()
        parser.add_argument("--source-root", required=True)
        args = parser.parse_args(argv)
        report = audit_lifecycle_live_evidence_source(Path(args.source_root))
        if not _valid_report(report):
            raise TypeError("AUDIT_REPORT_SHAPE")
    except Exception as exc:
        report = _blocked(exc)
    try:
        payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    except Exception as exc:
        report = _blocked(exc)
        try:
            payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        except Exception as fallback:
            payload = (
                '{"blockers":["AUDIT_UNREADABLE:' + type(fallback).__name__ + '"],'
                '"checked_projections":[],"dependencies":{},'
                '"ready_for_replay":false,"ready_for_training":false,'
                '"source_commits":{},"source_subset_verified":false,'
                '"status":"BLOCKED"}'
            )
            report = _blocked(fallback)
    print(payload)
    return 0 if (
        report.get("status") == "VERIFIED"
        and report.get("source_subset_verified") is True
    ) else 2


if __name__ == "__main__":
    raise SystemExit(main())
