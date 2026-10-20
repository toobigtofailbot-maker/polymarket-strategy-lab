"""S10-HERMES-LIVE-BRIDGE-01 R001-R006: offline protocol tests only.

Real verified STRAT-LIFE / Hermes / Alpha stores, the genuine run_oauth_attempt with its
child runner patched (the AUTO-01 ``_oauth_world`` pattern), real Gate C permits and the
unmodified LiveOrchestrator.preflight over injected read-only seams. No provider, OAuth,
credential, account, network, order or capital activity; every PASS here is PROTOCOL_ONLY.
"""
import ast
import copy
import dataclasses
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from src.research_runtime import live_preflight_bridge as bridge
from tests.research_runtime import test_autonomous_opportunity_cycle as auto
from tests.exploratory_gate_c import test_exploratory_gate_c as X

ROOT = Path(__file__).resolve().parents[2]
SIGNER, WALLET, RELEASE = "0x" + "a" * 40, "0x" + "b" * 40, "c" * 40
FRESH_BOOK = X.book_doc(timestamp=str(X.BOOK_MS + 1_500))
GAMMA = X.gamma_doc(orderMinSize=1)


def host_doc(**changes):
    doc = {
        "schema_id": "polymarket-execution-host-currentness", "schema_version": "1.0.0",
        "status": "EXECUTION_HOST_CURRENT", "verification_mode": "strict",
        "host_instance_id": "pmhost-v1:" + "1" * 64, "boot_instance_id": "pmboot-v1:" + "2" * 64,
        "bound_release_sha": RELEASE, "active_release_sha": RELEASE, "release_manifest_sha256": "3" * 64,
        "ntp_state": "synchronized", "firewall_state": "ssh_only_inbound", "persistent_state": "present",
    }
    doc.update(changes)
    return doc


