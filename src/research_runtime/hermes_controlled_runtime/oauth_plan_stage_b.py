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

# Shared SIWC admission/storage primitives execute in the pinned phase child.
# Defining them (including the CLI parse-only seam) performs no private I/O.
_SIWC_SOURCE = r'''
import base64, errno, hashlib, json, math, os, pathlib, re, secrets, stat, sys

class SIWCBlocked(Exception):
    """Only fixed local codes cross this boundary; never an input or OS error."""

def siwc_json(raw, limit):
    if type(raw) is not bytes or not 0 < len(raw) <= limit:
        raise SIWCBlocked("RECORD_INVALID")
    try:
        text = raw.decode("utf-8")
        depth, quoted, escaped = 0, False, False
        for char in text:
            if quoted:
                if escaped: escaped = False
                elif char == "\\": escaped = True
                elif char == '"': quoted = False
            elif char == '"': quoted = True
            elif char in "[{":
                depth += 1
                if depth > 8: raise ValueError()
            elif char in "]}": depth -= 1
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result: raise ValueError()
                result[key] = value
            return result
        def finite(value):
            number = float(value)
            if not math.isfinite(number): raise ValueError()
            return number
        value = json.loads(text, object_pairs_hook=pairs, parse_float=finite,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if type(value) is not dict: raise ValueError()
        return value
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        raise SIWCBlocked("RECORD_INVALID") from None

def siwc_bytes(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise SIWCBlocked("RECORD_INVALID") from None

def siwc_text(value, limit=4096):
    try:
        return type(value) is str and 0 < len(value.encode("utf-8")) <= limit
    except UnicodeError:
        return False

def siwc_path(value, *, windows=False):
    if not siwc_text(value) or any(ord(c) < 32 for c in value):
        raise SIWCBlocked("STORAGE_UNSAFE")
    cls = pathlib.PureWindowsPath if windows else pathlib.PurePosixPath
    path = cls(value)
    parts = value.replace("\\", "/").split("/") if windows else value.split("/")
    if not path.is_absolute() or any(p in (".", "..") for p in parts):
        raise SIWCBlocked("STORAGE_UNSAFE")
    if windows:
        if (not re.fullmatch(r"[A-Za-z]:", path.drive) or value.startswith(("\\", "/"))
                or ":" in value[2:] or any(c in value[2:] for c in '<>"|?*')):
            raise SIWCBlocked("STORAGE_UNSAFE")
        for part in path.parts[1:]:
            if (part.endswith((".", " ")) or "~" in part or
                    re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part)):
                raise SIWCBlocked("STORAGE_UNSAFE")
    elif value.startswith("//") or "\\" in value:
        raise SIWCBlocked("STORAGE_UNSAFE")
    return path

def siwc_overlap(left, right):
    return left == right or left in right.parents or right in left.parents

_SIWC_OPERATIONS = frozenset(("prepare-vm-host", "import-selected", "preflight-only", "source-export",
                              "source-login", "dispatch"))
_SIWC_RECEIPT_OPERATIONS = _SIWC_OPERATIONS - {"dispatch"}
_SIWC_OPERATOR_KEYS = frozenset(("schema_id", "schema_version", "operation", "operation_alias",
    "selected_client_id", "selected_subject", "approved_storage_root", "excluded_roots",
    "destination_host_id", "expected_source_commit", "expected_runtime_profile_sha256",
    "refresh_allowed", "valid_from_ns", "valid_until_ns", "attestation"))

def siwc_operator(raw, *, operation, now_ns, source_commit, profile, windows=False):
    record = siwc_json(raw, 65536)
    if (set(record) != _SIWC_OPERATOR_KEYS or type(operation) is not str or operation not in _SIWC_OPERATIONS
            or record["operation"] != operation or record["schema_id"] != "siwc-vm-operator-binding"
            or record["schema_version"] != "1.0.0"):
        raise SIWCBlocked("OPERATOR_BINDING_INVALID")
    start, end = record["valid_from_ns"], record["valid_until_ns"]
    if (type(now_ns) is not int or type(start) is not int or type(end) is not int
            or not 0 < start <= now_ns <= end or not 0 < end - start <= 900000000000
            or not siwc_text(record["operation_alias"], 48)
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", record["operation_alias"])
            or type(record["refresh_allowed"]) is not bool):
        raise SIWCBlocked("OPERATOR_BINDING_INVALID")
    selected = record["selected_client_id"], record["selected_subject"]
    unbound = "dynamic_agent_client", "NEW_REGISTRATION_UNBOUND"
    if selected == (None,None):
        if operation != "prepare-vm-host": raise SIWCBlocked("OPERATOR_BINDING_INVALID")
    elif selected == unbound:
        if operation != "source-login": raise SIWCBlocked("OPERATOR_BINDING_INVALID")
    elif (not all(siwc_text(v) for v in selected) or selected[0] == unbound[0] or selected[1] == unbound[1]):
        raise SIWCBlocked("OPERATOR_BINDING_INVALID")
    if operation in {"source-login","source-export","dispatch"} and record["refresh_allowed"]:
        raise SIWCBlocked("OPERATOR_BINDING_INVALID")
    for key, expected, size in (("expected_source_commit", source_commit, 40),
                                 ("expected_runtime_profile_sha256", profile, 64)):
        if (type(record[key]) is not str or not re.fullmatch("[0-9a-f]{%d}" % size, record[key])
                or record[key] != expected):
            raise SIWCBlocked("OPERATOR_BINDING_INVALID")
    host = record["destination_host_id"]
    if (host is not None if operation in {"prepare-vm-host","source-login"} else not siwc_text(host)):
        raise SIWCBlocked("OPERATOR_BINDING_INVALID")
    if (windows and operation not in {"source-login","source-export"}) or (
            not windows and operation in {"source-login","source-export"}):
        raise SIWCBlocked("PLATFORM_UNSUPPORTED")
    attestation = record["attestation"]
    if operation == "preflight-only":
        if (type(attestation) is not dict or set(attestation) != {
                "purchased_credits_disabled", "model_visible_in_chatgpt", "source"}
                or attestation["purchased_credits_disabled"] is not True
                or attestation["model_visible_in_chatgpt"] is not True
                or attestation["source"] != "OPERATOR_ATTESTATION"):
            raise SIWCBlocked("OPERATOR_BINDING_INVALID")
    elif attestation is not None:
        raise SIWCBlocked("OPERATOR_BINDING_INVALID")
    root = siwc_path(record["approved_storage_root"], windows=windows)
    excluded = record["excluded_roots"]
    if type(excluded) is not list or not 1 <= len(excluded) <= 32:
        raise SIWCBlocked("OPERATOR_BINDING_INVALID")
    paths = [siwc_path(p, windows=windows) for p in excluded]
    if len(set(paths)) != len(paths) or any(siwc_overlap(root, p) for p in paths):
        raise SIWCBlocked("STORAGE_UNSAFE")
    return record

def siwc_jwt_payload(value):
    try:
        if not siwc_text(value, 65536): raise ValueError()
        parts = value.split(".")
        if len(parts) != 3 or any(not re.fullmatch(r"[A-Za-z0-9_-]+", p) for p in parts):
            raise ValueError()
        return siwc_json(base64.b64decode(parts[1] + "=" * (-len(parts[1]) % 4),
                                         altchars=b"-_", validate=True), 65536)
    except (ValueError, SIWCBlocked):
        raise SIWCBlocked("TRANSFER_INVALID") from None

def siwc_transfer(raw, binding, *, destination_host_id, source_profile, issuer, resource, scopes):
    transfer = siwc_json(raw, 262144)
    if (set(transfer) != {"schema_id", "schema_version", "registration", "credential",
                          "source_host_id", "source_validation"}
            or transfer["schema_id"] != "siwc-selected-transfer" or transfer["schema_version"] != "1.0.0"):
        raise SIWCBlocked("TRANSFER_INVALID")
    reg, cred, proof = transfer["registration"], transfer["credential"], transfer["source_validation"]
    if (type(reg) is not dict or set(reg) != {"client_id", "subject"}
            or type(cred) is not dict or set(cred) != {"issuer", "subject", "client_id", "id_token",
                "ext_agent_host_id", "access_token", "refresh_token", "token_type", "expires_at", "scopes", "saved_at"}
            or type(proof) is not dict or set(proof) != {
                "source_commit", "runtime_profile_sha256", "validated_login_identity"}
            or proof["validated_login_identity"] is not True
            or proof["source_commit"] != binding["expected_source_commit"]
            or proof["runtime_profile_sha256"] != source_profile
            or not siwc_text(transfer["source_host_id"]) or not siwc_text(destination_host_id)
            or destination_host_id != binding["destination_host_id"]
            or destination_host_id == transfer["source_host_id"]
            or cred["ext_agent_host_id"] != transfer["source_host_id"]
            or cred["issuer"] != issuer or type(cred["token_type"]) is not str or cred["token_type"].lower() != "bearer"
            or type(cred["expires_at"]) is not int or type(cred["saved_at"]) is not int
            or not 0 < cred["saved_at"] < cred["expires_at"]
            or type(cred["scopes"]) is not list or any(type(s) is not str for s in cred["scopes"])
            or len(cred["scopes"]) != len(set(cred["scopes"])) or not set(scopes) <= set(cred["scopes"])
            or any(not siwc_text(cred[k], 65536) for k in ("access_token", "refresh_token", "id_token"))):
        raise SIWCBlocked("TRANSFER_INVALID")
    for key, selected in (("client_id", "selected_client_id"), ("subject", "selected_subject")):
        if not siwc_text(reg[key]) or reg[key] != cred[key] or reg[key] != binding[selected]:
            raise SIWCBlocked("TRANSFER_INVALID")
    access, identity = siwc_jwt_payload(cred["access_token"]), siwc_jwt_payload(cred["id_token"])
    if (access.get("iss") != issuer or access.get("aud") != resource
            or access.get("client_id") != reg["client_id"] or access.get("sub", reg["subject"]) != reg["subject"]
            or type(access.get("scope")) is not str or set(access["scope"].split()) != set(cred["scopes"])
            or identity.get("iss") != issuer or identity.get("aud") != reg["client_id"]
            or identity.get("sub") != reg["subject"]):
        raise SIWCBlocked("TRANSFER_INVALID")
    # Payload consistency only, never signature verification or fresh entitlement.
    return transfer

_SIWC_STATE_KEYS = frozenset(("schema_id", "schema_version", "state", "operation_alias",
    "selected_generation", "registration_binding", "source_host_binding", "destination_host_binding",
    "export_digest", "target_binding"))

def siwc_export_state(raw, state):
    value = siwc_json(raw, 16384)
    if (set(value) != _SIWC_STATE_KEYS or value["schema_id"] != "siwc-source-export-state"
            or value["schema_version"] != "1.0.0" or value["state"] != state
            or state not in ("PENDING", "RETIRED")
            or type(value["selected_generation"]) is not int or value["selected_generation"] < 0
            or not siwc_text(value["operation_alias"], 48)
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", value["operation_alias"])
            or any(type(value[k]) is not str or not re.fullmatch(r"[0-9a-f]{64}", value[k])
                   for k in ("registration_binding", "source_host_binding", "destination_host_binding",
                             "export_digest", "target_binding"))):
        raise SIWCBlocked("EXPORT_STATE_INVALID")
    return value

def siwc_source_state(pending, retired, *, interrupted=False):
    if pending is None and retired is None: return "EXPORT_STATE_INVALID" if interrupted else "ACTIVE"
    if pending is None or retired is None: return "EXPORT_STATE_INVALID"
    try:
        p, r = siwc_export_state(pending, "PENDING"), siwc_export_state(retired, "RETIRED")
    except SIWCBlocked:
        return "EXPORT_STATE_INVALID"
    return ("SOURCE_SESSION_RETIRED" if {k:v for k,v in p.items() if k != "state"} ==
            {k:v for k,v in r.items() if k != "state"} else "EXPORT_STATE_INVALID")

class SIWCPosixSlot:
    """Existing private directory only; no repair, ancestor creation or lock deletion."""
    def __repr__(self): return "<SIWC protected slot>"

    def __init__(self, path, *, approved_root, excluded_roots):
        self.fd, self.lock_fd = None, None
        if sys.platform != "linux" or os.getuid() == 0 or not all(hasattr(os, k) for k in (
                "O_NOFOLLOW", "O_DIRECTORY", "O_CLOEXEC", "O_NONBLOCK")):
            raise SIWCBlocked("PLATFORM_UNSUPPORTED")
        target, approved = siwc_path(path), siwc_path(approved_root)
        if (target != approved and approved not in target.parents) or any(
                siwc_overlap(target, siwc_path(p)) for p in excluded_roots):
            raise SIWCBlocked("STORAGE_UNSAFE")
        # Validate syntax first, then resolve public excluded roots. The target
        # itself is walked without following links below; an alias of a release
        # root must not turn credentials inside that release into an allowed slot.
        try:
            if any(siwc_overlap(target,siwc_path(os.path.realpath(str(siwc_path(p)),strict=True)))
                   for p in excluded_roots):
                raise SIWCBlocked("STORAGE_UNSAFE")
        except OSError:
            raise SIWCBlocked("STORAGE_UNSAFE") from None
        fd = None
        try:
            fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
            self._directory(fd, leaf=target == pathlib.PurePosixPath("/"))
            for part in target.parts[1:]:
                next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                os.close(fd)
                fd = next_fd
                self._directory(fd)
            self._directory(fd, leaf=True)
            self.fd = fd
        except (OSError, SIWCBlocked):
            if fd is not None: os.close(fd)
            raise SIWCBlocked("STORAGE_UNSAFE") from None

    def _directory(self, fd, *, leaf=False):
        info = os.fstat(fd)
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, os.getuid()) or info.st_mode & 0o022
                or (leaf and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700))):
            raise SIWCBlocked("STORAGE_UNSAFE")

    def _name(self, name):
        if type(name) is not str or not re.fullmatch(r"[a-zA-Z0-9._-]{1,128}", name) or name in (".", ".."):
            raise SIWCBlocked("STORAGE_UNSAFE")

    def _file(self, fd, limit):
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != 0o600 or not 0 <= info.st_size <= limit):
            raise SIWCBlocked("STORAGE_UNSAFE")
        return info

    def _open(self, name, *, create=False, limit=262144):
        self._name(name)
        fd = os.open(name, os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK |
                     (os.O_CREAT | os.O_EXCL if create else 0), 0o600, dir_fd=self.fd)
        try:
            self._file(fd, limit)
            return fd
        except BaseException:
            os.close(fd)
            raise

    def __enter__(self):
        import fcntl
        try:
            try:
                self.lock_fd = self._open("session.lock", create=True, limit=0)
                os.fsync(self.lock_fd)
                os.fsync(self.fd)
            except FileExistsError:
                self.lock_fd = self._open("session.lock", limit=0)
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return self
        except OSError as exc:
            code = "SESSION_BUSY" if exc.errno in (errno.EACCES, errno.EAGAIN) else "STORAGE_UNSAFE"
            self.close()
            raise SIWCBlocked(code) from None
        except BaseException:
            self.close()
            raise

    def _locked(self):
        if self.lock_fd is None: raise SIWCBlocked("SESSION_NOT_LOCKED")
        self._directory(self.fd, leaf=True)

    def read(self, name, limit=262144):
        self._locked()
        fd = None
        try:
            fd = self._open(name, limit=limit)
            before = self._file(fd, limit)
            raw = os.read(fd, limit + 1)
            after = self._file(fd, limit)
            named = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
            if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
                    (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                    or (named.st_dev, named.st_ino) != (after.st_dev, after.st_ino)
                    or len(raw) != after.st_size):
                raise SIWCBlocked("STORAGE_UNSAFE")
            return raw
        except FileNotFoundError:
            if fd is not None:
                raise SIWCBlocked("STORAGE_UNSAFE") from None
            return None
        except OSError:
            raise SIWCBlocked("STORAGE_UNSAFE") from None
        finally:
            if fd is not None: os.close(fd)

    def publish(self, name, raw, limit=262144):
        self._locked()
        self._name(name)
        if type(raw) is not bytes or not 0 < len(raw) <= limit: raise SIWCBlocked("RECORD_INVALID")
        fd = None
        temp = ".siwc-" + secrets.token_hex(16)
        try:
            # Check any target kind before creating even the temporary file.
            try: os.stat(name, dir_fd=self.fd, follow_symlinks=False)
            except FileNotFoundError: pass
            else: raise SIWCBlocked("TARGET_EXISTS")
            fd = self._open(temp, create=True, limit=limit)
            if os.write(fd, raw) != len(raw): raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
            os.fsync(fd)
            expected = self._file(fd, limit)
            os.lseek(fd, 0, os.SEEK_SET)
            if os.read(fd, limit + 1) != raw: raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
            named = os.stat(temp, dir_fd=self.fd, follow_symlinks=False)
            if (named.st_dev, named.st_ino) != (expected.st_dev, expected.st_ino):
                raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
            os.link(temp, name, src_dir_fd=self.fd, dst_dir_fd=self.fd, follow_symlinks=False)
            os.unlink(temp, dir_fd=self.fd)
            os.fsync(self.fd)
            final = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
            if (final.st_dev, final.st_ino) != (expected.st_dev, expected.st_ino) or self.read(name, limit) != raw:
                raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
        except OSError:
            raise SIWCBlocked("PUBLICATION_AMBIGUOUS") from None
        finally:
            if fd is not None: os.close(fd)
        # Failed calls deliberately retain any orphan; no adoption, deletion or retry.

    def barrier(self, name, raw, limit=16384):
        self._locked()
        self._name(name)
        if type(raw) is not bytes or not 0 < len(raw) <= limit: raise SIWCBlocked("RECORD_INVALID")
        fd = None
        try:
            fd = self._open(name, create=True, limit=limit)
            if os.write(fd, raw) != len(raw): raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
            os.fsync(fd)
            os.fsync(self.fd)
            if self.read(name, limit) != raw: raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
        except OSError:
            raise SIWCBlocked("PUBLICATION_AMBIGUOUS") from None
        finally:
            if fd is not None: os.close(fd)

    def replace_credential(self, raw):
        self._locked()
        if type(raw) is not bytes or not 0 < len(raw) <= 262144: raise SIWCBlocked("RECORD_INVALID")
        before = self.read("credential.json")
        if before is None: raise SIWCBlocked("CREDENTIAL_MISSING")
        temp = ".siwc-" + secrets.token_hex(16)
        fd = self._open(temp,create=True)
        try:
            if os.write(fd,raw) != len(raw): raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
            os.fsync(fd)
            expected = self._file(fd,262144)
            os.lseek(fd,0,0)
            if os.read(fd,262145) != raw or self.read("credential.json") != before:
                raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
            os.replace(temp,"credential.json",src_dir_fd=self.fd,dst_dir_fd=self.fd)
            os.fsync(self.fd)
            actual = os.stat("credential.json",dir_fd=self.fd,follow_symlinks=False)
            if (actual.st_dev,actual.st_ino) != (expected.st_dev,expected.st_ino) or self.read("credential.json") != raw:
                raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
        except OSError:
            raise SIWCBlocked("PUBLICATION_AMBIGUOUS") from None
        finally: os.close(fd)

    def finish_pending(self, expected):
        self._locked()
        if self.read("operation-pending.json",16384) != expected: raise SIWCBlocked("SLOT_PENDING")
        os.unlink("operation-pending.json",dir_fd=self.fd)
        os.fsync(self.fd)

    def names(self):
        self._locked()
        return set(os.listdir(self.fd))

    def target_binding(self, name):
        self._locked()
        self._name(name)
        info = os.fstat(self.fd)
        return hashlib.sha256(siwc_bytes([info.st_dev,info.st_ino,name])).hexdigest()

    def close(self):
        for name in ("lock_fd", "fd"):
            fd = getattr(self, name)
            if fd is not None:
                os.close(fd)
                setattr(self, name, None)

    def __exit__(self, *exc): self.close()

def siwc_retire_source(slot, state):
    """W1/W2 only: no token-bearing file is created by this operation."""
    if siwc_source_state(slot.read("export-pending.json"), slot.read("export-retired.json")) != "ACTIVE":
        raise SIWCBlocked("SOURCE_SESSION_RETIRED")
    pending = dict(state, state="PENDING")
    retired = dict(state, state="RETIRED")
    p, r = siwc_bytes(pending), siwc_bytes(retired)
    siwc_export_state(p, "PENDING")
    siwc_export_state(r, "RETIRED")
    slot.barrier("export-pending.json", p, 16384)
    slot.barrier("export-retired.json", r, 16384)
    if siwc_source_state(slot.read("export-pending.json"), slot.read("export-retired.json")) != "SOURCE_SESSION_RETIRED":
        raise SIWCBlocked("EXPORT_STATE_INVALID")
    permit = object()
    slot._export_permit = permit
    return permit

def siwc_publish_retired_export(source, output, name, raw, state, *, permit):
    # Process-local and consumed before exposure: a restarted caller cannot finish
    # an earlier export merely because valid retirement records remain on disk.
    if permit is None or getattr(source,"_export_permit",None) is not permit:
        raise SIWCBlocked("SOURCE_SESSION_RETIRED")
    source._export_permit = None
    def verify():
        p, r = source.read("export-pending.json",16384), source.read("export-retired.json",16384)
        if (siwc_source_state(p,r) != "SOURCE_SESSION_RETIRED"
                or siwc_export_state(p,"PENDING") != dict(state,state="PENDING")
                or siwc_export_state(r,"RETIRED") != dict(state,state="RETIRED")):
            raise SIWCBlocked("EXPORT_STATE_INVALID")
    verify()
    if (type(raw) is not bytes or not 0 < len(raw) <= 262144
            or hashlib.sha256(raw).hexdigest() != state["export_digest"]
            or output.target_binding(name) != state["target_binding"]):
        raise SIWCBlocked("EXPORT_STATE_INVALID")
    output.publish(name,raw)
    verify()
    # Receipt publication remains the caller's required final barrier; this is
    # not a public success receipt and never re-enables the source.

_SIWC_RECEIPT_KEYS = frozenset(("schema_id", "schema_version", "operation", "operation_alias", "evidence_class",
    "source_commit", "prompt_sha256", "spec_sha256", "hermes_commit", "runtime_profile_sha256", "checked_at_ns",
    "status", "reason_code", "storage_checked", "registration_binding_checked", "destination_host_preserved",
    "source_retired", "generation", "route", "scopes_checked", "refresh_count", "catalogue_count", "endpoints",
    "dispatch_count", "evaluation_status", "evaluation_reason", "real_entitlement", "execution_authority",
    "capital_at_risk_usd", "orders"))
_SIWC_RECEIPT_REASONS = frozenset(("RECORD_INVALID", "OPERATOR_BINDING_INVALID", "TRANSFER_INVALID",
    "STORAGE_UNSAFE", "PLATFORM_UNSUPPORTED", "SESSION_BUSY", "SOURCE_SESSION_RETIRED", "EXPORT_STATE_INVALID",
    "TARGET_EXISTS", "PUBLICATION_AMBIGUOUS", "EXPORT_PUBLICATION_AMBIGUOUS", "DURABILITY_UNESTABLISHED",
    "PLAN_USAGE_UNVERIFIED", "CONTRACT_BINDING_PENDING"))
_SIWC_EVALUATION_REASONS = frozenset(("PLAN_USAGE_UNVERIFIED","PREFLIGHT_REPORT_INVALID","PIN_MISMATCH",
    "PROFILE_MISMATCH","API_KEY_ENV_PRESENT","PREFLIGHT_BLOCKED","UNEXPECTED_NETWORK_TARGET",
    "CONTROL_PLANE_UNEXPECTED","PLAN_SCOPE_MISSING","ACCESS_TOKEN_BINDING_INVALID","TOKEN_STALE",
    "MODEL_CATALOG_UNAVAILABLE","OAUTH_MODEL_NOT_AVAILABLE","CREDITS_STATUS_UNVERIFIED","MOCK_TRANSPORT_NOT_ELIGIBLE"))

def siwc_offline_receipt(*, operation, alias, source_commit, prompt_sha256, spec_sha256,
                         hermes_commit, profile, checked_at_ns, endpoints=()):
    # No child report/facts argument: protected fields cannot enter by projection.
    if type(endpoints) not in (tuple,list) or len(endpoints) > 2 or any(type(e) is not dict for e in endpoints):
        raise SIWCBlocked("RECEIPT_INVALID")
    receipt = dict(schema_id="siwc-vm-nondispatch-receipt", schema_version="1.0.0", operation=operation,
        operation_alias=alias, evidence_class="OFFLINE_TEST_ONLY", source_commit=source_commit,
        prompt_sha256=prompt_sha256, spec_sha256=spec_sha256, hermes_commit=hermes_commit,
        runtime_profile_sha256=profile, checked_at_ns=checked_at_ns, status="BLOCKED",
        reason_code="PLAN_USAGE_UNVERIFIED", storage_checked=False, registration_binding_checked=False,
        destination_host_preserved=False, source_retired=False, generation=None,
        route=dict(provider="custom", api_mode="codex_responses", base_url="https://api.openai.com/v1", model="gpt-6.1-sol"),
        scopes_checked=False, refresh_count=sum(e.get("method") == "POST" for e in endpoints),
        catalogue_count=sum(e.get("method") == "GET" for e in endpoints), endpoints=list(endpoints), dispatch_count=0,
        evaluation_status="PLAN_USAGE_UNVERIFIED", evaluation_reason="PLAN_USAGE_UNVERIFIED",
        real_entitlement="UNVERIFIED", execution_authority="NONE", capital_at_risk_usd=0, orders=0)
    siwc_receipt_bytes(receipt)
    return receipt

def siwc_receipt_bytes(receipt):
    """The offline publication seam admits a closed vocabulary, never child facts."""
    if type(receipt) is not dict or set(receipt) != _SIWC_RECEIPT_KEYS:
        raise SIWCBlocked("RECEIPT_INVALID")
    if any(type(receipt[k]) is not str for k in ("evidence_class","status","evaluation_status")):
        raise SIWCBlocked("RECEIPT_INVALID")
    if (receipt["schema_id"] != "siwc-vm-nondispatch-receipt" or receipt["schema_version"] != "1.0.0"
            or type(receipt["operation"]) is not str or receipt["operation"] not in _SIWC_RECEIPT_OPERATIONS
            or not siwc_text(receipt["operation_alias"], 48)
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", receipt["operation_alias"])
            or receipt["evidence_class"] not in {"OFFLINE_TEST_ONLY","OWNER_AUTHORIZED_CONTROL_PLANE"}
            or receipt["status"] not in {"DONE","BLOCKED"}
            or (receipt["reason_code"] is not None and (type(receipt["reason_code"]) is not str or receipt["reason_code"] not in _SIWC_RECEIPT_REASONS))
            or receipt["evaluation_status"] not in {"PLAN_USAGE_ELIGIBLE","PLAN_USAGE_UNVERIFIED","NOT_EVALUATED"}
            or (receipt["evaluation_reason"] is not None and (type(receipt["evaluation_reason"]) is not str or receipt["evaluation_reason"] not in _SIWC_EVALUATION_REASONS))
            or receipt["real_entitlement"] != "UNVERIFIED" or receipt["execution_authority"] != "NONE"
            or type(receipt["checked_at_ns"]) is not int or receipt["checked_at_ns"] <= 0
            or receipt["route"] != dict(provider="custom", api_mode="codex_responses",
                                          base_url="https://api.openai.com/v1", model="gpt-6.1-sol")):
        raise SIWCBlocked("RECEIPT_INVALID")
    if receipt["evidence_class"] == "OFFLINE_TEST_ONLY" and (
            receipt["status"] != "BLOCKED" or receipt["evaluation_status"] != "PLAN_USAGE_UNVERIFIED"
            or receipt["evaluation_reason"] != "PLAN_USAGE_UNVERIFIED"):
        raise SIWCBlocked("RECEIPT_INVALID")
    if receipt["status"] == "DONE" and (receipt["reason_code"] is not None or
            (receipt["operation"] == "preflight-only" and receipt["evaluation_status"] != "PLAN_USAGE_ELIGIBLE")):
        raise SIWCBlocked("RECEIPT_INVALID")
    if receipt["evaluation_status"] == "PLAN_USAGE_ELIGIBLE" and receipt["operation"] != "preflight-only":
        raise SIWCBlocked("RECEIPT_INVALID")
    for key, size in (("source_commit", 40), ("prompt_sha256", 64), ("spec_sha256", 64),
                      ("hermes_commit", 40), ("runtime_profile_sha256", 64)):
        if type(receipt[key]) is not str or not re.fullmatch("[0-9a-f]{%d}" % size, receipt[key]):
            raise SIWCBlocked("RECEIPT_INVALID")
    for key in ("storage_checked", "registration_binding_checked", "destination_host_preserved", "source_retired", "scopes_checked"):
        if type(receipt[key]) is not bool: raise SIWCBlocked("RECEIPT_INVALID")
    if receipt["generation"] is not None and (type(receipt["generation"]) is not int or receipt["generation"] < 0):
        raise SIWCBlocked("RECEIPT_INVALID")
    for key in ("dispatch_count", "capital_at_risk_usd", "orders"):
        if type(receipt[key]) is not int or receipt[key] != 0: raise SIWCBlocked("RECEIPT_INVALID")
    endpoints = receipt["endpoints"]
    if type(endpoints) is not list or len(endpoints) > 2:
        raise SIWCBlocked("RECEIPT_INVALID")
    sequence = []
    for endpoint in endpoints:
        if (type(endpoint) is not dict or set(endpoint) != {"method","host","path","status"}
                or type(endpoint["status"]) is not int or not 100 <= endpoint["status"] <= 599):
            raise SIWCBlocked("RECEIPT_INVALID")
        triple = (endpoint["method"],endpoint["host"],endpoint["path"])
        if triple == ("POST","auth.openai.com","/api/accounts/oauth/token"): sequence.append("POST")
        elif triple == ("GET","api.openai.com","/v1/models"): sequence.append("GET")
        else: raise SIWCBlocked("RECEIPT_INVALID")
    if sequence not in ([],["POST"],["GET"],["POST","GET"]): raise SIWCBlocked("RECEIPT_INVALID")
    if len(endpoints) == 2 and endpoints[0]["status"] != 200: raise SIWCBlocked("RECEIPT_INVALID")
    for key, method in (("refresh_count","POST"),("catalogue_count","GET")):
        if type(receipt[key]) is not int or receipt[key] != sequence.count(method):
            raise SIWCBlocked("RECEIPT_INVALID")
    return siwc_bytes(receipt)
'''

