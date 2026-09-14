import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

const API = "http://127.0.0.1:8000/api";
const VIEWS = ["Overview", "Market Truth", "Experiments", "Paper Operations", "Audit / Health"] as const;
type View = (typeof VIEWS)[number];
type LoadState<T> =
  | { kind: "loading" }
  | { kind: "error"; code: string }
  | { kind: "ready"; data: T };
type ListResponse<T> = { items: T[]; count: number; limit: number };

type Health = {
  status: "OK" | "DEGRADED";
  read_only: true;
  wp169: { configured: boolean; readable: boolean };
  wp170: { configured: boolean; readable: boolean };
  paper: { configured: boolean; readable: boolean };
};
type Overview = {
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
type MarketItem = {
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
type Experiment = {
  experiment_id: string;
  experiment_family_id: string;
  trial_number: number;
  hypothesis_id: string;
  preregistered_at: string;
  lifecycle_state: string | null;
  result_status: string | null;
  oos_exposure_ordinal: number | null;
};
type ExperimentDetail = Experiment & {
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
type AuditItem = {
  source: "WP169" | "WP170";
  record_id: string | null;
  experiment_id: string | null;
  kind: string;
  sequence: number;
  status: string;
  occurred_at: string;
};
type PaperSummary = {
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
type PaperOrder = {
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
type PaperFill = {
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
type PaperPosition = {
  market_id: string;
  asset_id: string;
  quantity: string;
  cost_basis: string;
  realized_pnl: string;
  mark: string | null;
  marked_value: string | null;
};
type PaperRisk = {
  limits: { max_open_orders: number };
  utilization: { open_orders: number; max_open_orders: number; reserved_cash: string };
  deny_count: number;
  resolution_pending: string[];
  latest_decision: { result: string; reason_codes: string[] } | null;
};

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(API + path, { method: "GET" });
  const body: unknown = await response.json();
  if (!response.ok) {
    const code = typeof body === "object" && body !== null && "error" in body
      ? (body as { error?: { code?: string } }).error?.code
      : undefined;
    throw new Error(code || "INTERNAL_ERROR");
  }
  return body as T;
}

function StatePanel<T>({
  state,
  empty,
  children,
}: {
  state: LoadState<T>;
  empty?: (value: T) => boolean;
  children: (value: T) => React.ReactNode;
}) {
  if (state.kind === "loading") return <div className="panel state">Loading validated local evidence…</div>;
  if (state.kind === "error") {
    return <div className="panel state error">Source unavailable. Safe code: {state.code}</div>;
  }
  if (empty?.(state.data)) return <div className="panel state">No evidence is available in this view.</div>;
  return <>{children(state.data)}</>;
}

function OverviewView({ epoch }: { epoch: number }) {
  const [state, setState] = useState<LoadState<Overview>>({ kind: "loading" });
  useEffect(() => {
    setState({ kind: "loading" });
    getJson<Overview>("/overview")
      .then((data) => setState({ kind: "ready", data }))
      .catch((error: Error) => setState({ kind: "error", code: error.message }));
  }, [epoch]);
  return (
    <StatePanel state={state}>
      {(data) => (
        <>
          <div className="grid">
            <Metric label="Normalized observations" value={data.market_truth.normalized_count} />
            <Metric label="Accepted observations" value={data.market_truth.accepted_count} />
            <Metric label="Open gap events" value={data.market_truth.open_gap_count} />
            <Metric label="Experiments" value={data.experiments.experiment_count} />
            <Metric label="Lifecycle receipts" value={data.experiments.lifecycle_count} />
            <Metric label="Evidence receipts" value={data.experiments.evidence_count} />
          </div>
          <div className="panel">
            <span className="eyebrow">Freshness</span>
            <p>{data.market_truth.latest_received_at || "No market timestamp available"}</p>
            <span className="pill">Read only</span>
          </div>
        </>
      )}
    </StatePanel>
  );
}

function MarketView({ epoch }: { epoch: number }) {
  const [state, setState] = useState<LoadState<ListResponse<MarketItem>>>({ kind: "loading" });
  useEffect(() => {
    setState({ kind: "loading" });
    getJson<ListResponse<MarketItem>>("/market-truth/recent")
      .then((data) => setState({ kind: "ready", data }))
      .catch((error: Error) => setState({ kind: "error", code: error.message }));
  }, [epoch]);
  return (
    <StatePanel state={state} empty={(data) => data.count === 0}>
      {(data) => (
        <div className="panel">
          <table><thead><tr><th>Received</th><th>Source</th><th>Event</th><th>Market / Asset</th><th>Status</th></tr></thead>
            <tbody>{data.items.map((item) => <tr key={item.observation_id}>
              <td>{item.received_at}</td><td>{item.source_kind}</td><td>{item.event_kind}</td>
              <td className="token">{item.market_id || "—"}<br />{item.asset_id || "—"}</td>
              <td><span className={"pill " + (item.status === "ACCEPTED" ? "" : "warn")}>{item.status}</span></td>
            </tr>)}</tbody>
          </table>
        </div>
      )}
    </StatePanel>
  );
}

function ExperimentsView({ epoch }: { epoch: number }) {
  const [state, setState] = useState<LoadState<ListResponse<Experiment>>>({ kind: "loading" });
  const [detail, setDetail] = useState<LoadState<ExperimentDetail> | null>(null);
  useEffect(() => {
    setState({ kind: "loading" });
    setDetail(null);
    getJson<ListResponse<Experiment>>("/experiments")
      .then((data) => setState({ kind: "ready", data }))
      .catch((error: Error) => setState({ kind: "error", code: error.message }));
  }, [epoch]);
  const openDetail = (id: string) => {
    setDetail({ kind: "loading" });
    getJson<{ item: ExperimentDetail }>("/experiments/" + encodeURIComponent(id))
      .then(({ item }) => setDetail({ kind: "ready", data: item }))
      .catch((error: Error) => setDetail({ kind: "error", code: error.message }));
  };
  return (
    <>
      <StatePanel state={state} empty={(data) => data.count === 0}>
        {(data) => <div className="panel"><table><thead><tr><th>Experiment</th><th>Trial</th><th>Lifecycle</th><th>Evidence result</th><th>OOS use</th></tr></thead>
          <tbody>{data.items.map((item) => <tr key={item.experiment_id}>
            <td className="token"><button className="link" onClick={() => openDetail(item.experiment_id)}>{item.experiment_id}</button></td>
            <td>{item.trial_number}</td><td>{item.lifecycle_state || "Not started"}</td>
            <td><span className="pill">{item.result_status || "No evidence"}</span></td>
            <td>{item.oos_exposure_ordinal == null ? "—" : item.oos_exposure_ordinal === 1 ? "First look" : "Reused / diagnostic"}</td>
          </tr>)}</tbody>
        </table></div>}
      </StatePanel>
      {detail && <StatePanel state={detail}>{(item) => <div className="panel">
        <span className="eyebrow">Experiment detail · evidence status only</span>
        <div className="detail">
          {Object.entries(item).map(([key, value]) => <div key={key}><strong>{key}</strong><br /><span className="token">{Array.isArray(value) ? value.join(", ") || "—" : String(value ?? "—")}</span></div>)}
        </div>
      </div>}</StatePanel>}
    </>
  );
}

function AuditView({ epoch }: { epoch: number }) {
  const [audit, setAudit] = useState<LoadState<ListResponse<AuditItem>>>({ kind: "loading" });
  const [health, setHealth] = useState<LoadState<Health>>({ kind: "loading" });
  useEffect(() => {
    setAudit({ kind: "loading" }); setHealth({ kind: "loading" });
    getJson<ListResponse<AuditItem>>("/audit/recent").then((data) => setAudit({ kind: "ready", data })).catch((error: Error) => setAudit({ kind: "error", code: error.message }));
    getJson<Health>("/health").then((data) => setHealth({ kind: "ready", data })).catch((error: Error) => setHealth({ kind: "error", code: error.message }));
  }, [epoch]);
  return <>
    <StatePanel state={health}>{(data) => <div className="grid">
      <Metric label="Overall health" value={data.status} />
      <Metric label="WP169 readable" value={data.wp169.readable ? "Yes" : "No"} />
      <Metric label="WP170 readable" value={data.wp170.readable ? "Yes" : "No"} />
      <Metric label="Paper store readable" value={data.paper.readable ? "Yes" : "No"} />
    </div>}</StatePanel>
    <StatePanel state={audit} empty={(data) => data.count === 0}>{(data) => <div className="panel">
      <table><thead><tr><th>Time</th><th>Source</th><th>Kind</th><th>Status</th><th>Evidence ID</th></tr></thead>
        <tbody>{data.items.map((item, index) => <tr key={(item.record_id || item.source) + index}>
          <td>{item.occurred_at}</td><td>{item.source}</td><td>{item.kind}</td><td><span className="pill">{item.status}</span></td><td className="token">{item.record_id || "—"}</td>
        </tr>)}</tbody>
      </table>
    </div>}</StatePanel>
  </>;
}

function PaperView({ epoch }: { epoch: number }) {
  const [summary, setSummary] = useState<LoadState<PaperSummary>>({ kind: "loading" });
  const [orders, setOrders] = useState<LoadState<ListResponse<PaperOrder>>>({ kind: "loading" });
  const [fills, setFills] = useState<LoadState<ListResponse<PaperFill>>>({ kind: "loading" });
  const [positions, setPositions] = useState<LoadState<ListResponse<PaperPosition>>>({ kind: "loading" });
  const [risk, setRisk] = useState<LoadState<PaperRisk>>({ kind: "loading" });
  useEffect(() => {
    setSummary({ kind: "loading" }); setOrders({ kind: "loading" });
    setFills({ kind: "loading" }); setPositions({ kind: "loading" }); setRisk({ kind: "loading" });
    getJson<PaperSummary>("/paper/summary").then((data) => setSummary({ kind: "ready", data })).catch((error: Error) => setSummary({ kind: "error", code: error.message }));
    getJson<ListResponse<PaperOrder>>("/paper/orders").then((data) => setOrders({ kind: "ready", data })).catch((error: Error) => setOrders({ kind: "error", code: error.message }));
    getJson<ListResponse<PaperFill>>("/paper/fills").then((data) => setFills({ kind: "ready", data })).catch((error: Error) => setFills({ kind: "error", code: error.message }));
    getJson<ListResponse<PaperPosition>>("/paper/positions").then((data) => setPositions({ kind: "ready", data })).catch((error: Error) => setPositions({ kind: "error", code: error.message }));
    getJson<PaperRisk>("/paper/risk").then((data) => setRisk({ kind: "ready", data })).catch((error: Error) => setRisk({ kind: "error", code: error.message }));
  }, [epoch]);
  return <>
    <StatePanel state={summary}>{(data) => <><div className="grid">
      <Metric label="Paper control" value={data.control_state} />
      <Metric label="Reconciliation" value={data.reconciliation_state} />
      <Metric label="Free cash" value={data.free_cash} />
      <Metric label="Equity" value={data.equity ?? "Unavailable"} />
      <Metric label="Realized PnL" value={data.realized_pnl} />
      <Metric label="Unrealized PnL" value={data.unrealized_pnl ?? "Unavailable"} />
    </div><div className="panel"><span className="eyebrow">Market-data freshness</span><p>{data.last_market_receive_ns ?? "No valid paper mark"}</p><span className="pill">Simulated paper only</span></div></>}</StatePanel>
    <StatePanel state={risk}>{(data) => <div className="panel"><span className="eyebrow">Hard paper risk</span><p>Open orders {data.utilization.open_orders} / {data.utilization.max_open_orders} · Reserved cash {data.utilization.reserved_cash} · Denials {data.deny_count}</p><p>Latest decision: {data.latest_decision?.result ?? "None"} · Blocks: {data.latest_decision?.reason_codes.join(", ") || "None"}</p><p>Resolution pending: {data.resolution_pending.join(", ") || "None"}</p></div>}</StatePanel>
    <StatePanel state={orders} empty={(data) => data.count === 0}>{(data) => <div className="panel"><span className="eyebrow">Paper orders</span><table><thead><tr><th>Order</th><th>Side / Style</th><th>Quantity</th><th>Filled / Average</th><th>Status</th></tr></thead><tbody>{data.items.map((item) => <tr key={item.order_id}><td className="token">{item.order_id}</td><td>{item.side}<br />{item.order_style}</td><td>{item.quantity}</td><td>{item.filled_quantity}<br />{item.average_fill_price ?? "—"}</td><td><span className="pill">{item.status}</span></td></tr>)}</tbody></table></div>}</StatePanel>
    <StatePanel state={positions} empty={(data) => data.count === 0}>{(data) => <div className="panel"><span className="eyebrow">Paper positions</span><table><thead><tr><th>Asset</th><th>Quantity</th><th>Cost basis</th><th>Mark / Value</th><th>Realized PnL</th></tr></thead><tbody>{data.items.map((item) => <tr key={item.asset_id}><td className="token">{item.asset_id}</td><td>{item.quantity}</td><td>{item.cost_basis}</td><td>{item.mark ?? "Unavailable"}<br />{item.marked_value ?? "Unavailable"}</td><td>{item.realized_pnl}</td></tr>)}</tbody></table></div>}</StatePanel>
    <StatePanel state={fills} empty={(data) => data.count === 0}>{(data) => <div className="panel"><span className="eyebrow">Recent simulated fills</span><table><thead><tr><th>Fill</th><th>Side</th><th>Quantity</th><th>Price / Fee</th><th>Costs / Markout</th></tr></thead><tbody>{data.items.map((item) => <tr key={item.fill_id}><td className="token">{item.fill_id}</td><td>{item.side}</td><td>{item.quantity}</td><td>{item.price}<br />{item.fee}</td><td>{item.spread_cost} / {item.depth_slippage_cost} / {item.latency_cost}<br />{item.adverse_selection_cost ?? item.markout_status}</td></tr>)}</tbody></table></div>}</StatePanel>
  </>;
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="card"><span>{label}</span><strong>{value}</strong></div>;
}

function App() {
  const [view, setView] = useState<View>("Overview");
  const [epoch, setEpoch] = useState(0);
  const content = view === "Overview" ? <OverviewView epoch={epoch} /> :
    view === "Market Truth" ? <MarketView epoch={epoch} /> :
    view === "Experiments" ? <ExperimentsView epoch={epoch} /> :
    view === "Paper Operations" ? <PaperView epoch={epoch} /> : <AuditView epoch={epoch} />;
  return <div className="shell">
    <aside><div className="brand">Evidence Cockpit</div><nav>
      {VIEWS.map((name) => <button key={name} className={name === view ? "active" : ""} onClick={() => setView(name)}>{name}</button>)}
    </nav><div className="posture">LOCAL · READ ONLY COCKPIT<br />Simulated paper only<br />No real execution or live authority</div></aside>
    <main><header><div><div className="eyebrow">WP171/WP173 · validated local evidence</div><h1>{view}</h1></div><button className="refresh" onClick={() => setEpoch((value) => value + 1)}>Refresh</button></header>{content}</main>
  </div>;
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
