"""Synthetic numerical cases and inert-text audit tampering; no live imports."""

import ast
import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]


def detector():
    return importlib.import_module("trading_system.tree_replay._vendor.level_reversal")


def classify(frame, **kwargs):
    return importlib.import_module("trading_system.tree_replay._vendor.pvsra").pvsra(frame, **kwargs)


def history(tf="5m", short=False, tier="climax"):
    # Historical spread-volume = 1000; the setup's spread-volume stays below it.
    # Only its independently specified 200% / 150% volume makes it a vector.
    count = 13 if tf == "5m" else 12
    frame = pd.DataFrame(
        [[103.0, 108.0, 98.0, 102.0, 100.0]] * count,
        columns=["open", "high", "low", "close", "volume"],
        index=pd.date_range("2026-09-09T00:00Z", periods=count, freq=tf.replace("m", "min")),
    )
    volume = 200.0 if tier == "climax" else 150.0
    if tf == "5m":
        frame.iloc[-2] = [102.0, 102.0, 98.0, 99.0, volume]
        frame.iloc[-1] = [99.0, 102.0, 99.0, 101.0, 100.0]
    else:
        frame.iloc[-1] = [102.0, 102.0, 98.0, 101.0, volume]
    if short:
        original = frame.copy()
        frame["open"] = 200 - original.open
        frame["close"] = 200 - original.close
        frame["high"] = 200 - original.low
        frame["low"] = 200 - original.high
    return frame


def detect(frame, tf="5m", levels=None, **kwargs):
    return detector().detect_frame(
        "SYNTH", tf, frame, [("PSY-LO", 100.0)] if levels is None else levels,
        now=kwargs.pop("now", frame.index[-1] + pd.Timedelta(minutes=int(tf[:-1]))),
        **kwargs,
    )


@pytest.mark.parametrize("short,direction,climax,rising", [
    (False, "לונג", "red", "violet"), (True, "שורט", "green", "blue"),
])
@pytest.mark.parametrize("tf,tier", [("5m", "climax"), ("15m", "climax"), ("15m", "rising")])
def test_detects_exact_timeframe_direction_and_vector(short, direction, climax, rising, tf, tier):
    frame = history(tf, short, tier)
    original = frame.copy(deep=True)
    result = detect(frame, tf)
    assert len(result) == 1
    event = result[0]
    assert event.direction == direction
    assert event.vector_kind == (climax if tier == "climax" else rising)
    assert event.confirmed_at == frame.index[-1] + pd.Timedelta(minutes=int(tf[:-1]))
    assert event.confirmation_open_time == frame.index[-1]
    assert event.sweep_extreme == (102.0 if short else 98.0)
    assert event.pattern == ("two_bar_" if tf == "5m" else "single_bar_") + ("reject" if short else "reclaim")
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("short", [False, True])
def test_m5_does_not_accept_rising_tier(short):
    assert detect(history(short=short, tier="rising")) == []


def test_pvsra_prior_ten_excludes_current_and_uses_inclusive_spread_volume_climax():
    frame = history()
    frame.iloc[-3] = [102, 107, 97, 102, 100]
    frame.iloc[-1] = [102, 107, 97, 102, 100]
    frame.iloc[-2] = [102, 107, 97, 102, 100]
    result = classify(frame)
    assert not result.climax.iloc[:10].any()
    assert result.avg_volume_10.iloc[10] == 100
    assert result.max_sv_10.iloc[10] == 1000
    assert result.kind.iloc[10] == "green"  # equality at spread-volume maximum
    frame.iloc[-1] = [102, 103, 101, 102, 200]
    result = classify(frame)
    assert result.avg_volume_10.iloc[-1] == 100
    assert result.vol_ratio.iloc[-1] == 2
    assert result.kind.iloc[-1] == "green"


@pytest.mark.parametrize("volume,kind", [(149.999, "down"), (150, "violet"), (199.999, "violet"), (200, "red")])
def test_pvsra_volume_threshold_boundaries(volume, kind):
    frame = history("15m")
    frame.iloc[-1, frame.columns.get_loc("volume")] = volume
    assert classify(frame).kind.iloc[-1] == kind


@pytest.mark.parametrize("missing", [False, True])
def test_pvsra_missing_or_zero_volume_is_explicitly_unavailable(missing):
    frame = history()
    frame["volume"] = 0
    if missing:
        frame = frame.drop(columns="volume")
    result = classify(frame)
    assert not result.available.any()
    assert not result.climax.any()
    assert not result.rising.any()
    assert result.kind.iloc[-2:].tolist() == ["down", "up"]


