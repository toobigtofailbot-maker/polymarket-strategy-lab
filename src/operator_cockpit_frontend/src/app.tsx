import { useState, type ReactNode } from "react";
import { useIsFetching, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { Navigate, NavLink, Route, Routes, useLocation } from "react-router";
import {
  auditRecentQuery,
  experimentDetailQuery,
  experimentsQuery,
  familyKey,
  healthQuery,
  hermesAssessmentDetailQuery,
  hermesAssessmentsQuery,
  marketRecentQuery,
  overviewQuery,
  paperFillsQuery,
  paperOrdersQuery,
  paperPositionsQuery,
  paperRiskQuery,
  paperSummaryQuery,
  strategiesQuery,
  strategyDetailQuery,
  toSafeErrorCode,
  type ContextStatus,
  type HermesNonAuthority,
  type JsonValue,
  type LatestHermesAssessment,
  type LifecycleAllocation,
  type ListResponse,
  type QueryFamily,
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
// Shell and routes
// ---------------------------------------------------------------------------

type ViewDefinition = { path: string; label: string; family: QueryFamily; element: ReactNode };

export const VIEWS: readonly ViewDefinition[] = [
  { path: "/overview", label: "Overview", family: "overview", element: <OverviewView /> },
  { path: "/markets", label: "Market Truth", family: "market", element: <MarketView /> },
  { path: "/experiments", label: "Experiments", family: "experiments", element: <ExperimentsView /> },
  { path: "/strategies", label: "Strategies", family: "strategies", element: <StrategiesView /> },
  { path: "/hermes", label: "Hermes", family: "hermes", element: <HermesView /> },
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
          <span>No execution or live authority</span>
        </div>
      </aside>
      <main className="main">
        <header className="page-header">
          <div>
            <div className="eyebrow">Validated cockpit evidence · WP171 / WP173</div>
            <h1>{active.label}</h1>
          </div>
          <RefreshControl family={active.family} />
        </header>
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
