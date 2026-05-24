import { cn } from "../lib/utils.js";

export default function MetricCard({ label, value, sub, accent, icon: Icon }) {
  return (
    <div className="metric-card">
      <div className="flex items-center justify-between">
        <span className="metric-label">{label}</span>
        {Icon && (
          <span className={cn("p-1.5 rounded-lg", accent || "bg-brand-500/10")}>
            <Icon size={14} className="text-brand-400" />
          </span>
        )}
      </div>
      <span className="metric-value">{value}</span>
      {sub && <span className="metric-sub">{sub}</span>}
    </div>
  );
}
