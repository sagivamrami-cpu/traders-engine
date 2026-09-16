### Task 1: Immutable replay evidence, ledger and activation contracts

**Files:**
- Create: `trading_system/tree_replay/causal_replay_contracts.py`
- Create: `tests/tree_replay/test_causal_replay_contracts.py`

**Interfaces:**
- Produces frozen `TrackerActivationEvidence`, `ReplayEvent`, `ReplayPassAnchor`, `ReplayEvidenceBundle`, `ReplayPassRecord`, and `ReplayRunLedger`.
- `canonical_digest(value: object) -> str` accepts only recursively finite JSON-compatible values and returns a SHA-256 digest of canonical UTF-8 JSON.
- `ReplayEvidenceBundle.events_before_or_at(at: datetime) -> tuple[ReplayEvent, ...]` returns only events whose `available_at <= at`; validation happens before selection.
- `ReplayRunLedger.append(record: ReplayPassRecord) -> ReplayRunLedger` returns a new ledger and rejects noncontiguous pass indexes, duplicate IDs, backward decision times and invalid predecessor digest.

- [ ] **Step 1: Write the failing contract tests**

```python
def test_anchor_requires_strict_schedule_and_exact_activation_coverage():
    activation = TrackerActivationEvidence(
        evidence_id="activation-1", source="watch-config", variant="level_reversal:5m",
        observed_at=T0, available_at=T0, covered_through=T1, enabled=True,
    )
    anchor = ReplayPassAnchor(
        pass_id="pass-1", decision_time=T1, source_variant="level_reversal:5m",
        required_event_ids=("bars-1",), activation=activation,
    )
    assert anchor.activation_state() == "EVIDENCED_ENABLED"

    with pytest.raises(ValueError, match="strictly increasing"):
        ReplayEvidenceBundle(run_id="run-1", instrument="OANDA:XAUUSD",
                             events=(event(T1, 1), event(T1, 0)), anchors=(anchor,))

def test_ledger_is_append_only_and_hash_chained():
    ledger = ReplayRunLedger.empty("run-1")
    first = ledger.append(record(index=0, predecessor_digest=ledger.digest))
    assert first.records[0].outcome == "OBSERVE_ONLY"
    with pytest.raises(ValueError, match="predecessor"):
        first.append(record(index=1, predecessor_digest="wrong"))
```

Include cases for naive/sub-microsecond times, duplicate event/pass IDs, a
future/uncovered/mismatched-variant activation record, nonfinite numbers,
unknown event kinds, event payload-availability mismatch, and a candidate
record that tries to contain `net_pnl`, `net_R`, `success` or `failure`.

- [ ] **Step 2: Run the contract tests and confirm they fail**

Run: `python -B -m pytest tests/tree_replay/test_causal_replay_contracts.py -q --tb=short -p no:cacheprovider`

Expected: import failure because `causal_replay_contracts` does not exist.

- [ ] **Step 3: Implement exact frozen contracts and canonical serialization**

```python
@dataclass(frozen=True, kw_only=True)
class TrackerActivationEvidence:
    evidence_id: str
    source: str
    variant: str
    observed_at: datetime
    available_at: datetime
    covered_through: datetime
    enabled: bool

    def state_at(self, *, decision_time: datetime, variant: str) -> str:
        at = _utc(decision_time, "decision_time")
        if variant != self.variant:
            return "MISMATCHED_VARIANT"
        if at < self.available_at:
            return "NOT_YET_AVAILABLE"
        if at > self.covered_through:
            return "COVERAGE_EXPIRED"
        return "EVIDENCED_ENABLED" if self.enabled else "EVIDENCED_DISABLED"

@dataclass(frozen=True, kw_only=True)
class ReplayPassRecord:
    pass_index: int
    pass_id: str
    decision_time: datetime
    outcome: str
    consumed_event_ids: tuple[str, ...]
    activation_state: str
    candidate: dict | None
    lifecycle_messages: tuple[tuple[str, bool], ...]
    diagnostics: tuple[dict, ...]
    predecessor_digest: str
```

Use the existing `bars._utc`, `_number`, `_validate_identity` and `state._identity`
helpers rather than accepting alternate time/instrument formats. Make all
exported collections tuples or detached canonical dictionaries. Permit exactly
`OBSERVE_ONLY`, `NO_CANDIDATE`, `BLOCKED`, `SKIPPED`, and `UNSUPPORTED` as
record outcomes. Validate candidate and diagnostics recursively before hashing.

- [ ] **Step 4: Run the focused contract suite**

Run: `python -B -m pytest tests/tree_replay/test_causal_replay_contracts.py -q --tb=short -p no:cacheprovider`

Expected: PASS; no contract creates a tracker row or economic field.

