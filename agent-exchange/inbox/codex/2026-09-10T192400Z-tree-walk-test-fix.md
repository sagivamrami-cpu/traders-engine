# Agent Exchange Request

Target: Codex scoped test-fix implementer
Sender: Codex controller
Created at: 2026-09-10 19:24 UTC
Status: ACTIONABLE

Objective: Task1 fix round1 — close I1 and M1 from agent-exchange/reviews/2026-09-10T191914Z-tree-walk-task-review.md. Read that review fully, the Task1 brief/report in .superpowers/sdd/2026-09-10-tree-walk-reader/, and binding TREE-WALK-READER-CONTRACT.md.

Write scope: tests/tree_replay/test_tree_walk.py only, plus .superpowers/sdd/2026-09-10-tree-walk-reader/task-1-fix-report.md. Keep all runtime/Task2/files/source untouched. No nestedagents/commits/data/live actions; edits via apply_patch. Current baseline71runtime/250combinedpassed. Main writes Task2 auditor while this disjoint fix runs.

Derive literal raw vector-zone cases and full named targets/obstacles/trace from actual source rules, not implementation-generated goldens. Name and prove candidate-only runtime mutations that these assertions catch; originals read/parse only, never execute. Add source-side vector boundary/4h failure/trace requests from M1. Existing cloud equality already covered. Report full command and terminal results, hand derivations, mutations and SHA256.

Verification: python -B -m pytest tests/tree_replay/test_tree_walk.py -q --tb=short -p no:cacheprovider. Do not run whole package or duplicate Task2 audit. Return brief completion and report path; review reserved for main.
