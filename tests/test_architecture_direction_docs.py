"""Docs tests for WP61 history and the current V2.1 architecture authority."""

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
    # WP61 text is retained as history only; V2.1 supersedes it as target architecture.
    assert "llm may be used only as read-only analyst/proposal layer" in lower
    assert "no autonomous llm execution authority" in lower
    assert "research-only -> paper -> dry-run -> manual live approval -> restricted live" in lower
    assert lower.index("llm may be used only as read-only analyst/proposal layer") < lower.index(
        'superseded by v2.1 (historical context only): the permanent "llm read-only'
    )
    assert lower.index("manual live approval -> restricted live") < lower.index(
        "superseded by v2.1 (historical context only): this universal research"
    )
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
    assert ("WP173 — Serious Paper Trading System + Paper Cockpit (current review target). Superseded status "
            "(S10-DEPLOY-PLAN-01): the \"current review target\" label above is the historical snapshot") in roadmap
    assert "WP173 has since merged via PR #175" in roadmap
    assert 'The old shorthand "after WP172 and before WP173" is superseded' in roadmap
    for claim in ("WP173 is unimplemented", "WP173 is not implemented", "reimplement WP173"):
        assert claim not in hosting and claim not in roadmap, claim
    # The serial deployment wording above is history; S10-DEPLOY-01 merged as a research
    # baseline and the serial migration point is not current universal architecture.
    adr = _flat(ADR)
    assert "S10-DEPLOY-01 has since merged as a research runtime baseline (PR #209" in adr
    assert 'The serial "after WP172 -> deploy -> WP173" migration point above is not current universal architecture.' in adr
    assert "That quotation does not override the current split research-baseline" in roadmap
    assert "host activation is NOT YET PERFORMED" in roadmap


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


# -- S10-STRAT-LIFE-01: V2.1 is current target architecture (R059-R066) --------

ADOPTION = ROOT / "docs" / "adoption_architecture_dependency_registry_and_alpha_factory_roadmap_lock_in.md"
HERMES_PLAN = ROOT / "docs" / "hermes_research_brain_execution_plan.md"
DATA_DIRECTION = ROOT / "docs" / "research_data_foundation_direction.md"
CONTRACT = ROOT / "docs" / "strategy_lifecycle_portfolio_authority_contract.md"
CANONICAL = (ADR, ADOPTION, HERMES_PLAN, DATA_DIRECTION, ROADMAP)


def _v21_section() -> str:
    adr = ADR.read_text(encoding="utf-8")
    return " ".join(adr.split("## V2.1 Strategy Lifecycle + Portfolio Authority Architecture", 1)[1].split())


def test_v21_is_accepted_current_target_architecture():
    section = _v21_section()
    assert "V2.1 target architecture: ACCEPTED" in section
    assert "This is the current target architecture" in section
    for doc in CANONICAL:
        assert "V2.1" in _flat(doc), doc.name
    for step in (
        "MARKET / PUBLIC DATA / EVENTS", "-> STRATEGY FAMILY / VERSION", "-> HERMES STRATEGY JUDGMENT",
        "-> PORTFOLIO AUTHORITY / ACTIVE BUDGET", "-> HARD EXECUTION SAFETY", "-> PAPER OR BOUNDED LIVE",
        "-> HERMES REASSESSMENT", "-> CONTINUE / SCALE / REDUCE / ADAPT / QUARANTINE",
    ):
        assert step in section, step
    assert "Soft strategy judgment is planned for Hermes but is not implemented by S10-STRAT-LIFE-01" in section
    assert "V2.1 target architecture: ACCEPTED" in _flat(ROADMAP)


def test_wp61_wp95_wp154_assumptions_marked_superseded():
    section = _v21_section()
    for text in (
        "WP61's permanent \"LLM read-only analyst/proposal layer only\" assumption: superseded",
        "WP61's universal research -> paper -> dry-run -> manual live approval -> restricted live ladder: superseded",
        "WP95's permanent Hermes-advisory-only / never-final-decision-maker assumption",
        "WP154 Section 5 universal claim", "Section 6 universal non-skippable single Alpha lineage",
        "Section 7 universal serial adoption sequence",
    ):
        assert text in section, text
    adoption = _flat(ADOPTION)
    assert adoption.count("Superseded by V2.1 as future target architecture (historical context only)") == 3
    assert "The WP154 text above is retained as history" in adoption
    assert "exact, ordered, and non-skippable" in adoption
    hermes = _flat(HERMES_PLAN)
    assert "WP95's permanent Hermes-advisory-only / never-final-decision-maker assumption is superseded" in hermes
    assert "act as the final decision-maker for trade, risk, or live actions" in hermes
    data = _flat(DATA_DIRECTION)
    assert "Strategy: rules-based plus research-score-driven first; LLM read-only analyst/proposal layer only." in data
    assert "Superseded by V2.1 as future target architecture (historical context only)" in data
    roadmap = _flat(ROADMAP)
    assert "Superseded by V2.1 (historical context only): the LLM read-only-only assumption" in roadmap


