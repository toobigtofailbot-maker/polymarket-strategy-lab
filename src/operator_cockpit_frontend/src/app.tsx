import { useState, type ReactNode } from "react";
import { useIsFetching, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { Navigate, NavLink, Route, Routes, useLocation } from "react-router";
import {
  auditRecentQuery,
  experimentDetailQuery,
  experimentsQuery,
  familyKey,
  healthQuery,
  marketRecentQuery,
  overviewQuery,
  paperFillsQuery,
  paperOrdersQuery,
  paperPositionsQuery,
  paperRiskQuery,
  paperSummaryQuery,
  toSafeErrorCode,
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
// Shell and routes
// ---------------------------------------------------------------------------

type ViewDefinition = { path: string; label: string; family: QueryFamily; element: ReactNode };

export const VIEWS: readonly ViewDefinition[] = [
  { path: "/overview", label: "Overview", family: "overview", element: <OverviewView /> },
  { path: "/markets", label: "Market Truth", family: "market", element: <MarketView /> },
  { path: "/experiments", label: "Experiments", family: "experiments", element: <ExperimentsView /> },
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
