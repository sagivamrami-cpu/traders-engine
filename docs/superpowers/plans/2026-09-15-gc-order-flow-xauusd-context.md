# GC Order Flow as XAUUSD Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, payload-private and causal GC futures Order Flow context sidecar for an `OANDA:XAUUSD` decision, without treating GC as an XAUUSD price, trade, or execution source.

**Architecture:** A caller supplies validated, minute-start GC flow observations plus a provenance/coverage contract. A pure aggregator returns either an available fixed-window context or a typed unavailable result at one XAUUSD decision timestamp. A separate evidence-sidecar binds the private context to the full-tree pass through a commitment only; it deliberately does not change `TreeReader` decisions because the pinned tree has no Order Flow input port. This preserves the original tree while making a replayable context available to the later feature/dataset layer.

**Tech Stack:** Python 3, dataclasses, `datetime`, `hashlib`/canonical JSON, PyYAML, pytest, existing `trading_system.tree_replay` contracts.

**Spec:** `docs/superpowers/specs/2026-09-15-gc-order-flow-xauusd-context-design.md`

## Global Constraints

- Target trade/price identity is exactly `OANDA:XAUUSD`; source identity is exactly `CME:GC` from `DATABENTO/GLBX.MDP3`.
- GC flow may contain only `minute`, `volume`, `delta`, and `trades`; no OHLC, price conversion, offset, alias, archived CVD, recomputed CVD, or cumulative state is allowed.
- A minute beginning at `m` is eligible only if its end `m + 60 seconds` and its declared source `available_at` are both no later than decision time `T`.
- Time is aware UTC. The half-open damaged interval `[2017-01-01T00:00:00Z, 2017-06-01T00:00:00Z)` is unavailable, never filled or aggregated.
- Missing, duplicate, malformed, non-finite, wrong-identity, late, out-of-coverage, or gapped inputs must produce a typed unavailable result; never zero, forward-fill, back-fill, reuse an old GC value, or fall back to XAUUSD.
- Window boundaries are caller-supplied; no implicit feature horizon or trading threshold is invented.
- Existing `TreeReader`, its decisions, alert behavior, economics, datasets, training, and all readiness flags remain unchanged.
- Public replay/checkpoint material holds only commitments and provenance, never raw GC minute values. Raw archive paths/payloads remain outside the repository and `agent-exchange`.

## Important integration finding

The pinned `TreeReader`/`FullTreeCausalProvider` surface has no dedicated
Order Flow port. Therefore this increment cannot honestly inject a new value
into the existing tree without changing its source behavior. It will implement
an additive **context sidecar** associated with a full-tree pass. A future,
separately approved tree-branch change may consume that sidecar; until then it
is a causal observation for analysis/dataset construction, not a new tree
veto or confirmation.

---

### Task 1: Pin the approved cross-market source policy

**Files:**
- Create: `configs/data/xauusd-gc-crossmarket-order-flow-context.yaml`
- Create: `schemas/xauusd_gc_crossmarket_order_flow_context.schema.json`
- Create: `trading_system/tree_replay/cross_market_flow_policy.py`
- Create: `tests/tree_replay/test_cross_market_flow_policy.py`

**Interfaces:**
- Produces `CrossMarketFlowPolicy.load(path: Path) -> CrossMarketFlowPolicy`.
- Produces immutable fields `target_instrument`, `source_instrument`, `source_dataset`, `archive_sha256`, `selected_member`, `allowed_columns`, `damaged_start`, and `damaged_end` for Tasks 2–4.

- [ ] **Step 1: Write failing policy tests**

