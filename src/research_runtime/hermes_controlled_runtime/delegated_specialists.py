"""Pinned upstream Hermes delegated specialists with a host-owned child witness (S10-HERMES-DELEGATED-SPECIALISTS-01).

One finite, opt-in, offline path: a restricted native Hermes parent (``web`` + ``delegation``)
built inside the pinned v0.21.3 venv makes ONE host-initiated synchronous call to the genuine
upstream ``tools.delegate_tool.delegate_task(tasks=[A3, A4], background=False)``. Task index 0 is
the FORECASTER and index 1 the FALSIFIER; those roles are caller-owned commitments bound by
index, never the upstream ``role`` argument and never a model self-report.

Witness seam (verified at commit 345cd2b): upstream ``_build_children`` reaches
``tools.delegate_tool._build_child_agent`` and ``_Batch.run_child`` reaches
``tools.delegate_tool._run_single_child`` through call-time module attribute lookups. For this
one bounded run the worker replaces those two module attributes with observers that CALL THE
ORIGINAL pinned functions, record the post-init child (sessions, lineage, depth/role, effective
model-facing tools) before any inference and the host-owned terminal result entry, and restore
the originals in ``finally``. A child whose effective tools, depth or lineage is wrong is refused
in the construction observer, so upstream never runs it. Upstream source is never edited.

Provider boundary: the only accepted transport is the offline scripted client installed at
``agent.process_bootstrap.OpenAI`` (upstream's single client chokepoint). Sockets and
subprocesses are denied by an audit hook inside the worker. Real provider transport is not
authorized by this WP and is not implemented.

This module's top level imports only the standard library so that the same file runs as the
worker under ``python -I -B`` inside the pinned venv. Host-side helpers import repository code
lazily. Nothing here touches accounts, markets, orders or credentials.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sys
import tempfile
import threading
import time

WP_ID = "S10-HERMES-DELEGATED-SPECIALISTS-01"
REQUEST_SCHEMA = "s10-hermes-delegated-request-v1"
WITNESS_SCHEMA = "s10-hermes-delegated-witness-v1"
SEALED_SCHEMA = "s10-hermes-delegated-sealed-witness-v1"
WITNESS_PREFIX = "hermesdelegationwitness:sha256:"
BINDING_PREFIX = "hermesdelegationbinding:sha256:"
EVIDENCE_CLASS = "OFFLINE_NATIVE_DELEGATION_TEST_ONLY"
ORIGIN_CLASS = "COLD_VERIFIED_OFFLINE_NATIVE_CHILD_PATH"
ACCEPTANCE_STATUS = "OFFLINE_IMPLEMENTATION_COMPLETE_REAL_PROVIDER_ACCEPTANCE_PENDING"
PROVIDER_INVOCATIONS = "ZERO_REAL_PROVIDER_INVOCATIONS"

PIN_COMMIT = "345cd2b057a452236de401d3534b8502a7465e8d"
PARENT_TOOLS = ("delegate_task", "web_extract", "web_search")
CHILD_TOOLS = ("web_extract", "web_search")
ROLE_BY_INDEX = ("FORECASTER", "FALSIFIER")
SENTINEL_BASE_URL = "http://127.0.0.1:9/v1"  # never reachable: every socket entry point is denied
SENTINEL_HOST, SENTINEL_PORT = "127.0.0.1", 9
SCRIPTED_MODES = ("reply", "raise", "sleep")
MAX_WITNESS_BYTES = 4 << 20

# LF-normalized SHA-256 of the exact pinned upstream seam files (tag v2026.9.14).
PIN_SEAM_SHA256 = {
    "tools/delegate_tool.py": "8d2d684eda36dfa2b8371da814522d9b08c686105969eef366d265ae6f9e50f2",
    "tools/delegate_tool_dispatch.py": "440e21dd9aa730cd31923871808710a3ab2546ef0deda3b6a85c9fc0a3ba7721",
    "tools/delegate_tool_results.py": "bbd8517b4e49d7fa55ffed36fdabf898c2a41292619be4777af55060b19440c5",
    "tools/delegate_tool_toolsets.py": "a1967a15c535dbbd100a812bfa5d43dd26459f1775ded775d59716faa1acfbe2",
    "tools/delegate_tool_config.py": "6d5d799be6021232ea352ede62f912642f0174654079bd42a99e40daab9f597c",
    "tools/delegate_tool_child_run.py": "42768b0fb5b816339665f492fdfffe0471f18557a33d88ad0acea03b653c8c1c",
    "toolsets.py": "7d743a132c00417604313c9832286825771c3da79a82a9c6c0308c82d77236fa",
    "run_agent.py": "dc125031d13e2a341eec473bcfcafce16c7356505dcbc560bec562b1ecaddc04",
    "agent/process_bootstrap.py": "660b79126385961c787dc1b7654cf5a6310f678d735004792c0e8c70b6554f93",
}
UPSTREAM_ENTRYPOINTS = ("delegate_task", "_build_children", "_build_child_agent", "_run_single_child")
_SUBPROCESS_EVENTS = ("subprocess.", "os.system", "os.spawn", "os.exec", "os.posix_spawn", "os.startfile", "os.fork")
_NETWORK_EVENTS = ("socket.connect", "socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr",
                   "socket.sendto", "socket.sendmsg")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _lf_sha(path: Path) -> str | None:
    try:
        return _sha(path.read_bytes().replace(b"\r\n", b"\n"))
    except OSError:
        return None


def task_marker(index: int, nonce: str) -> str:
    return f"[W01-TASK-{index}-{nonce}]"


# =====================================================================================
# Worker: runs ONLY inside the pinned venv (``python -I -B this_file --worker PIN REQUEST``)
# =====================================================================================


def _worker(pin_root: str, request_path: str) -> int:
    request = json.loads(Path(request_path).read_text(encoding="utf-8"))
    witness: dict = {"schema_id": WITNESS_SCHEMA, "request_id": request["request_id"], "nonce": request["nonce"],
                     "refusals": [], "network_attempts": [], "subprocess_attempts": 0, "subprocess_denied": [], "builds": [], "runs": [],
                     "model_requests": [], "late_runs": 0, "delegate_called": False, "delegate_results": [],
                     "restored": None, "defense_probe": request.get("defense_probe")}
    lock = threading.Lock()

    def audit(event: str, args: tuple) -> None:
        if event.startswith(_SUBPROCESS_EVENTS):
            witness["subprocess_attempts"] += 1
            program = args[0] if args and isinstance(args[0], (str, bytes, os.PathLike)) else None
            witness["subprocess_denied"].append([event, os.path.basename(os.fsdecode(program)) if program else None])
            raise OSError("W01_OFFLINE_SUBPROCESS_DENIED")
        if event in _NETWORK_EVENTS:
            target = args[1] if event in ("socket.connect", "socket.sendto") and len(args) > 1 else args[:2]
            host, port = (tuple(target) + (None, None))[:2] if isinstance(target, (tuple, list)) else (target, None)
            witness["network_attempts"].append(
                "SENTINEL_LOOPBACK" if (host, port) == (SENTINEL_HOST, SENTINEL_PORT) else "OTHER")
            raise OSError("W01_OFFLINE_NETWORK_DENIED")

    sys.addaudithook(audit)

    def emit(code: int) -> int:
        tmp = Path(request["witness_path"] + ".tmp")
        tmp.write_bytes(_canonical(witness))
        os.replace(tmp, request["witness_path"])
        return code

    def refuse(code: str) -> int:
        witness["refusals"].append(code)
        return emit(3)

    sys.path.insert(0, pin_root)
    try:
        import tools.delegate_tool as dt
        from tools import delegate_tool_config as dcfg
        from agent import process_bootstrap
        from openai.types.chat import ChatCompletion
    except Exception:  # noqa: BLE001 - closed code only; upstream text is never echoed
        return refuse("UPSTREAM_SEAM_MISSING")
    if any(not callable(getattr(dt, name, None)) for name in UPSTREAM_ENTRYPOINTS):
        return refuse("UPSTREAM_SEAM_MISSING")
    witness["seam_sha256"] = {rel: _lf_sha(Path(pin_root) / rel) for rel in PIN_SEAM_SHA256}
    witness["delegate_module_is_pinned"] = Path(dt.__file__).resolve() == (Path(pin_root) / "tools" / "delegate_tool.py").resolve()
    if witness["seam_sha256"] != PIN_SEAM_SHA256 or not witness["delegate_module_is_pinned"]:
        return refuse("PIN_SOURCE_MISMATCH")

    nonce = request["nonce"]
    goals = [task["goal"] for task in request["tasks"]]
    scripted = {int(k): v for k, v in request["scripted"].items()}

    class _Completions:
        def create(self, **kwargs):
            text = json.dumps(kwargs.get("messages") or [], ensure_ascii=False, default=str)
            hits = [i for i in scripted if task_marker(i, nonce) in text]
            tools = sorted(t.get("function", {}).get("name", "?") for t in (kwargs.get("tools") or []))
            with lock:
                witness["model_requests"].append({"task_index": hits[0] if len(hits) == 1 else None, "tools": tools})
            if len(hits) != 1:
                raise RuntimeError("W01_UNROUTED_MODEL_REQUEST")
            spec = scripted[hits[0]]
            if spec["mode"] == "raise":
                raise RuntimeError("W01_SCRIPTED_PROVIDER_FAILURE")
            if spec["mode"] == "sleep":
                time.sleep(spec["seconds"])
            return ChatCompletion.model_validate({
                "id": f"offline-{hits[0]}", "object": "chat.completion", "created": 0,
                "model": kwargs.get("model", "offline-scripted-model"),
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": spec["content"]}}],
                "usage": {"prompt_tokens": spec["prompt_tokens"], "completion_tokens": spec["completion_tokens"],
                          "total_tokens": spec["prompt_tokens"] + spec["completion_tokens"]}})

    class _OfflineScriptedClient:
        def __init__(self, **kwargs):
            self.base_url = kwargs.get("base_url")
            self.api_key = kwargs.get("api_key")
            self.chat = type("Chat", (), {"completions": _Completions()})()

        def close(self):
            return None

    process_bootstrap.OpenAI = _OfflineScriptedClient  # provider boundary only

    cfg = dict(dcfg._load_config())
    witness["knobs"] = {
        "max_spawn_depth": dcfg._get_max_spawn_depth(), "orchestrator_enabled": dcfg._get_orchestrator_enabled(),
        "inherit_mcp_toolsets": dcfg._get_inherit_mcp_toolsets(),
        "max_concurrent_children": dcfg._get_max_concurrent_children(),
        "child_timeout_seconds": float(dcfg._get_child_timeout()), "max_iterations": cfg.get("max_iterations"),
        "subagent_auto_approve": cfg.get("subagent_auto_approve"),
        "independent_completions": cfg.get("independent_completions")}
    hard = {"max_spawn_depth": 1, "orchestrator_enabled": False, "inherit_mcp_toolsets": False,
            "subagent_auto_approve": False, "independent_completions": False}
    if any(witness["knobs"][k] != v for k, v in hard.items()) or witness["knobs"] != request["expected_knobs"] \
            or not 1 <= int(witness["knobs"]["max_concurrent_children"] or 0) <= 2:
        return refuse("CONFIG_KNOB_MISMATCH")

    from run_agent import AIAgent
    parent = AIAgent(base_url=SENTINEL_BASE_URL, api_key="offline-scripted-boundary", provider="custom",
                     model="offline-scripted-model", quiet_mode=True, skip_context_files=True, skip_memory=True,
                     enabled_toolsets=list(request["parent_toolsets"]), max_iterations=1)
    witness["parent"] = {"session_id": parent.session_id, "valid_tools": sorted(parent.valid_tool_names or ()),
                         "schema_tools": sorted(t["function"]["name"] for t in (parent.tools or [])),
                         "enabled_toolsets": list(parent.enabled_toolsets or [])}
    if witness["parent"]["valid_tools"] != list(PARENT_TOOLS) or witness["parent"]["schema_tools"] != list(PARENT_TOOLS):
        witness["refusals"].append("PARENT_TOOLS_NOT_ALLOWED")
        if request.get("defense_probe") != "SKIP_PARENT_GATE":
            return emit(3)

    original_build, original_run = dt._build_child_agent, dt._run_single_child
    finished = threading.Event()

    def observed_build(*args, **kwargs):
        child = original_build(*args, **kwargs)  # the genuine pinned constructor
        index = kwargs.get("task_index", args[0] if args else None)
        row = {"task_index": index, "session_id": getattr(child, "session_id", None),
               "parent_session_id": getattr(child, "_parent_session_id", None),
               "subagent_id": getattr(child, "_subagent_id", None), "depth": getattr(child, "_delegate_depth", None),
               "delegate_role": getattr(child, "_delegate_role", None),
               "valid_tools": sorted(getattr(child, "valid_tool_names", None) or ()),
               "schema_tools": sorted(t["function"]["name"] for t in (getattr(child, "tools", None) or [])),
               "enabled_toolsets": list(getattr(child, "enabled_toolsets", None) or []),
               "goal_sha256": _sha(str(kwargs.get("goal", "")).encode("utf-8")), "problems": []}
        with lock:
            if index not in (0, 1) or kwargs.get("goal") != goals[index] \
                    or any(b["task_index"] == index for b in witness["builds"]) or len(witness["builds"]) >= 2:
                row["problems"].append("TASK_IDENTITY_INVALID")
            if row["valid_tools"] != list(CHILD_TOOLS) or row["schema_tools"] != list(CHILD_TOOLS):
                row["problems"].append("CHILD_TOOLS_NOT_ALLOWED")
            if row["depth"] != 1 or row["delegate_role"] != "leaf":
                row["problems"].append("CHILD_NOT_LEAF")
            if row["parent_session_id"] != parent.session_id or row["session_id"] in (None, parent.session_id):
                row["problems"].append("CHILD_LINEAGE_INVALID")
            witness["builds"].append(row)
        if row["problems"]:
            raise ValueError("W01_PRE_INFERENCE_REFUSAL")  # upstream _build_children aborts: no child runs
        return child

    def observed_run(*args, **kwargs):
        child = kwargs.get("child")
        index = kwargs.get("task_index", args[0] if args else None)
        entry = original_run(*args, **kwargs)  # the genuine pinned terminal executor
        summary = entry.get("summary") if isinstance(entry.get("summary"), str) else ""
        tokens = entry.get("tokens") if isinstance(entry.get("tokens"), dict) else {}
        row = {"task_index": index, "session_id": getattr(child, "session_id", None), "status": entry.get("status"),
               "exit_reason": entry.get("exit_reason"), "truncated": entry.get("truncated"),
               "api_calls": entry.get("api_calls"), "tokens": {"input": tokens.get("input"), "output": tokens.get("output")},
               "cost_usd": entry.get("cost_usd"), "cost_status": entry.get("cost_status"),
               "error_present": bool(entry.get("error")), "summary": summary,
               "summary_sha256": _sha(summary.encode("utf-8"))}
        with lock:
            if finished.is_set():
                witness["late_runs"] += 1
            else:
                witness["runs"].append(row)
        return entry

    dt._build_child_agent, dt._run_single_child = observed_build, observed_run
    try:
        witness["delegate_called"] = True
        raw = dt.delegate_task(tasks=[dict(task) for task in request["tasks"]], parent_agent=parent, background=False)
    finally:
        finished.set()
        dt._build_child_agent, dt._run_single_child = original_build, original_run
        witness["restored"] = dt._build_child_agent is original_build and dt._run_single_child is original_run
    try:
        result = json.loads(raw)
    except (TypeError, ValueError):
        result = {}
    witness["delegate_error"] = bool(isinstance(result, dict) and result.get("error"))
    witness["delegate_results"] = [{"task_index": r.get("task_index"), "status": r.get("status")}
                                   for r in (result.get("results") or []) if isinstance(r, dict)] \
        if isinstance(result, dict) else []
    if any(b["problems"] for b in witness["builds"]):
        witness["refusals"].append("PRE_INFERENCE_REFUSAL")
    return emit(0)


# =====================================================================================
# Host side: pin verification, bounded launch, witness validation and sealing
# =====================================================================================


@dataclasses.dataclass(frozen=True)
class DelegationWitness:
    """Host-sealed witness; only witnesses issued by ``run_delegated_specialists`` in THIS process are claimable."""

    witness_id: str
    body_json: str


@dataclasses.dataclass(frozen=True)
class DelegationResult:
    status: str
    refusal_codes: tuple[str, ...]
    witness: DelegationWitness | None
    receipt: dict


_ISSUED: dict[str, str] = {}
_CONSUMED: set[str] = set()
_REGISTRY_LOCK = threading.Lock()


class DelegationRefusal(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def pin_python(pin_root: Path) -> Path:
    return pin_root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def verify_pin(pin_root: object) -> str | None:
    """None when ``pin_root`` is the exact clean-seam pinned checkout, else a closed refusal code."""
    root = Path(str(pin_root)) if pin_root else None
    if root is None or not root.is_dir() or not (root / ".git" / "HEAD").is_file() or not pin_python(root).is_file():
        return "PINNED_RUNTIME_UNAVAILABLE"
    if (root / ".env").exists():
        return "PIN_ENV_FILE_PRESENT"  # upstream run_agent loads <pin>/.env at import; never allowed here
    if (root / ".git" / "HEAD").read_text(encoding="ascii", errors="replace").strip() != PIN_COMMIT:
        return "PIN_COMMIT_MISMATCH"
    if any(_lf_sha(root / rel) != digest for rel, digest in PIN_SEAM_SHA256.items()):
        return "PIN_SOURCE_MISMATCH"
    return None


def scripted_reply(content: str, *, prompt_tokens: int = 64, completion_tokens: int = 64, mode: str = "reply",
                   seconds: float = 0.0) -> dict:
    """One offline scripted provider-boundary reply (engineering test transport only)."""
    return {"mode": mode, "content": content, "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
            "seconds": seconds}


def expected_knobs(policy) -> dict:
    return {"max_spawn_depth": policy.max_spawn_depth, "orchestrator_enabled": policy.orchestrator_enabled,
            "inherit_mcp_toolsets": policy.inherit_mcp_toolsets,
            "max_concurrent_children": policy.max_concurrent_children,
            "child_timeout_seconds": float(policy.child_timeout_seconds), "max_iterations": policy.child_max_iterations,
            "subagent_auto_approve": policy.subagent_auto_approve,
            "independent_completions": policy.independent_completions}


def prepare_request(policy, *, request_id: str, source_binding_sha256: str, goals: tuple[str, str],
                    contexts: tuple[str, str], scripted: dict) -> dict:
    """Deterministic request; the nonce marks each task so the scripted boundary can route without trusting text."""
    nonce = secrets.token_hex(8)
    tasks = [{"goal": f"{task_marker(i, nonce)} {ROLE_BY_INDEX[i]}: {goals[i]}", "context": contexts[i]}
             for i in (0, 1)]
    return {"schema_id": REQUEST_SCHEMA, "request_id": request_id, "nonce": nonce, "policy_id": policy.policy_id,
            "source_binding_sha256": source_binding_sha256, "tasks": tasks,
            "scripted": {str(i): dict(scripted[i]) for i in (0, 1)}, "parent_toolsets": list(policy.parent_toolsets),
            "expected_knobs": expected_knobs(policy)}


def execute_worker(policy, pin_root: object, request: dict, *, managed_config_bytes: bytes | None = None,
                   timeout_seconds: float | None = None) -> tuple[object, dict | None]:
    """One bounded worker process in an ephemeral home outside the repo; returns (outcome, raw witness or None)."""
    from src.research_runtime.hermes_controlled_runtime.runner import run_pinned_python_worker

    root = Path(str(pin_root))
    work = Path(tempfile.mkdtemp(prefix="w01-delegation-"))
    try:
        home, managed, cwd, out = (work / name for name in ("home", "managed", "cwd", "out"))
        for directory in (home, managed, cwd, out):
            directory.mkdir()
        (managed / "config.yaml").write_bytes(managed_config_bytes if managed_config_bytes is not None
                                              else policy.managed_config_bytes())
        body = dict(request, witness_path=str(out / "witness.json"))
        (work / "request.json").write_bytes(_canonical(body))
        env = {"HERMES_HOME": str(home), "HOME": str(home), "USERPROFILE": str(home), "APPDATA": str(home),
               "LOCALAPPDATA": str(home), "TEMP": str(home), "TMP": str(home), "HERMES_MANAGED_DIR": str(managed),
               "PATH": str(pin_python(root).parent), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
               "PYTHONIOENCODING": "utf-8", "NO_COLOR": "1", "HERMES_DISABLE_LAZY_INSTALLS": "1"}
        if os.name == "nt" and os.environ.get("SYSTEMROOT"):
            env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
        outcome = run_pinned_python_worker(str(pin_python(root)), str(Path(__file__).resolve()),
                                           ["--worker", str(root), str(work / "request.json")], env=env, cwd=str(cwd),
                                           timeout_seconds=timeout_seconds or policy.worker_timeout_seconds)
        witness_file = out / "witness.json"
        if outcome.timed_out or outcome.launch_failed or not witness_file.is_file() \
                or witness_file.stat().st_size > MAX_WITNESS_BYTES:
            return outcome, None  # a killed or silent worker never publishes, even if it wrote late
        try:
            return outcome, json.loads(witness_file.read_bytes())
        except ValueError:
            return outcome, None
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _cost(run: dict) -> str | float:
    status, value = run.get("cost_status"), run.get("cost_usd")
    if status in (None, "", "unknown") or type(value) not in (int, float):
        return "UNKNOWN"  # absent or ambiguous cost is never treated as zero
    return float(value)


def validate_witness(policy, request: dict, outcome, raw: dict | None) -> list[str]:
    """Closed refusal codes; empty means two genuine, completed, correctly-scoped native children."""
    codes: list[str] = []
    if outcome is None or getattr(outcome, "timed_out", False):
        return ["WORKER_TIMEOUT"]
    if getattr(outcome, "launch_failed", False):
        return ["WORKER_LAUNCH_FAILED"]
    if not isinstance(raw, dict) or raw.get("schema_id") != WITNESS_SCHEMA:
        return ["WITNESS_MISSING"]
    codes.extend(c for c in raw.get("refusals", []) if isinstance(c, str))
    if outcome.exit_code != 0:
        codes.append("WORKER_EXIT_NONZERO")
    if raw.get("request_id") != request["request_id"] or raw.get("nonce") != request["nonce"]:
        codes.append("WITNESS_REQUEST_MISMATCH")
    if raw.get("defense_probe") is not None:
        codes.append("DEFENSE_PROBE_NEVER_ACCEPTED")
    if raw.get("seam_sha256") != PIN_SEAM_SHA256 or raw.get("delegate_module_is_pinned") is not True:
        codes.append("PIN_SOURCE_MISMATCH")
    if raw.get("knobs") != expected_knobs(policy):
        codes.append("CONFIG_KNOB_MISMATCH")
    parent = raw.get("parent") or {}
    if parent.get("valid_tools") != list(policy.parent_tools) or parent.get("schema_tools") != list(policy.parent_tools):
        codes.append("PARENT_TOOLS_NOT_ALLOWED")
    # Denied subprocess attempts (upstream shell probes) never execute; they are evidence, not a pass condition.
    if any(a != "SENTINEL_LOOPBACK" for a in raw.get("network_attempts", [])):
        codes.append("OFFLINE_BOUNDARY_VIOLATION")
    if raw.get("restored") is not True:
        codes.append("OBSERVER_NOT_RESTORED")
    if raw.get("late_runs"):
        codes.append("LATE_CHILD_PUBLICATION")
    builds, runs = raw.get("builds") or [], raw.get("runs") or []
    if not raw.get("delegate_called") or len(builds) != 2 or len(runs) != 2:
        codes.append("CHILD_CALLS_INCOMPLETE")
    if raw.get("delegate_error"):
        codes.append("DELEGATE_TASK_ERROR")
    if sorted(b.get("task_index") for b in builds if isinstance(b, dict)) != [0, 1] \
            or sorted(r.get("task_index") for r in runs if isinstance(r, dict)) != [0, 1]:
        codes.append("CHILD_ROLE_INDEX_INVALID")
    sessions = [b.get("session_id") for b in builds] + [parent.get("session_id")]
    subagents = [b.get("subagent_id") for b in builds]
    if len(set(sessions)) != len(sessions) or None in sessions or len(set(subagents)) != len(subagents) or None in subagents:
        codes.append("CHILD_IDENTITY_DUPLICATE_OR_MISSING")
    by_build = {b.get("task_index"): b for b in builds if isinstance(b, dict)}
    for build in builds:
        if build.get("problems") or build.get("depth") != 1 or build.get("delegate_role") != "leaf" \
                or build.get("parent_session_id") != parent.get("session_id"):
            codes.append("CHILD_CONSTRUCTION_INVALID")
        if build.get("valid_tools") != list(policy.child_tools) or build.get("schema_tools") != list(policy.child_tools):
            codes.append("CHILD_TOOLS_NOT_ALLOWED")
    goals = [task["goal"] for task in request["tasks"]]
    requests_by_index: dict = {}
    for req in raw.get("model_requests", []):
        requests_by_index.setdefault(req.get("task_index"), []).append(req)
        if req.get("task_index") not in (0, 1):
            codes.append("UNROUTED_MODEL_REQUEST")
        elif not set(req.get("tools", [])) <= set(policy.child_tools):
            codes.append("MODEL_FACING_TOOLS_NOT_ALLOWED")
    for run in runs:
        index = run.get("task_index")
        build = by_build.get(index)
        if build is None or run.get("session_id") != build.get("session_id"):
            codes.append("CHILD_RUN_UNOBSERVED_CONSTRUCTION")
            continue
        if build.get("goal_sha256") != _sha(goals[index].encode("utf-8")):
            codes.append("TASK_IDENTITY_INVALID")
        if run.get("status") != "completed" or run.get("exit_reason") != "completed" or run.get("truncated") \
                or run.get("error_present"):
            codes.append("CHILD_NOT_COMPLETED")
        tokens = run.get("tokens") or {}
        if type(run.get("api_calls")) is not int or type(tokens.get("input")) is not int \
                or type(tokens.get("output")) is not int:
            codes.append("CHILD_USAGE_UNKNOWN")
        elif run["api_calls"] > policy.max_child_api_calls or tokens["input"] + tokens["output"] > policy.max_child_tokens:
            codes.append("CHILD_BUDGET_EXCEEDED")
        elif len(requests_by_index.get(index, [])) != run["api_calls"]:
            codes.append("CHILD_MODEL_CALLS_UNACCOUNTED")
        summary = run.get("summary")
        if type(summary) is not str or not summary or len(summary) > policy.max_summary_chars \
                or _sha(summary.encode("utf-8")) != run.get("summary_sha256"):
            codes.append("CHILD_OUTPUT_INVALID")
        if policy.cost_certainty_required and _cost(run) == "UNKNOWN":
            codes.append("CHILD_COST_UNKNOWN")
    statuses = {r.get("task_index"): r.get("status") for r in raw.get("delegate_results", [])}
    if statuses != {0: "completed", 1: "completed"}:
        codes.append("DELEGATE_RESULT_NOT_COMPLETED")
    return sorted(set(codes))


def _stable_binding(policy, request: dict, children: list[dict]) -> str:
    """Session-independent binding: same pin, policy, source binding, roles, tools and outputs -> same digest."""
    stable = {"pin_commit": PIN_COMMIT, "policy_id": policy.policy_id,
              "source_binding_sha256": request["source_binding_sha256"],
              "children": [{k: c[k] for k in ("task_index", "role", "effective_tools", "status", "summary_sha256")}
                           for c in children]}
    return BINDING_PREFIX + _sha(_canonical(stable))


def seal(policy, request: dict, raw: dict) -> DelegationWitness:
    builds = {b["task_index"]: b for b in raw["builds"]}
    children = []
    for run in sorted(raw["runs"], key=lambda r: r["task_index"]):
        build = builds[run["task_index"]]
        children.append({"task_index": run["task_index"], "role": ROLE_BY_INDEX[run["task_index"]],
                         "session_id": build["session_id"], "parent_session_id": build["parent_session_id"],
                         "subagent_id": build["subagent_id"], "depth": build["depth"],
                         "delegate_role": build["delegate_role"], "effective_tools": build["valid_tools"],
                         "status": run["status"], "api_calls": run["api_calls"], "tokens": run["tokens"],
                         "cost": _cost(run), "summary": run["summary"], "summary_sha256": run["summary_sha256"]})
    body = {"schema_id": SEALED_SCHEMA, "wp_id": WP_ID, "request_id": request["request_id"],
            "policy_id": policy.policy_id, "pin_commit": PIN_COMMIT, "transport": policy.transport,
            "source_binding_sha256": request["source_binding_sha256"], "parent_session_id": raw["parent"]["session_id"],
            "parent_tools": raw["parent"]["valid_tools"], "knobs": raw["knobs"],
            "upstream_calls_observed": {"delegate_task": 1, "_build_child_agent": 2, "_run_single_child": 2},
            "children": children, "stable_binding": _stable_binding(policy, request, children),
            "evidence_class": EVIDENCE_CLASS, "origin_class": ORIGIN_CLASS, "acceptance_status": ACCEPTANCE_STATUS,
            "provider_invocations": PROVIDER_INVOCATIONS}
    body_json = _canonical(body).decode("utf-8")
    witness = DelegationWitness(WITNESS_PREFIX + _sha(body_json.encode("utf-8")), body_json)
    with _REGISTRY_LOCK:
        _ISSUED[witness.witness_id] = _sha(body_json.encode("utf-8"))
    return witness


def claim_witness(witness: object) -> dict:
    """One-shot claim of a witness issued in this process; forged, tampered, replayed or reloaded ones are refused."""
    if not isinstance(witness, DelegationWitness) or type(witness.body_json) is not str:
        raise DelegationRefusal("WITNESS_NOT_HOST_ISSUED")
    digest = _sha(witness.body_json.encode("utf-8"))
    with _REGISTRY_LOCK:
        issued = _ISSUED.get(witness.witness_id)
        if issued is None:
            raise DelegationRefusal("WITNESS_NOT_HOST_ISSUED")
        if issued != digest or witness.witness_id != WITNESS_PREFIX + digest:
            raise DelegationRefusal("WITNESS_TAMPERED")
        if witness.witness_id in _CONSUMED:
            raise DelegationRefusal("WITNESS_ALREADY_CONSUMED")
        _CONSUMED.add(witness.witness_id)
    return json.loads(witness.body_json)


def run_delegated_specialists(policy, pin_root: object, *, request_id: str, source_binding_sha256: str,
                              goals: tuple[str, str], contexts: tuple[str, str], scripted: dict) -> DelegationResult:
    """The single opt-in producer entrypoint: one parent, one synchronous native batch, two children, no retry."""
    from src.research_runtime.hermes_controlled_runtime.policy import DelegatedSpecialistsPolicy

    if type(policy) is not DelegatedSpecialistsPolicy:
        return DelegationResult("REFUSED", ("DELEGATED_POLICY_REQUIRED",), None, {})
    pin_refusal = verify_pin(pin_root)
    if pin_refusal:
        return DelegationResult("REFUSED", (pin_refusal,), None, {})
    if set(scripted) != {0, 1} or any(s.get("mode") not in SCRIPTED_MODES for s in scripted.values()):
        return DelegationResult("REFUSED", ("SCRIPTED_TRANSPORT_INVALID",), None, {})
    request = prepare_request(policy, request_id=request_id, source_binding_sha256=source_binding_sha256, goals=goals,
                              contexts=contexts, scripted=scripted)
    outcome, raw = execute_worker(policy, pin_root, request)
    codes = validate_witness(policy, request, outcome, raw)
    receipt = {"request_id": request_id, "policy_id": policy.policy_id, "pin_commit": PIN_COMMIT,
               "worker_exit_code": getattr(outcome, "exit_code", None), "worker_timed_out": getattr(outcome, "timed_out", None),
               "worker_stdout_sha256": getattr(outcome, "stdout_sha256", None),
               "worker_stderr_sha256": getattr(outcome, "stderr_sha256", None),
               "network_attempts_denied": len((raw or {}).get("network_attempts", [])),
               "subprocess_attempts_denied": (raw or {}).get("subprocess_attempts", 0),
               "model_requests": len((raw or {}).get("model_requests", [])), "refusal_codes": codes,
               "evidence_class": EVIDENCE_CLASS, "provider_invocations": PROVIDER_INVOCATIONS}
    if codes:
        return DelegationResult("REFUSED", tuple(codes), None, receipt)
    witness = seal(policy, request, raw)
    return DelegationResult("WITNESSED", (), witness, dict(receipt, witness_id=witness.witness_id))


if __name__ == "__main__" and len(sys.argv) == 4 and sys.argv[1] == "--worker":
    raise SystemExit(_worker(sys.argv[2], sys.argv[3]))
