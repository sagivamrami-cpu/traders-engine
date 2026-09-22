# Task1 fix1 scoped diff
No commits; compares actual files against the exact contents seen by Descartes.


diff --git a/trading_system/tree_replay/calendar.py b/trading_system/tree_replay/calendar.py
--- a/trading_system/tree_replay/calendar.py
+++ b/trading_system/tree_replay/calendar.py
@@ -107,14 +107,14 @@
-        "early_closes": (),
-    }
-    for field, expected in template.items():
-        actual = getattr(calendar, field)
-        if type(actual) is not type(expected) or actual != expected:
-            raise ValueError(f"unsupported research calendar field: {field}")
-        # Equality hides float weekday values and the time.fold attribute.
-        if isinstance(actual, time) and actual.fold != expected.fold:
-            raise ValueError(f"unsupported research calendar field: {field}")
-        if field == "closed_weekdays" and any(type(day) is not int for day in actual):
-            raise ValueError("closed_weekdays must contain exact integers")
-    _validate_text(calendar.version, "version")
-
-    # Validate caller evidence before resolving any minutes or decorating source.
+        "early_closes": (),
+    }
+    for field, expected in template.items():
+        actual = getattr(calendar, field)
+        if type(actual) is not type(expected) or actual != expected:
+            raise ValueError(f"unsupported research calendar field: {field}")
+        # Equality hides float weekdays, time.fold and date-dependent tzinfo.
+        if isinstance(actual, time) and (actual.tzinfo is not None or actual.fold != expected.fold):
+            raise ValueError(f"unsupported research calendar field: {field}")
+        if field == "closed_weekdays" and any(type(day) is not int for day in actual):
+            raise ValueError("closed_weekdays must contain exact integers")
+    _validate_text(calendar.version, "version")
+
+    # Validate caller evidence before resolving any minutes or decorating source.

diff --git a/tests/tree_replay/test_calendar.py b/tests/tree_replay/test_calendar.py
--- a/tests/tree_replay/test_calendar.py
+++ b/tests/tree_replay/test_calendar.py
@@ -317,12 +317,22 @@
-])
-def test_bridge_rejects_template_values_hidden_by_python_equality(research_calendar, changes):
-    with pytest.raises(ValueError):
-        bridge(replace(research_calendar, **changes))
-
-
-def test_bridge_hash_covers_every_calendar_field_with_literal_serialization(research_calendar):
-    result = bridge(replace(research_calendar, version="synthetic-v1"))
-    # Independent literal payload: dropping a field from provenance must fail.
-    serialized = (
-        '{"calendar_id":"cme-globex-metals-research-v1","closed_weekdays":[5],'
-        '"daily_break_end":"17:00:00","daily_break_start":"16:00:00",'
+])
+def test_bridge_rejects_template_values_hidden_by_python_equality(research_calendar, changes):
+    with pytest.raises(ValueError):
+        bridge(replace(research_calendar, **changes))
+
+
+@pytest.mark.parametrize("field,hour", [
+    ("regular_open", 17), ("regular_close", 16),
+    ("daily_break_start", 16), ("daily_break_end", 17),
+])
+def test_bridge_rejects_timezone_bearing_template_times(research_calendar, field, hour):
+    value = time(hour, tzinfo=ZoneInfo("America/Chicago"))
+    with pytest.raises(ValueError, match=field):
+        bridge(replace(research_calendar, **{field: value}))
+
+
+def test_bridge_hash_covers_every_calendar_field_with_literal_serialization(research_calendar):
+    result = bridge(replace(research_calendar, version="synthetic-v1"))
+    # Independent literal payload: dropping a field from provenance must fail.
+    serialized = (
+        '{"calendar_id":"cme-globex-metals-research-v1","closed_weekdays":[5],'
+        '"daily_break_end":"17:00:00","daily_break_start":"16:00:00",'
