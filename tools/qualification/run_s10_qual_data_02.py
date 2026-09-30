"""Manual foreground operator for S10-QUAL-DATA-02 (weather qualification corpus completion).

Frozen package: ``docs/wp_specs/S10-QUAL-DATA-02/`` and
``docs/qualification_weather_corpus_completion_contract.md``.

This is the ONLY network owner of S10-QUAL-DATA-02. It completes the frozen S10-QUAL-DATA-01
corpus by re-deriving the whole corpus with the unchanged S10-QUAL-DATA-01 derivation, using the
verified PR #202 run-01 raw artifacts as a content-addressed cache ("seed") and fetching only the
evidence the seed does not hold. It changes only four things relative to S10-QUAL-DATA-01:
failed-read accounting (S10-QUAL-DATA-01-D011), throttle handling, seed reuse and the bounded
budget. The S10-QUAL-DATA-01 operator and offline modules are imported unchanged; the only core
edit is the additive ``LABEL_V3_SOURCE_READ_FAILED`` market-exclusion code.

Exact command grammar (always run from the repository root):

  prepare          zero network: repo/predecessor gate, PR #202 seed discovery under git worktree
                   roots, seed verification bound to the exact predecessor code, admission of only
                   hash-valid successful seed artifacts, seed report, frozen plan + plan hash
  probe-sources    bounded: seed cache hit, one unseeded live fetch compared with the seed, typed
                   D011 failure, Gamma-by-id identity, production NDFD decode
  run-completion   ONE bounded real completion run from the frozen plan (seed used as cache)
  verify-final     zero network: re-hash seed + new artifacts, replay the derivation from retained
                   artifacts only; bundle, manifests, counts, seed and network accounting must match

Network: https GET / HEAD / Range GET only to archive.pendulumflow.com,
noaa-ndfd-pds.s3.amazonaws.com, gamma-api.polymarket.com (through the existing verified
``PolymarketPublicClient.get_market`` only) and api.weather.gov; no redirect, credential or
arbitrary URL. HTTP 429/503: at most three retries after the frozen delays 2 s, 8 s, 30 s (an
integer ``Retry-After`` in [0, 60] can only lengthen a delay); timeout/reset/truncation and other
retryable statuses: at most one immediate retry. No jitter, no adaptive retry. Every attempt and
received byte counts; seed bytes do not. Console output is closed codes, ids and digests only.
"""

from __future__ import annotations

import argparse
import dataclasses
import http.client
import json
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research import nws_ndfd_history as ndfd  # noqa: E402
from src.data_layer.analytical_research import pendulumflow_v3 as v3  # noqa: E402
from src.data_layer.analytical_research import qualification_data_readiness as qd  # noqa: E402
from src.data_layer.analytical_research.external_dataset import (  # noqa: E402
    ExternalSourceObject,
    build_external_dataset_descriptor,
)
from src.data_layer.polymarket.errors import PolymarketHTTPError, PolymarketReadOnlyError  # noqa: E402
from tools.qualification import run_s10_qual_data_01 as d1  # noqa: E402

# ── Frozen package identity ───────────────────────────────────────────────────

WP_ID = "S10-QUAL-DATA-02"
BASE_SHA = "6f67bac990d8ab338f1b87140ae077e9df4172dd"
PREDECESSOR_PR = 202
PREDECESSOR_HEAD = "33c031f41626550294eb6667620b4ce75589d719"
PINNED_BRANCH = "codex/s10-qual-data-02-weather-corpus-completion"
IMPORTER_ID = "s10-qual-data-02-operator"
CODE_FILES = (
    "src/data_layer/analytical_research/pendulumflow_v3.py",
    "src/data_layer/analytical_research/nws_ndfd_history.py",
    "src/data_layer/analytical_research/qualification_data_readiness.py",
    "tools/qualification/run_s10_qual_data_01.py",
    "tools/qualification/run_s10_qual_data_02.py",
)
PREDECESSOR_CODE_FILES = d1.CODE_FILES

# Frozen PR #202 seed (S10-QUAL-DATA-01 replacement run-01).
SEED_PARTS = ("local_data", "s10_qual_data_01", "run-01")
SEED_TERMINAL = qd.TERMINAL_INSUFFICIENT
SEED_TERMINAL_REASON = "FROZEN_BUDGET_EXHAUSTED"
SEED_BUNDLE_ID = "weatherqualbundle:sha256:ceca0252b4d41cf9b49591bb3a65ed9e0b79d9321b269ecbab86f5a90ea085e1"
SEED_DATASET_ID = "weatherqualdataset:sha256:9058a05354390ca7e61bcb47871f93b925e99571f7cc48f40b057eb0e8454413"
SEED_ENTRY_FIELDS = ("sha256", "bytes", "media_type", "last_modified", "status")

WORKSPACE_PARTS = ("local_data", "s10_qual_data_02", "run-01")
PLAN_FILENAME = "PLAN.json"
PLAN_HASH_FILENAME = "PLAN.sha256"
SEED_INDEX_FILENAME = "SEED_INDEX.json"
SEED_REPORT_FILENAME = "SEED_REPORT.json"
SEED_RAW_DIRNAME = "seed_raw"
REGISTRY_COPY_FILENAME = d1.REGISTRY_COPY_FILENAME
STATE_FILENAME = "STATE.json"
LEDGER_FILENAME = "NETWORK_LEDGER.json"
PROBE_FILENAME = "PROBE_RESULT.json"
BUNDLE_FILENAME = "READINESS_BUNDLE.json"
REPORT_FILENAME = "RUN_REPORT.json"
VERIFY_FILENAME = "VERIFY_FINAL.json"
MANIFESTS_FILENAME = "PROVENANCE_MANIFESTS.json"

# ── Network allowlist, retry policy and frozen new-network caps ───────────────

PENDULUMFLOW_HOST = d1.PENDULUMFLOW_HOST
NDFD_HOST = d1.NDFD_HOST
GAMMA_HOST = d1.GAMMA_HOST
NWS_HOST = d1.NWS_HOST
ALLOWED_HOSTS = d1.ALLOWED_HOSTS
ALLOWED_METHODS = d1.ALLOWED_METHODS
USER_AGENT = "polymarket-strategy-lab/S10-QUAL-DATA-02 (public read-only research; toobigtofailbot-maker)"

THROTTLE_STATUSES = frozenset({429, 503})
THROTTLE_DELAYS_SECONDS = (2, 8, 30)
MAX_THROTTLE_RETRIES = 3
RETRY_AFTER_MAX_SECONDS = 60
MAX_TRANSPORT_RETRIES = 1
OTHER_RETRYABLE_STATUSES = d1.RETRYABLE_STATUSES - THROTTLE_STATUSES

MAX_NETWORK_ATTEMPTS = 12_288
MAX_RESPONSE_BYTES = 6_442_450_944
MAX_SINGLE_RESPONSE = 268_435_456
MAX_DISTINCT_PENDULUM_HOURS = 2_000

# In-memory bound on retained PendulumFlow range bytes. An evicted hour's bytes are re-read from
# the local content-addressed store (already indexed), never from the network; results are unchanged.
MEMORY_RANGE_BYTES = 1_073_741_824
LTP_STATE_SEARCH_INCOMPLETE = "NOT_OBSERVED_SEARCH_INCOMPLETE_SOURCE_READ_FAILED"
READ_STAGES = ("MANIFEST", "TAIL", "FOOTER", "PRODUCT", "CHUNK", "DECODE")
PROBE_HOUR = d1.PROBE_HOUR
PROBE_MARKET_HOUR = d1.PROBE_MARKET_HOUR
PROBE_STEPS = (
    "seed_cache_hit",
    "gamma_by_id_identity",
    "rule_semantics",
    "unseeded_fetch_matches_seed",
    "d011_typed_failure",
    "ndfd_production_decode",
)

