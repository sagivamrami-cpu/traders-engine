# Selected reversal Plan handoff contract

Continuation of approved master C, after tracker source acceptance132950Z.
This is a bounded internal interface change, not a new trade policy or completion
of causal admission. Parent source intake/final review132300Z identified that
public pricing evidence omits Plan.close/kind and cannot drive faithful record.

## Design and ownership

Retain the actual selected event and pricing.Plan object from the existing single
source evaluation. Do not reconstruct it from JSON, rerun find or pricing, clone
source decision logic, or accept a caller-provided selection dictionary. Extract
the current find_reversal_asof body into _evaluate_reversal_asof with the same
keyword-only inputs. Existing public find_reversal_asof remains a dict-returning
wrapper with identical signature, validation, report content, hashes and VERSION.

Private frozen dataclass _ReversalEvaluation holds:
- report: dict, the existing pre-admission evidence report.
- selected_event: level_reversal.Reversal | None.
- selected_plan: pricing.Plan | None.
The dataclass freezes bindings, not the source Plan; source admission deliberately
mutates born_open, cooldown_release, entry labels/quality and dynamic attributes.
A new evaluation owns new objects; downstream Plan mutations cannot mutate an
already materialized report or another evaluation. No serializable capability,
auth guarantee, disk persistence, or public training feature is implied.

Retain both objects only when final report status is
PRODUCER_SELECTED_UNADMITTED and report selected is present after all existing
serialization succeeds. Both are None for unsupported symbol, no candidate,
missing inputs, source errors and pricing/snapshot serialization failures. A
source-selected PRICE_REFUSED Plan is retained as refused (not replaced, admitted
or auto-recorded). Original source and public compatibility remain authoritative.
The private evaluator performs no tracking, saving or notification on its own.

## Verification

Real synthetic FrameSpec/calendar/correction -> actual map -> find -> pricing
must produce event and Plan. Prove the exact selected object from a single call
is retained, with original close/kind/direction/style/target order and list fields.
Capture original public report decision/evaluation hashes before refactor for
representative accepted, refused, no-selection and unavailable fixtures; require
them unchanged afterward on this same dependency environment. Existing producer
78 tests remain; do not replace their tests or global pytest configuration.

Exercise late serialization failure after original find returns a real Plan:
private result must be BLOCKED with no retained event/Plan. Known input errors
must retain old raised exceptions, not new error reports. Confirm refused newest
M15 beats older paying M5. Confirm report detached from Plan lists and from later
tracker mutations; repeat evaluations independent.

Integration test uses actual selected Plan directly in real TrackerAdmission
with explicit test-only offline ports. Assert actual stored source geometry,
kind/reasons/targets, born state and unchanged pre-admission report/hash. Controlled
matrix/quote/state inputs here test the handoff, not actual causal provider
certification. No manually built Plan in this positive integration path.
No market logs/data access or economic labels. Source readiness flags remain false.

## Follow-on, not waived

Actual matrix/swing FrameSpec/correction ports; coverage-checked state/quotes/raw
log prefixes; heterogeneous watch memory and deletions; exact original caller
ordering/publication branches and lifecycle; other producers; simulator, dataset,
models. Preserve all seven constraints of final review132300Z. Do not treat this
handoff as outer admission, full source-loop replay, economic fill or training.
