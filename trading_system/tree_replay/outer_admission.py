"""Offline source-order admission for one retained level-reversal plan.

This adapter consumes supplied causal context only. A successful result is an
advisory tracker registration, never a fill, economic fact, delivery or label.
"""
from __future__ import annotations

from collections.abc import MutableMapping
from datetime import datetime

from .admission_context import CausalAdmissionContext
from .causal_replay_contracts import canonical_digest
from .clock import ReplayClock, _validate_binding
from .outer_admission_contracts import OuterAdmissionDecision, OuterAdmissionInputs
from .outer_admission_ports import entry_blocked, outside_hunting_window
from ._vendor import admission_quality
from ._vendor.pricing import Plan


_SUPPORTED_VARIANT = "level_reversal:5m"


def source_plan_digest(plan: Plan) -> str:
    """Commit the immutable source geometry before admission-side mutations.

    Entry-quality, born-open and cooldown annotations are intentionally absent:
    they are produced by later source gates.  The retained selected plan's
    pre-admission geometry and source decision fields are all committed.
    """
    if type(plan) is not Plan:
        raise ValueError("plan must be the retained exact source Plan")
    return canonical_digest({
        "symbol": plan.symbol,
        "close": plan.close,
        "kind": plan.kind,
        "direction": plan.direction,
        "style": plan.style,
        "entry": plan.entry,
        "stop": plan.stop,
        "targets": tuple(plan.targets),
        "obstacles": tuple(plan.obstacles),
        "atr": plan.atr,
        "risk": plan.risk,
        "rr": plan.rr,
        "rr_far": plan.rr_far,
        "refusal": plan.refusal,
        "tradeable": plan.tradeable,
        "reasons": tuple(plan.reasons),
        "warnings": tuple(plan.warnings),
    })


