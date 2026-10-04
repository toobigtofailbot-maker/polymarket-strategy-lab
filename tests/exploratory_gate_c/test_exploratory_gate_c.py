"""Focused tests for the S10-GATE-C-EXPLORE-01 exploratory Gate-C policy-permit core.

Every test is deterministic and local: lifecycle and Hermes strategy-manager stores are real
verified temporary SQLite stores, Hermes assessments are produced by the existing
FakeHermesBackend, and EXEC-FEAS snapshots are built from fixed in-memory public payloads.
No test performs network, account, credential, signing, order or live behavior.
"""

from __future__ import annotations

import ast
import dataclasses
from datetime import datetime, timezone
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys

import pytest

import src.exploratory_gate_c as G
from src.exploratory_gate_c import evaluator as E
from src.exploratory_gate_c import models as M
from src.exploratory_gate_c import (
    ExploratoryGateCDecision,
    ExploratoryGateCError,
    ExploratoryGateCPermit,
    build_exploratory_gate_c_permit,
    evaluate_exploratory_gate_c,
    validate_exploratory_gate_c_decision,
    validate_exploratory_gate_c_permit,
)
from src.execution_feasibility import (
    ExecutionFeasibilityAssessment,
    assess_execution_feasibility,
    build_execution_intent,
)
from src.execution_feasibility import models as FM
from src.execution_feasibility import public_market as P
from src.research_runtime.hermes_controlled_runtime import strategy_manager as sm
from src.research_runtime.hermes_controlled_runtime.models import (
    DRAFT_AUTHORITY_FLAGS,
    DRAFT_SCHEMA_VERSION,
)
from src.research_runtime.hermes_controlled_runtime.runner import (
    FakeHermesBackend,
    HermesInvocationOutcome,
)
from src.strategy_lifecycle import (
    CAPACITY_REASON_CODES,
    append_strategy_lifecycle_record,
    build_portfolio_authority_policy,
    build_portfolio_policy_receipt,
    build_strategy_family,
    build_strategy_health_receipt,
    build_strategy_restriction_receipt,
    build_strategy_risk_allocation,
    build_strategy_version,
    initialize_strategy_lifecycle_store,
    load_strategy_lifecycle_store,
)

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "exploratory_gate_c"
SPEC = ROOT / "docs" / "wp_specs" / "S10-GATE-C-EXPLORE-01" / "wp_spec.json"
SOURCES = sorted(PACKAGE.glob("*.py"))

T0 = 1_800_000_000_000_000_000
BOOK_MS = T0 // 1_000_000 - 1_000  # book observed 1 s before acquisition completed
BOOK_NS = BOOK_MS * 1_000_000
AGE = 5_000_000_000
PUBLIC_DEADLINE = BOOK_NS + AGE
AT = T0 + 1_000_000_000
CUTOFF_NS = T0 - 30_000_000_000
GAMMA_ID = "516710"
COND = "0x" + "ab" * 32
TOKEN = "71321045679252212594626385532706912750332728571942532289631379312455583992563"
OTHER_TOKEN = "52114319501245915516055106046884209969926127482827954674443846427813813222426"
HERMES_CUTOFF = "2026-10-01T00:00:00Z"
FIXED_CLOCK = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

STRATEGY_SPEC = {
    "thesis": {"claim": "fixture thesis"},
    "universe": {"category": "weather"},
    "entry_rule": {"signal": "fixture"},
    "exit_rule": {"horizon": "resolution"},
    "execution_rule": {"style": "AGGRESSIVE_TAKER", "max_slippage": "0.02"},
    "parameters": {"lookback": 5},
}
BOUNDS = {"lookback": {"kind": "INTEGER_RANGE", "min": 0, "max": 10}}
LIMITS = {
    "global_capital_at_risk_max_usd": "1000", "global_gross_exposure_max_usd": "1000",
    "global_daily_loss_max_usd": "100", "global_drawdown_max_usd": "200",
    "global_cumulative_loss_max_usd": "300", "exploratory_pool_max_usd": "300",
    "validated_pool_max_usd": "300", "mature_pool_max_usd": "300",
    "max_exploratory_per_strategy_usd": "100", "max_validated_per_strategy_usd": "200",
    "max_mature_per_strategy_usd": "300", "max_per_market_usd": "50",
    "max_order_notional_usd": "10", "max_active_strategies": 3, "max_active_markets": 10,
    "max_simultaneous_open_orders": 20, "max_mutations_per_minute": 60,
}
BOTH_STYLES = ("AGGRESSIVE_TAKER", "PASSIVE_MAKER")


def code_of(fn, *args, **kwargs) -> str:
    with pytest.raises(ExploratoryGateCError) as excinfo:
        fn(*args, **kwargs)
    assert str(excinfo.value) == excinfo.value.code
    assert excinfo.value.code in M.ERROR_CODES
    assert excinfo.value.__cause__ is None or excinfo.value.__suppress_context__
    return excinfo.value.code


# ---------------------------------------------------------------------------
# Lifecycle + Hermes world (real verified stores).
# ---------------------------------------------------------------------------


def _policy(*, styles=BOTH_STYLES, expires=None, label="Global envelope", predecessor=None,
            created=10, **limit_changes):
    limits = dict(LIMITS)
    limits.update(limit_changes)
    return build_portfolio_authority_policy(
        predecessor_policy_id=predecessor, policy_label=label,
        account_scope_ref="account:public-scope-1", effective_from_ns=created,
        expires_at_ns=expires, allowed_order_styles=styles, created_time_ns=created, **limits,
    )


def _activate(pol, previous=None, t=20):
    return build_portfolio_policy_receipt(
        action="ACTIVATE", policy_id=pol.policy_id, previous_active_policy_id=previous,
        human_authorization_ref="human:karl-approval-1", created_time_ns=t,
    )


def _allocation(ver, pol, *, band="EXPLORATORY_LIVE", budget="50", valid_from=100,
                valid_until=None):
    return build_strategy_risk_allocation(
        strategy_version_id=ver.strategy_version_id, policy_id=pol.policy_id, risk_band=band,
        active_budget_usd=budget, allocation_basis="DIRECT_DECISION",
        decision_ref="decision:unit-1", valid_from_ns=valid_from, valid_until_ns=valid_until,
        created_time_ns=100,
    )


def _health(ver, previous, new, t=50):
    return build_strategy_health_receipt(
        strategy_version_id=ver.strategy_version_id, previous_health_state=previous,
        new_health_state=new, decision_ref="decision:health-1", created_time_ns=t,
    )


def _pause(ver, t=60):
    return build_strategy_restriction_receipt(
        strategy_version_id=ver.strategy_version_id, restriction_key="pause.1", action="APPLY",
        restriction_kind="PAUSE_NEW_EXPOSURE", decision_ref="decision:restrict-1",
        created_time_ns=t,
    )


def _usage() -> bytes:
    return json.dumps({
        "input_tokens": 50, "output_tokens": 80, "total_tokens": 130, "api_calls": 1,
        "estimated_cost_usd": 0.04, "cost_status": "estimated",
        "cost_source": "official_docs_snapshot", "model": "example-model",
        "provider": "example-provider", "session_id": "s1", "completed": True, "failed": False,
    }).encode("utf-8")


def judgment(**overrides) -> dict:
    value = {
        "lifecycle_action": "CONTINUE", "recommended_health_state": "HEALTHY",
        "risk_direction": "UNCHANGED", "target_risk_band": None,
        "adaptation_recommendation": None,
    }
    value.update(overrides)
    return value


def _draft(request_id: str, strategy: dict) -> dict:
    draft = {
        "schema_version": DRAFT_SCHEMA_VERSION, "request_id": request_id,
        "research_summary": "Balanced public evidence; the edge looks intact but thin.",
        "evidence_for": ["forecast skill persists"], "evidence_against": ["liquidity is thin"],
        "uncertainties": ["seasonality"], "known_missing_data": ["no fill history"],
        "falsification_checks_performed": ["searched for contrary forecast-skill studies"],
        "limitations": ["public web only"],
        "what_would_change_the_conclusion": ["forecast skill collapse"],
        "suggested_next_research_steps": ["collect fill evidence"],
        "source_references": [{"url": "https://example.com/a", "title": "A",
                               "source_class": "reference"}],
        "confidence_label": "moderate", "strategy_assessment": strategy,
    }
    for flag in DRAFT_AUTHORITY_FLAGS:
        draft[flag] = True
    return draft


def _outcome(stdout: bytes) -> HermesInvocationOutcome:
    return HermesInvocationOutcome(
        stdout=stdout, stdout_truncated=False, stderr_byte_len=0, stderr_truncated=False,
        usage_file_bytes=_usage(), usage_file_truncated=False, exit_code=0,
        timed_out=False, launch_failed=False, duration_ms=10,
    )


