import { useEffect, useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { delay, http, HttpResponse, type HttpHandler } from "msw";
import { MemoryRouter } from "react-router";
import preview from "../.storybook/preview";
import {
  createQueryClient,
  familyKey,
  overviewQuery,
  type AlphaCandidateDetail,
  type AlphaCandidateSummary,
  type AlphaEpisodeDetail,
  type AlphaEpisodeSummary,
  type AlphaMemorySummary,
  type AlphaSourceReference,
  type AuditItem,
  type DiscoveryQueueResponse,
  type DiscoveryTriageResponse,
  type DiscoveryTriageSummary,
  type ContextStatus,
  type Experiment,
  type ExperimentDetail,
  type GatewayAuditItem,
  type GatewayStatus,
  type Health,
  type HermesAssessmentDetail,
  type HermesAssessmentItem,
  type LatestHermesAssessment,
  type ListResponse,
  type MarketItem,
  type OpsActivePolicy,
  type OpsPortfolio,
  type OpsStrategyReservation,
  type Overview,
  type PaperFill,
  type PaperOrder,
  type PaperPosition,
  type PaperRisk,
  type PaperSummary,
  type StrategyDetail,
  type StrategySummary,
  type StreamStatus,
} from "./api";
import { ControlCenter } from "./app";

// Deterministic reference states. Every /api request a story makes is answered by the MSW
// handlers below; anything unmocked hits the preview's closed INTERNAL_ERROR catch-all and
// never leaves the browser. Fixtures follow the current backend DTOs exactly.

const list = <T,>(items: T[], limit = 50): ListResponse<T> => ({ items, count: items.length, limit });
const closedError = (code: string, status: number) => HttpResponse.json({ error: { code } }, { status });

const overview: Overview = {
  read_only: true,
  market_truth: {
    normalized_count: 4,
    accepted_count: 2,
    quarantined_count: 1,
    open_gap_count: 0,
    latest_received_at: "2024-07-03T09:47:04.000000Z",
  },
  experiments: { experiment_count: 1, lifecycle_count: 5, evidence_count: 1 },
  recent_activity: { market_truth_count: 4, audit_count: 6 },
};

const marketItems: MarketItem[] = [
  {
    observation_id: "obs-0004",
    source_kind: "WS",
    event_kind: "book",
    market_id: "0xmarket-fixture-a",
    asset_id: "asset-fixture-yes",
    event_time: "2024-07-03T09:47:03.900000Z",
    received_at: "2024-07-03T09:47:04.000000Z",
    status: "ACCEPTED",
    book_ready: true,
  },
  {
    observation_id: "obs-0003",
    source_kind: "WS",
    event_kind: "price_change",
    market_id: "0xmarket-fixture-a",
    asset_id: "asset-fixture-no",
    event_time: "2024-07-03T09:47:02.500000Z",
    received_at: "2024-07-03T09:47:02.600000Z",
    status: "ACCEPTED",
    book_ready: false,
  },
  {
    observation_id: "obs-0002",
    source_kind: "WS",
    event_kind: "unknown",
    market_id: null,
    asset_id: null,
    event_time: null,
    received_at: "2024-07-03T09:47:01.000000Z",
    status: "QUARANTINED",
    book_ready: false,
  },
];

const experiment: Experiment = {
  experiment_id: "exp-fixture-0001",
  experiment_family_id: "family-fixture-01",
  trial_number: 1,
  hypothesis_id: "hyp-fixture-01",
  preregistered_at: "2024-07-01T12:00:00.000000Z",
  lifecycle_state: "EVIDENCE_RECORDED",
  result_status: "OOS_CRITERIA_MET_UNCOSTED",
  oos_exposure_ordinal: 1,
};

const experimentDetail: ExperimentDetail = {
  ...experiment,
  dataset_binding_id: "binding-fixture-01",
  research_dataset_manifest_id: "manifest-fixture-01",
  feature_definition_ids: ["feature-fixture-01", "feature-fixture-02"],
  feature_set_id: "featureset-fixture-01",
  label_definition_id: "label-fixture-01",
  split_assignment_id: "split-fixture-01",
  primary_metric_id: "metric-fixture-primary",
  secondary_metric_ids: [],
  baseline_id: "baseline-fixture-01",
  cost_model_reference: "costmodel-fixture-01",
  lifecycle_receipt_ids: ["lifecycle-fixture-01", "lifecycle-fixture-02"],
  evidence_receipt_ids: ["evidence-fixture-01"],
};

const paperSummary: PaperSummary = {
  session_id: "paper-session-fixture",
  control_state: "RUNNING",
  reconciliation_state: "RECONCILED",
  cash: "1000.00",
  free_cash: "940.00",
  reserved_cash: "60.00",
  equity: "1003.50",
  realized_pnl: "1.25",
  unrealized_pnl: "2.25",
  open_order_count: 1,
  fill_count: 1,
  markout_count: 1,
  last_market_receive_ns: 1720000024000000000,
  simulated_paper_only: true,
};
const paperOrders: PaperOrder[] = [
  {
    order_id: "paper-order-fixture-01",
    market_id: "0xmarket-fixture-a",
    asset_id: "asset-fixture-yes",
    side: "BUY",
    order_style: "LIMIT",
    quantity: "100",
    filled_quantity: "40",
    average_fill_price: "0.52",
    fee_paid: "0.00",
    status: "PARTIALLY_FILLED",
  },
];
const paperFills: PaperFill[] = [
  {
    fill_id: "paper-fill-fixture-01",
    order_id: "paper-order-fixture-01",
    side: "BUY",
    quantity: "40",
    price: "0.52",
    fee: "0.00",
    spread_cost: "0.20",
    depth_slippage_cost: "0.04",
    latency_cost: "0.01",
    adverse_selection_cost: null,
    markout_status: "PENDING",
    fill_kind: "SIMULATED_PAPER_FILL",
  },
];
const paperPositions: PaperPosition[] = [
  {
    market_id: "0xmarket-fixture-a",
    asset_id: "asset-fixture-yes",
    quantity: "40",
    cost_basis: "20.80",
    realized_pnl: "0.00",
    mark: "0.55",
    marked_value: "22.00",
  },
];
const paperRisk: PaperRisk = {
  limits: { max_open_orders: 5 },
  utilization: { open_orders: 1, max_open_orders: 5, reserved_cash: "60.00" },
  deny_count: 0,
  resolution_pending: [],
  latest_decision: { result: "ALLOW", reason_codes: [] },
};

const health: Health = {
  status: "OK",
  read_only: true,
  wp169: { configured: true, readable: true },
  wp170: { configured: true, readable: true },
  paper: { configured: true, readable: true },
  gateway: { configured: false, readable: false },
};
const auditItems: AuditItem[] = [
  {
    source: "WP170",
    record_id: "evidence-fixture-01",
    experiment_id: "exp-fixture-0001",
    kind: "EVIDENCE",
    sequence: 6,
    status: "OOS_CRITERIA_MET_UNCOSTED",
    occurred_at: "2024-07-03T10:00:00.000000Z",
  },
  {
    source: "WP169",
    record_id: "obs-0004",
    experiment_id: null,
    kind: "MARKET_TRUTH",
    sequence: 4,
    status: "ACCEPTED",
    occurred_at: "2024-07-03T09:47:04.000000Z",
  },
];

const handlers = {
  overview: http.get("/api/overview", () => HttpResponse.json(overview)),
  market: http.get("/api/market-truth/recent", () => HttpResponse.json(list(marketItems))),
  marketEmpty: http.get("/api/market-truth/recent", () => HttpResponse.json(list<MarketItem>([]))),
  experiments: http.get("/api/experiments", () => HttpResponse.json(list([experiment]))),
  experimentDetail: http.get("/api/experiments/:experimentId", ({ params }) =>
    params.experimentId === experiment.experiment_id
      ? HttpResponse.json({ item: experimentDetail })
      : closedError("NOT_FOUND", 404),
  ),
  paper: [
    http.get("/api/paper/summary", () => HttpResponse.json(paperSummary)),
    http.get("/api/paper/orders", () => HttpResponse.json(list(paperOrders))),
    http.get("/api/paper/fills", () => HttpResponse.json(list(paperFills))),
    http.get("/api/paper/positions", () => HttpResponse.json(list(paperPositions))),
    http.get("/api/paper/risk", () => HttpResponse.json(paperRisk)),
  ],
  paperUnavailable: http.get("/api/paper/*", () => closedError("SOURCE_UNAVAILABLE", 503)),
  health: http.get("/api/health", () => HttpResponse.json(health)),
  audit: http.get("/api/audit/recent", () => HttpResponse.json(list(auditItems))),
};

/** Fresh router + isolated query client per story so states never leak between stories. */
function StoryHost({ path, seed, refreshOnMount }: { path: string; seed?: boolean; refreshOnMount?: boolean }) {
  const [client] = useState(() => {
    const queryClient = createQueryClient();
    if (seed) queryClient.setQueryData(overviewQuery.queryKey, overview);
    return queryClient;
  });
  useEffect(() => {
    // Mirrors the Refresh control: invalidate only the active family.
    if (refreshOnMount) void client.invalidateQueries({ queryKey: familyKey("overview") });
  }, [client, refreshOnMount]);
  return (
    <MemoryRouter initialEntries={[path]}>
      <QueryClientProvider client={client}>
        <ControlCenter />
      </QueryClientProvider>
    </MemoryRouter>
  );
}

const meta = preview.meta({
  title: "Control Center/Foundation",
  component: StoryHost,
  args: { path: "/overview" },
});

// S10-CC-STREAM-01: every story receives the exact disabled transport status, so the shell never
// opens a browser stream in Storybook. No story mocks or opens a real stream.
const streamStatusDisabled: StreamStatus = {
  read_only: true,
  enabled: false,
  transport: "SSE",
  semantics: "SERVER_PACED_ACTIVE_FAMILY_REFRESH",
  source_push: false,
  canonical_event_stream: false,
  domain_freshness_guarantee: false,
  replay_available: false,
  base_tick_seconds: 5,
  refresh_seconds_by_family: {
    overview: 10,
    market: 5,
    experiments: 30,
    strategies: 30,
    hermes: 30,
    alpha: 30,
    ops: 5,
    paper: 5,
    audit: 10,
  },
};
const streamStatusDisabledHandler = http.get("/api/stream/status", () => HttpResponse.json(streamStatusDisabled));

const mock =
  (...items: (HttpHandler | HttpHandler[])[]) =>
  ({ msw }: { msw: { use: (...handlers: HttpHandler[]) => void } }) => {
    msw.use(streamStatusDisabledHandler, ...items.flat());
  };

export const OverviewHealthy = meta.story({
  args: { path: "/overview" },
  beforeEach: mock(handlers.overview),
});

export const OverviewSourceUnavailable = meta.story({
  args: { path: "/overview" },
  beforeEach: mock(http.get("/api/overview", () => closedError("SOURCE_UNAVAILABLE", 503))),
});

export const MarketTruthPopulated = meta.story({
  args: { path: "/markets" },
  beforeEach: mock(handlers.market),
});

export const MarketTruthEmpty = meta.story({
  args: { path: "/markets" },
  beforeEach: mock(handlers.marketEmpty),
});

export const ExperimentsPopulated = meta.story({
  args: { path: "/experiments" },
  beforeEach: mock(handlers.experiments, handlers.experimentDetail),
});

export const ExperimentsWithDetail = meta.story({
  args: { path: "/experiments" },
  beforeEach: mock(handlers.experiments, handlers.experimentDetail),
  play: async ({ canvas, userEvent }) => {
    await userEvent.click(await canvas.findByRole("button", { name: experiment.experiment_id }));
    await canvas.findByText("evidence_receipt_ids");
  },
});

export const PaperOperationsPopulated = meta.story({
  args: { path: "/paper" },
  beforeEach: mock(handlers.paper),
});

export const PaperOperationsSourceUnavailable = meta.story({
  args: { path: "/paper" },
  beforeEach: mock(handlers.paperUnavailable),
});

export const AuditHealthHealthy = meta.story({
  args: { path: "/audit" },
  beforeEach: mock(handlers.health, handlers.audit),
});

// The request never resolves, so the first-load state is held deterministically.
export const LoadingState = meta.story({
  args: { path: "/overview" },
  beforeEach: mock(
    http.get("/api/overview", async () => {
      await delay("infinite");
      return HttpResponse.json(overview);
    }),
  ),
});

// Cached evidence stays visible while the active family refetches; the refetch never resolves.
export const ManualRefreshInProgress = meta.story({
  args: { path: "/overview", seed: true, refreshOnMount: true },
  beforeEach: mock(
    http.get("/api/overview", async () => {
      await delay("infinite");
      return HttpResponse.json(overview);
    }),
  ),
});

// Backend INTERNAL_ERROR and a browser-level network failure both render closed safe codes only.
export const GenericSafeBackendError = meta.story({
  args: { path: "/audit" },
  beforeEach: mock(
    http.get("/api/health", () => closedError("INTERNAL_ERROR", 500)),
    http.get("/api/audit/recent", () => HttpResponse.error()),
  ),
});

// ---------------------------------------------------------------------------
// S10-CC-RESEARCH-01: Strategies + Hermes reference states. Every /api/strategies* and
// /api/hermes* request below is intercepted by MSW; fixtures mirror the backend DTOs.
// ---------------------------------------------------------------------------

const hex = (character: string) => character.repeat(64);
const familyId = "strategyfamily:sha256:" + hex("1");
const rootId = "strategyversion:sha256:" + hex("a");
const childId = "strategyversion:sha256:" + hex("b");
const policyId = "portfolioauthoritypolicy:sha256:" + hex("2");
const currentAssessmentId = "hermesstrategyassessment:sha256:" + hex("c");
const staleAssessmentId = "hermesstrategyassessment:sha256:" + hex("d");
const missingAssessmentId = "hermesstrategyassessment:sha256:" + hex("e");

const latestCurrent: LatestHermesAssessment = {
  assessment_id: currentAssessmentId,
  information_cutoff: "2026-10-01T00:00:00Z",
  confidence_label: "moderate",
  lifecycle_action: "CONTINUE",
  recommended_health_state: "HEALTHY",
  risk_direction: "UNCHANGED",
  target_risk_band: null,
  context_status: "CURRENT",
};

const childSummary: StrategySummary = {
  strategy_version_id: childId,
  strategy_family_id: familyId,
  parent_strategy_version_id: rootId,
  strategy_label: "weather-edge child",
  evidence_posture: "REPEATABLE_STATISTICAL",
  adaptation_class: "BOUNDED_ADAPTATION",
  created_time_ns: 3,
  current_health_state: "HEALTHY",
  current_allocation: {
    allocation_id: "strategyriskallocation:sha256:" + hex("3"),
    policy_id: policyId,
    risk_band: "EXPLORATORY_LIVE",
    active_budget_usd: "50",
    allocation_basis: "DIRECT_DECISION",
    valid_from_ns: 100,
    valid_until_ns: null,
  },
  active_restriction_count: 1,
  evidence_ref_count: 2,
  latest_hermes_assessment: latestCurrent,
};
const rootSummary: StrategySummary = {
  strategy_version_id: rootId,
  strategy_family_id: familyId,
  parent_strategy_version_id: null,
  strategy_label: "weather-edge root",
  evidence_posture: "REPEATABLE_STATISTICAL",
  adaptation_class: "ROOT",
  created_time_ns: 2,
  current_health_state: "NEW",
  current_allocation: null,
  active_restriction_count: 0,
  evidence_ref_count: 0,
  latest_hermes_assessment: null,
};

const childDetail: StrategyDetail = {
  strategy_version_id: childId,
  strategy_family_id: familyId,
  parent_strategy_version_id: rootId,
  strategy_label: childSummary.strategy_label,
  evidence_posture: childSummary.evidence_posture,
  adaptation_class: childSummary.adaptation_class,
  strategy_code_identity: "strategy_code:weather-edge-v2",
  created_time_ns: 3,
  creation_provenance: "fixture:storybook",
  evidence_refs: ["evidence:forecast-skill-study", "experiment:sha256:" + hex("4")],
  family: { strategy_family_id: familyId, family_key: "weather.edge", family_label: "Weather edge" },
  lineage_strategy_version_ids: [rootId, childId],
  strategy_definition: {
    thesis: { claim: "Forecast skill is underpriced near resolution" },
    universe: { category: "weather" },
    entry_rule: { signal: "forecast_gap" },
    exit_rule: { horizon: "resolution" },
    execution_rule: { style: "AGGRESSIVE_TAKER", max_slippage: "0.02" },
    parameters: { lookback: 6 },
  },
  adaptive_bounds: { lookback: { kind: "INTEGER_RANGE", min: 0, max: 10 } },
  current_state: {
    health_state: "HEALTHY",
    active_policy_id: policyId,
    allocation: childSummary.current_allocation,
    active_restrictions: [
      {
        restriction_receipt_id: "strategyrestriction:sha256:" + hex("5"),
        restriction_key: "pause.review",
        restriction_kind: "PAUSE_NEW_EXPOSURE",
        max_active_budget_usd: null,
        created_time_ns: 60,
      },
    ],
    strategy_lifecycle_context_sha256: hex("6"),
  },
  latest_hermes_assessment: latestCurrent,
};

const assessmentItem = (
  assessmentId: string,
  contextStatus: ContextStatus,
  decisionTimeNs: number,
): HermesAssessmentItem => ({
  assessment_id: assessmentId,
  strategy_version_id: contextStatus === "TARGET_MISSING" ? "strategyversion:sha256:" + hex("f") : childId,
  strategy_family_id: familyId,
  predecessor_assessment_id: null,
  information_cutoff: "2026-10-01T00:00:00Z",
  decision_time_ns: decisionTimeNs,
  trigger: "INITIAL_ASSESSMENT",
  confidence_label: "moderate",
  assessment_summary: "Balanced public evidence; the edge looks intact but thin.",
  lifecycle_action: "CONTINUE",
  recommended_health_state: "HEALTHY",
  risk_direction: "UNCHANGED",
  target_risk_band: null,
  context_status: contextStatus,
  canonical_soft_strategy_decision: true,
});

const currentAssessment = assessmentItem(currentAssessmentId, "CURRENT", 3000);
const assessmentDetail: HermesAssessmentDetail = {
  ...currentAssessment,
  run_record_id: "hermesstrategyrun:sha256:" + hex("7"),
  runtime_request_id: "hermesresearchrequest:sha256:" + hex("8"),
  runtime_receipt_id: "hermesresearchreceipt:sha256:" + hex("9"),
  subject_refs: [familyId, childId],
  input_evidence_refs: ["contextevidence:sha256:" + hex("0")],
  evidence_for: ["Forecast skill persists across two seasons"],
  evidence_against: ["Book depth is thin near resolution"],
  uncertainties: ["Seasonality of forecast error"],
  known_missing_data: ["No fill history yet"],
  falsification_checks_performed: ["Searched for contrary forecast-skill studies"],
  limitations: ["Public web evidence only"],
  what_would_change_the_conclusion: ["Forecast skill collapse in the next season"],
  suggested_next_research_steps: ["Collect simulated fill evidence"],
  adaptation_recommendation: null,
  strategy_lifecycle_context_sha256: hex("6"),
  lifecycle_store_head_entry_hash: hex("a"),
  active_policy_id: policyId,
  run: {
    provider_label: "example-provider",
    model_label: "example-model",
    hermes_version: "0.21.3",
    terminal_status: "COMPLETED",
    start_utc: "2026-10-01T12:00:00Z",
    end_utc: "2026-10-01T12:00:00Z",
    estimated_cost_usd: "0.04",
    cost_status: "ESTIMATED",
    cost_source: "OFFICIAL_DOCS_SNAPSHOT",
  },
  non_authority: {
    canonical_soft_strategy_decision: true,
    no_credential_authority: true,
    no_portfolio_policy_authority: true,
    no_hard_risk_override: true,
    no_paper_execution_authority: true,
    no_order_authority: true,
    no_execution_authority: true,
    no_live_authority: true,
  },
};

const decodedParam = (value: unknown) => decodeURIComponent(String(value));

const researchHandlers = {
  strategies: http.get("/api/strategies", () => HttpResponse.json(list([childSummary, rootSummary]))),
  strategiesNoHermes: http.get("/api/strategies", () =>
    HttpResponse.json(list([{ ...childSummary, latest_hermes_assessment: null }, rootSummary])),
  ),
  strategyDetail: http.get("/api/strategies/:strategyVersionId", ({ params }) =>
    decodedParam(params.strategyVersionId) === childId
      ? HttpResponse.json({ item: childDetail })
      : closedError("NOT_FOUND", 404),
  ),
  strategiesUnavailable: [
    http.get("/api/strategies", () => closedError("SOURCE_UNAVAILABLE", 503)),
    http.get("/api/strategies/*", () => closedError("SOURCE_UNAVAILABLE", 503)),
  ],
  hermes: http.get("/api/hermes/assessments", () => HttpResponse.json(list([currentAssessment]))),
  hermesStale: http.get("/api/hermes/assessments", () =>
    HttpResponse.json(
      list([
        assessmentItem(staleAssessmentId, "STALE_CONTEXT", 2000),
        assessmentItem(missingAssessmentId, "TARGET_MISSING", 1000),
      ]),
    ),
  ),
  hermesDetail: http.get("/api/hermes/assessments/:assessmentId", ({ params }) =>
    decodedParam(params.assessmentId) === currentAssessmentId
      ? HttpResponse.json({ item: assessmentDetail })
      : closedError("NOT_FOUND", 404),
  ),
  hermesUnavailable: http.get("/api/hermes/*", () => closedError("SOURCE_UNAVAILABLE", 503)),
};

export const StrategiesPopulatedCurrentHermes = meta.story({
  args: { path: "/strategies" },
  beforeEach: mock(researchHandlers.strategies, researchHandlers.strategyDetail),
});

export const StrategiesSelectedDetail = meta.story({
  args: { path: "/strategies" },
  beforeEach: mock(researchHandlers.strategies, researchHandlers.strategyDetail),
  play: async ({ canvas, userEvent }) => {
    await userEvent.click(await canvas.findByRole("button", { name: childSummary.strategy_label }));
    await canvas.findByText("Lineage · root → this version");
  },
});

export const StrategiesNoHermesAssessment = meta.story({
  args: { path: "/strategies" },
  beforeEach: mock(researchHandlers.strategiesNoHermes, researchHandlers.strategyDetail),
});

export const StrategiesSourceUnavailable = meta.story({
  args: { path: "/strategies" },
  beforeEach: mock(researchHandlers.strategiesUnavailable),
});

export const HermesPopulatedCurrent = meta.story({
  args: { path: "/hermes" },
  beforeEach: mock(researchHandlers.hermes, researchHandlers.hermesDetail),
});

export const HermesStaleContext = meta.story({
  args: { path: "/hermes" },
  beforeEach: mock(researchHandlers.hermesStale, researchHandlers.hermesDetail),
});

export const HermesSelectedDetail = meta.story({
  args: { path: "/hermes" },
  beforeEach: mock(researchHandlers.hermes, researchHandlers.hermesDetail),
  play: async ({ canvas, userEvent }) => {
    await userEvent.click(await canvas.findByRole("button", { name: currentAssessmentId }));
    await canvas.findByText("Non-authority");
  },
});

export const HermesSourceUnavailable = meta.story({
  args: { path: "/hermes" },
  beforeEach: mock(researchHandlers.hermesUnavailable),
});

// ---------------------------------------------------------------------------
// S10-CC-RESEARCH-02: Alpha Research Memory + Discovery Queue reference states. Every
// /api/alpha/** request below is intercepted by MSW (unmatched alpha paths get a closed
// NOT_FOUND); fixtures mirror the backend DTOs. Source locators are text only.
// ---------------------------------------------------------------------------

const alphaFlags = {
  advisory_only: true,
  no_execution_authority: true,
  no_strategy_authority: true,
  no_qualification_authority: true,
} as const;
const registryHead = "alpharegistryentry:sha256:" + hex("1");
const laterRegistryHead = "alpharegistryentry:sha256:" + hex("2");
const candidateA = "alphacandidate:sha256:" + hex("a");
const candidateB = "alphacandidate:sha256:" + hex("b");
const familyOne = "alphafamily:sha256:" + hex("c");
const familyTwo = "alphafamily:sha256:" + hex("d");
const episodeRoot = "alphaepisode:sha256:" + hex("1");
const episodeSupportive = "alphaepisode:sha256:" + hex("2");
const episodeNoEdge = "alphaepisode:sha256:" + hex("3");
const episodeReopen = "alphaepisode:sha256:" + hex("4");
const episodeData = "alphaepisode:sha256:" + hex("5");
const sourceOfficial = "alphasource:sha256:" + hex("6");
const sourceReference = "alphasource:sha256:" + hex("7");

const alphaMemory: AlphaMemorySummary = {
  head_entry_hash: registryHead,
  total_rows: 13,
  total_payload_bytes: 24576,
  record_counts: { research_source_references: 2, opportunity_candidates: 2, hypothesis_families: 3, research_episodes: 6 },
  ...alphaFlags,
};

const candidateSummaryA: AlphaCandidateSummary = {
  sequence_number: 2,
  candidate_id: candidateA,
  candidate_version: "v1",
  title: "Cold-weather scoring suppression",
  research_question: "Does forecast cold bias recorded totals in this exact scope?",
  subject_refs: ["market:polymarket:alpha"],
  evidence_lanes: ["FUNDAMENTAL", "WEATHER"],
  is_multi_lane: true,
  scope_key: "scope-alpha",
  mechanism_hint: "temperature suppresses scoring",
  novelty_fingerprint: "alphanovelty:sha256:" + hex("8"),
  human_review_required: true,
  family_count: 2,
  episode_count: 5,
  leaf_episode_count: 3,
};
const candidateSummaryB: AlphaCandidateSummary = {
  ...candidateSummaryA,
  sequence_number: 10,
  candidate_id: candidateB,
  title: "Resolution-source wording drift",
  research_question: "Does rule wording drift precede re-pricing?",
  subject_refs: ["market:polymarket:beta"],
  evidence_lanes: ["RESOLUTION_RULES"],
  is_multi_lane: false,
  scope_key: "scope-beta",
  family_count: 1,
  episode_count: 1,
  leaf_episode_count: 1,
};

const sources: AlphaSourceReference[] = [
  {
    source_reference_id: sourceOfficial,
    source_kind: "PUBLIC_HTTPS",
    source_class: "OFFICIAL",
    source_locator: "https://docs.polymarket.com/rules",
    title: "Resolution rules",
    observed_at: "2026-09-20T00:00:00Z",
    content_sha256: null,
    provenance: "human_research",
    public_research_only: true,
    advisory_only: true,
    no_execution_authority: true,
  },
  {
    source_reference_id: sourceReference,
    source_kind: "PUBLIC_HTTPS",
    source_class: "REFERENCE",
    source_locator: "https://example.org/reference",
    title: "Reference climatology",
    observed_at: "2026-09-21T00:00:00Z",
    content_sha256: hex("9"),
    provenance: "human_research",
    public_research_only: true,
    advisory_only: true,
    no_execution_authority: true,
  },
];

const episodeSummary = (
  id: string,
  family: string,
  state: AlphaEpisodeSummary["result_state"],
  sequence: number,
  links: { predecessor?: string; reopened?: string } = {},
): AlphaEpisodeSummary => ({
  sequence_number: sequence,
  research_episode_id: id,
  hypothesis_family_id: family,
  predecessor_episode_id: links.predecessor ?? null,
  reopened_episode_id: links.reopened ?? null,
  result_state: state,
  confidence_label: "moderate",
  evidence_lanes: ["WEATHER"],
  research_as_of: "2026-09-20T00:00:00Z",
  producer_type: "HUMAN_RESEARCH",
  human_review_required: true,
});

const familyRecord = (id: string, name: string, sequence: number, episodes: number, leaves: string[]) => ({
  sequence_number: sequence,
  hypothesis_family_id: id,
  family_version: "v1",
  family_name: name,
  mechanism_key: "mechanism-" + name.toLowerCase().replace(/[^a-z]+/g, "-"),
  mechanism_dimensions_json: '{"driver":"temperature"}',
  mechanism_fingerprint: "alphamechanism:sha256:" + hex(sequence === 3 ? "a" : "b"),
  falsifiable_theme: "Cold reduces recorded totals in the exact scope",
  predecessor_family_id: null,
  creation_provenance: "human_research",
  human_review_required: true,
  ...alphaFlags,
  episode_count: episodes,
  leaf_episode_ids: leaves,
});

const candidateDetailA: AlphaCandidateDetail = {
  candidate: {
    candidate_id: candidateA,
    candidate_version: "v1",
    title: candidateSummaryA.title,
    research_question: candidateSummaryA.research_question,
    thesis: "Cold forecasts suppress scoring in this exact recorded scope.",
    subject_refs: candidateSummaryA.subject_refs,
    evidence_lanes: candidateSummaryA.evidence_lanes,
    is_multi_lane: true,
    scope_key: "scope-alpha",
    mechanism_hint: candidateSummaryA.mechanism_hint,
    novelty_dimensions_json: '{"mechanism_key":"mechanism-alpha","scope_key":"scope-alpha","subject_keys":["alpha"]}',
    novelty_fingerprint: candidateSummaryA.novelty_fingerprint,
    discovery_provenance: "human_research",
    human_review_required: true,
    ...alphaFlags,
  },
  hypothesis_families: [
    familyRecord(familyOne, "Cold scoring suppression", 3, 4, [episodeSupportive, episodeReopen]),
    familyRecord(familyTwo, "Wind-driven pace", 4, 1, [episodeData]),
  ],
  research_episodes: [
    episodeSummary(episodeRoot, familyOne, "WATCH_FOR_CHANGE", 5),
    episodeSummary(episodeData, familyTwo, "DATA_INSUFFICIENT", 6),
    episodeSummary(episodeSupportive, familyOne, "RESEARCH_SUPPORTIVE", 7, { predecessor: episodeRoot }),
    episodeSummary(episodeNoEdge, familyOne, "NO_EDGE_CURRENTLY", 8, { predecessor: episodeRoot }),
    episodeSummary(episodeReopen, familyOne, "REOPEN_TRIGGERED", 9, { reopened: episodeNoEdge }),
  ],
  source_references: sources,
  deterministic_evidence_refs: ["det-alpha-1", "det-alpha-5", "det-alpha-2"],
  lineage_summary: {
    family_count: 2,
    episode_count: 5,
    leaf_episode_count: 3,
    leaf_episode_ids: [episodeData, episodeSupportive, episodeReopen],
  },
};

const reopenEpisodeDetail: AlphaEpisodeDetail = {
  research_episode_id: episodeReopen,
  episode_version: "v1",
  candidate_id: candidateA,
  hypothesis_family_id: familyOne,
  predecessor_episode_id: null,
  reopened_episode_id: episodeNoEdge,
  result_state: "REOPEN_TRIGGERED",
  confidence_label: "low",
  evidence_lanes: ["WEATHER"],
  is_multi_lane: false,
  exact_scope_json: '{"league":"nfl","season":"2026","venue":"outdoor"}',
  evidence_regime_json: '{"window":"2020-2025"}',
  research_question: candidateSummaryA.research_question,
  thesis: "A recorded rule change reopens the earlier no-edge result in this exact scope.",
  tested_assumptions: ["Temperature measured pre-kickoff"],
  evidence_for: ["Rule change alters the totals definition"],
  evidence_against: ["Prior no-edge result in the same scope"],
  uncertainties: ["Dome games"],
  known_missing_data: ["Post-change sample is small"],
  falsification_checks_performed: ["Checked warm-weather control"],
  limitations: ["Small sample"],
  what_would_change_the_conclusion: ["A post-change warm-weather run"],
  suggested_next_research_steps: ["Re-run the deterministic cohort after the change"],
  source_reference_ids: [sourceOfficial],
  source_references: [sources[0]],
  deterministic_evidence_refs: ["det-alpha-4"],
  material_change_basis: ["Resolution rule text changed"],
  producer_type: "HUMAN_RESEARCH",
  producer_version: "human-v1",
  producer_receipt_ref: null,
  research_as_of: "2026-09-25T00:00:00Z",
  creation_provenance: "human_research",
  human_review_required: true,
  ...alphaFlags,
};

const coverage = [
  { research_archetype: "resolution_contract", coverage_state: "UNKNOWN" },
  { research_archetype: "fundamental_public_info", coverage_state: "SUPPORTED" },
  { research_archetype: "domain_specific", coverage_state: "SUPPORTED" },
];
const triageAlphaId = "alphatriage:sha256:" + hex("a");
const triageSummary = (
  id: string,
  market: string,
  disposition: string,
  priority: string,
  extra: Partial<DiscoveryTriageSummary> = {},
): DiscoveryTriageSummary => ({
  market_triage_decision_id: id,
  market_id: "market:polymarket:" + market,
  event_id: "event:polymarket:" + market,
  category: "weather",
  eligibility: "ELIGIBLE",
  priority_class: priority,
  reopen_disposition: "NO_REOPEN",
  readiness: "READY",
  reason_codes: ["ALPHA_NO_CANONICAL_MATCH"],
  material_change_event_id: null,
  newly_observed_locally: false,
  final_disposition: disposition,
  selected_lane: ["CORE_PRIORITY", "EXPLORATION", "AUDIT"].includes(disposition) ? disposition : null,
  analysis_temporal_mode: "CURRENT_BUILD_ANALYSIS",
  alpha_memory_temporal_posture: "CURRENT_REGISTRY_BUILD_TIME_ONLY",
  alpha_registry_head_entry_hash: registryHead,
  matched_candidate_ids: [],
  matched_hypothesis_family_ids: [],
  matched_research_episode_ids: [],
  coverage,
  ...extra,
});
const triageAlpha = triageSummary(triageAlphaId, "alpha", "CORE_PRIORITY", "EXISTING_RESEARCH_FOLLOWUP", {
  reopen_disposition: "REOPEN_REVIEW_REQUIRED",
  reason_codes: ["MATERIAL_CHANGE_EXISTING_RESEARCH"],
  material_change_event_id: "alphachange:sha256:" + hex("e"),
  matched_candidate_ids: [candidateA],
  matched_hypothesis_family_ids: [familyOne, familyTwo],
  matched_research_episode_ids: [episodeRoot, episodeSupportive, episodeNoEdge, episodeReopen, episodeData],
});

const discoveryQueue: DiscoveryQueueResponse = {
  discovery_registry_head_entry_hash: "alphadiscoveryentry:sha256:" + hex("f"),
  queue_sequence_number: 11,
  queue: {
    alpha_research_queue_snapshot_id: "alphaqueue:sha256:" + hex("1"),
    policy_id: "alphadiscoverypolicy:sha256:" + hex("2"),
    universe_id: "alphauniverse:sha256:" + hex("3"),
    comparison_prior_universe_id: "alphauniverse:sha256:" + hex("4"),
    analysis_temporal_mode: "CURRENT_BUILD_ANALYSIS",
    alpha_memory_temporal_posture: "CURRENT_REGISTRY_BUILD_TIME_ONLY",
    alpha_registry_head_entry_hash: registryHead,
    historical_alpha_memory_available: false,
    historical_selection_replay_valid: false,
    queue_capacity: 4,
    configured_exploration_slots: 1,
    configured_audit_slots: 1,
    exploration_selected_count: 0,
    audit_selected_count: 1,
    unused_exploration_slots: 1,
    unused_audit_slots: 0,
    unused_capacity_reason_codes: ["EXPLORATION_POOL_EXHAUSTED"],
    max_per_category: 2,
    prior_only_market_ids: ["market:polymarket:omega"],
    ...alphaFlags,
  },
  policy: {
    alpha_discovery_policy_id: "alphadiscoverypolicy:sha256:" + hex("2"),
    policy_version: "fixture/1",
    eligible_market_statuses: ["open"],
    metadata_freshness_seconds: 60,
    order_book_freshness_seconds: 30,
    resolution_rule_freshness_seconds: 120,
    queue_capacity: 4,
    exploration_slots: 1,
    audit_slots: 1,
    max_per_category: 2,
    research_archetype_taxonomy_version: "alpha-archetypes/1",
  },
  universe: {
    alpha_universe_snapshot_id: "alphauniverse:sha256:" + hex("3"),
    as_of: "2026-10-01T00:00:30Z",
    cutoff_mode: "AS_OF_INGESTION_TIME",
    query_engine_version: "point-in-time-as-of-query@1.0.0",
    query_parameter_set_id: "s10-alpha-02:1.0.0",
    coverage_scope: "BOUNDED_OBSERVED_UNIVERSE",
    external_universe_completeness: "UNPROVEN",
    market_count: 6,
  },
  lanes: {
    core: [
      triageAlpha,
      triageSummary("alphatriage:sha256:" + hex("b"), "beta", "CORE_PRIORITY", "EXISTING_RESEARCH_FOLLOWUP", {
        reason_codes: ["EXISTING_RESEARCH_FOLLOWUP"],
        matched_candidate_ids: [candidateB],
      }),
    ],
    exploration: [],
    audit: [triageSummary("alphatriage:sha256:" + hex("c"), "epsilon", "AUDIT", "NEW_RESEARCH")],
    deferred: [
      triageSummary("alphatriage:sha256:" + hex("d"), "delta", "DEFERRED", "DEFER_CAPTURE_REFRESH", {
        eligibility: "DEFERRED",
        readiness: "DEFERRED",
        reopen_disposition: "REOPEN_UNAVAILABLE_DATA",
        reason_codes: ["METADATA_CONFLICT"],
      }),
    ],
    skipped_ineligible: [
      triageSummary("alphatriage:sha256:" + hex("e"), "gamma", "SKIPPED_INELIGIBLE", "INELIGIBLE", {
        eligibility: "INELIGIBLE",
        readiness: "INELIGIBLE",
        reason_codes: ["MARKET_STATUS_INELIGIBLE"],
      }),
    ],
    skipped_capacity: [
      triageSummary("alphatriage:sha256:" + hex("f"), "zeta", "SKIPPED_CAPACITY", "NEW_RESEARCH", {
        newly_observed_locally: true,
        reason_codes: ["ALPHA_NO_CANONICAL_MATCH", "NEWLY_OBSERVED_LOCALLY"],
      }),
    ],
  },
};

const triageDetail = (resolution: DiscoveryTriageResponse["alpha_memory_resolution"]): DiscoveryTriageResponse => ({
  triage: {
    ...triageAlpha,
    ...alphaFlags,
    policy_id: discoveryQueue.queue.policy_id,
    universe_id: discoveryQueue.queue.universe_id,
    comparison_prior_universe_id: discoveryQueue.queue.comparison_prior_universe_id,
    capture_requests: [
      {
        request_type: "ORDER_BOOK",
        market_id: "market:polymarket:alpha",
        token_id: "token:polymarket:alpha",
        universe_id: discoveryQueue.queue.universe_id,
        policy_id: discoveryQueue.queue.policy_id,
        comparison_prior_universe_id: discoveryQueue.queue.comparison_prior_universe_id,
        reason_code: "ORDER_BOOK_STALE",
        priority_class: "EXISTING_RESEARCH_FOLLOWUP",
        pre_allocation_semantic_key: hex("5"),
      },
    ],
    audit_digest: null,
    audit_eligible_pool_size: null,
    audit_selection_fraction_numerator: null,
    audit_selection_fraction_denominator: null,
    historical_alpha_memory_available: false,
    historical_selection_replay_valid: false,
    historical_replay_valid_for_alpha_memory: false,
  },
  universe_market: {
    market_id: "market:polymarket:alpha",
    event_id: "event:polymarket:alpha",
    market_status: "open",
    condition_id: "condition:alpha",
    token_ids: ["token:polymarket:alpha"],
    outcome_labels: ["No", "Yes"],
    resolution_date: "2026-12-01T00:00:00Z",
    category: "weather",
    question_text: "Will the recorded total be under 41.5?",
    metadata_record_version_id: "record:sha256:" + hex("6"),
    metadata_observed_time: "2026-10-01T00:00:00Z",
    metadata_freshness: "FRESH",
    data_gap_codes: ["ORDER_BOOK_STALE"],
    resolution_rule_count: 1,
    order_book_count: 1,
  },
  material_change: {
    material_change_event_id: "alphachange:sha256:" + hex("e"),
    prior_universe_id: "alphauniverse:sha256:" + hex("4"),
    current_universe_id: "alphauniverse:sha256:" + hex("3"),
    market_id: "market:polymarket:alpha",
    hard_change_classes: ["RESOLUTION_RULE_CHANGED"],
    soft_change_classes: ["MID_PRICE_MOVED"],
    review_only_change_classes: [],
    affected_token_ids: [{ change_class: "MID_PRICE_MOVED", token_ids: ["token:polymarket:alpha"] }],
    affected_resolution_source_ids: ["resolution-source:polymarket:primary"],
    before_record_version_ids: ["record:sha256:" + hex("7")],
    after_record_version_ids: ["record:sha256:" + hex("8")],
    comparison_diagnostics: [],
    reopen_material: true,
    ...alphaFlags,
  },
  alpha_memory_resolution: resolution,
});
const resolutionEmpty = { candidates: [], hypothesis_families: [], research_episodes: [] };
const triageResolved = triageDetail({
  status: "RESOLVED",
  bound_alpha_registry_head_entry_hash: registryHead,
  candidates: [candidateSummaryA],
  hypothesis_families: candidateDetailA.hypothesis_families.map((family) => ({
    sequence_number: family.sequence_number,
    hypothesis_family_id: family.hypothesis_family_id,
    family_name: family.family_name,
    mechanism_key: family.mechanism_key,
    falsifiable_theme: family.falsifiable_theme,
  })),
  research_episodes: candidateDetailA.research_episodes,
});
const triageAlphaUnavailable = triageDetail({
  status: "UNAVAILABLE",
  bound_alpha_registry_head_entry_hash: registryHead,
  ...resolutionEmpty,
});
const triageHeadMismatch = triageDetail({
  status: "HEAD_MISMATCH",
  bound_alpha_registry_head_entry_hash: registryHead,
  ...resolutionEmpty,
});

const triageHandler = (response: DiscoveryTriageResponse) =>
  http.get("/api/alpha/discovery/triage/:marketTriageDecisionId", ({ params }) =>
    decodedParam(params.marketTriageDecisionId) === triageAlphaId
      ? HttpResponse.json(response)
      : closedError("NOT_FOUND", 404),
  );

const alphaHandlers = {
  memory: [
    http.get("/api/alpha/memory", () => HttpResponse.json(alphaMemory)),
    http.get("/api/alpha/candidates", () => HttpResponse.json(list([candidateSummaryB, candidateSummaryA]))),
    http.get("/api/alpha/candidates/:candidateId", ({ params }) =>
      decodedParam(params.candidateId) === candidateA
        ? HttpResponse.json(candidateDetailA)
        : closedError("NOT_FOUND", 404),
    ),
    http.get("/api/alpha/episodes/:researchEpisodeId", ({ params }) =>
      decodedParam(params.researchEpisodeId) === episodeReopen
        ? HttpResponse.json({ item: reopenEpisodeDetail })
        : closedError("NOT_FOUND", 404),
    ),
  ],
  queue: http.get("/api/alpha/discovery/queue", () => HttpResponse.json(discoveryQueue)),
  // Any other alpha path stays inside the browser with a closed safe code.
  fallback: http.get("/api/alpha/*", () => closedError("NOT_FOUND", 404)),
  unavailable: http.get("/api/alpha/*", () => closedError("SOURCE_UNAVAILABLE", 503)),
  memoryUnavailable: [
    http.get("/api/alpha/memory", () => closedError("SOURCE_UNAVAILABLE", 503)),
    http.get("/api/alpha/candidates", () => closedError("SOURCE_UNAVAILABLE", 503)),
  ],
};

type PlayContext = {
  canvas: {
    findByRole: (role: string, options?: { name?: string }) => Promise<HTMLElement>;
    findByText: (text: string) => Promise<HTMLElement>;
  };
  userEvent: { click: (element: Element) => Promise<void> };
};
const openDiscoveryTab = async ({ canvas, userEvent }: PlayContext) => {
  await userEvent.click(await canvas.findByRole("tab", { name: "Discovery Queue" }));
  await canvas.findByText("Latest recorded discovery queue");
};
const openAlphaTriage = async (context: PlayContext) => {
  await openDiscoveryTab(context);
  await context.userEvent.click(await context.canvas.findByRole("button", { name: "market:polymarket:alpha" }));
  await context.canvas.findByText("Alpha-memory resolution");
};

export const AlphaMemoryPopulated = meta.story({
  args: { path: "/alpha" },
  beforeEach: mock(alphaHandlers.memory, alphaHandlers.fallback),
});

export const AlphaMemoryCandidateSelected = meta.story({
  args: { path: "/alpha" },
  beforeEach: mock(alphaHandlers.memory, alphaHandlers.fallback),
  play: async ({ canvas, userEvent }) => {
    await userEvent.click(await canvas.findByRole("button", { name: candidateSummaryA.title }));
    await canvas.findByText("Novelty dimensions");
  },
});

export const AlphaMemoryEpisodeReopenLineage = meta.story({
  args: { path: "/alpha" },
  beforeEach: mock(alphaHandlers.memory, alphaHandlers.fallback),
  play: async ({ canvas, userEvent }) => {
    await userEvent.click(await canvas.findByRole("button", { name: candidateSummaryA.title }));
    await userEvent.click(await canvas.findByRole("button", { name: episodeReopen }));
    await canvas.findByText("Exact scope (this result applies here only)");
  },
});

export const AlphaMemorySourceUnavailable = meta.story({
  args: { path: "/alpha" },
  beforeEach: mock(alphaHandlers.unavailable),
});

export const AlphaDiscoveryPopulatedQueue = meta.story({
  args: { path: "/alpha" },
  beforeEach: mock(alphaHandlers.memory, alphaHandlers.queue, triageHandler(triageResolved), alphaHandlers.fallback),
  play: openDiscoveryTab,
});

export const AlphaDiscoveryTriageMaterialChange = meta.story({
  args: { path: "/alpha" },
  beforeEach: mock(alphaHandlers.memory, alphaHandlers.queue, triageHandler(triageResolved), alphaHandlers.fallback),
  play: openAlphaTriage,
});

export const AlphaDiscoveryAlphaMemoryUnavailable = meta.story({
  args: { path: "/alpha" },
  beforeEach: mock(
    alphaHandlers.memoryUnavailable,
    alphaHandlers.queue,
    triageHandler(triageAlphaUnavailable),
    alphaHandlers.fallback,
  ),
  play: openAlphaTriage,
});

export const AlphaDiscoveryHeadMismatch = meta.story({
  args: { path: "/alpha" },
  beforeEach: mock(
    http.get("/api/alpha/memory", () => HttpResponse.json({ ...alphaMemory, head_entry_hash: laterRegistryHead })),
    alphaHandlers.queue,
    triageHandler(triageHeadMismatch),
    alphaHandlers.fallback,
  ),
  play: openAlphaTriage,
});

export const AlphaDiscoverySourceUnavailable = meta.story({
  args: { path: "/alpha" },
  beforeEach: mock(alphaHandlers.memory, alphaHandlers.unavailable),
  play: async ({ canvas, userEvent }) => {
    await userEvent.click(await canvas.findByRole("tab", { name: "Discovery Queue" }));
    await canvas.findByText("SOURCE_UNAVAILABLE");
  },
});

// ---------------------------------------------------------------------------
// S10-CC-OPS-01 operations states. Every /ops request (portfolio, gateway status/audit, paper
// summary/risk) is answered by a closed handler below; the /api/ops/* fallback is closed too.
// ---------------------------------------------------------------------------

const opsHash = (seed: string) => seed.repeat(64).slice(0, 64);
const opsPolicyId = "portfolioauthoritypolicy:sha256:" + opsHash("7");
const opsVersionA = "strategyversion:sha256:" + opsHash("a");
const opsVersionB = "strategyversion:sha256:" + opsHash("b");
const opsVersionC = "strategyversion:sha256:" + opsHash("c");
const opsEvaluatedAt = 1791547200000000000;

const opsActivePolicy: OpsActivePolicy = {
  policy_id: opsPolicyId,
  predecessor_policy_id: null,
  policy_label: "Global envelope fixture",
  venue_scope: ["POLYMARKET"],
  account_scope_ref: "account:public-scope-fixture",
  effective_from_ns: 1790000000000000000,
  expires_at_ns: null,
  limits: {
    global_capital_at_risk_max_usd: "1000",
    global_gross_exposure_max_usd: "1000",
    global_daily_loss_max_usd: "100",
    global_drawdown_max_usd: "200",
    global_cumulative_loss_max_usd: "300",
    exploratory_pool_max_usd: "300",
    validated_pool_max_usd: "300",
    mature_pool_max_usd: "300",
    max_exploratory_per_strategy_usd: "100",
    max_validated_per_strategy_usd: "200",
    max_mature_per_strategy_usd: "300",
    max_per_market_usd: "50",
    max_order_notional_usd: "10",
    max_active_strategies: 3,
    max_active_markets: 10,
    max_simultaneous_open_orders: 20,
    max_mutations_per_minute: 60,
  },
  allowed_order_styles: ["AGGRESSIVE_TAKER", "PASSIVE_MAKER"],
  created_time_ns: 1790000000000000000,
};

const opsReservation = (overrides: Partial<OpsStrategyReservation>): OpsStrategyReservation => ({
  allocation_id: "strategyriskallocation:sha256:" + opsHash("1"),
  strategy_version_id: opsVersionA,
  strategy_label: "weather-root",
  policy_id: opsPolicyId,
  risk_band: "EXPLORATORY_LIVE",
  active_budget_usd: "50",
  allocation_basis: "DIRECT_DECISION",
  valid_from_ns: 1790500000000000000,
  valid_until_ns: null,
  active_at_evaluation: true,
  health_state: "HEALTHY",
  capacity_status: "PORTFOLIO_CAPACITY_VALID",
  capacity_reason_codes: [],
  active_restrictions: [],
  ...overrides,
});

const OPS_NON_AUTHORITY: OpsPortfolio["non_authority"] = {
  budget_reservation_only: true,
  actual_account_exposure_not_measured: true,
  orders_not_measured: true,
  fills_not_measured: true,
  pnl_not_measured: true,
  gate_c_not_implied: true,
  execution_not_implied: true,
  live_not_implied: true,
};

const opsPortfolio: OpsPortfolio = {
  read_only: true,
  evaluated_at_ns: opsEvaluatedAt,
  lifecycle_store_head_entry_hash: opsHash("e"),
  active_policy: opsActivePolicy,
  capacity: {
    status: "PORTFOLIO_CAPACITY_VALID",
    reason_codes: [],
    evaluated_at_ns: opsEvaluatedAt,
    policy_id: opsPolicyId,
    reserved_budget_usd: { exploratory: "50", validated: "0", mature: "0", total: "50" },
    active_real_risk_strategy_count: 1,
  },
  strategy_reservations: [
    opsReservation({}),
    opsReservation({
      allocation_id: "strategyriskallocation:sha256:" + opsHash("2"),
      strategy_version_id: opsVersionB,
      strategy_label: "weather-child",
      active_budget_usd: "40",
      allocation_basis: "PARENT_INHERITANCE",
      valid_from_ns: 1795000000000000000,
      active_at_evaluation: false,
      health_state: "NEW",
    }),
  ],
  non_authority: OPS_NON_AUTHORITY,
};

const opsPortfolioNoPolicy: OpsPortfolio = {
  ...opsPortfolio,
  active_policy: null,
  capacity: {
    status: "PORTFOLIO_CAPACITY_REJECTED",
    reason_codes: ["POLICY_NOT_ACTIVE"],
    evaluated_at_ns: opsEvaluatedAt,
    policy_id: null,
    reserved_budget_usd: { exploratory: "0", validated: "0", mature: "0", total: "0" },
    active_real_risk_strategy_count: 0,
  },
  strategy_reservations: [opsReservation({ capacity_status: null, capacity_reason_codes: [] })],
};

const opsPortfolioRejected: OpsPortfolio = {
  ...opsPortfolio,
  capacity: {
    ...opsPortfolio.capacity,
    status: "PORTFOLIO_CAPACITY_REJECTED",
    reason_codes: ["RESTRICTION_BLOCKS_ACTIVE_RISK"],
    reserved_budget_usd: { exploratory: "50", validated: "0", mature: "0", total: "50" },
  },
  strategy_reservations: [
    opsReservation({
      strategy_version_id: opsVersionC,
      strategy_label: "weather-restricted",
      capacity_status: "PORTFOLIO_CAPACITY_REJECTED",
      capacity_reason_codes: ["RESTRICTION_BLOCKS_ACTIVE_RISK"],
      active_restrictions: [
        {
          restriction_receipt_id: "strategyrestriction:sha256:" + opsHash("9"),
          restriction_key: "pause.fixture",
          restriction_kind: "PAUSE_NEW_EXPOSURE",
          max_active_budget_usd: null,
          created_time_ns: 1791000000000000000,
        },
      ],
    }),
  ],
};

const gatewayStatus: GatewayStatus = {
  read_only: true,
  authority_state: "A0_DISABLED",
  disabled: true,
  disable_reason: "OPERATOR_DISABLED",
  credential_configured: false,
  reconciliation_state: "REQUIRED",
  heartbeat_state: "DISABLED",
  user_stream_state: "DISCONNECTED",
  access_state: "UNKNOWN",
  rate_limit_until_ns: null,
  prepared_order_count: 0,
  mutation_attempt_count: 0,
  open_order_count: 0,
  gate_b_authorized: false,
  restricted_live_available: false,
  restricted_live: {
    armed: false,
    halted: false,
    create_attempt_count: 0,
    capital_at_risk_pusd: "0",
    capital_committed_pusd: "0",
    reconciliation_state: "REQUIRED",
  },
};

const gatewayStatusRestrictedLive: GatewayStatus = {
  ...gatewayStatus,
  authority_state: "A3_RESTRICTED_LIVE",
  disabled: false,
  disable_reason: null,
  access_state: "ELIGIBLE",
  reconciliation_state: "HEALTHY",
  heartbeat_state: "HEALTHY",
  restricted_live_available: true,
  restricted_live: {
    armed: false,
    halted: true,
    create_attempt_count: 1,
    capital_at_risk_pusd: "0",
    capital_committed_pusd: "0",
    reconciliation_state: "HEALTHY",
  },
};

const gatewayAudit: GatewayAuditItem[] = [
  {
    sequence: 2,
    event_id: "gatewayevent:sha256:" + opsHash("4"),
    event_type: "GATEWAY_DISABLED",
    event_time_ns: 1791000000000000000,
    event_hash: opsHash("5"),
  },
  {
    sequence: 1,
    event_id: "gatewayevent:sha256:" + opsHash("3"),
    event_type: "GATEWAY_INITIALIZED",
    event_time_ns: 1790000000000000000,
    event_hash: opsHash("6"),
  },
];

const opsHandlers = {
  portfolio: (body: OpsPortfolio) => http.get("/api/ops/portfolio", () => HttpResponse.json(body)),
  portfolioUnavailable: http.get("/api/ops/portfolio", () => closedError("SOURCE_UNAVAILABLE", 503)),
  gateway: (status: GatewayStatus) => [
    http.get("/api/gateway/status", () => HttpResponse.json(status)),
    http.get("/api/gateway/audit", () => HttpResponse.json(list(gatewayAudit))),
  ],
  gatewayUnavailable: http.get("/api/gateway/*", () => closedError("SOURCE_UNAVAILABLE", 503)),
  paper: [
    http.get("/api/paper/summary", () => HttpResponse.json(paperSummary)),
    http.get("/api/paper/risk", () => HttpResponse.json(paperRisk)),
  ],
  paperUnavailable: http.get("/api/paper/*", () => closedError("SOURCE_UNAVAILABLE", 503)),
  fallback: http.get("/api/ops/*", () => closedError("NOT_FOUND", 404)),
};

// Exactly the two panels of the failed source show the closed code; every other panel stays usable.
const expectTwoUnavailable = async (canvas: { findAllByText: (text: string) => Promise<HTMLElement[]> }) => {
  const unavailable = await canvas.findAllByText("SOURCE_UNAVAILABLE");
  if (unavailable.length !== 2) throw new Error("expected exactly two unavailable OPS surfaces");
};

export const OpsAllSourcesAvailable = meta.story({
  args: { path: "/ops" },
  beforeEach: mock(opsHandlers.portfolio(opsPortfolio), opsHandlers.gateway(gatewayStatus), opsHandlers.paper, opsHandlers.fallback),
  play: async ({ canvas }) => {
    await canvas.findByText("Budget reservations — not actual account exposure.");
    await canvas.findByText("SIMULATED PAPER ONLY.");
    await canvas.findByText("Recorded gateway state — not a fresh account, host or network check.");
    await canvas.findByText("GATEWAY_DISABLED");
  },
});

export const OpsNoActivePolicy = meta.story({
  args: { path: "/ops" },
  beforeEach: mock(
    opsHandlers.portfolio(opsPortfolioNoPolicy),
    opsHandlers.gateway(gatewayStatus),
    opsHandlers.paper,
    opsHandlers.fallback,
  ),
  play: async ({ canvas }) => {
    await canvas.findByText("POLICY_NOT_ACTIVE");
    await canvas.findByText("No per-strategy result from the canonical evaluator");
  },
});

export const OpsCapacityRejectedRestriction = meta.story({
  args: { path: "/ops" },
  beforeEach: mock(
    opsHandlers.portfolio(opsPortfolioRejected),
    opsHandlers.gateway(gatewayStatus),
    opsHandlers.paper,
    opsHandlers.fallback,
  ),
  play: async ({ canvas }) => {
    await canvas.findByText("pause.fixture");
  },
});

export const OpsGatewayUnavailable = meta.story({
  args: { path: "/ops" },
  beforeEach: mock(opsHandlers.portfolio(opsPortfolio), opsHandlers.gatewayUnavailable, opsHandlers.paper, opsHandlers.fallback),
  play: async ({ canvas }) => {
    await canvas.findByText("Global envelope fixture");
    await canvas.findByText("Paper free cash");
    await expectTwoUnavailable(canvas);
  },
});

export const OpsPaperUnavailable = meta.story({
  args: { path: "/ops" },
  beforeEach: mock(opsHandlers.portfolio(opsPortfolio), opsHandlers.gateway(gatewayStatus), opsHandlers.paperUnavailable, opsHandlers.fallback),
  play: async ({ canvas }) => {
    await canvas.findByText("Global envelope fixture");
    await canvas.findByText("GATEWAY_DISABLED");
    await expectTwoUnavailable(canvas);
  },
});

export const OpsRecordedRestrictedLive = meta.story({
  args: { path: "/ops" },
  beforeEach: mock(
    opsHandlers.portfolio(opsPortfolio),
    opsHandlers.gateway(gatewayStatusRestrictedLive),
    opsHandlers.paper,
    opsHandlers.fallback,
  ),
  play: async ({ canvas }) => {
    await canvas.findByText("A3_RESTRICTED_LIVE");
    await canvas.findByText("Recorded restricted-live summary");
  },
});
