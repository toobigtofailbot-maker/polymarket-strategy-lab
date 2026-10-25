"""S10-HERMES-AUTO-02-REAL-01-ACTIVATION: official ChatGPT-plan OAuth one-call Stage B.

Offline only. The verdict, eligibility, journal and origin matrix runs on recorded child
reports of the exact shape the pinned child emits. When the exact pinned Hermes v0.21.3
checkout is present (local operator machine) the child itself runs in ``mode="mock"``: every
HTTP call (token, JWKS, model catalogue, Responses SSE) is an in-memory fixture and every
non-loopback socket is denied. NO_PROVIDER_CALL: no credential, OAuth account or provider
is used anywhere in this file.
"""
import copy
import dataclasses
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import os

import pytest

from src.research_runtime.hermes_controlled_runtime import oauth_plan_stage_b as op
from src.research_runtime.hermes_controlled_runtime import tool_free_stage_b as tf
from tests.research_runtime.hermes_controlled_runtime.test_tool_free_stage_b import PIN_ROOT, RECORDED_REPORT

ROOT = Path(__file__).resolve().parents[3]
T0 = 1_790_000_000_000_000_000
DEADLINE = T0 + 60_000_000_000
MODEL = op.ROUTE["model"]
MENU = [dict(candidate_id="alphacandidate:sha256:" + "1" * 64, strategy_version_id="strategyversion:sha256:" + "2" * 64,
             gamma_market_id="123", condition_id="0x" + "3" * 64, token_id="456")]
LINEAGE = [dict(candidate_id=MENU[0]["candidate_id"], hermes_assessment_id="hermesassessment:sha256:" + "4" * 64,
                context_sha256="5" * 64, active_policy_id="portfoliopolicy:sha256:" + "6" * 64)]
NO_TRADE = json.dumps(dict(action="NO_TRADE", proof_level="SYNTHETIC_ONLY", information_cutoff_ns=T0,
                           produced_at_ns=T0, expires_at_ns=DEADLINE))
ATTEST = dict(purchased_credits_disabled=True, model_visible_in_chatgpt=True, source="OPERATOR_ATTESTATION")
SCOPES = sorted(op.REQUIRED_SCOPES)


def make_request(menu=MENU, lineage=LINEAGE):
    return op.build_oauth_request(surface_report=RECORDED_REPORT, candidate_menu=menu, lineage=lineage,
                                  information_cutoff_ns=T0, issued_at_ns=T0, deadline_ns=DEADLINE)


REQUEST = make_request()


def set_path(report, changes):
    for path, value in changes.items():
        target, keys = report, path.split(".")
        for key in keys[:-1]:
            target = target[int(key)] if isinstance(target, list) else target[key]
        target[keys[-1]] = value
    return report


def preflight(mode="real", **changes):
    """Recorded shape of one real-mode preflight child report (synthetic values)."""
    report = dict(schema="oauth-plan-child-v1", phase="preflight", mode=mode, status="DONE", reason_code=None,
                  error_class=None, api_key_env_present=False, tls_verify=True, trust_env=False,
                  hermes_commit=tf.PINNED_HERMES_COMMIT, runtime_profile_sha256=RECORDED_REPORT["runtime_profile_sha256"], refreshed=False, token_seconds_remaining=3000,
                  scopes_granted=SCOPES, access_audience_ok=True, access_issuer_ok=True, client_match=True,
                  client_id_sha256="c" * 64, models_status=200, models_count=7, target_listed=True,
                  target_visibility="list", network_attempts=[["api.openai.com", 443, True]],
                  http_calls=[["GET", "api.openai.com", "/v1/models", 200]])
    return set_path(report, changes)


def sent(request=REQUEST, **changes):
    value = dict(method="POST", scheme="https", host="api.openai.com", port=None, path="/v1/responses",
                 body_sha256="f" * 64, body_bytes=1500, model=MODEL, stream=True, store=False,
                 body_keys=sorted(["include", "input", "instructions", "model", "prompt_cache_key", "reasoning",
                                   "store", "stream"]), include=["reasoning.encrypted_content"], tools_count=0,
                 input_roles=["user"], input_sha256=hashlib.sha256(op.real01._canon_input(request.model_input.decode())).hexdigest(),
                 instructions_sha256=request.instructions_sha256, authorization_bearer=True, retry_count_header="0")
    value.update(changes)
    return value


def dispatch(request=REQUEST, *, text=NO_TRADE, mode="real", **changes):
    """Recorded shape of one dispatch child report (synthetic values, no provider)."""
    report = dict(schema="oauth-plan-child-v1", phase="dispatch", mode=mode, status="DONE", reason_code=None,
                  error_class=None, api_key_env_present=False, tls_verify=True, trust_env=False,
                  hermes_commit=tf.PINNED_HERMES_COMMIT, runtime_profile_sha256=RECORDED_REPORT["runtime_profile_sha256"], hermes_version="0.21.3", construction_network_attempts=[],
                  token_seconds_remaining=3000, scopes_granted=SCOPES, sdk_max_retries=0, requests=[sent(request)],
                  presend_block=None, client_stop=None, http_status=None, failed_code=None,
                  terminal_events=["response.completed"], event_count=6, server_model=MODEL,
                  response_id_sha256="e" * 64, x_request_id_sha256="d" * 64,
                  usage=dict(input_tokens=400, output_tokens=60, total_tokens=460),
                  final=dict(status="completed", output_types=["reasoning", "message"], output_text=text),
                  network_attempts=[["api.openai.com", 443, True]] if mode == "real" else [],
                  http_calls=[["POST", "api.openai.com", "/v1/responses", 200]])
    return set_path(report, changes)


def classify(report, request=REQUEST, finished=T0 + 2):
    return op.classify_dispatch_report(request, report, dispatched_at_ns=T0 + 1, finished_at_ns=finished)


def eligible(checked=T0):
    verdict = op.evaluate_preflight(preflight(), attestation=dict(ATTEST), checked_at_ns=checked)
    assert verdict.status == op.PLAN_USAGE_ELIGIBLE and op.eligibility_is_witnessed(verdict)
    return verdict


def clock(start=T0 + 1):
    ticks = iter(range(start, start + 1000))
    return lambda: next(ticks)


class Spy:
    """Patched child runner: records each phase; returns (a copy of) the recorded outcome."""

    def __init__(self, monkeypatch, outcome):
        self.phases, self.outcome = [], outcome
        monkeypatch.setattr(op.OAuthPlanTransport, "_run_child", self._run)

    def _run(self, phase, extra, timeout_s):
        self.phases.append(phase)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return copy.deepcopy(self.outcome)


def transport(tmp_path, mode="real"):
    return op.OAuthPlanTransport(PIN_ROOT, tmp_path / "credentials", mode=mode,
                                 mock=None if mode == "real" else {"responses": {"kind": "http", "status": 500}})


def require_pin():
    if not (PIN_ROOT / ".git" / "HEAD").is_file():
        pytest.skip("exact pinned Hermes v0.21.3 checkout unavailable; recorded-report matrix only")


def mock_world(tmp_path, *, scenario=None, models=None, token=None, callback=None):
    """Native child in mock mode: in-memory OAuth/JWKS/catalogue/Responses, sockets denied."""
    mock = dict(responses=scenario or dict(kind="http", status=500),
                models=models or dict(status=200, body=dict(models=[dict(slug=MODEL, display_name="Sol", visibility="list")])))
    if token is not None:
        mock["token"] = token
    if callback is not None:
        mock["callback"] = callback
    return op.OAuthPlanTransport(PIN_ROOT, tmp_path / "creds", mode="mock", mock=mock, login_wait_s=30)


def sse_message(text, *, model=MODEL, usage=(10, 5, 15), extra_items=()):
    events = []
    for index, item in enumerate(extra_items):
        events += [dict(type="response.output_item.added", output_index=index, item=dict(item, status="in_progress")),
                   dict(type="response.output_item.done", output_index=index, item=dict(item, status="completed"))]
    index = len(extra_items)
    item = dict(id="m1", type="message", role="assistant", content=[])
    events += [dict(type="response.output_item.added", output_index=index, item=item),
               dict(type="response.output_text.delta", item_id="m1", output_index=index, delta=text),
               dict(type="response.output_item.done", output_index=index,
                    item=dict(item, status="completed", content=[dict(type="output_text", text=text)])),
               dict(type="response.completed", response=dict(
                   id="resp_mock", model=model, status="completed",
                   usage=dict(zip(("input_tokens", "output_tokens", "total_tokens"), usage))))]
    return dict(kind="sse", events=events)


# --------------------------------------------------------------------- R001


def test_oauth_plan_entitlement_fails_closed(tmp_path, monkeypatch):
    verdict = eligible()
    assert verdict.model == MODEL and verdict.reason_code is None and verdict.eligibility_id.startswith("oauthplaneligibility:")
    # One refresh before inference is a counted control-plane call, never an inference.
    refreshed = preflight(refreshed=True, http_calls=[["POST", "auth.openai.com", "/api/accounts/oauth/token", 200],
                                                      ["GET", "api.openai.com", "/v1/models", 200]],
                          network_attempts=[["auth.openai.com", 443, True], ["api.openai.com", 443, True]])
    assert op.evaluate_preflight(refreshed, attestation=dict(ATTEST), checked_at_ns=T0).status == op.PLAN_USAGE_ELIGIBLE
    blocked = {
        "PLAN_SCOPE_MISSING": preflight(scopes_granted=[s for s in SCOPES if s != op.PLAN_SCOPE]),
        "ACCESS_TOKEN_BINDING_INVALID": preflight(access_audience_ok=False),
        "OAUTH_MODEL_NOT_AVAILABLE": preflight(target_listed=False),
        "MODEL_CATALOG_UNAVAILABLE": preflight(models_status=401, models_count=None),
        "API_KEY_ENV_PRESENT": preflight(api_key_env_present=True),
        "CREDENTIAL_MISSING": preflight(status="BLOCKED", reason_code="CREDENTIAL_MISSING"),
        "REFRESH_FAILED": preflight(status="BLOCKED", reason_code="REFRESH_FAILED"),
        "UNEXPECTED_NETWORK_TARGET": preflight(network_attempts=[["chatgpt.com", 443, False]]),
        "CONTROL_PLANE_UNEXPECTED": preflight(http_calls=[["GET", "api.openai.com", "/v1/models", 200],
                                                          ["POST", "api.openai.com", "/v1/responses", 200]]),
        "TOKEN_STALE": preflight(token_seconds_remaining=30),
        "PIN_MISMATCH": preflight(hermes_commit="0" * 40),
        "MOCK_TRANSPORT_NOT_ELIGIBLE": preflight(mode="mock", network_attempts=[]),
        "PREFLIGHT_REPORT_INVALID": dispatch(),
    }
    for code, report in blocked.items():
        result = op.evaluate_preflight(report, attestation=dict(ATTEST), checked_at_ns=T0)
        assert result.status == op.PLAN_USAGE_UNVERIFIED and result.reason_code == code, (code, result.reason_code)
        assert not op.eligibility_is_witnessed(result)
    # Purchased-credit state is operator attestation only; anything less is unverified.
    for attestation in (None, {}, dict(ATTEST, purchased_credits_disabled=False), dict(ATTEST, source="MODEL"),
                        dict(ATTEST, extra=True)):
        assert op.evaluate_preflight(preflight(), attestation=attestation, checked_at_ns=T0).reason_code == \
            "CREDITS_STATUS_UNVERIFIED"
    forged = dataclasses.replace(verdict, model="gpt-other")
    assert not op.eligibility_is_witnessed(forged)
    assert not op.eligibility_is_witnessed(dataclasses.replace(verdict, _witness=object()))
    # No eligibility, forged, stale or unwitnessed eligibility: zero dispatch, nothing reserved.
    spy = Spy(monkeypatch, dispatch())
    for index, (value, code) in enumerate(((None, "PLAN_ELIGIBILITY_NOT_ESTABLISHED"),
                                           (forged, "PLAN_ELIGIBILITY_NOT_ESTABLISHED"),
                                           (op.evaluate_preflight(preflight(target_listed=False), attestation=ATTEST,
                                                                  checked_at_ns=T0), "PLAN_ELIGIBILITY_NOT_ESTABLISHED"),
                                           (eligible(T0 - op.MAX_ELIGIBILITY_AGE_NS - 10), "PLAN_ELIGIBILITY_STALE"))):
        journal = tmp_path / f"j{index}"
        result = op.run_oauth_attempt(REQUEST, eligibility=value, transport=transport(tmp_path), journal_dir=journal,
                                      clock_ns=clock())
        assert result.status == code and result.origin is None and not journal.exists()
    assert spy.phases == []
    # Credentials never live in the repository; real/mock mode is explicit.
    for bad in (ROOT / "local_credentials", ROOT):
        with pytest.raises(ValueError, match="CREDENTIAL_DIR_INSIDE_REPOSITORY"):
            op.OAuthPlanTransport(PIN_ROOT, bad)
    with pytest.raises(ValueError, match="CREDENTIAL_DIR_NOT_ABSOLUTE"):
        op.OAuthPlanTransport(PIN_ROOT, Path("relative"))
    for mode, mock in (("real", {}), ("mock", None), ("live", None)):
        with pytest.raises(ValueError, match="TRANSPORT_MODE_INVALID"):
            op.OAuthPlanTransport(PIN_ROOT, tmp_path / "c", mode=mode, mock=mock)
    # The child source holds the official endpoints only; no API-key or internal backend route.
    source = op._CHILD_SOURCE
    for forbidden in ("OPENAI_API_KEY", "chatgpt.com", "backend-api", "max_output_tokens", "verify=False", "print(record",
                      "auth.json"):
        assert forbidden not in source
    assert op.TOKEN_URL == "https://auth.openai.com/api/accounts/oauth/token" and op.RESOURCE == "https://api.openai.com/v1"
    assert op.AUTHORIZE_URL == "https://auth.openai.com/api/accounts/authorize" and op.PLAN_SCOPE in op.REQUIRED_SCOPES
    assert "code_challenge_method=\"S256\"" in source and "dynamic_agent_client" in source and '"127.0.0.1"' in source
    # Native phase-split coverage is in R001 (Windows) and R004 (Linux),
    # with exact records and journal admission; the unbound world is invalid.
    if (PIN_ROOT / ".git/HEAD").is_file():
        monkeypatch.undo()
        refused = mock_world(tmp_path).login()
        assert refused["status"] == "BLOCKED" and refused["http_calls"] == []
        assert not (tmp_path / "creds").exists()


# --------------------------------------------------------------------- R002


