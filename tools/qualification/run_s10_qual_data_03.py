"""Manual foreground operator for S10-QUAL-DATA-03 (prospective weather qualification OOS accrual).

Frozen package: ``docs/wp_specs/S10-QUAL-DATA-03/`` and
``docs/qualification_weather_oos_accrual_contract.md``; frozen analytic plan: S10-QUAL-PLAN-01
(plan SHA-256 ``3b2a99ab...a9463``, merged at ``75e17927...`` on 2026-10-01T02:39:26Z).

This is the ONLY network owner of S10-QUAL-DATA-03. It composes (never subclasses the
completion pipeline of) the unchanged S10-QUAL-DATA-01/02 operators: the DATA-02 bounded
transport and 429/503 retry policy, its typed per-hour PendulumFlow reads and its Gamma-by-id
path through the existing verified ``PolymarketPublicClient.get_market``; the DATA-01 NDFD object
access and provenance descriptors; and the pure ``qualification_oos_accrual`` module.

Exact command grammar (always run from the repository root; manual only, never scheduled):

  prepare        zero network: PLAN-01 / merge / freeze / DATA-02 identity binding, exact N2,
                 the N2 + 150 <= 256 provenance pre-gate, then the accrual-01 workspace
  probe-sources  ONE bounded pre-OOS source-contract probe (no OOS member, label or dataset)
  accrue         one manual bounded accrual run; refused before 2026-10-15T00:00:00Z
  seal           zero network, one-way: the OOS membership seal or the terminal insufficiency
  verify-final   zero network (sockets forbidden): replay every committed run from retained
                 evidence; ledger, sealed store, manifests, membership and reports must match

Network: https GET / Range GET only to archive.pendulumflow.com, noaa-ndfd-pds.s3.amazonaws.com,
gamma-api.polymarket.com (existing public client only), api.weather.gov and the exact frozen fee
page on help.polymarket.com; no redirect, credential, WebSocket, POST, CLOB/order endpoint or
browser automation. Console output is a closed visible report or ``STOP <CODE>`` only.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.analytical_research import nws_ndfd_history as ndfd  # noqa: E402
from src.data_layer.analytical_research import pendulumflow_v3 as v3  # noqa: E402
from src.data_layer.analytical_research import qualification_data_readiness as qd  # noqa: E402
from src.data_layer.analytical_research import qualification_oos_accrual as oa  # noqa: E402
from src.data_layer.analytical_research.external_dataset import (  # noqa: E402
    ExternalSourceObject,
    build_external_dataset_descriptor,
)
from tools.qualification import run_s10_qual_data_01 as d1  # noqa: E402
from tools.qualification import run_s10_qual_data_02 as d2  # noqa: E402

# ── Frozen package identity ───────────────────────────────────────────────────

WP_ID = oa.WP_ID
BASE_SHA = oa.PLAN_MERGE_SHA
PREDECESSOR_PR = 205
IMPORTER_ID = "s10-qual-data-03-operator"
CODE_FILES = (
    "src/data_layer/analytical_research/pendulumflow_v3.py",
    "src/data_layer/analytical_research/nws_ndfd_history.py",
    "src/data_layer/analytical_research/qualification_data_readiness.py",
    "src/data_layer/analytical_research/qualification_oos_accrual.py",
    "tools/qualification/run_s10_qual_data_01.py",
    "tools/qualification/run_s10_qual_data_02.py",
    "tools/qualification/run_s10_qual_data_03.py",
)

DATA02_BUNDLE_ID = oa.DATA02_BUNDLE_ID
DATA02_DATASET_ID = oa.DATA02_DATASET_ID

WORKSPACE_PARTS = ("local_data", "s10_qual_data_03", "accrual-01")
PROBE_PARTS = ("local_data", "s10_qual_data_03", "probe-01")
DATA02_PARTS = ("local_data", "s10_qual_data_02", "run-01")
PLAN_FILENAME = "PLAN.json"
PLAN_HASH_FILENAME = "PLAN.sha256"
PREPARE_REPORT_FILENAME = "PREPARE_REPORT.json"
STATE_FILENAME = "STATE.json"
INDEX_FILENAME = "INDEX.jsonl"
LEDGER_FILENAME = "CLASSIFICATION_LEDGER.jsonl"
RUNS_DIRNAME = "runs"
SEALED_DIRNAME = "sealed"
SEALED_RECORDS_FILENAME = "SEALED_RECORDS.jsonl"
SEAL_FILENAME = "SEAL.json"
SEAL_REPORT_FILENAME = "SEAL_REPORT.json"
VERIFY_FILENAME = "VERIFY_FINAL.json"
RUN_FILENAME = "RUN.json"
RUN_NETWORK_FILENAME = "NETWORK.json"
RUN_REPORT_FILENAME = "VISIBLE_REPORT.json"
PROBE_FILENAME = "PROBE_RESULT.json"

# ── Network allowlist, frozen caps ────────────────────────────────────────────

PENDULUMFLOW_HOST = d1.PENDULUMFLOW_HOST
NDFD_HOST = d1.NDFD_HOST
GAMMA_HOST = d1.GAMMA_HOST
NWS_HOST = d1.NWS_HOST
FEE_HOST = oa.FEE_DOC_HOST
FEE_URL = oa.FEE_DOC_URL
ALLOWED_HOSTS = frozenset(d1.ALLOWED_HOSTS | {FEE_HOST})
USER_AGENT = "polymarket-strategy-lab/S10-QUAL-DATA-03 (public read-only research; toobigtofailbot-maker)"

RUN_MAX_ATTEMPTS = 12_288
RUN_MAX_BYTES = 6_442_450_944
MAX_SINGLE_RESPONSE = 268_435_456
RUN_MAX_PENDULUM_HOURS = 2_000
CUM_MAX_ATTEMPTS = 65_536
CUM_MAX_BYTES = 34_359_738_368
CUM_MAX_PENDULUM_HOURS = 6_000
MAX_ACCRUE_RUNS = 64
MAX_CANDIDATES = 4_096
MAX_STATIONS = 128
PROBE_MAX_ATTEMPTS = 32
PROBE_MAX_BYTES = 16 * 1024 * 1024
PROBE_MAX_SINGLE_RESPONSE = 8 * 1024 * 1024
PROBE_MAX_PENDULUM_HOURS = 4
PROBE_HOUR = "2026-09-28/11"
PROBE_MARKET_HOUR = "2026-09-28/12"
FEE_MAX_BYTES = 8 * 1024 * 1024

HARD_STOPS = (
    "PLAN_FREEZE_INVALID",
    "STATE_DRIFT",
    "SOURCE_CONTRACT_DRIFT",
    "EXECUTION_TERMS_SOURCE_UNAVAILABLE",
    "PROVENANCE_CEILING_UNREACHABLE",
    "QUAL_PROVENANCE_LIMIT_EXCEEDED_UNAVOIDABLE",
    "MEMBERSHIP_REPRODUCTION_FAILED",
    "DEPENDENCY_EXPANSION_REQUIRED",
    "WORKFLOW_EXPANSION_REQUIRED",
    "SCOPE_EXPANSION_REQUIRED",
    "AUTHORITY_EXPANSION_REQUIRED",
    "ACCRUAL_BUDGET_EXHAUSTED",
    "CODE_DRIFT_AFTER_PROSPECTIVE_ACCRUAL",
)
STOP_CODES = HARD_STOPS + (
    "USAGE_ERROR",
    "PLAN_MISSING",
    "PLAN_INVALID",
    "DATA02_EVIDENCE_MISSING",
    "PREPARE_WORKSPACE_CONFLICT",
    "ACCRUAL_BEFORE_OOS_START",
    "ACCRUAL_FINALIZED",
    "NO_COMMITTED_RUN",
    "NOT_SEALABLE",
    "PROBE_ALREADY_RECORDED",
    "PROBE_AFTER_OOS_START",
    "DECODER_UNAVAILABLE",
    "VERIFY_FAILED",
    "VISIBLE_SCHEMA_VIOLATION",
)

TransportFailure = d1.TransportFailure
TransportRefused = d1.TransportRefused
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


def _jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, ValueError):
        raise OperatorStop("STATE_DRIFT") from None


def _write_jsonl_atomic(path: Path, records: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(b"".join(canonical(dict(r)) + b"\n" for r in records))
    os.replace(tmp, path)


# ── Ledger with per-run, cumulative and probe caps (DATA-02 transport unchanged) ──


@dataclasses.dataclass
class AccrualLedger(d2.Ledger):
    """The DATA-02 network ledger plus the DATA-03 caps. Exhausting a per-run cap raises
    ``RUN_*`` (the run ends ACCRUAL_INCOMPLETE); exhausting a cumulative cap raises
    ``CUMULATIVE_*`` (hard stop ACCRUAL_BUDGET_EXHAUSTED); the probe has its own small caps."""

    max_attempts: int = RUN_MAX_ATTEMPTS
    max_bytes: int = RUN_MAX_BYTES
    max_single: int = MAX_SINGLE_RESPONSE
    prior_attempts: int = 0
    prior_bytes: int = 0
    scope: str = "RUN"

    def check_attempt(self, expected_bytes: int | None) -> None:
        if self.scope == "RUN" and self.prior_attempts + self.attempts + 1 > CUM_MAX_ATTEMPTS:
            self.exhausted = "CUMULATIVE_ATTEMPT_BUDGET_EXHAUSTED"
            raise BudgetExhausted(self.exhausted)
        if self.attempts + 1 > self.max_attempts:
            self.exhausted = f"{self.scope}_ATTEMPT_BUDGET_EXHAUSTED"
            raise BudgetExhausted(self.exhausted)
        if expected_bytes is not None:
            if expected_bytes > self.max_single:
                self.exhausted = f"{self.scope}_SINGLE_RESPONSE_CAP"
                raise BudgetExhausted(self.exhausted)
            self._check_total(self.bytes + expected_bytes)

    def _check_total(self, total: int) -> None:
        if self.scope == "RUN" and self.prior_bytes + total > CUM_MAX_BYTES:
            self.exhausted = "CUMULATIVE_BYTE_BUDGET_EXHAUSTED"
            raise BudgetExhausted(self.exhausted)
        if total > self.max_bytes:
            self.exhausted = f"{self.scope}_BYTE_BUDGET_EXHAUSTED"
            raise BudgetExhausted(self.exhausted)

    def check_bytes(self) -> None:
        if self.max_single_response > self.max_single:
            self.exhausted = f"{self.scope}_SINGLE_RESPONSE_CAP"
            raise BudgetExhausted(self.exhausted)
        self._check_total(self.bytes)


def probe_ledger() -> AccrualLedger:
    return AccrualLedger(max_attempts=PROBE_MAX_ATTEMPTS, max_bytes=PROBE_MAX_BYTES,
                         max_single=PROBE_MAX_SINGLE_RESPONSE, scope="PROBE")


def fetch_fee_document(ledger: AccrualLedger, fetch: Callable[..., tuple[int, dict[str, str], bytes]],
                       sleep: Callable[[float], None]) -> d1.Response:
    """GET the exact frozen fee page under the frozen DATA-02 retry policy (429/503: 2/8/30 s,
    integer Retry-After in [0, 60] only lengthens; timeout/reset/truncation/408/5xx: one immediate
    retry); no redirect is followed. The DATA-01 URL policy has no rule for this host, so the exact
    URL is the whole allowlist entry."""

    headers = {"User-Agent": USER_AGENT, "Accept": "text/html"}
    throttles = transports = 0
    delay = 0
    while True:
        ledger.check_attempt(None)
        if delay:
            sleep(delay)
            delay = 0
        try:
            status, response_headers, body = fetch("GET", FEE_URL, headers, d1.TIMEOUT_SECONDS)
        except d1._TransportError as error:  # noqa: SLF001
            ledger.record(FEE_HOST, None, 0)
            if transports < d2.MAX_TRANSPORT_RETRIES:
                transports += 1
                ledger.note_transport_retry()
                continue
            raise TransportFailure("TRANSPORT_" + error.kind) from None
        ledger.record(FEE_HOST, status, len(body))
        ledger.check_bytes()
        if len(body) > FEE_MAX_BYTES:
            raise TransportFailure("RESPONSE_TOO_LARGE")
        if 300 <= status < 400:
            raise TransportFailure("NETWORK_REDIRECT_REFUSED")
        if status in d2.THROTTLE_STATUSES:
            if throttles < d2.MAX_THROTTLE_RETRIES:
                delay, valid, extended = d2.throttle_delay(throttles, response_headers.get("retry-after"))
                throttles += 1
                ledger.note_throttle_retry(delay, valid, extended)
                continue
            raise TransportFailure(f"HTTP_{status}")
        if status in d2.OTHER_RETRYABLE_STATUSES:
            if transports < d2.MAX_TRANSPORT_RETRIES:
                transports += 1
                ledger.note_transport_retry()
                continue
            raise TransportFailure(f"HTTP_{status}")
        if status != 200:
            raise TransportFailure(f"HTTP_{status}")
        declared = d1.content_length(response_headers)
        if declared is not None and len(body) < declared:
            if transports < d2.MAX_TRANSPORT_RETRIES:
                transports += 1
                ledger.note_transport_retry()
                continue
            raise TransportFailure("BODY_TRUNCATED")
        if declared is not None and len(body) > declared:
            raise TransportFailure("BODY_LENGTH_MISMATCH")
        return d1.Response(status, response_headers, body)


# ── Multi-run content-addressed store (append-only index, versioned mutable captures) ──


def _is_mutable(url: str) -> bool:
    parts = urllib.parse.urlsplit(url)
    return (url == FEE_URL or url == d1.pf_url("audit") or parts.hostname == GAMMA_HOST
            or (parts.hostname == NDFD_HOST and parts.path == "/"))


class AccrualStore(d2.ArtifactStore):
    """Immutable raw blobs by SHA-256 plus an append-only ``INDEX.jsonl`` of ``(run, key, entry)``.

    The view of run ``k`` holds every successful entry of runs ``< k`` (successful immutable bytes are
    reused, never redownloaded) and every entry of run ``k`` itself; failures of earlier runs are not
    in the view, so a later manual run may retry them. Mutable sources (audit page, NDFD listings,
    Gamma documents, the fee page) carry a ``capture=run-NNN`` key suffix: each run's capture is a new
    version and changed bytes never overwrite or backdate an earlier one. Replay never adopts.
    """

    def __init__(self, root: Path, run: int, transport: d2.BoundedTransport | None,
                 gamma_client_factory: Callable[[], object] | None = None, *, replay: bool = False,
                 clock: Callable[[], datetime] | None = None, sleep: Callable[[float], None] | None = None,
                 fetch: Callable[..., tuple[int, dict[str, str], bytes]] | None = None) -> None:
        super().__init__(root, transport, gamma_client_factory, replay=replay, sleep=sleep)
        self.run = run
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._fetch_fn = fetch or d1.urllib_fetch
        self.index_file = root / INDEX_FILENAME
        self.index = {}
        self.run_of: dict[str, int] = {}
        self._persisted: set[str] = set()
        for record in _jsonl(self.index_file):
            record_run, key, entry = int(record["run"]), str(record["key"]), dict(record["entry"])  # type: ignore[arg-type]
            if record_run > run or (record_run < run and "failed" in entry) or key in self.index:
                continue
            self.index[key] = entry
            self.run_of[key] = record_run
            self._persisted.add(key)

    def key(self, method: str, url: str, byte_range: tuple[int, int] | None = None) -> str:  # type: ignore[override]
        base = d1.ArtifactStore.key(method, url, byte_range)
        return f"{base} capture=run-{self.run:03d}" if _is_mutable(url) else base

    def _now(self) -> str:
        return oa.utc_text(self._clock().astimezone(timezone.utc).replace(microsecond=0))

    def _store(self, key: str, data: bytes, meta: Mapping[str, object]) -> None:
        super()._store(key, data, {**meta, "captured_at": self._now()})

    def _persist(self) -> None:
        if self.replay:
            raise OperatorStop("VERIFY_FAILED")
        new = [k for k in self.index if k not in self._persisted]
        if not new:
            return
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        with self.index_file.open("ab") as handle:
            for key in new:
                entry = self.index[key]
                entry.setdefault("captured_at", self._now())
                handle.write(canonical({"run": self.run, "key": key, "entry": entry}) + b"\n")
                self._persisted.add(key)
                self.run_of[key] = self.run
            handle.flush()
            os.fsync(handle.fileno())

    def versions(self, url: str, suffix: str = "") -> list[tuple[int, str, dict[str, object]]]:
        pattern = re.compile("^" + re.escape(f"GET {url} capture=run-") + r"(\d{3})" + re.escape(suffix) + "$")
        found = []
        for key, entry in self.index.items():
            match = pattern.fullmatch(key)
            if match:
                found.append((int(match.group(1)), key, entry))
        return sorted(found)

    def read_entry(self, key: str) -> bytes:
        return self._read_verified(str(self.index[key]["sha256"]))

    def fee_document(self, ledger: AccrualLedger | None) -> tuple[str, dict[str, object]]:
        key = self.key("GET", FEE_URL)
        self.used.add(key)
        if key in self.index:
            return key, self.index[key]
        if self.replay or ledger is None:
            raise ReplayMissing(key)
        try:
            response = fetch_fee_document(ledger, self._fetch_fn, self._sleep)
        except TransportFailure as failure:
            self.index[key] = {"failed": failure.code}
            self._persist()
            return key, self.index[key]
        self._store(key, response.body, {"media_type": "text/html", "last_modified": response.headers.get("last-modified"),
                                         "status": response.status})
        return key, self.index[key]

    def gamma_key(self, market_id: str, run: int | None = None) -> str:
        return (f"GET https://{GAMMA_HOST}/markets/{market_id} capture=run-{(run if run is not None else self.run):03d}"
                " via=PolymarketPublicClient.get_market")


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
    now: Callable[[], datetime] | None = None

    @property
    def workspace(self) -> Path:
        return self.repo_root.joinpath(*WORKSPACE_PARTS)

    @property
    def probe_workspace(self) -> Path:
        return self.repo_root.joinpath(*PROBE_PARTS)

    def run_git(self, *args: str) -> str:
        return (self.git or (lambda *a: _git(self.repo_root, *a)))(*args)

    def blob(self, revision: str, path: str) -> bytes:
        return (self.git_blob or (lambda r, p: _git_blob(self.repo_root, r, p)))(revision, path)

    def sleeper(self) -> Callable[[float], None]:
        return self.sleep or time.sleep

    def clock(self) -> datetime:
        moment = (self.now or (lambda: datetime.now(timezone.utc)))()
        if moment.tzinfo is None:
            raise OperatorStop("STATE_DRIFT")
        return moment.astimezone(timezone.utc)

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


def verify_plan_freeze(env: Environment) -> dict[str, object]:
    """Zero network: the merged PLAN-01 bytes (working tree and the merge commit), the power
    document, and the GitHub server merge event of PR #205 at or before the freeze deadline."""

    try:
        plan_bytes = (env.repo_root / oa.PLAN_PATH).read_bytes()
        power_bytes = (env.repo_root / oa.POWER_DOC_PATH).read_bytes()
    except OSError:
        raise OperatorStop("PLAN_FREEZE_INVALID") from None
    try:
        if env.blob(oa.PLAN_MERGE_SHA, oa.PLAN_PATH) != plan_bytes:
            raise OperatorStop("PLAN_FREEZE_INVALID")
        if oa.sha256_lf(env.blob(oa.PLAN_MERGE_SHA, oa.POWER_DOC_PATH)) != oa.sha256_lf(power_bytes):
            raise OperatorStop("PLAN_FREEZE_INVALID")
        lines = env.run_git("show", "-s", "--format=%H%n%P%n%cn%n%cI", oa.PLAN_MERGE_SHA).splitlines()
        env.run_git("merge-base", "--is-ancestor", oa.PLAN_MERGE_SHA, "HEAD")
    except OperatorStop:
        raise OperatorStop("PLAN_FREEZE_INVALID") from None
    if len(lines) < 4:
        raise OperatorStop("PLAN_FREEZE_INVALID")
    try:
        binding = oa.verify_plan_binding(plan_bytes, power_bytes)
        freeze = oa.verify_freeze_event(lines[0].strip(), lines[1].split(), lines[2].strip(), lines[3].strip())
    except oa.AccrualError:
        raise OperatorStop("PLAN_FREEZE_INVALID") from None
    return {**binding, **freeze}