class Ctx:
    """One witnessed (or not) OAuth choice over the native AUTO-01 world plus offline seams."""

    def __init__(self, tmp_path, monkeypatch, proposal=lambda trade: trade, *, mode="real", hermes=True,
                 **report_changes):
        from src.execution_gateway import live_orch as L
        from src.research_runtime.hermes_controlled_runtime import oauth_plan_stage_b as op
        from tests.research_runtime.hermes_controlled_runtime import test_oauth_plan_stage_b as fixture
        from tests.research_runtime.hermes_controlled_runtime.test_tool_free_stage_b import PIN_ROOT, RECORDED_REPORT
        self.tmp, self.op = tmp_path, op
        self.w, args, trade, assessments = auto.world(tmp_path, hermes=hermes)
        trade.update(requested_shares="8")  # inside the frozen $5 single-order envelope
        lineage = [dict(candidate_id=m["candidate_id"], hermes_assessment_id=a.assessment_id,
                        context_sha256=a.strategy_lifecycle_context_sha256, active_policy_id=trade["active_policy_id"])
                   for m, a in zip(args["candidate_menu"], assessments)]
        self.request = op.build_oauth_request(
            surface_report=RECORDED_REPORT, candidate_menu=args["candidate_menu"], lineage=lineage,
            information_cutoff_ns=args["information_cutoff_ns"], issued_at_ns=args["information_cutoff_ns"],
            deadline_ns=args["deadline_ns"])
        self.choice = dict(proposal(dict(trade)), produced_at_ns=self.request.issued_at_ns,
                           expires_at_ns=self.request.deadline_ns)
        report = fixture.dispatch(self.request, text=json.dumps(self.choice), mode=mode, **report_changes)
        monkeypatch.setattr(op.OAuthPlanTransport, "_run_child",
                            lambda self, phase, extra, timeout_s: copy.deepcopy(report))
        self.transport = op.OAuthPlanTransport(PIN_ROOT, tmp_path / "creds", mode=mode,
                                               mock=None if mode == "real" else {"responses": {}})
        self.eligibility = op.evaluate_preflight(fixture.preflight(), attestation=dict(fixture.ATTEST),
                                                 checked_at_ns=args["information_cutoff_ns"])
        self.result = self.attempt()
        self.args = dict(args, venue_snapshots=(X.snap(gamma=GAMMA),))  # pre-choice menu evidence
        self.now = X.AT + 1_000
        self.host, self.blocked, self.gamma, self.book = host_doc(), False, GAMMA, FRESH_BOOK
        self.fetches, self.on_fetch, self.fetch_error = [], None, None
        self.config = L.LiveOrchConfig(
            state_root=tmp_path / "state", expected_signer=SIGNER, expected_wallet=WALLET,
            lifecycle_store_path=args["lifecycle_store_path"], hermes_store_path=args["hermes_manager_store_path"],
            host=L.HostCurrentnessConfig(repository_root=tmp_path, binding_file=tmp_path / "b.json",
                                         active_release=tmp_path / "r", unit_dir=tmp_path / "u", ssh_port=22,
                                         expected_release_sha=RELEASE))

    def attempt(self):
        ticks = iter(range(self.request.information_cutoff_ns + 1, self.request.information_cutoff_ns + 100))
        return self.op.run_oauth_attempt(self.request, eligibility=self.eligibility, transport=self.transport,
                                         journal_dir=self.tmp / "oauth", clock_ns=lambda: next(ticks))

    def clock(self):
        self.now += 1_000_000
        return self.now

    def fetch(self, **identity):
        self.fetches.append(identity)
        if self.on_fetch is not None:
            self.on_fetch(self)
        if self.fetch_error is not None:
            raise self.fetch_error
        return X.snap(gamma=self.gamma, clob=self.book, completed=self.clock())

    def geoblock(self):
        from src.execution_gateway.gate_c import GateCGeoblockProof
        return GateCGeoblockProof.from_response({"blocked": self.blocked, "country": "ZZ"}, observed_time_ns=self.now)

    def run(self, result=..., **changes):
        kwargs = dict(live_config=self.config, alpha_registry_path=self.args["alpha_registry_path"],
                      candidate_menu=self.args["candidate_menu"], menu_venue_snapshots=self.args["venue_snapshots"],
                      evaluated_at_ns=self.args["evaluated_at_ns"],
                      information_cutoff_ns=self.args["information_cutoff_ns"], deadline_ns=self.args["deadline_ns"],
                      clock_ns=self.clock, host_currentness=lambda _config: dict(self.host), geoblock=self.geoblock,
                      venue_fetcher=self.fetch)
        kwargs.update(changes)
        return bridge.run_live_preflight_bridge(self.result if result is ... else result, **kwargs)


def zero_side_effects(receipt, *, fetches=0, preflight=0, permit=0):
    calls = receipt["calls"]
    assert calls == dict(provider=0, oauth_dispatch=0, venue_fetch=fetches, permit_built=permit, preflight=preflight,
                         canary=0, reconcile=0, private_session=0, order=0), calls
    assert receipt["no_order"] is True and receipt["no_live_authority"] is True
    assert receipt["exposure_posture"] == "NO_NEW_EXPOSURE" and receipt["account_readiness"] == "NOT_EVALUATED"
    assert receipt["receipt_id"].startswith("livepreflightbridge:sha256:")


def blocked(receipt, *codes, stage=None):
    assert receipt["status"] == "BLOCKED" and receipt["permit_id"] is None, receipt["reason_codes"]
    assert receipt["reason_codes"][:len(codes)] == list(codes), receipt["reason_codes"]
    if stage is not None:
        assert receipt["stage"] == stage, receipt["stage"]


def passed(receipt):
    assert receipt["status"] == "PASS" and receipt["stage"] == "COMPLETE", receipt["reason_codes"]
    assert receipt["preflight_status"] == receipt["preflight_code"] == "PREFLIGHT_PASS"
    zero_side_effects(receipt, fetches=2, preflight=1, permit=1)


