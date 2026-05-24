import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
import { api } from "../lib/api.js";
import PageHeader from "../components/PageHeader.jsx";
import { PageLoader, ErrorState } from "../components/LoadingState.jsx";

async function fetchShap(universeId) {
  const res = await fetch(`/api/shap/${universeId}`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export default function Explainability() {
  const { data: universes = [], isLoading, error } = useQuery({
    queryKey: ["universes"],
    queryFn: api.universes,
  });

  const [selectedId, setSelectedId] = useState(null);
  const activeId = selectedId || universes.find(u => u.universe_id === "universe_ml_model")?.universe_id || universes[0]?.universe_id;

  const { data: shapData, isLoading: shapLoading, error: shapError } = useQuery({
    queryKey: ["shap", activeId],
    queryFn: () => fetchShap(activeId),
    enabled: !!activeId,
  });

  if (isLoading) return <PageLoader message="Loading universes…" />;
  if (error) return <ErrorState error={error} />;

  const importance = shapData?.global?.feature_importance || [];
  const top20 = importance.slice(0, 20);

  const maxImportance = Math.max(...top20.map(f => f.importance), 1);

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="SHAP Explainability"
        subtitle="Feature importance and per-transaction explanations from the XGBoost ML universe"
      />
      <div className="p-8 space-y-6">
        {/* Universe selector — only ML universe has SHAP */}
        <div className="flex gap-2 flex-wrap">
          {universes.map((u) => (
            <button
              key={u.universe_id}
              onClick={() => setSelectedId(u.universe_id)}
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

        {shapLoading && <PageLoader message="Computing SHAP values…" />}
        {shapError && <ErrorState error={shapError} />}

        {shapData && !shapLoading && (
          <>
            {/* Availability banner */}
            <div className={`card border-${shapData.global?.shap_available ? "green" : "amber"}-500/20 bg-${shapData.global?.shap_available ? "green" : "amber"}-500/5`}>
              <p className={`text-sm ${shapData.global?.shap_available ? "text-green-400" : "text-amber-400"}`}>
                {shapData.global?.shap_available
                  ? `SHAP TreeExplainer active — ${shapData.global?.n_samples?.toLocaleString()} samples analyzed`
                  : `SHAP fallback mode — install 'shap' package for full explainability. ${shapData.global?.fallback_reason || ""}`}
              </p>
            </div>

            {/* Global feature importance */}
            <div className="card">
              <h3 className="text-sm font-semibold text-white mb-1">Global Feature Importance (mean |SHAP|)</h3>
              <p className="text-xs text-gray-500 mb-4">
                Expected value (model baseline): {shapData.global?.expected_value?.toFixed(4) ?? "—"}
              </p>
              <ResponsiveContainer width="100%" height={Math.max(300, top20.length * 28)}>
                <BarChart data={top20} layout="vertical" margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
                  <XAxis type="number" tick={{ fill: "#6b7280", fontSize: 10 }} />
                  <YAxis
                    type="category"
                    dataKey="feature"
                    width={180}
                    tick={{ fill: "#9ca3af", fontSize: 11 }}
                    tickFormatter={(v) => v.replace(/_/g, " ")}
                  />
                  <Tooltip
                    contentStyle={{ background: "#161b27", border: "1px solid #1f2937", borderRadius: 8 }}
                    formatter={(v) => [v.toFixed(6), "Importance"]}
                  />
                  <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
                    {top20.map((entry, i) => (
                      <Cell
                        key={i}
                        fill={`hsl(${240 - (entry.importance / maxImportance) * 120}, 70%, 60%)`}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Calibration results if available */}
            {shapData.calibration && (
              <div className="card">
                <h3 className="text-sm font-semibold text-white mb-4">Model Calibration</h3>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  {[
                    ["ECE (raw)", shapData.calibration.before?.ece?.toFixed(4), "text-red-400"],
                    ["ECE (calibrated)", shapData.calibration.after?.ece?.toFixed(4), "text-green-400"],
                    ["Brier (raw)", shapData.calibration.before?.brier_score?.toFixed(4), ""],
                    ["Brier (calibrated)", shapData.calibration.after?.brier_score?.toFixed(4), "text-green-400"],
                  ].map(([label, value, color]) => (
                    <div key={label} className="metric-card">
                      <span className="metric-label">{label}</span>
                      <span className={`metric-value text-xl ${color}`}>{value ?? "—"}</span>
                    </div>
                  ))}
                </div>
                {shapData.calibration.reliability_diagram?.length > 0 && (
                  <div className="mt-4">
                    <p className="text-xs text-gray-500 mb-2">Reliability Diagram — after calibration (diagonal = perfect)</p>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={shapData.calibration.after?.reliability_diagram || []}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                        <XAxis dataKey="mean_predicted" tick={{ fill: "#6b7280", fontSize: 10 }} tickFormatter={v => v.toFixed(1)} />
                        <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} domain={[0, 1]} />
                        <Tooltip contentStyle={{ background: "#161b27", border: "1px solid #1f2937", borderRadius: 8 }} />
                        <Bar dataKey="fraction_positive" fill="#6366f1" radius={[4, 4, 0, 0]} name="Fraction Positive" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