def test_official_oauth_hermes_toolfree_wire_strict(tmp_path, monkeypatch):
    verdict = op.verify_dispatch_wire(REQUEST, dispatch())
    assert verdict["status"] == op.real01.WIRE_CHECKED and verdict["wire_stage"] == "POST_SDK_PRESEND_CAPTURED", verdict
    for changes, code in (
            ({"requests.0.tools_count": 1}, "WIRE_UNSUPPORTED_OR_TOOL_FIELD"),
            ({"requests.0.body_keys": sorted(sent()["body_keys"] + ["tools"])}, "WIRE_UNSUPPORTED_OR_TOOL_FIELD"),
            ({"requests.0.body_keys": sorted(sent()["body_keys"] + ["tool_choice"])}, "WIRE_UNSUPPORTED_OR_TOOL_FIELD"),
            ({"requests.0.body_keys": sorted(sent()["body_keys"] + ["max_output_tokens"])}, "WIRE_UNSUPPORTED_OR_TOOL_FIELD"),
            ({"requests.0.body_keys": sorted(sent()["body_keys"] + ["metadata"])}, "WIRE_UNSUPPORTED_OR_TOOL_FIELD"),
            ({"requests.0.body_keys": sorted(sent()["body_keys"] + ["temperature"])}, "WIRE_UNSUPPORTED_OR_TOOL_FIELD"),
            ({"requests.0.body_keys": sorted(sent()["body_keys"] + ["background"])}, "WIRE_UNSUPPORTED_OR_TOOL_FIELD"),
            ({"requests.0.body_keys": sorted(sent()["body_keys"] + ["text"])}, "UNEXPECTED_REQUEST_FIELD"),
            ({"requests.0.body_keys": ["input", "model", "stream"]}, "UNEXPECTED_REQUEST_FIELD"),
            ({"requests.0.include": ["file_search_call.results"]}, "UNEXPECTED_REQUEST_FIELD"),
            ({"requests.0.store": True}, "WIRE_MODEL_OR_MODE_MISMATCH"),
            ({"requests.0.store": None}, "WIRE_MODEL_OR_MODE_MISMATCH"),
            ({"requests.0.stream": False}, "WIRE_MODEL_OR_MODE_MISMATCH"),
            ({"requests.0.model": "gpt-5.6-sol"}, "WIRE_MODEL_OR_MODE_MISMATCH"),
            ({"requests.0.input_roles": ["system", "user"]}, "WIRE_INPUT_ROLE_INVALID"),
            ({"requests.0.input_sha256": "0" * 64}, "WIRE_INPUT_MISMATCH"),
            ({"requests.0.host": "chatgpt.com", "requests.0.path": "/backend-api/codex/responses"}, "UNEXPECTED_ENDPOINT"),
            ({"requests.0.scheme": "http"}, "UNEXPECTED_ENDPOINT"),
            ({"requests.0.authorization_bearer": False}, "WIRE_AUTH_SHAPE_INVALID"),
            ({"requests.0.retry_count_header": None}, "SDK_RETRY_ENABLED"),
            ({"sdk_max_retries": 2}, "SDK_RETRY_ENABLED"),
            ({"presend_block": "PRESEND_WIRE_REJECTED"}, "PRESEND_WIRE_REJECTED"),
            ({"construction_network_attempts": [["models.dev", 443, False]]}, "UNEXPECTED_NETWORK_ATTEMPT"),
            ({"network_attempts": [["api.openai.com", 443, True], ["telemetry.example", 443, False]]},
             "UNEXPECTED_NETWORK_ATTEMPT"),
            ({"api_key_env_present": True}, "UNSAFE_CHILD_ENVIRONMENT"),
            ({"tls_verify": False}, "UNSAFE_CHILD_ENVIRONMENT"),
            ({"requests": [sent(), sent()]}, "MULTIPLE_DISPATCH_INVALID"),
            ({"requests": []}, "NOT_DISPATCHED"),
            ({"hermes_version": "0.22.0"}, "PIN_MISMATCH")):
        result = op.verify_dispatch_wire(REQUEST, dispatch(**changes))
        assert result["status"] == op.real01.WIRE_BLOCKED and result["reason_code"] == code, (changes, result)
        status, _, raw = classify(dispatch(**changes))
        assert status == code and raw is None
    # A child-blocked dispatch never classifies as provider output.
    assert classify(dispatch(status="BLOCKED", reason_code="TOKEN_NEAR_EXPIRY", requests=[]))[0] == \
        "DISPATCH_BLOCKED_TOKEN_NEAR_EXPIRY"
    # Request identity: pinned model, bounded input, tool-free surface from the verified probe.
    assert op.request_is_bound(REQUEST) and REQUEST.model == "gpt-6.1-sol" and REQUEST.base_url == "https://api.openai.com/v1"
    assert len(REQUEST.model_input) <= op.MAX_REQUEST_INPUT_BYTES and len(op.INSTRUCTIONS.encode()) < 1_024
    assert not op.request_is_bound(dataclasses.replace(REQUEST, model="gpt-5.6-sol"))
    assert not op.request_is_bound(dataclasses.replace(REQUEST, model_input=REQUEST.model_input + b" "))
    with pytest.raises(ValueError, match="REQUEST_INPUT_TOO_LARGE"):
        make_request(menu=MENU, lineage=LINEAGE * 8)
    for broken in ({**RECORDED_REPORT, "hermes_commit": "0" * 40}, {}):
        with pytest.raises(ValueError):
            op.build_oauth_request(surface_report=broken, candidate_menu=MENU, information_cutoff_ns=T0,
                                   issued_at_ns=T0, deadline_ns=DEADLINE)
    script = '''import sys
import src.research_runtime.hermes_controlled_runtime
def guard(name, args):
    if name.startswith(("socket.", "subprocess.Popen", "sqlite3.connect", "os.system", "os.putenv")): raise RuntimeError(name)
sys.addaudithook(guard)
import src.research_runtime.hermes_controlled_runtime.oauth_plan_stage_b
print("IMPORT_NO_IO_PASS")
'''
    imported = subprocess.run([sys.executable, "-B", "-c", script], cwd=ROOT, capture_output=True, text=True)
    assert imported.returncode == 0 and "IMPORT_NO_IO_PASS" in imported.stdout, imported.stderr
    # Native phase-split coverage is in R001 (Windows) and R004 (Linux),
    # with exact records and journal admission; the unbound world is invalid.
    assert op.REFRESH_MARGIN_S - 60 - op.MAX_ELIGIBILITY_AGE_NS // 10**9 >= op.MIN_TOKEN_SECONDS


# --------------------------------------------------------------------- R003


def test_oauth_one_post_crash_replay_no_retry(tmp_path, monkeypatch):
    outcomes = (
        (dispatch(), op.VALID_OUTPUT),
        (dispatch(http_calls=[["POST", "api.openai.com", "/v1/responses", 429]], final=None, error_class="RateLimitError",
                  terminal_events=[]), "PROVIDER_RATE_LIMITED"),
        (dispatch(http_calls=[["POST", "api.openai.com", "/v1/responses", 503]], final=None,
                  error_class="InternalServerError", terminal_events=[]), "PROVIDER_SERVER_ERROR"),
        (dispatch(final=dict(status="incomplete", output_types=["message"], output_text=NO_TRADE),
                  terminal_events=["response.incomplete"]), "RESPONSE_INCOMPLETE"),
        (dispatch(http_calls=[], final=None, error_class="APITimeoutError", terminal_events=[]), "PROVIDER_TIMEOUT"),
        (subprocess.TimeoutExpired("child", 1), "ATTEMPT_TIMEOUT_CONSUMED"),
        (RuntimeError("child crashed"), "ATTEMPT_TRANSPORT_FAILED_CONSUMED"),
    )
    for index, (outcome, status) in enumerate(outcomes):
        spy = Spy(monkeypatch, outcome)
        wire = transport(tmp_path)
        journal = tmp_path / f"journal{index}"
        first = op.run_oauth_attempt(REQUEST, eligibility=eligible(), transport=wire, journal_dir=journal, clock_ns=clock())
        assert first.status == status and spy.phases == ["dispatch"] and wire.dispatch_count == 1, (status, first)
        assert first.origin["application_retries"] == 0 and first.origin["fallback_used"] is False
        assert first.origin["token_refresh_during_dispatch"] is False
        assert (first.output_bytes is not None) == (status == op.VALID_OUTPUT)
        for _ in range(2):  # cold replay: stored terminal, zero redispatch, never a witness
            again = op.run_oauth_attempt(REQUEST, eligibility=eligible(), transport=wire, journal_dir=journal,
                                         clock_ns=clock())
            assert again.replayed and again.status == status and again.origin == first.origin
            assert not op.is_witnessed_result(again)
        other = op.run_oauth_attempt(make_request(lineage=[]), eligibility=eligible(), transport=wire, journal_dir=journal,
                                     clock_ns=clock())
        assert other.status == "JOURNAL_ALREADY_CONSUMED" and wire.dispatch_count == 1 and spy.phases == ["dispatch"]
    # Timeout/crash consumed the attempt with unknown provider outcome: honest, never retried.
    timed = json.loads((tmp_path / "journal5" / "oauthplan-attempt.json").read_bytes())
    assert timed["provider_invocation"] == "PROVIDER_INVOCATION_UNKNOWN" and timed["real_origin"] == op.REAL_ORIGIN_UNVERIFIED
    # Interrupted earlier attempt (reservation, no terminal): consumed, no dispatch.
    spy = Spy(monkeypatch, dispatch())
    crashed = tmp_path / "crashed"
    crashed.mkdir()
    (crashed / "oauthplan-attempt.reserved").write_bytes(REQUEST.request_id.encode())
    assert op.run_oauth_attempt(REQUEST, eligibility=eligible(), transport=transport(tmp_path), journal_dir=crashed,
                                clock_ns=clock()).status == "ATTEMPT_ALREADY_RESERVED"
    assert spy.phases == []
    # Tampered terminal: JOURNAL_INVALID, no dispatch.
    tampered = tmp_path / "journal0" / "oauthplan-attempt.json"
    record = json.loads(tampered.read_bytes())
    tampered.write_bytes(json.dumps(dict(record, status="FORGED")).encode())
    assert op.run_oauth_attempt(REQUEST, eligibility=eligible(), transport=transport(tmp_path),
                                journal_dir=tmp_path / "journal0", clock_ns=clock()).status == "JOURNAL_INVALID"
    assert spy.phases == []
    # Concurrent callers on one journal: exactly one dispatch.
    gate = threading.Barrier(6)
    shared = transport(tmp_path)
    def slow(wire, phase, extra, timeout_s):
        spy.phases.append(phase)
        return copy.deepcopy(dispatch())
    monkeypatch.setattr(op.OAuthPlanTransport, "_run_child", slow)
    results = []
    def worker():
        gate.wait()
        results.append(op.run_oauth_attempt(REQUEST, eligibility=eligible(), transport=shared,
                                            journal_dir=tmp_path / "concurrent", clock_ns=clock()).status)
    threads = [threading.Thread(target=worker) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert spy.phases == ["dispatch"] and shared.dispatch_count == 1 and results.count(op.VALID_OUTPUT) >= 1
    assert set(results) <= {op.VALID_OUTPUT, "ATTEMPT_ALREADY_RESERVED"}
    # Expired window or invalid transport: nothing reserved.
    late = op.run_oauth_attempt(REQUEST, eligibility=eligible(DEADLINE), transport=transport(tmp_path),
                                journal_dir=tmp_path / "late", clock_ns=clock(DEADLINE))
    assert late.status == "DEADLINE_EXCEEDED_NOT_DISPATCHED" and not (tmp_path / "late").exists()
    assert op.run_oauth_attempt(REQUEST, eligibility=eligible(), transport=object(), journal_dir=tmp_path / "x").status == \
        "REQUEST_OR_TRANSPORT_INVALID"
    # Native phase-split coverage is in R001 (Windows) and R004 (Linux),
    # with exact records and journal admission; the unbound world is invalid.


def test_oauth_terminal_publication_is_atomic(tmp_path, monkeypatch):
    """S10-HERMES-OAUTH-JOURNAL-01: no reader ever observes a partially written terminal."""
    import os
    spy = Spy(monkeypatch, dispatch())
    wire = transport(tmp_path)
    journal = tmp_path / "journal"
    terminal = journal / "oauthplan-attempt.json"
    # Freeze the writer after its bytes are written but before publication, deterministically.
    written, release, seen = threading.Event(), threading.Event(), []
    real_fsync = os.fsync

    def paused_fsync(fd):
        real_fsync(fd)
        written.set()
        assert release.wait(10)
    monkeypatch.setattr(os, "fsync", paused_fsync)
    writer_result = []
    writer = threading.Thread(target=lambda: writer_result.append(op.run_oauth_attempt(
        REQUEST, eligibility=eligible(), transport=wire, journal_dir=journal, clock_ns=clock())))
    writer.start()
    assert written.wait(10)
    # Mid-write: the full record sits in a private temporary file; the terminal is not visible.
    assert not terminal.exists() and [p.name for p in journal.glob(".oauthplan-attempt.*.tmp")]
    for _ in range(3):
        seen.append(op.run_oauth_attempt(REQUEST, eligibility=eligible(), transport=wire, journal_dir=journal,
                                         clock_ns=clock()).status)
    release.set()
    writer.join(10)
    monkeypatch.setattr(os, "fsync", real_fsync)
    assert seen == ["ATTEMPT_ALREADY_RESERVED"] * 3  # never JOURNAL_INVALID from a torn read
    assert writer_result[0].status == op.VALID_OUTPUT and wire.dispatch_count == 1 and spy.phases == ["dispatch"]
    assert op.verify_origin_record(json.loads(terminal.read_bytes())) and not list(journal.glob("*.tmp"))
    replay = op.run_oauth_attempt(REQUEST, eligibility=eligible(), transport=wire, journal_dir=journal, clock_ns=clock())
    assert replay.replayed and replay.status == op.VALID_OUTPUT and wire.dispatch_count == 1
    # Publication never overwrites: an existing terminal stays byte-identical.
    before = terminal.read_bytes()
    with pytest.raises(FileExistsError):
        op._publish_terminal(terminal, b"{}")
    assert terminal.read_bytes() == before and not list(journal.glob("*.tmp"))
    # A crash before publication leaves only the reservation: no terminal, no second dispatch.
    crashed = tmp_path / "crashed"
    crash_wire = transport(tmp_path)

    def crash_link(*_args):
        raise OSError("crash before publication")
    monkeypatch.setattr(os, "link", crash_link)
    with pytest.raises(OSError):
        op.run_oauth_attempt(REQUEST, eligibility=eligible(), transport=crash_wire, journal_dir=crashed, clock_ns=clock())
    monkeypatch.undo()
    spy = Spy(monkeypatch, dispatch())
    assert not (crashed / "oauthplan-attempt.json").exists() and not list(crashed.glob("*.tmp"))
    assert op.run_oauth_attempt(REQUEST, eligibility=eligible(), transport=crash_wire, journal_dir=crashed,
                                clock_ns=clock()).status == "ATTEMPT_ALREADY_RESERVED"
    assert crash_wire.dispatch_count == 1 and spy.phases == []


# --------------------------------------------------------------------- R004


def test_oauth_response_strict_origin_and_errors(tmp_path, monkeypatch):
    assert classify(dispatch())[0] == op.VALID_OUTPUT and classify(dispatch())[2] == NO_TRADE.encode()
    for changes, code in (
            ({"final.output_types": ["function_call", "message"]}, "TOOL_CALL_ATTEMPT_INVALID"),
            ({"final.output_types": ["web_search_call", "message"]}, "TOOL_CALL_ATTEMPT_INVALID"),
            ({"final.output_types": ["reasoning"]}, "RESPONSE_SHAPE_INVALID"),
            ({"final.output_types": ["message", "message"]}, "RESPONSE_SHAPE_INVALID"),
            ({"terminal_events": ["response.incomplete"]}, "RESPONSE_INCOMPLETE"),
            ({"terminal_events": []}, "RESPONSE_INCOMPLETE"),
            ({"terminal_events": ["response.failed"], "failed_code": "subscription_sharing_usage_limit_exceeded"},
             "PROVIDER_RESPONSE_FAILED"),
            ({"http_calls": [["POST", "api.openai.com", "/v1/responses", 403]], "final": None}, "PROVIDER_AUTH_OR_ENTITLEMENT_DENIED"),
            ({"http_calls": [["POST", "api.openai.com", "/v1/responses", 401]], "final": None}, "PROVIDER_AUTH_OR_ENTITLEMENT_DENIED"),
            ({"http_calls": [["POST", "api.openai.com", "/v1/responses", 400]], "final": None}, "PROVIDER_HTTP_ERROR"),
            ({"http_calls": [["POST", "api.openai.com", "/v1/responses", 200]] * 2}, "MULTIPLE_DISPATCH_INVALID"),
            ({"client_stop": "OUTPUT_CAP_EXCEEDED", "final.output_text": None}, "OUTPUT_SIZE_INVALID"),
            ({"client_stop": "CLIENT_STREAM_TIMEOUT"}, "PROVIDER_TIMEOUT"),
            ({"error_class": "APIConnectionError", "final": None}, "TRANSPORT_OR_STREAM_ERROR"),
            ({"server_model": "gpt-other"}, "MODEL_MISMATCH"),
            ({"final.output_text": "x" * (op.MAX_OUTPUT_BYTES + 1)}, "OUTPUT_SIZE_INVALID"),
            ({"final.output_text": '{"action":"NO_TRADE","action":"TRADE"}'}, "OUTPUT_JSON_INVALID"),
            ({"final.output_text": "[]"}, "OUTPUT_JSON_INVALID"),
            ({"final.output_text": "NO_TRADE"}, "OUTPUT_JSON_INVALID")):
        status, _, raw = classify(dispatch(**changes))
        assert status == code and raw is None, (changes, status)
    assert classify(dispatch(), finished=DEADLINE + 1)[0] == "DEADLINE_EXCEEDED"
    # Origin labels are earned, never assumed: full real evidence vs each missing provider field.
    for changes, origin, identity in (
            ({}, op.REAL_ORIGIN_VERIFIED, "PROVIDER_REPORTED_MODEL"),
            ({"usage": None}, op.REAL_TRANSPORT_UNVERIFIED, "MODEL_IDENTITY_UNVERIFIED"),
            ({"response_id_sha256": None}, op.REAL_TRANSPORT_UNVERIFIED, "MODEL_IDENTITY_UNVERIFIED"),
            ({"server_model": None}, op.REAL_TRANSPORT_UNVERIFIED, "MODEL_IDENTITY_UNVERIFIED"),
            ({"server_model": MODEL + "-2026-09-30"}, op.REAL_TRANSPORT_UNVERIFIED, "MODEL_IDENTITY_UNVERIFIED")):
        spy = Spy(monkeypatch, dispatch(**changes))
        result = op.run_oauth_attempt(REQUEST, eligibility=eligible(), transport=transport(tmp_path),
                                      journal_dir=tmp_path / f"o{len(changes)}{next(iter(changes), '')}", clock_ns=clock())
        record = result.origin
        assert result.status == op.VALID_OUTPUT and record["real_origin"] == origin, (changes, record)
        assert record["model_identity"] == identity and record["provider_invocation"] == op.OAUTH_AUTHENTICATED_HTTP
        assert op.is_witnessed_result(result) == (origin == op.REAL_ORIGIN_VERIFIED)
        assert record["plan_usage"] == op.PLAN_USAGE_ELIGIBLE and record["transport_mode"] == op.TRANSPORT_REAL
        assert record["usage_status"] == ("USAGE_UNKNOWN" if "usage" in changes else "USAGE_PROVIDER_REPORTED")
        assert record["output_token_cap"] == "NOT_SUPPORTED_ON_ROUTE_CLIENT_BYTE_CAP_ONLY"
        assert record["cost_status"] == "INCLUDED_PLAN_USAGE_NO_DOLLAR_AMOUNT_INFERRED"
        assert record["attestation_limit"] == "PROVIDER_REPORTED_NOT_CRYPTOGRAPHIC" and record["execution_authority"] == "NONE"
        assert op.verify_origin_record(record) and not op.verify_origin_record(dict(record, real_origin=op.REAL_ORIGIN_VERIFIED,
                                                                                    usage=None))
        public = json.dumps(record)
        for secret in (NO_TRADE, REQUEST.model_input.decode(), op.INSTRUCTIONS[:40], "resp_", "req_", str(tmp_path),
                       "Bearer", "access_token", "refresh_token"):
            assert secret not in public
    # Forged witness, tampered bytes and mock transport are never witnessed.
    spy = Spy(monkeypatch, dispatch())
    real = op.run_oauth_attempt(REQUEST, eligibility=eligible(), transport=transport(tmp_path), journal_dir=tmp_path / "w",
                                clock_ns=clock())
    assert op.is_witnessed_result(real)
    for forged in (dataclasses.replace(real, output_bytes=b'{"action":"PAUSE"}'), dataclasses.replace(real, _witness=object()),
                   dataclasses.replace(real, replayed=True), dataclasses.replace(real, status="TOOL_CALL_ATTEMPT_INVALID"),
                   op.OAuthPlanResult(real.request_id, real.status, dict(real.origin), real.output_bytes)):
        assert not op.is_witnessed_result(forged)
    spy = Spy(monkeypatch, dispatch(mode="mock"))
    mocked = op.run_oauth_attempt(REQUEST, eligibility=eligible(), transport=transport(tmp_path, mode="mock"),
                                  journal_dir=tmp_path / "m", clock_ns=clock())
    assert mocked.status == op.VALID_OUTPUT and mocked.origin["provider_invocation"] == "MOCK_TRANSPORT_ONLY"
    assert mocked.origin["real_origin"] == op.REAL_ORIGIN_UNVERIFIED and not op.is_witnessed_result(mocked)
    # Native phase-split coverage is in R001 (Windows) and R004 (Linux),
    # with exact records and journal admission; the unbound world is invalid.


def test_security_profile_oauth_preflight_and_origin_binding(tmp_path, monkeypatch):
    report = preflight()
    eligible = op.evaluate_preflight(report, checked_at_ns=T0, attestation=ATTEST)
    assert eligible.facts["runtime_profile_sha256"] == REQUEST.runtime_profile_sha256
    assert op.eligibility_is_witnessed(eligible)
    for digest in (None, "0" * 64):
        blocked = op.evaluate_preflight(dict(report, runtime_profile_sha256=digest), checked_at_ns=T0, attestation=ATTEST)
        assert blocked.reason_code == "PROFILE_MISMATCH" and not op.eligibility_is_witnessed(blocked)
        assert op.verify_dispatch_wire(REQUEST, dict(dispatch(), runtime_profile_sha256=digest))["reason_code"] == "PROFILE_MISMATCH"
    monkeypatch.setattr(tf, "verify_runtime_profile", lambda *a, **k: (_ for _ in ()).throw(ValueError("PROFILE_MISMATCH")))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("OAuth child launched"))
    (tmp_path / ".git").mkdir(); (tmp_path / ".git/HEAD").write_text(tf.PINNED_HERMES_COMMIT)
    credentials = tmp_path / "never-created-credentials"
    transport = op.OAuthPlanTransport(tmp_path, credentials, mode="mock", mock={})
    with pytest.raises(ValueError, match="PROFILE_MISMATCH"):
        transport.preflight()
    assert not credentials.exists()


