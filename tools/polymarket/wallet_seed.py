"""Synthetic scientific seed and separately reviewed non-study readiness.

Local records and terminal presence never authenticate external human approval.
Scientific production capture remains closed.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
from functools import wraps
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_layer.hermes_advisory_output_validator import _scan_forbidden_terms, _scan_raw_metadata_keys
from src.data_layer.point_in_time_market_research.research_provenance import (
    ObservabilityEvidence, build_pit_timestamps, build_raw_evidence_reference,
    build_research_provenance_manifest, canonicalize_utc_timestamp,
)
from src.data_layer.wallet_intelligence import contracts as C
from src.data_layer.wallet_intelligence import ledger as L
from src.data_layer.wallet_intelligence import profile as P
from src.data_layer.wallet_intelligence import reconciliation as R
from src.data_layer.wallet_intelligence import copyability as B
from src.execution_feasibility.public_market import public_get, decode_public_json

METHOD_DIGEST = "walletmethod:sha256:e08fe248dff75bd1e67503426801a6b6940d42ad4acb2bded89dd1650cba1656"
EXCHANGE = "0xe111180000d2663c0091e4f400237545b87b996b"
CTF = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"
COLLATERAL = "0x2791bca1f2de4661ed88a30c99a7a9449aa84174"
EXCHANGE_HASH = "3e2ba43e59d19191f0d208e39b1ec16f920bdda30ebfa062330ea9fe8d8363f5"
CTF_HASH = "984de1496ba73cea948f777d72201b9418041dce65551bff0b4d62101d2acd62"
TOPIC = "0xd543adfd945773f1a62f74f0ee55a5e3b9b1a28262980ba90b1a89f2ea84d8ee"
RPC_HOST = "polygon-bor-rpc.publicnode.com"
SELECTORS = frozenset({"0x856296f7", "0xd42dc0c2", "0x39dd7530", "0xdd34de67", "0x0504c814", "0x03cee3df", "0x3b521d78"})
RPC_METHODS = frozenset({"eth_chainId", "eth_getCode", "eth_getBlockByNumber", "eth_getBlockByHash", "eth_getTransactionReceipt", "eth_getLogs", "eth_call"})
LIMITS = {"calls": 128, "bytes": 8388608, "elapsed_seconds": 120, "timeout_seconds": 5}
LOG_RANGE_BLOCKS = 128
COVERAGE_EPISTEMICS = "RPC_CONTRACT_CONDITIONAL_NOT_PROVIDER_ATTESTED"
STATES = ("EXCLUDED", "UNKNOWN", "UNMATCHED", "MATCHED", "PENDING", "CENSORED")
STUDY_FIELDS = (
    "method_digest", "code_sha", "condition_id", "target_token_id", "complement_token_id",
    "rule_snapshot_digest", "event_id", "leakage_group_id", "source_chain_id",
    "cohort_reference_id", "profile_source_reference_id", "cluster_membership_digest",
    "freeze_time", "decision_time", "target_event_end", "label_deadline",
    "nonwallet_version", "wallet_added_version", "source_route_evidence_refs",
    "observation_group_missingness_policies", "approved_source_call_byte_elapsed_limits",
    "human_approval_record",
)


class SeedError(ValueError):
    """Closed diagnostics only; never retain an untrusted exception message."""


def _require(ok, code="FIELD_INVALID"):
    if not ok:
        raise SeedError(code)


def _closed(value, keys):
    _require(type(value) is dict and set(value) == set(keys))
    return value


def _stamp(value):
    return datetime.fromisoformat(canonicalize_utc_timestamp(value).replace("Z", "+00:00"))


def _hex(value, size=None):
    _require(type(value) is str and re.fullmatch(r"0x[0-9a-fA-F]*", value) is not None)
    _require(len(value) % 2 == 0 and (size is None or len(value) == 2 + size * 2))
    return bytes.fromhex(value[2:])


def _quantity(value):
    _require(type(value) is str and re.fullmatch(r"0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)", value) is not None)
    return int(value, 16)


def _decimal(value):
    _require(type(value) is str and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value) is not None)
    return Decimal(value)


def _fixed(value):
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _identity(prefix, value):
    return prefix + sha256(C.wallet_canonical_json_bytes(value)).hexdigest()


def _bounded(value, depth=0):
    _require(depth <= 24)
    if type(value) is dict:
        _require(len(value) <= 128 and all(type(k) is str and len(k) <= 128 for k in value))
        for child in value.values():
            _bounded(child, depth + 1)
    elif type(value) in (list, tuple):
        _require(len(value) <= 1024)
        for child in value:
            _bounded(child, depth + 1)
    else:
        _require(value is None or type(value) in (str, int, bool))
        if type(value) is str:
            _require(len(value) <= 16384)


@dataclass(frozen=True)
class SeedResult:
    status: str
    payload: dict = field(default_factory=dict)
    errors: tuple[str, ...] = ()
    origin: str = "SYNTHETIC"
    advisory_only: bool = True
    no_execution_authority: bool = True
    no_strategy_authority: bool = True
    no_qualification_authority: bool = True
    study_activated: bool = False


RESULT_FIELDS = frozenset(SeedResult.__dataclass_fields__)
FORBIDDEN_OUTPUT = ("buy/sell recommendation", "trade-ready", "execution-ready", "position sizing", "expected return", "profit target", "stop loss", "take profit", "copy signal", "strategy signal", "paper trading candidate")


def _scan_seed_output(value):
    if type(value) is dict:
        for key, child in value.items():
            _scan_seed_output(key); _scan_seed_output(child)
    elif type(value) in (list, tuple):
        for child in value:
            _scan_seed_output(child)
    elif type(value) is str:
        normalized = re.sub(r"[\s_-]+", " ", value.lower())
        _require(not any(re.sub(r"[\s_-]+", " ", term) in normalized for term in FORBIDDEN_OUTPUT), "OUTPUT_UNSAFE")


def result_to_mapping(result):
    _require(type(result) is SeedResult)
    data = asdict(result)
    _bounded(data)
    unsafe = []
    _scan_forbidden_terms(data, "", unsafe)
    _require(not unsafe, "OUTPUT_UNSAFE")
    _scan_seed_output(data)
    _require(result.origin == "SYNTHETIC" and result.study_activated is False and all(getattr(result, key) is True for key in ("advisory_only", "no_execution_authority", "no_strategy_authority", "no_qualification_authority")), "OUTPUT_UNSAFE")
    _scan_raw_metadata_keys(data, "", unsafe)
    _require(not unsafe, "OUTPUT_UNSAFE")
    return data


def _public(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        try:
            result = fn(*args, **kwargs)
            result_to_mapping(result)
            return result
        except SeedError as error:
            if fn.__name__ in ("materialize_forecast_pair", "attach_final_label"):
                status = "EXCLUDED" if str(error) in {"SEAL_INVALID", "METHOD_INVALID", "INSTRUMENT_INVALID", "IDENTITY_INVALID", "FREEZE_INVALID"} else "UNKNOWN"
                return SeedResult(status, {"enrolled_count": "NOT_ESTABLISHED", "synthetic_counts": {state: int(state == status) for state in STATES}, "numeric_summary": None}, errors=(str(error),))
            return SeedResult("INVALID", errors=(str(error),))
        except Exception:
            if fn.__name__ in ("materialize_forecast_pair", "attach_final_label"):
                return SeedResult("UNKNOWN", {"enrolled_count": "NOT_ESTABLISHED", "synthetic_counts": {state: int(state == "UNKNOWN") for state in STATES}, "numeric_summary": None}, errors=("FIELD_INVALID",))
            return SeedResult("INVALID", errors=("FIELD_INVALID",))
    return call


@dataclass(frozen=True)
class Request:
    name: str
    method: str
    params: tuple = ()
    url: str | None = None


@dataclass(frozen=True)
class SourceFrame:
    """Synthetic retained original bytes. No constructor can assert REAL origin."""
    request: Request
    body: bytes
    observed_at: str
    code_sha: str
    started_at: str | None = None
    origin: str = field(default="SYNTHETIC", init=False)

    @property
    def reference(self):
        return _identity("walletseedsource:sha256:", {
            "request": asdict(self.request), "body_sha256": sha256(self.body).hexdigest(),
            "bytes": len(self.body), "observed_at": self.observed_at,
            "code_sha": self.code_sha, "origin": self.origin,
            "started_at": self.started_at,
        })


@dataclass(frozen=True)
class SyntheticTransport:
    """Explicit fixture transport; accepted by exact type, never a production hook."""
    frames: tuple[SourceFrame, ...]
    evidence: dict | None = None


@dataclass(frozen=True)
class SyntheticDecisionClock:
    """Fixture clock only. A scalar timestamp is not a prospective commit proof."""
    at: str


def _rpc_document(body):
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, "SOURCE_INVALID")
            result[key] = value
        return result
    def invalid_number(value):
        raise SeedError("SOURCE_INVALID")
    document = json.loads(body, object_pairs_hook=pairs, parse_constant=invalid_number, parse_float=invalid_number)
    def bounds(value, depth=0, counter=None):
        counter = [0] if counter is None else counter
        counter[0] += 1
        _require(depth <= 24 and counter[0] <= 32768, "SOURCE_INVALID")
        if type(value) in (dict, list):
            _require(len(value) <= 1024, "SOURCE_INVALID")
            for child in value.values() if type(value) is dict else value:
                bounds(child, depth + 1, counter)
        elif type(value) is str:
            _require(len(value) <= 16384 or re.fullmatch(r"0x[0-9a-fA-F]+", value) is not None, "SOURCE_INVALID")
        else:
            _require(value is None or type(value) in (int, bool), "SOURCE_INVALID")
    bounds(document)
    return document


def _source_body(body, venue=False):
    _require(type(body) is bytes and len(body) <= 2097152, "SOURCE_INVALID")
    document = decode_public_json(body) if venue else _rpc_document(body)
    unsafe = []
    _scan_forbidden_terms(document, "", unsafe)
    _scan_raw_metadata_keys(document, "", unsafe)
    _require(not unsafe, "SOURCE_INVALID")
    if not venue:
        _closed(document, ("jsonrpc", "id", "result"))
        _require(document["jsonrpc"] == "2.0" and type(document["id"]) is int and document["id"] == 1)
        _require(document["result"] is not None, "SOURCE_INVALID")
        return document["result"]
    return document


def _frame(frame, method=None, cutoff=None):
    _require(type(frame) is SourceFrame and type(frame.request) is Request and frame.origin == "SYNTHETIC", "SOURCE_INVALID")
    _require(type(frame.body) is bytes and len(frame.body) <= 2097152)
    _require(re.fullmatch(r"[0-9a-f]{40}", frame.code_sha) is not None)
    if method is not None:
        _require(frame.request.method == method, "SOURCE_INVALID")
    if cutoff is not None:
        _require(_stamp(frame.observed_at) <= _stamp(cutoff), "LATE_SOURCE")
    _require(_stamp(frame.started_at or frame.observed_at) <= _stamp(frame.observed_at), "LATE_SOURCE")
    return _source_body(frame.body, frame.request.url is not None)


def _route(evidence, cutoff=None):
    _closed(evidence, ("chain", "finalized", "exchange_code", "ctf_code"))
    _require(_frame(evidence["chain"], "eth_chainId", cutoff) == "0x89", "CHAIN_INVALID")
    _require(evidence["chain"].request.params == (), "CHAIN_INVALID")
    _require(len({frame.code_sha for frame in evidence.values()}) == 1, "VERSION_INVALID")
    block = _frame(evidence["finalized"], "eth_getBlockByNumber", cutoff)
    _require(evidence["finalized"].request.params == ("finalized", False))
    _hex(block["hash"], 32)
    number = _quantity(block["number"])
    block_time = datetime.fromtimestamp(_quantity(block["timestamp"]), timezone.utc)
    _require(block_time <= _stamp(evidence["finalized"].observed_at), "FINALITY_INVALID")
    for key, address, expected in (("exchange_code", EXCHANGE, EXCHANGE_HASH), ("ctf_code", CTF, CTF_HASH)):
        frame = evidence[key]
        _require(frame.request.params == (address, block["number"]), "VERSION_INVALID")
        code = _hex(_frame(frame, "eth_getCode", cutoff))
        _require(sha256(code).hexdigest() == expected, "VERSION_INVALID")
    return {"chain_id": 137, "finalized_block": number, "finalized_hash": block["hash"], "code_sha": evidence["chain"].code_sha, "finalized_time": block_time.isoformat(),
            "route_id": _identity("walletseedroute:sha256:", [evidence[k].reference for k in sorted(evidence)])}


@_public
def validate_source_route(*, route_evidence):
    return SeedResult("VERIFIED_SYNTHETIC_ROUTE", _route(route_evidence))


def _instrument(instrument):
    _closed(instrument, ("condition_id", "target_token_id", "complement_token_id", "gamma_market_id", "rule_snapshot_digest", "event_id", "leakage_group_id", "wallets", "mapping"))
    _hex(instrument["condition_id"], 32)
    _require(instrument["condition_id"] == instrument["condition_id"].lower())
    for key in ("target_token_id", "complement_token_id", "gamma_market_id"):
        _require(re.fullmatch(r"[1-9][0-9]{0,77}", instrument[key]) is not None)
    _require(instrument["target_token_id"] != instrument["complement_token_id"])
    _require(type(instrument["wallets"]) is tuple and 1 <= len(instrument["wallets"]) <= 16)
    _require(len(set(instrument["wallets"])) == len(instrument["wallets"]))
    for wallet in instrument["wallets"]:
        _require(C.canonicalize_evm_address(wallet) == wallet)
    for key in ("rule_snapshot_digest", "event_id", "leakage_group_id"):
        _require(type(instrument[key]) is str and re.fullmatch(r"[A-Za-z0-9:_-]{1,128}", instrument[key]) is not None)
    return instrument


def _mapping_proof(instrument, route, cutoff):
    """Pure CTF responses, bound to exact calldata and one canonical route block."""
    frames = instrument["mapping"]
    _closed(frames, ("slots", "collateral", "collection_1", "collection_2", "position_1", "position_2"))
    condition = instrument["condition_id"][2:]
    word = lambda value: format(value, "064x")
    block = hex(route["finalized_block"])
    def read(key, contract, data):
        frame = frames[key]
        _require(frame.code_sha == route["code_sha"], "VERSION_INVALID")
        _require(frame.request.params == ({"to": contract, "data": data}, block), "INSTRUMENT_INVALID")
        return _hex(_frame(frame, "eth_call", cutoff), 32)
    _require(int.from_bytes(read("slots", CTF, "0xd42dc0c2" + condition), "big") == 2, "INSTRUMENT_INVALID")
    _require(read("collateral", EXCHANGE, "0x03cee3df").hex() == "0" * 24 + COLLATERAL[2:], "INSTRUMENT_INVALID")
    positions = []
    for index in (1, 2):
        collection = read(f"collection_{index}", CTF, "0x856296f7" + "0" * 64 + condition + word(index))
        position = read(f"position_{index}", CTF, "0x39dd7530" + "0" * 24 + COLLATERAL[2:] + collection.hex())
        positions.append(str(int.from_bytes(position, "big")))
    _require(positions == [instrument["target_token_id"], instrument["complement_token_id"]], "INSTRUMENT_INVALID")


def _fill(raw_log, receipt, block, finality, instrument, selected_log=None):
    _instrument(instrument)
    _closed(finality, ("route", "canonical", "cutoff"))
    cutoff = finality["cutoff"]
    route = _route(finality["route"], cutoff)
    _mapping_proof(instrument, route, cutoff)
    selection = None
    if type(raw_log) is tuple:
        _require(len(raw_log) == 2 and type(raw_log[1]) is int and raw_log[1] >= 0, "SOURCE_INVALID")
        raw_log, selection = raw_log
    logs = _frame(raw_log, "eth_getLogs", cutoff)
    _require(type(logs) is list and 0 < len(logs) <= 256, "SOURCE_INVALID")
    if selection is not None:
        _require(selection < len(logs), "SOURCE_INVALID")
        selected_log = logs[selection]
    if selected_log is None:
        _require(len(logs) == 1, "SOURCE_INVALID")
        selected_log = logs[0]
    _require(sum(x == selected_log for x in logs) == 1, "IDENTITY_INVALID")
    log = selected_log
    record = _frame(receipt, "eth_getTransactionReceipt", cutoff)
    header = _frame(block, cutoff=cutoff)
    canonical = _frame(finality["canonical"], "eth_getBlockByNumber", cutoff)
    _require(len({raw_log.code_sha, receipt.code_sha, block.code_sha, finality["canonical"].code_sha, finality["route"]["chain"].code_sha}) == 1, "VERSION_INVALID")
    _require(log.get("removed") is False and record["status"] == "0x1", "FINALITY_INVALID")
    _require(C.canonicalize_evm_address(log["address"]) == EXCHANGE, "VERSION_INVALID")
    _require(len(log["topics"]) == 4 and log["topics"][0].lower() == TOPIC, "ABI_INVALID")
    topics = [_hex(topic, 32) for topic in log["topics"]]
    _require(topics[2][:12] == topics[3][:12] == bytes(12), "ABI_INVALID")
    wallet = "0x" + topics[2][12:].hex()
    _require(wallet in instrument["wallets"], "IDENTITY_INVALID")
    _hex(log["transactionHash"], 32)
    _hex(log["blockHash"], 32)
    _require(receipt.request.params == (log["transactionHash"],), "IDENTITY_INVALID")
    for key in ("transactionHash", "blockHash", "blockNumber", "transactionIndex"):
        _require(log[key] == record[key], "IDENTITY_INVALID")
    _require(sum(item == log for item in record["logs"]) == 1, "IDENTITY_INVALID")
    _require(header["hash"] == canonical["hash"] == log["blockHash"] and header["number"] == canonical["number"] == log["blockNumber"], "FINALITY_INVALID")
    _require(finality["canonical"].request.params in ((header["number"], False), (header["number"], True)), "FINALITY_INVALID")
    _require(_quantity(header["number"]) <= route["finalized_block"], "FINALITY_INVALID")
    data = _hex(log["data"], 224)
    words = [int.from_bytes(data[i:i + 32], "big") for i in range(0, 224, 32)]
    side, token, making, taking = words[:4]
    _require(side in (0, 1) and making > 0 and taking > 0, "ABI_INVALID")
    _require(str(token) in (instrument["target_token_id"], instrument["complement_token_id"]), "INSTRUMENT_INVALID")
    with localcontext() as context:
        context.prec = 80
        cash, shares = (making, taking) if side == 0 else (taking, making)
        price = Decimal(cash) / Decimal(shares)
        _require(0 < price < 1, "INSTRUMENT_INVALID")
        event_time = datetime.fromtimestamp(_quantity(header["timestamp"]), timezone.utc).isoformat().replace("+00:00", "Z")
        event = C.build_wallet_evidence_event(
            identity_strength="CHAIN_NATIVE_STRONG", canonical_event_type="TRADE_FILL",
            canonical_wallet=wallet, combo_state="FALSE", source_system_family="POLYGON_RPC",
            chain_id=137, condition_context="DATA_API_RESPONSE_CONDITION_ID", condition_value=instrument["condition_id"],
            token_context="CLOB_TOKEN_ID", token_value=str(token), side="BUY" if side == 0 else "SELL",
            price=_fixed(price), size=_fixed(Decimal(shares) / 1000000), notional=_fixed(Decimal(cash) / 1000000),
            event_time=event_time, transaction_hash=log["transactionHash"], log_index=_quantity(log["logIndex"]),
            block_hash=log["blockHash"], source_contract_address=EXCHANGE,
        )
    chain = R.build_chain_event_evidence(chain_id=137, block_number=_quantity(log["blockNumber"]),
        block_hash=log["blockHash"], transaction_hash=log["transactionHash"], transaction_index=_quantity(log["transactionIndex"]),
        log_index=_quantity(log["logIndex"]), removed=False, finality_state="FINALIZED",
        confirmation_or_finality_time=finality["route"]["finalized"].observed_at)
    return event, chain


@_public
def decode_fill(*, raw_log, receipt, block, finality, instrument):
    event, chain = _fill(raw_log, receipt, block, finality, instrument)
    return SeedResult("DECODED_SYNTHETIC_FILL", {"event": asdict(event), "chain": asdict(chain)})


def _budget(budget):
    _closed(budget, LIMITS)
    for key, maximum in LIMITS.items():
        _require(type(budget[key]) is int and 0 < budget[key] <= maximum, "LIMIT_INVALID")


def _seal(seal):
    _closed(seal, ("payload", "digest", "approval"))
    payload = _closed(seal["payload"], STUDY_FIELDS)
    _bounded(payload)
    unsafe = []
    _scan_forbidden_terms(payload, "", unsafe); _scan_raw_metadata_keys(payload, "", unsafe)
    _require(not unsafe, "SEAL_INVALID")
    _require(re.fullmatch(r"[0-9a-f]{40}", payload["code_sha"]) is not None, "VERSION_INVALID")
    _require(payload["method_digest"] == METHOD_DIGEST, "METHOD_INVALID")
    _require(payload["source_chain_id"] == 137)
    _require(seal["digest"] == _identity("walletstudy:sha256:", payload), "SEAL_INVALID")
    _closed(payload["human_approval_record"], ("request_id", "requested_scope", "planned_approver"))
    _require(payload["human_approval_record"]["requested_scope"] == "ONE_UNIT_STUDY")
    for value in payload["human_approval_record"].values():
        _require(type(value) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value) is not None, "APPROVAL_INVALID")
    freeze, decision, end, deadline = (_stamp(payload[key]) for key in ("freeze_time", "decision_time", "target_event_end", "label_deadline"))
    _require(decision - freeze >= timedelta(days=1) and timedelta(hours=1) <= end - decision <= timedelta(days=7) and deadline - end == timedelta(days=30), "FREEZE_INVALID")
    _require(payload["nonwallet_version"] == "NONWALLET_MIDPOINT_V1" and payload["wallet_added_version"] == "WALLET_BLEND_010_V1")
    _budget(payload["approved_source_call_byte_elapsed_limits"])
    _closed(payload["source_route_evidence_refs"], ("route_id", "readiness_cohort_id", "readiness_head", "discovery_refs", "gamma_market_id", "requests"))
    policies = _closed(payload["observation_group_missingness_policies"], ("group", "membership", "no_replacement"))
    _require(policies["no_replacement"] is True and policies["group"] == payload["leakage_group_id"], "SEAL_INVALID")
    _require(type(policies["membership"]) is list and len(policies["membership"]) >= 1 and len(set(policies["membership"])) == len(policies["membership"]), "GROUP_INVALID")
    _require(payload["cluster_membership_digest"] == _identity("walletseedcluster:sha256:", policies["membership"]), "GROUP_INVALID")
    _hex(payload["condition_id"], 32)
    _require(payload["target_token_id"] != payload["complement_token_id"])
    return payload


def _approval(seal, phase):
    payload = seal["payload"]
    approval = _closed(seal["approval"], ("kind", "approved_digest", "method_digest", "code_sha", "phase", "hosts", "budget"))
    _require(approval["kind"] == "SYNTHETIC_DETACHED", "APPROVAL_INVALID")
    _require(approval["approved_digest"] == seal["digest"] and approval["method_digest"] == METHOD_DIGEST and approval["code_sha"] == payload["code_sha"] and approval["phase"] == phase, "APPROVAL_INVALID")
    _require(approval["hosts"] == (RPC_HOST, "clob.polymarket.com", "gamma-api.polymarket.com") and approval["budget"] == payload["approved_source_call_byte_elapsed_limits"], "APPROVAL_INVALID")


@_public
def build_study_seal(*, method, readiness, cohort, profile, instrument, clocks, budget, human_approval):
    _require(_identity("walletmethod:sha256:", {"method": method}) == METHOD_DIGEST, "METHOD_INVALID")
    _instrument(instrument)
    _budget(budget)
    _closed(clocks, ("freeze_time", "decision_time", "target_event_end", "label_deadline"))
    _closed(readiness, ("route", "ledger_path", "ledger_head", "cohort", "contexts", "identity_observability", "discovery_references"))
    _route(readiness["route"], clocks["freeze_time"])
    loaded = L.load_and_verify_wallet_evidence_ledger(readiness["ledger_path"])
    _require(loaded.is_valid and loaded.snapshot.head_hash == readiness["ledger_head"], "LEDGER_INVALID")
    rebuilt = P.build_wallet_profile_snapshot(wallet_ledger_path=readiness["ledger_path"], cohort_snapshot=readiness["cohort"],
        target_wallet=profile.representative_wallet, as_of=profile.as_of, market_contexts=readiness["contexts"], identity_observability=readiness["identity_observability"])
    _require(rebuilt == profile and _stamp(profile.as_of) <= _stamp(clocks["freeze_time"]), "PROFILE_INVALID")
    _require(type(cohort) is P.WalletDiscoveryCohortSnapshot and len(cohort.members) == 1)
    _require(cohort.members == readiness["cohort"].members and cohort.discovery_cutoff == readiness["cohort"].discovery_cutoff)
    _require(_stamp(cohort.discovery_cutoff) <= _stamp(clocks["freeze_time"]))
    t0 = _stamp(clocks["decision_time"])
    _require(_stamp(cohort.evaluation_start) == t0 - timedelta(hours=1) and _stamp(cohort.evaluation_end) == t0 + timedelta(microseconds=1))
    _require(tuple(profile.subject_wallets) == instrument["wallets"] and profile.sample_strength.status != "UNKNOWN_INDEPENDENCE", "GROUP_INVALID")
    references = tuple(readiness["discovery_references"])
    _require(references and all(ref in loaded.snapshot.record_ids() for ref in references), "SOURCE_INVALID")
    payload = {"method_digest": METHOD_DIGEST, "code_sha": readiness["route"]["chain"].code_sha,
        **{key: instrument[key] for key in ("condition_id", "target_token_id", "complement_token_id", "rule_snapshot_digest", "event_id", "leakage_group_id")},
        "source_chain_id": 137, "cohort_reference_id": cohort.wallet_discovery_cohort_snapshot_id,
        "profile_source_reference_id": profile.wallet_profile_snapshot_id,
        "cluster_membership_digest": _identity("walletseedcluster:sha256:", list(profile.subject_wallets)), **clocks,
        "nonwallet_version": "NONWALLET_MIDPOINT_V1", "wallet_added_version": "WALLET_BLEND_010_V1",
        "source_route_evidence_refs": {"route_id": _route(readiness["route"])["route_id"], "readiness_cohort_id": profile.cohort_snapshot_id,
            "readiness_head": readiness["ledger_head"], "discovery_refs": list(references), "gamma_market_id": instrument["gamma_market_id"], "requests": []},
        "observation_group_missingness_policies": {"group": instrument["leakage_group_id"], "membership": list(profile.subject_wallets), "no_replacement": True},
        "approved_source_call_byte_elapsed_limits": dict(budget), "human_approval_record": human_approval}
    seal = {"payload": payload, "digest": _identity("walletstudy:sha256:", payload), "approval": None}
    _seal(seal)
    return SeedResult("SYNTHETIC_SEAL_UNAPPROVED", seal)


def _request(request, phase, payload):
    _require(type(request) is Request and re.fullmatch(r"[a-z][a-z0-9_]{0,63}", request.name) is not None)
    unsafe = []
    _scan_forbidden_terms(asdict(request), "", unsafe); _scan_raw_metadata_keys(asdict(request), "", unsafe)
    _require(not unsafe, "REQUEST_DENIED")
    if request.url is not None:
        _require(request.method == "GET" and request.params == ())
        allowed = (f"https://clob.polymarket.com/book?token_id={payload['target_token_id']}",)
        market = payload["source_route_evidence_refs"].get("gamma_market_id")
        if type(market) is str and re.fullmatch(r"[1-9][0-9]{0,31}", market):
            allowed += (f"https://gamma-api.polymarket.com/markets/{market}",)
        _require(request.url in allowed and (phase != "READINESS" or "/book" not in request.url), "REQUEST_DENIED")
        return
    _require(request.method in RPC_METHODS and type(request.params) is tuple, "REQUEST_DENIED")
    params = request.params
    if request.method == "eth_chainId":
        _require(params == ())
    elif request.method == "eth_getCode":
        _require(len(params) == 2 and params[0] in (EXCHANGE, CTF)); _quantity(params[1])
    elif request.method in ("eth_getBlockByNumber", "eth_getBlockByHash"):
        _require(len(params) == 2 and type(params[1]) is bool)
        if request.method == "eth_getBlockByHash": _hex(params[0], 32)
        elif params[0] != "finalized": _quantity(params[0])
    elif request.method == "eth_getTransactionReceipt":
        _require(phase == "DECISION" and len(params) == 1); _hex(params[0], 32)
    elif request.method == "eth_getLogs":
        _require(phase == "DECISION" and len(params) == 1)
        filters = _closed(params[0], ("address", "fromBlock", "toBlock", "topics"))
        _require(filters["address"] == EXCHANGE and 0 <= _quantity(filters["toBlock"]) - _quantity(filters["fromBlock"]) < LOG_RANGE_BLOCKS)
        wallets = payload["observation_group_missingness_policies"]["membership"]
        makers = ["0x" + "0" * 24 + wallet[2:] for wallet in wallets]
        _require(filters["topics"] == [TOPIC, None, makers[0] if len(makers) == 1 else makers], "COVERAGE_UNKNOWN")
    else:
        _require(len(params) == 2)
        call = _closed(params[0], ("to", "data")); _quantity(params[1])
        _hex(call["data"])
        _require(call["to"] in (EXCHANGE, CTF) and call["data"][:10] in SELECTORS)
        _require(phase == "LABEL" or call["data"][:10] not in ("0xdd34de67", "0x0504c814"), "REQUEST_DENIED")


def _rpc_post(request, max_bytes, timeout, opener=None, *, context=None):
    """Dormant bounded transport. Public capture cannot activate it in this WP."""
    _require(type(request) is Request and request.method in RPC_METHODS and request.url is None, "REQUEST_DENIED")
    _require(opener is not None or (type(context) is _ReadinessRun and context.production and context.active and type(context.permit) is _ReadinessPermit and context.permit.issuer is _CONSOLE_PERMIT and not context.permit.active and context.permit.request_digest == context.request["digest"]), "PRODUCTION_DISABLED")
    _require(not (context is not None and context.production and opener is not None), "PRODUCTION_DISABLED")
    _require(type(max_bytes) is int and 0 < max_bytes <= 2097152 and type(timeout) in (int, float) and math.isfinite(timeout) and 0 < timeout <= 5, "LIMIT_INVALID")
    data = json.dumps({"jsonrpc": "2.0", "id": 1, "method": request.method, "params": request.params}, separators=(",", ":")).encode()
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            raise SeedError("REQUEST_DENIED")
    client = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    req = urllib.request.Request(f"https://{RPC_HOST}/", data=data, headers={"Content-Type": "application/json"}, method="POST")
    response = None
    try:
        try:
            response = client.open(req, timeout=timeout)
        except urllib.error.HTTPError as error:
            response = error
        status = response.status
        _require(type(status) is int, "SOURCE_INVALID")
        if context is not None:
            context.http_status = status
        chunks = []
        received = 0
        for _ in range((max_bytes + 65536) // 65536):
            remaining = max_bytes + 1 - received
            if remaining <= 0:
                break
            if context is not None:
                remaining_timeout = min(timeout, context.remaining_seconds(), timeout - (time.monotonic() - context.call_monotonic))
                _require(remaining_timeout > 0, "LIMIT_INVALID")
                stream_socket = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
                _require(not context.production or stream_socket is not None, "SOURCE_INVALID")
                if stream_socket is not None:
                    stream_socket.settimeout(remaining_timeout)
            chunk = response.read(min(65536, remaining))
            _require(type(chunk) is bytes and len(chunk) <= min(65536, remaining), "SOURCE_INVALID")
            if not chunk:
                break
            chunks.append(chunk)
            received += len(chunk)
            if context is not None:
                context.received_bytes += len(chunk)
                context.body = b"".join(chunks)
        body = b"".join(chunks)
        _require(len(body) <= max_bytes, "LIMIT_INVALID")
        _require(status == 200, "SOURCE_INVALID")
        return body
    except SeedError:
        raise
    except (OSError, ValueError, urllib.error.URLError):
        raise SeedError("SOURCE_UNAVAILABLE") from None
    finally:
        if response is not None:
            response.close()


def _retain(directory, name, content):
    directory = Path(directory)
    _require(directory.is_dir() and not directory.is_symlink(), "PATH_INVALID")
    path = directory / name
    _require(not path.is_symlink(), "PATH_INVALID")
    try:
        with path.open("xb") as stream:
            stream.write(content)
    except FileExistsError:
        _require(path.read_bytes() == content, "REPLAY_CONFLICT")
    return sha256(content).hexdigest()


def _raw(frame):
    book = frame.request.url and "/book" in frame.request.url
    venue = frame.request.url and frame.request.url.startswith("https://gamma-api.polymarket.com/markets/")
    return build_raw_evidence_reference(source_system="POLYMARKET_CLOB" if book else "POLYMARKET_GAMMA" if venue else "POLYGON_RPC",
        endpoint="/book" if book else "/markets/" + frame.request.url.rsplit("/", 1)[1] if venue else frame.request.method,
        retrieval_method="GET" if frame.request.url else "POST/read-only-RPC", content_sha256=sha256(frame.body).hexdigest(),
        byte_length=len(frame.body), media_type="application/json", pit=build_pit_timestamps(local_first_seen_time=frame.observed_at, ingestion_time=frame.observed_at),
        dq_flags=("OK",), replay_fidelity="EXACT", raw_snapshot_ref=frame.reference,
        request_parameters={"token_id": frame.request.url.split("token_id=", 1)[1]} if frame.request.url and "/book" in frame.request.url else {"request": _identity("rpc:", asdict(frame.request))})


def _source_limits(frames, payload, cutoff=None):
    budget = payload["approved_source_call_byte_elapsed_limits"]; _budget(budget)
    _require(0 < len(frames) <= budget["calls"], "LIMIT_INVALID")
    total = 0; starts = []; completions = []
    for frame in frames:
        _require(type(frame) is SourceFrame and frame.code_sha == payload["code_sha"], "VERSION_INVALID")
        begin, end = _stamp(frame.started_at or frame.observed_at), _stamp(frame.observed_at)
        _require(begin <= end and (cutoff is None or end <= _stamp(cutoff)), "LATE_SOURCE")
        _require(end - begin <= timedelta(seconds=budget["timeout_seconds"]), "LIMIT_INVALID")
        maximum = 65536 if frame.request.url and "/book" in frame.request.url else 2097152
        _require(type(frame.body) is bytes and len(frame.body) <= maximum, "LIMIT_INVALID")
        total += len(frame.body); starts.append(begin); completions.append(end)
    _require(total <= budget["bytes"] and max(completions) - min(starts) <= timedelta(seconds=budget["elapsed_seconds"]), "LIMIT_INVALID")


def _coverage_frames(bundle, instrument):
    return tuple(bundle["finality"].values()) + tuple(instrument["mapping"].values()) + bundle["blocks"] + bundle["receipts"] + bundle["logs"]


@_public
def capture_seed_evidence(*, seal, phase, ledger_path, output_dir, transport=None):
    # No trusted external operator receipt exists yet. Even a self-consistent REAL
    # approval mapping cannot reach either production transport implementation.
    _require(type(transport) is SyntheticTransport, "PRODUCTION_DISABLED")
    _require(phase in ("READINESS", "DECISION", "LABEL"), "PHASE_INVALID")
    if phase == "READINESS":
        _closed(seal, ("kind", "payload", "digest", "approval"))
        _require(seal["kind"] == "SYNTHETIC_READINESS", "PHASE_INVALID")
        _require(seal["digest"] == _identity("walletreadiness:sha256:", seal["payload"]))
        _approval(seal, phase)
        payload = seal["payload"]
    else:
        _require("kind" not in seal, "PHASE_INVALID")
        payload = _seal(seal); _approval(seal, phase)
    budget = payload["approved_source_call_byte_elapsed_limits"]; _budget(budget)
    _require(0 < len(transport.frames) <= budget["calls"] and len({f.request.name for f in transport.frames}) == len(transport.frames), "LIMIT_INVALID")
    _source_limits(transport.frames, payload, payload.get("decision_time") if phase == "DECISION" else None)
    loaded = L.load_and_verify_wallet_evidence_ledger(ledger_path)
    _require(loaded.is_valid, "LEDGER_INVALID")
    start = time.monotonic(); used = 0; records = []; refs = []; raw_refs = []; manifest_refs = []
    cutoff = payload.get("decision_time") if phase == "DECISION" else None
    for frame in transport.frames:
        _request(frame.request, phase, payload)
        _require(frame.code_sha == payload["code_sha"], "VERSION_INVALID")
        _require(time.monotonic() - start <= budget["elapsed_seconds"], "LIMIT_INVALID")
        maximum = 65536 if frame.request.url and "/book" in frame.request.url else 2097152
        _require(len(frame.body) <= min(maximum, budget["bytes"] - used), "LIMIT_INVALID")
        _frame(frame, cutoff=cutoff)
        used += len(frame.body); raw = _raw(frame)
        manifest = build_research_provenance_manifest(repo_code_identity=frame.code_sha, information_cutoff=frame.observed_at,
            input_evidence_reference_ids=(raw.raw_evidence_reference_id,), input_content_hashes=(raw.content_sha256,),
            output_identity=frame.reference, output_hash=sha256(frame.body).hexdigest(), request_source_version_refs=(seal["digest"],))
        records += [raw, manifest]; refs.append(frame.reference)
        raw_refs.append(raw.raw_evidence_reference_id); manifest_refs.append(manifest.research_provenance_manifest_id)
    coverage = None
    if transport.evidence is not None:
        _require(phase == "DECISION", "PHASE_INVALID")
        _closed(transport.evidence, ("instrument", "coverage"))
        captured_refs = {frame.reference for frame in transport.frames}
        def verify_refs(value):
            if type(value) is SourceFrame:
                _require(value.reference in captured_refs, "SOURCE_INVALID")
            elif type(value) is dict:
                for child in value.values(): verify_refs(child)
            elif type(value) in (tuple, list):
                for child in value: verify_refs(child)
        verify_refs(transport.evidence)
        chain_records, coverage = _chain_records(transport.evidence, seal)
        records += chain_records
    # Prevalidate the complete batch before publishing any retained file.
    L._prepare_batch(records)
    _require(time.monotonic() - start <= budget["elapsed_seconds"], "LIMIT_INVALID")
    binding = {"phase": phase, "seal_digest": seal["digest"], "sources": sorted(refs)}
    binding_file = "study.json" if phase != "READINESS" else "readiness.json"
    _retain(output_dir, binding_file, C.wallet_canonical_json_bytes({"payload": payload, "digest": seal["digest"]}))
    _retain(output_dir, phase.lower() + "-input.json", C.wallet_canonical_json_bytes(binding))
    for frame in transport.frames:
        _retain(output_dir, sha256(frame.body).hexdigest() + ".raw", frame.body)
    appended = L.append_wallet_evidence_records(ledger_path, records)
    _require(appended.is_valid, "LEDGER_INVALID")
    receipt = {"phase": phase, "code_sha": payload["code_sha"], "seal_digest": seal["digest"], "origin": "SYNTHETIC",
        "source_refs": refs, "calls": len(transport.frames), "bytes": used, "ledger_head": appended.snapshot.head_hash,
        "approved_budget": dict(budget), "raw_evidence_reference_ids": raw_refs, "research_provenance_manifest_ids": manifest_refs,
        "coverage_epistemics": COVERAGE_EPISTEMICS, "provider_attestation": "NOT_ESTABLISHED", "coverage": coverage,
        "requests": [{"request": asdict(frame.request), "started_at": frame.started_at or frame.observed_at, "completed_at": frame.observed_at,
                      "body_sha256": sha256(frame.body).hexdigest(), "bytes": len(frame.body), "reference": frame.reference} for frame in transport.frames]}
    receipt_id = _identity("walletseedcapture:sha256:", receipt)
    _retain(output_dir, receipt_id.split(":")[-1] + ".json", C.wallet_canonical_json_bytes(receipt))
    return SeedResult("SYNTHETIC_CAPTURE_RETAINED", {"receipt_id": receipt_id, **receipt})


def _coverage(bundle, seal, instrument):
    """Complete only conditional on pinned RPC conformance, never provider attestation."""
    _closed(bundle, ("blocks", "receipts", "logs", "finality", "start_block", "end_block"))
    payload = seal["payload"]; cutoff = payload["decision_time"]
    _require(all(type(bundle[key]) is tuple for key in ("blocks", "receipts", "logs")), "COVERAGE_UNKNOWN")
    _source_limits(_coverage_frames(bundle, instrument), payload, cutoff)
    _require(list(instrument["wallets"]) == payload["observation_group_missingness_policies"]["membership"], "GROUP_INVALID")
    route = _route(bundle["finality"], cutoff); _mapping_proof(instrument, route, cutoff)
    first, last = bundle["start_block"], bundle["end_block"]
    _require(type(first) is int and type(last) is int and 0 < first <= last == route["finalized_block"], "COVERAGE_UNKNOWN")
    start = _stamp(cutoff) - timedelta(hours=1)
    headers = {}
    for frame in bundle["blocks"]:
        header = _frame(frame, "eth_getBlockByNumber", cutoff)
        number = _quantity(header["number"])
        _require(frame.request.params in ((header["number"], False), (header["number"], True)), "COVERAGE_UNKNOWN")
        _require(number not in headers and first - 1 <= number <= last, "COVERAGE_UNKNOWN")
        _hex(header["hash"], 32); _hex(header["parentHash"], 32)
        timestamp = datetime.fromtimestamp(_quantity(header["timestamp"]), timezone.utc)
        _require(timestamp <= _stamp(frame.observed_at) and timestamp <= _stamp(route["finalized_time"]), "FINALITY_INVALID")
        headers[number] = (frame, header, timestamp)
    _require(all(number in headers for number in (first - 1, first, last)), "COVERAGE_UNKNOWN")
    _require(headers[first - 1][2] < start <= headers[first][2], "COVERAGE_UNKNOWN")
    _require(headers[last][1]["hash"] == route["finalized_hash"] and headers[last][2] == _stamp(route["finalized_time"]), "FINALITY_INVALID")
    ordered = sorted(headers)
    for index, number in enumerate(ordered):
        if index:
            prev = ordered[index - 1]
            _require(headers[prev][2] < headers[number][2], "FINALITY_INVALID")
            if number == prev + 1:
                _require(headers[number][1]["parentHash"] == headers[prev][1]["hash"], "FINALITY_INVALID")
    # Exact disjoint numeric chunks cover the eligible finalized range once.
    _require((last - first) // LOG_RANGE_BLOCKS + 1 == len(bundle["logs"]), "COVERAGE_UNKNOWN")
    expected_ranges = [(n, min(n + LOG_RANGE_BLOCKS - 1, last)) for n in range(first, last + 1, LOG_RANGE_BLOCKS)]
    _require(len(bundle["logs"]) == len(expected_ranges), "COVERAGE_UNKNOWN")
    rows = []; seen = set()
    for frame, bounds in zip(bundle["logs"], expected_ranges):
        _request(frame.request, "DECISION", payload)
        filters = frame.request.params[0]
        _require((_quantity(filters["fromBlock"]), _quantity(filters["toBlock"])) == bounds, "COVERAGE_UNKNOWN")
        logs = _frame(frame, "eth_getLogs", cutoff)
        # The ceiling may be a provider cap. Exact-cap results fail conservatively.
        _require(type(logs) is list and len(logs) < 256, "COVERAGE_UNKNOWN")
        for log in logs:
            _require(type(log) is dict and log.get("removed") is False, "FINALITY_INVALID")
            _require(C.canonicalize_evm_address(log["address"]) == EXCHANGE and len(log["topics"]) == 4 and log["topics"][0] == TOPIC, "ABI_INVALID")
            topics = [_hex(topic, 32) for topic in log["topics"]]
            _require(topics[2][:12] == topics[3][:12] == bytes(12) and "0x" + topics[2][12:].hex() in instrument["wallets"], "COVERAGE_UNKNOWN")
            data = _hex(log["data"], 224); _hex(log["transactionHash"], 32); _hex(log["blockHash"], 32)
            _require(int.from_bytes(data[:32], "big") in (0, 1) and int.from_bytes(data[64:96], "big") > 0 and int.from_bytes(data[96:128], "big") > 0, "ABI_INVALID")
            _quantity(log["transactionIndex"])
            number = _quantity(log["blockNumber"])
            _require(bounds[0] <= number <= bounds[1] and number in headers, "FINALITY_INVALID")
            identity = (log["transactionHash"], _quantity(log["logIndex"]))
            _require(identity not in seen, "COVERAGE_UNKNOWN")
            seen.add(identity); rows.append((frame, log))
    receipts = {}
    for frame in bundle["receipts"]:
        record = _frame(frame, "eth_getTransactionReceipt", cutoff)
        tx = record["transactionHash"]
        _require(frame.request.params == (tx,) and tx not in receipts, "IDENTITY_INVALID")
        _require(record["status"] == "0x1", "FINALITY_INVALID")
        receipts[tx] = (frame, record)
    _require(set(receipts) == {log["transactionHash"] for _, log in rows}, "COVERAGE_UNKNOWN")
    expected = []
    for tx, (_, record) in receipts.items():
        number = _quantity(record["blockNumber"])
        _require(number in headers and record["blockHash"] == headers[number][1]["hash"], "FINALITY_INVALID")
        transactions = headers[number][1]["transactions"]
        index = _quantity(record["transactionIndex"])
        _require(type(transactions) is list and index < len(transactions), "COVERAGE_UNKNOWN")
        transaction = transactions[index]
        _require((transaction["hash"] if type(transaction) is dict else transaction) == tx, "COVERAGE_UNKNOWN")
        for log in record["logs"]:
            if C.canonicalize_evm_address(log["address"]) == EXCHANGE and log["topics"] and log["topics"][0] == TOPIC:
                _require(len(log["topics"]) == 4, "ABI_INVALID")
                maker = _hex(log["topics"][2], 32)
                _require(maker[:12] == bytes(12), "ABI_INVALID")
                if "0x" + maker[12:].hex() in instrument["wallets"]:
                    expected.append(log)
    _require(sorted(C.wallet_canonical_json_bytes(x) for x in expected) == sorted(C.wallet_canonical_json_bytes(x) for _, x in rows), "COVERAGE_UNKNOWN")
    events = []
    for source, log in rows:
        frame, record = receipts[log["transactionHash"]]
        number = _quantity(log["blockNumber"]); block = headers[number][0]
        for key in ("transactionHash", "blockHash", "blockNumber", "transactionIndex"):
            _require(log[key] == record[key], "IDENTITY_INVALID")
        _require(sum(item == log for item in record["logs"]) == 1, "IDENTITY_INVALID")
        token = str(int.from_bytes(_hex(log["data"], 224)[32:64], "big"))
        if token not in (instrument["target_token_id"], instrument["complement_token_id"]):
            continue
        event, _ = _fill(source, frame, block, {"route": bundle["finality"], "canonical": block, "cutoff": cutoff}, instrument, selected_log=log)
        _require(start <= _stamp(event.event_time) <= _stamp(route["finalized_time"]), "COVERAGE_UNKNOWN")
        events.append((source, event))
    _require(len({e.wallet_event_id for _, e in events}) == len(events), "IDENTITY_INVALID")
    proof = {"status": "SOURCE_CONTRACT_COMPLETE_CONDITIONAL", "epistemics": COVERAGE_EPISTEMICS,
        "provider_attestation": "NOT_ESTABLISHED", "start_block": first, "finalized_frontier": last,
        "finalized_frontier_time": route["finalized_time"], "covered_block_count": last - first + 1,
        "range_count": len(expected_ranges), "returned_log_count": len(rows),
        "source_refs": [f.reference for f in _coverage_frames(bundle, instrument)]}
    return events, proof


def _chain_records(evidence, seal):
    events, proof = _coverage(evidence["coverage"], seal, evidence["instrument"])
    run = C.derive_ingest_run_key({"study_digest": seal["digest"], "phase": "DECISION"})
    records = []
    pages = {}
    for frame, event in events:
        if frame.reference not in pages:
            raw = _raw(frame)
            page = C.build_wallet_feed_page_evidence(raw_evidence_reference_id=raw.raw_evidence_reference_id,
                ingest_run_key=run, feed_key="TRADES", canonical_request_identity={"source": "POLYGON_RPC", "scope": seal["digest"]},
                requested_page_size=256, has_more=False, local_first_seen_time=frame.observed_at, ingestion_time=frame.observed_at,
                api_source_parser_version="wallet-seed/1.0.0", dq_flags=("OK",), replay_fidelity="EXACT",
                source_row_count=len(_frame(frame)), normalized_event_count=len(_frame(frame)), observation_count=len(_frame(frame)))
            pages[frame.reference] = (raw, page); records += [raw, page]
        raw, page = pages[frame.reference]
        observation = C.build_wallet_event_observation(wallet_event_id=event.wallet_event_id,
            wallet_feed_page_evidence_id=page.wallet_feed_page_evidence_id, ingest_run_key=run, source_system="POLYGON_RPC",
            endpoint="eth_getLogs", source_activity_type="OrderFilled", pit=build_pit_timestamps(local_first_seen_time=frame.observed_at,
                ingestion_time=frame.observed_at, event_time=event.event_time), dq_flags=("OK",), replay_fidelity="EXACT", raw_evidence_reference_id=raw.raw_evidence_reference_id)
        link = C.build_wallet_reconciliation_link(reconciliation_state="CHAIN_ONLY", relation_kind="CHAIN_CONFIRMATION",
            event_ids=(event.wallet_event_id,), finality_state="FINALIZED")
        records += [event, observation, link]
    return records, proof


def _decision_ledger(path, expected_head):
    loaded = L.load_and_verify_wallet_evidence_ledger(path)
    _require(loaded.is_valid and loaded.snapshot.head_hash == expected_head, "LEDGER_INVALID")
    return loaded.snapshot


@_public
def materialize_forecast_pair(*, seal, decision_bundle, ledger_path):
    payload = _seal(seal); _approval(seal, "DECISION")
    _closed(decision_bundle, ("instrument", "coverage", "ledger_head", "cohort", "profile", "contexts", "identity_observability", "books", "committed_at"))
    _decision_ledger(ledger_path, decision_bundle["ledger_head"])
    instrument = _instrument(decision_bundle["instrument"])
    for key in ("condition_id", "target_token_id", "complement_token_id", "rule_snapshot_digest", "event_id", "leakage_group_id"):
        _require(instrument[key] == payload[key], "SEAL_INVALID")
    cohort, profile = decision_bundle["cohort"], decision_bundle["profile"]
    _require(cohort.wallet_discovery_cohort_snapshot_id == payload["cohort_reference_id"] and profile.subject_wallets == instrument["wallets"], "PROFILE_INVALID")
    _require(list(instrument["wallets"]) == payload["observation_group_missingness_policies"]["membership"], "GROUP_INVALID")
    _require(all(context.independence_group_id == payload["leakage_group_id"] for context in decision_bundle["contexts"]), "GROUP_INVALID")
    t0 = _stamp(payload["decision_time"])
    _require(_stamp(profile.as_of) == t0 and profile.cohort_snapshot_id == payload["cohort_reference_id"], "PROFILE_INVALID")
    events, proof = _coverage(decision_bundle["coverage"], seal, instrument)
    snapshot = _decision_ledger(ledger_path, decision_bundle["ledger_head"])
    for frame in _coverage_frames(decision_bundle["coverage"], instrument):
        raw = _raw(frame)
        manifest = build_research_provenance_manifest(repo_code_identity=frame.code_sha, information_cutoff=frame.observed_at,
            input_evidence_reference_ids=(raw.raw_evidence_reference_id,), input_content_hashes=(raw.content_sha256,),
            output_identity=frame.reference, output_hash=sha256(frame.body).hexdigest(), request_source_version_refs=(seal["digest"],))
        _require(raw.raw_evidence_reference_id in snapshot.record_ids() and manifest.research_provenance_manifest_id in snapshot.record_ids(), "SOURCE_INVALID")
    native_ids = set(profile.included_wallet_event_ids)
    _require(native_ids == {event.wallet_event_id for _, event in events}, "PROFILE_INVALID")
    books = []
    for frame in decision_bundle["books"]:
        _require(frame.code_sha == payload["code_sha"], "VERSION_INVALID")
        document = _frame(frame, cutoff=payload["decision_time"])
        _require(frame.request.url == f"https://clob.polymarket.com/book?token_id={payload['target_token_id']}", "SOURCE_INVALID")
        if _stamp(frame.observed_at) < t0 - timedelta(seconds=30): continue
        _require(document["market"] == payload["condition_id"] and document["asset_id"] == payload["target_token_id"])
        _require(len(frame.body) <= 65536 and 0 < len(document["bids"]) <= 256 and 0 < len(document["asks"]) <= 256)
        bid = max(_decimal(x["price"]) for x in document["bids"]); ask = min(_decimal(x["price"]) for x in document["asks"])
        _require(0 < bid <= ask < 1 and ask - bid <= Decimal("0.1"), "BOOK_INVALID")
        raw = _raw(frame)
        manifest = build_research_provenance_manifest(repo_code_identity=frame.code_sha, information_cutoff=frame.observed_at,
            input_evidence_reference_ids=(raw.raw_evidence_reference_id,), input_content_hashes=(raw.content_sha256,),
            output_identity=frame.reference, output_hash=sha256(frame.body).hexdigest(), request_source_version_refs=(seal["digest"],))
        for sign, price, side in ((-1, bid, "bids"), (1, ask, "asks")):
            depth = sum((_decimal(x["size"]) for x in document[side] if _decimal(x["price"]) == price), Decimal(0))
            witness = B.WalletCopyabilityQuoteWitness("DATA_API_RESPONSE_CONDITION_ID", payload["condition_id"], "CLOB_TOKEN_ID", payload["target_token_id"],
                sign, _fixed(price), _fixed(depth), ObservabilityEvidence(local_first_seen_time=frame.observed_at), ("OK",), "EXACT", raw, manifest, frame.body)
            native = B.build_wallet_copyability_research_assessment(profile=profile, wallet_ledger_path=ledger_path, expected_ledger_head=decision_bundle["ledger_head"],
                cohort_snapshot=cohort, target_wallet=profile.representative_wallet, as_of=payload["decision_time"], market_contexts=decision_bundle["contexts"],
                quote_witnesses=(witness,), delay_seconds=("0",), cost_scenarios=(B.WalletCopyabilityCostScenario(None, None, None, None),), identity_observability=decision_bundle["identity_observability"])
            _require(native.quote_evidence[0].source_status == "OBSERVED", "BOOK_INVALID")
        semantic_book = {"market": document["market"], "asset_id": document["asset_id"],
            "bids": sorted((x["price"], x["size"]) for x in document["bids"]), "asks": sorted((x["price"], x["size"]) for x in document["asks"])}
        books.append((frame.observed_at, bid, ask, frame.reference, _identity("book:", semantic_book)))
    if not books:
        return _pair("UNKNOWN", payload, decision_bundle, None, None, None, proof)
    latest = max(_stamp(x[0]) for x in books); selected = [x for x in books if _stamp(x[0]) == latest]
    if len({x[4] for x in selected}) != 1:
        return _pair("UNKNOWN", payload, decision_bundle, None, None, None, proof)
    buys = [(frame.observed_at, event) for frame, event in events if event.side == "BUY"]
    vote = None
    if buys:
        last = max(_stamp(seen) for seen, _ in buys)
        votes = {int(event.token_value == payload["target_token_id"]) for seen, event in buys if _stamp(seen) == last}
        if len(votes) != 1: return _pair("UNKNOWN", payload, decision_bundle, None, None, None, proof)
        vote = votes.pop()
    if type(decision_bundle["committed_at"]) is not SyntheticDecisionClock or _stamp(decision_bundle["committed_at"].at) != t0:
        return _pair("UNMATCHED", payload, decision_bundle, None, None, vote, proof)
    with localcontext() as context:
        context.prec = 80
        p0 = (selected[0][1] + selected[0][2]) / 2
        pw = p0 if vote is None else Decimal("0.9") * p0 + Decimal("0.1") * vote
    return _pair("PENDING", payload, decision_bundle, _fixed(p0), _fixed(pw), vote, proof)


def _pair(status, payload, bundle, p0, pw, vote, proof):
    pair = {"method_digest": METHOD_DIGEST, "decision_time": payload["decision_time"], "target_event_end": payload["target_event_end"],
        "code_sha": payload["code_sha"],
        "label_deadline": payload["label_deadline"], "condition_id": payload["condition_id"], "target_token_id": payload["target_token_id"], "complement_token_id": payload["complement_token_id"],
        "rule_snapshot_digest": payload["rule_snapshot_digest"], "leakage_group_id": payload["leakage_group_id"], "ledger_head": bundle["ledger_head"],
        "p_nonwallet": p0, "p_wallet_added": pw, "p_masked": p0, "vote": vote, "coverage": proof,
        "label": None, "loss_nonwallet": None, "loss_wallet_added": None, "delta": None,
        "enrolled_count": "NOT_ESTABLISHED", "synthetic_counts": {state: int(state == status) for state in STATES}}
    pair["pair_id"] = _identity("walletseedpair:sha256:", pair)
    result = SeedResult(status, pair)
    # Internal result integrity, not a credential or a human-approval mechanism.
    # JSON round-trips and caller-rehashed mappings cannot become source-bound pairs.
    object.__setattr__(result, "_pair_commitment", pair["pair_id"])
    return result


@_public
def attach_final_label(*, pair, label_bundle, as_of):
    _require(type(pair) is SeedResult and pair.status in ("PENDING", "CENSORED", "MATCHED"), "PAIR_INVALID")
    _require(getattr(pair, "_pair_commitment", None) == pair.payload.get("pair_id"), "PAIR_INVALID")
    original = dict(pair.payload); pair_id = original.pop("pair_id")
    _require(pair_id == _identity("walletseedpair:sha256:", original), "PAIR_INVALID")
    _closed(label_bundle, ("instrument", "route", "denominator", "target_numerator", "complement_numerator", "venue"))
    instrument = _instrument(label_bundle["instrument"])
    for key in ("condition_id", "target_token_id", "complement_token_id", "rule_snapshot_digest", "leakage_group_id"):
        _require(instrument[key] == original[key], "LABEL_INVALID")
    route = _route(label_bundle["route"], as_of); _mapping_proof(instrument, route, as_of)
    _require(route["code_sha"] == original["code_sha"] and _stamp(route["finalized_time"]) > _stamp(original["target_event_end"]), "LABEL_INVALID")
    clocks = [frame.observed_at for key, frame in label_bundle.items() if type(frame) is SourceFrame]
    clocks += [frame.observed_at for frame in label_bundle["route"].values()]
    _require(all(_stamp(clock) > _stamp(original["target_event_end"]) and _stamp(clock) > _stamp(original["decision_time"]) for clock in clocks), "LABEL_INVALID")
    values = []
    for key, selector in (("denominator", "0xdd34de67"), ("target_numerator", "0x0504c814"), ("complement_numerator", "0x0504c814")):
        data = selector + original["condition_id"][2:]
        if key != "denominator": data += format(0 if key == "target_numerator" else 1, "064x")
        frame = label_bundle[key]
        _require(frame.code_sha == original["code_sha"], "VERSION_INVALID")
        _require(frame.request.params == ({"to": CTF, "data": data}, hex(route["finalized_block"])), "LABEL_INVALID")
        values.append(int.from_bytes(_hex(_frame(frame, "eth_call", as_of), 32), "big"))
    denominator, target, complement = values
    venue = _frame(label_bundle["venue"], cutoff=as_of)
    _require(label_bundle["venue"].code_sha == original["code_sha"], "VERSION_INVALID")
    _require(label_bundle["venue"].request.url == f"https://gamma-api.polymarket.com/markets/{instrument['gamma_market_id']}", "LABEL_INVALID")
    _require(str(venue.get("id")) == instrument["gamma_market_id"] and venue.get("conditionId") == original["condition_id"] and venue.get("negRisk") is False, "LABEL_INVALID")
    _require(not any(venue.get(flag) is True for flag in ("disputed", "void", "cancelled")), "LABEL_INVALID")
    tokens, prices = venue.get("clobTokenIds"), venue.get("outcomePrices")
    tokens = json.loads(tokens) if type(tokens) is str else tokens
    prices = json.loads(prices) if type(prices) is str else prices
    _require(type(tokens) is list and type(prices) is list and len(tokens) == len(prices) == 2 and set(tokens) == {original["target_token_id"], original["complement_token_id"]}, "LABEL_INVALID")
    resolution = venue.get("umaResolutionStatus")
    if denominator == 0:
        _require(resolution in ("proposed", "unresolved"), "LABEL_INVALID")
        status = "CENSORED" if _stamp(as_of) > _stamp(original["label_deadline"]) else "PENDING"
    else:
        _require(target in (0, denominator) and complement in (0, denominator) and target + complement == denominator, "LABEL_INVALID")
        y = int(target == denominator)
        _require(pair.status != "MATCHED" or original["label"] == y, "LABEL_INVALID")
        _require(resolution == "resolved" and venue.get("closed") is True, "LABEL_INVALID")
        by_token = {token: _decimal(price) for token, price in zip(tokens, prices)}
        _require(by_token[original["target_token_id"]] == y and by_token[original["complement_token_id"]] == 1 - y, "LABEL_INVALID")
        _require(all(_stamp(clock) <= _stamp(original["label_deadline"]) for clock in clocks), "LATE_SOURCE")
        with localcontext() as context:
            context.prec = 80
            l0 = (_decimal(original["p_nonwallet"]) - y) ** 2
            lw = (_decimal(original["p_wallet_added"]) - y) ** 2
            delta = l0 - lw
        original.update(label=y, loss_nonwallet=_fixed(l0), loss_wallet_added=_fixed(lw), delta=_fixed(delta))
        status = "MATCHED"
    original["synthetic_counts"] = {state: int(state == status) for state in STATES}
    original["pair_id"] = _identity("walletseedpair:sha256:", original)
    result = SeedResult(status, original)
    object.__setattr__(result, "_pair_commitment", original["pair_id"])
    return result


READINESS_POLICY_ID = "walletreadinesspolicy:sha256:1131374f86691e8f599b119f97155a2cda70f4d38fb70b468971a94267d48a2e"
READINESS_FIELDS = ("kind", "request_id", "code_sha", "method_digest", "not_before", "expires_at", "output_dir", "budget", "source_policy_id", "digest")
READINESS_STATUSES = frozenset({"DENIED", "READINESS_PREVIEW", "READINESS_INCONCLUSIVE", "SYNTHETIC_READINESS_OBSERVED", "OBSERVED_ROUTE_COMPATIBLE_PENDING_REVIEW"})
READINESS_ERRORS = frozenset({"FIELD_INVALID", "SOURCE_INVALID", "SOURCE_UNAVAILABLE", "CHAIN_INVALID", "VERSION_INVALID", "FINALITY_INVALID", "LIMIT_INVALID", "WINDOW_INVALID", "PATH_INVALID", "REPLAY_CONFLICT", "REQUEST_DENIED", "APPROVAL_INVALID", "PRODUCTION_DISABLED", "OPERATOR_CANCELLED", "ARGUMENT_INVALID"})
_CONSOLE_PERMIT = object()
_DIRECT_RESULT = object()


@dataclass
class _ReadinessPermit:
    request_digest: str
    approval_id: str
    issuer: object = field(repr=False)
    active: bool = True


@dataclass(frozen=True)
class ReadinessResult:
    status: str
    errors: tuple[str, ...] = ()
    request_digest: str | None = None
    receipt_id: str | None = None
    origin: str = "SYNTHETIC"
    operator_approval: str = "MANUAL_ASSERTION_REQUIRES_EXTERNAL_REVIEW"
    human_identity: str = "NOT_MACHINE_ATTESTED"
    observations: dict = field(default_factory=dict)
    accounting: dict = field(default_factory=dict)
    coverage_epistemics: str = COVERAGE_EPISTEMICS
    provider_attestation: str = "NOT_ESTABLISHED"
    enrolled_count: str = "NOT_ESTABLISHED"
    numeric_summary: None = None
    study_activated: bool = False
    advisory_only: bool = True
    no_execution_authority: bool = True
    no_strategy_authority: bool = True
    no_qualification_authority: bool = True


READINESS_RESULT_FIELDS = frozenset(ReadinessResult.__dataclass_fields__)


def readiness_result_to_mapping(*, result):
    _require(type(result) is ReadinessResult, "OUTPUT_UNSAFE")
    data = asdict(result)
    _bounded(data)
    unsafe = []
    _scan_forbidden_terms(data, "", unsafe)
    _scan_raw_metadata_keys(data, "", unsafe)
    _scan_seed_output(data)
    _require(not unsafe and type(result.status) is str and result.status in READINESS_STATUSES and type(result.errors) is tuple and all(type(code) is str and code in READINESS_ERRORS for code in result.errors), "OUTPUT_UNSAFE")
    _require(type(result.observations) is dict and type(result.accounting) is dict, "OUTPUT_UNSAFE")
    for key, prefix in (("request_digest", "walletreadinessrequest:sha256:"), ("receipt_id", "walletreadinesscapture:sha256:")):
        value = getattr(result, key)
        _require(value is None or type(value) is str and re.fullmatch(re.escape(prefix) + r"[0-9a-f]{64}", value) is not None, "OUTPUT_UNSAFE")
    _require(result.origin in ("SYNTHETIC", "DIRECT_HTTPS_NON_STUDY_PENDING_REVIEW"), "OUTPUT_UNSAFE")
    _require(result.operator_approval == "MANUAL_ASSERTION_REQUIRES_EXTERNAL_REVIEW" and result.human_identity == "NOT_MACHINE_ATTESTED", "OUTPUT_UNSAFE")
    _require(result.coverage_epistemics == COVERAGE_EPISTEMICS and result.provider_attestation == result.enrolled_count == "NOT_ESTABLISHED" and result.numeric_summary is None, "OUTPUT_UNSAFE")
    _require(result.study_activated is False and all(getattr(result, key) is True for key in ("advisory_only", "no_execution_authority", "no_strategy_authority", "no_qualification_authority")), "OUTPUT_UNSAFE")
    if result.origin != "SYNTHETIC":
        _require(getattr(result, "_direct_capture", None) is _DIRECT_RESULT and getattr(result, "_commitment", None) == _identity("readinessresult:", data), "OUTPUT_UNSAFE")
    _require(result.status != "OBSERVED_ROUTE_COMPATIBLE_PENDING_REVIEW" or result.origin != "SYNTHETIC", "OUTPUT_UNSAFE")
    return data


def _readiness_public(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        try:
            result = fn(*args, **kwargs)
            readiness_result_to_mapping(result=result)
            return result
        except SeedError as error:
            return ReadinessResult("DENIED", errors=(str(error) if str(error) in READINESS_ERRORS else "FIELD_INVALID",))
        except Exception:
            return ReadinessResult("DENIED", errors=("FIELD_INVALID",))
    return call


def _utc_now():
    return datetime.now(timezone.utc)


def _utc_text(value):
    return canonicalize_utc_timestamp(value.isoformat())


def _readiness_request(request):
    _closed(request, READINESS_FIELDS)
    _bounded(request)
    unsafe = []
    _scan_forbidden_terms(request, "", unsafe)
    _scan_raw_metadata_keys(request, "", unsafe)
    _scan_seed_output(request)
    _require(not unsafe, "REQUEST_DENIED")
    _require(request["kind"] == "NON_STUDY_READINESS" and request["method_digest"] == METHOD_DIGEST and request["source_policy_id"] == READINESS_POLICY_ID, "REQUEST_DENIED")
    _require(type(request["request_id"]) is str and re.fullmatch(r"[a-z][a-z0-9_]{0,63}", request["request_id"]) is not None, "REQUEST_DENIED")
    _require(type(request["code_sha"]) is str and re.fullmatch(r"[0-9a-f]{40}", request["code_sha"]) is not None, "VERSION_INVALID")
    for key in ("not_before", "expires_at"):
        _require(type(request[key]) is str and canonicalize_utc_timestamp(request[key]) == request[key], "WINDOW_INVALID")
    begin, end = _stamp(request["not_before"]), _stamp(request["expires_at"])
    _require(timedelta(0) < end - begin <= timedelta(seconds=120) and _utc_now() < end, "WINDOW_INVALID")
    _budget(request["budget"])
    _require(request["budget"]["calls"] >= 8, "LIMIT_INVALID")
    value = request["output_dir"]
    _require(type(value) is str and 0 < len(value) <= 4096 and all(ord(character) >= 32 for character in value), "PATH_INVALID")
    _require(Path(value).is_absolute() and os.path.normpath(value) == value and str(Path(value)) == value, "PATH_INVALID")
    payload = {key: value for key, value in request.items() if key != "digest"}
    _require(request["digest"] == _identity("walletreadinessrequest:sha256:", payload), "REQUEST_DENIED")
    return json.loads(C.wallet_canonical_json_bytes(request))


@_readiness_public
def validate_readiness_request(*, request):
    checked = _readiness_request(request)
    return ReadinessResult("READINESS_PREVIEW", request_digest=checked["digest"])


def _readiness_window(request):
    _require(_stamp(request["not_before"]) <= _utc_now() < _stamp(request["expires_at"]), "WINDOW_INVALID")


def _readiness_path(request, output_dir):
    path = Path(output_dir)
    _require(str(path) == request["output_dir"] and path.is_absolute(), "PATH_INVALID")
    _require(not any(part.is_symlink() for part in (path, *path.parents)) and path.resolve() == path, "PATH_INVALID")
    if path.is_relative_to(ROOT.resolve()):
        _require(path.is_relative_to(ROOT.resolve() / "local_data") and path != ROOT.resolve() / "local_data", "PATH_INVALID")
        ignored = subprocess.run(["git", "check-ignore", "--quiet", "--", str(path.relative_to(ROOT))], cwd=ROOT, capture_output=True, timeout=5)
        _require(ignored.returncode == 0, "PATH_INVALID")
    _require(path.parent.is_dir() and (not path.exists() or path.is_dir() and not any(path.iterdir())), "REPLAY_CONFLICT")
    if not path.exists():
        path.mkdir()
    return path


@dataclass
class _ReadinessRun:
    request: dict = field(repr=False)
    directory: Path = field(repr=False)
    production: bool = False
    permit: object = None
    active: bool = True
    start_monotonic: float = field(default_factory=time.monotonic)
    call_monotonic: float = 0
    calls: int = 0
    received_bytes: int = 0
    body: bytes = field(default=b"", repr=False)
    http_status: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    synthetic_elapsed: float = 0

    def remaining_seconds(self):
        elapsed = time.monotonic() - self.start_monotonic
        _require(elapsed >= 0, "LIMIT_INVALID")
        return min(self.request["budget"]["elapsed_seconds"] - max(elapsed, self.synthetic_elapsed), (_stamp(self.request["expires_at"]) - _utc_now()).total_seconds())

    def begin_call(self):
        _readiness_window(self.request)
        _require(self.active and self.calls < self.request["budget"]["calls"] and self.received_bytes < self.request["budget"]["bytes"] and self.remaining_seconds() > 0, "LIMIT_INVALID")
        self.calls += 1
        self.body = b""
        self.http_status = None
        self.started_at = _utc_text(_utc_now())
        self.completed_at = None
        self.call_monotonic = time.monotonic()

    def check_completion(self):
        _require(self.started_at is not None and self.completed_at is not None and _stamp(self.started_at) <= _stamp(self.completed_at), "WINDOW_INVALID")
        _require(_stamp(self.request["not_before"]) <= _stamp(self.started_at) <= _stamp(self.completed_at) < _stamp(self.request["expires_at"]), "WINDOW_INVALID")
        _require((_stamp(self.completed_at) - _stamp(self.started_at)).total_seconds() <= self.request["budget"]["timeout_seconds"] and time.monotonic() - self.call_monotonic <= self.request["budget"]["timeout_seconds"] and self.remaining_seconds() > 0, "LIMIT_INVALID")

    def accounting(self):
        elapsed = max(0, time.monotonic() - self.start_monotonic, self.synthetic_elapsed)
        return {"calls": self.calls, "received_bytes": self.received_bytes, "elapsed_seconds": format(elapsed, ".6f"), "byte_cap_breached": self.received_bytes > self.request["budget"]["bytes"], "elapsed_cap_breached": elapsed > self.request["budget"]["elapsed_seconds"]}


def _readiness_plan(index, frontier):
    if index == 0:
        return Request("chain", "eth_chainId")
    if index == 1:
        return Request("finalized", "eth_getBlockByNumber", ("finalized", False))
    if index in (2, 3):
        return Request("exchange_code" if index == 2 else "ctf_code", "eth_getCode", (EXCHANGE if index == 2 else CTF, frontier["number"]))
    if index in (4, 7):
        return Request("canonical_before" if index == 4 else "canonical_after", "eth_getBlockByNumber", (frontier["number"], False))
    if index == 5:
        return Request("predeployment_code", "eth_getCode", (EXCHANGE, "0x50f81d0"))
    return Request("predeployment_logs", "eth_getLogs", ({"address": EXCHANGE, "fromBlock": "0x50f8151", "toBlock": "0x50f81d0", "topics": [TOPIC]},))


def _readiness_header(value):
    _require(type(value) is dict, "FINALITY_INVALID")
    header = {key: value[key] for key in ("number", "hash", "timestamp")}
    for key in ("number", "timestamp"):
        _require(hex(_quantity(header[key])) == header[key], "FINALITY_INVALID")
    _hex(header["hash"], 32)
    _require(header["hash"] == header["hash"].lower(), "FINALITY_INVALID")
    return header


def _readiness_observe(index, value, completed_at, frontier, observations):
    if index == 0:
        _require(value == "0x89", "CHAIN_INVALID")
        observations["chain_id"] = 137
    elif index == 1:
        frontier.update(_readiness_header(value))
        block_time = datetime.fromtimestamp(_quantity(frontier["timestamp"]), timezone.utc)
        age = (_stamp(completed_at) - block_time).total_seconds()
        _require(0 <= age <= 300, "FINALITY_INVALID")
        observations.update(finalized_block=_quantity(frontier["number"]), finalized_hash=frontier["hash"], finalized_age_seconds=format(age, ".6f"))
    elif index in (2, 3):
        digest = sha256(_hex(value)).hexdigest()
        _require(digest == (EXCHANGE_HASH if index == 2 else CTF_HASH), "VERSION_INVALID")
        observations["exchange_code_sha256" if index == 2 else "ctf_code_sha256"] = digest
    elif index in (4, 7):
        _require(_readiness_header(value) == frontier, "FINALITY_INVALID")
        observations["canonical_checks"] = observations.get("canonical_checks", 0) + 1
    elif index == 5:
        _require(value == "0x", "VERSION_INVALID")
        observations["predeployment_code"] = "EMPTY_OBSERVED"
    else:
        _require(type(value) is list and not value, "SOURCE_INVALID")
        observations["log_probe"] = "EMPTY_METHOD_SHAPE_ONLY"


def _readiness_packet(context, request, valid):
    name = request.name
    content = context.body
    body_hash = sha256(content).hexdigest()
    origin = "DIRECT_HTTPS_NON_STUDY_PENDING_REVIEW" if context.production else "SYNTHETIC"
    metadata = {"request": asdict(request), "started_at": context.started_at, "completed_at": context.completed_at, "http_status": context.http_status, "body_sha256": body_hash, "bytes": len(content), "origin": origin, "validated": valid, "code_sha": context.request["code_sha"], "request_digest": context.request["digest"]}
    if valid:
        reference = _identity("walletreadinesssource:sha256:", metadata)
        raw = build_raw_evidence_reference(source_system="POLYGON_RPC", endpoint=request.method, retrieval_method="POST/read-only-RPC", content_sha256=body_hash, byte_length=len(content), media_type="application/json", pit=build_pit_timestamps(local_first_seen_time=context.completed_at, ingestion_time=context.completed_at), dq_flags=("OK",), replay_fidelity="EXACT", raw_snapshot_ref=reference, request_parameters={"request": _identity("rpc:", asdict(request))})
        manifest = build_research_provenance_manifest(repo_code_identity=context.request["code_sha"], information_cutoff=context.completed_at, input_evidence_reference_ids=(raw.raw_evidence_reference_id,), input_content_hashes=(raw.content_sha256,), output_identity=reference, output_hash=body_hash, request_source_version_refs=(context.request["digest"], READINESS_POLICY_ID))
        metadata.update(raw_reference=asdict(raw), provenance_manifest=asdict(manifest))
    _retain(context.directory, name + (".raw" if valid else ".quarantine.raw"), content)
    _retain(context.directory, name + ".json", C.wallet_canonical_json_bytes(metadata))


def _run_readiness(request, output_dir, transport=None, *, approval=None, permit=None):
    checked = _readiness_request(request)
    production = transport is None
    _require(not production or permit is not None, "PRODUCTION_DISABLED")
    if permit is not None:
        _require(type(permit) is _ReadinessPermit and permit.issuer is _CONSOLE_PERMIT and permit.active and permit.request_digest == checked["digest"] and permit.approval_id == _readiness_approval(checked, approval), "APPROVAL_INVALID")
        permit.active = False
    if production:
        _readiness_approval(checked, approval)
        _readiness_checkout(checked)
    _require(production or type(transport) is SyntheticTransport and type(transport.frames) is tuple and len(transport.frames) == 8 and transport.evidence is None, "REQUEST_DENIED")
    _readiness_window(checked)
    directory = _readiness_path(checked, output_dir)
    approval_record = approval if production else {"kind": "SYNTHETIC_ONLY_NO_OPERATOR_APPROVAL", "request_digest": checked["digest"]}
    approval_id = _identity("walletreadinessapproval:sha256:", approval_record)
    claim = {"request_digest": checked["digest"], "approval_id": approval_id, "code_sha": checked["code_sha"], "kind": "NON_STUDY_READINESS"}
    with (directory / "run.claim").open("xb") as stream:
        stream.write(C.wallet_canonical_json_bytes(claim))
    _retain(directory, "request.json", C.wallet_canonical_json_bytes(checked))
    _retain(directory, "approval.json", C.wallet_canonical_json_bytes(approval_record))
    context = _ReadinessRun(checked, directory, production, permit)
    frontier = {}
    observations = {"venue_source": "NOT_ESTABLISHED", "current_period_logs": "NOT_ESTABLISHED", "coverage": "NOT_ESTABLISHED"}
    errors = ()
    retention_failed = False
    for index in range(8):
        planned = _readiness_plan(index, frontier)
        valid = False
        attempted = False
        try:
            context.begin_call()
            attempted = True
            maximum = min(2097152, checked["budget"]["bytes"] - context.received_bytes)
            if production:
                try:
                    _rpc_post(planned, maximum, min(checked["budget"]["timeout_seconds"], context.remaining_seconds()), context=context)
                finally:
                    context.completed_at = _utc_text(_utc_now())
            else:
                source = transport.frames[index]
                _require(type(source) is SourceFrame and source.origin == "SYNTHETIC" and source.code_sha == checked["code_sha"] and source.request == planned, "SOURCE_INVALID")
                _require(type(source.body) is bytes, "SOURCE_INVALID")
                context.started_at = source.started_at or source.observed_at
                context.completed_at = source.observed_at
                context.synthetic_elapsed = max(context.synthetic_elapsed, (_stamp(source.observed_at) - _stamp(checked["not_before"])).total_seconds())
                context.body = source.body[:maximum + 1]
                context.received_bytes += len(context.body)
                context.http_status = 200
            _require(len(context.body) <= maximum and context.received_bytes <= checked["budget"]["bytes"], "LIMIT_INVALID")
            context.check_completion()
            value = _source_body(context.body)
            _readiness_observe(index, value, context.completed_at, frontier, observations)
            valid = True
        except KeyboardInterrupt:
            errors = ("OPERATOR_CANCELLED",)
        except SeedError as error:
            errors = (str(error) if str(error) in READINESS_ERRORS else "FIELD_INVALID",)
        except Exception:
            errors = ("FIELD_INVALID",)
        finally:
            if attempted:
                context.completed_at = context.completed_at or _utc_text(_utc_now())
                try:
                    _readiness_packet(context, planned, valid)
                except Exception:
                    errors = ("PATH_INVALID",)
                    retention_failed = True
        if errors:
            break
    context.active = False
    if not errors:
        try:
            _readiness_window(checked)
            _require(context.remaining_seconds() > 0, "LIMIT_INVALID")
            completed_at = _utc_text(_utc_now()) if production else context.completed_at
            age = (_stamp(completed_at) - datetime.fromtimestamp(_quantity(frontier["timestamp"]), timezone.utc)).total_seconds()
            _require(0 <= age <= 300, "FINALITY_INVALID")
            observations["finalized_age_seconds"] = format(age, ".6f")
        except SeedError as error:
            errors = (str(error),)
    status = "READINESS_INCONCLUSIVE" if errors else "OBSERVED_ROUTE_COMPATIBLE_PENDING_REVIEW" if production else "SYNTHETIC_READINESS_OBSERVED"
    result = ReadinessResult(status, errors=errors, request_digest=checked["digest"], origin="DIRECT_HTTPS_NON_STUDY_PENDING_REVIEW" if production else "SYNTHETIC", observations=observations, accounting=context.accounting())
    receipt = asdict(result)
    receipt.pop("receipt_id")
    receipt.update(approval_id=approval_id, code_sha=checked["code_sha"], approved_budget=checked["budget"], source_policy_id=READINESS_POLICY_ID)
    receipt_id = _identity("walletreadinesscapture:sha256:", receipt)
    if not retention_failed:
        try:
            _retain(directory, "receipt.json", C.wallet_canonical_json_bytes({"receipt_id": receipt_id, **receipt}))
            object.__setattr__(result, "receipt_id", receipt_id)
        except Exception:
            object.__setattr__(result, "status", "READINESS_INCONCLUSIVE")
            object.__setattr__(result, "errors", ("PATH_INVALID",))
    if production:
        object.__setattr__(result, "_direct_capture", _DIRECT_RESULT)
        object.__setattr__(result, "_commitment", _identity("readinessresult:", asdict(result)))
    return result


@_readiness_public
def capture_readiness(*, request, output_dir, transport=None):
    _require(type(transport) is SyntheticTransport, "PRODUCTION_DISABLED")
    return _run_readiness(request, output_dir, transport)


def _readiness_approval(request, approval):
    _closed(approval, ("kind", "request_digest", "planned_operator", "external_review_ref", "approved_at"))
    _scan_seed_output(approval)
    _require(approval["kind"] == "MANUAL_EXTERNAL_APPROVAL_REFERENCE" and approval["request_digest"] == request["digest"] and approval["planned_operator"] == "KARL", "APPROVAL_INVALID")
    reference = approval["external_review_ref"]
    _require(type(reference) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", reference) is not None, "APPROVAL_INVALID")
    _require(canonicalize_utc_timestamp(approval["approved_at"]) == approval["approved_at"] and _stamp(approval["approved_at"]) <= _stamp(request["not_before"]) and _stamp(approval["approved_at"]) <= _utc_now(), "APPROVAL_INVALID")
    return _identity("walletreadinessapproval:sha256:", approval)


def _readiness_checkout(request):
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True, timeout=5)
    clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--"], cwd=ROOT, capture_output=True, timeout=5)
    _require(head.stdout.strip() == request["code_sha"] and clean.returncode == 0, "VERSION_INVALID")


def _readiness_load(path):
    path = Path(path)
    _require(path.suffix == ".json" and not any(part.lower() in ("secrets", "credentials", "keys") or part.lower().startswith(".env") for part in path.parts), "PATH_INVALID")
    _require(path.is_file() and not any(part.is_symlink() for part in (path, *path.parents)), "PATH_INVALID")
    with path.open("rb") as stream:
        body = stream.read(32769)
    _require(len(body) <= 32768, "FIELD_INVALID")
    return _rpc_document(body)


def _readiness_console(request, approval):
    _require(sys.stdin.isatty() and sys.stderr.isatty() and sys.stdout.isatty(), "APPROVAL_INVALID")
    approval_id = _readiness_approval(request, approval)
    _readiness_window(request)
    _readiness_checkout(request)
    scope = {key: value for key, value in request.items() if key != "digest"}
    scope.update(request_digest=request["digest"], approval_id=approval_id, endpoint=f"https://{RPC_HOST}/", calls=8, operator_approval="MANUAL_ASSERTION_REQUIRES_EXTERNAL_REVIEW", human_identity="NOT_MACHINE_ATTESTED")
    print(json.dumps(scope, sort_keys=True), file=sys.stderr)
    challenge = secrets.token_hex(16)
    print("AUTHORIZE NON_STUDY_READINESS " + request["digest"] + " " + approval_id + " CHALLENGE " + challenge, file=sys.stderr)
    answer = sys.stdin.readline(512)
    _require(answer == "AUTHORIZE NON_STUDY_READINESS " + request["digest"] + " " + approval_id + " " + challenge + "\n", "APPROVAL_INVALID")
    _readiness_window(request)
    _readiness_checkout(request)
    return _ReadinessPermit(request["digest"], approval_id, _CONSOLE_PERMIT)


class _ReadinessParser(argparse.ArgumentParser):
    def error(self, message):
        raise SeedError("ARGUMENT_INVALID")


def main(argv=None):
    try:
        parser = _ReadinessParser(description="Default-off wallet seed; non-study operator readiness is separately reviewed.", allow_abbrev=False)
        parser.add_argument("--status", action="store_true")
        parser.add_argument("--readiness-request")
        parser.add_argument("--approval-record")
        args = parser.parse_args(argv)
        if args.readiness_request is None and args.approval_record is None:
            print(json.dumps(result_to_mapping(SeedResult("PRODUCTION_DISABLED")), sort_keys=True))
            return 0
        _require(not args.status and args.readiness_request is not None and args.approval_record is not None, "ARGUMENT_INVALID")
        _require(sys.stdin.isatty() and sys.stderr.isatty() and sys.stdout.isatty(), "APPROVAL_INVALID")
        request = _readiness_request(_readiness_load(args.readiness_request))
        approval = _readiness_load(args.approval_record)
        permit = _readiness_console(request, approval)
        result = _run_readiness(request, request["output_dir"], approval=approval, permit=permit)
    except KeyboardInterrupt:
        result = ReadinessResult("DENIED", errors=("OPERATOR_CANCELLED",))
    except SeedError as error:
        result = ReadinessResult("DENIED", errors=(str(error) if str(error) in READINESS_ERRORS else "FIELD_INVALID",))
    except Exception:
        result = ReadinessResult("DENIED", errors=("FIELD_INVALID",))
    print(json.dumps(readiness_result_to_mapping(result=result), sort_keys=True))
    return 0 if result.status == "OBSERVED_ROUTE_COMPATIBLE_PENDING_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
