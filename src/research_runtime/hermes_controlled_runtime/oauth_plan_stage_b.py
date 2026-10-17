"""One attended ChatGPT-plan OAuth Stage B inference (S10-HERMES-AUTO-02-REAL-01-ACTIVATION).

The single approved route is the official Sign in with ChatGPT plan-usage flow: the user's
OAuth access token as bearer to ``POST https://api.openai.com/v1/responses`` (never an API
key, never ChatGPT's internal backend). Everything that touches a credential or the network
runs in one pinned Hermes v0.21.3 child per phase (``login`` / ``preflight`` / ``dispatch``):

* ``login``      -- PKCE S256 + state + nonce, loopback ``127.0.0.1`` callback, the user's own
  browser consent, code exchange, JWKS ID-token validation, credentials stored atomically in a
  user-scoped directory OUTSIDE the repository.
* ``preflight``  -- at most one pre-inference token refresh, granted-scope/audience checks and the
  account model catalogue ``GET /v1/models`` (discovery, not entitlement proof).
* ``dispatch``   -- native ``AIAgent(enabled_toolsets=[])`` builds the request with every socket
  denied; a pre-send hook re-checks the final post-SDK body; then exactly one POST over an
  ``api.openai.com:443``-only socket allowlist, SDK ``max_retries=0``, no refresh, no fallback.

This parent module never reads a token; child reports carry digests and labels only. The
journal admits ONE dispatch per namespace, reserved before the child starts: any timeout,
crash, error or replay consumes it. Only a witnessed real-mode result with a provider-reported
response id, model and usage is ``REAL_ORIGIN_VERIFIED`` -- still provider-reported, not a
cryptographic attestation. ``max_output_tokens`` is unsupported on this route and is never
sent; the 16 KiB output and 45 s stream limits are client-side, not provider quotas.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
from pathlib import Path
import re

from src.strategy_lifecycle.models import strict_json_loads

from . import real_provider_stage_b as real01
from . import tool_free_stage_b as stage_b

ROUTE = dict(provider="custom", api_mode="codex_responses", base_url="https://api.openai.com/v1",
             model="gpt-6.1-sol")
API_HOST = "api.openai.com"
RESPONSES_PATH = "/v1/responses"
MODELS_PATH = "/v1/models"
AUTH_HOST = "auth.openai.com"
ISSUER = "https://auth.openai.com"
AUTHORIZE_URL = ISSUER + "/api/accounts/authorize"
TOKEN_URL = ISSUER + "/api/accounts/oauth/token"
JWKS_URL = ISSUER + "/.well-known/jwks.json"
RESOURCE = "https://api.openai.com/v1"
REQUIRED_SCOPES = frozenset({"openid", "profile", "email", "offline_access", "resource.invoke",
                             "chatgpt.tokens.use.direct"})
PLAN_SCOPE = "chatgpt.tokens.use.direct"
AGENT_NAME_HINT = "polymarket-strategy-lab Hermes Stage B"
TRANSPORT_REAL = "OAUTH_PLAN_HTTP"
TRANSPORT_MOCK = "OAUTH_MOCK_TRANSPORT"
PLAN_USAGE_ELIGIBLE = "PLAN_USAGE_ELIGIBLE"
PLAN_USAGE_UNVERIFIED = "PLAN_USAGE_UNVERIFIED"
OAUTH_AUTHENTICATED_HTTP = "OAUTH_AUTHENTICATED_HTTP"
REAL_ORIGIN_VERIFIED = "REAL_ORIGIN_VERIFIED"
REAL_TRANSPORT_UNVERIFIED = "REAL_TRANSPORT_OBSERVED_MODEL_OR_USAGE_UNVERIFIED"
REAL_ORIGIN_UNVERIFIED = real01.REAL_ORIGIN_UNVERIFIED
VALID_OUTPUT = stage_b.VALID_OUTPUT
MAX_REQUEST_INPUT_BYTES = 2_048  # the Responses `input` (user model input), UTF-8; instructions are fixed and digest-bound
MAX_OUTPUT_BYTES = stage_b.MAX_OUTPUT_BYTES  # client-side capture cap, not a provider token cap
STREAM_TIMEOUT_S = 45
MIN_TOKEN_SECONDS = 180  # dispatch never refreshes
# Preflight refreshes inside this margin, so a token that passed preflight still has
# >= REFRESH_MARGIN_S - MAX_ELIGIBILITY_AGE (300 s) > MIN_TOKEN_SECONDS left at dispatch.
REFRESH_MARGIN_S = 1_200
MAX_ELIGIBILITY_AGE_NS = 900_000_000_000
REQUEST_ID_PREFIX = "oauthplan:sha256:"
RECORD_ID_PREFIX = "oauthplanorigin:sha256:"
ELIGIBILITY_PREFIX = "oauthplaneligibility:sha256:"
INSTRUCTIONS = (
    "You are the Stage B opportunity chooser for a synthetic research menu. Reply with exactly one JSON "
    "object and nothing else. Always include action (NO_TRADE, PAUSE, REASSESS or TRADE), proof_level "
    "\"SYNTHETIC_ONLY\", and information_cutoff_ns, produced_at_ns and expires_at_ns copied unchanged from "
    "the input. For TRADE also include candidate_id and strategy_version_id of one menu item; "
    "hermes_assessment_id, context_sha256 and active_policy_id copied from that item's lineage entry; side "
    "\"BUY\"; execution_style \"PASSIVE_MAKER\"; order_type \"GTC\"; requested_shares and price_limit as "
    "decimal strings; post_only true; gtd_expiration_unix_s null. NO_TRADE is valid. You have no tools.")
# Final post-SDK body: the pinned native codex_responses keys only (official preview rules).
BODY_REQUIRED = frozenset({"input", "instructions", "model", "store", "stream"})
BODY_ALLOWED = BODY_REQUIRED | {"include", "prompt_cache_key", "reasoning"}
UNSUPPORTED_FIELDS = frozenset({
    "background", "conversation", "max_output_tokens", "max_tool_calls", "metadata", "moderation",
    "multi_agent", "prompt", "prompt_cache_retention", "safety_identifier", "temperature", "top_logprobs",
    "top_p", "truncation", "user", "previous_response_id", "tools", "tool_choice", "parallel_tool_calls",
    "service_tier"})
_INCLUDE_ALLOWED = {"reasoning.encrypted_content"}
_OUTPUT_TYPES_ALLOWED = {"message", "reasoning"}
_CHILD_SCHEMA = "oauth-plan-child-v1"
_ATTESTATION = {"purchased_credits_disabled": True, "model_visible_in_chatgpt": True,
                "source": "OPERATOR_ATTESTATION"}
_REPO_ROOT = Path(__file__).resolve().parents[3]

# Executed ONLY inside the pinned Hermes virtualenv child (``python -I -B -c``); spec on stdin.
_CHILD_SOURCE = r'''
import base64, hashlib, json, os, secrets, socket, sys, threading, time, urllib.parse, urllib.request
spec = json.loads(sys.stdin.buffer.read())
MODE, PHASE = spec["mode"], spec["phase"]
C = spec["constants"]
attempts, calls, allowed_hosts, allowed_ips, loopback = [], [], set(), set(), [None]
_getaddrinfo, _connect = socket.getaddrinfo, socket.socket.connect
def _deny(host, port):
    attempts.append([str(host)[:64], port if type(port) is int else str(port)[:16], False])
    raise OSError("network denied")
def guarded_getaddrinfo(host, port, *a, **k):
    if MODE == "mock" and host == "127.0.0.1" and port == loopback[0]:
        return _getaddrinfo(host, port, *a, **k)
    if str(host) not in allowed_hosts or port != 443:
        _deny(host, port)
    infos = _getaddrinfo(host, port, *a, **k)
    allowed_ips.update(info[4][0] for info in infos)
    attempts.append([str(host)[:64], port, True])
    return infos
def guarded_connect(self, address, *a, **k):
    host, port = tuple(address)[:2] if isinstance(address, tuple) else (address, None)
    if (MODE == "mock" and host == "127.0.0.1" and port == loopback[0]) or (host in allowed_ips and port == 443):
        return _connect(self, address, *a, **k)
    _deny(host, port)
socket.getaddrinfo = guarded_getaddrinfo
socket.socket.connect = guarded_connect
socket.socket.connect_ex = guarded_connect
sys.path.insert(0, os.getcwd())
import httpx, jwt
CRED = spec["credential_dir"]
def sha(data):
    return hashlib.sha256(data).hexdigest()
def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")
def label(value):
    return str(value)[:64] if value is not None else None
class Blocked(Exception):
    pass
def read(name):
    path = os.path.join(CRED, name)
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as stream:
        return json.loads(stream.read())
def write(name, value):  # atomic replace; the directory is user-scoped, never the repository
    os.makedirs(CRED, exist_ok=True)
    path, tmp = os.path.join(CRED, name), os.path.join(CRED, name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(json.dumps(value).encode("utf-8"))
    os.replace(tmp, path)
mock = spec.get("mock") or {}
mock_state = {}
def mock_handler(request):
    host, path = request.url.host, request.url.path
    if host == C["auth_host"] and path == "/.well-known/jwks.json":
        return httpx.Response(200, json={"keys": [mock_state["jwk"]]})
    if host == C["auth_host"] and path == "/api/accounts/oauth/token":
        form = dict(urllib.parse.parse_qsl(request.content.decode("ascii")))
        token = dict(mock.get("token") or {})
        if token.pop("status", 200) != 200:
            return httpx.Response(400, json={"error": "invalid_grant"})
        claims = dict(iss=C["issuer"], aud=form.get("client_id"), sub="mock-subject", nonce=mock_state.get("nonce"),
                      iat=int(time.time()), exp=int(time.time()) + 3600)
        claims.update(token.pop("id_claims", {}))
        body = dict(access_token="mock-access." + b64url(canon(dict(aud=C["resource"], iss=C["issuer"],
                    client_id=form.get("client_id"), scope=token.get("scope", " ".join(C["scopes"])),
                    exp=int(time.time()) + 3600))) + ".sig", refresh_token="mock-refresh", token_type="Bearer",
                    expires_in=3600, scope=" ".join(C["scopes"]))
        body.update(token)
        body["id_token"] = jwt.encode(claims, mock_state["key"], algorithm="RS256", headers={"kid": "mock"})
        return httpx.Response(200, json=body)
    if host == C["api_host"] and path == C["models_path"]:
        models = mock.get("models", {"status": 200, "body": {"models": []}})
        return httpx.Response(models["status"], json=models["body"])
    if host == C["api_host"] and path == C["responses_path"]:
        scenario = mock["responses"]
        if scenario["kind"] == "raise":
            raise getattr(httpx, scenario["error"])("mock transport error", request=request)
        if scenario["kind"] == "http":
            return httpx.Response(scenario["status"], json={"error": {"code": scenario.get("code"), "message": "mock"}})
        data = "".join("event: %s\ndata: %s\n\n" % (e.get("type", ""), json.dumps(e)) for e in scenario["events"])
        return httpx.Response(200, headers={"content-type": "text/event-stream", "x-request-id": "req_mock"},
                              content=data.encode("utf-8"))
    return httpx.Response(404, json={})
def on_response(response):
    request = response.request
    calls.append([request.method, request.url.host, request.url.path, response.status_code])
def client(timeout, request_hooks=()):
    kwargs = dict(timeout=httpx.Timeout(timeout), trust_env=False, follow_redirects=False,
                  event_hooks={"request": list(request_hooks), "response": [on_response]})
    if MODE == "mock":
        kwargs["transport"] = httpx.MockTransport(mock_handler)
    return httpx.Client(verify=True, **kwargs)
def jwt_payload(token):
    try:
        part = token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
    except Exception:
        return {}
def save_tokens(record, tok, scopes):
    record.update(access_token=tok["access_token"], refresh_token=tok.get("refresh_token", record.get("refresh_token")),
                  token_type=tok.get("token_type"), expires_at=int(time.time()) + int(tok["expires_in"]),
                  scopes=sorted(scopes), saved_at=int(time.time()))
    write("credential.json", record)
def token_fields_ok(tok):
    return (type(tok) is dict and type(tok.get("access_token")) is str and type(tok.get("expires_in")) is int
            and str(tok.get("token_type", "")).lower() == "bearer")
def phase_login(report):
    host = read("host_id.json") or {"ext_agent_host_id": "urn:uuid:" + __import__("uuid").uuid4().__str__()}
    write("host_id.json", host)
    registration = read("registration.json") or {}
    client_id = registration.get("client_id") or "dynamic_agent_client"
    from http.server import BaseHTTPRequestHandler, HTTPServer
    received, done = {}, threading.Event()
    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            parts = urllib.parse.urlsplit(self.path)
            if parts.path != "/auth/callback":
                self.send_response(404)
                self.end_headers()
                return
            received.update(urllib.parse.parse_qs(parts.query))
            body = b"<html><body>Sign-in received. You may close this tab.</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            done.set()
        def log_message(self, *args):
            pass
    class Listener(HTTPServer):
        allow_reuse_address = False  # Windows SO_REUSEADDR would let another socket share the port
        def server_bind(self):
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            HTTPServer.server_bind(self)
    try:
        server = Listener(("127.0.0.1", 1455), Callback)
    except OSError:
        server = Listener(("127.0.0.1", 0), Callback)
    loopback[0] = server.server_address[1]
    redirect = "http://127.0.0.1:%d/auth/callback" % loopback[0]
    state, nonce, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    params = dict(client_id=client_id, response_type="code", redirect_uri=redirect, scope=" ".join(C["scopes"]),
                  resource=C["resource"], state=state, nonce=nonce, code_challenge_method="S256",
                  code_challenge=b64url(hashlib.sha256(verifier.encode("ascii")).digest()),
                  ext_agent_host_id=host["ext_agent_host_id"])
    if client_id == "dynamic_agent_client":
        params["agent_name_hint"] = C["agent_name_hint"]
    url = C["authorize_url"] + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    report["registration"] = "NEW" if client_id == "dynamic_agent_client" else "RETURNING"
    try:
        if MODE == "mock":
            from cryptography.hazmat.primitives.asymmetric import rsa
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
            mock_state.update(key=key, jwk=dict(jwk, kid="mock", use="sig", alg="RS256"), nonce=nonce)
            reply = dict(code="mock-code", state=state, client_id="oaiapp_mock")
            reply.update(mock.get("callback") or {})
            reply = {k: v for k, v in reply.items() if v is not None}
            urllib.request.urlopen(redirect + "?" + urllib.parse.urlencode(reply), timeout=10).read()
        else:
            import webbrowser
            sys.stderr.write("Opening the system browser for Sign in with ChatGPT...\n")
            if not webbrowser.open(url):
                raise Blocked("BROWSER_OPEN_FAILED")
        if not done.wait(spec["login_wait_s"]):
            raise Blocked("CALLBACK_TIMEOUT")
    finally:
        server.shutdown()
        server.server_close()
    def one(key):
        values = received.get(key) or []
        if len(values) > 1:
            raise Blocked("CALLBACK_AMBIGUOUS")
        return values[0] if values else None
    if one("state") != state:
        raise Blocked("STATE_MISMATCH")
    if one("error"):
        raise Blocked("CONSENT_DENIED" if one("error") == "access_denied" else "AUTHORIZATION_ERROR")
    issued, code = one("client_id"), one("code")
    if client_id == "dynamic_agent_client":
        if not issued or issued == "dynamic_agent_client":
            raise Blocked("REGISTRATION_INCOMPLETE")
    elif issued not in (None, client_id):
        raise Blocked("CLIENT_ID_MISMATCH")
    issued = issued or client_id
    if not code:
        raise Blocked("CODE_MISSING")
    allowed_hosts.add(C["auth_host"])
    with client(30) as http:
        response = http.post(C["token_url"], data=dict(grant_type="authorization_code", client_id=issued, code=code,
                             code_verifier=verifier, redirect_uri=redirect, resource=C["resource"]))
        if response.status_code != 200:
            report["token_status"] = response.status_code
            raise Blocked("TOKEN_EXCHANGE_FAILED")
        tok = response.json()
        if not token_fields_ok(tok) or type(tok.get("id_token")) is not str:
            raise Blocked("TOKEN_RESPONSE_INVALID")
        kid = jwt.get_unverified_header(tok["id_token"]).get("kid")
        keys = [k for k in http.get(C["jwks_url"]).json().get("keys", []) if k.get("kid") == kid]
        if len(keys) != 1:
            raise Blocked("ID_TOKEN_KEY_UNKNOWN")
        try:
            claims = jwt.decode(tok["id_token"], key=jwt.PyJWK(keys[0]).key, algorithms=["RS256"], audience=issued,
                                issuer=C["issuer"], leeway=60, options={"require": ["exp", "iat", "iss", "aud", "sub"]})
        except Exception:
            raise Blocked("ID_TOKEN_INVALID")
        if claims.get("nonce") != nonce:
            raise Blocked("ID_TOKEN_NONCE_MISMATCH")
    if registration.get("subject") not in (None, claims["sub"]):
        raise Blocked("ACCOUNT_MISMATCH")
    scopes = set(str(tok.get("scope", "")).split())
    write("registration.json", dict(client_id=issued, subject=claims["sub"]))
    record = dict(issuer=C["issuer"], subject=claims["sub"], client_id=issued, id_token=tok["id_token"],
                  ext_agent_host_id=host["ext_agent_host_id"])
    save_tokens(record, tok, scopes)
    report.update(scopes_granted=sorted(scopes & set(C["scopes"])), id_token_valid=True,
                  client_id_sha256=sha(issued.encode("utf-8")))
def load_credential():
    record = read("credential.json")
    if type(record) is not dict or type(record.get("access_token")) is not str:
        raise Blocked("CREDENTIAL_MISSING")
    return record
def access_facts(report, record):
    claims = jwt_payload(record["access_token"])
    report.update(token_seconds_remaining=int(record["expires_at"] - time.time()),
                  scopes_granted=sorted(set(str(claims.get("scope", "")).split()) & set(C["scopes"])),
                  access_audience_ok=claims.get("aud") == C["resource"], access_issuer_ok=claims.get("iss") == C["issuer"],
                  client_match=claims.get("client_id") == record.get("client_id"),
                  client_id_sha256=sha(str(record.get("client_id")).encode("utf-8")))
def phase_preflight(report):
    record = load_credential()
    report["refreshed"] = False
    if record["expires_at"] - time.time() < spec["refresh_margin_s"]:
        allowed_hosts.add(C["auth_host"])
        with client(30) as http:
            response = http.post(C["token_url"], data=dict(grant_type="refresh_token", client_id=record["client_id"],
                                 refresh_token=record.get("refresh_token"), resource=C["resource"]))
        if response.status_code != 200 or not token_fields_ok(response.json()):
            report["refresh_status"] = response.status_code
            raise Blocked("REFRESH_FAILED")
        tok = response.json()
        save_tokens(record, tok, set(str(tok.get("scope", "")).split()))
        report["refreshed"] = True
    access_facts(report, record)
    allowed_hosts.add(C["api_host"])
    with client(30) as http:
        response = http.get("https://" + C["api_host"] + C["models_path"],
                            headers={"Authorization": "Bearer " + record["access_token"]})
    report["models_status"] = response.status_code
    models = response.json().get("models") if response.status_code == 200 else None
    if type(models) is list:
        target = [m for m in models if type(m) is dict and m.get("slug") == spec["model"]]
        report.update(models_count=len(models), target_listed=len(target) == 1,
                      target_visibility=label(target[0].get("visibility")) if len(target) == 1 else None)
def phase_dispatch(report):
    record = load_credential()
    access_facts(report, record)
    if report["token_seconds_remaining"] < spec["min_token_seconds"]:
        raise Blocked("TOKEN_NEAR_EXPIRY")  # never refresh around the one inference
    import hermes_cli
    from run_agent import AIAgent
    from agent.chat_completion_helpers import build_api_kwargs
    from agent import codex_runtime as cr
    route = spec["route"]
    agent = AIAgent(base_url=route["base_url"], api_key="oauth-plan-placeholder", provider=route["provider"],
                    api_mode=route["api_mode"], model=route["model"], quiet_mode=True, skip_context_files=True,
                    skip_memory=True, skip_background_review=True, max_iterations=1, enabled_toolsets=[])
    messages = [{"role": "system", "content": spec["instructions"]}, {"role": "user", "content": spec["model_input"]}]
    kwargs = build_api_kwargs(agent, messages)
    wire = cr._sanitize_consumer_codex_request(agent, kwargs)
    wire["stream"] = True
    wire["timeout"] = spec["timeout_s"]
    report.update(hermes_version=hermes_cli.__version__, construction_network_attempts=list(attempts))
    if attempts:
        raise Blocked("CONSTRUCTION_NETWORK_ATTEMPT")
    sent, presend = [], []
    def check(request):
        body = request.content
        try:
            p = json.loads(body)
        except Exception:
            p = None
        p = p if type(p) is dict else {}
        items = p.get("input") if type(p.get("input")) is list else []
        facts = dict(method=request.method, scheme=request.url.scheme, host=request.url.host, port=request.url.port,
                     path=request.url.path, body_sha256=sha(body), body_bytes=len(body), body_keys=sorted(p),
                     model=p.get("model"), stream=p.get("stream"), store=p.get("store"), include=p.get("include"),
                     tools_count=len(p.get("tools") or []), input_roles=[label(i.get("role")) if type(i) is dict else None for i in items],
                     input_sha256=sha(canon(p.get("input"))),
                     instructions_sha256=sha(p["instructions"].encode("utf-8")) if type(p.get("instructions")) is str else None,
                     authorization_bearer=request.headers.get("authorization", "").startswith("Bearer "),
                     retry_count_header=request.headers.get("x-stainless-retry-count"))
        sent.append(facts)
        keys = set(facts["body_keys"])
        ok = (len(sent) == 1 and (facts["method"], facts["scheme"], facts["host"], facts["path"]) ==
              ("POST", "https", C["api_host"], C["responses_path"]) and set(C["body_required"]) <= keys <= set(C["body_allowed"])
              and not keys & set(C["unsupported"]) and facts["model"] == route["model"] and facts["stream"] is True
              and facts["store"] is False and facts["input_roles"] == ["user"] and facts["authorization_bearer"])
        if not ok:
            presend.append("PRESEND_WIRE_REJECTED")
            raise RuntimeError("pre-send wire check failed")
    http = client(spec["timeout_s"], [check])
    sdk = agent._create_openai_client(dict(agent._client_kwargs, api_key=record["access_token"], base_url=route["base_url"],
                                      max_retries=0, http_client=http), reason="oauth_plan_dispatch", shared=False)
    report["sdk_max_retries"] = sdk.max_retries
    if sdk.max_retries != 0:
        raise Blocked("SDK_RETRY_ENABLED")
    allowed_hosts.add(C["api_host"])
    started, out = time.monotonic(), dict(bytes=0, stop=None)
    report.update(terminal_events=[], event_count=0)
    def on_event(event):
        kind = str(getattr(event, "type", ""))[:64]
        report["event_count"] += 1
        if kind == "response.output_text.delta":
            out["bytes"] += len(str(getattr(event, "delta", "")).encode("utf-8"))
        if kind in ("response.completed", "response.incomplete", "response.failed"):
            report["terminal_events"].append(kind)
            response = getattr(event, "response", None)
            model, rid = getattr(response, "model", None), getattr(response, "id", None)
            usage = getattr(response, "usage", None)
            error = getattr(response, "error", None)
            report.update(server_model=label(model) if type(model) is str else None,
                          response_id_sha256=sha(rid.encode("utf-8")) if type(rid) is str and rid else None,
                          failed_code=label(getattr(error, "code", None)) if error is not None else None,
                          usage=None if usage is None else {k: getattr(usage, k, None) for k in ("input_tokens", "output_tokens", "total_tokens")})
    def interrupt():
        if out["bytes"] > spec["max_output_bytes"]:
            out["stop"] = "OUTPUT_CAP_EXCEEDED"
        elif time.monotonic() - started > spec["timeout_s"]:
            out["stop"] = "CLIENT_STREAM_TIMEOUT"
        return out["stop"] is not None
    try:
        stream = sdk.responses.create(**cr._bypass_sdk_request_transform(wire))
        report["x_request_id_sha256"] = None
        headers = getattr(getattr(stream, "response", None), "headers", None)
        if headers is not None and headers.get("x-request-id"):
            report["x_request_id_sha256"] = sha(headers["x-request-id"].encode("utf-8"))
        final = cr._consume_codex_event_stream(stream, model=kwargs.get("model"), on_event=on_event, interrupt_check=interrupt)
        report["final"] = dict(status=label(final.status), output_types=[label(getattr(i, "type", "")) for i in final.output],
                               output_text=final.output_text if out["stop"] is None else None)
    except Exception as exc:
        report["error_class"] = type(exc).__name__.lstrip("_")[:64]
        status = getattr(exc, "status_code", None)
        report["http_status"] = status if type(status) is int else None
        body = getattr(exc, "body", None)
        code = body.get("code") if type(body) is dict else None
        report["failed_code"] = report.get("failed_code") or (label(code) if type(code) is str else None)
    finally:
        http.close()
    report.update(requests=sent, presend_block=presend[0] if presend else None, client_stop=out["stop"])
report = dict(schema="oauth-plan-child-v1", phase=PHASE, mode=MODE, status="DONE", reason_code=None, error_class=None,
              api_key_env_present=any("API_KEY" in k.upper() for k in os.environ), tls_verify=True, trust_env=False)
try:
    {"login": phase_login, "preflight": phase_preflight, "dispatch": phase_dispatch}[PHASE](report)
except Blocked as stop:
    report.update(status="BLOCKED", reason_code=str(stop))
except Exception as exc:
    report.update(status="BLOCKED", reason_code="CHILD_EXCEPTION", error_class=report.get("error_class") or type(exc).__name__[:64])
report.update(network_attempts=attempts, http_calls=calls)
print(json.dumps(report, sort_keys=True))
'''


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def oauth_model_input(candidate_menu, lineage, information_cutoff_ns: int, produced_at_ns: int,
                      expires_at_ns: int) -> bytes:
    """Exact user bytes: the AUTO-01 menu, optional native lineage and the clocks to copy."""
    return stage_b._canonical(dict(menu=[dict(m) for m in candidate_menu], lineage=[dict(x) for x in lineage],
                                   information_cutoff_ns=information_cutoff_ns, produced_at_ns=produced_at_ns,
                                   expires_at_ns=expires_at_ns))


@dataclass(frozen=True)
class OAuthPlanRequest:
    """Immutable one-attempt identity over a freshly verified tool-free Stage B request."""
    request_id: str
    stage_b_request_id: str
    provider: str
    api_mode: str
    base_url: str
    model: str
    instructions_sha256: str
    model_input_sha256: str
    candidate_menu_sha256: str
    information_cutoff_ns: int
    issued_at_ns: int
    deadline_ns: int
    hermes_commit: str
    tool_surface_fingerprint: str
    model_input: bytes = field(default=b"", repr=False)


def _preimage(request: OAuthPlanRequest) -> dict:
    return {k: v for k, v in request.__dict__.items() if k not in ("request_id", "model_input")}


def build_oauth_request(*, surface_report: object, candidate_menu, lineage=(), information_cutoff_ns: int,
                        issued_at_ns: int, deadline_ns: int) -> OAuthPlanRequest:
    """Raises ValueError(code). The model is told to copy issued/deadline as its own clocks."""
    from src.research_runtime import autonomous_opportunity_cycle as cycle
    from . import autonomous_feedback as fb
    menu = [dict(item) for item in candidate_menu]
    model_input = oauth_model_input(menu, lineage, information_cutoff_ns, issued_at_ns, deadline_ns)
    if len(model_input) > MAX_REQUEST_INPUT_BYTES:
        raise ValueError("REQUEST_INPUT_TOO_LARGE")
    stage = stage_b.build_stage_b_request(
        surface_report=surface_report, candidate_menu_sha256=cycle._digest(menu),
        output_schema_sha256=fb.choice_output_schema_sha256(), model_input_sha256=_sha(model_input),
        information_cutoff_ns=information_cutoff_ns, issued_at_ns=issued_at_ns, deadline_ns=deadline_ns,
        model_label=ROUTE["model"])
    draft = OAuthPlanRequest("", stage.request_id, ROUTE["provider"], ROUTE["api_mode"], ROUTE["base_url"],
                             ROUTE["model"], _sha(INSTRUCTIONS.encode("utf-8")), stage.model_input_sha256,
                             stage.candidate_menu_sha256, information_cutoff_ns, issued_at_ns, deadline_ns,
                             stage.hermes_commit, stage.tool_surface_fingerprint, model_input=model_input)
    return replace(draft, request_id=REQUEST_ID_PREFIX + stage_b._digest(_preimage(draft)))


def request_is_bound(request: object) -> bool:
    return (type(request) is OAuthPlanRequest and
            (request.provider, request.api_mode, request.base_url, request.model) == tuple(ROUTE.values()) and
            request.hermes_commit == stage_b.PINNED_HERMES_COMMIT and type(request.model_input) is bytes and
            _sha(request.model_input) == request.model_input_sha256 and
            request.instructions_sha256 == _sha(INSTRUCTIONS.encode("utf-8")) and
            request.request_id == REQUEST_ID_PREFIX + stage_b._digest(_preimage(request)))


# --------------------------------------------------------------------- transport


class OAuthPlanTransport:
    """The only credential/network seam: one pinned child per phase, user-scoped credentials.

    ``mode="mock"`` replaces every HTTP call with in-memory fixtures (no sockets at all) and
    can never yield a witnessed result. ``mode="real"`` is the attended official route.
    """

    def __init__(self, pin_root: object, credential_dir: object, *, mode: str = "real", mock: dict | None = None,
                 python_executable: object = None, login_wait_s: int = 300) -> None:
        credentials = Path(credential_dir)
        if not credentials.is_absolute():
            raise ValueError("CREDENTIAL_DIR_NOT_ABSOLUTE")
        resolved = credentials.resolve()
        if resolved == _REPO_ROOT or _REPO_ROOT in resolved.parents:
            raise ValueError("CREDENTIAL_DIR_INSIDE_REPOSITORY")
        if mode not in ("real", "mock") or (mode == "real") != (mock is None):
            raise ValueError("TRANSPORT_MODE_INVALID")
        self.mode, self._pin_root, self._credentials = mode, Path(pin_root).absolute(), resolved
        self._mock, self._python, self._login_wait_s = json.loads(json.dumps(mock or {})), python_executable, login_wait_s
        self.dispatch_count = 0
        self.control_phases: list[str] = []

    def _run_child(self, phase: str, extra: dict, timeout_s: float) -> dict:
        import os
        import subprocess
        import tempfile
        root = self._pin_root
        if (root / ".env").exists():  # pinned run_agent loads it at import
            raise ValueError("PIN_DOTENV_PRESENT")
        head = (root / ".git" / "HEAD").read_text(encoding="ascii").strip()
        exe = Path(self._python) if self._python is not None else (
            root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
        spec = dict(phase=phase, mode=self.mode, mock=self._mock, credential_dir=str(self._credentials),
                    model=ROUTE["model"], route=ROUTE, login_wait_s=self._login_wait_s,
                    refresh_margin_s=REFRESH_MARGIN_S, min_token_seconds=MIN_TOKEN_SECONDS,
                    constants=dict(api_host=API_HOST, auth_host=AUTH_HOST, issuer=ISSUER, authorize_url=AUTHORIZE_URL,
                                   token_url=TOKEN_URL, jwks_url=JWKS_URL, resource=RESOURCE, scopes=sorted(REQUIRED_SCOPES),
                                   agent_name_hint=AGENT_NAME_HINT, models_path=MODELS_PATH, responses_path=RESPONSES_PATH,
                                   body_required=sorted(BODY_REQUIRED), body_allowed=sorted(BODY_ALLOWED),
                                   unsupported=sorted(UNSUPPORTED_FIELDS)), **extra)
        # Windows may briefly keep the sterile home locked after the child exits; cleanup is
        # best-effort and never turns an already-finished phase into a transport failure.
        with tempfile.TemporaryDirectory(prefix="oauthplan-hermes-home-", ignore_cleanup_errors=True) as home:
            # Sterile route config: a known context window skips the authenticated /models init probe.
            Path(home, "config.yaml").write_text(
                "model:\n  provider: {provider}\n  default: {model}\n  base_url: {base_url}\n".format(**ROUTE)
                + f"  context_length: {real01.ROUTE_CONTEXT_LENGTH}\n", encoding="utf-8")
            env = {key: home for key in ("HERMES_HOME", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP")}
            env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", PATH=str(exe.parent), NO_COLOR="1")
            if "SYSTEMROOT" in os.environ:
                env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
            completed = subprocess.run([str(exe), "-I", "-B", "-c", _CHILD_SOURCE], cwd=root, env=env,
                                       input=json.dumps(spec).encode("utf-8"), capture_output=True,
                                       timeout=timeout_s, check=False)
        lines = completed.stdout.decode("utf-8", "replace").strip().splitlines()
        report = json.loads(lines[-1]) if completed.returncode == 0 and lines else {}
        if type(report) is dict and report:
            report["hermes_commit"] = head
        return report

    def login(self) -> dict:
        """Attended: opens the user's browser; the user performs consent. Control plane only."""
        self.control_phases.append("login")
        return self._run_child("login", {}, self._login_wait_s + 120)

    def preflight(self) -> dict:
        self.control_phases.append("preflight")
        return self._run_child("preflight", {}, 120)

    def _send(self, request: OAuthPlanRequest) -> dict:
        self.dispatch_count += 1
        return self._run_child("dispatch", dict(instructions=INSTRUCTIONS, model_input=request.model_input.decode("utf-8"),
                                                timeout_s=STREAM_TIMEOUT_S, max_output_bytes=MAX_OUTPUT_BYTES),
                               STREAM_TIMEOUT_S + 120)


