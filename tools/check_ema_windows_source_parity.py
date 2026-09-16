"""Audit complete EMA windows, deep CSV reader and strict seeded EMA without execution."""
import argparse
import json
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trading_system.tree_spec.ema_windows_source import audit_ema_windows_source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True,
                        help='Explicit parent of the retained chart-desk checkout')
    report = audit_ema_windows_source(parser.parse_args().source_root)
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report['source_subset_verified'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
