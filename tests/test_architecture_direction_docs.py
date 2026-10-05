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
                  "DATA-03 is moved to the VPS"):
        assert claim not in hosting, claim
        assert claim not in adr, claim
    # S10-DEPLOY-EXEC-01: the pre-purchase planning record is history; Karl's later purchase/provisioning
    # report is recorded only in the superseding current section, while host technical truth stays
    # unknown and no deployment or activation has happened.
    historical, current = hosting.split("## 11. Current Operator-Reported Provisioning State (S10-DEPLOY-EXEC-01)", 1)
    assert "deployment status: NOT_PROVISIONED / NOT_DEPLOYED" in historical
    assert "VPS purchased: YES" not in historical and "VPS purchased: YES" not in adr
    for text in ("VPS purchased: YES (operator-reported by Karl; not observed by the repository)",
                 "VPS provisioned: YES (operator-reported by Karl; not observed by the repository)",
                 "project deployment/configuration on that VPS: NOT PERFORMED",
                 "host activation / bootstrap / binding / reboot proof: NOT PERFORMED",
                 "actual host technical facts: UNKNOWN until a separately authorized Phase B verifies them",
                 "initial intended tier/direction: AlphaVPS / Sofia / C8G / one consolidated host",
                 "The repository has not observed this VPS."):
        assert text in current, text
    assert "Section 11 records that current state without rewriting this planning record." in historical
    for claim in ("project deployment/configuration on that VPS: PERFORMED", "actual host technical facts: VERIFIED",
                  "host activation: PERFORMED", "deployment status: DEPLOYED"):
        assert claim not in hosting, claim


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


# -- S10-HERMES-STRAT-01: canonical soft Hermes strategy judgment (R070-R073, R076) --

HERMES_STRAT_CONTRACT = ROOT / "docs" / "hermes_strategy_manager_contract.md"


def _hermes_strat_adr() -> str:
    adr = ADR.read_text(encoding="utf-8")
    return " ".join(adr.split("## V2.1 Hermes Strategy Manager Core (S10-HERMES-STRAT-01)", 1)[1].split())


def test_hermes_strat_raw_research_vs_canonical_decision():
    section = _hermes_strat_adr()
    assert ("Existing generic controlled research primitive: a research-only raw Hermes run with untrusted "
            "output and no direct strategy/execution/live authority.") in section
    assert ("HERMES-STRAT layer: verified STRAT-LIFE context + bounded evidence + existing controlled Hermes "
            "run + strategy-mode output schema + deterministic repository validation = canonical soft Hermes "
            "strategy decision.") in section
    contract = _flat(HERMES_STRAT_CONTRACT)
    assert "Raw model bytes never acquire repository authority" in contract
    assert "no per-strategy human-approval field" in contract
    assert "research-only raw Hermes output stays untrusted" in _flat(HERMES_PLAN)


def test_hermes_strat_permanent_advisory_target_superseded():
    section = _hermes_strat_adr()
    assert "Superseded as a current target statement (historical text retained)" in section
    assert "Hermes can never make strategy lifecycle decisions" in section
    hermes = _flat(HERMES_PLAN)
    assert "The permanent advisory-only target above is historical/superseded for this soft strategy judgment only" in hermes
    # Historical text is retained, not rewritten.
    assert "WP95's permanent Hermes-advisory-only / never-final-decision-maker assumption is superseded" in hermes
    assert "act as the final decision-maker for trade, risk, or live actions" in hermes
    assert "Supersession — V2.1 Hermes Strategy Manager (S10-HERMES-STRAT-01)" in _flat(ADOPTION)


def test_hermes_strat_hard_risk_execution_ownership_explicit():
    section = _hermes_strat_adr()
    assert "Hard deterministic ownership is unchanged and explicit" in section
    assert "Hermes cannot override them" in section
    assert "it is not a hard authorization" in section
    assert "Formal QUAL/WP170/WP172 remains the strongest evidence lane but is not made a universal gate" in section
    contract = _flat(HERMES_STRAT_CONTRACT)
    assert "never writes or opens the STRAT-LIFE store" in contract
    assert "SCALE stays downstream gated" in contract
    assert "is not a universal evidence gate" in _flat(DATA_DIRECTION)
    for claim in ("Hermes may place orders", "Hermes may sign", "Hermes strategy manager implemented: YES"):
        for doc in CANONICAL + (HERMES_STRAT_CONTRACT,):
            assert claim not in _flat(doc), (doc.name, claim)


