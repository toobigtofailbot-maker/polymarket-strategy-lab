"""Bounded public wallet evidence ingest lifecycle (S10-WALLET-01).

Deterministic collection over the three bounded public Data API v2 wallet feeds
(/v2/trades, /v2/activity, /v2/activity/combos). Network is OFF by default; a dry
run performs zero network work. Each successfully acquired page (including a
zero-event page) is committed atomically to the wallet evidence ledger before the
next page is requested, so first-seen evidence survives a later-page failure. A
pre-run ``ingest_run_key`` correlates page/observation/receipt records; the
terminal receipt has its own separate identity. There is no automatic resume, no
retry, no sleep, and no scheduler.

Posture: local, offline, stdlib-only, deterministic. Public GET-only. No
credentials, no order/signing/paper/live/qualification/Hermes/WP170 authority.
The sole network-capable component is the existing bounded public client.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from ..point_in_time_market_research.research_provenance import (
    PitTimestamps,
    build_pit_timestamps,
    build_raw_evidence_reference,
)
from ..polymarket.polling_policy import (
    WALLET_MAX_PAGES_PER_FEED,
    WALLET_MAX_SOURCE_ROWS_PER_FEED_RUN,
    WALLET_MAX_SOURCE_ROWS_TOTAL_RUN,
)
from . import contracts as C
from . import ledger as L
from .contracts import (
    WalletContractError,
    build_feed_acquisition_receipt,
    build_wallet_evidence_event,
    build_wallet_event_observation,
    build_wallet_feed_page_evidence,
    build_wallet_ingest_run_receipt,
    canonicalize_evm_address,
    derive_ingest_run_key,
    map_combo_activity_type,
    map_standard_activity_type,
)

PUBLIC_INGEST_LABEL = "PUBLIC_WALLET_EVIDENCE_INGEST_LIFECYCLE"
PUBLIC_INGEST_POSTURE = "LOCAL_OFFLINE_BOUNDED_PUBLIC_GET_ONLY_NO_SCHEDULER"

INGEST_RUN_SCHEMA_ID = "wallet-public-ingest-run"
INGEST_RUN_SCHEMA_VERSION = "1.0.0"
SOURCE_SYSTEM = "POLYMARKET_DATA_API_V2"
RETRIEVAL_METHOD = "GET/urllib/data-api-v2"
PARSER_VERSION = "wallet-ingest/1.0.0"
MEDIA_TYPE = "application/json"

# Default disposition for /v2/trades combo state: E2 (UNKNOWN) unless primary
# source truth explicitly proves ordinary-market-only (Section 4.E / 10.6).
TRADES_COMBO_STATE_DEFAULT = "UNKNOWN"

INGEST_MODES = (
    "DRY_RUN",
    "NETWORK",
    "LOCAL_RESPONSE_FIXTURE",
    "LOCAL_CHAIN_EVIDENCE",
)

REQUIRED_FEEDS = ("TRADES", "STANDARD_ACTIVITY", "COMBO_ACTIVITY")


def _err(code: str) -> WalletContractError:
    return WalletContractError(code)


# ---------------------------------------------------------------------------
# Request / result.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class WalletIngestRequest:
    canonical_wallet: str
    trades_start: str | None = None
    trades_end: str | None = None
    activity_start: str | None = None
    activity_end: str | None = None
    combo_condition: str | None = None
    collector_policy_version: str = "S10-WALLET-01/1.0.0"
    page_size: int = 100
    run_started_at: str = ""
    trades_combo_state: str = TRADES_COMBO_STATE_DEFAULT

    def frozen_user(self) -> str:
        return canonicalize_evm_address(self.canonical_wallet)

    def pre_run_preimage(self) -> dict:
        # ONLY pre-run scope fields. Page refs, response hashes, discovered
        # cursors, counts, completion state, and run-ended time are excluded.
        return {
            "schema_id": INGEST_RUN_SCHEMA_ID,
            "schema_version": INGEST_RUN_SCHEMA_VERSION,
            "canonical_wallet": canonicalize_evm_address(self.canonical_wallet),
            "feeds": list(REQUIRED_FEEDS),
            "trades_scope": {
                "start": self.trades_start,
                "end": self.trades_end,
                "taker_only": "false",
            },
            "activity_scope": {
                "start": self.activity_start,
                "end": self.activity_end,
                "exclude_deposits_withdrawals": "false",
                "sort_direction": "ASC",
            },
            "combo_scope": {
                "condition": self.combo_condition,
                "time_filter_capability": "NOT_SUPPORTED",
            },
            "page_size": self.page_size,
            "collector_policy_version": self.collector_policy_version,
            "run_started_at": self.run_started_at,
        }


@dataclass(frozen=True)
class FeedRunOutcome:
    feed_key: str
    completion_state: str
    failure_codes: tuple[str, ...]
    dq_flags: tuple[str, ...]
    page_evidence_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    event_ids: tuple[str, ...]
    raw_evidence_ids: tuple[str, ...]
    cursor_chain: tuple[tuple[str | None, str | None], ...]
    page_count: int
    source_row_count: int
    terminal_has_more: bool
    receipt: object


@dataclass(frozen=True)
class WalletIngestResult:
    collection_completion_state: str
    ingest_run_key: str
    wallet_ingest_run_receipt_id: str | None
    feed_outcomes: tuple[FeedRunOutcome, ...]
    error_codes: tuple[str, ...]
    transport_call_count: int
    appended_record_count: int
    dry_run: bool


def derive_run_key(request: WalletIngestRequest) -> str:
    return derive_ingest_run_key(request.pre_run_preimage())


# ---------------------------------------------------------------------------
# Row normalization.
# ---------------------------------------------------------------------------
def _row_get(row: Mapping, *names):
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return None


def _row_event_time(row: Mapping) -> str | None:
    value = _row_get(row, "timestamp", "event_time", "time")
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, Decimal)) and not isinstance(value, bool):
        from datetime import datetime, timezone

        seconds = int(value)
        return (
            datetime.fromtimestamp(seconds, tz=timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ")
        )
    return None


def _row_wallet(row: Mapping, fallback: str) -> str:
    value = _row_get(row, "proxy_wallet", "user", "wallet", "account")
    return str(value) if value is not None else fallback


def normalize_trade_row(row: Mapping, *, wallet: str, combo_state: str):
    condition = _row_get(row, "condition_id")
    token = _row_get(row, "token_id", "asset_id")
    event = build_wallet_evidence_event(
        identity_strength="SOURCE_CONTENT_DERIVED",
        canonical_event_type="TRADE_FILL",
        canonical_wallet=_row_wallet(row, wallet),
        combo_state=combo_state,
        source_system_family=SOURCE_SYSTEM,
        condition_context="DATA_API_RESPONSE_CONDITION_ID" if condition is not None else None,
        condition_value=(
            C.canonicalize_identifier("DATA_API_RESPONSE_CONDITION_ID", condition)
            if condition is not None
            else None
        ),
        token_context="CLOB_TOKEN_ID" if token is not None else None,
        token_value=(
            C.canonicalize_identifier("CLOB_TOKEN_ID", token) if token is not None else None
        ),
        side=_normalize_side(_row_get(row, "side")),
        price=_row_get(row, "price"),
        size=_row_get(row, "size", "shares"),
        event_time=_row_event_time(row),
        transaction_hash=_row_get(row, "transaction_hash", "tx_hash"),
        cost_basis_state="NOT_APPLICABLE",
    )
    return event, "TRADE", ()


def normalize_activity_row(row: Mapping, *, wallet: str, combo_state: str = "UNKNOWN"):
    source_type = _row_get(row, "type", "activity_type")
    if not isinstance(source_type, str):
        raise _err("RESPONSE")
    canonical = map_standard_activity_type(source_type)
    condition = _row_get(row, "condition_id")
    token = _row_get(row, "token_id", "asset_id")
    dq: list[str] = ["OK"]
    combo_state = None
    identity_strength = "SOURCE_CONTENT_DERIVED"
    identity_ambiguous = False
    if canonical == "TRADE_FILL":
        is_combo = row.get("is_combo")
        if isinstance(is_combo, bool):
            combo_state = "TRUE" if is_combo else "FALSE"
        else:
            # Missing/invalid required combo discriminator: do not invent a value.
            dq = ["SCHEMA_DRIFT"]
            identity_strength = "WEAK_PARTIAL"
            identity_ambiguous = True
    elif canonical == "UNKNOWN_PUBLIC_ACTIVITY":
        dq = ["SCHEMA_DRIFT", "PARTIALLY_OBSERVED"]
        identity_strength = "WEAK_PARTIAL"
        identity_ambiguous = True

    event = build_wallet_evidence_event(
        identity_strength=identity_strength,
        canonical_event_type=canonical,
        canonical_wallet=_row_wallet(row, wallet),
        combo_state=combo_state,
        source_system_family=SOURCE_SYSTEM,
        condition_context="DATA_API_RESPONSE_CONDITION_ID" if condition is not None else None,
        condition_value=(
            C.canonicalize_identifier("DATA_API_RESPONSE_CONDITION_ID", condition)
            if condition is not None
            else None
        ),
        token_context="CLOB_TOKEN_ID" if token is not None else None,
        token_value=(
            C.canonicalize_identifier("CLOB_TOKEN_ID", token) if token is not None else None
        ),
        side=_normalize_side(_row_get(row, "side")),
        price=_row_get(row, "price"),
        size=_row_get(row, "size", "shares"),
        event_time=_row_event_time(row),
        transaction_hash=_row_get(row, "transaction_hash", "tx_hash"),
        cost_basis_state=_cost_basis_for(canonical),
        identity_ambiguous=identity_ambiguous,
    )
    return event, source_type, tuple(dq) if dq != ["OK"] else ()


def normalize_combo_row(row: Mapping, *, wallet: str, combo_state: str = "UNKNOWN"):
    source_type = _row_get(row, "type", "activity_type")
    if not isinstance(source_type, str):
        raise _err("RESPONSE")
    canonical = map_combo_activity_type(source_type)
    native = _row_get(row, "id", "native_event_id")
    condition = _row_get(row, "condition_id", "combo_condition_id")
    dq = ["OK"] if canonical != "UNKNOWN_PUBLIC_ACTIVITY" else ["SCHEMA_DRIFT", "PARTIALLY_OBSERVED"]
    if native is not None:
        event = build_wallet_evidence_event(
            identity_strength="API_NATIVE_STRONG",
            canonical_event_type=canonical,
            canonical_wallet=_row_wallet(row, wallet),
            source_system_family=SOURCE_SYSTEM,
            native_event_id=C.canonicalize_identifier("SOURCE_NATIVE_EVENT_ID", native),
            condition_context="COMBO_CONDITION_ID" if condition is not None else None,
            condition_value=(
                C.canonicalize_identifier("COMBO_CONDITION_ID", condition)
                if condition is not None
                else None
            ),
            event_time=_row_event_time(row),
            transaction_hash=_row_get(row, "transaction_hash", "tx_hash"),
            cost_basis_state=_cost_basis_for(canonical),
        )
    else:
        event = build_wallet_evidence_event(
            identity_strength="WEAK_PARTIAL",
            canonical_event_type=canonical,
            canonical_wallet=_row_wallet(row, wallet),
            source_system_family=SOURCE_SYSTEM,
            condition_context="COMBO_CONDITION_ID" if condition is not None else None,
            condition_value=(
                C.canonicalize_identifier("COMBO_CONDITION_ID", condition)
                if condition is not None
                else None
            ),
            event_time=_row_event_time(row),
            transaction_hash=_row_get(row, "transaction_hash", "tx_hash"),
            cost_basis_state=_cost_basis_for(canonical),
            identity_ambiguous=True,
        )
    return event, source_type, tuple(dq) if dq != ["OK"] else ()


def _normalize_side(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if text in ("BUY", "SELL"):
        return text
    if text in ("B", "BID"):
        return "BUY"
    if text in ("S", "ASK"):
        return "SELL"
    return None


def _cost_basis_for(canonical_event_type: str) -> str:
    # Externally transferred/imported inventory and non-trade economics never get
    # a fabricated acquisition basis (10.5 / R-W13).
    if canonical_event_type in ("TRANSFER_IN", "DEPOSIT", "MIGRATION"):
        return "UNKNOWN"
    if canonical_event_type in (
        "REWARD",
        "MAKER_REBATE",
        "TAKER_REBATE",
        "REFERRAL_REWARD",
        "YIELD",
        "TIP",
        "FEE",
    ):
        return "NOT_APPLICABLE"
    return "NOT_APPLICABLE"


_NORMALIZERS = {
    "TRADES": normalize_trade_row,
    "STANDARD_ACTIVITY": normalize_activity_row,
    "COMBO_ACTIVITY": normalize_combo_row,
}


# ---------------------------------------------------------------------------
# Feed collection.
# ---------------------------------------------------------------------------
@dataclass
class _Clock:
    times: list[str]
    _i: int = 0

    def __call__(self) -> str:
        value = self.times[min(self._i, len(self.times) - 1)]
        self._i += 1
        return value


def _feed_plan(request: WalletIngestRequest):
    plans = []
    plans.append(
        {
            "feed_key": "TRADES",
            "endpoint": "/v2/trades",
            "time_filter_capability": "SUPPORTED",
            "requested_start": request.trades_start,
            "requested_end": request.trades_end,
            "acquisition_scope": "REQUESTED_TIME_WINDOW",
            "condition_scope": (),
            "frozen_filters": {
                "user": canonicalize_evm_address(request.canonical_wallet),
                "taker_only": "false",
            },
        }
    )
    plans.append(
        {
            "feed_key": "STANDARD_ACTIVITY",
            "endpoint": "/v2/activity",
            "time_filter_capability": "SUPPORTED",
            "requested_start": request.activity_start,
            "requested_end": request.activity_end,
            "acquisition_scope": "REQUESTED_TIME_WINDOW",
            "condition_scope": (),
            "frozen_filters": {
                "user": canonicalize_evm_address(request.canonical_wallet),
                "exclude_deposits_withdrawals": "false",
                "sort_direction": "ASC",
            },
        }
    )
    combo_scope = "CONDITION_SCOPED_ALL_AVAILABLE_AS_OF_RUN" if request.combo_condition else "ALL_AVAILABLE_AS_OF_RUN"
    plans.append(
        {
            "feed_key": "COMBO_ACTIVITY",
            "endpoint": "/v2/activity/combos",
            "time_filter_capability": "NOT_SUPPORTED",
            "requested_start": None,
            "requested_end": None,
            "acquisition_scope": combo_scope,
            "condition_scope": (request.combo_condition,) if request.combo_condition else (),
            "frozen_filters": {"user": canonicalize_evm_address(request.canonical_wallet)},
        }
    )
    return plans


def _run_feed(
    *,
    plan: dict,
    request: WalletIngestRequest,
    ingest_run_key: str,
    ledger_path,
    fetch_page: Callable,
    clock: Callable[[], str],
    counters: dict,
) -> FeedRunOutcome:
    feed = plan["feed_key"]
    endpoint = plan["endpoint"]
    normalizer = _NORMALIZERS[feed]
    wallet = canonicalize_evm_address(request.canonical_wallet)
    request_identity = dict(plan["frozen_filters"])

    page_ids: list[str] = []
    observation_ids: list[str] = []
    event_ids: list[str] = []
    raw_ids: list[str] = []
    cursor_chain: list[tuple[str | None, str | None]] = []
    failure_codes: list[str] = []
    feed_dq: set[str] = set()
    seen_cursors: set[str] = set()
    source_rows = 0
    completion = "COMPLETE"
    incoming_cursor: str | None = None

    for page_index in range(WALLET_MAX_PAGES_PER_FEED):
        try:
            page = fetch_page(feed, incoming_cursor)
        except _StopFeed as stop:
            failure_codes.append(stop.code)
            completion = stop.completion
            break

        counters["transport"] += page.get("_transport", 0)
        first_seen = clock()
        ingestion = clock()
        rows = list(page["rows"])
        source_rows += len(rows)

        raw = build_raw_evidence_reference(
            source_system=SOURCE_SYSTEM,
            endpoint=endpoint,
            retrieval_method=RETRIEVAL_METHOD,
            content_sha256=page["content_sha256"],
            byte_length=page["body_byte_length"],
            media_type=MEDIA_TYPE,
            pit=build_pit_timestamps(
                local_first_seen_time=first_seen, ingestion_time=ingestion
            ),
            dq_flags=["OK"],
            replay_fidelity="FAITHFUL",
            request_parameters=page["request_parameters"],
            cursor_anchor=incoming_cursor,
        )
        pit = build_pit_timestamps(
            local_first_seen_time=first_seen, ingestion_time=ingestion
        )
        # First pass: normalize rows into events (no page id needed yet).
        normalized: list[tuple[object, str, tuple]] = []
        page_dq: set[str] = set()
        for row in rows:
            event, source_activity_type, row_dq = normalizer(
                row, wallet=wallet, combo_state=request.trades_combo_state
            )
            normalized.append((event, source_activity_type, row_dq))
            for flag in row_dq:
                page_dq.add(flag)

        unique_event_ids = {ev.wallet_event_id for ev, _, _ in normalized}
        page_dq_flags = sorted(page_dq) if page_dq else ["OK"]
        has_more = bool(page["has_more"])
        outgoing_cursor = page["next_cursor"]

        page_evidence = build_wallet_feed_page_evidence(
            raw_evidence_reference_id=raw.raw_evidence_reference_id,
            ingest_run_key=ingest_run_key,
            feed_key=feed,
            canonical_request_identity=request_identity,
            requested_page_size=request.page_size,
            has_more=has_more,
            local_first_seen_time=first_seen,
            ingestion_time=ingestion,
            api_source_parser_version=PARSER_VERSION,
            dq_flags=page_dq_flags,
            replay_fidelity="FAITHFUL",
            source_row_count=len(rows),
            normalized_event_count=len(unique_event_ids),
            observation_count=len(normalized),
            incoming_cursor=incoming_cursor,
            outgoing_cursor=outgoing_cursor,
        )
        # Second pass: build observations now that the page-evidence id exists.
        records = [raw, page_evidence]
        seen_event_ids: set[str] = set()
        page_observation_ids: list[str] = []
        for event, source_activity_type, row_dq in normalized:
            if event.wallet_event_id not in seen_event_ids:
                records.append(event)
                seen_event_ids.add(event.wallet_event_id)
                event_ids.append(event.wallet_event_id)
            observation = build_wallet_event_observation(
                wallet_event_id=event.wallet_event_id,
                wallet_feed_page_evidence_id=page_evidence.wallet_feed_page_evidence_id,
                ingest_run_key=ingest_run_key,
                source_system=SOURCE_SYSTEM,
                endpoint=endpoint,
                source_activity_type=source_activity_type,
                pit=pit,
                dq_flags=list(row_dq) if row_dq else ["OK"],
                replay_fidelity="FAITHFUL",
                raw_evidence_reference_id=raw.raw_evidence_reference_id,
            )
            records.append(observation)
            page_observation_ids.append(observation.wallet_event_observation_id)

        append_result = L.append_wallet_evidence_records(ledger_path, records)
        if not append_result.is_valid:
            failure_codes.extend(append_result.error_codes)
            completion = "PARTIAL_SOURCE_FAILURE"
            break
        counters["appended"] += len(append_result.inserted_record_ids)

        page_ids.append(page_evidence.wallet_feed_page_evidence_id)
        raw_ids.append(raw.raw_evidence_reference_id)
        observation_ids.extend(page_observation_ids)
        cursor_chain.append((incoming_cursor, outgoing_cursor))
        for flag in page_dq_flags:
            if flag != "OK":
                feed_dq.add(flag)

        # Completeness / cursor decisions.
        if not has_more:
            completion = "COMPLETE"
            break
        if outgoing_cursor is None:
            failure_codes.append("CURSOR_GAP")
            feed_dq.update({"SEQUENCE_GAP"})
            completion = "PARTIAL_CURSOR_GAP"
            break
        if outgoing_cursor in seen_cursors or outgoing_cursor == incoming_cursor:
            failure_codes.append("CURSOR_GAP")
            feed_dq.update({"SEQUENCE_GAP"})
            completion = "PARTIAL_CURSOR_GAP"
            break
        if source_rows > WALLET_MAX_SOURCE_ROWS_PER_FEED_RUN:
            feed_dq.update({"PARTIALLY_OBSERVED", "SEQUENCE_GAP"})
            completion = "PARTIAL_LIMIT"
            break
        seen_cursors.add(outgoing_cursor)
        incoming_cursor = outgoing_cursor
    else:
        # Loop exhausted WALLET_MAX_PAGES_PER_FEED with has_more still true.
        feed_dq.update({"PARTIALLY_OBSERVED", "SEQUENCE_GAP"})
        completion = "PARTIAL_LIMIT"

    terminal_has_more = cursor_chain[-1][1] is not None if cursor_chain else False
    receipt = build_feed_acquisition_receipt(
        feed_key=feed,
        endpoint=endpoint,
        source_contract_version=INGEST_RUN_SCHEMA_VERSION,
        canonical_wallet=wallet,
        time_filter_capability=plan["time_filter_capability"],
        acquisition_scope=plan["acquisition_scope"],
        requested_page_size=request.page_size,
        feed_completion_state=completion,
        feed_replay_fidelity="FAITHFUL",
        requested_start=plan["requested_start"],
        requested_end=plan["requested_end"],
        condition_scope=plan["condition_scope"],
        frozen_filters=request_identity,
        page_count=len(page_ids),
        source_row_count=source_rows,
        page_evidence_ids=page_ids,
        cursor_chain=cursor_chain,
        terminal_has_more=terminal_has_more if completion != "COMPLETE" else False,
        feed_failure_codes=tuple(dict.fromkeys(failure_codes)),
        feed_dq_flags=sorted(feed_dq) if feed_dq else ["OK"],
    )
    return FeedRunOutcome(
        feed_key=feed,
        completion_state=completion,
        failure_codes=tuple(dict.fromkeys(failure_codes)),
        dq_flags=tuple(sorted(feed_dq)) if feed_dq else ("OK",),
        page_evidence_ids=tuple(page_ids),
        observation_ids=tuple(observation_ids),
        event_ids=tuple(dict.fromkeys(event_ids)),
        raw_evidence_ids=tuple(raw_ids),
        cursor_chain=tuple(cursor_chain),
        page_count=len(page_ids),
        source_row_count=source_rows,
        terminal_has_more=terminal_has_more,
        receipt=receipt,
    )


class _StopFeed(Exception):
    def __init__(self, code: str, completion: str) -> None:
        self.code = code
        self.completion = completion


# ---------------------------------------------------------------------------
# Top-level ingest.
# ---------------------------------------------------------------------------
def ingest_wallet_evidence(
    request: WalletIngestRequest,
    *,
    ledger_path,
    mode: str = "DRY_RUN",
    page_fetcher: Callable | None = None,
    clock_times: Sequence[str] | None = None,
) -> WalletIngestResult:
    """Run one bounded wallet evidence collection.

    ``mode='DRY_RUN'`` performs zero network and zero ledger writes.
    ``mode='LOCAL_RESPONSE_FIXTURE'`` and ``mode='NETWORK'`` both drive the same
    deterministic cursor walk through ``page_fetcher``; NETWORK expects a fetcher
    that performs exactly one bounded GET per page via the public client.
    """

    if mode not in INGEST_MODES:
        raise _err("FIELD_VALUE")
    ingest_run_key = derive_run_key(request)

    if mode == "DRY_RUN":
        return WalletIngestResult(
            collection_completion_state="DRY_RUN",
            ingest_run_key=ingest_run_key,
            wallet_ingest_run_receipt_id=None,
            feed_outcomes=(),
            error_codes=(),
            transport_call_count=0,
            appended_record_count=0,
            dry_run=True,
        )

    if page_fetcher is None:
        raise _err("FIELD_VALUE")

    # Collision / reuse guard (15.2.1): a NEW acquisition under an already-used
    # key must reject before any transport. Query the ledger for run-tagged rows.
    load = L.load_and_verify_wallet_evidence_ledger(ledger_path)
    if not load.is_valid:
        return _rejected_before_acquisition(ingest_run_key, load.error_codes)
    existing = L.query_records_by_ingest_run_key(load.snapshot, ingest_run_key)
    if existing:
        return WalletIngestResult(
            collection_completion_state="REJECTED_BEFORE_ACQUISITION",
            ingest_run_key=ingest_run_key,
            wallet_ingest_run_receipt_id=None,
            feed_outcomes=(),
            error_codes=("LEDGER_IDENTITY_CONFLICT",),
            transport_call_count=0,
            appended_record_count=0,
            dry_run=False,
        )

    clock = _Clock(list(clock_times) if clock_times else [request.run_started_at or "2026-01-01T00:00:00Z"])
    counters = {"transport": 0, "appended": 0}
    outcomes: list[FeedRunOutcome] = []
    for plan in _feed_plan(request):
        outcome = _run_feed(
            plan=plan,
            request=request,
            ingest_run_key=ingest_run_key,
            ledger_path=ledger_path,
            fetch_page=page_fetcher,
            clock=clock,
            counters=counters,
        )
        outcomes.append(outcome)

    collection_state = _derive_collection_state(outcomes)
    run_ended = clock()
    all_pages = tuple(pid for o in outcomes for pid in o.page_evidence_ids)
    all_raws = tuple(dict.fromkeys(rid for o in outcomes for rid in o.raw_evidence_ids))
    all_obs = tuple(oid for o in outcomes for oid in o.observation_ids)
    all_events = tuple(dict.fromkeys(eid for o in outcomes for eid in o.event_ids))
    aggregate_dq = sorted({f for o in outcomes for f in o.dq_flags if f != "OK"}) or ["OK"]

    receipt = build_wallet_ingest_run_receipt(
        ingest_run_key=ingest_run_key,
        canonical_wallet=canonicalize_evm_address(request.canonical_wallet),
        run_started_at=request.run_started_at or "2026-01-01T00:00:00Z",
        run_ended_at=run_ended,
        feed_receipts=tuple(o.receipt for o in outcomes),
        collection_completion_state=collection_state,
        collection_replay_fidelity="FAITHFUL",
        all_page_evidence_ids=all_pages,
        referenced_raw_evidence_ids=all_raws,
        aggregate_dq_flags=aggregate_dq,
        aggregate_page_count=sum(o.page_count for o in outcomes),
        aggregate_source_row_count=sum(o.source_row_count for o in outcomes),
        aggregate_event_count=len(all_events),
        aggregate_observation_count=len(all_obs),
        ordered_event_ids=all_events,
        ordered_observation_ids=all_obs,
    )
    append_receipt = L.append_wallet_evidence_records(ledger_path, [receipt])
    if append_receipt.is_valid:
        counters["appended"] += len(append_receipt.inserted_record_ids)
        receipt_id = receipt.wallet_ingest_run_receipt_id
    else:
        receipt_id = None

    return WalletIngestResult(
        collection_completion_state=collection_state,
        ingest_run_key=ingest_run_key,
        wallet_ingest_run_receipt_id=receipt_id,
        feed_outcomes=tuple(outcomes),
        error_codes=(),
        transport_call_count=counters["transport"],
        appended_record_count=counters["appended"],
        dry_run=False,
    )


def _derive_collection_state(outcomes: Sequence[FeedRunOutcome]) -> str:
    states = {o.feed_key: o.completion_state for o in outcomes}
    if all(states.get(feed) == "COMPLETE" for feed in REQUIRED_FEEDS) and len(outcomes) == len(REQUIRED_FEEDS):
        return "COMPLETE"
    # Otherwise surface the first non-complete reason deterministically.
    priority = (
        "PARTIAL_SOURCE_FAILURE",
        "PARTIAL_SCHEMA_DRIFT",
        "PARTIAL_CURSOR_GAP",
        "PARTIAL_LIMIT",
    )
    present = {o.completion_state for o in outcomes}
    for state in priority:
        if state in present:
            return state
    return "PARTIAL_SOURCE_FAILURE"


def _rejected_before_acquisition(ingest_run_key: str, error_codes) -> WalletIngestResult:
    return WalletIngestResult(
        collection_completion_state="REJECTED_BEFORE_ACQUISITION",
        ingest_run_key=ingest_run_key,
        wallet_ingest_run_receipt_id=None,
        feed_outcomes=(),
        error_codes=tuple(error_codes),
        transport_call_count=0,
        appended_record_count=0,
        dry_run=False,
    )


# ---------------------------------------------------------------------------
# Offline interrupted-run recovery (15.6 / R-D02).
# ---------------------------------------------------------------------------
def recover_interrupted_wallet_ingest(
    request: WalletIngestRequest,
    *,
    ledger_path,
    run_ended_at: str,
) -> WalletIngestResult:
    """Append exactly one PARTIAL_INTERRUPTED terminal receipt for a run that has
    committed page evidence but no terminal receipt. Performs ZERO network calls
    and rewrites/deletes nothing. Rejects if no page evidence exists or a terminal
    receipt already exists for the key."""

    ingest_run_key = derive_run_key(request)
    load = L.load_and_verify_wallet_evidence_ledger(ledger_path)
    if not load.is_valid:
        return _rejected_before_acquisition(ingest_run_key, load.error_codes)
    tagged = L.query_records_by_ingest_run_key(load.snapshot, ingest_run_key)
    page_ids = [
        r.record_id for r in tagged if r.record_kind == C.RECORD_KIND_WALLET_FEED_PAGE_EVIDENCE
    ]
    obs_ids = [
        r.record_id for r in tagged if r.record_kind == C.RECORD_KIND_WALLET_EVENT_OBSERVATION
    ]
    receipts = [
        r for r in tagged if r.record_kind == C.RECORD_KIND_WALLET_INGEST_RUN_RECEIPT
    ]
    if receipts:
        return WalletIngestResult(
            collection_completion_state="REJECTED_BEFORE_ACQUISITION",
            ingest_run_key=ingest_run_key,
            wallet_ingest_run_receipt_id=None,
            feed_outcomes=(),
            error_codes=("LEDGER_IDENTITY_CONFLICT",),
            transport_call_count=0,
            appended_record_count=0,
            dry_run=False,
        )
    if not page_ids:
        return _rejected_before_acquisition(ingest_run_key, ("REFERENCE_INVALID",))

    # Reconstruct minimal feed receipts from committed page evidence.
    raw_ids = sorted(
        {
            r.payload["raw_evidence_reference_id"]
            for r in tagged
            if r.record_kind == C.RECORD_KIND_WALLET_FEED_PAGE_EVIDENCE
        }
    )
    feed_receipts = []
    for plan in _feed_plan(request):
        feed_pages = [
            r.record_id
            for r in tagged
            if r.record_kind == C.RECORD_KIND_WALLET_FEED_PAGE_EVIDENCE
            and r.payload.get("feed_key") == plan["feed_key"]
        ]
        feed_receipts.append(
            build_feed_acquisition_receipt(
                feed_key=plan["feed_key"],
                endpoint=plan["endpoint"],
                source_contract_version=INGEST_RUN_SCHEMA_VERSION,
                canonical_wallet=canonicalize_evm_address(request.canonical_wallet),
                time_filter_capability=plan["time_filter_capability"],
                acquisition_scope=plan["acquisition_scope"],
                requested_page_size=request.page_size,
                feed_completion_state="PARTIAL_SOURCE_FAILURE" if feed_pages else "NOT_STARTED",
                feed_replay_fidelity="FAITHFUL",
                requested_start=plan["requested_start"],
                requested_end=plan["requested_end"],
                condition_scope=plan["condition_scope"],
                frozen_filters=plan["frozen_filters"],
                page_count=len(feed_pages),
                page_evidence_ids=feed_pages,
                feed_dq_flags=["PARTIALLY_OBSERVED"] if feed_pages else ["OK"],
            )
        )

    receipt = build_wallet_ingest_run_receipt(
        ingest_run_key=ingest_run_key,
        canonical_wallet=canonicalize_evm_address(request.canonical_wallet),
        run_started_at=request.run_started_at or "2026-01-01T00:00:00Z",
        run_ended_at=run_ended_at,
        feed_receipts=tuple(feed_receipts),
        collection_completion_state="PARTIAL_INTERRUPTED",
        collection_replay_fidelity="FAITHFUL",
        all_page_evidence_ids=tuple(page_ids),
        referenced_raw_evidence_ids=tuple(raw_ids),
        aggregate_dq_flags=["PARTIALLY_OBSERVED"],
        aggregate_page_count=len(page_ids),
        aggregate_observation_count=len(obs_ids),
        ordered_observation_ids=tuple(obs_ids),
    )
    append_receipt = L.append_wallet_evidence_records(ledger_path, [receipt])
    if not append_receipt.is_valid:
        return _rejected_before_acquisition(ingest_run_key, append_receipt.error_codes)
    return WalletIngestResult(
        collection_completion_state="PARTIAL_INTERRUPTED",
        ingest_run_key=ingest_run_key,
        wallet_ingest_run_receipt_id=receipt.wallet_ingest_run_receipt_id,
        feed_outcomes=(),
        error_codes=(),
        transport_call_count=0,
        appended_record_count=len(append_receipt.inserted_record_ids),
        dry_run=False,
    )


# ---------------------------------------------------------------------------
# Page fetchers.
# ---------------------------------------------------------------------------
def make_local_fixture_fetcher(pages_by_feed: Mapping[str, Sequence[Mapping]]) -> Callable:
    """Build a deterministic offline page fetcher from in-memory response pages.

    ``pages_by_feed[feed]`` is an ordered list of page dicts, each with keys
    rows, next_cursor, has_more, content_sha256, body_byte_length,
    request_parameters. Performs ZERO network work.
    """

    state = {feed: 0 for feed in pages_by_feed}

    def fetch(feed: str, cursor):
        pages = pages_by_feed.get(feed, [])
        index = state.get(feed, 0)
        if index >= len(pages):
            raise _StopFeed("SOURCE_UNAVAILABLE", "PARTIAL_SOURCE_FAILURE")
        page = dict(pages[index])
        state[feed] = index + 1
        page.setdefault("_transport", 0)
        return page

    return fetch


def make_network_fetcher(client, *, request: WalletIngestRequest, opener, guard=None) -> Callable:
    """Build a fetcher that performs exactly one bounded public GET per page via
    the existing public client. Applies the RateLimitGuard immediately before each
    request; a guard denial performs no request."""

    from ..polymarket.polling_policy import (
        WALLET_ACTIVITY_COMBOS_ENDPOINT_KEY,
        WALLET_ACTIVITY_ENDPOINT_KEY,
        WALLET_TRADES_ENDPOINT_KEY,
    )
    from ..polymarket.public_client import WalletDataApiError

    endpoint_keys = {
        "TRADES": WALLET_TRADES_ENDPOINT_KEY,
        "STANDARD_ACTIVITY": WALLET_ACTIVITY_ENDPOINT_KEY,
        "COMBO_ACTIVITY": WALLET_ACTIVITY_COMBOS_ENDPOINT_KEY,
    }

    def fetch(feed: str, cursor):
        if guard is not None:
            decision = guard.record_allowed(endpoint_keys[feed])
            if not decision.allowed:
                raise _StopFeed("RATE_LIMIT_GUARD_DENIED", "PARTIAL_SOURCE_FAILURE")
        try:
            if feed == "TRADES":
                result = client.get_wallet_trades_page(
                    user=request.frozen_user(),
                    start=request.trades_start,
                    end=request.trades_end,
                    cursor=cursor,
                    page_size=request.page_size,
                    opener=opener,
                )
            elif feed == "STANDARD_ACTIVITY":
                result = client.get_wallet_activity_page(
                    user=request.frozen_user(),
                    start=request.activity_start,
                    end=request.activity_end,
                    cursor=cursor,
                    page_size=request.page_size,
                    opener=opener,
                )
            else:
                result = client.get_wallet_activity_combos_page(
                    user=request.frozen_user(),
                    combo_condition=request.combo_condition,
                    cursor=cursor,
                    page_size=request.page_size,
                    opener=opener,
                )
        except WalletDataApiError as exc:
            completion = "PARTIAL_LIMIT" if exc.code == "LIMIT_EXCEEDED" else "PARTIAL_SOURCE_FAILURE"
            raise _StopFeed(exc.code, completion) from None
        return {
            "rows": result.rows,
            "next_cursor": result.next_cursor,
            "has_more": result.has_more,
            "content_sha256": result.content_sha256,
            "body_byte_length": result.body_byte_length,
            "request_parameters": result.request_parameters,
            "_transport": 1,
        }

    return fetch
