"""Synthetic original-response integration tests; no production transport."""
from copy import deepcopy
from dataclasses import asdict, fields, replace
from datetime import timedelta
from hashlib import sha256
import json
from pathlib import Path

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
        "finalized": frame("finalized", "eth_getBlockByNumber", ("finalized", False), {"number": "0x3", "hash": H3}, seen),
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
    receipt = {"transactionHash": TX, "blockHash": H2, "blockNumber": "0x2", "transactionIndex": "0x0", "status": "0x1", "logs": [log]}
    return {"blocks": (frame("block2", "eth_getBlockByNumber", ("0x2", True), block2), frame("block3", "eth_getBlockByNumber", ("0x3", True), block3)),
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


def label_bundle(inst, seen="2026-01-12T00:00:01Z", target=1, denominator=1, resolved=True):
    inst = instrument(seen)
    values = (denominator, target, denominator - target)
    result = {"instrument": inst, "route": route(seen)}
    for key, selector, value in zip(("denominator", "target_numerator", "complement_numerator"), ("0xdd34de67", "0x0504c814", "0x0504c814"), values):
        data = selector + CONDITION[2:] + ("" if key == "denominator" else word(0 if key == "target_numerator" else 1))
        result[key] = frame(key, "eth_call", ({"to": s.CTF, "data": data}, "0x3"), "0x" + word(value), seen)
    result["venue"] = frame("venue", "GET", (), {"conditionId": CONDITION, "resolved": resolved, "disputed": False, "void": False, "cancelled": False, "winningToken": "7" if target else "8"}, seen, url="https://gamma-api.polymarket.com/markets/17")
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
