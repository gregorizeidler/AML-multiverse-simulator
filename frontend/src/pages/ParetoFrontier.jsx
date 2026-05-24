import { useQuery } from "@tanstack/react-query";
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Label, ReferenceLine,
} from "recharts";
import { Star, TrendingUp, Shield } from "lucide-react";
import { fmtMoney, fmtPct } from "../lib/utils.js";
import PageHeader from "../components/PageHeader.jsx";
import { PageLoader, ErrorState } from "../components/LoadingState.jsx";

async function fetchPareto() {
  const res = await fetch("/api/pareto");
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

const COLORS = {
  pareto: "#6366f1",
  dominated: "#374151",
};

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-surface-card border border-surface-border rounded-xl p-3 text-xs space-y-1 shadow-xl">
      <p className="font-semibold text-white">{d.name}</p>
      <p className="text-gray-400">Rank #{d.rank}</p>
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 mt-1">
        <span className="text-gray-500">F1</span><span className="text-white font-mono">{d.f1?.toFixed(4)}</span>
        <span className="text-gray-500">Recall</span><span className="text-white font-mono">{d.recall?.toFixed(4)}</span>
        <span className="text-gray-500">FPR</span><span className="text-red-400 font-mono">{d.false_positive_rate?.toFixed(4)}</span>
        <span className="text-gray-500">Cost</span><span className="text-amber-400 font-mono">{fmtMoney(d.total_cost)}</span>
        <span className="text-gray-500">Pareto</span>
        <span className={d.on_pareto_front ? "text-green-400" : "text-gray-600"}>
          {d.on_pareto_front ? "✓ On frontier" : "Dominated"}
        </span>
      </div>
      {d.rank_sensitivity && (
        <div className="pt-1 border-t border-surface-border text-gray-500">
          Rank range: #{d.rank_sensitivity.min_rank} – #{d.rank_sensitivity.max_rank}
          {d.rank_sensitivity.rank_stable && <span className="ml-1 text-green-400">(stable)</span>}
        </div>
      )}
    </div>
  );
}

export default function ParetoFrontier() {
  const { data = [], isLoading, error } = useQuery({
    queryKey: ["pareto"],
    queryFn: fetchPareto,
  });

  if (isLoading) return <PageLoader message="Computing Pareto frontier…" />;
  if (error)     return <ErrorState error={error} />;

  const paretoPoints = data.filter(d => d.on_pareto_front);
  const dominated    = data.filter(d => !d.on_pareto_front);

  const scatterData = data.map(d => ({
    ...d,
    // X axis: Cost (lower = better → invert for intuitive viz)
    x: d.total_cost,
    y: d.f1,
    fill: d.on_pareto_front ? COLORS.pareto : COLORS.dominated,
    r: d.on_pareto_front ? 8 : 5,
  }));

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Pareto Frontier"
        subtitle="Non-dominated universes across F1 vs. Cost · ranked under 4 weight scenarios (sensitivity)"
      />
      <div className="p-8 space-y-6">
        {/* Legend + KPIs */}
        <div className="grid grid-cols-3 gap-4">
          <div className="metric-card">
            <span className="metric-label">On Pareto Frontier</span>
            <span className="metric-value text-brand-400">{paretoPoints.length}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Dominated Universes</span>
            <span className="metric-value text-gray-500">{dominated.length}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Total Universes</span>
            <span className="metric-value">{data.length}</span>
          </div>
        </div>

        {/* Pareto scatter: F1 vs Cost */}
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-1">F1 Score vs. Total Cost</h3>
          <p className="text-xs text-gray-500 mb-4">
            <span className="inline-block w-3 h-3 rounded-full bg-brand-500 mr-1" />
            Pareto-optimal (never dominated on ALL objectives simultaneously) ·
            <span className="inline-block w-3 h-3 rounded-full bg-gray-700 mx-1" />
            Dominated
          </p>
          <ResponsiveContainer width="100%" height={380}>
            <ScatterChart margin={{ top: 20, right: 40, bottom: 40, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis
                type="number"
                dataKey="x"
                name="Total Cost"
                tick={{ fill: "#6b7280", fontSize: 11 }}
                tickFormatter={v => `$${(v / 1000).toFixed(0)}k`}
              >
                <Label value="Total Operational Cost ($)" offset={-10} position="insideBottom" fill="#6b7280" fontSize={11} />
              </XAxis>
              <YAxis
                type="number"
                dataKey="y"
                name="F1 Score"
                tick={{ fill: "#6b7280", fontSize: 11 }}
                domain={[0, 1]}
              >
                <Label value="F1 Score" angle={-90} position="insideLeft" fill="#6b7280" fontSize={11} />
              </YAxis>
              <Tooltip content={<CustomTooltip />} />
              {/* Dominated */}
              <Scatter
                name="Dominated"
                data={dominated.map(d => ({ ...d, x: d.total_cost, y: d.f1 }))}
                fill={COLORS.dominated}
                opacity={0.7}
              />
              {/* Pareto-optimal */}
              <Scatter
                name="Pareto-Optimal"
                data={paretoPoints.map(d => ({ ...d, x: d.total_cost, y: d.f1 }))}
                fill={COLORS.pareto}
                opacity={1}
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        {/* Pareto frontier table */}
        <div className="card p-0 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-border flex items-center gap-2">
            <Star size={14} className="text-brand-400" />
            <h3 className="text-sm font-semibold text-white">Pareto-Optimal Universes</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-surface-border">
                  {["Universe", "F1", "Recall", "FPR", "Cost", "Rank", "Rank Range", "Stable"].map(h => (
                    <th key={h} className="px-4 py-3 text-left font-semibold text-gray-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {paretoPoints.sort((a, b) => a.rank - b.rank).map((u) => (
                  <tr key={u.universe_id} className="hover:bg-surface-hover">
                    <td className="px-4 py-3 text-white font-medium">{u.name}</td>
                    <td className="px-4 py-3 font-mono text-green-400">{u.f1?.toFixed(4)}</td>
                    <td className="px-4 py-3 font-mono">{u.recall?.toFixed(4)}</td>
                    <td className="px-4 py-3 font-mono text-red-400">{u.false_positive_rate?.toFixed(4)}</td>
                    <td className="px-4 py-3 font-mono text-amber-400">{fmtMoney(u.total_cost)}</td>
                    <td className="px-4 py-3 font-mono">#{u.rank}</td>
                    <td className="px-4 py-3 font-mono text-gray-400">
                      #{u.rank_sensitivity?.min_rank ?? "—"} – #{u.rank_sensitivity?.max_rank ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      {u.rank_sensitivity?.rank_stable
                        ? <span className="badge bg-green-500/10 text-green-400">Yes</span>
                        : <span className="badge bg-amber-500/10 text-amber-400">No</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Sensitivity analysis note */}
        <div className="card border-brand-500/20 bg-brand-500/5">
          <p className="text-xs text-gray-400">
            <strong className="text-white">Sensitivity Analysis:</strong> Each universe was ranked under 4 weight
            scenarios (F1-focused, Recall-focused, FPR-focused, Cost-focused). "Rank Range" shows min/max rank across
            all scenarios. "Stable" = rank doesn't move by more than 1 position — those universes are robust
            to changes in your optimization priority.
          </p>
        </div>
      </div>
    </div>
  );
}
