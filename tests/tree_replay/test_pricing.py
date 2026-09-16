"""End-to-end synthetic detection + original pricing; never simulated fills."""
from dataclasses import replace
from datetime import timedelta
import json

import pytest

from test_reversal import history, levels, schedule
from trading_system.tree_replay.levels import NamedLevel
from trading_system.tree_replay.reversal import detect_reversals_asof


def fixture(tf="5m", short=False, instrument="OANDA:XAUUSD", target_offsets=(5,10,15)):
    entry = {"OANDA:XAUUSD":100, "OANDA:NAS100USD":29000, "BINANCE:BTCUSDT":75000}.get(instrument,100)
    bars = [replace(b, instrument=instrument, open=b.open+entry-100,
                    high=b.high+entry-100, low=b.low+entry-100, close=b.close+entry-100)
            for b in history(tf, short)]
    ls = replace(levels(bars), instrument=instrument, levels=(
        NamedLevel(name="PSY-LO", price=entry),
        *(NamedLevel(name=f"target-{i}", price=entry+(-offset if short else offset))
          for i, offset in enumerate(target_offsets)),
    ))
    params = dict(snapshot_id="pricing-test", instrument=instrument, timeframe=tf,
                  decision_time=bars[-1].closed_at, history_start=bars[0].opened_at,
                  max_age_seconds=370, level_snapshot=ls, max_level_age_seconds=370)
    return bars, params


def price(bars, params, **changes):
    from trading_system.tree_replay.pricing import price_reversals_asof
    return price_reversals_asof(bars, **{**params, **changes})


@pytest.mark.parametrize("short", [False,True])
def test_m5_plan_uses_zone_edge_stop_and_nearer_obstacles(short):
    bars, args = fixture(short=short)
    out = price(bars,args)
    assert out["status"] == "PRICING_EVALUATED" and out["blocker"] is None
    assert out["detection_status"] == "DETECTED_UNPRICED"
    c = out["candidates"][0]
    p = c["source_plan"]
    assert p["entry"] == 100
    assert p["entry_zone"] == {"low":98,"high":102}
    assert p["stop"] == (107 if short else 93)
    assert p["risk_price"] == 7
    assert p["targets"][0]["price"] == (90 if short else 110)
    assert p["obstacles"] == [{"name":"target-0", "price":95 if short else 105}]
    assert p["rr_tp1"] == pytest.approx(10/7)
    assert p["source_tradeable"] and p["refusal"] is None
    assert c["pricing_status"] == "PRICE_ACCEPTED_UNADMITTED"
    assert not c["tradeable"] and c["trade_plan"] is None
    assert not out["ready_for_replay"] and not out["ready_for_training"]
    assert not any(key in c for key in ["label","fill","outcome","net_R"])
    assert "trade_plan_pricing" not in out["missing_stages"]
    assert "admission" in out["missing_stages"]
    json.dumps(out, allow_nan=False)


@pytest.mark.parametrize("short", [False,True])
def test_m15_keeps_intraday_multiplier_not_scalp_stop(short):
    bars,args = fixture("15m",short)
    p = price(bars,args)["candidates"][0]["source_plan"]
    assert p["style"] == "intraday"
    assert p["stop"] == (109.5 if short else 90.5)
    assert p["risk_price"] == 9.5
    assert p["targets"][0]["price"] == (85 if short else 115)
    assert len(p["obstacles"]) == 2


@pytest.mark.parametrize("short", [False,True])
def test_source_far_target_without_obstacle_gets_measured_rung(short):
    bars,args = fixture(short=short,target_offsets=(30,40))
    p = price(bars,args)["candidates"][0]["source_plan"]
    assert p["targets"][0] == {"name":"1.5R","price":89.5 if short else 110.5}
    assert len(p["targets"]) == 3
    assert p["source_tradeable"] and p["rr_tp1"] == 1.5


def test_far_target_with_obstacle_is_refusal_not_losing_trade():
    bars,args = fixture(target_offsets=(5,30))
    c = price(bars,args)["candidates"][0]
    p = c["source_plan"]
    assert c["pricing_status"] == "PRICE_REFUSED"
    assert p["refusal"].startswith("יעד ראשון רחוק:")
    assert p["targets"] == [{"name":"target-1","price":130}]
    assert p["obstacles"] == [{"name":"target-0","price":105}]
    assert p["entry"] == 100 and p["stop"] == 93
    assert not p["source_tradeable"] and not c["tradeable"]
    assert "FAILURE" not in json.dumps(c)