STOP_CODES = (
    "USAGE_ERROR",
    "STATE_DRIFT",
    "SEED_EVIDENCE_MISSING",
    "SEED_EVIDENCE_CONFLICT",
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

TransportRefused = d1.TransportRefused
TransportFailure = d1.TransportFailure
BudgetExhausted = d1.BudgetExhausted
ReplayMissing = d1.ReplayMissing
canonical = d1.canonical
sha256_hex = d1.sha256_hex
write_json_atomic = d1.write_json_atomic
read_json = d1.read_json


class OperatorStop(Exception):
    def __init__(self, code: str) -> None:
        if code not in STOP_CODES:
            code = "USAGE_ERROR"
        super().__init__(code)
        self.code = code


class SeedInvalid(ValueError):
    """A predecessor store that is present but not the exact verified PR #202 seed."""


class SourceReadFailed(Exception):
    """A v3 read or decode that failed after the allowed retries; never an empty result."""

    def __init__(self, stage: str, code: str) -> None:
        super().__init__(code)
        self.stage = stage
        self.code = code


# ── Ledger and bounded transport (429/503 backoff) ────────────────────────────


@dataclasses.dataclass
class Ledger:
    attempts: int = 0
    retries: int = 0
    throttle_retries: int = 0
    transport_retries: int = 0
    retry_after_valid: int = 0
    retry_after_extended: int = 0
    backoff_seconds: int = 0
    bytes: int = 0
    max_single_response: int = 0
    attempts_by_host: dict = dataclasses.field(default_factory=dict)
    bytes_by_host: dict = dataclasses.field(default_factory=dict)
    statuses: dict = dataclasses.field(default_factory=dict)
    refusals: int = 0
    exhausted: str | None = None
    # Probe traffic already spent against the same frozen caps (counted, never re-spent).
    baseline_attempts: int = 0
    baseline_bytes: int = 0

    def to_mapping(self) -> dict[str, object]:
        return dataclasses.asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "Ledger":
        return cls(**{field.name: value[field.name] for field in dataclasses.fields(cls)})  # type: ignore[arg-type]

    def total_attempts(self) -> int:
        return self.baseline_attempts + self.attempts

    def total_bytes(self) -> int:
        return self.baseline_bytes + self.bytes

    def check_attempt(self, expected_bytes: int | None) -> None:
        if self.total_attempts() + 1 > MAX_NETWORK_ATTEMPTS:
            self.exhausted = "ATTEMPT_BUDGET_EXHAUSTED"
            raise BudgetExhausted(self.exhausted)
        if expected_bytes is not None and self.total_bytes() + expected_bytes > MAX_RESPONSE_BYTES:
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

    def check_bytes(self) -> None:
        if self.total_bytes() > MAX_RESPONSE_BYTES:
            self.exhausted = "BYTE_BUDGET_EXHAUSTED"
            raise BudgetExhausted(self.exhausted)

    def note_transport_retry(self) -> None:
        self.retries += 1
        self.transport_retries += 1

    def note_throttle_retry(self, delay: int, valid: bool, extended: bool) -> None:
        self.retries += 1
        self.throttle_retries += 1
        self.backoff_seconds += delay
        self.retry_after_valid += int(valid)
        self.retry_after_extended += int(extended)


def throttle_delay(retry_index: int, retry_after: object) -> tuple[int, bool, bool]:
    """Frozen delay for throttle retry ``retry_index`` (0-based): ``(delay, retry_after_valid,
    retry_after_extended)``. Only an integer ``Retry-After`` in [0, 60] is honoured, and only to
    lengthen the frozen delay; dates, negatives, fractions and larger values are ignored."""

    frozen = THROTTLE_DELAYS_SECONDS[retry_index]
    if isinstance(retry_after, str) and re.fullmatch(r"\d{1,6}", retry_after.strip()):
        value = int(retry_after.strip())
        if value <= RETRY_AFTER_MAX_SECONDS:
            return max(frozen, value), True, value > frozen
    return frozen, False, False


class BoundedTransport:
    def __init__(self, ledger: Ledger, fetch: Callable[..., tuple[int, dict[str, str], bytes]] | None = None,
                 sleep: Callable[[float], None] | None = None) -> None:
        self.ledger = ledger
        self._fetch = fetch or d1.urllib_fetch
        self._sleep = sleep or time.sleep

    def request(self, method: str, url: str, *, byte_range: tuple[int, int] | None = None,
                accept: str = "*/*", expected_bytes: int | None = None) -> d1.Response:
        headers = {"User-Agent": USER_AGENT, "Accept": accept}
        if byte_range is not None:
            start, end = byte_range
            if not (0 <= start < end):
                raise TransportRefused("HEADER_NOT_ALLOWED")
            headers["Range"] = f"bytes={start}-{end - 1}"
            expected_bytes = end - start
        try:
            host, _path = d1.validate_request(method, url, headers)
        except TransportRefused:
            self.ledger.refusals += 1
            raise
        if expected_bytes is not None and expected_bytes > MAX_SINGLE_RESPONSE:
            self.ledger.refusals += 1
            raise TransportRefused("SINGLE_RESPONSE_CAP")
        throttles = transports = 0
        delay = 0
        while True:
            self.ledger.check_attempt(expected_bytes)
            if delay:
                self._sleep(delay)
                delay = 0
            try:
                status, response_headers, body = self._fetch(method, url, headers, d1.TIMEOUT_SECONDS)
            except d1._TransportError as error:  # noqa: SLF001
                self.ledger.record(host, None, 0)
                if transports < MAX_TRANSPORT_RETRIES:
                    transports += 1
                    self.ledger.note_transport_retry()
                    continue
                raise TransportFailure("TRANSPORT_" + error.kind) from None
            self.ledger.record(host, status, len(body))
            self.ledger.check_bytes()
            if len(body) > MAX_SINGLE_RESPONSE:
                raise TransportFailure("RESPONSE_TOO_LARGE")
            if 300 <= status < 400:
                raise TransportFailure("NETWORK_REDIRECT_REFUSED")
            if status in THROTTLE_STATUSES:
                if throttles < MAX_THROTTLE_RETRIES:
                    delay, valid, extended = throttle_delay(throttles, response_headers.get("retry-after"))
                    throttles += 1
                    self.ledger.note_throttle_retry(delay, valid, extended)
                    continue
                raise TransportFailure(f"HTTP_{status}")
            if status in OTHER_RETRYABLE_STATUSES:
                if transports < MAX_TRANSPORT_RETRIES:
                    transports += 1
                    self.ledger.note_transport_retry()
                    continue
                raise TransportFailure(f"HTTP_{status}")
            if byte_range is not None:
                if status == 206 and len(body) < byte_range[1] - byte_range[0]:
                    if transports < MAX_TRANSPORT_RETRIES:
                        transports += 1
                        self.ledger.note_transport_retry()
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
                declared = d1.content_length(response_headers)
                if declared is not None and len(body) < declared:
                    if transports < MAX_TRANSPORT_RETRIES:
                        transports += 1
                        self.ledger.note_transport_retry()
                        continue
                    raise TransportFailure("BODY_TRUNCATED")
                if declared is not None and len(body) > declared:
                    raise TransportFailure("BODY_LENGTH_MISMATCH")
            return d1.Response(status, response_headers, body)


# ── Seeded content-addressed artifact store ───────────────────────────────────


class ArtifactStore(d1.ArtifactStore):
    """The S10-QUAL-DATA-01 store plus a read-only seed cache.

    A request key present in the admitted seed index is served from the seed bytes (re-hashed)
    and indexed with ``origin: SEED`` and the seed's truthful source metadata; every other key is
    fetched through the bounded transport. Failed predecessor entries are never admitted, so they
    are fetched fresh. Replay never adopts: every key must already be indexed.
    """

    def __init__(self, root: Path, transport: BoundedTransport | None,
                 gamma_client_factory: Callable[[], object] | None = None, *, replay: bool = False,
                 seed_index: Mapping[str, Mapping[str, object]] | None = None, seed_raw: Path | None = None,
                 sleep: Callable[[float], None] | None = None) -> None:
        super().__init__(root, transport, gamma_client_factory, replay=replay)
        self.seed_index = dict(seed_index or {})
        self.seed_raw = seed_raw
        self._sleep = sleep or time.sleep

    def _read_verified(self, digest: str) -> bytes:
        path = self.raw / digest
        if not path.exists() and self.seed_raw is not None:
            path = self.seed_raw / digest
        try:
            data = path.read_bytes()
        except OSError:
            raise OperatorStop("VERIFY_FAILED") from None
        if sha256_hex(data) != digest:
            raise OperatorStop("VERIFY_FAILED")
        return data

    def adopt(self, key: str) -> bool:
        if self.replay or key in self.index or key not in self.seed_index:
            return False
        entry = self.seed_index[key]
        self._read_verified(str(entry["sha256"]))
        self.index[key] = {**{name: entry[name] for name in SEED_ENTRY_FIELDS}, "origin": "SEED"}
        self._persist()
        return True

    def get(self, url: str, *, byte_range: tuple[int, int] | None = None, accept: str = "*/*",
            media_type: str = "application/octet-stream", expected_bytes: int | None = None,
            use_seed: bool = True) -> bytes:
        if use_seed:
            self.adopt(self.key("GET", url, byte_range))
        return super().get(url, byte_range=byte_range, accept=accept, media_type=media_type,
                           expected_bytes=expected_bytes)

    def gamma_market(self, market_id: str, ledger: Ledger | None, *, use_seed: bool = True) -> dict[str, object]:
        """Gamma-by-id through the existing verified public client only (same retry policy)."""

        if not re.fullmatch(r"\d{1,20}", market_id):
            raise TransportRefused("URL_NOT_ALLOWED")
        url = f"https://{GAMMA_HOST}/markets/{market_id}"
        key = self.key("GET", url) + " via=PolymarketPublicClient.get_market"
        if use_seed:
            self.adopt(key)
        self.used.add(key)
        entry = self.index.get(key)
        if entry is not None:
            if "failed" in entry:
                raise TransportFailure(str(entry["failed"]))
            return json.loads(self._read_verified(str(entry["sha256"])).decode("utf-8"))
        if self.replay or self._gamma_factory is None or ledger is None:
            raise ReplayMissing(key)
        d1.validate_request("GET", url, {"User-Agent": USER_AGENT})
        if self._gamma_client is None:
            self._gamma_client = self._gamma_factory()
        failure_code = "GAMMA_UNAVAILABLE"
        throttles = transports = 0
        delay = 0
        while True:
            ledger.check_attempt(None)
            if delay:
                self._sleep(delay)
                delay = 0
            try:
                result = self._gamma_client.get_market(market_id)  # type: ignore[union-attr]
            except PolymarketHTTPError as error:
                ledger.record(GAMMA_HOST, error.status, len(getattr(error, "body", "") or ""))
                failure_code = f"HTTP_{error.status}"
                if error.status in THROTTLE_STATUSES and throttles < MAX_THROTTLE_RETRIES:
                    # The public client exposes no response headers: the frozen delay applies.
                    delay, valid, extended = throttle_delay(throttles, None)
                    throttles += 1
                    ledger.note_throttle_retry(delay, valid, extended)
                    continue
                if error.status in OTHER_RETRYABLE_STATUSES and transports < MAX_TRANSPORT_RETRIES:
                    transports += 1
                    ledger.note_transport_retry()
                    continue
                break
            except (PolymarketReadOnlyError, ConnectionError, TimeoutError, http.client.HTTPException, OSError):
                ledger.record(GAMMA_HOST, None, 0)
                failure_code = "TRANSPORT_ERROR"
                if transports < MAX_TRANSPORT_RETRIES:
                    transports += 1
                    ledger.note_transport_retry()
                    continue
                break
            data = canonical(result.data)
            ledger.record(GAMMA_HOST, result.request_info.status_code, len(data))
            ledger.check_bytes()
            if not isinstance(result.data, dict):
                failure_code = "GAMMA_RESPONSE_INVALID"
                break
            self._store(key, data, {"media_type": "application/json;canonical", "last_modified": None,
                                    "status": result.request_info.status_code})
            return result.data
        self.index[key] = {"failed": failure_code}
        self._persist()
        raise TransportFailure(failure_code)


# ── PendulumFlow hours with explicit read state (D011) ────────────────────────


class V3Hours(d1.V3Hours):
    """S10-QUAL-DATA-01 hour access plus a typed read state per ``(phase, family, hour)``.

    A failed manifest/tail/footer/product/chunk read or decode raises ``SourceReadFailed`` with its
    stage and closed code; it is never returned as an empty event list.
    """

    def __init__(self, store: ArtifactStore, audit: v3.V3AuditSnapshot | None) -> None:
        super().__init__(store, audit)
        self.stage = "MANIFEST"
        self.range_failure: str | None = None
        self.read_failures: dict[tuple[str, str, str], dict[str, str]] = {}
        self._recent: dict[str, None] = {}
        self._held_bytes = 0

    def _evict(self, current: str) -> None:
        self._recent.pop(current, None)
        self._recent[current] = None
        while self._held_bytes > MEMORY_RANGE_BYTES and len(self._recent) > 1:
            oldest = next(iter(self._recent))
            del self._recent[oldest]
            self._held_bytes -= sum(len(data) for _start, data in self.ranges.pop(oldest, []))
            self.files.pop(oldest, None)

    def _range(self, hour: str, start: int, end: int) -> bytes:
        url = d1.pf_url(v3.parquet_object_path(hour))
        self._track(hour, ArtifactStore.key("GET", url, (start, end)))
        try:
            data = self.store.get(url, byte_range=(start, end))
        except TransportFailure as failure:
            self.range_failure = failure.code
            raise v3.PendulumFlowError("V3_RANGE_NOT_RETAINED") from None
        self.ranges.setdefault(hour, []).append((start, data))
        self._held_bytes += len(data)
        return data

    def parquet(self, hour: str):
        if hour in self.files:
            return self.files[hour]
        self.stage = "MANIFEST"
        manifest = self.manifest(hour)
        self.stage = "TAIL"
        tail = self._range(hour, manifest.file_bytes - 8, manifest.file_bytes)
        footer_start, _length = v3.parse_parquet_tail(tail, manifest.file_bytes)
        self.stage = "FOOTER"
        self._range(hour, *v3.footer_fetch_range(manifest.file_bytes, footer_start))
        parquet = self._reopen(hour)
        self.files[hour] = parquet
        return parquet

    def full_product_events(self, hour: str, family: str) -> tuple[v3.V3Event, ...]:
        self.stage = "MANIFEST"
        product = self.manifest(hour).product(family)
        self.parquet(hour)
        self.stage = "PRODUCT"
        data = self._range(hour, product.byte_start, product.byte_end)
        v3.verify_product_bytes(product, data)
        self.stage = "DECODE"
        parquet = self._reopen(hour)
        events: list[v3.V3Event] = []
        for group in range(product.row_group_first, product.row_group_last + 1):
            events.extend(self._decode_group(parquet, hour, family, group, None))
        return tuple(events)

    def targeted_events(self, hour: str, family: str, condition_ids: Sequence[str]) -> tuple[v3.V3Event, ...]:
        self.stage = "MANIFEST"
        product = self.manifest(hour).product(family)
        parquet = self.parquet(hour)
        targets = [bytes.fromhex(cid[2:]) for cid in condition_ids]
        self.stage = "CHUNK"
        groups = v3.product_row_groups_for_markets(parquet, product, targets)
        for group in groups:
            for start, end in v3.column_chunk_ranges(parquet, product, group, v3.READ_COLUMNS[family]):
                if not any(s <= start and end <= s + len(d) for s, d in self.ranges.get(hour, [])):
                    self._range(hour, start, end)
        self.stage = "DECODE"
        parquet = self._reopen(hour)
        events: list[v3.V3Event] = []
        for group in groups:
            events.extend(self._decode_group(parquet, hour, family, group, set(targets)))
        return tuple(events)

    def read(self, phase: str, hour: str, family: str, conditions: Sequence[str] | None = None) -> tuple[v3.V3Event, ...]:
        """One typed read: the events, or ``SourceReadFailed`` recorded under (phase, family, hour)."""

        self.stage = "MANIFEST"
        self.range_failure = None
        try:
            if conditions is None:
                events = self.full_product_events(hour, family)
            else:
                events = self.targeted_events(hour, family, conditions)
            self._evict(hour)
            return events
        except v3.PendulumFlowError as error:
            if self.stage == "MANIFEST":
                code = self.failed.get(hour) or error.code
            else:
                code = self.range_failure or error.code
            self.read_failures.setdefault((phase, family, hour), {"stage": self.stage, "code": code})
            raise SourceReadFailed(self.stage, code) from None


def label_outcome(gamma: qd.GammaFacts, resolutions: Sequence[v3.V3Event], read_failed: bool) -> qd.LabelEvidence:
    """D011 label rule: a failed required ``market_resolved`` read is LABEL_V3_SOURCE_READ_FAILED;
    LABEL_V3_RESOLUTION_MISSING only after every relevant-window read succeeded."""

    if gamma.winning_outcome is None:
        raise qd.RuleExclusion("LABEL_GAMMA_NOT_FINAL")
    if read_failed:
        raise qd.RuleExclusion("LABEL_V3_SOURCE_READ_FAILED")
    return qd.resolve_label(gamma, resolutions)


# ── Completion pipeline (the unchanged DATA-01 derivation + D011 read state) ───


class CompletionPipeline(d1.ReadinessPipeline):
    def __init__(self, store: ArtifactStore, plan: Mapping[str, object], decode_fn: Callable[..., ndfd.DecodedPop12],
                 ledger: Ledger | None) -> None:
        super().__init__(store, plan, decode_fn, ledger)  # type: ignore[arg-type]
        self.history_invalid: dict[tuple[str, str], str] = {}
        self.ltp_failed: dict[tuple[str, str], list[str]] = {}
        self.tick_failed: set[str] = set()
        self.resolved_failed: set[str] = set()

    def _hour(self, hour: str) -> None:
        if hour not in self.touched_hours:
            if len(self.touched_hours) + 1 > MAX_DISTINCT_PENDULUM_HOURS:
                raise BudgetExhausted("PENDULUM_HOUR_BUDGET_EXHAUSTED")
            self.touched_hours.add(hour)

    def phase_audit(self) -> None:
        super().phase_audit()
        self.hours = V3Hours(self.store, self.audit)  # type: ignore[arg-type]

    def phase_labels(self) -> None:
        assert self.hours is not None
        for state in self._active():
            gamma = state.gamma
            assert gamma is not None
            if gamma.winning_outcome is None or gamma.closed_time is None:
                self._exclude(state, "LABEL_GAMMA_NOT_FINAL")
                continue
            closed = qd.parse_utc(gamma.closed_time)
            hours = v3.hours_between(closed - d1.LABEL_WINDOW, closed + d1.LABEL_WINDOW)
            self.label_hours[state.candidate.market_id] = list(hours)
            resolutions: list[v3.V3Event] = []
            read_failed = False
            for hour in hours:
                self._hour(hour)
                if (hour, "market_resolved") not in self.events and hour not in self.resolved_failed:
                    try:
                        self.events[(hour, "market_resolved")] = list(self.hours.read("labels", hour, "market_resolved"))  # type: ignore[attr-defined]
                    except SourceReadFailed:
                        self.resolved_failed.add(hour)
                if hour in self.resolved_failed:
                    read_failed = True
                    break
                resolutions.extend(e for e in self.events[(hour, "market_resolved")] if e.condition_id == state.candidate.condition_id)
            try:
                state.label = label_outcome(gamma, resolutions, read_failed)
            except qd.RuleExclusion as exclusion:
                self._exclude(state, exclusion.code)

    def phase_market_history(self) -> None:
        assert self.hours is not None
        by_date: dict[date, list[tuple[d1.MarketState, str, datetime]]] = {}
        for pair in self._pending_pairs():
            by_date.setdefault(pair[0].target_day, []).append(pair)
        for day in sorted(by_date):
            pairs = by_date[day]
            key = lambda pair: (pair[0].candidate.market_id, pair[1])  # noqa: E731
            lower = {key(p): v3.hour_start(v3.hour_key(max(p[2] - qd.MARKET_HISTORY_LOOKBACK,
                                                          qd.parse_utc(p[0].candidate.first_received)))) for p in pairs}
            top = max(v3.hour_start(v3.hour_key(p[2])) for p in pairs)
            done: set[tuple[str, str]] = set()  # found, or source-invalid (walk stopped)
            cursor = top
            while True:
                active = [p for p in pairs if key(p) not in done
                          and v3.hour_start(v3.hour_key(p[2])) >= cursor >= lower[key(p)]]
                if not active:
                    if all(cursor < lower[key(p)] or key(p) in done for p in pairs):
                        break
                    cursor -= timedelta(hours=1)
                    continue
                hour = v3.hour_key(cursor)
                self._hour(hour)
                conditions = sorted({p[0].candidate.condition_id for p in active})
                try:
                    bba = self.hours.read("market_history", hour, "best_bid_ask", conditions)  # type: ignore[attr-defined]
                except SourceReadFailed:
                    # D011: a failed required hour is not scanned; every pair still walking through
                    # it is source-invalid and its deeper walk-back stops here.
                    for state, checkpoint_id, _checkpoint in active:
                        self.history_invalid[(state.candidate.market_id, checkpoint_id)] = hour
                        done.add((state.candidate.market_id, checkpoint_id))
                    cursor -= timedelta(hours=1)
                    continue
                self.events.setdefault((hour, "best_bid_ask"), []).extend(bba)
                try:
                    trades = self.hours.read("market_history", hour, "last_trade_price", conditions)  # type: ignore[attr-defined]
                    ltp_ok = True
                except SourceReadFailed:
                    trades, ltp_ok = (), False
                self.events.setdefault((hour, "last_trade_price"), []).extend(trades)
                if (hour, "tick_size_change") not in self.events and hour not in self.tick_failed:
                    try:
                        self.events[(hour, "tick_size_change")] = list(
                            self.hours.read("market_history", hour, "tick_size_change"))  # type: ignore[attr-defined]
                    except SourceReadFailed:
                        self.tick_failed.add(hour)
                for state, checkpoint_id, checkpoint in active:
                    state.scanned_by_cp.setdefault(checkpoint_id, []).append(hour)
                    if hour not in state.scanned_hours:
                        state.scanned_hours.append(hour)
                    if not ltp_ok:
                        self.ltp_failed.setdefault((state.candidate.market_id, checkpoint_id), []).append(hour)
                    token = qd.yes_token(state.gamma)  # type: ignore[arg-type]
                    if any(e.asset_id == token and qd.parse_utc(e.timestamp_received) <= checkpoint
                           for e in self.events[(hour, "best_bid_ask")]):
                        done.add((state.candidate.market_id, checkpoint_id))
                cursor -= timedelta(hours=1)
            for state, _checkpoint_id, _checkpoint in pairs:
                state.history_complete = True

    def failed_read_facts(self) -> dict[str, object]:
        by_phase_family: dict[str, dict[str, int]] = {}
        by_stage: dict[str, int] = {}
        records = []
        failures = getattr(self.hours, "read_failures", {})
        for (phase, family, hour), detail in sorted(failures.items()):
            by_phase_family.setdefault(phase, {})
            by_phase_family[phase][family] = by_phase_family[phase].get(family, 0) + 1
            by_stage[detail["stage"]] = by_stage.get(detail["stage"], 0) + 1
            records.append([phase, family, hour, detail["stage"], detail["code"]])
        if self.discovery_failures:
            by_phase_family.setdefault("discovery", {})["new_market"] = len(self.discovery_failures)
        by_family: dict[str, int] = {}
        for families in by_phase_family.values():
            for family, count in families.items():
                by_family[family] = by_family.get(family, 0) + count
        return {
            "by_phase_family": {p: dict(sorted(f.items())) for p, f in sorted(by_phase_family.items())},
            "by_family": dict(sorted(by_family.items())),
            "by_stage": dict(sorted(by_stage.items())),
            "reads": records,
            "market_history_source_invalid_pairs": len(self.history_invalid),
            "tick_size_change_failed_hours": sorted(self.tick_failed),
            "market_resolved_failed_hours": sorted(self.resolved_failed),
        }

    def build(self) -> tuple[dict[str, object], list[object]]:
        assert self.hours is not None
        bba_coverage = self._coverage_map("best_bid_ask")
        ltp_coverage = self._coverage_map("last_trade_price")
        rows: list[dict[str, object]] = []
        row_exclusions: list[dict[str, object]] = []
        execution: dict[str, dict[str, object]] = {}
        candidate_rows: list[tuple[d1.MarketState, str, datetime, dict[str, object], dict[str, object], dict[str, object]]] = []
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
            facts = qd.execution_facts(state.gamma, state.rule, trade_events, tick_events)  # type: ignore[arg-type]
            # D011: failed trade/tick reads stay explicit; CURRENT_ONLY remains only on independent
            # current Gamma metadata, never implied by an unsearched hour.
            facts["FEES"]["v3_last_trade_price_failed_hours"] = sorted(
                {h for cp in qd.CHECKPOINT_IDS for h in self.ltp_failed.get((market_id, cp), [])})  # type: ignore[index]
            tick = facts["TICK_SIZE_MIN_ORDER"]
            tick["v3_tick_size_change_searched_hours"] = sorted(h for h in state.scanned_hours if h not in self.tick_failed)  # type: ignore[index]
            tick["v3_tick_size_change_failed_hours"] = sorted(h for h in state.scanned_hours if h in self.tick_failed)  # type: ignore[index]
            execution[market_id] = facts
            for checkpoint_id in qd.CHECKPOINT_IDS:
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
                        if (market_id, checkpoint_id) in self.history_invalid:
                            raise qd.RuleExclusion("MARKET_HISTORY_SOURCE_INVALID")
                        token = qd.yes_token(state.gamma)  # type: ignore[arg-type]
                        bba_events = [e for h in scanned for e in self.events.get((h, "best_bid_ask"), [])
                                      if e.condition_id == state.candidate.condition_id]
                        bba = qd.select_latest_market_event(
                            bba_events, family="best_bid_ask", asset_id=token, checkpoint=checkpoint,
                            lookback=qd.MARKET_HISTORY_LOOKBACK, scanned_hours=scanned, hour_coverage=bba_coverage)
                        ltp_failed = sorted(set(self.ltp_failed.get((market_id, checkpoint_id), [])))
                        ltp_scanned = [h for h in scanned if h not in ltp_failed]
                        cp_trades = [e for h in ltp_scanned for e in self.events.get((h, "last_trade_price"), [])
                                     if e.condition_id == state.candidate.condition_id]
                        try:
                            ltp = qd.select_latest_market_event(
                                cp_trades, family="last_trade_price", asset_id=token, checkpoint=checkpoint,
                                lookback=qd.MARKET_HISTORY_LOOKBACK, scanned_hours=ltp_scanned, hour_coverage=ltp_coverage)
                        except qd.RuleExclusion:
                            ltp = None
                        history = qd.market_history_evidence(bba, ltp, checkpoint, bba_coverage, ltp_coverage, ltp_scanned)
                        history["last_trade_price_failed_hours"] = ltp_failed
                        if ltp is None and ltp_failed:
                            history["last_trade_price_state"] = LTP_STATE_SEARCH_INCOMPLETE
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
            "completion": {"wp_id": WP_ID, "completes_wp_id": d1.WP_ID, "predecessor_bundle_id": SEED_BUNDLE_ID,
                           "predecessor_logical_dataset_id": SEED_DATASET_ID,
                           "derivation": "whole corpus re-derived; predecessor raw artifacts used only as a content-addressed cache"},
            "discovery_hours_utc": list(d1.DISCOVERY_HOURS_UTC),
            "discovery_hour_failures": dict(sorted(self.discovery_failures.items())),
            "pendulumflow_hours_touched": len(self.touched_hours),
            "pendulumflow_bba_coverage_by_hour": bba_coverage,
            "pendulumflow_invalid_rows_skipped": self.hours.invalid_rows,
            "pendulumflow_range_integrity": "small products (new_market, market_resolved, tick_size_change) are complete product ranges verified against the manifest SHA-256 (EXACT); best_bid_ask/last_trade_price row-group column chunks and footers are bound to the manifest byte range but not digest-verifiable in isolation (FAITHFUL)",
            "pendulumflow_failed_reads": self.failed_read_facts(),
            "label_window_minutes": int(d1.LABEL_WINDOW.total_seconds() // 60),
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

    def _provenance(self, candidate_rows):
        assert self.hours is not None and self.ndfd is not None
        repo_identity = str(self.plan["repo_code_identity"])
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
                quality_tier="THIRD_PARTY_EXTERNAL", importer_id=IMPORTER_ID, importer_version="1.0.0",
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
                quality_tier="OFFICIAL", importer_id=IMPORTER_ID, importer_version="1.0.0",
                license_id="US_GOVERNMENT_PUBLIC_DOMAIN", attribution="NOAA NDFD via NOAA Open Data Dissemination (noaa-ndfd-pds)")
            if descriptor.is_valid:
                dataset_ids.append(descriptor.descriptor.external_dataset_id)  # type: ignore[union-attr]
        groups: dict[tuple[str, str], dict[str, qd.RetainedArtifact]] = {}
        outputs: dict[tuple[str, str], list[dict[str, object]]] = {}
        cutoffs: dict[tuple[str, str], datetime] = {}

        def add(day: str, family: str, key: str, artifact: qd.RetainedArtifact) -> None:
            groups.setdefault((day, family), {})[key] = artifact

        def retained(key: str | None) -> bool:
            return bool(key) and key in self.store.index and "failed" not in self.store.index[key]  # type: ignore[operator]

        for state in sorted(self.markets.values(), key=lambda s: (s.target_day, len(s.candidate.market_id), s.candidate.market_id)):
            if state.excluded is not None and state.gamma is None:
                continue
            day = state.target_day.isoformat()
            for hour in sorted({state.candidate.discovery_hour, *state.scanned_hours}):
                for key in sorted(self.hours.keys_by_hour.get(hour, ())):
                    if retained(key):
                        kind, coverage = self._v3_kind(key, hour)
                        add(day, "PENDULUMFLOW_MARKET_HISTORY", key, self._artifact(key, kind, coverage))
            for key in sorted(state.weather_keys):
                if retained(key):
                    add(day, "NOAA_NDFD_WEATHER", key, self._artifact(key, "ndfd_object" if "YDUZ98" in key else "complete"))
            meta_keys = [self.gamma_keys.get(state.candidate.market_id), self.audit_key]
            if state.rule is not None:
                meta_keys.append(self.station_keys.get(state.rule.station_id))
            for key in meta_keys:
                if retained(key):
                    add(day, "GAMMA_NWS_RULE_LABEL_METADATA", key,  # type: ignore[arg-type]
                        self._artifact(key, "gamma" if "via=" in key else "complete"))  # type: ignore[arg-type,operator]
            for hour in self.label_hours.get(state.candidate.market_id, []):
                for key in sorted(self.hours.keys_by_hour.get(hour, ())):
                    if retained(key):
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
                break
        if self.budget_exhausted:
            for state in self.markets.values():
                # A market exhausted before its Gamma document was read has no facts to evaluate
                # (S10-QUAL-DATA-01 left it active and crashed building execution facts).
                if (state.excluded is None and not state.history_complete
                        and (state.gamma is None or any(self._row_pending(state, cp) for cp in qd.CHECKPOINT_IDS))):
                    state.excluded = "BUDGET_EXHAUSTED_BEFORE_EVALUATION"
            if self.hours is None:
                self.hours = V3Hours(self.store, self.audit)  # type: ignore[arg-type]
                self.ndfd = d1.NdfdAccess(self.store, self.decode_fn)
        return self.build()


# ── Bundle audit (look-ahead / authority laundering) ──────────────────────────


def audit_bundle(bundle: Mapping[str, object]) -> None:
    """Independent zero-network checks over a sealed bundle; closed ReadinessError on failure."""

    qd.verify_bundle(bundle)
    dataset = bundle["dataset"]  # type: ignore[index]
    if dataset["b0_contract_compatibility"] != qd.B0_EXTERNAL_ONLY:  # type: ignore[index]
        raise qd.ReadinessError("READINESS_AUTHORITY_LAUNDERING")
    for row in bundle["rows"]:  # type: ignore[union-attr]
        checkpoint = qd.parse_utc(row["checkpoint_time"])
        history = row["feature_evidence"]["market_history"]
        weather = row["feature_evidence"]["weather"]
        if history["source_class"] != v3.SOURCE_CLASS or history["source_authority"] != v3.B0_SOURCE_AUTHORITY:
            raise qd.ReadinessError("READINESS_AUTHORITY_LAUNDERING")
        times = [history["best_bid_ask"]["timestamp_received"], weather["public_available_time"]]
        if history.get("last_trade_price") is not None:
            times.append(history["last_trade_price"]["timestamp_received"])
        if any(qd.parse_utc(t) > checkpoint for t in times):
            raise qd.ReadinessError("READINESS_LOOK_AHEAD")
        if row["label_evidence"].get("post_outcome_evidence") is not True:
            raise qd.ReadinessError("READINESS_INPUT_INVALID")
    counts = dataset["counts"]  # type: ignore[index]
    recomputed = qd.derive_counts(
        int(counts["discovered_candidates"]), bundle["rows"], bundle["market_exclusions"],  # type: ignore[arg-type,index]
        bundle["row_exclusions"], bundle["source_facts"]["pendulumflow_bba_coverage_by_hour"],  # type: ignore[arg-type,index]
        [r["feature_evidence"]["weather"]["object_key"] for r in bundle["rows"]])  # type: ignore[index,union-attr]
    qd.verify_counts(counts, recomputed)  # type: ignore[arg-type]


# ── Seed verification (predecessor-code bound) ────────────────────────────────


def _need(condition: object, code: str) -> None:
    if not condition:
        raise SeedInvalid(code)


def verify_seed(path: Path, predecessor_digests: Mapping[str, str]) -> dict[str, object]:
    """Verify one PR #202 run-01 store; return its admitted successful artifacts (never decisions)."""

    try:
        plan = read_json(path / d1.PLAN_FILENAME)
        _need(isinstance(plan, dict), "SEED_PLAN_INVALID")
        plan_sha = sha256_hex(canonical(plan))
        _need(plan_sha == (path / d1.PLAN_HASH_FILENAME).read_text(encoding="utf-8").strip(), "SEED_PLAN_INVALID")
        _need(plan.get("frozen") == d1.frozen_plan_body(), "SEED_PLAN_DRIFT")
        _need(plan.get("code_digests") == dict(predecessor_digests), "SEED_CODE_NOT_PREDECESSOR")
        state = read_json(path / d1.STATE_FILENAME)
        _need(state.get("status") == "FINAL" and state.get("bundle_id") == SEED_BUNDLE_ID, "SEED_NOT_FINAL")
        bundle = read_json(path / d1.BUNDLE_FILENAME)
        try:
            qd.verify_bundle(bundle)
        except qd.ReadinessError:
            raise SeedInvalid("SEED_BUNDLE_INVALID") from None
        _need(bundle["bundle_id"] == SEED_BUNDLE_ID and bundle["logical_dataset_id"] == SEED_DATASET_ID, "SEED_IDENTITY_MISMATCH")
        _need(bundle["terminal"] == SEED_TERMINAL and bundle["terminal_reason"] == SEED_TERMINAL_REASON, "SEED_TERMINAL_MISMATCH")
        report = read_json(path / d1.REPORT_FILENAME)
        _need(report.get("bundle_id") == SEED_BUNDLE_ID and report.get("logical_dataset_id") == SEED_DATASET_ID
              and report.get("plan_sha256") == plan_sha, "SEED_REPORT_MISMATCH")
        verified = read_json(path / d1.VERIFY_FILENAME)
        _need(verified.get("status") == "VERIFIED" and verified.get("network_calls") == 0
              and verified.get("bundle_id") == SEED_BUNDLE_ID and verified.get("logical_dataset_id") == SEED_DATASET_ID
              and verified.get("plan_sha256") == plan_sha, "SEED_NOT_VERIFIED")
        index = read_json(path / d1.INDEX_FILENAME)
        _need(isinstance(index, dict), "SEED_INDEX_INVALID")
        admitted: dict[str, dict[str, object]] = {}
        failed_codes: dict[str, int] = {}
        admitted_bytes = 0
        for key, entry in sorted(index.items()):
            _need(isinstance(entry, dict), "SEED_INDEX_INVALID")
            if "failed" in entry:
                failed_codes[str(entry["failed"])] = failed_codes.get(str(entry["failed"]), 0) + 1
                continue
            _need(set(entry) == set(SEED_ENTRY_FIELDS), "SEED_INDEX_INVALID")
            digest = str(entry["sha256"])
            _need(re.fullmatch(r"[0-9a-f]{64}", digest), "SEED_INDEX_INVALID")
            data = (path / "raw" / digest).read_bytes()
            _need(sha256_hex(data) == digest and len(data) == entry["bytes"], "SEED_ARTIFACT_HASH_INVALID")
            admitted[key] = {name: entry[name] for name in SEED_ENTRY_FIELDS}
            admitted_bytes += len(data)
        _need(len(admitted) == verified.get("rehashed_artifacts"), "SEED_ARTIFACT_COUNT_MISMATCH")
        registry = path / d1.REGISTRY_COPY_FILENAME
        expected_registry = plan["alpha_registry"]
        _need(sha256_hex(registry.read_bytes()) == expected_registry["copy_sha256"], "SEED_REGISTRY_INVALID")
        lineage = d1.verify_alpha_registry(registry)
        _need(lineage["entry_hashes"] == expected_registry["entry_hashes"], "SEED_REGISTRY_INVALID")
    except SeedInvalid:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError, d1.OperatorStop):
        raise SeedInvalid("SEED_UNREADABLE") from None
    return {
        "plan": plan,
        "plan_sha256": plan_sha,
        "admitted": admitted,
        "admitted_bytes": admitted_bytes,
        "index_sha256": sha256_hex(canonical(admitted)),
        "failed_entries_not_admitted": sum(failed_codes.values()),
        "failed_codes_not_admitted": dict(sorted(failed_codes.items())),
        "ledger": read_json(path / d1.LEDGER_FILENAME),
        "rehashed_artifacts_reported": verified["rehashed_artifacts"],
    }


