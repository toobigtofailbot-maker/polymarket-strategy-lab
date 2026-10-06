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

// S10-CC-RESEARCH-01 read models. StrategyLifecycle state, Hermes soft judgments and any
// portfolio / execution / Gate-C / live authority are separate concepts and stay separate here.
export type ContextStatus = "CURRENT" | "STALE_CONTEXT" | "TARGET_MISSING";
export type LifecycleAllocation = {
  allocation_id: string;
  policy_id: string;
  risk_band: string;
  active_budget_usd: string;
  allocation_basis: string;
  valid_from_ns: number;
  valid_until_ns: number | null;
};
export type LatestHermesAssessment = {
  assessment_id: string;
  information_cutoff: string;
  confidence_label: string;
  lifecycle_action: string;
  recommended_health_state: string;
  risk_direction: string;
  target_risk_band: string | null;
  context_status: ContextStatus;
};
export type StrategySummary = {
  strategy_version_id: string;
  strategy_family_id: string;
  parent_strategy_version_id: string | null;
  strategy_label: string;
  evidence_posture: string;
  adaptation_class: string;
  created_time_ns: number;
  current_health_state: string | null;
  current_allocation: LifecycleAllocation | null;
  active_restriction_count: number;
  evidence_ref_count: number;
  latest_hermes_assessment: LatestHermesAssessment | null;
};
export type ActiveRestriction = {
  restriction_receipt_id: string;
  restriction_key: string;
  restriction_kind: string;
  max_active_budget_usd: string | null;
  created_time_ns: number;
};
export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };
export type StrategyDetail = {
  strategy_version_id: string;
  strategy_family_id: string;
  parent_strategy_version_id: string | null;
  strategy_label: string;
  evidence_posture: string;
  adaptation_class: string;
  strategy_code_identity: string;
  created_time_ns: number;
  creation_provenance: string;
  evidence_refs: string[];
  family: { strategy_family_id: string; family_key: string; family_label: string };
  lineage_strategy_version_ids: string[];
  strategy_definition: {
    thesis: JsonValue;
    universe: JsonValue;
    entry_rule: JsonValue;
    exit_rule: JsonValue;
    execution_rule: JsonValue;
    parameters: JsonValue;
  };
  adaptive_bounds: { [parameter: string]: JsonValue };
  current_state: {
    health_state: string | null;
    active_policy_id: string | null;
    allocation: LifecycleAllocation | null;
    active_restrictions: ActiveRestriction[];
    strategy_lifecycle_context_sha256: string;
  };
  latest_hermes_assessment: LatestHermesAssessment | null;
};
export type HermesAssessmentItem = {
  assessment_id: string;
  strategy_version_id: string;
  strategy_family_id: string;
  predecessor_assessment_id: string | null;
  information_cutoff: string;
  decision_time_ns: number;
  trigger: string;
  confidence_label: string;
  assessment_summary: string;
  lifecycle_action: string;
  recommended_health_state: string;
  risk_direction: string;
  target_risk_band: string | null;
  context_status: ContextStatus;
  canonical_soft_strategy_decision: true;
};
export type HermesNonAuthority = {
  canonical_soft_strategy_decision: true;
  no_credential_authority: true;
  no_portfolio_policy_authority: true;
  no_hard_risk_override: true;
  no_paper_execution_authority: true;
  no_order_authority: true;
  no_execution_authority: true;
  no_live_authority: true;
};
export type HermesAssessmentDetail = HermesAssessmentItem & {
  run_record_id: string;
  runtime_request_id: string;
  runtime_receipt_id: string;
  subject_refs: string[];
  input_evidence_refs: string[];
  evidence_for: string[];
  evidence_against: string[];
  uncertainties: string[];
  known_missing_data: string[];
  falsification_checks_performed: string[];
  limitations: string[];
  what_would_change_the_conclusion: string[];
  suggested_next_research_steps: string[];
  adaptation_recommendation: { kind: string; summary: string; parameter_updates: { [key: string]: JsonValue } } | null;
  strategy_lifecycle_context_sha256: string;
  lifecycle_store_head_entry_hash: string | null;
  active_policy_id: string | null;
  run: {
    provider_label: string;
    model_label: string;
    hermes_version: string;
    terminal_status: string;
    start_utc: string;
    end_utc: string;
    estimated_cost_usd: string | null;
    cost_status: string | null;
    cost_source: string | null;
  };
  non_authority: HermesNonAuthority;
};

