# Project Agent Memory

## Start here — Yuval handoff, 2026-09-16

Read `PROJECT_STATE.md` first, then `docs/architecture/YUVAL-HANDOFF.md` for
setup and the exact continuation queue. These are the current navigation and
status snapshot; the dated paragraphs below preserve component history.
When asked to "continue the plan", resume from that queue and check new exchange
results before selecting work. Old "next", "running", agent IDs and session IDs
below are historical observations, not evidence of a process running today.
The active branch is `plan/tree-to-trained-model-langgraph`, not `main`.
The governing design is the 2026-09-08 outcome-learning plan with its 2026-09-14
dynamic-management extension. Earlier numbered GC direction-model phases are
retained research history and do not establish readiness for the current goal.

Current source decision: OANDA:XAUUSD price/trade identity, with Databento
CME:GC closed-minute Order Flow as context only (no price alias, no CVD).
Full-tree provider, evidence capture and GC context have implementations and
local tests, but independent acceptance remains pending. A review request file
does not establish that a reviewer is running. Source access/retention permission
exists; actual OANDA historical evidence and news/options coverage are still
missing. The fixed-TP1 economic contract request is
`agent-exchange/inbox/human/2026-09-15T104734Z-human-fixed-full-tp1-economic-contract-required.md`.
Do not ask again which target instrument or GC context policy was selected.
No current outcome dataset or trained selection/management model is certified.

Source-audit tests use `.source-checkouts/` (or explicit environment overrides).
Prepare exact pins with `python tools/prepare_tree_sources.py`; source checkouts
and market data are local dependencies, not files to publish. The handoff guide
distinguishes source-code restoration from private data restoration.


## Active Trading-Model Design (2026-09-08)

For tree/model work, read the current agreed design before earlier phase plans:

- `docs/architecture/TR-TREE-OUTCOME-LEARNING-PLAN-2026-09-08.md`
- `docs/superpowers/plans/2026-09-08-tree-replay-foundation.md`
- `docs/superpowers/plans/2026-09-08-existing-baseline-contracts.md`
- `docs/superpowers/plans/2026-09-09-asof-ema-adapter.md`
- `docs/superpowers/plans/2026-09-09-session-ema-history.md`
- `docs/superpowers/plans/2026-09-09-level-reversal-asof.md`
- `docs/superpowers/plans/2026-09-09-reversal-pricing.md`
- `docs/superpowers/plans/2026-09-09-period-state-and-ranges.md`
- `docs/superpowers/plans/2026-09-09-correction-asof.md`
- `docs/superpowers/plans/2026-09-09-historical-levelmap-core.md`
- `docs/superpowers/plans/2026-09-09-reversal-producer-asof.md`
- `docs/architecture/TREE-OUTCOME-IMPLEMENTATION-TRACKER.md`
- `agent-exchange/decisions/2026-09-08T180046Z-user-economic-target-and-baseline.md`
- `agent-exchange/reviews/2026-09-08T175056Z-codex-existing-alerts-tree-study.md`

The objective is a model that filters/improves faithful tree-generated candidates,
not generic direction labels per bar. Source inventory is not an executable tree.
Unresolved domain definitions must remain explicit; never invent thresholds.

Dynamic-management scope update (2026-09-14): read master section 10א and tracker
J0–J7 before further tree/model planning. The user requested incorporation of the
three management HTMLs, Sagiv transcript and review conclusions into the work plan.
Review: `agent-exchange/reviews/2026-09-14T181224Z-codex-dynamic-management-materials.md`.
Dynamic management is now planned scope; J0 review/documentation is complete,
not implementation. Keep the fixed full-TP1 first experiment/control and original
source pins. Sagiv's executable rules, priority/state-transition closure, exact
entry/cost/venue contracts and historical coverage remain dependencies. Separate
decision trajectories/action outcomes from terminal trade labels; policy/horizon
identity and causal temporal splits are mandatory. Shared simulation/observations
remain reusable. No new thresholds, live policy or production permission was approved.

Latest lifecycle-transition helper acceptance:
`agent-exchange/status/2026-09-14T050000Z-codex-lifecycle-transitions.md`.
The accepted component is a pinned, offline message/state-helper projection;
it is not the tracker resolver loop and does not establish feed, persistence,
delivery, economic outcome, replay, dataset, training or model readiness.
Read `TRACKER-LIFECYCLE-TRANSITIONS-SOURCE-USAGE.md` before consuming it.