def frozen_plan_body() -> dict[str, object]:
    return {
        "wp_id": WP_ID,
        "base_sha": BASE_SHA,
        "predecessor": {"pr": PREDECESSOR_PR, "merge": oa.PLAN_MERGE_SHA, "plan_01_plan_sha256": oa.PLAN_SHA256,
                        "plan_01_merge_time": oa.PLAN_MERGE_TIME, "freeze_deadline": oa.FREEZE_DEADLINE},
        "oos_start": oa.OOS_START, "embargo_lower_bound": oa.EMBARGO_LOWER_BOUND, "cap": oa.CAP,
        "scan_days": [oa.SCAN_START.isoformat(), oa.SCAN_END.isoformat()],
        "discovery_hours_utc": list(oa.DISCOVERY_HOURS_UTC), "discovery_product": "PendulumFlow v3 new_market",
        "checkpoints": qd.checkpoint_definitions(), "label_window_minutes": 30,
        "b0": {"rule": oa.B0_RULE, "max_midpoint_spread": "0.1", "max_last_trade_age_seconds": oa.MAX_LAST_TRADE_AGE_SECONDS},
        "data02": {"bundle_id": oa.DATA02_BUNDLE_ID, "logical_dataset_id": oa.DATA02_DATASET_ID,
                   "oos_status": oa.DATA02_OOS_STATUS},
        "fee_document_url": FEE_URL,
        "allowlist": sorted(ALLOWED_HOSTS),
        "methods": ["GET"],
        "retry_policy": {"throttle_statuses": sorted(d2.THROTTLE_STATUSES), "throttle_delays_seconds": list(d2.THROTTLE_DELAYS_SECONDS),
                         "retry_after_max_seconds": d2.RETRY_AFTER_MAX_SECONDS, "transport_max_retries": d2.MAX_TRANSPORT_RETRIES},
        "budgets": {
            "run": {"attempts": RUN_MAX_ATTEMPTS, "bytes": RUN_MAX_BYTES, "single_response": MAX_SINGLE_RESPONSE,
                    "pendulumflow_hours": RUN_MAX_PENDULUM_HOURS},
            "cumulative": {"attempts": CUM_MAX_ATTEMPTS, "bytes": CUM_MAX_BYTES, "pendulumflow_hours": CUM_MAX_PENDULUM_HOURS,
                           "accrue_runs": MAX_ACCRUE_RUNS, "considered_target_dates": oa.MAX_CONSIDERED_TARGET_DATES,
                           "candidates": MAX_CANDIDATES, "stations": MAX_STATIONS},
        },
        "provenance": {"ceiling": oa.MAX_QUALIFICATION_PROVENANCE_MANIFESTS, "prospective_reserve": oa.PROSPECTIVE_MANIFEST_RESERVE},
    }


def load_plan(env: Environment) -> dict[str, object]:
    plan_path = env.workspace / PLAN_FILENAME
    hash_path = env.workspace / PLAN_HASH_FILENAME
    if not plan_path.exists() or not hash_path.exists():
        raise OperatorStop("PLAN_MISSING")
    try:
        plan = read_json(plan_path)
        recorded = hash_path.read_text(encoding="utf-8").strip()
    except (OSError, ValueError):
        raise OperatorStop("PLAN_INVALID") from None
    if not isinstance(plan, dict) or sha256_hex(canonical(plan)) != recorded or plan.get("frozen") != frozen_plan_body():
        raise OperatorStop("PLAN_INVALID")
    if plan.get("code_digests") != code_digests(env.repo_root):
        runs = env.workspace / RUNS_DIRNAME
        started = runs.exists() and any(runs.iterdir())
        raise OperatorStop("CODE_DRIFT_AFTER_PROSPECTIVE_ACCRUAL" if started else "STATE_DRIFT")
    return plan


def _plan_sha(plan: Mapping[str, object]) -> str:
    return sha256_hex(canonical(dict(plan)))


# ── Commands: prepare ─────────────────────────────────────────────────────────


def discover_data02(env: Environment) -> dict[str, object]:
    """The verified DATA-02 run-01 bundle, only beneath git worktree roots."""

    valid: list[dict[str, object]] = []
    for root in sorted(set(d1.worktree_roots(env)), key=str):  # type: ignore[arg-type]
        candidate = root.joinpath(*DATA02_PARTS)
        if not (candidate / d2.BUNDLE_FILENAME).is_file():
            continue
        try:
            bundle = read_json(candidate / d2.BUNDLE_FILENAME)
            verified = read_json(candidate / d2.VERIFY_FILENAME)
        except (OSError, ValueError):
            continue
        if not (isinstance(bundle, dict) and isinstance(verified, dict) and verified.get("status") == "VERIFIED"
                and verified.get("network_calls") == 0 and verified.get("bundle_id") == DATA02_BUNDLE_ID
                and verified.get("logical_dataset_id") == DATA02_DATASET_ID):
            continue
        valid.append(bundle)
    if not valid:
        raise OperatorStop("DATA02_EVIDENCE_MISSING")
    if len({sha256_hex(canonical(b)) for b in valid}) != 1:
        raise OperatorStop("PLAN_FREEZE_INVALID")
    return valid[0]