class StrategyBackend(FakeHermesBackend):
    """Deterministic fake Hermes backend returning one strategy-mode draft."""

    def __init__(self, strategy: dict):
        super().__init__([_outcome(b"{}")])
        self.strategy = strategy

    def invoke(self, **kwargs):
        argv = kwargs["argv"]
        self.call_count += 1
        envelope = json.loads(argv[argv.index("-z") + 1])
        return _outcome(json.dumps(_draft(envelope["request_id"], self.strategy)).encode("utf-8"))


@dataclasses.dataclass
class World:
    lifecycle: Path
    hermes: Path
    family: object
    version: object
    other_family: object
    other_version: object
    policy: object
    allocation: object | None

    def append(self, record) -> None:
        result = append_strategy_lifecycle_record(self.lifecycle, record)
        assert result.is_valid, result.error_codes

    def snapshot(self):
        result = load_strategy_lifecycle_store(self.lifecycle)
        assert result.is_valid
        return result.snapshot

    def assess(self, strategy: dict | None = None, *, version=None, t=1_000) -> object:
        target = version or self.version
        result = sm.run_hermes_strategy_assessment(
            lifecycle_snapshot=self.snapshot(), strategy_version_id=target.strategy_version_id,
            trigger="INITIAL_ASSESSMENT", trigger_ref=None,
            subject_refs=(target.strategy_version_id, target.strategy_family_id), evidence=(),
            information_cutoff=HERMES_CUTOFF, decision_time_ns=t,
            provider_label="example-provider", model_label="example-model",
            backend=StrategyBackend(judgment() if strategy is None else strategy),
            store_path=self.hermes, clock=lambda: FIXED_CLOCK,
        )
        assert result.status == sm.STATUS_ASSESSMENT_RECORDED, result.error_code
        return result.assessment


def make_world(tmp_path: Path, *, policy=None, allocation=True, allocation_kw=None,
               pre_hermes=(), strategy: dict | None = None, hermes=True) -> World:
    base = tmp_path / "stores"
    base.mkdir(parents=True)
    lifecycle = base / "lifecycle.sqlite3"
    hermes_path = base / "hermes_strategy.sqlite3"
    assert initialize_strategy_lifecycle_store(lifecycle).is_valid
    sm.initialize_hermes_strategy_manager_store(hermes_path)
    family = build_strategy_family(family_key="gatec.family", family_label="Gate C family",
                                   created_time_ns=1, creation_provenance="unit:fixture")
    other_family = build_strategy_family(family_key="other.family", family_label="Other",
                                         created_time_ns=1, creation_provenance="unit:fixture")
    versions = [
        build_strategy_version(
            strategy_family_id=fam.strategy_family_id, parent=None, strategy_label=label,
            evidence_posture="REPEATABLE_STATISTICAL", strategy_code_identity=code,
            strategy_spec=STRATEGY_SPEC, adaptive_bounds=BOUNDS, created_time_ns=2,
            creation_provenance="unit:fixture",
        )
        for fam, label, code in ((family, "v1", "strategy_code:v1"),
                                 (other_family, "v2", "strategy_code:v2"))
    ]
    pol = policy or _policy()
    world = World(lifecycle, hermes_path, family, versions[0], other_family, versions[1], pol,
                  None)
    for record in (family, other_family, *versions, pol, _activate(pol)):
        world.append(record)
    if allocation:
        world.allocation = _allocation(world.version, pol, **(allocation_kw or {}))
        world.append(world.allocation)
    for record in pre_hermes:
        world.append(record(world) if callable(record) else record)
    if hermes:
        world.assess(strategy)
    return world


# ---------------------------------------------------------------------------
# EXEC-FEAS fixtures (fixed in-memory public payloads; no network).
# ---------------------------------------------------------------------------


_DROP = object()
BIDS = [("0.50", "100"), ("0.49", "200")]
ASKS = [("0.52", "10"), ("0.53", "20"), ("0.55", "30"), ("0.60", "40")]


def gamma_doc(**changes) -> dict:
    doc = {
        "id": GAMMA_ID, "conditionId": COND, "clobTokenIds": json.dumps([TOKEN, OTHER_TOKEN]),
        "question": "fixture?", "active": True, "closed": False, "acceptingOrders": True,
        "enableOrderBook": True, "restricted": False, "negRisk": False,
        "orderPriceMinTickSize": 0.01, "orderMinSize": 5, "feesEnabled": True,
        "feeSchedule": {"rate": 0.0333, "exponent": 1, "takerOnly": True, "rebateRate": 0.2},
        "secondsDelay": 0,
    }
    doc.update(changes)
    return doc


def book_doc(bids=BIDS, asks=ASKS, **changes) -> dict:
    doc = {
        "market": COND, "asset_id": TOKEN, "timestamp": str(BOOK_MS), "hash": "a" * 40,
        "bids": [{"price": p, "size": s} for p, s in sorted(bids, key=lambda x: float(x[0]))],
        "asks": [{"price": p, "size": s}
                 for p, s in sorted(asks, key=lambda x: float(x[0]), reverse=True)],
        "min_order_size": "5", "tick_size": "0.01", "neg_risk": False,
        "last_trade_price": "0.51",
    }
    doc.update(changes)
    return doc


def snap(gamma=None, clob=None, *, completed=T0):
    def body(doc):
        return P.SourceFetchResult("BODY", json.dumps(doc).encode("utf-8"))

    return P.build_public_venue_snapshot(
        gamma_market_id=GAMMA_ID, condition_id=COND, token_id=TOKEN,
        acquisition_started_ns=completed - 10_000_000, acquisition_completed_ns=completed,
        gamma=body(gamma_doc() if gamma is None else gamma),
        clob=body(book_doc() if clob is None else clob),
    )


def intent(world: World, *, version=None, **changes):
    values = dict(
        strategy_version=version or world.version, gamma_market_id=GAMMA_ID, condition_id=COND,
        token_id=TOKEN, side="BUY", execution_style="AGGRESSIVE_TAKER", order_type="FOK",
        requested_shares="10", price_limit="0.55", post_only=False,
        information_cutoff_ns=CUTOFF_NS, max_public_data_age_ns=AGE,
    )
    values.update(changes)
    return build_execution_intent(**values)


def passive_gtd(world: World, *, expiration_s: int, cutoff_ns: int):
    return intent(world, execution_style="PASSIVE_MAKER", order_type="GTD", post_only=True,
                  price_limit="0.51", requested_shares="10", gtd_expiration_unix_s=expiration_s,
                  information_cutoff_ns=cutoff_ns)


@dataclasses.dataclass
class Exec:
    intent: object
    snapshot: object
    assessment: object


def execution(world: World, i=None, s=None, at=T0) -> Exec:
    i = intent(world) if i is None else i
    s = snap() if s is None else s
    return Exec(i, s, assess_execution_feasibility(i, s, evaluated_at_ns=at))


def evaluate(world: World, ex: Exec | None = None, **overrides):
    ex = execution(world) if ex is None else ex
    kwargs = dict(
        lifecycle_store_path=world.lifecycle, hermes_manager_store_path=world.hermes,
        strategy_version_id=world.version.strategy_version_id, execution_intent=ex.intent,
        venue_snapshot=ex.snapshot, execution_feasibility_assessment=ex.assessment,
        evaluated_at_ns=AT,
    )
    kwargs.update(overrides)
    return evaluate_exploratory_gate_c(**kwargs)


def reasons(decision) -> tuple[str, ...]:
    assert isinstance(decision, ExploratoryGateCDecision)
    validate_exploratory_gate_c_decision(decision)
    assert (decision.status == G.PERMIT_ELIGIBLE) == (decision.reason_codes == ())
    return decision.reason_codes


@pytest.fixture
def world(tmp_path):
    return make_world(tmp_path)


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in SOURCES)


def _imports() -> set[str]:
    imported: set[str] = set()
    for path in SOURCES:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                imported.add(node.module)
    return imported


# ---------------------------------------------------------------------------
# A. Import / API / forbidden authority (R001-R003).
# ---------------------------------------------------------------------------

_AUDIT_SCRIPT = r"""
import sys, threading
STRICT = sys.argv[1] == "strict"
if STRICT:
    # Pre-load the consumed read-only dependencies (and their third-party imports) so the
    # audit isolates the import side effects of src.exploratory_gate_c itself.
    import src.strategy_lifecycle, src.execution_feasibility
    import src.research_runtime.hermes_controlled_runtime.strategy_manager
events = []
WATCH = ("socket.connect", "socket.getaddrinfo", "socket.bind", "sqlite3.connect",
         "subprocess.", "os.system", "os.posix_spawn", "os.startfile",
         "_winapi.CreateProcess", "urllib.Request", "http.client.connect")
if STRICT:
    WATCH += ("socket.", "os.putenv", "os.unsetenv")
def hook(name, args):
    if name.startswith(WATCH):
        events.append(name)
    elif name == "open" and len(args) > 1 and isinstance(args[1], str) and any(c in args[1] for c in "wax+"):
        events.append("open-write")
sys.addaudithook(hook)
before = threading.active_count()
import src.exploratory_gate_c as pkg
assert pkg.__all__
gateway = sorted(name for name in sys.modules if name.startswith("src.execution_gateway"))
print(repr((events, threading.active_count() - before, gateway)))
"""


