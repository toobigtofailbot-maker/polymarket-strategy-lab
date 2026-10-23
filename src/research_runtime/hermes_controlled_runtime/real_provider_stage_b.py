"""Dormant single-request Hermes Codex Responses wire seam (S10-HERMES-AUTO-02-REAL-01).

Offline only. The one route under study is ``ROUTE`` (pinned Hermes ``openai-codex`` /
``codex_responses``); it is the single replaceable seam, not a provider framework.
``capture_offline_wire`` runs the exact pinned Hermes in an isolated child (empty sterile
home, stripped environment, sockets denied) and sends the native request through the
pinned OpenAI SDK into an in-memory ``httpx.MockTransport``: the captured POST is the
effective body AFTER SDK transformation. Nothing is sent to a provider and no credential
is read; the bearer is a placeholder.

The native ``run_codex_stream`` retries transport errors and ``run_conversation`` recovers
tool calls, so neither is used: the child makes one ``responses.create(stream=True)`` call
(SDK ``max_retries=0``) and assembles it with the native event consumer. A sterile
``config.yaml`` pins ``model.context_length`` so AIAgent init skips the authenticated
``/models`` catalogue probe; any socket attempt at all blocks the wire verdict.

Every result here is ``OFFLINE_WIRE_SIMULATED`` / ``MODEL_IDENTITY_UNVERIFIED``: fixture
server fields (model, response id, usage) are untrusted, and the native assembler's
``.model`` echoes the requested model. No code path in this module can mark a real origin.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
from pathlib import Path
import subprocess

from src.strategy_lifecycle.models import strict_json_loads

from . import tool_free_stage_b as stage_b

# The single provider seam. A different route needs a new approval, not a new framework.
ROUTE = dict(provider="openai-codex", api_mode="codex_responses",
             base_url="https://chatgpt.com/backend-api/codex", model="gpt-5.6-sol")
ENDPOINT_HOST = "chatgpt.com"
ENDPOINT_PATH = "/backend-api/codex/responses"
ROUTE_CONTEXT_LENGTH = 272_000
TRANSPORT_OFFLINE_FAKE_WIRE = "OFFLINE_FAKE_WIRE"
PROOF_CLASS = "OFFLINE_WIRE_SIMULATED"
PROVIDER_NOT_INVOKED = "PROVIDER_NOT_INVOKED"
MODEL_IDENTITY_UNVERIFIED = "MODEL_IDENTITY_UNVERIFIED"
MODEL_ORIGIN_UNVERIFIED = "MODEL_ORIGIN_UNVERIFIED"
REAL_ORIGIN_UNVERIFIED = "REAL_ORIGIN_UNVERIFIED"
FIXTURE_UNTRUSTED = "FIXTURE_UNTRUSTED"
WIRE_CHECKED = "OFFLINE_WIRE_COMPATIBILITY_CHECKED"
WIRE_BLOCKED = "OFFLINE_WIRE_COMPATIBILITY_BLOCKED"
VALID_OUTPUT = stage_b.VALID_OUTPUT
MAX_MODEL_INPUT_BYTES = stage_b.MAX_OUTPUT_BYTES
REQUEST_ID_PREFIX = "real01:sha256:"
RECORD_ID_PREFIX = "real01origin:sha256:"
INSTRUCTIONS = (
    "You are the Stage B opportunity chooser. The user message is a JSON object with an ordered candidate "
    "menu and information_cutoff_ns. Reply with exactly one strict JSON object and nothing else: action is "
    "NO_TRADE, PAUSE, REASSESS or TRADE; proof_level, information_cutoff_ns, produced_at_ns and expires_at_ns "
    "are always present; TRADE also names one menu candidate and the full order shape. NO_TRADE is valid. "
    "You have no tools.")
_WIRE_SCHEMA = "real01-offline-codex-wire-v1"
_BODY_REQUIRED = {"input", "instructions", "model", "stream"}
_BODY_ALLOWED = _BODY_REQUIRED | {"include", "prompt_cache_key", "reasoning", "store"}
_INCLUDE_ALLOWED = {"reasoning.encrypted_content"}
_TERMINAL_COMPLETED = ["response.completed"]
# The default-tools positive control's vision check looks up models.dev; denied pre-DNS. The
# explicit-empty dispatch agent must make no socket attempt at all.
_CONTROL_DENIED_TARGET = ("models.dev", 443)

# Executed ONLY inside the pinned Hermes virtualenv child (``python -I -B -c``); spec on stdin.
_WIRE_SOURCE = stage_b._OFFLINE_PROCESS_GUARD + r'''
import hashlib, json, os, socket, sys
attempts = []
def _record(host, port):
    attempts.append([str(host)[:64], port if type(port) is int else str(port)[:16]])
    raise OSError("offline wire: network denied")
def _connect(self, address, *a, **k):
    _record(*(tuple(address)[:2] if isinstance(address, tuple) else (address, None)))
socket.socket.connect = _connect
socket.socket.connect_ex = _connect
socket.create_connection = lambda address, *a, **k: _record(*tuple(address)[:2])
socket.getaddrinfo = lambda host, port, *a, **k: _record(host, port)
sys.path.insert(0, os.getcwd())
spec = json.loads(sys.stdin.buffer.read())
import httpx, hermes_cli
from run_agent import AIAgent
from agent.chat_completion_helpers import build_api_kwargs
from agent import codex_runtime as cr
route = spec["route"]
messages = [{"role": "system", "content": spec["instructions"]}, {"role": "user", "content": spec["model_input"]}]
def sha(data):
    return hashlib.sha256(data).hexdigest()
def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
def agent_for(enabled):
    kw = dict(base_url=route["base_url"], api_key="offline-wire-placeholder", provider=route["provider"],
              api_mode=route["api_mode"], model=route["model"], quiet_mode=True, skip_context_files=True,
              skip_memory=True, skip_background_review=True, max_iterations=1)
    if enabled is not None:
        kw["enabled_toolsets"] = enabled
    return AIAgent(**kw)
def send(agent, scenario):
    seen = []
    def handler(request):
        body = request.content
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = None
        p = parsed if isinstance(parsed, dict) else {}
        seen.append(dict(method=request.method, scheme=request.url.scheme, host=request.url.host,
            port=request.url.port, path=request.url.path, body_sha256=sha(body), body_bytes=len(body),
            body_keys=sorted(p) if parsed is p else None, model=p.get("model"), stream=p.get("stream"),
            store=p.get("store"), include=p.get("include"), tools_count=len(p.get("tools") or []),
            tool_choice_present="tool_choice" in p,
            instructions_sha256=sha(p["instructions"].encode("utf-8")) if isinstance(p.get("instructions"), str) else None,
            input_sha256=sha(canon(p.get("input"))), authorization_present="authorization" in request.headers,
            retry_count_header=request.headers.get("x-stainless-retry-count")))
        if scenario["kind"] == "raise":
            raise getattr(httpx, scenario["error"])("offline fake transport error", request=request)
        if scenario["kind"] == "http":
            return httpx.Response(scenario["status"], json={"error": {"message": "offline fake"}})
        data = "".join("event: %s\ndata: %s\n\n" % (e.get("type", ""), json.dumps(e)) for e in scenario["events"])
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=data.encode("utf-8"))
    client = agent._create_openai_client(
        dict(agent._client_kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler))),
        reason="real01_offline_wire", shared=False)
    out = dict(requests=seen, sdk_max_retries=client.max_retries, http_status=None, error_class=None,
               terminal_events=[], server_model=None, final=None)
    def on_event(event):
        kind = getattr(event, "type", "")
        if kind in ("response.completed", "response.incomplete", "response.failed"):
            out["terminal_events"].append(kind)
            model = getattr(getattr(event, "response", None), "model", None)
            out["server_model"] = model[:128] if isinstance(model, str) else None
    try:
        kwargs = build_api_kwargs(agent, messages)
        wire = cr._sanitize_consumer_codex_request(agent, kwargs)
        wire["stream"] = True
        wire["timeout"] = spec["timeout_s"]
        stream = client.responses.create(**cr._bypass_sdk_request_transform(wire))
        final = cr._consume_codex_event_stream(stream, model=kwargs.get("model"), on_event=on_event)
        usage = getattr(final, "usage", None)
        out["final"] = dict(status=final.status, assembler_model=final.model,
            output_types=[str(getattr(item, "type", ""))[:64] for item in final.output],
            output_text=final.output_text,
            response_id_sha256=sha(final.id.encode("utf-8")) if isinstance(final.id, str) else None,
            usage=None if usage is None else {k: getattr(usage, k, None) for k in ("input_tokens", "output_tokens", "total_tokens")})
    except Exception as exc:
        out["error_class"] = type(exc).__name__.lstrip("_")[:64]
        status = getattr(exc, "status_code", None)
        out["http_status"] = status if type(status) is int else None
    finally:
        client.close()
    return out
results = [send(agent_for([]), scenario) for scenario in spec["scenarios"]]
dispatch_attempts = list(attempts)
# Positive control only (default tool universe; its vision check may try models.dev, denied above).
control = send(agent_for(None), spec["scenarios"][0])["requests"]
print(json.dumps(dict(schema="real01-offline-codex-wire-v1", hermes_version=hermes_cli.__version__,
    results=results, control_tools_count=control[0]["tools_count"] if control else 0,
    network_attempts=dispatch_attempts, control_network_attempts=attempts[len(dispatch_attempts):]),
    sort_keys=True))
'''


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canon_input(text: str) -> bytes:
    # Same separators the child uses for the captured ``input`` field.
    return json.dumps([{"role": "user", "content": text}], sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def real01_model_input(candidate_menu, information_cutoff_ns) -> bytes:
    """The exact user bytes whose digest AUTO-02 ``cycle_request`` binds as ``model_input_sha256``."""
    return stage_b._canonical(dict(menu=[dict(item) for item in candidate_menu],
                                   information_cutoff_ns=information_cutoff_ns))


@dataclass(frozen=True)
class Real01Request:
    """Immutable one-attempt identity over a verified AUTO-02 Stage B request."""
    request_id: str
    stage_b_request_id: str
    provider: str
    api_mode: str
    base_url: str
    model: str
    instructions_sha256: str
    model_input_sha256: str
    issued_at_ns: int
    deadline_ns: int
    hermes_commit: str
    tool_surface_fingerprint: str
    runtime_profile_sha256: str
    transport_mode: str = TRANSPORT_OFFLINE_FAKE_WIRE
    model_input: bytes = field(default=b"", repr=False)


def _preimage(request: Real01Request) -> dict:
    return {k: v for k, v in request.__dict__.items() if k not in ("request_id", "model_input")}


def build_real01_request(stage_b_request: object, *, model_input: object) -> Real01Request:
    """Raises ValueError(code). Reuses the AUTO-02 pin, tool-surface fingerprint and clocks."""
    if not stage_b.request_is_bound(stage_b_request):
        raise ValueError("STAGE_B_REQUEST_UNBOUND")
    if type(model_input) is not bytes or not 0 < len(model_input) <= MAX_MODEL_INPUT_BYTES:
        raise ValueError("MODEL_INPUT_SIZE_INVALID")
    if _sha(model_input) != stage_b_request.model_input_sha256:
        raise ValueError("MODEL_INPUT_MISMATCH")
    if stage_b_request.model_label != ROUTE["model"]:
        raise ValueError("ROUTE_MODEL_MISMATCH")
    draft = Real01Request("", stage_b_request.request_id, ROUTE["provider"], ROUTE["api_mode"], ROUTE["base_url"],
                          ROUTE["model"], _sha(INSTRUCTIONS.encode("utf-8")), stage_b_request.model_input_sha256,
                          stage_b_request.issued_at_ns, stage_b_request.deadline_ns, stage_b_request.hermes_commit,
                          stage_b_request.tool_surface_fingerprint, stage_b_request.runtime_profile_sha256, model_input=model_input)
    return replace(draft, request_id=REQUEST_ID_PREFIX + stage_b._digest(_preimage(draft)))


def request_is_bound(request: object) -> bool:
    return (type(request) is Real01Request and request.transport_mode == TRANSPORT_OFFLINE_FAKE_WIRE and
            (request.provider, request.api_mode, request.base_url, request.model) == tuple(ROUTE.values()) and
            request.hermes_commit == stage_b.PINNED_HERMES_COMMIT and
            stage_b.profile_digest_is_approved(request.runtime_profile_sha256) and type(request.model_input) is bytes and
            _sha(request.model_input) == request.model_input_sha256 and
            request.instructions_sha256 == _sha(INSTRUCTIONS.encode("utf-8")) and
            request.request_id == REQUEST_ID_PREFIX + stage_b._digest(_preimage(request)))


def capture_offline_wire(pin_root: object, request: Real01Request, scenarios: list, *,
                         python_executable: object = None, timeout_s: float = 120) -> dict:
    """Run the pinned child once over offline fake ``scenarios``; returns the raw report.

    Reads only the pin's ``.git/HEAD`` (and refuses a pin-local ``.env``). Subprocess
    timeouts propagate to the caller, which treats them as a consumed attempt.
    """
    import os
    import tempfile
    root = Path(pin_root).absolute()
    if (root / ".env").exists():  # pinned run_agent loads it at import
        raise ValueError("PIN_DOTENV_PRESENT")
    head = (root / ".git" / "HEAD").read_text(encoding="ascii").strip()
    exe = Path(python_executable) if python_executable is not None else (
        root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    profile = stage_b.verify_runtime_profile(root, python_executable=exe)
    if profile != request.runtime_profile_sha256:
        raise ValueError("PROFILE_MISMATCH")
    spec = dict(route=ROUTE, instructions=INSTRUCTIONS, model_input=request.model_input.decode("utf-8"),
                scenarios=scenarios, timeout_s=timeout_s)
    with tempfile.TemporaryDirectory(prefix="real01-hermes-home-") as home:
        # Sterile route config: a known context window skips the authenticated /models init probe.
        Path(home, "config.yaml").write_text(
            "model:\n  provider: {provider}\n  default: {model}\n  base_url: {base_url}\n".format(**ROUTE)
            + f"  context_length: {ROUTE_CONTEXT_LENGTH}\nsecurity:\n  allow_lazy_installs: false\n", encoding="utf-8")
        env = {key: home for key in ("HERMES_HOME", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP")}
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", PATH=str(exe.parent), NO_COLOR="1", HERMES_DISABLE_LAZY_INSTALLS="1")
        if "SYSTEMROOT" in os.environ:
            env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
        completed = subprocess.run([str(exe), "-I", "-B", "-c", _WIRE_SOURCE], cwd=root, env=env,
                                   input=json.dumps(spec).encode("utf-8"), capture_output=True,
                                   timeout=timeout_s, check=False)
    if stage_b.verify_runtime_profile(root, python_executable=exe) != profile:
        raise ValueError("PROFILE_MISMATCH")
    lines = completed.stdout.decode("utf-8", "replace").strip().splitlines()
    report = json.loads(lines[-1]) if completed.returncode == 0 and lines else {}
    if type(report) is dict and report:
        report["hermes_commit"] = head
        report["runtime_profile_sha256"] = profile
    return report


class OfflineCodexWireTransport:
    """Trusted offline transport: one pinned child per dispatch, one fake scenario, no callables."""

    def __init__(self, pin_root: object, scenario: dict, *, python_executable: object = None,
                 timeout_s: float = 120) -> None:
        self._pin_root, self._python, self._timeout_s = pin_root, python_executable, timeout_s
        self._scenario = json.loads(json.dumps(scenario))
        self.dispatch_count = 0

    def _send(self, request: Real01Request, timeout_s: float) -> dict:
        self.dispatch_count += 1
        return capture_offline_wire(self._pin_root, request, [self._scenario], python_executable=self._python,
                                    timeout_s=min(timeout_s, self._timeout_s))


def verify_offline_wire(request: Real01Request, report: object) -> dict:
    """Pure verdict over one single-scenario report: post-SDK body, endpoint, tools, egress, retries."""
    def verdict(code: str | None, sent: dict | None = None) -> dict:
        return dict(status=WIRE_BLOCKED if code else WIRE_CHECKED, reason_code=code,
                    wire_stage="POST_SDK_HTTP_CAPTURED" if sent else "NOT_CAPTURED",
                    body_sha256=sent["body_sha256"] if sent else None, body_bytes=sent["body_bytes"] if sent else None)
    if type(report) is not dict or report.get("schema") != _WIRE_SCHEMA or type(report.get("results")) is not list \
            or len(report["results"]) != 1 or type(report["results"][0]) is not dict:
        return verdict("WIRE_REPORT_INVALID")
    if report.get("hermes_version") != stage_b.PINNED_HERMES_SEMVER or report.get("hermes_commit") != stage_b.PINNED_HERMES_COMMIT:
        return verdict("PIN_MISMATCH")
    if not stage_b.profile_digest_is_approved(report.get("runtime_profile_sha256")) or report.get("runtime_profile_sha256") != request.runtime_profile_sha256:
        return verdict("PROFILE_MISMATCH")
    control_attempts = report.get("control_network_attempts")
    if report.get("network_attempts") != [] or type(control_attempts) is not list or \
            any(a != list(_CONTROL_DENIED_TARGET) for a in control_attempts):
        return verdict("UNEXPECTED_NETWORK_ATTEMPT")
    if type(report.get("control_tools_count")) is not int or report["control_tools_count"] < 1:
        return verdict("NEGATIVE_CONTROL_NOT_OBSERVED")  # the capture must see tools when they exist
    result = report["results"][0]
    sent_list = result.get("requests")
    if type(sent_list) is not list or not sent_list:
        return verdict("NOT_DISPATCHED")
    if len(sent_list) != 1:
        return verdict("MULTIPLE_DISPATCH_INVALID")
    sent = sent_list[0]
    if type(sent) is not dict:
        return verdict("WIRE_REPORT_INVALID")
    if result.get("sdk_max_retries") != 0 or sent.get("retry_count_header") != "0":
        return verdict("SDK_RETRY_ENABLED", sent)
    if (sent.get("method"), sent.get("scheme"), sent.get("host"), sent.get("port"), sent.get("path")) != \
            ("POST", "https", ENDPOINT_HOST, None, ENDPOINT_PATH):
        return verdict("UNEXPECTED_ENDPOINT", sent)
    keys = sent.get("body_keys")
    if type(keys) is not list or sent.get("tools_count") != 0 or sent.get("tool_choice_present") is not False \
            or {"tools", "tool_choice", "parallel_tool_calls"} & set(keys):
        return verdict("WIRE_TOOLS_PRESENT", sent)
    include = sent.get("include")
    if not _BODY_REQUIRED <= set(keys) <= _BODY_ALLOWED or not (
            include is None or (type(include) is list and set(include) <= _INCLUDE_ALLOWED)):
        return verdict("UNEXPECTED_REQUEST_FIELD", sent)
    if sent.get("model") != request.model or sent.get("stream") is not True or sent.get("store") not in (None, False):
        return verdict("WIRE_MODEL_OR_MODE_MISMATCH", sent)
    if sent.get("instructions_sha256") != request.instructions_sha256 or \
            sent.get("input_sha256") != _sha(_canon_input(request.model_input.decode("utf-8"))):
        return verdict("WIRE_INPUT_MISMATCH", sent)
    if sent.get("authorization_present") is not True:
        return verdict("WIRE_AUTH_SHAPE_INVALID", sent)
    return verdict(None, sent)


def _label(value: object) -> str | None:
    if value is None:
        return None
    return value if type(value) is str and stage_b._LABEL.fullmatch(value) else "INVALID_LABEL"


def classify_wire_report(request: Real01Request, report: object, *, dispatched_at_ns: int,
                         finished_at_ns: int) -> tuple[str, dict, bytes | None]:
    """Pure: (terminal status, sanitized facts, accepted output bytes). Never retries."""
    wire = verify_offline_wire(request, report)
    results = report.get("results") if type(report) is dict else None
    result = results[0] if type(results) is list and len(results) == 1 and type(results[0]) is dict else {}
    final = result.get("final") if type(result.get("final")) is dict else None
    usage = final.get("usage") if final else None
    usage = usage if type(usage) is dict and all(type(usage.get(k)) is int and usage[k] >= 0
                                                 for k in ("input_tokens", "output_tokens", "total_tokens")) else None
    facts = dict(wire=wire, generation_requests=len(result["requests"]) if type(result.get("requests")) is list else None,
                 sdk_max_retries=result.get("sdk_max_retries") if type(result.get("sdk_max_retries")) is int else None,
                 http_status=result.get("http_status") if type(result.get("http_status")) is int else None,
                 error_class=_label(result.get("error_class")), server_model=_label(result.get("server_model")),
                 response_id_sha256=final.get("response_id_sha256") if final and type(final.get("response_id_sha256")) is str
                 and stage_b._HEX64.fullmatch(final["response_id_sha256"]) else None, usage=usage)
    if wire["status"] != WIRE_CHECKED:
        return wire["reason_code"], facts, None
    status, error = facts["http_status"], result.get("error_class")
    if status == 429:
        return "PROVIDER_RATE_LIMITED", facts, None
    if status is not None and status >= 500:
        return "PROVIDER_SERVER_ERROR", facts, None
    if status is not None:
        return "PROVIDER_HTTP_ERROR", facts, None
    if error == "APITimeoutError":
        return "PROVIDER_TIMEOUT", facts, None
    if error == "RuntimeError":  # native assembler: no terminal frame and no content
        return "RESPONSE_INCOMPLETE", facts, None
    if error is not None or final is None:
        return "TRANSPORT_OR_STREAM_ERROR", facts, None
    types = final.get("output_types")
    if type(types) is not list or any(t != "message" for t in types):
        return "TOOL_CALL_ATTEMPT_INVALID", facts, None  # function, built-in or server tool item
    if result.get("terminal_events") != _TERMINAL_COMPLETED or final.get("status") != "completed":
        return "RESPONSE_INCOMPLETE", facts, None
    if len(types) != 1:
        return "RESPONSE_SHAPE_INVALID", facts, None
    if facts["server_model"] is not None and facts["server_model"] != request.model:
        return "MODEL_MISMATCH", facts, None
    if not (request.issued_at_ns <= dispatched_at_ns <= finished_at_ns <= request.deadline_ns):
        return "DEADLINE_EXCEEDED", facts, None
    text = final.get("output_text")
    raw = text.encode("utf-8") if type(text) is str else b""
    if not 0 < len(raw) <= stage_b.MAX_OUTPUT_BYTES:
        return "OUTPUT_SIZE_INVALID", facts, None
    if usage is not None and usage["output_tokens"] > stage_b.MAX_OUTPUT_BYTES:
        return "USAGE_CAP_EXCEEDED", facts, None
    try:
        if type(strict_json_loads(text)) is not dict:
            raise ValueError
    except Exception:
        return "OUTPUT_JSON_INVALID", facts, None
    return VALID_OUTPUT, facts, raw


@dataclass(frozen=True)
class Real01Result:
    request_id: str
    status: str
    origin: dict | None
    output_bytes: bytes | None = field(default=None, repr=False)
    replayed: bool = False


def _origin_record(request: Real01Request, status: str, facts: dict, raw: bytes | None,
                   dispatched_at_ns: int, finished_at_ns: int | None) -> dict:
    wire = facts.get("wire") or {}
    record = dict(
        schema_id="hermes-real01-origin-record", request_id=request.request_id,
        stage_b_request_id=request.stage_b_request_id, hermes_commit=request.hermes_commit,
        tool_surface_fingerprint=request.tool_surface_fingerprint, runtime_profile_sha256=request.runtime_profile_sha256, provider=request.provider,
        api_mode=request.api_mode, endpoint_host=ENDPOINT_HOST, endpoint_path=ENDPOINT_PATH,
        expected_model=request.model, transport_mode=request.transport_mode, status=status,
        wire_stage=wire.get("wire_stage", "NOT_CAPTURED"), wire_status=wire.get("status"),
        wire_reason=wire.get("reason_code"), wire_body_sha256=wire.get("body_sha256"),
        wire_body_bytes=wire.get("body_bytes"), generation_requests=facts.get("generation_requests"),
        sdk_max_retries=facts.get("sdk_max_retries"), application_retries=0, fallback_used=False,
        dispatched_at_ns=dispatched_at_ns, finished_at_ns=finished_at_ns,
        http_status=facts.get("http_status"), error_class=facts.get("error_class"),
        raw_output_sha256=_sha(raw) if raw is not None else None,
        server_model_observed=facts.get("server_model"), server_identity_source=FIXTURE_UNTRUSTED,
        assembler_model_is_request_echo=True, model_identity=MODEL_IDENTITY_UNVERIFIED,
        response_id_sha256=facts.get("response_id_sha256"),
        response_id_origin=FIXTURE_UNTRUSTED if facts.get("response_id_sha256") else None,
        usage=facts.get("usage"), usage_status="USAGE_REPORTED_UNTRUSTED" if facts.get("usage") else "USAGE_UNKNOWN",
        cost_status="COST_UNKNOWN", price_source="UNVERIFIED", proof_class=PROOF_CLASS,
        provider_invocation=PROVIDER_NOT_INVOKED, model_origin_proof=MODEL_ORIGIN_UNVERIFIED,
        real_origin=REAL_ORIGIN_UNVERIFIED,
    )
    record["record_id"] = RECORD_ID_PREFIX + stage_b._digest(record)
    return record


def run_real01_attempt(request: object, *, transport: OfflineCodexWireTransport, journal_dir: object,
                       clock_ns=None) -> Real01Result:
    """Reserve, dispatch at most once, journal one terminal. Replays return the stored record."""
    import time
    clock = clock_ns or time.time_ns
    if not request_is_bound(request) or type(transport) is not OfflineCodexWireTransport:
        return Real01Result(getattr(request, "request_id", ""), "REQUEST_OR_TRANSPORT_INVALID", None)
    root = Path(journal_dir).absolute()
    stem = "real01-" + request.request_id.rsplit(":", 1)[1]
    terminal, marker = root / (stem + ".json"), root / (stem + ".reserved")
    if terminal.exists():
        try:
            record = json.loads(terminal.read_bytes())
            if record.get("runtime_profile_sha256") != request.runtime_profile_sha256:
                raise ValueError("PROFILE_MISMATCH")
            body = {k: v for k, v in record.items() if k != "record_id"}
            if record.get("record_id") != RECORD_ID_PREFIX + stage_b._digest(body) or \
                    record.get("request_id") != request.request_id:
                raise ValueError
        except Exception:
            return Real01Result(request.request_id, "JOURNAL_INVALID", None)
        return Real01Result(request.request_id, record["status"], record, None, True)  # zero redispatch
    dispatched = clock()
    if not request.issued_at_ns <= dispatched < request.deadline_ns:
        return Real01Result(request.request_id, "DEADLINE_EXCEEDED_NOT_DISPATCHED", None)
    try:
        root.mkdir(parents=True, exist_ok=True)
        with marker.open("xb") as stream:
            stream.write(request.request_id.encode("ascii"))
    except FileExistsError:
        # Interrupted or concurrent earlier attempt: consumed; never dispatch again.
        return Real01Result(request.request_id, "ATTEMPT_ALREADY_RESERVED", None)
    raw = None
    try:
        report = transport._send(request, (request.deadline_ns - dispatched) / 1e9)
        finished = clock()
        status, facts, raw = classify_wire_report(request, report, dispatched_at_ns=dispatched, finished_at_ns=finished)
    except subprocess.TimeoutExpired:
        status, facts, finished = "ATTEMPT_TIMEOUT_CONSUMED", {}, clock()
    except Exception:
        status, facts, finished = "ATTEMPT_TRANSPORT_FAILED_CONSUMED", {}, clock()
    record = _origin_record(request, status, facts, raw, dispatched, finished)
    with terminal.open("xb") as stream:
        stream.write(stage_b._canonical(record))
    return Real01Result(request.request_id, status, record, raw if status == VALID_OUTPUT else None)
