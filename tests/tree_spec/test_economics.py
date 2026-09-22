"""Synthetic resolved evidence only; expected amounts are hand calculated."""

from dataclasses import FrozenInstanceError, asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, Inexact, ROUND_DOWN, localcontext
from zoneinfo import ZoneInfo

import pytest


D = Decimal
T = datetime(2026, 9, 8, 12, tzinfo=timezone.utc)
POLICY = dict(
    policy_id="synthetic-v1", instrument="SYNTH:TEST", currency="USD",
    point_value=D("10"), quantity=D("2"), commission_per_side=D("1"),
    spread_points=D("0.1"), slippage_points_per_side=D("0.05"),
    pending_expiry_seconds=60, max_holding_seconds=300,
    fill_rule="supplied_verified_fills", simultaneous_rule="ambiguous",
    cost_basis="mid_price_plus_costs", provenance="synthetic cost assumptions",
)
TRADE = dict(
    candidate_id="synthetic-candidate", instrument="SYNTH:TEST", direction="LONG",
    decision_time=T, filled_at=T + timedelta(seconds=1),
    exited_at=T + timedelta(seconds=10), available_at=T + timedelta(seconds=11),
    entry_price=D("100"), initial_stop=D("98"), tp1=D("104"),
    exit_price=D("104"), exit_reason="TP1", evidence="synthetic settled fills",
)
POLICY_MONEY = (
    "point_value", "quantity", "commission_per_side", "spread_points",
    "slippage_points_per_side",
)
PRICES = ("entry_price", "initial_stop", "tp1", "exit_price")
TIMES = ("decision_time", "filled_at", "exited_at", "available_at")


@pytest.fixture
def api():
    from trading_system.tree_spec import economics

    return economics


def evaluate(api, *, policy=None, trade=None):
    return api.evaluate_resolved_trade(
        api.EconomicPolicy(**(POLICY | (policy or {}))),
        api.ResolvedTrade(**(TRADE | (trade or {}))),
    )


@pytest.mark.parametrize("direction,stop,target", [("LONG", "98", "104"), ("SHORT", "102", "96")])
def test_long_and_short_literal_net_economics(api, direction, stop, target):
    result = evaluate(api, trade=dict(direction=direction, initial_stop=D(stop), tp1=D(target), exit_price=D(target)))
    assert {key: result[key] for key in ("gross_pnl", "total_cost", "net_pnl", "initial_risk", "net_R")} == {
        "gross_pnl": "80", "total_cost": "6", "net_pnl": "74", "initial_risk": "40", "net_R": "1.85",
    }
    assert result["economic_label"] == "SUCCESS"
    assert result["candidate_id"] == "synthetic-candidate"
    assert result["policy_id"] == "synthetic-v1"
    assert result["instrument"] == "SYNTH:TEST"
    assert result["currency"] == "USD"
    assert result["label_end_time"] == "2026-09-08T12:00:10Z"
    assert result["available_at"] == "2026-09-08T12:00:11Z"
    assert result["provenance"] == POLICY["provenance"]
    assert result["evidence"] == TRADE["evidence"]
    assert not {"movement_success", "failure_probability", "trade_signal_score"} & result.keys()


@pytest.mark.parametrize("exit_price,reason,gross,net,r,label", [
    ("98", "STOP", "-40", "-46", "-1.15", "FAILURE"),
    ("100.3", "TIME_EXIT", "6", "0", "0", "BREAK_EVEN"),
    ("101", "INVALIDATION", "20", "14", "0.35", "SUCCESS"),
    ("99", "TIME_EXIT", "-20", "-26", "-0.65", "FAILURE"),
])
def test_fixed_initial_risk_and_labels_across_exit_reasons(api, exit_price, reason, gross, net, r, label):
    result = evaluate(api, trade=dict(exit_price=D(exit_price), exit_reason=reason))
    assert result["gross_pnl"] == gross
    assert result["net_pnl"] == net
    assert result["net_R"] == r
    assert result["initial_risk"] == "40"
    assert result["economic_label"] == label