def test_import_is_side_effect_free() -> None:
    """R001: fresh import has no network/subprocess/env-write/thread/sqlite/store creation.

    "strict" isolates this package's own import (every socket/env event is forbidden);
    "chain" also covers the pre-existing consumed import chain, whose third-party
    numerical libraries may read the hostname or set allocator env vars at import, but
    which must still open no connection, process, database or writable file.
    """
    for mode in ("strict", "chain"):
        result = subprocess.run([sys.executable, "-B", "-c", _AUDIT_SCRIPT, mode], cwd=ROOT,
                                capture_output=True, text=True, check=True, timeout=120)
        assert result.stdout.strip() == "([], 0, [])", mode
    for path in SOURCES:
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            assert not isinstance(node, (ast.Expr, ast.For, ast.While, ast.With, ast.Try)) or (
                isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
            ), path.name


def test_public_api_is_small() -> None:
    """R002: only frozen records/error/evaluator/validators/vocabularies are exported."""
    assert set(G.__all__) == {
        "DECISION_STATUSES", "ERROR_CODES", "EXPLORATORY_RISK_BAND",
        "PERMIT_COMPATIBLE_FEASIBILITY_STATUSES", "PERMIT_COMPATIBLE_HERMES_ACTIONS",
        "PERMIT_ELIGIBLE", "PERMIT_REJECTED", "REASON_CODES", "ExploratoryGateCDecision",
        "ExploratoryGateCError", "ExploratoryGateCPermit", "build_exploratory_gate_c_permit",
        "evaluate_exploratory_gate_c", "record_from_mapping",
        "validate_exploratory_gate_c_decision", "validate_exploratory_gate_c_permit",
    }
    for name in (n for n in G.__all__ if not n.isupper()):
        lowered = name.lower()
        for verb in ("sign", "submit", "cancel", "order", "live", "arm", "store", "persist",
                     "write", "save", "journal", "cache", "consume", "fetch", "credential"):
            assert verb not in lowered, name
    assert sorted(path.name for path in PACKAGE.iterdir() if path.suffix == ".py") == [
        "__init__.py", "evaluator.py", "models.py"]
    assert G.ERROR_CODES == (
        "FIELD_TYPE_INVALID", "FIELD_VALUE_INVALID", "LIMIT_EXCEEDED",
        "LIFECYCLE_STORE_INVALID", "HERMES_STORE_INVALID", "EXECUTION_INTENT_INVALID",
        "VENUE_SNAPSHOT_INVALID", "EXECUTION_ASSESSMENT_INVALID", "EXECUTION_BINDING_INVALID",
        "IDENTITY_DERIVATION_MISMATCH", "INTERNAL_VALIDATION_FAILED",
    )
    assert G.REASON_CODES == (
        "PORTFOLIO_CAPACITY_REJECTED", "ALLOCATION_REQUIRED", "EXPLORATORY_BAND_REQUIRED",
        "ALLOCATION_NOT_ACTIVE", "ACTIVE_BUDGET_REQUIRED", "HERMES_ASSESSMENT_REQUIRED",
        "HERMES_CONTEXT_STALE", "HERMES_POLICY_MISMATCH", "HERMES_ACTION_BLOCKS_NEW_EXPOSURE",
        "HERMES_TARGET_BAND_BLOCKS_NEW_EXPOSURE", "EXECUTION_STATUS_BLOCKS_NEW_EXPOSURE",
        "EXECUTION_PUBLIC_DATA_STALE", "ORDER_STYLE_NOT_ALLOWED",
        "ORDER_NOTIONAL_EXCEEDS_ALLOCATION", "ORDER_NOTIONAL_EXCEEDS_POLICY_ORDER_MAX",
        "ORDER_NOTIONAL_EXCEEDS_POLICY_MARKET_MAX", "GTD_EFFECTIVE_WINDOW_EXPIRED",
        "PERMIT_WINDOW_EMPTY",
    )
    assert G.DECISION_STATUSES == ("PERMIT_ELIGIBLE", "PERMIT_REJECTED")
    assert set(inspect.signature(evaluate_exploratory_gate_c).parameters) == {
        "lifecycle_store_path", "hermes_manager_store_path", "strategy_version_id",
        "execution_intent", "venue_snapshot", "execution_feasibility_assessment",
        "evaluated_at_ns",
    }
    assert list(inspect.signature(build_exploratory_gate_c_permit).parameters) == [
        "decision", "execution_intent"]


FORBIDDEN_SOURCE_TERMS = (
    "SecureClient", "AsyncSecureClient", "PublicClient", "private_key", "private key",
    "api_key", "mnemonic", "os.environ", "getenv", ".env", "place_order", "post_order",
    "cancel_order", "sign_order", "create_order", "execution_gateway", "GateCLivePermit",
    "GateCSession", "_GATE_C_ISSUER", "_GATE_C_EVENT_ISSUER", "A3_RESTRICTED_LIVE",
    "paper_trading", "operator_cockpit", "sqlite3", "socket", "urllib", "requests", "httpx",
    "websocket", "threading", "multiprocessing", "asyncio", "subprocess", "while True",
    "time.sleep", "geoblock", "write_text", "write_bytes", "mkdir", "append_strategy_lifecycle",
    "initialize_strategy_lifecycle_store", "initialize_hermes_strategy_manager_store",
    "run_hermes_strategy_assessment", "fetch_public_venue_snapshot", "FastAPI", "APIRouter",
)


def test_forbidden_imports_absent() -> None:
    """R003: no gateway/client/network/paper/cockpit/scheduler/persistence implementation."""
    text = source_text().lower()
    for term in FORBIDDEN_SOURCE_TERMS:
        assert term.lower() not in text, term
    assert _imports() <= {
        "__future__", "dataclasses", "decimal", "hashlib", "json", "os", "re", "typing",
        "src.execution_feasibility", "src.strategy_lifecycle",
        "src.research_runtime.hermes_controlled_runtime.strategy_manager",
    }
    for path in SOURCES:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"open", "exec", "eval", "__import__"}, path.name


# ---------------------------------------------------------------------------
# B. Verified store loading (R004-R006).
# ---------------------------------------------------------------------------


def test_lifecycle_store_loaded_verified(world, tmp_path, monkeypatch) -> None:
    """R004: lifecycle path is loaded only through the verified loader; tamper rejects."""
    calls = []
    original = E.load_strategy_lifecycle_store
    monkeypatch.setattr(E, "load_strategy_lifecycle_store",
                        lambda path: calls.append(path) or original(path))
    assert evaluate(world).status == G.PERMIT_ELIGIBLE
    assert calls == [world.lifecycle]
    monkeypatch.undo()
    missing = tmp_path / "missing.sqlite3"
    assert code_of(evaluate, world, lifecycle_store_path=missing) == "LIFECYCLE_STORE_INVALID"
    garbage = tmp_path / "garbage.sqlite3"
    garbage.write_bytes(b"not a sqlite store" * 64)
    assert code_of(evaluate, world, lifecycle_store_path=garbage) == "LIFECYCLE_STORE_INVALID"
    # Hash-chain tamper: rewrite one payload byte in the append-only table.
    tampered = tmp_path / "tampered.sqlite3"
    tampered.write_bytes(world.lifecycle.read_bytes())
    import sqlite3
    connection = sqlite3.connect(tampered)
    connection.execute("DROP TRIGGER lifecycle_records_no_update")
    connection.execute("UPDATE lifecycle_records SET payload_sha256 = ? WHERE sequence_number = 0",
                       ("0" * 64,))
    connection.commit()
    connection.close()
    assert code_of(evaluate, world, lifecycle_store_path=tampered) == "LIFECYCLE_STORE_INVALID"
    # The Hermes manager store is not an acceptable lifecycle store.
    assert code_of(evaluate, world, lifecycle_store_path=world.hermes) == "LIFECYCLE_STORE_INVALID"


