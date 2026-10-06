import { useEffect, useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { delay, http, HttpResponse, type HttpHandler } from "msw";
import { MemoryRouter } from "react-router";
import preview from "../.storybook/preview";
import {
  createQueryClient,
  familyKey,
  overviewQuery,
  type AuditItem,
  type ContextStatus,
  type Experiment,
  type ExperimentDetail,
  type Health,
  type HermesAssessmentDetail,
  type HermesAssessmentItem,
  type LatestHermesAssessment,
  type ListResponse,
  type MarketItem,
  type Overview,
  type PaperFill,
  type PaperOrder,
  type PaperPosition,
  type PaperRisk,
  type PaperSummary,
  type StrategyDetail,
  type StrategySummary,
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

const mock =
  (...items: (HttpHandler | HttpHandler[])[]) =>
  ({ msw }: { msw: { use: (...handlers: HttpHandler[]) => void } }) => {
    msw.use(...items.flat());
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
