from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from trading_system.data_foundation.hashing import sha256_file, stable_json_dumps
from trading_system.data_foundation.manifests import validate_json_payload
from trading_system.datasets.contracts import CandidateTrainingRow
from trading_system.features.contracts import utc_iso
from trading_system.models.readiness import TrainingReadinessResult, evaluate_training_readiness, load_training_policy
from trading_system.research.gc_real_dataset_contract import (
    build_gc_real_dataset_contract_report,
)
from trading_system.research.gc_real_dataset_build import load_build_manifest
from trading_system.research.readiness import (
    build_real_data_readiness_report,
    load_real_data_decisions,
    load_real_data_readiness_checklist,
)

REPORT_VERSION = "gc-pretraining-readiness-report-0.1.0"
MODE = "GC_PRETRAINING_READINESS"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas/gc_pretraining_readiness_report.schema.json"
HUMAN_DECISION_REQUEST = (
    "agent-exchange/inbox/human/2026-09-01T133200Z-human-phase-25-gc-dataset-gate-decisions.md"
)
BLOCKED_ACTIONS = (
    "BUILD_REAL_DATASET",
    "BUILD_ORDER_FLOW_FEATURES",
    "BUILD_CVD_FEATURES",
    "USE_ARCHIVED_CVD_COLUMN",
    "INGEST_PRECOMPUTED_CVD",
    "BUILD_MACRO_FEATURES",
    "USE_REVISED_MACRO_SERIES",
    "QUERY_OPTIONS_DATA",
    "INGEST_ORDERFLOW_4H_CSV",
    "JOIN_ORDERFLOW_4H_CSV_TO_TRAINING_ROWS",
    "USE_HHLL_AS_TRADE_CONTRACT_LABEL",
    "MAP_GC_TO_XAUUSD",
    "MAP_GC_TO_GLD",
    "INGEST_CONTINUOUS_OR_STITCHED_GC_SERIES",
    "TRAIN_PRODUCTION_MODEL",
    "CLAIM_EDGE",
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
)
PENDING_PROCESS_STEPS = (
    "COLLECT_HUMAN_GATE_DECISIONS",
    "PROCESS_PHASE24_EXTERNAL_REVIEWS",
    "PROCESS_LATEST_EXTERNAL_REVIEWS",
    "DESIGN_LABEL_AND_SPLIT_POLICY_CANDIDATES",
)
VARIANTS = ("ohlcv_only", "order_flow")
FEATURE_COLUMNS = {
    "ohlcv_only": (
        "close",
        "atr_14",
        "ret_1",
        "ret_4",
        "ret_8",
        "ret_14",
        "range_over_atr",
        "volume_30m",
        "seconds_with_trades",
    ),
    "order_flow": (
        "close",
        "atr_14",
        "ret_1",
        "ret_4",
        "ret_8",
        "ret_14",
        "range_over_atr",
        "volume_30m",
        "seconds_with_trades",
        "of_volume",
        "of_delta",
        "of_trades",
        "of_minutes_present",
        "of_volume_sum_14",
        "of_delta_sum_14",
        "of_trades_sum_14",
    ),
}