def test_live_bridge_witness_binding(tmp_path, monkeypatch):
    """R001: only a non-replayed witnessed OAuth choice bound to the exact menu and clocks admits."""
    ctx = Ctx(tmp_path / "ok", monkeypatch)
    assert ctx.op.is_witnessed_result(ctx.result)
    good = ctx.run()
    passed(good)
    assert good["real_origin_record_id"] == ctx.result.origin["record_id"]
    assert good["requested_choice_sha256"] == hashlib.sha256(ctx.result.output_bytes).hexdigest()
    # The frozen Stage B label is preserved and never elevated; injected success is protocol proof only.
    assert good["choice_proof_level"] == "SYNTHETIC_ONLY"
    assert good["choice_proof_level_meaning"] == "FROZEN_STAGE_B_LABEL_NOT_LIVE_VENUE_EVIDENCE"
    assert good["evidence_class"] == "OFFLINE_TEST_ONLY" and good["claim"] == "PROTOCOL_ONLY"
    assert good["choice_origin"] == "OFFLINE_TEST_ONLY" and good["choice_origin_limit"] == "PROVIDER_REPORTED_NOT_CRYPTOGRAPHIC"
    replace = dataclasses.replace
    forged = (None, object(), "TRADE", replace(ctx.result, replayed=True), replace(ctx.result, _witness=None),
              replace(ctx.result, output_bytes=json.dumps(dict(ctx.choice, requested_shares="7")).encode()),
              replace(ctx.result, origin=dict(ctx.result.origin, real_origin="REAL_ORIGIN_VERIFIED", status="X")),
              ctx.attempt())  # journal replay of the consumed single attempt
    assert forged[-1].replayed is True
    for result in forged:
        receipt = ctx.run(result)
        blocked(receipt, "REAL_ORIGIN_UNVERIFIED", stage="WITNESS")
        zero_side_effects(receipt)
        assert receipt["choice_origin"] == "UNVERIFIED" and receipt["auto01_receipt_id"] is None
    for name, kwargs in (("mock", dict(mode="mock")), ("nousage", dict(usage=None))):
        other = Ctx(tmp_path / name, monkeypatch, **kwargs)
        assert other.result.status == other.op.VALID_OUTPUT and not other.op.is_witnessed_result(other.result)
        blocked(other.run(), "REAL_ORIGIN_UNVERIFIED")
    # Menu and clock bindings are enforced by the reused AUTO-01 admission.
    for changes, code in ((dict(candidate_menu=list(reversed(ctx.args["candidate_menu"]))), "REAL_ORIGIN_BINDING_MISMATCH"),
                          (dict(evaluated_at_ns=ctx.args["information_cutoff_ns"] + 1), "REAL_ORIGIN_CLOCK_CONFLICT"),
                          (dict(information_cutoff_ns=ctx.args["information_cutoff_ns"] - 1), "VENUE_AFTER_CUTOFF")):
        receipt = ctx.run(**changes)
        blocked(receipt, code, stage="CHOICE_AND_STRATEGY")
        zero_side_effects(receipt)
    # A model claim of a stronger proof level is rejected natively, never relabelled.
    claimed = Ctx(tmp_path / "claim", monkeypatch, lambda t: dict(t, proof_level="REAL_PROVIDER"))
    blocked(claimed.run(), "PRODUCER_UNVERIFIED")