_SIWC_SOURCE += r'''
def siwc_windows_acl_policy(owner, current_sid, trusted, protected, entries, *, leaf, verified_volume_root=False):
    """Same conservative policy for native descriptors and synthetic ACE tests."""
    if (owner not in ({current_sid} if leaf else trusted) or not entries
            or (leaf and not protected)):
        raise SIWCBlocked("STORAGE_UNSAFE")
    for kind, flags, mask, sid in entries:
        if kind != 0: raise SIWCBlocked("STORAGE_UNSAFE")
        if leaf:
            if flags or sid not in {current_sid,"S-1-5-18"}: raise SIWCBlocked("STORAGE_UNSAFE")
        elif not flags & 8 and sid not in trusted and mask & 0x500D0156:
            # Only a separately proven root may permit sibling-directory creation.
            if not leaf and verified_volume_root is True and mask & 0x500D0156 == 4:
                continue
            raise SIWCBlocked("STORAGE_UNSAFE")

class SIWCWindowsSlot:
    """Native source-only NTFS handles; DACLs are inspected, never repaired."""
    def __repr__(self): return "<SIWC protected slot>"

    def __init__(self, path, *, approved_root, excluded_roots):
        if sys.platform != "win32": raise SIWCBlocked("PLATFORM_UNSUPPORTED")
        import ctypes as c
        from ctypes import wintypes as w
        self.c, self.w = c, w
        self.k, self.a = c.WinDLL("kernel32", use_last_error=True), c.WinDLL("advapi32", use_last_error=True)
        self.handles, self.lock_handle, self.fd = [], None, None
        self.root_identity, self.directory_checks = None, []
        P = c.c_void_p
        signatures = ((self.k, "CreateFileW", w.HANDLE, [w.LPCWSTR,w.DWORD,w.DWORD,P,w.DWORD,w.DWORD,w.HANDLE]),
            (self.k,"CloseHandle",w.BOOL,[w.HANDLE]),
            (self.k,"GetCurrentProcess",w.HANDLE,[]),
            (self.k,"LocalFree",P,[P]),
            (self.k,"GetFileInformationByHandle",w.BOOL,[w.HANDLE,P]),
            (self.k,"GetFinalPathNameByHandleW",w.DWORD,[w.HANDLE,w.LPWSTR,w.DWORD,w.DWORD]),
            (self.k,"GetVolumeInformationByHandleW",w.BOOL,[w.HANDLE,w.LPWSTR,w.DWORD,P,P,P,w.LPWSTR,w.DWORD]),
            (self.k,"GetDriveTypeW",w.UINT,[w.LPCWSTR]),
            (self.k,"FlushFileBuffers",w.BOOL,[w.HANDLE]),
            (self.k,"ReadFile",w.BOOL,[w.HANDLE,P,w.DWORD,P,P]),
            (self.k,"WriteFile",w.BOOL,[w.HANDLE,P,w.DWORD,P,P]),
            (self.k,"SetFilePointerEx",w.BOOL,[w.HANDLE,c.c_longlong,P,w.DWORD]),
            (self.k,"MoveFileExW",w.BOOL,[w.LPCWSTR,w.LPCWSTR,w.DWORD]),
            (self.k,"ReplaceFileW",w.BOOL,[w.LPCWSTR,w.LPCWSTR,w.LPCWSTR,w.DWORD,P,P]),
            (self.k,"DeleteFileW",w.BOOL,[w.LPCWSTR]),
            (self.k,"LockFileEx",w.BOOL,[w.HANDLE,w.DWORD,w.DWORD,w.DWORD,w.DWORD,P]),
            (self.k,"CreateDirectoryW",w.BOOL,[w.LPCWSTR,P]),
            (self.a,"OpenProcessToken",w.BOOL,[w.HANDLE,w.DWORD,P]),
            (self.a,"GetTokenInformation",w.BOOL,[w.HANDLE,c.c_int,P,w.DWORD,P]),
            (self.a,"ConvertSidToStringSidW",w.BOOL,[P,P]),
            (self.a,"ConvertStringSecurityDescriptorToSecurityDescriptorW",w.BOOL,[w.LPCWSTR,w.DWORD,P,P]),
            (self.a,"GetSecurityInfo",w.DWORD,[w.HANDLE,c.c_int,w.DWORD,P,P,P,P,P]),
            (self.a,"GetSecurityDescriptorControl",w.BOOL,[P,P,P]),
            (self.a,"GetAce",w.BOOL,[P,w.DWORD,P]))
        for dll, name, result, args in signatures:
            function = getattr(dll, name)
            function.restype, function.argtypes = result, args
        class Info(c.Structure):
            _fields_ = [("attributes",w.DWORD),("creation",w.FILETIME),("access",w.FILETIME),
                ("write",w.FILETIME),("volume",w.DWORD),("size_high",w.DWORD),("size_low",w.DWORD),
                ("links",w.DWORD),("index_high",w.DWORD),("index_low",w.DWORD)]
        class Overlapped(c.Structure):
            _fields_ = [("internal",c.c_size_t),("internal_high",c.c_size_t),
                        ("offset",w.DWORD),("offset_high",w.DWORD),("event",w.HANDLE)]
        class Security(c.Structure):
            _fields_ = [("length",w.DWORD),("descriptor",P),("inherit",w.BOOL)]
        self.Info, self.Overlapped, self.Security = Info, Overlapped, Security
        token = w.HANDLE()
        self._ok(self.a.OpenProcessToken(self.k.GetCurrentProcess(), 8, c.byref(token)))
        try:
            size = w.DWORD()
            self.a.GetTokenInformation(token, 1, None, 0, c.byref(size))
            data = c.create_string_buffer(size.value)
            self._ok(self.a.GetTokenInformation(token, 1, data, size, c.byref(size)))
            self.sid = self._sid(c.cast(data, c.POINTER(P))[0])
            elevated = w.DWORD()
            self._ok(self.a.GetTokenInformation(token, 20, c.byref(elevated), c.sizeof(elevated), c.byref(size)))
            if elevated.value: raise SIWCBlocked("PLATFORM_UNSUPPORTED")
        finally: self.k.CloseHandle(token)
        # TrustedInstaller is part of the Windows administrative trust base and
        # owns ordinary system-volume ancestors. Resolve that local service SID.
        self.a.LookupAccountNameW.argtypes = [w.LPCWSTR,w.LPCWSTR,P,P,w.LPWSTR,P,P]
        self.a.LookupAccountNameW.restype = w.BOOL
        sid_size, domain_size, use = w.DWORD(), w.DWORD(), w.DWORD()
        self.a.LookupAccountNameW(None,"NT SERVICE\\TrustedInstaller",None,c.byref(sid_size),
                                 None,c.byref(domain_size),c.byref(use))
        service_sid, domain = c.create_string_buffer(sid_size.value), c.create_unicode_buffer(domain_size.value)
        self._ok(self.a.LookupAccountNameW(None,"NT SERVICE\\TrustedInstaller",service_sid,c.byref(sid_size),
                                          domain,c.byref(domain_size),c.byref(use)))
        self.trusted = {self.sid,"S-1-5-18","S-1-5-32-544",self._sid(service_sid)}
        target, approved = siwc_path(path, windows=True), siwc_path(approved_root, windows=True)
        if (target != approved and approved not in target.parents) or any(
                siwc_overlap(target, siwc_path(p, windows=True)) for p in excluded_roots):
            raise SIWCBlocked("STORAGE_UNSAFE")
        if self.k.GetDriveTypeW(target.anchor) != 3: raise SIWCBlocked("PLATFORM_UNSUPPORTED")
        self.path = target
        try:
            current = pathlib.PureWindowsPath(target.anchor)
            for part in (None, *target.parts[1:]):
                if part is not None: current /= part
                handle = self._open_path(current, directory=True)
                self.handles.append(handle)
                if part is None:
                    self._prove_volume_root(handle)
                self._check(handle, current, directory=True, leaf=current == target)
                self.directory_checks.append((handle, current))
            self.fd = self.handles[-1]
            canonical_target = self._canonical_path(self.fd)
            for excluded in excluded_roots:
                # Excluded roots are public source/release directories. Follow
                # their aliases only to exclude their canonical targets, retain
                # no-delete-sharing handles, and never inspect private files.
                handle = self._open_path(siwc_path(excluded,windows=True),directory=True,follow=True)
                self.handles.append(handle)
                if siwc_overlap(canonical_target,self._canonical_path(handle)):
                    raise SIWCBlocked("STORAGE_UNSAFE")
            volume, flags, fs = w.DWORD(), w.DWORD(), c.create_unicode_buffer(32)
            self._ok(self.k.GetVolumeInformationByHandleW(self.fd,None,0,c.byref(volume),None,
                                                         c.byref(flags),fs,len(fs)))
            if fs.value != "NTFS" or not flags.value & 8: raise SIWCBlocked("PLATFORM_UNSUPPORTED")
        except BaseException:
            self.close()
            raise

    def _ok(self, result):
        if not result: raise SIWCBlocked("STORAGE_UNSAFE")

    def _prove_volume_root(self, handle):
        """An internal reference derived from the kernel handle, never an input alias."""
        c, w = self.c, self.w
        name = c.create_unicode_buffer(32768)
        size = self.k.GetFinalPathNameByHandleW(handle,name,len(name),1)
        if (not 0 < size < len(name) or not re.fullmatch(
                r"\\\\\?\\Volume\{[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\}\\",name.value)):
            raise SIWCBlocked("STORAGE_UNSAFE")
        reference = self._open_path(name.value,directory=True)
        self.handles.append(reference)
        identities = []
        for candidate in (handle,reference):
            info = self.Info()
            self._ok(self.k.GetFileInformationByHandle(candidate,c.byref(info)))
            if info.attributes & 0x400 or not info.attributes & 0x10:
                raise SIWCBlocked("STORAGE_UNSAFE")
            volume, flags, fs = w.DWORD(), w.DWORD(), c.create_unicode_buffer(32)
            self._ok(self.k.GetVolumeInformationByHandleW(candidate,None,0,c.byref(volume),None,
                                                         c.byref(flags),fs,len(fs)))
            if fs.value != "NTFS" or not flags.value & 8 or volume.value != info.volume:
                raise SIWCBlocked("PLATFORM_UNSUPPORTED")
            identities.append((info.volume,info.index_high,info.index_low))
        if identities[0] != identities[1]: raise SIWCBlocked("STORAGE_UNSAFE")
        self.root_identity = identities[0]

    def _sid(self, ptr):
        result = self.w.LPWSTR()
        self._ok(self.a.ConvertSidToStringSidW(ptr, self.c.byref(result)))
        try: return result.value
        finally: self.k.LocalFree(self.c.cast(result, self.c.c_void_p))

    def _acl(self, handle, *, leaf, verified_volume_root=False):
        c, w = self.c, self.w
        owner, acl, descriptor = c.c_void_p(), c.c_void_p(), c.c_void_p()
        if self.a.GetSecurityInfo(handle,1,5,c.byref(owner),None,c.byref(acl),None,c.byref(descriptor)):
            raise SIWCBlocked("STORAGE_UNSAFE")
        try:
            if not owner or not acl:
                raise SIWCBlocked("STORAGE_UNSAFE")
            control, revision = w.WORD(), w.DWORD()
            self._ok(self.a.GetSecurityDescriptorControl(descriptor,c.byref(control),c.byref(revision)))
            count = c.c_ushort.from_address(acl.value + 4).value
            if not count or count > 1024: raise SIWCBlocked("STORAGE_UNSAFE")
            entries = []
            for i in range(count):
                ace = c.c_void_p()
                self._ok(self.a.GetAce(acl,i,c.byref(ace)))
                kind, flags = c.c_ubyte.from_address(ace.value).value, c.c_ubyte.from_address(ace.value+1).value
                if kind != 0 or c.c_ushort.from_address(ace.value+2).value < 16:
                    raise SIWCBlocked("STORAGE_UNSAFE")
                mask = w.DWORD.from_address(ace.value+4).value
                sid = self._sid(c.c_void_p(ace.value+8))
                entries.append((kind,flags,mask,sid))
            siwc_windows_acl_policy(self._sid(owner),self.sid,self.trusted,
                                    bool(control.value & 0x1000),entries,leaf=leaf,
                                    verified_volume_root=verified_volume_root)
        finally: self.k.LocalFree(descriptor)

    def _canonical_path(self, handle):
        name = self.c.create_unicode_buffer(32768)
        size = self.k.GetFinalPathNameByHandleW(handle,name,len(name),1)
        if not 0 < size < len(name): raise SIWCBlocked("STORAGE_UNSAFE")
        return pathlib.PureWindowsPath(name.value)

    def _open_path(self, path, *, directory=False, create=False, lock=False, follow=False):
        c, w = self.c, self.w
        descriptor = c.c_void_p()
        security = None
        if create:
            self._ok(self.a.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                "O:"+self.sid+"D:P(A;;FA;;;"+self.sid+")(A;;FA;;;SY)",1,c.byref(descriptor),None))
            security = self.Security(c.sizeof(self.Security),descriptor,False)
        try:
            access = 0x20000 | (0 if directory else 0xC0000000)
            flags = (0 if follow else 0x200000) | (0x2000000 if directory else 0x80000000)
            handle = self.k.CreateFileW(str(path),access,3 if directory or lock else 0,
                c.byref(security) if security is not None else None,1 if create else 3,flags,None)
            if handle == c.c_void_p(-1).value:
                error = c.get_last_error()
                if error in (80,183): raise FileExistsError()
                if error in (2,3): raise FileNotFoundError()
                if error in (32,33): raise SIWCBlocked("SESSION_BUSY" if lock else "STORAGE_UNSAFE")
                raise SIWCBlocked("STORAGE_UNSAFE")
            return handle
        finally:
            if descriptor: self.k.LocalFree(descriptor)

    def _check(self, handle, path, *, directory=False, leaf=True, limit=262144):
        c = self.c
        info = self.Info()
        self._ok(self.k.GetFileInformationByHandle(handle,c.byref(info)))
        if (info.attributes & 0x400 or bool(info.attributes & 0x10) != directory
                or (not directory and (info.links != 1 or (info.size_high << 32 | info.size_low) > limit))):
            raise SIWCBlocked("STORAGE_UNSAFE")
        name = c.create_unicode_buffer(32768)
        size = self.k.GetFinalPathNameByHandleW(handle,name,len(name),0)
        if not 0 < size < len(name) or pathlib.PureWindowsPath(name.value.removeprefix("\\\\?\\")) != path:
            raise SIWCBlocked("STORAGE_UNSAFE")
        identity = info.volume, info.index_high, info.index_low
        if self.root_identity is None or info.volume != self.root_identity[0]:
            raise SIWCBlocked("STORAGE_UNSAFE")
        self._acl(handle,leaf=leaf,verified_volume_root=(directory and not leaf and
            handle == self.handles[0] and identity == self.root_identity))
        return identity

    def __enter__(self):
        try:
            try: self.lock_handle = self._open_path(self.path/"session.lock",create=True,lock=True)
            except FileExistsError: self.lock_handle = self._open_path(self.path/"session.lock",lock=True)
            self._check(self.lock_handle,self.path/"session.lock",limit=0)
            overlap = self.Overlapped()
            if not self.k.LockFileEx(self.lock_handle,3,0,1,0,self.c.byref(overlap)):
                raise SIWCBlocked("SESSION_BUSY")
            self._overlap = overlap
            return self
        except BaseException:
            self.close()
            raise

    def _locked(self):
        if self.lock_handle is None: raise SIWCBlocked("SESSION_NOT_LOCKED")
        for handle,path in self.directory_checks:
            self._check(handle,path,directory=True,leaf=path == self.path)

    def _length(self, handle):
        info = self.Info()
        self._ok(self.k.GetFileInformationByHandle(handle,self.c.byref(info)))
        return info.size_high << 32 | info.size_low

    def _name(self, name):
        if type(name) is not str or not re.fullmatch(r"[a-zA-Z0-9._-]{1,128}",name) or name in (".",".."):
            raise SIWCBlocked("STORAGE_UNSAFE")
        siwc_path(str(self.path/name),windows=True)

    def read(self, name, limit=262144):
        self._locked()
        self._name(name)
        try: handle = self._open_path(self.path/name)
        except FileNotFoundError: return None
        try:
            before = self._check(handle,self.path/name,limit=limit)
            data, size = self.c.create_string_buffer(limit+1), self.w.DWORD()
            self._ok(self.k.ReadFile(handle,data,limit+1,self.c.byref(size),None))
            if (size.value > limit or size.value != self._length(handle)
                    or self._check(handle,self.path/name,limit=limit) != before):
                raise SIWCBlocked("STORAGE_UNSAFE")
            return data.raw[:size.value]
        finally: self.k.CloseHandle(handle)

    def publish(self, name, raw, limit=262144):
        self._locked()
        self._name(name)
        if type(raw) is not bytes or not 0 < len(raw) <= limit: raise SIWCBlocked("RECORD_INVALID")
        if self.read(name,limit) is not None: raise SIWCBlocked("TARGET_EXISTS")
        temp = ".siwc-" + secrets.token_hex(16)
        handle = self._open_path(self.path/temp,create=True)
        try:
            expected = self._check(handle,self.path/temp,limit=limit)
            size = self.w.DWORD()
            self._ok(self.k.WriteFile(handle,raw,len(raw),self.c.byref(size),None))
            if size.value != len(raw): raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
            self._ok(self.k.FlushFileBuffers(handle))
            self._ok(self.k.SetFilePointerEx(handle,0,None,0))
            data = self.c.create_string_buffer(len(raw))
            self._ok(self.k.ReadFile(handle,data,len(raw),self.c.byref(size),None))
            if (size.value != len(raw) or self._length(handle) != len(raw) or data.raw != raw
                    or self._check(handle,self.path/temp,limit=limit) != expected):
                raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
        finally: self.k.CloseHandle(handle)
        # No-delete-sharing handle is closed before rename; directory handles remain.
        self._ok(self.k.MoveFileExW(str(self.path/temp),str(self.path/name),8))
        final = self._open_path(self.path/name)
        try:
            if self._check(final,self.path/name,limit=limit) != expected or self._length(final) != len(raw):
                raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
            self._ok(self.k.FlushFileBuffers(final))
            if self._check(final,self.path/name,limit=limit) != expected: raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
        finally: self.k.CloseHandle(final)
        if self.read(name,limit) != raw: raise SIWCBlocked("PUBLICATION_AMBIGUOUS")

    def barrier(self, name, raw, limit=16384):
        self._locked()
        self._name(name)
        if type(raw) is not bytes or not 0 < len(raw) <= limit: raise SIWCBlocked("RECORD_INVALID")
        try: handle = self._open_path(self.path/name,create=True)
        except (FileExistsError, FileNotFoundError): raise SIWCBlocked("PUBLICATION_AMBIGUOUS") from None
        try:
            expected = self._check(handle,self.path/name,limit=limit)
            size = self.w.DWORD()
            self._ok(self.k.WriteFile(handle,raw,len(raw),self.c.byref(size),None))
            if size.value != len(raw): raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
            self._ok(self.k.FlushFileBuffers(handle))
            self._ok(self.k.SetFilePointerEx(handle,0,None,0))
            data = self.c.create_string_buffer(len(raw))
            self._ok(self.k.ReadFile(handle,data,len(raw),self.c.byref(size),None))
            if (size.value != len(raw) or self._length(handle) != len(raw) or data.raw != raw
                    or self._check(handle,self.path/name,limit=limit) != expected):
                raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
        finally: self.k.CloseHandle(handle)

    def replace_credential(self, raw):
        self._locked()
        if type(raw) is not bytes or not 0 < len(raw) <= 262144: raise SIWCBlocked("RECORD_INVALID")
        before = self.read("credential.json")
        if before is None: raise SIWCBlocked("CREDENTIAL_MISSING")
        temp = ".siwc-" + secrets.token_hex(16)
        handle = self._open_path(self.path/temp,create=True)
        try:
            expected = self._check(handle,self.path/temp)
            size = self.w.DWORD()
            self._ok(self.k.WriteFile(handle,raw,len(raw),self.c.byref(size),None))
            if size.value != len(raw): raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
            self._ok(self.k.FlushFileBuffers(handle))
            self._ok(self.k.SetFilePointerEx(handle,0,None,0))
            data = self.c.create_string_buffer(len(raw))
            self._ok(self.k.ReadFile(handle,data,len(raw),self.c.byref(size),None))
            if (size.value != len(raw) or data.raw != raw or self._length(handle) != len(raw)
                    or self._check(handle,self.path/temp) != expected):
                raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
        finally: self.k.CloseHandle(handle)
        if self.read("credential.json") != before: raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
        # All target/temp handles are closed; parents and slot lock remain held.
        self._ok(self.k.ReplaceFileW(str(self.path/"credential.json"),str(self.path/temp),None,0,None,None))
        final = self._open_path(self.path/"credential.json")
        try:
            if self._check(final,self.path/"credential.json") != expected:
                raise SIWCBlocked("PUBLICATION_AMBIGUOUS")
            self._ok(self.k.FlushFileBuffers(final))
        finally: self.k.CloseHandle(final)
        if self.read("credential.json") != raw: raise SIWCBlocked("PUBLICATION_AMBIGUOUS")

    def finish_pending(self, expected):
        self._locked()
        if self.read("operation-pending.json",16384) != expected: raise SIWCBlocked("SLOT_PENDING")
        self._ok(self.k.DeleteFileW(str(self.path/"operation-pending.json")))

    def names(self):
        self._locked()
        return set(os.listdir(self.path))

    def target_binding(self, name):
        self._locked()
        self._name(name)
        identity = self._check(self.fd,self.path,directory=True)
        return hashlib.sha256(siwc_bytes([*identity,name.casefold()])).hexdigest()

    def close(self):
        if self.lock_handle is not None:
            self.k.CloseHandle(self.lock_handle)
            self.lock_handle = None
        for handle in reversed(self.handles): self.k.CloseHandle(handle)
        self.handles = []
        self.fd = None

    def __exit__(self, *exc): self.close()
'''

