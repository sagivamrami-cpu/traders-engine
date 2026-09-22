from __future__ import annotations
import hashlib
import json
from contextlib import contextmanager
import sys
from pathlib import Path, PurePosixPath
from .lifecycle_identity import LifecycleIdentity, identity
STORE = PurePosixPath('chart-desk/out/outbox.jsonl')
LATE_AFTER_S = 10 * 60

def _eid(text: str, ts: float) -> str:
    minute = int(ts // 60)
    return hashlib.sha256(f'{minute}|{text}'.encode()).hexdigest()[:16]

def _append_lock_path() -> Path:
    """Serialises every append with the compactor's swap (Codex, 09-06):
    an enqueue landing between the compactor's tail read and its rename
    went to the old inode -- the backup -- and vanished from the live
    journal. Separate from the flush lock, which is held for a whole pass
    and taken non-blocking; this one guards a single write and waits."""
    return STORE.with_suffix('.append.lock')

def _merge(rows: list) -> dict:
    """id -> merged final row. Last state wins per id."""
    last: dict = {}
    for r in rows:
        cur = last.get(r['id'])
        if cur is None:
            last[r['id']] = dict(r)
        else:
            cur.update({k: v for k, v in r.items() if k != 'ts'})
            cur['last_ts'] = r['ts']
    return last

class OutboxJournal:

    def __init__(self, source):
        self.source = source
        self.threads = LifecycleIdentity(source)
        self._BORN = {}

    def _rows(self) -> list:
        if not self.source.journal_exists():
            return []
        out = []
        for line in self.source.journal_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out

    @contextmanager
    def _append_lock(self):
        """The append lock, blocking. Held by every write and by the compactor
    across its read and its swap. NOT re-entrant: a holder writes through
    _write(), never _append()."""
        self.source.mkdir(STORE.parent.as_posix(), parents=True, exist_ok=True)
        with self.source.open_append_lock(_append_lock_path().as_posix(), 'a+') as lk:
            self.source.try_acquire(lk, timeout=None)
            try:
                yield
            finally:
                self.source.release(lk)

    def _write(self, row: dict) -> None:
        """The one physical write. The caller holds the append lock."""
        self.source.assert_offline()
        self.source.mkdir(STORE.parent.as_posix(), parents=True, exist_ok=True)
        with self.source.open_journal('a', encoding='utf-8') as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + '\n')

    def _append(self, row: dict) -> None:
        with self._append_lock():
            self._write(row)

    def _last_states(self) -> dict:
        return _merge(self._rows())

    def remember_born(self, text: str, ts: float) -> None:
        self._BORN[text] = float(ts)

    def enqueue(self, text: str, to_group: bool, kind: str='lifecycle', *, trade_context=None) -> str:
        """Persist the event. Returns its id.

    A DELIVERED OR RESOLVED ID CANNOT BE RESURRECTED. Codex's final-verdict
    catch: this appended PENDING unconditionally, and because the current
    view is last-state-wins per id, re-enqueueing a text the tracker
    regenerates within the same minute flipped a DELIVERED event back to
    PENDING -- the queue built to stop messages vanishing would instead
    send one twice.
    """
        if not isinstance(text, str) or not text.strip():
            print(f'[outbox] refused a non-message payload: {text!r:.80}', file=sys.stderr)
            return ''
        ts = self.source.now_epoch()
        needs_reply = bool(to_group and identity(text))
        if needs_reply and trade_context is None:
            trade_context = self.threads.context(text)
        born = self._BORN.pop(text, None)
        eid = _eid(text, ts)
        with self._append_lock():
            states = self._last_states()
            prior = states.get(eid)
            if prior is not None and prior.get('state') in ('DELIVERED', 'RESOLVED'):
                return eid
            if prior is not None and prior.get('state') == 'PENDING':
                if to_group and (not prior.get('to_group')):
                    self._write({'id': eid, 'ts': ts, 'state': 'PENDING', 'to_group': True})
                return eid
            for old_id, old in states.items():
                if old.get('state') == 'PENDING' and old.get('text') == text and (ts - float(old.get('ts', ts)) <= LATE_AFTER_S):
                    if to_group and (not old.get('to_group')):
                        self._write({'id': old_id, 'ts': ts, 'state': 'PENDING', 'to_group': True})
                    return old_id
            row = {'id': eid, 'ts': ts, 'text': text, 'to_group': bool(to_group), 'kind': kind, 'state': 'PENDING', 'attempts': 0, 'sent_personal': False, 'sent_group': False}
            if needs_reply:
                row.update(reply_required=True, trade_context=trade_context)
            if born and born < ts:
                row['born'] = born
            self._write(row)
        return eid

    def _mark(self, eid: str, state: str, **extra) -> None:
        row = {'id': eid, 'ts': self.source.now_epoch(), 'state': state}
        row.update(extra)
        self._append(row)

    def pending(self) -> list:
        """Current view: last state wins per id, PENDING rows only, oldest first.

    A row whose text is present but not a message (None, [], "") is still
    PENDING and is returned, so the flush can RESOLVE it; filtering on
    truthiness left such rows pending on disk forever (Codex, 2026-09-04).
    Only an orphan state row with no text at all is skipped.
    """
        rows = [r for r in self._last_states().values() if r.get('state') == 'PENDING' and 'text' in r]
        rows.sort(key=lambda r: r['ts'])
        return rows

    def resolve(self, eid: str, why: str) -> None:
        """Administrative removal -- the ONLY exit that is not a delivery."""
        self._mark(eid, 'RESOLVED', why=why)

    def resolve_text(self, text: str, why: str) -> int:
        """Resolve every pending event with this exact text. Returns count."""
        count = 0
        for ev in self.pending():
            if ev.get('text') == text:
                self.resolve(ev['id'], why)
                count += 1
        return count
