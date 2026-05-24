import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, PieChart, Pie, Cell, Legend,
} from "recharts";
import { ArrowLeft, AlertCircle } from "lucide-react";
import { api } from "../lib/api.js";
import { fmtPct, fmtNum, fmtMoney, fmtCount } from "../lib/utils.js";
import PageHeader from "../components/PageHeader.jsx";
import MetricCard from "../components/MetricCard.jsx";
import { PageLoader, ErrorState } from "../components/LoadingState.jsx";
import RankBadge from "../components/RankBadge.jsx";

const TOOLTIP_STYLE = {
  contentStyle: { background: "#161b27", border: "1px solid #1f2937", borderRadius: 8 },
  labelStyle: { color: "#9ca3af" },
};

const ALERT_LEVEL_COLORS = {
  critical: "#ef4444",
  high: "#f59e0b",
  medium: "#6366f1",
  low: "#22c55e",
};

export default function UniverseDetail() {
  const { id } = useParams();

  const { data: universe, isLoading: uLoading, error: uError } = useQuery({
    queryKey: ["universe", id],
    queryFn: () => api.universe(id),
  });

  const { data: alerts = [], isLoading: aLoading } = useQuery({
    queryKey: ["alerts", id],
    queryFn: () => api.alerts(id, 200),
  });

  if (uLoading) return <PageLoader message="Loading universe detail…" />;
  if (uError) return <ErrorState error={uError} />;

  const m = universe.metrics || {};

  const confusionData = [
    { label: "True Positives", value: m.true_positives, fill: "#22c55e" },
    { label: "False Positives", value: m.false_positives, fill: "#f59e0b" },
    { label: "False Negatives", value: m.false_negatives, fill: "#ef4444" },
    { label: "True Negatives", value: m.true_negatives, fill: "#6366f1" },
  ];

  // Alert level distribution
  const alertLevelCounts = alerts.reduce((acc, a) => {
    acc[a.alert_level] = (acc[a.alert_level] || 0) + 1;
    return acc;
  }, {});
  const alertLevelData = Object.entries(alertLevelCounts).map(([level, count]) => ({
    name: level,
    value: count,
    fill: ALERT_LEVEL_COLORS[level] || "#6366f1",
  }));

  // Top 10 alerts by score
  const topAlerts = [...alerts]
    .sort((a, b) => (b.alert_score || 0) - (a.alert_score || 0))
    .slice(0, 10);

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title={universe.name}
        subtitle={`Rank #${universe.rank} · ${universe.n_rules} rules · threshold ${universe.alert_threshold}`}
      >
        <Link to="/universes" className="btn-ghost text-sm">
          <ArrowLeft size={14} />
          Back
        </Link>
        <RankBadge rank={universe.rank} />
      </PageHeader>

      <div className="p-8 space-y-8">
        {/* KPI row */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <MetricCard label="F1 Score" value={fmtNum(m.f1)} />
          <MetricCard label="Recall" value={fmtPct(m.recall)} />
          <MetricCard label="Precision" value={fmtPct(m.precision)} />
          <MetricCard label="AUC-ROC" value={fmtNum(m.auc_roc)} />
          <MetricCard label="Total Cost" value={fmtMoney(m.total_cost)} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Confusion matrix bars */}
          <div className="card">
            <h3 className="text-sm font-semibold text-white mb-4">Confusion Matrix</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={confusionData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
                <XAxis type="number" tick={{ fill: "#6b7280", fontSize: 11 }} />
                <YAxis type="category" dataKey="label" width={120} tick={{ fill: "#9ca3af", fontSize: 11 }} />
                <Tooltip {...TOOLTIP_STYLE} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {confusionData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Alert level pie */}
          <div className="card">
            <h3 className="text-sm font-semibold text-white mb-4">
              Alert Distribution by Level
              {aLoading && <span className="ml-2 text-xs text-gray-500">loading…</span>}
            </h3>
            {alertLevelData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={alertLevelData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={90}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {alertLevelData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip {...TOOLTIP_STYLE} />
                  <Legend
                    wrapperStyle={{ fontSize: 12, color: "#9ca3af" }}
                    formatter={(value) => value.charAt(0).toUpperCase() + value.slice(1)}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-36 text-gray-600 text-sm">
                No alerts generated
              </div>
            )}
          </div>
        </div>

        {/* Cost breakdown */}
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-4">Cost Model Breakdown</h3>
          <div className="grid grid-cols-3 gap-6">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">Investigation Cost</p>
              <p className="text-lg font-mono font-semibold text-amber-400 mt-1">
                {fmtMoney(m.investigation_cost)}
              </p>
              <p className="text-xs text-gray-600 mt-0.5">
                {fmtCount(m.true_positives + m.false_positives)} alerts × $150
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">Missed Laundering</p>
              <p className="text-lg font-mono font-semibold text-red-400 mt-1">
                {fmtMoney(m.missed_laundering_cost)}
              </p>
              <p className="text-xs text-gray-600 mt-0.5">
                {fmtCount(m.false_negatives)} missed × $50,000
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">Total Cost</p>
              <p className="text-lg font-mono font-semibold text-white mt-1">
                {fmtMoney(m.total_cost)}
              </p>
              <p className="text-xs text-gray-600 mt-0.5">per simulation period</p>
            </div>
          </div>
        </div>

        {/* Top alerts table */}
        <div className="card p-0 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-border flex items-center gap-2">
            <AlertCircle size={14} className="text-amber-400" />
            <h3 className="text-sm font-semibold text-white">
              Top Alerts by Score (sample of 200)
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-surface-border">
                  {["TX ID", "From", "To", "Amount", "Score", "Level", "Illicit", "Typology"].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-4 py-3 text-left font-semibold text-gray-500 uppercase tracking-wider"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {topAlerts.map((alert, i) => (
                  <tr key={i} className="hover:bg-surface-hover transition-colors">
                    <td className="px-4 py-2.5 font-mono text-gray-400">{alert.tx_id}</td>
                    <td className="px-4 py-2.5 font-mono text-gray-300 truncate max-w-[100px]">
                      {alert.from_account}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-gray-300 truncate max-w-[100px]">
                      {alert.to_account}
                    </td>
                    <td className="px-4 py-2.5 font-mono">${Number(alert.amount || 0).toLocaleString()}</td>
                    <td className="px-4 py-2.5 font-mono text-brand-400 font-medium">
                      {fmtNum(alert.alert_score)}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className="badge"
                        style={{
                          background: `${ALERT_LEVEL_COLORS[alert.alert_level] || "#6366f1"}15`,
                          color: ALERT_LEVEL_COLORS[alert.alert_level] || "#6366f1",
                        }}
                      >
                        {alert.alert_level}
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      {alert.is_illicit ? (
                        <span className="badge bg-red-500/10 text-red-400">Yes</span>
                      ) : (
                        <span className="badge bg-green-500/10 text-green-400">No</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-gray-500 font-mono">
                      {alert.illicit_typology || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {topAlerts.length === 0 && (
              <div className="text-center py-8 text-gray-600 text-sm">No alerts found</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
