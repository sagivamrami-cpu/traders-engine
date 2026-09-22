from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from trading_system.data_foundation.hashing import stable_json_dumps
from trading_system.features.contracts import utc_iso

REPORT_VERSION = "databento-gc-vendor-preflight-0.1.0"
MODE = "DATABENTO_GC_VENDOR_PREFLIGHT"
VENDOR = "DATABENTO"
DATASET = "GLBX.MDP3"
CANONICAL_SYMBOL = "GC"
API_KEY_ENV = "DATABENTO_API_KEY"
API_KEY_SOURCE = f"ENV:{API_KEY_ENV}"
OFFLINE_STATUS = "OFFLINE_PLAN_RECORDED_API_KEY_BLOCKED"
ONLINE_COST_STATUS = "COST_ESTIMATES_RECORDED_PURCHASE_BLOCKED"
DATASET_METADATA_STATUS = "METADATA_RETURNED_NOT_APPROVED"
SCHEMAS_METADATA_STATUS = "METADATA_RETURNED_NOT_APPROVED"
SYMBOL_METADATA_STATUS = "SYMBOL_METADATA_RETURNED_IDENTITY_UNCONFIRMED"
CONTRACT_IDENTITY_STATUS = "UNDECLARED_PENDING_RESEARCH"
STYPE_IN_STATUS = "RESEARCH_DECISION_PENDING"
SYMBOL_IDENTITY_STATUS = "AMBIGUOUS_NOT_A_DATED_CONTRACT"
ESTIMATE_WINDOW_ROLE = "SAMPLE_DAY_NOT_FULL_INTERVAL"
COVERAGE_STATUS = "NOT_PROVEN_SAMPLE_DAY_ONLY"
MBO_ERA_STATUS = "MBO_ERA_COVERAGE_REQUIRES_VENDOR_VERIFICATION"
BLOCKED_ACTIONS = (
    "DOWNLOAD_DATABENTO_DATA",
    "PURCHASE_DATABENTO_DATA",
    "SUBMIT_DATABENTO_BATCH_JOB",
    "APPROVE_ORDER_FLOW_SOURCE",
    "APPROVE_OPTIONS_SOURCE",
    "QUERY_OPTIONS_PARENT",
    "PURCHASE_MBO_DATA",
    "MAP_GC_TO_XAUUSD",
    "MAP_GC_TO_GLD",
    "BUILD_REAL_DATASET",
    "DEPLOYMENT",
    "DATABENTO_LIVE_CALL_BLOCKED_UNTIL_CONTRACT_STYPE_DECISION",
    "BUILD_ORDER_FLOW_FEATURES",
    "BUILD_OPTIONS_FEATURES",
    "BUILD_PRODUCTION_TRAINING_DATASET",
    "TRAIN_PRODUCTION_MODEL",
    "CLAIM_EDGE",
    "MODEL_PROMOTION",
    "LIVE_TRADING",
    "BROKER_EXECUTION",
    "CAPITAL_ALLOCATION",
)
BASE_BLOCKED_REASONS = (
    "PURCHASE_REQUIRES_HUMAN_APPROVAL",
    "DATA_DOWNLOAD_BLOCKED",
    "PRODUCTION_READINESS_BLOCKED",
    "OPTIONS_PARENT_UNCONFIRMED",
    "MBO_REFERENCE_ONLY_NOT_A_PURCHASE_CANDIDATE",
)


@dataclass(frozen=True)
class DatabentoCostRequest:
    request_id: str
    purpose: str
    schema: str
    symbols: tuple[str, ...]
    stype_in: str
    start: str
    end: str
    query_symbols: tuple[str, ...] = ()
    query_stype_in: str | None = None


@dataclass(frozen=True)
class DatabentoOptionsParentPolicy:
    status: str
    candidate_symbols: tuple[str, ...]


