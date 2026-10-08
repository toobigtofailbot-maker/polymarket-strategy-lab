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

// S10-CC-OPS-01 read models. Portfolio policy and budget reservations, simulated paper state and
// recorded gateway state are separate sources with separate meanings; none of them is current
// authenticated account risk, host or network currentness, Gate-C eligibility or live authority.
export type CapacityStatus = "PORTFOLIO_CAPACITY_VALID" | "PORTFOLIO_CAPACITY_REJECTED";
export type OpsPolicyLimits = {
  global_capital_at_risk_max_usd: string;
  global_gross_exposure_max_usd: string;
  global_daily_loss_max_usd: string;
  global_drawdown_max_usd: string;
  global_cumulative_loss_max_usd: string;
  exploratory_pool_max_usd: string;
  validated_pool_max_usd: string;
  mature_pool_max_usd: string;
  max_exploratory_per_strategy_usd: string;
  max_validated_per_strategy_usd: string;
  max_mature_per_strategy_usd: string;
  max_per_market_usd: string;
  max_order_notional_usd: string;
  max_active_strategies: number;
  max_active_markets: number;
  max_simultaneous_open_orders: number;
  max_mutations_per_minute: number;
};
export type OpsActivePolicy = {
  policy_id: string;
  predecessor_policy_id: string | null;
  policy_label: string;
  venue_scope: string[];
  account_scope_ref: string;
  effective_from_ns: number;
  expires_at_ns: number | null;
  limits: OpsPolicyLimits;
  allowed_order_styles: string[];
  created_time_ns: number;
};
export type OpsCapacity = {
  status: CapacityStatus;
  reason_codes: string[];
  evaluated_at_ns: number | null;
  policy_id: string | null;
  reserved_budget_usd: { exploratory: string; validated: string; mature: string; total: string };
  active_real_risk_strategy_count: number;
};
export type OpsStrategyReservation = {
  allocation_id: string;
  strategy_version_id: string;
  strategy_label: string;
  policy_id: string;
  risk_band: string;
  active_budget_usd: string;
  allocation_basis: string;
  valid_from_ns: number;
  valid_until_ns: number | null;
  active_at_evaluation: boolean;
  health_state: string | null;
  capacity_status: CapacityStatus | null;
  capacity_reason_codes: string[];
  active_restrictions: ActiveRestriction[];
};
export type OpsNonAuthority = {
  budget_reservation_only: true;
  actual_account_exposure_not_measured: true;
  orders_not_measured: true;
  fills_not_measured: true;
  pnl_not_measured: true;
  gate_c_not_implied: true;
  execution_not_implied: true;
  live_not_implied: true;
};
export type OpsPortfolio = {
  read_only: true;
  evaluated_at_ns: number;
  lifecycle_store_head_entry_hash: string | null;
  active_policy: OpsActivePolicy | null;
  capacity: OpsCapacity;
  strategy_reservations: OpsStrategyReservation[];
  non_authority: OpsNonAuthority;
};
export type GatewayRestrictedLive = {
  armed: boolean;
  halted: boolean;
  create_attempt_count: number;
  capital_at_risk_pusd: string;
  capital_committed_pusd: string;
  reconciliation_state: string;
};
export type GatewayStatus = {
  read_only: true;
  authority_state: string;
  disabled: boolean;
  disable_reason: string | null;
  credential_configured: boolean;
  reconciliation_state: string;
  heartbeat_state: string;
  user_stream_state: string;
  access_state: string;
  rate_limit_until_ns: number | null;
  prepared_order_count: number;
  mutation_attempt_count: number;
  open_order_count: number;
  gate_b_authorized: false;
  restricted_live_available: boolean;
  restricted_live: GatewayRestrictedLive;
};
export type GatewayAuditItem = {
  sequence: number;
  event_id: string;
  event_type: string;
  event_time_ns: number;
  event_hash: string;
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
export type QueryFamily = "overview" | "market" | "experiments" | "strategies" | "hermes" | "alpha" | "ops" | "paper" | "audit";

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
// OPS-owned keys: Refresh on /ops invalidates only these, never the paper or other page families,
// even though four of them read the existing paper and gateway endpoints.
export const opsPortfolioQuery = queryOptions({
  queryKey: ["cc", "ops", "portfolio"] as const,
  queryFn: ({ signal }) => getJson<OpsPortfolio>("/ops/portfolio", signal),
});
export const opsGatewayStatusQuery = queryOptions({
  queryKey: ["cc", "ops", "gateway", "status"] as const,
  queryFn: ({ signal }) => getJson<GatewayStatus>("/gateway/status", signal),
});
export const opsGatewayAuditQuery = queryOptions({
  queryKey: ["cc", "ops", "gateway", "audit"] as const,
  queryFn: ({ signal }) => getJson<ListResponse<GatewayAuditItem>>("/gateway/audit", signal),
});
export const opsPaperSummaryQuery = queryOptions({
  queryKey: ["cc", "ops", "paper", "summary"] as const,
  queryFn: ({ signal }) => getJson<PaperSummary>("/paper/summary", signal),
});
export const opsPaperRiskQuery = queryOptions({
  queryKey: ["cc", "ops", "paper", "risk"] as const,
  queryFn: ({ signal }) => getJson<PaperRisk>("/paper/risk", signal),
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

// S10-CC-STREAM-01 transport. The default-off server stream carries transport metadata only: it
// tells the shell when to re-read the active family's existing HTTP snapshots. A transport
// connection, sequence, heartbeat or signal time is never domain freshness, a source change or
// any account, host, network, execution or live readiness.
export const STREAM_SCHEMA_VERSION = "1.0.0";
export const STREAM_FAMILIES = [
  "overview",
  "market",
  "experiments",
  "strategies",
  "hermes",
  "alpha",
  "ops",
  "paper",
  "audit",
] as const satisfies readonly QueryFamily[];
export type StreamEventKind = "RESYNC_REQUIRED" | "REFRESH_DUE" | "HEARTBEAT";
export type StreamEventName = "resync" | "refresh" | "heartbeat";
export const STREAM_EVENT_NAMES: Record<StreamEventName, StreamEventKind> = {
  resync: "RESYNC_REQUIRED",
  refresh: "REFRESH_DUE",
  heartbeat: "HEARTBEAT",
};
export type StreamStatus = {
  read_only: true;
  enabled: boolean;
  transport: "SSE";
  semantics: "SERVER_PACED_ACTIVE_FAMILY_REFRESH";
  source_push: false;
  canonical_event_stream: false;
  domain_freshness_guarantee: false;
  replay_available: false;
  base_tick_seconds: 5;
  refresh_seconds_by_family: Record<QueryFamily, number>;
};
export type StreamEvent = {
  schema_version: "1.0.0";
  connection_id: string;
  sequence: number;
  kind: StreamEventKind;
  family: QueryFamily;
  server_time_ns: string;
};

const STREAM_STATUS_KEYS = [
  "base_tick_seconds",
  "canonical_event_stream",
  "domain_freshness_guarantee",
  "enabled",
  "read_only",
  "refresh_seconds_by_family",
  "replay_available",
  "semantics",
  "source_push",
  "transport",
];
const STREAM_EVENT_KEYS = ["connection_id", "family", "kind", "schema_version", "sequence", "server_time_ns"];
const STREAM_CONNECTION_ID_RE = /^ccstream:[0-9a-f]{32}$/;
const STREAM_SERVER_TIME_NS_RE = /^(0|[1-9][0-9]{0,19})$/;

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);
const hasExactKeys = (record: Record<string, unknown>, keys: readonly string[]) =>
  Object.keys(record).sort().join(",") === keys.join(",");

/** Strict status validation: anything but the exact transport DTO is MALFORMED_RESPONSE. */
export function parseStreamStatus(body: unknown): StreamStatus {
  if (!isRecord(body) || !hasExactKeys(body, STREAM_STATUS_KEYS)) throw new SafeApiError("MALFORMED_RESPONSE");
  const cadence = body.refresh_seconds_by_family;
  if (
    body.read_only !== true ||
    typeof body.enabled !== "boolean" ||
    body.transport !== "SSE" ||
    body.semantics !== "SERVER_PACED_ACTIVE_FAMILY_REFRESH" ||
    body.source_push !== false ||
    body.canonical_event_stream !== false ||
    body.domain_freshness_guarantee !== false ||
    body.replay_available !== false ||
    body.base_tick_seconds !== 5 ||
    !isRecord(cadence) ||
    !hasExactKeys(cadence, [...STREAM_FAMILIES].sort()) ||
    !STREAM_FAMILIES.every((family) => {
      const seconds = cadence[family];
      return typeof seconds === "number" && Number.isSafeInteger(seconds) && seconds > 0 && seconds % 5 === 0;
    })
  ) {
    throw new SafeApiError("MALFORMED_RESPONSE");
  }
  return body as StreamStatus;
}

/**
 * Strict SSE data validation for one named event on the active family's stream. Returns null for
 * anything else; malformed transport input never becomes query data and is never rendered.
 */
export function parseStreamEvent(eventName: StreamEventName, data: unknown, family: QueryFamily): StreamEvent | null {
  if (typeof data !== "string" || data.length > 512) return null;
  let value: unknown;
  try {
    value = JSON.parse(data);
  } catch {
    return null;
  }
  if (!isRecord(value) || !hasExactKeys(value, STREAM_EVENT_KEYS)) return null;
  const { schema_version, connection_id, sequence, kind, server_time_ns } = value;
  if (schema_version !== STREAM_SCHEMA_VERSION) return null;
  if (typeof connection_id !== "string" || !STREAM_CONNECTION_ID_RE.test(connection_id)) return null;
  if (typeof sequence !== "number" || !Number.isSafeInteger(sequence) || sequence < 1) return null;
  const expectedKind = STREAM_EVENT_NAMES[eventName];
  if (kind !== expectedKind) return null;
  if (value.family !== family) return null;
  if (typeof server_time_ns !== "string" || !STREAM_SERVER_TIME_NS_RE.test(server_time_ns)) return null;
  return { schema_version: STREAM_SCHEMA_VERSION, connection_id, sequence, kind: expectedKind, family, server_time_ns };
}

// The only transport state kept per browser stream: the current connection id and last sequence.
export type StreamBaseline = { connectionId: string; sequence: number };
export type StreamStep = { baseline: StreamBaseline; resync: boolean; invalidate: boolean };

/**
 * Gap/resync rules. A first event, a new connection id or a same-connection sequence other than
 * last + 1 is a transport gap: re-read the active family over HTTP (there is no replay). Otherwise
 * RESYNC_REQUIRED and REFRESH_DUE re-read the active family and HEARTBEAT re-reads nothing. The
 * newest valid event always becomes the baseline.
 */
export function advanceStreamBaseline(baseline: StreamBaseline | null, event: StreamEvent): StreamStep {
  const next = { connectionId: event.connection_id, sequence: event.sequence };
  const continuous =
    baseline !== null && baseline.connectionId === event.connection_id && event.sequence === baseline.sequence + 1;
  if (!continuous || event.kind === "RESYNC_REQUIRED") return { baseline: next, resync: true, invalidate: true };
  return { baseline: next, resync: false, invalidate: event.kind === "REFRESH_DUE" };
}

/** Same-origin stream URL for one active query family. */
export const streamEventUrl = (family: QueryFamily) => API_BASE + "/stream/events?family=" + encodeURIComponent(family);

// Global transport status (not a page family): manual Refresh never touches it.
export const streamStatusQuery = queryOptions({
  queryKey: ["cc", "stream", "status"] as const,
  queryFn: async ({ signal }) => parseStreamStatus(await getJson<unknown>("/stream/status", signal)),
});

// Cockpit reads can replay verified stores, so nothing refetches on its own: no retry, no
// focus/reconnect refetch, no interval. Data changes only when the operator presses Refresh or,
// when the backend stream is explicitly enabled, when its signal invalidates the active family.
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

// S10-CC-CMD-01 protected commands. Default-off lifecycle-governance commands for exactly five
// canonical StrategyLifecycle records. The command secret is sent once to the local login route
// and never kept; the bearer token lives only in React memory at the shell controller and is sent
// as an explicit Authorization header (credentials are always omitted). Command requests are never
// retried automatically, never cached and never derived from the stream. None of this is account,
// order, Gate-C, execution or live authority.
export const COMMAND_KINDS = [
  "STRATEGY_PAUSE",
  "STRATEGY_RESUME",
  "STRATEGY_QUARANTINE",
  "POLICY_ACTIVATE",
  "POLICY_REVOKE",
] as const;
export type CommandKind = (typeof COMMAND_KINDS)[number];
export const CONFIRMATION_PHRASES: Record<CommandKind, string> = {
  STRATEGY_PAUSE: "CONFIRM-PAUSE",
  STRATEGY_RESUME: "CONFIRM-RESUME",
  STRATEGY_QUARANTINE: "CONFIRM-QUARANTINE",
  POLICY_ACTIVATE: "CONFIRM-ACTIVATE-POLICY",
  POLICY_REVOKE: "CONFIRM-REVOKE-POLICY",
};
// Mutation requests use retry = false: one request per explicit operator action, nothing more.
export const COMMAND_MUTATION_RETRY = false;

export type CommandStatus = {
  read_only: false;
  commands_enabled: boolean;
  auth_mode: "EPHEMERAL_BEARER_SESSION";
  session_ttl_seconds: 900;
  active_session: boolean;
  supported_commands: CommandKind[];
  no_product_network: true;
  no_account_access: true;
  no_order_authority: true;
  no_gate_c_authority: true;
  no_live_authority: true;
};
// Raw bearer token: React memory only (never query data, browser storage or a URL).
export type CommandSession = { operatorId: string; token: string; expiresAtMs: number };
export type CommandTarget =
  | { command_kind: "STRATEGY_PAUSE"; strategy_version_id: string }
  | { command_kind: "STRATEGY_RESUME"; strategy_version_id: string; restriction_key: string }
  | { command_kind: "STRATEGY_QUARANTINE"; strategy_version_id: string; previous_health_state: string }
  | { command_kind: "POLICY_ACTIVATE"; policy_id: string; previous_active_policy_id: string | null }
  | { command_kind: "POLICY_REVOKE"; policy_id: string };
export type CommandRequest = CommandTarget & {
  expected_lifecycle_store_head_entry_hash: string | null;
  issued_at_ms: number;
  confirmation_phrase: string;
};
export type CommandReceipt = {
  schema_version: "1.0.0";
  status: "COMMITTED" | "IDEMPOTENT_REPLAY";
  command_ref: string;
  command_kind: CommandKind;
  operator_id: string;
  canonical_record_kind: string;
  canonical_record_id: string;
  lifecycle_store_head_entry_hash: string | null;
  issued_at_ms: number;
  no_product_network: true;
  no_account_access: true;
  no_order_authority: true;
  no_gate_c_authority: true;
  no_live_authority: true;
};

const COMMAND_ERROR_CODES = [
  "COMMANDS_DISABLED",
  "AUTH_REQUIRED",
  "AUTH_FAILED",
  "AUTH_LOCKED",
  "SESSION_EXPIRED",
  "INVALID_COMMAND",
  "INVALID_CONFIRMATION",
  "STALE_STATE",
  "COMMAND_PRECONDITION_FAILED",
  "SOURCE_UNAVAILABLE",
  "INTERNAL_ERROR",
] as const;
const CANONICAL_ERROR_CODES = [
  "FIELD_TYPE_INVALID",
  "FIELD_VALUE_INVALID",
  "SCHEMA_CONFLICT",
  "INTEGRITY_TAMPER",
  "IDENTITY_CONFLICT",
  "REFERENCE_INVALID",
  "LINEAGE_INVALID",
  "ADAPTATION_INVALID",
  "POLICY_INVALID",
  "POLICY_TRANSITION_INVALID",
  "HEALTH_TRANSITION_INVALID",
  "ALLOCATION_INVALID",
  "RESTRICTION_TRANSITION_INVALID",
  "CAPACITY_INVALID",
  "LIMIT_EXCEEDED",
  "INTERNAL_VALIDATION_FAILED",
] as const;
export type CommandErrorCode = (typeof COMMAND_ERROR_CODES)[number] | "NETWORK_UNAVAILABLE" | "MALFORMED_RESPONSE";
// Outcomes where the request may or may not have committed; only an exact same-request retry is safe.
const AMBIGUOUS_COMMAND_CODES: readonly CommandErrorCode[] = ["NETWORK_UNAVAILABLE", "INTERNAL_ERROR", "MALFORMED_RESPONSE"];

export class CommandApiError extends Error {
  readonly code: CommandErrorCode;
  readonly canonicalErrorCode: string | null;
  constructor(code: CommandErrorCode, canonicalErrorCode: string | null = null) {
    super(code);
    this.name = "CommandApiError";
    this.code = code;
    this.canonicalErrorCode = canonicalErrorCode;
  }
  get ambiguous(): boolean {
    return AMBIGUOUS_COMMAND_CODES.includes(this.code);
  }
}

export function toCommandError(error: unknown): CommandApiError {
  return error instanceof CommandApiError ? error : new CommandApiError("INTERNAL_ERROR");
}

function commandErrorFromBody(body: unknown): CommandApiError {
  const error = isRecord(body) && isRecord(body.error) ? body.error : null;
  const code = COMMAND_ERROR_CODES.find((candidate) => candidate === error?.code) ?? "INTERNAL_ERROR";
  const canonical = CANONICAL_ERROR_CODES.find((candidate) => candidate === error?.canonical_error_code) ?? null;
  return new CommandApiError(code, code === "COMMAND_PRECONDITION_FAILED" ? canonical : null);
}

const COMMAND_STATUS_KEYS = [
  "active_session",
  "auth_mode",
  "commands_enabled",
  "no_account_access",
  "no_gate_c_authority",
  "no_live_authority",
  "no_order_authority",
  "no_product_network",
  "read_only",
  "session_ttl_seconds",
  "supported_commands",
];

/** Strict status validation; anything else is MALFORMED_RESPONSE and leaves commands unavailable. */
export function parseCommandStatus(body: unknown): CommandStatus {
  if (
    !isRecord(body) ||
    !hasExactKeys(body, COMMAND_STATUS_KEYS) ||
    body.read_only !== false ||
    typeof body.commands_enabled !== "boolean" ||
    body.auth_mode !== "EPHEMERAL_BEARER_SESSION" ||
    body.session_ttl_seconds !== 900 ||
    typeof body.active_session !== "boolean" ||
    !Array.isArray(body.supported_commands) ||
    body.supported_commands.join(",") !== COMMAND_KINDS.join(",") ||
    body.no_product_network !== true ||
    body.no_account_access !== true ||
    body.no_order_authority !== true ||
    body.no_gate_c_authority !== true ||
    body.no_live_authority !== true
  ) {
    throw new SafeApiError("MALFORMED_RESPONSE");
  }
  return body as CommandStatus;
}

// Global command capability (not a page family): manual Refresh never touches it.
export const commandStatusQuery = queryOptions({
  queryKey: ["cc", "commands", "status"] as const,
  queryFn: async ({ signal }) => parseCommandStatus(await getJson<unknown>("/commands/status", signal)),
});

/** OPS policy catalogue, validated at runtime; a missing or malformed catalogue offers no choice. */
export function parseOpsPolicies(portfolio: OpsPortfolio): OpsActivePolicy[] | null {
  const policies: unknown = (portfolio as { policies?: unknown }).policies;
  if (!Array.isArray(policies)) return null;
  const valid = policies.every(
    (policy) =>
      isRecord(policy) &&
      typeof policy.policy_id === "string" &&
      /^portfolioauthoritypolicy:sha256:[0-9a-f]{64}$/.test(policy.policy_id) &&
      typeof policy.policy_label === "string" &&
      typeof policy.effective_from_ns === "number" &&
      (policy.expires_at_ns === null || typeof policy.expires_at_ns === "number"),
  );
  return valid ? (policies as OpsActivePolicy[]) : null;
}

/** The one place a command request is minted: issued_at_ms is fixed here and reused on retry. */
export function newCommandRequest(target: CommandTarget, expectedHead: string | null): Readonly<CommandRequest> {
  return Object.freeze({
    ...target,
    expected_lifecycle_store_head_entry_hash: expectedHead,
    issued_at_ms: Date.now(),
    confirmation_phrase: CONFIRMATION_PHRASES[target.command_kind],
  });
}

// The only command transport: one same-origin request, explicit bearer header, no cache, no retry.
async function postCommand(path: string, payload: unknown | null, token: string | null): Promise<unknown> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (payload !== null) headers["Content-Type"] = "application/json";
  if (token !== null) headers.Authorization = "Bearer " + token;
  let response: Response;
  try {
    response = await fetch(API_BASE + path, {
      method: "POST",
      headers,
      body: payload === null ? undefined : JSON.stringify(payload),
      credentials: "omit",
      cache: "no-store",
    });
  } catch {
    throw new CommandApiError("NETWORK_UNAVAILABLE");
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new CommandApiError(response.ok ? "MALFORMED_RESPONSE" : "INTERNAL_ERROR");
  }
  if (!response.ok) throw commandErrorFromBody(body);
  if (!isRecord(body)) throw new CommandApiError("MALFORMED_RESPONSE");
  return body;
}

export async function loginCommandSession(secret: string): Promise<CommandSession> {
  const body = (await postCommand("/commands/session", { secret }, null)) as Record<string, unknown>;
  if (
    !hasExactKeys(body, ["expires_at_ms", "operator_id", "session_token"]) ||
    typeof body.operator_id !== "string" ||
    typeof body.session_token !== "string" ||
    !/^[A-Za-z0-9_-]{43}$/.test(body.session_token) ||
    typeof body.expires_at_ms !== "number" ||
    !Number.isSafeInteger(body.expires_at_ms)
  ) {
    throw new CommandApiError("MALFORMED_RESPONSE");
  }
  return { operatorId: body.operator_id, token: body.session_token, expiresAtMs: body.expires_at_ms };
}

export async function revokeCommandSession(token: string): Promise<void> {
  await postCommand("/commands/session/revoke", null, token);
}

const COMMAND_RECEIPT_KEYS = [
  "canonical_record_id",
  "canonical_record_kind",
  "command_kind",
  "command_ref",
  "issued_at_ms",
  "lifecycle_store_head_entry_hash",
  "no_account_access",
  "no_gate_c_authority",
  "no_live_authority",
  "no_order_authority",
  "no_product_network",
  "operator_id",
  "schema_version",
  "status",
];

export async function executeCommand(token: string, request: Readonly<CommandRequest>): Promise<CommandReceipt> {
  const body = (await postCommand("/commands/execute", request, token)) as Record<string, unknown>;
  if (
    !hasExactKeys(body, COMMAND_RECEIPT_KEYS) ||
    body.schema_version !== "1.0.0" ||
    (body.status !== "COMMITTED" && body.status !== "IDEMPOTENT_REPLAY") ||
    body.command_kind !== request.command_kind ||
    body.issued_at_ms !== request.issued_at_ms ||
    typeof body.command_ref !== "string" ||
    typeof body.operator_id !== "string" ||
    !body.command_ref.startsWith("cccmd:" + body.operator_id + ":sha256:") ||
    typeof body.canonical_record_kind !== "string" ||
    typeof body.canonical_record_id !== "string" ||
    (body.lifecycle_store_head_entry_hash !== null && typeof body.lifecycle_store_head_entry_hash !== "string") ||
    body.no_product_network !== true ||
    body.no_account_access !== true ||
    body.no_order_authority !== true ||
    body.no_gate_c_authority !== true ||
    body.no_live_authority !== true
  ) {
    throw new CommandApiError("MALFORMED_RESPONSE");
  }
  return body as CommandReceipt;
}

// HTTP families re-read after any command outcome; correctness never waits for the stream.
export const COMMAND_REREAD_FAMILIES: readonly QueryFamily[] = ["strategies", "ops"];
