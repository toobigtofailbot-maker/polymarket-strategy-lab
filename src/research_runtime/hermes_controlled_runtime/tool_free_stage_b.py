"""Default-off Hermes-native tool-free Stage B boundary (S10-HERMES-AUTO-02).

Offline only. ``probe_native_tool_surface`` runs the exact pinned Hermes AIAgent in an
isolated child (empty HERMES_HOME, stripped environment, sockets denied) and reports
the effective model-facing tool surface for ``enabled_toolsets=[]`` after every native
post-load injection, plus the serialized request ``build_api_kwargs`` would send. The
``None`` default is probed as a negative control so a stubbed selector cannot pass.

A real provider transport is DISABLED / NOT PROVEN: the only dispatch path is the
trusted :class:`OfflineStageBBackend` holding canned data (no callables, no I/O). A
tool-call attempt, provider error, model mismatch, late response, oversize or
non-strict JSON is an invalid terminal; there is no retry or fallback. SHA-256 binds
locally controlled evidence; it is not a provider attestation.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
from pathlib import Path
import re

from src.strategy_lifecycle.models import strict_json_loads

from .models import canonical_json_bytes as _canonical

PINNED_HERMES_COMMIT = "345cd2b057a452236de401d3534b8502a7465e8d"
PINNED_HERMES_SEMVER = "0.21.3"
SURFACE_CHECKED = "OFFLINE_NATIVE_TOOL_SURFACE_CHECKED"
SURFACE_BLOCKED = "TOOLFREE_NATIVE_PRECHECK_BLOCKED"
REAL_PROVIDER_NOT_INVOKED = "REAL_PROVIDER_NOT_INVOKED"
REAL_PROVIDER_TRANSPORT = "DISABLED_NOT_PROVEN"
TRANSPORT_OFFLINE_INJECTED = "OFFLINE_INJECTED"
VALID_OUTPUT = "VALID_OUTPUT"
MAX_OUTPUT_BYTES = 16_384
MAX_DISPATCH_WINDOW_NS = 300_000_000_000
REQUEST_ID_PREFIX = "stageb:sha256:"
# Explicit empty list. ``None`` means the full default universe in pinned model_tools.
NATIVE_ENABLED_TOOLSETS: tuple[str, ...] = ()
_LOOPBACK_SENTINEL = ("127.0.0.1", 9)
_HEX64 = re.compile(r"[0-9a-f]{64}")
_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")
_MAX_TIME = 2**63 - 1
_REPORT_KEYS = {"schema", "hermes_version", "hermes_commit", "selector_empty", "definitions_empty",
                "explicit_empty", "default_none", "network_attempts"}
_PROBE_KEYS = {"agent_tools", "valid_tool_names", "context_engine_tools", "request_keys",
               "request_tools", "tool_choice_present"}
_RESPONSE_KEYS = {"model", "content", "completed_at_ns", "tool_calls", "error"}

# Executed ONLY inside the pinned Hermes virtualenv child (``python -I -B -c``).
_PROBE_SOURCE = r'''
import json, os, socket, sys
attempts = []
def _record(host, port):
    attempts.append([str(host)[:64], port if type(port) is int else str(port)[:16]])
    raise OSError("offline probe: network denied")
def _connect(self, address, *a, **k):
    _record(*(tuple(address)[:2] if isinstance(address, tuple) else (address, None)))
def _create_connection(address, *a, **k):
    _record(*tuple(address)[:2])
def _getaddrinfo(host, port, *a, **k):
    _record(host, port)
socket.socket.connect = _connect
socket.socket.connect_ex = _connect
socket.create_connection = _create_connection
socket.getaddrinfo = _getaddrinfo
sys.path.insert(0, os.getcwd())
import hermes_cli, model_tools
from run_agent import AIAgent
from agent.chat_completion_helpers import build_api_kwargs
def names(tools):
    return sorted(t["function"]["name"] for t in (tools or []))
def probe(enabled):
    kw = dict(base_url="http://127.0.0.1:9/v1", api_key="offline-probe-placeholder", provider="custom",
              model="offline-probe-model", quiet_mode=True, skip_context_files=True, skip_memory=False,
              skip_background_review=True, max_iterations=1)
    if enabled is not None:
        kw["enabled_toolsets"] = enabled
    agent = AIAgent(**kw)
    request = build_api_kwargs(agent, [{"role": "user", "content": "offline tool-surface probe"}])
    return dict(agent_tools=names(agent.tools), valid_tool_names=sorted(agent.valid_tool_names or ()),
                context_engine_tools=sorted(getattr(agent, "_context_engine_tool_names", None) or ()),
                request_keys=sorted(request), request_tools=names(request.get("tools")),
                tool_choice_present="tool_choice" in request)
empty = probe([])
default = probe(None)
print(json.dumps(dict(schema="auto02-native-tool-surface-v1", hermes_version=hermes_cli.__version__,
    selector_empty=sorted(model_tools._select_tool_names([], None, True)),
    definitions_empty=names(model_tools.get_tool_definitions(enabled_toolsets=[], quiet_mode=True)),
    explicit_empty=empty, default_none=default, network_attempts=attempts), sort_keys=True))
'''


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _time(value: object) -> bool:
    return type(value) is int and 0 <= value <= _MAX_TIME


def _names(value: object) -> bool:
    return type(value) is list and all(type(n) is str for n in value)


def verify_native_tool_surface(report: object) -> dict:
    """Pure verdict over one probe report; never trusts a partial or stub-like report."""
    def blocked(code: str) -> dict:
        return dict(status=SURFACE_BLOCKED, reason_code=code, tool_surface_fingerprint=None,
                    hermes_commit=None, real_provider=REAL_PROVIDER_NOT_INVOKED,
                    provider_side_toolfree="UNPROVEN")
    if type(report) is not dict or set(report) != _REPORT_KEYS:
        return blocked("REPORT_INVALID")
    if report["schema"] != "auto02-native-tool-surface-v1" or report["hermes_version"] != PINNED_HERMES_SEMVER \
            or report["hermes_commit"] != PINNED_HERMES_COMMIT:
        return blocked("PIN_MISMATCH")
    probes = (report["explicit_empty"], report["default_none"])
    if not all(type(p) is dict and set(p) == _PROBE_KEYS and all(_names(p[k]) for k in _PROBE_KEYS - {"tool_choice_present"})
               and type(p["tool_choice_present"]) is bool for p in probes):
        return blocked("REPORT_INVALID")
    empty, default = probes
    if report["selector_empty"] != [] or report["definitions_empty"] != []:
        return blocked("SELECTOR_NOT_EMPTY")
    if any(empty[k] for k in ("agent_tools", "valid_tool_names", "context_engine_tools", "request_tools")) \
            or "tools" in empty["request_keys"] or empty["tool_choice_present"]:
        return blocked("EFFECTIVE_TOOLS_PRESENT")
    # Negative control: the same native path with ``None`` must expose the default universe.
    if not default["request_tools"] or "tools" not in default["request_keys"] \
            or default["request_tools"] != default["agent_tools"]:
        return blocked("NEGATIVE_CONTROL_NOT_OBSERVED")
    attempts = report["network_attempts"]
    if type(attempts) is not list or any(a != list(_LOOPBACK_SENTINEL) for a in attempts):
        return blocked("UNEXPECTED_NETWORK_TARGET")
    return dict(status=SURFACE_CHECKED, reason_code=None, tool_surface_fingerprint=_digest(report),
                hermes_commit=PINNED_HERMES_COMMIT, real_provider=REAL_PROVIDER_NOT_INVOKED,
                provider_side_toolfree="UNPROVEN")


def probe_native_tool_surface(pin_root: object, *, python_executable: object = None,
                              timeout_s: int = 300) -> dict:
    """Run the isolated child once and return the raw report (verify it separately).

    Reads only the pin's ``.git/HEAD`` (and refuses a pin-local ``.env``); the child gets a fresh empty home, no inherited
    variables except ``SYSTEMROOT`` (Windows loader), and denied sockets.
    """
    import os
    import subprocess
    import tempfile
    root = Path(pin_root).absolute()
    # Pinned run_agent loads <pin>/.env at import; refuse rather than expose any secret (existence only).
    if (root / ".env").exists():
        raise ValueError("PIN_DOTENV_PRESENT")
    head = (root / ".git" / "HEAD").read_text(encoding="ascii").strip()
    exe = Path(python_executable) if python_executable is not None else (
        root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    with tempfile.TemporaryDirectory(prefix="auto02-hermes-home-") as home:
        env = {key: home for key in ("HERMES_HOME", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP")}
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", PATH=str(exe.parent), NO_COLOR="1")
        if "SYSTEMROOT" in os.environ:
            env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
        completed = subprocess.run([str(exe), "-I", "-B", "-c", _PROBE_SOURCE], cwd=root, env=env,
                                   capture_output=True, timeout=timeout_s, check=False)
    lines = completed.stdout.decode("utf-8", "replace").strip().splitlines()
    report = json.loads(lines[-1]) if completed.returncode == 0 and lines else {}
    if type(report) is dict and report:
        report["hermes_commit"] = head
    return report


@dataclass(frozen=True)
class StageBRequest:
    """Content-addressed single-dispatch identity; ``enabled_toolsets`` is always empty."""
    request_id: str
    candidate_menu_sha256: str
    output_schema_sha256: str
    model_input_sha256: str
    information_cutoff_ns: int
    issued_at_ns: int
    deadline_ns: int
    model_label: str
    hermes_commit: str
    tool_surface_fingerprint: str
    enabled_toolsets: tuple[str, ...] = NATIVE_ENABLED_TOOLSETS
    transport_mode: str = TRANSPORT_OFFLINE_INJECTED


def _request_preimage(request: StageBRequest) -> dict:
    return {k: (list(v) if isinstance(v, tuple) else v) for k, v in request.__dict__.items() if k != "request_id"}


def build_stage_b_request(*, surface_report: object, candidate_menu_sha256: str, output_schema_sha256: str,
                          model_input_sha256: str, information_cutoff_ns: int, issued_at_ns: int,
                          deadline_ns: int, model_label: str) -> StageBRequest:
    """Bind one request to a freshly verified native surface; raises ValueError(code)."""
    verdict = verify_native_tool_surface(surface_report)
    if verdict["status"] != SURFACE_CHECKED:
        raise ValueError(verdict["reason_code"])
    if not all(type(v) is str and _HEX64.fullmatch(v) for v in
               (candidate_menu_sha256, output_schema_sha256, model_input_sha256)):
        raise ValueError("REQUEST_DIGEST_INVALID")
    if not (all(_time(t) for t in (information_cutoff_ns, issued_at_ns, deadline_ns)) and
            information_cutoff_ns <= issued_at_ns < deadline_ns <= issued_at_ns + MAX_DISPATCH_WINDOW_NS):
        raise ValueError("REQUEST_DEADLINE_INVALID")
    if type(model_label) is not str or not _LABEL.fullmatch(model_label):
        raise ValueError("REQUEST_MODEL_INVALID")
    draft = StageBRequest("", candidate_menu_sha256, output_schema_sha256, model_input_sha256,
                          information_cutoff_ns, issued_at_ns, deadline_ns, model_label,
                          verdict["hermes_commit"], verdict["tool_surface_fingerprint"])
    return replace(draft, request_id=REQUEST_ID_PREFIX + _digest(_request_preimage(draft)))


def request_is_bound(request: object) -> bool:
    return (type(request) is StageBRequest and request.enabled_toolsets == () and
            request.transport_mode == TRANSPORT_OFFLINE_INJECTED and
            request.hermes_commit == PINNED_HERMES_COMMIT and
            request.request_id == REQUEST_ID_PREFIX + _digest(_request_preimage(request)))


class OfflineStageBBackend:
    """Trusted offline test transport: canned responses keyed by request id, no callables."""

    def __init__(self, responses: dict) -> None:
        self._responses = {k: dict(v) for k, v in responses.items()}
        self.dispatch_count = 0

    def _dispatch(self, request: StageBRequest) -> object:
        self.dispatch_count += 1
        return self._responses.get(request.request_id)


_PRODUCER = object()


@dataclass(frozen=True)
class StageBResult:
    request_id: str
    status: str
    raw_output_sha256: str | None
    response_completed_ns: int | None
    output_bytes: bytes | None = field(default=None, repr=False)
    _witness: object = field(default=None, repr=False, compare=False)

    def to_public(self) -> dict:
        """Receipt view: never the raw model output."""
        return dict(request_id=self.request_id, status=self.status, raw_output_sha256=self.raw_output_sha256,
                    response_completed_ns=self.response_completed_ns, transport_mode=TRANSPORT_OFFLINE_INJECTED,
                    real_provider=REAL_PROVIDER_NOT_INVOKED)


def is_producer_result(result: object) -> bool:
    return (type(result) is StageBResult and result._witness is _PRODUCER and result.status == VALID_OUTPUT
            and type(result.output_bytes) is bytes
            and hashlib.sha256(result.output_bytes).hexdigest() == result.raw_output_sha256)


def _classify(request: StageBRequest, response: object) -> tuple[str, bytes | None, int | None]:
    if type(response) is not dict or "error" in response:
        return "PROVIDER_ERROR", None, None
    if not set(response) <= _RESPONSE_KEYS:
        return "RESPONSE_INVALID", None, None  # usage/cost/receipt claims are never accepted offline
    if response.get("tool_calls", []) != []:
        return "TOOL_CALL_ATTEMPT_INVALID", None, None
    if response.get("model") != request.model_label:
        return "MODEL_MISMATCH", None, None
    completed = response.get("completed_at_ns")
    if not _time(completed) or not request.issued_at_ns <= completed <= request.deadline_ns:
        return "DEADLINE_EXCEEDED", None, None
    content = response.get("content")
    raw = content.encode("utf-8") if type(content) is str else None
    if raw is None or not 0 < len(raw) <= MAX_OUTPUT_BYTES:
        return "OUTPUT_SIZE_INVALID", None, completed
    try:
        if type(strict_json_loads(content)) is not dict:
            raise ValueError
    except Exception:
        return "OUTPUT_JSON_INVALID", raw, completed
    return VALID_OUTPUT, raw, completed


def run_tool_free_stage_b(request: StageBRequest, *, backend: OfflineStageBBackend,
                          reservation_dir: object) -> StageBResult:
    """At most one offline dispatch per request id, reserved before the backend is touched."""
    if not request_is_bound(request) or type(backend) is not OfflineStageBBackend:
        return StageBResult(getattr(request, "request_id", ""), "REQUEST_OR_BACKEND_INVALID", None, None)
    marker = Path(reservation_dir).absolute() / ("stageb-" + request.request_id.rsplit(":", 1)[1] + ".reserved")
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        with marker.open("xb") as stream:
            stream.write(request.request_id.encode("ascii"))
    except FileExistsError:
        return StageBResult(request.request_id, "DISPATCH_ALREADY_RESERVED", None, None)
    status, raw, completed = _classify(request, backend._dispatch(request))
    digest = hashlib.sha256(raw).hexdigest() if raw is not None else None
    return StageBResult(request.request_id, status, digest, completed,
                        raw if status == VALID_OUTPUT else None, _PRODUCER)