def test_security_profile_oauth_claims_and_malformed_input():
    import ast
    import types
    tree = ast.parse(op._CHILD_SOURCE)
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "verify_id_token")
    source = ast.unparse(helper)
    assert "65536" in source and "1048576" in source and "100" in source
    calls = []
    class Blocked(Exception):
        pass
    class Response:
        status_code = 200
        def __init__(self, data): self.data = data
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_bytes(self): yield self.data
    document = dict(keys=[dict(kty="RSA", kid="synthetic", alg="RS256", use="sig")])
    def decode(token, **kwargs):
        calls.append(kwargs)
        assert kwargs["algorithms"] == ["RS256"]
        assert kwargs["options"] == {"require": ["exp", "iat", "iss", "aud", "sub"]}
        if token != "valid": raise ValueError("do-not-echo")
        return dict(nonce="nonce")
    namespace = dict(json=json, jwt=types.SimpleNamespace(get_unverified_header=lambda t:dict(kid="synthetic"),
                     PyJWK=lambda k:types.SimpleNamespace(key="synthetic-only"), decode=decode),
                     C=dict(jwks_url="https://synthetic.invalid/jwks", issuer="issuer"), Blocked=Blocked)
    exec(compile(ast.Module(body=[helper], type_ignores=[]), "actual-child-helper", "exec"), namespace)
    verify = namespace["verify_id_token"]
    def client(data): return types.SimpleNamespace(stream=lambda *a:Response(data))
    assert verify("valid", client(json.dumps(document).encode()), "aud", "nonce") == dict(nonce="nonce")
    for token, data, nonce in [("invalid", json.dumps(document).encode(), "nonce"),
                               ("valid", json.dumps(document).encode(), "wrong"),
                               ("x"*65537, b"{}", "nonce"),
                               ("valid", b"x"*1048577, "nonce"),
                               ("valid", b"["*1500, "nonce"),
                               ("valid", b"{", "nonce")]:
        with pytest.raises(Blocked) as exc: verify(token, client(data), "aud", nonce)
        assert str(exc.value) == "ID_TOKEN_INVALID" and "do-not-echo" not in str(exc.value)
    for keys in [[], [document["keys"][0]]*101, [document["keys"][0]]*2, [None],
                 [dict(kty="oct", kid="synthetic")], [dict(kty="RSA", kid="synthetic", alg="HS256")],
                 [dict(kty="RSA", kid="synthetic", use="enc")],
                 [dict(kty="RSA", kid="synthetic", alg=None)], [dict(kty="RSA", kid="synthetic", use=None)], [dict(kty="RSA", kid="other")]]:
        with pytest.raises(Blocked, match="ID_TOKEN_INVALID"):
            verify("valid", client(json.dumps(dict(keys=keys)).encode()), "aud", "nonce")
    assert calls[0]["options"] is not calls[1]["options"]
    if not (PIN_ROOT / ".git/HEAD").is_file():
        return  # Pure parser negatives above always run; real-library evidence is local candidate only.
    script = r"""import ast, base64, json, sys, time, socket
import jwt, httpx
from cryptography.hazmat.primitives.asymmetric import rsa
source=json.load(sys.stdin)["helper"]
class Blocked(Exception): pass
namespace=dict(json=json,jwt=jwt,Blocked=Blocked,C=dict(jwks_url="https://synthetic.invalid/jwks",issuer="issuer"))
exec(source,namespace)
verify=namespace["verify_id_token"]
key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
jwk=dict(json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())),kid="test",alg="RS256",use="sig")
now=int(time.time()); claims=dict(exp=now+300,iat=now,iss="issuer",aud="aud",sub="subject",nonce="nonce")
client=httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=dict(keys=[jwk]))))
def deny(*a,**k): raise OSError("network denied")
socket.socket.connect=socket.create_connection=socket.getaddrinfo=deny
assert verify(jwt.encode(claims,key,algorithm="RS256",headers=dict(kid="test")),client,"aud","nonce")["sub"]=="subject"
for change in [dict(exp=now-600),dict(iat=now+600),dict(iss="other"),dict(aud="other"),dict(nonce="wrong"),dict(sub=None)]:
    try:verify(jwt.encode(dict(claims,**change),key,algorithm="RS256",headers=dict(kid="test")),client,"aud","nonce")
    except Blocked as e:assert str(e)=="ID_TOKEN_INVALID"
    else:raise AssertionError("invalid claim accepted")
try:verify(jwt.encode(claims,b"synthetic-non-secret-key-material-32",algorithm="HS256",headers=dict(kid="test")),client,"aud","nonce")
except Blocked:pass
else:raise AssertionError("HS256 accepted")
header=base64.urlsafe_b64encode(b'{"kid":'+b'['*1500+b'0'+b']'*1500+b'}').rstrip(b'=').decode()+'.e30.AA'
try:verify(header,client,"aud","nonce")
except Blocked as e:assert str(e)=="ID_TOKEN_INVALID"
else:raise AssertionError("nested header accepted")
expired=jwt.encode(dict(claims,exp=now-600),key,algorithm="RS256")
options=dict(verify_signature=False);jwt.decode(expired,options=options);assert options==dict(verify_signature=False)
options["verify_signature"]=True
try:jwt.decode(expired,key.public_key(),algorithms=["RS256"],audience="aud",issuer="issuer",options=options)
except jwt.ExpiredSignatureError:pass
else:raise AssertionError("reused options bypass")
print("ACTUAL_CHILD_JWT_NEGATIVES_PASS")
"""
    import os
    exe = PIN_ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    completed = subprocess.run([str(exe), "-I", "-B", "-c", script], input=json.dumps(dict(helper=source)).encode(),
                               capture_output=True, timeout=60)
    assert completed.returncode == 0 and b"ACTUAL_CHILD_JWT_NEGATIVES_PASS" in completed.stdout, completed.stderr


# Shared primitive seam; native phase-split R001/R004 exercise the actual child.
def siwc_helpers():
    namespace = {}
    exec(compile(op._SIWC_SOURCE, "siwc-child-helpers", "exec"), namespace)
    return namespace


def siwc_binding(h, operation="import-selected"):
    value = dict(schema_id="siwc-vm-operator-binding", schema_version="1.0.0", operation=operation,
                 operation_alias="synthetic-01", selected_client_id="synthetic-client", selected_subject="synthetic-subject",
                 approved_storage_root="/private/siwc", excluded_roots=["/project"], destination_host_id="synthetic-destination",
                 expected_source_commit="a" * 40, expected_runtime_profile_sha256="b" * 64, refresh_allowed=False,
                 valid_from_ns=T0, valid_until_ns=T0 + 900_000_000_000, attestation=None)
    if operation in {"prepare-vm-host","source-login"}: value["destination_host_id"] = None
    if operation in {"source-login","source-export"}:
        value.update(approved_storage_root=r"C:\synthetic-private",excluded_roots=[r"C:\synthetic-project"])
    if operation == "preflight-only": value["attestation"] = dict(ATTEST)
    return value


