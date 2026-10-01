"""S10-QUAL-DATA-03 operator tests (prospective census, pending/terminal accrual, multi-run state,
seal, verify-final, budgets, exposure firewall, execution-terms capture).

Fully hermetic: a synthetic prospective world (PendulumFlow hours built with the v3 test builders,
Gamma documents through a fake public client, NDFD listings/objects retimed from the committed GRIB2
fixture, a fake decoder, the fee page) behind a fake transport with scripted faults; a fake clock and
a recording no-sleep seam; a module-wide socket guard proves no real network is attempted. The
frozen scan window and 50-date target are narrowed per test by monkeypatching the pure module.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import shutil
import socket
import struct
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

import tools.qualification.run_s10_qual_data_02 as d2
import tools.qualification.run_s10_qual_data_03 as op
from src.data_layer.analytical_research import nws_ndfd_history as ndfd
from src.data_layer.analytical_research import pendulumflow_v3 as v3
from src.data_layer.analytical_research import qualification as qualification_module
from src.data_layer.analytical_research import qualification_data_readiness as qd
from src.data_layer.analytical_research import qualification_oos_accrual as oa
from src.data_layer.polymarket.errors import PolymarketHTTPError

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "s10_qual_data_03_v3_builders", ROOT / "tests" / "data_layer" / "analytical_research" / "test_pendulumflow_v3.py")
builders = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builders)  # type: ignore[union-attr]

FIXTURE = ROOT / "tests" / "fixtures" / "ndfd_grib" / "ndfd_pop12_reference.grib2"
A, B = qd.CHECKPOINT_A, qd.CHECKPOINT_B
SCAN = (date(2026, 10, 16), date(2026, 10, 19))
NOW = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
RULE = (
    'This market will resolve to "Yes" if New York, NY records measurable precipitation on the date in the title. '
    "Measurable precipitation means 0.01 inches or more as reported by the PRECIPITATION (IN) figure in the NWS Daily "
    "Climate Report (CLI) for the city's station. A report of trace (\"T\") does not qualify. The observation period is "
    "the NWS climate day for KNYC: midnight to midnight local standard time. Resolution is based on the station's first "
    "published precipitation figure for the day. Subsequent revisions or corrections to the published data will not be "
    "considered; the first published value is final. The resolution source for this market is the NWS Daily Climate Report (CLI) for KNYC."
)
FEE_HTML = b"<html><body><h1>Trading Fees</h1><p>Weather markets: fee schedule applies.</p></body></html>"
MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december")

# ── socket guard ──────────────────────────────────────────────────────────────

NETWORK_ATTEMPTS: list[str] = []


@pytest.fixture(autouse=True)
def forbid_real_network(monkeypatch: pytest.MonkeyPatch):
    def refuse(*_args, **_kwargs):
        NETWORK_ATTEMPTS.append("socket")
        raise AssertionError("real network attempted in a hermetic operator test")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    yield


# ── synthetic prospective world ───────────────────────────────────────────────


def ts(moment: datetime) -> datetime:
    return moment


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def cid(byte: int) -> bytes:
    return bytes([byte]) * 32


def tok(decimal_id: str) -> bytes:
    return int(decimal_id).to_bytes(32, "big")


def slug_for(target: date, city: str = "new-york-ny") -> str:
    return f"where-will-it-rain-on-{MONTHS[target.month - 1]}-{target.day}-{target.year}-{city}"


def retimed(reference: datetime, end: datetime) -> bytes:
    """The committed PoP12 message with its section-1 reference time and section-4 interval end replaced."""

    data = bytearray(FIXTURE.read_bytes())
    position = 16
    while True:
        length = struct.unpack(">I", bytes(data[position:position + 4]))[0]
        number = data[position + 4]
        if number == 1:
            data[position + 12:position + 14] = struct.pack(">H", reference.year)
            data[position + 14:position + 19] = bytes([reference.month, reference.day, reference.hour, 0, 0])
        if number == 4:
            data[position + 47:position + 49] = struct.pack(">H", end.year)
            data[position + 49:position + 54] = bytes([end.month, end.day, end.hour, 0, 0])
            break
        position += length
    return bytes(data)


def wmo_object(day: date) -> bytes:
    reference = datetime(day.year, day.month, day.day, 10, tzinfo=timezone.utc)
    first = retimed(reference, reference.replace(hour=0) + timedelta(days=1, hours=12))
    second = retimed(reference, reference.replace(hour=0) + timedelta(days=2))
    return (b"\x01\r\r\n001\r\r\nYDUB12 KWBN 031046\r\r\n" + first
            + b"\r\r\n\x03\x01\r\r\n002\r\r\nYDUC12 KWBN 031046\r\r\n" + second + b"\r\r\n\x03")


def ndfd_key(day: date) -> str:
    return f"wmo/pop12/{day:%Y/%m/%d}/YDUZ98_KWBN_{day:%Y%m%d}1046"


class Market:
    def __init__(self, market_id: str, byte: int, target: date, created: datetime, *, city: str = "new-york-ny") -> None:
        self.id, self.byte, self.target, self.created = market_id, byte, target, created
        self.slug = slug_for(target, city)
        self.yes, self.no = f"{market_id}1", f"{market_id}2"
        self.closed_time = datetime(target.year, target.month, target.day, 18, 18, 5, tzinfo=timezone.utc) + timedelta(days=1)
        self.winner = "No"
        self.bid_ask = ("0.30", "0.36")
        self.emit_resolved = True

    @property
    def condition(self) -> str:
        return "0x" + cid(self.byte).hex()

    def new_market_row(self, received: datetime) -> dict[str, object]:
        return {"timestamp_received": received, "sequence": 1, "timestamp": received, "market": cid(self.byte), "id": self.id,
                "assets_ids": [tok(self.yes), tok(self.no)], "outcomes": ["Yes", "No"], "question": "Will it rain?",
                "slug": self.slug}

    def bba(self, received: datetime) -> dict[str, object]:
        bid, ask = self.bid_ask
        return {"timestamp_received": received, "sequence": 3, "timestamp": received, "market": cid(self.byte),
                "asset_id": tok(self.yes), "best_bid": Decimal(bid), "best_ask": Decimal(ask),
                "spread": Decimal(ask) - Decimal(bid)}

    def resolved(self, received: datetime) -> dict[str, object]:
        token = self.yes if self.winner == "Yes" else self.no
        return {"timestamp_received": received, "sequence": 7, "timestamp": received, "market": cid(self.byte), "id": self.id,
                "assets_ids": [tok(self.yes), tok(self.no)], "winning_asset_id": tok(token), "winning_outcome": self.winner}


class World:
    def __init__(self, markets: list[Market] | None = None, *, pop: int = 40) -> None:
        self.markets = {m.id: m for m in (markets if markets is not None else default_markets())}
        self.calls: list[tuple[str, str, str | None]] = []
        self.gamma_calls: list[str] = []
        self.gamma_final_after: dict[str, datetime] = {}
        self.gamma_fail: set[str] = set()
        self.gamma_identity_break: set[str] = set()
        self.faults: list[tuple[object, list[int]]] = []
        self.clock = NOW
        self.pop = pop
        self.extra_rows: dict[str, dict[str, list[dict[str, object]]]] = {}
        self.audit_measured_through = NOW
        self._cache: dict[str, tuple[bytes, dict[str, object]]] = {}

    # -- archive --
    def hour_rows(self, hour: str) -> dict[str, list[dict[str, object]]]:
        start = v3.hour_start(hour)
        rows: dict[str, list[dict[str, object]]] = {k: list(v) for k, v in self.extra_rows.get(hour, {}).items()}
        for market in self.markets.values():
            if v3.hour_key(market.created) == hour:
                rows.setdefault("new_market", []).append(market.new_market_row(market.created))
            if v3.hour_key(market.created + timedelta(minutes=56)) == hour:
                rows.setdefault("best_bid_ask", []).append(market.bba(market.created + timedelta(minutes=56)))
            b_start = datetime(market.target.year, market.target.month, market.target.day, 4, 30, tzinfo=timezone.utc)
            if v3.hour_key(b_start) == hour:
                rows.setdefault("best_bid_ask", []).append(market.bba(b_start))
            resolved = market.closed_time + timedelta(minutes=1)
            if market.emit_resolved and v3.hour_key(resolved) == hour:
                rows.setdefault("market_resolved", []).append(market.resolved(resolved))
        del start
        return rows

    def hour(self, hour: str) -> tuple[bytes, dict[str, object]]:
        rows = self.hour_rows(hour)
        key = hour + json.dumps({k: [repr(sorted(r.items())) for r in v] for k, v in sorted(rows.items())}, sort_keys=True)
        if key not in self._cache:
            self._cache[key] = builders.build_v3_hour(hour, rows)
        return self._cache[key]

    def audit(self) -> bytes:
        through = min(self.clock, self.audit_measured_through)
        measured = int((through - v3.hour_start(v3.LIVE_START_HOUR)).total_seconds() // 3600)
        published = int((self.clock - v3.hour_start(v3.LIVE_START_HOUR)).total_seconds() // 3600)
        return builders.audit_html([], measured_hours=measured, published=published)

    def fail(self, predicate, statuses) -> None:
        self.faults.append((predicate, list(statuses)))

    def fetch(self, method, url, headers, timeout):
        for predicate, remaining in self.faults:
            if remaining and predicate(url, headers):
                self.calls.append((method, url, headers.get("Range")))
                return remaining.pop(0), {}, b""
        self.calls.append((method, url, headers.get("Range")))
        if url == oa.FEE_DOC_URL:
            return 200, {"content-type": "text/html"}, FEE_HTML
        parts = url.split("/", 3)
        host, path = parts[2], "/" + (parts[3] if len(parts) > 3 else "")
        if host == op.PENDULUMFLOW_HOST:
            if path == "/audit":
                return 200, {}, self.audit()
            _v3, day, hh, name = path.strip("/").split("/")
            hour = f"{day}/{hh}"
            if v3.hour_start(hour) + timedelta(hours=1) > self.clock:
                return 404, {}, b"not found"
            data, manifest = self.hour(hour)
            if name == "manifest.json":
                return 200, {}, json.dumps(manifest).encode()
            start, end = (int(x) for x in headers["Range"][len("bytes="):].split("-"))
            return 206, {"last-modified": "Wed, 21 Oct 2026 00:00:00 GMT", "content-range": f"bytes {start}-{end}/{len(data)}"}, data[start:end + 1]
        if host == ndfd.BUCKET_HOST:
            if path.startswith("/?"):
                prefix = url.split("prefix=")[1].replace("%2F", "/")
                day = date(int(prefix[10:14]), int(prefix[15:17]), int(prefix[18:20]))
                contents = ""
                available = datetime(day.year, day.month, day.day, 10, 51, 56, tzinfo=timezone.utc)
                if available <= self.clock:
                    contents = (f"<Contents><Key>{ndfd_key(day)}</Key><LastModified>{available:%Y-%m-%dT%H:%M:%S}.000Z</LastModified>"
                                f"<Size>{len(wmo_object(day))}</Size></Contents>")
                return 200, {}, ('<?xml version="1.0" encoding="UTF-8"?><ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
                                 f"<Name>noaa-ndfd-pds</Name><Prefix>{prefix}</Prefix><IsTruncated>false</IsTruncated>{contents}</ListBucketResult>").encode()
            key = path[1:]
            day = date(int(key[10:14]), int(key[15:17]), int(key[18:20]))
            if key == ndfd_key(day):
                return 200, {"last-modified": f"{datetime(day.year, day.month, day.day, 10, 51, 56):%a, %d %b %Y %H:%M:%S} GMT"}, wmo_object(day)
            return 404, {}, b""
        if host == op.NWS_HOST and path == "/stations/KNYC":
            return 200, {}, json.dumps({"geometry": {"type": "Point", "coordinates": [-73.96667, 40.78333]},
                                        "properties": {"stationIdentifier": "KNYC", "timeZone": "America/New_York",
                                                       "name": "New York City, Central Park"}}).encode()
        return 404, {}, b""

    # -- gamma --
    def gamma_document(self, market_id: str) -> dict[str, object]:
        market = self.markets[market_id]
        final = self.clock >= self.gamma_final_after.get(market_id, market.closed_time)
        document = {
            "id": market_id, "conditionId": market.condition, "slug": market.slug,
            "clobTokenIds": json.dumps([market.yes, market.no]), "outcomes": json.dumps(["Yes", "No"]),
            "outcomePrices": json.dumps(["1", "0"] if market.winner == "Yes" else ["0", "1"]) if final else json.dumps(["0.4", "0.6"]),
            "closed": final, "umaResolutionStatus": "resolved" if final else "proposed",
            "startDate": (market.created - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "closedTime": market.closed_time.strftime("%Y-%m-%d %H:%M:%S+00") if final else None,
            "description": RULE, "resolutionSource": "https://forecast.weather.gov/product.php?issuedby=NYC&product=CLI",
            "feesEnabled": True, "feeType": "weather_fees", "orderMinSize": 5, "orderPriceMinTickSize": 0.001,
        }
        if market_id in self.gamma_identity_break:
            document["conditionId"] = "0x" + cid(0x99).hex()
        return document


class FakeGammaClient:
    def __init__(self, world: World) -> None:
        self.world = world

    def get_market(self, market_id: str):
        self.world.gamma_calls.append(market_id)
        if market_id not in self.world.markets or market_id in self.world.gamma_fail:
            raise PolymarketHTTPError(503 if market_id in self.world.gamma_fail else 404,
                                      "https://gamma-api.polymarket.com/markets/" + market_id)
        return SimpleNamespace(data=self.world.gamma_document(market_id), request_info=SimpleNamespace(status_code=200))


def default_markets() -> list[Market]:
    def created(day: int) -> datetime:
        return datetime(2026, 10, day, 11, 9, 14, 805697, tzinfo=timezone.utc)

    return [
        Market("4100170", 0x17, date(2026, 10, 17), created(16)),
        Market("4100180", 0x18, date(2026, 10, 18), created(17)),
        Market("4100190", 0x19, date(2026, 10, 19), created(18)),
        Market("4100191", 0x1A, date(2026, 10, 19), created(18)),
        Market("4100250", 0x25, date(2026, 10, 25), created(18)),  # outside the narrowed window
    ]


def fake_decode_factory(world: World):
    def fake_decode(message: bytes, stations):
        header = ndfd.parse_pop12_header(message)
        values = tuple(ndfd.StationValue(s.station_id, 1846511, 40.775844, -73.970832, 1.03, world.pop) for s in stations)
        return ndfd.DecodedPop12(header, (("edition", 2),), values)
    return fake_decode


# ── DATA-02 synthetic evidence ────────────────────────────────────────────────


def data02_bundle(manifests_per_date: int = 3, dates: int = 3) -> dict[str, object]:
    rows = []
    ready: list[str] = []
    for index in range(dates):
        day = date(2026, 8, 18) + timedelta(days=index)
        ids = [f"researchmanifest:sha256:{hashlib.sha256(f'{day}-{k}'.encode()).hexdigest()}" for k in range(manifests_per_date)]
        ready.extend(ids)
        candidate = qd.MarketCandidate(str(3_000_000 + index), "0x" + "ab" * 32, ("11", "12"), ("Yes", "No"), "Will it rain?",
                                       slug_for(day), f"{day}T11:00:00.000000Z", f"{day}/11")
        checkpoint = datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc)
        history = {"source_class": v3.SOURCE_CLASS, "source_authority": v3.B0_SOURCE_AUTHORITY, "ordering_basis": "timestamp_received",
                   "best_bid_ask": {"asset_id": "11", "best_bid": "0.40", "best_ask": "0.45", "spread": "0.05",
                                    "timestamp_received": f"{day}T11:30:00.000000Z", "venue_timestamp": f"{day}T11:30:00.000Z",
                                    "hour": f"{day}/11", "coverage_class": "FULL"},
                   "last_trade_price": None, "last_trade_price_state": "NOT_OBSERVED_IN_SEARCHED_HOURS",
                   "last_trade_price_searched_hours": [f"{day}/11"]}
        weather = {"source_class": ndfd.SOURCE_CLASS, "periods": [{"pop12_percent": 30}], "public_available_time": f"{day}T10:51:56Z",
                   "climate_day_start": f"{day}T05:00:00Z", "object_key": ndfd_key(day)}
        label = {"post_outcome_evidence": True, "winning_outcome": "No"}
        rows.append(qd.build_row(candidate=candidate, target_day=day, checkpoint_id=A, checkpoint_time=checkpoint, yes_token_id="11",
                                 market_history=history, weather=weather, label=label, manifest_ids=ids))
    counts = {"discovered_candidates": dates}
    return qd.build_bundle(rows=rows, market_exclusions=[], row_exclusions=[], counts=counts, execution_evidence={},
                           ready_manifest_ids=ready, diagnostic_manifest_ids=[], external_dataset_ids=[], source_facts={},
                           terminal_reason="EVIDENCE_COMPLETE_ROWS_PRESENT")


def write_data02(root: Path, bundle: dict[str, object]) -> None:
    workspace = root.joinpath(*op.DATA02_PARTS)
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / d2.BUNDLE_FILENAME).write_text(json.dumps(bundle), encoding="utf-8")
    (workspace / d2.VERIFY_FILENAME).write_text(json.dumps({"status": "VERIFIED", "network_calls": 0, "bundle_id": bundle["bundle_id"],
                                                             "logical_dataset_id": bundle["logical_dataset_id"]}), encoding="utf-8")


# ── fixture ───────────────────────────────────────────────────────────────────


def build_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, world: World, *, bundle: dict[str, object] | None = None,
              target: int = 2, min_rows: int = 2) -> SimpleNamespace:
    monkeypatch.setattr(oa, "SCAN_START", SCAN[0])
    monkeypatch.setattr(oa, "SCAN_END", SCAN[1])
    monkeypatch.setattr(oa, "TARGET_EFFECTIVE_DATES", target)
    monkeypatch.setattr(oa, "MIN_OOS_ROWS", min_rows)
    repo = tmp_path / "repo"
    for rel in (*op.CODE_FILES, oa.PLAN_PATH, oa.POWER_DOC_PATH):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, repo / rel)
    data02_root = tmp_path / "data02-worktree"
    bundle = bundle or data02_bundle()
    write_data02(data02_root, bundle)
    monkeypatch.setattr(op, "DATA02_BUNDLE_ID", bundle["bundle_id"])
    monkeypatch.setattr(op, "DATA02_DATASET_ID", bundle["logical_dataset_id"])
    state = {"dirty": "", "roots": [repo, data02_root], "merge_meta": None}

    def git(*args: str) -> str:
        if args[:2] == ("worktree", "list"):
            return "".join(f"worktree {r}\nHEAD {'a' * 40}\n\n" for r in state["roots"])
        if args == ("rev-parse", "HEAD"):
            return "a" * 40 + "\n"
        if args[0] == "status":
            return state["dirty"]
        if args[0] == "merge-base":
            return ""
        if args[:2] == ("show", "-s"):
            return state["merge_meta"] or (f"{oa.PLAN_MERGE_SHA}\n{' '.join(oa.PLAN_MERGE_PARENTS)}\nGitHub\n2026-09-30T20:39:26-06:00\n")
        raise AssertionError(args)

    def git_blob(revision: str, path: str) -> bytes:
        assert revision == oa.PLAN_MERGE_SHA
        return (ROOT / path).read_bytes()

    sleeps: list[float] = []
    env = op.Environment(repo_root=repo, git=git, git_blob=git_blob, fetch=world.fetch,
                         gamma_client_factory=lambda: FakeGammaClient(world), decode_fn=fake_decode_factory(world),
                         require_decoder=False, sleep=sleeps.append, now=lambda: world.clock)
    NETWORK_ATTEMPTS.clear()
    return SimpleNamespace(env=env, world=world, state=state, repo=repo, sleeps=sleeps, bundle=bundle, tmp=tmp_path)


@pytest.fixture()
def ctx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    return build_env(tmp_path, monkeypatch, World())


def ledger(ctx) -> list[dict[str, object]]:
    return op._jsonl(ctx.env.workspace / op.LEDGER_FILENAME)  # noqa: SLF001


def dates_of(ctx) -> dict[str, dict[str, object]]:
    return {str(e["target_date"]): e for e in ledger(ctx) if e["entry_kind"] == "DATE"}


# ── end to end ────────────────────────────────────────────────────────────────


def test_end_to_end_prepare_accrue_seal_verify(ctx) -> None:
    prepared = op.command_prepare(ctx.env)
    assert prepared["status"] == "PREPARED" and prepared["state"] == oa.STATE_NOT_STARTED and prepared["n2"] == 9
    report = op.command_accrue(ctx.env)
    assert report["state"] == oa.STATE_INCOMPLETE and report["run"] == 1 and report["budget_exhausted"] is None
    states = {d: (e["classification"], e["reason"]) for d, e in dates_of(ctx).items()}
    assert states == {
        "2026-10-16": ("EXCLUDED", "OOS_DATE_NO_ELIGIBLE_ROW"),
        "2026-10-17": ("EXCLUDED", "OOS_DATE_DECISION_IN_WP170_EMBARGO"),
        "2026-10-18": ("ELIGIBLE", None),
        "2026-10-19": ("ELIGIBLE", None),
    }
    assert report["prefix"] == {"length": 2, "target": 2, "earliest_pending_date": None, "pending_dates": 0,
                                "pending_markets": 0, "seal_decision": oa.STATE_SEALED}
    assert report["counts"]["outside_window_markets"] == 1
    assert report["counts"]["eligible_rows_by_checkpoint"] == {A: 3, B: 3}
    assert report["counts"]["b0_basis"] == {"MIDPOINT": 8}
    assert report["execution_evidence_states"]["SPREAD_DEPTH"] == "PARTIAL"
    assert report["execution_evidence_states"]["LATENCY"] == "MISSING"
    sealed = op.command_seal(ctx.env)
    assert sealed["state"] == oa.STATE_SEALED and sealed["oos_target_dates"] == 2 and sealed["oos_rows"] == 6
    assert sealed["oos_membership_id"].startswith(oa.MEMBERSHIP_ID_PREFIX)
    verified = op.command_verify(ctx.env)
    assert verified["status"] == "VERIFIED" and verified["network_calls"] == 0
    assert verified["oos_membership_id"] == sealed["oos_membership_id"]
    assert verified["data03_bundle_id"] == sealed["data03_bundle_id"]
    assert NETWORK_ATTEMPTS == []


def visible_files(ctx) -> list[Path]:
    workspace = ctx.env.workspace
    files = [workspace / op.PREPARE_REPORT_FILENAME, workspace / op.SEAL_REPORT_FILENAME, workspace / op.VERIFY_FILENAME]
    files += sorted(workspace.glob("runs/run-*/" + op.RUN_REPORT_FILENAME))
    return [f for f in files if f.exists()]


def comparable(report: dict[str, object]) -> dict[str, object]:
    """Visible report minus transport byte counters (raw response sizes are accounting, not values)."""

    out = json.loads(json.dumps(report))
    for scope in out.get("network", {}).values():
        for key in ("bytes", "max_single_response"):
            scope.pop(key, None)
    return out


def sealed_rows(ctx) -> dict[str, dict[str, object]]:
    records = op._jsonl(ctx.env.workspace / op.SEALED_DIRNAME / op.SEALED_RECORDS_FILENAME)  # noqa: SLF001
    return {r["row_id"]: r for record in records for r in record["rows"]}


# ── R: plan / freeze / prepare gates ──────────────────────────────────────────


def test_prepare_rejects_tampered_or_late_plan_freeze(ctx) -> None:
    ctx.state["merge_meta"] = f"{oa.PLAN_MERGE_SHA}\n{' '.join(oa.PLAN_MERGE_PARENTS)}\nGitHub\n2026-10-14T00:00:01Z\n"
    with pytest.raises(op.OperatorStop, match="PLAN_FREEZE_INVALID"):
        op.command_prepare(ctx.env)
    ctx.state["merge_meta"] = f"{oa.PLAN_MERGE_SHA}\n{' '.join(oa.PLAN_MERGE_PARENTS)}\nSomeone\n2026-09-30T20:39:26-06:00\n"
    with pytest.raises(op.OperatorStop, match="PLAN_FREEZE_INVALID"):
        op.command_prepare(ctx.env)
    ctx.state["merge_meta"] = None
    plan = ctx.repo / oa.PLAN_PATH
    plan.write_bytes(plan.read_bytes().replace(b'"oos_start":"2026-10-15T00:00:00Z"', b'"oos_start":"2026-10-16T00:00:00Z"'))
    with pytest.raises(op.OperatorStop, match="PLAN_FREEZE_INVALID"):
        op.command_prepare(ctx.env)
    assert not ctx.env.workspace.exists()


def test_prepare_requires_verified_data02_and_clean_tree(ctx) -> None:
    ctx.state["dirty"] = " M src/x.py"
    with pytest.raises(op.OperatorStop, match="STATE_DRIFT"):
        op.command_prepare(ctx.env)
    ctx.state["dirty"] = ""
    ctx.state["roots"] = [ctx.repo]
    with pytest.raises(op.OperatorStop, match="DATA02_EVIDENCE_MISSING"):
        op.command_prepare(ctx.env)
    assert not ctx.env.workspace.exists()


def test_n2_plus_reserve_pre_gate_stops_before_workspace(tmp_path, monkeypatch) -> None:
    ctx = build_env(tmp_path, monkeypatch, World(), bundle=data02_bundle(manifests_per_date=107, dates=1))
    with pytest.raises(op.OperatorStop, match="PROVENANCE_CEILING_UNREACHABLE"):
        op.command_prepare(ctx.env)
    assert not ctx.env.workspace.exists()
    ok = build_env(tmp_path / "ok", monkeypatch, World(), bundle=data02_bundle(manifests_per_date=106, dates=1))
    assert op.command_prepare(ok.env)["n2_plus_reserve"] == 256


def test_prepare_is_idempotent_and_conflict_closed(ctx) -> None:
    first = op.command_prepare(ctx.env)
    assert op.command_prepare(ctx.env)["status"] == "PREPARED_IDEMPOTENT"
    plan = json.loads((ctx.env.workspace / op.PLAN_FILENAME).read_text(encoding="utf-8"))
    plan["data02"]["n2"] = 1
    (ctx.env.workspace / op.PLAN_FILENAME).write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(op.OperatorStop, match="PREPARE_WORKSPACE_CONFLICT"):
        op.command_prepare(ctx.env)
    assert first["workspace_plan_sha256"] != hashlib.sha256(b"").hexdigest()


def test_no_accrue_before_oos_start(ctx) -> None:
    op.command_prepare(ctx.env)
    ctx.world.clock = datetime(2026, 10, 14, 23, 59, 59, tzinfo=timezone.utc)
    with pytest.raises(op.OperatorStop, match="ACCRUAL_BEFORE_OOS_START"):
        op.command_accrue(ctx.env)
    assert not (ctx.env.workspace / op.RUNS_DIRNAME).exists() and ctx.world.calls == []


# ── R: census ─────────────────────────────────────────────────────────────────


def test_census_uses_exactly_the_11_12_utc_new_market_hours(tmp_path, monkeypatch) -> None:
    late = Market("4100199", 0x1F, date(2026, 10, 19), datetime(2026, 10, 18, 13, 9, tzinfo=timezone.utc))
    ctx = build_env(tmp_path, monkeypatch, World(default_markets() + [late]))
    op.command_prepare(ctx.env)
    op.command_accrue(ctx.env)
    assert "4100199" not in dates_of(ctx)["2026-10-19"]["market_ids"]
    new_market_hours = {url.split("/v3/")[1][:13] for _m, url, _r in ctx.world.calls if url.endswith("manifest.json")}
    discovery = {f"{d}/{h:02d}" for d in ("2026-10-16", "2026-10-17", "2026-10-18", "2026-10-19") for h in (11, 12)}
    assert discovery <= new_market_hours
    assert not [c for c in ctx.world.calls if "gamma" in c[1]]  # Gamma only via the public client, never listed


def test_failed_discovery_hour_stays_structural_pending_then_resolves(ctx) -> None:
    op.command_prepare(ctx.env)
    hour = v3.manifest_object_path("2026-10-17/12")
    ctx.world.fail(lambda url, _h: url.endswith(hour), [503] * 4)
    report = op.command_accrue(ctx.env)
    assert set(dates_of(ctx)) == {"2026-10-16"}  # the census of every later date stays open
    assert report["prefix"]["earliest_pending_date"] == "2026-10-17" and report["prefix"]["seal_decision"] == op.oa.SEAL_NOT_READY
    assert report["counts"]["discovery_hours_pending"] == 1
    assert not any(e.get("market_exclusion") for e in ledger(ctx))
    report = op.command_accrue(ctx.env)
    assert report["run"] == 2 and report["prefix"]["length"] == 2 and report["prefix"]["seal_decision"] == oa.STATE_SEALED
    assert dates_of(ctx)["2026-10-16"]["run"] == 1 and dates_of(ctx)["2026-10-18"]["run"] == 2


def test_duplicate_witness_copies_collapse_by_earliest_receive(tmp_path, monkeypatch) -> None:
    world = World()
    market = world.markets["4100180"]
    world.extra_rows["2026-10-17/11"] = {"new_market": [market.new_market_row(market.created + timedelta(seconds=2))]}
    ctx = build_env(tmp_path, monkeypatch, world)
    op.command_prepare(ctx.env)
    op.command_accrue(ctx.env)
    entry = next(e for e in ledger(ctx) if e["subject_id"] == "4100180")
    a_row = next(r for r in entry["rows"] if r["checkpoint_id"] == A)
    assert a_row["decision_time"] == "2026-10-17T12:09:14.805697Z"


# ── R: pending label semantics ────────────────────────────────────────────────


def test_gamma_finality_repoll_failure_stays_pending_never_label_gamma_not_final(ctx) -> None:
    op.command_prepare(ctx.env)
    ctx.world.clock = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)  # 10-19 markets not yet final
    first = op.command_accrue(ctx.env)
    assert "2026-10-19" not in dates_of(ctx) and first["prefix"]["earliest_pending_date"] == "2026-10-19"
    ctx.world.clock = NOW
    ctx.world.gamma_fail = {"4100190", "4100191"}
    second = op.command_accrue(ctx.env)
    assert "2026-10-19" not in dates_of(ctx) and second["prefix"]["pending_markets"] == 2
    text = (ctx.env.workspace / op.LEDGER_FILENAME).read_text(encoding="utf-8")
    assert "LABEL_GAMMA_NOT_FINAL" not in text and "GAMMA_UNAVAILABLE" not in text
    ctx.world.gamma_fail = set()
    third = op.command_accrue(ctx.env)
    assert dates_of(ctx)["2026-10-19"]["classification"] == "ELIGIBLE" and third["prefix"]["seal_decision"] == oa.STATE_SEALED
    assert op.command_verify(ctx.env)["runs_replayed"] == 3


def test_label_window_without_resolution_and_failed_label_read_are_closed_codes(tmp_path, monkeypatch) -> None:
    world = World()
    world.markets["4100190"].emit_resolved = False
    world.markets["4100191"].closed_time = datetime(2026, 10, 20, 20, 18, 5, tzinfo=timezone.utc)
    ctx = build_env(tmp_path, monkeypatch, world)
    op.command_prepare(ctx.env)
    hour = v3.manifest_object_path("2026-10-20/20")
    world.fail(lambda url, _h: url.endswith(hour), [503] * 4)
    op.command_accrue(ctx.env)
    by_id = {e["subject_id"]: e for e in ledger(ctx) if e["entry_kind"] == "MARKET"}
    assert by_id["4100190"]["market_exclusion"] == "LABEL_V3_RESOLUTION_MISSING"
    assert by_id["4100191"]["market_exclusion"] == "LABEL_V3_SOURCE_READ_FAILED"
    assert dates_of(ctx)["2026-10-19"]["reason"] == "OOS_DATE_NO_ELIGIBLE_ROW"


def test_initial_gamma_failure_is_gamma_unavailable_and_identity_mismatch_closed(tmp_path, monkeypatch) -> None:
    world = World()
    world.gamma_fail = {"4100190"}
    world.gamma_identity_break = {"4100191"}
    ctx = build_env(tmp_path, monkeypatch, world)
    op.command_prepare(ctx.env)
    op.command_accrue(ctx.env)
    by_id = {e["subject_id"]: e for e in ledger(ctx) if e["entry_kind"] == "MARKET"}
    assert by_id["4100190"]["market_exclusion"] == "GAMMA_UNAVAILABLE"
    assert by_id["4100191"]["market_exclusion"] == "GAMMA_V3_IDENTITY_MISMATCH"


# ── R: stable prefix and seal ─────────────────────────────────────────────────


def test_rows_insufficient_and_seal_is_one_way(tmp_path, monkeypatch) -> None:
    ctx = build_env(tmp_path, monkeypatch, World(), min_rows=7)
    op.command_prepare(ctx.env)
    assert op.command_accrue(ctx.env)["prefix"]["seal_decision"] == oa.STATE_ROWS_INSUFFICIENT
    sealed = op.command_seal(ctx.env)
    assert sealed["state"] == oa.STATE_ROWS_INSUFFICIENT and sealed["oos_membership_id"].startswith(oa.MEMBERSHIP_ID_PREFIX)
    with pytest.raises(op.OperatorStop, match="ACCRUAL_FINALIZED"):
        op.command_seal(ctx.env)
    with pytest.raises(op.OperatorStop, match="ACCRUAL_FINALIZED"):
        op.command_accrue(ctx.env)
    assert op.command_verify(ctx.env)["state"] == oa.STATE_ROWS_INSUFFICIENT


def test_seal_refused_while_prefix_unstable_and_cap_insufficiency_waits(tmp_path, monkeypatch) -> None:
    ctx = build_env(tmp_path, monkeypatch, World(), target=3)
    op.command_prepare(ctx.env)
    ctx.world.clock = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
    assert op.command_accrue(ctx.env)["prefix"]["seal_decision"] == op.oa.SEAL_NOT_READY
    with pytest.raises(op.OperatorStop, match="NOT_SEALABLE"):
        op.command_seal(ctx.env)
    ctx.world.clock = NOW
    assert op.command_accrue(ctx.env)["prefix"]["seal_decision"] == oa.STATE_INSUFFICIENT_AT_CAP
    sealed = op.command_seal(ctx.env)
    assert sealed["state"] == oa.STATE_INSUFFICIENT_AT_CAP and sealed["oos_membership_id"] is None
    assert op.command_verify(ctx.env)["state"] == oa.STATE_INSUFFICIENT_AT_CAP


def test_sealed_membership_and_ledger_tampering_is_detected(ctx) -> None:
    op.command_prepare(ctx.env)
    op.command_accrue(ctx.env)
    op.command_seal(ctx.env)
    seal_path = ctx.env.workspace / op.SEALED_DIRNAME / op.SEAL_FILENAME
    original = seal_path.read_text(encoding="utf-8")
    tampered = json.loads(original)
    tampered["membership"]["preimage"]["oos_row_ids"] = tampered["membership"]["preimage"]["oos_row_ids"][1:]
    seal_path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(op.OperatorStop, match="MEMBERSHIP_REPRODUCTION_FAILED"):
        op.command_verify(ctx.env)
    seal_path.write_text(original, encoding="utf-8")
    path = ctx.env.workspace / op.LEDGER_FILENAME
    lines = path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    first["market_exclusion"] = "GAMMA_UNAVAILABLE"
    path.write_text("\n".join([json.dumps(first)] + lines[1:]) + "\n", encoding="utf-8")
    with pytest.raises(op.OperatorStop, match="STATE_DRIFT"):
        op.command_verify(ctx.env)


# ── R: multi-run state, crash, reuse, versioning ──────────────────────────────


def test_crashed_run_commits_nothing_and_resumes_same_run(ctx, monkeypatch) -> None:
    op.command_prepare(ctx.env)
    original = op.AccrualPipeline.phase_dates

    def crash(self):
        raise RuntimeError("simulated crash")

    monkeypatch.setattr(op.AccrualPipeline, "phase_dates", crash)
    with pytest.raises(RuntimeError):
        op.command_accrue(ctx.env)
    assert not (ctx.env.workspace / op.LEDGER_FILENAME).exists()
    record = json.loads((ctx.env.workspace / "runs" / "run-001" / op.RUN_FILENAME).read_text(encoding="utf-8"))
    assert record["status"] == "RUNNING"
    before = len(ctx.world.calls)
    monkeypatch.setattr(op.AccrualPipeline, "phase_dates", original)
    report = op.command_accrue(ctx.env)
    assert report["run"] == 1 and report["resumed"] is True
    resumed_calls = ctx.world.calls[before:]
    assert not [c for c in resumed_calls if c[1].endswith("2026-10-16/11/manifest.json")]  # immutable bytes reused
    assert op.command_verify(ctx.env)["runs_replayed"] == 1


def test_successful_immutable_sources_are_reused_across_runs(ctx) -> None:
    op.command_prepare(ctx.env)
    op.command_accrue(ctx.env)
    pf_calls = [c for c in ctx.world.calls if "/v3/" in c[1]]
    assert pf_calls and len({(c[1], c[2]) for c in pf_calls}) == len(pf_calls)  # no immutable request repeated in a run
    before = len(ctx.world.calls)
    ctx.world.clock = NOW + timedelta(hours=3)
    report = op.command_accrue(ctx.env)
    assert not [c for c in ctx.world.calls[before:] if "/v3/" in c[1] or "noaa" in c[1] or "weather.gov" in c[1]]
    assert report["network"]["run"]["artifacts_reused"] > 0


def test_no_alternative_discovery_source() -> None:
    text = (ROOT / "tools" / "qualification" / "run_s10_qual_data_03.py").read_text(encoding="utf-8")
    for token in ("get_markets", "keyset", "/markets?", "next_cursor", "/events", "public-search"):
        assert token not in text, token
    assert "get_market(" not in text.replace("PolymarketPublicClient.get_market", "")  # only via the DATA-02 Gamma path
    for url in ("https://gamma-api.polymarket.com/markets?closed=true", "https://gamma-api.polymarket.com/events",
                "https://clob.polymarket.com/markets/1", "https://gamma-api.polymarket.com/markets/keyset"):
        with pytest.raises(op.TransportRefused):
            op.d1.validate_request("GET", url, {"User-Agent": op.USER_AGENT})
    with pytest.raises(op.TransportRefused):
        op.d1.validate_request("POST", "https://gamma-api.polymarket.com/markets/1", {"User-Agent": op.USER_AGENT})


def test_immutable_reuse_mutable_versioning_and_terminal_immutability(ctx) -> None:
    op.command_prepare(ctx.env)
    op.command_accrue(ctx.env)
    index_before = (ctx.env.workspace / op.INDEX_FILENAME).read_bytes()
    ledger_before = ledger(ctx)
    calls = len(ctx.world.calls)
    ctx.world.clock = NOW + timedelta(hours=1)
    report = op.command_accrue(ctx.env)
    run2 = ctx.world.calls[calls:]
    assert {c[1] for c in run2} == {op.d1.pf_url("audit"), oa.FEE_DOC_URL}  # nothing immutable re-downloaded
    assert report["network"]["run"]["artifacts_new"] == 2
    index_after = (ctx.env.workspace / op.INDEX_FILENAME).read_bytes()
    assert index_after.startswith(index_before)  # append-only; earlier versions never overwritten
    keys = [json.loads(line)["key"] for line in index_after.decode().splitlines()]
    assert sum(k.startswith(f"GET {oa.FEE_DOC_URL} capture=run-") for k in keys) == 2
    assert sum(k.endswith("/audit capture=run-002") for k in keys) == 1
    assert ledger(ctx) == ledger_before  # no new terminal subject; committed entries unchanged
    assert op.command_verify(ctx.env)["runs_replayed"] == 2


def test_code_drift_after_prospective_accrual_stops(ctx) -> None:
    op.command_prepare(ctx.env)
    op.command_accrue(ctx.env)
    source = ctx.repo / "tools" / "qualification" / "run_s10_qual_data_03.py"
    source.write_text(source.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
    for command in (op.command_accrue, op.command_seal, op.command_verify):
        with pytest.raises(op.OperatorStop, match="CODE_DRIFT_AFTER_PROSPECTIVE_ACCRUAL"):
            command(ctx.env)


# ── R: budgets ────────────────────────────────────────────────────────────────


def test_per_run_budget_ends_incomplete_without_minting_exclusions(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(op, "RUN_MAX_ATTEMPTS", 40)
    ctx = build_env(tmp_path, monkeypatch, World())
    op.command_prepare(ctx.env)
    report = op.command_accrue(ctx.env)
    assert report["budget_exhausted"] == "RUN_ATTEMPT_BUDGET_EXHAUSTED" and report["state"] == oa.STATE_INCOMPLETE
    ledger_path = ctx.env.workspace / op.LEDGER_FILENAME
    assert not ledger_path.exists() or "BUDGET_EXHAUSTED_BEFORE_EVALUATION" not in ledger_path.read_text(encoding="utf-8")
    for _ in range(10):
        report = op.command_accrue(ctx.env)
        if report["prefix"]["seal_decision"] == oa.STATE_SEALED:
            break
    assert report["prefix"]["seal_decision"] == oa.STATE_SEALED
    assert all(json.loads(p.read_text())["attempts"] <= 40 for p in ctx.env.workspace.glob("runs/run-*/NETWORK.json"))
    assert op.command_verify(ctx.env)["status"] == "VERIFIED"


def test_cumulative_budget_is_a_hard_stop(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(op, "CUM_MAX_ATTEMPTS", 30)
    ctx = build_env(tmp_path, monkeypatch, World())
    op.command_prepare(ctx.env)
    with pytest.raises(op.OperatorStop, match="ACCRUAL_BUDGET_EXHAUSTED"):
        op.command_accrue(ctx.env)
    with pytest.raises(op.OperatorStop, match="ACCRUAL_BUDGET_EXHAUSTED"):
        op.command_accrue(ctx.env)


def test_unavoidable_provenance_overflow_stops(tmp_path, monkeypatch) -> None:
    ctx = build_env(tmp_path, monkeypatch, World(), target=90)
    op.command_prepare(ctx.env)
    with pytest.raises(op.OperatorStop, match="QUAL_PROVENANCE_LIMIT_EXCEEDED_UNAVOIDABLE"):
        op.command_accrue(ctx.env)
    with pytest.raises(op.OperatorStop, match="QUAL_PROVENANCE_LIMIT_EXCEEDED_UNAVOIDABLE"):
        op.command_accrue(ctx.env)


# ── R: exposure firewall ──────────────────────────────────────────────────────


def test_visible_reports_invariant_under_label_permutation_and_value_perturbation(tmp_path, monkeypatch) -> None:
    base = build_env(tmp_path / "base", monkeypatch, World())
    op.command_prepare(base.env)
    reference = comparable(op.command_accrue(base.env))
    permuted_world = World(pop=85)
    for market in permuted_world.markets.values():
        market.winner = "Yes"
        market.bid_ask = ("0.61", "0.64")
    other = build_env(tmp_path / "other", monkeypatch, permuted_world)
    op.command_prepare(other.env)
    assert comparable(op.command_accrue(other.env)) == reference
    base_rows, other_rows = sealed_rows(base), sealed_rows(other)
    assert set(base_rows) == set(other_rows)  # row ids are label/value free
    some = next(iter(base_rows))
    assert base_rows[some]["label"]["label_yes"] is False and other_rows[some]["label"]["label_yes"] is True
    assert base_rows[some]["features"] != other_rows[some]["features"]
    base_seal, other_seal = op.command_seal(base.env), op.command_seal(other.env)
    # Only the two SHA-256 commitments (bound to raw evidence through the ledger) may differ.
    commitments = ("oos_membership_id", "data03_bundle_id", "ledger_head")
    assert {k: v for k, v in base_seal.items() if k not in commitments} == {k: v for k, v in other_seal.items() if k not in commitments}
    for report in (base_seal, other_seal):
        assert all(str(report[k]).split(":sha256:")[1].isalnum() for k in commitments)


def test_no_label_or_value_text_reaches_visible_files(ctx, capsys) -> None:
    assert op.main(["prepare"], ctx.env) == 0
    assert op.main(["accrue"], ctx.env) == 0
    assert op.main(["seal"], ctx.env) == 0
    assert op.main(["verify-final"], ctx.env) == 0
    out = capsys.readouterr().out
    texts = [out] + [f.read_text(encoding="utf-8") for f in visible_files(ctx)]
    rows = sealed_rows(ctx)
    forbidden = {"winning", "label_yes", "4100181", "4100182", "outcomePrices"}
    for row in rows.values():
        forbidden |= {f'"{row["features"]["wx.ndfd_pop12_max_climate_day_v1"]}"', f'"{row["b0"]["value"]}"',
                      f'"{row["features"]["time.ndfd_lead_hours_v1"]}"'}
    for text in texts:
        for item in forbidden:
            assert item not in text, item


def test_exception_and_outcome_canaries_never_leak(ctx, capsys) -> None:
    op.command_prepare(ctx.env)

    def exploding(message, stations):
        raise RuntimeError("CANARY winning_outcome=Yes token 4100191 label_yes=True")

    ctx.env.decode_fn = exploding
    assert op.main(["accrue"], ctx.env) == 4
    out = capsys.readouterr()
    assert out.out.strip() == "STOP INTERNAL_ERROR:RuntimeError" and "CANARY" not in out.out + out.err
    assert op.main(["bogus"], ctx.env) == 2 and capsys.readouterr().out.strip() == "STOP USAGE_ERROR"


def test_verify_final_is_socket_forbidden(ctx, monkeypatch) -> None:
    op.command_prepare(ctx.env)
    op.command_accrue(ctx.env)
    seen: list[str] = []
    original = op.d1._forbid_network  # noqa: SLF001

    def tracking():
        restore = original()
        seen.append("forbidden")
        try:
            socket.create_connection(("archive.pendulumflow.com", 443))
        except op.d1._NetworkForbidden:  # noqa: SLF001
            seen.append("refused")
        return restore

    monkeypatch.setattr(op.d1, "_forbid_network", tracking)
    assert op.command_verify(ctx.env)["network_calls"] == 0
    assert seen == ["forbidden", "refused"]
    ctx.env.fetch = None
    ctx.env.gamma_client_factory = None
    assert op.command_verify(ctx.env)["status"] == "VERIFIED"


def test_raw_tamper_detected_before_network_and_by_verify(ctx) -> None:
    op.command_prepare(ctx.env)
    op.command_accrue(ctx.env)
    entry = next(e for e in ledger(ctx) if e["entry_kind"] == "MARKET" and e["artifacts"]["PENDULUMFLOW_MARKET_HISTORY"])
    digest = entry["artifacts"]["PENDULUMFLOW_MARKET_HISTORY"][0]["content_sha256"]
    (ctx.env.workspace / "raw" / digest).write_bytes(b"tampered")
    calls = len(ctx.world.calls)
    with pytest.raises(op.OperatorStop, match="STATE_DRIFT"):
        op.command_accrue(ctx.env)
    assert len(ctx.world.calls) == calls
    with pytest.raises(op.OperatorStop, match="STATE_DRIFT"):
        op.command_verify(ctx.env)


# ── R: execution terms ────────────────────────────────────────────────────────


def test_execution_terms_capture_fee_page_and_family_cohort_sufficiency(ctx) -> None:
    op.command_prepare(ctx.env)
    ctx.world.clock = datetime(2026, 10, 19, 14, 0, tzinfo=timezone.utc)  # 10-19 markets still open: pre-close capture
    op.command_accrue(ctx.env)
    ctx.world.clock = NOW
    report = op.command_accrue(ctx.env)
    states = report["execution_evidence_states"]
    assert states == {"FEES": "AVAILABLE", "LATENCY": "MISSING", "PARTIAL_FILL": "MISSING", "RESOLUTION_RULES": "AVAILABLE",
                      "SPREAD_DEPTH": "PARTIAL", "TICK_SIZE_MIN_ORDER": "AVAILABLE"}
    assert [c for c in ctx.world.calls if c[1] == oa.FEE_DOC_URL]
    internal = op.build_seal(ctx.env, op.load_plan(ctx.env), ledger(ctx),
                             op._jsonl(ctx.env.workspace / op.SEALED_DIRNAME / op.SEALED_RECORDS_FILENAME), NOW)[0]  # noqa: SLF001
    fees = internal["bundle"]["execution_evidence"]["FEES"]
    assert fees["state"] == "AVAILABLE" and fees["evidence_reference_ids"]
    assert internal["bundle"]["execution_evidence"]["TICK_SIZE_MIN_ORDER"]["official_tick_change_semantics"] == \
        "NOT_CAPTURED_NO_AUTHORIZED_EXACT_SOURCE"
    early = op.build_seal(ctx.env, op.load_plan(ctx.env), ledger(ctx),
                          op._jsonl(ctx.env.workspace / op.SEALED_DIRNAME / op.SEALED_RECORDS_FILENAME),  # noqa: SLF001
                          datetime(2026, 10, 19, 13, 0, tzinfo=timezone.utc))[0]
    assert early["bundle"]["execution_evidence"]["FEES"]["state"] == "MISSING"  # never backdated


def test_fee_page_redirect_and_throttle_follow_frozen_policy() -> None:
    sleeps: list[float] = []

    def scripted(responses):
        queue = list(responses)

        def fetch(method, url, headers, timeout):
            assert method == "GET" and url == oa.FEE_DOC_URL
            return queue.pop(0)
        return fetch

    ledger_ = op.AccrualLedger()
    response = op.fetch_fee_document(ledger_, scripted([(429, {"retry-after": "9"}, b""), (503, {}, b""), (200, {}, FEE_HTML)]),
                                     sleeps.append)
    assert response.body == FEE_HTML and sleeps == [9, 8] and ledger_.attempts == 3
    with pytest.raises(op.TransportFailure, match="NETWORK_REDIRECT_REFUSED"):
        op.fetch_fee_document(op.AccrualLedger(), scripted([(301, {"location": "https://evil.example/"}, b"")]), sleeps.append)
    with pytest.raises(op.TransportFailure, match="HTTP_503"):
        op.fetch_fee_document(op.AccrualLedger(), scripted([(503, {}, b"")] * 4), sleeps.append)
    assert not oa.fee_document_valid("https://docs.polymarket.com/fees", 200, FEE_HTML)


# ── R: probe ──────────────────────────────────────────────────────────────────


def probe_ctx(tmp_path, monkeypatch) -> SimpleNamespace:
    market = Market("4099280", 0x28, date(2026, 9, 29), datetime(2026, 9, 28, 11, 9, 14, tzinfo=timezone.utc))
    world = World(default_markets() + [market])
    world.clock = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    return build_env(tmp_path, monkeypatch, world)


def test_probe_sources_bounded_pre_oos_and_one_shot(tmp_path, monkeypatch) -> None:
    ctx = probe_ctx(tmp_path, monkeypatch)
    report = op.command_probe(ctx.env)
    assert report["status"] == "PROBE_PASS" and report["oos_or_prospective_data_created"] is False
    assert set(report["checks"]) == {"fee_document", "pendulumflow_audit", "pendulumflow_discovery", "gamma_identity",
                                     "rule_semantics", "nws_station", "pendulumflow_targeted_read", "ndfd_listing_object"}
    network = report["network"]
    assert network["attempts"] <= op.PROBE_MAX_ATTEMPTS and network["bytes"] <= op.PROBE_MAX_BYTES
    assert network["max_single_response"] <= op.PROBE_MAX_SINGLE_RESPONSE and network["pendulumflow_hours"] <= 4
    hours = {url.split("/v3/")[1][:13] for _m, url, _r in ctx.world.calls if "/v3/" in url}
    assert hours <= {"2026-09-28/11", "2026-09-28/12"} and all(v3.hour_start(h) < oa.parse_utc(oa.OOS_START) for h in hours)
    assert not ctx.env.workspace.exists()
    with pytest.raises(op.OperatorStop, match="PROBE_ALREADY_RECORDED"):
        op.command_probe(ctx.env)


def test_probe_fee_failure_and_post_oos_refusal(tmp_path, monkeypatch) -> None:
    ctx = probe_ctx(tmp_path, monkeypatch)
    ctx.world.fail(lambda url, _h: url == oa.FEE_DOC_URL, [404])
    with pytest.raises(op.OperatorStop, match="EXECUTION_TERMS_SOURCE_UNAVAILABLE"):
        op.command_probe(ctx.env)
    late = probe_ctx(tmp_path / "late", monkeypatch)
    late.world.clock = datetime(2026, 10, 15, tzinfo=timezone.utc)
    with pytest.raises(op.OperatorStop, match="PROBE_AFTER_OOS_START"):
        op.command_probe(late.env)


# ── R: static authority boundaries ────────────────────────────────────────────


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            names |= {f"{node.module}.{alias.name}" for alias in node.names}
    return names


def test_no_candidate_gate_wp170_score_scheduler_or_mutation_surface() -> None:
    for rel in ("tools/qualification/run_s10_qual_data_03.py", "src/data_layer/analytical_research/qualification_oos_accrual.py"):
        path = ROOT / rel
        text = path.read_text(encoding="utf-8")
        imports = _imports(path)
        for banned in ("qualification_gate", "experiment_os", "experiment_registry", "sched", "threading", "asyncio",
                       "websockets", "multiprocessing", "crontab", "schedule"):
            assert not any(name == banned or name.endswith("." + banned) or name.startswith(banned + ".") for name in imports), (rel, banned)
        for token in ("build_qualification_candidate", "run_qualification_gate", "PreregisteredExperiment", "brier", "log_loss",
                      "\"POST\"", "Popen(", "CronCreate", "send_later", "authorization", "api_key", "private_key"):
            assert token not in text, (rel, token)
    assert oa.MAX_QUALIFICATION_PROVENANCE_MANIFESTS == qualification_module.MAX_QUALIFICATION_PROVENANCE_MANIFESTS
    assert op.ALLOWED_HOSTS == {"archive.pendulumflow.com", "noaa-ndfd-pds.s3.amazonaws.com", "gamma-api.polymarket.com",
                                "api.weather.gov", "help.polymarket.com"}
    assert op.FEE_URL == "https://help.polymarket.com/en/articles/13364478-trading-fees"


def test_malformed_trade_price_is_source_invalid_not_a_wedge(tmp_path, monkeypatch) -> None:
    world = World()
    market = world.markets["4100180"]
    market.bid_ask = ("0.10", "0.60")  # spread too wide: the trade path is required
    trade_time = market.created + timedelta(minutes=55)  # inside the scanned checkpoint hour
    world.extra_rows[v3.hour_key(trade_time)] = {"last_trade_price": [{
        "timestamp_received": trade_time, "sequence": 4, "timestamp": trade_time, "market": cid(market.byte),
        "asset_id": tok(market.yes), "price": None, "size": Decimal("1"), "side": "BUY", "fee_rate_bps": 0,
        "transaction_hash": b""}]}
    ctx = build_env(tmp_path, monkeypatch, world)
    op.command_prepare(ctx.env)
    op.command_accrue(ctx.env)
    entry = next(e for e in ledger(ctx) if e["subject_id"] == "4100180")
    assert {r["checkpoint_id"]: r["reason"] for r in entry["rows"]}[A] == "MARKET_HISTORY_SOURCE_INVALID"
    assert op.command_verify(ctx.env)["status"] == "VERIFIED"


def test_identity_inconsistent_market_recorded_once_across_runs(tmp_path, monkeypatch) -> None:
    world = World()
    market = world.markets["4100190"]
    clone = market.new_market_row(market.created + timedelta(seconds=3))
    clone["market"] = cid(0x77)
    world.extra_rows["2026-10-18/11"] = {"new_market": [clone]}
    ctx = build_env(tmp_path, monkeypatch, world)
    op.command_prepare(ctx.env)
    ctx.world.clock = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)  # 10-19 stays pending (label finality)
    op.command_accrue(ctx.env)
    op.command_accrue(ctx.env)
    ctx.world.clock = NOW
    op.command_accrue(ctx.env)
    entries = [e for e in ledger(ctx) if e["subject_id"] == "4100190"]
    assert len(entries) == 1 and entries[0]["market_exclusion"] == "V3_MARKET_IDENTITY_INCONSISTENT"
    assert op.command_verify(ctx.env)["runs_replayed"] == 3
