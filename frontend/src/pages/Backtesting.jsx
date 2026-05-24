import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend, ReferenceLine,
} from "recharts";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";
import { api } from "../lib/api.js";
import { fmtPct, fmtNum, fmtMoney, UNIVERSE_COLORS } from "../lib/utils.js";
import PageHeader from "../components/PageHeader.jsx";
import { PageLoader, ErrorState } from "../components/LoadingState.jsx";

const TOOLTIP_STYLE = {
  contentStyle: { background: "#161b27", border: "1px solid #1f2937", borderRadius: 8 },
  labelStyle: { color: "#9ca3af" },
};

export default function Backtesting() {
  const { data: allResults = [], isLoading, error } = useQuery({
    queryKey: ["backtesting"],
    queryFn: api.backtesting,
  });

  const [selectedIds, setSelectedIds] = useState([]);

  if (isLoading) return <PageLoader message="Loading backtesting results…" />;
  if (error) return <ErrorState error={error} />;

  if (!allResults.length) {
    return (
      <div className="flex flex-col h-full">
        <PageHeader title="Backtesting Engine" subtitle="Temporal performance drift analysis" />
        <div className="flex items-center justify-center h-64 text-gray-600 text-sm">
          No backtesting data. Run the simulation without <code className="font-mono bg-surface-card px-1 rounded">--no-backtest</code>.
        </div>
      </div>
    );
  }

  const activeIds = selectedIds.length > 0 ? selectedIds : allResults.map((r) => r.universe_id);
  const activeResults = allResults.filter((r) => activeIds.includes(r.universe_id));

  // Build time-series chart data aligned by window_id
  const maxWindows = Math.max(...allResults.map((r) => r.windows?.length || 0));
  const chartData = Array.from({ length: maxWindows }, (_, i) => {
    const point = { window: i + 1 };
    activeResults.forEach((result, ri) => {
      const w = result.windows?.[i];
      if (w) {
        point[`${result.universe_id}_f1`] = w.f1;
        point[`${result.universe_id}_recall`] = w.recall;
        point[`window_start`] = w.window_start;
      }
    });
    return point;
  });

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Backtesting Engine"
        subtitle="Temporal drift analysis — how each universe performs across rolling time windows"
      />

      <div className="p-8 space-y-8">
        {/* Universe selector */}
        <div className="flex flex-wrap gap-2">
          {allResults.map((r, i) => (
            <button
              key={r.universe_id}
              onClick={() =>
                setSelectedIds((prev) =>
                  prev.includes(r.universe_id)
                    ? prev.filter((id) => id !== r.universe_id)
                    : [...prev, r.universe_id]
                )
              }
              className="px-3 py-1.5 rounded-lg text-sm font-medium transition-all border"
              style={
                activeIds.includes(r.universe_id)
                  ? { background: `${UNIVERSE_COLORS[i % UNIVERSE_COLORS.length]}20`, borderColor: UNIVERSE_COLORS[i % UNIVERSE_COLORS.length], color: UNIVERSE_COLORS[i % UNIVERSE_COLORS.length] }
                  : { background: "transparent", borderColor: "#1f2937", color: "#6b7280" }
              }
            >
              {r.universe_name?.replace(" AML Strategy", "") || r.universe_id}
            </button>
          ))}
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {activeResults.map((r, i) => {
            const drift = r.f1_drift;
            const DriftIcon = drift > 0.02 ? TrendingUp : drift < -0.02 ? TrendingDown : Minus;
            const driftColor = drift > 0.02 ? "text-green-400" : drift < -0.02 ? "text-red-400" : "text-gray-400";
            return (
              <div key={r.universe_id} className="card" style={{ borderColor: `${UNIVERSE_COLORS[i % UNIVERSE_COLORS.length]}30` }}>
                <div className="flex items-start justify-between mb-3">
                  <p className="text-sm font-semibold text-white">
                    {r.universe_name?.replace(" AML Strategy", "") || r.universe_id}
                  </p>
                  <div className={`flex items-center gap-1 text-xs font-mono ${driftColor}`}>
                    <DriftIcon size={12} />
                    {drift > 0 ? "+" : ""}{(drift * 100).toFixed(1)}% F1 drift
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div>
                    <p className="text-xs text-gray-500">Avg F1</p>
                    <p className="text-base font-mono font-semibold text-white">{fmtNum(r.avg_f1)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Avg Recall</p>
                    <p className="text-base font-mono font-semibold">{fmtPct(r.avg_recall)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Windows</p>
                    <p className="text-base font-mono font-semibold">{r.n_windows}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* F1 over time chart */}
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-4">F1 Score Over Time (per window)</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="window" tick={{ fill: "#6b7280", fontSize: 11 }} label={{ value: "Window", position: "bottom", fill: "#6b7280", fontSize: 11 }} />
              <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} domain={[0, 1]} tickFormatter={(v) => v.toFixed(1)} />
              <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [v?.toFixed(3), ""]} labelFormatter={(l) => `Window ${l}`} />
              <Legend wrapperStyle={{ fontSize: 11, color: "#9ca3af" }} />
              {activeResults.map((r, i) => (
                <Line
                  key={r.universe_id}
                  type="monotone"
                  dataKey={`${r.universe_id}_f1`}
                  stroke={UNIVERSE_COLORS[i % UNIVERSE_COLORS.length]}
                  dot={false}
                  strokeWidth={2}
                  name={r.universe_name?.replace(" AML Strategy", "") || r.universe_id}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Window detail table for first active universe */}
        {activeResults[0] && (
          <div className="card p-0 overflow-hidden">
            <div className="px-6 py-4 border-b border-surface-border">
              <h3 className="text-sm font-semibold text-white">
                Window Detail — {activeResults[0].universe_name}
              </h3>
            </div>
            <div className="overflow-x-auto max-h-72">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-surface-border">
                    {["Window", "Period", "Transactions", "Illicit", "F1", "Recall", "FPR", "Cost"].map((h) => (
                      <th key={h} className="px-4 py-3 text-left font-semibold text-gray-500 uppercase tracking-wider">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {(activeResults[0].windows || []).map((w) => (
                    <tr key={w.window_id} className="hover:bg-surface-hover">
                      <td className="px-4 py-2 font-mono text-gray-400">#{w.window_id + 1}</td>
                      <td className="px-4 py-2 text-gray-400">{w.window_start} → {w.window_end}</td>
                      <td className="px-4 py-2 font-mono">{w.n_transactions?.toLocaleString()}</td>
                      <td className="px-4 py-2 font-mono text-red-400">{w.n_illicit}</td>
                      <td className="px-4 py-2 font-mono text-brand-400">{fmtNum(w.f1)}</td>
                      <td className="px-4 py-2 font-mono">{fmtPct(w.recall)}</td>
                      <td className="px-4 py-2 font-mono text-amber-400">{fmtPct(w.false_positive_rate)}</td>
                      <td className="px-4 py-2 font-mono">{fmtMoney(w.total_cost)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
