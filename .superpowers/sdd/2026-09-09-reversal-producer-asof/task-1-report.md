# Task 1 report — DONE, awaiting independent review

Scope: three existing runtime modules gain opt-in closed_base_prefix=False;
test_closed_prefix.py and CLOSED-BASE-PREFIX-USAGE.md are additive.
No original test expectations changed, no commits or other worker files edited.

TDD evidence recorded before compaction: initial missing-interface RED 55 failed,
1 passed, 1 skipped; removed irrelevant parameter combination; clean RED via
python -m pytest tests/tree_replay/test_closed_prefix.py -q --tb=no -rN:
55 failed, 1 passed in0.73s (exit1). First implementation GREEN56passed1.16s.
Six supplemental characterization cases were then added, without pretending
they failed before implementation. Fresh controller verification after recovery:

- python -m pytest tests/tree_replay/test_closed_prefix.py tests/tree_replay/test_periods.py tests/tree_replay/test_frames.py tests/tree_replay/test_levelmap.py -q --tb=short
  exit0,213passed6.54s, no pytest warnings.
- python -m pytest tests/tree_replay/test_closed_prefix.py -q --tb=short
  exit0,62passed1.12s, no pytest warnings.

Pre-change default fixture hashes retained and asserted by tests:
period48ffeb5bce9baa912b2d5080ba9bd9b65a11d67758d646a31c0c0ea7a811829a;
framefa221a0265d0ef2c5acc1bcb5cbf300cd98a2467a84ebb196780ff9fe471f0be;
mapa64b1f01d24b8ffd88ad63daef2b3b374a6ec1436781bbf25db045b49906ba6f.
Golden hashes protect existing API evidence compatibility; new price expectations
are literal, not runtime-generated oracles. Beforeimages are in this scratch.

Self-review: prefix floors only price observation; actual decision time remains
publication/freshness/metadata/calendar/period-ownership/source-session clock.
Empty current periods, missing history, unavailable publications remain blocked;
explicit closures and23/25h periods retain their supplied meanings. Map trace
retains cutoff, actual source clock and snapshot version. Default fields/hashes
and three-argument private source constructor remain compatible. False readiness,
unsupported open-only/base-partial observations and no feed certification stated.

No open findings or domain rulings. Git diff reports existing LF/CRLF conversion
warnings, not test/runtime warnings. No changes made to line-ending configuration.
Task3 and full pipeline remain unimplemented; this is only Task1 acceptance input.
