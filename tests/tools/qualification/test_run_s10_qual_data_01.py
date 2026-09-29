"""S10-QUAL-DATA-01 operator tests (R004, R005, R025, R026, R028).

Fully hermetic: every HTTP exchange goes through a fake transport, Gamma through a fake client,
NDFD decoding through a fake decoder built on the real header pre-parse, the Alpha registry
verifier is replaced by a content-keyed fake, and every workspace lives in ``tmp_path``. A
module-wide socket guard proves no real network is ever attempted.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import socket
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

import tools.qualification.run_s10_qual_data_01 as operator
from src.data_layer.analytical_research import nws_ndfd_history as ndfd
from src.data_layer.analytical_research.alpha_factory_registry import initialize_alpha_factory_registry
from src.data_layer.polymarket.errors import PolymarketHTTPError

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "s10_qual_data_v3_builders", ROOT / "tests" / "data_layer" / "analytical_research" / "test_pendulumflow_v3.py")
builders = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builders)  # type: ignore[union-attr]

FIXTURE = ROOT / "tests" / "fixtures" / "ndfd_grib" / "ndfd_pop12_reference.grib2"
YES = "104019219973195927512773044938021400951414920684302388248992716945822821205929"
NO = "113167652799514890762834887413625876113191931693034136211969831764710778770543"
MARKETS = {  # market id -> (condition byte, slug)
    "3719310": (0x0F, "where-will-it-rain-on-september-3-2026-new-york-ny"),
    "3719311": (0x2A, "where-will-it-rain-on-october-3-2026-new-york-ny"),
    "3719312": (0x3B, "where-will-it-rain-on-september-3-2026-miami-fl"),
    "3719313": (0x4C, "where-will-it-rain-on-september-3-2026-denver-co"),
}
NDFD_KEY = "wmo/pop12/2026/09/03/YDUZ98_KWBN_202609031046"


# ── socket guard (R026) ───────────────────────────────────────────────────────

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


# ── synthetic world ───────────────────────────────────────────────────────────


def ts(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def cid(byte: int) -> bytes:
    return bytes([byte]) * 32


def tok(decimal_id: str) -> bytes:
    return int(decimal_id).to_bytes(32, "big")  # observed v3 token-id shape


def _new_market(market_id: str, received: str) -> dict[str, object]:
    byte, slug = MARKETS[market_id]
    tokens = [YES, NO] if market_id == "3719310" else [f"{market_id}1", f"{market_id}2"]
    return {"timestamp_received": ts(received), "sequence": 1, "timestamp": ts(received), "market": cid(byte),
            "id": market_id, "assets_ids": [tok(t) for t in tokens], "outcomes": ["Yes", "No"],
            "question": "Will it rain?", "slug": slug}


def _bba(received: str, bid: str, ask: str, asset: str = YES) -> dict[str, object]:
    return {"timestamp_received": ts(received), "sequence": 3, "timestamp": ts(received), "market": cid(0x0F),
            "asset_id": tok(asset), "best_bid": Decimal(bid), "best_ask": Decimal(ask), "spread": Decimal(ask) - Decimal(bid)}


def build_world() -> dict[str, tuple[bytes, dict[str, object]]]:
    hours = {
        "2026-09-03/11": {
            "new_market": [_new_market(m, "2026-09-03T11:09:14.805697Z") for m in MARKETS]
            + [_new_market("3719310", "2026-09-03T11:09:16.414571Z")],
            "best_bid_ask": [_bba("2026-09-03T11:30:00Z", "0.30", "0.40")],
        },
        "2026-09-03/12": {
            "best_bid_ask": [_bba("2026-09-03T12:05:00.000001Z", "0.31", "0.39"),
                             _bba("2026-09-03T12:30:00Z", "0.99", "0.99"),
                             _bba("2026-09-03T12:06:00Z", "0.60", "0.70", asset=NO)],
            "last_trade_price": [{"timestamp_received": ts("2026-09-03T12:02:00Z"), "sequence": 4, "timestamp": ts("2026-09-03T12:01:59Z"),
                                  "market": cid(0x0F), "asset_id": tok(YES), "price": Decimal("0.35"), "size": Decimal("5"),
                                  "side": "BUY", "fee_rate_bps": 1000, "transaction_hash": b"\x01"}],
            "tick_size_change": [{"timestamp_received": ts("2026-09-03T12:00:30Z"), "sequence": 5, "timestamp": ts("2026-09-03T12:00:30Z"),
                                  "market": cid(0x0F), "asset_id": tok(YES), "old_tick_size": Decimal("0.01"), "new_tick_size": Decimal("0.001")}],
        },
        "2026-09-04/14": {
            "market_resolved": [{"timestamp_received": ts("2026-09-04T14:18:58.893393Z"), "sequence": 6, "timestamp": ts("2026-09-04T14:17:58Z"),
                                 "market": cid(0x0F), "id": "3719310", "assets_ids": [tok(YES), tok(NO)],
                                 "winning_asset_id": tok(NO), "winning_outcome": "No"}],
        },
    }
    return {hour: builders.build_v3_hour(hour, rows) for hour, rows in hours.items()}


def wmo_object() -> bytes:
    return b"\x01\r\r\n001\r\r\nYDUB12 KWBN 031046\r\r\n" + FIXTURE.read_bytes() + b"\r\r\n\x03"


def listing(prefix: str) -> bytes:
    contents = ""
    if prefix == "wmo/pop12/2026/09/03/":
        contents = f"<Contents><Key>{NDFD_KEY}</Key><LastModified>2026-09-03T10:51:56.000Z</LastModified><Size>{len(wmo_object())}</Size></Contents>"
    return ('<?xml version="1.0" encoding="UTF-8"?><ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
            f"<Name>noaa-ndfd-pds</Name><Prefix>{prefix}</Prefix><IsTruncated>false</IsTruncated>{contents}</ListBucketResult>").encode()


RULE = (
    'This market will resolve to "Yes" if New York, NY records measurable precipitation on September 3, 2026. '
    "Measurable precipitation means 0.01 inches or more as reported by the PRECIPITATION (IN) figure in the NWS Daily "
    "Climate Report (CLI) for the city's station. A report of trace (\"T\") does not qualify. The observation period is "
    "the NWS climate day for KNYC: midnight to midnight local standard time. Resolution is based on the station's first "
    "published precipitation figure for the day. Subsequent revisions or corrections to the published data will not be "
    "considered; the first published value is final. The resolution source for this market is the NWS Daily Climate Report (CLI) for KNYC."
)


def gamma_document(market_id: str) -> dict[str, object]:
    byte, slug = MARKETS[market_id]
    tokens = [YES, NO] if market_id == "3719310" else [f"{market_id}1", f"{market_id}2"]
    document = {
        "id": market_id, "conditionId": "0x" + cid(byte).hex(), "slug": slug, "clobTokenIds": json.dumps(tokens),
        "outcomes": json.dumps(["Yes", "No"]), "outcomePrices": json.dumps(["0", "1"]), "closed": True,
        "umaResolutionStatus": "resolved", "startDate": "2026-09-03T11:09:13Z", "closedTime": "2026-09-04 14:18:05.177609+00",
        "description": RULE, "resolutionSource": "https://forecast.weather.gov/product.php?issuedby=NYC&product=CLI",
        "feesEnabled": True, "feeType": "weather_fees", "orderMinSize": 5, "orderPriceMinTickSize": 0.001,
    }
    if market_id == "3719312":
        document["conditionId"] = "0x" + cid(0x99).hex()  # Gamma/v3 identity mismatch
    if market_id == "3719313":
        document["closed"] = False  # not final
    return document


class FakeGammaClient:
    def __init__(self, world: "FakeWorld") -> None:
        self.world = world

    def get_market(self, market_id: str):
        self.world.gamma_calls.append(market_id)
        if market_id not in MARKETS:
            raise PolymarketHTTPError(404, "https://gamma-api.polymarket.com/markets/" + market_id)
        document = self.world.gamma_override.get(market_id) or gamma_document(market_id)
        return SimpleNamespace(data=document, request_info=SimpleNamespace(status_code=200))


class FakeWorld:
    def __init__(self) -> None:
        self.hours = build_world()
        self.calls: list[tuple[str, str, str | None]] = []
        self.gamma_calls: list[str] = []
        self.gamma_override: dict[str, dict[str, object]] = {}

    def fetch(self, method: str, url: str, headers, timeout):
        self.calls.append((method, url, headers.get("Range")))
        parts = url.split("/", 3)
        host, path = parts[2], "/" + (parts[3] if len(parts) > 3 else "")
        lm = {"last-modified": "Wed, 09 Sep 2026 00:00:00 GMT"}
        if host == operator.PENDULUMFLOW_HOST:
            if path == "/audit":
                return 200, {}, builders.audit_html(["2026-08-18/06"])
            _v3, day, hh, name = path.strip("/").split("/")
            hour = f"{day}/{hh}"
            if hour not in self.hours:
                return 404, {}, b"not found"
            data, manifest = self.hours[hour]
            if name == "manifest.json":
                return 200, {}, json.dumps(manifest).encode()
            start, end = (int(x) for x in headers["Range"][len("bytes="):].split("-"))
            return 206, {**lm, "content-range": f"bytes {start}-{end}/{len(data)}"}, data[start:end + 1]
        if host == ndfd.BUCKET_HOST:
            if path.startswith("/?"):
                prefix = url.split("prefix=")[1].replace("%2F", "/")
                return 200, {}, listing(prefix)
            if path == "/" + NDFD_KEY:
                return 200, {"last-modified": "Thu, 03 Sep 2026 10:51:56 GMT"}, wmo_object()
            return 404, {}, b""
        if host == operator.NWS_HOST and path == "/stations/KNYC":
            return 200, {}, json.dumps({"geometry": {"type": "Point", "coordinates": [-73.96667, 40.78333]},
                                        "properties": {"stationIdentifier": "KNYC", "timeZone": "America/New_York",
                                                       "name": "New York City, Central Park"}}).encode()
        return 404, {}, b""


def fake_decode(message: bytes, stations):
    header = ndfd.parse_pop12_header(message)
    values = tuple(ndfd.StationValue(s.station_id, 1846511, 40.775844, -73.970832, 1.03, 99) for s in stations)
    return ndfd.DecodedPop12(header, (("edition", 2),), values)


def fake_registry_verifier(path: Path) -> dict[str, object]:
    content = Path(path).read_bytes()
    if not content.startswith(b"GENUINE"):
        raise ValueError("REGISTRY_INVALID")
    head = content.decode().split(":", 1)[1] if b":" in content else operator.qd.ALPHA_REGISTRY_HEAD
    return {"total_rows": 15, "head_entry_hash": head, "candidate_id": operator.qd.ALPHA_CANDIDATE_ID,
            "family_id": operator.qd.ALPHA_FAMILY_ID, "episode_id": operator.qd.ALPHA_EPISODE_ID,
            "result_state": "RESEARCH_SUPPORTIVE", "entry_hashes": [head]}


@pytest.fixture()
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = tmp_path / "repo"
    for rel in (*operator.CODE_FILES, operator.AF1_EVIDENCE_PATH):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, repo / rel)
    roots = [tmp_path / "wt-a", tmp_path / "wt-b", tmp_path / "wt-empty"]
    for root in roots[:2]:
        registry = root.joinpath(*operator.ALPHA_REGISTRY_RELATIVE)
        registry.parent.mkdir(parents=True, exist_ok=True)
        registry.write_bytes(b"GENUINE")
    fake = FakeWorld()
    state = {"branch": operator.PINNED_BRANCH, "dirty": "", "roots": roots}

    def git(*args: str) -> str:
        if args[:2] == ("worktree", "list"):
            return "".join(f"worktree {r}\nHEAD {'a' * 40}\n\n" for r in state["roots"])
        if args == ("rev-parse", "HEAD"):
            return "a" * 40 + "\n"
        if args == ("rev-parse", "--abbrev-ref", "HEAD"):
            return state["branch"] + "\n"
        if args[0] == "status":
            return state["dirty"]
        if args[0] == "merge-base":
            return ""
        raise AssertionError(args)

    monkeypatch.setattr(operator, "verify_alpha_registry", fake_registry_verifier)
    monkeypatch.setattr(operator, "PROBE_HOUR", "2026-09-03/11")
    monkeypatch.setattr(operator, "PROBE_MARKET_HOUR", "2026-09-03/12")
    env = operator.Environment(repo_root=repo, git=git, fetch=fake.fetch, gamma_client_factory=lambda: FakeGammaClient(fake),
                               decode_fn=fake_decode, require_decoder=False)
    NETWORK_ATTEMPTS.clear()
    return SimpleNamespace(env=env, fake=fake, state=state, repo=repo, roots=roots, tmp=tmp_path)


def run_all(world) -> dict[str, object]:
    operator.command_prepare(world.env)
    operator.command_probe(world.env)
    return operator.command_run(world.env)


# ── R004 / R005 ───────────────────────────────────────────────────────────────


def test_prepare_verifies_and_copies_genuine_alpha_registry(world) -> None:
    result = operator.command_prepare(world.env)
    assert result["status"] == "PREPARED"
    workspace = world.env.workspace
    copy = workspace / operator.REGISTRY_COPY_FILENAME
    assert copy.read_bytes() == b"GENUINE"
    plan_text = (workspace / operator.PLAN_FILENAME).read_text(encoding="utf-8")
    plan = json.loads(plan_text)
    assert plan["alpha_registry"]["verified_copies_found"] == 2  # two byte copies of one semantic snapshot
    assert plan["alpha_registry"]["head_entry_hash"] == operator.qd.ALPHA_REGISTRY_HEAD
    for root in world.roots:
        assert str(root) not in plan_text and root.name not in plan_text  # no source absolute path
    assert operator.command_prepare(world.env)["status"] == "PREPARED_IDEMPOTENT"
    # Two semantically different valid snapshots conflict.
    shutil.rmtree(workspace)
    world.roots[1].joinpath(*operator.ALPHA_REGISTRY_RELATIVE).write_bytes(b"GENUINE:alpharegistryentry:sha256:" + b"0" * 64)
    with pytest.raises(operator.OperatorStop) as excinfo:
        operator.command_prepare(world.env)
    assert excinfo.value.code == "ALPHA_LINEAGE_CONFLICT"
    # Zero valid snapshots (missing or invalid files) is missing evidence; never reconstructed.
    for root in world.roots[:2]:
        root.joinpath(*operator.ALPHA_REGISTRY_RELATIVE).write_bytes(b"not a registry")
    with pytest.raises(operator.OperatorStop) as excinfo:
        operator.command_prepare(world.env)
    assert excinfo.value.code == "ALPHA_LINEAGE_EVIDENCE_MISSING"
    assert not (workspace / operator.PLAN_FILENAME).exists()
    world.state["roots"] = [world.tmp / "nowhere"]
    with pytest.raises(operator.OperatorStop) as excinfo:
        operator.command_prepare(world.env)
    assert excinfo.value.code == "ALPHA_LINEAGE_EVIDENCE_MISSING"


def test_real_registry_verifier_rejects_non_genuine_registry(tmp_path: Path) -> None:
    # No monkeypatch here: the operator's real verifier uses the merged Alpha registry API.
    assert operator.verify_alpha_registry is not fake_registry_verifier
    empty = tmp_path / "alpha_registry.sqlite3"
    assert initialize_alpha_factory_registry(str(empty)).is_valid
    with pytest.raises(ValueError):
        operator.verify_alpha_registry(empty)  # valid registry, wrong semantic snapshot
    bogus = tmp_path / "bogus.sqlite3"
    bogus.write_bytes(b"GENUINE")
    with pytest.raises(ValueError):
        operator.verify_alpha_registry(bogus)  # not a registry at all


def test_prepare_refuses_dirty_or_wrong_branch_and_conflicting_workspace(world) -> None:
    world.state["dirty"] = " M docs/project_status.md\n"
    with pytest.raises(operator.OperatorStop) as excinfo:
        operator.command_prepare(world.env)
    assert excinfo.value.code == "STATE_DRIFT"
    world.state["dirty"] = ""
    world.state["branch"] = "main"
    with pytest.raises(operator.OperatorStop):
        operator.command_prepare(world.env)
    world.state["branch"] = operator.PINNED_BRANCH
    world.env.workspace.mkdir(parents=True)
    (world.env.workspace / "stray.txt").write_text("x", encoding="utf-8")
    with pytest.raises(operator.OperatorStop) as excinfo:
        operator.command_prepare(world.env)
    assert excinfo.value.code == "PREPARE_WORKSPACE_CONFLICT"


def test_af1_receipt_revalidated_and_bound(world) -> None:
    result = operator.verify_af1(world.repo)
    assert result == {"gate_receipt_id": operator.qd.AF1_RECEIPT_ID, "overall_disposition": "AF1_PASS",
                      "evidence_state": "FINALIZED", "dimensions_pass": 10}
    evidence_path = world.repo / operator.AF1_EVIDENCE_PATH
    original = json.loads(evidence_path.read_text(encoding="utf-8"))
    for mutate in (
        lambda d: d["gate_receipt"].__setitem__("overall_disposition", "AF1_FAIL"),
        lambda d: d["gate_receipt"].__setitem__("gate_receipt_id", "af1gate:sha256:" + "0" * 64),
        lambda d: d["gate_receipt"].__setitem__("evidence_state", "PENDING_RUNTIME"),
        lambda d: d.pop("gate_receipt"),
    ):
        document = json.loads(json.dumps(original))
        mutate(document)
        evidence_path.write_text(json.dumps(document), encoding="utf-8")
        with pytest.raises(operator.OperatorStop) as excinfo:
            operator.verify_af1(world.repo)
        assert excinfo.value.code == "AF1_EVIDENCE_DRIFT"
    evidence_path.write_text("{broken", encoding="utf-8")
    with pytest.raises(operator.OperatorStop):
        operator.verify_af1(world.repo)


# ── R025 transport / allowlist / budget ───────────────────────────────────────


def test_transport_allowlist_methods_budget_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    ua = {"User-Agent": operator.USER_AGENT}
    assert operator.validate_request("GET", "https://archive.pendulumflow.com/v3/2026-09-03/12/manifest.json", ua)
    assert operator.validate_request("GET", "https://noaa-ndfd-pds.s3.amazonaws.com/?list-type=2&prefix=wmo%2Fpop12%2F2026%2F09%2F03%2F", ua)
    refused = [
        ("POST", "https://archive.pendulumflow.com/audit", ua, "METHOD_NOT_ALLOWED"),
        ("DELETE", "https://api.weather.gov/stations/KNYC", ua, "METHOD_NOT_ALLOWED"),
        ("GET", "http://archive.pendulumflow.com/audit", ua, "URL_NOT_ALLOWED"),
        ("GET", "https://evil.example.com/audit", ua, "URL_NOT_ALLOWED"),
        ("GET", "https://user:pw@archive.pendulumflow.com/audit", ua, "URL_NOT_ALLOWED"),
        ("GET", "https://archive.pendulumflow.com:8443/audit", ua, "URL_NOT_ALLOWED"),
        ("GET", "https://archive.pendulumflow.com/v3/../secret", ua, "URL_NOT_ALLOWED"),
        ("GET", "https://archive.pendulumflow.com/audit?x=1", ua, "URL_NOT_ALLOWED"),
        ("GET", "https://api.weather.gov/points/40,-73", ua, "URL_NOT_ALLOWED"),
        ("GET", "https://gamma-api.polymarket.com/markets/keyset", ua, "URL_NOT_ALLOWED"),
        ("GET", "https://noaa-ndfd-pds.s3.amazonaws.com/?list-type=2&prefix=other%2F", ua, "URL_NOT_ALLOWED"),
        ("GET", "https://noaa-ndfd-pds.s3.amazonaws.com/", ua, "URL_NOT_ALLOWED"),
        ("GET", "https://api.weather.gov/stations/KNYC", {**ua, "Authorization": "Bearer x"}, "HEADER_NOT_ALLOWED"),
        ("GET", "https://api.weather.gov/stations/KNYC", {**ua, "Cookie": "a=b"}, "HEADER_NOT_ALLOWED"),
        ("GET", "https://archive.pendulumflow.com/audit", {**ua, "Range": "bytes=-5"}, "HEADER_NOT_ALLOWED"),
    ]
    for method, url, headers, code in refused:
        with pytest.raises(operator.TransportRefused) as excinfo:
            operator.validate_request(method, url, headers)
        assert excinfo.value.code == code, url

    calls: list[str] = []

    def scripted(responses):
        def fetch(method, url, headers, timeout):
            calls.append(url)
            item = responses.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        return fetch

    url = "https://api.weather.gov/stations/KNYC"
    ledger = operator.Ledger()
    transport = operator.BoundedTransport(ledger, scripted([(302, {"location": "https://evil.example.com/"}, b"")]))
    with pytest.raises(operator.TransportFailure) as excinfo:
        transport.request("GET", url)
    assert excinfo.value.code == "NETWORK_REDIRECT_REFUSED" and ledger.attempts == 1
    ledger = operator.Ledger()
    transport = operator.BoundedTransport(ledger, scripted([(503, {}, b""), (503, {}, b"")]))
    with pytest.raises(operator.TransportFailure) as excinfo:
        transport.request("GET", url)
    assert excinfo.value.code == "HTTP_503" and ledger.attempts == 2 and ledger.retries == 1  # exactly one retry
    ledger = operator.Ledger()
    transport = operator.BoundedTransport(ledger, scripted([operator._TransportError("TIMEOUT"), (200, {}, b"{}")]))
    assert transport.request("GET", url).body == b"{}" and ledger.attempts == 2 and ledger.retries == 1
    ledger = operator.Ledger()
    transport = operator.BoundedTransport(ledger, scripted([(404, {}, b"")]))
    with pytest.raises(operator.TransportFailure) as excinfo:
        transport.request("GET", url)
    assert excinfo.value.code == "HTTP_404" and ledger.retries == 0  # no semantic retry
    # Budgets fail closed: attempts, total bytes (pre-checked from the declared size), single response.
    ledger = operator.Ledger(attempts=operator.MAX_ATTEMPTS)
    calls.clear()
    with pytest.raises(operator.BudgetExhausted) as excinfo:
        operator.BoundedTransport(ledger, scripted([(200, {}, b"x")])).request("GET", url)
    assert excinfo.value.code == "ATTEMPT_BUDGET_EXHAUSTED" and calls == []
    ledger = operator.Ledger(bytes=operator.MAX_TOTAL_BYTES - 10)
    with pytest.raises(operator.BudgetExhausted) as excinfo:
        operator.BoundedTransport(ledger, scripted([(206, {}, b"x" * 100)])).request(
            "GET", "https://archive.pendulumflow.com/v3/2026-09-03/12/2026-09-03T12.parquet", byte_range=(0, 100))
    assert excinfo.value.code == "BYTE_BUDGET_EXHAUSTED" and calls == []
    ledger = operator.Ledger(bytes=operator.MAX_TOTAL_BYTES - 1)
    with pytest.raises(operator.BudgetExhausted):
        operator.BoundedTransport(ledger, scripted([(200, {}, b"xx")])).request("GET", url)
    assert ledger.bytes == operator.MAX_TOTAL_BYTES + 1  # counted truthfully, then fail closed
    with pytest.raises(operator.TransportRefused) as excinfo:
        operator.BoundedTransport(operator.Ledger(), scripted([])).request(
            "GET", "https://archive.pendulumflow.com/v3/2026-09-03/12/2026-09-03T12.parquet",
            byte_range=(0, operator.MAX_SINGLE_RESPONSE + 1))
    assert excinfo.value.code == "SINGLE_RESPONSE_CAP"
    monkeypatch.setattr(operator, "MAX_SINGLE_RESPONSE", 4)
    with pytest.raises(operator.TransportFailure) as excinfo:
        operator.BoundedTransport(operator.Ledger(), scripted([(200, {}, b"12345")])).request("GET", url)
    assert excinfo.value.code == "RESPONSE_TOO_LARGE"
    with pytest.raises(operator.TransportFailure) as excinfo:
        operator.BoundedTransport(operator.Ledger(), scripted([(206, {"content-range": "bytes 0-1/9"}, b"ab")])).request(
            "GET", "https://archive.pendulumflow.com/v3/2026-09-03/12/2026-09-03T12.parquet", byte_range=(0, 3))
    assert excinfo.value.code == "RANGE_RESPONSE_INVALID"
    store = operator.ArtifactStore(Path("unused"), None, replay=True)
    with pytest.raises(operator.TransportRefused):
        store.gamma_market("12; DROP", operator.Ledger())


# ── R026 / R027 / R028 end to end ─────────────────────────────────────────────


def test_operator_tests_hermetic_no_real_network(world) -> None:
    report = run_all(world)
    assert report["terminal"] == "QUAL_DATA_READY"
    assert NETWORK_ATTEMPTS == []
    hosts = {url.split("/")[2] for _m, url, _r in world.fake.calls}
    assert hosts <= operator.ALLOWED_HOSTS
    assert all(method == "GET" for method, _u, _r in world.fake.calls)
    assert world.fake.gamma_calls  # Gamma only through the (fake) PolymarketPublicClient seam
    assert not any("gamma-api" in url for _m, url, _r in world.fake.calls)


def test_end_to_end_ready_run_counts_and_rerun_refused(world) -> None:
    operator.command_prepare(world.env)
    probe = operator.command_probe(world.env)
    probe_calls, probe_gamma = len(world.fake.calls), len(world.fake.gamma_calls)
    assert probe["status"] == "PROBE_PASS" and probe["ledger"]["attempts"] == probe_calls + probe_gamma
    report = operator.command_run(world.env)
    bundle = json.loads((world.env.workspace / operator.BUNDLE_FILENAME).read_text(encoding="utf-8"))
    assert report["terminal"] == bundle["terminal"] == "QUAL_DATA_READY"
    assert bundle["terminal_reason"] == "EVIDENCE_COMPLETE_ROWS_PRESENT"
    counts = bundle["dataset"]["counts"]
    assert counts["discovered_candidates"] == 4 and counts["included_markets"] == 1
    assert counts["market_exclusion_reasons"] == {"GAMMA_V3_IDENTITY_MISMATCH": 1, "LABEL_GAMMA_NOT_FINAL": 1,
                                                  "TARGET_DATE_OUTSIDE_CORPUS": 1}
    assert counts["checkpoint_usable_rows"] == {"MARKET_OBSERVABLE_PLUS_60M_V1": 1, "TARGET_CLIMATE_DAY_START_V1": 0}
    assert counts["checkpoint_row_exclusion_reasons"]["TARGET_CLIMATE_DAY_START_V1"] == {"CHECKPOINT_B_MARKET_NOT_OPEN_60M": 1}
    assert counts["independent_target_dates"]["ANY_CHECKPOINT"] == 1
    row = bundle["rows"][0]
    assert row["checkpoint_time"] == "2026-09-03T12:09:14.805697Z"
    bba = row["feature_evidence"]["market_history"]["best_bid_ask"]
    assert (bba["best_bid"], bba["best_ask"], bba["timestamp_received"]) == ("0.31", "0.39", "2026-09-03T12:05:00.000001Z")
    assert row["feature_evidence"]["market_history"]["last_trade_price"]["fee_rate_bps"] == "1000"
    assert row["feature_evidence"]["weather"]["periods"][0]["pop12_percent"] == 99
    assert row["label_evidence"]["winning_outcome"] == "No"
    assert bundle["dataset"]["b0_contract_compatibility"] == "EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION"
    assert bundle["execution_evidence"]["3719310"]["FEES"]["state"] == "HISTORICALLY_EVIDENCED"
    assert len(row["provenance_manifest_ids"]) >= 3 and set(row["provenance_manifest_ids"]) <= set(bundle["dataset"]["ready_manifest_ids"])
    text = json.dumps(bundle)
    assert str(world.tmp) not in text and "SOURCE_KIND_CANONICAL_PIT" not in text
    ledger = report["network_ledger"]
    assert ledger["attempts"] == len(world.fake.calls) - probe_calls + len(world.fake.gamma_calls) - probe_gamma
    assert ledger["bytes"] > 0 and ledger["exhausted"] is None
    # ONE run only: a finalized run-01 refuses a second run and a conflicting prepare.
    with pytest.raises(operator.OperatorStop) as excinfo:
        operator.command_run(world.env)
    assert excinfo.value.code == "RUN_ALREADY_FINALIZED"
    assert operator.main(["run-readiness"], world.env) == 3


def test_verify_final_rederives_identities(world) -> None:
    run_all(world)
    calls_before = len(world.fake.calls)
    verified = operator.command_verify(world.env)
    assert verified["status"] == "VERIFIED" and verified["network_calls"] == 0
    assert len(world.fake.calls) == calls_before and NETWORK_ATTEMPTS == []
    bundle = json.loads((world.env.workspace / operator.BUNDLE_FILENAME).read_text(encoding="utf-8"))
    assert verified["bundle_id"] == bundle["bundle_id"] and verified["logical_dataset_id"] == bundle["logical_dataset_id"]
    assert verified["rehashed_artifacts"] > 10
    # Tampering with any retained raw artifact fails verification.
    raw = sorted((world.env.workspace / "raw").iterdir())[0]
    original = raw.read_bytes()
    raw.write_bytes(original + b"x")
    with pytest.raises(operator.OperatorStop) as excinfo:
        operator.command_verify(world.env)
    assert excinfo.value.code == "VERIFY_FAILED"
    raw.write_bytes(original)
    # Tampering with the sealed bundle fails verification.
    bundle_path = world.env.workspace / operator.BUNDLE_FILENAME
    tampered = json.loads(bundle_path.read_text(encoding="utf-8"))
    tampered["dataset"]["counts"]["included_markets"] = 99
    bundle_path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(operator.OperatorStop) as excinfo:
        operator.command_verify(world.env)
    assert excinfo.value.code == "VERIFY_FAILED"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    assert operator.command_verify(world.env)["status"] == "VERIFIED"
    # Code drift after the frozen plan is refused.
    code = world.repo / "src/data_layer/analytical_research/qualification_data_readiness.py"
    code.write_text(code.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
    with pytest.raises(operator.OperatorStop) as excinfo:
        operator.command_verify(world.env)
    assert excinfo.value.code == "CODE_DRIFT"


def test_budget_exhaustion_terminates_insufficient_and_replays(world, monkeypatch: pytest.MonkeyPatch) -> None:
    operator.command_prepare(world.env)
    operator.command_probe(world.env)
    # The budget is cumulative across a resumed run: seed the ledger 30 attempts below the frozen cap.
    operator.write_json_atomic(world.env.workspace / operator.LEDGER_FILENAME,
                               operator.Ledger(attempts=operator.MAX_ATTEMPTS - 30).to_mapping())
    report = operator.command_run(world.env)
    assert report["terminal"] == "QUAL_DATA_INSUFFICIENT" and report["terminal_reason"] == "FROZEN_BUDGET_EXHAUSTED"
    assert report["network_ledger"]["exhausted"] == "ATTEMPT_BUDGET_EXHAUSTED"
    assert report["network_ledger"]["attempts"] == operator.MAX_ATTEMPTS
    assert operator.command_verify(world.env)["terminal"] == "QUAL_DATA_INSUFFICIENT"


def test_probe_required_and_source_contract_drift_stops(world) -> None:
    operator.command_prepare(world.env)
    with pytest.raises(operator.OperatorStop) as excinfo:
        operator.command_run(world.env)
    assert excinfo.value.code == "PROBE_REQUIRED"
    world.fake.gamma_override["3719310"] = {**gamma_document("3719310"), "conditionId": "0x" + "ee" * 32}
    with pytest.raises(operator.OperatorStop) as excinfo:
        operator.command_probe(world.env)
    assert excinfo.value.code == "SOURCE_CONTRACT_DRIFT"
    probe = json.loads((world.env.workspace / operator.PROBE_FILENAME).read_text(encoding="utf-8"))
    assert probe["status"] == "SOURCE_CONTRACT_DRIFT"
    assert probe["failed_step"] == "gamma_by_id_identity" and probe["failure_code"] == "SOURCE_CONTRACT_DRIFT"
    assert probe["checks"] == {"v3_manifest_product_range_sha256": "PASS"}
    with pytest.raises(operator.OperatorStop) as excinfo:
        operator.command_verify(world.env)
    assert excinfo.value.code == "RUN_NOT_FINAL"


def test_cli_prints_closed_codes_only(world, capsys: pytest.CaptureFixture[str]) -> None:
    assert operator.main(["bogus"], world.env) == 2
    assert capsys.readouterr().out.strip() == "STOP USAGE_ERROR"
    assert operator.main(["verify-final"], world.env) == 3
    output = capsys.readouterr().out
    assert output.strip() == "STOP PLAN_MISSING" and str(world.tmp) not in output
    assert operator.main(["prepare"], world.env) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "PREPARED" and set(summary) <= {"status", "plan_sha256"}
