"""Manual foreground operator for S10-QUAL-DATA-01 (weather qualification-data readiness).

Frozen package: ``docs/wp_specs/S10-QUAL-DATA-01/`` and
``docs/qualification_weather_data_readiness_contract.md``.

This is the ONLY network owner of S10-QUAL-DATA-01. The offline ``src/`` modules
(``pendulumflow_v3``, ``nws_ndfd_history``, ``qualification_data_readiness``) make zero network
calls. The operator writes only beneath ``local_data/s10_qual_data_01/run-01/`` (ignored).

Exact command grammar (always run from the repository root):

  prepare          zero network: repo/predecessor gate, genuine PR #200 Alpha registry discovery
                   + verification + copy, AF1 receipt verification, frozen plan + plan hash
  probe-sources    bounded source drift smoke (v3 manifest/range, Gamma-by-id identity, NWS
                   station, one official NDFD object decoded through the production adapter)
  run-readiness    ONE bounded real corpus run from the frozen plan
  verify-final     zero network: re-hash every retained artifact and replay the deterministic
                   derivation from retained artifacts only; bundle identities must match

Network: https GET / HEAD / Range GET only to archive.pendulumflow.com,
noaa-ndfd-pds.s3.amazonaws.com, gamma-api.polymarket.com (through the existing verified
``PolymarketPublicClient.get_market`` only) and api.weather.gov; no redirect, no credential, no
arbitrary URL, no background loop, no sleep/backoff, at most one immediate retry for transport
timeout/reset, HTTP 408/429 or 5xx. Every attempt and byte is counted against the frozen budget.
Console output is closed codes, ids and digests only.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research import nws_ndfd_history as ndfd  # noqa: E402
from src.data_layer.analytical_research import pendulumflow_v3 as v3  # noqa: E402
from src.data_layer.analytical_research import qualification_data_readiness as qd  # noqa: E402
from src.data_layer.analytical_research.alpha_factory_gate import (  # noqa: E402
    AF1_DIMENSIONS,
    AF1GateReceipt,
    af1_record_from_mapping,
    validate_af1_record,
)
from src.data_layer.analytical_research.alpha_factory_registry import (  # noqa: E402
    load_and_verify_alpha_factory_registry,
)
from src.data_layer.analytical_research.external_dataset import (  # noqa: E402
    ExternalSourceObject,
    build_external_dataset_descriptor,
)
from src.data_layer.polymarket.errors import PolymarketHTTPError, PolymarketReadOnlyError  # noqa: E402
from src.data_layer.polymarket.public_client import PolymarketPublicClient  # noqa: E402

# ── Frozen package identity ───────────────────────────────────────────────────

WP_ID = "S10-QUAL-DATA-01"
BASE_SHA = "77738717fee422fe83d8bb2b7765c36dfbe6b283"
PREDECESSOR_PR = 201
PREDECESSOR_HEAD = "cd70800d40f60f4ec20f5b17e107cc56643562a2"
PINNED_BRANCH = "codex/s10-qual-data-01-weather-readiness"
AF1_EVIDENCE_PATH = "docs/gate_evidence/S10-GATE-AF1/af1_gate_evidence.json"
ALPHA_REGISTRY_RELATIVE = ("local_data", "s10_alpha_real_01", "attempt-01", "alpha_registry.sqlite3")
CODE_FILES = (
    "src/data_layer/analytical_research/pendulumflow_v3.py",
    "src/data_layer/analytical_research/nws_ndfd_history.py",
    "src/data_layer/analytical_research/qualification_data_readiness.py",
    "tools/qualification/run_s10_qual_data_01.py",
)

WORKSPACE_PARTS = ("local_data", "s10_qual_data_01", "run-01")
PLAN_FILENAME = "PLAN.json"
PLAN_HASH_FILENAME = "PLAN.sha256"
REGISTRY_COPY_FILENAME = "alpha_registry.sqlite3"
STATE_FILENAME = "STATE.json"
INDEX_FILENAME = "ARTIFACT_INDEX.json"
LEDGER_FILENAME = "NETWORK_LEDGER.json"
PROBE_FILENAME = "PROBE_RESULT.json"
BUNDLE_FILENAME = "READINESS_BUNDLE.json"
REPORT_FILENAME = "RUN_REPORT.json"
VERIFY_FILENAME = "VERIFY_FINAL.json"
MANIFESTS_FILENAME = "PROVENANCE_MANIFESTS.json"

# ── Network allowlist and frozen budgets ──────────────────────────────────────

PENDULUMFLOW_HOST = "archive.pendulumflow.com"
NDFD_HOST = ndfd.BUCKET_HOST
GAMMA_HOST = "gamma-api.polymarket.com"
NWS_HOST = "api.weather.gov"
ALLOWED_HOSTS = frozenset({PENDULUMFLOW_HOST, NDFD_HOST, GAMMA_HOST, NWS_HOST})
ALLOWED_METHODS = frozenset({"GET", "HEAD"})
USER_AGENT = "polymarket-strategy-lab/S10-QUAL-DATA-01 (public read-only research; toobigtofailbot-maker)"
TIMEOUT_SECONDS = 60
RETRYABLE_STATUSES = frozenset({408, 429}) | frozenset(range(500, 600))

MAX_TARGET_DATES = 40
MAX_CANDIDATES = 1024
MAX_STATIONS = 128
MAX_PENDULUM_HOURS = 2000
MAX_ATTEMPTS = 8192
MAX_TOTAL_BYTES = 2 * 1024 ** 3
MAX_SINGLE_RESPONSE = 256 * 1024 ** 2
MAX_RETRIES_PER_REQUEST = 1

_PATH_RULES = {
    PENDULUMFLOW_HOST: re.compile(r"^/(?:audit|v3/\d{4}-\d{2}-\d{2}/\d{2}/(?:manifest\.json|\d{4}-\d{2}-\d{2}T\d{2}\.parquet))$"),
    NDFD_HOST: re.compile(r"^/(?:wmo/pop12/\d{4}/\d{2}/\d{2}/YDUZ98_KWBN_\d{12})?$"),
    GAMMA_HOST: re.compile(r"^/markets/\d{1,20}$"),
    NWS_HOST: re.compile(r"^/stations/K[A-Z0-9]{3}$"),
}
_LISTING_PREFIX_RE = re.compile(r"^wmo/pop12/\d{4}/\d{2}/\d{2}/$")

DISCOVERY_HOURS_UTC = (11, 12)
LABEL_WINDOW = timedelta(minutes=30)
PROBE_HOUR = "2026-08-19/11"
PROBE_MARKET_HOUR = "2026-08-19/12"
PROBE_STEPS = (
    "v3_manifest_product_range_sha256",
    "gamma_by_id_identity",
    "rule_semantics",
    "nws_station_metadata",
    "v3_targeted_row_group_read",
    "ndfd_production_decode",
)

STOP_CODES = (
    "USAGE_ERROR",
    "STATE_DRIFT",
    "ALPHA_LINEAGE_EVIDENCE_MISSING",
    "ALPHA_LINEAGE_CONFLICT",
    "AF1_EVIDENCE_DRIFT",
    "PREPARE_WORKSPACE_CONFLICT",
    "PLAN_MISSING",
    "PLAN_INVALID",
    "CODE_DRIFT",
    "PROBE_REQUIRED",
    "SOURCE_CONTRACT_DRIFT",
    "DECODER_UNAVAILABLE",
    "RUN_ALREADY_FINALIZED",
    "RUN_NOT_FINAL",
    "VERIFY_FAILED",
)


class OperatorStop(Exception):
    def __init__(self, code: str) -> None:
        if code not in STOP_CODES:
            code = "USAGE_ERROR"
        super().__init__(code)
        self.code = code


class TransportRefused(Exception):
    """Refused before any transport attempt (allowlist/method/header/URL)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class TransportFailure(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class BudgetExhausted(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ReplayMissing(Exception):
    pass


# ── Canonical JSON / files ────────────────────────────────────────────────────


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(json.dumps(value, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8") + b"\n")
    os.replace(tmp, path)


def read_json(path: Path) -> object:
    return json.loads(path.read_bytes().decode("utf-8"))


# ── URL policy and bounded transport ──────────────────────────────────────────


def validate_request(method: str, url: str, headers: Mapping[str, str]) -> tuple[str, str]:
    if method not in ALLOWED_METHODS:
        raise TransportRefused("METHOD_NOT_ALLOWED")
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https":
        raise TransportRefused("URL_NOT_ALLOWED")
    if parts.username or parts.password or parts.port not in (None, 443) or parts.fragment:
        raise TransportRefused("URL_NOT_ALLOWED")
    host = (parts.hostname or "").lower()
    if host not in ALLOWED_HOSTS or parts.netloc.lower() not in (host, host + ":443"):
        raise TransportRefused("URL_NOT_ALLOWED")
    if not _PATH_RULES[host].fullmatch(parts.path):
        raise TransportRefused("URL_NOT_ALLOWED")
    if parts.query:
        query = urllib.parse.parse_qs(parts.query, keep_blank_values=True, strict_parsing=True)
        if host != NDFD_HOST or parts.path != "/" or set(query) != {"list-type", "prefix"}:
            raise TransportRefused("URL_NOT_ALLOWED")
        if query["list-type"] != ["2"] or len(query["prefix"]) != 1 or not _LISTING_PREFIX_RE.fullmatch(query["prefix"][0]):
            raise TransportRefused("URL_NOT_ALLOWED")
    elif host == NDFD_HOST and parts.path == "/":
        raise TransportRefused("URL_NOT_ALLOWED")
    for name in headers:
        if name.lower() not in ("user-agent", "accept", "range"):
            raise TransportRefused("HEADER_NOT_ALLOWED")
    if "range" in (n.lower() for n in headers):
        value = next(v for n, v in headers.items() if n.lower() == "range")
        if not re.fullmatch(r"bytes=\d+-\d+", value):
            raise TransportRefused("HEADER_NOT_ALLOWED")
    return host, parts.path


@dataclasses.dataclass
class Ledger:
    attempts: int = 0
    retries: int = 0
    bytes: int = 0
    max_single_response: int = 0
    attempts_by_host: dict = dataclasses.field(default_factory=dict)
    bytes_by_host: dict = dataclasses.field(default_factory=dict)
    statuses: dict = dataclasses.field(default_factory=dict)
    refusals: int = 0
    failures: dict = dataclasses.field(default_factory=dict)
    exhausted: str | None = None

    def to_mapping(self) -> dict[str, object]:
        return dataclasses.asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "Ledger":
        return cls(**{field.name: value[field.name] for field in dataclasses.fields(cls)})  # type: ignore[arg-type]

    def check_attempt(self, expected_bytes: int | None) -> None:
        if self.attempts + 1 > MAX_ATTEMPTS:
            self.exhausted = "ATTEMPT_BUDGET_EXHAUSTED"
            raise BudgetExhausted(self.exhausted)
        if expected_bytes is not None and self.bytes + expected_bytes > MAX_TOTAL_BYTES:
            self.exhausted = "BYTE_BUDGET_EXHAUSTED"
            raise BudgetExhausted(self.exhausted)

    def record(self, host: str, status: int | None, size: int) -> None:
        self.attempts += 1
        self.attempts_by_host[host] = self.attempts_by_host.get(host, 0) + 1
        self.bytes += size
        self.bytes_by_host[host] = self.bytes_by_host.get(host, 0) + size
        self.max_single_response = max(self.max_single_response, size)
        key = str(status) if status is not None else "TRANSPORT_ERROR"
        self.statuses[key] = self.statuses.get(key, 0) + 1


class _TransportError(Exception):
    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirect)


def urllib_fetch(method: str, url: str, headers: Mapping[str, str], timeout: float) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, method=method, headers=dict(headers))
    try:
        response = _NO_REDIRECT_OPENER.open(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        body = error.read(MAX_SINGLE_RESPONSE + 1) if error.fp is not None else b""
        return error.code, {k.lower(): v for k, v in (error.headers or {}).items()}, body
    except (socket.timeout, TimeoutError):
        raise _TransportError("TIMEOUT") from None
    except (ConnectionResetError, ConnectionAbortedError, http.client.HTTPException):
        # Includes http.client.RemoteDisconnected / IncompleteRead: a transport reset.
        raise _TransportError("RESET") from None
    except urllib.error.URLError as error:
        if isinstance(error.reason, (socket.timeout, TimeoutError)):
            raise _TransportError("TIMEOUT") from None
        if isinstance(error.reason, (ConnectionResetError, ConnectionAbortedError, http.client.HTTPException)):
            raise _TransportError("RESET") from None
        raise _TransportError("UNREACHABLE") from None
    except OSError:
        raise _TransportError("UNREACHABLE") from None
    with response:
        try:
            body = response.read(MAX_SINGLE_RESPONSE + 1)
        except (socket.timeout, TimeoutError):
            raise _TransportError("TIMEOUT") from None
        except (ConnectionResetError, ConnectionAbortedError, http.client.HTTPException, OSError):
            raise _TransportError("RESET") from None
        return response.status, {k.lower(): v for k, v in response.headers.items()}, body


def content_length(headers: Mapping[str, str]) -> int | None:
    """A trustworthy declared ``Content-Length`` (plain non-negative decimal), else ``None``.

    Absent, malformed or encoded (``Content-Encoding`` other than identity) lengths are not
    trusted; those bodies fall back to the bounded stream / byte-limit policy.
    """

    value = headers.get("content-length")
    encoding = (headers.get("content-encoding") or "identity").strip().lower()
    if value is None or encoding != "identity" or not re.fullmatch(r"\d{1,15}", value.strip()):
        return None
    return int(value.strip())


@dataclasses.dataclass(frozen=True)
class Response:
    status: int
    headers: dict
    body: bytes


class BoundedTransport:
    def __init__(self, ledger: Ledger, fetch: Callable[..., tuple[int, dict[str, str], bytes]] | None = None) -> None:
        self.ledger = ledger
        self._fetch = fetch or urllib_fetch

    def request(self, method: str, url: str, *, byte_range: tuple[int, int] | None = None,
                accept: str = "*/*", expected_bytes: int | None = None) -> Response:
        headers = {"User-Agent": USER_AGENT, "Accept": accept}
        if byte_range is not None:
            start, end = byte_range
            if not (0 <= start < end):
                raise TransportRefused("HEADER_NOT_ALLOWED")
            headers["Range"] = f"bytes={start}-{end - 1}"
            expected_bytes = end - start
        try:
            host, _path = validate_request(method, url, headers)
        except TransportRefused:
            self.ledger.refusals += 1
            raise
        if expected_bytes is not None and expected_bytes > MAX_SINGLE_RESPONSE:
            self.ledger.refusals += 1
            raise TransportRefused("SINGLE_RESPONSE_CAP")
        for attempt in range(1, MAX_RETRIES_PER_REQUEST + 2):
            self.ledger.check_attempt(expected_bytes)
            try:
                status, response_headers, body = self._fetch(method, url, headers, TIMEOUT_SECONDS)
            except _TransportError as error:
                self.ledger.record(host, None, 0)
                if attempt <= MAX_RETRIES_PER_REQUEST:
                    self.ledger.retries += 1
                    continue
                raise TransportFailure("TRANSPORT_" + error.kind) from None
            self.ledger.record(host, status, len(body))
            if self.ledger.bytes > MAX_TOTAL_BYTES:
                self.ledger.exhausted = "BYTE_BUDGET_EXHAUSTED"
                raise BudgetExhausted(self.ledger.exhausted)
            if len(body) > MAX_SINGLE_RESPONSE:
                raise TransportFailure("RESPONSE_TOO_LARGE")
            if 300 <= status < 400:
                raise TransportFailure("NETWORK_REDIRECT_REFUSED")
            if status in RETRYABLE_STATUSES:
                if attempt <= MAX_RETRIES_PER_REQUEST:
                    self.ledger.retries += 1
                    continue
                raise TransportFailure(f"HTTP_{status}")
            if byte_range is not None:
                if status == 206 and len(body) < byte_range[1] - byte_range[0]:
                    # A short 206 body is a transport truncation (connection dropped mid-body):
                    # the same single immediate retry as a timeout/reset, then a closed failure.
                    if attempt <= MAX_RETRIES_PER_REQUEST:
                        self.ledger.retries += 1
                        continue
                    raise TransportFailure("RANGE_TRUNCATED")
                if status != 206 or len(body) != byte_range[1] - byte_range[0]:
                    raise TransportFailure("RANGE_RESPONSE_INVALID")
                content_range = response_headers.get("content-range", "")
                if not content_range.startswith(f"bytes {byte_range[0]}-{byte_range[1] - 1}/"):
                    raise TransportFailure("RANGE_RESPONSE_INVALID")
            elif status != 200:
                raise TransportFailure(f"HTTP_{status}")
            else:
                declared = content_length(response_headers)
                if declared is not None and len(body) < declared:
                    # A short plain-200 body is a transport truncation (S10-QUAL-DATA-01-D009): one
                    # immediate retry, then a closed failure; a known-truncated body is never retained.
                    if attempt <= MAX_RETRIES_PER_REQUEST:
                        self.ledger.retries += 1
                        continue
                    raise TransportFailure("BODY_TRUNCATED")
                if declared is not None and len(body) > declared:
                    raise TransportFailure("BODY_LENGTH_MISMATCH")
            return Response(status, response_headers, body)
        raise TransportFailure("TRANSPORT_EXHAUSTED")  # pragma: no cover


# ── Content-addressed artifact store (resume + zero-network replay) ───────────


class ArtifactStore:
    """Immutable raw artifacts stored by SHA-256 plus a request-key index.

    In replay mode no transport exists: every request must already be retained (and its bytes
    re-hash to the indexed digest); a retained failure replays as the same failure.
    """

    def __init__(self, root: Path, transport: BoundedTransport | None,
                 gamma_client_factory: Callable[[], object] | None = None, *, replay: bool = False) -> None:
        self.root = root
        self.raw = root / "raw"
        self.index_path = root / INDEX_FILENAME
        self.transport = transport
        self.replay = replay
        self._gamma_factory = gamma_client_factory
        self._gamma_client = None
        self.index: dict[str, dict[str, object]] = (
            read_json(self.index_path) if self.index_path.exists() else {}  # type: ignore[assignment]
        )
        self.used: set[str] = set()

    @staticmethod
    def key(method: str, url: str, byte_range: tuple[int, int] | None = None) -> str:
        return f"{method} {url}" + (f" bytes={byte_range[0]}-{byte_range[1]}" if byte_range else "")

    def _read_verified(self, digest: str) -> bytes:
        data = (self.raw / digest).read_bytes()
        if sha256_hex(data) != digest:
            raise OperatorStop("VERIFY_FAILED")
        return data

    def _persist(self) -> None:
        write_json_atomic(self.index_path, self.index)

    def _store(self, key: str, data: bytes, meta: Mapping[str, object]) -> None:
        digest = sha256_hex(data)
        target = self.raw / digest
        if not target.exists():
            self.raw.mkdir(parents=True, exist_ok=True)
            tmp = target.with_name(digest + ".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, target)
        self.index[key] = {"sha256": digest, "bytes": len(data), **meta}
        self._persist()

    def entry(self, key: str) -> dict[str, object]:
        return self.index[key]

    def get(self, url: str, *, byte_range: tuple[int, int] | None = None, accept: str = "*/*",
            media_type: str = "application/octet-stream", expected_bytes: int | None = None) -> bytes:
        key = self.key("GET", url, byte_range)
        self.used.add(key)
        entry = self.index.get(key)
        if entry is not None:
            if "failed" in entry:
                raise TransportFailure(str(entry["failed"]))
            return self._read_verified(str(entry["sha256"]))
        if self.replay or self.transport is None:
            raise ReplayMissing(key)
        try:
            response = self.transport.request("GET", url, byte_range=byte_range, accept=accept,
                                              expected_bytes=expected_bytes)
        except TransportFailure as failure:
            self.index[key] = {"failed": failure.code}
            self._persist()
            raise
        self._store(key, response.body, {
            "media_type": media_type,
            "last_modified": response.headers.get("last-modified"),
            "status": response.status,
        })
        return response.body

    def gamma_market(self, market_id: str, ledger: Ledger | None) -> dict[str, object]:
        """Gamma-by-id through the existing verified public client only."""

        if not re.fullmatch(r"\d{1,20}", market_id):
            raise TransportRefused("URL_NOT_ALLOWED")
        url = f"https://{GAMMA_HOST}/markets/{market_id}"
        key = self.key("GET", url) + " via=PolymarketPublicClient.get_market"
        self.used.add(key)
        entry = self.index.get(key)
        if entry is not None:
            if "failed" in entry:
                raise TransportFailure(str(entry["failed"]))
            return json.loads(self._read_verified(str(entry["sha256"])).decode("utf-8"))
        if self.replay or self._gamma_factory is None or ledger is None:
            raise ReplayMissing(key)
        validate_request("GET", url, {"User-Agent": USER_AGENT})
        if self._gamma_client is None:
            self._gamma_client = self._gamma_factory()
        failure_code = "GAMMA_UNAVAILABLE"
        for attempt in range(1, MAX_RETRIES_PER_REQUEST + 2):
            ledger.check_attempt(None)
            try:
                result = self._gamma_client.get_market(market_id)  # type: ignore[union-attr]
            except PolymarketHTTPError as error:
                ledger.record(GAMMA_HOST, error.status, len(getattr(error, "body", "") or ""))
                failure_code = f"HTTP_{error.status}"
                if error.status in RETRYABLE_STATUSES and attempt <= MAX_RETRIES_PER_REQUEST:
                    ledger.retries += 1
                    continue
                break
            except (PolymarketReadOnlyError, ConnectionError, TimeoutError, http.client.HTTPException, OSError):
                # The existing public client wraps only urllib URLError; a raw connection reset
                # (e.g. http.client.RemoteDisconnected) is the same transport class here.
                ledger.record(GAMMA_HOST, None, 0)
                failure_code = "TRANSPORT_ERROR"
                if attempt <= MAX_RETRIES_PER_REQUEST:
                    ledger.retries += 1
                    continue
                break
            data = canonical(result.data)
            ledger.record(GAMMA_HOST, result.request_info.status_code, len(data))
            if ledger.bytes > MAX_TOTAL_BYTES:
                ledger.exhausted = "BYTE_BUDGET_EXHAUSTED"
                raise BudgetExhausted(ledger.exhausted)
            if not isinstance(result.data, dict):
                failure_code = "GAMMA_RESPONSE_INVALID"
                break
            self._store(key, data, {"media_type": "application/json;canonical", "last_modified": None,
                                    "status": result.request_info.status_code})
            return result.data
        self.index[key] = {"failed": failure_code}
        self._persist()
        raise TransportFailure(failure_code)


def default_gamma_client_factory() -> PolymarketPublicClient:
    # The client's urlopen uses the global opener; install one without redirect handling so a
    # redirect can never leave gamma-api.polymarket.com.
    urllib.request.install_opener(_NO_REDIRECT_OPENER)
    return PolymarketPublicClient(timeout_seconds=TIMEOUT_SECONDS, user_agent=USER_AGENT, allow_unverified_endpoints=False)


# ── PendulumFlow hour access ──────────────────────────────────────────────────


def pf_url(path: str) -> str:
    return f"https://{PENDULUMFLOW_HOST}/{path}"


class V3Hours:
    def __init__(self, store: ArtifactStore, audit: v3.V3AuditSnapshot | None) -> None:
        self.store = store
        self.audit = audit
        self.manifests: dict[str, v3.V3Manifest] = {}
        self.ranges: dict[str, list[tuple[int, bytes]]] = {}
        self.files: dict[str, object] = {}
        self.failed: dict[str, str] = {}
        self.invalid_rows = 0
        self.keys_by_hour: dict[str, set[str]] = {}

    def _track(self, hour: str, key: str) -> None:
        self.keys_by_hour.setdefault(hour, set()).add(key)

    def manifest(self, hour: str) -> v3.V3Manifest:
        if hour in self.manifests:
            return self.manifests[hour]
        if hour in self.failed:
            raise v3.PendulumFlowError("V3_MANIFEST_INVALID")
        url = pf_url(v3.manifest_object_path(hour))
        self._track(hour, ArtifactStore.key("GET", url))
        try:
            raw = self.store.get(url, accept="application/json", media_type="application/json")
            manifest = v3.validate_manifest(json.loads(raw.decode("utf-8")), hour)
        except TransportFailure as failure:
            self.failed[hour] = failure.code
            raise v3.PendulumFlowError("V3_MANIFEST_INVALID") from None
        except (ValueError, UnicodeDecodeError):
            self.failed[hour] = "V3_MANIFEST_INVALID"
            raise v3.PendulumFlowError("V3_MANIFEST_INVALID") from None
        self.manifests[hour] = manifest
        return manifest

    def _range(self, hour: str, start: int, end: int) -> bytes:
        url = pf_url(v3.parquet_object_path(hour))
        self._track(hour, ArtifactStore.key("GET", url, (start, end)))
        try:
            data = self.store.get(url, byte_range=(start, end))
        except TransportFailure:
            raise v3.PendulumFlowError("V3_RANGE_NOT_RETAINED") from None
        self.ranges.setdefault(hour, []).append((start, data))
        return data

    def parquet(self, hour: str):
        if hour in self.files:
            return self.files[hour]
        manifest = self.manifest(hour)
        tail = self._range(hour, manifest.file_bytes - 8, manifest.file_bytes)
        footer_start, _length = v3.parse_parquet_tail(tail, manifest.file_bytes)
        self._range(hour, *v3.footer_fetch_range(manifest.file_bytes, footer_start))
        parquet = self._reopen(hour)
        self.files[hour] = parquet
        return parquet

    def _reopen(self, hour: str):
        return v3.open_parquet(self.manifest(hour).file_bytes, self.ranges[hour])

    def coverage(self, hour: str, product: str) -> str:
        try:
            if self.audit is None:
                raise v3.PendulumFlowError("V3_COVERAGE_UNCLASSIFIED")
            return v3.classify_product_coverage(self.manifest(hour), product, self.audit)
        except v3.PendulumFlowError:
            return "UNCLASSIFIED"

    def full_product_events(self, hour: str, family: str) -> tuple[v3.V3Event, ...]:
        """Fetch one small product's complete byte range, verify its SHA-256, decode all rows."""

        manifest = self.manifest(hour)
        product = manifest.product(family)
        self.parquet(hour)
        data = self._range(hour, product.byte_start, product.byte_end)
        v3.verify_product_bytes(product, data)
        parquet = self._reopen(hour)
        events: list[v3.V3Event] = []
        for group in range(product.row_group_first, product.row_group_last + 1):
            events.extend(self._decode_group(parquet, hour, family, group, None))
        return tuple(events)

    def targeted_events(self, hour: str, family: str, condition_ids: Sequence[str]) -> tuple[v3.V3Event, ...]:
        """Only the row groups whose ``market`` statistics can hold a target, only the needed
        column chunks (never a whole-hour download)."""

        manifest = self.manifest(hour)
        product = manifest.product(family)
        parquet = self.parquet(hour)
        targets = [bytes.fromhex(cid[2:]) for cid in condition_ids]
        groups = v3.product_row_groups_for_markets(parquet, product, targets)
        for group in groups:
            for start, end in v3.column_chunk_ranges(parquet, product, group, v3.READ_COLUMNS[family]):
                if not any(s <= start and end <= s + len(d) for s, d in self.ranges.get(hour, [])):
                    self._range(hour, start, end)
        parquet = self._reopen(hour)
        events: list[v3.V3Event] = []
        for group in groups:
            events.extend(self._decode_group(parquet, hour, family, group, set(targets)))
        return tuple(events)

    def _decode_group(self, parquet, hour: str, family: str, group: int, targets: set[bytes] | None) -> list[v3.V3Event]:
        import pyarrow as pa  # noqa: PLC0415
        import pyarrow.compute as pc  # noqa: PLC0415

        try:
            table = parquet.read_row_group(group, columns=list(v3.READ_COLUMNS[family]))
        except v3.PendulumFlowError:
            raise
        except Exception:
            raise v3.PendulumFlowError("V3_ROW_INVALID") from None
        if targets is not None:
            table = table.filter(pc.is_in(table["market"], value_set=pa.array(sorted(targets), type=pa.binary())))
        events = []
        for row in table.to_pylist():
            try:
                events.append(v3.normalize_row(family, hour, group, row))
            except v3.PendulumFlowError:
                self.invalid_rows += 1
        return events


# ── NDFD access ───────────────────────────────────────────────────────────────


class NdfdAccess:
    def __init__(self, store: ArtifactStore, decode_fn: Callable[..., ndfd.DecodedPop12]) -> None:
        self.store = store
        self.decode_fn = decode_fn
        self.listings: dict[str, tuple[ndfd.NdfdObject, ...] | None] = {}
        self.objects: dict[str, bytes | None] = {}
        self.keys_by_day: dict[str, set[str]] = {}
        self.keys_by_object: dict[str, set[str]] = {}

    def listing(self, day: date) -> tuple[ndfd.NdfdObject, ...]:
        prefix = ndfd.day_prefix(day)
        if prefix not in self.listings:
            url = f"https://{NDFD_HOST}/?" + urllib.parse.urlencode({"list-type": "2", "prefix": prefix})
            self.keys_by_day.setdefault(day.isoformat(), set()).add(ArtifactStore.key("GET", url))
            try:
                raw = self.store.get(url, accept="application/xml", media_type="application/xml")
                self.listings[prefix] = ndfd.parse_s3_listing(raw, prefix)
            except (TransportFailure, ndfd.NdfdError):
                self.listings[prefix] = None
        listing = self.listings[prefix]
        if listing is None:
            raise ndfd.NdfdError("LISTING_INVALID")
        return listing

    def object_bytes(self, item: ndfd.NdfdObject) -> bytes:
        if item.key not in self.objects:
            url = f"https://{NDFD_HOST}/{item.key}"
            self.keys_by_object.setdefault(item.key, set()).add(ArtifactStore.key("GET", url))
            try:
                data = self.store.get(url, media_type="application/octet-stream", expected_bytes=item.byte_length)
                if len(data) != item.byte_length:
                    raise ndfd.NdfdError("TRUNCATED")
                self.objects[item.key] = data
            except (TransportFailure, ndfd.NdfdError):
                self.objects[item.key] = None
        data = self.objects[item.key]
        if data is None:
            raise ndfd.NdfdError("TRUNCATED")
        return data


# ── Lineage verification (prepare / verify-final) ─────────────────────────────


def verify_alpha_registry(path: Path) -> dict[str, object]:
    """Load with the merged registry API and require the exact PR #200 semantic snapshot."""

    result = load_and_verify_alpha_factory_registry(str(path))
    if not result.is_valid or result.snapshot is None:
        raise ValueError("REGISTRY_INVALID")
    snapshot = result.snapshot
    ids = {entry.record_kind: entry.record_id for entry in snapshot.entries if entry.record_kind != "RESEARCH_SOURCE_REFERENCE"}
    episodes = [entry.record for entry in snapshot.entries if entry.record_kind == "RESEARCH_EPISODE"]
    if (
        snapshot.total_rows != qd.ALPHA_REGISTRY_ROWS
        or snapshot.head_entry_hash != qd.ALPHA_REGISTRY_HEAD
        or ids.get("OPPORTUNITY_CANDIDATE") != qd.ALPHA_CANDIDATE_ID
        or ids.get("HYPOTHESIS_FAMILY") != qd.ALPHA_FAMILY_ID
        or ids.get("RESEARCH_EPISODE") != qd.ALPHA_EPISODE_ID
        or len(episodes) != 1
        or getattr(episodes[0], "result_state", None) != qd.ALPHA_RESULT_STATE
    ):
        raise ValueError("REGISTRY_SEMANTIC_MISMATCH")
    return {
        "total_rows": snapshot.total_rows,
        "head_entry_hash": snapshot.head_entry_hash,
        "candidate_id": qd.ALPHA_CANDIDATE_ID,
        "family_id": qd.ALPHA_FAMILY_ID,
        "episode_id": qd.ALPHA_EPISODE_ID,
        "result_state": qd.ALPHA_RESULT_STATE,
        "entry_hashes": [entry.entry_hash for entry in snapshot.entries],
    }


def discover_alpha_registry(worktree_roots: Sequence[Path]) -> tuple[Path, dict[str, object], int]:
    """Discover candidates only beneath git worktree roots; the same semantic snapshot may exist
    in several copies, two different valid snapshots are a conflict."""

    valid: list[tuple[Path, dict[str, object]]] = []
    for root in sorted(set(worktree_roots), key=lambda p: str(p)):
        candidate = root.joinpath(*ALPHA_REGISTRY_RELATIVE)
        if not candidate.is_file():
            continue
        try:
            valid.append((candidate, verify_alpha_registry(candidate)))
        except Exception:
            continue
    if not valid:
        raise OperatorStop("ALPHA_LINEAGE_EVIDENCE_MISSING")
    snapshots = {canonical(item[1]) for item in valid}
    if len(snapshots) != 1:
        raise OperatorStop("ALPHA_LINEAGE_CONFLICT")
    return valid[0][0], valid[0][1], len(valid)


def verify_af1(repo_root: Path) -> dict[str, object]:
    try:
        evidence = read_json(repo_root / AF1_EVIDENCE_PATH)
        receipt = af1_record_from_mapping(AF1GateReceipt, evidence["gate_receipt"])  # type: ignore[index]
        validate_af1_record(receipt)
    except Exception:
        raise OperatorStop("AF1_EVIDENCE_DRIFT") from None
    statuses = dict(receipt.dimension_statuses)
    if (
        receipt.gate_receipt_id != qd.AF1_RECEIPT_ID
        or receipt.overall_disposition != "AF1_PASS"
        or receipt.evidence_state != "FINALIZED"
        or set(statuses) != set(AF1_DIMENSIONS)
        or any(status != "PASS" for status in statuses.values())
    ):
        raise OperatorStop("AF1_EVIDENCE_DRIFT")
    return {"gate_receipt_id": receipt.gate_receipt_id, "overall_disposition": receipt.overall_disposition,
            "evidence_state": receipt.evidence_state, "dimensions_pass": len(statuses)}


def code_digests(repo_root: Path) -> dict[str, str]:
    return {path: sha256_hex((repo_root / path).read_bytes().replace(b"\r\n", b"\n")) for path in CODE_FILES}


def frozen_plan_body() -> dict[str, object]:
    return {
        "wp_id": WP_ID,
        "base_sha": BASE_SHA,
        "predecessor": {"pr": PREDECESSOR_PR, "head": PREDECESSOR_HEAD, "merge": BASE_SHA},
        "target_dates": list(qd.target_dates()),
        "checkpoints": qd.checkpoint_definitions(),
        "discovery_hours_utc_on_target_date": list(DISCOVERY_HOURS_UTC),
        "label_window_minutes_around_gamma_closed_time": int(LABEL_WINDOW.total_seconds() // 60),
        "market_history_scan": "hour of checkpoint backward to max(checkpoint-24h, v3 first receive) until the latest best_bid_ask <= checkpoint is found",
        "ndfd_product": ndfd.PRODUCT_FILE_PREFIX + "* (CONUS PoP12) whole-object GET",
        "allowlist": sorted(ALLOWED_HOSTS),
        "methods": sorted(ALLOWED_METHODS),
        "budgets": {
            "target_dates": MAX_TARGET_DATES, "candidates": MAX_CANDIDATES, "stations": MAX_STATIONS,
            "pendulum_hours": MAX_PENDULUM_HOURS, "attempts": MAX_ATTEMPTS, "total_bytes": MAX_TOTAL_BYTES,
            "single_response_bytes": MAX_SINGLE_RESPONSE, "retries_per_request": MAX_RETRIES_PER_REQUEST,
        },
        "decoder": {"python": "3.12", "eccodes": ndfd.EXPECTED_ECCODES_VERSION, "eccodeslib_non_windows": ndfd.EXPECTED_ECCODESLIB_VERSION},
        "lineage": {"alpha_candidate_id": qd.ALPHA_CANDIDATE_ID, "alpha_family_id": qd.ALPHA_FAMILY_ID,
                    "alpha_episode_id": qd.ALPHA_EPISODE_ID, "alpha_registry_head": qd.ALPHA_REGISTRY_HEAD,
                    "af1_receipt_id": qd.AF1_RECEIPT_ID},
    }


# ── Environment (injectable for hermetic tests) ───────────────────────────────


def _git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise OperatorStop("STATE_DRIFT")
    return completed.stdout


@dataclasses.dataclass
class Environment:
    repo_root: Path = REPO_ROOT
    git: Callable[..., str] | None = None
    fetch: Callable[..., tuple[int, dict[str, str], bytes]] | None = None
    gamma_client_factory: Callable[[], object] | None = None
    decode_fn: Callable[..., ndfd.DecodedPop12] | None = None
    require_decoder: bool = True

    @property
    def workspace(self) -> Path:
        return self.repo_root.joinpath(*WORKSPACE_PARTS)

    def run_git(self, *args: str) -> str:
        return (self.git or (lambda *a: _git(self.repo_root, *a)))(*args)

    def decoder(self) -> Callable[..., ndfd.DecodedPop12]:
        if self.decode_fn is not None:
            return self.decode_fn
        if self.require_decoder:
            try:
                ndfd.require_decoder(True)
            except ndfd.NdfdError:
                raise OperatorStop("DECODER_UNAVAILABLE") from None
        return ndfd.decode_pop12_message


def worktree_roots(env: Environment) -> list[Path]:
    roots = []
    for line in env.run_git("worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            roots.append(Path(line[len("worktree "):].strip()))
    return roots


# ── Commands ──────────────────────────────────────────────────────────────────


def load_plan(env: Environment) -> dict[str, object]:
    plan_path = env.workspace / PLAN_FILENAME
    hash_path = env.workspace / PLAN_HASH_FILENAME
    if not plan_path.exists() or not hash_path.exists():
        raise OperatorStop("PLAN_MISSING")
    plan = read_json(plan_path)
    if not isinstance(plan, dict) or sha256_hex(canonical(plan)) != hash_path.read_text(encoding="utf-8").strip():
        raise OperatorStop("PLAN_INVALID")
    if plan.get("frozen") != frozen_plan_body():
        raise OperatorStop("PLAN_INVALID")
    if plan.get("code_digests") != code_digests(env.repo_root):
        raise OperatorStop("CODE_DRIFT")
    return plan


def command_prepare(env: Environment) -> dict[str, object]:
    head = env.run_git("rev-parse", "HEAD").strip()
    branch = env.run_git("rev-parse", "--abbrev-ref", "HEAD").strip()
    dirty = env.run_git("status", "--porcelain", "--untracked-files=normal").strip()
    try:
        env.run_git("merge-base", "--is-ancestor", BASE_SHA, "HEAD")
    except OperatorStop:
        raise OperatorStop("STATE_DRIFT") from None
    if not re.fullmatch(r"[0-9a-f]{40}", head) or branch != PINNED_BRANCH or dirty:
        raise OperatorStop("STATE_DRIFT")
    source, lineage, copies = discover_alpha_registry(worktree_roots(env))
    af1 = verify_af1(env.repo_root)
    workspace = env.workspace
    plan = {
        "schema_id": "s10-qual-data-01-run-plan",
        "schema_version": "1.0.0",
        "frozen": frozen_plan_body(),
        "repo_code_identity": head,
        "code_digests": code_digests(env.repo_root),
        "alpha_registry": {**lineage, "source_sha256": sha256_hex(source.read_bytes()), "verified_copies_found": copies},
        "af1": af1,
    }
    plan_path = workspace / PLAN_FILENAME
    if plan_path.exists():
        existing = read_json(plan_path)
        comparable = dict(existing) if isinstance(existing, dict) else {}
        if isinstance(comparable.get("alpha_registry"), dict):
            comparable["alpha_registry"] = {k: v for k, v in comparable["alpha_registry"].items() if k != "copy_sha256"}
        if comparable != plan:
            raise OperatorStop("PREPARE_WORKSPACE_CONFLICT")
        return {"status": "PREPARED_IDEMPOTENT", "plan_sha256": sha256_hex(canonical(existing))}
    if workspace.exists() and any(workspace.iterdir()):
        raise OperatorStop("PREPARE_WORKSPACE_CONFLICT")
    workspace.mkdir(parents=True, exist_ok=True)
    copy_path = workspace / REGISTRY_COPY_FILENAME
    shutil.copyfile(source, copy_path)
    try:
        copied = verify_alpha_registry(copy_path)
    except Exception:
        copy_path.unlink(missing_ok=True)
        raise OperatorStop("ALPHA_LINEAGE_EVIDENCE_MISSING") from None
    if copied != lineage:
        raise OperatorStop("ALPHA_LINEAGE_CONFLICT")
    plan["alpha_registry"]["copy_sha256"] = sha256_hex(copy_path.read_bytes())  # type: ignore[index]
    write_json_atomic(plan_path, plan)
    (workspace / PLAN_HASH_FILENAME).write_text(sha256_hex(canonical(plan)) + "\n", encoding="utf-8")
    write_json_atomic(workspace / STATE_FILENAME, {"status": "PREPARED"})
    return {"status": "PREPARED", "plan_sha256": sha256_hex(canonical(plan))}


def _verify_registry_copy(env: Environment, plan: Mapping[str, object]) -> None:
    copy_path = env.workspace / REGISTRY_COPY_FILENAME
    expected = plan["alpha_registry"]  # type: ignore[index]
    try:
        lineage = verify_alpha_registry(copy_path)
    except Exception:
        raise OperatorStop("ALPHA_LINEAGE_EVIDENCE_MISSING") from None
    if sha256_hex(copy_path.read_bytes()) != expected["copy_sha256"] or lineage["entry_hashes"] != expected["entry_hashes"]:  # type: ignore[index]
        raise OperatorStop("ALPHA_LINEAGE_CONFLICT")


def command_probe(env: Environment) -> dict[str, object]:
    plan = load_plan(env)
    decode = env.decoder()
    probe_root = env.workspace / "probe"
    ledger = Ledger()
    store = ArtifactStore(probe_root, BoundedTransport(ledger, env.fetch),
                          env.gamma_client_factory or default_gamma_client_factory)
    checks: dict[str, object] = {}
    status = "PROBE_PASS"
    try:
        hours = V3Hours(store, None)
        events = hours.full_product_events(PROBE_HOUR, "new_market")
        checks["v3_manifest_product_range_sha256"] = "PASS"
        candidates, _bad = qd.candidates_from_new_market(
            [e for e in events if (e.field("slug") or "").startswith("where-will-it-rain-on-")]
        )
        if not candidates:
            raise OperatorStop("SOURCE_CONTRACT_DRIFT")
        candidate = candidates[0]
        gamma_doc = store.gamma_market(candidate.market_id, ledger)
        try:
            gamma = qd.normalize_gamma_market(gamma_doc, candidate)
        except qd.RuleExclusion:
            raise OperatorStop("SOURCE_CONTRACT_DRIFT") from None
        checks["gamma_by_id_identity"] = "PASS"
        rule = qd.parse_rule(gamma.description)
        checks["rule_semantics"] = rule.finality_policy
        station_raw = store.get(f"https://{NWS_HOST}/stations/{rule.station_id}", accept="application/geo+json",
                                media_type="application/geo+json")
        station = ndfd.parse_nws_station(json.loads(station_raw.decode("utf-8")), rule.station_id)
        checks["nws_station_metadata"] = "PASS"
        bba = hours.targeted_events(PROBE_MARKET_HOUR, "best_bid_ask", [candidate.condition_id])
        if not any(e.asset_id in candidate.asset_ids for e in bba):
            raise OperatorStop("SOURCE_CONTRACT_DRIFT")
        checks["v3_targeted_row_group_read"] = "PASS"
        receive = qd.parse_utc(candidate.first_received)
        checkpoint = qd.checkpoint_a(receive, qd.gamma_open_time_if_trustworthy(gamma.open_time, receive))
        access = NdfdAccess(store, decode)
        objects = [o for d in {checkpoint.date(), (checkpoint - timedelta(days=1)).date()} for o in access.listing(d)]
        vintage = ndfd.select_vintage(objects, checkpoint, qd.NDFD_VINTAGE_LOOKBACK)
        if vintage is None:
            raise OperatorStop("SOURCE_CONTRACT_DRIFT")
        data = access.object_bytes(vintage)
        slices = ndfd.scan_messages(data)
        decoded = decode(ndfd.message_bytes(data, slices[0]), [station])
        checks["ndfd_production_decode"] = "PASS"
        checks["ndfd_messages_in_probe_object"] = len(slices)
        checks["ndfd_probe_value_present"] = decoded.station_values[0].pop12_percent is not None
    except OperatorStop as stop:
        status = stop.code
        failure_code = stop.code
    except (TransportFailure, TransportRefused, BudgetExhausted, v3.PendulumFlowError, ndfd.NdfdError,
            qd.ReadinessError, qd.RuleExclusion) as error:
        status = "SOURCE_CONTRACT_DRIFT"
        failure_code = str(getattr(error, "code", "SOURCE_CONTRACT_DRIFT"))
    except ValueError:
        status = "SOURCE_CONTRACT_DRIFT"
        failure_code = "VALUE_INVALID"
    result = {"status": status, "checks": checks, "ledger": ledger.to_mapping(),
              "plan_sha256": sha256_hex(canonical(plan))}
    if status != "PROBE_PASS":
        # Closed diagnostic only: the first probe step that did not pass and its closed code.
        result["failed_step"] = next((step for step in PROBE_STEPS if step not in checks), "UNKNOWN")
        result["failure_code"] = failure_code
    write_json_atomic(env.workspace / PROBE_FILENAME, result)
    if status != "PROBE_PASS":
        raise OperatorStop("SOURCE_CONTRACT_DRIFT")
    return result


# ── Deterministic readiness derivation (shared by run-readiness and verify-final) ──


@dataclasses.dataclass
class MarketState:
    candidate: qd.MarketCandidate
    target_day: date
    gamma: qd.GammaFacts | None = None
    rule: qd.RuleSemantics | None = None
    station: ndfd.StationMetadata | None = None
    offset: int | None = None
    label: qd.LabelEvidence | None = None
    observable: datetime | None = None
    checkpoint_a: datetime | None = None
    checkpoints: dict = dataclasses.field(default_factory=dict)  # checkpoint id -> time (eligible only)
    weather_by_cp: dict = dataclasses.field(default_factory=dict)
    scanned_by_cp: dict = dataclasses.field(default_factory=dict)
    weather_keys: set = dataclasses.field(default_factory=set)
    excluded: str | None = None
    row_excluded: dict = dataclasses.field(default_factory=dict)
    scanned_hours: list = dataclasses.field(default_factory=list)
    slug_parsed: bool = True
    history_complete: bool = False


class ReadinessPipeline:
    def __init__(self, store: ArtifactStore, plan: Mapping[str, object], decode_fn: Callable[..., ndfd.DecodedPop12],
                 ledger: Ledger | None) -> None:
        self.store = store
        self.plan = plan
        self.decode_fn = decode_fn
        self.ledger = ledger
        self.markets: dict[str, MarketState] = {}
        self.market_exclusions: list[dict[str, object]] = []
        self.discovered = 0
        self.hours: V3Hours | None = None
        self.ndfd: NdfdAccess | None = None
        self.audit: v3.V3AuditSnapshot | None = None
        self.source_unavailable = False
        self.budget_exhausted: str | None = None
        self.touched_hours: set[str] = set()
        self.discovery_failures: dict[str, str] = {}
        self.station_keys: dict[str, str] = {}
        self.gamma_keys: dict[str, str] = {}
        self.audit_key = ArtifactStore.key("GET", pf_url("audit"))
        self.label_hours: dict[str, list[str]] = {}
        self.events: dict[tuple[str, str], list[v3.V3Event]] = {}

    # -- helpers --
    def _exclude(self, state: MarketState, reason: str) -> None:
        if state.excluded is None:
            state.excluded = reason

    def _active(self) -> list[MarketState]:
        return [s for s in sorted(self.markets.values(), key=lambda s: (s.target_day, len(s.candidate.market_id), s.candidate.market_id))
                if s.excluded is None]

    def _hour(self, hour: str) -> None:
        if hour not in self.touched_hours:
            if len(self.touched_hours) + 1 > MAX_PENDULUM_HOURS:
                raise BudgetExhausted("PENDULUM_HOUR_BUDGET_EXHAUSTED")
            self.touched_hours.add(hour)

    # -- phases --
    def phase_audit(self) -> None:
        try:
            raw = self.store.get(pf_url("audit"), accept="text/html", media_type="text/html")
            self.audit = v3.parse_audit_page(raw)
        except (TransportFailure, v3.PendulumFlowError):
            self.audit = None
            self.source_unavailable = True
        self.hours = V3Hours(self.store, self.audit)
        self.ndfd = NdfdAccess(self.store, self.decode_fn)

    def phase_discovery(self) -> None:
        assert self.hours is not None
        dates = [date.fromisoformat(d) for d in self.plan["frozen"]["target_dates"]]  # type: ignore[index]
        if len(dates) > MAX_TARGET_DATES:
            raise BudgetExhausted("TARGET_DATE_BUDGET_EXHAUSTED")
        rain_events: list[v3.V3Event] = []
        for day in dates:
            for hh in DISCOVERY_HOURS_UTC:
                hour = f"{day.isoformat()}/{hh:02d}"
                self._hour(hour)
                try:
                    events = self.hours.full_product_events(hour, "new_market")
                except v3.PendulumFlowError as error:
                    self.discovery_failures[hour] = error.code
                    continue
                rain_events.extend(
                    e for e in events
                    if (e.field("slug") or "").startswith("where-will-it-rain-on-")
                    or re.fullmatch(r"Will it rain in .+ on .+\?", e.field("question") or "")
                )
        candidates, inconsistent = qd.candidates_from_new_market(rain_events)
        self.discovered = len(candidates) + len(inconsistent)
        if self.discovered > MAX_CANDIDATES:
            raise BudgetExhausted("CANDIDATE_BUDGET_EXHAUSTED")
        if len(self.discovery_failures) == len(dates) * len(DISCOVERY_HOURS_UTC):
            self.source_unavailable = True
        for item in inconsistent:
            self.market_exclusions.append(qd.exclusion(item["market_id"], item["reason"]))
        window = set(self.plan["frozen"]["target_dates"])  # type: ignore[index]
        for candidate in candidates:
            parsed = qd.parse_rain_slug(candidate.slug)
            state = MarketState(candidate, parsed[0] if parsed else date.fromisoformat(qd.target_dates()[0]),
                                slug_parsed=parsed is not None)
            self.markets[candidate.market_id] = state
            if parsed is None:
                self._exclude(state, "SLUG_NOT_DAILY_RAIN_FAMILY")
            elif parsed[0].isoformat() not in window:
                self._exclude(state, "TARGET_DATE_OUTSIDE_CORPUS")

    def phase_gamma_rules(self) -> None:
        for state in self._active():
            key = ArtifactStore.key("GET", f"https://{GAMMA_HOST}/markets/{state.candidate.market_id}") + " via=PolymarketPublicClient.get_market"
            self.gamma_keys[state.candidate.market_id] = key
            try:
                document = self.store.gamma_market(state.candidate.market_id, self.ledger)
            except TransportFailure:
                self._exclude(state, "GAMMA_UNAVAILABLE")
                continue
            try:
                state.gamma = qd.normalize_gamma_market(document, state.candidate)
                state.rule = qd.parse_rule(state.gamma.description)
            except qd.RuleExclusion as exclusion:
                self._exclude(state, exclusion.code)

    def phase_stations(self) -> None:
        stations = sorted({s.rule.station_id for s in self._active() if s.rule is not None})
        if len(stations) > MAX_STATIONS:
            raise BudgetExhausted("STATION_BUDGET_EXHAUSTED")
        metadata: dict[str, ndfd.StationMetadata | str] = {}
        for station_id in stations:
            url = f"https://{NWS_HOST}/stations/{station_id}"
            self.station_keys[station_id] = ArtifactStore.key("GET", url)
            try:
                raw = self.store.get(url, accept="application/geo+json", media_type="application/geo+json")
                metadata[station_id] = ndfd.parse_nws_station(json.loads(raw.decode("utf-8")), station_id)
            except TransportFailure:
                metadata[station_id] = "STATION_METADATA_UNAVAILABLE"
            except (ndfd.NdfdError, ValueError, UnicodeDecodeError):
                metadata[station_id] = "STATION_METADATA_INVALID"
        for state in self._active():
            meta = metadata[state.rule.station_id]  # type: ignore[union-attr]
            if isinstance(meta, str):
                self._exclude(state, meta)
                continue
            state.station = meta
            try:
                state.offset = ndfd.standard_utc_offset_minutes(meta.time_zone, state.target_day)
            except ndfd.NdfdError:
                self._exclude(state, "STATION_OFFSET_UNDERIVABLE")

    def phase_labels(self) -> None:
        assert self.hours is not None
        for state in self._active():
            gamma = state.gamma
            assert gamma is not None
            if gamma.winning_outcome is None or gamma.closed_time is None:
                self._exclude(state, "LABEL_GAMMA_NOT_FINAL")
                continue
            closed = qd.parse_utc(gamma.closed_time)
            hours = v3.hours_between(closed - LABEL_WINDOW, closed + LABEL_WINDOW)
            self.label_hours[state.candidate.market_id] = list(hours)
            resolutions: list[v3.V3Event] = []
            for hour in hours:
                self._hour(hour)
                if (hour, "market_resolved") not in self.events:
                    try:
                        self.events[(hour, "market_resolved")] = list(self.hours.full_product_events(hour, "market_resolved"))
                    except v3.PendulumFlowError:
                        self.events[(hour, "market_resolved")] = []
                resolutions.extend(e for e in self.events[(hour, "market_resolved")] if e.condition_id == state.candidate.condition_id)
            try:
                state.label = qd.resolve_label(gamma, resolutions)
            except qd.RuleExclusion as exclusion:
                self._exclude(state, exclusion.code)

    def phase_checkpoints(self) -> None:
        for state in self._active():
            receive = qd.parse_utc(state.candidate.first_received)
            gamma_open = qd.gamma_open_time_if_trustworthy(state.gamma.open_time if state.gamma else None, receive)
            state.observable = qd.observable_time(receive, gamma_open)
            state.checkpoint_a = qd.checkpoint_a(receive, gamma_open)
            state.checkpoints[qd.CHECKPOINT_A] = state.checkpoint_a
            b_time, eligible = qd.checkpoint_b(state.target_day, state.offset, state.observable)  # type: ignore[arg-type]
            if eligible:
                state.checkpoints[qd.CHECKPOINT_B] = b_time
            else:
                state.row_excluded[qd.CHECKPOINT_B] = "CHECKPOINT_B_MARKET_NOT_OPEN_60M"
            for checkpoint_id, checkpoint in state.checkpoints.items():
                if state.label is not None and qd.parse_utc(state.label.v3_resolution_received) <= checkpoint:
                    state.row_excluded[checkpoint_id] = "LABEL_RESOLVED_BEFORE_CHECKPOINT"

    def _row_pending(self, state: MarketState, checkpoint_id: str) -> bool:
        return (state.excluded is None and checkpoint_id in state.checkpoints
                and checkpoint_id not in state.row_excluded)

    def _pending_pairs(self) -> list[tuple[MarketState, str, datetime]]:
        """Every (market, eligible checkpoint) still pending, in deterministic order."""

        return [(state, checkpoint_id, state.checkpoints[checkpoint_id])
                for state in self._active() for checkpoint_id in qd.CHECKPOINT_IDS
                if self._row_pending(state, checkpoint_id)]

    def phase_weather(self) -> None:
        assert self.ndfd is not None
        plans: dict[tuple[str, str], tuple[ndfd.NdfdObject, MarketState, str, datetime]] = {}
        for state, checkpoint_id, checkpoint in self._pending_pairs():
            low = checkpoint - qd.NDFD_VINTAGE_LOOKBACK
            days = sorted({(low + timedelta(hours=h)).date() for h in range(0, 49)} | {checkpoint.date()})
            objects: list[ndfd.NdfdObject] = []
            try:
                for day in days:
                    objects.extend(self.ndfd.listing(day))
                    state.weather_keys |= self.ndfd.keys_by_day.get(day.isoformat(), set())
            except ndfd.NdfdError:
                state.row_excluded[checkpoint_id] = "WEATHER_SOURCE_INVALID"
                continue
            vintage = ndfd.select_vintage(objects, checkpoint, qd.NDFD_VINTAGE_LOOKBACK)
            if vintage is None:
                state.row_excluded[checkpoint_id] = "WEATHER_NO_ELIGIBLE_VINTAGE"
                continue
            plans[(state.candidate.market_id, checkpoint_id)] = (vintage, state, checkpoint_id, checkpoint)
        decoded_cache: dict[tuple[str, int], tuple[ndfd.MessageSlice, ndfd.DecodedPop12] | str] = {}
        needs: dict[tuple[str, int], dict[str, ndfd.StationMetadata]] = {}
        object_info: dict[str, tuple[bytes, tuple[ndfd.MessageSlice, ...], list[ndfd.Pop12Header]] | str] = {}
        for _key, (vintage, state, checkpoint_id, _checkpoint) in sorted(plans.items()):
            if vintage.key not in object_info:
                try:
                    data = self.ndfd.object_bytes(vintage)
                    slices = ndfd.scan_messages(data)
                    headers = [ndfd.parse_pop12_header(ndfd.message_bytes(data, piece)) for piece in slices]
                    object_info[vintage.key] = (data, slices, headers)
                except ndfd.NdfdError:
                    object_info[vintage.key] = "WEATHER_SOURCE_INVALID"
            info = object_info[vintage.key]
            state.weather_keys |= self.ndfd.keys_by_object.get(vintage.key, set())
            if isinstance(info, str):
                state.row_excluded[checkpoint_id] = info
                continue
            start, end = ndfd.climate_day_window(state.target_day, state.offset)  # type: ignore[arg-type]
            for index in ndfd.intervals_overlapping(info[2], start, end):
                needs.setdefault((vintage.key, index), {})[state.station.station_id] = state.station  # type: ignore[union-attr]
        for (key, index), stations in sorted(needs.items()):
            data, slices, _headers = object_info[key]  # type: ignore[misc]
            try:
                decoded = self.decode_fn(ndfd.message_bytes(data, slices[index]), [stations[s] for s in sorted(stations)])
                decoded_cache[(key, index)] = (slices[index], decoded)
            except ndfd.NdfdError as error:
                decoded_cache[(key, index)] = "GRID_BINDING_INVALID" if error.code == "GRID_BINDING_INVALID" else "WEATHER_SOURCE_INVALID"
        for _key, (vintage, state, checkpoint_id, checkpoint) in sorted(plans.items()):
            if not self._row_pending(state, checkpoint_id):
                continue
            info = object_info[vintage.key]
            assert not isinstance(info, str)
            start, end = ndfd.climate_day_window(state.target_day, state.offset)  # type: ignore[arg-type]
            indexes = ndfd.intervals_overlapping(info[2], start, end)
            pairs = []
            failure = None
            for index in indexes:
                item = decoded_cache.get((vintage.key, index))
                if isinstance(item, str):
                    failure = item
                    break
                pairs.append(item)
            if failure:
                state.row_excluded[checkpoint_id] = failure
                continue
            # ``weather_evidence`` expects decoded periods indexed like the object's messages.
            full = []
            for index in range(len(info[1])):
                item = decoded_cache.get((vintage.key, index))
                if item is not None and not isinstance(item, str):
                    full.append(item)
            try:
                state.weather_by_cp[checkpoint_id] = qd.weather_evidence(
                    vintage, sha256_hex(info[0]), full, state.station, state.offset,  # type: ignore[arg-type]
                    state.target_day, checkpoint)
            except qd.RuleExclusion as exclusion:
                state.row_excluded[checkpoint_id] = exclusion.code

    def phase_market_history(self) -> None:
        assert self.hours is not None
        by_date: dict[date, list[tuple[MarketState, str, datetime]]] = {}
        for pair in self._pending_pairs():
            by_date.setdefault(pair[0].target_day, []).append(pair)
        for day in sorted(by_date):
            pairs = by_date[day]
            key = lambda pair: (pair[0].candidate.market_id, pair[1])  # noqa: E731
            lower = {key(p): v3.hour_start(v3.hour_key(max(p[2] - qd.MARKET_HISTORY_LOOKBACK,
                                                          qd.parse_utc(p[0].candidate.first_received)))) for p in pairs}
            top = max(v3.hour_start(v3.hour_key(p[2])) for p in pairs)
            found: set[tuple[str, str]] = set()
            cursor = top
            while True:
                active = [p for p in pairs if key(p) not in found
                          and v3.hour_start(v3.hour_key(p[2])) >= cursor >= lower[key(p)]]
                if not active:
                    if all(cursor < lower[key(p)] or key(p) in found for p in pairs):
                        break
                    cursor -= timedelta(hours=1)
                    continue
                hour = v3.hour_key(cursor)
                self._hour(hour)
                conditions = sorted({p[0].candidate.condition_id for p in active})
                for family in ("best_bid_ask", "last_trade_price"):
                    try:
                        events = self.hours.targeted_events(hour, family, conditions)
                    except v3.PendulumFlowError:
                        events = ()
                    self.events.setdefault((hour, family), []).extend(events)
                if (hour, "tick_size_change") not in self.events:
                    try:
                        self.events[(hour, "tick_size_change")] = list(self.hours.full_product_events(hour, "tick_size_change"))
                    except v3.PendulumFlowError:
                        self.events[(hour, "tick_size_change")] = []
                for state, checkpoint_id, checkpoint in active:
                    state.scanned_by_cp.setdefault(checkpoint_id, []).append(hour)
                    if hour not in state.scanned_hours:
                        state.scanned_hours.append(hour)
                    token = qd.yes_token(state.gamma)  # type: ignore[arg-type]
                    if any(e.asset_id == token and qd.parse_utc(e.timestamp_received) <= checkpoint
                           for e in self.events[(hour, "best_bid_ask")]):
                        found.add((state.candidate.market_id, checkpoint_id))
                cursor -= timedelta(hours=1)
            for state, _checkpoint_id, _checkpoint in pairs:
                state.history_complete = True

    def _coverage_map(self, product: str) -> dict[str, str]:
        assert self.hours is not None
        return {hour: self.hours.coverage(hour, product) for hour in sorted(self.touched_hours) if hour in self.hours.manifests}

    def build(self) -> tuple[dict[str, object], list[object]]:
        assert self.hours is not None
        bba_coverage = self._coverage_map("best_bid_ask")
        ltp_coverage = self._coverage_map("last_trade_price")
        rows: list[dict[str, object]] = []
        row_exclusions: list[dict[str, object]] = []
        execution: dict[str, dict[str, object]] = {}
        candidate_rows: list[tuple[MarketState, str, datetime, dict[str, object], dict[str, object], dict[str, object]]] = []
        for state in sorted(self.markets.values(), key=lambda s: (s.target_day, len(s.candidate.market_id), s.candidate.market_id)):
            market_id = state.candidate.market_id
            if state.excluded is not None:
                self.market_exclusions.append(qd.exclusion(
                    market_id, state.excluded, target_date=state.target_day.isoformat() if state.slug_parsed else None))
                continue
            trade_events = [e for h in state.scanned_hours for e in self.events.get((h, "last_trade_price"), [])
                            if e.condition_id == state.candidate.condition_id]
            tick_events = [e for h in state.scanned_hours for e in self.events.get((h, "tick_size_change"), [])
                           if e.asset_id in state.candidate.asset_ids]
            execution[market_id] = qd.execution_facts(state.gamma, state.rule, trade_events, tick_events)  # type: ignore[arg-type]
            for checkpoint_id in qd.CHECKPOINT_IDS:
                # Every checkpoint either has its actual closed exclusion reason or was evaluated.
                reason = state.row_excluded.get(checkpoint_id)
                if reason is None and checkpoint_id not in state.checkpoints:
                    if self.budget_exhausted is None:
                        raise qd.ReadinessError("READINESS_INPUT_INVALID")
                    reason = "BUDGET_EXHAUSTED_BEFORE_EVALUATION"
                if reason is None:
                    checkpoint = state.checkpoints[checkpoint_id]
                    scanned = state.scanned_by_cp.get(checkpoint_id, [])
                    try:
                        if checkpoint_id not in state.weather_by_cp:
                            raise qd.RuleExclusion("BUDGET_EXHAUSTED_BEFORE_EVALUATION" if self.budget_exhausted
                                                   else "WEATHER_SOURCE_INVALID")
                        token = qd.yes_token(state.gamma)  # type: ignore[arg-type]
                        bba_events = [e for h in scanned for e in self.events.get((h, "best_bid_ask"), [])
                                      if e.condition_id == state.candidate.condition_id]
                        bba = qd.select_latest_market_event(
                            bba_events, family="best_bid_ask", asset_id=token, checkpoint=checkpoint,
                            lookback=qd.MARKET_HISTORY_LOOKBACK, scanned_hours=scanned, hour_coverage=bba_coverage)
                        cp_trades = [e for h in scanned for e in self.events.get((h, "last_trade_price"), [])
                                     if e.condition_id == state.candidate.condition_id]
                        try:
                            ltp = qd.select_latest_market_event(
                                cp_trades, family="last_trade_price", asset_id=token, checkpoint=checkpoint,
                                lookback=qd.MARKET_HISTORY_LOOKBACK, scanned_hours=scanned, hour_coverage=ltp_coverage)
                        except qd.RuleExclusion:
                            ltp = None
                        history = qd.market_history_evidence(bba, ltp, checkpoint, bba_coverage, ltp_coverage, scanned)
                        candidate_rows.append((state, checkpoint_id, checkpoint, history, state.weather_by_cp[checkpoint_id],
                                               state.label.to_mapping(state.rule)))  # type: ignore[union-attr,arg-type]
                    except qd.RuleExclusion as exclusion:
                        reason = exclusion.code
                if reason is not None:
                    row_exclusions.append(qd.exclusion(market_id, reason, checkpoint_id, state.target_day.isoformat()))
        manifests, ready_ids_by_date, diagnostic_ids, dataset_ids = self._provenance(candidate_rows)
        for state, checkpoint_id, checkpoint, history, weather, label in candidate_rows:
            ready = ready_ids_by_date.get(state.target_day.isoformat())
            if not ready:
                row_exclusions.append(qd.exclusion(state.candidate.market_id, "MARKET_HISTORY_SOURCE_INVALID",
                                                   checkpoint_id, state.target_day.isoformat()))
                continue
            rows.append(qd.build_row(
                candidate=state.candidate, target_day=state.target_day, checkpoint_id=checkpoint_id,
                checkpoint_time=checkpoint, yes_token_id=qd.yes_token(state.gamma),  # type: ignore[arg-type]
                market_history=history, weather=weather, label=label, manifest_ids=ready))
        counts = qd.derive_counts(self.discovered, rows, self.market_exclusions, row_exclusions, bba_coverage,
                                  [r["feature_evidence"]["weather"]["object_key"] for r in rows])  # type: ignore[index]
        if self.budget_exhausted:
            reason = "FROZEN_BUDGET_EXHAUSTED"
        elif self.source_unavailable:
            reason = "SOURCE_UNAVAILABLE"
        elif rows:
            reason = "EVIDENCE_COMPLETE_ROWS_PRESENT"
        else:
            reason = "NO_EVIDENCE_COMPLETE_ROW"
        source_facts = {
            "audit": None if self.audit is None else {
                "partial_hours_in_scope": sorted(h for h in self.audit.partial_hours if h in self.touched_hours),
                "measured_on": self.audit.measured_on, "measured_hours": self.audit.measured_hours,
                "published_hours": self.audit.published_hours},
            "discovery_hours_utc": list(DISCOVERY_HOURS_UTC),
            "discovery_hour_failures": dict(sorted(self.discovery_failures.items())),
            "pendulumflow_hours_touched": len(self.touched_hours),
            "pendulumflow_bba_coverage_by_hour": bba_coverage,
            "pendulumflow_invalid_rows_skipped": self.hours.invalid_rows,
            "pendulumflow_range_integrity": "small products (new_market, market_resolved, tick_size_change) are complete product ranges verified against the manifest SHA-256 (EXACT); best_bid_ask/last_trade_price row-group column chunks and footers are bound to the manifest byte range but not digest-verifiable in isolation (FAITHFUL)",
            "label_window_minutes": int(LABEL_WINDOW.total_seconds() // 60),
            "ndfd_vintages": sorted({(r["feature_evidence"]["weather"]["object_key"], r["feature_evidence"]["weather"]["public_available_time"]) for r in rows}),  # type: ignore[index]
            "stations": sorted(self.station_keys),
            "frozen_budget_exhausted": self.budget_exhausted is not None,
            "decoder_contract": {"eccodes": ndfd.EXPECTED_ECCODES_VERSION, "python": "3.12"},
        }
        source_facts["ndfd_vintages"] = [list(v) for v in source_facts["ndfd_vintages"]]  # type: ignore[union-attr]
        bundle = qd.build_bundle(
            rows=rows, market_exclusions=self.market_exclusions, row_exclusions=row_exclusions, counts=counts,
            execution_evidence=execution, ready_manifest_ids=sorted({i for ids in ready_ids_by_date.values() for i in ids}),
            diagnostic_manifest_ids=diagnostic_ids, external_dataset_ids=dataset_ids, source_facts=source_facts,
            terminal_reason=reason)
        return bundle, manifests

    # -- provenance --
    def _artifact(self, key: str, kind: str, coverage: str | None = None) -> qd.RetainedArtifact:
        entry = self.store.entry(key)
        method, url, *rest = key.split(" ")
        parts = urllib.parse.urlsplit(url)
        params: list[tuple[str, str]] = []
        if rest and rest[0].startswith("bytes="):
            params.append(("range", rest[0][len("bytes="):]))
        if parts.query:
            params.extend(sorted(urllib.parse.parse_qsl(parts.query)))
        last_modified = entry.get("last_modified")
        public_time = None
        if isinstance(last_modified, str) and kind in ("v3", "v3_product", "ndfd_object"):
            try:
                public_time = qd.utc_text(datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=timezone.utc))
            except ValueError:
                public_time = None
        fidelity = {"complete": "EXACT", "v3_product": "EXACT", "v3": "FAITHFUL", "gamma": "FAITHFUL",
                    "ndfd_object": "EXACT"}[kind]
        dq: tuple[str, ...] = ("OK",)
        if coverage is not None and coverage not in v3.ADMISSIBLE_COVERAGE_CLASSES:
            dq, fidelity = ("PARTIALLY_OBSERVED",), "PARTIAL"
        return qd.RetainedArtifact(
            source_system={PENDULUMFLOW_HOST: "pendulumflow-v3", NDFD_HOST: "noaa-ndfd-pds", GAMMA_HOST: "polymarket-gamma",
                           NWS_HOST: "nws-api"}[parts.hostname],  # type: ignore[index]
            endpoint=f"{parts.hostname}{parts.path}",
            retrieval_method="HTTP_RANGE_GET" if params and params[0][0] == "range" else "HTTP_GET",
            request_parameters=tuple(params),
            content_sha256=str(entry["sha256"]),
            byte_length=int(entry["bytes"]),  # type: ignore[arg-type]
            media_type=str(entry.get("media_type") or "application/octet-stream"),
            public_available_time=public_time,
            event_time=None,
            resolution_time=None,
            dq_flags=dq,
            replay_fidelity=fidelity,
        )

    def _v3_kind(self, key: str, hour: str) -> tuple[str, str | None]:
        assert self.hours is not None
        if key.endswith("manifest.json"):
            return "complete", None
        manifest = self.hours.manifests.get(hour)
        if manifest is not None and " bytes=" in key:
            start, end = (int(x) for x in key.rsplit(" bytes=", 1)[1].split("-"))
            for product in manifest.products:
                if (start, end) == (product.byte_start, product.byte_end):
                    return "v3_product", self.hours.coverage(hour, product.name)
                if product.byte_start <= start and end <= product.byte_end:
                    return "v3", self.hours.coverage(hour, product.name)
        return "v3", None

    def _provenance(self, candidate_rows):
        assert self.hours is not None and self.ndfd is not None
        repo_identity = str(self.plan["repo_code_identity"])
        # External-history descriptors (declared source identity, never canonical PIT).
        dataset_ids: list[str] = []
        pf_objects = [
            ExternalSourceObject(v3.parquet_object_path(h), m.file_sha256, m.file_bytes, h)
            for h, m in sorted(self.hours.manifests.items())
        ]
        if pf_objects:
            hours_sorted = sorted(self.hours.manifests)
            descriptor = build_external_dataset_descriptor(
                provider_id=v3.PROVIDER_ID, dataset_name=v3.DATASET_NAME, dataset_version="union-event-sorted-v1",
                source_class=v3.SOURCE_CLASS,
                coverage_start=qd.utc_text(v3.hour_start(hours_sorted[0])),
                coverage_end=qd.utc_text(v3.hour_start(hours_sorted[-1]) + timedelta(hours=1)),
                source_objects=pf_objects[:1024],
                source_schema_fingerprint_sha256=sha256_hex(canonical({k: list(v) for k, v in v3.READ_COLUMNS.items()})),
                source_timestamp_semantics="venue timestamp (exchange, milliseconds UTC)",
                receive_timestamp_semantics="timestamp_received (capture host receipt, microseconds UTC); ordering basis",
                event_types=list(v3.REQUIRED_EVENT_FAMILIES), known_gap_policy="archive audit PARTIAL/SINGLE-BY-DEFECT hours diagnostic only",
                quality_tier="THIRD_PARTY_EXTERNAL", importer_id="s10-qual-data-01-operator", importer_version="1.0.0",
                license_id="UNSPECIFIED_PUBLIC_ARCHIVE", attribution="PendulumFlow Polymarket Orderbook Archive v3 (archive.pendulumflow.com)")
            if descriptor.is_valid:
                dataset_ids.append(descriptor.descriptor.external_dataset_id)  # type: ignore[union-attr]
        nd_objects = [
            ExternalSourceObject(key, sha256_hex(data), len(data), key.split("/")[-1])
            for key, data in sorted(self.ndfd.objects.items()) if data is not None
        ]
        if nd_objects:
            descriptor = build_external_dataset_descriptor(
                provider_id=ndfd.PROVIDER_ID, dataset_name=ndfd.DATASET_NAME, dataset_version="wmo-grib2-pop12",
                source_class=ndfd.SOURCE_CLASS,
                coverage_start=min(o.public_available_time for objs in self.ndfd.listings.values() if objs for o in objs),
                coverage_end=max(o.public_available_time for objs in self.ndfd.listings.values() if objs for o in objs),
                source_objects=nd_objects[:1024],
                source_schema_fingerprint_sha256=sha256_hex(b"GRIB2 template 4.9 discipline 0 category 1 number 8"),
                source_timestamp_semantics="GRIB reference time and forecast valid interval (section 1/4)",
                receive_timestamp_semantics="S3 LastModified conservative public availability bound",
                event_types=["PoP12"], known_gap_policy="missing vintages excluded, never interpolated",
                quality_tier="OFFICIAL", importer_id="s10-qual-data-01-operator", importer_version="1.0.0",
                license_id="US_GOVERNMENT_PUBLIC_DOMAIN", attribution="NOAA NDFD via NOAA Open Data Dissemination (noaa-ndfd-pds)")
            if descriptor.is_valid:
                dataset_ids.append(descriptor.descriptor.external_dataset_id)  # type: ignore[union-attr]
        # Group retained artifacts by target date and source family.
        groups: dict[tuple[str, str], dict[str, qd.RetainedArtifact]] = {}
        outputs: dict[tuple[str, str], list[dict[str, object]]] = {}
        cutoffs: dict[tuple[str, str], datetime] = {}

        def add(day: str, family: str, key: str, artifact: qd.RetainedArtifact) -> None:
            groups.setdefault((day, family), {})[key] = artifact

        for state in sorted(self.markets.values(), key=lambda s: (s.target_day, len(s.candidate.market_id), s.candidate.market_id)):
            if state.excluded is not None and state.gamma is None:
                continue
            day = state.target_day.isoformat()
            for hour in sorted({state.candidate.discovery_hour, *state.scanned_hours}):
                for key in sorted(self.hours.keys_by_hour.get(hour, ())):
                    if key in self.store.index and "failed" not in self.store.index[key]:
                        kind, coverage = self._v3_kind(key, hour)
                        add(day, "PENDULUMFLOW_MARKET_HISTORY", key, self._artifact(key, kind, coverage))
            for key in sorted(state.weather_keys):
                if key in self.store.index and "failed" not in self.store.index[key]:
                    add(day, "NOAA_NDFD_WEATHER", key, self._artifact(key, "ndfd_object" if "YDUZ98" in key else "complete"))
            meta_keys = [self.gamma_keys.get(state.candidate.market_id), self.audit_key]
            if state.rule is not None:
                meta_keys.append(self.station_keys.get(state.rule.station_id))
            for key in meta_keys:
                if key and key in self.store.index and "failed" not in self.store.index[key]:
                    add(day, "GAMMA_NWS_RULE_LABEL_METADATA", key,
                        self._artifact(key, "gamma" if "via=" in key else "complete"))
            for hour in self.label_hours.get(state.candidate.market_id, []):
                for key in sorted(self.hours.keys_by_hour.get(hour, ())):
                    if key in self.store.index and "failed" not in self.store.index[key]:
                        kind, coverage = self._v3_kind(key, hour)
                        add(day, "GAMMA_NWS_RULE_LABEL_METADATA", key, self._artifact(key, kind, coverage))
        for state, checkpoint_id, checkpoint, history, weather, label in candidate_rows:
            day = state.target_day.isoformat()
            record = {"market_id": state.candidate.market_id, "checkpoint_id": checkpoint_id,
                      "evidence_sha256": sha256_hex(qd.canonical_json_bytes({"market_history": history, "weather": weather, "label": label}))}
            for family in ("PENDULUMFLOW_MARKET_HISTORY", "NOAA_NDFD_WEATHER", "GAMMA_NWS_RULE_LABEL_METADATA"):
                outputs.setdefault((day, family), []).append(record)
                cutoffs[(day, family)] = max(cutoffs.get((day, family), checkpoint), checkpoint)
        all_manifests = []
        ready_by_date: dict[str, list[str]] = {}
        ready_families: dict[str, set[str]] = {}
        diagnostic_ids: list[str] = []
        for (day, family), artifacts in sorted(groups.items()):
            refs_ok, refs_degraded = [], []
            for key in sorted(artifacts):
                ref = qd.raw_reference(artifacts[key])
                (refs_ok if ref.dq_flags == ("OK",) else refs_degraded).append(ref)
            cutoff = cutoffs.get((day, family), datetime.fromisoformat(day + "T00:00:00+00:00") + timedelta(days=1))
            if family == "GAMMA_NWS_RULE_LABEL_METADATA":
                # Label evidence is post-outcome by construction; its cutoff is the latest retained label time.
                label_times = [qd.parse_utc(s.label.v3_resolution_received) for s in self.markets.values()
                               if s.label is not None and s.target_day.isoformat() == day]
                cutoff = max(label_times) if label_times else cutoff
            ready_manifests = qd.build_shard_manifests(
                target_date=day, shard_kind=family, references=refs_ok, output_records=outputs.get((day, family), []),
                information_cutoff=cutoff, repo_code_identity=repo_identity, dataset_refs=dataset_ids)
            degraded = qd.build_shard_manifests(
                target_date=day, shard_kind=family, references=refs_degraded, output_records=[],
                information_cutoff=cutoff, repo_code_identity=repo_identity, dataset_refs=dataset_ids)
            ready, diag = qd.split_ready_manifests(ready_manifests)
            all_manifests.extend(ready_manifests + degraded)
            diagnostic_ids.extend(m.research_provenance_manifest_id for m in diag + degraded)
            if ready and len(ready) == len(ready_manifests):
                ready_by_date.setdefault(day, []).extend(m.research_provenance_manifest_id for m in ready)
                ready_families.setdefault(day, set()).add(family)
        required = {"PENDULUMFLOW_MARKET_HISTORY", "NOAA_NDFD_WEATHER", "GAMMA_NWS_RULE_LABEL_METADATA"}
        # A date's rows are ready only when every one of its three source-family shards is a ready
        # manifest (DQ OK, EXACT/FAITHFUL, empty gap); otherwise its rows are excluded, never laundered.
        final_ready = {day: sorted(ids) for day, ids in ready_by_date.items() if ready_families.get(day, set()) >= required}
        return all_manifests, final_ready, sorted(diagnostic_ids), sorted(dataset_ids)

    def run(self) -> tuple[dict[str, object], list[object]]:
        phases = (self.phase_audit, self.phase_discovery, self.phase_gamma_rules, self.phase_stations,
                  self.phase_labels, self.phase_checkpoints, self.phase_weather, self.phase_market_history)
        for phase in phases:
            try:
                phase()
            except BudgetExhausted as exhausted:
                self.budget_exhausted = exhausted.code
                break
            if self.source_unavailable:
                # A whole source (the archive audit, or every discovery hour) is unavailable: no
                # row can be evidence-complete, so the remaining budget is not spent.
                break
        if self.budget_exhausted:
            # Markets with no final disposition are recorded truthfully, never silently dropped.
            for state in self.markets.values():
                if (state.excluded is None and not state.history_complete
                        and any(self._row_pending(state, cp) for cp in qd.CHECKPOINT_IDS)):
                    state.excluded = "BUDGET_EXHAUSTED_BEFORE_EVALUATION"
            if self.hours is None:
                self.hours = V3Hours(self.store, self.audit)
                self.ndfd = NdfdAccess(self.store, self.decode_fn)
        return self.build()


def command_run(env: Environment) -> dict[str, object]:
    plan = load_plan(env)
    state_path = env.workspace / STATE_FILENAME
    state = read_json(state_path) if state_path.exists() else {}
    if isinstance(state, dict) and state.get("status") == "FINAL":
        raise OperatorStop("RUN_ALREADY_FINALIZED")
    probe = env.workspace / PROBE_FILENAME
    if not probe.exists() or read_json(probe).get("status") != "PROBE_PASS":  # type: ignore[union-attr]
        raise OperatorStop("PROBE_REQUIRED")
    _verify_registry_copy(env, plan)
    verify_af1(env.repo_root)
    decode = env.decoder()
    ledger_path = env.workspace / LEDGER_FILENAME
    ledger = Ledger.from_mapping(read_json(ledger_path)) if ledger_path.exists() else Ledger()  # type: ignore[arg-type]
    resumed = bool(state.get("status") == "RUNNING") if isinstance(state, dict) else False
    write_json_atomic(state_path, {"status": "RUNNING", "resumed": resumed})
    store = ArtifactStore(env.workspace, BoundedTransport(ledger, env.fetch),
                          env.gamma_client_factory or default_gamma_client_factory)
    try:
        pipeline = ReadinessPipeline(store, plan, decode, ledger)
        bundle, manifests = pipeline.run()
    finally:
        write_json_atomic(ledger_path, ledger.to_mapping())
    qd.verify_bundle(bundle)
    write_json_atomic(env.workspace / MANIFESTS_FILENAME, [m.logical_preimage() | {"id": m.research_provenance_manifest_id} for m in manifests])
    write_json_atomic(env.workspace / BUNDLE_FILENAME, bundle)
    report = {
        "wp_id": WP_ID,
        "plan_sha256": sha256_hex(canonical(plan)),
        "bundle_id": bundle["bundle_id"],
        "logical_dataset_id": bundle["logical_dataset_id"],
        "terminal": bundle["terminal"],
        "terminal_reason": bundle["terminal_reason"],
        "network_ledger": ledger.to_mapping(),
        "resumed": resumed,
        "python": platform.python_version(),
        "platform": platform.system(),
        "retained_artifacts": len(store.index),
        "completed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    write_json_atomic(env.workspace / REPORT_FILENAME, report)
    write_json_atomic(state_path, {"status": "FINAL", "terminal": bundle["terminal"], "bundle_id": bundle["bundle_id"]})
    return report


class _NetworkForbidden(Exception):
    pass


def _forbid_network() -> Callable[[], None]:
    originals = (socket.socket.connect, socket.socket.connect_ex, socket.create_connection, socket.getaddrinfo)

    def refuse(*_args: object, **_kwargs: object):
        raise _NetworkForbidden("network forbidden during verify-final")

    socket.socket.connect = refuse  # type: ignore[assignment]
    socket.socket.connect_ex = refuse  # type: ignore[assignment]
    socket.create_connection = refuse  # type: ignore[assignment]
    socket.getaddrinfo = refuse  # type: ignore[assignment]

    def restore() -> None:
        socket.socket.connect, socket.socket.connect_ex, socket.create_connection, socket.getaddrinfo = originals  # type: ignore[assignment]

    return restore


def command_verify(env: Environment) -> dict[str, object]:
    restore = _forbid_network()
    try:
        plan = load_plan(env)
        state = read_json(env.workspace / STATE_FILENAME) if (env.workspace / STATE_FILENAME).exists() else {}
        if not isinstance(state, dict) or state.get("status") != "FINAL":
            raise OperatorStop("RUN_NOT_FINAL")
        _verify_registry_copy(env, plan)
        af1 = verify_af1(env.repo_root)
        decode = env.decoder()
        store = ArtifactStore(env.workspace, None, None, replay=True)
        rehashed = 0
        for key, entry in sorted(store.index.items()):
            if "failed" in entry:
                continue
            store._read_verified(str(entry["sha256"]))  # noqa: SLF001
            rehashed += 1
        stored = read_json(env.workspace / BUNDLE_FILENAME)
        try:
            qd.verify_bundle(stored)  # type: ignore[arg-type]
        except qd.ReadinessError:
            raise OperatorStop("VERIFY_FAILED") from None
        pipeline = ReadinessPipeline(store, plan, decode, None)
        if stored.get("terminal_reason") == "FROZEN_BUDGET_EXHAUSTED":  # type: ignore[union-attr]
            original_get = store.get

            def get_or_exhaust(*args, **kwargs):
                try:
                    return original_get(*args, **kwargs)
                except ReplayMissing:
                    raise BudgetExhausted("REPLAYED_BUDGET_EXHAUSTION") from None

            store.get = get_or_exhaust  # type: ignore[method-assign]
        try:
            rebuilt, manifests = pipeline.run()
        except (ReplayMissing, _NetworkForbidden):
            raise OperatorStop("VERIFY_FAILED") from None
        if canonical(rebuilt) != canonical(stored):
            raise OperatorStop("VERIFY_FAILED")
        stored_manifests = read_json(env.workspace / MANIFESTS_FILENAME)
        rebuilt_manifests = [m.logical_preimage() | {"id": m.research_provenance_manifest_id} for m in manifests]
        if canonical(stored_manifests) != canonical(rebuilt_manifests):
            raise OperatorStop("VERIFY_FAILED")
        for manifest in manifests:
            if manifest.research_provenance_manifest_id in rebuilt["dataset"]["ready_manifest_ids"]:  # type: ignore[index]
                qd.require_ready_manifests([manifest])
        result = {
            "status": "VERIFIED",
            "network_calls": 0,
            "plan_sha256": sha256_hex(canonical(plan)),
            "rehashed_artifacts": rehashed,
            "bundle_id": rebuilt["bundle_id"],
            "logical_dataset_id": rebuilt["logical_dataset_id"],
            "terminal": rebuilt["terminal"],
            "b0_contract_compatibility": rebuilt["dataset"]["b0_contract_compatibility"],  # type: ignore[index]
            "ready_manifests": len(rebuilt["dataset"]["ready_manifest_ids"]),  # type: ignore[index]
            "af1_receipt_id": af1["gate_receipt_id"],
            "alpha_registry_head": plan["alpha_registry"]["head_entry_hash"],  # type: ignore[index]
        }
        write_json_atomic(env.workspace / VERIFY_FILENAME, result)
        return result
    finally:
        restore()


COMMANDS = {
    "prepare": command_prepare,
    "probe-sources": command_probe,
    "run-readiness": command_run,
    "verify-final": command_verify,
}


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> "None":  # type: ignore[override]
        raise OperatorStop("USAGE_ERROR")


def main(argv: Sequence[str] | None = None, env: Environment | None = None) -> int:
    parser = _Parser(prog="run_s10_qual_data_01.py", add_help=False)
    parser.add_argument("command", choices=sorted(COMMANDS))
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
        result = COMMANDS[args.command](env or Environment())
    except OperatorStop as stop:
        print(f"STOP {stop.code}")
        return 2 if stop.code == "USAGE_ERROR" else 3
    summary = {k: result[k] for k in ("status", "terminal", "terminal_reason", "bundle_id", "logical_dataset_id", "plan_sha256") if k in result}
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
