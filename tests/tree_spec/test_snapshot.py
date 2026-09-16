from dataclasses import replace
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest


T = datetime(2026, 9, 8, 12, tzinfo=timezone.utc)


@pytest.fixture
def api():
    from trading_system.tree_spec import snapshot

    return snapshot


@pytest.fixture
def definition(api):
    return api.FeatureDefinition("ema_gap", "number", "ticks", "PRE_ENTRY", True)


@pytest.fixture
def observation(api):
    return api.FeatureObservation("ema_gap", 3.5, "KNOWN", T, T, "fixture:quotes")


def build(api, definition, observation):
    return api.build_snapshot("s1", T, (definition,), (observation,))


@pytest.mark.parametrize("field", ["observed_at", "available_at"])
def test_future_information_cannot_enter_pre_entry_snapshot(api, definition, observation, field):
    with pytest.raises(ValueError, match="future"):
        build(api, definition, replace(observation, **{field: T + timedelta(seconds=1)}))


@pytest.mark.parametrize("field", ["observed_at", "available_at"])
def test_naive_observation_time_is_rejected(api, definition, observation, field):
    with pytest.raises(ValueError, match="timezone"):
        build(api, definition, replace(observation, **{field: T.replace(tzinfo=None)}))


def test_naive_decision_time_is_rejected(api, definition, observation):
    with pytest.raises(ValueError, match="timezone"):
        api.build_snapshot("s1", T.replace(tzinfo=None), (definition,), (observation,))


def test_publication_before_observation_is_rejected(api, definition, observation):
    with pytest.raises(ValueError, match="before observation"):
        build(api, definition, replace(observation, available_at=T - timedelta(seconds=1)))


@pytest.mark.parametrize("phase", ["POST_ENTRY", "OUTCOME", "invalid"])
def test_non_pre_entry_definition_is_rejected(api, definition, observation, phase):
    with pytest.raises(ValueError, match="PRE_ENTRY"):
        build(api, replace(definition, phase=phase), observation)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, "3", {}, []])
def test_number_features_do_not_accept_nonfinite_or_wrong_type_values(api, definition, observation, value):
    with pytest.raises(ValueError, match="number"):
        build(api, definition, replace(observation, value=value))


def test_known_zero_and_false_remain_distinct_from_missing(api, definition, observation):
    zero = build(api, definition, replace(observation, value=0)).to_payload()
    false = build(api, replace(definition, dtype="boolean", unit="boolean"), replace(observation, value=False)).to_payload()
    assert type(zero["features"]["ema_gap"]) is int
    assert zero["features"]["ema_gap"] == 0
    assert false["features"]["ema_gap"] is False
    assert false["availability"]["ema_gap"] == "KNOWN"


@pytest.mark.parametrize("status", ["UNKNOWN", "UNAVAILABLE", "NOT_APPLICABLE", "STALE"])
def test_required_missing_blocks_and_is_not_replaced_by_zero(api, definition, observation, status):
    result = build(api, definition, replace(observation, value=None, status=status))
    assert result.eligible is False
    assert result.blocking_features == ("ema_gap",)
    assert result.to_payload()["features"]["ema_gap"] is None


def test_optional_missing_preserves_none_without_blocking(api, definition, observation):
    result = build(api, replace(definition, required=False), replace(observation, value=None, status="UNAVAILABLE"))
    assert result.eligible is True
    assert result.to_payload()["availability"]["ema_gap"] == "UNAVAILABLE"


@pytest.mark.parametrize(("status", "value"), [("UNKNOWN", 0), ("STALE", 5), ("KNOWN", None), ("made-up", None)])
def test_status_and_payload_cannot_contradict_each_other(api, definition, observation, status, value):
    with pytest.raises(ValueError):
        build(api, definition, replace(observation, value=value, status=status))


