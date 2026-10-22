"""S10-LIVE-CANARY-01 R002-R007: offline protocol tests of the attended composer only.

Real verified STRAT-LIFE / Hermes / Alpha stores (the AUTO-01 world), the genuine
run_oauth_attempt with a patched child (the ``_oauth_world`` pattern), the merged bridge,
real Gate C permits, a real native LIVE-ORCH ledger and LiveOrchestrator.canary over the
offline Harness fake venue. No provider, OAuth, credential, account, network, order or
capital activity; every result here is OFFLINE_TEST_ONLY / PROTOCOL_ONLY.
"""
import ast
import calendar
import copy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

import src.execution_gateway.live_canary as lc
import src.execution_gateway.live_orch as L
from src.execution_gateway.gate_b import GateBSecretLease, WalletSessionLock
from src.execution_gateway.gate_c import GateCGeoblockProof
from src.execution_gateway.gateway import ProtectedExecutionGateway
from src.research_runtime import live_preflight_bridge as bridge
from src.research_runtime.hermes_controlled_runtime import oauth_plan_stage_b as op
from src.research_runtime.hermes_controlled_runtime import tool_free_stage_b as tf
from tests.execution_gateway import test_live_orch as T
from tests.exploratory_gate_c import test_exploratory_gate_c as X
from tests.research_runtime import test_autonomous_opportunity_cycle as auto
from tests.research_runtime.hermes_controlled_runtime import test_oauth_plan_stage_b as fixture
from tests.research_runtime.hermes_controlled_runtime.test_tool_free_stage_b import PIN_ROOT, RECORDED_REPORT

ROOT = Path(__file__).resolve().parents[2]
SIGNER, WALLET, RELEASE = T.SIGNER, T.WALLET, T.RELEASE
GAMMA = X.gamma_doc(orderMinSize=1)
FRESH_BOOK = X.book_doc(timestamp=str(X.BOOK_MS + 1_500))
PHRASE = L.LIVE_ORCH_CONFIRMATION_PHRASE
HOUR_NS = 3600 * 1_000_000_000


