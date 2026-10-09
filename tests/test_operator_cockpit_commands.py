"""S10-CC-CMD-01 protected operator commands (C01-C16).

Every lifecycle fixture is a real verified StrategyLifecycle store built through the public
lifecycle API. Commands run in-process through FastAPI's TestClient: no test opens a network
socket or reaches any external or product network. The only command secret is an obviously
synthetic sentinel assembled at runtime; it is never a real credential.
"""

from __future__ import annotations

import ast
import dataclasses
import getpass
import hashlib
import http.client
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src import operator_cockpit as cockpit
from src import operator_cockpit_commands as commands
from src.strategy_lifecycle import (
    PORTFOLIO_CAPACITY_REJECTED,
    PORTFOLIO_CAPACITY_VALID,
    PortfolioCapacityResult,
    StrategyCapacityResult,
    append_strategy_lifecycle_record,
    build_portfolio_authority_policy,
    build_portfolio_policy_receipt,
    build_strategy_family,
    build_strategy_health_receipt,
    build_strategy_restriction_receipt,
    build_strategy_risk_allocation,
    build_strategy_version,
    canonical_json_bytes,
    initialize_strategy_lifecycle_store,
    load_strategy_lifecycle_store,
)
from src.strategy_lifecycle import models as M
from src.strategy_lifecycle import store as S
from tests.test_operator_cockpit_research import BOUNDS, LIMITS, STRATEGY_SPEC


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src" / "operator_cockpit_commands.py"
COCKPIT = ROOT / "src" / "operator_cockpit.py"
STORE = ROOT / "src" / "strategy_lifecycle" / "store.py"
FRONTEND_ROOT = ROOT / "src" / "operator_cockpit_frontend"
FRONTEND = FRONTEND_ROOT / "src"
CONTRACT = ROOT / "docs" / "control_center_command_contract.md"

# Obviously synthetic test-only sentinels, assembled at runtime (never a real credential).
SENTINEL = "SYNTHETIC-CMD01-TEST-SENTINEL-" + "q" * 20
OTHER_SENTINEL = "SYNTHETIC-CMD01-WRONG-SENTINEL-" + "z" * 20
NOW_MS = 1_000_000
OPERATOR = "op-karl"
COMMAND_ROUTES = {
    "/api/commands/status": {"GET"},
    "/api/commands/session": {"POST"},
    "/api/commands/session/revoke": {"POST"},
    "/api/commands/execute": {"POST"},
}
RECEIPT_KEYS = {
    "schema_version", "status", "command_ref", "command_kind", "operator_id",
    "canonical_record_kind", "canonical_record_id", "lifecycle_store_head_entry_hash",
    "issued_at_ms", "no_product_network", "no_account_access", "no_order_authority",
    "no_gate_c_authority", "no_live_authority",
}
STATUS_KEYS = {
    "read_only", "commands_enabled", "auth_mode", "session_ttl_seconds", "active_session",
    "supported_commands", "no_product_network", "no_account_access", "no_order_authority",
    "no_gate_c_authority", "no_live_authority",
}
KINDS = ("STRATEGY_PAUSE", "STRATEGY_RESUME", "STRATEGY_QUARANTINE", "POLICY_ACTIVATE", "POLICY_REVOKE")
PHRASES = {
    "STRATEGY_PAUSE": "CONFIRM-PAUSE",
    "STRATEGY_RESUME": "CONFIRM-RESUME",
    "STRATEGY_QUARANTINE": "CONFIRM-QUARANTINE",
    "POLICY_ACTIVATE": "CONFIRM-ACTIVATE-POLICY",
    "POLICY_REVOKE": "CONFIRM-REVOKE-POLICY",
}


def _error(code: str) -> dict:
    return {"error": {"code": code}}


# ---------------------------------------------------------------------------
# Fixtures: real verified lifecycle stores, deterministic clock, synthetic auth.
# ---------------------------------------------------------------------------


def _family(key: str):
    return build_strategy_family(
        family_key=key, family_label="Command family", created_time_ns=1,
        creation_provenance="unit:fixture",
    )


def _version(family, label: str):
    return build_strategy_version(
        strategy_family_id=family.strategy_family_id, parent=None, strategy_label=label,
        evidence_posture="REPEATABLE_STATISTICAL", strategy_code_identity="strategy_code:v1",
        strategy_spec=STRATEGY_SPEC, adaptive_bounds=BOUNDS, evidence_refs=(),
        created_time_ns=2, creation_provenance="unit:fixture",
    )


def _policy(label: str, *, effective=10, expires=None, predecessor=None, created=10, **overrides):
    limits = dict(LIMITS)
    limits.update(overrides)
    return build_portfolio_authority_policy(
        predecessor_policy_id=predecessor, policy_label=label,
        account_scope_ref="account:public-scope-1", effective_from_ns=effective,
        expires_at_ns=expires, allowed_order_styles=("PASSIVE_MAKER",), created_time_ns=created,
        **limits,
    )


def _policy_receipt(action: str, policy, previous, t: int):
    return build_portfolio_policy_receipt(
        action=action, policy_id=policy.policy_id, previous_active_policy_id=previous,
        human_authorization_ref="human:fixture-1", created_time_ns=t,
    )


def _allocation(version, policy, *, budget="50", start=100, until=None, t=100):
    return build_strategy_risk_allocation(
        strategy_version_id=version.strategy_version_id, policy_id=policy.policy_id,
        risk_band="EXPLORATORY_LIVE", active_budget_usd=budget, allocation_basis="DIRECT_DECISION",
        decision_ref="decision:fixture-1", valid_from_ns=start, valid_until_ns=until,
        created_time_ns=t,
    )


def _health(version, previous: str, new: str, t: int = 50):
    return build_strategy_health_receipt(
        strategy_version_id=version.strategy_version_id, previous_health_state=previous,
        new_health_state=new, decision_ref="decision:fixture-health", created_time_ns=t,
    )


def _restriction(version, key: str, kind: str, *, cap=None, action="APPLY", t: int = 60):
    return build_strategy_restriction_receipt(
        strategy_version_id=version.strategy_version_id, restriction_key=key, action=action,
        restriction_kind=kind, max_active_budget_usd=cap, decision_ref="decision:fixture-restrict",
        created_time_ns=t,
    )


@dataclasses.dataclass
class Lab:
    path: Path
    a: object = None
    b: object = None
    p1: object = None
    p2: object = None
    advance_count: int = 0

    def append(self, record):
        result = append_strategy_lifecycle_record(self.path, record)
        assert result.is_valid, result.error_codes
        return record

    def snapshot(self):
        result = load_strategy_lifecycle_store(self.path)
        assert result.is_valid, result.error_codes
        return result.snapshot

    def head(self):
        return self.snapshot().store_head_entry_hash

    def rows(self) -> int:
        return self.snapshot().total_rows

    def digest(self) -> str:
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def advance(self) -> None:
        """Advance the store head with an unrelated canonical record (strategy B only)."""
        self.advance_count += 1
        self.append(_restriction(self.b, f"unrelated.{self.advance_count}", "PAPER_ONLY", t=70))


def _empty_lab(tmp_path: Path, name: str = "lab") -> Lab:
    base = tmp_path / name
    base.mkdir()
    path = base / "lifecycle.sqlite3"
    assert initialize_strategy_lifecycle_store(path).is_valid
    return Lab(path)


def _seed(lab: Lab, *, activate=True, allocate=True) -> Lab:
    fam_a, fam_b = _family("cmd.alpha"), _family("cmd.beta")
    lab.a, lab.b = _version(fam_a, "alpha"), _version(fam_b, "beta")
    lab.p1 = _policy("Primary envelope")
    lab.p2 = _policy("Successor envelope", predecessor=lab.p1.policy_id, created=11, effective=11)
    for record in (fam_a, lab.a, fam_b, lab.b, lab.p1, lab.p2):
        lab.append(record)
    if activate:
        lab.append(_policy_receipt("ACTIVATE", lab.p1, None, 20))
        if allocate:
            lab.append(_allocation(lab.a, lab.p1))
    return lab


@pytest.fixture
def lab(tmp_path: Path) -> Lab:
    return _seed(_empty_lab(tmp_path))


class Clock:
    def __init__(self) -> None:
        self.value = NOW_MS

    def __call__(self) -> int:
        return self.value


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    current = Clock()
    monkeypatch.setattr(commands, "_now_ms", current)
    return current


def _auth(operator_id: str = OPERATOR, secret: str = SENTINEL) -> commands.CommandAuth:
    return commands.bootstrap_command_auth(
        operator_id, is_tty=lambda: True, read_secret=lambda _prompt: secret
    )


class Cockpit:
    def __init__(self, path: Path | None, auth: commands.CommandAuth | None) -> None:
        self.auth = auth
        self.app = cockpit.create_app(
            cockpit.CockpitConfig(None, None, None, None, path, command_auth=auth)
        )
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.responses: list[tuple[int, object]] = []

    def _record(self, response):
        try:
            body = response.json()
        except ValueError:
            body = response.text
        self.responses.append((response.status_code, body))
        return response.status_code, body

    def status(self, query: str = ""):
        return self._record(self.client.get("/api/commands/status" + query))

    def login(self, secret: str = SENTINEL, **kwargs):
        return self._record(self.client.post("/api/commands/session", json={"secret": secret}, **kwargs))

    def token(self) -> str:
        status, body = self.login()
        assert status == 200, body
        return body["session_token"]

    def revoke(self, token: str | None, **kwargs):
        headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
        return self._record(self.client.post("/api/commands/session/revoke", headers=headers, **kwargs))

    def execute(self, token: str | None, body, *, headers=None, raw: bytes | None = None, path="/api/commands/execute"):
        all_headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
        all_headers.update(headers or {})
        if raw is not None:
            all_headers.setdefault("Content-Type", "application/json")
            return self._record(self.client.post(path, content=raw, headers=all_headers))
        return self._record(self.client.post(path, json=body, headers=all_headers))


def _cockpit(lab: Lab | None, auth: commands.CommandAuth | None = None) -> Cockpit:
    return Cockpit(lab.path if lab is not None else None, auth)


def _body(kind: str, lab: Lab, *, head="current", issued: int | None = None, phrase=None, **target) -> dict:
    body = {
        "command_kind": kind,
        "expected_lifecycle_store_head_entry_hash": lab.head() if head == "current" else head,
        "issued_at_ms": NOW_MS if issued is None else issued,
        "confirmation_phrase": PHRASES[kind] if phrase is None else phrase,
    }
    body.update(target)
    return body


def _pause(lab: Lab, version=None, **kw) -> dict:
    return _body("STRATEGY_PAUSE", lab, strategy_version_id=(version or lab.a).strategy_version_id, **kw)


def _resume(lab: Lab, key: str, version=None, **kw) -> dict:
    return _body("STRATEGY_RESUME", lab, strategy_version_id=(version or lab.a).strategy_version_id,
                 restriction_key=key, **kw)


def _quarantine(lab: Lab, previous: str, version=None, **kw) -> dict:
    return _body("STRATEGY_QUARANTINE", lab, strategy_version_id=(version or lab.b).strategy_version_id,
                 previous_health_state=previous, **kw)


def _activate(lab: Lab, policy, previous, **kw) -> dict:
    return _body("POLICY_ACTIVATE", lab, policy_id=policy.policy_id,
                 previous_active_policy_id=previous.policy_id if previous is not None else None, **kw)


def _revoke(lab: Lab, policy, **kw) -> dict:
    return _body("POLICY_REVOKE", lab, policy_id=policy.policy_id, **kw)


def _ok(result: tuple[int, object], status: str = "COMMITTED") -> dict:
    code, body = result
    assert code == 200, body
    assert set(body) == RECEIPT_KEYS and body["status"] == status, body
    return body