_SIWC_SOURCE += r'''
def siwc_prepare_host(slot):
    """Child-local primitive, called only after the new operation's bound admission."""
    if slot.names() - {"session.lock", "host_id.json"}: raise SIWCBlocked("TARGET_EXISTS")
    existing = slot.read("host_id.json",4096)
    if existing is not None:
        record = siwc_json(existing,4096)
        if set(record) != {"ext_agent_host_id"} or not siwc_text(record["ext_agent_host_id"]):
            raise SIWCBlocked("RECORD_INVALID")
        return
    import uuid
    slot.publish("host_id.json",siwc_bytes(dict(ext_agent_host_id="urn:uuid:"+str(uuid.uuid4()))),4096)

def siwc_import_transfer(slot, raw, binding, *, source_profile, issuer, resource, scopes):
    if slot.names() - {"session.lock", "host_id.json"}: raise SIWCBlocked("TARGET_EXISTS")
    host = siwc_json(slot.read("host_id.json",4096),4096)
    if set(host) != {"ext_agent_host_id"}: raise SIWCBlocked("TRANSFER_INVALID")
    transfer = siwc_transfer(raw,binding,destination_host_id=host["ext_agent_host_id"],source_profile=source_profile,
                             issuer=issuer,resource=resource,scopes=scopes)
    marker = dict(schema_id="siwc-import-state",schema_version="1.0.0",state="PENDING",
                  transfer_digest=hashlib.sha256(raw).hexdigest())
    slot.barrier("import-pending.json",siwc_bytes(marker))
    slot.publish("registration.json",siwc_bytes(transfer["registration"]),16384)
    slot.publish("credential.json",siwc_bytes(dict(transfer["credential"],ext_agent_host_id=host["ext_agent_host_id"])))
    slot.barrier("import-committed.json",siwc_bytes(dict(marker,state="COMMITTED")))

def siwc_slot_usable(slot):
    """No repair or fallback: orphan, interrupted or retired slots refuse."""
    names = slot.names()
    allowed = {"session.lock","host_id.json","registration.json","credential.json",
               "export-pending.json","export-retired.json","import-pending.json","import-committed.json"}
    state = siwc_source_state(slot.read("export-pending.json",16384),slot.read("export-retired.json",16384))
    if state != "ACTIVE": raise SIWCBlocked(state)
    if "operation-pending.json" in names: raise SIWCBlocked("SLOT_PENDING")
    if any(n not in allowed and not re.fullmatch(r"mutation-commit-[1-9][0-9]{0,18}\.json",n)
           and not re.fullmatch(r"preflight-used-[a-z0-9][a-z0-9-]{0,47}\.json",n)
           for n in names): raise SIWCBlocked("SLOT_PENDING")
    for name in names:
        if name.startswith("preflight-used-"):
            used = siwc_json(slot.read(name,16384),16384)
            if used != {"schema_id":"siwc-preflight-consumed","operation_alias":name[15:-5]}:
                raise SIWCBlocked("SLOT_PENDING")
    pending, committed = slot.read("import-pending.json",16384),slot.read("import-committed.json",16384)
    if pending is None and committed is None: return
    if pending is None or committed is None: raise SIWCBlocked("SLOT_PENDING")
    p, c = siwc_json(pending,16384), siwc_json(committed,16384)
    if (set(p) != {"schema_id","schema_version","state","transfer_digest"}
            or p["schema_id"] != "siwc-import-state" or p["schema_version"] != "1.0.0"
            or p["state"] != "PENDING" or type(p["transfer_digest"]) is not str
            or not re.fullmatch(r"[0-9a-f]{64}",p["transfer_digest"])
            or c != dict(p,state="COMMITTED")
            or not {"credential.json","registration.json","host_id.json"} <= names):
        raise SIWCBlocked("SLOT_PENDING")

def siwc_parse_cli(argv):
    """Private parse-only seam: usage errors never inspect a file or echo argv."""
    if type(argv) is not list or any(type(arg) is not str or not arg for arg in argv):
        raise SIWCBlocked("USAGE_INVALID")
    if argv in ([],["--help"],["-h"]): return None
    if argv[0] not in {"prepare-vm-host","import-selected","preflight-only"}:
        raise SIWCBlocked("USAGE_INVALID")
    flags = {"--pin-root","--credential-dir","--operator-record","--receipt"}
    if argv[0] == "import-selected": flags.add("--transfer-file")
    if len(argv) != 1+2*len(flags): raise SIWCBlocked("USAGE_INVALID")
    result = {"operation":argv[0]}
    for flag, value in zip(argv[1::2],argv[2::2]):
        if flag not in flags or flag in result or value.startswith("-"):
            raise SIWCBlocked("USAGE_INVALID")
        result[flag] = value
    if set(result) != flags | {"operation"}: raise SIWCBlocked("USAGE_INVALID")
    return result

class SIWCPreflightBudget:
    """Request-hook primitive: consumes each attempt before send, never retries."""
    def __repr__(self): return "<SIWC non-dispatch budget>"

    def __init__(self, *, refresh_required, refresh_allowed):
        if type(refresh_required) is not bool or type(refresh_allowed) is not bool:
            raise SIWCBlocked("PREFLIGHT_REFUSED")
        self.required, self.allowed = refresh_required, refresh_allowed
        self.refresh_count, self.catalogue_count, self.stopped, self.inflight = 0,0,False,None
        self._endpoints = []

    def admit(self, method, url):
        from urllib.parse import urlsplit
        if self.stopped or self.inflight is not None:
            self.stopped = True
            raise SIWCBlocked("PREFLIGHT_REFUSED")
        try:
            # urlsplit strips controls/leading spaces; reject those bytes before
            # parsing so normalization cannot turn a forbidden target into one.
            if type(url) is not str or any(ord(char) <= 32 or ord(char) == 127 for char in url):
                raise ValueError()
            parts = urlsplit(url)
            if (parts.scheme != "https" or parts.username is not None
                    or parts.password is not None or parts.port not in (None,443) or parts.query or parts.fragment):
                raise ValueError()
            target = method,parts.hostname,parts.path
            if target == ("POST","auth.openai.com","/api/accounts/oauth/token"):
                if not self.required or not self.allowed or self.refresh_count or self.catalogue_count: raise ValueError()
                self.refresh_count += 1
            elif target == ("GET","api.openai.com","/v1/models"):
                if self.required or self.catalogue_count: raise ValueError()
                self.catalogue_count += 1
            else: raise ValueError()
            self.inflight = target
        except (TypeError,ValueError,UnicodeError):
            self.stopped = True
            raise SIWCBlocked("PREFLIGHT_REFUSED") from None

    def complete(self, status):
        if self.inflight is None or self.stopped: raise SIWCBlocked("PREFLIGHT_REFUSED")
        target = self.inflight
        self.inflight = None
        if type(status) is not int or not 100 <= status <= 599:
            self.stopped = True
            raise SIWCBlocked("PREFLIGHT_REFUSED")
        self._endpoints.append(dict(zip(("method","host","path","status"),(*target,status))))
        if status != 200:
            self.stopped = True
            raise SIWCBlocked("PREFLIGHT_REFUSED")
        if target[0] == "POST": self.required = False

    def endpoints(self):
        return [dict(e) for e in self._endpoints]

def siwc_read_private_file(path, excluded, limit):
    """Read only the bound private input, without creating a bootstrap lock."""
    windows = sys.platform == "win32"
    target = siwc_path(path,windows=windows)
    cls = SIWCWindowsSlot if windows else SIWCPosixSlot
    storage = cls(str(target.parent),approved_root=str(target.parent),excluded_roots=excluded)
    handle = None
    try:
        if windows:
            handle = storage._open_path(target)
            identity = storage._check(handle,target,limit=limit)
            data, size = storage.c.create_string_buffer(limit+1), storage.w.DWORD()
            storage._ok(storage.k.ReadFile(handle,data,limit+1,storage.c.byref(size),None))
            if size.value > limit or storage._length(handle) != size.value or storage._check(handle,target,limit=limit) != identity:
                raise SIWCBlocked("STORAGE_UNSAFE")
            return data.raw[:size.value]
        handle = storage._open(target.name,limit=limit)
        before = storage._file(handle,limit)
        raw = os.read(handle,limit+1)
        after = storage._file(handle,limit)
        named = os.stat(target.name,dir_fd=storage.fd,follow_symlinks=False)
        if (len(raw) != before.st_size or (before.st_dev,before.st_ino,before.st_mtime_ns,before.st_size) !=
                (after.st_dev,after.st_ino,after.st_mtime_ns,after.st_size) or
                (named.st_dev,named.st_ino) != (before.st_dev,before.st_ino)):
            raise SIWCBlocked("STORAGE_UNSAFE")
        return raw
    except OSError:
        raise SIWCBlocked("STORAGE_UNSAFE") from None
    finally:
        if handle is not None:
            if windows: storage.k.CloseHandle(handle)
            else: os.close(handle)
        storage.close()

def siwc_generation(slot):
    commits = sorted((int(n[16:-5]),n) for n in slot.names()
                     if re.fullmatch(r"mutation-commit-[1-9][0-9]{0,18}\.json",n))
    if not commits: return 0
    if [g for g,n in commits] != list(range(1,len(commits)+1)):
        raise SIWCBlocked("SLOT_PENDING")
    for expected_generation, committed_name in commits:
        metadata = siwc_json(slot.read(committed_name,16384),16384)
        if (set(metadata) != {"schema_id","generation","credential_digest","registration_digest","validated_login_identity"}
                or metadata["schema_id"] != "siwc-mutation-commit" or type(metadata["generation"]) is not int
                or metadata["generation"] != expected_generation or metadata["validated_login_identity"] is not True
                or any(type(metadata[k]) is not str or not re.fullmatch(r"[0-9a-f]{64}",metadata[k])
                       for k in ("credential_digest","registration_digest"))):
            raise SIWCBlocked("SLOT_PENDING")
    generation, name = commits[-1]
    record = siwc_json(slot.read(name,16384),16384)
    if (set(record) != {"schema_id","generation","credential_digest","registration_digest","validated_login_identity"}
            or record["schema_id"] != "siwc-mutation-commit" or type(record["generation"]) is not int
            or record["generation"] != generation or record["validated_login_identity"] is not True
            or record["credential_digest"] != hashlib.sha256(slot.read("credential.json")).hexdigest()
            or record["registration_digest"] != hashlib.sha256(slot.read("registration.json",16384)).hexdigest()):
        raise SIWCBlocked("SLOT_PENDING")
    return generation

def siwc_begin_mutation(slot, operation, alias):
    siwc_slot_usable(slot)
    generation = siwc_generation(slot)+1
    if generation >= 10**19: raise SIWCBlocked("SLOT_PENDING")
    pending = siwc_bytes(dict(schema_id="siwc-mutation-pending",operation=operation,
                             operation_alias=alias,generation=generation))
    slot.barrier("operation-pending.json",pending,16384)
    return pending

def siwc_complete_mutation(slot, pending):
    state = siwc_json(pending,16384)
    committed = siwc_bytes(dict(schema_id="siwc-mutation-commit",generation=state["generation"],
        credential_digest=hashlib.sha256(slot.read("credential.json")).hexdigest(),
        registration_digest=hashlib.sha256(slot.read("registration.json",16384)).hexdigest(),validated_login_identity=True))
    slot.barrier("mutation-commit-%d.json" % state["generation"],committed,16384)
    slot.finish_pending(pending)

def siwc_login_selection(slot, binding):
    pair = binding["selected_client_id"],binding["selected_subject"]
    if pair == ("dynamic_agent_client","NEW_REGISTRATION_UNBOUND"):
        if slot.names() != {"session.lock"}: raise SIWCBlocked("OPERATOR_BINDING_INVALID")
        return True
    siwc_slot_usable(slot)
    registration = siwc_json(slot.read("registration.json",16384),16384)
    credential = siwc_json(slot.read("credential.json"),262144)
    host = siwc_json(slot.read("host_id.json",4096),4096)
    if (set(registration) != {"client_id","subject"} or
            (registration["client_id"],registration["subject"]) != pair or
            (credential.get("client_id"),credential.get("subject")) != pair or
            credential.get("ext_agent_host_id") != host.get("ext_agent_host_id") or not siwc_generation(slot)):
        raise SIWCBlocked("OPERATOR_BINDING_INVALID")
    return False
'''

