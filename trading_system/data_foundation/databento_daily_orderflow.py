"""Cost-gated, atomic daily retention of Databento Order Flow evidence."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any, Callable
from uuid import uuid4


VERSION = "databento-orderflow-daily-v1"


@dataclass(frozen=True)
class Asset:
    target_instrument: str
    source_instrument: str
    request_symbol: str
    slug: str


@dataclass(frozen=True)
class Request:
    asset: Asset
    schema: str
    day: date

    @property
    def start(self) -> datetime:
        return datetime.combine(self.day, time.min, tzinfo=UTC)

    @property
    def end(self) -> datetime:
        return self.start + timedelta(days=1)

    @property
    def filename(self) -> str:
        return f"{self.asset.slug}-{self.schema}.dbn.zst"


@dataclass(frozen=True)
class Policy:
    version: str
    dataset: str
    stype_in: str
    daily_cost_cap_usd: float
    schemas: tuple[str, ...]
    assets: tuple[Asset, ...]

    def requests_for(self, day: date) -> tuple[Request, ...]:
        return tuple(Request(asset, schema, day) for asset in self.assets for schema in self.schemas)


def load_policy(path: Path) -> Policy:
    raw = json.loads(path.read_text(encoding="utf-8"))
    policy = Policy(
        version=str(raw["version"]),
        dataset=str(raw["dataset"]),
        stype_in=str(raw["stype_in"]),
        daily_cost_cap_usd=float(raw["daily_cost_cap_usd"]),
        schemas=tuple(str(x) for x in raw["schemas"]),
        assets=tuple(Asset(**item) for item in raw["assets"]),
    )
    if policy.version != VERSION:
        raise ValueError("ORDERFLOW_POLICY_VERSION")
    if policy.dataset != "GLBX.MDP3" or policy.stype_in != "continuous":
        raise ValueError("ORDERFLOW_SOURCE_IDENTITY")
    if policy.schemas != ("trades", "mbp-10"):
        raise ValueError("ORDERFLOW_SCHEMAS")
    if len(policy.assets) != 3 or len({x.slug for x in policy.assets}) != 3:
        raise ValueError("ORDERFLOW_ASSETS")
    if policy.daily_cost_cap_usd <= 0:
        raise ValueError("ORDERFLOW_COST_CAP")
    return policy


def closed_utc_dates(start: date, end: date, *, now: datetime | None = None) -> tuple[date, ...]:
    """Inclusive date range containing closed UTC days only."""
    current = (now or datetime.now(UTC)).astimezone(UTC).date()
    if start > end:
        raise ValueError("DATE_RANGE")
    if start >= current:
        raise ValueError("CURRENT_UTC_DAY")
    final = min(end, current - timedelta(days=1))
    return tuple(start + timedelta(days=i) for i in range((final - start).days + 1))


def _json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_dbn(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("EMPTY_DBN")
    import databento as db

    store = db.DBNStore.from_file(path)
    count = sum(1 for _ in store)
    return {
        "record_count": count,
        "schema": str(store.schema),
        "dataset": str(store.metadata.dataset),
    }


def create_historical_client(api_key_env: str = "DATABENTO_API_KEY") -> Any:
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise ValueError("DATABENTO_API_KEY_MISSING")
    import databento as db

    return db.Historical(key=api_key)


def record_blocked_status(data_root: Path, day: date, status: str) -> dict[str, Any]:
    payload = {
        "version": VERSION,
        "day": day.isoformat(),
        "status": status,
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    _json_write(Path(data_root) / "status" / f"{day.isoformat()}.json", payload)
    return payload


class DailyOrderFlowCollector:
    def __init__(
        self,
        policy: Policy,
        client: Any,
        data_root: Path,
        *,
        validator: Callable[[Path], dict[str, Any]] = validate_dbn,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.policy = policy
        self.client = client
        self.root = Path(data_root)
        self.validator = validator
        self.now = now

    def _status(self, day: date, status: str, **extra: Any) -> dict[str, Any]:
        payload = {
            "version": VERSION,
            "day": day.isoformat(),
            "status": status,
            "recorded_at": self.now().astimezone(UTC).isoformat(),
            **extra,
        }
        _json_write(self.root / "status" / f"{day.isoformat()}.json", payload)
        return payload

    def _existing_complete(self, day: date, requests: tuple[Request, ...]) -> bool:
        final = self.root / "days" / day.isoformat()
        manifest_path = final / "day-manifest.json"
        if not manifest_path.is_file():
            return False
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifacts = manifest["artifacts"]
            expected = {(r.asset.slug, r.schema) for r in requests}
            actual = {(x["asset_slug"], x["schema"]) for x in artifacts}
            if actual != expected or manifest["status"] != "COMPLETE":
                return False
            return all(
                (final / item["file"]).is_file()
                and _sha256(final / item["file"]) == item["sha256"]
                for item in artifacts
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return False

    def _cost(self, request: Request) -> float:
        return float(self.client.metadata.get_cost(
            dataset=self.policy.dataset,
            start=request.start.isoformat(),
            end=request.end.isoformat(),
            symbols=request.asset.request_symbol,
            schema=request.schema,
            stype_in=self.policy.stype_in,
        ))

    def collect(self, day: date) -> dict[str, Any]:
        requests = self.policy.requests_for(day)
        if self._existing_complete(day, requests):
            return self._status(day, "ALREADY_COMPLETE")

        try:
            costs = [(request, self._cost(request)) for request in requests]
        except Exception as exc:
            return self._status(day, "FAILED_COST_ESTIMATE", error_type=type(exc).__name__)
        total_cost = sum(cost for _, cost in costs)
        if total_cost > self.policy.daily_cost_cap_usd:
            return self._status(
                day, "BLOCKED_COST_CAP", estimated_cost_usd=total_cost,
                daily_cost_cap_usd=self.policy.daily_cost_cap_usd,
            )

        staging_root = self.root / ".staging"
        staging = staging_root / f"{day.isoformat()}-{uuid4().hex}"
        staging.mkdir(parents=True, exist_ok=False)
        artifacts: list[dict[str, Any]] = []
        cost_map = {(r.asset.slug, r.schema): cost for r, cost in costs}
        try:
            for request in requests:
                raw = staging / request.filename
                self.client.timeseries.get_range(
                    dataset=self.policy.dataset,
                    start=request.start.isoformat(),
                    end=request.end.isoformat(),
                    symbols=request.asset.request_symbol,
                    schema=request.schema,
                    stype_in=self.policy.stype_in,
                    stype_out="instrument_id",
                    path=raw,
                )
                validation = self.validator(raw)
                artifacts.append({
                    **validation,
                    "asset_slug": request.asset.slug,
                    "target_instrument": request.asset.target_instrument,
                    "source_instrument": request.asset.source_instrument,
                    "request_symbol": request.asset.request_symbol,
                    "dataset": self.policy.dataset,
                    "stype_in": self.policy.stype_in,
                    "schema": request.schema,
                    "start": request.start.isoformat(),
                    "end": request.end.isoformat(),
                    "file": request.filename,
                    "bytes": raw.stat().st_size,
                    "sha256": _sha256(raw),
                    "estimated_cost_usd": cost_map[(request.asset.slug, request.schema)],
                })
            manifest = {
                "version": VERSION,
                "status": "COMPLETE",
                "day": day.isoformat(),
                "acquired_at": self.now().astimezone(UTC).isoformat(),
                "estimated_cost_usd": total_cost,
                "daily_cost_cap_usd": self.policy.daily_cost_cap_usd,
                "artifacts": artifacts,
            }
            _json_write(staging / "day-manifest.json", manifest)
            final = self.root / "days" / day.isoformat()
            final.parent.mkdir(parents=True, exist_ok=True)
            if final.exists():
                raise FileExistsError("INVALID_EXISTING_DAY")
            os.replace(staging, final)
            return self._status(day, "COMPLETE", estimated_cost_usd=total_cost, artifacts=len(artifacts))
        except Exception as exc:
            shutil.rmtree(staging, ignore_errors=True)
            return self._status(day, "FAILED_DOWNLOAD", error_type=type(exc).__name__)
        finally:
            try:
                staging_root.rmdir()
            except OSError:
                pass