def test_pvsra_custom_lookback_and_no_auction_api():
    result = classify(history(), lookback=3)
    assert result.avg_volume_10.iloc[:3].isna().all()
    assert result.avg_volume_10.iloc[3] == 100
    with pytest.raises(TypeError):
        classify(history(), auction=False)


@pytest.mark.parametrize("tf", ["5m", "15m"])
def test_unfinished_stale_and_nonadjacent_evidence_cannot_detect(tf):
    frame = history(tf)
    close = frame.index[-1] + pd.Timedelta(minutes=int(tf[:-1]))
    assert detect(frame, tf, now=close - pd.Timedelta(microseconds=1)) == []
    assert len(detect(frame, tf, now=close + pd.Timedelta(seconds=370), max_age_s=370)) == 1
    assert detect(frame, tf, now=close + pd.Timedelta(seconds=370, microseconds=1), max_age_s=370) == []
    frame.index = frame.index[:-1].append(pd.DatetimeIndex([frame.index[-1] + pd.Timedelta(minutes=int(tf[:-1]))]))
    assert detect(frame, tf) == []


def test_level_order_breaks_equal_distance_ties_and_nearest_close_wins():
    frame = history()
    assert detect(frame, levels=[("PSY-LO", 100), ("YDAY-LO", 100)])[0].level_name == "PSY-LO"
    assert detect(frame, levels=[("YDAY-LO", 100), ("PSY-LO", 100)])[0].level_name == "YDAY-LO"
    assert detect(frame, levels=[("PSY-LO", 100), ("YDAY-LO", 100.5)])[0].level_name == "YDAY-LO"


def test_only_exact_eligible_level_names_are_admitted():
    frame = history()
    assert detect(frame, levels=[("EMA200-1h-extra", 100), ("QUARTER", 100)]) == []
    assert detect(frame, levels=[SimpleNamespace(name="EMA200-1h", price=100)])[0].level_name == "EMA200-1h"


def test_event_vector_bucket_differs_from_confirmation_dedup_bucket():
    frame = history()
    event = detect(frame)[0]
    assert event.event_id == "SYNTH|לונג|2026-09-09T00:45:00+00:00"
    assert event.confirmed_at == pd.Timestamp("2026-09-09T01:05Z")
    # Another turn has a different vector bucket. Initially the confirmation
    # buckets also differ; shifting both turns by five minutes merges only
    # their confirmation buckets, so the newest confirmation then wins.
    suffix = pd.DataFrame([[101, 102, 98, 99, 250], [99, 102, 99, 101, 100]],
                          columns=frame.columns,
                          index=pd.date_range("2026-09-09T01:05Z", periods=2, freq="5min"))
    result = detect(pd.concat([frame, suffix]))
    # The second close is 01:15, hence a distinct dedup bucket and both survive.
    assert len(result) == 2
    assert [e.event_id for e in result] == [
        "SYNTH|לונג|2026-09-09T01:00:00+00:00",
        "SYNTH|לונג|2026-09-09T00:45:00+00:00",
    ]
    shifted = pd.concat([frame, suffix])
    shifted.index = shifted.index - pd.Timedelta(minutes=5)
    assert len(detect(shifted)) == 1  # closes 01:00 and 01:10 share a bucket


def test_normalisation_keeps_last_revision_and_sorts_without_changing_source_input():
    frame = history()
    bad = frame.iloc[[-1]].copy()
    bad["close"] = 99
    combined = pd.concat([bad, frame.iloc[::-1]])
    pd.testing.assert_frame_equal(detector()._normalise(combined), frame, check_freq=False)
    assert detect(combined, now=pd.Timestamp("2026-09-09T02:00Z")) == detect(frame)


@pytest.mark.parametrize("tf,field,value", [
    ("5m", "prior", 100), ("5m", "vector", 100), ("5m", "confirmation", 100),
    ("15m", "prior", 100), ("15m", "confirmation", 99),
])
def test_directional_arrival_and_reclaim_are_required(tf, field, value):
    frame = history(tf)
    index = {"prior": -3 if tf == "5m" else -2, "vector": -2, "confirmation": -1}[field]
    frame.iloc[index, frame.columns.get_loc("close")] = value
    assert detect(frame, tf) == []


