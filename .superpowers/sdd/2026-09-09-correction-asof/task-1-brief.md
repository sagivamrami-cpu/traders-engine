## Task 1: Pure source closure, audit and as-of evidence adapter

**Files:**
- Create trading_system/tree_replay/_vendor/correction.py
- Create trading_system/tree_replay/corrections.py
- Create tools/check_correction_source_parity.py
- Create configs/trees/correction-source-contracts.json
- Create tests/tree_replay/test_correction_source.py
- Create tests/tree_replay/test_corrections.py
- Create docs/architecture/CORRECTION-ASOF-USAGE.md

**Pinned input:** chart-desk commit 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9; chartdesk/basis.py Git blob f3396f3a9fefd71f0f71422001a5521af0a05cd2.
Retained checkout: C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149/chart-desk.

**Source interface:** vendor module imports only future annotations, dataclass and pandas; contains exact complete Correction, exact EXCHANGE_NATIVE, and broker_shape_ok_at(corr, days: float, *, decision_time) -> bool.
The predicate is the original broker_shape_ok with exactly three explicit adaptations: rename to broker_shape_ok_at; add required keyword-only decision_time argument; replace the single pd.Timestamp.now("UTC") call with pd.Timestamp(decision_time). All other executable statements, docstrings, branch order and constants remain identical.

**Audit interface:** check_source_parity(source_root: Path) -> dict; CLI --source-root overrides TR_CHARTDESK_SOURCE_ROOT, then retained default. Fixed expected commit/blob/manifest/imports/ordered symbols live independently in the auditor. Normalize CRLF as existing audits do. Compare the entire ordered vendor module AST against the expected source projection/specialization, reject extra/rebound/imported code. Check exactly one expected clock call before specializing. Validate baseline chart-desk pin occurs exactly once. Strict JSON comparison distinguishes false from 0. Missing source/contract/vendor, syntax errors, changed source/manifest/constant/branch/clock/import/module shape fail closed (CLI exit 2), never skipped. Success exit 0 means this subset only.

**Public interface:**

```python
@dataclass(frozen=True, kw_only=True)
class CorrectionEvidence:
    evidence_id: str
    frame_id: str
    instrument: str
    version: str
    observed_at: datetime
    available_at: datetime
    provenance: str
    offset: float
    source: str
    confidence: str
    note: str
    tv_from: datetime | None = None

def assess_correction_asof(
    correction: CorrectionEvidence | None, *, instrument: str,
    frame_id: str, decision_time: datetime, lookback_days: float,
    max_age_seconds: int,
) -> dict:
    ...
```

Constructor: reuse existing _utc, _number, _validate_identity and _text validation conventions. Every text except note is nonempty and trimmed; note must be a string (empty allowed). Offset is a finite native int/float (negative allowed, bool invalid). Timestamps are UTC-aware, normalized, microsecond-exact. available_at >= observed_at. If supplied, tv_from <= observed_at (it attests where genuine bars already begin). Do not require tv_from for tv_spliced: source with absent seam is valid evidence with shape false. Source/confidence are not narrowed to the obsolete comment's enums; preserve strings like tv_daily, mt5_broker, tv_spliced, n/a and vendor additions. Frozen evidence must not mutate.

Call validation: exact instrument/frame_id match or ValueError (no silent alias/association); correction must be None or CorrectionEvidence. decision_time validation as above; lookback_days finite native nonnegative; max_age_seconds native nonnegative int (not bool). All structural validation precedes temporal assessment.

Statuses/blockers in precedence order:
1. None -> BLOCKED / CORRECTION_MISSING.
2. observed_at > T -> BLOCKED / CORRECTION_FUTURE_OBSERVATION.
3. available_at > T -> BLOCKED / CORRECTION_UNAVAILABLE.
4. (T-observed_at).total_seconds() > max_age_seconds -> BLOCKED / CORRECTION_STALE.
5. Otherwise ASSESSED / blocker null, including shape false and unverified true.

Output contains schema_version correction-asof-v1, calculation_version chartdesk-correction-asof-v1, instrument, frame_id, decision_time (ISO UTC Z), lookback_days, max_age_seconds, status, blocker, evidence, unverified, broker_shape_ok, evidence_hash and both readiness flags false. On BLOCKED, evidence/unverified/broker_shape_ok are all null; do not leak an unavailable correction's offset/source/ID into a usable payload or hash. On ASSESSED, evidence is the canonical dataclass dictionary (UTC Z timestamps) and predicates are original Correction.unverified and broker_shape_ok_at with explicit T. Hash is SHA256 of the canonical result excluding evidence_hash (sort_keys, compact JSON, allow_nan=False). It includes policy, version and selected evidence; changes in unavailable payload at the same blocker must not affect the hash. No hidden wall clock, input mutation, offset application, feed inference, source-level trade admission or true readiness.

- [ ] Write failing behavioral tests before production edits. Use real data objects. Representative expected behavior:

```python
# At a replay instant exactly 20 elapsed days after the TV seam: true.
# One microsecond before that instant: false, regardless of today's date.
assert assess_correction_asof(e, instrument=e.instrument, frame_id=e.frame_id,
    decision_time=e.tv_from + timedelta(days=20), lookback_days=20,
    max_age_seconds=30*86400)["broker_shape_ok"] is True
# Different evidence payloads unavailable at T have the same blocked hash.
# Native BTC with source='none', confidence='n/a': shape true, unverified false.
# Native BTC with source='none', confidence='unknown': both flags true.
# Unknown GC symbol is not OANDA; it cannot inherit native-BTC exemption.
```

Test matrix: source None, pure broker sources, native identity, lower/upper/wrong identities, proxy, absent splice seam, 7/20-day exact boundaries, offset sign/zero irrelevance to shape, unverified narrow predicate and class show/render; numeric/string/UTC/submicrosecond validation, identity/frame mismatch, missing/future/delayed/stale and exact freshness, current/future seam, frozen/nonmutation, hash stability/policy/evidence changes, blocked payload noninterference. Include audit mutation tests on temporary synthetic copies (fixed production pins are not monkeypatched): altered manifest/baseline/source/vendor and executable additions, wall-clock restoration, missing prerequisites. Use env configurable source fixture, fail if absent. No real data calls.
- [ ] Run python -m pytest tests/tree_replay/test_correction_source.py tests/tree_replay/test_corrections.py -q --tb=short; record expected RED before implementing.
- [ ] Implement exact closure/audit, immutable adapter and usage documentation using the contracts above; no broader source consumers in this task.
- [ ] Run the same focused tests and python tools/check_correction_source_parity.py; record GREEN and limitations.
- [ ] Self-review, report using agent-exchange/templates/result.md, then independent task review; no commits.