@dataclass(frozen=True)
class DatabentoVendorPreflightPolicy:
    version: str
    vendor: str
    dataset: str
    canonical_symbol: str
    api_key_env: str
    max_estimated_cost_usd: float
    no_data_download: bool
    purchase_allowed: bool
    timeseries_get_range_allowed: bool
    requests: tuple[DatabentoCostRequest, ...]
    options_parent: DatabentoOptionsParentPolicy


@dataclass(frozen=True)
class DatabentoEstimatedRequest:
    request_id: str
    purpose: str
    dataset: str
    schema: str
    symbols: tuple[str, ...]
    stype_in: str
    query_symbols: tuple[str, ...]
    query_stype_in: str | None
    start: str
    end: str
    cost_usd: float | None
    availability_status: str
    purchase_candidate: bool
    symbol_identity_status: str
    estimate_window_role: str
    blocked_reasons: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "purpose": self.purpose,
            "dataset": self.dataset,
            "schema": self.schema,
            "symbols": list(self.symbols),
            "stype_in": self.stype_in,
            "query_symbols": list(self.query_symbols),
            "query_stype_in": self.query_stype_in,
            "start": self.start,
            "end": self.end,
            "cost_usd": self.cost_usd,
            "availability_status": self.availability_status,
            "purchase_candidate": self.purchase_candidate,
            "symbol_identity_status": self.symbol_identity_status,
            "estimate_window_role": self.estimate_window_role,
            "blocked_reasons": list(self.blocked_reasons),
        }


@dataclass(frozen=True)
class DatabentoVendorPreflightReport:
    report_id: str
    created_at: datetime
    status: str
    policy: DatabentoVendorPreflightPolicy
    api_key_present: bool
    dataset_status: str
    schemas_status: str
    symbol_resolution_status: str
    estimated_requests: tuple[DatabentoEstimatedRequest, ...]
    blocked_reasons: tuple[str, ...]

    @property
    def stype_in_status(self) -> str:
        if any(request.query_symbols or request.query_stype_in for request in self.policy.requests):
            return "COST_PREFLIGHT_QUERY_STYPE_RECORDED_NOT_IDENTITY"
        return STYPE_IN_STATUS

    def to_payload(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "report_version": REPORT_VERSION,
            "mode": MODE,
            "created_at": utc_iso(self.created_at),
            "status": self.status,
            "vendor": self.policy.vendor,
            "dataset": self.policy.dataset,
            "canonical_symbol": self.policy.canonical_symbol,
            "api_key_source": f"ENV:{self.policy.api_key_env}",
            "api_key_present": self.api_key_present,
            "dataset_status": self.dataset_status,
            "schemas_status": self.schemas_status,
            "symbol_resolution_status": self.symbol_resolution_status,
            "no_data_download": self.policy.no_data_download,
            "download_allowed": False,
            "purchase_allowed": False,
            "timeseries_get_range_allowed": False,
            "dataset_construction_allowed": False,
            "training_allowed": False,
            "contract_identity_status": CONTRACT_IDENTITY_STATUS,
            "stype_in_status": self.stype_in_status,
            "estimate_window_role": ESTIMATE_WINDOW_ROLE,
            "coverage_status": COVERAGE_STATUS,
            "mbo_era_status": MBO_ERA_STATUS,
            "max_estimated_cost_usd": self.policy.max_estimated_cost_usd,
            "estimated_requests": [request.to_payload() for request in self.estimated_requests],
            "options_parent": {
                "status": self.policy.options_parent.status,
                "candidate_symbols": list(self.policy.options_parent.candidate_symbols),
                "queried": False,
            },
            "allowed_next_actions": [],
            "blocked_actions": list(BLOCKED_ACTIONS),
            "blocked_reasons": list(self.blocked_reasons),
        }