class OuterAdmissionAdapter:
    """Apply the pinned outer gates without source imports or external I/O."""

    def __init__(self, *, admission: CausalAdmissionContext):
        if type(admission) is not CausalAdmissionContext:
            raise ValueError("admission must be an exact CausalAdmissionContext")
        if type(admission._clock) is not ReplayClock:
            raise ValueError("admission must use an exact ReplayClock")
        _validate_binding(admission._clock, admission.decision_time)
        self.admission = admission

    def _decision(self, inputs, *, status, trace, reason=None, tracker_id=None,
                  tracker_state_digest=None, annotations=()):
        return OuterAdmissionDecision(
            decision_id=f"{inputs.input_id}:outer-admission", input_id=inputs.input_id,
            status=status, gate_trace=tuple(trace), reason=reason,
            tracker_id=tracker_id, tracker_state_digest=tracker_state_digest,
            annotations=annotations,
        )

    def _annotate_entry_quality(self, plan: Plan, at: datetime) -> tuple[str, ...]:
        """Preserve source quality annotation as non-veto, including source catches."""
        try:
            now = at.timestamp()
            since = now - admission_quality.MAX_REJECTION_AGE_S
            atr = float(plan.atr or 0.0)
            other = "לונג" if plan.direction == "שורט" else "שורט"
            quality = admission_quality.evaluate(
                direction=plan.direction, entry=plan.entry, atr=atr, reasons=plan.reasons,
                aligned_rejection=self.admission.tracker._recent_rejection(
                    plan.symbol, plan.direction, since, now, plan.entry,
                ),
                opposing_rejection=self.admission.tracker._recent_rejection(
                    plan.symbol, other, since, now, plan.entry,
                    require_overlap=False, max_distance=atr or None,
                ),
            )
            plan.entry_quality = quality
            plan.entry_labels = list(quality["labels"])
            return (
                "entry_quality:annotated",
                *(("entry_quality:aligned_rejection",)
                  if quality["aligned_rejection"] is not None else ()),
                *(("entry_quality:opposing_rejection",)
                  if quality["opposing_rejection"] is not None else ()),
                *(f"entry_quality:label:{label}" for label in plan.entry_labels),
            )
        except Exception:
            # The pinned source records a diagnostic and continues; the detached
            # decision has no raw log payload or exception text field.
            return ("entry_quality:unavailable",)

    def evaluate(self, inputs: OuterAdmissionInputs, plan: Plan, *, active_reversals: MutableMapping,
                 watch_state: MutableMapping, record_alerts_enabled: bool) -> OuterAdmissionDecision:
        if type(inputs) is not OuterAdmissionInputs:
            raise ValueError("inputs must be exact OuterAdmissionInputs")
        if type(plan) is not Plan:
            raise ValueError("plan must be the retained exact source Plan")
        if not isinstance(watch_state, MutableMapping):
            raise ValueError("watch_state must be a mutable source state mapping")
        if not isinstance(active_reversals, MutableMapping):
            raise ValueError("active_reversals must be a mutable source state mapping")
        if type(record_alerts_enabled) is not bool:
            raise ValueError("record_alerts_enabled must be an explicit bool")
        if source_plan_digest(plan) != inputs.plan_digest:
            return self._decision(inputs, status="BLOCKED", trace=("plan_commitment",),
                                  reason="PLAN_DIGEST_MISMATCH")
        at = self.admission.decision_time
        if at < inputs.available_at or at > inputs.covered_through:
            return self._decision(inputs, status="BLOCKED", trace=("evidence",),
                                  reason="ADMISSION_INPUT_UNAVAILABLE")
        if inputs.source_variant != _SUPPORTED_VARIANT:
            return self._decision(inputs, status="UNSUPPORTED", trace=("variant",),
                                  reason="SOURCE_VARIANT_UNSUPPORTED")

        trace: list[str] = ["entry_quality_annotation"]
        annotations = self._annotate_entry_quality(plan, at)
        trace.append("tradeable_plan")
        if not plan.tradeable:
            return self._decision(inputs, status="REJECTED", trace=trace,
                                  reason=plan.refusal or "PLAN_NOT_TRADEABLE", annotations=annotations)
        trace.append("hunting_window")
        outside = outside_hunting_window(at)
        if outside:
            return self._decision(inputs, status="REJECTED", trace=trace, reason=outside,
                                  annotations=annotations)
        trace.append("entry_clock")
        closed = entry_blocked(at)
        if closed:
            return self._decision(inputs, status="REJECTED", trace=trace, reason=closed,
                                  annotations=annotations)
        trace.append("post_stop")
        cooldown = self.admission.tracker.blocked_after_stop(plan.symbol, plan.direction, plan)
        if cooldown:
            return self._decision(inputs, status="REJECTED", trace=trace, reason=cooldown,
                                  annotations=annotations)
        trace.append("occupied_slot")
        if self.admission.tracker.has_open(plan.symbol, plan.direction):
            return self._decision(inputs, status="REJECTED", trace=trace, reason="OCCUPIED_SLOT",
                                  annotations=annotations)
        trace.append("same_level")
        same_level = self.admission.tracker.blocked_same_level(plan.symbol, plan.direction, plan.entry)
        if same_level:
            return self._decision(inputs, status="REJECTED", trace=trace, reason=same_level,
                                  annotations=annotations)
        trace.append("active_reversal")
        # The source exposes the valid reversal to later producers in this
        # pass even if its own episode was already admitted earlier.
        active_reversals[plan.symbol] = plan
        state_key = f"{plan.symbol}:level_reversal:{inputs.episode_id}"
        trace.append("episode")
        if watch_state.get(state_key):
            return self._decision(inputs, status="REJECTED", trace=trace,
                                  reason="ALREADY_ADMITTED_EPISODE", annotations=annotations)
        trace.append("record_alert_guard")
        if not record_alerts_enabled:
            return self._decision(inputs, status="OBSERVE_ONLY", trace=trace,
                                  reason="SOURCE_ALERT_RECORDING_DISABLED", annotations=annotations)
        before = self.admission.load()
        trace.append("record")
        try:
            recorded = self.admission.tracker.record(
                plan, variant=inputs.source_variant, to_group=True,
            )
        except Exception:
            # The source logs the failure and continues the pass.  Preserve
            # that non-publication result without exposing exception text.
            return self._decision(inputs, status="BLOCKED", trace=trace,
                                  reason="TRACKER_RECORD_FAILED", annotations=annotations)
        if not recorded:
            return self._decision(inputs, status="REJECTED", trace=trace,
                                  reason="DUPLICATE_TRACKER_RECORD", annotations=annotations)
        after = self.admission.load()
        created = tuple(key for key in after if key not in before)
        if len(created) != 1 or type(after[created[0]]) is not dict:
            return self._decision(inputs, status="BLOCKED", trace=trace,
                                  reason="TRACKER_RECORD_IDENTITY_UNAVAILABLE", annotations=annotations)
        tracker_id = after[created[0]].get("trade_id")
        if type(tracker_id) is not str or not tracker_id:
            return self._decision(inputs, status="BLOCKED", trace=trace,
                                  reason="TRACKER_RECORD_IDENTITY_UNAVAILABLE", annotations=annotations)
        watch_state[state_key] = {
            "ts": at.timestamp(), "direction": plan.direction, "entry": plan.entry,
        }
        return self._decision(inputs, status="ADMITTED_TRACKER", trace=trace,
                              tracker_id=tracker_id, tracker_state_digest=canonical_digest(after),
                              annotations=annotations)