def siwc_transfer_fixture(h):
    import base64
    def token(claims):
        return "e30." + base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode() + ".c3ludGhldGlj"
    credential = dict(issuer=op.ISSUER, subject="synthetic-subject", client_id="synthetic-client",
        id_token=token(dict(iss=op.ISSUER, sub="synthetic-subject", aud="synthetic-client")),
        access_token=token(dict(iss=op.ISSUER, sub="synthetic-subject", aud=op.RESOURCE,
                               client_id="synthetic-client", scope=" ".join(SCOPES))),
        refresh_token="synthetic-only-refresh-sentinel", token_type="Bearer", expires_at=200, saved_at=100,
        scopes=SCOPES, ext_agent_host_id="synthetic-source")
    return dict(schema_id="siwc-selected-transfer", schema_version="1.0.0", registration=dict(
        client_id=credential["client_id"], subject=credential["subject"]), credential=credential,
        source_host_id="synthetic-source", source_validation=dict(source_commit="a" * 40,
        runtime_profile_sha256="c" * 64, validated_login_identity=True))


def siwc_state_fixture():
    return dict(schema_id="siwc-source-export-state", schema_version="1.0.0", operation_alias="synthetic-01",
        selected_generation=1, registration_binding="1" * 64, source_host_binding="2" * 64,
        destination_host_binding="3" * 64, export_digest="4" * 64, target_binding="5" * 64)


def test_siwc_selected_registration_handoff():
    h = siwc_helpers()
    binding, transfer = siwc_binding(h), siwc_transfer_fixture(h)
    def validate(value, destination="synthetic-destination"):
        return h["siwc_transfer"](json.dumps(value).encode(), binding, destination_host_id=destination,
            source_profile="c" * 64, issuer=op.ISSUER, resource=op.RESOURCE, scopes=SCOPES)
    assert validate(transfer) == transfer  # Includes every issued byte; no reminting/normalization.
    changes = [dict(registration=dict(transfer["registration"], client_id="mixed")),
               dict(source_host_id="synthetic-destination"), dict(source_validation=dict(
                   transfer["source_validation"], validated_login_identity=False)), dict(extra="secret-sentinel")]
    changes += [dict(credential=dict(transfer["credential"], **change)) for change in (
        dict(subject="mixed"), dict(issuer="wrong"), dict(client_id="mixed"), dict(id_token="missing"),
        dict(scopes=SCOPES[:-1]), dict(scopes=SCOPES+SCOPES[:1]), dict(refresh_token=None),
        dict(expires_at=True), dict(saved_at=201), dict(access_token="e30.e30.c2ln"))]
    for change in changes:
        with pytest.raises(h["SIWCBlocked"]): validate(dict(transfer, **change))
    for key in transfer:
        invalid = dict(transfer)
        invalid.pop(key)
        with pytest.raises(h["SIWCBlocked"]): validate(invalid)
    with pytest.raises(h["SIWCBlocked"]): validate(transfer, destination="other")
    if sys.platform == "win32" and (PIN_ROOT/".git/HEAD").is_file():
        siwc_native_windows_mock_handoff(h)


def siwc_native_windows_mock_handoff(h):
    """Genuine secured child/native Windows filesystem; all HTTP is synthetic."""
    import time
    import uuid
    root = siwc_windows_private_directory(Path(Path.cwd().anchor),"siwc-synthetic-"+uuid.uuid4().hex)
    credentials = siwc_windows_private_directory(root,"credentials")
    output = siwc_windows_private_directory(root,"output")
    source_commit = subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    profile = tf.verify_runtime_profile(PIN_ROOT)
    def record(operation,client="dynamic_agent_client",subject="NEW_REGISTRATION_UNBOUND"):
        now = time.time_ns()
        value = dict(siwc_binding(h,operation),operation_alias="synthetic-"+uuid.uuid4().hex,
            selected_client_id=client,selected_subject=subject,approved_storage_root=str(root),
            excluded_roots=[str(ROOT),str(PIN_ROOT)],expected_source_commit=source_commit,
            expected_runtime_profile_sha256=profile,valid_from_ns=now-1000000000,valid_until_ns=now+800000000000)
        path = root/(operation+"-"+uuid.uuid4().hex+".json")
        with h["SIWCWindowsSlot"](str(root),approved_root=str(root),excluded_roots=[]) as store:
            store.publish(path.name,json.dumps(value).encode(),65536)
        return path
    def transport(path,credential_path=credentials,**mock):
        return op.OAuthPlanTransport(PIN_ROOT,credential_path,mode="mock",mock=mock,operator_record_path=path,login_wait_s=10)
    source = transport(record("source-login"))
    with h["SIWCWindowsSlot"](str(credentials),approved_root=str(root),excluded_roots=[]) as store:
        for name in ("registration.json","credential.json","host_id.json","operation-pending.json",
                     "export-pending.json","export-retired.json",".siwc-orphan"):
            store.publish(name,b'{"synthetic_partial":true}')
            with pytest.raises(h["SIWCBlocked"]):
                h["siwc_login_selection"](store,dict(selected_client_id="dynamic_agent_client",selected_subject="NEW_REGISTRATION_UNBOUND"))
            (credentials/name).unlink()  # Reset only this deliberately corrupted synthetic fixture.
    assert source.login()["status"] == "DONE"
    files = {p.name:p.read_bytes() for p in credentials.iterdir()}
    refused = source.login()  # Sentinels cannot turn a returning slot into NEW.
    assert refused["status"] == "BLOCKED" and refused["http_calls"] == []
    assert files == {p.name:p.read_bytes() for p in credentials.iterdir()}
    wrong_selection = transport(record("source-login","oaiapp_mock","wrong-synthetic-subject")).login()
    assert wrong_selection["status"] == "BLOCKED" and wrong_selection["http_calls"] == []
    assert files == {p.name:p.read_bytes() for p in credentials.iterdir()}
    source = transport(record("source-login","oaiapp_mock","mock-subject"))
    assert source.login()["status"] == "DONE"  # Exercises real ReplaceFileW identity/ACL/flush checks.
    path = record("source-export","oaiapp_mock","mock-subject")
    wrong = transport(path).login()
    assert wrong["status"] == "BLOCKED" and wrong["http_calls"] == []
    exporter = transport(path)
    bundle = output/"selected.json"
    result = exporter.export_selected_session(transfer_file=bundle)
    assert result["status"] == "DONE"
    receipt = json.loads((output/"selected.json.receipt.json").read_bytes())
    assert receipt["evidence_class"] == "OFFLINE_TEST_ONLY" and receipt["dispatch_count"] == 0
    transferred = json.loads(bundle.read_bytes())
    assert transferred["registration"] == {"client_id":"oaiapp_mock","subject":"mock-subject"}
    assert transferred["credential"]["access_token"].startswith("mock-access.")
    assert transferred["source_validation"]["validated_login_identity"] is True
    replay = exporter.export_selected_session(transfer_file=output/"second.json")
    assert replay["status"] == "BLOCKED" and not (output/"second.json").exists()
    assert source.login()["reason_code"] == "SOURCE_SESSION_RETIRED"
    # Preserve native callback/OIDC/scope negatives under separate, correctly
    # admitted fresh source slots; the legacy unbound world can no longer log in.
    for kwargs,code in ((dict(callback=dict(error="access_denied",code=None)),"CONSENT_DENIED"),
        (dict(callback=dict(state="forged-state")),"STATE_MISMATCH"),
        (dict(callback=dict(client_id=None)),"REGISTRATION_INCOMPLETE"),
        (dict(token=dict(id_claims=dict(aud="oaiapp_other"))),"ID_TOKEN_INVALID"),
        (dict(token=dict(id_claims=dict(nonce="replayed"))),"ID_TOKEN_INVALID"),
        (dict(token=dict(status=400)),"TOKEN_EXCHANGE_FAILED"),
        (dict(token=dict(scope="openid profile email offline_access")),"TOKEN_RESPONSE_INVALID")):
        invalid_slot = siwc_windows_private_directory(root,"invalid-"+uuid.uuid4().hex)
        refused = transport(record("source-login"),credential_path=invalid_slot,**kwargs).login()
        assert refused["status"] == "BLOCKED" and refused["reason_code"] == code
        assert not (invalid_slot/"credential.json").exists() and (invalid_slot/"operation-pending.json").exists()
    assert tf.verify_runtime_profile(PIN_ROOT) == profile


def test_siwc_storage_confinement_atomicity():
    h = siwc_helpers()
    for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'[]', b'\xff',
                b'{"a":'+b'['*8+b'0'+b']'*8+b'}', b'{' + b' '*65536 + b'}'):
        with pytest.raises(h["SIWCBlocked"], match="^RECORD_INVALID$"): h["siwc_json"](raw,65536)
    assert h["siwc_json"](b'{"quoted":"[[[[[[[[[","a":[1]}',65536)["a"] == [1]
    for path in ("relative", "/safe/../secret", "/safe/./secret", "//server/share", "/safe\x00file"):
        with pytest.raises(h["SIWCBlocked"]): h["siwc_path"](path)
    for path in (r"C:\safe\..\secret", r"\\server\share", r"\\?\C:\secret", r"C:\safe\token:ads",
                 r"C:\safe\NUL.txt", "C:\\safe\\trailing.", "C:\\safe\\trailing ", r"C:\PROGRA~1\secret"):
        with pytest.raises(h["SIWCBlocked"]): h["siwc_path"](path, windows=True)
    assert h["siwc_path"](r"C:\private\slot", windows=True).name == "slot"


def test_siwc_refresh_owner_and_crash():
    h, state = siwc_helpers(), siwc_state_fixture()
    pending = json.dumps(dict(state,state="PENDING")).encode()
    retired = json.dumps(dict(state,state="RETIRED")).encode()
    classify = h["siwc_source_state"]
    assert classify(None,None) == "ACTIVE"
    for p,r in ((b"",None),(pending,None),(None,retired),(b"{",retired),
                (pending,json.dumps(dict(state,state="RETIRED",selected_generation=2)).encode())):
        assert classify(p,r) == "EXPORT_STATE_INVALID"
    assert classify(pending,retired) == "SOURCE_SESSION_RETIRED"
    assert classify(pending,retired,interrupted=True) == "SOURCE_SESSION_RETIRED"
    # Every failure prefix retains state and cannot resume publication on restart.
    class FaultSlot:
        def __init__(self, fail): self.files, self.calls, self.fail = {}, [], fail
        def read(self,name,*args): return self.files.get(name)
        def barrier(self,name,raw,*args):
            self.calls.append(name)
            self.files[name] = b"{" if len(self.calls) == self.fail else raw
            if len(self.calls) == self.fail: raise h["SIWCBlocked"]("PUBLICATION_AMBIGUOUS")
    for cut in (1,2,3):
        slot = FaultSlot(cut)
        if cut < 3:
            with pytest.raises(h["SIWCBlocked"]): h["siwc_retire_source"](slot,state)
        else: h["siwc_retire_source"](slot,state)
        assert set(slot.files) <= {"export-pending.json","export-retired.json"}
        assert classify(slot.read("export-pending.json"),slot.read("export-retired.json")) != "ACTIVE"
        original = dict(slot.files)
        with pytest.raises(h["SIWCBlocked"]): h["siwc_retire_source"](slot,state)
        assert slot.files == original
    bundle = b'{"synthetic":"issued-set"}'
    state = dict(state,export_digest=hashlib.sha256(bundle).hexdigest())
    class Output:
        def __init__(self): self.files = {}
        def target_binding(self,name): return state["target_binding"]
        def publish(self,name,raw): self.files[name] = raw
    source, output = FaultSlot(3), Output()
    with pytest.raises(h["SIWCBlocked"]):
        h["siwc_publish_retired_export"](source,output,"transfer.json",bundle,state,permit=object())
    assert output.files == {}
    permit = h["siwc_retire_source"](source,state)
    h["siwc_publish_retired_export"](source,output,"transfer.json",bundle,state,permit=permit)
    assert output.files == {"transfer.json":bundle}
    with pytest.raises(h["SIWCBlocked"]):
        h["siwc_publish_retired_export"](source,output,"second.json",bundle,state,permit=permit)
    restarted = FaultSlot(3)
    restarted.files = dict(source.files)
    with pytest.raises(h["SIWCBlocked"]):
        h["siwc_publish_retired_export"](restarted,output,"second.json",bundle,state,permit=permit)
    assert set(output.files) == {"transfer.json"}
    if sys.platform == "win32":
        if not siwc_windows_elevated_refusal(h):
            siwc_windows_crash_boundaries(h)
    elif sys.platform == "linux":
        siwc_posix_mutation_crash_boundaries(h)
    # Persistence schedules may lose only writes before their required barrier.
    # Losing an acknowledged retirement is an unsupported-device counterexample,
    # never a power-loss PASS or a source-export admission.
    for pending_saved,retired_saved,bundle_saved in ((False,False,False),(True,False,False),
                                                   (True,True,False),(True,True,True)):
        restarted = classify(pending if pending_saved else None,retired if retired_saved else None)
        if bundle_saved: assert restarted == "SOURCE_SESSION_RETIRED"
        if not pending_saved: assert restarted == "ACTIVE" and not bundle_saved
    unsupported = dict(acknowledged_retirement_lost=True,bundle_persisted=True)
    assert classify(pending,None) == "EXPORT_STATE_INVALID"
    assert unsupported["acknowledged_retirement_lost"] and unsupported["bundle_persisted"]
    assert "DURABILITY_UNESTABLISHED" in h["_SIWC_RECEIPT_REASONS"]