Latest outcome-event/shelf-write prerequisite acceptance:
`agent-exchange/status/2026-09-14T060000Z-codex-lifecycle-outcome-shelf.md`.
These records are raw tracker facts and shelf preservation only, not a trade
outcome label, fill/P&L assertion, replay/dataset or model-ready artifact.

Latest live-evidence source prerequisite acceptance:
`agent-exchange/status/2026-09-14T065000Z-codex-lifecycle-live-evidence.md`.
It is a pinned offline projection of fresh quote and post-fill historical-tape
evidence; read `LIFECYCLE-LIVE-EVIDENCE-SOURCE-USAGE.md` before consuming it.
It has no bar acquisition/fallback, resolver/state-transition, economics,
replay, dataset, training, model or live-trading readiness claim.
Latest live-resolution evidence source prerequisite acceptance:
`agent-exchange/status/2026-09-14T074000Z-codex-lifecycle-live-resolution-evidence.md`.
It is a pinned offline projection of the resolver's fresh-price and
corrected-forming-bar evidence block. Read
`LIFECYCLE-LIVE-RESOLUTION-EVIDENCE-SOURCE-USAGE.md` before consuming it.
It preserves the source quote-age exception boundary but has no resolver state
mutation, outcome/economics, replay, dataset, training, model or readiness
claim.
Latest OPEN protection source prerequisite acceptance:
`agent-exchange/status/2026-09-14T141000Z-codex-lifecycle-open-protection.md`.
It is a pinned, offline conservative ambiguity projection over a caller-supplied
post-fill window. Read `LIFECYCLE-OPEN-PROTECTION-SOURCE-USAGE.md` before
consuming it. It resolves only an unordered protective/unhit-target touch;
ordinary target/progress/protection order, source acquisition, economics,
replay, datasets, training, models and live-trading readiness remain absent.
Latest OPEN post-fill evidence source prerequisite acceptance:
`agent-exchange/status/2026-09-14T111000Z-codex-lifecycle-open-postfill-evidence.md`.
It collects a causal caller-supplied post-fill price window only; read
`LIFECYCLE-OPEN-POSTFILL-EVIDENCE-SOURCE-USAGE.md` before consuming it. It is
not a resolver or outcome/economic/data/model component, and all readiness
flags remain false.
Latest OPEN ordinary-resolution source acceptance:
`agent-exchange/status/2026-09-14T171000Z-codex-lifecycle-open-ordinary-resolution.md`.
It is the pinned post-ambiguity progress/target/protective branch over
caller-supplied evidence. Read `LIFECYCLE-OPEN-ORDINARY-RESOLUTION-SOURCE-USAGE.md`
before consuming it. Minimum-success, zone return, full resolver composition,
persistence/delivery, economics, replay/dataset/training/model work and all
readiness claims remain excluded.
Latest OPEN minimum-success source acceptance:
`agent-exchange/status/2026-09-14T201000Z-codex-lifecycle-open-minimum-success.md`.
It is the pinned, pre-ambiguity supplied-evidence projection for the tracker
minimum message and raw fact. Read
`LIFECYCLE-OPEN-MINIMUM-SUCCESS-SOURCE-USAGE.md` before consuming it. Its raw
fact is not economic or model data; all resolver, persistence, replay and
readiness work remains separate.
Latest OPEN zone-return source acceptance:
`agent-exchange/status/2026-09-14T234000Z-codex-lifecycle-open-zone-return.md`.
It is a pinned, private supplied-spot advisory projection for the live
zone-return helper and caller boundary. Read
`LIFECYCLE-OPEN-ZONE-RETURN-USAGE.md` before consuming it. It retains actual
Revalidation offline-port effects; zone return directly only writes
`zone_return_at`. Full OPEN composition, persistence, replay/dataset/training,
model and live-trading readiness remain separate.
Latest live resolver source acceptance:
`agent-exchange/status/2026-09-15T004000Z-codex-lifecycle-live-resolver.md`.
It is the pinned offline PENDING/OPEN resolver kernel. Its two quote snapshots,
fallback and child order are verified; caller commit and all replay/dataset/
training/model readiness remain separate and false.
Latest closed-bar PENDING resolution acceptance:
`agent-exchange/status/2026-09-15T023000Z-codex-lifecycle-closed-pending-resolution.md`.
It is a pinned offline projection of only `check()`'s PENDING branch over
caller-supplied closed-bar evidence. Its expiry, directional missed-R,
open-slot/revalidation order, separate fill clock and conservative same-window
entry/stop outcome are verified. It ends before OPEN progression; acquisition,
persistence/delivery, replay/economics/dataset/training/model and all readiness
claims remain separate and false.
Latest closed-bar resolver acceptance:
`agent-exchange/status/2026-09-15T032000Z-codex-lifecycle-closed-resolver.md`.
It is the pinned offline `check()` lifecycle through ordinary OPEN closure over
one caller-supplied corrected 15m/three-day frame per eligible record. It
preserves pre-fill versus post-fill extrema, PENDING fall-through, closed-bar
minimum/protection/ordinary order and short direction fidelity. It has no
persistence, delivery, replay/economics/dataset/training/model readiness; all
readiness claims remain false.
Latest closed-bar causal replay Task 4 acceptance:
`agent-exchange/status/2026-09-15T070000Z-codex-closed-bar-replay-task4.md`.
Tasks 1-4 now provide a bounded, offline, supplied-evidence replay spine with
source-order audit, shared-clock/provider checkpoints, exact event-to-provider
bindings and a raw-payload-free ledger. Newly selected reversal plans remain
OBSERVE_ONLY; only supplied tracker state may advance through the closed
lifecycle. Read `docs/architecture/CAUSAL-REPLAY-USAGE.md` before consuming it.
Final bounded closed-bar replay acceptance:
`agent-exchange/status/2026-09-15T080000Z-codex-closed-bar-causal-replay.md`.
Tasks 1-5 are accepted after 278 focused tests, source-order verification and
an independent final review. This is still a bounded offline supplied-evidence
spine only: public replay/training readiness remains false by design, while
outer admission, other producers, economics, datasets, training and production
permissions remain separate work.
The approved baseline is the existing six-repository implementation, pinned by
commit. Reuse it rather than reconstructing behavior from HTML alone. Primary
objective: net economic performance; movement success/MAE/MFE are separate targets.
First economic simulation: original entry/stop, full exit at TP1, no optional
partials, scale-in or BE/trailing. Costs and time-exit details must be explicit
before economic labels are generated. Do not modify live alert behavior.
Source pins and resolved-trade economics now live in `trading_system/tree_spec/`.
Neither is a replay engine or permission to generate market labels. See
`docs/architecture/EXISTING-BASELINE-CONTRACTS-USAGE.md` for the offline interfaces.
An additive closed-bar EMA/cloud observation adapter is in
`trading_system/tree_replay/`; see `docs/architecture/ASOF-EMA-ADAPTER-USAGE.md`.
The default supports contiguous history and microsecond-exact timestamps only.
Opt-in supplied session schedules are documented in
`docs/architecture/SESSION-EMA-ADAPTER-USAGE.md`; whole-bar membership and every
expected seed-history bar are checked. The GC bridge is normal-hours research
only, not historical holiday/era evidence. Complete source partial-bar handling
and full replay are not certified. Existing calendar/data policies remain unchanged.
An offline level-reversal detection adapter now emits explicitly UNPRICED setups
from supplied as-of levels and closed bars. See
`docs/architecture/LEVEL-REVERSAL-ASOF-USAGE.md`. This covers only one detector,
not historical level-map construction, trade plans, admission, arbitration,
execution outcomes or dataset/training readiness. No live alert behavior changes.
An additive pricing wrapper now computes original source entry zones, stop bands,
targets, obstacles and refusals; see `docs/architecture/REVERSAL-PRICING-USAGE.md`.
Source pricing acceptance remains UNADMITTED, never a fill or outcome. Exact
producer symbols are required; GC is not aliased to OANDA spot. Repeated level
display names need distinct explicit level IDs and prices; detector adapter v2
distinguishes the changed evidence serialization from previous evaluation hashes.
The full tracker preserves outstanding B-I work; component acceptance does not
complete the full model plan. External admission/state, other producer paths and
the full outcome pipeline remain.
Daily-period aggregation is now additive under tree_replay/periods.py: explicit
period boundaries/calendar, closed lower bars only, separate price/publication
cutoffs and blocked output on missing expected history. See
`docs/architecture/DAILY-PERIOD-ASOF-USAGE.md`. No inferred broker day or open-only
tick support. Pure source range/rollover/back-day functions and their audit are
documented in `docs/architecture/RANGE-SOURCE-USAGE.md`; they do not constitute
the full historical map or validate arbitrary input frames. The exact GC versus
OANDA source variant remains a real-data question in the human inbox; synthetic
engineering can proceed without silently mapping instruments.
Supplied correction evidence is now assessed against explicit replay time in
tree_replay/corrections.py; see docs/architecture/CORRECTION-ASOF-USAGE.md.
The source shape predicate is audited with only a clock/signature specialization.
Missing/future/delayed/stale evidence is distinct from assessed-but-unverified
or proxy evidence. ASSESSED is not producer admission or feed certification.
No offsets are applied. Frame identity/provenance remain caller attestations.
Historical map inputs can now be reconstructed through frames.py and bound to
the complete original level-map graph through levelmap.py. Read
docs/architecture/HISTORICAL-FRAMES-USAGE.md and HISTORICAL-LEVELMAP-USAGE.md.
Daily boundaries/source labels and intraday origins/calendars are explicit;
higher frames use published closed-base prefixes, not final future OHLC.
Lazy original fetch order, asymmetric correction gates, source omissions and
stable repeated-name level IDs are retained. Snapshot observation/publication
equals decision time because session/shape state depends on that clock; actual
price timestamps remain in dependency traces. BUILT_UNADMITTED is not producer
admission, a fill or a label. No open-only/base-partial support or GC spot alias.
The graph audit checks full ordered source projections and inherited dependencies,
including independently pinned/ordered EMA dependencies. Runtime construction
does not itself run the source audit. Full outer admission/state/arbitration,
simulation, data coverage, dataset and model work remain open. Read the latest
exchange acceptance before assuming a pending implementation is accepted.
The pinned legacy replay hook emits source=replay, which does not qualify OANDA
broker shape; never silently relabel it as tv_daily. The full historical source
contract documents this and the hook's cursor/publication/calendar limitations.
The additive full internal reversal producer now joins real historical maps and
frames to original find/selection/pricing at actual T. See
docs/architecture/REVERSAL-PRODUCER-ASOF-USAGE.md and CLOSED-BASE-PREFIX-USAGE.md.
An older fresh confirmation can be selected; event time is not decision time.
Default newest-confirmation wrappers/guards remain unchanged. Opt-in prefix
mode floors price observations only; publication, freshness and source gates
retain actual T. Source-selected refusals are not replaced by older paying
events. Public tradeable/readiness remain false; no outcomes or fitting.
Task/final acceptance must be read from exchange status, not inferred from code.
Outer market-watch admission/tracker/episode state and other producers remain;
MARKET-WATCH-ADMISSION-SOURCE-INTAKE.md maps their pinned dependencies. Quality
shadow annotations must not become vetoes, PENDING must not become OPEN exposure,
and source advisory state must not silently become fixed-TP1 economic state.
The combined internal reversal-producer component is accepted in
agent-exchange/status/2026-09-09T122023Z-codex-reversal-producer.md.
All7source audits,1841integration and2213broad tests passed; legacy validators
excluded, latest78producer tests separately cover the final test-only refinement.
This does not close outer admission, other branches, simulation, dataset or model.
Admission dependencies are accepted; see
docs/superpowers/plans/2026-09-09-admission-dependencies.md and latest exchange status.
Private source matrix/quality/clocks/swing closure has93scoped passing tests/source
audit. New state.py stores supplied causal advisory memory with bounded coverage
and checkpoint validation; it does not generate tracker lifecycle transitions.
Task2 temporal and identity defects were fixed and independently re-reviewed.
Final acceptance: agent-exchange/status/2026-09-09T125556Z-codex-admission-dependencies.md.
677expanded integration tests and source audit passed. Test-root portability
remains a deferred Minor before another runner/CI; original worker RED unknown.
Full outer gate/record binding and source-generated lifecycle remain open. Source
VWAP NaN can produce short strength100; preserved baseline behavior, not a win
probability. Read ADMISSION-CALCULATIONS-USAGE.md and CAUSAL-ADMISSION-MEMORY-USAGE.md.
Next source closure is planned/under implementation in
docs/superpowers/plans/2026-09-09-tracker-admission-source.md and
docs/architecture/TRACKER-ADMISSION-SOURCE-CONTRACT.md. Independent acceptance
must precede causal binding; private offline ports do not prove whole-loop replay.
Full raw-log selection includes non-rejection bytes and intra-pass log appends;
never substitute the semantic rejection-only memory stream as byte-faithful history.
Tracker source closure is accepted in
agent-exchange/status/2026-09-09T132950Z-codex-tracker-admission-source.md.
Fresh129scoped tests/source audit passed, task and final reviews clean; prior428
integration cases overlap. Next binding must retain the actual selected Plan:
public producer evidence omits close/kind and is not a recordable source Plan.
Full watch state includes scalar cooldowns, object episodes and deletions; its
write boundaries differ from tracker save. Branch publication ordering differs.
Read all seven final-review132300Z requirements before causal binding. No full
replay, economic labels or model readiness is implied by this acceptance.
Selected-Plan handoff accepted134259Z-codex-reversal-handoff: private
_evaluate_reversal_asof returns original event/Plan plus detached evidence;
public find_reversal_asof remains unchanged, including hashes/false readiness.
208combined and24focused tests passed, task/final reviews clean. Selected
refusals remain refused; failed serialization retains no source objects.
Next execute2026-09-09-admission-frame-binding plan/spec. Original matrix uses
all delivered frame rows, no producer correction veto or closed-target filter.
LOOKBACK identifies requests, not delivered days; fresh TV/MT5 source returns
full loaded frame. Preserve actual supplied seed/dependency coverage separately.
Causal admission frames accepted154823Z-codex-admission-frames: exact six requests,
real original matrix/swing/tracker reads from available closed-base prefixes.
436combined tests and sourceaudit10 passed; task/final reviews clean. M1long-history
regression catches wrong requested-day trimming. Independent seeds are not full
historical feed evidence. Read ADMISSION-FRAME-BINDING-USAGE.md. State/save/locks,
quotes, full raw logs, caller ordering and lifecycle remain before full replay.
Tracker storage accepted160544Z-codex-tracker-storage: source load/save over causal
ordered text, absent/unknown/read failure distinct, reread and shrink/quarantine
guards preserved. Current309tests/sourceaudit2passed; task/fix/final reviews clean.
Creation effects explicitly replay-only; failed child remains traced despite
successful best-effort save. Read TRACKER-STORAGE-BINDING-USAGE.md. Snapshot is
one artifact handoff, NOT full checkpoint. Quotes/raw logs, exact lock/caller
order, full watch state and generated advisory lifecycle remain. Source intake
documents quote publication versus lp freshness and pre-producer resolver order.
Causal quote/watch IO accepted162759Z-codex-quote-watch-io: fresh269planned tests
and source audits4/7passed, task/final reviews clean. Full raw prefix and original
logger/session semantics retained; final reviewer also checked4,936 reader/tail
comparisons. Read CAUSAL-QUOTE-WATCH-IO-USAGE.md. Explicit artifact snapshot is
not full checkpoint. Lock/caller/watch state/generated lifecycle still remain;
next source policy plan2026-09-09-tracker-lock-source, no assumed wait duration.
Tracker lock source policy accepted163655Z-codex-tracker-lock-source:31runtime
and17audit tests,263combined fresh7.89s, sourceaudit4/7 and task/final reviewsPASS.
Read TRACKER-LOCK-SOURCE-USAGE.md. Original depth/waits/skip/stall/cleanup over
explicit ports; NOT OS locking or historical acquisition scheduling. Next caller
binding must distinguish frozen pass-anchor from operation clocks and separate
market-watch lock/state persistence. Full tree suite24845 reached terminalexit0:
2404passed347.81s on unchanged runtime; final acceptance addendum164109Z records
scope. This is tree_replay/tree_spec, not full-loop parity or model readiness.
No running tests/own reviewers remain. Full goal remains active.
Shared clock/context accepted170950Z-codex-admission-context after clean task/final
reviews; fresh362planned tests7.02s, four source audits and independent combined
boundary probes. Read CAUSAL-ADMISSION-CONTEXT-USAGE.md. Original consumers now
share operation time and ordered full-image publications; pass anchor stays fixed.
Source catches remain traced; recordTrue is not full quality approval or fill.
Prior2404broad tests predate this component. Watch storage is separately under
review in2026-09-09-watch-state-binding plan. Source intake now maps independent
claim verifier, bar-position geometry, movement proof and gate/outbox persistence.
Original caller/separate watch lock/mixed-time producer/generated lifecycle,
remaining branches and economics/dataset/model work remain. Do not infer OS lock
or whole-checkpoint fidelity. No context tests/reviewers remain running.
Watch storage accepted171410Z-codex-watch-storage:32runtime/18audit tests; final
174combined7.22s and task/final reviewsPASS. Read WATCH-STATE-BINDING-USAGE.md.
Original heterogeneous state/default JSON/two saves, no tracker shrink/atomic
policy; saved image separate from unsaved caller. Not full checkpoint/watchlock.
Broad tree suite78562 completed2529passed339.40s,exit0; no runtime/test edits
during run. Acceptance171410Zaddendum171652Z supersedes earlier live notes. Next
plan2026-09-09-bar-lifecycle-primitives and full source spec are written; read
both before tests/implementation. All own reviewers closed; full goal active.
No testprocess remains live. Fulltree tests are not fullrepo/legacyvalidators,
whole historical-loop parity, economic labels or training certification.
Bar-lifecycle primitives accepted173529Z-codex-lifecycle-primitives: original
fivefunction geometry, completevoice and explicit-clock DeskSuccess;74runtime/
31audit tests and independent task/final reviewsPASS. Main final105passed25.05s,
combined183passed38.89s, CLI VERIFIED3+inherited7. Read BAR-LIFECYCLE-PRIMITIVES-
USAGE.md; raw caller tape is not causal certification, movement is not economics.
Broad77054 completed2634passed352.79s exit0 on unchanged runtime/tests; postrun
hashesmatch. Not fullrepo/legacyvalidators or fullhistoricalreplay/model proof.
Independent verifier and stretch accepted205232Z-codex-verifier-stretch after
separate task/final spec/qualityPASS reviews. M1closed; erroredreview replaced
by completed204523Zreview, not waived.475combined78.87s and freshauditsVERIFIED,
hashesmatch. Curieclosed; no reviewers/tests live. Private supplied ports are
not historical certification. Fullcaller/lifecycle/effects remain. Read
INDEPENDENT-CLAIM-VERIFIER-USAGE and STRETCH-SOURCE-CONTRACT/USAGE. Source
prose differs from actual dependency: ADR14 and open+/-ADR/2, not ADR20/fullADR.
Shape20days is separate. Real original behavior retained; private ports and
NaN semantics are not causal/JSON feature certification.205232Z has current
hashes/process evidence. Next2026-09-09-ema-deep-reader plan/spec, runtime and
38cases andusage now exist with153combined passing; auditor/reviews remain. Preserve
source rawcomparison rounding; exactflat fixture uses128 after constant100 gave
EMA200100.0000000000001. Full EMA/deep/calendars/tree revalidation,
causal feeds, resolver/caller/otherbranches/economics/data/models remain open.
Complete EMA/deep reader accepted211034Z after task/final spec/qualityPASS and
M1closure.45runtime/58auditcases, fresh257combined15.27s/CLIverified/hashesmatch.
No reviewers/tests live. Read EMA-DEEP-READER-USAGE.md. Rawports are not causal
feeds or seam certification. Next2026-09-10-revalidation-source plan/spec now
has actual composed revalidation runtime and77focusedtests passing3.43s after
normalRED50. Prior360combined10.88s predates10test additions only. Usage exists;
Task1package/review and fullTask2auditor/reviews remain; not accepted.
Latest211455Zrevalidation status supersedes those testcounts: fresh370planned
tests passed5.54s on currentfiles; no code edits afterwards, no tests/agentslive.
Its tree_walk boundary is explicitly unbound, not a complete tree implementation.
Read newplan/spec/ledger before continuing. Fullcaller/effects/otherproducers,
economics/data/models/holdout/human gates stay required; no new labels/model.
Pending-plan revalidation accepted213925Z after both task and final spec/quality
reviewsPASS;539combined114.26s, freshsourceCLI VERIFIED/currenthashesmatch.
Read REVALIDATION-SOURCE-USAGE.md. No reviewers/tests live. Rawports and unbound
tree_walk are not wholecausalreplay; outcomes/data/models remain. Main completed
full1496line tree+all dependency readers intake in FULL-TREE-WALK-SOURCE-INTAKE.md.
Next2026-09-10-tree-tr-memory plan/spec:25normalRED then181combinedGREEN5.94s;
runtime andtests exist, usage/taskreview/auditor/finalreview still outstanding.
Preserve source[-1]/[-2] conventions, news15minveto versus30minshadow, WM/liquidity
different swing priorities and repeatedfeeds. No newhumanstrategydecision.
Vector memory/pivots accepted215229Z after task/final spec/qualityPASS; M1closed,
fresh224combined12.90s and postreviewCLI VERIFIED/hashesmatch. Read TREE-TR-MEMORY-
USAGE.md. No componenttests/agentslive. Next2026-09-10-tree-pattern-readers has
actualfourreaders/66runtimecases and182combinedGREEN; auditor/reviews pending.
Rawports notcausalcertification; fulltree/caller/economics/dataset/models remain.
Patternreaders accepted220345Z after task/final spec/qualityPASS andM1closure;
282combined29.08s, postreviewsourceCLI VERIFIED/currenthashesmatch. Read TREE-
PATTERN-READERS-USAGE.md. Actualfourreaders notfullcausalfeed/treecertification.
Next2026-09-10-options-wall-reader has actualrawJSON/CSV reader and38runtime/
38auditcases;143combinedGREEN8.35s before1M1testaddition. Task1reviewapproved;
Task2/finalreviews pending. Fullwalk/caller/economics/dataset/models remain.
Optionsreader accepted220947Z after task/final spec/qualityPASS/M1closure;
current144combined8.96s, postreviewCLI VERIFIED/hashesmatch. Read OPTIONS-WALL-
READER-USAGE.md. No reviewerslive. Broadtree suite40048 stillRUNNING atlast
22:09:30UTC; no passclaim. Preserve runtime/tests untilterminal. Next2026-09-10-
levelmap-operation-clock plan/spec/ledger written, no implementationyet. Actual
broker-shape predicate mustreadclockonlyonsplice; sessionclockonlyafter5mfetch/
gates. Existingfixed-Tpublicmap unchanged. Fulltree/caller/economics/data/models
remain; usercontinuegoal active, no humanblocker to syntheticengineering.
Latest2026-09-10continuation supersedes broad40048RUNNING:3312passed576.22s,
exit0; scope tree_replay/tree_spec only. Operationclockmap Task1nowimplemented
after48normalRED; verification/sourceaudit/task/finalreview pending. Full
master active; syntheticengineering unblocked; no new economicdataset/model.
Operationclockmap accepted190902Z after task/final spec/qualityPASS.344combined
188.03s, sourceCLI VERIFIED/actualinheritedgraph, reviewedhashesmatch. I1source
duplication disposition disclosed/accepted; keep bothprojections audited. Read
LEVELMAP-OPERATION-CLOCK-USAGE.md. Next2026-09-10-tree-walk-reader spec/plan/ledger
written after mainfull1496line source reread; no tree implementationyet. Original
house/strict, actualreaders, news15min/operationclocks required; no newpolicy.
Complete treewalk/FirstVector/bothbuilders accepted193848Z-codex-tree-walk after
task/finalspecqualityPASS, I1/M1testcoverageandmissingpin-auditerrorfixed/reviewed.
Current293combined342.70s and274Task1combined8.64s passed, freshfullsourceCLI and
reviewedhashesmatch. Read TREE-WALK-READER-USAGE.md. No own tests/reviewers live.
Full12sourcevisitedstages overrawports isnot22HTMLfamily/causalfeed/fullcaller/
admission/fill/modelcertification. Next2026-09-10-tree-revalidation-binding spec/
plan/ledgerwritten: actualMatrixReader andTreeReader mustsupplyRevalidation, not
providerfinalverdicts. Sourcependingage/default-house/operationclocks unchanged.
Fullgoalactive; no neweconomicdataset/model, syntheticengineeringunblocked.
Actualtree/matrix pendingbinding accepted200014Z after task/final specqualityPASS,
no findings.250plannedcombined49.26s/240Task1combined19.87s and freshsourceCLI
VERIFIED/reviewedhashesmatch. Read TREE-REVALIDATION-BINDING-USAGE.md. Original
twohour/house/opposition/verified/operationclock behavior retained; rawports not
causalfeed/fullcaller/fill/modelproof. No own tests/reviewerslive. Next source
intake LIFECYCLE-CLAIM-PERSISTENCE-INTAKE.md and2026-09-10-lifecycle-identity-source
spec/plan/ledger written, implementationnotstarted. Actualreceipts/thread/cache
then gate/park/outbox/resolver/caller/causalproviders and E-I remain. Fullgoalactive.
Lifecycle identity/receipts/thread accepted201630Z after task/finalspecqualityPASS
and I1stop-disambiguation proofclosure.208combined16.50s/54postreview14.11s,
freshsourceCLI VERIFIED/reviewedhashesmatch. Read LIFECYCLE-IDENTITY-SOURCE-USAGE.
No own tests/reviewerslive. Actualsource cache/matcher/geometry/context are not
causalartifact/delivery/economicproof. Next2026-09-10-outbox-journal-source spec/
plan/ledgerwritten; runtimeabsent. Then gate/park/atomicstore/resolver/caller and
causalproviders/fullmasterE-I remain. No neweconomicdataset/model; goalACTIVE.
Outbox journal accepted2026-09-13T233500Z after task/final spec-quality review
and documentation-only M1 closure. Fresh140combined18.92s and retained-source
CLI VERIFIED; full inherited identity/tracker-admission graph remains false for
replay/training readiness. Read OUTBOX-JOURNAL-SOURCE-USAGE. This is offline
journal state, not delivery/fill/economic proof. Next plan/spec:
2026-09-13-lifecycle-gate-park-source and LIFECYCLE-GATE-PARK-SOURCE-CONTRACT;
actual gate/parking/retry, then caller/resolver/causal providers and masterE-I.
Lifecycle gate/park/retry accepted2026-09-14T024000Z after task/audit/final
review chain and malformed-child-report M1 closure. Fresh162runtime and28source
audit/mutation tests pass; retained-source CLI VERIFIED with real verifier,
journal and identity children, all readiness false. Read LIFECYCLE-GATE-PARK-
SOURCE-USAGE and TRACKER-LIFECYCLE-CALLER-SOURCE-INTAKE. Source preserves the
matched-trade to_group parking field even when it differs from message routing.
Next is caller changed-only gate/persist/save binding with causal artifacts;
never infer full replay/delivery/fill/economics/data/model readiness.
Tracker lifecycle caller seam accepted2026-09-14T041000Z after task/fix/final
reviews. Fresh70runtime/source/child tests passed in74.94s and retained-source
CLI VERIFIED. Closed and live callers now preserve changed-only
resolve->gate/persist->save; live uses the source-owned shared reentrant lock.
Read TRACKER-LIFECYCLE-CALLER-SOURCE-USAGE. This is a seam only: source mutation
bodies, parked replay context, scheduling, delivery/fill/economics/data/model
remain open and readiness stays false.
Check the latest baseline-contracts/tree-replay status under `agent-exchange/status/`
for implemented scope, verification and next steps. This memory is local project
documentation, not production-data, promotion, deployment or live-trading approval.