def test_hermes_store_loaded_verified(world, tmp_path, monkeypatch) -> None:
    """R005: Hermes path is loaded only via the verified loader; no fabricated snapshot."""
    calls = []
    original = E.load_hermes_strategy_manager_store
    monkeypatch.setattr(E, "load_hermes_strategy_manager_store",
                        lambda path: calls.append(path) or original(path))
    assert evaluate(world).status == G.PERMIT_ELIGIBLE
    assert calls == [world.hermes]
    monkeypatch.undo()
    garbage = tmp_path / "garbage.sqlite3"
    garbage.write_bytes(b"\x00" * 4096)
    assert code_of(evaluate, world, hermes_manager_store_path=garbage) == "HERMES_STORE_INVALID"
    assert code_of(evaluate, world,
                   hermes_manager_store_path=tmp_path / "absent.sqlite3") == "HERMES_STORE_INVALID"
    assert code_of(evaluate, world, hermes_manager_store_path=world.lifecycle) == (
        "HERMES_STORE_INVALID")
    # Caller-fabricated snapshots are not accepted as authority in place of a store path.
    hermes_snapshot = sm.load_hermes_strategy_manager_store(world.hermes)
    assert code_of(evaluate, world, hermes_manager_store_path=hermes_snapshot) == (
        "FIELD_TYPE_INVALID")
    assert code_of(evaluate, world, lifecycle_store_path=world.snapshot()) == "FIELD_TYPE_INVALID"
    assert code_of(evaluate, world, lifecycle_store_path=b"bytes.sqlite3") == "FIELD_TYPE_INVALID"


def test_store_paths_never_persist_or_echo(tmp_path) -> None:
    """R006: decision/permit/errors contain no local path or raw store error."""
    marker = "PATHMARKER_secret_dir"
    nested = tmp_path / marker
    nested.mkdir()
    w = make_world(nested)
    decision = evaluate(w)
    permit = build_exploratory_gate_c_permit(decision, execution_intent=execution(w).intent)
    for record in (decision, permit):
        text = json.dumps(record.to_mapping())
        assert marker not in text and str(tmp_path) not in text
        assert "sqlite3" not in text and "path" not in " ".join(record.to_mapping())
    missing = nested / "nope.sqlite3"
    for kwargs in ({"lifecycle_store_path": missing}, {"hermes_manager_store_path": missing}):
        with pytest.raises(ExploratoryGateCError) as excinfo:
            evaluate(w, **kwargs)
        assert marker not in str(excinfo.value) and marker not in repr(excinfo.value)
        assert str(excinfo.value) in M.ERROR_CODES


# ---------------------------------------------------------------------------
# C. Strategy / policy / allocation / capacity (R007-R011).
# ---------------------------------------------------------------------------


def test_target_strategy_and_policy_resolve(world) -> None:
    """R007: StrategyVersion, active policy and allocation derive from verified replay."""
    decision = evaluate(world)
    snapshot = world.snapshot()
    assert decision.status == G.PERMIT_ELIGIBLE and reasons(decision) == ()
    assert decision.strategy_version_id == world.version.strategy_version_id
    assert decision.strategy_family_id == world.family.strategy_family_id
    assert decision.active_policy_id == world.policy.policy_id == snapshot.active_policy_id
    assert decision.allocation_id == world.allocation.allocation_id
    assert decision.lifecycle_store_head_entry_hash == snapshot.store_head_entry_hash
    hermes = sm.load_hermes_strategy_manager_store(world.hermes)
    assert decision.hermes_manager_store_head_entry_hash == hermes.store_head_entry_hash
    unknown = "strategyversion:sha256:" + "f" * 64
    assert code_of(evaluate, world, strategy_version_id=unknown) == "FIELD_VALUE_INVALID"
    assert code_of(evaluate, world, strategy_version_id="strategyversion:x") == (
        "FIELD_VALUE_INVALID")
    assert code_of(evaluate, world, strategy_version_id=None) == "FIELD_TYPE_INVALID"


@pytest.mark.parametrize(
    "allocation_kw, expected",
    [
        ({"band": "PAPER", "budget": "0"},
         ("EXPLORATORY_BAND_REQUIRED", "ACTIVE_BUDGET_REQUIRED",
          "ORDER_NOTIONAL_EXCEEDS_ALLOCATION")),
        ({"band": "VALIDATED_LIVE"}, ("EXPLORATORY_BAND_REQUIRED",)),
        ({"band": "MATURE_LIVE"}, ("EXPLORATORY_BAND_REQUIRED",)),
        ({"budget": "0"}, ("ACTIVE_BUDGET_REQUIRED", "ORDER_NOTIONAL_EXCEEDS_ALLOCATION")),
        ({"valid_from": T0 + 60_000_000_000}, ("ALLOCATION_NOT_ACTIVE",)),
        ({"valid_until": T0}, ("ALLOCATION_NOT_ACTIVE", "PERMIT_WINDOW_EMPTY")),
    ],
)
def test_exploratory_allocation_required(tmp_path, allocation_kw, expected) -> None:
    """R008: PAPER/VALIDATED/MATURE, inactive or zero-budget allocation rejects."""
    w = make_world(tmp_path, allocation_kw=allocation_kw)
    decision = evaluate(w)
    assert decision.status == G.PERMIT_REJECTED
    assert reasons(decision) == expected
    assert decision.allocation_id == w.allocation.allocation_id


def test_missing_allocation_rejects(tmp_path) -> None:
    """R008: a missing allocation rejects and the target capacity result is absent."""
    w = make_world(tmp_path, allocation=False)
    decision = evaluate(w)
    assert reasons(decision) == ("PORTFOLIO_CAPACITY_REJECTED", "ALLOCATION_REQUIRED")
    assert decision.allocation_id is None
    assert decision.target_strategy_capacity_status is None
    assert decision.target_strategy_capacity_reason_codes == ()


def test_portfolio_capacity_required(tmp_path) -> None:
    """R009: global and target capacity must both be PORTFOLIO_CAPACITY_VALID."""
    # Target-local restriction blocks target capacity (applied before the Hermes run).
    w = make_world(tmp_path / "a", pre_hermes=(lambda w: _pause(w.version),))
    decision = evaluate(w)
    assert reasons(decision) == ("PORTFOLIO_CAPACITY_REJECTED",)
    assert decision.target_strategy_capacity_status == "PORTFOLIO_CAPACITY_REJECTED"
    # An unrelated strategy's blocked active budget rejects global capacity only.
    w2 = make_world(tmp_path / "b")
    w2.append(_allocation(w2.other_version, w2.policy, budget="20"))
    w2.append(_health(w2.other_version, "NEW", "QUARANTINED", t=200))
    decision2 = evaluate(w2)
    assert reasons(decision2) == ("PORTFOLIO_CAPACITY_REJECTED",)
    assert decision2.portfolio_capacity_status == "PORTFOLIO_CAPACITY_REJECTED"
    assert decision2.target_strategy_capacity_status == "PORTFOLIO_CAPACITY_VALID"
    # The full lifecycle head is a hard currentness key; the Hermes context is not stale.
    assert decision2.lifecycle_store_head_entry_hash != evaluate(make_world(tmp_path / "c")) \
        .lifecycle_store_head_entry_hash


def test_capacity_reasons_preserved(tmp_path) -> None:
    """R010: STRAT-LIFE reasons are preserved verbatim, not re-derived or duplicated."""
    w = make_world(tmp_path / "a", pre_hermes=(lambda w: _pause(w.version),))
    decision = evaluate(w)
    capacity = E.evaluate_portfolio_capacity(w.snapshot(), AT)
    assert decision.portfolio_capacity_reason_codes == capacity.reason_codes == (
        "RESTRICTION_BLOCKS_ACTIVE_RISK",)
    target = capacity.strategy_result(w.version.strategy_version_id)
    assert decision.target_strategy_capacity_reason_codes == target.reason_codes
    assert not set(decision.reason_codes) & set(CAPACITY_REASON_CODES)
    # Policy expiry is inherited as POLICY_EXPIRED (global rejection).
    pol = _policy(expires=T0 + 500_000_000)
    w2 = make_world(tmp_path / "b", policy=pol, allocation_kw={"valid_until": T0 + 500_000_000})
    decision2 = evaluate(w2)
    assert decision2.portfolio_capacity_reason_codes == ("POLICY_EXPIRED",)
    assert "PORTFOLIO_CAPACITY_REJECTED" in reasons(decision2)


def test_policy_is_never_mutated(world) -> None:
    """R011: evaluation appends nothing and alters no policy/allocation/health/restriction."""
    stores = sorted(world.lifecycle.parent.iterdir())
    before = {path: _file_digest(path) for path in stores}
    snapshot_before = world.snapshot()
    decision = evaluate(world)
    build_exploratory_gate_c_permit(decision, execution_intent=execution(world).intent)
    evaluate(world, evaluated_at_ns=PUBLIC_DEADLINE)
    assert sorted(world.lifecycle.parent.iterdir()) == stores
    assert {path: _file_digest(path) for path in stores} == before
    after = world.snapshot()
    assert after.store_head_entry_hash == snapshot_before.store_head_entry_hash
    assert after.current_allocation_by_strategy_version == (
        snapshot_before.current_allocation_by_strategy_version)
    assert after.current_health_by_strategy_version == (
        snapshot_before.current_health_by_strategy_version)


