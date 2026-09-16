# Tracker lifecycle transitions source usage

`LifecycleTransitions(source)` is an offline projection of the selected
chart-desk tracker transition and message helpers. It owns one
`DeskSuccess(source)` instance and consumes accepted lifecycle voice, canonical
symbol and entry-band components.

```python
from trading_system.tree_replay._vendor.lifecycle_transitions import LifecycleTransitions

transitions = LifecycleTransitions(source)
messages = transitions._progress_messages(trade, best, short, name, side)
```

The component only constructs source messages and mutates the source-owned
trade fields that its selected helpers mutate: `terminal_result`, progress
ladder fields, and (through `_mark_terminal`) `state` plus `resolved_ts`.
`_mark_terminal` uses `source.now_epoch()` instead of the source wall clock.
All other selected behavior preserves the pinned tracker helper semantics,
including ambiguity resolving conservatively to the published protection.

It does not read feeds or quotes, resolve an open trade, revalidate, persist
state, journal or deliver a message, create a fill/outcome/economic label, or
establish replay, dataset, training or model readiness. Resolver loops and
their causal inputs remain deferred.

Acceptance evidence is recorded in
`agent-exchange/status/2026-09-14T050000Z-codex-lifecycle-transitions.md`.
The retained-source auditor pins the chart-desk commit and tracker blob, checks
the complete projection, and requires the accepted lifecycle-bars,
desk-success, and lifecycle-voice proof. Its JSON CLI and every child failure
path fail closed; both readiness flags remain false.