def siwc_windows_crash_boundaries(h):
    """Real native calls/child death; no hardware power-loss inference."""
    import uuid
    points = ("before-pending","pending-created","pending-partial","pending-written","pending-flushed",
        "pending-barrier","retired-written","retired-barrier","bundle-written","bundle-flush",
        "after-move","final-flush","receipt-flush","reported-success")
    script = r'''
import json,sys,time,socket
v=json.load(sys.stdin); h={}; exec(compile(v["source"],"siwc-native-fault-child","exec"),h)
socket.socket.connect=socket.create_connection=lambda *a,**k:(_ for _ in ()).throw(OSError("offline"))
def cut(name):
    if name == v["point"]:
        print("CUT",flush=True); time.sleep(60); raise RuntimeError("test supervisor failed")
with h["SIWCWindowsSlot"](v["slot"],approved_root=v["root"],excluded_roots=[]) as s, \
     h["SIWCWindowsSlot"](v["output"],approved_root=v["root"],excluded_roots=[]) as o:
    handles={}; publication=["bundle"]
    for store in (s,o):
        k=store.k; create,write,flush,move=k.CreateFileW,k.WriteFile,k.FlushFileBuffers,k.MoveFileExW
        def hooked_create(path,*args,_call=create):
            name=str(path).replace("\\","/").rsplit("/",1)[-1]
            creating_pending = name == "export-pending.json" and args[3] == 1
            if creating_pending: cut("before-pending")
            handle=_call(path,*args); handles[handle]=name
            if creating_pending: cut("pending-created")
            return handle
        def hooked_write(handle,raw,length,size,overlap,_call=write):
            name=handles.get(handle,"")
            if name == "export-pending.json" and v["point"] == "pending-partial":
                result=_call(handle,raw,max(1,length//2),size,overlap); cut("pending-partial"); return result
            result=_call(handle,raw,length,size,overlap)
            if name == "export-pending.json": cut("pending-written")
            if name == "export-retired.json": cut("retired-written")
            if name.startswith(".siwc-") and publication[0] == "bundle": cut("bundle-written")
            return result
        def hooked_flush(handle,_call=flush):
            name=handles.get(handle,"")
            if name.startswith(".siwc-"):
                cut("receipt-flush" if publication[0] == "receipt" else "bundle-flush")
            if name == "transfer.json": cut("final-flush")
            result=_call(handle)
            if name == "export-pending.json": cut("pending-flushed")
            return result
        def hooked_move(*args,_call=move):
            assert args[2] == 8
            result=_call(*args)
            if publication[0] == "bundle": cut("after-move")
            return result
        k.CreateFileW,k.WriteFile,k.FlushFileBuffers,k.MoveFileExW=hooked_create,hooked_write,hooked_flush,hooked_move
    barrier=s.barrier
    def checked_barrier(name,*args):
        barrier(name,*args)
        cut("pending-barrier" if name == "export-pending.json" else "retired-barrier")
    s.barrier=checked_barrier
    raw=b'{"synthetic":"token-sentinel"}'
    state=dict(v["state"],export_digest=h["hashlib"].sha256(raw).hexdigest(),target_binding=o.target_binding("transfer.json"))
    permit=h["siwc_retire_source"](s,state)
    h["siwc_publish_retired_export"](s,o,"transfer.json",raw,state,permit=permit)
    publication[0]="receipt"; o.publish("receipt.json",b'{"synthetic_receipt":true}')
    cut("reported-success")
'''
    for point in points:
        root = siwc_windows_private_directory(Path(Path.cwd().anchor),"siwc-synthetic-"+uuid.uuid4().hex)
        source = siwc_windows_private_directory(root,"source")
        output = siwc_windows_private_directory(root,"output")
        with h["SIWCWindowsSlot"](str(source),approved_root=str(root),excluded_roots=[]) as store:
            store.publish("credential.json",b'{"synthetic_credential":"original"}')
            original = (source/"credential.json").read_bytes()
            original_id = (source/"credential.json").stat().st_ino
            lock_id = (source/"session.lock").stat().st_ino
        child = subprocess.Popen([sys.executable,"-I","-B","-c",script],stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            child.stdin.write(json.dumps(dict(source=op._SIWC_SOURCE,root=str(root),slot=str(source),
                output=str(output),state=siwc_state_fixture(),point=point)))
            child.stdin.close()
            assert child.stdout.readline().strip() == "CUT"
            with pytest.raises(h["SIWCBlocked"],match="^SESSION_BUSY$"):
                with h["SIWCWindowsSlot"](str(source),approved_root=str(root),excluded_roots=[]): pass
            child.kill();child.wait(timeout=10)
            with h["SIWCWindowsSlot"](str(source),approved_root=str(root),excluded_roots=[]) as store:
                state = h["siwc_source_state"](store.read("export-pending.json"),store.read("export-retired.json"))
                assert (source/"credential.json").read_bytes() == original
                assert (source/"credential.json").stat().st_ino == original_id
                assert (source/"session.lock").stat().st_ino == lock_id
                if point == "before-pending": assert state == "ACTIVE"
                else: assert state in {"EXPORT_STATE_INVALID","SOURCE_SESSION_RETIRED"}
                exposed = any(p.name != "session.lock" for p in output.iterdir())
                if exposed: assert state == "SOURCE_SESSION_RETIRED"
                if point in {"bundle-written","bundle-flush","after-move","final-flush","receipt-flush","reported-success"}:
                    assert state == "SOURCE_SESSION_RETIRED"
        finally:
            if child.poll() is None: child.kill();child.wait(timeout=10)


def test_siwc_non_dispatch_preflight_receipt(monkeypatch,capsys):
    h = siwc_helpers()
    receipt = h["siwc_offline_receipt"](operation="preflight-only",alias="synthetic-01",source_commit="a"*40,
        prompt_sha256="b"*64,spec_sha256="c"*64,hermes_commit=tf.PINNED_HERMES_COMMIT,
        profile=RECORDED_REPORT["runtime_profile_sha256"],checked_at_ns=T0)
    assert set(receipt) == h["_SIWC_RECEIPT_KEYS"]  # serializer field coverage, not an entitlement test
    raw = h["siwc_receipt_bytes"](receipt)
    assert json.loads(raw) == receipt and receipt["dispatch_count"] == 0
    assert receipt["evidence_class"] == "OFFLINE_TEST_ONLY" and receipt["status"] == "BLOCKED"
    for key in receipt:
        missing = dict(receipt)
        missing.pop(key)
        with pytest.raises(h["SIWCBlocked"],match="^RECEIPT_INVALID$"): h["siwc_receipt_bytes"](missing)
    for change in (dict(extra="secret-sentinel"),dict(reason_code="secret-sentinel"),dict(operation=[]),
                   dict(evaluation_reason={"secret-sentinel":"leak"}),dict(status="DONE"),dict(orders=True),
                   dict(endpoints=[{"token":"secret-sentinel"}]),dict(route=dict(receipt["route"],token="secret-sentinel")),
                   dict(dispatch_count=1),dict(refresh_count=1),dict(generation=False),dict(real_entitlement="VERIFIED")):
        with pytest.raises(h["SIWCBlocked"],match="^RECEIPT_INVALID$") as error:
            h["siwc_receipt_bytes"](dict(receipt,**change))
        assert "secret-sentinel" not in repr(error.value)
    if sys.platform == "linux" and (PIN_ROOT/".git/HEAD").is_file():
        siwc_native_linux_bridge(h,monkeypatch,capsys)


def siwc_native_linux_bridge(h,monkeypatch,capsys):
    """Actual Git-backed Linux child/profile/files; provider HTTP stays mocked."""
    import time
    import uuid
    revision = subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    profile = tf.verify_runtime_profile(PIN_ROOT)
    original_transport = op.OAuthPlanTransport
    with siwc_posix_root() as directory:
        root = Path(directory)
        credentials, output = root/"credentials",root/"output"
        credentials.mkdir(mode=0o700);output.mkdir(mode=0o700)
        def binding_path(operation,host=None,refresh=False):
            now = time.time_ns()
            value = dict(siwc_binding(h,operation),approved_storage_root=str(root),excluded_roots=[str(ROOT),str(PIN_ROOT)],
                expected_source_commit=revision,expected_runtime_profile_sha256=profile,
                destination_host_id=host,refresh_allowed=refresh,operation_alias="synthetic-"+uuid.uuid4().hex,
                valid_from_ns=now-1000000000,valid_until_ns=now+800000000000)
            if operation == "prepare-vm-host": value.update(selected_client_id=None,selected_subject=None)
            path = root/(uuid.uuid4().hex+".json")
            with h["SIWCPosixSlot"](directory,approved_root=directory,excluded_roots=[]) as store:
                store.publish(path.name,json.dumps(value).encode(),65536)
            return path
        models = dict(status=200,body=dict(models=[dict(slug=MODEL,visibility="list")]))
        def transport(path,token=None,model_response=None,scenario=None):
            mock = dict(models=models if model_response is None else model_response)
            if token is not None: mock["token"] = token
            if scenario is not None: mock["responses"] = scenario
            return original_transport(PIN_ROOT,credentials,mode="mock",mock=mock,operator_record_path=path)
        prepared = transport(binding_path("prepare-vm-host"))
        prepared._receipt_path = str(output/"prepared.json")
        assert prepared.prepare_vm_host()["status"] == "DONE"
        host_before = (credentials/"host_id.json").read_bytes()
        host = json.loads(host_before)["ext_agent_host_id"]
        imported = transport(binding_path("import-selected",host))
        imported._receipt_path = str(output/"imported.json")
        transfer = siwc_transfer_fixture(h)
        transfer["source_validation"].update(source_commit=revision,runtime_profile_sha256=RECORDED_REPORT["runtime_profile_sha256"])
        transfer["credential"].update(expires_at=int(time.time())+3600,saved_at=int(time.time())-1)
        with h["SIWCPosixSlot"](str(output),approved_root=directory,excluded_roots=[]) as store:
            store.publish("selected.json",json.dumps(transfer).encode())
        assert imported.import_selected_session(transfer_file=output/"selected.json")["status"] == "DONE"
        assert (credentials/"host_id.json").read_bytes() == host_before
        # Exercise the unchanged VM caller on its actual Linux target. It has
        # no operator record and must stop before journal/model/account effects.
        from src.execution_gateway import live_canary
        journal = output/"never-created-journal"
        case = dict(oauth_pin_root=str(PIN_ROOT),oauth_credential_dir=str(credentials),
            oauth_journal_dir=str(journal),plan_usage_attestation=ATTEST,oauth_deadline_s=60)
        with monkeypatch.context() as patch:
            patch.setattr(tf,"probe_native_tool_surface",lambda *a,**k:RECORDED_REPORT)
            patch.setattr(op,"run_oauth_attempt",lambda *a,**k:pytest.fail("unbound caller dispatch"))
            with pytest.raises(live_canary.CanaryBlocked,match="OAUTH_PREFLIGHT_INELIGIBLE"):
                live_canary.native_oauth_attempt(case,candidate_menu=MENU,lineage=LINEAGE,information_cutoff_ns=T0,
                                                clock_ns=lambda:T0+1)
        assert not journal.exists()
        path = binding_path("preflight-only",host)
        checked = transport(path)
        checked._receipt_path = str(output/"preflight.json")
        report = checked.preflight()
        assert report["status"] == "DONE" and report["http_calls"] == [["GET",op.API_HOST,op.MODELS_PATH,200]]
        evaluation = op.evaluate_preflight(report,attestation=ATTEST,checked_at_ns=time.time_ns())
        assert evaluation.status == op.PLAN_USAGE_UNVERIFIED
        receipt = checked._preflight_receipt(report,evaluation)["receipt"]
        encoded = h["siwc_receipt_bytes"](receipt)
        assert receipt["status"] == "BLOCKED" and receipt["catalogue_count"] == 1 and receipt["dispatch_count"] == 0
        assert all(secret.encode() not in encoded for secret in ("synthetic-client","synthetic-subject","synthetic-source","synthetic-only-refresh-sentinel"))
        def factory(pin_root,credential_dir,*,operator_record_path):
            assert Path(pin_root)==PIN_ROOT and Path(credential_dir)==credentials
            return transport(operator_record_path)
        path = binding_path("preflight-only",host)
        with monkeypatch.context() as patch:
            patch.setattr(op,"OAuthPlanTransport",factory)
            patch.setattr(op,"run_oauth_attempt",lambda *a,**k:pytest.fail("CLI dispatch"))
            patch.setattr(original_transport,"_send",lambda *a,**k:pytest.fail("CLI dispatch"))
            code = op.main(["preflight-only","--pin-root",str(PIN_ROOT),"--credential-dir",str(credentials),
                "--operator-record",str(path),"--receipt",str(output/"cli.json")])
            assert code == 1
            public = json.loads(capsys.readouterr().out)
            assert public["dispatch_count"] == 0 and public["evidence_class"] == "OFFLINE_TEST_ONLY"
            assert public["catalogue_count"] == 1
        for model_response,reason in ((dict(status=200,body=dict(models=[dict(slug="gpt-other")])),"OAUTH_MODEL_NOT_AVAILABLE"),
                (dict(status=200,body=dict(models={})),"MODEL_CATALOG_UNAVAILABLE")):
            absent = transport(binding_path("preflight-only",host),model_response=model_response).preflight()
            assert op.evaluate_preflight(absent,attestation=ATTEST,checked_at_ns=time.time_ns()).reason_code == reason
            assert len(absent["http_calls"]) == 1
        for http_status in (401,403,429,500):
            refused_catalogue = transport(binding_path("preflight-only",host),model_response=dict(status=http_status,body={})).preflight()
            assert refused_catalogue["status"] == "BLOCKED" and len(refused_catalogue["http_calls"]) == 1
        # Original native SDK/SSE/wire/no-retry coverage now uses the Linux
        # selected import and distinct dispatch record through the real journal.
        surface = copy.deepcopy(RECORDED_REPORT)
        surface["runtime_profile_sha256"] = profile
        request = op.build_oauth_request(surface_report=surface,candidate_menu=MENU,lineage=LINEAGE,
            information_cutoff_ns=T0,issued_at_ns=T0,deadline_ns=DEADLINE)
        reasoning = dict(id="r1",type="reasoning",summary=[])
        function = dict(id="fc1",type="function_call",call_id="c1",name="terminal",arguments="{}")
        scenarios = [(sse_message(NO_TRADE,extra_items=[reasoning]),op.VALID_OUTPUT),
            (sse_message(NO_TRADE,extra_items=[function]),"TOOL_CALL_ATTEMPT_INVALID"),
            (sse_message("x"*(op.MAX_OUTPUT_BYTES+10)),"OUTPUT_SIZE_INVALID"),
            (sse_message(NO_TRADE,model="gpt-other"),"MODEL_MISMATCH"),
            (dict(kind="http",status=429,code="subscription_sharing_usage_limit_exceeded"),"PROVIDER_RATE_LIMITED"),
            (dict(kind="raise",error="ReadTimeout"),"PROVIDER_TIMEOUT")]
        for index,(scenario,expected) in enumerate(scenarios):
            dispatched = transport(binding_path("dispatch",host),scenario=scenario)
            journal = output/("journal-"+str(index))
            result = op.run_oauth_attempt(request,eligibility=None,transport=dispatched,journal_dir=journal,clock_ns=clock())
            assert result.status == expected and dispatched.dispatch_count == 1
            assert result.origin["real_origin"] == op.REAL_ORIGIN_UNVERIFIED
            replay = op.run_oauth_attempt(request,eligibility=None,transport=dispatched,journal_dir=journal,clock_ns=clock())
            assert replay.replayed and dispatched.dispatch_count == 1
        stopped = transport(binding_path("dispatch",host),scenario=sse_message(NO_TRADE))
        original_child,observations = stopped._run_child,[]
        def capture(phase,extra,timeout):
            result = original_child(phase,extra,timeout)
            observations.append(result)
            return result
        with monkeypatch.context() as patch:
            patch.setattr(op,"UNSUPPORTED_FIELDS",op.UNSUPPORTED_FIELDS|{"include"})
            patch.setattr(stopped,"_run_child",capture)
            op.run_oauth_attempt(request,eligibility=None,transport=stopped,journal_dir=output/"presend",clock_ns=clock())
        assert len(observations) == 1 and observations[0]["presend_block"] == "PRESEND_WIRE_REJECTED"
        assert observations[0]["http_calls"] == [] and len(observations[0]["requests"]) == 1
        # Near-expiry refresh false refuses before any endpoint and leaves bytes unchanged.
        with h["SIWCPosixSlot"](str(credentials),approved_root=directory,excluded_roots=[]) as store:
            credential = json.loads(store.read("credential.json"))
            credential["expires_at"] = int(time.time())+10
            store.replace_credential(json.dumps(credential).encode())
        before = (credentials/"credential.json").read_bytes()
        refused = transport(binding_path("preflight-only",host)).preflight()
        assert refused["status"] == "BLOCKED" and refused["http_calls"] == []
        assert (credentials/"credential.json").read_bytes() == before
        refreshed = transport(binding_path("preflight-only",host,True)).preflight()
        assert refreshed["status"] == "DONE" and refreshed["refreshed"] is True
        assert [c[:3] for c in refreshed["http_calls"]] == [["POST",op.AUTH_HOST,"/api/accounts/oauth/token"],["GET",op.API_HOST,op.MODELS_PATH]]
        assert not (credentials/"operation-pending.json").exists()
        repeated = transport(path).preflight()
        assert repeated["status"] == "BLOCKED" and repeated["http_calls"] == []
        gated = original_transport(PIN_ROOT,credentials,mode="real",operator_record_path=binding_path("dispatch",host))
        with pytest.raises(ValueError,match="^DISPATCH_AUTHORITY_REQUIRED$"): gated._send(REQUEST)
        assert gated.dispatch_count == 0
        # A known coherent near-expiry fixture, then an uncertain refresh result.
        with h["SIWCPosixSlot"](str(credentials),approved_root=directory,excluded_roots=[]) as store:
            pending = h["siwc_begin_mutation"](store,"preflight-only","synthetic-expiry")
            credential = json.loads(store.read("credential.json"))
            credential["expires_at"] = int(time.time())+10
            store.replace_credential(json.dumps(credential).encode())
            h["siwc_complete_mutation"](store,pending)
        before_failure = (credentials/"credential.json").read_bytes()
        failing = transport(binding_path("preflight-only",host,True),token=dict(status=400))
        failed = failing.preflight()
        assert failed["status"] == "BLOCKED" and len(failed["http_calls"]) == 1
        assert failed["http_calls"][0][:3] == ["POST",op.AUTH_HOST,"/api/accounts/oauth/token"]
        assert (credentials/"operation-pending.json").exists()
        assert (credentials/"credential.json").read_bytes() == before_failure
        again = failing.preflight()
        assert again["status"] == "BLOCKED" and again["http_calls"] == []
        assert (credentials/"credential.json").read_bytes() == before_failure
        assert tf.verify_runtime_profile(PIN_ROOT) == profile
        # Each uncertain grant gets a new synthetic imported slot. Native child
        # must retain pending/old bytes and stop before catalogue or a retry.
        import base64
        def access(**changes):
            claims = dict(iss=op.ISSUER,aud=op.RESOURCE,client_id="synthetic-client",
                sub="synthetic-subject",scope=" ".join(SCOPES),exp=int(time.time())+3600)
            claims.update(changes)
            return "e30."+base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()+".c3ludGhldGlj"
        bad_tokens = [dict(access_token="malformed"),dict(access_token=access(iss="wrong")),
            dict(access_token=access(aud="wrong")),dict(access_token=access(client_id="wrong")),
            dict(access_token=access(sub="wrong")),dict(scope="openid profile"),
            dict(id_token="unvalidated-replacement"),dict(refresh_token=None),dict(expires_in=True)]
        for replacement in bad_tokens:
            credentials = root/("refresh-negative-"+uuid.uuid4().hex)
            credentials.mkdir(mode=0o700)
            with h["SIWCPosixSlot"](str(credentials),approved_root=directory,excluded_roots=[]) as store:
                h["siwc_prepare_host"](store)
                selected_host = json.loads(store.read("host_id.json"))["ext_agent_host_id"]
                selected = dict(siwc_binding(h),destination_host_id=selected_host,expected_source_commit=revision)
                imported_set = siwc_transfer_fixture(h)
                imported_set["source_validation"].update(source_commit=revision,
                    runtime_profile_sha256=RECORDED_REPORT["runtime_profile_sha256"])
                imported_set["credential"].update(expires_at=int(time.time())+10,saved_at=int(time.time())-1)
                h["siwc_import_transfer"](store,json.dumps(imported_set).encode(),selected,
                    source_profile=RECORDED_REPORT["runtime_profile_sha256"],issuer=op.ISSUER,
                    resource=op.RESOURCE,scopes=SCOPES)
            old = (credentials/"credential.json").read_bytes()
            refused_transport = transport(binding_path("preflight-only",selected_host,True),token=replacement)
            refused = refused_transport.preflight()
            assert refused["status"] == "BLOCKED" and len(refused["http_calls"]) == 1
            assert refused["http_calls"][0][:3] == ["POST",op.AUTH_HOST,"/api/accounts/oauth/token"]
            assert (credentials/"credential.json").read_bytes() == old
            assert (credentials/"operation-pending.json").exists()
            assert refused_transport.preflight()["http_calls"] == []
        assert tf.verify_runtime_profile(PIN_ROOT) == profile


def test_siwc_cli_parse_and_preflight_budget(capsys):
    h = siwc_helpers()
    parse = h["siwc_parse_cli"]
    assert parse([]) is None and parse(["--help"]) is None
    flags = ["--pin-root","synthetic-pin","--credential-dir","synthetic-slot",
             "--operator-record","synthetic-binding","--receipt","synthetic-receipt"]
    assert parse(["preflight-only",*flags])["operation"] == "preflight-only"
    for args in (["login"],["dispatch"],["source-export"],["preflight-only"],
                 ["preflight-only",*flags,"--receipt","secret-sentinel"],
                 ["preflight-only",*flags[:-2],"--operator-record","secret-sentinel"],
                 ["preflight-only",*flags[:-1],"--secret-sentinel"],
                 ["preflight-only",*flags,"secret-sentinel"],None):
        with pytest.raises(h["SIWCBlocked"],match="^USAGE_INVALID$") as error: parse(args)
        assert "secret-sentinel" not in repr(error.value)
    make = h["SIWCPreflightBudget"]
    for refreshed in (False,True):
        budget = make(refresh_required=refreshed,refresh_allowed=refreshed)
        if refreshed:
            budget.admit("POST",op.TOKEN_URL)
            budget.complete(200)
        budget.admit("GET",op.RESOURCE+"/models")
        budget.complete(200)
        for method,url in (("GET",op.RESOURCE+"/models"),("POST",op.TOKEN_URL)):
            with pytest.raises(h["SIWCBlocked"]): budget.admit(method,url)
        assert (budget.refresh_count,budget.catalogue_count) == (int(refreshed),1)
        receipt = h["siwc_offline_receipt"](operation="preflight-only",alias="synthetic-01",source_commit="a"*40,
            prompt_sha256="b"*64,spec_sha256="c"*64,hermes_commit=tf.PINNED_HERMES_COMMIT,
            profile=RECORDED_REPORT["runtime_profile_sha256"],checked_at_ns=T0,endpoints=budget.endpoints())
        assert json.loads(h["siwc_receipt_bytes"](receipt))["status"] == "BLOCKED"
    targets = [("POST",op.RESOURCE+"/responses"),("GET","https://chatgpt.com/backend-api/models"),
               ("GET","https://secret-sentinel.invalid/v1/models"),("POST",op.RESOURCE+"/models"),
               ("GET",op.RESOURCE+"/models?secret-sentinel=true"),("GET","https://secret-sentinel@api.openai.com/v1/models"),
               ("GET","http://api.openai.com/v1/models"),("GET","https://api.openai.com:444/v1/models"),
               ("GET","\nhttps://api.openai.com/v1/models"),("GET","https://api.openai.com/v1/mo\tdels"),
               ("GET"," https://api.openai.com/v1/models")]
    for method,url in targets:
        budget = make(refresh_required=False,refresh_allowed=False)
        with pytest.raises(h["SIWCBlocked"],match="^PREFLIGHT_REFUSED$") as error: budget.admit(method,url)
        assert "secret-sentinel" not in repr(error.value)
        with pytest.raises(h["SIWCBlocked"]): budget.admit("GET",op.RESOURCE+"/models")
    for status in (301,401,403,429,500):
        budget = make(refresh_required=True,refresh_allowed=True)
        budget.admit("POST",op.TOKEN_URL)
        with pytest.raises(h["SIWCBlocked"]): budget.complete(status)
        with pytest.raises(h["SIWCBlocked"]): budget.admit("GET",op.RESOURCE+"/models")
        assert budget.refresh_count == 1 and budget.catalogue_count == 0
    budget = make(refresh_required=True,refresh_allowed=False)
    with pytest.raises(h["SIWCBlocked"]): budget.admit("POST",op.TOKEN_URL)
    assert budget.refresh_count == budget.catalogue_count == 0
    budget = make(refresh_required=True,refresh_allowed=True)
    budget.admit("POST",op.TOKEN_URL)
    with pytest.raises(h["SIWCBlocked"]): budget.admit("GET",op.RESOURCE+"/models")
    with pytest.raises(h["SIWCBlocked"]): budget.complete(200)
    with pytest.raises(h["SIWCBlocked"]): budget.admit("POST",op.TOKEN_URL)
    assert budget.refresh_count == 1 and budget.catalogue_count == 0
    assert capsys.readouterr() == ("","")


def test_siwc_real_cli_help_and_usage_have_no_private_io(monkeypatch,capsys):
    def deny(*args,**kwargs): pytest.fail("CLI parse/help constructed transport")
    monkeypatch.setattr(op,"OAuthPlanTransport",deny)
    assert op.main([]) == 0 and op.main(["--help"]) == 0
    assert "preflight-only" in capsys.readouterr().out
    for argv in (["login"],["dispatch"],["source-export"],["preflight-only","--secret-sentinel"],
                 ["prepare-vm-host","--pin-root","secret-sentinel"]):
        assert op.main(argv) == 2
        output = capsys.readouterr()
        assert "secret-sentinel" not in output.out and output.err == ""
        assert json.loads(output.out) == dict(status="BLOCKED",reason_code="USAGE_INVALID")


def test_siwc_authority_and_redaction(monkeypatch,capsys):
    h = siwc_helpers()
    def deny(*args,**kwargs): pytest.fail("independent helper reached a legacy phase")
    monkeypatch.setattr(op.OAuthPlanTransport,"login",deny)
    monkeypatch.setattr(op.OAuthPlanTransport,"_send",deny)
    monkeypatch.setattr(op,"run_oauth_attempt",deny)
    for operation in sorted(h["_SIWC_OPERATIONS"]):
        value = siwc_binding(h,operation)
        def validate(raw,phase=operation):
            return h["siwc_operator"](raw,operation=phase,now_ns=T0+1,source_commit="a"*40,profile="b"*64,
                windows=operation in {"source-login","source-export"})
        assert validate(json.dumps(value).encode()) == value
        for phase in ("login",*sorted(h["_SIWC_OPERATIONS"]-{operation})):
            with pytest.raises(h["SIWCBlocked"]): validate(json.dumps(value).encode(),phase)
        for change in (dict(extra="secret-sentinel"),dict(selected_subject=None),dict(valid_from_ns=True),
                       dict(valid_until_ns=T0-1),dict(valid_until_ns=T0+900_000_000_001),dict(refresh_allowed=1),
                       dict(expected_runtime_profile_sha256="0"*64),dict(attestation={"secret-sentinel":True}),
                       dict(excluded_roots=["/private"]),dict(excluded_roots=["/project","/project"])):
            with pytest.raises(h["SIWCBlocked"]) as error: validate(json.dumps(dict(value,**change)).encode())
            assert "secret-sentinel" not in repr(error.value)
    output = capsys.readouterr()
    assert output.out == output.err == ""


def test_siwc_typed_initial_identity_and_phase_matrix():
    h = siwc_helpers()
    for operation in sorted(h["_SIWC_OPERATIONS"]):
        windows = operation in {"source-login","source-export"}
        value = siwc_binding(h,operation)
        def validate(v,phase=operation,platform=windows):
            return h["siwc_operator"](json.dumps(v).encode(),operation=phase,now_ns=T0+1,
                                      source_commit="a"*40,profile="b"*64,windows=platform)
        assert validate(value) == value
        for other in h["_SIWC_OPERATIONS"]-{operation}:
            with pytest.raises(h["SIWCBlocked"]): validate(value,phase=other)
        with pytest.raises(h["SIWCBlocked"],match="^PLATFORM_UNSUPPORTED$"):
            validate(value,platform=not windows)
        for client,subject in ((None,None),(None,"synthetic-subject"),("synthetic-client",None),
              ("dynamic_agent_client","NEW_REGISTRATION_UNBOUND"),
              ("dynamic_agent_client","synthetic-subject"),("synthetic-client","NEW_REGISTRATION_UNBOUND")):
            proposed = dict(value,selected_client_id=client,selected_subject=subject)
            admitted = (operation == "prepare-vm-host" and client is subject is None) or (
                operation == "source-login" and (client,subject)==("dynamic_agent_client","NEW_REGISTRATION_UNBOUND"))
            if admitted: assert validate(proposed) == proposed
            else:
                with pytest.raises(h["SIWCBlocked"]): validate(proposed)
        if operation in {"source-login","source-export","dispatch"}:
            with pytest.raises(h["SIWCBlocked"]): validate(dict(value,refresh_allowed=True))
    with pytest.raises(h["SIWCBlocked"],match="^RECEIPT_INVALID$"):
        h["siwc_offline_receipt"](operation="dispatch",alias="synthetic-01",source_commit="a"*40,
            prompt_sha256="b"*64,spec_sha256="c"*64,hermes_commit=tf.PINNED_HERMES_COMMIT,
            profile=RECORDED_REPORT["runtime_profile_sha256"],checked_at_ns=T0)


def siwc_posix_mutation_crash_boundaries(h):
    # Actual death after durable pending / simulated single send / replacement.
    script = '''import json,sys,time
v=json.load(sys.stdin); h={}; exec(compile(v["source"],"siwc-refresh-fault","exec"),h)
with h["SIWCPosixSlot"](v["path"],approved_root=v["path"],excluded_roots=[]) as slot:
    pending=h["siwc_begin_mutation"](slot,"preflight-only","synthetic-refresh")
    if v["point"] != "before-send":
        slot.publish("synthetic-send.json",b'{"count":1}')
    if v["point"] == "after-replace":
        slot.replace_credential(b'{"synthetic":"rotated"}')
    print("CUT",flush=True); time.sleep(60)
'''
    for point in ("before-send","after-send","after-replace"):
        with siwc_posix_root() as directory:
            with h["SIWCPosixSlot"](directory,approved_root=directory,excluded_roots=[]) as slot:
                slot.publish("credential.json",b'{"synthetic":"old"}')
                slot.publish("registration.json",b'{"synthetic":"selected"}')
            child = subprocess.Popen([sys.executable,"-I","-B","-c",script],stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                child.stdin.write(json.dumps(dict(source=op._SIWC_SOURCE,path=directory,point=point)))
                child.stdin.close()
                assert child.stdout.readline().strip() == "CUT"
                with pytest.raises(h["SIWCBlocked"],match="^SESSION_BUSY$"):
                    with h["SIWCPosixSlot"](directory,approved_root=directory,excluded_roots=[]): pass
                child.kill();child.wait(timeout=10)
                with h["SIWCPosixSlot"](directory,approved_root=directory,excluded_roots=[]) as slot:
                    before = {p.name:p.read_bytes() for p in Path(directory).iterdir()}
                    with pytest.raises(h["SIWCBlocked"],match="^SLOT_PENDING$"):
                        h["siwc_begin_mutation"](slot,"preflight-only","synthetic-refresh")
                    assert before == {p.name:p.read_bytes() for p in Path(directory).iterdir()}
                    assert slot.read("credential.json") == (b'{"synthetic":"rotated"}' if
                        point == "after-replace" else b'{"synthetic":"old"}')
                    assert (slot.read("synthetic-send.json") is not None) == (point != "before-send")
            finally:
                if child.poll() is None: child.kill();child.wait(timeout=10)


def siwc_posix_root():
    """Actual Linux private ancestor, deliberately outside world-writable /tmp."""
    import tempfile
    return tempfile.TemporaryDirectory(prefix="siwc-native-",dir=Path.home())


@pytest.mark.skipif(sys.platform != "linux",reason="native POSIX destination case; Windows has separate native cases")
def test_siwc_posix_storage_and_import():
    h = siwc_helpers()
    with siwc_posix_root() as directory:
        root = Path(directory)
        with h["SIWCPosixSlot"](str(root),approved_root=str(root),excluded_roots=[str(op._REPO_ROOT)]) as slot:
            h["siwc_prepare_host"](slot)
            first = slot.read("host_id.json",4096)
            h["siwc_prepare_host"](slot)
            assert slot.read("host_id.json",4096) == first
            binding = dict(siwc_binding(h),destination_host_id=json.loads(first)["ext_agent_host_id"])
            transfer = siwc_transfer_fixture(h)
            h["siwc_import_transfer"](slot,json.dumps(transfer).encode(),binding,source_profile="c"*64,
                issuer=op.ISSUER,resource=op.RESOURCE,scopes=SCOPES)
            h["siwc_slot_usable"](slot)
            credential = json.loads(slot.read("credential.json"))
            assert credential == dict(transfer["credential"],ext_agent_host_id=binding["destination_host_id"])
            assert slot.read("host_id.json",4096) == first
            before = {p.name:p.read_bytes() for p in root.iterdir()}
            with pytest.raises(h["SIWCBlocked"],match="^TARGET_EXISTS$"):
                h["siwc_import_transfer"](slot,json.dumps(transfer).encode(),binding,source_profile="c"*64,
                    issuer=op.ISSUER,resource=op.RESOURCE,scopes=SCOPES)
            assert before == {p.name:p.read_bytes() for p in root.iterdir()}
            assert all(p.stat().st_mode & 0o777 == 0o600 for p in root.iterdir())
        with h["SIWCPosixSlot"](str(root),approved_root=str(root),excluded_roots=[]) as slot:
            h["siwc_slot_usable"](slot)
            assert slot.read("host_id.json",4096) == first


@pytest.mark.skipif(sys.platform != "linux",reason="native POSIX destination case")
def test_siwc_posix_negative_files_and_faults(monkeypatch):
    h = siwc_helpers()
    with siwc_posix_root() as directory:
        root = Path(directory)
        def open_slot(): return h["SIWCPosixSlot"](str(root),approved_root=str(root),excluded_roots=[])
        with open_slot() as slot:
            for kind in ("symlink","hardlink","fifo","mode"):
                target = root/kind
                if kind == "symlink": target.symlink_to(root/"absent")
                elif kind == "fifo": os.mkfifo(target,0o600)
                else:
                    target.write_bytes(b"old")
                    target.chmod(0o600 if kind == "hardlink" else 0o644)
                    if kind == "hardlink": os.link(target,root/"second-name")
                with pytest.raises(h["SIWCBlocked"]): slot.read(kind)
                with pytest.raises(h["SIWCBlocked"]): slot.publish(kind,b"new")
                assert not target.is_file() or target.read_bytes() == b"old"
            slot.publish("safe",b"coherent")
            inode = (root/"safe").stat().st_ino
            with pytest.raises(h["SIWCBlocked"]): slot.publish("safe",b"overwrite")
            assert (root/"safe").read_bytes() == b"coherent" and (root/"safe").stat().st_ino == inode
            def fail(*args): raise OSError("secret-sentinel")
            with monkeypatch.context() as patch:
                patch.setattr(os,"fsync",fail)
                with pytest.raises(h["SIWCBlocked"],match="^PUBLICATION_AMBIGUOUS$") as error:
                    slot.barrier("import-pending.json",b'{"partial":true}')
                assert "secret-sentinel" not in repr(error.value)
            assert (root/"import-pending.json").exists()
            with pytest.raises(h["SIWCBlocked"]): h["siwc_slot_usable"](slot)
            assert any(p.name == "import-pending.json" for p in root.iterdir())
        root.chmod(0o755)
        with pytest.raises(h["SIWCBlocked"]): open_slot()
        root.chmod(0o700)
        with pytest.raises(h["SIWCBlocked"]): h["SIWCPosixSlot"](str(root),approved_root=str(root),excluded_roots=[str(root)])
        with pytest.raises(h["SIWCBlocked"]): h["SIWCPosixSlot"]("/tmp",approved_root="/tmp",excluded_roots=[])
        alias = root/"directory-link"
        alias.symlink_to(root,target_is_directory=True)
        with pytest.raises(h["SIWCBlocked"]): h["SIWCPosixSlot"](str(alias),approved_root=str(root),excluded_roots=[])
        # The excluded public root may itself be aliased. No credential/lock
        # creation is permitted inside its underlying canonical directory.
        before = {p.name:p.lstat().st_ino for p in root.iterdir()}
        with pytest.raises(h["SIWCBlocked"],match="^STORAGE_UNSAFE$"):
            h["SIWCPosixSlot"](str(root),approved_root=str(root),excluded_roots=[str(alias)])
        assert before == {p.name:p.lstat().st_ino for p in root.iterdir()}


@pytest.mark.skipif(sys.platform != "linux",reason="native POSIX destination import crash case")
def test_siwc_posix_import_fault_prefixes(monkeypatch):
    h = siwc_helpers()
    for cut in (1,2,3,4):
        with siwc_posix_root() as directory:
            root = Path(directory)
            with h["SIWCPosixSlot"](directory,approved_root=directory,excluded_roots=[]) as slot:
                h["siwc_prepare_host"](slot)
                host = slot.read("host_id.json",4096)
                binding = dict(siwc_binding(h),destination_host_id=json.loads(host)["ext_agent_host_id"])
                original_publish, original_barrier, calls = slot.publish, slot.barrier, []
                def fail_after(name,raw,limit=262144):
                    method = original_barrier if name.startswith("import-") else original_publish
                    method(name,raw,limit)
                    calls.append(name)
                    if len(calls) == cut: raise h["SIWCBlocked"]("PUBLICATION_AMBIGUOUS")
                with monkeypatch.context() as patch:
                    patch.setattr(slot,"publish",fail_after)
                    patch.setattr(slot,"barrier",fail_after)
                    with pytest.raises(h["SIWCBlocked"]):
                        h["siwc_import_transfer"](slot,json.dumps(siwc_transfer_fixture(h)).encode(),binding,
                            source_profile="c"*64,issuer=op.ISSUER,resource=op.RESOURCE,scopes=SCOPES)
                assert slot.read("host_id.json",4096) == host
                before = {p.name:p.read_bytes() for p in root.iterdir()}
                if cut < 4:
                    with pytest.raises(h["SIWCBlocked"],match="^SLOT_PENDING$"): h["siwc_slot_usable"](slot)
                else: h["siwc_slot_usable"](slot)  # Complete durable commit survives a lost reply.
                with pytest.raises(h["SIWCBlocked"],match="^TARGET_EXISTS$"):
                    h["siwc_import_transfer"](slot,json.dumps(siwc_transfer_fixture(h)).encode(),binding,
                        source_profile="c"*64,issuer=op.ISSUER,resource=op.RESOURCE,scopes=SCOPES)
                assert before == {p.name:p.read_bytes() for p in root.iterdir()}


@pytest.mark.skipif(sys.platform != "linux",reason="native POSIX destination process lock case")
def test_siwc_posix_lock_process_death():
    h = siwc_helpers()
    with siwc_posix_root() as directory:
        spec = json.dumps(dict(source=op._SIWC_SOURCE,path=directory))
        script = '''import json,sys,time
v=json.load(sys.stdin); n={}; exec(compile(v["source"],"siwc-child-helpers","exec"),n)
with n["SIWCPosixSlot"](v["path"],approved_root=v["path"],excluded_roots=[]) as slot:
    print("LOCKED",flush=True)
    time.sleep(30)
'''
        child = subprocess.Popen([sys.executable,"-I","-B","-c",script],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,text=True)
        try:
            child.stdin.write(spec); child.stdin.close()
            assert child.stdout.readline().strip() == "LOCKED"
            with pytest.raises(h["SIWCBlocked"],match="^SESSION_BUSY$"):
                with h["SIWCPosixSlot"](directory,approved_root=directory,excluded_roots=[]): pass
            inode = (Path(directory)/"session.lock").stat().st_ino
            child.kill(); child.wait(timeout=10)
            with h["SIWCPosixSlot"](directory,approved_root=directory,excluded_roots=[]): pass
            assert (Path(directory)/"session.lock").stat().st_ino == inode
        finally:
            if child.poll() is None: child.kill(); child.wait(timeout=10)


def siwc_windows_elevated_refusal(h):
    """Actual elevated runners prove refusal; native positives require ordinary tokens."""
    import ctypes as c
    from ctypes import wintypes as w
    import tempfile
    import uuid
    k, a = c.WinDLL("kernel32",use_last_error=True), c.WinDLL("advapi32",use_last_error=True)
    k.GetCurrentProcess.restype = w.HANDLE
    k.CloseHandle.argtypes = [w.HANDLE]
    a.OpenProcessToken.argtypes = [w.HANDLE,w.DWORD,c.c_void_p]
    a.GetTokenInformation.argtypes = [w.HANDLE,c.c_int,c.c_void_p,w.DWORD,c.c_void_p]
    token, elevated, size = w.HANDLE(), w.DWORD(), w.DWORD()
    assert a.OpenProcessToken(k.GetCurrentProcess(),8,c.byref(token))
    try:
        assert a.GetTokenInformation(token,20,c.byref(elevated),c.sizeof(elevated),c.byref(size))
    finally:
        assert k.CloseHandle(token)
    if not elevated.value:
        return False
    # No token downgrade, privilege mock, ACL change or ignored native failure.
    # This path never exists, so unsupported admission must leave it absent.
    absent = Path(tempfile.gettempdir())/("siwc-never-created-"+uuid.uuid4().hex)
    assert not absent.exists()
    with pytest.raises(h["SIWCBlocked"],match="^PLATFORM_UNSUPPORTED$"):
        with h["SIWCWindowsSlot"](str(absent),approved_root=str(absent),excluded_roots=[]): pass
    assert not absent.exists()
    return True


def siwc_windows_private_directory(parent,name="slot"):
    """Synthetic fixture only: create a new directory with its DACL from birth."""
    import ctypes as c
    from ctypes import wintypes as w
    k, a = c.WinDLL("kernel32",use_last_error=True), c.WinDLL("advapi32",use_last_error=True)
    P = c.c_void_p
    k.GetCurrentProcess.restype = w.HANDLE
    k.CloseHandle.argtypes = [w.HANDLE]
    k.LocalFree.argtypes = [P]
    a.OpenProcessToken.argtypes = [w.HANDLE,w.DWORD,P]
    a.GetTokenInformation.argtypes = [w.HANDLE,c.c_int,P,w.DWORD,P]
    a.ConvertSidToStringSidW.argtypes = [P,P]
    a.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [w.LPCWSTR,w.DWORD,P,P]
    k.CreateDirectoryW.argtypes = [w.LPCWSTR,P]
    token, size, descriptor, sid = w.HANDLE(), w.DWORD(), P(), w.LPWSTR()
    assert a.OpenProcessToken(k.GetCurrentProcess(),8,c.byref(token))
    try:
        a.GetTokenInformation(token,1,None,0,c.byref(size))
        data = c.create_string_buffer(size.value)
        assert a.GetTokenInformation(token,1,data,size,c.byref(size))
        assert a.ConvertSidToStringSidW(c.cast(data,c.POINTER(P))[0],c.byref(sid))
        sddl = "O:"+sid.value+"D:P(A;;FA;;;"+sid.value+")(A;;FA;;;SY)"
        assert a.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,1,c.byref(descriptor),None)
        class Security(c.Structure):
            _fields_ = [("length",w.DWORD),("descriptor",P),("inherit",w.BOOL)]
        security = Security(c.sizeof(Security),descriptor,False)
        path = parent/name
        assert k.CreateDirectoryW(str(path),c.byref(security))
        return path
    finally:
        k.CloseHandle(token)
        if sid: k.LocalFree(c.cast(sid,P))
        if descriptor: k.LocalFree(descriptor)


@pytest.mark.skipif(sys.platform != "win32",reason="native Windows source case")
def test_siwc_windows_storage_barriers_and_lock(tmp_path):
    h = siwc_helpers()
    if siwc_windows_elevated_refusal(h):
        return
    # The ordinary temp ancestry may grant sandbox principals write/delete.
    # Create only this synthetic private fixture directly under the same root.
    import uuid
    root = siwc_windows_private_directory(Path(tmp_path.anchor),"siwc-synthetic-"+uuid.uuid4().hex)
    def open_slot():
        return h["SIWCWindowsSlot"](str(root),approved_root=str(root),excluded_roots=[str(op._REPO_ROOT)])
    policy, observed_root = h["siwc_windows_acl_policy"], []
    def observe_policy(owner,current,trusted,protected,entries,*,leaf,verified_volume_root=False):
        if verified_volume_root and any(not flags & 8 and sid not in trusted and mask & 0x500D0156 == 4
                                       for kind,flags,mask,sid in entries):
            observed_root.append(True)
        return policy(owner,current,trusted,protected,entries,leaf=leaf,verified_volume_root=verified_volume_root)
    h["siwc_windows_acl_policy"] = observe_policy
    with open_slot() as slot:
        assert observed_root  # Actual native root ACE, not a mocked root predicate.
        slot.publish("synthetic.json",b'{"synthetic":true}')
        assert slot.read("synthetic.json") == b'{"synthetic":true}'
        identity = (root/"synthetic.json").stat().st_ino
        with pytest.raises(h["SIWCBlocked"],match="^TARGET_EXISTS$"):
            slot.publish("synthetic.json",b"overwrite")
        assert (root/"synthetic.json").stat().st_ino == identity
        siwc_native_windows_root_negatives(h,slot,root)
        original_canonical = h["SIWCWindowsSlot"]._canonical_path
        def excluded_alias(self,handle):
            path = original_canonical(self,handle)
            if handle == self.fd: return path
            return original_canonical(self,self.fd)/"synthetic-release"
        # Real Win32 handles, with bounded canonical-name injection for an
        # excluded alias; no host junction, ACL or volume mutation is required.
        h["SIWCWindowsSlot"]._canonical_path = excluded_alias
        try:
            with pytest.raises(h["SIWCBlocked"],match="^STORAGE_UNSAFE$"):
                open_slot()
        finally: h["SIWCWindowsSlot"]._canonical_path = original_canonical
        with pytest.raises(h["SIWCBlocked"],match="^SESSION_BUSY$"):
            with open_slot(): pass
        h["siwc_retire_source"](slot,siwc_state_fixture())
        assert h["siwc_source_state"](slot.read("export-pending.json"),slot.read("export-retired.json")) == "SOURCE_SESSION_RETIRED"
    with open_slot() as slot:
        with pytest.raises(h["SIWCBlocked"],match="^SOURCE_SESSION_RETIRED$"):
            h["siwc_slot_usable"](slot)
    siwc_native_windows_replacement_failures(h)
    siwc_native_windows_publication_failures(h)


def siwc_native_windows_publication_failures(h):
    """Inject BOOL/short-I/O failures around real handles; no repair or retry."""
    import ctypes
    import uuid
    for api in ("CreateFileW","WriteFile","FlushFileBuffers","SetFilePointerEx","ReadFile","MoveFileExW"):
        for short in ((False,True) if api in {"WriteFile","ReadFile"} else (False,)):
            root = siwc_windows_private_directory(Path(Path.cwd().anchor),"siwc-synthetic-"+uuid.uuid4().hex)
            with h["SIWCWindowsSlot"](str(root),approved_root=str(root),excluded_roots=[]) as slot:
                slot.publish("credential.json",b'{"synthetic":"old"}')
                original_bytes = (root/"credential.json").read_bytes()
                original_id = (root/"credential.json").stat().st_ino
                original, calls = getattr(slot.k,api), []
                def fail(*args):
                    calls.append(True)
                    if api == "CreateFileW":
                        ctypes.set_last_error(32)  # sharing collision before token publication
                        return ctypes.c_void_p(-1).value
                    if short:
                        adjusted = list(args); adjusted[2] = max(1,args[2]//2)
                        return original(*adjusted)
                    return False
                setattr(slot.k,api,fail)
                try:
                    with pytest.raises(h["SIWCBlocked"]): slot.publish("transfer.json",b'{"synthetic":"token"}')
                    assert calls and not (root/"transfer.json").exists()
                finally: setattr(slot.k,api,original)
                assert (root/"credential.json").read_bytes() == original_bytes
                assert (root/"credential.json").stat().st_ino == original_id


def siwc_native_windows_root_negatives(h,slot,root):
    """Native handles with bounded injected metadata; no actual ACL mutations."""
    import ctypes
    original_final,original_info = slot.k.GetFinalPathNameByHandleW,slot.k.GetFileInformationByHandle
    def probe():
        candidate = h["SIWCWindowsSlot"].__new__(h["SIWCWindowsSlot"])
        for name in ("c","w","k","a","Info","Security"): setattr(candidate,name,getattr(slot,name))
        candidate.handles,candidate.lock_handle,candidate.fd,candidate.root_identity=[],None,None,None
        return candidate
    for fault in ("subdirectory","truncated","wrong-volume","wrong-identity"):
        candidate = probe()
        def final(handle,buffer,length,flags):
            result = original_final(handle,buffer,length,flags)
            if flags == 1:
                if fault == "subdirectory": buffer.value += "synthetic-child\\";return len(buffer.value)
                if fault == "truncated": return length
            return result
        def information(handle,pointer):
            result = original_info(handle,pointer)
            if handle != slot.handles[0]:
                info = ctypes.cast(pointer,ctypes.POINTER(slot.Info)).contents
                if fault == "wrong-volume": info.volume ^= 1
                if fault == "wrong-identity": info.index_low ^= 1
            return result
        slot.k.GetFinalPathNameByHandleW,slot.k.GetFileInformationByHandle=final,information
        try:
            with pytest.raises(h["SIWCBlocked"]): candidate._prove_volume_root(slot.handles[0])
            assert candidate.root_identity is None
        finally:
            slot.k.GetFinalPathNameByHandleW,slot.k.GetFileInformationByHandle=original_final,original_info
            candidate.close()
    # Held parent handles prohibit replacement/rename without touching host ACLs.
    with pytest.raises(OSError): root.rename(root.with_name(root.name+"-moved"))
    assert root.is_dir() and not root.with_name(root.name+"-moved").exists()
    os.link(root/"synthetic.json",root/"synthetic-alias.json")
    try:
        with pytest.raises(h["SIWCBlocked"],match="^STORAGE_UNSAFE$"): slot.read("synthetic.json")
    finally: (root/"synthetic-alias.json").unlink()  # This test's synthetic link only.
    assert slot.read("synthetic.json") == b'{"synthetic":true}'
    original_read = slot.k.ReadFile
    def short_read(handle,buffer,length,size,overlap):
        return original_read(handle,buffer,8,size,overlap)
    slot.k.ReadFile = short_read
    try:
        with pytest.raises(h["SIWCBlocked"],match="^STORAGE_UNSAFE$"): slot.read("synthetic.json")
    finally: slot.k.ReadFile = original_read
    def reparse_info(handle,pointer):
        result = original_info(handle,pointer)
        ctypes.cast(pointer,ctypes.POINTER(slot.Info)).contents.attributes |= 0x400
        return result
    slot.k.GetFileInformationByHandle = reparse_info
    try:
        with pytest.raises(h["SIWCBlocked"],match="^STORAGE_UNSAFE$"): slot.read("synthetic.json")
    finally: slot.k.GetFileInformationByHandle = original_info
    assert slot.read("synthetic.json") == b'{"synthetic":true}'


def siwc_native_windows_replacement_failures(h):
    import ctypes
    import uuid
    for outcome,error in (("unchanged",1175),("missing",1176),("renamed-original",1177)):
        root = siwc_windows_private_directory(Path(Path.cwd().anchor),"siwc-synthetic-"+uuid.uuid4().hex)
        with h["SIWCWindowsSlot"](str(root),approved_root=str(root),excluded_roots=[]) as slot:
            slot.publish("credential.json",b'{"synthetic":"old"}')
            slot.barrier("operation-pending.json",b'{"synthetic_pending":true}')
            original_id = (root/"credential.json").stat().st_ino
            pending_id = (root/"operation-pending.json").stat().st_ino
            original = slot.k.ReplaceFileW
            calls = []
            def partial(target,replacement,backup,flags,*rest):
                calls.append(True)
                assert backup is None and flags == 0
                if outcome == "missing": assert slot.k.DeleteFileW(target)
                if outcome == "renamed-original":
                    # Documented1177: old file renamed, replacement still at its
                    # original name with merged metadata. Identical private DACLs
                    # in this fixture need no real ACL mutation to model the state.
                    assert slot.k.MoveFileExW(target,str(root/"synthetic-old-renamed.json"),8)
                ctypes.set_last_error(error)
                return False
            slot.k.ReplaceFileW = partial
            try:
                with pytest.raises(h["SIWCBlocked"]): slot.replace_credential(b'{"synthetic":"new"}')
                assert len(calls) == 1 and slot.read("operation-pending.json") == b'{"synthetic_pending":true}'
                assert (root/"operation-pending.json").stat().st_ino == pending_id
                replacements = [p for p in root.iterdir() if p.name.startswith(".siwc-")]
                assert len(replacements) == 1 and replacements[0].read_bytes() == b'{"synthetic":"new"}'
                if outcome == "unchanged":
                    assert slot.read("credential.json") == b'{"synthetic":"old"}'
                    assert (root/"credential.json").stat().st_ino == original_id
                else: assert slot.read("credential.json") is None
                if outcome == "renamed-original":
                    old = root/"synthetic-old-renamed.json"
                    assert old.read_bytes() == b'{"synthetic":"old"}' and old.stat().st_ino == original_id
                with pytest.raises(h["SIWCBlocked"]): h["siwc_slot_usable"](slot)
            finally: slot.k.ReplaceFileW = original


@pytest.mark.skipif(sys.platform != "win32",reason="native Windows unsafe ACL case")
def test_siwc_windows_unsafe_storage_refuses_without_mutation(tmp_path):
    h = siwc_helpers()
    if siwc_windows_elevated_refusal(h):
        return
    ordinary = tmp_path/"inherited"
    ordinary.mkdir()
    before = ordinary.stat()
    with pytest.raises(h["SIWCBlocked"],match="^STORAGE_UNSAFE$"):
        with h["SIWCWindowsSlot"](str(ordinary),approved_root=str(ordinary),excluded_roots=[]): pass
    assert list(ordinary.iterdir()) == [] and ordinary.stat().st_ino == before.st_ino


def test_siwc_malformed_inputs_never_escape_closed_errors():
    h = siwc_helpers()
    value = siwc_binding(h)
    for operation in ([], {}, None, True):
        with pytest.raises(h["SIWCBlocked"],match="^OPERATOR_BINDING_INVALID$"):
            h["siwc_operator"](json.dumps(value).encode(),operation=operation,now_ns=T0,
                               source_commit="a"*40,profile="b"*64)
    for operation in ([], {}, None, True):
        with pytest.raises(h["SIWCBlocked"],match="^RECEIPT_INVALID$"):
            h["siwc_offline_receipt"](operation=operation,alias="synthetic-01",source_commit="a"*40,
                prompt_sha256="b"*64,spec_sha256="c"*64,hermes_commit=tf.PINNED_HERMES_COMMIT,
                profile=RECORDED_REPORT["runtime_profile_sha256"],checked_at_ns=T0)


def test_siwc_windows_acl_policy_conservative_matrix():
    h = siwc_helpers()
    check = h["siwc_windows_acl_policy"]
    owner, system, admin, installer, untrusted = "synthetic-owner","S-1-5-18","S-1-5-32-544","synthetic-installer","S-1-5-11"
    trusted = {owner,system,admin,installer}
    full = 0x1F01FF
    private = [(0,0,full,owner),(0,0,full,system)]
    check(owner,owner,trusted,True,private,leaf=True)
    for principal in trusted:
        check(principal,owner,trusted,False,[(0,0,full,principal)],leaf=False)
    for mask in (2,4,16,64,256,0x10000,0x40000,0x80000,0x10000000,0x40000000):
        with pytest.raises(h["SIWCBlocked"],match="^STORAGE_UNSAFE$"):
            check(installer,owner,trusted,False,[(0,0,mask,untrusted)],leaf=False)
    # The observed C:\\ grant is precisely the mask4 case, independent of leaf path.
    for path_label in ("private-temp","private-home","new-private-leaf"):
        with pytest.raises(h["SIWCBlocked"],match="^STORAGE_UNSAFE$"):
            check(installer,owner,trusted,False,[(0,0,4,untrusted)],leaf=False)
    for entries,protected,actual_owner in ((private,False,owner),([],True,owner),
        (private,True,untrusted),([(0,16,full,owner)],True,owner),
        (private+[(0,0,1,untrusted)],True,owner),([(1,0,full,owner)],True,owner)):
        with pytest.raises(h["SIWCBlocked"],match="^STORAGE_UNSAFE$"):
            check(actual_owner,owner,trusted,protected,entries,leaf=True)
    check(installer,owner,trusted,False,[(0,0,0x1200A9,untrusted)],leaf=False)
    # INHERIT_ONLY does not grant access to the ancestor itself; leaf DACLs
    # independently reject inherited/broad access. This preserves existing policy.
    check(installer,owner,trusted,False,[(0,8,full,untrusted)],leaf=False)
    # The private root classifier is fed by handle proof in native storage code.
    check(installer,owner,trusted,False,[(0,0,4,untrusted)],leaf=False,verified_volume_root=True)
    check(installer,owner,trusted,False,[(0,0,0x1200A9|4,untrusted)],leaf=False,verified_volume_root=True)
    for mask in (2,16,64,256,0x10000,0x40000,0x80000,0x10000000,0x40000000):
        for addition in (0,4):
            with pytest.raises(h["SIWCBlocked"],match="^STORAGE_UNSAFE$"):
                check(installer,owner,trusted,False,[(0,0,mask|addition,untrusted)],
                      leaf=False,verified_volume_root=True)
    with pytest.raises(h["SIWCBlocked"],match="^STORAGE_UNSAFE$"):
        check(owner,owner,trusted,True,private+[(0,0,4,untrusted)],leaf=True,verified_volume_root=True)
    with pytest.raises(h["SIWCBlocked"],match="^STORAGE_UNSAFE$"):
        check(installer,owner,trusted,False,[(0,0,4,untrusted),(0,0,64,untrusted)],
              leaf=False,verified_volume_root=True)


@pytest.mark.skipif(sys.platform != "linux",reason="actual anchored POSIX read race")
def test_siwc_posix_missing_name_after_open_is_not_absence(monkeypatch):
    h = siwc_helpers()
    with siwc_posix_root() as directory:
        with h["SIWCPosixSlot"](directory,approved_root=directory,excluded_roots=[]) as slot:
            slot.barrier("export-pending.json",b'{"synthetic":true}')
            real_stat = os.stat
            def lose_name(path,*args,**kwargs):
                if path == "export-pending.json": raise FileNotFoundError("synthetic-only")
                return real_stat(path,*args,**kwargs)
            with monkeypatch.context() as patch:
                patch.setattr(os,"stat",lose_name)
                with pytest.raises(h["SIWCBlocked"],match="^STORAGE_UNSAFE$"):
                    slot.read("export-pending.json")
            assert slot.read("export-pending.json") == b'{"synthetic":true}'