# ── Environment (injectable for hermetic tests) ───────────────────────────────


def _git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise OperatorStop("STATE_DRIFT")
    return completed.stdout


def _git_blob(repo_root: Path, revision: str, path: str) -> bytes:
    completed = subprocess.run(["git", "-C", str(repo_root), "show", f"{revision}:{path}"], capture_output=True, check=False)
    if completed.returncode != 0:
        raise OperatorStop("STATE_DRIFT")
    return completed.stdout


@dataclasses.dataclass
class Environment:
    repo_root: Path = REPO_ROOT
    git: Callable[..., str] | None = None
    git_blob: Callable[[str, str], bytes] | None = None
    fetch: Callable[..., tuple[int, dict[str, str], bytes]] | None = None
    gamma_client_factory: Callable[[], object] | None = None
    decode_fn: Callable[..., ndfd.DecodedPop12] | None = None
    require_decoder: bool = True
    sleep: Callable[[float], None] | None = None

    @property
    def workspace(self) -> Path:
        return self.repo_root.joinpath(*WORKSPACE_PARTS)

    def run_git(self, *args: str) -> str:
        return (self.git or (lambda *a: _git(self.repo_root, *a)))(*args)

    def blob(self, revision: str, path: str) -> bytes:
        return (self.git_blob or (lambda r, p: _git_blob(self.repo_root, r, p)))(revision, path)

    def sleeper(self) -> Callable[[float], None]:
        return self.sleep or time.sleep

    def decoder(self) -> Callable[..., ndfd.DecodedPop12]:
        if self.decode_fn is not None:
            return self.decode_fn
        if self.require_decoder:
            try:
                ndfd.require_decoder(True)
            except ndfd.NdfdError:
                raise OperatorStop("DECODER_UNAVAILABLE") from None
        return ndfd.decode_pop12_message


