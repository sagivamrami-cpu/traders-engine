from __future__ import annotations

from datetime import UTC, date, datetime
import hashlib
import json
from pathlib import Path

import pytest

from trading_system.data_foundation.databento_daily_orderflow import (
    DailyOrderFlowCollector,
    closed_utc_dates,
    create_historical_client,
    load_policy,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "configs/data/databento-orderflow-daily.json"


class _Metadata:
    def __init__(self, costs):
        self.costs = costs
        self.calls = []

    def get_cost(self, **kwargs):
        self.calls.append(kwargs)
        return self.costs.get((kwargs["symbols"], kwargs["schema"]), 1.0)


class _Timeseries:
    def __init__(self):
        self.calls = []

    def get_range(self, **kwargs):
        self.calls.append(kwargs)
        Path(kwargs["path"]).write_bytes(
            (kwargs["symbols"] + "|" + kwargs["schema"]).encode("ascii")
        )


class _Client:
    def __init__(self, costs=None):
        self.metadata = _Metadata(costs or {})
        self.timeseries = _Timeseries()


def _validate(path: Path):
    assert path.stat().st_size > 0
    return {"record_count": 7, "schema": path.stem.split("-")[-1]}


def test_policy_is_exact_three_assets_and_two_orderflow_schemas():
    policy = load_policy(POLICY)
    assert [a.request_symbol for a in policy.assets] == ["GC.v.0", "NQ.v.0", "BTC.v.0"]
    assert policy.schemas == ("trades", "mbp-10")
    assert len(policy.requests_for(date(2026, 9, 18))) == 6


def test_api_key_is_required_without_leaking_or_fallback(monkeypatch):
    monkeypatch.delenv("DATABENTO_API_KEY", raising=False)
    with pytest.raises(ValueError, match="DATABENTO_API_KEY_MISSING"):
        create_historical_client()


def test_current_or_future_utc_day_is_refused():
    now = datetime(2026, 9, 20, 10, tzinfo=UTC)
    assert closed_utc_dates(date(2026, 9, 18), date(2026, 9, 20), now=now) == (
        date(2026, 9, 18), date(2026, 9, 19)
    )
    with pytest.raises(ValueError, match="CURRENT_UTC_DAY"):
        closed_utc_dates(date(2026, 9, 20), date(2026, 9, 20), now=now)


def test_cost_is_estimated_for_all_six_before_any_download(tmp_path):
    policy = load_policy(POLICY)
    client = _Client({("BTC.v.0", "mbp-10"): 30.0})
    result = DailyOrderFlowCollector(policy, client, tmp_path, validator=_validate).collect(date(2026, 9, 18))
    assert result["status"] == "BLOCKED_COST_CAP"
    assert len(client.metadata.calls) == 6
    assert client.timeseries.calls == []
    assert (tmp_path / "status/2026-09-18.json").exists()


def test_complete_day_is_atomic_hashed_and_has_all_members(tmp_path):
    policy = load_policy(POLICY)
    client = _Client()
    result = DailyOrderFlowCollector(policy, client, tmp_path, validator=_validate).collect(date(2026, 9, 18))
    assert result["status"] == "COMPLETE"
    final = tmp_path / "days/2026-09-18"
    assert final.is_dir()
    assert len(client.timeseries.calls) == 6
    manifest = json.loads((final / "day-manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["artifacts"]) == 6
    assert {(x["asset_slug"], x["schema"]) for x in manifest["artifacts"]} == {
        (a, s) for a in ("gold", "nasdaq", "bitcoin") for s in ("trades", "mbp-10")
    }
    for item in manifest["artifacts"]:
        raw = final / item["file"]
        assert hashlib.sha256(raw.read_bytes()).hexdigest() == item["sha256"]
        assert item["record_count"] == 7
    assert not (tmp_path / ".staging").exists() or not any((tmp_path / ".staging").iterdir())


def test_second_run_verifies_and_skips_download(tmp_path):
    policy = load_policy(POLICY)
    first = _Client()
    collector = DailyOrderFlowCollector(policy, first, tmp_path, validator=_validate)
    assert collector.collect(date(2026, 9, 18))["status"] == "COMPLETE"
    second = _Client()
    result = DailyOrderFlowCollector(policy, second, tmp_path, validator=_validate).collect(date(2026, 9, 18))
    assert result["status"] == "ALREADY_COMPLETE"
    assert second.metadata.calls == []
    assert second.timeseries.calls == []


def test_failed_download_never_publishes_partial_day(tmp_path):
    policy = load_policy(POLICY)
    client = _Client()
    original = client.timeseries.get_range
    def fail_third(**kwargs):
        if len(client.timeseries.calls) == 2:
            raise RuntimeError("network")
        return original(**kwargs)
    client.timeseries.get_range = fail_third
    result = DailyOrderFlowCollector(policy, client, tmp_path, validator=_validate).collect(date(2026, 9, 18))
    assert result["status"] == "FAILED_DOWNLOAD"
    assert not (tmp_path / "days/2026-09-18").exists()
    assert (tmp_path / "status/2026-09-18.json").exists()


def test_request_retains_both_target_and_context_identities(tmp_path):
    policy = load_policy(POLICY)
    client = _Client()
    DailyOrderFlowCollector(policy, client, tmp_path, validator=_validate).collect(date(2026, 9, 18))
    manifest = json.loads((tmp_path / "days/2026-09-18/day-manifest.json").read_text(encoding="utf-8"))
    gold = next(x for x in manifest["artifacts"] if x["asset_slug"] == "gold" and x["schema"] == "trades")
    assert gold["target_instrument"] == "OANDA:XAUUSD"
    assert gold["source_instrument"] == "CME:GC"
    assert gold["request_symbol"] == "GC.v.0"
    call = next(x for x in client.timeseries.calls if x["symbols"] == "GC.v.0" and x["schema"] == "trades")
    assert call["stype_in"] == "continuous"
    assert call["dataset"] == "GLBX.MDP3"
