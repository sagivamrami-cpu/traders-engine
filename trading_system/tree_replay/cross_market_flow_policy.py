"""Pinned policy for CME GC flow used only as XAUUSD research context."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from trading_system.data_foundation.manifests import load_json


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/xauusd_gc_crossmarket_order_flow_context.schema.json"


def _utc(value: object, name: str) -> datetime:
    if type(value) is not str:
        raise ValueError(f"CROSS_MARKET_POLICY:{name}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"CROSS_MARKET_POLICY:{name}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError(f"CROSS_MARKET_POLICY:{name}")
    return parsed.astimezone(UTC)


@dataclass(frozen=True, kw_only=True)
class CrossMarketFlowPolicy:
    target_instrument: str
    source_instrument: str
    source_dataset: str
    archive_sha256: str
    selected_member: str
    allowed_columns: tuple[str, ...]
    damaged_start: datetime
    damaged_end: datetime

    @classmethod
    def load(cls, path: Path) -> "CrossMarketFlowPolicy":
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("policy must be a mapping")
            schema = load_json(SCHEMA_PATH)
            Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)
            damaged = payload["damaged_window"]
            if not isinstance(damaged, dict):
                raise ValueError("damaged window must be a mapping")
            start = _utc(damaged["start"], "damaged_start")
            end = _utc(damaged["end"], "damaged_end")
            if not start < end:
                raise ValueError("damaged window must be ordered")
            return cls(
                target_instrument=str(payload["target_instrument"]),
                source_instrument=str(payload["source_instrument"]),
                source_dataset=str(payload["source_dataset"]),
                archive_sha256=str(payload["archive_sha256"]),
                selected_member=str(payload["selected_member"]),
                allowed_columns=tuple(payload["allowed_columns"]),
                damaged_start=start,
                damaged_end=end,
            )
        except (OSError, TypeError, ValidationError, ValueError, yaml.YAMLError) as exc:
            if isinstance(exc, ValueError) and str(exc).startswith("CROSS_MARKET_POLICY"):
                raise
            raise ValueError("CROSS_MARKET_POLICY") from exc
