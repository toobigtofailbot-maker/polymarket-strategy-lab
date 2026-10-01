"""Focused docs tests for WP61 architecture direction lock-in."""

from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
ADR = ROOT / "docs" / "architecture_decision_record.md"


def test_architecture_direction_record_exists():
    assert ADR.exists()


def test_architecture_direction_lockin_contains_required_decisions():
    text = ADR.read_text(encoding="utf-8")
    lower = text.lower()

    assert "## WP61 Direction Lock-In - User-Approved Execution Path" in text
    assert "sqlite first" in lower
    assert "postgres deferred" in lower or "postgres later" in lower
    assert "streamlit first" in lower
    assert "grafana later" in lower
    assert "next.js only if productizing" in lower
    assert "local development first" in lower
    assert "cheap vps later" in lower
    assert "rules-based + research-score-driven strategy first" in lower
    assert "llm may be used only as read-only analyst/proposal layer" in lower
    assert "no autonomous llm execution authority" in lower
    assert "research-only -> paper -> dry-run -> manual live approval -> restricted live" in lower
    assert "no database, dashboard, runtime, deployment, scheduler, or execution implementation in wp61" in lower
    assert "agent mode / deep research" in lower


HOSTING = ROOT / "docs" / "production_vps_hosting_direction.md"
CHARTER = ROOT / "docs" / "project_charter.md"
ROADMAP = ROOT / "docs" / "long_term_bot_completion_roadmap.md"
INDEX = ROOT / "docs" / "repo_truth_index.md"


def _flat(path: pathlib.Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_production_vps_hosting_direction_contract():
    hosting = _flat(HOSTING)
    adr = _flat(ADR)
    for text in (
        "decision status: APPROVED_PLANNING_DIRECTION", "deployment status: NOT_PROVISIONED / NOT_DEPLOYED",
        "provider: AlphaVPS", "location: Sofia, Bulgaria", "initial tier: C8G",
        "initial resources: 4 vCPU / 8 GB ECC RAM / 75 GB NVMe RAID-10", "OS: Ubuntu 24.04 LTS / x86-64",
        "architecture: ONE_CONSOLIDATED_POLYMARKET_VPS", "default separate research/live VPS: NO",
        "upgrade path: C8G -> C12G -> C16G/P-series -> larger only by telemetry evidence",
        "future implementation package: S10-DEPLOY-01", "future package state: NOT AUTHORIZED",
        "DRAFT-ELIGIBLE LATER / NOT AUTHORIZED NOW", "not automatic upgrades", "Karl decides after reviewing telemetry",
        "MemAvailable", "Execution-path interference", "Resource-isolation failure", "Kubernetes is not required",
        "Single-host coexistence proof", "C8G_SUFFICIENT", "UPGRADE_ELIGIBLE:<reason>",
        "It must not auto-upgrade or auto-purchase", "A second VPS is not a normal scaling step",
        "DATA-03 is not moved to the VPS", "DATA-03 remains on the current operator environment",
        "zero-network `prepare`", "`2026-10-15T00:00:00Z`", "remains substantively unchanged",
        "Current live authority remains unchanged", "Gate C is NOT AUTHORIZED", "capital at risk USD 0; orders 0",
    ):
        assert text in hosting, text
    for proof in ("Host identity / reproducibility", "Persistence", "Process/service supervision", "Recovery proof",
                  "Clock", "Secrets", "Firewall / network", "Backup / restore", "Health / monitoring", "Logs / evidence"):
        assert f"- {proof}:" in hosting, proof
    for text in (
        "## S10-DEPLOY-PLAN-01 Production VPS Hosting Direction Lock", "Provider: AlphaVPS.",
        "Location: Sofia, Bulgaria.", "Initial tier: C8G (4 vCPU / 8 GB ECC RAM / 75 GB NVMe RAID-10).",
        "OS: Ubuntu 24.04 LTS / x86-64.", "Architecture: ONE_CONSOLIDATED_POLYMARKET_VPS.",
        "Default separate research/live VPS: NO.", "DRAFT-ELIGIBLE LATER / NOT AUTHORIZED NOW",
        "DATA-03 remains on the current operator environment and is not moved to the VPS.",
    ):
        assert text in adr, text
    for claim in ("deployment status: DEPLOYED", "S10-DEPLOY-01 is AUTHORIZED", "future package state: AUTHORIZED",
                  "default separate research/live VPS: YES", "Gate C is AUTHORIZED", "live: ENABLED",
                  "DATA-03 is moved to the VPS", "VPS purchased: YES"):
        assert claim not in hosting, claim
        assert claim not in adr, claim


def test_hosting_direction_migration_point_and_wp173_truth():
    roadmap = _flat(ROADMAP)
    for text in (_flat(HOSTING), roadmap):
        assert ("after a real strategy-specific WP172 EXECUTABLE_EDGE_PASS exists and before the first serious "
                "production-hosted paper runtime using the existing WP173 system") in text
        assert ("-> real WP172 executable-edge evidence / EXECUTABLE_EDGE_PASS -> S10-DEPLOY-01 Production VPS Runtime "
                "Baseline -> serious production-hosted WP173 paper runtime") in text or (
                "-> real WP172 executable-edge evidence / PASS -> S10-DEPLOY-01 Production VPS Runtime Baseline -> "
                "serious production-hosted WP173 paper runtime") in text
    hosting = _flat(HOSTING)
    assert "merged via PR #174" in hosting and "merged via PR #175" in hosting
    assert "WP173 code is not reimplemented" in hosting
    assert "not folded into WP173 or WP174" in hosting
    assert "WP173 — Serious Paper Trading System + Paper Cockpit (merged via PR #175" in roadmap
    assert "WP173 — Serious Paper Trading System + Paper Cockpit (current review target)" not in roadmap
    assert 'The old shorthand "after WP172 and before WP173" is superseded' in roadmap
    for claim in ("WP173 is unimplemented", "WP173 is not implemented", "reimplement WP173"):
        assert claim not in hosting and claim not in roadmap, claim


def test_hosting_direction_supersedes_stale_vps_wording():
    charter = _flat(CHARTER)
    assert "VPS and cloud choices remain open" not in charter
    assert "supersedes the earlier charter statement that VPS and cloud choices remained open" in charter
    for text in ("AlphaVPS, Sofia, Bulgaria", "C8G", "ONE consolidated Polymarket VPS", "S10-DEPLOY-01",
                 "NOT AUTHORIZED", "docs/production_vps_hosting_direction.md"):
        assert text in charter, text
    adr = _flat(ADR)
    assert adr.index("Cheap VPS later") < adr.index('Superseded (historical context only): the generic "cheap VPS later"')
    roadmap = _flat(ROADMAP)
    assert 'Its "cheap VPS later" hosting shorthand is historical context only, superseded' in roadmap
    index = _flat(INDEX)
    assert 'Its WP61 "cheap VPS later" hosting shorthand is historical context only, superseded' in index
    hosting = _flat(HOSTING)
    assert "## 2. Superseded Planning Statements" in hosting
    assert "the `docs/project_charter.md` statement that VPS and cloud choices remain open" in hosting
