"""Attended one-process Hermes choice -> native permit -> LIVE-ORCH first BUY canary.

S10-LIVE-CANARY-01. A foreground composer of unchanged native interfaces only:

    check: verified stores, policy/allocation/capacity, Alpha lineage, canonical assessment,
           strict host currentness, geoblock, fresh public venue, LIVE-ORCH ledger, OAuth
           paths and the read-only Stage A binding -- no OAuth, key, session or order.
    run:   attended TTY -> check -> one witnessed OAuth Stage B choice (fresh single-use
           journal) -> merged bridge handoff (fresh Gate C permit + read-only preflight)
           -> Stage A recheck -> exact order summary -> Stage B ID-bound confirmation
           -> exactly one LiveOrchestrator(config).canary(permit, intent), production defaults.

The canary is execution-mechanics validation only, never edge, profit or strategy
qualification; ONE_CREATE_ATTEMPTED is not a fill. The composer handles no secret: the
signer key exists only inside the native Gate-B no-echo prompt and the OAuth credential
directory is passed only to the native transport. Stage A binding is machine conformance
only; owner approval of the artifact is established outside code by Karl's activation
record (receipt label MACHINE_CONFORMANCE_ONLY_OWNER_APPROVAL_EXTERNAL). Any injected test
seam makes the run OFFLINE_TEST_ONLY / PROTOCOL_ONLY. There is no scheduler, loop, retry,
SELL or envelope change. Importing this module performs no I/O.
"""
import calendar
import hashlib
import json
from pathlib import Path
import re
import sys
import time

CASE_SCHEMA = ("polymarket-live-canary-case", "1.0.0")
STAGE_A_SCHEMA = ("polymarket-live-canary-stage-a", "1.0.0")
STAGE_A_BINDING = "MACHINE_CONFORMANCE_ONLY_OWNER_APPROVAL_EXTERNAL"
MAX_STAGE_A_SPAN_NS = 72 * 3600 * 1_000_000_000
CLEAN_TERMINAL_STATES = ("CREATE_REJECTED", "TERMINAL_NO_POSITION", "TERMINAL_KNOWN_POSITION")
_MAX_FILE_BYTES = 65_536
_HEX64 = re.compile(r"[0-9a-f]{64}")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_MENU_KEYS = {"candidate_id", "strategy_version_id", "gamma_market_id", "condition_id", "token_id"}
_PATH_KEYS = ("lifecycle_store_path", "hermes_store_path", "alpha_registry_path", "live_orch_state_root",
              "oauth_pin_root", "oauth_credential_dir", "oauth_journal_dir", "stage_a_authorization_path")
_HOST_KEYS = {"repository_root", "binding_file", "active_release", "unit_dir", "ssh_port", "expected_release_sha"}
_CASE_REQUIRED = {"schema_id", "schema_version", *_PATH_KEYS, "public_signer_address", "deposit_wallet_address",
                  "host", "plan_usage_attestation", "candidate_menu", "max_hermes_age_s",
                  "stage_a_authorization_sha256"}
_CASE_OPTIONAL = {"oauth_deadline_s": 180, "max_public_data_age_s": 60}
_OPERATOR_RECORD_KEYS = ("oauth_preflight_operator_record_path", "oauth_dispatch_operator_record_path")
_STAGE_A_KEYS = {"schema_id", "schema_version", "release_sha", "execution_host_binding_sha256",
                 "live_orch_state_root", "ledger_head_at_approval", "public_signer_address",
                 "deposit_wallet_address", "approved_menu", "side", "max_create_attempts", "envelope",
                 "valid_from_utc", "valid_until_utc"}
_ENVELOPE_KEYS = {"account_usd", "order_usd", "aggregate_commitment_usd", "free_collateral_usd"}
_BRIDGE_SEAMS = ("clock_ns", "host_currentness", "geoblock", "venue_fetcher")


class CanaryBlocked(Exception):
    def __init__(self, *codes: str):
        super().__init__(codes[0])
        self.codes = list(codes)


def _require(condition: bool, *codes: str) -> None:
    if not condition:
        raise CanaryBlocked(*codes)


def _strict_json(raw: bytes) -> object:
    def pairs(items):
        keys = [k for k, _ in items]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate key")
        return dict(items)

    def constant(_name):
        raise ValueError("constant")

    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)


def _read_bounded(path: Path) -> bytes:
    with open(path, "rb") as stream:
        raw = stream.read(_MAX_FILE_BYTES + 1)
    if len(raw) > _MAX_FILE_BYTES:
        raise ValueError("too large")
    return raw


