"""Source-faithful planned prices on as-of setups, not admission or execution."""
import math

import pandas as pd

from trading_system.tree_spec.snapshot import FeatureDefinition, FeatureObservation, build_snapshot
from .bars import select_closed_bars
from .reversal import SOURCE_COMMIT, _hash, _numeric_frame, detect_reversals_asof


PRICING_VERSION = "chartdesk-closed-reversal-pricing-v1"
# The original producer's traded identities, not a futures-to-spot conversion.
SUPPORTED_INSTRUMENTS = frozenset({"OANDA:XAUUSD", "OANDA:NAS100USD", "BINANCE:BTCUSDT"})


def _finite(value, name, *, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"nonfinite numeric source pricing result: {name}")
    if positive and value <= 0:
        raise ValueError(f"source pricing geometry must be positive: {name}")
    return float(value)


def _source_plan(plan, zone):
    values = {name: _finite(getattr(plan, name), name, positive=True)
              for name in ("entry", "stop", "atr")}
    low, high = (_finite(value, "entry zone", positive=True) for value in zone)
    values.update(entry_zone={"low":low, "high":high},
                  risk_price=_finite(plan.risk, "risk", positive=True),
                  rr_tp1=_finite(plan.rr, "rr"), rr_far=_finite(plan.rr_far, "rr_far"))
    for kind in ("targets", "obstacles"):
        values[kind] = [{"name":name, "price":_finite(price, kind, positive=True)}
                        for name, price in getattr(plan, kind)]
    return {**values, "symbol":plan.symbol, "source_direction":plan.direction,
            "style":plan.style, "refusal":plan.refusal, "source_tradeable":plan.tradeable,
            "reasons":list(plan.reasons), "warnings":list(plan.warnings)}


def _pricing_snapshot(plan, *, snapshot_id, decision_time, observed_at, available_at, source):
    fields = [
        ("entry_price", plan["entry"], "number", "price"),
        ("entry_zone_low", plan["entry_zone"]["low"], "number", "price"),
        ("entry_zone_high", plan["entry_zone"]["high"], "number", "price"),
        ("stop_price", plan["stop"], "number", "price"),
        ("initial_risk_price", plan["risk_price"], "number", "price_distance"),
        ("atr", plan["atr"], "number", "price"),
        ("rr_tp1", plan["rr_tp1"], "number", "reward_risk_ratio"),
        ("rr_far", plan["rr_far"], "number", "reward_risk_ratio"),
        ("target_count", len(plan["targets"]), "number", "count"),
        ("obstacle_count", len(plan["obstacles"]), "number", "count"),
        ("source_tradeable", plan["source_tradeable"], "boolean", "boolean"),
        ("refusal", plan["refusal"], "category", "source_refusal"),
    ]
    for i in range(3):
        value = plan["targets"][i]["price"] if i < len(plan["targets"]) else None
        fields.append((f"tp{i+1}_price", value, "number", "price"))
    definitions, observations = [], []
    for name, value, dtype, unit in fields:
        feature_id = f"pricing.{name}"
        definitions.append(FeatureDefinition(feature_id, dtype, unit, "PRE_ENTRY", False))
        observations.append(FeatureObservation(
            feature_id, value, "NOT_APPLICABLE" if value is None else "KNOWN",
            observed_at, available_at, source))
    return build_snapshot(snapshot_id, decision_time, definitions, observations).to_payload()


def price_reversals_asof(bars, *, snapshot_id, instrument, timeframe, decision_time,
                         history_start, max_age_seconds, level_snapshot,
                         max_level_age_seconds, session_schedule=None) -> dict:
    """Detect from validated inputs and compute original planned geometry.

    Source pricing acceptance is NOT whole-producer acceptance: no account state,
    news calendar, arbitration, pending-order lifecycle, fill or economic outcome
    is reconstructed here. Unsupported identities cannot inherit spot rules.
    """
    bars = tuple(bars)  # a generator must feed detection and pricing identically
    params = dict(snapshot_id=snapshot_id, instrument=instrument, timeframe=timeframe,
                  decision_time=decision_time, history_start=history_start,
                  max_age_seconds=max_age_seconds, level_snapshot=level_snapshot,
                  max_level_age_seconds=max_level_age_seconds, session_schedule=session_schedule)
    detection = detect_reversals_asof(bars, **params)
    digest = _hash({"detection_evaluation_sha256":detection["evaluation_sha256"],
                    "source_commit":SOURCE_COMMIT, "pricing_version":PRICING_VERSION})
    result = {**detection, "schema_version":"tree-priced-reversal-v1",
              "detection_status":detection["status"],
              "detection_evaluation_sha256":detection["evaluation_sha256"],
              "evaluation_sha256":digest,
              "calculation":{**detection["calculation"], "pricing_adapter_version":PRICING_VERSION}}
    for candidate in result["candidates"]:
        candidate.update(pricing_status="UNAVAILABLE", source_plan=None, pricing_snapshot=None)
    if not result["candidates"]:
        return result
    if instrument not in SUPPORTED_INSTRUMENTS:
        result.update(status="BLOCKED", blocker="PRICING_UNSUPPORTED_INSTRUMENT")
        return result

    from ._vendor.level_reversal import Reversal
    from ._vendor import pricing, reversal_pricing
    window_params = dict(instrument=instrument, timeframe=timeframe, decision_time=decision_time,
                         history_start=history_start, max_age_seconds=max_age_seconds)
    if session_schedule is None:
        window = select_closed_bars(bars, **window_params)
    else:
        from .session_bars import select_session_bars
        window = select_session_bars(bars, **window_params, session_schedule=session_schedule)
    if window.blocker is not None:
        raise ValueError("pricing window disagrees with detection input evidence")
    frame = _numeric_frame(window.bars)
    available = max(level_snapshot.available_at, *(b.available_at for b in window.bars))
    if session_schedule is not None:
        available = max(available, window.calendar_available_at)
    source = f"chart-desk@{SOURCE_COMMIT};{PRICING_VERSION};evaluation={digest}"
    for candidate in result["candidates"]:
        event = Reversal(
            symbol=candidate["symbol"], timeframe=candidate["timeframe"],
            direction=candidate["source_direction"], level_name=candidate["level_name"],
            level_price=candidate["level_price"], approach=candidate["approach"],
            pattern=candidate["pattern"], vector_kind=candidate["vector_kind"],
            vector_open_time=pd.Timestamp(candidate["vector_open_time"]),
            confirmation_open_time=pd.Timestamp(candidate["confirmation_open_time"]),
            confirmed_at=pd.Timestamp(candidate["confirmed_at"]),
            sweep_extreme=candidate["sweep_extreme"], close=candidate["close"],
            event_id=candidate["source_event_id"])
        try:
            plan = reversal_pricing.build_plan(event, level_snapshot.levels, frame)
            payload = _source_plan(plan, pricing.entry_zone(instrument, plan.entry))
        except (FloatingPointError, OverflowError, ZeroDivisionError) as exc:
            raise ValueError("numeric overflow in source pricing geometry") from exc
        candidate.update(
            source_plan=payload,
            pricing_status="PRICE_ACCEPTED_UNADMITTED" if payload["source_tradeable"] else "PRICE_REFUSED",
            pricing_snapshot=_pricing_snapshot(
                payload, snapshot_id=f"{snapshot_id}:pricing:{candidate['candidate_id']}",
                decision_time=window.decision_time, observed_at=event.confirmed_at,
                available_at=available, source=source))
    result["status"] = "PRICING_EVALUATED"
    result["missing_stages"] = [stage for stage in result["missing_stages"] if stage != "trade_plan_pricing"]
    return result
