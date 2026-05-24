import { useQuery } from "@tanstack/react-query";
import { Users, Link, AlertTriangle } from "lucide-react";
import { fmtCount } from "../lib/utils.js";
import PageHeader from "../components/PageHeader.jsx";
import { PageLoader, ErrorState } from "../components/LoadingState.jsx";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

async function fetchEntityResolution() {
  const res = await fetch("/api/entity-resolution");
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export default function EntityResolution() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["entity-resolution"],
    queryFn: fetchEntityResolution,
  });

  if (isLoading) return <PageLoader message="Running entity resolution…" />;
  if (error)     return <ErrorState error={error} />;

  if (!data) {
    return (
      <div className="flex flex-col h-full">
        <PageHeader title="Entity Resolution" subtitle="Linking accounts to the same real-world customer" />
        <div className="flex items-center justify-center h-64 text-gray-600 text-sm">No data. Run simulation first.</div>
      </div>
    );
  }

  const riskDist = data.entity_risk_distribution || {};
  const riskData = [
    { risk: "High (>0.6)", count: riskDist.high || 0, fill: "#ef4444" },
    { risk: "Medium (0.3-0.6)", count: riskDist.medium || 0, fill: "#f59e0b" },
    { risk: "Low (<0.3)", count: riskDist.low || 0, fill: "#22c55e" },
  ];

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Entity Resolution"
        subtitle="Union-Find algorithm linking accounts by shared customer_id · email domain · phone prefix"
      />
      <div className="p-8 space-y-6">
        {/* KPIs */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="metric-card">
            <span className="metric-label">Real Entities</span>
            <span className="metric-value">{fmtCount(data.n_entities)}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Accounts Linked</span>
            <span className="metric-value text-brand-400">{fmtCount(data.n_accounts_linked)}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Multi-Account Entities</span>
            <span className="metric-value text-amber-400">{fmtCount(data.entities_with_multiple_accounts)}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Max Accounts / Entity</span>
            <span className="metric-value">{data.max_accounts_per_entity}</span>
          </div>
        </div>

        {/* Risk distribution */}
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-4">Entity Risk Distribution</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={riskData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="risk" tick={{ fill: "#9ca3af", fontSize: 11 }} />
              <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#161b27", border: "1px solid #1f2937", borderRadius: 8 }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {riskData.map((entry, i) => (
                  <Bar key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Explanation */}
        <div className="card border-blue-500/20 bg-blue-500/5 space-y-3">
          <div className="flex items-center gap-2">
            <Link size={14} className="text-blue-400" />
            <h3 className="text-sm font-semibold text-white">How Entity Resolution Works</h3>
          </div>
          <div className="text-xs text-gray-400 space-y-2">
            <p>
              <strong className="text-white">Problem:</strong> A money launderer operating 5 accounts appears as 5
              independent nodes in the transaction graph. Without entity resolution, the betweenness centrality
              of each node underestimates the true risk.
            </p>
            <p>
              <strong className="text-white">Solution:</strong> Union-Find links accounts sharing (1) the same
              customer_id, (2) the same non-generic email domain (e.g. @shellcorp.com), or (3) the same
              phone prefix. Linked accounts inherit a shared entity risk score.
            </p>
            <p>
              <strong className="text-white">Impact:</strong> The GNN Universe and rule engine use{" "}
              <code className="font-mono bg-surface px-1 rounded">from_entity_risk</code> as a feature,
              allowing detection of shell company networks that individually appear low-risk.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