# ---------------------------------------------------------------------------
# D. Hermes latest compatible assessment (R012-R016).
# ---------------------------------------------------------------------------


def test_latest_hermes_assessment_selected_from_store(tmp_path) -> None:
    """R012: the latest same-strategy assessment is used; an older one cannot be chosen."""
    w = make_world(tmp_path / "a")
    first = sm.load_hermes_strategy_manager_store(w.hermes).latest_assessment_id(
        w.version.strategy_version_id)
    reduce = w.assess(judgment(lifecycle_action="REDUCE", risk_direction="DECREASE"), t=2_000)
    decision = evaluate(w)
    assert decision.hermes_assessment_id == reduce.assessment_id != first
    assert reasons(decision) == ("HERMES_ACTION_BLOCKS_NEW_EXPOSURE",)
    # Reverse order: a newer CONTINUE supersedes an older REDUCE.
    w2 = make_world(tmp_path / "b",
                    strategy=judgment(lifecycle_action="REDUCE", risk_direction="DECREASE"))
    assert reasons(evaluate(w2)) == ("HERMES_ACTION_BLOCKS_NEW_EXPOSURE",)
    latest = w2.assess(judgment(), t=2_000)
    decision2 = evaluate(w2)
    assert decision2.status == G.PERMIT_ELIGIBLE
    assert decision2.hermes_assessment_id == latest.assessment_id
    # A later assessment for an unrelated strategy changes the store head but not the target.
    w2.assess(judgment(), version=w2.other_version, t=3_000)
    decision3 = evaluate(w2)
    assert decision3.status == G.PERMIT_ELIGIBLE
    assert decision3.hermes_assessment_id == latest.assessment_id
    assert decision3.hermes_manager_store_head_entry_hash != (
        decision2.hermes_manager_store_head_entry_hash)
    # No API parameter can supply a caller-selected (historical) assessment.
    params = set(inspect.signature(evaluate_exploratory_gate_c).parameters)
    assert not any("hermes_assessment" in name or "snapshot" == name for name in params)
    # No assessment at all rejects.
    w3 = make_world(tmp_path / "c", hermes=False)
    decision4 = evaluate(w3)
    assert reasons(decision4) == ("HERMES_ASSESSMENT_REQUIRED",)
    assert decision4.hermes_assessment_id is None
    assert decision4.hermes_manager_store_head_entry_hash is None


def test_hermes_context_and_policy_must_match(tmp_path) -> None:
    """R013: assessment policy and strategy-local lifecycle fingerprint must be current."""
    w = make_world(tmp_path / "a")
    w.append(_health(w.version, "NEW", "WATCH", t=200))
    assert reasons(evaluate(w)) == ("HERMES_CONTEXT_STALE",)
    # A replacement active policy invalidates allocation binding and the Hermes policy.
    w2 = make_world(tmp_path / "b")
    replacement = _policy(label="Replacement envelope", predecessor=w2.policy.policy_id,
                          created=300)
    w2.append(replacement)
    w2.append(_activate(replacement, previous=w2.policy.policy_id, t=400))
    decision = evaluate(w2)
    assert {"HERMES_CONTEXT_STALE", "HERMES_POLICY_MISMATCH", "ALLOCATION_REQUIRED",
            "PORTFOLIO_CAPACITY_REJECTED"} <= set(reasons(decision))
    assert decision.active_policy_id == replacement.policy_id


@pytest.mark.parametrize(
    "strategy, eligible",
    [
        (judgment(), True),
        (judgment(recommended_health_state="WATCH"), True),
        (judgment(lifecycle_action="SCALE", risk_direction="INCREASE"), True),
        (judgment(lifecycle_action="SCALE", risk_direction="INCREASE",
                  target_risk_band="VALIDATED_LIVE"), True),
        (judgment(lifecycle_action="REDUCE", risk_direction="DECREASE"), False),
        (judgment(lifecycle_action="ADAPT", risk_direction="UNCHANGED",
                  adaptation_recommendation={"kind": "PARAMETER_UPDATE",
                                             "summary": "Shorten the lookback window.",
                                             "parameter_updates": {"lookback": 4}}), False),
        (judgment(lifecycle_action="PAPER", risk_direction="PAPER_ONLY",
                  target_risk_band="PAPER"), False),
        (judgment(lifecycle_action="QUARANTINE", risk_direction="ZERO",
                  recommended_health_state="QUARANTINED"), False),
        (judgment(lifecycle_action="RETIRE", risk_direction="ZERO",
                  recommended_health_state="RETIRED"), False),
    ],
)
def test_continue_and_scale_only(tmp_path, strategy, eligible) -> None:
    """R014: CONTINUE/UNCHANGED and SCALE/INCREASE only; other actions reject."""
    w = make_world(tmp_path, strategy=strategy)
    decision = evaluate(w)
    if eligible:
        assert decision.status == G.PERMIT_ELIGIBLE
        permit = build_exploratory_gate_c_permit(decision, execution_intent=execution(w).intent)
        # SCALE never widens the hard allocation: the permit is the exact intent notional.
        assert permit.authorized_order_notional_usd == "5.5"
        assert permit.allocation_id == w.allocation.allocation_id
    else:
        assert decision.status == G.PERMIT_REJECTED
        assert "HERMES_ACTION_BLOCKS_NEW_EXPOSURE" in reasons(decision)


@pytest.mark.parametrize("health", ["QUARANTINED", "RETIRED"])
def test_hermes_health_blocks(tmp_path, health) -> None:
    """R015: a QUARANTINED/RETIRED recommendation blocks even CONTINUE/UNCHANGED."""
    w = make_world(tmp_path, strategy=judgment(recommended_health_state=health))
    assert reasons(evaluate(w)) == ("HERMES_ACTION_BLOCKS_NEW_EXPOSURE",)


@pytest.mark.parametrize(
    "band, expected",
    [
        ("PAPER", ("HERMES_TARGET_BAND_BLOCKS_NEW_EXPOSURE",)),
        (None, ()), ("EXPLORATORY_LIVE", ()), ("VALIDATED_LIVE", ()), ("MATURE_LIVE", ()),
    ],
)
def test_hermes_target_paper_blocks(tmp_path, band, expected) -> None:
    """R016: target PAPER blocks; other targets never widen the current allocation."""
    w = make_world(tmp_path, strategy=judgment(target_risk_band=band))
    decision = evaluate(w)
    assert reasons(decision) == expected
    if not expected:
        permit = build_exploratory_gate_c_permit(decision, execution_intent=execution(w).intent)
        assert permit.allocation_id == w.allocation.allocation_id
        assert permit.authorized_order_notional_usd == decision.intent_order_notional_usd


# ---------------------------------------------------------------------------
# E. Exact EXEC-FEAS binding (R017-R020).
# ---------------------------------------------------------------------------


def _forge_assessment(assessment, **changes):
    values = {field.name: getattr(assessment, field.name)
              for field in dataclasses.fields(assessment)}
    values.update(changes)
    values["execution_feasibility_assessment_id"] = FM._PENDING_ID
    return ExecutionFeasibilityAssessment(**values)


def test_exec_records_validate_and_bind(world) -> None:
    """R017: intent binds the current StrategyVersion; records exact-type and round-trip."""
    ex = execution(world)
    assert evaluate(world, ex).status == G.PERMIT_ELIGIBLE
    # Intent bound to another StrategyVersion.
    other = execution(world, intent(world, version=world.other_version))
    assert code_of(evaluate, world, other) == "EXECUTION_BINDING_INVALID"
    # Wrong types.
    assert code_of(evaluate, world, execution_intent=ex.intent.to_mapping()) == (
        "EXECUTION_INTENT_INVALID")
    assert code_of(evaluate, world, venue_snapshot=ex.snapshot.to_mapping()) == (
        "VENUE_SNAPSHOT_INVALID")
    assert code_of(evaluate, world, execution_feasibility_assessment=None) == (
        "EXECUTION_ASSESSMENT_INVALID")
    # In-memory tamper of frozen records fails the exact round trip.
    for record, field, value, code in (
        (ex.intent, "requested_shares", "11", "EXECUTION_INTENT_INVALID"),
        (ex.snapshot, "book_hash", "b" * 40, "VENUE_SNAPSHOT_INVALID"),
        (ex.assessment, "status", "LIMITED", "EXECUTION_ASSESSMENT_INVALID"),
    ):
        tampered = dataclasses.replace(record)
        object.__setattr__(tampered, field, value)
        name = {"EXECUTION_INTENT_INVALID": "execution_intent",
                "VENUE_SNAPSHOT_INVALID": "venue_snapshot",
                "EXECUTION_ASSESSMENT_INVALID": "execution_feasibility_assessment"}[code]
        assert code_of(evaluate, world, ex, **{name: tampered}) == code
    # Assessment for a different snapshot / intent.
    other_snapshot = snap(clob=book_doc(hash="c" * 40))
    mismatched = Exec(ex.intent, ex.snapshot,
                      assess_execution_feasibility(ex.intent, other_snapshot, evaluated_at_ns=T0))
    assert code_of(evaluate, world, mismatched) == "EXECUTION_BINDING_INVALID"
    other_intent = intent(world, requested_shares="12")
    mismatched2 = Exec(other_intent, ex.snapshot, ex.assessment)
    assert code_of(evaluate, world, mismatched2) == "EXECUTION_BINDING_INVALID"


