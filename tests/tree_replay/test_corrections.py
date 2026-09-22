"""As-of contract regressions using caller-supplied synthetic evidence only."""

from dataclasses import FrozenInstanceError, asdict, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import importlib
import importlib.util
import json

import numpy as np
import pandas as pd
import pytest


T = datetime(2020, 2, 1, tzinfo=timezone.utc)
US = timedelta(microseconds=1)


def api():
    name = "trading_system.tree_replay.corrections"
    assert importlib.util.find_spec(name) is not None, "Missing assigned corrections adapter"
    return importlib.import_module(name)


def evidence(**changes):
    return api().CorrectionEvidence(**(dict(
        evidence_id="e1", frame_id="daily-1", instrument="OANDA:XAUUSD",
        version="fixture-v1", observed_at=T, available_at=T,
        provenance="synthetic observation", offset=-12, source="tv_spliced",
        confidence="high", note="", tv_from=T - timedelta(days=20),
    ) | changes))


def assess(e, **changes):
    return api().assess_correction_asof(e, **(dict(
        instrument="OANDA:XAUUSD", frame_id="daily-1", decision_time=T,
        lookback_days=20, max_age_seconds=30 * 86400,
    ) | changes))


@pytest.mark.parametrize("days", [7, 20])
@pytest.mark.parametrize("delta,want", [(-US, False), (timedelta(0), True), (US, True)])
def test_splice_boundary_uses_replay_instant_not_today(days, delta, want):
    e = evidence(observed_at=T - timedelta(days=1), available_at=T - timedelta(days=1),
                 tv_from=T - timedelta(days=days))
    result = assess(e, decision_time=T + delta, lookback_days=days)
    assert result["status"] == "ASSESSED"
    assert result["broker_shape_ok"] is want


@pytest.mark.parametrize("source,confidence,symbol,shape,unverified", [
    ("tv_daily", "unknown", "OANDA:XAUUSD", True, False),
    ("mt5_broker", "high", "OANDA:XAUUSD", True, False),
    ("none", "n/a", "BINANCE:BTCUSDT", True, False),
    ("none", "unknown", "BINANCE:BTCUSDT", True, True),
    ("none", "unknown", "COMEX:GC", False, True),
    ("none", "n/a", "OANDA:XAUUSD", False, False),
    ("none", "n/a", "binance:btcusdt", False, False),
    ("none", "n/a", "BINANCE:BTCUSD", False, False),
    ("none", "n/a", "OANDA:BTCUSDT", False, False),
    ("tv_live", "high", "OANDA:XAUUSD", False, False),
    ("cash_hours", "medium", "OANDA:XAUUSD", False, False),
    ("cached_stale", "low", "OANDA:XAUUSD", False, False),
    ("replay", "high", "OANDA:XAUUSD", False, False),
    ("replay", "high", "BINANCE:BTCUSDT", True, False),
    ("vendor_addition", "vendor_confidence", "OANDA:XAUUSD", False, False),
    ("NONE", "unknown", "OANDA:XAUUSD", False, False),
    ("none", "UNKNOWN", "OANDA:XAUUSD", False, False),
])
def test_quality_flags_are_source_predicates_not_admission(source, confidence, symbol, shape, unverified):
    out = assess(evidence(source=source, confidence=confidence, instrument=symbol), instrument=symbol)
    assert (out["status"], out["blocker"]) == ("ASSESSED", None)
    assert out["broker_shape_ok"] is shape
    assert out["unverified"] is unverified
    assert out["ready_for_replay"] is out["ready_for_training"] is False


@pytest.mark.parametrize("offset", [-100, 0, 100])
def test_offset_does_not_repair_proxy_shape(offset):
    out = assess(evidence(source="tv_live", offset=offset))
    assert out["broker_shape_ok"] is False
    assert out["evidence"]["offset"] == offset


def test_splice_without_seam_is_valid_but_has_no_shape_proof():
    out = assess(evidence(tv_from=None))
    assert out["status"] == "ASSESSED"
    assert out["broker_shape_ok"] is False
    assert out["evidence"]["tv_from"] is None