def test_hermes_strat_known_candidate_path_records_capability():
    section = _hermes_strat_adr()
    path = ("lifecycle (S10-STRAT-LIFE-01: MERGED) -> Hermes strategy manager (S10-HERMES-STRAT-01: "
            "implemented capability)")
    assert path in section
    assert "S10-EXEC-FEAS-01: next core package after HERMES-STRAT review and merge" in section
    roadmap = _flat(ROADMAP)
    # S10-EXEC-FEAS-01: HERMES-STRAT is now a merged capability (PR #211).
    assert "## S10-HERMES-STRAT-01 Hermes Strategy Manager Core (merged)" in ROADMAP.read_text(encoding="utf-8")
    assert "Hermes strategy manager (S10-HERMES-STRAT-01: implemented capability, MERGED in PR #211)" in roadmap


def test_hermes_strat_alpha03_parallel():
    section = _hermes_strat_adr()
    assert "ALPHA-03 remains a parallel, non-blocking feeder." in section
    assert "ALPHA-03" not in section.split("Known-candidate path capability status:", 1)[1].split("ALPHA-03 remains", 1)[0]
    assert "ALPHA-03 remains a parallel feeder" in _flat(ROADMAP)
    assert "ALPHA-03 stays parallel" in _flat(ADOPTION)


# -- S10-EXEC-FEAS-01: current public execution feasibility (R062-R063) --

EXEC_FEAS_CONTRACT = ROOT / "docs" / "execution_feasibility_contract.md"


def _exec_feas_adr() -> str:
    adr = ADR.read_text(encoding="utf-8")
    return " ".join(adr.split("## V2.1 Current Public Execution Feasibility Core (S10-EXEC-FEAS-01)", 1)[1].split())


def test_exec_feas_current_public_mechanics_not_wp172():
    section = _exec_feas_adr()
    assert "S10-HERMES-STRAT-01: MERGED." in section
    assert "S10-EXEC-FEAS-01 is implemented as the current public mechanical feasibility sibling" in section
    assert "Current public execution feasibility is not WP172 executable edge" in section
    assert "WP172 remains the formal durable executable-edge evidence lane" in section
    assert "EXECUTABLE_EDGE_PASS is not reused, renamed, bypassed or weakened" in section
    hermes_adr = _hermes_strat_adr()
    assert "Status: MERGED (PR #211 merged at" in hermes_adr
    contract = _flat(EXEC_FEAS_CONTRACT)
    assert "WP172 remains the formal durable executable-edge evidence lane" in contract
    assert "no EXEC-FEAS status is equivalent to a WP172 PASS" in contract
    assert "never claims the server-rounded fee" in contract
    # S10-GATE-C-EXPLORE-01: EXEC-FEAS is now MERGED (PR #212); that claim is no longer forbidden.
    for claim in ("EXEC-FEAS authorizes orders", "Gate C: AUTHORIZED", "live: ENABLED",
                  "S10-GATE-C-EXPLORE-01: STARTED"):
        for doc in CANONICAL + (EXEC_FEAS_CONTRACT,):
            assert claim not in _flat(doc), (doc.name, claim)