def _unique(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _report_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def _request_from_payload(raw: dict[str, Any]) -> DatabentoCostRequest:
    symbols = tuple(str(symbol).strip() for symbol in raw.get("symbols", []) if str(symbol).strip())
    query_symbols = tuple(str(symbol).strip() for symbol in raw.get("query_symbols", []) if str(symbol).strip())
    query_stype_raw = raw.get("query_stype_in")
    query_stype_in = str(query_stype_raw).strip() if query_stype_raw else None
    return DatabentoCostRequest(
        request_id=str(raw.get("request_id", "")).strip(),
        purpose=str(raw.get("purpose", "")).strip(),
        schema=str(raw.get("schema", "")).strip(),
        symbols=symbols,
        stype_in=str(raw.get("stype_in", "")).strip(),
        start=str(raw.get("start", "")).strip(),
        end=str(raw.get("end", "")).strip(),
        query_symbols=query_symbols,
        query_stype_in=query_stype_in,
    )


def load_databento_vendor_preflight_policy(path: Path) -> DatabentoVendorPreflightPolicy:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return load_databento_vendor_preflight_policy_from_mapping(raw)


def load_databento_vendor_preflight_policy_from_mapping(raw: Any) -> DatabentoVendorPreflightPolicy:
    if not isinstance(raw, dict):
        raise ValueError("Databento preflight policy must be a mapping")
    requests = tuple(_request_from_payload(item) for item in raw.get("requests", []))
    options_raw = raw.get("options_parent", {})
    options_parent = DatabentoOptionsParentPolicy(
        status=str(options_raw.get("status", "")).strip(),
        candidate_symbols=tuple(
            str(symbol).strip() for symbol in options_raw.get("candidate_symbols", []) if str(symbol).strip()
        ),
    )
    policy = DatabentoVendorPreflightPolicy(
        version=str(raw.get("version", "")).strip(),
        vendor=str(raw.get("vendor", "")).strip(),
        dataset=str(raw.get("dataset", "")).strip(),
        canonical_symbol=str(raw.get("canonical_symbol", "")).strip(),
        api_key_env=str(raw.get("api_key_env", API_KEY_ENV)).strip(),
        max_estimated_cost_usd=float(raw.get("max_estimated_cost_usd", 0.0)),
        no_data_download=bool(raw.get("no_data_download", False)),
        purchase_allowed=bool(raw.get("purchase_allowed", False)),
        timeseries_get_range_allowed=bool(raw.get("timeseries_get_range_allowed", False)),
        requests=requests,
        options_parent=options_parent,
    )
    _validate_policy(policy)
    return policy


def load_databento_vendor_preflight_policy_from_object(
    policy: DatabentoVendorPreflightPolicy,
) -> DatabentoVendorPreflightPolicy:
    _validate_policy(policy)
    return policy


def _validate_policy(policy: DatabentoVendorPreflightPolicy) -> None:
    if policy.version != REPORT_VERSION:
        raise ValueError("Unexpected Databento preflight policy version")
    if policy.vendor != VENDOR:
        raise ValueError("Databento preflight policy must use DATABENTO vendor")
    if policy.dataset != DATASET:
        raise ValueError("Databento preflight policy must use GLBX.MDP3")
    if policy.canonical_symbol != CANONICAL_SYMBOL:
        raise ValueError("Databento preflight policy must use GC canonical symbol")
    if policy.api_key_env != API_KEY_ENV:
        raise ValueError("Databento API key env var must be DATABENTO_API_KEY")
    if policy.purchase_allowed:
        raise ValueError("Databento preflight policy must not allow purchases")
    if not policy.no_data_download:
        raise ValueError("Databento preflight policy must block downloads")
    if policy.timeseries_get_range_allowed:
        raise ValueError("Databento preflight policy must not allow timeseries.get_range")
    if not policy.requests:
        raise ValueError("Databento preflight policy must define cost requests")
    if policy.options_parent.status != "UNCONFIRMED_DO_NOT_QUERY":
        raise ValueError("Options parent must remain unconfirmed until human approval")
    if policy.options_parent.candidate_symbols:
        raise ValueError("Options parent candidates must stay empty before confirmation")
    for request in policy.requests:
        if not all((request.request_id, request.purpose, request.schema, request.symbols, request.stype_in, request.start, request.end)):
            raise ValueError("Every Databento preflight request must be fully specified")
        if any(symbol != CANONICAL_SYMBOL for symbol in request.symbols):
            raise ValueError("Phase 21 may only preflight GC order-flow requests")
        if bool(request.query_symbols) != bool(request.query_stype_in):
            raise ValueError("Databento query symbols and query stype must be set together")
        if request.query_symbols and not _query_symbols_match_stype(request.query_symbols, request.query_stype_in):
            raise ValueError("Databento query symbols are not valid for query stype")


def _query_symbols_match_stype(symbols: tuple[str, ...], stype_in: str | None) -> bool:
    if stype_in == "raw_symbol":
        return all(_is_gc_dated_contract(symbol) for symbol in symbols)
    if stype_in == "parent":
        return symbols == ("GC.FUT",)
    if stype_in == "continuous":
        return all(symbol.startswith("GC.v.") and symbol[5:].isdigit() for symbol in symbols)
    return False


def _is_gc_dated_contract(symbol: str) -> bool:
    if len(symbol) < 4:
        return False
    month = symbol[2]
    year = symbol[3:]
    return symbol.startswith("GC") and month in "FGHJKMNQUVXZ" and year.isdigit() and 1 <= len(year) <= 2


def _request_query_symbols(request: DatabentoCostRequest) -> tuple[str, ...]:
    return request.query_symbols or request.symbols


def _request_query_stype_in(request: DatabentoCostRequest) -> str:
    return request.query_stype_in or request.stype_in


def _planned_requests(policy: DatabentoVendorPreflightPolicy, status: str, reason: str) -> tuple[DatabentoEstimatedRequest, ...]:
    return tuple(
        DatabentoEstimatedRequest(
            request_id=request.request_id,
            purpose=request.purpose,
            dataset=policy.dataset,
            schema=request.schema,
            symbols=request.symbols,
            stype_in=request.stype_in,
            query_symbols=request.query_symbols,
            query_stype_in=request.query_stype_in,
            start=request.start,
            end=request.end,
            cost_usd=None,
            availability_status=status,
            purchase_candidate=False,
            symbol_identity_status=SYMBOL_IDENTITY_STATUS,
            estimate_window_role=ESTIMATE_WINDOW_ROLE,
            blocked_reasons=(reason,),
        )
        for request in policy.requests
    )


def _build_report(
    *,
    policy: DatabentoVendorPreflightPolicy,
    created_at: datetime,
    status: str,
    api_key_present: bool,
    dataset_status: str,
    schemas_status: str,
    symbol_resolution_status: str,
    estimated_requests: tuple[DatabentoEstimatedRequest, ...],
    blocked_reasons: tuple[str, ...],
) -> DatabentoVendorPreflightReport:
    id_payload = {
        "created_at": utc_iso(created_at),
        "status": status,
        "dataset_status": dataset_status,
        "schemas_status": schemas_status,
        "symbol_resolution_status": symbol_resolution_status,
        "estimated_requests": [request.to_payload() for request in estimated_requests],
        "blocked_reasons": list(blocked_reasons),
    }
    return DatabentoVendorPreflightReport(
        report_id=_report_id(id_payload),
        created_at=created_at,
        status=status,
        policy=policy,
        api_key_present=api_key_present,
        dataset_status=dataset_status,
        schemas_status=schemas_status,
        symbol_resolution_status=symbol_resolution_status,
        estimated_requests=estimated_requests,
        blocked_reasons=blocked_reasons,
    )


def build_offline_databento_vendor_preflight(
    policy: DatabentoVendorPreflightPolicy,
    *,
    created_at: datetime,
) -> DatabentoVendorPreflightReport:
    return _build_report(
        policy=policy,
        created_at=created_at,
        status=OFFLINE_STATUS,
        api_key_present=False,
        dataset_status="NOT_CHECKED_OFFLINE",
        schemas_status="NOT_CHECKED_OFFLINE",
        symbol_resolution_status="NOT_CHECKED_OFFLINE",
        estimated_requests=_planned_requests(policy, "PLANNED_NOT_ESTIMATED", "API_KEY_NOT_USED_OFFLINE"),
        blocked_reasons=_unique(["API_KEY_NOT_USED_OFFLINE", *BASE_BLOCKED_REASONS]),
    )


def build_missing_api_key_databento_vendor_preflight(
    policy: DatabentoVendorPreflightPolicy,
    *,
    created_at: datetime,
) -> DatabentoVendorPreflightReport:
    return _build_report(
        policy=policy,
        created_at=created_at,
        status="BLOCKED_API_KEY_MISSING",
        api_key_present=False,
        dataset_status="NOT_CHECKED_API_KEY_MISSING",
        schemas_status="NOT_CHECKED_API_KEY_MISSING",
        symbol_resolution_status="NOT_CHECKED_API_KEY_MISSING",
        estimated_requests=_planned_requests(policy, "BLOCKED_API_KEY_MISSING", "API_KEY_ENV_MISSING"),
        blocked_reasons=_unique(["API_KEY_ENV_MISSING", *BASE_BLOCKED_REASONS]),
    )


def build_missing_contract_stype_decision_databento_vendor_preflight(
    policy: DatabentoVendorPreflightPolicy,
    *,
    created_at: datetime,
    api_key_present: bool,
) -> DatabentoVendorPreflightReport:
    return _build_report(
        policy=policy,
        created_at=created_at,
        status="BLOCKED_CONTRACT_STYPE_DECISION_MISSING",
        api_key_present=api_key_present,
        dataset_status="NOT_CHECKED_CONTRACT_STYPE_DECISION_MISSING",
        schemas_status="NOT_CHECKED_CONTRACT_STYPE_DECISION_MISSING",
        symbol_resolution_status="NOT_CHECKED_CONTRACT_STYPE_DECISION_MISSING",
        estimated_requests=_planned_requests(
            policy,
            "BLOCKED_CONTRACT_STYPE_DECISION_MISSING",
            "CONTRACT_STYPE_DECISION_MISSING",
        ),
        blocked_reasons=_unique(["CONTRACT_STYPE_DECISION_MISSING", *BASE_BLOCKED_REASONS]),
    )


def _safe_call(default: Any, func, *args, **kwargs) -> tuple[Any, str | None]:
    try:
        return func(*args, **kwargs), None
    except Exception:
        return default, "DATABENTO_METADATA_CALL_FAILED"


def build_online_databento_vendor_preflight(
    policy: DatabentoVendorPreflightPolicy,
    *,
    client: Any,
    created_at: datetime,
    api_key_present: bool,
) -> DatabentoVendorPreflightReport:
    _, dataset_error = _safe_call(None, client.metadata.get_dataset, policy.dataset)
    schemas_raw, schemas_error = _safe_call([], client.metadata.list_schemas, policy.dataset)
    available_schemas = {str(schema) for schema in schemas_raw or []}
    unique_symbols = _unique([symbol for request in policy.requests for symbol in _request_query_symbols(request)])
    unique_stypes = _unique([_request_query_stype_in(request) for request in policy.requests])
    earliest = min(request.start for request in policy.requests)[:10]
    latest = max(request.end for request in policy.requests)[:10]
    if len(unique_stypes) != 1:
        symbology_error = "DATABENTO_QUERY_STYPE_MIXED"
    else:
        _, symbology_error = _safe_call(
            None,
            client.symbology.resolve,
            dataset=policy.dataset,
            symbols=list(unique_symbols),
            stype_in=unique_stypes[0],
            stype_out="instrument_id",
            start_date=earliest,
            end_date=latest,
        )

    estimated: list[DatabentoEstimatedRequest] = []
    report_reasons: list[str] = list(BASE_BLOCKED_REASONS)
    if dataset_error:
        report_reasons.append(dataset_error)
    if schemas_error:
        report_reasons.append(schemas_error)
    if symbology_error:
        report_reasons.append("DATABENTO_SYMBOLOGY_RESOLUTION_FAILED")

    for request in policy.requests:
        reasons: list[str] = []
        cost_usd: float | None = None
        availability_status = "COST_ESTIMATE_RECORDED_NOT_A_PURCHASE_QUOTE"
        if request.schema not in available_schemas:
            reasons.append("SCHEMA_NOT_AVAILABLE")
            availability_status = "BLOCKED_SCHEMA_UNSUPPORTED"
        elif symbology_error:
            reasons.append("SYMBOL_RESOLUTION_FAILED")
            availability_status = "BLOCKED_SYMBOL_RESOLUTION_FAILED"
        elif request.schema == "mbo":
            reasons.append("MBO_REFERENCE_ONLY_NOT_A_PURCHASE_CANDIDATE")
            availability_status = "REFERENCE_ONLY_NOT_A_PURCHASE_CANDIDATE"
        else:
            cost_raw, cost_error = _safe_call(
                None,
                client.metadata.get_cost,
                dataset=policy.dataset,
                start=request.start,
                end=request.end,
                symbols=list(_request_query_symbols(request)),
                schema=request.schema,
                stype_in=_request_query_stype_in(request),
            )
            if cost_error:
                reasons.append("COST_ESTIMATE_FAILED")
                availability_status = "BLOCKED_COST_ESTIMATE_FAILED"
            else:
                cost_usd = float(cost_raw)
                if cost_usd > policy.max_estimated_cost_usd:
                    reasons.append("COST_EXCEEDS_POLICY_LIMIT")
                    availability_status = "BLOCKED_COST_EXCEEDS_POLICY_LIMIT"
        report_reasons.extend(reasons)
        estimated.append(
            DatabentoEstimatedRequest(
                request_id=request.request_id,
                purpose=request.purpose,
                dataset=policy.dataset,
                schema=request.schema,
                symbols=request.symbols,
                stype_in=request.stype_in,
                query_symbols=request.query_symbols,
                query_stype_in=request.query_stype_in,
                start=request.start,
                end=request.end,
                cost_usd=cost_usd,
                availability_status=availability_status,
                purchase_candidate=False,
                symbol_identity_status=SYMBOL_IDENTITY_STATUS,
                estimate_window_role=ESTIMATE_WINDOW_ROLE,
                blocked_reasons=tuple(reasons),
            )
        )

    hard_failures = set(report_reasons) - set(BASE_BLOCKED_REASONS)
    status = "BLOCKED" if hard_failures else ONLINE_COST_STATUS
    return _build_report(
        policy=policy,
        created_at=created_at,
        status=status,
        api_key_present=api_key_present,
        dataset_status="BLOCKED" if dataset_error else DATASET_METADATA_STATUS,
        schemas_status="BLOCKED" if schemas_error else SCHEMAS_METADATA_STATUS,
        symbol_resolution_status="BLOCKED" if symbology_error else SYMBOL_METADATA_STATUS,
        estimated_requests=tuple(estimated),
        blocked_reasons=_unique(report_reasons),
    )


class SafeDatabentoMetadataClient:
    def __init__(self, client: Any):
        self.metadata = client.metadata
        self.symbology = client.symbology

    @property
    def timeseries(self) -> Any:
        raise RuntimeError("Databento timeseries surface is not allowed in Phase 21 preflight")

    @property
    def batch(self) -> Any:
        raise RuntimeError("Databento batch surface is not allowed in Phase 21 preflight")

    @property
    def live(self) -> Any:
        raise RuntimeError("Databento live surface is not allowed in Phase 21 preflight")


def wrap_databento_metadata_client(client: Any) -> SafeDatabentoMetadataClient:
    return SafeDatabentoMetadataClient(client)


def create_databento_historical_client(api_key_env: str = API_KEY_ENV) -> Any:
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise ValueError("Databento API key env var is missing")
    import databento as db

    return wrap_databento_metadata_client(db.Historical(key=api_key))
