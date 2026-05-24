import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, AlertTriangle, Info, TrendingUp, DollarSign } from "lucide-react";
import { api } from "../lib/api.js";
import { fmtPct, fmtNum, fmtMoney, PRIORITY_STYLES } from "../lib/utils.js";
import PageHeader from "../components/PageHeader.jsx";
import { PageLoader, ErrorState } from "../components/LoadingState.jsx";

const PRIORITY_ICONS = {
  high: AlertTriangle,
  medium: TrendingUp,
  low: Info,
  info: CheckCircle2,
};

const TYPE_LABELS = {
  threshold_adjustment: "Threshold Adjustment",
  cost_optimization: "Cost Optimization",
  deploy_recommendation: "Deploy Recommendation",
  hybrid_strategy: "Hybrid Strategy",
  cost_analysis: "Cost Analysis",
};

export default function Recommendations() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["recommendations"],
    queryFn: api.recommendations,
  });

  if (isLoading) return <PageLoader message="Loading recommendations…" />;
  if (error) return <ErrorState error={error} />;

  const {
    best_universe_name,
    best_metrics = {},
    recommendations = [],
    policy_summary,
  } = data;

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Policy Recommendations"
        subtitle="AI-driven analysis of all universes with actionable deployment guidance"
      />

      <div className="p-8 space-y-8">
        {/* Policy summary banner */}
        {policy_summary && (
          <div className="card border-brand-600/30 bg-brand-600/5">
            <div className="flex gap-3">
              <CheckCircle2 className="text-brand-400 shrink-0 mt-0.5" size={18} />
              <div>
                <p className="text-sm font-semibold text-white mb-1">Policy Summary</p>
                <p className="text-sm text-gray-400 leading-relaxed">{policy_summary}</p>
              </div>
            </div>
          </div>
        )}

        {/* Best universe KPIs */}
        {best_universe_name && (
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
              Recommended Universe — <span className="text-brand-400">{best_universe_name}</span>
            </h2>
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              <div className="metric-card">
                <span className="metric-label">F1 Score</span>
                <span className="metric-value">{fmtNum(best_metrics.f1)}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">Recall</span>
                <span className="metric-value">{fmtPct(best_metrics.recall)}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">Precision</span>
                <span className="metric-value">{fmtPct(best_metrics.precision)}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">FPR</span>
                <span className="metric-value">{fmtPct(best_metrics.false_positive_rate)}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">Total Cost</span>
                <span className="metric-value text-red-400">{fmtMoney(best_metrics.total_cost)}</span>
              </div>
            </div>
          </div>
        )}

        {/* Recommendation cards */}
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-4">
            Actionable Recommendations
          </h2>
          <div className="space-y-4">
            {recommendations.map((rec, i) => {
              const Icon = PRIORITY_ICONS[rec.priority] || Info;
              const style = PRIORITY_STYLES[rec.priority] || PRIORITY_STYLES.info;
              return (
                <div key={i} className="card hover:bg-surface-hover transition-colors">
                  <div className="flex items-start gap-4">
                    <div
                      className="p-2 rounded-lg shrink-0"
                      style={{
                        background:
                          rec.priority === "high"
                            ? "#ef444415"
                            : rec.priority === "medium"
                            ? "#f59e0b15"
                            : "#6366f115",
                      }}
                    >
                      <Icon
                        size={16}
                        className={
                          rec.priority === "high"
                            ? "text-red-400"
                            : rec.priority === "medium"
                            ? "text-amber-400"
                            : "text-brand-400"
                        }
                      />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`badge ${style} text-xs`}>
                          {rec.priority?.toUpperCase()}
                        </span>
                        <span className="text-xs text-gray-600">
                          {TYPE_LABELS[rec.type] || rec.type}
                        </span>
                      </div>
                      <h3 className="text-sm font-semibold text-white mb-1">{rec.title}</h3>
                      <p className="text-sm text-gray-400 mb-3">{rec.detail}</p>
                      <div className="flex items-center gap-2 bg-surface rounded-lg px-3 py-2 border border-surface-border">
                        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider shrink-0">
                          Action
                        </span>
                        <span className="text-xs text-gray-300 font-mono">{rec.suggested_action}</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
            {recommendations.length === 0 && (
              <div className="text-center py-12 text-gray-600">
                No recommendations available. Run the simulation first.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