```python
def test_policy_pins_only_the_approved_xauusd_gc_context_identity():
    policy = CrossMarketFlowPolicy.load(POLICY)
    assert policy.target_instrument == "OANDA:XAUUSD"
    assert policy.source_instrument == "CME:GC"
    assert policy.source_dataset == "DATABENTO/GLBX.MDP3"
    assert policy.allowed_columns == ("minute", "volume", "delta", "trades")
    assert policy.damaged_start == datetime(2017, 1, 1, tzinfo=UTC)
    assert policy.damaged_end == datetime(2017, 6, 1, tzinfo=UTC)

def test_policy_rejects_any_price_column_or_changed_identity(tmp_path):
    changed = valid_policy_text().replace("volume", "close", 1)
    path = tmp_path / "policy.yaml"
    path.write_text(changed, encoding="utf-8")
    with pytest.raises(ValueError, match="CROSS_MARKET_POLICY"):
        CrossMarketFlowPolicy.load(path)
```

- [ ] **Step 2: Run the policy tests and verify they fail**

Run: `python -B -m pytest tests/tree_replay/test_cross_market_flow_policy.py -q --tb=short -p no:cacheprovider`

Expected: FAIL because the policy loader does not exist.

- [ ] **Step 3: Create the schema and configuration**

Create a versioned YAML policy whose immutable literals are the approved
identities, archive SHA-256 `34f82b1b9306f3605b00d60bcb96cb4aa0fc74c5de1f2d2401d1c1d610f03155`,
member `gc/GCext_of_1m.parquet`, the four allowed columns in their exact
order, UTC minute-start semantics, the damaged interval, and decision
reference `agent-exchange/decisions/2026-09-15T102150Z-human-gc-order-flow-xauusd-context.md`.
The schema must set `additionalProperties: false` and prohibit a price/venue
mapping field.

- [ ] **Step 4: Implement the minimal fail-closed loader**

```python
@dataclass(frozen=True)
class CrossMarketFlowPolicy:
    target_instrument: str
    source_instrument: str
    source_dataset: str
    archive_sha256: str
    selected_member: str
    allowed_columns: tuple[str, ...]
    damaged_start: datetime
    damaged_end: datetime

    @classmethod
    def load(cls, path: Path) -> "CrossMarketFlowPolicy":
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        # Validate schema and exact approved literals before constructing cls.
```

Reject naïve/non-UTC timestamps, a reversed interval, unknown fields, and all
values differing from the approved source contract.

- [ ] **Step 5: Run policy tests and the existing canonical-manifest regression**

Run: `python -B -m pytest tests/tree_replay/test_cross_market_flow_policy.py tests/research/test_gc_canonical_order_flow_input_manifest.py -q --tb=short -p no:cacheprovider`

Expected: PASS; the old GC manifest remains historical input identity and is not silently rewritten.

- [ ] **Step 6: Commit**

```bash
git add configs/data/xauusd-gc-crossmarket-order-flow-context.yaml schemas/xauusd_gc_crossmarket_order_flow_context.schema.json trading_system/tree_replay/cross_market_flow_policy.py tests/tree_replay/test_cross_market_flow_policy.py
git commit -m "feat: pin GC flow context policy for XAUUSD"
```

### Task 2: Implement the causal, typed GC context aggregator

**Files:**
- Create: `trading_system/tree_replay/cross_market_flow.py`
- Create: `tests/tree_replay/test_cross_market_flow.py`

**Interfaces:**
- Consumes `CrossMarketFlowPolicy` from Task 1.
- Produces `GcFlowMinute`, `CrossMarketFlowInput`, `CrossMarketFlowContext`, and `build_cross_market_flow_context(source, *, decision_time, window_start)`.
- `CrossMarketFlowContext.status` is exactly `AVAILABLE` or `UNAVAILABLE`; `reason` is `None` only for available results.
- Later tasks use `CrossMarketFlowContext.commitment() -> dict[str, object]` and its private values only through the exact object.

- [ ] **Step 1: Write failing causal-boundary tests**