def test_exec_feas_known_candidate_path_gate_c_next():
    section = _exec_feas_adr()
    path = ("lifecycle (S10-STRAT-LIFE-01: MERGED) -> Hermes strategy manager (S10-HERMES-STRAT-01: MERGED) -> "
            "execution feasibility (S10-EXEC-FEAS-01: implemented capability, current review target) -> "
            "exploratory Gate C (S10-GATE-C-EXPLORE-01: next core package after EXEC-FEAS review and merge; "
            "NOT AUTHORIZED / NOT STARTED)")
    assert path in section
    assert "ALPHA-03 remains a parallel, non-blocking feeder and is not a prerequisite." in section
    assert "ALPHA-03" not in section.split("Known-candidate path capability status:", 1)[1].split("ALPHA-03 remains", 1)[0]
    roadmap = _flat(ROADMAP)
    # S10-GATE-C-EXPLORE-01: EXEC-FEAS is now a merged capability (PR #212); its status line is history.
    assert "## S10-EXEC-FEAS-01 Current Public Execution Feasibility Core (merged)" in ROADMAP.read_text(encoding="utf-8")
    for text in ("Status at EXEC-FEAS implementation time: S10-STRAT-LIFE-01: MERGED; S10-HERMES-STRAT-01: MERGED; "
                 "S10-EXEC-FEAS-01: then the implemented review target (now MERGED in PR #212);",
                 "execution feasibility (S10-EXEC-FEAS-01: implemented capability, MERGED in PR #212)",
                 "ALPHA-03, DATA-03 and the Control Center (S10-CC-FOUND-01) stay parallel"):
        assert text in roadmap, text


# -- S10-GATE-C-EXPLORE-01: exploratory Gate C policy permit core (R043) --

GATE_C_CONTRACT = ROOT / "docs" / "exploratory_gate_c_contract.md"
LIVE_AUTH = ROOT / "docs" / "live_trading_authorization.md"


def _gate_c_adr() -> str:
    adr = ADR.read_text(encoding="utf-8")
    return " ".join(adr.split("## V2.1 Exploratory Gate C Policy Permit Core (S10-GATE-C-EXPLORE-01)", 1)[1].split())


def test_direction_docs():
    section = _gate_c_adr()
    path = ("lifecycle (S10-STRAT-LIFE-01: MERGED) -> Hermes strategy manager (S10-HERMES-STRAT-01: MERGED) -> "
            "execution feasibility (S10-EXEC-FEAS-01: MERGED) -> exploratory Gate C (S10-GATE-C-EXPLORE-01: "
            "implemented capability, current review target) -> execution host (S10-DEPLOY-EXEC-01: next core "
            "successor after GATE-C-EXPLORE review and merge; NOT STARTED) -> live orchestrator "
            "(S10-LIVE-ORCH-01: later) -> tiny exploratory live")
    assert path in section
    for text in ("S10-EXEC-FEAS-01: MERGED.", "Governance track PROTECTED",
                 "necessary-but-not-sufficient future evidence",
                 "A SCALE judgment never widens the current EXPLORATORY_LIVE allocation",
                 "WP175 remains the historical/manual real restricted-live canary",
                 "S10-CC-OPS-01 may begin only after GATE-C-EXPLORE merges, as a separate package",
                 "ALPHA-03 remains a parallel, non-blocking feeder", "DATA-03 remains unchanged and non-blocking"):
        assert text in section, text
    exec_feas = _exec_feas_adr()
    assert "Status: MERGED (PR #212 merged at `35db4f05347b8b27f7bd0296cf9b1b0627e58d12`, head `99f3c3c8acc09ae3b5646f785446d69a7b8b2290`" in exec_feas
    # S10-DEPLOY-EXEC-01: GATE-C-EXPLORE is now merged (PR #213); its implementation-time record is history.
    assert ("Status: MERGED (PR #213 merged at `0392c2d2080a656d8ffd69f42abf8ad91d1f90e2`, head "
            "`342dfeb24652eccb1b6bdf237039b268115b1fb7`") in section
    roadmap = _flat(ROADMAP)
    assert "## S10-GATE-C-EXPLORE-01 Exploratory Gate C Policy Permit Core (merged)" in ROADMAP.read_text(encoding="utf-8")
    for text in ("Status at GATE-C-EXPLORE implementation time: S10-STRAT-LIFE-01: MERGED; S10-HERMES-STRAT-01: "
                 "MERGED; S10-EXEC-FEAS-01: MERGED; S10-GATE-C-EXPLORE-01: then the current protected implemented "
                 "review target (now MERGED in PR #213); S10-DEPLOY-EXEC-01: then the next core successor after "
                 "review+merge; S10-LIVE-ORCH-01: later;",
                 "exploratory Gate C (S10-GATE-C-EXPLORE-01: implemented capability, MERGED in PR #213) -> execution "
                 "host (S10-DEPLOY-EXEC-01: see the current section below)",
                 "Earlier merged predecessor: S10-EXEC-FEAS-01 Current Public Execution Feasibility Core (PR #212",
                 # S10-LIVE-ORCH-01: DEPLOY-EXEC (PR #214) is now the immediate merged predecessor.
                 "Earlier merged predecessor: S10-GATE-C-EXPLORE-01 Exploratory Gate C Policy Permit Core (PR #213"):
        assert text in roadmap, text