def test_target_exit_can_lose_after_costs(api):
    result = evaluate(api, policy=dict(commission_per_side=D("40")))
    assert result["total_cost"] == "84"
    assert result["net_pnl"] == "-4"
    assert result["economic_label"] == "FAILURE"


def test_executable_fills_charge_only_position_commission(api):
    result = evaluate(api, policy=dict(cost_basis="executable_fills", spread_points=D("0"), slippage_points_per_side=D("0")))
    assert result["total_cost"] == "2"
    assert result["net_pnl"] == "78"
    assert result["net_R"] == "1.95"


@pytest.mark.parametrize("field", ["spread_points", "slippage_points_per_side"])
def test_executable_fills_reject_double_charged_price_costs(api, field):
    changes = dict(cost_basis="executable_fills", spread_points=D("0"), slippage_points_per_side=D("0"))
    changes[field] = D("0.01")
    with pytest.raises(ValueError):
        evaluate(api, policy=changes)


@pytest.mark.parametrize("field", list(POLICY))
def test_policy_requires_every_setting(api, field):
    values = POLICY.copy()
    del values[field]
    with pytest.raises(TypeError):
        api.EconomicPolicy(**values)


@pytest.mark.parametrize("field", list(TRADE))
def test_resolved_trade_requires_every_setting(api, field):
    values = TRADE.copy()
    del values[field]
    with pytest.raises(TypeError):
        api.ResolvedTrade(**values)


@pytest.mark.parametrize("name,values", [("EconomicPolicy", POLICY), ("ResolvedTrade", TRADE)])
def test_contracts_are_keyword_only_and_immutable(api, name, values):
    cls = getattr(api, name)
    with pytest.raises(TypeError):
        cls(*values.values())
    obj = cls(**values)
    with pytest.raises(FrozenInstanceError):
        setattr(obj, next(iter(values)), "changed")


@pytest.mark.parametrize("field", POLICY_MONEY)
@pytest.mark.parametrize("value", [None, True, False, 1, 0.1, "1", D("NaN"), D("sNaN"), D("Infinity"), D("-Infinity"), D("-1")])
def test_policy_rejects_invalid_money(api, field, value):
    with pytest.raises(ValueError):
        evaluate(api, policy={field: value})


@pytest.mark.parametrize("field", ["point_value", "quantity"])
def test_policy_requires_positive_position_and_point_value(api, field):
    with pytest.raises(ValueError):
        evaluate(api, policy={field: D("0")})


@pytest.mark.parametrize("field", PRICES)
@pytest.mark.parametrize("value", [None, True, False, 100, 100.0, "100", D("NaN"), D("sNaN"), D("Infinity"), D("-Infinity"), D("0"), D("-1")])
def test_trade_rejects_invalid_prices(api, field, value):
    with pytest.raises(ValueError):
        evaluate(api, trade={field: value})


@pytest.mark.parametrize("which,field", [("policy", f) for f in ("policy_id", "instrument", "currency", "provenance")] + [("trade", f) for f in ("candidate_id", "instrument", "evidence")])
@pytest.mark.parametrize("value", ["", "  ", None, True])
def test_identity_and_evidence_cannot_be_missing(api, which, field, value):
    with pytest.raises(ValueError):
        evaluate(api, **{which: {field: value}})


@pytest.mark.parametrize("field", ["pending_expiry_seconds", "max_holding_seconds"])
@pytest.mark.parametrize("value", [0, -1, True, False, 1.5, "60", None])
def test_durations_are_explicit_positive_integers(api, field, value):
    with pytest.raises(ValueError):
        evaluate(api, policy={field: value})


@pytest.mark.parametrize("field,value", [("fill_rule", "touch"), ("simultaneous_rule", "target_first"), ("cost_basis", "free")])
def test_unsupported_policy_modes_fail(api, field, value):
    with pytest.raises(ValueError):
        evaluate(api, policy={field: value})


@pytest.mark.parametrize("reason", ["UNFILLED", "AMBIGUOUS", "UNRESOLVED", "CANCELLED", "REJECTED", "PARTIAL", None])
def test_non_resolved_outcomes_cannot_be_labeled(api, reason):
    with pytest.raises(ValueError):
        evaluate(api, trade=dict(exit_reason=reason))