@pytest.mark.parametrize("lookback,want", [(0, True), (0.000001, False)])
def test_current_seam_covers_only_zero_lookback(lookback, want):
    assert assess(evidence(tv_from=T), lookback_days=lookback)["broker_shape_ok"] is want


@pytest.mark.parametrize("changes,when,budget,blocker", [
    (None, T, 0, "CORRECTION_MISSING"),
    ({"observed_at": T + US, "available_at": T + US}, T, 0, "CORRECTION_FUTURE_OBSERVATION"),
    ({"available_at": T + US}, T, 0, "CORRECTION_UNAVAILABLE"),
    ({"observed_at": T - timedelta(days=2), "available_at": T + US}, T, 0, "CORRECTION_UNAVAILABLE"),
    ({}, T + US, 0, "CORRECTION_STALE"),
    ({}, T + timedelta(seconds=5) + US, 5, "CORRECTION_STALE"),
    ({}, T + timedelta(seconds=5), 5, None),
    ({}, T, 0, None),
])
def test_temporal_precedence_and_exact_freshness(changes, when, budget, blocker):
    out = assess(None if changes is None else evidence(**changes), decision_time=when, max_age_seconds=budget)
    assert out["blocker"] == blocker
    assert out["status"] == ("BLOCKED" if blocker else "ASSESSED")
    if blocker:
        assert out["evidence"] is out["unverified"] is out["broker_shape_ok"] is None
    assert out["ready_for_replay"] is out["ready_for_training"] is False


@pytest.mark.parametrize("field", ["evidence_id", "frame_id", "instrument", "version", "provenance", "source", "confidence"])
@pytest.mark.parametrize("value", ["", " spaced", "trailing ", None, 1])
def test_invalid_text_is_rejected_without_silent_trimming(field, value):
    with pytest.raises(ValueError):
        evidence(**{field: value})


@pytest.mark.parametrize("value", ["GC", "A:B:C", "A:", ":B", "A:B C"])
def test_instrument_requires_exact_venue_symbol(value):
    with pytest.raises(ValueError):
        evidence(instrument=value)


@pytest.mark.parametrize("field", ["offset", "lookback_days"])
@pytest.mark.parametrize("value", [True, "1", float("nan"), float("inf"), -float("inf"), Decimal("1"), np.float64(1), 10**400])
def test_numbers_must_be_native_and_finite(field, value):
    with pytest.raises(ValueError):
        if field == "offset":
            evidence(offset=value)
        else:
            assess(None, lookback_days=value)


@pytest.mark.parametrize("value", [-1, -0.5])
def test_negative_lookback_is_invalid_even_for_missing_evidence(value):
    with pytest.raises(ValueError):
        assess(None, lookback_days=value)


@pytest.mark.parametrize("value", [True, -1, 1.0, "1", None, np.int64(1)])
def test_freshness_budget_must_be_native_nonnegative_integer(value):
    with pytest.raises(ValueError):
        assess(None, max_age_seconds=value)


@pytest.mark.parametrize("field", ["observed_at", "available_at", "tv_from", "decision_time"])
@pytest.mark.parametrize("value", [datetime(2020, 2, 1), "2020-02-01T00:00:00Z", pd.Timestamp("2020-02-01T00:00:00.000000001Z"), pd.NaT])
def test_timestamps_require_aware_microsecond_exact_datetimes(field, value):
    with pytest.raises(ValueError):
        if field == "decision_time":
            assess(None, decision_time=value)
        else:
            evidence(**{field: value})


@pytest.mark.parametrize("changes", [{"available_at": T - US}, {"tv_from": T + US}, {"note": None}, {"note": 0}, {"source": "replay", "note": {"replay": True}}])
def test_inconsistent_evidence_is_rejected(changes):
    with pytest.raises(ValueError):
        evidence(**changes)