def test_exec_assessment_must_recompute_exactly(world) -> None:
    """R018: a self-consistent assessment that does not re-derive is rejected."""
    ex = execution(world)
    forged = _forge_assessment(ex.assessment, best_bid="0.49", spread="0.03")
    assert forged != ex.assessment
    assert code_of(evaluate, world, Exec(ex.intent, ex.snapshot, forged)) == (
        "EXECUTION_BINDING_INVALID")
    # Re-evaluation uses the assessment's own recorded time, not the Gate-C time.
    later = execution(world, at=T0 + 500_000_000)
    assert evaluate(world, later).execution_feasibility_assessment_id == (
        later.assessment.execution_feasibility_assessment_id)
    # Gate-C evaluation time cannot precede the feasibility evaluation time.
    assert code_of(evaluate, world, later, evaluated_at_ns=T0) == "FIELD_VALUE_INVALID"


def test_feasible_and_limited_can_qualify(world) -> None:
    """R019: FEASIBLE and LIMITED qualify; LIMITED diagnostics are preserved."""
    feasible = evaluate(world)
    assert feasible.execution_feasibility_status == "FEASIBLE"
    assert feasible.status == G.PERMIT_ELIGIBLE
    limited_ex = execution(world, s=snap(gamma=gamma_doc(secondsDelay=3)))
    assert limited_ex.assessment.status == "LIMITED"
    limited = evaluate(world, limited_ex)
    assert limited.status == G.PERMIT_ELIGIBLE
    assert limited.execution_feasibility_status == "LIMITED"
    assert limited.execution_feasibility_diagnostic_codes == limited_ex.assessment.diagnostic_codes
    assert "MARKETABLE_ORDER_DELAY" in limited.execution_feasibility_diagnostic_codes
    permit = build_exploratory_gate_c_permit(limited, execution_intent=limited_ex.intent)
    assert permit.feasibility_status == "LIMITED"
    assert permit.feasibility_diagnostic_codes == limited_ex.assessment.diagnostic_codes
    # No automatic size haircut.
    assert permit.requested_shares == limited_ex.intent.requested_shares


def test_inconclusive_and_not_feasible_reject(world) -> None:
    """R020: INCONCLUSIVE and NOT_FEASIBLE cannot create a permit."""
    stale_book = snap(clob=book_doc(timestamp=str(BOOK_MS - 10_000)))
    inconclusive = execution(world, s=stale_book)
    assert inconclusive.assessment.status == "INCONCLUSIVE"
    decision = evaluate(world, inconclusive)
    assert "EXECUTION_STATUS_BLOCKS_NEW_EXPOSURE" in reasons(decision)
    assert code_of(build_exploratory_gate_c_permit, decision,
                   execution_intent=inconclusive.intent) == "FIELD_VALUE_INVALID"
    not_feasible = execution(world, intent(world, requested_shares="15", price_limit="0.52"))
    assert not_feasible.assessment.status == "NOT_FEASIBLE"
    decision2 = evaluate(world, not_feasible)
    assert reasons(decision2) == ("EXECUTION_STATUS_BLOCKS_NEW_EXPOSURE",)
    assert "FOK_INSUFFICIENT_VISIBLE_DEPTH" in decision2.execution_feasibility_diagnostic_codes
    # CLOB unavailable: no book timestamp, so public mechanics are stale/unknown too.
    unavailable = P.build_public_venue_snapshot(
        gamma_market_id=GAMMA_ID, condition_id=COND, token_id=TOKEN,
        acquisition_started_ns=T0 - 10_000_000, acquisition_completed_ns=T0,
        gamma=P.SourceFetchResult("BODY", json.dumps(gamma_doc()).encode("utf-8")),
        clob=P.SourceFetchResult("UNAVAILABLE"),
    )
    decision3 = evaluate(world, execution(world, s=unavailable))
    assert decision3.public_mechanics_deadline_ns is None
    assert {"EXECUTION_STATUS_BLOCKS_NEW_EXPOSURE", "EXECUTION_PUBLIC_DATA_STALE"} <= set(
        reasons(decision3))


# ---------------------------------------------------------------------------
# F. Exact-intent policy ceilings (R021-R024).
# ---------------------------------------------------------------------------


def test_order_style_policy_gate(tmp_path) -> None:
    """R021: execution_style must be allowed by the active PortfolioAuthorityPolicy."""
    w = make_world(tmp_path, policy=_policy(styles=("PASSIVE_MAKER",)))
    assert reasons(evaluate(w)) == ("ORDER_STYLE_NOT_ALLOWED",)
    passive = intent(w, execution_style="PASSIVE_MAKER", order_type="GTC", post_only=True,
                     price_limit="0.51")
    assert evaluate(w, execution(w, passive)).status == G.PERMIT_ELIGIBLE


def test_notional_matches_exec_assessment(world) -> None:
    """R022: exact Decimal requested_shares*price_limit equals the EXEC-FEAS notional."""
    ex = execution(world, intent(world, requested_shares="9.123456789012345678",
                                 price_limit="0.55"))
    decision = evaluate(world, ex)
    assert decision.intent_order_notional_usd == ex.assessment.intent_notional_at_price_limit_usd
    assert decision.intent_order_notional_usd == "5.0179012339567901229"
    assert M.intent_order_notional("9.123456789012345678", "0.55") == M.Decimal(
        "5.0179012339567901229")


def test_notional_never_exceeds_allocation(tmp_path) -> None:
    """R023: exact intent notional above the active strategy budget rejects."""
    w = make_world(tmp_path, allocation_kw={"budget": "5"})
    assert reasons(evaluate(w)) == ("ORDER_NOTIONAL_EXCEEDS_ALLOCATION",)
    w_equal = make_world(tmp_path / "eq", allocation_kw={"budget": "5.5"})
    assert evaluate(w_equal).status == G.PERMIT_ELIGIBLE


def test_notional_never_exceeds_policy_order_or_market_caps(tmp_path) -> None:
    """R024: exact intent notional above max_order_notional_usd / max_per_market_usd rejects."""
    w = make_world(tmp_path / "a")
    big = execution(w, intent(w, requested_shares="25"))  # 13.75 > order max 10
    assert reasons(evaluate(w, big)) == ("ORDER_NOTIONAL_EXCEEDS_POLICY_ORDER_MAX",)
    w2 = make_world(tmp_path / "b",
                    policy=_policy(max_per_market_usd="10", max_order_notional_usd="10"))
    assert reasons(evaluate(w2, execution(w2, intent(w2, requested_shares="25")))) == (
        "ORDER_NOTIONAL_EXCEEDS_POLICY_ORDER_MAX", "ORDER_NOTIONAL_EXCEEDS_POLICY_MARKET_MAX")
    w3 = make_world(tmp_path / "c", policy=_policy(max_order_notional_usd="5.5"))
    assert evaluate(w3).status == G.PERMIT_ELIGIBLE


# ---------------------------------------------------------------------------
# G. Freshness / permit window (R025-R028).
# ---------------------------------------------------------------------------


def test_public_mechanics_deadline(world) -> None:
    """R025: deadline = book_timestamp_ns + max_public_data_age_ns; at/after expiry rejects."""
    decision = evaluate(world)
    assert decision.public_mechanics_deadline_ns == PUBLIC_DEADLINE
    assert decision.permit_valid_until_ns == PUBLIC_DEADLINE
    assert evaluate(world, evaluated_at_ns=PUBLIC_DEADLINE - 1).status == G.PERMIT_ELIGIBLE
    for at in (PUBLIC_DEADLINE, PUBLIC_DEADLINE + 1):
        assert reasons(evaluate(world, evaluated_at_ns=at)) == (
            "EXECUTION_PUBLIC_DATA_STALE", "PERMIT_WINDOW_EMPTY")


def test_permit_uses_earliest_policy_allocation_public_deadline(tmp_path) -> None:
    """R026: valid_until is the exact minimum of available public/policy/allocation deadlines."""
    allocation_end = AT + 1_000_000_000
    w = make_world(tmp_path / "a", allocation_kw={"valid_until": allocation_end})
    assert evaluate(w).permit_valid_until_ns == allocation_end < PUBLIC_DEADLINE
    policy_end = AT + 500_000_000
    w2 = make_world(tmp_path / "b", policy=_policy(expires=policy_end),
                    allocation_kw={"valid_until": policy_end})
    decision = evaluate(w2)
    assert decision.permit_valid_until_ns == policy_end
    permit = build_exploratory_gate_c_permit(decision, execution_intent=execution(w2).intent)
    assert permit.valid_until_ns == policy_end and permit.issued_at_ns == AT
    late_allocation = make_world(tmp_path / "c", allocation_kw={"valid_until": T0 * 2})
    assert evaluate(late_allocation).permit_valid_until_ns == PUBLIC_DEADLINE


