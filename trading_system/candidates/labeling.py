from __future__ import annotations

from trading_system.candidates.contracts import CandidateAction, OutcomeLabel, TradeContract
from trading_system.data_foundation.contracts import NormalizedBar

LABEL_VERSION = "fixture-outcome-0.1.0"


def build_fixture_trade_contract(candidate_bar: NormalizedBar) -> TradeContract:
    entry = candidate_bar.close
    stop = candidate_bar.low
    risk = entry - stop
    if risk <= 0:
        raise ValueError("long fixture contract requires entry above stop")
    return TradeContract(
        contract_version="fixture-tr-contract-0.1.0",
        entry_policy="FIXTURE_CLOSE_ENTRY",
        entry_price=entry,
        stop_policy="FIXTURE_BAR_LOW",
        stop_price=stop,
        target_policy="FIXTURE_TWO_R_TARGET",
        target_price=entry + 2 * risk,
        expiry_policy="FIXTURE_MAX_BARS",
        max_holding_bars=2,
        commission=0.0,
        slippage_model_version="fixture-zero-slippage-0.1.0",
        fill_policy_version="fixture-close-fill-0.1.0",
    )


def _empty_excluded_label(candidate_id: str) -> OutcomeLabel:
    return OutcomeLabel(
        candidate_id=candidate_id,
        label_version=LABEL_VERSION,
        outcome_class="EXPIRED",
        target_before_stop=0,
        stop_before_target=0,
        expired=1,
        net_return_r=None,
        mae_r=None,
        mfe_r=None,
        time_to_outcome_bars=None,
        filled=False,
        realized_slippage_ticks=None,
        label_quality="EXCLUDED_FROM_TRAINING",
    )


def _r_values(contract: TradeContract, bars: list[NormalizedBar]) -> tuple[float, float]:
    risk = contract.entry_price - contract.stop_price
    mae = max((contract.entry_price - bar.low) / risk for bar in bars)
    mfe = max((bar.high - contract.entry_price) / risk for bar in bars)
    return mae, mfe


def label_long_candidate(
    candidate: CandidateAction,
    contract: TradeContract,
    future_bars: list[NormalizedBar],
) -> OutcomeLabel:
    if candidate.status != "ELIGIBLE":
        return _empty_excluded_label(candidate.candidate_id)

    evaluated: list[NormalizedBar] = []
    for index, bar in enumerate(sorted(future_bars, key=lambda item: item.observed_at), start=1):
        if index > contract.max_holding_bars:
            break
        evaluated.append(bar)
        target_touched = bar.high >= contract.target_price
        stop_touched = bar.low <= contract.stop_price
        mae, mfe = _r_values(contract, evaluated)
        if target_touched and stop_touched:
            return OutcomeLabel(
                candidate_id=candidate.candidate_id,
                label_version=LABEL_VERSION,
                outcome_class="AMBIGUOUS",
                target_before_stop=0,
                stop_before_target=0,
                expired=0,
                net_return_r=None,
                mae_r=mae,
                mfe_r=mfe,
                time_to_outcome_bars=index,
                filled=True,
                realized_slippage_ticks=0.0,
                label_quality="EXCLUDED_FROM_TRAINING",
            )
        if target_touched:
            return OutcomeLabel(
                candidate_id=candidate.candidate_id,
                label_version=LABEL_VERSION,
                outcome_class="TARGET_FIRST",
                target_before_stop=1,
                stop_before_target=0,
                expired=0,
                net_return_r=2.0,
                mae_r=mae,
                mfe_r=mfe,
                time_to_outcome_bars=index,
                filled=True,
                realized_slippage_ticks=0.0,
                label_quality="HIGH",
            )
        if stop_touched:
            return OutcomeLabel(
                candidate_id=candidate.candidate_id,
                label_version=LABEL_VERSION,
                outcome_class="STOP_FIRST",
                target_before_stop=0,
                stop_before_target=1,
                expired=0,
                net_return_r=-1.0,
                mae_r=mae,
                mfe_r=mfe,
                time_to_outcome_bars=index,
                filled=True,
                realized_slippage_ticks=0.0,
                label_quality="HIGH",
            )

    if not evaluated:
        return _empty_excluded_label(candidate.candidate_id)

    risk = contract.entry_price - contract.stop_price
    mae, mfe = _r_values(contract, evaluated)
    final_close = evaluated[-1].close
    return OutcomeLabel(
        candidate_id=candidate.candidate_id,
        label_version=LABEL_VERSION,
        outcome_class="EXPIRED",
        target_before_stop=0,
        stop_before_target=0,
        expired=1,
        net_return_r=(final_close - contract.entry_price) / risk,
        mae_r=mae,
        mfe_r=mfe,
        time_to_outcome_bars=len(evaluated),
        filled=True,
        realized_slippage_ticks=0.0,
        label_quality="MEDIUM",
    )
