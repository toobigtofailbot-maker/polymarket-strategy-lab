"""Synthetic original-response integration tests; no production transport."""
from copy import deepcopy
from dataclasses import asdict, fields, replace
from datetime import timedelta
from hashlib import sha256
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace
import urllib.error

import pytest

from tools.polymarket import wallet_seed as s

CODE = "a" * 40
WALLET = "0x" + "1" * 40
CONDITION = "0x" + "ab" * 32
T0 = "2026-01-11T00:00:00Z"
READY = "2026-01-08T20:00:00Z"
TX = "0x" + "c" * 64
H2, H3 = "0x" + "b" * 64, "0x" + "d" * 64


def frame(name, method, params, result, seen=T0, url=None):
    document = result if url else {"jsonrpc": "2.0", "id": 1, "result": result}
    return s.SourceFrame(s.Request(name, method, params, url), s.C.wallet_canonical_json_bytes(document), seen, CODE)


def change(frame_value, result):
    document = result if frame_value.request.url else {"jsonrpc": "2.0", "id": 1, "result": result}
    return replace(frame_value, body=s.C.wallet_canonical_json_bytes(document))


def word(value):
    return format(value, "064x")


def route(seen=T0):
    return {
        "chain": frame("chain", "eth_chainId", (), "0x89", seen),
        "finalized": frame("finalized", "eth_getBlockByNumber", ("finalized", False), {"number": "0x3", "hash": H3, "timestamp": hex(int(s._stamp(seen).timestamp()))}, seen),
        "exchange_code": frame("exchange_code", "eth_getCode", (s.EXCHANGE, "0x3"), "0x6001", seen),
        "ctf_code": frame("ctf_code", "eth_getCode", (s.CTF, "0x3"), "0x6002", seen),
    }


def instrument(seen=T0):
    def call(name, contract, data, result):
        return frame(name, "eth_call", ({"to": contract, "data": data}, "0x3"), "0x" + result, seen)
    mapping = {
        "slots": call("slots", s.CTF, "0xd42dc0c2" + CONDITION[2:], word(2)),
        "collateral": call("collateral", s.EXCHANGE, "0x03cee3df", "0" * 24 + s.COLLATERAL[2:]),
    }
    for index in (1, 2):
        mapping[f"collection_{index}"] = call(f"collection_{index}", s.CTF, "0x856296f7" + "0" * 64 + CONDITION[2:] + word(index), word(index))
        mapping[f"position_{index}"] = call(f"position_{index}", s.CTF, "0x39dd7530" + "0" * 24 + s.COLLATERAL[2:] + word(index), word(index + 6))
    return {"condition_id": CONDITION, "target_token_id": "7", "complement_token_id": "8", "gamma_market_id": "17",
        "rule_snapshot_digest": "rule:sha256:" + "f" * 64, "event_id": "event01", "leakage_group_id": "group01", "wallets": (WALLET,), "mapping": mapping}


def logs(side=0, token=7, seen=T0):
    amounts = (6000000, 10000000) if side == 0 else (10000000, 6000000)
    log = {"address": s.EXCHANGE, "topics": [s.TOPIC, "0x" + "e" * 64, "0x" + "0" * 24 + WALLET[2:], "0x" + "0" * 24 + s.EXCHANGE[2:]],
        "data": "0x" + "".join(word(x) for x in (side, token, *amounts, 0, 0, 0)), "transactionHash": TX,
        "blockHash": H2, "blockNumber": "0x2", "transactionIndex": "0x0", "logIndex": "0x0", "removed": False}
    filters = {"address": s.EXCHANGE, "fromBlock": "0x2", "toBlock": "0x3", "topics": [s.TOPIC, None, "0x" + "0" * 24 + WALLET[2:]]}
    return frame("logs", "eth_getLogs", (filters,), [log], seen), log


def coverage(side=0, token=7, empty=False):
    raw, log = logs(side, token)
    start = int((s._stamp(T0) - timedelta(hours=1)).timestamp())
    block2 = {"number": "0x2", "hash": H2, "parentHash": "0x" + "0" * 64, "timestamp": hex(start), "transactions": [] if empty else [TX]}
    block3 = {"number": "0x3", "hash": H3, "parentHash": H2, "timestamp": hex(int(s._stamp(T0).timestamp())), "transactions": []}
    predecessor = {"number": "0x1", "hash": "0x" + "0" * 64, "parentHash": "0x" + "0" * 64, "timestamp": hex(start - 2)}
    receipt = {"transactionHash": TX, "blockHash": H2, "blockNumber": "0x2", "transactionIndex": "0x0", "status": "0x1", "logs": [log]}
    return {"blocks": (frame("block2", "eth_getBlockByNumber", ("0x2", True), block2), frame("block3", "eth_getBlockByNumber", ("0x3", True), block3), frame("predecessor", "eth_getBlockByNumber", ("0x1", False), predecessor)),
        "receipts": () if empty else (frame("receipt", "eth_getTransactionReceipt", (TX,), receipt),),
        "logs": (change(raw, []) if empty else raw,), "finality": route(), "start_block": 2, "end_block": 3}


def approve(seal, phase="DECISION"):
    seal = deepcopy(seal)
    seal["approval"] = {"kind": "SYNTHETIC_DETACHED", "approved_digest": seal["digest"], "method_digest": s.METHOD_DIGEST,
        "code_sha": CODE, "phase": phase, "hosts": (s.RPC_HOST, "clob.polymarket.com", "gamma-api.polymarket.com"),
        "budget": seal["payload"]["approved_source_call_byte_elapsed_limits"]}
    return seal


@pytest.fixture
def pins(monkeypatch):
    # Fixed deployed constants are checked before scoped synthetic bytecode pins.
    assert s.EXCHANGE_HASH == "3e2ba43e59d19191f0d208e39b1ec16f920bdda30ebfa062330ea9fe8d8363f5"
    assert s.CTF_HASH == "984de1496ba73cea948f777d72201b9418041dce65551bff0b4d62101d2acd62"
    monkeypatch.setattr(s, "EXCHANGE_HASH", sha256(bytes.fromhex("6001")).hexdigest())
    monkeypatch.setattr(s, "CTF_HASH", sha256(bytes.fromhex("6002")).hexdigest())


def native_setup(tmp_path, pins):
    path = tmp_path / "wallet.sqlite3"
    assert s.L.initialize_wallet_evidence_ledger(path).is_valid
    raw = s._raw(route(READY)["chain"])
    manifest = s.build_research_provenance_manifest(repo_code_identity=CODE, information_cutoff=READY,
        input_evidence_reference_ids=(raw.raw_evidence_reference_id,), input_content_hashes=(raw.content_sha256,), output_identity="synthetic-readiness", output_hash=raw.content_sha256)
    assert s.L.append_wallet_evidence_records(path, (raw, manifest)).is_valid
    member = s.P.WalletDiscoveryCohortMember(WALLET, "CANDIDATE", "manual-operational-feasibility", (raw.raw_evidence_reference_id,),
        (manifest.research_provenance_manifest_id,), s.ObservabilityEvidence(local_first_seen_time=READY))
    def cohort(start, end):
        return s.P.build_wallet_discovery_cohort_snapshot(discovery_cutoff=READY, evaluation_start=start, evaluation_end=end,
            discovery_method="CALLER_SUPPLIED_PIT_SET", selection_policy_id="manual-source-feasibility", selection_policy_version="1", members=(member,), provenance_manifests=(manifest,))
    ready_cohort = cohort(READY, "2026-01-08T21:00:00Z")
    future_cohort = cohort("2026-01-10T23:00:00Z", "2026-01-11T00:00:00.000001Z")
    contexts = tuple(s.P.build_wallet_profile_market_context(condition_context="DATA_API_RESPONSE_CONDITION_ID", condition_value=CONDITION,
        token_context="CLOB_TOKEN_ID", token_value=str(token), instrument_class="STANDARD_BINARY_OUTCOME",
        metadata_observability=s.ObservabilityEvidence(local_first_seen_time=READY), metadata_dq_flags=("OK",), metadata_replay_fidelity="EXACT",
        category_label="synthetic", mechanism_label="binary", horizon_label="one-day", independence_group_id="group01",
        research_provenance_manifest_ids=(manifest.research_provenance_manifest_id,)) for token in (7, 8))
    ready_profile = s.P.build_wallet_profile_snapshot(wallet_ledger_path=path, cohort_snapshot=ready_cohort,
        target_wallet=WALLET, as_of="2026-01-08T21:00:00Z", market_contexts=contexts)
    readiness = {"route": route(READY), "ledger_path": path, "ledger_head": ready_profile.wallet_ledger_head_hash,
        "cohort": ready_cohort, "contexts": contexts, "identity_observability": {}, "discovery_references": (raw.raw_evidence_reference_id,)}
    protocol = (s.ROOT / "docs/wallet_incrementality_prospective_seed_protocol.md").read_text(encoding="utf-8")
    method = json.loads(protocol.split("```json\n", 1)[1].split("```", 1)[0])["method"]
    args = dict(method=method, readiness=readiness, cohort=future_cohort, profile=ready_profile, instrument=instrument(READY),
        clocks={"freeze_time": "2026-01-09T00:00:00Z", "decision_time": T0, "target_event_end": "2026-01-12T00:00:00Z", "label_deadline": "2026-02-11T00:00:00Z"},
        budget=dict(s.LIMITS), human_approval={"request_id": "synthetic-request01", "requested_scope": "ONE_UNIT_STUDY", "planned_approver": "Karl"})
    result = s.build_study_seal(**args)
    assert result.status == "SYNTHETIC_SEAL_UNAPPROVED", result
    return path, args, approve(result.payload), future_cohort, contexts