// S10-CC-RESEARCH-02 read models. Alpha Factory research memory and Alpha Discovery priority are
// research records only: never qualification, Strategy/Hermes linkage, trade priority or authority.
export type AlphaAuthorityFlags = {
  advisory_only: true;
  no_execution_authority: true;
  no_strategy_authority: true;
  no_qualification_authority: true;
};
export type ResearchResultState =
  | "RESEARCH_SUPPORTIVE"
  | "NO_EDGE_CURRENTLY"
  | "HYPOTHESIS_FALSIFIED"
  | "DATA_INSUFFICIENT"
  | "EXECUTION_UNECONOMIC"
  | "WATCH_FOR_CHANGE"
  | "RESEARCH_STALE"
  | "REOPEN_TRIGGERED"
  | "MECHANISM_FAMILY_EXHAUSTED";
export type AlphaMemorySummary = AlphaAuthorityFlags & {
  head_entry_hash: string | null;
  total_rows: number;
  total_payload_bytes: number;
  record_counts: {
    research_source_references: number;
    opportunity_candidates: number;
    hypothesis_families: number;
    research_episodes: number;
  };
};
export type AlphaCandidateSummary = {
  sequence_number: number;
  candidate_id: string;
  candidate_version: string;
  title: string;
  research_question: string;
  subject_refs: string[];
  evidence_lanes: string[];
  is_multi_lane: boolean;
  scope_key: string;
  mechanism_hint: string;
  novelty_fingerprint: string;
  human_review_required: boolean;
  family_count: number;
  episode_count: number;
  leaf_episode_count: number;
};
export type AlphaCandidateRecord = AlphaAuthorityFlags & {
  candidate_id: string;
  candidate_version: string;
  title: string;
  research_question: string;
  thesis: string;
  subject_refs: string[];
  evidence_lanes: string[];
  is_multi_lane: boolean;
  scope_key: string;
  mechanism_hint: string;
  novelty_dimensions_json: string;
  novelty_fingerprint: string;
  discovery_provenance: string;
  human_review_required: boolean;
};
export type AlphaHypothesisFamily = AlphaAuthorityFlags & {
  sequence_number: number;
  hypothesis_family_id: string;
  family_version: string;
  family_name: string;
  mechanism_key: string;
  mechanism_dimensions_json: string;
  mechanism_fingerprint: string;
  falsifiable_theme: string;
  predecessor_family_id: string | null;
  creation_provenance: string;
  human_review_required: boolean;
  episode_count: number;
  leaf_episode_ids: string[];
};
export type AlphaEpisodeSummary = {
  sequence_number: number;
  research_episode_id: string;
  hypothesis_family_id: string;
  predecessor_episode_id: string | null;
  reopened_episode_id: string | null;
  result_state: ResearchResultState;
  confidence_label: string;
  evidence_lanes: string[];
  research_as_of: string;
  producer_type: string;
  human_review_required: boolean;
};
export type AlphaSourceReference = {
  source_reference_id: string;
  source_kind: string;
  source_class: string;
  source_locator: string;
  title: string;
  observed_at: string;
  content_sha256: string | null;
  provenance: string;
  public_research_only: true;
  advisory_only: true;
  no_execution_authority: true;
};
export type AlphaCandidateDetail = {
  candidate: AlphaCandidateRecord;
  hypothesis_families: AlphaHypothesisFamily[];
  research_episodes: AlphaEpisodeSummary[];
  source_references: AlphaSourceReference[];
  deterministic_evidence_refs: string[];
  lineage_summary: {
    family_count: number;
    episode_count: number;
    leaf_episode_count: number;
    leaf_episode_ids: string[];
  };
};
export type AlphaEpisodeDetail = AlphaAuthorityFlags & {
  research_episode_id: string;
  episode_version: string;
  candidate_id: string;
  hypothesis_family_id: string;
  predecessor_episode_id: string | null;
  reopened_episode_id: string | null;
  result_state: ResearchResultState;
  confidence_label: string;
  evidence_lanes: string[];
  is_multi_lane: boolean;
  exact_scope_json: string;
  evidence_regime_json: string;
  research_question: string;
  thesis: string;
  tested_assumptions: string[];
  evidence_for: string[];
  evidence_against: string[];
  uncertainties: string[];
  known_missing_data: string[];
  falsification_checks_performed: string[];
  limitations: string[];
  what_would_change_the_conclusion: string[];
  suggested_next_research_steps: string[];
  source_reference_ids: string[];
  source_references: AlphaSourceReference[];
  deterministic_evidence_refs: string[];
  material_change_basis: string[];
  producer_type: string;
  producer_version: string;
  producer_receipt_ref: string | null;
  research_as_of: string;
  creation_provenance: string;
  human_review_required: boolean;
};
export type CoverageEntry = { research_archetype: string; coverage_state: string };
export type DiscoveryTriageSummary = {
  market_triage_decision_id: string;
  market_id: string;
  event_id: string;
  category: string | null;
  eligibility: string;
  priority_class: string;
  reopen_disposition: string;
  readiness: string;
  reason_codes: string[];
  material_change_event_id: string | null;
  newly_observed_locally: boolean;
  final_disposition: string;
  selected_lane: string | null;
  analysis_temporal_mode: string;
  alpha_memory_temporal_posture: string;
  alpha_registry_head_entry_hash: string | null;
  matched_candidate_ids: string[];
  matched_hypothesis_family_ids: string[];
  matched_research_episode_ids: string[];
  coverage: CoverageEntry[];
};
export type DiscoveryCaptureRequest = {
  request_type: string;
  market_id: string;
  token_id: string | null;
  universe_id: string;
  policy_id: string;
  comparison_prior_universe_id: string | null;
  reason_code: string;
  priority_class: string;
  pre_allocation_semantic_key: string;
};
export type DiscoveryTriageDetail = DiscoveryTriageSummary &
  AlphaAuthorityFlags & {
    policy_id: string;
    universe_id: string;
    comparison_prior_universe_id: string | null;
    capture_requests: DiscoveryCaptureRequest[];
    audit_digest: string | null;
    audit_eligible_pool_size: number | null;
    audit_selection_fraction_numerator: number | null;
    audit_selection_fraction_denominator: number | null;
    historical_alpha_memory_available: boolean;
    historical_selection_replay_valid: boolean;
    historical_replay_valid_for_alpha_memory: boolean;
  };
