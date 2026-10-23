"""S10-HERMES-AUTO-02 tool-free Stage B: exact-pin native surface and offline producer.

The live probe runs the pinned Hermes v0.21.3 checkout when present (local operator
machine); the verifier matrix always runs on a recorded report of the same shape.
No real provider, credential or product network is used.
"""
import copy
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from src.research_runtime.hermes_controlled_runtime import tool_free_stage_b as tf

ROOT = Path(__file__).resolve().parents[3]
PIN_ROOT = Path(os.environ.get("POLYMARKET_HERMES_PIN_ROOT",
                               "hermes-security-candidate-not-configured"))
_DEFAULT_TOOLS = ["clarify", "delegate_task", "execute_code", "memory", "patch", "read_file", "search_files",
                  "skill_manage", "skill_view", "skills_list", "terminal", "tool_call",
                  "tool_describe", "tool_search", "web_extract", "web_search", "write_file"]
# Synthetic copy of the sealed Windows 68-distribution observation on 2026-10-23; not native proof.
RECORDED_REPORT = dict(
    schema="auto02-native-tool-surface-v2", runtime_profile_sha256=tf._profile_entries()[0]["profile_id"].rsplit(":", 1)[1], hermes_version="0.21.3", hermes_commit=tf.PINNED_HERMES_COMMIT,
    selector_empty=[], definitions_empty=[], network_attempts=[["127.0.0.1", 9]] * 2,
    explicit_empty=dict(agent_tools=[], valid_tool_names=[], context_engine_tools=[],
                        request_keys=["messages", "model", "timeout"], request_tools=[], tool_choice_present=False),
    default_none=dict(agent_tools=_DEFAULT_TOOLS, valid_tool_names=_DEFAULT_TOOLS, context_engine_tools=[],
                      request_keys=["messages", "model", "timeout", "tools"], request_tools=_DEFAULT_TOOLS,
                      tool_choice_present=False),
)
T0 = 1_790_000_000_000_000_000


def make_request(report=RECORDED_REPORT, **changes):
    values = dict(surface_report=report, candidate_menu_sha256="a" * 64, output_schema_sha256="b" * 64,
                  model_input_sha256="c" * 64, information_cutoff_ns=T0, issued_at_ns=T0 + 1,
                  deadline_ns=T0 + 60_000_000_000, model_label="offline-injected-model")
    values.update(changes)
    return tf.build_stage_b_request(**values)


def response(request, content='{"action":"NO_TRADE"}', **changes):
    value = dict(model=request.model_label, content=content, completed_at_ns=request.issued_at_ns + 5)
    value.update(changes)
    return value


def mutated(path, value):
    report = copy.deepcopy(RECORDED_REPORT)
    target = report
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return report