def code_digests(repo_root: Path) -> dict[str, str]:
    return {path: sha256_hex((repo_root / path).read_bytes().replace(b"\r\n", b"\n")) for path in CODE_FILES}


def predecessor_code_digests(env: Environment) -> dict[str, str]:
    return {path: sha256_hex(env.blob(PREDECESSOR_HEAD, path).replace(b"\r\n", b"\n")) for path in PREDECESSOR_CODE_FILES}


def discover_seed(env: Environment, predecessor_digests: Mapping[str, str]) -> tuple[Path, dict[str, object], int]:
    """Discover the PR #202 seed only beneath git worktree roots. Byte-identical valid copies may
    exist; two valid stores that disagree are a conflict; none valid is missing evidence."""

    valid: list[tuple[Path, dict[str, object]]] = []
    for root in sorted(set(d1.worktree_roots(env)), key=lambda p: str(p)):  # type: ignore[arg-type]
        candidate = root.joinpath(*SEED_PARTS)
        if not (candidate / d1.PLAN_FILENAME).is_file():
            continue
        try:
            valid.append((candidate, verify_seed(candidate, predecessor_digests)))
        except SeedInvalid:
            continue
    if not valid:
        raise OperatorStop("SEED_EVIDENCE_MISSING")
    if len({(item["index_sha256"], item["plan_sha256"]) for _path, item in valid}) != 1:
        raise OperatorStop("SEED_EVIDENCE_CONFLICT")
    return valid[0][0], valid[0][1], len(valid)


