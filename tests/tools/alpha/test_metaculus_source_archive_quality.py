"""S10-R3-METACULUS-SRC-01: genuine vendored Metaculus source-archive code over cold-verified native SRC-01 sources.

The SRC-01 world is SANITIZED_SYNTHETIC (native fixtures from test_source_grounding). Direct vectors
are re-derived from the pinned upstream modules' own documented behaviour (canonicalize.py
docstring, quality.py BLOCK_SIGNATURES / MIN_TEXT_LEN / status>=400). Nothing here proves real
source quality lift, source authenticity or any forecast/trading value.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tomllib
import types

import pytest

from src.data_layer.analytical_research import metaculus_source_archive_bridge as MB
from src.data_layer.analytical_research import source_grounding as SG
from tests.data_layer.analytical_research.test_alpha_discovery import _pit_store
from tests.tools.alpha import test_source_grounding as TSG
from tools.alpha import run_metaculus_source_archive_quality as MQ
from tools.alpha import run_source_grounding as SGCLI

REPO_ROOT = Path(__file__).resolve().parents[3]
VENDOR = REPO_ROOT / "src" / "data_layer" / "analytical_research" / "metaculus_source_archive"
# SHA-256 of the pinned upstream bytes (Metaculus/forecasting-tools@a54dd64), fetched independently at implementation.
UPSTREAM_SHA256 = {
    "LICENSE": "381e7c01be4ef601bdcc0608a0b11d27ef9dfacb2feee7da658eb97e29c998ed",
    "canonicalize.py": "dc58daf8f3bf77b4d6c94f08dc0d30ea679aa81e5c2a7611e43f3e65992e4fdb",
    "models.py": "9a3238598f7e28bd1513a59df00b9ede4a1ad3493727f2a981cfbcc97f68f15b",
    "quality.py": "2bb58bd8c7b449a39dc0ec5423b3af3080144e1bcbaa30ab5dc3c6401e9567ce",
}
# Native SRC-01 code identity on main 439dcfb: the historical modules must stay byte-identical.
SRC_CODE_IDENTITY = "code:sha256:79ab2243eb9f86d9dbcf07ed117b2701848b9cfb0a2318a78feeb7d1b3bd364d"
GOOD = TSG.GOOD_HTML
OTHER = TSG.FED_TEXT
UNICODE = ("<html><body><h2>Indice des prix à la consommation</h2><p>" + "Le rapport mensuel de l'indice des prix "
           "a été publié — données révisées, méthodologie inchangée ✓ " * 4 + "</p></body></html>").encode("utf-8")
SECRETISH = GOOD + ("gh" + "p_" + "q" * 30).encode()  # assembled at runtime so no literal token sits in the repo
BASE = "https://example.invalid/cpi"


def _sources(put):
    def s(label, slug, data, url, **overrides):
        return TSG._source(label, slug, put(f"{label}-{hashlib.sha256(url.encode()).hexdigest()[:8]}.bin", data), data, url=url, **overrides)
    return [
        s("good-a", "cpi", GOOD, "https://Example.invalid:443/cpi/?utm_source=news&b=2&a=1"),
        s("good-a-alias", "cpi", GOOD, BASE + "?a=1&b=2"),                      # native DEDUPED; same url_hash
        s("page-2", "cpi", OTHER, BASE + "?a=1&b=2&page=2", media_type="text/plain"),  # distinct non-tracking param
        s("not-found", "cpi", GOOD, BASE + "/missing", http_status=404),
        s("redirect", "cpi", GOOD, BASE + "/moved", http_status=302),
        s("continue", "cpi", GOOD, BASE + "/continue", http_status=100),
        s("server-error", "cpi", GOOD, BASE + "/err", http_status=503),
        s("thin", "cpi", b"<p>short note</p>", BASE + "/thin"),
        s("block", "cpi", TSG.BLOCK_PAGE, BASE + "/block"),
        s("login", "cpi", TSG.LOGIN_PAGE, BASE + "/login"),
        s("interstitial", "cpi", TSG.INTERSTITIAL, BASE + "/check"),
        s("unicode", "fed-hold-sep", UNICODE, "https://example.invalid/fed"),
        s("bad-utf8", "cpi", b"\xff\xfe" + b"a" * 300, BASE + "/bin"),
        s("future", "cpi", OTHER, BASE + "/future", source_publish_time="2026-07-01T00:00:00Z",
          public_available_time="2026-07-01T00:00:00Z"),
        s("unsafe-url", "cpi", OTHER, BASE + "?token=abc"),
        s("empty", "cpi", b"", BASE + "/empty"),
        s("secretish", "gdp", SECRETISH, "https://example.invalid/gdp"),
        s("cross-market", "nba-celtics", GOOD, BASE + "?b=2&a=1"),             # same url_hash, other market
        s("good-a", "cpi", OTHER, BASE + "/dup-label"),                        # duplicate label
        s("no-status", "cpi", OTHER, BASE + "/nostatus", http_status=None),
        s("no-ingest", "cpi", OTHER, BASE + "/noclock", ingestion_time=None),  # missing native clock
    ]


def make_world(base: Path, corpus_class="SANITIZED_SYNTHETIC"):
    pit = _pit_store(base, TSG._pit_records())

    def put(name, data):
        path = (base / name).resolve()
        path.write_bytes(data)
        return path
    queries = [{"query_id": q, "text": t, "category_hint": c, "relevant_market_ids": [TSG._mid(x) for x in rel]}
               for q, t, c, rel in TSG.QUERIES]
    case = {"schema_id": SG.CASE_SCHEMA, "case_label": "mcsrc-synthetic", "corpus_class": corpus_class,
            "pit_store": str(pit), "alpha_registry": None, "policy": TSG._policy_mapping(), "as_of": TSG.AS_OF,
            "rule_texts": [], "sources": _sources(put), "queries": queries}
    case_path = base / "case.json"
    case_path.write_text(json.dumps(case), encoding="utf-8")
    return case_path


def run_src(base: Path, corpus_class="SANITIZED_SYNTHETIC") -> Path:
    inputs = base / "inputs"
    inputs.mkdir(parents=True)
    scratch = (base / "src").resolve()
    assert SGCLI.main(["run", "--case", str(make_world(inputs, corpus_class)), "--scratch-dir", str(scratch)]) == 0
    return scratch


def run_quality(src, scratch, capsys=None):
    code = MQ.main(["run", "--src-scratch", str(src), "--scratch-dir", str(scratch)])
    output = json.loads(capsys.readouterr().out.strip().splitlines()[-1]) if capsys else None
    path = Path(scratch) / "receipt.json"
    return code, output, json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def rows(receipt):
    return {(r["index"], r["source_label"]): r for r in receipt["core"]["results"]}


def by_label(receipt):
    out = {}
    for r in receipt["core"]["results"]:
        out.setdefault(r["source_label"], r)
    return out


def tree_hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}


def fresh_loader(monkeypatch):
    """Force a cold load; monkeypatch restores sys.modules and the cache consistently at teardown."""
    for name in MB.MODULE_NAMES:
        monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setattr(MB, "_LOADED", {})


def vendor_copy(tmp_path, monkeypatch, mutate=None):
    target = tmp_path / "vendor" / "metaculus_source_archive"
    target.mkdir(parents=True)
    for name in MB.VENDOR_PINS:
        shutil.copyfile(VENDOR / name, target / name)
    if mutate:
        mutate(target)
    fresh_loader(monkeypatch)
    monkeypatch.setattr(MB, "vendor_dir", lambda: target)
    return target


@pytest.fixture(scope="module")
def src(tmp_path_factory):
    return run_src(tmp_path_factory.mktemp("mc_src"))


@pytest.fixture(scope="module")
def quality(src, tmp_path_factory):
    scratch = tmp_path_factory.mktemp("mc_q") / "scratch"
    code, output, receipt = run_quality(src, scratch)
    assert code == 0, output
    return scratch, receipt


# ------------------------------------------------------------------ R001


def test_metaculus_exact_source_license_and_dependency_closure():
    assert sorted(p.name for p in VENDOR.iterdir() if p.name != "__pycache__") == sorted(MB.VENDOR_PINS)
    assert not (VENDOR / "__init__.py").exists()  # the heavy upstream package initializer is never vendored
    for name, pin in MB.VENDOR_PINS.items():
        data = (VENDOR / name).read_bytes()
        assert MB.git_blob_sha1(data) == pin
        assert hashlib.sha256(data).hexdigest() == UPSTREAM_SHA256[name]
        assert b"\r\n" not in data
    license_text = (VENDOR / "LICENSE").read_text(encoding="utf-8")
    assert license_text.startswith("MIT License\n\nCopyright (c) 2024 CodexVeritas\n")
    assert "The above copyright notice and this permission notice shall be included" in license_text
    for _, filename in MB.MODULE_FILES:
        assert MB.import_closure((VENDOR / filename).read_bytes()) == MB.IMPORT_CLOSURE[filename]
    stdlib = set(sys.stdlib_module_names)
    for names in MB.IMPORT_CLOSURE.values():
        for name in names:
            assert name.split(".")[0] in stdlib or name == "pydantic" or name.startswith(MB.PACKAGE + ".")
    assert MB._require_pydantic().split(".")[0] == "2"
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    deps = project["dependencies"]
    assert "polymarket-client==0.10.0" in deps
    assert not any("forecasting" in d.casefold() or d.casefold().startswith("pydantic") for d in deps)
    assert any(r.replace(" ", "").startswith("pydantic") for r in importlib.metadata.requires("polymarket-client") or [])
    with pytest.raises(importlib.metadata.PackageNotFoundError):
        importlib.metadata.distribution("forecasting-tools")
    identity = MB.upstream_identity()
    assert identity["commit"] == "a54dd6443d19745b267e99a3b0b7627e74b9a57a" and identity["license"] == "MIT"
    assert identity["git_blob_sha1"] == MB.VENDOR_PINS


# ------------------------------------------------------------------ R002


def test_metaculus_actual_vendor_functions_invoked(src, tmp_path, monkeypatch, capsys):
    canonicalize, models, quality = MB.load_upstream()
    for module, filename in ((canonicalize, "canonicalize.py"), (models, "models.py"), (quality, "quality.py")):
        assert Path(module.__file__) == VENDOR / filename
        assert sys.modules[module.__name__] is module
        assert module.__name__ == f"{MB.PACKAGE}.{filename[:-3]}"
    assert quality.CaptureResult is models.CaptureResult  # upstream absolute import resolved to the vendored module
    assert models.canonicalize_url is canonicalize.canonicalize_url
    for func, filename in ((quality.evaluate, "quality.py"), (models.url_hash, "models.py"),
                           (models.content_hash, "models.py"), (canonicalize.canonicalize_url, "canonicalize.py")):
        assert Path(func.__code__.co_filename) == VENDOR / filename
    assert not hasattr(sys.modules[MB.PACKAGE], "__file__") or sys.modules[MB.PACKAGE].__file__ is None
    assert sys.modules[MB.PACKAGE].__path__ == []
    assert "pydantic" in sys.modules and issubclass(models.CaptureResult, sys.modules["pydantic"].BaseModel)

    # Spy on the real upstream callables: the production CLI must reach every one of them.
    seen = {name: 0 for name in MB.INVOKED}

    def spy(owner, attr, key):
        original = getattr(owner, attr)

        def wrapper(*args, **kwargs):
            seen[key] += 1
            return original(*args, **kwargs)
        monkeypatch.setattr(owner, attr, wrapper)
    spy(quality, "evaluate", "quality.evaluate")
    spy(models, "url_hash", "models.url_hash")
    spy(models, "content_hash", "models.content_hash")
    spy(models, "canonicalize_url", "canonicalize.canonicalize_url")  # the name url_hash calls internally
    spy(canonicalize, "canonicalize_url", "canonicalize.canonicalize_url")
    original_init = models.CaptureResult.__init__

    def init(self, **kwargs):
        seen["models.CaptureResult"] += 1
        original_init(self, **kwargs)
    monkeypatch.setattr(models.CaptureResult, "__init__", init)
    code, output, receipt = run_quality(src, tmp_path / "scratch", capsys)
    assert code == 0 and output["status"] == "RUN_COMPLETE"
    evaluated = receipt["core"]["counts"]["upstream_evaluated"]
    assert evaluated > 0 and output["quality_evaluate_invocations"] == evaluated
    calls = receipt["core"]["invocations"]
    for name in ("quality.evaluate", "models.url_hash", "models.content_hash", "models.CaptureResult",
                 "canonicalize.canonicalize_url"):
        assert seen[name] == calls[name], name
    assert calls["canonicalize.canonicalize_url"] == 2 * evaluated
    # Every recorded upstream outcome equals a fresh direct call on the same frozen bytes and view.
    case = json.loads((tmp_path / "scratch" / "inputs" / "src" / "frozen_case.json").read_text(encoding="utf-8"))
    for row in receipt["core"]["results"]:
        if row["verdict"] != "UPSTREAM_EVALUATED":
            continue
        entry = case["sources"][row["index"]]
        raw = (tmp_path / "scratch" / "inputs" / "src" / "inputs" / entry["file"]).read_bytes()
        text = SG._visible_text(raw)
        verdict = quality.evaluate(models.CaptureResult(url=entry["url"], final_url=entry["url"],
                                                        status_code=entry["http_status"], markdown=text))
        assert (verdict.passed, verdict.reason or None) == (row["upstream_passed"], row["upstream_reason"])
        assert row["url_hash"] == models.url_hash(entry["url"]) == hashlib.sha256(
            canonicalize.canonicalize_url(entry["url"]).encode()).hexdigest()
        assert row["capture_content_hash"] == hashlib.sha256(text.encode()).hexdigest()
    # A substituted evaluator changes the receipt: the vendored function is the one actually used.
    monkeypatch.setattr(quality, "evaluate", lambda result, **_: quality.QualityVerdict(passed=True))
    _, _, forged = run_quality(src, tmp_path / "forged")
    assert forged["core"]["counts"]["upstream_passed"] == evaluated != receipt["core"]["counts"]["upstream_passed"]


# ------------------------------------------------------------------ R003


def test_metaculus_verified_src01_native_source_consumer(src, quality, tmp_path, capsys):
    assert SGCLI.code_identity() == SRC_CODE_IDENTITY
    before = tree_hashes(src)
    scratch, receipt = quality
    assert tree_hashes(src) == before  # the native scratch is read-only input
    assert SGCLI.verify(src)["status"] == "VERIFIED"
    src_receipt = json.loads((src / "receipt.json").read_text(encoding="utf-8"))
    inputs = receipt["core"]["inputs"]
    assert inputs["src_receipt_id"] == src_receipt["receipt_id"] and inputs["src_verification"] == "VERIFIED"
    assert inputs["src_wp_id"] == "S10-R3-SRC-01" and inputs["src_code_identity"] == src_receipt["core"]["code_identity"]
    assert inputs["file_sha256"] == tree_hashes(src)
    assert receipt["receipt_id"].startswith(MQ.RECEIPT_PREFIX)
    assert sorted(p.name for p in scratch.iterdir()) == ["inputs", "receipt.json"]
    assert len(receipt["core"]["results"]) == len(src_receipt["core"]["sources"]["entries"])
    # A native scratch that no longer verifies is refused before any upstream call.
    broken = tmp_path / "broken"
    shutil.copytree(src, broken)
    (broken / "inputs" / "sources" / "000.bin").write_bytes(GOOD + b" tampered")
    code, output, _ = run_quality(broken, tmp_path / "s1", capsys)
    assert code == 1 and output == {"status": "STOPPED", "reason_code": "SRC_RECEIPT_NOT_VERIFIED"}
    # LOCAL_REAL_PIT stays caller-local, unauthenticated evidence.
    real_src = run_src(tmp_path / "real", "LOCAL_REAL_PIT")
    code, _, real = run_quality(real_src, tmp_path / "s2")
    assert code == 0 and real["core"]["inputs"]["corpus_class"] == "LOCAL_REAL_PIT"
    assert real["core"]["inputs"]["origin_authentication"] == "CALLER_LOCAL_UNAUTHENTICATED"
    assert real["core"]["counts"]["authenticated_web_evidence"] == 0
    assert all(r["authenticated_web_evidence"] is False for r in real["core"]["results"])


# ------------------------------------------------------------------ R004


def test_metaculus_quality_url_dedup_and_native_admission_boundaries(src, quality):
    _, receipt = quality
    src_receipt = json.loads((src / "receipt.json").read_text(encoding="utf-8"))
    native = src_receipt["core"]["sources"]["entries"]
    for row in receipt["core"]["results"]:
        assert (row["native_status"], row["native_reason"]) == (native[row["index"]]["status"], native[row["index"]]["reason"])
        assert row["promotes_native_status"] is False and row["authenticated_web_evidence"] is False
    labels = by_label(receipt)
    expect = {
        "good-a": ("ACCEPTED", "AGREE_PASS"), "good-a-alias": ("DEDUPED", "AGREE_PASS"),
        "page-2": ("ACCEPTED", "AGREE_PASS"), "not-found": ("QUALITY_FAILED", "AGREE_FAIL"),
        "redirect": ("QUALITY_FAILED", "UPSTREAM_PASS_NATIVE_FAIL"),
        "continue": ("QUALITY_FAILED", "UPSTREAM_PASS_NATIVE_FAIL"),
        "server-error": ("QUALITY_FAILED", "AGREE_FAIL"), "thin": ("QUALITY_FAILED", "AGREE_FAIL"),
        "block": ("QUALITY_FAILED", "AGREE_FAIL"), "login": ("QUALITY_FAILED", "UPSTREAM_PASS_NATIVE_FAIL"),
        "interstitial": ("QUALITY_FAILED", "AGREE_FAIL"), "unicode": ("ACCEPTED", "AGREE_PASS"),
        "cross-market": ("ACCEPTED", "AGREE_PASS"),
    }
    for label, (status, agreement) in expect.items():
        assert (labels[label]["native_status"], labels[label]["agreement"]) == (status, agreement), label
    assert labels["redirect"]["native_reason"] == "HTTP_STATUS_302" and labels["redirect"]["upstream_passed"] is True
    assert labels["login"]["native_reason"] == "LOGIN_WALL" and labels["login"]["upstream_reason"] is None
    # Native refusals before quality never reach upstream and never gain authority.
    abstain = {"bad-utf8": "INVALID_UTF8_OR_NUL", "future": "NATIVE_PRE_QUALITY_REFUSED:FUTURE_CONTENT",
               "unsafe-url": "NATIVE_PRE_QUALITY_REFUSED:SOURCE_URL_UNSAFE",
               "empty": "NATIVE_PRE_QUALITY_REFUSED:SOURCE_MISSING_OR_EMPTY",
               "secretish": "SECRET_SHAPED_CONTENT",
               "no-ingest": "NATIVE_PRE_QUALITY_REFUSED:SOURCE_INGESTION_CLOCK_MISSING", 19: "NATIVE_PRE_QUALITY_REFUSED:SOURCE_FIELDS_INVALID"}
    for label, reason in abstain.items():
        row = receipt["core"]["results"][label] if type(label) is int else labels[label]  # 19: no-status row has no label
        assert (row["verdict"], row["reason"], row["upstream_passed"], row["url_hash"]) == ("ABSTAINED", reason, None, None)
    dup = rows(receipt)[(18, "good-a")]
    assert dup["reason"] == "NATIVE_PRE_QUALITY_REFUSED:CONFLICTING_SOURCE_IDENTITY"
    assert labels["secretish"]["native_status"] == "ACCEPTED"  # native admits it; the comparison still refuses to touch it
    # URL identity: upstream canonical key is separate from native URL safety / per-market dedup.
    a, alias, cross, page = (labels[k] for k in ("good-a", "good-a-alias", "cross-market", "page-2"))
    assert a["url_hash"] == alias["url_hash"] == cross["url_hash"] != page["url_hash"]
    assert a["url_canonical_changed"] is True and alias["url_canonical_changed"] is False
    assert cross["market_id"] != a["market_id"] and cross["native_status"] == "ACCEPTED"
    assert receipt["core"]["dedup"] == {
        "evaluated": 13, "distinct_url_hash": 11, "url_alias_collapsed": 2, "url_canonical_changed": 2,
        "url_hash_same_content_differs": 0, "url_hash_spans_markets": 1, "distinct_capture_content_hash": 7,
        "upstream_url_content_duplicates": 2, "native_deduped": 1, "dedup_disagreements": 1,
        "upstream_content_hash_mismatch": 0}
    assert all(r["upstream_content_hash_matches_native"] for r in receipt["core"]["results"] if r["verdict"] == "UPSTREAM_EVALUATED")
    assert receipt["core"]["counts"]["native_accepted"] == src_receipt["core"]["sources"]["counts"].get("ACCEPTED")
    assert receipt["core"]["counts"]["promoted_by_upstream"] == 0


# ------------------------------------------------------------------ R005


def test_metaculus_upstream_aligned_quality_and_canonicalization_vectors(quality):
    canonicalize, models, quality_mod = MB.load_upstream()
    body = "x" * 200

    def evaluate(status, text):
        verdict = quality_mod.evaluate(models.CaptureResult(url="https://a.invalid", final_url="https://a.invalid",
                                                            status_code=status, markdown=text, fetched_at="t"))
        return verdict.passed, verdict.reason
    assert evaluate(200, body) == (True, "")
    assert evaluate(None, body) == (True, "")            # no status is not gated upstream
    assert evaluate(302, body) == (True, "")             # redirects pass upstream; native fails non-2xx
    assert evaluate(399, body) == (True, "")
    assert evaluate(400, body) == (False, "http_status=400")
    assert evaluate(404, body) == (False, "http_status=404")
    assert evaluate(503, body) == (False, "http_status=503")
    assert evaluate(200, "x" * 199) == (False, "thin_content len=199")
    assert evaluate(200, "   " + "x" * 199 + "   ") == (False, "thin_content len=199")  # stripped first
    assert evaluate(200, None) == (False, "thin_content len=0")
    for sig in quality_mod.BLOCK_SIGNATURES:
        assert evaluate(200, body + " " + sig.upper()) == (False, f"block_signature={sig!r}")
    assert evaluate(200, body + " please log in to continue") == (True, "")  # login walls are a native-only extension
    assert evaluate(200, "é" * 200) == (True, "")                            # Unicode length is characters
    assert quality_mod.MIN_TEXT_LEN == SG.MIN_TEXT_LEN == 200
    assert tuple(quality_mod.BLOCK_SIGNATURES) == SG.BLOCK_SIGNATURES       # native adaptation stayed faithful
    html_only = models.CaptureResult(url="u", final_url="u", html="<p>" + body + "</p>", fetched_at="t")
    assert quality_mod.evaluate(html_only).passed is True                    # markdown or html
    c = canonicalize.canonicalize_url
    vectors = {
        "HTTPS://Example.COM:443/a/?utm_source=x&b=2&a=1#frag": "https://example.com/a?a=1&b=2",
        "http://example.com:80/": "http://example.com",
        "http://example.com:8080/x/": "http://example.com:8080/x",
        "https://example.com/x?gclid=1&FBCLID=2&utm_campaign=y&ref=keep&source=keep": "https://example.com/x?ref=keep&source=keep",
        "https://example.com/x?page=2": "https://example.com/x?page=2",
        "https://www.example.com/x": "https://www.example.com/x",
        "mailto:a@example.com": "mailto:a@example.com",
        "  https://example.com/x  ": "https://example.com/x",
        "http://[::1/x": "http://[::1/x",  # unparsable netloc is returned stripped, unchanged
        "": "",
    }
    for raw, expected in vectors.items():
        assert c(raw) == expected, raw
        assert c(c(raw)) == c(raw)
    assert c("http://example.com/x") != c("https://example.com/x")  # no scheme upgrade
    assert models.url_hash("https://example.com/x/?utm_medium=a#f") == models.url_hash("https://EXAMPLE.com/x")
    assert models.url_hash("https://example.com/x?a=1") != models.url_hash("https://example.com/x?a=2")
    assert models.content_hash("abc") == models.content_hash(b"abc") == hashlib.sha256(b"abc").hexdigest()
    assert models.content_hash("abc") != models.content_hash("abd")
    assert models.CaptureResult(url="u", final_url="f", markdown="m", fetched_at="t").content_hash == hashlib.sha256(b"m").hexdigest()
    assert models.CaptureResult(url="u", final_url="f", fetched_at="t").content_hash == hashlib.sha256(b"f").hexdigest()
    # Exact denominators over the native world; no quality-lift claim is made.
    _, receipt = quality
    counts = receipt["core"]["counts"]
    assert counts == {
        "sources_total": 21, "upstream_evaluated": 13, "abstained": 8,
        "abstention_reasons": {"INVALID_UTF8_OR_NUL": 1, "NATIVE_PRE_QUALITY_REFUSED:CONFLICTING_SOURCE_IDENTITY": 1,
                               "NATIVE_PRE_QUALITY_REFUSED:FUTURE_CONTENT": 1,
                               "NATIVE_PRE_QUALITY_REFUSED:SOURCE_FIELDS_INVALID": 1,
                               "NATIVE_PRE_QUALITY_REFUSED:SOURCE_INGESTION_CLOCK_MISSING": 1,
                               "NATIVE_PRE_QUALITY_REFUSED:SOURCE_MISSING_OR_EMPTY": 1,
                               "NATIVE_PRE_QUALITY_REFUSED:SOURCE_URL_UNSAFE": 1, "SECRET_SHAPED_CONTENT": 1},
        "upstream_passed": 8, "native_quality_passed": 5, "agree_pass": 5, "agree_fail": 5,
        "divergent_upstream_pass_native_fail": 3, "divergent_upstream_fail_native_pass": 0, "divergent_total": 3,
        "divergent_non_2xx_upstream_pass": 2,
        "upstream_reasons": {"PASSED": 8, "block_signature": 2, "http_status": 2, "thin_content": 1},
        "native_accepted": 5, "promoted_by_upstream": 0, "authenticated_web_evidence": 0}
    assert receipt["core"]["adoption"]["value_status"] == "OPERATIONAL_USEFULNESS_NOT_VERIFIED"


# ------------------------------------------------------------------ R006


def _rewrite(path, mutate, *, reid=False):
    receipt = json.loads(path.read_text(encoding="utf-8"))
    mutate(receipt)
    if reid:
        receipt["receipt_id"] = MQ.finalize(receipt["core"])["receipt_id"]
    path.write_text(json.dumps(receipt), encoding="utf-8")


def _verify(scratch, capsys):
    code = MQ.main(["verify", "--scratch-dir", str(scratch)])
    return code, json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def test_metaculus_receipt_cold_verify_idempotency_and_tamper(src, quality, tmp_path, monkeypatch, capsys):
    scratch, receipt = quality
    raw_receipt = (scratch / "receipt.json").read_bytes()
    assert MQ.finalize(receipt["core"])["receipt_id"] == receipt["receipt_id"]
    upstream = receipt["core"]["upstream"]
    assert upstream["git_blob_sha1"] == MB.VENDOR_PINS and upstream["sha256"] == UPSTREAM_SHA256
    assert set(receipt["core"]["invocations"]) == set(MB.INVOKED)
    # Cold verify re-invokes the real upstream code with every socket blocked.
    fresh_loader(monkeypatch)
    blocked = []
    original = socket.create_connection
    monkeypatch.setattr(MB, "load_upstream", (lambda load: lambda: (blocked.append(
        socket.create_connection is not original), load())[1])(MB.load_upstream))
    assert _verify(scratch, capsys) == (0, {"status": "VERIFIED", "failures": [], "receipt_id": receipt["receipt_id"],
                                            "network_attempts": 0})
    assert blocked == [True]
    # Identical replay is idempotent and writes nothing.
    code, output, _ = run_quality(src, scratch, capsys)
    assert (code, output["status"]) == (0, "IDEMPOTENT_VERIFIED") and (scratch / "receipt.json").read_bytes() == raw_receipt
    # A second independent run over the same SRC bytes reproduces the identical receipt id.
    _, _, again = run_quality(src, tmp_path / "again")
    assert again["receipt_id"] == receipt["receipt_id"]
    # Changed native input over an existing receipt refuses.
    changed = tmp_path / "changed-src"
    shutil.copytree(src, changed)
    (changed / "frozen_case.json").write_bytes((changed / "frozen_case.json").read_bytes() + b" ")
    code, output, _ = run_quality(changed, scratch, capsys)
    assert (code, output) == (1, {"status": "STOPPED", "reason_code": "SCRATCH_NOT_EMPTY"})
    # A partially written scratch (inputs but no receipt) refuses.
    partial = tmp_path / "partial"
    (partial / "inputs").mkdir(parents=True)
    code, output, _ = run_quality(src, partial, capsys)
    assert (code, output) == (1, {"status": "STOPPED", "reason_code": "SCRATCH_NOT_EMPTY"})
    # Receipt tamper: id-only, re-id'd body change, false provenance, copied source bytes, extra key.
    cases = {
        "id": (lambda r: r.update(receipt_id=MQ.RECEIPT_PREFIX + "0" * 64), False, ["RECEIPT_ID_MISMATCH"]),
        "count": (lambda r: r["core"]["counts"].update(upstream_passed=99), True, ["OUTPUT_MISMATCH:counts"]),
        "provenance": (lambda r: r["core"]["inputs"].update(origin_authentication="AUTHENTICATED_WEB"), True,
                       ["OUTPUT_MISMATCH:inputs"]),
        "promotion": (lambda r: r["core"]["results"][9].update(native_status="ACCEPTED"), True, ["OUTPUT_MISMATCH:results"]),
        "extra": (lambda r: r.update(note="accepted"), False, ["RECEIPT_SHAPE_INVALID"]),
    }
    for name, (mutate, reid, failures) in cases.items():
        target = tmp_path / f"t-{name}"
        shutil.copytree(scratch, target)
        _rewrite(target / "receipt.json", mutate, reid=reid)
        code, output = _verify(target, capsys)
        assert (code, output["status"], output["failures"]) == (1, "TAMPER_DETECTED", failures), name
    target = tmp_path / "t-bytes"
    shutil.copytree(scratch, target)
    (target / "inputs" / "src" / "inputs" / "sources" / "009.bin").write_bytes(GOOD)
    code, output = _verify(target, capsys)
    assert (code, output["failures"]) == (1, ["RECOMPUTE_REFUSED:SRC_RECEIPT_NOT_VERIFIED"])
    # The copied SRC tree is still re-hashed by the derived receipt itself.
    target = tmp_path / "t-extra-file"
    shutil.copytree(scratch, target)
    (target / "inputs" / "src" / "planted.txt").write_bytes(b"x")
    code, output = _verify(target, capsys)
    assert (code, output["failures"]) == (1, ["OUTPUT_MISMATCH:inputs"])


# ------------------------------------------------------------------ R007


def test_metaculus_negative_safety_and_import_collision(src, quality, tmp_path, monkeypatch, capsys):
    scratch, receipt = quality

    def stop(code):
        return pytest.raises(MB.MetaculusStop, match=f"^{code}$")
    # Wrong blobs, missing license, planted package initializer, symlink/hardlink vendored files.
    for mutate, code in (
            (lambda d: (d / "quality.py").write_bytes((d / "quality.py").read_bytes().replace(b"MIN_TEXT_LEN = 200", b"MIN_TEXT_LEN = 1")),
             "UPSTREAM_BLOB_MISMATCH"),
            (lambda d: (d / "LICENSE").unlink(), "UPSTREAM_FILE_MISSING"),
            (lambda d: (d / "__init__.py").write_bytes(b""), "UPSTREAM_VENDOR_DIR_UNEXPECTED_FILE"),
            (lambda d: os.link(d / "models.py", d.parent / "models-link.py"), "UPSTREAM_FILE_UNSAFE")):
        with monkeypatch.context() as m:
            vendor_copy(tmp_path / code / str(id(mutate)), m, mutate)
            with stop(code):
                MB.load_upstream()
    # Import-closure drift and dynamic imports are detected statically, before any byte executes.
    models_src = (VENDOR / "models.py").read_bytes()
    assert MB.import_closure(models_src + b"\nimport os\n") != MB.IMPORT_CLOSURE["models.py"]
    assert "<dynamic>" in MB.import_closure(b"__import__('socket')\n")
    assert "<dynamic>" in MB.import_closure(b"import importlib\nimportlib.import_module('socket')\n")
    with monkeypatch.context() as m:
        vendor_copy(tmp_path / "closure", m)
        m.setattr(MB, "IMPORT_CLOSURE", dict(MB.IMPORT_CLOSURE, **{"models.py": {"__future__"}}))
        with stop("UPSTREAM_IMPORT_CLOSURE_DRIFT"):
            MB.load_upstream()
    # Pydantic missing or incompatible.
    for fake, code in ((None, "PYDANTIC_UNAVAILABLE"), (types.SimpleNamespace(VERSION="1.10.13"), "PYDANTIC_INCOMPATIBLE")):
        with monkeypatch.context() as m:
            fresh_loader(m)
            m.setitem(sys.modules, "pydantic", fake)
            with stop(code):
                MB.load_upstream()
    # Foreign preloaded aliases are never overwritten.
    for name in MB.MODULE_NAMES:
        with monkeypatch.context() as m:
            fresh_loader(m)
            foreign = types.ModuleType(name)
            m.setitem(sys.modules, name, foreign)
            with stop("UPSTREAM_ALIAS_COLLISION"):
                MB.load_upstream()
            assert sys.modules[name] is foreign
    # A failing upstream import leaves no half-registered module behind.
    with monkeypatch.context() as m:
        vendor_copy(tmp_path / "boom", m)
        m.setattr(MB, "PACKAGE_STUBS", MB.PACKAGE_STUBS)
        real_compile = compile
        m.setattr("builtins.compile", lambda src_, name, *a, **k: (_ for _ in ()).throw(SyntaxError("x"))
                  if name.endswith("quality.py") else real_compile(src_, name, *a, **k))
        with stop("UPSTREAM_IMPORT_FAILED"):
            MB.load_upstream()
        assert not any(name in sys.modules for name in MB.MODULE_NAMES)
    # Caller path boundaries: relative, in-repo, scratch-inside-source, symlinked or hardlinked SRC files.
    refusals = [
        (["run", "--src-scratch", "relative/src", "--scratch-dir", str(tmp_path / "r1")], "SRC_SCRATCH_UNUSABLE"),
        (["run", "--src-scratch", str(REPO_ROOT / "docs"), "--scratch-dir", str(tmp_path / "r2")], "SRC_SCRATCH_UNUSABLE"),
        (["run", "--src-scratch", str(src), "--scratch-dir", str(REPO_ROOT / "mc-scratch")], "SCRATCH_INSIDE_REPOSITORY"),
        (["run", "--src-scratch", str(src), "--scratch-dir", str(src / "nested")], "SRC_SCRATCH_UNUSABLE"),
        (["verify", "--scratch-dir", "relative"], "SCRATCH_INVALID"),
    ]
    linked = tmp_path / "linked"
    shutil.copytree(src, linked)
    os.link(linked / "inputs" / "sources" / "000.bin", tmp_path / "outside-link.bin")
    refusals.append((["run", "--src-scratch", str(linked), "--scratch-dir", str(tmp_path / "r3")], "SRC_SCRATCH_UNSAFE"))
    for argv, code in refusals:
        assert MQ.main(argv) == 1
        assert json.loads(capsys.readouterr().out) == {"status": "STOPPED", "reason_code": code}, argv
    assert not (REPO_ROOT / "mc-scratch").exists()
    try:
        sym = tmp_path / "sym"
        shutil.copytree(src, sym)
        (sym / "inputs" / "sources" / "001.bin").unlink()
        os.symlink(src / "inputs" / "sources" / "001.bin", sym / "inputs" / "sources" / "001.bin")
    except OSError:
        sym = None  # symlink creation needs privilege on some Windows hosts; hardlink case above still runs
    if sym is not None:
        assert MQ.main(["run", "--src-scratch", str(sym), "--scratch-dir", str(tmp_path / "r4")]) == 1
        assert json.loads(capsys.readouterr().out)["reason_code"] == "SRC_SCRATCH_UNSAFE"
    # Size / count limits.
    with monkeypatch.context() as m:
        m.setattr(MQ, "MAX_SRC_FILES", 2)
        assert MQ.main(["run", "--src-scratch", str(src), "--scratch-dir", str(tmp_path / "r5")]) == 1
        assert json.loads(capsys.readouterr().out)["reason_code"] == "SRC_SCRATCH_TOO_LARGE"
    # Duplicate JSON keys / nonfinite values / invalid UTF-8 / depth in the derived receipt.
    for name, payload, code in (("dup", b'{"core": {}, "core": {}, "receipt_id": "x"}', "RECEIPT_UNREADABLE"),
                                ("nan", b'{"core": {"x": NaN}, "receipt_id": "x"}', "RECEIPT_UNREADABLE"),
                                ("utf8", b'{"core": "\xff"}', "RECEIPT_UNREADABLE")):
        target = tmp_path / f"j-{name}"
        shutil.copytree(scratch, target)
        (target / "receipt.json").write_bytes(payload)
        assert MQ.main(["verify", "--scratch-dir", str(target)]) == 1
        assert json.loads(capsys.readouterr().out) == {"status": "STOPPED", "reason_code": code}, name
    # Pathologically deep JSON fails closed either way: some CPython builds raise RecursionError while parsing
    # (RECEIPT_UNREADABLE), others parse it and the shape check refuses it.
    target = tmp_path / "j-deep"
    shutil.copytree(scratch, target)
    (target / "receipt.json").write_bytes(b"[" * 100000 + b"]" * 100000)
    assert MQ.main(["verify", "--scratch-dir", str(target)]) == 1
    assert json.loads(capsys.readouterr().out) in (
        {"status": "STOPPED", "reason_code": "RECEIPT_UNREADABLE"},
        {"status": "TAMPER_DETECTED", "failures": ["RECEIPT_SHAPE_INVALID"], "receipt_id": None, "network_attempts": 0})
    # Hash-mismatched frozen source behind a matching native receipt hash, and misaligned source rows.
    case = json.loads((src / "frozen_case.json").read_text(encoding="utf-8"))
    src_core = json.loads((src / "receipt.json").read_text(encoding="utf-8"))["core"]
    with stop("SRC_SOURCE_ROWS_MISALIGNED"):
        MB.assess_sources(dict(case, sources=case["sources"][:-1]), src_core, lambda rel: b"")
    with stop("SRC_INPUT_HASH_MISMATCH"):
        forged = copy.deepcopy(src_core)
        forged["inputs"]["file_sha256"]["sources/000.bin"] = "0" * 64
        target = tmp_path / "hash"
        shutil.copytree(src, target / "src")
        (target / "src" / "receipt.json").write_text(json.dumps({"core": forged, "receipt_id": "r"}), encoding="utf-8")
        MQ.build_quality_core(target, "code", {"status": "VERIFIED", "receipt_id": "r"})
    # Socket attempts from inside the upstream call path stop the run.
    with monkeypatch.context() as m:
        canonicalize, models, quality_mod = MB.load_upstream()
        m.setattr(quality_mod, "evaluate", lambda result, **_: socket.create_connection(("example.invalid", 80)))
        code, output, written = run_quality(src, tmp_path / "net", capsys)
        assert (code, output) == (1, {"status": "STOPPED", "reason_code": "NETWORK_ATTEMPT_BLOCKED"}) and written is None
    # Output never carries source URLs, body text or local paths.
    code, output, _ = run_quality(src, tmp_path / "quiet", capsys)
    printed = json.dumps(output)
    assert code == 0 and set(output) == {"status", "receipt_id", "sources_total", "upstream_evaluated", "abstained",
                                         "divergent_total", "quality_evaluate_invocations", "network_attempts"}
    blob = (tmp_path / "quiet" / "receipt.json").read_text(encoding="utf-8")
    for text in (printed, blob):
        assert "example.invalid" not in text.casefold() and "consumer price index" not in text
        assert str(tmp_path) not in text and str(tmp_path).replace("\\", "/") not in text
        assert "gh" + "p_" not in text


# ------------------------------------------------------------------ R008


def test_metaculus_authority_and_preserved_36_capability_ids(quality):
    _, receipt = quality
    ids = MB.PROGRAM_CAPABILITY_IDS
    assert len(ids) == len(set(ids)) == 36 and {"R3-01", "R3-01-SOURCE_ARCHIVE"} <= set(ids)
    assert len([i for i in ids if len(i) == 5]) == 29  # one capability per program repository R3-01..R3-29
    adoption = receipt["core"]["adoption"]
    assert adoption == {"R3-01": "SELECTIVE_UPSTREAM_CODE_REUSE_OFFLINE",
                        "R3-01-SOURCE_ARCHIVE": "SELECTIVE_UPSTREAM_CODE_REUSE_OFFLINE",
                        "value_status": "OPERATIONAL_USEFULNESS_NOT_VERIFIED", "owner_acceptance": "PENDING",
                        "native_source_admission": "UNCHANGED_CONTROLLING", "program_capability_ids": 36,
                        "other_capability_ids": "UNCHANGED",
                        "r3_23_public_get_activation": "UNCONSUMED_SEPARATE_OWNER_INSTRUCTION"}
    authority = receipt["core"]["authority"]
    assert authority["research_only"] is True and authority["network_calls"] == authority["provider_calls"] == 0
    assert not any(v for k, v in authority.items() if k not in ("research_only", "network_calls", "provider_calls"))
    # No network, provider, SDK, Hermes, execution or install surface is imported by the new code.
    forbidden = ("requests", "httpx", "urllib.request", "http.client", "aiohttp", "socket", "subprocess", "polymarket",
                 "py_clob_client", "tools.hermes", "src.execution_gateway", "src.paper_trading", "src.live_pilot",
                 "tools.alpha.run_official_sdk", "pip", "forecasting_tools")
    for path in (Path(MB.__file__), Path(MQ.__file__)):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        imported |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert not any(name == f or name.startswith(f + ".") for name in imported for f in forbidden), path
    contract = (REPO_ROOT / "docs" / "metaculus_source_archive_quality_contract.md").read_text(encoding="utf-8")
    for phrase in ("SELECTIVE_UPSTREAM_CODE_REUSE_OFFLINE", "R3-01-SOURCE_ARCHIVE", "owner acceptance: PENDING",
                   "UNCONSUMED", "PR #268", "36"):
        assert phrase in contract, phrase
    status = (REPO_ROOT / "docs" / "status_entries" / "S10-R3-METACULUS-SRC-01.md").read_text(encoding="utf-8")
    assert "Merge: NO" in status and "Ponytail LITE" in status
    deferred = (REPO_ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    assert "S10-R3-METACULUS-SRC-01" in deferred