def test_gate_c_explore_is_not_live_or_legacy_gate_c():
    contract = _flat(GATE_C_CONTRACT)
    for text in ("necessary-but-not-sufficient future evidence", "WP175 remains the historical/manual real restricted-live canary",
                 "issues or consumes no legacy WP175 Gate-C live permit, arms no session and enters no A3 state",
                 "No arbitrary TTL", "Capital/orders USD 0 / 0", "`LIVE TRADING STATUS: DISABLED`"):
        assert text in contract, text
    live = LIVE_AUTH.read_text(encoding="utf-8")
    assert live.splitlines()[2] == "LIVE TRADING STATUS: DISABLED"
    live_flat = " ".join(live.split())
    for text in ("S10-GATE-C-EXPLORE-01 (V2.1 exploratory Gate C policy permit core) is separate from WP175.",
                 "An exploratory permit is necessary-but-not-sufficient future evidence for one exact intent, not live activation;",
                 "enters no A3 state"):
        assert text in live_flat, text
    # S10-DEPLOY-EXEC-01: GATE-C-EXPLORE is now MERGED (PR #213); that claim is no longer forbidden.
    for claim in ("Gate C: AUTHORIZED", "live: ENABLED", "LIVE TRADING STATUS: ENABLED", "S10-DEPLOY-EXEC-01: STARTED",
                  "A3_RESTRICTED_LIVE: ENTERED"):
        for doc in CANONICAL + (GATE_C_CONTRACT, LIVE_AUTH):
            assert claim not in _flat(doc), (doc.name, claim)


# -- S10-DEPLOY-EXEC-01: execution-host runtime substrate (R026, R030) --

EXEC_HOST_CONTRACT = ROOT / "docs" / "execution_host_runtime_contract.md"
DEPLOY_BASELINE_CONTRACT = ROOT / "docs" / "research_platform_runtime_baseline_contract.md"


def _deploy_exec_adr() -> str:
    adr = ADR.read_text(encoding="utf-8")
    return " ".join(adr.split("## V2.1 Execution-Host Runtime Substrate (S10-DEPLOY-EXEC-01)", 1)[1].split())


def _deploy_exec_roadmap() -> str:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    # S10-LIVE-ORCH-01: DEPLOY-EXEC merged (PR #214); its roadmap section is retained as merged history.
    section = roadmap.split("## S10-DEPLOY-EXEC-01 Execution-Host Runtime Substrate & Coexistence Proof (merged)", 1)[1]
    section = section.split("\n## ", 1)[0]
    return " ".join(section.split())


def test_execution_host_docs_forbid_automatic_upgrade_and_second_host():
    contract = _flat(EXEC_HOST_CONTRACT)
    for text in ("the evaluator grants no purchase, resize or second-host authority",
                 "Karl, who decides whether the same single-host architecture is retried on an approved larger tier",
                 "A second host is a separate material architecture decision, never a same-package scaling action",
                 "proves evaluator semantics only, never actual host capacity",
                 "`EXECUTION_HOST_INCONCLUSIVE` outranks all of them"):
        assert text in contract, text
    hosting = _flat(HOSTING)
    for text in ("nothing is auto-purchased or auto-upgraded, Karl decides, and a second VPS remains a separate "
                 "material architecture decision rather than a scaling step",
                 "The research and critical slice values in Section 5 are unchanged."):
        assert text in hosting, text
    assert "nothing is auto-purchased or auto-upgraded" in _deploy_exec_adr()
    assert "no automatic upgrade or purchase; Karl decides" in _deploy_exec_roadmap()
    # The DEPLOY-01 research-baseline contract and its closed research dispositions remain unchanged history.
    baseline = _flat(DEPLOY_BASELINE_CONTRACT)
    assert "S10-DEPLOY-EXEC-01" not in baseline and "C8G_RESEARCH_BASELINE_SUFFICIENT" in baseline
    for claim in ("auto-upgrade: YES", "automatic upgrade: YES", "second VPS: AUTHORIZED", "auto-purchase: YES"):
        for doc in (EXEC_HOST_CONTRACT, HOSTING, ADR, ROADMAP):
            assert claim not in _flat(doc), (doc.name, claim)


