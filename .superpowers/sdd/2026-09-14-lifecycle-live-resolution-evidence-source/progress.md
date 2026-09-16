# SDD ledger — plan: docs/superpowers/plans/2026-09-14-lifecycle-live-resolution-evidence-source.md

## Pre-flight review

| Tasks/interfaces | Producer → consumer | Finding / ruling |
| --- | --- | --- |
| Task 1 collector → later resolver body | `(prices, bar_extremes)` only | Clean. It must have no trade mutation or messages. |
| accepted live evidence → Task 1 | `_live_prices()` fresh map and `FORCE_BAR_AGE_S` | Clean. Reuse rather than duplicate it. |
| Task 1 runtime → Task 2 audit | extracted leading source statements | Clean. Audit must pin statement order and permitted ports, not claim full `_check_live_locked` parity. |
| fallback correction → economic outcome | corrected frame low/high/close evidence | Ruling: preserve raw evidence only; no fill/outcome inference. Cost if wrong: later components could mistake range evidence for an executed lifecycle event. |

Task 1: in progress. Source remains read/parsed only; no acquisition, broker,
state change, delivery, outcome, replay, dataset or model work is in scope.

Task 1: complete after M1 repair and scoped re-review. The falsy quote-row
source normalization is now exact; fresh focused evidence: `30 passed in
1.70s`. No resolver-state or economic behavior was added.

Task 2: complete and accepted with the final combined component. The source
auditor initially exposed the real quote-age exception-boundary mismatch; a
normal RED regression test reproduced it before the runtime projection was
aligned. The final source projection is verified at the pinned commit/blob;
fresh combined evidence is `49 passed in 4.55s`, retained CLI `VERIFIED`, and
the independent final review is PASS. The collector remains evidence only;
resolver mutation, economics, outcomes, replay, dataset and model work remain
out of scope.
