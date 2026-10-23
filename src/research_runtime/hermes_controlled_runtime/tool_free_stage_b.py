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
_REPORT_KEYS = {"schema", "hermes_version", "hermes_commit", "runtime_profile_sha256", "selector_empty", "definitions_empty",
                "explicit_empty", "default_none", "network_attempts"}
_PROBE_KEYS = {"agent_tools", "valid_tool_names", "context_engine_tools", "request_keys",
               "request_tools", "tool_choice_present"}
_RESPONSE_KEYS = {"model", "content", "completed_at_ns", "tool_calls", "error"}

# Offline children may not escape socket guards through an installer or other process.
_OFFLINE_PROCESS_GUARD = r'''
import sys

def _deny_offline_process(event, args):
    if event.startswith(("subprocess.", "os.system", "os.spawn", "os.exec", "os.posix_spawn", "os.startfile")):
        raise OSError("offline child: subprocess denied")
sys.addaudithook(_deny_offline_process)
'''
_WINDOWS_DEFAULT_TOOLS = ["clarify", "delegate_task", "execute_code", "memory", "patch", "read_file",
    "search_files", "skill_manage", "skill_view", "skills_list", "terminal", "tool_call", "tool_describe",
    "tool_search", "web_extract", "web_search", "write_file"]

# Executed ONLY inside the pinned Hermes virtualenv child (``python -I -B -c``).
_PROBE_SOURCE = _OFFLINE_PROCESS_GUARD + r'''
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
print(json.dumps(dict(schema="auto02-native-tool-surface-v2", hermes_version=hermes_cli.__version__,
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


# Owner-controlled immutable source is assumed; this is not hostile-host attestation.
_PROFILE_POLICY_SHA256 = "eba64a49fa0d6215278b34e96725e195fb1549d143673117c992b6ae52935680"
_PROFILE_KEYS = {"schema", "upstream_commit", "hermes_version", "python_implementation",
                 "python_version", "platform", "machine", "pyproject_sha256", "uv_lock_sha256",
                 "installed_inventory_sha256"}
_METADATA_SOURCE = r'''
import importlib.metadata, json, platform, socket, sys
def denied(*args, **kwargs):
    raise OSError("profile metadata: network denied")
socket.socket.connect = socket.socket.connect_ex = denied
socket.create_connection = socket.getaddrinfo = denied
inventory = sorted([dict(name=d.metadata["Name"].lower().replace("_", "-"), version=d.version)
                    for d in importlib.metadata.distributions()], key=lambda d: d["name"])
print(json.dumps(dict(python_implementation=platform.python_implementation(),
    python_version=platform.python_version(), platform=sys.platform,
    machine=platform.machine().lower(), inventory=inventory), allow_nan=False))