def frozen_plan_body() -> dict[str, object]:
    semantics = {k: v for k, v in d1.frozen_plan_body().items() if k not in ("wp_id", "base_sha", "predecessor", "budgets")}
    return {
        "wp_id": WP_ID,
        "base_sha": BASE_SHA,
        "predecessor": {"pr": PREDECESSOR_PR, "head": PREDECESSOR_HEAD, "merge": BASE_SHA},
        "frozen_semantics_unchanged_from": d1.WP_ID,
        **semantics,
        "finality_policies": list(qd.FINALITY_POLICIES),
        "b0_rule": qd.B0_EXTERNAL_ONLY + " unless genuine canonical PIT is independently bound",
        "seed": {"bundle_id": SEED_BUNDLE_ID, "logical_dataset_id": SEED_DATASET_ID, "terminal": SEED_TERMINAL,
                 "terminal_reason": SEED_TERMINAL_REASON,
                 "admission": "successful hash-valid raw artifacts + their source metadata only; failed entries, rows, exclusions, bundle, manifests and decisions never seeded"},
        "d011": {
            "best_bid_ask": "failed hour is not scanned; pair walking through it is MARKET_HISTORY_SOURCE_INVALID; walk stops",
            "last_trade_price": "failed hour not listed as searched; failure recorded; never implies absence",
            "market_resolved": "any failed required read -> LABEL_V3_SOURCE_READ_FAILED; LABEL_V3_RESOLUTION_MISSING only after all reads succeeded",
            "tick_size_change": "failed hour recorded as not searched; CURRENT_ONLY only on independent current Gamma metadata",
            "stages": list(READ_STAGES),
        },
        "retry_policy": {
            "throttle_statuses": sorted(THROTTLE_STATUSES), "throttle_max_retries": MAX_THROTTLE_RETRIES,
            "throttle_delays_seconds": list(THROTTLE_DELAYS_SECONDS), "retry_after_max_seconds": RETRY_AFTER_MAX_SECONDS,
            "retry_after_rule": "integer Retry-After in [0,60] -> max(frozen delay, Retry-After); otherwise frozen delay",
            "transport_max_retries": MAX_TRANSPORT_RETRIES, "jitter": False, "adaptive": False,
        },
        "allowlist": sorted(ALLOWED_HOSTS),
        "methods": sorted(ALLOWED_METHODS),
        "budgets": {
            "network_attempts": MAX_NETWORK_ATTEMPTS, "response_bytes": MAX_RESPONSE_BYTES,
            "single_response_bytes": MAX_SINGLE_RESPONSE, "distinct_pendulum_hours": MAX_DISTINCT_PENDULUM_HOURS,
            "target_dates": d1.MAX_TARGET_DATES, "candidates": d1.MAX_CANDIDATES, "stations": d1.MAX_STATIONS,
            "seed_bytes_consume_caps": False, "probe_traffic_counts_against_caps": True,
        },
    }


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