def command_prepare(env: Environment) -> dict[str, object]:
    head = env.run_git("rev-parse", "HEAD").strip()
    dirty = env.run_git("status", "--porcelain", "--untracked-files=normal").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", head) or dirty:
        raise OperatorStop("STATE_DRIFT")
    freeze = verify_plan_freeze(env)
    bundle = discover_data02(env)
    try:
        n2, eligible_dates = oa.historical_n2(bundle, bundle_id=DATA02_BUNDLE_ID, dataset_id=DATA02_DATASET_ID)
    except oa.AccrualError:
        raise OperatorStop("PLAN_FREEZE_INVALID") from None
    if not oa.provenance_pre_gate(n2):
        raise OperatorStop("PROVENANCE_CEILING_UNREACHABLE")
    plan = {
        "schema_id": "s10-qual-data-03-accrual-plan",
        "schema_version": "1.0.0",
        "frozen": frozen_plan_body(),
        "plan_binding": freeze,
        "repo_code_identity": head,
        "code_digests": code_digests(env.repo_root),
        "data02": {"bundle_id": DATA02_BUNDLE_ID, "logical_dataset_id": DATA02_DATASET_ID, "n2": n2,
                   "eligible_historical_dates": list(eligible_dates)},
    }
    workspace = env.workspace
    plan_path = workspace / PLAN_FILENAME
    if plan_path.exists():
        if read_json(plan_path) != plan:
            raise OperatorStop("PREPARE_WORKSPACE_CONFLICT")
        status = "PREPARED_IDEMPOTENT"
    else:
        if workspace.exists() and any(workspace.iterdir()):
            raise OperatorStop("PREPARE_WORKSPACE_CONFLICT")
        workspace.mkdir(parents=True, exist_ok=True)
        write_json_atomic(plan_path, plan)
        (workspace / PLAN_HASH_FILENAME).write_text(_plan_sha(plan) + "\n", encoding="utf-8")
        write_json_atomic(workspace / STATE_FILENAME, {"status": oa.STATE_NOT_STARTED})
        status = "PREPARED"
    state = read_json(workspace / STATE_FILENAME)
    report = oa.validate_visible_report({
        "kind": "PREPARE", "wp_id": WP_ID, "status": status, "state": state["status"],  # type: ignore[index]
        "plan_sha256": oa.PLAN_SHA256, "plan_merge_sha": oa.PLAN_MERGE_SHA, "plan_merge_time": oa.PLAN_MERGE_TIME,
        "repo_code_identity": head, "workspace_plan_sha256": _plan_sha(plan),
        "data02_bundle_id": DATA02_BUNDLE_ID, "data02_dataset_id": DATA02_DATASET_ID,
        "data02_eligible_dates": len(eligible_dates), "n2": n2, "n2_plus_reserve": n2 + oa.PROSPECTIVE_MANIFEST_RESERVE,
        "provenance_ceiling": oa.MAX_QUALIFICATION_PROVENANCE_MANIFESTS, "provenance_pre_gate": True,
    })
    write_json_atomic(workspace / PREPARE_REPORT_FILENAME, report)
    return report


# ── Per-run accrual derivation (shared by accrue and verify-final replay) ─────


@dataclasses.dataclass
class RowWork:
    checkpoint_id: str
    decision_time: datetime | None = None
    state: str = "PENDING"  # PENDING | CANDIDATE | EXCLUDED
    reason: str | None = None
    row_id: str | None = None
    b0: oa.B0Result | None = None
    q: str | None = None
    l_days: str | None = None
    l_seconds: str | None = None
    history: dict | None = None
    weather: dict | None = None
    scanned: list = dataclasses.field(default_factory=list)
    weather_keys: set = dataclasses.field(default_factory=set)