def test_short_history_and_unsupported_timeframe_are_empty():
    assert detect(history().iloc[:11]) == []
    assert detect(history(), "30m") == []


def blob(text):
    data = text.encode("utf-8")
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


@pytest.fixture
def audit(tmp_path, monkeypatch):
    """Portable source-shaped text. Patch trusted pins only for this fixture.

    The real pinned files are verified separately by the required CLI. The
    raising sentinel would make any accidental source execution fail loudly.
    """
    from tools import check_reversal_source_parity as checker

    config = json.loads((ROOT / "configs/trees/level-reversal-contracts.json").read_text(encoding="utf-8"))
    source = tmp_path / "source"
    vendor_root = tmp_path / "engine"
    for row in config["files"]:
        if row["vendor_path"]:
            target = vendor_root / row["vendor_path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text((ROOT / row["vendor_path"]).read_text(encoding="utf-8"), encoding="utf-8")
    level = (vendor_root / config["files"][0]["vendor_path"]).read_text(encoding="utf-8")
    pvsra = ast.parse((vendor_root / config["files"][1]["vendor_path"]).read_text(encoding="utf-8"))
    fn = next(n for n in pvsra.body if isinstance(n, ast.FunctionDef))
    fn.args = ast.parse('def pvsra(df: pd.DataFrame, lookback: int = 10, *, auction: bool | pd.Series = False, session_tz: str = A.DEFAULT_TZ) -> pd.DataFrame: pass').body[0].args
    body = fn.body[1:] if ast.get_docstring(fn) is not None else fn.body
    setup = ast.parse('slots = A.resolve_slots(df.index, auction, session_tz)\namask = None if slots is None else slots.ne("")\nextra: dict = {}\nif amask is None or not bool(amask.any()):\n    slots = None\nelse:\n    raise RuntimeError("auction not used")').body
    guard = ast.parse('if slots is not None:\n    raise RuntimeError("auction not used")').body
    fn.body = [ast.Expr(value=ast.Constant(value="Synthetic source fixture")), *body[:7], *setup, *body[7:-1], *guard, body[-1]]
    texts = {
        "chartdesk/level_reversal.py": level,
        "chartdesk/tr.py": ast.unparse(ast.fix_missing_locations(pvsra)),
        "chartdesk/auction.py": 'def resolve_slots(index, auction, tz: str = DEFAULT_TZ) -> pd.Series | None:\n    """Synthetic source fixture."""\n    if auction is False or auction is None:\n        return None\n    raise RuntimeError("not the default path")\n',
    }
    pins = {}
    for row in config["files"]:
        path = source / row["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        text = texts[row["path"]] + '\nraise RuntimeError("SOURCE MUST NOT EXECUTE")\n'
        path.write_text(text, encoding="utf-8")
        pins[row["path"]] = row["git_blob_sha1"] = blob(text)
    contract = vendor_root / "configs/trees/level-reversal-contracts.json"
    contract.parent.mkdir(parents=True, exist_ok=True)
    contract.write_text(json.dumps(config), encoding="utf-8")
    baseline = contract.with_name("existing-alerts-baseline.json")
    baseline.write_text(json.dumps({"repositories": [{"name": "chart-desk", "commit": checker.SOURCE_COMMIT}]}), encoding="utf-8")
    monkeypatch.setattr(checker, "ROOT", vendor_root)
    monkeypatch.setattr(checker, "CONTRACT", contract)
    monkeypatch.setattr(checker, "SOURCE_BLOBS", pins)
    return checker, source, vendor_root


def test_audit_accepts_inert_source_and_never_enables_readiness(audit):
    checker, source, _ = audit
    report = checker.check_source_parity(source)
    assert report["blockers"] == []
    assert report["subset_verified"] is True
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


@pytest.mark.parametrize("case", ["file_missing", "file_duplicate", "file_extra", "symbol_missing", "symbol_duplicate", "symbol_extra", "imports", "blob", "commit", "path", "statements", "malformed", "not_object"])
def test_audit_rejects_manifest_omissions_and_tampering(audit, case):
    checker, source, _ = audit
    data = json.loads(checker.CONTRACT.read_text(encoding="utf-8"))
    if case == "file_missing":
        data["files"].pop()
    elif case == "file_duplicate":
        data["files"].append(copy.deepcopy(data["files"][0]))
    elif case == "file_extra":
        data["files"].append({"path": "elsewhere.py"})
    elif case.startswith("symbol_"):
        symbols = data["files"][0]["symbols"]
        if case == "symbol_missing":
            symbols.pop()
        else:
            symbols.append(symbols[0] if case == "symbol_duplicate" else "find")
    elif case == "imports":
        data["files"][0]["allowed_imports"] += "\nimport os"
    elif case == "blob":
        data["files"][0]["git_blob_sha1"] = "0" * 40
    elif case == "commit":
        data["commit"] = "0" * 40
    elif case == "path":
        data["files"][0]["vendor_path"] = "../outside.py"
    elif case == "statements":
        data["files"][1]["statement_indices"].pop()
    elif case == "not_object":
        data = []
    checker.CONTRACT.write_text("{" if case == "malformed" else json.dumps(data), encoding="utf-8")
    report = checker.check_source_parity(source)
    assert report["subset_verified"] is False
    assert report["blockers"]


@pytest.mark.parametrize("file,mutation", [
    ("level_reversal", "extra"), ("level_reversal", "duplicate"), ("level_reversal", "import"),
    ("level_reversal", "missing"), ("level_reversal", "body"), ("level_reversal", "decorator"),
    ("pvsra", "extra"), ("pvsra", "duplicate"), ("pvsra", "import"),
    ("pvsra", "missing"), ("pvsra", "body"), ("pvsra", "decorator"),
])
def test_audit_rejects_extra_or_changed_executable_vendor_code(audit, file, mutation):
    checker, source, root = audit
    path = root / f"trading_system/tree_replay/_vendor/{file}.py"
    text = path.read_text(encoding="utf-8")
    symbol = "detect_frame" if file == "level_reversal" else "pvsra"
    if mutation == "extra":
        text += "\nprint('unexpected')\n"
    elif mutation == "duplicate":
        node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == symbol)
        text += "\n" + ast.unparse(node)
    elif mutation == "import":
        text += "\nimport os\n"
    elif mutation == "missing":
        text = text.replace("def " + symbol + "(", "def omitted(")
    elif mutation == "decorator":
        text = text.replace("def " + symbol + "(", "@print\ndef " + symbol + "(")
    else:
        text = text.replace('len(df) < 12', 'len(df) < 11') if file == "level_reversal" else text.replace('sv_x >= max_sv10', 'sv_x > max_sv10')
    path.write_text(text, encoding="utf-8")
    assert checker.check_source_parity(source)["subset_verified"] is False


@pytest.mark.parametrize("path", ["chartdesk/level_reversal.py", "chartdesk/tr.py", "chartdesk/auction.py"])
@pytest.mark.parametrize("missing", [False, True])
def test_audit_rejects_missing_or_modified_pinned_source(audit, path, missing):
    checker, source, _ = audit
    target = source / path
    if missing:
        target.unlink()
    else:
        target.write_text(target.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    assert checker.check_source_parity(source)["subset_verified"] is False


@pytest.mark.parametrize("path,before,after", [
    ("chartdesk/tr.py", "auction: bool | pd.Series=False", "auction: bool | pd.Series=True"),
    ("chartdesk/tr.py", "slots = A.resolve_slots(df.index, auction, session_tz)", "slots = None"),
    ("chartdesk/tr.py", "slots = None", "slots = True"),
    ("chartdesk/auction.py", "return None", "return True"),
])
def test_audit_checks_specialization_preconditions_even_with_reapproved_blob(audit, path, before, after):
    checker, source, _ = audit
    target = source / path
    original = target.read_text(encoding="utf-8")
    assert before in original
    modified = original.replace(before, after)
    target.write_text(modified, encoding="utf-8")
    checker.SOURCE_BLOBS[path] = blob(modified)
    data = json.loads(checker.CONTRACT.read_text(encoding="utf-8"))
    next(row for row in data["files"] if row["path"] == path)["git_blob_sha1"] = blob(modified)
    checker.CONTRACT.write_text(json.dumps(data), encoding="utf-8")
    assert checker.check_source_parity(source)["subset_verified"] is False


def test_cli_missing_source_fails_closed(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / "tools/check_reversal_source_parity.py"),
                             "--source-root", str(tmp_path)], capture_output=True, text=True, check=False)
    assert result.returncode != 0
    report = json.loads(result.stdout)
    assert report["subset_verified"] is False
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False
