import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Layers, Users, DollarSign, AlertTriangle } from "lucide-react";
import { fmtMoney, fmtCount } from "../lib/utils.js";
import PageHeader from "../components/PageHeader.jsx";
import { PageLoader, ErrorState } from "../components/LoadingState.jsx";
import { api } from "../lib/api.js";

const PRIORITY_STYLES = {
  critical: "bg-red-500/10 text-red-400 border-red-500/20",
  high:     "bg-amber-500/10 text-amber-400 border-amber-500/20",
  medium:   "bg-brand-500/10 text-brand-400 border-brand-500/20",
  low:      "bg-gray-500/10 text-gray-400 border-gray-500/20",
  noise:    "bg-gray-800 text-gray-600 border-gray-700",
};

async function fetchCases(universeId) {
  const res = await fetch(`/api/cases/${universeId}`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export default function Cases() {
  const { data: universes = [], isLoading, error } = useQuery({
    queryKey: ["universes"],
    queryFn: api.universes,
  });

  const [selectedId, setSelectedId] = useState(null);
  const [expandedCase, setExpandedCase] = useState(null);
  const activeId = selectedId || universes[0]?.universe_id;

  const { data: cases = [], isLoading: cLoading, error: cError } = useQuery({
    queryKey: ["cases", activeId],
    queryFn: () => fetchCases(activeId),
    enabled: !!activeId,
  });

  if (isLoading) return <PageLoader message="Loading universes…" />;
  if (error) return <ErrorState error={error} />;

  const realCases = cases.filter(c => c.cluster_label >= 0);
  const noiseCases = cases.filter(c => c.cluster_label < 0);
  const totalAmount = realCases.reduce((s, c) => s + (c.total_amount || 0), 0);

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Case Management"
        subtitle="DBSCAN-clustered alert groups — each case groups related suspicious transactions for investigation"
      />
      <div className="p-8 space-y-6">
        {/* Universe selector */}
        <div className="flex gap-2 flex-wrap">
          {universes.map((u) => (
            <button
              key={u.universe_id}
              onClick={() => { setSelectedId(u.universe_id); setExpandedCase(null); }}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all border ${
                activeId === u.universe_id
                  ? "bg-brand-600 text-white border-brand-600"
                  : "bg-surface-card border-surface-border text-gray-400 hover:text-white"
              }`}
            >
              {u.name?.replace(" AML Strategy", "")}
            </button>
          ))}
        </div>

        {cLoading && <PageLoader message="Clustering alerts…" />}
        {cError && <ErrorState error={cError} />}

        {!cLoading && cases.length > 0 && (
          <>
            {/* Summary KPIs */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="metric-card">
                <span className="metric-label">Cases</span>
                <span className="metric-value">{realCases.length}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">Total Suspicious Amount</span>
                <span className="metric-value text-red-400">{fmtMoney(totalAmount)}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">Critical Cases</span>
                <span className="metric-value text-red-400">
                  {realCases.filter(c => c.priority === "critical").length}
                </span>
              </div>
              <div className="metric-card">
                <span className="metric-label">Noise (Isolated Alerts)</span>
                <span className="metric-value text-gray-500">{noiseCases.length}</span>
              </div>
            </div>

            {/* Cases grid */}
            <div className="grid grid-cols-1 gap-3">
              {realCases.map((c) => (
                <div
                  key={c.case_id}
                  className="card cursor-pointer hover:bg-surface-hover transition-colors"
                  onClick={() => setExpandedCase(expandedCase === c.case_id ? null : c.case_id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className="p-2 rounded-lg bg-brand-500/10 shrink-0">
                        <Layers size={14} className="text-brand-400" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-mono text-xs text-gray-500">{c.case_id}</span>
                          <span className={`badge border ${PRIORITY_STYLES[c.priority] || PRIORITY_STYLES.medium} text-xs uppercase`}>
                            {c.priority}
                          </span>
                          {c.typologies?.map(t => (
                            <span key={t} className="badge bg-surface text-gray-500 border border-surface-border text-xs capitalize">
                              {t.replace("_", " ")}
                            </span>
                          ))}
                        </div>
                        <div className="flex gap-5 text-xs text-gray-500">
                          <span className="flex items-center gap-1">
                            <AlertTriangle size={10} /> {c.n_alerts} alerts
                          </span>
                          <span className="flex items-center gap-1">
                            <Users size={10} /> {c.accounts?.length} accounts
                          </span>
                          <span className="flex items-center gap-1">
                            <DollarSign size={10} /> {fmtMoney(c.total_amount)}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-xs text-gray-500">Max Score</p>
                      <p className="text-sm font-mono font-semibold text-brand-400">
                        {c.max_alert_score?.toFixed(3)}
                      </p>
                    </div>
                  </div>

                  {/* Expanded detail */}
                  {expandedCase === c.case_id && (
                    <div className="mt-4 pt-4 border-t border-surface-border space-y-4"
                         onClick={(e) => e.stopPropagation()}>
                      <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Accounts Involved</p>
                        <div className="flex flex-wrap gap-2">
                          {c.accounts?.map((acc, i) => (
                            <span key={i} className="font-mono text-xs bg-surface border border-surface-border rounded px-2 py-1 text-gray-300">
                              {acc}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Sample Alert IDs</p>
                        <div className="flex flex-wrap gap-2">
                          {c.alert_ids?.slice(0, 10).map((id, i) => (
                            <span key={i} className="font-mono text-xs text-gray-500">{id}</span>
                          ))}
                          {(c.alert_ids?.length || 0) > 10 && (
                            <span className="text-xs text-gray-600">+{c.alert_ids.length - 10} more</span>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {realCases.length === 0 && (
                <div className="text-center py-12 text-gray-600">
                  No cases found for this universe. Run the simulation with more transactions.
                </div>
              )}
            </div>
          </>
        )}

        {!cLoading && cases.length === 0 && !cError && (
          <div className="text-center py-12 text-gray-600">
            No alert data. Run the simulation first.
          </div>
        )}
      </div>
    </div>
  );
}
