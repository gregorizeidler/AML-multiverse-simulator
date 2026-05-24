import { clsx } from "clsx";

export function cn(...args) {
  return clsx(...args);
}

export function fmtPct(v, decimals = 1) {
  if (v == null) return "—";
  return `${(v * 100).toFixed(decimals)}%`;
}

export function fmtNum(v, decimals = 3) {
  if (v == null) return "—";
  return Number(v).toFixed(decimals);
}

export function fmtMoney(v) {
  if (v == null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(v);
}

export function fmtCount(v) {
  if (v == null) return "—";
  return new Intl.NumberFormat("en-US").format(v);
}

export function rankColor(rank) {
  if (rank === 1) return "text-yellow-400";
  if (rank === 2) return "text-gray-300";
  if (rank === 3) return "text-amber-600";
  return "text-gray-500";
}

export function scoreColor(score) {
  if (score >= 0.7) return "#22c55e";
  if (score >= 0.5) return "#f59e0b";
  return "#ef4444";
}

export const UNIVERSE_COLORS = [
  "#6366f1", "#22c55e", "#f59e0b", "#ec4899", "#14b8a6",
];

export const PRIORITY_STYLES = {
  high: "bg-red-500/10 text-red-400 border border-red-500/20",
  medium: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  low: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  info: "bg-brand-500/10 text-brand-400 border border-brand-500/20",
};