def load_seed_index(env: Environment, plan: Mapping[str, object]) -> dict[str, dict[str, object]]:
    try:
        index = read_json(env.workspace / SEED_INDEX_FILENAME)
    except (OSError, ValueError):
        raise OperatorStop("PLAN_INVALID") from None
    if not isinstance(index, dict) or sha256_hex(canonical(index)) != plan["seed"]["index_sha256"]:  # type: ignore[index]
        raise OperatorStop("PLAN_INVALID")
    return index  # type: ignore[return-value]


def command_prepare(env: Environment) -> dict[str, object]:
    head = env.run_git("rev-parse", "HEAD").strip()
    branch = env.run_git("rev-parse", "--abbrev-ref", "HEAD").strip()
    dirty = env.run_git("status", "--porcelain", "--untracked-files=normal").strip()
    for ancestor in (BASE_SHA, PREDECESSOR_HEAD):
        env.run_git("merge-base", "--is-ancestor", ancestor, "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", head) or branch != PINNED_BRANCH or dirty:
        raise OperatorStop("STATE_DRIFT")
    predecessor_digests = predecessor_code_digests(env)
    source, seed, copies = discover_seed(env, predecessor_digests)
    try:
        af1 = d1.verify_af1(env.repo_root)
    except d1.OperatorStop:
        raise OperatorStop("AF1_EVIDENCE_DRIFT") from None
    seed_plan = seed["plan"]
    plan = {
        "schema_id": "s10-qual-data-02-run-plan",
        "schema_version": "1.0.0",
        "frozen": frozen_plan_body(),
        "repo_code_identity": head,
        "code_digests": code_digests(env.repo_root),
        "predecessor_code_digests": dict(predecessor_digests),
        "seed": {
            "plan_sha256": seed["plan_sha256"],
            "index_sha256": seed["index_sha256"],
            "admitted_artifacts": len(seed["admitted"]),  # type: ignore[arg-type]
            "admitted_bytes": seed["admitted_bytes"],
            "failed_entries_admitted": 0,
            "failed_entries_not_admitted": seed["failed_entries_not_admitted"],
            "verified_copies_found": copies,
        },
        "alpha_registry": seed_plan["alpha_registry"],  # type: ignore[index]
        "af1": af1,
    }
    workspace = env.workspace
    plan_path = workspace / PLAN_FILENAME
    if plan_path.exists():
        if read_json(plan_path) != plan:
            raise OperatorStop("PREPARE_WORKSPACE_CONFLICT")
        return {"status": "PREPARED_IDEMPOTENT", "plan_sha256": sha256_hex(canonical(plan))}
    if workspace.exists() and any(workspace.iterdir()):
        raise OperatorStop("PREPARE_WORKSPACE_CONFLICT")
    seed_raw = workspace / SEED_RAW_DIRNAME
    seed_raw.mkdir(parents=True, exist_ok=True)
    admitted: dict[str, dict[str, object]] = seed["admitted"]  # type: ignore[assignment]
    for digest in sorted({str(entry["sha256"]) for entry in admitted.values()}):
        target = seed_raw / digest
        shutil.copyfile(source / "raw" / digest, target)
        if sha256_hex(target.read_bytes()) != digest:
            raise OperatorStop("SEED_EVIDENCE_MISSING")
    registry = workspace / REGISTRY_COPY_FILENAME
    shutil.copyfile(source / d1.REGISTRY_COPY_FILENAME, registry)
    try:
        lineage = d1.verify_alpha_registry(registry)
    except Exception:
        raise OperatorStop("ALPHA_LINEAGE_EVIDENCE_MISSING") from None
    if (sha256_hex(registry.read_bytes()) != plan["alpha_registry"]["copy_sha256"]  # type: ignore[index]
            or lineage["entry_hashes"] != plan["alpha_registry"]["entry_hashes"]):  # type: ignore[index]
        raise OperatorStop("ALPHA_LINEAGE_CONFLICT")
    write_json_atomic(workspace / SEED_INDEX_FILENAME, admitted)
    seed_ledger = seed["ledger"]
    write_json_atomic(workspace / SEED_REPORT_FILENAME, {
        "wp_id": WP_ID,
        "predecessor": {"pr": PREDECESSOR_PR, "head": PREDECESSOR_HEAD, "bundle_id": SEED_BUNDLE_ID,
                        "logical_dataset_id": SEED_DATASET_ID, "terminal": SEED_TERMINAL,
                        "terminal_reason": SEED_TERMINAL_REASON, "plan_sha256": seed["plan_sha256"],
                        "code_digests_bound_to_predecessor_head": True, "verify_final": "VERIFIED",
                        "rehashed_artifacts_reported": seed["rehashed_artifacts_reported"]},
        "admitted_artifacts": len(admitted),
        "admitted_bytes": seed["admitted_bytes"],
        "failed_entries_admitted": 0,
        "failed_entries_not_admitted": seed["failed_entries_not_admitted"],
        "failed_codes_not_admitted": seed["failed_codes_not_admitted"],
        "predecessor_network": {"attempts": seed_ledger.get("attempts"), "bytes": seed_ledger.get("bytes")},  # type: ignore[union-attr]
        "seed_index_sha256": seed["index_sha256"],
        "verified_copies_found": copies,
        "seeded": "successful raw artifacts + source metadata only",
        "never_seeded": ["rows", "exclusions", "bundle", "ready manifests", "scanned-hour decisions",
                         "label classifications", "execution-evidence decisions"],
    })
    write_json_atomic(plan_path, plan)
    (workspace / PLAN_HASH_FILENAME).write_text(sha256_hex(canonical(plan)) + "\n", encoding="utf-8")
    write_json_atomic(workspace / STATE_FILENAME, {"status": "PREPARED"})
    return {"status": "PREPARED", "plan_sha256": sha256_hex(canonical(plan))}


