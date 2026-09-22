"""Real dependency integration, not a full historical map or feed certification."""
from datetime import datetime, timedelta, timezone

import pandas as pd

from trading_system.tree_replay._vendor.ranges import average_range
from trading_system.tree_replay.corrections import CorrectionEvidence, assess_correction_asof


def test_asof_shape_threshold_changes_range_verification_without_shifting_prices():
    # Breaks if the adapter uses today's clock, changes source >= to >, or the
    # source range formula changes prices when its broker_bars flag changes.
    threshold = datetime(2020, 2, 1, tzinfo=timezone.utc)
    correction = CorrectionEvidence(
        evidence_id="synthetic-correction", frame_id="synthetic-daily",
        instrument="OANDA:XAUUSD", version="fixture-v1",
        observed_at=threshold - timedelta(seconds=1),
        available_at=threshold - timedelta(seconds=1),
        provenance="synthetic frame evidence", source="tv_spliced",
        confidence="high", offset=12, note="Not a live feed or broker attestation",
        tv_from=threshold - timedelta(days=20),
    )
    frame = pd.DataFrame(
        [dict(open=100, high=105, low=95, close=100),
         dict(open=100, high=110, low=90, close=100),
         dict(open=100, high=115, low=95, close=110)],
        index=pd.date_range("2020-01-29", periods=3, tz="UTC"),
    )
    original = frame.copy(deep=True)
    observations = []
    for decision, verified in ((threshold - timedelta(microseconds=1), False),
                               (threshold, True)):
        assessed = assess_correction_asof(
            correction, instrument=correction.instrument, frame_id=correction.frame_id,
            decision_time=decision, lookback_days=20, max_age_seconds=1,
        )
        assert assessed["status"] == "ASSESSED"
        assert assessed["blocker"] is None
        assert assessed["broker_shape_ok"] is verified
        assert assessed["unverified"] is False
        assert assessed["ready_for_replay"] is False
        assert assessed["ready_for_training"] is False
        levels = average_range(frame, 2, broker_bars=assessed["broker_shape_ok"])
        assert levels["verified"] is verified
        assert levels["range"] == 15
        assert levels["high"] == 110
        assert levels["low"] == 100
        observations.append(assessed)
    assert observations[0]["evidence_hash"] != observations[1]["evidence_hash"]
    pd.testing.assert_frame_equal(frame, original)
