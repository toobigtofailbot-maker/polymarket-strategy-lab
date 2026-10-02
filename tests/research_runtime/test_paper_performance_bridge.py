from dataclasses import fields
import sqlite3

import pytest

from src.data_layer.analytical_research import alpha_factory as af
from src.paper_trading import PaperEngine, PaperStore, PaperTradingError
from src.research_runtime.paper_performance_bridge import (
    ResearchPaperPerformanceSnapshot,
    build_research_paper_performance_snapshot,
    build_snapshot_context_evidence,
    snapshot_to_mapping,
)
from tests.data_layer.analytical_research.test_alpha_factory_records import episode_input
from tests.paper_trading.conftest import generous_limits, make_engine, paper_book
from tests.paper_trading.test_models import _research_binding, _research_intent


def _filled_store(path):
    store = PaperStore(path, create=True)
    binding = _research_binding()
    engine = PaperEngine.create_research(
        store, binding, generous_limits(), session_label="research", created_time_ns=100
    )
    engine.process_market_event(paper_book(100))
    engine.submit(_research_intent(binding, decision_time_ns=101))
    engine.process_market_event(paper_book(111))
    return store, engine


def test_snapshot_binds_exact_store_head_and_state(tmp_path) -> None:
    with _filled_store(tmp_path / "paper.sqlite3")[0] as store:
        snapshot = build_research_paper_performance_snapshot(store)
        head = store.current_head()
        assert head is not None
        assert snapshot.paper_store_event_sequence == head.last_sequence
        assert snapshot.paper_store_event_head == head.last_event_hash
        assert snapshot.paper_store_state_hash == head.state_hash
        assert snapshot.paper_session_id


def test_snapshot_reproduces_paper_counts_and_arithmetic(tmp_path) -> None:
    store, engine = _filled_store(tmp_path / "paper.sqlite3")
    with store:
        snapshot = build_research_paper_performance_snapshot(store)
        assert snapshot.intent_count == snapshot.order_count == 1
        assert snapshot.fill_count == 1
        assert snapshot.intended_quantity == snapshot.filled_quantity == "4"
        assert snapshot.fill_ratio == "1"
        assert snapshot.cash == engine.state.account.cash
        assert snapshot.fee_total == engine.state.fills[0].fee


def test_snapshot_rejects_corrupt_or_blocked_store(tmp_path) -> None:
    path = tmp_path / "paper.sqlite3"
    store, _engine = _filled_store(path)
    store.close()
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE paper_checkpoint SET state_hash=?", ("0" * 64,))
    with PaperStore(path) as corrupt:
        assert corrupt.reconciliation_blocked
        with pytest.raises(PaperTradingError, match="SNAPSHOT_RECONCILIATION_BLOCKED"):
            build_research_paper_performance_snapshot(corrupt)


def test_snapshot_fixed_no_authority_posture(tmp_path) -> None:
    with _filled_store(tmp_path / "paper.sqlite3")[0] as store:
        snapshot = build_research_paper_performance_snapshot(store)
        assert snapshot.research_paper_only
        assert snapshot.advisory_only
        assert snapshot.no_qualification_authority
        assert snapshot.no_execution_authority
        assert snapshot.no_live_authority
        serialized = snapshot_to_mapping(snapshot)
        assert {item.name for item in fields(ResearchPaperPerformanceSnapshot)} <= set(serialized)
        assert all("path" not in key for key in serialized)


def test_snapshot_builds_deterministic_project_evidence(tmp_path) -> None:
    with _filled_store(tmp_path / "paper.sqlite3")[0] as store:
        snapshot = build_research_paper_performance_snapshot(store)
        item = build_snapshot_context_evidence(
            snapshot,
            subject_refs=snapshot.subject_refs,
            scope_sha256="a" * 64,
            information_cutoff="2026-10-01T00:00:00Z",
            admissibility_status="ADMISSIBLE",
            direction="SUPPORTING",
        )
        assert item.evidence_class == "DETERMINISTIC_DERIVED"
        assert item.origin == "DETERMINISTIC_PROJECT_EVIDENCE"
        assert item.direction == "SUPPORTING"


def test_snapshot_id_is_valid_alpha_deterministic_evidence_ref(tmp_path) -> None:
    with _filled_store(tmp_path / "paper.sqlite3")[0] as store:
        snapshot = build_research_paper_performance_snapshot(store)
        result = af.build_research_episode(
            episode_input(
                source_reference_ids=[],
                deterministic_evidence_refs=[snapshot.snapshot_id],
                producer_type="DETERMINISTIC_ANALYSIS",
            )
        )
        assert result.is_valid
        assert snapshot.snapshot_id in result.record.deterministic_evidence_refs


def test_snapshot_supports_qualified_store_without_promotion(tmp_path) -> None:
    store, _engine = make_engine(tmp_path / "qualified.sqlite3")
    with store:
        snapshot = build_research_paper_performance_snapshot(store)
        assert snapshot.binding_kind == "QUALIFIED_PAPER"
        assert snapshot.research_paper_only
        assert snapshot.no_qualification_authority