@pytest.mark.parametrize("direction", ["long", "BUY", "", None])
def test_unsupported_direction_fails(api, direction):
    with pytest.raises(ValueError):
        evaluate(api, trade=dict(direction=direction))


@pytest.mark.parametrize("instrument", ["OTHER:TEST", "SYNTH:OTHER", "TEST", "SYNTH:", ":TEST", " SYNTH:TEST", "SYNTH:TEST:EXTRA"])
def test_instrument_requires_exact_venue_symbol(api, instrument):
    with pytest.raises(ValueError):
        evaluate(api, trade=dict(instrument=instrument))


@pytest.mark.parametrize("instrument", ["TEST", "SYNTH:", ":TEST", "SYNTH:TEST:EXTRA", "SYNTH: TEST"])
def test_policy_rejects_malformed_instrument(api, instrument):
    with pytest.raises(ValueError):
        evaluate(api, policy=dict(instrument=instrument), trade=dict(instrument=instrument))


@pytest.mark.parametrize("direction,stop,tp1", [("LONG", "100", "104"), ("LONG", "101", "104"), ("LONG", "98", "100"), ("LONG", "98", "99"), ("SHORT", "100", "96"), ("SHORT", "99", "96"), ("SHORT", "102", "100"), ("SHORT", "102", "101")])
def test_stop_and_target_must_bracket_entry_in_trade_direction(api, direction, stop, tp1):
    with pytest.raises(ValueError):
        evaluate(api, trade=dict(direction=direction, initial_stop=D(stop), tp1=D(tp1)))


@pytest.mark.parametrize("field", TIMES)
@pytest.mark.parametrize("value", [T.replace(tzinfo=None), None, "2026-09-08T12:00:00Z"])
def test_timestamps_must_be_aware_datetimes(api, field, value):
    with pytest.raises(ValueError):
        evaluate(api, trade={field: value})


@pytest.mark.parametrize("changes", [dict(decision_time=T + timedelta(seconds=2)), dict(exited_at=T), dict(available_at=T + timedelta(seconds=9))])
def test_future_order_timestamps_are_rejected(api, changes):
    with pytest.raises(ValueError):
        evaluate(api, trade=changes)


@pytest.mark.parametrize("delay", [60, 61])
def test_fill_at_or_after_pending_expiry_is_rejected(api, delay):
    at = T + timedelta(seconds=delay)
    with pytest.raises(ValueError):
        evaluate(api, trade=dict(filled_at=at, exited_at=at, available_at=at))


def test_fill_just_before_expiry_and_exit_at_holding_limit_are_allowed(api):
    filled = T + timedelta(seconds=60, microseconds=-1)
    exited = filled + timedelta(seconds=300)
    assert evaluate(api, trade=dict(filled_at=filled, exited_at=exited, available_at=exited))["net_pnl"] == "74"
    with pytest.raises(ValueError):
        evaluate(api, trade=dict(filled_at=filled, exited_at=exited + timedelta(microseconds=1), available_at=exited + timedelta(seconds=1)))


def test_same_instant_exit_is_valid_with_evidence(api):
    result = evaluate(api, trade={field: T for field in TIMES})
    assert result["label_end_time"] == "2026-09-08T12:00:00Z"


def test_utc_serialization_is_independent_of_offset(api):
    changes = {field: TRADE[field].astimezone(timezone(timedelta(hours=3))) for field in TIMES}
    assert evaluate(api, trade=changes) == evaluate(api)


def test_dst_fold_valid_order_and_elapsed_time_use_utc(api):
    zone = ZoneInfo("America/New_York")
    early = datetime(2026, 11, 1, 1, 50, tzinfo=zone, fold=0)  # 05:50 UTC
    late = datetime(2026, 11, 1, 1, 10, tzinfo=zone, fold=1)  # 06:10 UTC
    result = evaluate(api, policy=dict(max_holding_seconds=1200), trade=dict(decision_time=early, filled_at=early, exited_at=late, available_at=late))
    assert result["label_end_time"] == "2026-11-01T06:10:00Z"
    assert result["available_at"] == "2026-11-01T06:10:00Z"
    with pytest.raises(ValueError):
        evaluate(api, policy=dict(max_holding_seconds=1199), trade=dict(decision_time=early, filled_at=early, exited_at=late, available_at=late))