def test_current_hermes_research_mode_unchanged():
    for doc in (ADR, ADOPTION, HERMES_PLAN):
        text = _flat(doc)
        assert "research-only and unchanged until S10-HERMES-STRAT-01" in text, doc.name
    hermes = _flat(HERMES_PLAN)
    assert "implements no Hermes strategy-manager runtime" in hermes
    assert "Runtime authority: NONE" in hermes
    for claim in ("Hermes strategy manager implemented: YES", "Hermes may place orders", "Hermes may sign"):
        for doc in CANONICAL + (CONTRACT,):
            assert claim not in _flat(doc), (doc.name, claim)


def test_formal_qual_wp170_wp172_lane_preserved():
    section = _v21_section()
    assert "Formal QUAL/WP170/WP172 remains the strongest evidence lane, not the universal path." in section
    assert "Existing qualification/WP170/formal-WP172 mechanics remain unchanged." in section
    assert ("candidate needing durable/larger evidence -> qualification -> WP170 -> formal WP172 -> "
            "qualified paper -> larger validated risk band") in section
    assert "Current Gate C remains its existing strict qualified/canary implementation" in section
    assert "Existing WP173 qualified and research-paper modes remain unchanged." in section
    assert "Strong formal lane (unchanged)" in _flat(ROADMAP)


def test_known_candidate_path_does_not_require_alpha03():
    section = _v21_section()
    path = ("KNOWN CANDIDATE -> lifecycle -> Hermes strategy manager -> execution feasibility -> "
            "exploratory Gate C -> execution host -> live orchestrator -> tiny exploratory live")
    assert path in section and path in _flat(ROADMAP)
    assert "ALPHA-03" not in path
    assert "Known-candidate path (does not require ALPHA-03)" in section
    assert ("S10-STRAT-LIFE-01 -> S10-HERMES-STRAT-01 -> S10-EXEC-FEAS-01 -> S10-GATE-C-EXPLORE-01 -> "
            "S10-DEPLOY-EXEC-01 -> S10-LIVE-ORCH-01") in section
    assert "is not a hard prerequisite for first exploratory live from an already-known candidate" in section


def test_alpha03_is_parallel_feeder():
    section = _v21_section()
    assert "ALPHA-03 is a parallel recurring-discovery feeder, not a prerequisite for a known candidate." in section
    assert "S10-ALPHA-03 discovery lane (parallel)" in section
    assert "ALPHA-03 -> recurring autonomous discovery/research -> new candidate -> same lifecycle" in section
    assert "ALPHA-03 remains separately gated and off the first-known-candidate critical path." in section
    assert "ALPHA-03 is a parallel feeder, not a prerequisite" in _flat(ROADMAP)


def test_global_portfolio_envelope_replaces_per_strategy_approval():
    section = _v21_section()
    assert "Humans define the outer blast radius." in section
    assert ("A human-authorized global PortfolioAuthorityPolicy replaces per-strategy manual live "
            "approval as target architecture; no per-strategy human approval field exists.") in section
    adr = _flat(ADR)
    assert "including manual live approval per strategy, is superseded as future target architecture" in adr
    contract = _flat(CONTRACT)
    assert "One global `PortfolioAuthorityPolicy` is the human-defined outer envelope" in contract
    assert "No per-child or per-strategy human approval field exists." in contract
    assert "LIVE TRADING STATUS: DISABLED" in (ROOT / "docs" / "live_trading_authorization.md").read_text(encoding="utf-8")


def test_strategy_local_quarantine_and_bounded_adaptation_recorded():
    section = _v21_section()
    for text in (
        "Strategy-local failure is strategy-local by default.",
        "Bounded child adaptations may inherit bounded freedom.",
        "Material children lose automatic higher-band inheritance but remain eligible for exploratory treatment.",
    ):
        assert text in section, text
    contract = _flat(CONTRACT)
    assert "Strategy-local failure stays strategy-local" in contract
    assert "material children are capped at min(parent band, EXPLORATORY_LIVE)" in contract
    assert "Only mechanical boundedness is classified" in contract
    assert "A strategy-local event never creates a global restriction." in contract