```python
def test_minute_is_not_eligible_until_its_end_at_or_before_decision_time():
    source = source_with(minute("2026-01-02T09:30:00Z", available_at="2026-01-02T09:31:00Z"))
    early = build_cross_market_flow_context(source, decision_time=at("2026-01-02T09:30:59Z"), window_start=at("2026-01-02T09:30:00Z"))
    on_end = build_cross_market_flow_context(source, decision_time=at("2026-01-02T09:31:00Z"), window_start=at("2026-01-02T09:30:00Z"))
    assert (early.status, early.reason) == ("UNAVAILABLE", "GC_MINUTE_NOT_CLOSED")
    assert on_end.status == "AVAILABLE"

def test_gap_damage_nonfinite_and_identity_error_do_not_create_values():
    for source, reason in [(gapped_source(), "GC_MINUTE_GAP"), (damaged_source(), "GC_DAMAGED_ERA"), (nan_source(), "GC_NONFINITE_VALUE"), (wrong_identity_source(), "GC_SOURCE_IDENTITY")]:
        result = build_cross_market_flow_context(source, decision_time=T, window_start=T - timedelta(minutes=5))
        assert (result.status, result.reason, result.volume, result.delta, result.trades) == ("UNAVAILABLE", reason, None, None, None)
```

- [ ] **Step 2: Run the aggregator tests and verify they fail**

Run: `python -B -m pytest tests/tree_replay/test_cross_market_flow.py -q --tb=short -p no:cacheprovider`

Expected: FAIL because the input and aggregator types do not exist.

- [ ] **Step 3: Implement exact immutable inputs and output**

```python
@dataclass(frozen=True, kw_only=True)
class GcFlowMinute:
    minute_start: datetime
    available_at: datetime
    volume: float
    delta: float
    trades: float

@dataclass(frozen=True, kw_only=True)
class CrossMarketFlowInput:
    policy: CrossMarketFlowPolicy
    archive_sha256: str
    coverage_start: datetime
    coverage_end: datetime
    minutes: tuple[GcFlowMinute, ...]

@dataclass(frozen=True, kw_only=True)
class CrossMarketFlowContext:
    status: str
    reason: str | None
    target_instrument: str
    source_instrument: str
    source_dataset: str
    decision_time: datetime
    window_start: datetime
    observed_at: datetime | None
    available_at: datetime | None
    volume: float | None
    delta: float | None
    trades: float | None
```

Require strict one-minute ascending rows. For `[window_start, decision_time)`
consider only full minutes whose end is no later than `decision_time`; then
require every such minute, in order, to be supplied and available. Sum only
finite `volume`, `delta`, and `trades` using `math.fsum`. Return a single
deterministic reason selected in this order: identity, coverage, damaged era,
duplicate/order, non-finite, not closed, late, gap. Do not add ratios in this
increment: their window and denominator semantics are a later feature contract.

- [ ] **Step 4: Add the remaining mandatory behavior tests**

Add tests for exact minute-end inclusion, caller-supplied delayed availability,
empty/no-full-minute window, later future minute exclusion, no output price
fields, deterministic aggregate commitment, and repeated invocation equality.

- [ ] **Step 5: Run the focused suite**

Run: `python -B -m pytest tests/tree_replay/test_cross_market_flow_policy.py tests/tree_replay/test_cross_market_flow.py -q --tb=short -p no:cacheprovider`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add trading_system/tree_replay/cross_market_flow.py tests/tree_replay/test_cross_market_flow.py
git commit -m "feat: add causal GC flow context aggregator"
```

### Task 3: Bind the context to full-tree replay evidence without changing the tree

**Files:**
- Create: `trading_system/tree_replay/full_tree_cross_market_context.py`
- Create: `tests/tree_replay/test_full_tree_cross_market_context.py`
- Modify: `trading_system/tree_replay/full_tree_checkpoint.py`
- Modify: `tests/tree_replay/test_full_tree_checkpoint.py`

**Interfaces:**
- Consumes `CrossMarketFlowContext` from Task 2 and `FullTreeEvidenceBundle`/`FullTreeProviderBaseline`.
- Produces `FullTreeCrossMarketContextRecord.capture(bundle, pass_id, context) -> FullTreeCrossMarketContextRecord`.
- Produces `FullTreeCrossMarketContextRecord.commitment() -> dict[str, object]` with target/source identity, decision/window times, status/reason, context digest, and parent bundle/pass commitments only.
- Produces `FullTreeCrossMarketContextBaseline.capture(bundle, records) -> str` for resume verification.

- [ ] **Step 1: Write failing binding tests**

```python
def test_context_record_rejects_a_different_target_or_decision_time_than_the_parent_pass():
    with pytest.raises(ValueError, match="CROSS_MARKET_PARENT"):
        FullTreeCrossMarketContextRecord.capture(bundle, "pass-1", available_context(target="CME:GC"))
    with pytest.raises(ValueError, match="CROSS_MARKET_PARENT"):
        FullTreeCrossMarketContextRecord.capture(bundle, "pass-1", available_context(decision_time=T1 + timedelta(microseconds=1)))