def _seeded_store(env: Environment, root: Path, ledger: Ledger | None, plan: Mapping[str, object], *,
                  replay: bool = False) -> ArtifactStore:
    transport = None if replay else BoundedTransport(ledger, env.fetch, env.sleeper())  # type: ignore[arg-type]
    return ArtifactStore(root, transport, None if replay else (env.gamma_client_factory or d1.default_gamma_client_factory),
                         replay=replay, seed_index=load_seed_index(env, plan), seed_raw=env.workspace / SEED_RAW_DIRNAME,
                         sleep=env.sleeper())


def d011_self_check(root: Path) -> dict[str, str]:
    """Zero-network typed-failure proof on the real operator path: a failed manifest read of a
    ``market_resolved`` hour is a typed MANIFEST failure (never empty) and classifies the label as
    LABEL_V3_SOURCE_READ_FAILED; the same code survives the closed vocabulary."""

    hour = PROBE_MARKET_HOUR
    store = ArtifactStore(root, None, replay=True)
    store.index[ArtifactStore.key("GET", d1.pf_url(v3.manifest_object_path(hour)))] = {"failed": "HTTP_503"}
    hours = V3Hours(store, None)
    try:
        hours.read("probe", hour, "market_resolved")
    except SourceReadFailed as failure:
        typed = f"{failure.stage}:{failure.code}"
    else:
        raise OperatorStop("SOURCE_CONTRACT_DRIFT")
    gamma = qd.GammaFacts("0", "0x" + "00" * 32, (("No", "2"), ("Yes", "1")), None, None, "Yes", "", "", None, None, None, None, None)
    label = missing = "NONE"
    try:
        label_outcome(gamma, [], read_failed=True)
    except qd.RuleExclusion as exclusion:
        label = exclusion.code
    try:
        label_outcome(gamma, [], read_failed=False)
    except qd.RuleExclusion as exclusion:
        missing = exclusion.code
    if (typed, label, missing) != ("MANIFEST:HTTP_503", "LABEL_V3_SOURCE_READ_FAILED", "LABEL_V3_RESOLUTION_MISSING"):
        raise OperatorStop("SOURCE_CONTRACT_DRIFT")
    return {"read": typed, "failed_read_label": label, "successful_empty_read_label": missing}


def command_probe(env: Environment) -> dict[str, object]:
    plan = load_plan(env)
    decode = env.decoder()
    probe_root = env.workspace / "probe"
    ledger = Ledger()
    store = _seeded_store(env, probe_root, ledger, plan)
    live = ArtifactStore(probe_root / "live", store.transport, env.gamma_client_factory or d1.default_gamma_client_factory,
                         sleep=env.sleeper())
    checks: dict[str, object] = {}
    status = "PROBE_PASS"
    failure_code = None
    try:
        hours = V3Hours(store, None)
        events = hours.read("probe", PROBE_HOUR, "new_market")
        if ledger.attempts != 0 or not all(store.index[k].get("origin") == "SEED" for k in hours.keys_by_hour[PROBE_HOUR]):
            raise OperatorStop("SOURCE_CONTRACT_DRIFT")
        checks["seed_cache_hit"] = "PASS"
        candidates, _bad = qd.candidates_from_new_market(
            [e for e in events if (e.field("slug") or "").startswith("where-will-it-rain-on-")])
        seeded_ids = [c for c in candidates if ArtifactStore.key("GET", f"https://{GAMMA_HOST}/markets/{c.market_id}")
                      + " via=PolymarketPublicClient.get_market" in store.seed_index]
        if not seeded_ids:
            raise OperatorStop("SOURCE_CONTRACT_DRIFT")
        candidate = seeded_ids[0]
        seeded = qd.normalize_gamma_market(store.gamma_market(candidate.market_id, None), candidate)
        current = qd.normalize_gamma_market(live.gamma_market(candidate.market_id, ledger, use_seed=False), candidate)
        if (current.market_id, current.condition_id, current.token_by_outcome) != (seeded.market_id, seeded.condition_id, seeded.token_by_outcome):
            raise OperatorStop("SOURCE_CONTRACT_DRIFT")
        checks["gamma_by_id_identity"] = "PASS"
        checks["rule_semantics"] = qd.parse_rule(current.description).finality_policy
        url = d1.pf_url(v3.manifest_object_path(PROBE_MARKET_HOUR))
        seed_entry = store.seed_index.get(ArtifactStore.key("GET", url))
        if seed_entry is None:
            raise OperatorStop("SOURCE_CONTRACT_DRIFT")
        fresh = live.get(url, accept="application/json", media_type="application/json", use_seed=False)
        if sha256_hex(fresh) != seed_entry["sha256"]:
            raise OperatorStop("SOURCE_CONTRACT_DRIFT")  # the archive changed under the seed
        checks["unseeded_fetch_matches_seed"] = "PASS"
        checks["d011_typed_failure"] = d011_self_check(probe_root / "d011")
        receive = qd.parse_utc(candidate.first_received)
        checkpoint = qd.checkpoint_a(receive, qd.gamma_open_time_if_trustworthy(seeded.open_time, receive))
        access = d1.NdfdAccess(store, decode)
        objects = [o for d in sorted({checkpoint.date(), (checkpoint - timedelta(days=1)).date()}) for o in access.listing(d)]
        vintage = ndfd.select_vintage(objects, checkpoint, qd.NDFD_VINTAGE_LOOKBACK)
        if vintage is None:
            raise OperatorStop("SOURCE_CONTRACT_DRIFT")
        data = access.object_bytes(vintage)
        station = ndfd.parse_nws_station(json.loads(store.get(
            f"https://{NWS_HOST}/stations/{qd.parse_rule(seeded.description).station_id}",
            accept="application/geo+json", media_type="application/geo+json").decode("utf-8")),
            qd.parse_rule(seeded.description).station_id)
        slices = ndfd.scan_messages(data)
        decoded = decode(ndfd.message_bytes(data, slices[0]), [station])
        checks["ndfd_production_decode"] = "PASS"
        checks["ndfd_probe_value_present"] = decoded.station_values[0].pop12_percent is not None
    except OperatorStop as stop:
        status = failure_code = stop.code
    except (TransportFailure, TransportRefused, BudgetExhausted, ReplayMissing, v3.PendulumFlowError, ndfd.NdfdError,
            qd.ReadinessError, qd.RuleExclusion, SourceReadFailed, d1.OperatorStop) as error:
        status = "SOURCE_CONTRACT_DRIFT"
        failure_code = str(getattr(error, "code", "SOURCE_CONTRACT_DRIFT"))
    except ValueError:
        status, failure_code = "SOURCE_CONTRACT_DRIFT", "VALUE_INVALID"
    result: dict[str, object] = {"status": status, "checks": checks, "ledger": ledger.to_mapping(),
                                 "plan_sha256": sha256_hex(canonical(plan))}
    if status != "PROBE_PASS":
        result["failed_step"] = next((step for step in PROBE_STEPS if step not in checks), "UNKNOWN")
        result["failure_code"] = failure_code
    write_json_atomic(env.workspace / PROBE_FILENAME, result)
    if status != "PROBE_PASS":
        raise OperatorStop("SOURCE_CONTRACT_DRIFT")
    return result


def seed_usage(index: Mapping[str, Mapping[str, object]]) -> dict[str, int]:
    seeded = [e for e in index.values() if e.get("origin") == "SEED"]
    fresh = [e for e in index.values() if "failed" not in e and e.get("origin") != "SEED"]
    return {
        "seed_artifacts_reused": len(seeded),
        "seed_bytes_reused": sum(int(e["bytes"]) for e in seeded),  # type: ignore[arg-type]
        "new_artifacts_retained": len(fresh),
        "new_bytes_retained": sum(int(e["bytes"]) for e in fresh),  # type: ignore[arg-type]
        "failed_entries": sum(1 for e in index.values() if "failed" in e),
        "evidence_bytes_including_seed": sum(int(e["bytes"]) for e in index.values() if "failed" not in e),  # type: ignore[arg-type]
    }