def test_execution_host_successor_boundary_live_orch_remains_separate():
    section = _deploy_exec_adr()
    path = ("lifecycle (S10-STRAT-LIFE-01: MERGED) -> Hermes strategy manager (S10-HERMES-STRAT-01: MERGED) -> "
            "execution feasibility (S10-EXEC-FEAS-01: MERGED) -> exploratory Gate C (S10-GATE-C-EXPLORE-01: MERGED) "
            "-> execution host (S10-DEPLOY-EXEC-01: implemented repository mechanism, current review target; real "
            "host proof separately gated as Phase B) -> live orchestrator (S10-LIVE-ORCH-01: next core successor, "
            "NOT STARTED) -> tiny exploratory live")
    assert path in section
    for text in ("S10-GATE-C-EXPLORE-01: MERGED.", "Governance track RUNTIME",
                 "This is an execution-capable host substrate, not economic execution authority",
                 "Gate-C eligibility and DEPLOY-EXEC host proof are each necessary but not sufficient for live execution",
                 "the actual AlphaVPS host proof", "is a separately authorized Phase B after merge"):
        assert text in section, text
    contract = _flat(EXEC_HOST_CONTRACT)
    for text in ("S10-LIVE-ORCH-01 remains the next core package",
                 "DEPLOY-EXEC success is necessary but not sufficient for live execution",
                 "`live_readiness: NOT_IMPLIED` and `required_successor: S10-LIVE-ORCH-01`",
                 "Phase B (real AlphaVPS proof): NOT AUTHORIZED by Phase A",
                 "`LIVE TRADING STATUS: DISABLED` remains true; capital/orders USD 0 / 0."):
        assert text in contract, text
    roadmap = _deploy_exec_roadmap()
    assert ("live orchestrator (S10-LIVE-ORCH-01: next core successor after execution-host substrate proof, "
            "NOT STARTED)") in roadmap
    live = " ".join(LIVE_AUTH.read_text(encoding="utf-8").split())
    assert LIVE_AUTH.read_text(encoding="utf-8").splitlines()[2] == "LIVE TRADING STATUS: DISABLED"
    assert "S10-DEPLOY-EXEC-01 (execution-host runtime substrate) grants no live authority." in live
    assert "is necessary but not sufficient for live execution: S10-LIVE-ORCH-01 must still revalidate" in live
    for claim in ("S10-LIVE-ORCH-01: STARTED", "S10-LIVE-ORCH-01: MERGED", "Phase B: PERFORMED", "EXECUTION_HOST_PROVEN_C8G: ACHIEVED",
                  "live: ENABLED", "LIVE TRADING STATUS: ENABLED"):
        for doc in CANONICAL + (EXEC_HOST_CONTRACT, LIVE_AUTH, HOSTING):
            assert claim not in _flat(doc), (doc.name, claim)

# -- S10-LIVE-ORCH-01: restricted live orchestration + first-live canary core (R008) --

LIVE_ORCH_CONTRACT = ROOT / "docs" / "live_orchestration_contract.md"


def _live_orch_adr() -> str:
    adr = ADR.read_text(encoding="utf-8")
    return " ".join(adr.split(
        "## V2.1 Restricted Live Orchestration + First-Live Canary Core (S10-LIVE-ORCH-01)", 1)[1].split())


