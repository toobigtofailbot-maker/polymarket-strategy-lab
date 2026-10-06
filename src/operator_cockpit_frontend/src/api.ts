import { QueryClient, queryOptions } from "@tanstack/react-query";

// Same-origin only. Local development reaches the loopback backend through the Vite dev proxy;
// the application never names a host, reads an environment URL or sends credentials.
export const API_BASE = "/api";

export type ListResponse<T> = { items: T[]; count: number; limit: number };

export type Health = {
  status: "OK" | "DEGRADED";
  read_only: true;
  wp169: { configured: boolean; readable: boolean };
  wp170: { configured: boolean; readable: boolean };
  paper: { configured: boolean; readable: boolean };
  gateway: { configured: boolean; readable: boolean };
};
export type Overview = {
  read_only: true;
  market_truth: {
    normalized_count: number;
    accepted_count: number;
    quarantined_count: number;
    open_gap_count: number;
    latest_received_at: string | null;
  };
  experiments: {
    experiment_count: number;
    lifecycle_count: number;
    evidence_count: number;
  };
  recent_activity: { market_truth_count: number; audit_count: number };
};
export type MarketItem = {
  observation_id: string;
  source_kind: string;
  event_kind: string;
  market_id: string | null;
  asset_id: string | null;
  event_time: string | null;
  received_at: string;
  status: string;
  book_ready: boolean;
};
export type Experiment = {
  experiment_id: string;
  experiment_family_id: string;
  trial_number: number;
  hypothesis_id: string;
  preregistered_at: string;
  lifecycle_state: string | null;
  result_status: string | null;
  oos_exposure_ordinal: number | null;
};
export type ExperimentDetail = Experiment & {
  dataset_binding_id: string;
  research_dataset_manifest_id: string;
  feature_definition_ids: string[];
  feature_set_id: string;
  label_definition_id: string;
  split_assignment_id: string;
  primary_metric_id: string;
  secondary_metric_ids: string[];
  baseline_id: string;
  cost_model_reference: string;
  lifecycle_receipt_ids: string[];
  evidence_receipt_ids: string[];
};
export type AuditItem = {
  source: "WP169" | "WP170";
  record_id: string | null;
  experiment_id: string | null;
  kind: string;
  sequence: number;
  status: string;
  occurred_at: string;
};
export type PaperSummary = {
  session_id: string;
  control_state: string;
  reconciliation_state: string;
  cash: string;
  free_cash: string;
  reserved_cash: string;
  equity: string | null;
  realized_pnl: string;
  unrealized_pnl: string | null;
  open_order_count: number;
  fill_count: number;
  markout_count: number;
  last_market_receive_ns: number | null;
  simulated_paper_only: true;
};
export type PaperOrder = {
  order_id: string;
  market_id: string;
  asset_id: string;
  side: string;
  order_style: string;
  quantity: string;
  filled_quantity: string;
  average_fill_price: string | null;
  fee_paid: string;
  status: string;
};
export type PaperFill = {
  fill_id: string;
  order_id: string;
  side: string;
  quantity: string;
  price: string;
  fee: string;
  spread_cost: string;
  depth_slippage_cost: string;
  latency_cost: string;
  adverse_selection_cost: string | null;
  markout_status: string;
  fill_kind: "SIMULATED_PAPER_FILL";
};
export type PaperPosition = {
  market_id: string;
  asset_id: string;
  quantity: string;
  cost_basis: string;
  realized_pnl: string;
  mark: string | null;
  marked_value: string | null;
};
export type PaperRisk = {
  limits: { max_open_orders: number };
  utilization: { open_orders: number; max_open_orders: number; reserved_cash: string };
  deny_count: number;
  resolution_pending: string[];
  latest_decision: { result: string; reason_codes: string[] } | null;
};

// Closed error vocabulary: the four backend codes plus two frontend transport codes. Nothing
// else (URL, path, body, stack, exception text) is ever surfaced to the operator.
const BACKEND_ERROR_CODES = ["INVALID_INPUT", "NOT_FOUND", "SOURCE_UNAVAILABLE", "INTERNAL_ERROR"] as const;
export type SafeErrorCode =
  | (typeof BACKEND_ERROR_CODES)[number]
  | "NETWORK_UNAVAILABLE"
  | "MALFORMED_RESPONSE";