def command_run(env: Environment) -> dict[str, object]:
    plan = load_plan(env)
    state_path = env.workspace / STATE_FILENAME
    state = read_json(state_path) if state_path.exists() else {}
    if isinstance(state, dict) and state.get("status") == "FINAL":
        raise OperatorStop("RUN_ALREADY_FINALIZED")
    probe_path = env.workspace / PROBE_FILENAME
    probe = read_json(probe_path) if probe_path.exists() else {}
    if not isinstance(probe, dict) or probe.get("status") != "PROBE_PASS":
        raise OperatorStop("PROBE_REQUIRED")
    try:
        d1._verify_registry_copy(env, plan)  # type: ignore[arg-type]  # noqa: SLF001
        d1.verify_af1(env.repo_root)
    except d1.OperatorStop as stop:
        raise OperatorStop(stop.code) from None
    decode = env.decoder()
    ledger_path = env.workspace / LEDGER_FILENAME
    probe_ledger = probe["ledger"]
    ledger = (Ledger.from_mapping(read_json(ledger_path)) if ledger_path.exists()  # type: ignore[arg-type]
              else Ledger(baseline_attempts=int(probe_ledger["attempts"]), baseline_bytes=int(probe_ledger["bytes"])))
    resumed = bool(state.get("status") == "RUNNING") if isinstance(state, dict) else False
    write_json_atomic(state_path, {"status": "RUNNING", "resumed": resumed})
    store = _seeded_store(env, env.workspace, ledger, plan)
    try:
        pipeline = CompletionPipeline(store, plan, decode, ledger)
        bundle, manifests = pipeline.run()
    finally:
        write_json_atomic(ledger_path, ledger.to_mapping())
    audit_bundle(bundle)
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
        "probe_ledger": probe_ledger,
        "new_network_attempts_total": ledger.total_attempts(),
        "new_network_bytes_total": ledger.total_bytes(),
        "budget_exhausted": pipeline.budget_exhausted,
        "seed": seed_usage(store.index) | {"seed_artifacts_admitted": plan["seed"]["admitted_artifacts"],  # type: ignore[index]
                                           "seed_bytes_admitted": plan["seed"]["admitted_bytes"]},  # type: ignore[index]
        "resumed": resumed,
        "python": platform.python_version(),
        "platform": platform.system(),
        "retained_artifacts": len(store.index),
        "completed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    write_json_atomic(env.workspace / REPORT_FILENAME, report)
    write_json_atomic(state_path, {"status": "FINAL", "terminal": bundle["terminal"], "bundle_id": bundle["bundle_id"]})
    return report


def verify_network_accounting(ledger: Mapping[str, object], report: Mapping[str, object]) -> None:
    probe = report["probe_ledger"]
    for item in (ledger, probe):
        if (item["attempts"] != sum(item["attempts_by_host"].values())  # type: ignore[index,union-attr]
                or item["bytes"] != sum(item["bytes_by_host"].values())  # type: ignore[index,union-attr]
                or item["attempts"] != sum(item["statuses"].values())  # type: ignore[index,union-attr]
                or set(item["attempts_by_host"]) - ALLOWED_HOSTS  # type: ignore[index,arg-type]
                or item["max_single_response"] > MAX_SINGLE_RESPONSE):  # type: ignore[index,operator]
            raise OperatorStop("VERIFY_FAILED")
    if (dict(ledger) != report["network_ledger"]
            or ledger["baseline_attempts"] != probe["attempts"] or ledger["baseline_bytes"] != probe["bytes"]  # type: ignore[index]
            or report["new_network_attempts_total"] != ledger["attempts"] + probe["attempts"]  # type: ignore[index,operator]
            or report["new_network_bytes_total"] != ledger["bytes"] + probe["bytes"]  # type: ignore[index,operator]
            or report["new_network_attempts_total"] > MAX_NETWORK_ATTEMPTS  # type: ignore[operator]
            or report["new_network_bytes_total"] > MAX_RESPONSE_BYTES + MAX_SINGLE_RESPONSE):  # type: ignore[operator]
        raise OperatorStop("VERIFY_FAILED")


def command_verify(env: Environment) -> dict[str, object]:
    restore = d1._forbid_network()  # noqa: SLF001
    try:
        plan = load_plan(env)
        state = read_json(env.workspace / STATE_FILENAME) if (env.workspace / STATE_FILENAME).exists() else {}
        if not isinstance(state, dict) or state.get("status") != "FINAL":
            raise OperatorStop("RUN_NOT_FINAL")
        try:
            d1._verify_registry_copy(env, plan)  # type: ignore[arg-type]  # noqa: SLF001
            af1 = d1.verify_af1(env.repo_root)
        except d1.OperatorStop as stop:
            raise OperatorStop(stop.code) from None
        decode = env.decoder()
        store = _seeded_store(env, env.workspace, None, plan, replay=True)
        seed_index = store.seed_index
        if (any("failed" in entry or set(entry) != set(SEED_ENTRY_FIELDS) for entry in seed_index.values())
                or len(seed_index) != plan["seed"]["admitted_artifacts"]):  # type: ignore[index]
            raise OperatorStop("VERIFY_FAILED")
        seed_rehashed = 0
        for digest in sorted({str(e["sha256"]) for e in seed_index.values()}):
            data = (env.workspace / SEED_RAW_DIRNAME / digest).read_bytes()
            if sha256_hex(data) != digest:
                raise OperatorStop("VERIFY_FAILED")
            seed_rehashed += 1
        if sum(int(e["bytes"]) for e in seed_index.values()) != plan["seed"]["admitted_bytes"]:  # type: ignore[index,arg-type]
            raise OperatorStop("VERIFY_FAILED")
        rehashed = 0
        for key, entry in sorted(store.index.items()):
            if "failed" in entry:
                continue
            if entry.get("origin") == "SEED":
                seeded = seed_index.get(key)
                if seeded is None or {k: entry[k] for k in SEED_ENTRY_FIELDS} != seeded:
                    raise OperatorStop("VERIFY_FAILED")
            store._read_verified(str(entry["sha256"]))  # noqa: SLF001
            rehashed += 1
        stored = read_json(env.workspace / BUNDLE_FILENAME)
        try:
            audit_bundle(stored)  # type: ignore[arg-type]
        except qd.ReadinessError:
            raise OperatorStop("VERIFY_FAILED") from None
        pipeline = CompletionPipeline(store, plan, decode, None)
        if stored.get("terminal_reason") == "FROZEN_BUDGET_EXHAUSTED":  # type: ignore[union-attr]
            original_get, original_gamma = store.get, store.gamma_market

            def get_or_exhaust(*args, **kwargs):
                try:
                    return original_get(*args, **kwargs)
                except ReplayMissing:
                    raise BudgetExhausted("REPLAYED_BUDGET_EXHAUSTION") from None

            def gamma_or_exhaust(*args, **kwargs):
                try:
                    return original_gamma(*args, **kwargs)
                except ReplayMissing:
                    raise BudgetExhausted("REPLAYED_BUDGET_EXHAUSTION") from None

            store.get = get_or_exhaust  # type: ignore[method-assign]
            store.gamma_market = gamma_or_exhaust  # type: ignore[method-assign]
        try:
            rebuilt, manifests = pipeline.run()
        except (ReplayMissing, d1._NetworkForbidden):  # noqa: SLF001
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
        report = read_json(env.workspace / REPORT_FILENAME)
        ledger = read_json(env.workspace / LEDGER_FILENAME)
        verify_network_accounting(ledger, report)  # type: ignore[arg-type]
        usage = seed_usage(store.index)
        if any(report["seed"][k] != v for k, v in usage.items()):  # type: ignore[index]
            raise OperatorStop("VERIFY_FAILED")
        if (report["bundle_id"], report["logical_dataset_id"]) != (rebuilt["bundle_id"], rebuilt["logical_dataset_id"]):  # type: ignore[index]
            raise OperatorStop("VERIFY_FAILED")
        result = {
            "status": "VERIFIED",
            "network_calls": 0,
            "plan_sha256": sha256_hex(canonical(plan)),
            "rehashed_artifacts": rehashed,
            "seed_artifacts_rehashed": seed_rehashed,
            "failed_seed_entries_admitted": 0,
            "bundle_id": rebuilt["bundle_id"],
            "logical_dataset_id": rebuilt["logical_dataset_id"],
            "terminal": rebuilt["terminal"],
            "terminal_reason": rebuilt["terminal_reason"],
            "b0_contract_compatibility": rebuilt["dataset"]["b0_contract_compatibility"],  # type: ignore[index]
            "ready_manifests": len(rebuilt["dataset"]["ready_manifest_ids"]),  # type: ignore[index]
            "seed": usage,
            "new_network_attempts_total": report["new_network_attempts_total"],  # type: ignore[index]
            "new_network_bytes_total": report["new_network_bytes_total"],  # type: ignore[index]
            "af1_receipt_id": af1["gate_receipt_id"],
            "alpha_registry_head": plan["alpha_registry"]["head_entry_hash"],  # type: ignore[index]
        }
        write_json_atomic(env.workspace / VERIFY_FILENAME, result)
        return result
    except OSError:
        raise OperatorStop("VERIFY_FAILED") from None
    finally:
        restore()


COMMANDS = {
    "prepare": command_prepare,
    "probe-sources": command_probe,
    "run-completion": command_run,
    "verify-final": command_verify,
}


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> "None":  # type: ignore[override]
        raise OperatorStop("USAGE_ERROR")


def main(argv: Sequence[str] | None = None, env: Environment | None = None) -> int:
    parser = _Parser(prog="run_s10_qual_data_02.py", add_help=False)
    parser.add_argument("command", choices=sorted(COMMANDS))
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
        result = COMMANDS[args.command](env or Environment())
    except (OperatorStop, d1.OperatorStop) as stop:
        print(f"STOP {stop.code}")
        return 2 if stop.code == "USAGE_ERROR" else 3
    summary = {k: result[k] for k in ("status", "terminal", "terminal_reason", "bundle_id", "logical_dataset_id", "plan_sha256") if k in result}
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