def test_live_bridge_native_strategy_currentness(tmp_path, monkeypatch):
    """R002: only the replay-verified latest canonical assessment under current policy/allocation."""
    ctx = Ctx(tmp_path / "ok", monkeypatch)
    good = ctx.run()
    passed(good)
    latest = ctx.w.assess  # bound method kept for the stale case below
    assert good["strategy_assessment"] == "VALIDATED_CANONICAL_ONLY"
    assert good["strategy_origin_proof"] == "LABELS_ONLY_NOT_PROOF_OF_AUTHENTICATED_INFERENCE"
    assert good["hermes_assessment_id"] == ctx.choice["hermes_assessment_id"]
    assert good["hermes_run_record_id"].startswith("hermesstrategyrun:sha256:")
    # Missing, stale-by-age and forged lineage: STRATEGY_ASSESSMENT_UNAVAILABLE before any venue read.
    missing = Ctx(tmp_path / "missing", monkeypatch, hermes=False)
    for receipt, code in ((missing.run(), "HERMES_ASSESSMENT_REQUIRED"),
                          (ctx.run(max_hermes_age_ns=1), "HERMES_ASSESSMENT_STALE"),
                          (Ctx(tmp_path / "forged", monkeypatch, lambda t: dict(t, hermes_assessment_id=(
                              "hermesstrategyassessment:sha256:" + "f" * 64))).run(), "HERMES_LINEAGE_STALE_OR_FORGED")):
        blocked(receipt, "STRATEGY_ASSESSMENT_UNAVAILABLE", code, stage="CHOICE_AND_STRATEGY")
        zero_side_effects(receipt)
        assert receipt["strategy_assessment"] is None
    # A newer assessment supersedes the one the choice bound.
    latest(t=X.T0 - 500_000)
    blocked(ctx.run(), "STRATEGY_ASSESSMENT_UNAVAILABLE", "HERMES_LINEAGE_STALE_OR_FORGED")
    # An assessment whose run record cannot be resolved is not accepted (no receipt is synthesized).
    from src.research_runtime.hermes_controlled_runtime import strategy_manager as sm
    fresh = Ctx(tmp_path / "norun", monkeypatch)
    original = sm.load_hermes_strategy_manager_store
    monkeypatch.setattr(sm, "load_hermes_strategy_manager_store",
                        lambda path: dataclasses.replace(original(path), run_records=()))
    receipt = fresh.run()
    blocked(receipt, "STRATEGY_ASSESSMENT_UNAVAILABLE", "STRATEGY_RUN_RECORD_MISMATCH", stage="NATIVE_STRATEGY")
    zero_side_effects(receipt)
    monkeypatch.setattr(sm, "load_hermes_strategy_manager_store", original)
    # Stores moving between admission and the fresh Gate C bind no mixed evidence.
    moved = Ctx(tmp_path / "moved", monkeypatch)
    moved.on_fetch = lambda c: (c.w.assess(t=X.T0 - 400_000), setattr(c, "on_fetch", None))
    receipt = moved.run()
    blocked(receipt, "STORE_CHANGED", stage="FRESH_NATIVE_PERMIT")
    zero_side_effects(receipt, fetches=1)
    # Revoked policy / expired allocation fail natively at the fresh Gate C.
    expired = Ctx(tmp_path / "revoked", monkeypatch)
    expired.w.append(X.build_portfolio_policy_receipt(action="REVOKE", policy_id=expired.w.policy.policy_id,
        previous_active_policy_id=expired.w.policy.policy_id, human_authorization_ref="synthetic:revoke",
        created_time_ns=2000))
    receipt = expired.run()
    assert receipt["status"] == "BLOCKED" and receipt["calls"]["preflight"] == 0


