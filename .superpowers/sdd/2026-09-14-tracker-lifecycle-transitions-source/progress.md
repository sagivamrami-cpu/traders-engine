# SDD ledger — plan: docs/superpowers/plans/2026-09-14-tracker-lifecycle-transitions-source.md

## Pre-flight review

| Tasks/interfaces | Producer → consumer | Finding / ruling |
| --- | --- | --- |
| Task 1 runtime → Task 2 audit | selected tracker helper AST and `LifecycleTransitions` constructor | Clean. Task 2 statically pins exactly Task 1's selected helper projection. |
| Task 1 → lifecycle bars | source `_entry_band` geometry | Clean. Reuse accepted private helper; no new entry rule is created. |
| Task 1 → desk success | source `desk_success.stop_note` | Ruling: bind one `DeskSuccess(source)` on the transition instance. Cost if wrong: a future resolver may need a differently scoped success instance, so this component must not claim resolver integration. |
| Task 1 → source clock | source `_mark_terminal` `time.time()` | Clean specialization: raw `source.now_epoch()` is the only clock substitution. |
| Task 1 vs deferred zone return | `_zone_return_message` calls revalidation and adds live-only semantics | Ruling: exclude it. It belongs to the later live resolver/revalidation binding, not this feed-independent transition set. |

Task 1: in progress. Retained source is parsed only. No feed, outcome write,
delivery, broker, replay, dataset or model action is in scope.

Task 2: fix round 1. Independent review found mutable child-audit identity and
unserializable-child CLI failure paths. Ruling: both are load-bearing because
this component may certify its transitive lifecycle-bars/desk-success proof;
pin the sole child identity, require its verified projection set, validate
JSON-serializability, and keep the CLI fail-closed. Cost if wrong: a future
audit change may need an explicit contract extension rather than silently
changing the certified dependency set.

Task 1: complete. Runtime projection and its independent task review closed
after source-marker, ordering and malformed-input fixes. The focused runtime
suite passed 18 cases. It constructs messages/state only and retains no
resolver, persistence, delivery, outcome or readiness claim.

Task 2: complete. The auditor/CLI and final combined review closed after three
fail-closed repair rounds: child identity/projection pinning, malformed or
unserializable child reports, and unexpected JSON serialization exceptions.
Fresh combined runtime/source/child verification passed 73 cases in 48.51s;
the retained-source CLI was VERIFIED with both readiness flags false.
