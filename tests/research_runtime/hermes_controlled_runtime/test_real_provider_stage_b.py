"""S10-HERMES-AUTO-02-REAL-01: dormant one-request Codex Responses wire and honest origin.

The native checks run the exact pinned Hermes v0.21.3 child when the checkout is present
(local operator machine): a placeholder bearer, a sterile home, denied sockets and an
in-memory httpx MockTransport behind the pinned OpenAI SDK. The verdict/journal matrix
always runs on recorded reports of the same shape. NO_PROVIDER_CALL: no credential,
provider, model or product network is used anywhere.
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

from src.research_runtime.hermes_controlled_runtime import autonomous_feedback as fb
from src.research_runtime.hermes_controlled_runtime import real_provider_stage_b as rp
from src.research_runtime.hermes_controlled_runtime import tool_free_stage_b as tf
from tests.research_runtime.hermes_controlled_runtime.test_tool_free_stage_b import PIN_ROOT, RECORDED_REPORT

ROOT = Path(__file__).resolve().parents[3]
T0 = 1_790_000_000_000_000_000
MODEL = rp.ROUTE["model"]
MENU = [dict(candidate_id="alphacandidate:sha256:" + "1" * 64, strategy_version_id="strategyversion:sha256:" + "2" * 64,
             gamma_market_id="123", condition_id="0x" + "3" * 64, token_id="456")]
NO_TRADE = json.dumps(dict(action="NO_TRADE", proof_level="SYNTHETIC_ONLY", information_cutoff_ns=T0,
                           produced_at_ns=T0 + 1, expires_at_ns=T0 + 30_000_000_000))
TRADE = json.dumps(dict(json.loads(NO_TRADE), action="TRADE", candidate_id=MENU[0]["candidate_id"],
                        strategy_version_id=MENU[0]["strategy_version_id"], hermes_assessment_id=None,
                        context_sha256=None, active_policy_id=None, side="BUY", execution_style="PASSIVE_MAKER",
                        order_type="GTC", requested_shares="10", price_limit="0.51", post_only=True,
                        gtd_expiration_unix_s=None))


def make_request(menu=MENU, deadline_ns=T0 + 60_000_000_000):
    stage = fb.cycle_request(surface_report=RECORDED_REPORT, candidate_menu=menu, information_cutoff_ns=T0,
                             issued_at_ns=T0, deadline_ns=deadline_ns, model_label=MODEL)
    return rp.build_real01_request(stage, model_input=rp.real01_model_input(menu, T0))


REQUEST = make_request()


def message(text, *, model=MODEL, usage=(10, 5, 15), terminal="response.completed", status="completed"):
    item = dict(id="m1", type="message", role="assistant", content=[])
    response = dict(id="resp_offline_fixture", model=model, status=status)
    if usage is not None:
        response["usage"] = dict(zip(("input_tokens", "output_tokens", "total_tokens"), usage))
    if model is None:
        del response["model"]
    return [dict(type="response.output_item.added", output_index=0, item=item),
            dict(type="response.output_text.delta", item_id="m1", output_index=0, delta=text),
            dict(type="response.output_item.done", output_index=0, item=dict(item, status="completed",
                 content=[dict(type="output_text", text=text)])),
            dict(type=terminal, response=response)]


def item_events(item, index=0):
    return [dict(type="response.output_item.added", output_index=index, item=dict(item, status="in_progress")),
            dict(type="response.output_item.done", output_index=index, item=dict(item, status="completed"))]


FUNCTION_CALL = dict(id="fc1", type="function_call", call_id="call1", name="terminal", arguments="{}")
WEB_SEARCH = dict(id="ws1", type="web_search_call", action=dict(type="search", query="offline"))
COMPLETED = message(NO_TRADE)[-1]
SCENARIOS = {  # name -> (offline fake server behaviour, expected terminal)
    "no_trade": (dict(kind="sse", events=message(NO_TRADE)), rp.VALID_OUTPUT),
    "trade": (dict(kind="sse", events=message(TRADE)), rp.VALID_OUTPUT),
    "function_call": (dict(kind="sse", events=item_events(FUNCTION_CALL) + [COMPLETED]), "TOOL_CALL_ATTEMPT_INVALID"),
    "builtin_tool": (dict(kind="sse", events=item_events(WEB_SEARCH) + message(NO_TRADE)), "TOOL_CALL_ATTEMPT_INVALID"),
    "two_replies": (dict(kind="sse", events=message(NO_TRADE)[:3] + [dict(e, output_index=1) for e in message(NO_TRADE)]),
                    "RESPONSE_SHAPE_INVALID"),
    "incomplete": (dict(kind="sse", events=message(NO_TRADE, terminal="response.incomplete", status="incomplete")),
                   "RESPONSE_INCOMPLETE"),
    "no_terminal": (dict(kind="sse", events=message(NO_TRADE)[:3]), "RESPONSE_INCOMPLETE"),
    "empty_sse": (dict(kind="sse", events=[]), "RESPONSE_INCOMPLETE"),
    "stream_error": (dict(kind="sse", events=[dict(type="error", message="offline fixture")]), "TRANSPORT_OR_STREAM_ERROR"),
    "model_mismatch": (dict(kind="sse", events=message(NO_TRADE, model="gpt-other")), "MODEL_MISMATCH"),
    "no_usage": (dict(kind="sse", events=message(NO_TRADE, usage=None)), rp.VALID_OUTPUT),
    "malformed": (dict(kind="sse", events=message('{"action":"NO_TRADE","action":"TRADE"}')), "OUTPUT_JSON_INVALID"),
    "rate_limited": (dict(kind="http", status=429), "PROVIDER_RATE_LIMITED"),
    "server_error": (dict(kind="http", status=503), "PROVIDER_SERVER_ERROR"),
    "read_timeout": (dict(kind="raise", error="ReadTimeout"), "PROVIDER_TIMEOUT"),
    "connect_error": (dict(kind="raise", error="ConnectError"), "TRANSPORT_OR_STREAM_ERROR"),
}


@pytest.fixture(scope="module")
def native_report():
    """One pinned child over every offline scenario (each scenario: fresh SDK client), or None."""
    if not (PIN_ROOT / ".git" / "HEAD").is_file():
        return None
    report = rp.capture_offline_wire(PIN_ROOT, REQUEST, [s for s, _ in SCENARIOS.values()])
    assert len(report["results"]) == len(SCENARIOS), report
    return report


def require_pin(native_report):
    if native_report is None:
        pytest.skip("exact pinned Hermes v0.21.3 checkout unavailable; recorded-report matrix only")


def single(report, name):
    return dict(report, results=[report["results"][list(SCENARIOS).index(name)]])


def sent(request=REQUEST, **changes):
    value = dict(method="POST", scheme="https", host="chatgpt.com", port=None, path="/backend-api/codex/responses",
                 body_sha256="f" * 64, body_bytes=1200, body_keys=sorted(["include", "input", "instructions", "model",
                 "prompt_cache_key", "reasoning", "store", "stream"]), model=MODEL, stream=True, store=False,
                 include=["reasoning.encrypted_content"], tools_count=0, tool_choice_present=False,
                 instructions_sha256=request.instructions_sha256,
                 input_sha256=hashlib.sha256(rp._canon_input(request.model_input.decode())).hexdigest(),
                 authorization_present=True, retry_count_header="0")
    value.update(changes)
    return value


def recorded(request=REQUEST, *, text=NO_TRADE, requests=None, **changes):
    """Shape recorded from the exact-pin child on 2026-10-16 (synthetic copy for the pure verdict)."""
    result = dict(requests=[sent(request)] if requests is None else requests, sdk_max_retries=0, http_status=None,
                  error_class=None, terminal_events=["response.completed"], server_model=MODEL,
                  final=dict(status="completed", assembler_model=MODEL, output_types=["message"], output_text=text,
                             response_id_sha256="e" * 64,
                             usage=dict(input_tokens=10, output_tokens=5, total_tokens=15)))
    report = dict(schema="real01-offline-codex-wire-v1", hermes_version="0.21.3", hermes_commit=tf.PINNED_HERMES_COMMIT,
                  control_tools_count=18, network_attempts=[], control_network_attempts=[["models.dev", 443]],
                  results=[result])
    for path, value in changes.items():
        target = report
        keys = path.split(".")
        for key in keys[:-1]:
            target = target[int(key)] if isinstance(target, list) else target[key]
        target[keys[-1]] = value
    return report


def classify(report, request=REQUEST, finished=T0 + 2):
    return rp.classify_wire_report(request, report, dispatched_at_ns=T0 + 1, finished_at_ns=finished)


def test_real01_native_final_wire_has_no_tool_or_unapproved_endpoint(native_report, tmp_path):
    # Binding reuse: AUTO-02 cycle_request's model_input digest is exactly the bytes sent.
    stage = fb.cycle_request(surface_report=RECORDED_REPORT, candidate_menu=MENU, information_cutoff_ns=T0,
                             issued_at_ns=T0, deadline_ns=T0 + 60_000_000_000, model_label=MODEL)
    assert REQUEST.stage_b_request_id == stage.request_id and rp.request_is_bound(REQUEST)
    assert REQUEST.model_input_sha256 == stage.model_input_sha256 == hashlib.sha256(REQUEST.model_input).hexdigest()
    assert REQUEST.tool_surface_fingerprint == stage.tool_surface_fingerprint and REQUEST.transport_mode == "OFFLINE_FAKE_WIRE"
    for bad, code in ((dict(model_label="offline-injected-model"), "ROUTE_MODEL_MISMATCH"),):
        other = fb.cycle_request(surface_report=RECORDED_REPORT, candidate_menu=MENU, information_cutoff_ns=T0,
                                 issued_at_ns=T0, deadline_ns=T0 + 60_000_000_000, **bad)
        with pytest.raises(ValueError, match=code):
            rp.build_real01_request(other, model_input=REQUEST.model_input)
    for model_input, code in ((REQUEST.model_input + b" ", "MODEL_INPUT_MISMATCH"), (b"", "MODEL_INPUT_SIZE_INVALID"),
                              (b"x" * (rp.MAX_MODEL_INPUT_BYTES + 1), "MODEL_INPUT_SIZE_INVALID")):
        with pytest.raises(ValueError, match=code):
            rp.build_real01_request(stage, model_input=model_input)
    with pytest.raises(ValueError, match="STAGE_B_REQUEST_UNBOUND"):
        rp.build_real01_request(dataclasses.replace(stage, transport_mode="REAL_PROVIDER"), model_input=REQUEST.model_input)
    # Pure verdict: every tool leak, foreign endpoint, egress, retry or input change blocks.
    assert rp.verify_offline_wire(REQUEST, recorded())["status"] == rp.WIRE_CHECKED
    keys = sent()["body_keys"]
    for path, value, code in (
        ("results.0.requests.0.tools_count", 1, "WIRE_TOOLS_PRESENT"),
        ("results.0.requests.0.tool_choice_present", True, "WIRE_TOOLS_PRESENT"),
        ("results.0.requests.0.body_keys", sorted(keys + ["tools"]), "WIRE_TOOLS_PRESENT"),
        ("results.0.requests.0.body_keys", sorted(keys + ["parallel_tool_calls"]), "WIRE_TOOLS_PRESENT"),
        ("results.0.requests.0.body_keys", sorted(keys + ["max_tool_calls"]), "UNEXPECTED_REQUEST_FIELD"),
        ("results.0.requests.0.include", ["web_search_call.action.sources"], "UNEXPECTED_REQUEST_FIELD"),
        ("results.0.requests.0.host", "api.openai.com", "UNEXPECTED_ENDPOINT"),
        ("results.0.requests.0.path", "/v1/responses", "UNEXPECTED_ENDPOINT"),
        ("results.0.requests.0.port", 8443, "UNEXPECTED_ENDPOINT"),
        ("results.0.requests.0.method", "GET", "UNEXPECTED_ENDPOINT"),
        ("results.0.requests.0.model", "gpt-other", "WIRE_MODEL_OR_MODE_MISMATCH"),
        ("results.0.requests.0.stream", False, "WIRE_MODEL_OR_MODE_MISMATCH"),
        ("results.0.requests.0.input_sha256", "0" * 64, "WIRE_INPUT_MISMATCH"),
        ("results.0.requests.0.instructions_sha256", "0" * 64, "WIRE_INPUT_MISMATCH"),
        ("results.0.requests.0.authorization_present", False, "WIRE_AUTH_SHAPE_INVALID"),
        ("results.0.requests.0.retry_count_header", "1", "SDK_RETRY_ENABLED"),
        ("results.0.sdk_max_retries", 2, "SDK_RETRY_ENABLED"),
        ("network_attempts", [["chatgpt.com", 443]], "UNEXPECTED_NETWORK_ATTEMPT"),
        ("control_network_attempts", [["api.example.com", 443]], "UNEXPECTED_NETWORK_ATTEMPT"),
        ("control_tools_count", 0, "NEGATIVE_CONTROL_NOT_OBSERVED"),
        ("hermes_version", "0.21.4", "PIN_MISMATCH"),
        ("hermes_commit", "0" * 40, "PIN_MISMATCH"),
        ("schema", "auto02-native-tool-surface-v1", "WIRE_REPORT_INVALID"),
    ):
        verdict = rp.verify_offline_wire(REQUEST, recorded(**{path: value}))
        assert verdict["status"] == rp.WIRE_BLOCKED and verdict["reason_code"] == code, (path, verdict)
    for report in (None, {}, dict(recorded(), results=[])):
        assert rp.verify_offline_wire(REQUEST, report)["reason_code"] == "WIRE_REPORT_INVALID"
    # Pre-SDK or partial captures never claim final-wire proof.
    assert rp.verify_offline_wire(REQUEST, recorded(requests=[]))["wire_stage"] == "NOT_CAPTURED"
    # Source: one direct SDK call, never the retrying native stream helper or the conversation loop.
    for forbidden in ("run_conversation", "run_codex_stream", "auth.json", "load_dotenv", "--toolsets"):
        assert forbidden not in rp._WIRE_SOURCE
    assert "httpx.MockTransport(handler)" in rp._WIRE_SOURCE and 'api_key="offline-wire-placeholder"' in rp._WIRE_SOURCE
    (tmp_path / ".git").mkdir()
    (tmp_path / ".env").write_bytes(b"PLACEHOLDER=1")
    with pytest.raises(ValueError, match="PIN_DOTENV_PRESENT"):
        rp.capture_offline_wire(tmp_path, REQUEST, [SCENARIOS["no_trade"][0]], python_executable=tmp_path / "missing")
    script = '''import sys
import src.research_runtime.hermes_controlled_runtime
def guard(name, args):
    if name.startswith(("socket.", "subprocess.Popen", "sqlite3.connect", "os.system", "os.putenv")): raise RuntimeError(name)
sys.addaudithook(guard)
import src.research_runtime.hermes_controlled_runtime.real_provider_stage_b
print("IMPORT_NO_IO_PASS")
'''
    imported = subprocess.run([sys.executable, "-B", "-c", script], cwd=ROOT, capture_output=True, text=True)
    assert imported.returncode == 0 and "IMPORT_NO_IO_PASS" in imported.stdout, imported.stderr
    require_pin(native_report)
    # Native exact pin: post-SDK body captured, no tools, approved endpoint, zero sockets.
    assert native_report["hermes_commit"] == tf.PINNED_HERMES_COMMIT and native_report["network_attempts"] == []
    assert native_report["control_tools_count"] >= 1  # same capture sees the default tool universe
    verdict = rp.verify_offline_wire(REQUEST, single(native_report, "no_trade"))
    assert verdict["status"] == rp.WIRE_CHECKED and verdict["wire_stage"] == "POST_SDK_HTTP_CAPTURED", verdict
    body = single(native_report, "no_trade")["results"][0]["requests"][0]
    assert body["tools_count"] == 0 and not body["tool_choice_present"] and body["retry_count_header"] == "0"
    assert set(body["body_keys"]) <= rp._BODY_ALLOWED and body["host"] == "chatgpt.com"


def patched_capture(monkeypatch, outcome):
    calls = []
    def fake(pin_root, request, scenarios, **kwargs):
        calls.append(len(scenarios))
        if isinstance(outcome, BaseException):
            raise outcome
        return copy.deepcopy(outcome)
    monkeypatch.setattr(rp, "capture_offline_wire", fake)
    return calls


def clock():
    ticks = iter(range(T0 + 1, T0 + 1000))
    return lambda: next(ticks)


def test_real01_one_request_reservation_and_no_retry_on_failure(native_report, tmp_path, monkeypatch):
    # Journal: reserve before dispatch, one terminal, replay never redispatches.
    for index, (outcome, status) in enumerate((
            (recorded(), rp.VALID_OUTPUT), (recorded(**{"results.0.http_status": 429,
             "results.0.error_class": "RateLimitError", "results.0.final": None}), "PROVIDER_RATE_LIMITED"),
            (recorded(**{"results.0.http_status": 503, "results.0.final": None}), "PROVIDER_SERVER_ERROR"),
            (subprocess.TimeoutExpired("child", 1), "ATTEMPT_TIMEOUT_CONSUMED"),
            (RuntimeError("child crashed"), "ATTEMPT_TRANSPORT_FAILED_CONSUMED"))):
        calls = patched_capture(monkeypatch, outcome)
        transport = rp.OfflineCodexWireTransport(PIN_ROOT, SCENARIOS["no_trade"][0])
        journal = tmp_path / f"journal{index}"
        first = rp.run_real01_attempt(REQUEST, transport=transport, journal_dir=journal, clock_ns=clock())
        assert first.status == status and calls == [1] and transport.dispatch_count == 1, (status, first)
        assert first.origin["application_retries"] == 0 and first.origin["fallback_used"] is False
        assert (first.output_bytes is not None) == (status == rp.VALID_OUTPUT)
        for _ in range(2):
            again = rp.run_real01_attempt(REQUEST, transport=transport, journal_dir=journal, clock_ns=clock())
            assert again.replayed and again.status == status and again.origin == first.origin
            assert again.output_bytes is None and transport.dispatch_count == 1 and calls == [1]
        assert sorted(p.suffix for p in journal.iterdir()) == [".json", ".reserved"]
    calls = patched_capture(monkeypatch, recorded())
    transport = rp.OfflineCodexWireTransport(PIN_ROOT, SCENARIOS["no_trade"][0])
    stem = "real01-" + REQUEST.request_id.rsplit(":", 1)[1]
    # Interrupted earlier attempt (reservation, no terminal): consumed, blocked, no dispatch.
    (tmp_path / "interrupted").mkdir()
    (tmp_path / "interrupted" / (stem + ".reserved")).write_bytes(b"x")
    blocked = rp.run_real01_attempt(REQUEST, transport=transport, journal_dir=tmp_path / "interrupted", clock_ns=clock())
    assert blocked.status == "ATTEMPT_ALREADY_RESERVED" and transport.dispatch_count == 0
    # Tampered terminal: never trusted, never redispatched.
    (tmp_path / "tampered").mkdir()
    (tmp_path / "tampered" / (stem + ".json")).write_text(json.dumps(dict(status=rp.VALID_OUTPUT)))
    assert rp.run_real01_attempt(REQUEST, transport=transport, journal_dir=tmp_path / "tampered",
                                 clock_ns=clock()).status == "JOURNAL_INVALID"
    # Expired deadline: nothing reserved or sent.
    late = rp.run_real01_attempt(REQUEST, transport=transport, journal_dir=tmp_path / "late",
                                 clock_ns=lambda: REQUEST.deadline_ns)
    assert late.status == "DEADLINE_EXCEEDED_NOT_DISPATCHED" and not (tmp_path / "late").exists()
    # Forged identity or substituted transport: rejected before reservation.
    class Sub(rp.OfflineCodexWireTransport):
        pass
    for request, carrier in ((dataclasses.replace(REQUEST, deadline_ns=REQUEST.deadline_ns + 1), transport),
                             (dataclasses.replace(REQUEST, transport_mode="REAL_PROVIDER"), transport),
                             (dataclasses.replace(REQUEST, model_input=b"{}"), transport),
                             (REQUEST, Sub(PIN_ROOT, {}))):
        assert rp.run_real01_attempt(request, transport=carrier, journal_dir=tmp_path / "forged",
                                     clock_ns=clock()).status == "REQUEST_OR_TRANSPORT_INVALID"
    assert transport.dispatch_count == 0 and calls == [] and not (tmp_path / "forged").exists()
    # Concurrent callers: exactly one dispatch; the other is blocked while the first is in flight.
    release, entered, outcomes = threading.Event(), threading.Event(), []
    def slow(*args, **kwargs):
        entered.set()
        assert release.wait(30)
        return recorded()
    monkeypatch.setattr(rp, "capture_offline_wire", slow)
    racing = rp.OfflineCodexWireTransport(PIN_ROOT, SCENARIOS["no_trade"][0])
    worker = threading.Thread(target=lambda: outcomes.append(rp.run_real01_attempt(
        REQUEST, transport=racing, journal_dir=tmp_path / "race", clock_ns=clock())))
    worker.start()
    assert entered.wait(30)
    second = rp.run_real01_attempt(REQUEST, transport=racing, journal_dir=tmp_path / "race", clock_ns=clock())
    release.set()
    worker.join(30)
    assert second.status == "ATTEMPT_ALREADY_RESERVED" and outcomes[0].status == rp.VALID_OUTPUT
    assert racing.dispatch_count == 1
    require_pin(native_report)
    # Native: every failure class produced exactly one fake generation POST (SDK retries 0,
    # no native stream retry, no conversation recovery).
    for name in SCENARIOS:
        result = native_report["results"][list(SCENARIOS).index(name)]
        assert len(result["requests"]) == 1 and result["sdk_max_retries"] == 0, name
    # Native production path: one pinned child, one fake POST, then replay with zero spawns.
    monkeypatch.undo()
    native = rp.OfflineCodexWireTransport(PIN_ROOT, SCENARIOS["no_trade"][0])
    done = rp.run_real01_attempt(REQUEST, transport=native, journal_dir=tmp_path / "native", clock_ns=clock())
    assert done.status == rp.VALID_OUTPUT and done.origin["generation_requests"] == 1, done
    assert done.origin["wire_stage"] == "POST_SDK_HTTP_CAPTURED" and done.origin["sdk_max_retries"] == 0
    assert rp.run_real01_attempt(REQUEST, transport=native, journal_dir=tmp_path / "native", clock_ns=clock()).replayed
    assert native.dispatch_count == 1


def test_real01_origin_labels_fail_closed_without_server_model_attestation(native_report, tmp_path, monkeypatch):
    patched_capture(monkeypatch, recorded())
    result = rp.run_real01_attempt(REQUEST, transport=rp.OfflineCodexWireTransport(PIN_ROOT, {}),
                                   journal_dir=tmp_path, clock_ns=clock())
    record = result.origin
    # A matching fixture server model, provider id and usage are still not identity proof.
    assert result.status == rp.VALID_OUTPUT and record["server_model_observed"] == MODEL
    assert record["model_identity"] == "MODEL_IDENTITY_UNVERIFIED" and record["proof_class"] == "OFFLINE_WIRE_SIMULATED"
    assert record["provider_invocation"] == "PROVIDER_NOT_INVOKED" and record["model_origin_proof"] == "MODEL_ORIGIN_UNVERIFIED"
    assert record["real_origin"] == "REAL_ORIGIN_UNVERIFIED" and record["server_identity_source"] == "FIXTURE_UNTRUSTED"
    assert record["assembler_model_is_request_echo"] is True and record["response_id_origin"] == "FIXTURE_UNTRUSTED"
    assert record["usage_status"] == "USAGE_REPORTED_UNTRUSTED" and record["cost_status"] == "COST_UNKNOWN"
    assert record["price_source"] == "UNVERIFIED" and record["raw_output_sha256"] == hashlib.sha256(NO_TRADE.encode()).hexdigest()
    body = {k: v for k, v in record.items() if k != "record_id"}
    assert record["record_id"] == rp.RECORD_ID_PREFIX + tf._digest(body)
    public = json.dumps(record)
    for secret in ("NO_TRADE", REQUEST.model_input.decode(), rp.INSTRUCTIONS[:40], "offline-wire-placeholder",
                   "resp_offline_fixture", str(tmp_path), "authorization"):
        assert secret not in public
    # Absent usage stays UNKNOWN (never zero); absent server model stays unverified, not mismatch.
    status, facts, _ = classify(recorded(**{"results.0.final.usage": None, "results.0.server_model": None}))
    assert status == rp.VALID_OUTPUT and facts["usage"] is None and facts["server_model"] is None
    zero = rp._origin_record(REQUEST, status, facts, b"{}", T0 + 1, T0 + 2)
    assert zero["usage_status"] == "USAGE_UNKNOWN" and zero["cost_status"] == "COST_UNKNOWN"
    assert zero["model_identity"] == "MODEL_IDENTITY_UNVERIFIED"
    assert classify(recorded(**{"results.0.server_model": "gpt-other"}))[0] == "MODEL_MISMATCH"
    assert classify(recorded(**{"results.0.final.usage": dict(input_tokens=-1, output_tokens=0, total_tokens=0)}))[1]["usage"] is None
    # Relabelled, re-digested or forged real claims never admit through the AUTO-01 seam.
    forged = dict(record, proof_class="REAL_PROVIDER_VERIFIED", model_identity="MODEL_IDENTITY_VERIFIED",
                  provider_invocation="REAL_PROVIDER_OBSERVED", real_origin="REAL_ORIGIN_VERIFIED",
                  server_identity_source="SERVER_ATTESTED")
    forged["record_id"] = rp.RECORD_ID_PREFIX + tf._digest({k: v for k, v in forged.items() if k != "record_id"})
    for evidence in (record, forged, result, {}, "REAL_PROVIDER_VERIFIED", None):
        with pytest.raises(fb.FeedbackRejected, match="REAL_ORIGIN_UNVERIFIED"):
            fb.verify_real_origin_evidence(evidence)
    assert not hasattr(rp, "REAL_PROVIDER_VERIFIED")
    require_pin(native_report)
    # Native: the pinned assembler echoes the REQUESTED model even when the server says otherwise.
    mismatch = single(native_report, "model_mismatch")["results"][0]
    assert mismatch["server_model"] == "gpt-other" and mismatch["final"]["assembler_model"] == MODEL
    assert classify(single(native_report, "model_mismatch"))[0] == "MODEL_MISMATCH"
    assert single(native_report, "no_usage")["results"][0]["final"]["usage"] is None


def test_real01_untrusted_response_strict_choice_and_tool_rejection(native_report):
    # NO_TRADE and TRADE are both valid offline classifications; neither carries real authority.
    assert classify(recorded())[0] == classify(recorded(text=TRADE))[0] == rp.VALID_OUTPUT
    for path, value, code in (
        ("results.0.final.output_types", ["function_call"], "TOOL_CALL_ATTEMPT_INVALID"),
        ("results.0.final.output_types", ["web_search_call", "message"], "TOOL_CALL_ATTEMPT_INVALID"),
        ("results.0.final.output_types", ["message", "message"], "RESPONSE_SHAPE_INVALID"),
        ("results.0.final.output_types", [], "RESPONSE_SHAPE_INVALID"),
        ("results.0.terminal_events", ["response.incomplete"], "RESPONSE_INCOMPLETE"),
        ("results.0.terminal_events", [], "RESPONSE_INCOMPLETE"),
        ("results.0.final.status", "incomplete", "RESPONSE_INCOMPLETE"),
        ("results.0.final.output_text", "x" * (tf.MAX_OUTPUT_BYTES + 1), "OUTPUT_SIZE_INVALID"),
        ("results.0.final.output_text", "", "OUTPUT_SIZE_INVALID"),
        ("results.0.final.output_text", '{"action":NaN}', "OUTPUT_JSON_INVALID"),
        ("results.0.final.output_text", "[]", "OUTPUT_JSON_INVALID"),
        ("results.0.final.output_text", "NO_TRADE", "OUTPUT_JSON_INVALID"),
        ("results.0.final.usage", dict(input_tokens=1, output_tokens=tf.MAX_OUTPUT_BYTES + 1, total_tokens=1),
         "USAGE_CAP_EXCEEDED"),
        ("results.0.http_status", 400, "PROVIDER_HTTP_ERROR"),
        ("results.0.error_class", "RuntimeError", "RESPONSE_INCOMPLETE"),
        ("results.0.error_class", "APITimeoutError", "PROVIDER_TIMEOUT"),
        ("results.0.final", None, "TRANSPORT_OR_STREAM_ERROR"),
    ):
        status, _, raw = classify(recorded(**{path: value}))
        assert status == code and raw is None, (path, status)
    assert classify(recorded(), finished=REQUEST.deadline_ns + 1)[0] == "DEADLINE_EXCEEDED"
    require_pin(native_report)
    # Native: the real pinned SSE consumer + this classifier over every offline scenario.
    for name, (_, expected) in SCENARIOS.items():
        status, _, raw = classify(single(native_report, name))
        assert status == expected, (name, status)
        assert (raw is not None) == (expected == rp.VALID_OUTPUT)
    assert classify(single(native_report, "no_trade"))[2] == NO_TRADE.encode()
