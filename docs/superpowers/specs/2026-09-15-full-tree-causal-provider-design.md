# Full-Tree Causal Provider Design

**Status:** approved architecture; implementation plan follows.

**Decision record:** `agent-exchange/decisions/2026-09-15T060239Z-human-full-tree-causal-provider-design.md`.

**Source authorities:** the accepted `TreeReader` and `TreeRevalidation`
components, chart-desk commit `68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9`,
`docs/architecture/TREE-WALK-READER-CONTRACT.md`, and
`docs/architecture/TREE-REVALIDATION-BINDING-CONTRACT.md`.

## 1. Goal

Build an offline historical replay boundary that runs the complete, accepted
tree from raw evidence available at each decision time. The boundary must
exercise the actual `TreeReader` and its `trade_from_walk` builder, and must
also be capable of supplying the actual `TreeRevalidation` port for historical
pending-plan checks.

The output is a source-faithful observation of one tree pass: stopped walk,
completed walk without a trade plan, refused plan, or observed candidate plan.
It does not create a tracker row, order, fill, economic outcome, dataset row or
model label.

## 2. Why this is a separate subsystem

`CausalAdmissionContext` owns tracker, watch, quote, lock and admission-frame
state for the accepted `level_reversal:5m` spine. The complete tree requires
additional raw ports: news calendar text, options report listing/bytes,
TradingView CSV, independent source clocks, and revalidation deep/calendar/
shadow operations. It also makes repeated reads that are meaningful source
behavior.

The new subsystem consists of a private full-tree evidence bundle, a raw-port
provider, a pass runner and a checkpoint boundary. It does not extend the old
admission context or change the existing `ClosedBarCausalReplay` path.

## 3. Scope and explicit variants

The runner supports exactly these source variants:

| Replay variant | `TreeReader.walk` argument | Meaning |
| --- | --- | --- |
| `full_tree:house` | `house` | Existing tool-level universe used by the source house path. |
| `full_tree:strict` | `strict` | Existing full level universe, including the source pivot additions. |

Variants are independent identities. They may examine the same raw evidence,
but their walk, plan commitment, refusal and later outcomes must never be
merged. `level_reversal:5m` remains owned by the existing replay runner.

## 4. Evidence contracts

### 4.1 Artifact

`FullTreeArtifact` represents one immutable raw value held privately by the
caller. It has these required fields:

| Field | Meaning |
| --- | --- |
| `artifact_id` | Stable identity unique within a bundle. |
| `kind` | `FRAME`, `CLOCK`, `TEXT`, `REPORT_LIST`, `BYTES`, `SHADOW_RESULT`, or `ERROR`. |
| `observed_at` | When the source value describes the world. |
| `available_at` | Earliest replay time at which the value may be read. |
| `covered_through` | Last replay time for which the value may be read. |
| `content_digest` | SHA-256 commitment to its canonical raw value. |
| `value` | Private raw value or supplied exception descriptor; never serialized into a ledger or checkpoint. |

All timestamps are UTC and microsecond exact. The interval must satisfy
`observed_at <= available_at <= covered_through`. An operation may consume an
artifact only when its pass decision time lies within
`[available_at, covered_through]`.

Frame artifacts contain a source-faithful pandas frame plus the corresponding
accepted correction object. Their digest is calculated from canonical columns,
index, values and correction fields. Text and bytes artifacts are committed by
their exact UTF-8 bytes. Clocks are committed by their UTC timestamp. The
provider copies frames before returning them so a tree consumer cannot mutate a
bundle artifact for a later call.

### 4.2 Operation schedule

`FullTreeOperation` binds a source call to one artifact. It has:

```text
operation_id, kind, arguments, artifact_id, sequence
```

`kind` is one of:

```text
FETCH_CORRECTED, NOW_UTC, NOW_EPOCH, NOW_TIMESTAMP,
CALENDAR_TEXT, CALENDAR_EXISTS,
LIST_REPORTS, READ_REPORT, READ_TV_CSV,
DEEP_EXISTS, DEEP_BYTES, ENSURE_SHADOW_PARENT, SHADOW_OPEN
```

`arguments` are canonical JSON and must match the source call exactly. For
example, a `FETCH_CORRECTED` operation contains `symbol`, `timeframe` and
`lookback`; `READ_REPORT` contains its logical report ID. Each pass carries an
ordered tuple of operations. The provider consumes the next operation only if
both kind and arguments match the call it receives. A missing, early, late,
out-of-order or mismatched operation fails closed with a structured provider
error.

This schedule preserves source behavior. It does not globally memoize a
request. If source code calls `fetch_corrected(symbol, "15m", 10)` twice, the
schedule contains two operations. They may bind to the same artifact ID when
the same evidence is valid for both calls, but they remain separate trace
events.

### 4.3 Pass and bundle

`FullTreePass` contains `pass_id`, `decision_time`, `source_variant`, `mode`
and its ordered operations. A normal pass has `mode="TREE_WALK"`; a pending-plan
check has `mode="TREE_REVALIDATION"` plus a private pending-plan value committed
by its public digest. Its time is strictly later than the preceding pass. The
pass has no activation state: this subsystem observes the tree before admission.

`FullTreeEvidenceBundle` contains `run_id`, exact `instrument`, a tuple of
artifacts and a tuple of passes. Artifact IDs and pass IDs are unique. The
bundle has a canonical public manifest made only of identities, times, kinds,
operation arguments and digests. The private artifact values are deliberately
absent from `as_dict`, run ledgers and checkpoints.