This repository uses `agent-exchange/` as the shared coordination directory for
Codex, Claude Code, Groq, and human operators.

## Mandatory Startup Check

Every agent working in this repository must read:

1. `AGENTS.md`
2. `agent-exchange/README.md`
3. `agent-exchange/protocol.md`

Then the agent must inspect its own inbox before starting new work:

- Codex: `agent-exchange/inbox/codex/`
- Claude Code: `agent-exchange/inbox/claude-code/`
- Groq: `agent-exchange/inbox/groq/`
- Human-facing requests: `agent-exchange/inbox/human/`

## Operating Model

- Codex owns architecture, phase sequencing, task routing, acceptance decisions,
  commits, pushes, and PR updates.
- Claude Code implements tasks only from scoped task contracts.
- Groq reviews, generates scenarios, finds contradictions, and summarizes
  research outputs.
- Humans approve production data, raw-data retention, model promotion, live
  trading, broker execution, capital allocation, and deployment.

## Exchange Rules

- Use one markdown file per request, review, status note, or decision.
- Use `agent-exchange/templates/request.md` for task handoffs.
- Use `agent-exchange/templates/result.md` for implementation/status outputs.
- Use `agent-exchange/templates/review.md` for review-only outputs.
- Do not delete or mutate inbox files unless explicitly asked.
- Record outcomes in `agent-exchange/status/`, `agent-exchange/reviews/`,
  `agent-exchange/decisions/`, or `agent-exchange/archive/`.
- Never put secrets, API keys, broker credentials, private account data, raw
  market-data payloads, or large generated artifacts in `agent-exchange/`.

## Codex Result Intake

When Codex is waiting for Claude Code, Groq, or a human, run:

`python tools/watch_agent_exchange.py`

For a current snapshot, run:

`python tools/watch_agent_exchange.py --once`

When a new or modified result appears, Codex must read the result file, read
the original request referenced by that result, inspect `git status --short`
and `git diff`, rerun applicable verification commands, and then record an
acceptance, revision request, or human-blocked status under
`agent-exchange/status/`.

## Approval Boundary

An inbox message is not sufficient approval for:

- production data vendor approval
- raw-data retention
- model promotion
- live trading
- broker execution
- capital allocation
- deployment

Those actions require explicit human approval with approver, timestamp, scope,
decision, and evidence recorded in `agent-exchange/decisions/`.