def _int_in(value: object, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _menu_ok(menu: object) -> bool:
    return (type(menu) is list and 1 <= len(menu) <= 8 and
            all(type(m) is dict and set(m) == _MENU_KEYS and all(type(v) is str and 0 < len(v) <= 256
                                                                for v in m.values()) for m in menu))


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _operator_record_path_ok(value: object) -> bool:
    return (type(value) is str and bool(value) and not any(ord(c) < 32 or ord(c) == 127 for c in value) and
            Path(value).is_absolute() and
            not any(part in {".", ".."} for part in value.replace("\\", "/").split("/")))


def load_case(path: object) -> dict:
    """Closed strict-JSON case; any defect is CASE_INVALID (never echoed)."""
    try:
        case = _strict_json(_read_bounded(Path(path)))
        _require(type(case) is dict and _CASE_REQUIRED <= set(case) <=
                 _CASE_REQUIRED | set(_CASE_OPTIONAL) | set(_OPERATOR_RECORD_KEYS) and
                 (case["schema_id"], case["schema_version"]) == CASE_SCHEMA, "CASE_INVALID")
        case = {**_CASE_OPTIONAL, **case}
        _require(all(type(case[k]) is str and Path(case[k]).is_absolute() for k in _PATH_KEYS), "CASE_INVALID")
        _require(all(_operator_record_path_ok(case[k]) for k in _OPERATOR_RECORD_KEYS if k in case), "CASE_INVALID")
        host = case["host"]
        _require(type(host) is dict and set(host) == _HOST_KEYS and _int_in(host["ssh_port"], 1, 65535) and
                 all(type(host[k]) is str for k in _HOST_KEYS - {"ssh_port"}), "CASE_INVALID")
        _require(_menu_ok(case["candidate_menu"]) and type(case["plan_usage_attestation"]) is dict, "CASE_INVALID")
        _require(_int_in(case["oauth_deadline_s"], 1, 300) and _int_in(case["max_hermes_age_s"], 1, 86_400) and
                 _int_in(case["max_public_data_age_s"], 1, 60), "CASE_INVALID")
        _require(type(case["stage_a_authorization_sha256"]) is str and
                 _HEX64.fullmatch(case["stage_a_authorization_sha256"]) is not None, "CASE_INVALID")
        _live_config(case).validate()
        return case
    except CanaryBlocked:
        raise
    except Exception:
        raise CanaryBlocked("CASE_INVALID") from None


def _live_config(case: dict):
    from src.execution_gateway.live_orch import HostCurrentnessConfig, LiveOrchConfig
    host = case["host"]
    return LiveOrchConfig(
        state_root=Path(case["live_orch_state_root"]), expected_signer=case["public_signer_address"],
        expected_wallet=case["deposit_wallet_address"], lifecycle_store_path=Path(case["lifecycle_store_path"]),
        hermes_store_path=Path(case["hermes_store_path"]),
        host=HostCurrentnessConfig(repository_root=Path(host["repository_root"]),
                                   binding_file=Path(host["binding_file"]), active_release=Path(host["active_release"]),
                                   unit_dir=Path(host["unit_dir"]), ssh_port=host["ssh_port"],
                                   expected_release_sha=host["expected_release_sha"]))


# ----------------------------------------------------------------- Stage A (section 4H)


def execution_host_binding_sha256(case: dict) -> str:
    """Pure: SHA-256 of native store.canonical_json over the case's LiveOrchConfig host fields."""
    from src.execution_gateway.store import canonical_json
    return hashlib.sha256(canonical_json(case["host"]).encode("utf-8")).hexdigest()


def read_ledger_head(path: object) -> str:
    """Pure read: the non-empty, replay-valid native ledger head; never creates or opens a gateway."""
    from src.execution_gateway.gateway import _validate_replay
    from src.execution_gateway.store import GatewayStore
    path = Path(path)
    _require(path.is_file(), "STAGE_A_LEDGER_UNINITIALIZED")
    try:
        store = GatewayStore(path)  # non-create mode: a missing or invalid path is refused
    except Exception:
        raise CanaryBlocked("STAGE_A_LEDGER_UNINITIALIZED") from None
    try:
        mapping, head, events = store.load()
        state = _validate_replay(events)
        valid = mapping is not None and type(head) is str and bool(events) and state.to_mapping() == dict(mapping)
    except Exception:
        valid = False
    finally:
        store.close()
    _require(valid and _HEX64.fullmatch(head) is not None, "STAGE_A_LEDGER_UNINITIALIZED")
    return head


def _utc_ns(text: object) -> int:
    _require(type(text) is str and _UTC.fullmatch(text) is not None, "STAGE_A_INVALID")
    try:
        seconds = calendar.timegm(time.strptime(text, "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        raise CanaryBlocked("STAGE_A_INVALID") from None
    return seconds * 1_000_000_000


def _ledger_codes(case: dict, approved_head: str) -> list:
    from src.execution_gateway.live_orch import canonical_live_orch_store_path
    try:
        head = read_ledger_head(canonical_live_orch_store_path(Path(case["live_orch_state_root"]),
                                                               case["deposit_wallet_address"]))
    except CanaryBlocked as error:
        return error.codes
    return [] if head == approved_head else ["STAGE_A_CONSUMED"]


def bind_stage_a(case: dict, *, now_ns: int) -> dict:
    """Machine-verifiable Stage A conformance; raises with every failing STAGE_A_* code."""
    from decimal import Decimal, InvalidOperation
    from src.execution_gateway import live_orch as L
    try:
        raw = _read_bounded(Path(case["stage_a_authorization_path"]))
    except Exception:
        raise CanaryBlocked("STAGE_A_UNAVAILABLE") from None
    _require(hashlib.sha256(raw).hexdigest() == case["stage_a_authorization_sha256"], "STAGE_A_DIGEST_MISMATCH")
    try:
        stage = _strict_json(raw)
    except Exception:
        raise CanaryBlocked("STAGE_A_INVALID") from None
    _require(type(stage) is dict and set(stage) == _STAGE_A_KEYS and
             (stage["schema_id"], stage["schema_version"]) == STAGE_A_SCHEMA, "STAGE_A_INVALID")
    _require(all(type(stage[k]) is str for k in ("release_sha", "live_orch_state_root", "public_signer_address",
                                                  "deposit_wallet_address", "side")) and
             all(type(stage[k]) is str and _HEX64.fullmatch(stage[k]) is not None
                 for k in ("execution_host_binding_sha256", "ledger_head_at_approval")) and
             type(stage["max_create_attempts"]) is int and _menu_ok(stage["approved_menu"]) and
             type(stage["envelope"]) is dict and set(stage["envelope"]) == _ENVELOPE_KEYS and
             all(type(v) is str for v in stage["envelope"].values()), "STAGE_A_INVALID")
    try:
        envelope = {k: Decimal(v) for k, v in stage["envelope"].items()}
    except InvalidOperation:
        raise CanaryBlocked("STAGE_A_INVALID") from None
    start, end = _utc_ns(stage["valid_from_utc"]), _utc_ns(stage["valid_until_utc"])
    _require(0 < end - start <= MAX_STAGE_A_SPAN_NS, "STAGE_A_INVALID")
    codes = []
    if not start <= now_ns < end:
        codes.append("STAGE_A_WINDOW_INVALID")
    native = dict(account_usd=L.AUTHORIZED_ACCOUNT_CAPITAL_USD, order_usd=L.SINGLE_ORDER_WORST_CASE_MAX_USD,
                  aggregate_commitment_usd=L.MAX_TOTAL_EARLY_COMMITMENT_USD,
                  free_collateral_usd=L.MIN_FREE_COLLATERAL_RESERVE_USD)
    if (stage["release_sha"] != case["host"]["expected_release_sha"] or
            stage["execution_host_binding_sha256"] != execution_host_binding_sha256(case) or
            stage["live_orch_state_root"] != case["live_orch_state_root"] or
            stage["public_signer_address"].lower() != case["public_signer_address"].lower() or
            stage["deposit_wallet_address"].lower() != case["deposit_wallet_address"].lower() or
            _canonical(stage["approved_menu"]) != _canonical(case["candidate_menu"]) or
            stage["side"] != "BUY" or stage["max_create_attempts"] != 1 or envelope != native):
        codes.append("STAGE_A_SCOPE_MISMATCH")
    codes += _ledger_codes(case, stage["ledger_head_at_approval"])
    if codes:
        raise CanaryBlocked(*codes)
    return dict(stage, valid_from_ns=start, valid_until_ns=end)


def _recheck_stage_a(case: dict, stage: dict, *, now_ns: int, permit=None, intent=None) -> None:
    codes = [] if stage["valid_from_ns"] <= now_ns < stage["valid_until_ns"] else ["STAGE_A_WINDOW_INVALID"]
    codes += _ledger_codes(case, stage["ledger_head_at_approval"])
    if intent is not None:
        approved = {(m["strategy_version_id"], m["gamma_market_id"], m["condition_id"], m["token_id"])
                    for m in stage["approved_menu"]}
        if (intent.strategy_version_id, intent.gamma_market_id, intent.condition_id, intent.token_id) not in approved \
                or intent.side != "BUY":
            codes.append("STAGE_A_SCOPE_MISMATCH")
        if permit is None or permit.execution_intent_id != intent.execution_intent_id or \
                permit.strategy_version_id != intent.strategy_version_id:
            codes.append("PERMIT_INTENT_MISMATCH")
    if codes:
        raise CanaryBlocked(*codes)


# ----------------------------------------------------------------- check (non-economic)


def _receipt(command: str, offline: bool) -> dict:
    return dict(schema_id="polymarket-live-canary-receipt", schema_version="1.0.0", command=command,
                status="BLOCKED", reason_codes=[], evidence_class="OFFLINE_TEST_ONLY" if offline else "NATIVE_PRODUCTION",
                claim="PROTOCOL_ONLY" if offline else "EXECUTION_MECHANICS_ONLY_NOT_EDGE_OR_PROFIT",
                stage_a_binding=None, stage_a_authorization_sha256=None, active_policy_id=None,
                venue_snapshot_ids=[], seconds_delay_applicability=None, bridge_receipt_id=None,
                bridge_status=None, permit_id=None, execution_intent_id=None, live_orch=None,
                calls=dict(oauth_dispatch=0, confirmation_prompt=0, canary=0, order=0),
                no_live_authority=True, fill_or_profit_claim=False)


def _finish(receipt: dict) -> dict:
    receipt["receipt_id"] = "livecanary:sha256:" + hashlib.sha256(_canonical(receipt)).hexdigest()
    return receipt


def _orchestrator_reader(config, seams: dict):
    from src.execution_gateway import live_orch as L

    def refused(*_args, **_kwargs):  # check never needs a secret, client or pause
        raise L.GatewayError("CHECK_PRIVATE_ACCESS_REFUSED")

    native = L.LiveOrchDependencies()
    deps = L.LiveOrchDependencies(
        clock_ns=seams.get("clock_ns") or native.clock_ns,
        host_currentness=seams.get("host_currentness") or native.host_currentness,
        geoblock=seams.get("geoblock") or native.geoblock,
        venue_fetcher=seams.get("venue_fetcher") or native.venue_fetcher,
        secret_provider_factory=refused, client_factory=refused, pause=refused)
    return L.LiveOrchestrator(config, dependencies=deps), deps


def _check(case: dict, seams: dict, receipt: dict) -> dict:
    """Every precondition, read-only; returns native facts the run reuses."""
    from decimal import Decimal
    from src.execution_gateway import live_orch as L
    from src.exploratory_gate_c.evaluator import (
        EXPLORATORY_RISK_BAND, HERMES_HEALTH_BLOCKING_NEW_EXPOSURE, HERMES_TARGET_BAND_BLOCKING_NEW_EXPOSURE,
        PERMIT_COMPATIBLE_HERMES_ACTIONS,
    )
    config = _live_config(case)
    reader, deps = _orchestrator_reader(config, seams)
    now = deps.clock_ns()
    codes, facts = [], dict(lineage=[], snapshots=[])
    menu = case["candidate_menu"]
    # 1. Native verified stores.
    lifecycle = hermes = alpha = None
    try:
        from src.strategy_lifecycle import load_strategy_lifecycle_store
        result = load_strategy_lifecycle_store(config.lifecycle_store_path)
        lifecycle = result.snapshot if result.is_valid is True else None
    except Exception:
        pass
    try:
        from src.research_runtime.hermes_controlled_runtime.strategy_manager import (
            load_hermes_strategy_manager_store, strategy_lifecycle_context_fingerprint,
        )
        hermes = load_hermes_strategy_manager_store(config.hermes_store_path)
    except Exception:
        pass
    try:
        from src.data_layer.analytical_research.alpha_factory import OpportunityCandidate
        from src.data_layer.analytical_research.alpha_factory_registry import load_and_verify_alpha_factory_registry
        result = load_and_verify_alpha_factory_registry(Path(case["alpha_registry_path"]))
        alpha = result.snapshot if result.is_valid is True else None
    except Exception:
        pass
    codes += [code for store, code in ((lifecycle, "LIFECYCLE_STORE_INVALID"), (hermes, "HERMES_STORE_INVALID"),
                                       (alpha, "ALPHA_STORE_INVALID")) if store is None]
    if lifecycle is not None and hermes is not None and alpha is not None:
        from src.strategy_lifecycle import PORTFOLIO_CAPACITY_VALID, evaluate_portfolio_capacity
        # 2. Active policy, EXPLORATORY_LIVE allocation with budget, native capacity.
        policy = lifecycle.policy_by_id(lifecycle.active_policy_id)
        receipt["active_policy_id"] = None if policy is None else policy.policy_id
        if policy is None:
            codes.append("POLICY_NOT_ACTIVE")
        capacity = evaluate_portfolio_capacity(lifecycle, now)
        candidates = {e.record.candidate_id: e.record for e in alpha.entries if type(e.record) is OpportunityCandidate}
        for item in menu:
            sid = item["strategy_version_id"]
            version = lifecycle.version_by_id(sid)
            allocation = lifecycle.allocation_of(sid)
            target = capacity.strategy_result(sid)
            if allocation is None or policy is None or allocation.policy_id != policy.policy_id:
                codes.append("ALLOCATION_REQUIRED")
            elif (allocation.risk_band != EXPLORATORY_RISK_BAND or not allocation.is_active_at(now) or
                  Decimal(allocation.active_budget_usd) <= 0):
                codes.append("ALLOCATION_NOT_ACTIVE")
            if capacity.status != PORTFOLIO_CAPACITY_VALID or target is None or target.status != PORTFOLIO_CAPACITY_VALID:
                codes.append("PORTFOLIO_CAPACITY_REJECTED")
            # 3. AUTO-01 Alpha lineage.
            candidate = candidates.get(item["candidate_id"])
            if not (candidate is not None and version is not None and
                    {r for r in version.evidence_refs if r.startswith("alphacandidate:sha256:")} == {candidate.candidate_id}
                    and f'market:polymarket:{item["gamma_market_id"]}' in candidate.subject_refs
                    and f'token:polymarket:{item["token_id"]}' in candidate.subject_refs):
                codes.append("ALPHA_STRATEGY_LINEAGE_INVALID")
            # 4. Latest canonical assessment, current and new-exposure compatible, run record resolves.
            latest_id = hermes.latest_assessment_id(sid)
            latest = next((a for a in hermes.assessments if a.assessment_id == latest_id), None)
            runs = [] if latest is None else [r for r in hermes.run_records if r.run_record_id == latest.run_record_id]
            if (version is None or latest is None or len(runs) != 1 or
                    latest.strategy_lifecycle_context_sha256 != strategy_lifecycle_context_fingerprint(lifecycle, sid) or
                    latest.active_policy_id != lifecycle.active_policy_id or
                    (latest.lifecycle_action, latest.risk_direction) not in PERMIT_COMPATIBLE_HERMES_ACTIONS or
                    latest.recommended_health_state in HERMES_HEALTH_BLOCKING_NEW_EXPOSURE or
                    latest.target_risk_band == HERMES_TARGET_BAND_BLOCKING_NEW_EXPOSURE or
                    not now - case["max_hermes_age_s"] * 1_000_000_000 < latest.decision_time_ns <= now):
                codes.append("STRATEGY_ASSESSMENT_UNAVAILABLE")
            else:
                facts["lineage"].append(dict(candidate_id=item["candidate_id"], hermes_assessment_id=latest.assessment_id,
                                             context_sha256=latest.strategy_lifecycle_context_sha256,
                                             active_policy_id=lifecycle.active_policy_id))
    # 5. Strict host currentness and 6. geoblock (native, never retried through another route).
    for step, unavailable in ((reader._host_current, "HOST_NOT_CURRENT"), (reader._geoblock, "ACCESS_NOT_ELIGIBLE")):
        try:
            step()
        except Exception as error:
            codes.append(error.code if isinstance(error, L.GatewayError) else unavailable)
    # 7. One fresh public snapshot per distinct menu market.
    identities = list(dict.fromkeys((m["gamma_market_id"], m["condition_id"], m["token_id"]) for m in menu))
    for gamma_market_id, condition_id, token_id in identities:
        try:
            snapshot = deps.venue_fetcher(gamma_market_id=gamma_market_id, condition_id=condition_id, token_id=token_id)
        except Exception:
            codes.append("VENUE_SNAPSHOT_UNAVAILABLE")
            continue
        if (snapshot.active is not True or snapshot.closed is not False or snapshot.accepting_orders is not True
                or snapshot.enable_order_book is not True):
            codes.append("MARKET_NOT_ELIGIBLE")
        if snapshot.gamma_neg_risk is not False or snapshot.book_neg_risk is not False:
            codes.append("NEG_RISK_UNSUPPORTED")
        if snapshot.fees_enabled is None:
            codes.append("FEE_CONFIGURATION_UNKNOWN")
        if snapshot.seconds_delay not in (None, 0):
            codes.append("SECONDS_DELAY_UNSUPPORTED")
        facts["snapshots"].append(snapshot)
    receipt["venue_snapshot_ids"] = [s.venue_snapshot_id for s in facts["snapshots"]]
    # Absent is admissible only for a post-only PASSIVE_MAKER GTC/GTD intent (LIVE-ORCH section 4F).
    if facts["snapshots"]:
        receipt["seconds_delay_applicability"] = ("POST_ONLY_REQUIRED" if any(
            s.seconds_delay is None for s in facts["snapshots"]) else "CHECKED_ZERO")
    # 8. LIVE-ORCH ledger health (the native read-only replay used by preflight).
    try:
        reader._read_ledger()
    except Exception:
        codes.append("LIVE_ORCH_LEDGER_UNHEALTHY")
    # 9. OAuth pin root and credential directory exist (contents never read).
    if not Path(case["oauth_pin_root"]).is_dir():
        codes.append("OAUTH_PIN_ROOT_MISSING")
    if not Path(case["oauth_credential_dir"]).is_dir():
        codes.append("OAUTH_CREDENTIAL_DIR_MISSING")
    # 10. Stage A binding (machine conformance only).
    try:
        facts["stage_a"] = bind_stage_a(case, now_ns=now)
        receipt.update(stage_a_binding=STAGE_A_BINDING, stage_a_authorization_sha256=case["stage_a_authorization_sha256"])
    except CanaryBlocked as error:
        codes += error.codes
    facts.update(config=config, deps=deps, codes=list(dict.fromkeys(codes)))
    return facts


def check(case_path: object, *, clock_ns=None, host_currentness=None, geoblock=None, venue_fetcher=None) -> dict:
    """Non-economic: no OAuth, key prompt, Gate-B session, order or store write."""
    seams = dict(clock_ns=clock_ns, host_currentness=host_currentness, geoblock=geoblock, venue_fetcher=venue_fetcher)
    receipt = _receipt("check", any(v is not None for v in seams.values()))
    try:
        facts = _check(load_case(case_path), seams, receipt)
        receipt.update(status="BLOCKED" if facts["codes"] else "PASS", reason_codes=facts["codes"] or ["CHECK_PASS"])
    except CanaryBlocked as error:
        receipt["reason_codes"] = error.codes
    except Exception:
        receipt["reason_codes"] = ["CHECK_STEP_FAILED"]
    if receipt["status"] != "PASS":
        receipt.update(stage_a_binding=None)
    return _finish(receipt)


# ----------------------------------------------------------------- run (attended, economic)


def _stdin_is_tty() -> bool:
    try:
        return sys.stdin.isatty()
    except Exception:
        return False


def _emit(value: dict) -> None:
    sys.stdout.write(json.dumps(value, sort_keys=True) + "\n")
    sys.stdout.flush()


def native_oauth_attempt(case: dict, *, candidate_menu, lineage, information_cutoff_ns, clock_ns):
    """Production Stage B: tool surface, eligibility preflight, one request, ONE dispatch."""
    from src.research_runtime.hermes_controlled_runtime import oauth_plan_stage_b as op
    from src.research_runtime.hermes_controlled_runtime.tool_free_stage_b import probe_native_tool_surface
    preflight_record, dispatch_record = (case.get(k) for k in _OPERATOR_RECORD_KEYS)
    _require(all(_operator_record_path_ok(p) for p in (preflight_record, dispatch_record)),
             "OAUTH_PREFLIGHT_INELIGIBLE")
    _require(Path(preflight_record) != Path(dispatch_record), "OAUTH_PREFLIGHT_INELIGIBLE")
    journal = Path(case["oauth_journal_dir"])
    _require(not journal.exists() or (journal.is_dir() and not any(journal.iterdir())), "OAUTH_JOURNAL_NOT_FRESH")
    surface = probe_native_tool_surface(Path(case["oauth_pin_root"]))
    preflight_transport = op.OAuthPlanTransport(Path(case["oauth_pin_root"]), Path(case["oauth_credential_dir"]),
                                               mode="real", operator_record_path=preflight_record)
    eligibility = op.evaluate_preflight(preflight_transport.preflight(), attestation=case["plan_usage_attestation"],
                                        checked_at_ns=clock_ns())
    _require(op.eligibility_is_witnessed(eligibility), "OAUTH_PREFLIGHT_INELIGIBLE")
    issued = clock_ns()
    _require(0 <= issued - eligibility.checked_at_ns <= op.MAX_ELIGIBILITY_AGE_NS, "OAUTH_PREFLIGHT_INELIGIBLE")
    request = op.build_oauth_request(surface_report=surface, candidate_menu=candidate_menu, lineage=lineage,
                                     information_cutoff_ns=information_cutoff_ns, issued_at_ns=issued,
                                     deadline_ns=issued + case["oauth_deadline_s"] * 1_000_000_000)
    dispatch_transport = op.OAuthPlanTransport(Path(case["oauth_pin_root"]), Path(case["oauth_credential_dir"]),
                                              mode="real", operator_record_path=dispatch_record)
    return op.run_oauth_attempt(request, eligibility=eligibility, transport=dispatch_transport, journal_dir=journal,
                                clock_ns=clock_ns), request.deadline_ns


def run(case_path: object, *, clock_ns=None, host_currentness=None, geoblock=None, venue_fetcher=None,
        oauth_attempt=None, confirmation_reader=None, orchestrator_factory=None) -> dict:
    """Attended: at most one LiveOrchestrator.canary call; every failure is zero canary."""
    seams = dict(clock_ns=clock_ns, host_currentness=host_currentness, geoblock=geoblock, venue_fetcher=venue_fetcher)
    offline = any(v is not None for v in (*seams.values(), oauth_attempt, confirmation_reader, orchestrator_factory))
    receipt = _receipt("run", offline)
    calls = receipt["calls"]
    lock = None
    try:
        # Fakes never reach the production economic path; checked before any I/O.
        _require(not offline or orchestrator_factory is not None, "OFFLINE_SEAM_IN_ECONOMIC_PATH")
        _require(_stdin_is_tty(), "ATTENDED_TTY_REQUIRED")
        case = load_case(case_path)
        from src.execution_gateway import live_orch as L
        from src.execution_gateway.gate_b import WalletSessionLock
        try:
            lock = WalletSessionLock(Path(case["live_orch_state_root"]) / "live_canary",
                                     case["deposit_wallet_address"]).acquire()
        except L.GatewayError:
            raise CanaryBlocked("STAGE_A_RUN_LOCKED") from None
        facts = _check(case, seams, receipt)
        if facts["codes"]:
            raise CanaryBlocked(*facts["codes"])
        stage, deps = facts["stage_a"], facts["deps"]
        clock = deps.clock_ns
        # Fresh native menu snapshots; the information cutoff is the latest acquisition.
        try:
            snapshots = [deps.venue_fetcher(gamma_market_id=s.gamma_market_id, condition_id=s.condition_id,
                                            token_id=s.token_id) for s in facts["snapshots"]]
        except Exception:
            raise CanaryBlocked("VENUE_SNAPSHOT_UNAVAILABLE") from None
        cutoff = max(s.acquisition_completed_ns for s in snapshots)
        calls["oauth_dispatch"] += 1
        try:
            result, deadline = (oauth_attempt or native_oauth_attempt)(
                case, candidate_menu=case["candidate_menu"], lineage=facts["lineage"], information_cutoff_ns=cutoff,
                clock_ns=clock)
        except CanaryBlocked:
            raise
        except Exception:  # probe, transport or request failure: no retry, no second dispatch
            raise CanaryBlocked("OAUTH_ATTEMPT_FAILED") from None
        from src.research_runtime.hermes_controlled_runtime.oauth_plan_stage_b import is_witnessed_result
        _require(is_witnessed_result(result), "OAUTH_RESULT_NOT_WITNESSED")
        from src.research_runtime.live_preflight_bridge import prepare_live_canary_handoff
        bridge, permit, intent = prepare_live_canary_handoff(
            result, live_config=facts["config"], alpha_registry_path=Path(case["alpha_registry_path"]),
            candidate_menu=case["candidate_menu"], menu_venue_snapshots=tuple(snapshots), evaluated_at_ns=clock(),
            information_cutoff_ns=cutoff, deadline_ns=deadline,
            max_public_data_age_ns=case["max_public_data_age_s"] * 1_000_000_000,
            max_hermes_age_ns=case["max_hermes_age_s"] * 1_000_000_000, **seams)
        receipt.update(bridge_receipt_id=bridge["receipt_id"], bridge_status=bridge["status"])
        if bridge["status"] != "PASS" or permit is None:
            receipt.update(status="ABSTAIN" if bridge["status"] == "ABSTAIN" else "BLOCKED",
                           reason_codes=list(bridge["reason_codes"]) or ["BRIDGE_NOT_PASS"])
            return _finish(receipt)
        _require(offline or bridge["evidence_class"] != "OFFLINE_TEST_ONLY", "OFFLINE_HANDOFF_IN_PRODUCTION")
        receipt.update(permit_id=permit.permit_id, execution_intent_id=intent.execution_intent_id)
        _recheck_stage_a(case, stage, now_ns=clock(), permit=permit, intent=intent)
        details = bridge["preflight_details"]
        displayed = clock()
        _emit(dict(record="order_summary", strategy_version_id=intent.strategy_version_id,
                   gamma_market_id=intent.gamma_market_id, condition_id=intent.condition_id, token_id=intent.token_id,
                   side=intent.side, requested_shares=intent.requested_shares, price_limit=intent.price_limit,
                   principal_usd=details.get("principal_notional_usd"),
                   fee_reserve_usd=details.get("worst_case_fee_reserve_usd"),
                   figures="BRIDGE_TIME_INFORMATIONAL_NATIVE_USD5_CAP_ENFORCED_AT_ADMISSION",
                   permit_id=permit.permit_id, execution_intent_id=intent.execution_intent_id,
                   stage_a_authorization_sha256=case["stage_a_authorization_sha256"],
                   stage_a_valid_until_utc=stage["valid_until_utc"],
                   seconds_left_in_permit_window=max(0, (permit.valid_until_ns - displayed) // 1_000_000_000)))
        # Stage B: phrase + permit and Stage A suffixes (a human correlation check, not authentication).
        expected = f"{L.LIVE_ORCH_CONFIRMATION_PHRASE} {permit.permit_id[-12:]} {case['stage_a_authorization_sha256'][-12:]}"
        calls["confirmation_prompt"] += 1
        try:
            typed = (confirmation_reader or input)(
                f"Type {L.LIVE_ORCH_CONFIRMATION_PHRASE} <last 12 of permit_id> <last 12 of Stage A digest>: ")
        except EOFError:
            typed = None
        _require(typed == expected, "OWNER_CONFIRMATION_MISMATCH")
        _emit(dict(record="stage_b_confirmation", permit_id=permit.permit_id,
                   execution_intent_id=intent.execution_intent_id,
                   stage_a_authorization_sha256=case["stage_a_authorization_sha256"],
                   displayed_at_ns=displayed, confirmed_at_ns=clock(), authorization="EVIDENCE_ONLY_NOT_AUTHORIZATION"))
        # Last boundary, under the still-held run lock.
        _recheck_stage_a(case, stage, now_ns=clock(), permit=permit, intent=intent)
        orchestrator = orchestrator_factory(facts["config"]) if offline else L.LiveOrchestrator(facts["config"])
        calls["canary"] += 1
        outcome = orchestrator.canary(permit, intent)
        calls["order"] = outcome.create_transmits
        receipt.update(status=outcome.status, reason_codes=[outcome.code], live_orch=outcome.to_mapping())
        if outcome.episode_id is not None and outcome.episode_state not in CLEAN_TERMINAL_STATES:
            receipt["reconcile_required"] = True
    except CanaryBlocked as error:
        receipt.update(status="BLOCKED", reason_codes=error.codes)
    except Exception as error:  # native validation code only; never the message or input
        code = getattr(error, "code", None)
        receipt.update(status="BLOCKED", reason_codes=[code if isinstance(code, str) and code.isupper()
                                                       and len(code) <= 64 else "RUN_STEP_FAILED"])
        if calls["canary"]:  # never claim a clean outcome once canary was entered
            receipt["reconcile_required"] = True
    finally:
        if lock is not None:
            lock.close()
    return _finish(receipt)


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="python -m src.execution_gateway.live_canary")
    parser.add_argument("command", choices=("check", "run"))
    parser.add_argument("--case", required=True)
    args = parser.parse_args(argv)
    receipt = check(args.case) if args.command == "check" else run(args.case)
    _emit(receipt)
    if receipt.get("reconcile_required"):
        # Operator terminal only, never part of the sanitized receipt; no automatic reconcile loop.
        case = load_case(args.case)
        host = case["host"]
        sys.stdout.write(" ".join([
            "Episode is not clean-terminal. Run: python -m src.execution_gateway.live_orch reconcile",
            "--state-root", case["live_orch_state_root"], "--expected-signer", case["public_signer_address"],
            "--expected-wallet", case["deposit_wallet_address"], "--lifecycle-store", case["lifecycle_store_path"],
            "--hermes-store", case["hermes_store_path"], "--repository-root", host["repository_root"],
            "--binding-file", host["binding_file"], "--active-release", host["active_release"],
            "--unit-dir", host["unit_dir"], "--ssh-port", str(host["ssh_port"]),
            "--expected-release-sha", host["expected_release_sha"]]) + "\n")
    return 0 if receipt["status"] in ("PASS", "CANARY_COMPLETE") else 2


if __name__ == "__main__":
    sys.exit(main())
