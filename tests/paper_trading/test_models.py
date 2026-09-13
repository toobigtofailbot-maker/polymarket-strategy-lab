from dataclasses import FrozenInstanceError, asdict, replace

import pytest

from src.paper_trading import (
    PaperEngine,
    PaperStore,
    PaperTradingError,
    build_paper_intent,
    build_strategy_binding,
    validate_paper_intent,
)
from src.paper_trading.models import content_id

from conftest import edge_stack, generous_limits


def test_binding_requires_exact_eligible_wp172_assessment(tmp_path) -> None:
    model, _experiment, _evidence, _trace, _window, assessment, binding = edge_stack()
    assert binding.assessment_id == assessment.assessment_id
    assert binding.cost_model_id == model.cost_model_id
    assert binding.decision_trace_id == assessment.decision_trace_id
    assert binding.market_data_lineage_id == assessment.market_data_lineage_id
    assert binding.simulated_paper_only
    with pytest.raises(PaperTradingError, match="WP172_BINDING_INVALID"):
        build_strategy_binding(
            replace(assessment, wp173_evaluation_eligible=False),
            model,
            strategy_label="bad",
            created_time_ns=1,
        )
    other, *_ = edge_stack(fee_rate_bps="101")
    with pytest.raises(PaperTradingError, match="WP172_BINDING_INVALID"):
        build_strategy_binding(
            assessment, other, strategy_label="mismatch", created_time_ns=1
        )
    forged = replace(binding, fee_rate_bps="0", binding_id="")
    forged_preimage = asdict(forged)
    forged_preimage.pop("binding_id")
    forged_preimage.pop("simulated_paper_only")
    forged = replace(
        forged,
        binding_id=content_id("paperbinding:sha256:", forged_preimage),
    )
    with PaperStore(tmp_path / "forged.sqlite3", create=True) as store:
        with pytest.raises(PaperTradingError, match="WP172_BINDING_INVALID"):
            PaperEngine.create(
                store,
                forged,
                generous_limits(),
                assessment=assessment,
                cost_model=model,
                session_label="forged",
                created_time_ns=1,
            )


def test_intent_is_content_addressed_immutable_and_style_bound() -> None:
    *_, binding = edge_stack()
    intent = build_paper_intent(
        binding,
        market_id="market:a",
        asset_id="asset:a",
        side="BUY",
        quantity="4",
        order_style="AGGRESSIVE_TAKER",
        reference_price="0.5",
        decision_time_ns=100,
    )
    validate_paper_intent(intent, binding)
    assert intent == build_paper_intent(
        binding,
        market_id="market:a",
        asset_id="asset:a",
        side="BUY",
        quantity="4",
        order_style="AGGRESSIVE_TAKER",
        reference_price="0.5",
        decision_time_ns=100,
    )
    with pytest.raises(PaperTradingError, match="INTENT_INVALID"):
        validate_paper_intent(replace(intent, quantity="5"), binding)
    with pytest.raises(PaperTradingError, match="INTENT_INVALID"):
        build_paper_intent(
            binding,
            market_id="market:a",
            asset_id="asset:a",
            side="BUY",
            quantity="4",
            order_style="PASSIVE_MAKER",
            reference_price="0.5",
            decision_time_ns=100,
        )
    with pytest.raises(FrozenInstanceError):
        intent.quantity = "5"  # type: ignore[misc]
