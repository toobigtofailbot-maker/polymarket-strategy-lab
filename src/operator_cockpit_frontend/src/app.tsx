import { useEffect, useState, type ReactNode } from "react";
import { useIsFetching, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { Navigate, NavLink, Route, Routes, useLocation } from "react-router";
import {
  advanceStreamBaseline,
  alphaCandidateDetailQuery,
  alphaCandidatesQuery,
  alphaDiscoveryQueueQuery,
  alphaEpisodeDetailQuery,
  alphaMemoryQuery,
  alphaTriageDetailQuery,
  auditRecentQuery,
  experimentDetailQuery,
  experimentsQuery,
  familyKey,
  healthQuery,
  hermesAssessmentDetailQuery,
  hermesAssessmentsQuery,
  marketRecentQuery,
  opsGatewayAuditQuery,
  opsGatewayStatusQuery,
  opsPaperRiskQuery,
  opsPaperSummaryQuery,
  opsPortfolioQuery,
  overviewQuery,
  paperFillsQuery,
  paperOrdersQuery,
  paperPositionsQuery,
  paperRiskQuery,
  paperSummaryQuery,
  parseStreamEvent,
  STREAM_EVENT_NAMES,
  strategiesQuery,
  strategyDetailQuery,
  streamEventUrl,
  streamStatusQuery,
  toSafeErrorCode,
  type AlphaResolutionStatus,
  type AlphaSourceReference,
  type CapacityStatus,
  type ContextStatus,
  type DiscoveryLaneName,
  type GatewayAuditItem,
  type GatewayStatus,
  type HermesNonAuthority,
  type JsonValue,
  type LatestHermesAssessment,
  type LifecycleAllocation,
  type ListResponse,
  type OpsActivePolicy,
  type OpsPolicyLimits,
  type OpsPortfolio,
  type OpsStrategyReservation,
  type PaperRisk,
  type PaperSummary,
  type QueryFamily,
  type ResearchResultState,
  type StreamBaseline,
  type StreamEventName,
} from "./api";

// ---------------------------------------------------------------------------
// Source-owned primitives
// ---------------------------------------------------------------------------

type Tone = "neutral" | "success" | "warning" | "danger";

export function Button({
  children,
  onClick,
  variant = "secondary",
  busy = false,
  disabled = false,
}: {
  children: ReactNode;
  onClick: () => void;
  variant?: "primary" | "secondary" | "link";
  busy?: boolean;
  disabled?: boolean;
}) {
  return (
    <button type="button" className={`btn btn-${variant}`} onClick={onClick} disabled={disabled} aria-busy={busy || undefined}>
      {children}
    </button>
  );
}

function NavItem({ to, children }: { to: string; children: ReactNode }) {
  return (
    <NavLink to={to} className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}>
      {children}
    </NavLink>
  );
}

export function StatusPill({ children, tone = "neutral" }: { children: ReactNode; tone?: Tone }) {
  return <span className={`pill pill-${tone}`}>{children}</span>;
}

