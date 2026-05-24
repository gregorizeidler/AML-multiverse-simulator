import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Sliders, Play, RefreshCw } from "lucide-react";
import { fmtMoney, fmtPct } from "../lib/utils.js";
import { api } from "../lib/api.js";
import PageHeader from "../components/PageHeader.jsx";
import { PageLoader, ErrorState } from "../components/LoadingState.jsx";

async function simulateThresholds(universeId, thresholds, alertThreshold) {
  const res = await fetch("/api/simulate-thresholds", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ universe_id: universeId, thresholds, alert_threshold: alertThreshold }),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

function MetricDelta({ label, baseline, current, invert = false }) {
  const delta = current - baseline;
  const pct = baseline !== 0 ? (delta / Math.abs(baseline)) * 100 : 0;
  const isGood = invert ? delta < 0 : delta > 0;
  return (
    <div className="metric-card">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{typeof current === "number" && current < 10 ? current.toFixed(4) : fmtMoney(current)}</span>
      {delta !== 0 && (
        <span className={`text-xs font-mono ${isGood ? "text-green-400" : "text-red-400"}`}>
          {delta > 0 ? "+" : ""}{pct.toFixed(1)}%
        </span>
      )}
    </div>
  );
}

export default function ThresholdSimulator() {
  const { data: universes = [], isLoading, error } = useQuery({
    queryKey: ["universes"],
    queryFn: api.universes,
  });

  const [selectedId, setSelectedId] = useState(null);
  const [thresholds, setThresholds] = useState({});
  const [alertThreshold, setAlertThreshold] = useState(null);
  const [simResult, setSimResult] = useState(null);
  const [simLoading, setSimLoading] = useState(false);
  const [simError, setSimError] = useState(null);

  const activeUniverse = universes.find(u => u.universe_id === (selectedId || universes[0]?.universe_id));

  const handleSelectUniverse = (u) => {
    setSelectedId(u.universe_id);
    setThresholds({});
    setAlertThreshold(u.config?.scoring?.alert_threshold || 2.5);
    setSimResult(null);
  };

  const handleThresholdChange = (ruleId, value) => {
    setThresholds(prev => ({ ...prev, [ruleId]: parseFloat(value) }));
  };

  const handleSimulate = async () => {
    if (!activeUniverse) return;
    setSimLoading(true);
    setSimError(null);
    try {
      const result = await simulateThresholds(
        activeUniverse.universe_id,
        thresholds,
        alertThreshold || activeUniverse.config?.scoring?.alert_threshold
      );
      setSimResult(result);
    } catch (e) {
      setSimError(e.message);
    } finally {
      setSimLoading(false);
    }
  };

  if (isLoading) return <PageLoader message="Loading universes…" />;
  if (error)     return <ErrorState error={error} />;

  const baseline = activeUniverse?.metrics;
  const rules    = activeUniverse?.config?.rules || [];

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Threshold Simulator"
        subtitle="Interactively tune rule thresholds and see real-time impact on F1, Recall, FPR, and Cost"
      />
      <div className="p-8 space-y-6">
        {/* Universe selector */}
        <div className="flex gap-2 flex-wrap">
          {universes.map(u => (
            <button
              key={u.universe_id}
              onClick={() => handleSelectUniverse(u)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-all ${
                (selectedId || universes[0]?.universe_id) === u.universe_id
                  ? "bg-brand-600 text-white border-brand-600"
                  : "bg-surface-card border-surface-border text-gray-400 hover:text-white"
              }`}
            >
              {u.name?.replace(" AML Strategy", "")}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Controls */}
          <div className="card space-y-5">
            <div className="flex items-center gap-2">
              <Sliders size={14} className="text-brand-400" />
              <h3 className="text-sm font-semibold text-white">Rule Thresholds</h3>
            </div>

            {rules.length === 0 && (
              <p className="text-xs text-gray-500">Select a universe to see its rules.</p>
            )}

            {rules.map(rule => {
              const orig = rule.threshold;
              const current = thresholds[rule.id] ?? orig;
              return (
                <div key={rule.id}>
                  <div className="flex justify-between text-xs text-gray-400 mb-1">
                    <span className="font-medium text-gray-300">{rule.name || rule.id}</span>
                    <span className="font-mono">{current?.toFixed(3)}</span>
                  </div>
                  <input
                    type="range"
                    min={Math.max(orig * 0.2, 0.001)}
                    max={orig * 2.0}
                    step={orig * 0.01}
                    value={current}
                    onChange={e => handleThresholdChange(rule.id, e.target.value)}
                    className="w-full accent-brand-500"
                  />
                  <div className="flex justify-between text-[10px] text-gray-700">
                    <span>{(orig * 0.2).toFixed(2)}</span>
                    <span className="text-gray-600">baseline: {orig}</span>
                    <span>{(orig * 2.0).toFixed(2)}</span>
                  </div>
                </div>
              );
            })}

            {/* Alert threshold */}
            {baseline && (
              <div>
                <div className="flex justify-between text-xs text-gray-400 mb-1">
                  <span className="font-medium text-brand-300">Alert Threshold (sum of weights)</span>
                  <span className="font-mono">{(alertThreshold ?? activeUniverse?.config?.scoring?.alert_threshold ?? 2.5).toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min={0.5}
                  max={10}
                  step={0.1}
                  value={alertThreshold ?? activeUniverse?.config?.scoring?.alert_threshold ?? 2.5}
                  onChange={e => setAlertThreshold(parseFloat(e.target.value))}
                  className="w-full accent-brand-500"
                />
              </div>
            )}

            <div className="flex gap-3 pt-2">
              <button
                onClick={handleSimulate}
                disabled={simLoading || !activeUniverse}
                className="btn-primary flex-1 disabled:opacity-40"
              >
                {simLoading ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
                {simLoading ? "Simulating…" : "Simulate"}
              </button>
              <button
                onClick={() => { setThresholds({}); setSimResult(null); }}
                className="btn-ghost"
              >
                Reset
              </button>
            </div>

            {simError && (
              <p className="text-xs text-red-400 bg-red-500/10 rounded-lg px-3 py-2">{simError}</p>
            )}
          </div>

          {/* Results */}
          <div className="space-y-4">
            {!simResult && !simLoading && (
              <div className="card h-full flex items-center justify-center text-gray-600 text-sm">
                Adjust thresholds and click Simulate to see impact
              </div>
            )}

            {simResult && (
              <>
                <div className="card border-brand-500/20 bg-brand-500/5">
                  <p className="text-xs text-gray-400">
                    <strong className="text-brand-300">Ranking Score:</strong>{" "}
                    {simResult.ranking_score?.toFixed(4)} vs baseline {baseline?.ranking_score?.toFixed(4)}{" "}
                    <span className={simResult.ranking_score > (baseline?.ranking_score || 0) ? "text-green-400" : "text-red-400"}>
                      ({simResult.ranking_score > (baseline?.ranking_score || 0) ? "+" : ""}
                      {((simResult.ranking_score - (baseline?.ranking_score || 0)) * 100).toFixed(1)}%)
                    </span>
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  {[
                    ["F1 Score", "f1", false],
                    ["Recall", "recall", false],
                    ["Precision", "precision", false],
                    ["FPR", "false_positive_rate", true],
                    ["Alerts", "n_alerts", false],
                    ["Total Cost", "total_cost", true],
                  ].map(([label, key, invert]) => (
                    <MetricDelta
                      key={key}
                      label={label}
                      baseline={baseline?.[key] || 0}
                      current={simResult[key] || 0}
                      invert={invert}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