@pytest.mark.parametrize("action", ["NO_TRADE", "PAUSE", "REASSESS"])
def test_live_bridge_abstains_without_preflight(tmp_path, monkeypatch, action):
    """R003: abstention yields zero permit, venue read and preflight; malformed output stops."""
    def fail(*_a, **_k):
        raise AssertionError("seam must not be reached")

    abstain = Ctx(tmp_path / "abstain", monkeypatch, lambda t: {k: t[k] for k in auto.cycle._CLOCK_KEYS} | {"action": action})
    receipt = abstain.run(clock_ns=fail, host_currentness=fail, geoblock=fail, venue_fetcher=fail)
    assert receipt["status"] == "ABSTAIN" and receipt["action"] == action and receipt["reason_codes"] == [action]
    assert receipt["choice_proof_level"] == "SYNTHETIC_ONLY" and receipt["claim"] == "PROTOCOL_ONLY"
    assert receipt["permit_id"] is None and receipt["preflight_status"] is None and receipt["fresh_venue_snapshot_id"] is None
    zero_side_effects(receipt)
    for bad in (lambda t: dict(t, action="BUY"), lambda t: dict(t, extra="x"), lambda t: dict(t, requested_shares=8),
                lambda t: {k: t[k] for k in auto.cycle._CLOCK_KEYS} | {"action": action, "candidate_id": "x"}):
        other = Ctx(tmp_path / f"bad{len(list((tmp_path).iterdir()))}", monkeypatch, bad)
        receipt = other.run(clock_ns=fail, host_currentness=fail, geoblock=fail, venue_fetcher=fail)
        assert receipt["status"] == "BLOCKED" and receipt["action"] is None
        zero_side_effects(receipt)


def test_live_bridge_rederives_native_gate_c(tmp_path, monkeypatch):
    """R004: one fresh native BUY intent / venue / feasibility / Gate C permit; AUTO-01 preview never reused."""
    import src.exploratory_gate_c as gate
    from src.research_runtime.hermes_controlled_runtime.autonomous_feedback import admit_oauth_choice
    ctx = Ctx(tmp_path / "ok", monkeypatch)
    rest = {k: v for k, v in ctx.args.items() if k != "choice"}
    preview = admit_oauth_choice(ctx.result, **rest)
    assert preview["status"] == "ELIGIBLE_PREVIEW"
    built = []
    original = gate.build_exploratory_gate_c_permit
    monkeypatch.setattr(gate, "build_exploratory_gate_c_permit",
                        lambda decision, **kw: built.append(decision) or original(decision, **kw))
    receipt = ctx.run()
    passed(receipt)
    menu_snapshot = ctx.args["venue_snapshots"][0]
    fresh = built[-1]
    assert fresh.venue_snapshot_id == receipt["fresh_venue_snapshot_id"] != menu_snapshot.venue_snapshot_id
    assert receipt["permit_id"] != preview["preview_permit"]["permit_id"]
    assert receipt["execution_intent_id"] != preview["execution_intent"]["execution_intent_id"]
    assert receipt["gate_c_decision_id"] == fresh.decision_id and receipt["auto01_preview"] == "NEVER_PROMOTED"
    assert receipt["preflight_details"]["venue_snapshot_id"] not in (menu_snapshot.venue_snapshot_id,
                                                                      receipt["fresh_venue_snapshot_id"])
    # SELL is never a first-canary candidate: stopped before any venue read.
    sell = Ctx(tmp_path / "sell", monkeypatch, lambda t: dict(t, side="SELL"))
    receipt = sell.run()
    blocked(receipt, "SIDE_UNSUPPORTED_FIRST_CANARY")
    zero_side_effects(receipt)
    # Fresh venue failures: stale book, identity drift, synthetic pre-cutoff snapshot, fetch failure.
    from src.execution_feasibility import ExecutionFeasibilityError
    cases = (
        (dict(book=X.book_doc(timestamp=str(X.BOOK_MS - 60_000))), "GATE_C_REJECTED"),  # fresh fetch, stale book
        (dict(fetch_error=ExecutionFeasibilityError("SOURCE_UNAVAILABLE")), "VENUE_SNAPSHOT_UNAVAILABLE"),
    )
    for index, (changes, code) in enumerate(cases):
        case = Ctx(tmp_path / f"venue{index}", monkeypatch)
        for key, value in changes.items():
            setattr(case, key, value)
        receipt = case.run()
        blocked(receipt, code, stage="FRESH_NATIVE_PERMIT")
        zero_side_effects(receipt, fetches=1)
    stale = Ctx(tmp_path / "precut", monkeypatch)
    stale.fetch = lambda **kw: stale.fetches.append(kw) or ctx.args["venue_snapshots"][0]
    blocked(stale.run(venue_fetcher=stale.fetch), "VENUE_SNAPSHOT_INVALID")
    other = Ctx(tmp_path / "drift", monkeypatch)
    other.gamma = dict(GAMMA, clobTokenIds=json.dumps([X.OTHER_TOKEN, X.TOKEN]))
    other.book = X.book_doc(asset_id=X.OTHER_TOKEN, timestamp=str(X.BOOK_MS + 1_500))
    assert other.run()["status"] == "BLOCKED"
    # Policy ceilings are re-decided natively on the fresh venue, never inherited.
    large = Ctx(tmp_path / "large", monkeypatch, lambda t: dict(t, requested_shares="100"))
    receipt = large.run()
    blocked(receipt, "GATE_C_REJECTED")
    assert "ORDER_NOTIONAL_EXCEEDS_POLICY_ORDER_MAX" in receipt["native_reasons"]["gate_c"]
    zero_side_effects(receipt, fetches=1)


