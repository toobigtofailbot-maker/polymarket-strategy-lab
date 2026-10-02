from dataclasses import FrozenInstanceError, asdict, fields, replace

import pytest

from src.paper_trading import (
    PaperEngine,
    PaperStore,
    PaperTradingError,
    ResearchPaperStrategyBinding,
    build_research_strategy_binding,
    build_paper_intent,
    build_strategy_binding,
    validate_paper_intent,
    validate_research_strategy_binding,
    validate_strategy_binding,
)
from src.paper_trading.models import content_id

from tests.paper_trading.conftest import edge_stack, generous_limits


def _research_binding(**overrides):
    values = dict(
        candidate_id="candidate:sha256:" + "1" * 64,
        hypothesis_family_id="family:sha256:" + "2" * 64,
        research_episode_id="episode:sha256:" + "3" * 64,
        strategy_spec_id="strategyspec:sha256:" + "4" * 64,
        strategy_version="research-v1",
        strategy_code_identity="code:sha256:" + "5" * 64,
        subject_refs=("market:a",),
        scope_id="scope:sha256:" + "6" * 64,
        allowed_market_ids=("market:a",),
        market_data_lineage_id="lineage:sha256:" + "7" * 64,
        decision_time_start_ns=100,
        decision_time_end_ns=200,
        execution_mode="AGGRESSIVE_TAKER",
        fee_rate_bps="100",
        maker_rebate_bps="0",
        latency_ns=10,
        order_ttl_ns=None,
        queue_ahead_multiplier="1",
        markout_horizon_ns=0,
        max_data_age_ns=100,
        reserved_evidence_policy="NON_CONFIRMATORY_RESEARCH_PAPER",
        reserved_evidence_refs=(),
        admitted_scope_refs=(),
        created_time_ns=1,
    )
    values.update(overrides)
    return build_research_strategy_binding(**values)


def _research_intent(binding, **overrides):
    values = dict(
        market_id="market:a",
        asset_id="asset:a",
        side="BUY",
        quantity="4",
        order_style=binding.execution_mode,
        reference_price="0.5",
        decision_time_ns=100,
    )
    values.update(overrides)
    return build_paper_intent(binding, **values)


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


def test_research_binding_is_deterministic() -> None:
    binding = _research_binding(subject_refs=("market:z", "market:a"), allowed_market_ids=("market:b", "market:a"))
    assert binding == _research_binding(subject_refs=("market:a", "market:z"), allowed_market_ids=("market:a", "market:b"))
    assert binding.binding_id.startswith("researchpaperbinding:sha256:")
    assert tuple(item.name for item in fields(ResearchPaperStrategyBinding)) == (
        "schema_version", "binding_id", "binding_kind", "candidate_id",
        "hypothesis_family_id", "research_episode_id", "strategy_spec_id",
        "strategy_version", "strategy_code_identity", "subject_refs", "scope_id",
        "allowed_market_ids", "market_data_lineage_id", "decision_time_start_ns",
        "decision_time_end_ns", "execution_mode", "fee_rate_bps", "maker_rebate_bps",
        "latency_ns", "order_ttl_ns", "queue_ahead_multiplier", "markout_horizon_ns",
        "max_data_age_ns", "reserved_evidence_policy", "reserved_evidence_refs",
        "admitted_scope_refs", "created_time_ns", "research_paper_only",
        "simulated_paper_only", "qualification_claim", "executable_edge_claim",
        "wp173_qualified_evaluation_eligible", "gate_c_eligible",
        "live_promotion_eligible", "real_capital_usd",
    )
    validate_research_strategy_binding(binding)


def test_research_binding_rejects_forgery() -> None:
    with pytest.raises(PaperTradingError, match="RESEARCH_BINDING_INVALID"):
        validate_research_strategy_binding(replace(_research_binding(), fee_rate_bps="0"))


def test_research_binding_authority_flags_are_fixed() -> None:
    binding = _research_binding()
    with pytest.raises(PaperTradingError, match="RESEARCH_BINDING_INVALID"):
        validate_research_strategy_binding(replace(binding, qualification_claim=True))
    with pytest.raises(FrozenInstanceError):
        binding.gate_c_eligible = True  # type: ignore[misc]


def test_research_binding_rejects_invalid_scopes() -> None:
    for change in (
        {"subject_refs": ()},
        {"allowed_market_ids": ()},
        {"allowed_market_ids": ("market:a", "market:a")},
        {"subject_refs": ("",)},
    ):
        with pytest.raises(PaperTradingError, match="RESEARCH_BINDING_INVALID"):
            _research_binding(**change)


def test_research_binding_rejects_invalid_window() -> None:
    for start, end in ((100, 100), (101, 100), (-1, 100)):
        with pytest.raises(PaperTradingError, match="RESEARCH_BINDING_INVALID"):
            _research_binding(decision_time_start_ns=start, decision_time_end_ns=end)


def test_qualified_binding_contract_remains_unchanged() -> None:
    *_, binding = edge_stack()
    validate_strategy_binding(binding)
    assert binding.binding_id.startswith("paperbinding:sha256:")


def test_research_intent_inside_scope_passes() -> None:
    binding = _research_binding()
    intent = _research_intent(binding)
    validate_paper_intent(intent, binding)
    assert intent.binding_id == binding.binding_id


def test_research_intent_outside_market_rejects() -> None:
    with pytest.raises(PaperTradingError, match="INTENT_INVALID"):
        _research_intent(_research_binding(), market_id="market:b")


def test_research_intent_outside_window_rejects() -> None:
    for decision_time_ns in (99, 200):
        with pytest.raises(PaperTradingError, match="INTENT_INVALID"):
            _research_intent(_research_binding(), decision_time_ns=decision_time_ns)


def test_research_intent_style_mismatch_rejects() -> None:
    with pytest.raises(PaperTradingError, match="INTENT_INVALID"):
        _research_intent(_research_binding(), order_style="PASSIVE_MAKER")


def test_reserved_evidence_requires_proven_non_overlap() -> None:
    reserved = "evidence:sha256:" + "8" * 64
    with pytest.raises(PaperTradingError, match="RESEARCH_BINDING_INVALID"):
        _research_binding(reserved_evidence_refs=(reserved,))
    proof = content_id(
        "nonoverlap:sha256:",
        {
            "reserved_evidence_ref": reserved,
            "scope_id": "scope:sha256:" + "6" * 64,
            "allowed_market_ids": ["market:a"],
            "decision_time_start_ns": 100,
            "decision_time_end_ns": 200,
        },
    )
    with pytest.raises(PaperTradingError, match="RESEARCH_BINDING_INVALID"):
        _research_binding(
            reserved_evidence_refs=(reserved,), admitted_scope_refs=(proof,)
        )
    assert _research_binding().reserved_evidence_refs == ()