class AccrualPipeline:
    """One accrual run: frozen census, per-market structural/label classification, terminal ledger
    bodies and sealed records. Terminal subjects of earlier runs are never re-evaluated."""

    def __init__(self, store: AccrualStore, plan: Mapping[str, object], decode_fn: Callable[..., ndfd.DecodedPop12],
                 ledger: AccrualLedger | None, *, run: int, as_of: datetime, prior_entries: Sequence[Mapping[str, object]],
                 prior_hours: frozenset[str]) -> None:
        self.store = store
        self.plan = plan
        self.decode_fn = decode_fn
        self.ledger = ledger
        self.run = run
        self.as_of = as_of
        self.prior_markets = {str(e["subject_id"]): e for e in prior_entries if e["entry_kind"] == "MARKET"}
        self.prior_dates = {str(e["target_date"]): e for e in prior_entries if e["entry_kind"] == "DATE"}
        self.prior_hours = prior_hours
        self.prior_stations = {str(e["station_id"]) for e in self.prior_markets.values() if e.get("station_id")}
        self.audit: v3.V3AuditSnapshot | None = None
        self.audit_key: str | None = None
        self.hours: d2.V3Hours | None = None
        self.ndfd: d1.NdfdAccess | None = None
        self.touched_hours: set[str] = set()
        self.discovery_ok: set[str] = set()
        self.discovery_events: dict[str, list[v3.V3Event]] = {}
        self.discovery_failed: set[str] = set()
        self.budget_exhausted: str | None = None
        self.new_bodies: list[dict[str, object]] = []
        self.new_sealed: list[dict[str, object]] = []
        self.events: dict[tuple[str, str, str], tuple[v3.V3Event, ...]] = {}
        self.tick_events: dict[str, tuple[v3.V3Event, ...]] = {}
        self.tick_failed: set[str] = set()
        self.stations: dict[str, object] = {}
        self.decoded: dict[tuple[str, int, str], tuple[ndfd.MessageSlice, ndfd.DecodedPop12] | str] = {}
        self.discovered_in_window: set[str] = set()
        self.outside_window: set[str] = set()
        self.coverage_seen: dict[str, str] = {}
        self.fee_capture: dict[str, object] | None = None

    # -- hour availability under the current audit snapshot --
    def _index(self, hour: str) -> int:
        return int((v3.hour_start(hour) - v3.hour_start(v3.LIVE_START_HOUR)).total_seconds() // 3600)

    def published(self, hour: str) -> bool:
        if self.audit is None or v3.hour_start(hour) + timedelta(hours=1) > self.as_of:
            return False
        return 0 <= self._index(hour) < self.audit.published_hours

    def measured(self, hour: str) -> bool:
        return self.published(hour) and self._index(hour) < self.audit.measured_hours  # type: ignore[union-attr]

    def _hour(self, hour: str) -> None:
        if hour not in self.touched_hours:
            if len(self.touched_hours) + 1 > RUN_MAX_PENDULUM_HOURS:
                raise BudgetExhausted("RUN_PENDULUM_HOUR_BUDGET_EXHAUSTED")
            if len(self.prior_hours | self.touched_hours | {hour}) > CUM_MAX_PENDULUM_HOURS:
                raise BudgetExhausted("CUMULATIVE_PENDULUM_HOUR_BUDGET_EXHAUSTED")
            self.touched_hours.add(hour)

    # -- phases --
    def phase_audit(self) -> None:
        url = d1.pf_url("audit")
        try:
            self.store.get(url, accept="text/html", media_type="text/html")
        except TransportFailure:
            pass
        for _run, key, entry in reversed(self.store.versions(url)):
            if "failed" in entry:
                continue
            try:
                self.audit = v3.parse_audit_page(self.store.read_entry(key))
                self.audit_key = key
                break
            except v3.PendulumFlowError:
                continue
        self.hours = d2.V3Hours(self.store, self.audit)  # type: ignore[arg-type]
        self.ndfd = d1.NdfdAccess(self.store, self.decode_fn)  # type: ignore[arg-type]

    def phase_fee(self) -> None:
        key, entry = self.store.fee_document(self.ledger)
        valid = "failed" not in entry and oa.fee_document_valid(FEE_URL, int(entry.get("status", 0)), self.store.read_entry(key))  # type: ignore[arg-type]
        self.fee_capture = {"key": key, "ok": "failed" not in entry, "contract_valid": valid}

    def phase_discovery(self) -> None:
        assert self.hours is not None
        for day in oa.scan_days():
            for hh in oa.DISCOVERY_HOURS_UTC:
                hour = oa.discovery_hour(day, hh)
                if not self.published(hour):
                    continue
                self._hour(hour)
                try:
                    events = self.hours.read("discovery", hour, "new_market")
                except d2.SourceReadFailed:
                    self.discovery_failed.add(hour)  # census stays structural pending; retried later
                    continue
                self.discovery_ok.add(hour)
                self.discovery_events[hour] = [e for e in events if oa.is_rain_family_event(e)]
        seen: set[str] = set()
        for hour in sorted(self.discovery_events):
            for event in self.discovery_events[hour]:
                if event.market_id is None or event.market_id in seen:
                    continue
                seen.add(event.market_id)
                parsed = qd.parse_rain_slug(event.field("slug"))
                if parsed is not None and oa.SCAN_START <= parsed[0] <= oa.SCAN_END:
                    self.discovered_in_window.add(event.market_id)
                else:
                    self.outside_window.add(event.market_id)
        if len(seen) > MAX_CANDIDATES:
            raise BudgetExhausted("CUMULATIVE_CANDIDATE_BUDGET_EXHAUSTED")

    def phase_gamma_capture(self) -> None:
        """Capture-only: a current Gamma document for every known in-window non-terminal market
        that has no successful capture yet (pre-close rule/fee/tick evidence as early as possible)."""

        for market_id in sorted(self.discovered_in_window - set(self.prior_markets), key=lambda m: (len(m), m)):
            if any("failed" not in e for _r, _k, e in self.store.versions(f"https://{GAMMA_HOST}/markets/{market_id}",
                                                                          " via=PolymarketPublicClient.get_market")):
                continue
            try:
                self.store.gamma_market(market_id, self.ledger)
            except TransportFailure:
                continue

    def phase_dates(self) -> None:
        for day in oa.scan_days():
            iso = day.isoformat()
            if iso in self.prior_dates:
                continue
            if not oa.census_closed(day, frozenset(self.discovery_ok)):
                break  # every later census needs a superset of these hours
            census = oa.assign_census(self.discovery_events, day)
            outcomes: list[dict[str, object]] = []
            pending = False
            for market_id in census.inconsistent_market_ids:
                if market_id in self.prior_markets:
                    outcomes.append(dict(self.prior_markets[market_id]))
                    continue
                outcomes.append(self._market_entry(day, market_id, None, "V3_MARKET_IDENTITY_INCONSISTENT"))
            for candidate in census.candidates:
                if candidate.market_id in self.prior_markets:
                    outcomes.append(dict(self.prior_markets[candidate.market_id]))
                    continue
                outcome = self.evaluate_market(day, candidate)
                if outcome is None:
                    pending = True
                    continue
                outcomes.append(outcome)
            if not pending:
                self._date_entry(day, outcomes)

    # -- market evaluation --
    def _gamma_versions(self, market_id: str, candidate: qd.MarketCandidate) -> list[tuple[int, str, dict, qd.GammaFacts | str]]:
        out = []
        for run, key, entry in self.store.versions(f"https://{GAMMA_HOST}/markets/{market_id}", " via=PolymarketPublicClient.get_market"):
            if "failed" in entry:
                continue
            document = json.loads(self.store.read_entry(key).decode("utf-8"))
            try:
                facts: qd.GammaFacts | str = qd.normalize_gamma_market(document, candidate)
            except qd.RuleExclusion as exclusion:
                facts = exclusion.code
            out.append((run, key, document, facts))
        return out

    def _poll_gamma(self, market_id: str) -> bool:
        if self.store.gamma_key(market_id) in self.store.index:
            return "failed" not in self.store.index[self.store.gamma_key(market_id)]
        try:
            self.store.gamma_market(market_id, self.ledger)
            return True
        except TransportFailure:
            return False

    def _station(self, station_id: str) -> ndfd.StationMetadata | str:
        if station_id not in self.stations:
            if len(self.prior_stations | set(self.stations) | {station_id}) > MAX_STATIONS:
                raise BudgetExhausted("CUMULATIVE_STATION_BUDGET_EXHAUSTED")
            url = f"https://{NWS_HOST}/stations/{station_id}"
            try:
                raw = self.store.get(url, accept="application/geo+json", media_type="application/geo+json")
                self.stations[station_id] = ndfd.parse_nws_station(json.loads(raw.decode("utf-8")), station_id)
            except TransportFailure:
                self.stations[station_id] = "STATION_METADATA_UNAVAILABLE"
            except (ndfd.NdfdError, ValueError, UnicodeDecodeError):
                self.stations[station_id] = "STATION_METADATA_INVALID"
        return self.stations[station_id]  # type: ignore[return-value]

    def evaluate_market(self, day: date, candidate: qd.MarketCandidate) -> dict[str, object] | None:
        """A terminal market ledger body, or ``None`` while the market is pending."""

        market_id = candidate.market_id
        versions = self._gamma_versions(market_id, candidate)
        if not versions:
            if not self._poll_gamma(market_id):
                return self._market_entry(day, market_id, candidate, "GAMMA_UNAVAILABLE")
            versions = self._gamma_versions(market_id, candidate)
        _run0, initial_key, _doc, initial = versions[0]
        if isinstance(initial, str):
            return self._market_entry(day, market_id, candidate, initial, versions=versions)
        try:
            rule = qd.parse_rule(initial.description)
        except qd.RuleExclusion as exclusion:
            return self._market_entry(day, market_id, candidate, exclusion.code, versions=versions)
        station = self._station(rule.station_id)
        if isinstance(station, str):
            return self._market_entry(day, market_id, candidate, station, versions=versions, rule=rule)
        try:
            offset = ndfd.standard_utc_offset_minutes(station.time_zone, day)
        except ndfd.NdfdError:
            return self._market_entry(day, market_id, candidate, "STATION_OFFSET_UNDERIVABLE", versions=versions, rule=rule)
        receive = qd.parse_utc(candidate.first_received)
        gamma_open = qd.gamma_open_time_if_trustworthy(initial.open_time, receive)
        observable = qd.observable_time(receive, gamma_open)
        rows = {cp: RowWork(cp) for cp in qd.CHECKPOINT_IDS}
        rows[qd.CHECKPOINT_A].decision_time = qd.checkpoint_a(receive, gamma_open)
        b_time, b_ok = qd.checkpoint_b(day, offset, observable)
        rows[qd.CHECKPOINT_B].decision_time = b_time
        if not b_ok:
            rows[qd.CHECKPOINT_B].state, rows[qd.CHECKPOINT_B].reason = "EXCLUDED", "CHECKPOINT_B_MARKET_NOT_OPEN_60M"
        yes = qd.yes_token(initial)
        for row in rows.values():
            if row.state == "EXCLUDED":
                continue
            row.row_id = oa.prospective_row_id(target_date=day.isoformat(), market_id=market_id,
                                               condition_id=candidate.condition_id, checkpoint_id=row.checkpoint_id,
                                               decision_time=oa.utc_text(row.decision_time), yes_token_id=yes)  # type: ignore[arg-type]
            self._evaluate_row(day, candidate, station, offset, row, yes)
        if any(r.state == "PENDING" for r in rows.values()):
            return None
        label: qd.LabelEvidence | None = None
        final_key: str | None = None
        label_hours: list[str] = []
        if any(r.state == "CANDIDATE" for r in rows.values()):
            outcome = self._label(market_id, candidate, versions)
            if outcome is None:
                return None
            if isinstance(outcome, str):
                return self._market_entry(day, market_id, candidate, outcome, versions=self._gamma_versions(market_id, candidate),
                                          rule=rule, rows=rows)
            label, final_key, label_hours = outcome
            for row in rows.values():
                if row.state == "CANDIDATE" and qd.parse_utc(label.v3_resolution_received) <= row.decision_time:  # type: ignore[operator]
                    row.state, row.reason = "EXCLUDED", "LABEL_RESOLVED_BEFORE_CHECKPOINT"
        return self._market_entry(day, market_id, candidate, None, versions=self._gamma_versions(market_id, candidate),
                                  rule=rule, rows=rows, label=label, final_key=final_key, label_hours=label_hours)

    def _label(self, market_id: str, candidate: qd.MarketCandidate, versions) -> tuple[qd.LabelEvidence, str, list[str]] | str | None:
        """PENDING_LABEL_FINALITY (``None``) until a final Gamma capture and every published
        label-window read exist; a Gamma re-poll failure never mints absence."""

        assert self.hours is not None
        final, bad = _final_capture(versions)
        if bad is not None:
            return bad
        if final is None:
            self._poll_gamma(market_id)  # this run's re-poll (cached if already captured); failure stays pending
            final, bad = _final_capture(self._gamma_versions(market_id, candidate))
            if bad is not None:
                return bad
            if final is None:
                return None
        key, gamma = final
        closed = qd.parse_utc(gamma.closed_time)
        hours = list(v3.hours_between(closed - oa.LABEL_WINDOW, closed + oa.LABEL_WINDOW))
        if not all(self.published(h) for h in hours):
            return None
        resolutions: list[v3.V3Event] = []
        read_failed = False
        for hour in hours:
            self._hour(hour)
            try:
                events = self.hours.read("labels", hour, "market_resolved")
            except d2.SourceReadFailed:
                read_failed = True
                break
            resolutions.extend(e for e in events if e.condition_id == candidate.condition_id)
        try:
            return d2.label_outcome(gamma, resolutions, read_failed), key, hours
        except qd.RuleExclusion as exclusion:
            return exclusion.code

    def _listing(self, day: date, checkpoint: datetime, keys: set) -> tuple[ndfd.NdfdObject, ...] | None:
        """The earliest NDFD day listing captured at or after ``min(day end, checkpoint)`` (final for
        selection); otherwise a fresh capture now. A listing captured earlier is never final."""

        prefix = ndfd.day_prefix(day)
        url = f"https://{NDFD_HOST}/?" + urllib.parse.urlencode({"list-type": "2", "prefix": prefix})
        threshold = min(datetime(day.year, day.month, day.day, tzinfo=timezone.utc) + timedelta(days=1), checkpoint)
        for _run, key, entry in self.store.versions(url):
            if "failed" in entry or qd.parse_utc(entry["captured_at"]) < threshold:
                continue
            keys.add(key)
            try:
                return ndfd.parse_s3_listing(self.store.read_entry(key), prefix)
            except ndfd.NdfdError:
                return None
        try:
            raw = self.store.get(url, accept="application/xml", media_type="application/xml")
        except TransportFailure:
            return None
        keys.add(self.store.key("GET", url))
        try:
            return ndfd.parse_s3_listing(raw, prefix)
        except ndfd.NdfdError:
            return None

    def _evaluate_row(self, day: date, candidate: qd.MarketCandidate, station: ndfd.StationMetadata, offset: int,
                      row: RowWork, yes: str) -> None:
        assert self.hours is not None and self.ndfd is not None and row.decision_time is not None
        checkpoint = row.decision_time
        if checkpoint > self.as_of:
            return  # checkpoint not reached: structural pending
        lower = max(checkpoint - qd.MARKET_HISTORY_LOOKBACK, qd.parse_utc(candidate.first_received))
        walk = list(v3.hours_between(lower, checkpoint))
        if not all(self.measured(h) for h in walk):
            return  # a required archive hour is not yet published/audit-measured
        low = checkpoint - qd.NDFD_VINTAGE_LOOKBACK
        days = sorted({(low + timedelta(hours=h)).date() for h in range(0, 49)} | {checkpoint.date()})
        objects: list[ndfd.NdfdObject] = []
        for listing_day in days:
            listing = self._listing(listing_day, checkpoint, row.weather_keys)
            if listing is None:
                row.state, row.reason = "EXCLUDED", "WEATHER_SOURCE_INVALID"
                return
            objects.extend(listing)
        vintage = ndfd.select_vintage(objects, checkpoint, qd.NDFD_VINTAGE_LOOKBACK)
        if vintage is None:
            row.state, row.reason = "EXCLUDED", "WEATHER_NO_ELIGIBLE_VINTAGE"
            return
        try:
            data = self.ndfd.object_bytes(vintage)
            slices = ndfd.scan_messages(data)
            headers = [ndfd.parse_pop12_header(ndfd.message_bytes(data, piece)) for piece in slices]
        except ndfd.NdfdError:
            row.state, row.reason = "EXCLUDED", "WEATHER_SOURCE_INVALID"
            return
        row.weather_keys |= self.ndfd.keys_by_object.get(vintage.key, set())
        start, end = ndfd.climate_day_window(day, offset)
        decoded = []
        for index in ndfd.intervals_overlapping(headers, start, end):
            cache = (vintage.key, index, station.station_id)
            if cache not in self.decoded:
                try:
                    self.decoded[cache] = (slices[index], self.decode_fn(ndfd.message_bytes(data, slices[index]), [station]))
                except ndfd.NdfdError as error:
                    self.decoded[cache] = "GRID_BINDING_INVALID" if error.code == "GRID_BINDING_INVALID" else "WEATHER_SOURCE_INVALID"
            item = self.decoded[cache]
            if isinstance(item, str):
                row.state, row.reason = "EXCLUDED", item
                return
            decoded.append(item)
        try:
            weather = qd.weather_evidence(vintage, sha256_hex(data), decoded, station, offset, day, checkpoint)
        except qd.RuleExclusion as exclusion:
            row.state, row.reason = "EXCLUDED", exclusion.code
            return
        history = self._market_history(candidate, row, yes, lower, checkpoint)
        if isinstance(history, str):
            row.state, row.reason = "EXCLUDED", history
            return
        try:
            b0 = oa.materialize_b0(history, checkpoint)
        except qd.RuleExclusion as exclusion:
            row.state, row.reason = "EXCLUDED", exclusion.code
            return
        except oa.AccrualError:  # a malformed source bid/ask/price is a source defect, never a wedge
            row.state, row.reason = "EXCLUDED", "MARKET_HISTORY_SOURCE_INVALID"
            return
        if not b0.available:
            row.state, row.reason = "EXCLUDED", "B0_UNAVAILABLE"
            return
        row.state, row.b0, row.history, row.weather = "CANDIDATE", b0, history, weather
        row.q = oa.materialize_q(weather)
        row.l_seconds, row.l_days = oa.materialize_l(weather)

    def _market_history(self, candidate: qd.MarketCandidate, row: RowWork, yes: str, lower: datetime,
                        checkpoint: datetime) -> dict[str, object] | str:
        """The DATA-02 D011 walk-back for one (market, checkpoint): a failed best_bid_ask hour is
        MARKET_HISTORY_SOURCE_INVALID; a failed last_trade_price hour is never listed as searched."""

        assert self.hours is not None
        cid = candidate.condition_id
        cursor = v3.hour_start(v3.hour_key(checkpoint))
        floor = v3.hour_start(v3.hour_key(lower))
        scanned: list[str] = []
        ltp_failed: list[str] = []
        bba_events: list[v3.V3Event] = []
        trades: list[v3.V3Event] = []
        while cursor >= floor:
            hour = v3.hour_key(cursor)
            self._hour(hour)
            try:
                bba = self.hours.read("market_history", hour, "best_bid_ask", [cid])
            except d2.SourceReadFailed:
                return "MARKET_HISTORY_SOURCE_INVALID"
            try:
                trades.extend(self.hours.read("market_history", hour, "last_trade_price", [cid]))
            except d2.SourceReadFailed:
                ltp_failed.append(hour)
            if hour not in self.tick_events and hour not in self.tick_failed:
                try:
                    self.tick_events[hour] = self.hours.read("market_history", hour, "tick_size_change")
                except d2.SourceReadFailed:
                    self.tick_failed.add(hour)
            scanned.append(hour)
            bba_events.extend(bba)
            self.coverage_seen[hour] = self.hours.coverage(hour, "best_bid_ask")
            if any(e.asset_id == yes and qd.parse_utc(e.timestamp_received) <= checkpoint for e in bba):
                break
            cursor -= timedelta(hours=1)
        row.scanned = scanned
        bba_cov = {h: self.hours.coverage(h, "best_bid_ask") for h in scanned}
        ltp_scanned = [h for h in scanned if h not in ltp_failed]
        ltp_cov = {h: self.hours.coverage(h, "last_trade_price") for h in ltp_scanned}
        try:
            latest = qd.select_latest_market_event(bba_events, family="best_bid_ask", asset_id=yes, checkpoint=checkpoint,
                                                   lookback=qd.MARKET_HISTORY_LOOKBACK, scanned_hours=scanned, hour_coverage=bba_cov)
        except qd.RuleExclusion as exclusion:
            return exclusion.code
        try:
            ltp = qd.select_latest_market_event(trades, family="last_trade_price", asset_id=yes, checkpoint=checkpoint,
                                                lookback=qd.MARKET_HISTORY_LOOKBACK, scanned_hours=ltp_scanned, hour_coverage=ltp_cov)
        except qd.RuleExclusion:
            ltp = None
        history = qd.market_history_evidence(latest, ltp, checkpoint, bba_cov, ltp_cov, ltp_scanned)
        history["last_trade_price_failed_hours"] = sorted(ltp_failed)
        if ltp is None and ltp_failed:
            history["last_trade_price_state"] = oa.LTP_STATE_SEARCH_INCOMPLETE
        return history

    # -- terminal bodies --
    def _artifact(self, key: str, kind: str, coverage: str | None = None) -> dict[str, object]:
        artifact = d1.ReadinessPipeline._artifact(self, key, kind, coverage)  # type: ignore[arg-type]  # frozen descriptor semantics
        mapping = dataclasses.asdict(artifact)
        mapping["request_parameters"] = [list(p) for p in artifact.request_parameters]
        mapping["dq_flags"] = list(artifact.dq_flags)
        return mapping

    def _v3_kind(self, key: str, hour: str) -> tuple[str, str | None]:
        return d1.ReadinessPipeline._v3_kind(self, key, hour)  # type: ignore[arg-type]

    def _retained(self, key: str | None) -> bool:
        return bool(key) and key in self.store.index and "failed" not in self.store.index[key]  # type: ignore[operator]

    def _market_entry(self, day: date, market_id: str, candidate: qd.MarketCandidate | None, exclusion: str | None, *,
                      versions=None, rule: qd.RuleSemantics | None = None, rows: Mapping[str, RowWork] | None = None,
                      label: qd.LabelEvidence | None = None, final_key: str | None = None,
                      label_hours: Sequence[str] = ()) -> dict[str, object]:
        assert self.hours is not None
        if exclusion is not None and exclusion in oa.FORBIDDEN_PROSPECTIVE_REASONS:
            raise oa.AccrualError("ACCRUAL_INPUT_INVALID")
        row_bodies = []
        sealed_rows = []
        scanned: set[str] = set()
        if exclusion is None and rows is not None:
            for cp in qd.CHECKPOINT_IDS:
                row = rows[cp]
                state = "ELIGIBLE" if row.state == "CANDIDATE" else "EXCLUDED"
                row_bodies.append({
                    "checkpoint_id": cp, "row_id": row.row_id if state == "ELIGIBLE" else None,
                    "decision_time": oa.utc_text(row.decision_time) if row.decision_time else None,
                    "state": state, "reason": row.reason if state == "EXCLUDED" else None,
                    "b0_basis": row.b0.basis if state == "ELIGIBLE" and row.b0 else None,
                })
                scanned |= set(row.scanned)
                if state == "ELIGIBLE":
                    sealed_rows.append({
                        "row_id": row.row_id, "checkpoint_id": cp, "b0": {"rule": oa.B0_RULE, "basis": row.b0.basis,  # type: ignore[union-attr]
                                                                          "value": row.b0.value},  # type: ignore[union-attr]
                        "features": {"mkt.ext_b0_probability_v1": row.b0.value, "time.ndfd_lead_hours_v1": row.l_days,  # type: ignore[union-attr]
                                     "wx.ndfd_pop12_max_climate_day_v1": row.q},
                        "l_seconds": row.l_seconds,
                        "feature_evidence": {"market_history": row.history, "weather": row.weather},
                        "label": {"label_ref": oa.LABEL_REF, "label_yes": label.winning_outcome == "Yes",  # type: ignore[union-attr]
                                  **label.to_mapping(rule)},  # type: ignore[union-attr,arg-type]
                    })
        artifacts: dict[str, list[dict[str, object]]] = {"PENDULUMFLOW_MARKET_HISTORY": [], "NOAA_NDFD_WEATHER": [],
                                                         "GAMMA_NWS_RULE_LABEL_METADATA": []}
        pf_hours: dict[str, list[object]] = {}
        if candidate is not None:
            for hour in sorted({candidate.discovery_hour, *scanned}):
                for key in sorted(self.hours.keys_by_hour.get(hour, ())):
                    if self._retained(key):
                        kind, coverage = self._v3_kind(key, hour)
                        artifacts["PENDULUMFLOW_MARKET_HISTORY"].append(self._artifact(key, kind, coverage))
                manifest = self.hours.manifests.get(hour)
                if manifest is not None:
                    pf_hours[hour] = [manifest.file_sha256, manifest.file_bytes]
            if rows is not None:
                for key in sorted({k for r in rows.values() for k in r.weather_keys}):
                    if self._retained(key):
                        artifacts["NOAA_NDFD_WEATHER"].append(self._artifact(key, "ndfd_object" if "YDUZ98" in key else "complete"))
            meta = [k for _r, k, _d, _f in (versions or [])] + [self.audit_key]
            if rule is not None:
                meta.append(d1.ArtifactStore.key("GET", f"https://{NWS_HOST}/stations/{rule.station_id}"))
            for key in meta:
                if self._retained(key):
                    artifacts["GAMMA_NWS_RULE_LABEL_METADATA"].append(self._artifact(key, "gamma" if "via=" in key else "complete"))  # type: ignore[arg-type]
            for hour in label_hours:
                for key in sorted(self.hours.keys_by_hour.get(hour, ())):
                    if self._retained(key):
                        kind, coverage = self._v3_kind(key, hour)
                        artifacts["GAMMA_NWS_RULE_LABEL_METADATA"].append(self._artifact(key, kind, coverage))
        for family in artifacts:
            unique = {a["content_sha256"] + "|" + a["endpoint"] + "|" + canonical(a["request_parameters"]).decode(): a for a in artifacts[family]}
            artifacts[family] = [unique[k] for k in sorted(unique)]
        gamma_captures = []
        for run, key, document, facts in versions or []:
            entry = self.store.index[key]
            cohort = None
            try:
                cohort = qd.parse_rule(document.get("description")).rule_cohort_id if not isinstance(facts, str) else None
            except qd.RuleExclusion:
                cohort = None
            gamma_captures.append({
                "capture_id": oa.capture_id(key, str(entry["sha256"]), run, str(entry["captured_at"])),
                "captured_at": entry["captured_at"], "run": run,
                "pre_close": document.get("closed") is not True,
                "fees_enabled_known": isinstance(document.get("feesEnabled"), bool),
                "tick_known": qd._decimal_text(document.get("orderPriceMinTickSize")) is not None,  # noqa: SLF001
                "min_size_known": qd._decimal_text(document.get("orderMinSize")) is not None,  # noqa: SLF001
                "parsed_rule_cohort_id": cohort,
            })
        tick_ids = []
        for hour in sorted(scanned):
            manifest = self.hours.manifests.get(hour)
            if manifest is None or hour in self.tick_failed:
                continue
            product = manifest.product("tick_size_change")
            key = d1.ArtifactStore.key("GET", d1.pf_url(v3.parquet_object_path(hour)), (product.byte_start, product.byte_end))
            if self._retained(key):
                entry = self.store.index[key]
                tick_ids.append(oa.capture_id(key, str(entry["sha256"]), self.store.run_of.get(key, self.run),
                                              str(entry.get("captured_at", ""))))
        if sealed_rows:
            self.new_sealed.append({"record_kind": "MARKET_SEALED_ROWS", "run": self.run, "target_date": day.isoformat(),
                                    "market_id": market_id, "rows": sealed_rows})
        body = {
            "entry_kind": "MARKET", "run": self.run, "target_date": day.isoformat(), "subject_id": market_id,
            "condition_id": candidate.condition_id if candidate else None,
            "market_exclusion": exclusion,
            "rows": row_bodies,
            "rule_cohort_id": rule.rule_cohort_id if rule else None,
            "station_id": rule.station_id if rule else None,
            "label_available_time": label.v3_resolution_received if label else None,
            "final_gamma_capture": final_key is not None,
            "execution": {"gamma_captures": gamma_captures, "tick_history_complete": bool(scanned) and not (scanned & self.tick_failed),
                          "tick_history_capture_ids": sorted(tick_ids)},
            "artifacts": artifacts,
            "pendulumflow_hours": {h: pf_hours[h] for h in sorted(pf_hours)},
            "has_sealed_rows": bool(sealed_rows),
        }
        self.new_bodies.append(body)
        return body

    def _date_entry(self, day: date, markets: Sequence[Mapping[str, object]]) -> None:
        iso = day.isoformat()
        exclusions: list[dict[str, str]] = []
        candidates: dict[str, str] = {}
        by_cp: dict[str, int] = {cp: 0 for cp in qd.CHECKPOINT_IDS}
        for market in sorted(markets, key=lambda m: (len(str(m["subject_id"])), str(m["subject_id"]))):
            if market["market_exclusion"]:
                exclusions.append(oa.oos_exclusion(iso, "MARKET", str(market["subject_id"]), str(market["market_exclusion"])))
                continue
            for row in market["rows"]:  # type: ignore[union-attr]
                if row["state"] == "ELIGIBLE":
                    candidates[str(row["row_id"])] = str(row["decision_time"])
                else:
                    exclusions.append(oa.oos_exclusion(iso, "ROW", oa.row_subject_id(str(market["subject_id"]), str(row["checkpoint_id"])),
                                                       str(row["reason"])))
        manifests = date_manifests(iso, markets, str(self.plan["repo_code_identity"]))
        ready_ids = manifests["ready_ids"]
        if candidates and not manifests["all_families_ready"]:
            for market in markets:
                for row in market.get("rows", []):  # type: ignore[union-attr]
                    if row["state"] == "ELIGIBLE":
                        exclusions.append(oa.oos_exclusion(iso, "ROW", oa.row_subject_id(str(market["subject_id"]), str(row["checkpoint_id"])),
                                                           "MARKET_HISTORY_SOURCE_INVALID"))
            candidates = {}
            ready_ids = []
        classification, reason = oa.classify_date(iso, candidates)
        if classification == oa.DATE_ELIGIBLE:
            for market in markets:
                for row in market.get("rows", []):  # type: ignore[union-attr]
                    if row["state"] == "ELIGIBLE":
                        by_cp[str(row["checkpoint_id"])] += 1
        else:
            exclusions.append(oa.oos_exclusion(iso, "DATE", iso, str(reason)))
        self.new_bodies.append({
            "entry_kind": "DATE", "run": self.run, "target_date": iso, "subject_id": iso,
            "classification": classification, "reason": reason,
            "market_ids": sorted((str(m["subject_id"]) for m in markets), key=lambda m: (len(m), m)),
            "row_decision_times": dict(sorted(candidates.items())) if classification == oa.DATE_ELIGIBLE else {},
            "eligible_rows_by_checkpoint": by_cp,
            "exclusions": sorted(exclusions, key=lambda e: (e["target_date"], e["subject_kind"], e["subject_id"])),
            "manifest_ids": sorted(ready_ids) if classification == oa.DATE_ELIGIBLE else [],
            "manifest_count": len(ready_ids) if classification == oa.DATE_ELIGIBLE else 0,
        })

    def run_all(self) -> None:
        phases = (self.phase_audit, self.phase_fee, self.phase_discovery, self.phase_gamma_capture, self.phase_dates)
        for phase in phases:
            try:
                phase()
            except BudgetExhausted as exhausted:
                self.budget_exhausted = exhausted.code
                break
        if self.hours is None:
            self.hours = d2.V3Hours(self.store, self.audit)  # type: ignore[arg-type]


def _final_capture(versions) -> tuple[tuple[str, qd.GammaFacts] | None, str | None]:
    """The earliest final Gamma capture, or a closed identity exclusion carried by any capture."""

    for _run, _key, _document, facts in versions:
        if isinstance(facts, str):
            return None, facts
    for _run, key, _document, facts in versions:
        if facts.winning_outcome is not None and facts.closed_time is not None:
            return (key, facts), None
    return None, None


def date_manifests(iso: str, markets: Sequence[Mapping[str, object]], repo_identity: str) -> dict[str, object]:
    """Deterministic <=256-item ready-subset provenance shards per source family of one date."""

    families = ("PENDULUMFLOW_MARKET_HISTORY", "NOAA_NDFD_WEATHER", "GAMMA_NWS_RULE_LABEL_METADATA")
    groups: dict[str, dict[str, qd.RetainedArtifact]] = {family: {} for family in families}
    outputs: list[dict[str, object]] = []
    checkpoints: list[datetime] = []
    labels: list[datetime] = []
    hours: dict[str, list[object]] = {}
    for market in markets:
        for family in families:
            for item in market.get("artifacts", {}).get(family, []):  # type: ignore[union-attr]
                artifact = qd.RetainedArtifact(**{**item, "request_parameters": tuple(tuple(p) for p in item["request_parameters"]),
                                                  "dq_flags": tuple(item["dq_flags"])})
                groups[family][artifact.content_sha256 + artifact.endpoint + repr(artifact.request_parameters)] = artifact
        hours.update(market.get("pendulumflow_hours", {}))  # type: ignore[arg-type]
        for row in market.get("rows", []):  # type: ignore[union-attr]
            if row["state"] == "ELIGIBLE":
                outputs.append({"market_id": market["subject_id"], "checkpoint_id": row["checkpoint_id"], "row_id": row["row_id"]})
                checkpoints.append(qd.parse_utc(row["decision_time"]))
        if market.get("label_available_time"):
            labels.append(qd.parse_utc(market["label_available_time"]))
    outputs.sort(key=lambda r: str(r["row_id"]))
    dataset_ids: list[str] = []
    if hours:
        ordered = sorted(hours)
        descriptor = build_external_dataset_descriptor(
            provider_id=v3.PROVIDER_ID, dataset_name=v3.DATASET_NAME, dataset_version="union-event-sorted-v1",
            source_class=v3.SOURCE_CLASS, coverage_start=qd.utc_text(v3.hour_start(ordered[0])),
            coverage_end=qd.utc_text(v3.hour_start(ordered[-1]) + timedelta(hours=1)),
            source_objects=[ExternalSourceObject(v3.parquet_object_path(h), str(hours[h][0]), int(hours[h][1]), h) for h in ordered][:1024],  # type: ignore[arg-type]
            source_schema_fingerprint_sha256=sha256_hex(canonical({k: list(v) for k, v in v3.READ_COLUMNS.items()})),
            source_timestamp_semantics="venue timestamp (exchange, milliseconds UTC)",
            receive_timestamp_semantics="timestamp_received (capture host receipt, microseconds UTC); ordering basis",
            event_types=list(v3.REQUIRED_EVENT_FAMILIES), known_gap_policy="archive audit PARTIAL/SINGLE-BY-DEFECT hours diagnostic only",
            quality_tier="THIRD_PARTY_EXTERNAL", importer_id=IMPORTER_ID, importer_version="1.0.0",
            license_id="UNSPECIFIED_PUBLIC_ARCHIVE", attribution="PendulumFlow Polymarket Orderbook Archive v3 (archive.pendulumflow.com)")
        if descriptor.is_valid:
            dataset_ids.append(descriptor.descriptor.external_dataset_id)  # type: ignore[union-attr]
    objects = [a for a in groups["NOAA_NDFD_WEATHER"].values() if "YDUZ98" in a.endpoint and a.public_available_time]
    if objects:
        times = sorted(str(a.public_available_time) for a in objects)
        descriptor = build_external_dataset_descriptor(
            provider_id=ndfd.PROVIDER_ID, dataset_name=ndfd.DATASET_NAME, dataset_version="wmo-grib2-pop12",
            source_class=ndfd.SOURCE_CLASS, coverage_start=times[0], coverage_end=times[-1],
            source_objects=[ExternalSourceObject(a.endpoint.split("/", 1)[1], a.content_sha256, a.byte_length, a.endpoint.rsplit("/", 1)[1])
                            for a in sorted(objects, key=lambda a: a.endpoint)][:1024],
            source_schema_fingerprint_sha256=sha256_hex(b"GRIB2 template 4.9 discipline 0 category 1 number 8"),
            source_timestamp_semantics="GRIB reference time and forecast valid interval (section 1/4)",
            receive_timestamp_semantics="S3 LastModified conservative public availability bound",
            event_types=["PoP12"], known_gap_policy="missing vintages excluded, never interpolated",
            quality_tier="OFFICIAL", importer_id=IMPORTER_ID, importer_version="1.0.0",
            license_id="US_GOVERNMENT_PUBLIC_DOMAIN", attribution="NOAA NDFD via NOAA Open Data Dissemination (noaa-ndfd-pds)")
        if descriptor.is_valid:
            dataset_ids.append(descriptor.descriptor.external_dataset_id)  # type: ignore[union-attr]
    default_cutoff = datetime.fromisoformat(iso + "T00:00:00+00:00") + timedelta(days=1)
    ready_ids: list[str] = []
    families_ready: set[str] = set()
    manifests = []
    for family in families:
        refs_ok, refs_degraded = [], []
        for key in sorted(groups[family]):
            ref = qd.raw_reference(groups[family][key])
            (refs_ok if ref.dq_flags == ("OK",) else refs_degraded).append(ref)
        cutoff = max(checkpoints) if checkpoints else default_cutoff
        if family == "GAMMA_NWS_RULE_LABEL_METADATA" and labels:
            cutoff = max(labels)
        ready_manifests = qd.build_shard_manifests(target_date=iso, shard_kind=family, references=refs_ok, output_records=outputs,
                                                   information_cutoff=cutoff, repo_code_identity=repo_identity,
                                                   dataset_refs=dataset_ids)
        ready, _diagnostic = qd.split_ready_manifests(ready_manifests)
        manifests.extend(ready_manifests)
        if ready and len(ready) == len(ready_manifests):
            ready_ids.extend(m.research_provenance_manifest_id for m in ready)
            families_ready.add(family)
    return {"ready_ids": sorted(ready_ids), "all_families_ready": families_ready == set(families), "manifests": manifests}


# ── Commands: accrue ──────────────────────────────────────────────────────────


def _runs_dir(env: Environment) -> Path:
    return env.workspace / RUNS_DIRNAME


def _run_dir(env: Environment, run: int) -> Path:
    return _runs_dir(env) / f"run-{run:03d}"


def _run_records(env: Environment) -> list[dict[str, object]]:
    records = []
    root = _runs_dir(env)
    if not root.exists():
        return []
    for path in sorted(root.iterdir()):
        if not re.fullmatch(r"run-\d{3}", path.name):
            raise OperatorStop("STATE_DRIFT")
        try:
            records.append(read_json(path / RUN_FILENAME))  # type: ignore[arg-type]
        except (OSError, ValueError):
            raise OperatorStop("STATE_DRIFT") from None
    for number, record in enumerate(records, start=1):
        if record.get("run") != number or (record.get("status") != "COMMITTED" and number != len(records)):
            raise OperatorStop("STATE_DRIFT")
    return records


def _network_of(env: Environment, run: int) -> dict[str, object]:
    path = _run_dir(env, run) / RUN_NETWORK_FILENAME
    return read_json(path) if path.exists() else AccrualLedger().to_mapping()  # type: ignore[return-value]


def _network_visible(ledgers: Sequence[Mapping[str, object]], hours: int, reused: int, new: int, failed: int) -> dict[str, object]:
    total: dict[str, object] = {"attempts": 0, "bytes": 0, "retries": 0, "throttle_retries": 0, "transport_retries": 0,
                                "backoff_seconds": 0, "max_single_response": 0, "refusals": 0, "attempts_by_host": {},
                                "statuses": {}}
    for item in ledgers:
        for field in ("attempts", "bytes", "retries", "throttle_retries", "transport_retries", "backoff_seconds", "refusals"):
            total[field] = int(total[field]) + int(item[field])  # type: ignore[arg-type]
        total["max_single_response"] = max(int(total["max_single_response"]), int(item["max_single_response"]))  # type: ignore[arg-type]
        for name in ("attempts_by_host", "statuses"):
            for key, value in item[name].items():  # type: ignore[union-attr]
                total[name][key] = total[name].get(key, 0) + int(value)  # type: ignore[union-attr,index]
    return {**total, "attempts_by_host": dict(sorted(total["attempts_by_host"].items())),  # type: ignore[union-attr]
            "statuses": dict(sorted(total["statuses"].items())), "pendulumflow_hours": hours,  # type: ignore[union-attr]
            "artifacts_reused": reused, "artifacts_new": new, "failed_reads": failed}


def _verify_existing(env: Environment, entries: Sequence[Mapping[str, object]], sealed: Sequence[Mapping[str, object]]) -> None:
    """Before any network acquisition: both chains verify and every raw blob referenced by an
    already terminal entry re-hashes to its digest."""

    try:
        oa.verify_chain(entries)
        oa.verify_chain(sealed, oa.SEALED_RECORD_PREFIX)
    except oa.AccrualError:
        raise OperatorStop("STATE_DRIFT") from None
    raw = env.workspace / "raw"
    for entry in entries:
        for items in (entry.get("artifacts") or {}).values():  # type: ignore[union-attr]
            for item in items:
                digest = str(item["content_sha256"])
                try:
                    if sha256_hex((raw / digest).read_bytes()) != digest:
                        raise OperatorStop("STATE_DRIFT")
                except OSError:
                    raise OperatorStop("STATE_DRIFT") from None


def _state(env: Environment) -> dict[str, object]:
    path = env.workspace / STATE_FILENAME
    try:
        state = read_json(path)
    except (OSError, ValueError):
        raise OperatorStop("STATE_DRIFT") from None
    if not isinstance(state, dict) or state.get("status") not in oa.STATES:
        raise OperatorStop("STATE_DRIFT")
    return state


def build_accrue_report(*, plan: Mapping[str, object], run: int, resumed: bool, as_of: datetime,
                        entries: Sequence[Mapping[str, object]], pipeline: AccrualPipeline,
                        run_network: Mapping[str, object], cumulative_networks: Sequence[Mapping[str, object]],
                        cumulative_hours: int, store: AccrualStore) -> tuple[dict[str, object], oa.PrefixState]:
    markets = [e for e in entries if e["entry_kind"] == "MARKET"]
    dates = [e for e in entries if e["entry_kind"] == "DATE"]
    states = {str(e["target_date"]): str(e["classification"]) for e in dates}
    prefix = oa.stable_prefix(states)
    rows_by_date = {str(e["target_date"]): list(e["row_decision_times"]) for e in dates}  # type: ignore[arg-type]
    decision = oa.seal_decision(prefix, rows_by_date)
    manifest_counts = [int(next(e for e in dates if e["target_date"] == d)["manifest_count"]) for d in prefix.eligible_dates]  # type: ignore[arg-type]
    n2 = int(plan["data02"]["n2"])  # type: ignore[index]
    coverage: dict[str, int] = {}
    for klass in pipeline.coverage_seen.values():
        coverage[klass] = coverage.get(klass, 0) + 1
    published_required = [oa.discovery_hour(day, hh) for day in oa.scan_days() for hh in oa.DISCOVERY_HOURS_UTC
                          if v3.hour_start(oa.discovery_hour(day, hh)) + timedelta(hours=1) <= as_of]
    counts = oa.structural_counts(markets, dates, discovered_markets=len(pipeline.discovered_in_window),
                                  outside_window_markets=len(pipeline.outside_window),
                                  discovery_hours_read=len(pipeline.discovery_ok),
                                  discovery_hours_pending=len([h for h in published_required if h not in pipeline.discovery_ok]),
                                  coverage_classes=coverage)
    terminal_markets = {str(e["subject_id"]) for e in markets}
    exec_states = {cls: "MISSING" for cls in oa.EXECUTION_CLASSES}
    if prefix.eligible_dates:
        captured = [qd.parse_utc(v["captured_at"]) for v in store.index.values() if v.get("captured_at")]
        cutoff = max(captured) if captured else as_of
        exec_states = {cls: str(v["state"]) for cls, v in execution_for(env_store=store, entries=entries,
                                                                         dates=prefix.eligible_dates, cutoff=cutoff).items()}
    run_view = {k: v for k, v in store.index.items() if store.run_of.get(k) == run}
    report = {
        "kind": "ACCRUE", "wp_id": WP_ID, "status": "ACCRUED", "state": oa.STATE_INCOMPLETE, "run": run, "resumed": resumed,
        "as_of": oa.utc_text(as_of), "plan_sha256": oa.PLAN_SHA256, "workspace_plan_sha256": _plan_sha(plan),
        "ledger_entries": len(entries), "budget_exhausted": pipeline.budget_exhausted,
        "counts": counts,
        "prefix": {"length": len(prefix.eligible_dates), "target": oa.TARGET_EFFECTIVE_DATES,
                   "earliest_pending_date": prefix.earliest_pending_date, "pending_dates": prefix.pending_dates,
                   "pending_markets": len(pipeline.discovered_in_window - terminal_markets), "seal_decision": decision},
        "provenance": {"n2": n2, "prefix_manifests": sum(manifest_counts),
                       "projected_final_manifests": oa.projected_manifest_count(n2, manifest_counts),
                       "ceiling": oa.MAX_QUALIFICATION_PROVENANCE_MANIFESTS},
        "execution_evidence_states": exec_states,
        "network": {
            "run": _network_visible([run_network], len(pipeline.touched_hours),
                                    len([k for k in store.used if store.run_of.get(k, run) < run]),
                                    len([k for k, v in run_view.items() if "failed" not in v]),
                                    len([k for k, v in run_view.items() if "failed" in v])),
            "cumulative": _network_visible(cumulative_networks, cumulative_hours, 0,
                                           len([v for v in store.index.values() if "failed" not in v]),
                                           len([v for v in run_view.values() if "failed" in v])),
        },
    }
    return oa.validate_visible_report(report), prefix


def execution_for(*, env_store: AccrualStore, entries: Sequence[Mapping[str, object]], dates: Sequence[str],
                  cutoff: datetime) -> dict[str, dict[str, object]]:
    by_market = {str(e["subject_id"]): e for e in entries if e["entry_kind"] == "MARKET"}
    date_entries = {str(e["target_date"]): e for e in entries if e["entry_kind"] == "DATE"}
    markets = []
    rows_total = 0
    for day in dates:
        for market_id in date_entries[day]["market_ids"]:  # type: ignore[union-attr]
            market = by_market[market_id]
            eligible = [r for r in market["rows"] if r["state"] == "ELIGIBLE"]  # type: ignore[union-attr]
            if market["market_exclusion"] or not eligible:
                continue
            rows_total += len(eligible)
            markets.append({"market_id": market_id, "rule_cohort_id": market["rule_cohort_id"],
                            "gamma_captures": market["execution"]["gamma_captures"],  # type: ignore[index]
                            "tick_history_complete": market["execution"]["tick_history_complete"],  # type: ignore[index]
                            "tick_history_capture_ids": market["execution"]["tick_history_capture_ids"]})  # type: ignore[index]
    fees = []
    for run, key, entry in env_store.versions(FEE_URL):
        if "failed" in entry:
            continue
        fees.append({"capture_id": oa.capture_id(key, str(entry["sha256"]), run, str(entry["captured_at"])),
                     "captured_at": entry["captured_at"], "url": FEE_URL,
                     "contract_valid": oa.fee_document_valid(FEE_URL, int(entry.get("status", 0)), env_store.read_entry(key))})  # type: ignore[arg-type]
    # Every OOS row carries its decision-time top-of-book bid/ask (the B0 evidence); depth is never captured.
    return oa.classify_execution_evidence(markets, fees, cutoff, rows_total, rows_total)


def run_pipeline(env: Environment, plan: Mapping[str, object], run: int, as_of: datetime,
                 prior: Sequence[Mapping[str, object]], prior_hours: frozenset[str], *, replay: bool,
                 ledger: AccrualLedger | None, budget_replay: str | None = None) -> tuple[AccrualPipeline, AccrualStore]:
    transport = None if replay else d2.BoundedTransport(ledger, env.fetch, env.sleeper())  # type: ignore[arg-type]
    store = AccrualStore(env.workspace, run, transport,
                         None if replay else (env.gamma_client_factory or d1.default_gamma_client_factory),
                         replay=replay, clock=env.clock, sleep=env.sleeper(), fetch=env.fetch)
    if replay and budget_replay:
        original_get, original_gamma, original_fee = store.get, store.gamma_market, store.fee_document

        def get_or_exhaust(*args, **kwargs):
            try:
                return original_get(*args, **kwargs)
            except ReplayMissing:
                raise BudgetExhausted(budget_replay) from None

        def gamma_or_exhaust(*args, **kwargs):
            try:
                return original_gamma(*args, **kwargs)
            except ReplayMissing:
                raise BudgetExhausted(budget_replay) from None

        def fee_or_exhaust(*args, **kwargs):
            try:
                return original_fee(*args, **kwargs)
            except ReplayMissing:
                raise BudgetExhausted(budget_replay) from None

        store.get, store.gamma_market, store.fee_document = get_or_exhaust, gamma_or_exhaust, fee_or_exhaust  # type: ignore[method-assign]
    pipeline = AccrualPipeline(store, plan, env.decoder(), ledger, run=run, as_of=as_of, prior_entries=prior,
                               prior_hours=prior_hours)
    pipeline.run_all()
    return pipeline, store


def command_accrue(env: Environment) -> dict[str, object]:
    now = env.clock()
    if now < oa.parse_utc(oa.OOS_START):
        raise OperatorStop("ACCRUAL_BEFORE_OOS_START")
    plan = load_plan(env)
    verify_plan_freeze(env)
    state = _state(env)
    if state["status"] in oa.FINAL_STATES:
        raise OperatorStop("ACCRUAL_FINALIZED")
    if state.get("hard_stop"):
        raise OperatorStop(str(state["hard_stop"]))
    records = _run_records(env)
    committed = [r for r in records if r.get("status") == "COMMITTED"]
    resumed = bool(records) and records[-1].get("status") != "COMMITTED"
    run = len(records) if resumed else len(records) + 1
    if not resumed and len(committed) >= MAX_ACCRUE_RUNS:
        raise OperatorStop("ACCRUAL_BUDGET_EXHAUSTED")
    networks = [_network_of(env, int(r["run"])) for r in committed]  # type: ignore[arg-type]
    prior_attempts = sum(int(n["attempts"]) for n in networks)  # type: ignore[arg-type]
    prior_bytes = sum(int(n["bytes"]) for n in networks)  # type: ignore[arg-type]
    if prior_attempts >= CUM_MAX_ATTEMPTS or prior_bytes >= CUM_MAX_BYTES:
        raise OperatorStop("ACCRUAL_BUDGET_EXHAUSTED")
    # Entries of an uncommitted (crashed) run were never committed: they are discarded and re-derived.
    entries = [e for e in _jsonl(env.workspace / LEDGER_FILENAME) if int(e["run"]) < run]  # type: ignore[arg-type]
    sealed = [e for e in _jsonl(env.workspace / SEALED_DIRNAME / SEALED_RECORDS_FILENAME) if int(e["run"]) < run]  # type: ignore[arg-type]
    _verify_existing(env, entries, sealed)
    prior_hours = frozenset(h for r in committed for h in r.get("pendulumflow_hours", []))  # type: ignore[union-attr]
    run_dir = _run_dir(env, run)
    if resumed:
        as_of = oa.parse_utc(records[-1]["as_of"])
        ledger = AccrualLedger.from_mapping(_network_of(env, run))
    else:
        as_of = now.replace(microsecond=0)
        ledger = AccrualLedger()
        write_json_atomic(run_dir / RUN_FILENAME, {"run": run, "status": "RUNNING", "as_of": oa.utc_text(as_of),
                                                   "repo_code_identity": plan["repo_code_identity"]})
    ledger.prior_attempts, ledger.prior_bytes, ledger.scope = prior_attempts, prior_bytes, "RUN"
    ledger.max_attempts, ledger.max_bytes, ledger.max_single = RUN_MAX_ATTEMPTS, RUN_MAX_BYTES, MAX_SINGLE_RESPONSE
    try:
        pipeline, store = run_pipeline(env, plan, run, as_of, entries, prior_hours, replay=False, ledger=ledger)
    finally:
        write_json_atomic(run_dir / RUN_NETWORK_FILENAME, ledger.to_mapping())
    new_entries = oa.chain_append(entries, pipeline.new_bodies)
    oa.assert_terminal_entries_unchanged(entries, new_entries)
    new_sealed = oa.chain_append(sealed, pipeline.new_sealed, oa.SEALED_RECORD_PREFIX)
    network = ledger.to_mapping()
    hours = sorted(prior_hours | pipeline.touched_hours)
    report, prefix = build_accrue_report(plan=plan, run=run, resumed=resumed, as_of=as_of, entries=new_entries, pipeline=pipeline,
                                         run_network=network, cumulative_networks=[*networks, network],
                                         cumulative_hours=len(hours), store=store)
    _write_jsonl_atomic(env.workspace / SEALED_DIRNAME / SEALED_RECORDS_FILENAME, new_sealed)
    _write_jsonl_atomic(env.workspace / LEDGER_FILENAME, new_entries)
    write_json_atomic(run_dir / RUN_REPORT_FILENAME, report)
    hard_stop = None
    if pipeline.budget_exhausted and pipeline.budget_exhausted.startswith("CUMULATIVE_"):
        hard_stop = "ACCRUAL_BUDGET_EXHAUSTED"
    elif report["provenance"]["projected_final_manifests"] > oa.MAX_QUALIFICATION_PROVENANCE_MANIFESTS:  # type: ignore[index]
        hard_stop = "QUAL_PROVENANCE_LIMIT_EXCEEDED_UNAVOIDABLE"
    write_json_atomic(run_dir / RUN_FILENAME, {
        "run": run, "status": "COMMITTED", "as_of": oa.utc_text(as_of), "repo_code_identity": plan["repo_code_identity"],
        "budget_exhausted": pipeline.budget_exhausted, "pendulumflow_hours": sorted(pipeline.touched_hours),
        "ledger_head": _head(new_entries), "ledger_entries": len(new_entries),
        "sealed_head": str(new_sealed[-1]["entry_hash"]) if new_sealed else oa.LEDGER_GENESIS,
        "seal_decision": report["prefix"]["seal_decision"],  # type: ignore[index]
    })
    write_json_atomic(env.workspace / STATE_FILENAME, {"status": oa.STATE_INCOMPLETE, "runs_committed": run,
                                                       "ledger_head": _head(new_entries),
                                                       "seal_decision": report["prefix"]["seal_decision"],  # type: ignore[index]
                                                       "hard_stop": hard_stop})
    del prefix
    if hard_stop:
        raise OperatorStop(hard_stop)
    return report


# ── Commands: seal / verify-final ─────────────────────────────────────────────


def _head(entries: Sequence[Mapping[str, object]]) -> str:
    return str(entries[-1]["entry_hash"]) if entries else oa.LEDGER_GENESIS


def _raw_index_sha(env: Environment) -> str:
    path = env.workspace / INDEX_FILENAME
    return sha256_hex(path.read_bytes() if path.exists() else b"")


def build_seal(env: Environment, plan: Mapping[str, object], entries: Sequence[Mapping[str, object]],
               sealed: Sequence[Mapping[str, object]], seal_time: datetime) -> tuple[dict[str, object], dict[str, object]]:
    """Pure (zero network) seal derivation from the committed ledger, sealed store and raw index."""

    dates = [e for e in entries if e["entry_kind"] == "DATE"]
    prefix = oa.stable_prefix({str(e["target_date"]): str(e["classification"]) for e in dates})
    rows_by_date = {str(e["target_date"]): list(e["row_decision_times"]) for e in dates}  # type: ignore[arg-type]
    decision = oa.seal_decision(prefix, rows_by_date)
    if decision == oa.SEAL_NOT_READY:
        raise OperatorStop("NOT_SEALABLE")
    by_date = {str(e["target_date"]): e for e in dates}
    markets = {str(e["subject_id"]): e for e in entries if e["entry_kind"] == "MARKET"}
    last = prefix.eligible_dates[-1] if prefix.complete else oa.window_dates()[-1]
    exclusions = [dict(x) for day in oa.window_dates() if day <= last for x in by_date[day]["exclusions"]]  # type: ignore[union-attr]
    times = {r: t for day in prefix.eligible_dates for r, t in by_date[day]["row_decision_times"].items()}  # type: ignore[union-attr]
    manifest_ids: list[str] = []
    for day in prefix.eligible_dates:
        rebuilt = date_manifests(day, [markets[m] for m in by_date[day]["market_ids"]], str(plan["repo_code_identity"]))  # type: ignore[union-attr]
        if rebuilt["ready_ids"] != by_date[day]["manifest_ids"]:
            raise OperatorStop("MEMBERSHIP_REPRODUCTION_FAILED")
        manifest_ids.extend(rebuilt["ready_ids"])  # type: ignore[arg-type]
    n2 = int(plan["data02"]["n2"])  # type: ignore[index]
    if n2 + len(manifest_ids) > oa.MAX_QUALIFICATION_PROVENANCE_MANIFESTS:
        raise OperatorStop("QUAL_PROVENANCE_LIMIT_EXCEEDED_UNAVOIDABLE")
    store = AccrualStore(env.workspace, 10 ** 6, None, replay=True)
    execution = execution_for(env_store=store, entries=entries, dates=prefix.eligible_dates, cutoff=seal_time)
    head = str(entries[-1]["entry_hash"]) if entries else oa.LEDGER_GENESIS
    bundle = oa.build_data03_bundle(ledger_head=head, oos_target_dates=prefix.eligible_dates, oos_row_ids=list(times),
                                    oos_exclusions=exclusions, provenance_manifest_ids=manifest_ids,
                                    execution_evidence=execution, raw_index_sha256=_raw_index_sha(env), terminal=decision)
    membership = None
    if prefix.complete:
        preimage = oa.expected_membership(dates, prefix, str(bundle["bundle_id"]))
        membership = {"preimage": preimage, "oos_membership_id": oa.membership_id(preimage)}
    values: dict[str, dict[str, str]] = {ref: {} for ref in oa.FEATURE_REFS}
    labels: dict[str, dict[str, object]] = {}
    for record in sealed:
        for row in record["rows"]:  # type: ignore[union-attr]
            if row["row_id"] in times:
                for ref in oa.FEATURE_REFS:
                    values[ref][str(row["row_id"])] = str(row["features"][ref])
                labels[str(row["row_id"])] = dict(row["label"])
    internal = {
        "seal_time": oa.utc_text(seal_time), "decision": decision, "bundle": bundle, "membership": membership,
        "feature_column_ids": {ref: oa.feature_column_id(ref, values[ref]) for ref in oa.FEATURE_REFS if values[ref]},
        "label_store_id": oa.label_store_id(labels) if labels else None,
        "sealed_head": str(sealed[-1]["entry_hash"]) if sealed else oa.LEDGER_GENESIS,
        "n2": n2, "prospective_manifests": len(manifest_ids),
    }
    visible = oa.validate_visible_report({
        "kind": "SEAL", "wp_id": WP_ID, "status": "SEALED", "state": decision, "plan_sha256": oa.PLAN_SHA256, "ledger_head": head,
        "oos_membership_id": membership["oos_membership_id"] if membership else None, "data03_bundle_id": str(bundle["bundle_id"]),
        "oos_target_dates": len(prefix.eligible_dates), "oos_rows": len(times), "oos_exclusions": len(exclusions),
        "end_time": membership["preimage"]["end_time"] if membership else None,  # type: ignore[index]
        "provenance": {"n2": n2, "prospective": len(manifest_ids), "total": n2 + len(manifest_ids),
                       "ceiling": oa.MAX_QUALIFICATION_PROVENANCE_MANIFESTS},
        "execution_evidence_states": {cls: str(v["state"]) for cls, v in execution.items()},
    })
    return internal, visible


def command_seal(env: Environment) -> dict[str, object]:
    restore = d1._forbid_network()  # noqa: SLF001
    try:
        plan = load_plan(env)
        state = _state(env)
        if state["status"] in oa.FINAL_STATES or (env.workspace / SEALED_DIRNAME / SEAL_FILENAME).exists():
            raise OperatorStop("ACCRUAL_FINALIZED")
        if state.get("hard_stop"):
            raise OperatorStop(str(state["hard_stop"]))
        records = _run_records(env)
        if not records or records[-1].get("status") != "COMMITTED":
            raise OperatorStop("NO_COMMITTED_RUN")
        entries = _jsonl(env.workspace / LEDGER_FILENAME)
        sealed = _jsonl(env.workspace / SEALED_DIRNAME / SEALED_RECORDS_FILENAME)
        _verify_existing(env, entries, sealed)
        internal, visible = build_seal(env, plan, entries, sealed, env.clock().replace(microsecond=0))
        again, _visible = build_seal(env, plan, entries, sealed, oa.parse_utc(internal["seal_time"]))
        if canonical(again) != canonical(internal):
            raise OperatorStop("MEMBERSHIP_REPRODUCTION_FAILED")
        write_json_atomic(env.workspace / SEALED_DIRNAME / SEAL_FILENAME, internal)
        write_json_atomic(env.workspace / SEAL_REPORT_FILENAME, visible)
        write_json_atomic(env.workspace / STATE_FILENAME, {"status": internal["decision"], "runs_committed": len(records),
                                                           "ledger_head": visible["ledger_head"], "hard_stop": None})
        return visible
    finally:
        restore()


def verify_network_accounting(networks: Sequence[Mapping[str, object]]) -> None:
    for item in networks:
        if (item["attempts"] != sum(item["attempts_by_host"].values())  # type: ignore[union-attr]
                or item["bytes"] != sum(item["bytes_by_host"].values())  # type: ignore[union-attr]
                or item["attempts"] != sum(item["statuses"].values())  # type: ignore[union-attr]
                or set(item["attempts_by_host"]) - ALLOWED_HOSTS  # type: ignore[arg-type]
                or int(item["attempts"]) > RUN_MAX_ATTEMPTS or int(item["max_single_response"]) > MAX_SINGLE_RESPONSE):  # type: ignore[arg-type]
            raise OperatorStop("VERIFY_FAILED")
    if (sum(int(n["attempts"]) for n in networks) > CUM_MAX_ATTEMPTS  # type: ignore[arg-type]
            or sum(int(n["bytes"]) for n in networks) > CUM_MAX_BYTES + MAX_SINGLE_RESPONSE):  # type: ignore[arg-type]
        raise OperatorStop("VERIFY_FAILED")


def command_verify(env: Environment) -> dict[str, object]:
    restore = d1._forbid_network()  # noqa: SLF001
    try:
        plan = load_plan(env)
        state = _state(env)
        records = _run_records(env)
        committed = [r for r in records if r.get("status") == "COMMITTED"]
        if not committed:
            raise OperatorStop("NO_COMMITTED_RUN")
        last = int(committed[-1]["run"])  # type: ignore[arg-type]
        entries = [e for e in _jsonl(env.workspace / LEDGER_FILENAME) if int(e["run"]) <= last]  # type: ignore[arg-type]
        sealed = [e for e in _jsonl(env.workspace / SEALED_DIRNAME / SEALED_RECORDS_FILENAME) if int(e["run"]) <= last]  # type: ignore[arg-type]
        _verify_existing(env, entries, sealed)
        rehashed = 0
        for record in _jsonl(env.workspace / INDEX_FILENAME):
            entry = record["entry"]
            if "failed" in entry:  # type: ignore[operator]
                continue
            digest = str(entry["sha256"])  # type: ignore[index]
            if sha256_hex((env.workspace / "raw" / digest).read_bytes()) != digest:
                raise OperatorStop("VERIFY_FAILED")
            rehashed += 1
        replayed: list[dict[str, object]] = []
        replayed_sealed: list[dict[str, object]] = []
        hours: set[str] = set()
        networks = []
        for record in committed:
            run = int(record["run"])  # type: ignore[arg-type]
            try:
                pipeline, store = run_pipeline(env, plan, run, oa.parse_utc(record["as_of"]), replayed, frozenset(hours),
                                               replay=True, ledger=None,
                                               budget_replay=str(record["budget_exhausted"]) if record.get("budget_exhausted") else None)
            except (ReplayMissing, d1._NetworkForbidden):  # noqa: SLF001
                raise OperatorStop("VERIFY_FAILED") from None
            if pipeline.budget_exhausted != record.get("budget_exhausted"):
                raise OperatorStop("VERIFY_FAILED")
            replayed = oa.chain_append(replayed, pipeline.new_bodies)
            replayed_sealed = oa.chain_append(replayed_sealed, pipeline.new_sealed, oa.SEALED_RECORD_PREFIX)
            if sorted(pipeline.touched_hours) != list(record.get("pendulumflow_hours", [])):  # type: ignore[arg-type]
                raise OperatorStop("VERIFY_FAILED")
            hours |= pipeline.touched_hours
            network = _network_of(env, run)
            networks.append(network)
            report, _prefix = build_accrue_report(plan=plan, run=run, resumed=False, as_of=oa.parse_utc(record["as_of"]),
                                                  entries=replayed, pipeline=pipeline, run_network=network,
                                                  cumulative_networks=list(networks), cumulative_hours=len(hours), store=store)
            stored = read_json(_run_dir(env, run) / RUN_REPORT_FILENAME)
            comparable = {k: v for k, v in stored.items() if k not in ("resumed", "network")}  # type: ignore[union-attr]
            if canonical({k: v for k, v in report.items() if k not in ("resumed", "network")}) != canonical(comparable):
                raise OperatorStop("VERIFY_FAILED")
            if record.get("ledger_head") != _head(replayed):
                raise OperatorStop("VERIFY_FAILED")
        if canonical(replayed) != canonical(entries) or canonical(replayed_sealed) != canonical(sealed):
            raise OperatorStop("VERIFY_FAILED")
        verify_network_accounting(networks)
        membership_id = bundle_id = None
        seal_path = env.workspace / SEALED_DIRNAME / SEAL_FILENAME
        if state["status"] in oa.FINAL_STATES:
            stored_seal = read_json(seal_path)
            internal, _visible = build_seal(env, plan, entries, sealed, oa.parse_utc(stored_seal["seal_time"]))  # type: ignore[index]
            if canonical(internal) != canonical(stored_seal) or internal["decision"] != state["status"]:
                raise OperatorStop("MEMBERSHIP_REPRODUCTION_FAILED")
            bundle_id = str(internal["bundle"]["bundle_id"])  # type: ignore[index]
            if internal["membership"]:
                membership_id = str(internal["membership"]["oos_membership_id"])  # type: ignore[index]
        elif seal_path.exists():
            raise OperatorStop("VERIFY_FAILED")
        report = oa.validate_visible_report({
            "kind": "VERIFY_FINAL", "wp_id": WP_ID, "status": "VERIFIED", "state": state["status"], "network_calls": 0,
            "runs_replayed": len(committed), "raw_rehashed": rehashed,
            "ledger_head": str(entries[-1]["entry_hash"]) if entries else oa.LEDGER_GENESIS,
            "oos_membership_id": membership_id, "data03_bundle_id": bundle_id, "plan_sha256": oa.PLAN_SHA256,
            "network": {"cumulative": _network_visible(networks, len(hours), 0, rehashed, 0)},
        })
        write_json_atomic(env.workspace / VERIFY_FILENAME, report)
        return report
    except OSError:
        raise OperatorStop("VERIFY_FAILED") from None
    finally:
        restore()


# ── Commands: probe-sources (one bounded pre-OOS probe) ───────────────────────


def command_probe(env: Environment) -> dict[str, object]:
    if env.clock() >= oa.parse_utc(oa.OOS_START):
        raise OperatorStop("PROBE_AFTER_OOS_START")
    root = env.probe_workspace
    if (root / PROBE_FILENAME).exists() or (root.exists() and any(root.iterdir())):
        raise OperatorStop("PROBE_ALREADY_RECORDED")
    verify_plan_freeze(env)
    ledger = probe_ledger()
    transport = d2.BoundedTransport(ledger, env.fetch, env.sleeper())
    store = AccrualStore(root, 1, transport, env.gamma_client_factory or d1.default_gamma_client_factory,
                         clock=env.clock, sleep=env.sleeper(), fetch=env.fetch)
    checks: dict[str, str] = {}
    hours_touched: set[str] = set()
    failure: str | None = None
    try:
        key, entry = store.fee_document(ledger)
        if "failed" in entry or not oa.fee_document_valid(FEE_URL, int(entry.get("status", 0)), store.read_entry(key)):  # type: ignore[arg-type]
            raise OperatorStop("EXECUTION_TERMS_SOURCE_UNAVAILABLE")
        checks["fee_document"] = "PASS"
        audit = v3.parse_audit_page(store.get(d1.pf_url("audit"), accept="text/html", media_type="text/html"))
        checks["pendulumflow_audit"] = "PASS"
        hours = d2.V3Hours(store, audit)  # type: ignore[arg-type]
        for hour in (PROBE_HOUR, PROBE_MARKET_HOUR):
            if v3.hour_start(hour) >= oa.parse_utc(oa.OOS_START):
                raise OperatorStop("SOURCE_CONTRACT_DRIFT")
        hours_touched.add(PROBE_HOUR)
        events = [e for e in hours.read("probe", PROBE_HOUR, "new_market") if oa.is_rain_family_event(e)]
        candidates, _bad = qd.candidates_from_new_market(events)
        candidates = tuple(c for c in candidates if qd.parse_rain_slug(c.slug) is not None)
        if not candidates:
            raise OperatorStop("SOURCE_CONTRACT_DRIFT")
        checks["pendulumflow_discovery"] = "PASS"
        candidate = candidates[0]
        gamma = qd.normalize_gamma_market(store.gamma_market(candidate.market_id, ledger), candidate)
        checks["gamma_identity"] = "PASS"
        rule = qd.parse_rule(gamma.description)
        checks["rule_semantics"] = rule.finality_policy
        station = ndfd.parse_nws_station(json.loads(store.get(f"https://{NWS_HOST}/stations/{rule.station_id}",
                                                              accept="application/geo+json",
                                                              media_type="application/geo+json").decode("utf-8")), rule.station_id)
        del station
        checks["nws_station"] = "PASS"
        receive = qd.parse_utc(candidate.first_received)
        checkpoint = qd.checkpoint_a(receive, qd.gamma_open_time_if_trustworthy(gamma.open_time, receive))
        prefix = ndfd.day_prefix(checkpoint.date())
        listing = ndfd.parse_s3_listing(store.get(f"https://{NDFD_HOST}/?" + urllib.parse.urlencode({"list-type": "2", "prefix": prefix}),
                                                  accept="application/xml", media_type="application/xml"), prefix)
        vintage = ndfd.select_vintage(listing, checkpoint, qd.NDFD_VINTAGE_LOOKBACK)
        if vintage is None or vintage.byte_length > PROBE_MAX_SINGLE_RESPONSE:
            raise OperatorStop("SOURCE_CONTRACT_DRIFT")
        data = d1.NdfdAccess(store, env.decode_fn or ndfd.decode_pop12_message).object_bytes(vintage)  # type: ignore[arg-type]
        slices = ndfd.scan_messages(data)
        for piece in slices:
            ndfd.parse_pop12_header(ndfd.message_bytes(data, piece))
        checks["ndfd_listing_object"] = "PASS"
        hours_touched.add(PROBE_MARKET_HOUR)
        if len(hours_touched) > PROBE_MAX_PENDULUM_HOURS:
            raise OperatorStop("SOURCE_CONTRACT_DRIFT")
        bba = hours.read("probe", PROBE_MARKET_HOUR, "best_bid_ask", [candidate.condition_id])
        if not any(e.asset_id in candidate.asset_ids for e in bba):
            raise OperatorStop("SOURCE_CONTRACT_DRIFT")
        checks["pendulumflow_targeted_read"] = "PASS"
    except OperatorStop as stop:
        failure = stop.code
    except (TransportFailure, TransportRefused, BudgetExhausted, ReplayMissing, v3.PendulumFlowError, ndfd.NdfdError,
            qd.ReadinessError, qd.RuleExclusion, d2.SourceReadFailed, ValueError, KeyError):
        failure = "SOURCE_CONTRACT_DRIFT"
    network = _network_visible([ledger.to_mapping()], len(hours_touched), 0,
                               len([v for v in store.index.values() if "failed" not in v]),
                               len([v for v in store.index.values() if "failed" in v]))
    result = {"kind": "PROBE", "wp_id": WP_ID, "status": "PROBE_PASS", "plan_sha256": oa.PLAN_SHA256,
              "checks": checks, "network": network, "oos_or_prospective_data_created": False}
    if failure is not None:
        write_json_atomic(root / PROBE_FILENAME, {**result, "status": "PROBE_FAILED", "failure_code": failure,
                                                  "ledger": ledger.to_mapping()})
        raise OperatorStop(failure if failure in STOP_CODES else "SOURCE_CONTRACT_DRIFT")
    report = oa.validate_visible_report(result)
    write_json_atomic(root / PROBE_FILENAME, {**report, "ledger": ledger.to_mapping()})
    return report


COMMANDS = {
    "prepare": command_prepare,
    "probe-sources": command_probe,
    "accrue": command_accrue,
    "seal": command_seal,
    "verify-final": command_verify,
}


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> "None":  # type: ignore[override]
        raise OperatorStop("USAGE_ERROR")


_ACCRUAL_STOPS = {"PLAN_FREEZE_INVALID": "PLAN_FREEZE_INVALID", "MEMBERSHIP_REPRODUCTION_FAILED": "MEMBERSHIP_REPRODUCTION_FAILED",
                  "LEDGER_CHAIN_INVALID": "STATE_DRIFT", "VISIBLE_SCHEMA_VIOLATION": "VISIBLE_SCHEMA_VIOLATION"}


def main(argv: Sequence[str] | None = None, env: Environment | None = None) -> int:
    """Closed console: the validated visible report, ``STOP <CODE>`` or
    ``STOP INTERNAL_ERROR:<ExceptionClass>`` only (no traceback, repr or message echo)."""

    parser = _Parser(prog="run_s10_qual_data_03.py", add_help=False)
    parser.add_argument("command", choices=sorted(COMMANDS))
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
        result = COMMANDS[args.command](env or Environment())
        text = json.dumps(oa.validate_visible_report(result), sort_keys=True)
    except OperatorStop as stop:
        print(f"STOP {stop.code}")
        return 2 if stop.code == "USAGE_ERROR" else 3
    except (d1.OperatorStop, d2.OperatorStop) as stop:
        print("STOP " + ("VERIFY_FAILED" if stop.code == "VERIFY_FAILED" else "STATE_DRIFT"))
        return 3
    except oa.AccrualError as error:
        print(f"STOP {_ACCRUAL_STOPS.get(error.code, 'INTERNAL_ERROR:AccrualError')}")
        return 3
    except Exception as error:  # noqa: BLE001 - closed console: class name only, never the message
        print(f"STOP INTERNAL_ERROR:{type(error).__name__}")
        return 4
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
