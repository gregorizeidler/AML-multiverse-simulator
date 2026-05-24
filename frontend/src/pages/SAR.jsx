import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileText, ChevronDown, ChevronUp, DollarSign, Users, AlertTriangle } from "lucide-react";
import { api } from "../lib/api.js";
import { fmtMoney, fmtCount } from "../lib/utils.js";
import PageHeader from "../components/PageHeader.jsx";
import { PageLoader, ErrorState } from "../components/LoadingState.jsx";

const TYPOLOGY_COLORS = {
  smurfing:      { bg: "bg-brand-500/10",  text: "text-brand-400",  border: "border-brand-500/20" },
  layering:      { bg: "bg-amber-500/10",  text: "text-amber-400",  border: "border-amber-500/20" },
  structuring:   { bg: "bg-green-500/10",  text: "text-green-400",  border: "border-green-500/20" },
  round_tripping:{ bg: "bg-pink-500/10",   text: "text-pink-400",   border: "border-pink-500/20"  },
  unknown:       { bg: "bg-gray-500/10",   text: "text-gray-400",   border: "border-gray-500/20"  },
};

function TypologyBadge({ typology }) {
  const s = TYPOLOGY_COLORS[typology] || TYPOLOGY_COLORS.unknown;
  return (
    <span className={`badge ${s.bg} ${s.text} border ${s.border} capitalize`}>
      {typology?.replace("_", " ")}
    </span>
  );
}

function SARCard({ report }) {
  const [expanded, setExpanded] = useState(false);
  const fin = report.financial_activity || {};
  const typologies = report.typologies || {};

  return (
    <div className="card hover:bg-surface-hover transition-colors cursor-pointer"
         onClick={() => setExpanded((v) => !v)}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-red-500/10 shrink-0">
            <FileText size={16} className="text-red-400" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-xs text-gray-500">{report.sar_id}</span>
              <TypologyBadge typology={typologies.primary} />
            </div>
            <p className="text-sm font-semibold text-white mb-0.5">
              {typologies.primary?.replace("_", " ")?.toUpperCase()} — {report.universe_id}
            </p>
            <p className="text-xs text-gray-500">
              Activity: {report.activity_period?.start} → {report.activity_period?.end}
              {" · "}Filing: {report.filing_date}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4 shrink-0">
          <div className="text-right">
            <p className="text-xs text-gray-500">Suspicious Amount</p>
            <p className="text-sm font-mono font-semibold text-red-400">
              {fmtMoney(fin.total_suspicious_amount)}
            </p>
          </div>
          {expanded ? (
            <ChevronUp size={16} className="text-gray-500" />
          ) : (
            <ChevronDown size={16} className="text-gray-500" />
          )}
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-surface-border">
        {[
          ["Transactions", fmtCount(fin.n_transactions), ""],
          ["Avg Alert Score", fin.avg_alert_score?.toFixed(3), "text-brand-400"],
          ["Max Score", fin.max_alert_score?.toFixed(3), "text-red-400"],
          ["Subjects", fmtCount(report.subjects?.length), ""],
        ].map(([label, value, color]) => (
          <div key={label}>
            <p className="text-xs text-gray-500">{label}</p>
            <p className={`text-sm font-mono font-semibold mt-0.5 ${color || "text-white"}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="mt-5 space-y-5" onClick={(e) => e.stopPropagation()}>
          {/* Narrative */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              SAR Narrative
            </p>
            <div className="bg-surface border border-surface-border rounded-lg p-4 text-xs text-gray-400 leading-relaxed whitespace-pre-wrap font-mono">
              {report.narrative}
            </div>
          </div>

          {/* Subjects */}
          {report.subjects?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1">
                <Users size={11} /> Subjects ({report.subjects.length})
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {report.subjects.map((s, i) => (
                  <div key={i} className="bg-surface border border-surface-border rounded-lg px-4 py-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-xs text-white">{s.account_id}</span>
                      <span className={`badge text-xs capitalize ${
                        s.role === "originator" ? "bg-red-500/10 text-red-400" :
                        s.role === "beneficiary" ? "bg-amber-500/10 text-amber-400" :
                        "bg-gray-500/10 text-gray-400"
                      }`}>{s.role}</span>
                    </div>
                    <div className="flex gap-3 text-xs text-gray-500">
                      <span>{fmtCount(s.transaction_count)} txns</span>
                      <span>{fmtMoney(s.total_amount)}</span>
                      <span>{s.countries?.join(", ")}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommended actions */}
          {report.recommended_actions?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1">
                <AlertTriangle size={11} /> Recommended Actions
              </p>
              <ul className="space-y-1">
                {report.recommended_actions.map((action, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-gray-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-400 mt-1.5 shrink-0" />
                    {action}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function SAR() {
  const { data: reports = [], isLoading, error } = useQuery({
    queryKey: ["sar"],
    queryFn: api.sar,
  });

  const [filter, setFilter] = useState("all");

  if (isLoading) return <PageLoader message="Loading SAR reports…" />;
  if (error) return <ErrorState error={error} />;

  const typologies = ["all", ...new Set(reports.map((r) => r.typologies?.primary).filter(Boolean))];
  const filtered = filter === "all" ? reports : reports.filter((r) => r.typologies?.primary === filter);

  const totalAmount = reports.reduce((s, r) => s + (r.financial_activity?.total_suspicious_amount || 0), 0);

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="SAR Reports"
        subtitle="Auto-generated Suspicious Activity Reports — review and complete before filing to FinCEN"
      />

      <div className="p-8 space-y-6">
        {/* Summary KPIs */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="metric-card">
            <span className="metric-label">Total SARs</span>
            <span className="metric-value">{reports.length}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Total Suspicious Amount</span>
            <span className="metric-value text-red-400">{fmtMoney(totalAmount)}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Typologies Covered</span>
            <span className="metric-value">{typologies.length - 1}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Universes</span>
            <span className="metric-value">{new Set(reports.map((r) => r.universe_id)).size}</span>
          </div>
        </div>

        {/* Disclaimer */}
        <div className="card border-amber-500/20 bg-amber-500/5 text-xs text-amber-400 flex gap-2">
          <AlertTriangle size={14} className="shrink-0 mt-0.5" />
          <span>
            These SAR narratives are auto-generated by the AML Multiverse Simulator for educational
            purposes. A licensed compliance officer must review, validate, and complete each SAR before
            any submission to FinCEN or other regulatory bodies.
          </span>
        </div>

        {/* Filter */}
        <div className="flex gap-2 flex-wrap">
          {typologies.map((t) => (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                filter === t
                  ? "bg-brand-600 text-white"
                  : "bg-surface-card border border-surface-border text-gray-400 hover:text-white"
              }`}
            >
              {t === "all" ? "All" : t.replace("_", " ")}
            </button>
          ))}
        </div>

        {/* SAR cards */}
        <div className="space-y-4">
          {filtered.map((report) => (
            <SARCard key={report.sar_id} report={report} />
          ))}
          {filtered.length === 0 && (
            <div className="text-center py-16 text-gray-600">
              No SAR reports found. Run the simulation to generate them.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