def test_no_paying_target_preserves_refused_geometry():
    bars,args = fixture(target_offsets=(1,5))
    c = price(bars,args)["candidates"][0]
    p = c["source_plan"]
    assert c["pricing_status"] == "PRICE_REFUSED"
    assert p["targets"] == [] and p["rr_tp1"] == 0
    assert p["obstacles"] == [{"name":"target-1","price":105}]
    snap = c["pricing_snapshot"]
    assert snap["features"]["pricing.tp1_price"] is None
    assert snap["availability"]["pricing.tp1_price"] == "NOT_APPLICABLE"


@pytest.mark.parametrize("instrument", ["CME:GC","COMEX:GCZ6","OTHER:XAUUSD","CME:NQ"])
def test_unmapped_instrument_is_explicitly_unsupported_not_spot_alias(instrument):
    bars,args = fixture(instrument=instrument)
    out = price(bars,args)
    assert out["status"] == "BLOCKED" and out["blocker"] == "PRICING_UNSUPPORTED_INSTRUMENT"
    assert out["detection_status"] == "DETECTED_UNPRICED"
    c = out["candidates"][0]
    assert c["pricing_status"] == "UNAVAILABLE" and c["source_plan"] is None
    assert c["symbol"] == instrument and not c["tradeable"]


@pytest.mark.parametrize("instrument,offsets", [
    ("OANDA:NAS100USD",(200,300,500)),("BINANCE:BTCUSDT",(1000,2000,3000)),
])
@pytest.mark.parametrize("short", [False,True])
def test_other_original_source_instruments_keep_identity(instrument,offsets,short):
    bars,args = fixture(instrument=instrument,target_offsets=offsets,short=short)
    c = price(bars,args)["candidates"][0]
    assert c["source_plan"]["symbol"] == instrument
    assert c["source_plan"]["source_tradeable"]
    assert c["source_plan"]["risk_price"] == (95 if "NAS" in instrument else 460)


def test_prior_detection_result_is_not_mutated_or_reinterpreted():
    bars,args = fixture()
    before = detect_reversals_asof(bars,**args)
    out = price(bars,args)
    assert before == detect_reversals_asof(bars,**args)
    assert out["detection_evaluation_sha256"] == before["evaluation_sha256"]
    assert out["evaluation_sha256"] != before["evaluation_sha256"]
    assert out["candidates"][0]["candidate_id"] == before["candidates"][0]["candidate_id"]
    assert out["candidates"][0]["snapshot"] == before["candidates"][0]["snapshot"]


def test_generator_and_unordered_bar_input_are_reusable_and_deterministic():
    bars,args = fixture()
    expected = price(bars,args)
    assert price(iter(bars),args) == expected
    assert price(list(reversed(bars)),args) == expected


def test_later_or_changed_target_evidence_changes_evaluation_not_setup_id():
    bars,args = fixture()
    first = price(bars,args)
    last = args["level_snapshot"].levels[-1]
    changed = replace(args["level_snapshot"], levels=args["level_snapshot"].levels[:-1]+(replace(last,price=120),))
    later = price(bars,args,level_snapshot=changed)
    assert first["candidates"][0]["candidate_id"] == later["candidates"][0]["candidate_id"]
    assert first["evaluation_sha256"] != later["evaluation_sha256"]


def test_unavailable_levels_or_history_never_receive_prices():
    bars,args = fixture()
    for changes,why in [(dict(level_snapshot=None),"LEVELS_UNAVAILABLE"),
                        (dict(decision_time=args["decision_time"]+timedelta(seconds=371)),"STALE")]:
        result = price(bars,args,**changes)
        assert result["status"] == "BLOCKED" and result["blocker"] == why
        assert result["candidates"] == []
    missing = bars[:4]+bars[5:]
    assert price(missing,args)["blocker"] == "HISTORY_GAP"


def test_no_current_setup_does_not_become_pricing_refusal():
    bars,args = fixture()
    bars[-1] = replace(bars[-1],close=99)
    result = price(bars,args)
    assert result["status"] == "NO_CANDIDATE" and result["candidates"] == []
    assert result["blocker"] is None


