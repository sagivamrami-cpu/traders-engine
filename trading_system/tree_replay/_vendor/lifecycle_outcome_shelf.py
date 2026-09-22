"""Pinned tracker outcome/shelf helpers over raw offline artifact ports only."""
from __future__ import annotations

import json
from pathlib import PurePosixPath

from .tracker_admission import TrackerAdmission


class LifecycleOutcomeShelf:
    OUTCOMES = PurePosixPath("chart-desk/out/trade_outcomes.jsonl")

    EXPIRE_H = 24.0
    EXPIRE_BY_STYLE = {"scalp": 6.0, "intraday": 6.0,
                       "swing": 24.0, "tree": 8.0}

    def __init__(self, source):
        self.source = source
        self.admission = TrackerAdmission(source)

    def _outcome(self, row: dict, *, event_ts: float | None = None) -> None:
        self.source.outcomes_mkdir(self.OUTCOMES.parent.as_posix(),
                                   parents=True, exist_ok=True)
        now = self.source.now_epoch()
        at = float(event_ts) if event_ts else now
        with self.source.open_outcomes("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": now, **row, "event_ts": at},
                                ensure_ascii=False) + "\n")

    def _atomic_json(self, path, obj) -> None:
        self.source.atomic_mkdir(path.parent.as_posix(), parents=True, exist_ok=True)
        fd, tmp = self.source.atomic_mkstemp(path.parent.as_posix(), suffix=".tmp")
        try:
            with self.source.atomic_fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(obj, fh, ensure_ascii=False)
                fh.flush()
                self.source.atomic_fsync(fh)
            self.source.atomic_replace(tmp, path.as_posix())
        except Exception:
            try:
                self.source.atomic_unlink(tmp)
            except Exception:
                pass
            raise

    def has_open(self, symbol: str, direction: str | None = None,
                 *, state: dict | None = None) -> bool:
        return self.admission.has_open(symbol, direction, state=state)

    def _expire_h(self, t: dict) -> float:
        style = (t.get("style") or "intraday").lower()
        if "tree" in (t.get("variant") or ""):
            return self.EXPIRE_BY_STYLE["tree"]
        return self.EXPIRE_BY_STYLE.get(style, self.EXPIRE_H)

    SHELF = PurePosixPath("chart-desk/out/shelved_trades.json")

    SHELF_MAX_H = 48.0

    REVIVAL_COOLDOWN_S = 900.0

    def _shelve(self, t: dict) -> None:
        try:
            d = (json.loads(self.source.shelf_text(encoding="utf-8"))
                 if self.source.shelf_exists() else {})
        except Exception:
            d = {}
        k = f"{t['symbol']}|{t['direction']}|{round(float(t['entry']), 2)}"
        first_ts = float(t.get("revived_from_ts") or t["ts"])
        d[k] = {"symbol": t["symbol"], "direction": t["direction"],
                "entry": float(t["entry"]), "stop": float(t["stop"]),
                "targets": t.get("targets") or [], "style": t.get("style"),
                "variant": t.get("variant"), "to_group": bool(t.get("to_group")),
                "original_ts": first_ts, "shelved_ts": self.source.now_epoch()}
        self._atomic_json(self.SHELF, d)