def test_public_commitment_does_not_expose_raw_gc_values_and_resume_digest_detects_change():
    record = FullTreeCrossMarketContextRecord.capture(bundle, "pass-1", available_context())
    public = record.commitment()
    assert "volume" not in public and "delta" not in public and "trades" not in public
    assert FullTreeCrossMarketContextBaseline.capture(bundle, (record,)) != FullTreeCrossMarketContextBaseline.capture(bundle, (changed_value_record,))
```

- [ ] **Step 2: Run binding tests and verify they fail**

Run: `python -B -m pytest tests/tree_replay/test_full_tree_cross_market_context.py -q --tb=short -p no:cacheprovider`

Expected: FAIL because the sidecar contract does not exist.

- [ ] **Step 3: Implement the sidecar record and checkpoint baseline**

The record must bind exactly one context to an existing pass, match the
bundle's instrument and pass `decision_time`, and retain the private context
only in memory. Its public commitment is canonical JSON/SHA-256 like the
existing full-tree contracts. Extend `full_tree_checkpoint.py` only with a
parallel baseline type; do not alter `FullTreeReplayCheckpoint` or claim that
the existing tree replay consumes the context.

- [ ] **Step 4: Add capture/replay equivalence tests**

Construct two identical input frames and prove equal public records/baselines;
then vary only a raw GC value and prove public digest changes without the value
appearing in `repr()` or `commitment()`. Test unavailable contexts preserve
their reason and have no values. Test parent bundle mutation, pass mismatch,
and target/source mismatch are rejected.

- [ ] **Step 5: Run focused replay regressions**

Run: `python -B -m pytest tests/tree_replay/test_cross_market_flow.py tests/tree_replay/test_full_tree_cross_market_context.py tests/tree_replay/test_full_tree_checkpoint.py tests/tree_replay/test_full_tree_capture.py tests/tree_replay/test_full_tree_replay.py -q --tb=short -p no:cacheprovider`

Expected: PASS; existing `TreeReader` behavior has no changed assertions.

- [ ] **Step 6: Commit**

```bash
git add trading_system/tree_replay/full_tree_cross_market_context.py trading_system/tree_replay/full_tree_checkpoint.py tests/tree_replay/test_full_tree_cross_market_context.py tests/tree_replay/test_full_tree_checkpoint.py
git commit -m "feat: bind GC flow context to tree evidence sidecar"
```

### Task 4: Certify source boundaries and update the project record

**Files:**
- Create: `trading_system/tree_spec/cross_market_flow_source.py`
- Create: `tests/tree_spec/test_cross_market_flow_source.py`
- Create: `docs/architecture/GC-XAUUSD-CROSSMARKET-FLOW-USAGE.md`
- Modify: `docs/superpowers/specs/2026-09-15-gc-order-flow-xauusd-context-design.md`
- Modify: `docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md`
- Create: `agent-exchange/status/2026-09-15T<UTC>-codex-gc-xauusd-context.md`

**Interfaces:**
- Consumes the Task 1–3 modules.
- Produces `check_cross_market_flow_source() -> dict[str, object]` with a `VERIFIED`/`BLOCKED` static report and false `ready_for_replay`/`ready_for_training` fields.

- [ ] **Step 1: Write failing static-audit tests**

```python
def test_static_audit_proves_no_price_mapping_or_live_loader_and_false_readiness():
    report = check_cross_market_flow_source()
    assert report["status"] == "VERIFIED"
    assert report["forbidden_price_mapping"] is False
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False

