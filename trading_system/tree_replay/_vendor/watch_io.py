"""Original watch logger on explicit local ports; no live imports."""
import json


class WatchLogger:
    def __init__(self, source):
        self.source = source

    def log(self, row: dict) -> None:
        row.setdefault("sessions", sorted(self.source.current_session()))
        self.source.ensure_out()
        with self.source.event_log_writer() as f:
            f.write(json.dumps({"ts": self.source.now_epoch(), **row}, ensure_ascii=False) + "\n")
