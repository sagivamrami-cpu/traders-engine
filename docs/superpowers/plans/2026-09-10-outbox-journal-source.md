# Outbox journal source implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Track checkboxes.

**Goal:** Original enqueue/deduplication/resolve journal over explicit offline effects.
**Architecture:** Actual source journal composes the accepted LifecycleIdentity reader; raw effect ports preserve ordering and process-local born memory. Independent inert auditor proves complete source projection and real inherited identity graph.
**Tech Stack:** Python, JSONL, context managers, pytest, AST.
**Spec:** docs/architecture/OUTBOX-JOURNAL-SOURCE-CONTRACT.md

## Global constraints

- Existing approved feature checkout, main inline critical path with independent
  review sidecars. No commits/push/cleanup, original source imports or live IO.
- chart-desk68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9;
  chartdesk/outbox.py blob1cf608f81e30c82ddd83b211a0ca743133699e45.
- All exact interfaces/substitutions in spec bind both tasks. Preserve original
  behavior; never infer timestamps, economic results or final queue/identity.
- Logical STORE is chart-desk/out/outbox.jsonl. Supplied raw sinks must be offline.
- Original selected signatures/decorators and bodies must be read before edits;
  actual source projection, not rewriting from test outcomes.

## Task1: Original journal and real thread composition

Create trading_system/tree_replay/_vendor/outbox_journal.py,
tests/tree_replay/test_outbox_journal.py and
docs/architecture/OUTBOX-JOURNAL-SOURCE-USAGE.md.

- [x] Read selected outbox functions and setup, full spec/intake, accepted
  lifecycle identity interface. Independently record exact signatures/counts.
- [x] Write lazy import plus raw in-memory sink fixture. No physical files,
  clocks or locks in defaults. Its journal writer must append actual serialized
  text and raw reader must return those bytes for a second enqueue.
  First required behavior:
  ```python
  name = 'trading_system.tree_replay._vendor.outbox_journal'
  assert importlib.util.find_spec(name) is not None, 'outbox journal missing'
  journal = importlib.import_module(name).OutboxJournal(raw)
  first = journal.enqueue('notice', False)
  second = journal.enqueue('notice', False)
  assert first == second == 'ae73500e104a8e28'
  assert len(raw.text.splitlines()) == 1
  assert journal.pending()[0]['attempts'] == 0
  ```
  This literal ID was independently calculated from `2|notice` using hashlib,
  with raw clock120.0, not from _eid or another runtime helper.
- [x] Add literal cases for all nine spec behavioral groups, including actual
  context clock order, full row/merge/deduplication boundaries, prior sent flags,
  all born cases, failure/release and explicit offline refusal. Capture source
  stderr with capsys and assert it; no warning suppression.
- [x] Run `python -B -m pytest tests/tree_replay/test_outbox_journal.py -q --tb=short -p no:cacheprovider`; verify normal missingmodule RED.
- [x] Inertly extract original selected functions and adapt exact spec ports.
  Constructor body:
  ```python
  def __init__(self, source):
      self.source = source
      self.threads = LifecycleIdentity(source)
      self._BORN = {}
  ```
  Keep entire selected functions, method/source order and contextmanager.
- [x] GREEN `python -B -m pytest tests/tree_replay/test_outbox_journal.py tests/tree_replay/test_lifecycle_identity.py -q --tb=short -p no:cacheprovider`.
  Document ports/scope, exact terminal evidence/hashes and full diff; request
  independent task spec/quality review. Resolve findings before acceptance.

## Task2: Complete source proof and final acceptance

Create trading_system/tree_spec/outbox_journal_source.py,
tools/check_outbox_journal_source_parity.py,
tests/tree_spec/test_outbox_journal_source.py.

- [x] Missing-auditor RED and real actual inherited graph test:
  ```python
  r = api().audit_outbox_journal_source(SOURCE)
  assert r['source_subset_verified'] and r['blockers'] == []
  assert r['dependencies']['lifecycle_identity']['source_subset_verified']
  assert not r['ready_for_replay'] and not r['ready_for_training']
  ```
  Candidate mutations: constructor sharing, early clock, context provider,
  _BORN pop order,600 boundary, terminal resurrection, attempt reset, lock
  exclusion/release/timeout, guard removal, read/write dispatch/serialization.
  Source mutations: pins/blob/signatures/decorators/order/duplicate/missing,
  exact substitution counts. Actual inherited identity drift must block.
- [x] RED `python -B -m pytest tests/tree_spec/test_outbox_journal_source.py -q --tb=short -p no:cacheprovider` before auditor/CLI code.
- [x] Implement independent literal source projection and full runtime AST
  comparison with actual audit_lifecycle_identity_source dependency. Source
  read/parse, missing pin, child falseempty/trueblocked/errors must yield blockers.
  No execution/compilation/import of retained modules or replay runtime.
- [x] CLI argparse required --source-root, JSON report, exit0 verified/2 blocked;
  test unrelated cwd, actual missingpin and inert guard subprocess.
- [x] GREEN `python -B -m pytest tests/tree_replay/test_outbox_journal.py tests/tree_spec/test_outbox_journal_source.py tests/tree_replay/test_lifecycle_identity.py -q --tb=short -p no:cacheprovider`.
  Run `python -B tools/check_outbox_journal_source_parity.py --source-root C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149`.
- [x] Independent task and full combined reviews, scoped fixes, fresh verification,
  hashes and acceptance. Update usage/master/tracker/AGENTS; keep whole master
  active. Next gate/park/atomic-store/resolver/caller/causal provider work remains.
