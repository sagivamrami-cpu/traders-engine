"""Original lifecycle gate, parking and retry over explicit offline effects."""
from __future__ import annotations

import json
import sys
from pathlib import PurePosixPath

from .claim_verifier import ClaimVerifier
from .lifecycle_identity import _match_trade_for_text
from .outbox_journal import OutboxJournal


PARK = PurePosixPath('chart-desk/out/parked_claims.json')
PARK_MAX_AGE_S = 3600.0


class LifecycleGate:
    def __init__(self, source):
        self.source = source
        self.verifier = ClaimVerifier(source)
        self.outbox = OutboxJournal(source)
        self.threads = self.outbox.threads

    def _persist_gated_lifecycle(self, msgs: list, state: dict) -> list:
        """Gate and persist lifecycle messages before state is saved."""
        if not msgs:
            return []
        send, blocked = self.gate(msgs, state=state)
        sent_texts = {text for text, _to_group in send}
        for text, to_group in send:
            self.outbox.enqueue(text, to_group,
                                trade_context=self.threads.context(text, state))
        for text, why in blocked:
            if text in sent_texts or str(why).startswith('STALE:'):
                continue
            eid = self.outbox.enqueue(text, False, kind='blocked_lifecycle')
            self.outbox.resolve(eid, f'blocked by gate: {why}')
        return msgs

    def gate(self, msgs: list, state: dict | None=None) -> tuple[list, list]:
        """Verify every outcome claim against the tape. Returns (send, blocked).

        THE GATE, added 2026-08-27 after the fourth reporting bug reached his
        phone. Every one of them announced something that had not happened, and
        every one passed its own tests -- because a test checks the code you wrote
        against the behaviour you believed.

        So the claim is re-derived from bars by chartdesk/verify.py, which shares
        no state and no helper with the resolvers here. Two independent readings
        of the same tape must agree or the message does not go out. A verifier
        built on the resolver's helpers would inherit the resolver's bugs and
        agree with them; that is why it does its own fetch and its own fill
        location, and why it is deliberately dumber than what it checks.

        Messages that make no factual claim about a price being reached -- a
        proximity alert, a break-even note -- pass untouched. They describe a
        state, and there is nothing on the tape to disagree with.
        """
        d = state if state is not None else self.source.load()
        send, blocked = [], []
        for text, to_group in msgs:
            tr, ambiguous_matches = _match_trade_for_text(text, d)
            if ambiguous_matches:
                if to_group and not any(self.threads._group_has(t) for t in ambiguous_matches):
                    send.append((text, False))
                    blocked.append((text, 'ambiguous lifecycle with no group receipt'))
                else:
                    send.append((text, to_group))
                self._unpark_text(text)
                continue
            if tr is None:
                send.append((text, to_group))
                self._unpark_text(text)
                continue
            if (text.strip().startswith(('🔒', '🏁')) and 'TP' in text
                    and tr.get('targets')):
                v = self.verifier.target(tr, float(tr['targets'][0][1]))
                if not v.ok:
                    if getattr(v, 'stale', False):
                        self._park(tr, text)
                        blocked.append((text, f'STALE: {v.reason}'))
                    else:
                        blocked.append((text, v.reason))
                    continue
            else:
                v = self.verifier.check_message(text, tr)
                if not v.ok:
                    if getattr(v, 'stale', False):
                        self._park(tr, text)
                        blocked.append((text, f'STALE: {v.reason}'))
                    else:
                        blocked.append((text, v.reason))
                    continue
            if to_group and not self.threads._group_has(tr):
                send.append((text, False))
                blocked.append((text, 'no group receipt for the entry — '
                                      'sent to Sagiv only'))
                self._unpark_text(text)
                continue
            send.append((text, to_group))
            self._unpark_text(text)
        return send, blocked

    def _park_key(self, tr: dict, text: str) -> str:
        first = (text.strip().splitlines() or [''])[0]
        return f"{tr.get('symbol')}|{tr.get('entry')}|{first}"

    def _park(self, tr: dict, text: str) -> None:
        try:
            d = json.loads(self.source.park_text(encoding='utf-8')) if self.source.park_exists() else {}
        except Exception:
            d = {}
        k = self._park_key(tr, text)
        if k not in d:
            d[k] = {'text': text, 'ts': self.source.now_epoch(),
                    'symbol': tr.get('symbol'), 'entry': tr.get('entry'),
                    'to_group': bool(tr.get('to_group'))}
            self._atomic_json(PARK, d)

    def _unpark_text(self, text: str) -> None:
        if not self.source.park_exists():
            return
        try:
            d = json.loads(self.source.park_text(encoding='utf-8'))
        except Exception:
            return
        keep = {k: v for k, v in d.items() if v.get('text') != text}
        if len(keep) != len(d):
            self._atomic_json(PARK, keep)

    def replay_parked(self, state: dict | None=None) -> list:
        """Re-offer held messages now that the tape may have caught up.

        Returns [(text, to_group)] for anything that now verifies. Anything still
        unverifiable stays parked; anything the tape now CONTRADICTS is dropped
        with a note, because a fresher tape that disagrees is a real answer.
        """
        if not self.source.park_exists():
            return []
        try:
            d = json.loads(self.source.park_text(encoding='utf-8'))
        except Exception:
            return []
        if not d:
            return []
        trades = state if state is not None else self.source.load()
        out, keep, now = [], {}, self.source.now_epoch()
        for k, rec in d.items():
            head = rec['text'].splitlines()[0][:60]
            if now - float(rec.get('ts', 0)) > PARK_MAX_AGE_S:
                print(f'[parked] expired unverified: {head}', file=sys.stderr)
                self._park_lost(rec, 'הטייפ לא הכריע תוך שעה')
                continue
            tr = next((t for t in trades.values()
                       if t.get('symbol') == rec.get('symbol')
                       and abs(float(t.get('entry', 0))
                               - float(rec.get('entry', 0))) < 1e-6), None)
            if tr is None:
                continue
            v = self.verifier.check_message(rec['text'],
                                            dict(tr, claim_ts=float(rec.get('ts') or 0)))
            if v.ok:
                out.append((rec['text'], rec.get('to_group', False)))
                self.outbox.remember_born(rec['text'], float(rec.get('ts') or now))
                print(f'[parked] released after the tape caught up: {head}',
                      file=sys.stderr)
            elif getattr(v, 'stale', False):
                keep[k] = rec
            else:
                print(f'[parked] dropped, tape now contradicts it: {v.reason}',
                      file=sys.stderr)
                self._park_lost(rec, f'הטייפ סותר אותה: {v.reason}')
        self._atomic_json(PARK, keep)
        return out

    def _park_lost(self, rec: dict, why: str) -> None:
        """A parked claim that will never go out is told to Sagiv, not to stderr.

        Codex (2026-09-03): a stop that fell on a 61-minute tape outage expired
        here in silence -- the trade was terminal, so nothing regenerated the
        label, and the only trace was a log line. The state has moved on; the
        channel has not. That is exactly the divergence issue #5 is about, and
        the operator has to hear it while `trade_admin resend` can still fix it.
        """
        when = self.source.format_il_clock(rec.get('ts') or self.source.now_epoch())
        head = rec['text'].strip().splitlines()[0]
        note = (f'⚠️ תווית אבדה בחניה ({when}) — {why}\n{head}\n'
                'המעקב כבר סימן את זה; הערוץ לא שמע. '
                'trade_admin resend אם זה אמת.')
        try:
            self.outbox.enqueue(note, False, kind='park_lost')
        except Exception as e:
            print(f'[parked] could not queue the loss note: {e}', file=sys.stderr)

    def _atomic_json(self, path, obj) -> None:
        self.source.atomic_mkdir(path.parent.as_posix(), parents=True, exist_ok=True)
        fd, tmp = self.source.atomic_mkstemp(path.parent.as_posix(), suffix='.tmp')
        try:
            with self.source.atomic_fdopen(fd, 'w', encoding='utf-8') as fh:
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
