from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from trading_system.candidates.generation import generate_fixture_candidate
from trading_system.candidates.labeling import build_fixture_trade_contract, label_long_candidate
from trading_system.data_foundation.contracts import NormalizedBar
from trading_system.data_foundation.csv_onboarding import build_raw_source_manifest_for_csv
from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.data_foundation.normalization import (
    NormalizationPolicy,
    SymbolMap,
    normalize_ohlcv_row,
    read_csv_rows,
)
from trading_system.datasets.factory import build_candidate_training_row
from trading_system.datasets.splits import ChronologicalSplitBoundaries, assign_chronological_split
from trading_system.features.contracts import utc_iso
from trading_system.features.market_state import build_unified_market_state
from trading_system.models.baseline import train_majority_baseline
from trading_system.models.contracts import ModelTrainingRun
from trading_system.models.readiness import TrainingPolicy

RUN_VERSION = "offline-research-run-0.1.0"
MODE = "LOCAL_CSV_DRY_RUN"
SAFETY_STATUS = "BLOCKED_FOR_RESEARCH_ONLY"
BLOCKED_ACTIONS = (
    "PRODUCTION_VENDOR_APPROVAL",
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
)
BLOCKED_REASONS = (
    "PRODUCTION_SOURCE_NOT_APPROVED",
    "LOCAL_CSV_DRY_RUN_ONLY",
    "NO_HUMAN_MODEL_PROMOTION_APPROVAL",
)
FIXTURE_DRY_RUN_SOURCE_ID = "local-csv-ohlcv-fixture"
FIXTURE_DRY_RUN_SYMBOL = "TR_FIXTURE_SPY"


@dataclass(frozen=True)
class OfflineResearchRun:
    run_id: str
    created_at: datetime
    raw_source_manifest: dict[str, Any]
    normalized_bar_count: int
    snapshot_count: int
    candidate_count: int
    training_row_count: int
    included_training_row_count: int
    training_run: ModelTrainingRun

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "run_version": RUN_VERSION,
            "mode": MODE,
            "created_at": utc_iso(self.created_at),
            "raw_source_manifest": self.raw_source_manifest,
            "normalized_bar_count": self.normalized_bar_count,
            "snapshot_count": self.snapshot_count,
            "candidate_count": self.candidate_count,
            "training_row_count": self.training_row_count,
            "included_training_row_count": self.included_training_row_count,
            "training_run": self.training_run.to_payload(),
            "safety_status": SAFETY_STATUS,
            "blocked_actions": list(BLOCKED_ACTIONS),
            "blocked_reasons": list(BLOCKED_REASONS),
        }


def _normalize_records(
    csv_path: Path,
    metadata: Mapping[str, Any],
    policy: NormalizationPolicy,
    symbol_map: SymbolMap,
) -> list[NormalizedBar]:
    records = [
        normalize_ohlcv_row(
            row,
            policy,
            symbol_map,
            source_id=str(metadata["source_id"]),
            source_version=str(metadata["schema_version"]),
        )
        for row in read_csv_rows(csv_path)
    ]
    return sorted(records, key=lambda record: (record.observed_at, record.available_at, record.raw_symbol))


def _require_fixture_dry_run_identity(metadata: Mapping[str, Any]) -> None:
    if (
        metadata.get("source_id") != FIXTURE_DRY_RUN_SOURCE_ID
        or metadata.get("canonical_symbol") != FIXTURE_DRY_RUN_SYMBOL
    ):
        raise ValueError(
            "fixture-only dry-run requires source_id "
            f"'{FIXTURE_DRY_RUN_SOURCE_ID}' and canonical_symbol "
            f"'{FIXTURE_DRY_RUN_SYMBOL}'"
        )


def _split_boundaries(records: list[NormalizedBar]) -> ChronologicalSplitBoundaries:
    observed_times = sorted({record.observed_at for record in records})
    if len(observed_times) < 3:
        raise ValueError("local CSV dry-run requires at least three distinct observed timestamps")
    train_index = max(0, (len(observed_times) // 3) - 1)
    validation_index = max(train_index + 1, ((len(observed_times) * 2) // 3) - 1)
    return ChronologicalSplitBoundaries(
        train_end=observed_times[train_index],
        validation_end=observed_times[validation_index],
    )


def _bar_for_snapshot(records: list[NormalizedBar], observed_at: str) -> NormalizedBar:
    matches = [record for record in records if utc_iso(record.observed_at) == observed_at]
    if not matches:
        raise ValueError(f"no normalized bar for snapshot observed_at {observed_at}")
    return max(matches, key=lambda record: record.available_at)


def _run_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def build_local_csv_research_dry_run(
    csv_path: Path,
    metadata: Mapping[str, Any],
    policy: NormalizationPolicy,
    symbol_map: SymbolMap,
    training_policy: TrainingPolicy,
    *,
    created_at: datetime,
) -> OfflineResearchRun:
    _require_fixture_dry_run_identity(metadata)
    raw_manifest = build_raw_source_manifest_for_csv(
        csv_path,
        metadata,
        policy,
        symbol_map,
        ingested_at=created_at,
    )
    records = _normalize_records(csv_path, metadata, policy, symbol_map)
    boundaries = _split_boundaries(records)
    source_hashes = {str(raw_manifest["source_id"]): str(raw_manifest["raw_file_sha256"])}
    snapshots = [
        build_unified_market_state(
            records,
            str(raw_manifest["canonical_symbol"]),
            record.available_at,
            computed_at=created_at,
        )
        for record in sorted(records, key=lambda item: item.available_at)
    ]

    candidates = [generate_fixture_candidate(snapshot, created_at=created_at) for snapshot in snapshots]
    rows = []
    for snapshot, candidate in zip(snapshots, candidates):
        observed_at = str(snapshot.feature_values["data.observed_at"].value)
        current_bar = _bar_for_snapshot(records, observed_at)
        future_bars = [
            record
            for record in records
            if record.canonical_symbol == current_bar.canonical_symbol and record.observed_at > current_bar.observed_at
        ]
        contract = build_fixture_trade_contract(current_bar) if candidate.status == "ELIGIBLE" else None
        label = label_long_candidate(candidate, contract, future_bars) if contract is not None else None
        rows.append(
            build_candidate_training_row(
                snapshot,
                candidate,
                contract,
                label,
                split=assign_chronological_split(snapshot.observation_time, boundaries),
                source_hashes=source_hashes,
            )
        )

    training_run = train_majority_baseline(rows, training_policy, created_at=created_at)
    id_payload = {
        "created_at": utc_iso(created_at),
        "raw_file_sha256": raw_manifest["raw_file_sha256"],
        "training_row_ids": [row.row_id for row in rows],
        "training_run_id": training_run.run_id,
    }
    return OfflineResearchRun(
        run_id=_run_id(id_payload),
        created_at=created_at,
        raw_source_manifest=raw_manifest,
        normalized_bar_count=len(records),
        snapshot_count=len(snapshots),
        candidate_count=len(candidates),
        training_row_count=len(rows),
        included_training_row_count=sum(1 for row in rows if row.included_in_training),
        training_run=training_run,
    )