# --------------------------------------------------------------------- R001 eligibility

_OBSERVED = object()


@dataclass(frozen=True)
class PlanEligibility:
    status: str
    reason_code: str | None
    model: str
    checked_at_ns: int
    mode: str
    facts: dict
    eligibility_id: str
    _witness: object = field(default=None, repr=False, compare=False)


def _calls_ok(report: dict, allowed: set) -> bool:
    calls = report.get("http_calls")
    return type(calls) is list and all(type(c) is list and len(c) == 4 and (c[0], c[1], c[2]) in allowed for c in calls)


def _attempts_ok(report: dict, hosts: set) -> bool:
    attempts = report.get("network_attempts")
    return type(attempts) is list and all(type(a) is list and len(a) == 3 and a[2] is True and a[0] in hosts and a[1] == 443
                                          for a in attempts)


def evaluate_preflight(report: object, *, attestation: object, checked_at_ns: int) -> PlanEligibility:
    """Pure R001 verdict over one preflight report and the operator's credit/model attestation.

    Purchased-credit state has no API: only the operator's explicit attestation can establish it.
    """
    def verdict(code: str | None, facts: dict, mode: str = "UNKNOWN") -> PlanEligibility:
        body = dict(status=PLAN_USAGE_UNVERIFIED if code else PLAN_USAGE_ELIGIBLE, reason_code=code,
                    model=ROUTE["model"], checked_at_ns=checked_at_ns, mode=mode, facts=facts)
        return PlanEligibility(**body, eligibility_id=ELIGIBILITY_PREFIX + stage_b._digest(body),
                               _witness=_OBSERVED if code is None else None)
    if type(report) is not dict or report.get("schema") != _CHILD_SCHEMA or report.get("phase") != "preflight":
        return verdict("PREFLIGHT_REPORT_INVALID", {})
    facts = {k: report.get(k) for k in ("scopes_granted", "access_audience_ok", "access_issuer_ok", "client_match",
                                        "token_seconds_remaining", "refreshed", "models_status", "models_count",
                                        "target_listed", "target_visibility", "client_id_sha256")}
    facts["http_calls"] = report.get("http_calls")
    mode = report.get("mode") if report.get("mode") in ("real", "mock") else "UNKNOWN"
    if report.get("hermes_commit") != stage_b.PINNED_HERMES_COMMIT:
        return verdict("PIN_MISMATCH", facts, mode)
    if report.get("api_key_env_present") is not False:
        return verdict("API_KEY_ENV_PRESENT", facts, mode)
    if report.get("status") != "DONE":
        return verdict(str(report.get("reason_code") or "PREFLIGHT_BLOCKED")[:64], facts, mode)
    if report.get("tls_verify") is not True or report.get("trust_env") is not False or \
            not _attempts_ok(report, {AUTH_HOST, API_HOST}):
        return verdict("UNEXPECTED_NETWORK_TARGET", facts, mode)
    refresh = {("POST", AUTH_HOST, "/api/accounts/oauth/token")} if report.get("refreshed") is True else set()
    calls = report.get("http_calls") or []
    if not _calls_ok(report, {("GET", API_HOST, MODELS_PATH)} | refresh) or len(calls) != 1 + len(refresh):
        return verdict("CONTROL_PLANE_UNEXPECTED", facts, mode)
    if type(facts["scopes_granted"]) is not list or not REQUIRED_SCOPES <= set(facts["scopes_granted"]):
        return verdict("PLAN_SCOPE_MISSING", facts, mode)
    if facts["access_audience_ok"] is not True or facts["access_issuer_ok"] is not True or facts["client_match"] is not True:
        return verdict("ACCESS_TOKEN_BINDING_INVALID", facts, mode)
    if type(facts["token_seconds_remaining"]) is not int or facts["token_seconds_remaining"] < REFRESH_MARGIN_S - 60:
        return verdict("TOKEN_STALE", facts, mode)
    if facts["models_status"] != 200 or type(facts["models_count"]) is not int:
        return verdict("MODEL_CATALOG_UNAVAILABLE", facts, mode)
    if facts["target_listed"] is not True:
        return verdict("OAUTH_MODEL_NOT_AVAILABLE", facts, mode)
    if attestation != _ATTESTATION:
        return verdict("CREDITS_STATUS_UNVERIFIED", facts, mode)
    if mode != "real":
        return verdict("MOCK_TRANSPORT_NOT_ELIGIBLE", facts, mode)
    return verdict(None, facts, mode)