function Panel({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <section className="panel">
      {title && <h2 className="panel-title">{title}</h2>}
      {children}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="metric">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function MetricGrid({ children }: { children: ReactNode }) {
  return <dl className="metric-grid">{children}</dl>;
}

function DataTable({ label, headers, children }: { label: string; headers: string[]; children: ReactNode }) {
  return (
    <div className="table-wrap" role="region" aria-label={label} tabIndex={0}>
      <table>
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header} scope="col">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

function Token({ children }: { children: ReactNode }) {
  return <span className="token">{children}</span>;
}

function StateSurface({ kind, children }: { kind: "loading" | "empty" | "error"; children: ReactNode }) {
  return (
    <div className={`state state-${kind}`} role={kind === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}

function SafeError({ error }: { error: unknown }) {
  return (
    <StateSurface kind="error">
      Source unavailable. Safe code: <code>{toSafeErrorCode(error)}</code>
    </StateSurface>
  );
}

/** Renders first-load, safe-error, empty and ready states for one query. */
function QueryState<T>({
  query,
  label,
  isEmpty,
  children,
}: {
  query: UseQueryResult<T>;
  label: string;
  isEmpty?: (data: T) => boolean;
  children: (data: T) => ReactNode;
}) {
  if (query.data === undefined) {
    if (query.isError) return <SafeError error={query.error} />;
    return <StateSurface kind="loading">Loading {label}…</StateSurface>;
  }
  return (
    <>
      {query.isError && (
        <p className="inline-alert" role="alert">
          Refresh failed; showing the last loaded {label}. Safe code: <code>{toSafeErrorCode(query.error)}</code>
        </p>
      )}
      {isEmpty?.(query.data) ? (
        <StateSurface kind="empty">No {label} in this view.</StateSurface>
      ) : (
        children(query.data)
      )}
    </>
  );
}

const isEmptyList = <T,>(data: ListResponse<T>) => data.count === 0;
const yesNo = (value: boolean) => (value ? "Yes" : "No");

// ---------------------------------------------------------------------------
// Views (semantics carried over unchanged from the WP171/WP173 cockpit)
// ---------------------------------------------------------------------------

function OverviewView() {
  const overview = useQuery(overviewQuery);
  return (
    <QueryState query={overview} label="overview evidence">
      {(data) => (
        <>
          <MetricGrid>
            <Metric label="Normalized observations" value={data.market_truth.normalized_count} />
            <Metric label="Accepted observations" value={data.market_truth.accepted_count} />
            <Metric label="Open gap events" value={data.market_truth.open_gap_count} />
            <Metric label="Experiments" value={data.experiments.experiment_count} />
            <Metric label="Lifecycle receipts" value={data.experiments.lifecycle_count} />
            <Metric label="Evidence receipts" value={data.experiments.evidence_count} />
          </MetricGrid>
          <Panel title="Latest market receipt">
            <p className="mono">{data.market_truth.latest_received_at || "No market timestamp available"}</p>
            <StatusPill>Read only</StatusPill>
          </Panel>
        </>
      )}
    </QueryState>
  );
}

function MarketView() {
  const recent = useQuery(marketRecentQuery);
  return (
    <QueryState query={recent} label="market observations" isEmpty={isEmptyList}>
      {(data) => (
        <Panel title="Recent market observations">
          <DataTable label="Recent market observations" headers={["Received", "Source", "Event", "Market / Asset", "Status", "Book ready"]}>
            {data.items.map((item) => (
              <tr key={item.observation_id}>
                <td className="mono">{item.received_at}</td>
                <td>{item.source_kind}</td>
                <td>{item.event_kind}</td>
                <td>
                  <Token>{item.market_id || "—"}</Token>
                  <br />
                  <Token>{item.asset_id || "—"}</Token>
                </td>
                <td>
                  <StatusPill tone={item.status === "ACCEPTED" ? "success" : "warning"}>{item.status}</StatusPill>
                </td>
                <td>{yesNo(item.book_ready)}</td>
              </tr>
            ))}
          </DataTable>
        </Panel>
      )}
    </QueryState>
  );
}

function ExperimentDetailPanel({ experimentId, onClose }: { experimentId: string; onClose: () => void }) {
  const detail = useQuery(experimentDetailQuery(experimentId));
  return (
    <Panel title="Experiment detail · evidence status only">
      <div className="panel-actions">
        <Button variant="secondary" onClick={onClose}>
          Close detail
        </Button>
      </div>
      <QueryState query={detail} label="experiment detail">
        {(item) => (
          <dl className="detail-grid">
            {Object.entries(item).map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd className="token">{Array.isArray(value) ? value.join(", ") || "—" : String(value ?? "—")}</dd>
              </div>
            ))}
          </dl>
        )}
      </QueryState>
    </Panel>
  );
}

function ExperimentsView() {
  const experiments = useQuery(experimentsQuery);
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <>
      <QueryState query={experiments} label="experiments" isEmpty={isEmptyList}>
        {(data) => (
          <Panel title="Preregistered experiments">
            <DataTable label="Preregistered experiments" headers={["Experiment", "Trial", "Lifecycle", "Evidence result", "OOS use"]}>
              {data.items.map((item) => (
                <tr key={item.experiment_id} className={item.experiment_id === selected ? "selected" : undefined}>
                  <td>
                    <Button variant="link" onClick={() => setSelected(item.experiment_id)}>
                      <span className="token">{item.experiment_id}</span>
                    </Button>
                  </td>
                  <td>{item.trial_number}</td>
                  <td>{item.lifecycle_state || "Not started"}</td>
                  <td>
                    <StatusPill>{item.result_status || "No evidence"}</StatusPill>
                  </td>
                  <td>
                    {item.oos_exposure_ordinal == null
                      ? "—"
                      : item.oos_exposure_ordinal === 1
                        ? "First look"
                        : "Reused / diagnostic"}
                  </td>
                </tr>
              ))}
            </DataTable>
          </Panel>
        )}
      </QueryState>
      {selected && <ExperimentDetailPanel experimentId={selected} onClose={() => setSelected(null)} />}
    </>
  );
}

function PaperView() {
  const summary = useQuery(paperSummaryQuery);
  const risk = useQuery(paperRiskQuery);
  const orders = useQuery(paperOrdersQuery);
  const positions = useQuery(paperPositionsQuery);
  const fills = useQuery(paperFillsQuery);
  return (
    <>
      <QueryState query={summary} label="paper summary">
        {(data) => (
          <>
            <MetricGrid>
              <Metric label="Paper control" value={data.control_state} />
              <Metric label="Reconciliation" value={data.reconciliation_state} />
              <Metric label="Free cash" value={data.free_cash} />
              <Metric label="Equity" value={data.equity ?? "Unavailable"} />
              <Metric label="Realized PnL" value={data.realized_pnl} />
              <Metric label="Unrealized PnL" value={data.unrealized_pnl ?? "Unavailable"} />
            </MetricGrid>
            <Panel title="Market-data freshness">
              <p className="mono">{data.last_market_receive_ns ?? "No valid paper mark"}</p>
              <StatusPill tone="warning">Simulated paper only</StatusPill>
            </Panel>
          </>
        )}
      </QueryState>
      <QueryState query={risk} label="paper risk">
        {(data) => (
          <Panel title="Hard paper risk">
            <p>
              Open orders {data.utilization.open_orders} / {data.utilization.max_open_orders} · Reserved cash{" "}
              {data.utilization.reserved_cash} · Denials {data.deny_count}
            </p>
            <p>
              Latest decision: {data.latest_decision?.result ?? "None"} · Blocks:{" "}
              {data.latest_decision?.reason_codes.join(", ") || "None"}
            </p>
            <p>Resolution pending: {data.resolution_pending.join(", ") || "None"}</p>
          </Panel>
        )}
      </QueryState>
      <QueryState query={orders} label="paper orders" isEmpty={isEmptyList}>
        {(data) => (
          <Panel title="Paper orders">
            <DataTable label="Paper orders" headers={["Order", "Side / Style", "Quantity", "Filled / Average", "Status"]}>
              {data.items.map((item) => (
                <tr key={item.order_id}>
                  <td>
                    <Token>{item.order_id}</Token>
                  </td>
                  <td>
                    {item.side}
                    <br />
                    {item.order_style}
                  </td>
                  <td className="num">{item.quantity}</td>
                  <td className="num">
                    {item.filled_quantity}
                    <br />
                    {item.average_fill_price ?? "—"}
                  </td>
                  <td>
                    <StatusPill>{item.status}</StatusPill>
                  </td>
                </tr>
              ))}
            </DataTable>
          </Panel>
        )}
      </QueryState>
      <QueryState query={positions} label="paper positions" isEmpty={isEmptyList}>
        {(data) => (
          <Panel title="Paper positions">
            <DataTable label="Paper positions" headers={["Asset", "Quantity", "Cost basis", "Mark / Value", "Realized PnL"]}>
              {data.items.map((item) => (
                <tr key={item.asset_id}>
                  <td>
                    <Token>{item.asset_id}</Token>
                  </td>
                  <td className="num">{item.quantity}</td>
                  <td className="num">{item.cost_basis}</td>
                  <td className="num">
                    {item.mark ?? "Unavailable"}
                    <br />
                    {item.marked_value ?? "Unavailable"}
                  </td>
                  <td className="num">{item.realized_pnl}</td>
                </tr>
              ))}
            </DataTable>
          </Panel>
        )}
      </QueryState>
      <QueryState query={fills} label="simulated fills" isEmpty={isEmptyList}>
        {(data) => (
          <Panel title="Recent simulated fills">
            <DataTable label="Recent simulated fills" headers={["Fill", "Side", "Quantity", "Price / Fee", "Costs / Markout"]}>
              {data.items.map((item) => (
                <tr key={item.fill_id}>
                  <td>
                    <Token>{item.fill_id}</Token>
                  </td>
                  <td>{item.side}</td>
                  <td className="num">{item.quantity}</td>
                  <td className="num">
                    {item.price}
                    <br />
                    {item.fee}
                  </td>
                  <td className="num">
                    {item.spread_cost} / {item.depth_slippage_cost} / {item.latency_cost}
                    <br />
                    {item.adverse_selection_cost ?? item.markout_status}
                  </td>
                </tr>
              ))}
            </DataTable>
          </Panel>
        )}
      </QueryState>
    </>
  );
}

function AuditView() {
  const health = useQuery(healthQuery);
  const audit = useQuery(auditRecentQuery);
  return (
    <>
      <QueryState query={health} label="health">
        {(data) => (
          <MetricGrid>
            <Metric
              label="Overall health"
              value={<StatusPill tone={data.status === "OK" ? "success" : "warning"}>{data.status}</StatusPill>}
            />
            <Metric label="WP169 readable" value={yesNo(data.wp169.readable)} />
            <Metric label="WP170 readable" value={yesNo(data.wp170.readable)} />
            <Metric label="Paper store readable" value={yesNo(data.paper.readable)} />
          </MetricGrid>
        )}
      </QueryState>
      <QueryState query={audit} label="audit records" isEmpty={isEmptyList}>
        {(data) => (
          <Panel title="Recent audit records">
            <DataTable label="Recent audit records" headers={["Time", "Source", "Kind", "Status", "Evidence ID"]}>
              {data.items.map((item, index) => (
                <tr key={(item.record_id || item.source) + index}>
                  <td className="mono">{item.occurred_at}</td>
                  <td>{item.source}</td>
                  <td>{item.kind}</td>
                  <td>
                    <StatusPill>{item.status}</StatusPill>
                  </td>
                  <td>
                    <Token>{item.record_id || "—"}</Token>
                  </td>
                </tr>
              ))}
            </DataTable>
          </Panel>
        )}
      </QueryState>
    </>
  );
}

// ---------------------------------------------------------------------------
// S10-CC-RESEARCH-01 research views: StrategyLifecycle state + Hermes soft judgments.
// Read only. Lifecycle state, Hermes judgments and portfolio/execution/Gate-C/live
// authority stay visibly separate; no control here changes any of them.
// ---------------------------------------------------------------------------

const CONTEXT_TONE: Record<ContextStatus, Tone> = {
  CURRENT: "success",
  STALE_CONTEXT: "warning",
  TARGET_MISSING: "danger",
};

function ContextPill({ status }: { status: ContextStatus }) {
  return <StatusPill tone={CONTEXT_TONE[status]}>{status}</StatusPill>;
}

function Notice({ children }: { children: ReactNode }) {
  return (
    <aside className="notice" role="note">
      {children}
    </aside>
  );
}

function DetailList({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="detail-grid">
      {items.map(([key, value]) => (
        <div key={key}>
          <dt>{key}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function JsonBlock({ value }: { value: JsonValue }) {
  return <pre className="json-block">{JSON.stringify(value, null, 2)}</pre>;
}

function TextList({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="evidence-section">
      <h3>{title}</h3>
      {items.length === 0 ? (
        <p className="muted">None recorded.</p>
      ) : (
        <ul>
          {items.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function RefList({ title, refs }: { title: string; refs: string[] }) {
  return (
    <section className="evidence-section">
      <h3>{title}</h3>
      {refs.length === 0 ? (
        <p className="muted">None recorded.</p>
      ) : (
        <ul className="ref-list">
          {refs.map((ref) => (
            <li key={ref}>
              <Token>{ref}</Token>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function AllocationText({ allocation }: { allocation: LifecycleAllocation | null }) {
  if (!allocation) return <>No lifecycle allocation</>;
  return (
    <>
      {allocation.risk_band} · {allocation.active_budget_usd} USD reserved
    </>
  );
}

function LatestAssessment({ latest }: { latest: LatestHermesAssessment | null }) {
  if (!latest) {
    return (
      <p className="muted">
        No Hermes soft assessment available (none recorded for this version, or the Hermes source is unavailable).
      </p>
    );
  }
  return (
    <DetailList
      items={[
        ["Assessment", <Token>{latest.assessment_id}</Token>],
        ["Context", <ContextPill status={latest.context_status} />],
        ["Information cutoff", <span className="mono">{latest.information_cutoff}</span>],
        ["Confidence", latest.confidence_label],
        ["Lifecycle action (soft)", latest.lifecycle_action],
        ["Recommended health (soft)", latest.recommended_health_state],
        ["Risk direction (soft)", latest.risk_direction],
        ["Target risk band (soft)", latest.target_risk_band ?? "—"],
      ]}
    />
  );
}

function StrategyDetailPanel({ strategyVersionId, onClose }: { strategyVersionId: string; onClose: () => void }) {
  const detail = useQuery(strategyDetailQuery(strategyVersionId));
  return (
    <Panel title="Strategy version · lifecycle state">
      <div className="panel-actions">
        <Button variant="secondary" onClick={onClose}>
          Close detail
        </Button>
      </div>
      <QueryState query={detail} label="strategy detail">
        {(item) => (
          <div className="detail-stack">
            <DetailList
              items={[
                ["Strategy version", <Token>{item.strategy_version_id}</Token>],
                ["Label", item.strategy_label],
                [
                  "Family",
                  <>
                    {item.family.family_label} · <Token>{item.family.family_key}</Token>
                  </>,
                ],
                ["Family ID", <Token>{item.family.strategy_family_id}</Token>],
                ["Parent version", <Token>{item.parent_strategy_version_id ?? "Root (no parent)"}</Token>],
                ["Evidence posture", item.evidence_posture],
                ["Adaptation class", item.adaptation_class],
                ["Code identity", <Token>{item.strategy_code_identity}</Token>],
                ["Created (ns)", <span className="mono">{item.created_time_ns}</span>],
                ["Creation provenance", <Token>{item.creation_provenance}</Token>],
              ]}
            />
            <section className="evidence-section">
              <h3>Lineage · root → this version</h3>
              <ol className="lineage">
                {item.lineage_strategy_version_ids.map((id) => (
                  <li key={id} className={id === item.strategy_version_id ? "lineage-current" : undefined}>
                    <Token>{id}</Token>
                  </li>
                ))}
              </ol>
            </section>
            <section className="evidence-section">
              <h3>Current lifecycle state</h3>
              <DetailList
                items={[
                  ["Health", <StatusPill>{item.current_state.health_state ?? "Unknown"}</StatusPill>],
                  ["Active portfolio policy", <Token>{item.current_state.active_policy_id ?? "None active"}</Token>],
                  ["Lifecycle allocation", <AllocationText allocation={item.current_state.allocation} />],
                  ["Lifecycle context sha256", <Token>{item.current_state.strategy_lifecycle_context_sha256}</Token>],
                ]}
              />
              <p className="muted">Allocation is a lifecycle budget reservation, not actual exposure, positions or orders.</p>
              <h3>Active restrictions</h3>
              {item.current_state.active_restrictions.length === 0 ? (
                <p className="muted">No active restrictions.</p>
              ) : (
                <ul className="ref-list">
                  {item.current_state.active_restrictions.map((restriction) => (
                    <li key={restriction.restriction_receipt_id}>
                      <StatusPill tone="warning">{restriction.restriction_kind}</StatusPill>{" "}
                      <Token>{restriction.restriction_key}</Token>
                      {restriction.max_active_budget_usd !== null && <> · cap {restriction.max_active_budget_usd} USD</>}
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <section className="evidence-section">
              <h3>Strategy definition</h3>
              {Object.entries(item.strategy_definition).map(([key, value]) => (
                <div key={key} className="definition-entry">
                  <h4>{key}</h4>
                  <JsonBlock value={value} />
                </div>
              ))}
              <h4>adaptive_bounds</h4>
              <JsonBlock value={item.adaptive_bounds} />
            </section>
            <RefList title="Evidence references" refs={item.evidence_refs} />
            <section className="evidence-section">
              <h3>Latest Hermes soft assessment</h3>
              <LatestAssessment latest={item.latest_hermes_assessment} />
            </section>
          </div>
        )}
      </QueryState>
    </Panel>
  );
}

function StrategiesView() {
  const strategies = useQuery(strategiesQuery);
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <>
      <Notice>
        <strong>Lifecycle state, not trading authority.</strong> Allocation is a lifecycle budget reservation, not actual
        exposure. Hermes columns show soft advisory judgments with their context status (CURRENT, STALE_CONTEXT or
        TARGET_MISSING). Nothing here is approval to trade, Gate-C eligibility, execution readiness or live permission.
      </Notice>
      <div className={selected ? "split" : undefined}>
        <QueryState query={strategies} label="strategy versions" isEmpty={isEmptyList}>
          {(data) => (
            <Panel title="Strategy versions">
              <DataTable
                label="Strategy versions"
                headers={["Strategy", "Health", "Lifecycle allocation", "Restrictions", "Hermes soft context"]}
              >
                {data.items.map((item) => (
                  <tr key={item.strategy_version_id} className={item.strategy_version_id === selected ? "selected" : undefined}>
                    <td>
                      <Button variant="link" onClick={() => setSelected(item.strategy_version_id)}>
                        {item.strategy_label}
                      </Button>
                      <br />
                      <Token>{item.strategy_version_id}</Token>
                      <br />
                      <span className="muted">
                        {item.evidence_posture} · {item.adaptation_class} · {item.evidence_ref_count} evidence refs
                      </span>
                    </td>
                    <td>
                      <StatusPill>{item.current_health_state ?? "Unknown"}</StatusPill>
                    </td>
                    <td>
                      <AllocationText allocation={item.current_allocation} />
                    </td>
                    <td className="num">{item.active_restriction_count}</td>
                    <td>
                      {item.latest_hermes_assessment ? (
                        <>
                          <ContextPill status={item.latest_hermes_assessment.context_status} />
                          <br />
                          {item.latest_hermes_assessment.lifecycle_action} · {item.latest_hermes_assessment.confidence_label}
                        </>
                      ) : (
                        <span className="muted">No Hermes assessment</span>
                      )}
                    </td>
                  </tr>
                ))}
              </DataTable>
            </Panel>
          )}
        </QueryState>
        {selected && <StrategyDetailPanel strategyVersionId={selected} onClose={() => setSelected(null)} />}
      </div>
    </>
  );
}

const NON_AUTHORITY_LABELS: [keyof HermesNonAuthority, string][] = [
  ["canonical_soft_strategy_decision", "Canonical soft strategy decision"],
  ["no_credential_authority", "No credential authority"],
  ["no_portfolio_policy_authority", "No portfolio policy authority"],
  ["no_hard_risk_override", "No hard risk override"],
  ["no_paper_execution_authority", "No paper execution authority"],
  ["no_order_authority", "No order authority"],
  ["no_execution_authority", "No execution authority"],
  ["no_live_authority", "No live authority"],
];

function HermesDetailPanel({ assessmentId, onClose }: { assessmentId: string; onClose: () => void }) {
  const detail = useQuery(hermesAssessmentDetailQuery(assessmentId));
  return (
    <Panel title="Hermes soft assessment · research judgment only">
      <div className="panel-actions">
        <Button variant="secondary" onClick={onClose}>
          Close detail
        </Button>
      </div>
      <QueryState query={detail} label="assessment detail">
        {(item) => (
          <div className="detail-stack">
            <p className="summary">{item.assessment_summary}</p>
            <DetailList
              items={[
                ["Assessment", <Token>{item.assessment_id}</Token>],
                ["Strategy version", <Token>{item.strategy_version_id}</Token>],
                ["Strategy family", <Token>{item.strategy_family_id}</Token>],
                ["Predecessor", <Token>{item.predecessor_assessment_id ?? "None (first assessment)"}</Token>],
                ["Context", <ContextPill status={item.context_status} />],
                ["Information cutoff", <span className="mono">{item.information_cutoff}</span>],
                ["Decision time (ns)", <span className="mono">{item.decision_time_ns}</span>],
                ["Trigger", item.trigger],
                ["Confidence", item.confidence_label],
              ]}
            />
            <section className="evidence-section">
              <h3>Soft lifecycle / risk recommendation</h3>
              <DetailList
                items={[
                  ["Lifecycle action", item.lifecycle_action],
                  ["Recommended health", item.recommended_health_state],
                  ["Risk direction", item.risk_direction],
                  ["Target risk band", item.target_risk_band ?? "—"],
                  [
                    "Adaptation recommendation",
                    item.adaptation_recommendation ? (
                      <>
                        {item.adaptation_recommendation.kind} · {item.adaptation_recommendation.summary}
                        <JsonBlock value={item.adaptation_recommendation.parameter_updates} />
                      </>
                    ) : (
                      "None"
                    ),
                  ],
                ]}
              />
              <p className="muted">A recommendation is advisory. It changes no lifecycle state, allocation, policy or order.</p>
            </section>
            <div className="evidence-columns">
              <TextList title="Evidence for" items={item.evidence_for} />
              <TextList title="Evidence against" items={item.evidence_against} />
              <TextList title="Uncertainties" items={item.uncertainties} />
              <TextList title="Known missing data" items={item.known_missing_data} />
              <TextList title="Falsification checks performed" items={item.falsification_checks_performed} />
              <TextList title="Limitations" items={item.limitations} />
              <TextList title="What would change the conclusion" items={item.what_would_change_the_conclusion} />
              <TextList title="Suggested next research steps" items={item.suggested_next_research_steps} />
            </div>
            <RefList title="Subject references" refs={item.subject_refs} />
            <RefList title="Input evidence references" refs={item.input_evidence_refs} />
            <section className="evidence-section">
              <h3>Context binding</h3>
              <DetailList
                items={[
                  ["Assessed context sha256", <Token>{item.strategy_lifecycle_context_sha256}</Token>],
                  ["Lifecycle store head at assessment", <Token>{item.lifecycle_store_head_entry_hash ?? "—"}</Token>],
                  ["Active policy at assessment", <Token>{item.active_policy_id ?? "None active"}</Token>],
                ]}
              />
            </section>
            <section className="evidence-section">
              <h3>Run metadata</h3>
              <DetailList
                items={[
                  [
                    "Provider / model",
                    <>
                      {item.run.provider_label} · {item.run.model_label}
                    </>,
                  ],
                  ["Hermes version", item.run.hermes_version],
                  ["Terminal status", item.run.terminal_status],
                  [
                    "Run window (UTC)",
                    <span className="mono">
                      {item.run.start_utc} → {item.run.end_utc}
                    </span>,
                  ],
                  [
                    "Estimated cost",
                    <>
                      {item.run.estimated_cost_usd ?? "—"} USD · {item.run.cost_status ?? "—"} · {item.run.cost_source ?? "—"}
                    </>,
                  ],
                  ["Run record", <Token>{item.run_record_id}</Token>],
                  [
                    "Runtime request / receipt",
                    <>
                      <Token>{item.runtime_request_id}</Token>
                      <br />
                      <Token>{item.runtime_receipt_id}</Token>
                    </>,
                  ],
                ]}
              />
            </section>
            <section className="evidence-section">
              <h3>Non-authority</h3>
              <ul className="flag-list">
                {NON_AUTHORITY_LABELS.map(([flag, label]) => (
                  <li key={flag}>
                    <StatusPill tone={item.non_authority[flag] ? "neutral" : "danger"}>
                      {item.non_authority[flag] ? "TRUE" : "FALSE"}
                    </StatusPill>{" "}
                    {label}
                  </li>
                ))}
              </ul>
            </section>
          </div>
        )}
      </QueryState>
    </Panel>
  );
}

function HermesView() {
  const assessments = useQuery(hermesAssessmentsQuery);
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <>
      <Notice>
        <strong>Hermes assessments are soft research judgments.</strong> They do not grant portfolio, execution, Gate-C
        or live authority. Context status compares each assessment with the current lifecycle context: CURRENT,
        STALE_CONTEXT (lifecycle changed since the assessment) or TARGET_MISSING.
      </Notice>
      <div className={selected ? "split" : undefined}>
        <QueryState query={assessments} label="Hermes assessments" isEmpty={isEmptyList}>
          {(data) => (
            <Panel title="Hermes soft assessments">
              <DataTable label="Hermes soft assessments" headers={["Assessment", "Strategy", "Soft recommendation", "Confidence", "Context"]}>
                {data.items.map((item) => (
                  <tr key={item.assessment_id} className={item.assessment_id === selected ? "selected" : undefined}>
                    <td>
                      <Button variant="link" onClick={() => setSelected(item.assessment_id)}>
                        <span className="token">{item.assessment_id}</span>
                      </Button>
                      <br />
                      <span className="mono muted">
                        {item.information_cutoff} · {item.decision_time_ns}
                      </span>
                    </td>
                    <td>
                      <Token>{item.strategy_version_id}</Token>
                    </td>
                    <td>
                      {item.lifecycle_action} · {item.recommended_health_state}
                      <br />
                      <span className="muted">
                        Risk {item.risk_direction}
                        {item.target_risk_band ? " → " + item.target_risk_band : ""}
                      </span>
                    </td>
                    <td>{item.confidence_label}</td>
                    <td>
                      <ContextPill status={item.context_status} />
                    </td>
                  </tr>
                ))}
              </DataTable>
            </Panel>
          )}
        </QueryState>
        {selected && <HermesDetailPanel assessmentId={selected} onClose={() => setSelected(null)} />}
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// S10-CC-RESEARCH-02 Alpha workspace: recorded Alpha Factory research memory and the latest
// recorded Alpha Discovery queue. Read only. Research records never become qualification,
// strategy selection, trade priority, execution or live authority, and no source is fetched.
// ---------------------------------------------------------------------------

const RESULT_TONE: Record<ResearchResultState, Tone> = {
  RESEARCH_SUPPORTIVE: "success",
  NO_EDGE_CURRENTLY: "neutral",
  HYPOTHESIS_FALSIFIED: "neutral",
  DATA_INSUFFICIENT: "warning",
  EXECUTION_UNECONOMIC: "neutral",
  WATCH_FOR_CHANGE: "warning",
  RESEARCH_STALE: "warning",
  REOPEN_TRIGGERED: "warning",
  MECHANISM_FAMILY_EXHAUSTED: "neutral",
};

function ResultStatePill({ state }: { state: ResearchResultState }) {
  return <StatusPill tone={RESULT_TONE[state]}>{state}</StatusPill>;
}

function LaneTags({ lanes, multiLane }: { lanes: string[]; multiLane: boolean }) {
  return (
    <span className="tag-row">
      {lanes.map((lane) => (
        <StatusPill key={lane}>{lane}</StatusPill>
      ))}
      {multiLane && <span className="muted">multi-lane</span>}
    </span>
  );
}

/** Canonical JSON text from a record, pretty-printed for reading only. */
function JsonText({ value }: { value: string }) {
  let pretty = value;
  try {
    pretty = JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    // Keep the canonical text as recorded.
  }
  return <pre className="json-block">{pretty}</pre>;
}

/** Source locators are canonical evidence metadata shown as text only: never linked or fetched. */
function SourceReferenceList({ sources }: { sources: AlphaSourceReference[] }) {
  return (
    <section className="evidence-section">
      <h3>Source references</h3>
      {sources.length === 0 ? (
        <p className="muted">None recorded.</p>
      ) : (
        <ul className="ref-list source-list">
          {sources.map((source) => (
            <li key={source.source_reference_id}>
              <strong>{source.title}</strong> <StatusPill>{source.source_kind}</StatusPill>{" "}
              <StatusPill>{source.source_class}</StatusPill>
              <br />
              <span className="locator">{source.source_locator}</span>
              <br />
              <span className="muted">
                Observed <span className="mono">{source.observed_at}</span> · {source.provenance}
              </span>
              <br />
              <Token>{source.source_reference_id}</Token>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function AlphaEpisodePanel({ researchEpisodeId, onClose }: { researchEpisodeId: string; onClose: () => void }) {
  const detail = useQuery(alphaEpisodeDetailQuery(researchEpisodeId));
  return (
    <Panel title="Research episode · recorded evidence">
      <div className="panel-actions">
        <Button variant="secondary" onClick={onClose}>
          Close episode
        </Button>
      </div>
      <QueryState query={detail} label="research episode">
        {(item) => (
          <div className="detail-stack">
            <p className="summary">{item.thesis}</p>
            <DetailList
              items={[
                ["Research episode", <Token>{item.research_episode_id}</Token>],
                ["Research state", <ResultStatePill state={item.result_state} />],
                ["Confidence", item.confidence_label],
                ["Evidence lanes", <LaneTags lanes={item.evidence_lanes} multiLane={item.is_multi_lane} />],
                ["Research question", item.research_question],
                ["Research as of", <span className="mono">{item.research_as_of}</span>],
                ["Candidate", <Token>{item.candidate_id}</Token>],
                ["Hypothesis family", <Token>{item.hypothesis_family_id}</Token>],
                ["Predecessor episode", <Token>{item.predecessor_episode_id ?? "None (lineage root)"}</Token>],
                ["Reopens episode", <Token>{item.reopened_episode_id ?? "—"}</Token>],
                ["Episode version", <Token>{item.episode_version}</Token>],
              ]}
            />
            {item.result_state === "RESEARCH_SUPPORTIVE" && (
              <p className="muted">
                RESEARCH_SUPPORTIVE means further deterministic qualification may be worthwhile. It is not a qualification
                pass, proven predictive edge, positive out-of-sample result, executable edge or trading readiness.
              </p>
            )}
            <div className="evidence-columns">
              <TextList title="Tested assumptions" items={item.tested_assumptions} />
              <TextList title="Evidence for" items={item.evidence_for} />
              <TextList title="Evidence against" items={item.evidence_against} />
              <TextList title="Uncertainties" items={item.uncertainties} />
              <TextList title="Known missing data" items={item.known_missing_data} />
              <TextList title="Falsification checks performed" items={item.falsification_checks_performed} />
              <TextList title="Limitations" items={item.limitations} />
              <TextList title="What would change the conclusion" items={item.what_would_change_the_conclusion} />
              <TextList title="Suggested next research steps" items={item.suggested_next_research_steps} />
              <TextList title="Material change basis" items={item.material_change_basis} />
            </div>
            <section className="evidence-section">
              <h3>Exact scope (this result applies here only)</h3>
              <JsonText value={item.exact_scope_json} />
              <h3>Evidence regime</h3>
              <JsonText value={item.evidence_regime_json} />
            </section>
            <SourceReferenceList sources={item.source_references} />
            <RefList title="Deterministic evidence references (opaque)" refs={item.deterministic_evidence_refs} />
            <section className="evidence-section">
              <h3>Producer provenance</h3>
              <DetailList
                items={[
                  ["Producer", item.producer_type],
                  ["Producer version", <Token>{item.producer_version}</Token>],
                  ["Producer receipt", <Token>{item.producer_receipt_ref ?? "—"}</Token>],
                  ["Creation provenance", <Token>{item.creation_provenance}</Token>],
                  ["Human review required", yesNo(item.human_review_required)],
                ]}
              />
            </section>
          </div>
        )}
      </QueryState>
    </Panel>
  );
}

function AlphaCandidatePanel({
  candidateId,
  selectedEpisode,
  onSelectEpisode,
  onClose,
}: {
  candidateId: string;
  selectedEpisode: string | null;
  onSelectEpisode: (researchEpisodeId: string) => void;
  onClose: () => void;
}) {
  const detail = useQuery(alphaCandidateDetailQuery(candidateId));
  return (
    <Panel title="Research candidate · recorded lineage">
      <div className="panel-actions">
        <Button variant="secondary" onClick={onClose}>
          Close candidate
        </Button>
      </div>
      <QueryState query={detail} label="candidate lineage">
        {(data) => {
          const leaves = new Set(data.lineage_summary.leaf_episode_ids);
          return (
            <div className="detail-stack">
              <p className="summary">{data.candidate.thesis}</p>
              <DetailList
                items={[
                  ["Candidate", <Token>{data.candidate.candidate_id}</Token>],
                  ["Title", data.candidate.title],
                  ["Research question", data.candidate.research_question],
                  ["Evidence lanes", <LaneTags lanes={data.candidate.evidence_lanes} multiLane={data.candidate.is_multi_lane} />],
                  ["Scope key", <Token>{data.candidate.scope_key}</Token>],
                  ["Mechanism hint", data.candidate.mechanism_hint],
                  ["Novelty fingerprint", <Token>{data.candidate.novelty_fingerprint}</Token>],
                  ["Discovery provenance", <Token>{data.candidate.discovery_provenance}</Token>],
                  ["Human review required", yesNo(data.candidate.human_review_required)],
                ]}
              />
              <section className="evidence-section">
                <h3>Novelty dimensions</h3>
                <JsonText value={data.candidate.novelty_dimensions_json} />
              </section>
              <RefList title="Subject references" refs={data.candidate.subject_refs} />
              <section className="evidence-section">
                <h3>
                  Research lineage · {data.lineage_summary.family_count} families · {data.lineage_summary.episode_count}{" "}
                  episodes · {data.lineage_summary.leaf_episode_count} research leaves
                </h3>
                <p className="muted">
                  A research leaf is an episode no later episode of the same lineage builds on or reopens. Several leaves
                  can coexist; a leaf is not a qualification, approval or trading signal.
                </p>
                {data.hypothesis_families.map((family) => (
                  <div key={family.hypothesis_family_id} className="family-block">
                    <h4>{family.family_name}</h4>
                    <p className="muted">
                      {family.falsifiable_theme} · mechanism <Token>{family.mechanism_key}</Token>
                    </p>
                    <p className="muted">
                      Family <Token>{family.hypothesis_family_id}</Token> · fingerprint{" "}
                      <Token>{family.mechanism_fingerprint}</Token>
                    </p>
                    <ol className="lineage">
                      {data.research_episodes
                        .filter((episode) => episode.hypothesis_family_id === family.hypothesis_family_id)
                        .map((episode) => (
                          <li
                            key={episode.research_episode_id}
                            className={episode.research_episode_id === selectedEpisode ? "lineage-current" : undefined}
                          >
                            <Button variant="link" onClick={() => onSelectEpisode(episode.research_episode_id)}>
                              <span className="token">{episode.research_episode_id}</span>
                            </Button>
                            <div className="tag-row">
                              <ResultStatePill state={episode.result_state} />
                              <span className="muted">
                                #{episode.sequence_number} · {episode.confidence_label} · {episode.producer_type}
                              </span>
                              {leaves.has(episode.research_episode_id) && <StatusPill>research leaf</StatusPill>}
                            </div>
                            {episode.predecessor_episode_id && (
                              <div className="muted">
                                Builds on <Token>{episode.predecessor_episode_id}</Token>
                              </div>
                            )}
                            {episode.reopened_episode_id && (
                              <div className="muted">
                                Reopens <Token>{episode.reopened_episode_id}</Token> (appended; the earlier episode is
                                unchanged)
                              </div>
                            )}
                          </li>
                        ))}
                    </ol>
                  </div>
                ))}
              </section>
              <SourceReferenceList sources={data.source_references} />
              <RefList title="Deterministic evidence references (opaque)" refs={data.deterministic_evidence_refs} />
            </div>
          );
        }}
      </QueryState>
    </Panel>
  );
}

function ResearchMemoryPane() {
  const memory = useQuery(alphaMemoryQuery);
  const candidates = useQuery(alphaCandidatesQuery);
  const [candidate, setCandidate] = useState<string | null>(null);
  const [episode, setEpisode] = useState<string | null>(null);
  const selectCandidate = (candidateId: string | null) => {
    setCandidate(candidateId);
    setEpisode(null);
  };
  return (
    <>
      <Notice>
        <strong>Alpha Factory records research history.</strong>{" "}
        RESEARCH_SUPPORTIVE is not qualification, executable edge, profitability or trading authority.
        Negative results describe their exact recorded scope and evidence regime only, never a permanent market or category
        blacklist. A reopen appends new lineage; earlier episodes are never rewritten.
      </Notice>
      <QueryState query={memory} label="Alpha research memory">
        {(data) => (
          <>
            <MetricGrid>
              <Metric label="Candidates" value={data.record_counts.opportunity_candidates} />
              <Metric label="Hypothesis families" value={data.record_counts.hypothesis_families} />
              <Metric label="Research episodes" value={data.record_counts.research_episodes} />
              <Metric label="Source references" value={data.record_counts.research_source_references} />
              <Metric label="Registry rows" value={data.total_rows} />
            </MetricGrid>
            <p className="muted">
              Recorded research memory · registry head <Token>{data.head_entry_hash ?? "Empty registry (no records)"}</Token>
            </p>
          </>
        )}
      </QueryState>
      <div className={candidate ? "split" : undefined}>
        <QueryState query={candidates} label="research candidates" isEmpty={isEmptyList}>
          {(data) => (
            <Panel title="Research candidates · registry order (newest record first)">
              <DataTable label="Research candidates" headers={["Candidate", "Evidence lanes", "Lineage"]}>
                {data.items.map((item) => (
                  <tr key={item.candidate_id} className={item.candidate_id === candidate ? "selected" : undefined}>
                    <td>
                      <Button variant="link" onClick={() => selectCandidate(item.candidate_id)}>
                        {item.title}
                      </Button>
                      <br />
                      <Token>{item.candidate_id}</Token>
                      <br />
                      <span className="muted">{item.research_question}</span>
                    </td>
                    <td>
                      <LaneTags lanes={item.evidence_lanes} multiLane={item.is_multi_lane} />
                    </td>
                    <td className="num">
                      {item.family_count} families
                      <br />
                      {item.episode_count} episodes
                      <br />
                      {item.leaf_episode_count} research leaves
                    </td>
                  </tr>
                ))}
              </DataTable>
            </Panel>
          )}
        </QueryState>
        {candidate && (
          <AlphaCandidatePanel
            candidateId={candidate}
            selectedEpisode={episode}
            onSelectEpisode={setEpisode}
            onClose={() => selectCandidate(null)}
          />
        )}
      </div>
      {episode && <AlphaEpisodePanel researchEpisodeId={episode} onClose={() => setEpisode(null)} />}
    </>
  );
}

const LANE_SECTIONS: [DiscoveryLaneName, string, string][] = [
  ["core", "Core priority", "Research allocation lane; not trade priority."],
  ["exploration", "Exploration", "Coverage-seeking research allocation."],
  ["audit", "Audit", "Deterministic audit sample of the remaining research pool."],
  ["deferred", "Deferred", "Waiting on capture refresh before research."],
  ["skipped_ineligible", "Skipped · ineligible", "Market status outside the recorded policy."],
  ["skipped_capacity", "Skipped · capacity", "Eligible but outside the recorded queue capacity."],
];

const RESOLUTION_TONE: Record<AlphaResolutionStatus, Tone> = {
  RESOLVED: "success",
  NOT_BOUND: "neutral",
  UNAVAILABLE: "warning",
  HEAD_MISMATCH: "danger",
};

const RESOLUTION_TEXT: Record<AlphaResolutionStatus, string> = {
  RESOLVED:
    "The verified Alpha Factory registry head equals the Alpha-memory binding head recorded on this triage; only the canonical matched ids are resolved.",
  NOT_BOUND:
    "This triage was recorded without an Alpha-memory binding head (for example a historical replay); no Alpha records are resolved.",
  UNAVAILABLE:
    "This triage binds an Alpha-memory head, but the Alpha Factory registry is not configured or could not be verified here. The canonical matched ids remain the record.",
  HEAD_MISMATCH:
    "The verified Alpha Factory registry head differs from the Alpha-memory binding head recorded on this triage, so no ids are resolved against it. This is research-lineage truth, not market freshness.",
};

function TriageDetailPanel({ marketTriageDecisionId, onClose }: { marketTriageDecisionId: string; onClose: () => void }) {
  const detail = useQuery(alphaTriageDetailQuery(marketTriageDecisionId));
  return (
    <Panel title="Triage decision · research allocation evidence">
      <div className="panel-actions">
        <Button variant="secondary" onClick={onClose}>
          Close triage
        </Button>
      </div>
      <QueryState query={detail} label="triage detail">
        {(data) => {
          const { triage, universe_market: market, material_change: change, alpha_memory_resolution: alpha } = data;
          return (
            <div className="detail-stack">
              <DetailList
                items={[
                  ["Triage decision", <Token>{triage.market_triage_decision_id}</Token>],
                  ["Market / event", <><Token>{triage.market_id}</Token><br /><Token>{triage.event_id}</Token></>],
                  ["Category", triage.category ?? "—"],
                  ["Final disposition (research lane)", <StatusPill>{triage.final_disposition}</StatusPill>],
                  ["Priority class (research)", triage.priority_class],
                  ["Readiness (research control)", triage.readiness],
                  ["Reopen disposition (research)", triage.reopen_disposition],
                  ["Eligibility", triage.eligibility],
                  ["Newly observed locally", yesNo(triage.newly_observed_locally)],
                  ["Analysis mode", triage.analysis_temporal_mode],
                  ["Alpha-memory posture", triage.alpha_memory_temporal_posture],
                  ["Alpha-memory binding head", <Token>{triage.alpha_registry_head_entry_hash ?? "None (not bound)"}</Token>],
                  ["Historical selection replay valid", yesNo(triage.historical_selection_replay_valid)],
                ]}
              />
              <RefList title="Reason codes" refs={triage.reason_codes} />
              <section className="evidence-section">
                <h3>Capture requests (data only; nothing is fetched)</h3>
                {triage.capture_requests.length === 0 ? (
                  <p className="muted">None recorded.</p>
                ) : (
                  <ul className="ref-list">
                    {triage.capture_requests.map((request) => (
                      <li key={request.pre_allocation_semantic_key}>
                        <StatusPill>{request.request_type}</StatusPill> {request.reason_code}
                        {request.token_id && (
                          <>
                            {" "}
                            · <Token>{request.token_id}</Token>
                          </>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </section>
              <section className="evidence-section">
                <h3>Research archetype coverage</h3>
                <dl className="coverage-grid">
                  {triage.coverage.map((entry) => (
                    <div key={entry.research_archetype}>
                      <dt>{entry.research_archetype}</dt>
                      <dd>{entry.coverage_state}</dd>
                    </div>
                  ))}
                </dl>
              </section>
              <section className="evidence-section">
                <h3>Observed universe market</h3>
                <p className="summary">{market.question_text ?? "No question text recorded"}</p>
                <DetailList
                  items={[
                    ["Market status", market.market_status ?? "—"],
                    ["Condition", <Token>{market.condition_id ?? "—"}</Token>],
                    ["Outcomes", market.outcome_labels.join(" / ") || "—"],
                    ["Resolution date", <span className="mono">{market.resolution_date ?? "—"}</span>],
                    ["Metadata observed", <span className="mono">{market.metadata_observed_time}</span>],
                    ["Recorded metadata freshness", market.metadata_freshness],
                    ["Rules / books recorded", `${market.resolution_rule_count} / ${market.order_book_count}`],
                    ["Data gaps", market.data_gap_codes.join(", ") || "None"],
                  ]}
                />
                <RefList title="Token ids" refs={market.token_ids} />
              </section>
              <section className="evidence-section">
                <h3>Material change</h3>
                {change === null ? (
                  <p className="muted">No material change recorded for this triage.</p>
                ) : (
                  <>
                    <DetailList
                      items={[
                        ["Material change", <Token>{change.material_change_event_id}</Token>],
                        ["Prior → current universe", <><Token>{change.prior_universe_id}</Token><br /><Token>{change.current_universe_id}</Token></>],
                        ["Hard changes", change.hard_change_classes.join(", ") || "None"],
                        ["Soft changes", change.soft_change_classes.join(", ") || "None"],
                        ["Review-only changes", change.review_only_change_classes.join(", ") || "None"],
                        ["Reopen-material (research)", yesNo(change.reopen_material)],
                        ["Diagnostics", change.comparison_diagnostics.join(", ") || "None"],
                      ]}
                    />
                    <ul className="ref-list">
                      {change.affected_token_ids.map((entry) => (
                        <li key={entry.change_class}>
                          {entry.change_class}: {entry.token_ids.join(", ")}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </section>
              <section className="evidence-section">
                <h3>Alpha-memory resolution</h3>
                <p>
                  <StatusPill tone={RESOLUTION_TONE[alpha.status]}>{alpha.status}</StatusPill>
                </p>
                <p className="muted">{RESOLUTION_TEXT[alpha.status]}</p>
                <RefList title="Matched candidate ids (canonical)" refs={triage.matched_candidate_ids} />
                <RefList title="Matched hypothesis family ids (canonical)" refs={triage.matched_hypothesis_family_ids} />
                <RefList title="Matched research episode ids (canonical)" refs={triage.matched_research_episode_ids} />
                {alpha.status === "RESOLVED" && (
                  <ul className="ref-list">
                    {alpha.candidates.map((candidate) => (
                      <li key={candidate.candidate_id}>
                        <strong>{candidate.title}</strong> · <Token>{candidate.candidate_id}</Token>
                      </li>
                    ))}
                    {alpha.research_episodes.map((episode) => (
                      <li key={episode.research_episode_id}>
                        <ResultStatePill state={episode.result_state} /> <Token>{episode.research_episode_id}</Token>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          );
        }}
      </QueryState>
    </Panel>
  );
}

function DiscoveryQueuePane() {
  const queue = useQuery(alphaDiscoveryQueueQuery);
  const [triage, setTriage] = useState<string | null>(null);
  return (
    <>
      <Notice>
        <strong>Discovery priority is research allocation only.</strong>{" "}
        It is not strategy selection or trade priority.
        READY is research-control readiness, not trading readiness; REOPEN_ELIGIBLE is a research reopen condition, not
        strategy or live authorization. This view shows the latest recorded discovery queue from the verified Discovery
        registry over a bounded observed universe whose external completeness is UNPROVEN.
      </Notice>
      <QueryState query={queue} label="latest recorded discovery queue">
        {(data) => (
          <>
            <MetricGrid>
              <Metric label="Universe as_of" value={<span className="mono">{data.universe.as_of}</span>} />
              <Metric label="Observed markets" value={data.universe.market_count} />
              <Metric
                label="External completeness"
                value={<StatusPill tone="warning">{data.universe.external_universe_completeness}</StatusPill>}
              />
              <Metric label="Queue capacity" value={data.queue.queue_capacity} />
              <Metric
                label="Unused exploration / audit"
                value={`${data.queue.unused_exploration_slots} / ${data.queue.unused_audit_slots}`}
              />
              <Metric label="Registry sequence" value={data.queue_sequence_number} />
            </MetricGrid>
            <Panel title="Latest recorded discovery queue">
              <DetailList
                items={[
                  ["Queue snapshot", <Token>{data.queue.alpha_research_queue_snapshot_id}</Token>],
                  ["Universe snapshot", <Token>{data.universe.alpha_universe_snapshot_id}</Token>],
                  ["Coverage scope", data.universe.coverage_scope],
                  ["Analysis mode", data.queue.analysis_temporal_mode],
                  ["Alpha-memory posture", data.queue.alpha_memory_temporal_posture],
                  ["Alpha-memory binding head", <Token>{data.queue.alpha_registry_head_entry_hash ?? "None (not bound)"}</Token>],
                  ["Discovery registry head", <Token>{data.discovery_registry_head_entry_hash ?? "—"}</Token>],
                  ["Unused capacity reasons", data.queue.unused_capacity_reason_codes.join(", ") || "None"],
                  ["Prior-only markets", data.queue.prior_only_market_ids.join(", ") || "None"],
                  ["Policy", <>{data.policy.policy_version} · <Token>{data.policy.alpha_discovery_policy_id}</Token></>],
                  [
                    "Policy slots (queue capacity / exploration / audit / per category)",
                    `${data.policy.queue_capacity} / ${data.policy.exploration_slots} / ${data.policy.audit_slots} / ${data.policy.max_per_category}`,
                  ],
                  [
                    "Recorded freshness thresholds (metadata / book / rule, s)",
                    `${data.policy.metadata_freshness_seconds} / ${data.policy.order_book_freshness_seconds} / ${data.policy.resolution_rule_freshness_seconds}`,
                  ],
                ]}
              />
            </Panel>
            <div className={triage ? "split" : undefined}>
              <div className="detail-stack">
                {LANE_SECTIONS.map(([lane, title, description]) => (
                  <Panel key={lane} title={`${title} · ${data.lanes[lane].length}`}>
                    <p className="muted">{description}</p>
                    {data.lanes[lane].length === 0 ? (
                      <p className="muted">No triage decisions in this lane.</p>
                    ) : (
                      <DataTable label={title} headers={["Market", "Research priority", "Readiness / reopen", "Alpha refs"]}>
                        {data.lanes[lane].map((item) => (
                          <tr
                            key={item.market_triage_decision_id}
                            className={item.market_triage_decision_id === triage ? "selected" : undefined}
                          >
                            <td>
                              <Button variant="link" onClick={() => setTriage(item.market_triage_decision_id)}>
                                <span className="token">{item.market_id}</span>
                              </Button>
                              <br />
                              <span className="muted">
                                {item.category ?? "Uncategorized"}
                                {item.newly_observed_locally ? " · newly observed locally" : ""}
                              </span>
                            </td>
                            <td>
                              {item.priority_class}
                              <br />
                              <span className="muted">{item.reason_codes.join(", ")}</span>
                            </td>
                            <td>
                              {item.readiness}
                              <br />
                              <span className="muted">{item.reopen_disposition}</span>
                            </td>
                            <td className="num">
                              {item.matched_candidate_ids.length} candidates
                              <br />
                              {item.matched_research_episode_ids.length} episodes
                            </td>
                          </tr>
                        ))}
                      </DataTable>
                    )}
                  </Panel>
                ))}
              </div>
              {triage && <TriageDetailPanel marketTriageDecisionId={triage} onClose={() => setTriage(null)} />}
            </div>
          </>
        )}
      </QueryState>
    </>
  );
}

function AlphaView() {
  const [tab, setTab] = useState<"memory" | "discovery">("memory");
  return (
    <>
      <div className="tabs" role="tablist" aria-label="Alpha research workspace">
        <button type="button" role="tab" aria-selected={tab === "memory"} className="tab" onClick={() => setTab("memory")}>
          Research Memory
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "discovery"}
          className="tab"
          onClick={() => setTab("discovery")}
        >
          Discovery Queue
        </button>
      </div>
      <div role="tabpanel">{tab === "memory" ? <ResearchMemoryPane /> : <DiscoveryQueuePane />}</div>
    </>
  );
}

// ---------------------------------------------------------------------------
// S10-CC-OPS-01 operations view: portfolio policy / budget reservations, recorded gateway
// state and simulated paper risk. Read only. Each source loads and fails independently, and
// no value from one source is combined with another. Capacity comes only from the backend's
// canonical evaluator at the backend evaluation time; the browser clock is never used.
// ---------------------------------------------------------------------------

const CAPACITY_TONE: Record<CapacityStatus, Tone> = {
  PORTFOLIO_CAPACITY_VALID: "success",
  PORTFOLIO_CAPACITY_REJECTED: "warning",
};

function CapacityPill({ status }: { status: CapacityStatus }) {
  return <StatusPill tone={CAPACITY_TONE[status]}>{status}</StatusPill>;
}

function ReasonCodes({ codes }: { codes: string[] }) {
  if (codes.length === 0) return <span className="muted">None</span>;
  return (
    <span className="tag-row">
      {codes.map((code) => (
        <Token key={code}>{code}</Token>
      ))}
    </span>
  );
}

const POLICY_LIMIT_LABELS: [keyof OpsPolicyLimits, string][] = [
  ["global_capital_at_risk_max_usd", "Global capital-at-risk ceiling (USD)"],
  ["global_gross_exposure_max_usd", "Global gross exposure ceiling (USD)"],
  ["global_daily_loss_max_usd", "Global daily loss ceiling (USD)"],
  ["global_drawdown_max_usd", "Global drawdown ceiling (USD)"],
  ["global_cumulative_loss_max_usd", "Global cumulative loss ceiling (USD)"],
  ["exploratory_pool_max_usd", "Exploratory pool ceiling (USD)"],
  ["validated_pool_max_usd", "Validated pool ceiling (USD)"],
  ["mature_pool_max_usd", "Mature pool ceiling (USD)"],
  ["max_exploratory_per_strategy_usd", "Exploratory per-strategy ceiling (USD)"],
  ["max_validated_per_strategy_usd", "Validated per-strategy ceiling (USD)"],
  ["max_mature_per_strategy_usd", "Mature per-strategy ceiling (USD)"],
  ["max_per_market_usd", "Per-market ceiling (USD)"],
  ["max_order_notional_usd", "Order notional ceiling (USD)"],
  ["max_active_strategies", "Max active strategies"],
  ["max_active_markets", "Max active markets"],
  ["max_simultaneous_open_orders", "Max simultaneous open orders"],
  ["max_mutations_per_minute", "Max mutations per minute"],
];

function ActivePolicy({ policy }: { policy: OpsActivePolicy | null }) {
  if (!policy) {
    return (
      <p className="muted">
        No active portfolio policy in the verified lifecycle store. Capacity below is the canonical evaluator result for
        that state.
      </p>
    );
  }
  return (
    <>
      <DetailList
        items={[
          ["Policy", policy.policy_label],
          ["Policy ID", <Token>{policy.policy_id}</Token>],
          ["Predecessor policy", <Token>{policy.predecessor_policy_id ?? "None"}</Token>],
          ["Venue scope", policy.venue_scope.join(", ")],
          ["Account scope ref", <Token>{policy.account_scope_ref}</Token>],
          ["Effective from (ns)", <span className="mono">{policy.effective_from_ns}</span>],
          ["Expires at (ns)", <span className="mono">{policy.expires_at_ns ?? "No expiry"}</span>],
          ["Allowed order styles", policy.allowed_order_styles.join(", ")],
          ["Created (ns)", <span className="mono">{policy.created_time_ns}</span>],
        ]}
      />
      <h3 className="subsection-title">Policy ceilings (limits, not utilization)</h3>
      <dl className="coverage-grid">
        {POLICY_LIMIT_LABELS.map(([key, label]) => (
          <div key={key}>
            <dt>{label}</dt>
            <dd>{policy.limits[key]}</dd>
          </div>
        ))}
      </dl>
    </>
  );
}

function PortfolioAuthorityPanel({ portfolio }: { portfolio: UseQueryResult<OpsPortfolio> }) {
  return (
    <Panel title="Portfolio Authority">
      <Notice>
        <strong>Budget reservations — not actual account exposure.</strong> Orders, fills, PnL and account balances are
        not measured here. Nothing here implies Gate-C eligibility, execution or live authority.
      </Notice>
      <QueryState query={portfolio} label="portfolio authority">
        {(data) => (
          <div className="detail-stack">
            <DetailList
              items={[
                ["Canonical capacity", <CapacityPill status={data.capacity.status} />],
                ["Capacity reasons", <ReasonCodes codes={data.capacity.reason_codes} />],
                ["Backend evaluation time (ns)", <span className="mono">{data.evaluated_at_ns}</span>],
                ["Lifecycle store head", <Token>{data.lifecycle_store_head_entry_hash ?? "Empty store"}</Token>],
              ]}
            />
            <MetricGrid>
              <Metric label="Exploratory reserved (USD)" value={data.capacity.reserved_budget_usd.exploratory} />
              <Metric label="Validated reserved (USD)" value={data.capacity.reserved_budget_usd.validated} />
              <Metric label="Mature reserved (USD)" value={data.capacity.reserved_budget_usd.mature} />
              <Metric label="Total reserved (USD)" value={data.capacity.reserved_budget_usd.total} />
              <Metric label="Strategies holding reservations" value={data.capacity.active_real_risk_strategy_count} />
            </MetricGrid>
            <section className="evidence-section">
              <h3>Active portfolio policy</h3>
              <ActivePolicy policy={data.active_policy} />
            </section>
          </div>
        )}
      </QueryState>
    </Panel>
  );
}

function RecordedGatewayPanel({ status }: { status: UseQueryResult<GatewayStatus> }) {
  return (
    <Panel title="Recorded Runtime / Gateway">
      <Notice>
        <strong>Recorded gateway state — not a fresh account, host or network check.</strong> Persisted gateway evidence;
        not a fresh account, host or network eligibility check.
      </Notice>
      <QueryState query={status} label="recorded gateway state">
        {(data) => (
          <div className="detail-stack">
            <DetailList
              items={[
                ["Recorded gateway state", <StatusPill>{data.authority_state}</StatusPill>],
                ["Recorded disable reason", data.disable_reason ?? "None recorded"],
                ["Recorded gateway access state", <StatusPill>{data.access_state}</StatusPill>],
                ["Recorded reconciliation", data.reconciliation_state],
                ["Recorded heartbeat", data.heartbeat_state],
                ["Recorded user stream", data.user_stream_state],
                ["Recorded open order count", data.open_order_count],
                ["Recorded prepared / mutation attempts", `${data.prepared_order_count} / ${data.mutation_attempt_count}`],
              ]}
            />
            <section className="evidence-section">
              <h3>Recorded restricted-live summary</h3>
              <DetailList
                items={[
                  ["Restricted-live recorded", yesNo(data.restricted_live_available)],
                  ["Recorded armed / halted", `${yesNo(data.restricted_live.armed)} / ${yesNo(data.restricted_live.halted)}`],
                  ["Recorded create attempts", data.restricted_live.create_attempt_count],
                  ["Recorded capital at risk (pUSD)", data.restricted_live.capital_at_risk_pusd],
                  ["Recorded capital committed (pUSD)", data.restricted_live.capital_committed_pusd],
                  ["Recorded restricted-live reconciliation", data.restricted_live.reconciliation_state],
                ]}
              />
            </section>
          </div>
        )}
      </QueryState>
    </Panel>
  );
}

function SimulatedPaperPanel({
  summary,
  risk,
}: {
  summary: UseQueryResult<PaperSummary>;
  risk: UseQueryResult<PaperRisk>;
}) {
  return (
    <Panel title="Simulated Paper Risk">
      <Notice>
        <strong>SIMULATED PAPER ONLY.</strong> Paper cash and PnL are never combined with portfolio budget reservations or
        recorded gateway state. Detailed orders, fills and positions stay on Paper Operations.
      </Notice>
      <QueryState query={summary} label="simulated paper summary">
        {(data) => (
          <MetricGrid>
            <Metric label="Paper control" value={data.control_state} />
            <Metric label="Paper reconciliation" value={data.reconciliation_state} />
            <Metric label="Paper free cash" value={data.free_cash} />
            <Metric label="Paper equity" value={data.equity ?? "Unavailable"} />
            <Metric label="Paper realized PnL" value={data.realized_pnl} />
            <Metric label="Paper unrealized PnL" value={data.unrealized_pnl ?? "Unavailable"} />
          </MetricGrid>
        )}
      </QueryState>
      <QueryState query={risk} label="simulated paper risk">
        {(data) => (
          <DetailList
            items={[
              ["Paper open orders", `${data.utilization.open_orders} / ${data.utilization.max_open_orders}`],
              ["Paper reserved cash", data.utilization.reserved_cash],
              ["Paper risk denials", data.deny_count],
              ["Latest paper risk decision", data.latest_decision?.result ?? "None"],
              ["Paper resolution pending", data.resolution_pending.join(", ") || "None"],
            ]}
          />
        )}
      </QueryState>
    </Panel>
  );
}

function ReservationWindow({ item }: { item: OpsStrategyReservation }) {
  return (
    <>
      <span className="mono">
        {item.valid_from_ns} → {item.valid_until_ns ?? "open"}
      </span>
      <br />
      <StatusPill tone={item.active_at_evaluation ? "neutral" : "warning"}>
        {item.active_at_evaluation ? "Inside window at evaluation" : "Outside window at evaluation"}
      </StatusPill>
    </>
  );
}

function StrategyReservationsPanel({ portfolio }: { portfolio: UseQueryResult<OpsPortfolio> }) {
  return (
    <Panel title="Strategy Reservations">
      <p className="muted">
        A reservation window only says whether the allocation window covers the backend evaluation time. It is not
        policy, capacity, Gate-C or live eligibility.
      </p>
      <QueryState
        query={portfolio}
        label="strategy reservations"
        isEmpty={(data) => data.strategy_reservations.length === 0}
      >
        {(data) => (
          <DataTable
            label="Strategy reservations"
            headers={["Strategy", "Reserved budget", "Window", "Health", "Canonical capacity", "Active restrictions"]}
          >
            {data.strategy_reservations.map((item) => (
              <tr key={item.allocation_id}>
                <td>
                  {item.strategy_label}
                  <br />
                  <Token>{item.strategy_version_id}</Token>
                </td>
                <td>
                  {item.risk_band} · {item.active_budget_usd} USD
                  <br />
                  <span className="muted">{item.allocation_basis}</span>
                </td>
                <td>
                  <ReservationWindow item={item} />
                </td>
                <td>
                  <StatusPill>{item.health_state ?? "Unknown"}</StatusPill>
                </td>
                <td>
                  {item.capacity_status ? (
                    <>
                      <CapacityPill status={item.capacity_status} />
                      <br />
                      <ReasonCodes codes={item.capacity_reason_codes} />
                    </>
                  ) : (
                    <span className="muted">No per-strategy result from the canonical evaluator</span>
                  )}
                </td>
                <td>
                  {item.active_restrictions.length === 0 ? (
                    <span className="muted">None</span>
                  ) : (
                    <ul className="ref-list">
                      {item.active_restrictions.map((restriction) => (
                        <li key={restriction.restriction_receipt_id}>
                          <StatusPill tone="warning">{restriction.restriction_kind}</StatusPill>{" "}
                          <Token>{restriction.restriction_key}</Token>
                          {restriction.max_active_budget_usd !== null && (
                            <> · cap {restriction.max_active_budget_usd} USD</>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </td>
              </tr>
            ))}
          </DataTable>
        )}
      </QueryState>
    </Panel>
  );
}

function RecordedGatewayEventsPanel({ audit }: { audit: UseQueryResult<ListResponse<GatewayAuditItem>> }) {
  return (
    <Panel title="Recent Recorded Gateway Events">
      <p className="muted">Persisted gateway audit metadata in recorded sequence order.</p>
      <QueryState query={audit} label="recorded gateway events" isEmpty={isEmptyList}>
        {(data) => (
          <DataTable
            label="Recent recorded gateway events"
            headers={["Sequence", "Event type", "Event time (ns)", "Event ID", "Event hash"]}
          >
            {data.items.map((item) => (
              <tr key={item.event_id}>
                <td className="num">{item.sequence}</td>
                <td>{item.event_type}</td>
                <td className="mono">{item.event_time_ns}</td>
                <td>
                  <Token>{item.event_id}</Token>
                </td>
                <td>
                  <Token>{item.event_hash}</Token>
                </td>
              </tr>
            ))}
          </DataTable>
        )}
      </QueryState>
    </Panel>
  );
}

function OpsView() {
  const portfolio = useQuery(opsPortfolioQuery);
  const gatewayStatus = useQuery(opsGatewayStatusQuery);
  const gatewayAudit = useQuery(opsGatewayAuditQuery);
  const paperSummary = useQuery(opsPaperSummaryQuery);
  const paperRisk = useQuery(opsPaperRiskQuery);
  return (
    <>
      <Notice>
        <strong>Separate sources, separate meanings.</strong> Portfolio policy and budget reservations, simulated paper
        state and recorded gateway state are shown side by side, never combined. None of them is current authenticated
        account risk, host or network eligibility, Gate-C eligibility or execution / live authority.
      </Notice>
      <div className="ops-grid">
        <PortfolioAuthorityPanel portfolio={portfolio} />
        <RecordedGatewayPanel status={gatewayStatus} />
        <SimulatedPaperPanel summary={paperSummary} risk={paperRisk} />
      </div>
      <StrategyReservationsPanel portfolio={portfolio} />
      <RecordedGatewayEventsPanel audit={gatewayAudit} />
    </>
  );
}

// ---------------------------------------------------------------------------
// Shell and routes
// ---------------------------------------------------------------------------

type ViewDefinition = { path: string; label: string; family: QueryFamily; element: ReactNode };

export const VIEWS: readonly ViewDefinition[] = [
  { path: "/overview", label: "Overview", family: "overview", element: <OverviewView /> },
  { path: "/markets", label: "Market Truth", family: "market", element: <MarketView /> },
  { path: "/experiments", label: "Experiments", family: "experiments", element: <ExperimentsView /> },
  { path: "/strategies", label: "Strategies", family: "strategies", element: <StrategiesView /> },
  { path: "/hermes", label: "Hermes", family: "hermes", element: <HermesView /> },
  { path: "/alpha", label: "Alpha Research", family: "alpha", element: <AlphaView /> },
  { path: "/ops", label: "Operations", family: "ops", element: <OpsView /> },
  { path: "/paper", label: "Paper Operations", family: "paper", element: <PaperView /> },
  { path: "/audit", label: "Audit / Health", family: "audit", element: <AuditView /> },
];

function RefreshControl({ family }: { family: QueryFamily }) {
  const queryClient = useQueryClient();
  const fetching = useIsFetching({ queryKey: familyKey(family) }) > 0;
  // Invalidate only the active route family; inactive pages keep their cached evidence.
  const refresh = () => void queryClient.invalidateQueries({ queryKey: familyKey(family) });
  return (
    <Button variant="primary" onClick={refresh} busy={fetching} disabled={fetching}>
      {fetching ? "Refreshing…" : "Refresh"}
    </Button>
  );
}

// S10-CC-STREAM-01: the single centralized auto-refresh transport. It owns the only browser stream,
// opens it only when the backend reports streaming enabled, and only ever invalidates the active
// family so the existing HTTP snapshots are re-read. It never writes query data, never retries on
// its own (native browser reconnect only) and never asserts domain freshness.
type TransportState = "Disabled" | "Connecting" | "Connected" | "Resyncing" | "Disconnected";
const TRANSPORT_TONE: Record<TransportState, Tone> = {
  Disabled: "neutral",
  Connecting: "neutral",
  Connected: "success",
  Resyncing: "warning",
  Disconnected: "warning",
};
export const STREAM_NOTICE =
  "Auto-refresh updates this workspace from the existing authoritative HTTP snapshots. Stream connection state is transport status, not domain freshness or trading readiness.";

// Integer nanoseconds -> UTC timestamp via BigInt; the server signal time is never coerced to an
// unsafe JavaScript number and the browser clock is never consulted.
const signalTimeUtc = (serverTimeNs: string) => new Date(Number(BigInt(serverTimeNs) / 1_000_000n)).toISOString();

function StreamRefreshController({ family }: { family: QueryFamily }) {
  const queryClient = useQueryClient();
  const status = useQuery(streamStatusQuery);
  const enabled = status.data?.enabled === true;
  const [transport, setTransport] = useState<{ state: TransportState; signalNs: string | null }>({
    state: "Disabled",
    signalNs: null,
  });

  useEffect(() => {
    if (!enabled) return;
    let open = true;
    let baseline: StreamBaseline | null = null;
    const source = new EventSource(streamEventUrl(family));
    setTransport({ state: "Connecting", signalNs: null });
    const reread = (resync: boolean) => {
      // Never abort an in-flight re-read: a projection slower than the cadence must still land.
      const settled = queryClient.invalidateQueries({ queryKey: familyKey(family) }, { cancelRefetch: false });
      if (!resync) return void settled;
      void settled.finally(() => {
        if (open) setTransport((current) => (current.state === "Resyncing" ? { ...current, state: "Connected" } : current));
      });
    };
    const listeners = (Object.keys(STREAM_EVENT_NAMES) as StreamEventName[]).map((name) => {
      const listener = (message: MessageEvent) => {
        const event = parseStreamEvent(name, message.data, family);
        if (event === null) {
          // Malformed transport input is dropped; the next valid event takes the resync path.
          baseline = null;
          return;
        }
        const step = advanceStreamBaseline(baseline, event);
        baseline = step.baseline;
        setTransport({ state: step.resync ? "Resyncing" : "Connected", signalNs: event.server_time_ns });
        if (step.invalidate) reread(step.resync);
      };
      source.addEventListener(name, listener);
      return [name, listener] as const;
    });
    // Native reconnect only. A reconnect is a new server connection whose first event resyncs.
    source.onerror = () => {
      baseline = null;
      setTransport((current) => ({ ...current, state: "Disconnected" }));
    };
    return () => {
      open = false;
      for (const [name, listener] of listeners) source.removeEventListener(name, listener);
      source.onerror = null;
      source.close();
    };
  }, [enabled, family, queryClient]);

  const state: TransportState = enabled ? transport.state : "Disabled";
  return (
    <div className="stream-indicator">
      {/* Only the state is a live region; the signal time changes every tick and is not announced. */}
      <span role="status">
        <StatusPill tone={TRANSPORT_TONE[state]}>Auto-refresh: {state}</StatusPill>
      </span>
      {enabled && transport.signalNs !== null && (
        <span className="stream-signal">
          Server refresh-signal time <code>{signalTimeUtc(transport.signalNs)}</code>
        </span>
      )}
    </div>
  );
}

export function ControlCenter() {
  const { pathname } = useLocation();
  const active = VIEWS.find((view) => view.path === pathname) ?? VIEWS[0];
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">Control Center</div>
        <nav aria-label="Control Center views">
          {VIEWS.map((view) => (
            <NavItem key={view.path} to={view.path}>
              {view.label}
            </NavItem>
          ))}
        </nav>
        <div className="posture" aria-label="Authority posture">
          <strong>READ ONLY CONTROL CENTER</strong>
          <span>Simulated paper only</span>
          <span>Hermes: soft judgments only</span>
          <span>Alpha: research records only</span>
          <span>Ops: reservations + recorded state only</span>
          <span>No execution or live authority</span>
        </div>
      </aside>
      <main className="main">
        <header className="page-header">
          <div>
            <div className="eyebrow">Validated cockpit evidence · WP171 / WP173</div>
            <h1>{active.label}</h1>
          </div>
          <div className="page-actions">
            <StreamRefreshController family={active.family} />
            <RefreshControl family={active.family} />
          </div>
        </header>
        <p className="stream-notice">{STREAM_NOTICE}</p>
        <Routes>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          {VIEWS.map((view) => (
            <Route key={view.path} path={view.path} element={view.element} />
          ))}
          <Route path="*" element={<Navigate to="/overview" replace />} />
        </Routes>
      </main>
    </div>
  );
}