@pytest.mark.parametrize("changes", [
    {"instrument": "COMEX:GC"}, {"instrument": "oanda:xauusd"}, {"instrument": "XAUUSD"},
    {"frame_id": "other-frame"}, {"frame_id": ""}, {"frame_id": 1},
])
def test_identity_validation_precedes_future_evidence_assessment(changes):
    e = evidence(observed_at=T + US, available_at=T + US)
    with pytest.raises(ValueError):
        assess(e, **changes)


@pytest.mark.parametrize("value", [0, {}, "evidence", object()])
def test_only_explicit_evidence_or_none_is_accepted(value):
    with pytest.raises(ValueError):
        assess(value)


def test_normalized_canonical_payload_and_hash_are_complete():
    local = T.astimezone(timezone(timedelta(hours=3)))
    e = evidence(observed_at=local, available_at=local, note=" note may retain spaces ")
    before = asdict(e)
    out = assess(e, decision_time=local)
    expected = {
        "schema_version": "correction-asof-v1",
        "calculation_version": "chartdesk-correction-asof-v1",
        "instrument": "OANDA:XAUUSD", "frame_id": "daily-1",
        "decision_time": "2020-02-01T00:00:00Z", "lookback_days": 20.0,
        "max_age_seconds": 2592000, "status": "ASSESSED", "blocker": None,
        "evidence": {
            "evidence_id": "e1", "frame_id": "daily-1", "instrument": "OANDA:XAUUSD",
            "version": "fixture-v1", "observed_at": "2020-02-01T00:00:00Z",
            "available_at": "2020-02-01T00:00:00Z", "provenance": "synthetic observation",
            "offset": -12.0, "source": "tv_spliced", "confidence": "high",
            "note": " note may retain spaces ", "tv_from": "2020-01-12T00:00:00Z",
        },
        "unverified": False, "broker_shape_ok": True,
        "ready_for_replay": False, "ready_for_training": False,
    }
    digest = hashlib.sha256(json.dumps(expected, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    assert out == expected | {"evidence_hash": digest}
    assert e.observed_at.tzinfo is timezone.utc
    assert asdict(e) == before
    assert assess(e) == out
    out["evidence"]["offset"] = 999
    assert assess(e)["evidence"]["offset"] == -12
    with pytest.raises(FrozenInstanceError):
        e.offset = 100


@pytest.mark.parametrize("changes", [
    {"evidence_id": "e2"}, {"version": "v2"}, {"offset": 3}, {"source": "tv_daily"},
    {"confidence": "new"}, {"note": "new"}, {"provenance": "new"},
    {"observed_at": T - US}, {"tv_from": T - timedelta(days=21)},
])
def test_selected_evidence_changes_hash(changes):
    assert assess(evidence(**changes))["evidence_hash"] != assess(evidence())["evidence_hash"]


@pytest.mark.parametrize("changes", [
    {"lookback_days": 7}, {"max_age_seconds": 0}, {"decision_time": T + US},
])
def test_policy_and_clock_changes_hash(changes):
    assert assess(evidence(), **changes)["evidence_hash"] != assess(evidence())["evidence_hash"]


@pytest.mark.parametrize("temporal", [
    {"available_at": T + US},
    {"observed_at": T + US, "available_at": T + US},
    {"observed_at": T - timedelta(days=31), "tv_from": None},
])
def test_blocked_payload_changes_cannot_leak_into_output_or_hash(temporal):
    first = evidence(**temporal)
    second = replace(first, evidence_id="secret-id", offset=12345, source="secret-source",
                     confidence="secret-confidence", note="secret-note", provenance="secret-provenance")
    assert assess(first)["status"] == "BLOCKED"
    assert assess(first) == assess(second)


def test_microseconds_are_retained_in_output():
    e = evidence(observed_at=T + US, available_at=T + US, tv_from=T - US)
    out = assess(e, decision_time=T + US)
    assert out["decision_time"] == "2020-02-01T00:00:00.000001Z"
    assert out["evidence"]["tv_from"] == "2020-01-31T23:59:59.999999Z"
