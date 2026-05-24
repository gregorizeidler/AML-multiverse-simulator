import { useQuery } from "@tanstack/react-query";
import { FlaskConical, GitBranch } from "lucide-react";
import { api } from "../lib/api.js";
import PageHeader from "../components/PageHeader.jsx";
import { PageLoader, ErrorState } from "../components/LoadingState.jsx";

export default function Mutations() {
  const { data: mutations = [], isLoading, error } = useQuery({
    queryKey: ["mutations"],
    queryFn: api.mutations,
  });

  if (isLoading) return <PageLoader message="Loading mutation configs…" />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Mutation Engine"
        subtitle="Auto-generated universe config variants from the evolutionary optimizer"
      />

      <div className="p-8 space-y-4">
        <div className="card border-amber-500/20 bg-amber-500/5 mb-6">
          <div className="flex gap-3">
            <FlaskConical className="text-amber-400 shrink-0 mt-0.5" size={18} />
            <div>
              <p className="text-sm font-semibold text-white mb-1">How It Works</p>
              <p className="text-sm text-gray-400">
                The mutation engine takes the top-2 ranked universes, randomly perturbs their
                rule thresholds, weights, and scoring parameters, and generates new candidate
                configs. These can be saved as YAML files and re-simulated in the next round.
              </p>
            </div>
          </div>
        </div>

        {mutations.length === 0 ? (
          <div className="text-center py-16 text-gray-600">
            No mutations available. Run the simulation first.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {mutations.map((mut, i) => (
              <div key={i} className="card">
                <div className="flex items-start gap-3 mb-4">
                  <div className="p-2 rounded-lg bg-brand-600/10 shrink-0">
                    <GitBranch size={16} className="text-brand-400" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white">{mut.name}</h3>
                    <p className="text-xs text-gray-500 font-mono">{mut.id}</p>
                  </div>
                </div>

                {/* Mutation log */}
                {mut._mutation_log && mut._mutation_log.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      Mutations Applied
                    </p>
                    <div className="space-y-1">
                      {mut._mutation_log.map((entry, j) => (
                        <div
                          key={j}
                          className="flex items-center gap-2 bg-surface rounded px-3 py-1.5 border border-surface-border"
                        >
                          <span className="w-1.5 h-1.5 rounded-full bg-brand-400 shrink-0" />
                          <span className="text-xs font-mono text-gray-300">{entry}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Scoring thresholds */}
                {mut.scoring && (
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-surface rounded-lg px-4 py-3 border border-surface-border">
                      <p className="text-xs text-gray-500 uppercase tracking-wider">Alert Threshold</p>
                      <p className="text-lg font-mono font-semibold text-brand-400 mt-0.5">
                        {mut.scoring.alert_threshold}
                      </p>
                    </div>
                    <div className="bg-surface rounded-lg px-4 py-3 border border-surface-border">
                      <p className="text-xs text-gray-500 uppercase tracking-wider">High Risk Threshold</p>
                      <p className="text-lg font-mono font-semibold text-red-400 mt-0.5">
                        {mut.scoring.high_risk_threshold}
                      </p>
                    </div>
                  </div>
                )}

                {/* Rules summary */}
                <div className="mt-4">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                    Rules ({mut.rules?.length || 0})
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {(mut.rules || []).map((r) => (
                      <div
                        key={r.id}
                        className="bg-surface border border-surface-border rounded px-2 py-1 text-xs"
                      >
                        <span className="text-gray-500 font-mono">{r.id}</span>
                        <span className="text-gray-600 mx-1">·</span>
                        <span className="text-gray-300">{r.name}</span>
                        <span className="text-gray-600 mx-1">·</span>
                        <span className="font-mono text-brand-400">
                          {r.operator} {r.threshold}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