def test_static_audit_blocks_a_future_minute_comparison_or_cvd_token(monkeypatch):
    report = mutated_source_report(monkeypatch, "available_at <= decision_time", "available_at < decision_time")
    assert report["status"] == "BLOCKED"
```

- [ ] **Step 2: Run static-audit tests and verify they fail**

Run: `python -B -m pytest tests/tree_spec/test_cross_market_flow_source.py -q --tb=short -p no:cacheprovider`

Expected: FAIL because the audit is absent.

- [ ] **Step 3: Implement a narrow AST/text static audit**

Audit only local source files. Block network/filesystem-live imports, `cvd` or
price/OHLC output fields, mutation of `TreeReader`/`FullTreeCausalProvider`,
and weakened closed-minute comparison. Verify policy binding, source/target
identity literals, damaged-window call, context sidecar commitment, and false
readiness. The audit must never inspect the raw archive.

- [ ] **Step 4: Document how to use the sidecar safely**

The usage document must show a synthetic caller flow: load policy, construct
`CrossMarketFlowInput` from caller-supplied rows, build context at the same
pass time, capture the sidecar record, and store only its public commitment.
State clearly that source acquisition, historical OANDA coverage, news/options
coverage, economics, dataset construction, model training, and live trading
are still not completed. Update the design status to implemented only after
all verification succeeds; otherwise record the exact failing condition.

- [ ] **Step 5: Run all relevant verification**

Run: `python -B -m pytest tests/tree_replay/test_cross_market_flow_policy.py tests/tree_replay/test_cross_market_flow.py tests/tree_replay/test_full_tree_cross_market_context.py tests/tree_replay/test_full_tree_checkpoint.py tests/tree_replay/test_full_tree_capture.py tests/tree_replay/test_full_tree_replay.py tests/tree_spec/test_cross_market_flow_source.py tests/tree_spec/test_full_tree_capture_source.py tests/tree_spec/test_full_tree_replay_source.py -q --tb=short -p no:cacheprovider`

Run: `python -B -m pytest tests/research/test_gc_canonical_order_flow_input_manifest.py -q --tb=short -p no:cacheprovider`

Run: `git diff --check`

Expected: every command exits 0. Any skipped historical/vendor input is reported as unavailable, not treated as a passing data replay.

- [ ] **Step 6: Record the evidence and commit**

Use the status template with exact test output, the unchanged readiness scope,
the pending OANDA/news/options dependencies, and the fact that a separately
approved tree-branch interface would be required before this context can alter
tree decisions.

```bash
git add trading_system/tree_spec/cross_market_flow_source.py tests/tree_spec/test_cross_market_flow_source.py docs/architecture/GC-XAUUSD-CROSSMARKET-FLOW-USAGE.md docs/superpowers/specs/2026-09-15-gc-order-flow-xauusd-context-design.md docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md agent-exchange/status/2026-09-15T<UTC>-codex-gc-xauusd-context.md
git commit -m "docs: certify GC flow context boundary"
```

## Plan self-review

**Spec coverage:** Task 1 pins identities, allowed fields, timestamps and the damaged range. Task 2 proves causality, missing/late/error behavior and avoids invented features. Task 3 preserves provenance and deterministic replay-side commitments without changing the tree. Task 4 statically audits forbidden paths and records remaining readiness dependencies. The absent current `TreeReader` Order Flow port is explicitly contained rather than hidden.

**Placeholder scan:** No task uses an unbounded implementation placeholder; the one timestamp in the status filename is deliberately generated at execution time to comply with the agent-exchange protocol.

**Type consistency:** `CrossMarketFlowPolicy` feeds `CrossMarketFlowInput`; the latter produces `CrossMarketFlowContext`; the sidecar consumes that context and its baseline is parallel to, not a mutation of, `FullTreeReplayCheckpoint`.

## Execution choice

The user has already asked to continue autonomously. Execute inline in an isolated worktree using `superpowers:executing-plans`, one task at a time with the stated test gates and commits.