def test_exact_pin_native_toolfree_request_has_zero_effective_tools(tmp_path):
    # Source-level: explicit empty list only; never the CLI flag or the None default.
    source = Path(tf.__file__).read_text(encoding="utf-8")
    assert tf.NATIVE_ENABLED_TOOLSETS == () and "--toolsets" not in source
    assert "empty = probe([])" in tf._PROBE_SOURCE and "default = probe(None)" in tf._PROBE_SOURCE
    assert tf.verify_native_tool_surface(RECORDED_REPORT)["status"] == tf.SURFACE_CHECKED
    # Mock-resistant matrix: every leak, stub-like selector or foreign network target blocks.
    for path, value, code in (
        (("explicit_empty", "request_tools"), ["memory"], "EFFECTIVE_TOOLS_PRESENT"),
        (("explicit_empty", "agent_tools"), ["terminal"], "EFFECTIVE_TOOLS_PRESENT"),
        (("explicit_empty", "valid_tool_names"), ["kanban_show"], "EFFECTIVE_TOOLS_PRESENT"),
        (("explicit_empty", "context_engine_tools"), ["lcm_grep"], "EFFECTIVE_TOOLS_PRESENT"),
        (("explicit_empty", "request_keys"), ["messages", "model", "tools"], "EFFECTIVE_TOOLS_PRESENT"),
        (("explicit_empty", "tool_choice_present"), True, "EFFECTIVE_TOOLS_PRESENT"),
        (("selector_empty",), ["web_search"], "SELECTOR_NOT_EMPTY"),
        (("definitions_empty",), ["tool_search"], "SELECTOR_NOT_EMPTY"),
        (("default_none", "request_tools"), [], "NEGATIVE_CONTROL_NOT_OBSERVED"),
        (("default_none", "request_keys"), ["messages", "model"], "NEGATIVE_CONTROL_NOT_OBSERVED"),
        (("network_attempts",), [["api.example.com", 443]], "UNEXPECTED_NETWORK_TARGET"),
        (("hermes_version",), "0.21.4", "PIN_MISMATCH"),
        (("hermes_commit",), "0" * 40, "PIN_MISMATCH"),
        (("explicit_empty", "mcp_tools"), [], "REPORT_INVALID"),
        (("producer_receipt",), "REAL_PROVIDER", "REPORT_INVALID"),
    ):
        verdict = tf.verify_native_tool_surface(mutated(path, value))
        assert verdict == dict(status=tf.SURFACE_BLOCKED, reason_code=code, tool_surface_fingerprint=None,
                               hermes_commit=None, runtime_profile_sha256=None, real_provider=tf.REAL_PROVIDER_NOT_INVOKED,
                               provider_side_toolfree="UNPROVEN"), (path, verdict)
    for bad in (None, [], {}, "report"):
        assert tf.verify_native_tool_surface(bad)["status"] == tf.SURFACE_BLOCKED
    # A pin-local .env would be loaded by pinned run_agent: refused before any child starts.
    (tmp_path / ".env").write_bytes(b"PLACEHOLDER=1")
    with pytest.raises(ValueError, match="PIN_DOTENV_PRESENT"):
        tf.probe_native_tool_surface(tmp_path, python_executable=tmp_path / "missing-python")
    if not (PIN_ROOT / ".git" / "HEAD").is_file():
        pytest.skip("exact pinned Hermes v0.21.3 checkout unavailable; recorded-report matrix only")
    report = tf.probe_native_tool_surface(PIN_ROOT)
    verdict = tf.verify_native_tool_surface(report)
    assert verdict["status"] == tf.SURFACE_CHECKED, (verdict, report)
    assert report["hermes_commit"] == tf.PINNED_HERMES_COMMIT and report["hermes_version"] == "0.21.3"
    empty, default = report["explicit_empty"], report["default_none"]
    assert empty["agent_tools"] == empty["request_tools"] == empty["valid_tool_names"] == []
    assert "tools" not in empty["request_keys"] and not empty["tool_choice_present"]
    # The same native path with None really selects the default universe (not a stub).
    assert {"terminal", "memory", "web_search"} <= set(default["request_tools"])
    assert all(attempt == ["127.0.0.1", 9] for attempt in report["network_attempts"])
    assert verdict["real_provider"] == "REAL_PROVIDER_NOT_INVOKED" and verdict["provider_side_toolfree"] == "UNPROVEN"