def test_gtd_effective_deadline_included(world) -> None:
    """R027: GTD adds expiration*1e9-60s to the minimum; an expired window rejects."""
    early_cutoff = T0 - 1_000_000_000_000
    expiration_s = T0 // 1_000_000_000 + 61  # effective deadline T0 + 1 s
    gtd = passive_gtd(world, expiration_s=expiration_s, cutoff_ns=early_cutoff)
    ex = execution(world, gtd)
    assert ex.assessment.status == "FEASIBLE"
    effective = expiration_s * 1_000_000_000 - 60_000_000_000
    assert effective == T0 + 1_000_000_000 < PUBLIC_DEADLINE
    ok = evaluate(world, ex, evaluated_at_ns=T0 + 500_000_000)
    assert ok.status == G.PERMIT_ELIGIBLE
    assert ok.gtd_effective_deadline_ns == effective == ok.permit_valid_until_ns
    permit = build_exploratory_gate_c_permit(ok, execution_intent=gtd)
    assert permit.gtd_expiration_unix_s == expiration_s and permit.valid_until_ns == effective
    expired = evaluate(world, ex, evaluated_at_ns=effective)
    assert reasons(expired) == ("GTD_EFFECTIVE_WINDOW_EXPIRED", "PERMIT_WINDOW_EMPTY")
    # Non-GTD intents have no GTD deadline.
    assert evaluate(world).gtd_effective_deadline_ns is None


def test_no_arbitrary_ttl(world) -> None:
    """R028: no WP175 10-minute arm/qualification TTL or synthetic TTL is used."""
    text = source_text()
    for marker in ("600_000_000_000", "600000000000", "timedelta", "TTL_NS", "ttl_ns",
                   "minutes", "time.time", "datetime"):
        assert marker not in text, marker
    decision = evaluate(world)
    assert decision.permit_valid_until_ns == min(PUBLIC_DEADLINE, T0 * 10)
    assert decision.permit_valid_until_ns - decision.evaluated_at_ns == PUBLIC_DEADLINE - AT


# ---------------------------------------------------------------------------
# H. Decision / permit identity and tamper rejection (R029-R034).
# ---------------------------------------------------------------------------


def _example(rule_id: str) -> dict:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    for item in spec["examples"]["items"]:
        if rule_id in item["derivation_rule_ids"]:
            return item["input"]
    raise AssertionError(rule_id)


def _expected_id(mapping: dict, id_field: str, prefix: str) -> str:
    preimage = {key: value for key, value in mapping.items() if key != id_field}
    text = json.dumps(preimage, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)
    return prefix + hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_decision_content_id_roundtrip(world) -> None:
    """R029: decision id re-derives over every non-id field; the exact loader rejects tamper."""
    decision = evaluate(world)
    mapping = decision.to_mapping()
    assert decision.decision_id == _expected_id(mapping, "decision_id", M.DECISION_ID_PREFIX)
    assert ExploratoryGateCDecision.from_mapping(mapping) == decision
    assert G.record_from_mapping(json.loads(json.dumps(mapping))) == decision
    example = _example("exploratory_gate_c_decision_content_id")
    loaded = G.record_from_mapping(example)
    assert loaded.decision_id == example["decision_id"] == _expected_id(
        example, "decision_id", M.DECISION_ID_PREFIX)
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    rule = spec["identity_derivations"]["items"][0]
    assert sorted(rule["source_paths"]) == sorted(k for k in mapping if k != "decision_id")
    for key in mapping:
        if key == "decision_id":
            continue
        tampered = dict(mapping)
        value = tampered[key]
        if isinstance(value, bool):
            tampered[key] = not value
        elif isinstance(value, int):
            tampered[key] = value + 1
        elif isinstance(value, list):
            tampered[key] = ["PERMIT_WINDOW_EMPTY"]
        elif value is None:
            tampered[key] = "x"
        else:
            tampered[key] = value[:-1] + ("0" if value[-1] != "0" else "1")
        with pytest.raises(ExploratoryGateCError):
            ExploratoryGateCDecision.from_mapping(tampered)
    tampered = dict(mapping, decision_id=M.DECISION_ID_PREFIX + "0" * 64)
    assert code_of(ExploratoryGateCDecision.from_mapping, tampered) == (
        "IDENTITY_DERIVATION_MISMATCH")
    in_memory = dataclasses.replace(decision)
    object.__setattr__(in_memory, "evaluated_at_ns", AT + 1)
    assert code_of(validate_exploratory_gate_c_decision, in_memory) == (
        "IDENTITY_DERIVATION_MISMATCH")
    assert code_of(validate_exploratory_gate_c_decision, mapping) == "FIELD_TYPE_INVALID"
    assert code_of(ExploratoryGateCDecision.from_mapping, {**mapping, "extra": 1}) == (
        "FIELD_VALUE_INVALID")


def test_decision_rejected_is_still_canonical(tmp_path) -> None:
    """R030: ineligible valid state yields a content-addressed PERMIT_REJECTED decision."""
    w = make_world(tmp_path, allocation_kw={"band": "PAPER", "budget": "0"},
                   strategy=judgment(lifecycle_action="REDUCE", risk_direction="DECREASE"))
    decision = evaluate(w, evaluated_at_ns=PUBLIC_DEADLINE)
    assert decision.status == G.PERMIT_REJECTED
    assert reasons(decision) == (
        "EXPLORATORY_BAND_REQUIRED", "ACTIVE_BUDGET_REQUIRED",
        "HERMES_ACTION_BLOCKS_NEW_EXPOSURE", "EXECUTION_PUBLIC_DATA_STALE",
        "ORDER_NOTIONAL_EXCEEDS_ALLOCATION", "PERMIT_WINDOW_EMPTY",
    )
    assert list(decision.reason_codes) == sorted(decision.reason_codes,
                                                 key=G.REASON_CODES.index)
    assert decision.decision_id == _expected_id(decision.to_mapping(), "decision_id",
                                                M.DECISION_ID_PREFIX)
    assert evaluate(w, evaluated_at_ns=PUBLIC_DEADLINE) == decision  # deterministic


def test_decision_bounds_and_no_echo(world) -> None:
    """R031: reason arrays/strings are bounded and closed; invalid raw values never echo."""
    mapping = evaluate(world).to_mapping()
    secret = "SECRET-VALUE-0xdeadbeef"
    cases = [
        dict(mapping, reason_codes=["PERMIT_WINDOW_EMPTY", "PERMIT_WINDOW_EMPTY"],
             status="PERMIT_REJECTED"),
        dict(mapping, reason_codes=["PERMIT_WINDOW_EMPTY", "PORTFOLIO_CAPACITY_REJECTED"],
             status="PERMIT_REJECTED"),
        dict(mapping, reason_codes=[secret], status="PERMIT_REJECTED"),
        dict(mapping, reason_codes=["X"] * 1_000, status="PERMIT_REJECTED"),
        dict(mapping, execution_feasibility_diagnostic_codes=["CLIENT_LATENCY_UNKNOWN"] * 65),
        dict(mapping, strategy_version_id=secret),
        dict(mapping, intent_order_notional_usd="5.50"),
        dict(mapping, intent_order_notional_usd="1" * 200),
        dict(mapping, intent_order_notional_usd=5.5),
        dict(mapping, evaluated_at_ns=True),
        dict(mapping, evaluated_at_ns=2**63),
        dict(mapping, status="PERMIT_ELIGIBLE", reason_codes=["PERMIT_WINDOW_EMPTY"]),
        dict(mapping, status=secret),
        dict(mapping, portfolio_capacity_reason_codes=["POLICY_EXPIRED"]),
        dict(mapping, target_strategy_capacity_status=None),
        dict(mapping, permit_valid_until_ns=PUBLIC_DEADLINE + 1),
        dict(mapping, schema_version="2.0.0"),
    ]
    for case in cases:
        with pytest.raises(ExploratoryGateCError) as excinfo:
            ExploratoryGateCDecision.from_mapping(case)
        assert secret not in str(excinfo.value) and secret not in repr(excinfo.value)
        assert str(excinfo.value) in M.ERROR_CODES


