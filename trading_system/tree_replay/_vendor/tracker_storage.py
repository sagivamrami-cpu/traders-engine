"""Private original tracker load/save with explicit offline artifact ports."""
import json


class TrackerStorage:
    def __init__(self, source):
        self.source = source

    def load(self) -> dict:
        if not self.source.exists():
            return {}
        return json.loads(self.source.read_text())

    def save(self, d: dict, *, allow_shrink: bool = False) -> None:
        if self.source.is_live_test_target():
            raise RuntimeError(
                "refusing to write the live open_trades.json from a test process: "
                "patch tracker.STATE (and OUTCOMES) to a temp path in setUp")
        if not allow_shrink and self.source.exists():
            try:
                cur = json.loads(self.source.read_text())
            except Exception:
                cur = None
            if cur is not None:
                self.source.audit_creation(cur, d)
            lost = set() if cur is None else set(cur) - set(d)
            if cur is None or (len(cur) >= 4 and len(lost) > len(cur) // 2):
                quarantine = self.source.quarantine_path(f".rejected-{int(self.source.now_epoch())}")
                quarantine.write_text(json.dumps(d, ensure_ascii=False, indent=1))
                detail = "state unreadable" if cur is None else f"would drop {len(lost)}/{len(cur)} keys"
                raise RuntimeError(f"_save refused: {detail}; dict quarantined at {quarantine.name}")
        self.source.atomic_write(json.dumps(d, ensure_ascii=False, indent=1))