@pytest.mark.parametrize("boundary", ["decision", "exit", "available", "expiry"])
def test_dst_fold_cannot_hide_bad_chronology_or_expiry(api, boundary):
    zone = ZoneInfo("America/New_York")
    early = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    late = early.replace(fold=1)
    changes = dict.fromkeys(TIMES, early)
    if boundary == "decision":
        changes["decision_time"] = late
    elif boundary == "exit":
        changes.update(filled_at=late, available_at=late)
    elif boundary == "available":
        changes["exited_at"] = late
    else:
        changes.update(filled_at=late, exited_at=late, available_at=late)
    policy = dict(pending_expiry_seconds=7200, max_holding_seconds=7200)
    if boundary == "expiry":
        policy["pending_expiry_seconds"] = 3600
    with pytest.raises(ValueError):
        evaluate(api, policy=policy, trade=changes)


def test_policy_hash_is_stable_and_sensitive_to_explicit_settings(api):
    baseline = evaluate(api)["policy_sha256"]
    assert len(baseline) == 64
    assert set(baseline) <= set("0123456789abcdef")
    assert evaluate(api)["policy_sha256"] == baseline
    assert evaluate(api, policy=dict(commission_per_side=D("1.00")))["policy_sha256"] == baseline
    for change in (dict(commission_per_side=D("2")), dict(simultaneous_rule="stop_first"), dict(provenance="another synthetic assumption"), dict(pending_expiry_seconds=61), dict(max_holding_seconds=301)):
        assert evaluate(api, policy=change)["policy_sha256"] != baseline


def test_caller_decimal_context_cannot_change_arithmetic_or_hash(api):
    baseline = evaluate(api)
    with localcontext() as ctx:
        ctx.prec = 2
        ctx.rounding = ROUND_DOWN
        ctx.Emax = 1
        ctx.Emin = -1
        ctx.traps[Inexact] = True
        assert evaluate(api) == baseline
        assert ctx.prec == 2
        assert ctx.traps[Inexact] is True


def test_nonterminating_net_r_is_deterministic_under_caller_precision(api):
    changes = dict(initial_stop=D("97"), exit_price=D("101"))
    with localcontext() as ctx:
        ctx.prec = 3
        low = evaluate(api, trade=changes)
        ctx.prec = 80
        high = evaluate(api, trade=changes)
    assert low == high
    assert low["net_pnl"] == "14"
    assert low["initial_risk"] == "60"
    assert low["net_R"].startswith("0.233333333333333333333333333333")


@pytest.mark.parametrize("value", [D("1E+999999"), D("1E-999999"), D("1.000000000000000000000000000000000000000000000000001")])
def test_unrepresentable_amounts_fail_instead_of_silently_rounding(api, value):
    with pytest.raises(ValueError):
        evaluate(api, policy=dict(point_value=value))


def test_nonfinite_arithmetic_is_rejected_even_if_caller_disables_traps(api):
    with localcontext() as ctx:
        for signal in ctx.traps:
            ctx.traps[signal] = False
        with pytest.raises(ValueError):
            evaluate(api, policy=dict(point_value=D("1E+900"), quantity=D("1E+900")))


def test_tiny_nonzero_net_is_not_rounded_to_break_even(api):
    result = evaluate(api, policy=dict(commission_per_side=D("39.999999999999999999999999999999999999999999999999"), spread_points=D("0"), slippage_points_per_side=D("0")))
    assert D(result["net_pnl"]) == D("2E-48")
    assert result["economic_label"] == "SUCCESS"


def test_evaluation_does_not_mutate_supplied_contracts(api):
    policy, trade = api.EconomicPolicy(**POLICY), api.ResolvedTrade(**TRADE)
    before = (asdict(policy), asdict(trade))
    result = api.evaluate_resolved_trade(policy, trade)
    result["net_pnl"] = "tampered"
    assert (asdict(policy), asdict(trade)) == before
    assert api.evaluate_resolved_trade(policy, trade)["net_pnl"] == "74"
