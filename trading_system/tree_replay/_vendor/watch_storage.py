"""Pinned market_watch.main persistence statements over explicit offline ports."""
import json


class WatchStorage:
    def __init__(self, source):
        self.source = source

    def load(self):
        st = json.loads(self.source.read_text()) if self.source.exists() else {}
        return st

    def save_before_producers(self, st):
        self.source.ensure_directory(exist_ok=True)
        self.source.write_text(json.dumps(st))

    def save_final(self, st):
        self.source.write_text(json.dumps(st))
