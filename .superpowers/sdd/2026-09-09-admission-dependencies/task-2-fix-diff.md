# Task2 review fix round1
No commits. Compare frozen files reviewed at125000Z to current runtime/tests/docs.
warning: in the working copy of '.superpowers/sdd/2026-09-09-admission-dependencies/before-review-state.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'trading_system/tree_replay/state.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/.superpowers/sdd/2026-09-09-admission-dependencies/before-review-state.py b/trading_system/tree_replay/state.py
index ca22943..391423e 100644
--- a/.superpowers/sdd/2026-09-09-admission-dependencies/before-review-state.py
+++ b/trading_system/tree_replay/state.py
@@ -57,36 +57,41 @@ def _payload(text, stream, observed_at):
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
-    observed_epoch = (Decimal(elapsed.days * 86400 + elapsed.seconds)
-                      + Decimal(elapsed.microseconds) / 1_000_000)
+    elapsed_us = (elapsed.days * 86400 + elapsed.seconds) * 1_000_000 + elapsed.microseconds
+    # Decimal string construction is exact regardless of caller precision;
+    # Decimal division/addition would round under an ambient low-precision context.
+    observed_epoch = Decimal(f'{elapsed_us}e-6')
     time_fields = ('ts', 'resolved_ts') if stream == 'tracker' else ('ts',)
     # Compare the JSON decimal, not binary float expansion. An ordinary source
     # timestamp ending .123456 otherwise expands just past that microsecond.
     # Parsing original text also prevents finer future fractions being rounded
     # down by json.loads before this causal check.
     epoch_values = json.loads(text, parse_float=Decimal)
+    stored_epochs = json.loads(normalized, parse_float=Decimal)
     for name in time_fields:
         if name not in result:
             continue
         value = result[name]
         if type(value) not in (int, float) or (type(value) is float and not isfinite(value)):
             raise ValueError(f'payload {name} must be a finite numeric epoch')
         if Decimal(epoch_values[name]) > observed_epoch:
             raise ValueError(f'payload {name} cannot exceed observed_at')
+        if Decimal(stored_epochs[name]) != Decimal(epoch_values[name]):
+            raise ValueError(f'payload {name} loses precision during JSON normalization')
     return normalized
 
 
 @dataclass(frozen=True, kw_only=True)
 class MemoryEvent:
     """One fully observed source-row replacement or append-only rejection."""
 
     event_id: str
     sequence: int
     stream: str

warning: in the working copy of '.superpowers/sdd/2026-09-09-admission-dependencies/before-review-test_state.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/tree_replay/test_state.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/.superpowers/sdd/2026-09-09-admission-dependencies/before-review-test_state.py b/tests/tree_replay/test_state.py
index 1dbd7c3..5e39a5a 100644
--- a/.superpowers/sdd/2026-09-09-admission-dependencies/before-review-test_state.py
+++ b/tests/tree_replay/test_state.py
@@ -1,14 +1,15 @@
 """Synthetic evidence-store tests: publication order, not economic simulation."""
 
 from dataclasses import FrozenInstanceError, replace
 from datetime import datetime, timedelta, timezone
+from decimal import localcontext
 import importlib
 import importlib.util
 import hashlib
 import json
 
 import pandas as pd
 import pytest
 
 
 T = datetime(2026, 9, 7, 10, tzinfo=timezone.utc)
@@ -131,22 +132,23 @@ def test_invalid_event_contract_is_rejected(field, value):
 @pytest.mark.parametrize('field,value', [('ts', '123'), ('ts', True),
     ('ts', None), ('resolved_ts', '123'), ('resolved_ts', True)])
 def test_source_timestamp_fields_must_be_real_finite_epochs(field, value):
     with pytest.raises(ValueError):
         event(payload_json=json.dumps({field: value}))
 
 
 @pytest.mark.parametrize('stream,field', [('tracker', 'ts'), ('tracker', 'resolved_ts'),
     ('episode', 'ts'), ('rejection', 'ts')])
 def test_source_payload_cannot_smuggle_a_future_resolution(stream, field):
-    with pytest.raises(ValueError):
-        event(stream=stream, payload_json=json.dumps({field: (T + HOUR).timestamp()}))
+    with pytest.raises(ValueError, match='cannot exceed observed_at'):
+        event(stream=stream, key='e1' if stream == 'rejection' else 'trade1',
+              payload_json=json.dumps({field: (T + HOUR).timestamp()}))
 
 
 def test_rejection_key_must_be_its_append_only_event_id():
     with pytest.raises(ValueError):
         event(stream='rejection', key='shared')
 
 
 @pytest.mark.parametrize('events', ['list', 'duplicate_id', 'duplicate_sequence', 'reversed',
     'reversed_publication', 'before_start', 'beyond_coverage', 'untyped'])
 def test_journal_rejects_corrupt_order_or_coverage_instead_of_sorting(events):