def test_all_pricing_features_are_pre_entry_with_latest_dependency_publication():
    bars,args = fixture()
    close = args["decision_time"]
    bars[0] = replace(bars[0],available_at=close+timedelta(seconds=1))
    ls = replace(args["level_snapshot"],available_at=close+timedelta(seconds=2))
    cal = replace(schedule(bars),instrument=args["instrument"],available_at=close+timedelta(seconds=3))
    c = price(bars,args,decision_time=close+timedelta(seconds=4),level_snapshot=ls,session_schedule=cal)["candidates"][0]
    snap = c["pricing_snapshot"]
    assert snap["features"]["pricing.initial_risk_price"] == 7
    assert snap["features"]["pricing.rr_tp1"] == pytest.approx(10/7)
    assert snap["features"]["pricing.target_count"] == 2
    assert snap["features"]["pricing.obstacle_count"] == 1
    for p in snap["provenance"].values():
        assert p["phase"] == "PRE_ENTRY"
        assert p["observed_at"] == close.isoformat().replace("+00:00","Z")
        assert p["available_at"] == (close+timedelta(seconds=3)).isoformat().replace("+00:00","Z")
    assert snap["availability"]["pricing.refusal"] == "NOT_APPLICABLE"


def test_future_suffix_is_neither_atr_input_nor_pricing_evidence():
    bars,args = fixture()
    close = args["decision_time"]
    future = replace(bars[-1],opened_at=close,closed_at=close+timedelta(minutes=5),
                     available_at=close+timedelta(minutes=5),high=10000,low=1,volume=100000)
    assert price(bars+[future],args) == price(bars,args)


def test_nonpositive_source_stop_is_not_silently_repaired():
    bars,args = fixture(target_offsets=(10,20,30))
    # Scale a valid pattern down so the source's absolute gold stop band would
    # put a long stop below zero. This geometry must not enter a priced snapshot.
    bars = [replace(b,open=b.open/100,high=b.high/100,low=b.low/100,close=b.close/100) for b in bars]
    ls = replace(args["level_snapshot"],levels=tuple(replace(lv,price=lv.price/100) for lv in args["level_snapshot"].levels))
    with pytest.raises(ValueError,match="numeric|positive|geometry"):
        price(bars,args,level_snapshot=ls)


def test_repeated_quarter_names_require_distinct_identity_and_preserve_both_targets():
    bars,args = fixture(target_offsets=())
    ls = replace(args["level_snapshot"], levels=args["level_snapshot"].levels+(
        NamedLevel(name="Q-QUARTER", price=125, level_id="quarter:125"),
        NamedLevel(name="Q-QUARTER", price=175, level_id="quarter:175"),
    ))
    p = price(bars,args,level_snapshot=ls)["candidates"][0]["source_plan"]
    assert p["targets"] == [{"name":"1.5R","price":110.5},
                            {"name":"Q-QUARTER","price":125},
                            {"name":"Q-QUARTER","price":175}]


@pytest.mark.parametrize("level_id", ["", " x", "x ", 1, False])
def test_explicit_level_identity_must_be_valid_text(level_id):
    with pytest.raises(ValueError):
        NamedLevel(name="Q-QUARTER",price=125,level_id=level_id)


def test_ambiguous_or_repeated_level_identity_still_rejects():
    bars,args = fixture()
    first = NamedLevel(name="Q-QUARTER",price=125,level_id="q1")
    for second in [NamedLevel(name="Q-QUARTER",price=175),
                   NamedLevel(name="Q-QUARTER",price=175,level_id="q1"),
                   NamedLevel(name="Q-QUARTER",price=125,level_id="q2"),
                   NamedLevel(name="other",price=175,level_id="q1")]:
        with pytest.raises(ValueError):
            replace(args["level_snapshot"],levels=(first,second))


def test_distinct_source_level_id_changes_evaluation_fingerprint():
    bars,args = fixture()
    first = price(bars,args)
    old = args["level_snapshot"].levels
    changed = replace(args["level_snapshot"],levels=(replace(old[0],level_id="psy-low"),)+old[1:])
    assert price(bars,args,level_snapshot=changed)["evaluation_sha256"] != first["evaluation_sha256"]