'''


def _profile_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _profile_hash(value: object) -> str:
    return hashlib.sha256(_profile_json(value)).hexdigest()


def _profile_entries() -> list:
    """Load only the hash-bound repository policy, never an operator-supplied policy."""
    try:
        raw = (Path(__file__).resolve().parents[3] / "docs/hermes_runtime_security_profile.json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != _PROFILE_POLICY_SHA256:
            raise ValueError("PROFILE_INVALID")
        entries = json.loads(raw)["profiles"]
        if type(entries) is not list or len(entries) != 2:
            raise ValueError("PROFILE_INVALID")
        for entry in entries:
            preimage, inventory = entry["preimage"], entry["inventory"]
            if set(preimage) != _PROFILE_KEYS or not _inventory_valid(inventory) or \
                    preimage["installed_inventory_sha256"] != _profile_hash(inventory) or \
                    entry["profile_id"] != "hermes-profile:sha256:" + _profile_hash(preimage):
                raise ValueError("PROFILE_INVALID")
        return entries
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        raise ValueError("PROFILE_INVALID") from None


def _inventory_valid(inventory: object) -> bool:
    if type(inventory) is not list or not inventory:
        return False
    if any(type(d) is not dict or set(d) != {"name", "version"} or
           any(type(d[k]) is not str or not d[k] for k in ("name", "version")) or
           d["name"] != d["name"].lower().replace("_", "-") for d in inventory):
        return False
    names = [d["name"] for d in inventory]
    return names == sorted(set(names))


def profile_digest_is_approved(value: object) -> bool:
    if type(value) is not str or not _HEX64.fullmatch(value):
        return False
    try:
        return any(e["profile_id"] == "hermes-profile:sha256:" + value for e in _profile_entries())
    except ValueError:
        return False


def verify_profile_metadata(metadata: object, *, pyproject_sha256: str, uv_lock_sha256: str,
                            source_head: str) -> str:
    """Pure comparison against the trusted policy; errors contain no rejected metadata."""
    entries = _profile_entries()
    keys = {"python_implementation", "python_version", "platform", "machine", "inventory"}
    if type(metadata) is not dict or set(metadata) != keys or not _inventory_valid(metadata["inventory"]) or \
            any(type(metadata[k]) is not str or not metadata[k] for k in keys - {"inventory"}):
        raise ValueError("PROFILE_INVALID")
    preimage = dict(schema="hermes-runtime-profile-v1", upstream_commit=PINNED_HERMES_COMMIT,
                    hermes_version=PINNED_HERMES_SEMVER, pyproject_sha256=pyproject_sha256,
                    uv_lock_sha256=uv_lock_sha256,
                    installed_inventory_sha256=_profile_hash(metadata["inventory"]),
                    **{k: metadata[k] for k in keys - {"inventory"}})
    matches = [e for e in entries if e["preimage"] == preimage and e["inventory"] == metadata["inventory"]]
    if len(matches) != 1:
        raise ValueError("PROFILE_MISMATCH")
    if source_head != PINNED_HERMES_COMMIT:
        raise ValueError("PIN_MISMATCH")
    return _profile_hash(preimage)


def verify_runtime_profile(pin_root: object, *, python_executable: object = None) -> str:
    """Recheck exact dependency inputs and pin-owned interpreter before each app child."""
    import os
    import subprocess
    import tempfile
    try:
        root = Path(pin_root).absolute()
        if (root / ".env").exists():
            raise ValueError("PIN_DOTENV_PRESENT")
        _profile_entries()
        project_hash = hashlib.sha256((root / "pyproject.toml").read_bytes()).hexdigest()
        lock_hash = hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest()
        entries = _profile_entries()
        if not any(e["preimage"]["pyproject_sha256"] == project_hash and
                   e["preimage"]["uv_lock_sha256"] == lock_hash for e in entries):
            raise ValueError("PROFILE_MISMATCH")
        exe = Path(python_executable).absolute() if python_executable is not None else (
            root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
        # A Linux venv's python may itself be a symlink; its invocation path must be pin-owned.
        if not exe.parent.resolve().is_relative_to((root / ".venv").resolve()) or not exe.is_file():
            raise ValueError("PROFILE_MISMATCH")
        head = (root / ".git/HEAD").read_text(encoding="ascii").strip()
        with tempfile.TemporaryDirectory(prefix="hermes-profile-home-") as home:
            env = {k: home for k in ("HOME", "HERMES_HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP")}
            env.update(PATH=str(exe.parent), PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")
            if "SYSTEMROOT" in os.environ:
                env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
            completed = subprocess.run([str(exe), "-I", "-B", "-c", _METADATA_SOURCE], cwd=root,
                                       env=env, capture_output=True, timeout=30, check=False)
        if completed.returncode != 0 or len(completed.stdout) > 1_048_576 or completed.stderr:
            raise ValueError("PROFILE_INVALID")
        metadata = json.loads(completed.stdout)
        return verify_profile_metadata(metadata, pyproject_sha256=project_hash,
                                       uv_lock_sha256=lock_hash, source_head=head)
    except (OSError, TypeError, KeyError, UnicodeError, RecursionError, subprocess.SubprocessError):
        raise ValueError("PROFILE_INVALID") from None
    except ValueError as exc:
        code = str(exc)
        raise ValueError(code if code in {"PROFILE_INVALID", "PROFILE_MISMATCH", "PIN_MISMATCH", "PIN_DOTENV_PRESENT"}
                         else "PROFILE_INVALID") from None


def verify_native_tool_surface(report: object) -> dict:
    """Pure verdict over one probe report; never trusts a partial or stub-like report."""
    def blocked(code: str) -> dict:
        return dict(status=SURFACE_BLOCKED, reason_code=code, tool_surface_fingerprint=None,
                    hermes_commit=None, runtime_profile_sha256=None, real_provider=REAL_PROVIDER_NOT_INVOKED,
                    provider_side_toolfree="UNPROVEN")
    if type(report) is not dict or set(report) != _REPORT_KEYS:
        return blocked("REPORT_INVALID")
    if report["schema"] != "auto02-native-tool-surface-v2" or report["hermes_version"] != PINNED_HERMES_SEMVER \
            or report["hermes_commit"] != PINNED_HERMES_COMMIT:
        return blocked("PIN_MISMATCH")
    if not profile_digest_is_approved(report["runtime_profile_sha256"]):
        return blocked("PROFILE_MISMATCH")
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
    windows_digest = next(e["profile_id"].rsplit(":", 1)[1] for e in _profile_entries()
                          if e["preimage"]["platform"] == "win32")
    if report["runtime_profile_sha256"] == windows_digest and any(
            default[k] != _WINDOWS_DEFAULT_TOOLS for k in ("request_tools", "agent_tools", "valid_tool_names")):
        return blocked("NEGATIVE_CONTROL_NOT_OBSERVED")
    attempts = report["network_attempts"]
    if type(attempts) is not list or any(a != list(_LOOPBACK_SENTINEL) for a in attempts):
        return blocked("UNEXPECTED_NETWORK_TARGET")
    return dict(status=SURFACE_CHECKED, reason_code=None, tool_surface_fingerprint=_digest(report),
                hermes_commit=PINNED_HERMES_COMMIT, runtime_profile_sha256=report["runtime_profile_sha256"], real_provider=REAL_PROVIDER_NOT_INVOKED,
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
    profile = verify_runtime_profile(root, python_executable=exe)
    with tempfile.TemporaryDirectory(prefix="auto02-hermes-home-") as home:
        Path(home, "config.yaml").write_text("security:\n  allow_lazy_installs: false\n", encoding="utf-8")
        env = {key: home for key in ("HERMES_HOME", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP")}
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", PATH=str(exe.parent), NO_COLOR="1", HERMES_DISABLE_LAZY_INSTALLS="1")
        if "SYSTEMROOT" in os.environ:
            env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
        completed = subprocess.run([str(exe), "-I", "-B", "-c", _PROBE_SOURCE], cwd=root, env=env,
                                   capture_output=True, timeout=timeout_s, check=False)
    if verify_runtime_profile(root, python_executable=exe) != profile:
        raise ValueError("PROFILE_MISMATCH")
    lines = completed.stdout.decode("utf-8", "replace").strip().splitlines()
    report = json.loads(lines[-1]) if completed.returncode == 0 and lines else {}
    if type(report) is dict and report:
        report["hermes_commit"] = head
        report["runtime_profile_sha256"] = profile
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
    runtime_profile_sha256: str
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
                          verdict["hermes_commit"], verdict["tool_surface_fingerprint"], verdict["runtime_profile_sha256"])
    return replace(draft, request_id=REQUEST_ID_PREFIX + _digest(_request_preimage(draft)))


def request_is_bound(request: object) -> bool:
    return (type(request) is StageBRequest and request.enabled_toolsets == () and
            request.transport_mode == TRANSPORT_OFFLINE_INJECTED and
            request.hermes_commit == PINNED_HERMES_COMMIT and
            profile_digest_is_approved(request.runtime_profile_sha256) and
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
    runtime_profile_sha256: str | None = None
    output_bytes: bytes | None = field(default=None, repr=False)
    _witness: object = field(default=None, repr=False, compare=False)

    def to_public(self) -> dict:
        """Receipt view: never the raw model output."""
        return dict(request_id=self.request_id, status=self.status, raw_output_sha256=self.raw_output_sha256,
                    response_completed_ns=self.response_completed_ns, runtime_profile_sha256=self.runtime_profile_sha256, transport_mode=TRANSPORT_OFFLINE_INJECTED,
                    real_provider=REAL_PROVIDER_NOT_INVOKED)


def is_producer_result(result: object) -> bool:
    return (type(result) is StageBResult and result._witness is _PRODUCER and result.status == VALID_OUTPUT
            and profile_digest_is_approved(result.runtime_profile_sha256) and type(result.output_bytes) is bytes
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
    return StageBResult(request.request_id, status, digest, completed, request.runtime_profile_sha256,
                        raw if status == VALID_OUTPUT else None, _PRODUCER)
