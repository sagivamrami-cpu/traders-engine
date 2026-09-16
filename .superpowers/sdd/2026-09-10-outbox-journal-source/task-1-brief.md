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

- [ ] Read selected outbox functions and setup, full spec/intake, accepted
  lifecycle identity interface. Independently record exact signatures/counts.
- [ ] Write lazy import plus raw in-memory sink fixture. No physical files,
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
- [ ] Add literal cases for all nine spec behavioral groups, including actual
  context clock order, full row/merge/deduplication boundaries, prior sent flags,
  all born cases, failure/release and explicit offline refusal. Capture source
  stderr with capsys and assert it; no warning suppression.
- [ ] Run `python -B -m pytest tests/tree_replay/test_outbox_journal.py -q --tb=short -p no:cacheprovider`; verify normal missingmodule RED.
- [ ] Inertly extract original selected functions and adapt exact spec ports.
  Constructor body:
  ```python
  def __init__(self, source):
      self.source = source
      self.threads = LifecycleIdentity(source)
      self._BORN = {}
  ```
  Keep entire selected functions, method/source order and contextmanager.
- [ ] GREEN `python -B -m pytest tests/tree_replay/test_outbox_journal.py tests/tree_replay/test_lifecycle_identity.py -q --tb=short -p no:cacheprovider`.
  Document ports/scope, exact terminal evidence/hashes and full diff; request
  independent task spec/quality review. Resolve findings before acceptance.


