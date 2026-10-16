"""Offline synthetic assessment mechanics; no provider or strategy authority.

The trusted caller supplies the unchanged TS01 cold export result. This consumer
checks its internal binding; it does not independently authenticate an archive.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re

from .models import (
    build_strategy_research_draft_output_schema, canonical_json_bytes,
    check_strategy_assessment_consistency, sha256_hex, validate_research_draft,
)

_LIMIT = 65_536
_FILES = ("00_A.json", "01_HANDOFF.json", "02_B.json", "03_TERMINAL.json")
_STATUSES = {"OFFLINE_SYNTHETIC_VALIDATED", "INVALID_OUTPUT", "INTERRUPTED_BLOCKED"}


def _require(condition):
    if not condition:
        raise ValueError("TS02_INVALID")


def _utc(value):
    _require(isinstance(value, str) and re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", value))
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    _require(moment.tzinfo is not None)
    return moment.astimezone(timezone.utc)


def _bounded_json(value):
    encoded = canonical_json_bytes(value)
    _require(len(encoded) <= _LIMIT)
    return encoded


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def build_handoff(*, stage_a_text, trusted_pair, cutoff, expected_request_id,
                  strategy_parameter_names, max_sources=8):
    """Consume a producer-owned cold export, never a mapping supplied by Stage A."""
    _require(isinstance(stage_a_text, str) and 0 < len(stage_a_text.encode("utf-8")) <= 20_000)
    _require(isinstance(expected_request_id, str) and re.fullmatch(r"[A-Za-z0-9:._-]{1,160}", expected_request_id))
    _require(isinstance(strategy_parameter_names, (tuple, list)) and len(strategy_parameter_names) <= 64)
    _require(all(isinstance(n, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", n) for n in strategy_parameter_names))
    _require(len(set(strategy_parameter_names)) == len(strategy_parameter_names))
    _require(type(max_sources) is int and 1 <= max_sources <= 8)
    names = sorted(strategy_parameter_names)
    schema = build_strategy_research_draft_output_schema(expected_request_id=expected_request_id,
        max_sources=max_sources, strategy_parameter_names=names)
    deadline = _utc(cutoff)
    pair = trusted_pair
    _require(isinstance(pair, dict) and set(pair) == {"status", "proof_level", "transport_mode",
        "market_id", "token_id", "receipt_sha256", "attempts", "selected"})
    _require(pair["status"] == "ADMITTED" and pair["proof_level"] == "LOCAL_PRODUCER_WITNESS")
    _require(pair["transport_mode"] in ("INJECTED", "NATIVE_HTTP"))
    attempts = pair["attempts"]
    _require(isinstance(attempts, list) and 2 <= len(attempts) <= 12)
    ledger = []
    selected = []
    rows = []
    previous = datetime.min.replace(tzinfo=timezone.utc)
    for item in attempts:
        _require(isinstance(item, dict))
        raw = item["raw_bytes"]
        _require(isinstance(raw, bytes) and len(raw) <= _LIMIT)
        _require(type(item["byte_length"]) is int and len(raw) == item["byte_length"]
                 and sha256_hex(raw) == item["raw_sha256"])
        start, end, receive = map(_utc, (item["request_started_at"], item["response_completed_at"], item["received_at"]))
        _require(previous <= start <= end <= receive <= deadline)
        previous = receive
        _require(type(item["http_status"]) is int and 100 <= item["http_status"] <= 599)
        _require(type(item["duration_ns"]) is int and item["duration_ns"] >= 0)
        ledger.append({key: value for key, value in item.items() if key != "raw_bytes"})
        if 200 <= item["http_status"] < 300:
            selected.append(item["occurrence_id"])
            rows.append((item, json.loads(raw, object_pairs_hook=_unique)))
    _require(len(rows) == 2 and len(set(selected)) == 2 and selected == pair["selected"])
    gamma, book = rows[0][1], rows[1][1]
    _require(rows[0][0]["endpoint"] == "market-by-id" and rows[1][0]["endpoint"] == "book")
    _require(rows[0][0]["source_kind"] == "GAMMA" and rows[1][0]["source_kind"] == "CLOB")
    tokens = gamma["clobTokenIds"]
    if isinstance(tokens, str):
        tokens = json.loads(tokens, object_pairs_hook=_unique)
    _require(isinstance(tokens, list) and 1 <= len(tokens) <= 100 and len(set(tokens)) == len(tokens))
    _require(all(isinstance(t, str) and re.fullmatch(r"[0-9]{1,78}", t) for t in tokens))
    _require(isinstance(pair["market_id"], str) and re.fullmatch(r"[0-9]{1,20}", pair["market_id"]))
    _require(str(gamma["id"]) == pair["market_id"] and tokens[0] == pair["token_id"] == book["asset_id"])
    _require(isinstance(gamma["conditionId"], str) and re.fullmatch(r"0x[0-9a-fA-F]{64}", gamma["conditionId"]))
    _require(gamma["conditionId"] == book["market"])
    body = dict(schema="ts01-local-producer-witness-v1", market_id=pair["market_id"],
                token_id=pair["token_id"], attempts=ledger, selected=selected, transport_mode=pair["transport_mode"])
    _require(sha256_hex(_bounded_json(body)) == pair["receipt_sha256"])
    summary = dict(schema="ts02-offline-v1", proof_level="SYNTHETIC_ONLY",
        stage_a_provenance="INJECTED_UNVERIFIED", stage_a_sha256=sha256_hex(stage_a_text.encode("utf-8")),
        stage_a_bytes=len(stage_a_text.encode("utf-8")), market_id=pair["market_id"], token_id=pair["token_id"],
        condition_id=gamma["conditionId"], receipt_sha256=pair["receipt_sha256"],
        transport_mode=pair["transport_mode"], cutoff=deadline.isoformat(),
        sources=[{key: item[key] for key in ("occurrence_id", "raw_id", "raw_sha256", "byte_length", "received_at")} for item, _ in rows],
        expected_request_id=expected_request_id, strategy_parameter_names=names, max_sources=max_sources,
        output_contract_sha256=sha256_hex(_bounded_json(schema)))
    run_id = sha256_hex(_bounded_json(summary))
    handoff = dict(run_id=run_id, stage_a_id=run_id + ":A", stage_b_id=run_id + ":B",
                   summary=summary, UNTRUSTED_STAGE_A_TEXT=stage_a_text)
    _bounded_json(handoff)
    return handoff


def _terminal(status, run_id=None, handoff_sha256=None, output_sha256=None):
    return dict(status=status, run_id=run_id, proof_level="SYNTHETIC_ONLY",
                provider_toolfree="UNPROVEN", handoff_sha256=handoff_sha256, output_sha256=output_sha256)


def _sync_directory(path):
    if os.name != "nt":
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _write(path, body):
    payload = _bounded_json(body)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    _sync_directory(path.parent)


def _read(path):
    _require(not path.is_symlink() and path.is_file() and path.stat().st_nlink == 1)
    with path.open("rb") as stream:
        raw = stream.read(_LIMIT + 1)
    _require(len(raw) <= _LIMIT)
    value = json.loads(raw, object_pairs_hook=_unique)
    _require(_bounded_json(value) == raw)
    return value


def _root(path):
    root = Path(path).absolute()
    _require(not any(p.is_symlink() for p in (root, *root.parents)))
    return root


def verify_offline_run(output_dir, run_id):
    """Cold verify only; never repair, delete a reservation or dispatch a callback."""
    try:
        _require(isinstance(run_id, str) and re.fullmatch(r"[0-9a-f]{64}", run_id))
        root = _root(output_dir)
        reservation = _read(root / (run_id + ".reserved"))
        _require(set(reservation) == {"summary", "handoff_sha256"})
        _require(sha256_hex(_bounded_json(reservation["summary"])) == run_id)
        directory = root / run_id
        _require(not directory.is_symlink() and set(p.name for p in directory.iterdir()) == set(_FILES))
        previous = sha256_hex(_bounded_json(reservation))
        bodies = []
        for index, name in enumerate(_FILES):
            record = _read(directory / name)
            _require(set(record) == {"body", "previous_sha256", "sha256"})
            body = record["body"]
            _require(record["previous_sha256"] == previous)
            _require(record["sha256"] == sha256_hex(_bounded_json(dict(body=body, previous_sha256=previous))))
            bodies.append(body)
            previous = record["sha256"]
        summary = reservation["summary"]
        _require(bodies[0] == {key: summary[key] for key in ("stage_a_sha256", "stage_a_bytes", "stage_a_provenance")})
        _require(bodies[1] == reservation)
        _require(set(bodies[2]) == {"status", "output_sha256"} and bodies[2]["status"] in _STATUSES)
        output_hash = bodies[2]["output_sha256"]
        _require(output_hash is None or isinstance(output_hash, str) and re.fullmatch(r"[0-9a-f]{64}", output_hash))
        _require(bodies[2]["status"] != "OFFLINE_SYNTHETIC_VALIDATED" or output_hash is not None)
        expected = _terminal(bodies[2]["status"], run_id, reservation["handoff_sha256"], output_hash)
        _require(bodies[3] == expected)
        return expected
    except Exception:
        return _terminal("INCOMPLETE_BLOCKED")


def run_offline_two_stage(output_dir, *, stage_b, **inputs):
    """One injected offline callback at most per source-bound run in this journal.

    The operator must retain/protect the journal. Deleting all local evidence is
    outside its trust model; hashes are not signatures or provider attestations.
    """
    try:
        handoff = build_handoff(**inputs)
    except Exception:
        return _terminal("SOURCE_UNTRUSTED")
    run_id = handoff["run_id"]
    digest = sha256_hex(_bounded_json(handoff))
    summary = handoff["summary"]
    reservation = dict(summary=summary, handoff_sha256=digest)
    try:
        root = _root(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        marker = root / (run_id + ".reserved")
        directory = root / run_id
        if marker.exists() or marker.is_symlink() or directory.exists() or directory.is_symlink():
            result = verify_offline_run(root, run_id)
            _require(result["handoff_sha256"] == digest)
            return result
        # Exclusive-create is the permanent dispatch reservation, including partial writes.
        try:
            _write(marker, reservation)
        except FileExistsError:
            return verify_offline_run(root, run_id)
        directory.mkdir()
        _sync_directory(root)
        previous = sha256_hex(_bounded_json(reservation))
        def append(index, body):
            nonlocal previous
            record = dict(body=body, previous_sha256=previous)
            record["sha256"] = sha256_hex(_bounded_json(record))
            _write(directory / _FILES[index], record)
            previous = record["sha256"]
        append(0, {key: summary[key] for key in ("stage_a_sha256", "stage_a_bytes", "stage_a_provenance")})
        append(1, reservation)
        schema = build_strategy_research_draft_output_schema(expected_request_id=summary["expected_request_id"],
            max_sources=summary["max_sources"], strategy_parameter_names=summary["strategy_parameter_names"])
        status, output_hash = "INTERRUPTED_BLOCKED", None
        try:
            raw = stage_b(handoff=json.loads(_bounded_json(handoff)), output_contract=schema, expected_request_id=summary["expected_request_id"],
                          strategy_parameter_names=tuple(summary["strategy_parameter_names"]), tool_capabilities=())
        except Exception:
            pass  # A timeout/refusal/exception consumes the reserved slot permanently.
        else:
            status = "INVALID_OUTPUT"
            try:
                _require(isinstance(raw, (str, bytes)))
                raw = raw.encode("utf-8") if isinstance(raw, str) else raw
                _require(0 < len(raw) <= _LIMIT)
                output_hash = sha256_hex(raw)
                draft = validate_research_draft(raw, expected_request_id=summary["expected_request_id"],
                    max_sources=summary["max_sources"], strategy_mode=True,
                    strategy_parameter_names=summary["strategy_parameter_names"])
                _require(check_strategy_assessment_consistency(draft.strategy_projection.strategy_assessment))
                status = "OFFLINE_SYNTHETIC_VALIDATED"
            except Exception:
                pass
        append(2, dict(status=status, output_sha256=output_hash))
        append(3, _terminal(status, run_id, digest, output_hash))
        return verify_offline_run(root, run_id)
    except Exception:
        return _terminal("INCOMPLETE_BLOCKED")