def test_stage_b_single_dispatch_and_invalid_terminals(tmp_path):
    request = make_request()
    assert tf.request_is_bound(request) and request.enabled_toolsets == ()
    backend = tf.OfflineStageBBackend({request.request_id: response(request)})
    first = tf.run_tool_free_stage_b(request, backend=backend, reservation_dir=tmp_path)
    assert first.status == tf.VALID_OUTPUT and tf.is_producer_result(first)
    assert first.raw_output_sha256 == hashlib.sha256(b'{"action":"NO_TRADE"}').hexdigest()
    public = first.to_public()
    assert {f.name for f in dataclasses.fields(tf.StageBResult)} == set(public) - {
        "transport_mode", "real_provider"} | {"output_bytes", "_witness"}
    assert "output_bytes" not in public and "_witness" not in public
    assert "NO_TRADE" not in json.dumps(public)
    replay = tf.run_tool_free_stage_b(request, backend=backend, reservation_dir=tmp_path)
    assert replay.status == "DISPATCH_ALREADY_RESERVED" and backend.dispatch_count == 1
    assert not tf.is_producer_result(replay)
    cases = (
        (dict(tool_calls=[{"name": "terminal"}]), "TOOL_CALL_ATTEMPT_INVALID"),
        (dict(error="provider 400"), "PROVIDER_ERROR"),
        (dict(usage={"cost_usd": "0"}), "RESPONSE_INVALID"),
        (dict(producer_receipt="REAL_PROVIDER"), "RESPONSE_INVALID"),
        (dict(model="other-model"), "MODEL_MISMATCH"),
        (dict(completed_at_ns=T0 + 120_000_000_000), "DEADLINE_EXCEEDED"),
        (dict(completed_at_ns=T0), "DEADLINE_EXCEEDED"),
        (dict(content="x" * (tf.MAX_OUTPUT_BYTES + 1)), "OUTPUT_SIZE_INVALID"),
        (dict(content=""), "OUTPUT_SIZE_INVALID"),
        (dict(content='{"action":"NO_TRADE","action":"TRADE"}'), "OUTPUT_JSON_INVALID"),
        (dict(content='{"action":NaN}'), "OUTPUT_JSON_INVALID"),
        (dict(content="[]"), "OUTPUT_JSON_INVALID"),
        (None, "PROVIDER_ERROR"),
    )
    for index, (changes, code) in enumerate(cases):
        other = make_request(model_input_sha256=f"{index:064x}")
        canned = {} if changes is None else {other.request_id: response(other, **changes)}
        result = tf.run_tool_free_stage_b(other, backend=tf.OfflineStageBBackend(canned), reservation_dir=tmp_path)
        assert result.status == code and not tf.is_producer_result(result), (changes, result)
        assert result.output_bytes is None
    # Callback-style or subclassed backends, forged requests and unverified surfaces never dispatch.
    class Sub(tf.OfflineStageBBackend):
        pass
    fresh = make_request(model_input_sha256="d" * 64)
    sub = Sub({fresh.request_id: response(fresh)})
    assert tf.run_tool_free_stage_b(fresh, backend=sub, reservation_dir=tmp_path).status == "REQUEST_OR_BACKEND_INVALID"
    assert sub.dispatch_count == 0
    for forged in (dataclasses.replace(fresh, enabled_toolsets=("web",)),
                   dataclasses.replace(fresh, deadline_ns=fresh.deadline_ns + 1),
                   dataclasses.replace(fresh, transport_mode="REAL_PROVIDER")):
        assert tf.run_tool_free_stage_b(forged, backend=backend, reservation_dir=tmp_path).status == \
            "REQUEST_OR_BACKEND_INVALID"
    assert backend.dispatch_count == 1
    for changes, code in ((dict(surface_report=mutated(("default_none", "request_tools"), [])),
                           "NEGATIVE_CONTROL_NOT_OBSERVED"),
                          (dict(deadline_ns=T0 + 400_000_000_000), "REQUEST_DEADLINE_INVALID"),
                          (dict(issued_at_ns=T0 - 1), "REQUEST_DEADLINE_INVALID"),
                          (dict(candidate_menu_sha256="A" * 64), "REQUEST_DIGEST_INVALID"),
                          (dict(model_label="../x"), "REQUEST_MODEL_INVALID")):
        with pytest.raises(ValueError, match=code):
            make_request(**changes)