## 5. Provider behavior

`FullTreeCausalProvider(bundle, pass_id)` exposes only the raw ports required
by accepted source consumers:

```python
fetch_corrected(symbol, timeframe, lookback)
now_utc()
now_epoch()
now_timestamp(*, tz)
calendar_text(path)
calendar_exists(path)
list_reports()
read_report(logical_id)
read_tv_csv(filename)
deep_exists(key)
deep_bytes(key)
ensure_shadow_parent(*, parents, exist_ok)
shadow_open(mode, encoding)
```

The provider has no default filesystem, network client, manifest lookup or
fallback data source. Constructing it makes no calls. Every call consumes the
next scheduled operation and records a private trace containing operation ID,
kind, arguments and artifact digest. The public pass record contains only the
digest-bound trace summary.

`shadow_open` returns an in-memory context manager. It validates the source
mode and encoding, captures any write for trace comparison, and never creates a
real file. Supplied shadow failures are raised at the scheduled source point;
the accepted source code retains its own catch/continue behavior.

## 6. Runner behavior

`FullTreeCausalReplay` owns an immutable bundle and creates a fresh provider
for each pass.

For a normal tree-observation pass it performs this sequence:

1. Validate the pass variant and its bundle manifest.
2. Create `FullTreeCausalProvider` at that pass.
3. Construct `TreeReader(provider)`; construction must consume zero operations.
4. Run `walk(instrument, tree_variant)`.
5. Run `trade_from_walk(walk)` only when the walk is complete and directional.
6. Require every scheduled operation to have been consumed, unless the source
   path returned before later operations were reached. The unconsumed suffix is
   recorded as not reached, never treated as evidence consumed.
7. Append one chained, payload-free observation record.

The observation outcomes are:

| Outcome | Meaning |
| --- | --- |
| `TREE_BLOCKED` | The provider contract could not provide source-faithful evidence. |
| `TREE_STOPPED` | The source tree stopped for its own reason. |
| `TREE_OBSERVED_NO_PLAN` | The tree reached its final stage but produced no plan. |
| `TREE_REFUSED_PLAN` | The builder produced an original refusal. |
| `TREE_CANDIDATE_OBSERVED` | A source plan was built and is recorded as an observation. |
| `UNSUPPORTED` | The pass declares another source variant. |

Candidate records contain a `walk_digest`, optional `plan_digest`, direction,
variant, reached stage, source reason/refusal category and artifact-operation
commitments. They do not contain raw frames, report contents, net P&L, net R,
success, failure, fill or tracker identity.

`TreeRevalidation(provider)` is available only through an explicit
`TREE_REVALIDATION` pass mode. Its original `revalidate_pending` three-result
contract `(ok, reason, verified)` produces a revalidation observation. It does
not construct a replacement plan or turn a clean result into a fill or label.

## 7. Checkpoint and resume

The checkpoint boundary is between completed passes. A pass is rerun from its
first scheduled operation after interruption; this is safe because the provider
has no external effects and shadow writes are in memory.

`FullTreeProviderBaseline.capture(bundle)` stores only the public bundle-manifest
fingerprint. A checkpoint stores the baseline fingerprint, bundle fingerprint,
chained ledger, next pass index and the last completed decision time. Resume
requires the caller to retain and supply the same private bundle. A digest,
manifest, pass sequence or ledger-prefix mismatch blocks resume.

An uninterrupted run and a run resumed at any completed pass boundary must
produce identical public ledger records and trace commitments.

## 8. Source and data invariants

- The source tree, matrix, pricing and revalidation implementations remain
  untouched.
- The runner uses actual `TreeReader` and `TreeRevalidation`, never a supplied
  final `Walk`, `Plan`, boolean decision or hand-written approximation.
- Source-specific mixed forming/completed row conventions remain visible.
- Independent source clock calls stay independent. A clock read is not hoisted
  to the beginning of a pass.
- Optional options/pattern/liquidity failures retain their original behavior.
  Missing data is not manufactured into a negative signal.
- The source news blackout and revalidation news shadow keep their different
  source windows and consumers.
- No raw market data is placed in `agent-exchange`, replay ledger or checkpoint.
- `ready_for_replay` and `ready_for_training` remain false. This component is
  prerequisite evidence for later replay, simulation and training work.

## 9. Verification and acceptance

Acceptance requires all of the following:

1. Contract tests reject duplicate IDs, invalid timestamp windows, digest shape
   errors, unsupported variants and operations with noncanonical arguments.
2. Provider tests prove exact order, repeated reads, deep copies, late/missing
   artifacts, errors at the scheduled call and absence of filesystem/network
   fallback.
3. Runtime tests run actual house and strict walks on literal multiframe tapes;
   they cover source stop, completed no-plan, refused plan and observed plan.
4. Revalidation tests cover the under-two-hour skip, exactly-two-hour check,
   opposing tree, stopped/unavailable tree and shadow operation ordering.
5. Checkpoint tests prove resumed and uninterrupted ledgers are identical and
   reject changed bundle, artifact digest, operation schedule or clock state.
6. A static audit pins the required full-tree raw port surface and proves the
   runner does not import a live loader or accept final-result injection.
7. Existing tree-reader, tree-revalidation and closed-bar replay suites remain
   green. Independent review is required before component acceptance.

## 10. Out of scope

Economic fill simulation, costs, P&L, success/failure labels, dataset tables,
model fitting, management policies, data-vendor acquisition, raw-data retention,
broker execution and live deployment are separate subsequent workstreams.
