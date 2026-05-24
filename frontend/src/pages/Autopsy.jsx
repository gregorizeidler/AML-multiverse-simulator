import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
import { api } from "../lib/api.js";
import { fmtPct, fmtMoney } from "../lib/utils.js";
import PageHeader from "../components/PageHeader.jsx";
import { PageLoader, ErrorState } from "../components/LoadingState.jsx";

const TYPOLOGY_COLORS = {
  smurfing: "#6366f1",
  layering: "#f59e0b",
  structuring: "#22c55e",
  round_tripping: "#ec4899",
};

export default function Autopsy() {
  const { data: universes = [], isLoading: uLoading, error: uError } = useQuery({
    queryKey: ["universes"],
    queryFn: api.universes,
  });

  const [selectedId, setSelectedId] = useState(null);
  const activeId = selectedId || universes[0]?.universe_id;

  const { data: autopsy, isLoading: aLoading, error: aError } = useQuery({
    queryKey: ["autopsy", activeId],
    queryFn: () => api.autopsy(activeId),
    enabled: !!activeId,
  });

  if (uLoading) return <PageLoader message="Loading universes…" />;
  if (uError) return <ErrorState error={uError} />;

  const fnByTypology = autopsy?.fn_by_typology || {};
  const typologyData = Object.entries(fnByTypology).map(([name, count]) => ({
    name,
    count,
    fill: TYPOLOGY_COLORS[name] || "#6366f1",
  }));

  const fnSummary = autopsy?.fn_summary || {};
  const fpSummary = autopsy?.fp_summary || {};
  const falseNegatives = autopsy?.false_negatives || [];
  const falsePositives = autopsy?.false_positives || [];

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Failure Autopsy"
        subtitle="Deep-dive into missed detections (false negatives) and false alarms"
      />

      <div className="p-8 space-y-6">
        {/* Universe selector */}
        <div className="flex gap-2 flex-wrap">
          {universes.map((u) => (
            <button
              key={u.universe_id}
              onClick={() => setSelectedId(u.universe_id)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                activeId === u.universe_id
                  ? "bg-brand-600 text-white"
                  : "bg-surface-card border border-surface-border text-gray-400 hover:text-white"
              }`}
            >
              {u.name.replace(" AML Strategy", "")}
            </button>
          ))}
        </div>

        {aLoading && <PageLoader message="Loading autopsy report…" />}
        {aError && <ErrorState error={aError} />}

        {autopsy && !aLoading && (
          <>
            {/* Summary KPIs */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="metric-card">
                <span className="metric-label">Missed Illicit Txns</span>
                <span className="metric-value text-red-400">{fnSummary.total_missed ?? "—"}</span>
                <span className="metric-sub">Miss rate: {fmtPct(fnSummary.miss_rate)}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">Avg Amount Missed</span>
                <span className="metric-value">{fmtMoney(fnSummary.avg_amount_missed)}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">False Alerts</span>
                <span className="metric-value text-amber-400">{fpSummary.total_false_alerts ?? "—"}</span>
                <span className="metric-sub">FP rate: {fmtPct(fpSummary.fp_rate)}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">Avg Score Gap</span>
                <span className="metric-value">{fnSummary.avg_score_gap?.toFixed(3) ?? "—"}</span>
                <span className="metric-sub">distance to threshold</span>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Typology breakdown */}
              <div className="card">
                <h3 className="text-sm font-semibold text-white mb-4">Missed by Typology</h3>
                {typologyData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={typologyData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                      <XAxis dataKey="name" tick={{ fill: "#6b7280", fontSize: 11 }} />
                      <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} />
                      <Tooltip
                        contentStyle={{ background: "#161b27", border: "1px solid #1f2937", borderRadius: 8 }}
                      />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {typologyData.map((entry, i) => (
                          <Cell key={i} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-gray-600 text-sm">No missed detections recorded.</p>
                )}
              </div>

              {/* Top false negatives */}
              <div className="card p-0 overflow-hidden">
                <div className="px-5 py-4 border-b border-surface-border">
                  <h3 className="text-sm font-semibold text-white">
                    Top Missed Illicit Transactions
                  </h3>
                </div>
                <div className="divide-y divide-surface-border max-h-64 overflow-y-auto">
                  {falseNegatives.slice(0, 10).map((fn, i) => (
                    <div key={i} className="px-5 py-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-xs text-gray-400">{fn.tx_id}</span>
                        <span className="badge bg-red-500/10 text-red-400 text-xs">
                          {fn.typology}
                        </span>
                      </div>
                      <div className="flex gap-4 text-xs text-gray-500">
                        <span>Score: <span className="text-white">{fn.alert_score?.toFixed(3)}</span></span>
                        <span>Gap: <span className="text-amber-400">{fn.score_gap?.toFixed(3)}</span></span>
                        <span>Amount: <span className="text-white">{fmtMoney(fn.amount)}</span></span>
                      </div>
                      <p className="text-xs text-gray-600 mt-1 italic">{fn.reason}</p>
                    </div>
                  ))}
                  {falseNegatives.length === 0 && (
                    <div className="px-5 py-6 text-center text-gray-600 text-sm">
                      No false negatives — perfect recall!
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* False positives */}
            <div className="card p-0 overflow-hidden">
              <div className="px-6 py-4 border-b border-surface-border">
                <h3 className="text-sm font-semibold text-white">
                  False Positives — Legitimate Transactions Wrongly Flagged
                </h3>
              </div>
              <div className="divide-y divide-surface-border max-h-56 overflow-y-auto">
                {falsePositives.slice(0, 10).map((fp, i) => (
                  <div key={i} className="px-6 py-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-xs text-gray-400">{fp.tx_id}</span>
                      <span className="text-xs text-amber-400 font-mono">
                        score: {fp.alert_score?.toFixed(3)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 italic">{fp.reason}</p>
                  </div>
                ))}
                {falsePositives.length === 0 && (
                  <div className="px-6 py-6 text-center text-gray-600 text-sm">
                    No false positives — perfect precision!
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