def test_live_bridge_preflight_fail_closed(tmp_path, monkeypatch):
    """R005: native preflight blocks host, geoblock, venue, fee, envelope, ledger and window failures."""
    cases = (
        (dict(host=host_doc(ntp_state="unsynchronized")), "HOST_NOT_CURRENT"),
        (dict(host=host_doc(active_release_sha="d" * 40)), "HOST_NOT_CURRENT"),
        (dict(blocked=True), "ACCESS_NOT_ELIGIBLE"),
    )
    for index, (changes, code) in enumerate(cases):
        ctx = Ctx(tmp_path / f"host{index}", monkeypatch)
        for key, value in changes.items():
            setattr(ctx, key, value)
        receipt = ctx.run()
        blocked(receipt, "PREFLIGHT_BLOCKED", code, stage="PREFLIGHT")
        assert receipt["preflight_status"] == "BLOCKED" and receipt["preflight_code"] == code
        zero_side_effects(receipt, fetches=1, preflight=1, permit=1)
        assert not (ctx.tmp / "state").exists()
    # The preflight's own fresh venue read drifts after the bridge's permit was built.
    def drift(gamma=None, book=None):
        def change(c):
            if len(c.fetches) == 2:
                c.gamma, c.book = gamma or c.gamma, book or c.book
        return change
    no_fee = dict(GAMMA)
    no_fee.pop("feesEnabled")
    no_fee.pop("feeSchedule", None)
    for index, (hook, code) in enumerate(((drift(gamma=dict(GAMMA, closed=True)), "MARKET_NOT_ELIGIBLE"),
                                          (drift(gamma=no_fee), "FEE_CONFIGURATION_UNKNOWN"),
                                          (drift(book=X.book_doc(min_order_size="9", timestamp=str(X.BOOK_MS + 1_500))),
                                           "MINIMUM_ORDER_NOT_MET"))):
        ctx = Ctx(tmp_path / f"venue{index}", monkeypatch)
        ctx.on_fetch = hook
        receipt = ctx.run()
        blocked(receipt, "PREFLIGHT_BLOCKED", code, stage="PREFLIGHT")
        zero_side_effects(receipt, fetches=2, preflight=1, permit=1)
    # The frozen $5 single-order worst case is enforced by native preflight, not widened.
    big = Ctx(tmp_path / "big", monkeypatch, lambda t: dict(t, requested_shares="10"))
    blocked(big.run(), "PREFLIGHT_BLOCKED", "SINGLE_ORDER_LIMIT_EXCEEDED")
    # An unhealthy LIVE-ORCH ledger blocks; preflight never repairs or writes it.
    ledger = Ctx(tmp_path / "ledger", monkeypatch)
    from src.execution_gateway import live_orch as L
    path = L.canonical_live_orch_store_path(ledger.config.state_root, WALLET)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not a ledger")
    receipt = ledger.run()
    assert receipt["status"] == "BLOCKED" and receipt["stage"] == "PREFLIGHT" and receipt["calls"]["preflight"] == 1
    assert path.read_bytes() == b"not a ledger"
    # Currentness window: an expired choice never reaches preflight.
    late = Ctx(tmp_path / "late", monkeypatch)
    late.now = late.args["deadline_ns"]
    receipt = late.run()
    blocked(receipt, "CHOICE_WINDOW_EXPIRED", stage="FRESH_NATIVE_PERMIT")
    zero_side_effects(receipt)