def eligibility_is_witnessed(eligibility: object) -> bool:
    if type(eligibility) is not PlanEligibility or eligibility._witness is not _OBSERVED:
        return False
    body = {k: getattr(eligibility, k) for k in ("status", "reason_code", "model", "checked_at_ns", "mode", "facts")}
    return (eligibility.status == PLAN_USAGE_ELIGIBLE and eligibility.mode == "real" and
            eligibility.eligibility_id == ELIGIBILITY_PREFIX + stage_b._digest(body))


# --------------------------------------------------------------------- R002 wire / R004 classification


def verify_dispatch_wire(request: OAuthPlanRequest, report: object) -> dict:
    """Pure verdict over the post-SDK request the child observed before sending."""
    def verdict(code: str | None, sent: dict | None = None) -> dict:
        return dict(status=real01.WIRE_BLOCKED if code else real01.WIRE_CHECKED, reason_code=code,
                    wire_stage="POST_SDK_PRESEND_CAPTURED" if sent else "NOT_CAPTURED",
                    body_sha256=sent.get("body_sha256") if sent else None,
                    body_bytes=sent.get("body_bytes") if sent else None)
    if type(report) is not dict or report.get("schema") != _CHILD_SCHEMA or report.get("phase") != "dispatch":
        return verdict("WIRE_REPORT_INVALID")
    if report.get("hermes_version") != stage_b.PINNED_HERMES_SEMVER or report.get("hermes_commit") != stage_b.PINNED_HERMES_COMMIT:
        return verdict("PIN_MISMATCH")
    if report.get("api_key_env_present") is not False or report.get("tls_verify") is not True or \
            report.get("trust_env") is not False:
        return verdict("UNSAFE_CHILD_ENVIRONMENT")
    if report.get("construction_network_attempts") != [] or not _attempts_ok(report, {API_HOST}):
        return verdict("UNEXPECTED_NETWORK_ATTEMPT")
    sent_list = report.get("requests")
    if type(sent_list) is not list or not sent_list:
        return verdict("NOT_DISPATCHED")
    if len(sent_list) != 1 or type(sent_list[0]) is not dict:
        return verdict("MULTIPLE_DISPATCH_INVALID")
    sent = sent_list[0]
    if report.get("sdk_max_retries") != 0 or sent.get("retry_count_header") != "0":
        return verdict("SDK_RETRY_ENABLED", sent)
    if (sent.get("method"), sent.get("scheme"), sent.get("host"), sent.get("port"), sent.get("path")) != \
            ("POST", "https", API_HOST, None, RESPONSES_PATH):
        return verdict("UNEXPECTED_ENDPOINT", sent)
    keys = sent.get("body_keys")
    if type(keys) is not list or sent.get("tools_count") != 0 or UNSUPPORTED_FIELDS & set(keys):
        return verdict("WIRE_UNSUPPORTED_OR_TOOL_FIELD", sent)
    include = sent.get("include")
    if not BODY_REQUIRED <= set(keys) <= BODY_ALLOWED or not (
            include is None or (type(include) is list and set(include) <= _INCLUDE_ALLOWED)):
        return verdict("UNEXPECTED_REQUEST_FIELD", sent)
    if sent.get("model") != request.model or sent.get("stream") is not True or sent.get("store") is not False:
        return verdict("WIRE_MODEL_OR_MODE_MISMATCH", sent)
    if sent.get("input_roles") != ["user"]:
        return verdict("WIRE_INPUT_ROLE_INVALID", sent)
    if sent.get("instructions_sha256") != request.instructions_sha256 or \
            sent.get("input_sha256") != _sha(real01._canon_input(request.model_input.decode("utf-8"))):
        return verdict("WIRE_INPUT_MISMATCH", sent)
    if sent.get("authorization_bearer") is not True:
        return verdict("WIRE_AUTH_SHAPE_INVALID", sent)
    if report.get("presend_block") is not None:
        return verdict("PRESEND_WIRE_REJECTED", sent)
    return verdict(None, sent)


