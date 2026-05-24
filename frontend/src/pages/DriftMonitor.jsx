import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
import { AlertTriangle, CheckCircle, TrendingDown } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import { PageLoader, ErrorState } from "../components/LoadingState.jsx";

async function fetchDrift() {
  const res = await fetch("/api/drift");
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

const SEVERITY_STYLES = {
  none:   "bg-green-500/10  text-green-400  border-green-500/20",
  low:    "bg-blue-500/10   text-blue-400   border-blue-500/20",
  medium: "bg-amber-500/10  text-amber-400  border-amber-500/20",
  high:   "bg-red-500/10    text-red-400    border-red-500/20",
};

const PSI_COLOR = (psi) =>
  psi > 0.25 ? "#ef4444" : psi > 0.10 ? "#f59e0b" : "#22c55e";

export default function DriftMonitor() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["drift"],
    queryFn: fetchDrift,
  });

  if (isLoading) return <PageLoader message="Running drift detection…" />;
  if (error)     return <ErrorState error={error} />;

  if (!data || !data.length) {
    return (
      <div className="flex flex-col h-full">
        <PageHeader title="Drift Monitor" subtitle="Concept drift detection via KS test + PSI" />
        <div className="flex items-center justify-center h-64 text-gray-600 text-sm">
          No drift data. Run the simulation first.
        </div>
      </div>
    );
  }

  // Use latest drift report
  const report = data[data.length - 1];
  const features = report.features || [];
  const drifted = features.filter(f => f.is_drifted);

  const barData = features.slice(0, 20).map(f => ({
    feature: f.feature.replace(/_/g, " "),
    ks: f.ks_statistic,
    psi: f.psi,
    drifted: f.is_drifted,
  }));

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Concept Drift Monitor"
        subtitle={`${report.reference_period} → ${report.current_period} · KS test + Population Stability Index`}
      />
      <div className="p-8 space-y-6">
        {/* Overall severity */}
        <div className={`card border ${SEVERITY_STYLES[report.severity] || SEVERITY_STYLES.none}`}>
          <div className="flex items-center gap-3">
            {report.severity === "none" || report.severity === "low" ? (
              <CheckCircle size={18} className="text-green-400 shrink-0" />
            ) : (
              <TrendingDown size={18} className="text-red-400 shrink-0" />
            )}
            <div>
              <p className="text-sm font-semibold text-white capitalize">
                {report.severity} Drift Detected
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                {drifted.length}/{features.length} features drifted · Overall KS score: {report.overall_drift_score?.toFixed(4)}
                {report.alert_rate_drift != null && ` · Alert rate change: ${report.alert_rate_drift > 0 ? "+" : ""}${(report.alert_rate_drift * 100).toFixed(2)}%`}
              </p>
            </div>
          </div>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="metric-card">
            <span className="metric-label">Features Monitored</span>
            <span className="metric-value">{report.n_features_monitored}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Features Drifted</span>
            <span className="metric-value text-red-400">{report.n_features_drifted}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Drift Score</span>
            <span className="metric-value">{report.overall_drift_score?.toFixed(4)}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Alert Rate Δ</span>
            <span className={`metric-value ${(report.alert_rate_drift || 0) > 0 ? "text-red-400" : "text-green-400"}`}>
              {report.alert_rate_drift != null ? `${report.alert_rate_drift > 0 ? "+" : ""}${(report.alert_rate_drift * 100).toFixed(2)}%` : "—"}
            </span>
          </div>
        </div>

        {/* PSI bar chart */}
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-1">PSI per Feature</h3>
          <p className="text-xs text-gray-500 mb-4">
            PSI &lt;0.10: stable · 0.10–0.25: monitor · &gt;0.25: major shift
          </p>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={barData} layout="vertical" margin={{ top: 5, right: 40, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
              <XAxis type="number" tick={{ fill: "#6b7280", fontSize: 10 }} />
              <YAxis type="category" dataKey="feature" width={160} tick={{ fill: "#9ca3af", fontSize: 10 }} />
              <Tooltip
                contentStyle={{ background: "#161b27", border: "1px solid #1f2937", borderRadius: 8 }}
                formatter={(v, name) => [v?.toFixed(4), name.toUpperCase()]}
              />
              <Bar dataKey="psi" radius={[0, 4, 4, 0]} name="PSI">
                {barData.map((entry, i) => (
                  <Cell key={i} fill={PSI_COLOR(entry.psi)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Feature drift table */}
        <div className="card p-0 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-border">
            <h3 className="text-sm font-semibold text-white">Feature Drift Detail</h3>
          </div>
          <div className="overflow-x-auto max-h-80">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-surface-border">
                  {["Feature", "KS Stat", "p-value", "PSI", "Mean Δ%", "Severity", "Drifted"].map(h => (
                    <th key={h} className="px-4 py-3 text-left font-semibold text-gray-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {features.map((f, i) => (
                  <tr key={i} className="hover:bg-surface-hover">
                    <td className="px-4 py-2.5 font-mono text-gray-300">{f.feature}</td>
                    <td className="px-4 py-2.5 font-mono">{f.ks_statistic?.toFixed(4)}</td>
                    <td className="px-4 py-2.5 font-mono">{f.p_value?.toFixed(4)}</td>
                    <td className="px-4 py-2.5 font-mono" style={{ color: PSI_COLOR(f.psi) }}>
                      {f.psi?.toFixed(4)}
                    </td>
                    <td className={`px-4 py-2.5 font-mono ${f.mean_shift_pct > 0 ? "text-red-400" : "text-green-400"}`}>
                      {f.mean_shift_pct > 0 ? "+" : ""}{f.mean_shift_pct?.toFixed(1)}%
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={`badge border ${SEVERITY_STYLES[f.severity] || ""} text-xs`}>
                        {f.severity}
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      {f.is_drifted
                        ? <span className="badge bg-red-500/10 text-red-400">Yes</span>
                        : <span className="badge bg-green-500/10 text-green-400">No</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
