import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  ScatterChart, Scatter, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, ZAxis,
} from "recharts";
import { ChevronRight } from "lucide-react";
import { api } from "../lib/api.js";
import { fmtPct, fmtNum, fmtMoney, UNIVERSE_COLORS } from "../lib/utils.js";
import PageHeader from "../components/PageHeader.jsx";
import RankBadge from "../components/RankBadge.jsx";
import { PageLoader, ErrorState } from "../components/LoadingState.jsx";

const TOOLTIP_STYLE = {
  contentStyle: { background: "#161b27", border: "1px solid #1f2937", borderRadius: 8 },
  labelStyle: { color: "#9ca3af" },
};

export default function UniverseList() {
  const { data: universes = [], isLoading, error } = useQuery({
    queryKey: ["universes"],
    queryFn: api.universes,
  });

  if (isLoading) return <PageLoader message="Loading universes…" />;
  if (error) return <ErrorState error={error} />;

  const scatterData = universes.map((u, i) => ({
    name: u.name,
    x: +(u.metrics?.false_positive_rate || 0).toFixed(4),
    y: +(u.metrics?.recall || 0).toFixed(4),
    z: +(u.metrics?.f1 || 0).toFixed(3) * 100,
    fill: UNIVERSE_COLORS[i % UNIVERSE_COLORS.length],
  }));

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Parallel Universes"
        subtitle="All simulated AML policy configurations and their comparative performance"
      />

      <div className="p-8 space-y-8">
        {/* Recall vs FPR scatter */}
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-1">Recall vs False Positive Rate</h3>
          <p className="text-xs text-gray-500 mb-4">
            Ideal universe: top-left corner (high recall, low FPR). Bubble size = F1 score.
          </p>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis
                dataKey="x"
                name="FPR"
                label={{ value: "False Positive Rate", position: "bottom", fill: "#6b7280", fontSize: 11 }}
                tick={{ fill: "#6b7280", fontSize: 11 }}
                tickFormatter={(v) => `${(v * 100).toFixed(1)}%`}
              />
              <YAxis
                dataKey="y"
                name="Recall"
                tick={{ fill: "#6b7280", fontSize: 11 }}
                tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
              />
              <ZAxis dataKey="z" range={[100, 800]} />
              <Tooltip
                {...TOOLTIP_STYLE}
                cursor={{ strokeDasharray: "3 3" }}
                content={({ payload }) => {
                  if (!payload?.length) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="bg-surface-card border border-surface-border rounded-lg p-3 text-xs">
                      <p className="font-semibold text-white mb-1">{d.name}</p>
                      <p className="text-gray-400">FPR: {fmtPct(d.x)}</p>
                      <p className="text-gray-400">Recall: {fmtPct(d.y)}</p>
                      <p className="text-brand-400">F1: {fmtNum(d.z / 100)}</p>
                    </div>
                  );
                }}
              />
              {scatterData.map((entry, i) => (
                <Scatter key={i} data={[entry]} fill={entry.fill} opacity={0.85} />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        {/* Universe cards */}
        <div className="grid grid-cols-1 gap-4">
          {universes.map((u, i) => (
            <Link
              key={u.universe_id}
              to={`/universes/${u.universe_id}`}
              className="card hover:bg-surface-hover transition-all duration-150 group"
            >
              <div className="flex items-start gap-4">
                <RankBadge rank={u.rank} />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-white group-hover:text-brand-400 transition-colors">
                      {u.name}
                    </h3>
                    <span className="badge bg-surface text-gray-500 border border-surface-border text-xs">
                      {u.n_rules} rules
                    </span>
                  </div>

                  <div className="grid grid-cols-3 md:grid-cols-6 gap-4 mt-3">
                    {[
                      ["F1", fmtNum(u.metrics?.f1), "text-brand-400"],
                      ["Recall", fmtPct(u.metrics?.recall), "text-green-400"],
                      ["Precision", fmtPct(u.metrics?.precision), "text-white"],
                      ["FPR", fmtPct(u.metrics?.false_positive_rate), "text-amber-400"],
                      ["Alerts", u.metrics?.n_alerts?.toLocaleString(), "text-white"],
                      ["Cost", fmtMoney(u.metrics?.total_cost), "text-red-400"],
                    ].map(([label, value, color]) => (
                      <div key={label}>
                        <p className="text-xs text-gray-500 uppercase tracking-wider">{label}</p>
                        <p className={`text-sm font-mono font-medium mt-0.5 ${color}`}>{value}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <ChevronRight
                  size={16}
                  className="text-gray-600 group-hover:text-brand-400 transition-colors shrink-0 mt-1"
                />
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