_SNAPSHOT_SUFFIX = re.compile(r"-\d{4}-\d{2}-\d{2}")


def _model_relation(observed: object, expected: str) -> str:
    if observed is None:
        return "NOT_REPORTED"
    if observed == expected:
        return "EXACT"
    if type(observed) is str and observed.startswith(expected) and _SNAPSHOT_SUFFIX.fullmatch(observed[len(expected):]):
        return "DATED_SNAPSHOT"
    return "MISMATCH"


def _usage(value: object) -> dict | None:
    keys = ("input_tokens", "output_tokens", "total_tokens")
    if type(value) is dict and all(type(value.get(k)) is int and value[k] >= 0 for k in keys):
        return {k: value[k] for k in keys}
    return None


def classify_dispatch_report(request: OAuthPlanRequest, report: object, *, dispatched_at_ns: int,
                             finished_at_ns: int) -> tuple[str, dict, bytes | None]:
    """Pure: (terminal status, sanitized facts, accepted output bytes). Never retries."""
    wire = verify_dispatch_wire(request, report)
    report = report if type(report) is dict else {}
    final = report.get("final") if type(report.get("final")) is dict else None
    calls = report.get("http_calls") if type(report.get("http_calls")) is list else []
    inference_calls = [c for c in calls if type(c) is list and c[:3] == ["POST", API_HOST, RESPONSES_PATH]]
    sent = report.get("requests") if type(report.get("requests")) is list else []
    facts = dict(wire=wire, mode=report.get("mode"), generation_requests=len(sent),
                 http_responses=len(inference_calls), sdk_max_retries=report.get("sdk_max_retries"),
                 http_status=inference_calls[0][3] if len(inference_calls) == 1 and type(inference_calls[0][3]) is int
                 else report.get("http_status") if type(report.get("http_status")) is int else None,
                 error_class=real01._label(report.get("error_class")), failed_code=real01._label(report.get("failed_code")),
                 client_stop=real01._label(report.get("client_stop")), server_model=real01._label(report.get("server_model")),
                 response_id_sha256=report.get("response_id_sha256") if type(report.get("response_id_sha256")) is str
                 and stage_b._HEX64.fullmatch(report["response_id_sha256"]) else None,
                 x_request_id_sha256=report.get("x_request_id_sha256") if type(report.get("x_request_id_sha256")) is str
                 and stage_b._HEX64.fullmatch(report["x_request_id_sha256"]) else None,
                 usage=_usage(report.get("usage")), presend_block=real01._label(report.get("presend_block")))
    if report.get("status") == "BLOCKED" and report.get("reason_code") != "CHILD_EXCEPTION":
        return "DISPATCH_BLOCKED_" + str(report.get("reason_code"))[:48], facts, None
    if wire["status"] != real01.WIRE_CHECKED:
        return wire["reason_code"], facts, None
    if len(inference_calls) > 1:
        return "MULTIPLE_DISPATCH_INVALID", facts, None
    status = facts["http_status"]
    if status in (401, 403):
        return "PROVIDER_AUTH_OR_ENTITLEMENT_DENIED", facts, None
    if status == 429:
        return "PROVIDER_RATE_LIMITED", facts, None
    if status is not None and status >= 500:
        return "PROVIDER_SERVER_ERROR", facts, None
    if status is not None and status != 200:
        return "PROVIDER_HTTP_ERROR", facts, None
    if facts["client_stop"] == "OUTPUT_CAP_EXCEEDED":
        return "OUTPUT_SIZE_INVALID", facts, None
    if facts["client_stop"] is not None or facts["error_class"] in ("APITimeoutError", "ReadTimeout"):
        return "PROVIDER_TIMEOUT", facts, None
    terminals = report.get("terminal_events")
    if terminals == ["response.failed"]:
        return "PROVIDER_RESPONSE_FAILED", facts, None
    if facts["error_class"] is not None or final is None:
        return "TRANSPORT_OR_STREAM_ERROR", facts, None
    types = final.get("output_types")
    if type(types) is not list or any(t not in _OUTPUT_TYPES_ALLOWED for t in types):
        return "TOOL_CALL_ATTEMPT_INVALID", facts, None
    if terminals != ["response.completed"] or final.get("status") != "completed":
        return "RESPONSE_INCOMPLETE", facts, None
    if types.count("message") != 1:
        return "RESPONSE_SHAPE_INVALID", facts, None  # reasoning-only or several replies
    if _model_relation(facts["server_model"], request.model) == "MISMATCH":
        return "MODEL_MISMATCH", facts, None
    if not (request.issued_at_ns <= dispatched_at_ns <= finished_at_ns <= request.deadline_ns):
        return "DEADLINE_EXCEEDED", facts, None
    text = final.get("output_text")
    raw = text.encode("utf-8") if type(text) is str else b""
    if not 0 < len(raw) <= MAX_OUTPUT_BYTES:
        return "OUTPUT_SIZE_INVALID", facts, None
    try:
        if type(strict_json_loads(text)) is not dict:
            raise ValueError
    except Exception:
        return "OUTPUT_JSON_INVALID", facts, None
    return VALID_OUTPUT, facts, raw