def _fails(result: tuple[int, object], code: str, canonical: str | None = None, *, pure: bool = False) -> None:
    http, body = result
    assert http == commands.COMMAND_ERROR_STATUS[code], (http, body)
    if code == "COMMAND_PRECONDITION_FAILED" and canonical is None and not pure:
        # Refused either by a command precondition or first by canonical replay in the preview;
        # a canonical code, when present, is always from the closed StrategyLifecycle vocabulary.
        assert set(body) == {"error"} and body["error"]["code"] == code, body
        assert set(body["error"]) <= {"code", "canonical_error_code"}, body
        assert body["error"].get("canonical_error_code", "FIELD_VALUE_INVALID") in M.ERROR_CODES, body
        return
    expected = {"code": code}
    if canonical is not None:
        expected["canonical_error_code"] = canonical
    assert body == {"error": expected}, body


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _module_code() -> str:
    return _source(MODULE).split('"""', 2)[2]


def _walk_strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _walk_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_strings(item)
    else:
        yield str(value)


# --- Optional behavioral harness: runs the real api.ts under Node type stripping -------------

NODE_HARNESS = r"""
import { pathToFileURL } from "node:url";
const api = await import(pathToFileURL(process.argv[2]).href);
const out = {};
const calls = [];
let mode = "receipt";
const json = (body, status = 200) => new Response(JSON.stringify(body), { status });
globalThis.fetch = async (url, init) => {
  calls.push({ url, method: init.method, headers: init.headers, credentials: init.credentials, cache: init.cache,
               body: init.body ?? null });
  if (mode === "network") throw new TypeError("transport failure C:/synthetic/path");
  if (mode === "login") return json({ operator_id: "op-karl", session_token: "a".repeat(43), expires_at_ms: 5 });
  if (mode === "stale") return json({ error: { code: "STALE_STATE" } }, 409);
  if (mode === "precondition")
    return json({ error: { code: "COMMAND_PRECONDITION_FAILED", canonical_error_code: "HEALTH_TRANSITION_INVALID" } }, 409);
  if (mode === "unknown") return json({ error: { code: "SOMETHING_ELSE", detail: "C:/synthetic/path" } }, 409);
  if (mode === "malformed") return new Response("not json", { status: 200 });
  const request = JSON.parse(init.body);
  const flag = mode === "receipt_authority" ? false : true;
  const ref = mode === "receipt_operator" ? "cccmd:op-other:sha256:" + "c".repeat(64) : "cccmd:op-karl:sha256:" + "c".repeat(64);
  if (mode === "receipt_operator" || mode === "receipt_authority") return json({
    schema_version: "1.0.0", status: "COMMITTED", command_ref: ref,
    command_kind: request.command_kind, operator_id: "op-karl", canonical_record_kind: "STRATEGY_RESTRICTION_RECEIPT",
    canonical_record_id: "strategyrestriction:sha256:" + "d".repeat(64), lifecycle_store_head_entry_hash: "e".repeat(64),
    issued_at_ms: request.issued_at_ms, no_product_network: true, no_account_access: true, no_order_authority: true,
    no_gate_c_authority: flag, no_live_authority: true,
  });
  const receipt = {
    schema_version: "1.0.0", status: "COMMITTED", command_ref: "cccmd:op-karl:sha256:" + "c".repeat(64),
    command_kind: request.command_kind, operator_id: "op-karl", canonical_record_kind: "STRATEGY_RESTRICTION_RECEIPT",
    canonical_record_id: "strategyrestriction:sha256:" + "d".repeat(64), lifecycle_store_head_entry_hash: "e".repeat(64),
    issued_at_ms: request.issued_at_ms, no_product_network: true, no_account_access: true, no_order_authority: true,
    no_gate_c_authority: true, no_live_authority: true,
  };
  const invalid = {
    receipt_ref: { command_ref: "cccmd:op-karl:sha256:arbitrary" },
    receipt_kind: { canonical_record_kind: "STRATEGY_HEALTH_RECEIPT" },
    receipt_id: { canonical_record_id: "strategyhealth:sha256:" + "d".repeat(64) },
    receipt_id_digest: { canonical_record_id: "strategyrestriction:sha256:unsafe" },
    receipt_head: { lifecycle_store_head_entry_hash: "not-a-head" },
    receipt_head_newline: { lifecycle_store_head_entry_hash: "e".repeat(64) + "\n" },
    receipt_null_head: { lifecycle_store_head_entry_hash: null },
    receipt_invalid_operator: { operator_id: "op-A", command_ref: "cccmd:op-A:sha256:" + "c".repeat(64) },
  };
  return json({ ...receipt, ...(invalid[mode] ?? {}) });
};
Date.now = () => 1234;
const request = api.newCommandRequest(
  { command_kind: "STRATEGY_PAUSE", strategy_version_id: "strategyversion:sha256:" + "a".repeat(64) }, "b".repeat(64));
out.request = request;
out.frozen = Object.isFrozen(request);
out.retry_constant = api.COMMAND_MUTATION_RETRY;
const attempt = async (name, fn) => {
  calls.length = 0;
  try { out[name] = { ok: await fn(), calls: calls.length, call: calls[0] ?? null }; }
  catch (error) {
    out[name] = { code: error.code, ambiguous: error.ambiguous, canonical: error.canonicalErrorCode, message: error.message,
                  calls: calls.length, call: calls[0] ?? null };
  }
};
mode = "receipt"; await attempt("receipt", () => api.executeCommand("t".repeat(43), request));
mode = "network"; await attempt("network", () => api.executeCommand("t".repeat(43), request));
mode = "stale"; await attempt("stale", () => api.executeCommand("t".repeat(43), request));
mode = "precondition"; await attempt("precondition", () => api.executeCommand("t".repeat(43), request));
mode = "unknown"; await attempt("unknown", () => api.executeCommand("t".repeat(43), request));
mode = "malformed"; await attempt("malformed", () => api.executeCommand("t".repeat(43), request));
mode = "receipt_operator"; await attempt("receipt_operator", () => api.executeCommand("t".repeat(43), request));
mode = "receipt_authority"; await attempt("receipt_authority", () => api.executeCommand("t".repeat(43), request));
for (const name of ["receipt_ref", "receipt_kind", "receipt_id", "receipt_id_digest", "receipt_head", "receipt_head_newline",
                    "receipt_null_head", "receipt_invalid_operator"]) {
  mode = name; await attempt(name, () => api.executeCommand("t".repeat(43), request));
}
mode = "login"; await attempt("login", () => api.loginCommandSession("synthetic-input"));
mode = "receipt"; await attempt("revoke", () => api.revokeCommandSession("t".repeat(43)));
const status = {
  read_only: false, commands_enabled: true, auth_mode: "EPHEMERAL_BEARER_SESSION", session_ttl_seconds: 900,
  active_session: false, supported_commands: ["STRATEGY_PAUSE", "STRATEGY_RESUME", "STRATEGY_QUARANTINE",
  "POLICY_ACTIVATE", "POLICY_REVOKE"], no_product_network: true, no_account_access: true, no_order_authority: true,
  no_gate_c_authority: true, no_live_authority: true,
};
const parse = (body) => { try { return api.parseCommandStatus(body).commands_enabled; } catch (error) { return error.code; } };
out.status = {
  exact: parse(status),
  closed_mock_error: parse({ error: { code: "INTERNAL_ERROR" } }),
  extra: parse({ ...status, session_token: "x" }),
  sixth_command: parse({ ...status, supported_commands: [...status.supported_commands, "PAPER_KILL"] }),
  live_authority: parse({ ...status, no_live_authority: false }),
};
const policy = { policy_id: "portfolioauthoritypolicy:sha256:" + "f".repeat(64), policy_label: "P",
                 effective_from_ns: 1, expires_at_ns: null };
out.policies = {
  missing: api.parseOpsPolicies({}),
  malformed: api.parseOpsPolicies({ policies: [{ policy_id: "free-form" }] }),
  valid: api.parseOpsPolicies({ policies: [policy] }),
};
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def node_behavior(tmp_path_factory):
    """Runs the real api.ts when Node and the locked node_modules are installed; else None."""
    node = shutil.which("node")
    if node is None or not (FRONTEND_ROOT / "node_modules" / "@tanstack" / "react-query").is_dir():
        return None
    harness = tmp_path_factory.mktemp("command_harness") / "harness.mjs"
    harness.write_text(NODE_HARNESS, encoding="utf-8", newline="\n")
    completed = subprocess.run(
        [node, str(harness), str(FRONTEND / "api.ts")],
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    return json.loads(completed.stdout.strip().splitlines()[-1])


# ---------------------------------------------------------------------------
# C01-C03 bootstrap, sessions, routes
# ---------------------------------------------------------------------------


def test_c01_commands_default_off_and_tty_secret_bootstrap_is_closed(
    lab, clock, monkeypatch, tmp_path, capsys
) -> None:
    # Default-off configuration and routes.
    names = [field.name for field in dataclasses.fields(cockpit.CockpitConfig)]
    assert names[-2:] == ["streaming_enabled", "command_auth"]
    assert cockpit.CockpitConfig(None, None).command_auth is None
    legacy = cockpit.CockpitConfig(None, None, None, None, lab.path, None, None, None, False)
    assert legacy.command_auth is None
    for wrong in ("op-karl", SENTINEL, object(), True):
        with pytest.raises(TypeError):
            cockpit.CockpitConfig(None, None, command_auth=wrong)
    with pytest.raises(TypeError):
        commands.CommandAuth(OPERATOR, b"x" * 32)  # only the TTY bootstrap constructs auth
    off = _cockpit(lab)
    status, body = off.status()
    assert status == 200 and body["commands_enabled"] is False and body["active_session"] is False
    _fails(off.login(), "COMMANDS_DISABLED")
    _fails(off.revoke("a" * 43), "COMMANDS_DISABLED")
    _fails(off.execute("a" * 43, _pause(lab)), "COMMANDS_DISABLED")

    # Operator id closure, including ids whose command_ref would not be a safe opaque ref.
    for good in ("op-karl", "op-a", "op-a1_b-c", "op-" + "a" * 31):
        assert commands.validate_operator_id(good) == good
    for bad in ("karl", "op-", "op-Karl", "op--x", "op-" + "a" * 32, "op-a b", "op-a:b", "op-secret1",
                "op-bearer", "op-passwordx", "op-credential", " op-a", None, 1):
        with pytest.raises(commands.CommandBootstrapError) as caught:
            commands.validate_operator_id(bad)
        assert caught.value.code == "OPERATOR_ID_INVALID"

    # Non-TTY fails closed before any secret is read.
    reads: list[str] = []
    with pytest.raises(commands.CommandBootstrapError) as caught:
        commands.bootstrap_command_auth(OPERATOR, is_tty=lambda: False, read_secret=reads.append)
    assert caught.value.code == "TTY_REQUIRED" and reads == []
    assert commands._stdin_is_tty() in (True, False)
    monkeypatch.setattr(commands.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    assert commands._stdin_is_tty() is False
    monkeypatch.setattr(commands.sys, "stdin", None)
    assert commands._stdin_is_tty() is False
    monkeypatch.undo()
    monkeypatch.setattr(commands, "_now_ms", clock)

    # Secret type/length/printability; the raw secret never appears in the failure.
    for bad_secret in ("short", "x" * 31, "x" * 257, "x" * 31 + "\n", "\x00" * 40, None, b"x" * 40):
        with pytest.raises(commands.CommandBootstrapError) as caught:
            commands.bootstrap_command_auth(OPERATOR, is_tty=lambda: True, read_secret=lambda _p, s=bad_secret: s)
        assert caught.value.code == "SECRET_INVALID" and str(caught.value) == "SECRET_INVALID"
    for edge in ("x" * 32, "y" * 256):
        assert commands.bootstrap_command_auth(OPERATOR, is_tty=lambda: True, read_secret=lambda _p, s=edge: s)

    # CLI: argv/environment never carry the secret; the TTY getpass is the only source.
    env_value = "SYNTHETIC-CMD01-ENVIRONMENT-VALUE-" + "e" * 16
    for name in ("COCKPIT_COMMAND_SECRET", "CC_COMMAND_SECRET", "COMMAND_SECRET", "OPERATOR_SECRET",
                 "CC_ENABLE_COMMANDS", "COCKPIT_ENABLE_COMMANDS"):
        monkeypatch.setenv(name, env_value)
    launched: list = []
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=lambda app, **kw: launched.append((app, kw))))
    prompts: list[str] = []

    def fake_getpass(prompt: str) -> str:
        prompts.append(prompt)
        return SENTINEL

    monkeypatch.setattr(getpass, "getpass", fake_getpass)
    base = ["--market-truth-store", str(tmp_path / "m.sqlite3"), "--experiment-registry", str(tmp_path / "r.sqlite3"),
            "--strategy-lifecycle-store", str(lab.path)]
    assert cockpit.main(base) == 0
    assert prompts == []  # no prompt without the explicit flag
    monkeypatch.setattr(commands, "_stdin_is_tty", lambda: False)
    with pytest.raises(SystemExit):
        cockpit.main(base + ["--enable-commands", "--operator-id", OPERATOR])
    assert prompts == []
    monkeypatch.setattr(commands, "_stdin_is_tty", lambda: True)
    for rejected in (
        ["--enable-commands"],
        ["--enable-commands", "--operator-id", "op-Bad"],
        ["--operator-id", OPERATOR],
        ["--enable-commands", "--operator-id", OPERATOR, "--command-secret", SENTINEL],
        ["--enable-commands", "--operator-id", OPERATOR, "--secret", SENTINEL],
        ["--enable-commands=yes", "--operator-id", OPERATOR],
    ):
        with pytest.raises(SystemExit):
            cockpit.main(base + rejected)
    # argparse errors never echo an argv value (review N2): bad int, explicit-argument and ambiguous forms.
    for echoed in (["--port", SENTINEL], ["--enable-commands=" + SENTINEL], ["--enable=" + SENTINEL],
                   ["--operator-id", OPERATOR, SENTINEL]):
        with pytest.raises(SystemExit):
            cockpit.main(base + echoed)
        assert SENTINEL not in capsys.readouterr().err, echoed
    assert cockpit.main(base + ["--enable-commands", "--operator-id", OPERATOR]) == 0
    assert prompts == ["Control Center command secret: "]
    assert [kw for _app, kw in launched] == [{"host": "127.0.0.1", "port": 8000}] * 2
    disabled_app, enabled_app = launched[0][0], launched[1][0]
    disabled = TestClient(disabled_app)
    assert disabled.get("/api/commands/status").json()["commands_enabled"] is False
    enabled = TestClient(enabled_app)
    assert enabled.get("/api/commands/status").json()["commands_enabled"] is True
    assert enabled.post("/api/commands/session", json={"secret": env_value}).json() == _error("AUTH_FAILED")
    login = enabled.post("/api/commands/session", json={"secret": SENTINEL})
    assert login.status_code == 200 and login.json()["operator_id"] == OPERATOR
    captured = capsys.readouterr()
    assert SENTINEL not in captured.out + captured.err and env_value not in captured.out + captured.err

    # Source: no environment, file or argv secret path; only getpass at bootstrap.
    for text in (_source(COCKPIT), _module_code()):
        for banned in ("environ", "getenv", "dotenv", "read_text", "read_bytes", "sys.argv",
                       "--secret", "--command-secret", "--token", "--password"):
            assert banned not in text, banned
    for banned in ("open(", "Path(", "fromfile"):
        assert banned not in _module_code(), banned
    assert _module_code().count("getpass.getpass") == 1
    assert 'parser.add_argument("--enable-commands", action="store_true", default=False)' in _source(COCKPIT)
    assert 'parser.add_argument("--operator-id")' in _source(COCKPIT)


@pytest.mark.parametrize("value", ["SYNTHETIC'ARGV", 'SYNTHETIC"ARGV', 'SYNTHETIC\'"ARGV', "SYNTHETIC\nARGV"])
def test_cli_invalid_value_never_echoes_either_repr_quote_style(value, capsys) -> None:
    parser = cockpit._CockpitArgumentParser()
    parser.add_argument("--port", type=int)
    with pytest.raises(SystemExit) as caught:
        parser.parse_args(["--port", value])
    assert caught.value.code == 2
    output = capsys.readouterr().err
    assert "INVALID_COCKPIT_ARGUMENTS" in output
    assert "SYNTHETIC" not in output and "ARGV" not in output


def test_c02_auth_session_token_ttl_single_session_revoke_and_lockout(lab, clock) -> None:
    assert (commands.SESSION_TTL_SECONDS, commands.MAX_ACTIVE_SESSIONS, commands.SESSION_TOKEN_BYTES,
            commands.MAX_FAILED_LOGINS) == (900, 1, 32, 5)
    auth = _auth()
    c = _cockpit(lab, auth)
    assert c.status()[1]["active_session"] is False
    status, login = c.login()
    assert status == 200 and set(login) == {"operator_id", "session_token", "expires_at_ms"}
    first = login["session_token"]
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", first)
    assert login["expires_at_ms"] == NOW_MS + 900_000 and login["operator_id"] == OPERATOR
    assert c.status()[1]["active_session"] is True
    # The server keeps digests only: neither the token nor the secret is held anywhere in auth.
    held = [getattr(auth, name) for name in commands.CommandAuth.__slots__]
    flat = repr(held) + repr(auth) + repr(cockpit.CockpitConfig(None, None, command_auth=auth))
    assert first not in flat and SENTINEL not in flat
    assert hashlib.sha256(SENTINEL.encode()).hexdigest() not in repr(auth)
    assert repr(auth) == "CommandAuth(operator_id='op-karl')"
    assert _module_code().count("hmac.compare_digest(") == 2
    assert "secrets.token_urlsafe(SESSION_TOKEN_BYTES)" in _module_code()

    # A new login invalidates the prior session (MAX_ACTIVE_SESSIONS == 1).
    second = c.token()
    assert second != first
    _fails(c.execute(first, _pause(lab)), "AUTH_REQUIRED")
    _fails(c.revoke(first), "AUTH_REQUIRED")

    # Unknown, malformed, duplicated or missing bearer headers.
    for headers in ({"Authorization": "Bearer " + "A" * 43}, {"Authorization": second},
                    {"Authorization": "bearer " + second}, {"Authorization": "Bearer " + second + "x"},
                    {"Authorization": "Basic " + second}):
        _fails(c.execute(None, _pause(lab), headers=headers), "AUTH_REQUIRED")
    _fails(c.execute(None, _pause(lab)), "AUTH_REQUIRED")
    duplicated = c.client.post(
        "/api/commands/execute", json=_pause(lab),
        headers=[("Authorization", "Bearer " + second), ("Authorization", "Bearer " + second)],
    )
    assert duplicated.json() == _error("AUTH_REQUIRED")

    # Revoke invalidates the current token; revoke takes no body or query.
    _fails(c.revoke(second, content=b"{}"), "INVALID_COMMAND")
    status, revoked = c.revoke(second)
    assert status == 200 and revoked == {"schema_version": "1.0.0", "status": "SESSION_REVOKED", "active_session": False}
    _fails(c.execute(second, _pause(lab)), "AUTH_REQUIRED")
    _fails(c.revoke(second), "AUTH_REQUIRED")
    assert c.status()[1]["active_session"] is False

    # Expiry: exactly at expires_at_ms the session ends.
    third = c.token()
    clock.value = NOW_MS + 900_000 - 1
    _ok(c.execute(third, _pause(lab, issued=NOW_MS)))
    clock.value = NOW_MS + 900_000
    assert c.status()[1]["active_session"] is False
    _fails(c.execute(third, _pause(lab, issued=NOW_MS)), "SESSION_EXPIRED")
    _fails(c.execute(third, _pause(lab, issued=NOW_MS)), "AUTH_REQUIRED")
    clock.value = NOW_MS

    # Malformed login bodies are INVALID_COMMAND and are not guesses.
    for raw, content_type in ((b'{"secret": 1}', "application/json"), (b'{}', "application/json"),
                              (b'{"secret": "a", "x": 1}', "application/json"), (b"[]", "application/json"),
                              (b"not json", "application/json"), (b'{"secret": "a"}', "text/plain"),
                              (b'{"secret": "a", "secret": "b"}', "application/json")):
        response = c.client.post("/api/commands/session", content=raw, headers={"Content-Type": content_type})
        assert response.json() == _error("INVALID_COMMAND"), raw
    assert c.client.post("/api/commands/session?x=1", json={"secret": SENTINEL}).json() == _error("INVALID_COMMAND")

    # Five failed logins lock auth until process restart; the lock also ends the session.
    fourth = c.token()
    for _ in range(4):
        _fails(c.login(OTHER_SENTINEL), "AUTH_FAILED")
    assert auth.locked is False
    _fails(c.login(OTHER_SENTINEL), "AUTH_FAILED")
    assert auth.locked is True
    _fails(c.login(), "AUTH_LOCKED")
    _fails(c.login(OTHER_SENTINEL), "AUTH_LOCKED")
    _fails(c.execute(fourth, _pause(lab)), "AUTH_REQUIRED")
    assert c.status()[1]["active_session"] is False
    restarted = _cockpit(lab, _auth())  # a new process bootstrap starts unlocked
    assert restarted.login()[0] == 200

    # Review F1: a revoke or replacement login that lands while the body is being read wins.
    racing_auth = _auth()
    racing = _cockpit(lab, racing_auth)
    racing_token = racing.token()
    real_body = cockpit._command_body

    async def revoke_during_read(request, *, json_body):
        body = await real_body(request, json_body=json_body)
        racing_auth.revoke([f"Bearer {racing_token}"])
        return body

    rows = lab.rows()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(cockpit, "_command_body", revoke_during_read)
        _fails(racing.execute(racing_token, _pause(lab, version=lab.b)), "AUTH_REQUIRED")
    assert lab.rows() == rows
    replaced = racing.token()

    async def relogin_during_read(request, *, json_body):
        body = await real_body(request, json_body=json_body)
        racing_auth.login(SENTINEL)
        return body

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(cockpit, "_command_body", relogin_during_read)
        _fails(racing.execute(replaced, _pause(lab, version=lab.b)), "AUTH_REQUIRED")
    assert lab.rows() == rows
    route = _source(COCKPIT)
    route = route[route.index('@app.post("/api/commands/execute")'):route.index("return app")]
    assert route.index("await _command_body(") < route.rindex("auth.authenticate(authorization)")
    # Surrogate-containing secrets never raise; they simply fail.
    assert commands._digest("\ud800") is None
    fresh = _auth()
    with pytest.raises(commands.CommandError) as caught:
        fresh.login("\ud800" * 40)
    assert caught.value.code == "AUTH_FAILED"


def test_c03_cors_and_exact_31_route_surface(lab, clock) -> None:
    c = _cockpit(lab, _auth())
    domain = {route.path: set(route.methods or ()) for route in c.app.routes if route.path.startswith("/api/")}
    assert len(domain) == 31
    assert {path: methods for path, methods in domain.items() if path.startswith("/api/commands")} == COMMAND_ROUTES
    assert [path for path, methods in domain.items() if methods != {"GET"}] == [
        "/api/commands/session", "/api/commands/session/revoke", "/api/commands/execute",
    ]
    (cors,) = [item for item in c.app.user_middleware if item.cls.__name__ == "CORSMiddleware"]
    assert cors.kwargs == {
        "allow_origins": ["http://127.0.0.1:5173", "http://localhost:5173"],
        "allow_methods": ["GET", "POST"],
        "allow_headers": ["Content-Type", "Authorization"],
    }
    preflight = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"}
    allowed = c.client.options("/api/commands/execute", headers={"Origin": "http://127.0.0.1:5173", **preflight})
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert "access-control-allow-credentials" not in allowed.headers
    for origin in ("http://evil.example", "http://127.0.0.1:5174", "null"):
        denied = c.client.options("/api/commands/execute", headers={"Origin": origin, **preflight})
        assert denied.status_code == 400 and "access-control-allow-origin" not in denied.headers, origin
    put = c.client.options("/api/commands/execute", headers={
        "Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "PUT"})
    assert put.status_code == 400
    cookie_header = c.client.options("/api/commands/execute", headers={
        "Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "cookie"})
    assert cookie_header.status_code == 400
    # Exact method closure.
    for path, methods in COMMAND_ROUTES.items():
        for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            if method not in methods:
                assert c.client.request(method, path).status_code == 405, (path, method)
    assert c.status("?x=1") == (400, _error("INVALID_COMMAND"))
    status, body = c.status()
    assert set(body) == STATUS_KEYS and body == {
        "read_only": False, "commands_enabled": True, "auth_mode": "EPHEMERAL_BEARER_SESSION",
        "session_ttl_seconds": 900, "active_session": False, "supported_commands": list(KINDS),
        "no_product_network": True, "no_account_access": True, "no_order_authority": True,
        "no_gate_c_authority": True, "no_live_authority": True,
    }
    # No cookie or ambient browser auth anywhere in the backend.
    for text in (_source(COCKPIT), _module_code()):
        for banned in ("set_cookie", "Set-Cookie", "request.cookies", "allow_credentials", "SessionMiddleware",
                       'allow_origins=["*"]', "allow_origin_regex", "csrf"):
            assert banned not in text, banned


# ---------------------------------------------------------------------------
# C04-C07 request closure, identity, conditional preview/append and exact retry
# ---------------------------------------------------------------------------


def test_c04_command_request_parser_and_confirmation_matrix_fail_closed(lab, clock) -> None:
    valid = {
        "STRATEGY_PAUSE": _pause(lab),
        "STRATEGY_RESUME": _resume(lab, "pause.1"),
        "STRATEGY_QUARANTINE": _quarantine(lab, "NEW"),
        "POLICY_ACTIVATE": _activate(lab, lab.p2, lab.p1),
        "POLICY_REVOKE": _revoke(lab, lab.p1),
    }
    assert tuple(valid) == commands.COMMAND_KINDS == KINDS
    assert commands.CONFIRMATION_PHRASES == PHRASES
    for kind, body in valid.items():
        assert commands.normalize_command_request(dict(body))["command_kind"] == kind
        expected_keys = set(commands.COMMON_FIELDS) | set(commands.TARGET_FIELDS[kind])
        assert set(body) == expected_keys
        for key in expected_keys:
            missing = {k: v for k, v in body.items() if k != key}
            with pytest.raises(commands.CommandError) as caught:
                commands.normalize_command_request(missing)
            assert caught.value.code == "INVALID_COMMAND", (kind, key)
        for extra in ("idempotency_key", "operator_id", "restriction_kind", "max_active_budget_usd",
                      "policy", "evidence_refs", "decision_ref", "created_time_ns"):
            if extra in body:
                continue
            with pytest.raises(commands.CommandError) as caught:
                commands.normalize_command_request({**body, extra: "x"})
            assert caught.value.code == "INVALID_COMMAND", (kind, extra)
        for other_kind, phrase in PHRASES.items():
            if other_kind == kind:
                continue
            with pytest.raises(commands.CommandError) as caught:
                commands.normalize_command_request({**body, "confirmation_phrase": phrase})
            assert caught.value.code == "INVALID_CONFIRMATION"
        for phrase in ("", PHRASES[kind].lower(), PHRASES[kind] + " ", " " + PHRASES[kind], "CONFIRM"):
            with pytest.raises(commands.CommandError) as caught:
                commands.normalize_command_request({**body, "confirmation_phrase": phrase})
            assert caught.value.code == "INVALID_CONFIRMATION"
        with pytest.raises(commands.CommandError) as caught:
            commands.normalize_command_request({**body, "confirmation_phrase": None})
        assert caught.value.code == "INVALID_COMMAND"
    bad_values = {
        "command_kind": ("STRATEGY_PAUSE ", "strategy_pause", "PAPER_KILL", "GATEWAY_DISABLE", "ORDER_CANCEL", 1, None),
        "expected_lifecycle_store_head_entry_hash": ("A" * 64, "a" * 63, "a" * 65, 1, "g" * 64),
        "issued_at_ms": (True, False, -1, 1.5, "1", None, 2**53),
        "strategy_version_id": ("strategyversion:sha256:" + "A" * 64, "x", 1, None),
    }
    for key, values in bad_values.items():
        for value in values:
            with pytest.raises(commands.CommandError) as caught:
                commands.normalize_command_request({**valid["STRATEGY_PAUSE"], key: value})
            assert caught.value.code == "INVALID_COMMAND", (key, value)
    for value in ("Pause.1", "", "1pause", "a" * 129, None):
        with pytest.raises(commands.CommandError):
            commands.normalize_command_request({**valid["STRATEGY_RESUME"], "restriction_key": value})
    for value in ("quarantined", "UNKNOWN", "", None):
        with pytest.raises(commands.CommandError):
            commands.normalize_command_request({**valid["STRATEGY_QUARANTINE"], "previous_health_state": value})
    for value in ("portfolioauthoritypolicy:sha256:" + "z" * 64, "free-form-policy", 7):
        with pytest.raises(commands.CommandError):
            commands.normalize_command_request({**valid["POLICY_ACTIVATE"], "previous_active_policy_id": value})
        with pytest.raises(commands.CommandError):
            commands.normalize_command_request({**valid["POLICY_REVOKE"], "policy_id": value})
    assert commands.normalize_command_request(
        {**valid["POLICY_ACTIVATE"], "previous_active_policy_id": None})["previous_active_policy_id"] is None
    for not_object in ([], "x", 1, None):
        with pytest.raises(commands.CommandError):
            commands.normalize_command_request(not_object)

    # HTTP: closed shapes, body bound, media type, query and session time window; zero writes.
    c = _cockpit(lab, _auth())
    token = c.token()
    before = lab.digest()
    _fails(c.execute(token, {**valid["STRATEGY_PAUSE"], "idempotency_key": "k"}), "INVALID_COMMAND")
    _fails(c.execute(token, {**valid["STRATEGY_PAUSE"], "confirmation_phrase": "CONFIRM-RESUME"}), "INVALID_CONFIRMATION")
    _fails(c.execute(token, None, raw=b'{"command_kind": "STRATEGY_PAUSE", "command_kind": "STRATEGY_PAUSE"}'), "INVALID_COMMAND")
    _fails(c.execute(token, None, raw=b"\xff\xfe"), "INVALID_COMMAND")
    _fails(c.execute(token, None, raw=b'{"issued_at_ms": NaN}'), "INVALID_COMMAND")
    _fails(c.execute(token, None, raw=json.dumps({**valid["STRATEGY_PAUSE"], "pad": "x" * 5000}).encode()), "INVALID_COMMAND")
    _fails(c.execute(token, None, raw=json.dumps(valid["STRATEGY_PAUSE"]).encode(),
                     headers={"Content-Type": "text/plain"}), "INVALID_COMMAND")
    _fails(c.execute(token, valid["STRATEGY_PAUSE"], path="/api/commands/execute?x=1"), "INVALID_COMMAND")
    for issued in (NOW_MS - 1, NOW_MS + 5_001, NOW_MS + 900_000):
        _fails(c.execute(token, _pause(lab, issued=issued)), "INVALID_COMMAND")
    clock.value = NOW_MS + 10_000
    _ok(c.execute(token, _pause(lab, issued=NOW_MS + 15_000)))  # +5 s positive skew is permitted
    clock.value = NOW_MS
    assert lab.rows() == 9  # eight seed records plus the one skewed-but-valid pause
    lab_digest_after = lab.digest()
    assert lab_digest_after != before
    # A command can never be written without auth, even with a perfect body.
    _fails(c.execute(None, _pause(lab, version=lab.b)), "AUTH_REQUIRED")
    assert lab.digest() == lab_digest_after


def test_c05_command_identity_is_deterministic_and_secret_free(lab, clock) -> None:
    request = commands.normalize_command_request(_quarantine(lab, "NEW"))
    first = commands.command_identity(OPERATOR, request)
    again = commands.command_identity(OPERATOR, commands.normalize_command_request(_quarantine(lab, "NEW")))
    assert first == again
    expected = hashlib.sha256(
        json.dumps({"command": request, "operator_id": OPERATOR}, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert first.command_digest == expected
    assert canonical_json_bytes({"command": request, "operator_id": OPERATOR}).decode() == json.dumps(
        {"command": request, "operator_id": OPERATOR}, sort_keys=True, separators=(",", ":"))
    assert first.command_ref == f"cccmd:{OPERATOR}:sha256:{expected}"
    assert M.opaque_ref(first.command_ref) == first.command_ref
    assert first.created_time_ns == NOW_MS * 1_000_000
    assert commands.command_identity("op-other", request).command_ref != first.command_ref
    for change in ({"issued_at_ms": NOW_MS + 1}, {"expected_lifecycle_store_head_entry_hash": "0" * 64},
                   {"previous_health_state": "HEALTHY"}):
        changed = commands.normalize_command_request({**_quarantine(lab, "NEW"), **change})
        assert commands.command_identity(OPERATOR, changed).command_digest != first.command_digest
    # Request-bound previous state makes the rebuilt canonical record byte-identical after commit.
    record = commands.build_command_record(request, first)
    c = _cockpit(lab, _auth())
    token = c.token()
    receipt = _ok(c.execute(token, _quarantine(lab, "NEW")))
    rebuilt = commands.build_command_record(request, commands.command_identity(OPERATOR, request))
    assert rebuilt == record and canonical_json_bytes(rebuilt.to_mapping()) == canonical_json_bytes(record.to_mapping())
    assert receipt["canonical_record_id"] == record.record_id and receipt["command_ref"] == first.command_ref
    activate = commands.normalize_command_request(_activate(lab, lab.p2, lab.p1))
    identity = commands.command_identity(OPERATOR, activate)
    assert commands.build_command_record(activate, identity) == commands.build_command_record(activate, identity)
    # Overflowing the canonical time domain fails closed.
    huge = {**request, "issued_at_ms": 2**53 - 1}
    with pytest.raises(commands.CommandError) as caught:
        commands.command_identity(OPERATOR, huge)
    assert caught.value.code == "INVALID_COMMAND"
    # Identity carries no secret, token or path.
    serialized = json.dumps(dataclasses.asdict(first))
    assert SENTINEL not in serialized and str(lab.path) not in serialized and "Bearer" not in serialized
    assert "idempotency" not in _module_code().lower()


def test_c06_conditional_preview_is_no_write_and_stale_head_is_no_write(lab, clock) -> None:
    request = commands.normalize_command_request(_pause(lab))
    identity = commands.command_identity(OPERATOR, request)
    record = commands.build_command_record(request, identity)
    head = lab.head()
    before = lab.digest()
    preview = S.preview_strategy_lifecycle_record(lab.path, record, head)
    assert preview.status == "PREVIEW_READY" and preview.error_codes == ()
    assert preview.store_head_entry_hash == head and preview.record_id == record.record_id
    assert preview.before_snapshot.store_head_entry_hash == head
    assert preview.before_snapshot.restrictions_of(lab.a.strategy_version_id) == ()
    assert preview.candidate_snapshot.restrictions_of(lab.a.strategy_version_id) == (record,)
    assert preview.candidate_snapshot.total_rows == preview.before_snapshot.total_rows + 1
    assert lab.digest() == before
    stale = "0" * 64
    assert S.preview_strategy_lifecycle_record(lab.path, record, stale).status == "STALE_HEAD"
    result = S.conditional_append_strategy_lifecycle_record(lab.path, record, stale)
    assert (result.status, result.error_codes, result.store_head_entry_hash) == ("STALE_HEAD", (), None)
    assert lab.digest() == before
    # HTTP: a stale expected head for a new mutation is STALE_STATE with zero writes.
    c = _cockpit(lab, _auth())
    token = c.token()
    _fails(c.execute(token, _pause(lab, head=stale)), "STALE_STATE")
    _fails(c.execute(token, _pause(lab, head=None)), "STALE_STATE")
    assert lab.digest() == before
    committed = _ok(c.execute(token, _pause(lab)))
    # The preview's candidate head is exactly the head the conditional append committed.
    assert committed["lifecycle_store_head_entry_hash"] == lab.head() == preview.candidate_snapshot.store_head_entry_hash
    assert lab.rows() == preview.candidate_snapshot.total_rows


def test_c07_exact_retry_wins_before_stale_head_and_appends_once(lab, clock, monkeypatch) -> None:
    c = _cockpit(lab, _auth())
    token = c.token()
    pause_body = _pause(lab)
    pause = _ok(c.execute(token, pause_body))
    snapshot = lab.snapshot()
    (applied,) = snapshot.restrictions_of(lab.a.strategy_version_id)
    flows = [
        (pause_body, pause),
    ]
    lab.advance()
    resume_body = _resume(lab, applied.restriction_key, issued=NOW_MS + 1)
    flows.append((resume_body, _ok(c.execute(token, resume_body))))
    lab.advance()
    quarantine_body = _quarantine(lab, "NEW", issued=NOW_MS + 2)
    flows.append((quarantine_body, _ok(c.execute(token, quarantine_body))))
    lab.advance()
    revoke_body = _revoke(lab, lab.p1, issued=NOW_MS + 3)
    flows.append((revoke_body, _ok(c.execute(token, revoke_body))))
    lab.advance()
    activate_body = _activate(lab, lab.p1, None, issued=NOW_MS + 4)
    flows.append((activate_body, _ok(c.execute(token, activate_body))))
    assert [receipt["command_kind"] for _body, receipt in flows] == list(KINDS[:3]) + ["POLICY_REVOKE", "POLICY_ACTIVATE"]
    lab.advance()  # every committed request now carries a stale expected head

    # Mutable-state preconditions must never run on an exact retry.
    def forbidden(*_args):
        raise AssertionError("precondition evaluated on an exact retry")

    for kind in KINDS:
        monkeypatch.setitem(commands._CHECKS, kind, forbidden)
    appended: list = []
    real_append = commands.conditional_append_strategy_lifecycle_record
    monkeypatch.setattr(commands, "conditional_append_strategy_lifecycle_record",
                        lambda *args: (appended.append(args), real_append(*args))[1])
    rows = lab.rows()
    for body, receipt in flows:
        status, replay = c.execute(token, body)  # the lost-response retry: exact same request
        assert status == 200, replay
        assert replay["status"] == "IDEMPOTENT_REPLAY"
        for key in ("command_ref", "canonical_record_id", "canonical_record_kind", "command_kind", "issued_at_ms"):
            assert replay[key] == receipt[key], key
        assert replay["lifecycle_store_head_entry_hash"] == lab.head()
    assert lab.rows() == rows and appended == []
    monkeypatch.undo()
    monkeypatch.setattr(commands, "_now_ms", clock)
    # A different request with the same stale head is STALE_STATE and writes nothing.
    for body, _receipt in flows:
        fresh = {**body, "issued_at_ms": body["issued_at_ms"] + 100}
        _fails(c.execute(token, fresh), "STALE_STATE")
    assert lab.rows() == rows
    # The store primitive also resolves the duplicate before the head comparison (race path).
    request = commands.normalize_command_request(pause_body)
    record = commands.build_command_record(request, commands.command_identity(OPERATOR, request))
    replay = S.conditional_append_strategy_lifecycle_record(lab.path, record, "f" * 64)
    assert replay.status == "IDEMPOTENT_REPLAY" and replay.record_id == record.record_id
    assert lab.rows() == rows


# ---------------------------------------------------------------------------
# C08-C12 the five canonical commands
# ---------------------------------------------------------------------------


def test_c08_strategy_pause_uses_canonical_pause_restriction(lab, clock) -> None:
    c = _cockpit(lab, _auth())
    token = c.token()
    before = lab.snapshot()
    body = _pause(lab)
    receipt = _ok(c.execute(token, body))
    after = lab.snapshot()
    assert after.total_rows == before.total_rows + 1
    (restriction,) = after.restrictions_of(lab.a.strategy_version_id)
    request = commands.normalize_command_request(body)
    identity = commands.command_identity(OPERATOR, request)
    assert restriction.restriction_receipt_id == receipt["canonical_record_id"]
    assert receipt["canonical_record_kind"] == "STRATEGY_RESTRICTION_RECEIPT"
    assert restriction.action == "APPLY" and restriction.restriction_kind == "PAUSE_NEW_EXPOSURE"
    assert restriction.restriction_key == "cc.pause." + identity.command_digest[:24]
    assert restriction.max_active_budget_usd is None and restriction.evidence_refs == ()
    assert restriction.decision_ref == receipt["command_ref"] == identity.command_ref
    assert restriction.created_time_ns == NOW_MS * 1_000_000
    # Nothing else in canonical state changed.
    for name in ("active_policy_id", "families", "strategy_versions", "policies",
                 "current_health_by_strategy_version", "current_allocation_by_strategy_version"):
        assert getattr(after, name) == getattr(before, name), name
    # Pause cannot stack another active PAUSE_NEW_EXPOSURE.
    _fails(c.execute(token, _pause(lab, issued=NOW_MS + 1)), "COMMAND_PRECONDITION_FAILED", pure=True)
    lab.append(_restriction(lab.b, "pause.manual", "PAUSE_NEW_EXPOSURE"))
    _fails(c.execute(token, _pause(lab, version=lab.b, issued=NOW_MS + 2)), "COMMAND_PRECONDITION_FAILED", pure=True)
    # Pause of a retired or unknown version fails closed.
    lab.append(_health(lab.b, "NEW", "RETIRED", t=80))
    rows = lab.rows()
    lab.append(_restriction(lab.b, "pause.manual", "PAUSE_NEW_EXPOSURE", action="CLEAR", t=81))
    _fails(c.execute(token, _pause(lab, version=lab.b, issued=NOW_MS + 3)), "COMMAND_PRECONDITION_FAILED", pure=True)
    unknown = _body("STRATEGY_PAUSE", lab, strategy_version_id="strategyversion:sha256:" + "9" * 64, issued=NOW_MS + 4)
    _fails(c.execute(token, unknown), "COMMAND_PRECONDITION_FAILED", "REFERENCE_INVALID")
    assert lab.rows() == rows + 1


def test_c09_strategy_resume_only_clears_exact_pause_and_uses_target_plus_aggregate_capacity(
    lab, clock, monkeypatch
) -> None:
    c = _cockpit(lab, _auth())
    token = c.token()
    _ok(c.execute(token, _pause(lab)))
    (pause,) = lab.snapshot().restrictions_of(lab.a.strategy_version_id)
    # Non-pause restrictions can never be cleared by resume.
    lab.append(_restriction(lab.a, "paper.only", "PAPER_ONLY"))
    lab.append(_restriction(lab.a, "cap.low", "ACTIVE_BUDGET_CAP", cap="75"))
    for key in ("paper.only", "cap.low", "missing.key"):
        # The exact CLEAR candidate is PAUSE_NEW_EXPOSURE with no cap, so canonical replay rejects it.
        _fails(c.execute(token, _resume(lab, key, issued=NOW_MS + 1)), "COMMAND_PRECONDITION_FAILED",
               "RESTRICTION_TRANSITION_INVALID")
    # Target still PAPER_ONLY with an active positive allocation: its own invalidity blocks resume.
    _fails(c.execute(token, _resume(lab, pause.restriction_key, issued=NOW_MS + 2)), "COMMAND_PRECONDITION_FAILED",
           pure=True)
    lab.append(_restriction(lab.a, "paper.only", "PAPER_ONLY", action="CLEAR", t=61))
    # Unrelated strategy-local blockers (B quarantined with its own positive allocation) never deadlock.
    lab.append(_allocation(lab.b, lab.p1, budget="40", t=110))
    lab.append(_health(lab.b, "NEW", "QUARANTINED", t=120))
    capacity_calls: list = []
    real = commands.evaluate_portfolio_capacity
    monkeypatch.setattr(commands, "evaluate_portfolio_capacity",
                        lambda snapshot, at: (capacity_calls.append((snapshot, at)), real(snapshot, at))[1])
    rows = lab.rows()
    receipt = _ok(c.execute(token, _resume(lab, pause.restriction_key, issued=NOW_MS + 3)))
    assert len(capacity_calls) == 1
    snapshot, at = capacity_calls[0]
    assert at == (NOW_MS + 3) * 1_000_000
    assert snapshot.restrictions_of(lab.a.strategy_version_id) == lab.snapshot().restrictions_of(lab.a.strategy_version_id)
    assert real(snapshot, at).strategy_result(lab.b.strategy_version_id).reason_codes == ("HEALTH_BLOCKS_ACTIVE_RISK",)
    after = lab.snapshot()
    assert after.total_rows == rows + 1
    remaining = {item.restriction_key: item.restriction_kind for item in after.restrictions_of(lab.a.strategy_version_id)}
    assert remaining == {"cap.low": "ACTIVE_BUDGET_CAP"}  # cap untouched; only the exact pause cleared
    assert receipt["canonical_record_kind"] == "STRATEGY_RESTRICTION_RECEIPT"
    monkeypatch.undo()
    monkeypatch.setattr(commands, "_now_ms", clock)
    # Target ACTIVE_BUDGET_CAP below its reservation: target invalidity blocks.
    lab.append(_restriction(lab.a, "pause.again", "PAUSE_NEW_EXPOSURE", t=130))
    lab.append(_restriction(lab.a, "cap.tight", "ACTIVE_BUDGET_CAP", cap="10", t=131))
    _fails(c.execute(token, _resume(lab, "pause.again", issued=NOW_MS + 4)), "COMMAND_PRECONDITION_FAILED",
           pure=True)
    lab.append(_restriction(lab.a, "cap.tight", "ACTIVE_BUDGET_CAP", cap="10", action="CLEAR", t=132))
    # True global reasons block: synthetic aggregate overflow, then a real revoked/expired policy.
    fake = PortfolioCapacityResult(
        status=PORTFOLIO_CAPACITY_REJECTED, reason_codes=("EXPLORATORY_POOL_EXCEEDED",), at_time_ns=0,
        policy_id=lab.p1.policy_id, exploratory_active_usd="0", validated_active_usd="0", mature_active_usd="0",
        total_active_usd="0", active_real_risk_strategy_count=0,
        strategy_results=(StrategyCapacityResult(lab.a.strategy_version_id, PORTFOLIO_CAPACITY_VALID, (), "EXPLORATORY_LIVE", "50"),),
    )
    monkeypatch.setattr(commands, "evaluate_portfolio_capacity", lambda *_a: fake)
    _fails(c.execute(token, _resume(lab, "pause.again", issued=NOW_MS + 5)), "COMMAND_PRECONDITION_FAILED",
           pure=True)
    local_only = dataclasses.replace(fake, reason_codes=("HEALTH_BLOCKS_ACTIVE_RISK",), strategy_results=(
        StrategyCapacityResult(lab.a.strategy_version_id, PORTFOLIO_CAPACITY_VALID, (), "EXPLORATORY_LIVE", "50"),
        StrategyCapacityResult(lab.b.strategy_version_id, PORTFOLIO_CAPACITY_REJECTED, ("HEALTH_BLOCKS_ACTIVE_RISK",),
                               "EXPLORATORY_LIVE", "40"),
    ))
    monkeypatch.setattr(commands, "evaluate_portfolio_capacity", lambda *_a: local_only)
    rows = lab.rows()
    _ok(c.execute(token, _resume(lab, "pause.again", issued=NOW_MS + 6)))
    assert lab.rows() == rows + 1
    monkeypatch.undo()
    monkeypatch.setattr(commands, "_now_ms", clock)
    lab.append(_restriction(lab.a, "pause.third", "PAUSE_NEW_EXPOSURE", t=140))
    lab.append(_policy_receipt("REVOKE", lab.p1, lab.p1.policy_id, 150))
    _fails(c.execute(token, _resume(lab, "pause.third", issued=NOW_MS + 7)), "COMMAND_PRECONDITION_FAILED",
           pure=True)
    # Quarantined or retired targets can never be resumed.
    lab.append(_restriction(lab.b, "pause.b", "PAUSE_NEW_EXPOSURE", t=160))
    _fails(c.execute(token, _resume(lab, "pause.b", version=lab.b, issued=NOW_MS + 8)), "COMMAND_PRECONDITION_FAILED")
    lab.append(_health(lab.b, "QUARANTINED", "RETIRED", t=170))
    _fails(c.execute(token, _resume(lab, "pause.b", version=lab.b, issued=NOW_MS + 9)), "COMMAND_PRECONDITION_FAILED")
    source = _module_code()
    assert source.count("evaluate_portfolio_capacity(candidate, at_time_ns)") == 1
    assert 'restriction_kind=_PAUSE' in source and "PAPER_ONLY" not in source and "ACTIVE_BUDGET_CAP" not in source


def test_c10_strategy_quarantine_is_canonical_and_authority_reducing(lab, clock) -> None:
    c = _cockpit(lab, _auth())
    token = c.token()
    rows = lab.rows()
    body = _quarantine(lab, "NEW")
    receipt = _ok(c.execute(token, body))
    snapshot = lab.snapshot()
    assert snapshot.total_rows == rows + 1
    assert snapshot.health_of(lab.b.strategy_version_id) == "QUARANTINED"
    assert receipt["canonical_record_kind"] == "STRATEGY_HEALTH_RECEIPT"
    request = commands.normalize_command_request(body)
    record = commands.build_command_record(request, commands.command_identity(OPERATOR, request))
    assert record.record_id == receipt["canonical_record_id"]
    assert (record.previous_health_state, record.new_health_state, record.decision_ref, record.evidence_refs,
            record.created_time_ns) == ("NEW", "QUARANTINED", receipt["command_ref"], (), NOW_MS * 1_000_000)
    # Cannot re-quarantine; previous-state binding must equal current health.
    _fails(c.execute(token, _quarantine(lab, "QUARANTINED", issued=NOW_MS + 1)), "COMMAND_PRECONDITION_FAILED",
           "HEALTH_TRANSITION_INVALID")
    _fails(c.execute(token, _quarantine(lab, "NEW", issued=NOW_MS + 2)), "COMMAND_PRECONDITION_FAILED")
    _fails(c.execute(token, _quarantine(lab, "HEALTHY", version=lab.a, issued=NOW_MS + 3)), "COMMAND_PRECONDITION_FAILED")
    lab.append(_health(lab.a, "NEW", "WATCH", t=80))
    _ok(c.execute(token, _quarantine(lab, "WATCH", version=lab.a, issued=NOW_MS + 4)))
    # RETIRED is never revived or quarantined.
    lab.append(_health(lab.b, "QUARANTINED", "RETIRED", t=90))
    _fails(c.execute(token, _quarantine(lab, "RETIRED", issued=NOW_MS + 5)), "COMMAND_PRECONDITION_FAILED",
           "HEALTH_TRANSITION_INVALID")
    assert lab.snapshot().health_of(lab.b.strategy_version_id) == "RETIRED"
    # Quarantine never touches allocations, policies or restrictions (authority reducing only).
    after = lab.snapshot()
    assert after.current_allocation_by_strategy_version == snapshot.current_allocation_by_strategy_version
    assert after.active_policy_id == snapshot.active_policy_id == lab.p1.policy_id


def _capacity(lab: Lab, top: tuple[str, ...], local: tuple[str, ...]) -> PortfolioCapacityResult:
    return PortfolioCapacityResult(
        status=PORTFOLIO_CAPACITY_REJECTED if top else PORTFOLIO_CAPACITY_VALID, reason_codes=top, at_time_ns=0,
        policy_id=lab.p2.policy_id, exploratory_active_usd="0", validated_active_usd="0", mature_active_usd="0",
        total_active_usd="0", active_real_risk_strategy_count=0,
        strategy_results=(StrategyCapacityResult(
            lab.a.strategy_version_id, PORTFOLIO_CAPACITY_REJECTED if local else PORTFOLIO_CAPACITY_VALID,
            local, "EXPLORATORY_LIVE", "50"),),
    )


def test_c11_policy_activate_requires_existing_policy_and_structurally_safe_capacity(
    tmp_path, clock, monkeypatch
) -> None:
    lab = _seed(_empty_lab(tmp_path, "inactive"), activate=False)
    future = lab.append(_policy("Future envelope", effective=10**18, created=12))
    expired = lab.append(_policy("Expired envelope", effective=12, expires=13, created=12))
    c = _cockpit(lab, _auth())
    token = c.token()
    unknown = _body("POLICY_ACTIVATE", lab, policy_id="portfolioauthoritypolicy:sha256:" + "9" * 64,
                    previous_active_policy_id=None)
    _fails(c.execute(token, unknown), "COMMAND_PRECONDITION_FAILED")
    _fails(c.execute(token, _activate(lab, future, None, issued=NOW_MS + 1)), "COMMAND_PRECONDITION_FAILED", pure=True)
    _fails(c.execute(token, _activate(lab, expired, None, issued=NOW_MS + 2)), "COMMAND_PRECONDITION_FAILED")
    _fails(c.execute(token, _activate(lab, lab.p1, lab.p2, issued=NOW_MS + 3)), "COMMAND_PRECONDITION_FAILED")
    rows = lab.rows()
    receipt = _ok(c.execute(token, _activate(lab, lab.p1, None, issued=NOW_MS + 4)))
    assert lab.rows() == rows + 1 and lab.snapshot().active_policy_id == lab.p1.policy_id
    assert receipt["canonical_record_kind"] == "PORTFOLIO_POLICY_RECEIPT"
    # Already active, and previous binding must match exactly.
    _fails(c.execute(token, _activate(lab, lab.p1, lab.p1, issued=NOW_MS + 5)), "COMMAND_PRECONDITION_FAILED",
           "POLICY_TRANSITION_INVALID")
    _fails(c.execute(token, _activate(lab, lab.p2, None, issued=NOW_MS + 6)), "COMMAND_PRECONDITION_FAILED")
    # Real ALLOCATION_POLICY_MISMATCH blocks; allocations are never migrated.
    allocation = lab.append(_allocation(lab.a, lab.p1, t=100))
    _fails(c.execute(token, _activate(lab, lab.p2, lab.p1, issued=NOW_MS + 7)), "COMMAND_PRECONDITION_FAILED", pure=True)
    assert lab.snapshot().allocation_of(lab.a.strategy_version_id) == allocation
    # Real safety-reducing local blocker (quarantined target) does not deadlock re-activation.
    lab.append(_health(lab.a, "NEW", "QUARANTINED", t=120))
    lab.append(_policy_receipt("REVOKE", lab.p1, lab.p1.policy_id, 130))
    rows = lab.rows()
    _ok(c.execute(token, _activate(lab, lab.p1, None, issued=NOW_MS + 8)))
    assert lab.rows() == rows + 1
    assert lab.snapshot().allocation_of(lab.a.strategy_version_id) == allocation
    # Real ACTIVE_BUDGET_CAP_EXCEEDED blocks re-activation.
    lab.append(_policy_receipt("REVOKE", lab.p1, lab.p1.policy_id, 140))
    lab.append(_health(lab.a, "QUARANTINED", "DEGRADED", t=141))
    lab.append(_restriction(lab.a, "cap.tight", "ACTIVE_BUDGET_CAP", cap="10", t=142))
    _fails(c.execute(token, _activate(lab, lab.p1, None, issued=NOW_MS + 9)), "COMMAND_PRECONDITION_FAILED", pure=True)
    lab.append(_restriction(lab.a, "cap.tight", "ACTIVE_BUDGET_CAP", cap="10", action="CLEAR", t=143))
    # Classification matrix over the canonical evaluator result (exactly one evaluation).
    matrix = {
        ((), ()): True,
        ((), ("HEALTH_BLOCKS_ACTIVE_RISK",)): True,
        ((), ("RESTRICTION_BLOCKS_ACTIVE_RISK",)): True,
        ((), ("HEALTH_BLOCKS_ACTIVE_RISK", "RESTRICTION_BLOCKS_ACTIVE_RISK")): True,
        ((), ("ALLOCATION_POLICY_MISMATCH",)): False,
        ((), ("ALLOCATION_INVALID",)): False,
        ((), ("PER_STRATEGY_LIMIT_EXCEEDED",)): False,
        ((), ("ACTIVE_BUDGET_CAP_EXCEEDED",)): False,
        ((), ("HEALTH_BLOCKS_ACTIVE_RISK", "PER_STRATEGY_LIMIT_EXCEEDED")): False,
        (("EXPLORATORY_POOL_EXCEEDED",), ()): False,
        (("VALIDATED_POOL_EXCEEDED",), ()): False,
        (("MATURE_POOL_EXCEEDED",), ()): False,
        (("GLOBAL_CAPITAL_LIMIT_EXCEEDED",), ()): False,
        (("MAX_ACTIVE_STRATEGIES_EXCEEDED",), ()): False,
        (("POLICY_NOT_EFFECTIVE",), ()): False,
        (("INTERNAL_VALIDATION_FAILED",), ()): False,
    }
    issued = NOW_MS + 100
    for (top_only, local), allowed in matrix.items():
        calls: list = []
        result = _capacity(lab, tuple(sorted(set(top_only) | set(local))), local)
        monkeypatch.setattr(commands, "evaluate_portfolio_capacity", lambda s, t, r=result: (calls.append(t), r)[1])
        issued += 1
        rows = lab.rows()
        outcome = c.execute(token, _activate(lab, lab.p1, None, issued=issued))
        assert len(calls) == 1 and calls[0] == issued * 1_000_000, (top_only, local, outcome)
        if allowed:
            _ok(outcome)
            assert lab.rows() == rows + 1
            # A distinct revoke receipt each time (an identical one would be an idempotent replay).
            lab.append(_policy_receipt("REVOKE", lab.p1, lab.p1.policy_id, issued))
            assert lab.snapshot().active_policy_id is None
        else:
            _fails(outcome, "COMMAND_PRECONDITION_FAILED", pure=True)
            assert lab.rows() == rows
    source = _module_code()
    assert '_SAFETY_REDUCING_LOCAL_REASONS = frozenset(\n    {"HEALTH_BLOCKS_ACTIVE_RISK", "RESTRICTION_BLOCKS_ACTIVE_RISK"}\n)' in source
    for forbidden in ("build_portfolio_authority_policy", "build_strategy_risk_allocation", "StrategyRiskAllocation("):
        assert forbidden not in source, forbidden


def test_c12_policy_revoke_requires_exact_active_policy(lab, clock) -> None:
    c = _cockpit(lab, _auth())
    token = c.token()
    _fails(c.execute(token, _revoke(lab, lab.p2)), "COMMAND_PRECONDITION_FAILED")
    rows = lab.rows()
    body = _revoke(lab, lab.p1, issued=NOW_MS + 1)
    receipt = _ok(c.execute(token, body))
    assert lab.rows() == rows + 1 and lab.snapshot().active_policy_id is None
    request = commands.normalize_command_request(body)
    record = commands.build_command_record(request, commands.command_identity(OPERATOR, request))
    assert (record.action, record.policy_id, record.previous_active_policy_id, record.human_authorization_ref) == (
        "REVOKE", lab.p1.policy_id, lab.p1.policy_id, receipt["command_ref"])
    _fails(c.execute(token, _revoke(lab, lab.p1, issued=NOW_MS + 2)), "COMMAND_PRECONDITION_FAILED")
    _fails(c.execute(token, _revoke(lab, lab.p2, issued=NOW_MS + 3)), "COMMAND_PRECONDITION_FAILED")
    # Revoke leaves the policy catalogue and allocations untouched.
    snapshot = lab.snapshot()
    assert [p.policy_id for p in snapshot.policies] == [lab.p1.policy_id, lab.p2.policy_id]
    assert snapshot.allocation_of(lab.a.strategy_version_id).policy_id == lab.p1.policy_id


# ---------------------------------------------------------------------------
# C13 outward safety, boundaries and network
# ---------------------------------------------------------------------------


def test_c13_receipts_and_errors_never_echo_secret_token_path_or_raw_exception(
    lab, clock, monkeypatch, tmp_path
) -> None:
    auth = _auth()
    c = _cockpit(lab, auth)
    c.login(OTHER_SENTINEL)
    token = c.token()
    c.status()
    receipt = _ok(c.execute(token, _pause(lab)))
    assert set(receipt) == RECEIPT_KEYS
    assert all(receipt[flag] is True for flag in commands.NON_AUTHORITY)
    c.execute(token, _pause(lab, issued=NOW_MS + 1))
    c.execute(token, _pause(lab, head="0" * 64, issued=NOW_MS + 2))
    c.execute(token, {**_pause(lab), "confirmation_phrase": SENTINEL})
    c.execute(token, {**_pause(lab), "strategy_version_id": SENTINEL})
    c.execute(token, None, raw=("{" + SENTINEL).encode())

    def exploding(*_args):
        raise RuntimeError(f"{SENTINEL} {tmp_path} Traceback sqlite3.OperationalError")

    monkeypatch.setattr(commands, "preview_strategy_lifecycle_record", exploding)
    assert c.execute(token, _pause(lab, issued=NOW_MS + 3)) == (500, _error("INTERNAL_ERROR"))
    monkeypatch.undo()
    monkeypatch.setattr(commands, "_now_ms", clock)
    # Unreadable or tampered sources map to SOURCE_UNAVAILABLE without detail.
    garbage = tmp_path / "garbage.sqlite3"
    garbage.write_bytes(b"not sqlite " + str(tmp_path).encode())
    for path in (garbage, tmp_path / "missing.sqlite3", None):
        other = Cockpit(path, auth)
        assert other.execute(token, _pause(lab, issued=NOW_MS + 4)) == (503, _error("SOURCE_UNAVAILABLE"))
        c.responses.extend(other.responses)
    c.revoke(token)
    c.execute(token, _pause(lab))
    for status, body in c.responses:
        strings = list(_walk_strings(body))
        text = json.dumps(body)
        assert SENTINEL not in text and OTHER_SENTINEL not in text
        assert str(tmp_path) not in text and str(lab.path) not in text
        for banned in ("Traceback", "sqlite", "Exception", "Error(", "\\", "secret", "password"):
            assert banned not in text, (banned, text)
        if isinstance(body, dict) and "error" in body:
            assert set(body) == {"error"}
            assert set(body["error"]) <= {"code", "canonical_error_code"}
            assert body["error"]["code"] in commands.COMMAND_ERROR_CODES
            if "canonical_error_code" in body["error"]:
                assert body["error"]["canonical_error_code"] in M.ERROR_CODES
        elif isinstance(body, dict) and "session_token" not in body:
            assert token not in strings
    # Exceptions and reprs are payload-free.
    error = commands.CommandError("NOT_A_CODE")
    assert error.code == "INTERNAL_ERROR" and str(error) == "INTERNAL_ERROR"
    assert commands.CommandError("COMMAND_PRECONDITION_FAILED", SENTINEL).canonical_error_code == "INTERNAL_VALIDATION_FAILED"
    assert SENTINEL not in repr(auth) + repr(commands.command_status(auth))
    # Docs and package artifacts never carry the sentinel.
    for doc in (CONTRACT, ROOT / "docs" / "status_entries" / "S10-CC-CMD-01.md"):
        assert SENTINEL not in _source(doc)


def test_c13_command_module_owner_and_non_authority_boundary() -> None:
    source = _source(MODULE)
    tree = ast.parse(source)
    modules = {
        node.module if isinstance(node, ast.ImportFrom) else alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert modules == {
        "__future__", "dataclasses", "getpass", "hashlib", "hmac", "re", "secrets", "sys", "time",
        "pathlib", "typing", "src.strategy_lifecycle", "src.strategy_lifecycle.models",
        "src.strategy_lifecycle.store",
    }
    store_names = {
        alias.name for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "src.strategy_lifecycle.store"
        for alias in node.names
    }
    assert store_names == {"conditional_append_strategy_lifecycle_record", "preview_strategy_lifecycle_record"}
    code = _module_code()
    for forbidden in (
        "sqlite3", "subprocess", "socket", "urllib", "requests", "httpx", "websocket", "asyncio", "threading",
        "paper_trading", "execution_gateway", "exploratory_gate_c", "execution_feasibility", "live_orchestration",
        "research_runtime", "hermes", "data_layer",
        "initialize_strategy_lifecycle_store", "open(", "write_text", "write_bytes", "environ", "getenv",
        "place_order", "create_order", "submit_order", "post_order", "sign", "GateC", "LiveOrch", "PaperEngine",
        "queue", "while ", "sleep", "retry(",
    ):
        assert forbidden not in code, forbidden
    # The legacy unconditional append is never used for commands.
    assert not re.search(r"(?<!conditional_)append_strategy_lifecycle_record\(", code)
    # Every command maps to exactly one existing canonical lifecycle builder.
    for builder in ("build_strategy_restriction_receipt", "build_strategy_health_receipt",
                    "build_portfolio_policy_receipt"):
        assert builder in code
    assert code.count("conditional_append_strategy_lifecycle_record(") == 1
    assert code.count("preview_strategy_lifecycle_record(") == 1
    # The cockpit reaches commands only through this module; the store's legacy append is unchanged.
    cockpit_source = _source(COCKPIT)
    assert "from src import operator_cockpit_commands as commands" in cockpit_source
    # No direct lifecycle import (and so no lifecycle mutation) from the cockpit module itself.
    assert "from src.strategy_lifecycle" not in cockpit_source and "import strategy_lifecycle" not in cockpit_source


def test_c13_zero_external_product_network(lab, clock, monkeypatch) -> None:
    attempts: list = []

    def forbidden(*args, **kwargs):
        attempts.append(args)
        raise AssertionError("network attempted")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(http.client.HTTPConnection, "connect", forbidden)
    c = _cockpit(lab, _auth())
    token = c.token()
    _ok(c.execute(token, _pause(lab)))
    _ok(c.execute(token, _quarantine(lab, "NEW", issued=NOW_MS + 1)))
    _ok(c.execute(token, _revoke(lab, lab.p1, issued=NOW_MS + 2)))
    c.revoke(token)
    assert attempts == []


# ---------------------------------------------------------------------------
# C14-C16 frontend and Storybook
# ---------------------------------------------------------------------------


def _function(source: str, name: str) -> str:
    section = source[source.index(f"function {name}("):]
    return section[: section.index("\n}\n")]


def _api_command_section() -> str:
    api_source = _source(FRONTEND / "api.ts")
    return api_source[api_source.index("// S10-CC-CMD-01 protected commands."):]


def test_frontend_pending_response_cannot_cross_session_epoch(tmp_path) -> None:
    """Run the actual provider with deterministic hooks and deferred transport promises."""
    node = shutil.which("node")
    if node is None or not (FRONTEND_ROOT / "node_modules" / "@tanstack" / "react-query").is_dir():
        pytest.skip("locked frontend Node environment unavailable")
    provider = _function(_source(FRONTEND / "app.tsx"), "CommandSessionProvider") + "\n}\n"
    provider = provider.replace(
        "return <CommandContext.Provider value={controller}>{children}</CommandContext.Provider>;",
        "return controller;",
    )
    source = tmp_path / "provider.tsx"
    source.write_text(provider, encoding="utf-8")
    harness = tmp_path / "provider.mjs"
    harness.write_text(r'''
import fs from "node:fs";
import { stripTypeScriptTypes } from "node:module";
const compiled = stripTypeScriptTypes(fs.readFileSync(process.argv[2], "utf8"));
const factory = new Function("env", "with (env) { " + compiled + "; return CommandSessionProvider; }");
const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => { resolve=a; reject=b; });
                        return { promise, resolve, reject }; };
const out = {};
for (const scenario of ["late_success", "late_error", "foreign_operator", "late_unlock"]) {
  const slots = [], epoch = { current: 0 }; let cursor=0, pending=deferred(), login=deferred();
  class CommandApiError extends Error { constructor(code) { super(code); this.code=code; } }
  const env = {
    useQueryClient: () => ({ invalidateQueries: () => undefined }),
    useQuery: () => ({ data: { commands_enabled: true } }),
    useState: (initial) => { const i=cursor++; if (!(i in slots)) slots[i]=initial;
                            return [slots[i], (value) => { slots[i]=value; }]; },
    useRef: () => epoch, useMemo: (fn) => fn(),
    commandStatusQuery: { queryKey: [] }, COMMAND_REREAD_FAMILIES: ["strategies","ops"],
    familyKey: (family) => [family], SESSION_ENDING_CODES: ["AUTH_REQUIRED","SESSION_EXPIRED","COMMANDS_DISABLED"],
    loginCommandSession: async () => scenario === "late_unlock" ? login.promise :
       ({ operatorId: "op-karl", token: "synthetic", expiresAtMs: 900 }),
    revokeCommandSession: async () => undefined,
    executeCommand: async () => pending.promise,
    CommandApiError, toCommandError: (error) => error,
  };
  const Provider=factory(env); const render=() => { cursor=0; return Provider({ children: null }); };
  let controller=render();
  if (scenario === "late_unlock") {
    const unlock=controller.unlock("synthetic");
    await render().lock();
    login.resolve({ operatorId:"op-karl", token:"synthetic", expiresAtMs:900 });
    await unlock;
    out[scenario] = { posture: render().posture, receipt: render().lastReceipt };
    continue;
  }
  await controller.unlock("synthetic"); controller=render();
  const command=controller.run({});
  if (scenario !== "foreign_operator") {
    await controller.lock(); await render().unlock("synthetic");
  }
  if (scenario === "late_error") pending.reject(new CommandApiError("AUTH_REQUIRED"));
  else pending.resolve({ operator_id: scenario === "foreign_operator" ? "op-other" : "op-karl" });
  const result=await command;
  out[scenario] = { posture:render().posture, receipt:render().lastReceipt, code:result.error?.code };
}
console.log(JSON.stringify(out));
''', encoding="utf-8")
    completed = subprocess.run(
        [node, str(harness), str(source)],
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    for scenario in ("late_success", "late_error", "foreign_operator"):
        assert result[scenario]["posture"] == "Unlocked"
        assert result[scenario]["receipt"] is None
    assert result["late_success"]["code"] == "AUTH_REQUIRED"
    assert result["foreign_operator"]["code"] == "MALFORMED_RESPONSE"
    assert result["late_unlock"]["posture"] == "Locked" and result["late_unlock"]["receipt"] is None


def _app_command_section() -> str:
    app_source = _source(FRONTEND / "app.tsx")
    start = app_source.index("// S10-CC-CMD-01 protected command surface.")
    return app_source[start: app_source.index("// S10-CC-STREAM-01: the single centralized auto-refresh transport.")]


def test_c14_frontend_command_token_is_memory_only_and_mutations_never_auto_retry(node_behavior) -> None:
    api_source = _source(FRONTEND / "api.ts")
    app_source = _source(FRONTEND / "app.tsx")
    combined = api_source + app_source
    for banned in ("localStorage", "sessionStorage", "indexedDB", "document.cookie", "cookie", "Cookie",
                   "useMutation", "setTimeout", "setInterval", "retry: true", "setQueryData", "sendBeacon",
                   "serviceWorker", "navigator.credentials", "window.location", "searchParams", "URLSearchParams",
                   "history.push", "error.message"):
        assert banned not in combined, banned
    assert api_source.count("retry: false,") == 1  # the unchanged conservative query default
    assert "export const COMMAND_MUTATION_RETRY = false;" in api_source
    assert api_source.count('credentials: "omit"') == 2
    transport = _function(api_source, "postCommand")
    assert transport.count("fetch(") == 1 and 'method: "POST"' in transport and 'cache: "no-store"' in transport
    for loop in ("for (", "while (", ".then(", "retry"):
        assert loop not in transport, loop
    assert api_source.count("fetch(") == 2  # getJson + postCommand only
    # The raw token never enters query keys/data, URLs or storage; it lives in provider state only.
    login = _function(api_source, "loginCommandSession")
    assert api_source.count("session_token") == login.count("session_token") and "session_token" not in app_source
    provider = _function(app_source, "CommandSessionProvider")
    assert app_source.count(".value.token") == provider.count(".value.token") == 2
    assert "useState<{ value: CommandSession; epoch: number } | null>(null)" in provider
    assert app_source.count("executeCommand(") == provider.count("executeCommand(") == 1
    assert app_source.count("loginCommandSession(") == provider.count("loginCommandSession(") == 1
    assert app_source.count("revokeCommandSession(") == provider.count("revokeCommandSession(") == 1
    assert 'queryKey: ["cc", "commands", "status"] as const' in api_source
    unlock = _function(app_source, "UnlockCommands")
    assert 'useState("")' in unlock and 'setSecret("");' in unlock and 'type="password"' in unlock
    # Exact same-request retry only: the request is minted once and reused unchanged.
    request_factory = _function(api_source, "newCommandRequest")
    assert "Object.freeze(" in request_factory and request_factory.count("Date.now()") == 1
    assert api_source.count("Date.now()") == 1 and app_source.count("Date.now") == 0
    action = _function(app_source, "CommandAction")
    assert action.count("submit(newCommandRequest(") == 1 and "submit(request)" in action
    assert "epoch === controller.sessionEpoch" in action and "error.ambiguous" in action
    if node_behavior is not None:
        request = node_behavior["request"]
        assert node_behavior["frozen"] is True and node_behavior["retry_constant"] is False
        assert request == {
            "command_kind": "STRATEGY_PAUSE", "strategy_version_id": "strategyversion:sha256:" + "a" * 64,
            "expected_lifecycle_store_head_entry_hash": "b" * 64, "issued_at_ms": 1234,
            "confirmation_phrase": "CONFIRM-PAUSE",
        }
        receipt = node_behavior["receipt"]
        assert receipt["calls"] == 1 and receipt["ok"]["status"] == "COMMITTED"
        call = receipt["call"]
        assert call["url"] == "/api/commands/execute" and call["method"] == "POST"
        assert call["credentials"] == "omit" and call["cache"] == "no-store"
        assert call["headers"] == {"Accept": "application/json", "Content-Type": "application/json",
                                   "Authorization": "Bearer " + "t" * 43}
        assert json.loads(call["body"]) == request
        network = node_behavior["network"]
        assert (network["code"], network["ambiguous"], network["calls"], network["message"]) == (
            "NETWORK_UNAVAILABLE", True, 1, "NETWORK_UNAVAILABLE")
        assert node_behavior["stale"]["code"] == "STALE_STATE" and node_behavior["stale"]["ambiguous"] is False
        assert node_behavior["precondition"]["canonical"] == "HEALTH_TRANSITION_INVALID"
        assert node_behavior["unknown"]["code"] == "INTERNAL_ERROR" and node_behavior["unknown"]["calls"] == 1
        assert node_behavior["malformed"]["code"] == "MALFORMED_RESPONSE"
        # Review N3: a receipt with a foreign command_ref or a false authority flag is rejected.
        assert node_behavior["receipt_operator"]["code"] == "MALFORMED_RESPONSE"
        assert node_behavior["receipt_authority"]["code"] == "MALFORMED_RESPONSE"
        for name in ("receipt_ref", "receipt_kind", "receipt_id", "receipt_id_digest", "receipt_head", "receipt_head_newline",
                     "receipt_null_head", "receipt_invalid_operator"):
            assert node_behavior[name]["code"] == "MALFORMED_RESPONSE", name
        login = node_behavior["login"]
        assert login["calls"] == 1 and "Authorization" not in login["call"]["headers"]
        assert login["ok"] == {"operatorId": "op-karl", "token": "a" * 43, "expiresAtMs": 5}
        revoke = node_behavior["revoke"]
        assert revoke["call"]["body"] is None and revoke["call"]["headers"]["Authorization"] == "Bearer " + "t" * 43


def test_c15_frontend_controls_are_exact_and_no_execution_live_or_hermes_actions_exist(node_behavior) -> None:
    api_source = _source(FRONTEND / "api.ts")
    app_source = _source(FRONTEND / "app.tsx")
    section = _app_command_section()
    assert re.findall(r'COMMAND_KINDS = \[\s*"([A-Z_]+)",\s*"([A-Z_]+)",\s*"([A-Z_]+)",\s*"([A-Z_]+)",\s*"([A-Z_]+)",\s*\]',
                      api_source) == [KINDS]
    labels = re.findall(r'<CommandAction\s[^>]*?label=(?:"([^"]+)"|\{`([^`]+)`\})', section)
    assert [a or b for a, b in labels] == [
        "Pause new exposure", "Resume · clear pause ${restriction.restriction_key}", "Quarantine",
        "Activate selected policy", "Revoke active policy",
    ]
    for control in ("Unlock", "Lock commands", "Submit command", "Retry same request", "Close review", "Done",
                    "Dismiss", "Review again"):
        assert control in section, control
    for banned in (">Arm<", ">Halt<", ">Trade<", ">Cancel<", ">Reconcile<", ">Run<", ">Reassess<", ">Approve<",
                   ">Allocate<", ">Kill<", ">Disable gateway<", ">Acknowledge<", ">Edit policy<", ">Create policy<",
                   "Run Hermes", "PAPER_ONLY", "ACTIVE_BUDGET_CAP", "allocation editor"):
        assert banned not in section, banned
    # Command head comes from a fresh OPS HTTP read only; never from SSE or the strategy detail.
    assert "readCommandHead: () => queryClient.fetchQuery({ ...opsPortfolioQuery, staleTime: 0 })" in section
    assert "head: fresh.lifecycle_store_head_entry_hash" in section
    assert "lifecycle_store_head_entry_hash" not in _function(app_source, "StrategyCommands")
    for transport in ("EventSource", "streamStatusQuery", "StreamRefreshController", "parseStreamEvent", "STREAM_"):
        assert transport not in section, transport
    # Policy choices come only from the verified catalogue; no free-form policy id input.
    policy = _function(app_source, "PolicyCommands")
    assert "parseOpsPolicies(portfolio)" in policy and "parseOpsPolicies(fresh)" in policy
    assert policy.count("<input") == 0 and policy.count("<select") == 1
    assert section.count("<input") == 2  # the bootstrap secret and the confirmation phrase only
    # Resume is offered only for an exact visible PAUSE_NEW_EXPOSURE restriction.
    strategy = _function(app_source, "StrategyCommands")
    assert "restriction.restriction_kind === PAUSE_KIND && restriction.max_active_budget_usd === null" in section
    assert strategy.count("activePauses(item)") == 1 and strategy.count("activePauses(detail)") == 2
    # Review F2: target fields and displayed state come from a fresh strategy-detail read at review time.
    assert "queryClient.fetchQuery({ ...strategyDetailQuery(versionId), staleTime: 0 })" in strategy
    assert "previous_health_state: current }" in strategy and "state: strategyState(detail)" in strategy
    assert "previous_health_state: health" not in strategy
    assert 'const PAUSE_KIND = "PAUSE_NEW_EXPOSURE";' in section
    # Controls render only when unlocked; outcomes always re-read strategies and ops over HTTP.
    assert strategy.count('if (controller.posture !== "Unlocked") return null;') == 1
    assert policy.count('if (controller.posture !== "Unlocked") return null;') == 1
    assert 'export const COMMAND_REREAD_FAMILIES: readonly QueryFamily[] = ["strategies", "ops"];' in api_source
    provider = _function(app_source, "CommandSessionProvider")
    assert "invalidateQueries({ queryKey: familyKey(family) })" in provider and "} finally {\n          reread();" in provider
    # The last sanitized receipt stays visible after the re-read (session-scoped, no token).
    assert provider.count("setLastReceipt(receipt);") == 1
    assert provider.count("setLastReceipt(null);") == 2  # review N1: reset on unlock and lock
    assert "lastReceipt: session === null ? null : lastReceipt," in provider
    assert app_source.count("<LastCommandReceipt />") == 2
    receipt_view = _function(app_source, "LastCommandReceipt")
    assert ".token" not in receipt_view and "session_token" not in receipt_view and "Bearer" not in receipt_view
    assert "canonical_record_id" in receipt_view
    # Global shell posture strings.
    for posture in ('"Commands: Locked"', '"Commands: Disabled"', "<>Commands: Unlocked · {controller.operatorId}</>"):
        assert posture in section, posture
    assert app_source.count("<CommandPosture />") == 1 and app_source.count("<CommandSessionProvider>") == 1
    # Stale state requires a fresh review; confirmation phrase gating before submit.
    assert 'error?.code === "STALE_STATE" ? "Review again"' in section
    assert "disabled={stage.typed !== phrase}" in section
    if node_behavior is not None:
        assert node_behavior["status"]["exact"] is True
        assert node_behavior["status"]["sixth_command"] == "MALFORMED_RESPONSE"
        assert node_behavior["status"]["live_authority"] == "MALFORMED_RESPONSE"
        assert node_behavior["policies"]["missing"] is None and node_behavior["policies"]["malformed"] is None
        assert node_behavior["policies"]["valid"][0]["policy_label"] == "P"


def test_c16_storybook_command_states_are_synthetic_and_network_closed(node_behavior) -> None:
    stories = _source(FRONTEND / "foundation.stories.tsx")
    for banned in ("/api/commands", "session_token", "Bearer", "commandStatus", "CommandSession", "secret"):
        assert banned not in stories, banned
    preview = _source(FRONTEND_ROOT / ".storybook" / "preview.ts")
    assert 'http.all("/api/*"' in preview and '{ error: { code: "INTERNAL_ERROR" } }, { status: 500 }' in preview
    assert "print.error()" in preview
    # A missing command-status mock leaves commands unavailable with no mutation affordance.
    provider = _function(_source(FRONTEND / "app.tsx"), "CommandSessionProvider")
    assert "const available = status.data?.commands_enabled === true;" in provider
    assert "if (!available) return COMMANDS_UNAVAILABLE;" in provider
    section = _app_command_section()
    assert 'posture: "Disabled",' in section[section.index("const COMMANDS_UNAVAILABLE"):]
    if node_behavior is not None:
        assert node_behavior["status"]["closed_mock_error"] == "MALFORMED_RESPONSE"
        assert node_behavior["status"]["extra"] == "MALFORMED_RESPONSE"