export type DiscoveryLaneName = "core" | "exploration" | "audit" | "deferred" | "skipped_ineligible" | "skipped_capacity";
export type DiscoveryQueueResponse = {
  discovery_registry_head_entry_hash: string | null;
  queue_sequence_number: number;
  queue: AlphaAuthorityFlags & {
    alpha_research_queue_snapshot_id: string;
    policy_id: string;
    universe_id: string;
    comparison_prior_universe_id: string | null;
    analysis_temporal_mode: string;
    alpha_memory_temporal_posture: string;
    alpha_registry_head_entry_hash: string | null;
    historical_alpha_memory_available: boolean;
    historical_selection_replay_valid: boolean;
    queue_capacity: number;
    configured_exploration_slots: number;
    configured_audit_slots: number;
    exploration_selected_count: number;
    audit_selected_count: number;
    unused_exploration_slots: number;
    unused_audit_slots: number;
    unused_capacity_reason_codes: string[];
    max_per_category: number;
    prior_only_market_ids: string[];
  };
  policy: {
    alpha_discovery_policy_id: string;
    policy_version: string;
    eligible_market_statuses: string[];
    metadata_freshness_seconds: number;
    order_book_freshness_seconds: number;
    resolution_rule_freshness_seconds: number;
    queue_capacity: number;
    exploration_slots: number;
    audit_slots: number;
    max_per_category: number;
    research_archetype_taxonomy_version: string;
  };
  universe: {
    alpha_universe_snapshot_id: string;
    as_of: string;
    cutoff_mode: string;
    query_engine_version: string;
    query_parameter_set_id: string;
    coverage_scope: string;
    external_universe_completeness: string;
    market_count: number;
  };
  lanes: Record<DiscoveryLaneName, DiscoveryTriageSummary[]>;
};
export type AlphaResolutionStatus = "NOT_BOUND" | "UNAVAILABLE" | "HEAD_MISMATCH" | "RESOLVED";
export type DiscoveryTriageResponse = {
  triage: DiscoveryTriageDetail;
  universe_market: {
    market_id: string;
    event_id: string;
    market_status: string | null;
    condition_id: string | null;
    token_ids: string[];
    outcome_labels: string[];
    resolution_date: string | null;
    category: string | null;
    question_text: string | null;
    metadata_record_version_id: string;
    metadata_observed_time: string;
    metadata_freshness: string;
    data_gap_codes: string[];
    resolution_rule_count: number;
    order_book_count: number;
  };
  material_change:
    | (AlphaAuthorityFlags & {
        material_change_event_id: string;
        prior_universe_id: string;
        current_universe_id: string;
        market_id: string;
        hard_change_classes: string[];
        soft_change_classes: string[];
        review_only_change_classes: string[];
        affected_token_ids: { change_class: string; token_ids: string[] }[];
        affected_resolution_source_ids: string[];
        before_record_version_ids: string[];
        after_record_version_ids: string[];
        comparison_diagnostics: string[];
        reopen_material: boolean;
      })
    | null;
  alpha_memory_resolution: {
    status: AlphaResolutionStatus;
    bound_alpha_registry_head_entry_hash: string | null;
    candidates: AlphaCandidateSummary[];
    hypothesis_families: {
      sequence_number: number;
      hypothesis_family_id: string;
      family_name: string;
      mechanism_key: string;
      falsifiable_theme: string;
    }[];
    research_episodes: AlphaEpisodeSummary[];
  };
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
export type QueryFamily = "overview" | "market" | "experiments" | "strategies" | "hermes" | "alpha" | "paper" | "audit";

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
export const strategiesQuery = queryOptions({
  queryKey: ["cc", "strategies", "list"] as const,
  queryFn: ({ signal }) => getJson<ListResponse<StrategySummary>>("/strategies", signal),
});
export const strategyDetailQuery = (strategyVersionId: string) =>
  queryOptions({
    queryKey: ["cc", "strategies", "detail", strategyVersionId] as const,
    queryFn: async ({ signal }) =>
      (await getJson<{ item: StrategyDetail }>("/strategies/" + encodeURIComponent(strategyVersionId), signal)).item,
  });
export const hermesAssessmentsQuery = queryOptions({
  queryKey: ["cc", "hermes", "list"] as const,
  queryFn: ({ signal }) => getJson<ListResponse<HermesAssessmentItem>>("/hermes/assessments", signal),
});
export const hermesAssessmentDetailQuery = (assessmentId: string) =>
  queryOptions({
    queryKey: ["cc", "hermes", "detail", assessmentId] as const,
    queryFn: async ({ signal }) =>
      (await getJson<{ item: HermesAssessmentDetail }>("/hermes/assessments/" + encodeURIComponent(assessmentId), signal))
        .item,
  });
export const alphaMemoryQuery = queryOptions({
  queryKey: ["cc", "alpha", "memory"] as const,
  queryFn: ({ signal }) => getJson<AlphaMemorySummary>("/alpha/memory", signal),
});
export const alphaCandidatesQuery = queryOptions({
  queryKey: ["cc", "alpha", "candidates", "list"] as const,
  queryFn: ({ signal }) => getJson<ListResponse<AlphaCandidateSummary>>("/alpha/candidates", signal),
});
export const alphaCandidateDetailQuery = (candidateId: string) =>
  queryOptions({
    queryKey: ["cc", "alpha", "candidates", "detail", candidateId] as const,
    queryFn: ({ signal }) =>
      getJson<AlphaCandidateDetail>("/alpha/candidates/" + encodeURIComponent(candidateId), signal),
  });
export const alphaEpisodeDetailQuery = (researchEpisodeId: string) =>
  queryOptions({
    queryKey: ["cc", "alpha", "episodes", "detail", researchEpisodeId] as const,
    queryFn: async ({ signal }) =>
      (await getJson<{ item: AlphaEpisodeDetail }>("/alpha/episodes/" + encodeURIComponent(researchEpisodeId), signal))
        .item,
  });
export const alphaDiscoveryQueueQuery = queryOptions({
  queryKey: ["cc", "alpha", "discovery", "queue"] as const,
  queryFn: ({ signal }) => getJson<DiscoveryQueueResponse>("/alpha/discovery/queue", signal),
});
export const alphaTriageDetailQuery = (marketTriageDecisionId: string) =>
  queryOptions({
    queryKey: ["cc", "alpha", "discovery", "triage", marketTriageDecisionId] as const,
    queryFn: ({ signal }) =>
      getJson<DiscoveryTriageResponse>("/alpha/discovery/triage/" + encodeURIComponent(marketTriageDecisionId), signal),
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