def utc(ns: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ns // 1_000_000_000))


def ledger_path(root: Path) -> Path:
    return L.canonical_live_orch_store_path(root, WALLET)


def bootstrap(root: Path) -> str:
    """Section 7(i) steps 1-5: parent 0700, native create once, close, read-only head."""
    path = ledger_path(root)
    path.parent.mkdir(parents=True, mode=0o700)
    assert not path.exists()
    ProtectedExecutionGateway.create(path, created_time_ns=X.T0 - 10).close()
    return lc.read_ledger_head(path)


class Canary:
    """One AUTO-01 world, a bootstrapped native ledger, a Stage A artifact and offline seams."""

    def __init__(self, tmp_path, monkeypatch, proposal=lambda trade: trade, *, hermes=True, allocation=True):
        self.tmp, self.mp = tmp_path, monkeypatch
        tmp_path.mkdir(parents=True, exist_ok=True)
        self.w, args, trade, _assessments = auto.world(tmp_path / "stores", hermes=hermes, allocation=allocation)
        trade.update(requested_shares="8")  # inside the frozen $5 single-order envelope
        self.trade = proposal(dict(trade))
        self.now = X.AT
        self.host, self.blocked, self.gamma, self.book = T.host_doc(), False, GAMMA, FRESH_BOOK
        self.records, self.oauth_calls, self.factory_calls, self.journals = [], 0, 0, 0
        self.typed = None  # None: type the correct line; callable(canary) -> line
        self.on_confirm = None
        self.venue = T.FakeVenue()
        self.venue.on_post = T._rest
        self.secret_requests = 0
        self.canary_args = []
        (tmp_path / "pin").mkdir()
        (tmp_path / "creds").mkdir()
        self.state = tmp_path / "state"
        self.head = bootstrap(self.state)
        self.case = dict(
            schema_id="polymarket-live-canary-case", schema_version="1.0.0",
            lifecycle_store_path=str(args["lifecycle_store_path"]), hermes_store_path=str(args["hermes_manager_store_path"]),
            alpha_registry_path=str(args["alpha_registry_path"]), live_orch_state_root=str(self.state),
            oauth_pin_root=str(tmp_path / "pin"), oauth_credential_dir=str(tmp_path / "creds"),
            oauth_journal_dir=str(tmp_path / "journal"), stage_a_authorization_path=str(tmp_path / "stage_a.json"),
            public_signer_address=SIGNER, deposit_wallet_address=WALLET,
            host=dict(repository_root=str(tmp_path), binding_file=str(tmp_path / "b.json"),
                      active_release=str(tmp_path / "r"), unit_dir=str(tmp_path / "u"), ssh_port=22,
                      expected_release_sha=RELEASE),
            plan_usage_attestation=dict(fixture.ATTEST), candidate_menu=args["candidate_menu"],
            max_hermes_age_s=3600, stage_a_authorization_sha256="0" * 64)
        self.stage = dict(
            schema_id="polymarket-live-canary-stage-a", schema_version="1.0.0", release_sha=RELEASE,
            execution_host_binding_sha256=lc.execution_host_binding_sha256(self.case),
            live_orch_state_root=str(self.state), ledger_head_at_approval=self.head,
            public_signer_address=SIGNER, deposit_wallet_address=WALLET, approved_menu=args["candidate_menu"],
            side="BUY", max_create_attempts=1,
            envelope=dict(account_usd="100", order_usd="5", aggregate_commitment_usd="30", free_collateral_usd="70"),
            valid_from_utc=utc(X.T0 - HOUR_NS), valid_until_utc=utc(X.T0 + HOUR_NS))
        self.write()
        monkeypatch.setattr(lc, "_emit", self.records.append)
        monkeypatch.setattr(lc, "_stdin_is_tty", lambda: True)

    # files -----------------------------------------------------------------
    def write(self, stage_bytes=None):
        raw = stage_bytes if stage_bytes is not None else json.dumps(self.stage).encode()
        Path(self.case["stage_a_authorization_path"]).write_bytes(raw)
        self.case["stage_a_authorization_sha256"] = hashlib.sha256(raw).hexdigest()
        (self.tmp / "case.json").write_text(json.dumps(self.case), encoding="utf-8")
        return self.tmp / "case.json"

    # seams -----------------------------------------------------------------
    def clock(self):
        self.now += 1_000_000
        return self.now

    def fetch(self, **_identity):
        return X.snap(gamma=self.gamma, clob=self.book, completed=self.clock())

    def geoblock(self):
        return GateCGeoblockProof.from_response({"blocked": self.blocked, "country": "ZZ"}, observed_time_ns=self.now)

    def oauth(self, case, *, candidate_menu, lineage, information_cutoff_ns, clock_ns):
        self.oauth_calls += 1
        issued = clock_ns()
        request = op.build_oauth_request(surface_report=RECORDED_REPORT, candidate_menu=candidate_menu,
                                         lineage=lineage, information_cutoff_ns=information_cutoff_ns,
                                         issued_at_ns=issued, deadline_ns=issued + 180_000_000_000)
        choice = dict(self.trade, information_cutoff_ns=information_cutoff_ns, produced_at_ns=issued,
                      expires_at_ns=request.deadline_ns)
        report = fixture.dispatch(request, text=json.dumps(choice))
        self.mp.setattr(op.OAuthPlanTransport, "_run_child", lambda _self, phase, extra, timeout_s: copy.deepcopy(report))
        transport = op.OAuthPlanTransport(PIN_ROOT, self.tmp / "creds", mode="real")
        eligibility = op.evaluate_preflight(fixture.preflight(), attestation=dict(fixture.ATTEST),
                                            checked_at_ns=issued)
        self.journals += 1
        result = op.run_oauth_attempt(request, eligibility=eligibility, transport=transport,
                                      journal_dir=self.tmp / f"oauth{self.journals}", clock_ns=clock_ns)
        return result, request.deadline_ns

    def confirm(self, _prompt):
        summary = [r for r in self.records if r.get("record") == "order_summary"][-1]
        if self.on_confirm is not None:
            self.on_confirm(self)
        if self.typed is not None:
            return self.typed(summary)
        return f"{PHRASE} {summary['permit_id'][-12:]} {summary['stage_a_authorization_sha256'][-12:]}"

    def deps(self):
        canary = self

        class _Provider:
            def acquire(self):
                canary.secret_requests += 1
                return GateBSecretLease(T.SECRET)

        def pause(seconds):
            canary.now += int(seconds * 1_000_000_000)

        return L.LiveOrchDependencies(
            clock_ns=self.clock, host_currentness=lambda _config: dict(self.host), geoblock=self.geoblock,
            venue_fetcher=self.fetch, secret_provider_factory=_Provider,
            client_factory=lambda key, wallet: self.venue, pause=pause)

    def factory(self, config):
        self.factory_calls += 1
        orchestrator = L.LiveOrchestrator(config, dependencies=self.deps())
        original = orchestrator.canary

        def canary(permit, intent):
            self.canary_args.append((permit, intent, len(self.records)))
            return original(permit, intent)

        orchestrator.canary = canary
        return orchestrator

    def seams(self, **changes):
        value = dict(clock_ns=self.clock, host_currentness=lambda _config: dict(self.host), geoblock=self.geoblock,
                     venue_fetcher=self.fetch, oauth_attempt=self.oauth, confirmation_reader=self.confirm,
                     orchestrator_factory=self.factory)
        value.update(changes)
        return value

    def check(self, **changes):
        seams = {k: v for k, v in self.seams(**changes).items() if k in ("clock_ns", "host_currentness",
                                                                          "geoblock", "venue_fetcher")}
        return lc.check(self.write(), **seams)

    def run(self, **changes):
        self.records.clear()
        return lc.run(self.write(), **self.seams(**changes))


def zero_economic(receipt, canary):
    assert receipt["calls"]["canary"] == 0 and receipt["calls"]["order"] == 0
    assert canary.factory_calls == 0 and canary.venue.posts == [] and canary.secret_requests == 0


def one_create(receipt, canary):
    assert receipt["status"] == "CANARY_COMPLETE" and receipt["reason_codes"] == ["ONE_CREATE_ATTEMPTED"], receipt
    assert receipt["live_orch"]["create_transmits"] == 1 and len(canary.venue.posts) == 1
    assert receipt["calls"] == dict(oauth_dispatch=1, confirmation_prompt=1, canary=1, order=1)
    assert receipt["evidence_class"] == "OFFLINE_TEST_ONLY" and receipt["claim"] == "PROTOCOL_ONLY"


# ----------------------------------------------------------------- R002


def test_live_canary_check_is_non_economic(tmp_path, monkeypatch):
    """R002: all preconditions PASS read-only; each missing precondition returns its exact code."""
    def deny(*_a, **_k):
        raise AssertionError("forbidden surface reached")

    monkeypatch.setattr(op.OAuthPlanTransport, "_run_child", deny)
    monkeypatch.setattr(tf, "probe_native_tool_surface", deny)
    monkeypatch.setattr(op, "run_oauth_attempt", deny)
    for name in ("canary", "_open_session", "_truth"):
        monkeypatch.setattr(L.LiveOrchestrator, name, deny)
    c = Canary(tmp_path / "ok", monkeypatch)
    before = ledger_path(c.state).read_bytes()
    good = c.check()
    assert good["status"] == "PASS" and good["reason_codes"] == ["CHECK_PASS"], good["reason_codes"]
    assert good["stage_a_binding"] == lc.STAGE_A_BINDING and good["seconds_delay_applicability"] == "CHECKED_ZERO"
    assert good["calls"] == dict(oauth_dispatch=0, confirmation_prompt=0, canary=0, order=0)
    assert ledger_path(c.state).read_bytes() == before and not (c.state / "live_canary").exists()
    text = json.dumps(good)
    assert c.head not in text and c.stage["execution_host_binding_sha256"] not in text
    # Gamma without secondsDelay still passes check: admissible only for post-only (LIVE-ORCH 4F).
    c.gamma = {k: v for k, v in GAMMA.items() if k != "secondsDelay"}
    assert c.check()["seconds_delay_applicability"] == "POST_ONLY_REQUIRED"

    def codes(canary, **changes):
        receipt = canary.check(**changes)
        assert receipt["status"] == "BLOCKED" and receipt["stage_a_binding"] is None
        assert receipt["calls"]["oauth_dispatch"] == 0
        return receipt["reason_codes"]

    cases = [
        (dict(gamma=dict(GAMMA, secondsDelay=3)), "SECONDS_DELAY_UNSUPPORTED"),
        (dict(gamma=dict(GAMMA, negRisk=True), book=X.book_doc(neg_risk=True)), "NEG_RISK_UNSUPPORTED"),
        (dict(gamma=dict(GAMMA, closed=True)), "MARKET_NOT_ELIGIBLE"),
        (dict(blocked=True), "ACCESS_NOT_ELIGIBLE"),
        (dict(host=T.host_doc(ntp_state="unsynchronized")), "HOST_NOT_CURRENT"),
    ]
    for index, (changes, code) in enumerate(cases):
        other = Canary(tmp_path / f"venue{index}", monkeypatch)
        for key, value in changes.items():
            setattr(other, key, value)
        assert code in codes(other), code
    missing = Canary(tmp_path / "missing", monkeypatch, hermes=False)
    assert "STRATEGY_ASSESSMENT_UNAVAILABLE" in codes(missing)
    stale = Canary(tmp_path / "stale", monkeypatch)
    stale.case["max_hermes_age_s"] = 1
    stale.now = X.T0 + 5_000_000_000
    assert "STRATEGY_ASSESSMENT_UNAVAILABLE" in codes(stale)
    revoked = Canary(tmp_path / "revoked", monkeypatch)
    revoked.w.append(X.build_portfolio_policy_receipt(action="REVOKE", policy_id=revoked.w.policy.policy_id,
        previous_active_policy_id=revoked.w.policy.policy_id, human_authorization_ref="synthetic:revoke",
        created_time_ns=2000))
    assert "POLICY_NOT_ACTIVE" in codes(revoked)
    unallocated = Canary(tmp_path / "unallocated", monkeypatch, allocation=False)
    assert "ALLOCATION_REQUIRED" in codes(unallocated)
    expired = Canary(tmp_path / "expired", monkeypatch, allocation=False)
    for version in (expired.w.version, expired.w.other_version):
        expired.w.append(X._allocation(version, expired.w.policy, valid_until=X.T0 - 1))
    assert "ALLOCATION_NOT_ACTIVE" in codes(expired)
    lineage = Canary(tmp_path / "lineage", monkeypatch)
    first, second = lineage.case["candidate_menu"]
    lineage.case["candidate_menu"] = [dict(first, candidate_id=second["candidate_id"]),
                                      dict(second, candidate_id=first["candidate_id"])]
    lineage.stage["approved_menu"] = lineage.case["candidate_menu"]
    assert "ALPHA_STRATEGY_LINEAGE_INVALID" in codes(lineage)
    unhealthy = Canary(tmp_path / "unhealthy", monkeypatch)
    ledger_path(unhealthy.state).write_bytes(b"not a ledger")
    assert {"LIVE_ORCH_LEDGER_UNHEALTHY", "STAGE_A_LEDGER_UNINITIALIZED"} <= set(codes(unhealthy))
    nopin = Canary(tmp_path / "nopin", monkeypatch)
    nopin.case["oauth_pin_root"] = str(tmp_path / "absent-pin")
    assert "OAUTH_PIN_ROOT_MISSING" in codes(nopin)
    # Malformed case: unknown key, duplicate key, relative path, out-of-range bound, bad JSON.
    bad = Canary(tmp_path / "bad", monkeypatch)
    path = bad.write()
    raw = path.read_text(encoding="utf-8")
    for body in (json.dumps(dict(bad.case, extra=1)), raw[:-1] + ', "max_hermes_age_s": 5}',
                 json.dumps(dict(bad.case, lifecycle_store_path="relative/life.sqlite3")),
                 json.dumps(dict(bad.case, max_public_data_age_s=61)), "{not json", json.dumps([1])):
        path.write_text(body, encoding="utf-8")
        assert lc.check(path, clock_ns=bad.clock)["reason_codes"] == ["CASE_INVALID"]


# ----------------------------------------------------------------- R003


def test_live_canary_run_requires_attended_tty_and_single_oauth_dispatch(tmp_path, monkeypatch):
    """R003: non-TTY refuses before I/O; one dispatch per run; unusable OAuth is BLOCKED, zero canary."""
    c = Canary(tmp_path / "tty", monkeypatch)
    monkeypatch.setattr(lc, "_stdin_is_tty", lambda: False)
    receipt = lc.run(tmp_path / "never-read.json", **c.seams())
    assert receipt["reason_codes"] == ["ATTENDED_TTY_REQUIRED"] and c.oauth_calls == 0
    zero_economic(receipt, c)
    monkeypatch.setattr(lc, "_stdin_is_tty", lambda: True)
    one_create(c.run(), c)
    assert c.oauth_calls == 1
    # The production OAuth attempt (journal, eligibility, request, ONE dispatch) over patched children.
    built = []
    original_build = op.build_oauth_request
    monkeypatch.setattr(op, "build_oauth_request", lambda **kw: built.append(original_build(**kw)) or built[-1])
    monkeypatch.setattr(tf, "probe_native_tool_surface", lambda pin_root, **_kw: copy.deepcopy(RECORDED_REPORT))

    def children(canary, *, preflight=None, usage=True):
        sends = []

        def child(_self, phase, extra, timeout_s):
            if phase == "preflight":
                return preflight or fixture.preflight()
            sends.append(phase)
            request = built[-1]
            clocks = json.loads(request.model_input)
            choice = dict(canary.trade, information_cutoff_ns=clocks["information_cutoff_ns"],
                          produced_at_ns=clocks["produced_at_ns"], expires_at_ns=clocks["expires_at_ns"])
            return fixture.dispatch(request, text=json.dumps(choice), **({} if usage else dict(usage=None)))

        monkeypatch.setattr(op.OAuthPlanTransport, "_run_child", child)
        return sends

    native = Canary(tmp_path / "native", monkeypatch)
    sends = children(native)
    one_create(native.run(oauth_attempt=None), native)
    assert sends == ["dispatch"] and sorted(p.name for p in Path(native.case["oauth_journal_dir"]).iterdir()) == [
        "oauthplan-attempt.json", "oauthplan-attempt.reserved"]
    # Native OAuth setup failures and an unavailable fresh menu read stop with zero dispatch and zero canary.
    def broken_probe(pin_root, **_kw):
        raise RuntimeError("pin unavailable")

    probe = Canary(tmp_path / "probe", monkeypatch)
    children(probe)
    monkeypatch.setattr(tf, "probe_native_tool_surface", broken_probe)
    receipt = probe.run(oauth_attempt=None)
    assert receipt["reason_codes"] == ["OAUTH_ATTEMPT_FAILED"] and receipt["calls"]["confirmation_prompt"] == 0
    zero_economic(receipt, probe)
    monkeypatch.setattr(tf, "probe_native_tool_surface", lambda pin_root, **_kw: copy.deepcopy(RECORDED_REPORT))
    offline_venue = Canary(tmp_path / "venue", monkeypatch)
    reads = []

    def failing_menu_read(**identity):
        reads.append(identity)
        if len(reads) > 1:
            raise RuntimeError("venue unavailable")
        return offline_venue.fetch(**identity)

    receipt = offline_venue.run(venue_fetcher=failing_menu_read)
    assert receipt["reason_codes"] == ["VENUE_SNAPSHOT_UNAVAILABLE"] and offline_venue.oauth_calls == 0
    zero_economic(receipt, offline_venue)
    for name, setup, code in (
            ("reused", lambda k: (Path(k.case["oauth_journal_dir"]).mkdir(),
                                  (Path(k.case["oauth_journal_dir"]) / "x").write_text("x")), "OAUTH_JOURNAL_NOT_FRESH"),
            ("inelig", lambda k: None, "OAUTH_PREFLIGHT_INELIGIBLE"),
            ("unwitnessed", lambda k: None, "OAUTH_RESULT_NOT_WITNESSED")):
        other = Canary(tmp_path / name, monkeypatch)
        setup(other)
        sends = children(other, preflight=fixture.preflight(target_listed=False) if name == "inelig" else None,
                         usage=name != "unwitnessed")
        receipt = other.run(oauth_attempt=None)
        assert receipt["reason_codes"] == [code], receipt["reason_codes"]
        assert sends == ([] if name != "unwitnessed" else ["dispatch"])
        assert receipt["calls"]["confirmation_prompt"] == 0
        zero_economic(receipt, other)


# ----------------------------------------------------------------- R004


def test_live_canary_abstain_or_blocked_never_reaches_canary(tmp_path, monkeypatch):
    """R004: ABSTAIN or BLOCKED bridge results: zero confirmation prompt, zero key prompt, zero canary."""
    abstain = Canary(tmp_path / "abstain", monkeypatch,
                     lambda t: {k: t[k] for k in auto.cycle._CLOCK_KEYS} | {"action": "NO_TRADE"})
    receipt = abstain.run()
    assert receipt["status"] == "ABSTAIN" and receipt["reason_codes"] == ["NO_TRADE"]
    assert receipt["permit_id"] is None and receipt["calls"]["confirmation_prompt"] == 0
    zero_economic(receipt, abstain)
    big = Canary(tmp_path / "big", monkeypatch, lambda t: dict(t, requested_shares="10"))
    receipt = big.run()
    assert receipt["status"] == "BLOCKED" and receipt["reason_codes"][:2] == ["PREFLIGHT_BLOCKED",
                                                                                "SINGLE_ORDER_LIMIT_EXCEEDED"]
    assert receipt["calls"]["confirmation_prompt"] == 0 and not [r for r in big.records
                                                                 if r.get("record") == "order_summary"]
    zero_economic(receipt, big)


# ----------------------------------------------------------------- R005


def test_live_canary_confirmation_binds_exact_permit(tmp_path, monkeypatch):
    """R005: exact IDs shown; Stage A binding and single use; only phrase + both suffixes reach one canary."""
    c = Canary(tmp_path / "ok", monkeypatch)
    captured = []
    original = bridge.prepare_live_canary_handoff
    monkeypatch.setattr(bridge, "prepare_live_canary_handoff",
                        lambda result, **kw: captured.append(original(result, **kw)) or captured[-1])
    receipt = c.run()
    one_create(receipt, c)
    _bridge_receipt, permit, intent = captured[-1]
    summary, confirmation = c.records[0], c.records[1]
    assert summary["record"] == "order_summary" and confirmation["record"] == "stage_b_confirmation"
    assert (summary["permit_id"], summary["execution_intent_id"]) == (permit.permit_id, intent.execution_intent_id)
    assert summary["stage_a_authorization_sha256"] == c.case["stage_a_authorization_sha256"]
    assert confirmation["authorization"] == "EVIDENCE_ONLY_NOT_AUTHORIZATION"
    assert confirmation["displayed_at_ns"] < confirmation["confirmed_at_ns"]
    # Identical objects; the record was flushed before the single canary call.
    assert len(c.canary_args) == 1 and c.canary_args[0][0] is permit and c.canary_args[0][1] is intent
    assert c.canary_args[0][2] == 2
    assert receipt["stage_a_binding"] == "MACHINE_CONFORMANCE_ONLY_OWNER_APPROVAL_EXTERNAL"
    for text in map(json.dumps, [receipt, *c.records]):
        assert "AUTHENTICATED" not in text.upper().replace("_NOT_AUTHENTICATED", "")

    # Wrong confirmation lines -> OWNER_CONFIRMATION_MISMATCH with zero canary.
    def eof(_summary):
        raise EOFError

    wrong = (lambda s: "yes", lambda s: PHRASE, lambda s: f"{PHRASE} {s['permit_id'][-12:]}",
             lambda s: f"{PHRASE} {'f' * 12} {s['stage_a_authorization_sha256'][-12:]}",
             lambda s: f"{PHRASE} {s['stage_a_authorization_sha256'][-12:]} {s['permit_id'][-12:]}",
             lambda s: f"{PHRASE} {s['permit_id'][-12:]} {s['stage_a_authorization_sha256'][-12:]} ok",
             lambda s: f" {PHRASE} {s['permit_id'][-12:]} {s['stage_a_authorization_sha256'][-12:]}", eof)
    for index, typed in enumerate(wrong):
        other = Canary(tmp_path / f"wrong{index}", monkeypatch)
        other.typed = typed
        receipt = other.run()
        assert receipt["reason_codes"] == ["OWNER_CONFIRMATION_MISMATCH"] and receipt["calls"]["confirmation_prompt"] == 1
        assert not [r for r in other.records if r.get("record") == "stage_b_confirmation"]
        zero_economic(receipt, other)

    def blocked_before_oauth(canary, *codes):
        oauth, factory, posts = canary.oauth_calls, canary.factory_calls, len(canary.venue.posts)
        receipt = canary.run()
        assert set(codes) <= set(receipt["reason_codes"]), receipt["reason_codes"]
        assert receipt["status"] == "BLOCKED" and canary.oauth_calls == oauth
        assert receipt["calls"] == dict(oauth_dispatch=0, confirmation_prompt=0, canary=0, order=0)
        assert (canary.factory_calls, len(canary.venue.posts)) == (factory, posts)
        return receipt

    # Machine-verifiable Stage A failures, all before any OAuth dispatch.
    gone = Canary(tmp_path / "gone", monkeypatch)
    gone.write()
    Path(gone.case["stage_a_authorization_path"]).unlink()
    (gone.tmp / "case.json").write_text(json.dumps(gone.case), encoding="utf-8")
    assert lc.run(gone.tmp / "case.json", **gone.seams())["reason_codes"] == ["STAGE_A_UNAVAILABLE"]
    for name, mutate, code in (
            ("hash", lambda k: k.case.update(stage_a_authorization_sha256="e" * 64), "STAGE_A_DIGEST_MISMATCH"),
            ("tamper", lambda k: Path(k.case["stage_a_authorization_path"]).write_bytes(
                json.dumps(dict(k.stage, max_create_attempts=2)).encode()), "STAGE_A_DIGEST_MISMATCH")):
        other = Canary(tmp_path / name, monkeypatch)
        other.write()
        mutate(other)
        (other.tmp / "case.json").write_text(json.dumps(other.case), encoding="utf-8")
        receipt = lc.run(other.tmp / "case.json", **other.seams())
        assert receipt["reason_codes"] == [code] and other.oauth_calls == 0
        zero_economic(receipt, other)
    scope = dict(release_sha="d" * 40, execution_host_binding_sha256="a" * 64, live_orch_state_root=str(tmp_path / "x"),
                 public_signer_address="0x" + "c" * 40, deposit_wallet_address="0x" + "d" * 40, side="SELL",
                 max_create_attempts=2, approved_menu=[c.stage["approved_menu"][0]],
                 envelope=dict(c.stage["envelope"], order_usd="6"))
    for key, value in scope.items():
        other = Canary(tmp_path / f"scope-{key}", monkeypatch)
        other.stage[key] = value
        blocked_before_oauth(other, "STAGE_A_SCOPE_MISMATCH")
    for name, window in (("early", (X.T0 + HOUR_NS, X.T0 + 2 * HOUR_NS)), ("late", (X.T0 - 2 * HOUR_NS, X.T0 - HOUR_NS))):
        other = Canary(tmp_path / name, monkeypatch)
        other.stage.update(valid_from_utc=utc(window[0]), valid_until_utc=utc(window[1]))
        blocked_before_oauth(other, "STAGE_A_WINDOW_INVALID")
    for name, changes in (("empty", dict(ledger_head_at_approval="EMPTY")),
                          ("span", dict(valid_until_utc=utc(X.T0 + 80 * HOUR_NS))),
                          ("unknown", dict(approved_by="KARL"))):
        other = Canary(tmp_path / name, monkeypatch)
        other.stage.update(changes)
        blocked_before_oauth(other, "STAGE_A_INVALID")
    # The window closes between bridge PASS and .canary: last-boundary recheck.
    closing = Canary(tmp_path / "closing", monkeypatch)
    closing.on_confirm = lambda k: setattr(k, "now", calendar.timegm(time.strptime(
        k.stage["valid_until_utc"], "%Y-%m-%dT%H:%M:%SZ")) * 1_000_000_000)
    receipt = closing.run()
    assert receipt["reason_codes"] == ["STAGE_A_WINDOW_INVALID"] and receipt["calls"]["confirmation_prompt"] == 1
    zero_economic(receipt, closing)
    # Chosen intent outside approved_menu, or a permit/intent mismatch, at the pre-canary recheck.
    approved = dict(valid_from_ns=0, valid_until_ns=2**62, ledger_head_at_approval=c.head,
                    approved_menu=c.stage["approved_menu"])
    item = c.stage["approved_menu"][0]
    good_intent = SimpleNamespace(strategy_version_id=item["strategy_version_id"], gamma_market_id=item["gamma_market_id"],
                                  condition_id=item["condition_id"], token_id=item["token_id"], side="BUY",
                                  execution_intent_id="i")
    fresh = Canary(tmp_path / "recheck", monkeypatch)
    good_permit = SimpleNamespace(execution_intent_id="i", strategy_version_id=item["strategy_version_id"])
    lc._recheck_stage_a(fresh.case, approved, now_ns=1, permit=good_permit, intent=good_intent)
    for intent_changes, permit, code in ((dict(token_id="999"), good_permit, "STAGE_A_SCOPE_MISMATCH"),
                                         (dict(side="SELL"), good_permit, "STAGE_A_SCOPE_MISMATCH"),
                                         ({}, SimpleNamespace(execution_intent_id="j", strategy_version_id="s"),
                                          "PERMIT_INTENT_MISMATCH")):
        with pytest.raises(lc.CanaryBlocked) as error:
            lc._recheck_stage_a(fresh.case, approved, now_ns=1, permit=permit,
                                intent=SimpleNamespace(**dict(vars(good_intent), **intent_changes)))
        assert error.value.codes == [code]

    # Single use: at most one CREATE per Stage A, whatever happens around it.
    rerun = Canary(tmp_path / "rerun", monkeypatch)
    one_create(rerun.run(), rerun)
    blocked_before_oauth(rerun, "STAGE_A_CONSUMED")  # sequential replay after an admission
    assert len(rerun.venue.posts) == 1
    locked = Canary(tmp_path / "locked", monkeypatch)
    held = WalletSessionLock(locked.state / "live_canary", WALLET).acquire()  # a concurrent attended run
    assert locked.run()["reason_codes"] == ["STAGE_A_RUN_LOCKED"] and locked.oauth_calls == 0
    held.close()
    one_create(locked.run(), locked)
    Path(WalletSessionLock(locked.state / "live_canary", WALLET).path).write_text(WALLET)  # crash left a stale lock
    assert locked.run()["reason_codes"] == ["STAGE_A_RUN_LOCKED"]
    Path(WalletSessionLock(locked.state / "live_canary", WALLET).path).unlink()
    blocked_before_oauth(locked, "STAGE_A_CONSUMED")
    deleted = Canary(tmp_path / "deleted", monkeypatch)
    one_create(deleted.run(), deleted)
    ledger_path(deleted.state).unlink()  # same approved path, ledger removed after an admission
    blocked_before_oauth(deleted, "STAGE_A_LEDGER_UNINITIALIZED")
    # Recreated through native create at a new time: a different genesis hash.
    ProtectedExecutionGateway.create(ledger_path(deleted.state), created_time_ns=X.T0 - 5).close()
    blocked_before_oauth(deleted, "STAGE_A_CONSUMED")
    assert len(deleted.venue.posts) == 1
    early = Canary(tmp_path / "early-event", monkeypatch)
    ProtectedExecutionGateway.open(ledger_path(early.state), opened_time_ns=X.T0).close()  # event before the run
    blocked_before_oauth(early, "STAGE_A_CONSUMED")
    for name, hook, code in (
            ("boundary-event", lambda k: ProtectedExecutionGateway.open(ledger_path(k.state), opened_time_ns=k.now).close(),
             "STAGE_A_CONSUMED"),
            ("boundary-delete", lambda k: ledger_path(k.state).unlink(), "STAGE_A_LEDGER_UNINITIALIZED"),
            ("boundary-recreate", lambda k: (ledger_path(k.state).unlink(), ProtectedExecutionGateway.create(
                ledger_path(k.state), created_time_ns=k.now).close()), "STAGE_A_CONSUMED")):
        other = Canary(tmp_path / name, monkeypatch)
        other.on_confirm = hook
        receipt = other.run()
        assert receipt["reason_codes"] == [code] and receipt["calls"]["confirmation_prompt"] == 1
        zero_economic(receipt, other)
    other_root = Canary(tmp_path / "other-root", monkeypatch)
    moved = tmp_path / "other-root-state"
    bootstrap(moved)
    other_root.case["live_orch_state_root"] = str(moved)  # same Stage A, a distinct (fresh) root
    blocked_before_oauth(other_root, "STAGE_A_SCOPE_MISMATCH")

    # Bootstrap order (section 7(i)), offline: missing parent and ledger -> head -> Stage A -> check.
    root = tmp_path / "boot" / "state"
    path = ledger_path(root)
    with pytest.raises(Exception):
        ProtectedExecutionGateway.create(path, created_time_ns=X.T0)  # native create needs the parent
    with pytest.raises(lc.CanaryBlocked) as error:
        lc.read_ledger_head(path)
    assert error.value.codes == ["STAGE_A_LEDGER_UNINITIALIZED"] and not path.exists()
    head = bootstrap(root)
    assert lc.read_ledger_head(path) == head and len(head) == 64
    with pytest.raises(Exception):
        ProtectedExecutionGateway.create(path, created_time_ns=X.T0)  # never re-initialized
    boot = Canary(tmp_path / "boot-case", monkeypatch)
    boot.case["live_orch_state_root"] = str(root)
    boot.stage.update(live_orch_state_root=str(root), ledger_head_at_approval=head)
    assert boot.check()["status"] == "PASS"
    # check before any Stage A is only a typed BLOCKED result carrying no binding inputs.
    first = Canary(tmp_path / "first", monkeypatch)
    first.write()
    Path(first.case["stage_a_authorization_path"]).unlink()
    (first.tmp / "case.json").write_text(json.dumps(first.case), encoding="utf-8")
    pre = lc.check(first.tmp / "case.json", clock_ns=first.clock, host_currentness=lambda _c: dict(first.host),
                   geoblock=first.geoblock, venue_fetcher=first.fetch)
    assert pre["status"] == "BLOCKED" and pre["reason_codes"] == ["STAGE_A_UNAVAILABLE"]
    assert first.head not in json.dumps(pre) and lc.execution_host_binding_sha256(first.case) not in json.dumps(pre)
    nothing = Canary(tmp_path / "nothing", monkeypatch)
    ledger_path(nothing.state).unlink()
    assert "STAGE_A_LEDGER_UNINITIALIZED" in nothing.check()["reason_codes"]
    assert not ledger_path(nothing.state).exists()  # check never creates the ledger


# ----------------------------------------------------------------- R006


def test_live_canary_end_to_end_offline_one_create(tmp_path, monkeypatch):
    """R006: offline chain to ONE_CREATE_ATTEMPTED; windows, freshness and fee drift fail closed."""
    c = Canary(tmp_path / "ok", monkeypatch)
    c.gamma = {k: v for k, v in GAMMA.items() if k != "secondsDelay"}  # passive menu item without Gamma delay
    receipt = c.run()
    one_create(receipt, c)
    assert c.venue.posts[0].post_only is True
    assert receipt["live_orch"]["episode_state"] in lc.CLEAN_TERMINAL_STATES
    assert "reconcile_required" not in receipt
    repeat = c.run()
    assert repeat["status"] == "BLOCKED" and len(c.venue.posts) == 1  # Stage A / journal / permit consumed

    # (i) The OAuth result finishes after its request deadline: AUTO-01 blocks before any fresh read.
    late = Canary(tmp_path / "late", monkeypatch)
    original = late.oauth

    def late_oauth(case, **kw):
        result, deadline = original(case, **kw)
        late.now = deadline + 1
        return result, deadline

    receipt = late.run(oauth_attempt=late_oauth)
    assert receipt["status"] == "BLOCKED" and receipt["permit_id"] is None and late.oauth_calls == 1
    zero_economic(receipt, late)
    # (ii) The fresh book is older than max_public_data_age at the fresh Gate C: no re-fetch.
    stale = Canary(tmp_path / "stale", monkeypatch)
    fetches = []

    def aging_fetch(**identity):
        fetches.append(identity)
        if len(fetches) > 2:  # check + menu snapshots done; the bridge's fresh read sees an old book
            stale.book = X.book_doc(timestamp=str(X.BOOK_MS - 60_000))
        return stale.fetch(**identity)

    receipt = stale.run(venue_fetcher=aging_fetch)
    assert receipt["reason_codes"][0] == "GATE_C_REJECTED" and receipt["permit_id"] is None
    zero_economic(receipt, stale)
    # (iii) The permit window passes between bridge PASS and confirmation.
    window = Canary(tmp_path / "window", monkeypatch)
    window.on_confirm = lambda k: setattr(k, "now", k.now + 61_000_000_000)
    receipt = window.run()
    assert receipt["reason_codes"] in (["PERMIT_EXPIRED"], ["CHOICE_WINDOW_EXPIRED"])
    assert window.venue.posts == [] and receipt["calls"]["oauth_dispatch"] == 1
    # (iv) A public-data age above 60 s is a malformed case.
    wide = Canary(tmp_path / "wide", monkeypatch)
    wide.case["max_public_data_age_s"] = 61
    assert wide.run()["reason_codes"] == ["CASE_INVALID"] and wide.oauth_calls == 0
    # Fee drift. Composer orders are post-only PASSIVE_MAKER (AUTO-01 admits GTC/GTD only), so the
    # maker fee reserve is exactly zero or the configuration is unknown: drift fails closed natively.
    drift = Canary(tmp_path / "drift", monkeypatch)
    drift.on_confirm = lambda k: setattr(k, "gamma", dict(GAMMA, feeSchedule=dict(
        rate=0.5, exponent=1, takerOnly=False, rebateRate=0)))
    receipt = drift.run()
    assert receipt["reason_codes"] == ["FEE_CONFIGURATION_UNKNOWN"], receipt["reason_codes"]
    assert receipt["live_orch"]["create_transmits"] == 0 and drift.venue.posts == []
    # The native USD 5 cap is applied to the canary-time fee recomputation, not the bridge-time one:
    # a taker permit whose preflight fits the cap is refused at admission once the fee rate rises.
    harness = T.Harness(tmp_path / "cap", X.make_world(tmp_path / "cap-world"))
    permit, intent = T.make_permit(harness.world)
    preflight = harness.orchestrator().preflight(permit, intent)
    assert preflight.status == "PREFLIGHT_PASS"
    assert Decimal(preflight.details["principal_notional_usd"]) + Decimal(
        preflight.details["worst_case_fee_reserve_usd"]) <= 5
    harness.gamma = dict(GAMMA, feeSchedule=dict(rate=0.5, exponent=1, takerOnly=True, rebateRate=0))
    capped = harness.orchestrator().canary(permit, intent)
    assert (capped.code, capped.create_transmits) == ("SINGLE_ORDER_LIMIT_EXCEEDED", 0)
    assert harness.venue.posts == []


# ----------------------------------------------------------------- R007


def test_live_canary_receipt_sanitized_and_no_authority_inflation(tmp_path, monkeypatch):
    """R007: sanitized receipts, no import I/O, no loop/retry/SELL/scheduler, fakes isolated."""
    c = Canary(tmp_path / "ok", monkeypatch)
    receipts = [c.check(), c.run()]
    one_create(receipts[1], c)
    for text in map(json.dumps, receipts):
        for secret in (str(tmp_path), "creds", SIGNER, WALLET, "OPERATOR_ATTESTATION", T.SECRET, "eyJ"):
            assert secret not in text, secret
        assert "receipt_id" in text and "livecanary:sha256:" in text
    # Fake isolation: any seam without orchestrator_factory never reaches the economic path.
    constructed = []
    monkeypatch.setattr(L.LiveOrchestrator, "canary", lambda *a, **k: constructed.append("canary"))
    for name in ("clock_ns", "host_currentness", "geoblock", "venue_fetcher", "oauth_attempt", "confirmation_reader"):
        other = Canary(tmp_path / f"seam-{name}", monkeypatch)
        only = {name: other.seams()[name]}
        receipt = lc.run(other.write(), **only)
        assert receipt["reason_codes"] == ["OFFLINE_SEAM_IN_ECONOMIC_PATH"] and other.oauth_calls == 0
        assert receipt["evidence_class"] == "OFFLINE_TEST_ONLY"
        zero_economic(receipt, other)
    assert constructed == []
    # No seams at all, but an OFFLINE_TEST_ONLY handoff: refused before any production orchestrator.
    prod = Canary(tmp_path / "prod", monkeypatch)
    facts_receipt = lc._receipt("run", True)
    facts = lc._check(lc.load_case(prod.write()), dict(clock_ns=prod.clock, host_currentness=lambda _c: dict(prod.host),
                                                      geoblock=prod.geoblock, venue_fetcher=prod.fetch), facts_receipt)
    assert facts["codes"] == []
    monkeypatch.setattr(lc, "_check", lambda case, seams, receipt: facts)
    monkeypatch.setattr(lc, "native_oauth_attempt", prod.oauth)
    offline_handoff = []
    original = bridge.prepare_live_canary_handoff

    def offline_bridge(result, **kw):
        kw.update(clock_ns=prod.clock, host_currentness=lambda _c: dict(prod.host), geoblock=prod.geoblock,
                  venue_fetcher=prod.fetch)
        offline_handoff.append(original(result, **kw))
        return offline_handoff[-1]

    monkeypatch.setattr(bridge, "prepare_live_canary_handoff", offline_bridge)

    native_orchestrator = L.LiveOrchestrator

    def no_production(config, **kwargs):
        if "dependencies" not in kwargs:  # the bridge's read-only preflight injects refusing seams
            raise AssertionError("production LiveOrchestrator constructed")
        return native_orchestrator(config, **kwargs)

    monkeypatch.setattr(L, "LiveOrchestrator", no_production)
    monkeypatch.setattr("builtins.input", lambda *_a: pytest.fail("confirmation prompted"))
    receipt = lc.run(prod.tmp / "case.json")
    assert offline_handoff[-1][0]["status"] == "PASS", offline_handoff[-1][0]["reason_codes"]
    assert offline_handoff[-1][0]["evidence_class"] == "OFFLINE_TEST_ONLY"
    assert receipt["reason_codes"] == ["OFFLINE_HANDOFF_IN_PRODUCTION"]
    assert receipt["evidence_class"] == "NATIVE_PRODUCTION" and receipt["calls"]["canary"] == 0
    assert prod.venue.posts == [] and prod.secret_requests == 0
    # Source: no loop, retry, scheduler, SELL path, envelope override or raw client surface.
    source = Path(lc.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert not [n for n in ast.walk(tree) if isinstance(n, (ast.While, ast.AsyncFunctionDef))]
    for forbidden in ("SecureClient", "time.sleep", "schedule(", "websocket", "place_limit_order",
                      "place_market_order", "post_order", "os.environ", "fastapi", "approve(", "redeem",
                      "session_key", "builder_code", "envelope=", "threading", "retry("):
        assert forbidden not in source, forbidden
    production = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and n.func.attr == "LiveOrchestrator" and isinstance(n.func.value, ast.Name) and n.func.value.id == "L"]
    economic = [n for n in production if not n.keywords]
    assert len(economic) == 1 and len(economic[0].args) == 1  # production defaults: config only
    assert (L.AUTHORIZED_ACCOUNT_CAPITAL_USD, L.SINGLE_ORDER_WORST_CASE_MAX_USD, L.MAX_TOTAL_EARLY_COMMITMENT_USD,
            L.MIN_FREE_COLLATERAL_RESERVE_USD, L.MAX_CREATE_PER_CANARY) == (100, 5, 30, 70, 1)
    # The package __init__ (pre-existing) is loaded first; importing this module itself adds no I/O
    # and no src module: Hermes, Alpha, bridge and OAuth imports are lazy, inside functions.
    script = '''import sys
import src.execution_gateway
before = set(sys.modules)
def guard(name, args):
    if name.startswith(("socket.", "subprocess.", "sqlite3.connect", "os.system", "os.putenv", "urllib.")):
        raise RuntimeError(name)
sys.addaudithook(guard)
import src.execution_gateway.live_canary
added = {m for m in set(sys.modules) - before if m.startswith("src.")}
assert added == {"src.execution_gateway.live_canary"}, added
print("IMPORT_NO_IO_PASS")
'''
    result = subprocess.run([sys.executable, "-B", "-c", script], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0 and "IMPORT_NO_IO_PASS" in result.stdout, result.stderr