# Executed ONLY inside the pinned Hermes virtualenv child (``python -I -B -c``); spec on stdin.
_CHILD_SOURCE = r'''
import base64, hashlib, json, os, secrets, socket, sys, threading, time, urllib.parse, urllib.request
spec = json.loads(sys.stdin.buffer.read())
MODE, PHASE = spec["mode"], spec["phase"]
C = spec["constants"]
if PHASE != "login":
    def deny_process(event, args):
        if event.startswith(("subprocess.","os.system","os.posix_spawn","os.spawn","os.exec","os.startfile")):
            raise OSError("process denied")
    sys.addaudithook(deny_process)
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
slot, binding, mutation_pending, preflight_budget, output_slot = None, None, None, None, None
receipt_attempted, receipt_permitted = False, False

def admit_slot():
    global slot, binding
    operation = {"login":"source-login","preflight":"preflight-only","dispatch":"dispatch",
                 "prepare-vm-host":"prepare-vm-host","import-selected":"import-selected",
                 "source-export":"source-export"}.get(PHASE)
    if not operation or not spec.get("operator_record_path"):
        raise SIWCBlocked("OPERATOR_BINDING_INVALID")
    excluded = spec["excluded_roots"]
    raw = siwc_read_private_file(spec["operator_record_path"],excluded,65536)
    binding = siwc_operator(raw,operation=operation,now_ns=time.time_ns(),
        source_commit=spec["source_commit"],profile=spec["runtime_profile_sha256"],windows=sys.platform == "win32")
    operator_path = siwc_path(spec["operator_record_path"],windows=sys.platform == "win32")
    approved = siwc_path(binding["approved_storage_root"],windows=sys.platform == "win32")
    if approved not in operator_path.parents: raise SIWCBlocked("STORAGE_UNSAFE")
    cls = SIWCWindowsSlot if sys.platform == "win32" else SIWCPosixSlot
    slot = cls(CRED,approved_root=binding["approved_storage_root"],
               excluded_roots=list(set(binding["excluded_roots"]+excluded)))
    slot.__enter__()
    if spec.get("receipt_only"):
        if PHASE != "preflight": raise SIWCBlocked("OPERATOR_BINDING_INVALID")
        return
    if PHASE == "login":
        siwc_login_selection(slot,binding)
    elif PHASE not in {"prepare-vm-host","import-selected"}:
        siwc_slot_usable(slot)
        siwc_generation(slot)
        credential = load_credential()
        registration = read("registration.json")
        host = read("host_id.json")
        if (type(registration) is not dict or set(registration) != {"client_id","subject"}
                or registration != {"client_id":binding["selected_client_id"],"subject":binding["selected_subject"]}
                or credential.get("client_id") != registration["client_id"]
                or credential.get("subject") != registration["subject"]
                or credential.get("issuer") != C["issuer"] or type(host) is not dict
                or set(host) != {"ext_agent_host_id"}
                or credential.get("ext_agent_host_id") != host["ext_agent_host_id"]
                or (PHASE != "source-export" and host["ext_agent_host_id"] != binding["destination_host_id"])):
            raise SIWCBlocked("OPERATOR_BINDING_INVALID")
        claims = siwc_jwt_payload(credential.get("id_token"))
        if claims.get("iss") != C["issuer"] or claims.get("aud") != registration["client_id"] or claims.get("sub") != registration["subject"]:
            raise SIWCBlocked("TRANSFER_INVALID")
        validate_issued_access(credential)
    if PHASE == "dispatch" and not spec.get("dispatch_admission"):
        raise SIWCBlocked("OPERATOR_BINDING_INVALID")
    if PHASE == "preflight":
        report.update(operator_attestation_checked=True,storage_checked=True,registration_binding_checked=True,
                      destination_host_preserved=True,scopes_checked=True,generation=siwc_generation(slot))

def admit_output():
    global output_slot
    path = spec.get("receipt_file")
    if not path: raise SIWCBlocked("RECORD_INVALID")
    target = siwc_path(path,windows=sys.platform == "win32")
    credentials = siwc_path(CRED,windows=sys.platform == "win32")
    if siwc_overlap(target.parent,credentials): raise SIWCBlocked("STORAGE_UNSAFE")
    cls = SIWCWindowsSlot if sys.platform == "win32" else SIWCPosixSlot
    output_slot = cls(str(target.parent),approved_root=binding["approved_storage_root"],
                      excluded_roots=list(set(spec["excluded_roots"]+binding["excluded_roots"])))
    output_slot.__enter__()
    if output_slot.read(target.name) is not None: raise SIWCBlocked("TARGET_EXISTS")
    return target.name

def publish_control_receipt(report):
    global receipt_attempted
    receipt_attempted = True
    evaluation = spec.get("evaluation") or {"status":"NOT_EVALUATED","reason_code":None}
    receipt = siwc_offline_receipt(operation=binding["operation"],alias=binding["operation_alias"],
        source_commit=spec["source_commit"],prompt_sha256=spec["prompt_sha256"],spec_sha256=spec["spec_sha256"],
        hermes_commit=spec["hermes_commit"],profile=spec["runtime_profile_sha256"],checked_at_ns=time.time_ns(),
        endpoints=spec.get("receipt_endpoints",[]))
    for k in ("storage_checked","registration_binding_checked","destination_host_preserved","source_retired","scopes_checked"):
        receipt[k] = report.get(k) is True
    receipt["generation"] = report.get("generation")
    if MODE == "real":
        receipt["evidence_class"] = "OWNER_AUTHORIZED_CONTROL_PLANE"
        status = evaluation.get("status")
        receipt["evaluation_status"] = status if status in {"NOT_EVALUATED","PLAN_USAGE_ELIGIBLE","PLAN_USAGE_UNVERIFIED"} else "PLAN_USAGE_UNVERIFIED"
        reason = evaluation.get("reason_code")
        receipt["evaluation_reason"] = reason if reason is None or reason in _SIWC_EVALUATION_REASONS else "PLAN_USAGE_UNVERIFIED"
        accepted = report.get("status") == "DONE" and (PHASE != "preflight" or status == "PLAN_USAGE_ELIGIBLE")
        receipt["status"] = "DONE" if accepted else "BLOCKED"
        receipt["reason_code"] = None if accepted else "PLAN_USAGE_UNVERIFIED"
    target = siwc_path(spec["receipt_file"],windows=sys.platform == "win32")
    output_slot.publish(target.name,siwc_receipt_bytes(receipt))
    report["receipt"] = receipt

def phase_prepare_host(report):
    siwc_prepare_host(slot)
    report.update(storage_checked=True,destination_host_preserved=True,generation=0)

def phase_import(report):
    path = siwc_path(spec["transfer_file"],windows=False)
    if (siwc_overlap(path.parent,siwc_path(CRED)) or siwc_path(binding["approved_storage_root"]) not in path.parents):
        raise SIWCBlocked("STORAGE_UNSAFE")
    raw = siwc_read_private_file(str(path),spec["excluded_roots"],262144)
    siwc_import_transfer(slot,raw,binding,source_profile=spec["windows_profile_sha256"],issuer=C["issuer"],
                         resource=C["resource"],scopes=C["scopes"])
    report.update(storage_checked=True,registration_binding_checked=True,destination_host_preserved=True,
                  scopes_checked=True,generation=0)

def phase_export(report):
    if not siwc_generation(slot): raise SIWCBlocked("TRANSFER_INVALID")
    target = siwc_path(spec["transfer_file"],windows=True)
    receipt = siwc_path(spec["receipt_file"],windows=True)
    if target.parent != receipt.parent or target.name == receipt.name:
        raise SIWCBlocked("STORAGE_UNSAFE")
    if output_slot.read(target.name) is not None: raise SIWCBlocked("TARGET_EXISTS")
    host = read("host_id.json")["ext_agent_host_id"]
    bundle = dict(schema_id="siwc-selected-transfer",schema_version="1.0.0",registration=read("registration.json"),
        credential=load_credential(),source_host_id=host,source_validation=dict(source_commit=spec["source_commit"],
        runtime_profile_sha256=spec["runtime_profile_sha256"],validated_login_identity=True))
    raw = siwc_bytes(bundle)
    siwc_transfer(raw,binding,destination_host_id=binding["destination_host_id"],
                  source_profile=spec["runtime_profile_sha256"],issuer=C["issuer"],resource=C["resource"],scopes=C["scopes"])
    state = dict(schema_id="siwc-source-export-state",schema_version="1.0.0",operation_alias=binding["operation_alias"],
        selected_generation=siwc_generation(slot),registration_binding=sha(siwc_bytes(bundle["registration"])),
        source_host_binding=sha(host.encode()),destination_host_binding=sha(binding["destination_host_id"].encode()),
        export_digest=sha(raw),target_binding=output_slot.target_binding(target.name))
    permit = siwc_retire_source(slot,state)
    siwc_publish_retired_export(slot,output_slot,target.name,raw,state,permit=permit)
    report.update(storage_checked=True,registration_binding_checked=True,source_retired=True,
                  destination_host_preserved=True,scopes_checked=True,generation=state["selected_generation"])
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
    raw = slot.read(name,4096 if name == "host_id.json" else 16384 if name == "registration.json" else 262144)
    return siwc_json(raw,262144) if raw is not None else None
def write(name, value):
    raw = siwc_bytes(value)
    existing = slot.read(name)
    if name == "credential.json" and existing is not None:
        slot.replace_credential(raw)
    elif existing is None:
        slot.publish(name,raw,4096 if name == "host_id.json" else 16384 if name == "registration.json" else 262144)
    elif existing != raw:
        raise SIWCBlocked("OPERATOR_BINDING_INVALID")
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
        if form.get("grant_type") == "authorization_code":
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
    if PHASE == "preflight": preflight_budget.complete(response.status_code)
def client(timeout, request_hooks=()):
    hooks = list(request_hooks)
    if PHASE == "preflight":
        def check_control(request):
            if preflight_budget is None: raise SIWCBlocked("PREFLIGHT_REFUSED")
            preflight_budget.admit(request.method,str(request.url))
        hooks.insert(0,check_control)
    kwargs = dict(timeout=httpx.Timeout(timeout), trust_env=False, follow_redirects=False,
                  event_hooks={"request": hooks, "response": [on_response]})
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
    if not all(siwc_text(record.get(k),65536) for k in ("access_token","refresh_token","id_token")):
        raise Blocked("TOKEN_RESPONSE_INVALID")
    validate_issued_access(record)
    write("credential.json", record)
def token_fields_ok(tok):
    return (type(tok) is dict and siwc_text(tok.get("access_token"),65536) and type(tok.get("expires_in")) is int
            and tok["expires_in"] > 0
            and siwc_text(tok.get("scope"),16384)
            and ("refresh_token" not in tok or siwc_text(tok["refresh_token"],65536))
            and str(tok.get("token_type", "")).lower() == "bearer")
def verify_id_token(token, http, audience, nonce):
    try:
        if type(token) is not str or len(token.encode("utf-8")) > 65_536:
            raise ValueError()
        kid = jwt.get_unverified_header(token).get("kid")
        if type(kid) is not str or not kid:
            raise ValueError()
        # Bound the bytes as they arrive, before parsing JSON or constructing any key.
        chunks, size = [], 0
        with http.stream("GET", C["jwks_url"]) as response:
            if response.status_code != 200:
                raise ValueError()
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > 1_048_576:
                    raise ValueError()
                chunks.append(chunk)
        document = json.loads(b"".join(chunks))
        keys = document.get("keys") if type(document) is dict else None
        if type(keys) is not list or len(keys) > 100 or any(type(k) is not dict for k in keys):
            raise ValueError()
        keys = [k for k in keys if k.get("kid") == kid]
        if len(keys) != 1 or keys[0].get("kty") != "RSA":
            raise ValueError()
        key = keys[0]
        if ("alg" in key and key["alg"] != "RS256") or ("use" in key and key["use"] != "sig"):
            raise ValueError()
        claims = jwt.decode(token, key=jwt.PyJWK(keys[0]).key, algorithms=["RS256"], audience=audience,
                            issuer=C["issuer"], leeway=60, options={"require": ["exp", "iat", "iss", "aud", "sub"]})
        if claims.get("nonce") != nonce:
            raise ValueError()
        return claims
    except Exception:
        raise Blocked("ID_TOKEN_INVALID") from None
def phase_login(report):
    pending = siwc_begin_mutation(slot,"source-login",binding["operation_alias"])
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
    else:
        params["id_token_hint"] = load_credential()["id_token"]
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
    if not siwc_text(issued):
        raise Blocked("REGISTRATION_INCOMPLETE")
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
        claims = verify_id_token(tok["id_token"], http, issued, nonce)
    if registration.get("subject") not in (None, claims["sub"]):
        raise Blocked("ACCOUNT_MISMATCH")
    scopes = set(str(tok.get("scope", "")).split())
    if (not set(C["scopes"]) <= scopes or not siwc_text(claims.get("sub")) or
            issued == "dynamic_agent_client" or claims["sub"] == "NEW_REGISTRATION_UNBOUND"):
        raise Blocked("TOKEN_RESPONSE_INVALID")
    write("registration.json", dict(client_id=issued, subject=claims["sub"]))
    record = dict(issuer=C["issuer"], subject=claims["sub"], client_id=issued, id_token=tok["id_token"],
                  ext_agent_host_id=host["ext_agent_host_id"])
    save_tokens(record, tok, scopes)
    siwc_complete_mutation(slot,pending)
    report.update(scopes_granted=sorted(scopes & set(C["scopes"])), id_token_valid=True,
                  client_id_sha256=sha(issued.encode("utf-8")))
def load_credential():
    record = read("credential.json")
    if (type(record) is not dict or set(record) != {"issuer","subject","client_id","id_token","ext_agent_host_id",
            "access_token","refresh_token","token_type","expires_at","scopes","saved_at"}
            or not all(siwc_text(record.get(k),65536) for k in ("access_token","refresh_token","id_token"))
            or type(record["expires_at"]) is not int or type(record["saved_at"]) is not int
            or type(record["scopes"]) is not list or any(type(s) is not str for s in record["scopes"])
            or len(record["scopes"]) != len(set(record["scopes"]))):
        raise Blocked("CREDENTIAL_MISSING")
    return record

def validate_issued_access(record):
    payload = siwc_jwt_payload(record["access_token"])
    if (payload.get("iss") != C["issuer"] or payload.get("aud") != C["resource"]
            or payload.get("client_id") != record["client_id"]
            or payload.get("sub",record["subject"]) != record["subject"]
            or type(payload.get("scope")) is not str
            or set(payload["scope"].split()) != set(record["scopes"])
            or not set(C["scopes"]) <= set(record["scopes"])):
        raise Blocked("ACCESS_TOKEN_BINDING_INVALID")
    if "exp" in payload and (type(payload["exp"]) is not int or
            (payload["exp"] <= time.time() and record["expires_at"] > time.time())):
        raise Blocked("ACCESS_TOKEN_BINDING_INVALID")
def access_facts(report, record):
    claims = jwt_payload(record["access_token"])
    report.update(token_seconds_remaining=int(record["expires_at"] - time.time()),
                  scopes_granted=sorted(set(str(claims.get("scope", "")).split()) & set(C["scopes"])),
                  access_audience_ok=claims.get("aud") == C["resource"], access_issuer_ok=claims.get("iss") == C["issuer"],
                  client_match=claims.get("client_id") == record.get("client_id"),
                  client_id_sha256=sha(str(record.get("client_id")).encode("utf-8")))
def phase_preflight(report):
    global preflight_budget
    record = load_credential()
    # A consumed owner alias cannot replay an authenticated phase, even if its
    # receipt is lost or another caller enters between preflight and publication.
    slot.barrier("preflight-used-"+binding["operation_alias"]+".json",siwc_bytes(dict(
        schema_id="siwc-preflight-consumed",operation_alias=binding["operation_alias"])),16384)
    preflight_budget = SIWCPreflightBudget(refresh_required=record["expires_at"] - time.time() < spec["refresh_margin_s"],
                                          refresh_allowed=binding["refresh_allowed"])
    report["refreshed"] = False
    if record["expires_at"] - time.time() < spec["refresh_margin_s"]:
        if not binding["refresh_allowed"]:
            raise Blocked("REFRESH_FAILED")
        pending = siwc_begin_mutation(slot,"preflight-only",binding["operation_alias"])
        allowed_hosts.add(C["auth_host"])
        with client(30) as http:
            response = http.post(C["token_url"], data=dict(grant_type="refresh_token", client_id=record["client_id"],
                                 refresh_token=record.get("refresh_token"), resource=C["resource"]))
        if response.status_code != 200 or not token_fields_ok(response.json()):
            report["refresh_status"] = response.status_code
            raise Blocked("REFRESH_FAILED")
        tok = response.json()
        payload = siwc_jwt_payload(tok.get("access_token"))
        scopes = set(str(tok.get("scope", "")).split())
        if (("id_token" in tok and tok["id_token"] != record["id_token"]) or payload.get("iss") != C["issuer"] or payload.get("aud") != C["resource"]
                or payload.get("client_id") != record["client_id"]
                or payload.get("sub",record["subject"]) != record["subject"]
                or not set(C["scopes"]) <= scopes or set(str(payload.get("scope", "")).split()) != scopes
                or ("refresh_token" in tok and not siwc_text(tok["refresh_token"],65536))):
            raise Blocked("TOKEN_RESPONSE_INVALID")
        save_tokens(record, tok, set(str(tok.get("scope", "")).split()))
        siwc_complete_mutation(slot,pending)
        report["refreshed"] = True
        report["generation"] = siwc_generation(slot)
    access_facts(report, record)
    if (not report["access_audience_ok"] or not report["access_issuer_ok"] or not report["client_match"]
            or not set(C["scopes"]) <= set(report["scopes_granted"]) or report["token_seconds_remaining"] < spec["min_token_seconds"]):
        raise Blocked("ACCESS_TOKEN_BINDING_INVALID")
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
    admit_slot()
    if PHASE in {"prepare-vm-host","import-selected","source-export"} or spec.get("receipt_file"):
        admit_output()
        receipt_permitted = PHASE in {"prepare-vm-host","import-selected","source-export"} or spec.get("receipt_only") is True
    if not spec.get("receipt_only"):
        {"login": phase_login, "preflight": phase_preflight, "dispatch": phase_dispatch,
         "prepare-vm-host":phase_prepare_host,"import-selected":phase_import,"source-export":phase_export}[PHASE](report)
    if PHASE in {"prepare-vm-host","import-selected","source-export"} or spec.get("receipt_only"):
        if spec.get("receipt_only"):
            report.update(spec.get("receipt_flags") or {})
        publish_control_receipt(report)
except SIWCBlocked as stop:
    report.update(status="BLOCKED", reason_code=str(stop))
except Blocked as stop:
    report.update(status="BLOCKED", reason_code=str(stop))
except Exception as exc:
    report.update(status="BLOCKED", reason_code="CHILD_EXCEPTION", error_class=report.get("error_class") or type(exc).__name__[:64])
finally:
    if receipt_permitted and not receipt_attempted:
        try: publish_control_receipt(report)
        except Exception:
            report.update(status="BLOCKED",reason_code="EXPORT_PUBLICATION_AMBIGUOUS",error_class=None)
    if output_slot is not None: output_slot.close()
    if slot is not None: slot.close()
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
    runtime_profile_sha256: str
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
                             stage.hermes_commit, stage.tool_surface_fingerprint, stage.runtime_profile_sha256, model_input=model_input)
    return replace(draft, request_id=REQUEST_ID_PREFIX + stage_b._digest(_preimage(draft)))


def request_is_bound(request: object) -> bool:
    return (type(request) is OAuthPlanRequest and
            (request.provider, request.api_mode, request.base_url, request.model) == tuple(ROUTE.values()) and
            request.hermes_commit == stage_b.PINNED_HERMES_COMMIT and
            stage_b.profile_digest_is_approved(request.runtime_profile_sha256) and type(request.model_input) is bytes and
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
                 python_executable: object = None, login_wait_s: int = 300, operator_record_path: object = None) -> None:
        if any(p in {".",".."} for p in str(credential_dir).replace("\\","/").split("/")):
            raise ValueError("CREDENTIAL_DIR_NOT_ABSOLUTE")
        credentials = Path(credential_dir)
        if not credentials.is_absolute():
            raise ValueError("CREDENTIAL_DIR_NOT_ABSOLUTE")
        if ".." in credentials.parts or "." in credentials.parts:
            raise ValueError("CREDENTIAL_DIR_NOT_ABSOLUTE")
        resolved = credentials.absolute()
        if resolved == _REPO_ROOT or _REPO_ROOT in resolved.parents:
            raise ValueError("CREDENTIAL_DIR_INSIDE_REPOSITORY")
        if mode not in ("real", "mock") or (mode == "real") != (mock is None):
            raise ValueError("TRANSPORT_MODE_INVALID")
        self.mode, self._pin_root, self._credentials = mode, Path(pin_root).absolute(), resolved
        self._mock, self._python, self._login_wait_s = json.loads(json.dumps(mock or {})), python_executable, login_wait_s
        self._operator_record_path = str(operator_record_path) if operator_record_path is not None else None
        self._receipt_path = None
        self._dispatch_admitted = False
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
        profile = stage_b.verify_runtime_profile(root, python_executable=exe)
        if "runtime_profile_sha256" in extra and extra["runtime_profile_sha256"] != profile:
            raise ValueError("PROFILE_MISMATCH")
        spec = dict(phase=phase, mode=self.mode, mock=self._mock, credential_dir=str(self._credentials),
                    operator_record_path=self._operator_record_path,
                    source_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=_REPO_ROOT,
                                                         stderr=subprocess.DEVNULL,text=True).strip(),
                    hermes_commit=head,
                    windows_profile_sha256=next(e["profile_id"].rsplit(":",1)[1] for e in stage_b._profile_entries()
                                               if e["preimage"]["platform"] == "win32"),
                    prompt_sha256=_sha((_REPO_ROOT/"docs/wp_specs/S10-HERMES-SIWC-VM-01/wp_prompt.txt").read_bytes()),
                    spec_sha256=_sha((_REPO_ROOT/"docs/wp_specs/S10-HERMES-SIWC-VM-01/wp_spec.json").read_bytes()),
                    excluded_roots=[str(_REPO_ROOT),str(root)],
                    dispatch_admission=self._dispatch_admitted is _OBSERVED,
                    model=ROUTE["model"], route=ROUTE, login_wait_s=self._login_wait_s,
                    refresh_margin_s=REFRESH_MARGIN_S, min_token_seconds=MIN_TOKEN_SECONDS,
                    constants=dict(api_host=API_HOST, auth_host=AUTH_HOST, issuer=ISSUER, authorize_url=AUTHORIZE_URL,
                                   token_url=TOKEN_URL, jwks_url=JWKS_URL, resource=RESOURCE, scopes=sorted(REQUIRED_SCOPES),
                                   agent_name_hint=AGENT_NAME_HINT, models_path=MODELS_PATH, responses_path=RESPONSES_PATH,
                                   body_required=sorted(BODY_REQUIRED), body_allowed=sorted(BODY_ALLOWED),
                                   unsupported=sorted(UNSUPPORTED_FIELDS)), **extra)
        spec["runtime_profile_sha256"] = profile
        # Windows may briefly keep the sterile home locked after the child exits; cleanup is
        # best-effort and never turns an already-finished phase into a transport failure.
        with tempfile.TemporaryDirectory(prefix="oauthplan-hermes-home-", ignore_cleanup_errors=True) as home:
            # Sterile route config: a known context window skips the authenticated /models init probe.
            Path(home, "config.yaml").write_text(
                "model:\n  provider: {provider}\n  default: {model}\n  base_url: {base_url}\n".format(**ROUTE)
                + f"  context_length: {real01.ROUTE_CONTEXT_LENGTH}\nsecurity:\n  allow_lazy_installs: false\n", encoding="utf-8")
            env = {key: home for key in ("HERMES_HOME", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP")}
            env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", PATH=str(exe.parent), NO_COLOR="1", HERMES_DISABLE_LAZY_INSTALLS="1")
            if "SYSTEMROOT" in os.environ:
                env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
            # The expanded native program exceeds Windows' command-line limit.
            # Carry immutable program/spec bytes on stdin; argv remains a fixed loader.
            program = (stage_b._OFFLINE_PROCESS_GUARD if self.mode == "mock" else "") + _SIWC_SOURCE + _CHILD_SOURCE
            loader = ("import io,json,sys; p=json.loads(sys.stdin.buffer.read()); "
                      "sys.stdin=io.TextIOWrapper(io.BytesIO(json.dumps(p['spec']).encode('utf-8'))); "
                      "exec(compile(p['source'],'oauth-plan-native-child','exec'))")
            completed = subprocess.run([str(exe), "-I", "-B", "-c",loader], cwd=root, env=env,
                                       input=json.dumps(dict(source=program,spec=spec)).encode("utf-8"), capture_output=True,
                                       timeout=timeout_s, check=False)
        if stage_b.verify_runtime_profile(root, python_executable=exe) != profile:
            raise ValueError("PROFILE_MISMATCH")
        lines = completed.stdout.decode("utf-8", "replace").strip().splitlines()
        report = json.loads(lines[-1]) if completed.returncode == 0 and lines else {}
        if type(report) is dict and report:
            report["hermes_commit"] = head
            report["runtime_profile_sha256"] = profile
        return report

    def login(self) -> dict:
        """Attended: opens the user's browser; the user performs consent. Control plane only."""
        self.control_phases.append("login")
        return self._run_child("login", {}, self._login_wait_s + 120)

    def preflight(self) -> dict:
        self.control_phases.append("preflight")
        extra = dict(receipt_file=self._receipt_file()) if self._receipt_path is not None else {}
        return self._run_child("preflight", extra, 120)

    def _receipt_file(self) -> str | None:
        return self._receipt_path or (self._operator_record_path + ".receipt.json" if self._operator_record_path else None)

    def prepare_vm_host(self) -> dict:
        self.control_phases.append("prepare-vm-host")
        return self._run_child("prepare-vm-host",dict(receipt_file=self._receipt_file()),120)

    def import_selected_session(self, *, transfer_file: object) -> dict:
        self.control_phases.append("import-selected")
        return self._run_child("import-selected",dict(transfer_file=str(transfer_file),receipt_file=self._receipt_file()),120)

    def export_selected_session(self, *, transfer_file: object) -> dict:
        self.control_phases.append("source-export")
        return self._run_child("source-export",dict(transfer_file=str(transfer_file),receipt_file=str(transfer_file)+".receipt.json"),120)

    def _preflight_receipt(self, report: dict, evaluation: PlanEligibility) -> dict:
        safe_calls = report.get("http_calls",[])
        endpoints = [dict(zip(("method","host","path","status"),c)) for c in safe_calls
                     if type(c) is list and len(c) == 4 and (c[0],c[1],c[2]) in {
                         ("POST",AUTH_HOST,"/api/accounts/oauth/token"),("GET",API_HOST,MODELS_PATH)}]
        return self._run_child("preflight",dict(receipt_only=True,receipt_file=self._receipt_file(),
            evaluation=dict(status=evaluation.status,reason_code=evaluation.reason_code),receipt_endpoints=endpoints,
            receipt_flags={k:report.get(k) for k in ("status","storage_checked","registration_binding_checked",
                "destination_host_preserved","source_retired","generation","scopes_checked")}),120)

    def _send(self, request: OAuthPlanRequest) -> dict:
        if self._dispatch_admitted is not _OBSERVED:
            raise ValueError("DISPATCH_AUTHORITY_REQUIRED")
        self.dispatch_count += 1
        return self._run_child("dispatch", dict(instructions=INSTRUCTIONS, runtime_profile_sha256=request.runtime_profile_sha256, model_input=request.model_input.decode("utf-8"),
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
    if not stage_b.profile_digest_is_approved(report.get("runtime_profile_sha256")):
        return verdict("PROFILE_MISMATCH", facts, mode)
    facts["runtime_profile_sha256"] = report["runtime_profile_sha256"]
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
            stage_b.profile_digest_is_approved(eligibility.facts.get("runtime_profile_sha256")) and
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
    if not stage_b.profile_digest_is_approved(report.get("runtime_profile_sha256")) or report.get("runtime_profile_sha256") != request.runtime_profile_sha256:
        return verdict("PROFILE_MISMATCH")
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
        tool_surface_fingerprint=request.tool_surface_fingerprint, runtime_profile_sha256=request.runtime_profile_sha256, provider_route="CHATGPT_PLAN_OAUTH",
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
    if not stage_b.profile_digest_is_approved(record.get("runtime_profile_sha256")):
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


def _publish_terminal(terminal: Path, body: bytes) -> None:
    """Publish the immutable terminal complete or not at all (S10-HERMES-OAUTH-JOURNAL-01).

    The bytes are written and fsynced to a private same-directory temporary file, then
    hard-linked into place: the link is atomic and never overwrites, so a reader sees no
    terminal or the whole one. A crash before the link leaves only the reservation, which
    blocks any further dispatch.
    """
    import os
    import tempfile
    fd, tmp = tempfile.mkstemp(prefix=".oauthplan-attempt.", suffix=".tmp", dir=terminal.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(tmp, terminal)  # FileExistsError keeps an existing terminal immutable
    finally:
        os.unlink(tmp)


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
            if not verify_origin_record(record) or record.get("runtime_profile_sha256") != request.runtime_profile_sha256:
                raise ValueError
        except Exception:
            return OAuthPlanResult(request_id, "JOURNAL_INVALID", None)
        if record["request_id"] != request_id:
            return OAuthPlanResult(request_id, "JOURNAL_ALREADY_CONSUMED", None)
        return OAuthPlanResult(request_id, record["status"], record, None, True)  # zero redispatch
    if marker.exists():
        return OAuthPlanResult(request_id, "ATTEMPT_ALREADY_RESERVED", None)
    real = transport.mode == "real"
    if real and (not eligibility_is_witnessed(eligibility) or
                 eligibility.facts.get("runtime_profile_sha256") != request.runtime_profile_sha256):
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
        transport._dispatch_admitted = _OBSERVED
        report = transport._send(request)
        finished = clock()
        status, facts, raw = classify_dispatch_report(request, report, dispatched_at_ns=dispatched, finished_at_ns=finished)
    except subprocess.TimeoutExpired:
        status, facts, finished = "ATTEMPT_TIMEOUT_CONSUMED", dict(mode=transport.mode, generation_requests=1), clock()
    except Exception:
        status, facts, finished = "ATTEMPT_TRANSPORT_FAILED_CONSUMED", dict(mode=transport.mode, generation_requests=1), clock()
    finally:
        transport._dispatch_admitted = False
    record = _origin_record(request, status, facts, raw, eligibility, dispatched, finished)
    _publish_terminal(terminal, stage_b._canonical(record))
    witnessed = real and status == VALID_OUTPUT and record["real_origin"] == REAL_ORIGIN_VERIFIED
    return OAuthPlanResult(request_id, status, record, raw if status == VALID_OUTPUT else None, False,
                           _OBSERVED if witnessed else None)


def main(argv: list[str] | None = None) -> int:
    """Only the three non-dispatch operator commands; all private I/O stays child-local."""
    import sys
    import time
    helpers: dict = {}
    exec(compile(_SIWC_SOURCE,"siwc-parse-only","exec"),helpers)
    try:
        parsed = helpers["siwc_parse_cli"](list(sys.argv[1:]) if argv is None else argv)
    except Exception:
        print('{"status":"BLOCKED","reason_code":"USAGE_INVALID"}')
        return 2
    if parsed is None:
        print("SIWC non-dispatch: prepare-vm-host | import-selected | preflight-only")
        return 0
    try:
        transport = OAuthPlanTransport(parsed["--pin-root"],parsed["--credential-dir"],
                                       operator_record_path=parsed["--operator-record"])
        transport._receipt_path = parsed["--receipt"]
        operation = parsed["operation"]
        if operation == "prepare-vm-host":
            report = transport.prepare_vm_host()
        elif operation == "import-selected":
            report = transport.import_selected_session(transfer_file=parsed["--transfer-file"])
        else:
            initial = transport.preflight()
            evaluated = evaluate_preflight(initial,attestation=dict(_ATTESTATION) if
                initial.get("operator_attestation_checked") is True else None,checked_at_ns=time.time_ns())
            report = transport._preflight_receipt(initial,evaluated)
        receipt = report.get("receipt")
        if type(receipt) is not dict:
            raise ValueError()
        helpers["siwc_receipt_bytes"](receipt)
        print(json.dumps(receipt,sort_keys=True))
        return 0 if receipt["status"] == "DONE" else 1
    except Exception:
        print('{"status":"BLOCKED","reason_code":"RECORD_INVALID"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
