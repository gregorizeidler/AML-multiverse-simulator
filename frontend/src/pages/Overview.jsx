import { useQuery } from "@tanstack/react-query";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend, Cell,
} from "recharts";
import { ShieldCheck, AlertTriangle, Activity, DollarSign, Globe2 } from "lucide-react";
import { api } from "../lib/api.js";
import { fmtPct, fmtNum, fmtMoney, fmtCount, UNIVERSE_COLORS } from "../lib/utils.js";
import PageHeader from "../components/PageHeader.jsx";
import MetricCard from "../components/MetricCard.jsx";
import { PageLoader, ErrorState } from "../components/LoadingState.jsx";
import RankBadge from "../components/RankBadge.jsx";

const TOOLTIP_STYLE = {
  contentStyle: { background: "#161b27", border: "1px solid #1f2937", borderRadius: 8 },
  labelStyle: { color: "#9ca3af" },
};

export default function Overview() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["summary"],
    queryFn: api.summary,
  });

  if (isLoading) return <PageLoader message="Loading simulation summary…" />;
  if (error) return <ErrorState error={error} />;

  const { dataset, universes = [], best_universe_id } = data;
  const best = universes.find((u) => u.universe_id === best_universe_id) || universes[0];

  const radarData = best
    ? [
        { metric: "Recall", value: (best.metrics?.recall || 0) * 100 },
        { metric: "Precision", value: (best.metrics?.precision || 0) * 100 },
        { metric: "F1", value: (best.metrics?.f1 || 0) * 100 },
        { metric: "AUC-ROC", value: (best.metrics?.auc_roc || 0) * 100 },
        { metric: "Low FPR", value: (1 - (best.metrics?.false_positive_rate || 0)) * 100 },
      ]
    : [];

  const barData = universes.map((u, i) => ({
    name: u.name.replace(" AML Strategy", "").replace(" Strategy", ""),
    f1: +(u.metrics?.f1 || 0).toFixed(3),
    recall: +(u.metrics?.recall || 0).toFixed(3),
    fpr: +(u.metrics?.false_positive_rate || 0).toFixed(3),
    color: UNIVERSE_COLORS[i % UNIVERSE_COLORS.length],
  }));

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Simulation Overview"
        subtitle="Real-time view of your synthetic fintech and multiverse AML simulation"
      />

      <div className="p-8 space-y-8">
        {/* Dataset KPIs */}
        <section>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-4">
            Dataset
          </h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              label="Transactions"
              value={fmtCount(dataset?.n_transactions)}
              icon={Activity}
            />
            <MetricCard
              label="Illicit Transactions"
              value={fmtCount(dataset?.illicit_transactions)}
              sub={fmtPct(dataset?.illicit_ratio) + " of all"}
              icon={AlertTriangle}
            />
            <MetricCard
              label="Customers"
              value={fmtCount(dataset?.n_customers)}
              icon={Globe2}
            />
            <MetricCard
              label="Universes Simulated"
              value={universes.length}
              icon={ShieldCheck}
            />
          </div>
        </section>

        {/* Best Universe KPIs */}
        {best && (
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-4">
              Best Universe — <span className="text-brand-400">{best.name}</span>
            </h2>
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              <MetricCard label="F1 Score" value={fmtNum(best.metrics?.f1)} icon={ShieldCheck} />
              <MetricCard label="Recall" value={fmtPct(best.metrics?.recall)} icon={Activity} />
              <MetricCard label="Precision" value={fmtPct(best.metrics?.precision)} />
              <MetricCard label="FPR" value={fmtPct(best.metrics?.false_positive_rate)} />
              <MetricCard
                label="Total Cost"
                value={fmtMoney(best.metrics?.total_cost)}
                icon={DollarSign}
              />
            </div>
          </section>
        )}

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Radar chart for best universe */}
          {best && radarData.length > 0 && (
            <div className="card">
              <h3 className="text-sm font-semibold text-white mb-4">
                Best Universe — Performance Radar
              </h3>
              <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={radarData} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
                  <PolarGrid stroke="#1f2937" />
                  <PolarAngleAxis
                    dataKey="metric"
                    tick={{ fill: "#6b7280", fontSize: 11 }}
                  />
                  <Radar
                    dataKey="value"
                    stroke="#6366f1"
                    fill="#6366f1"
                    fillOpacity={0.25}
                    strokeWidth={2}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* F1 bar chart across universes */}
          <div className="card">
            <h3 className="text-sm font-semibold text-white mb-4">F1 Score by Universe</h3>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={barData} margin={{ top: 5, right: 5, bottom: 20, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis
                  dataKey="name"
                  tick={{ fill: "#6b7280", fontSize: 10 }}
                  angle={-15}
                  textAnchor="end"
                />
                <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} domain={[0, 1]} />
                <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [v.toFixed(3), "F1"]} />
                <Bar dataKey="f1" radius={[4, 4, 0, 0]}>
                  {barData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Universe ranking table */}
        <section>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-4">
            Universe Ranking
          </h2>
          <div className="card overflow-hidden p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border">
                  {["Rank", "Universe", "F1", "Recall", "Precision", "FPR", "Alerts", "Total Cost"].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {universes.map((u) => (
                  <tr
                    key={u.universe_id}
                    className="hover:bg-surface-hover transition-colors"
                  >
                    <td className="px-5 py-3">
                      <RankBadge rank={u.rank} />
                    </td>
                    <td className="px-5 py-3 font-medium text-white">{u.name}</td>
                    <td className="px-5 py-3 font-mono text-brand-400">
                      {fmtNum(u.metrics?.f1)}
                    </td>
                    <td className="px-5 py-3 font-mono">{fmtPct(u.metrics?.recall)}</td>
                    <td className="px-5 py-3 font-mono">{fmtPct(u.metrics?.precision)}</td>
                    <td className="px-5 py-3 font-mono text-amber-400">
                      {fmtPct(u.metrics?.false_positive_rate)}
                    </td>
                    <td className="px-5 py-3 font-mono">{fmtCount(u.metrics?.n_alerts)}</td>
                    <td className="px-5 py-3 font-mono text-red-400">
                      {fmtMoney(u.metrics?.total_cost)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
