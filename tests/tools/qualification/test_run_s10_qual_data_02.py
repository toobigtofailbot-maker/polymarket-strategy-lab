"""S10-QUAL-DATA-02 operator tests (seed admission, D011 read state, throttle policy, caps, replay).

Fully hermetic: the PR #202 seed is produced in ``tmp_path`` by the unchanged S10-QUAL-DATA-01
operator against the same synthetic world its own tests use, every HTTP exchange goes through a
fake transport with scripted faults, Gamma through a fake client, NDFD decoding through a fake
decoder, sleeping through a recording no-sleep seam, and a module-wide socket guard proves no
real network is ever attempted.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import shutil
import socket
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

import tools.qualification.run_s10_qual_data_01 as d1
import tools.qualification.run_s10_qual_data_02 as op
from src.data_layer.analytical_research import pendulumflow_v3 as v3
from src.data_layer.analytical_research import qualification_data_readiness as qd
from src.data_layer.polymarket.errors import PolymarketHTTPError

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "s10_qual_data_01_operator_world", ROOT / "tests" / "tools" / "qualification" / "test_run_s10_qual_data_01.py")
w1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(w1)  # type: ignore[union-attr]

A, B = qd.CHECKPOINT_A, qd.CHECKPOINT_B
HOUR = "2026-09-03/12"
B_HOUR = "2026-09-04/05"  # checkpoint-B walk hour of market 3719314 (never a discovery hour)
PF_URL = "https://archive.pendulumflow.com/v3/2026-09-03/12/2026-09-03T12.parquet"

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


# ── synthetic world with scripted faults ──────────────────────────────────────


class FaultyWorld(w1.FakeWorld):
    """The S10-QUAL-DATA-01 synthetic world, completed with the empty label-window hours a real
    archive always serves, plus scripted per-request faults ``(predicate, [status, ...])``."""

    def __init__(self) -> None:
        super().__init__()
        for hour in ("2026-09-04/13", "2026-09-05/13"):
            self.hours[hour] = w1.builders.build_v3_hour(hour, {})
        # A real archive hour is far larger than PyArrow's 64 KiB speculative footer read; pad the
        # tail of this hour so its best_bid_ask / last_trade_price column chunks need their own
        # targeted range reads (the chunk stage), exactly as on the real archive.
        self.hours[B_HOUR] = w1.builders.build_v3_hour(B_HOUR, {
            "best_bid_ask": [w1._bba("2026-09-04T05:30:00Z", "0.90", "0.95", asset="37193141", market=0x5D)],
            # A trade after checkpoint B: its row group must be read, but it is never selectable.
            "last_trade_price": [{"timestamp_received": w1.ts("2026-09-04T05:40:00Z"), "sequence": 4,
                                  "timestamp": w1.ts("2026-09-04T05:40:00Z"), "market": w1.cid(0x5D),
                                  "asset_id": w1.tok("37193141"), "price": Decimal("0.9"), "size": Decimal("1"),
                                  "side": "BUY", "fee_rate_bps": 0, "transaction_hash": b""}],
            "tick_size_change": [_tick_filler(i) for i in range(3000)],
        })
        self.faults: list[tuple[object, list[tuple[int, dict[str, str]]]]] = []

    def fail(self, predicate, statuses, headers=None) -> None:
        self.faults.append((predicate, [(s, dict(headers or {})) for s in statuses]))

    def fetch(self, method, url, headers, timeout):
        for predicate, remaining in self.faults:
            if remaining and predicate(url, headers):
                status, extra = remaining.pop(0)
                self.calls.append((method, url, headers.get("Range")))
                return status, extra, b""
        return super().fetch(method, url, headers, timeout)

    def product_range(self, hour: str, family: str):
        start, end = self.hours[hour][1]["products"][family]["byte_range"]
        path = v3.parquet_object_path(hour)

        def predicate(url, headers):
            if not url.endswith(path) or "Range" not in headers:
                return False
            first = int(headers["Range"][len("bytes="):].split("-")[0])
            return start <= first < end
        return predicate


def _tick_filler(i: int) -> dict[str, object]:
    market = hashlib.sha256(b"filler-%d" % i).digest()
    return {"timestamp_received": w1.ts("2026-09-04T05:10:00Z"), "sequence": i + 10, "timestamp": w1.ts("2026-09-04T05:10:00Z"),
            "market": market, "asset_id": hashlib.sha256(market).digest(), "old_tick_size": Decimal("0.01"),
            "new_tick_size": Decimal("0.001")}


def persistent_503(world: FaultyWorld, predicate) -> None:
    world.fail(predicate, [503] * (1 + op.MAX_THROTTLE_RETRIES))


def build_seed(tmp_path: Path, fake: FaultyWorld) -> Path:
    """A genuine S10-QUAL-DATA-01 run-01 (budget-exhausted, with a failed 503 entry) + verify-final."""

    repo = tmp_path / "seed-worktree"
    for rel in (*d1.CODE_FILES, d1.AF1_EVIDENCE_PATH):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, repo / rel)
    registry = repo.joinpath(*d1.ALPHA_REGISTRY_RELATIVE)
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_bytes(b"GENUINE")

    def git(*args: str) -> str:
        if args[:2] == ("worktree", "list"):
            return f"worktree {repo}\n\n"
        if args == ("rev-parse", "HEAD"):
            return "b" * 40 + "\n"
        if args == ("rev-parse", "--abbrev-ref", "HEAD"):
            return d1.PINNED_BRANCH + "\n"
        return ""

    env = d1.Environment(repo_root=repo, git=git, fetch=fake.fetch, gamma_client_factory=lambda: w1.FakeGammaClient(fake),
                         decode_fn=w1.fake_decode, require_decoder=False)
    d1.command_prepare(env)
    d1.command_probe(env)
    # The predecessor's archive throttled one discovery hour past its single immediate retry.
    fake.fail(lambda url, _h: url.endswith(v3.manifest_object_path("2026-08-19/11")), [503, 503])
    d1.write_json_atomic(env.workspace / d1.LEDGER_FILENAME, d1.Ledger(attempts=d1.MAX_ATTEMPTS - 93).to_mapping())
    report = d1.command_run(env)
    assert report["terminal_reason"] == "FROZEN_BUDGET_EXHAUSTED"
    assert d1.command_verify(env)["status"] == "VERIFIED"
    index = json.loads((env.workspace / d1.INDEX_FILENAME).read_text(encoding="utf-8"))
    # The predecessor stopped before labels and market history: those are completion work.
    later = ("2026-09-04/04", "2026-09-04/05", "2026-09-04/13", "2026-09-04/14", "2026-09-05/13", "2026-09-05/14")
    assert not any(hour in key for key in index for hour in later)
    assert any("via=" in key for key in index) and any("/stations/" in key for key in index)
    return repo


@pytest.fixture()
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(d1, "verify_alpha_registry", w1.fake_registry_verifier)
    monkeypatch.setattr(d1, "PROBE_HOUR", "2026-09-03/11")
    monkeypatch.setattr(d1, "PROBE_MARKET_HOUR", HOUR)
    monkeypatch.setattr(op, "PROBE_HOUR", "2026-09-03/11")
    monkeypatch.setattr(op, "PROBE_MARKET_HOUR", HOUR)
    fake = FaultyWorld()
    seed_repo = build_seed(tmp_path, fake)
    seed = seed_repo.joinpath(*op.SEED_PARTS)
    bundle = json.loads((seed / d1.BUNDLE_FILENAME).read_text(encoding="utf-8"))
    monkeypatch.setattr(op, "SEED_BUNDLE_ID", bundle["bundle_id"])
    monkeypatch.setattr(op, "SEED_DATASET_ID", bundle["logical_dataset_id"])
    fake.calls.clear()
    fake.gamma_calls.clear()
    repo = tmp_path / "repo"
    for rel in (*op.CODE_FILES, d1.AF1_EVIDENCE_PATH):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, repo / rel)
    state = {"branch": op.PINNED_BRANCH, "dirty": "", "roots": [seed_repo, repo, tmp_path / "empty"]}

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

    blobs: dict[str, bytes] = {}

    def git_blob(revision: str, path: str) -> bytes:
        assert revision == op.PREDECESSOR_HEAD
        return blobs.get(path, (seed_repo / path).read_bytes())

    sleeps: list[float] = []
    env = op.Environment(repo_root=repo, git=git, git_blob=git_blob, fetch=fake.fetch,
                         gamma_client_factory=lambda: w1.FakeGammaClient(fake), decode_fn=w1.fake_decode,
                         require_decoder=False, sleep=sleeps.append)
    NETWORK_ATTEMPTS.clear()
    return SimpleNamespace(env=env, fake=fake, state=state, repo=repo, seed=seed, seed_repo=seed_repo, tmp=tmp_path,
                           blobs=blobs, sleeps=sleeps)


def run_all(world) -> dict[str, object]:
    op.command_prepare(world.env)
    op.command_probe(world.env)
    return op.command_run(world.env)


def bundle_of(world) -> dict[str, object]:
    return json.loads((world.env.workspace / op.BUNDLE_FILENAME).read_text(encoding="utf-8"))


def row_reasons(bundle, market_id: str) -> dict[str, str]:
    return {e["checkpoint_id"]: e["reason"] for e in bundle["row_exclusions"] if e["market_id"] == market_id}


def tree_digest(path: Path) -> dict[str, int]:
    return {str(p.relative_to(path)): p.stat().st_size for p in sorted(path.rglob("*")) if p.is_file()} | {
        "#": hash(tuple(p.read_bytes() for p in sorted(path.rglob("*")) if p.is_file()))}


# ── seed admission ────────────────────────────────────────────────────────────


def test_prepare_admits_only_verified_successful_seed(world) -> None:
    before = tree_digest(world.seed)
    result = op.command_prepare(world.env)
    assert result["status"] == "PREPARED"
    workspace = world.env.workspace
    seed_index = json.loads((workspace / op.SEED_INDEX_FILENAME).read_text(encoding="utf-8"))
    predecessor = json.loads((world.seed / d1.INDEX_FILENAME).read_text(encoding="utf-8"))
    assert seed_index and not any("failed" in e for e in seed_index.values())
    assert set(seed_index) == {k for k, e in predecessor.items() if "failed" not in e}
    failed_keys = [k for k, e in predecessor.items() if "failed" in e]
    assert failed_keys and not set(failed_keys) & set(seed_index)  # the 503 entry is never admitted
    for entry in seed_index.values():
        assert op.sha256_hex((workspace / op.SEED_RAW_DIRNAME / entry["sha256"]).read_bytes()) == entry["sha256"]
    report = json.loads((workspace / op.SEED_REPORT_FILENAME).read_text(encoding="utf-8"))
    assert report["failed_entries_admitted"] == 0 and report["failed_entries_not_admitted"] == len(failed_keys)
    assert report["admitted_artifacts"] == len(seed_index)
    assert report["admitted_bytes"] == sum(e["bytes"] for e in seed_index.values())
    assert "rows" in report["never_seeded"] and "label classifications" in report["never_seeded"]
    plan_text = (workspace / op.PLAN_FILENAME).read_text(encoding="utf-8")
    plan = json.loads(plan_text)
    assert plan["seed"]["failed_entries_admitted"] == 0 and plan["seed"]["verified_copies_found"] == 1
    assert plan["predecessor_code_digests"] == json.loads((world.seed / d1.PLAN_FILENAME).read_text(encoding="utf-8"))["code_digests"]
    for text in (plan_text, (workspace / op.SEED_REPORT_FILENAME).read_text(encoding="utf-8")):
        assert str(world.tmp) not in text and "seed-worktree" not in text  # seed path never enters identity
    # Only raw artifacts cross over: no predecessor bundle, rows, manifests or decisions.
    assert sorted(p.name for p in workspace.iterdir()) == sorted(
        [op.PLAN_FILENAME, op.PLAN_HASH_FILENAME, op.SEED_INDEX_FILENAME, op.SEED_REPORT_FILENAME, op.SEED_RAW_DIRNAME,
         op.REGISTRY_COPY_FILENAME, op.STATE_FILENAME])
    assert op.command_prepare(world.env)["status"] == "PREPARED_IDEMPOTENT"
    assert tree_digest(world.seed) == before  # DATA-01 evidence never mutated


@pytest.mark.parametrize("mutation", ["raw_tamper", "not_verified", "wrong_bundle", "code_not_predecessor",
                                      "wrong_terminal", "count_mismatch", "no_roots"])
def test_seed_missing_or_unverifiable_stops(world, monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    seed = world.seed
    if mutation == "raw_tamper":
        target = sorted((seed / "raw").iterdir())[0]
        target.write_bytes(target.read_bytes() + b"x")
    elif mutation == "not_verified":
        (seed / d1.VERIFY_FILENAME).write_text(json.dumps({"status": "VERIFY_FAILED"}), encoding="utf-8")
    elif mutation == "wrong_bundle":
        monkeypatch.setattr(op, "SEED_BUNDLE_ID", "weatherqualbundle:sha256:" + "0" * 64)
    elif mutation == "code_not_predecessor":
        world.blobs["src/data_layer/analytical_research/qualification_data_readiness.py"] = b"# not the predecessor\n"
    elif mutation == "wrong_terminal":
        monkeypatch.setattr(op, "SEED_TERMINAL_REASON", "SOURCE_UNAVAILABLE")
    elif mutation == "count_mismatch":
        verify = json.loads((seed / d1.VERIFY_FILENAME).read_text(encoding="utf-8"))
        verify["rehashed_artifacts"] += 1
        (seed / d1.VERIFY_FILENAME).write_text(json.dumps(verify), encoding="utf-8")
    elif mutation == "no_roots":
        world.state["roots"] = [world.tmp / "nowhere"]
    with pytest.raises(op.OperatorStop) as excinfo:
        op.command_prepare(world.env)
    assert excinfo.value.code == "SEED_EVIDENCE_MISSING"
    assert not world.env.workspace.exists()  # no fallback fresh run, nothing prepared


def test_seed_conflict_between_valid_stores(world) -> None:
    twin = world.tmp / "twin"
    shutil.copytree(world.seed_repo, twin)
    world.state["roots"].append(twin)
    assert op.command_prepare(world.env)["status"] == "PREPARED"  # byte-identical copies agree
    assert json.loads((world.env.workspace / op.PLAN_FILENAME).read_text(encoding="utf-8"))["seed"]["verified_copies_found"] == 2
    shutil.rmtree(world.env.workspace)
    index_path = twin.joinpath(*op.SEED_PARTS) / d1.INDEX_FILENAME
    index = json.loads(index_path.read_text(encoding="utf-8"))
    key = next(k for k, e in sorted(index.items()) if "failed" not in e)
    index[key]["last_modified"] = "Thu, 01 Jan 2026 00:00:00 GMT"  # valid store, different source metadata
    index_path.write_text(json.dumps(index), encoding="utf-8")
    with pytest.raises(op.OperatorStop) as excinfo:
        op.command_prepare(world.env)
    assert excinfo.value.code == "SEED_EVIDENCE_CONFLICT"


def test_prepare_refuses_state_drift_and_conflicting_workspace(world) -> None:
    world.state["dirty"] = " M docs/project_status.md\n"
    with pytest.raises(op.OperatorStop) as excinfo:
        op.command_prepare(world.env)
    assert excinfo.value.code == "STATE_DRIFT"
    world.state["dirty"] = ""
    world.state["branch"] = "main"
    with pytest.raises(op.OperatorStop) as excinfo:
        op.command_prepare(world.env)
    assert excinfo.value.code == "STATE_DRIFT"
    world.state["branch"] = op.PINNED_BRANCH
    world.env.workspace.mkdir(parents=True)
    (world.env.workspace / "stray.txt").write_text("x", encoding="utf-8")
    with pytest.raises(op.OperatorStop) as excinfo:
        op.command_prepare(world.env)
    assert excinfo.value.code == "PREPARE_WORKSPACE_CONFLICT"


# ── retry / throttle policy ───────────────────────────────────────────────────


def scripted(responses, calls=None):
    calls = [] if calls is None else calls

    def fetch(method, url, headers, timeout):
        calls.append(url)
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
    return fetch


URL = "https://api.weather.gov/stations/KNYC"


def test_throttle_backoff_frozen_delays_and_retry_after() -> None:
    cases = [
        ([(503, {}, b"")] * 4, "HTTP_503", [2, 8, 30]),
        ([(429, {}, b"")] * 4, "HTTP_429", [2, 8, 30]),
        ([(429, {"retry-after": "45"}, b""), (200, {}, b"{}")], None, [45]),
        ([(503, {"retry-after": "1"}, b""), (200, {}, b"{}")], None, [2]),  # never shortens the frozen delay
        ([(503, {"retry-after": "60"}, b""), (503, {"retry-after": "60"}, b""), (503, {"retry-after": "60"}, b""),
          (200, {}, b"{}")], None, [60, 60, 60]),
        ([(503, {"retry-after": "61"}, b""), (503, {"retry-after": "abc"}, b""),
          (503, {"retry-after": "Wed, 21 Oct 2026 07:28:00 GMT"}, b""), (200, {}, b"{}")], None, [2, 8, 30]),
        ([(503, {"retry-after": "-1"}, b""), (503, {"retry-after": "2.5"}, b""), (200, {}, b"{}")], None, [2, 8]),
    ]
    for responses, failure, expected_sleeps in cases:
        sleeps: list[float] = []
        ledger = op.Ledger()
        transport = op.BoundedTransport(ledger, scripted(list(responses)), sleeps.append)
        if failure:
            with pytest.raises(op.TransportFailure) as excinfo:
                transport.request("GET", URL)
            assert excinfo.value.code == failure  # exhausted retry = closed failure, never absence
        else:
            assert transport.request("GET", URL).body == b"{}"
        assert sleeps == expected_sleeps
        assert ledger.attempts == len(expected_sleeps) + 1 == ledger.statuses.get("503", 0) + ledger.statuses.get("429", 0) + ledger.statuses.get("200", 0)
        assert ledger.throttle_retries == ledger.retries == len(expected_sleeps) and ledger.backoff_seconds == sum(expected_sleeps)
    ledger = op.Ledger()
    op.BoundedTransport(ledger, scripted([(429, {"retry-after": "45"}, b""), (503, {"retry-after": "3"}, b""), (200, {}, b"{}")]),
                        lambda _s: None).request("GET", URL)
    assert (ledger.retry_after_valid, ledger.retry_after_extended) == (2, 1)
    # Throttle and transport retries are counted separately; a reset still gets one immediate retry.
    sleeps = []
    ledger = op.Ledger()
    transport = op.BoundedTransport(ledger, scripted([(503, {}, b""), d1._TransportError("RESET"), (503, {}, b""), (200, {}, b"{}")]),
                                    sleeps.append)
    assert transport.request("GET", URL).body == b"{}"
    assert sleeps == [2, 8] and (ledger.throttle_retries, ledger.transport_retries, ledger.attempts) == (2, 1, 4)
    assert op.throttle_delay(0, None) == (2, False, False) and op.throttle_delay(2, " 7 ") == (30, True, False)


def test_transport_failures_keep_single_immediate_retry() -> None:
    part_range = (0, 4)
    cases = [
        ([d1._TransportError("TIMEOUT")] * 2, None, "TRANSPORT_TIMEOUT", 2),
        ([d1._TransportError("RESET"), (200, {}, b"{}")], None, None, 2),
        ([(500, {}, b"")] * 2, None, "HTTP_500", 2),
        ([(408, {}, b""), (200, {}, b"{}")], None, None, 2),
        ([(206, {"content-range": "bytes 0-3/9"}, b"ab")] * 2, part_range, "RANGE_TRUNCATED", 2),
        ([(200, {"content-length": "8"}, b"abc")] * 2, None, "BODY_TRUNCATED", 2),
        ([(404, {}, b"")], None, "HTTP_404", 1),
        ([(302, {"location": "https://evil.example.com/"}, b"")], None, "NETWORK_REDIRECT_REFUSED", 1),
    ]
    for responses, byte_range, failure, attempts in cases:
        sleeps: list[float] = []
        ledger = op.Ledger()
        url = PF_URL if byte_range else URL
        transport = op.BoundedTransport(ledger, scripted(list(responses)), sleeps.append)
        if failure:
            with pytest.raises(op.TransportFailure) as excinfo:
                transport.request("GET", url, byte_range=byte_range)
            assert excinfo.value.code == failure
        else:
            transport.request("GET", url, byte_range=byte_range)
        assert ledger.attempts == attempts and sleeps == [] and ledger.throttle_retries == 0
    calls: list[str] = []
    for method, url in (("POST", URL), ("GET", "https://evil.example.com/audit"), ("GET", "http://api.weather.gov/stations/KNYC")):
        with pytest.raises(op.TransportRefused):
            op.BoundedTransport(op.Ledger(), scripted([], calls)).request(method, url)
    assert calls == []


def test_gamma_throttle_policy_and_failure_retained(tmp_path: Path) -> None:
    class Client:
        def __init__(self, statuses):
            self.statuses = list(statuses)

        def get_market(self, market_id):
            status = self.statuses.pop(0)
            if status != 200:
                raise PolymarketHTTPError(status, "https://gamma-api.polymarket.com/markets/" + market_id)
            return SimpleNamespace(data={"id": market_id}, request_info=SimpleNamespace(status_code=200))

    sleeps: list[float] = []
    ledger = op.Ledger()
    store = op.ArtifactStore(tmp_path / "a", None, lambda: Client([503, 503, 503, 503]), sleep=sleeps.append)
    with pytest.raises(op.TransportFailure) as excinfo:
        store.gamma_market("3719310", ledger)
    assert excinfo.value.code == "HTTP_503" and sleeps == [2, 8, 30] and ledger.attempts == 4
    with pytest.raises(op.TransportFailure):
        store.gamma_market("3719310", ledger)  # the closed failure replays; no fifth attempt
    assert ledger.attempts == 4
    sleeps.clear()
    store = op.ArtifactStore(tmp_path / "b", None, lambda: Client([429, 502, 200]), sleep=sleeps.append)
    ledger = op.Ledger()
    assert store.gamma_market("3719310", ledger) == {"id": "3719310"}
    assert sleeps == [2] and (ledger.throttle_retries, ledger.transport_retries, ledger.attempts) == (1, 1, 3)


# ── caps and seed accounting ──────────────────────────────────────────────────


def test_new_network_caps_and_seed_bytes_uncounted(tmp_path: Path) -> None:
    assert (op.MAX_NETWORK_ATTEMPTS, op.MAX_RESPONSE_BYTES, op.MAX_SINGLE_RESPONSE, op.MAX_DISTINCT_PENDULUM_HOURS) == (
        12_288, 6_442_450_944, 268_435_456, 2_000)
    assert op.MAX_SINGLE_RESPONSE == d1.MAX_SINGLE_RESPONSE  # the shared urllib read bound
    calls: list[str] = []
    ledger = op.Ledger(baseline_attempts=op.MAX_NETWORK_ATTEMPTS - 1, attempts=1)
    with pytest.raises(op.BudgetExhausted) as excinfo:
        op.BoundedTransport(ledger, scripted([(200, {}, b"x")], calls)).request("GET", URL)
    assert excinfo.value.code == "ATTEMPT_BUDGET_EXHAUSTED" and calls == []
    ledger = op.Ledger(baseline_bytes=op.MAX_RESPONSE_BYTES - 10)
    with pytest.raises(op.BudgetExhausted) as excinfo:
        op.BoundedTransport(ledger, scripted([(206, {}, b"x" * 100)], calls)).request("GET", PF_URL, byte_range=(0, 100))
    assert excinfo.value.code == "BYTE_BUDGET_EXHAUSTED" and calls == []
    ledger = op.Ledger(bytes=op.MAX_RESPONSE_BYTES - 1)
    with pytest.raises(op.BudgetExhausted):
        op.BoundedTransport(ledger, scripted([(200, {}, b"xx")])).request("GET", URL)
    assert ledger.bytes == op.MAX_RESPONSE_BYTES + 1  # counted truthfully, then fail closed
    ledger = op.Ledger(bytes=op.MAX_RESPONSE_BYTES - 1)
    with pytest.raises(op.BudgetExhausted):  # a throttle response's bytes count too
        op.BoundedTransport(ledger, scripted([(503, {}, b"xx")])).request("GET", URL)
    with pytest.raises(op.TransportRefused) as excinfo:
        op.BoundedTransport(op.Ledger(), scripted([])).request("GET", PF_URL, byte_range=(0, op.MAX_SINGLE_RESPONSE + 1))
    assert excinfo.value.code == "SINGLE_RESPONSE_CAP"
    # Seed hits consume no attempt and no byte.
    raw = tmp_path / "seed_raw"
    raw.mkdir()
    body = b'{"seeded": true}'
    digest = op.sha256_hex(body)
    (raw / digest).write_bytes(body)
    seed_index = {f"GET {URL}": {"sha256": digest, "bytes": len(body), "media_type": "application/geo+json",
                                 "last_modified": None, "status": 200}}
    ledger = op.Ledger()
    store = op.ArtifactStore(tmp_path / "ws", op.BoundedTransport(ledger, scripted([], calls)), seed_index=seed_index, seed_raw=raw)
    assert store.get(URL) == body and ledger.attempts == 0 and ledger.bytes == 0 and calls == []
    assert store.index[f"GET {URL}"]["origin"] == "SEED" and op.seed_usage(store.index)["seed_bytes_reused"] == len(body)
    (raw / digest).write_bytes(body + b"x")  # a corrupted seed artifact is never served
    store = op.ArtifactStore(tmp_path / "ws2", op.BoundedTransport(op.Ledger(), scripted([])), seed_index=seed_index, seed_raw=raw)
    with pytest.raises(op.OperatorStop):
        store.get(URL)


# ── D011 read state ───────────────────────────────────────────────────────────


def test_bba_failed_hour_is_source_invalid_and_stops_walk(world) -> None:
    persistent_503(world.fake, world.fake.product_range(B_HOUR, "best_bid_ask"))
    run_all(world)
    bundle = bundle_of(world)
    assert row_reasons(bundle, "3719314")[B] == "MARKET_HISTORY_SOURCE_INVALID"
    assert sorted((r["market_id"], r["checkpoint_id"]) for r in bundle["rows"]) == [("3719310", A), ("3719314", A)]
    # The failed hour is not scanned and the walk stops: the older hour is never requested.
    assert not any("2026-09-04/04" in url or "2026-09-04T04" in url for _m, url, _r in world.fake.calls)
    failed = bundle["source_facts"]["pendulumflow_failed_reads"]
    assert failed["reads"] == [["market_history", "best_bid_ask", B_HOUR, "CHUNK", "HTTP_503"]]
    assert failed["by_phase_family"]["market_history"] == {"best_bid_ask": 1} and failed["by_stage"] == {"CHUNK": 1}
    assert failed["by_phase_family"]["discovery"] == {"new_market": len(bundle["source_facts"]["discovery_hour_failures"])}
    assert failed["market_history_source_invalid_pairs"] == 1
    assert world.sleeps == [2, 8, 30]  # the frozen throttle schedule, through the no-sleep seam


def test_ltp_failed_hour_not_listed_as_searched(world) -> None:
    persistent_503(world.fake, world.fake.product_range(B_HOUR, "last_trade_price"))
    run_all(world)
    bundle = bundle_of(world)
    row = next(r for r in bundle["rows"] if (r["market_id"], r["checkpoint_id"]) == ("3719314", B))
    history = row["feature_evidence"]["market_history"]
    assert history["best_bid_ask"]["best_bid"] == "0.21"  # the BBA reads themselves succeeded
    assert history["last_trade_price"] is None
    assert history["last_trade_price_state"] == op.LTP_STATE_SEARCH_INCOMPLETE  # never "not observed"
    assert history["last_trade_price_failed_hours"] == [B_HOUR]
    assert history["last_trade_price_searched_hours"] == ["2026-09-04/04"]
    ok = next(r for r in bundle["rows"] if (r["market_id"], r["checkpoint_id"]) == ("3719310", A))["feature_evidence"]["market_history"]
    assert ok["last_trade_price_state"] == "OBSERVED" and ok["last_trade_price_failed_hours"] == []
    assert bundle["execution_evidence"]["3719314"]["FEES"]["v3_last_trade_price_failed_hours"] == [B_HOUR]
    assert bundle["source_facts"]["pendulumflow_failed_reads"]["by_phase_family"]["market_history"] == {"last_trade_price": 1}


def test_label_source_read_failed_vs_resolution_missing(world) -> None:
    persistent_503(world.fake, world.fake.product_range("2026-09-04/14", "market_resolved"))
    run_all(world)
    reasons = {e["market_id"]: e["reason"] for e in bundle_of(world)["market_exclusions"]}
    assert reasons["3719310"] == "LABEL_V3_SOURCE_READ_FAILED"
    assert "LABEL_V3_RESOLUTION_MISSING" not in reasons.values()
    assert bundle_of(world)["dataset"]["counts"]["market_exclusion_reasons"]["LABEL_V3_SOURCE_READ_FAILED"] == 1


def test_label_resolution_missing_only_after_successful_reads(world) -> None:
    world.fake.hours["2026-09-04/14"] = w1.builders.build_v3_hour("2026-09-04/14", {})  # read succeeds, no resolution
    run_all(world)
    reasons = {e["market_id"]: e["reason"] for e in bundle_of(world)["market_exclusions"]}
    assert reasons["3719310"] == "LABEL_V3_RESOLUTION_MISSING"
    assert bundle_of(world)["source_facts"]["pendulumflow_failed_reads"]["reads"] == []
    gamma = qd.GammaFacts("1", "0x" + "0f" * 32, (("No", "2"), ("Yes", "1")), None, None, "No", "", "", None, None, None, None, None)
    for read_failed, code in ((True, "LABEL_V3_SOURCE_READ_FAILED"), (False, "LABEL_V3_RESOLUTION_MISSING")):
        with pytest.raises(qd.RuleExclusion) as excinfo:
            op.label_outcome(gamma, [], read_failed)
        assert excinfo.value.code == code


def test_tick_failed_read_explicit_current_only_supported(world) -> None:
    persistent_503(world.fake, world.fake.product_range(HOUR, "tick_size_change"))
    run_all(world)
    tick = bundle_of(world)["execution_evidence"]["3719310"]["TICK_SIZE_MIN_ORDER"]
    assert tick["tick_size_state"] == "CURRENT_ONLY" and tick["gamma_current_tick_size"]  # independently supported
    assert tick["v3_tick_size_change_failed_hours"] == [HOUR] and HOUR not in tick["v3_tick_size_change_searched_hours"]
    assert bundle_of(world)["source_facts"]["pendulumflow_failed_reads"]["tick_size_change_failed_hours"] == [HOUR]


def test_tick_history_evidenced_when_read_succeeds(world) -> None:
    run_all(world)
    tick = bundle_of(world)["execution_evidence"]["3719310"]["TICK_SIZE_MIN_ORDER"]
    assert tick["tick_size_state"] == "HISTORICALLY_EVIDENCED" and tick["v3_tick_size_change_failed_hours"] == []


# ── completion, probe, verify ─────────────────────────────────────────────────


def test_completion_rederives_whole_corpus_not_inherited(world) -> None:
    report = run_all(world)
    bundle = bundle_of(world)
    assert report["seed"]["seed_artifacts_reused"] > 0 and report["seed"]["new_artifacts_retained"] > 0
    seed_bundle = json.loads((world.seed / d1.BUNDLE_FILENAME).read_text(encoding="utf-8"))
    assert bundle["bundle_id"] != seed_bundle["bundle_id"] and bundle["terminal"] == "QUAL_DATA_READY"
    # A fresh, unseeded derivation from the same world produces the byte-identical bundle: the seed
    # is only a cache, never an inherited decision.
    plan = json.loads((world.env.workspace / op.PLAN_FILENAME).read_text(encoding="utf-8"))
    ledger = op.Ledger()
    fresh = op.ArtifactStore(world.tmp / "fresh", op.BoundedTransport(ledger, world.fake.fetch, lambda _s: None),
                             lambda: w1.FakeGammaClient(world.fake))
    rebuilt, _manifests = op.CompletionPipeline(fresh, plan, w1.fake_decode, ledger).run()
    assert op.canonical(rebuilt) == op.canonical(bundle)
    assert report["network_ledger"]["attempts"] < ledger.attempts  # the seed saved real requests
    assert bundle["source_facts"]["completion"]["predecessor_bundle_id"] == op.SEED_BUNDLE_ID
    text = json.dumps(bundle)
    assert str(world.tmp) not in text and "SOURCE_KIND_CANONICAL_PIT" not in text


def test_memory_bound_eviction_never_changes_bundle_or_network(world, monkeypatch: pytest.MonkeyPatch) -> None:
    report = run_all(world)
    plan = json.loads((world.env.workspace / op.PLAN_FILENAME).read_text(encoding="utf-8"))
    runs = []
    for bound in (op.MEMORY_RANGE_BYTES, 1):
        monkeypatch.setattr(op, "MEMORY_RANGE_BYTES", bound)
        ledger = op.Ledger()
        store = op.ArtifactStore(world.tmp / f"mem-{bound}", op.BoundedTransport(ledger, world.fake.fetch, lambda _s: None),
                                 lambda: w1.FakeGammaClient(world.fake))
        bundle, _manifests = op.CompletionPipeline(store, plan, w1.fake_decode, ledger).run()
        runs.append((op.canonical(bundle), ledger.attempts))
    assert runs[0] == runs[1]  # evicted hours are re-read from the local store, never refetched
    assert op.canonical(bundle_of(world)) == runs[0][0] and report["terminal"] == "QUAL_DATA_READY"


def test_probe_proves_seed_hit_unseeded_fetch_typed_failure(world) -> None:
    op.command_prepare(world.env)
    probe = op.command_probe(world.env)
    assert probe["status"] == "PROBE_PASS"
    checks = probe["checks"]
    assert {k: checks[k] for k in ("seed_cache_hit", "gamma_by_id_identity", "unseeded_fetch_matches_seed", "ndfd_production_decode")} == {
        "seed_cache_hit": "PASS", "gamma_by_id_identity": "PASS", "unseeded_fetch_matches_seed": "PASS", "ndfd_production_decode": "PASS"}
    assert checks["d011_typed_failure"] == {"read": "MANIFEST:HTTP_503", "failed_read_label": "LABEL_V3_SOURCE_READ_FAILED",
                                            "successful_empty_read_label": "LABEL_V3_RESOLUTION_MISSING"}
    assert checks["rule_semantics"] in qd.FINALITY_POLICIES
    assert probe["ledger"]["attempts"] >= 2 and world.fake.gamma_calls  # live Gamma + live manifest
    # An archive object that changed under the seed is source-contract drift.
    world.fake.hours[HOUR][1]["republished"] = True
    shutil.rmtree(world.env.workspace / "probe")
    with pytest.raises(op.OperatorStop) as excinfo:
        op.command_probe(world.env)
    assert excinfo.value.code == "SOURCE_CONTRACT_DRIFT"
    failed = json.loads((world.env.workspace / op.PROBE_FILENAME).read_text(encoding="utf-8"))
    assert failed["failed_step"] == "unseeded_fetch_matches_seed"
    with pytest.raises(op.OperatorStop) as excinfo:
        op.command_run(world.env)
    assert excinfo.value.code == "PROBE_REQUIRED"


def test_end_to_end_completion_counts_and_rerun_refused(world) -> None:
    report = run_all(world)
    bundle = bundle_of(world)
    assert report["terminal"] == bundle["terminal"] == "QUAL_DATA_READY"
    counts = bundle["dataset"]["counts"]
    assert counts["discovered_candidates"] == 5 and counts["included_markets"] == 2
    assert counts["checkpoint_usable_rows"] == {A: 2, B: 1}
    assert bundle["dataset"]["b0_contract_compatibility"] == qd.B0_EXTERNAL_ONLY
    assert bundle["dataset"]["wp_id"] == d1.WP_ID and bundle["source_facts"]["completion"]["wp_id"] == op.WP_ID
    assert report["new_network_attempts_total"] == report["network_ledger"]["attempts"] + report["probe_ledger"]["attempts"]
    assert report["budget_exhausted"] is None and report["resumed"] is False
    # The seeded 503 key was re-fetched fresh (never admitted, never treated as absence).
    index = json.loads((world.env.workspace / d1.INDEX_FILENAME).read_text(encoding="utf-8"))
    refetched = d1.ArtifactStore.key("GET", d1.pf_url(v3.manifest_object_path("2026-08-19/11")))
    assert index[refetched].get("origin") != "SEED"
    with pytest.raises(op.OperatorStop) as excinfo:
        op.command_run(world.env)
    assert excinfo.value.code == "RUN_ALREADY_FINALIZED"
    assert op.main(["run-completion"], world.env) == 3


def test_verify_final_zero_network_rehash_seed_and_new(world) -> None:
    run_all(world)
    calls_before = len(world.fake.calls)
    verified = op.command_verify(world.env)
    assert verified["status"] == "VERIFIED" and verified["network_calls"] == 0 and verified["failed_seed_entries_admitted"] == 0
    assert len(world.fake.calls) == calls_before and NETWORK_ATTEMPTS == []
    bundle = bundle_of(world)
    assert (verified["bundle_id"], verified["logical_dataset_id"]) == (bundle["bundle_id"], bundle["logical_dataset_id"])
    assert verified["seed_artifacts_rehashed"] > 0 and verified["rehashed_artifacts"] > verified["seed"]["seed_artifacts_reused"]
    workspace = world.env.workspace

    def expect(code: str) -> None:
        with pytest.raises(op.OperatorStop) as excinfo:
            op.command_verify(world.env)
        assert excinfo.value.code == code

    for target in (sorted((workspace / op.SEED_RAW_DIRNAME).iterdir())[0], sorted((workspace / "raw").iterdir())[0]):
        original = target.read_bytes()
        target.write_bytes(original + b"x")
        expect("VERIFY_FAILED")
        target.write_bytes(original)
    for name, mutate, code in (
        (op.SEED_INDEX_FILENAME, lambda d: d.update({"GET https://api.weather.gov/stations/KXYZ": {"failed": "HTTP_503"}}), "PLAN_INVALID"),
        (op.REPORT_FILENAME, lambda d: d["seed"].update({"seed_bytes_reused": 1}), "VERIFY_FAILED"),
        (op.REPORT_FILENAME, lambda d: d.update({"new_network_attempts_total": 1}), "VERIFY_FAILED"),
        (op.LEDGER_FILENAME, lambda d: d.update({"bytes": d["bytes"] + 1}), "VERIFY_FAILED"),
        (op.BUNDLE_FILENAME, lambda d: d["dataset"]["counts"].update({"included_markets": 99}), "VERIFY_FAILED"),
    ):
        path = workspace / name
        original = path.read_text(encoding="utf-8")
        document = json.loads(original)
        mutate(document)
        path.write_text(json.dumps(document), encoding="utf-8")
        expect(code)
        path.write_text(original, encoding="utf-8")
    assert op.command_verify(world.env)["status"] == "VERIFIED"
    code = world.repo / "src/data_layer/analytical_research/qualification_data_readiness.py"
    code.write_text(code.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
    expect("CODE_DRIFT")


def test_budget_exhaustion_terminates_insufficient_and_replays(world) -> None:
    op.command_prepare(world.env)
    probe = op.command_probe(world.env)
    op.write_json_atomic(world.env.workspace / op.LEDGER_FILENAME, op.Ledger(
        baseline_attempts=op.MAX_NETWORK_ATTEMPTS - 20,
        baseline_bytes=probe["ledger"]["bytes"]).to_mapping())
    report = op.command_run(world.env)
    assert report["terminal"] == qd.TERMINAL_INSUFFICIENT and report["terminal_reason"] == "FROZEN_BUDGET_EXHAUSTED"
    assert report["network_ledger"]["exhausted"] == "ATTEMPT_BUDGET_EXHAUSTED"
    assert report["network_ledger"]["baseline_attempts"] + report["network_ledger"]["attempts"] == op.MAX_NETWORK_ATTEMPTS


def test_frozen_semantics_and_boundaries_unchanged() -> None:
    body = op.frozen_plan_body()
    semantics = body
    assert semantics["target_dates"] == list(qd.target_dates()) and len(semantics["target_dates"]) == 40
    assert semantics["target_dates"][0] == "2026-08-18" and semantics["target_dates"][-1] == "2026-09-26"
    assert semantics["checkpoints"] == qd.checkpoint_definitions()
    assert set(semantics["checkpoints"]) >= {A, B}
    assert semantics["checkpoints"]["market_history_lookback_hours"] == 24 and semantics["checkpoints"]["ndfd_vintage_lookback_hours"] == 48
    assert semantics["label_window_minutes_around_gamma_closed_time"] == 30
    assert "whole-object" in semantics["ndfd_product"]
    assert body["finality_policies"] == ["FIRST_PUBLISHED_FINAL", "LATEST_BEFORE_2359_ET", "LAST_BEFORE_1400_ET"]
    assert body["allowlist"] == sorted(d1.ALLOWED_HOSTS) == sorted(
        {"archive.pendulumflow.com", "noaa-ndfd-pds.s3.amazonaws.com", "gamma-api.polymarket.com", "api.weather.gov"})
    assert body["methods"] == ["GET", "HEAD"]
    assert body["retry_policy"]["throttle_delays_seconds"] == [2, 8, 30] and body["retry_policy"]["jitter"] is False
    assert body["budgets"]["seed_bytes_consume_caps"] is False
    assert v3.SOURCE_CLASS == "THIRD_PARTY_NATIVE_FRAME_ARCHIVE" and qd.derive_b0_compatibility() == qd.B0_EXTERNAL_ONLY
    assert op.CODE_FILES[:4] == (*d1.CODE_FILES[:3], "tools/qualification/run_s10_qual_data_01.py")


def test_no_qualification_candidate_gate_or_trading_path() -> None:
    path = ROOT / "tools" / "qualification" / "run_s10_qual_data_02.py"
    forbidden = ("qualification", "qualification_gate", "experiment_os", "experiment_registry", "paper", "execution",
                 "live", "gateway", "hermes", "wallet", "order")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    allowed = {"tools.qualification", "tools.qualification.run_s10_qual_data_01"}  # the unchanged DATA-01 operator
    for name in imported - allowed:
        assert not any(part in forbidden for part in name.split(".")), name
    text = path.read_text(encoding="utf-8")
    for call in ("build_qualification_candidate", "evaluate_qualification_gate", "QualificationCandidate(", "place_order",
                 "submit_order", "cancel_order", "private_key", "api_key", "Authorization", "random", "jitter("):
        assert call not in text, call


def test_operator_tests_hermetic_no_real_network(world) -> None:
    report = run_all(world)
    assert report["terminal"] == "QUAL_DATA_READY" and NETWORK_ATTEMPTS == []
    assert {url.split("/")[2] for _m, url, _r in world.fake.calls} <= op.ALLOWED_HOSTS
    assert all(method == "GET" for method, _u, _r in world.fake.calls)
    assert not any("gamma-api" in url for _m, url, _r in world.fake.calls)


def test_cli_prints_closed_codes_only(world, capsys: pytest.CaptureFixture[str]) -> None:
    assert op.main(["bogus"], world.env) == 2
    assert capsys.readouterr().out.strip() == "STOP USAGE_ERROR"
    assert op.main(["verify-final"], world.env) == 3
    output = capsys.readouterr().out
    assert output.strip() == "STOP PLAN_MISSING" and str(world.tmp) not in output
    assert op.main(["prepare"], world.env) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "PREPARED" and set(summary) <= {"status", "plan_sha256"}