def test_live_bridge_no_side_effects_or_claim_inflation(tmp_path, monkeypatch):
    """R006: no OAuth/provider/account/sign/create/cancel/reconcile/daemon or store mutation; honest labels."""
    from src.execution_gateway import live_orch as L
    ctx = Ctx(tmp_path, monkeypatch)
    stores = [ctx.args[k] for k in ("lifecycle_store_path", "hermes_manager_store_path", "alpha_registry_path")]
    journal = sorted((tmp_path / "oauth").iterdir())
    digests = lambda: [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in stores + journal]  # noqa: E731
    before = digests()

    def deny(*_a, **_k):
        raise AssertionError("forbidden surface reached")

    monkeypatch.setattr(ctx.op.OAuthPlanTransport, "_run_child", deny)
    monkeypatch.setattr(ctx.op.OAuthPlanTransport, "_send", deny)
    monkeypatch.setattr(ctx.op, "run_oauth_attempt", deny)
    for name in ("canary", "reconcile", "_open_session", "_truth", "_reconcile_pass"):
        monkeypatch.setattr(L.LiveOrchestrator, name, deny)
    receipt = ctx.run()
    passed(receipt)
    assert before == digests() and not (tmp_path / "state").exists()
    text = json.dumps(receipt)
    assert str(tmp_path) not in text and "creds" not in text and "eyJ" not in text
    assert receipt["claim"] == "PROTOCOL_ONLY" and receipt["evidence_class"] == "OFFLINE_TEST_ONLY"
    # Without injected seams the class is native, but a non-witnessed input still stops before any I/O.
    native = bridge.run_live_preflight_bridge(dataclasses.replace(ctx.result, replayed=True), live_config=ctx.config,
        alpha_registry_path=stores[2], candidate_menu=ctx.args["candidate_menu"],
        menu_venue_snapshots=ctx.args["venue_snapshots"], evaluated_at_ns=X.AT,
        information_cutoff_ns=X.T0, deadline_ns=ctx.args["deadline_ns"])
    blocked(native, "REAL_ORIGIN_UNVERIFIED")
    assert native["evidence_class"] == "NATIVE_READ_ONLY_SEAMS" and native["choice_origin"] == "UNVERIFIED"
    zero_side_effects(native)
    # Source: lazy native imports, only .preflight on the orchestrator, no OAuth transport use.
    source = Path(bridge.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    top = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert {a.name for n in top for a in n.names} == {"hashlib", "json"}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert "preflight" in attrs and not attrs & {"canary", "reconcile", "_send", "_run_child", "run_oauth_attempt",
                                               "_open_session", "acquire"}
    assert not re.search(r"(_OBSERVED|_witness)", source) and "api_key" not in source.lower()
    script = '''import sys
def guard(name, args):
    if name.startswith(("socket.", "subprocess.", "sqlite3.connect", "os.system", "os.putenv", "urllib.")):
        raise RuntimeError(name)
sys.addaudithook(guard)
import src.research_runtime.live_preflight_bridge
assert "src.execution_gateway.live_orch" not in sys.modules
print("IMPORT_NO_IO_PASS")
'''
    result = subprocess.run([sys.executable, "-B", "-c", script], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0 and "IMPORT_NO_IO_PASS" in result.stdout, result.stderr
