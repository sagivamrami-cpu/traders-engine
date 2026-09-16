"""Causal supplied advisory-memory evidence, not a tracker or trade simulator.

Completeness and provenance are caller attestations. No disk, wall clock, feed,
or trading service is accessed. Fixed-TP1 economic state is deliberately excluded.
"""

from dataclasses import dataclass, fields
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from math import isfinite

from .bars import _utc


_SCHEMA = 'causal-admission-memory-v1'
_CHECKPOINT_SCHEMA = 'causal-admission-memory-checkpoint-v1'
_ORIGIN = 'supplied_source_advisory'
_STREAMS = ('tracker', 'episode', 'rejection')
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _identity(value, field):
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f'{field} must be a nonempty trimmed string')


def _json_text(value):
    try:
        text = json.dumps(value, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=False, allow_nan=False)
        text.encode('utf-8')
        return text
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError('memory must contain finite UTF-8 JSON values') from exc


def _hash(value):
    return hashlib.sha256(_json_text(value).encode('utf-8')).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _constant(value):
    raise ValueError(f'nonfinite JSON constant: {value}')


def _payload(text, stream, observed_at):
    if type(text) is not str:
        raise ValueError('payload_json must be text')
    try:
        result = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, RecursionError) as exc:
        raise ValueError('payload_json must be unambiguous finite JSON') from exc
    if type(result) is not dict:
        raise ValueError('payload_json must encode an object')
    normalized = _json_text(result)
    elapsed = observed_at - _EPOCH
    observed_epoch = (Decimal(elapsed.days * 86400 + elapsed.seconds)
                      + Decimal(elapsed.microseconds) / 1_000_000)
    time_fields = ('ts', 'resolved_ts') if stream == 'tracker' else ('ts',)
    # Compare the JSON decimal, not binary float expansion. An ordinary source
    # timestamp ending .123456 otherwise expands just past that microsecond.
    # Parsing original text also prevents finer future fractions being rounded
    # down by json.loads before this causal check.
    epoch_values = json.loads(text, parse_float=Decimal)
    for name in time_fields:
        if name not in result:
            continue
        value = result[name]
        if type(value) not in (int, float) or (type(value) is float and not isfinite(value)):
            raise ValueError(f'payload {name} must be a finite numeric epoch')
        if Decimal(epoch_values[name]) > observed_epoch:
            raise ValueError(f'payload {name} cannot exceed observed_at')
    return normalized


@dataclass(frozen=True, kw_only=True)
class MemoryEvent:
    """One fully observed source-row replacement or append-only rejection."""

    event_id: str
    sequence: int
    stream: str
    key: str
    observed_at: datetime
    available_at: datetime
    payload_json: str

    def __post_init__(self):
        _identity(self.event_id, 'event_id')
        _identity(self.key, 'key')
        if type(self.sequence) is not int or self.sequence < 0:
            raise ValueError('sequence must be a native nonnegative integer')
        if type(self.stream) is not str or self.stream not in _STREAMS:
            raise ValueError('stream must be tracker, episode or rejection')
        if self.stream == 'rejection' and self.key != self.event_id:
            raise ValueError('rejection key must equal event_id')
        for name in ('observed_at', 'available_at'):
            object.__setattr__(self, name, _utc(getattr(self, name), name))
        if self.available_at < self.observed_at:
            raise ValueError('available_at cannot precede observed_at')
        object.__setattr__(self, 'payload_json',
                           _payload(self.payload_json, self.stream, self.observed_at))


@dataclass(frozen=True, kw_only=True)
class MemoryJournal:
    """Append-ordered evidence and explicit bounded completeness attestation."""

    journal_id: str
    origin: str
    start_at: datetime
    covered_through: datetime
    complete: bool
    events: tuple[MemoryEvent, ...]

    def __post_init__(self):
        _identity(self.journal_id, 'journal_id')
        if type(self.origin) is not str or self.origin != _ORIGIN:
            raise ValueError('origin must be supplied_source_advisory')
        if type(self.complete) is not bool:
            raise ValueError('complete must be an explicit bool')
        for name in ('start_at', 'covered_through'):
            object.__setattr__(self, name, _utc(getattr(self, name), name))
        if self.covered_through < self.start_at:
            raise ValueError('covered_through cannot precede start_at')
        if type(self.events) is not tuple:
            raise ValueError('events must be an immutable tuple')
        seen = set()
        previous = None
        for event in self.events:
            if type(event) is not MemoryEvent:
                raise ValueError('events must contain exact MemoryEvent objects')
            if event.event_id in seen:
                raise ValueError('duplicate event_id')
            seen.add(event.event_id)
            if previous is not None and (event.sequence <= previous.sequence
                    or event.available_at < previous.available_at):
                raise ValueError('events must preserve increasing sequence/publication order')
            if event.observed_at < self.start_at or event.available_at > self.covered_through:
                raise ValueError('events lie outside declared journal coverage')
            previous = event


