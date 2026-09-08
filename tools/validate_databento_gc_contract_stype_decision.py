from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.research.databento_contract_stype_decision import (
    load_databento_contract_stype_decision,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a Databento GC contract/stype decision.")
    parser.add_argument(
        "--decision",
        type=Path,
        default=ROOT / "configs/data/databento-gc-contract-stype-decision-template.yaml",
    )
    return parser.parse_args()


def main() -> int:
    try:
        decision = load_databento_contract_stype_decision(parse_args().decision)
    except Exception:
        print(json.dumps({"error": "DATABENTO_CONTRACT_STYPE_DECISION_INVALID", "status": "BLOCKED"}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(decision.to_payload(), ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