def test_live_orch_direction_docs_record_dormant_capability_and_separate_canary():
    section = _live_orch_adr()
    path = ("lifecycle (S10-STRAT-LIFE-01: MERGED) -> Hermes strategy manager (S10-HERMES-STRAT-01: MERGED) -> "
            "execution feasibility (S10-EXEC-FEAS-01: MERGED) -> exploratory Gate C (S10-GATE-C-EXPLORE-01: MERGED) "
            "-> execution host (S10-DEPLOY-EXEC-01: MERGED) -> live orchestrator (S10-LIVE-ORCH-01: implemented "
            "dormant capability, current protected review target) -> first restricted live canary "
            "(S10-LIVE-CANARY-01: separately gated, NOT AUTHORIZED)")
    assert path in section
    for text in ("Governance track PROTECTED", "exact 27-path XL scope", "independent certificate",
                 "S10-DEPLOY-EXEC-01: MERGED (PR #214 merged at `fe4e2f1557dec5667d32fa1479f0bfc7ead1c940`",
                 "constructs no raw SDK client and adds no direct mutation boundary",
                 "The first-live CREATE side is BUY only",
                 "Merge does not activate live trading",
                 "WP175 remains the historical/manual restricted-live canary path"):
        assert text in section, text
    assert "Status: MERGED (PR #214 merged at `fe4e2f1557dec5667d32fa1479f0bfc7ead1c940`" in _deploy_exec_adr()
    contract = _flat(LIVE_ORCH_CONTRACT)
    for text in ("`LIVE TRADING STATUS: DISABLED`", "SIDE_UNSUPPORTED_FIRST_CANARY",
                 "durable ADMISSION -> durable CREATE_STARTED -> one economic transmit maximum",
                 "Admission persistence failure means zero transmit",
                 "including the venue code `unknown`", "FAILED is terminal failure and never an active fill",
                 "At most three cancel/reconcile rounds per foreground invocation",
                 "`current_value` is never read, so a mark-to-market decline never frees budget",
                 "No UTC-day realized-loss ledger or account-equity high-water drawdown is claimed",
                 "`fetch_public_venue_snapshot(*, gamma_market_id, condition_id, token_id, opener=None, clock_ns=None)`",
                 "ORDER_ENCODING_UNSUPPORTED", "This contract never authorizes a real order"):
        assert text in contract, text
    for constant, value in (("AUTHORIZED_ACCOUNT_CAPITAL_USD", "100"), ("SINGLE_ORDER_WORST_CASE_MAX_USD", "5"),
                            ("MAX_TOTAL_EARLY_COMMITMENT_USD", "30"), ("MIN_FREE_COLLATERAL_RESERVE_USD", "70")):
        assert f"| `{constant}` | {value} |" in LIVE_ORCH_CONTRACT.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")
    assert "## S10-LIVE-ORCH-01 Restricted Live Orchestration + First-Live Canary Core (current)" in roadmap
    assert "## S10-DEPLOY-EXEC-01 Execution-Host Runtime Substrate & Coexistence Proof (merged)" in roadmap
    flat_roadmap = _flat(ROADMAP)
    for text in ("Current protected implementation package: S10-LIVE-ORCH-01 Restricted Live Orchestration +",
                 "Immediate merged predecessor: S10-DEPLOY-EXEC-01 Execution-Host Runtime Substrate &"):
        assert text in flat_roadmap, text
    live_text = LIVE_AUTH.read_text(encoding="utf-8")
    assert live_text.splitlines()[2] == "LIVE TRADING STATUS: DISABLED"
    live = " ".join(live_text.split())
    for text in ("S10-LIVE-ORCH-01 (restricted live orchestration + first-live canary core) merges dormant "
                 "protected capability only and grants no live authority.",
                 "may transmit at most one BUY CREATE", "Merge does not activate live trading",
                 "| S10-LIVE-ORCH-01 first restricted live canary | No (dormant; separate exact-merge activation required) |"):
        assert text in live, text
    for claim in ("S10-LIVE-ORCH-01: MERGED", "S10-LIVE-CANARY-01: STARTED", "S10-LIVE-CANARY-01: AUTHORIZED",
                  "LIVE TRADING STATUS: ENABLED", "live: ENABLED", "AUTO_SCALING` | TRUE", "SELL CREATE: SUPPORTED"):
        for doc in CANONICAL + (LIVE_ORCH_CONTRACT, LIVE_AUTH):
            assert claim not in _flat(doc), (doc.name, claim)