@dataclass(frozen=True)
class GcPretrainingReadinessReport:
    report_id: str
    created_at: datetime
    payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        validate_json_payload(SCHEMA_PATH, self.payload)
        return self.payload


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _report_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _safe_ref(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(Path(__file__).resolve().parents[2]).as_posix()
    except ValueError:
        return resolved.name


def _path_is_under_reviews(path: Path) -> bool:
    return _path_is_under_exchange_subdir(path, "reviews")


def _path_is_under_status(path: Path) -> bool:
    return _path_is_under_exchange_subdir(path, "status")


def _path_is_under_exchange_subdir(path: Path, subdir: str) -> bool:
    resolved = path.resolve()
    for parent in (resolved.parent, *resolved.parents):
        if parent.name == subdir and parent.parent.name == "agent-exchange":
            try:
                resolved.relative_to(parent.resolve())
            except ValueError:
                return False
            return True
    return False


def _valid_groq_phase24_review(path: Path | None, intake_path: Path | None) -> bool:
    if path is None or not path.exists() or not path.is_file():
        return False
    if not _path_is_under_reviews(path):
        return False
    text = path.read_text(encoding="utf-8")
    if "Reviewer:\nGroq" not in text and "Reviewer:\r\nGroq" not in text:
        return False
    if "phase-24" not in text.lower():
        return False
    if "Verdict:\nACCEPT" not in text and "Verdict:\r\nACCEPT" not in text:
        return False
    if intake_path is None or not intake_path.exists() or not intake_path.is_file():
        return False
    if not _path_is_under_status(intake_path):
        return False
    intake = intake_path.read_text(encoding="utf-8")
    if "Sender:\nCodex" not in intake and "Sender:\r\nCodex" not in intake:
        return False
    if "Status:\nACCEPTED_BY_CODEX" not in intake and "Status:\r\nACCEPTED_BY_CODEX" not in intake:
        return False
    return path.name in intake or path.as_posix() in intake or str(path) in intake


def _to_utc_datetime(value: Any) -> datetime:
    return pd.Timestamp(value).tz_convert("UTC").to_pydatetime()


def _none_if_missing(value: Any) -> Any:
    return None if pd.isna(value) else value


def candidate_rows_from_build_manifest(
    build_manifest_path: Path,
    *,
    rows_root: Path,
    variant: str,
) -> tuple[dict[str, Any], list[CandidateTrainingRow]]:
    if variant not in VARIANTS:
        raise ValueError(f"unknown GC dataset variant: {variant}")
    manifest = load_build_manifest(build_manifest_path)
    rows_path = rows_root / str(manifest["rows_relative_dir"]) / str(manifest["rows_file"])
    if not rows_path.is_file():
        raise FileNotFoundError("GC dataset rows parquet is missing for the build manifest")
    if sha256_file(rows_path) != manifest["rows_sha256"]:
        raise ValueError("GC dataset rows parquet hash does not match the build manifest")
    frame = pd.read_parquet(rows_path)
    if len(frame) != int(manifest["rows_count"]):
        raise ValueError("GC dataset rows count does not match the build manifest")
    if list(frame.columns) != list(manifest["rows_columns"]):
        raise ValueError("GC dataset rows columns do not match the build manifest")
    dataset_id = str(manifest["dataset_id"])
    feature_columns = FEATURE_COLUMNS[variant]
    included_column = f"included_{variant}"
    reasons_column = f"exclusion_reasons_{variant}"
    rows: list[CandidateTrainingRow] = []
    for record in frame.to_dict(orient="records"):
        reasons_value = record.get(reasons_column, "")
        reasons = tuple(str(reason) for reason in str(reasons_value).split("|") if reason)
        included = bool(record[included_column])
        candidate_id = str(record["candidate_id"])
        rows.append(
            CandidateTrainingRow(
                row_id=f"{candidate_id}:{variant}",
                dataset_id=dataset_id,
                dataset_version=str(record["dataset_version"]),
                snapshot_id=f"GC:30m:{pd.Timestamp(record['bar_start']).strftime('%Y%m%dT%H%M%SZ')}",
                candidate_id=candidate_id,
                symbol="GC",
                observation_time=_to_utc_datetime(record["bar_end"]),
                graph_id="gc-30m-outcome-contract",
                graph_version=str(manifest["builder_version"]),
                direction=str(record["direction"]),
                candidate_status="ELIGIBLE" if included else "REJECTED",
                features={column: _none_if_missing(record.get(column)) for column in feature_columns},
                feature_schema_version=str(manifest["feature_schema_version"]),
                contract_version=str(manifest["contract_version"]),
                label_version=str(manifest["label_version"]),
                outcome_class=_none_if_missing(record.get("outcome_class")),
                label_quality=str(record["label_quality"]),
                included_in_training=included,
                exclusion_reasons=reasons,
                split=str(record["split"]),
                source_hashes=dict(manifest["source_hashes"]),
                outcome_return_r=_none_if_missing(record.get("net_return_r")),
            )
        )
    return manifest, rows


def _readiness_payload(result: TrainingReadinessResult, variant: str) -> dict[str, Any]:
    return {
        "variant": variant,
        "ready": result.ready,
        "blocked_reasons": list(result.blocked_reasons),
        "split_summary": result.split_summary,
        "class_distribution": result.class_distribution,
    }


def build_gc_pretraining_readiness_report(
    *,
    contract_path: Path,
    decisions_path: Path,
    checklist_path: Path,
    training_policy_path: Path,
    created_at: datetime,
    groq_phase24_review_path: Path | None = None,
    groq_phase24_intake_path: Path | None = None,
    build_manifest_path: Path | None = None,
    rows_root: Path | None = None,
    variant: str = "order_flow",
) -> GcPretrainingReadinessReport:
    contract_report = build_gc_real_dataset_contract_report(
        contract_path,
        decisions_path,
        created_at=created_at,
    ).to_payload()
    checklist = load_real_data_readiness_checklist(checklist_path)
    decisions = load_real_data_decisions(decisions_path)
    real_data = build_real_data_readiness_report(
        checklist,
        created_at=created_at,
        decisions=decisions,
    ).to_payload()
    training_policy = load_training_policy(training_policy_path)
    rows_root = rows_root or (Path(__file__).resolve().parents[2] / "market-data/gc-30m-real")

    review_blockers = []
    if not _valid_groq_phase24_review(groq_phase24_review_path, groq_phase24_intake_path):
        review_blockers.append("GROQ_PHASE24_IMPLEMENTATION_REVIEW_PENDING")
    pending_steps = [
        "COLLECT_HUMAN_GATE_DECISIONS",
        *("PROCESS_PHASE24_EXTERNAL_REVIEWS" for _ in review_blockers[:1]),
        "PROCESS_LATEST_EXTERNAL_REVIEWS",
        "DESIGN_LABEL_AND_SPLIT_POLICY_CANDIDATES",
    ]

    construction_allowed = (
        contract_report["dataset_construction_allowed"] is True
        and contract_report["status"] == "CONSTRUCTION_AUTHORIZED_TRAINING_BLOCKED"
    )
    build_manifest: dict[str, Any] | None = None
    training_readiness: dict[str, Any] | None = None
    build_blockers: list[str] = []
    if construction_allowed and build_manifest_path is not None:
        try:
            build_manifest, rows = candidate_rows_from_build_manifest(
                build_manifest_path,
                rows_root=rows_root,
                variant=variant,
            )
            if build_manifest["dataset_id"] != contract_report["dataset_identity"]["dataset_id"]:
                build_blockers.append("BUILD_MANIFEST_DATASET_ID_MISMATCH")
            else:
                training_result = evaluate_training_readiness(rows, training_policy)
                training_readiness = _readiness_payload(training_result, variant)
                if not training_result.ready:
                    build_blockers.extend(training_result.blocked_reasons)
        except Exception:
            build_blockers.append("BUILD_MANIFEST_INVALID_OR_ROWS_UNREADABLE")
    real_dataset_built = bool(build_manifest is not None and not build_blockers)
    training_ready = bool(real_dataset_built and training_readiness and training_readiness["ready"] and not review_blockers)
    required_gates = _unique(
        [
            *contract_report["required_unsatisfied_gates"],
            *([] if construction_allowed else ["DATASET_CONSTRUCTION_AUTHORIZATION"]),
            *([] if real_dataset_built else ["REAL_DATASET_NOT_BUILT"]),
            *build_blockers,
            *review_blockers,
        ]
    )
    if construction_allowed:
        pending_steps = [
            *("PROCESS_PHASE24_EXTERNAL_REVIEWS" for _ in review_blockers[:1]),
            "BUILD_IDENTIFIED_REAL_DATASET",
            "EVALUATE_TRAINING_READINESS",
        ]
    blocked_actions = _unique(
        [
            *contract_report["blocked_actions"],
            *[
                action
                for action in BLOCKED_ACTIONS
                if action
                not in (
                    "BUILD_REAL_DATASET",
                    "BUILD_ORDER_FLOW_FEATURES",
                    *(() if not training_ready else ("TRAIN_PRODUCTION_MODEL",)),
                )
            ],
            *([] if construction_allowed else ["BUILD_REAL_DATASET", "BUILD_ORDER_FLOW_FEATURES"]),
        ]
    )
    if training_ready:
        blocked_actions = [action for action in blocked_actions if action != "TRAIN_PRODUCTION_MODEL"]
    body = {
        "report_version": REPORT_VERSION,
        "mode": MODE,
        "created_at": utc_iso(created_at),
        "status": "READY" if training_ready else "BLOCKED",
        "canonical_symbol": contract_report["canonical_symbol"],
        "candidate_timeframe": contract_report["candidate_timeframe"],
        "dataset_contract_id": contract_report["contract_id"],
        "dataset_contract_status": contract_report["status"],
        "real_data_readiness_status": real_data["status"],
        "real_data_satisfied_count": real_data["satisfied_count"],
        "real_data_open_count": real_data["open_count"],
        "training_policy_version": training_policy.version,
        "training_start_allowed": training_ready,
        "dataset_construction_allowed": construction_allowed,
        "model_promotion_allowed": False,
        "required_pretraining_gates": required_gates,
        "blocked_actions": blocked_actions,
        "blocking_reviews": review_blockers,
        "human_decision_request": HUMAN_DECISION_REQUEST,
        "pending_process_steps": [] if training_ready else pending_steps,
        "build_manifest_ref": _safe_ref(build_manifest_path) if build_manifest_path is not None else None,
        "built_dataset_id": build_manifest["dataset_id"] if build_manifest is not None else None,
        "training_readiness": training_readiness,
    }
    report_id = _report_id(body)
    payload = {"report_id": report_id, **body}
    return GcPretrainingReadinessReport(report_id=report_id, created_at=created_at, payload=payload)