def test_tool_free_modules_import_without_side_effects():
    # The pre-existing package __init__ loads analytical libraries (env writes); audit only
    # what the two new modules add after it.
    script = '''import sys
import src.research_runtime.hermes_controlled_runtime
def guard(name, args):
    if name.startswith(("socket.", "subprocess.", "sqlite3.connect", "os.system", "os.putenv")): raise RuntimeError(name)
sys.addaudithook(guard)
import src.research_runtime.hermes_controlled_runtime.tool_free_stage_b
import src.research_runtime.hermes_controlled_runtime.autonomous_feedback
print("IMPORT_NO_IO_PASS")
'''
    result = subprocess.run([sys.executable, "-B", "-c", script], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0 and "IMPORT_NO_IO_PASS" in result.stdout, result.stderr


def profile_metadata(entry=None):
    entry = entry or tf._profile_entries()[0]
    return dict(**{k: entry["preimage"][k] for k in
                   ("python_implementation", "python_version", "platform", "machine")},
                inventory=copy.deepcopy(entry["inventory"]))


def test_security_profile_hash_binds_dependency_inputs(tmp_path, monkeypatch):
    for entry in tf._profile_entries():
        metadata = profile_metadata(entry)
        args = dict(pyproject_sha256=entry["preimage"]["pyproject_sha256"],
                    uv_lock_sha256=entry["preimage"]["uv_lock_sha256"], source_head=tf.PINNED_HERMES_COMMIT)
        digest = tf.verify_profile_metadata(metadata, **args)
        assert entry["profile_id"] == "hermes-profile:sha256:" + digest
        assert tf.verify_profile_metadata(copy.deepcopy(metadata), **args) == digest
        cases = []
        for field in ("python_version", "platform", "machine", "python_implementation"):
            changed = copy.deepcopy(metadata); changed[field] = "wrong"; cases.append((changed, "PROFILE_MISMATCH"))
        for edit in ("version", "missing", "extra", "duplicate", "unsorted"):
            changed = copy.deepcopy(metadata)
            if edit == "version": changed["inventory"][0]["version"] = "0.0"
            if edit == "missing": changed["inventory"].pop()
            if edit == "extra": changed["inventory"].append(dict(name="zz-extra", version="1"))
            if edit == "duplicate": changed["inventory"].append(changed["inventory"][0])
            if edit == "unsorted": changed["inventory"].reverse()
            cases.append((changed, "PROFILE_INVALID" if edit in ("duplicate", "unsorted") else "PROFILE_MISMATCH"))
        cases += [(None, "PROFILE_INVALID"), ({**metadata, "raw": "do-not-echo"}, "PROFILE_INVALID")]
        for changed, code in cases:
            with pytest.raises(ValueError) as exc:
                tf.verify_profile_metadata(changed, **args)
            assert str(exc.value) == code and "do-not-echo" not in str(exc.value)
        for field in ("pyproject_sha256", "uv_lock_sha256", "source_head"):
            with pytest.raises(ValueError, match="PIN_MISMATCH" if field == "source_head" else "PROFILE_MISMATCH"):
                tf.verify_profile_metadata(metadata, **dict(args, **{field: "0" * 64}))
    (tmp_path / "pyproject.toml").write_text("changed input")
    (tmp_path / "uv.lock").write_text("changed lock")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("child started before input rejection"))
    with pytest.raises(ValueError, match="PROFILE_MISMATCH"):
        tf.verify_runtime_profile(tmp_path)
    if (PIN_ROOT / ".git/HEAD").is_file():
        for outside in (sys.executable, str(tmp_path / "python;echo-injection.exe")):
            with pytest.raises(ValueError, match="PROFILE_MISMATCH"):
                tf.verify_runtime_profile(PIN_ROOT, python_executable=outside)
    policy = Path(tf.__file__).resolve().parents[3] / "docs/hermes_runtime_security_profile.json"
    original_read = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda self: b"untrusted" if self == policy else original_read(self))
    with pytest.raises(ValueError, match="PROFILE_INVALID"):
        tf._profile_entries()