def prepared(tmp_path, pins, side=0, token=7, empty=False, second_book=False, opposing=False):
    path, args, seal, cohort, contexts = native_setup(tmp_path, pins)
    data = coverage(side, token, empty)
    if opposing:
        original = s._frame(data["logs"][0]); another = deepcopy(original[0])
        another["logIndex"] = "0x1"
        another["data"] = "0x" + word(0) + word(8) + "".join(word(x) for x in (6000000, 10000000, 0, 0, 0))
        data["logs"] = (change(data["logs"][0], original + [another]),)
        receipt = s._frame(data["receipts"][0]); receipt["logs"] += [another]
        data["receipts"] = (change(data["receipts"][0], receipt),)
    inst = instrument()
    book = frame("book", "GET", (), {"market": CONDITION, "asset_id": "7", "bids": [{"price": "0.55", "size": "10"}], "asks": [{"price": "0.65", "size": "10"}], "neg_risk": False}, url="https://clob.polymarket.com/book?token_id=7")
    books = (book,)
    if second_book:
        other = s._frame(book); other["asks"][0]["size"] = "11"
        books += (replace(change(book, other), request=replace(book.request, name="book_other")),)
    frames = tuple(data["finality"].values()) + tuple(inst["mapping"].values()) + data["blocks"] + data["receipts"] + data["logs"] + books
    captured = s.capture_seed_evidence(seal=seal, phase="DECISION", ledger_path=path, output_dir=tmp_path,
        transport=s.SyntheticTransport(frames, {"instrument": inst, "coverage": data}))
    assert captured.status == "SYNTHETIC_CAPTURE_RETAINED", captured
    profile = s.P.build_wallet_profile_snapshot(wallet_ledger_path=path, cohort_snapshot=cohort, target_wallet=WALLET, as_of=T0, market_contexts=contexts)
    bundle = {"instrument": inst, "coverage": data, "ledger_head": profile.wallet_ledger_head_hash, "cohort": cohort,
        "profile": profile, "contexts": contexts, "identity_observability": {}, "books": books, "committed_at": s.SyntheticDecisionClock(T0)}
    return path, seal, bundle, frames


def test_verified_route_and_decode(pins):
    assert s.validate_source_route(route_evidence=route()).status == "VERIFIED_SYNTHETIC_ROUTE"
    wrong = route(); wrong["exchange_code"] = change(wrong["exchange_code"], "0x6003")
    assert s.validate_source_route(route_evidence=wrong).errors == ("VERSION_INVALID",)
    for side, token in ((0, 7), (0, 8), (1, 7), (1, 8)):
        data = coverage(side, token)
        finality = {"route": data["finality"], "canonical": data["blocks"][0], "cutoff": T0}
        result = s.decode_fill(raw_log=data["logs"][0], receipt=data["receipts"][0], block=data["blocks"][0], finality=finality, instrument=instrument())
        assert result.status == "DECODED_SYNTHETIC_FILL", result
        assert result.payload["event"]["canonical_wallet"] == WALLET
        assert result.payload["event"]["side"] == ("BUY" if side == 0 else "SELL")
        assert result.payload["event"]["token_value"] == str(token)
        for mutation in ("emitter", "topic", "width", "padding", "removed", "identity"):
            frame_value = data["logs"][0]; log = deepcopy(s._frame(frame_value)[0])
            if mutation == "emitter": log["address"] = s.CTF
            if mutation == "topic": log["topics"][0] = "0x" + "0" * 64
            if mutation == "width": log["data"] = log["data"][:-2]
            if mutation == "padding": log["topics"][2] = "0x" + "1" * 64
            if mutation == "removed": log["removed"] = True
            if mutation == "identity": log["transactionHash"] = "0x" + "2" * 64
            assert s.decode_fill(raw_log=change(frame_value, [log]), receipt=data["receipts"][0], block=data["blocks"][0], finality=finality, instrument=instrument()).status == "INVALID"


def test_original_chain_intake(tmp_path, pins):
    path, seal, bundle, _ = prepared(tmp_path, pins)
    loaded = s.L.load_and_verify_wallet_evidence_ledger(path)
    events = [r.payload for r in loaded.snapshot.entries if r.record_kind == "WALLET_EVIDENCE_EVENT"]
    assert len(events) == 1 and events[0]["identity_strength"] == "CHAIN_NATIVE_STRONG"
    assert events[0]["source_system_family"] == "POLYGON_RPC"
    assert bundle["profile"].included_wallet_event_ids == (events[0]["wallet_event_id"],)
    data = deepcopy(bundle["coverage"])
    broken = s._frame(data["receipts"][0]); broken["status"] = "0x0"
    data["receipts"] = (change(data["receipts"][0], broken),)
    result = s.materialize_forecast_pair(seal=seal, decision_bundle={**bundle, "coverage": data}, ledger_path=path)
    assert result.status == "UNKNOWN" and result.errors == ("FINALITY_INVALID",)
    data = deepcopy(bundle["coverage"]); data["logs"] = (replace(data["logs"][0], observed_at="2026-01-11T00:00:01Z"),)
    assert s.materialize_forecast_pair(seal=seal, decision_bundle={**bundle, "coverage": data}, ledger_path=path).status == "UNKNOWN"
    assert s.decode_fill(raw_log={"origin": "REAL_DIRECT_HTTPS"}, receipt={}, block={}, finality={}, instrument=instrument()).status == "INVALID"


def test_native_book_and_profile_admission(tmp_path, pins):
    path, seal, bundle, _ = prepared(tmp_path, pins)
    result = s.materialize_forecast_pair(seal=seal, decision_bundle=bundle, ledger_path=path)
    assert result.status == "PENDING" and result.payload["p_nonwallet"] == "0.6", result
    book = bundle["books"][0]; document = s._frame(book); document["bids"][0]["price"] = "0.54"
    tampered = {**bundle, "books": (change(book, document),)}
    assert s.materialize_forecast_pair(seal=seal, decision_bundle=tampered, ledger_path=path).status == "UNKNOWN"
    assert s.materialize_forecast_pair(seal=seal, decision_bundle={**bundle, "profile": replace(bundle["profile"], evidence_window_start=T0)}, ledger_path=path).status == "UNKNOWN"
    assert s.materialize_forecast_pair(seal=seal, decision_bundle={**bundle, "books": ()}, ledger_path=path).status == "UNKNOWN"
    assert s.materialize_forecast_pair(seal=seal, decision_bundle={**bundle, "committed_at": None}, ledger_path=path).status == "UNMATCHED"
    assert s.materialize_forecast_pair(seal=seal, decision_bundle={**bundle, "committed_at": T0}, ledger_path=path).status == "UNMATCHED"