@pytest.mark.parametrize("case", ["duplicate_definition", "duplicate_observation", "unknown", "missing", "empty"])
def test_snapshot_requires_one_observation_per_registered_feature(api, definition, observation, case):
    definitions, observations = (definition,), (observation,)
    if case == "duplicate_definition":
        definitions += (definition,)
    elif case == "duplicate_observation":
        observations += (observation,)
    elif case == "unknown":
        observations = (replace(observation, feature_id="future_pnl"),)
    elif case == "missing":
        observations = ()
    else:
        definitions, observations = (), ()
    with pytest.raises(ValueError):
        api.build_snapshot("s1", T, definitions, observations)


def test_snapshot_copies_inputs_and_normalizes_time_to_utc(api, definition, observation):
    local_time = T.astimezone(timezone(timedelta(hours=3)))
    definitions, observations = [definition], [replace(observation, available_at=local_time)]
    result = api.build_snapshot("s1", local_time, definitions, observations)
    definitions.clear()
    observations.clear()
    payload = result.to_payload()
    assert payload["features"] == {"ema_gap": 3.5}
    assert payload["decision_time"] == "2026-09-08T12:00:00Z"
    assert payload["provenance"]["ema_gap"]["available_at"] == "2026-09-08T12:00:00Z"
    payload["features"]["ema_gap"] = 100
    assert result.to_payload()["features"]["ema_gap"] == 3.5


@pytest.mark.parametrize(("dtype", "value", "valid"), [("category", "REVERSAL", True), ("category", 0, False), ("boolean", 1, False), ("unknown", 1, False)])
def test_declared_scalar_type_is_enforced(api, definition, observation, dtype, value, valid):
    if valid:
        changed = replace(definition, dtype=dtype)
        observed = replace(observation, value=value)
        assert build(api, changed, observed).to_payload()["features"]["ema_gap"] == "REVERSAL"
    else:
        with pytest.raises(ValueError):
            changed = replace(definition, dtype=dtype)
            observed = replace(observation, value=value)
            build(api, changed, observed)


@pytest.mark.parametrize("field", ["feature_id", "unit"])
def test_definition_requires_identity_and_unit(api, definition, observation, field):
    with pytest.raises(ValueError):
        build(api, replace(definition, **{field: ""}), observation)


def test_observation_requires_provenance(api, definition, observation):
    with pytest.raises(ValueError, match="source"):
        build(api, definition, replace(observation, source=""))


@pytest.mark.parametrize("field", ["observed_at", "available_at"])
def test_repeated_dst_hour_cannot_hide_future_information(api, definition, observation, field):
    zone = ZoneInfo("America/New_York")
    decision = datetime(2026, 11, 1, 1, 45, tzinfo=zone, fold=0)  # 05:45 UTC
    future = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=1)  # 06:30 UTC
    item = replace(observation, observed_at=decision, available_at=decision)
    item = replace(item, **{field: future})
    with pytest.raises(ValueError, match="future"):
        api.build_snapshot("s1", decision, (definition,), (item,))


def test_repeated_dst_hour_does_not_reject_an_earlier_instant(api, definition, observation):
    zone = ZoneInfo("America/New_York")
    decision = datetime(2026, 11, 1, 1, 20, tzinfo=zone, fold=1)  # 06:20 UTC
    past = datetime(2026, 11, 1, 1, 50, tzinfo=zone, fold=0)  # 05:50 UTC
    item = replace(observation, observed_at=past, available_at=past)
    assert api.build_snapshot("s1", decision, (definition,), (item,)).eligible is True


def test_publication_order_uses_instants_across_dst_fold(api, definition, observation):
    zone = ZoneInfo("America/New_York")
    item = replace(
        observation,
        observed_at=datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=1),
        available_at=datetime(2026, 11, 1, 1, 45, tzinfo=zone, fold=0),
    )
    decision = datetime(2026, 11, 1, 2, 0, tzinfo=zone)
    with pytest.raises(ValueError, match="before observation"):
        api.build_snapshot("s1", decision, (definition,), (item,))
