"""Read-only CLI for the pinned pattern-reader graph."""
import argparse
import json
from pathlib import Path
import sys

if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from trading_system.tree_spec.pattern_readers_source import audit_pattern_readers_source


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    args=parser.parse_args()
    result=audit_pattern_readers_source(args.source_root)
    print(json.dumps(result,ensure_ascii=True,sort_keys=True,indent=2))
    return 0 if result['source_subset_verified'] else 2


if __name__=='__main__':
    raise SystemExit(main())