def test_security_profile_native_tools_and_denied_sockets(tmp_path, monkeypatch):
    assert tf.verify_native_tool_surface(RECORDED_REPORT)["status"] == tf.SURFACE_CHECKED
    old = dict(RECORDED_REPORT, schema="auto02-native-tool-surface-v1")
    old.pop("runtime_profile_sha256")
    assert tf.verify_native_tool_surface(old)["reason_code"] == "REPORT_INVALID"
    for digest in (None, "", "0" * 64):
        assert tf.verify_native_tool_surface(dict(RECORDED_REPORT, runtime_profile_sha256=digest))["status"] == tf.SURFACE_BLOCKED
    # Both installer-style subprocesses and shell execution are denied, before app imports.
    script = tf._OFFLINE_PROCESS_GUARD + """
import os, subprocess, sys
for attempt in (lambda: subprocess.run([sys.executable, "-c", "pass"]), lambda: os.system("exit 0")):
    try: attempt()
    except OSError as exc: assert str(exc) == "offline child: subprocess denied"
    else: raise AssertionError("process escaped")
print("OFFLINE_PROCESS_DENIAL_PASS")
"""
    sealed = subprocess.run([sys.executable, "-I", "-B", "-c", script], capture_output=True, timeout=30)
    assert sealed.returncode == 0 and b"OFFLINE_PROCESS_DENIAL_PASS" in sealed.stdout
    # A successful-looking app report cannot conceal inventory drift after construction.
    with monkeypatch.context() as patch:
        (tmp_path / ".git").mkdir(); (tmp_path / ".git/HEAD").write_text(tf.PINNED_HERMES_COMMIT)
        profiles = iter([RECORDED_REPORT["runtime_profile_sha256"], "0" * 64])
        patch.setattr(tf, "verify_runtime_profile", lambda *a, **k: next(profiles))
        patch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 0, b"{}", b""))
        with pytest.raises(ValueError, match="PROFILE_MISMATCH"):
            tf.probe_native_tool_surface(tmp_path)
    if (PIN_ROOT / ".git/HEAD").is_file():
        before = tf.verify_runtime_profile(PIN_ROOT)
        report = tf.probe_native_tool_surface(PIN_ROOT)
        assert before == tf.verify_runtime_profile(PIN_ROOT) == report["runtime_profile_sha256"]
        assert tf.verify_native_tool_surface(report)["status"] == tf.SURFACE_CHECKED
        assert report["default_none"]["request_tools"] == _DEFAULT_TOOLS
        assert report["explicit_empty"]["request_tools"] == []
        assert all(a == ["127.0.0.1", 9] for a in report["network_attempts"])


def test_security_profile_dependency_and_image_compatibility():
    expected = {"anyio": "4.14.2", "certifi": "2026.10.19", "pillow": "13.0.0", "pyjwt": "2.15.0", "urllib3": "2.8.0"}
    for entry in tf._profile_entries():
        installed = {d["name"]: d["version"] for d in entry["inventory"]}
        assert {k: installed[k] for k in expected} == expected
        assert tf._profile_hash(entry["inventory"]) == entry["preimage"]["installed_inventory_sha256"]
    if (PIN_ROOT / ".git/HEAD").is_file():
        before = tf.verify_runtime_profile(PIN_ROOT)
        script = """import io, importlib.metadata
from PIL import Image
expected = {"anyio":"4.14.2","certifi":"2026.10.19","pillow":"13.0.0","pyjwt":"2.15.0","urllib3":"2.8.0"}
assert all(importlib.metadata.version(k)==v for k,v in expected.items())
for fmt in ("PNG", "JPEG", "GIF", "TIFF"):
    data=io.BytesIO(); Image.new("RGB", (8,8), "blue").save(data,format=fmt)
    with Image.open(io.BytesIO(data.getvalue())) as im:
        im.load(); im.thumbnail((4,4)); out=io.BytesIO(); im.convert("RGBA").save(out,format="PNG")
        assert out.getvalue().startswith(b"\\x89PNG")
print("IMAGE_AND_DEPENDENCY_PROFILE_PASS")
"""
        exe = PIN_ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run = subprocess.run([str(exe), "-I", "-B", "-c", script], capture_output=True, timeout=60)
        assert run.returncode == 0 and b"IMAGE_AND_DEPENDENCY_PROFILE_PASS" in run.stdout, run.stderr
        assert tf.verify_runtime_profile(PIN_ROOT) == before
