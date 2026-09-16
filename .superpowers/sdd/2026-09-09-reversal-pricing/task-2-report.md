# Task 2 report

Implemented pricing.py, test_pricing.py and explicit optional level IDs in
levels.py; bumped reversal adapter v1 -> v2 for evidence serialization change.
Task requirements: Task 2 in docs/superpowers/plans/2026-09-09-reversal-pricing.md.
Source dependencies are Task1, not independently reimplemented.

RED: initial 24 tests failed missing pricing module. GREEN:24 passed.
Identity amendment RED:8 failed /24 passed (unsupported level_id).
GREEN: pricing + previous reversal tests 123 passed in1.77s.
Fresh controller verification: pricing_source + pricing + reversal 197 passed
in3.66s, exit0. Pricing source CLI: subset_verified true, blockers empty;
ready_for_replay and ready_for_training false, exit0.

Recomputes detection from trusted bars, preserving candidate_id and source event
identity. Uses original source stop bands, zone, ATR, obstacle ladder and refusal.
Supported identities are exact producer symbols only. GC not silently aliased.
No admission, fill, outcome or label generation; tradeable false and trade_plan
None persist even when source_tradeable true. Availability includes all bars,
levels and supplied calendar. Generator input materialized once. Future suffix
not used. Missing pricing TP fields NOT_APPLICABLE, not numeric zero.

Ruling recorded in progress.md: source levelmap emits duplicate Q-QUARTER display
names at different prices. Require distinct explicit level_id for repeated names,
keep duplicate ID or same name/price rejected. If this identity policy is wrong,
historical adapters and stored evidence keys require migration. Version bump
distinguishes previous hashes; numerical detector logic unchanged.

Documentation remains Task3. No commits, live effects, raw data, models or source
checkout execution. None of this accepts a full replay or production deployment.
