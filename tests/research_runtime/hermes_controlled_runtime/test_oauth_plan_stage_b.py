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
                  hermes_commit=tf.PINNED_HERMES_COMMIT, refreshed=False, token_seconds_remaining=3000,
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
                  hermes_commit=tf.PINNED_HERMES_COMMIT, hermes_version="0.21.3", construction_network_attempts=[],
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
    require_pin()
    monkeypatch.undo()  # the real child runner from here on
    # Native mock sign-in: PKCE/state/nonce, loopback callback, token exchange, JWKS-signed ID token.
    world = mock_world(tmp_path)
    login = world.login()
    assert login["status"] == "DONE" and login["registration"] == "NEW" and login["id_token_valid"] is True, login
    assert set(login["scopes_granted"]) == op.REQUIRED_SCOPES and login["network_attempts"] == []
    assert [c[:3] for c in login["http_calls"]] == [["POST", "auth.openai.com", "/api/accounts/oauth/token"],
                                                    ["GET", "auth.openai.com", "/.well-known/jwks.json"]]
    stored = json.loads((tmp_path / "creds" / "credential.json").read_text())
    for secret in (stored["access_token"], stored["refresh_token"], stored["id_token"], "mock-subject", "oaiapp_mock"):
        assert secret not in json.dumps(login)
    check = world.preflight()
    assert check["status"] == "DONE" and check["target_listed"] is True and check["refreshed"] is False, check
    verdict = op.evaluate_preflight(check, attestation=ATTEST, checked_at_ns=T0)
    assert verdict.reason_code == "MOCK_TRANSPORT_NOT_ELIGIBLE"  # mock can never become eligible
    returning = world.login()
    assert returning["status"] == "DONE" and returning["registration"] == "RETURNING"
    for kwargs, code in ((dict(callback=dict(error="access_denied", code=None)), "CONSENT_DENIED"),
                         (dict(callback=dict(state="forged-state")), "STATE_MISMATCH"),
                         (dict(callback=dict(client_id=None)), "REGISTRATION_INCOMPLETE"),
                         (dict(token=dict(id_claims=dict(aud="oaiapp_other"))), "ID_TOKEN_INVALID"),
                         (dict(token=dict(id_claims=dict(nonce="replayed"))), "ID_TOKEN_NONCE_MISMATCH"),
                         (dict(token=dict(status=400)), "TOKEN_EXCHANGE_FAILED")):
        failed = mock_world(tmp_path / code, **kwargs).login()
        assert failed["status"] == "BLOCKED" and failed["reason_code"] == code, (code, failed)
        assert not (tmp_path / code / "creds" / "credential.json").exists()
    # Granted scopes without chatgpt.tokens.use.direct: sign-in kept, plan usage blocked before inference.
    narrow = mock_world(tmp_path / "narrow", token=dict(scope="openid profile email offline_access"))
    assert narrow.login()["status"] == "DONE"
    assert op.evaluate_preflight(narrow.preflight(), attestation=ATTEST, checked_at_ns=T0).reason_code == "PLAN_SCOPE_MISSING"
    missing = mock_world(tmp_path / "absent", models=dict(status=200, body=dict(models=[dict(slug="gpt-other")])))
    assert missing.login()["status"] == "DONE"
    report = missing.preflight()
    assert report["target_listed"] is False and op.evaluate_preflight(
        dict(report, mode="real"), attestation=ATTEST, checked_at_ns=T0).reason_code == "OAUTH_MODEL_NOT_AVAILABLE"
    assert mock_world(tmp_path / "nocred").preflight()["reason_code"] == "CREDENTIAL_MISSING"


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
    require_pin()
    # Native exact pin, mock transport: post-SDK body captured before send, zero tools, official route.
    world = mock_world(tmp_path, scenario=sse_message(NO_TRADE))
    assert world.login()["status"] == "DONE"
    report = world._send(REQUEST)
    assert report["status"] == "DONE" and report["construction_network_attempts"] == [] and report["network_attempts"] == []
    body = report["requests"][0]
    assert op.verify_dispatch_wire(REQUEST, report)["status"] == op.real01.WIRE_CHECKED, (report, body)
    assert body["tools_count"] == 0 and body["store"] is False and body["stream"] is True and body["input_roles"] == ["user"]
    assert "max_output_tokens" not in body["body_keys"] and set(body["body_keys"]) <= op.BODY_ALLOWED
    assert body["host"] == "api.openai.com" and body["path"] == "/v1/responses" and body["retry_count_header"] == "0"
    assert report["sdk_max_retries"] == 0 and report["hermes_version"] == "0.21.3"
    # The pre-send hook really stops the bytes: forbid a key the native body always carries.
    monkeypatch.setattr(op, "UNSUPPORTED_FIELDS", op.UNSUPPORTED_FIELDS | {"include"})
    blocked = world._send(REQUEST)
    assert blocked["presend_block"] == "PRESEND_WIRE_REJECTED" and blocked["http_calls"] == [], blocked
    assert blocked.get("final") is None and len(blocked["requests"]) == 1
    # Timing invariant: an eligible token always outlives the eligibility window at dispatch.
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
    require_pin()
    monkeypatch.undo()  # the real child runner from here on
    # Native mock: a 429 and a read timeout each make exactly one POST and no SDK retry.
    for name, scenario, expected in (("rl", dict(kind="http", status=429, code="subscription_sharing_usage_limit_exceeded"),
                                      "PROVIDER_RATE_LIMITED"),
                                     ("to", dict(kind="raise", error="ReadTimeout"), "PROVIDER_TIMEOUT")):
        world = mock_world(tmp_path / name, scenario=scenario)
        assert world.login()["status"] == "DONE"
        result = op.run_oauth_attempt(REQUEST, eligibility=None, transport=world, journal_dir=tmp_path / name / "j",
                                      clock_ns=clock())
        assert result.status == expected and world.dispatch_count == 1, result
        assert result.origin["generation_requests"] == 1 and result.origin["transport_mode"] == op.TRANSPORT_MOCK
        assert result.origin["real_origin"] == op.REAL_ORIGIN_UNVERIFIED


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
    require_pin()
    monkeypatch.undo()  # the real child runner from here on
    # Native mock SSE through the pinned assembler: reasoning + message is valid; tool items are not.
    reasoning = dict(id="r1", type="reasoning", summary=[])
    function = dict(id="fc1", type="function_call", call_id="c1", name="terminal", arguments="{}")
    for name, scenario, expected in (("ok", sse_message(NO_TRADE, extra_items=[reasoning]), op.VALID_OUTPUT),
                                     ("tool", sse_message(NO_TRADE, extra_items=[function]), "TOOL_CALL_ATTEMPT_INVALID"),
                                     ("cap", sse_message("x" * (op.MAX_OUTPUT_BYTES + 10)), "OUTPUT_SIZE_INVALID"),
                                     ("model", sse_message(NO_TRADE, model="gpt-other"), "MODEL_MISMATCH")):
        world = mock_world(tmp_path / ("native" + name), scenario=scenario)
        assert world.login()["status"] == "DONE"
        report = world._send(REQUEST)
        status, facts, raw = classify(report)
        assert status == expected, (name, status, report.get("final"), report.get("error_class"))
        if expected == op.VALID_OUTPUT:
            assert raw == NO_TRADE.encode() and facts["usage"] == dict(input_tokens=10, output_tokens=5, total_tokens=15)
            assert facts["response_id_sha256"] == hashlib.sha256(b"resp_mock").hexdigest()
            assert facts["x_request_id_sha256"] == hashlib.sha256(b"req_mock").hexdigest()