@@ -263,10 +265,47 @@ def test_restore_validates_structure_even_when_checksum_is_recomputed(mutation):
         row['available_at'] = (T + HOUR + US).isoformat()
     elif mutation == 'wrong_origin':
         c['journal']['origin'] = 'economic_tp1'
     else:
         c['journal']['events'] = {}
     unsigned = {key: c[key] for key in ('schema', 'journal')}
     c['checksum'] = hashlib.sha256(json.dumps(unsigned, sort_keys=True,
         separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()
     with pytest.raises(ValueError):
         api().restore_memory(c)
+
+
+@pytest.mark.parametrize('precision', [1, 6, 10, 16, 28, 50])
+def test_causal_epoch_boundary_does_not_depend_on_ambient_decimal_precision(precision):
+    t = T.replace(microsecond=900000)
+    with localcontext() as ctx:
+        ctx.prec = precision
+        with pytest.raises(ValueError, match='cannot exceed observed_at'):
+            event(observed_at=t, available_at=t, payload_json='{"ts":1788775200.95}')
+        e = event(observed_at=t, available_at=t, payload_json='{"ts":1788775200.9}')
+        assert e.payload_json == '{"ts":1788775200.9}'
+
+
+def test_rejection_valid_timestamp_reaches_projection():
+    e = event(stream='rejection', key='e1', payload_json='{"ts":1788775200}')
+    assert api().memory_asof(journal((e,)), T)['rejection_events'] == [{'ts': 1788775200}]
+
+
+def test_epoch_that_loses_precision_in_json_normalization_is_rejected_at_ingestion():
+    t = datetime(2255, 1, 1, microsecond=1, tzinfo=timezone.utc)
+    with pytest.raises(ValueError, match='loses precision'):
+        event(observed_at=t, available_at=t, payload_json='{"ts":8993721600.000001}')
+
+
+@pytest.mark.parametrize('precision', [1, 10, 28])
+@pytest.mark.parametrize('t,payload', [
+    (datetime(2255, 1, 1, microsecond=2, tzinfo=timezone.utc), '{"ts":8993721600.000002}'),
+    (datetime(1969, 12, 31, 23, 59, 59, 900000, tzinfo=timezone.utc), '{"ts":-0.1}'),
+])
+def test_representable_epochs_roundtrip_without_numeric_context_dependence(precision, t, payload):
+    with localcontext() as ctx:
+        ctx.prec = precision
+        e = event(observed_at=t, available_at=t, payload_json=payload)
+        j = journal((e,), start_at=t, covered_through=t)
+        restored = api().restore_memory(api().checkpoint_memory(j))
+        assert restored == j
+        assert api().memory_asof(restored, t) == api().memory_asof(j, t)

warning: in the working copy of '.superpowers/sdd/2026-09-09-admission-dependencies/before-review-CAUSAL-ADMISSION-MEMORY-USAGE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/architecture/CAUSAL-ADMISSION-MEMORY-USAGE.md', LF will be replaced by CRLF the next time Git touches it
diff --git a/.superpowers/sdd/2026-09-09-admission-dependencies/before-review-CAUSAL-ADMISSION-MEMORY-USAGE.md b/docs/architecture/CAUSAL-ADMISSION-MEMORY-USAGE.md
index a69ad85..6e572ca 100644
--- a/.superpowers/sdd/2026-09-09-admission-dependencies/before-review-CAUSAL-ADMISSION-MEMORY-USAGE.md
+++ b/docs/architecture/CAUSAL-ADMISSION-MEMORY-USAGE.md
@@ -34,20 +34,25 @@ assert restored == journal
   state. Queries outside coverage return UNAVAILABLE with null state outputs.
 - Event sequence is globally unique/increasing and publication time is
   nondecreasing. Equal-time sequence order is preserved. Wrong ordering is
   rejected, never silently sorted. Event IDs are globally unique.
 - Tracker/episode events replace the entire row at `key`. Rejections append,
   with `key == event_id`. No deletion command or implicit row merge exists.
 - Both timestamps must be aware, microsecond-exact and observed <= available.
   Numeric source `ts` and tracker `resolved_ts` cannot exceed event observation.
   Epoch comparison uses original JSON decimal tokens, avoiding binary-float
   artifacts and rejecting finer future fractions before JSON float rounding.
+  The observation boundary is independent of ambient Decimal precision. If a
+  source epoch cannot retain its decimal value through JSON float normalization,
+  ingestion rejects it explicitly rather than producing an unrestorable journal
+  or silently moving its time. This can exclude extremely precise epoch payloads;
+  it does not infer or round a substitute timestamp.
 - Payload is immutable canonical JSON text. Duplicate keys, nonfinite numbers,
   non-object roots and non-UTF8 text are rejected. Missing source fields remain
   visible for downstream source gates to handle; malformed rows are not dropped.
 - Actual T selects published events only. `event_trace` carries their times,
   sequence, keys and payload hashes. Later publications do not alter an earlier
   snapshot or its hash. Output objects are detached from journal memory.
 - Checkpoints contain full history with schema/checksum. Restore checks fields,
   canonical timestamps/payload, ordering and coverage even with a recomputed
   checksum. This checksum detects corruption, not malicious forgery or false
   provenance. It is not cryptographic authentication of market history.