export class SafeApiError extends Error {
  readonly code: SafeErrorCode;
  constructor(code: SafeErrorCode) {
    super(code);
    this.name = "SafeApiError";
    this.code = code;
  }
}

export function toSafeErrorCode(error: unknown): SafeErrorCode {
  return error instanceof SafeApiError ? error.code : "INTERNAL_ERROR";
}

function backendErrorCode(body: unknown): SafeErrorCode {
  if (typeof body === "object" && body !== null && "error" in body) {
    const code = (body as { error?: { code?: unknown } }).error?.code;
    const known = BACKEND_ERROR_CODES.find((candidate) => candidate === code);
    if (known) return known;
  }
  return "INTERNAL_ERROR";
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(API_BASE + path, {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "omit",
      signal,
    });
  } catch (cause) {
    if (signal?.aborted) throw cause;
    throw new SafeApiError("NETWORK_UNAVAILABLE");
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new SafeApiError(response.ok ? "MALFORMED_RESPONSE" : "INTERNAL_ERROR");
  }
  if (!response.ok) throw new SafeApiError(backendErrorCode(body));
  if (typeof body !== "object" || body === null) throw new SafeApiError("MALFORMED_RESPONSE");
  return body as T;
}

// Query keys are grouped by route family so a manual refresh can target exactly one page.
export type QueryFamily = "overview" | "market" | "experiments" | "paper" | "audit";

export const familyKey = (family: QueryFamily) => ["cc", family] as const;

export const overviewQuery = queryOptions({
  queryKey: [...familyKey("overview"), "summary"],
  queryFn: ({ signal }) => getJson<Overview>("/overview", signal),
});
export const marketRecentQuery = queryOptions({
  queryKey: [...familyKey("market"), "recent"],
  queryFn: ({ signal }) => getJson<ListResponse<MarketItem>>("/market-truth/recent", signal),
});
export const experimentsQuery = queryOptions({
  queryKey: [...familyKey("experiments"), "list"],
  queryFn: ({ signal }) => getJson<ListResponse<Experiment>>("/experiments", signal),
});
export const experimentDetailQuery = (experimentId: string) =>
  queryOptions({
    queryKey: [...familyKey("experiments"), "detail", experimentId],
    queryFn: async ({ signal }) =>
      (await getJson<{ item: ExperimentDetail }>("/experiments/" + encodeURIComponent(experimentId), signal)).item,
  });
export const paperSummaryQuery = queryOptions({
  queryKey: [...familyKey("paper"), "summary"],
  queryFn: ({ signal }) => getJson<PaperSummary>("/paper/summary", signal),
});
export const paperOrdersQuery = queryOptions({
  queryKey: [...familyKey("paper"), "orders"],
  queryFn: ({ signal }) => getJson<ListResponse<PaperOrder>>("/paper/orders", signal),
});
export const paperFillsQuery = queryOptions({
  queryKey: [...familyKey("paper"), "fills"],
  queryFn: ({ signal }) => getJson<ListResponse<PaperFill>>("/paper/fills", signal),
});
export const paperPositionsQuery = queryOptions({
  queryKey: [...familyKey("paper"), "positions"],
  queryFn: ({ signal }) => getJson<ListResponse<PaperPosition>>("/paper/positions", signal),
});
export const paperRiskQuery = queryOptions({
  queryKey: [...familyKey("paper"), "risk"],
  queryFn: ({ signal }) => getJson<PaperRisk>("/paper/risk", signal),
});
export const healthQuery = queryOptions({
  queryKey: [...familyKey("audit"), "health"],
  queryFn: ({ signal }) => getJson<Health>("/health", signal),
});
export const auditRecentQuery = queryOptions({
  queryKey: [...familyKey("audit"), "recent"],
  queryFn: ({ signal }) => getJson<ListResponse<AuditItem>>("/audit/recent", signal),
});

// Cockpit reads can replay verified stores, so nothing refetches on its own: no retry, no
// focus/reconnect refetch, no interval. Data changes only when the operator presses Refresh.
// Query-cache staleness is an implementation detail, never domain freshness.
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
        refetchOnReconnect: false,
        staleTime: Infinity,
      },
    },
  });
}
