import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Globe2, Network, AlertTriangle, Lightbulb,
  FlaskConical, ShieldAlert, Radio, BarChart2, FileText,
  MessageSquare, Microscope, Layers, Activity, GitMerge,
  Sliders, Users, Dna,
} from "lucide-react";
import { cn } from "../lib/utils.js";

const NAV_SECTIONS = [
  {
    label: "Analysis",
    items: [
      { to: "/overview",        label: "Overview",         icon: LayoutDashboard },
      { to: "/universes",       label: "Universes",        icon: Globe2 },
      { to: "/network",         label: "Network Graph",    icon: Network },
      { to: "/pareto",          label: "Pareto Frontier",  icon: GitMerge },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { to: "/autopsy",         label: "Failure Autopsy",  icon: AlertTriangle },
      { to: "/cases",           label: "Case Management",  icon: Layers },
      { to: "/sar",             label: "SAR Reports",      icon: FileText },
      { to: "/recommendations", label: "Recommendations",  icon: Lightbulb },
      { to: "/entity",          label: "Entity Resolution",icon: Users },
    ],
  },
  {
    label: "ML & Explainability",
    items: [
      { to: "/explainability",  label: "SHAP Explainer",   icon: Microscope },
      { to: "/drift",           label: "Drift Monitor",    icon: Activity },
      { to: "/threshold",       label: "Threshold Sim",    icon: Sliders },
    ],
  },
  {
    label: "Advanced",
    items: [
      { to: "/live",            label: "Live Stream",      icon: Radio },
      { to: "/backtesting",     label: "Backtesting",      icon: BarChart2 },
      { to: "/mutations",       label: "Mutations",        icon: FlaskConical },
      { to: "/chat",            label: "AI Chat (RAG)",    icon: MessageSquare },
    ],
  },
];

export default function Sidebar() {
  return (
    <aside className="w-60 shrink-0 flex flex-col bg-surface-card border-r border-surface-border">
      <div className="flex items-center gap-3 px-5 py-5 border-b border-surface-border">
        <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center shrink-0">
          <ShieldAlert size={16} className="text-white" />
        </div>
        <div>
          <p className="font-semibold text-sm text-white leading-tight">AML Multiverse</p>
          <p className="text-xs text-gray-500">Simulator v3</p>
        </div>
      </div>

      <nav className="flex-1 py-4 px-3 overflow-y-auto space-y-5">
        {NAV_SECTIONS.map(({ label, items }) => (
          <div key={label}>
            <p className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-gray-600">
              {label}
            </p>
            <div className="space-y-0.5">
              {items.map(({ to, label: itemLabel, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
                      isActive
                        ? "bg-brand-600/15 text-brand-400 border border-brand-600/20"
                        : "text-gray-400 hover:text-white hover:bg-surface-hover"
                    )
                  }
                >
                  <Icon size={15} />
                  {itemLabel}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="px-5 py-4 border-t border-surface-border">
        <p className="text-xs text-gray-600">AML Multiverse v3.0</p>
        <p className="text-xs text-gray-700 mt-0.5">GNN · RAG · Pareto · Optuna</p>
      </div>
    </aside>
  );
}