# --------------------------------------------------------------------- R003 one attempt / origin


@dataclass(frozen=True)
class OAuthPlanResult:
    request_id: str
    status: str
    origin: dict | None
    output_bytes: bytes | None = field(default=None, repr=False)
    replayed: bool = False
    _witness: object = field(default=None, repr=False, compare=False)


def _origin_record(request: OAuthPlanRequest, status: str, facts: dict, raw: bytes | None, eligibility: object,
                   dispatched_at_ns: int, finished_at_ns: int | None) -> dict:
    wire = facts.get("wire") or {}
    real = facts.get("mode") == "real"
    sent = facts.get("generation_requests") or 0
    answered = facts.get("http_status") is not None or facts.get("http_responses")
    invocation = ("PROVIDER_NOT_INVOKED" if not sent or facts.get("presend_block") else
                  OAUTH_AUTHENTICATED_HTTP if real and answered else
                  "MOCK_TRANSPORT_ONLY" if not real else "PROVIDER_INVOCATION_UNKNOWN")
    relation = _model_relation(facts.get("server_model"), request.model)
    # Only the exact pinned slug verifies; a dated snapshot is honest transport, not the pinned model.
    complete = (invocation == OAUTH_AUTHENTICATED_HTTP and status == VALID_OUTPUT and relation == "EXACT"
                and facts.get("response_id_sha256") is not None and facts.get("usage") is not None)
    eligible = eligibility_is_witnessed(eligibility)
    record = dict(
        schema_id="hermes-oauth-plan-origin-record", request_id=request.request_id,
        stage_b_request_id=request.stage_b_request_id, hermes_commit=request.hermes_commit,
        tool_surface_fingerprint=request.tool_surface_fingerprint, provider_route="CHATGPT_PLAN_OAUTH",
        endpoint_host=API_HOST, endpoint_path=RESPONSES_PATH, expected_model=request.model,
        transport_mode=TRANSPORT_REAL if real else TRANSPORT_MOCK, status=status,
        eligibility_id=getattr(eligibility, "eligibility_id", None),
        plan_usage=PLAN_USAGE_ELIGIBLE if eligible else PLAN_USAGE_UNVERIFIED,
        credits_status="OPERATOR_ATTESTED_PURCHASED_CREDITS_DISABLED" if eligible else "UNVERIFIED",
        wire_stage=wire.get("wire_stage", "NOT_CAPTURED"), wire_status=wire.get("status"),
        wire_reason=wire.get("reason_code"), wire_body_sha256=wire.get("body_sha256"),
        wire_body_bytes=wire.get("body_bytes"), generation_requests=sent,
        sdk_max_retries=facts.get("sdk_max_retries"), application_retries=0, fallback_used=False,
        token_refresh_during_dispatch=False, dispatched_at_ns=dispatched_at_ns, finished_at_ns=finished_at_ns,
        http_status=facts.get("http_status"), error_class=facts.get("error_class"), failed_code=facts.get("failed_code"),
        client_stop=facts.get("client_stop"), raw_output_sha256=_sha(raw) if raw is not None else None,
        server_model_observed=facts.get("server_model"), server_model_relation=relation,
        response_id_sha256=facts.get("response_id_sha256"), x_request_id_sha256=facts.get("x_request_id_sha256"),
        usage=facts.get("usage"), usage_status="USAGE_PROVIDER_REPORTED" if facts.get("usage") else "USAGE_UNKNOWN",
        output_token_cap="NOT_SUPPORTED_ON_ROUTE_CLIENT_BYTE_CAP_ONLY", client_output_cap_bytes=MAX_OUTPUT_BYTES,
        client_stream_timeout_s=STREAM_TIMEOUT_S, cost_status="INCLUDED_PLAN_USAGE_NO_DOLLAR_AMOUNT_INFERRED"
        if eligible else "COST_UNKNOWN", candidate_menu_sha256=request.candidate_menu_sha256,
        information_cutoff_ns=request.information_cutoff_ns, issued_at_ns=request.issued_at_ns,
        deadline_ns=request.deadline_ns, provider_invocation=invocation,
        model_identity="PROVIDER_REPORTED_MODEL" if complete else "MODEL_IDENTITY_UNVERIFIED",
        real_origin=REAL_ORIGIN_VERIFIED if complete and eligible else
        REAL_TRANSPORT_UNVERIFIED if invocation == OAUTH_AUTHENTICATED_HTTP else REAL_ORIGIN_UNVERIFIED,
        attestation_limit="PROVIDER_REPORTED_NOT_CRYPTOGRAPHIC", execution_authority="NONE",
    )
    record["record_id"] = RECORD_ID_PREFIX + stage_b._digest(record)
    return record


