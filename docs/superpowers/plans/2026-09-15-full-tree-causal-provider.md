# Full-Tree Causal Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** Build an offline, source-faithful replay boundary that runs the accepted complete tree from scheduled historical evidence and records only what the tree observed.

**Architecture:** Add a parallel full-tree subsystem under \`trading_system/tree_replay/\`. It supplies actual \`TreeReader\` and \`TreeRevalidation\` calls through an in-memory, ordered raw-port provider; it neither extends \`CausalAdmissionContext\` nor changes the accepted \`level_reversal:5m\` replay path. Immutable public commitments identify evidence and execution order, while raw values remain private to the caller.

**Tech Stack:** Python 3, dataclasses, pandas, pytest, existing tree replay contracts and source-audit CLI conventions.

**Spec:** \`docs/superpowers/specs/2026-09-15-full-tree-causal-provider-design.md\`

## Global Constraints

- Support only \`full_tree:house\` and \`full_tree:strict\`; do not modify \`level_reversal:5m\`.
- Run the accepted \`TreeReader\`, \`trade_from_walk\`, and, in explicit mode, \`TreeRevalidation\`; never accept a supplied final walk, plan, boolean or hand-written approximation.
- All operation calls are scheduled, ordered and digest-bound. Repeated source reads remain distinct operations.
- No filesystem, network, live loader, default data source, raw data, raw frames, report contents, raw text, fills, P&L, labels or model outputs may appear in a public ledger, checkpoint or \`agent-exchange/\`.
- A source failure must arise at the scheduled source call. Preserve source catch/continue behavior; do not invent negative signals.
- Resume only between completed passes. A resumed ledger must equal the uninterrupted ledger byte-for-byte at the public-contract level.
- Keep existing tree reader, revalidation and closed-bar suites green. Every task requires independent review before component acceptance.

---

## File Structure

| File | Responsibility |
| --- | --- |
| \`trading_system/tree_replay/full_tree_contracts.py\` | Immutable full-tree artifact, operation, pass, bundle and public-manifest contracts. |
| \`trading_system/tree_replay/full_tree_provider.py\` | Ordered in-memory raw-port provider for TreeReader and TreeRevalidation. |
| \`trading_system/tree_replay/full_tree_replay.py\` | Actual source-tree pass runner, observation ledger and revalidation mode. |
| \`trading_system/tree_replay/full_tree_checkpoint.py\` | Public baseline/checkpoint capture and safe resume validation. |
| \`tools/check_full_tree_replay_source_parity.py\` | Static audit of required raw ports and prohibited live/final-result shortcuts. |
| \`tests/tree_replay/test_full_tree_contracts.py\` | Contract invariants and private/public boundary tests. |
| \`tests/tree_replay/test_full_tree_provider.py\` | Port ordering, repeats, copying and scheduled failure tests. |
| \`tests/tree_replay/test_full_tree_replay.py\` | Actual house/strict walk and revalidation behavior tests. |
| \`tests/tree_replay/test_full_tree_checkpoint.py\` | Interruption/resume equivalence and rejection tests. |
| \`tests/tree_spec/test_full_tree_replay_source.py\` | Static-source audit tests. |

### Task 1: Immutable evidence and schedule contracts

**Files:**
- Create: \`trading_system/tree_replay/full_tree_contracts.py\`
- Create: \`tests/tree_replay/test_full_tree_contracts.py\`

**Interfaces:**
- Produces \`FullTreeArtifact\`, \`FullTreeOperation\`, \`FullTreePass\`, \`FullTreeEvidenceBundle\`, \`TreeFramePayload\`, \`ProviderErrorPayload\`, \`canonical_operation_arguments\`, \`full_tree_manifest\`, and \`full_tree_manifest_digest\`.
- \`FullTreeArtifact\` fields are \`artifact_id, kind, observed_at, available_at, covered_through, content_digest, value\`.
- \`FullTreeOperation\` fields are \`operation_id, kind, arguments, artifact_id, sequence\`.
- \`FullTreePass\` fields are \`pass_id, decision_time, source_variant, mode, operations\`.
- \`FullTreeEvidenceBundle\` fields are \`run_id, instrument, artifacts, passes\`.

- [ ] **Step 1: Write the failing contract tests**

\`\`\`python
def test_manifest_excludes_private_artifact_values() -> None:
    bundle = make_bundle(value=b"private calendar contents")
    manifest = full_tree_manifest(bundle)

    assert "private calendar contents" not in repr(manifest)
    assert manifest["artifacts"][0]["content_digest"] == bundle.artifacts[0].content_digest


def test_bundle_rejects_noncanonical_operation_arguments() -> None:
    operation = FullTreeOperation(
        operation_id="op-1",
        kind="FETCH_CORRECTED",
        arguments={"lookback": 10, "symbol": "OANDA:XAUUSD", "timeframe": "5m"},
        artifact_id="frame-1",
        sequence=0,
    )

    with pytest.raises(ValueError, match="FULL_TREE_NONCANONICAL_ARGUMENTS"):
        FullTreeEvidenceBundle(run_id="run-1", instrument="OANDA:XAUUSD",
                               artifacts=(make_artifact(),), passes=(make_pass(operation),))
\`\`\`

- [ ] **Step 2: Run the tests to establish the red state**

Run: \`python -B -m pytest tests/tree_replay/test_full_tree_contracts.py -q --tb=short -p no:cacheprovider\`

Expected: FAIL because \`full_tree_contracts\` does not exist.

- [ ] **Step 3: Implement the smallest immutable contracts**

\`\`\`python
@dataclass(frozen=True)
class FullTreeArtifact:
    artifact_id: str
    kind: str
    observed_at: datetime
    available_at: datetime
    covered_through: datetime
    content_digest: str
    value: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if not (self.observed_at <= self.available_at <= self.covered_through):
            raise ValueError("FULL_TREE_INVALID_ARTIFACT_WINDOW")
        if not re.fullmatch(r"[0-9a-f]{64}", self.content_digest):
            raise ValueError("FULL_TREE_INVALID_ARTIFACT_DIGEST")
\`\`\`

Implement canonical arguments as UTF-8 JSON with sorted keys, compact separators and only JSON scalar/list/map values. Reject values whose supplied mapping is not identical to that canonical decode. Make \`as_dict()\` and \`full_tree_manifest()\` expose IDs, kinds, timestamps, arguments, sequences and digests only; omit \`value\`.

- [ ] **Step 4: Add edge-contract cases and run the focused suite**

Add tests for duplicate artifact/pass/operation IDs, unsupported variants, non-increasing pass times, invalid digest shape, operation sequence gaps, artifact references that do not exist, and \`TreeFramePayload\` requiring a pandas frame.

Run: \`python -B -m pytest tests/tree_replay/test_full_tree_contracts.py -q --tb=short -p no:cacheprovider\`

Expected: PASS.

- [ ] **Step 5: Commit the isolated contract task**

\`\`\`bash
git add trading_system/tree_replay/full_tree_contracts.py tests/tree_replay/test_full_tree_contracts.py
git commit -m "feat: add full-tree causal evidence contracts"
\`\`\`

### Task 2: Ordered, in-memory raw-port provider

**Files:**
- Create: \`trading_system/tree_replay/full_tree_provider.py\`
- Create: \`tests/tree_replay/test_full_tree_provider.py\`
- Modify: \`trading_system/tree_replay/full_tree_contracts.py\`

**Interfaces:**
- Consumes the Task 1 bundle and a chosen \`FullTreePass\`.
- Produces \`FullTreeCausalProvider(bundle: FullTreeEvidenceBundle, pass_id: str)\`.
- Provider public methods are exactly \`fetch_corrected(symbol, timeframe, lookback)\`, \`now_utc()\`, \`now_epoch()\`, \`now_timestamp(*, tz)\`, \`calendar_text(path)\`, \`calendar_exists(path)\`, \`list_reports()\`, \`read_report(logical_id)\`, \`read_tv_csv(filename)\`, \`deep_exists(key)\`, \`deep_bytes(key)\`, \`ensure_shadow_parent(*, parents, exist_ok)\`, \`shadow_open(mode, encoding)\`, \`assert_no_unexpected_calls()\`, and \`public_trace()\`.
- \`fetch_corrected\` returns the Task 1 \`TreeFramePayload\`; clock ports return UTC values; shadow writes live only in memory.

- [ ] **Step 1: Write failing provider tests for exact order and repeated reads**

\`\`\`python
def test_repeated_fetches_are_two_distinct_scheduled_operations() -> None:
    provider = FullTreeCausalProvider(bundle_with_operations(
        fetch("op-1", "frame-1"), fetch("op-2", "frame-1")
    ), pass_id="pass-1")

    first = provider.fetch_corrected("OANDA:XAUUSD", "5m", 600)
    first.frame.iloc[0, 0] = -999
    second = provider.fetch_corrected("OANDA:XAUUSD", "5m", 600)

    assert second.frame.iloc[0, 0] != -999
    assert [entry["operation_id"] for entry in provider.public_trace()] == ["op-1", "op-2"]


def test_out_of_order_port_call_fails_closed() -> None:
    provider = FullTreeCausalProvider(bundle_with_operations(clock("op-1")), pass_id="pass-1")

    with pytest.raises(FullTreeProviderError, match="FULL_TREE_OPERATION_MISMATCH"):
        provider.calendar_text("calendar.txt")
\`\`\`

- [ ] **Step 2: Run the provider test file in red**

Run: \`python -B -m pytest tests/tree_replay/test_full_tree_provider.py -q --tb=short -p no:cacheprovider\`

Expected: FAIL because \`FullTreeCausalProvider\` does not exist.

- [ ] **Step 3: Implement a single schedule-consuming primitive and all source ports**

\`\`\`python
def _consume(self, kind: str, arguments: Mapping[str, object]) -> FullTreeArtifact:
    expected = self._next_operation()
    canonical = canonical_operation_arguments(arguments)
    if expected.kind != kind or expected.arguments != canonical:
        raise FullTreeProviderError("FULL_TREE_OPERATION_MISMATCH")
    artifact = self._artifact_by_id[expected.artifact_id]
    if not (artifact.available_at <= self.decision_time <= artifact.covered_through):
        raise FullTreeProviderError("FULL_TREE_ARTIFACT_UNAVAILABLE")
    self._cursor += 1
    self._trace.append(_public_trace_entry(expected, artifact))
    return artifact
\`\`\`

Return frame copies with \`frame.copy(deep=True)\`. For \`ERROR\` payloads raise the declared exception class only after consuming the operation. Implement \`shadow_open\` as an in-memory text context manager that validates scheduled \`mode\` and \`encoding\`, captures writes and exposes no filesystem path. Do not import \`pathlib\`, \`requests\`, live loaders or any storage client.

- [ ] **Step 4: Prove the public/private boundary and source-error timing**

Add tests for a late artifact, a missing operation, supplied \`ERROR\` on \`read_report\`, independent clocks, report-list ordering, shadow-write capture, and a trace that contains no raw text/bytes/frame values.

Run: \`python -B -m pytest tests/tree_replay/test_full_tree_provider.py -q --tb=short -p no:cacheprovider\`

Expected: PASS.

- [ ] **Step 5: Commit the provider task**

\`\`\`bash
git add trading_system/tree_replay/full_tree_contracts.py trading_system/tree_replay/full_tree_provider.py tests/tree_replay/test_full_tree_provider.py
git commit -m "feat: add ordered full-tree evidence provider"
\`\`\`

### Task 3: Actual TreeReader house/strict observation runner

**Files:**
- Create: \`trading_system/tree_replay/full_tree_replay.py\`
- Create: \`tests/tree_replay/test_full_tree_replay.py\`
- Modify: \`trading_system/tree_replay/__init__.py\` only if that package currently exports replay APIs.

**Interfaces:**
- Consumes \`FullTreeCausalProvider\`, \`TreeReader\` from \`trading_system.tree_replay._vendor.tree_walk\`, and its \`trade_from_walk\` behavior.
- Produces \`FullTreeCausalReplay(bundle)\`, \`FullTreeObservationRecord\`, \`FullTreeReplayResult\`, and \`run_pass(pass_id)\`.
- \`FullTreeObservationRecord\` fields are \`pass_id, decision_time, source_variant, outcome, reached_stage, direction, reason_category, source_reason_digest, walk_digest, plan_digest, trace_digest, previous_record_digest, record_digest\`.

- [ ] **Step 1: Write red tests that use literal multiframe evidence and actual source methods**

\`\`\`python
def test_house_and_strict_are_independent_actual_tree_observations() -> None:
    house = FullTreeCausalReplay(house_bundle()).run_pass("house-pass").record
    strict = FullTreeCausalReplay(strict_bundle()).run_pass("strict-pass").record

    assert house.source_variant == "full_tree:house"
    assert strict.source_variant == "full_tree:strict"
    assert house.record_digest != strict.record_digest


def test_tree_reader_construction_consumes_no_operation() -> None:
    replay = FullTreeCausalReplay(bundle_for_stopped_walk())

    result = replay.run_pass("pass-1")

    assert result.record.outcome == "TREE_STOPPED"
    assert result.record.trace_digest == digest_of_expected_source_calls()
\`\`\`

The fixtures must construct real frames and scheduled artifacts. They must not monkeypatch \`walk\`, inject a \`Walk\`, inject a \`Plan\`, or replace \`trade_from_walk\`.

- [ ] **Step 2: Run runner tests in red**

Run: \`python -B -m pytest tests/tree_replay/test_full_tree_replay.py -q --tb=short -p no:cacheprovider\`

Expected: FAIL because the runner does not exist.

- [ ] **Step 3: Implement exact variant dispatch and payload-free observation records**

\`\`\`python
def run_pass(self, pass_id: str) -> FullTreeReplayResult:
    selected = self._bundle.pass_by_id(pass_id)
    if selected.mode != "TREE_WALK":
        raise ValueError("FULL_TREE_PASS_MODE_MISMATCH")
    if selected.source_variant not in {"full_tree:house", "full_tree:strict"}:
        return self._unsupported(selected)
    provider = FullTreeCausalProvider(self._bundle, pass_id)
    reader = TreeReader(provider)
    walk = reader.walk(self._bundle.instrument, selected.source_variant.removeprefix("full_tree:"))
    plan = reader.trade_from_walk(walk) if walk.complete and walk.direction else None
    return self._append_observation(selected, walk, plan, provider)
\`\`\`

Classify only \`TREE_BLOCKED\`, \`TREE_STOPPED\`, \`TREE_OBSERVED_NO_PLAN\`, \`TREE_REFUSED_PLAN\`, \`TREE_CANDIDATE_OBSERVED\`, or \`UNSUPPORTED\`. Create stable semantic summaries from approved primitive fields; hash summaries with canonical JSON. Never call \`repr(walk)\`, store raw facts, source reports, frames, P&L, fills or labels.

- [ ] **Step 4: Complete source-outcome and chain tests**

Add actual-source tests for a source stop, completed non-directional walk, builder refusal, observed candidate, unsupported variant, provider-blocked pass, and a two-pass ledger whose second \`previous_record_digest\` is the first record digest.

Run: \`python -B -m pytest tests/tree_replay/test_full_tree_replay.py -q --tb=short -p no:cacheprovider\`

Expected: PASS.

- [ ] **Step 5: Commit the runner task**

\`\`\`bash
git add trading_system/tree_replay/full_tree_replay.py tests/tree_replay/test_full_tree_replay.py
git commit -m "feat: replay full tree from causal evidence"
\`\`\`

### Task 4: Explicit TreeRevalidation pass mode

**Files:**
- Modify: \`trading_system/tree_replay/full_tree_contracts.py\`
- Modify: \`trading_system/tree_replay/full_tree_replay.py\`
- Modify: \`tests/tree_replay/test_full_tree_replay.py\`

**Interfaces:**
- Extends \`FullTreePass.mode\` with \`"TREE_REVALIDATION"\` and enables its private \`pending_plan\` value committed by \`pending_plan_digest\`.
- Produces \`run_revalidation_pass(pass_id)\` and an observation reason based on the original three-tuple \`(ok, reason, verified)\`.
- Consumes actual \`TreeRevalidation(provider)\`; it does not create a replacement plan.

- [ ] **Step 1: Write failing revalidation boundary tests**

\`\`\`python
def test_revalidation_under_two_hours_preserves_source_skip() -> None:
    record = FullTreeCausalReplay(revalidation_bundle(age_minutes=119)).run_pass("revalidate-1").record

    assert record.outcome == "TREE_OBSERVED_NO_PLAN"
    assert record.reason_category == "REVALIDATION_UNVERIFIED_SKIP"


def test_revalidation_at_two_hours_consumes_scheduled_tree_evidence() -> None:
    record = FullTreeCausalReplay(revalidation_bundle(age_minutes=120)).run_pass("revalidate-2").record

    assert record.reason_category == "REVALIDATION_VERIFIED"
    assert record.trace_digest == digest_of_expected_revalidation_calls()
\`\`\`

- [ ] **Step 2: Run the narrow red tests**

Run: \`python -B -m pytest tests/tree_replay/test_full_tree_replay.py -q -k revalidation --tb=short -p no:cacheprovider\`

Expected: FAIL because revalidation mode is unsupported.

- [ ] **Step 3: Dispatch to the original revalidation component only in the explicit mode**

\`\`\`python
if selected.mode == "TREE_REVALIDATION":
    provider = FullTreeCausalProvider(self._bundle, pass_id)
    ok, reason, verified = TreeRevalidation(provider).revalidate_pending(selected.pending_plan)
    return self._append_revalidation_observation(
        selected, ok=ok, reason=reason, verified=verified, provider=provider
    )
\`\`\`

Validate that \`pending_plan\` is present only in \`TREE_REVALIDATION\`, its canonical digest matches the declared one, and a tree-walk pass cannot silently use it. Map the original return values to a finite reason category and a digest of the original reason text; do not translate them to execution, fill or training outcomes.

- [ ] **Step 4: Add adversarial source-preservation cases**

Add tests for exactly two hours, opposing direction, stopped/unavailable source tree, news-calendar shadow ordering and in-memory shadow write. Assert that the provider preserves scheduled failures for the component’s own catch/continue branches.

Run: \`python -B -m pytest tests/tree_replay/test_full_tree_replay.py -q -k revalidation --tb=short -p no:cacheprovider\`

Expected: PASS.

- [ ] **Step 5: Commit the revalidation mode**

\`\`\`bash
git add trading_system/tree_replay/full_tree_contracts.py trading_system/tree_replay/full_tree_replay.py tests/tree_replay/test_full_tree_replay.py
git commit -m "feat: add causal full-tree revalidation passes"
\`\`\`

### Task 5: Checkpoint and resumable public ledger

**Files:**
- Create: \`trading_system/tree_replay/full_tree_checkpoint.py\`
- Create: \`tests/tree_replay/test_full_tree_checkpoint.py\`
- Modify: \`trading_system/tree_replay/full_tree_replay.py\`

**Interfaces:**
- Produces \`FullTreeProviderBaseline.capture(bundle)\`, \`FullTreeReplayCheckpoint\`, \`FullTreeCheckpointStore\`, \`checkpoint_after(result, next_pass_index)\`, and \`resume(bundle, checkpoint)\`.
- A checkpoint contains only \`baseline_digest, bundle_manifest_digest, records, next_pass_index, last_completed_decision_time\`.
- Consumes the caller-retained private \`FullTreeEvidenceBundle\`; no artifact value is serialized.

- [ ] **Step 1: Write red equivalence and tamper tests**

\`\`\`python
def test_resume_matches_uninterrupted_public_ledger() -> None:
    uninterrupted = FullTreeCausalReplay(bundle_three_passes()).run_all()
    interrupted = FullTreeCausalReplay(bundle_three_passes())
    first = interrupted.run_pass("pass-1")
    checkpoint = interrupted.checkpoint_after(first, next_pass_index=1)

    resumed = FullTreeCausalReplay.resume(bundle_three_passes(), checkpoint).run_all()

    assert resumed.records == uninterrupted.records


def test_resume_rejects_changed_operation_schedule() -> None:
    checkpoint = checkpoint_after_first_pass(bundle_three_passes())

    with pytest.raises(ValueError, match="FULL_TREE_CHECKPOINT_BUNDLE_MISMATCH"):
        FullTreeCausalReplay.resume(bundle_with_changed_operation(), checkpoint)
\`\`\`

- [ ] **Step 2: Run checkpoint tests in red**

Run: \`python -B -m pytest tests/tree_replay/test_full_tree_checkpoint.py -q --tb=short -p no:cacheprovider\`

Expected: FAIL because checkpoint APIs do not exist.

- [ ] **Step 3: Implement capture, restore and ledger-prefix validation**

\`\`\`python
@dataclass(frozen=True)
class FullTreeReplayCheckpoint:
    baseline_digest: str
    bundle_manifest_digest: str
    records: tuple[FullTreeObservationRecord, ...]
    next_pass_index: int
    last_completed_decision_time: datetime | None

    def as_dict(self) -> dict[str, object]:
        return {"baseline_digest": self.baseline_digest, ...}
\`\`\`

On resume, recompute the bundle manifest digest, validate record-chain digests in sequence, confirm \`next_pass_index\` equals the record count, and require the last record time to equal \`last_completed_decision_time\`. Rerun an interrupted pass only from its first operation; no provider state survives a checkpoint.

- [ ] **Step 4: Add negative cases and run the complete checkpoint suite**

Add changed artifact digest, changed clock artifact, changed pass time, changed ledger predecessor and a checkpoint containing a raw value key. The last case must be rejected before running a pass.

Run: \`python -B -m pytest tests/tree_replay/test_full_tree_checkpoint.py -q --tb=short -p no:cacheprovider\`

Expected: PASS.

- [ ] **Step 5: Commit checkpoint support**

\`\`\`bash
git add trading_system/tree_replay/full_tree_checkpoint.py trading_system/tree_replay/full_tree_replay.py tests/tree_replay/test_full_tree_checkpoint.py
git commit -m "feat: checkpoint full-tree causal replay"
\`\`\`

### Task 6: Static source audit and regression integration

**Files:**
- Create: \`tools/check_full_tree_replay_source_parity.py\`
- Create: \`tests/tree_spec/test_full_tree_replay_source.py\`
- Modify: \`docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md\`

**Interfaces:**
- Produces a CLI result \`VERIFIED\` only if all raw source port names are bound, actual \`TreeReader\` and \`TreeRevalidation\` imports are present, and no prohibited live/final-result path is imported.
- The audit accepts \`--source-root\` for the pinned source checkout and returns non-zero for source/API mismatch.

- [ ] **Step 1: Write failing static audit tests**

\`\`\`python
def test_audit_requires_all_tree_reader_and_revalidation_ports(tmp_path: Path) -> None:
    result = run_audit(tmp_path, provider_text="class FullTreeCausalProvider:\\n    def now_utc(self): pass\\n")

    assert result.returncode != 0
    assert "READ_TV_CSV" in result.stdout
    assert "SHADOW_OPEN" in result.stdout


def test_audit_rejects_final_result_injection(tmp_path: Path) -> None:
    result = run_audit(tmp_path, runner_text="def run(walk): return walk")

    assert result.returncode != 0
    assert "FINAL_RESULT_INJECTION" in result.stdout
\`\`\`

- [ ] **Step 2: Run the static audit tests in red**

Run: \`python -B -m pytest tests/tree_spec/test_full_tree_replay_source.py -q --tb=short -p no:cacheprovider\`

Expected: FAIL because the CLI does not exist.

- [ ] **Step 3: Implement deterministic source/API checks**

Make the CLI read only source text from the supplied root and local implementation text. Require every named provider method, \`TreeReader\`, \`TreeRevalidation\`, both supported variants and the absence of imports/references to known live loader modules or a public \`walk\`/ \`plan\` runner parameter. Emit one line per check and an overall \`VERIFIED\` or \`FAILED\` result.

- [ ] **Step 4: Run full component and inherited regressions**

Run:

\`\`\`powershell
python -B -m pytest tests/tree_replay/test_full_tree_contracts.py tests/tree_replay/test_full_tree_provider.py tests/tree_replay/test_full_tree_replay.py tests/tree_replay/test_full_tree_checkpoint.py tests/tree_replay/test_tree_walk.py tests/tree_replay/test_tree_revalidation.py tests/tree_replay/test_causal_replay.py tests/tree_spec/test_full_tree_replay_source.py -q --tb=short -p no:cacheprovider
python -B tools/check_full_tree_replay_source_parity.py --source-root C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
\`\`\`

Expected: pytest PASS and CLI \`VERIFIED\`.

- [ ] **Step 5: Update the tracker and commit the audit**

Record exact test output, source pin and review state in the tracker. Do not state \`ready_for_replay\` or \`ready_for_training\`.

\`\`\`bash
git add tools/check_full_tree_replay_source_parity.py tests/tree_spec/test_full_tree_replay_source.py docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md
git commit -m "test: audit full-tree causal replay binding"
\`\`\`

### Task 7: Independent review and component acceptance

**Files:**
- Create: \`agent-exchange/inbox/groq/<timestamp>-codex-full-tree-provider-review.md\`
- Create: \`agent-exchange/inbox/claude-code/<timestamp>-codex-full-tree-provider-review.md\`
- Create: \`agent-exchange/status/<timestamp>-codex-full-tree-provider-progress.md\`
- Create after clean review: \`agent-exchange/status/<timestamp>-codex-full-tree-provider-accepted.md\`

**Interfaces:**
- Consumes the task commits, exact focused command output, static-audit output and source pin.
- Produces either a revision task contract or an acceptance record. A green local test run alone does not produce acceptance.

- [ ] **Step 1: Create two independent, read-only review requests**

Use \`agent-exchange/templates/review.md\`. Ask each reviewer to inspect: source-faithful actual-reader use, operation ordering and repeats, artifact availability windows, raw-data non-disclosure, source failure timing, revalidation mode, checkpoint equivalence, existing-path isolation and test adequacy. Include hashes and commands; include no raw market data.

- [ ] **Step 2: Run the final verification before reading reviews**

Run:

\`\`\`powershell
python -B -m pytest tests/tree_replay/test_full_tree_contracts.py tests/tree_replay/test_full_tree_provider.py tests/tree_replay/test_full_tree_replay.py tests/tree_replay/test_full_tree_checkpoint.py tests/tree_replay/test_tree_walk.py tests/tree_replay/test_tree_revalidation.py tests/tree_replay/test_causal_replay.py tests/tree_spec/test_full_tree_replay_source.py -q --tb=short -p no:cacheprovider
python -B tools/check_full_tree_replay_source_parity.py --source-root C:\Users\roeea\AppData\Local\Temp\tr-tree-source-review-4efd65cf2e284d97a81199af6195f149
git diff --check
\`\`\`

Expected: all tests PASS, audit \`VERIFIED\`, whitespace check clean.

- [ ] **Step 3: Triage each review result against code and source**

For every finding, reproduce the claimed behavior with a focused test or record why the finding is not applicable. If code changes, add a regression test first, rerun the relevant source audit and request re-review of the changed scope.

- [ ] **Step 4: Create a truthful acceptance or revision status**

Acceptance status must list the exact source pin, commands, result counts, reviewer identities, reviewed commit hashes and scope boundaries. It must say that this is prerequisite evidence only: no data-vendor approval, raw retention approval, simulation, labeled dataset, model promotion, broker execution or live trading is authorized.

- [ ] **Step 5: Commit only the non-sensitive coordination records**

\`\`\`bash
git add agent-exchange/inbox/groq agent-exchange/inbox/claude-code agent-exchange/status
git commit -m "docs: record full-tree provider review outcome"
\`\`\`