def test_permit_only_from_eligible_decision(tmp_path) -> None:
    """R032: the permit builder rejects PERMIT_REJECTED and tampered decisions."""
    w = make_world(tmp_path, allocation_kw={"budget": "5"})
    rejected = evaluate(w)
    ex = execution(w)
    assert code_of(build_exploratory_gate_c_permit, rejected, execution_intent=ex.intent) == (
        "FIELD_VALUE_INVALID")
    w2 = make_world(tmp_path / "ok")
    eligible = evaluate(w2)
    tampered = dataclasses.replace(eligible)
    object.__setattr__(tampered, "intent_order_notional_usd", "50")
    assert code_of(build_exploratory_gate_c_permit, tampered,
                   execution_intent=execution(w2).intent) == "IDENTITY_DERIVATION_MISMATCH"
    assert code_of(build_exploratory_gate_c_permit, eligible.to_mapping(),
                   execution_intent=execution(w2).intent) == "FIELD_TYPE_INVALID"


def test_permit_is_exact_intent_only(world) -> None:
    """R033: permit copies exact market/order scope; notional is the exact intent notional."""
    ex = execution(world)
    decision = evaluate(world, ex)
    permit = build_exploratory_gate_c_permit(decision, execution_intent=ex.intent)
    for name in ("gamma_market_id", "condition_id", "token_id", "side", "execution_style",
                 "order_type", "requested_shares", "price_limit", "post_only",
                 "gtd_expiration_unix_s"):
        assert getattr(permit, name) == getattr(ex.intent, name), name
    for name in ("strategy_version_id", "strategy_family_id", "lifecycle_store_head_entry_hash",
                 "active_policy_id", "allocation_id", "hermes_assessment_id",
                 "execution_intent_id", "venue_snapshot_id",
                 "execution_feasibility_assessment_id"):
        assert getattr(permit, name) == getattr(decision, name), name
    assert permit.decision_id == decision.decision_id
    assert permit.authorized_order_notional_usd == "5.5" == decision.intent_order_notional_usd
    assert permit.exact_intent_only is True
    # A different intent (even with the same strategy) cannot be substituted.
    other = intent(world, requested_shares="9")
    assert code_of(build_exploratory_gate_c_permit, decision, execution_intent=other) == (
        "EXECUTION_BINDING_INVALID")
    assert code_of(build_exploratory_gate_c_permit, decision,
                   execution_intent=ex.intent.to_mapping()) == "EXECUTION_INTENT_INVALID"
    # The record itself rejects a widened authorized notional.
    widened = dict(permit.to_mapping(), authorized_order_notional_usd="10")
    assert code_of(ExploratoryGateCPermit.from_mapping, widened) == "FIELD_VALUE_INVALID"


def test_permit_content_id_roundtrip(world) -> None:
    """R034: permit id re-derives over every non-id field; the exact loader rejects tamper."""
    ex = execution(world)
    permit = build_exploratory_gate_c_permit(evaluate(world, ex), execution_intent=ex.intent)
    mapping = permit.to_mapping()
    assert permit.permit_id == _expected_id(mapping, "permit_id", M.PERMIT_ID_PREFIX)
    assert validate_exploratory_gate_c_permit(permit) is permit
    assert G.record_from_mapping(json.loads(json.dumps(mapping))) == permit
    example = _example("exploratory_gate_c_permit_content_id")
    assert G.record_from_mapping(example).permit_id == example["permit_id"] == _expected_id(
        example, "permit_id", M.PERMIT_ID_PREFIX)
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    rule = spec["identity_derivations"]["items"][1]
    assert sorted(rule["source_paths"]) == sorted(k for k in mapping if k != "permit_id")
    for key, value in (("valid_until_ns", permit.valid_until_ns + 1),
                       ("issued_at_ns", permit.issued_at_ns + 1),
                       ("token_id", OTHER_TOKEN), ("side", "SELL"),
                       ("decision_id", M.DECISION_ID_PREFIX + "1" * 64)):
        assert code_of(ExploratoryGateCPermit.from_mapping, dict(mapping, **{key: value})) == (
            "IDENTITY_DERIVATION_MISMATCH")
    in_memory = dataclasses.replace(permit)
    object.__setattr__(in_memory, "requested_shares", "100")
    assert code_of(validate_exploratory_gate_c_permit, in_memory) == "FIELD_VALUE_INVALID"
    assert code_of(validate_exploratory_gate_c_permit, mapping) == "FIELD_TYPE_INVALID"
    assert code_of(G.record_from_mapping, dict(mapping, schema_id="other")) == (
        "FIELD_VALUE_INVALID")


# ---------------------------------------------------------------------------
# I. Runtime revalidation / non-authority / legacy separation (R035-R038).
# ---------------------------------------------------------------------------


def test_runtime_revalidation_flags_are_fixed_true(world) -> None:
    """R035: account/access/reconciliation/runtime-identity revalidation cannot be false."""
    ex = execution(world)
    decision = evaluate(world, ex)
    permit = build_exploratory_gate_c_permit(decision, execution_intent=ex.intent)
    for record in (decision, permit):
        for flag in M.REVALIDATION_FIELDS:
            assert getattr(record, flag) is True
            assert code_of(type(record).from_mapping,
                           dict(record.to_mapping(), **{flag: False})) == "FIELD_VALUE_INVALID"
            with pytest.raises(ExploratoryGateCError):
                dataclasses.replace(record, **{flag: False})
    assert decision.canonical_hard_eligibility_decision is True
    assert code_of(ExploratoryGateCDecision.from_mapping,
                   dict(decision.to_mapping(), canonical_hard_eligibility_decision=False)) == (
        "FIELD_VALUE_INVALID")
    assert code_of(ExploratoryGateCPermit.from_mapping,
                   dict(permit.to_mapping(), exact_intent_only=False)) == "FIELD_VALUE_INVALID"


def test_no_account_or_access_claims(world) -> None:
    """R036: no balance/allowance/positions/open-orders/loss/drawdown/geoblock/credential."""
    ex = execution(world)
    decision = evaluate(world, ex)
    permit = build_exploratory_gate_c_permit(decision, execution_intent=ex.intent)
    forbidden = ("balance", "allowance", "position", "open_order", "loss", "drawdown",
                 "geoblock", "country", "ip_address", "credential_ref", "private", "wallet",
                 "api_key", "secret", "passphrase", "signature", "account_ref")
    for record in (decision, permit):
        for name in record.to_mapping():
            if name.startswith(("no_", "requires_")):
                continue
            assert not any(term in name for term in forbidden), name
        values = json.dumps([v for k, v in record.to_mapping().items()
                             if not k.startswith(("no_", "requires_"))]).lower()
        assert "account:public-scope-1" not in values
        for term in forbidden:
            assert term not in values, term


def test_no_live_order_authority_flags_fixed_true(world) -> None:
    """R037: credential/signing/order/transport/live non-authority booleans are fixed true."""
    ex = execution(world)
    decision = evaluate(world, ex)
    permit = build_exploratory_gate_c_permit(decision, execution_intent=ex.intent)
    assert M.NON_AUTHORITY_FIELDS == (
        "no_credential_authority", "no_signing_authority", "no_order_authority",
        "no_execution_transport_authority", "no_live_authority")
    for record in (decision, permit):
        for flag in M.NON_AUTHORITY_FIELDS:
            assert getattr(record, flag) is True
            for bad in (False, None, 1, "true"):
                with pytest.raises(ExploratoryGateCError):
                    type(record).from_mapping(dict(record.to_mapping(), **{flag: bad}))


def test_legacy_gate_c_not_imported() -> None:
    """R038: no src.execution_gateway import and no legacy WP175 permit/session/A3 internals."""
    for module in _imports():
        assert not module.startswith("src.execution_gateway"), module
        assert "paper" not in module and "cockpit" not in module, module
    text = source_text()
    for name in ("GateCLivePermit", "GateCSession", "_GATE_C_ISSUER", "_GATE_C_EVENT_ISSUER",
                 "A3_RESTRICTED_LIVE", "arm(", "execution_gateway"):
        assert name not in text, name
    for name in dir(G):
        assert not name.startswith(("GateC", "A3")), name


# ---------------------------------------------------------------------------
# J. Spec example truth and canonicalization.
# ---------------------------------------------------------------------------


def test_spec_examples_and_canonicalization_truth() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    for item in spec["examples"]["items"]:
        assert item["expected_valid"] is True
        record = G.record_from_mapping(item["input"])
        assert record.to_mapping() == item["input"]
        canonical = item["input"]
        rule = next(r for r in spec["identity_derivations"]["items"]
                    if r["rule_id"] in item["derivation_rule_ids"])
        assert rule["canonicalization"]["sort_keys"] is True
        assert record.record_id == _expected_id(canonical, rule["target_path"], rule["prefix"])
    assert M.canonical_json_bytes({"b": None, "a": [2, 1], "é": "ü"}) == (
        '{"a":[2,1],"b":null,"é":"ü"}'.encode("utf-8"))
    for bad in (1.5, float("nan"), {1: "x"}, M.Decimal("1")):
        with pytest.raises(ExploratoryGateCError):
            M.canonical_json_bytes(bad)