def verify_origin_record(record: object) -> bool:
    if type(record) is not dict or record.get("schema_id") != "hermes-oauth-plan-origin-record":
        return False
    body = {k: v for k, v in record.items() if k != "record_id"}
    return record.get("record_id") == RECORD_ID_PREFIX + stage_b._digest(body)


def is_witnessed_result(result: object) -> bool:
    """True only for a live (non-replayed) real-mode result this module produced and verified."""
    return (type(result) is OAuthPlanResult and result._witness is _OBSERVED and not result.replayed and
            result.status == VALID_OUTPUT and type(result.output_bytes) is bytes and verify_origin_record(result.origin)
            and result.origin["request_id"] == result.request_id and result.origin["real_origin"] == REAL_ORIGIN_VERIFIED
            and result.origin["transport_mode"] == TRANSPORT_REAL
            and result.origin["raw_output_sha256"] == _sha(result.output_bytes))


def run_oauth_attempt(request: object, *, eligibility: object, transport: object, journal_dir: object,
                      clock_ns=None) -> OAuthPlanResult:
    """Reserve the journal's single attempt, dispatch at most once, journal one terminal.

    A journal namespace admits ONE dispatch ever: the same request replays its terminal, a
    reservation without a terminal is consumed, and any other request id is refused.
    """
    import subprocess
    import time
    clock = clock_ns or time.time_ns
    request_id = getattr(request, "request_id", "")
    if not request_is_bound(request) or type(transport) is not OAuthPlanTransport:
        return OAuthPlanResult(request_id, "REQUEST_OR_TRANSPORT_INVALID", None)
    root = Path(journal_dir).absolute()
    marker, terminal = root / "oauthplan-attempt.reserved", root / "oauthplan-attempt.json"
    if terminal.exists():
        try:
            record = json.loads(terminal.read_bytes())
            if not verify_origin_record(record):
                raise ValueError
        except Exception:
            return OAuthPlanResult(request_id, "JOURNAL_INVALID", None)
        if record["request_id"] != request_id:
            return OAuthPlanResult(request_id, "JOURNAL_ALREADY_CONSUMED", None)
        return OAuthPlanResult(request_id, record["status"], record, None, True)  # zero redispatch
    if marker.exists():
        return OAuthPlanResult(request_id, "ATTEMPT_ALREADY_RESERVED", None)
    real = transport.mode == "real"
    if real and not eligibility_is_witnessed(eligibility):
        return OAuthPlanResult(request_id, "PLAN_ELIGIBILITY_NOT_ESTABLISHED", None)
    dispatched = clock()
    if real and not 0 <= dispatched - eligibility.checked_at_ns <= MAX_ELIGIBILITY_AGE_NS:
        return OAuthPlanResult(request_id, "PLAN_ELIGIBILITY_STALE", None)
    if not request.issued_at_ns <= dispatched < request.deadline_ns:
        return OAuthPlanResult(request_id, "DEADLINE_EXCEEDED_NOT_DISPATCHED", None)
    try:
        root.mkdir(parents=True, exist_ok=True)
        with marker.open("xb") as stream:
            stream.write(request_id.encode("ascii"))
    except FileExistsError:
        return OAuthPlanResult(request_id, "ATTEMPT_ALREADY_RESERVED", None)  # concurrent caller
    raw = None
    try:
        report = transport._send(request)
        finished = clock()
        status, facts, raw = classify_dispatch_report(request, report, dispatched_at_ns=dispatched, finished_at_ns=finished)
    except subprocess.TimeoutExpired:
        status, facts, finished = "ATTEMPT_TIMEOUT_CONSUMED", dict(mode=transport.mode, generation_requests=1), clock()
    except Exception:
        status, facts, finished = "ATTEMPT_TRANSPORT_FAILED_CONSUMED", dict(mode=transport.mode, generation_requests=1), clock()
    record = _origin_record(request, status, facts, raw, eligibility, dispatched, finished)
    with terminal.open("xb") as stream:
        stream.write(stage_b._canonical(record))
    witnessed = real and status == VALID_OUTPUT and record["real_origin"] == REAL_ORIGIN_VERIFIED
    return OAuthPlanResult(request_id, status, record, raw if status == VALID_OUTPUT else None, False,
                           _OBSERVED if witnessed else None)