def test_prospective_seal_and_coverage(tmp_path, pins):
    path, args, seal, _, _ = native_setup(tmp_path, pins)
    expected = "walletstudy:sha256:" + sha256(json.dumps(seal["payload"], sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    assert expected == seal["digest"] and "approved_digest" not in seal["payload"]["human_approval_record"]
    bad = {**args, "human_approval": {**args["human_approval"], "approved_digest": expected}}
    assert s.build_study_seal(**bad).status == "INVALID"
    bad = {**args, "clocks": {**args["clocks"], "freeze_time": T0}}
    assert s.build_study_seal(**bad).errors == ("FREEZE_INVALID",)
    assert s.capture_seed_evidence(seal=seal, phase="READINESS", ledger_path=path, output_dir=tmp_path, transport=s.SyntheticTransport((route()["chain"],))).errors == ("FIELD_INVALID",)
    unapproved = deepcopy(seal); unapproved["approval"] = None
    assert s.capture_seed_evidence(seal=unapproved, phase="DECISION", ledger_path=path, output_dir=tmp_path, transport=s.SyntheticTransport((route()["chain"],))).status == "INVALID"
    other = tmp_path / "empty"; other.mkdir()
    path, seal, bundle, _ = prepared(other, pins, empty=True)
    result = s.materialize_forecast_pair(seal=seal, decision_bundle=bundle, ledger_path=path)
    assert result.status == "PENDING" and result.payload["vote"] is None and result.payload["p_wallet_added"] == result.payload["p_nonwallet"]
    partial = deepcopy(bundle["coverage"]); partial["blocks"] = partial["blocks"][:1]
    assert s.materialize_forecast_pair(seal=seal, decision_bundle={**bundle, "coverage": partial}, ledger_path=path).errors == ("COVERAGE_UNKNOWN",)
    realistic = tmp_path / "r004-realistic"; realistic.mkdir()
    rp, rs, rb, rf, capture = realistic_prepared(realistic, pins)
    assert capture.payload["coverage"]["covered_block_count"] == 1771 and capture.payload["calls"] == len(rf) < 128
    assert s.materialize_forecast_pair(seal=rs, decision_bundle=rb, ledger_path=rp).status == "PENDING"


def label_bundle(inst, seen="2026-01-12T00:00:01Z", target=1, denominator=1, resolved=True):
    inst = instrument(seen)
    values = (denominator, target, denominator - target)
    result = {"instrument": inst, "route": route(seen)}
    for key, selector, value in zip(("denominator", "target_numerator", "complement_numerator"), ("0xdd34de67", "0x0504c814", "0x0504c814"), values):
        data = selector + CONDITION[2:] + ("" if key == "denominator" else word(0 if key == "target_numerator" else 1))
        result[key] = frame(key, "eth_call", ({"to": s.CTF, "data": data}, "0x3"), "0x" + word(value), seen)
    result["venue"] = frame("venue", "GET", (), {"id": "17", "conditionId": CONDITION, "umaResolutionStatus": "resolved" if resolved else "proposed", "closed": True,
        "negRisk": False, "clobTokenIds": '["7","8"]', "outcomePrices": '["1","0"]' if target else '["0","1"]'}, seen, url="https://gamma-api.polymarket.com/markets/17")
    return result


def test_paired_forecast_label_and_conservation(tmp_path, pins):
    for token, expected, delta in ((7, "0.64", "0.0304"), (8, "0.54", "-0.0516")):
        directory = tmp_path / str(token); directory.mkdir()
        path, seal, bundle, _ = prepared(directory, pins, token=token)
        pair = s.materialize_forecast_pair(seal=seal, decision_bundle=bundle, ledger_path=path)
        assert pair.payload["p_wallet_added"] == expected and pair.payload["p_masked"] == "0.6", pair
        result = s.attach_final_label(pair=pair, label_bundle=label_bundle(bundle["instrument"]), as_of="2026-01-12T00:00:02Z")
        assert result.status == "MATCHED" and result.payload["delta"] == delta, result
        assert sum(result.payload["synthetic_counts"].values()) == 1 and result.payload["enrolled_count"] == "NOT_ESTABLISHED"
        assert not result.study_activated and result.origin == "SYNTHETIC"
        invalid = label_bundle(bundle["instrument"], target=1, denominator=2)
        assert s.attach_final_label(pair=pair, label_bundle=invalid, as_of="2026-01-12T00:00:02Z").status == "UNKNOWN"
        early = label_bundle(bundle["instrument"], seen="2026-01-12T00:00:00Z")
        assert s.attach_final_label(pair=pair, label_bundle=early, as_of="2026-01-12T00:00:02Z").status == "UNKNOWN"
        pending = label_bundle(bundle["instrument"], target=0, denominator=0, resolved=False)
        assert s.attach_final_label(pair=pair, label_bundle=pending, as_of="2026-01-12T00:00:02Z").status == "PENDING"
        assert s.attach_final_label(pair=pair, label_bundle=pending, as_of="2026-02-12T00:00:00Z").status == "CENSORED"


def test_transport_activation_and_restart(tmp_path, pins, monkeypatch):
    path, seal, bundle, frames = prepared(tmp_path, pins)
    def forbidden(*args, **kwargs):
        pytest.fail("production transport was invoked")
    monkeypatch.setattr(s.urllib.request, "build_opener", forbidden)
    monkeypatch.setattr(s, "public_get", forbidden)
    assert s.capture_seed_evidence(seal=seal, phase="DECISION", ledger_path=path, output_dir=tmp_path).errors == ("PRODUCTION_DISABLED",)
    real = deepcopy(seal); real["approval"]["kind"] = "REAL_DIRECT_HTTPS"
    assert s.capture_seed_evidence(seal=real, phase="DECISION", ledger_path=path, output_dir=tmp_path, transport=s.SyntheticTransport(frames)).errors == ("APPROVAL_INVALID",)
    old_head = s.L.load_and_verify_wallet_evidence_ledger(path).snapshot.head_hash
    again = s.capture_seed_evidence(seal=seal, phase="DECISION", ledger_path=path, output_dir=tmp_path, transport=s.SyntheticTransport(frames, {"instrument": bundle["instrument"], "coverage": bundle["coverage"]}))
    assert again.status == "SYNTHETIC_CAPTURE_RETAINED" and s.L.load_and_verify_wallet_evidence_ledger(path).snapshot.head_hash == old_head
    malicious = replace(frames[-1], request=s.Request("private", "GET", (), "https://clob.polymarket.com/orders"))
    assert s.capture_seed_evidence(seal=seal, phase="DECISION", ledger_path=path, output_dir=tmp_path, transport=s.SyntheticTransport((malicious,))).errors == ("REQUEST_DENIED",)
    limited = deepcopy(seal); limited["payload"]["approved_source_call_byte_elapsed_limits"]["bytes"] = 1
    limited["digest"] = s._identity("walletstudy:sha256:", limited["payload"]); limited = approve(limited)
    assert s.capture_seed_evidence(seal=limited, phase="DECISION", ledger_path=path, output_dir=tmp_path, transport=s.SyntheticTransport(frames)).errors == ("LIMIT_INVALID",)
    new = frame("later", "eth_chainId", (), "0x89", seen="2026-01-11T00:00:01Z")
    raw = s._raw(new); assert s.L.append_wallet_evidence_records(path, (raw,)).is_valid
    assert s.materialize_forecast_pair(seal=seal, decision_bundle=bundle, ledger_path=path).errors == ("LEDGER_INVALID",)
    assert s.main(["--status"]) == 0


def test_safe_output_and_scope():
    result = s.SeedResult("PRODUCTION_DISABLED")
    assert {f.name for f in fields(result)} == set(s.result_to_mapping(result)) == s.RESULT_FIELDS
    for field_name in ("status", "payload", "errors", "origin"):
        injected = replace(result, **{field_name: {"nested": "buy/sell recommendation"} if field_name == "payload" else ("buy/sell recommendation",) if field_name == "errors" else "buy/sell recommendation"})
        with pytest.raises(s.SeedError, match="OUTPUT_UNSAFE"):
            s.result_to_mapping(injected)
    bad = s.validate_source_route(route_evidence={"secret-sentinel-never-echo": "secret-sentinel-never-echo"})
    assert "secret-sentinel" not in json.dumps(s.result_to_mapping(bad))
    spec = json.loads((s.ROOT / "docs/wp_specs/S10-WALLET-SEED-02/wp_spec.json").read_text(encoding="utf-8"))
    assert spec["scope"]["required_changed_files"] == spec["scope"]["allowed_changed_files"] and len(spec["scope"]["required_changed_files"]) == 9
    assert spec["authority"]["network"] and not spec["authority"]["source_runtime"]
    assert spec["identity"]["risk_level"] == 3 and spec["successor_boundary"]["separately_gated"]


@pytest.mark.parametrize("fault", ("chain", "code_block", "finality_hash", "missing_receipt", "hidden_fill", "duplicate", "tail", "code_revision", "json_id", "future_clock"))
def test_source_negative_matrix(tmp_path, pins, fault):
    path, seal, bundle, _ = prepared(tmp_path, pins)
    data = deepcopy(bundle["coverage"])
    if fault == "chain": data["finality"]["chain"] = change(data["finality"]["chain"], "0x1")
    if fault == "code_block": data["finality"]["ctf_code"] = replace(data["finality"]["ctf_code"], request=s.Request("ctf_code", "eth_getCode", (s.CTF, "0x2")))
    if fault == "finality_hash": data["finality"]["finalized"] = change(data["finality"]["finalized"], {"number": "0x3", "hash": "0x" + "1" * 64})
    if fault == "missing_receipt": data["receipts"] = ()
    if fault == "hidden_fill": data["logs"] = (change(data["logs"][0], []),)
    if fault == "duplicate": data["logs"] = data["logs"] * 2
    if fault == "tail": data["blocks"] = (data["blocks"][0],)
    if fault == "code_revision": data["receipts"] = (replace(data["receipts"][0], code_sha="b" * 40),)
    if fault == "json_id": data["logs"] = (replace(data["logs"][0], body=b'{"jsonrpc":"2.0","id":2,"result":[]}'),)
    if fault == "future_clock": data["finality"]["finalized"] = replace(data["finality"]["finalized"], observed_at="2026-01-11T00:00:01Z")
    result = s.materialize_forecast_pair(seal=seal, decision_bundle={**bundle, "coverage": data}, ledger_path=path)
    assert result.status in ("UNKNOWN", "EXCLUDED") and result.payload.get("p_wallet_added") is None
    assert sum(result.payload["synthetic_counts"].values()) == 1


def test_replacement_and_pair_rehash_rejected(tmp_path, pins):
    path, seal, bundle, frames = prepared(tmp_path, pins)
    old_head = s.L.load_and_verify_wallet_evidence_ledger(path).snapshot.head_hash
    replacement = deepcopy(seal); replacement["payload"]["event_id"] = "replacement01"
    replacement["digest"] = s._identity("walletstudy:sha256:", replacement["payload"]); replacement = approve(replacement)
    result = s.capture_seed_evidence(seal=replacement, phase="DECISION", ledger_path=path, output_dir=tmp_path, transport=s.SyntheticTransport(frames))
    assert result.errors == ("REPLAY_CONFLICT",) and s.L.load_and_verify_wallet_evidence_ledger(path).snapshot.head_hash == old_head
    pair = s.materialize_forecast_pair(seal=seal, decision_bundle=bundle, ledger_path=path)
    original = deepcopy(pair.payload); original["p_wallet_added"] = "0.99"; original.pop("pair_id")
    original["pair_id"] = s._identity("walletseedpair:sha256:", original)
    forged = s.SeedResult("PENDING", original)
    assert s.attach_final_label(pair=forged, label_bundle=label_bundle(bundle["instrument"]), as_of="2026-01-12T00:00:02Z").errors == ("PAIR_INVALID",)


def test_conflicting_books_and_unsafe_capture(tmp_path, pins):
    path, seal, bundle, frames = prepared(tmp_path, pins, second_book=True)
    assert s.materialize_forecast_pair(seal=seal, decision_bundle=bundle, ledger_path=path).status == "UNKNOWN"
    old_head = s.L.load_and_verify_wallet_evidence_ledger(path).snapshot.head_hash
    bad = replace(frames[0], request=replace(frames[0].request, name="place_order"))
    assert s.capture_seed_evidence(seal=seal, phase="DECISION", ledger_path=path, output_dir=tmp_path, transport=s.SyntheticTransport((bad,))).errors == ("REQUEST_DENIED",)
    assert s.L.load_and_verify_wallet_evidence_ledger(path).snapshot.head_hash == old_head
    with pytest.raises(s.SeedError):
        s.result_to_mapping(s.SeedResult("PENDING", origin="REAL_DIRECT_HTTPS", study_activated=True))


def test_rpc_runtime_size_and_strict_numbers(pins):
    large = s.SourceFrame(s.Request("runtime", "eth_getCode", (s.EXCHANGE, "0x3")), json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0x" + "60" * 21037}).encode(), T0, CODE)
    assert len(s._hex(s._frame(large))) == 21037
    for body in (b'{"jsonrpc":"2.0","id":1,"result":0.5}', b'{"jsonrpc":"2.0","id":1,"result":NaN}', b'{"jsonrpc":"2.0","id":1,"id":1,"result":"0x89"}'):
        with pytest.raises(s.SeedError): s._frame(replace(large, body=body))


def test_opposing_votes_keep_one_unknown_group(tmp_path, pins):
    path, seal, bundle, _ = prepared(tmp_path, pins, opposing=True)
    result = s.materialize_forecast_pair(seal=seal, decision_bundle=bundle, ledger_path=path)
    assert result.status == "UNKNOWN" and result.payload["p_wallet_added"] is None
    assert sum(result.payload["synthetic_counts"].values()) == 1
    data = bundle["coverage"]
    decoded = s.decode_fill(raw_log=(data["logs"][0], 1), receipt=data["receipts"][0], block=data["blocks"][0],
        finality={"route": data["finality"], "canonical": data["blocks"][0], "cutoff": T0}, instrument=bundle["instrument"])
    assert decoded.payload["event"]["token_value"] == "8" and decoded.payload["event"]["log_index"] == 1


@pytest.mark.parametrize("fault", ("mapping_code", "book_code", "membership", "context_group"))
def test_decision_bindings_rejected(tmp_path, pins, fault):
    path, seal, bundle, _ = prepared(tmp_path, pins)
    bundle = deepcopy(bundle)
    if fault == "mapping_code":
        bundle["instrument"]["mapping"]["slots"] = replace(bundle["instrument"]["mapping"]["slots"], code_sha="b" * 40)
    if fault == "book_code": bundle["books"] = (replace(bundle["books"][0], code_sha="b" * 40),)
    if fault == "membership":
        seal = deepcopy(seal)
        seal["payload"]["observation_group_missingness_policies"]["membership"] = ["0x" + "2" * 40]
        seal["digest"] = s._identity("walletstudy:sha256:", seal["payload"])
        seal = approve(seal)
    if fault == "context_group":
        bundle["contexts"] = tuple(replace(context, independence_group_id="other_group") for context in bundle["contexts"])
    assert s.materialize_forecast_pair(seal=seal, decision_bundle=bundle, ledger_path=path).status in ("UNKNOWN", "EXCLUDED")


@pytest.mark.parametrize("fault", ("old_finalized", "mapping_code", "payout_code", "venue_code", "wrong_prices", "unknown_status"))
def test_label_source_bindings_rejected(tmp_path, pins, fault):
    path, seal, bundle, _ = prepared(tmp_path, pins)
    pair = s.materialize_forecast_pair(seal=seal, decision_bundle=bundle, ledger_path=path)
    label = label_bundle(bundle["instrument"])
    if fault == "old_finalized":
        block = s._frame(label["route"]["finalized"])
        block["timestamp"] = hex(int(s._stamp(T0).timestamp()))
        label["route"]["finalized"] = change(label["route"]["finalized"], block)
    if fault == "mapping_code": label["instrument"]["mapping"]["slots"] = replace(label["instrument"]["mapping"]["slots"], code_sha="b" * 40)
    if fault == "payout_code": label["denominator"] = replace(label["denominator"], code_sha="b" * 40)
    if fault == "venue_code": label["venue"] = replace(label["venue"], code_sha="b" * 40)
    if fault in ("wrong_prices", "unknown_status"):
        venue = s._frame(label["venue"])
        if fault == "wrong_prices": venue["outcomePrices"] = '["0","1"]'
        else: venue["umaResolutionStatus"] = "unknown"
        label["venue"] = change(label["venue"], venue)
    assert s.attach_final_label(pair=pair, label_bundle=label, as_of="2026-01-12T00:00:02Z").status == "UNKNOWN"


def test_label_capture_preserves_gamma_source_and_receipt_refs(tmp_path, pins):
    path, seal, bundle, _ = prepared(tmp_path, pins)
    venue = label_bundle(bundle["instrument"])["venue"]
    result = s.capture_seed_evidence(seal=approve(seal, "LABEL"), phase="LABEL", ledger_path=path,
        output_dir=tmp_path, transport=s.SyntheticTransport((venue,)))
    assert result.status == "SYNTHETIC_CAPTURE_RETAINED", result
    raw = s._raw(venue)
    assert raw.source_system == "POLYMARKET_GAMMA" and raw.endpoint == "/markets/17"
    assert result.payload["raw_evidence_reference_ids"] == [raw.raw_evidence_reference_id]
    assert len(result.payload["research_provenance_manifest_ids"]) == 1
    assert result.payload["approved_budget"] == seal["payload"]["approved_source_call_byte_elapsed_limits"]
    payload = deepcopy(result.payload); identity = payload.pop("receipt_id")
    assert identity == s._identity("walletseedcapture:sha256:", payload)


def realistic_prepared(tmp_path, pins, empty=False, token=7, opposing=False, offset=0):
    """1771 finalized blocks, sparse original range replies and counted anchor search."""
    path, _, seal, cohort, contexts = native_setup(tmp_path, pins)
    t0 = s._stamp(T0); first, last, fill_number = 2, 1772, 352
    seen = lambda seconds: (t0 - timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")
    block_hash = lambda n: H2 if n == fill_number else H3 if n == last else "0x" + word(n)
    cache = {}
    def header(n):
        if n not in cache:
            cache[n] = frame("block_" + str(n), "eth_getBlockByNumber", (hex(n), False),
                {"number": hex(n), "hash": block_hash(n), "parentHash": block_hash(n - 1),
                 "transactions": ([TX] if n == fill_number and not empty else []) + ["0x" + "f" * 64],
                 "timestamp": hex(int((t0 - timedelta(hours=1) + timedelta(seconds=2 * (n - first) + offset)).timestamp()))}, seen(3))
        return cache[n]
    # Every binary-search request is a retained SourceFrame and counted in capture.
    low, high = 0, last
    while low < high:
        mid = (low + high) // 2
        if s._quantity(s._frame(header(mid))["timestamp"]) < int((t0 - timedelta(hours=1)).timestamp()): low = mid + 1
        else: high = mid
    assert low == first
    headers = (header(first), header(last), header(first - 1)) + (() if empty else (header(fill_number),))
    finality = route(seen(4))
    finality["finalized"] = change(finality["finalized"], {"number": hex(last), "hash": H3, "timestamp": s._frame(header(last))["timestamp"]})
    for key in ("exchange_code", "ctf_code"):
        finality[key] = replace(finality[key], request=replace(finality[key].request, params=(finality[key].request.params[0], hex(last))))
    inst = instrument(seen(3))
    inst["mapping"] = {key: replace(value, request=replace(value.request, params=(value.request.params[0], hex(last)))) for key, value in inst["mapping"].items()}
    log = deepcopy(logs(token=token)[1]); log["blockNumber"] = hex(fill_number)
    matched_logs = [] if empty else [log]
    if opposing:
        other = deepcopy(log); other["logIndex"] = "0x1"
        other["data"] = "0x" + word(0) + word(8) + other["data"][130:]
        matched_logs.append(other)
    ranges = []
    for index, start in enumerate(range(first, last + 1, 128)):
        end = min(start + 127, last)
        filters = {"address": s.EXCHANGE, "fromBlock": hex(start), "toBlock": hex(end), "topics": [s.TOPIC, None, "0x" + "0" * 24 + WALLET[2:]]}
        ranges.append(frame("range_" + str(index), "eth_getLogs", (filters,), matched_logs if start <= fill_number <= end else [], seen(2)))
    receipts = () if empty else (frame("receipt", "eth_getTransactionReceipt", (TX,),
        {"transactionHash": TX, "blockHash": H2, "blockNumber": hex(fill_number), "transactionIndex": "0x0", "status": "0x1", "logs": matched_logs}, seen(1)),)
    data = {"blocks": headers, "receipts": receipts, "logs": tuple(ranges), "finality": finality, "start_block": first, "end_block": last}
    book = frame("book", "GET", (), {"market": CONDITION, "asset_id": "7", "bids": [{"price": "0.55", "size": "10"}], "asks": [{"price": "0.65", "size": "10"}], "neg_risk": False}, T0, url="https://clob.polymarket.com/book?token_id=7")
    frames = tuple(finality.values()) + tuple(inst["mapping"].values()) + tuple(cache.values()) + receipts + tuple(ranges) + (book,)
    captured = s.capture_seed_evidence(seal=seal, phase="DECISION", ledger_path=path, output_dir=tmp_path,
        transport=s.SyntheticTransport(frames, {"instrument": inst, "coverage": data}))
    assert captured.status == "SYNTHETIC_CAPTURE_RETAINED", captured
    profile = s.P.build_wallet_profile_snapshot(wallet_ledger_path=path, cohort_snapshot=cohort, target_wallet=WALLET, as_of=T0, market_contexts=contexts)
    bundle = {"instrument": inst, "coverage": data, "ledger_head": profile.wallet_ledger_head_hash, "cohort": cohort,
        "profile": profile, "contexts": contexts, "identity_observability": {}, "books": (book,), "committed_at": s.SyntheticDecisionClock(T0)}
    return path, seal, bundle, frames, captured


@pytest.mark.parametrize("empty,token", ((True, 7), (False, 7), (False, 8)))
def test_realistic_hourly_range_feasibility(tmp_path, pins, empty, token):
    path, seal, bundle, frames, captured = realistic_prepared(tmp_path, pins, empty, token)
    assert len(bundle["coverage"]["logs"]) == 14
    assert len(bundle["coverage"]["blocks"]) <= 4
    assert captured.payload["calls"] == len(frames) <= 45 < 128
    assert captured.payload["bytes"] == sum(len(f.body) for f in frames) < 8388608
    proof = captured.payload["coverage"]
    assert proof["covered_block_count"] == 1771 and proof["finalized_frontier_time"] == "2026-01-10T23:59:00+00:00"
    assert proof["status"] == "SOURCE_CONTRACT_COMPLETE_CONDITIONAL" and proof["provider_attestation"] == "NOT_ESTABLISHED"
    result = s.materialize_forecast_pair(seal=seal, decision_bundle=bundle, ledger_path=path)
    assert result.status == "PENDING", result
    assert result.payload["coverage"] == proof and result.payload["p_nonwallet"] == "0.6"
    assert result.payload["p_wallet_added"] == ("0.6" if empty else "0.64" if token == 7 else "0.54")
    assert result.payload["vote"] == (None if empty else int(token == 7))
    assert result.payload["enrolled_count"] == "NOT_ESTABLISHED" and not result.study_activated
    if not empty:
        event = next(e.payload for e in s.L.load_and_verify_wallet_evidence_ledger(path).snapshot.entries if e.record_kind == "WALLET_EVIDENCE_EVENT")
        assert event["event_time"] == "2026-01-10T23:11:40Z"
        assert bundle["coverage"]["logs"][2].observed_at == "2026-01-10T23:59:58Z"
        assert bundle["profile"].included_wallet_event_ids == (event["wallet_event_id"],)


@pytest.mark.parametrize("fault", ("missing", "overlap", "gap", "early", "late_range", "maker_filter", "token_filter", "emitter_filter", "topic_filter", "early_anchor", "late_finality", "wrong_frontier", "unfinal_log", "receipt", "header", "transaction_membership", "duplicate", "wrong_maker", "late_log", "timeout", "partial", "error", "oversize", "cap", "forged_origin", "body_rehash"))
def test_realistic_range_negative_matrix(tmp_path, pins, fault):
    path, seal, bundle, _, _ = realistic_prepared(tmp_path, pins)
    data = deepcopy(bundle["coverage"]); ranges = list(data["logs"])
    if fault == "missing": ranges.pop()
    if fault in ("overlap", "gap", "early", "late_range", "maker_filter", "token_filter", "emitter_filter", "topic_filter"):
        index = 1 if fault in ("overlap", "gap") else 0
        filters = deepcopy(ranges[index].request.params[0])
        if fault == "overlap": filters["fromBlock"] = hex(s._quantity(filters["fromBlock"]) - 1)
        if fault == "gap": filters["fromBlock"] = hex(s._quantity(filters["fromBlock"]) + 1)
        if fault == "early": filters["fromBlock"] = "0x1"
        if fault == "late_range": filters["toBlock"] = hex(s._quantity(filters["toBlock"]) + 1)
        if fault == "maker_filter": filters["topics"][2] = "0x" + word(2)
        if fault == "token_filter": filters["topics"].append("0x" + word(7))
        if fault == "emitter_filter": filters["address"] = s.CTF
        if fault == "topic_filter": filters["topics"][0] = "0x" + "0" * 64
        ranges[index] = replace(ranges[index], request=replace(ranges[index].request, params=(filters,)))
    if fault == "early_anchor":
        value = s._frame(data["blocks"][2]); value["timestamp"] = s._frame(data["blocks"][0])["timestamp"]
        data["blocks"] = (*data["blocks"][:2], change(data["blocks"][2], value), data["blocks"][3])
    if fault == "late_finality": data["finality"]["finalized"] = replace(data["finality"]["finalized"], observed_at="2026-01-11T00:00:01Z")
    if fault == "wrong_frontier":
        value = s._frame(data["finality"]["finalized"]); value["hash"] = "0x" + "3" * 64
        data["finality"]["finalized"] = change(data["finality"]["finalized"], value)
    if fault == "receipt": data["receipts"] = ()
    if fault == "header":
        value = s._frame(data["blocks"][3]); value["hash"] = "0x" + "3" * 64
        data["blocks"] = (*data["blocks"][:3], change(data["blocks"][3], value))
    if fault == "transaction_membership":
        value = s._frame(data["blocks"][3]); value["transactions"].reverse()
        data["blocks"] = (*data["blocks"][:3], change(data["blocks"][3], value))
    if fault in ("unfinal_log", "duplicate", "wrong_maker", "cap", "body_rehash"):
        value = s._frame(ranges[2])
        if fault == "unfinal_log": value[0]["blockNumber"] = hex(1773)
        if fault == "wrong_maker": value[0]["topics"][2] = "0x" + word(2)
        if fault == "body_rehash": value[0]["data"] = "0x" + word(0) + word(8) + value[0]["data"][130:]
        if fault == "duplicate": value *= 2
        if fault == "cap": value *= 256
        ranges[2] = change(ranges[2], value)
    if fault == "late_log": ranges[0] = replace(ranges[0], observed_at="2026-01-11T00:00:01Z")
    if fault == "timeout": ranges[0] = replace(ranges[0], started_at="2026-01-10T23:59:50Z")
    if fault == "partial": ranges[0] = replace(ranges[0], body=b'{"jsonrpc":"2.0","id":1,"result":[],"truncated":true}')
    if fault == "error": ranges[0] = replace(ranges[0], body=b'{"jsonrpc":"2.0","id":1,"error":{"code":-32005,"message":"range cap"}}')
    if fault == "oversize": ranges[0] = replace(ranges[0], body=b" " * 2097153)
    if fault == "forged_origin": object.__setattr__(ranges[0], "origin", "REAL_DIRECT_HTTPS")
    data["logs"] = tuple(ranges)
    result = s.materialize_forecast_pair(seal=seal, decision_bundle={**bundle, "coverage": data}, ledger_path=path)
    assert result.status == "UNKNOWN" and result.payload.get("p_wallet_added") is None, result
    assert sum(result.payload["synthetic_counts"].values()) == 1 and not result.study_activated


def test_realistic_request_byte_elapsed_budget_exhaustion(tmp_path, pins):
    path, seal, bundle, frames, _ = realistic_prepared(tmp_path, pins)
    before = s.L.load_and_verify_wallet_evidence_ledger(path).snapshot.head_hash
    extra = tuple(frame("extra_" + str(i), "eth_chainId", (), "0x89") for i in range(129 - len(frames)))
    assert len(frames + extra) == 129
    assert s.capture_seed_evidence(seal=seal, phase="DECISION", ledger_path=path, output_dir=tmp_path,
        transport=s.SyntheticTransport(frames + extra)).errors == ("LIMIT_INVALID",)
    # Dense returned transactions need receipts even when they share one block.
    dense = deepcopy(bundle["coverage"]); template = s._frame(dense["receipts"][0]); rows = []; receipts = []
    for index in range(110):
        log = deepcopy(template["logs"][0]); log.update(transactionHash="0x" + word(index + 100), transactionIndex=hex(index), logIndex=hex(index))
        rows.append(log)
        record = {**template, "transactionHash": log["transactionHash"], "transactionIndex": hex(index), "logs": [log]}
        receipts.append(frame("dense_receipt_" + str(index), "eth_getTransactionReceipt", (log["transactionHash"],), record))
    dense["receipts"] = tuple(receipts)
    dense["logs"] = (*dense["logs"][:2], change(dense["logs"][2], rows), *dense["logs"][3:])
    block = s._frame(dense["blocks"][3]); block["transactions"] = [log["transactionHash"] for log in rows]
    dense["blocks"] = (*dense["blocks"][:3], change(dense["blocks"][3], block))
    dense_result = s.materialize_forecast_pair(seal=seal, decision_bundle={**bundle, "coverage": dense}, ledger_path=path)
    assert dense_result.status == "UNKNOWN" and dense_result.errors == ("LIMIT_INVALID",)
    for key, value in (("calls", len(frames) - 1), ("bytes", sum(len(f.body) for f in frames) - 1), ("elapsed_seconds", 3)):
        limited = deepcopy(seal); limited["payload"]["approved_source_call_byte_elapsed_limits"][key] = value
        limited["digest"] = s._identity("walletstudy:sha256:", limited["payload"]); limited = approve(limited)
        assert s.capture_seed_evidence(seal=limited, phase="DECISION", ledger_path=path, output_dir=tmp_path,
            transport=s.SyntheticTransport(frames)).errors == ("LIMIT_INVALID",)
    assert s.L.load_and_verify_wallet_evidence_ledger(path).snapshot.head_hash == before


def test_realistic_six_states_and_conditional_empty_limitation(tmp_path, pins):
    path, seal, bundle, _, _ = realistic_prepared(tmp_path, pins)
    pair = s.materialize_forecast_pair(seal=seal, decision_bundle=bundle, ledger_path=path)
    assert pair.status == "PENDING"
    bad = deepcopy(seal); bad["payload"]["method_digest"] = "wrong"
    excluded = s.materialize_forecast_pair(seal=bad, decision_bundle=bundle, ledger_path=path)
    unknown = s.materialize_forecast_pair(seal=seal, decision_bundle={**bundle, "books": ()}, ledger_path=path)
    unmatched = s.materialize_forecast_pair(seal=seal, decision_bundle={**bundle, "committed_at": None}, ledger_path=path)
    def final_label(denominator=1):
        label = label_bundle(bundle["instrument"], target=denominator, denominator=denominator, resolved=bool(denominator))
        number = hex(20000)
        block = s._frame(label["route"]["finalized"]); block["number"] = number
        label["route"]["finalized"] = change(label["route"]["finalized"], block)
        for key in ("exchange_code", "ctf_code"):
            value = label["route"][key]; label["route"][key] = replace(value, request=replace(value.request, params=(value.request.params[0], number)))
        for owner in (label["instrument"]["mapping"], label):
            for key, value in list(owner.items()):
                if type(value) is s.SourceFrame and value.request.method == "eth_call":
                    owner[key] = replace(value, request=replace(value.request, params=(value.request.params[0], number)))
        return label
    matched = s.attach_final_label(pair=pair, label_bundle=final_label(), as_of="2026-01-12T00:00:02Z")
    censored = s.attach_final_label(pair=pair, label_bundle=final_label(0), as_of="2026-02-12T00:00:00Z")
    for result, state in ((excluded, "EXCLUDED"), (unknown, "UNKNOWN"), (unmatched, "UNMATCHED"), (matched, "MATCHED"), (pair, "PENDING"), (censored, "CENSORED")):
        assert result.status == state, result
        assert sum(result.payload["synthetic_counts"].values()) == 1 and result.payload["enrolled_count"] == "NOT_ESTABLISHED"
    assert matched.payload["delta"] == "0.0304"
    # Empty conforming fixtures certify conditional coverage, never physical absence.
    other = tmp_path / "empty"; other.mkdir()
    empty_path, empty_seal, empty_bundle, _, capture = realistic_prepared(other, pins, empty=True)
    no_signal = s.materialize_forecast_pair(seal=empty_seal, decision_bundle=empty_bundle, ledger_path=empty_path)
    assert no_signal.payload["vote"] is None and capture.payload["provider_attestation"] == "NOT_ESTABLISHED"


def test_realistic_same_clock_conflict_and_between_block_start(tmp_path, pins):
    path, seal, bundle, _, capture = realistic_prepared(tmp_path, pins, opposing=True)
    result = s.materialize_forecast_pair(seal=seal, decision_bundle=bundle, ledger_path=path)
    assert capture.payload["coverage"]["returned_log_count"] == 2 and result.status == "UNKNOWN"
    assert result.payload["p_wallet_added"] is None and sum(result.payload["synthetic_counts"].values()) == 1
    other = tmp_path / "between"; other.mkdir()
    path, seal, bundle, _, _ = realistic_prepared(other, pins, offset=1)
    assert s.materialize_forecast_pair(seal=seal, decision_bundle=bundle, ledger_path=path).status == "PENDING"


def test_range_filter_covers_all_sealed_makers_without_token_narrowing(tmp_path, pins):
    _, seal, bundle, _, _ = realistic_prepared(tmp_path, pins, empty=True)
    seal = deepcopy(seal); inst = deepcopy(bundle["instrument"]); data = deepcopy(bundle["coverage"])
    makers = (WALLET, "0x" + "2" * 40); inst["wallets"] = makers
    seal["payload"]["observation_group_missingness_policies"]["membership"] = list(makers)
    ranges = []
    for value in data["logs"]:
        filters = deepcopy(value.request.params[0]); filters["topics"][2] = ["0x" + "0" * 24 + maker[2:] for maker in makers]
        ranges.append(replace(value, request=replace(value.request, params=(filters,))))
    data["logs"] = tuple(ranges)
    events, proof = s._coverage(data, seal, inst)
    assert events == [] and proof["range_count"] == 14
    with pytest.raises(s.SeedError, match="COVERAGE_UNKNOWN"):
        s._coverage({**data, "logs": bundle["coverage"]["logs"]}, seal, inst)


@pytest.fixture(autouse=True)
def deny_source_network(monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail("source network must remain disabled in synthetic tests")
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(s.urllib.request.OpenerDirector, "open", denied)
    monkeypatch.setattr(s.urllib.request, "urlopen", denied)


def readiness_digest(request):
    request["digest"] = s._identity("walletreadinessrequest:sha256:", {key: value for key, value in request.items() if key != "digest"})
    return request


@pytest.fixture
def readiness_inputs(tmp_path, pins, monkeypatch):
    now = s._stamp(T0)
    monkeypatch.setattr(s, "_utc_now", lambda: now)
    directory = tmp_path / "probe"
    request = readiness_digest({"kind": "NON_STUDY_READINESS", "request_id": "synthetic_probe", "code_sha": CODE,
        "method_digest": s.METHOD_DIGEST, "not_before": s._utc_text(now), "expires_at": s._utc_text(now + timedelta(seconds=120)),
        "output_dir": str(directory), "budget": dict(s.LIMITS), "source_policy_id": s.READINESS_POLICY_ID})
    header = {"number": "0x6000000", "hash": H3, "timestamp": hex(int((now - timedelta(seconds=60)).timestamp()))}
    values = ("0x89", header, "0x6001", "0x6002", header, "0x", [], header)
    frames = tuple(s.SourceFrame(s._readiness_plan(index, header), s.C.wallet_canonical_json_bytes({"jsonrpc": "2.0", "id": 1, "result": value}),
        s._utc_text(now + timedelta(seconds=index)), CODE) for index, value in enumerate(values))
    approval = {"kind": "MANUAL_EXTERNAL_APPROVAL_REFERENCE", "request_digest": request["digest"], "planned_operator": "KARL",
        "external_review_ref": "synthetic-side19-fixture", "approved_at": s._utc_text(now - timedelta(seconds=1))}
    return request, directory, frames, approval


@pytest.mark.parametrize("fault", ("missing", "null", "type", "empty", "extra", "phase", "code", "method", "policy", "budget_missing", "budget_bool", "budget_float", "budget_calls", "budget_large", "path", "digest", "expired", "wide", "wording", "credential"))
def test_readiness_request_scope(readiness_inputs, fault):
    request, directory, frames, _ = readiness_inputs
    assert s.validate_readiness_request(request=request).status == "READINESS_PREVIEW"
    future = deepcopy(request)
    future["not_before"] = s._utc_text(s._stamp(T0) + timedelta(seconds=30))
    readiness_digest(future)
    assert s.validate_readiness_request(request=future).status == "READINESS_PREVIEW"
    assert s.capture_readiness(request=future, output_dir=directory, transport=s.SyntheticTransport(frames)).errors == ("WINDOW_INVALID",)
    assert not directory.exists()
    bad = deepcopy(request)
    if fault == "missing": bad.pop("code_sha")
    if fault == "null": bad["request_id"] = None
    if fault == "type": bad["request_id"] = 1
    if fault == "empty": bad["request_id"] = ""
    if fault == "extra": bad["wallets"] = [WALLET]
    if fault == "phase": bad["kind"] = "DECISION"
    if fault == "code": bad["code_sha"] = "short"
    if fault == "method": bad["method_digest"] = "changed"
    if fault == "policy": bad["source_policy_id"] = "changed"
    if fault == "budget_missing": bad["budget"].pop("bytes")
    if fault == "budget_bool": bad["budget"]["calls"] = True
    if fault == "budget_float": bad["budget"]["timeout_seconds"] = 1.0
    if fault == "budget_calls": bad["budget"]["calls"] = 7
    if fault == "budget_large": bad["budget"]["bytes"] += 1
    if fault == "path": bad["output_dir"] = "relative"
    if fault == "expired": bad["expires_at"] = T0
    if fault == "wide": bad["expires_at"] = s._utc_text(s._stamp(T0) + timedelta(seconds=121))
    if fault == "wording": bad["request_id"] = "trade_ready"
    if fault == "credential": bad["api_key"] = "inert-secret-sentinel"
    if fault != "budget_float": readiness_digest(bad)
    if fault == "digest": bad["digest"] = "changed"
    rejected = s.validate_readiness_request(request=bad)
    assert rejected.status == "DENIED"
    assert "inert-secret-sentinel" not in json.dumps(s.readiness_result_to_mapping(result=rejected))
    assert s.capture_readiness(request=bad, output_dir=directory, transport=s.SyntheticTransport(frames)).status == "DENIED"
    assert not directory.exists()


class Terminal(io.StringIO):
    def isatty(self):
        return True


@pytest.mark.parametrize("fault", ("absent", "hash_only", "wrong_digest", "wrong_operator", "future", "empty", "extra", "duplicate", "noninteractive", "eof", "challenge", "early"))
def test_readiness_manual_boundary(readiness_inputs, monkeypatch, fault):
    request, directory, frames, approval = readiness_inputs
    assert s.capture_readiness(request=request, output_dir=directory).errors == ("PRODUCTION_DISABLED",)
    assert s.capture_readiness(request=request, output_dir=directory, transport=object()).errors == ("PRODUCTION_DISABLED",)
    with pytest.raises(s.SeedError, match="PRODUCTION_DISABLED"):
        s._rpc_post(frames[0].request, 1024, 1)
    output = io.StringIO()
    monkeypatch.setattr(sys, "stdout", output)
    assert s.main(["--status"]) == 0
    assert json.loads(output.getvalue())["status"] == "PRODUCTION_DISABLED"
    monkeypatch.setenv("ACT01_APPROVED", "true")
    assert s.main(["--yes", "inert-secret-sentinel"]) == 1
    assert "inert-secret-sentinel" not in output.getvalue()
    invalid = deepcopy(approval)
    if fault == "absent": invalid = None
    if fault == "hash_only": invalid = {"digest": s._identity("approval:", approval)}
    if fault == "wrong_digest": invalid["request_digest"] = "changed"
    if fault == "wrong_operator": invalid["planned_operator"] = "OTHER"
    if fault == "future": invalid["approved_at"] = s._utc_text(s._stamp(T0) + timedelta(seconds=1))
    if fault == "empty": invalid["external_review_ref"] = ""
    if fault == "extra": invalid["approved"] = True
    if fault == "duplicate":
        with pytest.raises(s.SeedError):
            s._rpc_document(b'{"kind":"one","kind":"two"}')
        invalid = {"kind": "conflict"}
    monkeypatch.setattr(s, "_readiness_checkout", lambda checked: None)
    monkeypatch.setattr(sys, "stdout", Terminal())
    monkeypatch.setattr(sys, "stderr", Terminal())
    monkeypatch.setattr(s.secrets, "token_hex", lambda size: "fixture-challenge")
    approval_id = s._identity("walletreadinessapproval:sha256:", approval)
    answer = "AUTHORIZE NON_STUDY_READINESS " + request["digest"] + " " + approval_id + " fixture-challenge\n"
    monkeypatch.setattr(sys, "stdin", io.StringIO(answer) if fault == "noninteractive" else Terminal("" if fault == "eof" else "wrong\n" if fault == "challenge" else answer))
    if fault == "early":
        request["not_before"] = s._utc_text(s._stamp(T0) + timedelta(seconds=30))
        readiness_digest(request)
        invalid["request_digest"] = request["digest"]
    with pytest.raises((s.SeedError, TypeError)):
        s._readiness_console(request, invalid)
    assert not directory.exists()
    if fault != "early":
        monkeypatch.setattr(sys, "stdin", Terminal(answer))
        permit = s._readiness_console(request, approval)
        assert type(permit) is s._ReadinessPermit and permit.active
        result = s._run_readiness(request, directory, s.SyntheticTransport(frames), approval=approval, permit=permit)
        assert result.origin == "SYNTHETIC" and result.human_identity == "NOT_MACHINE_ATTESTED"
        assert result.operator_approval == "MANUAL_ASSERTION_REQUIRES_EXTERNAL_REVIEW"
        assert not permit.active
        with pytest.raises(s.SeedError, match="APPROVAL_INVALID"):
            s._run_readiness(request, directory, s.SyntheticTransport(frames), approval=approval, permit=permit)


@pytest.mark.parametrize("fault", ("none", "chain", "stale", "future", "boundary", "noncanonical", "missing", "null", "error", "id", "bool_id", "duplicate_key", "float", "truncated", "partial", "exchange_code", "ctf_code", "code_request", "before_header", "after_header", "predeployment_code", "logs", "filter", "large_runtime"))
def test_readiness_fixed_source_plan(readiness_inputs, monkeypatch, fault):
    request, directory, frames, _ = readiness_inputs
    frames = list(frames)
    if fault == "chain": frames[0] = change(frames[0], "0x1")
    if fault in ("stale", "future", "boundary", "noncanonical", "missing"):
        header = s._frame(frames[1])
        if fault == "stale": header["timestamp"] = hex(int((s._stamp(T0) - timedelta(seconds=300)).timestamp()))
        if fault == "future": header["timestamp"] = hex(int((s._stamp(T0) + timedelta(seconds=2)).timestamp()))
        if fault == "boundary": header["timestamp"] = hex(int((s._stamp(T0) - timedelta(seconds=300)).timestamp()))
        if fault == "noncanonical": header["timestamp"] = "0x00"
        if fault == "missing": header.pop("timestamp")
        frames[1] = change(frames[1], header)
        if fault == "boundary":
            frames[4] = change(frames[4], header)
            frames[7] = change(frames[7], header)
            frames = [replace(value, observed_at=T0) for value in frames]
    if fault == "null": frames[1] = change(frames[1], None)
    bodies = {"error": b'{"jsonrpc":"2.0","id":1,"error":{"code":-32001,"message":"pruned"}}',
        "id": b'{"jsonrpc":"2.0","id":2,"result":"0x89"}', "bool_id": b'{"jsonrpc":"2.0","id":true,"result":"0x89"}',
        "duplicate_key": b'{"jsonrpc":"2.0","id":1,"id":1,"result":"0x89"}', "float": b'{"jsonrpc":"2.0","id":1,"result":0.5}',
        "truncated": b'{"jsonrpc":"2.0",', "partial": b'{"jsonrpc":"2.0","id":1,"result":"0x89","truncated":true}'}
    if fault in bodies: frames[0] = replace(frames[0], body=bodies[fault])
    if fault == "exchange_code": frames[2] = change(frames[2], "0x6003")
    if fault == "ctf_code": frames[3] = change(frames[3], "0x6003")
    if fault == "code_request": frames[2] = replace(frames[2], request=replace(frames[2].request, params=(s.EXCHANGE, "0x1")))
    if fault in ("before_header", "after_header"):
        index = 4 if fault == "before_header" else 7
        header = s._frame(frames[index]); header["hash"] = H2
        frames[index] = change(frames[index], header)
    if fault == "predeployment_code": frames[5] = change(frames[5], "0x60")
    if fault == "logs": frames[6] = change(frames[6], [{"transactionHash": TX}])
    if fault == "filter": frames[6] = replace(frames[6], request=replace(frames[6].request, params=({"address": s.EXCHANGE, "fromBlock": "0x0", "toBlock": "0x50f81d0", "topics": [s.TOPIC]},)))
    if fault == "large_runtime":
        runtime = bytes.fromhex("60" * 21037)
        monkeypatch.setattr(s, "EXCHANGE_HASH", sha256(runtime).hexdigest())
        frames[2] = replace(frames[2], body=json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0x" + runtime.hex()}).encode())
    result = s.capture_readiness(request=request, output_dir=directory, transport=s.SyntheticTransport(tuple(frames)))
    success = fault in ("none", "boundary", "large_runtime")
    assert result.status == ("SYNTHETIC_READINESS_OBSERVED" if success else "READINESS_INCONCLUSIVE"), result
    assert result.accounting["calls"] <= 8
    assert result.provider_attestation == "NOT_ESTABLISHED" and result.enrolled_count == "NOT_ESTABLISHED"
    assert result.observations["coverage"] == result.observations["current_period_logs"] == "NOT_ESTABLISHED"
    assert not list(directory.glob("*.sqlite*")) and not (directory / "study.json").exists()
    if success:
        assert result.accounting["calls"] == 8
        assert result.accounting["received_bytes"] == sum(len(value.body) for value in frames)
        assert result.observations["log_probe"] == "EMPTY_METHOD_SHAPE_ONLY"
        filters = frames[6].request.params[0]
        assert int(filters["toBlock"], 16) - int(filters["fromBlock"], 16) + 1 == 128
        assert filters["topics"] == [s.TOPIC] and int(filters["toBlock"], 16) == 84902353 - 1
        assert result.observations["canonical_checks"] == 2
    else:
        assert list(directory.glob("*.quarantine.raw"))


class FakeReadinessResponse:
    def __init__(self, body, status=200, fault=None):
        self.body = body
        self.status = status
        self.fault = fault
        self.offset = 0
        self.closed = False
    def read(self, maximum):
        if self.fault is not None:
            raise self.fault
        result = self.body[self.offset:self.offset + maximum]
        self.offset += len(result)
        return result
    def close(self):
        self.closed = True


class FakeReadinessOpener:
    def __init__(self, response, fault=None):
        self.response = response
        self.fault = fault
        self.requests = []
    def open(self, request, timeout):
        self.requests.append((request, timeout))
        if self.fault is not None:
            raise self.fault
        return self.response


@pytest.mark.parametrize("fault", ("none", "non200", "open", "timeout", "oversize", "elapsed", "utc", "proxy", "calls", "bytes", "default", "redirect"))
def test_readiness_transport_budgets(readiness_inputs, monkeypatch, fault):
    request, directory, frames, _ = readiness_inputs
    context = s._ReadinessRun(request, directory)
    context.begin_call()
    response = FakeReadinessResponse(b"a" * (65 if fault == "oversize" else 20), status=429 if fault == "non200" else 200,
        fault=TimeoutError("inert-secret-sentinel") if fault == "timeout" else None)
    opener = FakeReadinessOpener(response, urllib.error.URLError("inert-secret-sentinel") if fault == "open" else None)
    active_opener = opener
    if fault in ("default", "redirect"):
        context.production = True
        context.permit = s._ReadinessPermit(request["digest"], "synthetic-approval", s._CONSOLE_PERMIT, active=False)
        timeouts = []
        response.fp = SimpleNamespace(raw=SimpleNamespace(_sock=SimpleNamespace(settimeout=timeouts.append)))
        def default_builder(*handlers):
            assert isinstance(handlers[0], s.urllib.request.ProxyHandler) and handlers[0].proxies == {}
            if fault == "redirect":
                with pytest.raises(s.SeedError, match="REQUEST_DENIED"):
                    handlers[1].redirect_request(None, None, 302, "redirect", {}, "https://fixture.invalid")
                opener.fault = s.SeedError("REQUEST_DENIED")
            return opener
        monkeypatch.setattr(s.urllib.request, "build_opener", default_builder)
        monkeypatch.setenv("HTTPS_PROXY", "http://fixture.invalid")
        active_opener = None
    if fault == "elapsed": context.start_monotonic -= 121
    if fault == "utc": monkeypatch.setattr(s, "_utc_now", lambda: s._stamp(T0) + timedelta(seconds=120))
    if fault == "proxy": monkeypatch.setenv("HTTPS_PROXY", "http://fixture.invalid")
    if fault in ("non200", "open", "timeout", "oversize", "elapsed", "utc", "redirect"):
        with pytest.raises(s.SeedError) as failure:
            s._rpc_post(frames[0].request, 64, 1, active_opener, context=context)
        assert "inert-secret-sentinel" not in str(failure.value)
    else:
        assert s._rpc_post(frames[0].request, 64, 1, active_opener, context=context) == response.body
    assert len(opener.requests) == 1 and context.calls == 1
    sent, timeout = opener.requests[0]
    assert sent.full_url == f"https://{s.RPC_HOST}/" and sent.method == "POST" and 0 < timeout <= 5
    assert dict(sent.header_items()) == {"Content-type": "application/json"}
    assert json.loads(sent.data)["method"] == "eth_chainId"
    assert response.closed or fault in ("open", "redirect")
    if fault == "default": assert timeouts and all(0 < value <= 1 for value in timeouts)
    if fault == "oversize": assert context.received_bytes == 65 and len(context.body) == 65
    if fault == "non200": assert context.received_bytes == 20
    if fault == "calls":
        context.calls = 128
        with pytest.raises(s.SeedError): context.begin_call()
        assert context.calls == 128
    if fault == "bytes":
        request["budget"]["bytes"] = 1
        readiness_digest(request)
        result = s.capture_readiness(request=request, output_dir=directory, transport=s.SyntheticTransport(frames))
        assert result.status == "READINESS_INCONCLUSIVE" and result.accounting["calls"] == 1
        assert result.accounting["received_bytes"] == 2 and result.accounting["byte_cap_breached"]


@pytest.mark.parametrize("fault", ("none", "abort", "partial", "symlink", "existing", "path", "approval"))
def test_readiness_immutable_capture_and_replay(readiness_inputs, monkeypatch, tmp_path, fault):
    request, directory, frames, approval = readiness_inputs
    observed = s._readiness_observe
    def checked_observe(index, value, completed_at, frontier, observations):
        assert (directory / "run.claim").is_file()
        if fault == "abort" and index == 2:
            raise KeyboardInterrupt()
        return observed(index, value, completed_at, frontier, observations)
    monkeypatch.setattr(s, "_readiness_observe", checked_observe)
    if fault == "symlink":
        target = tmp_path / "target"; target.mkdir()
        try:
            directory.symlink_to(target, target_is_directory=True)
        except OSError:
            pytest.skip("Windows symlink privilege unavailable; authoritative Linux checks this case")
    if fault == "existing":
        directory.mkdir(); (directory / "run.claim").write_bytes(b"prior-immutable-fixture")
    if fault == "path":
        directory = tmp_path / "different"
    if fault == "partial":
        retained = s._retain
        def fail_metadata(path, name, content):
            if name == "chain.json": raise OSError("inert-secret-sentinel")
            return retained(path, name, content)
        monkeypatch.setattr(s, "_retain", fail_metadata)
    result = s.capture_readiness(request=request, output_dir=directory, transport=s.SyntheticTransport(frames))
    if fault in ("symlink", "existing", "path"):
        assert result.status == "DENIED"
        if fault == "existing": assert (directory / "run.claim").read_bytes() == b"prior-immutable-fixture"
        return
    assert result.status == ("READINESS_INCONCLUSIVE" if fault in ("abort", "partial") else "SYNTHETIC_READINESS_OBSERVED")
    assert (directory / "run.claim").exists()
    if fault == "partial":
        assert result.accounting["calls"] == 1 and result.receipt_id is None
        assert (directory / "chain.raw").exists() and not (directory / "receipt.json").exists()
    else:
        metadata = json.loads((directory / "chain.json").read_bytes())
        assert (directory / "chain.raw").read_bytes() == frames[0].body
        assert metadata["raw_reference"]["content_sha256"] == sha256(frames[0].body).hexdigest()
        assert metadata["raw_reference"]["pit"]["local_first_seen_time"] == frames[0].observed_at
        assert metadata["provenance_manifest"]["input_evidence_reference_ids"] == [metadata["raw_reference"]["raw_evidence_reference_id"]]
        receipt = json.loads((directory / "receipt.json").read_bytes())
        assert receipt["code_sha"] == CODE and receipt["request_digest"] == request["digest"]
        assert result.receipt_id == receipt["receipt_id"]
    if fault == "abort": assert result.errors == ("OPERATOR_CANCELLED",) and result.accounting["calls"] == 3
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    if fault == "approval": approval["external_review_ref"] = "another-synthetic-reference"
    replay = s.capture_readiness(request=request, output_dir=directory, transport=s.SyntheticTransport(frames))
    assert replay.status == "DENIED"
    assert before == {path.name: path.read_bytes() for path in directory.iterdir()}


@pytest.mark.parametrize("variant", ("trade-ready", "TRADE_READY", "trade ready", "buy/sell recommendation", "Buy/Sell_Recommendation", "copy_signal"))
def test_readiness_safe_output_and_no_promotion(readiness_inputs, variant):
    request, directory, frames, _ = readiness_inputs
    result = s.capture_readiness(request=request, output_dir=directory, transport=s.SyntheticTransport(frames))
    serialized = s.readiness_result_to_mapping(result=result)
    assert {item.name for item in fields(result)} == set(serialized) == s.READINESS_RESULT_FIELDS
    for item in fields(result):
        value = (variant,) if item.name == "errors" else {"nested": variant} if item.name in ("observations", "accounting") else variant
        with pytest.raises(s.SeedError):
            s.readiness_result_to_mapping(result=replace(result, **{item.name: value}))
    with pytest.raises(s.SeedError):
        s.readiness_result_to_mapping(result=replace(result, observations={"raw_metadata": {"api_key": "inert-secret-sentinel"}}))
    forged = replace(result, origin="DIRECT_HTTPS_NON_STUDY_PENDING_REVIEW")
    object.__setattr__(forged, "_commitment", s._identity("readinessresult:", asdict(forged)))
    with pytest.raises(s.SeedError, match="OUTPUT_UNSAFE"):
        s.readiness_result_to_mapping(result=forged)
    assert s.capture_seed_evidence(seal=serialized, phase="DECISION", ledger_path=directory / "absent.sqlite", output_dir=directory).errors == ("PRODUCTION_DISABLED",)
    assert serialized["numeric_summary"] is None and not serialized["study_activated"]
    assert serialized["operator_approval"] == "MANUAL_ASSERTION_REQUIRES_EXTERNAL_REVIEW"
    assert "inert-secret-sentinel" not in json.dumps(serialized)


def test_readiness_import_and_cli_never_open_source_transport():
    script = "import socket,urllib.request; deny=lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('network')); socket.create_connection=deny; urllib.request.OpenerDirector.open=deny; from tools.polymarket import wallet_seed; assert wallet_seed.main(['--status'])==0"
    completed = subprocess.run([sys.executable, "-B", "-c", script], cwd=s.ROOT, capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0 and json.loads(completed.stdout)["status"] == "PRODUCTION_DISABLED"


def test_readiness_policy_matches_exact_v2_package():
    with pytest.raises(TypeError):
        s.readiness_result_to_mapping(s.ReadinessResult("DENIED"))
    spec = json.loads((s.ROOT / "docs/wp_specs/S10-WALLET-SEED-ACT-01/wp_spec.json").read_bytes())
    example = spec["examples"]["items"][0]["input"]
    assert example["readiness_policy_id"] == s.READINESS_POLICY_ID
    assert s._identity("walletreadinesspolicy:sha256:", {"readiness": example["readiness"]}) == s.READINESS_POLICY_ID
    assert example["readiness"]["max_finalized_age_seconds"] == 300 and example["readiness"]["plan_calls"] == 8
    assert spec["scope"]["required_changed_files"] == spec["scope"]["allowed_changed_files"]
    assert spec["scope"]["max_changed_files"] == 9 and not spec["authority"]["source_runtime"]