def _journal(value):
    if type(value) is not MemoryJournal:
        raise ValueError('journal must be an exact MemoryJournal')


def _event_record(event):
    return {field.name: (getattr(event, field.name).isoformat()
                        if field.name in ('observed_at', 'available_at')
                        else getattr(event, field.name)) for field in fields(MemoryEvent)}


def memory_asof(journal: MemoryJournal, decision_time: datetime) -> dict:
    """Project only available evidence; revisions never backdate a state row."""
    _journal(journal)
    decision_time = _utc(decision_time, 'decision_time')
    blocker = None
    if not journal.complete:
        blocker = 'INCOMPLETE_HISTORY'
    elif decision_time < journal.start_at:
        blocker = 'BEFORE_COVERAGE'
    elif decision_time > journal.covered_through:
        blocker = 'AFTER_COVERAGE'
    result = dict(schema=_SCHEMA, status='UNAVAILABLE' if blocker else 'AVAILABLE',
        blocker=blocker, decision_time=decision_time.isoformat(),
        journal_id=journal.journal_id, origin=journal.origin,
        start_at=journal.start_at.isoformat(),
        tracker_state=None if blocker else {}, episode_state=None if blocker else {},
        rejection_events=None if blocker else [], selected_event_ids=[], event_trace=[],
        tradeable=False, replay_ready=False, training_ready=False)
    if not blocker:
        for event in journal.events:
            if event.available_at > decision_time:
                break
            value = json.loads(event.payload_json)
            if event.stream == 'rejection':
                result['rejection_events'].append(value)
            else:
                result[f'{event.stream}_state'][event.key] = value
            result['selected_event_ids'].append(event.event_id)
            trace = _event_record(event)
            trace['payload_hash'] = _hash(value)
            del trace['payload_json']
            result['event_trace'].append(trace)
    result['evaluation_hash'] = _hash(result)
    return result


def checkpoint_memory(journal: MemoryJournal) -> dict:
    """Serialize the entire supplied journal, not an engine checkpoint."""
    _journal(journal)
    data = dict(journal_id=journal.journal_id, origin=journal.origin,
                start_at=journal.start_at.isoformat(),
                covered_through=journal.covered_through.isoformat(),
                complete=journal.complete,
                events=[_event_record(event) for event in journal.events])
    result = dict(schema=_CHECKPOINT_SCHEMA, journal=data)
    result['checksum'] = _hash(result)
    return result


def _keys(value, expected, name):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError(f'{name} has an invalid structure')


def _parse_time(value, name):
    if type(value) is not str:
        raise ValueError(f'{name} must be an ISO timestamp')
    try:
        result = _utc(datetime.fromisoformat(value), name)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f'{name} must be an aware ISO timestamp') from exc
    # Checkpoints use the exact canonical serializer. In particular, never
    # truncate nanosecond strings accepted by datetime.fromisoformat.
    if result.isoformat() != value:
        raise ValueError(f'{name} must use canonical microsecond-exact UTC encoding')
    return result


def restore_memory(checkpoint: dict) -> MemoryJournal:
    """Validate version/checksum/types, then reconstruct through public contracts."""
    _keys(checkpoint, ('schema', 'journal', 'checksum'), 'checkpoint')
    if checkpoint['schema'] != _CHECKPOINT_SCHEMA:
        raise ValueError('unsupported memory checkpoint schema')
    content = {key: checkpoint[key] for key in ('schema', 'journal')}
    if type(checkpoint['checksum']) is not str or checkpoint['checksum'] != _hash(content):
        raise ValueError('invalid memory checkpoint checksum')
    data = checkpoint['journal']
    _keys(data, (f.name for f in fields(MemoryJournal)), 'journal')
    if type(data['events']) is not list:
        raise ValueError('checkpoint events must be a list')
    events = []
    for row in data['events']:
        _keys(row, (f.name for f in fields(MemoryEvent)), 'event')
        values = dict(row)
        for name in ('observed_at', 'available_at'):
            values[name] = _parse_time(values[name], name)
        events.append(MemoryEvent(**values))
    values = dict(data, events=tuple(events))
    for name in ('start_at', 'covered_through'):
        values[name] = _parse_time(values[name], name)
    restored = MemoryJournal(**values)
    if checkpoint_memory(restored) != checkpoint:
        raise ValueError('checkpoint must use canonical payload encoding')
    return restored
